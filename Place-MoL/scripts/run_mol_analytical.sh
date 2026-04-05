#!/bin/bash

set -e
cd "$(dirname "$0")/.."

design_name=$1
config_file=${2:-or_3D.json}  # Default to or_3D.json if not provided

python src/place_3d/main.py --benchmark=$design_name --seed=3 --config_file=$config_file
