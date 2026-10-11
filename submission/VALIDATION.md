# 第八版验证记录

本版最终策略为原第七版 MLS 规划加长、高扇出普通网选层，组合精确运行加速。已完成最终源码的八例 GRT/官方合法性检查，以及 bp、bp_multi 的完整时序对照与产物身份绑定。**尚未获得第八版官方提交成绩，不能确认达到 25 分。**

## 环境与源码身份

- 官方镜像：`gaocr/3dbench-contest:20260914`，实际 ID `sha256:eb877c5e1f4d94881992b55d474ab189ab3308dac3f38208c5c8b0dd7544bd98`。
- 官方基础源码 commit：`305d3ba2ddfd00591924cc586ad408179f566afe`；本版 13 份覆盖层已完整构建，二进制 SHA256 为 `c8f664f33bb87b6174de743b155032e6edd278c0cd615374d4552b4de79c9e44`。
- 最终路由冻结源码 ZIP SHA256：`4f0082b1113bef5a31f4bfefe86de60b4526bb76076f10366415ffba60796f94`。发布包更新了说明及支持工具，运行文件须与该冻结版本相同；发布包本身的摘要保存在包外审计，避免文档自引用哈希。
- 最终路由：32 线程、jobs=1，复用与 13 份覆盖层完全匹配的已验证二进制。固定评估器、输入、SDC、平台及 RCX 均未修改。

## TNS、WNS 与质量取舍

以下是同镜像、同输入/完整平台摘要、同固定引擎、每次 12 线程的实际两轮 DRT、RCX 和最终 STA。两层日志均确认 `droute_end_iter=2`。基线重新测得的 bp/bp_multi 结果与保存的第七版官方指标一致。

| 用例 | 指标 | 第七版 | 第八版选定策略 |
|---|---|---:|---:|
| bp | TNS / ns | -164904 | -162678 |
| bp | WNS / ns | -22.2297 | -22.3057 |
| bp | DRC | 13784 | 13754 |
| bp | 详细线长 / μm | 7873312.12 | 7876304.96 |
| bp | HBT | 4231 | 4231 |
| bp_multi | TNS / ns | -83567.5 | -83525.9 |
| bp_multi | WNS / ns | -16.9927 | -16.651 |
| bp_multi | DRC | 4800 | 4887 |
| bp_multi | 详细线长 / μm | 3892767.95 | 3892501.57 |
| bp_multi | HBT | 3456 | 3456 |

bp 的 TNS 负 slack 损失减少 1.35%，但 WNS 损失增加 0.34%；bp_multi 的 TNS 损失减少 0.05%、WNS 损失减少 2.01%，但 DRC 增加 1.81%。两例超免费额度 HBT 均为 0。收益有限，不能表述为所有时序或物理指标均改善。

完整质量测量使用原规划器和独立选层流程；最终包改用等价的包围盒计算与融合选层流程，并采用新的 13 覆盖层二进制。独立审核固定了源码差分哈希，官方 Python 3.12 下八例的计划 JSON、apply Tcl、选层 Tcl/JSON 逐字节一致。最终 bp/bp_multi 的实际 MLS 计划、canonical DEF/guide/ODB 和提交 ODB 必须与该质量测量逐字节一致，才绑定上述指标。这不是宣称最终 ZIP 又重跑了一遍 STA，也不把其他用例标为已完成新时序测量。

本轮未完成 bp_quad 的完整新 DRT/STA；其选层会改变布线，最终时序仍有不确定性。几何代理、空选层或合法性通过均不能替代相应时序覆盖。

## 完整入口耗时

以下五例分别比较同 32 线程、jobs=1 的完整外部 `run.sh` 墙时，每版每例一次。基线与候选的输入、平台和固定引擎一致，启动预约没有其他活动实验；这不证明宿主不存在任何未登记负载。构建、局部 CLI、采样器和固定 DRT 时间均不计入。

