# RUN-ORCH-36：G-14 口径裁决 + P2 拆包 + reason_code 接线逐条分派

- 状态：ACCEPTED（主控裁决，T+6.0h）
- 触发：ADJ-G14 取证（`dsm_stage/ADJ-G14/G14-EVIDENCE.md`，487 行 / 44541 B）；P2PREP 盘点（`dsm_stage/P2PREP/P2-EXEC-SPEC.md`，374 行）；R15B2 接线登记（`dsm_stage/R15B2/CONSUMPTION-TODO.md` 9 条 + `MODELS-DEFERRED.md` 4 项）
- 关联：ORCH-34（退出码归属、ratchet 收缩排程）、ORCH-35（G-10）

## 第一部分：G-14「低证据占比上升 → MIX_QUALITY_DEGRADED」

### 取证事实（ADJ-G14，逐字）
- **分子**：SDD **L1416**（§3.16.2）逐字为「构造一级库中 **C 类占比**上升的场景」，是**唯一**明文触发量。**「C+D 占比」逐字原文未找到**（`低证据等级` 全文仅 L1202 的 `evidence_class_min`，与 G-14 无关；L1722 / L1854 只给承载与「防作弊」目的，不给分子）。
- **原文自身互斥**：L1416 限定「**一级库中** C 类」，而 L1002 / L137 / L1436 明文 **C 类不得进一级库**（一级库内 C 恒为 0）。故 L1416 的限定语在字面上不可满足。
- **分母**：**原文未定义**。全文 `分母` 仅 6 处命中，唯一相关的是 **L1004**「`NOT_ASSESSED` 单独计数，**不计入分母**」（负向排除，非正向定义）。13 卡出桥 / 12 事实 pair / assessed 集 / 池内策略数 四候选**无一被明文点名**，11 vs 12 在 SDD 层面不可判定。
- **实现**（`dsm/pooling.py:200-208`）：分子 = `sum(structure[c] for c in LOW_EVIDENCE_CLASSES)` = **C+D**（常量 `:74`，注释锚 `[L1854]` 但该行无此字样）；分母 = 四类合计（基线 **11**，**不剔** `NOT_ASSESSED`），与同模块两列 `share_*` 所用 `domain_count` / `len(assessed)`（`:424/:425`）**不同源**。判据 `:211-224`：`now - before > numeric.TOL`（`numeric.py:19` = 1E-12）。阈值**非明文数字、不在 config、不属 K-01~K-20**（L1734-L1757 已逐条核过）。
- **GAP-06（独立且决定性）**：`mix_quality_verdict` **未被 `dsm/reports.py` / `dsm/cli.py` 调用** → 「报告出现警示」在现接线下**永不成立**。

### 裁决
1. **分子改为「C 类占比」**。理由：L1416 是唯一明文，而 C+D 口径**零原文依据**；在「一处明文（含一个自相矛盾的限定语）」与「零原文」之间，依原文优先取前者。且 G-14 这个守护点的**存在目的**就是验证「C 类占比上升能否被检出」——若实现度量 C+D，则当 fixtures 把 2 个策略从 D 搬到 C 时 `(C+D)` 恒为 `8/11` 不变，守护点对其声称要防的情形**完全失效（vacuous）**，这本身违 V-14。
2. **「一级库中」记为 `ERRATUM-04`**，不据其字面实现（一级库内 C 恒 0 会使该判据恒不触发）。交业务签认：若确认应为「候选池 / 全体策略中 C 类占比」，则本裁决第 1 条的实现口径不变，仅文案更正。
3. **分母必须与两列 `share_*` 同源，且依 L1004 剔除 `NOT_ASSESSED`**。同一模块内对同一概念使用两个不同分母不可辩护。这是原文约束下的**收窄**，不是发明。11 vs 12 的争议（D-A1-07）由 A1c 依 A1CPREP 的裁决处理，本条只要求「同源 + 剔 NOT_ASSESSED」。
4. **阈值属工程默认，不是签认值**：实现用 `numeric.TOL`（1E-12）等价于「任何上升都警示」。**保持该默认不变**（改阈值即发明业务参数，违 R-12），但必须：① 在代码注释与 `docs/deliverables/K-SIGNOFF-CHECKLIST.md` 中登记为**新立 K 项**（建议 `K-21 MIX_QUALITY_DEGRADED 触发阈值`），当前值一律 `PLACEHOLDER`；② P3a 披露「现用 1E-12 为工程默认，非业务签认」。
5. **GAP-06 必须修**：`mix_quality_verdict` 接入 `dsm/reports.py` 与 `dsm/cli.py`，使警示真正出现在报告里。算出而不披露 = 静默降级，违 V-14。**此项与第 1~3 条同批，否则修了也观测不到。**
6. **执行包 = G14FIX**，写集 `dsm/pooling.py` + `dsm/reports.py` + `tests/test_pooling.py`；**必须排在 MODELS-1 之后**（MODELS-1 对 `dsm/pooling.py` 有条件写集）。`tests/test_golden_b.py` 的 g14 期望**不改**——本裁决使实现向 L1416 对齐，该测试应自然转绿；若仍红，说明修得不彻底，**禁止反填期望**（R-14）。
7. **CONSUMPTION-TODO 第 6 条**（`pooling.py:396-397` 的 `PRIMARY_POOL_REJECTED_GRADE` 单槽 `None`）**并入 G14FIX**，因为它同样落在 `dsm/pooling.py`，避免两个包抢同一写集。

