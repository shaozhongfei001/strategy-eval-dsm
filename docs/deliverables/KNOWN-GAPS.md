# 已知缺口清单（KNOWN-GAPS · P3c-prep 前移建表）

- 性质：§3.2 第 239 行 P3c 交付物中「**已知缺口**」部分的建表与填满（README / `git tag v1.1.0` 由 P3c 在 P2 收口后执行，本包未打 tag、未改 README.md）。配套文件：`docs/deliverables/K-SIGNOFF-CHECKLIST.md`。
- 事实来源与核实方式：`ops/dag-state.json`（contract_gaps_pending 41 条 / gap_adjudications_SP1 / gap_adjudications_SP2 / r15_batch_2 / defects / orch_lessons）、`docs/adr/RUN-ORCH-25..30`、各 lane 缺口档案（`dsm_stage/{E5,A4,C2b,B1b,SEAM-1,EFIX-1,A1b}/`），以及**本包对代码的 grep 实测**（观测 HEAD `da4d0a9`，2026-11-25，P3c-final 复核）。lane 自述与代码实测不符处以**实测为准**并写进「备注」列。
- **P3c-final 修订（本版本 · 定稿）**：① 六类 `PLACEHOLDER-TO-REFRESH` 已刷新 5 类，剩余 1 类（`output_fingerprints` 的逐文件 sha256 台账）见 §H。② 计数口径改写：**阻塞 16 → 14 条／非阻塞 48 → 51 条／合计 64 → 65 条**（E-8／G-2／G-3 转 CLOSED，新登 G-20）。③ 哈希台账按 **ORCH-44** 定稿：权威值仍是 `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`，`f437c0ea…` 定性为 **non-canonical（测试内自测值）**、**不入台账**（见 §H 与 K-SIGNOFF **K-36**）。④ K-35 的「历史缺末尾 LF = 22 个」**被本包实测证伪**，权威数 **18 个**，且**并非**全在 `docs/**`＋`README.md`（详见 §H-4）。⑤ 新增 **K-36~K-39**（ORCH-44 分配）。
- **DOC-FINAL 修订（本轮 · 全量 0 failed 终值落地；观测 HEAD `037b862`／CMB-1）**：① **G-20 转 CLOSED** —— 唯一红条 `tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502 assert 8 == 9`）由 **CMB-1 @`037b862`** 精确化收口（`:502` 期望 `9→8`、`:482` docstring「keeps only 9」→「only 8」、断言上方加 5 行依据注释；删除 2 行、净断言 +0、无 skip／xfail／or 化／区间断言、未碰任何实现文件）。② 全量 pytest 终值 = **0 failed／2302 passed／2302 collected**（0 error／0 skip／0 xfail）→ **tag 前置 ① 改判「满足」**；曾未满足的历史（`1 failed／2301 passed／2302 collected` @`93abfee`／`da4d0a9`）**保留为追记**（§H-14），不抹去。③ 计数按同一 grep 口径重测：**阻塞 14 → 13／非阻塞 51 → 52／合计 65 不变**（CLOSED 行仍留账内计非阻塞）。④ `ahead` 重测 **59** @`037b862`（本包提交后 60）、`git tag -l` 仍 **0**。⑤ K 编号合计 **39**／签认动作 **43** 不变。⑥ `V-ACCEPTANCE-EVIDENCE.md` 开工时仍为 ` M`（P3a-final 在飞）→ 本包**未触碰**该文件，故 V-1 的三态上调由该包自行落地；本包只提供其上调所需的实测依据。
- **P3c-pre2 修订（上一版本）**：① 修 **D-DOC-01**——原汇总节自称「阻塞 19 条」而同文件逐条列举与逐行 grep（含 F-1／F-2 加粗「是」）均为 **24 条**（ORCH-39 第2条裁 24 为**当时**权威值）；本包不照抄 24，而是从当前正文重新逐条清点、按 ORCH-40／ORCH-41／ORCH-42 已关闭项扣减、并登记新增缺口，得**新的权威计数：阻塞 16 条／非阻塞 48 条／合计 64 条**，汇总节与正文逐条列举**由同一份数据生成并已回读自证相等**。② 新增 **G 节 19 行**（含 P2-wire-A @`53ed80c` 上报的「M29 九步 marshal 本体未落地」等阻塞级缺口）。③ A~F 各行「阻塞交付」列按实测关闭依据改写，关闭依据一律带 commit 号。
- 本包写集 = 本文件 + `K-SIGNOFF-CHECKLIST.md` + `P3c-DELIVERY-PACKAGE.md` + `README.md`；**未写** `V-ACCEPTANCE-EVIDENCE.md`（归并发的 P3a-pre2）、`P3b-REPRO-HARNESS.md`（归 P3b）、`dsm/**`、`tests/**`、`fixtures/**`、`tools/**`、`config/**`、`ops/dag-state.json`、`docs/adr/**`、`pyproject.toml`。未 tag、未 push（R-13）。
- **R-12 声明**：最终全量 pytest 数字、最终 `reproducibility_hash`／`output_fingerprints`、最终 `git rev-list --count origin/main..HEAD` 一律写 `PLACEHOLDER-TO-REFRESH(<负责人>)`——本包（P3c-final）已把可实测者全部换成实测终值（§H）；仍缺的按 R-12 保留 PLACEHOLDER 并写明缺什么。**DOC-FINAL 本轮**：`最终全量 pytest` 已实测闭合（0 failed／2302 passed／2302 collected @CMB-1 `037b862`）故其 PLACEHOLDER 撤销；`ahead` 已重测 59 @`037b862`；仍剩 `output_fingerprints` 的 64 位生产台账（主控）与**最终 HEAD 上的 `repro_offline.sh` 复跑**（主控，见 §H-14 对 ③ 的追记）——本包不代跑（派工单明令）。
- **边界声明（诚实性红线，原文照录不软化）**：K-01~K-35 一律 PLACEHOLDER；`config/` 实测 **0 文件**，真实运行被 `EXIT_CONFIG=3` 拒绝（**设计如此，非 bug**）；无 console script、**无前端界面**；本 RUN 未接入真实用户／行内授权／生产对账／因果增量；`CEL` 增量层契约在 v1 保留未接入（`CEL_NOT_CONNECTED`）。
- 判据基线：M38（K 参数）、M39（G0~G8 门禁，`docs/digest/M39-risks-gates.md` L35-L43 = SDD L1787-L1795）。
- 「是否阻塞交付」口径：**是** = 阻塞 G7/真实运行/P3c 正式出分；**否** = 已有排定修复包或仅文档勘误，不阻塞合成数据演练（M39 L45「门禁失败时的合法动作」仍允许）。

## A. 契约容器类（models.py 单点化 / R-15）

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| A-1 | Step1 出结果需携 downgrades | AttainmentResult 未上移 `models.py` | `dsm/attainment.py:235` 本地声明 `AttainmentResult(AttainmentFrame)`（只加 downgrades 列，is-a 契约类型下游零改动） | 主控 R-15 单点化（r15_batch_2.models_questions 第 1 条） | 否 | ADJ-4：本地声明已被 SP-1 确认为合法过渡 |
| A-2 | whatif 预演出报告 | WhatifReport 等「8 个输出模型」是否上移 models.py | `dsm/whatif.py:232` 模块内声明 WhatifReport（字段名逐字 M10 [L649]-[L661] + run_id/operator/reconciliation/refuse_signoff 4 个可追溯列） | 主控（r15_batch_2.models_questions 第 2 条；A4 G-A4-2） | 否 | **与 lane 自述不符**：A4 gaps.md 称「8 个输出模型」在 whatif.py 内声明，实测 `grep -n "^class" dsm/whatif.py` 只有 1 个非异常输出模型类（WhatifReport:232），其余 10 个是异常类 |
| A-3 | Step7 池级披露需要 flags 载体 | `PoolStats` 无 `flags` 列（C5 请求，照 SensitivityReport.flags） | 池级否决信息经 `dsm/reason_codes.py:84-85` PRIMARY_POOL_REJECTED_* 逐策略表达；`dsm/models.py:1190` 的 `flags: tuple[ReasonCode,...]`（B-018 载体）只挂在敏感性族模型上 | 主控 r15 batch / SP-3（models_questions 第 3 条） | 否 | 实测 `dsm/models.py:1303-1320`：PoolStats 仅 rows/evidence_structure/not_assessed_count/not_assessed_reasons 四列 |
| A-4 | 同上（行级） | `PoolFrame` 无 flags 列 | `dsm/models.py:1294-1301` 仅 `rows` | 同上 | 否 | 实测一致（PoolRow 在 models.py:977） |
| A-5 | L5 旁路诊断出容器 | EntropyDiagnostic / CollinearityReport 未上移 models.py（F3 请求） | `dsm/diagnostics.py:113/138` 本地 `_Frozen` 声明；models.py 只有 EntropyDiagnosticRow（:1158） | 主控（models_questions 第 4 条） | 否 | ADJ-4 确认合法 |
| A-6 | preflight 出结果 | PreflightResult 无契约模型 | `dsm/preflight.py:125` 本地声明 | 主控 R-15 | 否 | models.py grep `class PreflightResult` 无命中（实测） |
| A-7 | Step5 滞回入参 | GradeRuleSet 不在 models.py（digest L962 签名要求） | `dsm/grading.py:79` 本地声明（models.py 只有 T7 行模型 GradeRow，:954） | 主控 SP-3 | 否 | contract_gaps B3 |
| A-8 | audit manifest | RunContext 不在契约层 | `dsm/audit.py:54` 本地声明（ruling 31） | 主控 SP-3 | 否 | contract_gaps F2 |
| A-9 | AHP 产出容器 | AhpResult / ConsistencyReport / InconsistentPair 不在 models.py | `dsm/weights_ahp.py:126/138/155` 本地声明（+198 AhpHierarchy） | 主控 SP-3（ADJ-4 已确认合法） | 否 | 另：AhpSegment 单层承载不了两级 → 维度层/指标层各出一份 payload（D1 上报） |
| A-10 | 归一/池化接缝的模型位 | D-MODELS-01（models.py + normalize.py 契约位） | 未动（等 SEAM-1 收口） | MODELS-1（ORCH-29 第 4 条） | 否 | dag-state defects 实测 status=OPEN　**已闭合**：D-MODELS-01 由 MODELS-1 @`cc18a38` 收口（ORCH-38 第1条；defects 实测 status=CLOSED） |

## B. reason_code 类（R-15 batch-2 · `r15_batch_2.status=queued`，blocked_on=EFIX-1 的 test_architecture ratchet 32 对，`tests/test_architecture.py:540` 实测在案）

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| B-1 | design_card 表级缺失 | `DESIGN_CARD_TABLE_ABSENT`（BLOCK）未注册（C2b 上报） | C2b 实测（`dsm_stage/C2b/NOTES-C2b.md` §2 三期 diag）：C-08 已是策略级 blocks_run=False，无表级 BLOCK 行为 | 主控 R-15（先盘点触发场景） | 否 | **张力**：ORCH-30 撤回表级 BLOCK 后，该码触发场景是否还存在须先盘点再注册　**已闭合**：`DESIGN_CARD_TABLE_ABSENT` 已注册（R15B2 @`db13471` new_codes 实测；退出码以 M21 L892 的 io 层 4 为准，ORCH-34 第1条） |
| B-2 | 卡索引遇重复 strategy_id×version | 专用码未注册（名称待盘点，C2b 上报） | 现**静默取后一行**（r15 原文：「违 M18 L1102，属 V-14 静默降级」） | 主控 R-15 | 否 | 静默降级在修复前持续存在　**注册面已闭合**：`DESIGN_CARD_DUPLICATE_KEY` 已注册（R15B2 @`db13471`，BLOCK，`reason_codes.py:142`）；但 HEAD `git grep` 实测 dsm/ 内仅注册表命中、零消费点 → 「静默取后一行」残项移入 G-15 |
| B-3 | Spearman 一方零方差 | 零方差处置码未注册（D4 gap7 / SP2） | `dsm/numeric.py:211-215` 抛 DivisionUndefinedError；`dsm/diagnostics.py:233-235/281` rho 置 None，**不编字面量** | 主控 R-15（与 ADJ-1 同批） | 否 | grep 注册表无 Spearman/零方差相关码（实测）　**已闭合**：`SPEARMAN_ZERO_VARIANCE` 已注册（R15B2 @`db13471`）且 `dsm/reports.py` 有实测消费点；severity 依据仍 PLACEHOLDER → 新立 K-30；模块侧 `triangulation.py:380-388` 与 `:420-426` 未把该码塞进 flags → 残项移入 G-15 |
| B-4 | 标定 H-2/H-3/H-5 与红线排除 | 专用码未注册（A2 上报） | `dsm/weights_combine.py:673`（H-2）/`:661`（H-5）以布尔判据 + CombineError 路径表达，未落码 | 主控 R-15 | 否 |　**注册面已闭合**：`H2_DIM_WEIGHT_BELOW_FLOOR`／`H3_METRIC_WEIGHT_BELOW_FLOOR`／`H5_SHIFT_FROM_AHP_EXCEEDED`／`REDLINE_EXCLUDED_FROM_ENTROPY` 四码均已注册（R15B2 @`db13471`）；`weights_combine.py:683-690` 与 `:475-481` 的逐条 append 未落（P2-wire-A 禁写该文件）→ 残项移入 G-15（归 A2b） |
| B-5 | 一级库准入 grade≠L1 | 专用码未注册（C5 上报） | 用 PRIMARY_POOL_REJECTED_EVIDENCE / _ROBUST（`dsm/reason_codes.py:84-85`）近似表达证据/稳健两类否决 | 主控 R-15 | 否 |　**已闭合**：`PRIMARY_POOL_REJECTED_GRADE` 已注册（R15B2 @`db13471`）并经 G14FIX @`42d5346` 接入 `pooling.py`（HEAD git grep 实测 pooling.py 5 处 + reports.py 命中） |
| B-6 | C-03 权重未归一 | C-03 专用码未注册 | `dsm/preflight.py:215-237` **沿用 CONFIG_SEMANTIC_ERROR**（注释实测在案）；`dsm/config.py:665-676` 同样单一码 | 主控 R-15 | 否 | message 已含判据描述（SP2 原文口径） |
| B-7 | GEOMETRIC 算子近似归因 | `APPROXIMATE_ATTRIBUTION` 未注册（M10 [L674] 要求，A4 上报） | `dsm/whatif.py` 非 LINEAR 一律抛 WhatifOperatorError(CONFIG_SEMANTIC_ERROR)，**不出近似归因**（G-A4-1） | 主控 R-15 | 否 | grep 注册表无 APPROXIMATE_ATTRIBUTION（实测）　**注册面已闭合**：`APPROXIMATE_ATTRIBUTION` 已注册（R15B2 @`db13471`）且 `dsm/whatif.py` 有实测消费点（3 处）；GEOMETRIC 近似归因本 RUN 不做 → 见 G-19 |
| B-8 | missing_rule=ZERO/IMPUTE 合成分出行 | 「事实行缺失已按 missing_rule 处置」码未注册（B1b 上报；不得挪用 MISSING_RATE_WARN） | 合成行 reason_code=null（r15 原文口径，未编造字面量，R-12 合规） | 主控 R-15 | 否 |　**注册面已闭合**：`MISSING_FACT_RULE_APPLIED` 已注册（R15B2 @`db13471`，WARN，`reason_codes.py:151`）；HEAD git grep 实测 dsm/ 内零消费点，`attainment.py:524/528/532` 仍 reason_code=None → 残项移入 G-15（归 B1b／A1c，不得挪用 MISSING_RATE_WARN） |
| B-9 | digest 码名与注册名不一致 | M05/M31/M37 用旧名（详见 E-4） | ADJ-3：一律用注册名 GR_CAPPED_NO_TARGET / GR_EVIDENCE_GATE_L1 / GR_VERSION_BREAK / GR_STREAK_NOT_MET / GR_REDLINE_FORCED | 设计方更正 digest（本 run 不改冻结 digest） | 否 | 实测 `dsm/reason_codes.py:60-61` 注册名在案 |
| B-10 | 注册表盘点口径 | r15 纪律行称「先盘点已注册 79 码」 | — | 主控 | 否 | **实测 81 条**（`dsm/reason_codes.py` `_DEFS` 条目行计数）；79 为过时口径，盘点基准应以实测为准 |

