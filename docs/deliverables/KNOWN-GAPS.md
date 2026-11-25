# 已知缺口清单（KNOWN-GAPS · P3c-prep 前移建表）

- 性质：§3.2 第 239 行 P3c 交付物中「**已知缺口**」部分的建表与填满（README / `git tag v1.1.0` 由 P3c 在 P2 收口后执行，本包未打 tag、未改 README.md）。配套文件：`docs/deliverables/K-SIGNOFF-CHECKLIST.md`。
- 事实来源与核实方式：`ops/dag-state.json`（contract_gaps_pending 41 条 / gap_adjudications_SP1 / gap_adjudications_SP2 / r15_batch_2 / defects / orch_lessons）、`docs/adr/RUN-ORCH-25..30`、各 lane 缺口档案（`dsm_stage/{E5,A4,C2b,B1b,SEAM-1,EFIX-1,A1b}/`），以及**本包对代码的 grep 实测**（观测 HEAD `f27334d`，2026-11-25）。lane 自述与代码实测不符处以**实测为准**并写进「备注」列。
- **P3c-pre2 修订（本版本）**：① 修 **D-DOC-01**——原汇总节自称「阻塞 19 条」而同文件逐条列举与逐行 grep（含 F-1／F-2 加粗「是」）均为 **24 条**（ORCH-39 第2条裁 24 为**当时**权威值）；本包不照抄 24，而是从当前正文重新逐条清点、按 ORCH-40／ORCH-41／ORCH-42 已关闭项扣减、并登记新增缺口，得**新的权威计数：阻塞 16 条／非阻塞 48 条／合计 64 条**，汇总节与正文逐条列举**由同一份数据生成并已回读自证相等**。② 新增 **G 节 19 行**（含 P2-wire-A @`53ed80c` 上报的「M29 九步 marshal 本体未落地」等阻塞级缺口）。③ A~F 各行「阻塞交付」列按实测关闭依据改写，关闭依据一律带 commit 号。
- 本包写集 = 本文件 + `K-SIGNOFF-CHECKLIST.md` + `P3c-DELIVERY-PACKAGE.md` + `README.md`；**未写** `V-ACCEPTANCE-EVIDENCE.md`（归并发的 P3a-pre2）、`P3b-REPRO-HARNESS.md`（归 P3b）、`dsm/**`、`tests/**`、`fixtures/**`、`tools/**`、`config/**`、`ops/dag-state.json`、`docs/adr/**`、`pyproject.toml`。未 tag、未 push（R-13）。
- **R-12 声明**：最终全量 pytest 数字、最终 `reproducibility_hash`／`output_fingerprints`、最终 `git rev-list --count origin/main..HEAD` 一律写 `PLACEHOLDER-TO-REFRESH(<负责人>)`——A1d／E2b／E3b／P2-wire-A／P2-wire-B 并发施工，本包此刻测到的都不是终值。
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
| D-6 | D-A1-05 | fixtures 或 io_loaders 格式归属二选一（按 M21/M18 原文） | 未定 | A1c 或 C1c | 否 | OPEN　**已闭合**：D-A1-05 由 A1d @`f27334d` 按 ORCH-41 第1条 R2 的**列级口径**落地（`io_loaders.py` 新增 `_required_text_columns()` 与常量 `TEXT_AS_IS_COLUMNS`，必填 str 列的空单元格读回空串；NULL_LITERALS／后缀白名单／models.py／evidence.py 逐字节未动，fixtures 零改动）。A1d 实测 spine 7 红 → 1 红，剩余 1 红归因归 G14FIX 写集；全量终值 PLACEHOLDER-TO-REFRESH(P2-wire-B) |
| D-7 | D-C2-01 | —（上报被撤回） | CLOSED_AS_MISREPORTED：ORCH-30 实测三期唯一 blocks_run=True 为 C-01；preflight PROD=0，仅补 4 条负向测试 | 无（记录保留） | 否 | 状态字符串非 CLOSED，按任务口径列入本表 |

