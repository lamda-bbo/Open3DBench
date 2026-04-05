#!/bin/bash

set -euo pipefail

METHOD=${1:?Usage: $0 <mol-analytical|mol-tiling> [place_mol_mol_final_dir] [target_pack_root]}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/../.." && pwd)
DEFAULT_SOURCE_DIR="${REPO_ROOT}/Place-MoL/results/${METHOD}/mol_final"
SOURCE_DIR=${2:-${DEFAULT_SOURCE_DIR}}
PACK_ROOT=${3:-evaluation_pack_custom}
TARGET_DIR="${SCRIPT_DIR}/${PACK_ROOT}/${METHOD}"

case "${METHOD}" in
  mol-analytical|mol-tiling)
    ;;
  *)
    echo "Unsupported method: ${METHOD}" >&2
    exit 1
    ;;
esac

mkdir -p "${TARGET_DIR}"

copy_def() {
    local place_mol_name=$1
    local openroad_name=$2
    local src="${SOURCE_DIR}/${place_mol_name}_suffixed.def"
    local dst="${TARGET_DIR}/${openroad_name}.def"

    if [[ ! -f "${src}" ]]; then
        echo "Missing source DEF: ${src}" >&2
        exit 1
    fi

    cp "${src}" "${dst}"
    echo "Copied ${src} -> ${dst}"
}

copy_def "ariane133" "ariane133"
copy_def "ariane136" "ariane136"
copy_def "bp" "black_parrot"
copy_def "bp_be" "bp_be_top"
copy_def "bp_fe" "bp_fe_top"
copy_def "bp_multi" "bp_multi_top"
copy_def "bp_quad" "bp_quad"
copy_def "swerv_wrapper" "swerv_wrapper"

if [[ -f "${SOURCE_DIR}/mem_on_logic_results.csv" ]]; then
    cp "${SOURCE_DIR}/mem_on_logic_results.csv" "${TARGET_DIR}/mem_on_logic_results.csv"
    echo "Copied ${SOURCE_DIR}/mem_on_logic_results.csv -> ${TARGET_DIR}/mem_on_logic_results.csv"
fi
