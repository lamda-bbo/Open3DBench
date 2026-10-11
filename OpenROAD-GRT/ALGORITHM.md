# 第八版：高扇出长线选层与运行加速

本版保留第七版的 HBT 重定位、共享预算、分组及逐接收端路径保护，只为仍然存在的长、高扇出普通网增加主干选层。所有用例使用同一套输入特征规则，没有用例名或逐网白名单。默认门槛为 fanout ≥ 512、HPWL ≥ 400 μm，底 die 主干使用 metal4–10，上 die 使用 metal11–17；合法 pin access 和原 die 硬窗口仍保留。

新的官方容器完整 DRT2/RCX/STA 对照中，bp 的 TNS 从 -164904 改为 -162678 ns，WNS 从 -22.2297 改为 -22.3057 ns；bp_multi 的 TNS 从 -83567.5 改为 -83525.9 ns，WNS 从 -16.9927 改为 -16.651 ns。bp DRC 13784→13754，bp_multi DRC 4800→4887，HBT 数均不变。这是有局部退步的取舍，不是每例每指标均改善；最终包的输出身份、验证覆盖和完整入口耗时见 `VALIDATION.md`。

试验中的更细分组以及按接收端代理收益调整叶 HBT 落点均未纳入最终规划器。后者虽然改善部分 TNS，却改变候选排序和预算分配，且使 bp_fe 的 TNS/WNS 与 bp 的 WNS 退步。保留原规划使此轮时序变化集中在选层策略。

运行加速不改变这一选定策略的计划与指令：

- 2D/3D 迷宫搜索通过距离地址索引找到堆位置，保持原比较和相等代价处理顺序。3D 正代价达到 BIG_INT 哨兵时，本次搜索回退原 first-match 线性查找，覆盖可能重复入堆的地址。使用网格的成员关系采用 byte 标记，原有有序遍历保留。索引增加临时内存，不宣称降低峰值内存。
- 标准 guide 行使用 from_chars 和最近技术层缓存；非标准格式回退原流式解析。Python guide 覆盖和邻接查询共享精确空间树，使用层掩码剪枝，保持矩形索引顺序、连通分量和完整检查。合并器按完整网块写出，保留重复网与格式错误的处理规则。
- MLS 包围盒由四次扫描合为一次，保留首值、NaN、正负零及空输入异常行为。规划进程复用已读取的原始清单，生成与独立选层 CLI 相同的 Tcl 和 JSON，减少重复解析大清单。
- 只有本次规划返回匹配 token、MLS 应用与快照检查成功，且消费端路径匹配时，单进程路由才使用预生成选层文件；标记仅消费一次。禁用、独立进程、外部准备或缺少成功标记时保留原路径，不能凭旧文件存在就复用。

原生覆盖层现为 13 份，已在官方基础源码上完整编译。原生扫描、确定性排序、两 die 路由、signal type/TRACKS 恢复和最终 ODB 重开验证均保留。阶段计时不等于完整入口时间，也不能把多个局部加速百分比相加；正式 25 分尚待服务器验证。

## 1. 既有 HBT 重定位

`hbt_optimizer.py` 根据每颗 HBT 的相连线网建立局部目标：相连线网 HPWL 之和。移除待优化 HBT 的 pin 后，每张 pin 包围盒给出 x、y 方向的两个端点。对所有端点排序，中间两个端点之间形成该轴的凸最优区间，两轴组合为最优矩形。

在当前点、当前点投影到最优矩形的位置、矩形中心与角点附近搜索合法 lattice 空位。每次只接受相连线网总 HPWL 严格下降且至少节省 0.1 μm 的移动，更新占用表和该 HBT 在全部相连线网中的 pin 坐标后再处理下一颗。默认做 2 轮坐标下降、搜索半径 2 个 pitch、最多接受 65,536 次移动。第二版的 4,096 次上限会让大设计在第一轮就停止；新上限不增加 HBT 数量，也不放宽任何布局约束。比较落点时先选 HPWL 最小，再选移动距离最短，最后按坐标排序，结果确定。

