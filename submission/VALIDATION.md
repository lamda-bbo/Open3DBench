# 第十三版：直接复用准备后的数据库检查信息

本版以 v12 为基线，沿用 MLS/HBT、选层与容量策略。新原生接口从准备后的 OpenDB 导出分类与严格连通检查所需信息，省去中间 DEF 写入及重复解析；不支持的特殊 DEF 语法自动回退，错误或哈希不一致仍阻止发布。输入 master 扫描只读至 COMPONENTS 结束，输入摘要改为流式计算。

全八例新旧提交 ODB、guide、MLS 计划和官方 canonical DEF/guide/ODB 逐字节一致，官方合法性通过；222 项生产、7 项支持及 14 项验证器篡改/留存测试通过。13 次真实原生导出与原 DEF writer/parser 对照通过，并确认数据库未改动。NDR 与供电/地参考名称由只读 Tcl 兼容性检查保护，查询不可用时回退原 DEF 路径。记录见 `reports/optimization_v13/all8_final_validation/runtime_report.json`。

本地入口耗时来自共享宿主的 RAM 工作区，仅为观测；官方已知成绩仍为 23.00806162648646（23.01），尚未确认达到 25 分。预算 512/768 的时序实验与本推荐包分开保存，本包预算保持 384。

---

# 历史 v12 与更早记录

# 第十二版验证范围

本轮最终八例对照全部通过：每例新旧提交 ODB、source guide、MLS 计划及官方 canonical DEF/guide/ODB 均一致，官方合法性均通过。此结论来自本地官方容器；新官方分数仍未取得。

基线是 `submission_v11.zip`，对应 `result/scoring_result-5/detailed_scores.json` 的官方 23.00806162648646 分。最终可执行源码冻结于 `reports/optimization_v12/final_validation_candidate.zip`；原生 13 文件与已验证 v8 二进制来源逐文件相同。

生产回归 207 项、支持工具回归 7 项通过。专项对照确认：历史 BP 8123 条完整连通诊断不变；最新五例 guide 的连通分量 ID 不变；BP 338543 条分类记录、pin 数、分类顺序及缓存 payload 不变。全量入口与官方 canonical 合法性对照的最终状态见 `reports/optimization_v12/all8_final_validation/runtime_report.json`。

验证使用固定官方镜像、公开输入和已验证公开 GRT 二进制，以冻结 v11 为基线逐例交替运行。核对独立 ODB 重开、提交 ODB、source guide、MLS 计划/清单、apply Tcl、die lists，以及官方 canonical DEF/guide/ODB 的 SHA-256。

本次使用 RAM 工作区。宿主仍保留旧实验的两个阻塞 Python 读取进程，启动时没有竞争的 EDA worker；因此报告按 `shared_host_functional_identity_only` 保存，仅把各次完整入口耗时视为本轮观测，不宣称干净独占的速度收益，也不推算官方分数。没有新执行 DRT/RCX/STA；只有最终物理和 canonical 产物与 v11 相同的用例才能继承既有质量输入身份。

第一次 `all8_validation` 在冻结后发现最后一项合并失败清理尚未纳入，已停止并标为 superseded，结果不用于最终验收。以 `all8_final_validation` 为准。发布源码的执行文件必须与该冻结包逐字节一致；文档变更单独核对。

并行失败边界由真实 Tcl 执行测试覆盖：两项验证失败、连通性独立失败、read_guides/write_db 失败、同时失败、零退出但 stderr、长报告、串行/少核心回退、合并失败与旧产物清理。独立源码复核未发现剩余问题。

---

# 历史 v11 验证记录

# 第十一版验证记录

本版保留 v8 物理策略，只优化六个 Python 运行文件。13 份原生覆盖层与 v8 相同。本次保存的官方打榜记录为 **22.536600893681708 分（约 22.54）**；v11 尚无新的官方成绩，**不能确认达到 25 分**。

## 已知官方结果与服务器失败

证据为仓库 `result/scoring_result-4/scores.json`、`detailed_scores.json` 和 `result/prediction_result-4/ingestion_results.json`。本次记录成功 5/8：bp_fe、bp_be、bp、bp_multi、swerv_wrapper。保存指标为运行时间合计 162.138508 秒、平均 TNS -52247.738 ns、平均 WNS -9.525286 ns。

