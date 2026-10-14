#!/usr/bin/env python3
"""Run both read-only die-guide checks, retaining each report and failure."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def run_check(command: list[str]) -> tuple[int, bytes, bytes, int]:
    """Capture a complete child report while the other checker can progress."""
    started = time.monotonic()
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return (result.returncode, result.stdout, result.stderr,
                round((time.monotonic() - started) * 1000))
    except OSError as error:
        return (1, b"", f"Cannot run guide check: {error}\n".encode(),
                round((time.monotonic() - started) * 1000))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results_dir", type=Path)
    parser.add_argument("--def-file", required=True, type=Path)
    parser.add_argument("--classification-cache", type=Path)
    parser.add_argument('--prepared-metadata', type=Path)
    parser.add_argument('--prepared-metadata-sha256')
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--max-cc-rects", type=int, default=5000)
    parser.add_argument("--mode", choices=("serial", "parallel"),
                        default=os.environ.get("GRT_CHECK_MODE", "parallel"))
    args = parser.parse_args()
    if args.prepared_metadata_sha256 is not None and args.prepared_metadata is None:
        parser.error('--prepared-metadata-sha256 requires --prepared-metadata')
    if args.mode not in ("serial", "parallel"):
        parser.error(f"invalid GRT_CHECK_MODE: {args.mode!r}")
    try:
        available_cores = int(os.environ.get("NUM_CORES", "2"))
    except ValueError:
        parser.error("NUM_CORES must be a positive integer")
    if available_cores < 1:
        parser.error("NUM_CORES must be a positive integer")
    if available_cores == 1:
        args.mode = "serial"

    script_dir = Path(__file__).resolve().parent
    layer_command = [sys.executable, str(script_dir / "check_2d_net_guide_layers.py"),
                     str(args.results_dir / "route.guide"), str(args.def_file)]
    if args.classification_cache is not None:
        layer_command.extend(["--classification-cache", str(args.classification_cache)])
    connectivity_command = [sys.executable,
                            str(script_dir / "diagnose_guide_connectivity.py"),
                            str(args.results_dir), "--def-file", str(args.def_file),
                            "--strict", "--top", str(args.top),
                            "--max-cc-rects", str(args.max_cc_rects)]
    commands = [layer_command, connectivity_command]
    if args.prepared_metadata is not None:
        for command in commands:
            command.extend(['--prepared-metadata', str(args.prepared_metadata)])
            if args.prepared_metadata_sha256 is not None:
                command.extend(['--prepared-metadata-sha256', args.prepared_metadata_sha256])
    started = time.monotonic()
    if args.mode == "parallel":
        # Both programs are single-threaded and only read the shared inputs.
        # Always join both; a failure in either must prevent final publication.
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(run_check, commands))
    else:
        results = [run_check(command) for command in commands]

    failed = False
    for name, (returncode, stdout, stderr, elapsed_ms) in zip(
            ("check_guide_layers", "check_guide_connectivity"), results):
        sys.stdout.buffer.write(stdout)
        sys.stdout.buffer.write(f"GRT_STAGE {name}_ms={elapsed_ms}\n".encode())
        sys.stdout.buffer.flush()
        sys.stderr.buffer.write(stderr)
        sys.stderr.buffer.flush()
        if returncode:
            failed = True
            print(f"Guide check {name} failed with exit code {returncode}", file=sys.stderr)
    print(f"GRT_CHECK_MODE {args.mode}")
    print(f"GRT_STAGE check_guides_ms={round((time.monotonic() - started) * 1000)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
