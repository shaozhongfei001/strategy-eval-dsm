<!-- ADR: ORCH-24 | task: S1-T06 | 依据: docs/digest/S1-T06.md（SDD sha256[:12] 708679e9a83d / 2003 行 / 177646 B）| 主控: Orchestrator | 日期: 2026-11-24 -->
<!-- 承接: ORCH-23（S1-T05 PLACEHOLDER 契约，裁决 1-24）、ORCH-20 L145（四段 kind 条件式必填 + FROZEN 缺 whatif_run_id 归 T06）、ORCH-14 L39（红线指标存在性归 T06，不得提前实现）、ORCH-16（SDD 逐字名优先）、ORCH-22 裁决 31（不预建未要求的聚合模型） -->

# ORCH-24：`dsm/config.py` 语义校验 + 权重版本校验契约（S1-T06）

本 ADR 是 S1-T06 的唯一契约权威。R3 按此写 RED，R2 按此最小实现，R4 按此逐条判定（H-11：
期望值不得跟随实现；无人值守下 R4 依 SDD 原文行号 + 本 ADR 判定，判定依据落 docs/adr/ 视为签认）。
凡 SDD 沉默处一律标「SDD 未给」并登记 `ops/blockers.md`，**不发明业务数值**（H-5）。

---

## 0. 权威优先级（本 ADR 内部一律适用）

1. SDD 正文（`[LXXX]`）> 非权威分册 DESIGN-详细设计 > 仓内既成实现。判例：ORCH-16 裁决 1。
2. SDD 内部冲突时取 **多数口径 + 保守超集**（`[L1307]`「宁可不评，不可错评」）。
3. `[L911]` 口径统一声明：§3.4.1 表（C-01~C-10）是 preflight 判据的唯一口径；
   `[L879]`/`[L880]` 是 **config 加载层** 判据。二者对象不同，不构成冲突（见裁决 1）。

---

## 1. 任务边界

### 裁决 1：T06 只做「配置加载期静态校验」，不做 C-01~C-10 的运行期编排

- **做**（ORCH §5 第 181 行逐字六条 + `[L880]` 三条 + `[L1435]` P-11）：
  Σ W_d = 1；每维度内 Σ w_j = 1；attainment_floor 单调 L1 > L2 > L3 > L4；
  红线阈值引用的指标必须存在于 metric_dict；action 非空；anchor_set 成员必须存在于 strategy_master；
  status 必须为 FROZEN；评价期必须落在 `[effective_from, effective_to]`；
  FROZEN 而缺 whatif_run_id → 加载失败。
- **不做**（写明以免 R2 提前实现，违 ORCH-14 L39「不得提前实现」）：
  * C-02 `[L901]`/`[L1285]`/`[L1286]` 的「未签认指标剔除 + 权重重归一 + 维度 W 置 0」——运行期降级，归 S3 preflight；
  * C-03 `[L902]` 的「每个签认指标在权重配置中有对应项 / 无孤儿权重项」——需 metric_dict 签认状态，归 S3；
  * C-10 `[L909]`/`[L1298]` 的「未被淘汰 / 未换 version_id / 回退仅当期归一化 + 秩反转风险标注」——运行期降级，归 S3/S5；
  * 分册 L324「HARD 红线指标须 is_redline = true 且 dim_code 匹配」——SDD `[L879]` 六条未列，归 S3（C-03）候选，登记 B-028；
  * audit_bundle 写出、score_card 抑制（`[L917]`）——归 S6/S9。
- T05 已冻结的 12 个公开名与 209+ 条既有用例**一条不改**（H-11）；T06 只追加。

### 裁决 2：三个纯函数 + `load_all` 挂钩；跨文件判据用**必填入参**注入，禁可选默认（防静默跳过）

SDD 未给 config 层如何取得 metric_dict / strategy_master（二者是 csv，`[L877]`/`[L1251]`，
由 L1 `io_loaders` 负责，**S1 阶段尚未存在**）。裁定：

- `validate_semantics(cfg)`：四条**无外部依赖**判据（Σ×2、attainment_floor、actions）→ `load_all` 一律调用。
- `validate_weights(cfg, *, period)`：`period` **必填无默认**（H-8：period 由参数注入，禁墙钟）→
  `load_all` 仅在调用方注入 `period` 时调用。
- `validate_cross_file(cfg, *, metric_ids, strategy_ids)`：两条跨文件判据，**两个入参均必填无默认**→
  `load_all` **不调用**（S1 无 csv 加载器）；由 S3 preflight 调用。
- **不得**给 `metric_ids` / `strategy_ids` / `period` 设 `None` 默认后再「若为 None 则跳过」——
  那是 V-14 禁止的静默降级。必填无默认使漏调用在类型/运行期立刻暴露。
- 强制接线（防止 `validate_cross_file` 沦为死代码）：S9-T02 `tests/test_architecture.py` 必须断言
  `dsm/preflight.py` 引用 `config.validate_cross_file` 与 `config.validate_weights`；登记 B-029。

---

## 2. 异常与退出码

### 裁决 3：异常名取 SDD 逐字 → `ConfigSemanticError` / `WeightVersionInvalidError`；分册名不建

- `[L881]` 逐字：`ConfigPlaceholderError（退出码 3）、ConfigSemanticError、WeightVersionInvalidError`。
- 分册 L312-L313 的 `WeightSumError` / `WeightVersionNotFrozenError` **不建**（ORCH-16 裁决 1：SDD 逐字名优先；
  H-10：不新造名词）。R3 若写出这两个名字即判 FAIL。
