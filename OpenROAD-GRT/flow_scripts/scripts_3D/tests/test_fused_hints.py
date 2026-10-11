#!/usr/bin/env python3
"""Exercise fused/standalone hint outputs and Tcl preparation failure handling."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1]


def fixture():
    nets=[]
    for die in ('bottom','upper'):
        pins=[{'inst':f'driver_{die}','pin':'Z','x':24000,'y':24000,
               'die':die,'io':'OUTPUT','hbt':False}]
        pins += [{'inst':f'sink{i}_{die}','pin':'A',
                  'x':900000+(i%32)*1000,'y':180000+(i//32)*1000,
                  'die':die,'io':'INPUT','hbt':False} for i in range(640)]
        nets.append({'name': 'net[error NOT_RUN];$x\\"_' + die, 'pins':pins,
                     'signal_type':'SIGNAL','special':False,'bterms':False})
    return {'dbu_per_micron':1000,'manufacturing_grid':5,
            'die_area':[0,0,1000000,1000000],'hbt_master_size':[1000,1000],
            'hbts':[{'name':'HBT_legacy','x':6900,'y':13300}], 'nets':nets}


class FusedHintCLITest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        (self.path/'manifest.json').write_text(json.dumps(fixture()))
        (self.path/'protected.json').write_text(json.dumps([fixture()['nets'][1]['name']]))
        (self.path/'config.json').write_text(json.dumps({'multi_branch_enabled':True,
            'relocation_enabled':False,'max_new_hbts':9}))

    def run_planner(self, prefix, options=()):
        cmd=[sys.executable,str(SCRIPT_DIR/'mls_planner.py'),'--manifest',str(self.path/'manifest.json'),
             '--config',str(self.path/'config.json'),'--protected-nets',str(self.path/'protected.json'),
             '--plan',str(self.path/(prefix+'_plan.json')),'--apply-tcl',str(self.path/(prefix+'_apply.tcl')),*map(str,options)]
        return subprocess.run(cmd,text=True,capture_output=True)

    def options(self, prefix, token='valid_nonce_123'):
        return ['--layer-hints-tcl',self.path/(prefix+'_hints.tcl'),
                '--layer-hints-report',self.path/(prefix+'_hints.json'),'--layer-hints-token',token]

    def test_separate_and_fused_cli_outputs_are_byte_identical(self):
        old=self.run_planner('before');self.assertEqual(old.returncode,0,old.stderr)
        hint=subprocess.run([sys.executable,str(SCRIPT_DIR/'plan_net_layer_hints.py'),
            '--manifest',str(self.path/'manifest.json'),'--enable','--mls-plan',str(self.path/'before_plan.json'),
            '--output-tcl',str(self.path/'before_hints.tcl'),'--report-json',str(self.path/'before_hints.json')],
            text=True,capture_output=True)
        self.assertEqual(hint.returncode,0,hint.stderr)
        fused=self.run_planner('after',self.options('after'))
        self.assertEqual(fused.returncode,0,fused.stderr)
        self.assertIn('MLS_LAYER_HINTS_READY valid_nonce_123\n',fused.stdout)
        for suffix in ('_plan.json','_apply.tcl','_hints.tcl','_hints.json'):
            self.assertEqual((self.path/('before'+suffix)).read_bytes(),(self.path/('after'+suffix)).read_bytes(),suffix)
        hints=json.loads((self.path/'after_hints.json').read_text())
        self.assertEqual(hints['stats']['skipped']['shared_original'],1)
        self.assertEqual(hints['stats']['selected_nets'],1)
        self.assertIn('_upper',hints['selected'][0]['net'])

    def test_no_optional_flags_produces_only_the_mls_outputs(self):
        result = self.run_planner('standalone')
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((self.path/'standalone_plan.json').read_text())
        self.assertEqual(json.loads(result.stdout), plan['stats'])
        self.assertTrue((self.path/'standalone_apply.tcl').is_file())
        self.assertNotIn('MLS_LAYER_HINTS', result.stdout)
        self.assertEqual(list(self.path.glob('*hints*')), [])

    def test_partial_output_failure_preserves_mls_and_emits_no_success(self):
        old=self.run_planner('before');self.assertEqual(old.returncode,0,old.stderr)
        (self.path/'after_hints.json').mkdir()
        fused=self.run_planner('after',self.options('after'))
        self.assertEqual(fused.returncode,0,fused.stderr)
        self.assertIn('MLS_LAYER_HINTS_FALLBACK IsADirectoryError',fused.stdout)
        self.assertNotIn('MLS_LAYER_HINTS_READY',fused.stdout)
        self.assertTrue((self.path/'after_hints.tcl').is_file())
        for suffix in ('_plan.json','_apply.tcl'):
            self.assertEqual((self.path/('before'+suffix)).read_bytes(),(self.path/('after'+suffix)).read_bytes())

    def test_optional_argument_validation_precedes_output_writes(self):
        options=[['--layer-hints-token','token'],self.options('x','bad\nmarker'),
                 ['--layer-hints-tcl',self.path/'manifest.json','--layer-hints-report',self.path/'x.json','--layer-hints-token','token']]
        for option in options:
            before=(self.path/'manifest.json').read_bytes()
            result=self.run_planner('after',option)
            self.assertEqual(result.returncode,2,result.stderr)
            self.assertFalse((self.path/'after_plan.json').exists())
            self.assertEqual((self.path/'manifest.json').read_bytes(),before)


@unittest.skipUnless(shutil.which('tclsh'),'Tcl unavailable')
class FusedHintTclTest(unittest.TestCase):
    def invoke(self, *, behavior='ready', mode='single', enabled='1', consume=True, mutation='', prepare=True):
        prep=(SCRIPT_DIR/'prepare_mls.tcl').read_text().rsplit('\nmls_prepare::run',1)[0]
        router=(SCRIPT_DIR/'global_route_single_process.tcl').read_text()
        helper=router[router.index('proc fused_plan_layer_hints {'):router.index('proc fused_snapshot_sigtypes {')]
        stage=router[router.index('set ::grt_layer_hints [dict create]'):router.index('# Keep the pre-GRT metadata')]
        stage='set fused_script_dir $::env(SCRIPTS)\n'+stage
        mock=r'''
namespace eval ord {
  proc get_db {} {return db}
  proc get_db_block {} {return block}
}
namespace eval grt {proc mls_protected_net_names {} {return {}}}
proc master {method} {return 1000}
proc mls_prepare::check_hbt_master {args} {return master}
proc mls_prepare::inst_snapshot {args} {return {}}
proc mls_prepare::bterm_snapshot {args} {return {}}
proc mls_prepare::check_snapshot {args} {
  if {$::env(BEHAVIOR) eq "snapshot_failure"} {error SNAPSHOT_FAILED}
}
proc mls_prepare::use_native_scan {args} {return 1}
proc write_test_file {path contents} {
  set fp [open $path w]; puts -nonewline $fp $contents; close $fp
}
proc mls_prepare::export_manifest {path args} {write_test_file $path "{}\n"}
set ::fallback_calls 0
set ::precompute_requested 0
set ::applied 0
proc option_value {args key} {
  set index [lsearch -exact $args $key]
  if {$index < 0} {return ""}
  return [lindex $args [expr {$index+1}]]
}
rename exec real_exec
proc exec {args} {
  set program [file tail [lindex $args 1]]
  if {$program eq "mls_planner.py"} {
    set token [option_value $args --layer-hints-token]
    set ::precompute_requested [expr {$token ne ""}]
    if {$::env(BEHAVIOR) eq "planner_failure"} {error PLANNER_FAILED}
    set apply [option_value $args --apply-tcl]
    if {$::env(BEHAVIOR) eq "apply_failure"} {
      write_test_file $apply "error APPLY_FAILED\n"
    } else {write_test_file $apply "set ::applied 1\n"}
    write_test_file [option_value $args --plan] "{}\n"
    if {$token ne ""} {
      write_test_file [option_value $args --layer-hints-tcl] "set ::grt_layer_hints {cached {metal4 metal10}}\n"
      write_test_file [option_value $args --layer-hints-report] "{}\n"
      if {$::env(BEHAVIOR) eq "ready" || $::env(BEHAVIOR) in {apply_failure snapshot_failure}} {
        return "{}\nMLS_LAYER_HINTS_READY $token"
      }
      if {$::env(BEHAVIOR) eq "wrong_token"} {return "{}\nMLS_LAYER_HINTS_READY wrong_token"}
      if {$::env(BEHAVIOR) eq "prefix_only"} {return "{}\nextra MLS_LAYER_HINTS_READY $token"}
      return "{}\nMLS_LAYER_HINTS_FALLBACK OSError"
    }
    return "{}"
  }
  if {$program eq "plan_net_layer_hints.py"} {
    incr ::fallback_calls
    if {$::env(BEHAVIOR) eq "fallback_failure"} {error FALLBACK_FAILED}
    write_test_file [option_value $args --output-tcl] "set ::grt_layer_hints {fresh {metal4 metal10}}\n"
    write_test_file [option_value $args --report-json] "{}\n"
    return "{}"
  }
  error "Unexpected program $program"
}
proc fused_stage {name body} {uplevel 1 $body}
# Stale file contents and even a stale global from an earlier invocation are
# deliberately present. Only the current prepare's exact token may authorize reuse.
write_test_file $::env(RESULTS_DIR)/net_layer_hints.tcl "set ::grt_layer_hints {stale {metal4 metal10}}\n"
write_test_file $::env(REPORTS_DIR)/net_layer_hints.json "{}\n"
set ::grt_precomputed_layer_hints [dict create token old tcl stale report stale]
'''
        program=prep+'\n'+helper+'\n'+mock+'\n'
        # Use the actual router reset statement before invoking the preparation hook.
        reset='unset -nocomplain ::grt_precomputed_layer_hints'
        self.assertIn(reset,router)
        program+=reset+'\nset failed 0\n'
        if prepare:
            program+='if {[catch {mls_prepare::run} message]} {puts "ERROR $message"; set failed 1}\n'
        else:
            program+='write_test_file $::env(RESULTS_DIR)/mls_manifest.json "{}\\n"\n'
        program+='puts "PREPARED [info exists ::grt_precomputed_layer_hints]"\n'
        program+=mutation+'\n'
        if consume:
            program+='if {!$failed} {\nif {[catch {\n'+stage+'\n} message]} {puts "ERROR $message"; set failed 1}\n}\n'
        program+='puts "RESULT requested=$::precompute_requested fallback=$::fallback_calls applied=$::applied marker=[info exists ::grt_precomputed_layer_hints] failed=$failed"\n'
        program+='if {[info exists ::grt_layer_hints]} {puts "HINTS [dict keys $::grt_layer_hints]"}\n'
        with tempfile.TemporaryDirectory() as temp:
            env=dict(os.environ,RESULTS_DIR=temp,REPORTS_DIR=temp,SCRIPTS=str(SCRIPT_DIR),
                     GRT_PROCESS_MODE=mode,GRT_HIGH_FANOUT_LAYERS=enabled,BEHAVIOR=behavior)
            for key in ('MLS_CONFIG','MLS_TIMING_CSV','GRT_HIGH_FANOUT_POLICY'):
                env.pop(key,None)
            result=subprocess.run(['tclsh'],input=program,text=True,capture_output=True,env=env)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(result.stderr,'',result.stderr)
        return result.stdout

    def test_success_reuses_current_files_after_apply_and_consumes_marker(self):
        out=self.invoke()
        self.assertIn('PREPARED 1',out)
        self.assertIn('requested=1 fallback=0 applied=1 marker=0 failed=0',out)
        self.assertIn('HINTS cached',out)

    def test_absent_wrong_and_prefixed_marker_all_run_original_fallback(self):
        for behavior in ('no_marker','wrong_token','prefix_only'):
            with self.subTest(behavior=behavior):
                out=self.invoke(behavior=behavior)
                self.assertIn('PREPARED 0',out)
                self.assertIn('fallback=1 applied=1 marker=0 failed=0',out)
                self.assertIn('HINTS fresh',out)

    def test_missing_or_mismatched_outputs_invalidate_marker(self):
        mutations=['file delete $::env(RESULTS_DIR)/net_layer_hints.tcl',
                   'file delete $::env(REPORTS_DIR)/net_layer_hints.json',
                   'dict set ::grt_precomputed_layer_hints report wrong_path',
                   'set ::grt_precomputed_layer_hints malformed_marker',
                   'dict set ::grt_precomputed_layer_hints token ""']
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                out=self.invoke(mutation=mutation)
                self.assertIn('fallback=1 applied=1 marker=0 failed=0',out)
                self.assertIn('HINTS fresh',out)

    def test_disabled_does_not_precompute_or_run_hint_cli(self):
        out=self.invoke(enabled='0')
        self.assertIn('requested=0 fallback=0 applied=1 marker=0 failed=0',out)
        self.assertIn('HINTS \n',out)

    def test_isolated_prepare_does_not_request_precompute(self):
        out=self.invoke(mode='isolated',consume=False)
        self.assertIn('requested=0 fallback=0 applied=1 marker=0 failed=0',out)

    def test_external_preparation_without_marker_keeps_standalone_path(self):
        out=self.invoke(prepare=False)
        self.assertIn('requested=0 fallback=1 applied=0 marker=0 failed=0',out)
        self.assertIn('HINTS fresh',out)

    def test_prepare_failures_never_publish_success(self):
        for behavior in ('planner_failure','apply_failure','snapshot_failure'):
            with self.subTest(behavior=behavior):
                out=self.invoke(behavior=behavior)
                self.assertIn('PREPARED 0',out)
                self.assertIn('marker=0 failed=1',out)
                self.assertIn('fallback=0',out)

    def test_original_fallback_error_still_aborts(self):
        out=self.invoke(behavior='fallback_failure')
        self.assertIn('ERROR FALLBACK_FAILED',out)
        self.assertIn('fallback=1 applied=1 marker=0 failed=1',out)

    def test_success_marker_is_not_reusable_twice(self):
        out=self.invoke(mutation='fused_plan_layer_hints $::env(SCRIPTS)')
        self.assertIn('fallback=1 applied=1 marker=0 failed=0',out)
        self.assertIn('HINTS fresh',out)


if __name__=='__main__':
    unittest.main()
