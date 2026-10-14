# 3D-IC 全局布线第十一版：保留 v8 策略的运行优化

本版沿用第八版的 HBT 重定位、MLS 共享规划、容量预留和长、高扇出普通网主干选层，优化六个 Python 运行文件。13 份原生 GRT 覆盖层与 v8 逐文件相同，未引入新的布线策略。

本次上传保存的官方记录为 **22.536600893681708 分（显示为 22.54）**，成功运行 5/8 个用例。**25 分尚未获得官方确认。** 已完成 191 项生产回归、7 项支持工具回归、5 项对固定 v8 源码的边界对照，以及八例本地官方合法性/产物一致性验证。八例结论合并首轮七个已完成对照和 bp_quad 完整重试，保留首轮整体 FAIL。完整入口对照仅作共享宿主功能验证，未获得干净独占的速度测量，详见 [VALIDATION.md](VALIDATION.md)。

## 构建与运行

在官方 `gaocr/3dbench-contest:20260914` 镜像内运行：

```bash
bash build.sh 32
bash run.sh <input_dir> <output_dir> <platform_dir> [threads=32]
```

输入目录必须含 `4_1_cts.def`、`4_cts.sdc`，线程数为 1–32。源码包包含 13 份覆盖层，从镜像 `/opt/contest/openroad-base` 完整构建；默认编译缓存为 `/tmp/open3dbench-grt-build-<uid>`，可用 `SUBMISSION_BUILD_DIR` 指定。v11 的原生源码和构建脚本沿用 v8；本轮本地验证仅在逐项核对构建来源和二进制 SHA 后复用已验证的 v8 二进制。提交包仍不携带二进制。`OPENROAD_EXE` 可指定经验证的兼容程序。

必需输出为 `5_1_grt.odb`。入口继续生成 `route.guide`、MLS 计划及运行清单，完成层归属、pin 覆盖、连通性检查，并使用独立 OpenROAD 进程 `read_db` 重开新 ODB；失败返回非零。重开通过后，ODB 从输出目录内部的临时工作目录原子重命名到最终路径，省去整个 ODB 的复制。原临时 `results/5_1_grt.odb` 因此不再保留；这只是单个 ODB 文件的原子发布，消费者仍须检查入口退出状态和运行清单。

默认 `SUBMISSION_EXPORT_DEF=0`，省去补充文件 `submission.def` 的最终导出和复制，保留 ODB 独立重开验证。官方评估器会从提交 ODB 生成 canonical DEF/guide。需要最终 DEF 时，可显式启用：

```bash
SUBMISSION_EXPORT_DEF=1 bash run.sh <input_dir> <output_dir> <platform_dir> 32
```

该 DEF 来自独立重开的最终 ODB，不能用准备阶段 DEF 代替；运行清单用布尔字段 `submission_export_def` 记录开关。仅接受 `0`、`1`。

本地仓库使用 `python3 submission/package.py` 同步生产源码并生成根目录 `submission.zip`。最终发布包身份与说明核验以仓库 `reports/optimization_v11/FINAL_INTEGRATION_AUDIT.json` 的 `status`/`final` 为准；上述构建流程针对完整源码包。包内不包含输入数据、二进制或实验产物。批量入口为：

```bash
python3 submission/run_public_cases.py <input_root> <output_root> --threads 32 --mode both
```

## v11 运行优化

| 文件（包内相对路径） | 改动 |
|---|---|
| `flow_scripts/scripts_3D/die_net_common.py` | 流式提供原始连接 tuple，公开 dataclass 接口保留。 |
| `flow_scripts/scripts_3D/export_die_net_lists.py` | 直接分类连接，减少对象构造，保留顺序、重复网语义和完整分类缓存。 |
| `flow_scripts/scripts_3D/diagnose_guide_connectivity.py` | 跳过当前未检查普通网矩形行的 token 分配，保留原严格诊断。 |
| `flow_scripts/scripts_3D/hbt_optimizer.py` | 只在整数几何已达精确最优或 HPWL 下界时跳过无收益搜索；实际路径 guard 仍完整搜索，保留拒绝统计。 |
| `flow_scripts/scripts_3D/mls_planner.py` | 减少需求网格边界裁剪和合法站点间距检查的临时对象。 |
| `src/run_router.py` | 可选最终 DEF 导出，保留独立 ODB 重开，以同文件系统原子重命名发布 ODB。 |

