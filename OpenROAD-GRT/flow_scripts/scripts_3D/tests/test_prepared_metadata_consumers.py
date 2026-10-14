#!/usr/bin/env python3
"""Compare native metadata consumers to the unchanged complete DEF checks."""
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from check_2d_net_guide_layers import check, classify_net_from_def
from diagnose_guide_connectivity import build_net_pins, run_diagnosis
from die_net_common import iter_net_connections
from export_die_net_lists import main as export_main
from prepared_metadata import read_prepared_metadata

DEF = '''COMPONENTS 4 ;
- c_bottom BUF_bottom + PLACED ( 1000 1000 ) N ;
- c_upper BUF_upper + PLACED ( 12000 1000 ) N ;
- HBT_keep HBT_BOTIN + FIXED ( 1000 1000 ) N ;
- HBT_cover HBT_BOTIN + COVER ( 1000 1000 ) N ;
END COMPONENTS
PINS 1 ;
- io + NET io + LAYER metal10 ( 0 0 ) ( 10 10 ) + PLACED ( 1000 1000 ) N ;
END PINS
NETS 7 ;
- io ( PIN io ) ( c_bottom A ) ;
- mixed ( c_bottom A ) ( c_upper A ) ;
- single ( c_bottom A ) ;
- split_BOT ( HBT_keep BOT ) ( c_bottom A ) ;
- split_TOP ( HBT_keep TOP ) ( c_upper A ) ;
- unplaced_BOT ( HBT_cover BOT ) ;
- zero ;
END NETS
'''
GUIDE = '''split_BOT
(
0 0 4200 4200 metal10
)
split_TOP
(
0 0 4200 4200 metal11
8400 0 16800 4200 metal11
4200 0 8400 4200 metal11
)
'''


