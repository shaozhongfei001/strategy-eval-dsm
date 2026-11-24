# digest M38-k-params -- K-01 ~ K-20 开放参数（须行方签认，模型侧不得拟定）
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1734-1760
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1734-1760 -->
 1734| ## 5.1 开放参数 K-01 ~ K-20（全部须行方签认，模型侧不得拟定）
 1735| 
 1736| | # | 参数 | 位置 | 性质 | 校准 / 确定方法 |
 1737| |---|---|---|---|---|
 1738| | K-01 | 维度权重 W_d | weights yaml | **治理参数** | AHP 两两比较 + 一致性检验（CR < 0.1）；专家组 ≥ 5 人；结果签认并冻结 |
 1739| | K-02 | 维度内指标权重 w_j | weights yaml | **治理参数** | 同上；v1.1 起与熵权按 α 组合后冻结 |
 1740| | K-03 | 各级 attainment_floor | grade_rules yaml | **治理参数** | 用历史策略回测标定：取达成率分布分位点（如 L1 = P80、L2 = P50、L3 = P20），并与业务可接受的淘汰比例联立求解 |
 1741| | K-04 | 红线阈值（投诉率、退订率、触达频次上限、合规违规数） | redlines yaml | **治理参数** | 引用行内既有制度阈值 / 监管要求 / 客诉管理办法，**不得由模型方拟定** |
 1742| | K-05 | attainment_cap | eval_config | 技术参数 | 取历史达成率 P99 与业务可解释上限的较大者，建议 1.5–2.0 区间内选定 |
 1743| | K-06 | min_coverage_for_absolute_track | eval_config | 技术参数 | 依指标字典目标值覆盖率现状定；先测现状再定，避免大面积封顶 |
 1744| | K-07 | min_sample_size_for_A / 显著性水平 / 最小可检测效应 | eval_config | **治理参数** | 由行方统计口径或既有 AB 平台规范提供 |
 1745| | K-08 | promotion_streak / demotion_immediate | grade_rules yaml | **治理参数** | 与评价周期联定；建议升级需 2 期、降级即时（审慎不对称） |
 1746| | K-09 | 评价周期（MONTH / QUARTER） | eval_config | **治理参数** | 须与策略迭代周期对齐；高频迭代策略建议 MONTH 或滚动窗口 |
 1747| | K-10 | missing_rate_warn / missing_rate_block | eval_config | 技术参数 | 先用历史数据跑出缺失率分布，取 P75 / P95 作为初始阈值 |
 1748| | K-11 | flip_rate 管理阈值（stable_max / review_max） | eval_config | **治理参数** | 首轮运行后按实际分布标定；建议初始 5% / 15% |
 1749| | K-12 | 锚定基准策略集成员 | anchor_set yaml | **治理参数** | 覆盖各 biz_domain 与各历史等级、运行满一个完整周期的策略；须书面说明选取依据 |
 1750| | K-13 | 证据折扣表（仅当 evidence_mode = DISCOUNT） | eval_config | **治理参数** | **建议不启用**；若启用须经审批并纳入敏感性分析 |
 1751| | K-14 | 维度指标细项与口径 | metric_dict csv | **治理参数** | 由行方按分册 A 三（四）要求补齐并签认（= P0-5，全模型的地基） |
 1752| | K-15 | alpha_floor | weight_construction | **治理参数** | 建议 0.50，含义「业务判断至少占一半」；由评价管理委员会确定，**不由数据标定** |
 1753| | K-16 | drift_budget | weight_construction | **治理参数** | 先用历史数据跑出各 α 的 drift 分布，取 P25 作为初始预算，再由委员会确认 |
 1754| | K-17 | boundary_budget | weight_construction | **治理参数** | 同上思路；含义「最多容忍多少比例的策略处于等级边界」 |
 1755| | K-18 | boundary_epsilon | weight_construction | 技术参数 | 取 attainment_floor 量纲的 2%–5%，与指标精度匹配 |
 1756| | K-19 | min_dim_weight | weight_construction | **治理参数** | 任一维度的最低话语权，建议 ≥ 0.05；由委员会确定 |
 1757| | K-20 | max_shift_from_ahp | weight_construction（H-5） | **治理参数** | 建议 0.30；过松则熵权实质主导，过紧则组合无意义（RK-14） |
 1758| 
 1759| > **纪律**：K-15~K-20 全部是**治理参数而非统计参数** —— 它们表达的是「行方愿意让数据在多大程度上影响专家判断」，必须由人签认，**不得由标定程序自行选择**（P-13 机器守护）。α 本身由标定给出，但被 alpha_floor 与 H-5 双重约束。
 1760| 
