#!/usr/bin/env python3
"""Check route.guide for 2D nets using layers from the opposite die."""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

from die_net_common import (
    classify_all_nets,
    parse_inst_die_map,
    parse_nets,
    parse_pin_die_map,
)

BOTTOM_MAX = 10
UPPER_MIN = 11
METAL_RE = re.compile(r"^metal(\d+)$", re.I)


def parse_layer(name: str) -> int | None:
    match = METAL_RE.match(name.strip())
    return int(match.group(1)) if match else None


def classify_net_from_def(def_path: Path) -> dict[str, str]:
    """Return net_name -> '2d_bottom' | '2d_upper' | '3d' | 'unknown'."""
    return classify_all_nets(
        parse_nets(def_path),
        parse_inst_die_map(def_path),
        parse_pin_die_map(def_path),
    )


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
) -> tuple[dict[str, str], dict[str, list[int]]]:
    net_class = classify_net_from_def(def_path)
    violations: dict[str, list[int]] = defaultdict(list)

    for net, layer in parse_guide(guide_path):
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
    net_class, violations = check(guide_path, def_path)

    n2b = sum(1 for c in net_class.values() if c == "2d_bottom")
    n2u = sum(1 for c in net_class.values() if c == "2d_upper")
    n3d = sum(1 for c in net_class.values() if c == "3d")
    print(f"DEF classification: 2D_bottom={n2b} 2D_upper={n2u} 3D={n3d}")

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
