# digest M42-l0-tools -- L0a / L0b 离线工具层规格
# 消费方: WP-weights_*,WP-whatif
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1066-1075
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1066-1075 -->
 1066| ## 3.9 L0a / L0b 离线工具层
 1067| 
 1068| | 模块 | 签名 | 关键规格 | 异常与退出码 |
 1069| |---|---|---|---|
 1070| | weights_ahp.py（L0a） | elicit(matrices) -> AhpResult；check_consistency(A) -> ConsistencyReport | 几何平均法 + 特征向量法交叉验证；多专家几何聚合；CR ≥ 0.1 拒绝并输出最不一致前 5 对；**产出 status 只能是 DRAFT** | MatrixNotReciprocalError、ConsistencyFailedError（退出码 6）；写 FROZEN → 抛错 |
 1071| | weights_combine.py（L0a） | combine(ahp, entropy, opts) -> CombinedWeights；build_draft(...) -> WeightVersionDoc | 六步见 §2.4.3；INACTIVE 回退；H-1~H-5 硬约束；status = DRAFT | AlphaInfeasibleError（由标定侧抛）、EntropyInsufficientSample（降级为 α=1 并显著标注） |
 1072| | weights_calibrate.py（L0b） | calibrate(grid, window, inputs, config) -> CalibrationReport | 字典序可行集取最小可行 α；五项稳定性指标；边界情形四种处置；报告写入 provenance.alpha_basis | AlphaInfeasibleError（退出码 7）、AlphaFloorInfeasibleError |
 1073| | whatif.py（L0b） | run(candidate, baseline, inputs, config, period) -> WhatifReport | 重跑 Step 1–7（可选 Step 8）；Δcomposite = Σ ΔW_d · dim_d 精确分解（两段串行处理维度内权重变化）；输出写独立目录（INV-2） | redline_delta 非空 → 报告标注 CONFIG_INCONSISTENT 并建议拒绝签认 |
 1074| | fixtures_gen.py（L0a） | gen(spec) -> Fixtures | 生成合成策略 / 指标 / 事实 / 设计卡 / 红线 / 权重 / golden 期望值；**不使用任何真实客户数据**；可复现（固定 seed）；覆盖 G-01~G-15 每条用例的触发条件 | —— |
 1075| 
