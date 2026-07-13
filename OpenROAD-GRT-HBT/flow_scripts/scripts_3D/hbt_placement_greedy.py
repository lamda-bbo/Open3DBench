#!/usr/bin/env python3
"""Greedy HBT placement minimizing bottom + upper subnet bounding-box HPWL."""

from __future__ import annotations

import os
from dataclasses import dataclass

from mol_hbt_common import ComponentInfo, PinRef

# HBT macro size from LEF (microns); DEF uses 2000 DBU/um.
HBT_SIZE_DBU = int(os.environ.get("HBT_SIZE_DBU", "2000"))
# metal10/m11 track pitch from make_tracks.tcl (microns).
METAL_PITCH_UM = float(os.environ.get("METAL_PITCH_UM", "1.6"))
METAL_TRACK_OFFSET_X_UM = float(os.environ.get("METAL_TRACK_OFFSET_X_UM", "0.095"))
METAL_TRACK_OFFSET_Y_UM = float(os.environ.get("METAL_TRACK_OFFSET_Y_UM", "0.07"))
# hb_layer via center pitch tracks metal10/m11 (1.6 um); must match make_tracks.
HBT_PITCH_UM = float(os.environ.get("HBT_PITCH_UM", str(METAL_PITCH_UM)))
HBT_PITCH_DBU = int(os.environ.get("HBT_PITCH_DBU", "0"))
# Greedy search step = HBT pitch * coarse factor (default 4 -> 6.4 um).
HBT_GRID_COARSE_FACTOR = int(os.environ.get("HBT_GRID_COARSE_FACTOR", "4"))


@dataclass(frozen=True)
class AlignedHbtGrid:
    """Placement lattice aligned to metal tracks and hb_layer pitch."""

    metal_pitch_x: int
    metal_pitch_y: int
    metal_offset_x: int
    metal_offset_y: int
    hbt_pitch_x: int
    hbt_pitch_y: int
    search_step_x: int
    search_step_y: int
    hbt_size: int

    @property
    def origin_offset_x(self) -> int:
        """Lower-left origin lattice offset so HBT center sits on metal tracks."""
        return self.metal_offset_x - self.hbt_size // 2

    @property
    def origin_offset_y(self) -> int:
        """Lower-left origin lattice offset so HBT center sits on metal tracks."""
        return self.metal_offset_y - self.hbt_size // 2

    def snap_origin(self, x: int, y: int) -> tuple[int, int]:
        """Snap HBT lower-left origin to the aligned coarse search lattice."""
        sx = (
            int(round((x - self.origin_offset_x) / self.search_step_x))
            * self.search_step_x
            + self.origin_offset_x
        )
        sy = (
            int(round((y - self.origin_offset_y) / self.search_step_y))
            * self.search_step_y
            + self.origin_offset_y
        )
        return sx, sy

    def center_on_metal_track(self, origin: tuple[int, int]) -> bool:
        """Return True when HBT macro center aligns with metal10/m11 tracks."""
        cx, cy = hbt_center_from_origin(origin[0], origin[1], size=self.hbt_size)
        on_x = (cx - self.metal_offset_x) % self.metal_pitch_x == 0
        on_y = (cy - self.metal_offset_y) % self.metal_pitch_y == 0
        return on_x and on_y


def _dbu_per_um() -> int:
    return int(os.environ.get("DEF_DISTANCE_DBU", "2000"))


def _um_to_dbu(value_um: float) -> int:
    return int(round(value_um * _dbu_per_um()))