## E. 文档矛盾类

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| E-1 | ORCH-24 内部矛盾 | L43+L320 与 L36+L342+L406 四条不可能同时成立（B4 G3） | RT-08 / ORCH-25 已裁；文档勘误留 P3a 披露 | 主控/文档侧勘误 | 否 | 实测代码 `dsm/config.py:449` 的 `load_all(config_dir, *, period=None, run_at=None)` 与 ORCH-24 L43 逐字一致（L36「12 个公开名与既有用例一条不改」侧由 config.py:1166「period 必填无默认」注释体现口径分歧） |
| E-2 | M29 L1334 vs M43 L942 池键顺序 | 两文对分池键顺序的口径未对齐（B4 上报） | 代码取 M43 L942 逐字 `(biz_domain, evidence_class)`：实测 `dsm/models.py:751-752` PoolKey；normalize 分组键 `(period, pool_key, metric_id)`（`dsm/normalize.py:22/339`） | 设计方勘误 | 否 | **本包复核**：M29 L1334 原文只写「Step 2 normalize → 池内标准化 + 锚定集参照」，两行之间未见逐字可判的「顺序矛盾」；矛盾实点请主控给出（以实测原文为准的备注） |
| E-3 | M22/M28 的 C-08 严重度读法 | 「severity=BLOCK」被读成「阻断整轮」（P2a 归因错误 + 主控 ORCH-29 第 3 条自行补出表级 BLOCK） | ORCH-30 撤回并定纪律（orch_lessons L-05：severity 与 blocks_run 分离；原文未写 BLOCK 不得新增 BLOCK） | 无（教训入档） | 否 | C2b 三期 diag 实测唯一轮级阻断=C-01（`dsm_stage/C2b/NOTES-C2b.md` §2） |
| E-4 | 文档码名 vs 注册名 | M31 L1406 / M37 L1669 写 `GRADE_CAPPED_NO_TARGET`，注册名是 `GR_CAPPED_NO_TARGET`（`dsm/reason_codes.py:60`）；M37 L1656 写 `PL_L1_GATE_EVIDENCE`，注册表**无此名**（实测最接近 PRIMARY_POOL_REJECTED_EVIDENCE，`:84`） | ADJ-3 一律用注册名；digest 冻结不改，文档更正登记为缺口 | 设计方更正 M31/M37 | 否 | M43 L944 四码 INACTIVE_METRIC/RANK_REVERSAL_RISK/SMALL_POOL/ANCHOR_SET_STALE 与注册名一致（实测 `dsm/reason_codes.py:49-51/59`） |
| E-5 | M00 层级自相矛盾 | L276-278 称 weights_ahp/weights_combine/fixtures_gen 属「L0a 无依赖」，但 [L537] 要求熵权「两个计算者共用同一实现」，INV-1（L300）禁 L5 反向 import（E5 GAP-E5-01） | ORCH-03 裁决新增 `dsm/entropy.py`（L1 唯一实现，两侧从 L1 导入）；ORCH-26/27 落 ADR | 已裁（勘误留文档侧） | 否 | **与 lane 自述不符**：E5 档案称 weights_combine「L39 from dsm import numeric, weights_ahp」，实测现 HEAD 该文件 `:47-48` 为 `from dsm import numeric` + `from dsm.entropy import entropy_weights`，**不 import weights_ahp** |
| E-6 | M00 L294 L0b 目标清单非穷尽 | 在飞 L0b 模块（A3 标定 / A4 whatif）都需要清单外的边（E5 GAP-E5-09，自标 BLOCKING，阻断 A3/A4 转绿） | E5 以 ratchet/白名单暂缓 | 主控裁决（后续 ORCH） | 是 | `dsm_stage/E5/GAPS-E5.md` 实测标题行 |
| E-7 | combine 产物落点冲突 | [L1368] 要求写 `config/weights_WV-DRAFT.yaml` vs [L1091]「重跑不覆盖」+ config/ 为签认载体禁自动生成（D5 gap4） | 维持 `out/combine/<run_id>/`，不改 config/；P3a 披露 | 设计方 | 否 | SP2 BLOCKING_candidates 实测 |
| E-8 | Step8/Step7 顺序空洞 | 主流程 Step8(sensitivity) 在 Step7(pooling) 之后 → FLIP_RATE_UNUSABLE 首过必然无载体（C5 gap3） | C5 以必填 keyword-only sensitivity 入参 + 缺失即不予准入（PRIMARY_POOL_REJECTED_ROBUST）显式处理，非静默 | **待 SP-3 裁**（是否 P2 集成时加「Step8 后回跑 Step7」） | 是 | SP2 ruling 原文「待 SP-3 裁」实测 |

## F. G5 / G7 门禁（M39 L40 / L42，SDD L1792 / L1794 逐字）

