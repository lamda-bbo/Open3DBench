# 2026 EDA Elite Challenge: Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC

This repository provides the public code, benchmark interface, and baseline for the **2026 China Graduate IC Innovation Competition - EDA Elite Challenge**.

赛题中文名称：**时序驱动与 HB 布局协同的面对面键合 3D-IC 三维全局布线方法**

English title: **Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC**

## 1. Contest Description

The contest asks participants to co-optimize Metal Layer Sharing net selection and subnet assignment, incremental HBT placement, and timing-driven 3D global routing. The submitted algorithm must produce a routed OpenDB database containing the resulting guides, HBT placement, and net/subnet connectivity.

## 2. Quick Start

Pull the contest image and clone the `EDA_contest` branch:

```bash
docker pull gaocr/3dbench-contest:20260724

git clone --branch EDA_contest --single-branch \
  https://github.com/lamda-bbo/Open3DBench.git
cd Open3DBench
```

Download the input archive from Section 4, place it in `input/`, and extract
it:

```bash
mkdir -p input
tar -xzf \
  input/open3dbench_8cases_post_hbt_input_20260724.tar.gz \
  -C input
```

Start the contest container from the repository root:

```bash
./start_contest_docker.sh
```

All subsequent commands are run inside this container. Compile the GRT
baseline with 32 parallel build jobs, then run `bp_fe`:

```bash
contest build 32

INPUT=/workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724
contest run-grt bp_fe "$INPUT" baseline
```

Run the fixed DRT, DRC, and timing evaluator:

```bash
contest evaluate \
  bp_fe \
  "$INPUT" \
  /workspace/Open3DBench/output/bp_fe/baseline \
  /workspace/Open3DBench/reports/bp_fe/baseline
cat reports/bp_fe/baseline/metrics.json
```

Replace `bp_fe` and `baseline` to run another case or keep multiple experiment
outputs. GRT results are stored under `output/`, and evaluation reports are
stored under `reports/`.

## 3. Repository and Baseline

```text
Open3DBench/
├── OpenROAD-GRT/       # Modified OpenROAD with the 3D GRT baseline
│   ├── openroad_src/   # Source code for OpenROAD src/grt
│   └── flow_scripts/   # GRT and post-route HBT conversion scripts
├── OpenROAD-3D/        # OpenROAD-based 3D backend flow
├── Place-MoL/          # Memory-on-Logic placement flow
└── Place-LoL/
```

The supplied baseline is a reproducible starting point for development. It
routes the HBT locations and `_BOT`/`_TOP` subnets already present in the input
and does not introduce additional Metal Layer Sharing nets.

### 3.1 Restricted die-by-die GRT baseline

The provided OpenROAD source adds a per-net routing-layer range to `GlobalRouter` and propagates it into FastRoute. The allowed layer range is enforced during topology generation, resource accounting, maze expansion, and route reconstruction, so a die-local net cannot move to the opposite die as a congestion fallback. HBT pins are retained as real routing terminals that can be naturally processed by the router.

### 3.2 Multi-pass run

1. Classify the input net into bottom-die and top-die subnets.
2. Route bottom-die subnets on `metal2-metal10` and top-die subnets on `metal11-metal20` in isolated OpenROAD processes.
3. Merge the two standard guide results and import them into the final `5_1_grt.odb`.

## 4. Input and Output Files

Input package download:

