"""
Greedy-based 3D placement pipeline.

Flow: partition → upper_die_macro_place (skyline heuristic) → bottom_die_macro_place (skyline heuristic) → cell_placement → cell_legalization.
"""
import os
import sys
import csv
import time
import numpy as np

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)

from src.run_dmp import ProblemInstance, seed_torch
from src.place_3d.greedyPlacer import GreedyMacroPlacer
from src.utils import DefProcessor
from src.utils.layout_plotter import LayoutPlotter

import src.place_3d.main as main_mod
from src.place_3d.main import (
    process_args,
    step_1_partition,
    step_7_cell_replacement,
    step_8_cell_legalization,
)


def get_result_dir_greedy(partition_method):
    """Result/log directory for tiling pipeline, separate from main.py (e.g. results/mol-tiling-min-cut)."""
    if partition_method == "min-cut":
        return "results/mol-tiling-min-cut"
    if partition_method == "max-cut":
        return "results/mol-tiling-max-cut"
    if partition_method == "GNN":
        return "results/mol-tiling"
    return "results/mol-tiling"


def save_and_fix_def(args, init_problem_instance, partition_method):
    """
    Save current placement DEF and fix macro status/direction -> macro_fixed.def.
    No place_2D; only DEF I/O and fix.
    """
    print("\n" + "=" * 50)
    print("Save DEF + Fix Macros (before macro place)")
    print("=" * 50)
    result_dir = get_result_dir_greedy(partition_method)
    placement_path = os.path.join(result_dir, "def_before_macro", f"{args.benchmark}.def")
    os.makedirs(os.path.dirname(placement_path), exist_ok=True)
    # save_placement expects results['placement']; sync from placedb if missing
    if not hasattr(init_problem_instance, "results") or init_problem_instance.results is None:
        init_problem_instance.results = {}
    if "placement" not in init_problem_instance.results:
        db = init_problem_instance.dmp_placedb
        init_problem_instance.results["placement"] = (db.node_x.copy(), db.node_y.copy())
    init_problem_instance.save_placement(placement_path)
    print(f"Placement DEF saved to: {placement_path}")
    fixed_def_path = os.path.join("benchmarks", "or_3D", args.benchmark, "macro_fixed.def")
    print("Processing DEF (fix macro status and change directions to N)...")
    res = DefProcessor.fix_def_file_from_instance(
        init_problem_instance,
        placement_path,
        fixed_def_path,
        change_direction=True,
    )
    print(f"Fixed {res['fixed_count']} macros, changed {res['changed_direction_count']} macro directions to N")
    print(f"Fixed DEF saved to: {fixed_def_path}")
    return fixed_def_path


def upper_die_macro_place(args, problem_instance, partition_result):
    """
    Place upper-die macros. No prototyping; only macro names and problem instance.
    """
    print("\n" + "=" * 50)
    print("Upper-Die Macro Placement (Greedy Skyline)")
    print("=" * 50)
    macro_names = partition_result["upper_die_macro_names"]
    params = getattr(args, "macro_place_params", None) or {}
    device = f"cuda:{args.gpu}" if args.use_cuda else "cpu"
    placer = GreedyMacroPlacer(problem_instance, macro_names, params=params, device=device)
    placer.optimize(num_iterations=1, verbose=True, plot_interval=None, plot_dir=None, log_dir=None)
    placer.update_placement()
    print(f"Upper-die: placed {len(macro_names)} macros.")


def bottom_die_macro_place(args, problem_instance, partition_result):
    """
    Place bottom-die macros. No prototyping; only macro names and problem instance.
    """
    print("\n" + "=" * 50)
    print("Bottom-Die Macro Placement (Greedy Skyline)")
    print("=" * 50)
    macro_names = partition_result["bottom_die_macro_names"]
    params = getattr(args, "macro_place_params", None) or {}
    device = f"cuda:{args.gpu}" if args.use_cuda else "cpu"
    placer = GreedyMacroPlacer(problem_instance, macro_names, params=params, device=device)
    placer.optimize(num_iterations=1, verbose=True, plot_interval=None, plot_dir=None, log_dir=None)
    placer.update_placement()
    print(f"Bottom-die: placed {len(macro_names)} macros.")


