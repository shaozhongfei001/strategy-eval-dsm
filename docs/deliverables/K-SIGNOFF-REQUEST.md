# 行方签认请求单（K-SIGNOFF-REQUEST · v1.2 RUN · SIGN-1）

- **性质**：本文件是 v1.2 RUN（ORCH-50 增派包 SIGN-1）新建的**对外送签单据**，把 v1.1 移交的 9 条「我方不可闭合」阻塞缺口（`C-1 C-2 C-3 C-4 C-5 C-6 C-8` 口径签认 + `F-1` G5 D6 复核 + `F-2` G7 治理配置签认，含 K-01~K-40）整理为**可一次性送签、逐条可勾选**的清单。配套内部底稿：`docs/deliverables/K-SIGNOFF-CHECKLIST.md`（P3c-final 定稿）、`docs/deliverables/KNOWN-GAPS.md` §C/§F。
- **观测基线**：本包开工 HEAD = `22f8179`（实测 `git rev-parse HEAD`）。本单引用的代码行号凡标注【实测@22f8179】者为 SIGN-1 本包亲自 grep 复核；凡标注【清单实测@`aa4a9ba`】者转录自 `K-SIGNOFF-CHECKLIST.md`（该文件自述观测 HEAD `aa4a9ba`），**未在本 HEAD 逐行复测，行号可能已漂移**，签认前以复核命令重取（见 §7）。
- **R-12 红线声明**：本单所有「现拟定值」列**一律是代码现值 / 主控采纳值 / 夹具合成值**，不是行方签认值；本单**不替行方填任何签认值**，所有勾选位一律空白；不得据本单宣称任何签认已发生。**本单不宣称任何 V 项或 G5／G7 已通过**。
- **首屏声明引用（`README.md` 原文，一字不改地转录，非本包改写）**：「本仓库当前 **G5（D6 证据复核）与 G7（治理配置签认）两道门禁均未通过**……因此本仓库**只能用于合成数据的全流程演练**，**不得输出任何可用于真实资源配置的分数或等级**」。
- **签认前状态红线（`docs/RUN-UNATTENDED-v1.2.md` §1 逐字）**：「不做 **C-1~C-6 / C-8** 口径签认：只能送签，签认前一律标『推断 / 合成待签认』，**V 表不得记已验证**」。

---

## §1 用法（给签认人）

1. 逐行核对「键位／治理项」「现拟定值」「出处」「属性」「需谁签」「不签的后果」。
2. 接受现拟定值 → 在「签认勾选」列打勾并填写：`[ ] 已签认  值=______  签认人=______  日期=______`；改动 → 勾「已签认」并在值栏写新值；否决 → 勾「不签认」并在备注写明替代口径。
3. **载体要求（M39 G7 判据）**：签认结果必须写进 `config/` 的 yaml 载体（`eval_config.yaml`／`weights_*.yaml`／`redlines.yaml`／`grade_rules.yaml`／`anchor_set.yaml`／`ahp_matrices.yaml`【实测@22f8179 `dsm/config.py:76-80`】），且**不得残留 PLACEHOLDER 词表命中值**（词表 `dsm/config.py:84-85`：`PLACEHOLDER/TODO/TBD/XXX` 整值与前缀【清单实测@`aa4a9ba`】；本包复测该四词常量在 `22f8179` 仍在 `dsm/config.py:84-85`）。仅在本单上打勾**不等于**签认完成——完成判据见 §5.4。
4. 属性图例：`公开标准值`＝外部公开文献标准值；`代码拟定`＝实现侧默认／工程容差代用（非行方意志）；`推断实现`＝契约无明文、按语义推导的实现；`纯演练假定`＝仅存在于合成 fixtures／夹具的假定值。

---

## §2 九条阻塞缺口 ↔ 本单在册动作 对照

| 缺口 | 一句话内容（摘自 KNOWN-GAPS §C/§F） | 在册 K 编号 / 送签路径 | 需谁签 | 不签的后果 |
|---|---|---|---|---|
| C-1 | Step7 占比双报：两个分母口径（同域已参评／全体已参评，均剔 NOT_ASSESSED）为 C5 自裁 | **既有文档中无对应 K 编号**——`KNOWN-GAPS.md` C-1 行逐字：「未进 M38 K-01~K-20 编号表，签认时须新立编号」；K 号按 L-12 归主控单点分配，**本包不自行编号**（关联既有 K-21③／K-38 的 12／11／9 三口径留痕） | 评价管理委员会 | G7 阻塞面之一；三口径虽已由 ERRATUM-11 权威化并在 G14FIX @`42d5346` 落地，但**行方签认动作仍未发生** |
| C-2 | normalize／pooling 池样本下限 `min_pool_size` 的 yaml 键位未签认（现复用 `eval_config.normalize.min_pool_size`，[L943] 只在 normalize 块给过该键） | **无对应 K 编号，需新立**（键位签认，连带 C-2 的 SMALL_POOL／[L1005] POOL_TOO_SMALL 共用阈值口径） | 行方 + 设计方确认键位 | 键位不签 → 该治理值无合法载体，真实运行被 `EXIT_CONFIG=3` 拒（§5.2） |
| C-3 | `impute_scope` 默认 **ALL_ROWS** 属代码拟定，digest 未给默认（与 ADJ-2「必填无默认不猜数」相悖的实测反例之一，另见 C-4／K-08／K-11／K-15／K-20 的代码默认） | **无对应 K 编号，需新立** | 行方签认默认方向或改必填 | 中位数填充范围按代码默认出数，口径未经业务确认 |
| C-4 | 三角验证配置：`gra_norm` 键名拼写与取值 `initial/mean` 由模块自定；`rho`、`divergence_threshold`、`enabled` 值未签认 | **无对应 K 编号，需新立**（severity 关联 K-30） | 行方签认值；键名请设计方确认 | 三角验证结论（METHOD_AGREEMENT／DIVERGENCE）不可对外辩护 |
| C-5 | 标定 [L540] 边界 epsilon：`shift` 必填但 digest 无值 | **无对应 K 编号，需新立** | 行方签认 | `dsm/weights_calibrate.py:709` 缺值即抛 `CalibrateError('shift ... is required; no value is invented (R-12)')`【实测@22f8179】→ 标定命令不可跑 |
| C-6 | 标定窗口期数下限：原文未给 N≥几，代码取「两期起」而 M39 RK-10 要求「N<3 回退 α=1 + 首屏披露」，两机制并存 | **无对应 K 编号，需新立** | 设计方确认「恰 2 期」走哪条 | 边界情形行为未钉死，验收无依据 |
| C-8 | Saaty RI 表／「并列最不一致前 5 对」度量／SHORTFALL_CLAMPED 第四公式 | ADJ-6 要求 RI「进 K 清单待行方确认」——**既有文档中未找到该专列 K 编号，编号缺失，需主控按 L-12 补分配**；同行注：G14FIX 的 5 条待签认项已并入 **K-21①~⑤** | 行方确认（RI／度量）+ 设计方确认（第四公式） | `SHORTFALL_CLAMPED` 属**推断实现**，ADJ-7 已裁「保留实现但标记推断，待设计方确认，V 表不得记已验证」 |
| F-1 | **G5** D6 三项争议来源逐字复核 | 无 K 编号——见 **§4 复核单**（A-1／A-2／A-3 三条独立勾选） | 行方 / D6 复核方 | M39 原文状态「**未完成 → 复核前全面禁用（§5.5.3）**」，复核完成前**任何争议来源结论禁止引用** |
| F-2 | **G7** 治理配置签认 | **即本单 §3 全表 K-01~K-40** | 评价管理委员会（治理项）+ 主控（台账／门禁项） | `config/` 已提交 0 文件【实测@22f8179：`git ls-files config` = 0】→ `dsm score` 真实运行被 `dsm/config.py:449 load_all()` 以 `EXIT_CONFIG=3`（`:71`）【实测@22f8179】拒绝，只能跑合成演练 |