- 三个异常**平级继承 `Exception`**（`[L881]` 未给继承关系，SDD 沉默 → 取最保守的平级，不发明中间基类）。
- **不动** T05 的 `ConfigPlaceholderError`（已 R4 复核通过、即将落库）。audit_bundle 需要 reason_code 时
  由 S6 按异常类型映射到已注册的 `RC.CONFIG_PLACEHOLDER`；登记 B-030。

### 裁决 4：退出码 —— `ConfigSemanticError` = 3，`WeightVersionInvalidError` = 2

SDD 未给两个新异常的专属退出码（`[L881]` 只给 ConfigPlaceholderError 的 3）。裁定：

| 异常 | exit_code | 依据 |
|---|---|---|
| `ConfigPlaceholderError` | 3（`EXIT_CONFIG`，T05 已建） | `[L881]` 逐字 |
| `ConfigSemanticError` | 3（`EXIT_CONFIG`） | `[L1080]` 3 = 配置错；`[L1282]` config 层「抛错终止」同层同出口 |
| `WeightVersionInvalidError` | **2**（新增 `EXIT_BLOCK = 2`） | `[L1280]`「权重版本过期或 DRAFT → BLOCK + 退出码 2」；`[L900]` C-01「BLOCK，退出码 2」；`[L1413]` G-11(a)「preflight = BLOCK，code = STALE」 |

- `[L1281]`「FROZEN 缺 whatif_run_id → 加载失败」未给码；因 `[L900]` C-01 判据**已含** whatif_run_id
  且整条 C-01 的后果是「BLOCK，退出码 2」，裁定该子情形同为 2（多数口径）。
- `EXIT_BLOCK = 2` 与 `EXIT_CONFIG = 3` 均为**单一事实源**，S9-T01 `cli.py` 必须 import，不得重写字面量。
- 两个码都非 0，`[L1091]`「退出码非 0 不得产出 score_card」自然成立。登记 B-031 请行方签认此映射。

### 裁决 5：reason_code 一律 `RC.<NAME>`，禁裸字符串（H-6 / H-7 / P-8 AST 扫描）

T06 只允许引用 S0 已注册的五枚（实测 `dsm/reason_codes.py` 第 31-36 行）：

| 情形 | reason_code | 严重度（注册表原值） |
|---|---|---|
| status = DRAFT | `RC.WEIGHT_VERSION_DRAFT` | BLOCK |
| 无版本覆盖评价期（含 period 超出 effective_to） | `RC.WEIGHT_VERSION_STALE` | BLOCK |
| FROZEN 而缺 whatif_run_id / provenance 缺 whatif_run_id | `RC.WEIGHT_MISSING_WHATIF_RUN_ID` | BLOCK |
| 多版本同时覆盖评价期 / approved_by·approved_date 缺 / 其他版本级不自洽 | `RC.WEIGHT_VERSION_INVALID` | BLOCK |
| 六条语义判据任一违规、结构缺失、数值类型非法 | `RC.CONFIG_SEMANTIC_ERROR` | BLOCK |

- 禁止出现 `'WEIGHT_VERSION_DRAFT'` 一类裸字符串字面量（S9-T02 P-8 AST 扫描会判 FAIL）。
- `str(RC.X) == 'RC.X'`，写 CSV / hash 时必须用 `.value`（S0 已钉的坑，T06 沿用）。
- T06 起 `dsm/config.py` **首次** import `dsm.reason_codes`；这是 H-9 允许的同层（L1）依赖。

---

## 3. 数值与日期口径（承接 ORCH-23 裁决 4 转来的 H-4 挂钩点）

### 裁决 6：Σ 比较 = Decimal + `numeric.eq_tol(total, numeric.ONE)`，容差 1e-12

- 容差三处并存的定性：`[L879]` 未带容差、`[L902]` 写「两级权重各自归一（1e-12）」、
  P-5/P-14 `[L1429]`/`[L1438]` 带 1e-12 → **唯一实数口径是 1e-12**，且与 H-4 一致。裁定容差 = `numeric.TOL`。
- 一律 `numeric.D(value)` 转 Decimal（H-4「字符串构造」），比较一律 `numeric.eq_tol(...)`；
  **禁止**在 config.py 内出现 `1e-12` / `0.000000000001` 一类 float 字面量（H-4 + R4 的 float 扫描）。
- 求和用 Python 内建 `sum(..., numeric.ZERO)` 或 `numeric.weighted_sum`；不得用 float 累加。

### 裁决 7：float / bool 一律**拒**，不 silently `from_float`

- `numeric.D` 实测已拒 float（`FloatNotAllowedError`）与 bool（`NumericError`）；空串亦拒。
- 裁定：权重值与 attainment_floor 值必须是 `int` / `str` / `Decimal`；遇 float / bool / 空串 / 不可解析串 →
  记 `NUMERIC` 违规（**不抛 NumericError 出圈**，一律转成 `ConfigSemanticError`），与 S1-T02 的
  `Ratio` 拒 float 口径一致（V-5 / H-4）。
- `numeric.from_float` 在 T06 **不得被调用**（配置里不该出现 float；出现即违规）。
- 行方 yaml 若写裸小数（`0.35`）需改为字符串（`'0.35'`）：登记 B-032 请行方签认。

### 裁决 8：period 与生效区间 —— 月粒度、双闭区间、一律补 `-01` 后字典序比较

SDD 未给 period 格式声明与区间闭合性（grep「闭区间/半开/inclusive」零命中）。裁定：

