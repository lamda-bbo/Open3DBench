#!/usr/bin/env python3
"""Shared helpers for MoL HBT insertion and die-aware GRT net classification."""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

BOTTOM_MAX_LAYER = 10
UPPER_MIN_LAYER = 11

# Clock/reset nets kept unsplit in LoL; MoL die-by-die flow may still split them.
SKIPPED_3D_NETS = frozenset(
    {
        "clk_i",
        "rst_n_i",
        "clk",
        "p_bsg_tag_clk_i",
        "p_clk_A_i",
        "p_clk_B_i",
        "p_clk_C_i",
        "p_ci_clk_i",
        "p_ci2_tkn_i",
        "p_co_clk_i",
        "p_co2_tkn_i",
    }
)

OUTPUT_PIN_NAMES = frozenset(
    {
        "Z",
        "Q",
        "Y",
        "ZN",
        "QN",
        "CO",
        "SO",
        "O",
        "OA",
        "OB",
        "OP",
        "ON",
        "NC",
        "CON",
        "OUT",
    }
)

NET_HEADER_RE = re.compile(r"^\s*-\s+(\S+)")
PIN_CONN_RE = re.compile(r"\(\s*(\S+)\s+(\S+)\s*\)")
MACRO_RE = re.compile(r"^MACRO\s+(\S+)")
PIN_DIR_RE = re.compile(r"^\s*PIN\s+(\S+)")
DIRECTION_RE = re.compile(r"^\s*DIRECTION\s+(INPUT|OUTPUT|INOUT)\s*;")


@dataclass(frozen=True)
class PinRef:
    """Reference to one instance pin on a net."""

    inst: str
    pin: str


@dataclass(frozen=True)
class ComponentInfo:
    """Placed component metadata from DEF."""

    inst: str
    cell: str
    die: str
    x: int
    y: int


@dataclass(frozen=True)
class NetRecord:
    """One DEF net and its pin connections."""

    name: str
    pins: tuple[PinRef, ...]
    raw_lines: tuple[str, ...]


def name_die(name: str) -> str | None:
    """Return die id from instance or cell naming convention."""
    if name.endswith("_bottom") or name.startswith("HBT_BOTIN_"):
        return "bottom"
    if name.endswith("_upper") or name.startswith("HBT_TOPIN_"):
        return "upper"
    return None


def parse_inst_die_map(def_path: Path) -> dict[str, str]:
    """Map instance name -> bottom|upper using DEF component lines."""
    inst_die_map: dict[str, str] = {}
    in_components = False

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("COMPONENTS"):
                in_components = True
                continue
            if in_components and stripped.startswith("END COMPONENTS"):
                break
            if not in_components or not stripped.startswith("- "):
                continue
            parts = stripped.split()
            if len(parts) < 3:
                continue
            inst = parts[1]
            cell = parts[2]
            die = name_die(inst) or name_die(cell)
            if die:
                inst_die_map[inst] = die

    return inst_die_map


def parse_components(def_path: Path) -> dict[str, ComponentInfo]:
    """Parse DEF components with placement coordinates."""
    components: dict[str, ComponentInfo] = {}
    in_components = False
    current_inst: str | None = None
    current_cell: str | None = None

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
                if len(parts) >= 3:
                    current_inst = parts[1]
                    current_cell = parts[2]
                    if "PLACED" in stripped or "FIXED" in stripped or "COVER" in stripped:
                        open_idx = parts.index("(") if "(" in parts else -1
                        if open_idx >= 0 and open_idx + 2 < len(parts):
                            x_val = int(parts[open_idx + 1])
                            y_val = int(parts[open_idx + 2])
                            die = name_die(current_inst) or name_die(current_cell) or "unknown"
                            components[current_inst] = ComponentInfo(
                                inst=current_inst,
                                cell=current_cell,
                                die=die,
                                x=x_val,
                                y=y_val,
                            )
                            current_inst = None
                            current_cell = None
                continue

            if current_inst is None or current_cell is None:
                continue

            if "PLACED" not in stripped and "FIXED" not in stripped:
                continue

            parts = stripped.split()
            if "(" not in parts:
                continue
            open_idx = parts.index("(")
            x_val = int(parts[open_idx + 1])
            y_val = int(parts[open_idx + 2])
            die = name_die(current_inst) or name_die(current_cell) or "unknown"
            components[current_inst] = ComponentInfo(
                inst=current_inst,
                cell=current_cell,
                die=die,
                x=x_val,
                y=y_val,
            )

    return components


def parse_lef_pin_directions(lef_paths: Iterable[Path]) -> dict[str, dict[str, str]]:
    """Build cell -> {pin_name: direction} from LEF files."""
    directions: dict[str, dict[str, str]] = defaultdict(dict)

    for lef_path in lef_paths:
        if not lef_path.exists():
            continue
        current_macro: str | None = None
        current_pin: str | None = None
        with lef_path.open(encoding="utf-8", errors="ignore") as lef_file:
            for line in lef_file:
                macro_match = MACRO_RE.match(line)
                if macro_match:
                    current_macro = macro_match.group(1)
                    current_pin = None
                    continue
                if line.startswith("END ") and current_macro:
                    current_macro = None
                    current_pin = None
                    continue
                pin_match = PIN_DIR_RE.match(line)
                if pin_match and current_macro:
                    current_pin = pin_match.group(1)
                    continue
                dir_match = DIRECTION_RE.match(line)
                if dir_match and current_macro and current_pin:
                    directions[current_macro][current_pin] = dir_match.group(1)
                    current_pin = None

    return directions


