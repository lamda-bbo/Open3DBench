#!/usr/bin/env python3
"""Check route.guide for 2D nets using layers from the opposite die."""

from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from mol_layer_share_common import (
    build_subnet_manifest_index,
    is_share_subnet_name,
    layer_allowed_for_share_subnet,
    load_share_manifest,
    manifest_path_from_env,
)

BOTTOM_MAX = 10
UPPER_MIN = 11
METAL_RE = re.compile(r"^metal(\d+)$", re.I)


def parse_layer(name: str) -> int | None:
    match = METAL_RE.match(name.strip())
    return int(match.group(1)) if match else None


def name_die(name: str) -> str | None:
    if name.endswith("_bottom") or name.startswith("HBT_BOTIN_"):
        return "bottom"
    if name.endswith("_upper") or name.startswith("HBT_TOPIN_"):
        return "upper"
    return None


def parse_inst_die_map(def_path: Path) -> dict[str, str]:
    """Map instance name -> die using instance/cell name suffixes."""
    inst_die_map: dict[str, str] = {}
    in_components = False

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("COMPONENTS"):
                in_components = True
                continue
            if in_components and stripped.startswith("END COMPONENTS"):
                break
            if not in_components or not stripped.startswith("- "):
                continue
            parts = stripped.split()
            if len(parts) < 3:
                continue
            inst = parts[1]
            cell = parts[2]
            die = name_die(inst) or name_die(cell)
            if die:
                inst_die_map[inst] = die

    return inst_die_map


def classify_net_from_def(def_path: Path) -> dict[str, str]:
    """Return net_name -> '2d_bottom' | '2d_upper' | '3d' | 'unknown'."""
    inst_die_map = parse_inst_die_map(def_path)
    net_pins: dict[str, set[str]] = defaultdict(set)
    in_nets = False
    cur_net: str | None = None

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("NETS"):
                in_nets = True
                continue
            if in_nets and stripped.startswith("END NETS"):
                break
            if not in_nets:
                continue
            if stripped.startswith("- "):
                cur_net = stripped.split()[1]
                if cur_net.endswith("_BOT"):
                    net_pins[cur_net].add("bottom")
                elif cur_net.endswith("_TOP"):
                    net_pins[cur_net].add("upper")
                rest = stripped[len("- " + cur_net) :].strip()
                if rest.startswith("("):
                    for pin in re.findall(r"\(\s*(\S+)", rest):
                        if pin != "PIN":
                            die = inst_die_map.get(pin)
                            if die:
                                net_pins[cur_net].add(die)
                continue
            if cur_net and stripped.startswith("("):
                parts = stripped.strip("() ;").split()
                if len(parts) >= 2 and parts[0] != "PIN":
                    inst = parts[0]
                    die = inst_die_map.get(inst)
                    if die:
                        net_pins[cur_net].add(die)

    classification: dict[str, str] = {}
    for net, dies in net_pins.items():
        if is_share_subnet_name(net):
            classification[net] = "layer_share"
            continue
        if net.endswith("_BOT"):
            classification[net] = "2d_bottom"
        elif net.endswith("_TOP"):
            classification[net] = "2d_upper"
        elif "bottom" in dies and "upper" in dies:
            classification[net] = "3d"
        elif "bottom" in dies:
            classification[net] = "2d_bottom"
        elif "upper" in dies:
            classification[net] = "2d_upper"
        else:
            classification[net] = "unknown"
    return classification


def parse_guide(guide_path: Path):
    """Yield (net_name, layer_num) for each guide rectangle line."""
    cur_net: str | None = None
    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            line = line.rstrip()
            if not line:
                continue
            if line == "(":
                continue
            if line == ")":
                cur_net = None
                continue
            parts = line.split()
            if len(parts) >= 5:
                layer = parse_layer(parts[-1])
                if layer is not None and cur_net:
                    yield cur_net, layer
                continue
            if len(parts) == 1:
                cur_net = line
                continue
            if line.endswith("("):
                cur_net = line[:-1].strip()


def layer_allowed_plain_2d(cls: str, layer: int) -> bool:
    if cls == "2d_bottom":
        return layer <= BOTTOM_MAX
    if cls == "2d_upper":
        return layer >= UPPER_MIN
    return True


def check(
    guide_path: Path,
    def_path: Path,
    subnet_index: dict[str, dict[str, object]],
) -> tuple[dict[str, str], dict[str, list[int]]]:
    net_class = classify_net_from_def(def_path)
    violations: dict[str, list[int]] = defaultdict(list)

    for net, layer in parse_guide(guide_path):
        if net in subnet_index:
            if not layer_allowed_for_share_subnet(net, layer, subnet_index[net]):
                violations[net].append(layer)
            continue
        cls = net_class.get(net)
        if not layer_allowed_plain_2d(cls or "", layer):
            violations[net].append(layer)

    return net_class, violations


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <route.guide> <design.def>", file=sys.stderr)
        sys.exit(2)

    guide_path = Path(sys.argv[1])
    def_path = Path(sys.argv[2])
    results_dir = Path(os.environ.get("RESULTS_DIR", def_path.parent))
    manifest = load_share_manifest(manifest_path_from_env(results_dir))
    subnet_index = build_subnet_manifest_index(manifest)

    net_class, violations = check(guide_path, def_path, subnet_index)

    n2b = sum(1 for c in net_class.values() if c == "2d_bottom")
    n2u = sum(1 for c in net_class.values() if c == "2d_upper")
    n3d = sum(1 for c in net_class.values() if c == "3d")
    nshare = sum(1 for c in net_class.values() if c == "layer_share")
    print(
        f"DEF classification: 2D_bottom={n2b} 2D_upper={n2u} "
        f"3D={n3d} layer_share={nshare}"
    )

    if not violations:
        print("PASS: no cross-die layer usage in 2D nets")
        return

    print(f"FAIL: {len(violations)} nets with cross-die layers in guide")
    for net in sorted(violations)[:20]:
        layers = sorted(set(violations[net]))
        print(f"  {net} ({net_class.get(net, '?')}): illegal layers {layers}")
    if len(violations) > 20:
        print(f"  ... and {len(violations) - 20} more")
    sys.exit(1)


if __name__ == "__main__":
    main()