保护任何接触 CLOCK、非 SIGNAL、special 或封装引脚网的 HBT。HBT master 和连接保持不变，不改变非 HBT 元件、封装引脚或其连接。公开输入中的既有 HBT 为 COVER，应用移动时先改为 PLACED，再设置新位置，最后设为 FIRM；这些状态变化仅作用于允许修改的 HBT。

HBT pin 的位置随移动同步更新，多个 HBT 相连的网使用前一步更新后的坐标。最终几何节省按受影响线网集合计算一次，不重复计算共享线网。这一目标并非 RC 时延模型，也不保证每条相连子网单独变短。

## 2. 共享线网选择与动态需求

将 die 区域划分为默认 32×32 的网格。每条同 die 线网按 pin 包围盒分配 HPWL，建立类似 RUDY 的需求图。该图不包含详细布线阻塞和精确金属容量。

### 高扇出多分支与接收端保护

默认先处理底 die 上唯一 OUTPUT 驱动、至少 128 个 INPUT 接收端、HPWL 至少 400 μm 的普通 SIGNAL 网。排除 special、封装引脚、已有 HBT、既有 `_BOT`/`_TOP` 子网和 MLS 家族。准备阶段还检查实际 OpenDB master terminal 的 CLOCK/POWER/GROUND 类型，保护未在 DEF 中声明 USE 的时钟等网络。

每轮选择 HPWL × 接收端数最大的组，再沿该组最长轴做中位数切分，初始目标组数为 `min(8, ceil(sinks/64))`。源端附近选择一颗根 HBT，每组中位点附近选择一颗叶 HBT；全部落点必须满足输入 lattice、边界及间距。上 die 的一个共享子网连接根与各叶 HBT，底 die 的叶子子网分别连接接收端组。

对于每个接收端，计算源端到根 HBT、根到叶 HBT、叶到接收端的完整 Manhattan 路径。只有满足以下两个条件的接收端才使用跨层分支，其余保留在含原驱动端的 S0 中直接连接：

```text
完整三段距离 <= 1.05 × 原源端到接收端距离 + 6.4 μm
本 die 两段距离 + 0.1 × 借用 die 距离 + 25.6 μm <= 原直接距离
```

这里的 0.1 是候选排序的启发式权重，**不是实际层电阻比**；第二项也不是 STA 时延。固定 RCX 模型与 LEF 的区别见第 6 节。保留在 S0 的接收端按原直接距离计入整网评分，不计算借层节省。全网平均加权距离下降不足 20% 时放弃候选。删除空叶组后重新编号；只剩一个远端组时允许退化为两 HBT 的合法树，无远端组则不共享。

候选按所有接收端的加权距离减少量除以新增 HBT 数量排序，同分按网名排序。实际选择时重新检查已占用站点；找不到完整合法方案或预算不足时保留原网。成功后更新源端、叶子和借用 die 的需求。该过程使用相同规则处理全部用例，不以 case 名称分支。

逐接收端保护来自实际详细布线的反例：未保护方案降低了平均路径电阻，却将一条共享干线上的负载集中起来，并使另一接收端成为新的最坏路径。校验器会从原终端和实际 HBT 坐标独立重建每条受保护路径，不能只信计划里的代理统计。几何保护仍不保证所有实际 RC 路径都改善，最终采用依据是固定 DRT/STA 对照。

### 剩余预算中的双 HBT 共享

原有低扇出方案使用剩余预算。候选必须是非 special 的 SIGNAL 网，pin 数为 2–16，只有一个 OUTPUT driver，其他 pin 均为 INPUT，且所有 pin 属于同一 die。同样排除受保护网、HBT/封装引脚网、既有子网和 MLS 家族；原网 HPWL 至少 40 μm。

