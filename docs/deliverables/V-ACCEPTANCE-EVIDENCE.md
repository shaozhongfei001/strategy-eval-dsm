# V-1 ~ V-20 全量验收证据表（定稿前移版 · P3a-pre2）

- **性质**：本文件是 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` 的**定稿前移版**。初版由 P3a-prep 建於 `358b4ea`（✅12 / ❌3 / ⏳5，后经 `0d4d4aa` 诚实性补记与 `358b4ea` §五 覆盖汇总）。本包（P3a-pre2 · ORCH-41 第9条）在其后 **9 个新提交 / 7 轮裁决（ORCH-35 ~ ORCH-41）/ 9→11 条 ERRATUM / 23→27 条缺陷 / K 号扩至 K-29** 的基础上**逐条重判**，把文档推进到**只差最终数字刷新**的状态。
- **唯一待刷新项**：全量 pytest 的 `failed / passed / collected` 与最终 `reproducibility_hash` 一律写 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`。理由（R-12）：本包施工期间 A1d / E2b / E3b / P2-wire-A **四包并发在飞**，`git status --porcelain` 实测 8 个被改文件（`dsm/cli.py`、`dsm/io_loaders.py`、`dsm/reason_codes.py`、`dsm/reports.py`、`ops/dag-state.json`、`tests/test_golden_a.py`、`tests/test_golden_b.py`、`tests/test_integration_spine.py`），**任何此刻测到的数都不是终值**。
- **本包亲自实测（只读，未跑任何写盘命令、未跑 pytest、未跑 `fixtures gen`）**：
  1. 契约核验：`sha256sum 工行参考文件/开发设计文档-策略评价可辩护评分模型DSM-v1.1.md` = `708679e9a83d71784146fc71bcc72998d3c420e152c391415f02bbf6d69fe57f`（[:12] = **`708679e9a83d`** ✅ 与 `dag-state.sdd_fingerprint` 一致），`wc -l` = **2003** ✅。
  2. 邻仓只读核验：`/home/szf/dev/CampaignLab` = `m0-framework` / `0cccb76` / porcelain **0** / `rev-list --count HEAD` **154** ✅ 四项全一致，**未触碰**。
  3. 本仓：branch `main`，HEAD = **`858ebc8`**（LOO-1），`git log -25` 轨迹逐条读取。
  4. `ops/dag-state.json` 全量字段读取（decisions ORCH-31~41 / defects 27 / errata 11 / contract_gaps_pending 49 条含 K-21~K-29 / orch_lessons 12 / pytest_baseline / frozen_fixtures / reproducibility_evidence）。
  5. `grep` 取证（本包亲自执行，非转录）：`tests/test_golden_a.py:416 test_g02_c_class_high_score_is_gated_to_l2_and_ranked_only_in_c_pool`、`tests/test_properties_all.py:552 test_p06_downgrading_evidence_to_C_never_relaxes_the_L1_library_gate`、`tests/test_pooling.py:142 test_pool_key_is_domain_times_evidence_class`、`:184 test_g02_c_class_barred_from_primary_library`、`:201 test_g02_clean_a_b_l1_rows_are_admitted`、`:381 test_mix_quality_degraded_needs_a_signed_baseline`、`:601 test_models1_step7_pool_key_refuses_a_missing_evidence_class`、`tests/test_attainment.py:378/637/749 isinstance(..., Decimal)`、`:752 as_tuple().exponent == -12`。
- **转录纪律（R-12 / L-08 / L-09）**：凡标注「转录」的数字，均给出**确切出处**（commit / 文件:行号 / ORCH 号 / 包 NOTES），本包不为其准确性背书、亦不改写；行号一律以各包 NOTES 的实测对照表为权威（L-09：`cc18a38` 提交信息内的行号是提交前估值，权威对照表在 `dsm_stage/MODELS-1/NOTES-MODELS-1.md §七`）。
- **结论口径**：✅ = 判据已有实测证据且未被后续变更推翻；❌ = 实测不通过或**端到端未闭环**（并写明缺什么、归谁）；⏳ = 机制已落地，但判据要求的终值 / 载体接线 / 第二人复跑尚缺，待 P2-wire-B 或 P3b 刷新。

---

- **⚠️ 施工期 HEAD 漂移（必须与 §K 追记同读）**：本包开工实测 HEAD = `858ebc8`（LOO-1）；**定稿落盘前 HEAD 已推进到 `0d8afeb`**，其间落地 4 个提交（`53ed80c` P2-wire-A、`f4aaa6b` ORCH-40+ORCH-41 台账、`f27334d` A1d、`0d8afeb` E3b）。**§A / §B 中所有「在飞 / 施工中」表述以 §K 追记为准；§K 明示哪几条判定的前提已变。** 唯一仍在飞的包 = **E2b**（`git status --porcelain` 实测：`fixtures/golden/golden_map.json`、`tests/test_golden_a.py`、`tools/gen_golden.py`）。

---

## §A 验收项逐条判定表（V-1 ~ V-20，全部重判）

