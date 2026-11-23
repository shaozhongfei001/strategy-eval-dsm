# ORCH-22：S1-T04 输出模型 / 8 个 Frame / ScoringContext 的契约裁决（含 AuditBundle 15 项口径）

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-24 |
| 阶段 / 任务 | S1 / S1-T04（L0 取证后、L1 RED 前） |
| 裁决人 | Orchestrator（主控） |
| 类型 | 契约裁决 + 原文沉默处的最小闭包裁决（ORCH §10.2-2 / §10.2-4） |
| 输入 | `docs/digest/S1-T04.md`（R1 本次取证，93 行）、`docs/digest/S1-T01.md`、`S1-T01c.md`、`S1-T01d.md`、`S1-T01e.md`、`docs/adr/ORCH-13.md`、`ORCH-15.md`、`ORCH-16.md`、`ORCH-21.md`、`docs/ORCHESTRATION-v1.0.md` 附录 ORCH-02/ORCH-03 |
| 效力 | 本 ADR 是 S1-T04 的**契约权威**。H-11 无人值守下由 R4 依「digest 原文行号 + 本 ADR」逐条判定，判定依据即本文件，视为签认 |

## 0. R1 取证纠正的 3 个事实（先于一切裁决）

1. **AuditBundle 是 15 项，不是 17 项。** `[L1051]` 原文以顿号分隔，R1 实测顿号 14 个 = 15 项。
   主控派工预研写的「17 项」是把第 9 项（8 张输入表的 SHA256 与行数）与第 10 项（输出文件清单与 SHA256）
   各拆成两项的**拆分口径**，不是原文口径。按 ORCH 卷首「与 SDD 冲突时一律以 SDD 为准」→ **按 15 项建模**。
2. **§3.11.3 `[L1218]-[L1226]` 不给逐表字段清单**，只有「输出 / 格式 / 一行代表什么 / 谁看 / 用来做什么」五列。
   字段清单的原文出处是 §4.6（`[L1608]-[L1640]`）与 §3.7（`[L1018]`/`[L1028]`/`[L1040]`），已在 `S1-T01d.md`。
   → **各输出模型的 grain 取 `[L1220]-[L1226]` 的「一行代表什么」列逐字**（见裁决 21/24/27）。
3. **`[L1040]` 的字段名是 `metric_code` 而不是 `metric_id`**（其余全篇用 `metric_id`，见 `[L1130]`/`[L1180]`/`[L1149]`）。
   按 ORCH-16 裁决 1「保留 SDD 逐字字段名，不重命名」→ **EntropyDiagnosticRow 用 `metric_code`**，不做「统一美化」。

## 1. AuditBundle（依据 `[L1050]-[L1055]`）

### 裁决 14：15 项 → 16 个字段的逐条映射表

第 11 项「启用的敏感性方案与 seed」含两个独立数据，落 2 个字段；其余 14 项各落 1 字段，共 **16 字段**。
SDD 给的是中文描述而非英文字段名，故下表是**命名映射裁决**，R4 按此逐条核对，不得自行改名。

| # | `[L1051]` 原文项（逐字） | 字段名 | 类型 | 依据 |
|---|---|---|---|---|
| 1 | run_id | `run_id` | str | [L1051]、[L1091] 重跑生成新 run_id 目录 |
| 2 | run_at（由 CLI 注入） | `run_at` | datetime | [L1051]、[L1089] --run-at、[L1271] 禁计算层调系统时钟（H-8） |
| 3 | period | `period` | str | [L1051]、[L1089]、[L1149] |
| 4 | dsm_version | `dsm_version` | str | [L1051] |
| 5 | design_version | `design_version` | str | [L1051] |
| 6 | cel_contract_version | `cel_contract_version` | str | [L1051]、[L1897] |
| 7 | weight_version_id | `weight_version_id` | str | [L1051]、[L1190] |
| 8 | config 全量快照的 SHA256 | `config_snapshot_sha256` | str | [L1051] |
| 9 | 8 张输入表的 SHA256 与行数 | `input_fingerprints` | InputFingerprints | [L1051]、[L888]、[L891]（裁决 15） |
| 10 | 输出文件清单与 SHA256 | `output_fingerprints` | dict[str, str] | [L1051]（键=文件名，值=SHA256；原文未给字节数，故不加） |
| 11a | 启用的敏感性方案 | `sensitivity_schemes` | tuple[SchemeName, ...] | [L1051]、[L1015]（裁决 18） |
| 11b | seed | `seed` | StrictInt \| None = None | [L1051]、[L1089]、[L1270] 未设 seed 拒跑 MC |
| 12 | preflight findings 全量 | `preflight_findings` | tuple[PreflightFinding, ...] | [L1051]、[L1063]⑩（裁决 16） |
| 13 | 降级动作全量 | `downgrade_actions` | tuple[DowngradeAction, ...] | [L1051]、H-6（裁决 17） |
| 14 | exit_code | `exit_code` | StrictInt | [L1051]、[L1080]-[L1087]（退出码集合按命令而异，models 层不封闭） |
| 15 | reproducibility_hash | `reproducibility_hash` | str | [L1051]、[L1052] |

全部 16 字段**必填无默认**，只有 `seed` 可空（`[L1270]` 明示未设 seed 是合法状态，只是不能跑 MC）。
SHA256 类字段在 models 层**只声明为 str，不加 64 位十六进制格式校验器**——格式校验属 audit.py（S6），
在契约层加正则等于发明 SDD 未写的约束。

### 裁决 15：InputTableFingerprint / InputFingerprints 共用一个定义，且**不封闭键集**

- `InputTableFingerprint`：`sha256: str`、`row_count: StrictInt`（计数走 int，H-4）。依据 `[L888]`「每文件算 SHA256 与行数 → InputFingerprints」。
- 类型别名 `InputFingerprints = dict[str, InputTableFingerprint]`。**AuditBundle 与 ScoringContext 共用这一个定义**，
  即 ORCH-13 裁决 1 A 组的 `input_fingerprints: InputFingerprints` 就是本类型，不得各建一份。
- **键集不封闭**（不写成恰好 8 键）：`[L877]` 的配置文件名里有 `weights_*.yaml` 这样的**通配写法**，
  `[L888]` 又按 `data/<period>/` 与 `config/` 两个目录取文件，"哪些文件参与指纹"由 io_loaders（S3）决定。
  在 models 层封闭键集会让 S3 每加一个文件都成为破坏性契约变更。理由与 ORCH-20 裁决 7（B-016）同源。

