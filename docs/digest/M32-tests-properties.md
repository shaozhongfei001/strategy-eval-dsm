# digest M32-tests-properties -- P-1 ~ P-15 属性不变量
# 消费方: WP-properties
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1421-1440
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1421-1440 -->
 1421| ### 3.16.3 属性不变量 P-1 ~ P-15
 1422| 
 1423| | # | 不变量 | 断言 |
 1424| |---|---|---|
 1425| | P-1 | **单调性** | 任一正向指标值提升（其余不变）→ composite_absolute 不下降 |
 1426| | P-2 | **非补偿性** | 任一 HARD 红线违反 → grade 恒等于 forced_grade，**与其余指标多好无关** |
 1427| | P-3 | **幂等性** | 同输入同配置运行两次 → reproducibility_hash 相等 |
 1428| | P-4 | **锚定不变性** | 向当期集合新增一个不在锚定集的策略 → 存量策略的 norm 与 grade 不变 |
 1429| | P-5 | **权重归一（扰动下）** | 任何扰动方案下 Σ W_d = 1（1e-12 容差） |
 1430| | P-6 | **证据门禁单调** | evidence_class 由 A/B 降为 C 时，eligible_for_L1_library 只可能由 true 变 false，绝不反向放宽 |
 1431| | P-7 | **金额精确性** | MONEY_MINOR 字段全程整数运算，结果与 Decimal 参考实现精确相等 |
 1432| | P-8 | **封顶有效性** | 任一指标 attainment ≤ attainment_cap |
 1433| | P-9 | **降级诚实性** | 绝对轨覆盖率不足时，grade 必不优于 max_grade_if_no_target |
 1434| | P-10 | **无静默默认** | 任一 PLACEHOLDER 未替换 → 配置加载阶段即抛错，不进入计算 |
 1435| | **P-11** | 权重来源可追溯 | 任何 FROZEN 权重版本必须具备完整 provenance（AHP 矩阵 + CR；若 combined 则含 α + alpha_basis + whatif_run_id），缺任一项 → 配置加载失败 |
 1436| | **P-12** | **α 不改变治理约束** | 对任意 α ∈ [alpha_floor, 1]：红线违反恒为 forced_grade；C 类恒不得进一级库；D 类恒不出分（**权重变化不得成为绕过门禁的通道**） |
 1437| | **P-13** | 治理预算不可被标定篡改 | calibrate / combine 的运行不得修改 alpha_floor、drift_budget、boundary_budget、boundary_epsilon、min_dim_weight、max_shift_from_ahp 的取值 |
 1438| | **P-14** | 组合权重归一 | 任意 α、任意回退组合下，Σ W_d = 1 且每维度内 Σ w_j = 1（1e-12） |
 1439| | **P-15** | **回退不稀释** | 命中 ENTROPY_INACTIVE_FALLBACK 的指标，其组合权重严格等于 AHP 权重（未经维度归一前） |
 1440| 
