# ORCH-20：WeightProvenance 四段可空性、α 键类型与 7 项歧义的裁决（S1-T03）

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-24 |
| 阶段 / 任务 | S1 / S1-T03（R3 交付后、R2 实现前） |
| 裁决人 | Orchestrator（主控） |
| 类型 | 契约裁决（H-11：无人值守下由主控依 SDD 原文行号判定，落本 ADR 视为签认） |
| 依据 | `docs/digest/S1-T03.md`（SDD 708679e9a83d / 2003 行）；ORCH-02 / ORCH-13 / ORCH-15 / ORCH-16 / ORCH-17 / ORCH-18 |

R3 在交付报告第 7 段提出 7 个歧义点。逐条裁决如下。**裁决 1 与裁决 5 要求 R3 改测试**（属 L1 阶段的定向修正，
不是放宽断言）；其余按 R3 已落地口径确认。

---

## 裁决 1：四段 `ahp / entropy / combine / alpha_basis` 在 **models 层一律可空**（推翻 R3 的"必填非 None"）

R3 原方案：四段必填非 None，`AHP_ONLY` 用"空集合快照"占位。

**改为**：四段均为 `Optional[<段模型>] = None`。理由（三条原文口径一致指向"存在性校验属加载层"）：

1. [L1435] P-11 原文：「任何 **FROZEN** 权重版本必须具备完整 provenance（AHP 矩阵 + CR；
   **若 combined 则含** α + alpha_basis + whatif_run_id），缺任一项 → **配置加载失败**」。
   两点关键：①义务主体是 FROZEN 版本，不是所有实例；②失败点是**配置加载**，不是模型构造。
   [L1435] 的「若 combined 则含」本身就是**条件式**要求，与"四段恒必填"直接冲突。
2. [L1241] `whatif_run_id`：「FROZEN 而缺此项 → **配置加载**直接失败」；[L880] 与 [L1281] 同旨。
   S1-T02 已据此把 `whatif_run_id` 做成可空、把检查留给 S1-T06。四段若必填，将与同一份原文的
   既定处理**自相矛盾**。
3. **H-5 反证**：`kind = EXPERT_ONLY` 或 `AHP_ONLY` 时并不存在熵权标定数据。若强制 `entropy` 段非空，
   生产者只能填"空集合/零值快照"，而零是**业务数值**，等于逼迫实现方拟定数据 —— 违反 H-5。
   可空是唯一不需要捏造数值的口径。

**"§3.11.4 四段齐全"（ORCH §5 S1-T03 验收项）的解释**：指 `WeightProvenance` **声明**了
`ahp / entropy / combine / alpha_basis` 四个段、且每段是**独立的子模型类型**（不是一个 dict 混装），
并非"每个实例四段都非空"。R3 已有的 `test_all_four_segments_are_declared` /
`test_segment_annotations_are_basemodel_subclasses` 正是该验收项的正确载体，**保留**；
`test_every_segment_is_required_not_nullable` **改为**断言四段可空且默认 None，并新增一条断言：
「四段的存在性/条件式必填校验**不在 models 层**，归 S1-T06（config 语义校验，[L1435][L880]）」，
写法参照 R3 已有的 `test_models_layer_does_not_grow_a_status_column_for_the_frozen_rule`。

## 裁决 2：`WeightVersionDoc.provenance` **可空、默认 None**（确认 R3 方案）

依据同裁决 1 第 1、2 条：[L1435]「FROZEN 必须具备完整 provenance …… 缺任一项 → 配置加载失败」是
**加载层**义务，归 S1-T06；[L1193] 只声明 `provenance.*` 见 §3.11.4，未规定非空。
另：S1-T02 已冻结的 341 条基线用例的 T6 payload 不含 provenance，模型层必填会破坏既有 golden（H-11 禁止）。
`test_weight_version_doc_without_provenance_still_builds` 保留。

## 裁决 3：子模型与字段命名表**认可**，但附三条强制约束（确认 R3 方案 + 加约束）

SDD 只逐字给出 `per_period_entropy` 与 `drift_by_metric` [L1777]；其余名称是 R3 对 [L1232]-[L1240]
散文的规范化映射。依 ORCH-16（SDD 逐字名优先）与 ORCH-13（最小可推导闭包）认可该表，约束：

1. **逐字名不得改写**：`per_period_entropy` / `drift_by_metric` 必须原样使用 [L1777]。
2. **每个派生字段必须带行内 `[Lxxxx]` 注释**，指向 [L1232]-[L1240] / [L636] 中的具体承重行；
   R4 逐字段核对"该字段能否指回某一行原文"，指不回的一律判 ❌ 要求删除（同 ORCH-13 裁决 3）。
