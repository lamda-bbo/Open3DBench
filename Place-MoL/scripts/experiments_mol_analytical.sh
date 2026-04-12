#!/bin/bash

set -e
cd "$(dirname "$0")/.."

cd DREAMPlace
mkdir -p build
cd build
cmake ..
make -j 8
make -j 8 install
cd ../../

design_names=(
    "ariane133"
    "ariane136"
    "bp"
    "bp_multi"
)

for design in "${design_names[@]}"; do
    echo "Processing design: $design"
    python src/place_3d/main.py --benchmark="$design" --seed=3 --config_file=or_3D.json
done

python src/place_3d/main.py --benchmark=bp_quad --seed=3 --config_file=or_3D_bp_quad.json
python src/place_3d/main.py --benchmark=swerv_wrapper --seed=3 --config_file=or_3D_swerv.json
python src/place_3d/main.py --benchmark=bp_be --seed=3 --config_file=or_3D_bp_be.json
python src/place_3d/main.py --benchmark=bp_fe --seed=3 --config_file=or_3D_bp_fe.json