| 用例 | 第七版 / s | 第八版 / s | 减少 |
|---|---:|---:|---:|
| bp_fe | 19.231 | 18.735 | 2.58% |
| bp_be | 29.578 | 28.592 | 3.33% |
| bp | 136.479 | 130.143 | 4.64% |
| bp_multi | 56.825 | 54.322 | 4.40% |
| swerv_wrapper | 44.402 | 42.883 | 3.42% |
| 合计 | 286.515 | 274.675 | 4.13% |

合计减少 11.840 秒（4.13%），不承诺其他机器获得同幅收益。其他三例没有本轮同条件入口对照；五例全部计时和合法性完成后才进行磁盘去重，随后三个用例的耗时不用于此比较。原生运行优化单独测得的 4.38% 和规划阶段的约 25% 不能与这里的完整入口收益相加。

## 八例合法性与回归

| 用例 | 最终 GRT / 官方合法性 | 实际应用选层网数 |
|---|---|---:|
| bp_fe | PASS | 0 |
| bp_be | PASS | 0 |
| bp | PASS | 59 |
| bp_multi | PASS | 14 |
| swerv_wrapper | PASS | 0 |
| ariane133 | PASS | 0 |
| ariane136 | PASS | 0 |
| bp_quad | PASS | 18 |

八例执行完整 guide 层归属、pin 覆盖、连通性检查与最终 ODB 重开。新规划未改变原共享预算和 HBT 布局策略。没有按 case 名称选择不同算法。

生产回归 **191 项通过**，支持工具 **7 项通过**；另有官方 Python 3.12 下 87 项针对性测试与八例四产物对照，属于交叉验证，不与生产测试简单累加。新增检查覆盖 bbox 的 NaN/正负零/空输入、MLS 原网排除先于排序预算、融合成功标记、旧文件、禁用/独立进程/外部准备回退及失败传播。原生解析和堆/网格差分验证通过 AddressSanitizer/UndefinedBehaviorSanitizer；没有宣称完成 LeakSanitizer 或降低峰值内存。

更细分组在 bp_multi 上同时恶化 TNS/WNS，未采用。新的叶 HBT 落点策略虽然改善部分 TNS，却改变排序与资源分配，使 bp_fe 的 TNS/WNS 和 bp 的 WNS 退步，最终也未采用。拒绝候选的产物已经逐文件解压校验后无损归档，源代码、日志与质量证据保留。

## 包外证据

以下目录均相对于仓库 `reports/optimization_v8`，不随源码 ZIP 携带大型实验数据：

- `FINAL_INTEGRATION_AUDIT.json`：最终源码、源码包、13 覆盖层构建、八例合法性和两个时序测量的严格产物绑定。
- `FINAL_RUNTIME_AUDIT.json`：上述五例完整入口、线程、输入与预约记录对照。
- `TRUNK512_BP_QUALITY_AUDIT.json`、`TRUNK512_MULTI_QUALITY_AUDIT.json`：完整固定评估测量及逐项退步/改善。
- `fused_hint_validation/independent_review.json` 与 `independent_binding_result.json`：固定源码差分、官方八例四产物及测试证据。
- `native_final_validation/binary_reference.json`：完整构建、原生/Tcl 清单及边界 fixture 对照；`RUNTIME_PARITY_AUDIT.json` 验证纯运行优化八例与 v7 的结果一致。
- `FINAL_PRODUCTION_TESTS.log`、`FINAL_SUPPORT_TESTS.log`：实际生产及工具回归。
- `final_trunk_all8_experiments/20261008T012342Z-6ba654e4`：最终版本实际运行快照；固定质量测量分别见 `trunk512_bp_experiments/20261007T155351Z-cec87dca` 和 `trunk512_multi_experiments/20261007T055040Z-6a5b4b20`。

用户本次报告的官方成绩约 20.6 分；本地保存的 `result/scoring_result-3` 则记录 21.6456 分及 5/8 成功，两者不能混作同一次测量。保存结果中三个 `Input DEF file not found` 的服务器错误缺少尝试路径和完整日志，其根因仍未证实；本地八例通过不等于已修复服务器输入问题。
