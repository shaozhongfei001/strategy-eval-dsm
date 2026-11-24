# RUN-ORCH-30 · 撤回 ORCH-29 第 3 条的错误部分 + 主流程真阻塞重定位 + R-15 批量注册排程

- **时刻**：T+5.1h（C2b `10df9f8` 交付后）
- **裁决人**：主控（Orchestrator）
- **触发**：C2b 按「原文优先于裁决」的指令核对 M22 原文后，**推翻了主控在 ORCH-29 第 3 条中的部分裁决，并推翻了 P2a 的缺陷归因**。两项推翻均有逐字引文与实测支撑，主控予以采纳并公开纠错。

## 第 1 条 · 撤回「C-08 表级缺失 → 整轮 BLOCK」

**M22 L907 逐字**：`| C-08 | 评价设计卡完备性 | PARTIAL（缺对照安排或成功判定）→ 证据上限压到 C；MISSING → 证据 D → NOT_ASSESSED | **降级** |`
M22 L900-L909 中标注 `**BLOCK**` 的只有 **C-01 / C-02（清空维度数≥2）/ C-03 / C-07 / C-09**，C-08 不在其中。旁证：**M28 L1292** `| 评价设计卡 MISSING | C-08 | 证据 D → NOT_ASSESSED | 否 | 台账单独计数 |`、**M23 L977** `设计卡缺失 → D（NOT_ASSESSED）`、**M29 L1346** `… + NOT_ASSESSED 单列`。

→ **ORCH-29 第 3 条中「整轮 BLOCK（保留）」一节撤回**（原文无依据，属主控过度规格化）。C2b 的实际交付（`dsm/preflight.py` **PROD=0** + 4 条新测试，C2 既有 20 条零弱化：169 insertions / 1 deletion 且唯一删除行是 import 合并）**予以核可**。

**表级故障的正确出口**（采 C2b 实测口径）：缺必需列 / 容器不可读 → 在 **io 层**以 `DataLoadError` **退出码 4** 硬失败（**M21 L892**），发生在 preflight 之前；`TABLE_ABSENT ∉ BLOCKING_KINDS`。

## 第 2 条 · severity 与 blocks_run 的关系（消解 ORCH-29 第 3 条的自相矛盾）

主控原裁决同时写了「WARN 级 finding」与「BLOCK 不得降为 WARN」，C2b 指出二者矛盾。**采纳 C2b 的读法并定为口径**：
- `reason_codes` 注册表里的 **severity 属签认属性，任何 lane 与主控都不得为通过测试而改写**（V-14）；
- **是否阻断本轮只由 `blocks_run` 决定**，与 severity 字面无关；
- 因此 `EVIDENCE_CARD_MISSING` 保持 severity=BLOCK 而 `blocks_run=False` **不构成矛盾**，也**不得**把策略级码塞进 `RUN_BLOCKING_CODES`（那会直接弱化 C2 既有 L328/L468/L486 三条断言）。

## 第 3 条 · 主流程真阻塞重定位：D-A1-04 是唯一 BLOCK 源

C2b 用冻结 fixtures 对 2026-Q1/Q2/Q3 三期真跑（`dsm_stage/C2b/diag_c08.py`），三期完全一致：**唯一 `blocks_run=True` 的是 C-01 `WEIGHT_MISSING_WHATIF_RUN_ID`**；C-08 的 `EVIDENCE_CARD_MISSING`(S-010) / `EVIDENCE_CARD_PARTIAL`(S-011) 均 `blocks_run=False`，S-010 早已在 `not_assessed` 中。

→ **P2a 的第 ② 条归因（「C-08 单主体卡缺失被判整轮 BLOCK」）判定为误报**，成因是把注册表 severity=BLOCK 读成「阻断整轮」。**主流程走不通的唯一原因是 D-A1-04**（fixtures 的 FROZEN 权重文档 `provenance=null`，缺 `whatif_run_id`）。
原文支撑：**M22 L900** `含 approved_by/approved_date/whatif_run_id → **BLOCK**，退出码 2`；**M28 L1281** `权重 FROZEN 但缺 whatif_run_id → 加载失败`。**实现照原文正确，数据违约**，故不得降为 WARN（V-14），必须修 fixtures。
→ **A1c 的优先级升为最高**，且 **D-A1-04 列为 A1c 的第一优先项**。C-04（S-005 v1 缺失率 14/14）同属 fixtures 数据缺陷（**M22 L903** `超 block 阈 → 该策略 NOT_ASSESSED（台账单独计数）| WARN / 策略级降级`，实现已是策略级），归 A1c。

## 第 4 条 · R-15 reason_code 批量注册（第 2 批）排程

已累积的注册需求（**由主控统一改 `dsm/reason_codes.py` + `tests/test_reason_codes.py`，lane 不得自行新增**）：
| 来源 | 建议码 | 用途 |
|---|---|---|
| C2b | `DESIGN_CARD_TABLE_ABSENT`（BLOCK） | 设计卡表整体缺失 → audit + 退出码 2；C2b 已核验该码不在 `STRATEGY_SCOPED` 内，落地不触碰既有断言 |
| C2b | 重复 `strategy_id × version` 卡索引码 | 现行实现静默取后一行，违 **M18 L1102**（T4 粒度＝策略 × 版本），属 V-14 静默降级，必须显式拒绝 |
| D4 | Spearman 零方差码 | 现 `rho`/`agreement` 置 None 无码 |
| A2 | H-2 / H-3 / H-5 与红线排除专用码 | 现复用泛码 |
| C5 | 一级库准入「等级 != L1」码 | 现单槽留 None |
| C2 | C-03 专用码 | 现沿用 `CONFIG_SEMANTIC_ERROR` |
| A4 | `APPROXIMATE_ATTRIBUTION` | 非 LINEAR 算子一律拒算所需 |

**时序约束**：必须等 **EFIX-1** 落地后再动 —— E5 的 `test_architecture.py` 含「碰撞留在已审清单内」的 **ratchet（32 对）**，新增码会改变碰撞计数，而 EFIX-1 此刻正在改该文件。派工时须先做**已注册码清单盘点**（读 `dsm/reason_codes.py` + `dsm_stage/E5/GAPS-E5.md` + `dsm_stage/A4/gaps.md` + `dsm_stage/C2b/NOTES-C2b.md`），**只补缺失者，不得重复注册、不得改名既有码**（名称一律用注册名，ADJ-3）。

## 第 5 条 · 复现哈希将失效（必须提前声明，避免后续误判为造假）

A1c 一旦执行受控解冻，`fixtures/` 内容变更 → **P2a 记录的 `reproducibility_hash = 8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8`（评价期 2026-Q2）必然改变**。这是**预期结果，不是回归**。
- 该哈希作为「A1c 之前」的证据**保留入册**，标注 `superseded_by_A1c`；
- **P3b 第二人复跑必须以 A1c 之后重新测得的哈希为准**，且须在**全新 clone + 断网单机 + 同 seed** 下与 P2 收口时的哈希**精确相等**；
- P3a 验收证据表须同时列出「解冻前哈希 / 解冻后哈希 / 变更原因 / 前后 fixtures sha256 清单」，不得只报其一。
