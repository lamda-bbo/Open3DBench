"""Regression for preserving thermal source power, independent of STA installation.

Run with python3 -m unittest discover -s test -p test_thermal_power_no_filter.py.
THERMAL_POWER_SCRIPT may select an alternate script for negative-control testing.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SCRIPT = Path(os.environ.get('THERMAL_POWER_SCRIPT',
              Path(__file__).resolve().parents[1] / 'HotSpot/scripts/run_report_power.tcl'))

MOCK_STA = r'''
set env(HOTSPOT_OUTPUT) [lindex $argv 1]
set env(NAME) [lindex $argv 2]
foreach key {FINAL_V FINAL_SDC FINAL_SPEF} { set env($key) unused }
foreach command {read_liberty read_verilog link_design read_sdc read_spef set_power_activity} {
    proc $command {args} {}
}
proc report_power {args} {
    set instances [lindex $args 1]
    set file [open [lindex $args end] a]
    puts $file "   Internal  Switching    Leakage      Total"
    puts $file "      Power      Power      Power      Power (Watts)"
    puts $file "--------------------------------------------"
    foreach instance $instances {
        switch -- $instance {
            max_cap_high { set p 0.02 }
            ram_high { set p 0.003 }
            ordinary { set p 0.0005 }
            max_cap_low { set p 0.001 }
            renamed_high { set p 0.02 }
            default { error "Unexpected test instance: $instance" }
        }
        puts $file [format "   %.2e   0.00e+00   0.00e+00   %.2e %s" $p $p $instance]
    }
    close $file
}
source [lindex $argv 0]
'''


@unittest.skipUnless(shutil.which('tclsh'), 'tclsh is required')
class ThermalPowerRetention(unittest.TestCase):
    def run_case(self, design, high_name='max_cap_high'):
        with tempfile.TemporaryDirectory(prefix='thermal-power-regression-') as tmp:
            root = Path(tmp)
            (root/'mock_sta.tcl').write_text(MOCK_STA)
            (root/'Grid_(0, 0).txt').write_text(high_name+' ram_high ordinary max_cap_low')
            (root/'Grid_(9, 9).txt').write_text('ram_high')
            (root/'Grid_(5, 5).txt').write_text('')
            result = subprocess.run(['tclsh', str(root/'mock_sta.tcl'), str(SCRIPT),
                                     str(root), design], cwd=tmp, capture_output=True,
                                    text=True, check=True)
            names, values = (root/'gcc.ptrace').read_text().splitlines()
            trace = dict(zip(names.split(), map(float, values.split())))
            self.assertEqual(set(trace), {'Grid_0_0', 'Grid_5_5', 'Grid_9_9'})
            self.assertAlmostEqual(trace['Grid_0_0'], .245)
            self.assertAlmostEqual(trace['Grid_9_9'], .03)
            self.assertEqual(trace['Grid_5_5'], 0)
            self.assertAlmostEqual(sum(trace.values()), .275)
            self.assertNotIn('Removing high-power', result.stdout)
            self.assertNotIn('Finding cell:', result.stdout)
            return trace

    def test_bp_fe_keeps_ram_and_high_power_buffers(self):
        self.run_case('bp_fe_top')

    def test_other_design_keeps_high_power_buffers(self):
        self.run_case('bp_be_top')

    def test_instance_and_design_names_do_not_change_power(self):
        self.assertEqual(self.run_case('bp_fe_top'),
                         self.run_case('another_design', 'renamed_high'))


if __name__ == '__main__':
    unittest.main()
