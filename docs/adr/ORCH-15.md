# ORCH-15 evidence_source 属输出侧字段，不进 8 个输入 Row

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02（R4 复核质询点 A5）→ 归属 S1-T04 与 S5-T01 |
| 裁决人 | Orchestrator（主控） |
| 类型 | 契约归属裁决 |

## 事实

- SDD [L1895]：`evidence_class` 枚举保持 A/B/C/D；**新增** `evidence_source ∈ {CARD_ONLY, CEL_ESTIMATED}`；首版恒为 CARD_ONLY
- SDD [L870]：CEL-0 预留 = DesignCardRow 增 7 个可空字段；`evidence_source ∈ {CARD_ONLY, CEL_ESTIMATED}`；
  **ScoreCardRow** 增加增量三列 + value_captured 占位；AuditBundle 增加 cel_contract_version
- SDD [L980]：**EvidenceFrame** 字段 = evidence_class、evidence_reason、**evidence_source**（CARD_ONLY / CEL_ESTIMATED）、control_group_id、interpretation_limit
- SDD [L1162-1174]：DesignCardRow（T4）的字段清单里**没有** `evidence_source`
- R4 实测：`dsm/models.py` 全文 `evidence_source` / `CARD_ONLY` / `CEL_ESTIMATED` 命中数 = 0

## 裁决

`evidence_source` 是**判定结果**而非**输入事实**：它由 evidence.py 依据设计卡判定后产出（[L980] 把它列在 EvidenceFrame 字段里），
并在 [L870] 中与 ScoreCardRow 的增量三列并列提及。因此：

- **不属** S1-T02（8 个输入 Row）—— R4 判 ⚠ 正确，实现者未加是**对的**，不得为消 ⚠ 而硬加进 DesignCardRow
  （硬加会违反 A3「字段须与 [L1162-1174] 逐一对齐」，且 [L1902] 明示 models.py 是 frozen + extra=forbid，乱加字段属破坏性契约变更）
- **属** S1-T04：`ScoreCardRow` 输出模型须含 `evidence_source`（依据 [L870]）
- **属** S5-T01：`EvidenceFrame` 须含 `evidence_source`（依据 [L980]），取值 Literal `{CARD_ONLY, CEL_ESTIMATED}`，首版恒为 `CARD_ONLY`（[L1895]）
- S1-T04 / S5-T01 的验收清单须显式包含此项，R4 届时按本 ADR 判定

## 依据

SDD L870 / L980 / L1162-1174 / L1895 / L1902；ORCH §5.2 S1-T04、§5.6 S5-T01；§2 H-10。
