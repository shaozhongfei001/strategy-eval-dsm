# digest M26-reports -- report.md 十段 / score_card 各段含义 / grade_ledger 设计
# 消费方: WP-reports
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1057-1065, 1608-1635
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1057-1065 -->
 1057| ### 3.8.2 reports.py —— 报告生成
 1058| 
 1059| | 项 | 内容 |
 1060| |---|---|
 1061| | 签名 | def render(bundle: AuditBundle, frames: AllFrames, config) -> ReportSet |
 1062| | 产出 | report.md（**10 段固定结构**）、score_card.csv、grade_ledger.csv、sensitivity_report.csv、entropy_diagnostic.csv、triangulation.md、audit.json |
 1063| | report.md 十段 | ①首屏结论与**可用性声明**（能否用于淘汰）②本期评价范围与覆盖率③等级分布与占比双报④一级库准入与拒绝清单⑤红线命中与豁免清单⑥证据结构（A/B/C/D 计数与 NOT_ASSESSED 明细）⑦稳健性结果（flip_rate / 稳定性标签分布 / LOO 主导指标）⑧方法三角一致性⑨指标健康度与字典工单⑩附录：preflight 全部 WARN、降级动作全量、权重版本与 provenance、复现指引 |
 1064| | 硬要求 | 首屏第一段必须写 usable_for_elimination 与其依据；**禁止**只报合并占比；**禁止**省略 NOT_ASSESSED 计数；任何降级都必须在正文可见位置披露，不得只放附录 |
 1065| 

<!-- SDD 1608-1635 -->
 1608| ### 4.6.1 score_card 的关键段与业务含义
 1609| 
 1610| | 段 | 业务含义 |
 1611| |---|---|
 1612| | 版本四元组（weight_version_id / dict_version / anchor_set_id / run_id） | **这个分数是哪套规则算出来的** —— 申诉与复跑的第一入口 |
 1613| | per_metric（实际值 / 目标值 / 达成率三列并排） | 业务方最容易质疑的就是这一层，所以**全部保留、不做黑箱** |
 1614| | per_dim（各维度达成率、相对分、coverage、W） | coverage 低说明这个维度评得不全（有指标缺目标值），**必须显式暴露** |
 1615| | composite_absolute | **主分数**，用于定级。含义是加权后的整体目标达成率：1.0 = 刚好达标，1.2 = 超额 20% |
 1616| | composite_relative | **辅分数**，仅用于同池排名。**不能用来判达标** |
 1617| | evidence_class + evidence_reason | **这个分数有多可信**，以及为什么（B = 有同期对照的准实验，不是随机分流） |
 1618| | interpretation_limit | C 类必填的解释限制；未填 → 降 D 不出分 |
 1619| | redline_pass + redline_flags | 有没有踩线。踩线时分数照算但**不生效**，等级直接强制 |
 1620| | grade + grade_reason_codes | 最终等级与**判定路径**（按判定顺序记录，能一眼看出是正常评上的一级，还是被证据门禁降下来的二级） |
 1621| | capped_flag + cap_reason | 是否被封顶（无目标值 / 证据 C）及原因 |
 1622| | ranking_pool + rank_in_pool + pool_size | **在哪个池里排第几**。池 = 业务领域 × 证据等级，所以 A 类策略永不与 C 类策略同池比较 |
 1623| | eligible_for_L1_library + l1_gate_reasons | **能不能进优质策略库、能不能被跨机构推广**。这是最实际的一个布尔值 |
 1624| | stability_label + flip_under_pct10/20 | **这个等级稳不稳**。NEAR_BOUNDARY = 权重稍动就可能变级 → 报告标注边界结论，不得作为淘汰唯一依据 |
 1625| | usable_for_elimination | 本期结论能否用于淘汰（受 flip_rate 与方法分歧双重约束） |
 1626| | CEL-0 增量三列 + value_captured | 首版恒为空，报告显式写「本期末接入增量估计」，**不得静默留白** |
 1627| 
 1628| ### 4.6.2 grade_ledger 的关键设计
 1629| 
 1630| - **recommended_action 与 decided_action 分两列**，直接落地主报告第三章「评价建议与执行决定区分记录」的要求。含义：模型只给建议，**人做决定并签字**；两者不一致时必须写 decision_note —— 既保护业务判断空间，也留下问责痕迹
 1631| - 各级动作**逐字取自分册 A 第三章（七）**，被评价部门看到的是自己文件里的语言，不是模型发明的新词
 1632| - 三级策略**必须**有 owner_dept / owner_name / deadline（原文「明确优化责任部门、整改要求及完成时限」）
 1633| - 四级退出策略**必须**有 archive_ref（原文「纳入退出管理并做好历史记录归档」）
 1634| - 缺项会在报告中标记为**台账不完整**
 1635| 
