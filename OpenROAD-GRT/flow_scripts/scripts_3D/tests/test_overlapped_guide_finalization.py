#!/usr/bin/env python3
"""Execute fused finalization with real validators and delayed child barriers."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT_DIR = Path(os.environ.get('MLS_TEST_SCRIPT_DIR', Path(__file__).resolve().parents[1]))
SOURCE = (SCRIPT_DIR / 'global_route_single_process.tcl').read_text()
STAGE = SOURCE[SOURCE.index('proc fused_stage '):SOURCE.index('proc fused_plan_layer_hints ')]
FINALIZE = SOURCE[SOURCE.index('set fused_guide $::env(RESULTS_DIR)/route.guide'):]


@unittest.skipUnless(shutil.which('tclsh'), 'Tcl interpreter unavailable')
class OverlappedFinalizationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix='fused checks ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'results'
        self.results.mkdir()
        self.scripts = self.root / 'scripts'
        self.scripts.mkdir()
        (self.results / 'design.def').write_text('''COMPONENTS 2 ;
- HBT_one HBT_BOTIN + PLACED ( 10 10 ) N ;
- cell_bottom BUF_bottom + PLACED ( 10 10 ) N ;
END COMPONENTS
NETS 1 ;
- split_BOT ( HBT_one BOT ) ( cell_bottom A ) ;
END NETS
''')
        (self.scripts / 'merge_route_guides.py').write_text('''import os, sys
from pathlib import Path
if os.environ.get('FIXTURE_FAILURE') == 'merge':
    raise RuntimeError('mock merge failure')
Path(sys.argv[1]).write_text(os.environ['FIXTURE_GUIDE'])
''')
        # Keep both production checkers unchanged. The wrapper makes overlap
        # observable without relying on timing differences or sleeps in tests.
        (self.scripts / 'validate_die_guides.py').write_text('''import os, runpy, sys, time
from pathlib import Path
root = Path(os.environ['RESULTS_DIR'])
def record(value):
    with (root / 'events').open('a') as stream:
        stream.write(value + '\\n')
def unpublished():
    assert not (root / '5_1_grt.odb').exists(), 'ODB published before validation'
    assert not (root / '.grt_finalize_complete').exists(), 'marker published before validation'
record('check_start')
(root / '.checker_started').touch()
unpublished()
if os.environ['FIXTURE_OVERLAP'] == '1':
    deadline = time.monotonic() + 4
    while not (root / '.finalizer_done').exists():
        if time.monotonic() > deadline:
            raise RuntimeError('finalizer did not overlap the validator')
        time.sleep(0.005)
unpublished()
status = 0
try:
    runpy.run_path(os.environ['FIXTURE_REAL_VALIDATOR'], run_name='__main__')
except SystemExit as error:
    status = error.code or 0
unpublished()
record('check_done:' + str(status))
if os.environ.get('FIXTURE_ZERO_STDERR') == '1':
    print('mock stderr with successful check exit', file=sys.stderr)
if os.environ.get('FIXTURE_LARGE_REPORT') == '1':
    print('LARGE_REPORT_' + 'x' * 300000)
raise SystemExit(status)
''')
        self.tcl = self.root / 'run.tcl'
        self.tcl.write_text(STAGE + r'''
proc event {value} {
  set stream [open $::env(RESULTS_DIR)/events a]
  puts $stream $value
  close $stream
}
proc finalizer_done {} {
  close [open $::env(RESULTS_DIR)/.finalizer_done w]
}
proc read_guides {path} {
  if {$::env(FIXTURE_OVERLAP) eq "1"} {
    set deadline [expr {[clock milliseconds] + 4000}]
    while {![file exists $::env(RESULTS_DIR)/.checker_started]} {
      if {[clock milliseconds] > $deadline} {error "Checker was not started before read_guides"}
      after 5
    }
  }
  event read_guides
  if {$::env(FIXTURE_FAILURE) eq "read"} {
    finalizer_done
    error "mock read_guides failure"
  }
}
proc write_db {path} {
  if {$path eq "$::env(RESULTS_DIR)/5_1_grt.odb"} {error "ODB was not staged"}
  event write_db
  set stream [open $path w]
  puts -nonewline $stream "fresh routed ODB"
  close $stream
  finalizer_done
  if {$::env(FIXTURE_FAILURE) eq "write"} {error "mock write_db failure"}
}
namespace eval grt {proc clear_net_routing_layers {} {}}
proc set_routing_layers {args} {}
set fused_script_dir $::env(FIXTURE_SCRIPTS)
set fused_input_def $::env(RESULTS_DIR)/design.def
set fused_classification_cache $::env(RESULTS_DIR)/missing_cache.json
set fused_bottom_guide unused_bottom.guide
set fused_upper_guide unused_upper.guide
set fused_track_patterns {}
set fused_net_sigtypes {}
set fused_layer_adjustments {}
set fused_bot_min metal2
set fused_top_max metal20
''' + FINALIZE)

    def invoke(self, *, guide='split_BOT\n(\n0 0 100 100 metal10\n)\n',
               mode='parallel', cores='3', failure='', validate=True,
               large=False, zero_stderr=False) -> subprocess.CompletedProcess[str]:
        # Old artifacts must not survive an unsuccessful attempt.
        (self.results / '5_1_grt.odb').write_text('stale ODB')
        (self.results / '.grt_finalize_complete').write_text('stale marker')
        overlap = validate and mode == 'parallel' and cores == '3'
        env = dict(os.environ, RESULTS_DIR=str(self.results), FIXTURE_SCRIPTS=str(self.scripts),
                   FIXTURE_REAL_VALIDATOR=str(SCRIPT_DIR / 'validate_die_guides.py'),
                   FIXTURE_GUIDE=guide, FIXTURE_OVERLAP=str(int(overlap)),
                   FIXTURE_FAILURE=failure, GRT_CHECK_MODE=mode, NUM_CORES=cores,
                   VALIDATE_DIE_GUIDES='1' if validate else '0',
                   FIXTURE_LARGE_REPORT=str(int(large)), FIXTURE_ZERO_STDERR=str(int(zero_stderr)))
        env.pop('WORK_HOME', None)
        return subprocess.run(['tclsh', str(self.tcl)], text=True, capture_output=True,
                              env=env, check=False, timeout=10)

    def events(self) -> list[str]:
        return (self.results / 'events').read_text().splitlines()

    def assert_unpublished(self) -> None:
        self.assertFalse((self.results / '5_1_grt.odb').exists())
        self.assertFalse((self.results / '.grt_finalize_complete').exists())
        self.assertFalse(list(self.results.glob('.5_1_grt.*.tmp.odb')))
        self.assertFalse(list(self.results.glob('.guide_checks.*.stderr')))

    def test_checks_overlap_finalization_and_gate_publication(self) -> None:
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.events(), ['check_start', 'read_guides', 'write_db', 'check_done:0'])
        self.assertIn('GRT_CHECK_SCHEDULE overlap', result.stdout)
        self.assertIn('STRICT PASS', result.stdout)
        self.assertEqual((self.results / '5_1_grt.odb').read_text(), 'fresh routed ODB')
        self.assertEqual((self.results / '.grt_finalize_complete').read_text(), 'odb_size=16\n')
        self.assertFalse(list(self.results.glob('.5_1_grt.*.tmp.odb')))

    def test_both_actual_check_failures_are_retained_and_no_odb_is_published(self) -> None:
        result = self.invoke(guide='split_BOT\n(\n0 0 100 100 metal11\n)\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('check_guide_layers failed', result.stdout + result.stderr)
        self.assertIn('check_guide_connectivity failed', result.stdout + result.stderr)
        self.assertEqual(self.events(), ['check_start', 'read_guides', 'write_db', 'check_done:1'])
        self.assert_unpublished()

    def test_connectivity_failure_after_layer_success_blocks_publication(self) -> None:
        result = self.invoke(guide='split_BOT\n(\n10000 10000 11000 11000 metal10\n)\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('PASS: no cross-die', result.stdout)
        self.assertIn('check_guide_connectivity failed', result.stdout + result.stderr)
        self.assert_unpublished()

    def test_failed_finalization_still_joins_checkers_and_removes_partial_odb(self) -> None:
        for failure in ('read', 'write'):
            with self.subTest(failure=failure):
                # Separate executions in each subtest retain their own artifacts.
                for path in self.results.glob('.*'):
                    path.unlink()
                (self.results / 'events').unlink(missing_ok=True)
                result = self.invoke(failure=failure)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'mock {"read_guides" if failure == "read" else "write_db"} failure', result.stderr)
                self.assertEqual(self.events()[-1], 'check_done:0')
                self.assert_unpublished()

    def test_simultaneous_finalizer_and_checker_failures_are_both_reported(self) -> None:
        result = self.invoke(failure='write', guide='split_BOT\n(\n0 0 100 100 metal11\n)\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mock write_db failure', result.stderr)
        self.assertIn('Guide validation also failed', result.stderr)
        self.assertIn('check_guide_layers failed', result.stdout + result.stderr)
        self.assertEqual(self.events()[-1], 'check_done:1')
        self.assert_unpublished()

    def test_serial_and_small_core_budgets_validate_before_finalizing(self) -> None:
        for mode, cores in (('serial', '3'), ('parallel', '1'), ('parallel', '2')):
            with self.subTest(mode=mode, cores=cores):
                (self.results / 'events').unlink(missing_ok=True)
                result = self.invoke(mode=mode, cores=cores)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.events(), ['check_start', 'check_done:0', 'read_guides', 'write_db'])
                self.assertIn('GRT_CHECK_SCHEDULE before_finalize', result.stdout)

    def test_disabled_validation_preserves_explicit_bypass(self) -> None:
        result = self.invoke(validate=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.events(), ['read_guides', 'write_db'])
        self.assertTrue((self.results / '.grt_finalize_complete').exists())

    def test_large_child_report_is_drained_without_deadlock(self) -> None:
        result = self.invoke(large=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('LARGE_REPORT_' + 'x' * 300000, result.stdout)
        self.assertTrue((self.results / '.grt_finalize_complete').exists())

    def test_successful_exit_with_stderr_preserves_exec_failure_contract(self) -> None:
        result = self.invoke(zero_stderr=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mock stderr with successful check exit', result.stderr)
        self.assertEqual(self.events()[-1], 'check_done:0')
        self.assert_unpublished()

    def test_failed_merge_clears_stale_completion_and_output_before_starting_child(self) -> None:
        result = self.invoke(failure='merge')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('mock merge failure', result.stderr)
        self.assertFalse((self.results / 'events').exists())
        self.assert_unpublished()

    def test_invalid_checker_mode_fails_before_finalization_and_clears_stale_output(self) -> None:
        result = self.invoke(mode='invalid')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('read_guides', self.events())
        self.assert_unpublished()


if __name__ == '__main__':
    unittest.main()