| # | 门禁 | 通过判据（M39 逐字） | 当前实测状态 | 闭合责任方 | 阻塞交付 | 备注 |
|---|---|---|---|---|---|---|
| F-1 | **G5** D6 证据复核已完成 | 「三项争议来源逐字复核并给出采用 / 排除结论；未复核项标『禁止引用』」；M39 原文状态列：**「未完成 → 复核前全面禁用（§5.5.3）」** | 未完成：`grep -rn D6 dsm/*.py` 无命中，本 run 无复核产物；代码侧与之相容（未验证载体一律显式异常，如 `dsm/whatif.py:268-287` WhatifInputError 拒 PLACEHOLDER/None） | 行方 / D6 复核方 | **是** | 复核完成前，任何争议来源结论**禁止引用**；本两清单未引用争议来源数值 |
| F-2 | **G7** 治理配置已签认 | 「权重、门槛、红线阈值、评价周期、各指标目标值、α 及 K-15~K-20 全部脱离 PLACEHOLDER」；M39 原文状态列：**「未完成（依赖行方，见 §5.9）」** | 未完成且**无载体**：config/ 0 文件（实测 `find config -type f` = 0）；20 项 K 全部未脱 PLACEHOLDER（见 K-SIGNOFF-CHECKLIST.md）；真实运行在 `config.load_all()`（`dsm/config.py:449`）按 `EXIT_CONFIG=3`（`:71`）拒绝 | 行方（评价管理委员会）——即 K 清单的签认动作 | **是** | G7 未过时按 M39 L45：仅允许合成数据全流程/演示报告/whatif 预演，**不得**输出可用于真实资源配置的分数或等级 |


## G. 本轮新增登记（ORCH-39 ~ ORCH-42 期间产生／闭合的缺陷与缺口 · P3c-pre2 建表）

