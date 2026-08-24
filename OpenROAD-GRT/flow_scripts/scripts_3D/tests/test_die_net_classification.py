#!/usr/bin/env python3
"""Regression tests for DEF package-pin die classification."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from die_net_common import (
    classify_all_nets,
    parse_inst_die_map,
    parse_nets,
    parse_pin_die_map,
)
from check_2d_net_guide_layers import check


class PackagePinTest(unittest.TestCase):
    def test_package_pin_layer_drives_classification(self) -> None:
        content = """VERSION 5.8 ;
DESIGN test ;
UNITS DISTANCE MICRONS 2000 ;
COMPONENTS 2 ;
  - u_bottom BUF_bottom + PLACED ( 10000 10000 ) N ;
  - u_upper BUF_upper + PLACED ( 80000 80000 ) N ;
END COMPONENTS
PINS 2 ;
  - io_bottom + NET to_upper + DIRECTION INPUT
    + LAYER metal6 ( 0 0 ) ( 100 100 ) + FIXED ( 0 50000 ) N ;
  - io_upper + NET to_bottom + DIRECTION INPUT
    + LAYER metal19 ( 0 0 ) ( 100 100 ) + FIXED ( 100000 50000 ) N ;
END PINS
NETS 2 ;
  - to_upper ( PIN io_bottom ) ( u_upper A ) + USE SIGNAL ;
  - to_bottom ( PIN io_upper ) ( u_bottom A ) + USE SIGNAL ;
END NETS
END DESIGN
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            def_path = Path(temp_dir) / "design.def"
            def_path.write_text(content, encoding="utf-8")

            pin_die_map = parse_pin_die_map(def_path)
            nets = parse_nets(def_path)
            classification = classify_all_nets(
                nets,
                parse_inst_die_map(def_path),
                pin_die_map,
            )

        self.assertEqual(pin_die_map, {"io_bottom": "bottom", "io_upper": "upper"})
        self.assertEqual(classification, {"to_upper": "3d", "to_bottom": "3d"})
        self.assertIn(("PIN", "io_bottom"), {(pin.inst, pin.pin) for pin in nets[0].pins})

    def test_package_pin_layer_is_used_by_guide_check(self) -> None:
        content = """VERSION 5.8 ;
DESIGN test ;
COMPONENTS 2 ;
  - u_bottom BUF_bottom + PLACED ( 10000 10000 ) N ;
  - u_upper BUF_upper + PLACED ( 80000 80000 ) N ;
END COMPONENTS
PINS 2 ;
  - io_bottom + NET bottom_net + LAYER metal6 ( 0 0 ) ( 100 100 ) ;
  - io_upper + NET upper_net + LAYER metal19 ( 0 0 ) ( 100 100 ) ;
END PINS
NETS 2 ;
  - bottom_net ( PIN io_bottom ) ( u_bottom A ) ;
  - upper_net ( PIN io_upper ) ( u_upper A ) ;
END NETS
END DESIGN
"""
        guide = """bottom_net
(
0 0 4200 4200 metal11
)
upper_net
(
0 0 4200 4200 metal10
)
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            def_path = Path(temp_dir) / "design.def"
            guide_path = Path(temp_dir) / "route.guide"
            def_path.write_text(content, encoding="utf-8")
            guide_path.write_text(guide, encoding="utf-8")
            classification, violations = check(guide_path, def_path)

        self.assertEqual(classification["bottom_net"], "2d_bottom")
        self.assertEqual(classification["upper_net"], "2d_upper")
        self.assertEqual(violations, {"bottom_net": [11], "upper_net": [10]})


if __name__ == "__main__":
    unittest.main()
