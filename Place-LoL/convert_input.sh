#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUILD_DIR="${SCRIPT_DIR}/build_convert_only"
INSTALL_DIR="${SCRIPT_DIR}/install"

usage() {
  echo "Usage: bash convert_input.sh <design|iccad_2022_all|iccad_2023_all> <variant> <terminal_size>"
}

if [[ $# -lt 3 ]]; then
  usage
  exit 1
fi

design_opt=$1
input_variant=$2
terminal_size=$3

if [[ "${design_opt}" == "iccad_2023_all" ]]; then
  designs=(swerv_wrapper bp bp_be bp_fe bp_multi ariane133 ariane136 bp_quad)
elif [[ "${design_opt}" == "iccad_2022_all" ]]; then
  designs=(aes ibex jpeg swerv dynamic_node)
else
  designs=("${design_opt}")
fi

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"
cmake .. -DPLACELOL_CONVERT_ONLY=ON
make -j
make -j install
cd "${INSTALL_DIR}"

for design_name in "${designs[@]}"; do
  params_json="test/3D_input_${input_variant}/${design_name}.json"
  python3 dreamplace/convert_input.py "${params_json}" "${design_name}" "${input_variant}" "${terminal_size}"
done
