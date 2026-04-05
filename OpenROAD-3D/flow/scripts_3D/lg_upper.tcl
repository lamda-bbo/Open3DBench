set all_lefs [concat $env(TECH_LEF) $env(SC_LEF) $env(ADDITIONAL_LEFS)]
foreach lef_file $all_lefs {
    read_lef $lef_file
}
read_def $env(RESULTS_DIR)/upper.def
save_image -resolution 1 $::env(RESULTS_DIR)/upper_before_lg.webp 
detailed_placement -max_displacement 300
save_image -resolution 1 $::env(RESULTS_DIR)/upper_legalized.webp 
write_def $env(RESULTS_DIR)/upper_legalized.def