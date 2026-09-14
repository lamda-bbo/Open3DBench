"""Dependency-free regression tests; run with python3 -m unittest discover -s test."""
from pathlib import Path
import subprocess
import unittest

FLOW = Path(__file__).resolve().parents[1]


class ResizerConstraints(unittest.TestCase):
    def test_platform_defaults(self):
        result = subprocess.run(
            ['make', '-s', '-f', str(FLOW / 'platforms/nangate45_3D/config.mk'),
             '--eval=check:;@echo $(MAX_FANOUT); echo $(DONT_USE_CELLS)', 'check'],
            check=True, text=True, stdout=subprocess.PIPE)
        lines = result.stdout.splitlines()
        self.assertEqual(lines[0], '32')
        self.assertTrue({'HBT_BOTIN', 'HBT_TOPIN'} <= set(lines[1].split()))

    def test_reapplied_to_each_design_load(self):
        script = '''
set calls {}
proc current_design {} {return test_design}
proc set_max_fanout {value design} {lappend ::calls [list $value $design]}
source {%s}
# Stub external loading operations, exercising the real standalone branch.
proc source {path} {}
proc read_db {path} {}
proc read_sdc {path} {set ::sdc_loaded 1}
set ::env(SCRIPTS_DIR) /unused
set ::env(RESULTS_DIR) /unused
set ::env(PLATFORM_DIR) /unused
unset -nocomplain ::env(MAX_FANOUT)
load_design dummy.odb dummy.sdc first
if {[llength $calls] != 0} {error "Unexpected default for other platforms"}
set ::env(MAX_FANOUT) 32
load_design dummy.odb dummy.sdc second
load_design dummy.odb dummy.sdc third
if {$calls ne {{32 test_design} {32 test_design}}} {error "Constraint not reapplied"}
set ::env(MAX_FANOUT) 64
load_design dummy.odb dummy.sdc override
if {[lindex $calls end] ne {64 test_design}} {error "Override ignored"}
foreach invalid {0 -1 1.5 abc {}} {
  set ::env(MAX_FANOUT) $invalid
  if {![catch {load_design dummy.odb dummy.sdc invalid}]} {error "Invalid limit accepted"}
}
puts TEST_PASS
''' % (FLOW / 'scripts/load.tcl').as_posix()
        result = subprocess.run(['tclsh'], input=script, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.stderr, '')
        self.assertIn('TEST_PASS', result.stdout)


if __name__ == '__main__':
    unittest.main()
