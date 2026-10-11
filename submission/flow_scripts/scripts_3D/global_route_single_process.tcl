# Two-pass GRT in one OpenROAD process. Both passes keep their
# original die-only layer interval. A native reset clears the queued subset;
# the portable fallback uses read_guides with temporary bottom-only net flags.
utl::set_metrics_stage "globalroute__fused"
source $::env(SCRIPTS_DIR)/load.tcl
proc fused_stage {name script} {
  set started [clock milliseconds]
  set result [uplevel 1 $script]
  puts "GRT_STAGE ${name}_ms=[expr {[clock milliseconds] - $started}]"
  return $result
}
proc fused_plan_layer_hints {script_dir} {
  set hints_tcl [file normalize $::env(RESULTS_DIR)/net_layer_hints.tcl]
  set hints_report [file normalize $::env(REPORTS_DIR)/net_layer_hints.json]
  set reused 0
  if {[info exists ::grt_precomputed_layer_hints]} {
    set ready $::grt_precomputed_layer_hints
    # This marker is local to one successful preparation and is consumed once.
    unset ::grt_precomputed_layer_hints
    if {[catch {
      set reused [expr {[dict get $ready token] ne "" &&
        [dict get $ready tcl] eq $hints_tcl && [dict get $ready report] eq $hints_report &&
        [file isfile $hints_tcl] && [file isfile $hints_report]}]
    }]} { set reused 0 }
  }
  if {!$reused} {
    puts [exec python3 $script_dir/plan_net_layer_hints.py \
      --manifest $::env(RESULTS_DIR)/mls_manifest.json --enable \
      --mls-plan $::env(RESULTS_DIR)/mls_plan.json \
      --output-tcl $hints_tcl --report-json $hints_report]
  }
  source $hints_tcl
}
proc fused_snapshot_sigtypes {block} {
  # In the supplied GRT, initClockNets is the only routing operation that
  # changes a net's SigType. It uses the same native findClkNets query.
  # The supplied FASTROUTE_TCL changes tracks/layer settings only, and both
  # routing passes preserve the netlist and SDC after this snapshot.
  set mode [expr {[info exists ::env(GRT_METADATA_SNAPSHOT)] ? $::env(GRT_METADATA_SNAPSHOT) : "auto"}]
  if {$mode ni {auto all}} { error "Invalid GRT_METADATA_SNAPSHOT '$mode'" }
  if {$mode eq "all"} {
    puts "GRT_METADATA_SNAPSHOT fallback=forced_all"
  } elseif {[info commands ::sta::find_all_clk_nets] ne ""} {
    set saved {}
    if {![catch {
      foreach net [::sta::find_all_clk_nets] {
        lappend saved [list $net [$net getSigType]]
      }
    }]} {
      puts "GRT_METADATA_SNAPSHOT mode=clock_nets count=[llength $saved]"
      return $saved
    }
    puts "GRT_METADATA_SNAPSHOT fallback=query_error"
  } else {
    puts "GRT_METADATA_SNAPSHOT fallback=missing_query"
  }
  # Discard any partial snapshot if querying or reading a returned net failed.
  set saved {}
  foreach net [$block getNets] {
    lappend saved [list $net [$net getSigType]]
  }
  puts "GRT_METADATA_SNAPSHOT mode=all_nets count=[llength $saved]"
  return $saved
}
set fused_started [clock milliseconds]
set fused_initial_design [expr {[info exists ::env(GRT_INITIAL_DESIGN)] ? $::env(GRT_INITIAL_DESIGN) : "4_cts.odb"}]
load_design $fused_initial_design 4_cts.sdc "Starting fused die-by-die global routing"
puts "GRT_STAGE load_design_ms=[expr {[clock milliseconds] - $fused_started}]"
set fused_script_dir [file dirname [file normalize [info script]]]
source $fused_script_dir/routing_capacity.tcl
set fused_input_def $::env(RESULTS_DIR)/4_1_cts.def
unset -nocomplain ::grt_precomputed_layer_hints
if {[info exists ::env(GRT_PREPARE_TCL)] && $::env(GRT_PREPARE_TCL) ne ""} {
  fused_stage prepare {source [file normalize $::env(GRT_PREPARE_TCL)]}
  set fused_input_def $::env(RESULTS_DIR)/4_grt_input.def
  fused_stage write_prepared {
    # The single process keeps this prepared database live for both passes.
    # Preserve the optional checkpoint for debugging, without serializing it
    # in the normal path. Classification and strict checks still use the DEF.
    if {[info exists ::env(GRT_SAVE_CHECKPOINTS)] && $::env(GRT_SAVE_CHECKPOINTS) eq "1"} {
      write_db $::env(RESULTS_DIR)/4_grt_input.odb
    }
    write_def $fused_input_def
  }
}
set ::env(GRT_INPUT_DEF) $fused_input_def
set ::grt_layer_hints [dict create]
set fused_hints_mode [expr {[info exists ::env(GRT_HIGH_FANOUT_LAYERS)] ? $::env(GRT_HIGH_FANOUT_LAYERS) : "0"}]
if {$fused_hints_mode ni {0 1}} { error "GRT_HIGH_FANOUT_LAYERS must be 0 or 1" }
set ::fused_hints_policy [expr {[info exists ::env(GRT_HIGH_FANOUT_POLICY)] ? $::env(GRT_HIGH_FANOUT_POLICY) : "layers"}]
if {$::fused_hints_policy ni {layers resistance}} { error "GRT_HIGH_FANOUT_POLICY must be layers or resistance" }
if {$fused_hints_mode eq "1" && [file exists $::env(RESULTS_DIR)/mls_manifest.json]} {
  fused_stage plan_layer_hints {
    fused_plan_layer_hints $fused_script_dir
  }
}
# Keep the pre-GRT metadata used by an isolated finalizer. make_tracks appends
# patterns to a populated grid, and GRT marks clock leaf nets as CLOCK.
fused_stage metadata_snapshot {
  set fused_block [ord::get_db_block]
  set fused_net_sigtypes [fused_snapshot_sigtypes $fused_block]
  set fused_track_patterns {}
  set fused_layer_adjustments {}
  foreach layer [[ord::get_db_tech] getLayers] {
    if {[$layer getType] ne "ROUTING"} { continue }
    lappend fused_layer_adjustments [list $layer [$layer getLayerAdjustment]]
    set track [$fused_block findTrackGrid $layer]
    set x_patterns {}
    set y_patterns {}
    set existed [expr {$track ne "NULL"}]
    if {$existed} {
      for {set i 0} {$i < [$track getNumGridPatternsX]} {incr i} {
        lappend x_patterns [$track getGridPatternX $i]
      }
      for {set i 0} {$i < [$track getNumGridPatternsY]} {incr i} {
        lappend y_patterns [$track getGridPatternY $i]
      }
    }
    lappend fused_track_patterns [list $layer $existed $x_patterns $y_patterns]
  }
}
if {[info exists ::env(FASTROUTE_TCL)]} { source $::env(FASTROUTE_TCL) }
if {[info commands set_net_routing_layers] eq ""} {
  error "Fused routing requires hard per-net routing layer constraints"
}
set fused_bot_min [expr {[info exists ::env(BOTTOM_DIE_MIN_LAYER)] ? $::env(BOTTOM_DIE_MIN_LAYER) : "metal2"}]
set fused_bot_max [expr {[info exists ::env(BOTTOM_DIE_MAX_LAYER)] ? $::env(BOTTOM_DIE_MAX_LAYER) : "metal10"}]
set fused_top_min [expr {[info exists ::env(UPPER_DIE_MIN_LAYER)] ? $::env(UPPER_DIE_MIN_LAYER) : "metal11"}]
set fused_top_max [expr {[info exists ::env(UPPER_DIE_MAX_LAYER)] ? $::env(UPPER_DIE_MAX_LAYER) : "metal20"}]
set fused_adjustment [expr {[info exists ::env(GLOBAL_ROUTING_LAYER_ADJUSTMENT)] ? $::env(GLOBAL_ROUTING_LAYER_ADJUSTMENT) : 0.5}]
set fused_args [expr {[info exists ::env(GLOBAL_ROUTE_ARGS)] ? $::env(GLOBAL_ROUTE_ARGS) : \
  {-allow_congestion -congestion_iterations 1 -congestion_report_iter_step 5 -verbose}}]
