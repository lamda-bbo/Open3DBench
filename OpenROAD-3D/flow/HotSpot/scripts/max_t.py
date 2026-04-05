#! /usr/bin/python3
import numpy as np
import sys

usage = \
"""
usage: grid_thermal_map.py <flp_file> <grid_temp_file> <filename>.png [--fontsize <size>] (or)
       grid_thermal_map.py <flp_file> <grid_temp_file> <rows> <cols> <filename>.png [--fontsize <size>] (or)
       grid_thermal_map.py <flp_file> <grid_temp_file> <rows> <cols> <min> <max> <filename>.png [--fontsize <size>]

Saves a heat map as a PNG image with the filename <filename>.png

<flp_file>       -- path to the file containing the floorplan (eg: example.flp)
<grid_temp_file> -- path to the grid temperatures file (eg: layer_0.grid.steady)
<rows>           -- no. of rows in the grid (default 64)
<cols>           -- no. of columns in the grid (default 64)
<min>            -- min. temperature of the scale (defaults to min. from <grid_temp_file>)
<max>            -- max. temperature of the scale (defaults to max. from <grid_temp_file>)
--fontsize       -- (optional) default font size for labels and title (default 10)
"""

fontsize = 15

name_fontsize_map = {
    'module1': 12,
    'module2': 14,
    'module3': 8,

}

if '--fontsize' in sys.argv:
    fontsize_index = sys.argv.index('--fontsize')
    try:
        fontsize = int(sys.argv[fontsize_index + 1])
        del sys.argv[fontsize_index:fontsize_index + 2]
    except (IndexError, ValueError):
        print("Error: Invalid value for --fontsize")
        print(usage)
        sys.exit(1)

if len(sys.argv) == 4:
    flp_filename = sys.argv[1]
    temperatures_filename = sys.argv[2]
    output_filename = sys.argv[3]
    rows = 64
    cols = 64
    min_temp = None
    max_temp = None
elif len(sys.argv) == 6:
    flp_filename = sys.argv[1]
    temperatures_filename = sys.argv[2]
    rows = int(sys.argv[3])
    cols = int(sys.argv[4])
    output_filename = sys.argv[5]
    min_temp = None
    max_temp = None
elif len(sys.argv) == 8:
    flp_filename = sys.argv[1]
    temperatures_filename = sys.argv[2]
    rows = int(sys.argv[3])
    cols = int(sys.argv[4])
    min_temp = float(sys.argv[5])
    max_temp = float(sys.argv[6])
    output_filename = sys.argv[7]
else:
    print(usage)
    sys.exit(0)

temps = []
with open(temperatures_filename, "r") as fp:
    for line in fp:
        temps.append(float(line.strip().split()[1]))

temps = np.reshape(temps, (rows, cols))

print(f"Maximum Temperature in {output_filename} = {np.max(temps)}")