3. **`CalibrationReport` 这个类名不得在 `dsm/models.py` 占用**：[L1072] 它是
   `weights_calibrate.py`（L0b）的返回类型名，属 S7-T0x；`alpha_basis` 段的类名另取
   （如 `AlphaBasisSegment`），避免与 L0b 契约撞名（H-9 分层清晰）。

## 裁决 4：CEL-0 按 **7** 字段（无需再裁，重申 ORCH-02）

[L1894] 表格 8 项 vs [L1918] 7 字段的歧义已由 ORCH-02 裁定：`interpretation_limit` 是 T4 正式字段
[L1172]，不属 CEL 预留。S1-T02 已落地 7 字段，本任务只做**回归固化**（`CEL0_RESERVED` 恰为 7、
`DesignCardRow` 字段集与 S1-T02 逐字相同）。

## 裁决 5：`α` 一律是 `Ratio`(Decimal)，**禁止**把 α 当作裸字符串字典键（推翻 R3 的 str 键）

R3 原方案：`candidate_alpha_matrix = {'0.3': {...}, '0.7': {...}}`、`excluded_alphas = {'0.3': RC....value}`，
即 α 以 **str 作字典键**。

**改为**：`candidate_alpha_matrix: dict[Ratio, dict[str, Ratio]]`、`excluded_alphas: dict[Ratio, ReasonCode]`。理由：

1. **H-4 硬性**：α 是权重/比率（[L1236]「α 值」、K-15 `alpha_floor`、[L638] P-13 治理参数），
   「比率/达成率/权重/均值一律 Decimal（字符串构造）」。把比率塞进 str 键，等于让一个比率
   **绕过 numeric 闸门**以字符串形态存在于契约里 —— 与 S1-T02 已确立的 `Ratio` 闸门直接冲突。
2. **候选集去重失真（实测）**：[L636]/[L1239] 的 `alpha_basis` 要承载「**全部候选 α** × 全部指标的矩阵」，
   [L1072] 还要在「字典序可行集取**最小可行 α**」。str 键下同一个 α 的不同写法是**不同的键**：
   实测 `{'0.5','0.50','0.7'}` 有 **3** 个不同键，而 `[Decimal('0.5'),Decimal('0.50'),Decimal('0.7')]`
   只有 **2** 个不同值 —— 候选集**虚增**了一个并不存在的 α，可行集与「最小可行 α」随之失真。
   **实测更正（按 B-012 留痕）**：本 ADR 初稿曾以「str 字典序给出错误最小值」为理由，该理由**不成立**：
   α 落在 `[0,1)` 且写作 `0.x` 时，str 字典序与数值序一致（实测 `sorted(['0.9','0.10','0.3'])` =
   `['0.10','0.3','0.9']`，与 Decimal 排序相同）。故本裁决**只**以「去重失真 + 相等判定失真」两条为据。
3. **H-11 相等判定（实测）**：α 的相等必须走 `numeric.eq_tol`（1e-12）。实测
   `Decimal('0.70') == Decimal('0.7')` 为 **True**，而 `'0.70' == '0.7'` 为 **False** ——
   str 键会把同一个 α 判为两个不同候选，且用数值算出的 `alpha_star` 反查 str 键矩阵时会**查不到**。

对应地，`alpha_star: Ratio`（R3 已是 Decimal，确认）。R3 需把 `RATIO_PATHS` 中
`('alpha_basis','candidate_alpha_matrix','0.3',METRIC_A)` 一类路径的键改成 Decimal 构造，
并把 `excluded_alphas` 的键改成 Decimal；`build_with` / `get_at` 辅助函数需支持 Decimal 键寻址。

**不受本裁决影响的 str 键**（确认可用 str）：`excluded_periods` 的期标识（`'2026-04'`）、
`per_period_entropy` / `window_periods` / `calibration_periods` 的期标识、`comparison_by_metric` 与
`drift_by_metric` 的 `metric_id`、`comparison_matrices` 的 expert_id / metric_id、
`binding_constraints` 的约束名 —— 这些都是**标识符/名称**，不是数值，str 是正确类型。

## 裁决 6：`seed` 与 `entropy_weight` 的可空性（部分推翻 R3）

