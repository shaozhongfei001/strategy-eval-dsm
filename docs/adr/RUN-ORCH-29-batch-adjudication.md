# RUN-ORCH-29 · A3/A4/P2a 交付后的批量裁决（架构注入 · 测试侧修正 · C-08 语义 · 池键顺序 · fixtures 受控解冻 · 预算超支）

- **时刻**：T+4.9h（A3 `2de42db`、A4 `b2119e3`+`9078201`、P2a `8cd222c` 交付后；**31 个计划包全部交付**）
- **裁决人**：主控（Orchestrator）

## 第 1 条 · L0 层内部 import 边（D-A2-01 / D-A3-01）→ 包 ARCH-1

原文（`docs/digest/M00-architecture.md`）：L276 `L0a 离线无依赖工具（不依赖任何内部层）`；L278 `weights_combine.py 组合权重（消费 L0a 与熵权快照）`；L286 `L0a → 无内部依赖（独立命令行工具）`；L294 `L0b → L1-L5（单向调用；反向禁止）`；L300 `INV-1：L0b 可 import L1–L5；L1–L5 不得 import L0a / L0b`；L282 `…拆分后依赖仍严格单向`。

1. **L278「消费 L0a」= 消费产物（数据/快照），非 import 模块**——唯一能使 L278 与 L276/L286 同时成立的读法（延续 ORCH-27）。
2. **L0a → L1 例外维持**（ORCH-03 + SDD §2.4.2 L537「熵权六步两个计算者共用同一实现」+ numeric 唯一数值口径）；L286 读作「无 L0 / L2+ 依赖」。
3. **L0b 只能 import L1–L5**（L294 逐字）；A3 请求的「L0b→L0a 豁免」**驳回**。`weights_calibrate` 需要组合权重能力 → **注入 callable**（keyword-only 必填 `combine_fn`），与 L282「L0b 需跑完整 Step1–7 流水线」一致（流水线各步均在 L1–L5）。
4. `weights_combine` 改为消费 **AHP 快照数据**，不 import `weights_ahp`。
5. **禁隐藏导入**：`TYPE_CHECKING` / `try-ImportError` / `importlib` 动态导入 / 鸭子类型绕过，一律视为未修复（E5 是 AST 扫描；A3 已用鸭子类型去掉 `weights_ahp` import，该手法**不予认可**为最终态，ARCH-1 须改为真注入）。
6. 签名 delta 允许（新增 keyword-only 必填入参），须逐条上报供 **P2** 对齐 `dsm/cli.py` 调用点（cli 不在 ARCH-1 写集）。

## 第 2 条 · 验证 lane 的两处测试侧修正 → 包 EFIX-1

- **E4b**：`tests/test_properties_all.py::test_p13b` 以 `inputs=None` 调用且只捕获 `TypeError`，而 V-14 要求对 `None` 抛**显式业务异常**——**测试构造错误，非实现缺陷**（A3 上报成立）。修法：按 `2de42db` 的真实公开签名与真实入参容器重写调用，**P-13 属性断言强度不得减弱**（写跨模块全局版，docstring 指名模块内局部版）。
- **E5b**：`ALLOWED['L0a']` 由 `('L0a','L1')` **收紧**为 `('L1',)`；`ALLOWED['L0b']` **维持 L1–L5 不放宽**（驳回 E5 的 `+'L0a','L6'` 建议）。收紧属允许动作。修完后 `weights_combine→weights_ahp`、`weights_calibrate→weights_combine` 两条边保持 **预期 RED**，由 ARCH-1 消除；**禁为变绿而放宽**。
- A4 已按 ORCH-27 自修 D-A4-01/D-A4-02（`whatif.py` 哈希改 callable 注入、零 L6 依赖、`run()` 新增 `input_dir`/`directory_hash`、`WhatifReport` 新增 `readonly_proof`，commit `9078201`）→ **两缺陷关闭**，EFIX-1 须实测复核该边确已消失。

## 第 3 条 · preflight C-08 语义（D-C2-01）→ 包 C2b

**现象**（P2a 实测）：冻结 fixtures 任何一期都 BLOCK，主流程永久走 L1322-1326 的 `写 audit_bundle / 退出码 2 / 不产 score_card` 分支。其中 C-08 把**单个主体**的 `design_card` 缺失判为**整轮 BLOCK**，与 **M29 L1346 逐字**冲突：`Step 7 pooling → 分池禁混排 + 一级库门禁 + 占比双报 + NOT_ASSESSED 单列`。

