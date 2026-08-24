#!/usr/bin/env python3
"""Export per-die net name lists for die-by-die global routing."""

from __future__ import annotations

import sys
from pathlib import Path

from die_net_common import (
    classify_all_nets,
    parse_inst_die_map,
    parse_nets,
    parse_pin_die_map,
)


def write_list(path: Path, names: list[str]) -> None:
    """Write one net name per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")


def assign_die_routing_pass(label: str) -> str | None:
    """Map a classified net label to bottom/upper GRT pass, or None if special."""
    if label == "2d_bottom":
        return "bottom"
    if label == "2d_upper":
        return "upper"
    return None


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            f"Usage: {sys.argv[0]} <design.def> [output_dir]",
            file=sys.stderr,
        )
        return 2

    def_path = Path(sys.argv[1])
    output_dir = (
        Path(sys.argv[2])
        if len(sys.argv) == 3
        else def_path.parent / "die_net_lists"
    )
    inst_die_map = parse_inst_die_map(def_path)
    pin_die_map = parse_pin_die_map(def_path)
    nets = parse_nets(def_path)
    classification = classify_all_nets(nets, inst_die_map, pin_die_map)

    bottom: list[str] = []
    upper: list[str] = []
    special: list[str] = []
    for net in nets:
        if len(net.pins) < 2:
            special.append(net.name)
            continue

        label = classification.get(net.name, "unknown")
        routing_pass = assign_die_routing_pass(label)
        if routing_pass == "bottom":
            bottom.append(net.name)
        elif routing_pass == "upper":
            upper.append(net.name)
        elif label == "3d":
            special.append(net.name)
        else:
            special.append(net.name)

    write_list(output_dir / "bottom_2d.txt", sorted(set(bottom)))
    write_list(output_dir / "upper_2d.txt", sorted(set(upper)))
    write_list(output_dir / "special.txt", sorted(set(special)))

    print(
        f"Die net lists: bottom={len(bottom)} upper={len(upper)} "
        f"special={len(special)} -> {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