set fused_list_dir $::env(RESULTS_DIR)/die_net_lists
set fused_classification_cache $::env(RESULTS_DIR)/.net_classification.json
fused_stage classify_nets {
  exec python3 $fused_script_dir/export_die_net_lists.py $fused_input_def $fused_list_dir \
    --classification-cache $fused_classification_cache
}
set fused_block [ord::get_db_block]
proc fused_read_nets {path} {
  set fp [open $path r]
  set names {}
  foreach name [split [read $fp] "\n"] {
    set name [string trim $name]
    if {$name ne ""} { lappend names $name }
  }
  close $fp
  return $names
}
proc fused_route_pass {names min_layer max_layer guide report} {
  # An empty GRT queue means all nets in OpenROAD. Publish an empty pass
  # without calling the router when this die has no routable net.
  if {[llength $names] == 0} {
    set fp [open $guide w]
    close $fp
    set fp [open $report w]
    close $fp
    return
  }
  set_routing_layers -signal ${min_layer}-${max_layer}
  set_global_routing_layer_adjustment ${min_layer}-${max_layer} $::fused_adjustment
  grt_capacity::apply $min_layer $max_layer
  if {[info exists ::env(MACRO_EXTENSION)]} { set_macro_extension $::env(MACRO_EXTENSION) }
  set has_hints [expr {[dict size $::grt_layer_hints] > 0}]
  set hints_policy [expr {[info exists ::fused_hints_policy] ? $::fused_hints_policy : "layers"}]
  set hint_count 0
  set resistance_hint_count 0
  if {$has_hints && $hints_policy eq "resistance"} {
    if {[info commands ::grt::clear_net_resistance_aware] eq "" ||
        [info commands set_net_resistance_aware] eq ""} {
      error "Selected-net resistance routing requires the matching submitted GRT binary"
    }
    # The next pass must not inherit the first die's selected network set.
    ::grt::clear_net_resistance_aware
  }
  set enqueue_started [clock milliseconds]
  set dispatch [expr {[info exists ::env(GRT_LAYER_DISPATCH)] ? $::env(GRT_LAYER_DISPATCH) : "auto"}]
  if {$dispatch ni {auto legacy}} { error "Invalid GRT_LAYER_DISPATCH '$dispatch'" }
  set native_layers [expr {$dispatch ne "legacy" &&
    [info commands ::grt::set_net_routing_layers] ne "" &&
    [info commands ::grt::parse_layer_name] ne ""}]
  set tech [ord::get_db_tech]
  if {$native_layers} {
    # The public wrapper performs these same parses before forwarding a dbNet
    # and two layer integers to this existing native setter. Net existence,
    # hint clamps and native range validation still apply to every net.
    if {$::fused_block eq "NULL"} { error "Missing dbBlock" }
    set pass_min [::grt::parse_layer_name $min_layer]
    set pass_max [::grt::parse_layer_name $max_layer]
    if {$pass_min > $pass_max} { error "Net routing layer range must be min-max" }
  } else {
    set pass_min [[$tech findLayer $min_layer] getRoutingLevel]
    set pass_max [[$tech findLayer $max_layer] getRoutingLevel]
  }
  foreach name $names {
    set net [$::fused_block findNet $name]
    if {$net eq "NULL"} { error "Missing classified net '$name'" }
    set net_min $min_layer
    set net_max $max_layer
    set net_min_level $pass_min
    set net_max_level $pass_max
    if {$has_hints && [dict exists $::grt_layer_hints $name] && [$net getSigType] eq "SIGNAL"} {
      # Clock/power master pins can identify protected nets even if their
      # DEF USE was omitted. Never promote their routing floor/ceiling.
      set protected 0
      foreach iterm [$net getITerms] {
        if {[[$iterm getMTerm] getSigType] in {CLOCK POWER GROUND}} {
          set protected 1
          break
        }
      }
      if {!$protected} {
        if {$hints_policy eq "resistance"} {
          set_net_resistance_aware $name
          incr resistance_hint_count
        } else {
          lassign [dict get $::grt_layer_hints $name] hint_min hint_max
          set hint_lo [$tech findLayer $hint_min]
          set hint_hi [$tech findLayer $hint_max]
          if {$hint_lo eq "NULL" || $hint_hi eq "NULL"} { error "Unknown hinted routing layer for '$name'" }
          set lo [expr {max($pass_min, [$hint_lo getRoutingLevel])}]
          set hi [expr {min($pass_max, [$hint_hi getRoutingLevel])}]
          if {$lo > $hi} { error "Layer hint leaves no legal die layer for '$name'" }
          set net_min_level $lo
          set net_max_level $hi
          if {!$native_layers} {
            set net_min [[$tech findRoutingLayer $lo] getName]
            set net_max [[$tech findRoutingLayer $hi] getName]
          }
          incr hint_count
        }
      }
    }
    if {$native_layers} {
      ::grt::set_net_routing_layers $net $net_min_level $net_max_level
    } else {
      set_net_routing_layers $name $net_min $net_max
    }
    grt::add_net_to_route $net
  }
  puts "GRT_LAYER_DISPATCH native=$native_layers die=$min_layer-$max_layer"
  puts "GRT_STAGE enqueue_${min_layer}_${max_layer}_ms=[expr {[clock milliseconds] - $enqueue_started}]"
  puts "GRT_LAYER_HINTS applied=$hint_count die=$min_layer-$max_layer"
  puts "GRT_RESISTANCE_HINTS applied=$resistance_hint_count die=$min_layer-$max_layer"
  puts "Fused process pass: [llength $names] nets on $min_layer-$max_layer"
  global_route -guide_file $guide -congestion_report_file $report {*}$::fused_args
}
set fused_bottom [fused_read_nets $fused_list_dir/bottom_2d.txt]
set fused_upper [fused_read_nets $fused_list_dir/upper_2d.txt]
set fused_bottom_guide $::env(RESULTS_DIR)/route_bottom.guide
set fused_upper_guide $::env(RESULTS_DIR)/route_upper.guide
fused_stage route_bottom {
  fused_route_pass $fused_bottom $fused_bot_min $fused_bot_max \
    $fused_bottom_guide $::env(REPORTS_DIR)/congestion_bottom.rpt
}
set fused_started [clock milliseconds]