**裁决**：C-08 两分法——
- **整轮 BLOCK（保留）**：表整体缺失 / 文件不可读 / 该期**全部**主体无卡 / 表结构或必需列缺失，即「本轮评价无法成立」。
- **单主体缺失（不 BLOCK）**：该主体 Step3 落 **NOT_ASSESSED**（已注册码 + WARN finding + 报告披露），Step7 按 L1346 **单列**，**不计入**占比双报分母（沿用 C5 冻结口径），不影响其它主体。
- 这不是 V-14 静默降级（显式码 + WARN + 披露）；BLOCK 仍不得降为 WARN。
- **原文优先**：若 M22 的 C-08 逐字要求「单主体缺卡即整轮 BLOCK」，C2b 不得改代码，须上报 BLOCKING 附双方引文，升级 SDD 勘误。
- P2a 另报的 **C-01（FROZEN 权重 `provenance=null` 缺 `whatif_run_id`）** 与 **C-04（S-005 v1 缺失率 14/14）** 判定为 **fixtures 数据缺陷（归 A1c）**，非 preflight 实现缺陷；C2b 只核原文并给归属建议。

## 第 4 条 · 池键顺序矛盾（D-MODELS-01）→ 包 MODELS-1（**等 SEAM-1 落地后派**）

**矛盾**：**M29 L1334** `Step 2 normalize → 池内标准化 + 锚定集参照` 排在 **L1338** `Step 3 evidence → A/B/C/D` **之前**；而 **M43 L942** 要求 normalize `标准化在**池内**进行（biz_domain × evidence_class）`，`evidence_class` 却由 Step3 才产生。现行 `models.PoolKey.evidence_class` 为 required，致 Step2 无法先于 Step3 构键（P2a 实测）。

**裁决**：`PoolKey.evidence_class` 改为**可选（None 允许）**；Step2 在 evidence_class 未知时按 **biz_domain** 分区做标准化（且按 M43 L941 统计量**优先取自 anchor_set**，故分区口径对结果的影响主要在锚定集失效的回退路径）；**Step7 pooling 必须使用完整 (biz_domain × evidence_class) 键**，禁混排（P-6/G-02 不松动）。
- 这是对**冻结契约** `dsm/models.py` 的一次 **R-15 变更**，主控在此**明确授权**（写集含 `dsm/models.py`），并要求：① 变更前后 `PoolKey` 的序列化形态与既有 19 条 pooling 测试全部保持绿；② 在 **P3a** 验收证据表披露「M29 L1334 与 M43 L942 存在顺序矛盾，本 run 采 Step2 松键 + Step7 严键的读法」。
- **时序**：必须等 **SEAM-1** 落地（同写 `normalize.py`/`pooling.py`），避免写集冲突。

## 第 5 条 · fixtures 受控解冻（D-A1-02 / D-A1-03 / D-A1-04 / D-A1-05）→ 包 A1c（**等在飞 lane 落地后派**）

两个独立 lane（E2 golden、P2a 集成）**互相印证**同一批 fixtures 缺陷，故认定非误报：

| 缺陷 | 事实 | 原文判据 |
|---|---|---|
| D-A1-02 | `design_card.jsonl` 中 DID+CONCURRENT_CONTROL 卡缺 `alt_method_note` / `interpretation_limit` → 实测证据分布 **A3 B0 C4 D5/D6**，与声明 **A3B3C4D2** 不符 | **M34 L1459** `证据分布：A×3、B×3、C×4、D×2（确保四类路径都被走到）` |
| D-A1-03 | 主评价期 `2026-Q3` 事实表缺 4 格，含 `S-008/v1/M_COMPLAINT_RATE`（HARD 红线指标）→ `redline.evaluate` 按 V-14 抛错，Step4-9 整链断 | **M34 L1460** `刻意构造：1 个高贡献 + 红线违反（G-03）…`（构造必须可达） |
| D-A1-04 | FROZEN 权重文档 `provenance=null`，缺 `whatif_run_id` → C-01 恒 BLOCK | **M29 L1322** 主流程应能走 `status=PASS/WARN` 分支 |
| D-A1-05 | `design_card` 为 JSONL，而 `io_loaders` 只认 CSV/Parquet 且 `''`→None，T4 永远加载不出（`DataLoadError MODEL_ROW_REJECTED`） | **M29 L1330** `io_loaders → 8 表 + InputFingerprints（SHA256 / 行数）` |

