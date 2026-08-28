# Load merged die-by-die guides into ODB (stock OpenROAD fallback).
utl::set_metrics_stage "globalroute__finalize"
source $::env(SCRIPTS_DIR)/load.tcl
set grt_input_odb [expr {[info exists ::env(GRT_INPUT_ODB)] ? \
  $::env(GRT_INPUT_ODB) : "4_cts.odb"}]
puts "GRT finalizer input ODB: $grt_input_odb"
load_design $grt_input_odb 4_cts.sdc "Finalize die-by-die global routing"

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

set output_odb $::env(RESULTS_DIR)/5_1_grt.odb
set success_marker $::env(RESULTS_DIR)/.grt_finalize_complete
write_db $output_odb

# Publish completion only after the ODB has been fully written.  The parent
# process uses this marker to distinguish a valid child result from a real
# finalization failure.
set marker_tmp ${success_marker}.[pid].tmp
set marker_fp [open $marker_tmp w]
puts $marker_fp "odb_size=[file size $output_odb]"
close $marker_fp
file rename -force $marker_tmp $success_marker
puts "Die-by-die GRT finalization complete: $output_odb"
