# digest M41-cel -- CEL 因果证据层：CEL-0 首版预留 + 二期路线
# 消费方: WP-models,WP-evidence
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1886-1924
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1886-1924 -->
 1886| ## 5.8 CEL 因果证据层：二期路线（首版只预留契约）
 1887| 
 1888| ### 5.8.1 CEL-0：首版零成本接口预留（**纳入首版范围**）
 1889| 
 1890| 只加字段与枚举，**不加计算逻辑、不加依赖、不加 CLI 子命令**：
 1891| 
 1892| | 位置 | 预留内容 | 首版取值规则 |
 1893| |---|---|---|
 1894| | T4 design_cards | incremental_value、incremental_ci_lower / upper、estimator_method、experiment_id、holdout_id、mde_ok、interpretation_limit | 全部可空；为空时 evidence.py 按现行规则判定，行为与无预留时完全一致 |
 1895| | evidence_class 枚举 | 保持 A/B/C/D；新增 evidence_source ∈ {CARD_ONLY, CEL_ESTIMATED} | 首版恒为 CARD_ONLY |
 1896| | score_card | 增量三列（点估计 / 区间 / 方法）+ value_captured 占位 | 首版全部为空，报告中**显式写「本期末接入增量估计」，不得静默留白** |
 1897| | audit.json | cel_contract_version | 首版固定为占位版本，便于二期识别契约代际 |
 1898| | eval_config | cel.enabled = false | 单开关，默认关闭；关闭时 CEL 相关字段**一律不参与任何判定**；若非空则抛 CelDisabledDataPresentError（RK-15） |
 1899| 
 1900| **守护用例（V-20）**：cel.enabled = false 时，逐字段比对首版输出与关闭预留字段的基线，**必须完全一致**（G-01~G-15 全过）。这条用例是「范围不变、契约先行」的守护者。
 1901| 
 1902| **为什么必须现在做**：models.py 采用 frozen + extra=forbid。二期才加「增量值 / 置信区间 / 估计方法 / 留出组 ID」属于**破坏性契约变更**：所有 fixtures、golden 期望值、报告模板、审计哈希输入都要重做。**首版预留的成本接近零，二期补的成本高一个量级。**
 1903| 
 1904| ### 5.8.2 二期模块规格摘要（CEL-1 ~ CEL-5）
 1905| 
 1906| | 模块 | 职责 | 关键规则 | 降级 |
 1907| |---|---|---|---|
 1908| | **CEL-1** experiment_registry.py | 登记每条策略的对照安排，产出可供估计的分组清单；把「常驻留出组」作为跨策略公共基准 | ①每个目标细分必须预留排除组；②留出组在同一观察期内**不得**接收任何同类触达，否则记 CONTAMINATED；③不同实验的 uplift **不可简单相加**，存在并行重叠时标记 OVERLAP 并以常驻留出组口径为准 | 无分组快照 / 分组被污染 → status = UNAVAILABLE，证据等级不得评为 A/B |
 1909| | **CEL-2** incremental_estimator.py | 按可用证据选择估计分支（RCT/AB、常驻留出组、准实验 DID/合成对照/geo/switchback、无对照），输出点估计、区间与 MDE 判定；**不自己造对照组** | ①任何分支都**不得**用观测转化率冒充增量；②sample_size_ok 未达门槛时点估计可给但 mde_ok = false，且不得据此升级证据等级；③数值口径一律走 numeric.py；④无对照分支输出 incremental_value = null、证据 C、interpretation_limit 必填否则降 D | 估计失败**不抛异常中断主流程**：写 reason_code + 空值 + 降级证据 + audit 留痕（R5） |
 1910| | **CEL-3** evidence_bridge.py | 把 CEL-2 的结果桥接为 evidence.py 认识的证据等级标签 | 单向：CEL → T4 → evidence.py；evidence.py **不得**反向调用 CEL；A 类判定保守，关键词清单外**不认 A**，禁止用模型猜测 | 桥接失败 → 保持 CARD_ONLY 判定 |
 1911| | **CEL-4** value_capture.py（可选） | 把增量按行方认可的单价口径折算为经济价值，用于资源倾斜的**披露**，不用于分级门槛 | ①单价口径与价值边界须版本化签认，**禁止在代码里写死金额**；②同一增量不得在多个策略上重复计入（组合口径去重）；③借鉴同业「把增量纳入制度化价值捕获与常态披露」的**思路**，但**不引用其金额作为本模型参数** | 单价未签认 → 只输出物理增量与「未货币化」标记，**不得输出金额** |
 1912| | **CEL-5** meta_evaluation.py | 定期回测「被评为一级 / 进入优质策略库的策略」在后续期间的真实增量表现，检验体系的**预测效度** | ①只用后续期数据，**严禁用当期分数自证**；②结论是「对体系的检验」，不自动改写既有等级；③触发 META_VALIDITY_WARNING 时要求人工复核指标字典与权重版本，而不是自动调参 | 后续期数据不足 → 不出结论并标注窗口不足 |
 1913| 
 1914| ### 5.8.3 二期数据契约增量（不改 8 表结构，只做可空扩展）
 1915| 
 1916| | 编号 | 表 | 变更性质 | 内容 |
 1917| |---|---|---|---|
 1918| | T4（扩展） | design_cards | 可空字段扩展 | §5.8.1 的 7 个字段（首版即预留） |
 1919| | T9（新增，二期） | experiment_registry | CEL-1 产物 | experiment_id 主键；holdout_id / assignment_unit / randomized / status / exclusion_rules |
 1920| | T10（新增，二期） | incremental_estimates | CEL-2 产物 | strategy_id + version_id + period + estimator_method 联合主键；点估计 / 区间 / MDE / reason_codes |
 1921| | T11（新增，可选） | value_capture | CEL-4 产物 | 价值口径版本号必填；单价未签认时金额字段为 null |
 1922| 
 1923| **契约不变量**：①首版 T9–T11 不加载、不参与校验；②任何新增字段都不得改变现有 golden 用例的期望值；③字段命名与枚举须登记到 reason_codes.py 单一事实源；④所有金额走 numeric.py 精确口径。
 1924| 
