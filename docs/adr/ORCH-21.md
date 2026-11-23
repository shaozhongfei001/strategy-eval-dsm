# ORCH-21：S1-T03 R4 复核后裁决（calibration_report_ref 可空、ENTROPY_UNSTABLE 归属、6 项 ⚠ 处置）

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-24 |
| 阶段 / 任务 | S1 / S1-T03（L4 R4 复核之后、L6 落库之前） |
| 裁决人 | Orchestrator（主控） |
| 类型 | 复核后裁决（H-11：无人值守下由主控依 SDD 原文行号判定，落本 ADR 视为签认） |
| 输入 | R4 独立复核报告（三审 35 条：✅28 / ⚠7 / ❌0，总判定 **PASS**）；`docs/digest/S1-T03.md`；`docs/adr/ORCH-20.md` |
| 前置 | ORCH-20 的 8 项裁决经 R4 逐条实测确认**全部落地**（C1~C8 全 ✅），本 ADR 只处理 R4 提出的 7 个 ⚠ |

R4 未判任何 ❌，故本 ADR 不是返工裁决，而是**对 7 个 ⚠ 的处置裁决**。其中 ⚠-2 与 ⚠-7 涉及契约，
必须由主控裁定后才能动代码（R4 明确要求「在裁决落地前 R6 不得自行改动该行」）。

---

## 裁决 9（⚠-7 / G3）：`CombineSegment.calibration_report_ref` 改为**可空** `str | None = None`

**采纳 R4 建议。** 三条依据（均可指回 digest 承重行）：

1. **[L634] 存在一条"标定根本没发生"的明文路径**：「熵权样本不足 → **跳过标定**，直接 α = 1，
   记 `ENTROPY_INSUFFICIENT_SAMPLE`」。该码已在 `dsm/reason_codes.py` 注册。标定被跳过 →
   **不存在 [L636] 定义的 CalibrationReport** → 不存在"α 标定报告引用"。而此时 `combine` 段
   仍必须生产（α=1 要落 [L1236] 的 α 值、[L1237] 的四列对照表），必填 `str` 就会
   **逼迫生产者捏造一个引用字符串**。
2. **[L1236] 把 α 来源封闭为 `{CALIBRATED, MANUAL}` 二值**（R4 实测 `get_args` 恰 2 值）。
   `MANUAL` 时 α 出自治理决策而非标定运行，"α **标定**报告引用"无所指；[L634] 的跳过路径
   也只能落在这两值之一，语义上记 `MANUAL` → 必填引用在该路径上**必然空指**。
3. **与 ORCH-20 裁决 1 / 裁决 6 同一条推理**：可空是唯一不需要捏造的口径。此处风险**更高** ——
   捏造出来的是一个**看起来可审计的引用字符串**，会直接污染 [L636] 要求的「可审计链闭环」，
   比填一个 0 更隐蔽，属 H-6「无静默降级」精神的反面。

**对"保持必填"一方论据的回应**：[L1236] 确为平铺列举、无条件式措辞，但该列的**所指对象**
（CalibrationReport）在 [L634] 路径下不存在；"MANUAL 时填治理决议文号"这一替代口径
**在授权区间内找不到任何一处命名过这样一份治理文档**（[L636] 只命名 CalibrationReport），
属实现方自拟，比可空更弱（H-11）。

**落地要求**：
- `dsm/models.py` L427 改为 `calibration_report_ref: str | None = None  # [L1236]/[L634] ...`
- **新增 1 条测试** `test_calibration_report_ref_accepts_none_when_alpha_is_manual`：
  构造 `alpha_source='MANUAL'` 且 `calibration_report_ref=None` 必须成功；
  同时保留"给了 str 就落 str"的正向断言。
- R4 实测变更成本：`tests/` 中该字段仅 2 处命中（payload 取值 + `COMBINE_FIELDS` 元组），
  **无任何测试断言它拒绝 None** → 本裁决**不修改任何既有断言、不改变任何 golden 期望值**（H-11 安全），
  既有 341 + 237 = 578 条用例期望值一条不变。

## 裁决 10（⚠-2）：`ENTROPY_UNSTABLE` 标注**不在 models 层设载体**，归 S8 与报告层

