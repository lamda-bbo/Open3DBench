#!/bin/bash

set -euo pipefail

PACK_ROOT=${1:-evaluation_pack}

run_task() {
    local design_fullname=$1
    local design_shortname=$2
    local method=$3
    local def_input="${PACK_ROOT}/${method}/${design_fullname}.def"
    local work_variant="mol"
    local work_log_dir="logs/nangate45_3D/${design_shortname}/${work_variant}"
    local work_results_dir="results/nangate45_3D/${design_shortname}/${work_variant}"
    local archive_dir="logs/nangate45_3D/${design_shortname}/${method}"
    local runtime_log="${work_log_dir}/runtime.log"

    mkdir -p "${work_log_dir}"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting task: ${design_fullname} (${method})" >> "${runtime_log}"

    local start_time
    start_time=$(date +%s)

    make \
        DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config_upper_shrink.mk \
        DEF_INPUT="${def_input}" \
        DEF_VERSION="${design_shortname}" \
        FLOW_VARIANT="${work_variant}" \
        do-autoflow

    local hotspot_time
    hotspot_time=$(date +%s)

    make \
        DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config.mk \
        DEF_INPUT="${def_input}" \
        DEF_VERSION="${design_shortname}" \
        FLOW_VARIANT="${work_variant}" \
        do-cts_eval

    make \
        DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config.mk \
        DEF_VERSION="${design_shortname}" \
        FLOW_VARIANT="${work_variant}" \
        do-hotspot

    local end_time
    end_time=$(date +%s)

    local open3d_rt=$((hotspot_time - start_time))
    local hotspot_rt=$((end_time - hotspot_time))

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished task: ${design_fullname} (${method}). Open3D Runtime: ${open3d_rt}s, HotSpot Runtime: ${hotspot_rt}s" >> "${runtime_log}"
    echo "-----------------------------------------------------" >> "${runtime_log}"

    rm -rf "${archive_dir}"
    mkdir -p "${archive_dir}"

    cp -a "${work_log_dir}/." "${archive_dir}/"

    if compgen -G "${work_results_dir}/*.png" > /dev/null; then
        cp -a "${work_results_dir}/"*.png "${archive_dir}/"
    fi

    if [ -d "${work_results_dir}/hotspot_outputs" ]; then
        cp -a "${work_results_dir}/hotspot_outputs" "${archive_dir}/"
    fi
}

export OPENROAD_EXE=$(command -v openroad)

run_task "ariane133" "ariane133" "mol-tiling"
run_task "ariane136" "ariane136" "mol-tiling"
run_task "black_parrot" "bp" "mol-tiling"
run_task "bp_be_top" "bp_be" "mol-tiling"
run_task "bp_fe_top" "bp_fe" "mol-tiling"
run_task "bp_multi_top" "bp_multi" "mol-tiling"
run_task "swerv_wrapper" "swerv_wrapper" "mol-tiling"
run_task "bp_quad" "bp_quad" "mol-tiling"
