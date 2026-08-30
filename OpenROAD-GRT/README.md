# OpenROAD 3D GRT Baseline

This directory contains the modifiable OpenROAD global-routing baseline. It is the main development area for changing the 3D GRT algorithm and developing the metal layer sharing policy. 

## 1. OpenROAD source files

The files below are relative to `openroad_src/`.

| File | Role in global routing |
|---|---|
| `src/grt/include/grt/GlobalRouter.h` | Declares the top-level global router, including its configuration, routing state, guide I/O, incremental-routing, congestion, and reporting interfaces. |
| `src/grt/src/GlobalRouter.cpp` | Implements the main GRT flow: builds the routing grid and capacities from OpenDB, creates net and pin models, invokes the routing engine, and converts the result into routing guides. |
| `src/grt/src/GlobalRouter.{i,tcl}` | Defines the Tcl/SWIG command interface, argument checking, and user-facing wrappers for configuring and running global routing. |
| `src/grt/src/Pin.h` | Defines the routing-terminal model, including pin geometry, routing layers, physical and on-grid locations, and attributes used to select access points. |
| `src/grt/src/fastroute/include/DataType.h` | Defines FastRoute's core data structures for nets, grid edges, routing trees, segments, and maze routes. |
| `src/grt/src/fastroute/include/FastRoute.h` | Declares the FastRoute routing engine and its APIs for grid construction, topology generation, congestion optimization, layer assignment, and route extraction. |
| `src/grt/src/fastroute/src/{FastRoute.cpp,utility.cpp}` | Implements the FastRoute pipeline, including net initialization, routing-resource accounting, Steiner topology processing, congestion-driven rip-up and reroute, layer assignment, and segment generation. |

The primary source-level extension is:

```tcl
set_net_routing_layers <net_name> <min_layer> <max_layer>
```

This is a hard per-net constraint. A restricted net cannot use the other die's metal layers as a congestion fallback.

The baseline optionally runs `GRT_PREPARE_TCL` to update HBT placement or subnet connectivity, then classifies the selected input design into bottom- and upper-die net lists. It routes the two metal stacks in isolated OpenROAD processes, using `metal2-metal10` for bottom-die nets and `metal11-metal20` for upper-die nets. The two guide files are merged into `route.guide` and loaded into `5_1_grt.odb`; final checks verify layer ownership, terminal coverage, and guide connectivity without modifying the routing result.

## 3. GRT Hyperparameters

The following environment variables control the baseline. Defaults are defined in `flow_scripts/scripts_3D/global_route_die_by_die.tcl`.

| Variable | Default | Meaning |
|---|---:|---|
| `BOTTOM_DIE_MIN_LAYER` | `metal2` | Lowest signal-routing layer in the bottom pass. |
| `BOTTOM_DIE_MAX_LAYER` | `metal10` | Highest signal-routing layer in the bottom pass. |
| `UPPER_DIE_MIN_LAYER` | `metal11` | Lowest signal-routing layer in the upper pass. |
| `UPPER_DIE_MAX_LAYER` | `metal20` | Highest signal-routing layer in the upper pass. |
| `GLOBAL_ROUTING_LAYER_ADJUSTMENT` | `0.5` | Capacity adjustment applied to the active layer interval. |
| `GLOBAL_ROUTE_ARGS` | `-congestion_iterations 2 -congestion_report_iter_step 5 -verbose` | Arguments passed to each `global_route` invocation. |
| `MACRO_EXTENSION` | platform setting | Optional macro blockage extension in GCells. |
| `VALIDATE_DIE_GUIDES` | `1` | Set to `0` only to skip merged-guide validation. |
| `DIE_GUIDE_MAX_CC_RECTS` | `5000` | Rectangle limit used by the strict connectivity diagnostic. |
| `OPENROAD_EXE` | `openroad` | OpenROAD executable used for isolated upper and finalize processes. |
| `GRT_PREPARE_TCL` | unset | Optional one-time HBT placement and netlist preparation script. |

`GRT_PASS_NET_LIST`, `GRT_PASS_GUIDE_OUT`, `GRT_PASS_MIN_LAYER`, and `GRT_PASS_MAX_LAYER` are internal pass variables set by the main Tcl script; they are not normal tuning knobs.

Example override:

```bash
export GLOBAL_ROUTING_LAYER_ADJUSTMENT=0.5
export GLOBAL_ROUTE_ARGS="-congestion_iterations 4 -congestion_report_iter_step 2 -verbose"
```

## 4. Build and Run

Run the following commands from the repository root. The container setup and
input download are described in the top-level `README.md`.

Start the environment:

```bash
./start_contest_docker.sh
```

All remaining commands are run inside the container. Compile the OpenROAD GRT
overlay with 32 build jobs:

```bash
contest build 32
```

Run the baseline on `bp_fe`:

```bash
INPUT=/workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724
contest run-grt bp_fe "$INPUT" baseline
```

To keep multiple configurations, change the final run label, for example `baseline_c4`. C++ changes under `openroad_src/` require another `contest build`; Tcl and Python flow changes are used by the next prepared run.

The fixed evaluator can consume the GRT output as follows:

```bash
contest evaluate \
  bp_fe \
  "$INPUT" \
  /workspace/Open3DBench/output/bp_fe/baseline \
  /workspace/Open3DBench/reports/bp_fe/baseline
```

## 5. Script Execution Path

| Order | Script | Purpose |
|---:|---|---|
| 1 | `flow_scripts/scripts/global_route_die_by_die.tcl` | Flow-compatible entry point. |
| 2 | `scripts_3D/global_route_die_by_die.tcl` | Loads the design, exports net lists, and runs both die passes. |
| 3 | `scripts_3D/global_route_single_pass.tcl` | Runs the isolated upper-die pass. |
| 4 | `scripts_3D/merge_route_guides.py` | Concatenates the two standard guide sets without changing rectangles. |
| 5 | `scripts_3D/check_2d_net_guide_layers.py` | Verifies die-local layer ownership. |
| 6 | `scripts_3D/diagnose_guide_connectivity.py` | Checks strict guide and terminal connectivity. |
| 7 | `scripts_3D/finalize_die_by_die_grt.tcl` | Reads the merged guides and writes the routed ODB. |

## 6. Raw Outputs

| Output | Description |
|---|---|
| `die_net_lists/{bottom_2d,upper_2d,special}.txt` | Net classification used by the two passes. |
| `4_grt_input.{odb,def}` | Optional shared snapshot produced only when `GRT_PREPARE_TCL` is set. |
| `route_bottom.guide` | Raw bottom-die guide file. |
| `route_upper.guide` | Raw upper-die guide file. |
| `route.guide` | Merged guide submitted to the next routing stage. |
| `5_1_grt.odb` | OpenDB database containing the merged global-routing guides. |
| `congestion_{bottom,upper}.rpt` | Per-die congestion reports from the bottom and upper routing passes. |
| `grt_pass_upper.log`, `grt_finalize.log` | Isolated-pass and finalization logs. |