- 本节由 **P3c-pre2** 依派工单「新增的缺口也要登记（不要只删不增）」+ ORCH-42 补充事实建立；每行的关闭依据均为**本包亲自实测或主控裁决原文**（`ops/dag-state.json` 的 `decisions.ORCH-39~ORCH-42`／`defects`（27 条）／`errata`（11 条）+ 各 lane 的 `dsm_stage/*/NEED-WIRING.md`），未实测的一律写 PLACEHOLDER-TO-REFRESH。
- 观测 HEAD = `f27334d`（A1d）；本包施工期间 HEAD 依次为 `858ebc8`（LOO-1）→ `53ed80c`（P2-wire-A）→ `f4aaa6b`（ORCH-40+41 入账）→ `f27334d`（A1d）。`git tag -l` 实测 **0** 条；`git rev-list --count origin/main..HEAD` = PLACEHOLDER-TO-REFRESH(主控 push 前重测)。
- G-14／G-15／G-17 三行在 `dag-state` 的 `defects` 里**尚无缺陷号**；本包按 **L-12** 纪律不自占编号（编号单点分配权在主控），只描述事实与归属。

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| G-1 | D-EVID-01 出桥范围未按评价期过滤 | `evidence.classify` 出桥 13 行 vs 本期评价范围 12 个 (strategy,version) 对 | EVID-1 @`897cad1` 落地按评价期过滤；CODES-2 @`32cafd0` 注册 `RC.EV_OUT_OF_EVAL_PERIOD`（INFO／blocks_run False），`dsm/evidence.py` 的 `PLACEHOLDER_OUT_OF_PERIOD_CODE` 已消除；P2-wire-A @`53ed80c` 第③项把范围过滤披露端到端接进 reports | 已闭合（ORCH-40 第2条签认判据等级 derived:） | 否 | 出桥 13→12 实测印证；`spine:663` 的断言由 A1d @`f27334d` 改 13→12（未删、未弱化） |
| G-2 | D-A1-06 G05 变体与 golden hand 口径不自洽 | golden_map 记 S-009_CONTRIB=1.900000／综合分 1.5346，按实际 fixture 手算应为 1.810000000000／1.507600000000 | 未代填（R-14）；A1c ADR §11 已登记应改值与原文依据 L1407／L1460／L1342 | E2b（ORCH-41 第5条：golden_map 单写者=E2b，撤销原「交 E3b」的分派） | 是 | defects 实测 status=OPEN；属 R-14 的手算更新，不是照抄实现输出 |
| G-3 | D-A1-07 13／12／11 三分母互不相等 | 「证据结构占比」的分母定义未定，golden 记 4/12 | 三口径已裁并实测入册：出桥 12／证据结构 A3B3C4D2=12／占比双报 A3B3C3D2=11；ORCH-41 第8条升级为权威口径（ERRATUM-11：pooling universe 分母=11、G-14 判据分母=9） | E3b（陈旧常量按 E3PREP 独立手算更新，**严禁按实测反填**；仍红则报 blocked 附差异表） | 是 | defects 实测 status=OPEN（口径已裁、落实未完） |
| G-4 | D-A1-08 IMPUTE_MEDIAN 的中位数参考集 | 参考集口径未定（E3 的假设经覆盖矩阵证伪） | ATT-1 @`dce1ac5`：`compute(..., anchor_set=None)` keyword-only，anchor 优先、失效回退当期池并落 `RC.ANCHOR_SET_STALE`（WARN／blocks_run False） | 已闭合（ORCH-40 第3条） | 否 | 接线余点：golden_a:287／780→E2b、`spine:166`→A1d（**已由 A1d @`f27334d` 接上**，实测哈希 UNCHANGED，因 spine 评价期事实表完整不触发 IMPUTE 分支）、cli Step1→P2-wire |
| G-5 | D-A1-09 仓库级 `data/<period>/` + `config/` 布局 | A1DPREP 与 A1d 两侧实测**判定不需要**：`_stage(spine:120-131)` 早已按 [L888] 在 tmp_path 下产出 `config/*.csv` + `data/<period>/*.csv`，`io_loaders.py:274-279/314-320/301` 早已实现 | 无需处置（ORCH-41 第1条 R3 确认；A1d R3 复测证实后缀白名单 `:189-190`／`:274-279` 根本没触发，唯一抛错点是 `:270` 的 `MODEL_ROW_REJECTED`；同时撤销 E3PREP NEED-FIXTURES 第⑧条的风险前提） | 无（**已判定不需要**，非留空） | 否 | L888 的仓库级布局迁移仍不在本 RUN 范围（ORCH-38 第7条维持） |
| G-6 | D-D2-01 LOO 影响力排名产出物缺失 | [L748]／[L1409]／[L1450] 要求「每指标 LOO 影响力排名（主导指标清单）」，原实现只有 flip_rate 警示判据（全文「跨度／极差／span」0 次 → 算式属 derived） | LOO-1 @`858ebc8` 新增 `SensitivityReport.loo_impact: tuple[tuple[str, Ratio], ...] = ()`（带默认值，既有构造点零改动，ORCH-41 第3条硬约束） | 已闭合（ORCH-40 第7条改判「实现缺项、非测试过严」+ ORCH-41 第2条收口） | 否 | 实测 loo_impact_max = M_REV_MINOR 0.120000000000 与手算逐位相符（次高 M_CONTACT_FREQ_PER_30D 0.098323076923，唯一最大者无并列）；**出口面见 G-16** |
| G-7 | D-SEN-01 dominant 清单排序依据 | 按发现顺序而非影响力排序 | LOO-1 @`858ebc8` 改按 loo_impact 降序；flip_rate 警示判据保留为**独立字段**，二者并列呈现、不得合并或互相替代（ORCH-40 第7条） | 已闭合（ORCH-41 第2条） | 否 | g07 两条改前改后均 2 passed；`tests/test_sensitivity.py` 29 passed（22 旧 + 7 新）；`reproducibility_hash` 不变（`audit.py:242` 不消费 SensitivityReport） |
| G-8 | D-G14-01 `mix_quality_verdict` 无出口 | reports／cli 均未调用 → 「报告出现 MIX_QUALITY_DEGRADED 警示」永不成立（V-14 静默降级） | reports 面已闭合：G14FIX @`42d5346` 接入 `reports.py:419`（_section_6，[L1063]⑥）；cli 面 P2-wire-A @`53ed80c` 落了 seam `cli.py:406 _render_reports`，但**该 seam 目前没有生产调用点，只由测试驱动**（见 G-14） | P2-wire-B／主控（需 M29 九步 marshal 落地） | 是 | defects 实测 status=OPEN；MD 报告面已可见、**CLI 端到端面仍不可达** |
| G-9 | D-G14-02 G-14 分子／分母零原文依据 | 分子用 C+D（`LOW_EVIDENCE_CLASSES`）零依据，唯一明文 SDD L1416 写「C 类占比」；分母用四类合计且不剔 NOT_ASSESSED，与同模块两列 `share_*`（`pooling.py:424/425`）不同源 | G14FIX @`42d5346`：分子改 **C 类占比**（L1416 verbatim）、分母 `assessed_denominator()` 与 `share_*` 同源（L1004 负向排除 verbatim + 同源 derived）；阈值 `numeric.TOL` 一字未改、仅标工程默认（K-21）；不改 `LOW_EVIDENCE_CLASSES` 常量（它另承担 (C+D) 披露口径，被 g14 `:1692-1699` 与 `test_pooling:350/352` 钉住） | 代码面已闭合（ORCH-40 第6条签认）；defects 状态待主控翻转 | 否 | 实测 PoolStats A3B3C3D2=11／NA=2／已参评 9；判据 3/9=0.333333333333 → 5/9=0.555555555556，Δ=2/9 > TOL 触发；g14 三条仍红归因 A1c 后过期的手算 expects → E3b |
| G-10 | D-DOC-01 本文件阻塞计数自相矛盾 | 汇总节自称 **19** 条，同文件逐条列举与逐行 grep（含 F-1／F-2 加粗「是」）均为 **24** 条 | **本包（P3c-pre2）已修**：按 ORCH-40／41／42 的关闭项扣减 + 新登记缺口，从正文逐条重新清点；汇总节改由脚本与正文**同一数据源**生成 | P3c-pre2（本包）；`ops/dag-state.json` 的 defects 状态待主控翻转 | 否 | 验收条件「汇总数 == 正文逐条列举数」已回读自证（见汇总节）；顺带修复 `C-8` 行因未转义竖线导致的 9 列畸形（本包只做 escape-aware 解析与 flag 归位，**未改写其原有文字内容**） |
| G-11 | D-CLI-01 无 console script | `pyproject.toml` 无 `[project.scripts]` → SDD L805／L836 的 `dsm` 可执行入口未落成 | 唯一入口 `/home/szf/venvs/dsm/bin/python -m dsm.cli`（顶层 8 个 COMMAND：preflight／score／sensitivity／ahp／combine／fixtures／calibrate／whatif，其中 ahp／combine／fixtures 为二级组 → **叶子命令 8 条**，与 L1080-L1087 逐条对应；公共 6 参数 + `--schemes`；退出码 0／2／3／4／5／6／7） | 已接受并披露（ORCH-39 第3条，ACCEPTED-DISCLOSED）；本 RUN **裁定不补** | 否 | 理由=避免写集扩散到 `pyproject.toml` 并与 P2-cli／P2-wire-A 抢同一文件；README §5.1 与交付包 §1 第 12 项已如实披露 |
| G-12 | D-MODELS-02 `PoolStats` 缺「已参评主体的四类分布」载体 | 冻结契约无该列，G14FIX 提 3 个方案交主控裁（`dsm_stage/G14FIX/NEED-CONTRACT.md`） | 维持 reports 本地容器方案（`dsm/reports.py:108 AllFrames.previous_pool_stats`，ADJ-4），本 RUN 不改 `models.py` 的 `PoolStats` | 下一版本（ORCH-40 第6条，ACCEPTED-DISCLOSED） | 否 | 决定性理由=`models.py` 已由 LOO-1 获 R-15 单点授权做最小新增，再叠加会放大回归面且余量不足；本地容器已满足 V-14 披露 |
| G-13 | D-TOOLS-01 编码门禁作用域过宽 | `tools/normalize.py --check` 的 `targets()` 用 `os.walk(ROOT)`，含 gitignored 的 `dsm_stage/` → 现报 `NEEDS_NORMALIZATION 38 of 666`，抽样前 4 条全在 `dsm_stage/ADJ-G07/`（**假红**） | 权威口径（ORCH-42 第6条）：**四要素（UTF-8 strict／无 BOM／LF／源码无 TAB）全量硬失败 + 末尾 LF 只对「本次变更文件」断言**；受控文件（`git ls-files`，实测 189 个）四要素违规实测 **0**（BOM 0／CR 0／TAB 0／解码失败 0）；历史遗留 **22 个**缺末尾 LF（全在 `docs/**` 与 `README.md`，**不是 ORCH-36 第11条写的 20 个**）**只披露不返工** | P2-wire-B（作用域收窄为 `git ls-files`；ORCH-41 第4条⑦明示可移交） | 否 | defects 实测 status=OPEN；门禁明文定义在 `docs/ORCH-TEMPLATE-v1.0.md:146`（H-G3）+ `docs/CONTEXT-BRIEF-v1.0.md:33` + `docs/RUN-UNATTENDED-v2.0.md:72` + `docs/adr/ORCH-21.md:130` |
| G-14 | **M29 九步 marshal（[L1330]-[L1358]）本体未落地**（本包新登记，dag-state 尚无缺陷号） | `dsm/cli.py:_chain_gate` 在模块齐全时仍 `raise InvariantError`（退出码 5），`_period_cases` 同样以此为由拒绝 → P2-wire-A @`53ed80c` 落的两个 seam（`cli.py:391 _report_frames`／`cli.py:406 _render_reports`）**目前没有生产调用点，只由测试驱动** | **不得写成「CLI 已可用」**：真实运行先被 `config.load_all()` 以 `EXIT_CONFIG=3` 拒绝（`config/` 实测 0 文件，设计如此非缺陷）；即便配置齐备也会在 marshal 处以退出码 5 拒绝 | P2-wire-B／主控（需 A1c fixtures + Step1-8 编排，超出 45 分钟接线包） | 是 | ORCH-42 第2条明示为**阻塞级**缺口；依据 HANDOFF-P2 §2、INV-2（M00 L301：shell 不得内联任何一步）、[L1556] 一带的 CLI 要求；marshal 落地后 `frames = cli._report_frames(...)` → `cli._render_reports(run, bundle, frames, app)` 两个披露载体（`previous_pool_stats`／`evaluation_scope`）会自动接上，LOO 摘要也应挂在同一 seam 避免第二套输出 |
| G-15 | **reason_code 接线待办**（CONSUMPTION-TODO 第 2／3模块侧／4／5／7／9 条，本包新登记） | 六个码**已在册**但消费点未落，原症状仍在：**#2** `preflight.py:320` 建索引前查重（`DESIGN_CARD_DUPLICATE_KEY`；违 M18 [L1102] T4 粒度=策略×版本，重复键静默取后一行可能把 MISSING 卡盖成 COMPLETE=V-14）；**#3 模块侧** `triangulation.py:380-388`／`:420-426` 把零方差的一对 rho 与 agreement 置 None 时未带 `SPEARMAN_ZERO_VARIANCE` 进 `report.flags`（下游只读 flags 会漏判）；**#4/#5** `weights_combine.py:683-690` 未按 violations 逐条 append H2／H3／H5_SHIFT（`ALPHA_INFEASIBLE` 留给「可行集为空」`L631`）、`:475-481` 红线指标排除出熵权组合时未逐指标披露 `REDLINE_EXCLUDED_FROM_ENTROPY`；**#7** `preflight.py:215-237` 的 C-03 仍沿用 `CONFIG_SEMANTIC_ERROR`，应换 `WEIGHT_DICT_MISALIGNED`（M22 [L902] 逐字 BLOCK）并同步 `RUN_BLOCKING_CODES(:36-40)`／`DISCLOSURE(:42-49)`；**#9** `attainment.py:524`（ZERO 合成行）／`:528`（SKIP）／`:532`（IMPUTE）的 `reason_code=None` 应改 `MISSING_FACT_RULE_APPLIED`（**不得**挪用 `MISSING_RATE_WARN`，其 message 绑定「缺失率超过预警阈值」，挪用即虚报） | 逐条归属（ORCH-42 第3条）：#2→A1c／C2b（唯一性更可能在 io／models 层落地）；#3→D4；#4/#5→A2b；#7→C2；#9→B1b／A1c。P2-wire-A 一律**未代改**（写集禁写），其对 `preflight.py` 的授权仅 209-211 等价性核验 | P2-wire-B + 上述各归属包 | 是 | 换码后必须复核 `tests/test_preflight.py:240`（`all(f.code == C-03 and f.blocks_run)`）与 `:451` 的一致性断言，**不得弱化**；渲染侧披露位已由 P2-wire-A 落在 `reports.py:591-601`（⑧ 段 + `triangulation.md`）；依据 [L631]／[L62] D2 约束①／[L1140]／M18 [L1134]／M22 [L903]／M31 [L1411] G-09 四分支须各不相同 |
| G-16 | LOO 影响力排名的出口面（三载体分别定性） | MD 面／CSV 面／CLI 摘要面三者状态不同，须分别披露，不得笼统称「已闭环」 | **MD 面已闭环**（P2-wire-A @`53ed80c` 第⑧项：`report.md` ⑦ 段渲染逐指标排名 + loo_impact_max + 「存在单一指标过度影响」文案，与 `loo_dominant_metrics` 并列呈现，`loo_impact` 为空元组时显式披露「本轮未执行 LOO」，数值 Decimal 原样不经 float）；**CSV 面本 RUN 不做**（ORCH-42 第4条：`reports.SENSITIVITY_COLUMNS` 13 列无 metric_id／loo_impact，把 metric_id 塞进 `strategy_id` 列会污染列语义，扩列即改**契约面表头**且 `tests/test_reports.py:355` 已钉表头，属契约变更而非接线，且 E2b／E3b golden 面在飞会引发不可控重写）；**CLI 摘要面**被 G-14 的 marshal 缺位挡住 | CSV 面：主控已裁本 RUN 不做，登记为 **K-32** 待签认；CLI 摘要面：随 G-14 | 否 | MD 面闭环即视为本 RUN 达标（ORCH-42 第4条）；V-5（契约列不得静默增删）风险已规避；接线后 `output_fingerprints` 必变、`reproducibility_hash` 不受影响 |
| G-17 | G-14 的**上期 PoolStats 载体缺位**（本包新登记） | `Inputs`（[L891]）无 `previous_pool_stats` 列、`AuditBundle`（[L1051] 十六列）无 `pool_stats` 列，而 `models.py` 属 MODELS-1／LOO-1 独占写集 | `_previous_pool_stats()` 现阶段只能返回 None，报告**显式披露「本期不可比」**（符合 V-14：不造假基线） | 主控裁（契约级变更）；本 RUN **不做**（ORCH-42 第5条） | 否 | 见 `dsm_stage/G14FIX/NEED-CONTRACT.md` 与 `dsm_stage/P2-wire-A/NEED-WIRING.md` 第 10 条；登记为 **K-33** 待签认 |
| G-18 | `loo_impact` 未补进 ORCH-22 契约表（K-25） | `docs/adr/ORCH-22.md` 裁决 25 的 `SensitivityReport` 字段表与 `docs/adr/ORCH-22-review-S1-T04.md:136` 对账表均无该字段 | P2-wire-A 已按主控指令**沿用 `loo_impact` 原名**、未自创别名；`docs/**` 属禁写面，本包亦无权改 | 主控（后续 ORCH 补录） | 否 | R-15 授权 + ORCH-22 契约表同步要求（LOO-1 NEED-WIRING 第 5 条） |
| G-19 | whatif 的 GEOMETRIC 近似归因本 RUN 不做（⚠️ **编号撞号**） | 派工单要求登记为 `D-A4-02`，但 `ops/dag-state.json → defects` **已存在** `D-A4-02`（`dsm/whatif.py:571` 裸字面量，status=CLOSED，fix_commit `9078201`）——两者不是同一件事 | 现状：`dsm/whatif.py` 非 LINEAR 一律抛 `WhatifOperatorError(CONFIG_SEMANTIC_ERROR)`，**不出近似归因**（G-A4-1）；`APPROXIMATE_ATTRIBUTION` 码已注册备用（见 B-7） | 下一版本；**编号请主控改号**（同 L-12：编号单点分配权在主控，本包不自占 `D-A4-02`） | 否 | 本包按派工单登记内容但不复用已 CLOSED 的同号缺陷，避免台账混淆 |