- `period` 形态取 `[L386]`/`[L1536]`/`[L1548]` 的唯一示例形态 `YYYY-MM`；同时**接受** `YYYY-MM-DD`
  （`[L889]` ISO 约束）与 `datetime.date` / `datetime.datetime`（PyYAML `safe_load` 会把 ISO 日期解析成 date）。
- `effective_from` / `effective_to` 同上三种形态。
- 规约函数 `period_key(value) -> str`：date/datetime → `isoformat()`；`'YYYY-MM'` → `'YYYY-MM-01'`；
  `'YYYY-MM-DD'` → 原样（strip 后）。**一律左对齐补到日**，随后做字符串字典序比较（ISO 字典序 == 时间序）。
- 闭合性：**双闭区间** `from <= period <= to`。依据：`[L880]` 的方括号记法（数学惯例即闭区间）+
  `[L1413]` 只把「period **超出** effective_to」判为 STALE（等价于 to 当天仍在期内）。
- 补 `-01` 而非补月末，是 `[L1307]`「宁可不评，不可错评」的偏严侧：月粒度下行为完全正确
  （period=2026-10、to=2026-10 → `2026-10-01 <= 2026-10-01` 在期内；period=2026-11 → STALE），
  仅在「period 为日粒度而端点为月粒度」时偏严判 STALE。登记 B-033 请行方签认。
- 形态非法（既非 date 也不匹配 `^\d{4}-\d{2}(-\d{2})?$`）→ `STRUCTURE` 违规，`ConfigSemanticError`。
- **不得**用 `datetime.now()` / `date.today()` 推断当前期（H-8）；`run_at` 本期只接受不使用（裁决 15）。

---

## 4. 六条语义判据的逐条口径

### 裁决 9：Σ W_d = 1 / Σ w_j = 1 —— 对象键名、范围与结构前置

- 键名逐字取 `[L1192]`：`level1_weights`（维度权重，Σ = 1）、`level2_weights`（维度内指标权重，维度内 Σ = 1）。
  仓内 `models.WeightVersionDoc` 已按此行建字段，形态为 `dict[str, Ratio]` 与 `dict[str, dict[str, Ratio]]`。
- **校验范围**：`cfg.weights` 中 **status == 'FROZEN' 的每一份**（`[L1190]`「只有 FROZEN 能用于评分」）。
  DRAFT（`[L379]` 由 `dsm combine build` 产出的中间物）**不校验 Σ**，避免中间产物误伤；
  但它仍受裁决 15 的 status 枚举与 P-11 无关约束。period 注入时选中的那份必为 FROZEN，故 Σ 必被校验。
- 结构前置：weights 树**顶层**必须直接含 `level1_weights` 与 `level2_weights`（`[L1190]-[L1194]` 是 T6 表的列 =
  文档顶层字段，不递归查找）；缺任一键 → `STRUCTURE` 违规。
- 判定：`eq_tol(sum(level1_weights.values()), ONE)`；对 `level2_weights` 的**每个** dim 分别
  `eq_tol(sum(该 dim 的值), ONE)`。空 mapping 的 Σ = 0 ≠ 1 → 自然违规，不特判。
- `level2_weights` 的 dim 键与 `level1_weights` 的 dim 键是否必须一致：SDD 未给 →
  **不校验**（属 C-03 对齐范畴，裁决 1 已划出）；登记 B-034 记事实。
- 违规路径沿用 ORCH-23 裁决 8 的表示法：`<stem>.level1_weights`、`<stem>.level2_weights.<dim>`。

### 裁决 10：attainment_floor 四级**严格递减**；分册「L4 可为 null」在 T05 口径下不可达

- `[L879]` 逐字「attainment_floor 单调（L1 > L2 > L3 > L4）」+ `[L493]`「按 attainment_floor[L1..L4] 映射基础等级」
  → 裁定**四级齐全且严格递减**。分册 L323「L1 > L2 > L3，L4 可为 null」不采纳（SDD 优先，ORCH-16）。
- **关键交互**：ORCH-23 裁决 6 已定「`None` 一律命中 PLACEHOLDER」，故任何 `attainment_floor: null`
  在 T05 阶段就已被 `ConfigPlaceholderError` 拦下，T06 永远看不到 None。分册的「L4 可为 null」
  在本流程口径下**不可达**；若行方确要允许 L4 空，须先改 T05 的必填性口径 → 登记 B-035 请行方签认。
- 比较用 Decimal **精确** `>`（序关系不引入容差）：两级 floor 之差即使小于 1e-12，只要相等即违规。
- 规则集合的取法见裁决 14（递归收集同时含 `grade_code` 与 `attainment_floor` 的 mapping）。
- 四级必须恰为 `{L1, L2, L3, L4}` 各一条（`[L1200]` GradeCode）；缺级 / 重复级 → `STRUCTURE` 违规；
  四级齐全但序不严格递减 → `FLOOR_MONOTONIC` 违规，路径取该条规则的定位路径。

### 裁决 11：`action` 非空 → 字段名取 `[L1205]` 的 **`actions`**；`action_gate` 不校验

- `[L879]` 写单数「action」、`[L1254]` 写「各级 action」、`[L1205]` 字段名逐字为 `actions` / `action_gate`。
  仓内 `models.GradeRuleRow.actions` 已按 `[L1205]` 建为 `tuple[str, ...] | None`（既成事实 + SDD 字段表优先）。
- 裁定判据：**每条 grade_rule 的 `actions` 必须非空**——`None`（T05 已拦）、空 list / 空 tuple / 空 dict /
  空串 / 全为空白串的序列，一律 `ACTION_NON_EMPTY` 违规。
