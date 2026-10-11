#!/usr/bin/env python3
"""Register an official build and every materialized source overlay."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
from verify_official_container import digest, write_manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-report', type=Path, required=True)
    parser.add_argument('--parity-report', type=Path, required=True)
    parser.add_argument('--prior-reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report_path = args.build_report.resolve(strict=True)
    build = json.loads(report_path.read_text())
    previous = json.loads(args.prior_reference.read_text())
    if build['status'] != 'complete' or build['exit_code'] != 0:
        raise ValueError('Official build did not complete')
    incremental_parent = None
    if build['fresh_build'] is not True:
        if build.get('build_kind') != 'incremental_verified_full_build_clone':
            raise ValueError('Incremental build lacks verified full-build ancestry')
        parent_path = Path(build['parent_build_report'])
        if digest(parent_path) != build['parent_build_report_sha256']:
            raise ValueError('Incremental parent build report changed')
        parent = json.loads(parent_path.read_text())
        if parent.get('status') != 'complete' or parent.get('fresh_build') is not True or parent.get('exit_code') != 0:
            raise ValueError('Incremental parent was not a completed fresh build')
        if parent['image_id'] != build['image_id'] or parent['openroad_base_commit'] != build['openroad_base_commit']:
            raise ValueError('Incremental parent image/base identity differs')
        if digest(Path(parent['public_binary'])) != parent['public_binary_sha256'] or digest(Path(parent['source_zip'])) != parent['source_zip_sha256']:
            raise ValueError('Incremental parent binary or source archive changed')
        incremental_parent = {'report': str(parent_path.resolve()), 'report_sha256': digest(parent_path),
                              'binary_sha256': parent['public_binary_sha256'], 'source_zip_sha256': parent['source_zip_sha256']}
    if build['image_id'] != previous['image_id'] or build['openroad_base_commit'] != previous['openroad_base_commit']:
        raise ValueError('Official image/base identity changed')
    binary = Path(build['public_binary']); archive = Path(build['source_zip'])
    if digest(binary) != build['public_binary_sha256'] or digest(archive) != build['source_zip_sha256']:
        raise ValueError('Built binary or compiled source ZIP changed')
    log = report_path.parent / 'build.log'
    if digest(log) != build['build_log_sha256']:
        raise ValueError('Official build log changed')
    with zipfile.ZipFile(archive) as source:
        overlays = {name: hashlib.sha256(source.read(name)).hexdigest() for name in sorted(source.namelist())
                    if name.startswith('openroad_overlay/') and not name.endswith('/')}
    if not overlays or overlays != build['overlay_file_sha256']:
        raise ValueError('Build ZIP overlay hashes differ from build report')
    materialized = binary.parents[2] / 'openroad-src'
    for name, expected in overlays.items():
        if digest(materialized / name[len('openroad_overlay/'):]) != expected:
            raise ValueError('Materialized compiled overlay differs: ' + name)
    parity_path = args.parity_report.resolve(strict=True)
    parity = json.loads(parity_path.read_text())
    if not {'original', 'boundaries'} <= parity['comparisons'].keys() or any(
        item.get('equal') is not True for item in parity['comparisons'].values()):
        raise ValueError('Native/Tcl export parity was not confirmed')
    result = dict(previous)
    result.update(scope='verified_official_fresh_build_reference' if build['fresh_build'] is True else 'verified_official_incremental_build_reference',
                  build_kind='fresh' if build['fresh_build'] is True else build['build_kind'],
                  verified_incremental_parent=incremental_parent,
                  captured_utc=datetime.now(timezone.utc).isoformat(),
                  source_zip=str(archive), source_zip_sha256=digest(archive), public_binary=str(binary),
                  public_binary_sha256=digest(binary), overlay_file_sha256=overlays,
                  verification=str(report_path), verification_sha256=digest(report_path),
                  export_parity_report=str(parity_path), export_parity_report_sha256=digest(parity_path),
                  inherited_quality_baseline_reference=str(args.prior_reference.resolve()),
                  inherited_quality_baseline_reference_sha256=digest(args.prior_reference),
                  compiled_materialized_source=str(materialized))
    write_manifest(args.output, result)
    print(f'Captured official build reference: {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
