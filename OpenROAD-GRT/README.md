# 第十三版：直接复用准备后的数据库检查信息

本版以 v12 为基线，沿用 MLS/HBT、选层与容量策略。新原生接口从准备后的 OpenDB 导出分类与严格连通检查所需信息，省去中间 DEF 写入及重复解析；不支持的特殊 DEF 语法自动回退，错误或哈希不一致仍阻止发布。输入 master 扫描只读至 COMPONENTS 结束，输入摘要改为流式计算。

全八例新旧提交 ODB、guide、MLS 计划和官方 canonical DEF/guide/ODB 逐字节一致，官方合法性通过；222 项生产、7 项支持及 14 项验证器篡改/留存测试通过。13 次真实原生导出与原 DEF writer/parser 对照通过，并确认数据库未改动。NDR 与供电/地参考名称由只读 Tcl 兼容性检查保护，查询不可用时回退原 DEF 路径。记录见 `reports/optimization_v13/all8_final_validation/runtime_report.json`。

本地入口耗时来自共享宿主的 RAM 工作区，仅为观测；官方已知成绩仍为 23.00806162648646（23.01），尚未确认达到 25 分。预算 512/768 的时序实验与本推荐包分开保存，本包预算保持 384。

---

# 历史 v12 与更早记录

# 第十二版运行加速

本轮最终八例对照全部通过：每例新旧提交 ODB、source guide、MLS 计划及官方 canonical DEF/guide/ODB 均一致，官方合法性均通过。此结论来自本地官方容器；新官方分数仍未取得。

最新官方基线为 **23.01 分，5/8 成功**。本版保留全部原生覆盖层与物理策略，使用有界精确 guide 网格、等价连接分类，并让只读检查与 ODB 最终化重叠。至少 3 核且并行模式启用重叠；所有检查成功后才发布，独立 ODB 重开仍执行。

已通过 207 项生产与 7 项支持工具回归。全八例完整入口、官方合法性与产物身份以 `reports/optimization_v12/all8_final_validation/runtime_report.json` 为准。完整说明见仓库 `submission/README.md`、`submission/VALIDATION.md` 与本目录 `ALGORITHM.md`。新正式成绩尚未取得。

---

# 历史 v11 说明

# OpenROAD 3D GRT Baseline

The v11 submission keeps the v8 routing policy and all 13 native overlay files, and optimizes Python planning, classification, guide diagnostics and final ODB publication. See [submission instructions](../submission/README.md), [validation scope](../submission/VALIDATION.md) and [algorithm details](ALGORITHM.md).

The budget512 BP evaluator record is complete, with TNS -157898 ns, WNS -22.1521 ns, DRC 13379, detailed wirelength 7919728.98 μm and HBT count 4359. Its subsequent retention driver exited 139; the RAM container was removed and the final archive/receipt are missing, so the independent quality audit is **INCOMPLETE**. The recommended package retains v8's `max_new_hbts=384` and the six validated runtime changes. Budget512 is not adopted; reserve75 BP failed during GRT with -11 before DRT/STA. These records do not establish a new official score or a complete-entry runtime gain. Final release-package identity and documentation verification are governed by `reports/optimization_v11/FINAL_INTEGRATION_AUDIT.json`'s `status`/`final` fields.


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
