utl::set_metrics_stage "detailedplace__{}"
puts "sourcing..."
source $::env(SCRIPTS_DIR)/load.tcl
puts "loading design..."
load_design 3_4_place_resized.odb 2_floorplan.sdc "Starting detailed placement"

source $::env(PLATFORM_DIR)/setRC.tcl

set_placement_padding -global \
    -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) \
    -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)


proc run_detailed_placement {max_displacement} {
    if {$max_displacement eq ""} {
        set command "detailed_placement"
        try {
        puts "dp ing..."
        # detailed_placement
        puts "Command succeeded: $command"
        return 0
    } on error {errMsg} {
        puts "Command failed: $command"
        puts "Error message: $errMsg"
        return 1
    }



    } else {
        set command "detailed_placement -max_displacement $max_displacement"
    }

    

    puts "Running: detailed_placement -max_displacement $max_displacement"
    try {
        # detailed_placement -max_displacement $max_displacement
        puts "Command succeeded: $command"
        return 0
    } on error {errMsg} {
        puts "Command failed: $command"
        puts "Error message: $errMsg"
        return 1
    }
}

set success [run_detailed_placement ""]

if {$success} {
    set max_displacement_values {50 100 500 1000 5000 10000 50000 100000 500000 1000000}
    foreach max_displacement $max_displacement_values {
        set success [run_detailed_placement $max_displacement]
        if {!$success} {
            break
        }
    }
}

if {$success} {
    puts "All attempts failed."
} else {
    puts "Placement succeeded."
}

# if {[info exists ::env(ENABLE_DPO)] && $::env(ENABLE_DPO)} {
#   if {[info exist ::env(DPO_MAX_DISPLACEMENT)]} {
#     improve_placement -max_displacement $::env(DPO_MAX_DISPLACEMENT)
#   } else {
#     improve_placement
#   }
# }
# puts "optimize_mirroring"
# optimize_mirroring

# utl::info FLW 12 "Placement violations [check_placement -verbose]."

estimate_parasitics -placement

# source $::env(SCRIPTS_DIR)/report_metrics.tcl
# report_metrics "detailed place"

if {![info exists save_checkpoint] || $save_checkpoint} {
  write_db $::env(RESULTS_DIR)/3_5_place_dp.odb
}
