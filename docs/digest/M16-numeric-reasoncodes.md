# digest M16-numeric-reasoncodes -- numeric 关键函数与规则 + reason_code 单一事实源
# 消费方: ALL
# 来源: 开发设计文档-策略评价可辩护评分模型DSM-v1.1.md (sha256[:12] 708679e9a83d)
# 行区间: 840-859
# 规则: 行号即原文行号，逐字摘录，不得改写；本文件是该任务的唯一事实来源


<!-- SDD 840-859 -->
  840| ### 3.3.1 numeric.py —— 数值口径（R6 的唯一实现点）
  841| 
  842| | 项 | 内容 |
  843| |---|---|
  844| | 职责 | 提供全系统唯一的数值比较与运算入口，任何模块**不得**自行写 == / abs(a−b) < eps |
  845| | 关键函数 | to_minor(x) → int（元转最小货币单位，非整数即抛 NonIntegerAmountError）；from_minor(x) → Decimal（仅展示层用）；safe_div(a, b, on_zero)（显式指定分母为 0 的返回值，禁止默认 0）；eq_exact(a, b)（金额 / 计数用）；eq_tol(a, b, tol=Decimal(1e-12))（比率 / 达成率 / 权重 / 均值用）；q12(x)（quantize 到 1e-12）；weighted_sum(pairs)（顺序固定 + q12） |
  846| | 规则 | 金额一律 int（字段名后缀 _minor）；Decimal 一律**字符串构造**，禁止 Decimal(0.1)；除法必须走 safe_div；序列化前显式排序遍历 |
  847| | 异常 | NonIntegerAmountError、DivisionUndefinedError |
  848| | 复杂度 | O(1) |
  849| | 依赖 | 无（标准库 decimal） |
  850| 
  851| ### 3.3.2 reason_codes.py —— reason_code 单一事实源
  852| 
  853| | 项 | 内容 |
  854| |---|---|
  855| | 职责 | 用枚举集中定义全部 reason_code，禁止在业务代码里写字面量字符串（P-8 用 AST 扫描守护） |
  856| | 分类 | Preflight（C_*）、Weight（WEIGHT_REALLOCATED / ENTROPY_* / ALPHA_*）、Evidence（EVIDENCE_*）、Redline（REDLINE_HARD_* / REDLINE_SOFT_*）、Grade（CAPPED_* / VERSION_BREAK / HYSTERESIS_*）、Robust（FLIP_RATE_UNUSABLE / METHOD_DIVERGENCE / DOMINANT_METRIC / NORMALIZATION_SENSITIVE）、Diagnostic（RETIRE_OR_REDLINE / MERGE_OR_DROP / REDEFINE / CONTENT_VALIDITY_DOUBT）、Invariant（INVARIANT_VIOLATION_*） |
  857| | 结构 | 每个 code 携带：code、severity（INFO/WARN/BLOCK）、user_message_template（中文，报告直接渲染）、owner_hint（该找谁整改） |
  858| | 理由 | 报告可解释性与工单派发都依赖它；散落字面量会导致拼写分叉与漏披露 |
  859| 
