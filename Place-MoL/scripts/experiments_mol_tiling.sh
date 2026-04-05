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
    # python src/place_3d/main.py --benchmark=$design --seed=3
    bash scripts/run_mol_tiling.sh $design 3 or_3D.json
done

# python src/place_3d/main.py --benchmark=bp_quad --seed=3 --config_file=or_3D_bp_quad.json
# python src/place_3d/main.py --benchmark=swerv_wrapper --seed=3 --config_file=or_3D_swerv.json
bash scripts/run_mol_tiling.sh bp_quad 3 or_3D_bp_quad.json
bash scripts/run_mol_tiling.sh swerv_wrapper 3 or_3D_swerv.json
bash scripts/run_mol_tiling.sh bp_be 3 or_3D_bp_be.json
bash scripts/run_mol_tiling.sh bp_fe 3 or_3D_bp_fe.json
