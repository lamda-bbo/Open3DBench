read_lef $::env(TECH_LEF)
read_lef $::env(SC_LEF)
if {[info exist ::env(ADDITIONAL_LEFS)]} {
foreach lef $::env(ADDITIONAL_LEFS) {
    read_lef $lef
}
}
foreach lib_file $env(LIB_FILES) {
  read_lib $lib_file
}
read_def $::env(INPUT_DEF)
read_sdc $::env(RESULTS_DIR)/1_synth.sdc

source evaluation_pack/macro_placement_dmp/$::env(INPUT_DESIGN_NAME).macro

lassign $::env(MACRO_PLACE_HALO) halo_x halo_y
lassign $::env(MACRO_PLACE_CHANNEL) channel_x channel_y
set halo_max [expr max($halo_x, $halo_y)]
set channel_max [expr max($channel_x, $channel_y)]
set blockage_width [expr max($halo_max, $channel_max/2)]

# source $::env(SCRIPTS_DIR)/placement_blockages.tcl
# block_channels $blockage_width 

write_db $::env(RESULTS_DIR)/2_4_floorplan_macro.odb
# write_sdc $::env(RESULTS_DIR)/2_floorplan.sdc
# save_image -resolution 1 $::env(RESULTS_DIR)/2d_origin.webp 