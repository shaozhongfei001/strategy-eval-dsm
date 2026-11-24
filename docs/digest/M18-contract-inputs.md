# digest M18-contract-inputs -- 输入 8 表总览与逐表关键字段
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1093-1215
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1093-1215 -->
 1093| ## 3.11 数据契约
 1094| 
 1095| ### 3.11.1 输入 8 张表总览
 1096| 
 1097| | # | 表 | 业务含义 | 粒度 | 提供方（建议） | 更新频率 | 性质 |
 1098| |---|---|---|---|---|---|---|
 1099| | T1 | strategy_master | **被评价的对象清单**：哪条策略、哪个版本、属哪个业务领域、谁负责 | 策略 × 版本 | 策略管理部门 / 营销活动管理平台 | 每期 | 业务数据 |
 1100| | T2 | metric_dict | **评价指标字典与口径**：每个指标怎么算、目标多少、谁签认 | 指标 | 指标负责人（评价管理部门牵头） | 变更时 | 治理配置 |
 1101| | T3 | metric_facts | **本期各策略各指标实际值**（长表） | 策略 × 版本 × 期 × 指标 | 数据部门（从各业务系统汇总） | 每期 | 业务数据 |
 1102| | T4 | design_cards | **评价设计卡**：有无对照、成功怎么判、风险约束、谁负责评价 | 策略 × 版本 | 策略上线时的设计者（上线前填） | 策略上线时 | 业务数据 |
 1103| | T5 | redlines | **红线阈值**：哪些指标超限就一票否决 | 指标 | 风险 / 合规 / 消保部门 | 变更时 | 治理配置 |
 1104| | T6 | weights | **权重版本**：维度权重、维度内指标权重、谁批的、怎么来的 | 版本 | 评价管理委员会（AHP + 组合 + 签认） | 年度 | 治理配置 |
 1105| | T7 | grade_rules | **分级门槛与各级动作** | 等级 | 评价管理部门 | 年度 | 治理配置 |
 1106| | T8 | anchor_set | **锚定基准策略集**：用哪几条老策略当尺子 | 集合 | 评价管理部门 | 年度 | 治理配置 |
 1107| 
 1108| > **关键理解**：T2/T5/T6/T7/T8 是**治理配置**（人工签认、变化慢、决定规则）；T1/T3/T4 是**业务数据**（每期变、决定结果）。模型的**全部主观性都集中在治理配置里并且都要签字**，业务数据部分是纯客观计算。这是「可辩护」的结构基础。
 1109| 
 1110| ### 3.11.2 各表关键字段（开发口径）
 1111| 
 1112| **T1 strategy_master**
 1113| 
 1114| | 字段 | 业务含义 |
 1115| |---|---|
 1116| | strategy_id | 策略唯一身份，**跨版本不变** |
 1117| | version_id | 策略版本；**内容一改就是新版本**，跨版本不做趋势比较 |
 1118| | strategy_name | 人能看懂的名字 |
 1119| | biz_domain | 业务领域，**分池的第一维** |
 1120| | scene_code / segment_type | 经营场景 / 客群类型（EXISTING、NEW 等） |
 1121| | online_date / offline_date | 上线、下线日 |
 1122| | owner_dept / owner_name | 责任部门与责任人 —— **三级策略整改要落到这两列** |
 1123| | status | ACTIVE / PAUSED / RETIRED |
 1124| | version_change_note | 版本变更说明，用于判定 VERSION_BREAK |
 1125| 
 1126| **T2 metric_dict（全模型的地基）**
 1127| 
 1128| | 字段 | 业务含义 |
 1129| |---|---|
 1130| | metric_id / metric_name | 指标标识与名称 |
 1131| | dim_code | 属哪个维度（**配置驱动的维度注册表，不硬编码枚举**，D7） |
 1132| | numerator_def / denominator_def | 分子 / 分母口径（**逐字、可签认**；比率类分母必填） |
 1133| | time_window / dedup_rule | 时间窗 / 去重与归因规则 |
 1134| | missing_rule | 缺数据处置：ZERO / SKIP / IMPUTE_MEDIAN / BLOCK |
 1135| | outlier_rule | 异常值处置（如 CLIP_P1_P99） |
 1136| | attainment_formula | RATIO_DIRECT / INVERSE_RATIO / SHORTFALL_CLAMPED / INTERVAL |
 1137| | direction | +1 越大越好 / −1 越小越好 |
 1138| | unit | MONEY_MINOR（最小货币单位）/ COUNT / RATIO / DURATION_SEC |
 1139| | target_value / target_basis | **目标值**及其来源（预算 / 历史基线 / 行业参考），**必须可追溯** |
 1140| | is_redline | 是否红线指标（true 则**不参与熵权组合**，D2 约束①） |
 1141| | owner_name / signoff_status / signoff_date | 责任人 / 签认状态 / 签认日期 —— **PENDING 或 REJECTED 的指标不参与评分** |
 1142| | dim_signoff_status | 维度签认状态（v1.1 新增，D7） |
 1143| | dict_version / caliber_version | 字典版本与口径版本，**必须与事实数据一致**（C-07） |
 1144| 
 1145| **T3 metric_facts（长表）**
 1146| 
 1147| | 字段 | 业务含义 |
 1148| |---|---|
 1149| | strategy_id / version_id / period / metric_id | 四元定位键 |
 1150| | value_num / value_den / value | 分子 / 分母 / 指标值（**金额用最小货币单位整数**） |
 1151| | data_quality_flag | OK / PARTIAL / SUSPECT / STALE —— **SUSPECT 会被剔除**（C-06） |
 1152| | snapshot_time / data_as_of | 快照时间与数据所属时点，用于 C-05 新鲜度 |
 1153| | source_table | 溯源表名 —— 出问题时能查回源头 |
 1154| | caliber_version | 口径版本，须等于 metric_dict.caliber_version（C-07） |
 1155| 
 1156| > **为什么用长表不用宽表**：指标会增减，宽表每次改口径都要改表结构；长表加一行即可，且**缺哪个指标一目了然**（缺行而不是空列），这让 preflight 的缺失率计算准确。
 1157| 
 1158| **T4 design_cards（决定这条策略的分数能不能被相信）**
 1159| 
 1160| | 字段 | 业务含义 |
 1161| |---|---|
 1162| | direct_goal | 这条策略的直接目标 |
 1163| | process_metrics / result_metrics | 过程指标 / 结果指标清单 |
 1164| | observation_window | 观察多久才算数 |
 1165| | data_source / data_timeliness | 数据从哪来、多快到 |
 1166| | eval_method | AB_TEST / RCT / HOLDOUT / DID / SYNTHETIC_CONTROL / GEO / SWITCHBACK / PSM / OBSERVATIONAL_ONLY |
 1167| | **control_arrangement** | NONE / HISTORICAL_BASELINE / CONCURRENT_CONTROL / RANDOMIZED |
 1168| | success_criteria | 成功判定（含显著性水平与最小效应，若有） |
 1169| | risk_constraints | 风险约束清单（喂给红线判定） |
 1170| | eval_owner | 评价责任人 |
 1171| | **alt_method_note** | 无严谨对照条件时用了什么替代方法 |
 1172| | **interpretation_limit** | **解释限制** —— C 类策略**必须填**，否则降 D 不出分（D4） |
 1173| | card_status | COMPLETE / PARTIAL / MISSING（**由完备性规则自动推导，不允许人工填**，防自评宽松） |
 1174| | CEL-0 预留（可空） | incremental_value / incremental_ci_lower / incremental_ci_upper / estimator_method / experiment_id / holdout_id / mde_ok |
 1175| 
 1176| **T5 redlines**
 1177| 
 1178| | 字段 | 业务含义 |
 1179| |---|---|
 1180| | metric_id / level | 哪个指标；HARD（一票否决）/ SOFT（独立扣减） |
 1181| | comparator / threshold_value | 比较方式（GT / GTE / LT / LTE）与阈值 |
 1182| | forced_grade | 违反后强制降到哪级（默认 L4） |
 1183| | reason_code | 原因码，出现在台账与报告里 |
 1184| | waiver_allowed | 是否允许例外豁免（允许则**必须有审批留痕**，无留痕视为未豁免） |
 1185| 
 1186| **T6 weights（年度签认，期内冻结）**
 1187| 
 1188| | 字段 | 业务含义 |
 1189| |---|---|
 1190| | weight_version_id / status | 版本号；**只有 FROZEN 能用于评分**（DRAFT 是待签认草稿） |
 1191| | effective_from / effective_to | 生效期间 —— **期内权重不变，这是跨期可比的前提**（治 F2） |
 1192| | level1_weights / level2_weights | 维度权重（Σ=1）/ 维度内指标权重（维度内 Σ=1） |
 1193| | provenance.* | 见 §3.11.4 |
 1194| | approved_by / approved_date | 谁批的、什么时候批的 |
 1195| 
 1196| **T7 grade_rules**
 1197| 
 1198| | 字段 | 业务含义 |
 1199| |---|---|
 1200| | grade_code / grade_label | L1「重点推广、沉淀复用」/ L2「持续运行、跟踪提升」/ L3「专项诊断、限期优化」/ L4「暂停评估、整改退出」（标题逐字取自分册 A 第三章（七）） |
 1201| | **attainment_floor** | **该等级的绝对达成率下限** —— 门槛挂在是否达标上，不是排第几（治 F3） |
 1202| | evidence_class_min | 该等级要求的最低证据等级（L1 建议要求 ≥ B） |
 1203| | redline_pass_required | 是否要求红线全过 |
 1204| | promotion_streak | 连续达标几期才允许升级（防抖动；降级默认即时） |
 1205| | actions / action_gate | 该级应执行动作（逐字取自原文，直接写进台账）/ 一级库动作门禁 |
 1206| | max_grade_if_no_target | 绝对轨不可用时的封顶等级（默认 L3） |
 1207| 
 1208| **T8 anchor_set**
 1209| 
 1210| | 字段 | 业务含义 |
 1211| |---|---|
 1212| | anchor_set_id / strategy_ids | 一组**长期保留的参照策略**，作为归一化的尺子 |
 1213| | effective_from / effective_to | 生效期间 |
 1214| | rationale | **选取依据（必须可辩护）**：建议覆盖各业务领域与各历史等级，且已运行满一个完整周期 |
 1215| 
