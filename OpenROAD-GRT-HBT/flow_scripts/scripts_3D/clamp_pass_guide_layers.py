#!/usr/bin/env python3
"""Drop guide rectangles outside a die pass layer window (e.g. m11-m20 for upper GRT)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

METAL_RE = re.compile(r"^metal(\d+)$", re.I)


def parse_layer(name: str) -> int | None:
    """Return metal layer index or None."""
    match = METAL_RE.match(name.strip())
    return int(match.group(1)) if match else None


def clamp_guides(
    guide_path: Path,
    min_layer: int,
    max_layer: int,
    out_path: Path,
) -> tuple[int, int, int]:
    """Remove guide rects with layer number outside [min_layer, max_layer]."""
    removed = 0
    kept = 0
    nets_touched = 0
    cur_net: str | None = None
    net_had_removal = False
    out_lines: list[str] = []

    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            raw = line.rstrip("\n")
            stripped = raw.strip()

            if not stripped:
                out_lines.append(raw)
                continue
            if stripped == "(":
                out_lines.append(raw)
                continue
            if stripped == ")":
                if net_had_removal:
                    nets_touched += 1
                cur_net = None
                net_had_removal = False
                out_lines.append(raw)
                continue

            parts = stripped.split()
            if len(parts) >= 5:
                layer_num = parse_layer(parts[-1])
                if layer_num is not None and (
                    layer_num < min_layer or layer_num > max_layer
                ):
                    removed += 1
                    net_had_removal = True
                    continue
                kept += 1
                out_lines.append(raw)
                continue

            if len(parts) == 1:
                cur_net = stripped
                out_lines.append(raw)
                continue
            if stripped.endswith("("):
                cur_net = stripped[:-1].strip()
                out_lines.append(raw)
                continue

            out_lines.append(raw)

    out_path.write_text("\n".join(out_lines) + "\n")
    return removed, kept, nets_touched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide_in", type=Path)
    parser.add_argument("min_layer", type=int, help="Minimum metal layer number (inclusive)")
    parser.add_argument("max_layer", type=int, help="Maximum metal layer number (inclusive)")
    parser.add_argument(
        "guide_out",
        type=Path,
        nargs="?",
        help="Output guide (default: overwrite guide_in)",
    )
    args = parser.parse_args()

    out = args.guide_out or args.guide_in
    removed, kept, nets = clamp_guides(
        args.guide_in,
        args.min_layer,
        args.max_layer,
        out,
    )
    print(
        f"Clamped guide layers metal{args.min_layer}-metal{args.max_layer}: "
        f"removed {removed} rects ({nets} nets), kept {kept}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