### 裁决 16：PreflightFinding 取 3 字段最小闭包，severity 复用既有单一事实源

`PreflightFinding`：`code: str`、`severity: Severity`、`message: str`。
- `severity` **必须**用 `dsm.reason_codes.Severity`（S0 基线已存在，实测成员 = INFO / WARN / BLOCK），**不得新建枚举**（H-7 单一事实源精神）。
- `code` 是**门禁/校验编号**（如 `[L900]` 的 C-01、G-01~G-15），不是 reason_code，故用 str 而非 `ReasonCode` 注解。
- finding 的完整结构（作用对象、证据行号、建议动作）SDD 未给 → 登记 **B-019**，转 S3 preflight 任务；
  届时若需扩字段，按 `[L1902]` 的预留理由由主控再裁决，不在本任务预建。

### 裁决 17：DowngradeAction 是 H-6 在数据结构上的落点

`DowngradeAction`：`reason_code: ReasonCode`（**必填**）、`action: str`、`subject: str | None = None`。
- H-6「任何降级、回退、剔除、封顶都必须带 reason_code 且出现在报告中」→ `reason_code` 必填且走 `ReasonCode` 注解
  （只接受已注册 `RC.<NAME>`，裸字符串字面量在构造时即 ValidationError，H-7）。
- `subject` = 降级作用对象（strategy_id / metric_id / period 之类标识），可空。
- `[L1054]`「任何命令失败都必须写 audit_bundle」是**行为**约束，属 cli/audit 层，models 层不建字段。

### 裁决 18：SchemeName 落地

`SchemeName = Literal['OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP']`（`[L1015]` 逐字，5 值封闭）。
`S1-T01d.md` 已把它记为「签名内出现但 SDD 未定义字段的辅助类型名」，本任务落地为 Literal。

## 2. 输出模型（6 个，`[L867]`）

### 裁决 19：StabilityLabel 取 ORCH-03 的三值

`StabilityLabel = Literal['STABLE', 'NEAR_BOUNDARY', 'UNSTABLE']`。
`[L1018]` 写 `BOUNDARY`，但 `[L1624]` 与 `reason_codes.py` 已注册的是 `NEAR_BOUNDARY`；
ORCH 附录 ORCH-03 已裁决统一取 `{STABLE, NEAR_BOUNDARY, UNSTABLE}`（语义不变）。
实测三值均已注册为 RC 成员，severity 分别 = INFO / WARN / WARN。

### 裁决 20：新增 FrameGrade，**不得放宽既有 GradeCode**

`FrameGrade = Literal['L1', 'L2', 'L3', 'L4', 'NOT_ASSESSED']`（`[L964]` 逐字 5 值）。
- 用于 `GradeRow.grade`（`[L964]`）与 `ScoreCardRow.grade`（`[L1620]`）。
- 既有 `GradeCode = Literal['L1','L2','L3','L4']`（`[L1200]`）**保持 4 值不动**：它是 T7 grade_rules 的等级码，
  `GradeRuleRow.grade_code` 与 `GradeRuleRow.max_grade_if_no_target` 专用。把 NOT_ASSESSED 塞进 GradeCode
  会让 T7 出现「门槛挂在 NOT_ASSESSED 上」这种无意义行，属契约污染。
- `NOT_ASSESSED` 已注册为 RC 成员（实测 severity=BLOCK，describe=「该策略本期不可评价，不出分，在台账单独计数」）。

### 裁决 21：ScoreCardRow —— grain 与 35 个字段

grain 取 `[L1220]` 逐字「一条策略在一个评价期的完整评分明细」→ 定位键 = strategy_id / version_id / period
（`[L1149]` 四元键去掉 metric_id，因为 metric 维度由 `per_metric` 承载）。

| 段 | 字段 | 类型 | 依据 |
|---|---|---|---|
| 定位键 | `strategy_id` / `version_id` / `period` | str | [L1149]、[L1220] |
| [L1612] 版本四元组 | `weight_version_id` / `dict_version` / `anchor_set_id` / `run_id` | str | [L1612]「这个分数是哪套规则算出来的，申诉与复跑第一入口」；[L955] 权重版本 id 必须写入每一行 |
| [L1613] | `per_metric` | dict[str, ScoreCardMetricCell] | 键=metric_id；「实际值/目标值/达成率三列并排」「全部保留、不做黑箱」（裁决 23） |
| [L1614] | `per_dim` | dict[str, ScoreCardDimCell] | 键=dim_code（[L1131]）；「各维度达成率、相对分、coverage、W」（裁决 23） |
| [L1615] | `composite_absolute` | Ratio \| None = None | 主分数，用于定级。**可空**：[L964] 与 RC.NOT_ASSESSED 明示「不出分」，强制必填会迫使为不可评价策略编造分数（逻辑同 ORCH-21 裁决 9） |
| [L1616] | `composite_relative` | Ratio \| None = None | 辅分数，仅同池排名，不能判达标；同上可空 |
| [L1617] | `evidence_class` | EvidenceClass | 必填：[L977]① 设计卡缺失也判 D，任何策略都有证据等级 |
| [L1617] | `evidence_reason` | ReasonCode | 必填，[L982] 三码之一 |
| ORCH-15 | `evidence_source` | EvidenceSource | **本任务必须落地**：[L870]/[L980]，ORCH-15 明示「属 S1-T04：ScoreCardRow 输出模型须含 evidence_source」 |
| [L1618] | `interpretation_limit` | str \| None = None | C 类必填的**规则**属 evidence/grading 层（[L977]⑤），models 层只建可空列 |
| [L1619] | `redline_pass` | StrictBool | 「踩线时分数照算但不生效，等级强制」 |
| [L1619] | `redline_flags` | tuple[ReasonCode, ...] = () | 同上；REDLINE_HARD_HIT / REDLINE_SOFT_HIT / WAIVER_* |
| [L1620] | `grade` | FrameGrade | 裁决 20 |
| [L1620] | `grade_reason_codes` | tuple[ReasonCode, ...] | **逐字用 `grade_reason_codes`**（[L1620]），不改成 GradeFrame 的 `grade_reason_path`（[L964]）——两处原文名字不同，按 ORCH-16 裁决 1 各自保名 |
| [L1621] | `capped_flag` | StrictBool | 无目标值/证据 C 封顶 |
| [L1621] | `cap_reason` | ReasonCode \| None = None | 未封顶时为 None |
| [L1622] | `ranking_pool` | PoolKey \| None = None | 池=业务领域×证据等级（[L1001]）。可空：[L1004] NOT_ASSESSED 单独计数、不进池 |
| [L1622] | `rank_in_pool` | StrictInt \| None = None | 计数走 int（H-4）；同上可空 |
| [L1622] | `pool_size` | StrictInt \| None = None | 同上 |
| [L1623] | `eligible_for_L1_library` | StrictBool | 字段名逐字含大写 L1，Python 标识符合法，不改写 |
| [L1623] | `l1_gate_reasons` | tuple[ReasonCode, ...] = () | PRIMARY_POOL_REJECTED_EVIDENCE / PRIMARY_POOL_REJECTED_ROBUST（[L1005]） |
| [L1624] | `stability_label` | StabilityLabel \| None = None | 裁决 19。可空：敏感性未跑时无标签 |
| [L1624] | `flip_under_pct10` | Ratio \| None = None | 逐字名（[L1624] 写作 flip_under_pct10/20） |
| [L1624] | `flip_under_pct20` | Ratio \| None = None | 同上 |
| [L1625] | `usable_for_elimination` | StrictBool | 受 flip_rate 与方法分歧双重约束；[L1064] 首屏第一段必须写它 |
| [L1626]/[L1896] | `incremental_value` | FactValue \| None = None | CEL-0 点估计；**unit 多态**故用 FactValue 且**保留逐字名不加 _minor**（裁决 22） |
| [L1626]/[L1896] | `incremental_ci_lower` | FactValue \| None = None | CEL-0 区间下界 |
| [L1626]/[L1896] | `incremental_ci_upper` | FactValue \| None = None | CEL-0 区间上界 |
| [L1626]/[L1896] | `estimator_method` | str \| None = None | CEL-0 方法 |
| [L1896] | `value_captured_minor` | MoneyMinor \| None = None | **裁决 22**：本字段加 `_minor` 后缀 |

