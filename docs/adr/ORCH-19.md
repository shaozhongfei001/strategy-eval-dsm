# ORCH-19：commit ffa9a30 message 中 8 个 Row 类名勘误（H-12 禁改历史 → 以本 ADR 为准）

- 裁决编号：ORCH-19
- 日期：2026-11-23
- 阶段 / 任务：S1 / S1-T02（落库后自检发现）
- 裁决人：Orchestrator（R5 落库后 L3 复核）
- 类型：文档记录勘误（不涉及代码变更，不触发回归）

## 1. 事实

commit `ffa9a30`（S1-T02 落库）的 message 正文把 8 个输入 Row 写成了：

    CardMetaRow / CardWeightRow / MetricFactRow / TargetRow / ThresholdRow /
    PenaltyRow / RedlineRow / SampleRow

该串来源是上一会话交接摘要的转述，**未经实测**。落库后以 `vars(dsm.models)` 实测比对，
`dsm/models.py` 中真实的 8 个输入 Row（继承 `_InputRow`，`frozen=True, extra='forbid'`）为：

| # | 类名 | models.py 行号 | SDD 依据（digest 标注） |
|---|------|---------------|------------------------|
| 1 | `StrategyMasterRow` | L209 | [L1099]、[L1112]-[L1124] |
| 2 | `MetricDictRow` | L226 | [L1131]-[L1139] |
| 3 | `MetricFactRow` | L272 | [L1150]-[L1151] |
| 4 | `DesignCardRow` | L291 | [L1173] |
| 5 | `RedlineRow` | L324 | [L1180]-[L1181] |
| 6 | `WeightVersionDoc` | L336 | [L1190] |
| 7 | `GradeRuleRow` | L352 | [L1200] |
| 8 | `AnchorSetDoc` | L366 | [L1895] |

基类 `_InputRow` 在 L203。message 中其余技术表述经复核**准确**：
数值闸门实测为 `MoneyMinor`(L102) / `Ratio`(L103) / `FactValue`(L110) / `MinorUnits`(L127) /
`UnitValue`(L128) / `StrictInt`(L186) / `StrictBool`(L187) / `ReasonCode`(L153) /
`MetricDirection`(L163)，其中 `FactValue = MoneyMinor | Ratio`、`UnitValue = MinorUnits | Ratio`
为 union 别名（非 `Annotated`），故首次 `grep '= Annotated'` 未列出，二次实测已确认存在。

## 2. 为什么不 amend

ORCH §2 **H-12 git 纪律**明文：「**禁止** `--force`、禁止改历史」。commit `ffa9a30` 已 push 到
`origin/main`（`7ab1e9b..ffa9a30`），amend 必然伴随 force push，直接违反 H-12。
故不改写历史，以本 ADR 作为该 commit message 的权威勘误。

## 3. 裁决

1. `ffa9a30` 的 **代码产物与测试证据不受影响**：`dsm/models.py` 373 行、
   `tests/test_models_input.py` 1146 行 / 341 用例、全量 427 passed / 0 failed / 0 skipped，
   均已由 L3 `orch_verify.py` 判 ALL GREEN、L4 R4 三审 PASS。缺陷仅在 message 文字。
2. 本 ADR 为 S1-T02 的 Row 清单**唯一权威记录**；`ops/dag-state.json` 中 S1-T02 的
   `evidence.models_input_rows` 按实测值写入（非 message 值）。
3. 后续任何交付文档（README、V-4~V-20 证据表、待签认清单）引用 8 个 Row 时，
   一律以本 ADR 表格为准，不得复制 `ffa9a30` 的 message 串。

## 4. 流程整改（追加进 ORCH §7.1 坑清单）

**B-012（新坑）**：commit message 与 evidence 中的**一切类名 / 文件名 / 计数 / 行号**，
必须在写 message **之前**由脚本实测取得（`vars(module)`、`grep -n`、`wc -l`、
`pytest --collect-only`），**禁止**从交接摘要、上一会话记忆或任务标题推断。
交接摘要属"线索"不属"证据"；ORCH §8「实测优先」同样适用于 message 文字。
本条已同步登记 `ops/blockers.md` B-012，并在 §9 对账单「缺口与 blocker」段披露。