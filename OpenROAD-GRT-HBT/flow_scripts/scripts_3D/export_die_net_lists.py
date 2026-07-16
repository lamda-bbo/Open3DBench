#!/usr/bin/env python3
"""Export per-die net name lists for die-by-die global routing."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from mol_hbt_common import (
    classify_all_nets,
    count_net_routing_terminals,
    parse_inst_die_map,
    parse_nets,
)
from mol_layer_share_common import (
    build_subnet_manifest_index,
    is_share_subnet_name,
    load_share_manifest,
    manifest_path_from_env,
    routing_pass_for_share_subnet,
)


def write_list(path: Path, names: list[str]) -> None:
    """Write one net name per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")


def assign_die_routing_pass(net_name: str, label: str) -> str | None:
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
    output_dir = Path(sys.argv[2]) if len(sys.argv) == 3 else def_path.parent / "die_net_lists"
    results_dir = Path(os.environ.get("RESULTS_DIR", def_path.parent))
    manifest = load_share_manifest(manifest_path_from_env(results_dir))
    subnet_index = build_subnet_manifest_index(manifest)

    inst_die_map = parse_inst_die_map(def_path)
    nets = parse_nets(def_path)
    classification = classify_all_nets(nets, inst_die_map)

    bottom: list[str] = []
    upper: list[str] = []
    special: list[str] = []
    share_count = 0
    io_promoted = 0

    for net in nets:
        if net.name in subnet_index:
            routing_pass = routing_pass_for_share_subnet(net.name, subnet_index[net.name])
            if routing_pass == "bottom":
                bottom.append(net.name)
            elif routing_pass == "upper":
                upper.append(net.name)
            else:
                special.append(net.name)
            share_count += 1
            continue

        if is_share_subnet_name(net.name) and net.name not in subnet_index:
            special.append(net.name)
            continue

        # An IO net with a chip port may expose only one instance pin here.
        if count_net_routing_terminals(net) < 2:
            special.append(net.name)
            continue

        label = classification.get(net.name, "unknown")
        routing_pass = assign_die_routing_pass(net.name, label)
        if routing_pass == "bottom":
            bottom.append(net.name)
            if len(net.pins) < 2:
                io_promoted += 1
        elif routing_pass == "upper":
            upper.append(net.name)
            if len(net.pins) < 2:
                io_promoted += 1
        elif label == "3d":
            special.append(net.name)
        else:
            special.append(net.name)

    write_list(output_dir / "bottom_2d.txt", sorted(set(bottom)))
    write_list(output_dir / "upper_2d.txt", sorted(set(upper)))
    write_list(output_dir / "special.txt", sorted(set(special)))

    print(
        f"Die net lists: bottom={len(bottom)} upper={len(upper)} "
        f"special={len(special)} layer_share_subnets={share_count} "
        f"io_promoted={io_promoted} -> {output_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
