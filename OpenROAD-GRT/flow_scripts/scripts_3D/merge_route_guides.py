#!/usr/bin/env python3
"""Merge multiple OpenROAD route.guide files without duplicate nets."""

import sys
from pathlib import Path
from typing import Dict, List, Optional


def parse_guide_nets(guide_path: Path) -> Dict[str, List[str]]:
    """Parse guide file into net -> list of body lines (including net header block)."""
    blocks: Dict[str, List[str]] = {}
    current_net: Optional[str] = None
    current_lines: List[str] = []

    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.rstrip("\n")
            if stripped == "":
                continue
            if stripped == ")":
                if current_net is not None:
                    current_lines.append(stripped)
                    blocks[current_net] = current_lines
                    current_net = None
                    current_lines = []
                continue
            if stripped == "(":
                if current_net is not None:
                    current_lines.append(stripped)
                continue
            if current_net is None:
                current_net = stripped
                current_lines = [stripped]
                continue
            current_lines.append(stripped)

    return blocks


def parse_guide_net_blocks(guide_path: Path) -> Dict[str, List[List[str]]]:
    """Parse guide file into net -> list of rect-line blocks."""
    blocks_by_net: Dict[str, List[List[str]]] = {}
    current_net: Optional[str] = None
    current_rects: List[str] = []
    in_block = False

    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.rstrip("\n")
            if stripped == "":
                continue
            if stripped == "(":
                in_block = True
                current_rects = []
                continue
            if stripped == ")":
                in_block = False
                if current_net is not None:
                    blocks_by_net.setdefault(current_net, []).append(current_rects)
                continue
            if not in_block:
                current_net = stripped
                continue
            current_rects.append(stripped)

    return blocks_by_net


def select_guide_block(net_name: str, rect_blocks: List[List[str]]) -> List[str]:
    """Pick one duplicate guide block; _BOT keeps HBT cover, others keep main GRT path."""
    if len(rect_blocks) == 1:
        return rect_blocks[0]
    if net_name.endswith("_BOT"):
        return rect_blocks[-1]
    return max(rect_blocks, key=len)


def parse_guide_net_rects(guide_path: Path) -> Dict[str, List[str]]:
    """Collect routing rect lines per net from duplicate guide blocks."""
    blocks_by_net = parse_guide_net_blocks(guide_path)
    return {
        net_name: select_guide_block(net_name, rect_blocks)
        for net_name, rect_blocks in blocks_by_net.items()
        if rect_blocks
    }


def merge_guides(inputs: List[Path], output_path: Path) -> None:
    """Merge guide blocks; later files must not repeat net names."""
    merged: Dict[str, str] = {}
    for guide_path in inputs:
        blocks = dict(iter_guide_text_blocks(guide_path))
        for net_name, block in blocks.items():
            if net_name in merged:
                raise ValueError(f"Duplicate net {net_name} in merge inputs")
            merged[net_name] = block

    with output_path.open("w", encoding="utf-8") as out_file:
        for net_name in sorted(merged):
            out_file.write(merged[net_name])


def iter_guide_text_blocks(guide_path: Path):
    """Yield complete blocks, preserving the permissive legacy parser rules.

    Joining a block immediately avoids retaining a Python string/list entry
    for every rectangle and writing each rectangle separately. Duplicate nets
    within a file still keep their last complete block through dict().
    """
    current_net = None
    current_lines = []
    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.rstrip("\n")
            if stripped == "":
                continue
            if stripped == ")":
                if current_net is not None:
                    current_lines.append(stripped)
                    yield current_net, "\n".join(current_lines) + "\n"
                    current_net = None
                    current_lines = []
                continue
            if stripped == "(":
                if current_net is not None:
                    current_lines.append(stripped)
                continue
            if current_net is None:
                current_net = stripped
                current_lines = [stripped]
                continue
            current_lines.append(stripped)


def main() -> int:
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <out.guide> <in1.guide> [in2.guide ...]",
            file=sys.stderr,
        )
        return 2

    output_path = Path(sys.argv[1])
    inputs = [Path(path) for path in sys.argv[2:]]
    merge_guides(inputs, output_path)
    print(f"Merged {len(inputs)} guides -> {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
