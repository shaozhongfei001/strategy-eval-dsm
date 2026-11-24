# digest M22-preflight -- C-01 ~ C-10 前置校验
# 消费方: WP-preflight
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 896-920
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 896-920 -->
  896| ### 3.4.1 preflight.py —— Step 0 前置校验（C-01 ~ C-10）
  897| 
  898| | 编号 | 检查项 | 判据 | 严重度与动作 |
  899| |---|---|---|---|
  900| | C-01 | 权重版本有效性 | status = FROZEN；评价期在生效区间内；含 approved_by / approved_date / whatif_run_id | **BLOCK**，退出码 2 |
  901| | C-02 | 指标签认状态与维度覆盖 | 未签认指标 → 剔除并重归一（WARN）；某维度被清空 → 该维度 W 置 0 重归一；清空维度数 ≥ 2 → **BLOCK** | WARN / BLOCK |
  902| | C-03 | 权重与指标字典对齐 | 每个签认指标在权重配置中有对应项；无孤儿权重项；两级权重各自归一（1e-12） | **BLOCK** |
  903| | C-04 | 缺失率 | 超 warn 阈 → WARN 并按 missing_rule 处理；超 block 阈 → 该策略 NOT_ASSESSED（台账单独计数） | WARN / 策略级降级 |
  904| | C-05 | 数据新鲜度 | metric_facts 的 data_as_of 与评价期一致；滞后 → WARN + score_card 标注 | WARN |
  905| | C-06 | 数据质量标记 | 上游 quality_flag = SUSPECT → 剔除该指标（降 coverage）+ WARN | WARN |
  906| | C-07 | 口径版本一致性 | metric_facts 声明的 caliber_version 必须等于 metric_dict 的 caliber_version | **BLOCK** |
  907| | C-08 | 评价设计卡完备性 | PARTIAL（缺对照安排或成功判定）→ 证据上限压到 C；MISSING → 证据 D → NOT_ASSESSED | 降级 |
  908| | C-09 | 金额字段整数性 | 任何 *_minor 字段出现小数或非数值 | **BLOCK** |
  909| | C-10 | 锚定集有效性 | 成员存在、未被淘汰、未换 version_id；失效 → 回退仅当期归一化 + **报告首屏标注秩反转风险** | WARN + 降级 |
  910| 
  911| > **口径统一声明**：本表为整合后 C-01~C-10 的唯一口径；若与 DSN §4.6 逐条文字有出入，**以本表为准**（§0.3 D1 裁决的延伸）。
  912| 
  913| | 项 | 内容 |
  914| |---|---|
  915| | 函数签名 | def run(inputs: Inputs, config: AppConfig) -> PreflightResult |
  916| | PreflightResult | status ∈ {PASS, WARN, BLOCK}；findings: list[Finding]（含 code / severity / scope / detail / owner_hint）；coverage_after_drop（剔除未签认指标后的覆盖率） |
  917| | BLOCK 行为 | **只写 audit_bundle**（记录为什么没跑出结果）+ 退出码 2，**不产出 score_card** |
  918| | 原则 | 宁可不评，不可错评；任何 WARN 都进最终报告附录，不会被静默吞掉 |
  919| | 复杂度 | O(策略数 × 指标数) |
  920| 