| V-x | 判据（M36 = SDD L1490-L1513） | 判定依据（实测命令 / 观测值 / 出处） | 结论 |
|---|---|---|---|
| V-1 | 「G-01 至 G-15 全部通过」(L1494) | 权威基线 `pytest_baseline.after_MODELS1` = **11 failed / 2190 passed / 2201 collected / 0 error / 0 skip / 0 xfail @ `cc18a38`**（ORCH-38 第1条、ORCH-39 第4条采信；11 红逐条拆分官方标 `PLACEHOLDER` 待 P2-wire-B）。其中 golden 侧红 = `golden_a g04/g08` + `golden_b g05/g06/g07/g10/g14`。**修因已落地**：D-A1-02/03/04 CLOSED @ `6299245`（A1c，ORCH-40 第5条）、D-A1-08 CLOSED @ `dce1ac5`（ATT-1，ORCH-40 第3条）、D-SPEC-G10 CLOSED-BY-ORCH-35、D-D2-01/D-SEN-01 CLOSED @ `858ebc8`（LOO-1，ORCH-41 第2条）、G-14 口径 @ `42d5346`（G14FIX，ORCH-40 第6条）。**但 expects 侧更新仍在飞**：E2b（`tools/gen_golden.py` + `golden_map.json` + `test_golden_a.py`）、E3b（`test_golden_b.py`）、A1d（`test_integration_spine.py` + `dsm/io_loaders.py`）→ 终值 `PLACEHOLDER-TO-REFRESH(P2-wire-B)` | ❌（当前不通过；归因已全部落地，终判待 P2-wire-B） |
| V-2 | 「P-1 至 P-15 全部通过（**hypothesis 各 500 例**）」(L1495) | 转录初版 @ `358b4ea` 实测：`pytest tests/test_properties_all.py` = `16 passed`，但 `tests/test_properties_all.py:73` 为 `MAXEX = settings(max_examples=25, deadline=None)`（R-11 开发期档）→ **500 例从未跑过**。本包未复跑。500 例属 Phase 3 门禁，须由 P2-wire-B 在全量收口时执行 | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-B / 500 例档未跑)` |
| V-3 | 「**第二人复跑** reproducibility_hash 精确相等」(L1496) | 机制侧转录：`tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs` 在 `42d5346` 两跑相等（`reproducibility_evidence.invalidation_log[seq4].two_runs_equal = true`）。**第二人「全新 clone + 真断网 + 同 seed」复跑属 P3b，尚未执行**。当前哈希 `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` @ `42d5346`（见 §H），**终值待定** | ⏳ `PLACEHOLDER-TO-REFRESH(P3b)` |
| V-4 | 「任一分数判定路径可在 **3 层内**回溯到原始指标值」(L1497) | 转录初版 @ `358b4ea` 实测（只读探针 `dsm_stage/P3a-prep/v4b_probe.py` 真跑 `_run_chain`）：抽查 S-001/v1/2026-Q2/`M_AUM_MINOR`，L1 `score_card.per_metric` → L2 `AttainmentRow` → L3 `fixtures/input/metric_fact.jsonl` + `metric_dict.jsonl`，**3 层闭合**。**但 A1c @ `6299245` 已受控解冻并重冻 fixtures**（`metric_fact` 仍 896 行、`design_card` 补 `alt_method_note`、2026-Q3 缺格载体由 `M_COMPLAINT_RATE` 迁至 `M_SATISFY_SCORE`），初版抽查的具体数值载体已变 → 须在终值 HEAD 上重抽 | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-B / A1c 重冻后重抽 3 层链)` |
| V-5 | 「配置含 PLACEHOLDER 时启动失败且**一次列出全部**未填字段」(L1498) | 转录初版 @ `358b4ea`：`tests/test_config_placeholder.py` = `201 passed`；「一次列出全部」专项 5 条（`test_t05_b01_all_paths_are_listed_at_once`、`b07_the_message_lists_every_path_on_its_own_dash_line`、`d10_every_none_in_a_tree_is_reported`、`g03_all_five_missing_files_are_reported_at_once`、`g08_an_empty_config_dir_reports_everything_missing`）= `5 passed`；`test_p10_placeholder_in_any_config_file_blocks_load` = `1 passed`。`config/**` 与 `tests/test_config_*` 不在 A1d/E2b/E3b/P2-wire-A 任一写集内（ORCH-40 第8条 R1 已把 `fixtures/**` 与 `dsm/fixtures_gen.py` 移出 A1d 写集；ORCH-41 第1条驳回改 `dsm/models.py:373`）→ 该结论未被后续变更触及。前提披露见 §J（`config/` 实测 0 文件，真实运行被 `EXIT_CONFIG=3` 拒绝，**设计如此**） | ✅（转录 + 写集不相交论证） |
| V-6 | 「红线违反时等级**恒为 forced_grade**，与其余指标无关」(L1499) = G-03 + P-2 | **四条不可砍底线之一**。见 §B-3 完整证据链。转录初版：`test_g03_hard_redline_forces_l4_and_composite_stays_but_does_not_count` `1 passed`、`test_p02_hard_redline_grade_equals_forced_no_matter_how_good` `1 passed`、`tests/test_redline.py -k g03` `5 passed`（含 `test_g03_hard_row_has_no_weight_or_deduction_hook`、`test_g03_redline_bypass_keeps_the_score_identical`、`test_g03_soft_crossing_deducts_alone_and_never_forces`）。A1c 提交说明逐字：「**G-03/G-15 零影响**」（`6299245`），且 D-A1-03 的缺格载体由 HARD 红线指标 `M_COMPLAINT_RATE` 迁至 `M_SATISFY_SCORE` 后「`g09` 实测仍绿」 | ✅（底线成立；终值全量数字 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`） |
| V-7 | 「新增策略不改变存量策略等级」(L1500) = G-05 + P-4 | 初版 §五 曾由 ⏳ **改判 ❌**（G-05 实测：新增极值策略使存量 S-011 `composite 0.967705891652 → 0.968545891652`）。**根因已裁并修**：ORCH-37 第8条把 `IMPUTE_MEDIAN` 的中位数参考集裁为 `anchor_set` 优先（失效回退当期池 + `ANCHOR_SET_STALE`），ATT-1 落地 @ `dce1ac5`，D-A1-08 CLOSED，记 ERRATUM-08（SDD L1134 对参考集**零字规定**）。**仍未闭环**：ORCH-40 第3条实测「`g05` 仍红，根因 = `tests/test_golden_b.py:343 _chain` 未传 `anchor_set`」（ATT-1 用只读插件注入后 g05 转绿、期望值一字未改）→ 归 **E3b**；其余接线点 `golden_a:287/780` → E2b、`spine:166` → A1d、cli Step1 → P2-wire。**另有守护力缺口 K-28**：现 fixtures 下 anchor-first 与 pool-only 的中位数恰好相等（均 `0.101500000000`）→ `g09` 对 ORCH-37 第8条 / ERRATUM-08 **零守护力（vacuous）**，ORCH-41 第6条裁本 RUN 不加 variant | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-B / E3b+E2b+A1d 的 anchor_set 接线)` |
| V-8 | 「报告含分池占比 + 合并占比 + 证据结构披露 + flip_rate + UNSTABLE 清单 + recommended/decided 分列」(L1501) | 转录初版：`tests/test_reports.py` = `17 passed` + 专项 4 条 `4 passed`（`test_report_has_ten_sections_in_fixed_order`、`test_recommended_and_decided_are_two_independent_columns`、`test_grade_distribution_and_evidence_structure_are_double_reported`、`test_sensitivity_veto_has_report_columns`）。**但 `dsm/reports.py` 正在 P2-wire-A 写集内**（ORCH-40 第6条：GAP-06 已接进 `reports.py:419` 的 `_section_6`；ORCH-41 第4条：`reports.py:451` 只渲染 `loo_dominant_metrics`，`loo_impact` 排名**在报告面无任何出口**，第⑧条已由条件项升为**必做项**）→ 现有 ✅ 不可沿用 | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-A 落地后由 P2-wire-B 复测)` |
| V-9 | 「金额全程整数运算，与 **Decimal 参考实现精确相等**；比率 **1e-12** 容差」(L1502) = G-11 + P-7 | **四条不可砍底线之一**。见 §B-1 完整证据链（含本包亲自 grep 到的 `tests/test_attainment.py:749/752` 与 LOO-1 的 q12/非-float/两跑逐字节相等断言）。`numeric.TOL = 1E-12` | ✅（底线成立；终值全量数字 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`） |
| V-10 | 「不依赖数据库、网络、调度器；**断网单机可完整跑通**」(L1503) | 转录初版：`test_inv2_no_inlined_algorithms_v10_offline` `1 passed`（AST 扫 `dsm/cli.py`，import 根与 `FORBIDDEN_IMPORTS` 交集为空；全程序只 1 处时钟读点 `_now()`）、`tests/test_architecture.py -k "h8 or inv1 or inv2 or inv3"` `6 passed`。**真断网 + 全新 clone 完整跑通属 P3b**：harness 已就绪 = `tools/repro_offline.sh` + `docs/deliverables/P3b-REPRO-HARNESS.md` @ `d228edd`，隔离级 **L3-strong**（全新本地 clone `--no-hardlinks` + `unshare -rn` netns 真断网 + 独立 venv 无 system site-packages + 26 个本地 wheel `--no-index`），已 6 轮实跑（4× L3-strong PASS 18/16/17/22s、1× 弱隔离降级 PASS、1× `--strict-isolation` 按设计 FAIL），幂等自清理残留 0/0。**但尚未在最终 HEAD 上跑** | ⏳ `PLACEHOLDER-TO-REFRESH(P3b)` |
| V-11 | 「AHP 工具在 **CR ≥ 0.1 时拒绝**产出权重；产出 status 只能是 DRAFT」(L1504) | 转录初版：`pytest tests/test_methods_ahp.py -k "t_ahp_05 or t_ahp_06"` = `6 passed, 11 deselected`（`test_t_ahp_05_cr_at_or_above_threshold_rejects_the_draft`、`_cr_below_threshold_is_accepted`、`_worst_five_pairs_are_ordered_by_deviation`、`_random_index_table_and_two_by_two_boundary`、`test_t_ahp_06_elicit_only_ever_produces_draft`、`_writing_frozen_raises`）。RI 表来源 ADJ-6（Saaty 标准表，n>10 抛错不外推）。`dsm/weights_ahp.py` 不在任一在飞写集内 | ✅（转录） |
| V-12 | 「篡改熵权诊断输出**不改变任何分数与等级**」(L1505) = T-ENT-03 | 转录初版：`test_t_ent_03_no_output_carries_an_aggregate_consumable_weight`、`test_weight_vector_carries_no_aggregate_consumable_field`、`test_inv3_score_runtime_never_reaches_an_entropy_recompute_module` 各 `1 passed`；`tests/test_entropy.py tests/test_diagnostics.py` 全绿。LOO-1 回归实测（ORCH-41 第2条）：`test_models_output + test_architecture` 合计 **642 passed（635→642，零红）** → 未被推翻 | ✅（转录 + LOO-1 回归印证） |
| V-13 | 「**关闭 triangulation 不改变**任何分数与等级」(L1506) = T-TOP-03 | 转录初版：`pytest tests/test_triangulation.py -k "t_top_03 or tri_01_scores_and_grades_identical or disabled_switch"` = `3 passed, 15 deselected`（`test_t_top_03_output_is_bypass_only_and_carries_no_score_or_grade`、`test_t_tri_01_scores_and_grades_identical_with_triangulation_on_and_off`、`test_t_tri_01_disabled_switch_emits_no_output_object`）；辅证 `test_t_tri_01_veto_is_boolean_only_and_not_compensable` 同批全绿 | ✅（转录） |
| V-14 | 「所有降级路径都有 reason_code **且出现在报告中**（**无静默降级**）」(L1507)，检验方式「**遍历 §3.14 矩阵逐条断言**」 | **四条不可砍底线之一，当前 ❌ 未端到端闭环**。见 §B-2 完整证据链与逐条缺口。初版实测的两项硬缺口至今**未闭合**：①M28 降级矩阵实测 **26 行**（L1280-L1305），`grep -rn 'M28' tests/*.py` 仅 **3 处**命中且全在 `test_preflight.py` 的 docstring/注释（L6/L506/L596），**零断言** → 26 行逐条遍历守护仍不存在；②`excluded`（EVID-1）与 `loo_impact`（LOO-1）的**报告面出口在 P2-wire-A 施工中**（ORCH-40 第2条「V-14 端到端未闭环（`excluded` 只到 API 层）→ 接线归 P2-wire-A ③」；ORCH-41 第4条第⑧条升为必做）。**在 P2-wire-A 落地前，本文件不得声称 V-14 端到端已闭环** | ❌（未闭环；缺 26 行遍历断言 + `excluded`/`loo_impact` 报告出口，归 P2-wire-A / P2-wire-B） |
| V-15 | 「任一 **FROZEN** 权重版本都能**出示完整证据链**：AHP 比较矩阵 → CR → 标定窗口熵权 → α 及标定报告 → 组合权重对照表 → whatif run_id」(L1508) | 负向守护转录初版已 ✅（`test_p11_frozen_weight_version_without_full_provenance_fails_the_load` `1 passed`、`test_p11_alpha_basis_closes_the_provenance_chain` `1 passed`、`tests/test_models_provenance.py` `239 passed`；`WeightProvenance.model_fields` = `['ahp','alpha_basis','approved_by','approved_date','combine','effective_from','effective_to','entropy','kind','whatif_run_id']`）。**正向实例已补**：A1c @ `6299245`（ORCH-40 第5条）补 provenance **七键**（`kind=AHP_ONLY` + `ahp` 段 + `whatif_run_id=WIF-SYNTH-2026-01` + 签认四件套），D-A1-04 CLOSED，C-01 恒 BLOCK 解除、spine step2 由红转绿走到 M29 L1322 右支。**诚实性红线**：这七键**全部是合成值、待业务签认**，不得冒充签认真值、不得填 K-01~K-20（ORCH-37 第5条：沿用 SYNTH 合成命名约定并标注待签认） | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-B / 正向链条须在终值 HEAD 上重抽查并逐键标「合成待签认」)` |
| V-16 | 「篡改**在线**熵权诊断输出，不改变任何分数与等级（**离线组合权重已冻结**）」(L1509) = T-CMB-06 | 转录初版：`test_t_cmb_06_entropy_provenance_is_a_frozen_snapshot` `1 passed`（`WeightProvenance.entropy` 是快照值、非可调用对象）、`tests/test_aggregate.py` `18 passed`、架构批 `6 passed`（含 `test_orch03_entropy_is_l1_and_the_only_implementation`、`test_orch03_l5_never_imports_l0a_or_l0b_and_diagnostics_uses_l1_entropy`、`test_inv3_score_runtime_never_reaches_an_entropy_recompute_module`） | ✅（转录） |
| V-17 | 「α 取**任意合法值**，红线否决与证据门禁结果不变」(L1510) = P-12 | 转录初版：`test_p12_alpha_changes_no_redline_or_evidence_gate`、`test_p12_alpha_moves_only_the_weights_and_never_a_gate_input` 各 `1 passed`。**例数限制同 V-2**（`max_examples=25`，500 例未跑） | ✅（机制成立；例数口径见 V-2 的 ⏳） |
| V-18 | 「whatif 运行**不污染生产输出**；候选权重与冻结权重相同时结果与 score **完全一致**」(L1511) = T-WIF-02 / T-WIF-03 | 转录初版：`pytest tests/test_methods_whatif.py -k "wif02 or wif03"` = `6 passed, 14 deselected`（`test_wif02_input_directory_hash_unchanged_before_and_after_run`、`_directory_digest_detects_a_single_byte_change`、`_run_writes_nothing_at_all`、`test_wif03_equal_weights_reproduce_score_exactly`、`_baseline_arm_reproduces_production_step5_and_step6`、`_tampered_production_score_is_refused`）；A4 归因精确性初版自行复跑 PASS，手算常量见 `tests/test_methods_whatif.py:222-262`（段1 `0.018` / 段2 `-0.180` / 交叉 `-0.006` / dim_total `-0.168`；对账 `cross_term_sum = 0.012` 独立成列可核）。**遗留披露**：D-A4-02（whatif GEOMETRIC 近似归因分支）ORCH-36 第10条裁 **WONTFIX-THIS-RUN**，M10 L674/L473 的要求尚未实现，现状抛 `WhatifOperatorError` 是**显式拒绝**、符合 V-14 | ✅（转录；D-A4-02 属新增功能缺口，见 §E） |
| V-19 | 「α* 由标定产出且**未通过放宽治理预算**得到；α* < alpha_floor 时按 floor 处理或直接报错，**无静默降级**」(L1512) = T-CMB-04 / T-CAL-04 | 转录初版：`test_t_cmb_04_alpha_floor_is_never_widened` `1 passed`；`-k "v19 or t_cal_04"` `4 passed, 20 deselected`（`test_v19_a_candidate_below_the_floor_is_clamped_up_to_the_floor`、`test_v19_an_infeasible_floor_raises_instead_of_degrading`、`test_t_cal_04_p13_the_config_object_is_never_modified`、`test_t_cal_04_p13_a_tighter_budget_moves_alpha_star_and_not_the_budget`，= RK-12 / M39 L1776 机器守护）；A3 字典序非加权 `2 passed`（`test_lexicographic_not_a_weighted_objective`：α=0.50 `boundary_ratio=1` > 预算 0.70 → `violations=(BOUNDARY,)`、`excluded_alphas[0.5]=ALPHA_INFEASIBLE`、`alpha_star=0.75`，report 每行 dump 后无任何含 `score`/`lambda`/`objective`/`cost` 的键；`test_whole_grid_is_traversed_and_never_short_circuited`） | ✅（转录） |
| V-20 | 「cel.enabled = false 时，输出与关闭 CEL-0 预留字段的基线**逐字段一致**（**G-01~G-15 全过**）」(L1513) | 转录初版：`tests/test_evidence.py -k cel` `2 passed, 16 deselected`（RK-15 / M39 L1779：cel 关闭且预留字段非空 → 必抛 `CelDisabledDataPresentError`）、`tests/test_models_output.py -k "cel or cel0"` `33 passed, 569 deselected`、`test_cel0_columns_are_never_silently_blank` `1 passed`（M28 L1304）。**但括注「G-01~G-15 全过」当前不成立**（同 V-1）→ 判据整体不可判 ✅。注：`dsm/evidence.py` 已由 CODES-2 @ `32cafd0` 变更（新增 `EV_OUT_OF_EVAL_PERIOD`，总数钉子 90→91），ORCH-41 第1条明令**禁改** `dsm/evidence.py`（A1d 必须改则报 blocked） | ⏳ `PLACEHOLDER-TO-REFRESH(P2-wire-B / 括注依赖 V-1)` |

**§A 汇总（本包重判）**：✅ **10** 条（V-5、V-6、V-9、V-11、V-12、V-13、V-16、V-17、V-18、V-19）；❌ **2** 条（V-1、V-14）；⏳ **8** 条（V-2、V-3、V-4、V-7、V-8、V-10、V-15、V-20）。合计 **20** 条。
**与初版（✅12/❌3/⏳5）的差异逐条说明**：V-4 ✅→⏳（A1c 重冻 fixtures 使抽查载体失效）、V-8 ✅→⏳（`reports.py` 进 P2-wire-A 写集）、V-15 ⏳ 保持（正向实例已由 A1c 补出但为合成待签认，须终值重抽）、V-7 ❌→⏳（ATT-1 已修根因，仅剩 E3b/E2b/A1d 的 `anchor_set` 接线）、V-14 ❌ 保持（缺口收窄但**未闭环**）、V-1 ❌ 保持（11 红权威基线 + expects 在飞）。**V-9 / V-6 两条底线保持 ✅**。
**四条不可砍底线现状**：V-9 数值口径 **✅** ／ V-14 无静默降级 **❌（端到端未闭环）** ／ V-6 + G-03 + P-2 红线非补偿 **✅** ／ G-02 + P-6 证据门禁 + 分池禁混排 **✅（机制层，见 §B-4）**。
---

## §B 四条不可砍底线的证据链（签核核心）

### B-1 · V-9 数值口径：金额与计数 int 精确、比率 Decimal 容差 1e-12、**全程不经 float**

| 证据面 | 具体证据 | 出处 |
|---|---|---|
| 原语层 | `numeric.TOL = 1E-12`；`numeric.eq_exact` 拒绝两侧 float；金额比较精确不用容差；`q12` 恒落 12 位且幂等 | 转录初版 @ `358b4ea`：`pytest tests/test_numeric.py tests/test_numeric_properties.py` = **`68 passed`**，含 `test_eq_exact_refuses_floats_on_both_sides`、`test_money_compares_exactly_never_with_tolerance`、`test_q12_always_lands_on_exactly_twelve_places_and_is_idempotent` |
| 金额 int 管线 | `test_p07_money_minor_int_pipeline_equals_decimal_reference_exactly` **`1 passed`**（int 管线 == Decimal 参考实现，精确相等） | 转录初版 @ `358b4ea`，SDD L1502 / G-11 + P-7 |
| 报告面无 float | `tests/test_methods_calibrate.py::test_v9_no_report_value_is_a_float` **`1 passed`** | 转录初版 @ `358b4ea` |
| G-11 门禁 | `pytest tests/test_preflight.py -k g11` = **`2 passed`**（`test_g11a_weight_version_stale_blocks`、`test_g11b_money_non_integer_blocks`） | 转录初版 @ `358b4ea` |
| **达成率 q12 且非 float（本包亲自 grep 取证）** | `tests/test_attainment.py:378` `assert isinstance(made.attainment, Decimal)`；`:637` `assert isinstance(hole.attainment, Decimal)`；`:749` `assert isinstance(made.attainment, Decimal)`；**`:752` `assert made.attainment.as_tuple().exponent == -12, 'q12 口径：12 位小数'`** | 本包实测 `grep -rn` @ HEAD `858ebc8`（只读） |
| **ATT-1 偶数样本中位数口径** | ATT-1 落地 `compute(..., anchor_set=None)` keyword-only，`IMPUTE_MEDIAN` 统计量参考集 **anchor 优先、池回退**并落 `RC.ANCHOR_SET_STALE`（severity WARN / `blocks_run=False`）；其中位数为 **Decimal、非 float、exponent == -12**（与上条 `test_attainment.py:749/752` 同一断言族） | `dce1ac5`（ATT-1）/ ORCH-40 第3条 / ORCH-37 第8条 / ERRATUM-08 |
| **LOO-1 影响力量度 q12 且两跑逐字节相等** | LOO-1 新增 7 条测试，其中一条逐字为「**值为 q12 Decimal 非 float 且两跑逐字节相等**」；裁定的算式 `loo_impact[m] = max over 参评策略 s of |composite_LOO(m,s) - composite_base(s)|`，**L954 维度内重归一、q12 Decimal、不经 float**；实测 `loo_impact_max = M_REV_MINOR 0.120000000000`（次高 `M_CONTACT_FREQ_PER_30D 0.098323076923`，唯一最大者无并列）与手算逐位相符；回归 `tests/test_sensitivity.py` **29 passed（22 旧 + 7 新）** | `858ebc8`（LOO-1）/ ORCH-40 第7条 / ORCH-41 第2条 |
| G-14 判据口径为 Decimal 除法 | G-14 判据 = C 类计数 / **9**：基线 `3/9 = 0.333333333333` → 变体 `5/9 = 0.555555555556`，`Δ = 2/9 > numeric.TOL`（12 位十进制展开，非 float） | ERRATUM-11 / ORCH-41 第8条 / G14FIX @ `42d5346` |
| P2-wire-A 的接线约束 | 报告面渲染 `loo_impact` 时**数值 Decimal 原样输出不经 float、不四舍五入到少于 q12** | ORCH-41 第4条（对 P2-wire-A 的强制要求） |

**判定：V-9 ✅ 成立。** 唯一保留：全量终值数字 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`。**不为业务口径背书**：`SHORTFALL_CLAMPED` 第四公式属 ADJ-7 **推断实现**（M02 只给 3 个公式），V-9 的 ✅ 只覆盖「金额 int 精确 / 比率 1e-12 / 不经 float」的**数值口径本身**，不为该第四公式的业务正确性背书（初版 D-10，仍有效）。

### B-2 · V-14 无静默降级：**逐条给证据 + 逐条写明仍未闭环的部分**

**已落地的披露通道（每条给出处）**：

| # | 披露通道 | 证据 | 出处 |
|---|---|---|---|
| 1 | **frame 级披露通道**（`NormalizedFrame.warnings` / `.excluded`） | MODELS-1 落地 ORCH-32 第2/5条：frame 级 `warnings` 与 `excluded` 两列 + 全指标 INACTIVE 零行断链守护；spine 由 6 红降至 4 红 | `cc18a38`（MODELS-1）/ ORCH-32 / ORCH-38 第1条 |
| 2 | **`EvidenceScope.excluded`**（出桥范围按评价期过滤的显式披露） | EVID-1 落地：出桥由 **13 → 12**（多出的 S-005/v1 为 RETIRED、`offline_date=2026-06-30`、本期以 v2 出值），D-EVID-01 CLOSED；判据等级 **derived:**（verbatim 侧 L1063②/⑥、L1003、L942、L1459；等式本身 derived，取自 A1CPREP §6-B.2/§6-B.4 + ORCH-37 第9条）；驳回「RETIRED+offline_date」判据（T4 设计卡无该两列，在 T2 `strategy_master` L1121/L1123，而 L976 签名无 master 入参 → 本层不可实现，**未叠加凑数**） | `897cad1`（EVID-1）/ ORCH-40 第2条 |
| 3 | **`ANCHOR_SET_STALE` 回退留痕** | ATT-1：`anchor_set` 失效时回退当期池并**落码留痕**（`RC.ANCHOR_SET_STALE`，WARN / `blocks_run=False`）；`anchor_set=None` 时保持既有池口径且**不臆造码（H-7）**的处置经 ORCH-40 第3条追认 | `dce1ac5`（ATT-1）/ ORCH-37 第8条 / ERRATUM-08 |
| 4 | **`mix_quality_verdict` 接进 report.md ⑥** | G14FIX 落地 GAP-06：`dsm/reports.py:419` 的 `_section_6`（对应 SDD `[L1063]⑥`）；实测 `PoolStats A3B3C3D2=11 / NA=2 / 已参评 9`，G-14 判据 `3/9 → 5/9` 触发 `MIX_QUALITY_DEGRADED`。**修 GAP-06 的理由逐字**：「否则算出而不披露 = 静默降级（V-14）」 | `42d5346`（G14FIX）/ ORCH-36 第4条 / ORCH-40 第6条 |
| 5 | **披露码注册表单点化 + 消除 PLACEHOLDER 码** | CODES-2 注册第 3 批 `EV_OUT_OF_EVAL_PERIOD`（severity **INFO** / `blocks_run` **False**），消除 EVID-1 遗留的 PLACEHOLDER 披露码；总数钉子 **90 → 91** 并保留 BATCH2 全部断言；`_BASIS` 逐字登记（severity derived: L1063②/⑥+L1003+L1459+L1117/L1121/L1123，与同语义族 `GR_VERSION_BREAK`(INFO) 对齐；`blocks_run` derived: 不属 M22 L917 的 BLOCK 行任一情形）；`tests/test_evidence.py` 的范围过滤披露断言由「等于 PLACEHOLDER 常量」**精确化**为「等于注册码 + `is_registered` + severity INFO + `blocks_run` False」（R-14 精确化）；实测 `reason_codes + evidence + architecture` = **62 passed / 0 failed** | `32cafd0`（CODES-2）/ ORCH-41 第1条 |
| 6 | **显式拒绝而非静默近似** | whatif GEOMETRIC 近似归因分支本 RUN 不补（D-A4-02，WONTFIX-THIS-RUN），现状抛 `WhatifOperatorError` —— ORCH-36 第10条逐字认定「**是显式拒绝，符合 V-14**」 | ORCH-36 第10条 |
| 7 | **severity 与 blocks_run 分离**（防止为过测试而改严重度） | 口径定为「**severity 是签认属性（任何 lane 与主控都不得为通过测试而改写，V-14），是否阻断本轮只由 `blocks_run` 决定**」；两处 R-12 PLACEHOLDER 严重度（`SPEARMAN_ZERO_VARIANCE`、`APPROXIMATE_ATTRIBUTION`）**维持暂定 WARN + PLACEHOLDER 标记，不得升格 BLOCK**，其正当性来源是 V-14（必须披露）而非门禁 | ORCH-30 第1/3条 / ORCH-34 第1/2条 / 初版 D-3 / L-05 |

