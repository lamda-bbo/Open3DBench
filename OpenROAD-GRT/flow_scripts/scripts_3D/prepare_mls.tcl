# Optional GRT_PREPARE_TCL hook. Export the loaded OpenDB design, plan metal
# layer sharing in Python, and apply the resulting OpenDB edits once. The
# caller persists the shared ODB/DEF used by both die routing processes.
namespace eval mls_prepare {
  variable script_dir [file dirname [file normalize [info script]]]
  variable die_cache [dict create]

  proc json_string {value} {
    set escaped [string map [list \\ \\\\ \" \\\" \n \\n \r \\r \t \\t \b \\b \f \\f] $value]
    # Instance/net names can contain Tcl metacharacters and control characters.
    # JSON encoding must preserve their literal spelling without evaluation.
    # Normal DEF names contain no control bytes after the string-map above.
    # Avoid a per-character Tcl loop for every net and terminal in large cases.
    if {![regexp {[\x00-\x1f]} $escaped]} { return \"$escaped\" }
    set result ""
    foreach ch [split $escaped ""] {
      scan $ch %c code
      if {$code < 32} {
        append result [format {\u%04x} $code]
      } else {
        append result $ch
      }
    }
    return \"$result\"
  }

  proc hbt_name {name} {
    return [expr {[string match HBT_* $name] || [string match LS_HBT_* $name]}]
  }

  proc instance_die {inst} {
    variable die_cache
    set inst_name [$inst getName]
    if {[dict exists $die_cache $inst_name]} { return [dict get $die_cache $inst_name] }
    foreach name [list $inst_name [[$inst getMaster] getName]] {
      if {[string match *_bottom $name]} {
        dict set die_cache $inst_name bottom
        return bottom
      }
      if {[string match *_upper $name]} {
        dict set die_cache $inst_name upper
        return upper
      }
    }
    dict set die_cache $inst_name ""
    return ""
  }

  proc layer_die {layer} {
    if {$layer ne "NULL" && [regexp {^metal([0-9]+)$} [$layer getName] -> number]} {
      if {$number <= 10} { return bottom }
      return upper
    }
    return ""
  }

  proc json_die {die} {
    if {$die eq ""} { return null }
    return [json_string $die]
  }

  proc rect_values {rect} {
    return [list [$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]]
  }

  proc use_native_scan {command} {
    set mode [expr {[info exists ::env(MLS_PREPARE_SCAN)] ? $::env(MLS_PREPARE_SCAN) : "auto"}]
    if {$mode ni {auto native tcl}} { error "Invalid MLS_PREPARE_SCAN '$mode'" }
    set available [expr {[info commands $command] ne ""}]
    if {$mode eq "native" && !$available} { error "Native MLS scan unavailable: $command" }
    return [expr {$mode ne "tcl" && $available}]
  }

  proc inst_snapshot {block} {
    if {[use_native_scan ::grt::mls_instance_snapshot]} {
      set records [::grt::mls_instance_snapshot]
      if {[llength $records] % 6 != 0} { error "Malformed native MLS component snapshot" }
      set snapshot [dict create]
      foreach {name master x y orient status} $records {
        dict set snapshot $name [list $master [list $x $y] $orient $status]
      }
      return $snapshot
    }
    set snapshot [dict create]
    foreach inst [$block getInsts] {
      set name [$inst getName]
      if {[hbt_name $name]} { continue }
      dict set snapshot $name [list [[$inst getMaster] getName] \
        [$inst getOrigin] [$inst getOrient] [$inst getPlacementStatus]]
    }
    return $snapshot
  }

  proc bterm_snapshot {block} {
    set snapshot [dict create]
    foreach bterm [$block getBTerms] {
      set net [$bterm getNet]
      set net_name ""
      if {$net ne "NULL"} { set net_name [$net getName] }
      set geometry {}
      foreach bpin [$bterm getBPins] {
        set boxes {}
        foreach box [$bpin getBoxes] {
          lappend boxes [list [[$box getTechLayer] getName] \
            [rect_values $box]]
        }
        lappend geometry [list [$bpin getPlacementStatus] $boxes]
      }
      dict set snapshot [$bterm getName] [list [$bterm getIoType] \
        [$bterm getSigType] $net_name $geometry]
    }
    return $snapshot
  }

  proc check_snapshot {before after what} {
    if {[dict size $before] != [dict size $after]} {
      error "MLS preparation changed the number of $what"
    }
    dict for {name value} $before {
      if {![dict exists $after $name] || [dict get $after $name] ne $value} {
        error "MLS preparation changed protected $what '$name'"
      }
    }
  }

  proc check_hbt_master {db name} {
    set master [$db findMaster $name]
    if {$master eq "NULL"} { error "MLS requires HBT master '$name'" }
    foreach {pin expected_layer} {BOT metal10 TOP metal11} {
      set mterm [$master findMTerm $pin]
      if {$mterm eq "NULL"} { error "$name is missing terminal $pin" }
      set found 0
      foreach mpin [$mterm getMPins] {
        foreach box [$mpin getGeometry] {
          set layer [$box getTechLayer]
          if {$layer ne "NULL" && [$layer getName] eq $expected_layer} { set found 1 }
        }
      }
      if {!$found} { error "$name/$pin has no geometry on $expected_layer" }
    }
    return $master
  }

  proc iterm_record {iterm} {
    set inst [$iterm getInst]
    set name [$inst getName]
    set pin [[$iterm getMTerm] getName]
    set is_hbt [hbt_name $name]
    set die [instance_die $inst]
    if {$is_hbt} {
      if {$pin eq "BOT"} { set die bottom }
      if {$pin eq "TOP"} { set die upper }
    }
    lassign [$iterm getAvgXY] valid x y
    if {!$valid} {
      set box [$inst getBBox]
      set x [expr {([$box xMin] + [$box xMax]) / 2}]
      set y [expr {([$box yMin] + [$box yMax]) / 2}]
    }
    set hbt_json [expr {$is_hbt ? "true" : "false"}]
    return [format {{"inst":%s,"pin":%s,"x":%d,"y":%d,"die":%s,"io":%s,"hbt":%s}} \
      [json_string $name] [json_string $pin] $x $y [json_die $die] \
      [json_string [$iterm getIoType]] $hbt_json]
  }

  proc bterm_record {bterm} {
    set count 0
    set sx 0
    set sy 0
    set dies {}
    foreach bpin [$bterm getBPins] {
      foreach box [$bpin getBoxes] {
        set rect $box
        incr sx [expr {([$rect xMin] + [$rect xMax]) / 2}]
        incr sy [expr {([$rect yMin] + [$rect yMax]) / 2}]
        incr count
        set die [layer_die [$box getTechLayer]]
        if {$die ne "" && [lsearch -exact $dies $die] < 0} { lappend dies $die }
      }
    }
    set die ""
    if {[llength $dies] == 1} { set die [lindex $dies 0] }
    set x [expr {$count ? $sx / $count : 0}]
    set y [expr {$count ? $sy / $count : 0}]
    return [format {{"inst":"PIN","pin":%s,"x":%d,"y":%d,"die":%s,"io":%s,"hbt":false}} \
      [json_string [$bterm getName]] $x $y [json_die $die] \
      [json_string [$bterm getIoType]]]
  }

  proc export_manifest {path db block bottom_master} {
    # Keep the portable exporter for independently checking the native path
    # and for binaries built before the optional command was introduced.
    set exporter [expr {[info exists ::env(MLS_MANIFEST_EXPORTER)] ? $::env(MLS_MANIFEST_EXPORTER) : "auto"}]
    if {$exporter ni {auto native tcl}} { error "Invalid MLS_MANIFEST_EXPORTER '$exporter'" }
    if {$exporter ne "tcl" && [info commands ::grt::export_mls_manifest] ne ""} {
      ::grt::export_mls_manifest $path
      return
    }
    if {$exporter eq "native"} { error "Native MLS manifest exporter is unavailable" }
    variable die_cache
    set die_cache [dict create]
    set dbu [$block getDbUnitsPerMicron]
    set grid [[ord::get_db_tech] getManufacturingGrid]
    if {$grid < 1} { set grid 1 }
    set area [rect_values [$block getDieArea]]
    set fp [open $path w]
    puts -nonewline $fp "\{"
    puts $fp [format {"dbu_per_micron":%d,"manufacturing_grid":%d,"die_area":[%s],"hbt_master_size":[%d,%d],"hbts":[} \
      $dbu $grid [join $area ,] [$bottom_master getWidth] [$bottom_master getHeight]]
    set sep ""
    foreach inst [$block getInsts] {
      set name [$inst getName]
      if {![hbt_name $name]} { continue }
      set box [$inst getBBox]
      set x [expr {([$box xMin] + [$box xMax]) / 2}]
      set y [expr {([$box yMin] + [$box yMax]) / 2}]
      puts $fp "$sep[format {{"name":%s,"x":%d,"y":%d}} [json_string $name] $x $y]"
      set sep ,
    }
    puts $fp {],"nets":[}
    set sep ""
    foreach net [$block getNets] {
      set pins {}
      foreach iterm [$net getITerms] { lappend pins [iterm_record $iterm] }
      set bterms [$net getBTerms]
      foreach bterm $bterms { lappend pins [bterm_record $bterm] }
      set special [expr {[$net isSpecial] ? "true" : "false"}]
      set has_bterms [expr {[llength $bterms] ? "true" : "false"}]
      puts $fp "$sep[format {{"name":%s,"signal_type":%s,"special":%s,"bterms":%s,"pins":[%s]}} \
        [json_string [$net getName]] [json_string [$net getSigType]] \
        $special $has_bterms [join $pins ,]]"
      set sep ,
    }
    puts $fp "\]\}"
    close $fp
  }

  proc run {} {
    variable script_dir
    unset -nocomplain ::grt_precomputed_layer_hints
    set db [ord::get_db]
    set block [ord::get_db_block]
    if {$block eq "NULL"} { error "MLS preparation requires a loaded design" }
    set bot_master [check_hbt_master $db HBT_BOTIN]
    set top_master [check_hbt_master $db HBT_TOPIN]
    if {[$bot_master getWidth] != [$top_master getWidth] || \
        [$bot_master getHeight] != [$top_master getHeight]} {
      error "MLS HBT masters must have equal dimensions"
    }
    set stage_start [clock milliseconds]
    set original_instances [inst_snapshot $block]
    set original_bterms [bterm_snapshot $block]
    puts "MLS_STAGE snapshot_before_ms=[expr {[clock milliseconds] - $stage_start}]"
    set manifest $::env(RESULTS_DIR)/mls_manifest.json
    set plan $::env(RESULTS_DIR)/mls_plan.json
    set apply_tcl $::env(RESULTS_DIR)/mls_apply.tcl
    set stage_start [clock milliseconds]
    export_manifest $manifest $db $block $bot_master
    puts "MLS_STAGE export_manifest_ms=[expr {[clock milliseconds] - $stage_start}]"
    set stage_start [clock milliseconds]
    # Protect clock/power master terminals even when the input DEF omitted USE.
    # This list is input data only; it does not mutate the netlist or STA state.
    set protected_path $::env(RESULTS_DIR)/mls_protected_nets.json
    set protected_fp [open $protected_path w]
    set protected_names {}
    if {[use_native_scan ::grt::mls_protected_net_names]} {
      foreach name [::grt::mls_protected_net_names] {
        lappend protected_names [json_string $name]
      }
    } else {
      # MTerm handles and types are stable throughout this read-only scan.
      # Keep the cache local to this run; every visited ITerm still resolves its
      # own master terminal, and first-read lookup errors must propagate.
      set protected_mterm_cache [dict create]
      foreach net [$block getNets] {
        set protected [expr {[$net getSigType] ne "SIGNAL" || [$net isSpecial]}]
        if {!$protected} {
          foreach iterm [$net getITerms] {
            set mterm [$iterm getMTerm]
            if {![dict exists $protected_mterm_cache $mterm]} {
              dict set protected_mterm_cache $mterm \
                [expr {[$mterm getSigType] in {CLOCK POWER GROUND}}]
            }
            if {[dict get $protected_mterm_cache $mterm]} {
              set protected 1
              break
            }
          }
        }
        if {$protected} { lappend protected_names [json_string [$net getName]] }
      }
    }
    puts $protected_fp "\[[join $protected_names ,]\]"
    close $protected_fp
    puts "MLS_STAGE protected_scan_ms=[expr {[clock milliseconds] - $stage_start}]"
    set command [list python3 $script_dir/mls_planner.py --manifest $manifest \
      --plan $plan --apply-tcl $apply_tcl --protected-nets $protected_path]
    if {[info exists ::env(MLS_CONFIG)] && $::env(MLS_CONFIG) ne ""} {
      lappend command --config [file normalize $::env(MLS_CONFIG)]
    }
    if {[info exists ::env(MLS_TIMING_CSV)] && $::env(MLS_TIMING_CSV) ne ""} {
      lappend command --timing-csv [file normalize $::env(MLS_TIMING_CSV)]
    }
    # Only the fused routing path consumes hints in this process. A unique
    # token proves that this invocation wrote both files, not merely that old
    # files happen to exist in the results directory.
    set hint_token ""
    if {(![info exists ::env(GRT_PROCESS_MODE)] || $::env(GRT_PROCESS_MODE) eq "single") &&
        [info exists ::env(GRT_HIGH_FANOUT_LAYERS)] && $::env(GRT_HIGH_FANOUT_LAYERS) eq "1"} {
      set hint_token "[pid]-[clock clicks]"
      set hint_tcl [file normalize $::env(RESULTS_DIR)/net_layer_hints.tcl]
      set hint_report [file normalize $::env(REPORTS_DIR)/net_layer_hints.json]
      lappend command --layer-hints-tcl $hint_tcl --layer-hints-report $hint_report \
        --layer-hints-token $hint_token
    }
    puts "MLS geometry manifest: $manifest"
    set stage_start [clock milliseconds]
    set planner_output [exec {*}$command 2>@1]
    puts $planner_output
    set hints_ready [expr {$hint_token ne "" &&
      [lsearch -exact [split $planner_output \n] "MLS_LAYER_HINTS_READY $hint_token"] >= 0}]
    puts "MLS_STAGE plan_ms=[expr {[clock milliseconds] - $stage_start}]"
    # Execute at global scope so the emitted script uses the usual OpenROAD
    # Tcl context, while all integration helpers remain in this namespace.
    set stage_start [clock milliseconds]
    uplevel #0 [list source $apply_tcl]
    puts "MLS_STAGE apply_ms=[expr {[clock milliseconds] - $stage_start}]"
    set stage_start [clock milliseconds]
    check_snapshot $original_instances [inst_snapshot $block] "non-HBT components"
    check_snapshot $original_bterms [bterm_snapshot $block] "package pins"
    puts "MLS_STAGE snapshot_after_ms=[expr {[clock milliseconds] - $stage_start}]"
    if {$hints_ready} {
      set ::grt_precomputed_layer_hints [dict create token $hint_token tcl $hint_tcl report $hint_report]
    }
    puts "MLS preparation preserved [dict size $original_instances] components and [dict size $original_bterms] package pins; plan: $plan"
  }
}

mls_prepare::run
