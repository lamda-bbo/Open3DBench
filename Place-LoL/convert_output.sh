#!/bin/bash

# set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BUILD_DIR="${SCRIPT_DIR}/build_convert_only"
INSTALL_DIR="${SCRIPT_DIR}/install"

usage() {
  echo "Usage: bash convert_output.sh <design|iccad2022_all|iccad2023_all> <method> <variant>"
}

if [[ $# -lt 3 ]]; then
  usage
  exit 1
fi

design_opt=$1
method=$2
input_variant=$3

if [[ "${design_opt}" == "iccad2023_all" ]]; then
  designs=(swerv_wrapper bp bp_be bp_fe bp_multi ariane133 ariane136 bp_quad)
elif [[ "${design_opt}" == "iccad2022_all" ]]; then
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

failed_designs=()

for design_name in "${designs[@]}"; do
  params_json="test/3D_input_${input_variant}/${design_name}.json"

  if [[ ! -f "${params_json}" ]]; then
    echo "[WARN] Missing input json for ${design_name}: ${params_json}"
    failed_designs+=("${design_name}")
    continue
  fi

  if ! python3 dreamplace/convert_output.py "${params_json}" "${design_name}" "${method}" "${input_variant}"; then
    echo "[WARN] convert_output failed for ${design_name}, continuing..."
    failed_designs+=("${design_name}")
    continue
  fi
done

if [[ ${#failed_designs[@]} -gt 0 ]]; then
  echo
  echo "[WARN] Finished with failures:"
  printf '  - %s\n' "${failed_designs[@]}"
else
  echo "[INFO] All designs finished successfully."
fi