对 x、y 两轴分别在最大的 pin 间隙处切分，含 driver 的组为源端组。两个组内 HPWL 之和不得超过原网的 35%。初步评分为：

```text
score = (source_demand - target_demand) / (1 + source_demand)
        × trunk_length_um - local_group_hpwl_um - hbt_cost_um
```

默认 `hbt_cost_um=12.8` 是两次垂直连接的几何惩罚，不能作为 3 Ω/0.6 fF 的时延计算。

候选按初始评分降序、原网名升序处理。在准备放置时重新评估当前需求；每次成功共享后，从源 die 减去原网需求，加回两端局部子网，并在另一 die 加入新增主干需求。矩形更新后按需重建前缀和，使后续候选看到已承担的负载；不会一直使用共享前的静态需求图。

已有逐网 slack 可通过 `MLS_TIMING_CSV` 提供，表头为 `net,slack_ns`，名称与原 DEF 一致。默认禁止已标注且 slack 小于 0 ns 的网进行共享。未知 slack 的网仍参与几何评分，报告明确记录 `timing_source`。本版尚未自动提取 OpenSTA 逐网 slack，也没有布线后的时序反馈优化。

## 3. 两颗新 HBT 联合放置

保留输入 HBT 中心的 6.4 μm lattice 余数，所有新旧 HBT 均满足制造网格、die 边界和保守方形间距：任意两点必须满足 `|dx| >= pitch` 或 `|dy| >= pitch`。

对两个 pin 组，分别在坐标中位数和朝向另一组的包围盒投影位置周围搜索合法点。组合两端候选，直接最小化以下完整链路的 HPWL：

```text
HPWL(source group + HBT0) + Manhattan(HBT0, HBT1)
    + HPWL(sink group + HBT1)
```

这利用了 pin 包围盒内部的平坦最优区间，减少两端各自选最近站点产生的回头绕路。找不到两个相互合法的站点时放弃候选，不输出残缺家族。配置搜索半径为 0 时只检查原目标的最近网格点。

多分支与双 HBT 方案共用最多新增 384 颗 HBT、最多共享 192 条网的预算；总 HBT 数仍限制在保守几何容量的 30% 以内。容量为 `floor(die_width/pitch) × floor(die_height/pitch)`。固定检查器按输入 lattice 计算，可能给出稍大容量；本版保留更严格预算，不消耗超额 HBT。

对于旧双 HBT 候选，放置后若估计总线长超过原网的 130%，或扣除绕路后的评分低于阈值，就保留原网。多分支使用第 2 节的逐接收端路径保护，不具有这一总 HPWL 上限。报告记录原始 HPWL、共享链路估计、两 die 当前需求及 optional slack。

## 4. 子网与信号方向

多分支底层网使用以原驱动端为根的有向树：S0 包含驱动端、保留直连的接收端和根 HBT；S1 位于上 die，连接所有 HBT 的 TOP；S2 及后续子网位于底 die，分别连接一颗叶 HBT 和一个远端组。根使用 HBT_BOTIN，各叶使用 HBT_TOPIN。

原有双 HBT 底层网使用以下有向拓扑：

```text
driver group -- S0 BOT -- HBT_BOTIN -- S1 TOP -- HBT_TOPIN -- S2 BOT -- sink group
```

三个子网依次命名为 `<original>__MLS__S0__BOT`、`<original>__MLS__S1__TOP`、`<original>__MLS__S2__BOT`；新增实例名为唯一的 `LS_HBT_<id>`。上层网交换 BOT/TOP 和两种 HBT master 的顺序，使 Liberty 方向与信号方向一致。

原网中每个逻辑 pin 恰好转移到一个子网，原网删除。每颗新 HBT 的 BOT/TOP pin 分别接到对应 die 的子网。折叠 HBT 后应恢复原网的完整 terminal 集合和连通性。