注：**C-7（`cli.py` calibrate 仅捕获 TypeError）为非阻塞项**，不在 9 条阻塞缺口之列，本单不设签认动作，仅在此登记提示（归属 EFIX-1 后续）。

---

## §3 K-01~K-40 主表（40 个编号全部在册）

| 编号 | 键位／治理项 | 现拟定值（代码／夹具实际用的值，非签认值） | 出处 | 属性 | 需谁签 | 不签的后果 |
|---|---|---|---|---|---|---|
| K-01 | 维度权重 W_d（`config/weights_*.yaml`） | 无签认值、无已提交载体；集成演练由冻结 fixtures 的合成权重文档代用；DRAFT 权重被拒（`dsm/weights_combine.py:126` AHP_DRAFT_ONLY 门【清单实测@`aa4a9ba`】） | M38 L13／SDD 1738；`dsm/config.py:80` WEIGHTS_GLOB、`dsm/weights_combine.py:302`（清单实测@`aa4a9ba`） | 纯演练假定 | 评价管理委员会（专家组 ≥5 人 + AHP 一致性 CR<0.1） | G7 阻塞核心项；报告 `OPEN_PARAMETER_IDS` 把 K-01~K-20 渲染为 PLACEHOLDER（`dsm/reports.py:80/644`【实测@22f8179】） |
| K-02 | 维度内指标权重 w_j（weights yaml，与熵权按 α 组合后冻结） | 同 K-01：无签认值，fixtures 合成值代用 | M38 L14／SDD 1739；`dsm/models.py:551`、`dsm/weights_combine.py:303`（清单实测@`aa4a9ba`） | 纯演练假定 | 评价管理委员会 | 同 K-01 |
| K-03 | 各级 attainment_floor（grade_rules yaml） | 无签认值；冻结 fixtures 的门槛为**合成治理值**（`dsm/fixtures_gen.py:340` 注释自述【清单实测@`aa4a9ba`】）；M38 原文仅给举例分位锚「如 L1=P80、L2=P50、L3=P20」 | M38 L15／SDD 1740；`dsm/config.py:580/907-1013`、`dsm/grading.py:79/137-164`（清单实测@`aa4a9ba`） | 纯演练假定 | 评价管理委员会（附历史分位与可接受淘汰比例） | 定级四档门槛全为合成值 → 等级不可用于真实资源配置 |
| K-04 | 红线阈值（投诉率／退订率／触达频次上限／合规违规数，redlines yaml） | 无签认值；fixtures 合成阈值代用（M_CONTACT_FREQ_PER_30D／M_COMPLAINT_RATE，`dsm/fixtures_gen.py:316/319`【清单实测@`aa4a9ba`】） | M38 L16／SDD 1741（**明文「不得由模型方拟定」**）；`dsm/redline.py:265` | 纯演练假定（且契约禁止我方拟定） | 行方（引用行内制度／监管阈值） | 红线判定无制度依据 |
| K-05 | attainment_cap（键位 `eval_config.attainment.cap` 等为模块自定） | 无签认值；golden G-03 手算夹具取 Decimal(2)（`tests/test_golden_a.py:51`【清单实测@`aa4a9ba`】）；M38 建议区间 1.5–2.0 | M38 L17／SDD 1742；`dsm/attainment.py:110-116/196-203/230`（清单实测@`aa4a9ba`）；键位自定 = SP-1 记录 BLOCKING | 代码拟定（键位自定）+ 纯演练假定（值） | 设计方确认键位 + 评价管理委员会定值 | 达成率封顶口径未定，绝对轨／相对轨可比性受损 |
| K-06 | min_coverage_for_absolute_track（eval_config） | **无默认，必填**（不猜数）；golden G-04 用「60% 目标缺失→封顶 L3」判据场景（夹具值） | M38 L18／SDD 1743；`dsm/grading.py:29/82/90/153-156/317`（清单实测@`aa4a9ba`） | 无默认，必填 | 评价管理委员会（先实测覆盖率现状，依赖 K-14） | 绝对轨封顶判据无合法阈值 |
| K-07 | min_sample_size_for_A／显著性水平／MDE（eval_config） | **无默认，必填，且代码无落点**（`grep -rn min_sample_size dsm/ tools/ tests/` 无命中【清单实测@`aa4a9ba`】；现状 A 类判定只查关键词 + RANDOMIZED） | M38 L19／SDD 1744；`dsm/evidence.py:38/175/219`（清单实测@`aa4a9ba`） | 无默认，必填（未实现） | 行方（统计口径／AB 平台规范） | Step3 证据 A 类判定不完备，AB 结论辩护力不足 |
| K-08 | promotion_streak／demotion_immediate（grade_rules yaml） | 代码默认 **2 期／True**，取 SDD L965 明文默认（`dsm/grading.py:60-61`【实测@22f8179】），非行方签认 | M38 L20／SDD 1745；`dsm/grading.py:83-84/91-92/198-200/345`（清单实测@`aa4a9ba`） | 代码拟定（契约明文默认代用） | 评价管理委员会（确认沿用或改） | 滞回参数按契约举例值运行，未经委员会决议 |
| K-09 | 评价周期（MONTH／QUARTER／滚动，eval_config） | 无签认值；代码只有字符串期次校验、**无 MONTH/QUARTER 枚举**（`grep -rn QUARTER dsm/ 无命中`【清单实测@`aa4a9ba`】）；load_all 的 period 关键字参 `dsm/config.py:449`【实测@22f8179】 | M38 L21／SDD 1746 | 推断实现（仅字符串期次粒度） | 评价管理委员会 | 周期制式与策略迭代周期是否对齐未经确认，滞回跨期（K-08 联定）悬空 |
| K-10 | missing_rate_warn／missing_rate_block（eval_config） | **无默认，必填**（`dsm/preflight.py:120-121`【清单实测@`aa4a9ba`】）；config 空 → 真实运行到 `dsm/cli.py:264` 即 EXIT_CONFIG（清单实测@`aa4a9ba`） | M38 L22／SDD 1747 | 无默认，必填 | 评价管理委员会（附历史缺失率分布 P75/P95 实测依据） | 缺失率门禁无阈值可执行 |
| K-11 | flip_rate 管理阈值 stable_max／review_max（eval_config.sensitivity） | 双轨不一致：sensitivity 侧**代码默认 0.05/0.15**（`dsm/sensitivity.py:510-511`【实测@22f8179】；清单记 @`aa4a9ba` 为 `:423-424`，行号已漂移），calibrate 侧**必填无默认**（缺键抛 MissingBudgetError，`dsm/weights_calibrate.py:400-410`【清单实测@`aa4a9ba`】）；M38 建议初始 5%/15% | M38 L23／SDD 1748 | 代码拟定（默认恰等于契约建议值） | 评价管理委员会（并裁决 sensitivity 侧默认是否撤销——治理参数不得由代码拟定） | 「由代码给默认」与治理参数定位相抵；D2 敏感性判定依据未签 |
| K-12 | 锚定基准策略集成员 + rationale（anchor_set yaml） | 无签认值；fixtures 合成锚定集代用（rationale='SYNTH-ANCHOR-RATIONALE'，`dsm/fixtures_gen.py:355`【清单实测@`aa4a9ba`】） | M38 L24／SDD 1749；`dsm/models.py:571/578`、`dsm/normalize.py:295/315-325`（清单实测@`aa4a9ba`） | 纯演练假定 | 评价管理委员会（书面选取依据；RK-8 变更须与权重同级签认） | Step2 锚定优先归一与 RANK_REVERSAL_RISK 回退链建立在合成集上 |
| K-13 | 证据折扣表（仅当 evidence_mode=DISCOUNT） | 现状 **GATE_ONLY**，DISCOUNT 未立 ADR 时拒绝给出任何乘数（`dsm/evidence.py:73`【实测@22f8179】；清单记 `:68`，行号已漂移）；折扣表**无代码落点** | M38 L25／SDD 1750（**原文明文建议不启用**） | 代码拟定（现状与契约建议一致） | 评价管理委员会（签认「首版不启用 DISCOUNT」即闭合；若启用须折扣表+审批+敏感性分析+ADR） | 不签则证据折扣是否启用无治理结论 |
| K-14 | 维度指标细项与口径（metric_dict csv：分子/分母定义、方向、单位、目标值） | 无签认字典；合成指标字典代用（fixtures）。**RK-1 明示：K-14 未定则无法产出真实分数** | M38 L26／SDD 1751；`dsm/models.py:291`、`dsm/normalize.py:146-158`、`dsm/io_loaders.py:152`（清单实测@`aa4a9ba`） | 纯演练假定 | 行方按分册 A 三（四）逐条补齐签认（= P0-5，全模型地基；含 G7 判据里的「各指标目标值」） | 全链路地基未定，任何真实分数不可产出 |
| K-15 | alpha_floor（weight_construction） | 双轨：combine 侧代码默认 **D('0.5')**（`dsm/weights_combine.py:135`【实测@22f8179】，注 [L563]）；calibrate 侧必填无默认（`dsm/weights_calibrate.py:192/400-410`【清单实测@`aa4a9ba`】）；M38 建议 0.50 | M38 L27／SDD 1752（「由评价管理委员会确定，**不由数据标定**」） | 代码拟定（SDD 明文 0.5 代用） | 评价管理委员会（委员会决议，P-13/RK-12） | G7 判据点名项（「α 及 K-15~K-20」）；不签 → α 相关标定与组合均无治理依据 |
| K-16 | drift_budget（weight_construction） | **无默认，必填**；config 空即 MissingBudgetError（`dsm/weights_calibrate.py:141` 类注释、`:658` DRIFT 硬约束【清单实测@`aa4a9ba`】）；M38 只给方法（历史 drift 分布 P25） | M38 L28／SDD 1753 | 无默认，必填 | 评价管理委员会（附历史分布实测依据） | 标定 DRIFT 硬约束不可执行 |
| K-17 | boundary_budget（weight_construction） | **无默认，必填**（`dsm/weights_calibrate.py:194/659`【清单实测@`aa4a9ba`】） | M38 L29／SDD 1754 | 无默认，必填 | 评价管理委员会 | 标定 BOUNDARY 硬约束不可执行 |
| K-18 | boundary_epsilon（weight_construction） | **无默认，必填**；且量纲锚 = K-03 attainment_floor 未签 → 区间（M38 给 2%–5%）无法先于 K-03 定值（`dsm/weights_calibrate.py:195/519/653`【清单实测@`aa4a9ba`】） | M38 L30／SDD 1755 | 无默认，必填 | 行方 + 设计方（与 K-03、指标精度联定） | 等级边界带定义悬空 |
| K-19 | min_dim_weight（weight_construction） | calibrate／combine 两侧均**必填无默认**（`dsm/weights_combine.py:136`【实测@22f8179】注 [L564]）；M38 建议 ≥0.05 | M38 L31／SDD 1756 | 无默认，必填 | 评价管理委员会 | H-2 维度最低话语权约束不可执行 |
| K-20 | max_shift_from_ahp（weight_construction，H-5） | combine 侧代码默认 **D('0.30')**（`dsm/weights_combine.py:140`【实测@22f8179】注 [L568]）；calibrate 侧必填（`dsm/weights_calibrate.py:199`【实测@22f8179】）；M38 建议 0.30 | M38 L32／SDD 1757；RK-14 | 代码拟定（SDD 明文 0.30 代用） | 评价管理委员会（含 RK-14 的 shift 比值披露口径） | G7 判据点名项；熵权实质主导风险未经治理确认 || K-21 | G14FIX 的 5 条待签认项（合并条目，**必须按 §3.1 子表 ①~⑤ 逐项勾选**） | 见子表 | KNOWN-GAPS C-8 行「并入 K-21」+ 主控 ORCH-42 第1条；来源 `dsm_stage/G14FIX/K-21-PROPOSAL.md`（⚠️ `dsm_stage/` 属 gitignored，归档风险 = K-39） | 混合（见子表） | 业务方（评价管理委员会）+ 设计方 + 行方风控 | G-14 判据三要素（阈值/分子/分母）全为工程默认或 derived，未签前 `MIX_QUALITY_DEGRADED` 的每次告警都可被质疑 |
| K-22 | `loo_dominant_flip_rate` 配置键（LOO 主导翻转率阈值） | **无默认，必填注入**：缺则 `MissingConfigError`，不给默认值（ORCH-40 第7条） | 契约原文**无出处**（`dsm/sensitivity.py` 与 `tests/test_golden_b.py` 各自营造——K-SIGNOFF K-22 行原文）→ **出处缺失，需设计方确认** | 代码拟定（键名自定，无契约依据） | 评价管理委员会 | LOO 主导判定阈值无契约出处，敏感性结论辩护力受损 |
| K-23 | G-14 两口径 population **巧合一致**（现 fixtures 下 NOT_ASSESSED 中 C 类=0） | 数据巧合，非契约保证（`A1CPREP §6-B.4` 的 S-008 即「C 类且 NOT_ASSESSED」反例） | K-SIGNOFF K-23 行；披露义务归 P3a | 纯演练假定 | 业务方 + 设计方 | 若被误当契约保证，换数据后两口径分离将颠覆 G-14 结论 |
| K-24 | LOO 影响力度量算式 `loo_impact[m]=max_s abs(composite_LOO-composite_base)`（q12 Decimal，不经 float） | 现算式为**推导所得**；实测 loo_impact_max = M_REV_MINOR 0.120000000000 与手算逐位相符（夹具面） | 原文 L748／L1409／L1450 只要求「影响力排名」产出物，未逐字给算式；全文「跨度/极差/span」出现 0 次（K-SIGNOFF K-24 行） | 推断实现（derived） | 业务方 + 设计方（确认为验收口径） | 度量未签 → LOO 排名数值的可比性与验收判据不成立 |
| K-25 | `SensitivityReport.loo_impact` 字段名（契约表补录） | 字段名取 L1409 verbatim；新字段带默认值 `()`（ORCH-41 第3条硬约束） | `docs/adr/ORCH-22.md` 裁决 25 字段表**没有该条**（K-SIGNOFF K-25 行）；对账表 `docs/adr/ORCH-22-review-S1-T04.md:136` | 代码拟定（名 verbatim，契约表登记缺失） | 主控（契约表补录）+ 设计方 | 契约面与代码面字段表不一致，后续包可能漏接 |
| K-26 | g07 docstring 陈旧数值（0.098 → 实测 0.012950000000） | 归 E3b 内务：只改 docstring、禁改 assert；g07 两条现绿（ORCH-41 第7条解除 HELD） | K-SIGNOFF K-26 行（实测值，非 PLACEHOLDER） | 无业务数值（工程内务） | **无需行方签认**（主控核验；列于本单为编号完整性） | 不修则留下「文档与夹具矛盾」陈旧口径 |
| K-27 | LOO 影响力精确并列的处置（tie-break） | 现行为「并列双方都列出、不提名唯一榜首」（LOO-1 有测试钉住） | 契约**未给 tie-break 规则**；ORCH-40 第7条明示「并列报 blocked，禁自造 tie-break」 | 推断实现（保守处置） | 业务方 | 榜首唯一性需求未裁，报告可读性口径未定 |
| K-28 | g09 对 ERRATUM-08 的守护力 vacuous（anchor-first 与 pool-only 中位数恰好相等，均 0.101500000000） | 本 RUN 不加 variant（ORCH-41 第6条：避免再解冻 A1c 重冻 fixtures）；交 P3a 披露 | K-SIGNOFF K-28 行；ORCH-37 第8条／ERRATUM-08 | 纯演练假定（巧合致零守护） | 业务方 + 主控 | 该 golden 守护对判据变更不敏感，回归防线有洞 |
| K-29 | LOO targets 含未签认指标 `M_REPEAT_USE_COUNT`（排名实为 15 条，g07 docstring 写 14 条） | 指标未签即进 LOO targets；本项原被 LOO-1 自报为 K-23，因撞号按 L-12 改记 K-29 | K-SIGNOFF K-29 行；ORCH-41 第7条 | 纯演练假定（未签认指标参与排名） | 业务方（指标体系归口） | 指标体系含未经业务确认的成员，排名解读有噪声 |
| K-30 | `SPEARMAN_ZERO_VARIANCE` 的 severity | 暂定 **WARN**、`blocks_run=False`（blocks_run 有逐字依据 [L1022]「不入分」；渲染披露位 `reports.py:591-601` 为清单实测@`aa4a9ba`） | ORCH-34 第2条：维持暂定、**不得升格为 BLOCK**；原文未给该码 severity（K-SIGNOFF K-30 行） | 代码拟定（severity derived） | 业务方 | severity 未签 → 该降级码的首屏/阻断行为可被质疑 |
| K-31 | `cel_contract_version` 占位 | 保持 **PLACEHOLDER**：契约 [L1897]「首版固定为占位版本」+ [L1795] G8 三者绑定「待 G0–G7 完成后发布」→ 无可取版本串，编值违 R-12；落点 `dsm/cli.py:281-286` audit_context（清单实测@`aa4a9ba`） | K-SIGNOFF K-31 行 | 契约要求占位（非我方待办数值） | 主控 + 行方（G8 发布口径） | G0~G7 未全过前无法发布设计冻结版本号（M39 G8） |
| K-32 | LOO 影响力 CSV 载体是否扩列（`metric_id`／`loo_impact`） | 本 RUN 不做（ORCH-42 第4条裁定）；MD 面已闭环（report.md ⑦ 段）；CSV 13 列被 `tests/test_reports.py:355` 钉死 = 契约面表头 | K-SIGNOFF K-32 行；`reports.SENSITIVITY_COLUMNS` | 处置签认（契约变更决策，非数值） | 业务方 + 设计方（契约面） | 扩列未裁 → LOO 产出物在 CSV 面对用户不可见（V-5 风险已规避） |
| K-33 | G-14 上期 PoolStats 载体缺位 | 本 RUN 不做（ORCH-42 第5条）：`_previous_pool_stats()` 返回 None，报告显式披露「本期不可比」（符合 V-14 不造假基线） | [L891] Inputs 无列、[L1051] AuditBundle 十六列无 `pool_stats`；D-MODELS-02（`reports.py:108` AllFrames，ADJ-4）——K-SIGNOFF K-33 行 | 处置签认（契约级缺口） | 业务方 + 设计方（契约面） | 上期对比无载体，G-14 只能报「不可比」 |
| K-34 | M29 九步 marshal 的 CLI 端到端验收口径 | 清单实测@`aa4a9ba`：`cli.py:_chain_gate` 模块齐全时仍 raise InvariantError（退出码 5）；**本包实测@22f8179：`dsm/cli.py:319 _chain_gate` 仍在、raise 仍在（:333 起）、`:918 except OSError` 仍在**；本 RUN 的 M29-1 包正在返工（在飞），本单成文时**不预判其结果** | [L1330]-[L1358]；KNOWN-GAPS G-14/H-9；`dsm/cli.py:319/918`【实测@22f8179】 | 处置签认（验收口径） | 主控 + 行方 UAT | marshal 未落地则 CLI 端到端不可用，K-01~K-20 签认后仍需此项闭合才能真实出数；**不得写成「CLI 已可用」** |
| K-35 | 编码门禁「末尾 LF」口径与历史数目 | ORCH-42 第6条权威口径：四要素全量硬失败 + 末尾 LF 只对本次变更文件断言；历史 17 个（@`da4d0a9`，K-SIGNOFF P3c-final 计数校正节）只披露不返工；其中 9 个非 `docs/**` 清零需主控单独授权（BK-3 已获 ORCH-49 授权，在飞） | ORCH-36 第11条（20→证伪）→ ORCH-44 第2条（权威 17/18 之辨）→ ORCH-42 第6条；KNOWN-GAPS §H-4 | 门禁口径（derived） | 主控（口径）+ P2-wire-B/BK-3（实现） | 口径不统一则门禁假红/漏红反复出现（本单 §6 验收判据 2 即依该口径） |
| K-36 | 权威 `reproducibility_hash` 唯一口径 | 只认 `tools/repro_offline.sh` 的 `RESULT=… HASH=…` 行；测试内自测值一律 non-canonical（ROB-1 的 `f437c0ea…` 不入台账）；台账四值末位现值 `e5923465…80904`（v1.2 实现面改动后**必变**，ORCH-49 第5条预声明） | K-SIGNOFF K-36 行（`repro_offline.sh:243/261/294/362` 探针链）；ORCH-44 定稿 | 台账口径（主控） | 主控（台账口径）+ 各实现包 | 口径不签 → 哈希台账再被测试内临时值污染（本 RUN 已发生一次误读） |
| K-37 | `NEED-GOLDEN-MAP` 之 G-10 hand 记录陈旧 | 判据已按 ORCH-35 转绿（单维 WARN／≥2 维 BLOCK + exit 2），但 `fixtures/golden/golden_map.json` 的 G-10 `hand` 手算留痕可能仍是旧判据 → 有被「反填回退」风险（R-14 反向弱化） | K-SIGNOFF K-37 行；ORCH-35 | 记录订正授权 | E3b 后续／主控（`fixtures/**` 属禁写面） | 不授权改写 → 下一个包可能照旧判据反填期望 |
| K-38 | `NEED-GOLDEN-MAP` 之 G-14 hand 缺三口径留痕 | 三口径 = 主体级 12／池级 universe 11／G-14 判据分母 9；比值留痕 3/9、5/9、5/11、7/11（A1d「把 11 标 superseded_by_G14FIX」建议**已被主控驳回**，KNOWN-GAPS §H-8） | K-SIGNOFF K-38 行；ORCH-44 第6条；ERRATUM-11 | 记录订正授权 | E3b 后续／P2-wire-B(2/2)／主控 | hand 不写全三对比例 → 后续包拿 11 或 12 当 G-14 分母 |
| K-39 | P3b 工装 B1~B9 修复状态 + `dsm_stage/` 归档风险 | B1／B7 已修复 @`da4d0a9`；L3-strong 签核**仅限该次签核 HEAD**，HEAD 前移须复跑；`dsm_stage/` gitignored 而多份裁决依据只存在于其中（含本单 K-21 所引 `K-21-PROPOSAL.md`） | K-SIGNOFF K-39 行；KNOWN-GAPS §H-15.1 | 处置签认（交付完整性） | 主控（归档决策）+ 行方（交付完整性） | 不决定归档 → 交付物引用不存在的证据文件；不标注适用域 → 「L3-strong」被误用到新 HEAD |
| K-40 | v1.1 台账 `ops/dag-state.json` 内 160 处「?」mojibake（work_packages 4 个载体节点） | 原文不可从该文件恢复（备份对比 BACKUP_QMARK=160=PATCHED_QMARK=160，本轮零新增）；处置 = 只披露不猜测回填（重写=伪造历史）；**本 RUN 不动**（ORCH-49 第6条裁定：保持开放，取证与回填另立维护动作） | `ops/dag-state.json` K-40 条目（`id:"K-40"`，blocking:false，owner「下一版 RUN 主控」）+ `ops/dag-state.json:732/:763`（BK-1）+ `ops/dag-state-v1.2.json:444`（ORCH-49 第6条）【实测@22f8179】 | 台账完整性处置（非行方治理值） | 主控（v1.2 收口后单独裁）；行方仅需知悉披露 | 不回填 → v1.1 审计面 4 个节点中文原文持续缺损；**禁止**凭上下文猜测重写 |

