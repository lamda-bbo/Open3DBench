#!/usr/bin/env python3
"""Insert HBT buffers and split cross-die (3D) nets in MoL post-CTS DEF.

Placement modes (HBT_PLACEMENT env):
  centroid - geometric center of all pin instance origins (legacy default)
  greedy   - minimize bottom + upper subnet bounding-box HPWL on coarse grid sites
"""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from mol_hbt_common import (
    ComponentInfo,
    NetRecord,
    PinRef,
    SKIPPED_3D_NETS,
    classify_all_nets,
    choose_hbt_type,
    centroid_for_pins,
    default_lef_paths,
    parse_components,
    parse_inst_die_map,
    parse_lef_pin_directions,
    parse_nets,
)
from hbt_placement_greedy import (
    CoreBbox,
    HbtOccupancyIndex,
    aligned_hbt_placement_core,
    default_aligned_hbt_grid,
    greedy_hbt_position,
    parse_core_bbox_from_env,
    pin_coords,
)


@dataclass(frozen=True)
class SplitPlan:
    """Plan for splitting one 3D net with an HBT buffer."""

    original_net: str
    hbt_idx: int
    hbt_cell: str
    hbt_inst: str
    hbt_x: int
    hbt_y: int
    bottom_pins: tuple[PinRef, ...]
    top_pins: tuple[PinRef, ...]
    bot_net: str
    top_net: str


def parse_die_bbox(def_path: Path) -> CoreBbox:
    """Read the physical DIEAREA from DEF in database units."""
    die_re = re.compile(r"^\s*DIEAREA\s+(.*?)\s*;\s*$")
    point_re = re.compile(r"\(\s*(-?\d+)\s+(-?\d+)\s*\)")
    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            match = die_re.match(line)
            if match is None:
                continue
            points = [
                (int(x), int(y)) for x, y in point_re.findall(match.group(1))
            ]
            if len(points) < 2:
                break
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            return CoreBbox(min(xs), min(ys), max(xs), max(ys))
    raise ValueError(f"Missing or invalid DIEAREA in {def_path}")


def intersect_bbox(lhs: CoreBbox, rhs: CoreBbox) -> CoreBbox:
    """Return the non-empty intersection of two placement rectangles."""
    result = CoreBbox(
        max(lhs.x_min, rhs.x_min),
        max(lhs.y_min, rhs.y_min),
        min(lhs.x_max, rhs.x_max),
        min(lhs.y_max, rhs.y_max),
    )
    if result.x_min >= result.x_max or result.y_min >= result.y_max:
        raise ValueError(f"Empty HBT placement region: {lhs} intersect {rhs}")
    return result


def build_split_plans(
    nets: list[NetRecord],
    inst_die_map: dict[str, str],
    components: dict[str, ComponentInfo],
    lef_dirs: dict[str, dict[str, str]],
    *,
    split_clocks: bool = True,
    placement_mode: str = "centroid",
    placement_core: CoreBbox | None = None,
) -> tuple[list[SplitPlan], dict[str, str]]:
    """Build HBT split plans for all cross-die nets."""
    classification = classify_all_nets(nets, inst_die_map)
    pending: list[tuple[NetRecord, tuple[PinRef, ...], tuple[PinRef, ...], str]] = []
    hbt_idx = 0

    for net in nets:
        if classification.get(net.name) != "3d":
            continue
        if not split_clocks and net.name in SKIPPED_3D_NETS:
            continue

        bottom_inst_pins = tuple(
            pin_ref
            for pin_ref in net.pins
            if inst_die_map.get(pin_ref.inst) == "bottom"
        )
        top_inst_pins = tuple(
            pin_ref
            for pin_ref in net.pins
            if inst_die_map.get(pin_ref.inst) == "upper"
        )
        if not bottom_inst_pins or not top_inst_pins:
            continue

        # MoL top-level ports are physically on the bottom die.  Choose the HBT
        # direction from component pins first, then retain ports on the bottom
        # subnet so DEF PINS and NETS keep the same electrical connectivity.
        hbt_cell = choose_hbt_type(
            bottom_inst_pins,
            top_inst_pins,
            components,
            lef_dirs,
        )
        bottom_pins = tuple(
            pin_ref for pin_ref in net.pins if pin_ref.inst == "PIN"
        ) + bottom_inst_pins
        top_pins = top_inst_pins
        pending.append((net, bottom_pins, top_pins, hbt_cell))
        hbt_idx += 1

    plans: list[SplitPlan] = []
    if placement_mode == "greedy":
        aligned_grid = default_aligned_hbt_grid()
        requested_core = (
            placement_core
            if placement_core is not None
            else parse_core_bbox_from_env()
        )
        core = aligned_hbt_placement_core(
            requested_core,
            aligned_grid,
        )
        occupancy_index = HbtOccupancyIndex(
            pitch=aligned_grid.hbt_pitch_x,
            size=aligned_grid.hbt_size,
        )
        order = sorted(
            range(len(pending)),
            key=lambda idx: (
                -(len(pending[idx][1]) + len(pending[idx][2])),
                pending[idx][0].name,
            ),
        )
        hubs: list[tuple[int, int]] = [(0, 0)] * len(pending)
        for idx in order:
            net, bottom_pins, top_pins, _ = pending[idx]
            bottom_xy = pin_coords(bottom_pins, components)
            top_xy = pin_coords(top_pins, components)
            hub = greedy_hbt_position(
                bottom_xy,
                top_xy,
                core=core,
                aligned_grid=aligned_grid,
                occupancy_index=occupancy_index,
            )
            hubs[idx] = hub
            occupancy_index.add(hub)
    else:
        hubs = []

    for idx, (net, bottom_pins, top_pins, hbt_cell) in enumerate(pending):
        if placement_mode == "greedy":
            cx, cy = hubs[idx]
        else:
            cx, cy = centroid_for_pins(net.pins, components)
        hbt_inst = f"{hbt_cell}_{idx}"
        plans.append(
            SplitPlan(
                original_net=net.name,
                hbt_idx=idx,
                hbt_cell=hbt_cell,
                hbt_inst=hbt_inst,
                hbt_x=cx,
                hbt_y=cy,
                bottom_pins=bottom_pins,
                top_pins=top_pins,
                bot_net=f"{net.name}_BOT",
                top_net=f"{net.name}_TOP",
            )
        )

    return plans, classification


