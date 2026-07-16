#!/usr/bin/env python3
"""Algorithms and helpers for MoL 2D metal-layer sharing net split.

Each shared 2D net is split into exactly three subnets with at most two HBTs:

  {net}_SN0  native segment + HBT0 (home-die metal pool)
  {net}_SN1  borrow segment: HBT0 + HBT1 (other-die metal pool)
  {net}_SN2  native segment + HBT1 (home-die metal pool)

Upper-home example (borrows bottom m2-m10 for SN1):

  pins -- SN0 -- HBT0.TOP | HBT0.BOT -- SN1 -- HBT1.BOT | HBT1.TOP -- SN2 -- pins
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from mol_hbt_common import (
    ComponentInfo,
    NetRecord,
    PinRef,
    choose_hbt_type,
    classify_net_pins,
    centroid_for_pins,
)

SUBNET_SN0_SUFFIX = "_SN0"
SUBNET_SN1_SUFFIX = "_SN1"
SUBNET_SN2_SUFFIX = "_SN2"
SHARE_SUBNET_SUFFIXES = (SUBNET_SN0_SUFFIX, SUBNET_SN1_SUFFIX, SUBNET_SN2_SUFFIX)

LS_HBT_INST_PREFIX = "LS_HBT_"
MANIFEST_DEFAULT_NAME = "mol_layer_share_manifest.json"

# Default HBT separation in DEF DBU prevents colocated terminals.
DEFAULT_HBT_MIN_SEPARATION_DBU = 1600


@dataclass(frozen=True)
class SharePolicy:
    """Which nets may borrow another die's routing layers."""

    share_nets: frozenset[str]
    hbt_min_separation_dbu: int = DEFAULT_HBT_MIN_SEPARATION_DBU
    use_fixed_placement: bool = True


@dataclass(frozen=True)
class HbtPinRoles:
    """HBT pin names on native vs borrowed metal pools."""

    native_pin: str
    borrow_pin: str


@dataclass(frozen=True)
class LayerShareSplitPlan:
    """Split plan for one shared 2D net (3 subnets, 2 HBTs)."""

    original_net: str
    home_die: str
    borrow_die: str
    hbt_cell: str
    hbt0_inst: str
    hbt1_inst: str
    hbt0_x: int
    hbt0_y: int
    hbt1_x: int
    hbt1_y: int
    sn0_pins: tuple[PinRef, ...]
    sn2_pins: tuple[PinRef, ...]
    sn0_net: str
    sn1_net: str
    sn2_net: str


def load_share_net_list(path: Path) -> frozenset[str]:
    """Load net names from a share allowlist file (one name per line, # comments)."""
    names: set[str] = set()
    with path.open(encoding="utf-8") as share_file:
        for line in share_file:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            names.add(stripped.split()[0])
    return frozenset(names)


def resolve_share_policy(
    *,
    share_list_path: Path | None = None,
    share_nets_env: str | None = None,
) -> SharePolicy:
    """Build SharePolicy from CLI path and/or MOL_SHARE_NET_LIST / env override."""
    names: set[str] = set()

    list_path = share_list_path
    if list_path is None:
        env_path = os.environ.get("MOL_SHARE_NET_LIST")
        if env_path:
            list_path = Path(env_path)

    if list_path is not None and list_path.exists():
        names.update(load_share_net_list(list_path))

    env_nets = share_nets_env if share_nets_env is not None else os.environ.get(
        "MOL_LAYER_SHARE_NETS",
        "",
    )
    for part in env_nets.split(","):
        net_name = part.strip()
        if net_name:
            names.add(net_name)

    sep = int(os.environ.get("MOL_HBT_MIN_SEPARATION_DBU", DEFAULT_HBT_MIN_SEPARATION_DBU))
    fixed = os.environ.get("MOL_LAYER_SHARE_FIXED", "1") != "0"
    return SharePolicy(share_nets=frozenset(names), hbt_min_separation_dbu=sep, use_fixed_placement=fixed)


def is_share_subnet_name(net_name: str) -> bool:
    """Return True if net_name is a layer-share subnet."""
    return any(net_name.endswith(suffix) for suffix in SHARE_SUBNET_SUFFIXES)


def subnet_suffix(net_name: str) -> str | None:
    """Return _SN0/_SN1/_SN2 suffix if present."""
    for suffix in SHARE_SUBNET_SUFFIXES:
        if net_name.endswith(suffix):
            return suffix
    return None


