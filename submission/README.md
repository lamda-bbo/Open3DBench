# 3D-IC 全局绕线第八版提交

本版保留第七版的连接规划，为长、高扇出普通网络启用主干选层，并加速路由搜索、guide 处理及规划清单读取。优化规则统一应用于全部输入，不按用例名或指定网络分支。

相同官方容器、12 线程、固定两轮详细布线及完整 RCX/STA 对照：

| 用例 | TNS（ns，v7 → v8 策略） | WNS（ns，v7 → v8 策略） | DRC |
|---|---:|---:|---:|
| bp | -164904 → -162678 | -22.2297 → -22.3057 | 13784 → 13754 |
| bp_multi | -83567.5 → -83525.9 | -16.9927 → -16.6510 | 4800 → 4887 |

bp 的 TNS 改善 1.35%，但 WNS 恶化 0.34%；bp_multi 的 WNS 改善 2.01%，但 DRC 增加 1.81%。两例 HBT 数不变。时序不是每个指标都改善，25 分仍需官方提交验证。最终源码与这些测量之间的产物身份、八例检查及完整入口计时见 [VALIDATION.md](VALIDATION.md)。

最终五例同 32 线程完整入口合计 **286.515 → 274.675 秒，减少 4.13%**；八例 GRT/官方合法性均通过，生产与支持工具共 198 项回归通过。完整新时序对照覆盖上表两例。

## 构建与运行

在官方镜像内运行：

```bash
bash build.sh 32
bash run.sh <input_dir> <output_dir> <platform_dir> [threads=32]
```

输入目录需含 `4_1_cts.def`、`4_cts.sdc`，线程数为 1–32。提交包包含 13 份 GRT 源码覆盖层及运行脚本，从镜像 `/opt/contest/openroad-base` 完整构建。编译缓存默认位于 `/tmp/open3dbench-grt-build-<uid>`，可由 `SUBMISSION_BUILD_DIR` 指定；本版原生源码已改变，需要重新构建，也可用 `OPENROAD_EXE` 指定经验证的兼容程序。

入口完成既有 HBT 重定位和共享规划后，分别路由两个 die。层归属、pin 覆盖、连通性检查及 ODB 独立重开验证通过后才发布结果；失败返回非零。物理 TRACKS、技术库、RCX 模型与固定评估器保持原样。

本地仓库使用 `python3 submission/package.py` 同步生产源码并生成根目录 `submission.zip`。包内不包含二进制、输入数据或实验产物。批量运行入口：

```bash
python3 submission/run_public_cases.py <input_root> <output_root> --threads 32 --mode both
```

## 默认策略与对照选项

M2 容量削减 70%、M3 削减 60%，其他当前 die 路由层削减 50%；全局拥塞迭代一次。最多共享 192 条网、增加 384 颗 HBT，多分支接收端路径保护继续启用。没有采用实验中的更细分组或新叶 HBT 落点策略。

默认 `GRT_HIGH_FANOUT_LAYERS=1`、`GRT_HIGH_FANOUT_POLICY=layers`。对尚未被 MLS 替换、fanout ≥ 512、HPWL ≥ 400 μm 的普通网，底 die 主干使用 metal4–10，上 die 使用 metal11–17；最多 256 条，保留 pin access、时钟等保护与 die 硬窗口。`GRT_HIGH_FANOUT_LAYERS=0` 关闭该策略。独立进程对照路径不应用此选层。

规划器复用已读取清单生成选层文件；只有本次成功标记与路径匹配才复用。其余情况走原独立 CLI，旧文件存在不构成复用依据。原 `grt.plan_layer_hints` 的部分时间移入 `mls.plan`，不能只比较其中一个阶段。

`MLS_ENABLE=0` 关闭 MLS，`MLS_CONFIG` 指定规划参数；`GRT_LAYER_ADJUSTMENTS=''` 恢复统一容量。沿用 `MLS_PREPARE_SCAN=auto|native|tcl`、`MLS_MANIFEST_EXPORTER=tcl`、`GRT_METADATA_SNAPSHOT=all`、`GRT_LAYER_DISPATCH=legacy`、`GRT_PASS_RESET=legacy`、`GRT_PROCESS_MODE=isolated`、`GRT_INPUT_MODE=odb`、`GRT_CHECK_MODE=serial` 和 `GRT_SAVE_CHECKPOINTS=1` 对照选项。显式电阻研究策略仍不是默认算法。

完整 Runtime 取外部 `run.sh` 墙时，不含构建或评估器 DRT 时间；内部父子阶段与并行子阶段不能重复相加。算法细节见 [ALGORITHM.md](ALGORITHM.md)，验证工具见 [support/README.md](support/README.md)。