合计 **35 字段**。`[L1626]`「首版恒为空，报告显式写『本期末接入增量估计』，不得静默留白」——
"报告显式写"是 reports 层行为（S6），models 层只保证 5 个 CEL-0 字段默认 None。

### 裁决 22：`value_captured` 加 `_minor` 后缀；CEL-0 增量三列不加（消解 ORCH-16 裁决 1 与裁决 2 的冲突）

ORCH-16 裁决 1 说「保留 SDD 逐字字段名，不加 `_minor`」，裁决 2 又说「后续阶段若出现纯金额列
（**例如 value_captured 的金额形态**）必须加 `_minor` 后缀」。两者在 value_captured 上正面冲突。裁决如下：

- **`value_captured` → `value_captured_minor`**（类型 `MoneyMinor | None = None`）。理由：
  ① ORCH-16 裁决 2 已**点名**本字段；② 裁决 1 的**理据**是「这些列是 unit 多态列，静态加 `_minor`
  会错误宣称这列永远是钱，对 unit=RATIO 的指标反而是错误信息」——value_captured **不是**多态列，
  `[L1896]` 的语义就是已捕获价值（金额），故裁决 1 的理据在此不适用；③ H-4 是不可协商硬约束，明写「后缀 `_minor`」；
  ④ ORCH-16 裁决 3 已确立「金额语义由类型与校验器保证」，此处类型（MoneyMinor）与字段名后缀一致，是最强形态。
- **`incremental_value` / `incremental_ci_lower` / `incremental_ci_upper` 保留逐字名、不加后缀**，类型 `FactValue | None`
  （= `MoneyMinor | Ratio`，与 DesignCardRow `[L1174]` 已落地形态一致）：它们是 **unit 多态**列，正落在裁决 1 的理据内。
- **由此确立全项目边界（对 ORCH-16 的补充，后续阶段一律照此判定）**：
  **多态列保 SDD 逐字名；纯金额列加 `_minor` 后缀。** 判据 = 该列的静态类型是联合（含 Ratio）还是纯 `MoneyMinor`。

### 裁决 23：per_metric / per_dim 用嵌套子模型，不扁平化成前缀列

`[L1613]`「实际值/目标值/达成率三列并排」+「全部保留、不做黑箱」，`[L1614]`「各维度达成率、相对分、coverage、W」
都是**逐指标 / 逐维度的多列**，扁平化成 `metric_X_actual` 这类前缀列会破坏 `[L1272]`「字典/集合排序后遍历」
与 `[L1053]` 规范化序列化的可复现性，且指标集是配置驱动的（`[L1131]` dim_code 不硬编码枚举，D7）。故：

- `ScoreCardMetricCell`（3 字段）：`actual_value: FactValue`（与 MetricFactRow.value `[L1150]` 同型）、
  `target_value: UnitValue | None = None`（ORCH-14 的 unit 多态，与 MetricDictRow.target_value 同型）、
  `attainment: Ratio | None = None`（**可空依据 `[L930]`「目标值缺失→attainment=null（不得用均值代替）」**）。
- `ScoreCardDimCell`（4 字段）：`attainment: Ratio | None = None`、`relative_score: Ratio | None = None`、
  `coverage: Ratio`、`weight: Ratio`（`[L1614]` 的 W 即维度权重 W_d，`[L879]`/`[L1192]`）。
- 容器一律 `dict[str, <Cell>]`，键为 metric_id / dim_code；`[L1053]`③ 要求序列化前按 key 显式排序（属 audit 层行为）。

### 裁决 24：GradeLedgerRow —— recommended_action 与 decided_action 必须分两列

grain 取 `[L1221]` 逐字「一条策略的等级变更与应执行动作」。

| 字段 | 类型 | 依据 |
|---|---|---|
| `strategy_id` / `version_id` / `period` | str | [L1149]、[L1221] |
| `grade` | FrameGrade | [L1620]/[L964]，裁决 20 |
| `previous_grade` | FrameGrade \| None = None | **[L1221]「等级变更」**必须有 from→to；[L890] 上期 grade_ledger 缺失按 FIRST_PERIOD 处理 → 故可空 |
| `recommended_action` | str \| None = None | **[L1630] 分两列之一**；V-8 逐字判据见 [L1863]「grade_ledger 的 recommended_action / decided_action 双字段」。模型只给建议 |
| `decided_action` | str \| None = None | **[L1630] 分两列之二**；人做决定并签字 |
| `decision_note` | str \| None = None | [L1630]「两者不一致时必须写 decision_note」。**一致性校验属 grading/reports 层**，models 层只建列（L2 最小实现） |
| `owner_dept` / `owner_name` | str \| None = None | [L1632] 三级策略必须有；[L1122] T1 已有同名列 |
| `deadline` | date \| None = None | [L1632]；ISO 日期用 date 类型（与 [L889] 及既有 approved_date 同型） |
| `archive_ref` | str \| None = None | [L1633] 四级退出必须有 |
| `ledger_complete` | StrictBool | [L1634]「缺项在报告中标记为台账不完整」的**载体**；标记逻辑属 reports 层 |
| `usable_for_elimination` | StrictBool | **[L1019] 逐字「写 grade_ledger.usable_for_elimination=false」** |

