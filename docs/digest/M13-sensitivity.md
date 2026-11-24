# digest M13-sensitivity -- OAT / MC / LOO / NORM_SWAP / flip_rate / 稳定性标签
# 消费方: WP-sensitivity
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 742-752, 1010-1021
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 742-752 -->
  742| ## 2.7 稳健性分析（sensitivity.py，M-I）
  743| 
  744| | 方案 | 做法 | 输出 | 判据 |
  745| |---|---|---|---|
  746| | **OAT_10 / OAT_20** | 逐个维度权重 ±10% / ±20% 扰动后重归一，重跑 Step 5–6 | 每方案 flip_rate（等级翻转策略占比）、逐策略 stability 标签 | overall_flip_rate ≤ stable_max（默认 0.05）→ STABLE；≤ review_max（默认 0.15）→ BOUNDARY；> review_max → **FLIP_RATE_UNUSABLE，本期不得用于淘汰** |
  747| | **MC（Dirichlet）** | 从以冻结权重为均值的 Dirichlet 分布抽 S 组权重（**固定 seed**，seed 写入 audit_bundle；未设 seed 则拒绝运行 MC） | 等级分布、逐策略等级众数与置信区间 | 同上 |
  748| | **LOO（留一指标）** | 逐个指标剔除后重归一、重跑 | 每指标的 LOO 影响力排名（主导指标清单） | 单指标剔除导致 flip_rate 超阈 → DOMINANT_METRIC 警示，进字典工单 |
  749| | **归一化互换** | min-max ↔ z-score ↔ rank-percentile 互换，重跑相对轨 | 相对轨排名变化 | 秩相关低于阈值 → NORMALIZATION_SENSITIVE |
  750| 
  751| **性能优化（RK-6）**：Step 1–4 的结果在所有方案间**复用**，只重跑 Step 5–6；指标数 > 60 时 LOO 改为按维度抽样。
  752| 

<!-- SDD 1010-1021 -->
 1010| ### 3.7.1 sensitivity.py —— Step 8 敏感性与稳健性（M-I）
 1011| 
 1012| | 项 | 内容 |
 1013| |---|---|
 1014| | 签名 | def run(base: ScoringContext, schemes: list[SchemeName], config) -> SensitivityReport |
 1015| | 方案 | OAT_10 / OAT_20 / MC / LOO / NORM_SWAP（见 §2.7） |
 1016| | 复用 | Step 1–4 的结果在所有方案间**复用**，只重跑 Step 5–6（RK-6 性能对策） |
 1017| | MC 纪律 | numpy + **固定 seed**；seed 写入 audit_bundle；**未设 seed 则拒绝运行 MC 方案**（抛 SeedRequiredError） |
 1018| | 输出 | overall_flip_rate（逐方案）、每策略 stability 标签 ∈ {STABLE, BOUNDARY, UNSTABLE}、LOO 主导指标清单、NORM_SWAP 秩相关 |
 1019| | 首屏否决 | overall_flip_rate > review_max → FLIP_RATE_UNUSABLE，报告首屏声明「本期结果不得用于淘汰决策」，并写 grade_ledger.usable_for_elimination = false |
 1020| | 抽样降级 | 指标数 > loo_sampling_threshold（默认 60）时 LOO 改为按维度抽样，并在报告标注 LOO_SAMPLED |
 1021| 
