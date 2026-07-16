#!/usr/bin/env python3
"""Diagnose GRT guide connectivity issues that trigger DRT-0218."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from mol_hbt_common import parse_nets
from mol_layer_share_common import SHARE_SUBNET_SUFFIXES

GCELL_STEP = 4200
BOTTOM_DIE_MAX_LAYER = 10
UPPER_DIE_MIN_LAYER = 11
METAL_RE = re.compile(r"^metal(\d+)$", re.I)
GRT_MISSING_RE = re.compile(
    r"Missing route to pin (\S+) in net (\S+)\.",
)


@dataclass(frozen=True)
class GuideRect:
    """One global-route guide rectangle."""

    layer: str
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class NetDiag:
    """Connectivity diagnosis for one net."""

    net: str
    pin_count: int
    guide_rects: int
    uncovered_pins: int
    hbt_uncovered: int
    same_layer_components: int
    pin_components: int
    illegal_layers: int
    grt_missing_pins: int
    has_m10_pre_scrub: bool
    m10_removed_by_scrub: bool


def parse_grt_missing(log_path: Path) -> dict[str, set[str]]:
    """Return net -> missing pin names from GRT-0026 warnings."""
    missing: dict[str, set[str]] = defaultdict(set)
    if not log_path.exists():
        return missing
    for line in log_path.open(encoding="utf-8"):
        match = GRT_MISSING_RE.search(line)
        if match:
            pin, net = match.group(1), match.group(2)
            missing[net].add(pin)
    return missing


def parse_guides(guide_path: Path) -> dict[str, list[GuideRect]]:
    """Parse route.guide into net -> guide rectangles."""
    nets: dict[str, list[GuideRect]] = defaultdict(list)
    cur_net: str | None = None
    with guide_path.open(encoding="utf-8") as guide_file:
        for line in guide_file:
            stripped = line.strip()
            if stripped in ("(", ")"):
                if stripped == ")":
                    cur_net = None
                continue
            parts = stripped.split()
            if len(parts) >= 5:
                layer = parts[-1]
                if METAL_RE.match(layer) and cur_net:
                    nets[cur_net].append(
                        GuideRect(
                            layer=layer,
                            x1=int(parts[0]),
                            y1=int(parts[1]),
                            x2=int(parts[2]),
                            y2=int(parts[3]),
                        )
                    )
                continue
            if len(parts) == 1:
                cur_net = parts[0]
            elif stripped.endswith("("):
                cur_net = stripped[:-1].strip()
    return nets


def pin_covered(x: int, y: int, rects: list[GuideRect], margin: int) -> bool:
    """Check whether a pin coordinate overlaps any guide bbox (expanded)."""
    for rect in rects:
        if (
            rect.x1 - margin <= x <= rect.x2 + margin
            and rect.y1 - margin <= y <= rect.y2 + margin
        ):
            return True
    return False


def is_hbt_split_net(net: str) -> bool:
    """Return true for MoL HBT-mediated split nets."""
    return (
        net.endswith("_BOT")
        or net.endswith("_TOP")
        or net.endswith(SHARE_SUBNET_SUFFIXES)
    )


def metal_index(layer: str) -> int | None:
    """Return metalN index, or None for non-metal guide layers."""
    match = METAL_RE.match(layer)
    return int(match.group(1)) if match else None


def xy_touches(a: GuideRect, b: GuideRect, margin: int = 1) -> bool:
    """Check whether two guide boxes touch/overlap in XY."""
    return not (
        a.x2 < b.x1 - margin
        or b.x2 < a.x1 - margin
        or a.y2 < b.y1 - margin
        or b.y2 < a.y1 - margin
    )


def guide_components_3d(rects: list[GuideRect]) -> list[int]:
    """Return 3D connected-component ids for guide rectangles."""
    if not rects:
        return []
    parent = list(range(len(rects)))
    layer_ids = [metal_index(rect.layer) for rect in rects]

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for i in range(len(rects)):
        li = layer_ids[i]
        if li is None:
            continue
        for j in range(i + 1, len(rects)):
            lj = layer_ids[j]
            if lj is None:
                continue
            if li == lj and xy_touches(rects[i], rects[j]):
                union(i, j)
            elif abs(li - lj) == 1 and xy_touches(rects[i], rects[j], margin=0):
                union(i, j)

    return [find(i) for i in range(len(rects))]


def pin_component_count(
    rects: list[GuideRect],
    pins: list[tuple[str, int, int]],
    margin: int,
) -> int:
    """Count distinct 3D guide components touched by covered pins."""
    if not rects or not pins:
        return 0
    components = guide_components_3d(rects)
    pin_components: set[int] = set()
    for _inst, x, y in pins:
        for idx, rect in enumerate(rects):
            if pin_covered(x, y, [rect], margin):
                pin_components.add(components[idx])
                break
    return len(pin_components)


def illegal_layer_count(net: str, rects: list[GuideRect]) -> int:
    """Count guide rects that violate the die-local layer window."""
    illegal = 0
    for rect in rects:
        layer_idx = metal_index(rect.layer)
        if layer_idx is None:
            continue
        if net.endswith("_BOT") and layer_idx > BOTTOM_DIE_MAX_LAYER:
            illegal += 1
        elif net.endswith("_TOP") and layer_idx < UPPER_DIE_MIN_LAYER:
            illegal += 1
    return illegal


def same_layer_components(rects: list[GuideRect]) -> int:
    """Count connected components among same-layer touching rectangles."""
    if not rects:
        return 0
    parent = list(range(len(rects)))

    def find(idx: int) -> int:
        while parent[idx] != idx:
            parent[idx] = parent[parent[idx]]
            idx = parent[idx]
        return idx

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def touches(a: GuideRect, b: GuideRect) -> bool:
        if a.layer != b.layer:
            return False
        return not (
            a.x2 < b.x1 - 1
            or b.x2 < a.x1 - 1
            or a.y2 < b.y1 - 1
            or b.y2 < a.y1 - 1
        )

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            if touches(rects[i], rects[j]):
                union(i, j)
    return len({find(i) for i in range(len(rects))})


def parse_components_multiline(def_path: Path) -> dict[str, tuple[int, int]]:
    """Parse DEF components; PLACED may appear on the following line."""
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
                if pending_inst and ("PLACED" in stripped or "FIXED" in stripped):
                    match = re.search(r"\(\s*(\d+)\s+(\d+)\s*\)", stripped)
                    if match:
                        components[pending_inst] = (
                            int(match.group(1)),
                            int(match.group(2)),
                        )
                    pending_inst = None
                continue
            if pending_inst and ("PLACED" in stripped or "FIXED" in stripped):
                match = re.search(r"\(\s*(\d+)\s+(\d+)\s*\)", stripped)
                if match:
                    components[pending_inst] = (
                        int(match.group(1)),
                        int(match.group(2)),
                    )
                pending_inst = None

    return components


def build_net_pins(
    def_path: Path,
) -> dict[str, list[tuple[str, int, int]]]:
    """Return net -> [(inst, x, y), ...] using component origins."""
    components = parse_components_multiline(def_path)
    net_pins: dict[str, list[tuple[str, int, int]]] = defaultdict(list)
    for net in parse_nets(def_path):
        for pin_ref in net.pins:
            loc = components.get(pin_ref.inst)
            if loc is None:
                continue
            net_pins[net.name].append((pin_ref.inst, loc[0], loc[1]))
    return net_pins


def diagnose_net(
    net: str,
    rects: list[GuideRect],
    pins: list[tuple[str, int, int]],
    grt_missing: set[str],
    upper_rects: list[GuideRect] | None,
    margin: int,
    max_cc_rects: int,
) -> NetDiag:
    """Build one net-level connectivity report."""
    uncovered = 0
    hbt_uncovered = 0
    for inst, x, y in pins:
        if not pin_covered(x, y, rects, margin):
            uncovered += 1
            if inst.startswith("HBT_") or inst.startswith("LS_HBT_"):
                hbt_uncovered += 1

    cc = 0
    pin_cc = -1
    if len(rects) <= max_cc_rects:
        cc = same_layer_components(rects)
        pin_cc = pin_component_count(rects, pins, margin)
    illegal_layers = illegal_layer_count(net, rects)

    has_m10 = any(r.layer.lower() == "metal10" for r in (upper_rects or []))
    has_m10_post = any(r.layer.lower() == "metal10" for r in rects)
    return NetDiag(
        net=net,
        pin_count=len(pins),
        guide_rects=len(rects),
        uncovered_pins=uncovered,
        hbt_uncovered=hbt_uncovered,
        same_layer_components=cc,
        pin_components=pin_cc,
        illegal_layers=illegal_layers,
        grt_missing_pins=len(grt_missing),
        has_m10_pre_scrub=has_m10,
        m10_removed_by_scrub=has_m10 and not has_m10_post,
    )


def score_candidate(diag: NetDiag) -> float:
    """Rank likelihood of DRT-0218 (higher = more likely fatal)."""
    if diag.pin_count == 0:
        return -1.0
    if diag.guide_rects == 0:
        return 100.0 if is_hbt_split_net(diag.net) else -1.0
    score = 0.0
    if diag.illegal_layers:
        score += 100 + min(diag.illegal_layers, 100)
    if diag.grt_missing_pins:
        score += 50 + diag.grt_missing_pins * 10
    if diag.hbt_uncovered:
        score += 30 + diag.hbt_uncovered * 5
    if diag.uncovered_pins:
        score += 20 + min(diag.uncovered_pins, 20) * 3
    if diag.same_layer_components > 1:
        ratio = diag.same_layer_components / max(diag.guide_rects, 1)
        score += 15 + ratio * 40
    if diag.pin_components > 1:
        score += 40 + diag.pin_components * 5
    if diag.m10_removed_by_scrub:
        score += 25
    if diag.pin_count > 1000:
        score *= 0.3
    return score


def resolve_grt_log_path(results_dir: Path) -> Path:
    """Map a results directory to its GRT finalize log under WORK_HOME or flow/logs."""
    work_home = os.environ.get("WORK_HOME", "").strip()
    if work_home:
        work_root = Path(work_home)
        try:
            rel = results_dir.relative_to(work_root / "results")
            return work_root / "logs" / rel / "grt_finalize.log"
        except ValueError:
            pass

    flow_dir = results_dir
    while flow_dir.name != "flow" and flow_dir.parent != flow_dir:
        flow_dir = flow_dir.parent
    try:
        rel = results_dir.relative_to(flow_dir / "results")
    except ValueError:
        parts = list(results_dir.parts)
        if "results" in parts:
            idx = parts.index("results")
            log_parts = parts[:idx] + ["logs"] + parts[idx + 1 :]
            return Path(*log_parts) / "grt_finalize.log"
        msg = f"Cannot map results dir to logs: {results_dir}"
        raise ValueError(msg) from None
    return flow_dir / "logs" / rel / "grt_finalize.log"


def run_diagnosis(
    results_dir: Path,
    max_cc_rects: int,
    top_k: int,
    split_only: bool = False,
) -> list[NetDiag]:
    """Run full diagnosis for one MoL results directory."""
    def_path = results_dir / "4_1_cts.def"
    guide_path = results_dir / "route.guide"
    upper_path = results_dir / "route_upper.guide"
    log_path = resolve_grt_log_path(results_dir)

    guides = parse_guides(guide_path)
    upper_guides = parse_guides(upper_path) if upper_path.exists() else {}
    net_pins = build_net_pins(def_path)
    grt_missing = parse_grt_missing(log_path)
    margin = GCELL_STEP // 2

    diags: list[NetDiag] = []
    if split_only:
        candidate_nets = {
            net
            for net in set(guides) | set(net_pins)
            if is_hbt_split_net(net)
        }
    else:
        candidate_nets = set(guides)
        candidate_nets.update(net for net in net_pins if is_hbt_split_net(net))
    for net in sorted(candidate_nets):
        rects = guides.get(net, [])
        pins = net_pins.get(net, [])
        if not pins:
            continue
        diags.append(
            diagnose_net(
                net=net,
                rects=rects,
                pins=pins,
                grt_missing=grt_missing.get(net, set()),
                upper_rects=upper_guides.get(net),
                margin=margin,
                max_cc_rects=max_cc_rects,
            )
        )
    diags.sort(key=score_candidate, reverse=True)
    ranked = [d for d in diags if score_candidate(d) > 0]
    return ranked[:top_k]


def print_report(label: str, diags: list[NetDiag]) -> None:
    """Print ranked diagnosis table."""
    print(f"\n{'=' * 72}")
    print(f"{label}")
    print(f"{'=' * 72}")
    print(
        f"{'net':<55} {'pins':>5} {'rects':>6} {'uncov':>5} "
        f"{'hbtU':>4} {'CC':>5} {'pinC':>5} {'badL':>5} "
        f"{'GRT':>4} {'scrub':>5}"
    )
    for diag in diags:
        scrub = "m10-" if diag.m10_removed_by_scrub else ""
        cc = str(diag.same_layer_components) if diag.same_layer_components else "?"
        pin_cc = str(diag.pin_components) if diag.pin_components > 0 else "?"
        print(
            f"{diag.net:<55} {diag.pin_count:>5} {diag.guide_rects:>6} "
            f"{diag.uncovered_pins:>5} {diag.hbt_uncovered:>4} {cc:>5} "
            f"{pin_cc:>5} {diag.illegal_layers:>5} {diag.grt_missing_pins:>4} "
            f"{scrub:>5}"
        )


def strict_failure(diag: NetDiag) -> bool:
    """Return true for invariants reliable from DEF-level guide geometry.

    Complete pin coverage is enforced in GlobalRouter with ODB pin geometry.
    DEF instance origins are only an approximate diagnostic for ordinary pins.
    """
    return is_hbt_split_net(diag.net) and (
        diag.guide_rects == 0
        or diag.illegal_layers > 0
        or diag.hbt_uncovered > 0
        or diag.pin_components > 1
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_dir",
        type=Path,
        help="e.g. results/nangate45_3D/ariane133/mol_die",
    )
    parser.add_argument("--top", type=int, default=25, help="Top candidates to show")
    parser.add_argument(
        "--max-cc-rects",
        type=int,
        default=2000,
        help="Skip CC analysis above this guide-rect count",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any HBT split net has illegal layers or disconnected pin guides",
    )
    args = parser.parse_args()

    top_k = 1000000 if args.strict else args.top
    diags = run_diagnosis(
        args.results_dir,
        args.max_cc_rects,
        top_k,
        split_only=args.strict,
    )
    shown = diags[: args.top]
    print_report(str(args.results_dir), shown)

    scrub_hits = [d for d in shown if d.m10_removed_by_scrub]
    if scrub_hits:
        print(f"\nScrub removed m10 on {len(scrub_hits)} candidate nets in top-{args.top}")

    high_cc = [d for d in shown if d.same_layer_components > 10]
    if high_cc:
        print(f"Highly fragmented (CC>10): {len(high_cc)} nets in top-{args.top}")

    if args.strict:
        failures = [diag for diag in diags if strict_failure(diag)]
        if failures:
            print(f"\nSTRICT FAIL: {len(failures)} HBT split nets violate guide invariants")
            print_report("strict failures", failures[: args.top])
            return 1
        print("\nSTRICT PASS: all HBT split net guides are die-local and HBT-connected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
