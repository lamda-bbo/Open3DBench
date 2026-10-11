#!/usr/bin/env python3
"""Validate ordinary-net selection, deterministic bounds and Tcl quoting."""
import copy
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plan_net_layer_hints import emit_layer_hints, plan_layer_hints, shared_original_nets


def example(name="long_control", die="bottom", fanout=512, span=400000):
    pins = [{"inst": "driver_" + die, "pin": "Z", "x": 0, "y": 0,
             "io": "OUTPUT", "die": die, "hbt": False}]
    pins += [{"inst": "sink_" + str(i) + "_" + die, "pin": "A", "x": span,
              "y": 0, "io": "INPUT", "die": die, "hbt": False} for i in range(fanout)]
    return {"name": name, "pins": pins, "signal_type": "SIGNAL", "special": False}


def manifest(nets):
    return {"dbu_per_micron": 1000, "nets": nets}


class LayerHintTest(unittest.TestCase):
    def test_disabled_default_and_empty_budget_emit_empty_dictionary(self):
        for cfg in (None, {"enabled": True, "max_nets": 0}):
            result = plan_layer_hints(manifest([example()]), cfg)
            self.assertEqual(result["selected"], [])
            self.assertNotIn("dict set", emit_layer_hints(result))

    def test_both_thresholds_apply_and_ranges_match_die_rc_order(self):
        nets = [example("bottom"), example("upper", "upper"),
                example("low_fanout", fanout=511), example("short", span=399999)]
        design = manifest(nets)
        before = copy.deepcopy(design)
        result = plan_layer_hints(design, {"enabled": True})
        self.assertEqual(design, before)
        self.assertEqual([(n["net"], n["min_layer"], n["max_layer"]) for n in result["selected"]],
                         [("bottom", 4, 10), ("upper", 11, 17)])
        self.assertEqual(result["stats"]["selected_by_die"], {"bottom": 1, "upper": 1})

    def test_rejects_clock_special_cross_die_hbt_package_and_split_nets(self):
        changes = [lambda n: n.update(signal_type="CLOCK"),
                   lambda n: n.update(signal_type="POWER"),
                   lambda n: n.update(special=True),
                   lambda n: n.update(name="ordinary_BOT"),
                   lambda n: n.update(name="ordinary__MLS__S0__BOT"),
                   lambda n: n["pins"][1].update(hbt=True),
                   lambda n: n["pins"][1].update(inst="HBT_0"),
                   lambda n: n["pins"][1].update(inst="LS_HBT_0"),
                   lambda n: n["pins"][1].update(inst="PIN"),
                   lambda n: n["pins"][1].update(die="upper"),
                   lambda n: n["pins"][1].update(die=None),
                   lambda n: n["pins"][1].update(io="OUTPUT"),
                   lambda n: n["pins"][1].update(io="INOUT"),
                   lambda n: n["pins"][1].update(pin="CK"),
                   lambda n: n["pins"][1].update(pin="CLK"),
                   lambda n: n["pins"][1].update(pin="clk")]
        for change in changes:
            net = example()
            change(net)
            self.assertEqual(plan_layer_hints(manifest([net]), {"enabled": True})["selected"], [])

    def test_priority_budget_and_name_ties_are_input_order_independent(self):
        nets = [example("z"), example("a"), example("largest", span=600000)]
        cfg = {"enabled": True, "max_nets": 2}
        first = plan_layer_hints(manifest(nets), cfg)
        self.assertEqual(first, plan_layer_hints(manifest(list(reversed(nets))), cfg))
        self.assertEqual([r["net"] for r in first["selected"]], ["largest", "a"])

    def test_deleted_mls_original_cannot_consume_a_live_net_budget_slot(self):
        nets = [example("deleted", fanout=600), example("live_z"), example("live_a")]
        excluded = shared_original_nets({"selected": [{"original": "deleted"}]})
        for order in (nets, list(reversed(nets))):
            with self.subTest(order=[net["name"] for net in order]):
                result = plan_layer_hints(manifest(order),
                                          {"enabled": True, "max_nets": 1}, excluded)
                self.assertEqual([row["net"] for row in result["selected"]], ["live_a"])
                self.assertEqual(result["stats"]["candidate_nets"], 2)
                self.assertEqual(result["stats"]["skipped"]["shared_original"], 1)

    def test_applied_plan_requires_unambiguous_original_net_names(self):
        self.assertEqual(shared_original_nets({"selected": []}), set())
        self.assertEqual(shared_original_nets({"selected": [{"original": "literal[3]"}]}),
                         {"literal[3]"})
        for malformed in ({}, {"selected": None}, {"selected": {}},
                          {"selected": [None]}, {"selected": [{}]},
                          {"selected": [{"original": ""}]},
                          {"selected": [{"original": 1}]},
                          {"selected": [{"original": "same"}, {"original": "same"}]}):
            with self.subTest(plan=malformed), self.assertRaises(ValueError):
                shared_original_nets(malformed)

    @unittest.skipUnless(shutil.which("tclsh"), "Tcl is not installed")
    def test_tcl_round_trip_does_not_execute_net_names(self):
        hostile = 'net[error HARM];$value\\"\n☃'
        result = plan_layer_hints(manifest([example(hostile)]), {"enabled": True})
        program = emit_layer_hints(result) + '\nputs [dict size $::grt_layer_hints]\n'
        program += 'puts [lindex [dict values $::grt_layer_hints] 0]\n'
        run = subprocess.run([shutil.which("tclsh")], input=program, text=True,
                             capture_output=True, check=True)
        self.assertEqual(run.stderr, "")
        self.assertEqual(run.stdout.splitlines(), ["1", "metal4 metal10"])

    def test_configuration_validation(self):
        for cfg in ({"enabled": "true"}, {"min_fanout": True}, {"min_fanout": 1},
                    {"min_hpwl_um": 0}, {"min_hpwl_um": float("nan")},
                    {"max_nets": -1}, {"max_nets": False}, {"unknown": 1}):
            with self.subTest(cfg=cfg), self.assertRaises(ValueError):
                plan_layer_hints(manifest([example()]), cfg)


if __name__ == "__main__":
    unittest.main()
