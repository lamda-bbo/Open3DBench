#!/usr/bin/env python3
"""Check route.guide for 2D nets using layers from the opposite die."""

from __future__ import annotations

import re
import argparse
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from die_net_common import (
    classify_all_nets,
    iter_nets,
    parse_inst_die_map,
    parse_pin_die_map,
    read_classification_cache,
)
from prepared_metadata import read_prepared_metadata

BOTTOM_MAX = 10
UPPER_MIN = 11
METAL_RE = re.compile(r"^metal(\d+)$", re.I)


@lru_cache(maxsize=128)
def parse_layer(name: str) -> int | None:
    match = METAL_RE.match(name.strip())
    return int(match.group(1)) if match else None


def classify_net_from_def(
    def_path: Path,
    classification_cache: Path | None = None,
) -> dict[str, str]:
    """Return net_name -> '2d_bottom' | '2d_upper' | '3d' | 'unknown'."""
    if classification_cache is not None:
        cached = read_classification_cache(classification_cache, def_path)
        if cached is not None:
            return cached
    return classify_all_nets(
        iter_nets(def_path),
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
    classification_cache: Path | None = None,
    prepared_metadata: Path | None = None,
    prepared_metadata_sha256: str | None = None,
) -> tuple[dict[str, str], dict[str, list[int]]]:
    net_class = (read_prepared_metadata(prepared_metadata, prepared_metadata_sha256).classification()
                 if prepared_metadata is not None else classify_net_from_def(def_path, classification_cache))
    violations: dict[str, list[int]] = defaultdict(list)

    for net, layer in parse_guide(guide_path):
        cls = net_class.get(net)
        if not layer_allowed_plain_2d(cls or "", layer):
            violations[net].append(layer)

    return net_class, violations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide_path", type=Path)
    parser.add_argument("def_path", type=Path)
    parser.add_argument("--classification-cache", type=Path)
    parser.add_argument("--prepared-metadata", type=Path)
    parser.add_argument("--prepared-metadata-sha256")
    args = parser.parse_args()
    if args.prepared_metadata_sha256 is not None and args.prepared_metadata is None:
        parser.error('--prepared-metadata-sha256 requires --prepared-metadata')
    net_class, violations = check(args.guide_path, args.def_path, args.classification_cache,
                                  args.prepared_metadata, args.prepared_metadata_sha256)

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