digest [L1777]（RK-13）原文两句：「provenance.entropy 保留 `per_period_entropy` 与 `drift_by_metric`
（字段名原文）；**drift 超阈值指标标注 `ENTROPY_UNSTABLE`**」。前半句已落地（R4 字节级核对 ✅）。
后半句在 `EntropySegment` 的 6 个字段中**无载体**（R4 实测 `ENTROPY_UNSTABLE` 在 `dsm/models.py`
出现 **0** 次，该码在 `reason_codes.py` 已注册）。

**裁决：不加字段。** 理由：
1. ORCH-20 裁决 3 已认可 [L1234]-[L1235] 推出的 **6 字段** entropy 表；加第 7 字段会**违反该裁决**，
   且 [L1234]-[L1235] 原文并未把"不稳定标注"列为 entropy 段的组成部分。
2. "超阈值"的阈值是 **`drift_budget`（K-16，治理参数）**，依 H-5 现为 `PLACEHOLDER`、**未签认**。
   在阈值未定的情况下于契约层预留一个"标注集合"，该集合**永远无法被正确填充**，
   反而会诱导实现方拟定阈值（H-5）或静默留空（H-6 反面）。
3. 该标注是**派生结论**而非**输入事实**：可由已落地的 `drift_by_metric`（[L1234]/[L1777] 逐字名）
   与 `drift_budget` 在 **L0a `weights_entropy` / `weights_combine`（S7/S8）** 比对后产出，
   并由报告层披露。这与 ORCH-15 把 `evidence_source`（判定结果）划归输出侧是**同一条原则**。

**登记**：`ops/blockers.md` **B-018** —— 完成条件：S8-T01（`weights_combine.py`）取到 SDD 中
`drift_budget` 阈值口径与 `ENTROPY_UNSTABLE` 标注落点的原文后，决定标注的承载位置
（Frame 列 / 报告段 / provenance 追加字段），补 ADR 后回填。与 B-016（H-1~H-5 键集）同批交 S8。

## 处置 11（⚠-1）：接受现状 + **补录** `test_models_input.py` 的 RED 证据

R4 实测：`tests/test_models_input.py` 的 +8/-10（删白名单预授权项 + `provenance` 入 `DIGEST_FIELDS`）
制造了 1 条新 RED —— 用 HEAD 的 `dsm/` 跑当前 tests 得 `1 failed, 340 passed`，
失败项 `test_every_digest_named_field_is_declared[WeightVersionDoc]`，异常类型 **`AssertionError`**
（`tests/test_models_input.py:649`）。该 RED **实质成立**（R4 已独立复现），但 `L1-red.txt`
只含 `test_models_provenance.py` 的 237 条。

**裁决**：RED 判据满足（§7.2 L1 只要求"有失败输出证据 + 失败原因是功能未实现"，
`AssertionError: WeightVersionDoc is missing digest-named fields: provenance` 正是功能未实现）。
但为审计完整，**必须把 R4 复现的这段追加进 `ops/evidence/S1-T03/L1-red.txt` 末尾**，
并显式注明：①来源是既有测试文件的**门禁收紧**（不是新文件）；②异常类型是 `AssertionError`，
在 ORCH-20 落地顺序 1 声明的 `{AttributeError, ValidationError}` 之外，原因即①。
**同时修正 ORCH-20 落地顺序 1 的措辞适用范围**：该措辞只约束 `tests/test_models_provenance.py`。

## 处置 12（⚠-3）：接受跨 digest 引用 `[L889]`，**不改代码**

R4 实测 4 处行内注释含 `[L889]`（`interview_dates` L384、`approved_date` L470、
`effective_from` L471、`effective_to` L472），而 `docs/digest/S1-T03.md` 的 46 个行号 token 中无 L889。
**裁决接受**：①这 4 个字段**同时**引用了 S1-T03 digest 内的承重行（`[L1232]` / `[L1242]`），
ORCH-13 裁决 3 的"能否指回某一行原文"判据**成立**；②`[L889]`（日期列必须 ISO 格式）已在仓内
`docs/digest/S1-T01c.md` L17 落盘，且 HEAD 的 `dsm/models.py` 已引用 7 次（现 11 次），
是 S1-T02 既定的**跨 digest 引用惯例**。**纪律明确化**：行内 `[Lxxxx]` 允许引用**任何已落盘 digest**
覆盖的 SDD 行，但该 digest 必须已入库（`docs/digest/INDEX.md` 可查）；不得引用未落盘的行号。