通用校验要求 HBT 数为子网数减一、原驱动子网入度为零、其余子网入度为一，且所有子网从驱动端可达；同时检查 HBT master 的输入输出方向、每个终端出现次数、die 归属、命名和几何。官方检查器及最终 HBT 折叠支持这种连通家族，不需要修改固定评估器。

## 5. 布线与运行开销

第四版 `bp_fe` 的 4,084 条最终 DRC 中，M2 占 3,056 条，M3 占 389 条。本版为低层详细接入与绕行预留全局路由资源，默认 `GRT_LAYER_ADJUSTMENTS='metal2=0.7,metal3=0.6'`，先应用统一削减比例（默认 0.5），再替换指定层比例；0.7 表示削减 70%。原生模型在既有阻塞处理后计算容量，保留整数取整与非零边最少一条资源的语义，因此不能把这些设置解释为相对于物理 TRACKS 的精确最终容量比例。

全部条目先检查真实 routing 层、有限十进制数值 `[0,1]` 和重复项，再仅应用当前 die 窗口内的层；另一 die 的合法条目留给对应 pass。空配置恢复统一容量对照。单进程与独立进程共用配置，空 die 跳过路由。此策略只影响全局路由资源估计，不修改物理 TRACKS、LEF、RCX 或逐网硬层约束；最终 ODB 恢复原层调整元数据。不依赖 case 名、历史违例坐标或逐网名单，也不是 pin-density 自适应模型。违例分层统计支持选择这一配置，但不单独证明每条违例消除的物理因果。

入口记录 `grt_capacity_adjustment_default`、`grt_layer_adjustments_requested` 与按 die 列出的 `grt_capacity_adjustments`；最后一项仅列实际应用的逐层覆盖，未列出的层使用全局比例。较小 GRT overflow 不代表较少最终 DRC，所有容量候选必须由固定官方详细布线评测决定是否采用。

准备步骤先应用全部既有 HBT 重定位，再切分共享网和创建新 HBT。底层路由始终限制在 `metal2–metal10`，上层限制在 `metal11–metal20`，并对每条网应用 `set_net_routing_layers` 硬约束。底 die 普通 pin 的合法 metal1 接入 guide 仍保留，不能将主干 M2 下界误当成 pin access 的限制。两次路由使用同一份准备后网表与布局，合并 guide 后执行层归属、pin 覆盖和连通性检查。默认 FastRoute 拥塞迭代为 1 次（初版为 2 次）；固定评估器的详细布线仍为 `-droute_end_iter 2`，没有减少评测迭代。通过 `GLOBAL_ROUTE_ARGS` 可切回 2 次全局迭代。该迭代参数沿用第二版；第五版曾对比 1/30 次 GRT 迭代，固定 DRT 参数相同；30 次迭代的候选因耗时或质量取舍未采用，历史结果保存在包外 `reports/optimization_v5`。

默认使用同一 OpenROAD 进程执行两次 die 局部路由。两 die 队列均非空时，`grt::reset_die_routing_pass` 只清空待路由队列，并逐网调用 OpenDB `clearGuides()` 清理暂存 guide，保留硬层约束。下一次 `global_route` 本身会清理并重建路由模型、资源网格和 GCELL，因此无须在两次路由之间重新解析整份底层 guide。此调用不会修改普通网属性、非 HBT 元件或 STA 状态。

任一 die 队列为空或使用旧二进制时，保留原 `read_guides` 交接流程及 `try/finally` 恢复的临时 special 标记；`GRT_PASS_RESET=legacy` 可强制运行该对照路径。`GRT_PROCESS_MODE=isolated` 可切回初版独立进程流程。最终恢复原 TRACKS，以及所有可能被 GRT 改变的时钟网原 signal type；查询失效或强制 all 模式时恢复全网快照。其余网的 signal type 保持不变。随后完整读入合并 guide，恢复层容量调整字段并发布 ODB。交接优化可能改变内部 guide IDs，但必须保持实际网表、布局、层范围和 guide 几何相同。

