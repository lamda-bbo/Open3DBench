# 2026 EDA Elite Challenge: Timing-Driven 3D Global Routing with HB Co-Optimization

This repository is the contest code package for the **2026 China Graduate IC Innovation Competition - EDA Elite Challenge**.

赛题中文名称：**时序驱动与 HB 布局协同的面对面键合 3D-IC 三维全局布线方法**

English title: **Timing-Driven 3D Global Routing with HB Co-Optimization for Face-to-Face-Bonded 3D-IC**


## 1. Contest Overview / 赛题简介


Face-to-face-bonded 3D ICs use Hybrid Bonding Terminals (HBTs) to connect two stacked dies. Compared with conventional 2D routing, this creates a new optimization opportunity: selected nets may share routing resources across the two dies through HBTs, reducing congestion on the over-utilized die and exploiting under-used metal resources on the other die.

The goal of this contest is to design a timing-driven 3D global-routing algorithm with coordinated metal-layer sharing, cross-die net splitting, HBT placement, and 3D routing planning. Contestants should build on the provided Open3DBench-based baseline, improve the HBT placement and global-routing strategy, and output legal OpenROAD/FastRoute route guides together with updated HBT placement and split-net connectivity. The final evaluator will run detailed routing and DRC checking with TritonRoute, and timing analysis with OpenSTA. 

面对面键合 3D-IC 通过混合键合端子（Hybrid Bonding Terminal, HBT）实现上下 die 之间的垂直互连。与传统二维布线相比，3D-IC 提供了新的优化空间：部分线网可以通过 HBT 借用相邻 die 的金属层资源，从而缓解单个 die 的局部拥塞，并提升上下 die 间布线资源的整体利用率。

本赛题要求参赛者设计一种时序驱动的 3D 全局布线算法，协同优化金属层共享线网选择、跨 die 线网切分、HBT 布局以及 3D 布线路径规划。参赛者应基于本仓库提供的 Open3DBench baseline，在 HBT 放置和 GRT 流程上进行改进，输出符合 OpenROAD/FastRoute 标准的 `.guide` 文件，以及更新后的 HBT 布局和跨 die 线网切分结果。最终评估器将使用 TritonRoute 完成详细布线和 DRC 检查，并调用 OpenSTA 完成 3D 时序分析。

## 2. Repository Layout

```text
Open3DBench/
├── OpenROAD-GRT-HBT/   # Public OpenROAD GRT/HBT baseline patch
│   ├── openroad_src/   # Source overlay for OpenROAD src/grt
│   └── flow_scripts/   # OpenROAD-3D flow scripts for HBT and GRT
├── OpenROAD-3D/        # Backend flow interface and evaluation harness
├── Place-MoL/          # Memory-on-logic placement flow
└── Place-LoL/          # Logic-on-logic conversion and placement utilities
```

The public package exposes the baseline GRT and HBT algorithm code together with the flow interface used by the contest benchmarks.

## 3. Baseline GRT Algorithm

The baseline global router follows a die-by-die routing philosophy for the NanGate45_3D stack. Instead of treating the stacked design as a flat routing problem, it separates routing intent according to die ownership: bottom-die 2D nets should mainly use bottom-die routing resources, top-die 2D nets should mainly use top-die routing resources, and cross-die connectivity should pass through HBT access points.

### 3.1 Source-Level Idea

At the algorithm level, the baseline makes global routing aware of each net's preferred die and routing-layer range. The goal is to guide ordinary 2D nets toward die-local resources while preserving explicit accessibility for HBT-related nets.

For die-local 2D nets, the router avoids creating guides on the opposite die. For HBT-related nets, the router keeps the HBT boundary reachable so detailed routing can later connect the corresponding bottom/top segments.

### 3.2 Multi-Pass Idea

The baseline runs GRT in multiple logical passes. A bottom pass handles bottom-die nets, a top pass handles top-die nets, and HBT or cross-die connectivity is preserved through shared boundary anchors.

This makes congestion and layer availability easier to control than an unrestricted flat pass, while still producing one merged guide file for the downstream flow.

### 3.3 Post-Processing Idea

After routing, guide finalization keeps the merged route guide consistent with die ownership. Bottom guides remain on bottom resources, top guides remain on top resources, and HBT access guides are retained around the die boundary. This step is intended as a consistency layer around the algorithm output rather than a replacement for routing optimization.

