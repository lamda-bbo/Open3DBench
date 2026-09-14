#!/usr/bin/env python3
"""Replay a saved final ODB/SPEF without modifying the original run.

Run inside the evaluation image. Output must be a new directory. Optional
--remove-net NAME injects a missing D_NET and requires fail-closed behavior.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def tcl(value):
    value = str(value)
    if any(c in value for c in "{}\n\r"):
        raise ValueError("Unsupported character in Tcl path")
    return "{" + value + "}"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def remove_net(source, target, name):
    net_id = None
    with source.open() as stream:
        for line in stream:
            fields = line.split()
            if len(fields) == 2 and fields[0].startswith("*") and fields[1] == name:
                net_id = fields[0]
                break
    if net_id is None:
        raise ValueError("Fault-injection net not found")
    skip = False
    removed = 0
    with source.open() as stream, target.open("w") as output:
        for line in stream:
            if line.startswith("*D_NET "):
                skip = line.split()[1] == net_id
                removed += int(skip)
            if not skip:
                output.write(line)
            if line.startswith("*END"):
                skip = False
    if removed != 1:
        raise ValueError("Expected exactly one removed D_NET")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--flow", required=True, type=Path)
    parser.add_argument("--design-config", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--make-var", action="append", default=[])
    parser.add_argument("--remove-net")
    parser.add_argument("--odb", default="6_final.odb")
    parser.add_argument("--sdc", default="6_1_fill.sdc")
    args = parser.parse_args()
    flow, output = args.flow.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ, OPENROAD_EXE="/usr/bin/openroad", PYTHONDONTWRITEBYTECODE="1")
    exported = subprocess.run(["make", "-s", "--no-print-directory",
        "DESIGN_CONFIG=" + args.design_config] + args.make_var +
        ["--eval=spef_test_env: ; @/usr/bin/env", "spef_test_env"],
        cwd=str(flow), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, check=True)
    for line in exported.stdout.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            env[key] = value
    results = Path(env["RESULTS_DIR"])
    if not results.is_absolute():
        results = flow / results
    inputs = [results / args.odb, results / args.sdc, results / "6_final.spef"]
    before = {str(path): sha(path) for path in inputs}
    spef = inputs[-1]
    if args.remove_net:
        spef = output / "missing_net.spef"
        remove_net(inputs[-1], spef, args.remove_net)
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    script = output / "replay.tcl"
    source = '''source $::env(SCRIPTS_DIR)/load.tcl
load_design %s %s {checked SPEF regression}
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set canonical {}
foreach obj [concat [$block getNets] [$block getInsts]] { lappend canonical [list $obj [$obj getName]] }
set ::env(SCRIPTS_DIR) %s
source $::env(SCRIPTS_DIR)/read_spef_checked.tcl
set code [catch {read_spef_checked %s %s} message]
foreach row $canonical {
  lassign $row obj name
  if {[$obj getName] ne $name} { error "Canonical name changed: $name" }
}
puts {CANONICAL_NAMES_UNCHANGED}
''' % (tcl(args.odb), tcl(args.sdc), tcl(scripts), tcl(spef), tcl(output / "spef"))
    if args.remove_net:
        source += '''if {!$code} { error "Corrupt SPEF was incorrectly accepted" }
puts "EXPECTED_FAILURE $message"
'''
    else:
        source += '''if {$code} { error $message }
report_worst_slack -max -digits 6
report_tns -digits 6
report_checks -path_delay max -group_count 1 -fields {capacitance slew input_pin net} -digits 6
'''
    source += 'puts {REPLAY_PASS}\nexit\n'
    script.write_text(source)
    with (output / "replay.log").open("w") as log:
        result = subprocess.run([env["OPENROAD_EXE"], "-exit", "-no_init", str(script)],
            cwd=str(flow), env=env, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    after = {str(path): sha(path) for path in inputs}
    log = (output / "replay.log").read_text()
    passed = result.returncode == 0 and "REPLAY_PASS" in log and before == after
    summary = {"pass": passed, "exit": result.returncode, "fault_net": args.remove_net,
               "canonical_names_unchanged": "CANONICAL_NAMES_UNCHANGED" in log,
               "inputs_unchanged": before == after, "input_sha256": before,
               "wns_ns": re.findall(r"worst slack\s+(-?[\d.eE+]+)", log),
               "tns_ns": re.findall(r"^tns\s+(-?[\d.eE+]+)", log, re.M)}
    (output / "result.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    if not passed:
        raise SystemExit("Replay failed: " + str(output / "replay.log"))


if __name__ == "__main__":
    main()
