# Convert routed HBT COVER buffers into one fixed hb_layer via after DRT.
#
# GR phase keeps HBT_* / LS_HBT_* instances as pin targets for global routing.
# After DR, each buffer is replaced at the same location by:
#   1) a single net containing both routed subnet dbWires and all terminals
#   2) one FIXED hb_layer_0 via connecting metal10 to metal11
#
# Invoke after detailed routing and before the final unified DRC check.
# Disabled only when HBT_CONVERT_TO_VIA=0.

proc find_hbt_dr_via { tech } {
  set via_name "hb_layer_0"
  if {[info exists ::env(HBT_DR_VIA_NAME)] && $::env(HBT_DR_VIA_NAME) ne ""} {
    set via_name $::env(HBT_DR_VIA_NAME)
  }
  foreach via [$tech getVias] {
    if {[$via getName] eq $via_name} {
      return $via
    }
  }
  utl::error MOL 501 "HBT DR via '$via_name' not found in tech LEF."
}

proc hbt_subnet_pair_p { bot_name top_name } {
  if {![string match *_BOT $bot_name]} {
    return 0
  }
  if {![string match *_TOP $top_name]} {
    return 0
  }
  set prefix_bot [string range $bot_name 0 end-4]
  set prefix_top [string range $top_name 0 end-4]
  return [expr {$prefix_bot eq $prefix_top}]
}

proc hbt_inst_center { inst } {
  lassign [$inst getOrigin] ox oy
  set master [$inst getMaster]
  set mx [$master getWidth]
  set my [$master getHeight]
  return [list [expr {$ox + $mx / 2}] [expr {$oy + $my / 2}]]
}

proc append_net_wire { dst_net src_net } {
  set src_wire [$src_net getWire]
  if {$src_wire eq "NULL"} {
    return
  }
  set dst_wire [$dst_net getWire]
  if {$dst_wire eq "NULL"} {
    set dst_wire [odb::dbWire_create $dst_net]
  }
  # dbWire::append copies the encoded paths and fixes donor junction ids.
  $dst_wire append $src_wire 0
}

proc merge_hbt_subnets { block bot_net top_net base_name source_net } {
  # Preserve the source-side dbWire as the root of the merged network.  This
  # keeps RC extraction anchored at a real driver/BTerm instead of an empty
  # legacy base net.
  set survivor $source_net
  set base_net [$block findNet $base_name]
  set donors [list $bot_net $top_net]
  if {$base_net ne "NULL"} {
    lappend donors $base_net
  }

  foreach donor $donors {
    if {$donor eq $survivor} {
      continue
    }
    if {![$survivor canMergeNet $donor]} {
      utl::error MOL 504 "Cannot merge HBT subnet [$donor getName] into [$survivor getName]."
    }
    append_net_wire $survivor $donor
    $survivor mergeNet $donor
  }

  if {[$survivor getName] ne $base_name && ![$survivor rename $base_name]} {
    utl::error MOL 506 "Failed to rename merged HBT net to '$base_name'."
  }
  return $survivor
}

proc add_fixed_hbt_via { net tech_via m10 cx cy } {
  set wire [$net getWire]
  set enc [odb::dbWireEncoder]
  if {$wire eq "NULL"} {
    set wire [odb::dbWire_create $net]
    $enc begin $wire
  } else {
    $enc append $wire
  }
  $enc newPath $m10 "FIXED"
  $enc addPoint $cx $cy
  $enc addTechVia $tech_via
  $enc end
}

proc convert_hbt_buffers_to_vias {} {
  if {[info exists ::env(HBT_CONVERT_TO_VIA)] && $::env(HBT_CONVERT_TO_VIA) eq "0"} {
    puts "HBT via conversion disabled (HBT_CONVERT_TO_VIA=0)."
    return
  }

  set block [ord::get_db_block]
  if {$block eq "NULL"} {
    utl::error MOL 502 "convert_hbt_buffers_to_vias: missing dbBlock."
  }
  set tech [ord::get_db_tech]
  set tech_via [find_hbt_dr_via $tech]
  set m10 [$tech findLayer metal10]
  if {$m10 eq "NULL"} {
    utl::error MOL 503 "metal10 not found for HBT via conversion."
  }
  set hbt_insts {}
  foreach inst [$block getInsts] {
    set name [$inst getName]
    if {[regexp {^(HBT_|LS_HBT_)} $name]} {
      lappend hbt_insts $inst
    }
  }

  set converted 0
  set skipped 0
  set report_file ""
  if {[info exists ::env(HBT_MERGE_REPORT)] && $::env(HBT_MERGE_REPORT) ne ""} {
    set report_file $::env(HBT_MERGE_REPORT)
  } elseif {[info exists ::env(RESULTS_DIR)] && $::env(RESULTS_DIR) ne ""} {
    set report_file $::env(RESULTS_DIR)/hbt_net_merge.tsv
  }
  set report_fp ""
  if {$report_file ne ""} {
    set report_fp [open $report_file w]
    puts $report_fp "merged_net\tbot_net\ttop_net\tsource_net\tx\ty\tvia"
  }

  foreach inst $hbt_insts {
    set bot_net "NULL"
    set top_net "NULL"
    foreach iterm [$inst getITerms] {
      set pin_name [[$iterm getMTerm] getName]
      set net [$iterm getNet]
      if {$net eq "NULL"} {
        continue
      }
      if {$pin_name eq "BOT"} {
        set bot_net $net
      } elseif {$pin_name eq "TOP"} {
        set top_net $net
      }
    }
    if {$bot_net eq "NULL" || $top_net eq "NULL"} {
      incr skipped
      continue
    }

    set bot_name [$bot_net getName]
    set top_name [$top_net getName]
    if {![hbt_subnet_pair_p $bot_name $top_name]} {
      puts "WARN: skip HBT [$inst getName] (non _BOT/_TOP pair: $bot_name / $top_name)"
      incr skipped
      continue
    }

    set base_name [string range $bot_name 0 end-4]
    set master_name [[$inst getMaster] getName]
    if {[string match *TOPIN* $master_name]} {
      set source_net $top_net
    } else {
      set source_net $bot_net
    }
    lassign [hbt_inst_center $inst] cx cy
    set source_name [$source_net getName]
    set merged_net [merge_hbt_subnets $block $bot_net $top_net $base_name $source_net]
    odb::dbInst_destroy $inst
    add_fixed_hbt_via $merged_net $tech_via $m10 $cx $cy
    if {$report_fp ne ""} {
      puts $report_fp "$base_name\t$bot_name\t$top_name\t$source_name\t$cx\t$cy\t[$tech_via getName]"
    }
    incr converted
  }

  if {$report_fp ne ""} {
    close $report_fp
  }

  puts "HBT buffer -> merged net + single fixed via: converted=$converted skipped=$skipped via=[$tech_via getName]"
}

convert_hbt_buffers_to_vias