**仍未闭环的部分（如实写明，禁软化）**：

1. **M28 降级矩阵 26 行逐条遍历断言仍不存在**。初版实测：M28 矩阵 **26 行**（SDD L1280-L1305），`grep -rn 'M28' tests/*.py` 仅 **3 处**命中且**全在 `test_preflight.py` 的 docstring / 注释**（L6 / L506 / L596），**零断言**；最接近的 `tests/test_reason_codes.py::test_every_downgrade_path_has_a_disclosure_code`（PASS）只断言 `CONTRACT_DISCLOSURE_CODES`（实测 15 个码）全部已注册，**既未逐条对应 26 行，也未断言「出现在报告中」**。→ **该缺口至今无包认领落地证据**，`PLACEHOLDER-TO-REFRESH(P2-wire-B / 26 行 × 六列逐条断言)`。
2. **`excluded` 与 `loo_impact` 的报告面出口在 P2-wire-A 施工中，尚未落地**。ORCH-40 第2条逐字：「**V-14 端到端未闭环（`excluded` 只到 API 层）→ 接线归 P2-wire-A ③**」；ORCH-41 第4条逐字：`dsm/reports.py:451` 只渲染 `loo_dominant_metrics`，**`loo_impact` 排名在报告面无任何出口**，致 SDD **L748**（每指标的 LOO 影响力排名）、**L1409**（`loo_impact` 最大者 + 报告输出「存在单一指标过度影响」）、**L1858**（是否存在某一指标过度影响综合得分 → `sensitivity_report`）三处**契约强制产出物对用户仍不可见**，属 V-14 披露缺口；第⑧条已由「条件项」**升为必做项**，优先级 **③(EVID-1 披露) > ⑧(LOO 排名出口) > ②(G14 cli) > ① > ④ > ⑤ > ⑥ > ⑦**（⑦ 编码门禁收窄 D-TOOLS-01 时间不够可移交 P2-wire-B，**③ 与 ⑧ 必须完成**）。→ **在 P2-wire-A 落地前，本文件不得声称 V-14 端到端已闭环。**
3. **注册表规模数字须重测**。初版曾登记 **79 码（BLOCK 28 / WARN 38 / INFO 13）**、`CONTRACT_DISCLOSURE_CODES` **15**、`tests/test_reason_codes.py` **18 passed**，但初版 §四 已自证该组数字是 **R15B2（`db13471`）提交前快照**；此后 R15B2 与 CODES-2（`32cafd0`，总数钉子 **90→91**）均已改变注册表 → `PLACEHOLDER-TO-REFRESH(P2-wire-B / 注册表规模与 ratchet 32→28)`。
4. **`dsm/cli.py:250 cel_contract_version` 与 `:252 reproducibility_hash` 仍是 PLACEHOLDER** → 归 P2-wire-A ⑤（ORCH-40 第4条）。

**判定：V-14 ❌（机制层已有多条真实披露通道，端到端未闭环）。**

### B-3 · V-6 + G-03 + P-2：红线非补偿（不可用其它指标的好分数抵偿红线违反）

| 证据面 | 证据 | 出处 |
|---|---|---|
| golden G-03 | `tests/test_golden_a.py::test_g03_hard_redline_forces_l4_and_composite_stays_but_does_not_count` **`1 passed`**（HARD 红线强制 L4；composite 照算但**不生效** = 非补偿的直接断言） | 转录初版 @ `358b4ea`，SDD L1499 |
| 属性 P-02 | `tests/test_properties_all.py::test_p02_hard_redline_grade_equals_forced_no_matter_how_good` **`1 passed`**（「无论其它指标多好」= 非补偿的随机化守护） | 转录初版 @ `358b4ea` |
| 模块层 | `pytest tests/test_redline.py -k g03` = **`5 passed, 16 deselected`**，含 `test_g03_hard_row_has_no_weight_or_deduction_hook`（HARD 行**无权重/扣分钩子** → 结构上不可能被补偿）、`test_g03_redline_bypass_keeps_the_score_identical`、`test_g03_soft_crossing_deducts_alone_and_never_forces`（SOFT 只单独扣分、从不强制） | 转录初版 @ `358b4ea` |
| 未被后续变更推翻 | A1c @ `6299245` 提交说明逐字：「**G-03/G-15 零影响**」；D-A1-03 的 BLOCK 缺格载体由 `M_COMPLAINT_RATE`（HARD 红线）**迁至 `M_SATISFY_SCORE`** 并同维对调 `missing_rule`，解 `dsm/redline.py:330` 死锁且「**G-09 四分支不塌（g09 实测仍绿）**」 | `6299245` / ORCH-37 第1条 / ORCH-40 第5条 |
| 三角验证不可补偿（旁证） | `test_t_tri_01_veto_is_boolean_only_and_not_compensable`（veto 仅布尔、不可补偿）在同文件全绿批次内 | 转录初版 @ `358b4ea`（V-13 辅证） |
| 相关缺口 | ①`preflight.py:209-211`「全维清空也 BLOCK」分支归 P2 核验（ORCH-35 第4条：仅在与 L901「清空维度数 >= 2 → BLOCK」严格等价时可保留；维度总数为 1 且被清空应为 WARN，不等价则修正，并须补边界测试）；②CONSUMPTION-TODO #7 的 WARN→BLOCK 行为变更已批准（M22 L902 逐字 BLOCK），换 `WEIGHT_DICT_MISALIGNED` 并同步进 `RUN_BLOCKING_CODES` 与 DISCLOSURE，须复核 `tests/test_preflight.py:240` 与 L451 一致性断言**不得弱化** → 归 P2-wire（ORCH-36 第9条） | ORCH-35 第4条 / ORCH-36 第8/9条 |

