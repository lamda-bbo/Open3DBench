#!/usr/bin/env python3
"""Bound trunk routing layers for long, high-fanout ordinary signal nets.

This is a geometry/load proxy, not measured timing. The planner is disabled by
default and changes no placement or connectivity. Pin access can still use
same-die layers outside the trunk interval in the router's existing via repair.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path

from mls_planner import tcl_word


DEFAULT_CONFIG = {
    "enabled": False,
    "min_fanout": 512,
    "min_hpwl_um": 400.0,
    "max_nets": 256,
}


def shared_original_nets(plan):
    """Exclude deleted MLS originals before ranking the remaining live nets."""
    selected = plan.get("selected")
    if not isinstance(selected, list):
        raise ValueError("MLS plan selected must be a list")
    names = set()
    for entry in selected:
        if not isinstance(entry, dict) or not isinstance(entry.get("original"), str) or not entry["original"]:
            raise ValueError("MLS plan selected entries require an original net name")
        if entry["original"] in names:
            raise ValueError("Duplicate MLS original net: " + entry["original"])
        names.add(entry["original"])
    return names


def plan_layer_hints(manifest, config=None, excluded_originals=()):
    values = dict(DEFAULT_CONFIG)
    if config:
        unknown = set(config) - set(values)
        if unknown:
            raise ValueError(f"Unknown layer hint keys: {sorted(unknown)}")
        values.update(config)
    if not isinstance(values["enabled"], bool):
        raise ValueError("enabled must be a JSON boolean")
    for key, minimum in (("min_fanout", 2), ("max_nets", 0)):
        value = values[key]
        if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
            raise ValueError(f"{key} must be an integer >= {minimum}")
    span_threshold = values["min_hpwl_um"]
    if (not isinstance(span_threshold, (int, float)) or isinstance(span_threshold, bool)
            or not math.isfinite(span_threshold) or span_threshold <= 0):
        raise ValueError("min_hpwl_um must be finite and positive")
    dbu = manifest["dbu_per_micron"]
    if not isinstance(dbu, (int, float)) or not math.isfinite(dbu) or dbu <= 0:
        raise ValueError("dbu_per_micron must be finite and positive")
    result = {"version": 1, "config": values, "selected": [],
              "stats": {"input_nets": len(manifest["nets"]), "candidate_nets": 0,
                        "selected_nets": 0, "selected_by_die": {}, "skipped": {}}}
    if not values["enabled"] or not values["max_nets"]:
        return result
    candidates, skipped = [], Counter()
    excluded_originals = set(excluded_originals)
    for net in manifest["nets"]:
        name, pins = net["name"], net["pins"]
        if name in excluded_originals:
            skipped["shared_original"] += 1
            continue
        if net.get("special") or net.get("signal_type", "SIGNAL") != "SIGNAL":
            skipped["non_signal_or_special"] += 1
            continue
        if name.endswith(("_BOT", "_TOP")) or "__MLS__" in name:
            skipped["split_subnet"] += 1
            continue
        if any(p.get("hbt") or p["inst"] == "PIN"
               or p["inst"].startswith(("HBT_", "LS_HBT_")) for p in pins):
            skipped["hbt_or_package"] += 1
            continue
        # Some DEFs leave a clock leaf net's USE as SIGNAL. The Tcl caller
        # additionally checks MTerm SigType; these exact conventional names
        # provide a conservative guard using the geometry manifest alone.
        if any(p.get("pin") in {"CK", "CLK", "CLKN", "CKN", "clk"} for p in pins):
            skipped["clock_pin"] += 1
            continue
        dies = {p.get("die") for p in pins}
        if len(dies) != 1 or not dies <= {"bottom", "upper"}:
            skipped["nonlocal_die"] += 1
            continue
        if (sum(p.get("io") == "OUTPUT" for p in pins) != 1
                or any(p.get("io") not in ("INPUT", "OUTPUT") for p in pins)):
            skipped["ambiguous_direction"] += 1
            continue
        fanout = len(pins) - 1
        if fanout < values["min_fanout"]:
            skipped["low_fanout"] += 1
            continue
        hpwl = sum(max(p[axis] for p in pins) - min(p[axis] for p in pins)
                   for axis in ("x", "y")) / dbu
        if hpwl < span_threshold:
            skipped["short"] += 1
            continue
        die = next(iter(dies))
        minimum, maximum = (4, 10) if die == "bottom" else (11, 17)
        candidates.append({"net": name, "die": die, "fanout": fanout,
                           "hpwl_um": hpwl, "priority": fanout * hpwl,
                           "min_layer": minimum, "max_layer": maximum})
    candidates.sort(key=lambda item: (-item["priority"], item["net"]))
    selected = candidates[:values["max_nets"]]
    result["selected"] = selected
    result["stats"].update({"candidate_nets": len(candidates), "selected_nets": len(selected),
                            "selected_by_die": dict(sorted(Counter(x["die"] for x in selected).items())),
                            "selected_total_fanout": sum(x["fanout"] for x in selected),
                            "selected_total_hpwl_um": sum(x["hpwl_um"] for x in selected),
                            "skipped": dict(sorted(skipped.items()))})
    return result


def emit_layer_hints(plan):
    lines = ["# Generated trunk layer hints; the caller intersects its die interval.",
             "set ::grt_layer_hints [dict create]"]
    for entry in plan["selected"]:
        lines.append(f"dict set ::grt_layer_hints {tcl_word(entry['net'])} "
                     f"[list metal{entry['min_layer']} metal{entry['max_layer']}]")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-tcl", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, required=True)
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--min-fanout", type=int, default=DEFAULT_CONFIG["min_fanout"])
    parser.add_argument("--min-hpwl-um", type=float, default=DEFAULT_CONFIG["min_hpwl_um"])
    parser.add_argument("--max-nets", type=int, default=DEFAULT_CONFIG["max_nets"])
    parser.add_argument("--mls-plan", type=Path, help="Exclude originals replaced by this applied MLS plan")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    excluded = shared_original_nets(json.loads(args.mls_plan.read_text(encoding="utf-8"))) if args.mls_plan else ()
    plan = plan_layer_hints(manifest, {"enabled": args.enable, "min_fanout": args.min_fanout,
                                    "min_hpwl_um": args.min_hpwl_um, "max_nets": args.max_nets}, excluded)
    args.output_tcl.write_text(emit_layer_hints(plan), encoding="utf-8")
    args.report_json.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(plan["stats"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