### §3.1 K-21 子表（5 个待签认子项，逐项独立勾选；来源 `dsm_stage/G14FIX/K-21-PROPOSAL.md`，ORCH-42 第1条要求逐条并入）

| 子项 | 是什么 | 现拟定值（非签认值） | 出处 | 属性 | 需谁签 | 不签的后果 |
|---|---|---|---|---|---|---|
| K-21① | G-14 `MIX_QUALITY_DEGRADED` 触发阈值绝对值 | `numeric.TOL = Decimal('1E-12')`（`dsm/numeric.py:19`【实测@22f8179】），判据 `now-before>TOL` 语义等价「任何上升都警示」；代码两处均标注「工程默认，非业务签认值」 | K-SIGNOFF K-21① 行；ADJ-G14 逐条核过 SDD L1734-L1757 全文缺位；ORCH-36 第3条 | 代码拟定（工程默认） | 业务方 + 行方风控 | G-14 每次触发都可被质疑「阈值是你们自己定的」 |
| K-21② | G-14 判据分子口径 | 现取 **C 类计数**（SDD L1416 verbatim；「C+D 占比」零原文依据）；G14FIX @`42d5346` 落地（`pooling.py:101/264-281/300`【清单实测@`aa4a9ba`】） | SDD L1416；K-SIGNOFF K-21② 行 | 契约 verbatim（改判需签认） | 业务方 + 设计方 | 若行方本意是 C+D，现实现与意图相反 |
| K-21③ | G-14 判据分母口径 | 现取 **9**（= pooling universe 11 − NOT_ASSESSED 2）；负向排除 verbatim = SDD L1004「NOT_ASSESSED 不计入分母」→ ERRATUM-05；12／11／9 由 ERRATUM-11 权威化 | SDD L1004；ERRATUM-05／-11；ORCH-36 第2条 | 推断实现（derived，负向排除为 verbatim） | 业务方 + 设计方 | 分母争议未了（A1d 的 superseded 建议已被驳回，KNOWN-GAPS §H-8） |
| K-21④ | `MIX_QUALITY_DEGRADED` 严重度 | **WARN、blocks_run=False**（与 L1005 同族两码对齐；未签前不得升格，ORCH-30） | K-SIGNOFF K-21④ 行 | 代码拟定（derived） | 业务方 + 行方风控 | 是否阻断运行无业务结论 |
| K-21⑤ | L1416 限定语「一级库中」与「C 类不得进一级库」（L1002／L137／L1436）字面互斥 | **不据字面实现**（否则 G-14 恒不触发）；已在代码注释与报告正文双处披露（ERRATUM-04） | SDD L1416 vs L1002/L137/L1436；ERRATUM-04；K-SIGNOFF K-21⑤ 行 | 契约 verbatim 冲突（待业务更正文案） | 业务方 + 设计方 | 文案不更正 → 判据字面与可执行性永久互斥 |
### §3.2 签认勾选栏（40 个编号 + K-21 五子项 = 45 个勾选位，全部空白，本包不代填）