- `action_gate` **不做**非空校验（`[L879]` 只说 action；最小实现，不提前扩判据）。
- 键名口径差登记 B-036。

### 裁决 12：红线阈值引用的指标必须存在于 metric_dict —— 递归收集 `metric_id`

- 判据逐字 `[L879]`；字段出处 `[L1180]`（redlines 的 `metric_id`）。ORCH-14 L39 明示此校验归 T06。
- 取法：递归遍历 `cfg.redlines` 树，收集**所有含 `metric_id` 键的 mapping** 的该值（保守超集，
  规避 SDD 未给 redlines 顶层键名的沉默）；每个值必须 ∈ 注入的 `metric_ids` 集合，否则
  `REDLINE_METRIC_EXISTS` 违规，路径 = 该 mapping 的定位路径 + `.metric_id`。
- `metric_ids` 为空集合时：任何 metric_id 引用都违规（不静默放过）；`redlines` 树无任何 metric_id → 无违规。
- `level ∈ {HARD, SOFT}` `[L1180]`、`comparator`/`threshold_value` `[L1181]`、`forced_grade` `[L1182]`、
  `reason_code` `[L1183]`、`waiver_allowed` `[L1184]` 的枚举/类型校验属 models 层（S1-T02 已建 RedlineRow），
  T06 **不重复**。`[L994]`「阈值必须引用行内既有制度文号、不得由模型方拟定」是治理约束，
  非机器可判据 → 登记 B-037（行方签认项），T06 不实现。

### 裁决 13：anchor_set 成员必须存在于 strategy_master —— 递归收集 `strategy_ids`

- 判据逐字 `[L879]`；字段出处 `[L1212]`（`anchor_set_id` / `strategy_ids`），仓内
  `models.AnchorSetDoc.strategy_ids: tuple[str, ...]` 已建。
- 取法：递归遍历 `cfg.anchor_set` 树，收集**所有键名为 `strategy_ids`** 的值（应为序列），展开每个成员；
  成员必须 ∈ 注入的 `strategy_ids` 集合，否则 `ANCHOR_MEMBER_EXISTS` 违规，路径 = `<定位路径>.strategy_ids[i]`。
- **双出口的定性**（`[L879]` config 语义校验 vs `[L909]`/`[L1298]` C-10 WARN + 回退仍出分）：
  裁定 T06 只做**静态存在性**（配置里的 id 在 master 注册表中根本不存在 = 配置错，硬失败）；
  C-10 的「未被淘汰（status）/ 未换 version_id / 回退仅当期归一化 + 首屏标注秩反转风险」是**运行期动态**判定，
  归 S3 preflight。二者对象不同：T06 管配置自洽，C-10 管运行期失效。C-10 的存在性分支因此成为
  防御性冗余，符合 `[L1307]` 保守原则。登记 B-038 记此定性。
- `strategy_ids` 为空序列 → 无违规（锚定集是否为空属 C-10 有效性范畴，T06 不判）。

### 裁决 14：树形态沉默 → **递归键收集法**（weights 顶层例外）

SDD 未给 `redlines.yaml` / `grade_rules.yaml` / `anchor_set.yaml` 的顶层键名（`[L1180]-[L1184]`、
`[L1200]-[L1206]`、`[L1212]-[L1214]` 只给列名）。裁定统一取法，避免 R2 各自发明：

- `redlines` / `grade_rules` / `anchor_set` 三棵树：**递归收集**满足条件的 mapping / 键值
  （条件见裁决 12 / 13；grade_rules 的条件 = 同时含 `grade_code` 与 `attainment_floor` 两个键的 mapping）。
  不假设顶层是 list 还是 dict，不假设分组键名。
- `weights_*`：**顶层直取**（裁决 9），因为 `[L1190]-[L1194]` 明确是文档级列。
- `eval_config` / `ahp_matrices`：T06 **不校验**（`[L879]` 六条不涉及；ahp 矩阵内容一致性属 S6/S7）。
- 递归收集到的定位路径一律沿用 ORCH-23 裁决 8 的表示法（stem + 点号 + `[i]`，0 起）。
- 同一 `grade_code` 被收集到多次 → `STRUCTURE` 违规（配置不自洽，不得静默取第一个）。

---

## 5. 权重版本校验

### 裁决 15：判定顺序与 reason_code 映射（固定序，确定性可复现）

`validate_weights(cfg, *, period)` 按**固定顺序**判定，全部违规一次性收集（裁决 18），
但 `reason_code` 取**首个命中**的那条（一个异常一个 reason_code，便于 `[L917]` audit 与 G-11 golden 断言）：

| 序 | 判据 | 命中时 reason_code | 依据 |
|---|---|---|---|
| 1 | `cfg.weights` 为空（一份 weights_*.yaml 都没有） | `RC.WEIGHT_VERSION_INVALID` | `[L877]` 六类文件必备；ORCH-23 裁决 10 已保证「至少一份」，此处为防御性冗余 |
| 2 | 覆盖 period 的版本数 == 0 | `RC.WEIGHT_VERSION_STALE` | `[L880]`、`[L1413]` G-11(a) code = STALE |
| 3 | 覆盖 period 的版本数 >= 2 | `RC.WEIGHT_VERSION_INVALID` | SDD 未给；`[L1191]`「期内权重不变」要求唯一 → 保守判失败，登记 B-039 |
| 4 | 选中版本 status != 'FROZEN' | `RC.WEIGHT_VERSION_DRAFT`（status == 'DRAFT'）/ `RC.WEIGHT_VERSION_INVALID`（其他值） | `[L880]`、`[L1190]`、`[L1280]` |
| 5 | 选中版本 provenance 缺 `whatif_run_id`（或 strip 后为空） | `RC.WEIGHT_MISSING_WHATIF_RUN_ID` | `[L880]`、`[L678]`、`[L1241]`、`[L1281]`、`[L1374]` 五处一致 |
| 6 | 选中版本 provenance 缺其他必填段（裁决 17） | `RC.WEIGHT_VERSION_INVALID` | `[L1435]` P-11 |
| 7 | 选中版本缺 `approved_by` / `approved_date`（或 strip 后为空） | `RC.WEIGHT_VERSION_INVALID` | `[L900]` C-01、`[L1194]`、`[L1242]` |

