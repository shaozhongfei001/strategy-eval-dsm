# digest M21-io-loaders -- io_loaders 规格：类型强制 / 指纹 / 上期数据
# 消费方: WP-io_loaders
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 884-893
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 884-893 -->
  884| ### 3.3.5 io_loaders.py —— 输入加载与指纹
  885| 
  886| | 项 | 内容 |
  887| |---|---|
  888| | 职责 | 按 period 读取 data/<period>/ 下的 T1/T3/T4，读取 config/ 下的 T2/T5/T6/T7/T8；对每个文件计算 SHA256 与行数，产出 InputFingerprints |
  889| | 类型强制 | 金额列必须解析为 int（失败即记 C-09）；日期列必须为 ISO 格式；枚举列做 Literal 校验 |
  890| | 上期数据 | 滞回与版本断点需要上一期 grade_ledger；缺失时按 FIRST_PERIOD 处理并 WARN，**不得**默认给最低等级 |
  891| | 输出 | Inputs（8 表）+ InputFingerprints（写入 audit.json，是第二人复跑的比对基准） |
  892| | 异常 | DataLoadError（退出码 4） |
  893| 