格式统一为：`[ ] 已签认  值=______  签认人=______  日期=______`。「值」栏接受三类写法：确认现拟定值 / 新值 / 「维持」；未签认的保持空勾并可在行尾补 `[ ] 不签认  理由=______`。

- [ ] K-01 已签认  值=______  签认人=______  日期=______
- [ ] K-02 已签认  值=______  签认人=______  日期=______
- [ ] K-03 已签认  值=______  签认人=______  日期=______
- [ ] K-04 已签认  值=______  签认人=______  日期=______
- [ ] K-05 已签认  值=______  签认人=______  日期=______
- [ ] K-06 已签认  值=______  签认人=______  日期=______
- [ ] K-07 已签认  值=______  签认人=______  日期=______
- [ ] K-08 已签认  值=______  签认人=______  日期=______
- [ ] K-09 已签认  值=______  签认人=______  日期=______
- [ ] K-10 已签认  值=______  签认人=______  日期=______
- [ ] K-11 已签认  值=______  签认人=______  日期=______
- [ ] K-12 已签认  值=______  签认人=______  日期=______
- [ ] K-13 已签认  值=______  签认人=______  日期=______
- [ ] K-14 已签认  值=______  签认人=______  日期=______
- [ ] K-15 已签认  值=______  签认人=______  日期=______
- [ ] K-16 已签认  值=______  签认人=______  日期=______
- [ ] K-17 已签认  值=______  签认人=______  日期=______
- [ ] K-18 已签认  值=______  签认人=______  日期=______
- [ ] K-19 已签认  值=______  签认人=______  日期=______
- [ ] K-20 已签认  值=______  签认人=______  日期=______
- [ ] K-21 已签认（须 §3.1 子表 ①~⑤ 全部单独勾选后方可勾本行）  值=______  签认人=______  日期=______
    - [ ] K-21① 已签认  值=______  签认人=______  日期=______
    - [ ] K-21② 已签认  值=______  签认人=______  日期=______
    - [ ] K-21③ 已签认  值=______  签认人=______  日期=______
    - [ ] K-21④ 已签认  值=______  签认人=______  日期=______
    - [ ] K-21⑤ 已签认  值=______  签认人=______  日期=______