## 汇总计数（**P3c-pre2 重算：与正文逐条列举同源生成，已回读自证相等**）

- 条目总数：**A 10 + B 10 + C 8 + D 7 + E 8 + F 2 + G 19 = 64 条**（脚本回读实测 64 行，与各节逐条列举数一致）。
- 「是否阻塞交付」= **是：16 条** —— C-1、C-2、C-3、C-4、C-5、C-6、C-8；E-6、E-8；F-1、F-2；G-2、G-3、G-8、G-14、G-15。
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
| D-6（原24） |  D-A1-05：design_card 为 JSONL 而 io_loaders 只认 CSV／Parquet 且空串→None  |  **已落地**：A1d 按 ORCH-41 第1条 R2 的列级口径修（新增 `_required_text_columns()` 与 `TEXT_AS_IS_COLUMNS`），fixtures 零改动；spine 7 红 → 1 红  |  A1d @`f27334d`  |  **否**（扣减；剩余 1 红 A1d 实测归因归 G14FIX 写集，全量终值 PLACEHOLDER-TO-REFRESH(P2-wire-B)）  |
| E-6（原24） |  M00 L294 的 L0b 目标清单非穷尽（E5 GAP-E5-09 自标 BLOCKING，阻断 A3／A4 转绿）  |  未见闭合裁决  |  —  |  **是**（保持）  |
| E-8（原24） |  Step8(sensitivity) 在 Step7(pooling) 之后 → FLIP_RATE_UNUSABLE 首过必然无载体  |  C5 已显式处理（`PRIMARY_POOL_REJECTED_ROBUST`，非静默）；是否加「Step8 后回跑 Step7」仍待裁  |  —  |  **是**（保持）  |
| F-1（原24） |  **G5** D6 证据复核未完成 → 复核前全面禁用（M39 L40／SDD L1792）  |  未完成，本 RUN 无复核产物；代码侧与之相容（未验证载体一律显式异常）  |  依赖行方／D6 复核方  |  **是**（保持）  |
| F-2（原24） |  **G7** 治理配置未签认 → K 项全部未脱 PLACEHOLDER（M39 L42／SDD L1794）  |  未完成且**无载体**：`config/` 实测 0 文件，真实运行被 `EXIT_CONFIG=3` 拒绝（**设计如此，非 bug**）  |  依赖行方（评价管理委员会）  |  **是**（保持）  |