提交入口将层约束能力检查合并到 DEF 读取进程，并记录进程与内部阶段耗时。准备阶段默认在命令可用时使用 `grt::export_mls_manifest` 原生流式导出，旧二进制回退到 Tcl；`MLS_MANIFEST_EXPORTER=tcl` 可显式选择对照实现。两条路径保留同一 JSON schema、DBU 坐标、OpenDB 实例/网/pin 遍历顺序及全部普通 pin、HBT pin、封装引脚记录。名称中的引号、反斜杠、Unicode 和控制字符完整转义；中心和 BPin 平均坐标按 Tcl 整数除法向下取整，负半整数也一致，避免 C++ 默认向零截断造成坐标差异。HBT 优化只为实际包含 HBT 的网复制 pin 数据，其他网保持只读，避免大用例全量深拷贝。

严格 guide 诊断只物化其原本检查的 `_BOT`/`_TOP` 网的矩形与相关 DEF 组件位置，保留这些网的全部普通/HBT pins 和原始矩形顺序。同层和跨层连通分量合并到一次矩形对扫描，pin 覆盖结果复用；原覆盖 margin、同层一 DBU 接触容差、相邻层无容差、连通分析数量限制及全部 strict failure 条件保持不变。逐层合法性检查仍遍历全部 guide，网分类和列表导出使用全量流式 DEF 解析。

逐 die 流程的列表导出同时产生完整分类缓存，逐层检查通过可选 `--classification-cache` 复用。读取前验证整数 schema 版本、完整 DEF 的 SHA-256、保留插入顺序的完整 payload SHA-256，以及每个网名和分类标签的类型；缺失、过期或损坏的缓存回退到完整解析。导出前后核对 DEF 哈希并原子发布缓存，缓存放在结果工作目录，不复制到提交的网列表目录。独立运行检查器时默认不使用缓存。

最终 ODB 必须为当前运行新生成的文件，并由 OpenROAD 重新打开验证。详细布线由固定评估器执行，运行时间比较使用提交入口耗时，不使用评估器包含 DRT 的墙时。内部 `grt.prepare` 包含 `mls.*` 子阶段，各项细分耗时不能直接相加。

## 6. 高扇出选层与可选电阻研究

`plan_net_layer_hints.py` 从完整几何清单筛选同 die、单 OUTPUT 驱动的普通 SIGNAL 网。候选 fanout 至少 512、HPWL 至少 400 μm，先排除已被当前 MLS 计划替换的原网，再按 fanout × HPWL 降序最多选择 256 条；同分按网名排序。排除 special、封装引脚、HBT、已拆分/MLS 子网和带已知时钟引脚的网，应用时再检查 MTerm 的 CLOCK/POWER/GROUND 类型以及路由器最终识别的 signal type。筛选统一使用输入特征，不依赖公开 case 名称。它是负载与长度代理，不能称为实测时序关键度。

提交入口默认设置 `GRT_HIGH_FANOUT_LAYERS=1`，单进程默认采用下述 layers 策略；`GRT_HIGH_FANOUT_POLICY=resistance` 将所选网传给原生 `set_net_resistance_aware`。每次 die 路由前清除前一次集合，保持底层 metal2–10、上层 metal11–20 的完整主干硬区间。FastRoute 的层分配和适用的 3D 重布线对这些网使用已有 wire/via 电阻代价，其余网不启用该标记；保持原普通网排序和重布线阈值。不会触发原生自动 RA 的全局 slack 排名、时钟优先排序或自动扩选。路由资源竞争仍可能间接改变未选择网的 guide，因此不能承诺时钟 guide 逐字节不变。

