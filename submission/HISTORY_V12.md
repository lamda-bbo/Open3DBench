# 3D-IC 全局布线第十二版：检查与输出并行加速

本轮最终八例对照全部通过：每例新旧提交 ODB、source guide、MLS 计划及官方 canonical DEF/guide/ODB 均一致，官方合法性均通过。此结论来自本地官方容器；新官方分数仍未取得。

本版以官方 **23.00806162648646 分（23.01）** 的 v11 为基线，保留 v8 的物理布线策略与全部 13 份原生覆盖层。新增改动仅涉及网络分类、精确空间索引、检查调度及运行清单。

- 网络分类先判断 BOT/TOP terminal，再查 HBT 前缀；分类优先级和缓存格式保持一致。
- 常规整数 guide 使用有内存上限的稀疏网格，超大或异常几何继续使用原空间树；精确相交判定和结果顺序保持一致。
- 默认单进程、并行检查且至少 3 核时，两个只读检查与数据库最终化同时执行。必须等待全部检查成功才发布 ODB 和完成标记；串行模式及 1–2 核仍按顺序执行。
- 保留独立 ODB 重开验证，并在 `run_manifest.json` 新增 `grt_check_schedule`；实际等待时间记录为 `grt.check_guides_wait`。重叠阶段耗时不可相加作为入口时间。

本地完整验证记录位于 `reports/optimization_v12/all8_final_validation/runtime_report.json`，发布结论以其最终状态与 `reports/optimization_v12/FINAL_RELEASE.json` 为准。已完成 207 项生产回归、7 项支持工具回归。25 分尚未获得官方确认。

## 构建和运行

```bash
bash build.sh 32
bash run.sh <input_dir> <output_dir> <platform_dir> 32
```

在官方镜像 `gaocr/3dbench-contest:20260914` 中构建。`run.sh` 位于 ZIP 根目录，必需产物为 `5_1_grt.odb`。输入目录须包含 `4_1_cts.def`、`4_cts.sdc`；不随提交携带公开输入或预计算的布线结果。

默认不导出补充最终 DEF；需要时设置 `SUBMISSION_EXPORT_DEF=1`，从独立重开的最终 ODB 导出。设置 `GRT_CHECK_MODE=serial` 可关闭检查重叠。`GRT_PROCESS_MODE=isolated` 保留原独立进程实现；所有既有策略和对照开关见 `ALGORITHM.md`。

本地打包：`python3 submission/package.py`。空间索引、分类和并行发布的回归测试保留在仓库 `OpenROAD-GRT/flow_scripts/scripts_3D/tests`，实验记录不进入源码包。v11 历史说明保留于 `HISTORY_V11.md`；完整验证范围见 `VALIDATION.md`。

官方 23.01 分记录有 3 例报 `Input DEF file not found`。提交入口不产生该错误文字，本地输入完整；现有资料更指向服务器输入发现阶段，但缺少服务器尝试路径，不能断言根因已修复。应核查平台输入，不能用本地合法性结果代替正式成功率。
