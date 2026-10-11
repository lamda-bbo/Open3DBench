#!/usr/bin/env python3
"""Export per-die net name lists for die-by-die global routing."""

from __future__ import annotations

import sys
import argparse
from pathlib import Path

from die_net_common import (
    classify_net_connections,
    iter_net_connections,
    parse_inst_die_map,
    parse_pin_die_map,
    def_sha256,
    write_classification_cache,
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("def_path", type=Path)
    parser.add_argument("output_dir", type=Path, nargs="?")
    parser.add_argument("--classification-cache", type=Path)
    args = parser.parse_args()
    def_path = args.def_path
    output_dir = args.output_dir or def_path.parent / "die_net_lists"
    input_digest = def_sha256(def_path) if args.classification_cache is not None else None
    inst_die_map = parse_inst_die_map(def_path)
    pin_die_map = parse_pin_die_map(def_path)
    # Keep compact metadata rather than every pin connection in the design.
    # Retaining the final classification per name also preserves the original
    # behavior for repeated DEF net names.
    nets: list[tuple[str, int]] = []
    classification: dict[str, str] = {}
    for name, pins in iter_net_connections(def_path):
        nets.append((name, len(pins)))
        classification[name] = classify_net_connections(
            name, pins, inst_die_map, pin_die_map
        )
    if args.classification_cache is not None:
        write_classification_cache(
            args.classification_cache, def_path, classification,
            expected_def_sha256=input_digest,
        )

    bottom: list[str] = []
    upper: list[str] = []
    special: list[str] = []
    for name, pin_count in nets:
        if pin_count < 2:
            special.append(name)
            continue

        label = classification.get(name, "unknown")
        routing_pass = assign_die_routing_pass(label)
        if routing_pass == "bottom":
            bottom.append(name)
        elif routing_pass == "upper":
            upper.append(name)
        elif label == "3d":
            special.append(name)
        else:
            special.append(name)

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
