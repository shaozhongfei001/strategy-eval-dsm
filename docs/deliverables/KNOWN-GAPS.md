# 已知缺口清单（KNOWN-GAPS · P3c-prep 前移建表）

- 性质：§3.2 第 239 行 P3c 交付物中「**已知缺口**」部分的建表与填满（README / `git tag v1.1.0` 由 P3c 在 P2 收口后执行，本包未打 tag、未改 README.md）。配套文件：`docs/deliverables/K-SIGNOFF-CHECKLIST.md`。
- 事实来源与核实方式：`ops/dag-state.json`（contract_gaps_pending 41 条 / gap_adjudications_SP1 / gap_adjudications_SP2 / r15_batch_2 / defects / orch_lessons）、`docs/adr/RUN-ORCH-25..30`、各 lane 缺口档案（`dsm_stage/{E5,A4,C2b,B1b,SEAM-1,EFIX-1,A1b}/`），以及**本包对代码的 grep 实测**（观测 HEAD `aa4a9ba`，2026-11-25）。lane 自述与代码实测不符处以**实测为准**并写进「备注」列。
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
| A-10 | 归一/池化接缝的模型位 | D-MODELS-01（models.py + normalize.py 契约位） | 未动（等 SEAM-1 收口） | MODELS-1（ORCH-29 第 4 条） | 是 | dag-state defects 实测 status=OPEN |

## B. reason_code 类（R-15 batch-2 · `r15_batch_2.status=queued`，blocked_on=EFIX-1 的 test_architecture ratchet 32 对，`tests/test_architecture.py:540` 实测在案）

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| B-1 | design_card 表级缺失 | `DESIGN_CARD_TABLE_ABSENT`（BLOCK）未注册（C2b 上报） | C2b 实测（`dsm_stage/C2b/NOTES-C2b.md` §2 三期 diag）：C-08 已是策略级 blocks_run=False，无表级 BLOCK 行为 | 主控 R-15（先盘点触发场景） | 否 | **张力**：ORCH-30 撤回表级 BLOCK 后，该码触发场景是否还存在须先盘点再注册 |
| B-2 | 卡索引遇重复 strategy_id×version | 专用码未注册（名称待盘点，C2b 上报） | 现**静默取后一行**（r15 原文：「违 M18 L1102，属 V-14 静默降级」） | 主控 R-15 | 是 | 静默降级在修复前持续存在 |
| B-3 | Spearman 一方零方差 | 零方差处置码未注册（D4 gap7 / SP2） | `dsm/numeric.py:211-215` 抛 DivisionUndefinedError；`dsm/diagnostics.py:233-235/281` rho 置 None，**不编字面量** | 主控 R-15（与 ADJ-1 同批） | 是 | grep 注册表无 Spearman/零方差相关码（实测） |
| B-4 | 标定 H-2/H-3/H-5 与红线排除 | 专用码未注册（A2 上报） | `dsm/weights_combine.py:673`（H-2）/`:661`（H-5）以布尔判据 + CombineError 路径表达，未落码 | 主控 R-15 | 是 | |
| B-5 | 一级库准入 grade≠L1 | 专用码未注册（C5 上报） | 用 PRIMARY_POOL_REJECTED_EVIDENCE / _ROBUST（`dsm/reason_codes.py:84-85`）近似表达证据/稳健两类否决 | 主控 R-15 | 是 | |
| B-6 | C-03 权重未归一 | C-03 专用码未注册 | `dsm/preflight.py:215-237` **沿用 CONFIG_SEMANTIC_ERROR**（注释实测在案）；`dsm/config.py:665-676` 同样单一码 | 主控 R-15 | 否 | message 已含判据描述（SP2 原文口径） |
| B-7 | GEOMETRIC 算子近似归因 | `APPROXIMATE_ATTRIBUTION` 未注册（M10 [L674] 要求，A4 上报） | `dsm/whatif.py` 非 LINEAR 一律抛 WhatifOperatorError(CONFIG_SEMANTIC_ERROR)，**不出近似归因**（G-A4-1） | 主控 R-15 | 是 | grep 注册表无 APPROXIMATE_ATTRIBUTION（实测） |
| B-8 | missing_rule=ZERO/IMPUTE 合成分出行 | 「事实行缺失已按 missing_rule 处置」码未注册（B1b 上报；不得挪用 MISSING_RATE_WARN） | 合成行 reason_code=null（r15 原文口径，未编造字面量，R-12 合规） | 主控 R-15 | 是 | |
| B-9 | digest 码名与注册名不一致 | M05/M31/M37 用旧名（详见 E-4） | ADJ-3：一律用注册名 GR_CAPPED_NO_TARGET / GR_EVIDENCE_GATE_L1 / GR_VERSION_BREAK / GR_STREAK_NOT_MET / GR_REDLINE_FORCED | 设计方更正 digest（本 run 不改冻结 digest） | 否 | 实测 `dsm/reason_codes.py:60-61` 注册名在案 |
| B-10 | 注册表盘点口径 | r15 纪律行称「先盘点已注册 79 码」 | — | 主控 | 否 | **实测 81 条**（`dsm/reason_codes.py` `_DEFS` 条目行计数）；79 为过时口径，盘点基准应以实测为准 |

