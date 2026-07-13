#!/usr/bin/env python3
"""Re-apply MoL post-GRT guide fixes (clamp, merge, HBT inject, scrub) without OpenROAD."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
FLOW_DIR = SCRIPT_DIR.parent


def run_py(script: str, args: list[str]) -> None:
    """Run a helper script under scripts_3D."""
    cmd = [sys.executable, str(SCRIPT_DIR / script), *args]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


DESIGN_CONFIGS: dict[str, str] = {
    "ariane133": "designs/nangate45_3D/ariane133/config_mol_die.mk",
    "ariane136": "designs/nangate45_3D/ariane136/config_mol_die.mk",
    "bp_fe": "designs/nangate45_3D/bp_fe_top/config_mol_die.mk",
}


def resolve_design_variant(results_dir: Path) -> tuple[str, str]:
    """Extract design nick and flow variant from a MoL results directory."""
    resolved = results_dir.resolve()
    roots: list[Path] = []
    work_home = os.environ.get("WORK_HOME", "").strip()
    if work_home:
        roots.append(Path(work_home) / "results")
    roots.append(FLOW_DIR / "results")

    for root in roots:
        try:
            rel = resolved.relative_to(root.resolve())
        except ValueError:
            continue
        if len(rel.parts) >= 3:
            return rel.parts[1], rel.parts[2]

    msg = f"Cannot resolve design/variant from results dir: {results_dir}"
    raise ValueError(msg)


def run_finalize(results_dir: Path) -> None:
    """Load updated route.guide into 5_1_grt.odb via OpenROAD."""
    design, variant = resolve_design_variant(results_dir)
    config = DESIGN_CONFIGS.get(design)
    if config is None:
        raise ValueError(f"No DESIGN_CONFIG mapping for design {design}")
    cmd = [
        "make",
        f"DESIGN_CONFIG={config}",
        f"FLOW_VARIANT={variant}",
        "do-mol-grt-finalize-only",
    ]
    work_home = os.environ.get("WORK_HOME", "").strip()
    if work_home:
        cmd[1:1] = [f"WORK_HOME={work_home}"]
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=FLOW_DIR)


def reprocess(
    results_dir: Path,
    *,
    scrub: bool,
    validate: bool,
    finalize: bool,
) -> None:
    """Replay guide post-processing for one MoL results directory."""
    bottom = results_dir / "route_bottom.guide"
    upper = results_dir / "route_upper.guide"
    merged = results_dir / "route.guide"
    def_file = results_dir / "4_1_cts.def"

    if not bottom.exists() or not upper.exists():
        raise FileNotFoundError(f"Missing pass guides in {results_dir}")
    if not def_file.exists():
        raise FileNotFoundError(f"Missing DEF {def_file}")

    os.environ.setdefault("RESULTS_DIR", str(results_dir))

    run_py("clamp_pass_guide_layers.py", [str(bottom), "1", "10", str(bottom)])
    run_py("clamp_pass_guide_layers.py", [str(upper), "11", "20", str(upper)])
    run_py(
        "merge_route_guides.py",
        [str(merged), str(bottom), str(upper)],
    )
    run_py("inject_hbt_cover_guides.py", [str(merged), str(def_file), str(merged)])
    if scrub:
        run_py(
            "scrub_2d_net_guide_layers.py",
            [str(merged), str(def_file), str(merged)],
        )
    run_py("check_2d_net_guide_layers.py", [str(merged), str(def_file)])
    if validate:
        run_py(
            "diagnose_guide_connectivity.py",
            [
                str(results_dir),
                "--strict",
                "--top",
                "50",
                "--max-cc-rects",
                os.environ.get("DIE_GUIDE_MAX_CC_RECTS", "5000"),
            ],
        )
    if finalize:
        run_finalize(results_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_dir",
        type=Path,
        help="e.g. results/nangate45_3D/ariane133/mol_die",
    )
    parser.add_argument(
        "--no-scrub",
        action="store_true",
        help="Skip scrub_2d_net_guide_layers.py",
    )
    parser.add_argument(
        "--no-finalize",
        action="store_true",
        help="Skip OpenROAD finalize (read_guides -> 5_1_grt.odb)",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip strict HBT split-net guide validation",
    )
    args = parser.parse_args()
    reprocess(
        args.results_dir.resolve(),
        scrub=not args.no_scrub,
        validate=not args.no_validate,
        finalize=not args.no_finalize,
    )
    print(f"PASS guide reprocess: {args.results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
