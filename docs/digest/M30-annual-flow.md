# digest M30-annual-flow -- 年度权重构造五步（含人工签认断点）
# 消费方: WP-weights_*
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 1360-1384
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 1360-1384 -->
 1360| ### 3.15.2 年度权重构造流程（五步，含人工签认断点）
 1361| 
 1362|     1) dsm ahp build      专家两两比较 → 权重 + CR 检验（CR ≥ 0.1 拒绝，退出码 6）
 1363|                           产出 status = DRAFT 的 AHP 结果
 1364|     2) dsm calibrate      标定窗口（默认过去 4 期）→ 五个稳定性指标 × α 网格
 1365|                           → α* = 满足全部约束的最小 α（且 ≥ alpha_floor）
 1366|                           产出 CalibrationReport（写入 provenance.alpha_basis）
 1367|     3) dsm combine build  档 2 组合 + INACTIVE 回退 + 维度内归一 + H-1~H-5 校验
 1368|                           产出 config/weights_WV-DRAFT.yaml（status 只能是 DRAFT）
 1369|     4) dsm whatif         用候选权重重跑某个历史期 → 谁升谁降 / 占比变化 / 维度归因
 1370|                           redline_delta 非空 → 判为配置不一致，建议拒绝签认
 1371|     5) 人工签认（工具无权执行）
 1372|                           编辑 weights_WV-<新版本>.yaml：status DRAFT → FROZEN
 1373|                           填 approved_by / approved_date / whatif_run_id
 1374|                           缺 whatif_run_id 而写 FROZEN → 下次 config 加载直接失败
 1375| 
 1376| ### 3.15.3 指标字典治理闭环（每期旁路 → 下期生效）
 1377| 
 1378|     diagnostics 输出 entropy_diagnostic.csv
 1379|         → 逐指标 status（OK / LOW_VARIATION / INACTIVE / COLLINEAR）+ suggested_action + owner
 1380|         → 指标负责人处置：REDEFINE（改口径）/ MERGE_OR_DROP（合并或退役）/ RETIRE_OR_REDLINE（改红线）
 1381|         → 评价管理委员会签认字典变更（dict_version 递增）
 1382|         → 下一期 preflight C-07 校验口径版本一致 → 新字典生效
 1383|         → 若涉及权重结构变化 → 触发 §3.15.2 的 whatif 预演（不等年度周期）
 1384| 