**判定：V-6 ✅（红线非补偿成立）。** 终值全量数字 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`。

### B-4 · G-02 + P-6：证据门禁 + 分池禁混排

| 证据面 | 证据 | 出处 |
|---|---|---|
| G-02 golden 载体 | `tests/test_golden_a.py:416 def test_g02_c_class_high_score_is_gated_to_l2_and_ranked_only_in_c_pool`（**C 类高分被门禁压到 L2，且只在 C 池内排名** = 门禁 + 禁混排同一断言） | **本包亲自 grep 取证** @ HEAD `858ebc8` |
| P-6 属性 | `tests/test_properties_all.py:552 def test_p06_downgrading_evidence_to_C_never_relaxes_the_L1_library_gate`（**证据降级到 C 永不放松一级库门禁** = 非补偿式门禁的随机化守护） | **本包亲自 grep 取证** @ HEAD `858ebc8` |
| 分池键 = `biz_domain × evidence_class` | `tests/test_pooling.py:142 def test_pool_key_is_domain_times_evidence_class`；`tests/test_pooling.py:601 def test_models1_step7_pool_key_refuses_a_missing_evidence_class`（Step7 严键：`evidence_class` 缺失即**拒绝**，不得混排） | **本包亲自 grep 取证** @ HEAD `858ebc8`；契约依据 SDD **M43 L942**「标准化在池内进行（`biz_domain × evidence_class`）」 |
| C 类禁入一级库 | `tests/test_pooling.py:184 def test_g02_c_class_barred_from_primary_library`、`:201 def test_g02_clean_a_b_l1_rows_are_admitted`；原文三处互证 **L1002 / L137 / L1436**（C 类不得进一级库 → 一级库内 C 恒 0，这正是 ERRATUM-04 的成因） | **本包亲自 grep 取证** @ HEAD `858ebc8`；ERRATUM-04 |
| 池键顺序矛盾的处置（分池不被破坏） | **M29 L1334**（Step2 normalize 在 Step3 evidence 之前）vs **M43 L942**（池键含 `evidence_class`，而它由 Step3 才产生）→ 本 RUN 采「**Step2 松键 + Step7 严键**」读法：`PoolKey.evidence_class` 改为**可选**，Step7 严键拒绝缺失（上条 `:601` 即其守护）；D-MODELS-01 CLOSED @ `cc18a38` | 初版 D-9 / ORCH-29 第4条 / ORCH-38 第1条 |
| G-14 与分池同源（不得两个分母） | `tests/test_pooling.py:381 def test_mix_quality_degraded_needs_a_signed_baseline`（**本包亲自 grep**）；G14FIX 落地：分子 = **C 类占比**（verbatim L1416，`pooling.py:101/264-281/300`）、分母 = `assessed_denominator()` 与同模块两列 `share_*` **同源**（L1004 verbatim 负向排除 + 同源 derived）、阈值 `numeric.TOL` **一字未改**仅标工程默认（K-21）；追认**不改 `LOW_EVIDENCE_CLASSES` 常量**的处置正确（该常量另承担 `low_evidence_share()` 的 (C+D) 披露口径，被 `g14 :1692-1699` 与 `test_pooling:350/352` 钉住） | **本包亲自 grep** + `42d5346` / ORCH-36 第1/2/3条 / ORCH-37 第7条 / ORCH-40 第6条 |
| 三口径权威化（防分母混用） | **12** = evidence 侧出桥（只服务 Step-3 分类，M34 的 4-12 → 6-12）；**11** = pooling 侧 universe 四类合计（ORCH-37 第6条读法甲 + L1003 + L1063⑥，服务 `evidence_structure` 与 (C+D) 披露）；**9** = 11 − NOT_ASSESSED(2)（ORCH-36 第3条同源 + L1004，服务 `c_class_share` 与两列 `share_*`）→ **G-14 判据分母 = 9** | ERRATUM-11 / ORCH-41 第8条（采 E3PREP 独立手算，**先算后测**，与 A1c 提交说明逐位吻合） |
| **证据不足处（PLACEHOLDER）** | ①上述测试函数的**通过/失败终态**本包未复跑（并发禁跑全量）→ `PLACEHOLDER-TO-REFRESH(P2-wire-B)`；②`g14` 三条在 `42d5346` 时点**仍红**，ORCH-40 第6条认定「根因全在 A1c 后过期的手算 expects → E3b（**未反填**）」，ORCH-41 第8条进一步**允许 E3b 按 E3PREP 独立手算值更新陈旧常量**（属 R-14 的「手算更新」，非「照抄实现输出」），但若贴补丁 4 后仍红则判 G14FIX 修得不彻底、**报 blocked 附差异表，严禁按实测反填**；③K-23：当前 NOT_ASSESSED 中 C 类 = 0，使 G-14 分子（全体口径）与分母（已参评口径）的 population **巧合一致**，A1CPREP §6-B.4 里 S-008 就是「C 类且 NOT_ASSESSED」→ **这是数据巧合非契约保证**，须披露 | ORCH-40 第6条 / ORCH-41 第8条 / K-23（ORCH-40 第6条） |

**判定：G-02 + P-6 + 分池禁混排 ✅（机制层，测试载体已亲自 grep 存在；终态数字待 P2-wire-B）。**

---

## §C 裁决台账（ORCH-31 ~ ORCH-41）

| 裁决 | 裁了什么 | 决定性理由 | 落地包 | 落地 commit | 状态 |
|---|---|---|---|---|---|
| **ORCH-31**（T+5.28h） | ARCH-1 收口 + P2 签名 delta 三项 + `arch1_residual_gaps` 两项；`docs/adr/` 归档 | 架构批（H-8 单点时钟 / INV-1~3）已实测转绿，P2 接线前须先钉签名 | ARCH-1 → P2-cli / P2-wire | `bb89abc` 前后（ADR：`docs/adr/RUN-ORCH-27-layer-dependency-final.md` 系列） | 已落地（ADR 归档） |
| **ORCH-32**（T+5.5h 前后） | 授权 `NormalizedFrame` 增 **frame 级披露通道**（`warnings` / `excluded`）+ `PoolKey.evidence_class` 改**可选** + 全指标 INACTIVE 零行断链守护；并预声明「MODELS-1 可能造成第三次哈希失效」 | D-MODELS-01（M29 L1334 Step2 在 Step3 前 vs M43 L942 池键含 `evidence_class`）必须解，且 V-14 需要 frame 级披露载体 | MODELS-1 | `cc18a38` | 已落地；**其哈希预声明经 ORCH-38 第4条按实测更正为「未失效」→ L-08** |
| **ORCH-33** | E3 收口 + 哈希台账 seq1 补全 64 位 + 纠正 ORCH-30 只预声明 A1c 的遗漏 | SEAM-1（`8f2eca3`）造成的失效**未被预声明**，台账必须记实测并标注遗漏 | 主控（台账）/ P3a | 台账更正 | 已落地 |
| **ORCH-34**（T+5.59h） | R15B2 收口七项：①`DESIGN_CARD_TABLE_ABSENT` 退出码**以 M21 L892 的 io 层 4 为准**（ORCH-30 第4条「退出码 2」属层归属误记，更正）；②两处 R-12 PLACEHOLDER 严重度维持 WARN、**不得升格 BLOCK**；③ratchet **32→28 收缩不在本批做**，排给 P2 且必须在 A1c 之后；④CONSUMPTION-TODO 9 条分派；⑤`models_questions` 4 项本 RUN 不做；⑥全量口径统一为 **13/2182/2195 @ `358b4ea`**；⑦复现哈希登记纠正为 **`4de4b8cb…`** | 「设计卡表整体缺失」语义上是**输入表加载失败**而非轮级门禁阻断；一码两退出码属口径矛盾；原文无严重度列，暂定值只是工程默认，正当性来源是 V-14 而非门禁；A1c 会重生成 fixtures，先收缩会二次改动 | P2-cli / P2-wire / P3a / P3c | `db13471`（R15B2）+ 台账 | 已落地；③ 的 ratchet 32→28 **仍待 P2-wire-B** |
| **ORCH-35**（T+5.67h） | G-10「维度被清空」原文互斥裁决：**规范判据 = M22 C-02（SDD L901）**，实现正确、**测试期望过严**；M31 L1412 与 §4.4 L1585 记为文档勘误（ERRATUM-01）；`DIMENSION_EMPTIED` 无原文依据（ERRATUM-03）；`preflight.py:209-211` 归 P2 核验；D-SPEC-G10 → **CLOSED-BY-ORCH-35** | **内部一致性论证，不依赖任何「哪节权限更高」的元规则**：L901 同句内既规定「单维清空 → 该维度 W 置 0 重归一」，又规定「清空维度数 >= 2 → BLOCK」；若单维清空即 BLOCK，则「W 置 0 重归一」一支**永无执行机会而成死条款**；原文同句保留两支即证明单维清空被设计为可继续。M28 **L1286** 同文为第二来源印证。故 ADJ-G10 提出的「L911 是否覆盖 M31 golden 表」争议不影响本裁决（另记 ERRATUM-02） | E3b（测试改名 + 新增 >=2 维 BLOCK 测试）+ P2（preflight 分支核验） | 待 E3b / P2-wire | **裁决已定，落地在飞**（E3b 写集，见 ORCH-41 第8条采纳的 g10 方案：断言类数 6 → 11 严格增加） |
| **ORCH-36**（T+5.90h） | G-14 口径裁决（分子改 **C 类占比** / 分母**同源剔 NOT_ASSESSED** / 阈值保持 `numeric.TOL` 仅标工程默认并立 **K-21** / **GAP-06 必须接线**）+ **P2 拆为 P2-cli 与 P2-wire** + CONSUMPTION-TODO 9 条逐条分派 + whatif GEOMETRIC 本 RUN 不做（D-A4-02 WONTFIX）+ tf 额度上调 + 编码门禁四要素与作用域收窄（D-TOOLS-01）+ pytest 命令口径固化（L-07） | **SDD L1416 是唯一明文，C+D 口径零原文依据**；且守护点若度量 C+D 则对其声称要防的情形**完全失效**（D→C 搬运时 (C+D) 恒 8/11 不变），**违 V-14**；L1416「一级库中」限定语与 L1002/L137/L1436 字面互斥 → ERRATUM-04 交签认，不据字面实现。**同模块对同一概念用两个分母不可辩护** → 分母必须与 `share_*` 同源。改阈值即发明业务参数、违 R-12 | G14FIX（分子/分母/GAP-06 接 reports）+ P2-cli + P2-wire（cli 侧 / message / 编码门禁） | `42d5346`（G14FIX）、`2ee10ed`+`da88ff7`（P2-cli） | 已落地（cli 侧 GAP-06 出口与 ERRATUM-07 的 message 更正**移交 P2-wire-A**） |
| **ORCH-37**（T+6.04h） | A1CPREP §9.3 **十项裁决**：①追认 `missing_rule` 同维对调 + 洞迁 `S-008/v1/M_SATISFY_SCORE`（**主控自我纠错**：ORCH-29 第5条前提被 `MISSING_CELLS` 刻意构造证伪）；②D-A1-05 拆为 **A1d** 且降级为条件执行；③双口径同时入册（主体级 **A3B3C4D2** + 行级 **A3B4C4D2**）；④只补 `alt_method_note`、**不补** `interpretation_limit`（B 类无该义务，`evidence.py:248-249` + L1172/L1293）；⑤补 `whatif_run_id` 必须同时补 `ahp` 段、沿用 SYNTH 合成命名并标注待签认、**不得伪造业务真值**；⑥占比双报分母裁 **11**（读法甲，与 ORCH-36 第2条独立结论一致 → 双来源交叉印证）；⑦G-14 分子维持 C 类占比、不采 C+D，`reason_codes.py:86` 的 message 属实现侧自撰、**以其为据属循环引证** → ERRATUM-07；⑧`IMPUTE_MEDIAN` 参考集取 `anchor_set`（失效回退当期池 + `ANCHOR_SET_STALE`），依据等级 **derived:**（L1134 零字规定）→ ERRATUM-08，落地新立 **ATT-1**；⑨13 vs 12 归实现侧 → 新立 **D-EVID-01 / 包 EVID-1**，不补事实不删卡（保 G-08）；⑩D-A1-08 落地新立 **ATT-1**，不并入 MODELS-1（写集零交集、MODELS-1 已饱和） | 原文优先 + 单写者纪律 + R-14 边界（「A1c 只允许改 golden_map 的**载体指纹类字段**；`expects`/`hand`/`probes[].e` 的任何数值改动一律留 E2b/E3b 独立手算」） | A1c / ATT-1 / EVID-1 / MODELS-1 / P2-cli 五包并发（写集两两不相交，6 槽满） | `6299245`、`dce1ac5`、`897cad1`、`cc18a38`、`2ee10ed` | 已落地；**第6条「分母裁 11」的措辞经 ORCH-41 第8条精确化为三口径（ERRATUM-11）** |
| **ORCH-38**（T+6.17h） | MODELS-1 收口（`cc18a38`）+ **两项写集/断言偏离追认** + 🔴 **复现哈希台账按实测更正**（seq2 未失效）+ 🔴 **A1d 触发条件已满足 → 必须执行** + A1d 范围收紧（目录布局迁移不在内）+ 新权威基线 **11/2190/2201** + L-08 / L-09 | 追认理由见 §G-①/②；哈希更正理由：`dsm/audit.py:242` 只哈希 `score_card` / `grade_ledger` / `weight_version_id`，MODELS-1 是**纯增披露面**、被哈希数值一位未变 → 「预声明可能失效」≠「必然失效」（**L-08**）；A1d 触发条件 = 「是否存在专门因 JSONL 而红的测试」，MODELS-1 实测 `step1_io_loaders_loads_the_frozen_design_card_table` 红、根因正是 design_card 为 JSONL 而 io_loaders 只认 CSV/Parquet（D-A1-05） | 主控 / A1d / P3a / P3b | 台账 + `ac12ed5` | 已落地；A1d **在飞**（ORCH-40 第8条 + ORCH-41 第1条两次修订其写集与修法） |
| **ORCH-39**（T+6.32h） | P3C-draft 收口（`2313857`）+ KNOWN-GAPS 阻塞数裁 **24**（立 **D-DOC-01**）+ CLI 无 console script 事实入册（立 **D-CLI-01**，本 RUN 不补以免写集扩散）+ 新权威基线 `after_MODELS1` 登记（11 红拆分留 PLACEHOLDER 待 P2-wire-B）+ 派 **ADJ-G07** + **进度压缩六项裁定**（E2b/E3b 由串行改并行；新增只读预备包 E2PREP/E3PREP 前移手算 expects；P3b 提前到 A1d 落地即派；**P2-wire 拆为 A/B**；P3a 与 P3c 并行；空槽优先级 A1d > E2b/E3b > P2-wire-A > P3b > P3a/P3c） | 文件汇总节自称 19、实测逐行 grep（含 F-1/F-2 加粗「是」）= **24**，裁 24 为权威值，**文件更正归 P3c 正式包写集、主控不代改**；`pyproject.toml` 无 `[project.scripts]` → SDD L805/L836 的 `dsm` 可执行入口未落成，唯一入口 `python -m dsm.cli`（8 条叶子命令与 L1080-L1087 逐条对应，公共 6 参数 + `--schemes`，退出码 0/2/3/4/5/6/7）；**余量 3.68h 而原串行关键路径估算 >4.3h 必超线**，而 **S7 方法层与 S8 权重链（档 2）不得砍，故只压编排不砍范围** | P3c / P2-wire-A / P2-wire-B / P3b / 本包（P3a-pre2） | `2313857` + `313a0d6` | 已落地；**本包（P3a-pre2）即 ORCH-39 第6.5条 + ORCH-41 第9条的产物** |
| **ORCH-40**（T+6.84h） | 六包收口（CODES-2 / EVID-1 / ATT-1 / P2-cli / A1c / G14FIX）+ 裁 **g07 为实现缺项**（D-D2-01 由 OPEN-WONTFIX-THIS-RUN **改判待修**，派 LOO-1）+ 裁 A1d 的 **R1~R5** 五项前置争议 + **E2b/E3b 范围重定义**并与 A1d 三包并行 + 哈希台账 **seq3/seq4** 补记（现值 `e5923465…`）+ 立 **K-22 / K-23** + 四包预算超支核可不返工（立 **L-10**） | g07：LOO「影响力」量度经 ADJ-G07 只读取证后裁为**实现缺项**（SDD L748/L1409/L1450 逐字要求「影响力排名」，而 `_run_loo` 只累计等级翻转数并按 targets 顺序 append dominant，`models.py` 无承载字段）；裁定量度 = `max over 参评策略 of |composite_LOO − composite_base|`（L954 维度内重归一、q12、**不经 float**），并列报 blocked **禁自造 tie-break**，dominant 改按 `loo_impact` 降序，**保留 flip_rate 警示判据为独立字段**；⚠️ 因 A1c 上报 g07 已转绿 → interrupt 调整 LOO-1 任务性质为「补齐契约强制产出物**且不得打破已绿 g07**」，若改排序会使 g07 变红则**报 blocked、不得动测试一个字** | LOO-1 / A1d / E2b / E3b / P2-wire-A / P3a | `32cafd0`、`897cad1`、`dce1ac5`、`2ee10ed`+`da88ff7`、`6299245`、`42d5346` | 已落地；A1d/E2b/E3b/P2-wire-A **在飞** |
| **ORCH-41**（T+7.05h） | A1DPREP / E2PREP / E3PREP / LOO-1 四包收口 + **驳回 `models.py:373` 放宽方案**改走 io_loaders 列级口径 + LOO-1 新字段**可选性硬约束** + **P2-wire-A 第⑧条升为必做** + **E2b/E3b 按 golden_map 单写者切分**（第5条：把 golden_map 的 hand 修正**从 E3b 改判给 E2b，撤销 A1c ADR §11 的分派**）+ **G-14 三口径权威化（ERRATUM-11）** + K-24~K-29 入册 + L-11 / L-12 + 第9条：再派 **P3a-pre2 与 P3c-pre2**（写集不相交，把交付尾部文档工作前移，**只留最终数字待 P2-wire-B 刷新**） | 驳回 `success_criteria: str → str \| None` 的三条决定性理由：①与 `tests/test_golden_a.py:885` 既有绿断言 `assert card.success_criteria == ''` 造成同一逻辑数据在 spine 路径得 `None`、golden_a 路径得 `''` 的**双值不一致（串味）**；②`dsm/models.py` 是 **LOO-1 的独占写集**（R-15 单点授权），并发写同一文件；③需连带改 `dsm/evidence.py:246-249` 做 None 防御，扩大写集（且 CODES-2 刚落地，ORCH-41 第1条明令禁改）。改采 **io_loaders 列级口径**：凡模型字段为必填 `str` 的列，其空单元格不得被 `NULL_LITERALS` 升格为 `None`（空串本身就是合法 str 值）；**严禁全局改 `NULL_LITERALS` 语义**（会连带 8 张表）。golden_map 单写者理由：`fixtures/golden/golden_map.json` 是 `tools/gen_golden.py` 的**生成物**，golden_a 与 golden_b 的 `hand`/`probes[].e` 都在其中 → 二者不可分写；**严禁手改 golden_map.json**（手改会被下次重生成覆盖并破坏冻结可复现性，ORCH-40 第5条） | A1d / E2b / E3b / P2-wire-A / **P3a-pre2（本包）** / P3c-pre2 | `858ebc8`（LOO-1）+ 本包提交 | **本包即其第9条的落地产物**；A1d/E2b/E3b/P2-wire-A 在飞 |

---

## §D ERRATUM 台账（11 条，9 → 11）

| ID | 原文位置 | 问题 | 处置 | 状态 | 归属 |
|---|---|---|---|---|---|
| **ERRATUM-01** | SDD **M31 L1412** 与 **§4.4 L1585** | 两处写「维度被清空 → BLOCK」，与规范判据 **M22 C-02（L901）**「清空维度数 >= 2 才 BLOCK、单维清空 WARN + 该维度 W 置 0 重归一」不一致 | **本 RUN 以 L901 为准**（ORCH-35）；交业务签认。若业务确认单维即阻断，则属 **C-02 阈值变更（>=2 改 >=1）**，须走契约变更流程并同步改实现与本裁决，**不得由本 RUN 单方决定** | **已裁定**（本 RUN 口径）+ **OPEN-需业务确认**（阈值是否变更） | P3a 披露 + 业务签认 |
| **ERRATUM-02** | SDD **L911** 口径统一声明 | 其适用范围只逐字约束「C 表 vs DSN」，对 M31 golden 表的权限**未逐字明确** | ORCH-35 的裁决**不依赖 L911**（改用内部一致性论证 + M28 **L1286** 第二来源），故不影响结论；该**元规则争议**交签认 | **OPEN-需业务确认** | P3a 披露 + 业务签认 |
| **ERRATUM-03** | `dsm/reason_codes.py` 的 **`DIMENSION_EMPTIED`** | 该码名在 **SDD 全文 0 命中**，属**工程自名** | 按 **ADJ-3 不改名不删除**；`severity`/`blocks_run` **服从 L901**（单维清空场景 WARN / `blocks_run=False`）；P3a 须披露**无原文依据**。ORCH-35 第2条进一步要求：E3b 的 g10 断言中 **`DIMENSION_EMPTIED` 不得出现**，披露码用注册名 **`WEIGHT_REALLOCATED`** | **已裁定**（不改名 + 服从 L901），**无原文依据这一事实须永久披露** | P3a 披露 |
| **ERRATUM-04** | SDD **L1416**（§3.16.2） | 逐字为「构造**一级库中** C 类占比上升的场景」，但 **L1002 / L137 / L1436** 明文 C 类不得进一级库（一级库内 C 恒 0）→「一级库中」这一限定语**字面不可满足**，会使 `MIX_QUALITY_DEGRADED` 判据**恒不触发** | **ORCH-36 第1条：不据「一级库中」字面实现，分子取「C 类占比」**（L1416 是唯一明文，C+D 口径零原文依据）；交业务签认是否应表述为「候选池 / 全体策略中 C 类占比」 | **已裁定**（实现口径）+ **OPEN-需业务确认**（措辞） | P3a 披露 + 业务签认 |
| **ERRATUM-05** | SDD 全文（**分母定义缺位**） | 「证据结构占比」的分母**从未被明文定义**；全文「分母」仅 6 处命中，唯一相关的 **L1004** 是**负向排除**（NOT_ASSESSED 不计入分母）。**13 卡出桥 / 12 事实 pair / assessed 集 / 池内策略数**四候选无一被点名 → **11 vs 12 在 SDD 层面不可判定** | **ORCH-36 第2条**：实现层要求分母与同模块 `share_*` 两列**同源**并依 L1004 剔 NOT_ASSESSED；11 vs 12 的数据侧由 A1c 依 A1CPREP 裁决处理（D-A1-07）；分母的**规范定义**交业务签认。**后经 ORCH-41 第8条升级为三口径权威（见 ERRATUM-11）** | **已裁定**（实现同源约束）+ **OPEN-需业务确认**（规范定义） | P3a 披露 + 业务签认 |
| **ERRATUM-06** | `dsm/pooling.py:74` 的注释锚 **`[L1854]`** | `LOW_EVIDENCE_CLASSES` 常量注释自引 SDD L1854 作为依据，但 **ADJ-G14 实测该行无「C+D」字样**，L1854 只给承载与防作弊目的、**不给分子** | 注释锚失效属**可辩护性缺陷**；G14FIX 改分子为 C 类占比后须**同步更正注释锚为 L1416**，并在 P3a 披露原注释锚不成立。G14FIX 落地说明逐字：分子 = C 类占比（verbatim **L1416**，`pooling.py:101/264-281/300`）；并**追认不改 `LOW_EVIDENCE_CLASSES` 常量**（该常量另承担 `low_evidence_share()` 的 (C+D) 披露口径，被 `g14 :1692-1699` 与 `test_pooling:350/352` 钉住，改常量会连带改既有断言） | **已裁定 + 已落地**（`42d5346`） | G14FIX + P3a 披露 |
| **ERRATUM-07** | `dsm/reason_codes.py:86` 的 **message 文本** | 写「**低证据等级占比上升**」，与 ORCH-36 第1条裁定的分子口径（L1416「C 类占比」）不符；该 message 是**实现侧自撰文本**，曾被 A1CPREP **误引为 C+D 口径的依据（循环引证）** | 更正为「**C 类证据占比上升**」，归 **P2-wire**（`reason_codes.py` 单写者）；**ADJ-3 不改码名**。ORCH-37 第7条明确：以 message 为据属**循环引证**，不得作为口径依据 | **已裁定**，落地**在飞**（P2-wire-A 写集含 `dsm/reason_codes.py`，仅限 `MIX_QUALITY_DEGRADED` 的 message） | P2-wire |
| **ERRATUM-08** | SDD **L1134**（`missing_rule` 枚举） | 只枚举 **ZERO / SKIP / IMPUTE_MEDIAN / BLOCK** 四种规则名，对 `IMPUTE_MEDIAN` 的「**中位数取自哪个参考集**」**零字规定** → 原文缺口。实现取当期池，导致 **G-05 不变性**（L1407 + L1428 P-4 + L1500 V-7）在**结构上不可能满足** | **ORCH-37 第8条按 `derived:` 裁为取自 `anchor_set`**（失效回退当期池 + `ANCHOR_SET_STALE`），**与 L941 同口径**；ATT-1 落地 @ `dce1ac5`（D-A1-08 CLOSED）；须走 **SDD 勘误 + 业务签认**。**遗留守护力缺口 = K-28**（现 fixtures 下 anchor-first 与 pool-only 中位数恰好相等 `0.101500000000` → g09 **vacuous**） | **已裁定 + 已落地**；**OPEN-需业务确认**（SDD 勘误）；**守护力缺口 K-28 未闭环** | ATT-1 + P3a 披露 + 业务签认 |
| **ERRATUM-09** | SDD **L982** | 写 **`EVIDENCE_DOWNGRADED_PARTIAL`**，而注册名是 **`EVIDENCE_CARD_PARTIAL`**（`dsm/reason_codes.py:69`） | 按 **ADJ-3 以注册名为准**，文档须更正；A1CPREP 附录A 已给 **36 行「文档码名 → 注册名」对照表**（ORCH-33 第6条：一律以注册名为准，对照表交 P3a 归档）。同类：M31 写 `STALE` 而注册名 `WEIGHT_VERSION_STALE` | **已裁定**（以注册名为准）；**文档更正 OPEN** | P3a 披露 |
| **ERRATUM-10** | SDD **L1085**（combine 命令级退出码「**0/3**」）vs **M21 L892**（io 层唯一出口 `DataLoadError` → 退出码 **4**） | P2-cli 实测：`cmd_combine_build` 的 `build_draft` **需读 `data/`**，故 combine build **可能出现 exit 4**，与 L1085 的「0/3」枚举冲突 | **以 M21 L892 为准**（io 层故障**优先于**命令级摘要）；**L1085 的退出码枚举未覆盖 io 层故障，属摘要不完整**。与 ORCH-34 第1条同源同口径（`DESIGN_CARD_TABLE_ABSENT` 亦裁归 io 层 exit 4） | **OPEN-需业务确认** | P3a 披露 |
| **ERRATUM-11** | **ORCH-37 第6条「占比分母裁 11」的措辞** | 该措辞易被误读为「**G-14 判据的分母 = 11**」 | **权威化为三口径**（E3PREP 独立手算，**先算后测**，与 A1c 提交说明逐位吻合）：**12** = evidence 侧出桥（只服务 Step-3 分类，M34 的 4-12 → 6-12）；**11** = pooling 侧 universe 四类合计（ORCH-37 第6条读法甲 + L1003 + L1063⑥，服务 `evidence_structure` 与 (C+D) 披露）；**9** = 11 − NOT_ASSESSED(2)（ORCH-36 第3条同源 + L1004，服务 `c_class_share` 与两列 `share_*`）。**精确化为「pooling universe 分母 = 11，G-14 判据分母 = 9」；二者不矛盾**（前者是结构计数分母，后者是已参评分母）。G-14 判据 = C 类计数 / 9：基线 `3/9 = 0.333333333333` → 变体 `5/9 = 0.555555555556`，`Δ = 2/9 > numeric.TOL` | **已裁定** | E3b 落实 / P3a 披露 |

**ERRATUM 计数**：**11 条**（初版建表时为 9 条，ORCH-40 第4条新增 ERRATUM-10、ORCH-41 第8条新增 ERRATUM-11）。其中**已裁定** 8 条（01/03/04/05/06/07/08/09/11 中的裁定面）、**OPEN-需业务确认** 5 条（01 的阈值面、02、04 的措辞面、05 的规范定义面、08 的 SDD 勘误面、10）—— 同一条可同时具两面，逐条见上表「状态」列。
---

## §E 缺陷台账（27 条，23 → 27）

计数（本包依 `ops/dag-state.json` 的 `defects` 数组逐条实读）：**CLOSED 16** + **CLOSED_AS_MISREPORTED 1** + **CLOSED-BY-ORCH-35 1** + **OPEN 7** + **ACCEPTED-DISCLOSED 2** = **27**。

| id | 症状（摘） | 归属包 | commit | 状态 | 依据 |
|---|---|---|---|---|---|
| D-C1-01 | `read_parquet(dtype=str)` → pyarrow `TypeError`；**被 venv 无 pyarrow 静默掩盖**（正是 V-14 要防的情形） | C1b | `6430e2b` | **CLOSED** | 装 pyarrow 26.0.1 后重跑 `tests/test_io_loaders.py`；新增 CSV/Parquet 双分支逐字段值+type 双断言；pyproject 增 parquet extra（ADJ-8） |
| D-A2-01 | H-9 INV-1：`weights_combine.py → dsm.weights_ahp` | A2b | `41f0e13` | **CLOSED** | ADR `RUN-ORCH-27-layer-dependency-final.md`；Step1 改消费 `AhpHierarchySnapshot` 快照，新增 keyword-only 必填 `elicit_hierarchy` |
| D-A1-01 | `dsm/fixtures_gen.py` L316/319/322/482 reason_code 裸字面量，违 P-8 | A1b | `0547190` | **CLOSED** | 改 `RC.*.value`；重生成 fixtures 须逐字节相同 |
| D-A3-01 | `weights_calibrate.py` L84/85 import L0a/L0b，违 M00 L294 | A3b | `dcf12e4` | **CLOSED** | 四能力改 `CalibrationInputs` keyword-only 必填注入；`calibrate(...)` 冻结 marshal 不变 |
| D-A4-01 | `whatif.py` L262/275 import `audit`(L6)，违 M00 L294 | A4b | `9078201` | **CLOSED** | 目录哈希改 callable 注入（R-7 禁重复实现）；`WhatifReport` 新增 `readonly_proof` |
| D-A4-02 | `whatif.py` L571 `'GR_REDLINE_FORCED'` 裸字面量 + L76 `NOT_ASSESSED` 域常量，P-8 ratchet | A4b | `9078201` | **CLOSED**（裸字面量面） | 改 `RC.*`（同段 L573 已用 `RC.*`）。**⚠️ 须区分**：ORCH-36 第10条另裁「whatif **GEOMETRIC 近似归因分支**本 RUN 不补，登记 D-A4-02（**WONTFIX-THIS-RUN**）」→ 该**功能缺口面**仍 OPEN，M10 L674/L473 要求尚未实现，`APPROXIMATE_ATTRIBUTION` 的 severity 为 PLACEHOLDER，现状抛 `WhatifOperatorError`（显式拒绝，符合 V-14），**交下一版本** |
| D-B1-01 | `_apply_missing_rule` 只在「事实行存在且 value<0」时分派；整行缺失 → **ZERO/IMPUTE_MEDIAN/BLOCK/SKIP 四分支塌缩**，违 G-09 | B1b | `996e1c3` | **CLOSED** | E2 手算独立重算（`d3b3d5f`）：ZERO 应 1 行 `attainment=0`/COST `0.399159663866`/composite `0.826551606617`，实测 0 行/`0.798319327731`/`0.882433959559`；BLOCK 应不出分而实测出分 `1.161723266903` |
| D-SEAM-01 | 单例池 → normalize 判 sd=0 不出 `composite_relative`；pooling 对 null 一律抛 `PoolingInputError` → M29 Step7 中断，卡住 G-01/G-02/G-04 与 spine×14 | SEAM-1 | `8f2eca3` | **CLOSED** | ADR `RUN-ORCH-28-normalize-pooling-seam.md`：锚定参考尺改为**不按池裁剪**（`anchor_ref[(period,metric)]`），回退仍严格池内；有标注的 null 由 `reject_reason` 承载而非抛错 |
| D-A1-02 | 四条 DID+CONCURRENT_CONTROL 卡缺 `alt_method_note` 与 `interpretation_limit` → 实测分布 **A3B0C4D6** ≠ manifest 声明 **A3B3C4D2**；G-04/G-08 subject 落 NOT_ASSESSED | A1c | `6299245` | **CLOSED**（`closed_at T+6.84h`） | ORCH-37 第4条：只补 `alt_method_note`、不补 `interpretation_limit`（B 类无该义务，`evidence.py:248-249` + L1172/L1293）；证据分布**主体级恰为 A3B3C4D2 / 行级 A3B4C4D2 双口径入册**（ORCH-37 第3条） |
| D-C2-01 | C-08 把单主体 design_card 缺失判为**整轮 BLOCK**，与 M29 L1346「NOT_ASSESSED 单列」冲突 | C2b | `10df9f8` | **CLOSED_AS_MISREPORTED** | ORCH-30 第1/3条：**M22 L907 C-08 严重度列只有「降级」、无 BLOCK**；三期实测唯一 `blocks_run=True` 为 **C-01 `WEIGHT_MISSING_WHATIF_RUN_ID`**。P2a 归因错误（把 `severity=BLOCK` 读成阻断整轮）→ **preflight 实现合规、PROD=0**，仅补 4 条测试锁死行为。教训 **L-05** |
| D-MODELS-01 | `PoolKey.evidence_class` required=True，但 M29 **L1334** Step2 排在 **L1338** Step3 之前 → Step2 无法构键 | MODELS-1 | `cc18a38` | **CLOSED** | ORCH-32 / ORCH-38 第1条：采「**Step2 松键 + Step7 严键**」；spine 6 红→4 红，余 4 红全归 fixtures |
| D-A1-03 | 主评价期 2026-Q3 缺 4 格，含 `S-008/v1/M_COMPLAINT_RATE`（HARD 红线）→ `redline.evaluate` 抛错，Step4-9 在主评价期整链断；违 M34 L1460 | A1c | `6299245` | **CLOSED** | ORCH-37 第1条**追认（主控自我纠错）**：ORCH-29 第5条前提被 `MISSING_CELLS` 刻意构造**证伪** → BLOCK 缺格载体由 `M_COMPLAINT_RATE` 迁至 **`M_SATISFY_SCORE`** 并同维对调 `missing_rule`，解 `dsm/redline.py:330` 死锁，**G-09 四分支不塌（g09 实测仍绿）**，G-03/G-15 零影响 |
| D-A1-04 | FROZEN 权重 `provenance=null` 缺 `whatif_run_id` → **C-01 恒 BLOCK**，主流程永久无法走 M29 L1322 的 PASS/WARN 分支 | A1c | `6299245` | **CLOSED**（主流程唯一真阻塞） | 补 provenance **七键**（`kind=AHP_ONLY` + `ahp` 段 + `whatif_run_id=WIF-SYNTH-2026-01` + 签认四件套），**全部合成待业务签认**（ORCH-37 第5条：不得伪造业务真值、不得填 K-01~K-20）；双来源印证 = ORCH-30 第3条 C2b 三期真跑 + E3 GAP-E3-05（T7 `provenance=null`）；spine step2 由红转绿走到 L1322 右支 |
| **D-A1-05** | design_card 为 **JSONL** 而 io_loaders 只认 CSV/Parquet 且 `''→None`，T4 永远加载不出（`DataLoadError MODEL_ROW_REJECTED`）；违 M29 L1330「io_loaders → 8 表」 | **A1d（在飞）** | — | **OPEN** | ORCH-38 第6条：触发条件已满足 → **必须执行**；ORCH-40 第8条 R1~R5 五项裁定；**ORCH-41 第1条两次修订**：①A1DPREP 净树快照实测**驳回**「8 张表 JSONL→CSV」（撞 `tests/*.py` 里 **41 处** `.jsonl` 直读，还要改 `dsm/fixtures_gen.py:548` 的「rows 只数 .jsonl」规则并同步 manifest 24 个字段），真正抛错点是 `io_loaders.py:270` 的 `DataLoadError`「design_cards row 11/12 refused by DesignCardRow: success_criteria」而**非** `:189-190` 的后缀检查 → **A1d 写集移除 `dsm/fixtures_gen.py` 与 `fixtures/**`**；②**驳回 `dsm/models.py:373`（`success_criteria: str → str \| None`）**，改采 **io_loaders 列级口径修正** |
| **D-A1-06** | G05 变体把正向指标 `M_AUM_MINOR` 留成 10000=目标值（达成率 1.0），与 golden_map hand 口径「+1 指标一律 1.900000」不自洽；按实际 fixture 手算 `CONTRIB=1.810000000000`、综合分 `1.507600000000`，而 golden_map 写 `1.900000` / `1.5346` | **E2b（在飞）** | — | **OPEN** | ORCH-37 的 R-14 边界：**A1c 只登记不代填**；ORCH-40 第9条列 E3b；**ORCH-41 第5条改判给 E2b**（golden_map 是 `tools/gen_golden.py` 的生成物，单写者）；手算依据 = `0.80*1.9+0.10*1.0+0.10*1.9`、`0.30*0.09=0.027`；原文 L1407/L1460/L1342 |
| **D-A1-07** | `evidence.classify` 按设计卡出桥 **13** 行，评价期事实只有 **12** 个 (strategy,version) pair（S-005/v1 无本期事实），pooling 侧证据结构口径为 **11**（实测 A3 B0 C3 D5），golden 记 4/12 → **13/12/11 三分母互不相等** | A1c（口径）+ EVID-1（实现）+ E3b（expects） | `6299245` / `897cad1` | **OPEN（状态字段滞后，见下注）** | ORCH-37 第6条裁 11（读法甲）；ORCH-37 第9条「13 vs 12 归实现侧」→ D-EVID-01 / EVID-1；**ORCH-41 第8条权威化为三口径 12/11/9（ERRATUM-11）**。A1c 三计数实测入册：出桥 **12** / 证据结构 **A3B3C4D2=12** / 占比双报 **A3B3C3D2=11** |
| D-A1-08 | G-05 要求追加极端策略后存量 norm/composite/grade **完全不变**（ORCH-28 对 M43 L941 的裁决），实测 S-011/v1 的 `M_ROI` norm `0.500000000000 → 0.541666666667`、composite `0.967705891652 → 0.968545891652` | ATT-1 | `dce1ac5` | **CLOSED** | ORCH-37 第8条 + ERRATUM-08：`IMPUTE_MEDIAN` 参考集取 `anchor_set` 优先、失效回退当期池 + `ANCHOR_SET_STALE`。**⚠️ g05 仍红**：ORCH-40 第3条实证根因 = `tests/test_golden_b.py:343 _chain` **未传 `anchor_set`**（ATT-1 用只读插件注入后 g05 转绿、**期望值一字未改**）→ 归 **E3b**；其余接线点 `golden_a:287/780` → E2b、`spine:166` → A1d、cli Step1 → P2-wire |
| D-D2-01 | LOO 无「影响力」量度：手算期望按「剔除后综合分跨度」排序（`M_REV_MINOR` 剔除后 S-009 `1.268600000000 → 1.148600000000`，跨度 `0.120000000000` 最大），实测按 **flip 数**排序 | LOO-1 | `858ebc8` | **CLOSED**（由 WONTFIX **改判待修**后修毕） | ORCH-33 第5条曾裁「本 RUN 不新增实现、交下一版本」；**ORCH-40 第7条经 ADJ-G07 只读取证后改判为实现缺项并派 LOO-1**；实测 `loo_impact_max = M_REV_MINOR 0.120000000000` 与手算逐位相符；g07 两条改前改后均 **2 passed**（纯增量未打破） |
| D-SPEC-G10 | 原文互斥：M31（约 L1412）单维清空 → BLOCK + `DIMENSION_EMPTIED`；M22 C-02 清空维度数 >=2 才 BLOCK。实测实现走 WARN + `WEIGHT_REALLOCATED` / `exit_code=0` | E3b（测试）+ P2（preflight 分支核验） | — | **CLOSED-BY-ORCH-35**（判为**测试构造错误**，非实现缺陷） | ORCH-35 第1/8条；修法归 E3b：期望改单维清空 → WARN / `blocks_run=False` / `exit_code=0` / 该维度 W 置 0 / 重归一后权重和 Decimal 精确 = 1（V-9）/ 披露码 `WEIGHT_REALLOCATED`，测试改名，**并必须新增「清空 >=2 维 → BLOCK + exit_code 2」测试（该分支当前零覆盖）**，断言总数须 >= 改前，`git diff -U0` 自证零弱化（R-14）。ORCH-41 第8条采纳的 g10 方案：断言类数 **6 → 11 严格增加** |
| **D-TOOLS-01** | `tools/normalize.py --check` 默认作用域含 **gitignored 的 `dsm_stage/`** → 报 17 of 524 违规，而 17/17 全在 `dsm_stage/{C2b,E3,SEAM-1}`；**受版本控制文件实测违规 0** | **P2-wire（在飞）** | — | **OPEN** | ORCH-36 第11条：编码门禁四要素 = **UTF-8 strict / 无 BOM / LF / 源码无 TAB**，作用域**收窄为 `git ls-files`**；20 文件缺末尾 LF 属历史遗留，只对本次变更文件断言。ORCH-41 第4条：⑦ 时间不够可移交 **P2-wire-B** |
| **D-G14-01** | `mix_quality_verdict` 未被 `reports.py` / `cli.py` 调用 → 「报告出现 `MIX_QUALITY_DEGRADED` 警示」在现接线下**永不成立**；**算出而不披露属 V-14 静默降级** | G14FIX（reports）+ P2-wire-A（cli） | `42d5346` | **OPEN（状态字段滞后：reports 侧已落地，见下注）** | ORCH-36 第4条「GAP-06 必须修，与第1~3条同批，否则修了也观测不到」；ORCH-40 第6条：**GAP-06 已接进 `reports.py:419`（`_section_6`，[L1063]⑥），cli 侧移交 P2-wire-A** |
| **D-G14-02** | `MIX_QUALITY_DEGRADED` 分子用 **C+D**（`LOW_EVIDENCE_CLASSES`）**零原文依据**，唯一明文 L1416 写「C 类占比」；分母用四类合计且**不剔 NOT_ASSESSED**，与同模块两列 `share_*` 不同源 | G14FIX | `42d5346` | **OPEN（状态字段滞后：口径已落地，g14 测试 expects 归 E3b，见下注）** | ORCH-36 第1/2条 + ORCH-37 第7条 + ERRATUM-11；实测 `PoolStats A3B3C3D2=11 / NA=2 / 已参评 9`，G-14 判据 `3/9 → 5/9` 触发；**g14 三条仍红但根因全在 A1c 后过期的手算 expects → E3b（未反填）** |
| D-EVID-01 | 出桥范围未按评价期过滤设计卡：`evidence.classify` 出桥 **13** 行，而主评价期 2026-Q3 只有 **12** 个 pair；多出的是 S-005/v1（RETIRED、`offline_date=2026-06-30`、本期以 v2 出值） | EVID-1 | `897cad1` | **CLOSED** | ORCH-37 第9条 / ORCH-40 第2条：判据等级 **derived:**（verbatim 侧 L1063②/⑥、L1003、L942、L1459）；**驳回「RETIRED+offline_date」判据**（T4 无该两列，L976 签名无 master 入参 → 本层不可实现，**未叠加凑数**）；出桥 13→12 实测印证 |
| **D-DOC-01** | `docs/deliverables/KNOWN-GAPS.md` 汇总节自称阻塞 **19** 条，但同文件逐条列举与逐行 grep（含 F-1/F-2 加粗「是」）均为 **24** 条，**自相矛盾** | **P3c（在飞，P3c-pre2）** | — | **OPEN**（severity low） | ORCH-39 第2条：**裁 24 为权威值**；文件更正归 **P3c 正式包写集，主控不代改**。**注**：ORCH-41 第1条 CODES-2 消除了 EVID-1 遗留的 PLACEHOLDER 披露码 → **P3c 须相应下调该计数**（24 里含此项） |
| **D-CLI-01** | `pyproject.toml` 无 `[project.scripts]` → SDD **L805/L836** 的 `dsm` 可执行入口未落成；唯一入口 `python -m dsm.cli`（8 条叶子命令与 **L1080-L1087** 逐条对应，公共 6 参数 + `--schemes`，退出码 0/2/3/4/5/6/7） | P3c（仅披露） | — | **ACCEPTED-DISCLOSED**（severity medium） | ORCH-39 第3条：**本 RUN 不补 console script**（避免写集扩散并与 P2-cli/P2-wire-A 抢 `pyproject.toml`）。另披露：`--help` 误报 `exit=5 INTERNAL` 但进程 rc=0 → 归 P2-cli 在飞范围，不另立缺陷 |
| D-SEN-01 | SDD **L748** 逐字要求「每指标的 LOO 影响力排名（主导指标清单）」、**L1409**「`loo_impact` 最大者为该指标」、**L1450**「LOO 影响力排序」，但 `_run_loo` 只累计等级翻转数并按 targets 顺序 append dominant，`models.py` **无任何承载字段** | LOO-1 | `858ebc8` | **CLOSED** | ORCH-40 第7条 / ORCH-41 第2条：**R-15 授权**新增 `SensitivityReport.loo_impact: tuple[tuple[str, Ratio], ...] = ()`，**追加在末尾**（6 个既有字段名/类型/相对顺序/语义零变化，同 MODELS-1 先例），字段名取 **L1409 verbatim**；ORCH-41 第3条硬约束：**新增字段必须带默认值**（否则打断 `tests/test_golden_a.py:118` 的 `NO_VETO_SENSITIVITY` 替身使 g01/g02 转红，而该文件在 LOO-1 禁写集内） |
| **D-MODELS-02** | `PoolStats` 缺「**已参评主体的四类分布**」载体；G14FIX 提出 3 个方案交主控裁 | 下一版本（本 RUN 不做） | — | **ACCEPTED-DISCLOSED** | ORCH-40 第6条：**本 RUN 不改 `models.py` 的 `PoolStats`**，维持 **reports 本地容器（ADJ-4）** 方案；ORCH-36 第14条：G14FIX 若发现 `PoolStats` 缺 flags 载体，**不得擅改 `dsm/models.py`（MODELS-1 独占），须上报主控** |

**⚠️ 状态字段滞后（本包只披露、无权修改 `ops/dag-state.json`）**：`D-G14-01` / `D-G14-02` 在 `defects` 数组中仍记 **OPEN**，但 ORCH-40 第6条已明确 G14FIX @ `42d5346` 收口且「ORCH-36 第1/2条与 ORCH-37 第6/7条**全部落地**」；`D-A1-07` 仍记 OPEN 但 ORCH-41 第8条已权威化三口径。三者的**真实残余项**分别是：cli 侧 GAP-06 出口（P2-wire-A）、g14 测试 expects 更新（E3b）、以及分母的规范定义签认（业务）。**本表按「裁决 + 实测」重述，不照抄滞后的状态字段。**

---

## §F PLACEHOLDER / K 台账（K-01 ~ K-29）

### F-1 · K-01 ~ K-20（SDD §5.1，原文 L1734-L1759 逐条实读）：**一律 PLACEHOLDER，模型侧不得拟定**

| K | 是什么（SDD 原文列） | 载体 | 类别 | 现用的工程默认 / 处置 | 谁签认 | 完成条件 |
|---|---|---|---|---|---|---|
| K-01 | 维度权重 W_d | weights yaml | **治理参数** | **PLACEHOLDER**（P-10 强制拦截，`EXIT_CONFIG=3`） | AHP 两两比较 + 一致性检验（CR < 0.1）；专家组 ≥ 5 人 | 结果签认并冻结 |
| K-02 | 维度内指标权重 w_j | weights yaml | **治理参数** | **PLACEHOLDER**；v1.1 起与熵权按 α 组合后冻结 | 同 K-01 | 同上 |
| K-03 | 各级 attainment_floor | grade_rules yaml | **治理参数** | **PLACEHOLDER** | 用历史策略回测标定：取达成率分布分位点（如 L1=P80、L2=P50、L3=P20），并与业务可接受的淘汰比例联立求解 | 标定结果签认 |
| K-04 | 红线阈值（投诉率、退订率、触达频次上限、合规违规数） | redlines yaml | **治理参数** | **PLACEHOLDER**，**不得由模型方拟定** | 引用行内既有制度阈值 / 监管要求 / 客诉管理办法 | 逐条引用制度文号并签认 |
| K-05 | attainment_cap | eval_config | 技术参数 | **PLACEHOLDER** | 取历史达成率 P99 与业务可解释上限的较大者，建议 1.5–2.0 区间内选定 | 选定并签认 |
| K-06 | min_coverage_for_absolute_track | eval_config | 技术参数 | **做成必填无默认、未猜数**（SP-1 裁决）；G-04 绝对轨封顶判据 | 依指标字典目标值覆盖率现状定；先测现状再定，避免大面积封顶 | 须行方签认，进 K 清单 |
| K-07 | min_sample_size_for_A / 显著性水平 / 最小可检测效应 | eval_config | **治理参数** | **PLACEHOLDER** | 由行方统计口径或既有 AB 平台规范提供 | 提供并签认 |
| K-08 | promotion_streak / demotion_immediate | grade_rules yaml | **治理参数** | **PLACEHOLDER** | 与评价周期联定；建议升级需 2 期、降级即时（审慎不对称） | 签认 |
| K-09 | 评价周期（MONTH / QUARTER） | eval_config | **治理参数** | **PLACEHOLDER**（本 RUN 只用合成 2026-Q1/Q2/Q3） | 须与策略迭代周期对齐；高频迭代建议 MONTH 或滚动窗口 | 写入配置并签认 |
| K-10 | missing_rate_warn / missing_rate_block | eval_config | 技术参数 | **PLACEHOLDER** | 先用历史数据跑出缺失率分布，取 P75 / P95 作为初始阈值 | 标定并签认 |
| K-11 | flip_rate 管理阈值（stable_max / review_max） | eval_config | **治理参数** | **PLACEHOLDER** | 首轮运行后按实际分布标定；建议初始 5% / 15% | 标定并签认 |
| K-12 | 锚定基准策略集成员 | anchor_set yaml | **治理参数** | **PLACEHOLDER**；本 RUN 用合成 `fixtures/input/anchor_set.jsonl`。ATT-1 后 `anchor_set` 成为 `IMPUTE_MEDIAN` 的**首选参考集**（失效回退当期池 + `ANCHOR_SET_STALE`）→ 未签认时该回退路径会常态触发并留痕 | 覆盖各 biz_domain 与各历史等级、运行满一个完整周期的策略 | 填齐 `anchor_set.yaml` 并**书面说明选取依据**；否则秩反转治理失效（WARN 并降级为仅当期归一化） |
| K-13 | 证据折扣表（仅当 evidence_mode = DISCOUNT） | eval_config | **治理参数** | **PLACEHOLDER**；**建议不启用** | 若启用须经审批并纳入敏感性分析 | 审批 + 敏感性分析 |
| K-14 | 维度指标细项与口径 | metric_dict csv | **治理参数** | **PLACEHOLDER**（= P0-5，**全模型的地基**） | 由行方按分册 A 三（四）要求补齐并签认 | `metric_dict` 全字段填齐且 `signoff_status = SIGNED`；否则模型能跑但**只能评合成指标、无法出真实结论**（RK-1） |
| K-15 | alpha_floor | weight_construction | **治理参数** | 代码默认 `Decimal = 0.5`（SDD **L563** 逐字标注 K-15），含义「业务判断至少占一半」；**不由数据标定** | 评价管理委员会 | 签认并写入配置 |
| K-16 | drift_budget | weight_construction | **治理参数** | 默认 `0.05`（SDD **L619**，标「待校准」） | 评价管理委员会 | 先用历史数据跑出各 α 的 drift 分布取 P25，再由委员会确认 |
| K-17 | boundary_budget | weight_construction | **治理参数** | 默认 `0.20`（SDD **L620**，标「待校准」） | 评价管理委员会 | 同 K-16 思路；含义「最多容忍多少比例的策略处于等级边界」 |
| K-18 | boundary_epsilon | weight_construction | 技术参数 | 默认 `0.02`（SDD **L620**） | 评价管理委员会 | 取 attainment_floor 量纲的 2%–5%，与指标精度匹配 |
| K-19 | min_dim_weight | weight_construction | **治理参数** | SDD **L564** 逐字：任一维度组合后权重下限（防被熵权清零）；建议 ≥ 0.05 | 评价管理委员会 | 签认 |
| K-20 | max_shift_from_ahp | weight_construction（H-5） | **治理参数** | 默认 `Decimal = 0.30`（SDD **L568**）；过松则熵权实质主导、过紧则组合无意义（RK-14） | 评价管理委员会 | 签认；报告须披露「实际 shift 值 / 上限」的比值 |

**SDD 原文纪律（L1759，逐字要旨）**：「K-15~K-20 全部是**治理参数而非统计参数** —— 它们表达的是「行方愿意让数据在多大程度上影响专家判断」，必须由人签认，**不得由标定程序自行选择**（P-13 机器守护）。α 本身由标定给出，但被 alpha_floor 与 H-5 双重约束。」
**为什么无据**：SDD **M39 L1794（G7）** 原文状态列 = 「**未完成（依赖行方，见 §5.9）**」；**L1792（G5）** = 「未完成 → 复核前全面禁用」；**RK-2** = 「权重、门槛、红线阈值全部 PLACEHOLDER → 不能出正式结论；P-10 强制拦截」。§5.9 的 7 项行方交付（L1947-L1953）逐条列出签认人与未交付后果。

### F-2 · K-21 ~ K-29（本 RUN 新增，全部由**主控单点分配**）

| K | 是什么 | 为什么无据 | 现用的工程默认 / 处置 | 谁签认 | 完成条件 |
|---|---|---|---|---|---|
| **K-21** | G-14 的**阈值** = `numeric.TOL`（1E-12） | 原文只给判据方向（C 类占比「上升」），**未给阈值数值**；改阈值即发明业务参数、违 R-12 | **保持 `numeric.TOL` 工程默认一字未改，仅标注为非业务签认值**（ORCH-36 第3条）；**5 条待签认项见 `dsm_stage/G14FIX/K-21-PROPOSAL.md`** | 业务 / 评价管理委员会 | 5 条提案逐条签认后写入配置 |
| **K-22** | `loo_dominant_flip_rate` **配置键在契约原文无出处** | `dsm/sensitivity.py` 与 `tests/test_golden_b.py` **各自营造**该键名 | 保持「**必填注入、缺则 `MissingConfigError`、不给默认值**」（ORCH-40 第7条） | 业务 | 签认阈值并写入契约 |
| **K-23** | G14FIX 实测：当前 **NOT_ASSESSED 中 C 类 = 0**，使 G-14 分子（全体口径）与分母（已参评口径）的 population **巧合一致** | A1CPREP §6-B.4 里 **S-008 就是「C 类且 NOT_ASSESSED」** → 这是**数据巧合，非契约保证** | **P3a 须披露**（本表即披露）；不改实现（ORCH-40 第6条） | 业务 / 设计方 | 契约层明确两口径 population 关系，或补一个使二者不等的 variant |
| **K-24** | `loo_impact` **影响力度量算式属 `derived:`** | 原文 **L748 / L1409 / L1450** 只要求「影响力排名」这个**产出物**，**未逐字给算式**；全文「跨度 / 极差 / span」**0 次命中** | 现实现 = `max over 参评策略 of |composite_LOO − composite_base|`，**L954 维度内重归一、q12、不经 float**（ORCH-40 第7条裁定） | 业务 | 签认算式或给出原文口径 |
| **K-25** | `SensitivityReport.loo_impact` **字段名**取自 **L1409 verbatim**，但 **ORCH-22 裁决25 的契约表里没有这一条** | 契约表缺录 | 接线**沿用 `loo_impact`**；契约表补录由主控在后续 ORCH 处理（ORCH-41 第7条） | 主控 / 设计方 | 契约表补录该字段 |
| **K-26** | `tests/test_golden_b.py` 的 **g07 docstring** 里 `M_RETENTION_RATE 0.098000000000` 经 A1c 重冻**已失效**，实测 `0.012950000000` | docstring 是注释而非断言，A1c 重冻 fixtures 后未同步 | 归 **E3b，只改 docstring，禁改 assert**（ORCH-41 第7/8条） | E3b（本 RUN）+ 业务（指标签认面） | E3b 改完须重跑确认仍绿 |
| **K-27** | `loo_impact` **精确并列时双方都列出、不提名唯一榜首**；契约**未给 tie-break 规则** | 原文无 tie-break 规定；ORCH-40 第7条明令「并列报 blocked，**禁自造 tie-break**」 | 保持「**并列都列出**」（LOO-1 已落一条专门测试） | 业务 | 签认是否需要 tie-break 及其规则 |
| **K-28** | 现 fixtures 下 **anchor-first 与 pool-only 的中位数恰好相等**（均 `0.101500000000`）→ **g09 对 ORCH-37 第8条 / ERRATUM-08 零守护力（vacuous）** | 数据巧合使断言恒真，无法证伪参考集口径 | **本 RUN 不加 variant**（会再次解冻 A1c 刚重新冻结的 fixtures 并牵动全量手算，**余量不允许**）；交 P3a 披露（ORCH-41 第6条）。同案：E2PREP 的 NEED-FIXTURES 其余各条凡需改 `fixtures/` 下**非 golden_map** 文件的，**一律不做** | 业务 / 下一版本 | 新增使二者不等的 variant 并重算全量手算 expects |
| **K-29** | **LOO targets 含未签认指标 `M_REPEAT_USE_COUNT`**，排名实为 **15 条**而 g07 docstring 写 **14 条** | 指标签认面（K-14）未闭合 + docstring 陈旧 | 归 **E3b 只改 docstring**；**指标签认面交 P3a 披露**（本表即披露） | E3b（docstring）+ 业务（K-14） | docstring 改毕 + `M_REPEAT_USE_COUNT` 进 K-14 签认清单 |

### F-3 · 🔴 K 号撞号纠正（必须写明）

**LOO-1 自报的 K-23 已改记 K-29。** 依据 **ORCH-41 第7条**逐字：「LOO-1 上报的 K-23（LOO targets 含未签认指标 `M_REPEAT_USE_COUNT`，排名 15 条 vs docstring 14 条）与**主控在 ORCH-40 第6条已登记的 K-23**（G14FIX 的『NA 中 C 类 = 0 使两口径 population 巧合一致』）**撞号** → LOO-1 的改记 **K-29**；其余 K-24 / K-25 / K-26 / K-27 照单入册。→ 记 **L-12**（K 号必须由主控单点分配，子包不得自行编号）。」
**纠正措施（L-12）**：后续派工卡一律附「当前最大 K 号 = N，你新报的项从 N+1 起**暂记为 `K-LOCAL-<包号>-<序号>`**，由主控统一入册」。

### F-4 · 非 K 类的 PLACEHOLDER（同样须刷新）

| 位置 | 内容 | 归属 |
|---|---|---|
| 本文件 §A / §B | 全量 pytest `failed / passed / collected`、11 红逐条拆分 | `PLACEHOLDER-TO-REFRESH(P2-wire-B)` |
| 本文件 §H | 最终 `reproducibility_hash` | `PLACEHOLDER-TO-REFRESH(P3b)` |
| `dsm/cli.py:250` | `cel_contract_version` 仍 PLACEHOLDER | P2-wire-A ⑤（ORCH-40 第4条） |
| `dsm/cli.py:252` | `reproducibility_hash` 仍 PLACEHOLDER | P2-wire-A ⑤ |
| `dsm/reason_codes.py` | `SPEARMAN_ZERO_VARIANCE` / `APPROXIMATE_ATTRIBUTION` 的 severity = PLACEHOLDER（**维持暂定 WARN，不得升格 BLOCK**） | ORCH-34 第2条 / ORCH-36 第10条；P3a 列入待业务签认清单 |
| `ops/dag-state.json` | `pytest_baseline.after_MODELS1.split` = `PLACEHOLDER`（11 红逐条拆分待 P2-wire-B 权威重测登记，**避免主控凭记忆填数，符合 R-12**） | P2-wire-B（ORCH-39 第4条） |
| A1c 遗留 | `PLACEHOLDER-A1c-01`：新增红第⑩条 `test_l0b_whatif_step_unlocks_when_landed` **归因未闭环** | 交 **A1d** 闭环（ORCH-40 第5条） |
| ratchet | 白名单 **32 → 28** 收缩未做（必须在 A1c 之后；执行时须重新实测实际碰撞对数并据此设定新常量，保留「只许缩短」方向） | P2-wire-B（ORCH-34 第3条 / ORCH-39 第6.4条） |
| P2-cli 上报 | ⑤ `ahp_matrices` 形状二义维持 **P-7 OPEN**（按实现接、已登记）；① `EntropyInsufficientSample` 无独立退出码槽维持 **P-2 OPEN** | ORCH-40 第4条 |

---

## §G 写集偏离与纪律追认

| # | 偏离事实 | 正当理由 | 裁决出处 | 状态 |
|---|---|---|---|---|
| **①** | **MODELS-1 改了派工写集外的 `tests/test_models_output.py` 的 3 行登记数据表**（`FRAME_MODELS` / `SYN_PAYLOADS` 的 `NormalizedFrame` 条目、`SUB_MODELS[PoolKey]` 的 `req→null`），**零 assert 行改动** | ORCH-32 授权新增 frame 级列后，该文件的**模型花名册与 nullability 分区表必须同步**，否则会产生 **3 条归属本包的假红**（`test_d01[NormalizedFrame]` / `test_e04[NormalizedFrame]` / `test_j02[PoolKey]`）；且**当时无其他 lane 在飞该文件**，未违反单写者纪律 | **ORCH-38 第2条追认**（要求 P3a 在披露节记明此写集偏离及其正当理由 → 本行即履行） | 已追认 |
| **②** | **`tests/test_normalize.py:244` 由「整体相等」改 `dropped.rows == ()`，并新增 5 条留痕断言** | 「仅允许新增断言」与 ORCH-32 第2条**在数学上不可同时满足**：原断言 `dropped == NormalizedFrame(rows=())` 是**整体相等**比较，而新增的 `excluded` 列**必然非空** → 整体相等必失败。改后**原业务主张（零行、不编值）的实质逐字保留**，净强度增加 | **ORCH-38 第3条：裁定这「不是弱化」，而是「断言对象随契约扩展而精确化」，属 R-14 允许的情形**；并要求 **P3a 把该处置作为先例记录进 V-ACCEPTANCE-EVIDENCE，并附 `git diff -U0` 证据** | 已追认（**先例入册**）。⚠️ `git diff -U0` 证据的**取卷动作本包未执行**（`cc18a38` 已在历史中，且本包禁跑写盘命令）→ `PLACEHOLDER-TO-REFRESH(P2-wire-B / 附 cc18a38 的 git diff -U0 卷宗)` |
| **③** | **LOO-1 的 `tests/test_models_output.py` +4 行登记数据表** | 与 ① 同源同理：R-15 授权新增 `SensitivityReport.loo_impact` 后，模型花名册须同步，否则产生归属本包的假红。LOO-1 实测回归 **`test_models_output + test_architecture` 合计 642 passed（635 → 642，零红）** → 证明是**纯增量登记、未打破任何既有断言** | ORCH-41 第2条收口 + ORCH-38 第2条先例；**ORCH-41 第3条通用化硬约束**：「后续任何对 `models.py` 的 R-15 授权新增，**一律要求带默认值**，除非同时授权改所有构造点」 | 已追认（先例通用化） |
| **④** | **P2 拆为 P2-cli + P2-wire，P2-wire 再拆 A/B** | 一拆（ORCH-36 第6条）：P2 的 delta 中**有 6 项不依赖 fixtures**，可先行；余项（cli #4/#6、接线、`preflight:209-211` 核验、ratchet 32→28、编码门禁收窄、全量 0 failed 判定、哈希重登记）必须在 A1c + MODELS-1 + G14FIX 之后 → 原 P2 标 `superseded_by_split`。二拆（ORCH-39 第6.4条）：**余量 3.68h 而原串行关键路径估算 >4.3h 必超线**，而 **S7 方法层与 S8 权重链（档 2）不得砍，故只压编排不砍范围** → **P2-wire-A**（接线，不依赖 expects，前置 P2-cli+ATT-1+EVID-1+G14FIX）与 **P2-wire-B**（ratchet 32→28 + 全量 0 failed 判定 + 哈希重登记，前置 A+E2b+E3b+ADJ-G07） | ORCH-36 第6条 / ORCH-39 第6.4条 | 已落地（P2-cli `2ee10ed`+`da88ff7` 收口；P2-wire-A **在飞**；P2-wire-B 待派） |
| **⑤** | **ORCH-41 第5条把 golden_map 的 hand 修正从 E3b 改判给 E2b（撤销 A1c ADR §11 的分派）** | `fixtures/golden/golden_map.json` 是 **`tools/gen_golden.py` 的生成物**，golden_a 与 golden_b 的 `hand` / `probes[].e` **都在其中 → 二者不可分写**（单写者冲突）。裁定 **E2b =「golden 载体包」独占 `tools/gen_golden.py` + `fixtures/golden/golden_map.json` + `tests/test_golden_a.py`**（含 golden_b 侧的 hand 校正 = D-A1-06 的 `dim_CONTRIB 1.900000 → 1.810000000000` 与综合分 `1.5346 → 1.507600000000`，以及证据侧 `B0D5 → B3D2` / `NOT_ASSESSED 5 → 2` / 池集合 shares `SMALL_POOL`）；**E3b =「golden_b 断言包」只写 `tests/test_golden_b.py`**，需要 golden_map 配合的一律写 `dsm_stage/E3b/NEED-GOLDEN-MAP.md` 上报、**禁自改**。两包并行（写集不相交） | **ORCH-41 第5条**（据此**撤销 A1c ADR §11** 把 golden_map hand 修正「交 E3b」的分派；ORCH-37 第5条的落地归属更正为 E2b）。同源的更早裁定：**ORCH-40 第5条**「载体修正归 E2b 改 `tools/gen_golden.py`，**严禁手改 `golden_map.json`**（生成物，手改会被下次重生成覆盖并破坏冻结可复现性）」，根因 = `tools/gen_golden.py:179-187` 把 G-09 载体 `('S-008','M_COMPLAINT_RATE')` 与 `hand.branch_map` 写成**硬编码字面量** | 已裁定；E2b / E3b **在飞** |
| **⑥（补）** | **A1d 写集两次收窄**：ORCH-38 第7条（`dsm/io_loaders.py:274-279` 的 `data/<period>/` 目录布局迁移**不在范围**）→ ORCH-40 第8条 R3 维持 → **ORCH-41 第1条再移除 `dsm/fixtures_gen.py` 与 `fixtures/**`，并驳回改 `dsm/models.py:373`** | 最小修法优先 + 单写者纪律（`models.py` 是 LOO-1 独占写集）+ 防止串味（`test_golden_a.py:885` 既有绿断言 `assert card.success_criteria == ''`）+ 严禁全局改 `NULL_LITERALS` 语义（会连带 8 张表）。**同时确认 D-A1-09 不需要**（`_stage` `spine:120-131` 已在 `tmp_path` 下造 `data/<period>/` + `config/`，`io_loaders.py:274-279/314-320/301` 早已实现）→ **并撤销 E3PREP NEED-FIXTURES 第⑧条的风险前提** | ORCH-38 第7条 / ORCH-40 第8条 R1~R5 / ORCH-41 第1条 | 已裁定；A1d **在飞** |
| **⑦（补）** | **本包（P3a-pre2）自身的写集纪律** | 写集**仅** `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` 一个文件；**未跑** pytest、**未跑** `fixtures gen`、**未写** `dsm/** tests/** fixtures/** tools/** config/** ops/dag-state.json README.md docs/adr/** 及 `docs/deliverables/` 下其它文件；只显式 `git add docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`，**禁 `git add -A`**、禁 force/rebase/reset/amend/切分支、**禁 push、禁 tag**；未 spawn 子 agent、未调用 `request_user_input` | R-13 / R-12 / L-06 / 本包派工卡 §0-§1 | 本包自证（见提交后回读） |

---

## §H 复现哈希台账

| seq | 哈希 | commit | 变化原因 | 是否预声明 | 两跑是否相等 |
|---|---|---|---|---|---|
| 0（初值） | `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` | `8cd222c`（SP-1 / P2a） | 首次登记（period `2026-Q2`，断言 = `tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs`） | — | 是（P2a 两连跑） |
| 1 | `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7` | `8f2eca3`（SEAM-1） | **锚定参考尺改为不按池裁剪**，normalize 输出变化 | **无**（ORCH-30 只预声明了 A1c，**属遗漏，已由 ORCH-33 第3条纠正**） | **是**（SEAM-1 与 P3a-prep **双向独立实测一致**，2026-Q2，两连跑相等，exit 0/0） |
| 2 | `4de4b8cb…`（**未变**） | `cc18a38`（MODELS-1） | 预期原因 = `NormalizedFrame` 增 frame 级披露通道 + `PoolKey.evidence_class` 可选；**实测未发生变化** | **预声明过**（ORCH-32 第2/4条 + ORCH-30/31/33），但 **`occurred = false`** | **是**（MODELS-1 @ `cc18a38` 两连跑精确相等）。**ORCH-38 第4条更正**：`dsm/audit.py:242` 只哈希 `score_card` / `grade_ledger` / `weight_version_id`，MODELS-1 是**纯增披露面**、被哈希数值一位未变 → **台账以实测为准（L-08）** |
| 3 | `e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d` | `6299245`（A1c） | **A1c fixtures 受控解冻**（ORCH-29 第5条 / ORCH-37 十项裁决） | **是**（ORCH-30 第5条：受控解冻后该哈希**必然改变，属预期非回归**） | **是**（A1c 提交说明逐字：「连跑两次精确相等」） |
| 4 | **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`（当前值）** | `42d5346`（G14FIX） | **`reject_reason` 新增 `PRIMARY_POOL_REJECTED_GRADE`，经 `grade_ledger.l1_gate_reasons` 进入哈希面** | **否**（`pre_declared = false`，**属遗漏**，同 seq1 的 ORCH-33 第3条纠正口径） | **是**（`two_runs_equal = true`） |
| 5 | `PLACEHOLDER-TO-REFRESH(P3b)` | `PLACEHOLDER` | **预期**：A1d 的 `tests/test_integration_spine.py:166` `anchor_set` 接线（**ATT-1 已预告必变**）+ LOO-1 + P2-wire-A。**注**：LOO-1 已实测「`reproducibility_hash` **不变**（`audit.py:242` 不消费 `SensitivityReport`），但 `output_fingerprints` 将因 reports 接线而变」（ORCH-41 第2条）→ 再次印证 L-08「预声明 ≠ 必然失效」，**终值只记实测** | **是**（ORCH-40 第10条 seq5） | `PLACEHOLDER-TO-REFRESH(P3b)` |
| **终值** | **`PLACEHOLDER-TO-REFRESH(P3b)`** | 最终 HEAD | — | — | 必须是**同 seed 两连跑精确自等** |

**🔴 P3b 的判据（逐字照录，不得改写）**：「**最终 HEAD 上全新 clone + `unshare -rn` 真断网 + 同 seed 两连跑精确自等，不是与任何旧值相等。**」（`reproducibility_evidence.p3b_criterion`；ORCH-40 第10条同文；ORCH-33 第3条更早表述为「P3b 的最终判据是『A1c 与 MODELS-1 均落地后重测的哈希，两连跑精确相等』，**不是与 `8083efc9` 相等**」）

**哈希载体与输入（转录 `reproducibility_evidence.harness`）**：哈希源 = **`dsm/audit.py:242`**（载荷 231 / schema 43 / 规范化 113 行），载体 `dsm/models.py:1227`；**当前真值只由 `tests/test_integration_spine.py:146 _run_chain`（:480）以测试内合成 GOVERNANCE 驱动九步真跑产出，非 CLI 真实运行**（`dsm/cli.py:199` 仍 PLACEHOLDER，`config/` 0 文件）。输入 = seed `20260101` / period `2026-Q2` / `fixtures/input` + `golden` / 冻结权重版本 id；**`run_at` 与 `run_id` 注入但不入哈希**。
**纪律（ORCH-36 第13条）**：P2-wire 重登记 A1c 后重测值，并**保留旧值 `8083efc9` 与 `4de4b8cb` 供 P3a 披露，严禁修回旧值**。
**⚠️ 台账内部不一致（本包只披露、无权修改）**：`reproducibility_evidence.current_hash_asof` 仍写 **`358b4ea`**，而 `current_hash_commit` 写 **`42d5346`**、`current_hash` = `e5923465…` → 二者矛盾，`current_hash_asof` 疑为漏更新。另 `invalidation_log` 中存在**两条 `seq: 3`**（一条 `at: pending` 的占位、一条 A1c 的实测记录），且 seq2 那条仍写 `at: "pending"` 而 `occurred: false` → 序号与状态字段需主控清理。

---

## §I 教训台账（L-01 ~ L-12）

| ID | 一句话教训 | 纠正措施 |
|---|---|---|
| **L-01** | 并行期跑全量 pytest 被未跟踪半成品（`tests/test_methods_ahp.py`，D1 在飞）的 collection error 中断，整个 suite 拿不到统计行 | 同步点跑全量**必须带 `--continue-on-collection-errors`**，并在统计行之外**单独记录「收集错误文件清单」**；收集错误若来自未跟踪半成品属预期、不计入 failed 基线。基线重述：211 failed（`test_config_semantic` 108 / `test_config_weight_version` 96 / `test_config_properties` 7）+ D-C1-01 = 212 |
| **L-02** | 给 E5 的派工简报写「基线 10 failed」，但 E5 实测时 C1b/ORCH-25 已落地为 1 failed → lane 误判基线不符（GAP-E5-08） | **派工简报中的 pytest 基线数字必须标注截至哪个 commit**；主控在每次提交后同步刷新基线口径 |
| **L-03** | E5 引 M00 L278/L300 支持「L0a→L0a 合法」，但**未同时引 L276/L286/L294**，结论被原文推翻 | **架构争议上报必须附原文逐字引文**；主控裁决前须**四行齐读**（定义行 + 方向表 + INV 表 + 拆层动机） |
| **L-04** | A3 实测 161min（预算 90）、A4 110（75）、P2a 145（75）—— 共同原因：ORCH 裁决在**飞行中途**下达改变写集语义 + 并行期每包都跑全量回归 + 集成包需等上游落地反复重跑 | ①飞行中途下达的裁决**必须同时重设该包墙钟预算**，不得按原预算判超时；②lane 侧只跑「本包 + 受影响邻包」，**全量回归只在同步点由主控跑一次**；③集成类包预算按上游落地重跑次数上浮 |
| **L-05** | 主控 ORCH-29 第3条自行补出「C-08 表级缺失 → 整轮 BLOCK」，而 **M22 L907 原文 C-08 严重度列只有「降级」**；P2a 同时把 `severity=BLOCK` 误读为阻断整轮 —— **两者同源：都把「严重度标签」当成「阻断行为」** | ①裁决涉及新增阻断/降级行为时，**必须先取该检查项在 M22/M28 的严重度列与动作列逐字原文，原文未写 BLOCK 一律不得新增 BLOCK**；②**`severity` 与 `blocks_run` 分离**：severity 是签认属性（禁改写），阻断只看 `blocks_run`；③lane 依「原文优先」推翻主控裁决**属正确行为**，主控须公开纠错并记教训，**不得压回** |
| **L-06** | 主控写盘链路必须显式 **UTF-8 无 BOM**：PowerShell `Set-Content -Encoding ASCII` 会把 here-string 里的中文**静默转成问号**，而 `-Encoding UTF8` 又会**加 BOM** 使 bash 首行报 command not found | 正确做法 = `[IO.File]::WriteAllText(path, text, (New-Object System.Text.UTF8Encoding($false)))`。**事故**：`dbe96aa` 的提交信息与 ORCH-31 原文被转写为问号，已由 `0b0c8f3` 重写 ORCH-31 文本，`dbe96aa` **不做 amend**（避免与在飞 lane 抢 `index.lock` 及改写历史）。**规则**：此后所有主控脚本一律 UTF-8 无 BOM 落盘；**任何含中文的提交信息，提交后必须用 `git log -1 --pretty=%B` 回读自证可读**。（本包遵此执行，见 §G-⑦ 与提交后回读） |
| **L-07** | pytest 取数命令固定为 **`-ra --tb=no --continue-on-collection-errors`**：`pyproject.toml` 的 `addopts` 已含 `-q`，命令行再叠 `-q` 会变 `-qq`，**吞掉汇总行与 short summary**，看起来像 pytest 崩溃（P2PREP 踩中 2 次） | 任何 lane 与主控取六门禁数字**一律用该固定命令**；需要明细时用 `-ra`，**不得用 `-q`/`-qq`** |
| **L-08** | **预声明「可能失效」不等于「必然失效」** | 凡涉及 `reproducibility_hash` 的裁决，落地后**必须由执行包实测新旧值并上报，台账只记实测值**；主控不得把预声明当既成事实写入交付文档。**事故**：ORCH-30/31/33 预声明 MODELS-1 会造成第三次哈希失效，**实测未发生**（`audit.py:242` 只哈希 `score_card`/`grade_ledger`/`weight_version_id`，纯增披露面不影响） |
| **L-09** | 提交信息内的**代码行号**必须在提交后回读自证；R-13 禁 amend | **行号应以包内 NOTES 的实测对照表为权威，交付文档不得引用提交信息里的估值行号**。**事故**：`cc18a38` 的 message 行号为提交前估值（`models.py:773` / `normalize.py:311` / `pooling.py:227`），实测值见 `dsm_stage/MODELS-1/NOTES-MODELS-1.md §七`（`models.py:762` / `normalize.py:342` / `pooling.py:236`）。**本文件遵此：凡引用 MODELS-1 行号一律指向该对照表** |
| **L-10** | 高并发（6 槽满载）下 **HEAD 在单个包施工期间变动 3-5 次**，每包都必须额外做 base-vs-mine 对照跑才能干净归因 → 预算普遍超支 **1.5-2.2 倍**（EVID-1 52/25、P2-cli 72/45、A1c 72/60、G14FIX 78/35） | 后续派工卡一律在预算内**预置「净树重测 + 对照归因」时间（约 +40%）**，并把**写集切得更窄**以减少对照面；**核可不返工**（同 ORCH-38 第8条） |
| **L-11** | **派工卡里引用的测试文件名必须先实测存在，不得凭记忆**：LOO-1 的任务书写的 `tests/test_methods_sensitivity*.py` 在仓库内**无此名**，实际文件是 `tests/test_sensitivity.py` | 子包自行点名纠正未造成损失，但浪费一轮检索。**主控派工前对写集里每个文件名跑一次 `ls`/`grep` 实测** |
| **L-12** | **K 号（PLACEHOLDER 待签认项）必须由主控单点分配**：LOO-1 自行上报的 **K-23** 与主控在 **ORCH-40 第6条**已登记的 K-23 **撞号**，已改记 **K-29** | 后续派工卡一律附「**当前最大 K 号 = N，你新报的项从 N+1 起暂记为 `K-LOCAL-<包号>-<序号>`，由主控统一入册**」（详见 §F-3） |

---

## §J 边界声明（诚实性红线 · 原文照录不得软化）

1. **K-01 ~ K-21 一律 PLACEHOLDER。** 所有「digest/SDD 未给业务数值」的缺口（K-06 `min_coverage_for_absolute_track`、grade_rule 门槛、`promotion_streak`、evidence 四级判据界限等）**一律保持必填无默认或 PLACEHOLDER、不猜数**（ADJ-2 / R-12）。
2. **门禁 G5 / G7 未通过，本 RUN 全部结论只在「用合成数据跑通机制」口径下成立。** SDD **M39 L1792（G5）= 「未完成 → 复核前全面禁用」**、**L1794（G7）= 「未完成（依赖行方，见 §5.9）」**（G7 逐字要求「权重、门槛、红线阈值、评价周期、各指标目标值、α 及 K-15~K-20 **全部脱离 PLACEHOLDER**」）。因此**不得输出任何可用于真实资源配置的分数或等级**（**M39 L1797**）；该声明**必须进报告首屏**（守护 = `tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen`，初版实测 PASS）。
3. **`config/` 实测 0 文件，真实运行被 `EXIT_CONFIG=3` 拒绝 —— 这是设计如此，非 bug。** 出处：`reproducibility_evidence.harness.hash_source` 逐字「当前真值只由 `tests/test_integration_spine.py:146 _run_chain`（:480）以测试内合成 GOVERNANCE 驱动九步真跑产出，**非 CLI 真实运行**（`dsm/cli.py:199` 仍 PLACEHOLDER，**`config/` 0 文件**）」；`KNOWN-GAPS.md` F-2 行逐字「未完成且**无载体**：`config/` 0 文件（实测 `find …`）」；初版 V-5 专项 `test_g08_an_empty_config_dir_reports_everything_missing`（**空 config 目录必须一次报出全部缺失**）PASS 即为该行为的守护。**P-10 强制拦截**（RK-2）是契约要求，不是缺陷。
4. **`pyproject.toml` 无 `[project.scripts]` → 唯一入口 `python -m dsm.cli`（D-CLI-01）。** SDD **L805/L836** 的 `dsm` 可执行入口**未落成**；8 条叶子命令与 **L1080-L1087** 逐条对应，公共 6 参数 + `--schemes`，退出码 **0/2/3/4/5/6/7**。**本 RUN 不补 console script**（ORCH-39 第3条：避免写集扩散并与 P2-cli/P2-wire-A 抢 `pyproject.toml`）。另披露：`--help` 误报 `exit=5 INTERNAL` 但进程 rc=0（归 P2-cli 在飞范围）。
5. **无 console script、无前端界面。** 本 RUN 交付物 = Python 包 + CLI（`python -m dsm.cli`）+ 冻结 fixtures + 测试套件 + 文档；**不含任何 GUI / Web 前端 / 服务化部署件**。
6. **本 RUN 未接入真实用户 / 行内授权 / 生产对账 / 因果增量。** 具体：①**无真实用户或真实策略数据** —— 全部输入为合成 fixtures（`fixtures/input/*.jsonl`，`metric_fact` 896 行、period 2026-Q1/Q2/Q3），SDD §5.9 的 7 项行方交付（**L1947-L1953**）**一项未到**；②**无行内授权** —— K-01~K-21 无一人签认，`provenance` 七键为 A1c 合成（`whatif_run_id=WIF-SYNTH-2026-01`，`kind=AHP_ONLY`，**全部标注待业务签认**）；③**无生产对账** —— 未与任何行内既有系统做过数值对账，`reproducibility_hash` 的第二人复跑（V-3）尚未执行；④**无因果增量** —— `cel.enabled = false`（SDD **L1898** 单开关默认关闭），**CEL-0 预留字段一律不参与任何判定**，若非空则抛 `CelDisabledDataPresentError`（**RK-15**）；V-20 的机制侧已实测，但**任何真实因果增量值均未被接入或验证**。
7. **未 push、未 tag。** 本地领先 `origin/main`；`tags = 0`。**tag 须待 P2 全量转绿且由主控统一执行**（R-13 / ORCH-39 第1条 / `2313857` 提交说明逐字「不打 tag、不 push」）。
8. **邻仓 `/home/szf/dev/CampaignLab` 全程只读、未触碰。** 本包实测四项一致：**`m0-framework` / `0cccb76` / porcelain `0` / `rev-list --count HEAD` = `154`**。
9. **契约文件只读、指纹恒定。** `sha256[:12] = 708679e9a83d`、行数 **2003**，与 `dag-state.sdd_fingerprint` 一致（本包开工第一步即核验）。
10. **本文件的所有 ⏳ / ❌ 与 `PLACEHOLDER-TO-REFRESH` 均为有意保留，不是遗漏。** 在 **A1d + E2b + E3b + P2-wire-A → P2-wire-B** 收口前，**任何把本文件的 ⏳ 改判为 ✅ 的行为都属违 R-12**。定稿动作只剩两件：①P2-wire-B 刷新全量六门禁数字与 11 红拆分；②P3b 在最终 HEAD 上跑 `tools/repro_offline.sh`（L3-strong）登记终值哈希。

---

### 附 · 本文件的 `PLACEHOLDER-TO-REFRESH` 索引（共 12 处）

| # | 位置 | 缺什么 | 归属 |
|---|---|---|---|
| 1 | §A V-1 | 全量 `failed/passed/collected` + 11 红逐条拆分终值 | **P2-wire-B** |
| 2 | §A V-2 | hypothesis **500 例**档实跑结果 | **P2-wire-B** |
| 3 | §A V-3 | 第二人全新 clone + 真断网 + 同 seed 复跑 | **P3b** |
| 4 | §A V-4 | A1c 重冻后的 3 层回溯重抽查 | **P2-wire-B** |
| 5 | §A V-7 | `anchor_set` 三处接线（`golden_b:343` / `golden_a:287,780` / `spine:166`）后的 g05 终态 | **E3b + E2b + A1d → P2-wire-B** |
| 6 | §A V-8 | `reports.py` 的 `excluded` ③ 与 `loo_impact` ⑧ 出口落地后的报告面复测 | **P2-wire-A → P2-wire-B** |
| 7 | §A V-10 | 最终 HEAD 上的 L3-strong 断网完整跑通 | **P3b** |
| 8 | §A V-15 | 正向 provenance 七键的终值抽查（逐键标「合成待签认」） | **P2-wire-B** |
| 9 | §A V-20 | 括注「G-01~G-15 全过」（依赖 V-1） | **P2-wire-B** |
| 10 | §B-2 | M28 **26 行 × 六列**逐条遍历断言 + 注册表规模重测 + ratchet 32→28 | **P2-wire-B** |
| 11 | §G-② | `cc18a38` 的 `git diff -U0` 卷宗（ORCH-38 第3条要求附证据） | **P2-wire-B** |
| 12 | §H seq5 / 终值 | 最终 `reproducibility_hash` + 两跑自等证明 | **P3b** |

**本文件状态：定稿前移完成，只差上述 12 处最终数字刷新。**

---

## §K 施工期 HEAD 漂移追记（写入时刻实测 HEAD `0d8afeb`；本节明示 §A/§B 中前提已变的条目）

**本节只转录提交主题与 `git status` 实测，不含任何本包未亲自跑出的数字。** 本包全程未跑 pytest（并发禁跑 + 数字非终值），故以下条目**一律不改判 ✅**，只把「归谁 / 是否已落地」刷新为实测事实，最终判定仍留 `PLACEHOLDER-TO-REFRESH(P2-wire-B)`。

| 提交 | 主题（逐字转录 `git log --format=%s`） | 对本文件的影响 |
|---|---|---|
| `53ed80c` | **P2-wire-A: 披露/判据接线（③EVID-1 范围过滤端到端 + ⑧LOO 影响力排名出口 + ②G14 cli seam + ①第3条 + ④message 更正 + ⑤reproducibility_hash 真源接线）** | 🔴 **§B-2「仍未闭环」第 2 条的前提已变**：ORCH-41 第4条列为「必做」的 **③（`excluded` 报告出口）** 与 **⑧（`loo_impact` 排名出口）** 按提交主题**已接线**，**②（G14 cli seam）**、**④（ERRATUM-07 的 message 更正）**、**⑤（`dsm/cli.py:250/252` 两处 PLACEHOLDER）** 亦在其列。→ **§A V-8 与 V-14 的「归 P2-wire-A 施工中」应改读为「已提交，待 P2-wire-B 全量复测确认」**。**但本包未复跑，故 V-14 仍不得声称端到端闭环**：§B-2 的**第 1 条缺口（M28 26 行 × 六列逐条遍历断言）与第 3 条（注册表规模重测 + ratchet 32→28）在本包可见范围内仍无落地证据**，二者均归 **P2-wire-B**。 |
| `f4aaa6b` | **ORCH-40+ORCH-41: 六包收口+g07裁实现缺项派LOO-1+A1d R1~R5五项裁定 / A1DPREP驳回models放宽改走io_loaders列级口径+LOO-1新字段可选性+P2-wire-A⑧升必做+golden_map单写者切分E2b/E3…** | 主控台账提交（`ops/dag-state.json` + ADR）。本文件 §C / §D / §F 的内容即以此提交后的 `dag-state` 为源，**无漂移**。 |
| `f27334d` | **A1d: spine 红条按 ORCH-40/ORCH-41 裁决收口（7 红 -> 1 红，唯一剩余红有实测归因且归 G14FIX 写集）** | 🔴 **§A V-1 / V-7 与 §E D-A1-05 的前提已变**：`tests/test_integration_spine.py` 的 `anchor_set` 接线（`spine:166`，ORCH-40 第8条 R4）**已落地**，spine 由 7 红降至 **1 红**，且提交主题自述「唯一剩余红有实测归因且**归 G14FIX 写集**」。→ **D-A1-05 的落地证据已出现，但本包未复跑、亦未读到其 `NOTES`，故 §E 中 D-A1-05 的状态不在本包改判**（`dag-state.defects` 的 `status` 字段本包实读时仍为 `OPEN`）；**`PLACEHOLDER-A1c-01`（`test_l0b_whatif_step_unlocks_when_landed` 归因未闭环）是否已由本提交闭环，须由 P2-wire-B 确认。** |
| `0d8afeb` | **E3b: golden_b 断言包收口（7 红 -> 0 红；16 -> 18 条；assert 62 -> 72）** | 🔴 **§A V-1 / V-7 / §B-4 的前提已变**：`tests/test_golden_b.py` 由 **7 红 → 0 红**，测试数 **16 → 18 条**、断言 **62 → 72**（**净增**，符合 R-14 零弱化）。这意味着 **ORCH-35 第2条的 g10 改名 + 新增「>=2 维 → BLOCK + exit_code 2」测试**、**ORCH-41 第8条采纳的 g10 方案（断言类数 6 → 11 严格增加）**、**`golden_b:343` 的 `anchor_set` 接线**、**ERRATUM-11 的 G-14 分母 = 9**、**K-26 / K-29 的 docstring 更正**按其主题均已落地。→ **§B-4「证据不足处」第 ② 项（g14 三条仍红、归 E3b）的前提已变**；**§A V-1 的 golden_b 侧红条已按其自述清零**。**但本包未复跑，且 G-01~G-15 的完整判定还依赖 golden_a 侧（E2b 仍在飞），故 V-1 维持 ❌、终判留 P2-wire-B。** |

**仍在飞（本包实测 `git status --porcelain`）**：`fixtures/golden/golden_map.json`、`tests/test_golden_a.py`、`tools/gen_golden.py` —— 三者正是 **ORCH-41 第5条裁给 E2b 的独占写集**（golden 载体包），**与 E3b 的 `tests/test_golden_b.py` 写集不相交**，印证该切分有效。

**§K 结论（不得软化）**：本文件的 ✅/❌/⏳ 三态**一律不因 §K 而上调**。理由 = **R-12**：提交主题属**自述**，本包未亲自复跑；且 §B-2 的 **M28 26 行遍历断言**、**注册表规模与 ratchet 32→28**、**§G-② 的 `git diff -U0` 卷宗**、**§A V-2 的 500 例档**、**§H 的终值哈希**在本包可见范围内**仍全部缺位**。**定稿动作仍只剩两件**：① P2-wire-B 刷新全量六门禁数字 + 11 红拆分 + ratchet；② P3b 在最终 HEAD 上跑 `tools/repro_offline.sh`（L3-strong）登记终值哈希。