def default_aligned_hbt_grid() -> AlignedHbtGrid:
    """Build the default metal/HBT-aligned placement lattice from environment."""
    metal_pitch_x = _um_to_dbu(METAL_PITCH_UM)
    metal_pitch_y = metal_pitch_x
    metal_offset_x = _um_to_dbu(METAL_TRACK_OFFSET_X_UM)
    metal_offset_y = _um_to_dbu(METAL_TRACK_OFFSET_Y_UM)

    hbt_pitch_x = (
        HBT_PITCH_DBU if HBT_PITCH_DBU > 0 else _um_to_dbu(HBT_PITCH_UM)
    )
    hbt_pitch_y = hbt_pitch_x
    coarse = max(1, HBT_GRID_COARSE_FACTOR)
    search_step_x = int(
        os.environ.get("HBT_GRID_X_DBU", str(hbt_pitch_x * coarse))
    )
    search_step_y = int(
        os.environ.get("HBT_GRID_Y_DBU", str(hbt_pitch_y * coarse))
    )
    if search_step_x % hbt_pitch_x != 0 or search_step_y % hbt_pitch_y != 0:
        msg = (
            "HBT search step must be a multiple of HBT pitch: "
            f"step=({search_step_x},{search_step_y}) hbt=({hbt_pitch_x},{hbt_pitch_y})"
        )
        raise ValueError(msg)
    if hbt_pitch_x % metal_pitch_x != 0 or hbt_pitch_y % metal_pitch_y != 0:
        msg = (
            "HBT pitch must be a multiple of metal pitch: "
            f"hbt=({hbt_pitch_x},{hbt_pitch_y}) metal=({metal_pitch_x},{metal_pitch_y})"
        )
        raise ValueError(msg)
    if hbt_pitch_x < 2 * (HBT_SIZE_DBU // 2):
        msg = f"HBT pitch {hbt_pitch_x} DBU is below hb_layer minimum center spacing"
        raise ValueError(msg)

    return AlignedHbtGrid(
        metal_pitch_x=metal_pitch_x,
        metal_pitch_y=metal_pitch_y,
        metal_offset_x=metal_offset_x,
        metal_offset_y=metal_offset_y,
        hbt_pitch_x=hbt_pitch_x,
        hbt_pitch_y=hbt_pitch_y,
        search_step_x=search_step_x,
        search_step_y=search_step_y,
        hbt_size=HBT_SIZE_DBU,
    )


DEFAULT_ALIGNED_GRID = default_aligned_hbt_grid()
DEFAULT_GRID_X_DBU = DEFAULT_ALIGNED_GRID.search_step_x
DEFAULT_GRID_Y_DBU = DEFAULT_ALIGNED_GRID.search_step_y
# 导出默认 HBT pitch，供测试与外部脚本读取。
HBT_PITCH_DBU = DEFAULT_ALIGNED_GRID.hbt_pitch_x


@dataclass(frozen=True)
class CoreBbox:
    """Placement core rectangle in DBU."""

    x_min: int
    y_min: int
    x_max: int
    y_max: int

    def contains(self, x: int, y: int) -> bool:
        """Return True when (x, y) lies inside the core bbox."""
        return self.x_min <= x <= self.x_max and self.y_min <= y <= self.y_max

    def contains_hbt_origin(self, x: int, y: int, *, size: int) -> bool:
        """Return True when a size×size HBT at (x, y) fits inside the core."""
        return (
            self.x_min <= x
            and self.y_min <= y
            and x + size <= self.x_max
            and y + size <= self.y_max
        )


@dataclass(frozen=True)
class OccupiedRect:
    """Axis-aligned rectangle reserved for a placed HBT."""

    x1: int
    y1: int
    x2: int
    y2: int

    def overlaps(self, other: OccupiedRect) -> bool:
        """Return True when two rectangles overlap."""
        return not (
            self.x2 <= other.x1
            or other.x2 <= self.x1
            or self.y2 <= other.y1
            or other.y2 <= self.y1
        )


def parse_core_bbox_from_env() -> CoreBbox:
    """Read CORE_AREA from environment (microns) and convert to DBU."""
    raw = os.environ.get("CORE_AREA", "0 0 1000 1000")
    parts = [float(v) for v in raw.split()]
    if len(parts) != 4:
        msg = f"Invalid CORE_AREA: {raw}"
        raise ValueError(msg)
    dbu = _dbu_per_um()
    return CoreBbox(
        x_min=int(parts[0] * dbu),
        y_min=int(parts[1] * dbu),
        x_max=int(parts[2] * dbu),
        y_max=int(parts[3] * dbu),
    )


def _first_lattice_at_or_above(value: int, origin: int, pitch: int) -> int:
    """Return the smallest lattice point >= value."""
    if value <= origin:
        return origin
    return origin + ((value - origin + pitch - 1) // pitch) * pitch


def _last_lattice_at_or_below(limit: int, origin: int, pitch: int) -> int:
    """Return the largest lattice point <= limit."""
    if limit < origin:
        return origin
    return origin + ((limit - origin) // pitch) * pitch


def aligned_hbt_placement_core(
    core: CoreBbox,
    grid: AlignedHbtGrid,
) -> CoreBbox:
    """Snap core bounds inward so HBT origins align with the metal/via grid."""
    size = grid.hbt_size
    x_lo = _first_lattice_at_or_above(core.x_min, grid.origin_offset_x, grid.hbt_pitch_x)
    y_lo = _first_lattice_at_or_above(core.y_min, grid.origin_offset_y, grid.hbt_pitch_y)
    x_hi = _last_lattice_at_or_below(
        core.x_max - size,
        grid.origin_offset_x,
        grid.hbt_pitch_x,
    )
    y_hi = _last_lattice_at_or_below(
        core.y_max - size,
        grid.origin_offset_y,
        grid.hbt_pitch_y,
    )
    return CoreBbox(x_min=x_lo, y_min=y_lo, x_max=x_hi, y_max=y_hi)


def pin_coords(
    pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
) -> list[tuple[int, int]]:
    """Return placed instance origins for pin refs."""
    coords: list[tuple[int, int]] = []
    for pin_ref in pins:
        comp = components.get(pin_ref.inst)
        if comp is None:
            continue
        coords.append((comp.x, comp.y))
    return coords


def hpwl_max_min(
    pin_xy: list[tuple[int, int]],
    hub: tuple[int, int],
) -> int:
    """Half-perimeter wirelength: (max_x - min_x) + (max_y - min_y) over pins + hub."""
    if not pin_xy:
        return 0
    xs = [px for px, _ in pin_xy] + [hub[0]]
    ys = [py for _, py in pin_xy] + [hub[1]]
    return (max(xs) - min(xs)) + (max(ys) - min(ys))


def combined_hpwl_cost(
    bottom_xy: list[tuple[int, int]],
    top_xy: list[tuple[int, int]],
    hub: tuple[int, int],
) -> int:
    """Total HPWL for _BOT and _TOP subnets sharing one HBT hub."""
    return hpwl_max_min(bottom_xy, hub) + hpwl_max_min(top_xy, hub)


def hbt_center_from_origin(x: int, y: int, size: int = HBT_SIZE_DBU) -> tuple[int, int]:
    """Return HBT macro center from its DEF lower-left origin."""
    half = size // 2
    return (x + half, y + half)


def hbt_rect_at(x: int, y: int, size: int = HBT_SIZE_DBU) -> OccupiedRect:
    """Build the occupancy rectangle for one HBT at its lower-left origin."""
    return OccupiedRect(x, y, x + size, y + size)


def violates_hbt_pitch(
    origin: tuple[int, int],
    occupied_origins: tuple[tuple[int, int], ...],
    *,
    pitch: int = HBT_PITCH_DBU,
    size: int = HBT_SIZE_DBU,
) -> bool:
    """Return True when origin is closer than pitch to any placed HBT center."""
    cx, cy = hbt_center_from_origin(origin[0], origin[1], size=size)
    pitch_sq = pitch * pitch
    for ox, oy in occupied_origins:
        ocx, ocy = hbt_center_from_origin(ox, oy, size=size)
        dx = cx - ocx
        dy = cy - ocy
        if dx * dx + dy * dy < pitch_sq:
            return True
    return False


def build_candidate_hubs(
    bottom_xy: list[tuple[int, int]],
    top_xy: list[tuple[int, int]],
    *,
    aligned_grid: AlignedHbtGrid,
) -> list[tuple[int, int]]:
    """Generate snapped candidate HBT locations for one 3D net."""
    all_xy = bottom_xy + top_xy
    if not all_xy:
        return [aligned_grid.snap_origin(0, 0)]

    xs = sorted(coord[0] for coord in all_xy)
    ys = sorted(coord[1] for coord in all_xy)
    median_x = xs[len(xs) // 2]
    median_y = ys[len(ys) // 2]

    candidates: set[tuple[int, int]] = set()
    candidates.add(aligned_grid.snap_origin(median_x, median_y))

    for px, py in all_xy:
        candidates.add(aligned_grid.snap_origin(px, py))

    for bx, by in bottom_xy:
        for tx, ty in top_xy:
            mid_x = (bx + tx) // 2
            mid_y = (by + ty) // 2
            candidates.add(aligned_grid.snap_origin(mid_x, mid_y))

    return list(candidates)


def spiral_offsets(max_ring: int, step_x: int, step_y: int) -> list[tuple[int, int]]:
    """Generate grid offsets around a seed in expanding Manhattan rings."""
    offsets: list[tuple[int, int]] = [(0, 0)]
    for ring in range(1, max_ring + 1):
        for dx in range(-ring, ring + 1):
            for dy in range(-ring, ring + 1):
                if max(abs(dx), abs(dy)) != ring:
                    continue
                offsets.append((dx * step_x, dy * step_y))
    return offsets


def greedy_hbt_position(
    bottom_xy: list[tuple[int, int]],
    top_xy: list[tuple[int, int]],
    *,
    core: CoreBbox,
    occupied: tuple[tuple[int, int], ...] = (),
    aligned_grid: AlignedHbtGrid | None = None,
) -> tuple[int, int]:
    """Pick a legal hub minimizing combined subnet bounding-box HPWL (greedy per net)."""
    grid = aligned_grid if aligned_grid is not None else DEFAULT_ALIGNED_GRID
    candidates = build_candidate_hubs(bottom_xy, top_xy, aligned_grid=grid)
    ranked = sorted(
        candidates,
        key=lambda hub: combined_hpwl_cost(bottom_xy, top_xy, hub),
    )

    for hub in ranked:
        if not core.contains_hbt_origin(hub[0], hub[1], size=grid.hbt_size):
            continue
        if not grid.center_on_metal_track(hub):
            continue
        if violates_hbt_pitch(
            hub,
            occupied,
            pitch=grid.hbt_pitch_x,
            size=grid.hbt_size,
        ):
            continue
        return hub

    seed = ranked[0]
    for max_ring in range(1, 51):
        for dx, dy in spiral_offsets(
            max_ring=max_ring,
            step_x=grid.search_step_x,
            step_y=grid.search_step_y,
        ):
            hx, hy = grid.snap_origin(seed[0] + dx, seed[1] + dy)
            if not core.contains_hbt_origin(hx, hy, size=grid.hbt_size):
                continue
            hub = (hx, hy)
            if not grid.center_on_metal_track(hub):
                continue
            if violates_hbt_pitch(
                hub,
                occupied,
                pitch=grid.hbt_pitch_x,
                size=grid.hbt_size,
            ):
                continue
            return hub

    return seed


def greedy_placements_for_nets(
    net_specs: list[tuple[list[tuple[int, int]], list[tuple[int, int]], int]],
    *,
    core: CoreBbox | None = None,
    aligned_grid: AlignedHbtGrid | None = None,
) -> list[tuple[int, int]]:
    """Place HBTs greedily for many nets; harder nets (more pins) first."""
    grid = aligned_grid if aligned_grid is not None else DEFAULT_ALIGNED_GRID
    bbox = aligned_hbt_placement_core(
        core if core is not None else parse_core_bbox_from_env(),
        grid,
    )
    occupied: list[tuple[int, int]] = []
    order = sorted(
        range(len(net_specs)),
        key=lambda idx: (
            -(len(net_specs[idx][0]) + len(net_specs[idx][1])),
            net_specs[idx][2],
        ),
    )
    placements: list[tuple[int, int]] = [(0, 0)] * len(net_specs)

    for idx in order:
        bottom_xy, top_xy, _ = net_specs[idx]
        frozen_occupied = tuple(occupied)
        hub = greedy_hbt_position(
            bottom_xy,
            top_xy,
            core=bbox,
            occupied=frozen_occupied,
            aligned_grid=grid,
        )
        placements[idx] = hub
        occupied.append(hub)

    return placements
