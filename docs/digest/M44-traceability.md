# digest M44-traceability -- 追溯矩阵：原文条款 - 风险 - 方法 - 模块 - 测试
# 消费方: ORCH
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1841-1885
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1841-1885 -->
 1841| ## 5.6 追溯矩阵：原文条款 ↔ 风险 ↔ 方法 ↔ 模块 ↔ 测试
 1842| 
 1843| | 原文条款（章节定位，D5 口径） | 风险 | 采用方法 | 模块 | 测试 |
 1844| |---|---|---|---|---|
 1845| | 分册 A 三（三）方法论：AHP、TOPSIS、熵权法、GRA | F1 | AHP（造权重）+ 熵权（**v1.1 起按 α 组合入配置** + 在线诊断）+ TOPSIS/GRA（三角验证）；主方法改为达成率 + 阈值 | weights_ahp / weights_combine / weights_calibrate / diagnostics / triangulation | T-AHP-* T-ENT-* T-CMB-* T-CAL-* T-TOP-* T-GRA-* T-TRI-* |
 1846| | 分册 A 三（三）「可研究采用 AHP 与熵权法组合确定综合权重，再通过加权综合评分形成策略得分」 | F1 F2 | **✅ 字面完整落地**：AHP × 熵权按 α 组合 → 冻结 → 加权综合评分；α 由稳定性回测标定，可审计 | weights_ahp + weights_combine + weights_calibrate | T-CMB-01~09、T-CAL-01~04、P-11 / P-14 / P-15 |
 1847| | 分册 A 三（四）指标维度：贡献度 / 效益度 / 执行度 / 风险度 / 密切度 / 体验度（原文以「等」收尾） | F6 | 指标字典 + 签认 + CV/VIF/相关诊断 + GRA 低区分度诊断；**维度配置驱动不硬编码**（D7） | models / config / diagnostics / triangulation | T-ENT-02、T-GRA-03、G-10 |
 1848| | 分册 A 三（五）1 评分细则：评分区间、异常值处理 | —— | attainment_formula 四分派 + outlier_rule + cap | attainment | G-09、T-* |
 1849| | 分册 A 三（五）2 权重配置：一级、二级指标权重分配方式 | F1 F2 | 冻结权重版本 **+ provenance 完整证据链 + 逐指标对照披露** | config / weights_* / reports | T-AHP-06、T-CMB-06、V-12、V-15 |
 1850| | 分册 A 三（五）3 标准化：不同量纲、单位、方向 | F3 F5 | 方向归一 + 三种归一化 + 锚定集参照 | normalize | G-05、P-4 |
 1851| | 分册 A 三（五）4 分值输出：加权综合得分 | F3 F4 | 双轨聚合（绝对轨主、相对轨辅）+ 三算子可切换 | aggregate | G-01、P-1 |
 1852| | 分册 A 三（六）等级设定：划分规则、更新规则 | F3 | 门槛挂 attainment_floor + 滞回 + 版本断点 + 诚实封顶 | grading | G-01、G-04、G-08、P-9 |
 1853| | 分册 A 三（七）1 四级动作 | —— | grade_rules.actions 逐字取自原文 + recommended / decided 分列 | grading / pooling / reports | G-02、V-8 |
 1854| | 分册 A 三（七）2 策略池：评价—分层—优化—淘汰；提升一二级占比 | F8 | 分池禁混排 + 一级库门禁 + 占比双报 + MIX_QUALITY_DEGRADED 防作弊 | pooling | G-02、G-14、P-6 |
 1855| | 分册 A 四（一）数据完善：指标缺什么、数据缺什么 | —— | preflight C-02 / C-04 / C-05 / C-06 / C-07 | preflight | G-09、G-10、G-11 |
 1856| | 分册 A 四（二）功能完善：后台评价模型引擎 + 前台看板 | —— | DSM 即引擎的离线参考实现；CSV 输出供看板消费 | 全部 | V-10 |
 1857| | 分册 A 五（一）验证数据准备：含业务增量 | 因果缺口 | 增量口径**首版不实现，但契约已预留**（D3）；DSM 只消费 evidence_class | evidence / models（CEL-0） | V-20、CEL-0 一致性用例 |
 1858| | 分册 A 五（三）合理性验证第 3 条：是否存在某一指标过度影响综合得分 | F7 | **LOO + OAT 扰动 + flip_rate + 稳定性标签** | sensitivity | G-06、G-07、T-SEN-02 |
 1859| | 分册 A 五（四）体系优化：调整指标定义、计算逻辑、**评价权重**和分级标准 | —— | diagnostics 的 INACTIVE / COLLINEAR 清单 + **whatif 预演 + 标定报告**直接支撑权重调整决策 | diagnostics / whatif / weights_calibrate | T-ENT-*、T-WIF-01~05 |
 1860| | 主报告第一章：有 AB 与无 AB 策略的可比性 | **F8** | 证据分级 A/B/C/D + 分池键含 evidence_class | evidence / pooling | G-02、P-6 |
 1861| | 主报告第一章：策略内容变化可能影响前后结果可比性 | F5 | VERSION_BREAK + 滞回 + 锚定集 | grading / normalize | G-08、P-4 |
 1862| | 主报告第三章：评价设计卡（对照安排、成功判定、风险约束、评价责任人、解释限制） | F8 | design_cards 逐字段落地 + C 类强制解释限制 | models / evidence / redline | G-13 |
 1863| | 主报告第三章：评价建议与执行决定区分记录 | —— | grade_ledger 的 recommended_action / decided_action 双字段 | grading / reports | V-8 |
 1864| 
 1865| ## 5.7 编号统一映射表（D1 落地件）
 1866| 
 1867| | 统一编号（以 HD §10 为准） | RPT §9 对应编号 | 修复动作 | DSM 模块 | CEL 模块 |
 1868| |---|---|---|---|---|
 1869| | **P0-1** | R-P0-5 + R-P0-6 | 权重版本化冻结；熵权处置见 **D2**（v1.1 定稿为档 2 + 四约束） | config / weights_* | — |
 1870| | **P0-2** | R-P0-3 | 红线非补偿 | redline | — |
 1871| | **P0-3** | R-P0-4 | 双轨报告，门槛挂绝对达成率 | attainment / normalize / grading | — |
 1872| | **P0-4** | R-P0-2 | 权重扰动 → 分级翻转率 → 稳定性标签 | sensitivity | CEL-5（跨期效度） |
 1873| | **P0-5** | R-P0-7 | 指标论证表：责任人 / 签认 / 相关矩阵 / VIF | diagnostics / T2 | — |
 1874| | **P0-6** | R-P1-3 | 评价设计卡字段对齐主报告 | T4 / evidence | CEL-0 / CEL-3 |
 1875| | **P0-7** | R-P0-1 | 证据强度分级 + 禁混排 + C 类不进一级库 | evidence / pooling | CEL-1 / 2 / 3 供数 |
 1876| | **P0-8** | R-P1-2（部分） | 评价周期 / 版本 / 复评触发 | grading / T1 | — |
 1877| | **P0-9** | R-P0-3（部分） | 体验度定义为约束项 | redline / T5 | — |
 1878| | **P1-1** | RPT §6 结论 | 常驻对照组 + 增量口径 | 首版范围外（契约已预留） | **CEL-1 / CEL-2** |
 1879| | **P1-2** | RPT §5 对标 | uplift 分层 | 首版范围外 | 二期评估（前置条件见 §5.8.3） |
 1880| | **P1-4** | R-P1-1 | 秩反转治理与锚定集 | normalize / T8 | — |
 1881| | **P2-1** | RPT §6 国外对标 | DID / 合成对照 / geo / switchback | 首版范围外 | **CEL-2 分支 3** |
 1882| | **P2-3** | RPT §2.3 | 元评价：等级与后续增量的秩相关 | 无对应模块 | **CEL-5** |
 1883| 
 1884| > **使用规则**：代码注释、报告脚注、追溯矩阵**只允许**出现左列编号；RPT 编号仅在交叉参考时以 R- 前缀出现。
 1885| 