运行时间来自五个成功用例的 `algorithm_runtime` 之和，不包含固定评估器 DRT 时间。TNS/WNS 为这些成功用例的均值；不能将成功率用于反推八例分数。报告公开了权重，但未给出完整服务器归一化和失败用例处理规则，不能把节省秒数或局部百分比直接换算成达到 25 分所需的分数。

ariane133、ariane136、bp_quad 仍记录 `Input DEF file not found`。缺少服务器尝试路径、完整调用和日志，根因未证实，v11 未改输入发现逻辑。本地完整输入上的合法性或八例通过，均不等于已经修复这三个服务器问题。

## 源码、镜像与二进制身份

- 官方镜像 `gaocr/3dbench-contest:20260914`，ID `sha256:eb877c5e1f4d94881992b55d474ab189ab3308dac3f38208c5c8b0dd7544bd98`。
- 基础源码 commit `305d3ba2ddfd00591924cc586ad408179f566afe`；复用的已验证 v8 二进制 SHA256 `c8f664f33bb87b6174de743b155032e6edd278c0cd615374d4552b4de79c9e44`。验证同时绑定原生 13 文件、构建脚本、fresh-build 证明和原始构建 ZIP。
- 本轮对照基线 `submission_v8.zip` SHA256 `d976df3ba142e4316c58c3d147ecf67800ac85edcc45a7305bf96e36fee347de`。
- 冻结运行候选 `reports/optimization_v11/final_runtime_candidate.zip` SHA256 `e76665731f27efb67e05a1488b57a95759ad7515921c1bf6c3da904e6fdf0ddf`。此摘要对应评测候选，后续说明文档和支持工具更新后的发布包摘要须另行审计。
- 六份改动为 `src/run_router.py` 以及 `flow_scripts/scripts_3D/{die_net_common,export_die_net_lists,diagnose_guide_connectivity,hbt_optimizer,mls_planner}.py`。原生覆盖层逐文件不变；不得据此宣称所有包文件均未变，冻结候选还未携带一份支持工具测试文件。

## 已完成的回归与局部对照

生产回归 **191 项通过**，支持工具回归 **7 项通过**；另有 **5 项**对固定 `production_before_v11` 源码的运行边界对照通过。证据分别为 `FINAL_PRODUCTION_TESTS.log`、`FINAL_SUPPORT_TESTS.log`、`FINAL_RUNTIME_BOUNDARY_TESTS.log`，位于仓库 `reports/optimization_v11`。固定旧源码对照避免新实现与自身比较。

已有官方 Python 3.12.3 下 bp、bp_multi、bp_quad 的规划器对照：计划 JSON、apply Tcl、选层 Tcl/JSON 四产物逐字节一致。bp、bp_multi 的计划还与本次上传保存的计划一致；bp_quad 与保留的 v8 历史计划一致。HBT 剪枝仅对可证明无收益的整数几何启用，有实际路径 guard 时保留完整候选搜索和拒绝计数；非整数几何保留原搜索。间距判定、网格裁剪顺序和候选排序保持原语义。

| 单独规划器 CLI | v8 / s | v11 / s | 本阶段减少 |
|---|---:|---:|---:|
| bp | 13.564 | 12.269 | 9.54% |
| bp_multi | 6.561 | 5.674 | 13.52% |
| bp_quad | 55.081 | 45.214 | 17.91% |

这些是官方 Python 3.12.3 下的局部重放，四份输出逐字节相同。每版本每例测量一次；不能据此推算完整入口或服务器分数。证据为 `planner_validation/container/REPLAY.json` 和 `bp_quad_planner_replay/REPLAY.json`。

入口 fixture 对照覆盖新 ODB 独立重开、缺失/空产物、失败标记、导出失败、原子重命名失败及后续复制失败传播。默认 `SUBMISSION_EXPORT_DEF=0` 时最终 DEF 缺席；值为 `1` 时从独立重开的最终 ODB 导出。无效值失败。文件原子重命名保留新 ODB 字节，但不构成全部输出的原子事务，消费者须服从入口退出状态。

