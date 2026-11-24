# RUN-ORCH-28 · normalize × pooling 接缝缺陷终审（D-SEAM-01）

- **时刻**：T+4.5h（E2 `d3b3d5f` 与 A1b `0547190` 交付后）
- **裁决人**：主控（Orchestrator）
- **现象**：E2 的 G-01/G-02/G-04 三条 golden **Step1–6 逐位全绿**，卡在 Step7 —— `pooling.build` 抛 `PoolingInputError: 已参评但 composite_relative 为 null，池内不可比：S-003|v1|2026-Q3`；G-04 的 `(WEALTH,B)` 为单例池 → `dim_relative={}`。同根因使 `tests/test_integration_spine.py` 的 M29 Step7 中断。E2 判定「两模块各自都符合自己的 digest，冲突在接缝上」，请求主控裁决归属。

## 一、原文逐字（`docs/digest/M43-normalize.md`）

| 行 | 原文 |
|---|---|
| L939 | `签名 \| def compute(facts, metric_dict, anchor_set: AnchorSetDoc, config) -> NormalizedFrame` |
| **L941** | `锚定集 \| min_max 的 min/max 与 z_score 的 mean/sd **优先取自 anchor_set**；锚定集失效 → 回退当期池内统计 + 标注 RANK_REVERSAL_RISK` |
| L942 | `分池归一 \| 标准化在**池内**进行（biz_domain × evidence_class），禁止跨池归一（由 P-6 与 G-02 禁混排用例共同守护）` |
| **L943** | `边界 \| 零变异指标（sd = 0）→ INACTIVE，剔除并预警；池内样本数 < min_pool_size → WARN + 标注 SMALL_POOL` |
| L944 | `reason_code \| INACTIVE_METRIC、RANK_REVERSAL_RISK、SMALL_POOL、ANCHOR_SET_STALE` |
| L945 | `关键约束 \| 输出**只用于排名与相对轨综合分**，不得进入等级门槛判定` |
| L237-L239 | `固定 anchor_set（锚定基准策略集），标准化时以锚定集为参考尺` / `anchor_set.yaml **必须写 rationale**` / `锚定集失效（C-10 检出）→ 回退为仅当期归一化，并在**报告首屏显著标注秩反转风险**` |

## 二、裁决

1. **L943 是两条互相独立的边界，不得混用。** `sd = 0` 判 INACTIVE 的对象是**实际用于标准化的那一组统计量**；按 **L941**，anchor_set 有效时统计量**优先取自锚定集**，因此**单例池本身不产生 sd = 0**，仍应算出 `composite_relative`。只有「锚定集失效 → 回退当期池内统计」时，单例池才 sd=0 → 该指标 INACTIVE、剔除并预警。
   → **D3（normalize）把 sd=0 判据作用在当期池内统计上，属误读 L941/L943，为缺陷方。**
2. **`池内样本数 < min_pool_size` 的处置是 `WARN + 标注 SMALL_POOL`**（L943 后半），**不是**抛错、不是置 null、不是剔除该策略。
3. **pooling 侧**：仅当某行 `composite_relative` 为 null **且 normalize 未给出 SMALL_POOL / INACTIVE_METRIC / RANK_REVERSAL_RISK 任一标注**时，才属真契约违规、才允许抛 `PoolingInputError`。已显式标注者，pooling 必须按 **M24 L1006** 输出契约用 `reject_reason` 承载该码、令 `pool_rank = null`、**不得中断 M29 Step7**；该策略仍计入占比双报分母（沿用 C5 已冻结口径），且**当然不予一级库准入**（举证制：无法证明可比即不准入）。
   → **C5（pooling）对「有标注的 null」一律抛错，严于原文，为缺陷方之二。**
4. **不构成 V-14 静默降级**：WARN + 已注册 reason_code + 报告披露 = **显式降级留痕**。V-14 禁的是「静默」，不是「显式标注后的降级」。
5. **P-6 / G-02 不得松动**：SMALL_POOL 的池仍禁止跨池归一与合并排名；C 类仍禁入一级库。
6. **归属**：立单包 **SEAM-1**，写集 `dsm/normalize.py` + `dsm/pooling.py` + 两份对应测试。跨模块缺陷由主控裁决归属（§3.2 P2 条款），因两半必须就 SMALL_POOL 载体达成一致，拆两包会产生新的接缝风险。
7. **禁反填**：SEAM-1 不得修改 `tests/test_golden_a.py`（E2 的手算期望值是判据）与 `fixtures/**`（已冻结）。修完仍不绿则保持 RED 上报，由主控再裁。

## 三、同批认定的第二项缺陷（暂缓执行，等 P2a 落地）

**D-A1-02（fixtures 自相矛盾，E2 上报）**：`fixtures/input/design_card.jsonl` 中 S-004 / S-005v1 / S-005v2 / S-007 四条 `DID + CONCURRENT_CONTROL` 卡的 `alt_method_note` 与 `interpretation_limit` 全为 null，按 SDD L977 实测证据分布为 **A3 B0 C4 D6**，与 manifest 声明的 **A3B3C4D2** 不符，致 G-04/G-08 的 subject 落 NOT_ASSESSED。

**处置**：fixtures 虽已于 SP-1 冻结（`ca31dd1`），但**冻结件与自身 manifest 矛盾属缺陷，不属「签认值」**，故授权**受控解冻**：立 **A1c**（补两字段使声明分布成立 → 重生成 → 逐文件 sha256 对账 → 重新冻结 → 重算受影响 golden 手算值）+ **E2b**（仅按 A1c 的数据变化更新 `test_golden_a.py` 的 expects，且必须附**重新手算过程**，不得照抄实现输出）。
**时序约束**：**必须等 P2a 落地后再动 fixtures**——P2a 正在用当前 fixtures 跑九步贯通，中途换数据会污染其归因（B-011 同类风险）。A1c → E2b 严格串行，二者完成前 P2 的 0 failed 门禁不判定。全过程须在 **P3a** 验收证据表如实披露「曾受控解冻一次 + 原因 + 前后 sha256」。
