# digest M02-attainment -- 达成率四公式 + 模块规格 + 边界
# 消费方: WP-attainment
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 441-461, 923-934
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 441-461 -->
  441| ### 2.3.1 M-A 目标达成率法（attainment.py）
  442| 
  443|     方向为正（越大越好，如转化率、收入）:
  444|         attainment_j = actual_j / target_j
  445|     方向为负（越小越好，如投诉率、成本）:
  446|         attainment_j = target_j / actual_j          （actual_j = 0 时按 on_zero 规则处理）
  447|     区间型（落在区间内为达标）:
  448|         attainment_j = 1 − distance_to_interval_j / interval_halfwidth_j
  449| 
  450|     统一裁剪: attainment_j = clip(attainment_j, 0, attainment_cap)   # attainment_cap 为治理参数
  451|     无目标值: attainment_j = null → 该指标不计入绝对轨，触发等级封顶 max_grade_if_no_target
  452| 
  453| **规则**：
  454| 
  455| | 规则 | 内容 | 理由 |
  456| |---|---|---|
  457| | A-1 | 达成率一律用 safe_div，显式指定 on_zero（分母为 0 时的返回值） | R6 数值口径唯一 |
  458| | A-2 | 目标值缺失 → **不得**用池内均值或历史均值代替 | R4 不编造参数 |
  459| | A-3 | 达成率裁剪上限 attainment_cap 防止单指标爆表拉高综合分 | 抗极端值 |
  460| | A-4 | 分级门槛**只挂达成率**，不挂相对分位 | 治 F3 |
  461| 

<!-- SDD 923-934 -->
  923| ### 3.5.1 attainment.py —— Step 1 绝对达成率轨（入分主方法 M-A）
  924| 
  925| | 项 | 内容 |
  926| |---|---|
  927| | 签名 | def compute(facts: MetricFactFrame, metric_dict: MetricDict, config: AppConfig) -> AttainmentFrame |
  928| | 输出 | AttainmentFrame：逐（策略 × 指标）的 attainment、direction、target_source、has_target、capped_flag；逐策略的 attainment_coverage（有目标值指标数 / 签认指标数） |
  929| | 算法 | 见 §2.3.1（正向 actual/target；负向 target/actual；区间型 1 − dist/halfwidth；统一 clip 到 [0, attainment_cap]） |
  930| | 边界 | target = 0 且方向为负 → 走 safe_div 的 on_zero 配置；actual < 0 → 记 NEGATIVE_ACTUAL 并按 missing_rule 处理；目标值缺失 → attainment = null（**不得**用均值代替） |
  931| | reason_code | NO_TARGET_VALUE、ATTAINMENT_CAPPED、NEGATIVE_ACTUAL |
  932| | 关键约束 | **本模块的输出是分级门槛的唯一依据**；grading.py 不得从 normalize.py 取值判等级（P-1 属性测试守护） |
  933| | 复杂度 | O(策略数 × 指标数) |
  934| 
