#!/usr/bin/env python3
"""Freeze candidate sources/configs and optionally run true official-container experiments."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid
import zipfile

from verify_official_container import digest, unpack_zip, write_manifest

REPOSITORY = Path(__file__).resolve().parents[2]
CONTAINER_REPOSITORY = Path('/workspace/Open3DBench')


def container_path(path: Path) -> str:
    return str(CONTAINER_REPOSITORY / path.resolve().relative_to(REPOSITORY))


def translate(value):
    if isinstance(value, dict): return {key: translate(item) for key, item in value.items()}
    if isinstance(value, list): return [translate(item) for item in value]
    if isinstance(value, str) and (value == str(REPOSITORY) or value.startswith(str(REPOSITORY) + '/')):
        return container_path(Path(value))
    return value


def pairs(values: list[str]) -> dict[str, Path]:
    result = {}
    for value in values:
        label, sep, path = value.partition('=')
        if not sep or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', label) or label in result:
            raise ValueError('Use distinct label=path arguments with safe labels')
        result[label] = Path(path).resolve(strict=True)
    return result


def archive_directory(source: Path, output: Path) -> None:
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob('*')):
            if path.is_file() and not set(path.relative_to(source).parts) & {'.git', '.build', '__pycache__', 'test_output'}:
                if path.is_symlink(): raise ValueError('Candidate snapshot must not contain symlinks')
                archive.write(path, str(path.relative_to(source)))


def active_reservations() -> list[dict]:
    active = []
    paths = (path for directory in sorted((REPOSITORY / 'reports').glob('optimization_v*'))
             if directory.is_dir() for path in directory.rglob('host_experiment.json'))
    for path in paths:
        record = json.loads(path.read_text())
        if record.get('status') not in ('reserved', 'running'):
            continue
        alive = False
        if record.get('host_pid'):
            try: os.kill(record['host_pid'], 0); alive = True
            except ProcessLookupError: pass
            except PermissionError: alive = True
        if not alive:
            command = record.get('command', [])
            if '--name' in command:
                name = command[command.index('--name') + 1]
                probe = subprocess.run(['docker', 'inspect', '--format', '{{.State.Running}}', name], capture_output=True, text=True)
                alive = probe.returncode == 0 and probe.stdout.strip() == 'true'
        if alive:
            reserved = record.get('reserved_threads')
            if reserved is None:
                old_plan = json.loads((path.parent / 'prepared_plan.json').read_text())
                reserved = max(old_plan['jobs'] * old_plan.get('threads', 8), old_plan['build_threads'] if any(not item['reuse_verified_binary_expected'] for item in old_plan['candidates'].values()) else 0)
            active.append({'host_record': str(path), 'threads': reserved, 'external_threads': record.get('external_threads', 0)})
    return active


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', action='append', default=[], help='label=source.zip or label=submission-directory')
    parser.add_argument('--config', action='append', default=[], help='label=JSON; merge overrides into the captured candidate config')
    parser.add_argument('--baseline', action='append', default=[], help='Candidate label routed with MLS_ENABLE=0')
    parser.add_argument('--reuse-quality', action='append', default=[], help='Disabled: historical evaluation-time full platform fingerprints are unavailable')
    parser.add_argument('--canonical-gate', action='append', default=[], help='label=JSON mapping case names to required canonical DEF/guide SHA before detailed evaluation')
    parser.add_argument('--reference', type=Path, default=REPOSITORY / 'reports/optimization_v3/baseline_reference.json')
    parser.add_argument('--output-root', type=Path, default=REPOSITORY / 'reports/optimization_v3/experiments')
    parser.add_argument('--cases', nargs='+', default=['bp_fe'])
    parser.add_argument('--evaluate-cases', nargs='+', help='Cases receiving fresh fixed DRT/STA (default: bp_fe); must be included in --cases')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--threads', type=int, default=8, help='Threads per candidate for both GRT and fixed DRT/STA (default: 8)')
    parser.add_argument('--build-threads', type=int, default=32)
    parser.add_argument('--external-threads', type=int, default=0, help='Reserve budget for independently launched builds/jobs outside this tool')
    parser.add_argument('--grt-only', action='store_true', help='Omit detailed evaluation; canonical legality still runs')
    parser.add_argument('--execute', action='store_true', help='Start Docker; default only captures an immutable candidate plan')
    parser.add_argument('--plan', type=Path, help='Execute a previously prepared plan, without recapturing production files')
    args = parser.parse_args()
    if args.reuse_quality:
        parser.error('Official quality reuse is disabled: historical evaluation-time full platform collateral fingerprints are unavailable; request fresh evaluation')
    if (not 1 <= args.jobs <= 4 or not 1 <= args.threads <= 32 or args.jobs * args.threads > 32
            or not 1 <= args.build_threads <= 32 or not 0 <= args.external_threads <= 32):
        parser.error('jobs must be 1..4; threads and build-threads must be 1..32; jobs * threads must be <=32')
    if len(set(args.cases)) != len(args.cases) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', case) for case in args.cases):
        parser.error('Choose distinct safe case names')
    if args.grt_only and args.evaluate_cases:
        parser.error('--evaluate-cases cannot be combined with --grt-only')
    try:
        if args.plan:
            if args.candidate or args.config or args.baseline or args.reuse_quality or args.canonical_gate or args.evaluate_cases:
                raise ValueError('--plan cannot be combined with candidate/config/baseline capture')
            plan_path = args.plan.resolve(strict=True)
            plan = json.loads(plan_path.read_text()); run = plan_path.parent
            if any(item.get('reuse_quality') for item in plan['candidates'].values()):
                raise ValueError('Prepared quality-reuse plans are disabled until full evaluation-time platform collateral identity is proven; prepare a fresh evaluation plan')
        else:
            evaluate_cases = [] if args.grt_only else (args.evaluate_cases or ['bp_fe'])
            if len(set(evaluate_cases)) != len(evaluate_cases) or set(evaluate_cases) - set(args.cases):
                raise ValueError('Evaluation cases must be distinct and included in --cases; use --grt-only to omit DRT/STA')
            candidates = pairs(args.candidate); configs = pairs(args.config); gates = pairs(args.canonical_gate)
            if not candidates: raise ValueError('At least one --candidate label=path is required')
            if set(configs) - set(candidates) or set(args.baseline) - set(candidates) or set(gates) - set(candidates):
                raise ValueError('Config/baseline labels must refer to captured candidates')
            reference = json.loads(args.reference.resolve(strict=True).read_text())
            if digest(Path(reference['source_zip'])) != reference['source_zip_sha256'] or digest(Path(reference['public_binary'])) != reference['public_binary_sha256']:
                raise ValueError('Verified baseline archive or public binary changed')
            output = args.output_root.resolve()
            if not output.is_relative_to(REPOSITORY): raise ValueError('Output must stay inside the repository')
            batch = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
            run = output / batch; run.mkdir(parents=True)
            (run / 'home').mkdir()
            for name in ('verify_official_experiments.py', 'verify_official_container.py'):
                destination = 'official_common.py' if name == 'verify_official_container.py' else name
                shutil.copy2(Path(__file__).parent / name, run / destination)
            revision = subprocess.run(['git', '-C', str(REPOSITORY), 'rev-parse', 'HEAD'], capture_output=True, text=True)
            plan = {'scope': 'captured_official_candidate_plan', 'status': 'prepared', 'batch': batch,
                    'created_utc': datetime.now(timezone.utc).isoformat(), 'source_commit_at_capture': revision.stdout.strip(),
                    'baseline': translate(reference), 'input_root': translate(reference['input_root']),
                    'cases': args.cases, 'threads': args.threads, 'jobs': args.jobs, 'build_threads': args.build_threads,
                    'grt_only': args.grt_only, 'evaluate_cases': evaluate_cases, 'candidates': {},
                    'driver_sha256': digest(run / 'verify_official_experiments.py'), 'common_sha256': digest(run / 'official_common.py')}
            for label, original in candidates.items():
                if not original.is_relative_to(REPOSITORY): raise ValueError('Candidate sources must be in the repository')
                directory = run / 'candidates' / label; directory.mkdir(parents=True)
                captured = directory / 'original_source.zip'
                if original.is_dir(): archive_directory(original, captured)
                else: shutil.copy2(original, captured)
                with zipfile.ZipFile(captured) as archive:
                    if archive.testzip() is not None or len(archive.namelist()) != len(set(archive.namelist())):
                        raise ValueError('ZIP CRC failed or ZIP contains duplicate paths')
                temporary = directory / 'capture_source'
                unpack_zip(captured, temporary)
                config = temporary / 'flow_scripts/scripts_3D/mls_config.json'
                config_data = json.loads(config.read_text())
                override_sha = None
                if label in configs:
                    override = json.loads(configs[label].read_text())
                    if not isinstance(override, dict): raise ValueError('Config overrides must be a JSON object')
                    config_data.update(override)
                    override_sha = digest(configs[label])
                    config.write_text(json.dumps(config_data, indent=2) + '\n')
                snapshot = directory / 'source.zip'; archive_directory(temporary, snapshot)
                fingerprint = {str(p.relative_to(temporary)): digest(p) for p in sorted((temporary / 'openroad_overlay').rglob('*')) if p.is_file()}
                expected_canonical = json.loads(gates[label].read_text()) if label in gates else {}
                if set(expected_canonical) - set(args.cases): raise ValueError('Canonical gate names a case outside this plan')
                for case, expected in expected_canonical.items():
                    if set(expected) != {'submission.def', 'route.guide'} or any(not re.fullmatch(r'[0-9a-f]{64}', value) for value in expected.values()):
                        raise ValueError('Canonical gate must contain DEF/guide SHA256 pairs')
                plan['candidates'][label] = {'original_source': str(original), 'original_source_sha256': digest(captured),
                    'source_zip_sha256': digest(snapshot), 'overlay_file_sha256': fingerprint,
                    'reuse_verified_binary_expected': bool(fingerprint) and fingerprint == reference['overlay_file_sha256'],
                    'config_sha256': digest(config), 'config_values': config_data,
                    'override_source': str(configs[label]) if label in configs else None, 'override_sha256': override_sha,
                    'baseline_mode': label in args.baseline,
                    'expected_canonical': expected_canonical,
                    'canonical_gate_source_sha256': digest(gates[label]) if label in gates else None}
                shutil.rmtree(temporary)
            plan_path = run / 'prepared_plan.json'; write_manifest(plan_path, plan)
        if not plan_path.is_relative_to(REPOSITORY): raise ValueError('Plan must be in the repository')
        print(f'Prepared plan: {plan_path}', flush=True)
        for label, record in plan['candidates'].items():
            print(f'{label}: verified binary reuse={record["reuse_verified_binary_expected"]}; source SHA={record["source_zip_sha256"]}', flush=True)
        if not args.execute:
            print('No candidate execution requested; use --plan <path> --execute to start the captured plan.', flush=True)
            return 0
        if (run / 'experiment.json').exists() or (run / 'host_experiment.json').exists():
            raise ValueError('Plan already executed; create a fresh snapshot/plan')
        if digest(run / 'verify_official_experiments.py') != plan['driver_sha256'] or digest(run / 'official_common.py') != plan['common_sha256']:
            raise ValueError('Captured experiment driver changed')
        if plan.get('reuse_module_sha256') and digest(run / 'reuse_official_metrics.py') != plan['reuse_module_sha256']:
            raise ValueError('Captured quality reuse module changed')
        inspection = subprocess.run(['docker', 'image', 'inspect', plan['baseline']['image_id']], capture_output=True, text=True)
        if inspection.returncode: raise RuntimeError('Official image unavailable or Docker access denied: ' + inspection.stderr.strip())
        image = json.loads(inspection.stdout)[0]
        if image['Id'] != plan['baseline']['image_id']: raise ValueError('Docker image identity changed')
        container_run = container_path(run)
        command = ['docker', 'run', '--rm', '--init', '--pull=never', '--name', 'open3dbench-experiment-' + plan['batch'].lower(),
            '--user', f'{os.getuid()}:{os.getgid()}', '--ulimit', 'stack=-1:-1', '-e', 'HOME=' + container_run + '/home',
            '-v', f'{REPOSITORY}:{CONTAINER_REPOSITORY}:ro', '-v', f'{run}:{container_run}:rw',
            '-w', str(CONTAINER_REPOSITORY), '--entrypoint', '/usr/bin/python3', image['Id'],
            container_run + '/verify_official_experiments.py', '--plan', container_path(plan_path),
            '--expected-plan-sha256', digest(plan_path)]
        reserved = max(plan['jobs'] * plan.get('threads', 8), plan['build_threads'] if any(not item['reuse_verified_binary_expected'] for item in plan['candidates'].values()) else 0)
        host = {'scope': 'official_container_experiment_host', 'status': 'queued', 'image_id': image['Id'],
                'prepared_plan_sha256': digest(plan_path), 'command': command, 'host_pid': os.getpid(),
                'reserved_threads': reserved, 'external_threads': args.external_threads,
                'thread_budget_note': 'Atomic admission checks active tool reservations plus caller-declared external jobs against 32; builds finish before candidate pools.'}
        host_path = run / 'host_experiment.json'
        lock_path = REPOSITORY / 'reports/optimization_v3/scheduling.lock'; lock_path.parent.mkdir(exist_ok=True)
        with lock_path.open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            active = active_reservations()
            external_reservation = max([args.external_threads, *[item['external_threads'] for item in active]])
            total = reserved + external_reservation + sum(item['threads'] for item in active)
            if total > 32:
                raise RuntimeError(f'Thread budget unavailable: active + requested + external = {total} > 32; prepared plan remains unexecuted')
            host.update(status='reserved', other_active_reservations=active, admitted_total_threads=total,
                        effective_external_reservation=external_reservation)
            write_manifest(host_path, host)
        host['status'] = 'running'; write_manifest(host_path, host)
        with (run / 'docker_run.log').open('w') as log:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
            for line in process.stdout:
                log.write(line); log.flush(); print(line, end='', flush=True)
            code = process.wait()
        record_path = run / 'experiment.json'
        complete = code == 0 and record_path.is_file() and json.loads(record_path.read_text()).get('status') == 'complete'
        host.update(status='complete' if complete else 'failed', docker_exit_code=code); write_manifest(host_path, host)
        return 0 if complete else (code or 1)
    except Exception as error:
        if 'host_path' in locals() and host_path.is_file():
            failed_host = json.loads(host_path.read_text())
            failed_host.update(status='failed', error=str(error)); write_manifest(host_path, failed_host)
        print(f'Official experiment preparation/execution failed: {error}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
