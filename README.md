# 2026 EDA Elite Challenge: Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC

This repository provides the public code, benchmark interface, and baseline for the **2026 China Graduate IC Innovation Competition - EDA Elite Challenge**.

赛题中文名称：**时序驱动与 HB 布局协同的面对面键合 3D-IC 三维全局布线方法**

English title: **Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC**

## 1. Contest Description

Participants are required to jointly optimize metal layer sharing net selection and subnet assignment, incremental HBT placement, and timing-driven 3D global routing. The submitted algorithm must produce a routed OpenDB database containing the final global-routing guides, HBT placement, and net/subnet connectivity.

## 2. Quick Start

Pull the contest image and clone the `EDA_contest` branch:

```bash
docker pull gaocr/3dbench-contest:20260914

git clone --branch EDA_contest --single-branch \
  https://github.com/lamda-bbo/Open3DBench.git
cd Open3DBench
```

Extract the release bundle linked in Section 4, place its input archive in this
repository's `input/` directory, and unpack the input archive:

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

### MLS submission, version 11

Version 11 preserves the version 8 routing policy and its 13 native source
overlays, and optimizes six Python runtime files. It reduces allocations in DEF
classification, guide diagnostics, demand-grid clipping and site checks; HBT
search skips apply only to integer geometry proven to have no better HPWL point,
with actual path-guard searches and statistics preserved. Final ODB publication
uses a rename within the output filesystem after an independent reopen check.

The saved official submission scored **22.5366 (22.54 displayed), with 5/8 cases
successful**. A score of 25 remains unverified. Production tests (191), support
tests (7), and five comparisons against frozen old runtime source passed.
All eight cases have completed official local legality and artifact identity
comparisons, combining seven completed pairs from the first batch and a full
bp_quad retry; the first batch's overall FAIL is preserved. Explicit final DEF
export also passed an FE smoke with unchanged canonical output. Complete entry
comparisons use a shared host for functional
validation; no clean exclusive 32-thread runtime gain is established. On
official Python 3.12.3, standalone planner wall time decreased by 9.54%, 13.52%,
and 17.91% for bp, bp_multi, and bp_quad with all four outputs identical. These phase
measurements do not establish complete entry or official score gains.

The final supplementary `submission.def` export now defaults to disabled
(`SUBMISSION_EXPORT_DEF=0`). The required output remains `5_1_grt.odb`; the
independent `read_db` verification remains mandatory, and `route.guide` is still
written. The official evaluator regenerates canonical DEF/guides from the ODB.
Set `SUBMISSION_EXPORT_DEF=1` to export a final DEF from the reopened ODB.

See [submission instructions](submission/README.md),
[validation scope](submission/VALIDATION.md), and
[algorithm details](OpenROAD-GRT/ALGORITHM.md) for unchanged v8 settings and its
historical timing evidence. The reserve75 and zero-extra-iteration FE experiments have
mixed quality results and have not been adopted. The budget512 BP evaluator
record is complete: TNS -157898 ns, WNS -22.1521 ns, DRC 13379, detailed wirelength
7919728.98 μm and HBT count 4359. The subsequent retention driver exited 139;
the RAM container was removed and the archive and receipt are missing. The
independent quality audit is therefore **INCOMPLETE**, despite the completed
evaluation record. The recommended package keeps v8's `max_new_hbts=384`
and the six validated runtime changes; budget512 is not adopted. Reserve75 BP
returned -11 during GRT before DRT/STA. The three saved server
`Input DEF file not found` failures have no verified cause or fix.

```bash
python3 submission/package.py
bash submission/build.sh 32
bash submission/run.sh \
  "$INPUT/cases/bp_fe/grt_input" \
  output/bp_fe/mls_v11 \
  "$INPUT/platforms/nangate45_3D" 32
```

The source-only `submission.zip` has `run.sh` at its root. Build it in the official
image; a verified v8 binary is compatible only after source/build identity
checks. Full runtime comparisons exclude the preliminary build and fixed
evaluator, and do not predict the official normalized score.
Final release-package identity and documentation verification are governed by
the `status` and `final` fields in
`reports/optimization_v11/FINAL_INTEGRATION_AUDIT.json`.

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

### 3.3 HBT and subnet naming

Existing HBT instances keep names beginning with `HBT_`. New HBT instances introduced by Metal Layer Sharing must be named `LS_HBT_<id>`, where `<id>` uniquely identifies each HBT. Subnets derived from an original net must be named `<original_net>__MLS__S<id>__BOT` or `<original_net>__MLS__S<id>__TOP`; `<original_net>` is the exact original net name, and `S<id>` uniquely identifies each subnet derived from it.

## 4. Input and Output Files

Download the [release bundle from Google Drive](https://drive.google.com/file/d/1BvkJXGITgEXt2EHV_bVx3Fz9HOedyWXk/view?usp=sharing),
which includes the inputs, baseline source, and Docker image. After extracting
`Open3DBench-offline-20260915.tar.gz`, the input archive is located at:

```text
Open3DBench-offline-20260915/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724.tar.gz
```

The inputs use a 6.4 um HBT pitch, a 3.0 ohm HBT series resistance, and
0.6 fF total HBT capacitance.

Input archive SHA-256:
`d27c12edb98bbda2c250f879b46361bce5d1d574f69b9bb2aec68c6049f6af2b`

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

The table reports the existing eight-case baseline routes, produced with the
3D GRT baseline and two detailed-routing optimization iterations
(`droute_end_iter=2`). TNS and WNS are setup timing metrics re-evaluated from
these routed databases using the supplied evaluator and timing constraints.
All cases use a 6.4 um HBT pitch, 3.0 ohm resistance, and 0.6 fF total capacitance.

| Case | HBTs / 30% Capacity | DRT-WL (um) | DRC | TNS (ns) | WNS (ns) |
|---|---:|---:|---:|---:|---:|
| `ariane133` | 4,025 / 7,300 | 5,678,764.46 | 15,276 | -21,178.44 | -4.57280 |
| `ariane136` | 4,046 / 7,300 | 5,667,695.84 | 15,964 | -6,130,643.00 | -381.76276 |
| `black_parrot` (`bp`) | 3,847 / 5,880 | 7,813,311.28 | 18,874 | -186,047.55 | -20.44161 |
| `bp_fe` | 1,149 / 1,729 | 1,378,685.12 | 4,257 | -8,828.74 | -4.00944 |
| `bp_be` | 1,105 / 2,176 | 2,368,525.41 | 8,099 | -6,886.91 | -4.32408 |
| `bp_multi` | 3,072 / 4,687 | 3,883,744.71 | 13,778 | -90,280.86 | -15.93247 |
| `swerv_wrapper` | 1,278 / 4,087 | 3,723,936.61 | 15,382 | -1,873.56 | -1.55317 |
| `bp_quad` | 27,835 / 45,630 | 41,694,313.23 | 23,862 | -1,716,879.50 | -113.96867 |