class PreparedConsumers(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / 'results'
        self.results.mkdir()
        self.def_path = self.results / 'prepared.def'
        self.def_path.write_text(DEF)
        self.guide = self.results / 'route.guide'
        self.guide.write_text(GUIDE)
        self.path = self.results / 'prepared.json'
        classification = classify_net_from_def(self.def_path)
        self.record = {'schema_version': 1, 'compatible': True, 'def_units': 2000,
                       'dbu_per_micron': 2000,
                       'nets': [[n, classification[n], len(p)] for n, p in iter_net_connections(self.def_path)],
                       'split_net_pins': build_net_pins(self.def_path, True)}
        self.fingerprint = self.write_record(self.record)

    def write_record(self, record):
        self.path.write_text(json.dumps(record))
        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def test_all_three_lists_and_counts_match_def_without_reading_a_def(self):
        logs = []
        for label, source, extra in (('def', self.def_path, []),
                                    ('native', self.root / 'not_present.def',
                                     ['--prepared-metadata', str(self.path), '--prepared-metadata-sha256', self.fingerprint])):
            destination = self.root / label
            log = io.StringIO()
            with patch.object(sys, 'argv', ['export', str(source), str(destination), *extra]), contextlib.redirect_stdout(log):
                self.assertEqual(export_main(), 0)
            logs.append(log.getvalue().replace(str(destination), '<directory>'))
        self.assertEqual(logs[0], logs[1])
        for name in ('bottom_2d.txt', 'upper_2d.txt', 'special.txt'):
            self.assertEqual((self.root / 'def' / name).read_bytes(), (self.root / 'native' / name).read_bytes())

    def test_layer_violations_and_complete_diagnostics_match_def(self):
        for guide in (GUIDE, GUIDE.replace('metal10', 'metal11'), GUIDE.replace('0 0 4200 4200', '50000 50000 60000 60000')):
            with self.subTest(guide=guide):
                self.guide.write_text(guide)
                self.assertEqual(check(self.guide, self.def_path),
                                 check(self.guide, self.root / 'missing.def', None, self.path, self.fingerprint))
                expected = run_diagnosis(self.results, 5000, 1000000, True, self.def_path)
                actual = run_diagnosis(self.results, 5000, 1000000, True,
                                      self.root / 'missing.def', self.path, self.fingerprint)
                self.assertEqual(expected, actual)

    def test_real_serial_parallel_validator_reports_and_failures_match(self):
        env = dict(os.environ, NUM_CORES='3')
        env.pop('WORK_HOME', None)
        for guide in (GUIDE, GUIDE.replace('metal10', 'metal11')):
            self.guide.write_text(guide)
            for mode in ('serial', 'parallel'):
                runs = []
                for extra in ([], ['--prepared-metadata', str(self.path), '--prepared-metadata-sha256', self.fingerprint]):
                    runs.append(subprocess.run([sys.executable, str(SCRIPTS / 'validate_die_guides.py'),
                                                str(self.results), '--def-file', str(self.def_path), '--mode', mode, *extra],
                                               env=env, capture_output=True, text=True))
                normalize = lambda text: re.sub(r'^GRT_(?:STAGE|CHECK_MODE).*\n', '', text, flags=re.M)
                self.assertEqual(runs[0].returncode, runs[1].returncode)
                self.assertEqual(normalize(runs[0].stdout), normalize(runs[1].stdout))
                self.assertEqual(runs[0].stderr, runs[1].stderr)

    def test_changed_missing_or_unbound_metadata_fails_closed(self):
        for value in (None, '', True, 123, '0' * 64):
            with self.assertRaises(ValueError):
                read_prepared_metadata(self.path, value)
        changed = copy.deepcopy(self.record)
        changed['split_net_pins'].pop('split_BOT')
        self.write_record(changed)
        with self.assertRaisesRegex(ValueError, 'fingerprint mismatch'):
            run_diagnosis(self.results, 5000, 1000000, True, self.def_path, self.path, self.fingerprint)
        self.path.unlink()
        with self.assertRaises(FileNotFoundError):
            read_prepared_metadata(self.path, self.fingerprint)

    def test_malformed_complete_records_rejected_before_checks(self):
        variants = []
        for field, value in (('schema_version', True), ('compatible', 1), ('def_units', False),
                             ('dbu_per_micron', 0), ('nets', None), ('split_net_pins', [])):
            record = copy.deepcopy(self.record)
            record[field] = value
            variants.append(record)
        for row in (['bad', 'unknown', True], ['a', 'bad', 1], ['a_BOT', '2d_upper', 2]):
            record = copy.deepcopy(self.record)
            record['nets'] = [row]
            variants.append(record)
        for rows in (list(reversed(self.record['nets'])), [self.record['nets'][0]] * 2):
            record = copy.deepcopy(self.record)
            record['nets'] = rows
            variants.append(record)
        for name, points in (('missing_BOT', [['HBT_x', 1, 2]]), ('mixed', [['c_bottom', 1, 2]]),
                             ('split_BOT', [['HBT_x', -1, 2]]), ('split_BOT', [['HBT_x', True, 2]]),
                             ('split_BOT', [['HBT_x', 1, 2]] * 3)):
            record = copy.deepcopy(self.record)
            record['split_net_pins'] = {name: points}
            variants.append(record)
        for record in variants:
            with self.subTest(record=record):
                fingerprint = self.write_record(record)
                with self.assertRaises(ValueError):
                    read_prepared_metadata(self.path, fingerprint)
        self.path.write_text('{"schema_version":1,"compatible":true,"compatible":false}')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            read_prepared_metadata(self.path, hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_probe_requires_explicit_compatible_fallback_and_consumer_rejects_it(self):
        fingerprint = self.write_record({'schema_version': 1, 'compatible': False, 'reason': 'regular_net_wire'})
        result = subprocess.run([sys.executable, str(SCRIPTS / 'prepared_metadata.py'), '--probe', str(self.path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'fallback regular_net_wire\n')
        with self.assertRaises(ValueError):
            read_prepared_metadata(self.path, fingerprint)

    @unittest.skipUnless(shutil.which('tclsh'), 'Tcl interpreter unavailable')
    def test_actual_tcl_dispatch_native_fallback_forced_and_checkpoint(self):
        text = (SCRIPTS / 'global_route_single_process.tcl').read_text()
        body = text[text.index('set fused_input_def '):text.index('set ::env(GRT_INPUT_DEF)')]
        hook = self.root / 'hook.tcl'
        hook.write_text('')
        for mode, available, compatible, checkpoints, success, writes in (
                ('auto', True, True, False, True, 0), ('auto', True, False, False, True, 1),
                ('auto', False, True, False, True, 1), ('def', True, True, False, True, 1),
                ('native', False, True, False, False, 0), ('native', True, False, False, False, 0),
                ('native', True, True, True, True, 1)):
            with self.subTest(mode=mode, available=available, compatible=compatible, checkpoints=checkpoints):
                self.write_record(self.record if compatible else {'schema_version': 1, 'compatible': False, 'reason': 'regular_net_wire'})
                env = dict(os.environ, RESULTS_DIR=str(self.results), GRT_PREPARE_TCL=str(hook),
                           GRT_PREPARED_METADATA=mode, GRT_SAVE_CHECKPOINTS='1' if checkpoints else '0',
                           TEST_METADATA_SOURCE=str(self.path), TEST_SCRIPT_DIR=str(SCRIPTS))
                prelude = '''set fused_script_dir $::env(TEST_SCRIPT_DIR)
set writes 0
proc fused_stage {name script} {uplevel 1 $script}
proc write_db {path} {}
proc write_def {path} {incr ::writes}
namespace eval grt {}
namespace eval ord {
  proc get_db_block {} {return fixture_block}
  proc get_db_tech {} {return fixture_tech}
}
proc fixture_block {method args} {return {}}
proc fixture_tech {method args} {return {}}
'''
                if available:
                    prelude += 'proc grt::export_prepared_routing_metadata {path} {file copy -force $::env(TEST_METADATA_SOURCE) $path}\n'
                tail = '\nif {[catch {\n' + body + '\n} message]} {puts stderr $message; puts "WRITES $writes"; exit 1}\nputs "WRITES $writes"\n'
                result = subprocess.run(['tclsh'], input=prelude + tail, env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
                self.assertIn(f'WRITES {writes}\n', result.stdout)

    @unittest.skipUnless(shutil.which('tclsh'), 'Tcl interpreter unavailable')
    def test_compatibility_guard_uses_original_parser_when_queries_are_unavailable(self):
        guarded = self.root / 'guarded.json'
        script = 'source {' + str(SCRIPTS / 'prepared_metadata.tcl') + '}\n'
        script += 'namespace eval grt {proc export_prepared_routing_metadata {path} {error "backend must not run"}}\n'
        script += 'prepared_metadata::export {' + str(guarded) + '}\n'
        result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(guarded.read_text()), {
            'schema_version': 1, 'compatible': False, 'reason': 'compatibility_query_unavailable'})


if __name__ == '__main__':
    unittest.main()