`[L1631]`「各级动作逐字取自分册 A 第三章（七）」→ action 类字段一律 `str`，
**models 层不得拟定任何动作文案**（H-5：不拟业务内容；分册 A 是 7 份只读文档之一，本任务未授权摘取）。
`recommended_action` / `decided_action` / `decision_note` 全部可空正是为此：强制必填会迫使编造文案。

### 裁决 25：SensitivityReport 是报告级模型（不是行模型）

`[L1222]` grain =「一次扰动方案下的等级翻转情况」，`[L1018]` 要求同时装「逐方案 overall_flip_rate」
与「每策略 stability 标签」两个粒度 → 一个模型装不下同一粒度，故用**报告级容器 + 两种子行**：

| 字段 | 类型 | 依据 |
|---|---|---|
| `by_scheme` | tuple[SensitivitySchemeResult, ...] | [L1018]「overall_flip_rate（逐方案）」 |
| `by_strategy` | tuple[SensitivityStrategyRow, ...] | [L1018]「每策略 stability 标签」 |
| `loo_dominant_metrics` | tuple[str, ...] = () | [L1018]「LOO 主导指标清单」 |
| `norm_swap_rank_correlation` | Ratio \| None = None | [L1018]「NORM_SWAP 秩相关」；Spearman 值域 [-1,1]，Ratio 无上界（ORCH-21 已确认这是正确的） |
| `flags` | tuple[ReasonCode, ...] = () | [L1020] LOO_SAMPLED 的标注载体 |
| `seed` | StrictInt \| None = None | [L1017]/[L1270]；「未设 seed 抛 SeedRequiredError」是 sensitivity.py（S6）的**行为**，models 层只建列 |

- `SensitivitySchemeResult`：`scheme: SchemeName`、`overall_flip_rate: Ratio`、
  `flipped_count: StrictInt`、`assessed_count: StrictInt`、`flag: ReasonCode | None = None`。
  **两个 count 是本裁决新增**（`[L1018]` 只写 overall_flip_rate）：一个不可还原分子分母的比率不可辩护
  （`[L1613]`「全部保留、不做黑箱」的精神 + `[L1052]` reproducibility_hash 要能复算）。
  `flag` 承载 `[L1019]` 的 FLIP_RATE_REVIEW / FLIP_RATE_UNUSABLE（实测均为已注册 RC）。
- `SensitivityStrategyRow`：`strategy_id: str`、`version_id: str`、`stability_label: StabilityLabel`、
  `flip_under_pct10: Ratio | None = None`、`flip_under_pct20: Ratio | None = None`。
  两个 flip 列在此**必须**存在：`[L1624]` 的 ScoreCardRow 同名两列要有来源，否则 score_card 的数无处可来。
- `[L1019]`「报告首屏声明不得用于淘汰」是 reports 层行为（`[L1064]`），models 层不建字段。

### 裁决 26：TriangulationReport 是报告级模型

`[L1224]` grain =「三种方法排序的一致性」。

| 字段 | 类型 | 依据 |
|---|---|---|
| `rows` | tuple[TriangulationStrategyRow, ...] | [L1028] topsis_rank / gra_rank 是逐策略的 |
| `rho_main_topsis` | Ratio \| None = None | [L1028] 逐字 ρ_main_topsis；希腊字母 ρ 非合法 Python 标识符，取 ASCII 规范映射 rho_ |
| `rho_main_gra` | Ratio \| None = None | [L1028] ρ_main_gra |
| `rho_topsis_gra` | Ratio \| None = None | [L1028] ρ_topsis_gra |
| `mean_rho` | Ratio \| None = None | [L1028] mean_ρ |
| `agreement` | MethodAgreement \| None = None | [L1028] 逐字 {METHOD_AGREEMENT, METHOD_DIVERGENCE}；实测两者均为已注册 RC |
| `gra_by_metric` | dict[str, Ratio] | [L1028]「逐指标 GRA 平均关联度」，键=metric_id |
| `flags` | tuple[ReasonCode, ...] = () | **[L1030]「triangulation.enabled=false→跳过并记 TRIANGULATION_DISABLED（不得静默）」**的载体 |

- `TriangulationStrategyRow`：`strategy_id: str`、`version_id: str`、`topsis_rank: StrictInt`、`gra_rank: StrictInt`（计数走 int，H-4）。
- `MethodAgreement = Literal['METHOD_AGREEMENT', 'METHOD_DIVERGENCE']`。
- 4 个 rho 与 agreement **全部可空**：`[L1030]` 允许整体跳过，强制必填会迫使编造相关系数（同 ORCH-21 裁决 9 逻辑）。
- `[L1029]`「不产出任何可对外披露排名」（RK-5）是**行为**约束，属 triangulation/reports 层；models 层只写进 docstring，不加字段。

### 裁决 27：EntropyDiagnosticRow 严格按 `[L1040]` 的 9 字段 + 1 个 B-018 载体

grain 取 `[L1223]` 逐字「一个指标的健康状况与建议动作」。