早期仅运行四文件候选的 FE 官方 smoke 已合法且 ODB 可读，不能用它替代最终六文件候选的八例验证。独立审核见 `FINAL_CANDIDATE_REVIEW.json`；局部规划、分类、连通性测量见 `planner_validation` 和 `RUNTIME_CANDIDATE_EVIDENCE.json`，这些测量不能当作完整入口收益。

## 八例合法性与产物身份

最终六文件候选已与 v8 完成下列八例完整入口、独立数据库重开及官方合法性对照。第一轮 `runtime_all8_functional/runtime_report.json` 的整体状态仍为 **FAIL**：前七例已完成，bp_quad 候选 GRT 返回 -11，未保留充分内部诊断，不能确定原因。随后用同一冻结候选 ZIP、镜像、输入和已验证二进制进行 bp_quad 完整重试，两版均合法且产物一致；`runtime_quad_retry/runtime_report.json` 为 **PASS**。合并结论只采用各例已完成的对照，不改写第一轮失败记录。

| 用例 | v11 GRT / 官方合法性 | v8→v11 物理与 canonical 文件身份 |
|---|---|---|
| bp_fe | PASS | 相同 |
| bp_be | PASS | 相同 |
| bp | PASS | 相同 |
| bp_multi | PASS | 相同 |
| swerv_wrapper | PASS | 相同 |
| ariane133 | PASS | 相同 |
| ariane136 | PASS | 相同 |
| bp_quad（完整重试） | PASS | 相同 |

验证要求提交 ODB、源 guide、计划 JSON、apply Tcl、MLS 清单及 die lists 的 SHA 一致，并比较官方从 ODB 重建的 canonical DEF/guide/ODB 与 canonical die lists。官方校验前后 canonical 三文件 SHA 必须不变，源 ODB 与输入也必须不变。运行使用固定镜像、输入、完整平台和已验证二进制，按 case 顺序交替 baseline/candidate。

上述对照均使用共享宿主、8 线程；首轮与已记录的 24 线程后台任务共存，重试与 12 线程 BP 时序实验共存，总预约不超过 32。报告 `runtime_scope=shared_host_functional_identity_only`，不计算入口速度比例或减少百分比。首轮因失败未完成整轮结束门槛，重试额外完成源码前后身份核对；两轮所需输入、完整平台、冻结源码和保留产物还由最终整合审计独立重哈希。

重试同时完成 `SUBMISSION_EXPORT_DEF=1` 的 FE smoke：官方合法，source/canonical/物理计划与第一轮默认不导出 DEF 的 FE 候选相同。默认候选没有最终 DEF 导出指令，独立 `read_db` 检查仍执行；显式开关通过最终 ODB 导出，未使用准备阶段 DEF 替代。

## 完整入口运行时间的验证范围

本轮未获得干净独占宿主、32 线程的完整入口计时。完整入口对照使用 8 线程，并与已记录的时序实验共享宿主；只用于验证产物和合法性，不报告速度收益。完整外部 `bash run.sh` 的原始墙时保留在运行报告中，构建、官方 snapshot/validator、哈希、归档和 DRT/RCX/STA 不计入该墙时。

reserve75 BP 失败后的两个临时文件读取进程处于内核存储等待，一次有界停止请求超时，未确认容器退出。它们不再运行 EDA，也不占用布线线程预约，但不能据此把宿主标为干净。证据为 `reserve75_bp_quality/20261011T074951Z-52606e8a/BLOCKED_RETENTION.json`；该失败实验的完整 RAM 归档未完成，小日志和已保存的审计仍保留。独占计时启动器会拒绝这个未解除的状态。

使用 `/scratch` tmpfs 缓解本地磁盘容量限制，TMPFS 的绝对墙时不能直接预测服务器文件系统。内部 `grt.prepare` 包含 `mls.*`，并行检查子项重叠；局部优化百分比不能相加，历史 v7→v8 完整入口减少 4.13% 也不是本轮 v8→v11 收益。

## 本轮质量研究：尚未采用

