#! /usr/bin/python3

import matplotlib.pyplot as plt
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

fig, axs = plt.subplots(1)
total_width = -np.inf
total_length = -np.inf
with open(flp_filename, "r") as fp:
    for line in fp:

        # Ignore blank lines and comments
        if line == "\n" or line[0] == '#':
            continue

        parts = line.split()
        name = parts[0]
        width = float(parts[1])
        length = float(parts[2])
        x = float(parts[3])
        y = float(parts[4])

        rectangle = plt.Rectangle((x, y), width, length, fc="none", ec="black")
        axs.add_patch(rectangle)


        current_fontsize = name_fontsize_map.get(name, fontsize)
        plt.text(x, y, name, fontsize=5)

        total_width = max(total_width, x + width)
        total_length = max(total_length, y + length)

temps = []
with open(temperatures_filename, "r") as fp:
    for line in fp:
        temps.append(float(line.strip().split()[1]))

temps = np.reshape(temps, (rows, cols))

im = axs.imshow(temps, cmap='hot_r', extent=(0, total_width, 0, total_length))

if min_temp is None and max_temp is None:
    im.set_clim(np.min(temps), np.max(temps))
else:
    im.set_clim(min_temp, max_temp)

cbar = fig.colorbar(im, ax=axs)
cbar.ax.tick_params(labelsize=fontsize)

axs.set_title(f"Heat Map\nMaximum Temperature = {np.max(temps)}", fontsize=fontsize)

print(f"Maximum Temperature = {np.max(temps)}")

# axs.set_xticks([n for n in np.linspace(0, total_width, 5)])
# axs.set_xticklabels([f"{n*(10**3):.2f}" for n in np.linspace(0, total_width, 5)], fontsize=fontsize)
# axs.set_xlabel("Horizontal Position (mm)", fontsize=fontsize)
axs.set_xticks([])
axs.set_yticks([])

# axs.set_yticks([n for n in np.linspace(0, total_length, 5)])
# axs.set_yticklabels([f"{n*(10**3):.2f}" for n in np.linspace(0, total_length, 5)], fontsize=fontsize)
# axs.set_ylabel("Vertical Position (mm)", fontsize=fontsize)

plt.axis('scaled')
plt.savefig(output_filename)