def hbt_pin_roles(hbt_cell: str) -> HbtPinRoles:
    """Map HBT cell type to native/borrow pin names."""
    if hbt_cell == "HBT_TOPIN":
        return HbtPinRoles(native_pin="TOP", borrow_pin="BOT")
    if hbt_cell == "HBT_BOTIN":
        return HbtPinRoles(native_pin="BOT", borrow_pin="TOP")
    msg = f"unsupported HBT cell for layer share: {hbt_cell}"
    raise ValueError(msg)


def borrow_die_for(home_die: str) -> str:
    """Return the die whose metal pool is borrowed."""
    if home_die == "upper":
        return "bottom"
    if home_die == "bottom":
        return "upper"
    msg = f"invalid home_die: {home_die}"
    raise ValueError(msg)


def partition_pins_by_centroid_bisect(
    pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
) -> tuple[tuple[PinRef, ...], tuple[PinRef, ...]]:
    """Split pins into two groups by bisecting through the net geometric center."""
    if len(pins) <= 1:
        return pins, ()

    cx, cy = centroid_for_pins(pins, components)
    group_a: list[PinRef] = []
    group_b: list[PinRef] = []

    for pin_ref in pins:
        comp = components.get(pin_ref.inst)
        if comp is None:
            group_a.append(pin_ref)
            continue
        dx = comp.x - cx
        dy = comp.y - cy
        if dx < 0 or (dx == 0 and dy < 0):
            group_a.append(pin_ref)
        else:
            group_b.append(pin_ref)

    if not group_a or not group_b:
        mid = max(1, len(pins) // 2)
        return tuple(pins[:mid]), tuple(pins[mid:])

    return tuple(group_a), tuple(group_b)


def hbt_location_for_pin_group(
    pins: tuple[PinRef, ...],
    fallback_pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
) -> tuple[int, int]:
    """Place HBT at pin-group centroid; fall back to full-net centroid."""
    if pins:
        return centroid_for_pins(pins, components)
    if fallback_pins:
        return centroid_for_pins(fallback_pins, components)
    return 0, 0


def separate_colocated_hbt(
    x0: int,
    y0: int,
    x1: int,
    y1: int,
    min_separation_dbu: int,
) -> tuple[int, int]:
    """Offset second HBT if both centroids coincide."""
    if x0 != x1 or y0 != y1:
        return x1, y1
    return x1 + min_separation_dbu, y1


def choose_hbt_cell_for_home_die(
    home_die: str,
    pins: tuple[PinRef, ...],
    components: dict[str, ComponentInfo],
    lef_dirs: dict[str, dict[str, str]],
) -> str:
    """Pick HBT_BOTIN/HBT_TOPIN from home die and driver direction."""
    if home_die == "upper":
        return choose_hbt_type((), pins, components, lef_dirs)
    if home_die == "bottom":
        return choose_hbt_type(pins, (), components, lef_dirs)
    msg = f"invalid home_die: {home_die}"
    raise ValueError(msg)


def build_layer_share_plan(
    net: NetRecord,
    home_die: str,
    hbt_cell: str,
    hbt0_inst: str,
    hbt1_inst: str,
    components: dict[str, ComponentInfo],
    policy: SharePolicy,
) -> LayerShareSplitPlan:
    """Build one 3-subnet / 2-HBT split plan for a shared 2D net."""
    sn0_pins, sn2_pins = partition_pins_by_centroid_bisect(net.pins, components)
    all_pins = net.pins

    hbt0_x, hbt0_y = hbt_location_for_pin_group(sn0_pins, all_pins, components)
    hbt1_x, hbt1_y = hbt_location_for_pin_group(sn2_pins, all_pins, components)
    hbt1_x, hbt1_y = separate_colocated_hbt(
        hbt0_x,
        hbt0_y,
        hbt1_x,
        hbt1_y,
        policy.hbt_min_separation_dbu,
    )

    borrow = borrow_die_for(home_die)
    return LayerShareSplitPlan(
        original_net=net.name,
        home_die=home_die,
        borrow_die=borrow,
        hbt_cell=hbt_cell,
        hbt0_inst=hbt0_inst,
        hbt1_inst=hbt1_inst,
        hbt0_x=hbt0_x,
        hbt0_y=hbt0_y,
        hbt1_x=hbt1_x,
        hbt1_y=hbt1_y,
        sn0_pins=sn0_pins,
        sn2_pins=sn2_pins,
        sn0_net=f"{net.name}{SUBNET_SN0_SUFFIX}",
        sn1_net=f"{net.name}{SUBNET_SN1_SUFFIX}",
        sn2_net=f"{net.name}{SUBNET_SN2_SUFFIX}",
    )


def build_layer_share_plans(
    nets: list[NetRecord],
    inst_die_map: dict[str, str],
    components: dict[str, ComponentInfo],
    lef_dirs: dict[str, dict[str, str]],
    policy: SharePolicy,
    *,
    start_hbt_idx: int = 0,
) -> tuple[list[LayerShareSplitPlan], list[str]]:
    """Build split plans for allowlisted 2D nets only."""
    plans: list[LayerShareSplitPlan] = []
    warnings: list[str] = []
    net_by_name = {net.name: net for net in nets}
    hbt_idx = start_hbt_idx

    for net_name in sorted(policy.share_nets):
        net = net_by_name.get(net_name)
        if net is None:
            warnings.append(f"skip missing net: {net_name}")
            continue
        if is_share_subnet_name(net_name):
            warnings.append(f"skip already-split net: {net_name}")
            continue
        if len(net.pins) < 1:
            warnings.append(f"skip empty net: {net_name}")
            continue

        label = classify_net_pins(net.name, net.pins, inst_die_map)
        if label not in ("2d_bottom", "2d_upper"):
            warnings.append(f"skip non-2D net {net_name} (class={label})")
            continue

        home_die = label.replace("2d_", "")
        hbt_cell = choose_hbt_cell_for_home_die(home_die, net.pins, components, lef_dirs)
        hbt0_inst = f"{LS_HBT_INST_PREFIX}{hbt_cell}_{hbt_idx}"
        hbt1_inst = f"{LS_HBT_INST_PREFIX}{hbt_cell}_{hbt_idx + 1}"

        plans.append(
            build_layer_share_plan(
                net,
                home_die,
                hbt_cell,
                hbt0_inst,
                hbt1_inst,
                components,
                policy,
            )
        )
        hbt_idx += 2

    return plans, warnings


def next_ls_hbt_index(components: dict[str, ComponentInfo]) -> int:
    """Return next free index for LS_HBT_* instances in DEF."""
    max_idx = -1
    pattern = re.compile(rf"^{re.escape(LS_HBT_INST_PREFIX)}(?:BOTIN|TOPIN)_(\d+)$")
    for inst_name in components:
        match = pattern.match(inst_name)
        if match:
            max_idx = max(max_idx, int(match.group(1)))
    return max_idx + 1


def format_subnet_lines(
    net_name: str,
    pin_refs: tuple[PinRef, ...],
    hbt_connections: tuple[tuple[str, str], ...],
) -> list[str]:
    """Format one DEF subnet with zero or more HBT pin connections."""
    lines = [f"- {net_name}"]
    for pin_ref in pin_refs:
        lines.append(f" ( {pin_ref.inst} {pin_ref.pin} )")
    for hbt_inst, hbt_pin in hbt_connections:
        lines.append(f" ( {hbt_inst} {hbt_pin} )")
    lines.append(" + USE SIGNAL ;")
    return lines


def format_split_subnet_lines(plan: LayerShareSplitPlan) -> list[str]:
    """Emit three DEF subnets for one layer-share plan."""
    roles = hbt_pin_roles(plan.hbt_cell)
    sn0 = format_subnet_lines(
        plan.sn0_net,
        plan.sn0_pins,
        ((plan.hbt0_inst, roles.native_pin),),
    )
    sn1 = format_subnet_lines(
        plan.sn1_net,
        (),
        (
            (plan.hbt0_inst, roles.borrow_pin),
            (plan.hbt1_inst, roles.borrow_pin),
        ),
    )
    sn2 = format_subnet_lines(
        plan.sn2_net,
        plan.sn2_pins,
        ((plan.hbt1_inst, roles.native_pin),),
    )
    return sn0 + sn1 + sn2


def plan_to_manifest_entry(plan: LayerShareSplitPlan) -> dict[str, object]:
    """Serialize one plan for mol_layer_share_manifest.json."""
    roles = hbt_pin_roles(plan.hbt_cell)
    return {
        "home_die": plan.home_die,
        "borrow_die": plan.borrow_die,
        "hbt_cell": plan.hbt_cell,
        "hbt_instances": [plan.hbt0_inst, plan.hbt1_inst],
        "hbt_locations": {
            plan.hbt0_inst: [plan.hbt0_x, plan.hbt0_y],
            plan.hbt1_inst: [plan.hbt1_x, plan.hbt1_y],
        },
        "subnets": {
            "SN0": {
                "name": plan.sn0_net,
                "routing_pool": "native",
                "pins": [f"{p.inst}/{p.pin}" for p in plan.sn0_pins],
                "hbt": {plan.hbt0_inst: roles.native_pin},
            },
            "SN1": {
                "name": plan.sn1_net,
                "routing_pool": "borrow",
                "pins": [],
                "hbt": {
                    plan.hbt0_inst: roles.borrow_pin,
                    plan.hbt1_inst: roles.borrow_pin,
                },
            },
            "SN2": {
                "name": plan.sn2_net,
                "routing_pool": "native",
                "pins": [f"{p.inst}/{p.pin}" for p in plan.sn2_pins],
                "hbt": {plan.hbt1_inst: roles.native_pin},
            },
        },
    }


def write_manifest(path: Path, plans: Iterable[LayerShareSplitPlan]) -> None:
    """Write layer-share manifest JSON for GRT export and checking."""
    payload = {
        "version": 1,
        "subnet_suffixes": list(SHARE_SUBNET_SUFFIXES),
        "nets": {plan.original_net: plan_to_manifest_entry(plan) for plan in plans},
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def build_subnet_manifest_index(
    manifest: dict[str, dict[str, object]],
) -> dict[str, dict[str, object]]:
    """Map subnet name -> manifest entry for the parent shared net."""
    index: dict[str, dict[str, object]] = {}
    for _orig, entry in manifest.items():
        subnets = entry.get("subnets", {})
        if not isinstance(subnets, dict):
            continue
        for spec in subnets.values():
            if isinstance(spec, dict) and "name" in spec:
                index[str(spec["name"])] = entry
    return index


def load_share_manifest(path: Path) -> dict[str, dict[str, object]]:
    """Load manifest; return original_net -> entry."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    nets = data.get("nets", {})
    if not isinstance(nets, dict):
        return {}
    return nets


def routing_pass_for_share_subnet(
    subnet_name: str,
    manifest_entry: dict[str, object],
) -> str | None:
    """Return 'bottom' or 'upper' GRT pass for a share subnet name."""
    pool = share_subnet_routing_pool(subnet_name, manifest_entry)
    home_die = manifest_entry.get("home_die")
    if pool is None or home_die not in ("upper", "bottom"):
        return None
    if pool == "native":
        return str(home_die)
    return "bottom" if home_die == "upper" else "upper"


def share_subnet_routing_pool(
    subnet_name: str,
    manifest_entry: dict[str, object],
) -> str | None:
    """Return 'native' or 'borrow' for a layer-share subnet."""
    subnets = manifest_entry.get("subnets", {})
    if not isinstance(subnets, dict):
        return None
    for spec in subnets.values():
        if isinstance(spec, dict) and spec.get("name") == subnet_name:
            pool = spec.get("routing_pool")
            return str(pool) if pool in ("native", "borrow") else None
    return None


def layer_allowed_for_share_subnet(
    subnet_name: str,
    layer: int,
    manifest_entry: dict[str, object],
    *,
    bottom_max: int = 10,
    upper_min: int = 11,
) -> bool:
    """Return True if layer is legal for a layer-share subnet."""
    pool = share_subnet_routing_pool(subnet_name, manifest_entry)
    home_die = manifest_entry.get("home_die")
    if pool is None or home_die not in ("upper", "bottom"):
        return True
    if pool == "native":
        if home_die == "upper":
            return layer >= upper_min
        return layer <= bottom_max
    if home_die == "upper":
        return layer <= bottom_max
    return layer >= upper_min


def manifest_path_from_env(results_dir: Path) -> Path:
    """Resolve manifest path from env or default under results."""
    env_path = os.environ.get("MOL_LAYER_SHARE_MANIFEST")
    if env_path:
        return Path(env_path)
    return results_dir / MANIFEST_DEFAULT_NAME
