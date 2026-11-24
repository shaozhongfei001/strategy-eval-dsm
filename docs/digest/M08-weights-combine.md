# digest M08-weights-combine -- 档 2 组合权重算法（8 步 + 四约束 + 回退不稀释）
# 消费方: WP-weights_combine
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 556-603
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 556-603 -->
  556| ### 2.4.3 档 2 组合权重算法（weights_combine.py）
  557| 
  558|     def combine(ahp: AhpResult, entropy: EntropySnapshot, opts: CombineOptions) -> CombinedWeights
  559|     def build_draft(ahp_matrices, facts_history, metric_dict, opts) -> WeightVersionDoc   # status = DRAFT
  560| 
  561|     class CombineOptions:
  562|         alpha: Decimal                     # 业务判断权重占比，∈ [alpha_floor, 1]
  563|         alpha_floor: Decimal = 0.5         # K-15，治理参数
  564|         min_dim_weight: Decimal            # K-19，任一维度组合后权重下限（防被熵权清零）
  565|         min_metric_weight: Decimal | None  # 指标层权重下限（可选）
  566|         entropy_min_strategies: int = 10   # 单期参评策略数下限，低于此不做组合
  567|         inactive_threshold: Decimal = 1e-4
  568|         max_shift_from_ahp: Decimal = 0.30 # K-20，H-5 用
  569| 
  570| **六步流程**：
  571| 
  572|     Step 1  AHP 权重：调用 weights_ahp.elicit + check_consistency
  573|             CR ≥ 0.1 → **直接抛错终止**，不进入组合（AHP 是前提，不是可选项）
  574|     Step 2  标定窗口熵权：对窗口内每一期 t
  575|             - 若该期参评策略数 n_t < entropy_min_strategies → 剔除该期，记 ENTROPY_PERIOD_SKIPPED
  576|             - 否则按 §2.4.2 六步算出 w_j(entropy, t)
  577|             - 全部期都被剔除 → **回退纯 AHP**（等价 α = 1），记 ENTROPY_INSUFFICIENT_SAMPLE，
  578|               并在草稿首屏显著标注
  579|             - w_j(entropy) = median_t ( w_j(entropy, t) )
  580|               drift_j = max_t w_j(entropy, t) − min_t w_j(entropy, t)
  581|     Step 3  INACTIVE 回退规则（**本方案最关键的一条**）
  582|             若指标 j 在标定窗口内零变异或 d_j < inactive_threshold：
  583|                 w_j(combined) = w_j(AHP)        # 直接沿用 AHP 权重，不做组合
  584|                 记 flag ENTROPY_INACTIVE_FALLBACK
  585|             理由：零变异指标的熵权必然趋 0，参与组合会把它权重稀释到 α 倍。
  586|                   以「投诉率常年 0.01%」为例，α = 0.5 时其权重被腰斩。
  587|                   回退规则确保「数据不动 ≠ 不重要」。该指标仍会出现在在线诊断里被建议退役或红线化。
  588|     Step 4  组合与归一（对非回退指标）
  589|             w_j(raw) = α · w_j(AHP) + (1 − α) · w_j(entropy)
  590|             维度内重新归一: w_j = w_j(raw) / Σ_{j ∈ d} w_j(raw)
  591|             维度层同样处理: W_d(raw) = α · W_d(AHP) + (1 − α) · W_d(entropy)
  592|                           （维度层熵权 = 该维度内指标熵权之和），再归一到 Σ W_d = 1
  593|     Step 5  硬约束校验（任一不满足 → 该 α 判为不可行，交给 §2.4.4 处理）
  594|             H-1  Σ W_d = 1 且每维度内 Σ w_j = 1（1e-12 容差）
  595|             H-2  每个维度 W_d ≥ min_dim_weight（防某维度被熵权整体压没）
  596|             H-3  任一指标 w_j ≥ min_metric_weight（若配置了）
  597|             H-4  CR < 0.1（AHP 前提）
  598|             H-5  组合后权重与纯 AHP 权重的 L1 距离 ≤ max_shift_from_ahp（默认 0.30）
  599|                  → 防止熵权把专家判断整体推翻，保证「业务判断主导」
  600|     Step 6  产出 WeightVersionDoc：status = **DRAFT**（工具无权写 FROZEN），provenance 见 §3.11.4
  601| 
  602| **复杂度**：O(N × 策略数 × 指标数)，N 为窗口期数；一次性离线运行，无性能压力。
  603| 
