#!/usr/bin/env python3
"""Scrub cross-die layer guide rects from 2D nets in route.guide.

Illegal rects are migrated to the nearest legal die boundary layer instead of
being dropped, so guide connectivity survives for DRT (avoids DRT-0218).

2D_bottom nets: metal11+ -> metal10.
2D_upper nets: metal10- -> metal11.
Layer-share subnets use mol_layer_share_manifest.json rules.
3D nets are unchanged.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from check_2d_net_guide_layers import (
    BOTTOM_MAX,
    UPPER_MIN,
    classify_net_from_def,
    layer_allowed_plain_2d,
    parse_layer,
)
from mol_layer_share_common import (
    build_subnet_manifest_index,
    layer_allowed_for_share_subnet,
    load_share_manifest,
    manifest_path_from_env,
    share_subnet_routing_pool,
)


def layer_name(layer: int) -> str:
    """Format metal layer index as route.guide layer string."""
    return f"metal{layer}"


def migrate_plain_2d_layer(cls: str, layer: int) -> int:
    """Map an illegal 2D net layer to the nearest legal boundary."""
    if cls == "2d_bottom":
        return min(layer, BOTTOM_MAX)
    if cls == "2d_upper":
        return max(layer, UPPER_MIN)
    return layer


def migrate_share_subnet_layer(
    subnet_name: str,
    layer: int,
    manifest_entry: dict[str, object],
) -> int:
    """Map an illegal layer-share subnet layer to the nearest legal boundary."""
    pool = share_subnet_routing_pool(subnet_name, manifest_entry)
    home_die = manifest_entry.get("home_die")
    if pool is None or home_die not in ("upper", "bottom"):
        return layer
    if pool == "native":
        if home_die == "upper":
            return max(layer, UPPER_MIN)
        return min(layer, BOTTOM_MAX)
    if home_die == "upper":
        return min(layer, BOTTOM_MAX)
    return max(layer, UPPER_MIN)


def resolve_scrub_layer(
    net: str,
    layer: int,
    net_class: dict[str, str],
    subnet_index: dict[str, dict[str, object]],
) -> int:
    """Return the layer to emit for one guide rect (possibly migrated)."""
    if net in subnet_index:
        allowed = layer_allowed_for_share_subnet(
            net,
            layer,
            subnet_index[net],
            bottom_max=BOTTOM_MAX,
            upper_min=UPPER_MIN,
        )
        if allowed:
            return layer
        return migrate_share_subnet_layer(net, layer, subnet_index[net])

    cls = net_class.get(net, "")
    if not cls.startswith("2d_"):
        return layer
    if layer_allowed_plain_2d(cls, layer):
        return layer
    return migrate_plain_2d_layer(cls, layer)


def scrub_guides(
    guide_path: Path,
    def_path: Path,
    out_path: Path,
    subnet_index: dict[str, dict[str, object]],
):
    net_class = classify_net_from_def(def_path)
    migrated = 0
    kept = 0
    nets_scrubbed = 0
    cur_net: str | None = None
    net_had_scrub = False
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
                if net_had_scrub:
                    nets_scrubbed += 1
                cur_net = None
                net_had_scrub = False
                out_lines.append(raw)
                continue

            parts = stripped.split()
            if len(parts) >= 5:
                layer_idx = parse_layer(parts[-1])
                if layer_idx is not None and cur_net is not None:
                    target = resolve_scrub_layer(
                        cur_net,
                        layer_idx,
                        net_class,
                        subnet_index,
                    )
                    if target != layer_idx:
                        migrated += 1
                        net_had_scrub = True
                        out_lines.append(
                            f"{parts[0]} {parts[1]} {parts[2]} {parts[3]} "
                            f"{layer_name(target)}"
                        )
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
    return migrated, kept, nets_scrubbed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide_in", type=Path)
    parser.add_argument("def_file", type=Path)
    parser.add_argument("guide_out", type=Path, nargs="?", default=None)
    args = parser.parse_args()

    results_dir = Path(os.environ.get("RESULTS_DIR", args.def_file.parent))
    manifest = load_share_manifest(manifest_path_from_env(results_dir))
    subnet_index = build_subnet_manifest_index(manifest)

    out = args.guide_out or args.guide_in
    migrated, kept, nets_scrubbed = scrub_guides(
        args.guide_in,
        args.def_file,
        out,
        subnet_index,
    )
    print(
        f"Scrubbed {migrated} illegal guide rects via layer migration "
        f"({nets_scrubbed} nets affected, {kept} rects kept)"
    )
    if migrated == 0:
        print("PASS: nothing to scrub")
    return 0


if __name__ == "__main__":
    sys.exit(main())
