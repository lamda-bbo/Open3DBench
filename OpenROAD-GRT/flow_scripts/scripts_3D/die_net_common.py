#!/usr/bin/env python3
"""DEF parsing and die-aware net classification for global routing."""

from __future__ import annotations

import re
import hashlib
import json
import os
import tempfile
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from itertools import islice

BOTTOM_MAX_LAYER = 10
UPPER_MIN_LAYER = 11

NET_HEADER_RE = re.compile(r"^\s*-\s+(\S+)")
PIN_CONN_RE = re.compile(r"\(\s*(\S+)\s+(\S+)\s*\)")
DEF_LAYER_RE = re.compile(r"\+\s+LAYER\s+(\S+)", re.IGNORECASE)
METAL_LAYER_RE = re.compile(r"^metal(\d+)$", re.IGNORECASE)
CLASSIFICATION_CACHE_VERSION = 1
CLASSIFICATION_LABELS = frozenset(("2d_bottom", "2d_upper", "3d", "unknown"))


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


def def_sha256(def_path: Path) -> str:
    """Hash the complete DEF bytes without retaining the file in memory."""
    digest = hashlib.sha256()
    with def_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def classification_payload_sha256(classification: dict[str, str]) -> str:
    """Hash every classification in its original DEF insertion order."""
    digest = hashlib.sha256()
    for chunk in iter_classification_json(classification):
        digest.update(chunk.encode("utf-8"))
    return digest.hexdigest()


def iter_classification_json(classification: dict[str, str]) -> Iterator[str]:
    """Encode the complete ordered map in bounded C-encoder batches.

    JSONEncoder.iterencode emits several Python fragments per net. Batching
    small ordered dictionaries produces identical compact JSON bytes while
    avoiding millions of Python hash/write calls and a whole-design buffer.
    """
    yield "{"
    entries = iter(classification.items())
    separator = ""
    while batch := dict(islice(entries, 4096)):
        encoded = json.dumps(batch, ensure_ascii=True, separators=(",", ":"))
        yield separator + encoded[1:-1]
        separator = ","
    yield "}"


