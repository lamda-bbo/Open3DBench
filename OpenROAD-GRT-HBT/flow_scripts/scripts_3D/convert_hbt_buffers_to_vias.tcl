# Convert placed HBT COVER buffers into fixed hb_layer routing vias before DRT.
#
# GR phase keeps HBT_* / LS_HBT_* instances as pin targets for global routing.
# DR phase replaces each buffer with hb_layer_0 at the same location:
#   1) copy {net}_TOP guides onto {net}_BOT
#   2) merge {net}_TOP into {net}_BOT
#   3) destroy the HBT instance
#   4) insert a FIXED hb_layer via at the buffer center on the merged net
#
# Enabled when MOL_HBT=1 (Makefile sets PRE_DETAIL_ROUTE_TCL).
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

proc copy_guides_to_net { from_net to_net } {
  # dbGuide has no setNet; recreate guides on the survivor net before mergeNet
  # destroys the donor net (and its guides).
  set copies {}
  foreach guide [$from_net getGuides] {
    set box [$guide getBox]
    lappend copies [list \
      [$guide getLayer] \
      [$guide getViaLayer] \
      [$box xMin] [$box yMin] [$box xMax] [$box yMax] \
      [$guide isCongested]]
  }
  foreach item $copies {
    lassign $item layer via_layer x1 y1 x2 y2 congested
    set rect [odb::Rect]
    $rect init $x1 $y1 $x2 $y2
    if {$via_layer eq "NULL"} {
      odb::dbGuide_create $to_net $layer NULL $rect $congested
    } else {
      odb::dbGuide_create $to_net $layer $via_layer $rect $congested
    }
  }
}

proc add_fixed_hbt_via { net tech_via m10 cx cy } {
  set existing_wire [$net getWire]
  if {$existing_wire ne "NULL"} {
    odb::dbWire_destroy $existing_wire
  }
  set wire [odb::dbWire_create $net]
  set enc [odb::dbWireEncoder]
  $enc begin $wire
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

    lassign [hbt_inst_center $inst] cx cy
    copy_guides_to_net $top_net $bot_net
    $bot_net mergeNet $top_net
    odb::dbInst_destroy $inst
    add_fixed_hbt_via $bot_net $tech_via $m10 $cx $cy
    incr converted
  }

  puts "HBT buffer -> via: converted=$converted skipped=$skipped via=[$tech_via getName]"
}

convert_hbt_buffers_to_vias
