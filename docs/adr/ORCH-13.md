# ORCH-13 ScoringContext 与两个 Frame 的字段清单在 SDD 缺定义：按最小可推导闭包实现

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1-T04 |
| 裁决人 | Orchestrator（主控） |
| 类型 | 契约缺口裁决（§10.2-4 预留并登记，不阻塞） |

## 事实

R1 实测：SDD 全文 `ScoringContext` **仅 1 处命中**，在 [L1014]，且**只作为签名类型名**出现，
无任何字段清单：

    [L1014] | 签名 | def run(base: ScoringContext, schemes: list[SchemeName], config) -> SensitivityReport |

配套原文 [L1016]：「复用 | Step 1-4 的结果在所有方案间**复用**，只重跑 Step 5-6（RK-6 性能对策）」。
另 `NormalizedFrame`（[L939-945]）与 `RedlineFrame`（[L988-994]）SDD 只给签名 + 语义 + reason_code，
**未列逐字段表**（对比：AttainmentFrame [L928]、ScoreFrame [L952]、GradeFrame [L964]、
EvidenceFrame [L980]、PoolFrame/PoolStats [L1006] 均有明确字段行）。

## 裁决 1：ScoringContext 字段 = 运行上下文 + Step 1-4 结果闭包

依据 [L1014] 的形参名 `base` 与 [L1016]「复用 Step 1-4 的结果」，其字段闭包**可从原文推导**，
不属发明。限定为以下两组，每个字段都必须能指回一行 SDD 原文：

**A. 运行上下文（H-8 纯函数要求：period 与 run_at 由参数注入，禁读系统时钟）**

| 字段 | 类型 | SDD 依据 |
|---|---|---|
| `period` | str | [L1089] CLI 公共参数 `--period` |
| `run_at` | str(ISO) | [L1089] `--run-at`（显式注入运行时间，程序内部不读系统时钟）；[L1271] 禁止计算层调系统时钟 |
| `seed` | int 或 None | [L1089] `--seed`；[L1017]/[L1270] 未设 seed 拒绝运行 MC |
| `weight_version_id` | str | [L1190]；[L955] 权重版本 id 必须写入每一行 score_card |
| `evidence_mode` | Literal | [L978] 默认 GATE_ONLY |
| `cel_enabled` | bool | [L1898] `eval_config.cel.enabled`，默认 false |
| `input_fingerprints` | InputFingerprints | [L891] 写入 audit.json，第二人复跑比对基准（V-3） |

**B. Step 1-4 中间结果（供 [L1016] 的跨方案复用）**
`attainment` / `normalized` / `evidence` / `redline` / `score` / `grade` / `pool` / `pool_stats`
——类型即 SDD [L868] 已定义的 8 个中间模型，一一对应，**不新增任何语义**。

**禁止**：在 ScoringContext 里放任何业务数值（H-5）、放当前时间（H-8）、放 SDD 未提及的字段。

## 裁决 2：NormalizedFrame / RedlineFrame 取「语义所需最小字段集」

以 SDD 已给的签名与语义行为骨架，字段仅取实现该语义**必需**者，且每个字段必须标注推导依据行号：

- `NormalizedFrame`（依据 [L939-945]）：定位键 `strategy_id` / `version_id` / `period` / `metric_id`（[L1149] 四元定位键）、
  `pool_key`（[L942] 池内归一 biz_domain × evidence_class）、`norm_value`（Decimal，[L940] 三种方法之一）、
  `method`（Literal `min_max`/`z_score`/`rank_percentile`，[L940]）、
  `anchor_used`（bool，[L941] 锚定集优先/回退）、`reason_code`（[L944] 四码）。
- `RedlineFrame`（依据 [L988-994]）：`metric_id`（[L988]）、`level`（Literal HARD/SOFT，[L989-990]）、
  `comparator` / `threshold_value`（[L1181]）、`hit`（bool）、`forced_grade`（[L989]，原文默认 L4）、
  `waiver_approval_id` / `waiver_valid_from` / `waiver_valid_to` / `waiver_scope`（[L991]）、
  `soft_deduction`（[L990] 独立扣减、不进加权）、`reason_code`（[L993] 四码）。

## 裁决 3：复核方式（H-11 无人值守下的签认替代）

因这两处无 SDD 逐字段原文，golden 期望值不得「首次跑通即固化」了事。
R4 必须**逐字段**核对：该字段是否可指回上表列出的某一行 SDD 原文；
指不回的字段一律判 ❌ 要求删除。判定依据写入本 ADR 的追加节，视为签认（H-11）。

## 依据

SDD L868 / L891 / L939-945 / L955 / L978 / L988-994 / L1014 / L1016 / L1017 / L1089 /
L1149 / L1181 / L1190 / L1270 / L1271 / L1898；ORCH §2 H-5/H-8/H-11、§10.2-4。
登记：`ops/blockers.md` B-004（ScoringContext）、B-005（两个 Frame）。
