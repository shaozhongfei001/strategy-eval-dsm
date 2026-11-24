# digest M15-modules-table -- 模块清单总表（23 模块 + 守护测试编号）
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 792-838
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 792-838 -->
  792| ## 3.1 技术选型与依赖
  793| 
  794| | 项 | 选择 | 理由 |
  795| |---|---|---|
  796| | 语言 | Python 3.11+ | 类型注解完备（typing.Literal / Self）、Decimal 原生、生态成熟；若行方为 Java 栈，**本文档的契约与规格不变，仅替换执行层** |
  797| | 数据契约 | pydantic v2 | frozen=True + extra=forbid 可在类型层强制不可变与「未声明字段即报错」，是 CEL-0 契约预留的前提 |
  798| | 数值 | decimal.Decimal（字符串构造） + int | R6：金额全链路不经 float；比率 1e-12 容差 |
  799| | 数据 IO | pandas（CSV / Parquet） | 只用于装载与向量化辅助，**不用于比较判定**（比较一律走 numeric.py） |
  800| | 数值计算 | numpy（仅 Monte Carlo） | MC 必须固定 seed 并写入 audit_bundle |
  801| | 配置 | PyYAML（治理配置） + CSV（字典与事实） | 治理配置需人工签认，YAML 便于加注释与 approved_by 字段 |
  802| | CLI | typer | 8 个子命令、退出码可控、自动生成 --help |
  803| | 测试 | pytest + hypothesis | 三层测试结构（单元 / golden / 属性） |
  804| | 架构守护 | import-linter（或 AST 扫描测试） | INV-1 与「L3 不得引用 L4」的机器守护 |
  805| | 打包 | pyproject.toml + 可执行入口 dsm | 离线安装，断网可跑（V-10） |
  806| 
  807| **明确不引入**：数据库、ORM、Web 框架、调度器、消息队列、任何 ML 训练库、任何联网校验。
  808| 
  809| ## 3.2 模块清单总表（23 个模块）
  810| 
  811| | 层 | 模块 | 职责（一句话） | 入分？ | 关键守护测试 |
  812| |---|---|---|---|---|
  813| | L1 | numeric.py | 金额整数运算与 1e-12 容差，**全系统唯一数值口径实现点** | — | T-NUM-* |
  814| | L1 | reason_codes.py | reason_code 单一事实源，禁止散落字面量 | — | P-8 |
  815| | L1 | models.py | pydantic v2 frozen 数据契约，extra=forbid | — | V-5、CEL-0 一致性用例 |
  816| | L1 | config.py | 配置加载 + **PLACEHOLDER 拦截**（未签认参数一律拒绝出分） | — | P-10、V-5 |
  817| | L1 | io_loaders.py | CSV / Parquet 读取 + 输入指纹（SHA256 / 行数） | — | G-12 |
  818| | L2 | preflight.py | C-01~C-10 前置校验，BLOCK 时只写审计包并退出码 2 | — | G-10、G-11 |
  819| | L3 | attainment.py | 绝对达成率轨，**分级门槛的唯一依据** | **是** | G-01、G-04 |
  820| | L3 | normalize.py | 相对标准化轨（含锚定集），只用于排名不用于门槛 | 辅轨 | G-05、P-4 |
  821| | L3 | aggregate.py | 双轨聚合（加权线性和为默认算子） | **是** | G-01、T-CMB-06 |
  822| | L3 | grading.py | 四级分级 + 滞回 + 版本断点 | **是** | G-04、G-08 |
  823| | L4 | evidence.py | A/B/C/D 证据强度分级，默认 GATE_ONLY（不乘入分数） | 门禁 | **G-02** |
  824| | L4 | redline.py | HARD / SOFT 红线旁路否决，**红线不参与加权** | **是（旁路）** | **G-03**、P-2 |
  825| | L4 | pooling.py | 分池禁混排 + 一级库门禁 + 占比双报 | 门禁 | G-02、P-6 |
  826| | L5 | sensitivity.py | OAT / MC / LOO / 归一化互换 → flip_rate 与稳定性标签 | 否决权 | G-05、G-06 |
  827| | L5 | triangulation.py | TOPSIS / GRA 三角验证（不入分，但可否决淘汰动作） | 否决权 | T-TOP-*、T-GRA-*、T-TRI-* |
  828| | L5 | diagnostics.py | 在线熵权 / CV / VIF / 相关矩阵，仅体检 | 否 | T-ENT-*、G-07 |
  829| | L6 | audit.py | manifest / 指纹 / reproducibility_hash | — | G-12、V-11 |
  830| | L7 | reports.py | 评分卡、等级台账、稳健性与诊断报告、审计包 | — | G-14 |
  831| | L0a | weights_ahp.py | AHP 两两比较 → 权重 + CR 一致性检验（离线造权重） | 入配置 | T-AHP-01~06 |
  832| | L0a | weights_combine.py | 档 2：AHP × 熵权组合权重（v1.1 新增） | 入配置 | T-CMB-01~06 |
  833| | L0a | fixtures_gen.py | 合成数据与 golden 期望值生成（**不使用任何真实客户数据**） | — | G-* 全套 |
  834| | L0b | weights_calibrate.py | α 稳定性回测标定（v1.1 新增） | 入配置 | T-CAL-01~04 |
  835| | L0b | whatif.py | 权重变更影响预演（v1.1 新增） | 决策工具 | T-WIF-01~03 |
  836| | — | cli.py | 命令行入口，8 个子命令 | — | V-10 |
  837| 
  838| ## 3.3 L1 契约层逐模块
