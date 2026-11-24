# digest M28-downgrade-matrix -- 错误处理与降级矩阵（V-14 逐条断言用）
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1276-1309
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1276-1309 -->
 1276| ## 3.14 错误处理与降级矩阵（R5：诚实降级优于假装精确）
 1277| 
 1278| | 情形 | 检测点 | 降级动作 | 是否出分 | 披露位置 |
 1279| |---|---|---|---|---|
 1280| | 权重版本过期或 DRAFT | C-01 / config | **BLOCK** | 否 | audit + 退出码 2 |
 1281| | 权重 FROZEN 但缺 whatif_run_id | config | **加载失败** | 否 | 错误信息 |
 1282| | 配置含 PLACEHOLDER | config | **抛错终止** | 否 | 一次列出全部未填字段路径 |
 1283| | 金额字段非整数 | C-09 / io_loaders | **BLOCK** | 否 | audit |
 1284| | 口径版本不一致 | C-07 | **BLOCK** | 否 | audit |
 1285| | 指标未签认 | C-02 | 剔除该指标，权重重归一 | 是（降 coverage） | score_card flag + 报告附录 |
 1286| | 某维度指标被清空 | C-02 | 该维度 W 置 0 并重归一；清空维度数 ≥ 2 → **BLOCK** | 视情况 | WEIGHT_REALLOCATED |
 1287| | 缺失率超 warn 阈 | C-04 | WARN，按 missing_rule 处理 | 是 | preflight findings |
 1288| | 缺失率超 block 阈 | C-04 | 该策略 NOT_ASSESSED | 否 | 台账单独计数 |
 1289| | 数据过期 | C-05 | WARN + 标注 | 是 | score_card |
 1290| | 数据质量 SUSPECT | C-06 | 剔除该指标 | 是（降 coverage） | flag |
 1291| | 评价设计卡 PARTIAL | C-08 | 证据上限压到 C | 是 | evidence_reason |
 1292| | 评价设计卡 MISSING | C-08 | 证据 D → NOT_ASSESSED | 否 | 台账单独计数 |
 1293| | C 类无解释限制 | evidence Step 5 | 降为 D → NOT_ASSESSED | 否 | evidence_reason |
 1294| | HARD 红线违反且无有效豁免 | redline | **强制 L4**，分数照算但不生效 | 是（不生效） | 红线清单 + 台账 |
 1295| | 豁免过期或范围不符 | redline | 视为无豁免，记 WAIVER_INVALID | 是 | 红线清单 |
 1296| | 目标值覆盖不足 | attainment / grading | 等级封顶 max_grade_if_no_target | 是（封顶） | capped_flag + cap_reason |
 1297| | 指标零变异（sd = 0） | normalize / diagnostics | INACTIVE，剔除并预警；造权重阶段走 AHP 回退 | 是 | entropy_diagnostic |
 1298| | 锚定集失效 | C-10 | 回退为仅当期归一化 + **显著标注秩反转风险** | 是 | 报告首屏 |
 1299| | flip_rate 超 review_max | sensitivity | 报告首屏声明「本期结果不得用于淘汰决策」+ 台账 usable_for_elimination = false | 是 | 首屏警示 |
 1300| | 三方法排序分歧 | triangulation | METHOD_DIVERGENCE，要求人工复核 | 是 | 首屏警示 |
 1301| | 熵权样本不足（组合阶段） | weights_combine | 回退纯 AHP（α=1）+ 草稿首屏显著标注 | 是（权重草稿） | ENTROPY_INSUFFICIENT_SAMPLE |
 1302| | α 可行集为空 | weights_calibrate | 抛 AlphaInfeasibleError + 输出违反矩阵 | 否（无权重草稿） | 退出码 7 |
 1303| | α* 低于 alpha_floor 且 floor 不可行 | weights_calibrate | 抛 AlphaFloorInfeasibleError（**不静默降级**） | 否 | 退出码 7 |
 1304| | CEL 字段存在但 cel.enabled = false | models / config | 字段一律不参与任何判定；报告显式写「本期末接入增量估计」，**不得静默留白** | 是 | 报告 |
 1305| | 内部不变量违反 | 各模块断言 | 抛 InvariantViolationError，退出码 5，**不产出任何结果** | 否 | audit |
 1306| 
 1307| **统一原则**：**宁可不评，不可错评**；任何降级都必须留下 reason_code 与披露位置，**禁止静默处理**。
 1308| 
 1309| 