- [ ] K-22 已签认  值=______  签认人=______  日期=______
- [ ] K-23 已签认  值=______  签认人=______  日期=______
- [ ] K-24 已签认  值=______  签认人=______  日期=______
- [ ] K-25 已签认  值=______  签认人=______  日期=______
- [ ] K-26 已知悉（工程内务，无需行方数值签认，主控核验即可）  值=______  签认人=______  日期=______
- [ ] K-27 已签认  值=______  签认人=______  日期=______
- [ ] K-28 已签认  值=______  签认人=______  日期=______
- [ ] K-29 已签认  值=______  签认人=______  日期=______
- [ ] K-30 已签认  值=______  签认人=______  日期=______
- [ ] K-31 已知悉（契约要求首版保持 PLACEHOLDER，G8 前不可填值）  值=______  签认人=______  日期=______
- [ ] K-32 已签认  值=______  签认人=______  日期=______
- [ ] K-33 已签认  值=______  签认人=______  日期=______
- [ ] K-34 已签认  值=______  签认人=______  日期=______
- [ ] K-35 已签认  值=______  签认人=______  日期=______
- [ ] K-36 已签认  值=______  签认人=______  日期=______
- [ ] K-37 已签认  值=______  签认人=______  日期=______
- [ ] K-38 已签认  值=______  签认人=______  日期=______
- [ ] K-39 已签认  值=______  签认人=______  日期=______
- [ ] K-40 已知悉（台账完整性处置归主控，行方无代签动作；勾选仅代表知悉披露）  值=______  签认人=______  日期=______