**扣减合计 13 行**（A-10；B-2／B-3／B-4／B-5／B-7／B-8；D-1／D-2／D-3／D-4／D-5／D-6）→ 原 24 − 13 = **11 行保持阻塞**（C-1~C-6、C-8；E-6、E-8；F-1、F-2）。其中 B 类 6 行属「注册面闭合、接线残项移入 G-15」，D-6 属 A1d 已落地。

### 本包新增的阻塞项（5 条，均在 G 节）

| 新增项 | 为什么算阻塞 | 归属 |
|---|---|---|
| G-2（新增） |  D-A1-06 的 golden 手算值不自洽（1.900000／1.5346 vs 手算 1.810000000000／1.507600000000）→ 全量无法转绿  |  E2b  |
| G-3（新增） |  D-A1-07 的陈旧常量未按 E3PREP 独立手算更新 → golden_b 无法转绿（口径已裁、落实未完）  |  E3b  |
| G-8（新增） |  `MIX_QUALITY_DEGRADED` 在 CLI 端到端面仍不可达（seam 无生产调用点）→ V-14「算出而不披露」未全闭合  |  P2-wire-B／主控  |
| G-14（新增） |  **M29 九步 marshal（[L1330]-[L1358]）本体未落地**：`_chain_gate` 在模块齐全时仍 raise InvariantError（退出码 5），CLI 端到端不可用，触碰 INV-2（M00 L301）  |  P2-wire-B／主控  |
| G-15（新增） |  reason_code 接线待办 6 条未落 → 重复键静默取后一行、C-03 沿用泛码、合成行 reason_code=None 等**静默降级**症状仍在（V-14）  |  P2-wire-B + A1c／C2b／A2b／C2／B1b／D4  |

