#!/usr/bin/env python3
"""Execute captured candidates in the official image; reuse only identical GRT overlays."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import stat
from threading import Event, Thread
import time
import traceback

from official_common import (BASE, CONTEST, EVALUATOR, VALIDATION, clean_environment,
    digest, read_json, run_stage, unpack_zip, verify_official_image, write_manifest)


def overlays(directory: Path) -> dict:
    return {str(p.relative_to(directory)): digest(p) for p in sorted((directory / 'openroad_overlay').rglob('*')) if p.is_file()}


def selected_evaluation_cases(plan: dict) -> list[str]:
    # Existing captured plans omitted this field and evaluated only bp_fe.
    cases = plan.get('evaluate_cases', [] if plan['grt_only'] else ['bp_fe'])
    if (not isinstance(cases, list) or any(not isinstance(case, str) for case in cases)
            or len(set(cases)) != len(cases) or set(cases) - set(plan['cases'])
            or (plan['grt_only'] and cases) or (not plan['grt_only'] and not cases)):
        raise ValueError('Evaluation cases must be distinct routed cases, or empty only for a GRT-only plan')
    return cases


def candidate_threads(plan: dict) -> int:
    threads = plan.get('threads', 8)
    if (not isinstance(threads, int) or not 1 <= threads <= 32
            or not 1 <= plan['jobs'] <= 4 or threads * plan['jobs'] > 32
            or not 1 <= plan['build_threads'] <= 32):
        raise ValueError('Invalid thread budget')
    return threads


def platform_file_state(directory: Path) -> dict:
    """Enumerate every regular collateral file without silently omitting links."""
    if directory.is_symlink():
        raise ValueError('Platform directory must not be a symlink: ' + str(directory))
    if not directory.is_dir():
        raise ValueError('Platform directory is unavailable: ' + str(directory))
    def walk_error(error):
        raise error
    state = {}
    for parent, directories, files in os.walk(directory, onerror=walk_error):
        for name in directories + files:
            path = Path(parent) / name
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                continue
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('Platform contains a non-regular file: ' + str(path))
            state[str(path.relative_to(directory))] = (info.st_dev, info.st_ino,
                info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    if not state:
        raise ValueError('Platform contains no collateral files: ' + str(directory))
    return state


def platform_fingerprint(directory: Path) -> dict[str, str]:
    before = platform_file_state(directory)
    hashes = {name: digest(directory / name) for name in sorted(before)}
    if platform_file_state(directory) != before:
        raise ValueError('Platform changed while its files were being fingerprinted')
    return hashes


def platform_difference(expected: dict, actual: dict) -> dict:
    return {'missing': sorted(expected.keys() - actual.keys()),
            'unexpected': sorted(actual.keys() - expected.keys()),
            'changed': sorted(name for name in expected.keys() & actual.keys()
                              if expected[name] != actual[name])}


def run_evaluation_with_platform_audit(command: list[str], env: dict, log: Path,
        cwd: Path, work: Path, input_platform: Path, expected: dict) -> dict:
    """Passively capture the platform before the official EXIT trap removes it.

    The flow's first platform-use log line occurs after materialization/overlay.
    Waiting for that line avoids hashing a partially copied platform. The fixed
    launcher, environment and command are passed through without interception.
    """
    evidence_path = log.parent / 'evaluation_platform.json'
    evidence = {'schema_version': 1, 'scope': 'evaluation_time_platform_snapshot',
                'status': 'waiting', 'input_platform': str(input_platform),
                'input_file_sha256': expected, 'observation_log': str(log),
                'method': 'passive_snapshot_after_official_platform_use_log',
                'continuous_mutation_monitor': False}
    stop = Event()

    def observe():
        start = time.monotonic()
        try:
            while not stop.is_set() and not log.is_file():
                stop.wait(0.05)
            if stop.is_set():
                raise ValueError('Evaluator ended before platform observation started')
            with log.open(errors='replace') as stream:
                pending = ''
                while not stop.is_set():
                    pending += stream.read()
                    lines = pending.split('\n')
                    pending = lines.pop()
                    for line in lines:
                        match = re.fullmatch(r'\[INFO\]\[FLOW\] Using platform directory (.+)', line)
                        if match is None:
                            continue
                        materialized = Path(match.group(1)).resolve()
                        relative = materialized.relative_to(work.resolve())
                        parts = relative.parts
                        if (len(parts) != 6 or parts[0] != 'evaluator-submissions'
                                or parts[2:] != ('OpenROAD-3D', 'flow', 'platforms', input_platform.name)):
                            raise ValueError('Official flow reported an unexpected materialized platform path')
                        evidence.update(materialized_platform=str(materialized),
                                        platform_use_log_line=line)
                        hash_start = time.monotonic()
                        hashes = platform_fingerprint(materialized)
                        evidence['fingerprint_wall_seconds'] = round(time.monotonic() - hash_start, 3)
                        if stop.is_set():
                            raise ValueError('Evaluator ended before the full platform snapshot completed')
                        difference = platform_difference(expected, hashes)
                        identical = not any(difference.values())
                        evidence.update(status='complete' if identical else 'mismatch',
                            captured_utc=datetime.now(timezone.utc).isoformat(),
                            observed_while_evaluator_running=True,
                            materialized_file_sha256=hashes, file_count=len(hashes),
                            matches_input=identical, difference=difference)
                        return
                    stop.wait(0.1)
            raise ValueError('Official flow platform-use log was not observed during evaluation')
        except Exception as error:
            evidence.update(status='failed', error=str(error))
        finally:
            evidence['observation_wall_seconds'] = round(time.monotonic() - start, 3)
            write_manifest(evidence_path, evidence)

    observer = Thread(target=observe, name='official-platform-audit', daemon=True)
    observer.start()
    try:
        stage = run_stage(command, env, log, cwd)
    finally:
        stop.set()
        observer.join()
    stage['platform_audit'] = {'path': str(evidence_path), 'sha256': digest(evidence_path),
        'status': evidence['status'], 'matches_input': evidence.get('matches_input', False),
        'file_count': evidence.get('file_count', 0)}
    if evidence['status'] != 'complete':
        stage.update(status='failed', error='Evaluation-time full platform identity was not verified; see ' + str(evidence_path))
    return stage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--expected-plan-sha256', required=True)
    args = parser.parse_args()
    if digest(args.plan) != args.expected_plan_sha256:
        raise ValueError('Prepared plan changed before container start')
    plan = read_json(args.plan)
    root = args.plan.parent
    repository = Path('/workspace/Open3DBench')
    record_path = root / 'experiment.json'
    if record_path.exists():
        raise ValueError('Refusing a reused experiment directory')
    threads = candidate_threads(plan)
    evaluate_cases = selected_evaluation_cases(plan)
    if any(item.get('reuse_quality') for item in plan['candidates'].values()):
        raise ValueError('Historical quality reuse is disabled: full evaluation-time platform collateral identity was not recorded')
    env = clean_environment()
    result = {'scope': 'official_container_candidate_experiments', 'status': 'preflight',
              'started_utc': datetime.now(timezone.utc).isoformat(), 'plan_sha256': digest(args.plan),
              'image_id': plan['baseline']['image_id'], 'threads_per_candidate': threads,
              'jobs': plan['jobs'], 'peak_candidate_threads': threads * plan['jobs'],
              'expected_fixed_drt_end_iter': 2, 'evaluate_cases': evaluate_cases, 'candidates': {}}
    def save(): write_manifest(record_path, result)
    save()
    try:
        image = verify_official_image(env, root / 'official_checksums.log', repository)
        reference = plan['baseline']
        if image['base_source_version'] != reference['openroad_base_commit']:
            raise ValueError('Official base source commit differs from verified v2')
        if image['evaluator_manifest'].get('evaluator_version') != '20260914':
            raise ValueError('Expected official evaluator version 20260914')
        for key, actual in (('evaluator_openroad_sha256', image['evaluator_openroad_sha256']),
                            ('evaluator_launcher_sha256', image['evaluator_sha256'])):
            if actual != reference[key]: raise ValueError('Fixed official evaluator identity changed: ' + key)
        binary = Path(reference['public_binary'])
        if digest(binary) != reference['public_binary_sha256'] or digest(Path(reference['source_zip'])) != reference['source_zip_sha256']:
            raise ValueError('Verified v2 binary or source archive identity changed')
        if digest(Path(reference['verification'])) != reference['verification_sha256']:
            raise ValueError('Verified v2 build report changed')
        build_proof = read_json(Path(reference['verification']))
        if reference['scope'] in ('verified_official_fresh_build_reference', 'verified_official_incremental_build_reference'):
            if build_proof.get('status') != 'complete' or build_proof.get('exit_code') != 0:
                raise ValueError('Referenced official fresh build failed')
            if reference['scope'] == 'verified_official_incremental_build_reference':
                parent = reference['verified_incremental_parent']
                parent_path = Path(parent['report'])
                if build_proof.get('fresh_build') is not False or build_proof.get('build_kind') != 'incremental_verified_full_build_clone' or digest(parent_path) != parent['report_sha256']:
                    raise ValueError('Referenced incremental build ancestry is invalid')
                previous = read_json(parent_path)
                if previous.get('status') != 'complete' or previous.get('fresh_build') is not True or previous.get('exit_code') != 0:
                    raise ValueError('Referenced incremental parent was not a completed fresh build')
                if previous['image_id'] != reference['image_id'] or previous['openroad_base_commit'] != reference['openroad_base_commit']:
                    raise ValueError('Referenced incremental parent image/base changed')
                if previous['public_binary_sha256'] != parent['binary_sha256'] or previous['source_zip_sha256'] != parent['source_zip_sha256']:
                    raise ValueError('Referenced incremental parent identity differs')
            elif build_proof.get('fresh_build') is not True:
                raise ValueError('Referenced fresh build was not fresh')
            expected = {'image_id': reference['image_id'], 'openroad_base_commit': reference['openroad_base_commit'],
                        'source_zip_sha256': reference['source_zip_sha256'], 'public_binary_sha256': reference['public_binary_sha256'],
                        'overlay_file_sha256': reference['overlay_file_sha256']}
            if any(build_proof.get(key) != value for key, value in expected.items()):
                raise ValueError('Referenced official build provenance differs from reuse reference')
            if digest(Path(reference['export_parity_report'])) != reference['export_parity_report_sha256']:
                raise ValueError('Export parity report changed')
        else:
            if build_proof.get('status') != 'complete' or build_proof.get('build', {}).get('status') != 'complete':
                raise ValueError('Referenced v2 official build was not completed')
            if build_proof['build']['binary_sha256'] != reference['public_binary_sha256'] or build_proof['archive_sha256'] != reference['source_zip_sha256']:
                raise ValueError('Referenced v2 build provenance differs from reuse reference')
        result['container'] = image
        inputs = Path(plan['input_root'])
        platform = inputs / 'platforms/nangate45_3D'
        result['input_platform_sha256'] = platform_fingerprint(platform)
        result['input_sha256'] = {case: {name: digest(inputs / 'cases' / case / 'grt_input' / name)
            for name in ('4_1_cts.def', '4_cts.sdc')} for case in plan['cases']}
        if 'bp_fe' in plan['cases'] and result['input_sha256']['bp_fe'] != reference['bp_fe_input_sha256']:
            raise ValueError('bp_fe input differs from the verified v2 baseline')
        # All builds finish before the candidate pool starts, avoiding overlap.
        for label, candidate in plan['candidates'].items():
            directory = root / 'candidates' / label
            archive = directory / 'source.zip'
            if digest(archive) != candidate['source_zip_sha256']:
                raise ValueError('Candidate source snapshot changed: ' + label)
            source = directory / 'source'
            unpack_zip(archive, source)
            fingerprint = overlays(source)
            if fingerprint != candidate['overlay_file_sha256']:
                raise ValueError('Candidate overlay snapshot changed: ' + label)
            reuse = bool(fingerprint) and fingerprint == reference['overlay_file_sha256']
            record = {'status': 'prepared', 'source_zip_sha256': digest(archive),
                      'source_dir': str(source), 'overlay_file_sha256': fingerprint,
                      'config_sha256': digest(source / 'flow_scripts/scripts_3D/mls_config.json'),
                      'binary_reused': reuse, 'cases': {case: {'status': 'queued'} for case in plan['cases']}}
            result['candidates'][label] = record
            save()
            if reuse:
                record.update(public_binary=str(binary), public_binary_sha256=reference['public_binary_sha256'],
                              build={'status': 'reused_identical_overlay_files', 'build_executed': False})
            else:
                build_root = directory / 'fresh_build'
                if build_root.exists(): raise ValueError('Build directory was not fresh')
                build_env = dict(env, OPENROAD_BASE_ROOT=str(BASE), SUBMISSION_BUILD_DIR=str(build_root))
                record['status'] = 'building'; save()
                build = run_stage(['bash', str(source / 'build.sh'), str(plan['build_threads'])], build_env,
                                  directory / 'build.log', repository)
                built = build_root / 'openroad-build/bin/openroad'
                record['build'] = dict(build, build_executed=True, fresh_build=True)
                if build['exit_code'] or not built.is_file() or not os.access(built, os.X_OK):
                    raise RuntimeError('Fresh candidate source build failed: ' + label)
                record.update(public_binary=str(built), public_binary_sha256=digest(built))
            record['status'] = 'routing'; save()

        def route(label: str, case: str) -> tuple:
            parent = result['candidates'][label]
            source = Path(parent['source_dir'])
            directory = root / 'candidates' / label / 'cases' / case
            directory.mkdir(parents=True)
            candidate = directory / 'submission'; candidate.mkdir()
            record = {'status': 'routing', 'candidate_dir': str(candidate)}
            try:
                route_env = dict(env, OPENROAD_EXE=parent['public_binary'], MLS_ENABLE='0' if plan['candidates'][label]['baseline_mode'] else '1')
                record['grt'] = run_stage(['bash', str(source / 'run.sh'), str(inputs / 'cases' / case / 'grt_input'),
                    str(candidate), str(platform), str(threads)], route_env, directory / 'grt.log', repository)
                if record['grt']['exit_code']: raise RuntimeError('Public GRT failed')
                manifest = read_json(candidate / 'run_manifest.json')
                if manifest['openroad_exe'] != parent['public_binary'] or manifest['threads'] != threads or manifest['input_sha256'] != result['input_sha256'][case]['4_1_cts.def']:
                    raise ValueError('Unexpected public GRT engine/thread/input')
                if manifest['mls_enabled'] != (not plan['candidates'][label]['baseline_mode']):
                    raise ValueError('Unexpected MLS mode')
                record.update(routing_manifest=manifest, source_odb_sha256=digest(candidate / '5_1_grt.odb'))
                canonical = directory / 'canonical'; canonical.mkdir()
                snapshot_env = dict(env, EVAL_SUBMISSION_ODB=str(candidate / '5_1_grt.odb'),
                    EVAL_SNAPSHOT_DEF=str(canonical / 'submission.def'), EVAL_SNAPSHOT_GUIDE=str(canonical / 'route.guide'),
                    EVAL_SNAPSHOT_ODB=str(canonical / '5_1_grt.odb'))
                record['snapshot'] = run_stage([str(EVALUATOR / 'bin/openroad_eval'), '-exit', '-no_init',
                    str(VALIDATION / 'snapshot_submission.tcl')], snapshot_env, directory / 'snapshot.log', repository)
                if record['snapshot']['exit_code']: raise RuntimeError('Official snapshot failed')
                original_hashes = {name: digest(canonical / name) for name in ('submission.def', 'route.guide', '5_1_grt.odb')}
                record['canonical_sha256'] = original_hashes
                record['legality_stage'] = run_stage(['python3', str(VALIDATION / 'validate_submission.py'),
                    '--reference-def', str(inputs / 'cases' / case / 'grt_input/4_1_cts.def'),
                    '--submission-def', str(canonical / 'submission.def'), '--canonical-guide', str(canonical / 'route.guide'),
                    '--die-list-dir', str(canonical / 'die_net_lists'), '--report', str(directory / 'legality.json')],
                    env, directory / 'legality.log', repository)
                record['legality'] = read_json(directory / 'legality.json')
                if record['legality_stage']['exit_code'] or record['legality'].get('legal') is not True:
                    raise RuntimeError('Official legality failed')
                if {name: digest(canonical / name) for name in original_hashes} != original_hashes:
                    raise ValueError('Canonical files changed during validation')
                expected = plan['candidates'][label].get('expected_canonical', {}).get(case)
                if expected:
                    record['expected_canonical_sha256'] = expected
                    record['canonical_gate_passed'] = all(original_hashes[name] == value for name, value in expected.items())
                    if record['canonical_gate_passed'] is not True:
                        raise ValueError('New routing canonical DEF/guide differs from the required reference; detailed evaluation is withheld')
                record['status'] = 'legal'
            except Exception as error:
                record.update(status='failed', error=str(error))
            return label, case, record

        result['status'] = 'routing_and_legality'; save()
        tasks = [(label, case) for label in result['candidates'] for case in plan['cases']]
        with ThreadPoolExecutor(max_workers=plan['jobs']) as pool:
            futures = [pool.submit(route, label, case) for label, case in tasks]
            for future in as_completed(futures):
                label, case, record = future.result()
                result['candidates'][label]['cases'][case] = record
                print(f'{label}/{case}: {record["status"]}', flush=True); save()

        def evaluate(label: str, case: str) -> tuple:
            record = result['candidates'][label]['cases'][case]
            directory = Path(record['candidate_dir']).parent
            reports = directory / 'evaluation'; reports.mkdir()
            work = directory / 'official_evaluator_work'
            if work.exists(): raise ValueError('Evaluator work directory was not fresh')
            eval_env = dict(env, CONTEST_ROOT=str(repository), WORK_ROOT=str(work),
                MATERIALIZED_OPEN3D=str(work / 'OpenROAD-3D'), CONTEST_EVAL_THREADS=str(threads))
            stage = run_evaluation_with_platform_audit(
                [str(CONTEST), 'evaluate', case, str(inputs), record['candidate_dir'], str(reports)],
                eval_env, directory / 'evaluate.log', repository, work, platform, result['input_platform_sha256'])
            stage.update(evaluator_invoked=True, full_evaluation_completed=False, work_root=str(work), report_dir=str(reports))
            try:
                if stage['exit_code']: raise RuntimeError('Official contest evaluate failed')
                if stage['platform_audit']['status'] != 'complete':
                    raise ValueError('Evaluation-time platform differs from the input or could not be captured')
                metrics = read_json(reports / 'metrics.json'); timing = read_json(reports / '6_report.json')
                if metrics.get('legal') is not True: raise ValueError('Official metrics are not legal')
                for key in ('drc', 'drt_wirelength_um', 'tns_ns', 'wns_ns', 'hbt_count'):
                    if key not in metrics or not math.isfinite(float(metrics[key])): raise ValueError('Invalid official metric: ' + key)
                for key in ('finish__timing__setup__tns', 'finish__timing__setup__ws'):
                    if key not in timing or not math.isfinite(float(timing[key])): raise ValueError('Final STA metric missing: ' + key)
                proof = {}
                for name in ('drt_pass_bottom.log', 'drt_pass_upper.log'):
                    paths = list(work.rglob(name))
                    if len(paths) != 1: raise ValueError('Expected one fixed DRT pass log: ' + name)
                    log_text = paths[0].read_text(errors='replace')
                    match = re.search(r'detailed_route arguments:[^\n]*-droute_end_iter\s+(\d+)\b', log_text)
                    if match is None or int(match.group(1)) != 2: raise ValueError('Actual DRT end_iter is not 2')
                    thread_match = re.search(r'^DRT pass threads:\s+(\d+)\s*$', log_text, re.M)
                    if thread_match is None or int(thread_match.group(1)) != threads:
                        raise ValueError('Actual DRT thread count differs from the captured plan')
                    proof[name] = {'path': str(paths[0]), 'sha256': digest(paths[0]), 'actual_drt_end_iter': 2,
                                   'actual_threads': int(thread_match.group(1))}
                if digest(Path(record['candidate_dir']) / '5_1_grt.odb') != record['source_odb_sha256']:
                    raise ValueError('Submitted ODB changed during evaluation')
                stage.update(full_evaluation_completed=True, metrics=metrics, metrics_sha256=digest(reports / 'metrics.json'),
                    final_sta_sha256=digest(reports / '6_report.json'), actual_drt_end_iter=2, actual_threads=threads,
                    fixed_iteration_log_proof=proof)
            except Exception as error: stage.update(status='failed', error=str(error))
            return label, case, stage

        if not plan['grt_only']:
            result['status'] = 'evaluating'; save()
            with ThreadPoolExecutor(max_workers=plan['jobs']) as pool:
                futures = [pool.submit(evaluate, label, case) for label, candidate in result['candidates'].items()
                           for case in evaluate_cases if candidate['cases'][case]['status'] == 'legal']
                for future in as_completed(futures):
                    label, case, stage = future.result()
                    record = result['candidates'][label]['cases'][case]; record['evaluation'] = stage
                    record['status'] = stage['status'] if stage['status'] in ('complete', 'complete_reused') else 'evaluation_failed'
                    print(f'{label}/{case} evaluation: {record["status"]}', flush=True); save()
        for candidate in result['candidates'].values():
            candidate['status'] = 'complete' if all(record['status'] in ('legal', 'complete', 'complete_reused') for record in candidate['cases'].values()) else 'failed'
        result.update(status='complete' if all(candidate['status'] == 'complete' for candidate in result['candidates'].values()) else 'failed',
                      finished_utc=datetime.now(timezone.utc).isoformat())
        save(); print(f'Official experiment: {record_path}', flush=True)
        return int(result['status'] != 'complete')
    except Exception as error:
        result.update(status='failed', error=str(error), traceback=traceback.format_exc()); save()
        print(f'Experiment failed: {error}; {record_path}', flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
