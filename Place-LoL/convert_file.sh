#!/bin/bash

set -euo pipefail

usage() {
  echo "Preferred:"
  echo "  bash convert_input.sh  <design|iccad_2022_all|iccad_2023_all> <variant> <terminal_size>"
  echo "  bash convert_output.sh <design|iccad2022_all|iccad2023_all> <method> <variant>"
  echo
  echo "Compatibility wrapper:"
  echo "  bash convert_file.sh <design_opt> <input|output> <method_or_dash> <variant> <terminal_size_or_dash>"
}

if [[ $# -lt 2 ]]; then
  usage
  exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

if [[ "$1" == "input" || "$1" == "output" ]]; then
  mode=$1
  shift
  if [[ "${mode}" == "input" ]]; then
    exec bash "${SCRIPT_DIR}/convert_input.sh" "$@"
  fi
  exec bash "${SCRIPT_DIR}/convert_output.sh" "$@"
fi

design_opt=$1
mode=$2
method=${3:-}
input_variant=${4:-}
terminal_size=${5:-}

case "${mode}" in
  input)
    if [[ -z "${input_variant}" || -z "${terminal_size}" ]]; then
      usage
      exit 1
    fi
    exec bash "${SCRIPT_DIR}/convert_input.sh" "${design_opt}" "${input_variant}" "${terminal_size}"
    ;;
  output)
    if [[ -z "${method}" || -z "${input_variant}" ]]; then
      usage
      exit 1
    fi
    exec bash "${SCRIPT_DIR}/convert_output.sh" "${design_opt}" "${method}" "${input_variant}"
    ;;
  *)
    echo "Unknown mode: ${mode}"
    usage
    exit 1
    ;;
esac