**最终权威计数 = 11（原 24 中保持）+ 5（本包新增）= 阻塞 16 条；非阻塞 48 条；合计 64 条。**

- SP-1 台账 21 条中 BLOCKING 7 条、SP-2 wave 新增缺口 70 条（计数实测于 dag-state）：本表收录其**未闭合且有裁决记录**的部分；各包 GAPS 全文按 SP2 note 只存在于 lane 会话／上报行，状态文件不重复存。
- **本文件内的 PLACEHOLDER-TO-REFRESH 清单（R-12）**：① 最终全量 pytest 的 failed／passed／collected → `PLACEHOLDER-TO-REFRESH(P2-wire-B)`（当前已入账权威基线仅到 `after_MODELS1` = 11 failed／2190 passed／2201 collected @ `cc18a38`，其 11 红逐条拆分本身也是 PLACEHOLDER）；② 最终 `reproducibility_hash` 与 `output_fingerprints` → `PLACEHOLDER-TO-REFRESH(P2-wire-B)`（P2-wire-A 结论：hash **unchanged**，因 `audit.py:242` 只吃 score_card／grade_ledger／weight_version_id，但 `report.md` ②⑥⑦⑧ 段文本变了 → fingerprints 必变；现值 `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` @ `42d5346`，旧值 `e5fa8ae0…`／`4de4b8cb…`／`8083efc9…` 一律保留供披露，**严禁修回**）；③ `git rev-list --count origin/main..HEAD` → `PLACEHOLDER-TO-REFRESH(主控 push 前重测)`；④ `git tag -l` 实测 **0** 条，`v1.1.0` 由主控最后统一执行；⑤ K-07 的 `min_sample_size_for_A`／显著性水平／MDE 无代码落点；⑥ G5／G7 的签认产物；⑦ 异机第二人复跑结论（P3b）；⑧ `cel_contract_version`（`cli.py:281-286`，[L1897] 首版固定为占位版本 → K-31）。
