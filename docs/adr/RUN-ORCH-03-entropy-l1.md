# ADR RUN-ORCH-03 - entropy.py 落位 L1（分层注释单点变更）

- 状态：已执行（SP-1，T+0.9h）
- 执行者：主控 Orchestrator（R-15：契约文件只有主控能在同步点改）
- 改动面：`dsm/__init__.py` 第 7 行，**1 行注释**，零代码逻辑变更

## 变更内容

    -    L1   numeric / reason_codes / models / config / io_loaders
    +    L1   numeric / reason_codes / models / config / io_loaders / entropy

## 问题

SDD 行 537 明确「熵权公式（六步，**两个计算者共用同一实现**）」。两个计算者是
`weights_combine.py`（L0a，离线权重构造）与 `diagnostics.py`（L5，在线诊断）。
但 INV-1 规定 **L1-L5 永不 import L0a/L0b** -> `diagnostics`(L5) 不能调用
`weights_combine`(L0a) 里的熵权实现。二者不可能同时满足，除非把实现放到更低层。

## 裁决

新增 `dsm/entropy.py`，层级 **L1**，作为熵权六步的**唯一实现**；
`weights_combine`(L0a) 与 `diagnostics`(L5) 都从 L1 导入它。

## 依据

1. 只有放在 L1 才同时满足 INV-1（L1 不 import L0）与「共用同一实现」。
2. 不放进 `numeric.py`：numeric.py 是「全系统唯一**数值口径**实现点」
   （金额 int / 比率 1e-12 原语），熵权是六步统计算法，混入会污染其职责，
   并让全部 6 条 lane 争抢同一文件的写集。
3. 类型隔离照旧成立：`WeightProvenance.entropy` 仍是**快照值**，不是可调用对象。
4. INV-3「a scoring run must never recompute entropy weights」不被违反：
   评分运行链（L1-L7）不重算熵权；`weights_combine` 属 L0a 离线构造，
   `diagnostics` 的在线熵权只作诊断，其输出对象**不含任何可被 aggregate 消费的权重字段**
   （由 F3 包内测试 + `tests/test_architecture.py` 双重守护）。

## 影响

- 模块数 23 -> **24**。
- **不改任何设计口径、不改任何算法步骤、不改任何数值口径。**
- F1（`dsm/entropy.py`，commit a4bd363）已按此落位交付，本 ADR 只补齐分层注释。

## 验证

- `from dsm.entropy import ...` 在 L0a（A2 weights_combine）与 L5（F3 diagnostics）均可用。
- 变更后全量回归结果见 SP-1 对账单（同一提交内记录）。
- `tests/test_architecture.py`（E5）将把「entropy 在 L1、L5 不 import L0a」写成机器守护。
