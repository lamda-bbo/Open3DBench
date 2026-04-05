#!/usr/bin/env bash

# Remove results from previous simulations
rm -f *.init
rm -f outputs/*

# Create outputs directory if it doesn't exist
mkdir outputs

../../hotspot -c test.config -p test.ptrace -grid_layer_file test.lcf -materials_file test.materials -model_type grid -detailed_3D on -steady_file outputs/test.steady -grid_steady_file outputs/test.grid.steady

# Copy steady-state results over to initial temperatures
cp outputs/test.steady test.init

# Transient simulation
../../hotspot -c test.config -p test.ptrace -grid_layer_file test.lcf -materials_file test.materials -model_type grid -detailed_3D on -o outputs/test.ttrace -grid_transient_file outputs/test.grid.ttrace

# Visualize Heat Map of Layer 0 with Perl and with Python script
../../scripts/split_grid_steady.py outputs/test.grid.steady 6 64 64
../../scripts/temp_tran.py -f outputs/test.grid.steady outputs/test_layer2.grid.steady outputs/test_layer0.grid.steady
../../scripts/grid_thermal_map.py floorplan2.flp outputs/test_layer2.grid.steady 64 64 outputs/core_thermal.png
../../scripts/grid_thermal_map.pl floorplan2.flp outputs/test_layer2.grid.steady 64 64 > outputs/core_thermal.svg

../../scripts/grid_thermal_map.py floorplan1.flp outputs/test_layer0.grid.steady 64 64 outputs/cache_thermal.png
../../scripts/grid_thermal_map.pl floorplan1.flp outputs/test_layer0.grid.steady 64 64 > outputs/cache_thermal.svg
