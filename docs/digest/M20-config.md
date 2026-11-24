# digest M20-config -- config.py 规格 + 配置体系 + PLACEHOLDER 纪律
# 消费方: WP-config
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 873-883, 1246-1260
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 873-883 -->
  873| ### 3.3.4 config.py —— 配置加载与 PLACEHOLDER 拦截
  874| 
  875| | 项 | 内容 |
  876| |---|---|
  877| | 职责 | 加载 eval_config.yaml / weights_*.yaml / redlines.yaml / grade_rules.yaml / anchor_set.yaml / ahp_matrices.yaml，做语义校验，并**拦截一切未签认占位值** |
  878| | PLACEHOLDER 拦截 | 递归遍历配置树，凡值为字符串 PLACEHOLDER、null（且字段声明为必填）、或形如 TODO / TBD / XXX 的，收集**全部**未填字段路径后一次性抛 ConfigPlaceholderError（不允许只报第一个） |
  879| | 语义校验 | Σ W_d = 1；每维度内 Σ w_j = 1；attainment_floor 单调（L1 > L2 > L3 > L4）；红线阈值引用的指标必须存在于 metric_dict；grade_rules 的 action 必须非空；anchor_set 成员必须存在于 strategy_master |
  880| | 权重版本校验 | status 必须为 FROZEN；当前评价期必须落在 [effective_from, effective_to]；**缺 whatif_run_id 而 status = FROZEN → 加载失败**（v1.1 新增，机器强制签认前必看预演） |
  881| | 异常 | ConfigPlaceholderError（退出码 3）、ConfigSemanticError、WeightVersionInvalidError |
  882| | 守护 | P-10（属性测试：任意含 PLACEHOLDER 的配置都不得产出分数） |
  883| 

<!-- SDD 1246-1260 -->
 1246| ## 3.12 配置体系与 PLACEHOLDER 拦截
 1247| 
 1248| | 配置文件 | 内容 | 签认方 |
 1249| |---|---|---|
 1250| | eval_config.yaml | 评价期类型、算子选择、evidence_mode、triangulation.enabled、cel.enabled、缺失与异常值策略、敏感性方案与阈值（stable_max / review_max / divergence_threshold）、loo_sampling_threshold | 评价管理部门 |
 1251| | metric_dict.csv | 指标口径、目标值、签认状态、维度归属 | 指标负责人 + 业务部门 |
 1252| | weights_WV-*.yaml | 维度与指标权重、provenance、status | 评价管理委员会 |
 1253| | redlines.yaml | HARD / SOFT 阈值、forced_grade、豁免规则（**须引用行内既有制度文号**） | 风险 / 合规 / 消保 |
 1254| | grade_rules.yaml | attainment_floor、evidence_class_min、promotion_streak、各级 action | 评价管理委员会 |
 1255| | anchor_set.yaml | 锚定成员、生效期、rationale | 评价管理部门 |
 1256| | ahp_matrices.yaml | 专家两两比较矩阵、专家标识、访谈日期 | 评价管理委员会 |
 1257| | weight_construction（在 eval_config 内） | alpha_floor、drift_budget、boundary_budget、boundary_epsilon、min_dim_weight、max_shift_from_ahp、alpha_grid、标定窗口 N | 评价管理委员会（**K-15~K-20 全部治理参数**） |
 1258| 
 1259| **PLACEHOLDER 纪律（R4 / P-10）**：所有业务数值默认写 PLACEHOLDER；config.py 递归扫描，**一次性列出全部未填字段路径**后抛 ConfigPlaceholderError（退出码 3）。模型侧**不得**拟定任何权重、门槛、阈值、单价、周期、样本量。
 1260| 
