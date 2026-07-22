#!/usr/bin/env python3
"""Regression tests for DEF I/O and preplaced-HBT handling."""

from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from hbt_placement_greedy import CoreBbox, default_aligned_hbt_grid
from mol_hbt_common import (
    ComponentInfo,
    classify_all_nets,
    parse_components,
    parse_inst_die_map,
    parse_nets,
    parse_pin_die_map,
)
from split_mol_hbt import build_split_plans, rewrite_def


def write_def(path: Path, body: str) -> None:
    path.write_text(
        "VERSION 5.8 ;\n"
        "DESIGN test ;\n"
        "UNITS DISTANCE MICRONS 2000 ;\n"
        "DIEAREA ( 0 0 ) ( 100000 100000 ) ;\n"
        f"{body}"
        "END DESIGN\n",
        encoding="utf-8",
    )


class PackagePinTest(unittest.TestCase):
    def test_package_pin_layer_drives_classification_and_subnet(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            def_path = Path(temp_dir) / "design.def"
            output_path = Path(temp_dir) / "split.def"
            write_def(
                def_path,
                """COMPONENTS 2 ;
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
""",
            )

            inst_die_map = parse_inst_die_map(def_path)
            pin_die_map = parse_pin_die_map(def_path)
            components = parse_components(def_path)
            nets = parse_nets(def_path)
            classification = classify_all_nets(nets, inst_die_map, pin_die_map)

            self.assertEqual(pin_die_map, {"io_bottom": "bottom", "io_upper": "upper"})
            self.assertEqual(classification, {"to_upper": "3d", "to_bottom": "3d"})
            self.assertIn(("PIN", "io_bottom"), {(p.inst, p.pin) for p in nets[0].pins})

            plans, _ = build_split_plans(
                nets,
                inst_die_map,
                components,
                {},
                pin_die_map,
                placement_mode="centroid",
            )
            rewrite_def(def_path, output_path, plans)
            rewritten = output_path.read_text(encoding="utf-8")

            self.assertIn("- io_bottom + NET to_upper_BOT", rewritten)
            self.assertIn("- io_upper + NET to_bottom_TOP", rewritten)
            self.assertIn("( PIN io_bottom )", rewritten)
            self.assertIn("( PIN io_upper )", rewritten)


class PreplacedHbtTest(unittest.TestCase):
    def test_existing_hbt_is_reserved_and_name_is_not_reused(self) -> None:
        grid = default_aligned_hbt_grid()
        existing_x, existing_y = grid.snap_origin(50000, 50000)

        with tempfile.TemporaryDirectory() as temp_dir:
            def_path = Path(temp_dir) / "design.def"
            write_def(
                def_path,
                f"""COMPONENTS 3 ;
  - HBT_BOTIN_0 HBT_BOTIN
    + COVER ( {existing_x} {existing_y} ) N ;
  - driver_bottom BUF_bottom + PLACED ( {existing_x} {existing_y} ) N ;
  - sink_upper BUF_upper + PLACED ( {existing_x} {existing_y} ) N ;
END COMPONENTS
PINS 0 ;
END PINS
NETS 1 ;
  - crossing ( driver_bottom Z ) ( sink_upper A ) + USE SIGNAL ;
END NETS
""",
            )

            components = parse_components(def_path)
            self.assertEqual(
                (components["HBT_BOTIN_0"].x, components["HBT_BOTIN_0"].y),
                (existing_x, existing_y),
            )
            plans, _ = build_split_plans(
                parse_nets(def_path),
                parse_inst_die_map(def_path),
                components,
                {"BUF_bottom": {"Z": "OUTPUT"}},
                parse_pin_die_map(def_path),
                placement_mode="greedy",
                placement_core=CoreBbox(0, 0, 100000, 100000),
            )

            self.assertEqual(len(plans), 1)
            self.assertEqual(plans[0].hbt_inst, "HBT_BOTIN_1")
            distance = math.hypot(
                plans[0].hbt_x - existing_x,
                plans[0].hbt_y - existing_y,
            )
            self.assertGreaterEqual(distance, grid.hbt_pitch_x)

    def test_off_grid_existing_hbt_is_rejected(self) -> None:
        grid = default_aligned_hbt_grid()
        x, y = grid.snap_origin(50000, 50000)
        components = {
            "HBT_BOTIN_0": ComponentInfo(
                inst="HBT_BOTIN_0",
                cell="HBT_BOTIN",
                die="bottom",
                x=x + 1,
                y=y,
            ),
        }
        with self.assertRaisesRegex(ValueError, "off the configured HBT grid"):
            build_split_plans(
                [],
                {},
                components,
                {},
                {},
                placement_mode="greedy",
                placement_core=CoreBbox(0, 0, 100000, 100000),
            )


if __name__ == "__main__":
    unittest.main()
