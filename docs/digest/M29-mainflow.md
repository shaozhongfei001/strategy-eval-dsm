# digest M29-mainflow -- 每期评分主流程九步 + 判定点与失败出口
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1312-1359
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1312-1359 -->
 1312| ### 3.15.1 每期评分主流程（含判定点与失败出口）
 1313| 
 1314|     +-----------------------------+
 1315|     | dsm preflight --period P    |
 1316|     +--------------+--------------+
 1317|                    |
 1318|           C-01~C-10 十项校验
 1319|                    |
 1320|         +----------+-----------+
 1321|         |                      |
 1322|      status=BLOCK          status=PASS/WARN
 1323|         |                      |
 1324|    写 audit_bundle        +----v---------------------+
 1325|    退出码 2               | dsm score --period P     |
 1326|    不产出 score_card      +----+---------------------+
 1327|                                |
 1328|               config.load_all()  →  PLACEHOLDER?  → 抛错，退出码 3，列出全部未填字段
 1329|                                |
 1330|               io_loaders       →  8 表 + InputFingerprints（SHA256 / 行数）
 1331|                                |
 1332|               Step 1 attainment  →  达成率矩阵 + coverage（无目标值 → null，不用均值代替）
 1333|                                |
 1334|               Step 2 normalize   →  池内标准化 + 锚定集参照（失效 → 回退 + 首屏标注）
 1335|                                |
 1336|               旁路 diagnostics   →  在线熵权 / CV / VIF / 相关（不入分，出工单）
 1337|                                |
 1338|               Step 3 evidence    →  A/B/C/D（短路判定；C 缺解释限制 → D）
 1339|                                |
 1340|               Step 4 redline     →  HARD 强制降级 / SOFT 独立扣减（不进加权）
 1341|                                |
 1342|               Step 5 aggregate   →  composite_absolute + composite_relative（只读 FROZEN 权重）
 1343|                                |
 1344|               Step 6 grading     →  基础等级 → 证据封顶 → 目标封顶 → 红线覆盖 → 滞回 → 版本断点
 1345|                                |
 1346|               Step 7 pooling     →  分池禁混排 + 一级库门禁 + 占比双报 + NOT_ASSESSED 单列
 1347|                                |
 1348|               旁路 triangulation →  TOPSIS / GRA / Spearman → AGREE or DIVERGENCE
 1349|                                |
 1350|               Step 8 sensitivity →  OAT / MC / LOO / NORM_SWAP → flip_rate + 稳定性标签
 1351|                                |
 1352|                         首屏可用性判定：
 1353|                         flip_rate > review_max 或 METHOD_DIVERGENCE
 1354|                              → usable_for_elimination = false（本期暂停淘汰）
 1355|                                |
 1356|               Step 9 audit       →  manifest + reproducibility_hash
 1357|                                |
 1358|               reports.render     →  report.md（10 段）+ 5 张表 + audit.json
 1359| 