> [Download the public input package from Google Drive](https://drive.google.com/file/d/1o4ExxQX9lBswf4VWYGUsLMqjWBKLCTW6/view?usp=share_link)

Expected archive: `open3dbench_8cases_post_hbt_input_20260724.tar.gz`

SHA-256:
`a7e254f8f4f2b84696ba2601ea6d2e4da76d083a336ac01981f0ed6b8c196814`

```text
open3dbench_8cases_post_hbt_input_20260724/
├── README.txt
├── MANIFEST.sha256
├── cases/<case>/
│   ├── grt_input/
│   └── flow_design/
└── platforms/nangate45_3D/
```

### 4.1 Per-Case Inputs

| File | Information described by the file |
|---|---|
| `cases/<case>/grt_input/4_1_cts.def` | Die area, rows and tracks, component and macro placement, pins, nets, CTS result, and the baseline HBT instances and segmented nets. |
| `cases/<case>/grt_input/4_cts.sdc` | Clocks, clock uncertainty, I/O delays, timing exceptions, and other timing constraints associated with the CTS design. |
| `cases/<case>/flow_design/config*.mk` | Design name, platform selection, source-file paths, routing layers, utilization targets, and flow parameters for the case. |
| `cases/<case>/flow_design/*.sdc` | Original design-level clock and timing constraints referenced by the case configuration. |
| `cases/<case>/flow_design/*.v` and `*.sv2v.v` | Verilog module, macro-wrapper, or design-source definitions required by the case. |
| `cases/<case>/flow_design/fastroute.tcl` | Case-specific global-routing layer adjustments and routing-capacity settings, when present. |

### 4.2 Platform Inputs

| File | Information described by the file |
|---|---|
| `platforms/nangate45_3D/config.mk` | Platform file locations, routing-layer definitions, RC setup, and default physical-design parameters. |
| `platforms/nangate45_3D/lef*/**.lef` | Manufacturing grid, routing and cut layers, tracks, vias, design rules, standard-cell geometry, macro geometry, and pin shapes. |
| `platforms/nangate45_3D/lib*/**.lib` | Cell and macro timing arcs, delays, constraints, capacitance, transition, and power models. |
| `platforms/nangate45_3D/setRC.tcl` and `nangate45_3D.rules` | Wire/via resistance-capacitance settings and extraction rules used for timing evaluation. |
| `platforms/nangate45_3D/fastroute.tcl`, `make_tracks.tcl`, and `grid_strategy*.tcl` | Default routing-layer adjustments, routing-track definitions, and power-grid settings. |
| `platforms/nangate45_3D/gds/`, `cdl/`, and `drc/` | Layout geometry, transistor-level connectivity, and physical-verification rule files. |
The input DEF provides a reproducible baseline state. Contest algorithms may change HBT placement and subnet connectivity as part of the required co-optimization, but must preserve all non-HBT component placement.

The evaluator models every HBT as a 3.0 ohm series via and 0.6 fF total
ground capacitance. The capacitance is divided equally between the metal10 and
metal11 ends of the extracted HBT resistor.

### 4.3 Required Output

| File | Information contained in the file |
|---|---|
| `5_1_grt.odb` | Final OpenDB database containing component placement, optimized HBT placement, net/subnet connectivity, and global-routing guides. |
| `route.guide` | Text representation of the global-routing guide rectangles and their routing layers. |

## 5. Baseline Results

The following clean-machine baseline was completed on all eight public cases
with the supplied input package, a 6.4 um HBT pitch, the 3D GRT baseline, the
binary 3D detailed-route evaluator, 32 DRT threads, and `droute_end_iter=2`
(initial routing plus two optimization iterations). Runtime is sequential
wall-clock time for GRT plus the complete evaluator, including DRT, unified
DRC, RC extraction, and final reporting, rounded to the nearest second. TNS
and WNS are setup metrics reported by OpenSTA after extraction of the final
routed database.

The timing columns predate the explicit 3.0 ohm/0.6 fF HBT RC model and must
be refreshed before they are used as final reference values.

| Case | Runtime | HBTs | GRT-WL (um) | DRT-WL (um) | DRC | TNS (ns) | WNS (ns) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `ariane133` | 0:46:36 | 4,025 | 7,296,432 | 5,677,850 | 20,136 | -3,588.38 | -1.58131 |
| `ariane136` | 0:48:33 | 4,046 | 7,318,850 | 5,667,230 | 20,498 | -733,528 | -33.9244 |
| `black_parrot` (`bp`) | 0:54:51 | 3,847 | 9,878,607 | 7,812,700 | 23,346 | -44,016.7 | -6.23160 |
| `bp_fe` | 0:07:58 | 1,149 | 1,660,760 | 1,378,720 | 5,618 | -2,697.30 | -1.35095 |
| `bp_be` | 0:13:34 | 1,105 | 2,909,234 | 2,368,436 | 9,744 | -1,524.91 | -1.41043 |
| `bp_multi` | 0:28:26 | 3,072 | 4,882,352 | 3,883,294 | 17,236 | -38,124.9 | -6.49778 |
| `swerv_wrapper` | 0:27:00 | 1,278 | 4,608,273 | 3,723,482 | 17,065 | -651.869 | -0.829784 |
| `bp_quad` | 4:49:47 | 27,835 | 51,423,464 | 41,690,978 | 31,078 | -547,196 | -27.9044 |
