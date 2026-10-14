#!/usr/bin/env python3
"""Regression tests for DEF package-pin die classification."""

from __future__ import annotations

import sys
import contextlib
import io
import itertools
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from die_net_common import (
    PinRef,
    classify_all_nets,
    classify_net_connections,
    classify_net_pins,
    iter_nets,
    parse_inst_die_map,
    parse_nets,
    parse_pin_die_map,
)
from check_2d_net_guide_layers import check
from export_die_net_lists import main as export_main
from unittest.mock import patch


class PackagePinTest(unittest.TestCase):
    def test_raw_classifier_matches_set_based_pin_oracle(self) -> None:
        # Exercise ordinary BOT/TOP pins, package-pin precedence, both HBT
        # prefixes, unknown dies and conflicting suffixes independently of
        # the optimized raw classifier's boolean state updates.
        inst_dies = {"lo": "bottom", "hi": "upper", "odd": "other",
                     "HBT_a": "upper", "LS_HBT_b": "bottom"}
        pin_dies = {"io_lo": "bottom", "io_hi": "upper", "BOT": "upper"}
        connections = [("lo", "A"), ("hi", "A"), ("odd", "A"),
                       ("absent", "A"), ("lo", "TOP"), ("hi", "BOT"),
                       ("PIN", "io_lo"), ("PIN", "io_hi"), ("PIN", "BOT"),
                       ("PIN", "absent"), ("HBT_a", "BOT"),
                       ("HBT_a", "TOP"), ("HBT_a", "A"),
                       ("LS_HBT_b", "BOT"), ("LS_HBT_b", "TOP")]
        for count in range(4):
            for pins in itertools.product(connections, repeat=count):
                refs = tuple(PinRef(inst=inst, pin=pin) for inst, pin in pins)
                for name in ("plain", "forced_BOT", "forced_TOP"):
                    self.assertEqual(
                        classify_net_connections(name, pins, inst_dies, pin_dies),
                        classify_net_pins(name, refs, inst_dies, pin_dies),
                        (name, pins),
                    )

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
            self.assertEqual(
                classify_all_nets(iter_nets(def_path), parse_inst_die_map(def_path),
                                  pin_die_map),
                classification,
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

    def test_streamed_export_preserves_pin_count_duplicates_and_classification(self) -> None:
        content = """COMPONENTS 2 ;
  - u_bottom BUF_bottom + PLACED ( 10000 10000 ) N ;
  - u_upper BUF_upper + PLACED ( 80000 80000 ) N ;
END COMPONENTS
PINS 1 ;
  - io_bottom + NET crossing + LAYER metal6 ( 0 0 ) ( 100 100 ) ;
END PINS
NETS 7 ;
  - bottom_net ( u_bottom A ) ( u_bottom Y ) ;
  - repeated ( u_bottom A ) ( u_bottom Y ) ;
  - repeated ( u_upper A ) ( u_upper Y ) ;
  - single_BOT ( u_bottom A ) ;
  - empty_TOP ;
  - crossing ( PIN io_bottom ) ( u_upper A ) ;
  - unknown ( absent A ) ( absent Y ) ;
END NETS
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            def_path = Path(temp_dir) / "design.def"
            output_dir = Path(temp_dir) / "lists"
            def_path.write_text(content, encoding="utf-8")
            output = io.StringIO()
            with patch.object(sys, "argv", ["export", str(def_path), str(output_dir)]):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(export_main(), 0)
            self.assertEqual((output_dir / "bottom_2d.txt").read_text(), "bottom_net\n")
            self.assertEqual((output_dir / "upper_2d.txt").read_text(), "repeated\n")
            self.assertEqual((output_dir / "special.txt").read_text(),
                             "crossing\nempty_TOP\nsingle_BOT\nunknown\n")
            self.assertIn("bottom=1 upper=2 special=4", output.getvalue())


if __name__ == "__main__":
    unittest.main()