# For two nonempty passes the next global_route reconstructs router models
# and GCELL state. Clear only the queued subset and DB guides at this boundary.
# Keep the legacy path for older binaries and either empty-die edge case.
set fused_reset_mode [expr {[info exists ::env(GRT_PASS_RESET)] ? $::env(GRT_PASS_RESET) : "auto"}]
if {$fused_reset_mode ni {auto native legacy}} { error "Invalid GRT_PASS_RESET '$fused_reset_mode'" }
set fused_has_native_reset [expr {[info commands ::grt::reset_die_routing_pass] ne ""}]
if {$fused_reset_mode eq "native" && !$fused_has_native_reset} {
  error "Native die routing pass reset is unavailable"
}
if {$fused_reset_mode ne "legacy" && $fused_has_native_reset &&
    [llength $fused_bottom] > 0 && [llength $fused_upper] > 0} {
  ::grt::reset_die_routing_pass
  puts "GRT_PASS_RESET native"
} else {
  # read_guides clears nets_to_route_ without reloading the design or Liberty.
  # Only bottom nets may rebuild pin models on the current bottom-only grid.
  # The other nets' original special flags are restored before upper routing.
  set fused_bottom_set [dict create]
  foreach name $fused_bottom { dict set fused_bottom_set $name 1 }
  set fused_temporary_flags {}
  foreach net [$fused_block getNets] {
    if {![dict exists $fused_bottom_set [$net getName]] && ![$net isSpecial]} {
      lappend fused_temporary_flags $net
      $net setSpecial
    }
  }
  try {
    if {[llength $fused_bottom]} { read_guides $fused_bottom_guide }
  } finally {
    foreach net $fused_temporary_flags { $net clearSpecial }
  }
  # A stock write_guides emits all guides stored in OpenDB. Remove the first
  # pass's stored guides after its immutable guide file has been saved, so the
  # upper output contains exactly the upper pass like an isolated process.
  foreach net [$fused_block getNets] {
    foreach guide [$net getGuides] { odb::dbGuide_destroy $guide }
  }
  puts "GRT_PASS_RESET legacy"
}
puts "GRT_STAGE reset_pass_ms=[expr {[clock milliseconds] - $fused_started}]"
fused_stage route_upper {
  fused_route_pass $fused_upper $fused_top_min $fused_top_max \
    $fused_upper_guide $::env(REPORTS_DIR)/congestion_upper.rpt
}