## C. 口径待签认类

| # | 条件 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| C-1 | Step7 占比双报 | 两个分母口径（同域已参评 / 全体已参评，均剔 NOT_ASSESSED）为 C5 自裁 | SP2 gap6：主控核可「属口径裁决非数值拟定」，标记**待行方签认**并入 K 清单 | 行方（P3c 签认回合） | 是 | 未进 M38 K-01~K-20 编号表，签认时须新立编号 |
| C-2 | normalize/pooling 池样本下限 | `min_pool_size` 的 yaml 键位未签认：现**复用 eval_config.normalize.min_pool_size**（[L943] 只在 normalize 块给过该键） | `dsm/normalize.py:42/70`（自述「缺口 4：键位未签认」）；`:104-109/124` 必填 StrictInt 无默认 | 行方 + 设计方确认键位 | 是 | SMALL_POOL（reason_codes.py:51）与 [L1005] POOL_TOO_SMALL 共用该阈值 |
| C-3 | IMPUTE_MEDIAN 的样本范围 | `impute_scope` 默认 **ALL_ROWS** 是代码拟定，digest 未给默认 | `dsm/attainment.py:149`（IMPUTE_SCOPE_ALL='ALL_ROWS'）、`:546`（run 形参默认值） | 行方签认默认方向或改必填 | 是 | 与 ADJ-2「必填无默认不猜数」相悖的实测反例之一（另见 C-4/K-08/K-11/K-15/K-20 的代码默认） |
| C-4 | 三角验证配置 | `gra_norm` 键名拼写与取值 `initial/mean` 由模块自定；`rho`、`divergence_threshold`、`enabled` 值未签认 | `dsm/triangulation.py:50-58`（CFG_KEYS=(enabled,rho,divergence_threshold,gra_norm)）、`:125-131`（缺键抛 MissingConfigError，不猜）；enabled 强制显式 bool（`:136-142`，H-5） | 行方签认值；键名请设计方确认 | 是 | |
| C-5 | 标定 [L540] 边界 epsilon | `shift` 必填但 digest 无值 | `dsm/weights_calibrate.py:266/708-709`（缺失即抛，不猜数 R-12） | 行方签认 | 是 | |
| C-6 | 标定窗口期数下限 | 窗口语义（N≥?）原文未给：代码取「两期起」而 M39 RK-10 要求「N<3 回退 α=1 + ENTROPY_INSUFFICIENT_SAMPLE 首屏披露」 | `dsm/weights_calibrate.py:135-138`（WindowError：<2 期或期名未知即抛；两期为下限，理由 [L619] 相邻期距离）；RK-10 回退由 insufficient_sample_error 注入钩子承接（`:30/:118`） | 设计方确认「恰 2 期」走哪条 | 是 | 两机制并存，边界情形未见原文钉死 |
| C-7 | `dsm/cli.py` calibrate 命令 | cmd_calibrate 把 `eval_config.weight_construction.window` 原样转发 calibrate，且仅捕获 TypeError | `dsm/cli.py:330-341`（实测 except 只有 TypeError） | EFIX-1 后续（异常面收敛） | 否 | EFIX-1 上报成立：window 期名未知/短于 2 期时 **WindowError 不被捕获**（grep dsm/cli.py 无 WindowError，实测），会以未处理异常崩而非受控退出码 |
| C-8 | Saaty RI 表 / 「并列最不一致前 5 对」度量 / SHORTFALL_CLAMPED | RI(n) 表值、不一致度量口径、第四公式均为公开标准值或推断实现 | ADJ-6：采纳 Saaty 标准表（n=1..10，n>10 抛 AhpError），provenance 写明来源 + 进 K 清单待行方确认；度量取 \|ln(a_ij·w_j/w_i)\| 推断；ADJ-7：SHORTFALL_CLAMPED 保留实现但标记「推断，待设计方确认」，V 表不得记已验证 | 行方确认（RI/度量）+ 设计方确认（第四公式） | 是 | contract_gaps B1（BLOCKING）/D1（BLOCKING）实测 |