该代价沿用原生 LEF 的层宽、sheet resistance 和 via resistance，不是包含负载电容与完整 cell delay 的 Elmore/STA 目标。它可能增加 via 和局部拥塞，必须通过固定评估器判断。原生 3D maze 的处理范围与绕线惩罚仍在，不能保证每条所选网都接受 3D 重布线。`GRT_SELECTIVE_RA` 日志记录实际激活数，入口 manifest 的 `grt_resistance_hint_counts` 记录两 die 的应用数量。

实际评测模型与这些 LEF 电阻存在重要差异。历史固定 RCX 诊断中的官方 `6_report.log` 明确加载输入平台的 `nangate45_3D.rules`，而非同目录的 `rcx_patterns.rules`。前者的默认宽度电阻表按奇数/偶数层分别使用相同系数；例如 metal3、11、13、15 均为 0.00253571，metal2、12 为 0.0015。在该历史诊断的最终 DEF/SPEF 中，384 μm 的 metal15 主干加 0.14 μm 宽度修正后得到 974.068 Ω，与该 RCX 系数吻合；其他层也完成了同网数值交叉核对。因此，LEF 中 metal15 与 metal11 的 40 倍单位电阻差异不能用来预测本平台的最终时序收益，也不能将论文中的低阻借层收益直接迁移到本评测。该发现只用于修正优化依据，未修改平台规则或固定评估器。

`GRT_HIGH_FANOUT_POLICY=layers` 是第八版默认策略：所选网主干限制为底层 metal4–10、上层 metal11–17，并与原 die 窗口求交。这一固定选层策略和选择性电阻代价并不等价。`GRT_HIGH_FANOUT_LAYERS=0` 关闭两者。独立进程回退流程不应用这些新选网策略。原生 `global_route -resistance_aware` 仍为自动选网模式；同时指定自动模式与显式网集合会报错，避免无声改变实验范围。

同时修复 FastRoute 的跨 pass 技术层缓存：每次 `preProcessTechLayers()` 清空后按当前层数重建，避免底 die 的 10 层缓存留在前缀、上 die 扩展到 20 层时把 metal11 错当 metal1。关闭 RA 时旧电阻代价为零，原来的纯几何路由没有暴露这一问题。回归测试直接执行实际 C++ 函数，验证 10→20→10 层重建；新二进制关闭选网后的官方 bp_fe canonical DEF/guide 与 v3 相同。

## 7. 可选完整路径保护与运行优化

第 2 节的多分支接收端保护默认启用。另有针对既有 HBT 重定位和旧双 HBT 共享的可选路径保护，默认关闭：重定位时重建唯一普通驱动端到各 sink 的完整跨 die Manhattan 路径，保护方向含糊或多 HBT 的网；旧共享候选则比较原直接路径与经过两个 HBT 的三段路径。独立消融配置要求既有路径不增长、旧共享路径不超过原来的 1.05 倍加 6.4 μm。这仍不保证实际 RC 时延或详细绕线长度不增长。

单进程默认直接从原 DEF、相同 LEF/Liberty/SDC/RC 初始化，省略初始 ODB 写入与重读；默认不保存准备后的 ODB 检查点。最终完整 ODB 仍必须写出并独立重开。`GRT_INPUT_MODE=odb` 和 `GRT_SAVE_CHECKPOINTS=1` 可恢复中间产物，独立进程自动选择 ODB 输入。

分类缓存按固定批次生成 JSON 和校验摘要，保留原顺序、编码与完整性检查。层归属和严格连通性两项只读检查默认并行，单线程请求时自动串行；任一项失败仍阻止发布。`GRT_CHECK_MODE=serial` 可关闭并行。`grt.check_guide_layers` 与 `grt.check_guide_connectivity` 的子项时间相互重叠，整个检查墙时为 `grt.check_guides`。

## 8. 参考文献与迁移边界

