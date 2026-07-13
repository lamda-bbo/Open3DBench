# Die-by-die global routing: each pass only sees the current die metal layers.
utl::set_metrics_stage "globalroute__{}"
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc "Starting die-by-die global routing"

if {[info exist env(FASTROUTE_TCL)]} {
  source $::env(FASTROUTE_TCL)
}

set bot_min [expr {[info exists ::env(BOTTOM_DIE_MIN_LAYER)] ? $::env(BOTTOM_DIE_MIN_LAYER) : "metal2"}]
set bot_max [expr {[info exists ::env(BOTTOM_DIE_MAX_LAYER)] ? $::env(BOTTOM_DIE_MAX_LAYER) : "metal10"}]
set top_min [expr {[info exists ::env(UPPER_DIE_MIN_LAYER)] ? $::env(UPPER_DIE_MIN_LAYER) : "metal11"}]
set top_max [expr {[info exists ::env(UPPER_DIE_MAX_LAYER)] ? $::env(UPPER_DIE_MAX_LAYER) : "metal20"}]

set list_dir $::env(RESULTS_DIR)/die_net_lists
set def_file $::env(RESULTS_DIR)/4_1_cts.def
set export_py $::env(SCRIPTS_DIR)/../scripts_3D/export_die_net_lists.py
exec python3 $export_py $def_file $list_dir

proc configure_die_routing_layers {min_layer max_layer} {
  set adj 0.5
  if {[info exists ::env(GLOBAL_ROUTING_LAYER_ADJUSTMENT)]} {
    set adj $::env(GLOBAL_ROUTING_LAYER_ADJUSTMENT)
  }
  set_global_routing_layer_adjustment ${min_layer}-${max_layer} $adj
  set_routing_layers -signal ${min_layer}-${max_layer}
  if {[info exist env(MACRO_EXTENSION)]} {
    set_macro_extension $env(MACRO_EXTENSION)
  }
  puts "Die GRT layer window: ${min_layer}-${max_layer}"
}

proc read_net_list {path} {
  if {![file exists $path]} {
    utl::error GRT 320 "Missing net list $path"
  }
  set fp [open $path r]
  set content [read $fp]
  close $fp
  set nets {}
  foreach line [split $content "\n"] {
    set net [string trim $line]
    if {$net ne ""} {
      lappend nets $net
    }
  }
  return $nets
}

proc add_nets_to_route_from_file {path} {
  set block [ord::get_db_block]
  set count 0
  foreach net_name [read_net_list $path] {
    set net [$block findNet $net_name]
    if {$net ne "NULL"} {
      grt::add_net_to_route $net
      incr count
    }
  }
  return $count
}

proc apply_layer_ranges {net_names min_layer max_layer} {
  if {[info commands set_net_routing_layers] eq ""} {
    puts "WARN: set_net_routing_layers unavailable; per-net layer clamp skipped."
    return
  }
  set block [ord::get_db_block]
  foreach net_name $net_names {
    set net [$block findNet $net_name]
    if {$net ne "NULL"} {
      set_net_routing_layers $net_name $min_layer $max_layer
    }
  }
}

proc openroad_exe {} {
  if {[info exists ::env(OPENROAD_EXE)]} {
    return $::env(OPENROAD_EXE)
  }
  return "openroad"
}

proc route_pass_subprocess {net_list_path guide_out min_layer max_layer pass_label} {
  set ::env(GRT_PASS_NET_LIST) $net_list_path
  set ::env(GRT_PASS_GUIDE_OUT) $guide_out
  set ::env(GRT_PASS_MIN_LAYER) $min_layer
  set ::env(GRT_PASS_MAX_LAYER) $max_layer
  set log_file $::env(LOG_DIR)/grt_pass_${pass_label}.log
  set pass_script $::env(SCRIPTS_DIR)/../scripts_3D/global_route_single_pass.tcl
  puts "Die-isolated subprocess pass $pass_label ($min_layer-$max_layer) -> $guide_out"
  exec [openroad_exe] -exit -no_init $pass_script > $log_file 2>&1
}

proc metal_layer_index {layer_name} {
  if {![regexp {(?i)^metal([0-9]+)$} $layer_name -> idx]} {
    utl::error GRT 324 "Invalid metal layer name $layer_name"
  }
  return $idx
}

proc clamp_pass_guide_file_if_enabled {guide_path min_layer max_layer} {
  if {[info exists ::env(CLAMP_PASS_GUIDE_LAYERS)]} {
    if {$::env(CLAMP_PASS_GUIDE_LAYERS) eq "" || $::env(CLAMP_PASS_GUIDE_LAYERS) eq "0"} {
      puts "Skipping pass guide clamp on $guide_path (CLAMP_PASS_GUIDE_LAYERS=0)"
      return
    }
  }
  set clamp_py $::env(SCRIPTS_DIR)/../scripts_3D/clamp_pass_guide_layers.py
  set min_n [metal_layer_index $min_layer]
  set max_n [metal_layer_index $max_layer]
  puts "Clamping $guide_path to ${min_layer}-${max_layer}"
  exec python3 $clamp_py $guide_path $min_n $max_n $guide_path
}

