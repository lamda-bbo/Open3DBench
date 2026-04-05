set def_version $env(DEF_VERSION)

set all_lefs [concat $env(TECH_LEF) $env(SC_LEF) $env(ADDITIONAL_LEFS)]
foreach lef_file $all_lefs {
    read_lef $lef_file
}
read_def $env(DEF_INPUT)
write_db $env(RESULTS_DIR)/3D_out.odb