---

## §4 F-1（G5）—— D6 三项争议来源逐字复核单

- **G5 通过判据（M39 L40／SDD L1792 逐字）**：「三项争议来源逐字复核并给出采用 / 排除结论；未复核项标『禁止引用』」；M39 原文状态列逐字：「**未完成** → 复核前全面禁用（§5.5.3）」。
- **当前实测状态（KNOWN-GAPS §F-2 行转录，观测 HEAD `da4d0a9`）**：未完成——`grep -rn D6 dsm/*.py` 无命中，v1.1 全 RUN 无复核产物；代码侧与之相容（未验证载体一律显式异常，如 `dsm/whatif.py` 对 PLACEHOLDER/None 抛 WhatifInputError/WhatifPlaceholderError，`dsm/whatif.py:268` 起【实测@22f8179 该函数 docstring 在位】）。
- **红线（本单重申，非新造规则）**：**复核完成前，任何争议来源结论禁止引用**——包括但不限于把「16 万次实验」「always-on 对照组」归给对应银行、或给秩反转综述补卷期页码。本单与 K-SIGNOFF／KNOWN-GAPS 两清单均未引用争议来源数值（KNOWN-GAPS §F 自述）。
- **三项争议来源（SDD §5.5.3 = digest M40 L1833-1837 逐字摘录）**：

