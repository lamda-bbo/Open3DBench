# Add explicit HBT resistance and capacitance to the OpenRCX network.
# OpenRCX may fold a via into a neighboring metal segment, so extraction uses
# a unique temporary resistance marker that is replaced after extraction.

proc hbt_rc_value { env_name default_value } {
  if {[info exists ::env($env_name)] && $::env($env_name) ne ""} {
    set value $::env($env_name)
  } else {
    set value $default_value
  }
  if {![string is double -strict $value] || $value <= 0.0} {
    utl::error MOL 601 "$env_name must be a positive number, found '$value'."
  }
  return [expr {double($value)}]
}

proc hbt_extraction_marker {} {
  return [hbt_rc_value HBT_EXTRACTION_MARKER_OHM 10000.1234567]
}

proc prepare_hbt_parasitic_extraction {} {
  set marker [hbt_extraction_marker]
  set tech [[ord::get_db] getTech]
  set hbt_layer [$tech findLayer hb_layer]
  set hbt_via [$tech findVia hb_layer_0]
  if {$hbt_layer eq "NULL" || $hbt_via eq "NULL"} {
    utl::error MOL 602 "hb_layer or hb_layer_0 is missing before HBT RC extraction."
  }
  $hbt_layer setResistance $marker
  $hbt_via setResistance $marker
  puts "HBT RC extraction marker: resistance=$marker ohm"
}

proc find_hbt_rc_segment { net x y marker } {
  set coordinate_matches {}
  set marker_matches {}
  set threshold [expr {$marker * 0.9}]

  foreach rseg [$net getRSegs] {
    set resistance [$rseg getResistance 0]
    if {$resistance < $threshold} {
      continue
    }
    lappend marker_matches $rseg
    lassign [$rseg getCoords] rx ry
    if {$rx == $x && $ry == $y} {
      lappend coordinate_matches $rseg
    }
  }

  if {[llength $coordinate_matches] == 1} {
    return [lindex $coordinate_matches 0]
  }
  if {[llength $coordinate_matches] > 1} {
    utl::error MOL 603 "Multiple HBT RC segments found on [$net getName] at ($x, $y)."
  }
  if {[llength $marker_matches] == 1} {
    return [lindex $marker_matches 0]
  }
  utl::error MOL 604 "Cannot uniquely locate the HBT RC marker segment on [$net getName] at ($x, $y); found [llength $marker_matches]."
}

proc add_hbt_parasitics {} {
  set merge_report $::env(RESULTS_DIR)/hbt_net_merge.tsv
  if {[info exists ::env(HBT_MERGE_REPORT)] && $::env(HBT_MERGE_REPORT) ne ""} {
    set merge_report $::env(HBT_MERGE_REPORT)
  }
  if {![file exists $merge_report]} {
    puts "HBT RC injection skipped: no merge report at $merge_report"
    return
  }

  set resistance [hbt_rc_value HBT_RESISTANCE_OHM 3.0]
  set capacitance [hbt_rc_value HBT_CAPACITANCE_FF 0.6]
  set marker [hbt_extraction_marker]
  set endpoint_cap [expr {$capacitance / 2.0}]
  set expected_via "hb_layer_0"
  if {[info exists ::env(HBT_DR_VIA_NAME)] && $::env(HBT_DR_VIA_NAME) ne ""} {
    set expected_via $::env(HBT_DR_VIA_NAME)
  }
  set block [ord::get_db_block]
  if {$block eq "NULL"} {
    utl::error MOL 610 "add_hbt_parasitics: missing dbBlock."
  }
  set corner_count [$block getCornerCount]
  if {$corner_count < 1} {
    set corner_count 1
  }

  set detail_report $::env(REPORTS_DIR)/hbt_parasitics.tsv
  set out [open $detail_report w]
  puts $out "net\tx\ty\tresistance_ohm\tcapacitance_ff\tsource_node\ttarget_node"

  set fp [open $merge_report r]
  set line_number 0
  set injected 0
  while {[gets $fp line] >= 0} {
    incr line_number
    if {$line_number == 1 || [string trim $line] eq ""} {
      continue
    }
    set fields [split $line "\t"]
    if {[llength $fields] < 7} {
      close $fp
      close $out
      utl::error MOL 611 "Malformed HBT merge report line $line_number in $merge_report."
    }
    set net_name [lindex $fields 0]
    set x [lindex $fields 4]
    set y [lindex $fields 5]
    set via_name [lindex $fields 6]
    if {$via_name ne $expected_via} {
      close $fp
      close $out
      utl::error MOL 612 "Unexpected HBT via '$via_name' for $net_name."
    }

    set net [$block findNet $net_name]
    if {$net eq "NULL"} {
      close $fp
      close $out
      utl::error MOL 613 "Merged HBT net '$net_name' is missing during RC injection."
    }
    set rseg [find_hbt_rc_segment $net $x $y $marker]
    set source_node [$rseg getSourceCapNode]
    set target_node [$rseg getTargetCapNode]
    if {$source_node eq "NULL" || $target_node eq "NULL"} {
      close $fp
      close $out
      utl::error MOL 614 "HBT RC segment on '$net_name' has a missing cap node."
    }

    for {set corner 0} {$corner < $corner_count} {incr corner} {
      set extracted_resistance [$rseg getResistance $corner]
      set corrected_resistance [expr {$extracted_resistance - $marker + $resistance}]
      if {$corrected_resistance <= 0.0} {
        close $fp
        close $out
        utl::error MOL 615 "Invalid corrected HBT segment resistance on '$net_name': $corrected_resistance."
      }
      $rseg setResistance $corrected_resistance $corner
      if {$source_node eq $target_node} {
        $source_node addCapacitance $capacitance $corner
      } else {
        $source_node addCapacitance $endpoint_cap $corner
        $target_node addCapacitance $endpoint_cap $corner
      }
    }
    puts $out "$net_name\t$x\t$y\t[$rseg getResistance 0]\t$capacitance\t[$source_node getNode]\t[$target_node getNode]"
    incr injected
  }
  close $fp
  close $out

  puts "HBT RC injection: count=$injected resistance=$resistance ohm capacitance=$capacitance fF report=$detail_report"
}