## C. 口径待签认类

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| C-1 | Step7 占比双报 | 两个分母口径（同域已参评 / 全体已参评，均剔 NOT_ASSESSED）为 C5 自裁 | SP2 gap6：主控核可「属口径裁决非数值拟定」，标记**待行方签认**并入 K 清单 | 行方（P3c 签认回合） | 是 | 未进 M38 K-01~K-20 编号表，签认时须新立编号　**ORCH-41／42 补充**：三口径已权威化（ERRATUM-11：出桥 12／pooling universe 11／G-14 判据分母 9），G14FIX @`42d5346` 已按 C 类占比落地；但**行方签认动作仍未发生**，故仍算阻塞 |
| C-2 | normalize/pooling 池样本下限 | `min_pool_size` 的 yaml 键位未签认：现**复用 eval_config.normalize.min_pool_size**（[L943] 只在 normalize 块给过该键） | `dsm/normalize.py:42/70`（自述「缺口 4：键位未签认」）；`:104-109/124` 必填 StrictInt 无默认 | 行方 + 设计方确认键位 | 是 | SMALL_POOL（reason_codes.py:51）与 [L1005] POOL_TOO_SMALL 共用该阈值 |
| C-3 | IMPUTE_MEDIAN 的样本范围 | `impute_scope` 默认 **ALL_ROWS** 是代码拟定，digest 未给默认 | `dsm/attainment.py:149`（IMPUTE_SCOPE_ALL='ALL_ROWS'）、`:546`（run 形参默认值） | 行方签认默认方向或改必填 | 是 | 与 ADJ-2「必填无默认不猜数」相悖的实测反例之一（另见 C-4/K-08/K-11/K-15/K-20 的代码默认） |
| C-4 | 三角验证配置 | `gra_norm` 键名拼写与取值 `initial/mean` 由模块自定；`rho`、`divergence_threshold`、`enabled` 值未签认 | `dsm/triangulation.py:50-58`（CFG_KEYS=(enabled,rho,divergence_threshold,gra_norm)）、`:125-131`（缺键抛 MissingConfigError，不猜）；enabled 强制显式 bool（`:136-142`，H-5） | 行方签认值；键名请设计方确认 | 是 | |
| C-5 | 标定 [L540] 边界 epsilon | `shift` 必填但 digest 无值 | `dsm/weights_calibrate.py:266/708-709`（缺失即抛，不猜数 R-12） | 行方签认 | 是 | |
| C-6 | 标定窗口期数下限 | 窗口语义（N≥?）原文未给：代码取「两期起」而 M39 RK-10 要求「N<3 回退 α=1 + ENTROPY_INSUFFICIENT_SAMPLE 首屏披露」 | `dsm/weights_calibrate.py:135-138`（WindowError：<2 期或期名未知即抛；两期为下限，理由 [L619] 相邻期距离）；RK-10 回退由 insufficient_sample_error 注入钩子承接（`:30/:118`） | 设计方确认「恰 2 期」走哪条 | 是 | 两机制并存，边界情形未见原文钉死 |
| C-7 | `dsm/cli.py` calibrate 命令 | cmd_calibrate 把 `eval_config.weight_construction.window` 原样转发 calibrate，且仅捕获 TypeError | `dsm/cli.py:330-341`（实测 except 只有 TypeError） | EFIX-1 后续（异常面收敛） | 否 | EFIX-1 上报成立：window 期名未知/短于 2 期时 **WindowError 不被捕获**（grep dsm/cli.py 无 WindowError，实测），会以未处理异常崩而非受控退出码 |
| C-8 | Saaty RI 表 / 「并列最不一致前 5 对」度量 / SHORTFALL_CLAMPED | RI(n) 表值、不一致度量口径、第四公式均为公开标准值或推断实现 | ADJ-6：采纳 Saaty 标准表（n=1..10，n>10 抛 AhpError），provenance 写明来源 + 进 K 清单待行方确认；度量取 \|ln(a_ij·w_j/w_i)\| 推断；ADJ-7：SHORTFALL_CLAMPED 保留实现但标记「推断，待设计方确认」，V 表不得记已验证 | 行方确认（RI/度量）+ 设计方确认（第四公式） | 是 | contract_gaps B1（BLOCKING）/D1（BLOCKING）实测　**并入 K-21**：G14FIX 的 5 条待签认项（含现用工程默认 `numeric.TOL = 1E-12`）已逐条并入 K-SIGNOFF-CHECKLIST 的 K-21①~⑤ |

## D. 缺陷类（`ops/dag-state.json` defects 中 status ≠ CLOSED 的全部条目，实测）

| # | 缺陷 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| D-1 | D-SEAM-01（normalize×pooling 接缝） | 单例池 sd=0 不出 composite_relative + pooling 对 null 抛 PoolingInputError → M29 Step7 中断，卡 golden G-01/G-02/G-04 与 spine×14 | SEAM-1 修复已按 ORCH-28 落地（`dsm_stage/SEAM-1/NOTES-SEAM-1.md`：事实认定+手算逐位验证+回归归因） | 主控收口（defects 表状态仍是 OPEN，**待主控翻转**） | 否 | **状态文件与 lane 档案不同步**：defects.status=OPEN vs SEAM-1 已交修复+测试　**已闭合**：D-SEAM-01 由 SEAM-1 @`8f2eca3` 修复并经 ORCH-32／33 收口（defects 实测 status=CLOSED） |
| D-2 | D-MODELS-01 | models.py/normalize.py 契约位（见 A-3/A-10） | 未动（等 SEAM-1） | MODELS-1（ORCH-29 第 4 条） | 否 | OPEN　**已闭合**：D-MODELS-01 由 MODELS-1 @`cc18a38` 收口（ORCH-38 第1条） |
| D-3 | D-A1-02 | 冻结 fixtures 4 条 DID+CONCURRENT_CONTROL 卡缺 alt_method_note/interpretation_limit → 实测证据分布 A3B0C4D6 ≠ manifest 声明 A3B3C4D2；G-04/G-08 subject 落 NOT_ASSESSED | fixtures 现状使用（G-04/G-08 仍 RED） | A1c → E2b（等 P2a 落地） | 否 | SEAM-1 档案确认 G-04/G-08 仍 RED 归因于此　**已闭合**：D-A1-02 由 A1c @`6299245` 补 [L1171] `alt_method_note`（四张 DID 卡；只补 note 不补 interpretation_limit，ORCH-37 第4条）；证据分布主体级 A3B3C4D2／行级 A3B4C4D2 双口径入册 |
| D-4 | D-A1-03 | fixtures（事实表）缺陷 | 未修 | A1c | 否 | OPEN　**已闭合**：D-A1-03 由 A1c @`6299245` 依 ORCH-37 第1条追认落地（BLOCK 缺格载体由 M_COMPLAINT_RATE 迁至 M_SATISFY_SCORE 并同维对调 missing_rule，解 `dsm/redline.py:330` 死锁，g09 实测仍绿） |
| D-5 | D-A1-04 | fixtures（权重文档）缺陷 | 未修 | A1c | 否 | OPEN　**已闭合（主流程唯一真阻塞解除）**：D-A1-04 由 A1c @`6299245` 补 provenance 七键（kind=AHP_ONLY + ahp 段 + whatif_run_id=WIF-SYNTH-2026-01 + 签认四件套，全部合成待业务签认）；spine step2 由红转绿、走到 [L1322] 右支（A1d 实测 WARN／findings 5 条） |
| D-6 | D-A1-05 | fixtures 或 io_loaders 格式归属二选一（按 M21/M18 原文） | 未定 | A1c 或 C1c | 否 | OPEN　**已闭合**：D-A1-05 由 A1d @`f27334d` 按 ORCH-41 第1条 R2 的**列级口径**落地（`io_loaders.py` 新增 `_required_text_columns()` 与常量 `TEXT_AS_IS_COLUMNS`，必填 str 列的空单元格读回空串；NULL_LITERALS／后缀白名单／models.py／evidence.py 逐字节未动，fixtures 零改动）。A1d 实测 spine 7 红 → 1 红，剩余 1 红归因归 G14FIX 写集；追记：P3c-final 亲测 1 failed／2301 passed／2302 collected @`da4d0a9`（15.48s），**当时未转绿**，归因 A1c @`6299245` 的 D-A1-03；**DOC-FINAL 终值 = 0 failed／2302 passed／2302 collected（CMB-1 @`037b862`）**，`**`2444 passed in 20.67s`**（门禁① 标准形式，**ORCH-69 主控亲测 @`a81730d`**：独立 clone、porcelain 0、rc=0、`grep -c '^FAILED'` = **0**；第二形式 `-m pytest --continue-on-collection-errors -o addopts= -q` = **`2444 passed in 17.28s`**、rc=0；账目自洽 = `a432ef6` 基线 2418 + M29-2 新增 8 + B12-FIX 新增 18 = **2444**；v1.1 的 CMB-1 终值 2302 @`037b862` 保留为历史）` 撤销 |
| D-7 | D-C2-01 | —（上报被撤回） | CLOSED_AS_MISREPORTED：ORCH-30 实测三期唯一 blocks_run=True 为 C-01；preflight PROD=0，仅补 4 条负向测试 | 无（记录保留） | 否 | 状态字符串非 CLOSED，按任务口径列入本表 |

