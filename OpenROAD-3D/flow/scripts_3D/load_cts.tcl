set all_lefs [concat $env(TECH_LEF) $env(SC_LEF) $env(ADDITIONAL_LEFS)]
foreach lef_file $all_lefs {
    read_lef $lef_file
}
read_def $env(RESULTS_DIR)/4_1_cts.def
write_db $env(RESULTS_DIR)/my_cts.odb

