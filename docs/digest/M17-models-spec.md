# digest M17-models-spec -- models.py 规格（frozen / extra=forbid / CEL-0）
# 消费方: WP-models
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 860-872
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 860-872 -->
  860| ### 3.3.3 models.py —— 数据契约（pydantic v2）
  861| 
  862| | 项 | 内容 |
  863| |---|---|
  864| | 职责 | 定义 8 张输入表、5 张输出表、权重版本与 provenance 的全部数据模型 |
  865| | 统一配置 | model_config = ConfigDict(frozen=True, extra=forbid)；枚举一律 typing.Literal 或 StrEnum |
  866| | 输入模型 | StrategyMasterRow、MetricDictRow、MetricFactRow、DesignCardRow、RedlineRow、WeightVersionDoc、GradeRuleRow、AnchorSetDoc |
  867| | 输出模型 | ScoreCardRow、GradeLedgerRow、SensitivityReport、EntropyDiagnosticRow、TriangulationReport、AuditBundle |
  868| | 中间模型 | AttainmentFrame、NormalizedFrame、EvidenceFrame、RedlineFrame、ScoreFrame、GradeFrame、PoolFrame、PoolStats |
  869| | v1.1 变更 | AhpProvenance → **WeightProvenance**（扩展，向后兼容原字段），见 §3.11.4 |
  870| | CEL-0 预留 | DesignCardRow 增加 7 个可空字段；evidence_source ∈ {CARD_ONLY, CEL_ESTIMATED}；ScoreCardRow 增加增量三列 + value_captured 占位；AuditBundle 增加 cel_contract_version（见 §5.8.1） |
  871| | 守护 | V-5（未声明字段必须报错）、CEL-0 一致性用例（cel.enabled=false 时逐字段比对 G-01~G-15 完全一致） |
  872| 
