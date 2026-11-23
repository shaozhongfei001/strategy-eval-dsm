# ORCH-12 metric_dict.csv（K-14）的 PLACEHOLDER 拦截归属：config.py 出扫描器，preflight 复用

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1-T05（出扫描器）→ S3-T01/T02（复用并汇总） |
| 裁决人 | Orchestrator（主控） |
| 类型 | 口径裁决（保守超集，§10.2-2 + §10.2-4） |

## 事实（逐字，见 docs/digest/S1-T01c.md / S1-T01e.md）

- SDD [L877] config.py 加载清单 = `eval_config.yaml / weights_*.yaml / redlines.yaml /
  grade_rules.yaml / anchor_set.yaml / ahp_matrices.yaml` —— **不含 `metric_dict.csv`**
- SDD [L878] PLACEHOLDER 拦截：**递归遍历配置树**，凡值为字符串 `PLACEHOLDER`、
  `null`（且字段声明为必填）、或形如 `TODO` / `TBD` / `XXX` 的，
  **收集全部未填字段路径后一次性抛 `ConfigPlaceholderError`（不允许只报第一个）**
- SDD [L888] io_loaders 按 period 读 `data/<period>/` 的 T1/T3/T4，读 `config/` 的 **T2**/T5-T8
- SDD [L1751] K-14 = 维度指标细项与口径，位置 = `metric_dict csv`
- SDD [L1141] `signoff_status` 为 PENDING 或 REJECTED 的指标不参与评分
- ORCH H-5：config.py 必须**递归拦截并一次性列出全部未填路径**

## 冲突

`metric_dict.csv` 里含 `target_value` 等业务数值（[L1139]），按 H-5 必须是 PLACEHOLDER 并被拦截；
但按 [L877] 它不在 config.py 的加载清单内，而由 io_loaders 读取（[L888]）。
SDD 未明说其 PLACEHOLDER 拦截归属。

## 裁决（三段，职责不混淆且覆盖不缩水）

1. **S1-T05**：config.py 的递归扫描实现为**可复用的纯函数**（形如
   `scan_placeholders(tree, path_prefix='') -> list[str]`，返回全部未填路径），
   S1 阶段只对 [L877] 的 6 个 YAML 配置树生效；`ConfigPlaceholderError` 一次列出全部路径，退出码 3（[L881][L1080]）。
2. **S3-T01**：io_loaders 读 `metric_dict.csv` 时按 [L889] 做类型强制，
   并对每行复用同一个 `scan_placeholders`（把行映射为 `{列名: 值}` 的树）；
   命中即在 `InputFingerprints` 之外另记未填路径清单，**不得静默丢弃**。
3. **S3-T02**：preflight 把「6 个 YAML 的未填路径」与「metric_dict 各行的未填路径」
   **合并成一份一次性清单**统一抛出，以满足 H-5 与 [L878]「不允许只报第一个」的整体意图；
   未签认指标另走 `METRIC_NOT_SIGNED`（[L1141]），缺目标值走 `NO_TARGET_VALUE` 且 attainment = null。

## 为什么不是「config.py 直接加载 metric_dict.csv」

那会与 [L877] 的加载清单直接矛盾（ORCH 卷首：与 SDD 冲突一律以 SDD 为准），
并让 config.py 承担 io_loaders 的职责，破坏 §3.3.4 / §3.3.5 的模块边界与 H-9 分层。

## 依据

SDD L877 / L878 / L881 / L888 / L889 / L1080 / L1139 / L1141 / L1751；ORCH §2 H-5、H-9；§10.2-2、§10.2-4。
登记：`ops/blockers.md` B-003。