reserve75 FE 的 TNS 变差，WNS/DRC 改善；零额外拥塞迭代 FE 候选的 TNS/DRC 变差，WNS 改善，未纳入本版默认策略。后者实验标签为 `zero_overflow`，实际设置 `-congestion_iterations 0`，不表示物理 overflow 为零。reserve75 BP 的 GRT 返回 -11，未进入 DRT/STA。

budget512 BP 的官方实验记录已完成：12 线程、两轮固定详细布线、RCX 和最终 STA，评估器返回 0。保存指标如下；它们来自完整评估记录，而非中途 STA：

| 指标 | budget512 BP 已记录值 |
|---|---:|
| TNS / ns | -157898 |
| WNS / ns | -22.1521 |
| DRC | 13379 |
| 详细线长 / μm | 7919728.98 |
| HBT | 4359 |

完成后的留存 driver 返回 139，RAM 容器退出并自动删除，最终 archive 和 receipt 缺失；严格独立质量审计为 **INCOMPLETE**。记录中的 SHA 不能替代读取、重哈希缺失的最终 physical/STA/platform 产物。证据为 `budget512_bp_quality/20261011T074618Z-835d97cd/experiment.json`、`host_experiment.json` 和 `timing_candidate/BUDGET512_BP_QUALITY_AUDIT.json`；后者标明 `INCOMPLETE_INDEPENDENT_QUALITY_AUDIT_RETENTION_FAILED`。同为 12 线程的历史 v8 BP 基线已独立审计，但新候选最终归档尚未独立验证，其他用例也没有完整质量覆盖。

保存数值相较 v8 BP 显示 TNS/WNS/DRC 改善、详细线长和 HBT 增加，但不能据此把 budget512 宣称为已验证质量升级。本版不采用该候选，主推荐包维持 v8 的 `max_new_hbts=384` 与已验证六文件运行优化。容量模型中的 GRT overflow 减少不能代替最终 DRC、RCX、TNS/WNS；本次 BP 评估也不产生新的官方八例分数或公平入口计时。相应隔离实验位于 `reserve75_fe_quality`、`zero_fe_quality_retry`、`budget512_bp_quality`、`reserve75_bp_quality`。

## 沿用的 v8 时序证据

以下是既有 v7→v8 质量测量，不是 v11 新跑 STA：相同官方镜像、输入与完整平台、固定引擎、12 线程，两轮 DRT 后完成 RCX 和最终 STA。最终 v8 的严格产物身份绑定见仓库 `reports/optimization_v8/FINAL_INTEGRATION_AUDIT.json`。

| 用例 | 指标 | v7 | v8 策略 |
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

bp TNS 损失减少 1.35%，WNS 损失增加 0.34%；bp_multi TNS 损失减少 0.05%、WNS 损失减少 2.01%，DRC 增加 1.81%。HBT 数不变，两例超免费额度 HBT 为 0。完整历史策略、拒绝候选、RC 模型边界和测量范围保留在 [ALGORITHM.md](ALGORITHM.md) 后文及 v8 包外证据。

v11 只有在实际提交/物理计划/canonical 输出与 v8 严格相同时才能继承该质量输入身份；合法性通过本身不构成时序改善证据。既有 v8 未完成 bp_quad 的完整新 DRT/STA，本轮也不将其标为有新增时序覆盖。

## 包外证据

仓库 `reports/optimization_v11` 保留 `FINAL_RUNTIME_SOURCE.json`、`FINAL_CANDIDATE_REVIEW.json`、三份最终测试日志、`planner_validation/container/REPLAY.json`、`RAM_RUNNER_RELEASE.json` 和实际验证报告。源码 ZIP 不携带大型实验产物。

八例合并对照和显式 DEF 导出 FE smoke 已完成，中间整合审计 `FINAL_INTEGRATION_AUDIT.intermediate.json` 对运行来源、实际保留文件、三例规划重放、最终回归及原始评分均通过；它的发布包组因当时根目录 ZIP 尚为旧版而失败，文档组显式跳过，不能把中间审核标为完成。最终发布包身份与说明核验以 `reports/optimization_v11/FINAL_INTEGRATION_AUDIT.json` 的 `status`/`final` 为准。本轮没有干净独占计时收益；新的服务器成绩尚未取得，不能以本地对照替代。
