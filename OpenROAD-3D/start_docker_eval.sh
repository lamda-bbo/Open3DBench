#!/bin/bash

set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(cd "${SCRIPT_DIR}/.." && pwd)
OPENROAD_ROOT="${SCRIPT_DIR}"
PLACE_LOL_ROOT="${REPO_ROOT}/Place-LoL"

if [[ ! -d "${PLACE_LOL_ROOT}" ]]; then
    echo "Place-LoL directory not found at: ${PLACE_LOL_ROOT}" >&2
    exit 1
fi

sudo docker run --rm -it \
    -v "${OPENROAD_ROOT}:/workspace/OpenROAD-3D" \
    -v "${PLACE_LOL_ROOT}:/workspace/Place-LoL" \
    shiyunqi/open3dbench:eval \
    bash -lc "export PLACE_LOL_ROOT=/workspace/Place-LoL && cd /workspace/OpenROAD-3D/flow && exec bash"