## 处置 13（⚠-4 / ⚠-5 / ⚠-6）：一次性**纯文档与补强**定向修（不动任何注解与断言语义）

R6 一轮做完以下 4 项（全部零契约风险）：
1. **⚠-4 行尾换行**：`tests/test_models_provenance.py`、`docs/digest/S1-T03.md`、
   `docs/adr/ORCH-20.md`、`docs/digest/INDEX.md`、`docs/adr/ORCH-21.md` 补末尾 `\n`，
   使仓库 8 个 `.py` 全部以 LF 结尾（H-3 三项本已全过、`normalize --check` 为 0，此项属一致性）。
2. **⚠-5 过时 docstring（3 处，必须改）**：
   - `dsm/models.py` **L1**：模块现含 14 个模型类 + `EvidenceSource`，"the eight input rows" 已不完整；
   - `dsm/models.py` **L56-L57**：`Not in scope for S1-T02 (ORCH-13): WeightProvenance and the CEL-0
     contract / wiring (S1-T03)` 两句皆已不成立（`WeightProvenance` 现于本文件 L373-L472；
     CEL-0 七字段 R4 实测在 **HEAD 就已落地**，`DesignCardRow` 23 字段已含全部 7 项）；
   - `dsm/models.py` **L477**：`provenance [L1193] is S1-T03 scope (ORCH-13)` 的推迟语气会**误导
     S1-T06 的实现者**以为该列尚未接线（实际就声明在 12 行之下）。
   依据：H-10 可辩护性 —— 文档与代码不一致会让下游按错误前提实现。
3. **⚠-6 补 1 条类名钉住测试**：R4 实测 `AhpSegment` / `EntropySegment` / `MetricWeightComparison` /
   `CombineSegment` / `AlphaBasisSegment` 这 **5 个类名在测试中命中 0 次**（测试经
   `_segment_class(annotation)` 从契约反解，故 ORCH-20 裁决 3 认可的命名表**无测试钉住**，
   未来改名不会红）。新增一条断言钉住这 5 个类名与四段的类名对应关系。
4. **裁决 9 的落地**（models.py L427 一行 + 新增 1 条测试）。

## 不需要处置的项

- **⚠-6 的"2 个字段弱覆盖"**（`calibration_periods`、`calibration_report_ref` 仅由字段集等值断言覆盖）：
  两者均为 **str 标识符列**，类型已由注解锁定，且 `calibration_report_ref` 经裁决 9 已补专项测试。
  `calibration_periods` 不另补（L2 最小实现纪律，避免为覆盖率而写无信息量的测试）。
- R4 的信息性实测（`numeric.D` 接受裸 int → `Decimal`）：属 **S1-T02 既有共享闸门**行为，
  S1-T03 未改动；float / bool 一律拒，H-4「不经 float」的意图保持。`Ratio` 无 `[0,1]` 上界是**正确的** ——
  λ_max ≥ 1、Saaty 标度至 9 都需表达。**不改**。

---

## 收敛要求（L5 → 回到 L3）

R6 一轮修完后，主控按 §7.3 复验：
1. 全量 `pytest tests/` **0 failed / 0 error / 0 skipped**，且用例总数 **≥ 664**
   （裁决 9 与处置 13-3 各新增至少 1 条，预期 ≥ 666）；
2. `normalize.py --check` = `NEEDS_NORMALIZATION 0 of N files`；
3. 全部变更文件 BOM=False / CR=0 / TAB=0 / strict-utf8=True / **以 LF 结尾**；
4. `git diff --numstat dsm/models.py` 的**删除行只能是** L1 / L56-L57 / L427 / L477 这几处
   docstring 与注解改写，**不得**出现任何既有字段被删或类型被放宽；
5. `ops/evidence/S1-T03/L1-red.txt` 已追加 R4 复现段；`L3-green.txt` 刷新为修复后的全量输出
   且**含结尾汇总行**（B-017）。

## 影响面

- 只影响 `dsm/models.py`（1 行注解 + 3 处 docstring）、`tests/test_models_provenance.py`（+2 函数）、
  `ops/evidence/S1-T03/*.txt`、4 个文件的行尾换行。
- 不改任何既有断言、不改任何 golden 期望值（H-11）。
- 转后续阶段：**B-016**（H-1~H-5 键集 → S8-T01）、**B-018**（`ENTROPY_UNSTABLE` 标注落点 → S8-T01）。