赛题的 [MLS 论文](https://gtcad.gatech.edu/www/papers/gtcad-tvlsi22-a.pdf) 和 [Open3DBench](https://arxiv.org/html/2503.12946v1) 提供了 F2F 金属层共享、HBT 与连接树优化的思路。本版多分支、局部直连和路径保护是结合实际服务器反例形成的实现，没有复现论文全部优化器，也不引用论文收益作为本提交收益。尤其不能将文献中的物理低阻借层优势直接等同于当前固定 RCX 模型的收益。

[H3D](https://www.cse.cuhk.edu.hk/~byu/papers/C297-ICCAD2025-3DRoute.pdf) 的连续最优区域与合法 HBT 候选思想，与本项目已有凸区间/离散落点搜索相关；完整树动态规划尚未实现。[CUGR](https://cwpui.com/doc/c10.pdf) 提示应关注 via/pin access 和详细布线可行性；其局部 guide patch 未并入本版。[FastRoute](https://onlinelibrary.wiley.com/doi/10.1155/2012/608362) 的局部拥塞反馈不能等同于统一放宽容量。历史固定 DRT 对照曾淘汰全局放宽容量、统一 M4 下界和原生自动 RA 等候选。第八版只对满足门槛的普通网采用 M4 主干下界，并明确保留实测 DRC 和 WNS 的局部取舍。

## 9. 验证与消融

Python 检查新旧 HBT 的数量、边界、制造网格、lattice 余数与间距，以及原始 terminal 集合、子网图连通性、命名和信号方向。Tcl 应用后检查所有非 HBT 的 master、位置、方向、placement 状态，以及封装引脚几何与连接。

使用固定检查器验证 canonical DEF/guide。全部公开用例的准备阶段检查与完整 GRT/DRT/STA 分开记录；几何检查通过不能替代正式评测。

回归测试覆盖共享与重定位约束、路径保护、封装引脚分类、严格检查边界、缓存回退、并行检查失败传播，以及实际 C++/Tcl 的技术层重建和选择性 RA 状态隔离。此前还以 1,000 组随机几何对照旧检查实现，完整诊断字段及 3D 组件 ID 一致。当前测试数量和新二进制的官方验证范围见 `VALIDATION.md`。

第三版已在官方 `20260914` 镜像中对照原生/Tcl 导出：bp_fe 输入的 37,248 个网、113,496 个 pins，以及转义、负半整数、缺失几何、混合 die BPin 等边界样例均一致；bp_quad 使用相同输入 ODB 对照此前保存的 Tcl manifest，1,363,004 个网、4,158,170 个 pins 的全部记录及顺序一致。该次微基准中 bp_fe 导出为 Tcl 3.138 秒、原生 0.186 秒；bp_quad 原生单线程导出 9.745 秒，加载与完整对照总墙时 62.898 秒，其中没有重跑 Tcl 导出。第四版新编译二进制又用准备后的 bp_fe ODB 对照，37,632 个网、114,264 个 pins 及新增边界 fixtures 全部逐字段一致。

使用既有第二版官方容器的 bp_fe/bp_quad 产物对照严格诊断，完整诊断输出与退出状态一致；全量分类、违规结果、CLI 输出和三份网列表也一致。微基准中严格诊断耗时分别从 2.594/96.234 秒降至 0.940/29.575 秒，bp_quad 峰值 RSS 从约 7.08 GiB 降至 0.50 GiB；复用分类缓存的 bp_quad 逐层检查从流式解析的 59.819 秒降至 24.721 秒。以上是在共享宿主上测量各工具的微基准，不能代替完整入口耗时或固定 DRT/DRC/STA 的质量与评分结果；证据分别保存在 `reports/optimization_v3` 下的 `native_export`、`diagnostics` 和 `classification_cache`。

`relocation_enabled=false` 可关闭既有 HBT 重定位；`max_new_hbts=0` 可运行仅重定位方案。`dynamic_demand` 和 `joint_site_placement` 分别控制需求更新与联合落点选择。`MLS_ENABLE=0` 则关闭所有准备修改，提供相同提交接口的布线基线。这些开关用于消融和同环境比较，不依赖公开 case 名称。
