# digest M35-milestones -- 里程碑 M1~M4b + 开工顺序 8 步
# 消费方: ORCH
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1464-1489
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1464-1489 -->
 1464| ## 3.17 分期实施与开工顺序
 1465| 
 1466| ### 3.17.1 里程碑
 1467| 
 1468| | 里程碑 | 模块 | 测试 | 工期 | 交付判据 |
 1469| |---|---|---|---|---|
 1470| | **M1 主干** | numeric / reason_codes / models（含 CEL-0 预留）/ config / io_loaders / preflight / attainment / normalize / aggregate / grading / cli(score) | G-01 G-04 G-08 G-09 G-10 G-11；T-SEN-01 部分；CEL-0 一致性用例 | 1.5–2 天 | 双轨评分与分级跑通；PLACEHOLDER 拦截生效 |
 1471| | **M2 门禁（最高价值）** | evidence / redline / pooling / cli 完善 / reports 首屏警示区 | **G-02 G-03** G-13 G-15；P-2 P-6 | 1 天 | C 类禁入一级库；红线非补偿恒 L4；占比双报与证据结构披露 |
 1472| | **M3 稳健与审计** | sensitivity（OAT / LOO / NORM_SWAP）/ audit / reports 完整版 | G-05 G-06 G-07 G-12 G-14；P-3 P-4 | 1–1.5 天 | flip_rate 与稳定性标签产出；第二人复跑哈希相等 |
 1473| | **M4a 方法层** | weights_ahp / diagnostics / triangulation / aggregate 的 GEOMETRIC 与 NON_COMPENSATORY / sensitivity 的 MC | T-AHP-01~06、T-ENT-01~03、T-TOP-01~03、T-GRA-01~03、T-TRI-01、T-SEN-02/03；P-1~P-10 全覆盖 | 1.5–2 天 | AHP 造权重可用（CR 检验 + 只出 DRAFT）；三路诊断与三角验证齐备且均不入分 |
 1474| | **M4b 权重构造链（v1.1）** | weights_combine / weights_calibrate / whatif / CLI 三子命令 | T-CMB-01~09、T-CAL-01~04、T-WIF-01~05、P-11~P-15 | 1.5–2 天 | 档 2 全链可用；INV-1/2/3 架构测试通过 |
 1475| | **M5（另议）** | CEL-1~CEL-5：实验登记 / 增量估计 / 证据桥接 / 价值货币化 / 元评价 | —— | 另议 | 需行方具备实验分流或留出组能力（见 §5.8） |
 1476| 
 1477| > M1–M3 = **3.5–4.5 天**即可交付可辩护、可复现、可审计的评分主干；M4a + M4b 再加 **3–4 天**把 AHP / 熵权 / TOPSIS / GRA 四种方法全部落地到正确位置并打通权重构造链。**合计 6.5–8.5 天**。
 1478| 
 1479| ### 3.17.2 开工顺序（8 步，照此执行）
 1480| 
 1481| 1. **骨架**：requirements.txt / pyproject.toml / dsm/__init__.py / reason_codes.py / numeric.py（+ 单测）
 1482| 2. **契约**：models.py（8 输入 + 5 输出 + CEL-0 可空字段，frozen + extra=forbid）/ config.py（PLACEHOLDER 拦截 + 语义校验 + whatif_run_id 强制）（+ V-5 负向测试）
 1483| 3. **加载与校验**：io_loaders.py（指纹）/ preflight.py（C-01~C-10）（+ G-10 G-11）
 1484| 4. **计算主干**：attainment.py / normalize.py / aggregate.py / grading.py（+ G-01 G-04 G-08 G-09）
 1485| 5. **门禁三件套（最高价值）**：evidence.py / redline.py / pooling.py（+ **G-02 G-03** G-13 G-15 + P-2 P-6）
 1486| 6. **稳健与审计**：sensitivity.py / audit.py / reports.py（+ G-05 G-06 G-07 G-12 G-14 + P-3 P-4）
 1487| 7. **方法层**：weights_ahp.py / diagnostics.py / triangulation.py（+ T-AHP-* T-ENT-* T-TOP-* T-GRA-* T-TRI-*）
 1488| 8. **权重构造链与收尾**：weights_combine.py / weights_calibrate.py / whatif.py / fixtures_gen.py / cli.py 八子命令 / 架构测试（INV-1/2/3）/ 属性测试全覆盖 / README（含复现步骤与第二人复跑指引）
 1489| 