| # | 争议表述（逐字） | 复核要求（逐字） | 已核可替代来源（逐字） | 复核勾选 |
|---|---|---|---|---|
| A-1 | 某国外银行「五年累计超 16 万次单独实验」 | 逐字打开原始页面复核；**复核前禁止引用** | 该行年报披露的模型与数据点规模；商学院案例的实验文化（定性） | [ ] 已复核  结论=采用/排除______  复核人=______  日期=______ |
| A-2 | 某国外银行「always-on（常设）对照组」 | 同上；复核前**不得**把「常驻对照组」归给该行 | 另一家数字银行的官方 universal holdouts 说明；咨询机构 2021 年关于「每个目标细分预留排除组」的规则 | [ ] 已复核  结论=采用/排除______  复核人=______  日期=______ |
| A-3 | 秩反转系统综述（2018）的具体卷期页码 | 存在两个可能出处，**未核清前只写「秩反转系统综述（2018，130 篇文献）」，不写卷期页码** | —— | [ ] 已复核  结论=采用/排除______  复核人=______  日期=______ |

- **沿用红线（SDD L1839 逐字）**：「任何未经核实的国内银行 uplift 人均金额、未经核实的『设置对照组』表述、未经核实的文献被引数、未经核实的客户侧金额拆分」——**两线一致，均不得引用**。
- **需谁签**：D6 复核方（逐字复核并出具采用/排除结论）→ 评价管理委员会背书 → G5 门禁判「通过」仅可由主控在复核产物落盘后登记，本包无权判定。
- **不签的后果**：G5 未过 → 按 README 首屏与 M39，本仓库不得输出可用于真实资源配置的分数或等级；三项争议来源在对外材料中永久禁用。
- **R-12 注意**：本包**未**打开任何原始页面、未核验任何第三方数字，表中三条仅转录契约原文；复核动作只能由行方/复核方执行。

---

## §5 F-2（G7）—— 治理配置签认状态与合成演练 config 的边界

### §5.1 G7 通过判据（M39 L42／SDD L1794 逐字）

「权重、门槛、红线阈值、评价周期、各指标目标值、α 及 K-15~K-20 全部脱离 PLACEHOLDER」；M39 原文状态列：「**未完成**（依赖行方，见 §5.9）」。⚠️ 逐字判据点名：K-15~K-20 与 α（即 K-15 的 alpha_floor 治理与 K-01/K-02 的 α 组合冻结）**必须全部脱离 PLACEHOLDER** 才算签认；「全部脱离」以 `config/` 载体实测为准，不以本单勾选数为准。

### §5.2 当前实测状态（观测 HEAD `22f8179`，本包亲测）

- `git ls-files config` = **0**：已提交的签认载体不存在。
- `dsm/config.py:449 load_all()` 对缺失文件／未填占位以 `EXIT_CONFIG=3`（`dsm/config.py:71`）拒绝【两处均实测@22f8179】→ **真实运行（`dsm score`）不可用，只能跑合成演练**（KNOWN-GAPS §F「设计如此，非缺陷」定性沿用）。
- `dsm/reports.py:80 OPEN_PARAMETER_IDS = K-01..K-20`、`:644` 在报告中把 20 项渲染为 PLACEHOLDER【实测@22f8179】。
- K-01~K-40 全部签认动作**均未发生**（本单 §3.2 勾选位全部空白即为现状凭证）。

### §5.3 ⚠️ M29-3 合成演练 config ≠ G7 已签（本 RUN 最重要的误读防线）

- 本 RUN 的 **M29-3 包正在 `config/` 造一套「完整但显式标注合成待签认」的演练 config**（写集 `config/**` + `tests/test_config_dryrun.py`，RUN §2 表；本包实测@22f8179 工作树已见未提交文件 `eval_config.yaml／weights_WV-SYNTH-2026.yaml／redlines.yaml／grade_rules.yaml／anchor_set.yaml／ahp_matrices.yaml`，`git ls-files` 计数仍为 0）。
- **RUN §1 逐字红线**：「M29-3 的演练 config 只是『合成待签认』样例，**绝不等于 G7 已签**」；其现值如 `whatif_run_id=WIF-SYNTH-2026-01`，逐键标注「合成值待业务签认」，**严禁冒充签认真值、严禁填 K-01~K-20**（RUN §3 M29-3 节）。
- 因此：**不得据演练 config 的存在宣称 G7 已通过、不得宣称本仓库可用于真实资源配置**；文档与 README 首屏的「G5／G7 未过 → 不得输出可用于真实资源配置的分数或等级」声明**一字不得改**（RUN §1，且有测试守护）。

