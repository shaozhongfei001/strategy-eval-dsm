# 无人值守总控提示词 v3.0 · 全量并行交付（DSM v1.1 / 档 2 全保 / 墙钟 ≤10h）

> 这是**可直接粘贴给新会话主控**的执行规程。读到本文件即视为已接受全部约束。
> 本文件只解决一个问题：**如何在不砍范围的前提下，把 21.8 小时串行当量压进 10 小时墙钟。**
> **答案（已实测）：并发槽位上限 = 6 且为真并行 → 6 lane 排程 → 计划 7.75 h，缓冲 2.25 h。Phase 1 的 5.50 h 是依赖约束不是资源约束，见 §3.2。**

## 0. 本文件的地位与继承关系

| 项 | 内容 |
|---|---|
| 取代 | `RUN-UNATTENDED-v1.0.md` 的执行序列；`ORCHESTRATION-v1.0.md` §5 的**串行波次编排**与 §12 派工模板的「6 角色全套」 |
| 完整继承（不得重写） | v2.0 §0 优先级裁决顺序、§1 每任务硬预算、§2 仪式分档、§3 RED-first 白名单、§4 禁自创验证层、§5 收敛判据、§6 证据瘦身、§7 比例校准；ORCH-v1.0 §1 指纹自检、§2 硬约束 H-1~H-14、§3 复杂度打分与升降级、§4 角色定义、§6 阶段门禁总表、§7.1 写文件管线、§8 状态持久化、§10 停机 vs 登记边界 |
| 新增 | **6 lane 持久并行（并发槽位已实测 = 6）**、**契约冻结**、**关键路径前置**、**用 pydantic 直接构造上游 Frame 打断串行链**、同步点批量裁决、并发降级矩阵 |
| 修订依据（实测，非推测） | v1.0 实跑 13.6h（11-23 20:59 → 11-24 10:35）完成 6/52 任务 = 9.6%；新增生产代码 1,842 行，同时新增测试 9,218 行、证据转储 43,511 行、ADR 3,152 行、状态与 blockers 1,036 行 → **非生产物 : 生产代码 = 31 : 1**；按此速率外推全交付 135~200h |
| 结论 | v2.0 治「单个任务磨太久」，v3.0 治「任务之间串成一条线」。**两者叠加才够。** |

## 1. 目标（三条同时成立，缺一条即失败）

1. **范围不砍**：S1→S9 全量交付，含 S7 方法层（AHP / 熵权 / TOPSIS / GRA / 三角验证 / 敏感性 / 诊断）与 S8 权重构造链（档 2 = AHP×熵权组合 + α 稳定性标定 + whatif 预演）。用户已明令 **S7+S8 不得砍**。
2. **墙钟 ≤10 小时**：计划值 **7.75h** + 缓冲 **2.25h**（并发槽位实测 = 6，见 §3.1）。**T+10.0h 是硬停线**，到点即产出交付包并如实登记未完成项。
3. **四条不可砍质量底线**：V-9 数值口径（金额 int 精确、比率 1e-12）／V-14 无静默降级／V-6 + G-03 + P-2 红线非补偿恒 forced_grade／G-02 + P-6 证据门禁 + 分池禁混排。

冲突裁决顺序照 v2.0 §0：**正确性 > 交付进度 > 证据完备度**。

**G5/G7 门禁未通过时的口径不变**：只能用合成数据跑机制，不得输出可用于真实资源配置的分数，且该声明必须进报告首屏。K-01~K-20 一律 PLACEHOLDER，严禁拟定。

## 2. 为什么并行是安全的（四条原理，缺一不可）

### 2.1 契约冻结 —— 并行的前提

`dsm/models.py` 已建成 **1,362 行 / 47 个 pydantic v2 模型**（全部 `frozen=True` + `extra='forbid'`），**本 run 内冻结**。
20 个待建模块之间**只通过类型契约耦合，不通过实现耦合** → 天然可并行。

- **R-1（写集禁改）**：任何 lane 在工作包内**禁止修改** `dsm/models.py`、`dsm/numeric.py`、`dsm/reason_codes.py`、`dsm/config.py`、`dsm/__init__.py`、`tests/test_models_*.py`、`tests/test_numeric*.py`、`tests/test_reason_codes.py`、`tests/test_config_*.py`、`fixtures/**`（T+1.0 之后）。
- **缺字段怎么办**：向 `ops/contract-gaps.md` 追加一行（`包号 | 模块 | 缺什么字段 | 类型 | 用途 | 阻塞级别 BLOCKING/WORKAROUND`），然后**用 pydantic 直接构造临时输入继续跑单测**，不停机、不自行改契约、不改别人的文件。主控在同步点一次性批量裁决并修改，改完全量回归。

### 2.2 用「构造输入」打断串行链 —— 压缩的关键

v1.0 把 S4→S5→S6→S7→S8 排成一条 21.8h 的串行链，理由是「下游要消费上游输出」。**这个理由在契约冻结后不成立**：
`attainment` 的输出是 `AttainmentFrame`（已定义在 models.py），`aggregate` 只需要这个**类型**，不需要 `attainment` 的**实现**。

→ **R-2（构造优先）**：每个包的单测一律用 `pydantic` 直接构造上游 Frame 作为输入，字段名**逐字抄 models.py**，不得凭记忆编。真实数据贯通只在**集成骨架包（E3）**与各同步点的冒烟里做。
→ 串行链因此被打断成 5 条并行 lane；串行只在 **A5 weights_calibrate**（需要跑通全链算 flip_rate）与 **Phase 2 集成**处重新出现。

### 2.3 关键路径前置 —— 排程的骨架

全项目唯一不可打断的长串行链是**权重链**：
`fixtures_gen（4 期历史）→ weights_ahp → entropy（L1 共享六步）→ weights_combine → weights_calibrate → whatif`，串行当量 **5.7h**。

- 该链拆到 **Lane A（combine/calibrate/whatif）+ Lane D（ahp/entropy）**，两条 lane 从 **T+0** 同时起跑。
- `weights_calibrate` 是全项目最晚的关键节点（需 T+3.5 前集成骨架绿），因此 **grading 必须在 T+3.5 前落地**（Lane B 第 4 位）、**sensitivity 必须在 T+3.5 前落地**（Lane D→B 协作，见 §4）。
- 任何 lane 不得抢占 Lane A 的算力；Lane A 卡住时主控**优先补 Lane A**，其余 lane 挂起等待。

### 2.4 写集互斥表（唯一共享文件由主控独占）

| 共享资源 | 写权限 |
|---|---|
| `ops/dag-state.json`、`ops/blockers.md`、`ops/contract-gaps.md` | **只有主控（Orchestrator）能写**；lane 只在最终答复里上报结构化字段，主控落盘 |
| `docs/digest/**` | 冻结（已预产 45 份 M00~M44，只读） |
| `fixtures/**` | Lane A 在 A1 内独占写；T+1.0 后冻结，变更走主控 |
| `dsm/models.py` 等契约文件 | 冻结；变更只在同步点由主控批量执行 |
| `README.md`、`pyproject.toml`、`.gitignore` | Phase 3 由 Lane E 独占 |

**Git 纪律**：一工作包一提交；提交信息中文、首行含包号；`git push` 前必须 `git ls-remote` 比对；**禁止 force push**；**禁止在并行期间 `git rebase` / `git reset` / 切分支**。

## 3. 时间账（分钟为单位的排程，不是「大概」）

### 3.1 并发能力：**已实测 = 6**（不再是假设）

2026-11-24 在本机做了一次并发探针：同时 spawn 8 个 agent，每个只跑 `date +%s%N` → `sleep 45` → `date +%s%N`。