## D. 缺陷类（`ops/dag-state.json` defects 中 status ≠ CLOSED 的全部条目，实测）

| # | 缺陷 | 缺什么 | 当前 WORKAROUND | 闭合责任方 | 阻塞交付 | 备注（实测） |
|---|---|---|---|---|---|---|
| D-1 | D-SEAM-01（normalize×pooling 接缝） | 单例池 sd=0 不出 composite_relative + pooling 对 null 抛 PoolingInputError → M29 Step7 中断，卡 golden G-01/G-02/G-04 与 spine×14 | SEAM-1 修复已按 ORCH-28 落地（`dsm_stage/SEAM-1/NOTES-SEAM-1.md`：事实认定+手算逐位验证+回归归因） | 主控收口（defects 表状态仍是 OPEN，**待主控翻转**） | 是 | **状态文件与 lane 档案不同步**：defects.status=OPEN vs SEAM-1 已交修复+测试 |
| D-2 | D-MODELS-01 | models.py/normalize.py 契约位（见 A-3/A-10） | 未动（等 SEAM-1） | MODELS-1（ORCH-29 第 4 条） | 是 | OPEN |
| D-3 | D-A1-02 | 冻结 fixtures 4 条 DID+CONCURRENT_CONTROL 卡缺 alt_method_note/interpretation_limit → 实测证据分布 A3B0C4D6 ≠ manifest 声明 A3B3C4D2；G-04/G-08 subject 落 NOT_ASSESSED | fixtures 现状使用（G-04/G-08 仍 RED） | A1c → E2b（等 P2a 落地） | 是 | SEAM-1 档案确认 G-04/G-08 仍 RED 归因于此 |
| D-4 | D-A1-03 | fixtures（事实表）缺陷 | 未修 | A1c | 是 | OPEN |
| D-5 | D-A1-04 | fixtures（权重文档）缺陷 | 未修 | A1c | 是 | OPEN |
| D-6 | D-A1-05 | fixtures 或 io_loaders 格式归属二选一（按 M21/M18 原文） | 未定 | A1c 或 C1c | 是 | OPEN |
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

## 汇总计数（实测）

- 条目总数：**A 10 + B 10 + C 8 + D 7 + E 8 + F 2 = 45 条**。
- 「是否阻塞交付」= 是：**19 条**（A-10；B-2/3/4/5/7/8；C-1~C-6、C-8；D-1~D-6；E-6、E-8；F-1、F-2）。其中纯依赖行方签认的：C-1~C-5、C-8、F-2，及 K 清单全部 20 项。
- SP-1 台账 21 条中 BLOCKING 7 条、SP-2 wave 新增缺口 70 条（计数实测于 dag-state）：本表收录其**未闭合且有裁决记录**的部分；各包 GAPS 全文按 SP2 note 只存在于 lane 会话/上报行，状态文件不重复存。