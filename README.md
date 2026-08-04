# 2026 EDA Elite Challenge: Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC

This repository provides the public code, benchmark interface, and baseline for the **2026 China Graduate IC Innovation Competition - EDA Elite Challenge**.

赛题中文名称：**时序驱动与 HB 布局协同的面对面键合 3D-IC 三维全局布线方法**

English title: **Timing-Driven 3D Global Routing with Hybrid Bonding Co-Optimization for Face-to-Face-Bonded 3D-IC**

## Quick Start

Install Docker, then pull the contest image and clone this branch. The dated
tag is recommended for reproducible experiments; `latest` points to the
current released evaluator.

```bash
docker pull gaocr/3dbench-contest:20260724

git clone --branch EDA_contest --single-branch \
  https://github.com/lamda-bbo/Open3DBench.git
cd Open3DBench
```

Download the public input archive from the link in Section 4, place it below
`input/`, and extract it:

```bash
mkdir -p input
tar -xzf \
  input/open3dbench_8cases_post_hbt_input_20260724_r3.tar.gz \
  -C input
test -f \
  input/open3dbench_8cases_post_hbt_input_20260724_r3/cases/bp_fe/grt_input/4_1_cts.def
```

### Start the Container

Start an interactive container from the repository root:

```bash
./start_contest_docker.sh
```

The current repository is mounted at `/workspace/Open3DBench`. Inside the
container, verify the source and evaluator revisions and incrementally compile
the public OpenROAD GRT baseline:

```bash
contest status
contest build 32
```

The first build compiles the complete public OpenROAD baseline. Later builds
only rebuild files affected by source changes under
`OpenROAD-GRT-HBT/openroad_src`.

The image contains the fixed DRT/DRC/STA evaluator as binaries only; its
private source is not included. The participant-modifiable GRT/HBT baseline
remains in this Git branch and is mounted into the container at runtime.

The wrapper above is equivalent to the following explicit Docker command:

```bash
mkdir -p .contest/home input output reports
docker run --rm -it \
  --init \
  --user "$(id -u):$(id -g)" \
  --ulimit stack=-1:-1 \
  -e HOME=/workspace/Open3DBench/.contest/home \
  -e CONTEST_ROOT=/workspace/Open3DBench \
  -v "$PWD:/workspace/Open3DBench" \
  -w /workspace/Open3DBench \
  gaocr/3dbench-contest:20260724 \
  shell
```

The same commands can be run directly from the host without opening an
interactive shell:

```bash
./start_contest_docker.sh status
./start_contest_docker.sh build 32
```

### Run the GRT Baseline

Run one case from inside the container:

```bash
INPUT=/workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724_r3
contest run-grt bp_fe "$INPUT" baseline
```

The submission is written to:

```text
output/bp_fe/baseline/
├── 5_1_grt.odb
├── die_net_lists/
├── route.guide
└── submission.env
```

### Run the DRT, DRC, and Timing Evaluator

The fixed evaluator runs detailed routing, unified DRC, RC extraction, and
OpenSTA timing analysis as one atomic command:

```bash
INPUT=/workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724_r3
contest evaluate \
  bp_fe \
  "$INPUT" \
  /workspace/Open3DBench/output/bp_fe/baseline \
  /workspace/Open3DBench/reports/bp_fe/baseline
```

The equivalent host-side command is:

```bash
./start_contest_docker.sh evaluate \
  bp_fe \
  /workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724_r3 \
  /workspace/Open3DBench/output/bp_fe/baseline \
  /workspace/Open3DBench/reports/bp_fe/baseline
```

DRT wirelength and DRC are reported in `metrics.json`,
`wirelength.rpt`, and `5_route_drc.rpt`. TNS and WNS are reported in
`metrics.json`, with the complete timing report in `6_report.log` and the
machine-readable OpenROAD metrics in `6_report.json`:

```bash
cat reports/bp_fe/baseline/metrics.json
```

DRT and timing are intentionally evaluated together. A standalone timing
command that accepts a participant-modifiable post-DRT database is not
provided, because modifying that intermediate database would invalidate the
fixed-evaluator scoring contract.

### Run All Eight Cases

The following host-side commands compile once, run all GRT baselines, and then
evaluate all submissions sequentially:

