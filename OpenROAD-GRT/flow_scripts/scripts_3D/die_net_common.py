#!/usr/bin/env python3
"""DEF parsing and die-aware net classification for global routing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

BOTTOM_MAX_LAYER = 10
UPPER_MIN_LAYER = 11

NET_HEADER_RE = re.compile(r"^\s*-\s+(\S+)")
PIN_CONN_RE = re.compile(r"\(\s*(\S+)\s+(\S+)\s*\)")
DEF_LAYER_RE = re.compile(r"\+\s+LAYER\s+(\S+)", re.IGNORECASE)
METAL_LAYER_RE = re.compile(r"^metal(\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class PinRef:
    """Reference to one instance pin on a net."""

    inst: str
    pin: str


@dataclass(frozen=True)
class NetRecord:
    """One DEF net and its pin connections."""

    name: str
    pins: tuple[PinRef, ...]


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


def routing_layer_die(layer_name: str) -> str | None:
    """Map a numbered metal layer to its physical die."""
    match = METAL_LAYER_RE.match(layer_name)
    if match is None:
        return None
    layer_num = int(match.group(1))
    if layer_num <= BOTTOM_MAX_LAYER:
        return "bottom"
    if layer_num >= UPPER_MIN_LAYER:
        return "upper"
    return None


def parse_pin_die_map(def_path: Path) -> dict[str, str]:
    """Map top-level DEF pin names to bottom|upper from their routing layers."""
    pin_die_map: dict[str, str] = {}
    in_pins = False
    current_pin: str | None = None
    current_layers: set[str] = set()

    def flush_pin() -> None:
        nonlocal current_pin, current_layers
        if current_pin is None:
            return
        dies = {
            die
            for layer in current_layers
            if (die := routing_layer_die(layer)) is not None
        }
        if len(dies) > 1:
            layers = ", ".join(sorted(current_layers))
            raise ValueError(
                f"DEF pin {current_pin} spans both dies through layers: {layers}"
            )
        if dies:
            pin_die_map[current_pin] = next(iter(dies))
        current_pin = None
        current_layers = set()

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("PINS"):
                in_pins = True
                continue
            if in_pins and stripped.startswith("END PINS"):
                flush_pin()
                break
            if not in_pins:
                continue

            if stripped.startswith("- "):
                flush_pin()
                parts = stripped.split()
                current_pin = parts[1] if len(parts) >= 2 else None
            if current_pin is not None:
                current_layers.update(DEF_LAYER_RE.findall(line))
                if ";" in line:
                    flush_pin()

    return pin_die_map


def parse_nets(def_path: Path) -> list[NetRecord]:
    """Parse all DEF nets into NetRecord objects."""
    nets: list[NetRecord] = []
    in_nets = False
    current_name: str | None = None
    current_pins: list[PinRef] = []

    def flush_net() -> None:
        nonlocal current_name, current_pins
        if current_name is None:
            return
        nets.append(
            NetRecord(
                name=current_name,
                pins=tuple(current_pins),
            )
        )
        current_name = None
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
                rest = stripped[len("- " + current_name) :].strip()
                for inst, pin_name in PIN_CONN_RE.findall(rest):
                    current_pins.append(PinRef(inst=inst, pin=pin_name))
                continue

            if current_name is None:
                continue

            for inst, pin_name in PIN_CONN_RE.findall(stripped):
                current_pins.append(PinRef(inst=inst, pin=pin_name))

    return nets


def classify_net_pins(
    net_name: str,
    pins: tuple[PinRef, ...],
    inst_die_map: dict[str, str],
    pin_die_map: dict[str, str] | None = None,
) -> str:
    """Classify net as 2d_bottom | 2d_upper | 3d | unknown."""
    if net_name.endswith("_BOT"):
        return "2d_bottom"
    if net_name.endswith("_TOP"):
        return "2d_upper"

    dies: set[str] = set()
    for pin_ref in pins:
        die = pin_ref_die(pin_ref, inst_die_map, pin_die_map)
        if die:
            dies.add(die)
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
    pin_die_map: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return mapping net_name -> classification label."""
    return {
        net.name: classify_net_pins(net.name, net.pins, inst_die_map, pin_die_map)
        for net in nets
    }


def pin_ref_die(
    pin_ref: PinRef,
    inst_die_map: dict[str, str],
    pin_die_map: dict[str, str] | None = None,
) -> str | None:
    """Return the die touched by one instance pin or top-level DEF pin."""
    if pin_ref.inst == "PIN":
        return (pin_die_map or {}).get(pin_ref.pin)
    if pin_ref.inst.startswith("HBT_"):
        if pin_ref.pin == "BOT":
            return "bottom"
        if pin_ref.pin == "TOP":
            return "upper"
    return inst_die_map.get(pin_ref.inst)