| 字段 | 类型 | 依据 |
|---|---|---|
| `metric_code` | str | **[L1040] 逐字 metric_code**（不是 metric_id，见 §0 第 3 条） |
| `e_j` | Ratio | [L1040] 熵值 |
| `d_j` | Ratio | [L1040] 差异系数 |
| `cv_j` | Ratio | [L1040] 变异系数 |
| `vif_j` | Ratio \| None = None | [L1040]；可空因单指标时相关矩阵求逆无定义（H-4「on_zero 可为 None 表示真未定义」同源逻辑） |
| `max_abs_corr` | Ratio \| None = None | [L1040]；同上 |
| `status` | EntropyStatus | [L1040] 逐字 4 值 {OK, LOW_VARIATION, INACTIVE, COLLINEAR}，**封闭，不得加第 5 值** |
| `suggested_action` | ReasonCode \| None = None | [L1040]/[L1041]「必须落 CSV」；值域为已注册 RC（实测 RETIRE_OR_REDLINE / MERGE_OR_DROP / REDEFINE / CONTENT_VALIDITY_DOUBT 四码正是诊断建议动作），走 ReasonCode 注解以满足 H-7 |
| `owner` | str | [L1040]/[L1041]；来源是 T2 的 owner_name（[L1141]），恒有值故必填 |
| `flags` | tuple[ReasonCode, ...] = () | **B-018 的载体**：[L1777] RK-13「drift 超阈值指标标注 ENTROPY_UNSTABLE」。实测 ENTROPY_UNSTABLE 已注册（severity=WARN） |

- `EntropyStatus = Literal['OK', 'LOW_VARIATION', 'INACTIVE', 'COLLINEAR']`。
- **为什么不把 ENTROPY_UNSTABLE 塞进 status**：ORCH-21 裁决 10 已判定「`[L1040]` 的 status 是封闭 4 值」，
  加第 5 值会同时违反 `[L1040]` 逐字清单与 ORCH-20 裁决 3 确立的「按原文推得的字段/枚举封闭」原则。
  标注是**可叠加**的（一个指标可以同时 INACTIVE 且 drift 超阈值），故用 `flags` 元组而非枚举值。
- **语义与阈值不在本任务**：何时置 ENTROPY_UNSTABLE、阈值取多少（K-16 drift_budget，PLACEHOLDER）归 S8-T01（B-018）。
- `[L1038]`「在线熵权只写诊断表，绝不回写权重」（INV-3）与 `[L1042]`「类型隔离+调用隔离」是**行为**约束，
  由 S9-T02 的 `tests/test_architecture.py` 守护，models 层写进 docstring。

## 3. 8 个中间 Frame + PoolStats（`[L868]`）

### 裁决 28：Frame 一律**行式**建模

理由：① `[L1149]` 四元定位键 + `[L1156]`「长表语义：缺哪个指标是缺行而不是空列」；
② `[L1053]` 规范化序列化五规则要求可排序、可复现，而 pydantic 的 dict 键必须是可哈希的标量，
复合键（strategy_id, metric_id）无法直接做 dict 键；③ 行式与 CSV 载体（`[L1220]-[L1223]`）同构。

- 每个 Frame = 一个 `frozen=True, extra=forbid` 模型，含 `rows: tuple[<XxxRow>, ...]` + 原文明说的聚合字段。
- 子行模型命名：`AttainmentRow` / `NormalizedRow` / `EvidenceRow` / **`RedlineEvalRow`** / `ScoreRow` / `GradeRow` / `PoolRow`。
  ⚠ **`RedlineRow` 已被 T5 输入表（`[L866]`，S1-T02 已落地）占用，RedlineFrame 的行模型不得复用该名字**，
  取 `RedlineEvalRow`（evaluate 的语义来自 `[L988]` 签名 `evaluate(...)`）。
- **有序列一律 `tuple[...]`，无序映射才用 `dict[...]`，全项目禁用 `set` / `frozenset`**：
  `[L1053]`③④ 要求可复现遍历序，而 Python 的 str 哈希受 PYTHONHASHSEED 随机化影响，
  `set[str]` 的遍历序跨进程不稳定，直接威胁 `[L1052]` reproducibility_hash 与 V-3「第二人复跑精确相等」。

