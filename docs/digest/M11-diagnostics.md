# digest M11-diagnostics -- 旁路诊断：在线熵权 / CV / VIF / 相关矩阵
# 消费方: WP-diagnostics
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 684-697, 1033-1043
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 684-697 -->
  684| ## 2.5 旁路诊断（第三层作用位）：在线熵权 / CV / VIF / 相关矩阵 / GRA 指标效度
  685| 
  686| diagnostics.py 每期运行，输出 entropy_diagnostic 表与 diagnostics.md，**本期不改任何分数**。它的权力体现在「改下期字典」：
  687| 
  688| | 诊断项 | 计算 | 触发阈值 | 建议动作 | 责任人 |
  689| |---|---|---|---|---|
  690| | 零变异 / 低区分度 | d_j = 1 − e_j | d_j < inactive_threshold | RETIRE_OR_REDLINE | 指标负责人 |
  691| | 共线性 | VIF_j = 1 / (1 − R²_j) | VIF_j > vif_max | MERGE_OR_DROP | 指标负责人 |
  692| | 冗余 | Pearson / Spearman 相关矩阵 | abs(ρ) > corr_max | MERGE_OR_DROP | 指标负责人 |
  693| | 离散度 | CV_j = sd_j / mean_j | CV_j < cv_min | REDEFINE | 指标负责人 |
  694| | **指标效度（GRA）** | 以各指标当期最优值构造参考序列，算每个指标与参考序列的关联度 γ_j | γ_j 连续 k 期趋 0 | CONTENT_VALIDITY_DOUBT：该指标不区分好坏策略，建议移出字典或重定义 | 指标负责人 + 评价管理委员会 |
  695| 
  696| **闭环要求**：诊断结果必须落成**工单**（entropy_diagnostic.csv 中含 suggested_action 与 owner 列），下期字典变更须回写变更记录。诊断不产生动作 = 白算。
  697| 

<!-- SDD 1033-1043 -->
 1033| ### 3.7.3 diagnostics.py —— 在线熵权 / CV / VIF / 相关矩阵（M-E 在线身份、M-J，全部不入分）
 1034| 
 1035| | 项 | 内容 |
 1036| |---|---|
 1037| | 签名 | def compute(facts, metric_dict, config) -> tuple[EntropyDiagnostic, CollinearityReport] |
 1038| | 在线熵权 | 单期计算，公式同 §2.4.2；**结果只写诊断表，绝不回写权重**（INV-3） |
 1039| | VIF | VIF_j = 1 / (1 − R²_j)，R²_j 由指标 j 对其余指标回归得到；实现上用相关矩阵求逆的对角元（等价且无需回归库） |
 1040| | 输出 | EntropyDiagnosticRow：metric_code、e_j、d_j、cv_j、vif_j、max_abs_corr、status ∈ {OK, LOW_VARIATION, INACTIVE, COLLINEAR}、suggested_action、owner |
 1041| | 工单闭环 | suggested_action 与 owner 必须落 CSV，供下期字典变更追踪；诊断不产生动作 = 白算 |
 1042| | 与离线熵权的隔离 | 类型隔离 + 调用隔离：diagnostics 输出对象不含任何可被 aggregate 消费的权重字段 |
 1043| 
