utl::set_metrics_stage "finish__{}"
source $::env(SCRIPTS_DIR)/load.tcl
load_design 6_1_fill.odb 6_1_fill.sdc "Starting final report"

if {[info exist env(IDEAL_CLOCK)]} {
  set_ideal_network [all_clocks]
  set_false_path -through rst_ni
  set_false_path -through reset_i
  set_false_path -through reset_l
  set_false_path -through p_clk_async_reset_i
} else {
  set_propagated_clock [all_clocks]
}

# Ensure all OR created (rsz/cts) instances are connected
global_connect

# Delete routing obstructions for final DEF
source $::env(SCRIPTS_DIR)/deleteRoutingObstructions.tcl
deleteRoutingObstructions

write_db $::env(RESULTS_DIR)/6_final.odb
write_def $::env(RESULTS_DIR)/6_final.def
write_verilog $::env(RESULTS_DIR)/6_final.v

# Run extraction and STA
if {[info exist ::env(RCX_RULES)]} {

  # Set RC corner for RCX
  # Set in config.mk
  if {[info exist ::env(RCX_RC_CORNER)]} {
    set rc_corner $::env(RCX_RC_CORNER)
  }

  # RCX section
  define_process_corner -ext_model_index 0 X
  set extract_args [list -ext_model_file $::env(RCX_RULES)]
  set hbt_merge_report $::env(RESULTS_DIR)/hbt_net_merge.tsv
  if {[info exists ::env(HBT_MERGE_REPORT)] && $::env(HBT_MERGE_REPORT) ne ""} {
    set hbt_merge_report $::env(HBT_MERGE_REPORT)
  }
  if {[file exists $hbt_merge_report]} {
    source $::env(SCRIPTS_DIR)/add_hbt_parasitics.tcl
    prepare_hbt_parasitic_extraction
    lappend extract_args -no_merge_via_res
  }
  extract_parasitics {*}$extract_args

  if {[file exists $hbt_merge_report]} {
    add_hbt_parasitics
  }

  # Write Spef
  write_spef $::env(RESULTS_DIR)/6_final.spef
  file delete $::env(DESIGN_NAME).totCap

  # Read Spef for OpenSTA
  read_spef $::env(RESULTS_DIR)/6_final.spef

  # Static IR drop analysis
  # if {[info exist ::env(PWR_NETS_VOLTAGES)]} {
  #   dict for {pwrNetName pwrNetVoltage}  {*}$::env(PWR_NETS_VOLTAGES) {
  #       set_pdnsim_net_voltage -net ${pwrNetName} -voltage ${pwrNetVoltage}
  #       analyze_power_grid -net ${pwrNetName} \
  #           -error_file $::env(REPORTS_DIR)/${pwrNetName}.rpt
  #   }
  # } else {
  #   puts "IR drop analysis for power nets is skipped because PWR_NETS_VOLTAGES is undefined"
  # }
  # if {[info exist ::env(GND_NETS_VOLTAGES)]} {
  #   dict for {gndNetName gndNetVoltage}  {*}$::env(GND_NETS_VOLTAGES) {
  #       set_pdnsim_net_voltage -net ${gndNetName} -voltage ${gndNetVoltage}
  #       analyze_power_grid -net ${gndNetName} \
  #           -error_file $::env(REPORTS_DIR)/${gndNetName}.rpt
  #   }
  # } else {
  #   puts "IR drop analysis for ground nets is skipped because GND_NETS_VOLTAGES is undefined"
  # }

} else {
  puts "OpenRCX is not enabled for this platform."
}

source $::env(SCRIPTS_DIR)/report_metrics.tcl
report_metrics "finish"

# Save a final image only when OpenROAD exposes the GUI command.
if {[info commands gui::show] ne "" && [llength [info procs save_image]] > 0} {
    gui::show "source $::env(SCRIPTS_DIR)/save_images.tcl" false
}
