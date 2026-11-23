# ORCH-16 `_minor` 后缀约定与 SDD 逐字字段名冲突时，以 SDD 为准

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02（R4 复核质询点 B4）；约束全阶段所有模块 |
| 裁决人 | Orchestrator（主控），采纳 R4 建议 |
| 类型 | 命名口径裁决（H-4 的适用边界限定） |

## 事实

- ORCH §2 H-4：「金额与计数一律 int（最小货币单位，**字段名后缀 `_minor`**）且精确相等」
- SDD [L1265]：金额 = int（最小货币单位，**字段名后缀 `_minor`**）；比较 = 精确相等；全链路不经 float
- 但 SDD 自己给的**逐字字段名**里没有 `_minor`：
  - [L1150] `value_num` / `value_den` / `value`（并注明「金额用最小货币单位整数」）
  - [L1174] `incremental_value` / `incremental_ci_lower` / `incremental_ci_upper`（CEL-0 预留）
  - [L1139] `target_value`、[L1181] `threshold_value`
- R4 实测：`dsm/models.py` 中 `*_minor` 字段命中数 = **0**

## 裁决

1. **保留 SDD 逐字字段名，不加 `_minor` 后缀、不重命名任何字段。**
   依据 ORCH 卷首「与 SDD 冲突时**一律以 SDD 为准**」：SDD 的字段名是契约事实，
   [L1265] 的后缀约定是**表述性惯例**，两者冲突时前者胜。
   且这些列是 **unit 多态列**（[L1138]），静态加 `_minor` 会错误宣称「这列永远是钱」，
   对 `unit = RATIO` 的指标反而是**错误信息**。
2. `_minor` 后缀约定的**适用范围限定**为：无歧义的**纯金额列**（该列在任何 unit 下都只能是钱）。
   本 8 张输入表中**不存在**这种列（R4 实测 0 命中），故 S1 无适用对象。
   后续阶段（S4~S8）若出现纯金额列（例如 value_captured 的金额形态、报告层的金额汇总列），
   **必须**加 `_minor` 后缀，R4 届时按本条判定。
3. 金额语义**由类型与校验器保证，不由字段名保证**：
   多态列一律用 `MoneyMinor | Ratio` 联合（int 落 int、Decimal 落 Decimal、float/bool 双支皆拒），
   能拿到 unit 的（如 MetricDictRow）再加 `model_validator` 做 unit 交叉校验（见 ORCH-14）。

## 依据

SDD L1138 / L1139 / L1150 / L1174 / L1181 / L1265；ORCH 卷首「以 SDD 为准」、§2 H-4；R4 实测 grep 0 命中。
