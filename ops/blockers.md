# ops/blockers.md — 待签认 / 待补登记簿（ORCH §10.2）

> 规则：无人值守下遇到「需要人签认」或「文档/环境/契约缺口」一律在此登记，写 `PLACEHOLDER` 后
> 用合成数据继续，**不停机、不拟定业务数值**。每条须写：缺什么 / 谁签认 / 完成条件 / 是否阻塞。

## 一、环境与文档缺口

| 编号 | 类型 | 缺什么 | 谁签认 | 完成条件 | 阻塞? | 登记时间 |
|---|---|---|---|---|---|---|
| B-001 | 环境漂移 | 只读邻仓 `/home/szf/dev/CampaignLab` 的 tag `R19-S14add` 实测不存在（`git tag -l` 为 0 个、`git show-ref` 无该 ref），与 `ops/dag-state.json` 原描述不符 | 邻仓无人值守 DAG 的负责人 | 确认该 tag 是被 DAG 移动/删除还是从未创建；确认后回填 dag-state 的 `readonly_neighbors` 描述 | 否（§10.1-2 只比对 `status --porcelain` 与 HEAD，二者已快照：branch=m0-framework / HEAD=0cccb76 / porcelain 空 / rev-list=154） | 2026-11-23 |
| B-002 | 文档缺口 | `docs/ORCHESTRATION-v1.0.md` 正文无 §8.2「三级自续跑」（§8.1 之后直接进 §9），但 `dag-state.json` session_log seq=1 与启动提示词均引用「按 §8.2 选 T1/T2/T3」 | Orchestrator 规程维护者 | 补写 §8.2 的 T1/T2/T3 定义；在此之前按提示词给出的语义执行：T1=直接进下一阶段；T2=运行时支持则自动开新会话续跑（本运行时**无** `create_thread` 工具，不可用）；T3=打印续跑提示词全文并把「现在从第 0 步开始」替换为「从 next_task = <task_id> 继续」 | 否（有明确 fallback 语义） | 2026-11-23 |
| B-003 | 契约归属 | `metric_dict.csv`（K-14）含 `target_value` 等业务数值，按 H-5 须拦 PLACEHOLDER，但 SDD [L877] 的 config.py 加载清单不含该 csv（由 io_loaders 读取，[L888]），拦截归属 SDD 未明说 | 评价管理部门（指标负责人）+ 设计方 | 确认 PLACEHOLDER 拦截归属。当前按 `docs/adr/ORCH-12.md` 执行：config.py 出可复用扫描器（S1-T05）→ io_loaders 逐行复用（S3-T01）→ preflight 合并成一次性清单（S3-T02） | 否（已有保守超集裁决，S1 不阻塞） | 2026-11-23 |
| B-004 | 契约缺口 | `ScoringContext` 在 SDD 全文仅 [L1014] 作为签名类型名出现，**无字段清单** | 设计方 | 确认字段闭包。当前按 `docs/adr/ORCH-13.md` 裁决 1 实现（运行上下文 7 字段 + Step 1-4 结果 8 字段，每字段均指回 SDD 行号）；R4 逐字段核对，指不回原文的字段一律删除 | 否（§10.2-4 预留并登记） | 2026-11-23 |
| B-005 | 契约缺口 | `NormalizedFrame`（[L939-945]）与 `RedlineFrame`（[L988-994]）SDD 只给签名+语义，**未列逐字段表**（其余 5 个 Frame 均有字段行） | 设计方 | 确认字段表。当前按 `docs/adr/ORCH-13.md` 裁决 2 取「语义所需最小字段集」并逐字段标注推导依据行号 | 否（同上） | 2026-11-23 |
| B-006 | 计量缺口 | 本运行时**未向 Orchestrator 暴露子智能体的 token 计量**（`spawn_agent` / `wait_agent` 均不返回 usage），ORCH §3.4 成本护栏中「flash ≤ 35% token 消耗」「max ≤ 65% token」两项**无法用实测数字核算** | Orchestrator 规程维护者 / 运行时提供方 | 运行时提供 per-agent token usage 回传；在此之前 §3.4 只核算可实测的三项：任务数按 C1/C2/C3 分布、低档任务数占比 ≥60%、升级次数与返工轮次。`dag-state.json` 各任务 `tokens_used` 一律记 `null`（**不估算、不编造**，H-10），阶段对账单第④段的 token 列一律记 ❌ 无实测证据 | 否（不阻塞开发；阻塞的是成本护栏的完整核算，交付时如实披露） | 2026-11-23 |
| B-007 | 口径沉默 | SDD [L1265]（金额=int）/[L1266]（计数=int）/[L1267]（比率=Decimal）三类口径**均未覆盖 `unit = DURATION_SEC`（秒数）**，而 [L1138] 的 unit 枚举含该值 | 设计方 / 评价管理部门 | 确认秒数列的数值口径（int 秒 / Decimal 秒 / 是否需 quantize）。当前按 §10.2-4 不发明口径：`MetricDictRow.target_value` 与 `RedlineRow.threshold_value` 在 `unit = DURATION_SEC` 时**不加类型约束**（仍受多态联合约束：int 落 int、Decimal 落 Decimal、float/bool 拒）。见 `docs/adr/ORCH-14.md` GAP-1 | 否（S1 不阻塞；S4 attainment 计算 INTERVAL 公式时需先闭合） | 2026-11-23 |
| B-008 | 职责归属 | `MetricFactRow.value` 在 `unit = MONEY_MINOR` 时仍接受带小数 Decimal（R4 实测 `Decimal('100.50')` 被接受）。MetricFactRow 不含 unit，模型层无从判定 | 数据部门 + 设计方 | SDD [L889] 已把「金额列必须解析为 int（失败即记 C-09）」指派给 **io_loaders**，故转为 **S3-T01 的验收项**：io_loaders 须结合 metric_dict 的 unit 对 T3 金额列强制 int，失败记 C-09；S3-T03 须有对应 golden。见 `docs/adr/ORCH-14.md` GAP-2 | 否（S1 不阻塞；**S3-T01 必须闭合**，否则 H-4 在数据入口失守） | 2026-11-23 |
| B-009 | 职责归属 | `RedlineRow.threshold_value` 与其所引用指标（`metric_id`，[L1180]）的 `unit` 一致性无法在模型层校验（RedlineRow 不含 unit） | 风险/合规/消保 + 评价管理委员会 | 转为 **S1-T06 的验收项**：config 语义校验 [L879]「红线阈值引用的指标必须存在于 metric_dict」须一并校验阈值类型与该指标 unit 口径一致（MONEY_MINOR/COUNT → int，RATIO → Decimal），不一致记 `CONFIG_SEMANTIC_ERROR`。见 `docs/adr/ORCH-14.md` 裁决 2 | 否（S1-T02 不阻塞；**S1-T06 必须闭合**） | 2026-11-23 |
| B-010 | 职责归属 | 模型层按 `docs/adr/ORCH-18.md` 收紧后（int 列拒 bool/float/str、bool 列只收 True/False），CSV 里的文本字面量（`true` / `1` / `yes`）必须在入口处显式转换，否则 S3 加载会大面积报错 | 数据部门 + 设计方 | 转为 **S3-T01 的验收项**：io_loaders 须提供**可审计的显式转换表**（列出接受哪些字面量），无法识别的字面量必须报错并记 reason_code（金额列依 [L889] 记 C-09），**不得**默认成 False / 0；S3-T03 须有对应 golden 负例 | 否（S1 不阻塞；**S3-T01 必须闭合**） | 2026-11-23 |
| B-011 | 流程缺陷 | 主控与子智能体**共用**临时目录 `C:\Users\szf\AppData\Local\Temp\dsm_ops\`，导致主控的 `verify.py` 在 22:27 被 R6 的同名探针脚本覆盖（实测：文件由 4742B 变 757B、内容非主控版本），主控一度执行到别人的脚本 | Orchestrator（主控） | 已即时处置：主控工具迁至私有子目录 `dsm_ops\_orch\`（`orch_verify.py` 等）；后续所有派工 prompt 强制要求子智能体把临时脚本放 `dsm_ops\<task_id>\` 子目录，**禁止**直接写 `dsm_ops\` 根。本条留档以说明本会话该次异常输出的成因 | 否（已处置） | 2026-11-23 |
| B-012 | 流程缺陷 | S1-T02 落库时 commit `ffa9a30` 的 message 正文把 8 个输入 Row 写成 `CardMetaRow / CardWeightRow / TargetRow / ThresholdRow / PenaltyRow / SampleRow` 等**代码中不存在的类名**；来源是上一会话交接摘要的转述而非实测。落库后用 `vars(dsm.models)` 比对发现（实测 8 个 Row 为 `StrategyMasterRow / MetricDictRow / MetricFactRow / DesignCardRow / RedlineRow / WeightVersionDoc / GradeRuleRow / AnchorSetDoc`） | Orchestrator（主控 R5） | H-12 明文禁 `--force` 与改历史，commit 已 push → **不 amend**，以 `docs/adr/ORCH-19.md` 作权威勘误；`dag-state.json` 的 evidence 一律按实测值写入。**整改**：commit message 与 evidence 中的一切类名 / 文件名 / 计数 / 行号，必须在写 message **之前**由脚本实测取得（`vars(module)`、`grep -n`、`wc -l`、`pytest --collect-only`），禁止从交接摘要、任务标题或记忆推断（ORCH §8 实测优先同样适用于 message 文字） | 否（已勘误） | 2026-11-23 |
| B-013 | 证据留存缺口 | S1-T02 的 L1（R3 先写 RED 测试）轮**原始 pytest 失败日志未留存**：`dsm_ops/` 下无任何含 `ModuleNotFoundError` 的输出文件，RED 事实目前只有 R3/R4 的转述，主控无法在落库时二次核验「失败原因是功能未实现」（§7.2 L1 判据） | Orchestrator（主控）+ R3 | 不追溯伪造。**整改（S1-T03 起强制）**：R3 交付时必须把 RED 轮完整 pytest 输出存为 `ops/evidence/<task_id>/L1-red.txt`（含 collect error 或 failed 计数与首条 traceback），R2 实现后再存 `ops/evidence/<task_id>/L3-green.txt`；派工 prompt 逐字写入该要求，R4 复核项增加「两份日志存在且 RED 早于 GREEN」 | 否（不阻塞 S1-T02，S1-T03 起生效） | 2026-11-23 |
| B-014 | 工具缺陷（本会话新踩） | 主控 staging 脚本 `mk_stage_t02.py` 把 STAGE 写成 Windows 路径 `C:/Users/.../dsm_stage_state_S1T02` 后交给 **WSL Linux python** 执行；Linux 侧不认 `C:` 盘符，把它当**相对路径**，于是在 cwd（`/mnt/d/ws/codex_rd/ss_campaignlab`）下建出了一个名为 `C:` 的目录树，文件写进误建目录、rsync 拿不到 → `ops/blockers.md` 静默漏改（porcelain 未显示 M，靠 `grep -c B-012` = 0 才发现） | Orchestrator（主控） | 已处置：内容抢救到正确 staging 后 `rm -rf` 误建目录（删前逐层 `find -printf` 核实仅含本次生成的 1 个文件；11-13 遗留的 `D:` 目录与 `C:Usersszf...` 文件未触碰）。**整改**：一切在 WSL 侧执行的脚本，路径一律用 `/mnt/c/...` 形式；写文件后必须立即 `wc -c` + `grep` 断言目标文件真实存在于预期路径，不得只看脚本自己打印的 WROTE 输出 | 否（已处置） | 2026-11-23 |
| B-015 | 工具缺陷（本会话新踩） | `_orch/set_task.py` 首版以**工作树**的 `ops/dag-state.json` 为基线。第一次 rsync 已把递增后的状态写进 repo，第二次重跑即基于已递增副本再加一遍 → counters 实测由 `flash2/max1/esc1/rework4` 变成 `flash3/max2/esc2/rework6`，且 session_log 会重复追加同一会话条目（虚增成本护栏分母，直接污染 §3.4 与阶段对账单第④段） | Orchestrator（主控） | 已处置：基线改为 `git show HEAD:ops/dag-state.json`（与工作树解耦 → 真正幂等），并 `git checkout -- ops/dag-state.json` 回滚被污染的工作树副本后重跑；实测 counters 单次递增正确（flash 1→2 / max 0→1 / esc 0→1 / rework 2→4，session_log 3→4，ancestors 8 项无重复）。**整改**：一切"读状态-改-写回"的工具必须以 git HEAD 或显式快照为基线，禁止读工作树；每次落库后用 `cmp_state.py` 对比 BASELINE vs STAGED 逐项核对递增幅度 | 否（已处置） | 2026-11-23 |

## 二、K-01 ~ K-20 业务数值待行方签认（H-5：一律写 PLACEHOLDER，严禁拟定）

> 权威出处：SDD §5.1 [L1734-1757]，压缩表见 `docs/digest/S1-T01e.md`。
> 「原文建议值」是 SDD 的**文字内容**，不是签认值；实现侧一律按 `PLACEHOLDER` 处理（[L1259][L878]）。
> 拦截落点依据 [L877]（config.py 加载清单）与 ORCH-12（metric_dict 归属）。

| 编号 | 参数 | 位置 | 性质 | 拦截落点 | 签认人 | 当前处置 |
|---|---|---|---|---|---|---|
| K-01 | 维度权重 W_d | weights yaml | 治理 | config.py [L877] | 评价管理委员会 | PLACEHOLDER |
| K-02 | 维度内指标权重 w_j | weights yaml | 治理 | config.py | 评价管理委员会 | PLACEHOLDER |
| K-03 | 各级 attainment_floor | grade_rules yaml | 治理 | config.py（单调校验 [L879]） | 评价管理委员会 | PLACEHOLDER |
| K-04 | 红线阈值（投诉率/退订率/触达频次上限/合规违规数） | redlines yaml | 治理 | config.py（引用指标存在性 [L879]） | 风险/合规/消保 | PLACEHOLDER |
| K-05 | attainment_cap | eval_config | 技术 | config.py | 评价管理部门 | PLACEHOLDER |
| K-06 | min_coverage_for_absolute_track | eval_config | 技术 | config.py | 评价管理部门 | PLACEHOLDER |
| K-07 | min_sample_size_for_A / 显著性水平 / 最小可检测效应 | eval_config | 治理 | config.py | 评价管理委员会 | PLACEHOLDER |
| K-08 | promotion_streak / demotion_immediate | grade_rules yaml | 治理 | config.py | 评价管理委员会 | PLACEHOLDER |
| K-09 | 评价周期（MONTH / QUARTER） | eval_config | 治理 | config.py | 评价管理部门 | PLACEHOLDER |
| K-10 | missing_rate_warn / missing_rate_block | eval_config | 技术 | config.py | 评价管理部门 | PLACEHOLDER |
| K-11 | flip_rate 管理阈值（stable_max / review_max） | eval_config | 治理 | config.py | 评价管理委员会 | PLACEHOLDER |
| K-12 | 锚定基准策略集成员 | anchor_set yaml | 治理 | config.py（成员存在性 [L879]） | 评价管理部门 | PLACEHOLDER |
| K-13 | 证据折扣表（仅当 evidence_mode = DISCOUNT） | eval_config | 治理 | config.py | 评价管理委员会 | PLACEHOLDER（原文建议不启用；DISCOUNT 须另立 ADR [L978]） |
| K-14 | 维度指标细项与口径 | metric_dict csv | 治理 | **io_loaders + preflight**（见 B-003 / ORCH-12） | 指标负责人 + 业务部门 | PLACEHOLDER |
| K-15 | alpha_floor | weight_construction（在 eval_config 内 [L1257]） | 治理 | config.py | 评价管理委员会 | PLACEHOLDER（原文建议 0.50，未定值） |
| K-16 | drift_budget | weight_construction | 治理 | config.py | 评价管理委员会 | PLACEHOLDER（原文方法：取历史 drift 分布 P25，未定值） |
| K-17 | boundary_budget | weight_construction | 治理 | config.py | 评价管理委员会 | PLACEHOLDER |
| K-18 | boundary_epsilon | weight_construction | 技术 | config.py | 评价管理委员会 | PLACEHOLDER（原文=attainment_floor 量纲的 2%-5%，未定值） |
| K-19 | min_dim_weight | weight_construction | 治理 | config.py | 评价管理委员会 | PLACEHOLDER（原文建议 >=0.05，未定值） |
| K-20 | max_shift_from_ahp | weight_construction（H-5） | 治理 | config.py | 评价管理委员会 | PLACEHOLDER（原文建议 0.30，未定值） |

**纪律 [L1759]**：K-15~K-20 全部是**治理参数**而非统计参数，必须由人签认，
不得由标定程序自行选择（P-13 机器守护）；α 本身由标定给出，但被 alpha_floor 与 H-5 双重约束。

## 三、门禁签认状态（G5 / G7）

| 门禁 | 含义 | 当前状态 | 完成条件 |
|---|---|---|---|
| G5 | 争议来源未复核 | ❌ 未签认 | 按 §10.2-3：仅允许用合成数据跑通全流程、演示报告样式、做 whatif 预演；**不得输出任何可用于真实资源配置的分数或等级**，此约束须写进每份报告首屏 |
| G7 | 治理配置未签认 | ❌ 未签认 | K-01~K-20 全部由上表签认人签字后方可置为已签认 |