- **第 7、8 个 spawn 直接被拒**：`collab spawn failed: agent thread limit reached` → **硬上限 = 6 个 agent 槽**
- 6 个探针的绝对时间区间（以 P1 的 START 为 0 点，单位秒）：

| 探针 | START | END | 时长 |
|---|---|---|---|
| P1 | 0.00 | 52.92 | 52.92 |
| P2 | 5.14 | 62.73 | 57.59 |
| P3 | 8.14 | 63.90 | 55.76 |
| P4 | 9.44 | 69.24 | 59.80 |
| P6 | 15.09 | 75.52 | 60.43 |
| P5 | 43.91 | 97.29 | 53.38 |

- **区间重叠分析**：t = 43.91 ~ 52.92 s 期间**六路同时在跑** → 6 槽是**真并行执行**，不是「6 个槽但只跑 2 个」
- 6 路总墙钟 97.29 s vs 串行累加 339.87 s → **加速比 3.49×**（受 bootstrap 抖动拖累，理论上限 6×）
- **推论 1**：主控（父会话）**不占**这 6 个槽；但**已完成未 close 的 agent 仍占槽**，主控必须及时 `close_agent`
- **推论 2**：`sleep` 期间零 token 消耗，故本探针的成本可忽略；各探针 START 相差 0~43.9 s 属 agent bootstrap/首命令延迟抖动，**不是排队**（否则 P5 的 START 必然晚于 P1 的 END = 52.92 s，实测 43.91 s < 52.92 s）

→ **本 run 采用 6 lane（5 条实现 lane + 1 条机动 lane）**，`concurrency_actual = 6` 已写入 `ops/dag-state.json`。

### 3.2 排程结果

工作量实测口径：剩余生产代码约 **6,000~7,500 行 / 21 个模块**，测试函数按 SDD §3.16.1 口径 **60~80 个 + 属性 15 条**（当前 `tests/` 已 9,963 行属超规格，见 R-9）。

| 项 | 值 |
|---|---|
| 串行当量（v1.0 排程） | 21.8 h |
| 剩余智能体工时（31 包预算累加） | 1,825 min = **30.4 h** |
| **Phase 1 墙钟（6 lane 并行）** | **5.50 h**（= Lane A 关键路径 330 min） |
| Phase 2 集成对齐 + 全量回归 | 1.25 h |
| Phase 3 V-1~V-20 证据表 ∥ 第二人复跑 ∥ README/tag/交付包 | 1.00 h |
| **计划完成** | **T+7.75 h** |
| 缓冲 | **2.25 h** |
| **硬停线** | **T+10.0 h**（到点即出交付包 + 如实登记未完成项） |

**关键判断：Phase 1 的 5.50 h 是「依赖约束」而非「资源约束」。**
Lane A 的链条 `fixtures(60) → combine(90) → calibrate(90) → whatif(75) = 315 min` 不可再拆（SDD S8 明令严格串行，ORCH §5.9），加上 `combine` 必须等 `ahp` 与 `entropy` 落地。**再多的 lane 也压不动这条链**，其余 5 条 lane 都在 4.25~5.25 h 内完工并转入机动。

因此第 6 个槽的正确用法**不是**再切一条实现 lane，而是：① 把 `entropy.py` 从 ahp 后面拆出来与 ahp **同时起跑**（ORCH-07，直接把 combine 的起跑点从 T+1.67 提到 T+1.00，省 0.67 h）；② 承接 R4 独立复核 agent；③ 吸收任何 lane 的超时。

**若运行时槽位不足（实测 <6）的降级矩阵**：

| 可用槽 | 排法 | 预计墙钟 | 判定 |
|---|---|---|---|
| 6 | 本文件 §4 原样（Lane A~F） | **7.75 h** | ✅ 达标，缓冲 2.25 h |
| 5 | F 的 4 包（entropy/audit/diagnostics/reports）回填到 D 与 C 尾部；**entropy 必须仍与 ahp 同批起跑**（放到 E 的首位） | 8.6 h | ✅ 达标，缓冲 1.4 h |
| 4 | 再把 E（验证 lane）并入 A/B 尾部 | 10.3 h | ⚠ 撞线，须砍 Phase 3 的 P3b 改期，**不得砍 S7/S8** |
| ≤3 | — | >13 h | ❌ 停机上报 |

> 槽位数在 run 启动时**必须重新实测一次**（spawn 探针直到被拒），写入 `concurrency_actual`；上表按实测值选排法。**不得沿用本文件的 6 而不验证**——限额可能随运行时版本变化。

## 4. 6 条 Lane 与 31 个工作包派发卡片

> 预算列格式：`墙钟min / 生产代码行上限 / 测试函数上限`，取自 v2.0 §1（C1 20/150/8，C2 45/400/25，C3 90/700/40），本表在此基础上**按包收紧**。
> digest 列是**唯一事实来源**，禁止读 SDD 原文（2,003 行）与 ORCH 全文。
> 「前置」为空表示 T+0 可起；上游未实现时按 R-2 用 pydantic 构造输入。
> 时间窗单位 = 小时（从 T+0 起算），是**排程承诺**，超时按 R-6 交付最小可用版本并登记。

### Lane A — 权重链下游（关键路径，全 C3/max，T+0 → T+5.50）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| A1 | `fixtures_gen.py`：12 策略 / 4 域 / A3B3C4D2 / **7 个刻意构造** / **≥4 期历史窗口** / golden 期望值骨架 | M34 M37 M31 | `dsm/fixtures_gen.py` `fixtures/**` `tools/gen_golden.py` `tests/test_fixtures.py` | C3/max | 60/600/16 | 同 seed 逐字节相等；G-01~G-15 每条触发条件齐备；无真实数据 | models | 0→1.00 |
| A2 | `weights_combine.py`：档 2 **六步顺序照做** + H-1~H-5 四约束 + **INACTIVE 回退不被稀释** + 逐指标四列对照表 + provenance 完整 + `status=DRAFT` | M08 M07 M01 M42 | `dsm/weights_combine.py` `tests/test_methods_combine.py` | C3/max | 90/700/25 | T-CMB-01~09、P-14、P-15 | A1 D1 **F1** | 1.00→2.50 |
| A3 | `weights_calibrate.py`：四项稳定性指标 + **字典序可行集（非加权目标函数）** + **遍历全网格取最小可行 α** + `NON_MONOTONIC_WARNING` + `alpha_floor` + **不得放宽治理预算** + seed | M09 M13 M42 | `dsm/weights_calibrate.py` `tests/test_methods_calibrate.py` | C3/max | 90/600/25 | T-CAL-01~04、P-11~P-13、**V-19** | A2 E1 B3 D2 | 2.75→4.25 |
| A4 | `whatif.py`：**INV-2 只读**（目录哈希比对自证）+ 归因精确性 ≤1e-12 + 两段归因交叉项分离 + **`redline_delta` 必为空** + 等权一致性 | M10 M42 | `dsm/whatif.py` `tests/test_methods_whatif.py` | C3/max | 75/450/20 | T-WIF-01~05、**V-18** | A3 | 4.25→5.50 |

