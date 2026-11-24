# RUN-ORCH-35：G-10「维度被清空」原文互斥裁决

- 状态：ACCEPTED（主控裁决，T+5.7h）
- 触发：E3（commit `35a6635`）上报 GAP-E3-02；P3a-prep（commit `358b4ea`）独立印证；取证包 ADJ-G10 产出 `dsm_stage/ADJ-G10/G10-EVIDENCE.md`（306 行，sha256 `7775539924e4…`）
- 关联缺陷：`D-SPEC-G10`
- 关联红测试：`tests/test_golden_b.py::test_g10_sust_dimension_emptied_must_block_preflight`

## 1. 争议

「单个维度被清空」的后果，原文存在互斥表述：

| 出处 | 逐字判据 | 后果 |
|---|---|---|
| **SDD L901**（M22 / §3.4.1，检查项 C-02） | 「未签认指标 → 剔除并重归一（WARN）；某维度被清空 → 该维度 W 置 0 重归一；清空维度数 ≥ 2 → BLOCK」 | 单维清空 = WARN + 重归一；**≥2 维**才 BLOCK |
| **SDD L1286**（M28） | 与 L901 同文（第二来源旁证） | 同上 |
| **SDD L1412**（M31，G-10 设计意图） | 「若该维度被清空 → preflight BLOCK」 | 单维清空 = **BLOCK** |
| **SDD L1585**（§4.4，不在任何 digest 段内） | 「整个维度被清空 → BLOCK」 | 单维清空 = **BLOCK** |

补充事实（ADJ-G10 实测）：
- `DIMENSION_EMPTIED` 在 SDD 全文 **0 命中**，系 `dsm/reason_codes.py` 注册表自名。
- 实现 `dsm/preflight.py` 完整对齐 L901 且注释自引 `[L901]`；单维清空实测 `WARN` / `exit_code=0`（与 E3 上报一致）。
- 实现另有 `dsm/preflight.py:209-211`「全维清空也 BLOCK」分支，**原文未找到**独立依据。
- C-03「无孤儿权重项」（L902，BLOCK）的「孤儿」定义**原文未找到**；实现按「不在指标字典才算孤儿」→ 本变体不命中（`preflight.py:226-227`）。
- 变体 `G10_dim_emptied` 实为**单个 JSON 文件**（非目录），且未改权重文档，SUST 下仍留 2 个未签认指标的权重项。

## 2. 裁决

**以 M22 C-02（SDD L901）为规范判据。实现正确，测试期望过严。M31 L1412 与 §4.4 L1585 记为文档勘误。**

决定性理由是**内部一致性**，不依赖任何「哪节权限更高」的元规则：L901 同句之内既规定「某维度被清空 → 该维度 W 置 0 重归一」，又规定「清空维度数 ≥ 2 → BLOCK」。若单维清空即 BLOCK，则「W 置 0 重归一」这一支**永无执行机会而成为死条款**。原文在同一句里同时保留两支，证明单维清空被设计为**可继续（WARN + 重归一）**，只有 ≥2 维清空才阻断。M28 L1286 同文构成第二来源印证。

因此本裁决**不需要**先解决 ADJ-G10 提出的「L911 口径统一声明是否覆盖 M31 golden 表」这一争议——该争议单独登记为 `ERRATUM-02`，其结论不影响本裁决成立。

## 3. 落地分派

1. **E3b**（写集含 `tests/test_golden_b.py`）：
   - 把该测试的期望改为 L901 的行为：单维清空 → `WARN`、`blocks_run=False`、`exit_code=0`、该维度 W 置 0、**重归一后权重和 Decimal 精确等于 1**（V-9）、披露码用实现实际产出的注册名（`WEIGHT_REALLOCATED`）。
   - 测试**改名**以反映正确期望（建议 `test_g10_single_dimension_emptied_reweights_to_zero_and_warns_not_blocks`），避免名字继续误导后来者。
   - **必须新增**一条覆盖 L901 真正 BLOCK 分支的测试：**清空 ≥2 个维度 → BLOCK + exit_code 2**。该分支当前**无任何测试覆盖**，补上是加强而非弱化，用以证明本裁决不是「为了转绿而放宽」。
   - 改名 + 新增后断言总数须 ≥ 改前；`git diff -U0` 自证无 `assert` / `pytest.raises` 行被删除或放宽（R-14）。
2. **P2**（写集含 `dsm/preflight.py`，且 R15B2 的 `CONSUMPTION-TODO.md` 已把 `preflight.py:36-40` / `:42-49` 两个接线口划给 P2）：
   - 核验 `preflight.py:209-211` 的「全维清空也 BLOCK」分支是否**严格等价于** L901 的「清空维度数 ≥ 2 → BLOCK」。若维度总数为 1 且被清空（清空数 = 1），按 L901 应为 WARN，该分支**不得**触发 BLOCK；不等价则修正。
   - 补一条「单维度体系被清空 → WARN 非 BLOCK」的边界测试。
3. **P3a**：把下列各项写入 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` 披露节与 `docs/deliverables/KNOWN-GAPS.md`，并列为**待业务签认项**：
   - `ERRATUM-01`：M31 L1412 与 §4.4 L1585 的「维度被清空 → BLOCK」与规范判据 L901 不一致。**若业务方确认「单维清空即应阻断」，则属 C-02 阈值变更（≥2 改为 ≥1）**，须走契约变更流程并同步改实现与本裁决，不得由本 RUN 单方决定。
   - `ERRATUM-02`：L911「口径统一声明」的适用范围只逐字约束「C 表 vs DSN」，对 M31 golden 表的权限未明确。
   - `DIMENSION_EMPTIED` 码名无原文依据（工程自名）；按 ADJ-3 不改名、不删除，但其 severity / blocks_run 须服从 L901（单维清空场景为 WARN / `blocks_run=False`）。
   - C-03「孤儿权重项」定义原文未找到，保持实现现状不猜（R-12），登记 `PLACEHOLDER` 交签认。

## 4. 红线自证

本裁决**不弱化任何既有断言**：被改的是一条其期望值与规范判据 L901 相矛盾的测试（同 ORCH-29 对 `test_p13b` 的定性——测试构造错误而非实现缺陷），且同时**新增**了此前完全无覆盖的 ≥2 维 BLOCK 分支测试。裁决前该测试保持 RED，禁止任何一方反填（R-14）。
