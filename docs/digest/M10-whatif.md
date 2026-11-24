# digest M10-whatif -- 权重变更影响预演 / 归因分解 / 只读 INV-2
# 消费方: WP-whatif
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 640-683
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 640-683 -->
  640| ### 2.4.5 whatif：权重变更影响预演（whatif.py）
  641| 
  642| **定位**：AHP / 组合权重在**签认前**的后果显示器。这是让权重决策从抽象讨论变成「看得到后果的选择」的关键工具，也是治理链上最实用的一环。
  643| 
  644|     dsm whatif --weights config/weights_WV-DRAFT.yaml --period 2026-09
  645|                [--baseline WV-2026-01] [--out reports/whatif/] [--include-sensitivity]
  646| 
  647| **执行内容**：用候选权重重跑指定历史期的 Step 1–7（Step 0 用候选权重重新校验 C-01 / C-03），可选再跑 Step 8；**全程只读输入，输出写独立目录**（INV-2）。
  648| 
  649| **WhatifReport 结构**：
  650| 
  651|     period / candidate_weight_version_id / baseline_weight_version_id
  652|     grade_changes: list[GradeChange]      # 谁升谁降
  653|         GradeChange = { strategy_id, version_id, baseline_grade, whatif_grade,
  654|                         delta_composite, main_driver_dim, explanation }
  655|     unchanged_count: int
  656|     occupancy_delta: OccupancyDelta       # L1-L4 与 NOT_ASSESSED 计数变化、分池/合并占比变化
  657|     redline_delta: list[str]              # 红线触发集合是否变化（正常应为空）
  658|     evidence_gate_delta: list[str]        # 一级库准入集合变化
  659|     attribution: list[DimAttribution]     # 维度级贡献分解
  660|     sensitivity_delta: SensitivityDelta | None   # flip_rate / stability 分布变化
  661|     warnings: list[RobustCode]
  662| 
  663| **Δcomposite 的精确分解（LINEAR 算子下可完全分解，这是选 LINEAR 为默认算子的额外收益）**：
  664| 
  665|     Δcomposite = composite(whatif) − composite(baseline)
  666|                = Σ_d [ W_d(whatif) · dim_d ] − Σ_d [ W_d(baseline) · dim_d ]
  667|                = Σ_d [ (W_d(whatif) − W_d(baseline)) · dim_d ]
  668|                = Σ_d ΔW_d · dim_d
  669| 
  670|     即每个维度的贡献 = ΔW_d · dim_d，**求和严格等于总差**（1e-12 容差，T-WIF-01 断言）。
  671|     注意：dim_d 本身不随维度权重变化（只有维度内权重变化才会改变 dim_d）。
  672|           因此若 level2_weights 也变了，需拆成两段分解：先固定维度权重算「维度内权重变化」的影响，
  673|           再算「维度权重变化」的影响。实现上按两段串行分解并分别报告，避免交叉项归因错误。
  674|     GEOMETRIC 算子下无精确线性分解 → 改用对数差分近似并标注 APPROXIMATE_ATTRIBUTION。
  675| 
  676| **三条治理用途（写进制度建议）**：
  677| 
  678| 1. **签认前必看**：weight_version 从 DRAFT 改 FROZEN 的申请，必须附对应 whatif run_id（缺则配置加载失败）
  679| 2. **异常拦截**：若 whatif 显示 redline_delta 非空 → **直接拒绝**。红线判定与权重无关，出现变化说明配置有误（这是一条免费的配置一致性检查）
  680| 3. **沟通材料**：grade_changes 清单可直接用于向被评价部门说明权重调整会影响谁，降低签认阻力与后续申诉
  681| 
  682| **性能**：单期重跑，与 score 同量级；--include-sensitivity 时约为 1 + 2×维度数 倍。
  683| 