1. `alpha_basis.seed` **可空**（`StrictInt | None = None`）。依据 [L636] 原文括注「seed（**若含 MC**）」——
   不含 MC 的标定没有 seed。R3 的 `test_seed_rejects_every_lax_int_form` **保留**（H-4/ORCH-18 的
   lax 强转闸门与可空性正交：None 合法，但 `True` / `3.0` / `'3'` / `Decimal('3')` / `b'3'` 一律拒绝）。
2. `comparison_by_metric[*].entropy_weight` **可空**（`Ratio | None = None`）。依据 [L1235]
   「命中 **INACTIVE 回退**的指标清单」：INACTIVE（零变异）指标的熵权在数学上**未定义**，
   强制必填会逼迫生产者填 0 或某个捏造值（H-5）。回退语义由同表的 `is_fallback` 列承载 [L1237]，
   不依赖 `entropy_weight` 非空。
   注意：`numeric.safe_div` 的 `on_zero` 参数本就是为"真未定义"设计的（可为 None），本裁决与之同旨。
   `ahp_weight` / `combined_weight` **仍为必填** `Ratio`（[L1237] 四列中这两列恒有值；
   且 ORCH §5 S8-T01「INACTIVE 回退不被稀释：命中回退的指标**组合权重严格等于 AHP 权重**」
   要求这两列必须可比对）。
   `is_fallback` 仍为必填 `StrictBool`（ORCH-18）。

## 裁决 7：`hard_check_results` **不在 models 层封闭键集**（确认 R3 方案）+ 登记缺口

[L1238] 只写「H-1~H-5 校验结果」，**SDD 的 H-1~H-5 具体定义不在 S1-T03 授权区间内**
（本任务 13 个区间未含其定义处），且与 ORCH §2 自己的 H-1~H-14 **同名不同义**，极易混淆。
故 models 层取 `dict[str, StrictBool]`，只固化"值是严格 bool"（ORCH-18），**不**固化键集。
键集口径待 S8-T01（`weights_combine.py`，ORCH §5 明列「H-1~H-5 校验」）取到 SDD 原文后确定，
登记为 `ops/blockers.md` **B-016**（不阻塞 S1-T03）。

## 裁决 8：「被剔除期 / 被排除 α 及原因」的载体（确认 R3 的 dict 形态，键类型见裁决 5）

[L1235]「被剔除期及原因」→ `excluded_periods: dict[str, ReasonCode]`（期标识为 str，确认）。
[L1240]「被排除 α 及原因」→ `excluded_alphas: dict[Ratio, ReasonCode]`（**键为 Decimal**，见裁决 5）。
两者的 reason 必须走 `ReasonCode` 闸门（H-6/H-7：只接受已注册 `RC.<NAME>`，裸字面量拒绝）。
不采用"pair 子行元组"方案：dict 已能表达"每项一个原因"，且 `extra=forbid` + `ReasonCode` 闸门
已提供等强的约束，再引入子模型属过度设计（L2 最小实现纪律）。

---

## 落地顺序

1. **R3（R6 定向修正）**：按裁决 1 / 5 / 6 改 `tests/test_models_provenance.py`，重跑确认
   **仍是 RED**（failed 计数可变，但 **error / collection error 必须为 0**，失败异常类型仍限于
   `AttributeError` 与 `ValidationError`），刷新 `ops/evidence/S1-T03/L1-red.txt`。
   **禁止**为了让数字好看而删用例或加 skip。
2. **R2（另一个 agent 实例）**：只拿 `docs/digest/S1-T03.md` + 本 ADR + 测试文件 + 既有公开签名，
   **禁止读 SDD 原文**（ORCH §4 R2 禁令），实现 `WeightProvenance` 及四段子模型 +
   `EvidenceSource` + `WeightVersionDoc.provenance` 接线，令全量测试转绿。
3. **R4（第三个 agent 实例）**：只拿 digest + 本 ADR + pytest 输出 + `git diff`，逐条核对，
   重点复核裁决 1 / 5 / 6 是否真的落地（Decimal 键、四段可空、entropy_weight 与 seed 可空）。

## 影响面

- 只影响 `dsm/models.py` 与 `tests/test_models_provenance.py`；`dsm/numeric.py`、`dsm/reason_codes.py` 不改。
- 不改变任何 S1-T02 已冻结的 341 条基线用例的期望值（H-11）。
- S1-T06 接手：四段的 kind 条件式必填校验、FROZEN 缺 `whatif_run_id` → 加载失败（[L880][L1281][L1435]、C-01 [L900]）。
- S8-T01 接手：`hard_check_results` 键集（B-016）、四列对照表的生成。
