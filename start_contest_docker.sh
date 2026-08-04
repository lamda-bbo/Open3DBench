#!/usr/bin/env bash

set -euo pipefail

repository=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
image=${OPEN3DBENCH_CONTEST_IMAGE:-shiyunqi/3dbench-contest:20260724}
docker_bin=${DOCKER_BIN:-docker}

mkdir -p \
  "${repository}/.contest/home" \
  "${repository}/input" \
  "${repository}/output" \
  "${repository}/reports"

docker_args=(run --rm)
if [[ -t 0 && -t 1 ]]; then
  docker_args+=(-it)
fi

command_args=("$@")
if [[ ${#command_args[@]} -eq 0 ]]; then
  command_args=(shell)
fi

exec "${docker_bin}" "${docker_args[@]}" \
  --init \
  --user "$(id -u):$(id -g)" \
  --ulimit stack=-1:-1 \
  -e HOME=/workspace/Open3DBench/.contest/home \
  -e CONTEST_ROOT=/workspace/Open3DBench \
  -v "${repository}:/workspace/Open3DBench" \
  -w /workspace/Open3DBench \
  "${image}" "${command_args[@]}"
