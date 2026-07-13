# EDA Contest GRT/HBT OpenROAD Patch

This directory contains the public OpenROAD changes for the EDA contest branch.
It only includes die-by-die global routing and HBT-related code. Die-by-die
detailed-routing evaluator code is intentionally not included.

## Directory Layout

```text
OpenROAD-GRT-HBT/
├── openroad_src/   # OpenROAD GRT source overlay
└── flow_scripts/   # OpenROAD-3D flow scripts for HBT and die-by-die GRT
```

`openroad_src/` should be overlaid on an OpenROAD source tree before building.
The files are restricted to `src/grt` and FastRoute:

- `src/grt/include/grt/GlobalRouter.h`
- `src/grt/src/GlobalRouter.{cpp,i,tcl}`
- `src/grt/src/Pin.h`
- `src/grt/src/fastroute/include/{DataType.h,FastRoute.h}`
- `src/grt/src/fastroute/src/{FastRoute.cpp,utility.cpp}`

`flow_scripts/` should be overlaid on `OpenROAD-3D/flow`. It contains HBT
generation/modeling scripts and die-by-die GRT guide scripts only.

## Inputs

The contest-facing flow expects the following inputs:

| File | Description |
|---|---|
| `4_1_cts.def` | Post-CTS DEF after contestant HBT placement and netlist split. HBT instances should appear as normal instances with `BOT` and `TOP` pins. |
| `*.lef`, tech LEF | Standard-cell, macro, and 3D technology LEF files. The default stack uses bottom routing layers `metal1-metal10` and top routing layers `metal11-metal20`. |
| `*.lib`, `*.sdc` | Timing libraries and constraints used by the OpenROAD flow. |
| optional die net lists | Lists of bottom-only and top-only 2D nets. If omitted, they can be inferred from DEF connectivity and HBT pin ownership. |

The GRT flow reads the DEF through OpenROAD/ODB, applies per-net routing-layer
constraints, and writes standard OpenROAD route guides.

## Outputs

| File | Description |
|---|---|
| `route.guide` | Merged global-routing guide for all nets. |
| `5_1_grt.odb` | ODB after global routing. |
| `*.rpt`, `*.log`, `*.json` | Runtime, GRT wirelength, overflow, and flow diagnostics. |
| HBT DEF/guide intermediates | Optional files emitted by the HBT split and guide-finalization scripts for debugging and reproducibility. |

The hidden evaluator may later consume `route.guide` and `5_1_grt.odb` to run
detailed route and DRC checks. The evaluator implementation is not part of this
package.

## Die-By-Die GRT Algorithm

The public GRT patch adds a per-net routing-layer range API to OpenROAD:

- Tcl command: `set_net_routing_layers <net> <min_layer> <max_layer>`
- C++ storage: per-net layer ranges in `GlobalRouter`
- FastRoute behavior: hard layer ranges prevent fallback assignment outside the
  requested die layer window when resources are scarce.

The flow classifies nets into three groups:

| Net type | Routing layer range |
|---|---|
| bottom 2D net | `metal1-metal10` |
| top 2D net | `metal11-metal20` |
| cross-die/HBT net | unrestricted or explicitly bridged through HBT pins |

After global routing, the guide finalization step merges bottom/top pass guides,
adds required pin-access anchors, and scrubs out-of-die guide rectangles for
strict 2D nets. HBT boundary pins are preserved as real guide targets so GRT
does not silently drop the vertical connection point.

## HBT Algorithm

The HBT scripts convert a split 3D net into explicit HBT connectivity:

1. Parse the post-CTS DEF and the split net structure.
2. Create or preserve HBT instances at legal hybrid-bonding coordinates.
3. Connect each HBT through a `BOT` pin on the lower die and a `TOP` pin on the
   upper die.
4. Model those pins on the boundary routing layers, usually `metal10` and
   `metal11`.
5. Feed the HBT pins into GRT as normal net terminals so the generated guide
   reaches the HBT location.

The included greedy HBT placer is a simple baseline: it assigns HBT locations by
local net demand and geometric proximity while respecting the available HBT
site grid. Contestants can replace this module with their own HBT-placement and
net-splitting algorithms as long as the resulting DEF follows the same
interface.

## Baseline Evaluation Results

The table below reports the existing baseline run using the public die-by-die
GRT/HBT code and the hidden detailed-route evaluator. These results were
collected on the current development server on 2026-07-13. `running` and
`not-started` entries are included for completeness.

| case | status | wall runtime | GRT runtime | DRT WL | DRC |
|---|---:|---:|---:|---:|---:|
| ariane133 | DONE | 5:22:47 | 00:01:48 | 5,690,813 | 82,274 |
| ariane136 | DONE | 4:42:36 | 00:01:52 | 5,677,655 | 89,452 |
| bp_fe | DONE | 0:28:35 | 00:00:14 | 1,287,086 | 17,396 |
| bp_be | DONE | 1:03:34 | 00:00:46 | 2,338,762 | 36,547 |
| swerv_wrapper | DONE | 2:18:29 | 00:01:43 | 3,805,093 | 77,207 |
| bp_multi | DONE | 2:34:54 | 00:00:57 | 3,872,559 | 58,055 |
| bp | running | - | 00:03:06 | - | - |
| bp_quad | not started | - | - | - | - |

## What Is Not Included

The following code is deliberately excluded from this public package:

- die-by-die detailed routing source code
- detailed-route evaluator scripts
- `detail_route_die_by_die.tcl`
- DRT guide splitting/sanitization helpers used only by the hidden evaluator
- post-DRT cross-die checking implementation

This keeps the contest algorithm interface public while leaving the final
evaluation path private.