**裁决**：fixtures 虽于 SP-1 冻结（`ca31dd1`），但**冻结件与自身 manifest / 与 M34 原文矛盾属缺陷，不属签认值**，故授权**受控解冻**，立 **A1c**：
1. 补 `design_card` 两字段使分布恰为 **A3B3C4D2**；补 `2026-Q3` 缺失事实格（含 HARD 红线指标）使 G-03 构造可达；FROZEN 权重补合成 `provenance.whatif_run_id`（**合成值必须显式标注为 fixtures 常量，不得冒充签认值、不得填 K-01~K-20**）。
2. **格式归属二选一，不得两边都改**：以 `docs/digest/M21-io-loaders.md` + `M18-contract-inputs.md`（T4 行）原文规定的格式为准——若原文未规定 JSONL，则 **A1c 改 fixtures 格式**；若原文规定八表含 JSONL，则立 **C1c 改 `io_loaders`**。判定必须附逐字引文。
3. 重生成 → **逐文件 sha256 前后对账**（沿用 A1b 已验证的做法：先用 HEAD 原码生成 baseline 证明管线有效）→ 重新冻结 → **重算受影响 golden 手算值**（写入 golden_map，附算式）。
4. 随后 **E2b / E3b 严格串行**：仅按 A1c 的**数据变化**更新 `test_golden_a.py` / `test_golden_b.py` 的 expects，**必须附重新手算过程**，禁照抄实现输出（R-14）。
5. **时序**：必须等 **B1b / SEAM-1 / E3** 落地后再动 fixtures（三者正在用当前 fixtures 跑验证，中途换数据会污染归因，B-011 同类风险）。
6. 全过程在 **P3a** 披露「受控解冻一次 + 原因 + 前后 sha256 清单」，在 **P3c** 的已知缺口清单中列明。

## 第 6 条 · 预算超支核可（ADJ-11）与教训 L-04

| 包 | 预算 min | 实测 min | 原因 |
|---|---|---|---|
| A3 | 90 | **161** | 飞行中途收到 ORCH-27 裁决需返工 + 并行落地触发 4 次全量回归 |
| A4 | 75 | **110** | 同上（ORCH-27 的 D-A4-01/02 中途修复） |
| P2a | 75 | **145** | 集成包需等 6 个模块落地后反复重跑；九步贯通 + 两次连跑哈希对账 |
| F4/D4/C2/A2 | — | 小幅超 | 已在 ADJ-9 核可 |

**核可，不返工**（返工需重占槽位，与 10h 硬停线冲突；且三者交付质量高：A3 24 测试全绿含字典序非加权手算对拍，A4 归因残差 ≤1e-12 且交叉项独立成列，P2a 九步真贯通 + `reproducibility_hash` 两次连跑精确相等）。

**L-04（新教训）**：① ORCH 裁决在 lane **飞行中途**下达并改变其写集语义时，该包墙钟预算**必须重设**，不得按原预算判超时；② 并行期**全量回归成本随包数线性上升**，lane 侧应改为「本包测试 + 受影响邻包测试」，**全量只在同步点由主控跑一次**；③ 集成类包（P2a/P2）的预算应按「等待上游落地」的重跑次数上浮，不能按单模块包估。

## 第 7 条 · 已取得的正向证据（供 P3a / P3b 直接引用）

- **V-3 / G-12 可复现性**：同 fixtures + 同 seed 连跑两次，`reproducibility_hash` **精确相等** = `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8`（评价期 `2026-Q2`，九步中间产物逐项相等、输入指纹逐字节相等）。断言名 `tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs`。
- **M29 九步全贯通**、**E1 的 SKIP_REGISTRY 已全清（实测 SKIP=0）**。
- **A4 归因精确性**：S4/D1 段1=0.018、段2=−0.180、交叉=−0.006、Σ=−0.058=0.702−0.760，`max_residual ≤ 1e-12`；交叉项独立成列证据 `Σ段1+Σ段2=−0.126 ≠ −0.114`，差值恰为 Σ交叉。
- **A3 字典序非加权**：α=0.50 的 drift 最小但 boundary 越界 → 仍选 0.75；报告无聚合分数列、全文件无 lambda。
