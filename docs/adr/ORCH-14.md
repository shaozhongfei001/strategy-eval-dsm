# ORCH-14 target_value / threshold_value 是 unit 多态列，不得静态声明为 Decimal

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02（R4 复核质询点 B3，判 ❌ 必修） |
| 裁决人 | Orchestrator（主控），采纳 R4 独立复核结论 |
| 类型 | 口径裁决（H-4 优先于 digest 沉默） |

## 事实

- SDD [L1138]：`unit ∈ {MONEY_MINOR（最小货币单位）, COUNT, RATIO, DURATION_SEC}`
- SDD [L1139]：`target_value` / `target_basis`（**未给类型**）
- SDD [L1181]：`comparator ∈ {GT,GTE,LT,LTE}` / `threshold_value`（**未给类型**）
- SDD [L1265]：金额 = int（最小货币单位，字段名后缀 `_minor`）；比较 = 精确相等；**全链路不经 float**
- SDD [L1266]：计数 = int；精确相等
- SDD [L1267]：比率/达成率/权重/均值 = Decimal（字符串构造）；1e-12 容差
- 被复核实现：`dsm/models.py` L145 `target_value: Ratio`、L214 `threshold_value: Ratio`
- R4 实测：`unit='MONEY_MINOR'` 时 `target_value=100`（int）落地 `Decimal('100')`；`Decimal('100.50')` **被接受**

## 裁决

digest 对这两列的类型沉默，但 [L1138] 已明示它们是 **unit 多态列**，
而 [L1265]/[L1266] 对金额与计数规定了 int 口径。把可为 MONEY_MINOR/COUNT 的列静态声明为 Decimal，
等于在契约层宣称「金额用 Decimal」，**直接违反 H-4**。H-4 是硬约束，优先级高于 digest 的沉默。
另：同文件已用 `FactValue = MoneyMinor | Ratio` 解决同类多态，L145/L214 未沿用属内部自相矛盾。

**分两种情形处置（不得混）：**

1. `MetricDictRow.target_value` → 改多态联合（int 落 int / Decimal 落 Decimal），
   并加 `model_validator(mode='after')` 做 **unit 交叉校验**（`unit` 在同一行内，可校验）：
   - `MONEY_MINOR` → 必须 `int`（非 bool）；Decimal / float 一律拒
   - `COUNT` → 必须 `int`
   - `RATIO` → 必须 `Decimal`；int / float 一律拒
   - `DURATION_SEC` → **不加约束**（见下方缺口）
   - `target_value is None` → **跳过校验**（[L930] 目标缺失 → attainment = null 是合法状态）
2. `RedlineRow.threshold_value` → 只改多态联合，**不加 unit 交叉校验、不新增 unit 字段**。
   RedlineRow 只有 `metric_id`（[L1180]），unit 在 metric_dict 内，模型层无从校验；
   该校验归 S1-T06 config 语义校验（[L879]「红线阈值引用的指标必须存在于 metric_dict」）。**不得提前实现**。

## 连带登记的两个缺口

- **GAP-1 `DURATION_SEC` 口径沉默**：[L1265]（金额）/[L1266]（计数）/[L1267]（比率）三类均未覆盖「秒数」。
  按 §10.2-4 不发明口径 → 不加约束，登记 `ops/blockers.md` B-007 待设计方确认。
- **GAP-2 `MetricFactRow.value` 接受带小数金额**：R4 实测 `value=Decimal('100.50')` 被接受。
  MetricFactRow 不含 unit，模型层无从判定该值是否为金额。
  SDD [L889] 已明确把「金额列必须解析为 int（失败即记 C-09）」指派给 **io_loaders**，
  故本项**不在 S1-T02 修**，转为 S3-T01 的验收项，登记 B-008。

## 依据

SDD L1138 / L1139 / L1181 / L1265 / L1266 / L1267 / L930 / L889 / L879 / L1180；ORCH §2 H-4、卷首「与 SDD 冲突以 SDD 为准」、§10.2-4。