set fused_guide $::env(RESULTS_DIR)/route.guide
fused_stage merge_guides {
  exec python3 $fused_script_dir/merge_route_guides.py $fused_guide $fused_bottom_guide $fused_upper_guide
}
if {![info exists ::env(VALIDATE_DIE_GUIDES)] || $::env(VALIDATE_DIE_GUIDES) ni {"" "0"}} {
  set fused_max_cc [expr {[info exists ::env(DIE_GUIDE_MAX_CC_RECTS)] ? $::env(DIE_GUIDE_MAX_CC_RECTS) : 5000}]
  # The router is idle here. Independent read-only checks can share two of
  # its reserved cores; either failure still prevents ODB publication.
  puts [exec python3 $fused_script_dir/validate_die_guides.py $::env(RESULTS_DIR) \
    --def-file $fused_input_def --classification-cache $fused_classification_cache \
    --top 50 --max-cc-rects $fused_max_cc]
}
set fused_started [clock milliseconds]
# Restore exactly the track patterns and net uses saved before routing. Native
# OpenROAD cannot read_db over a populated design, so restoration uses OpenDB
# setters and recreates each grid immediately to retain its original table id.
fused_stage restore_tracks {
  foreach entry $fused_track_patterns {
    lassign $entry layer existed x_patterns y_patterns
    set track [$fused_block findTrackGrid $layer]
    if {$track ne "NULL"} { odb::dbTrackGrid_destroy $track }
    if {$existed} {
      set track [odb::dbTrackGrid_create $fused_block $layer]
      foreach pattern $x_patterns { $track addGridPatternX {*}$pattern }
      foreach pattern $y_patterns { $track addGridPatternY {*}$pattern }
    }
  }
}
fused_stage restore_sigtypes {
  foreach entry $fused_net_sigtypes {
    lassign $entry net sigtype
    if {[$net getSigType] ne $sigtype} { $net setSigType $sigtype }
  }
}
grt::clear_net_routing_layers
set_routing_layers -signal ${fused_bot_min}-${fused_top_max}
fused_stage read_guides {read_guides $fused_guide}
# Capacity adjustments are router settings. Keep the prepared database values
# in the published ODB, as a fresh isolated finalizer does.
foreach entry $fused_layer_adjustments {
  lassign $entry layer adjustment
  $layer setLayerAdjustment $adjustment
}
# The fixed evaluator reads the original SDC and extracts its own parasitics.
# Publishing the routed ODB does not require a separate STA/ref-clock pass.
set fused_output $::env(RESULTS_DIR)/5_1_grt.odb
fused_stage write_db {write_db $fused_output}
set fused_marker $::env(RESULTS_DIR)/.grt_finalize_complete
set fp [open ${fused_marker}.[pid].tmp w]
puts $fp "odb_size=[file size $fused_output]"
close $fp
file rename -force ${fused_marker}.[pid].tmp $fused_marker
puts "GRT_STAGE finalize_ms=[expr {[clock milliseconds] - $fused_started}]"
puts "Fused die-by-die GRT complete: $fused_output"
