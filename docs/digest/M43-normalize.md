# digest M43-normalize -- 相对标准化轨：三方法 / 锚定集 / 池内归一
# 消费方: WP-normalize
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 935-946, 233-241
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 935-946 -->
  935| ### 3.5.2 normalize.py —— Step 2 相对标准化轨（M-H，含锚定集）
  936| 
  937| | 项 | 内容 |
  938| |---|---|
  939| | 签名 | def compute(facts, metric_dict, anchor_set: AnchorSetDoc, config) -> NormalizedFrame |
  940| | 支持方法 | min_max / z_score / rank_percentile（配置切换；归一化互换敏感性会全部跑一遍） |
  941| | 锚定集 | min_max 的 min/max 与 z_score 的 mean/sd **优先取自 anchor_set**；锚定集失效 → 回退当期池内统计 + 标注 RANK_REVERSAL_RISK |
  942| | 分池归一 | 标准化在**池内**进行（biz_domain × evidence_class），禁止跨池归一（由 P-6 与 G-02 禁混排用例共同守护） |
  943| | 边界 | 零变异指标（sd = 0）→ INACTIVE，剔除并预警；池内样本数 < min_pool_size → WARN + 标注 SMALL_POOL |
  944| | reason_code | INACTIVE_METRIC、RANK_REVERSAL_RISK、SMALL_POOL、ANCHOR_SET_STALE |
  945| | 关键约束 | 输出**只用于排名与相对轨综合分**，不得进入等级门槛判定 |
  946| 

<!-- SDD 233-241 -->
  233| ### 1.5.4 秩反转治理（F5）
  234| 
  235| 相对轨的标准化若只用「当期参评策略」作分母，则**新增或退出策略会改变存量策略的相对位置**（秩反转）。治理手段：
  236| 
  237| - 固定 anchor_set（锚定基准策略集），标准化时以锚定集为参考尺；
  238| - anchor_set.yaml **必须写 rationale**；锚定集变更须走与权重同级的签认与版本流程（RK-8）；
  239| - 锚定集失效（C-10 检出）→ 回退为仅当期归一化，并在**报告首屏显著标注秩反转风险**；
  240| - 发生淘汰后，报告须披露受影响策略清单。
  241| 