- 覆盖判定 = 裁决 8 的 `period_key(from) <= period_key(period) <= period_key(to)`。
- 缺 `effective_from` / `effective_to` / `status` / `provenance` 键 → `STRUCTURE` 违规，
  抛 **`ConfigSemanticError`**（结构/类型问题一律 3，版本策略问题一律 2；这条分界线 R4 按此判定）。
- `load_all(config_dir, *, period=None, run_at=None)`：
  * `period is None` → 不调 `validate_weights`（H-8：period 由参数注入；无注入则区间判据无从执行）。
    此时**仍**执行与 period 无关的版本级约束：对每一份 weights 树校验 status 枚举合法
    （∈ {DRAFT, FROZEN}，否则 `STRUCTURE`）与「status == FROZEN → 裁决 17 的 provenance 完整性 +
    whatif_run_id 非空」（`[L1374]`「下次 config 加载直接失败」正是无 period 也应生效的口径）。
  * `period is not None` → 调 `validate_weights`（其内部已含上述两项，不得重复报）。
  * `run_at` 本期**只接受不使用**（ORCH-23 裁决 11 预留的注入点；H-8 禁墙钟，S3 起才用）。
  * 生产入口（`dsm preflight` / `dsm score`）必须传 `period`：由 S9-T02 架构测试断言，登记 B-040。

### 裁决 16：「选中版本」由 `select_weight_stem(cfg, *, period)` 单独暴露

- 返回唯一覆盖 period 的 weights stem（`cfg.weights` 的键）；命中 0 份或 >= 2 份时**不返回**，
  由 `validate_weights` 统一收集违规后抛错。为可测性，`select_weight_stem` 自身在 0/≥2 时抛
  `WeightVersionInvalidError`（reason_code 按裁决 15 序 2 / 序 3）。
- 多份 weights 的 stem 序沿用 ORCH-23 裁决 9（stem 升序），保证「≥2 份」时 violations 的列出顺序确定。

### 裁决 17：P-11 provenance 完整性 —— kind 条件式必填（承接 ORCH-20 L145）

`[L1435]` P-11 逐字：「任何 FROZEN 权重版本必须具备完整 provenance（AHP 矩阵 + CR；
若 combined 则含 α + alpha_basis + whatif_run_id），缺任一项 → 配置加载失败」。
键名逐字取仓内 `models.WeightProvenance` / `AhpSegment` / `CombineSegment`（均按 `[L1228]-[L1245]` 建）：

| `provenance.kind`（`[L1231]` 逐字枚举） | 必填段 |
|---|---|
| `AHP_ONLY` | `ahp`（且 `ahp.comparison_matrices` 非空、`ahp.cr` 存在）+ `whatif_run_id` + `approved_by` + `approved_date` |
| `AHP_ENTROPY_COMBINED` | 上述全部 + `entropy` + `combine`（且 `combine.alpha` 存在）+ `alpha_basis` |
| `EXPERT_ONLY` | 同 `AHP_ONLY`（SDD 未给专属规则；`[L1435]`「任何 FROZEN」+「AHP 矩阵 + CR」无 kind 条件 → 保守超集）|

- `ahp.comparison_matrices` 必须非空 mapping（「AHP 矩阵」`[L1435]`/`[L1232]`）；`ahp.cr` 必须存在且可 `numeric.D`
  （CR 的**阈值** SDD 未给 → **不校验数值**，H-5 严禁拟定 0.1 一类业务值；登记 B-041）。
- `combine.alpha` 必须存在且可 `numeric.D`；α 的取值范围 SDD 未给 → **不校验数值**，登记 B-042。
- `provenance` 键本身缺失 → 对 FROZEN 版本是 `RC.WEIGHT_VERSION_INVALID`（P-11「缺任一项 → 加载失败」）；
  models 层 provenance 可空（ORCH-20 裁决 2）不代表 config 层可空，这正是 ORCH-20 L145 交给 T06 的事。
- 多余的段（如 AHP_ONLY 却带 entropy）**不报错**（最小实现，不发明「禁止多余段」判据）。
- `EXPERT_ONLY` 与「AHP 矩阵必填」的语义张力登记 B-043 请行方签认。

### 裁决 18：`whatif_run_id` 只校验**存在与非空**，不校验格式

- SDD 未给 whatif_run_id 的类型/长度/命名规则（`[L1241]` 只称「权重影响预演运行号」，`[L394]` 只到目录名一级）。
  H-5 禁拟定 → 裁定只判「键存在、值非 None（T05 已保证）、`str(value).strip() != ''`」。
- 类型：`models.WeightProvenance.whatif_run_id: str | None`（标识列保持 str，仓内既成口径）→
  config 层要求 `isinstance(value, str)`；非 str → `STRUCTURE` 违规。