def format_subnet_lines(
    net_name: str,
    pin_refs: tuple[PinRef, ...],
    hbt_inst: str,
    hbt_pin: str,
) -> list[str]:
    """Format one split subnet in DEF syntax."""
    lines = [f"- {net_name}"]
    for pin_ref in pin_refs:
        lines.append(f" ( {pin_ref.inst} {pin_ref.pin} )")
    lines.append(f" ( {hbt_inst} {hbt_pin} )")
    lines.append(" + USE SIGNAL ;")
    return lines


def rewrite_def(
    def_path: Path,
    output_path: Path,
    plans: list[SplitPlan],
) -> None:
    """Rewrite DEF with HBT components and split nets."""
    split_map = {plan.original_net: plan for plan in plans}
    pin_net_map = {
        plan.original_net: plan.bot_net
        for plan in plans
        if any(pin_ref.inst == "PIN" for pin_ref in plan.bottom_pins)
    }
    flat_hbt: list[str] = []
    for plan in plans:
        flat_hbt.append(f"  - {plan.hbt_inst} {plan.hbt_cell}")
        flat_hbt.append(f"    + COVER ( {plan.hbt_x} {plan.hbt_y} ) N ;")

    comp_count_re = re.compile(r"^(\s*COMPONENTS\s+)(\d+)(\s*;.*)$")
    net_count_re = re.compile(r"^(\s*NETS\s+)(\d+)(\s*;.*)$")
    pin_net_re = re.compile(r"(\+\s+NET\s+)(\S+)")

    with def_path.open(encoding="utf-8") as src, output_path.open(
        "w",
        encoding="utf-8",
    ) as dst:
        in_components = False
        in_pins = False
        in_nets = False
        net_buffer: list[str] = []
        current_net: str | None = None

        def flush_net() -> None:
            nonlocal net_buffer, current_net
            if current_net is None:
                return
            plan = split_map.get(current_net)
            if plan is None:
                dst.write("\n".join(net_buffer))
                dst.write("\n")
            else:
                bot_lines = format_subnet_lines(
                    plan.bot_net,
                    plan.bottom_pins,
                    plan.hbt_inst,
                    "BOT",
                )
                top_lines = format_subnet_lines(
                    plan.top_net,
                    plan.top_pins,
                    plan.hbt_inst,
                    "TOP",
                )
                dst.write("\n".join(bot_lines + top_lines))
                dst.write("\n")
            net_buffer = []
            current_net = None

        for line in src:
            stripped = line.strip()

            comp_match = comp_count_re.match(line)
            if comp_match:
                in_components = True
                old_count = int(comp_match.group(2))
                new_count = old_count + len(plans)
                dst.write(f"{comp_match.group(1)}{new_count}{comp_match.group(3)}\n")
                continue

            net_match = net_count_re.match(line)
            if net_match:
                in_nets = True
                old_count = int(net_match.group(2))
                new_count = old_count + len(plans)
                dst.write(f"{net_match.group(1)}{new_count}{net_match.group(3)}\n")
                continue

            if stripped.startswith("COMPONENTS"):
                in_components = True
                dst.write(line)
                continue

            if in_components and stripped.startswith("END COMPONENTS"):
                for hbt_line in flat_hbt:
                    dst.write(hbt_line + "\n")
                in_components = False
                dst.write(line)
                continue

            if stripped.startswith("PINS"):
                in_pins = True
                dst.write(line)
                continue

            if in_pins and stripped.startswith("END PINS"):
                in_pins = False
                dst.write(line)
                continue

            if in_pins:
                pin_net_match = pin_net_re.search(line)
                if pin_net_match:
                    old_net = pin_net_match.group(2)
                    new_net = pin_net_map.get(old_net)
                    if new_net is not None:
                        line = (
                            line[: pin_net_match.start(2)]
                            + new_net
                            + line[pin_net_match.end(2) :]
                        )
                dst.write(line)
                continue

            if stripped.startswith("NETS"):
                in_nets = True
                dst.write(line)
                continue

            if in_nets and stripped.startswith("END NETS"):
                flush_net()
                in_nets = False
                dst.write(line)
                continue

            if in_nets and stripped.startswith("- "):
                flush_net()
                current_net = stripped.split()[1]
                net_buffer = [line.rstrip("\n")]
                if ";" in stripped:
                    flush_net()
                continue

            if in_nets and current_net is not None:
                net_buffer.append(line.rstrip("\n"))
                if ";" in stripped:
                    flush_net()
                continue

            dst.write(line)

        if net_buffer:
            flush_net()


