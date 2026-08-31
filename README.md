# 2026 EDA Elite Challenge: Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC

This repository provides the public code, benchmark interface, and baseline for the **2026 China Graduate IC Innovation Competition - EDA Elite Challenge**.

赛题中文名称：**时序驱动与 HB 布局协同的面对面键合 3D-IC 三维全局布线方法**

English title: **Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC**

## 1. Contest Description

Participants are required to jointly optimize metal layer sharing net selection and subnet assignment, incremental HBT placement, and timing-driven 3D global routing. The submitted algorithm must produce a routed OpenDB database containing the final global-routing guides, HBT placement, and net/subnet connectivity.

## 2. Quick Start

Pull the contest image and clone the `EDA_contest` branch:

```bash
docker pull gaocr/3dbench-contest:20260724

git clone --branch EDA_contest --single-branch \
  https://github.com/lamda-bbo/Open3DBench.git
cd Open3DBench
```

Download the input archive, place it in `input/`, and extract it:

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

All subsequent commands are run inside this container. Compile the GRT baseline with 32 parallel build jobs, then run `bp_fe`:

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
├── Place-MoL/
└── Place-LoL/
```

The supplied baseline provides a reproducible starting point for development. It routes the HBT instances and _BOT/_TOP subnets already present in the input design and does not introduce additional Metal Layer Sharing nets.

### 3.1 Restricted die-by-die GRT baseline

The provided OpenROAD source adds a per-net routing-layer range to `GlobalRouter` and propagates it into FastRoute. The allowed layer range is enforced during topology generation, resource accounting, maze expansion, and route reconstruction, so a die-local net cannot move to the opposite die as a congestion fallback. HBT pins are retained as routing terminals that can be naturally processed by the router.

### 3.2 Multi-pass run

1. Classify the input net into bottom-die and top-die subnets.
2. Route bottom-die subnets on `metal2-metal10` and top-die subnets on `metal11-metal20` in isolated OpenROAD processes.
3. Merge the two standard guide results and import them into the final `5_1_grt.odb`.

### 3.3 HBT and subnet update interface

Algorithms that modify HBT placement or introduce additional net splits may specify GRT_PREPARE_TCL, which points to a Tcl preprocessing script that edits the loaded OpenDB design before net classification. The flow writes the result to `4_grt_input.odb` and `4_grt_input.def`, and both GRT passes and the merge step use that same snapshot.

Any HBT instance created by the GRT preparation script must satisfy the following requirements:

- The instance name must begin with HBT_ or LS_HBT_.
- The BOT pin must connect to exactly one bottom-die subnet.
- The TOP pin must connect to exactly one top-die subnet.
- The two subnets must form a matching <base>_BOT / <base>_TOP pair.
- Each HBT instance must occupy a distinct site on the 6.4 µm HBT grid.

If GRT_PREPARE_TCL is not set, the baseline directly routes the supplied `4_cts.odb` without creating an intermediate `4_grt_input.odb` or `4_grt_input.def` snapshot.

## 4. Input and Output Files

Input package download:

> [Download the public input package from Google Drive](https://drive.google.com/file/d/1o4ExxQX9lBswf4VWYGUsLMqjWBKLCTW6/view?usp=share_link)

Expected archive: `open3dbench_8cases_post_hbt_input_20260724.tar.gz`

Current public package revision: `2026-08-31`. This revision uses a 6.4 um HBT pitch, a 3.0 ohm HBT series resistance, and 0.6 fF total HBT capacitance. Verify the SHA-256 below before extracting the package.

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
| `cases/<case>/grt_input/4_1_cts.def` | Die area, rows and tracks, placement, pins, and nets |
| `cases/<case>/grt_input/4_cts.sdc` | Clocks, clock uncertainty, I/O delays, timing exceptions, and other timing constraints associated with the CTS design |
| `cases/<case>/flow_design/config*.mk` | Design name, platform selection, source-file paths, routing layers, utilization targets, and flow parameters for the case |
| `cases/<case>/flow_design/*.sdc` | Original clock and timing constraints|
| `cases/<case>/flow_design/*.v` and `*.sv2v.v` | Verilog module |
| `cases/<case>/flow_design/fastroute.tcl` | Global-routing settings |

### 4.2 Platform Inputs

| File | Information described by the file |
|---|---|
| `platforms/nangate45_3D/config.mk` | Platform file locations, routing-layer definitions, RC setup, and default physical-design parameters. |
| `platforms/nangate45_3D/lef*/**.lef` | Manufacturing grid, routing and cut layers, tracks, vias, design rules, standard-cell geometry, macro geometry, and pin shapes. |
| `platforms/nangate45_3D/lib*/**.lib` | Cell and macro timing arcs, delays, constraints, capacitance, transition, and power models. |
| `platforms/nangate45_3D/setRC.tcl` and `nangate45_3D.rules` | Wire/via resistance-capacitance settings and extraction rules used for timing evaluation. |
| `platforms/nangate45_3D/fastroute.tcl`, `make_tracks.tcl`, and `grid_strategy*.tcl` | Default routing-layer adjustments, routing-track definitions, and power-grid settings. |
| `platforms/nangate45_3D/gds/`, `cdl/`, and `drc/` | Layout geometry, transistor-level connectivity, and physical-verification rule files. |

The input DEF defines the reproducible baseline design state. Contest algorithms may modify HBT placement and subnet connectivity as part of the required co-optimization, but all non-HBT component placement must remain unchanged.

The evaluator models each HBT as a 3.0-ohm series resistance with 0.6 fF total ground capacitance. The capacitance is split equally between the metal10 and metal11 terminals of the extracted HBT resistor.

### 4.3 Required Output

| File | Information contained in the file |
|---|---|
| `5_1_grt.odb` | Final OpenDB database containing component placement, optimized HBT placement, net/subnet connectivity, and global-routing guides. |

Before DRT, the evaluator regenerates a canonical DEF and routing guide from `5_1_grt.odb`. It then checks:

- preservation of all non-HBT component placement and package pins;

- logical netlist equivalence after collapsing HBT connections;

- HBT legality;

- legality of global-routing guides (do not cross die).

## 5. Baseline Results

The following baseline results was completed on all eight public cases
with the supplied input package, a 6.4 um HBT pitch, the 3D GRT baseline, the
binary 3D detailed-route evaluator, and `droute_end_iter=2`
(initial routing plus two optimization iterations). TNS and WNS are setup
metrics reported by OpenSTA after extraction of the final routed database.

All eight rows were evaluated with the 3.0R/0.6fF HBT RC model.

| Case | HBTs / 30% Capacity | DRT-WL (um) | DRC | TNS (ns) | WNS (ns) |
|---|---:|---:|---:|---:|---:|
| `ariane133` | 4,025 / 7,300 | 5,678,764.46 | 15,276 | -3,590.99 | -1.58215 |
| `ariane136` | 4,046 / 7,300 | 5,667,695.84 | 15,964 | -733,522 | -33.9247 |
| `black_parrot` (`bp`) | 3,847 / 5,880 | 7,813,311.28 | 18,874 | -44,022.4 | -6.23185 |
| `bp_fe` | 1,149 / 1,729 | 1,378,685.12 | 4,257 | -2,697.39 | -1.35101 |
| `bp_be` | 1,105 / 2,176 | 2,368,525.41 | 8,099 | -1,526.59 | -1.4111 |
| `bp_multi` | 3,072 / 4,687 | 3,883,744.71 | 13,778 | -38,118.1 | -6.50626 |
| `swerv_wrapper` | 1,278 / 4,087 | 3,723,936.61 | 15,382 | -651.523 | -0.829661 |
| `bp_quad` | 27,835 / 45,630 | 41,694,313.23 | 23,862 | -547,096 | -27.9043 |
