# ORCH-18 lax 强转闸门的全字段适用规则：int 语义列与 bool 列一律显式设闸

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-23 |
| 阶段 / 任务 | S1 / S1-T02（R4 二审条件 1）；**约束 S1~S9 全部模型** |
| 裁决人 | Orchestrator（主控） |
| 类型 | 口径裁决（ORCH-17 的适用范围扩展） |

## 事实（R4 二审实测）

- `GradeRuleRow.promotion_streak: int`（`dsm/models.py` L328，SDD [L1204]「连续达标几期才允许升级」= 期数）
  **未设闸**：`True` → 接受落 `int 1`；`1.0` → 接受落 `1`；`'3'` → 接受落 `3`。测试文件对该字段无任何 lax 探针。
- 三个 bool 列同样未设闸：`mde_ok=1` → True、`mde_ok='true'` → True、`is_redline='yes'` → True、`waiver_allowed=1` → True。
- 对照：`direction`（[L1137]）已按 ORCH-17 设闸，13 例全对。

## 裁决 1：ORCH-17 的适用范围由「计数/方向/期数/序号」扩展为**全部 int 语义列**

`promotion_streak` 是期数，本就在 ORCH-17 列举范围内，属**实现遗漏**而非规约空白 → 判 ❌ 必修。
规则明确为：**凡字段注解含 `int`（含 `int | None`）且语义为计数/期数/序号/方向/最小货币单位者，
必须显式关闭 pydantic lax 强转**（`BeforeValidator` 或等价手段），只收 Python `int` 且拒 `bool`；
`float` / `Decimal` / `str` 一律拒。

## 裁决 2：bool 列一律只收 Python `bool`

SDD 未对 bool 列规定 lax 行为，但把 `'yes'` / `'true'` / `1` 静默解释为 True 属**未留痕的隐式类型转换**，
与下列三条直接抵触：
- [L889]：io_loaders 必须做「类型强制：金额列必须解析为 int（失败即记 C-09）；日期列必须 ISO；**枚举列做 Literal 校验**」——即 SDD 的总原则是**入口严格校验**，不是宽松解释
- H-6 / V-14 [L1507]：无静默降级。静默把 `'yes'` 当 True 正是一种无 reason_code 的隐式降级
- H-4 的立法精神：跨类型进入必须走**显式**通道（float 只能经 `from_float()`）

故裁决：`is_redline`（[L1140]）、`waiver_allowed`（[L1184]）、`mde_ok`（[L1174]）及后续所有 bool 列
**只收 `True` / `False`**；`1` / `0` / `'true'` / `'yes'` / `'Y'` / `None`（当字段必填时）一律拒。
`bool | None` 的可空列允许 `None`，但仍拒 int/str。

## 裁决 3：CSV 文本到 bool/int 的显式转换归 io_loaders（S3-T01）

模型层收紧后，CSV 里的 `'true'` / `'1'` 文本**必须**由 io_loaders 在入口处**显式**转换为 Python `bool` / `int`，
并且：
- 转换表（接受哪些字面量）必须写在代码里且**可审计**，不得散落在各处
- 无法识别的字面量必须**报错并记 reason_code**（金额列依 [L889] 记 C-09），**不得**默认成 False / 0
本项登记为 **S3-T01 的验收项**（`ops/blockers.md` B-010）。

## 裁决 4：R4 复核方式（防止逐个抓漏）

R4 在各阶段复核模型时，**必须做全字段扫描**而非抽查：枚举该模型所有 `int` / `bool` 语义字段，
对每个字段用 `True` / `1.0` / `'3'` / `'yes'` 四个探针实测，任一被接受即判 ❌。
本轮即因抽查而漏掉 `promotion_streak`，故立此规约。

## 依据

SDD L889 / L1137 / L1140 / L1174 / L1184 / L1204 / L1507；ORCH §2 H-4 / H-6；`docs/adr/ORCH-17.md`；R4 二审实测探针输出。
