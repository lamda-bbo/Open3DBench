# OpenROAD 3D GRT Baseline

This directory contains the modifiable OpenROAD global-routing baseline. It is the main development area for changing the 3D GRT algorithm and developing the metal layer sharing policy. 

## 1. OpenROAD source files

| File | Baseline function |
|---|---|
| `src/grt/include/grt/GlobalRouter.h` | Stores the per-net routing-layer range and exposes the C++ interface. |
| `src/grt/src/GlobalRouter.cpp` | Applies net constraints, preserves physical pin-access GCells, and validates restricted-net terminals. |
| `src/grt/src/GlobalRouter.{i,tcl}` | Exposes `set_net_routing_layers` to Tcl. |
| `src/grt/src/Pin.h` | Carries the pin data needed by die-local routing and guide generation. |
| `src/grt/src/fastroute/include/{DataType.h,FastRoute.h}` | Propagates each net's allowed layer interval into FastRoute data structures. |
| `src/grt/src/fastroute/src/{FastRoute.cpp,utility.cpp}` | Enforces the interval during topology construction, resource accounting, layer assignment, maze expansion, and route reconstruction. |

The primary source-level extension is:

```tcl
set_net_routing_layers <net_name> <min_layer> <max_layer>
```

This is a hard per-net constraint. A restricted net cannot use the other die's metal layers as a congestion fallback.

## 2. GRT Baseline

### 2.1 Net classification

`export_die_net_lists.py` reads `4_1_cts.def`, including component ownership, package I/O pins, and HBT pins. It writes:

- `bottom_2d.txt`: nets routed in the bottom-die pass;
- `upper_2d.txt`: nets routed in the upper-die pass;

The input represents a cross-die connection as two die-local subnets joined by an HBT instance. The HBT `BOT` and `TOP` pins remain real routing terminals.

### 2.2 Isolated two-pass routing

The baseline routes the two metal stacks separately:

1. The bottom pass loads `4_cts.odb`, applies the bottom layer interval to all bottom nets, and writes `route_bottom.guide`.
2. The upper pass starts an isolated OpenROAD process, applies the upper layer interval to all upper nets, and writes `route_upper.guide`.
3. The two standard guide files are merged into `route.guide` and loaded into `5_1_grt.odb`.

Process isolation keeps the two routing-resource views independent. The layer restriction itself is enforced in the routing algorithm, rather than by clamping guide layers after routing.

### 2.3 Pin access and validation

Boundary pin shapes may touch more than one GCell. The OpenROAD changes retain both the router-selected terminal GCell and the GCell derived from the physical pin geometry, then check that every restricted-net terminal is covered by the generated route. Postprocessing is validation-only: the flow merges raw guides, checks that 2D nets stay in their assigned metal stack, and performs a strict connectivity check. 

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

## 6. Main Outputs

| Output | Description |
|---|---|
| `die_net_lists/{bottom_2d,upper_2d,special}.txt` | Net classification used by the two passes. |
| `route_bottom.guide` | Raw bottom-die guide file. |
| `route_upper.guide` | Raw upper-die guide file. |
| `route.guide` | Merged guide submitted to the next routing stage. |
| `5_1_grt.odb` | OpenDB database containing the merged global-routing guides. |
| `congestion_bottom.rpt` | Bottom-pass congestion report. |
| `grt_pass_upper.log`, `grt_finalize.log` | Isolated-pass and finalization logs. |

Run the flow-script tests after changing DEF parsing or net classification:

```bash
python3 -m unittest discover \
  OpenROAD-GRT-HBT/flow_scripts/scripts_3D/tests -v
```