### 红线自证
本裁决**改的是实现去贴唯一明文原文**，不是改测试期望去贴实现。测试期望（E3 依 L1416 手算）保持不变。净效果：守护点从 vacuous 变为有效。

## 第二部分：P2 拆包

P2PREP 实测发现 R15B2 的 9 条消费点里 **8 条落点不在 `dsm/cli.py`**，且 `work_packages.P2.tf_max = 0` 与「5 处 delta 需新测试锁死」直接冲突，`budget_min=75` 明显不足。故拆为：

- **P2-cli**（已派，`dsm/cli.py` + `tests/test_cli.py`）：6 项**不依赖 fixtures** 的 delta —— #5 `_EXCEPTION_CODES`(L39-45) 补三族异常映射、#8 `cmd_combine_build`(L310) 接 `elicit_hierarchy`、#9 `cmd_calibrate`(L338) 接 4 个注入、#10 `cmd_whatif`(L352) 补 `run_id`/`input_dir`/`directory_hash` 与 `--include-sensitivity`、#14 `--help` 12/12 退出码 5（L435 吞 `SystemExit`）、#3 L193 静默 `pass`（违 V-14）。
- **P2-wire**（A1c + MODELS-1 之后）：#4 `reproducibility_hash`/`cel_contract_version` 硬写 PLACEHOLDER、#6 `_chain_gate`(L220-236) 九步 marshal、CONSUMPTION-TODO 的接线、`preflight.py:209-211` 等价性核验（ORCH-35 第4条）、ratchet 32→28 收缩、编码校验门禁收窄、**全量 0 failed 判定**。

**tf 额度**：P2-cli / P2-wire / G14FIX / E3b 一律批准新增测试（`tf_max` 由 0 上调），因多处 delta 必须新测试锁死；**禁弱化既有断言**的红线不变。

## 第三部分：CONSUMPTION-TODO 9 条逐条分派