```bash
set -euo pipefail

INPUT=/workspace/Open3DBench/input/open3dbench_8cases_post_hbt_input_20260724_r3
VARIANT=baseline
CASES=(
  ariane133
  ariane136
  bp
  bp_fe
  bp_be
  bp_multi
  swerv_wrapper
  bp_quad
)

./start_contest_docker.sh build 32

mkdir -p runlogs
for case_name in "${CASES[@]}"; do
  ./start_contest_docker.sh \
    run-grt "$case_name" "$INPUT" "$VARIANT" \
    2>&1 | tee "runlogs/${case_name}_grt.log"
done

for case_name in "${CASES[@]}"; do
  ./start_contest_docker.sh evaluate \
    "$case_name" \
    "$INPUT" \
    "/workspace/Open3DBench/output/${case_name}/${VARIANT}" \
    "/workspace/Open3DBench/reports/${case_name}/${VARIANT}" \
    2>&1 | tee "runlogs/${case_name}_evaluate.log"
done
```

`bp` is the BlackParrot case. `bp_quad` has the largest memory and runtime
requirements and is therefore placed last.

Public source, build files, and caches are stored under `.contest/`. GRT
outputs are written below `output/`, while evaluator metrics are written below
`reports/`. These generated directories are ignored by Git.

## 1. Contest Description

The contest asks participants to co-optimize Metal Layer Sharing net selection and subnet assignment, incremental HBT placement, and timing-driven 3D global routing. The submitted algorithm must produce a routed OpenDB database containing the resulting guides, HBT placement, and net/subnet connectivity.

## 2. Repository and Baseline

```text
Open3DBench/
├── OpenROAD-GRT-HBT/   # Modified OpenROAD with 3D GRT and HBT placement
│   ├── openroad_src/   # Source code for OpenROAD src/grt
│   └── flow_scripts/   # GRT and HBT scripts
├── OpenROAD-3D/        # OpenROAD-based 3D backend flow
├── Place-MoL/          # Memory-on-Logic placement flow
└── Place-LoL/
```

The supplied baseline could be the starting point for contest development, which does not introduce additional Metal Layer Sharing nets.

### 2.1 Source-Level GRT Changes

The provided OpenROAD source adds a per-net routing-layer range to `GlobalRouter` and propagates it into FastRoute. The allowed layer range is enforced during topology generation, resource accounting, maze expansion, and route reconstruction, so a die-local net cannot move to the opposite die as a congestion fallback. HBT pins are retained as real routing terminals that can be naturally processed by the router.

### 2.2 Die-by-Die Multi-Pass Baseline

1. Classify the input net into bottom-die and top-die subnets.
2. Route bottom-die subnets on `metal1-metal10` and top-die subnets on `metal11-metal20` in isolated OpenROAD processes.
3. Merge the two standard guide results and import them into the final `5_1_grt.odb`.

## 4. Input and Output Files

Input package download:

> [Download the public input package from Google Drive](https://drive.google.com/file/d/1o4ExxQX9lBswf4VWYGUsLMqjWBKLCTW6/view?usp=share_link)

Expected archive: `open3dbench_8cases_post_hbt_input_20260724_r3.tar.gz`

SHA-256:
`681d3f041c389097db348e622e21eea0b043c43a14bf6e5648b9316fbb473005`

Revision r3 preserves the r2 contents while correcting the post-CTS
per-die legalization of `bp_quad`; HBT coordinates and net connectivity are
unchanged.

```text
open3dbench_8cases_post_hbt_input_20260724_r3/
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
| `platforms/nangate45_3D/setRC.tcl` and `rcx_patterns.rules` | Wire/via resistance-capacitance settings and extraction rules used for timing evaluation. |
| `platforms/nangate45_3D/fastroute.tcl`, `make_tracks.tcl`, and `grid_strategy*.tcl` | Default routing-layer adjustments, routing-track definitions, and power-grid settings. |
| `platforms/nangate45_3D/gds/`, `cdl/`, and `drc/` | Layout geometry, transistor-level connectivity, and physical-verification rule files. |
The input DEF provides a reproducible baseline state. Contest algorithms may change HBT placement and subnet connectivity as part of the required co-optimization, but must preserve all non-HBT component placement.

### 4.3 Required Output

| File | Information contained in the file |
|---|---|
| `5_1_grt.odb` | Final OpenDB database containing component placement, optimized HBT placement, net/subnet connectivity, and global-routing guides. |
| `route.guide` | Text representation of the global-routing guide rectangles and their routing layers. |

## 5. Baseline Results

The following clean-machine baseline was completed on all eight public cases
with input revision r3, a 5.0 um HBT pitch, the 3D GRT baseline, the binary 3D
detailed-route evaluator, 32 DRT threads, and `droute_end_iter=2` (initial
routing plus two optimization iterations). Runtime is sequential wall-clock
time for GRT plus the complete evaluator, including DRT, unified DRC, RC
extraction, and final reporting, rounded to the nearest second. TNS and WNS are
setup metrics reported by OpenSTA after extraction of the final routed
database.

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
