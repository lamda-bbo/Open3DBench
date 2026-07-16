# EDA Contest GRT OpenROAD Patch

This directory contains the public OpenROAD changes for the EDA contest branch.
It includes the public die-by-die global-routing implementation and the HBT
generation utilities used to prepare the released inputs. Die-by-die
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

`flow_scripts/` should be overlaid on `OpenROAD-3D/flow`. It contains the
die-by-die GRT guide scripts and the HBT preparation utilities retained for
reference and reproducibility.

## Inputs

The contest-facing flow expects the following inputs:

| File | Description |
|---|---|
| `4_1_cts.def` | Provided post-placement, post-CTS, post-HBT DEF. It already contains HBT coordinates and `_BOT`/`_TOP` split-net connectivity. HBT instances appear as normal instances with `BOT` and `TOP` pins. |
| `*.lef`, tech LEF | Standard-cell, macro, and 3D technology LEF files. The default stack uses bottom routing layers `metal1-metal10` and top routing layers `metal11-metal20`. |
| `*.lib`, `*.sdc` | Timing libraries and constraints used by the OpenROAD flow. |
| optional die net lists | Lists of bottom-only and top-only 2D nets. If omitted, they can be inferred from DEF connectivity and HBT pin ownership. |

The GRT flow starts directly from this DEF, reads it through OpenROAD/ODB,
applies per-net routing-layer constraints, and writes standard OpenROAD route
guides. Contestants do not need to run HBT placement or net splitting first.

## Outputs

| File | Description |
|---|---|
| `route.guide` | Merged global-routing guide for all nets. |
| `5_1_grt.odb` | ODB after global routing. |
| `*.rpt`, `*.log`, `*.json` | Runtime, GRT wirelength, overflow, and flow diagnostics. |

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
| bottom 2D net | bottom stack `metal1-metal10`; signal routing defaults to `metal2-metal10` |
| top 2D net | `metal11-metal20` |
| cross-die/HBT net | split into die-local `_BOT` and `_TOP` subnets at an HBT |

HBT boundary pins are real guide targets. The source-level implementation
preserves the terminal and physical-geometry GCells, splits a covering segment
at the HBT when needed, and validates every restricted-net pin after routing.

The flow does not mutate algorithm output with guide injection, clamping, or
scrubbing. It merges the raw bottom/top guide files, checks layer ownership and
connectivity, and fails if the source algorithm left a pin uncovered. Obsolete
file-level guide repair scripts are not included.

## Baseline Evaluation Results

The table below reports the latest baseline from the supplied post-HBT inputs,
the public die-by-die GRT code, and the hidden detailed-route evaluator.
These results were collected on the development server on 2026-07-16. DRT used
32 threads with `droute_end_iter=2`; DRC is the unified full-stack count after
the final HBT net merge and fixed-via conversion. TNS and WNS are setup metrics
reported by OpenSTA after OpenRCX extraction of the final routed ODB.

| case | status | wall runtime | GRT WL | DRT WL | unified DRC | TNS (ns) | WNS (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| ariane133 | DONE | 1:14:01 | 7,518,274 | 5,789,263 | 20,175 | -3,641.05 | -1.58810 |
| ariane136 | DONE | 1:18:29 | 7,588,734 | 5,809,451 | 20,190 | -732,378 | -33.8851 |
| bp_fe | DONE | 0:10:11 | 1,713,704 | 1,423,445 | 5,676 | -2,698.66 | -1.35272 |
| bp_be | DONE | 0:20:35 | 2,979,267 | 2,389,764 | 9,010 | -1,526.35 | -1.41182 |
| bp | DONE | 1:23:32 | 9,984,157 | 7,846,499 | 20,172 | -43,927.0 | -6.23376 |
| bp_multi | DONE | 0:43:16 | 4,968,325 | 3,956,852 | 17,807 | -38,177.9 | -6.49767 |
| swerv_wrapper | DRT regression DONE | 0:27:52* | 4,977,322 | 3,900,344 | 16,878 | -648.691 | -0.826734 |
| bp_quad | PENDING | - | - | - | - | - | - |

`*` Checkpoint-based bottom/upper DRT regression plus unified post-DRT DRC.
Timing was subsequently measured from the same final routed ODB with the
standard final-report flow.

## What Is Not Included

The following code is deliberately excluded from this public package:

- die-by-die detailed routing source code
- detailed-route evaluator scripts
- `detail_route_die_by_die.tcl`
- DRT guide splitting/sanitization helpers used only by the hidden evaluator
- post-DRT cross-die checking implementation

This keeps the contest algorithm interface public while leaving the final
evaluation path private.