proc inject_hbt_cover_guides_if_enabled {guide_path def_path} {
  if {[info exists ::env(INJECT_HBT_COVER_GUIDES)]} {
    if {$::env(INJECT_HBT_COVER_GUIDES) eq "" || $::env(INJECT_HBT_COVER_GUIDES) eq "0"} {
      return
    }
  }
  set inject_py $::env(SCRIPTS_DIR)/../scripts_3D/inject_hbt_cover_guides.py
  puts "Injecting HBT pin cover guides into $guide_path"
  exec python3 $inject_py $guide_path $def_path $guide_path
}

proc merge_route_guide_files {output_guide guide_inputs} {
  set merge_py $::env(SCRIPTS_DIR)/../scripts_3D/merge_route_guides.py
  set cmd [linsert $guide_inputs 0 $merge_py $output_guide]
  puts "Merging [expr {[llength $guide_inputs]}] guide files -> $output_guide"
  exec python3 {*}$cmd
}

proc scrub_merged_guides_if_enabled {guide_path def_path} {
  if {![info exists ::env(SCRUB_2D_NET_GUIDES)]} {
    return
  }
  if {$::env(SCRUB_2D_NET_GUIDES) eq "" || $::env(SCRUB_2D_NET_GUIDES) eq "0"} {
    return
  }
  set scrub_py $::env(SCRIPTS_DIR)/../scripts_3D/scrub_2d_net_guide_layers.py
  puts "Scrubbing illegal cross-die layers from $guide_path"
  exec python3 $scrub_py $guide_path $def_path $guide_path
}


proc validate_merged_guides_if_enabled {results_dir} {
  if {[info exists ::env(VALIDATE_DIE_GUIDES)]} {
    if {$::env(VALIDATE_DIE_GUIDES) eq "" || $::env(VALIDATE_DIE_GUIDES) eq "0"} {
      puts "Skipping merged guide validation (VALIDATE_DIE_GUIDES=0)"
      return
    }
  }
  set diag_py $::env(SCRIPTS_DIR)/../scripts_3D/diagnose_guide_connectivity.py
  set max_cc 5000
  if {[info exists ::env(DIE_GUIDE_MAX_CC_RECTS)]} {
    set max_cc $::env(DIE_GUIDE_MAX_CC_RECTS)
  }
  puts "Validating merged HBT/die guides in $results_dir"
  exec python3 $diag_py $results_dir     --strict --top 50 --max-cc-rects $max_cc
}

proc finalize_merged_guides {} {
  set script $::env(SCRIPTS_DIR)/../scripts_3D/finalize_die_by_die_grt.tcl
  set log_file $::env(LOG_DIR)/grt_finalize.log
  puts "Loading merged guides into ODB via subprocess"
  exec [openroad_exe] -exit -no_init $script > $log_file 2>&1
}

set grt_args [expr {[info exists ::env(GLOBAL_ROUTE_ARGS)] ? $::env(GLOBAL_ROUTE_ARGS) : \
  {-congestion_iterations 2 -congestion_report_iter_step 5 -verbose}}]

set bottom_nets [read_net_list $list_dir/bottom_2d.txt]
set upper_nets [read_net_list $list_dir/upper_2d.txt]

puts "Die-by-die GRT: bottom=[llength $bottom_nets] upper=[llength $upper_nets]"
puts "  bottom layers: $bot_min-$bot_max"
puts "  upper layers:  $top_min-$top_max"

# --- Pass 1: bottom die (only bottom metal visible) ---
configure_die_routing_layers $bot_min $bot_max
apply_layer_ranges $bottom_nets $bot_min $bot_max
set bottom_added [add_nets_to_route_from_file $list_dir/bottom_2d.txt]
puts "Pass1: queued $bottom_added bottom nets for GRT"
global_route -guide_file $::env(RESULTS_DIR)/route_bottom.guide \
  -congestion_report_file $::env(REPORTS_DIR)/congestion_bottom.rpt \
  {*}$grt_args
clamp_pass_guide_file_if_enabled $::env(RESULTS_DIR)/route_bottom.guide metal1 $bot_max

# --- Pass 2: upper die (isolated subprocess, only upper metal visible) ---
route_pass_subprocess $list_dir/upper_2d.txt \
  $::env(RESULTS_DIR)/route_upper.guide $top_min $top_max upper
clamp_pass_guide_file_if_enabled $::env(RESULTS_DIR)/route_upper.guide $top_min $top_max

set merged_guide $::env(RESULTS_DIR)/route.guide
merge_route_guide_files $merged_guide [list \
  $::env(RESULTS_DIR)/route_bottom.guide \
  $::env(RESULTS_DIR)/route_upper.guide \
]
inject_hbt_cover_guides_if_enabled $merged_guide $def_file
scrub_merged_guides_if_enabled $merged_guide $def_file
validate_merged_guides_if_enabled $::env(RESULTS_DIR)
finalize_merged_guides
