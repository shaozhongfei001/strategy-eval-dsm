# ORCH-17 reason_code 必须在契约层校验为已注册码；Literal 的 lax 强转属 H-4 泄漏

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02（R4 复核质询点 E2 + 复核发现的 direction 泄漏）；约束全阶段 |
| 裁决人 | Orchestrator（主控） |
| 类型 | 口径裁决（H-7 / H-6 的机器守护前移）+ 通用实现规约 |

## 一、reason_code 契约层校验（E2，判必修）

### 事实
- SDD [L1183]：`reason_code`（出现在台账与报告里）
- SDD [L1507] V-14：所有降级路径都有 reason_code 且出现在报告中（**无静默降级**）
- SDD [L993]：红线 reason_code 形态为 `REDLINE_HARD_<code>` / `REDLINE_SOFT_<code>`（**动态生成**）
- S0 基线 `dsm/reason_codes.py` 已提供 `is_registered(code) -> bool`（含 `_DYNAMIC_PREFIXES` 处理动态码）、
  `redline_hard(metric_id) -> str`、`redline_soft(metric_id) -> str`
- R4 实测：`RedlineRow(reason_code='TOTALLY_MADE_UP_CODE')` **构造成功**；
  `dsm/models.py` 中 `field_validator` 命中 0、`is_registered` 命中 0

### 裁决
1. H-7 字面禁的是**源码里的裸字符串码**，`RedlineRow.reason_code: str` 未违反字面（R4 判 E1 ✅ 正确）。
2. 但**未注册码能在契约层构造成功**，等于把「无静默降级」（V-14 / H-6）的守护推迟到 L4/L5 才暴露，
   而守护工具 `is_registered()` 已就位却未被使用 → 判为**必修缺口**。
3. 处置：`reason_code` 字段加校验，调用 `dsm.reason_codes.is_registered`；未注册码必须拒。
   **不得**在 models.py 里硬编码任何裸 reason_code 字面量（H-7）；
   测试的期望值必须用 `RC.<NAME>.value` 或 `reason_codes.redline_hard(...)` 生成，**不得写裸字符串当期望**。
4. 注意 `str(RC.STABLE) == 'RC.STABLE'` 而 `RC.STABLE.value == 'STABLE'`（S0 已实测的陷阱），取值一律走 `.value`。
5. **推广**：后续所有阶段的模型（GradeLedgerRow、各 Frame 的 reason_code 列、审计包）一律按本条在**契约层**校验，
   不得留到运行期。R4 在各阶段按本 ADR 判定。

## 二、Literal 的 lax 强转属 H-4 泄漏（通用实现规约）

### 事实
R4 实测 `direction: Literal[1, -1]`（models.py L91）：
`True` → **接受并落 1**；`1.0` → **接受**；`Decimal('1')` → **接受**。
根因是 pydantic v2 默认 **lax** 模式会对 Literal 做隐式强转，而 Python 中 `bool` 是 `int` 子类、`1.0 == 1` 为真。

### 裁决
凡 Literal / int 语义字段承载**计数、方向、期数、序号**一类整数口径者，必须显式关闭 lax 强转：
用 `Field(strict=True)` 或 `BeforeValidator` 显式拒 `bool` / `float` / `Decimal` / `str`。
依据 [L1266]「计数 = int；精确相等」与 H-4「float 只能经 `from_float()` 进入」——
lax 强转让 float 与 bool **绕过** `from_float()` 直接落地为 int，属 H-4 泄漏。
**推广**：S1-T03/T04 与后续所有阶段的新增模型一律适用；R4 复核时须用 `True` / `1.0` 做探针实测，不得只看类型注解。

## 依据

SDD L993 / L1183 / L1266 / L1507；ORCH §2 H-4 / H-6 / H-7；S0 基线 `dsm/reason_codes.py` 实测 API；R4 实测探针输出。