def write_classification_cache(
    path: Path,
    def_path: Path,
    classification: dict[str, str],
    *,
    expected_def_sha256: str | None = None,
) -> None:
    """Atomically publish a complete classification tied to exact DEF bytes."""
    input_digest = def_sha256(def_path)
    if expected_def_sha256 is not None and input_digest != expected_def_sha256:
        raise ValueError("DEF changed while producing its classification cache")
    record = {
        "schema_version": CLASSIFICATION_CACHE_VERSION,
        "def_sha256": input_digest,
        "payload_sha256": classification_payload_sha256(classification),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=path.name + ".",
            suffix=".tmp", delete=False,
        ) as stream:
            temporary = stream.name
            stream.write(json.dumps(record, ensure_ascii=True, separators=(",", ":"))[:-1])
            stream.write(',"classification":')
            for chunk in iter_classification_json(classification):
                stream.write(chunk)
            stream.write("}\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def read_classification_cache(path: Path, def_path: Path) -> dict[str, str] | None:
    """Return a verified complete cache, or None to request fresh parsing."""
    try:
        with path.open(encoding="utf-8") as stream:
            record = json.load(stream)
        if not isinstance(record, dict):
            return None
        version = record.get("schema_version")
        if type(version) is not int or version != CLASSIFICATION_CACHE_VERSION:
            return None
        input_digest = record.get("def_sha256")
        payload_digest = record.get("payload_sha256")
        if not isinstance(input_digest, str) or not isinstance(payload_digest, str):
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", input_digest):
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", payload_digest):
            return None
        classification = record.get("classification")
        if not isinstance(classification, dict):
            return None
        if any(not isinstance(name, str) or not isinstance(label, str)
               or label not in CLASSIFICATION_LABELS
               for name, label in classification.items()):
            return None
        if classification_payload_sha256(classification) != payload_digest:
            return None
        if def_sha256(def_path) != input_digest:
            return None
        return classification
    except (OSError, ValueError, TypeError):
        return None


def name_die(name: str) -> str | None:
    """Return die id from instance or cell naming convention."""
    if name.endswith("_bottom") or name.startswith("HBT_BOTIN_"):
        return "bottom"
    if name.endswith("_upper") or name.startswith("HBT_TOPIN_"):
        return "upper"
    return None


def is_hbt_instance_name(name: str) -> bool:
    """Return whether an instance follows either supported HBT naming path."""
    return name.startswith(("HBT_", "LS_HBT_"))


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


def iter_net_connections(
    def_path: Path,
    *,
    net_name_filter: Callable[[str], bool] | None = None,
) -> Iterator[tuple[str, tuple[tuple[str, str], ...]]]:
    """Yield raw DEF connections without allocating a dataclass per pin.

    Filtering selects entire nets: every connection of a selected net is kept
    in DEF order, including ordinary instance and package pins.
    """
    in_nets = False
    current_name: str | None = None
    current_pins: list[tuple[str, str]] = []
    selected = False

    with def_path.open(encoding="utf-8") as def_file:
        for line in def_file:
            stripped = line.strip()
            if stripped.startswith("NETS"):
                in_nets = True
                continue
            if in_nets and stripped.startswith("END NETS"):
                if current_name is not None and selected:
                    yield current_name, tuple(current_pins)
                break
            if not in_nets:
                continue

            if stripped.startswith("- "):
                if current_name is not None and selected:
                    yield current_name, tuple(current_pins)
                current_name = None
                current_pins = []
                selected = False
                header_match = NET_HEADER_RE.match(stripped)
                if not header_match:
                    continue
                current_name = header_match.group(1)
                selected = net_name_filter is None or net_name_filter(current_name)
                if not selected:
                    continue
                rest = stripped[len("- " + current_name) :].strip()
                current_pins.extend(PIN_CONN_RE.findall(rest))
                continue

            if current_name is None or not selected:
                continue

            current_pins.extend(PIN_CONN_RE.findall(stripped))


def iter_nets(
    def_path: Path,
    *,
    net_name_filter: Callable[[str], bool] | None = None,
) -> Iterator[NetRecord]:
    """Yield the public net/pin records, preserving DEF connection order."""
    for name, pins in iter_net_connections(def_path, net_name_filter=net_name_filter):
        yield NetRecord(name=name, pins=tuple(PinRef(inst=inst, pin=pin) for inst, pin in pins))


def classify_net_connections(
    net_name: str,
    pins: tuple[tuple[str, str], ...],
    inst_die_map: dict[str, str],
    pin_die_map: dict[str, str],
) -> str:
    """Classify raw connections with the same rules as classify_net_pins."""
    if net_name.endswith("_BOT"):
        return "2d_bottom"
    if net_name.endswith("_TOP"):
        return "2d_upper"
    bottom = False
    upper = False
    other = False
    for inst, pin in pins:
        if inst == "PIN":
            die = pin_die_map.get(pin)
        elif is_hbt_instance_name(inst) and pin == "BOT":
            die = "bottom"
        elif is_hbt_instance_name(inst) and pin == "TOP":
            die = "upper"
        else:
            die = inst_die_map.get(inst)
        bottom = bottom or die == "bottom"
        upper = upper or die == "upper"
        other = other or bool(die and die not in ("bottom", "upper"))
        if bottom and upper:
            return "3d"
    if bottom and not other:
        return "2d_bottom"
    if upper and not other:
        return "2d_upper"
    return "unknown"


def parse_nets(def_path: Path) -> list[NetRecord]:
    """Parse all DEF nets into NetRecord objects."""
    return list(iter_nets(def_path))


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
    nets: Iterable[NetRecord],
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
    if is_hbt_instance_name(pin_ref.inst):
        if pin_ref.pin == "BOT":
            return "bottom"
        if pin_ref.pin == "TOP":
            return "upper"
    return inst_die_map.get(pin_ref.inst)
