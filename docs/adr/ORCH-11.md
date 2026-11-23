# ORCH-11 SDD L1268「float 后转 Decimal」中间态与 H-4「float 只能经 from_float() 进入」不冲突

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1（登记）；实际作用于 S7-T02 diagnostics / S8-T01 weights_combine |
| 裁决人 | Orchestrator（主控） |
| 类型 | 口径裁决（合并解释，非取舍） |

## 事实（逐字，见 docs/digest/S1-T01c.md）

- SDD [L1268]：熵权计算中的 ln = `Decimal.ln()` 或 float 后转 Decimal；1e-12；
  **允许 float 中间态，但输出前 quantize 到 1e-12**
- SDD [L1267]：比率/达成率/权重/均值 = Decimal（字符串构造）；比较 = 1e-12 容差；
  除法统一走 `safe_div`，显式指定 `on_zero`
- SDD [L1829]：任何比较不得自行实现，一律走 `numeric.py`（R6）
- ORCH H-4：float **只能经 `from_float()` 进入**

## 裁决

二者管辖对象不同，**合并适用，无需取舍**：

1. [L1268] 管辖的是「超越函数（熵权 ln）**计算过程中**是否允许 float 作为临时载体」——允许；
2. H-4 管辖的是「float **跨回 Decimal 世界的唯一通道**」——必须是 `numeric.from_float()`；
3. 合并后的强制链路：`float 中间态` → **必须** `numeric.from_float()` → **必须** `numeric.q12()`
   （输出前 quantize 到 1e-12，[L1268] 后半句）→ 方可进入任何比较（[L1829]，走 `numeric.eq_tol`）。

即：允许 float 出现在计算中途，**不允许 float 直接落地成 Decimal，也不允许绕过 q12 输出**。

## 机制已就位（无需新造）

S0 基线 `dsm/numeric.py` 实测已提供：
`from_float(value: float, places: int = 12) -> Decimal`、`q12(value) -> Decimal`、
`ln(value) -> Decimal`、`sqrt(value) -> Decimal`、`eq_tol(a, b, tol=TOL)`。

## 作用域与影响

S1 契约层不涉及熵权，本裁决在 S1 仅登记备查；实际约束 S7-T02 与 S8-T01。
不改变任何金额或等级语义。R4 在 S7/S8 复核时按本条判定。

## 依据

SDD L1267 / L1268 / L1829；ORCH §2 H-4；S0 基线 `dsm/numeric.py` 实测签名。