- 一次性列出全部违规（与 ORCH-23 裁决 9 同纪律，`[L878]`「不允许只报第一个」的精神延伸）：
  `ConfigSemanticError.violations` / `WeightVersionInvalidError.violations` 均为
  `tuple[tuple[str, str, str], ...]`，元素 = `(check_id, path, detail)`；
  排序 = `(CHECKS.index(check_id), path)`，去重，**不截断、不限量**。
- 消息格式（SDD 未给，本 ADR 定死供 V-5 / P-11 断言）：
  `ConfigSemanticError` 首行 `配置语义校验失败 N 项（退出码 3）`，随后每行 `  - <check_id> <path>: <detail>`；
  `WeightVersionInvalidError` 首行 `权重版本校验失败 N 项（退出码 2，<RC.value>）`，随后同格式。

---

## 6. 公开契约（T06 必须逐字实现；R3 按此写 RED；R4 按此判定）

### 裁决 19：新增公开名清单与签名（11 个新名 + 1 个签名扩展）

```
EXIT_BLOCK = 2                                     # [L1080]/[L1280] 单一事实源，cli.py 必须 import
SEMANTIC_CHECKS: tuple[str, ...] = (
    'SUM_LEVEL1', 'SUM_LEVEL2', 'FLOOR_MONOTONIC', 'REDLINE_METRIC_EXISTS',
    'ACTION_NON_EMPTY', 'ANCHOR_MEMBER_EXISTS', 'STRUCTURE', 'NUMERIC')   # [L879] 原文序 + 两个前置类
WEIGHT_CHECKS: tuple[str, ...] = (
    'WEIGHT_COVERAGE', 'WEIGHT_STATUS_FROZEN', 'WEIGHT_WHATIF_RUN_ID',
    'WEIGHT_PROVENANCE_COMPLETE', 'WEIGHT_APPROVAL', 'STRUCTURE', 'NUMERIC')

class ConfigSemanticError(Exception):              # [L881] 逐字名
    def __init__(self, violations): ...            # 接受 (check_id, path, detail) 三元组的可迭代
    violations: tuple[tuple[str, str, str], ...]   # 已按裁决 18 排序去重
    reason_code: ReasonCode                        # 恒为 RC.CONFIG_SEMANTIC_ERROR
    exit_code: int                                 # 恒为 EXIT_CONFIG == 3

class WeightVersionInvalidError(Exception):        # [L881] 逐字名
    def __init__(self, reason_code, violations=()): ...
    reason_code: ReasonCode                        # 裁决 15 表内四枚之一
    violations: tuple[tuple[str, str, str], ...]
    exit_code: int                                 # 恒为 EXIT_BLOCK == 2

def to_decimal(value, *, path) -> Decimal          # H-4 数值入口（ORCH-23 裁决 4 转来）；
                                                   # 失败抛 ConfigSemanticError（NUMERIC 违规），不外泄 NumericError
def period_key(value) -> str                       # 裁决 8；非法形态抛 ConfigSemanticError（STRUCTURE）
def validate_semantics(cfg) -> None                # 纯函数；裁决 9/10/11；抛 ConfigSemanticError
def validate_cross_file(cfg, *, metric_ids, strategy_ids) -> None
                                                   # 纯函数；裁决 12/13；两参必填无默认；抛 ConfigSemanticError
def select_weight_stem(cfg, *, period) -> str      # 裁决 16；纯函数
def validate_weights(cfg, *, period) -> None       # 纯函数；period 必填无默认；裁决 15/17
def load_all(config_dir, *, period=None, run_at=None) -> AppConfig
                                                   # ORCH-23 裁决 11 预留的追加；run_at 本期不用
```

- T05 的 12 个公开名（`EXIT_CONFIG` / `REQUIRED_CONFIG_STEMS` / `WEIGHTS_GLOB` / `PLACEHOLDER_TOKENS` /
  `PLACEHOLDER_PREFIXES` / `ConfigTree` / `AppConfig` / `ConfigPlaceholderError` / `is_placeholder_value` /
  `find_placeholders` / `scan_config_trees` / `load_all`）**签名与行为一条不改**，`load_all` 只追加可选 kwarg。
- 三个 validate_* 与 `to_decimal` / `period_key` / `select_weight_stem` **必须是纯函数**（H-8）：
  不 I/O、不读写全局状态、不取墙钟、不修改入参、同输入逐字节同输出。
- **不得**新增第四个/第五个异常名（`[L881]` 只给三个，H-10）；**不得**建 `WeightSumError` /
  `WeightVersionNotFrozenError`（裁决 3）。

### 裁决 20：分层与写集（H-9）

- `dsm/config.py` 属 **L1**（`dsm/__init__.py` 分层注释实测：`L1 numeric / reason_codes / models / config / io_loaders`）。
- T06 允许**新增** import：`dsm.numeric`、`dsm.reason_codes`（同层 L1，无环：二者均不 import config）。
- T06 **不得** import：`dsm.models`（避免 L1 内重复 schema 与潜在环；配置校验直接在 `ConfigTree` 原始 dict 上做）、
  任何 L0a/L0b（INV-1）、`io_loaders`（S1 尚不存在）。
- INV-2 / INV-3 本期无关（config 不写 reports、不算熵权）。
- 写集（**严格四个文件 + 证据**，多一个不许碰）：
  `dsm/config.py`（追加 + 裁决 22 的一行 docstring）、
  `tests/test_config_semantic.py`（新）、`tests/test_config_weight_version.py`（新）、
  `tests/test_config_properties.py`（追加 P-11 属性；既有 P-10 用例一条不改）。
