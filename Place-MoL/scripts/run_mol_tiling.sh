#!/bin/bash
# Run greedy-based 3D placement pipeline (main_greedy.py).
# Usage: ./scripts/run_mol_tiling.sh <benchmark> [seed] [config_file]
#   benchmark   - design name (required)
#   seed        - random seed (default: 3)
#   config_file - config JSON name under config/ (default: or_3D.json)
#
# Example:
#   ./scripts/run_mol_tiling.sh ariane133
#   ./scripts/run_mol_tiling.sh bp_quad 42
#   ./scripts/run_mol_tiling.sh bp_quad 42 or_3D_bp_quad.json

set -e
cd "$(dirname "$0")/.."

BENCHMARK=${1:?Usage: $0 <benchmark> [seed] [config_file]}
SEED=${2:-3}
CONFIG_FILE=${3:-or_3D.json}

python src/place_3d/main_greedy.py --benchmark="$BENCHMARK" --seed="$SEED" --config_file="$CONFIG_FILE"
