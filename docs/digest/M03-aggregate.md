# digest M03-aggregate -- 加权线性和 + 双轨聚合 + 权重重归一
# 消费方: WP-aggregate
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 462-477, 947-957
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 462-477 -->
  462| ### 2.3.2 M-B 加权线性和（aggregate.py）
  463| 
  464|     维度内得分:   dim_d   = Σ_{j ∈ d} w_j · x_j(绝对轨用 attainment_j，相对轨用 normalized_j)
  465|     综合分:       composite = Σ_d W_d · dim_d
  466|     约束:         Σ_d W_d = 1，每维度内 Σ_{j ∈ d} w_j = 1（1e-12 容差）
  467| 
  468| 支持三种算子（配置切换，默认 LINEAR）：
  469| 
  470| | 算子 | 公式 | 何时用 | 备注 |
  471| |---|---|---|---|
  472| | **LINEAR**（默认） | Σ W_d · dim_d | 常规 | 与原文一致；**唯一可做精确 Δ 分解**的算子（whatif 归因依赖它） |
  473| | GEOMETRIC | Π (dim_d)^(W_d)，dim_d ≤ 0 时按 eps 处理 | 需要「短板惩罚」时 | 无精确线性分解，whatif 改用对数差分近似并标注 APPROXIMATE_ATTRIBUTION |
  474| | NON_COMPENSATORY | min_d (dim_d) 或加权和取小 | 强非补偿场景 | v1.1 保留接口，**默认不启用**（红线已实现非补偿目的） |
  475| 
  476| **双轨**：同一套权重 W_d / w_j 分别作用于 attainment 矩阵与 normalized 矩阵，产出 composite_absolute 与 composite_relative 两个值，**分列披露**。
  477| 

<!-- SDD 947-957 -->
  947| ### 3.5.3 aggregate.py —— Step 5 双轨聚合（M-B）
  948| 
  949| | 项 | 内容 |
  950| |---|---|
  951| | 签名 | def compose(attainment: AttainmentFrame, normalized: NormalizedFrame, weights: WeightVersionDoc, config) -> ScoreFrame |
  952| | 输出 | ScoreFrame：composite_absolute、composite_relative、逐维度 dim_d（两轨各一套）、coverage、weight_version_id、operator |
  953| | 算子 | LINEAR（默认）/ GEOMETRIC / NON_COMPENSATORY（接口保留，默认不启用）；公式见 §2.3.2 |
  954| | 权重重归一 | 指标被剔除（未签认 / SUSPECT / INACTIVE）后，在**维度内**重归一并记 WEIGHT_REALLOCATED；维度被清空则 W_d 置 0 后在维度层重归一 |
  955| | 关键约束 | **INV-3**：本模块只读 FROZEN 权重，**不得**调用 diagnostics 或 weights_combine（T-CMB-06 用 mock 断言守护）；权重版本 id 必须写入每一行 score_card |
  956| | 复杂度 | O(策略数 × 指标数) |
  957| 