def default_lef_paths() -> list[Path]:
    """Resolve platform LEF paths from environment."""
    platform_dir = Path(os.environ.get("PLATFORM_DIR", "platforms/nangate45_3D"))
    return [
        platform_dir / "lef_bottom/NangateOpenCellLibrary.macro.mod.bottom.lef",
        platform_dir / "lef_upper/NangateOpenCellLibrary.macro.mod.upper.lef",
        platform_dir / "lef_upper/fakeram45_256x16.upper.lef",
    ]


def pin_direction(
    cell: str,
    pin: str,
    lef_dirs: dict[str, dict[str, str]],
) -> str:
    """Return INPUT|OUTPUT|INOUT|UNKNOWN for a cell pin."""
    cell_dirs = lef_dirs.get(cell)
    if cell_dirs and pin in cell_dirs:
        return cell_dirs[pin]
    if pin in OUTPUT_PIN_NAMES:
        return "OUTPUT"
    return "UNKNOWN"


def parse_nets(def_path: Path) -> list[NetRecord]:
    """Parse all DEF nets into NetRecord objects."""
    nets: list[NetRecord] = []
    in_nets = False
    current_name: str | None = None
    current_lines: list[str] = []
    current_pins: list[PinRef] = []

    def flush_net() -> None:
        nonlocal current_name, current_lines, current_pins
        if current_name is None:
            return
        nets.append(
            NetRecord(
                name=current_name,
                pins=tuple(current_pins),
                raw_lines=tuple(current_lines),
            )
        )
        current_name = None
        current_lines = []
        current_pins = []

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("NETS"):
                in_nets = True
                continue
            if in_nets and stripped.startswith("END NETS"):
                flush_net()
                break
            if not in_nets:
                continue

            if stripped.startswith("- "):
                flush_net()
                header_match = NET_HEADER_RE.match(stripped)
                if not header_match:
                    continue
                current_name = header_match.group(1)
                current_lines = [line.rstrip("\n")]
                rest = stripped[len("- " + current_name) :].strip()
                for inst, pin_name in PIN_CONN_RE.findall(rest):
                    if inst != "PIN":
                        current_pins.append(PinRef(inst=inst, pin=pin_name))
                continue

            if current_name is None:
                continue

            current_lines.append(line.rstrip("\n"))
            for inst, pin_name in PIN_CONN_RE.findall(stripped):
                if inst != "PIN":
                    current_pins.append(PinRef(inst=inst, pin=pin_name))

    return nets


def count_net_routing_terminals(net: NetRecord) -> int:
    """Count DEF net terminals including top-level PORT and instance pins."""
    total = 0
    for line in net.raw_lines:
        total += len(PIN_CONN_RE.findall(line))
    return total


def classify_net_pins(
    net_name: str,
    pins: tuple[PinRef, ...],
    inst_die_map: dict[str, str],
) -> str:
    """Classify net as 2d_bottom | 2d_upper | 3d | unknown."""
    if net_name.endswith("_BOT"):
        return "2d_bottom"
    if net_name.endswith("_TOP"):
        return "2d_upper"

    dies: set[str] = set()
    for pin_ref in pins:
        die = inst_die_map.get(pin_ref.inst)
        if die:
            dies.add(die)
        elif pin_ref.inst.startswith("HBT_") or pin_ref.inst.startswith("LS_HBT_"):
            if pin_ref.pin == "BOT":
                dies.add("bottom")
            elif pin_ref.pin == "TOP":
                dies.add("upper")
    if "bottom" in dies and "upper" in dies:
        return "3d"
    if dies == {"bottom"}:
        return "2d_bottom"
    if dies == {"upper"}:
        return "2d_upper"
    return "unknown"


def classify_all_nets(
    nets: list[NetRecord],
    inst_die_map: dict[str, str],
) -> dict[str, str]:
    """Return mapping net_name -> classification label."""
    return {
        net.name: classify_net_pins(net.name, net.pins, inst_die_map)
        for net in nets
    }


def choose_hbt_type(
    bottom_pins: tuple[PinRef, ...],
    top_pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
    lef_dirs: dict[str, dict[str, str]],
) -> str:
    """Return HBT_BOTIN or HBT_TOPIN following LoL driver-die rule."""
    for pin_ref in bottom_pins:
        comp = components.get(pin_ref.inst)
        if comp is None:
            continue
        if pin_direction(comp.cell, pin_ref.pin, lef_dirs) == "OUTPUT":
            return "HBT_BOTIN"

    for pin_ref in top_pins:
        comp = components.get(pin_ref.inst)
        if comp is None:
            continue
        if pin_direction(comp.cell, pin_ref.pin, lef_dirs) == "OUTPUT":
            return "HBT_TOPIN"

    if len(bottom_pins) >= len(top_pins):
        return "HBT_BOTIN"
    return "HBT_TOPIN"


def centroid_for_pins(
    pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
) -> tuple[int, int]:
    """Compute geometric center of instance origins for all pins on a net."""
    xs: list[int] = []
    ys: list[int] = []
    for pin_ref in pins:
        comp = components.get(pin_ref.inst)
        if comp is None:
            continue
        xs.append(comp.x)
        ys.append(comp.y)
    if not xs:
        return 0, 0
    return sum(xs) // len(xs), sum(ys) // len(ys)
