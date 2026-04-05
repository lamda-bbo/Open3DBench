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

write_db $::env(RESULTS_DIR)/3D_placement.odb
write_def $::env(RESULTS_DIR)/4_1_cts.def
save_image -resolution 1 $::env(RESULTS_DIR)/3d_origin.webp 