- `config/` 目录仍**不得**放任何文件（裁决 21）；`ops/`、`docs/`、只读区 CampaignLab、7 份工行文档一律不碰。

### 裁决 21：测试用配置一律合成（H-14）

- 所有 yaml 由测试用 `tmp_path` 现场生成，键名用 `SYN-*` 合成名，数值位置一律 `PLACEHOLDER`
  或**显式合成小数**（如 `'0.25'`）——注意：为验证 Σ = 1 必须给出具体权重值，这属**测试合成数据**
  而非「拟定业务数值」，允许；但 `dsm/config.py` 本体**不得**出现任何业务数值（H-5），
  容差只能引用 `numeric.TOL`。
- 随机性一律由 `--seed` 控制，同 seed 逐字节相等（H-14 / V-3）。
- T06 新增用例数由 R3 实测回报；全量 pytest 必须 0 failed / 0 error / **无新增 skip**。

### 裁决 22：顺手补 `_join` docstring（承接 ORCH-23 裁决 24 第 5 项）

`dsm/config.py` 的 `_join` docstring 补一句 ORCH-23 裁决 22 的 `[` 补口说明（相对路径以 `[` 开头时不插 `.`）。
**仅注释**，不得改 `_join` / `_walk` 的任何行为；R4 需比对改前后 `_join` 的字节码行为一致。

---

## 7. 本 ADR 新登记的 blocker（随 S1-T06 落库写入 ops/blockers.md）

| 编号 | 缺什么 | 谁签认 | 完成条件 |
|---|---|---|---|
| B-028 | 分册 L324「HARD 红线须 is_redline = true 且 dim_code 匹配」SDD `[L879]` 未列 | 行方评价管理部门 | 明确是否纳入 config 层；若纳入则追加判据与 RC |
| B-029 | `validate_cross_file` / `validate_weights` 的生产接线 | 开发（S3 / S9-T02） | 架构测试断言 preflight 引用二者并通过 |
| B-030 | `ConfigPlaceholderError` 无 reason_code 属性（T05 契约已冻结） | 行方 + 开发（S6） | audit 层按异常类型映射 `RC.CONFIG_PLACEHOLDER` |
| B-031 | `WeightVersionInvalidError` 退出码 2 与 `[L1080]`「3 = 配置错」的口径差 | 行方评价管理委员会 | 签认裁决 4 的映射表 |
| B-032 | 行方 yaml 若写裸小数需改字符串（裁决 7 拒 float） | 行方数据部门 | 提供权重/门槛的字符串写法样例 |
| B-033 | period 月粒度、双闭区间、一律补 `-01`（SDD 未给） | 行方评价管理部门 | 签认裁决 8 |
| B-034 | `level2_weights` 的 dim 键是否必须与 `level1_weights` 一致（SDD 未给） | 行方评价管理部门 | 明确后决定是否加入 T06 或 C-03 |
| B-035 | 分册「attainment_floor L4 可为 null」与 T05「None 一律命中」的冲突 | 行方评价管理部门 | 若允许 L4 空，须先改 T05 必填性口径 |
| B-036 | `[L879]` 单数 action vs `[L1205]` 复数 actions | 行方评价管理部门 | 签认裁决 11 取 `actions` |
| B-037 | `[L994]`「阈值必须引用行内既有制度文号」非机器可判 | 行方（R4 治理） | 提供文号字段与校验方式 |
| B-038 | anchor 成员存在性的双出口（`[L879]` 硬失败 vs `[L909]` WARN 回退） | 行方评价管理部门 | 签认裁决 13 的静态/动态分工 |
| B-039 | 多份 weights 同时覆盖一个评价期（SDD 未给） | 行方评价管理委员会 | 签认「保守判失败」或给出选择规则 |
| B-040 | 生产入口必须传 period（`load_all(period=None)` 仅供工具/测试） | 开发（S9-T01/T02） | 架构测试断言通过 |
| B-041 | AHP 的 CR 阈值（SDD 未给，H-5 禁拟定） | 行方评价管理委员会 | 给出 K-xx 编号与数值后追加校验 |
| B-042 | α 的取值范围（SDD 未给） | 行方评价管理委员会 | 同上 |
| B-043 | `EXPERT_ONLY` 是否也须具备 AHP 矩阵 + CR | 行方评价管理委员会 | 签认裁决 17 的保守超集 |

---

## 8. 验收清单（R3 写 RED / R4 判定，逐条可判定）