## E. 文档矛盾类

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| E-1 | ORCH-24 内部矛盾 | L43+L320 与 L36+L342+L406 四条不可能同时成立（B4 G3） | RT-08 / ORCH-25 已裁；文档勘误留 P3a 披露 | 主控/文档侧勘误 | 否 | 实测代码 `dsm/config.py:449` 的 `load_all(config_dir, *, period=None, run_at=None)` 与 ORCH-24 L43 逐字一致（L36「12 个公开名与既有用例一条不改」侧由 config.py:1166「period 必填无默认」注释体现口径分歧） |
| E-2 | M29 L1334 vs M43 L942 池键顺序 | 两文对分池键顺序的口径未对齐（B4 上报） | 代码取 M43 L942 逐字 `(biz_domain, evidence_class)`：实测 `dsm/models.py:751-752` PoolKey；normalize 分组键 `(period, pool_key, metric_id)`（`dsm/normalize.py:22/339`） | 设计方勘误 | 否 | **本包复核**：M29 L1334 原文只写「Step 2 normalize → 池内标准化 + 锚定集参照」，两行之间未见逐字可判的「顺序矛盾」；矛盾实点请主控给出（以实测原文为准的备注） |
| E-3 | M22/M28 的 C-08 严重度读法 | 「severity=BLOCK」被读成「阻断整轮」（P2a 归因错误 + 主控 ORCH-29 第 3 条自行补出表级 BLOCK） | ORCH-30 撤回并定纪律（orch_lessons L-05：severity 与 blocks_run 分离；原文未写 BLOCK 不得新增 BLOCK） | 无（教训入档） | 否 | C2b 三期 diag 实测唯一轮级阻断=C-01（`dsm_stage/C2b/NOTES-C2b.md` §2） |
| E-4 | 文档码名 vs 注册名 | M31 L1406 / M37 L1669 写 `GRADE_CAPPED_NO_TARGET`，注册名是 `GR_CAPPED_NO_TARGET`（`dsm/reason_codes.py:60`）；M37 L1656 写 `PL_L1_GATE_EVIDENCE`，注册表**无此名**（实测最接近 PRIMARY_POOL_REJECTED_EVIDENCE，`:84`） | ADJ-3 一律用注册名；digest 冻结不改，文档更正登记为缺口 | 设计方更正 M31/M37 | 否 | M43 L944 四码 INACTIVE_METRIC/RANK_REVERSAL_RISK/SMALL_POOL/ANCHOR_SET_STALE 与注册名一致（实测 `dsm/reason_codes.py:49-51/59`） |
| E-5 | M00 层级自相矛盾 | L276-278 称 weights_ahp/weights_combine/fixtures_gen 属「L0a 无依赖」，但 [L537] 要求熵权「两个计算者共用同一实现」，INV-1（L300）禁 L5 反向 import（E5 GAP-E5-01） | ORCH-03 裁决新增 `dsm/entropy.py`（L1 唯一实现，两侧从 L1 导入）；ORCH-26/27 落 ADR | 已裁（勘误留文档侧） | 否 | **与 lane 自述不符**：E5 档案称 weights_combine「L39 from dsm import numeric, weights_ahp」，实测现 HEAD 该文件 `:47-48` 为 `from dsm import numeric` + `from dsm.entropy import entropy_weights`，**不 import weights_ahp** |
| E-6 | M00 L294 L0b 目标清单非穷尽 | 在飞 L0b 模块（A3 标定 / A4 whatif）都需要清单外的边（E5 GAP-E5-09，自标 BLOCKING，阻断 A3/A4 转绿） | E5 以 ratchet/白名单暂缓；**ORCH-62 改判依据 = 全量 pytest 0 failed 已覆盖 A3（标定）／A4（whatif）两套件 ⇒「阻断转绿」的症状不再成立**（关闭证据 = 全量 0 failed；本棒不代跑终值，当前参考 = 2418 passed / 0 failed @`a432ef6`，主控独立 clone，porcelain 0） | 主控裁决（**ORCH-62 已裁**，登记于 `ops/dag-state-v1.2.json` `decisions/ORCH-62`；本棒对 ops/** 零写入） | **否**（ORCH-62 改判 是→否；**行／事实／WORKAROUND 全部保留披露，不得删除**；v1.1 原记「是」保留为历史） | `dsm_stage/E5/GAPS-E5.md` 实测标题行；**残留事实（不得写成已闭合）**= M00 L294 的 L0b 目标清单**仍非穷尽**，属**文档完备性**问题，不阻塞合成演练版交付；**重开条件** = 后续任何 L0b 新模块再需清单外的边，须登记为**新缺口**，不得沿用本裁定 |
| E-7 | combine 产物落点冲突 | [L1368] 要求写 `config/weights_WV-DRAFT.yaml` vs [L1091]「重跑不覆盖」+ config/ 为签认载体禁自动生成（D5 gap4） | 维持 `out/combine/<run_id>/`，不改 config/；P3a 披露 | 设计方 | 否 | SP2 BLOCKING_candidates 实测 |
| E-8 | Step8/Step7 顺序空洞 | 主流程 Step8(sensitivity) 在 Step7(pooling) 之后 → FLIP_RATE_UNUSABLE 首过必然无载体（C5 gap3） | C5 以必填 keyword-only sensitivity 入参 + 缺失即不予准入（PRIMARY_POOL_REJECTED_ROBUST）显式处理，非静默 | **待 SP-3 裁**（是否 P2 集成时加「Step8 后回跑 Step7」） | **否** | SP2 ruling 原文「待 SP-3 裁」实测 |

## F. G5 / G7 门禁（M39 L40 / L42，SDD L1792 / L1794 逐字）

| # | 门禁 | 通过判据（M39 逐字） | 当前实测状态 | 闭合责任方 | 阻塞交付 | 备注 |
|---|---|---|---|---|---|---|
| F-1 | **G5** D6 证据复核已完成 | 「三项争议来源逐字复核并给出采用 / 排除结论；未复核项标『禁止引用』」；M39 原文状态列：**「未完成 → 复核前全面禁用（§5.5.3）」** | 未完成：`grep -rn D6 dsm/*.py` 无命中，本 run 无复核产物；代码侧与之相容（未验证载体一律显式异常，如 `dsm/whatif.py:268-287` WhatifInputError 拒 PLACEHOLDER/None） | 行方 / D6 复核方 | **是** | 复核完成前，任何争议来源结论**禁止引用**；本两清单未引用争议来源数值 |
| F-2 | **G7** 治理配置已签认 | 「权重、门槛、红线阈值、评价周期、各指标目标值、α 及 K-15~K-20 全部脱离 PLACEHOLDER」；M39 原文状态列：**「未完成（依赖行方，见 §5.9）」** | 未完成且**无载体**：config/ 0 文件（实测 `find config -type f` = 0）；20 项 K 全部未脱 PLACEHOLDER（见 K-SIGNOFF-CHECKLIST.md）；真实运行在 `config.load_all()`（`dsm/config.py:449`）按 `EXIT_CONFIG=3`（`:71`）拒绝 | 行方（评价管理委员会）——即 K 清单的签认动作 | **是** | G7 未过时按 M39 L45：仅允许合成数据全流程/演示报告/whatif 预演，**不得**输出可用于真实资源配置的分数或等级 |


## G. 本轮新增登记（ORCH-39 ~ ORCH-42 期间产生／闭合的缺陷与缺口 · P3c-pre2 建表）

- 本节由 **P3c-pre2** 依派工单「新增的缺口也要登记（不要只删不增）」+ ORCH-42 补充事实建立；每行的关闭依据均为**本包亲自实测或主控裁决原文**（`ops/dag-state.json` 的 `decisions.ORCH-39~ORCH-42`／`defects`（27 条）／`errata`（11 条）+ 各 lane 的 `dsm_stage/*/NEED-WIRING.md`），未实测的一律写 PLACEHOLDER-TO-REFRESH。
- 观测 HEAD = `da4d0a9`（P3b-FIX）；P3c-pre2 施工期间 HEAD 依次为 `858ebc8`（LOO-1）→ `53ed80c`（P2-wire-A）→ `f4aaa6b`（ORCH-40+41 入账）→ `f27334d`（A1d）。`git tag -l` 实测 **0** 条；`git rev-list --count origin/main..HEAD` = **59**（DOC-FINAL 亲测 @`037b862`，`origin/main` = `3616f9722213f6da2cb0b4ff6fcf55cd947ed648` 已实测为 HEAD 祖先 → push 为 fast-forward；追记 54 @`da4d0a9` → 57 @`66481b1`；本包提交后为 60，push 前由主控重测），2026-11-25 09:10）。
- G-14／G-15／G-17 三行在 `dag-state` 的 `defects` 里**尚无缺陷号**；本包按 **L-12** 纪律不自占编号（编号单点分配权在主控），只描述事实与归属。

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| G-1 | D-EVID-01 出桥范围未按评价期过滤 | `evidence.classify` 出桥 13 行 vs 本期评价范围 12 个 (strategy,version) 对 | EVID-1 @`897cad1` 落地按评价期过滤；CODES-2 @`32cafd0` 注册 `RC.EV_OUT_OF_EVAL_PERIOD`（INFO／blocks_run False），`dsm/evidence.py` 的 `PLACEHOLDER_OUT_OF_PERIOD_CODE` 已消除；P2-wire-A @`53ed80c` 第③项把范围过滤披露端到端接进 reports | 已闭合（ORCH-40 第2条签认判据等级 derived:） | 否 | 出桥 13→12 实测印证；`spine:663` 的断言由 A1d @`f27334d` 改 13→12（未删、未弱化） |
| G-2 | D-A1-06 G05 变体与 golden hand 口径不自洽 | golden_map 记 S-009_CONTRIB=1.900000／综合分 1.5346，按实际 fixture 手算应为 1.810000000000／1.507600000000 | 未代填（R-14）；A1c ADR §11 已登记应改值与原文依据 L1407／L1460／L1342 | E2b（ORCH-41 第5条：golden_map 单写者=E2b，撤销原「交 E3b」的分派） | **否** | defects 实测 status=OPEN；属 R-14 的手算更新，不是照抄实现输出 |
| G-3 | D-A1-07 13／12／11 三分母互不相等 | 「证据结构占比」的分母定义未定，golden 记 4/12 | 三口径已裁并实测入册：出桥 12／证据结构 A3B3C4D2=12／占比双报 A3B3C3D2=11；ORCH-41 第8条升级为权威口径（ERRATUM-11：pooling universe 分母=11、G-14 判据分母=9） | E3b（陈旧常量按 E3PREP 独立手算更新，**严禁按实测反填**；仍红则报 blocked 附差异表） | **否** | defects 实测 status=OPEN（口径已裁、落实未完） |
| G-4 | D-A1-08 IMPUTE_MEDIAN 的中位数参考集 | 参考集口径未定（E3 的假设经覆盖矩阵证伪） | ATT-1 @`dce1ac5`：`compute(..., anchor_set=None)` keyword-only，anchor 优先、失效回退当期池并落 `RC.ANCHOR_SET_STALE`（WARN／blocks_run False） | 已闭合（ORCH-40 第3条） | 否 | 接线余点：golden_a:287／780→E2b、`spine:166`→A1d（**已由 A1d @`f27334d` 接上**，实测哈希 UNCHANGED，因 spine 评价期事实表完整不触发 IMPUTE 分支）、cli Step1→P2-wire |
| G-5 | D-A1-09 仓库级 `data/<period>/` + `config/` 布局 | A1DPREP 与 A1d 两侧实测**判定不需要**：`_stage(spine:120-131)` 早已按 [L888] 在 tmp_path 下产出 `config/*.csv` + `data/<period>/*.csv`，`io_loaders.py:274-279/314-320/301` 早已实现 | 无需处置（ORCH-41 第1条 R3 确认；A1d R3 复测证实后缀白名单 `:189-190`／`:274-279` 根本没触发，唯一抛错点是 `:270` 的 `MODEL_ROW_REJECTED`；同时撤销 E3PREP NEED-FIXTURES 第⑧条的风险前提） | 无（**已判定不需要**，非留空） | 否 | L888 的仓库级布局迁移仍不在本 RUN 范围（ORCH-38 第7条维持） |
| G-6 | D-D2-01 LOO 影响力排名产出物缺失 | [L748]／[L1409]／[L1450] 要求「每指标 LOO 影响力排名（主导指标清单）」，原实现只有 flip_rate 警示判据（全文「跨度／极差／span」0 次 → 算式属 derived） | LOO-1 @`858ebc8` 新增 `SensitivityReport.loo_impact: tuple[tuple[str, Ratio], ...] = ()`（带默认值，既有构造点零改动，ORCH-41 第3条硬约束） | 已闭合（ORCH-40 第7条改判「实现缺项、非测试过严」+ ORCH-41 第2条收口） | 否 | 实测 loo_impact_max = M_REV_MINOR 0.120000000000 与手算逐位相符（次高 M_CONTACT_FREQ_PER_30D 0.098323076923，唯一最大者无并列）；**出口面见 G-16** |
| G-7 | D-SEN-01 dominant 清单排序依据 | 按发现顺序而非影响力排序 | LOO-1 @`858ebc8` 改按 loo_impact 降序；flip_rate 警示判据保留为**独立字段**，二者并列呈现、不得合并或互相替代（ORCH-40 第7条） | 已闭合（ORCH-41 第2条） | 否 | g07 两条改前改后均 2 passed；`tests/test_sensitivity.py` 29 passed（22 旧 + 7 新）；`reproducibility_hash` 不变（`audit.py:242` 不消费 SensitivityReport） |
| G-8 | D-G14-01 `mix_quality_verdict` 无出口 | reports／cli 均未调用 → 「报告出现 MIX_QUALITY_DEGRADED 警示」永不成立（V-14 静默降级） | reports 面已闭合：G14FIX @`42d5346` 接入 `reports.py:419`（_section_6，[L1063]⑥）；cli 面 P2-wire-A @`53ed80c` 落了 seam `cli.py:406 _render_reports`，但**该 seam 目前没有生产调用点，只由测试驱动**（见 G-14） **【DOC-FINAL-B · CLOSED @`04cbe19`（M29-2，ORCH-59 六键口径）】**：三件套实测在位 —— ① **CLI 实跑 RC**：对照组（无上期基线）**RC=0**、实验组（带 WARN）**RC=0** ⇒ `UNCHANGED=True`（WARN 不阻断、不截断产物，七件齐／十段齐）；② **⑥ 段命中行**（[L1063]）逐字见本节末「G-8 关闭证据」代码块（`MIX_QUALITY_DEGRADED 一级库中 C 类证据占比上升，池质量退化（severity WARN，blocks_run=false，不中断 Step 7）`）；③ **交叉核对**：`pooling.mix_quality_verdict(cur, prev)` = `RC.MIX_QUALITY_DEGRADED`、`severity = WARN`、`blocks_run = False`、不在 `blocks_run_codes()` 内。全部为 **ORCH-69 主控亲测 @`a81730d`**（M29-2 实跑、主控复核唯一红归属）。 | P2-wire-B／主控（需 M29 九步 marshal 落地） | **否**（CLOSED @`04cbe19`；ORCH-63 目标值达成，阻塞由 11 降为 **10**；A 棒在本节上方所记「是／维持阻塞」与「M29-2 在飞」**保留为其写入时刻实况的历史追记**，不删不改写） | defects 实测 status=OPEN；MD 报告面已可见、**CLI 端到端面仍不可达** 【**DOC-FINAL-A（A 棒口径）**：`mix_quality_verdict` 的**六键披露口径已由 ORCH-59 预裁**（= NG-V12-20，契约 L1046 自指采六键、audit.json 自身 SHA256 走 `write_report_set` 返回值／CLI details 外部通道，**须在验收文档显式披露，不得静默**）；**M29-2 在飞未入 HEAD ⇒ 本棒不预填关闭证据**，G-8 维持「阻塞 = 是」；关闭证据三件套（CLI 实跑 RC、`report.md` ⑥ 段 `MIX_QUALITY_DEGRADED` 命中、对照组退出码逐字相等）待 **DOC-FINAL-B** 按最终 HEAD 实测填入。】 【**两条限定（不得只写「已关闭」）**：(1) 上期基线是经 `dsm/cli.py:_report_frames` 的**明文注入口**（P2-wire seam）构造的，因**真实数据面仍缺载体** —— `io_loaders.Inputs` 无 `previous_pool_stats` 字段、[L1051] 十六列无 `pool_stats` 列 ⇒ 生产 `report.md` ⑥ 段如实披露「本期不可比」；该载体缺位归 **v1.3**，并入 **NG-V12-19 同源说明、不新开码**。(2) 该实跑用的是**合法签认配置变体** `triangulation.enabled=false`（[L1022]「可关 → `TRIANGULATION_DISABLED`」）以隔离当时在飞的 B1／B2；B12-FIX `f213c1e` 落地后 `mean` 口径九步全通、七件齐备。对照组⑥段只有「本期**不可比** —— 无上期 pool_stats 基线」且**无**已触发判据行（缺基线也显式披露 = V-14 要求）。】 |
| G-9 | D-G14-02 G-14 分子／分母零原文依据 | 分子用 C+D（`LOW_EVIDENCE_CLASSES`）零依据，唯一明文 SDD L1416 写「C 类占比」；分母用四类合计且不剔 NOT_ASSESSED，与同模块两列 `share_*`（`pooling.py:424/425`）不同源 | G14FIX @`42d5346`：分子改 **C 类占比**（L1416 verbatim）、分母 `assessed_denominator()` 与 `share_*` 同源（L1004 负向排除 verbatim + 同源 derived）；阈值 `numeric.TOL` 一字未改、仅标工程默认（K-21）；不改 `LOW_EVIDENCE_CLASSES` 常量（它另承担 (C+D) 披露口径，被 g14 `:1692-1699` 与 `test_pooling:350/352` 钉住） | **CLOSED**（代码面 + golden 面均已闭合）：ORCH-40 第6条签认；`tests/test_golden_b.py` 由 7 红 → **0 红** @`0d8afeb` | 否 | 实测 PoolStats A3B3C3D2=11／NA=2／已参评 9；判据 3/9=0.333333333333 → 5/9=0.555555555556，Δ=2/9 > TOL 触发；g14 三条仍红归因 A1c 后过期的手算 expects → E3b |
| G-10 | D-DOC-01 本文件阻塞计数自相矛盾 | 汇总节自称 **19** 条，同文件逐条列举与逐行 grep（含 F-1／F-2 加粗「是」）均为 **24** 条 | **CLOSED**（P3c-pre2 @`d46bf48` 落地，P3c-final 复核）：按 ORCH-40／41／42 的关闭项扣减 + 新登记缺口，从正文逐条重新清点；汇总节由脚本与正文**同一数据源**生成；P3c-final 重新机械清点得 **65 行／flag「是」14**，与更新后汇总节逐字相等 | P3c-pre2 @`d46bf48` + P3c-final；`ops/dag-state.json` 的 defects 状态待主控翻转 | 否 | 验收条件「汇总数 == 正文逐条列举数」已回读自证（见汇总节）；顺带修复 `C-8` 行因未转义竖线导致的 9 列畸形（本包只做 escape-aware 解析与 flag 归位，**未改写其原有文字内容**） |
| G-11 | D-CLI-01 无 console script | `pyproject.toml` 无 `[project.scripts]` → SDD L805／L836 的 `dsm` 可执行入口未落成 | 唯一入口 `/home/szf/venvs/dsm/bin/python -m dsm.cli`（顶层 8 个 COMMAND：preflight／score／sensitivity／ahp／combine／fixtures／calibrate／whatif，其中 ahp／combine／fixtures 为二级组 → **叶子命令 8 条**，与 L1080-L1087 逐条对应；公共 6 参数 + `--schemes`；退出码 0／2／3／4／5／6／7） | 已接受并披露（ORCH-39 第3条，ACCEPTED-DISCLOSED）；本 RUN **裁定不补** | 否 | 理由=避免写集扩散到 `pyproject.toml` 并与 P2-cli／P2-wire-A 抢同一文件；README §5.1 与交付包 §1 第 12 项已如实披露 |
| G-12 | D-MODELS-02 `PoolStats` 缺「已参评主体的四类分布」载体 | 冻结契约无该列，G14FIX 提 3 个方案交主控裁（`dsm_stage/G14FIX/NEED-CONTRACT.md`） | 维持 reports 本地容器方案（`dsm/reports.py:108 AllFrames.previous_pool_stats`，ADJ-4），本 RUN 不改 `models.py` 的 `PoolStats` | 下一版本（ORCH-40 第6条，ACCEPTED-DISCLOSED） | 否 | 决定性理由=`models.py` 已由 LOO-1 获 R-15 单点授权做最小新增，再叠加会放大回归面且余量不足；本地容器已满足 V-14 披露 |
| G-13 | D-TOOLS-01 编码门禁作用域过宽 | `tools/normalize.py --check` 的 `targets()` 用 `os.walk(ROOT)`，含 gitignored 的 `dsm_stage/` → 现报 `NEEDS_NORMALIZATION 38 of 666`，抽样前 4 条全在 `dsm_stage/ADJ-G07/`（**假红**） | 权威口径（ORCH-42 第6条）：**四要素（UTF-8 strict／无 BOM／LF／源码无 TAB）全量硬失败 + 末尾 LF 只对「本次变更文件」断言**；受控文件（`git ls-files`，实测 189 个）四要素违规实测 **0**（BOM 0／CR 0／TAB 0／解码失败 0）；历史遗留 **17 个**缺末尾 LF（**ORCH-44 权威口径，@`da4d0a9` 须注明观测 HEAD**；ORCH-36 第11条的 20 与移交单的 22 **均作废**；其中 **9 个在 `dsm/**`／`tests/**`／`tools/**`**，清零需主控单独授权）**只披露不返工** | P2-wire-B（作用域收窄为 `git ls-files`；ORCH-41 第4条⑦明示可移交） | 否 | defects 实测 status=OPEN；门禁明文定义在 `docs/ORCH-TEMPLATE-v1.0.md:146`（H-G3）+ `docs/CONTEXT-BRIEF-v1.0.md:33` + `docs/RUN-UNATTENDED-v2.0.md:72` + `docs/adr/ORCH-21.md:130` |
| G-14 | **M29 九步 marshal（[L1330]-[L1358]）本体未落地**（本包新登记，dag-state 尚无缺陷号） | `dsm/cli.py:_chain_gate` 在模块齐全时仍 `raise InvariantError`（退出码 5），`_period_cases` 同样以此为由拒绝 → P2-wire-A @`53ed80c` 落的两个 seam（`cli.py:391 _report_frames`／`cli.py:406 _render_reports`）**目前没有生产调用点，只由测试驱动** | **不得写成「CLI 已可用」**：真实运行先被 `config.load_all()` 以 `EXIT_CONFIG=3` 拒绝（`config/` 实测 0 文件，设计如此非缺陷）；即便配置齐备也会在 marshal 处以退出码 5 拒绝 **【DOC-FINAL-A 追记 · CLOSED @`a432ef6`（M29-1）】**：判据两条已满足 —— ① 九步 marshal 本体落地（`git show --stat a432ef6` = `dsm/cli.py` +756／`tests/test_cli_marshal.py` +549）；② `_render_reports` 已有生产调用点。本棒 @`50fa9e0` 复测调用链锚点 = **`dsm/cli.py:953 → :959 → :1120 → :1129 write_report_set`**（`git show 50fa9e0:dsm/cli.py` 与 `a432ef6` 同值），`cmd_score` 成功路真实写出七件产物；旧 raise 串已删（`grep -c "chain modules are all present" dsm/cli.py` = **0**）。守护用例 = `tests/test_cli_marshal.py::test_nine_step_call_order_is_the_contract_flow_chart` / `test_chain_gate_returns_a_handler_triple_and_no_longer_refuses_a_full_tree` / `test_score_end_to_end_writes_ten_sections_five_tables_and_audit_json`。 | P2-wire-B／主控（需 A1c fixtures + Step1-8 编排，超出 45 分钟接线包） | **否**（CLOSED @`a432ef6`，转入非阻塞，**行保留在总账内**；v1.1 原记「是」与「两个 seam 无生产调用点」保留为历史） | ORCH-42 第2条明示为**阻塞级**缺口；依据 HANDOFF-P2 §2、INV-2（M00 L301：shell 不得内联任何一步）、[L1556] 一带的 CLI 要求；marshal 落地后 `frames = cli._report_frames(...)` → `cli._render_reports(run, bundle, frames, app)` 两个披露载体（`previous_pool_stats`／`evaluation_scope`）会自动接上，LOO 摘要也应挂在同一 seam 避免第二套输出 主控亲测（独立 clone @`a432ef6`，porcelain 0）：全量 **2418 passed / 0 failed**；`tests/test_cli_marshal.py` 定向 **17 passed**；**注意**：G-14 关闭**不等于** `output_fingerprints` 台账闭合（那属 G-8／NG-V12-20）；`ops/dag-state.json` 本棒未改。 |
| G-15 | **reason_code 接线待办**（CONSUMPTION-TODO 第 2／3模块侧／4／5／7／9 条，本包新登记） | 六个码**已在册**但消费点未落，原症状仍在：**#2** `preflight.py:320` 建索引前查重（`DESIGN_CARD_DUPLICATE_KEY`；违 M18 [L1102] T4 粒度=策略×版本，重复键静默取后一行可能把 MISSING 卡盖成 COMPLETE=V-14）；**#3 模块侧** `triangulation.py:380-388`／`:420-426` 把零方差的一对 rho 与 agreement 置 None 时未带 `SPEARMAN_ZERO_VARIANCE` 进 `report.flags`（下游只读 flags 会漏判）；**#4/#5** `weights_combine.py:683-690` 未按 violations 逐条 append H2／H3／H5_SHIFT（`ALPHA_INFEASIBLE` 留给「可行集为空」`L631`）、`:475-481` 红线指标排除出熵权组合时未逐指标披露 `REDLINE_EXCLUDED_FROM_ENTROPY`；**#7** `preflight.py:215-237` 的 C-03 仍沿用 `CONFIG_SEMANTIC_ERROR`，应换 `WEIGHT_DICT_MISALIGNED`（M22 [L902] 逐字 BLOCK）并同步 `RUN_BLOCKING_CODES(:36-40)`／`DISCLOSURE(:42-49)`；**#9** `attainment.py:524`（ZERO 合成行）／`:528`（SKIP）／`:532`（IMPUTE）的 `reason_code=None` 应改 `MISSING_FACT_RULE_APPLIED`（**不得**挪用 `MISSING_RATE_WARN`，其 message 绑定「缺失率超过预警阈值」，挪用即虚报） | 逐条归属（ORCH-42 第3条）：#2→A1c／C2b（唯一性更可能在 io／models 层落地）；#3→D4；#4/#5→A2b；#7→C2；#9→B1b／A1c。P2-wire-A 一律**未代改**（写集禁写），其对 `preflight.py` 的授权仅 209-211 等价性核验 **【DOC-FINAL-A 拆两段披露（ORCH-63 维持阻塞，不改判）】** ——（一）**已落地段**：`#2` 重复键出码 `DESIGN_CARD_DUPLICATE_KEY` + `#3` 零方差 Spearman 带码入 flags + 三角 verdict 静默补披露 = **RC-1 @`877b8fb`**（`dsm/preflight.py`／`dsm/triangulation.py`／`tests/test_reason_codes.py`，+319/-5）；`#4` 熵权组合逐条 append `H2/H3/H5_SHIFT` + `#7` C-03 换码 `WEIGHT_DICT_MISALIGNED`（含 `RUN_BLOCKING_CODES`／`DISCLOSURE` 同步）= **RC-2 @`dcb6f21`**（`dsm/preflight.py`／`dsm/weights_combine.py`／`tests/test_methods_combine.py`／`tests/test_preflight.py`，+77/-14）；`tests/test_reason_codes.py` 定向 **38 passed**（GATE-PRE `out/V14.log` 转录）。（二）**残留段（不得写成已闭合）**：`#5` 红线指标排除出熵权组合时未逐指标披露 `REDLINE_EXCLUDED_FROM_ENTROPY`、`#9` `attainment.py:524/:528/:532` 合成行 `reason_code=None` 未换 `MISSING_FACT_RULE_APPLIED` ⇒ 六处接线实测 **4/6**，残项登记 **NG-V12-19** 移交 v1.3（权威源 `ops/dag-state-v1.2.json` `carry_gaps_v12`）；换码处须复核 `tests/test_preflight.py:240`／`:451` 一致性断言，**不得弱化**（R-14）。 | P2-wire-B + 上述各归属包 | 是 | 换码后必须复核 `tests/test_preflight.py:240`（`all(f.code == C-03 and f.blocks_run)`）与 `:451` 的一致性断言，**不得弱化**；渲染侧披露位已由 P2-wire-A 落在 `reports.py:591-601`（⑧ 段 + `triangulation.md`）；依据 [L631]／[L62] D2 约束①／[L1140]／M18 [L1134]／M22 [L903]／M31 [L1411] G-09 四分支须各不相同 【ORCH-63 维持「阻塞 = 是」，本棒不得改判；V-14 四项齐备条件因本项不成立。】 |
| G-16 | LOO 影响力排名的出口面（三载体分别定性） | MD 面／CSV 面／CLI 摘要面三者状态不同，须分别披露，不得笼统称「已闭环」 | **MD 面已闭环**（P2-wire-A @`53ed80c` 第⑧项：`report.md` ⑦ 段渲染逐指标排名 + loo_impact_max + 「存在单一指标过度影响」文案，与 `loo_dominant_metrics` 并列呈现，`loo_impact` 为空元组时显式披露「本轮未执行 LOO」，数值 Decimal 原样不经 float）；**CSV 面本 RUN 不做**（ORCH-42 第4条：`reports.SENSITIVITY_COLUMNS` 13 列无 metric_id／loo_impact，把 metric_id 塞进 `strategy_id` 列会污染列语义，扩列即改**契约面表头**且 `tests/test_reports.py:355` 已钉表头，属契约变更而非接线，且 E2b／E3b golden 面在飞会引发不可控重写）；**CLI 摘要面**被 G-14 的 marshal 缺位挡住 | CSV 面：主控已裁本 RUN 不做，登记为 **K-32** 待签认；CLI 摘要面：随 G-14 | 否 | MD 面闭环即视为本 RUN 达标（ORCH-42 第4条）；V-5（契约列不得静默增删）风险已规避；接线后 `output_fingerprints` 必变、`reproducibility_hash` 不受影响 |
| G-17 | G-14 的**上期 PoolStats 载体缺位**（本包新登记） | `Inputs`（[L891]）无 `previous_pool_stats` 列、`AuditBundle`（[L1051] 十六列）无 `pool_stats` 列，而 `models.py` 属 MODELS-1／LOO-1 独占写集 | `_previous_pool_stats()` 现阶段只能返回 None，报告**显式披露「本期不可比」**（符合 V-14：不造假基线） | 主控裁（契约级变更）；本 RUN **不做**（ORCH-42 第5条） | 否 | 见 `dsm_stage/G14FIX/NEED-CONTRACT.md` 与 `dsm_stage/P2-wire-A/NEED-WIRING.md` 第 10 条；登记为 **K-33** 待签认 |
| G-18 | `loo_impact` 未补进 ORCH-22 契约表（K-25） | `docs/adr/ORCH-22.md` 裁决 25 的 `SensitivityReport` 字段表与 `docs/adr/ORCH-22-review-S1-T04.md:136` 对账表均无该字段 | P2-wire-A 已按主控指令**沿用 `loo_impact` 原名**、未自创别名；`docs/**` 属禁写面，本包亦无权改 | 主控（后续 ORCH 补录） | 否 | R-15 授权 + ORCH-22 契约表同步要求（LOO-1 NEED-WIRING 第 5 条） |
| G-19 | whatif 的 GEOMETRIC 近似归因本 RUN 不做（⚠️ **编号撞号**） | 派工单要求登记为 `D-A4-02`，但 `ops/dag-state.json → defects` **已存在** `D-A4-02`（`dsm/whatif.py:571` 裸字面量，status=CLOSED，fix_commit `9078201`）——两者不是同一件事 | 现状：`dsm/whatif.py` 非 LINEAR 一律抛 `WhatifOperatorError(CONFIG_SEMANTIC_ERROR)`，**不出近似归因**（G-A4-1）；`APPROXIMATE_ATTRIBUTION` 码已注册备用（见 B-7） | 下一版本；**编号请主控改号**（同 L-12：编号单点分配权在主控，本包不自占 `D-A4-02`） | 否 | 本包按派工单登记内容但不复用已 CLOSED 的同号缺陷，避免台账混淆 |
| G-20 | **CLOSED @CMB-1 `037b862`（DOC-FINAL 改判；原为全量 pytest 唯一残留红，P2-wire-B／P3b-FIX 均未跑全量故未发现）** `tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502 assert 8 == 9`） | 2026-Q3 完整策略数期望常量陈旧（曾使 **tag 前置 ①「0 failed」硬门禁不破**）→ 现 **① 满足**：全量 **0 failed／2302 passed／2302 collected**；独立推导链 **12 − 4 = 8** 见 §H-14 | 二分实测引入点 = A1c @`6299245` 的 D-A1-03（`M_COMPLAINT_RATE`→`M_SATISFY_SCORE` 载体迁移 + 同维对调 `missing_rule`，Q3 9→8），期望常量未同步；`cc18a38`／`dce1ac5` 绿、`6299245` 起红 | **CMB-1 @`037b862` 已落地**（写集仅 `tests/test_methods_combine.py`；`:502` 期望 `9→8` + `:482` docstring「only 9」→「only 8」+ 断言上方 5 行依据注释；删除 2 行、净断言 +0）；最小修法 = `:502` 9→8 + `:483` docstring 同步 + 附 D-A1-03 引文)；修法守 **禁** `>=`／区间／删断言／skip／xfail，未碰任何实现文件 | **否** | 追记（CLOSED @`037b862`）：P3c-final 实测 1 failed／2301 passed／2302 collected @`da4d0a9`（§H-1）；**终值：0 failed／2302 passed／2302 collected**（CMB-1 @`037b862`，观测工作树 `a396e0a`）；本包亲跑定向复核 `tests/test_methods_combine.py` = **22 passed in 0.67s**；闭合证据链 §H-14 |

## 汇总计数（**P3c-pre2 重算：与正文逐条列举同源生成，已回读自证相等**）

- 条目总数：**A 10 + B 10 + C 8 + D 7 + E 8 + F 2 + G 19 = 64 条**（脚本回读实测 64 行，与各节逐条列举数一致）。
- 「是否阻塞交付」= **是：16 条** —— C-1、C-2、C-3、C-4、C-5、C-6、C-8；E-6、E-8；F-1、F-2；G-2、G-3、G-8、G-14、G-15。【v1.2 指向：本节为 v1.1 中间态权威值，**保留为历史**；最新机械清点见 §G 之后「V12-DOC-FINAL-A 权威计数」追记（阻塞 11／非阻塞 54／合计 65 @`50fa9e0`）。】
- 「是否阻塞交付」= **否：48 条**（含本包按关闭依据改判的 A-10、B-1~B-5、B-7、B-8、D-1~D-6 共 15 行）。
- 其中**纯依赖行方签认**的：C-1~C-6、C-8、F-2，以及 K 清单全部 **35 个编号（K-01~K-35；含 K-21 的 5 个子项，共 39 个签认动作）**。K 项**不计入本表 64 行**，其阻塞性只通过 C 类与 F-2 体现，避免重复计数。
- **计数口径（ORCH-42 第7条）**：算「阻塞」= 该项未闭合会导致 ① `blocks_run=True` 的真实运行被拒，或 ② 触碰 V-9／V-14／V-6／G-02 红线（静默降级、算出而不披露、契约强制产出物对用户不可见、门禁未过而对外出分），或 ③ 使全量 pytest 无法转绿。**不**把 K-01~K-35 的编号总数当阻塞数，也**不**沿用 ORCH-39 的旧值 24。
- **D-DOC-01 验收自证**（可机械复核）：统计本文件中以 `| A-` … `| G-` 开头的表行数 = **64**；其中「阻塞交付」列为「是」的行数 = **16**，与上面两行汇总数**逐字相等**（本包以 escape-aware 解析回读实测；`C-8` 行内含转义竖线，按 7 列正确解析）。

### D-DOC-01 逐条清点表（原 24 项 → 现状 → 关闭依据 → 是否仍算阻塞）

> 「原计数项」= ORCH-39 第2条裁定的 24 条：A-10；B-2／B-3／B-4／B-5／B-7／B-8；C-1~C-6、C-8；D-1~D-6；E-6、E-8；F-1、F-2。

| 原计数项 | 原判「是」的理由 | 现状（本包实测／主控裁决） | 关闭依据（commit／裁决） | 是否仍算阻塞 |
|---|---|---|---|---|
| A-10（原24） |  D-MODELS-01 的 models.py／normalize.py 契约位未落  |  **CLOSED**（defects 实测 status=CLOSED）  |  MODELS-1 @`cc18a38`／ORCH-38 第1条  |  **否**（扣减）  |
| B-2（原24） |  卡索引重复 strategy_id×version 无专用码，现静默取后一行  |  码已注册（`DESIGN_CARD_DUPLICATE_KEY`，BLOCK，`reason_codes.py:142`）；HEAD `git grep` 实测 dsm/ 内零消费点  |  R15B2 @`db13471`（new_codes 实测）  |  **否**（本行扣减；接线残项移入 G-15，仍算阻塞）  |
| B-3（原24） |  Spearman 一方零方差无处置码  |  码已注册且 `reports.py` 有消费点；模块侧 `triangulation.py` 未把该码塞进 flags  |  R15B2 @`db13471`  |  **否**（本行扣减；残项移入 G-15）  |
| B-4（原24） |  标定 H-2／H-3／H-5 与红线排除无专用码  |  四码全部注册；`weights_combine.py:683-690`／`:475-481` 未逐条 append  |  R15B2 @`db13471`  |  **否**（本行扣减；残项移入 G-15，归 A2b）  |
| B-5（原24） |  一级库准入 grade≠L1 无专用码  |  码已注册且已接入 `pooling.py`（实测 5 处）+ `reports.py`  |  R15B2 @`db13471` + G14FIX @`42d5346`  |  **否**（扣减）  |
| B-7（原24） |  GEOMETRIC 近似归因码 `APPROXIMATE_ATTRIBUTION` 未注册  |  码已注册且 `whatif.py` 有消费点（3 处）  |  R15B2 @`db13471`  |  **否**（扣减；GEOMETRIC 本 RUN 不做 → G-19）  |
| B-8（原24） |  missing_rule 合成行无「已按规则处置」码  |  码已注册（`MISSING_FACT_RULE_APPLIED`，WARN，`reason_codes.py:151`）；`attainment.py:524/528/532` 仍 reason_code=None  |  R15B2 @`db13471`  |  **否**（本行扣减；残项移入 G-15，归 B1b／A1c）  |
| C-1（原24） |  Step7 占比双报两个分母口径为 C5 自裁、待行方签认  |  口径已权威化（ERRATUM-11：出桥 12／universe 11／G-14 分母 9），**签认动作仍未发生**  |  ORCH-41 第8条 + G14FIX @`42d5346`  |  **是**（保持）  |
| C-2（原24） |  `min_pool_size` 的 yaml 键位未签认（复用 normalize 块键）  |  未签认；`config/` 实测 0 文件  |  —  |  **是**（保持）  |
| C-3（原24） |  `impute_scope` 默认 ALL_ROWS 属代码拟定  |  未签认（ATT-1 只改中位数参考集优先级，未动本项默认）  |  ATT-1 @`dce1ac5` 不涉及本项  |  **是**（保持）  |
| C-4（原24） |  三角验证 `gra_norm`／`rho`／`divergence_threshold`／`enabled` 值与键名未签认  |  未签认（缺键抛 `MissingConfigError`，不猜）  |  —  |  **是**（保持）  |
| C-5（原24） |  标定 [L540] 边界 `epsilon`／`shift` 无原文值  |  未签认（缺失即抛，R-12 不猜数）  |  —  |  **是**（保持）  |
| C-6（原24） |  标定窗口期数下限（恰 2 期 vs RK-10 的 N<3 回退）未钉死  |  未签认，两机制并存  |  —  |  **是**（保持）  |
| C-8（原24） |  Saaty RI 表值／不一致度量口径／第四公式均属公开标准值或推断实现  |  G14FIX 的 5 条待签认项已逐条并入 **K-21①~⑤**（含现用工程默认 `1E-12`）  |  ORCH-42 第1条 + `dsm_stage/G14FIX/K-21-PROPOSAL.md`  |  **是**（保持）  |
| D-1（原24） |  D-SEAM-01：单例池 sd=0 不出 composite_relative + pooling 对 null 抛错，卡 G-01／G-02／G-04 与 spine×14  |  **CLOSED**  |  SEAM-1 @`8f2eca3`／ORCH-32+33 收口  |  **否**（扣减）  |
| D-2（原24） |  D-MODELS-01（同 A-10）  |  **CLOSED**  |  MODELS-1 @`cc18a38`  |  **否**（扣减）  |
| D-3（原24） |  D-A1-02：四张 DID 卡缺 `alt_method_note`，证据分布与 manifest 声明不符  |  **CLOSED**（主体级 A3B3C4D2／行级 A3B4C4D2 双口径入册）  |  A1c @`6299245`／ORCH-40 第5条  |  **否**（扣减）  |
| D-4（原24） |  D-A1-03：事实表 BLOCK 缺格载体错置致 `dsm/redline.py:330` 死锁  |  **CLOSED**（载体迁至 M_SATISFY_SCORE 并同维对调 missing_rule，g09 实测仍绿）  |  A1c @`6299245`／ORCH-37 第1条追认  |  **否**（扣减）  |
| D-5（原24） |  D-A1-04：权重文档缺 provenance 七键 → C-01 恒 BLOCK（**主流程唯一真阻塞**）  |  **CLOSED**；spine step2 走到 [L1322] 右支（A1d 实测 WARN／findings 5 条）  |  A1c @`6299245`／ORCH-30 第3条 C2b 三期真跑 + E3 GAP-E3-05 双来源印证  |  **否**（扣减）  |
| D-6（原24） |  D-A1-05：design_card 为 JSONL 而 io_loaders 只认 CSV／Parquet 且空串→None  |  **已落地**：A1d 按 ORCH-41 第1条 R2 的列级口径修（新增 `_required_text_columns()` 与 `TEXT_AS_IS_COLUMNS`），fixtures 零改动；spine 7 红 → 1 红  |  A1d @`f27334d`  |  **否**（扣减；剩余 1 红 A1d 实测归因归 G14FIX 写集，全量实测终值 1 failed／2301 passed／2302 collected @`da4d0a9`（P3c-final 亲测，15.48s））  |
| E-6（原24） | M00 L294 的 L0b 目标清单非穷尽（E5 GAP-E5-09 自标 BLOCKING，阻断 A3／A4 转绿） | **ORCH-62 改判非阻塞**：全量 0 failed 覆盖 A3／A4 两套件（关闭证据）；症状与 WORKAROUND 仍如实保留在 §E 的 E-6 行内（不删行）；原记「未见闭合裁决」→ 现闭合裁决 = ORCH-62 | 主控裁决 ORCH-62（`ops/dag-state-v1.2.json`） | **否**（ORCH-62 改判；重开条件 = 后续 L0b 新模块再需清单外的边须登记**新缺口**，不得沿用本裁定） |
| E-8（原24） |  Step8(sensitivity) 在 Step7(pooling) 之后 → FLIP_RATE_UNUSABLE 首过必然无载体  |  **CLOSED**：ORCH-43 裁「GRADE 先于 ROBUST」为权威口径（契约 §3.6.3 L1002 枚举序 + L1006 要求 ROBUST 须可被测试真实覆盖）→ G14FIX 的定序**不是缺陷**、A1d 保持红不弱化**正确**；ROB-1 以「真实载荷分布钉死 GRADE6／EVIDENCE4／D2／ROBUST0 + 合成 X-ROB 有无对照」收口，**强度高于原 `assert robust`**  |  ROB-1 @`111570a`／ORCH-43  |  **否**（扣减）  |
| F-1（原24） |  **G5** D6 证据复核未完成 → 复核前全面禁用（M39 L40／SDD L1792）  |  未完成，本 RUN 无复核产物；代码侧与之相容（未验证载体一律显式异常）  |  依赖行方／D6 复核方  |  **是**（保持）  |
| F-2（原24） |  **G7** 治理配置未签认 → K 项全部未脱 PLACEHOLDER（M39 L42／SDD L1794）  |  未完成且**无载体**：`config/` 实测 0 文件，真实运行被 `EXIT_CONFIG=3` 拒绝（**设计如此，非 bug**）  |  依赖行方（评价管理委员会）  |  **是**（保持）  |

**扣减合计 14 行**（A-10；B-2／B-3／B-4／B-5／B-7／B-8；D-1／D-2／D-3／D-4／D-5／D-6；**E-8**）→ 原 24 − 14 = **10 行保持阻塞**（C-1~C-6、C-8；E-6；F-1、F-2）。其中 B 类 6 行属「注册面闭合、接线残项移入 G-15」，D-6 属 A1d 已落地，**E-8 属 ORCH-43 裁口径 + ROB-1 @`111570a` 收口**。【v1.2 指向：本行为 P3c-pre 时点口径，**保留为历史**；最新清点见「V12-DOC-FINAL-A 权威计数」追记。】

### 新增阻塞项（P3c-final 重算：G 节 6 条中 4 条仍阻塞）

| 新增项 | 为什么算阻塞 | 归属 |
|---|---|---|
| G-2（新增） |  D-A1-06 的 golden 手算值不自洽（1.900000／1.5346 vs 手算 1.810000000000／1.507600000000）→ 全量无法转绿  |  E2b  |
| G-3（新增） |  D-A1-07 的陈旧常量未按 E3PREP 独立手算更新 → golden_b 无法转绿（口径已裁、落实未完）  |  E3b  |
| G-8（新增） | `MIX_QUALITY_DEGRADED` 在 CLI 端到端面仍不可达（seam 无生产调用点）→ V-14「算出而不披露」未全闭合 ⇒ **v1.2 实况（本棒复测）**：「seam 无生产调用点」自 M29-1 `a432ef6` 起过期（`dsm/cli.py:959` 已是生产调用点，本棒 `git show 50fa9e0:dsm/cli.py` 复验）；但 **CLI 实跑的 ⑥ 段警示 + 六键 `output_fingerprints` 台账尚未实测** ⇒ G-8 **维持阻塞**，归属 M29-2／主控（在飞）。原句保留为历史。 ⇒ **DOC-FINAL-B：已关闭 @`04cbe19`**（三件套 + 六键台账 + ⑥ 段命中行逐字见 §G 本节末「G-8 关闭证据」；**ORCH-69 主控亲测 @`a81730d`**）。A 棒的「维持阻塞」句保留为历史。 | M29-2／主控（**已闭合 @`04cbe19`**；V1.3 残留面 = 上期 `pool_stats` 数据载体，归 NG-V12-19 同源） |
| G-14（新增） | **M29 九步 marshal（[L1330]-[L1358]）本体未落地**：`_chain_gate` 在模块齐全时仍 raise InvariantError（退出码 5），CLI 端到端不可用，触碰 INV-2（M00 L301） ⇒ **已随 M29-1 `a432ef6` 关闭**：调用链 `dsm/cli.py:953 → :959 → :1120 → :1129 write_report_set`（本棒复测），旧 raise 串 grep = 0 命中；「CLI 端到端不可用」自该 commit 起过期（保留为历史）。 | M29-1／主控（**已闭合 @`a432ef6`**） |
| G-15（新增） | reason_code 接线待办 6 条未落 → 重复键静默取后一行、C-03 沿用泛码、合成行 reason_code=None 等**静默降级**症状仍在（V-14） ⇒ **DOC-FINAL-A 追记（ORCH-63）**：6 条中已落 **4 条**（RC-1 `877b8fb` 之 #2/#3 + RC-2 `dcb6f21` 之 #4/#7），**残留 #5／#9 未接 ⇒ 六处接线 4/6**，V-14 四项齐备条件不成立 ⇒ **仍算阻塞**（**ORCH-63 维持「是」，不得改判**）；原症状列举保留为 v1.1 历史。 | P2-wire-B(2/2) + A1c／C2b／A2b／C2／B1b／D4 ；已落地段 = RC-1／RC-2，残留段 = **NG-V12-19 → v1.3** |
| G-20（**P3c-final 新登**） |  全量 pytest 唯一残留红 `tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502` `assert combined.entropy.strategy_count_by_period['2026-Q3'] == 9` 实测 **8**）→ **tag 前置 ①「0 failed」硬门禁不破**，发布链路阻塞 | A1c @`6299245` 引入（本包 `git archive` 二分实测：`cc18a38`／`dce1ac5` **绿** → `6299245` 起 **红**，此后 `f27334d`／`31eb1b2`／`93abfee`／`da4d0a9` 六个 HEAD 均红）；归因待主控裁（A1c 提交信息自述「新增红 10 条逐条归因、允许仍红 6 条」，但**未逐条列出清单**，本包无法判定该条是否在其允许面内 → 不替它定性）|

**G-2／G-3 转 CLOSED**：G-2（D-A1-06 golden 手算值不自洽）由 E2b @`31eb1b2` 把 hand 校正落进 `tools/gen_golden.py` 后**重生成** `golden_map.json` 闭合（`golden_a` + fixtures 定向 36 passed／0 failed 实测）；G-3（D-A1-07 陈旧常量）由 E3b @`0d8afeb` 独立手算更新闭合（`golden_b` 7 红 → **0 红**，16→18 条，assert 62→72）。**二者不再计入阻塞**。

**P3c-final 权威计数 = 10（原 24 中保持）+ 4（G 节仍阻塞：G-8／G-14／G-15／G-20）= 阻塞 14 条；非阻塞 51 条；合计 65 条。**

**DOC-FINAL 权威计数 = 10（原 24 中保持）+ 3（G 节仍阻塞：G-8／G-14／G-15）= 阻塞 13 条；非阻塞 52 条；合计 65 条。**（G-20 已 CLOSED @CMB-1 `037b862`，按「CLOSED 行仍留在总账内计为非阻塞」的既有口径从阻塞转入非阻塞，故合计不变；上一版 14／51 **保留为追记**，不改写。）

> **V12-DOC-FINAL-A 权威计数（观测 HEAD `50fa9e0`；本节为**追记**，上方 v1.1 的 13／52／65 与更早的 14／51 一律保留为历史，不改写）**
>
> **机械清点（唯一权威口径，与正文逐条同源）**：命令 `/home/szf/venvs/dsm/bin/python dsm_stage/V12-GATE-PRE/out/count_gaps.py docs/deliverables/KNOWN-GAPS.md`；下方两行为该脚本输出的**转录**（OTHER 内每条的 flag 串按前 20 字符截断显示，完整输出请自跑该命令），非手工清点：
> `ROWS= 65 YES= 9 NO= 48 OTHER= [(E-6, **否**), (E-8, **否**), (F-1, **是**), (F-2, **是**), (G-2, **否**), (G-3, **否**), (G-14, **否**), (G-20, **否**)]`
> `YES_IDS= [C-1, C-2, C-3, C-4, C-5, C-6, C-8, G-15, G-8]`
>
> 该脚本只把「是否阻塞」列**逐字等于** `是`／`否` 的行计入 YES／NO，其余进 OTHER ⇒ 归并规则（列级解析口径，与 GATE-PRE 一致）：**阻塞 = YES 9 + OTHER 中以 `**是**` 打头的 F-1／F-2 共 2 = 11 条**；**非阻塞 = NO 48 + OTHER 中以 `**否**` 打头的 E-6／E-8／G-2／G-3／G-14／G-20 共 6 = 54 条**；**合计 65 条**（`ROWS` 逐字相符）。
> 逐条列举（阻塞 11）= C-1、C-2、C-3、C-4、C-5、C-6、C-8、F-1、F-2、G-8、G-15。
>
> **变化依据（每条给关闭／改判出处，非削弱披露）**：−E-6【**ORCH-62** 改判：全量 0 failed 覆盖 A3／A4，行／事实／WORKAROUND 全保留，重开条件已写入 §E 行内】、−G-14【**CLOSED @M29-1 `a432ef6`**：九步 marshal 本体落地 + `_render_reports` 生产调用点（本棒复测 `dsm/cli.py:953 → :959 → :1120 → :1129 write_report_set`；`grep -c "chain modules are all present" dsm/cli.py` = 0），主控独立 clone 实测 2418 passed／0 failed + `tests/test_cli_marshal.py` 定向 17 passed】；**G-8 依 A 棒口径维持阻塞**（M29-2 在飞未入 HEAD，六键口径已由 ORCH-59 预裁 = NG-V12-20，关闭证据待 B 棒实测）；**G-15 依 ORCH-63 维持阻塞**（残项 #5／#9 = NG-V12-19 → v1.3）。
> **A 棒 → B 棒追记**：M29-2（G-8 三件套）与 B12-FIX（NG-V12-27／28）落地并进入最终 HEAD 后，**由 DOC-FINAL-B 以同一命令重算**并追加新一节；本棒**不预填**其结果。上一版 13／52／65 保留为追记，不改写。
> 旁证（不可当权威，本棒实测）：`grep -c "^|" docs/deliverables/KNOWN-GAPS.md` 含跨节表头／分隔行，**不等于 65**，故一律走列级解析。

> **V12-DOC-FINAL-B 权威计数（观测 = 内容面最终 HEAD `a81730d`；ORCH-69／ORCH-68 主控亲测后落笔）**
>
> 命令 `/home/szf/venvs/dsm/bin/python dsm_stage/V12-GATE-PRE/out/count_gaps.py docs/deliverables/KNOWN-GAPS.md` 实测输出（本棒落笔后重跑，与正文逐条同源）：
> `ROWS= 65 YES= 8 NO= 48 OTHER= [(E-6, **否**), (E-8, **否**), (F-1, **是**), (F-2, **是**), (G-2, **否**), (G-3, **否**), (G-8, **否**), (G-14, **否**), (G-20, **否**)]`
> `YES_IDS= [C-1, C-2, C-3, C-4, C-5, C-6, C-8, G-15]`
>
> 归并规则同上（脚本只认逐字 `是`／`否`，余进 OTHER）：**阻塞 = YES 8 + OTHER 中 `**是**` 打头的 F-1／F-2 = 10 条**；**非阻塞 = NO 48 + OTHER 中 `**否**` 打头的 E-6／E-8／G-2／G-3／G-8／G-14／G-20 共 7 = 55 条**；**合计 65 条**。
> 逐条列举（阻塞 10）= C-1、C-2、C-3、C-4、C-5、C-6、C-8、F-1、F-2、G-15。
>
> **变化依据（每条给出处，非削弱披露）**：−G-8【**CLOSED @`04cbe19`（M29-2，ORCH-59 六键口径）**：CLI 实跑 RC 对照组 0／实验组 0（`UNCHANGED=True`）+ `report.md` ⑥ 段 `MIX_QUALITY_DEGRADED` 命中行逐字 + 交叉核对 `blocks_run=False` 且不在 `blocks_run_codes()`；三件套全文见本节末「G-8 关闭证据」；**ORCH-69 主控亲测 @`a81730d`**】。**G-15 依 ORCH-63 维持阻塞**（4/6，残项 #5／#9 = NG-V12-19 → v1.3；上期 `pool_stats` 数据载体缺位亦并入该条同源说明，**不新开码**）。E-6／G-14 的 A 棒改判**未回退**。**ORCH-68 的 B4 不新增 A~H 总账阻塞**（登记为 §I 的 NG-V12-29，`initial` 口径阻塞／`mean` 口径不阻塞）。
> **历史链（逐字保留为追记，不改写）**：24（ORCH-39）→ 16／48／64（P3c-pre2）→ 14／51／65（P3c-final）→ **13／52／65（v1.1 DOC-FINAL）** → **11／54／65（DOC-FINAL-A @`50fa9e0`）** → **10／55／65（DOC-FINAL-B @`a81730d`，本值）**。
>
> **§I 移交台账小计（B 棒刷新，与总账分列）**：13 行（NG-V12-19…31）。其中 CLOSED = NG-V12-27／28（@`f213c1e`）；独立新增阻塞事实 = **NG-V12-29**（仅对 `initial` 口径）；NG-V12-30／31 非阻塞；NG-V12-19 与 §G 的 G-15 同一事实。**PH-22 口径已由主控裁定**：§I 不入合计 65。

### G-8 关闭证据（ORCH-69 主控亲测 @`a81730d`；逐字转录，禁手抄改写）

`report.md` ⑥ 段命中三行（契约 [L1063]，逐字）：

```text
- G-14 C 类占比（分子 = C 类计数，[L1416]；分母 = 已参评数，与占比双报 share_* 同源、按 [L1004] 剔除 NOT_ASSESSED）：0.400000000000
- G-14 上期 C 类占比：0.300000000000 -> 本期 0.400000000000；判据阈值 1E-12 为**工程默认、非业务签认值**（PLACEHOLDER：建议新立 K-21）
- G-14 判据结论：**MIX_QUALITY_DEGRADED** 一级库中 C 类证据占比上升，池质量退化（severity WARN，blocks_run=false，不中断 Step 7）
```

- 交叉核对：`pooling.mix_quality_verdict(cur, prev)` = `RC.MIX_QUALITY_DEGRADED`；`severity = WARN`；`blocks_run = False`；不在 `blocks_run_codes()` 内。
- 对照组（无上期基线）⑥ 段只有「本期**不可比** —— 无上期 pool_stats 基线」，**无**已触发判据行 ⇒ 缺基线也显式披露（V-14 无静默降级要求成立）。
- **PH-21 两口径必须并写**（禁止只写 RC=0 造成「开箱即用」的错觉）：签认 `gra_norm=initial` → **RC=5**（= B4／NG-V12-29，错误原文 `TriangulationError: GRA 无量纲化参考值为 0（gra_norm=initial），关联度未定义`）；签认 `mean` → **RC=0** 且七件产物齐备（`audit.json`、`entropy_diagnostic.csv`、`grade_ledger.csv`、`report.md`、`score_card.csv`、`sensitivity_report.csv`、`triangulation.md`）。

- **计数口径（本轮沿用并在正文注明）**：阻塞 = `blocks_run=True` **或** 触碰 V-9／V-14／V-6／G-02 红线；非阻塞 = 已有排定修复包、已 CLOSED、或仅文档／签认待办。CLOSED 行**仍留在总账内**计为非阻塞（与 P3c-pre2 同口径），故合计由 64 → **65** 只反映 G-20 一条新增，不因闭环而减少。
- **变化分解**：阻塞 16 → **14**（−E-8 −G-2 −G-3 +G-20）；非阻塞 48 → **51**；合计 64 → **65**。
- **机械自证**（§H-6 命令）：追记 P3c-final 实测 正文表格行 **65**、flag「是」**14**；**DOC-FINAL 亲跑同一口径实测 = 正文表格行 65／flag「是」13／flag「否」52**，与本节「DOC-FINAL 权威计数」逐字相等（D-DOC-01 的验收条件在 DOC-FINAL 复核下仍成立）。

- SP-1 台账 21 条中 BLOCKING 7 条、SP-2 wave 新增缺口 70 条（计数实测于 dag-state）：本表收录其**未闭合且有裁决记录**的部分；各包 GAPS 全文按 SP2 note 只存在于 lane 会话／上报行，状态文件不重复存。
## H. P3c-final 定稿节（最终数字实测 + 台账定稿 + 计数自证）

> 本节所有数字均为 **P3c-final 本包在 HEAD `da4d0a9` 上亲自跑命令测得**（2026-11-25 09:04~09:22；观测 worktree 仅 1 个非本包脏文件 = `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`，属 P3a-final 在飞，不在 `dsm/**`／`tests/**`／`fixtures/**` 内，不影响 pytest 结论）。未测得的一律保留 PLACEHOLDER。

### H-1 最终全量 pytest（刷新 ①）

| 项 | 值 | 命令 |
|---|---|---|
| 统计行 | **1 failed, 2301 passed**（collected 2302）in 15.48s @`da4d0a9` | `/home/szf/venvs/dsm/bin/python3 -m pytest -o addopts= -q -p no:cacheprovider --tb=no -rfE` |
| 0-failed 门禁判定 | **未满足**（1 ≠ 0）→ **不得打 tag**；tag 前置 ① 是硬门禁，ORCH-44 明文**不得放宽** → 最终值登记为 `**`2444 passed in 20.67s`**（门禁① 标准形式，**ORCH-69 主控亲测 @`a81730d`**：独立 clone、porcelain 0、rc=0、`grep -c '^FAILED'` = **0**；第二形式 `-m pytest --continue-on-collection-errors -o addopts= -q` = **`2444 passed in 17.28s`**、rc=0；账目自洽 = `a432ef6` 基线 2418 + M29-2 新增 8 + B12-FIX 新增 18 = **2444**；v1.1 的 CMB-1 终值 2302 @`037b862` 保留为历史）` | 同上 |
| 主控归因与最小修法（ORCH-44 第1条） | 红因 = A1c @`6299245` 依 **ORCH-37 第1条追认（D-A1-03）** 把 BLOCK 缺格载体由 `M_COMPLAINT_RATE`（HARD 红线）迁至 `M_SATISFY_SCORE` 并同维对调 `missing_rule` → 2026-Q3 完整策略数 **9 → 8**，而 `:502` 期望常量未同步（独立复核：`metric_fact` 896 行／15 指标，Q3 = 8、其余四期各 12、SUSPECT 0）。**最小修法**：`:502` 的 `9 → 8` + `:483` docstring「keeps only 9」同步 + 附 D-A1-03 引文；**禁止** `>=`／区间／删断言／skip／xfail | 已派 **CMB-1**（写集仅 `tests/test_methods_combine.py`） |
| 唯一残留红 | `tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`，`tests/test_methods_combine.py:502`：`assert combined.entropy.strategy_count_by_period['2026-Q3'] == 9` 实测 **8** | `pytest tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures` |
| 引入点（二分实测） | `git archive` 导出到 `/tmp` 后单测该节点：`cc18a38` **绿**／`dce1ac5` **绿**／`6299245`(A1c) **红**／`f27334d` **红**／`31eb1b2` **红**／`111570a` **红**／`93abfee` **红** → 归 **A1c @`6299245`** | `git archive <sha> \| tar -x -C /tmp/p3cf_attr/<sha>` |
| 工装侧误读风险 | P3b-FIX 签核日志里的「`pytest_assertion = rc=0`」**只覆盖 `tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs` 这一个节点**（`tools/repro_offline.sh:293-295`），**不是全量转绿** | `grep -n "pytest -q" tools/repro_offline.sh` |
| 方法学附注 | 同一提交用 `git archive` 导出跑全量得 **12 failed**，多出的 1 条是 `tests/test_config_placeholder.py::test_t05_m04_the_repository_config_directory_stays_empty`，在真实仓库单测 **1 passed** → 系 `git archive` 不落空目录 `config/` 所致，**不是仓库红**；故基线对照一律以工作树为准 | `pytest tests/test_config_placeholder.py::test_t05_m04_the_repository_config_directory_stays_empty` |

**原 11 红的逐条拆分（刷新后 = 全部转绿，无需再拆分）**：基线 `after_MODELS1` = 11 failed／2190 passed／2201 collected @`cc18a38`。本包在 `/tmp` 的 `cc18a38` 导出树重跑并逐条点名，11 条为：
`test_golden_a::test_g04_target_missing_caps_grade_to_l3_for_every_k06_candidate`、`test_golden_a::test_g08_version_change_marks_break_suppresses_trend_and_resets_streak`、`test_golden_b::test_g05_appended_extreme_strategy_leaves_existing_norm_composite_grade_unchanged`、`test_golden_b::test_g06_at_least_one_near_boundary_strategy_flips_to_l3`、`test_golden_b::test_g07_loo_impact_max_is_the_dominant_weight_metric_m_rev_minor`、`test_golden_b::test_g10_sust_dimension_emptied_must_block_preflight`、`test_golden_b::test_g14_mix_quality_degraded_warning_fires_when_c_share_rises`、`test_integration_spine::test_step1_io_loaders_loads_the_frozen_design_card_table`、`test_integration_spine::test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures`、`test_integration_spine::test_step3_evidence_covers_the_m34_a3b3c4d2_distribution`、`test_integration_spine::test_step4_redline_runs_on_the_frozen_eval_period_fact_table`。
**新红登记**：唯一红 `test_build_draft_on_the_frozen_a1_fixtures` 由 A1c @`6299245` 的 D-A1-03 载体迁移引入（见 §H-1 归因行），已派 **CMB-1** 收口 → **G-20**。

**闭合归属**：spine step1~4 → A1d @`f27334d`（7 红→1 红）+ ROB-1 @`111570a`（1 红→**0 红**，22 passed／0 failed）；golden_b 全 5 条 → E3b @`0d8afeb`（7 红→**0 红**，16→18 条，assert 62→72）；golden_a 2 条 → E2b @`31eb1b2`（`golden_a` + fixtures 定向 **36 passed／0 failed**）。
→ **原 11 红已全部闭合**；当前 1 红是**另一条从未被任何包上报的红**（新登 G-20，见下），二者不得混为一谈。

### H-2 `reproducibility_hash` 台账定稿（ORCH-44；刷新 ②）

- **权威值 = `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（本包实测复述，非转录）。
- 台账（**只追加、严禁修回**）：`8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` → `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7`（`superseded_by_A1c`）→ `e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d`（@A1c）→ **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（@`42d5346`；**复测同值于 `0d8afeb`／`31eb1b2`／`93abfee`／`da4d0a9`**）。
- **本包亲自复测**：`bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --keep --strict-isolation` → **exit 0**、`RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=da4d0a9 ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=1 HEAD_STABLE=yes ASSERTION=pytest`；`netns_probe = offline-confirmed`、`clone_head = da4d0a9096d1bd6fd9dc77846b471ae9d96cfce7`（commit-exact，`src_dirty_files = 1` 已如实标注）。
- **`f437c0ead77b68c47c255db5b1b602c504da9efb9cda6a466e37c5020a6d71f8` 的定性（ORCH-44 更正，覆盖上一版派工单写法）**：**不是**权威哈希、**不入台账**；它是 ROB-1 在 spine 测试函数内把自包含合成载荷 X-ROB 计入链路产物后**自行测得的 non-canonical 值**。权威哈希来自 `tools/repro_offline.sh` 自己的离线探针（`:243` 起 probe、`:261` 取 `res['reproducibility_hash']`、`:294` 另跑 spine 多产物自等、`:362` 输出 `RESULT=... HASH=$FIRST`），**与测试内合成用例解耦**，故「测试新增合成载荷会漂移权威哈希」这一担忧**不成立**。→ 登记为 `K-SIGNOFF-CHECKLIST.md` **K-36**。
- 同值的原因链（保持披露）：`audit.py:242` 只吃 score_card／grade_ledger／weight_version_id；spine 评价期 2026-Q2 事实表完整 180 = 12×15，`IMPUTE_MEDIAN` 不触发 → A1d／P2-wire-A／ROB-1／P2-wire-B 四次落地后哈希**同值**，属实测而非巧合。
- **`output_fingerprints` 实测为「spine 面不可观测」（ORCH-44 第4条）——不得写「已变更」**：`bundle.output_fingerprints` 实测 = **`{}`（空）**；七件产物指纹的真实出口是 `reports.write_report_set`，而该 seam **无生产调用点**（M29 marshal 未落地）。P2-wire-B 已实算七件 **sha256[:16]**：`report_md 102d2d973c949ef2`／`score_card_csv bf583dc0da2da0a6`／`grade_ledger_csv 7afe10893ff2d366`／`sensitivity_report_csv 219b0880ff44d67f`／`triangulation_md ec8733e1f1b15ded`／`audit_json b81016fbd1eea897`／`entropy_diagnostic_csv 98207523a05e569f`。载体定义 `dsm/models.py:1247`（file → SHA256，[L1051] 第10项）。**缺什么**：CLI 端到端跑通后由主控把生产产物的 64 位值写进 `ops/dag-state.json → reproducibility_evidence`（`ops/**` 属本包禁写面）。

### H-3 ratchet 白名单实测（刷新 ③）

- **32 → 28 对**（P2-wire-B @`93abfee`），本包**独立复跑** `tests/test_architecture.py` = **11 passed／0 failed**。
- **失效对清单（4 条，全在 `dsm/fixtures_gen.py`）**，归因 = A1b @`0547190` 把裸字面量换成注册表符号：`('fixtures_gen','MONEY_NON_INTEGER')`←`:537`、`('fixtures_gen','REDLINE_HARD_M_COMPLAINT_RATE')`←`:363`、`('fixtures_gen','REDLINE_HARD_M_CONTACT_FREQ_PER_30D')`←`:360`、`('fixtures_gen','REDLINE_SOFT_M_OPTOUT_RATE')`←`:366`。
- fresh（白名单外新碰撞）**0**；stale **4 → 0**（4 条陈旧 allowance 已从白名单剔除，剔除后白名单 == 实际碰撞集，逐对相等）。
- **收紧方向核实**：新增 `COLLISION_INVENTORY_CEILING = 28` + 守护断言 `pairs <= CEILING` → 白名单增长直接红，只能由主控带书面理由抬高。P3c-final 复核确认这是**收紧不是弱化**：失效的 allowance 是 ratchet 上的洞，留着等于允许把 4 个码手写回去而测试不响。

### H-4 编码门禁 `tools/normalize.py --check` 实测（刷新 ④；K-35 数目校正）

- 命令 `python3 tools/normalize.py --check` → **exit 1**，关键四行输出逐字：
  `SCOPE git ls-files: 189 controlled files; gitignored scratch (dsm_stage/ ...) is NOT scanned (D-TOOLS-01)`；
  `FOUR_ELEMENTS UTF8_STRICT/NO_BOM/LF_LINE_ENDINGS/NO_TAB asserted on all 189 controlled files; TRAILING_LF asserted on the 1 changed file(s) only`；
  `NEEDS_NORMALIZATION 1 of 189 files` → 唯一硬失败 = `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md TRAILING_LF`（**P3a-final 在飞文件，本包禁写**）；
  `DISCLOSURE TRAILING_LF_HISTORICAL 17 of 189`。
- **本包另做逐字节独立实测**（对 `git show HEAD:<path>` 的 blob 判 `endswith(b"\n")`）：受控 **189** 文件；四要素违规 **0**（非 UTF-8 0／BOM 0／CRLF 0／TAB 0）；**缺末尾 LF = 18 个 blob**（含 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`，该文件 P3a-final 在飞、按 ORCH-42 口径计入「变更文件硬失败」而非历史披露，故门禁披露数为 17）；构成：
  `docs/**` 9 个（`docs/adr/ORCH-19.md`、`docs/adr/RUN-A1c-fixtures-controlled-thaw.md`、`docs/deliverables/P3b-REPRO-HARNESS.md`、`docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`、`docs/digest/S1-T01.md`、`S1-T01b.md`、`S1-T01c.md`、`S1-T01d.md`、`S1-T01e.md`）＋ `dsm/**` 3 个（`diagnostics.py`／`triangulation.py`／`whatif.py`）＋ `tests/**` 5 个（`test_diagnostics.py`／`test_golden_a.py`／`test_methods_whatif.py`／`test_sensitivity.py`／`test_triangulation.py`）＋ `tools/repro_offline.sh` 1 个。
- **与门禁自报 17 的差额 = 1**：`V-ACCEPTANCE-EVIDENCE.md` 因是「本次变更文件」被计入硬失败而非历史披露 → **18 = 17 披露 + 1 硬失败**，两套口径自洽。
- **⚠️ 数目更正（ORCH-44 第2条覆盖派工单转录与 ORCH-36 第11条）**：**20 与 22 均作废**；权威值 = **17（@`da4d0a9`）** = 本包 blob 实测 18 − `V-ACCEPTANCE-EVIDENCE.md` 1（计入变更文件硬失败）。**清零其中 9 个非 `docs/**` 文件需主控单独授权**（P2-wire-B GAP ③）。P2-wire-B 的两次实测（21 @`5d13ef3`／17 @`d46bf48`）与本包实测构成一致的**下降轨迹**（P3c-pre2 @`d46bf48` 补齐了本包文档的末尾 LF）。**「全在 `docs/**` 与 `README.md`」一句被实测证伪**：18 个里有 **9 个在 `dsm/**`／`tests/**`／`tools/**`**，全部落在本包与 P2-wire-B 的**禁写面**内 → 只披露不返工（V-14）；`README.md` **不在**名单内。
- `--check` 原报 `NEEDS_NORMALIZATION 38 of 666` 确认为 gitignored `dsm_stage/` 假红，已由 P2-wire-B 收窄到 `git ls-files` 消除（**D-TOOLS-01 闭合**）。

### H-5 `manifest.json` 的 golden_map 指纹（刷新 ⑤，E2b 移交项闭合）

- 本包自算 `fixtures/golden/golden_map.json`：**bytes = 24330**、**sha256 = `27c12b3e15aad3e7a147ac99a7d9e598b0b8fc65a44f14f8554dafa53dd39cfe`**。
- `fixtures/manifest.json` 现登记值与之**逐字相等**（P2-wire-B @`93abfee` 刷新）→ 原 stale 指纹（bytes 22130／sha 前缀 `dcfffd6a657b`）**已消除**，E2b 移交项闭合。

### H-6 发布数字与计数自证（刷新 ⑥）

- `git rev-list --count origin/main..HEAD` = **59**（DOC-FINAL 亲测 @`037b862`，`origin/main` = `3616f9722213f6da2cb0b4ff6fcf55cd947ed648` 已实测为 HEAD 祖先 → push 为 fast-forward；追记 54 @`da4d0a9` → 57 @`66481b1`；本包提交后为 60，push 前由主控重测）；P3C-draft 的 **34 作废**；本包提交后须由主控再重测）。
- `git tag -l` = **0 条**；`v1.1.0` 不存在，由主控执行（R-13）。
- 计数自证与本包实测输出：正文表格行 **65**、flag「是」**14** → 与「最终权威计数」节逐字相等（**D-DOC-01 验收条件在 P3c-final 复核下仍成立**）。
- `ops/dag-state.json → defects`／`errata`／`orch_lessons` = **27／11／12**（转录；`ops/**` 属本包禁写面，状态翻转归主控）。
- `reason_code` 注册数 **91**。

### H-7 ERRATUM-12 两套载荷计数（**严禁混用、严禁互相标 superseded**）

| 载荷 | 主体级 | 行级 | 池级 universe | NOT_ASSESSED | 已参评（G-14 分母） |
|---|---|---|---|---|---|
| **golden_b**（E2b 零 dsm-import 独立复核 + E3b 独立落地，双向印证） | A3B3C4D2 = **12** | A3B4C4D2 = **13** | A3B3C3D2 = **11** | **2** | **9** |
| **spine 2026-Q2**（A1d 实测 @`858ebc8`） | A3B3C4D2 = **12** | — | — | — | 已参评池计数和 A3B3C4D0 = **10**（占比分母 10）；12 主体全 L2 → 一级库 **0 准入** |

- G-14 判据：C 类计数／**9**，`3/9 = 0.333333333333 → 5/9 = 0.555555555556`，Δ = `0.222222222223` > TOL 触发。
- **三口径分工**（不得互换）：**判据用 9**（L1004 + ORCH-36 第3条，与 `share_*` 同源剔 NOT_ASSESSED）／**披露用 11**（L1003 + L1063⑥）／**Step-3 分类用 12**（L1459）。E3b 已把关系式写死：`assessed_denominator == Σevidence_structure − not_assessed_count`。
- E3b 另纠正：`SMALL_BASE` 应含 `(LOAN, C)`，共 **5 池**。
- **载体澄清（ORCH-44 第6条，P2-wire-B 独立复核一致）**：这些计数字面量**不在** `fixtures/golden/golden_map.json` 内（该文件是 **15 个 case** 的 `expects`／`hand`／`probes`）；golden_b 侧数字的载体是 `tests/test_golden_b.py` 的断言（本包实跑 **26 passed／0 failed** 为证）。spine 侧另实测 `primary_pool_eligible` 为真 **0**、等级分布 `L2×10 + NA×2`。

### H-8 A1d 的「把 11 标 `superseded_by_G14FIX`」建议 —— **主控驳回**

11 是 golden_b 的**池级 universe**，与 G-14 判据分母 **9** 是两个口径；10 属 spine 另一载荷。三者**互不替代**，任何 `superseded` 标记都属**口径污染**。本文各节一律按 §H-7 表呈现，不得再出现该标记。

### H-9 M29 九步 marshal 本体未落地（**保持阻塞，不得写成「CLI 已可用」**）

`dsm/cli.py:_chain_gate` 仍 `raise InvariantError`（退出码 5）；P2-wire-A @`53ed80c` 的两个 seam（`cli.py:391 _report_frames`／`cli.py:406 _render_reports`）**无生产调用点、只由测试驱动**。P2-wire-B(1/2) @`93abfee` 只补了 shell 侧 `anchor_set` 的**单点取法**（新增 `_anchor_set_doc(app)`，源 = config 层 `AnchorSetDoc`，与 `spine:137 _governance_docs()`、`normalize.compute` 第 3 位入参同源同对象），**并未落地九步编排**（其提交信息自述同此）。这是 **V-14 仍判 ❌** 的原因之一（另一原因 = M28 降级矩阵 26 行逐条遍历断言至今零断言）→ 保持 **G-14 阻塞**／**K-34** 待办。

### H-10 本文件仍保留的 PLACEHOLDER-TO-REFRESH（R-12）

① `output_fingerprints` 的 **64 位生产台账** → `**ORCH-69 主控亲测 @`a81730d`**（PH-12／NG-V12-20 口径，一次真实 CLI 实跑，键集**恰为 6** = `ARTIFACT_NAMES − {audit.json}`、逐值对落盘字节重算全等）：`report.md` = `2680703c1b453f0d7b0c083e892e54980a27da2e005740f8887c79494556f0c4`／`score_card.csv` = `9b5984d51aa118ebb1087ff83da0d29ba8ff8b730bfadcd9a336f9472f2fe38a`／`grade_ledger.csv` = `7afe10893ff2d366e191b7e997ac82d6c338031a5a6e6f4a675405f89cccd370`／`sensitivity_report.csv` = `d081efb8101121dba2f85fd556108cdfbfb1eb3efe823e7b3b8a867cfaeaffaa`／`entropy_diagnostic.csv` = `98207523a05e569fdea0568cbd8c6f55403d2a04c7c4703ffd6fbb8cafb9683a`／`triangulation.md` = `ec8733e1f1b15dedea2fd8d5923ddb201fb1881e0d4b905793ec85947c511b59`；`audit.json` 自身 sha256(落盘) = `083faf95f39fb55a962d73618dc86bb2ed82141068009b271e0745bcb665765a` 且 **`in_bundle=False`**（只经 `write_report_set` 返回值／CLI details 外部通道披露，正文搜不到该值 ⇒ 自指不可能）。⚠️ **跨运行不可比**：`run_id` 末段随机 8-hex ⇒ 上述具体值只对那一次运行有效，属**口径示例而非可复现常量**（NG-V12-26）；可复现的是**键集**与「逐值等于落盘重算」这条不变量（`tests/test_report_set_outlet.py` 8 条断言钉住）`（spine 面实测 `bundle.output_fingerprints = {}`；七件 sha256[:16] 已有 P2-wire-B 实算值，见 §H-2，**不得写「output_fingerprints 已变更」**）；⑦ 最终全量 pytest 的 **0-failed 结果本身** → **DOC-FINAL 已闭合**：实测 **0 failed／2302 passed／2302 collected**（① 原文命令统计行 `2302 passed in 10.98s`；观测工作树 `a396e0a`／提交后 HEAD `037b862`）；追记：该项在 P3c-final 为 `**`2444 passed in 20.67s`**（门禁① 标准形式，**ORCH-69 主控亲测 @`a81730d`**：独立 clone、porcelain 0、rc=0、`grep -c '^FAILED'` = **0**；第二形式 `-m pytest --continue-on-collection-errors -o addopts= -q` = **`2444 passed in 17.28s`**、rc=0；账目自洽 = `a432ef6` 基线 2418 + M29-2 新增 8 + B12-FIX 新增 18 = **2444**；v1.1 的 CMB-1 终值 2302 @`037b862` 保留为历史）`，实测 1／2301／2302 @`da4d0a9`，缺的是「转绿」而非数字，**现已转绿**；② K-07 的 `min_sample_size_for_A`／显著性水平／MDE 无代码落点；③ G5／G7 签认产物；④ 异机第二人复跑（V-3／V-10 维持 ⏳）；⑤ `cel_contract_version`（[L1897] 首版固定为占位版本 + [L1795] G8 未发布 → K-31）；⑥ `docs/adr/` 份数（`docs/adr/**` 属禁写面，本包未实测）。

### H-11 属 `ops/dag-state.json` 的台账矛盾 —— **只披露、本包不改**（主控写集，主控正在修）

① `reproducibility_evidence.invalidation_log` 出现**两个 `seq = 3`**；② `current_hash_asof` 仍写 `358b4ea`（权威哈希实测已复测到 `93abfee`／`da4d0a9`）；③ `defects` 状态滞后 3 处（`D-A1-05`／`D-G14-01`／`D-G14-02` 代码面已闭合但 status 未翻转）；④ `D-A4-02` **撞号**（whatif GEOMETRIC vs `whatif.py:571` 裸字面量，后者 CLOSED @`9078201`，同 L-12）。本包仅在 §H 与 `P3c-DELIVERY-PACKAGE.md` §5 披露，未写该文件。**ORCH-45 追记（已闭环）**：上述四项（三字段矛盾、`invalidation_log` seq2 的重复键、`defects` 状态滞后 3 处、`D-A4-02` 撞号）**已由主控在 ORCH-45 本轮 `ops/dag-state.json` 提交中修复，见 `ops/dag-state.json`**；该文件属主控写集，本包全程未触碰、未 add。

### H-12 本包新增的 K 条目索引（编号由主控 ORCH-44 单点分配，遵守 L-12）

**K-36**（权威哈希只认 `repro_offline.sh` 的 RESULT 行，测试内自测值一律标 non-canonical）／**K-37**（`NEED-GOLDEN-MAP` 之 G-10 hand 记录陈旧：须按 ORCH-35 改写为「单维 WARN／≥2 维 BLOCK+exit2」）／**K-38**（`NEED-GOLDEN-MAP` 之 G-14 hand 缺 pooling 三口径留痕 12／11／9 + 3/9、5/9、5/11、7/11）／**K-39**（P3b 工装 B1~B9 修复状态 + `dsm_stage/` 归档风险披露）。详见 `K-SIGNOFF-CHECKLIST.md`。

### H-13 P3c-final 实测台账（命令 → 输出摘要，全部本包亲跑）

| # | 命令 | 实测输出摘要 | 用于 |
|---|---|---|---|
| 1 | `cd /home/szf/dev/strategy-eval-dsm && git rev-parse --short HEAD; git rev-list --count origin/main..HEAD; git tag -l \| wc -l` | `da4d0a9`／**54**／**0** | §H-6、⑦ |
| 2 | `python3 -m pytest -o addopts= -q -p no:cacheprovider --tb=no -rfE` | **1 failed, 2301 passed in 15.48s**（collected 2302，0 error／0 skip／0 xfail） | ① |
| 3 | `python3 -m pytest -o addopts= -q tests/test_architecture.py` | **11 passed in 2.00s** | ratchet 28 绿 |
| 4 | `python3 -m pytest -o addopts= -q "tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen"` | **1 passed in 0.58s** | G5／G7 首屏声明守护 |
| 5 | `python3 tools/normalize.py --check; echo exit=$?` | **exit 1**；`SCOPE ... 189 controlled files`／`FOUR_ELEMENTS ... TRAILING_LF asserted on the 1 changed file(s) only`／`NEEDS_NORMALIZATION 1 of 189`（= `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md TRAILING_LF`）／`DISCLOSURE TRAILING_LF_HISTORICAL 17 of 189` | ④ |
| 6 | `git ls-files -z` + 对 `git show HEAD:<path>` 判 `endswith(b"\n")`／UTF-8／BOM／CRLF／TAB | 受控 **189**；四要素违规 **0**；缺末尾 LF blob **18**（披露 **17** + 变更硬失败 1）；非 `docs/**` **9** 个 | ④、K-35 |
| 7 | `sha256sum` + `len()` on `fixtures/golden/golden_map.json` | bytes **24330**／sha256 **`27c12b3e15aa…3dd39cfe`** == `fixtures/manifest.json` 登记值 | ⑤ |
| 8 | `bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --keep --strict-isolation` | **exit 0**；`RESULT=PASS HASH=e5923465…80904 COMMIT=da4d0a9 ELAPSED=15s ISOLATION=L3-strong … DIRTY=1 HEAD_STABLE=yes ASSERTION=pytest`；`netns_probe = offline-confirmed`；`clone_head` == `src_head`（commit-exact） | ③ |
| 9 | `git archive <sha> \| tar -x -C /tmp/p3cf_attr/<sha>` × {cc18a38, dce1ac5, 6299245, f27334d, 31eb1b2, 111570a, 93abfee} → 单测 `:502` 那条 | 绿／绿／**红**／红／红／红／红 → 引入点 = **A1c @`6299245`** | G-20 归因 |
| 10 | `cd /home/szf/dev/CampaignLab && git branch --show-current; git rev-parse --short HEAD; git status --porcelain \| wc -l; git rev-list --count HEAD` | `m0-framework`／`0cccb76`／**0**／**154**（开工 09:04 与收工各一次，两次一致） | ⑤（邻仓） |
| 11 | `sha256sum` + `wc -l` on 契约文件 | `708679e9a83d`／**2003 行** | 契约只读核验 |
| 12 | `grep -cE "^\\| [A-G]-[0-9]+ " docs/deliverables/KNOWN-GAPS.md` 与同前缀再筛「是」 | **65** 行／「是」**14**（见 §H-6，与本包更新后的汇总节逐字相等） | ⑥ |


### H-14 DOC-FINAL：全量 0 failed 终值、G-20 闭合证据链、tag 前置 ①~⑦ 重判（观测 HEAD `037b862`）

- **终值（转录 CMB-1 实测，本包不重跑全量）**：**0 failed／2302 passed／2302 collected**，0 error／0 skip／0 xfail。
  | 形式 | 命令 | 统计行原文 |
  |---|---|---|
  | 标准形式 | `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors` | **`2302 passed in 12.50s`** |
  | **tag 前置 ① 原文命令形式** | `/home/szf/venvs/dsm/bin/python -m pytest --continue-on-collection-errors -o addopts= -q 2>&1 \| tail -3` | **`2302 passed in 10.98s`** |
  判据满足理由：统计行形如 `N passed in Xs`，**无** `failed`／`error`／`skipped`／`xfailed` 字样。
- **观测 HEAD 如实注明**：全量跑在 **`a396e0a` 的工作树**上执行（CMB-1 提交前）；CMB-1 提交后 HEAD = **`037b862`**。docs-only 变更不参与测试收集，故终值对 `037b862` 及其后的文档提交仍有效。
- **本包亲跑的复核（非转录）**：`/home/szf/venvs/dsm/bin/python -m pytest -o addopts= -q tests/test_methods_combine.py` → **`22 passed in 0.67s`**；只读探针 `dsm_stage/CMB-1/probe_q3_count.py`（纯 stdlib、不 import dsm）在 `037b862` 复跑 → **`DERIVED_Q3_COUNT = 8`**，其余四期 **12**。
- **G-20 闭合的独立推导链（可复核）**：口径依契约 [L575]／[L1140]／[L1145] —— `n_t` = 当期同时携带全部 **entropy 指标**（`metric_dict` 中 `is_redline=false` 的 **12** 个；红线 **3** 个 `M_COMPLAINT_RATE`／`M_CONTACT_FREQ_PER_30D`／`M_OPTOUT_RATE` 不入 entropy）的策略数；缺行 = 缺格；`SUSPECT` 剔除（实测 **0**）。实测 `metric_fact` **896 行／15 指标／12 策略／5 期**，行数分布 **180×4 + 176（Q3）**；Q3 的 **4 个缺格** = `S-005×M_CAMPAIGN_COST_MINOR`、`S-006×M_CUST_GAIN`、`S-008×M_SATISFY_SCORE`、`S-011×M_ROI`，分属 **4 个不同策略** → **12 − 4 = 8**；其余四期各 12。归因佐证：`git show 6299245` 显示 `metric_fact` 唯一一行变更 = 删 `Q3/S-008/M_SATISFY_SCORE`、增 `Q3/S-008/M_COMPLAINT_RATE`，即 **A1c 的 D-A1-03 载体迁移**使缺格开始吃掉 entropy 完整策略数（9→8）→ 属**期望常量陈旧，非实现回归**。收口由 **CMB-1 @`037b862`** 完成（`:502` 期望 `9→8`、`:482` docstring 同步、断言上方 5 行依据注释；删除 2 行、净断言 +0、无 skip／xfail／or 化／区间断言、未碰任何实现文件）。
- **tag 前置逐条重判（DOC-FINAL）**：
  - **① 满足**（改判）。**追记（历史事实，不得抹去）**：本 RUN 内 ① **曾未满足** —— `1 failed／2301 passed／2302 collected` 实测于 `93abfee`／`da4d0a9`（15.48s），更早 `13 failed／2182 passed／collected 2195` @`358b4ea`、`11 failed／2190 passed` @`cc18a38`；现因唯一红条闭合而满足。
  - **② 满足（按 ORCH-44 重述判据）**：重述判据 = 「V-1~V-20 全 20 条在册；每条 ❌／⏳ 均有归属包 + K 缺口编号 + 下一版完成条件；且有 AUD-FINAL 零弱化卷宗佐证 C4（真弱化）= 0」。三子句现均成立（20 条在册；AUD-FINAL @`66481b1` 区间 `cc18a38..da4d0a9`：21 commits／12 触及 `tests/`／228 删除行，C1=20／C2=127／C3=81／**C4=0**、净增断言 **+332**、现存 skip／xfail **0**；V-14 的三项登记齐备）。**且逐字保留以下事实：原文 ❌=0 判据未被满足**，因 V-14 仍为 ❌ 且本 RUN 无法闭环（M28 降级矩阵 26 行逐条遍历断言至今零断言 + M29 九步 marshal 本体未落地，后者已裁为本 RUN 范围外）；在诚实性规则 R-12／R-14／V-14 与「凑 ❌=0」冲突时诚实性优先，故重述判据而非上调 V-14。**V-14 维持 ❌，本包不上调。**
  - **③ 满足（限 `93abfee`／`da4d0a9` 本次签核）**；CMB-1（`037b862`）与本轮文档提交使 HEAD 前移，**主控将在最终 HEAD 复跑 `bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`，结果记入 `ops/dag-state.json` 与最终报告**；复跑前 ③ 的最终态标注 = **`**ORCH-69 主控亲测 @`a81730d`**：RESULT 行逐字 = `RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=a81730d ELAPSED=18s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`；附属原文 `netns_probe = offline-confirmed` / `wh_manifest = verified(26 entries, sha256sum -c all OK)` / `run_#1 == run_#2 == e5923465…80904` / `RESULT_COMMIT = a81730dbb400a23bc50b81c5c8d7fd3bbfc069a9` / `stageA_rc=0` / 跑前跑后 porcelain 均 **0**；**载体 = 主仓库原地跑（非 clone）**，日志 `dsm_stage/V12-REPRO-PRE/out/prefinal_runA.log`。**PH-05 阶段 B 留坑** = `PLACEHOLDER-TO-REFRESH(主控@台账commit后的最终HEAD)`，原因：阶段 B 须与阶段 A 同 HEAD，而发版权威一跑在台账 commit 之后 ⇒ 其 RESULT 行与 `RESULT_COMMIT` **只记入 `v1.2.0` tag 消息、不回写文档**（避免移动 HEAD；ORCH-67）`**。V-3／V-10 维持 ⏳（第二人／异机复跑仍 PLACEHOLDER）。本包按派工单**未跑**该工装。 【**DOC-FINAL-B**：v1.2 的「最终 HEAD 复跑」已由主控执行完毕 —— 阶段 A 走**主仓库原地**（非 clone），RESULT 行逐字见本节 §G 之后「G-8 关闭证据」上方计数节与 V-ACCEPTANCE §O-B；阶段 B 因须与阶段 A 同 HEAD 而发版权威在台账 commit 之后 ⇒ 其 RESULT 行只入 `v1.2.0` tag 消息，不回写本文档（ORCH-67）。】
  - **④ 部分满足**：哈希侧闭合（`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`，多 HEAD 复测同值；`f437c0ea…` 按 ORCH-44／K-36 定性 **non-canonical**、不入台账）；台账侧（`current_hash_asof=358b4ea`、两个 `seq=3`、`defects` 状态滞后 3 处、`D-A4-02` 撞号）**属主控写集，本包只披露不改**，**主控正在本轮修复**（§H-11）。
  - **⑤ 满足**：本包亲跑 `cd /home/szf/dev/CampaignLab && git branch --show-current; git rev-parse --short HEAD; git status --porcelain \| wc -l; git rev-list --count HEAD` → **`m0-framework`／`0cccb76`／`0`／`154`**；契约 sha256[:12] = **`708679e9a83d`**、**2003 行**；邻仓只读、未触碰（收工复测一次）。
  - **⑥ 满足（本包重测）**：`grep -cE "^\| [A-G]-[0-9]+ " docs/deliverables/KNOWN-GAPS.md` = **65**；同前缀再筛 flag「是」= **13**（列级解析，转义竖线不计为分隔符）→ 阻塞 **13**／非阻塞 **52**／合计 **65**，与 §G「DOC-FINAL 权威计数」逐字相等（G-20 CLOSED 后自洽）。
  - **⑦ 待主控在 push 前实测（工作树须为空）**：判据与命令照抄 §2，核验时刻须为打 tag 当下。本包开工时 `git status --porcelain` = ` M docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（P3a-final 在飞）→ **本包跳过该文件**，只显式 `git add` 实际改动的文档；未 stash／checkout／restore／reset／clean；未 push、未 tag（R-13）。
- **发布数字（本包亲测 @`037b862`）**：`git rev-list --count origin/main..HEAD` = **59**（`origin/main` = `3616f9722213f6da2cb0b4ff6fcf55cd947ed648`；`git merge-base --is-ancestor origin/main HEAD` 实测为真 → push 是 fast-forward）；`git tag -l | wc -l` = **0**；本包提交后 ahead = 60，push 前由主控重测。

---

## H-15 V1-FINAL（ORCH-45）终值入档与缺口现状

**观测 HEAD = 最终 HEAD `3da51ab`（短 `3da51ab`），T+8.4h，全部为主控亲测**。本节只追加；H-1~H-14 与 A~G 节原文（含「13 红」「1 红」「PLACEHOLDER」表述）**逐字保留不作历史改写**。**本包未跑 pytest、未跑 `tools/repro_offline.sh`**，只引用主控钉死的终值。

### H-15.1 终值

- **全量 pytest**：标准形式 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors` → 统计行原文 **`2302 passed in 11.22s`**；① 原文命令形式 `... -m pytest --continue-on-collection-errors -o addopts= -q 2>&1` 尾接 tail 取末三行 → **`2302 passed in 10.84s`**；**0 failed / 0 error / 0 skip / 0 xfail**，collected **2302**。
- **P3b 正式签核（最终 HEAD，`--strict-isolation`）= PASS**，RESULT 行原文：`RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=3da51ab ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`；`all_equal=1`、`DIRTY=0`、`HEAD_STABLE=yes`、`netns_probe=offline-confirmed`、`wh_manifest=absent-unverified`、`env_python=Python 3.12.3`、`runs=2`、`elapsed_seconds=15`、`tmpdir=/tmp/p3b-repro.WQQSlx8P`（全字段见 `P3b-REPRO-HARNESS.md` §8 追加记录）。
- **工作树 / 邻仓 / 契约 / 发布数字**：`git status --porcelain` = **空**；邻仓四项 = `m0-framework`／`0cccb76`／`0`／`154`；契约 `sha256[:12]` = `708679e9a83d`、**2003 行**；`git rev-list --count origin/main..HEAD` = **62**（fast-forward）；`git tag -l` 计数 = **0**。

### H-15.2 缺口计数与 V-14 现状（不变）

- **阻塞 13 / 非阻塞 52 / 合计 65** 维持不变：本包只向本文件追加本节，**未改 A~G 与 H-1~H-14 的任何表格行与 flag 列**，故 tag 前置 ⑥ 仍自洽。【v1.2 指向：本句为 **v1.1 DOC-FINAL** 时点值，保留为历史；v1.2 本棒落笔后 = 阻塞 11／非阻塞 54／合计 65（`count_gaps.py` 同源清点），见 §G 汇总节追记与文末 §I。】
- **V-14 仍 ❌（ORCH-45 裁定维持 ❌、严禁上调）**，两项缺口一项未减：① **M28 降级矩阵 26 行 × 六列逐条遍历断言至今零断言、且至今无包认领**；② **M29 九步 marshal（[L1330]-[L1358]）本体未落地**——`dsm/cli.py:_chain_gate` 恒 `raise InvariantError`（退出码 5），`cli.py:391 _report_frames`／`:406 _render_reports` 两 seam 无生产调用点。**全量 0 failed 不等于 V-14 闭环**（见 H-9）。
- **V-1 依主控亲测上调 ✅**（❌ 由 2 条减为 1 条；三态 ✅11／❌1／⏳8）。

### H-15.3 本 RUN 不闭合、移交下一版的缺口（逐条写明缺什么）

| 缺口 | 缺什么 | 归属 |
|---|---|---|
| hypothesis **500 例档** | 现档 `tests/test_properties_all.py:73` = `max_examples=25`（R-11 开发期档），500 例**从未跑过** | 主控改派（本 RUN 无包认领） |
| **第二人 / 异机复跑** | 同机、同 Python 3.12.3、wheelhouse cp312-manylinux-x86_64 绑定、本次 `wh_manifest=absent-unverified` | 外部条件 |
| **3 层回溯重抽** | A1c 重冻 fixtures 后的抽查载体需重建 | 主控改派 |
| **`write_report_set` 生产出口** | 待 M29 marshal 落地；`bundle.output_fingerprints` spine 面实测 `{}` | 下一版 / 主控 |
| **provenance 七键终值抽查** | 终值 HEAD 逐键抽查 + 逐键标「合成待签认」 | 主控 |
| **M28 26 行断言** | 逐条遍历断言（零断言、零认领） | 主控裁决归属 |
| **`cli.py:918-919` OSError 静默降级** | AUD-FINAL 移交清单第 1 条，本 RUN 未返工 | 主控派工 |

### H-15.4 仍原样保留的诚实边界（一条都不得删）

`config/` 实测 **0 文件** → `dsm score` 端到端不可跑、`EXIT_CONFIG=3` 属**设计而非缺陷**；CLI 唯一入口 `python -m dsm.cli`、**无 console script**（D-CLI-01）；`cel_contract_version` 保持 **PLACEHOLDER**（[L1897] / [L1795]）；`f437c0ead77b…` 为 **non-canonical**、不入台账（K-36）；LOO 影响力 CSV 载体与 G-14 上期 PoolStats 载体**本 RUN 不做**（ORCH-42）；缺末尾 LF 的受控文件 **17 @`da4d0a9`**（其中 **9 个非 `docs/**`**，清零需**主控单独授权**；**本包仅为本轮改写的 `P3b-REPRO-HARNESS.md` 补齐其原有缺失的 1 个末尾 LF——该文件因属变更文件而受 `tools/normalize.py --check` 硬校验，非内容改写**，据此计数推算为 16，精确值由主控 push 前复测）；`dsm_stage/` **不入库**但多份裁决引用其中文件 → 归档风险披露保留（K-39）；**G5／G7 未过**，「**G5 / G7 未过，不得输出可用于真实资源配置的分数或等级**」声明一字未改；**未 push、未 tag**。


## §I v1.2 RUN 移交台账（NG-V12-19 … NG-V12-28 · DOC-FINAL-A 落笔 · 只追加）

- 权威源 = `ops/dag-state-v1.2.json` 的 `carry_gaps_v12[]`（本棒**只读**，`what`／`owner`／`close_condition` 逐字取用；该数组实测长度 = **28**，`NG-V12-19`…`NG-V12-28` 十条编号由**主控单点分配**，本棒不自占号）。
- **计数口径声明**：本节 10 行是「移交台账面」，与 §C／§E／§G 的既有行（G-15／G-8／NG-V12-19 即 G-15 残项等）**存在同源关系**，为避免双计，**不重复计入上方 A~H 总账的合计 65**；`count_gaps.py` 的行首 ID 正则为 `^\| [A-G]-[0-9]+ `，`NG-V12-*` 不在其匹配面内 ⇒ 机械清点自洽。最终入册口径归主控裁定（PH-22）。

| ID | 条件（何时触发） | 缺什么 | 归属 | 是否阻塞 | 备注 |
|---|---|---|---|---|---|
| NG-V12-19 | G-15 reason_code 六处接线的残项（#5／#9）在 v1.3 开工或 V-14 拟上调时触发 | G-15 reason_code 接线未齐（六处中 4 处已接，#5/#9 延期），V-14 因此维持 ❌ | v1.3 RUN | **是**（ORCH-63 维持 G-15 阻塞；severity=blocking-carry） | from = ORCH-63／RC-1 残项 #5、#9；close_condition = v1.3 落地 #5/#9 两处接线并使 V-14 四项齐备条件成立，再由主控亲测上调；与 §G 的 G-15 行同源，不重复计入总账 |
| NG-V12-20 | 任何把 `bundle.output_fingerprints` 读成「七件全含」的表述出现时触发 | 契约 L1046「AuditBundle 含输出文件清单与 SHA256」在 audit.json 自身亦为七件产物之一时字面自指；实现采六键口径，audit.json 自身 SHA256 走 write_report_set 返回值 / CLI details 外部通道披露 | M29-2 实现 + DOC-FINAL 披露 | 否（severity=informative） | ERRATUM-V12-07；**须在验收文档显式披露，不得静默**；契约只读不改原件；A 棒已在 V-ACCEPTANCE §O 与 §G 的 G-8 行披露 |
| NG-V12-21 | 有人按契约 L1225／L1638 把 `audit.json` 当合法 JSON 解析时触发 | audit.json 实为 serialize_bundle 的 canonical_text（obj:AuditBundle{...}），非合法 JSON；契约 L1225/L1638 要求 JSON | v1.3 RUN（reports.render_audit_json） | 否（severity=contract-deviation-carry，**本 RUN 不修**，ORCH-64 已裁） | close_condition = 改为真 JSON 输出并同步 tests/test_reports.py:336 与 M28-1 断言口径，**不弱化任何断言**；`tests/test_cli_marshal.py` 不得断言 json.loads(audit.json) 成功（ORCH-64 指令） |
| NG-V12-22 | 报告需区分 `ALPHA_INFEASIBLE` 与 `ALPHA_FLOOR_INFEASIBLE` 时触发 | dsm/cli.py _CODE_STATUS[7] 只有单标签 ALPHA_INFEASIBLE，与 ALPHA_FLOOR_INFEASIBLE 共用退出码 7，报告无法区分二者（与 ORCH-55 的 NG-V12-15 H-1 残留同族） | v1.3 RUN（cli.py） | 否（severity=disclosure） | 源 = M28-1 GAP-04；close_condition = 退出码 7 上区分两个标签，或在报告⑩段显式披露二者共用退出码；本棒实测 `git show 50fa9e0:dsm/cli.py` 第 29 行逐字含 `7: 'ALPHA_INFEASIBLE'` |
| NG-V12-23 | 外壳退出码被当作契约退出码使用时触发 | config.WeightVersionInvalidError.exit_code==2（config.py:696，与契约一致），但 cli.py 的 _EXCEPTION_CODES 把该类映射到 3（CONFIG）=> 外壳映射与契约不一致 | v1.3 RUN（cli.py） | 否（severity=contract-deviation-carry） | **锚点纠正（ERRATUM-V12-09，本棒实测）**：映射行 = **`dsm/cli.py:53`**（`617e7a5`／`b157e00`／`a432ef6`／`50fa9e0` 四 HEAD 同值；字典声明起于 `:52`）；dag-state 原文与本行所写 `cli.py:56` 系并发中间态转录误差，台账侧更正归主控；close_condition = 外壳映射改回 2 或给出契约层裁决，并补端到端断言 |
| NG-V12-24 | 逐字比对契约 §3.14 披露串与实现串时触发 | 契约字面与实现披露串差异 5 条：①L1298「秩反转/anchor」在 reports.py 零命中，实际由 preflight finding + audit.json + ⑩段承载；②L1299 sensitivity.veto() 只认 BLOCK 级 flag，review 档（FLIP_RATE_REVIEW=WARN）不把 usable_for_elimination 压 false；③契约句「本期结果不得用于淘汰决策」实得「本期结论不得作为淘汰唯一依据」；④L1286/L1301 契约第5列写码名 WEIGHT_REALLOCATED / ENTROPY_INSUFFICIENT_SAMPLE，实现如实复刻；⑤L1284/L1290 实现披露串比契约更具体 | 行方业务确认 + 主控（契约只读，不改原件） | 否（severity=informative） | 源 = M28-1 GAP-01/02/03/05/06（**五行合并为一行**，同性质同归属，避免把合计从 65 抬到 70 而稀释阻塞率统计意义，与 dag-state 映射逐字一致）；逐字出处 `tests/test_downgrade_matrix.py:19-36`（本棒实测行号） |
| NG-V12-25 | 把矩阵码名当契约强制引用时触发 | 降级矩阵 26 行中仅 7 行为契约字面码名，另 28 个码名系 M28-PRE 语义推定（ORCH-56 采纳），已在测试内逐行标注「推定」 | 行方业务确认 | 否（severity=informative） | **不得写成契约强制**；源 = M28-1 LITERAL_VS_INFERRED；出处 `tests/test_downgrade_matrix.py:46-50`；close_condition = 业务侧确认 28 个推定码名，或按确认结果改名 |
| NG-V12-26 | 要求七件产物**字节级**跨运行可比时触发 | run_id 末段为每次运行不同的 8 位十六进制（实测 -7bed95eb／-9168da65／-6a637057）=> 七件产物字节跨运行不可复现（report.md／score_card.csv 尤甚）。契约 L1640 的第二人复跑口径是比 reproducibility_hash 精确相等，故不违约 | v1.3／待行方口径 | 否（severity=informative） | **不构成违约**；close_condition = 若行方要求产物字节级可比，把 run_id 改为确定性派生（如输入指纹 + run_at 的哈希前 8 位）；该需求未确认前**不得**擅自改动实现 |
| NG-V12-27 | `dsm score` 在仓库冻结 fixtures 上跑到诊断段时触发（退出码 5、不产任何结果） | dsm/diagnostics.py:223 _pearson：钱款列 M_CAMPAIGN_COST_MINOR≈2.8e6 => sxx*syy≈1e26，quantize 到 1e-12 需 38 位有效数字 > Decimal 默认 prec 28 => InvalidOperation => dsm score 退出码 5、不产任何结果 | **B12-FIX（Epicurus）在飞**；否则 v1.3 | **否**（**CLOSED @`f213c1e`**，**ORCH-69 主控亲测 @`a81730d`**；A 棒所记「未修 = 阻塞／待 B 棒」保留为其写入时刻实况，不删） | **A 棒口径：B12-FIX 未入 HEAD ⇒ 按「未修」登记，修复结果一律待 DOC-FINAL-B 按最终 HEAD 实测填入**；close_condition = 局部提高 decimal 精度且保持纯 Decimal 精确算术（禁 float／禁粗化 quantize／禁吞异常），并以独立预言机验证相关系数正确；⚠️ 本缺陷由 M29-1 落地**首次可达**才暴露，**不得回读成 M29-1 的回归** ⇒ **DOC-FINAL-B 实测回填**：修复载体 = B12-FIX `f213c1e`（B1 `_pearson` Decimal 精度溢出，另修被 B1 掩盖的 `CollinearityReport.matrix` 非空格缺陷）。主控亲测 = 独立 clone @`f213c1e` 全量 **1 failed / 2443 passed**（唯一红 = 当时尚未翻面的 `tests/test_cli_marshal.py:296` 过渡钉，已由 **`a81730d`** 关闭 ⇒ ORCH-66）；新增两测试文件定向 **9 + 9 = 18 passed**；钉死套件 `test_diagnostics`／`test_triangulation`／`test_golden_a`／`test_golden_b`／`test_reason_codes`／`test_integration_spine` = **121 passed**；`all_codes()` 仍 = **91**、**无** `GRA_NORM_REFERENCE_ZERO`（未擅自加码）；`reproducibility_hash` = `e5923465…80904` **未变**。 |
| NG-V12-28 | `dsm score` 在仓库冻结 fixtures 上跑到 triangulation 段时触发（退出码 5） | dsm/triangulation.py:293 dimensionless：M_AUM_MINOR 在 12 主体上恒定 => min_max 归一后全 0 => gra_norm=initial/mean 两种签认口径参考值均为 0 => TriangulationError => 退出码 5 | **B12-FIX（Epicurus）在飞**；否则 v1.3 | **否**（**CLOSED @`f213c1e`**，**ORCH-69 主控亲测 @`a81730d`**；A 棒所记「未修 = 阻塞／待 B 棒」保留为其写入时刻实况，不删） | 同上：修复结果待 B 棒实测。close_condition = 零方差列改为显式降级 + 复用已注册码披露（先例 SPEARMAN_ZERO_VARIANCE），**禁发明第三种归一化口径、禁新增注册码（91 计数被钉）、禁改任何入分数值** ⇒ **DOC-FINAL-B 实测回填**：修复载体 = B12-FIX `f213c1e`（B2 `dimensionless` 参考值为 0，另修被 B1 掩盖的 `CollinearityReport.matrix` 非空格缺陷）。主控亲测 = 独立 clone @`f213c1e` 全量 **1 failed / 2443 passed**（唯一红 = 当时尚未翻面的 `tests/test_cli_marshal.py:296` 过渡钉，已由 **`a81730d`** 关闭 ⇒ ORCH-66）；新增两测试文件定向 **9 + 9 = 18 passed**；钉死套件 `test_diagnostics`／`test_triangulation`／`test_golden_a`／`test_golden_b`／`test_reason_codes`／`test_integration_spine` = **121 passed**；`all_codes()` 仍 = **91**、**无** `GRA_NORM_REFERENCE_ZERO`（未擅自加码）；`reproducibility_hash` = `e5923465…80904` **未变**。 |

**§I 节小计（与总账分列，不并入 65）**：10 行；其中「是」4 行（NG-V12-19 与 §G 的 G-15 同一事实、NG-V12-20 归实现面已预裁、NG-V12-27／28 为 B12-FIX 在飞未修）⇒ 按「同源不重复计」口径，**独立新增的阻塞事实 = NG-V12-27／28 两条**；若主控最终裁定并入总账，则收口值应为「阻塞 11 + 2 = 13／合计 65 + 10 = 75」并须声明与 G-15／G-8 同源不重复计 —— **该口径归主控定，本棒不擅改总账**。


> **DOC-FINAL-B 追加（ORCH-68 主控裁决 @`a81730d`）**：NG-V12-27／NG-V12-28 转 CLOSED；新增 **NG-V12-29／30／31** 三条。至此 §I 共 **13** 行（NG-V12-19…31），仍按 **PH-22 主控裁定**不计入 A~H 总账。**PH-22 口径裁定 = 采纳 A 棒声明**：§I 的 `NG-V12-*` 行**不计入**总账合计 **65**（`count_gaps.py` 行首正则 `^\| [A-G]-[0-9]+ ` 本就不匹配 `NG-`），以避免与 G-15／G-8 同源双计 —— 该口径**已由主控裁定，不再列为待定**。

| NG-V12-29 | **B4（ORCH-68）**：签认 `gra_norm=initial` 叠加 min_max 归一，在真实冻结 fixtures 上结构性触发 `dimensionless` 参考值为 0 ⇒ `dsm score` 退出码 **5**、不产任何结果 | `config/eval_config.yaml:104 gra_norm: initial` 确为**已签认枚举值**；`dsm/triangulation.py:315-329 dimensionless` 的 docstring 明写「参考值为 0 时除法 genuinely undefined → 报错，**不回落成第三种口径（那是发明数值，R-12）**」；触发列 = `M_CONTACT_FREQ_PER_30D`（`distinct=2`、**非**零方差；min_max 归一保证每列必有 0，`initial` 取 `vals[0]` ⇒ **结构性脆弱**） | 行方（config 语义签认）+ v1.3（`dsm/preflight.py` C-03 增配置语义校验） | **是（对 `initial` 口径阻塞；对 `mean` 口径不阻塞）** | 主控亲测 @`a81730d`：`initial` → RC=**5**，错误原文 `TriangulationError: GRA 无量纲化参考值为 0（gra_norm=initial），关联度未定义`；`mean` → RC=**0** 且七件产物齐备（`audit.json`／`entropy_diagnostic.csv`／`grade_ledger.csv`／`report.md`／`score_card.csv`／`sensitivity_report.csv`／`triangulation.md`）。**裁决两条（不得软化也不得加码）**：① **B4 不构成 V-14 违规** —— 退出码 5 + 点名注册错误 = **显式拒绝**，正是 [L1507]／[L1512]「无静默降级」所要求的行为，**不是**静默错值 ⇒ **不因此下调任何三态**；② 但它是**真实的开箱可用性缺口**。**本 RUN 不修，三条理由**：(a) 诚实修法需**新注册码**，会打破 `all_codes()` = **91** 的钉子且 severity 需行方签认；(b) 改 `config/**` 等于改**已签认业务值**（R-12 禁止）；(c) 时间盒。完成条件 = (a)(b) 其一落地且 `dsm score` 在签认 config 下退出码 0 |
| NG-V12-30 | 零方差列进入共线性判定面时触发（B12-FIX GAP#2） | 零方差列使 `_invert` 回 `None` ⇒ `singular=True` ⇒ 全部 12 指标被判 `COLLINEAR` + 12 张 `MERGE_OR_DROP` 工单；这是 `_invert` docstring 的**明文设计**，但 **B3 修好后首次可达** ⇒ 会把「rho 无定义」**误报成「共线性」**，属 V-14 反向风险 | L5 owner／v1.3 | 否（非阻塞，误报面） | **ORCH-68 主控登记 @`a81730d`**；close_condition = 区分「奇异/rho 无定义」与「共线性」两条披露路径，不弱化任何现有断言 |
| NG-V12-31 | 钱款列参与变异系数中间量计算时触发（B12-FIX GAP#3） | `dsm/diagnostics.py:207-213 _cv` 的中间量 `(D(v)-mu)**2` 在 `prec=28` 下**静默舍入**（钱款列 35 位 → 28 位），相对误差 ~**1e-17** | L5 owner／v1.3 | 否（**远低于 1e-12 输出分辨率，不产生错值、不阻断**） | **ORCH-68 主控登记 @`a81730d`**；可与 B1（NG-V12-27，已闭）同口径处理；close_condition = 中间量精度与输出分辨率对齐并补断言 |
