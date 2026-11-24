# docs/digest/INDEX.md -- SDD 摘录缓存索引（批量预产，ORCH v3.0 W0）

> 来源文档 sha256[:12] `708679e9a83d` / 2003 行。摘录逐字、带原文行号。
> **lane agent 只读本索引指向的 digest，禁止读 SDD 原文、禁止通读 ORCH。**

| digest | 主题 | 消费方 | SDD 行区间 | 行 | B | sha256[:12] |
|---|---|---|---|---|---|---|
| `M00-architecture.md` | 分层 / 依赖方向 / INV-1~3 / 数据流 | ALL | 206-241, 244-305 | 108 | 7852 | `87460dcaebd3` |
| `M01-method-matrix.md` | 四层作用位 + 方法定位矩阵 M-A~M-K（谁入分） | ALL | 408-438 | 39 | 4655 | `b596feb02d7f` |
| `M02-attainment.md` | 达成率四公式 + 模块规格 + 边界 | WP-attainment | 441-461, 923-934 | 43 | 2765 | `93e53de9d723` |
| `M03-aggregate.md` | 加权线性和 + 双轨聚合 + 权重重归一 | WP-aggregate | 462-477, 947-957 | 37 | 2565 | `c4a839ead64e` |
| `M04-redline.md` | 红线非补偿 + HARD/SOFT + 豁免 | WP-redline | 478-489, 984-995 | 34 | 2611 | `b8f3f304350b` |
| `M05-grading.md` | 分级六步 + 滞回 + 版本断点 | WP-grading | 490-500, 958-969 | 33 | 2424 | `4df996d72e0d` |
| `M06-ahp.md` | AHP：几何平均 / 特征向量 / CR / 只出 DRAFT | WP-weights_ahp | 501-523 | 31 | 2120 | `dbf0a78b3ffe` |
| `M07-entropy.md` | 熵权法：双重身份与隔离 / 平移消零 | WP-weights_combine,WP-diagnostics | 524-555 | 40 | 2839 | `a6db37f83463` |
| `M08-weights-combine.md` | 档 2 组合权重算法（8 步 + 四约束 + 回退不稀释） | WP-weights_combine | 556-603 | 56 | 4102 | `71ecf040377a` |
| `M09-alpha-calibrate.md` | alpha 标定：字典序可行集 / 四项稳定性指标 / 非单调 | WP-weights_calibrate | 604-639 | 44 | 4379 | `01bc5c7a06c3` |
| `M10-whatif.md` | 权重变更影响预演 / 归因分解 / 只读 INV-2 | WP-whatif | 640-683 | 52 | 3673 | `34329aec1aaa` |
| `M11-diagnostics.md` | 旁路诊断：在线熵权 / CV / VIF / 相关矩阵 | WP-diagnostics | 684-697, 1033-1043 | 35 | 2744 | `2363768ac72c` |
| `M12-triangulation.md` | TOPSIS / GRA / 三个 Spearman / 否决权 / 可关 | WP-triangulation | 698-741, 1022-1032 | 65 | 4739 | `cafba3a3737e` |
| `M13-sensitivity.md` | OAT / MC / LOO / NORM_SWAP / flip_rate / 稳定性标签 | WP-sensitivity | 742-752, 1010-1021 | 33 | 2781 | `93951061f356` |
| `M14-blindspots.md` | 方法盲区对照表 + 明确不实现的方法 | ALL | 753-781 | 37 | 3785 | `a9bfcc03b958` |
| `M15-modules-table.md` | 模块清单总表（23 模块 + 守护测试编号） | ALL | 792-838 | 55 | 4750 | `6286c98c4894` |
| `M16-numeric-reasoncodes.md` | numeric 关键函数与规则 + reason_code 单一事实源 | ALL | 840-859 | 28 | 2394 | `9221b86fa090` |
| `M17-models-spec.md` | models.py 规格（frozen / extra=forbid / CEL-0） | WP-models | 860-872 | 21 | 1629 | `baccf55f819d` |
| `M18-contract-inputs.md` | 输入 8 表总览与逐表关键字段 | ALL | 1093-1215 | 131 | 9233 | `7faf215c50c1` |
| `M19-contract-outputs.md` | 输出 5 表 + WeightProvenance 四段 | ALL | 1216-1245 | 38 | 3101 | `81cc6ee8b1c8` |
| `M20-config.md` | config.py 规格 + 配置体系 + PLACEHOLDER 纪律 | WP-config | 873-883, 1246-1260 | 36 | 3303 | `a5a138632315` |
| `M21-io-loaders.md` | io_loaders 规格：类型强制 / 指纹 / 上期数据 | WP-io_loaders | 884-893 | 18 | 1116 | `01f1a7883423` |
| `M22-preflight.md` | C-01 ~ C-10 前置校验 | WP-preflight | 896-920 | 33 | 2856 | `28c7717bdfbd` |
| `M23-evidence.md` | 证据强度五步短路 / GATE_ONLY / A 类保守性 | WP-evidence | 972-983 | 20 | 1786 | `edddf6f23f79` |
| `M24-pooling.md` | 分池禁混排 / 一级库门禁 / 占比双报 | WP-pooling | 996-1007 | 20 | 1448 | `342f8e43d857` |
| `M25-audit.md` | audit manifest / 规范化序列化五规则 / 复跑步骤 | WP-audit | 1046-1056, 1261-1275, 1636-1641 | 44 | 3674 | `6dc9b72dcc8c` |
| `M26-reports.md` | report.md 十段 / score_card 各段含义 / grade_ledger 设计 | WP-reports | 1057-1065, 1608-1635 | 47 | 4610 | `aafd88a20d75` |
| `M27-cli.md` | cli 八子命令与退出码 + 日常运行三步 | WP-cli | 1076-1092, 1519-1557 | 66 | 4677 | `e4afe7d01869` |
| `M28-downgrade-matrix.md` | 错误处理与降级矩阵（V-14 逐条断言用） | ALL | 1276-1309 | 42 | 3818 | `0f17fd588ee1` |
| `M29-mainflow.md` | 每期评分主流程九步 + 判定点与失败出口 | ALL | 1312-1359 | 56 | 3331 | `890a48c940ab` |
| `M30-annual-flow.md` | 年度权重构造五步（含人工签认断点） | WP-weights_* | 1360-1384 | 33 | 2356 | `8d0955c472fa` |
| `M31-tests-golden.md` | 三层测试结构 + G-01 ~ G-15 | WP-golden | 1387-1420 | 42 | 5191 | `32a08b9906a5` |
| `M32-tests-properties.md` | P-1 ~ P-15 属性不变量 | WP-properties | 1421-1440 | 28 | 2551 | `98c0d0b95208` |
| `M33-tests-methods.md` | 方法学专项 T-AHP/ENT/TOP/GRA/TRI/SEN/CMB/CAL/WIF | WP-methods | 1441-1454 | 22 | 2276 | `6627e0ecf4b2` |
| `M34-fixtures.md` | 合成 fixtures 生成规则（12 策略 / 4 域 / A3B3C4D2 / 7 构造） | WP-fixtures_gen | 1455-1463 | 17 | 1205 | `db542fe4f6e7` |
| `M35-milestones.md` | 里程碑 M1~M4b + 开工顺序 8 步 | ORCH | 1464-1489 | 34 | 3577 | `d13fcd0f988b` |
| `M36-acceptance.md` | V-1 ~ V-20 验收判据 | WP-acceptance | 1490-1518 | 37 | 2936 | `9161f8f7edf2` |
| `M37-examples.md` | 五个端到端示例 E1~E5（业务含义） | WP-golden,WP-reports | 1642-1680 | 47 | 5027 | `aeb46e701e6b` |
| `M38-k-params.md` | K-01 ~ K-20 开放参数（须行方签认，模型侧不得拟定） | ALL | 1734-1760 | 35 | 4335 | `cec972317960` |
| `M39-risks-gates.md` | RK-1~RK-15 风险 + G0~G8 冻结门禁 | ORCH | 1761-1798 | 46 | 5795 | `531b3f9c31a8` |
| `M40-evidence-discipline.md` | 证据边界与引用纪律 + 数值口径纪律 + D6 争议来源 | ALL | 1817-1840 | 32 | 2564 | `bd3b49bb6260` |
| `M41-cel.md` | CEL 因果证据层：CEL-0 首版预留 + 二期路线 | WP-models,WP-evidence | 1886-1924 | 47 | 5935 | `baf89d85a586` |
| `M42-l0-tools.md` | L0a / L0b 离线工具层规格 | WP-weights_*,WP-whatif | 1066-1075 | 18 | 2083 | `a0d3ad8b8a78` |
| `M43-normalize.md` | 相对标准化轨：三方法 / 锚定集 / 池内归一 | WP-normalize | 935-946, 233-241 | 31 | 2090 | `f5e49239697f` |
| `M44-traceability.md` | 追溯矩阵：原文条款 - 风险 - 方法 - 模块 - 测试 | ORCH | 1841-1885 | 53 | 6751 | `bfea0cf7c6d1` |

**合计 45 份 / 1864 行 / 160432 B**

## 旧 digest（前一轮 S1 契约层取证，保留供追溯）

`S1-T01.md` `S1-T01b.md` `S1-T01c.md` `S1-T01d.md` `S1-T01e.md` `S1-T03.md` `S1-T04.md` `S1-T05.md` `S1-T06.md`
