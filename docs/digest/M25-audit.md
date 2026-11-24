# digest M25-audit -- audit manifest / 规范化序列化五规则 / 复跑步骤
# 消费方: WP-audit
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1046-1056, 1261-1275, 1636-1641
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1046-1056 -->
 1046| ### 3.8.1 audit.py —— Step 9 审计与复现（R1 / R2）
 1047| 
 1048| | 项 | 内容 |
 1049| |---|---|
 1050| | 签名 | def build_manifest(inputs_fp, config, run_ctx, outputs_fp) -> AuditBundle |
 1051| | AuditBundle 内容 | run_id、run_at（**由 CLI 注入**）、period、dsm_version、design_version、cel_contract_version、weight_version_id、config 全量快照的 SHA256、8 张输入表的 SHA256 与行数、输出文件清单与 SHA256、启用的敏感性方案与 seed、preflight findings 全量、降级动作全量、exit_code、reproducibility_hash |
 1052| | reproducibility_hash | 对**规范化序列化后的关键结果**（score_card 的核心列 + grade_ledger 的等级列 + 权重版本 id）求 SHA256 |
 1053| | 规范化序列化五规则 | ①Decimal 统一 q12 后转字符串；②浮点一律先转 Decimal；③字典与集合遍历前显式按 key 排序；④列表顺序按业务主键排序（不按插入序）；⑤None 与空字符串严格区分（写作 null 与 empty） |
 1054| | 失败也要写 | **任何命令失败都必须写 audit_bundle**（记录为什么没跑出结果），这对审计至关重要 |
 1055| | 守护 | G-12（同输入两次运行 hash 相同）、V-11（新增输出字段未同步序列化器则测试失败） |
 1056| 

<!-- SDD 1261-1275 -->
 1261| ## 3.13 数值精度与可复现策略
 1262| 
 1263| | 数据类型 | 存储 / 运算类型 | 比较方式 | 说明 |
 1264| |---|---|---|---|
 1265| | 金额 | int（最小货币单位，字段名后缀 _minor） | **精确相等** | 全链路不经 float；展示层才转 Decimal 并指定 quantize |
 1266| | 计数 | int | 精确相等 | —— |
 1267| | 比率 / 达成率 / 权重 / 均值 | Decimal（字符串构造） | **1e-12 容差** | 除法统一走 safe_div，显式指定 on_zero |
 1268| | 熵权计算中的 ln | Decimal.ln() 或 float 后转 Decimal | 1e-12 | 允许 float 中间态，但**输出前 quantize 到 1e-12** |
 1269| | TOPSIS 的 sqrt | Decimal.sqrt() | 1e-12 | 不入分，但须可复现 |
 1270| | Monte Carlo | numpy + **固定 seed** | —— | seed 写入 audit_bundle；未设 seed 则拒绝运行 MC |
 1271| | 时间 | 由 CLI 注入 run_at | —— | **禁止**在计算层调用系统时钟（否则不可复现） |
 1272| | 字典 / 集合遍历 | 全部排序后遍历 | —— | 序列化前显式排序，保证跨版本一致 |
 1273| 
 1274| **reproducibility_hash 的稳定性保障**：见 §3.8.1 规范化序列化五规则。任何新增输出字段都必须同步更新序列化器，并由 G-12 与 V-11 守护。
 1275| 

<!-- SDD 1636-1641 -->
 1636| ### 4.6.3 audit.json 怎么用于第二人复跑
 1637| 
 1638| audit.json 含：输入 8 表的 SHA256 与行数、配置全量快照哈希、权重版本 id、启用的敏感性方案与 seed、preflight findings 全量、降级动作全量、输出文件清单与哈希、reproducibility_hash。
 1639| 
 1640| **复跑步骤**：第二人取同一批输入文件与配置目录 → 校验 SHA256 与 audit.json 记录一致 → 用同一 --run-at 与 --seed 执行 dsm score → 比对 reproducibility_hash（**必须精确相等**）→ 金额与整数字段精确相等、比率字段差值 ≤ 1e-12（V-3 / G-12）。
 1641| 