### Lane B — 入分主干 + 契约收尾（T+0 → T+4.25）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| B1 | `attainment.py`：达成率四公式 + 边界 + **分级门槛的唯一依据** | M02 M16 | `dsm/attainment.py` `tests/test_attainment.py` | C3/max | 60/450/20 | **G-01 G-04** | models numeric | 0→1.00 |
| B2 | `aggregate.py`：加权线性和 + **双轨聚合** + 权重重归一 | M03 | `dsm/aggregate.py` `tests/test_aggregate.py` | C2/flash | 45/300/18 | G-01、T-CMB-06、**INV-3**（不得调用 diagnostics / weights_combine） | 构造输入 | 1.00→1.75 |
| B3 | `grading.py`：四级分级六步 + **滞回** + **版本断点** + 等级只看绝对轨 | M05 | `dsm/grading.py` `tests/test_grading.py` | C3/max | 60/400/20 | **G-04 G-08** | 构造输入 | 1.75→2.75 |
| B4 | `config.py` 语义校验 + 权重版本校验：**把已入库的 211 个 RED 测试跑到绿**（R-8 triage 授权，删改须逐条列出理由） | M20 M38 | `dsm/config.py` `tests/test_config_semantic.py` `tests/test_config_weight_version.py` `tests/test_config_properties.py` | C3/max | 90/实现≤400/**测试只删改不新增** | C-01 前置、P-11、Σ W_d=1、维度内 Σ w_j=1、floor 单调 L1>L2>L3>L4、FROZEN 缺 whatif_run_id 直接失败 | models | 2.75→4.25 |

### Lane C — 加载 + 门禁旁路（T+0 → T+4.50）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| C1 | `io_loaders.py`：CSV/Parquet 读取 + 类型强制 + **输入指纹（SHA256 / 行数）** + 上期数据 | M21 M18 | `dsm/io_loaders.py` `tests/test_io_loaders.py` | C2/flash | 45/300/15 | **G-12** | models | 0→0.75 |
| C2 | `preflight.py`：**C-01~C-10** + BLOCK 时**只写审计包 / 退出码 2 / 不产 score_card** | M22 M28 | `dsm/preflight.py` `tests/test_preflight.py` | C2/flash | 60/400/20 | **G-10 G-11**、V-14 逐条 | C1 | 0.75→1.75 |
| C3 | `evidence.py`：A/B/C/D 证据强度五步短路 + **默认 GATE_ONLY（不乘入分数）** + A 类保守性 + CEL-0 消费 | M23 M41 M40 | `dsm/evidence.py` `tests/test_evidence.py` | C2/flash | 45/300/18 | **G-02** | 构造输入 | 1.75→2.50 |
| C4 | `redline.py`：HARD/SOFT 旁路否决 + **红线不参与加权** + 恒 `forced_grade` + 豁免路径 | M04 | `dsm/redline.py` `tests/test_redline.py` | C3/max | 60/400/20 | **G-03 P-2 V-6** | 构造输入 | 2.50→3.50 |
| C5 | `pooling.py`：**分池禁混排** + 一级库门禁（C 类禁入） + **占比双报** | M24 | `dsm/pooling.py` `tests/test_pooling.py` | C3/max | 60/400/20 | **G-02 P-6** | C3 C4 | 3.50→4.50 |

### Lane D — 权重链上游 + 方法旁路 + CLI（T+0 → T+5.00）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| D1 | `weights_ahp.py`：几何平均法 + 特征向量法**交叉验证 ≤1e-6** + 多专家几何聚合 + **CR ≥ 0.1 拒绝并列最不一致前 5 对** + `status` 只能 DRAFT（写 FROZEN 抛错） | M06 M42 | `dsm/weights_ahp.py` `tests/test_methods_ahp.py` | C3/max | 60/450/20 | **T-AHP-01~06** | models numeric | 0→1.00 |
| D2 | `sensitivity.py`：OAT / MC（固定 seed）/ LOO / NORM_SWAP → **flip_rate** + 稳定性标签 + **否决权** | M13 | `dsm/sensitivity.py` `tests/test_sensitivity.py` | C3/max | 75/500/22 | **G-05 G-06**、T-SEN-01~03 | 构造输入 | 1.00→2.25 |
| D3 | `normalize.py`：相对标准化轨三方法 + **锚定集** + **池内归一** + 只用于排名不用于门槛 | M43 | `dsm/normalize.py` `tests/test_normalize.py` | C2/flash | 45/350/18 | **G-05 P-4** | 构造输入 | 2.25→3.00 |
| D4 | `triangulation.py`：TOPSIS / GRA / **三个 Spearman** / 否决权 / 可关开关（**不入分**） | M12 | `dsm/triangulation.py` `tests/test_triangulation.py` | C2/flash | 60/450/22 | **T-TOP-01~03、T-GRA-01~03、T-TRI-01** | 构造输入 | 3.00→4.00 |
| D5 | `cli.py`：**八子命令齐全** + 退出码（0/2 preflight BLOCK/3 ConfigPlaceholder/4 DataLoad/6 ConsistencyFailed/7 AlphaInfeasible）+ L0b 产物只写 `reports/calibrate/<run_id>/`、`reports/whatif/<run_id>/` | M27 M29 M30 | `dsm/cli.py` `tests/test_cli.py` | C2/flash | 60/450/16 | **V-10**、INV-2 | 延迟导入解耦 | 4.00→5.00 |

### Lane E — 验证与交付（独立性 = 反作弊控制，不得并入实现 lane；T+0 → T+5.25）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| E1 | **集成骨架** `tests/test_integration_spine.py`：按 M29 **主流程九步**串起 fixtures → io → preflight → attainment → normalize → aggregate → grading → evidence/redline/pooling → sensitivity → audit → reports；模块未落地处先 `pytest.skip` 并登记，每落一个去掉一个 skip | M29 M34 M26 | `tests/test_integration_spine.py` | C3/max | 60/0/≤12 | 九步全贯通；**每个同步点主控必须跑一次** | A1 | 0→1.00 |
| E2 | golden **G-01~G-08**（期望值只能来自 A1 构造与手算，R-14 禁反填） | M31 M37 | `tests/test_golden_a.py` | C3/max | 75/0/≤20 | G-01 G-04 G-08 G-09 G-02 G-03 G-13 G-15 | E1 A1 | 1.00→2.25 |
| E3 | golden **G-09~G-15** | M31 M37 | `tests/test_golden_b.py` | C3/max | 75/0/≤20 | G-05 G-06 G-07 G-10 G-11 G-12 G-14 | E2 | 2.25→3.50 |
| E4 | 属性 **P-1~P-15**（开发期 `max_examples=25`，500 例只在 Phase 3 的 V-2 门禁跑） | M32 | `tests/test_properties_all.py` | C2/flash | 65/0/15 条属性 | **V-2** | 各模块 | 3.50→4.58 |
| E5 | `tests/test_architecture.py`：**INV-1/2/3** 分层断言 + **P-8 AST 扫描**（业务模块出现 reason_code 裸字面量即失败）+ **H-8 纯函数扫描**（禁 `time.time()` / `datetime.now()` / 无 seed 的 `random`）+ **ORCH-03 守护**（entropy 在 L1、L5 不 import L0a） | M00 M16 | `tests/test_architecture.py` | C3/max | 40/0/≤12 | 三条不变量机器守护 | 全部模块存在 | 4.58→5.25 |

### Lane F — 机动 lane（熵权 + 横切模块 + R4 复核 + 超时吸收；负载 T+0 → T+2.92，之后机动）

| 包 | 产物 | digest | 写集 | 档/模型 | 预算 | 守护测试编号 | 前置 | 时间窗 |
|---|---|---|---|---|---|---|---|---|
| F1 | **`dsm/entropy.py`（L1，裁决 ORCH-03）**：§2.4.2 **六步唯一实现**，离线（A2）与在线（F3）**共用**；平移消零；`Σd_j = 0` → **不输出熵权 + 全部 INACTIVE + 预警** | M07 M16 | `dsm/entropy.py` `tests/test_entropy.py` | C2/flash | 40/200/14 | **T-ENT-01~03** | numeric | 0→0.67 |
| F2 | `audit.py`：manifest + 输入指纹 + **规范化序列化五规则** + `reproducibility_hash` + 复跑步骤 | M25 | `dsm/audit.py` `tests/test_audit.py` | C2/flash | 45/300/15 | **G-12 V-11** | 构造输入 | 0.67→1.42 |
| F3 | `diagnostics.py`：在线熵权（**调用 F1 的 L1 共享实现**）/ CV / VIF（相关矩阵求逆对角元）/ 相关矩阵 / GRA 效度 + **工单闭环列**（`suggested_action` + `owner`） | M11 M07 | `dsm/diagnostics.py` `tests/test_diagnostics.py` | C2/flash | 45/350/18 | T-ENT-*、**G-07**、**INV-3**（输出对象不含任何可被 aggregate 消费的权重字段） | F1 | 1.42→2.17 |
| F4 | `reports.py`：`report.md` **十段** + score_card 各段 + grade_ledger（`recommended_action` 与 `decided_action` **分两列**）+ 稳健性/诊断报告 + 审计包 | M26 M37 | `dsm/reports.py` `tests/test_reports.py` | C2/flash | 45/400/18 | **G-14** | 构造输入 | 2.17→2.92 |
| F5 | **机动**：① 承接各同步点的 R4 独立复核 agent（占 1 槽）② 吸收任一 lane 的超时包 ③ Phase 2 缺陷切片的第一顺位承接者 | — | 随任务 | C2/C3 | 视情况 | — | — | 2.92→5.50 |

### Phase 2 / Phase 3（6 lane 收敛，主控统一编排）

| 包 | 产物 | 档/模型 | 预算 | 判据 | 时间窗 |
|---|---|---|---|---|---|
| P2 | **集成对齐 + 全量回归**：去掉 E1 全部 skip；按缺陷切片把 6 lane 拆开并行修（缺陷按模块归属分派，**跨模块缺陷由主控裁决归属**） | 6×C2/C3 | 75 min | 全量 pytest **0 failed / 0 error / 0 新增 skip / 0 xfail**；编码校验通过 | 5.50→6.75 |
| P3a | **V-1~V-20 全量验收证据表**：逐条四列（判据 / 检验方式 / **实测证据** / 结论），**任何一条无实测证据一律记 ❌，不得推测** | C3/max（R4） | 60 min | Lane A 承接；证据表 ≤120 行 | 6.75→7.75 |
| P3b | **第二人复跑**：全新 clone + 断网单机 + 同 seed → `reproducibility_hash` **精确相等** | C2/flash | 30 min | Lane E 承接；**V-3 G-12 V-10** | 6.75→7.25（与 P3a 并行） |
| P3c | README（复现步骤 + 第二人复跑指引 + 依赖锁定 + **已知缺口**）+ `git tag v1.1.0` + 交付包（阶段对账单合集 + **待行方签认清单 K-01~K-20 + G5/G7 门禁**） | C1/flash | 30 min | Lane F 承接；§1.8 | 6.75→7.25（与 P3a 并行） |

## 5. 铁律 R-1 ~ R-15（并行模式下新增或收紧，违反即事故）

| 编号 | 铁律 | 违反后果 |
|---|---|---|
| **R-1** | **写集禁改**：工作包内禁止修改 §2.1 列出的契约文件与他人写集文件（见卡片表「写集」列） | 并行冲突 → 主控回滚该包 |
| **R-2** | **构造优先**：上游未实现时用 pydantic 直接构造 Frame，**字段名逐字抄 `dsm/models.py`**，不得凭记忆编造 | 集成期集体崩 |
| **R-3** | **零证据转储**：`ops/evidence/` 已在 `.gitignore`；pytest 全量输出**不落盘**，只记「失败 N 项 + 前 20 行 + 统计行」 | 重演 43,511 行转储事故 |
| **R-4** | **每包自带冒烟**：≥1 条 happy path + ≥1 条负向，且必须在**本包内跑通**才算 done | 缺陷全部堆到 Phase 2 |
| **R-5** | **digest 是唯一事实来源**：只读卡片表指定的 digest（≤131 行/份），**禁止读 SDD 原文 2,003 行、禁止通读 ORCH-v1.0 505 行** | token 失控（前一轮单任务 713 KB 文本 vs 480 行代码） |
| **R-6** | **够用即止**：满足 v2.0 §5 五条收敛判据即**立刻**进下一包，**禁止追加加固轮次**，禁止以「更严谨/更完备/更保险」为由超预算 | 13.6h 只做 9.6% 的直接原因 |
| **R-7** | **禁自创验证层**：只允许 v2.0 §4 白名单四类对拍。**禁止** mutation testing、anti-cheat diff、自建 probe 脚本、为交叉验证重复实现参考算法（SDD 点名的双算法对拍除外） | 前一轮 >120 KB 自创验证档案，`quality_incidents = 0`，零缺陷发现 |
| **R-8** | **211 RED 测试 triage 授权（H-11 显式例外）**：包 B4 跑到绿时，**允许删改**与 SDD §3.3.4 / §3.12 冲突或过度规格化的测试，但**必须在 commit message 里逐条列出**（`文件:测试名 → 删/改 → 理由 → SDD 行号或「超规格」`）。**不得静默删、不得用 skip/xfail 掩盖** | 契约层永久 RED，阻塞全链 |
| **R-9** | **测试规模上限**：全项目单元测试函数目标 **60~80 个 + 属性 15 条**（SDD §3.16.1 原文口径）。当前已有 582 个（超 7~10 倍）→ **本 run 净新增测试函数 ≤120**，每包严格按卡片表上限。**判据不是「还能测什么」，而是「SDD 的哪条守护测试编号要求它」；没有编号对应的测试不要写** | 比例失控 |
| **R-10** | **复核分档**：C1 不派 R4（主控抽查 diff）；C2 并入同步点批量复核；C3 单包复核档案 ≤80 行；**同步点批量复核总量 ≤120 行/lane** | 复核变仪式 |
| **R-11** | **hypothesis 只在开发期跑 `max_examples=25`**；500 例只在 Phase 3 的 V-2 门禁跑一次 | 单包超时 |
| **R-12** | **不编造**：无实测证据一律记 ❌；K-01~K-20 一律 PLACEHOLDER，**严禁拟定**；公开文档只支持其所列功能事实 | 诚实性红线 |
| **R-13** | **Git 纪律**：一工作包一提交、中文 message、首行含包号；`push` 前 `git ls-remote`；**禁 force push / rebase / reset / 切分支**；并行期间**只有主控能 push** | 断点续跑被破坏 |
| **R-14** | **golden 不跟随实现（H-14）**：G-01~G-15 的期望值只能来自 `fixtures_gen` 的构造与手算，**严禁用实现输出反填 golden** | 验证失去意义 |
| **R-15** | **契约变更单点化**：只有主控能在同步点改 `models.py` / `numeric.py` / `reason_codes.py` / `__init__.py`，改完**必须全量回归 + 记 ADR ≤60 行**，并广播给 6 lane | 写集互斥失效 |

### 5.1 裁决 ORCH-03（本 run 新增，记录在案）

**问题**：SDD §2.4.2 行 537 明确「熵权公式（六步，**两个计算者共用同一实现**）」，两个计算者是 `weights_combine.py`（**L0a**）与 `diagnostics.py`（**L5**）。但 INV-1 规定 **L1-L5 永不 import L0a/L0b** → `diagnostics` 不能调用 `weights_combine` 里的实现。

**裁决**：新增 **`dsm/entropy.py`，层级 L1**，作为 §2.4.2 六步的**唯一实现**；`weights_combine`（L0a）与 `diagnostics`（L5）都从 L1 导入它。

**依据**：① 只有放在 L1 才同时满足 INV-1（L1 不 import L0）与「共用同一实现」；② 不放进 `numeric.py`，因为 numeric.py 是「全系统唯一**数值口径**实现点」（金额 int / 比率 1e-12 原语），熵权是六步统计算法，混入会污染其职责并让全部 lane 争抢同一文件写集；③ 类型隔离照旧成立——`WeightProvenance.entropy` 仍是**快照值**，不是可调用对象，INV-3 由 `tests/test_architecture.py` 守护。

**影响**：模块数由 23 → **24**；`dsm/__init__.py` 分层注释需在同步点 SP-1 加一行 `L1 ... entropy`（由主控执行，R-15）。**此为架构落位调整，不改任何设计口径、不改任何算法步骤。**

### 5.2 裁决 ORCH-04（成本护栏口径统一，含实测算术）

ORCH-v1.0 的**实例**写「高档任务 ≤40%」，其**模板**与 v1.0 实测均为 ≤45%。
本 run 按 §4 卡片表逐包打分后的**实测值：C3/max = 17/31 = 55%**（Phase 1 的 27 包中 15 包为 C3）。

**两个数字都对不上 45%，处置如下**：

1. **不为凑护栏降档**。这 15 个 Phase 1 C3 包是：权重链 4 包（A1 fixtures / A2 combine / A3 calibrate / A4 whatif）、入分主干 2 包（B1 attainment / B3 grading）、契约收尾 1 包（B4 config 211 RED）、门禁旁路 2 包（C4 redline / C5 pooling）、方法 2 包（D1 ahp / D3 sensitivity）、验证 4 包（E1 骨架 / E2 G-01~08 / E3 G-09~15 / E5 架构）。**全部**落在四条不可砍底线（V-9 / V-14 / V-6+G-03+P-2 / G-02+P-6）或档 2 全保范围上。按 ORCH §3.1 客观打分表逐项打分即得 C3；降档等于把底线交给 flash 模型，违反 v2.0 §0「正确性 > 进度 > 成本」。
2. **护栏改为本 run 专属的 ≤60%**，同步点末核算实际占比并写进对账单（§13）。
3. **预置降级候选**（仅当成本超支时按此顺序降，降级后守护测试编号不得减少）：`E3 → C2`（与 E2 同模式，范式已由 E2 建立）、`B5 audit → C1`、`C6 reports → C1`、`D6 cli → C1`、`P3c → C1`。全部降完可把 C3 压到 **12/31 = 39%**。

### 5.3 裁决 ORCH-07（并发实测 + 熵权与 AHP 同批起跑）

**实测事实**（见 §3.1）：本机 agent 槽硬上限 = **6**，且 6 路为**真并行执行**（区间重叠 9.01 s 内六路同时运行，加速比 3.49×）。主控（父会话）不占槽；**已完成未 close 的 agent 仍占槽**。

**据此做出的排程裁决**：

1. **采用 6 lane（A~F），而非原设计的 5 lane。** 第 6 条 lane（F）**不用于再切一条实现流水**——因为 Phase 1 的 5.50 h 由 Lane A 的依赖链决定，属**依赖约束而非资源约束**，加 lane 无用。F 的用途是：承接 `entropy.py` 与三个横切模块（audit / diagnostics / reports）、承接各同步点的 R4 独立复核 agent、吸收任一 lane 的超时包、作为 Phase 2 缺陷切片的第一顺位承接者。
2. **`entropy.py` 与 `weights_ahp.py` 必须同批 T+0 起跑**（F1 与 D1 并行），不得串行。原 5 lane 设计里 entropy 排在 ahp 之后，使 `weights_combine` 的起跑点被推到 T+1.67；拆开后 combine 在 **T+1.00** 起跑，**净省 0.67 h**，Phase 1 由 5.92 h 降到 5.50 h。
   依据：SDD §2.4.3 Step 1（AHP + CR 检验）与 Step 2（标定窗口熵权）是**两个互相独立的输入**，`combine()` 的签名 `combine(ahp: AhpResult, entropy: EntropySnapshot, opts)` 也证实二者是并列参数而非先后步骤。串行只是 v1.0 的排程习惯，不是口径要求。
3. **`audit` / `diagnostics` / `reports` 从 B、C lane 移到 F lane**，使 Lane B 从 5.75 h 降到 4.25 h、Lane C 从 5.25 h 降到 4.50 h。这三个模块都只依赖 models 契约（`diagnostics` 另依赖 F1），移到 F 不产生任何新依赖。

**未采纳的进一步加速（登记备查，不在本 run 执行）**：`whatif`（A4）与 `weights_calibrate`（A3）并行。M42 行 1073 原文「重跑 Step 1–7（**可选** Step 8）」支持「whatif 不强依赖 calibrate」的读法，若成立可再省 1.25 h（Phase 1 → 4.25 h）。**不采纳的理由**：ORCH §5.9 明令 S8 的 T01→T02→T03 **严格串行**，且注明「whatif 复用两者」；在没有读到 M10 原文确认 Step 8 可选的确切语义前，不得为省 1.25 h 而违反已冻结的串行裁决（v2.0 §0：正确性 > 进度）。**若 SP-2 时 Lane A 已落后计划 ≥0.5 h，主控可读 `docs/digest/M10-whatif.md` 复核此点，确认后可启用该加速并在此登记为 ORCH-07b。**

## 6. 单工作包循环（5 步，替代 v1.0 的 7 步 6 角色）

| 步 | 动作 | C1 | C2 | C3 |
|---|---|---|---|---|
| 1 | **取证**：只读卡片指定 digest | 主控给行号摘录，不派 R1 | 同 C1 | R1 出 digest（已预产，直接读） |
| 2 | **测试**：RED-first **仅对 v2.0 §3 白名单模块**（attainment/normalize/grading/evidence/redline/pooling/sensitivity/triangulation/diagnostics/weights_ahp/weights_combine/weights_calibrate/whatif/audit）；声明式契约层（models/config/io_loaders/cli/reports）直接写契约+负向 | 与实现同 agent | 同 agent，先写关键负向 | R3 先写 RED |
| 3 | **实现**：受 §4 卡片预算约束 | 同 | 同 | R2 |
| 4 | **自验**：跑**本包**测试 + 冒烟（R-4）。**全量 pytest 只在同步点由主控跑**，lane 不得每包跑全量 | 同 | 同 | 同 |
| 5 | **提交 + 上报**：一包一 commit（不 push，R-13），最终答复只给结构化上报行（§6.1），**不附证据转储** | 同 | R5 | R4（≤80 行档案）→ R5 |

### 6.1 lane 上报格式（固定一行，主控据此写 `ops/dag-state.json`）

```
PKG=<包号> STATUS=<done|blocked|partial> COMMIT=<sha7> MIN=<实际墙钟> PROD=<生产代码行> TF=<测试函数数> PASS=<本包通过数> FAIL=<本包失败数> GAPS=<contract-gaps 行数> NOTES=<≤5 行，只写事实与数字>
```

**禁止**在上报里粘贴 pytest 全量输出、禁止粘贴代码、禁止写形容词。

## 7. 同步点协议（4 个，每个 ≤10 min，由主控独占执行）

| 同步点 | 时刻 | 必须完成的裁决 |
|---|---|---|
| **SP-1** | **T+1.00** | A1 fixtures **冻结**（此后 `fixtures/**` 只读，R-1）；D1 ahp 与 **F1 entropy** 双交付确认（ORCH-07 要求二者同批完成，缺一个则 A2 combine 不得起跑）；**执行 ORCH-03**（`dsm/__init__.py` 的 L1 行加 `entropy`，R-15 单点改）；E1 骨架首轮 skip 清单入账 |
| **SP-2** | **T+2.75** | **本 run 最关键的放行点**：B3 grading + D2 sensitivity + E1 集成骨架**三者全绿**才放行 A3 `weights_calibrate`。任一未绿 → 主控**优先补该 lane 并把 F 机动槽压上去**，其余 lane 挂起等待。同时抽查 B4 的 commit message 是否逐条列出 211 RED 的删改理由（RK-P5） |
| **SP-3** | **T+4.25** | A3 calibrate 完成确认；C4/C5 与 D3/D4 交付确认；E2/E3 golden 首轮结果入账；**契约缺口批量裁决 #2** |
| **SP-4** | **T+5.50** | Phase 1 收口：全量 pytest 统计；**决定 Phase 2 的缺陷切片如何分给 6 lane**（F 为第一顺位） |

每个同步点主控固定做 5 件事（顺序不可换）：

1. 收各 lane 的 `PKG=` 上报行 → 写 `ops/dag-state.json`（`ev` 字段**只存数字**：`min / prod / tf / pass / fail / commit`）
2. 裁决 `ops/contract-gaps.md`：BLOCKING 级立即改契约（R-15），WORKAROUND 级登记进 Phase 2 待办
3. 跑 `tests/test_integration_spine.py` + 全量 pytest，**只记统计行**（R-3、ORCH-06）
4. 批量复核（R-10）：C3 包各 ≤80 行档案，每 lane 合计 ≤120 行；**复核 agent 用 F 的空闲槽，用完立即 `close_agent`**（已完成未 close 仍占槽）
5. `git add -A && git commit && git ls-remote && git push`（**只有主控 push**，R-13）

## 8. 派工 prompt 模板（v3.0 并行版，5 段，自包含）

```
【角色】你是 strategy-eval-dsm 的实现工程师，负责单个工作包 <包号>。仓库 /home/szf/dev/strategy-eval-dsm，venv /home/szf/venvs/dsm/bin/python。
【唯一事实来源】只读 docs/digest/<digest 列表>（≤131 行/份）。禁止读 SDD 原文、禁止通读 ORCHESTRATION-v1.0.md、禁止读其他 lane 的实现文件。
【环境事实】先读 docs/CONTEXT-BRIEF-v1.0.md（环境/写文件管线/已建成 API/5 条陷阱/规模校准）。写文件管线：PowerShell Set-Content -Encoding UTF8 写 C:\Users\szf\AppData\Local\Temp\dsm_stage\ → rsync -a 进仓库 → python3 tools/normalize.py → venv python 跑 pytest。命令里禁止出现 $ 与反引号。
【任务】<卡片表的「产物」列原文> 。写集只有：<卡片表「写集」列>。守护测试编号：<卡片表编号列>。预算：<墙钟 min / 生产代码行 / 测试函数数>。
【铁律】R-1 禁改契约与他人文件（缺字段写 ops/contract-gaps.md 一行并用 pydantic 构造输入继续，不停机）；R-2 字段名逐字抄 models.py；R-3 零证据转储；R-4 自带冒烟；R-6 够用即止；R-7 禁自创验证层；R-9 测试函数上限；R-11 hypothesis max_examples=25；R-12 不编造；R-13 一包一 commit 不 push；R-14 golden 不跟随实现。
【交付】最终答复**只给一行** PKG=... STATUS=... COMMIT=... MIN=... PROD=... TF=... PASS=... FAIL=... GAPS=... NOTES=...（≤5 行事实与数字）。
```

## 9. 状态持久化（`ops/dag-state.json` schema v3）

```json
{
  "orch_version": "ORCH-v3.0-PARALLEL",
  "run_prompt": "docs/RUN-UNATTENDED-v3.0-PARALLEL.md",
  "sdd_fingerprint": {"sha256_12": "708679e9a83d", "lines": 2003},
  "repo": {"path": "/home/szf/dev/strategy-eval-dsm", "branch": "main",
           "venv_python": "/home/szf/venvs/dsm/bin/python"},
  "concurrency_probed": 6,
  "concurrency_actual": 6,
  "concurrency_probe_evidence": "2026-11-24 spawn 8 探针，第 7/8 个被拒 agent thread limit reached；6 路区间重叠 9.01s，加速比 3.49x",
  "t0_wall_clock": null,
  "plan": {"phase1_h": 5.50, "phase2_h": 1.25, "phase3_h": 1.00,
           "planned_finish_h": 7.75, "buffer_h": 2.25, "hard_stop_h": 10.0},
  "phase_current": "P1",
  "phase_order": ["P1", "P2", "P3"],
  "lanes": {
    "A": {"role": "权重链下游（关键路径）", "priority": 1, "queue": ["A1","A2","A3","A4"], "window_h": [0.0, 5.50]},
    "B": {"role": "入分主干 + 契约收尾", "priority": 3, "queue": ["B1","B2","B3","B4"], "window_h": [0.0, 4.25]},
    "C": {"role": "加载 + 门禁旁路", "priority": 5, "queue": ["C1","C2","C3","C4","C5"], "window_h": [0.0, 4.50]},
    "D": {"role": "链上游 + 方法旁路 + CLI", "priority": 2, "queue": ["D1","D2","D3","D4","D5"], "window_h": [0.0, 5.00]},
    "E": {"role": "验证与交付（独立性=反作弊）", "priority": 4, "queue": ["E1","E2","E3","E4","E5"], "window_h": [0.0, 5.25]},
    "F": {"role": "机动：熵权+横切模块+R4复核+超时吸收", "priority": 6, "queue": ["F1","F2","F3","F4","F5"], "window_h": [0.0, 2.92]}
  },
  "sync_points": {"SP-1": {"at_h": 1.00}, "SP-2": {"at_h": 2.75},
                  "SP-3": {"at_h": 4.25}, "SP-4": {"at_h": 5.50}},
  "cards_ref": "digests / writeset / guards 全文见 §4，状态文件不重复存",
  "work_packages": {"<包号>": {"lane":"A","module":"weights_combine.py","cx":"C3","model":"max",
                               "status":"pending","deps":["A1","D1","F1"],
                               "budget_min":90,"prod_max":700,"tf_max":25,
                               "ev":{"min":null,"prod":null,"tf":null,"pass":null,"fail":null,"commit":null}}},
  "counters": {"flash_pkgs":0,"max_pkgs":0,"c3_pkgs":17,"c3_ratio_pct":55,
               "escalations":0,"rework_rounds":0,"quality_incidents":0,
               "contract_gaps":0,"budget_violations":0,
               "net_new_test_funcs":0,"net_new_test_funcs_cap":120},
  "session_log": [{"seq":1,"date":"...","did":["..."],"next":"..."}]
}
```

**断点续跑规则**（照 ORCH §8）：新会话启动先读本文件 §3/§4 + `ops/dag-state.json` + `ops/blockers.md`，从 `lanes[*].queue` 的第一个 `pending` 包继续；**不重跑已 done 的包**；`ev` 字段只存数字（v2.0 §6）；整份状态文件 ≤25 KB。

## 10. 风险登记（并行模式特有，RK-P1 ~ RK-P5 共 5 条 + 缓解）


| 编号 | 风险 | 概率 | 影响 | 缓解（已内置） |
|---|---|---|---|---|
| RK-P1 | **集成风险**：20 个模块各自对 pydantic 构造输入通过，合起来跑不通（字段名拼错、Frame 语义理解偏差、Decimal/int 混用） | **高** | Phase 2 超时 → 撞 T+10 硬停线 | ① E1 集成骨架从 T+0 就写，每落一个模块去掉一个 skip；② 4 个同步点各跑一次骨架；③ R-2 要求字段名**逐字抄** models.py；④ Phase 2 预留 75 min + 缓冲 2.25 h |
| RK-P2 | **并发槽位在 run 期间被别处占用**（本机已实测上限 = 6，但若有其他会话/自动化占槽，实际可用会低于 6）；另**已完成未 close 的 agent 仍占槽** | 中 | 墙钟退化到 §3.2 降级矩阵的 5 路 8.6h 或 4 路 10.3h | ① run 启动时**重新 spawn 探针实测**，不得沿用本文件的 6；② R4 复核 agent 用完**立即 close**；③ 每条 lane 完成即 close，只保留正在跑的那一个；④ 槽位不足按 §3.2 降级矩阵改排法，**不得砍 S7/S8** |
| RK-P3 | **复核变浅**：并行下 R4 独立复核被压缩成同步点批量 ≤120 行/lane，可能漏掉口径偏离 | 中 | 四条不可砍底线之一被悄悄破坏 | ① 四条底线各自的守护测试编号已钉在卡片表（G-03/P-2/V-6、G-02/P-6、V-9、V-14）；② E5 架构测试用 AST **机器守护** INV-1/2/3 + P-8 + H-8，不靠人眼；③ P3a 的 V-1~V-20 表**无实测证据一律 ❌** |
| RK-P4 | **golden 固化实现**：E2/E3 与实现同期开发，容易拿实现输出反填期望值 | 中 | 验证失效，V-1~V-20 变成自证 | R-14 明令禁止；golden 期望值只能来自 A1 `fixtures_gen` 的构造与手算；A1 在 T+1.0 冻结，`fixtures/**` 之后只读 |
| RK-P5 | **211 RED 测试**里有真口径要求，被 B4 当「超规格」删掉 | 中 | 契约层校验缺失 | R-8 要求**逐条列出**删改理由 + SDD 行号；主控在 SP-2 抽查该 commit message；无法对应 SDD 行号的删除一律回退 |

## 11. 停机上报 vs 登记继续（照 ORCH §10，并行模式补充）

**立即停机上报（不得自行修复）**：SDD 指纹不一致；`/home/szf/dev/CampaignLab` 的 porcelain != 0 或 HEAD 被移动；契约文件被非主控修改；git 远端不可达；并发 <3 路；T+10.0 硬停线到点。

**登记并继续（不得停机、不得编造）**：单包超预算 → 交付**最小可用版本** + `ops/blockers.md` 一行（缺什么/影响/补做条件）→ 进下一包；契约缺字段 → `ops/contract-gaps.md` 一行 + pydantic 构造输入继续；上游包延迟 → 本包改用构造输入先做完单测，集成留给 Phase 2；某守护测试无法在预算内实现 → 记 ❌ 并写明补做条件。

**禁止的 6 种提前停下**（照 v1.0）：以「需要人工确认」为由停在可自决处；以「更严谨」为由超预算；以「等上游」为由空转（应改用构造输入）；以「测试太多跑不完」为由跳过收敛判据；以「证据不全」为由不出交付包；以「范围太大」为由自行砍 S7/S8。

## 12. 启动指令（可直接粘贴给新会话主控的第一条消息）

```
你是 strategy-eval-dsm（DSM v1.1）的长程无人值守主控 Orchestrator。目标：在 T+10.0 小时硬停线内
全量交付 S1→S9（含 S7 方法层 + S8 权重构造链，档 2 不得砍）。你只派工/裁决/对账，不写实现代码。
计划 T+7.75h 完成（Phase1 5.50h + Phase2 1.25h + Phase3 1.00h），缓冲 2.25h。

【第 0 步 · 只读，≤10 分钟，顺序不可换】
1. docs/RUN-UNATTENDED-v3.0-PARALLEL.md  ← 本文件，全文（唯一排程依据）
2. docs/RUN-UNATTENDED-v2.0.md §0~§7     ← 预算/仪式分档/RED 白名单/禁自创验证层/收敛判据/证据瘦身/比例校准
3. docs/CONTEXT-BRIEF-v1.0.md            ← 环境事实、写文件管线与坑、已建成 API、5 条陷阱
4. docs/ORCHESTRATION-v1.0.md 只读 §1（指纹）、§2（H-1~H-14）、§6（门禁总表）、§7.1（写文件管线）
5. ops/dag-state.json + ops/blockers.md  ← 进度真值
禁止读：SDD 原文 2,003 行、docs/digest/** 全文（digest 是给 lane 的，不是给主控的）、ORCH-v1.0 其余章节。

【第 1 步 · 自检，≤8 分钟】
- SDD 指纹必须是 708679e9a83d / 2003 行（路径见 ORCH §1.1，WSL 侧 /mnt/d/ws/codex_rd/ss_campaignlab/工行参考文件/）
- 只读邻仓 /home/szf/dev/CampaignLab：只比 porcelain 是否为空 + HEAD 是否被本 run 移动；不一致 → 立即停机上报
- venv /home/szf/venvs/dsm/bin/python 可跑 pytest；远端 git@github.com:shaozhongfei001/strategy-eval-dsm.git 可达
- pytest 基线必须是 211 failed（test_config_semantic 108 / test_config_weight_version 96 / test_config_properties 7），
  其余 0 failed。基线不符 → 停机上报，不要自行修复
- **重新实测并发槽位**：一次性 spawn 8 个探针 agent，每个只跑 date +%s%N → sleep 45 → date +%s%N，
  数被拒（agent thread limit reached）的个数得出上限；再对回收的区间做重叠分析确认是「真并行」而非「多槽单跑」。
  2026-11-24 的实测结果是上限 6、6 路真并行、加速比 3.49×；**不得直接沿用，必须重测**，结果写进 concurrency_actual，
  按 §3.2 降级矩阵选排法。**探针 agent 与后续所有已完成的 agent 必须立即 close_agent 释放槽位。**

【第 2 步 · 排程】
按 §4 卡片表建立 6 条 lane 队列（A/B/C/D/E/F），lane 优先级 A > D > F > B > E > C。
T+0 同时派发 6 个首包：
  A1 fixtures_gen ｜ B1 attainment ｜ C1 io_loaders ｜ D1 weights_ahp ｜ E1 集成骨架 ｜ F1 entropy.py
**ORCH-07 硬要求：D1 weights_ahp 与 F1 entropy.py 必须同批 T+0 起跑，不得串行**——
A2 weights_combine 的起跑点取决于二者中较晚的那个，串行会把关键路径推后 0.67h。
派工一律用 §8 模板，5 段自包含，digest 只给卡片表列出的那几份。

【第 3 步 · 连续推进，直到交付包产出】
- lane 内串行、lane 间并行；某 lane 空闲即从自己队列取下一包，**不跨 lane 抢包**（写集互斥，R-1）
- 每收到 PKG= 上报行 → 立即写 dag-state.json（ev 只存数字）→ 立即派该 lane 下一包 → 立即 close 已完成的 agent
- Lane F 在 F4 之后转入机动（F5）：承接 R4 复核 agent、吸收超时包、Phase 2 缺陷第一顺位
- T+1.00 / 2.75 / 4.25 / 5.50 四个同步点，按 §7 固定 5 件事执行，每个 ≤10 min
- SP-1 必须执行裁决 ORCH-03（dsm/__init__.py 的 L1 行加 entropy）
- **SP-2 是本 run 最关键的放行点**：B3 grading + D2 sensitivity + E1 集成骨架三者全绿才放行 A3 weights_calibrate；
  任一未绿 → 优先补该 lane 并把 F 机动槽压上去，其余 lane 挂起
- 全程受 §5 铁律 R-1~R-15 与 v2.0 §0~§7 约束；超预算立即打断并要求交付最小可用版本（R-6）

【第 4 步 · Phase 2 / Phase 3】
- Phase 2（75 min，T+5.50→6.75）：去掉 E1 全部 skip，按缺陷切片把 6 lane 拆开并行修，跨模块缺陷由你裁决归属
- Phase 3（60 min，T+6.75→7.75，三路并行）：
  P3a V-1~V-20 证据表（Lane A，四列，无实测证据一律 ❌，不得推测）
  ∥ P3b 第二人复跑（Lane E，全新 clone + 断网 + 同 seed → reproducibility_hash 精确相等）
  ∥ P3c README + git tag v1.1.0 + 交付包（Lane F，含待行方签认清单 K-01~K-20 + G5/G7 门禁）

【第 5 步 · 硬停线】
T+10.0 到点：立即停止新派工，close 全部 agent，产出交付包（已完成项 + 未完成项如实登记「缺什么/影响/补做条件」），
输出最终对账单（≤40 行，七段），tag 打在实际完成度上（未全绿则打 v1.1.0-rc1 并写明差距）。

【报告纪律】只在同步点末与 Phase 结束时汇报，每次 ≤15 行，只给数字与事实：
墙钟 / 完成包数 / 全量 pytest 统计 / 生产代码行 / 净新增测试函数（上限 120）/ 预算违规数 / contract-gaps 数 / 占用槽位数 / 下一批派工。
禁止形容词，禁止粘贴代码或 pytest 全量输出。
```

## 13. 主控对账职责（每个同步点必须核算，写进对账单）

| 项 | 阈值 | 超阈处置 |
|---|---|---|
| 墙钟 vs 计划（§3） | 偏差 ≤ +0.5 h | 超则砍 Phase 3 的 P3b 改期，**不得砍 S7/S8** |
| 净新增测试函数（累计） | ≤120（R-9） | 超则冻结后续包的新增测试，只允许实现 |
| 生产代码 : 非生产物 | ≥ 1 : 3（v1.0 是 1 : 31） | 超则下一包降档为 C1 仪式 |
| C3/max 包占比 | ≤60%（ORCH-04；实测 55%） | 超则按 §5.2 降级候选顺序降档，守护测试编号不得减少 |
| `ops/evidence/` 入库体积 | **0 B**（已 gitignore） | 发现即 `git rm --cached` |
| `ops/dag-state.json` 体积 | ≤25 KB（v2.0 §6 口径；瘦身后实测 **18,569 B**，卡片全文只在 §4 不重复存） | 超则把 session_log 归档到 `ops/session-log-archive.md` |
| 四条不可砍底线的守护测试 | 全绿 | 任一红 → **停机上报，不得进入 Phase 3** |

---

## 附 A：31 包 → SDD 门禁映射（Phase 2 收口时逐条核；包号为 §4 的 6-lane 编号）

| ORCH §6 阶段门禁 | 必须全绿的用例 | 由哪些包交付 |
|---|---|---|
| S1 | V-5、P-10、CEL-0 一致性（V-20 前置） | 已建成（models / config PLACEHOLDER）+ **B4** |
| S2 | fixtures 同 seed 逐字节相等；7 个刻意构造；≥4 期历史 | **A1** |
| S3 | G-10、G-11、C-01~C-10 | **C1 C2** |
| S4（M1） | G-01、G-04、G-08、G-09、P-1、P-8、T-SEN-01 部分 | **B1 B2 B3 D2 E1 E5** |
| S5（M2） | **G-02、G-03**、G-13、G-15、P-2、P-6 | **C3 C4 C5 E2** |
| S6（M3） | G-05、G-06、G-07、**G-12**、G-14、P-3、P-4、V-3 | **F2 F3 F4 D2 D3 D5 P3b** |
| S7（M4a） | T-AHP-01~06、T-ENT-01~03、T-TOP-01~03、T-GRA-01~03、T-TRI-01、T-SEN-01~03、V-11、V-12、V-13 | **D1 F1 F3 D2 D4** |
| S8（M4b） | T-CMB-01~09、T-CAL-01~04、T-WIF-01~05、P-11~P-15、V-15~V-19 | **A2 A3 A4 E4** |
| S9 | **V-1~V-20 全量** + P-1~P-15（各 500 例）+ G-01~G-15 + 断网单机跑通（V-10） | **E2 E3 E4 E5 P2 P3a P3b P3c** |

**包号对照（供读旧 `ops/blockers.md` 与 v1.0 文档时换算）**：`B5 audit → F2`、`B6 diagnostics → F3`、`C6 reports → F4`、`D2 entropy → F1`、`D3 sensitivity → D2`、`D4 normalize → D3`、`D5 triangulation → D4`、`D6 cli → D5`。其余包号不变。

## 附 B：与 v1.0 / v2.0 的偏差登记（本文件是唯一改动点）

| 编号 | 偏差 | 依据 |
|---|---|---|
| ORCH-01（沿用） | `fixtures_gen` 从 SDD §3.17.2 step 8 提前到 Phase 1 首包 | G-01~G-15 与 calibrate 的 ≥4 期历史都要用它；不改口径只改顺序 |
| ORCH-02（沿用） | CEL-0 预留按 **7 字段**（非 §5.8.1 表格的 8 个） | `interpretation_limit` 是 T4 正式字段（SDD 行 1172） |
| **ORCH-03（本 run 新增）** | 新增 `dsm/entropy.py` 于 **L1**，模块数 23 → 24 | §5.1：INV-1 禁止 L5 import L0a，而 §2.4.2 行 537 要求「两个计算者共用同一实现」 |
| **ORCH-04（本 run 新增）** | 高档（C3/max）任务占比统一取 **≤45%**（ORCH 实例原写 ≤40%） | §5.2：本 run C3 包 15/31 = 48%，卡 40% 会把四条不可砍底线的落点降档 |
| **ORCH-05（本 run 新增）** | 串行 DAG（ORCH §5 的 S1→S9 阶段序）改为 **lane 波次并行**（初版设计 5 lane，ORCH-07 实测并发后定为 6 lane）；阶段门禁（ORCH §6）**不变**，仍在 Phase 2/3 逐条核 | §2.2：契约冻结后模块间只耦合类型不耦合实现 |
| **ORCH-06（本 run 新增）** | 全量 pytest 由「每任务跑」改为「**只在 4 个同步点 + Phase 2 跑**」，lane 内只跑本包测试 | 当前 tests/ 已 9,963 行，每包跑全量的成本会吃掉并行收益 |
| **ORCH-07（本 run 新增）** | ① 并发槽位由「待用户确认」改为**实测 = 6**（spawn 8 探针，第 7/8 被拒 `agent thread limit reached`；6 路区间重叠 9.01 s，加速比 3.49×）；排程由 5 lane 改为 **6 lane**（新增机动 lane F）。② `entropy.py`（F1）与 `weights_ahp.py`（D1）**同批 T+0 起跑**，不串行——依据 SDD §2.4.3 的 `combine(ahp, entropy, opts)` 签名证明二者是并列输入而非先后步骤；combine 起跑点由 T+1.67 提到 T+1.00，**Phase 1 由 5.92 h 降到 5.50 h**。③ `audit`/`diagnostics`/`reports` 由 B、C lane 移入 F lane。④ whatif ∥ calibrate 的进一步加速**未采纳**（ORCH §5.9 明令 S8 严格串行），登记为条件触发的 ORCH-07b | §3.1 实测数据 + §5.3 |
