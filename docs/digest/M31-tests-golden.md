# digest M31-tests-golden -- 三层测试结构 + G-01 ~ G-15
# 消费方: WP-golden
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1387-1420
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1387-1420 -->
 1387| ### 3.16.1 三层测试结构
 1388| 
 1389| | 层 | 目的 | 数量 | 位置 |
 1390| |---|---|---|---|
 1391| | 单元测试 | 每模块公式与边界 | 约 60–80 | tests/test_*.py |
 1392| | Golden 用例 | 端到端机制验证（**一条用例只验一个机制**） | G-01 ~ G-15 | tests/test_golden.py + fixtures/golden/ |
 1393| | 属性测试 | 不变量（hypothesis 随机输入 500 例/条） | P-1 ~ P-15 | tests/test_properties.py |
 1394| | 方法学专项 | 直接覆盖 AHP / 熵权 / TOPSIS / GRA / 组合 / 标定 / whatif | T-AHP / T-ENT / T-TOP / T-GRA / T-TRI / T-SEN / T-CMB / T-CAL / T-WIF | tests/test_methods.py |
 1395| | 架构测试 | INV-1 / INV-2 / INV-3 与分层依赖 | —— | tests/test_architecture.py |
 1396| 
 1397| **模块纯函数约束**：所有模块必须是**无副作用纯函数**（不读写全局状态、不依赖当前时间；时间由 config.period 与 run_at 参数注入）。这是 R2 可复现的前提，也是属性测试可行的前提。
 1398| 
 1399| ### 3.16.2 Golden 用例 G-01 ~ G-15
 1400| 
 1401| | # | 场景 | 输入要点 | 期望输出 | 验证的机制 |
 1402| |---|---|---|---|---|
 1403| | G-01 | A 类证据 + 全指标达标 + 无红线 | control_arrangement = RANDOMIZED，eval_method = AB_TEST，含显著性判定；composite_absolute ≥ floor(L1) | grade = L1；evidence_class = A；eligible_for_L1_library = true；reason_codes 为空 | 正常主路径 |
 1404| | **G-02** | **C 类高分策略** | control_arrangement = NONE，eval_method = OBSERVATIONAL_ONLY；composite_absolute 高于 floor(L1) | grade = L2（被证据门禁降级）；eligible_for_L1_library = **false**；rank_in_pool 仅在 (biz_domain, C) 池内；interpretation_limit 非空 | **P0-7 证据门禁 + 禁混排（治 F8）** |
 1405| | **G-03** | **贡献极高但投诉率超红线** | CONTRIB 维度 attainment = 1.9（接近 cap），COMPLAINT_RATE 超 HARD 阈值 | grade = **L4**（forced）；redline_pass = false；composite_absolute **仍输出但不生效** | **P0-2 非补偿（最关键用例，治 F4）** |
 1406| | G-04 | 目标值缺失导致绝对轨覆盖不足 | 60% 指标 target_value 为空，低于 min_coverage | grade 封顶 L3；capped_flag = true；cap_reason = GRADE_CAPPED_NO_TARGET | R5 诚实降级（治 F3） |
 1407| | G-05 | **新增极端策略** | 基线运行后追加一个 attainment 极高的新策略（不入锚定集），重跑 | 存量全部策略的 norm、composite、grade **完全不变** | **P1-4 锚定集治秩反转（F5）** |
 1408| | G-06 | 权重 +20% 扰动 | 对 CONTRIB 维度 W_d × 1.2，其余重归一 | flip_rate 计算正确；至少一个 NEAR_BOUNDARY 策略翻转为 L3；stability_label 正确 | **P0-4 敏感性（F7）** |
 1409| | G-07 | LOO 单指标过度影响 | 构造一个权重占比过大的指标 | loo_impact 最大者为该指标；报告输出「存在单一指标过度影响」警示 | 原文五（三）第 3 条 |
 1410| | G-08 | 策略版本变更 | 同 strategy_id，version_id 变化，version_change_note 非空 | VERSION_BREAK 标注；跨版本趋势比较被抑制；promotion_streak 计数重置 | P0-8 版本断点 |
 1411| | G-09 | 缺失指标的四种分支 | 分别构造 missing_rule = ZERO / SKIP / IMPUTE_MEDIAN / BLOCK | 四种分支结果各不相同且与规则一致；BLOCK 时该策略不产出分数 | Step 1 缺失处理 |
 1412| | G-10 | 未签认指标 | 某指标 signoff_status = PENDING | 该指标被剔除；coverage 下降；reason = METRIC_NOT_SIGNED；若该维度被清空 → preflight BLOCK | P0-5 签认门禁 |
 1413| | G-11 | 权重版本过期 / 金额非整数 | (a) period 超出 effective_to；(b) MONEY_MINOR 字段传入非整数 | (a) preflight = BLOCK，code = STALE；(b) preflight = BLOCK，code = MONEY_NON_INTEGER；**均不产出 score_card** | C-01 / C-09 |
 1414| | **G-12** | **第二人复跑** | 同 manifest 连续运行两次 | 两次 reproducibility_hash **精确相等**；金额与整数字段精确相等；比率字段差值 ≤ 1e-12 | **R2 可复现（验收硬门槛）** |
 1415| | G-13 | 评价设计卡 PARTIAL | 缺对照安排或成功判定 | 证据最高只能 C；evidence_reason 记录降级原因 | C-08 / D4 |
 1416| | G-14 | 占比双报中的质量退化 | 构造一级库中 C 类占比上升的场景 | 报告出现 MIX_QUALITY_DEGRADED 警示；池内占比与合并占比分列 | P0-7 占比双报 |
 1417| | G-15 | 豁免无审批留痕 | waiver_allowed = true 但缺 approval_id | 视为未豁免，HARD 红线照常强制降级，记 WAIVER_INVALID | 红线豁免纪律 |
 1418| 
 1419| **golden 期望值纪律**：期望值由**首次通过人工评审的运行结果**固化；之后任何变更都必须显式更新期望值并说明原因（防止 golden 沦为「跟随实现」）。
 1420| 
