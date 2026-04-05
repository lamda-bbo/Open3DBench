#!/bin/bash

# set -euo pipefail

run_task() {
    local design_fullname=$1
    local design_shortname=$2
    local method=$3
    local design_config="designs/nangate45/${design_fullname}/config.mk"
    local work_log_dir="logs/nangate45/${design_shortname}/${method}"
    local work_results_dir="results/nangate45/${design_shortname}/${method}"
    local runtime_log="${work_log_dir}/runtime.log"

    mkdir -p "${work_log_dir}"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting task: ${design_fullname} (${method})" >> "${runtime_log}"

    local start_time
    start_time=$(date +%s)

    make \
        DESIGN_CONFIG="${design_config}" \
        FLOW_VARIANT="${method}" \
        do-floorplan \
        do-place \
        do-cts \
        do-route \
        do-finish \
        do-hotspot_2D

    local end_time
    end_time=$(date +%s)

    local total_rt=$((end_time - start_time))

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished task: ${design_fullname} (${method}). Total Runtime: ${total_rt}s" >> "${runtime_log}"
    echo "-----------------------------------------------------" >> "${runtime_log}"

    rm -rf "${work_log_dir}/hotspot_outputs"

    if compgen -G "${work_results_dir}/*.png" > /dev/null; then
        cp -a "${work_results_dir}/"*.png "${work_log_dir}/"
    fi

    if [ -d "${work_results_dir}/hotspot_outputs" ]; then
        cp -a "${work_results_dir}/hotspot_outputs" "${work_log_dir}/"
    fi
}

export OPENROAD_EXE=$(command -v openroad)

run_task "ariane133" "ariane133" "2D_rtlmp"
run_task "ariane136" "ariane136" "2D_rtlmp"
run_task "black_parrot" "bp" "2D_rtlmp"
run_task "bp_be_top" "bp_be" "2D_rtlmp"
run_task "bp_fe_top" "bp_fe" "2D_rtlmp"
run_task "bp_multi_top" "bp_multi" "2D_rtlmp"
run_task "swerv_wrapper" "swerv_wrapper" "2D_rtlmp"
run_task "bp_quad" "bp_quad" "2D_rtlmp"