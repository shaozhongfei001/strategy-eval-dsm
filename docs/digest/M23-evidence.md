# digest M23-evidence -- 证据强度五步短路 / GATE_ONLY / A 类保守性
# 消费方: WP-evidence
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 972-983
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 972-983 -->
  972| ### 3.6.1 evidence.py —— Step 3 证据强度分级（A/B/C/D，D4 裁决后统一四档）
  973| 
  974| | 项 | 内容 |
  975| |---|---|
  976| | 签名 | def classify(design_cards: DesignCardFrame, facts: MetricFactFrame, config) -> EvidenceFrame |
  977| | 判定顺序（短路） | ① 设计卡缺失 → **D**（NOT_ASSESSED）；② randomized=true 且有对照组与事前成功判定（含显著性口径）→ **A**；③ 准实验（DID / 合成对照 / 分层匹配 / 时间断点，须写方法名与假设）→ **B**；④ 仅观测 → **C**；⑤ C 类**未写 interpretation_limit** → 降为 **D** |
  978| | 模式 | 默认 evidence_mode = **GATE_ONLY**：证据等级**不乘入分数**，只做封顶、分池与一级库准入。（另一模式 DISCOUNT 保留接口，启用须另立 ADR 并纳入敏感性扰动维度） |
  979| | A 类判定的保守性 | success_criteria 为自由文本时，用**外置可审计的关键词清单**识别显著性口径；清单外一律**保守不认 A**；**禁止用模型猜测**（RK-4） |
  980| | 输出 | evidence_class、evidence_reason、evidence_source（CARD_ONLY / CEL_ESTIMATED）、control_group_id、interpretation_limit |
  981| | 与 CEL 接口 | 单向：CEL → T4 → evidence.py；evidence.py **不得**反向调用 CEL |
  982| | reason_code | EVIDENCE_CARD_MISSING、EVIDENCE_C_NO_LIMIT、EVIDENCE_DOWNGRADED_PARTIAL |
  983| 
