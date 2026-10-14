# 第十三版：直接复用准备后的数据库检查信息

本版以 v12 为基线，沿用 MLS/HBT、选层与容量策略。新原生接口从准备后的 OpenDB 导出分类与严格连通检查所需信息，省去中间 DEF 写入及重复解析；不支持的特殊 DEF 语法自动回退，错误或哈希不一致仍阻止发布。输入 master 扫描只读至 COMPONENTS 结束，输入摘要改为流式计算。

全八例新旧提交 ODB、guide、MLS 计划和官方 canonical DEF/guide/ODB 逐字节一致，官方合法性通过；222 项生产、7 项支持及 14 项验证器篡改/留存测试通过。13 次真实原生导出与原 DEF writer/parser 对照通过，并确认数据库未改动。NDR 与供电/地参考名称由只读 Tcl 兼容性检查保护，查询不可用时回退原 DEF 路径。记录见 `reports/optimization_v13/all8_final_validation/runtime_report.json`。

本地入口耗时来自共享宿主的 RAM 工作区，仅为观测；官方已知成绩仍为 23.00806162648646（23.01），尚未确认达到 25 分。预算 512/768 的时序实验与本推荐包分开保存，本包预算保持 384。

## 构建和运行

```bash
bash build.sh 32
bash run.sh <input_dir> <output_dir> <platform_dir> 32
```

ZIP 根目录为 `run.sh`，输出为 `5_1_grt.odb`。`GRT_PREPARED_METADATA=def` 强制原 DEF 路径；`native` 要求新接口与兼容输入；默认 `auto` 自动回退。`GRT_SAVE_CHECKPOINTS=1` 保留准备阶段 ODB/DEF；`SUBMISSION_EXPORT_DEF=1` 从独立重开的最终 ODB 导出补充 DEF。全部层与严格连通检查、独立 ODB 重开及失败关闭仍执行。

历史 v12 说明见 `HISTORY_V12.md`，完整算法及验证范围见 `ALGORITHM.md` 和 `VALIDATION.md`。保存的三个服务器缺输入 DEF 失败尚缺实际尝试路径，不能将本地八例合法性视为服务器问题已修复。