规划器在官方 Python 3.12.3 下对 bp、bp_multi、bp_quad 的计划 JSON、apply Tcl、选层 Tcl/JSON 四产物逐字节一致；前两例计划与上传保存版本一致，bp_quad 与 v8 历史产物一致。单独规划阶段耗时分别减少 9.54%、13.52%、17.91%。这些局部测量不能代替完整 `run.sh` 收益或正式评分。

## 沿用的策略与对照选项

M2 容量削减 70%、M3 削减 60%，其他当前 die 路由层削减 50%；全局拥塞迭代一次。最多共享 192 条网、增加 384 颗 HBT，多分支接收端路径保护继续启用。原生资源估计的取整与阻塞处理不变，物理 TRACKS、技术库、RCX 和固定评估器不变。

默认 `GRT_HIGH_FANOUT_LAYERS=1`、`GRT_HIGH_FANOUT_POLICY=layers`。对尚未被 MLS 替换、fanout ≥ 512、HPWL ≥ 400 μm 的普通网，底 die 主干使用 metal4–10，上 die 使用 metal11–17；最多 256 条，保留 pin access、时钟保护与 die 硬窗口。`GRT_HIGH_FANOUT_LAYERS=0` 关闭该策略，独立进程对照路径不应用此选层。

规划器继续复用本次已读取的清单生成选层文件；仅本次成功标记和路径匹配时复用，其他情况走原独立 CLI。`MLS_ENABLE=0` 关闭 MLS，`MLS_CONFIG` 指定参数，`GRT_LAYER_ADJUSTMENTS=''` 恢复统一容量。沿用 `MLS_PREPARE_SCAN=auto|native|tcl`、`MLS_MANIFEST_EXPORTER=tcl`、`GRT_METADATA_SNAPSHOT=all`、`GRT_LAYER_DISPATCH=legacy`、`GRT_PASS_RESET=legacy`、`GRT_PROCESS_MODE=isolated`、`GRT_INPUT_MODE=odb`、`GRT_CHECK_MODE=serial`、`GRT_SAVE_CHECKPOINTS=1` 对照选项。

本轮 reserve75 与零额外拥塞迭代候选的 FE 详细评测出现不同指标间的取舍，尚未采用。后者实验标签为 `zero_overflow`，实际设置 `-congestion_iterations 0`，不表示物理 overflow 为零。budget512 BP 官方评估记录已完成，保存 TNS -157898 ns、WNS -22.1521 ns、DRC 13379、详细线长 7919728.98 μm、HBT 4359；随后留存 driver 返回 139，RAM 容器退出并自动删除，归档和 receipt 缺失，严格独立质量审计为 **INCOMPLETE**。这些已记录指标不能替代缺失的最终产物独立复核，也没有其他用例的完整质量覆盖，因此不采用 budget512。主推荐包保留 v8 的 `max_new_hbts=384` 与已验证六文件运行优化。reserve75 BP 的 GRT 返回 -11，未进入 DRT/STA。完整历史时序证据和策略边界保留在 [ALGORITHM.md](ALGORITHM.md) 后文。

Runtime 取外部 `run.sh` 完整墙时，不含构建和评估器 DRT/RCX/STA。共享宿主验证只用于合法性与文件一致性，不证明速度收益；内部父子阶段和并行阶段不能重复相加。验证工具说明见 [support/README.md](support/README.md)。