def plot_two_die_macros(problem_instance, partition_result, result_dir, benchmark):
    """Visualize upper-die and bottom-die macro layout using LayoutPlotter.plot_3d_macro_placement."""
    db = problem_instance.dmp_placedb
    xl, yl = float(db.xl), float(db.yl)
    xh, yh = float(db.xh), float(db.yh)

    def get_macro_arrays(names):
        ids = [db.node_name2id_map[n] for n in names if n in db.node_name2id_map]
        if not ids:
            return np.array([]), np.array([]), np.array([]), np.array([])
        ids = np.array(ids)
        return (
            db.node_x[ids].copy(),
            db.node_y[ids].copy(),
            db.node_size_x[ids].copy(),
            db.node_size_y[ids].copy(),
        )

    upper_x, upper_y, upper_w, upper_h = get_macro_arrays(partition_result["upper_die_macro_names"])
    bottom_x, bottom_y, bottom_w, bottom_h = get_macro_arrays(partition_result["bottom_die_macro_names"])

    figure_path = os.path.join(result_dir, "macro_layout", f"{benchmark}_two_die.png")
    LayoutPlotter.plot_3d_macro_placement(
        bottom_die_macro_x=bottom_x,
        bottom_die_macro_y=bottom_y,
        bottom_die_macro_w=bottom_w,
        bottom_die_macro_h=bottom_h,
        upper_die_macro_x=upper_x,
        upper_die_macro_y=upper_y,
        upper_die_macro_w=upper_w,
        upper_die_macro_h=upper_h,
        xl=xl, yl=yl, xh=xh, yh=yh,
        figure_path=figure_path,
    )
    print(f"Two-die macro layout plot saved to: {figure_path}")
    return figure_path


def main():
    """
    Flow: partition → (save DEF + fix macro) → upper_die_macro_place → bottom_die_macro_place
          → cell_placement → cell_legalization.
    Macro place uses problem_instance loaded from macro_fixed.def.
    """
    start_time = time.time()
    args, _ = process_args()
    seed_torch(args.seed)
    partition_method = (args.partition_params or {}).get("method", "GNN")

    print("\nCreating ProblemInstance...")
    init_problem_instance = ProblemInstance(args, args.benchmark)
    partition_result = step_1_partition(args, init_problem_instance)

    # Before macro place: save DEF + fix macro -> macro_fixed.def (no place_2D)
    fixed_def_path = save_and_fix_def(args, init_problem_instance, partition_method)
    # Macro place uses problem_instance loaded from macro_fixed.def
    print("\nLoading problem_instance from macro_fixed.def for macro placement...")
    problem_instance = ProblemInstance(
        args, args.benchmark, def_path=fixed_def_path, rand_init=False
    )

    upper_die_macro_place(args, problem_instance, partition_result)
    bottom_die_macro_place(args, problem_instance, partition_result)

    # Visualize two-die macro layout (LayoutPlotter.plot_3d_macro_placement)
    result_dir = get_result_dir_greedy(partition_method)
    plot_two_die_macros(problem_instance, partition_result, result_dir, args.benchmark)

    # Before cell placement: save macro-place result DEF and re-read from it (same as main.py shrunk_problem_instance)
    after_macro_def = os.path.join(result_dir, "after_macro", f"{args.benchmark}.def")
    os.makedirs(os.path.dirname(after_macro_def), exist_ok=True)
    problem_instance.save_placement(after_macro_def)
    print(f"\nCreating cell_problem_instance from DEF after macro place: {after_macro_def}")
    cell_problem_instance = ProblemInstance(
        args,
        args.benchmark,
        upper_die_macros=partition_result["upper_die_macro_names"],
        only_cells=True,
        def_path=after_macro_def,
    )

    # Cell placement & legalization: use greedy result dir so outputs don't mix with main.py
    main_mod.get_result_dir = get_result_dir_greedy
    final_cell_hpwl = step_7_cell_replacement(args, cell_problem_instance, partition_result)
    legalized_hpwl = step_8_cell_legalization(args, partition_result)

    total_runtime = time.time() - start_time
    result_dir = get_result_dir_greedy(partition_method)

    print("\n" + "=" * 50)
    print("Pipeline Summary (Greedy)")
    print("=" * 50)
    print("Flow: partition → (save DEF + fix macro) → upper_macro_place → bottom_macro_place → cell_placement → cell_legalization")
    print(f"Mem-on-logic HPWL before legalization: {final_cell_hpwl:.2f}")
    print(f"Mem-on-logic HPWL after legalization: {legalized_hpwl:.2f}")
    print(f"Total Runtime: {total_runtime:.2f} s ({total_runtime / 60:.2f} min)")
    print("=" * 50)

    csv_path = os.path.join(result_dir, "mol_final", "mem_on_logic_results.csv")
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    existing_rows = []
    if os.path.exists(csv_path):
        with open(csv_path, "r", newline="") as f:
            existing_rows = list(csv.reader(f))
    if existing_rows and "runtime" not in existing_rows[0]:
        existing_rows[0].append("runtime")
        for row in existing_rows[1:]:
            row.append("")
        with open(csv_path, "w", newline="") as f:
            csv.writer(f).writerows(existing_rows)
    with open(csv_path, "a", newline="") as f:
        w = csv.writer(f)
        if not existing_rows:
            w.writerow(["design_name", "hpwl", "hpwl_lg", "runtime"])
        w.writerow([args.benchmark, final_cell_hpwl, legalized_hpwl, total_runtime])
    print(f"Saved to CSV: {csv_path}")


if __name__ == "__main__":
    main()
