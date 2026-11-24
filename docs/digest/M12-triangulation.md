# digest M12-triangulation -- TOPSIS / GRA / 三个 Spearman / 否决权 / 可关
# 消费方: WP-triangulation
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 698-741, 1022-1032
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 698-741 -->
  698| ## 2.6 旁路验证（第四层作用位）：TOPSIS / GRA / Spearman 三角与「否决权」
  699| 
  700| ### 2.6.1 为什么 TOPSIS 与 GRA 只做三角验证
  701| 
  702| 两者都是**可补偿的排序类方法**（TOPSIS 用欧氏距离、GRA 用关联度，都允许长短板互相抵消）。若用于分级就会重新引入 F4；且它们输出的都是**相对名次**，会重新引入 F3。但它们作为**独立视角**极有价值：
  703| 
  704| - 若主排序（达成率加权）与 TOPSIS 排序、GRA 排序的 Spearman 秩相关**很高** → 结论对方法选择不敏感（稳健）；
  705| - 若**很低** → 等级结论主要由**方法选择**驱动而非**策略质量**驱动 → 触发 METHOD_DIVERGENCE 警示，要求人工复核，且**本期不得据此淘汰策略**。
  706| 
  707| 这正是 OECD/JRC 复合指标手册中「稳健性分析」的思路，用最低成本实现。
  708| 
  709| ### 2.6.2 TOPSIS 算法（triangulation.py）
  710| 
  711|     Step 1  向量标准化: r_ij = x_ij / sqrt( Σ_i x_ij² )
  712|     Step 2  加权: v_ij = w_j · r_ij                    # 权重直接取冻结的组合权重（不另设）
  713|     Step 3  正理想解 A+ = ( max_i v_ij | j 为正向 ; min_i v_ij | j 为负向 )
  714|             负理想解 A− = ( min_i v_ij | j 为正向 ; max_i v_ij | j 为负向 )
  715|     Step 4  欧氏距离: D_i+ = sqrt( Σ_j (v_ij − A+_j)² ) ，D_i− = sqrt( Σ_j (v_ij − A−_j)² )
  716|     Step 5  相对贴近度: C_i = D_i− / ( D_i+ + D_i− ) ，C_i ∈ [0,1]
  717|     Step 6  按 C_i 降序得 TOPSIS 排名
  718|     Step 7  Decimal.sqrt() 计算，输出前 quantize 到 1e-12（不入分，但须可复现）
  719| 
  720| ### 2.6.3 GRA 灰色关联分析（triangulation.py）
  721| 
  722|     Step 1  参考序列 x_0 = 各指标当期最优值构成的理想策略
  723|     Step 2  无量纲化（初值化或均值化，配置可切；两种都要跑并比对，属归一化互换敏感性）
  724|     Step 3  差序列 Δ_ij = abs( x_ij − x_0j )
  725|     Step 4  关联系数 ξ_ij = ( min Δ + ρ · max Δ ) / ( Δ_ij + ρ · max Δ )     # ρ 分辨系数，默认 0.5，配置项
  726|     Step 5  关联度 γ_i = Σ_j w_j · ξ_ij
  727|     Step 6  按 γ_i 降序得 GRA 排名
  728|     Step 7  副产物：逐指标的平均关联度 → 供 §2.5 的指标效度诊断使用
  729| 
  730| ### 2.6.4 三角验证判定
  731| 
  732|     ρ_main_topsis = spearman( composite_absolute 排名 , TOPSIS 排名 )
  733|     ρ_main_gra    = spearman( composite_absolute 排名 , GRA 排名 )
  734|     ρ_topsis_gra  = spearman( TOPSIS 排名 , GRA 排名 )
  735| 
  736|     mean_ρ = ( ρ_main_topsis + ρ_main_gra ) / 2
  737|     mean_ρ ≥ divergence_threshold（默认 0.8） → METHOD_AGREEMENT
  738|     mean_ρ <  divergence_threshold            → METHOD_DIVERGENCE：报告首屏警示 + 人工复核 + 本期暂停淘汰
  739| 
  740| **否决权的落地形式（不是装饰）**：METHOD_DIVERGENCE / FLIP_RATE_UNUSABLE 出现在报告**首屏第一段**，且 grade_ledger 中增加 column usable_for_elimination = false。淘汰动作的执行方（运营团队）看的是台账，台账上写着 false，就是真否决。
  741| 

<!-- SDD 1022-1032 -->
 1022| ### 3.7.2 triangulation.py —— TOPSIS / GRA 三角验证（M-F、M-G，不入分）
 1023| 
 1024| | 项 | 内容 |
 1025| |---|---|
 1026| | 签名 | def run(scores: ScoreFrame, normalized: NormalizedFrame, weights, config) -> TriangulationReport |
 1027| | 算法 | TOPSIS 见 §2.6.2；GRA 见 §2.6.3；权重直接取冻结的组合权重，**不另设** |
 1028| | 输出 | topsis_rank、gra_rank、ρ_main_topsis、ρ_main_gra、ρ_topsis_gra、mean_ρ、agreement ∈ {METHOD_AGREEMENT, METHOD_DIVERGENCE}、逐指标 GRA 平均关联度（供 diagnostics 的效度诊断） |
 1029| | 关键约束 | **不产出任何可用于对外披露的排名**；报告与代码注释双处明示仅三角验证（RK-5，T-TOP-03 回归守护） |
 1030| | 可关 | config.triangulation.enabled = false 时跳过并记 TRIANGULATION_DISABLED（不得静默） |
 1031| | 数值 | Decimal.sqrt()，输出前 q12；GRA 的分辨系数 ρ 与无量纲化方式为配置项，两者都纳入 NORM_SWAP 敏感性 |
 1032| 