| 编号 | 判据 | 依据 |
|---|---|---|
| T06-A | 新增 11 个公开名逐字齐备、签名一致；T05 的 12 个公开名签名与行为**零变更**（`load_all` 仅追加可选 kwarg） | 裁决 19 |
| T06-B | `EXIT_BLOCK == 2`、`EXIT_CONFIG == 3`；`ConfigSemanticError(...).exit_code == 3`；`WeightVersionInvalidError(RC.X).exit_code == 2` | 裁决 4 |
| T06-C | 不得存在 `WeightSumError` / `WeightVersionNotFrozenError`（`hasattr` 均 False）；三异常平级继承 `Exception` | 裁决 3 |
| T06-D | Σ 判据：level1 之和 ≠ 1（差 > 1e-12）→ `SUM_LEVEL1`；差 ≤ 1e-12 → 通过；level2 逐 dim 同口径；**只校验 FROZEN 份**，DRAFT 份不校验 | 裁决 6 / 9 |
| T06-E | attainment_floor：L1>L2>L3>L4 严格递减通过；任两处相等或逆序 → `FLOOR_MONOTONIC`；四级不齐 / grade_code 重复 → `STRUCTURE` | 裁决 10 |
| T06-F | actions：空 list / 空 tuple / 空串 / 全空白串序列 → `ACTION_NON_EMPTY`；非空 → 通过；`action_gate` 为空**不**报错 | 裁决 11 |
| T06-G | 跨文件：`metric_ids` / `strategy_ids` 为必填入参（漏传 → TypeError）；引用不存在成员 → `REDLINE_METRIC_EXISTS` / `ANCHOR_MEMBER_EXISTS`；路径含 `[i]` | 裁决 2 / 12 / 13 |
| T06-H | 版本：0 份覆盖 → `RC.WEIGHT_VERSION_STALE`；≥2 份 → `RC.WEIGHT_VERSION_INVALID`；选中为 DRAFT → `RC.WEIGHT_VERSION_DRAFT`；FROZEN 缺 whatif_run_id → `RC.WEIGHT_MISSING_WHATIF_RUN_ID`；退出码恒 2 | 裁决 15 / 16 |
| T06-I | 区间闭合：period == effective_from 与 period == effective_to 均判**在期内**；`'2026-10'` 与 `'2026-10-01'` 等价；date 对象与字符串等价 | 裁决 8 |
| T06-J | P-11：三种 kind 的必填段矩阵逐条命中；`ahp.comparison_matrices` 为空 → 违规；CR / α **只判存在不判数值** | 裁决 17 |
| T06-K | 一次性列出全部违规：多处违规 → `violations` 长度 == 违规数，按 `(CHECKS.index, path)` 排序去重、不截断；消息首行含 N 与退出码 | 裁决 18 |
| T06-L | 数值口径：float / bool / 空串 / 不可解析串 → `NUMERIC` 违规且**不外泄** `NumericError`；`config.py` 内 float 字面量数 == 0；容差只引用 `numeric.TOL` | 裁决 6 / 7 + H-4 |
| T06-M | reason_code：全部违规路径的 `reason_code` 均为 `RC` 成员；`config.py` 内裸 reason 字符串字面量数 == 0（AST 扫描） | 裁决 5 + H-6/H-7 |
| T06-N | 纯函数：三个 validate_* / `to_decimal` / `period_key` / `select_weight_stem` 无 I/O、无 `global`/`nonlocal`、无墙钟、不改入参、幂等 | H-8 |
| T06-O | 分层：`config.py` 的 import 集 ⊆ {stdlib, yaml, pydantic, dsm.numeric, dsm.reason_codes}；`dsm.models` 不在 `sys.modules`；L0a/L0b 零命中 | 裁决 20 + INV-1 |
| T06-P | H-5：`dsm/config.py` 内**零业务数值**（权重/门槛/阈值/目标值/单价/周期/样本量/K-01~K-20 具体值）；`PLACEHOLDER` 与 `K-nn` 字样不被 T06 新代码用作默认值 | `[L78]` `[L1259]` |
| T06-Q | P-11 属性测试：任意「FROZEN 且 provenance 不完整」的合成权重树必被拦、必不产出 AppConfig；同 seed 逐字节可复现 | `[L1435]` 裁决 21 |
| T06-R | `_join` docstring 已补裁决 22 说明，且 `_join`/`_walk` 行为逐字节未变 | 裁决 22 |
| T06-S | 全量 pytest 0 failed / 0 error / 无新增 skip；T05 落库后的既有一条不坏 | ORCH §6 S1 门禁 |

---

## 9. 依据行号汇总

SDD `[L78]` `[L150]-[L151]` `[L154]` `[L301]` `[L379]-[L380]` `[L386]` `[L394]` `[L493]` `[L647]`
`[L678]-[L679]` `[L877]` `[L879]-[L882]` `[L889]` `[L898]` `[L900]-[L902]` `[L909]` `[L911]` `[L917]`
`[L994]` `[L1080]` `[L1091]` `[L1105]-[L1106]` `[L1180]-[L1184]` `[L1190]-[L1194]` `[L1200]-[L1206]`
`[L1212]-[L1214]` `[L1228]-[L1245]` `[L1251]` `[L1254]` `[L1259]` `[L1280]-[L1282]` `[L1285]-[L1286]`
`[L1298]` `[L1307]` `[L1372]-[L1374]` `[L1413]` `[L1429]` `[L1435]` `[L1438]` `[L1508]` `[L1536]` `[L1548]`
非权威分册（仅对照，不采纳）：DESIGN-详细设计 L312-L313 / L320 / L323-L325。
仓内：`dsm/__init__.py` 分层注释、`dsm/numeric.py`（`D` / `TOL` / `ONE` / `eq_tol` / `from_float`）、
`dsm/reason_codes.py` 第 31-36 行五枚 RC、`dsm/models.py`（`WeightVersionDoc` / `WeightProvenance` /
`AhpSegment` / `CombineSegment` / `GradeRuleRow` / `AnchorSetDoc` 字段名逐字）、`docs/digest/S1-T06.md`（含 ⚠ 事实记录 13 条）。
ORCH：§2 H-4/H-5/H-6/H-7/H-8/H-9/H-10/H-11/H-14、§3.1 打分、§5 第 181 行 S1-T06、§6 S1 门禁、§10.2-2、§10.2-4；
ORCH-14 L39、ORCH-16 裁决 1、ORCH-20 裁决 1/2 + L145、ORCH-21 裁决 9、ORCH-22 裁决 31/34、ORCH-23 裁决 3/4/6/8/9/10/11/12/13/19/22/24。
