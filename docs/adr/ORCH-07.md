# ORCH-07 Ratio / MoneyMinor 注解类型在 SDD 零命中，判为 H-4 的工程实现手段

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02 |
| 裁决人 | Orchestrator（主控） |
| 类型 | 口径裁决（保守超集，§10.2-2） |

## 事实（实测 grep -Fn，SDD sha256[:12]=708679e9a83d / 2003 行）

| 词 | 命中数 | 命中行号 |
|---|---|---|
| `MoneyMinor` | 0 | — |
| `Ratio` | 0 | — |
| `Annotated` | 0 | — |
| `from_float` | 0 | — |
| `float` | 3 | L798、L1265、L1268 |

ORCH §5.2 S1-T02 要求 models.py 提供「拒 float 的 `Ratio` / `MoneyMinor` 注解类型」，
但 SDD 全文不存在这两个类型名。

## 裁决

1. `Ratio` / `MoneyMinor` **不是 SDD 口径，而是 ORCH H-4 在 pydantic 层的实现手段**。
   仍按 H-4 实现，作为「保守超集」——它只收紧类型、不放宽任何 SDD 口径，
   因此不可能与 SDD 冲突（ORCH 卷首：与 SDD 冲突时一律以 SDD 为准；此处不冲突，只是 SDD 未规定实现手法）。
2. 语义边界（不得越界发明）：
   - `MoneyMinor`：金额，Python `int`，最小货币单位，字段名后缀 `_minor`，**精确相等**比较；拒 float、拒 Decimal 小数。
   - `Ratio`：比率/达成率/权重/均值，Python `Decimal`，**字符串构造**，比较容差 1e-12（`numeric.TOL`）。
   - float 只能经 `numeric.from_float()` 进入——该函数**已存在于 S0 基线** `dsm/numeric.py`
     （实测签名 `from_float(value: float, places: int = 12) -> Decimal`），是既有代码事实，非本次发明。
3. 实现依据锚定 SDD §3.13 数值精度（L1261-1275，含 L1265/L1268 的 float 表述），
   逐字原文见 `docs/digest/S1-T01c.md`。

## 依据

ORCH §2 H-4；§10.2-2（不影响金额与等级语义的内部缺口 → 选保守超集 + 写 ADR）；
SDD §3.13（L1261-1275）；S0 基线 `dsm/numeric.py` 实测签名。

## 影响

本裁决**不改变任何金额或等级语义**，只把 H-4 从「靠纪律」升级为「靠类型系统机器守护」，
与产品「可辩护 / 可审计」的第一属性一致。不触发 §10.1 停机（不影响金额与等级语义）。
