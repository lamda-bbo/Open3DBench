#!/usr/bin/env python3
"""Isolated contest entry point: DEF -> prepared ODB -> two GRT passes -> ODB."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from materialize_source import source_fingerprint


def tcl_quote(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('[', '\\[').replace(']', '\\]') + '"'


def component_masters(def_path: Path, chunk_size: int = 1024 * 1024) -> set[str]:
    """Use the original section grammar without loading the later NETS section."""
    pattern = re.compile(r'\bCOMPONENTS\s+\d+\s*;(.*?)\bEND COMPONENTS\b', re.S)
    marker = 'END COMPONENTS'
    pieces: list[str] = []
    tail = ''
    pending_boundary = False
    with def_path.open() as stream:
        while chunk := stream.read(chunk_size):
            pieces.append(chunk)
            if pending_boundary or marker in tail + chunk:
                text = ''.join(pieces)
                section = pattern.search(text)
                # Read the following character before accepting a word boundary.
                if section is not None and section.end() < len(text):
                    return set(re.findall(r'^\s*-\s+\S+\s+(\S+)', section.group(1), re.M))
                pending_boundary = section is not None
            tail = (tail + chunk)[-(len(marker) - 1):]
    section = pattern.search(''.join(pieces))
    if section is None:
        raise ValueError('DEF has no COMPONENTS section')
    return set(re.findall(r'^\s*-\s+\S+\s+(\S+)', section.group(1), re.M))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def select_collateral(def_path: Path, platform: Path) -> tuple[list[Path], list[Path]]:
    """Load exact normal-size masters used by this DEF, avoiding shrink copies."""
    masters = component_masters(def_path)
    lef_files = [platform / 'lef/NangateOpenCellLibrary.tech.lef']
    cell_lefs = sorted((platform / 'lef_bottom').glob('*.lef')) + sorted((platform / 'lef_upper').glob('*.lef'))
    covered: set[str] = set()
    for lef in cell_lefs:
        names = set(re.findall(r'^\s*MACRO\s+(\S+)', lef.read_text(), re.M))
        if names & masters:
            lef_files.append(lef)
            covered.update(names)
    if masters - covered:
        raise ValueError(f'Platform LEFs lack masters: {sorted(masters - covered)[:20]}')
    lib_files: list[Path] = []
    for lib in sorted((platform / 'lib_bottom').glob('*.lib')) + sorted((platform / 'lib_upper').glob('*.lib')):
        if ' copy.' in lib.name:
            continue
        names = set(re.findall(r'\bcell\s*\(\s*"?([^\s)\"]+)"?\s*\)', lib.read_text()))
        if names & masters:
            lib_files.append(lib)
    for path in lef_files + lib_files:
        if not path.is_file():
            raise FileNotFoundError(path)
    if not lib_files:
        raise ValueError('No matching Liberty files in platform')
    return lef_files, lib_files


def resolve_executable(root: Path, threads: int) -> str:
    explicit = os.environ.get('OPENROAD_EXE')
    build_root = Path(os.environ.get('SUBMISSION_BUILD_DIR', str(Path(tempfile.gettempdir()) / f'open3dbench-grt-build-{os.getuid()}')))
    candidates = [explicit] if explicit else [str(root / 'bin/openroad')]
    if not explicit:
        stamp = build_root / '.submission-source-sha256'
        if stamp.is_file() and stamp.read_text().strip() == source_fingerprint(root / 'openroad_overlay'):
            candidates.append(str(build_root / 'openroad-build/bin/openroad'))
    for candidate in candidates:
        if candidate and (Path(candidate).is_file() or shutil.which(candidate)):
            return str(Path(shutil.which(candidate) or candidate).absolute())
    if explicit:
        raise FileNotFoundError(f'OPENROAD_EXE is not executable: {explicit}')
    subprocess.run(['bash', str(root / 'build.sh'), str(threads)], check=True)
    binary = build_root / 'openroad-build/bin/openroad'
    if not binary.is_file():
        raise RuntimeError('build.sh did not produce bin/openroad')
    return str(binary)


def run_openroad(exe: str, script: Path, env: dict[str, str], log: Path) -> float:
    print(f'OpenROAD: {script.name}; log: {log}', flush=True)
    stage_start = time.monotonic()
    with log.open('w') as output:
        result = subprocess.run([exe, '-exit', '-no_init', str(script)], env=env, stdout=output, stderr=subprocess.STDOUT)
    if result.returncode:
        tail = log.read_text(errors='replace').splitlines()[-30:]
        raise RuntimeError(f'OpenROAD exited {result.returncode}:\n' + '\n'.join(tail))
    return round(time.monotonic() - stage_start, 3)


def atomic_copy(source: Path, destination: Path) -> None:
    temporary = destination.with_name(destination.name + '.tmp')
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description='3D-IC MLS global router')
    parser.add_argument('input_dir', type=Path)
    parser.add_argument('output_dir', type=Path)
    parser.add_argument('platform_dir', type=Path)
    parser.add_argument('threads', type=int, nargs='?', default=32)
    args = parser.parse_args()
    if not 1 <= args.threads <= 32:
        parser.error('threads must be an integer between 1 and 32')
    process_mode = os.environ.get('GRT_PROCESS_MODE', 'single')
    input_mode = os.environ.get('GRT_INPUT_MODE', 'auto')
    if process_mode not in ('single', 'isolated'):
        parser.error("GRT_PROCESS_MODE must be 'single' or 'isolated'")
    if input_mode not in ('auto', 'def', 'odb'):
        parser.error("GRT_INPUT_MODE must be 'auto', 'def', or 'odb'")
    export_def_mode = os.environ.get('SUBMISSION_EXPORT_DEF', '0')
    if export_def_mode not in ('0', '1'):
        parser.error("SUBMISSION_EXPORT_DEF must be '0' or '1'")
    export_def = export_def_mode == '1'
    if input_mode == 'auto':
        input_mode = 'def' if process_mode == 'single' else 'odb'
    if process_mode == 'isolated' and input_mode == 'def':
        parser.error('Direct DEF input requires GRT_PROCESS_MODE=single')
    root = Path(__file__).resolve().parents[1]
    input_dir = args.input_dir.resolve(strict=True)
    platform = args.platform_dir.resolve(strict=True)
    if any('\n' in str(path) or '\r' in str(path) for path in (root, input_dir, args.output_dir, platform)):
        parser.error('paths must not contain newline characters')
    def_path, sdc_path = input_dir / '4_1_cts.def', input_dir / '4_cts.sdc'
    if not def_path.is_file() or not sdc_path.is_file():
        parser.error('input_dir must contain 4_1_cts.def and 4_cts.sdc')
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # An error must not leave a previous submission looking like this run's result.
    for name in ('5_1_grt.odb', 'route.guide', 'run_manifest.json', 'submission.def', 'mls_plan.json'):
        (output / name).unlink(missing_ok=True)
    lefs, libs = select_collateral(def_path, platform)
    exe = resolve_executable(root, args.threads)
    env = dict(os.environ)
    started = time.monotonic()
    work = Path(tempfile.mkdtemp(prefix='.grt-work-', dir=output))
    results, logs, reports = (work / p for p in ('results', 'logs', 'reports'))
    for directory in (results, logs, reports):
        directory.mkdir()
    shutil.copy2(def_path, results / '4_1_cts.def')
    shutil.copy2(sdc_path, results / '4_cts.sdc')
    env.update({
        'SCRIPTS_DIR': str(root / 'flow_scripts/scripts'),
        'RESULTS_DIR': str(results), 'LOG_DIR': str(logs), 'REPORTS_DIR': str(reports),
        'PLATFORM_DIR': str(platform), 'OPENROAD_EXE': exe,
        'NUM_CORES': str(args.threads), 'OMP_NUM_THREADS': str(args.threads),
        'MIN_ROUTING_LAYER': 'metal2', 'MAX_ROUTING_LAYER': 'metal20',
        'FASTROUTE_TCL': str(platform / 'fastroute.tcl'),
        'SUBMISSION_COLLATERAL_TCL': str(work / 'collateral.tcl'),
        'GRT_INITIAL_DESIGN': '4_1_cts.def' if input_mode == 'def' else '4_cts.odb',
        'GRT_PROCESS_MODE': process_mode,
    })
    (work / 'collateral.tcl').write_text(
        'set submission_lefs [list ' + ' '.join(tcl_quote(str(p)) for p in lefs) + ']\n' +
        'set submission_libs [list ' + ' '.join(tcl_quote(str(p)) for p in libs) + ']\n')
    env.setdefault('VALIDATE_DIE_GUIDES', '1')
    env.setdefault('GRT_LAYER_ADJUSTMENTS', 'metal2=0.7,metal3=0.6')
    env.setdefault('GRT_HIGH_FANOUT_LAYERS', '1')
    # Public case configs allow overflow for the fixed detailed-route evaluator.
    env.setdefault('GLOBAL_ROUTE_ARGS', '-allow_congestion -congestion_iterations 1 -congestion_report_iter_step 5 -verbose')
    if env.get('MLS_ENABLE', '1') != '0':
        hook = root / 'flow_scripts/scripts_3D/prepare_mls.tcl'
        if not hook.is_file():
            raise FileNotFoundError(f'Missing packaged MLS hook: {hook}; run package.py')
        env['GRT_PREPARE_TCL'] = str(hook)
        env.setdefault('MLS_CONFIG', str(root / 'flow_scripts/scripts_3D/mls_config.json'))
    else:
        env.pop('GRT_PREPARE_TCL', None)
    stage_seconds = {}
    if input_mode == 'odb':
        stage_seconds['load_input'] = run_openroad(exe, root / 'src/load_input.tcl', env, logs / 'load_input.log')
        if 'SUBMISSION_LAYER_CLAMP_READY' not in (logs / 'load_input.log').read_text():
            raise RuntimeError('OpenROAD initialization or layer-clamp probe failed')
        if not (results / '4_cts.odb').is_file():
            raise RuntimeError('Input conversion did not create 4_cts.odb')
    else:
        stage_seconds['load_input'] = 0.0
    stage_seconds['global_route'] = run_openroad(exe, root / 'flow_scripts/scripts/global_route_die_by_die.tcl', env, logs / 'global_route.log')
    global_route_log = (logs / 'global_route.log').read_text()
    if input_mode == 'def' and 'SUBMISSION_LAYER_CLAMP_READY' not in global_route_log:
        raise RuntimeError('Direct DEF initialization or layer-clamp probe failed')
    detail_seconds = {
        f'{category.lower()}.{name}': int(milliseconds) / 1000
        for category, name, milliseconds in re.findall(
            r'^(MLS|GRT)_STAGE (\w+)_ms=(\d+)$',
            global_route_log, re.M)
    }
    pass_reset = re.search(r'^GRT_PASS_RESET (native|legacy)$', global_route_log, re.M)
    prepared_metadata = re.search(r'^GRT_PREPARED_METADATA (native|def)(?: sha256=([0-9a-f]{64})| reason=(\S+))$', global_route_log, re.M)
    check_mode = re.search(r'^GRT_CHECK_MODE (parallel|serial)$', global_route_log, re.M)
    check_schedule = re.search(r'^GRT_CHECK_SCHEDULE (overlap|before_finalize)$', global_route_log, re.M)
    layer_hint_counts = {
        interval: int(count) for count, interval in re.findall(
            r'^GRT_LAYER_HINTS applied=(\d+) die=(\S+)$', global_route_log, re.M)
    }
    resistance_hint_counts = {
        interval: int(count) for count, interval in re.findall(
            r'^GRT_RESISTANCE_HINTS applied=(\d+) die=(\S+)$', global_route_log, re.M)
    }
    capacity_log = global_route_log + ''.join(
        '\n' + path.read_text() for path in sorted(logs.glob('grt_pass_*.log')))
    capacity_adjustments = {}
    for layer, adjustment, interval in re.findall(
            r'^GRT_CAPACITY layer=(\S+) adjustment=(\S+) die=(\S+)$',
            capacity_log, re.M):
        capacity_adjustments.setdefault(interval, {})[layer] = float(adjustment)
    odb, guide, marker = results / '5_1_grt.odb', results / 'route.guide', results / '.grt_finalize_complete'
    if not marker.is_file() or not odb.is_file() or not odb.stat().st_size or not guide.is_file() or not guide.stat().st_size:
        raise RuntimeError(f'Routing did not publish complete output; inspect {logs}')
    # Re-open the freshly written ODB with the same executable before publishing.
    verify = work / 'verify.tcl'
    verify_commands = [f'read_db {tcl_quote(str(odb))}']
    if export_def:
        verify_commands.append(f'write_def {tcl_quote(str(results / "submission.def"))}')
    verify_commands.append('puts "SUBMISSION_ODB_READABLE"')
    verify.write_text('\n'.join(verify_commands) + '\n')
    stage_seconds['verify_odb'] = run_openroad(exe, verify, env, logs / 'verify.log')
    if 'SUBMISSION_ODB_READABLE' not in (logs / 'verify.log').read_text():
        raise RuntimeError('Fresh ODB failed reopen verification')
    odb_bytes = odb.stat().st_size
    # Work files live inside output, so rename publishes the verified ODB
    # atomically without copying the entire database on the same filesystem.
    odb.replace(output / '5_1_grt.odb')
    atomic_copy(guide, output / 'route.guide')
    if export_def:
        atomic_copy(results / 'submission.def', output / 'submission.def')
    for plan in results.glob('mls*.json'):
        atomic_copy(plan, output / plan.name)
    shutil.copytree(results / 'die_net_lists', output / 'die_net_lists', dirs_exist_ok=True)
    manifest = {
        'input_sha256': file_sha256(def_path),
        'openroad_exe': exe, 'threads': args.threads,
        'mls_enabled': env.get('MLS_ENABLE', '1') != '0',
        'runtime_seconds': round(time.monotonic() - started, 3),
        'stage_seconds': stage_seconds,
        'detail_seconds': detail_seconds,
        'grt_pass_reset': pass_reset.group(1) if pass_reset else 'unreported',
        'grt_prepared_metadata': prepared_metadata.group(1) if prepared_metadata else 'unreported',
        'grt_prepared_metadata_sha256': prepared_metadata.group(2) if prepared_metadata else None,
        'grt_prepared_metadata_fallback_reason': prepared_metadata.group(3) if prepared_metadata else None,
        'grt_check_mode': check_mode.group(1) if check_mode else 'unreported',
        'grt_check_schedule': check_schedule.group(1) if check_schedule else 'unreported',
        'grt_layer_hint_counts': layer_hint_counts,
        'grt_resistance_hint_counts': resistance_hint_counts,
        'grt_capacity_adjustments': capacity_adjustments,
        'grt_capacity_adjustment_default': float(env.get('GLOBAL_ROUTING_LAYER_ADJUSTMENT', '0.5')),
        'grt_layer_adjustments_requested': env.get('GRT_LAYER_ADJUSTMENTS', ''),
        'global_route_args': env['GLOBAL_ROUTE_ARGS'],
        'grt_process_mode': process_mode, 'grt_input_mode': input_mode,
        'submission_export_def': export_def,
        'odb_bytes': odb_bytes, 'work_dir': str(work),
    }
    (output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'完成: {output / "5_1_grt.odb"} ({odb_bytes} bytes)', flush=True)


if __name__ == '__main__':
    main()
