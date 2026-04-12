#!/bin/bash

set -euo pipefail

run_task() {
    local design_fullname=$1
    local design_shortname=$2
    local variant=$3
    local method=$4
    mkdir -p logs/nangate45_3D/${design_shortname}/lol/
    local runtime_log="logs/nangate45_3D/${design_shortname}/lol/runtime.log"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting task: ${design_fullname}" >> "$runtime_log"
    
    local start_time=$(date +%s)

    make DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config_lol.mk do-lolflow

    local hotspot_time=$(date +%s)

    make DESIGN_CONFIG=designs/nangate45_3D/${design_fullname}/config_lol.mk do-hotspot
    
    local end_time=$(date +%s)
    
    local open3d_rt=$((hotspot_time - start_time))
    local hotspot_rt=$((end_time - hotspot_time))

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Finished task: ${design_fullname}. Open3D Runtime: ${open3d_rt}s, HotSpot Runtime: ${hotspot_rt}s" >> "$runtime_log"
    echo "-----------------------------------------------------" >> "$runtime_log"

    rm -rf logs/nangate45_3D/${design_shortname}/${method}_${variant}
    mv logs/nangate45_3D/${design_shortname}/lol logs/nangate45_3D/${design_shortname}/${method}_${variant}
    mv results/nangate45_3D/${design_shortname}/lol/*.png logs/nangate45_3D/${design_shortname}/${method}_${variant}/
    mv results/nangate45_3D/${design_shortname}/lol/hotspot_outputs logs/nangate45_3D/${design_shortname}/${method}_${variant}/
}

export DEF_VARIANT=$1
export METHOD=$2
export OPENROAD_EXE=$(command -v openroad)


run_task "aes_cipher_top"          "aes"             "${DEF_VARIANT}"  "${METHOD}" 
run_task "dynamic_node_top_wrap"   "dynamic_node"    "${DEF_VARIANT}"  "${METHOD}" 
run_task "ibex_core"               "ibex"            "${DEF_VARIANT}"  "${METHOD}" 
run_task "jpeg_encoder"            "jpeg"            "${DEF_VARIANT}"  "${METHOD}" 
run_task "swerv"                   "swerv"           "${DEF_VARIANT}"  "${METHOD}" 
