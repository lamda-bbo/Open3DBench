set all_lefs [concat $env(TECH_LEF) $env(SC_LEF) $env(ADDITIONAL_LEFS)]
foreach lef_file $all_lefs {
    read_lef $lef_file
}
read_def $env(RESULTS_DIR)/bottom.def
detailed_placement -max_displacement 300
write_def $env(RESULTS_DIR)/bottom_legalized.def
