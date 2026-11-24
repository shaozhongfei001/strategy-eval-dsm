# digest M05-grading -- 分级六步 + 滞回 + 版本断点
# 消费方: WP-grading
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 490-500, 958-969
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 490-500 -->
  490| ### 2.3.4 M-K 分级规则（grading.py）
  491| 
  492|     输入: composite_absolute、attainment 覆盖率、evidence_class、redline 结果、上期等级、version_id
  493|     Step 1  按 attainment_floor[L1..L4] 映射基础等级（门槛挂达成率）
  494|     Step 2  证据封顶: evidence_class = C → 最高二级；D → NOT_ASSESSED
  495|     Step 3  目标缺失封顶: max_grade_if_no_target（默认 L3）+ capped_flag + cap_reason
  496|     Step 4  红线覆盖: HARD 命中 → forced_grade
  497|     Step 5  滞回: 升级需连续 upgrade_consecutive_periods 期达标；降级即时（demotion_immediate = true）
  498|     Step 6  版本断点: version_id 变化 → 标记 VERSION_BREAK，不做跨版本趋势比较，滞回状态重置
  499|     输出: grade ∈ {L1, L2, L3, L4, NOT_ASSESSED} + grade_reason_path（有序 reason_code 列表）+ capped + action
  500| 

<!-- SDD 958-969 -->
  958| ### 3.5.4 grading.py —— Step 6 分级 + 滞回 + 版本断点（M-K）
  959| 
  960| | 项 | 内容 |
  961| |---|---|
  962| | 签名 | def assign(scores: ScoreFrame, attain: AttainmentFrame, ev: EvidenceFrame, rl: RedlineFrame, prev: GradeFrame or None, rules: GradeRuleSet) -> GradeFrame |
  963| | 六步 | 见 §2.3.4（基础等级 → 证据封顶 → 目标缺失封顶 → 红线覆盖 → 滞回 → 版本断点） |
  964| | 输出 | grade ∈ {L1, L2, L3, L4, NOT_ASSESSED}；grade_reason_path（**有序** reason_code 列表，可还原判定路径）；capped、cap_reason；action（各级应执行动作与期限）；usable_for_elimination |
  965| | 滞回参数 | upgrade_consecutive_periods（默认 2）、demotion_immediate（默认 true）、红线单期即降 |
  966| | 版本断点 | version_id 变化 → VERSION_BREAK，滞回状态重置，不做跨版本趋势比较 |
  967| | reason_code | CAPPED_NO_TARGET、CAPPED_EVIDENCE_C、VERSION_BREAK、HYSTERESIS_HOLD、FORCED_BY_REDLINE |
  968| | 关键约束 | 等级判定**只看绝对轨**；相对轨综合分只写披露列（P-1） |
  969| 