def write_report(
    report_path: Path,
    plans: list[SplitPlan],
    classification: dict[str, str],
    *,
    placement_mode: str,
) -> None:
    """Write a short split summary for debugging."""
    n3d = sum(1 for label in classification.values() if label == "3d")
    with report_path.open("w", encoding="utf-8") as report_file:
        report_file.write(f"placement_mode={placement_mode}\n")
        report_file.write(f"3d_nets_in_def={n3d}\n")
        report_file.write(f"hbt_inserted={len(plans)}\n")
        report_file.write(f"botin={sum(1 for p in plans if p.hbt_cell == 'HBT_BOTIN')}\n")
        report_file.write(f"topin={sum(1 for p in plans if p.hbt_cell == 'HBT_TOPIN')}\n")
        for plan in plans[:10]:
            report_file.write(
                f"sample {plan.original_net} -> {plan.bot_net}/{plan.top_net} "
                f"{plan.hbt_inst} @ ({plan.hbt_x},{plan.hbt_y})\n"
            )


def main() -> int:
    results_dir = Path(os.environ.get("RESULTS_DIR", "."))
    def_path = results_dir / "4_1_cts.def"
    if not def_path.exists():
        print(f"ERROR: missing {def_path}", file=sys.stderr)
        return 1

    split_clocks = os.environ.get("MOL_HBT_SPLIT_CLOCKS", "1") == "1"
    placement_mode = os.environ.get("HBT_PLACEMENT", "centroid").strip().lower() or "centroid"
    if placement_mode not in {"centroid", "greedy"}:
        print(f"ERROR: unknown HBT_PLACEMENT={placement_mode}", file=sys.stderr)
        return 2
    lef_paths = default_lef_paths()
    lef_dirs = parse_lef_pin_directions(lef_paths)

    inst_die_map = parse_inst_die_map(def_path)
    components = parse_components(def_path)
    nets = parse_nets(def_path)
    placement_core = intersect_bbox(
        parse_core_bbox_from_env(),
        parse_die_bbox(def_path),
    )
    plans, classification = build_split_plans(
        nets,
        inst_die_map,
        components,
        lef_dirs,
        split_clocks=split_clocks,
        placement_mode=placement_mode,
        placement_core=placement_core,
    )

    backup_path = results_dir / "4_1_cts.pre_hbt.def"
    output_path = results_dir / "4_1_cts.hbt.def"
    if not backup_path.exists():
        backup_path.write_bytes(def_path.read_bytes())

    rewrite_def(def_path, output_path, plans)
    output_path.replace(def_path)

    report_path = results_dir / "mol_hbt_split.rpt"
    write_report(report_path, plans, classification, placement_mode=placement_mode)
    print(
        f"MOL HBT split ({placement_mode}): inserted {len(plans)} HBT buffers, "
        f"report={report_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