| # | 落点 | 裁决归属 | 依据 / 备注 |
|---|---|---|---|
| 1 | `io_loaders.py:285-287` | **A1c 优先，其后 P2-wire** | 退出码 **4**（ORCH-34 第1条 / M21 L892）。若 D-A1-05 裁为「改 io_loaders 支持 JSONL」，则 `io_loaders.py` 写集在 A1c 期间归 A1c，P2-wire 排其后，避免撞车 |
| 2 | `preflight.py:320` 重复键静默取后一行 | **P2-wire** | 属实现层 V-14 静默降级，与 fixtures 无关；**A1c 不得改 `dsm/preflight.py`**。违 M18 L1102 |
| 3 | `triangulation.py:380-388 / :420-426` | **P2-wire** | `SPEARMAN_ZERO_VARIANCE`；severity 为 PLACEHOLDER（ORCH-34 第2条：维持暂定 WARN 不升格）；`blocks_run=False` 有逐字依据（M26 L1022「不入分」） |
| 4 | `weights_combine.py:683-690` | **P2-wire** | L631 逐字要求「输出每个 α 违反了哪条约束的矩阵」，泛码 `ALPHA_INFEASIBLE` 无法承载；`ALPHA_INFEASIBLE` 保留给「可行集为空」 |
| 5 | `weights_combine.py:475-481` | **P2-wire** | L62 D2 约束① + L1140 逐字「true 则不参与熵权组合」 |
| 6 | `pooling.py:396-397` | **G14FIX** | 同写集合并，避免两包抢 `dsm/pooling.py` |
| 7 | `preflight.py:215-237` C-03 | **P2-wire** | M22 L902 逐字 **BLOCK** → 换 `WEIGHT_DICT_MISALIGNED` 并同步进 `RUN_BLOCKING_CODES` 与 `DISCLOSURE`（`AUDIT_ONLY` = audit + 退出码 2）。**这是 WARN→BLOCK 的行为变更，批准**，因有逐字依据。换码后须复核 `tests/test_preflight.py:240` 与 L451 一致性断言，**不得弱化** |
| 8 | `whatif.py:452-463` GEOMETRIC 分支 | **本 RUN 不做（WONTFIX）** | 见下方第四部分 |
| 9 | `attainment.py:524/528/532` | **P2-wire** | `MISSING_FACT_RULE_APPLIED`；**不得**挪用 `MISSING_RATE_WARN`（其 message 绑定「缺失率超过预警阈值」，挪用即虚报）。M18 L1134 四种 missing_rule；M22 L903；M31 L1411 G-09 四分支须各不相同 |

## 第四部分：其他裁决

1. **CONSUMPTION-TODO 第 8 项（whatif GEOMETRIC 近似归因分支）本 RUN 不补**，登记 `D-A4-02`（WONTFIX-THIS-RUN）。理由：① 属**新增功能实现**而非缺陷修复；② 其 `APPROXIMATE_ATTRIBUTION` 的 severity 为 `PLACEHOLDER`（原文无严重度列），在硬停线内引入未签认的行为变更风险高于收益；③ 现状抛 `WhatifOperatorError` 是**显式拒绝**，符合 V-14（不是静默降级）。P3a 须披露 M10 L674 / L473 的「标注 `APPROXIMATE_ATTRIBUTION`」要求**尚未实现**，交下一版本。
2. **编码校验门禁收窄**：门禁有明文定义（非 PLACEHOLDER）——`docs/ORCH-TEMPLATE-v1.0.md:146`(H-G3) + `docs/CONTEXT-BRIEF-v1.0.md:33` + `docs/RUN-UNATTENDED-v2.0.md:72` + `docs/adr/ORCH-21.md:130`，四要素 = UTF-8 strict / 无 BOM / LF / 源码无 TAB；P-8 不属编码校验。**门禁作用域收窄为 `git ls-files`**（受版本控制文件，实测违规 **0**）。`tools/normalize.py --check` 默认作用域含 gitignored 的 `dsm_stage/`（故报 17/524，17/17 全在 `dsm_stage/{C2b,E3,SEAM-1}`）→ 登记 `D-TOOLS-01`，修默认作用域归 P2-wire。20 个文件缺末尾 LF 属历史遗留，**只对本次变更文件断言**，不为历史文件返工。
3. **pytest 命令口径固化（教训 L-07）**：`pyproject.toml` 的 `addopts` 已含 `-q`，再叠 `-q` 会变 `-qq` 并**吞掉汇总行与 short summary**（看似 pytest 崩溃）。取数命令一律 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=no --continue-on-collection-errors`。
4. **哈希纪律**：P2-wire 须重登记 A1c 后重测值，并**保留旧值 `8083efc9…` 与 `4de4b8cb…`** 供 P3a 披露，**严禁「修回」旧值**。
5. **`MODELS-DEFERRED.md` 4 项本 RUN 全部不做**（ORCH-31 第3条已定）。补记 P3c-prep 的实测纠偏：A4 自述「`whatif.py` 有 8 个输出模型」不实，实测仅 1 个非异常类（`WhatifReport:232`）；该 4 项中第 2 项须按实测重写后再交下一版本。第 3 项（`PoolStats` 加 `flags` 列）与本 ADR 第一部分第 3 条相关：若不加 `flags`，池级/报告级披露无载体，G14FIX 须自行确认 `mix_quality_verdict` 的承载字段，**不得为此擅自改 `dsm/models.py`**（MODELS-1 独占），如确有载体缺位则上报主控。
