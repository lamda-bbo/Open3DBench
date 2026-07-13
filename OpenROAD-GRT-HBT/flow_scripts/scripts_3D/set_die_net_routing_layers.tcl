# Assign per-net GRT layer ranges for whole-chip die-aware global routing.
# Used when PRE_GLOBAL_ROUTE is set (mol_stack / legacy flows). Die-by-die flow
# uses global_route_die_by_die.tcl instead.

if {[info commands set_net_routing_layers] eq ""} {
  puts "WARN: set_net_routing_layers is unavailable; rebuild OpenROAD with the Open3DBench GRT patch."
} else {

proc die_layer_range { env_min env_max default_min default_max } {
  if {[info exists ::env($env_min)]} { set min $::env($env_min) } else { set min $default_min }
  if {[info exists ::env($env_max)]} { set max $::env($env_max) } else { set max $default_max }
  return [list $min $max]
}

lassign [die_layer_range BOTTOM_DIE_MIN_LAYER BOTTOM_DIE_MAX_LAYER metal2 metal10] bot_min bot_max
lassign [die_layer_range UPPER_DIE_MIN_LAYER UPPER_DIE_MAX_LAYER metal11 metal20] top_min top_max

# 2D net: all pins on the same die -> must not cross die (per-die metal range).
# 3D net: pins on different dies -> may cross die (global metal range).
proc name_on_die { name } {
  if {[string match *_bottom $name] || [string match HBT_BOTIN_* $name]} {
    return bottom
  }
  if {[string match *_upper $name] || [string match HBT_TOPIN_* $name]} {
    return upper
  }
  return unknown
}

proc classify_net_die { inst_names cell_names } {
  set has_bottom 0
  set has_upper 0
  foreach inst $inst_names cell $cell_names {
    set die [name_on_die $inst]
    if {$die eq "unknown"} {
      set die [name_on_die $cell]
    }
    if {$die eq "bottom"} {
      set has_bottom 1
    }
    if {$die eq "upper"} {
      set has_upper 1
    }
  }

  if {$has_bottom && $has_upper} {
    return 3d
  }
  if {$has_bottom} {
    return 2d_bottom
  }
  if {$has_upper} {
    return 2d_upper
  }
  return unknown
}

set block [ord::get_db_block]
if {$block eq "NULL"} {
  utl::error GRT 311 "set_die_net_routing_layers: missing dbBlock."
}

set global_min $::env(MIN_ROUTING_LAYER)
set global_max $::env(MAX_ROUTING_LAYER)

set count_2d_bottom 0
set count_2d_upper 0
set count_3d 0
set skipped_count 0

foreach net [$block getNets] {
  if {[$net isSpecial]} { continue }
  set sig_type [$net getSigType]
  if {$sig_type ne "SIGNAL"} { continue }

  set inst_names {}
  set cell_names {}
  foreach iterm [$net getITerms] {
    set inst_obj [$iterm getInst]
    lappend inst_names [$inst_obj getName]
    lappend cell_names [[$inst_obj getMaster] getName]
  }

  set net_name [$net getName]
  set die [classify_net_die $inst_names $cell_names]
  if {[string match *_BOT $net_name]} {
    set die 2d_bottom
  } elseif {[string match *_TOP $net_name]} {
    set die 2d_upper
  }
  switch -- $die {
    2d_bottom {
      set_net_routing_layers [$net getName] $bot_min $bot_max
      incr count_2d_bottom
    }
    2d_upper {
      set_net_routing_layers [$net getName] $top_min $top_max
      incr count_2d_upper
    }
    3d {
      set_net_routing_layers [$net getName] $global_min $global_max
      incr count_3d
    }
    default {
      incr skipped_count
    }
  }
}

puts "Die-aware GRT: 2D_bottom=$count_2d_bottom 2D_upper=$count_2d_upper 3D=$count_3d skipped=$skipped_count"
puts "  2D bottom layers: $bot_min-$bot_max"
puts "  2D upper layers:  $top_min-$top_max"
puts "  3D global layers: $global_min-$global_max"

}
