# digest M19-contract-outputs -- 输出 5 表 + WeightProvenance 四段
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1216-1245
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1216-1245 -->
 1216| ### 3.11.3 输出 5 张表 + 报告
 1217| 
 1218| | 输出 | 格式 | 一行代表什么 | 谁看 | 用来做什么 |
 1219| |---|---|---|---|---|
 1220| | **score_card** | CSV | 一条策略在一个评价期的完整评分明细 | 评价管理部门、被评价部门 | 回答「我为什么是这个等级」 |
 1221| | **grade_ledger** | CSV | 一条策略的等级变更与应执行动作 | 运营团队、责任部门 | 派活：谁在什么期限前做什么 |
 1222| | **sensitivity_report** | CSV + MD | 一次扰动方案下的等级翻转情况 | 评价管理部门、审计 | 判断本期结论能不能用于淘汰 |
 1223| | **entropy_diagnostic** | CSV | 一个指标的健康状况与建议动作 | 指标负责人 | 字典维护工单 |
 1224| | **triangulation** | MD | 三种方法排序的一致性 | 评价管理部门 | 判断结论是否只是方法选择的产物 |
 1225| | **audit.json** | JSON | 一次运行的全部证据链 | 审计、第二人 | 复跑验证 |
 1226| | **report.md** | MD | 本期评价报告（10 段固定结构） | 管理层、评价管理委员会 | 决策与通报 |
 1227| 
 1228| ### 3.11.4 WeightProvenance（v1.1 由 AhpProvenance 扩展，向后兼容）
 1229| 
 1230|     class WeightProvenance:
 1231|         kind: AHP_ONLY | AHP_ENTROPY_COMBINED | EXPERT_ONLY
 1232|         ahp:                      # 专家两两比较矩阵、λ_max、CI、RI、CR、专家人数、访谈日期、
 1233|                                   # 几何平均法与特征向量法两套权重及其最大差
 1234|         entropy:                  # 标定窗口期列表、各期熵权、中位数熵权、逐指标漂移 drift_j、
 1235|                                   # 命中 INACTIVE 回退的指标清单、被剔除期及原因
 1236|         combine:                  # α 值、α 来源（CALIBRATED | MANUAL）、α 标定报告引用、
 1237|                                   # 逐指标四列对照表（AHP 值 / 熵权值 / 组合值 / 是否回退）、
 1238|                                   # H-1~H-5 校验结果
 1239|         alpha_basis:              # CalibrationReport 整体（候选 α × 指标矩阵、α*、命中约束、
 1240|                                   # 被排除 α 及原因、窗口期清单、run_id、seed）
 1241|         whatif_run_id:            # 权重影响预演运行号；FROZEN 而缺此项 → 配置加载直接失败
 1242|         approved_by / approved_date / effective_from / effective_to
 1243| 
 1244| > **业务含义**：这张表回答「凭什么贡献度占 30%」。以前答案是「专家定的」；现在答案是**完整的推导链（AHP + CR + 熵权 + α 标定）+ 后果预演（whatif）+ 签字人**。
 1245| 