| 模型 | 字段 | 依据 |
|---|---|---|
| `AttainmentRow` | strategy_id / version_id / period / metric_id: str；attainment: Ratio \| None = None；direction: MetricDirection；target_source: str \| None = None；has_target: StrictBool；capped_flag: StrictBool；reason_code: ReasonCode \| None = None | [L928] 逐字段；attainment 可空依 [L930]「目标值缺失→attainment=null（不得用均值代替）」；direction 用既有 MetricDirection（[L1137]）；target_source 对应 [L1139] target_basis；reason_code 承载 [L931] 三码 |
| `AttainmentFrame` | rows: tuple[AttainmentRow, ...]；attainment_coverage: dict[str, Ratio] | [L928]「逐策略 attainment_coverage（=有目标值指标数/签认指标数）」，键=strategy_id。**分母是"签认指标数"**（[L1141] PENDING/REJECTED 不参与评分）——该计算属 attainment.py（S4），models 层只建列 |
| `NormalizedRow` | strategy_id / version_id / period / metric_id: str；pool_key: PoolKey；norm_value: Ratio；method: NormalizationMethod；anchor_used: StrictBool；reason_code: ReasonCode \| None = None | **ORCH-13 裁决 2 逐字采纳**：定位键 [L1149]、pool_key [L942]、norm_value [L940]、method [L940]、anchor_used [L941]、reason_code [L944] 四码 |
| `NormalizedFrame` | rows: tuple[NormalizedRow, ...] | [L945]「输出只用于排名与相对轨综合分，不得进入等级门槛判定」是行为约束（P-1/G-01 守护），写 docstring |
| `EvidenceRow` | strategy_id / version_id: str；evidence_class: EvidenceClass；evidence_reason: ReasonCode；evidence_source: EvidenceSource；control_group_id: str \| None = None；interpretation_limit: str \| None = None | **[L980] 逐字 5 字段** + 定位键。evidence_source 依 ORCH-15「属 S5-T01：EvidenceFrame 须含 evidence_source」——本任务建 Frame 时一并落地 |
| `EvidenceFrame` | rows: tuple[EvidenceRow, ...] | [L977] 判定顺序、[L979] 关键词清单、[L981] 单向调用属 evidence.py（S5） |
| `RedlineEvalRow` | strategy_id / version_id / period / metric_id: str；level: RedlineLevel；comparator: Comparator；threshold_value: UnitValue；hit: StrictBool；forced_grade: GradeCode \| None = None；waiver_approval_id: str \| None = None；waiver_valid_from: date \| None = None；waiver_valid_to: date \| None = None；waiver_scope: str \| None = None；soft_deduction: Ratio \| None = None；reason_code: ReasonCode \| None = None | **ORCH-13 裁决 2 逐字采纳**（metric_id [L988]、level [L989-990]、comparator/threshold_value [L1181]、hit、forced_grade [L989]、四个 waiver 字段 [L991]、soft_deduction [L990]、reason_code [L993]）。`forced_grade` 用 **GradeCode 而非 FrameGrade**：红线强制的是 L1~L4 中的某级（[L989] 原文默认 L4），不会是 NOT_ASSESSED |
| `RedlineFrame` | rows: tuple[RedlineEvalRow, ...] | 非补偿语义（[L1870] P0-2 红线非补偿）属 redline.py（S5，G-03 守护） |
| `ScoreRow` | strategy_id / version_id / period: str；composite_absolute: Ratio \| None = None；composite_relative: Ratio \| None = None；dim_absolute: dict[str, Ratio]；dim_relative: dict[str, Ratio]；coverage: Ratio；weight_version_id: str；operator: ScoreOperator | [L952] 逐字：composite_absolute / composite_relative / 逐维度 dim_d（**两轨各一套** → dim_absolute + dim_relative）/ coverage / weight_version_id / operator。[L955] INV-3「权重版本 id 必须写入每一行 score_card」→ 故 weight_version_id 在**行**上必填 |
| `ScoreFrame` | rows: tuple[ScoreRow, ...] | [L953] ScoreOperator = Literal['LINEAR','GEOMETRIC','NON_COMPENSATORY']（逐字，NON_COMPENSATORY 默认不启用属 aggregate 层）；[L954] 权重重归一 + WEIGHT_REALLOCATED 属 aggregate（S4） |
| `GradeRow` | strategy_id / version_id / period: str；grade: FrameGrade；grade_reason_path: tuple[ReasonCode, ...]；capped: StrictBool；cap_reason: ReasonCode \| None = None；action: tuple[str, ...] \| None = None；usable_for_elimination: StrictBool | **[L964] 逐字 6 项**：grade（裁决 20）、grade_reason_path（有序 reason_code 列表，可还原判定路径）、capped、cap_reason、action（各级应执行动作与期限）、usable_for_elimination。`action` 用 tuple[str,...] \| None，**不拟文案**（同裁决 24） |
| `GradeFrame` | rows: tuple[GradeRow, ...] | [L965] 滞回参数（upgrade_consecutive_periods 原文默认 2 / demotion_immediate 原文默认 true / 红线单期即降）是**治理数值**，H-5 一律 PLACEHOLDER，归 config（S1-T05/T06）；[L966] VERSION_BREAK 与 [L968]「等级判定只看绝对轨」属 grading（S4/S5） |
| `PoolRow` | strategy_id / version_id / period: str；pool_key: PoolKey；pool_rank: StrictInt \| None = None；primary_pool_eligible: StrictBool；reject_reason: ReasonCode \| None = None | **[L1006] 逐字 4 字段** + 定位键。pool_rank 可空：[L1004] NOT_ASSESSED 不计入分母、不进排名 |
| `PoolFrame` | rows: tuple[PoolRow, ...] | [L1002] 一级库门禁四条件属 pooling（S5，G-02 守护） |
| `PoolStatRow` | pool_key: PoolKey；count: StrictInt；share_in_pool: Ratio；share_overall: Ratio | [L1006]「各池计数、占比双报（池内占比+合并占比）」；[L1003]「禁止只报合并占比」→ **两个占比字段必须并存**，缺一个即违反 [L1003] |
| `PoolStats` | rows: tuple[PoolStatRow, ...]；evidence_structure: dict[EvidenceClass, StrictInt]；not_assessed_count: StrictInt；not_assessed_reasons: dict[str, StrictInt] | [L1006]「证据结构（A/B/C/D 计数 [L1003]）」→ 键封闭为 EvidenceClass 四值（这是 SDD 逐字给的封闭集，与裁决 15 的开放键集不同）；[L1004]「NOT_ASSESSED 单独计数、不计入分母、显式列出条数与原因分布」→ not_assessed_count + not_assessed_reasons（键=原因标识，值为条数，计数走 int，H-4） |

### 裁决 29：PoolKey 是 2 字段的 frozen 子模型，三处共用

`PoolKey`：`biz_domain: str`（`[L1119]`「分池的第一维」）+ `evidence_class: EvidenceClass`。
依据 `[L1001]` 逐字「pool_key = (biz_domain, evidence_class)」。
`NormalizedRow` / `PoolRow` / `ScoreCardRow.ranking_pool` **共用这一个定义**，不得各建一份。
`[L1001]`「禁止跨池混排」（P-6 与 G-02 守护）是行为约束，属 normalize/pooling 层。

**池内占比的精确分母原文未给**：`[L1006]` 只写「占比双报（池内占比+合并占比）」，`[L1003]` 只写「禁止只报合并占比」。
按 §10.2-2「保守超集」→ **两列都建**，精确分母语义由 S5 pooling 任务定，登记 **B-020**。

## 4. ScoringContext（ORCH-13 裁决 1 的补充）

### 裁决 30：A 组补 `run_id`，共 8 字段；`run_at` 类型统一为 datetime

ORCH-13 裁决 1 的 A 组（运行上下文）7 项**全部保留**，追加第 8 项：

| 字段 | 类型 | 依据 |
|---|---|---|
| `period` | str | [L1089] --period、[L1149] |
| `run_at` | **datetime** | [L1089] --run-at、[L1271] 禁调系统时钟（H-8）。⚠ ORCH-13 写作「str(ISO)」，本裁决统一为 `datetime`，与 MetricFactRow.snapshot_time（[L1152]，已落地为 datetime）同型；**仅类型记法修正，语义与依据行号不变** |
| `run_id` | str | **本裁决新增**：[L1051] AuditBundle 第 1 项、[L1612] score_card 版本四元组含 run_id、[L1091]「重跑生成新 run_id 目录，不覆盖历史」。run_id 是运行上下文值，由 CLI/audit 注入；不在 base 上下文里，[L1016]「Step 1-4 结果在所有方案间复用」就无法把它带给 SensitivityReport |
| `seed` | StrictInt \| None = None | [L1089]、[L1017]/[L1270] 未设 seed 拒跑 MC |
| `weight_version_id` | str | [L1190]、[L955] |
| `evidence_mode` | EvidenceMode | [L978] 默认 GATE_ONLY；`EvidenceMode = Literal['GATE_ONLY', 'DISCOUNT']`（逐字）。DISCOUNT 启用须另立 ADR，属行为不属契约 |
| `cel_enabled` | StrictBool | [L1898] eval_config.cel.enabled 单开关，默认 false。⚠ **默认值不在 models 层给**（H-5：默认值属 config 层），故本字段**必填无默认** |
| `input_fingerprints` | InputFingerprints | [L891] 写入 audit.json，V-3 第二人复跑比对基准（裁决 15 的同一个类型） |