### §5.4 G7 判「通过」的建议完成判据（供收口包／主控引用；本包不判定）

1. §3.2 的 40 个编号（含 K-21①~⑤）逐条完成勾选且有权角色签认；
2. 签认值全部写入 `config/` 并**提交入库**（载体 = `dsm/config.py:76-80` 六类文件【实测@22f8179】），无任何 PLACEHOLDER 词表命中（`:84-85`）；
3. 主控在最终 HEAD 亲测 `load_all()` 成功、`dsm score` 在签认配置下端到端产出报告且 `OPEN_PARAMETER_IDS` 段不再渲染 PLACEHOLDER；
4. M39 逐字判据逐项对照：权重（K-01/K-02）／门槛（K-03）／红线阈值（K-04）／评价周期（K-09）／各指标目标值（K-14）／α 与 K-15~K-20 全部脱离 PLACEHOLDER。
5. 以上四条同时满足前，**G7 一律登记为未过**；本包未做任何「已通过」宣称。

---

## §6 在册覆盖度自证与计数口径披露

- **九条阻塞缺口全部在册**：C-1（§2 行1）、C-2（§2 行2）、C-3（§2 行3）、C-4（§2 行4）、C-5（§2 行5）、C-6（§2 行6）、C-8（§2 行7，关联 K-21①~⑤）、F-1（§4）、F-2（§5 + §3 全表）——与 `ops/dag-state-v1.2.json` 的 `blocking_gaps_inherited.external_only`（实测 9 条：C-1~C-6、C-8、F-1、F-2）逐条对应。
- **40 个编号全部在册**：K-01~K-40 在主表各有一行、在 §3.2 各有一个勾选位（K-26／K-31／K-40 为「知悉/核验」型动作，已在勾选行内注明，不属于行方数值签认）。
- **计数口径差异如实披露（未由本包调和）**：`K-SIGNOFF-CHECKLIST.md`（P3c-final）自述「39 个编号／43 个签认动作」（K-01~K-35 含 K-21 五子项=39，+K-36~K-39=43，**未含 K-40**）；`ops/dag-state.json:763`（BK-1 澄清节）写「K 签认动作 40 个（K-01~K-35 含 K-21 五子项=39，加 K-40）」（**未含 K-36~K-39**）。两口径互有遗漏，**并集 = 40 个编号 + K-21 拆出的 4 个额外子项 = 44 个动作位（本单 §3.2 共 45 个勾选位，含 K-21 母项）**。差异属台账问题，归主控在 V12-DOC-FINAL 统一口径，本包只登记不裁决。
- **无出处条目**：主表中唯一「出处缺失」是 **K-22**（契约原文无出处，需设计方确认，已如实标注）；C-1~C-6／C-8 的**新立 K 编号**在既有文档中不存在，本单按 L-12 不自行编号，登记为「需主控补分配」。

---

## §7 观测基线与复测命令（任何人可复核）

本包观测 HEAD = `22f8179`（开工时 `git rev-parse HEAD` 实测）。核心断言的复跑命令（在仓库根目录）：

```
git rev-parse HEAD                     # 期望 >= 22f8179；行号断言仅在该 HEAD 成立
git ls-files config | wc -l            # 期望 0（已提交载体不存在；工作树可能含 M29-3 未提交演练文件）
grep -n "EXIT_CONFIG = 3" dsm/config.py                       # :71
grep -n "def load_all" dsm/config.py                          # :449
grep -n "OPEN_PARAMETER_IDS" dsm/reports.py                   # :80/:644
grep -n "TOL = Decimal" dsm/numeric.py                        # :19
grep -n "IMPUTE_SCOPE_ALL" dsm/attainment.py                  # :170/:315/:640
grep -n "CFG_KEYS" dsm/triangulation.py                       # :55（CFG_GRA_NORM 取值 initial/mean 见 :56-57）
grep -n "D('0.5')\|D('0.30')\|min_dim_weight" dsm/weights_combine.py   # :135/:136/:140
grep -n "stable_max\|review_max" dsm/sensitivity.py | grep default     # :510-511
grep -n "DEFAULT_UPGRADE_CONSECUTIVE_PERIODS" dsm/grading.py  # :60
grep -n "_chain_gate\|except OSError" dsm/cli.py              # :319/:918（M29-1 在飞，交付后需重取行号）
grep -n "RI" dsm/weights_ahp.py | head                        # :62 CR_THRESHOLD、:73-74 Saaty RI 表 n=1..10
```

注：转录自 `K-SIGNOFF-CHECKLIST.md` 的行号以 `aa4a9ba` 为观测基线，其中 `attainment.py:149/546`、`evidence.py:68`、`sensitivity.py:423-424` 三处在 `22f8179` 已实测漂移（本单已改用新行号并双侧标注）。`cli.py:918` 与 `cli.py:319` 未漂移。

---

## 附：本单的红线自查（对照派工单【红线】节）

1. 未替行方填任何签认值：§3.2 与 §4 的全部「值／结论」栏空白。
2. 未把推断值写成已签认：属性列逐行标注 公开标准值／代码拟定／推断实现／纯演练假定；ADJ-6（Saaty RI = 公开标准值，采纳但待行方确认）、ADJ-7（SHORTFALL_CLAMPED = 推断实现，V 表不得记已验证）已按裁决原文转录于 §2 C-8 行与主表对应行（RI 专列编号缺失已在 C-8 行如实登记）。
3. 未引用任何第三方估价／性能数字；§4 三条争议来源仅转录契约原文，未做真伪判断。
4. 未宣称任何 V 项或 G5／G7 已通过；§5.4 仅为建议判据，判定权在行方签认 + 主控亲测。
5. 本包写集 = 仅本文件；`ops/dag-state*.json`、`config/**`、`dsm/**`、`tests/**`、既有交付文档一律未触碰。
