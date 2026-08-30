# Route a die-local net subset in an isolated OpenROAD process.
utl::set_metrics_stage "globalroute__pass"
source $::env(SCRIPTS_DIR)/load.tcl
set grt_input_odb [expr {[info exists ::env(GRT_INPUT_ODB)] ? \
  $::env(GRT_INPUT_ODB) : "4_cts.odb"}]
puts "GRT pass input ODB: $grt_input_odb"
load_design $grt_input_odb 4_cts.sdc "Single-pass die routing"

if {[info exist env(FASTROUTE_TCL)]} {
  source $::env(FASTROUTE_TCL)
}

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
    utl::error GRT 321 "Missing net list $path"
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

foreach var {GRT_PASS_NET_LIST GRT_PASS_GUIDE_OUT GRT_PASS_MIN_LAYER GRT_PASS_MAX_LAYER} {
  if {![info exists ::env($var)]} {
    utl::error GRT 322 "Missing environment variable $var"
  }
}

set pass_min $::env(GRT_PASS_MIN_LAYER)
set pass_max $::env(GRT_PASS_MAX_LAYER)
set grt_args [expr {[info exists ::env(GLOBAL_ROUTE_ARGS)] ? $::env(GLOBAL_ROUTE_ARGS) : \
  {-congestion_iterations 2 -congestion_report_iter_step 5 -verbose}}]

configure_die_routing_layers $pass_min $pass_max

set pass_nets [read_net_list $::env(GRT_PASS_NET_LIST)]
apply_layer_ranges $pass_nets $pass_min $pass_max
set queued [add_nets_to_route_from_file $::env(GRT_PASS_NET_LIST)]
puts "Single-pass GRT: queued $queued nets ($pass_min-$pass_max) -> $::env(GRT_PASS_GUIDE_OUT)"

set congestion_report $::env(REPORTS_DIR)/congestion_upper.rpt
set report_fp [open $congestion_report w]
close $report_fp

global_route -guide_file $::env(GRT_PASS_GUIDE_OUT) \
  -congestion_report_file $congestion_report \
  {*}$grt_args
write_guides $::env(GRT_PASS_GUIDE_OUT)
