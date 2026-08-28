#!/usr/bin/env python3
"""Structural regression tests for the optional shared GRT input snapshot."""

from __future__ import annotations

import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]


class SharedInputContractTest(unittest.TestCase):
    def test_default_path_keeps_original_inputs(self) -> None:
        main = (SCRIPT_DIR / "global_route_die_by_die.tcl").read_text(
            encoding="utf-8"
        )

        self.assertIn('set grt_input_odb "4_cts.odb"', main)
        self.assertIn("/4_1_cts.def", main)
        self.assertIn("if {[info exists ::env(GRT_PREPARE_TCL)]", main)

    def test_all_child_processes_use_selected_odb(self) -> None:
        for script_name in (
            "global_route_single_pass.tcl",
            "finalize_die_by_die_grt.tcl",
        ):
            script = (SCRIPT_DIR / script_name).read_text(encoding="utf-8")
            with self.subTest(script=script_name):
                self.assertIn("::env(GRT_INPUT_ODB)", script)
                self.assertIn('"4_cts.odb"', script)
                self.assertIn("load_design $grt_input_odb", script)

    def test_prepared_def_drives_classification_and_validation(self) -> None:
        main = (SCRIPT_DIR / "global_route_die_by_die.tcl").read_text(
            encoding="utf-8"
        )

        self.assertIn("exec python3 $export_py $grt_input_def $list_dir", main)
        self.assertIn("set ::env(GRT_INPUT_DEF) $grt_input_def", main)
        self.assertIn("--def-file $input_def", main)


if __name__ == "__main__":
    unittest.main()