B 组（Step 1-4 结果，供 `[L1016]` 跨方案复用）**8 字段照 ORCH-13 裁决 1 原文不动**，类型即本 ADR 裁决 28 定义的 8 个模型：
`attainment: AttainmentFrame`、`normalized: NormalizedFrame`、`evidence: EvidenceFrame`、`redline: RedlineFrame`、
`score: ScoreFrame`、`grade: GradeFrame`、`pool: PoolFrame`、`pool_stats: PoolStats`。

→ **ScoringContext 共 16 字段**（A 组 8 + B 组 8），除 `seed` 可为 None 外全部必填无默认。
**禁止**：放任何业务数值（H-5）、放当前时间（H-8）、放 SDD 与本 ADR 未提及的字段（ORCH-13 裁决 1 原禁令继续有效）。

### 裁决 31：不新建 AllFrames / ReportSet / RunContext

- `AllFrames`（`[L1061]` reports.render 的形参类型名）= ORCH-13 裁决 1 的 B 组 8 个 Frame，已由 `ScoringContext` 承载；
  reports.py（S6）直接收 `ScoringContext`，**不另建聚合模型**（多一层无原文依据的包装）。
- `ReportSet`（`[L1061]` 返回类型名）= `[L1062]` 的 7 个产出文件（report.md / score_card.csv / grade_ledger.csv /
  sensitivity_report.csv / entropy_diagnostic.csv / triangulation.md / audit.json），属 **S6 reports 任务**的返回结构；
  SDD 未给字段清单 → S1-T04 **不建**，登记 **B-021**。
- `run_ctx`（`[L1050]`）= `ScoringContext` 的 A 组；`inputs_fp` / `outputs_fp`（`[L1050]`）= `InputFingerprints` / `dict[str, str]`（裁决 15）。
  这三个都是**签名形参名**而非独立数据类型，不建模。
- `[L1222]` sensitivity_report 的「CSV + MD」两种载体如何拆分，SDD 未给 → 属 S6 reports 渲染职责，
  **models 层只有 1 个 `SensitivityReport`，不拆成两个模型**（并入 B-021）。

### 裁决 32：序列化五规则在 models 层的体现

`[L1053]` 的五条规范化序列化规则与 `[L1052]` 的 reproducibility_hash 算法**属 audit.py（S6），本任务不实现**。
models 层只需保证「类型可被五规则无损序列化」，具体三条纪律：
① 比率/权重/达成率/均值一律 `Ratio`（Decimal），**任何字段不得是 float**（H-4、`[L1265]`「全链路不经 float」）；
② 有序列一律 `tuple`，**禁 set/frozenset**（见裁决 28 第三条理由）；
③ `None` 与空字符串严格区分（`[L1053]`⑤）→ 可空字段默认值一律写 `None`，**不得用空字符串当"空"**；
空容器默认 `()`（tuple）或 `{}`（dict），不用 `None` 冒充空集合。
`[L1274]`「新增输出字段必须同步序列化器，由 G-12 与 V-11 守护」→ 本任务新增的每个字段都是 S6 序列化器的待办，
R4 须把「新增字段清单」抄进复核报告，作为 S6 的输入。

### 裁决 33：surplus 白名单（R4 判定依据，不得判 ❌）

`tests/test_models_input.py` 有一套「声明字段不得超出 digest 命名集 + 白名单」的门禁（S1-T03 刚收紧过）。
本任务新增的、SDD 未逐字给出但由本 ADR 授权的名字，**R4 按本条判定为已授权**：

- 容器字段名 `rows`（8 个 Frame 各一个）、`by_scheme`、`by_strategy`（裁决 25/28）
- 10 个子模型及其字段：`InputTableFingerprint`、`PreflightFinding`、`DowngradeAction`、`PoolKey`、
  `ScoreCardMetricCell`、`ScoreCardDimCell`、`SensitivitySchemeResult`、`SensitivityStrategyRow`、
  `TriangulationStrategyRow`、`PoolStatRow`
- 7 个 Frame 行模型：`AttainmentRow`、`NormalizedRow`、`EvidenceRow`、`RedlineEvalRow`、`ScoreRow`、`GradeRow`、`PoolRow`
- 标注载体 `flags`（EntropyDiagnosticRow / SensitivityReport / TriangulationReport 各一个，裁决 25/26/27）
- `SensitivitySchemeResult.flipped_count` / `.assessed_count` / `.flag`（裁决 25：比率必须可还原）
- `GradeLedgerRow.previous_grade` / `.ledger_complete`（裁决 24）
- `ScoringContext.run_id`（裁决 30）
- `value_captured_minor` 的 `_minor` 后缀（裁决 22）
- 9 个新枚举/别名：`SchemeName`、`StabilityLabel`、`FrameGrade`、`EntropyStatus`、`MethodAgreement`、
  `NormalizationMethod`、`ScoreOperator`、`EvidenceMode`、`InputFingerprints`

**不在白名单内的任何新增字段/模型，R4 一律判 ❌ 要求删除**（ORCH-13 裁决 3 的复核方式继续有效）。

## 5. 通用契约（全部新增模型一律适用）

1. `model_config = ConfigDict(frozen=True, extra='forbid')`（`[L865]`/`[L1902]`，V-5 `[L871]`）。
   建议复用既有 `_InputRow` 基类**或**新建同配置的 `_OutputModel` / `_FrameModel` 基类；
   若新建基类，配置必须与 `_InputRow` 逐字一致，且基类名以 `_` 开头（不进 `__all__`）。
2. H-4：金额与计数一律 int（`MoneyMinor` / `MinorUnits` / `StrictInt`）；比率/达成率/权重/均值/相关系数一律 `Ratio`（Decimal）；
   bool 一律 `StrictBool`。**任何字段不得声明为 `float` 或裸 `int`**（裸 int 绕过 StrictInt 的 lax 拒绝闸门）。
3. H-5：**不得为任何字段写业务数值默认值**（权重、门槛、阈值、目标值、单价、周期、样本量、K-01~K-20）。
   默认值只允许 `None` / `()` / `{}` / `False`（`False` 仅用于 StrictBool 的"未发生"语义，如 capped_flag）。
