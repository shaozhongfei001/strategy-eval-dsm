# digest M24-pooling -- 分池禁混排 / 一级库门禁 / 占比双报
# 消费方: WP-pooling
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 996-1007
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 996-1007 -->
  996| ### 3.6.3 pooling.py —— Step 7 分池禁混排 + 一级库门禁 + 占比双报
  997| 
  998| | 项 | 内容 |
  999| |---|---|
 1000| | 签名 | def build(scores, grades, ev, master, config) -> tuple[PoolFrame, PoolStats] |
 1001| | 分池维度 | pool_key = (biz_domain, evidence_class)；**禁止跨池混排**（P-6） |
 1002| | 一级库门禁 | 准入条件：evidence_class ∈ {A, B} 且 grade = L1 且 无 HARD 红线命中 且 无 FLIP_RATE_UNUSABLE；C 类**不得**进一级库 |
 1003| | 占比双报 | 同时报「池内占比」与「合并占比」，并披露各池的证据结构（A/B/C/D 计数）。禁止只报合并占比（会让 C 类混在 A 类里被误读） |
 1004| | NOT_ASSESSED | 单独计数，**不计入分母**，在台账与报告中显式列出条数与原因分布 |
 1005| | reason_code | POOL_TOO_SMALL、PRIMARY_POOL_REJECTED_EVIDENCE、PRIMARY_POOL_REJECTED_ROBUST |
 1006| | 输出 | PoolFrame（逐策略 pool_key、pool_rank、primary_pool_eligible、reject_reason）+ PoolStats（各池计数、占比双报、证据结构） |
 1007| 
