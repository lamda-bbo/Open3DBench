# Load merged die-by-die guides into ODB (stock OpenROAD fallback).
utl::set_metrics_stage "globalroute__finalize"
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc "Finalize die-by-die global routing"

set guide_file $::env(RESULTS_DIR)/route.guide
if {![file exists $guide_file]} {
  utl::error GRT 323 "Missing merged guide file $guide_file"
}

read_guides $guide_file

if {[info exist env(IDEAL_CLOCK)]} {
  set_ideal_network [all_clocks]
} else {
  set_propagated_clock [all_clocks]
}

if {[catch {estimate_parasitics -global_routing} err]} {
  puts "WARN: estimate_parasitics after read_guides failed: $err"
}

source [file join $::env(SCRIPTS_DIR) "write_ref_sdc.tcl"]
write_db $::env(RESULTS_DIR)/5_1_grt.odb
