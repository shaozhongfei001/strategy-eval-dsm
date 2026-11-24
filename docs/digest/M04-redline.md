# digest M04-redline -- 红线非补偿 + HARD/SOFT + 豁免
# 消费方: WP-redline
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 478-489, 984-995
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 478-489 -->
  478| ### 2.3.3 M-C 阈值否决 / 红线非补偿（redline.py）
  479| 
  480|     HARD 红线: 命中且无有效豁免 → forced_grade（默认 L4）
  481|                综合分**照算并披露**，但等级判定被旁路覆盖，分数不生效
  482|                reason_code = REDLINE_HARD_<code>；豁免须有 approval_id + 有效期
  483|     SOFT 红线: 命中 → 独立扣减（在等级判定之外单列），**不进加权**
  484|                reason_code = REDLINE_SOFT_<code>；扣减幅度由 grade_rules.yaml 配置
  485| 
  486| **为什么用阈值法而不是 PROMETHEE / ELECTRE**：非补偿的目的（风险不能被业绩买回）用红线旁路否决即可达成，实现成本是一个前置判断；outranking 类方法需要构造偏好关系矩阵、设定偏好 / 无差异 / 否决三类阈值，参数数量翻倍且难解释。**M4 之后可选引入**，不在最省力补救范围内。
  487| 
  488| **为什么红线指标不参与熵权组合（D2 约束①）**：风险 / 合规 / 体验类指标常年低变异，若参与数据驱动赋权，其权重会被系统性压低（F1）。把它们整条从加权体系里拿出来、改走硬阈值，是比「给它们设权重下限」更干净的解法。
  489| 

<!-- SDD 984-995 -->
  984| ### 3.6.2 redline.py —— Step 4 红线非补偿（M-C）
  985| 
  986| | 项 | 内容 |
  987| |---|---|
  988| | 签名 | def evaluate(facts, redlines: RedlineSet, waivers: WaiverSet) -> RedlineFrame |
  989| | HARD | 命中且无有效豁免 → forced_grade（默认 L4）；综合分照算并披露但**不生效** |
  990| | SOFT | 命中 → 独立扣减（在等级判定之外单列），**不进加权** |
  991| | 豁免 | 必须有 approval_id + 有效期 + 豁免范围；过期或范围不符 → 视为无豁免并记 WAIVER_INVALID |
  992| | 关键约束 | 红线指标**不参与熵权组合**（D2 约束①）；红线判定与权重**完全无关** → whatif 中 redline_delta 非空即为配置错误信号 |
  993| | reason_code | REDLINE_HARD_<code>、REDLINE_SOFT_<code>、WAIVER_INVALID、WAIVER_EXPIRED |
  994| | 阈值来源 | redlines.yaml 必须引用行内既有制度文号；**不得由模型方拟定**（R4） |
  995| 
