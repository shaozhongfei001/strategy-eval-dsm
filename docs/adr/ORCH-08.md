# ORCH-08 ORCH §5.2 给 S1-T01 的行区间漏配 §3.3.4 config.py

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T01、S1-T05、S1-T06 |
| 裁决人 | Orchestrator（主控） |
| 类型 | 规程缺陷登记 + 区间补配 |

## 事实

ORCH §5.2 给 S1-T01 的区间写作「§3.3.3(860-873)」。实测 SDD 标题地图：
`838:## 3.3 L1 契约层逐模块`，而 §3.3.4 config.py 起于 **L874**，止于 L893
（`894:## 3.4 L2 校验层`）。即授权区间在 §3.3.3 末尾**恰好截断**，
把 config.py 的模块规格整段排除在外。

## 后果（实测 grep 定位）

S1-T05 / S1-T06 的核心验收项原文全部落在被漏掉的 L874-893：
`TODO` / `TBD` / `XXX` 各 1 命中且**同在 L878**；`ConfigPlaceholderError` 命中 L310/878/881/1259；
`attainment_floor` 的语义校验命中 L879；`单调` 命中 L879。

## 裁决

补取 **L874-893（§3.3.4 config.py）** 进 S1-T01 的取证范围，落 `docs/digest/S1-T01c.md`。
适用 ORCH 卷首规则「与 SDD 冲突时一律以 SDD 为准」：SDD 的章节边界是事实，ORCH 的区间是笔误。

## 连带修正（同源笔误，一并登记 → 见 ORCH-08b）

ORCH §5.2 S1-T04 写「8 个中间 Frame + PoolStats + ScoringContext」，而 SDD L868 逐字为
「中间模型（8）：AttainmentFrame、NormalizedFrame、EvidenceFrame、RedlineFrame、ScoreFrame、
GradeFrame、PoolFrame、PoolStats」——即 **7 个 Frame + PoolStats 合计 8 个中间模型**，
ScoringContext 不在其中（实测全文仅 1 命中，在 L1014，属 §3.7 L5 稳健层）。
裁决：以 SDD 为准，实现 **7 个 Frame + PoolStats（= 8 个中间模型）+ ScoringContext（独立运行上下文模型）**。

## 依据

SDD L838 / L873 / L894 标题行；L878 / L879 / L881 grep 命中；L868 逐字原文；L1014 grep 命中。
ORCH 卷首「与 SDD 冲突时一律以 SDD 为准」；§10.2-2。

## 影响

仅取证区间与模型计数口径的澄清，不改任何设计语义。
