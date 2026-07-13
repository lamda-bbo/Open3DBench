#!/usr/bin/env python3
"""Inject HBT pin cover and Manhattan bridge guides into route.guide."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from mol_hbt_common import PinRef, parse_nets
from mol_layer_share_common import (
    SHARE_SUBNET_SUFFIXES,
    build_subnet_manifest_index,
    load_share_manifest,
    manifest_path_from_env,
    share_subnet_routing_pool,
)

# HBT macro size from LEF (microns); DEF uses 2000 DBU/um.
HBT_SIZE_DBU = int(os.environ.get("HBT_SIZE_DBU", "2000"))

METAL_RE = re.compile(r"^metal(\d+)$", re.I)
HBT_INST_RE = re.compile(r"^(HBT_|LS_HBT_)")
HBT_PIN_LAYERS = {"BOT": "metal10", "TOP": "metal11"}
DEFAULT_GCELL_STEP = 4200
DEFAULT_COVER_RADIUS = 1


@dataclass(frozen=True)
class CoverRect:
    """One guide rectangle to inject."""

    net: str
    layer: str
    x1: int
    y1: int
    x2: int
    y2: int


def _store_component_origin(
    components: dict[str, tuple[int, int]],
    inst: str,
    line: str,
) -> None:
    """Record one instance origin from a PLACED/FIXED/COVER line."""
    match = re.search(r"\(\s*(\d+)\s+(\d+)\s*\)", line)
    if match:
        components[inst] = (int(match.group(1)), int(match.group(2)))


def parse_components_multiline(def_path: Path) -> dict[str, tuple[int, int]]:
    """Parse DEF components; PLACED/FIXED/COVER may appear on the following line."""
    components: dict[str, tuple[int, int]] = {}
    in_components = False
    pending_inst: str | None = None

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("COMPONENTS"):
                in_components = True
                continue
            if in_components and stripped.startswith("END COMPONENTS"):
                break
            if not in_components:
                continue
            if stripped.startswith("- "):
                parts = stripped.split()
                pending_inst = parts[1] if len(parts) >= 2 else None
                if pending_inst and (
                    "PLACED" in stripped or "FIXED" in stripped or "COVER" in stripped
                ):
                    _store_component_origin(components, pending_inst, stripped)
                    pending_inst = None
                continue
            if pending_inst and (
                "PLACED" in stripped or "FIXED" in stripped or "COVER" in stripped
            ):
                _store_component_origin(components, pending_inst, stripped)
                pending_inst = None

    return components


def cover_box(x: int, y: int, step: int, radius: int) -> tuple[int, int, int, int]:
    """Build a gcell-sized cover rectangle centered near instance origin."""
    half = step * radius
    return (x - half, y - half, x + half, y + half)


def parse_guide_index(
    guide_path: Path,
) -> dict[str, list[tuple[int, int, int, int, str]]]:
    """Index existing guide rectangles per net."""
    nets: dict[str, list[tuple[int, int, int, int, str]]] = {}
    cur_net: str | None = None
    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.strip()
            if stripped in ("(", ")"):
                if stripped == ")":
                    cur_net = None
                continue
            parts = stripped.split()
            if len(parts) >= 5 and METAL_RE.match(parts[-1]):
                if cur_net:
                    nets.setdefault(cur_net, []).append(
                        (
                            int(parts[0]),
                            int(parts[1]),
                            int(parts[2]),
                            int(parts[3]),
                            parts[-1],
                        )
                    )
                continue
            if len(parts) == 1:
                cur_net = parts[0]
            elif stripped.endswith("("):
                cur_net = stripped[:-1].strip()
    return nets


def nearest_rect_on_layer(
    rects: list[tuple[int, int, int, int, str]],
    layer: str,
    x: int,
    y: int,
) -> tuple[int, int] | None:
    """Return center of nearest same-layer guide rect to (x, y)."""
    best: tuple[int, int] | None = None
    best_dist: int | None = None
    for x1, y1, x2, y2, rect_layer in rects:
        if rect_layer != layer:
            continue
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        dist = abs(cx - x) + abs(cy - y)
        if best_dist is None or dist < best_dist:
            best = (cx, cy)
            best_dist = dist
    return best


def first_rect_on_layer(
    rects: list[tuple[int, int, int, int, str]],
    layer: str,
) -> tuple[int, int] | None:
    """Return center of the first same-layer guide rect, for large-net fast paths."""
    for x1, y1, x2, y2, rect_layer in rects:
        if rect_layer == layer:
            return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None


def first_rect_any_layer(
    rects: list[tuple[int, int, int, int, str]],
) -> tuple[int, int, str] | None:
    """Return center and layer of the first guide rect, for large-net fast paths."""
    if not rects:
        return None
    x1, y1, x2, y2, rect_layer = rects[0]
    return ((x1 + x2) // 2, (y1 + y2) // 2, rect_layer)


def manhattan_bridge_rects(
    x: int,
    y: int,
    tx: int,
    ty: int,
    layer: str,
    step: int,
) -> list[tuple[int, int, int, int, str]]:
    """Build L-shaped bridge rects on one layer between two points."""
    half = max(step // 2, 1)
    rects: list[tuple[int, int, int, int, str]] = []
    x_lo, x_hi = sorted([x, tx])
    y_lo, y_hi = sorted([y, ty])
    if x_hi - x_lo >= step:
        rects.append((x_lo, y - half, x_hi, y + half, layer))
    if y_hi - y_lo >= step:
        rects.append((tx - half, y_lo, tx + half, y_hi, layer))
    return rects


def nearest_rect_any_layer(
    rects: list[tuple[int, int, int, int, str]],
    x: int,
    y: int,
) -> tuple[int, int, str] | None:
    """Return center and layer of nearest guide rect to (x, y)."""
    best: tuple[int, int, str] | None = None
    best_dist: int | None = None
    for x1, y1, x2, y2, rect_layer in rects:
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2
        dist = abs(cx - x) + abs(cy - y)
        if best_dist is None or dist < best_dist:
            best = (cx, cy, rect_layer)
            best_dist = dist
    return best


def is_mol_split_net(net_name: str, subnet_index: dict[str, dict[str, object]]) -> bool:
    """Return True for HBT-split (_TOP/_BOT) or layer-share subnet nets."""
    if net_name.endswith("_TOP") or net_name.endswith("_BOT"):
        return True
    if net_name in subnet_index:
        return True
    return net_name.endswith(SHARE_SUBNET_SUFFIXES)


def metal_layer_index(layer: str) -> int | None:
    """Return metalN index, or None for non-metal guide layers."""
    match = METAL_RE.match(layer)
    return int(match.group(1)) if match else None


def routing_layer_below(layer: str) -> str | None:
    """Return the die-local routing layer directly below ``layer``."""
    layer_idx = metal_layer_index(layer)
    if layer_idx is None or layer_idx <= 1:
        return None
    return f"metal{layer_idx - 1}"


def bridge_layer_for_subnet(
    net_name: str,
    subnet_index: dict[str, dict[str, object]],
) -> str | None:
    """Primary layer to stitch fragmented guides on a split net."""
    if net_name.endswith("_TOP"):
        return "metal11"
    if net_name.endswith("_BOT"):
        return "metal10"
    entry = subnet_index.get(net_name)
    if entry is None:
        return None
    pool = share_subnet_routing_pool(net_name, entry)
    home_die = entry.get("home_die")
    if pool is None or home_die not in ("upper", "bottom"):
        return None
    if pool == "native":
        return "metal11" if home_die == "upper" else "metal10"
    if home_die == "upper":
        return "metal10"
    return "metal11"


def pin_routing_layer(
    net_name: str,
    pin_ref: PinRef,
    subnet_index: dict[str, dict[str, object]],
) -> str | None:
    """Pick a die-appropriate routing layer for one pin cover."""
    if HBT_INST_RE.match(pin_ref.inst):
        return HBT_PIN_LAYERS.get(pin_ref.pin)
    bridge = bridge_layer_for_subnet(net_name, subnet_index)
    if bridge is not None:
        return bridge
    if net_name.endswith("_TOP"):
        return "metal11"
    if net_name.endswith("_BOT"):
        return "metal2"
    return None


def add_pin_cover_bridge(
    net_name: str,
    px: int,
    py: int,
    layer: str,
    existing: list[tuple[int, int, int, int, str]],
    *,
    gcell_step: int,
    cover_radius: int,
    add_rect,
) -> None:
    """Inject one pin cover and Manhattan bridge into the working guide index."""
    x1, y1, x2, y2 = cover_box(px, py, gcell_step, cover_radius)
    cover_rect = (x1, y1, x2, y2, layer)

    if len(existing) <= 5000:
        target = nearest_rect_on_layer(existing, layer, px, py)
    else:
        target = first_rect_on_layer(existing, layer)
    bridge_layer = layer
    if target is None:
        if len(existing) <= 5000:
            any_target = nearest_rect_any_layer(existing, px, py)
        else:
            any_target = first_rect_any_layer(existing)
        if any_target is not None:
            tx, ty, bridge_layer = any_target
        else:
            tx = ty = None
    else:
        tx, ty = target

    append_rect(net_name, cover_rect, existing, add_rect)

    below_layer = routing_layer_below(layer)
    if below_layer is not None:
        append_rect(
            net_name,
            duplicate_rect_on_layer(cover_rect, below_layer),
            existing,
            add_rect,
        )

    if tx is None or ty is None:
        return

    for bx1, by1, bx2, by2, bl in manhattan_bridge_rects(
        px, py, tx, ty, bridge_layer, gcell_step
    ):
        bridge_rect = (bx1, by1, bx2, by2, bl)
        append_rect(net_name, bridge_rect, existing, add_rect)
        if below_layer is not None and bl.lower() == layer.lower():
            mirror_bridge_to_below_layer(
                net_name,
                bridge_rect,
                below_layer=below_layer,
                existing=existing,
                add_rect=add_rect,
            )


def rects_touch(
    a: tuple[int, int, int, int, str],
    b: tuple[int, int, int, int, str],
) -> bool:
    """Return True when two same-layer guide rects overlap or touch."""
    if a[4] != b[4]:
        return False
    return not (a[2] < b[0] - 1 or b[2] < a[0] - 1 or a[3] < b[1] - 1 or b[3] < a[1] - 1)


def cross_layer_touch(
    upper: tuple[int, int, int, int, str],
    lower: tuple[int, int, int, int, str],
) -> bool:
    """Return True when adjacent metal layers overlap in XY (DRT-style adjacency)."""
    upper_idx = metal_layer_index(upper[4])
    lower_idx = metal_layer_index(lower[4])
    if upper_idx is None or lower_idx is None or abs(upper_idx - lower_idx) != 1:
        return False
    return not (
        upper[2] < lower[0]
        or lower[2] < upper[0]
        or upper[3] < lower[1]
        or lower[3] < upper[1]
    )


def layer_pair_has_contact(
    rects: list[tuple[int, int, int, int, str]],
    upper_layer: str,
    lower_layer: str,
) -> bool:
    """Return True when any upper-layer rect touches a lower-layer rect."""
    upper_rects = [rect for rect in rects if rect[4].lower() == upper_layer.lower()]
    lower_rects = [rect for rect in rects if rect[4].lower() == lower_layer.lower()]
    for upper_rect in upper_rects:
        for lower_rect in lower_rects:
            if cross_layer_touch(upper_rect, lower_rect):
                return True
    return False


def duplicate_rect_on_layer(
    rect: tuple[int, int, int, int, str],
    layer: str,
) -> tuple[int, int, int, int, str]:
    """Copy one guide rectangle onto another metal layer."""
    return (rect[0], rect[1], rect[2], rect[3], layer)


def append_rect(
    net_name: str,
    rect: tuple[int, int, int, int, str],
    existing: list[tuple[int, int, int, int, str]],
    add_rect,
) -> None:
    """Record one injected rectangle in the working guide index."""
    add_rect(net_name, rect[4], rect[0], rect[1], rect[2], rect[3])
    existing.append(rect)


def layer_component_centroids(
    layer_rects: list[tuple[int, int, int, int, str]],
) -> list[tuple[int, int]]:
    """Return one centroid per same-layer connected guide component."""
    if len(layer_rects) < 2:
        return []
    parent = list(range(len(layer_rects)))

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(layer_rects)):
        for j in range(i + 1, len(layer_rects)):
            if rects_touch(layer_rects[i], layer_rects[j]):
                union(i, j)

    groups: dict[int, list[int]] = {}
    for idx in range(len(layer_rects)):
        root = find(idx)
        groups.setdefault(root, []).append(idx)

    centroids: list[tuple[int, int]] = []
    for indices in groups.values():
        cx = sum((layer_rects[i][0] + layer_rects[i][2]) // 2 for i in indices) // len(
            indices
        )
        cy = sum((layer_rects[i][1] + layer_rects[i][3]) // 2 for i in indices) // len(
            indices
        )
        centroids.append((cx, cy))
    return centroids


def connect_fragmented_components_on_layer(
    net_name: str,
    existing: list[tuple[int, int, int, int, str]],
    *,
    layer: str,
    gcell_step: int,
    add_rect,
    max_components: int = 200,
) -> None:
    """Star-connect disjoint guide components on one routing layer."""
    layer_rects = [rect for rect in existing if rect[4].lower() == layer.lower()]
    # Avoid quadratic connected-component analysis on dense nets during smoke tests.
    if len(layer_rects) > max_components:
        return
    centroids = layer_component_centroids(layer_rects)
    if len(centroids) <= 1 or len(centroids) > max_components:
        return
    hub_x, hub_y = centroids[0]
    for tx, ty in centroids[1:]:
        for bx1, by1, bx2, by2, bl in manhattan_bridge_rects(
            hub_x, hub_y, tx, ty, layer, gcell_step
        ):
            append_rect(net_name, (bx1, by1, bx2, by2, bl), existing, add_rect)


def connect_fragmented_components(
    net_name: str,
    existing: list[tuple[int, int, int, int, str]],
    *,
    subnet_index: dict[str, dict[str, object]],
    gcell_step: int,
    add_rect,
    max_components: int = 200,
) -> None:
    """Star-connect disjoint guide components on the die bridge layer."""
    layer = bridge_layer_for_subnet(net_name, subnet_index)
    if layer is None:
        return
    connect_fragmented_components_on_layer(
        net_name,
        existing,
        layer=layer,
        gcell_step=gcell_step,
        add_rect=add_rect,
        max_components=max_components,
    )


def stitch_layer_pair_guides(
    net_name: str,
    existing: list[tuple[int, int, int, int, str]],
    *,
    upper_layer: str,
    lower_layer: str,
    gcell_step: int,
    add_rect,
    max_stitches: int = 48,
) -> None:
    """Add matching upper/lower gcell boxes so 3D guide connectivity can form."""
    lower_rects = [rect for rect in existing if rect[4].lower() == lower_layer.lower()]
    upper_rects = [rect for rect in existing if rect[4].lower() == upper_layer.lower()]
    if not lower_rects or not upper_rects:
        return

    lower_centroids = layer_component_centroids(lower_rects)
    if not lower_centroids and lower_rects:
        rect = lower_rects[0]
        lower_centroids = [((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2)]
    if not lower_centroids:
        return

    stitches = 0
    for lx, ly in lower_centroids:
        nearest = nearest_rect_on_layer(upper_rects, upper_layer, lx, ly)
        if nearest is None:
            continue
        ux, uy = nearest
        stitch_x = (lx + ux) // 2
        stitch_y = (ly + uy) // 2
        x1, y1, x2, y2 = cover_box(stitch_x, stitch_y, gcell_step, radius=1)
        append_rect(
            net_name,
            (x1, y1, x2, y2, upper_layer),
            existing,
            add_rect,
        )
        append_rect(
            net_name,
            (x1, y1, x2, y2, lower_layer),
            existing,
            add_rect,
        )
        stitches += 1
        if stitches >= max_stitches:
            break


def stitch_bridge_stack_for_subnet(
    net_name: str,
    existing: list[tuple[int, int, int, int, str]],
    *,
    subnet_index: dict[str, dict[str, object]],
    gcell_step: int,
    add_rect,
    max_stitches: int = 48,
) -> None:
    """Connect bridge-layer guides to the routing layer directly below."""
    bridge_layer = bridge_layer_for_subnet(net_name, subnet_index)
    if bridge_layer is None:
        return
    below_layer = routing_layer_below(bridge_layer)
    if below_layer is None:
        return
    stitch_layer_pair_guides(
        net_name,
        existing,
        upper_layer=bridge_layer,
        lower_layer=below_layer,
        gcell_step=gcell_step,
        add_rect=add_rect,
        max_stitches=max_stitches,
    )


def mirror_bridge_to_below_layer(
    net_name: str,
    bridge_rect: tuple[int, int, int, int, str],
    *,
    below_layer: str,
    existing: list[tuple[int, int, int, int, str]],
    add_rect,
) -> None:
    """Duplicate one bridge-layer Manhattan segment on the layer below."""
    mirrored = duplicate_rect_on_layer(bridge_rect, below_layer)
    append_rect(net_name, mirrored, existing, add_rect)


def connect_two_pin_endpoints(
    net_name: str,
    pin_locs: list[tuple[int, int]],
    *,
    subnet_index: dict[str, dict[str, object]],
    gcell_step: int,
    add_rect,
    existing: list[tuple[int, int, int, int, str]],
) -> None:
    """Bridge the two pin sites on the die boundary layer for 2-pin split nets."""
    if len(pin_locs) != 2:
        return
    layer = bridge_layer_for_subnet(net_name, subnet_index)
    if layer is None:
        return
    below_layer = routing_layer_below(layer)
    (x, y), (tx, ty) = pin_locs
    for bx1, by1, bx2, by2, bl in manhattan_bridge_rects(
        x, y, tx, ty, layer, gcell_step
    ):
        bridge_rect = (bx1, by1, bx2, by2, bl)
        append_rect(net_name, bridge_rect, existing, add_rect)
        if below_layer is not None:
            mirror_bridge_to_below_layer(
                net_name,
                bridge_rect,
                below_layer=below_layer,
                existing=existing,
                add_rect=add_rect,
            )


def collect_hbt_covers(
    def_path: Path,
    guide_index: dict[str, list[tuple[int, int, int, int, str]]],
    *,
    gcell_step: int,
    cover_radius: int,
    subnet_index: dict[str, dict[str, object]],
) -> list[CoverRect]:
    """Build cover + bridge rects for every pin on HBT-split nets."""
    components = parse_components_multiline(def_path)
    covers: list[CoverRect] = []
    seen: set[tuple[str, str, int, int, int, int]] = set()

    def add_rect(net: str, layer: str, x1: int, y1: int, x2: int, y2: int) -> None:
        key = (net, layer, x1, y1, x2, y2)
        if key in seen:
            return
        seen.add(key)
        covers.append(CoverRect(net=net, layer=layer, x1=x1, y1=y1, x2=x2, y2=y2))

    processed_nets: list[
        tuple[str, list[tuple[int, int]], list[tuple[int, int, int, int, str]]]
    ] = []

    for net in parse_nets(def_path):
        has_hbt = any(HBT_INST_RE.match(pin_ref.inst) for pin_ref in net.pins)
        if not has_hbt:
            continue
        existing = list(guide_index.get(net.name, []))
        pin_locs: list[tuple[int, int]] = []
        for pin_ref in net.pins:
            layer = pin_routing_layer(net.name, pin_ref, subnet_index)
            if layer is None:
                continue
            loc = components.get(pin_ref.inst)
            if loc is None:
                continue
            px, py = hbt_pin_anchor(pin_ref.inst, loc, size=HBT_SIZE_DBU)
            pin_locs.append((px, py))
            add_pin_cover_bridge(
                net.name,
                px,
                py,
                layer,
                existing,
                gcell_step=gcell_step,
                cover_radius=cover_radius,
                add_rect=add_rect,
            )
        processed_nets.append((net.name, pin_locs, existing))

    if os.environ.get("HBT_POST_STITCH", "0") == "1":
        for net_name, pin_locs, existing in processed_nets:
            if not is_mol_split_net(net_name, subnet_index):
                continue
            bridge_layer = bridge_layer_for_subnet(net_name, subnet_index)
            below_layer = (
                routing_layer_below(bridge_layer) if bridge_layer is not None else None
            )
            max_cc = 500 if len(pin_locs) <= 2 else 200
            if below_layer is not None:
                connect_fragmented_components_on_layer(
                    net_name,
                    existing,
                    layer=below_layer,
                    gcell_step=gcell_step,
                    add_rect=add_rect,
                    max_components=max_cc,
                )
            connect_fragmented_components(
                net_name,
                existing,
                subnet_index=subnet_index,
                gcell_step=gcell_step,
                add_rect=add_rect,
                max_components=max_cc,
            )
            if len(pin_locs) == 2:
                connect_two_pin_endpoints(
                    net_name,
                    pin_locs,
                    subnet_index=subnet_index,
                    gcell_step=gcell_step,
                    add_rect=add_rect,
                    existing=existing,
                )
            stitch_bridge_stack_for_subnet(
                net_name,
                existing,
                subnet_index=subnet_index,
                gcell_step=gcell_step,
                add_rect=add_rect,
            )

    return covers


def hbt_pin_anchor(
    inst: str,
    origin: tuple[int, int],
    *,
    size: int = HBT_SIZE_DBU,
) -> tuple[int, int]:
    """Return the routing anchor for an HBT pin (macro center, not lower-left)."""
    if HBT_INST_RE.match(inst):
        half = size // 2
        return (origin[0] + half, origin[1] + half)
    return origin


def parse_guide_blocks(guide_path: Path) -> dict[str, list[str]]:
    """Parse route.guide into one rect-line list per net (merge duplicate blocks)."""
    rects_by_net: dict[str, list[str]] = {}
    cur_net: str | None = None

    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.strip()
            if stripped in ("(", ")"):
                if stripped == ")":
                    cur_net = None
                continue
            parts = stripped.split()
            if len(parts) >= 5 and METAL_RE.match(parts[-1]) and cur_net:
                rects_by_net.setdefault(cur_net, []).append(stripped)
                continue
            if len(parts) == 1:
                cur_net = parts[0]
                rects_by_net.setdefault(cur_net, [])
                continue
            if stripped.endswith("("):
                cur_net = stripped[:-1].strip()
                rects_by_net.setdefault(cur_net, [])

    return rects_by_net


def write_guide_blocks(guide_path: Path, rects_by_net: dict[str, list[str]]) -> None:
    """Write a de-duplicated route.guide with exactly one block per net."""
    with guide_path.open("w", encoding="utf-8") as guide_file:
        for net in sorted(rects_by_net):
            guide_file.write(f"{net}\n(\n")
            for rect_line in rects_by_net[net]:
                guide_file.write(f"{rect_line}\n")
            guide_file.write(")\n")


def merge_covers_into_guide(guide_path: Path, covers: list[CoverRect]) -> int:
    """Merge injected rects into existing guide blocks (no duplicate net headers)."""
    rects_by_net = parse_guide_blocks(guide_path)
    seen: dict[str, set[tuple[str, int, int, int, int]]] = {
        net: {
            (line.split()[-1], int(line.split()[0]), int(line.split()[1]), int(line.split()[2]), int(line.split()[3]))
            for line in lines
        }
        for net, lines in rects_by_net.items()
    }
    added = 0
    for cover in covers:
        rect_key = (cover.layer, cover.x1, cover.y1, cover.x2, cover.y2)
        if rect_key in seen.setdefault(cover.net, set()):
            continue
        seen[cover.net].add(rect_key)
        rects_by_net.setdefault(cover.net, []).append(
            f"{cover.x1} {cover.y1} {cover.x2} {cover.y2} {cover.layer}"
        )
        added += 1
    write_guide_blocks(guide_path, rects_by_net)
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("guide_path", type=Path)
    parser.add_argument("def_path", type=Path)
    parser.add_argument(
        "guide_out",
        type=Path,
        nargs="?",
        help="Output guide (default: append in-place to guide_path)",
    )
    parser.add_argument(
        "--gcell-step",
        type=int,
        default=int(os.environ.get("GCELL_STEP", DEFAULT_GCELL_STEP)),
    )
    parser.add_argument(
        "--cover-radius",
        type=int,
        default=int(os.environ.get("HBT_COVER_RADIUS", DEFAULT_COVER_RADIUS)),
    )
    args = parser.parse_args()

    out_path = args.guide_out or args.guide_path
    if out_path != args.guide_path:
        out_path.write_text(args.guide_path.read_text(encoding="utf-8"), encoding="utf-8")

    guide_index = parse_guide_index(out_path)
    results_dir = Path(os.environ.get("RESULTS_DIR", args.def_path.parent))
    manifest = load_share_manifest(manifest_path_from_env(results_dir))
    subnet_index = build_subnet_manifest_index(manifest)
    covers = collect_hbt_covers(
        args.def_path,
        guide_index,
        gcell_step=args.gcell_step,
        cover_radius=args.cover_radius,
        subnet_index=subnet_index,
    )
    added = merge_covers_into_guide(out_path, covers)
    print(f"Injected {added} HBT cover/bridge guide rects into {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