4. H-6/H-7：一切 reason_code 列用 `ReasonCode` 注解类型（只接受已注册 `RC.<NAME>`），禁裸字符串字面量。
5. H-8：不得出现 `datetime.now` / `time.time` / `date.today` 等墙钟调用；`run_at` / `period` / `seed` 全部由参数注入。
6. H-9 INV-1：`dsm/models.py` 属 L1，**不得 import L0a/L0b**（weights_ahp / weights_combine / fixtures_gen /
   weights_calibrate / whatif）；INV-3：不得 import diagnostics。
7. ORCH-16：SDD 给了逐字名的一律逐字（含 `metric_code` 与 `metric_id` 的不一致、`grade_reason_codes` 与
   `grade_reason_path` 的不一致、`rho_` 的 ASCII 映射），**不得为"美观"统一改名**。
8. 新模型必须注册进测试的扫描清单（S1-T02 的 R4 已提出该 followup）：本任务在
   `tests/test_models_output.py` 里建 `OUTPUT_MODELS` / `FRAME_MODELS` / `SUB_MODELS` 三张字典，
   遍历式门禁（frozen+forbid、无 float、无墙钟、无业务字面量默认值、未声明字段必报错）一律走这三张表，
   **并加一条"清单完整性"断言**：`dsm.models.__all__` 里的每个模型类都必须出现在三张表之一，
   防止后续任务加模型却漏注册（把 S1-T02 R4 的 followup 制度化）。
9. `dsm/models.py` 的 `__all__` 必须同步追加全部新公开名（S1-T03 落库后实测为 19 项）。

### 裁决 34：字段计数与既有模型白名单的实测复核（L1 之后补，R2/R4 以此为准）

R3 在 L1 提出 4 点疑议，Orchestrator 用 ast 与表格切分探针实测复核，裁定如下（依据均为实测输出，非推理）：

| 疑议 | 裁定 | 实测依据（2026-11-24，仓库 HEAD e579bed + 在制品） |
|---|---|---|
| ScoreCardRow 到底 35 还是 36 字段 | **35**。裁决 21 表格实列 35 个字段名；标题与合计行原写 36 系笔误，已就地更正为 35 | 探针按竖线切分裁决 21 表格第 2 列并按顿号、逗号、斜杠拆分去重：rows_in_table 30、unique_fields **35**、anomalies 空、无重复字段；tests/test_models_output.py 的 EXPECTED_FIELDS 中 ScoreCardRow 长度同为 **35** |
| GradeLedgerRow 到底 13 还是 14 字段 | **14**。recommended 与 decided 两列并存，另加 decision_note | EXPECTED_FIELDS 中 GradeLedgerRow 长度 **14** |
| 新增模型类总数 32 还是 33 | **32**。PoolStats 已计入裁决 28 的 8 个中间 Frame，不得重复计数 | EXPECTED_FIELDS 键数 **32**；ScoringContext 16 字段；全部新增字段数合计 **219**；dup-field models 空 |
| 测试里的 PREEXISTING_MODELS 白名单是否可批准 | **批准**。用于把「既有模型不被本任务改动」变成可断言事实 | ast 探针读 dsm/models.py 顶层 ClassDef 得 15 个类，其中 1 个为私有基类 _InputRow，公开既有模型恰为 **14** 个，与白名单逐字相等；白名单与 EXPECTED_FIELDS 键集交集为**空**；EF_not_existing **32**（即 32 个新类均为新增名） |

实现后若实测字段数与本节不符，按 ORCH §7.3 走 R6 定向修复；**不得改测试、不得放宽断言**（H-11）。

## 6. 本 ADR 新登记的 blocker（随 S1-T04 落库时写入 ops/blockers.md）

| 编号 | 缺什么 | 谁签认 | 完成条件 | 阻塞? |
|---|---|---|---|---|
| B-019 | `PreflightFinding` 只建了 code/severity/message 三字段最小闭包，finding 的完整结构（作用对象、证据行号、建议动作）SDD 未给 | Orchestrator + S3 preflight 实现者 | S3 取到 §3.4 preflight 原文后落 digest，决定是否扩字段（扩字段属破坏性变更，须再立 ADR，参照 [L1902] 的预留理由） | 否 |
| B-020 | `[L1006]`「占比双报（池内占比+合并占比）」中**池内占比的精确分母**原文未给（[L1003] 只明说禁止只报合并占比） | Orchestrator + S5 pooling 实现者 | 本 ADR 按 §10.2-2 保守超集两列并存；S5 取到 pooling 原文后定分母语义并回填 | 否 |
| B-021 | `ReportSet` 字段清单与 sensitivity_report 的 CSV/MD 双载体拆分方式，SDD 均未给（[L1061]/[L1062]/[L1222]） | Orchestrator + S6 reports 实现者 | S6 按 [L1062] 的 7 个逐字文件名建 ReportSet，并定双载体拆分；本 ADR 裁决 31 已禁止在 models 层预建 | 否 |

## 7. 依据行号汇总

SDD `[L864]`-`[L871]` `[L877]` `[L879]` `[L888]`-`[L891]` `[L900]` `[L928]` `[L930]` `[L931]` `[L939]`-`[L945]`
`[L952]`-`[L955]` `[L964]`-`[L968]` `[L977]`-`[L982]` `[L988]`-`[L994]` `[L1001]`-`[L1006]` `[L1014]`-`[L1020]`
`[L1028]`-`[L1030]` `[L1038]` `[L1040]`-`[L1042]` `[L1046]` `[L1050]`-`[L1055]` `[L1061]`-`[L1064]`
`[L1080]`-`[L1091]` `[L1119]` `[L1122]` `[L1130]` `[L1131]` `[L1137]` `[L1139]` `[L1141]` `[L1149]` `[L1150]`
`[L1152]` `[L1156]` `[L1174]` `[L1180]` `[L1181]` `[L1190]` `[L1192]` `[L1200]` `[L1205]` `[L1218]`-`[L1226]`
`[L1265]` `[L1270]`-`[L1274]` `[L1608]`-`[L1640]` `[L1777]` `[L1843]` `[L1848]`-`[L1863]` `[L1867]`-`[L1884]`
`[L1888]` `[L1894]`-`[L1902]` `[L1914]`
仓内：ORCH-02、ORCH-03、ORCH-13、ORCH-14、ORCH-15、ORCH-16、ORCH-17、ORCH-18、ORCH-20、ORCH-21；
ORCH §2 H-4/H-5/H-6/H-7/H-8/H-9/H-11；§10.2-2、§10.2-4。