## 4. Baseline HBT Algorithm

The baseline HBT algorithm provides a simple reference strategy for vertical connectivity. It identifies nets that may benefit from cross-die routing, assigns HBT locations according to the geometric distribution of those nets, and rewrites the affected connectivity so each die-local segment can be routed mostly within its own die and joined through the HBT.

This baseline prioritizes reproducibility and simplicity over optimality. Contestants are expected to improve metal-layer sharing net selection, HBT placement, and timing/congestion-aware 3D global-routing strategy.

## 5. Input Files

Input package download:

> [Download the public input package from Google Drive](https://drive.google.com/file/d/1o4ExxQX9lBswf4VWYGUsLMqjWBKLCTW6/view?usp=share_link)

The input package contains eight public cases and the NanGate45_3D platform files required by the HBT placement and GRT stages. Its directory layout is:

```text
open3dbench_8cases_input_20260713/
├── cases/
│   ├── ariane133/
│   ├── ariane136/
│   ├── bp/
│   ├── bp_be/
│   ├── bp_fe/
│   ├── bp_multi/
│   ├── bp_quad/
│   └── swerv_wrapper/
└── platforms/
    └── nangate45_3D/
```

Each case directory contains:

| Path | Description |
|---|---|
| `cases/<case>/grt_input/4_1_cts.pre_hbt.def` | Post-CTS DEF before baseline HBT insertion. This is the recommended starting point for contestant HBT placement and net splitting. |
| `cases/<case>/grt_input/4_1_cts.def` | Baseline HBT-inserted DEF used by the provided reference flow. Contestants may use it as a reference or baseline comparison. |
| `cases/<case>/grt_input/1_synth.sdc` | Timing constraint file copied into the GRT-stage run directory. |
| `cases/<case>/flow_design/config*.mk` | OpenROAD-3D flow configuration files for the benchmark. |
| `cases/<case>/flow_design/*.sdc` | Original design SDC file used by the flow configuration. |
| `cases/<case>/flow_design/macros.v` | Macro wrapper definitions when required by the case. |
| `cases/<case>/flow_design/share_nets.txt` | Baseline metal-layer-sharing net list when available. |
| `cases/<case>/flow_design/fastroute.tcl` | Case-specific FastRoute settings when available. |
| `cases/<case>/flow_design/*.v` | Extra design source or wrapper files for cases that require them, such as `bp_quad`. |

The platform directory contains:

| Path | Description |
|---|---|
| `platforms/nangate45_3D/config.mk` | NanGate45_3D platform configuration referenced by the case configs. |
| `platforms/nangate45_3D/lef*` | Technology, standard-cell, macro, bottom-die, and top-die LEF files. |
| `platforms/nangate45_3D/lib*` | Timing libraries for normal, bottom-die, and top-die views. |
| `platforms/nangate45_3D/gds`, `cdl`, `drc` | Physical verification collateral included with the platform. |
| `platforms/nangate45_3D/*.tcl`, `*.rules`, `*.cfg` | Flow support files such as routing, RC, tapcell, and track-generation settings. |

The public case names in the package are:

```text
ariane133
ariane136
bp
bp_be
bp_fe
bp_multi
bp_quad
swerv_wrapper
```

Contestant HBT placement and net splitting should be reflected in the DEF passed to GRT. Fixed cell and macro placement should remain unchanged except for allowed HBT insertion, removal, or relocation.

## 6. Baseline Results

The table below reports public baseline runs using the provided GRT baseline. Runtime is end-to-end wall runtime for the evaluated HBT + GRT + DRT flow.

| Case | Status | Runtime | DRT-WL | DRC |
|---|---:|---:|---:|---:|
| `ariane133` | done | 5:22:47 | 5,690,813 | 82,274 |
| `ariane136` | done | 4:42:36 | 5,677,655 | 89,452 |
| `bp_fe` | done | 0:28:35 | 1,287,086 | 17,396 |
| `bp_be` | done | 1:03:34 | 2,338,762 | 36,547 |
| `swerv_wrapper` | done | 2:18:29 | 3,805,093 | 77,207 |
| `bp_multi` | done | 2:34:54 | 3,872,559 | 58,055 |

(To be completed)
