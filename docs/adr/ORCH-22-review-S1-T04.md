# ORCH-22 复核签认：S1-T04 输出/中间模型 32 类逐字段复核（R4 独立复核）

| 项 | 内容 |
|---|---|
| 日期 | 2026-11-24 |
| 阶段 / 任务 | S1 / S1-T04（L4 独立复核） |
| 复核人 | R4 Reviewer（只做复核，不改任何代码；修复归 R6） |
| 复杂度 | C2 |
| 契约权威 | `docs/adr/ORCH-22.md`（426 行，裁决 14~34）+ `docs/digest/S1-T04.md`（93 行，SDD `708679e9a83d` 行号摘录） |
| 被复核产物 | `dsm/models.py`（1362 行 / 71794 B / sha256[:12] `6ad7a930bfd1`），`git diff --numstat` = 836 insertions / **0 deletions** |
| 判据 | 只认「自己实测的命令输出」或「原文行号 / 裁决号」；实测原件见 `ops/evidence/S1-T04/L4-1-structure.txt`、`L4-2-c8-nullable-columns.txt`、`L4-3-pytest-and-anticheat.txt`、`L4-4-artifact-verify.txt` |

**R4 VERDICT: PASS**（C1~C11 全 ✅；R6 待修清单：**无阻塞项**，仅 2 条非阻塞建议见 §6）

无 `QUALITY_INCIDENT`：C7 反作弊门全部实测通过（测试文件未被改写、无新增 skip/xfail、models 层无删改行、实现真实新增 836 行、602 项 S1-T04 测试在零跳过下通过）。详见 §2 C7 与 `L4-3-pytest-and-anticheat.txt`。

## 1. 环境与实测方式（可复跑）

* 仓库 `/home/szf/dev/strategy-eval-dsm`，HEAD `e579bed`，工作树 7 项在制品（本复核未新增除本文与 4 个 L4 证据文件以外的任何文件）。
* 解释器 `/home/szf/venvs/dsm/bin/python` = 3.12.3，pydantic 2.14.4；pytest 未叠加 `-q`（`pyproject.toml` addopts 已含），计数一律由 `.py` 脚本 subprocess 采集，未在 bash 里 `pytest | grep`。
* 逐字段比对方法：用 ast 读 `dsm/models.py` 的 `AnnAssign`（注解 + 默认值逐字），再用行区间切分 `docs/adr/ORCH-22.md` 裁决 14/21/23/24/25/26/27/28/29/30 的表格与正文，按「首次出现位置」还原契约的字段顺序与类型文本，双向对账；**结论不依赖 `tests/test_models_output.py` 的清单**（测试清单只作为交叉验证）。

## 2. 复核清单逐条判定

| 项 | 判定 | 实测证据（文件 + 行） | 契约出处 |
|---|---|---|---|
| C1 六个输出模型逐字段 | ✅ | `L4-1-structure.txt`：per-model 表 32 行全 `order==ADR True`、type_text_diffs 仅 `stability_label`/`agreement`（→ C8）；`TYPE_TEXT_PAIRS_CHECKED 219 of 219`；`AuditBundle ruling 14: table item column = 1..15(11a/11b)` = 15 项 16 字段 | 裁决 14~27；`[L1051]`、`[L1612]`-`[L1626]`、`[L1628]`-`[L1634]`、`[L1018]`-`[L1020]`、`[L1028]`-`[L1030]`、`[L1040]` |
| C1 补充：GradeLedgerRow 双列 | ✅ | `L4-1`：`GradeLedgerRow | 14 | 14 | True | []`；`L4-3`：`-k d03/d04` 属 602 passed；实测字段序含 `recommended_action` / `decided_action` / `decision_note` 三列 | 裁决 24 + ORCH §5.2 S1-T04 验收；`[L1630]` |
| C2 8 个中间 Frame 行式 + PoolStats | ✅ | `L4-1`：`FRAME_ROWSTYLE` 9 行 `origin=tuple` 且元素类 `is` 命中；`RedlineFrame.rows` 元素 `=RedlineEvalRow`、`is not RedlineRow`（T5 输入模型）；`set[=0`、`frozenset` 只出现在注释行 L604 | 裁决 28 第 3 条（禁 set/frozenset）、`[L1053]`③④、`[L1052]`、V-3 |
| C2 补充：PoolKey 2 字段三处共用 | ✅ | `L4-1`：4 条 `resolves_to_same_PoolKey_object=True`（`NormalizedRow.pool_key`/`PoolRow.pool_key`/`PoolStatRow.pool_key`/`ScoreCardRow.ranking_pool`），`PoolKey fields=['biz_domain', 'evidence_class']` | 裁决 29；`[L1001]`、`[L1119]` |
| C2 补充：PoolStatRow 双占比 | ✅ | `L4-1`：`PoolStatRow` 4 字段 `share_in_pool` + `share_overall` 并存（type_text 全等） | 裁决 28/29 + B-020；`[L1006]`、`[L1003]`「禁止只报合并占比」 |
| C3 ScoringContext 16 字段（A8 + B8） | ✅ | `L4-1`：`ScoringContext | 16 | 16 | True | []`；A 组 8 项含 `run_id`，`run_at :: datetime`（必填）；B 组 8 项类型逐一对上裁决 30 正文 `attainment: AttainmentFrame` … `pool_stats: PoolStats` | 裁决 30；ORCH-13 裁决 1；`[L1089]`、`[L1271]`（H-8）、`[L1016]` |
| C4 未新建 AllFrames / ReportSet / RunContext | ✅ | `L4-1`：`AllFrames/ReportSet/RunContext present in dsm.models: []`；顶层类 48 = 14 既有公开 + `_InputRow` + 32 新增 + `_OutputModel`，无第 33 个新类 | 裁决 31；B-021 |
| C5 通用契约 | ✅ | `L4-1`：`models whose runtime config is not frozen+extra=forbid: []`；32 类基类全为 `_OutputModel`（`ConfigDict(frozen=True, extra='forbid')` 与 `_InputRow` 逐字同）；`default value spellings: ['()', 'None']`；`numeric literals in the whole new section: []`；`float literals: []`；`annotations containing bare float/int/bool/set/frozenset: []`；墙钟 token 全 0 命中；import 仅 `dsm.numeric` / `dsm.reason_codes`；`Enum 子类定义: []` 且 `severity is reason_codes.Severity -> True` | §5 通用契约 1~6、裁决 32；H-4/H-5/H-6/H-7/H-8/H-9、`[L865]`、`[L1265]`-`[L1267]`、`[L1271]` |
| C6 `_minor` 边界 / 逐字名 | ✅ | `L4-1`：`fields ending in _minor: ['value_captured_minor']`；verbatim `value_captured` 不存在；CEL-0 四列 `incremental_value`/`incremental_ci_lower`/`incremental_ci_upper`/`estimator_method` 保逐字名（ScoreCardRow 与既有 DesignCardRow 同名同序）；`evidence_source` 在 `ScoreCardRow` 与 `EvidenceRow` 均在位；`metric_code` 在 EntropyDiagnosticRow（`metric_id` 不在）、`grade_reason_codes` 与 `grade_reason_path` 分立 | 裁决 22、ORCH-16 裁决 1/2、ORCH-15、§0 第 3 条；`[L1896]`、`[L1040]`、`[L1620]` vs `[L964]` |
| C7 H-11 golden 纪律 | ✅（无 QUALITY_INCIDENT） | `L4-3`：测试文件 `bytes=77740 | lines=1753 | sha256[:12]=42cbbc85e7a8 | def test_=83`，与 `L1-red.txt` 的 `FILE STATS` / `COLLECTED: 602 tests collected` 逐字一致；文件未被 git 跟踪且 `tests/` 无改动项；全仓 skip/xfail 仅 `test_numeric_properties.py:114`（HEAD 既有，工作树未改）；`git diff --numstat dsm/models.py = 836  0`；HEAD 的 15 个类源码段 15/15 byte-identical；`full suite: 1268 passed`、`tests/test_models_output.py: 602 passed`、0 skipped / 0 error | ORCH §2 H-11；裁决 34 末段「不得改测试、不得放宽断言」 |
| C8 三列可空封闭集的 PlainValidator 实现 | ✅ 等价，不构成放宽 | `L4-2`：三列「合法成员 + None」全 ACCEPT（`model_dump_json` 出 `null`，序列化 0 warning），逐列 14~15 例非法输入（近名串 / 大小写变体 / 尾空格 / 空串 / int / bool / float / Decimal / list / tuple / str-Enum 成员 / `NOT_ASSESSED` 之于 GradeCode / 同一 12 输入的契约形态对照表）全 REJECT；`source uses get_args? True` 且 `_none_or_member` 内无硬编码成员清单（双事实源不存在）；成员集与裁决 19/20/26/28 逐字相等 | 裁决 21（`StabilityLabel | None`）、26（`MethodAgreement | None`）、28（`GradeCode | None`）；判定详见 §4 |
| C9 声明顺序 | ✅ 无需修正 | `L4-1`：32 类 `order==ADR` 全 True（含裁决 14/21/24/25/26/27/28/29/30 表格与正文两种载体）；`EXPECTED_FIELDS` 32 个值实测全部是 frozenset（集合不含列序契约），测试对列序无任何断言（d01 集合比较 / d10 计数 / j02 kind 字典），`L4-3` 602 passed 零跳过 | 裁决 32 + `[L1053]`③④；S6 列序 = `model_fields` 声明序 = ORCH-22 表格序，详见 §5 |
| C10 逐字段清单 | ✅ 已交付 | 本文 §3（32 类 / 219 字段，源码注解逐字 + 契约类型文本） | 裁决 32 末段「R4 须把新增字段清单抄进复核报告，作为 S6 的输入」 |
| C11 surplus 白名单 | ✅ | `L4-1`：`classes not covered by ruling 33 whitelist: []`、`whitelist classes not landed: []`、`fields outside ADR-parsed sets (surplus): []`；白名单内多出的 `rows`/`by_scheme`/`by_strategy`/`flags`/`flipped_count`/`assessed_count`/`flag`/`previous_grade`/`ledger_complete`/`run_id`/`_minor` 后缀一律按裁决 33 判 ✅ | 裁决 33 |

## 3. C10 逐字段清单（S6 序列化器输入事实）

约定：`声明` 列 = `dsm/models.py` 里该字段的注解与默认值**逐字**（ast.unparse，非重排非美化）；`契约类型` 列 = ORCH-22 对应表格/正文的类型文本。两列不等价的仅有 3 处（C8，已标 `*`）与 `severity` 的模块限定写法（同一对象，非差异）。容器形状写在类型里（`tuple[X, ...]` / `dict[K, V]`）。必填列 `= 必填`；可空列给默认值；空容器默认给 `= ()` / `= {}`。

实测合计：32 类 / 219 字段（`L4-1`：`new classes=32 ... total new fields=219`），与裁决 34 基线逐字相符。

### 3.1 六个输出模型（`[L867]`）

#### `AuditBundle` — 16 字段（裁决 14；依据 [L1051] 15 项 -> 16 字段）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `run_id` | `str` | `str` | 必填 |
| 2 | `run_at` | `datetime` | `datetime` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `dsm_version` | `str` | `str` | 必填 |
| 5 | `design_version` | `str` | `str` | 必填 |
| 6 | `cel_contract_version` | `str` | `str` | 必填 |
| 7 | `weight_version_id` | `str` | `str` | 必填 |
| 8 | `config_snapshot_sha256` | `str` | `str` | 必填 |
| 9 | `input_fingerprints` | `InputFingerprints` | `InputFingerprints` | 必填 |
| 10 | `output_fingerprints` | `dict[str, str]` | `dict[str, str]` | 必填 |
| 11 | `sensitivity_schemes` | `tuple[SchemeName, ...]` | `tuple[SchemeName, ...]` | 必填 |
| 12 | `seed` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |
| 13 | `preflight_findings` | `tuple[PreflightFinding, ...]` | `tuple[PreflightFinding, ...]` | 必填 |
| 14 | `downgrade_actions` | `tuple[DowngradeAction, ...]` | `tuple[DowngradeAction, ...]` | 必填 |
| 15 | `exit_code` | `StrictInt` | `StrictInt` | 必填 |
| 16 | `reproducibility_hash` | `str` | `str` | 必填 |

#### `ScoreCardRow` — 35 字段（裁决 21/22/23；依据 [L1612]-[L1626]、[L1220]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `weight_version_id` | `str` | `str` | 必填 |
| 5 | `dict_version` | `str` | `str` | 必填 |
| 6 | `anchor_set_id` | `str` | `str` | 必填 |
| 7 | `run_id` | `str` | `str` | 必填 |
| 8 | `per_metric` | `dict[str, ScoreCardMetricCell]` | `dict[str, ScoreCardMetricCell]` | 必填 |
| 9 | `per_dim` | `dict[str, ScoreCardDimCell]` | `dict[str, ScoreCardDimCell]` | 必填 |
| 10 | `composite_absolute` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 11 | `composite_relative` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 12 | `evidence_class` | `EvidenceClass` | `EvidenceClass` | 必填 |
| 13 | `evidence_reason` | `ReasonCode` | `ReasonCode` | 必填 |
| 14 | `evidence_source` | `EvidenceSource` | `EvidenceSource` | 必填 |
| 15 | `interpretation_limit` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 16 | `redline_pass` | `StrictBool` | `StrictBool` | 必填 |
| 17 | `redline_flags` | `tuple[ReasonCode, ...] = ()` | `tuple[ReasonCode, ...] = ()` | 空容器 () |
| 18 | `grade` | `FrameGrade` | `FrameGrade` | 必填 |
| 19 | `grade_reason_codes` | `tuple[ReasonCode, ...]` | `tuple[ReasonCode, ...]` | 必填 |
| 20 | `capped_flag` | `StrictBool` | `StrictBool` | 必填 |
| 21 | `cap_reason` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |
| 22 | `ranking_pool` | `PoolKey \| None = None` | `PoolKey \| None = None` | 可空(None) |
| 23 | `rank_in_pool` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |
| 24 | `pool_size` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |
| 25 | `eligible_for_L1_library` | `StrictBool` | `StrictBool` | 必填 |
| 26 | `l1_gate_reasons` | `tuple[ReasonCode, ...] = ()` | `tuple[ReasonCode, ...] = ()` | 空容器 () |
| 27 | `stability_label` | `_NullableStabilityLabel = None` | `StabilityLabel \| None = None` * | 可空(None) |
| 28 | `flip_under_pct10` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 29 | `flip_under_pct20` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 30 | `usable_for_elimination` | `StrictBool` | `StrictBool` | 必填 |
| 31 | `incremental_value` | `FactValue \| None = None` | `FactValue \| None = None` | 可空(None) |
| 32 | `incremental_ci_lower` | `FactValue \| None = None` | `FactValue \| None = None` | 可空(None) |
| 33 | `incremental_ci_upper` | `FactValue \| None = None` | `FactValue \| None = None` | 可空(None) |
| 34 | `estimator_method` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 35 | `value_captured_minor` | `MoneyMinor \| None = None` | `MoneyMinor \| None = None` | 可空(None) |

#### `GradeLedgerRow` — 14 字段（裁决 24；依据 [L1628]-[L1634]、[L1221]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `grade` | `FrameGrade` | `FrameGrade` | 必填 |
| 5 | `previous_grade` | `FrameGrade \| None = None` | `FrameGrade \| None = None` | 可空(None) |
| 6 | `recommended_action` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 7 | `decided_action` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 8 | `decision_note` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 9 | `owner_dept` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 10 | `owner_name` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 11 | `deadline` | `date \| None = None` | `date \| None = None` | 可空(None) |
| 12 | `archive_ref` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 13 | `ledger_complete` | `StrictBool` | `StrictBool` | 必填 |
| 14 | `usable_for_elimination` | `StrictBool` | `StrictBool` | 必填 |

#### `SensitivityReport` — 6 字段（裁决 25；依据 [L1018]-[L1020]、[L1222]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `by_scheme` | `tuple[SensitivitySchemeResult, ...]` | `tuple[SensitivitySchemeResult, ...]` | 必填 |
| 2 | `by_strategy` | `tuple[SensitivityStrategyRow, ...]` | `tuple[SensitivityStrategyRow, ...]` | 必填 |
| 3 | `loo_dominant_metrics` | `tuple[str, ...] = ()` | `tuple[str, ...] = ()` | 空容器 () |
| 4 | `norm_swap_rank_correlation` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 5 | `flags` | `tuple[ReasonCode, ...] = ()` | `tuple[ReasonCode, ...] = ()` | 空容器 () |
| 6 | `seed` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |

#### `TriangulationReport` — 8 字段（裁决 26；依据 [L1028]-[L1030]、[L1224]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[TriangulationStrategyRow, ...]` | `tuple[TriangulationStrategyRow, ...]` | 必填 |
| 2 | `rho_main_topsis` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 3 | `rho_main_gra` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 4 | `rho_topsis_gra` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 5 | `mean_rho` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 6 | `agreement` | `_NullableMethodAgreement = None` | `MethodAgreement \| None = None` * | 可空(None) |
| 7 | `gra_by_metric` | `dict[str, Ratio]` | `dict[str, Ratio]` | 必填 |
| 8 | `flags` | `tuple[ReasonCode, ...] = ()` | `tuple[ReasonCode, ...] = ()` | 空容器 () |

#### `EntropyDiagnosticRow` — 10 字段（裁决 27；依据 [L1040]、[L1223]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `metric_code` | `str` | `str` | 必填 |
| 2 | `e_j` | `Ratio` | `Ratio` | 必填 |
| 3 | `d_j` | `Ratio` | `Ratio` | 必填 |
| 4 | `cv_j` | `Ratio` | `Ratio` | 必填 |
| 5 | `vif_j` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 6 | `max_abs_corr` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 7 | `status` | `EntropyStatus` | `EntropyStatus` | 必填 |
| 8 | `suggested_action` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |
| 9 | `owner` | `str` | `str` | 必填 |
| 10 | `flags` | `tuple[ReasonCode, ...] = ()` | `tuple[ReasonCode, ...] = ()` | 空容器 () |

### 3.2 八个中间模型（`[L868]`）

#### `AttainmentFrame` — 2 字段（裁决 28；依据 [L928]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[AttainmentRow, ...]` | `tuple[AttainmentRow, ...]` | 必填 |
| 2 | `attainment_coverage` | `dict[str, Ratio]` | `dict[str, Ratio]` | 必填 |

#### `NormalizedFrame` — 1 字段（裁决 28；依据 [L945]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[NormalizedRow, ...]` | `tuple[NormalizedRow, ...]` | 必填 |

#### `EvidenceFrame` — 1 字段（裁决 28；依据 [L977]-[L981]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[EvidenceRow, ...]` | `tuple[EvidenceRow, ...]` | 必填 |

#### `RedlineFrame` — 1 字段（裁决 28；依据 [L988]-[L994]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[RedlineEvalRow, ...]` | `tuple[RedlineEvalRow, ...]` | 必填 |

#### `ScoreFrame` — 1 字段（裁决 28；依据 [L952]-[L955]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[ScoreRow, ...]` | `tuple[ScoreRow, ...]` | 必填 |

#### `GradeFrame` — 1 字段（裁决 28；依据 [L964]-[L968]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[GradeRow, ...]` | `tuple[GradeRow, ...]` | 必填 |

#### `PoolFrame` — 1 字段（裁决 28；依据 [L1002]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[PoolRow, ...]` | `tuple[PoolRow, ...]` | 必填 |

#### `PoolStats` — 4 字段（裁决 28/29；依据 [L1006]、[L1003]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `rows` | `tuple[PoolStatRow, ...]` | `tuple[PoolStatRow, ...]` | 必填 |
| 2 | `evidence_structure` | `dict[EvidenceClass, StrictInt]` | `dict[EvidenceClass, StrictInt]` | 必填 |
| 3 | `not_assessed_count` | `StrictInt` | `StrictInt` | 必填 |
| 4 | `not_assessed_reasons` | `dict[str, StrictInt]` | `dict[str, StrictInt]` | 必填 |

### 3.3 七个 Frame 行模型（裁决 33）

#### `AttainmentRow` — 10 字段（裁决 28；依据 [L928]、[L930]、[L931]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `metric_id` | `str` | `str` | 必填 |
| 5 | `attainment` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 6 | `direction` | `MetricDirection` | `MetricDirection` | 必填 |
| 7 | `target_source` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 8 | `has_target` | `StrictBool` | `StrictBool` | 必填 |
| 9 | `capped_flag` | `StrictBool` | `StrictBool` | 必填 |
| 10 | `reason_code` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |

#### `NormalizedRow` — 9 字段（裁决 28；依据 [L939]-[L945]、ORCH-13 裁决 2）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `metric_id` | `str` | `str` | 必填 |
| 5 | `pool_key` | `PoolKey` | `PoolKey` | 必填 |
| 6 | `norm_value` | `Ratio` | `Ratio` | 必填 |
| 7 | `method` | `NormalizationMethod` | `NormalizationMethod` | 必填 |
| 8 | `anchor_used` | `StrictBool` | `StrictBool` | 必填 |
| 9 | `reason_code` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |

#### `EvidenceRow` — 7 字段（裁决 28；依据 [L980]、ORCH-15）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `evidence_class` | `EvidenceClass` | `EvidenceClass` | 必填 |
| 4 | `evidence_reason` | `ReasonCode` | `ReasonCode` | 必填 |
| 5 | `evidence_source` | `EvidenceSource` | `EvidenceSource` | 必填 |
| 6 | `control_group_id` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 7 | `interpretation_limit` | `str \| None = None` | `str \| None = None` | 可空(None) |

#### `RedlineEvalRow` — 15 字段（裁决 28；依据 [L988]-[L993]、[L1181]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `metric_id` | `str` | `str` | 必填 |
| 5 | `level` | `RedlineLevel` | `RedlineLevel` | 必填 |
| 6 | `comparator` | `Comparator` | `Comparator` | 必填 |
| 7 | `threshold_value` | `UnitValue` | `UnitValue` | 必填 |
| 8 | `hit` | `StrictBool` | `StrictBool` | 必填 |
| 9 | `forced_grade` | `_NullableForcedGrade = None` | `GradeCode \| None = None` * | 可空(None) |
| 10 | `waiver_approval_id` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 11 | `waiver_valid_from` | `date \| None = None` | `date \| None = None` | 可空(None) |
| 12 | `waiver_valid_to` | `date \| None = None` | `date \| None = None` | 可空(None) |
| 13 | `waiver_scope` | `str \| None = None` | `str \| None = None` | 可空(None) |
| 14 | `soft_deduction` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 15 | `reason_code` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |

#### `ScoreRow` — 10 字段（裁决 28；依据 [L952]-[L955]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `composite_absolute` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 5 | `composite_relative` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 6 | `dim_absolute` | `dict[str, Ratio]` | `dict[str, Ratio]` | 必填 |
| 7 | `dim_relative` | `dict[str, Ratio]` | `dict[str, Ratio]` | 必填 |
| 8 | `coverage` | `Ratio` | `Ratio` | 必填 |
| 9 | `weight_version_id` | `str` | `str` | 必填 |
| 10 | `operator` | `ScoreOperator` | `ScoreOperator` | 必填 |

#### `GradeRow` — 9 字段（裁决 28；依据 [L964]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `grade` | `FrameGrade` | `FrameGrade` | 必填 |
| 5 | `grade_reason_path` | `tuple[ReasonCode, ...]` | `tuple[ReasonCode, ...]` | 必填 |
| 6 | `capped` | `StrictBool` | `StrictBool` | 必填 |
| 7 | `cap_reason` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |
| 8 | `action` | `tuple[str, ...] \| None = None` | `tuple[str, ...] \| None = None` | 可空(None) |
| 9 | `usable_for_elimination` | `StrictBool` | `StrictBool` | 必填 |

#### `PoolRow` — 7 字段（裁决 28；依据 [L1006]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `period` | `str` | `str` | 必填 |
| 4 | `pool_key` | `PoolKey` | `PoolKey` | 必填 |
| 5 | `pool_rank` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |
| 6 | `primary_pool_eligible` | `StrictBool` | `StrictBool` | 必填 |
| 7 | `reject_reason` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |

#### `PoolStatRow` — 4 字段（裁决 28/29；依据 [L1006]、[L1003]、B-020）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `pool_key` | `PoolKey` | `PoolKey` | 必填 |
| 2 | `count` | `StrictInt` | `StrictInt` | 必填 |
| 3 | `share_in_pool` | `Ratio` | `Ratio` | 必填 |
| 4 | `share_overall` | `Ratio` | `Ratio` | 必填 |

### 3.4 十个子模型（裁决 33）

#### `PoolKey` — 2 字段（裁决 29；依据 [L1001]、[L1119]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `biz_domain` | `str` | `str` | 必填 |
| 2 | `evidence_class` | `EvidenceClass` | `EvidenceClass` | 必填 |

#### `InputTableFingerprint` — 2 字段（裁决 15；依据 [L888]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `sha256` | `str` | `str` | 必填 |
| 2 | `row_count` | `StrictInt` | `StrictInt` | 必填 |

#### `PreflightFinding` — 3 字段（裁决 16；依据 [L900]、dsm.reason_codes.Severity）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `code` | `str` | `str` | 必填 |
| 2 | `severity` | `reason_codes.Severity` | `Severity` | 必填 |
| 3 | `message` | `str` | `str` | 必填 |

#### `DowngradeAction` — 3 字段（裁决 17；依据 [L1051] 第 13 项、H-6）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `reason_code` | `ReasonCode` | `ReasonCode` | 必填 |
| 2 | `action` | `str` | `str` | 必填 |
| 3 | `subject` | `str \| None = None` | `str \| None = None` | 可空(None) |

#### `ScoreCardMetricCell` — 3 字段（裁决 23；依据 [L1613]、[L1150]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `actual_value` | `FactValue` | `FactValue` | 必填 |
| 2 | `target_value` | `UnitValue \| None = None` | `UnitValue \| None = None` | 可空(None) |
| 3 | `attainment` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |

#### `ScoreCardDimCell` — 4 字段（裁决 23；依据 [L1614]、[L879]、[L1192]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `attainment` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 2 | `relative_score` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 3 | `coverage` | `Ratio` | `Ratio` | 必填 |
| 4 | `weight` | `Ratio` | `Ratio` | 必填 |

#### `SensitivitySchemeResult` — 5 字段（裁决 25；依据 [L1018]-[L1019]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `scheme` | `SchemeName` | `SchemeName` | 必填 |
| 2 | `overall_flip_rate` | `Ratio` | `Ratio` | 必填 |
| 3 | `flipped_count` | `StrictInt` | `StrictInt` | 必填 |
| 4 | `assessed_count` | `StrictInt` | `StrictInt` | 必填 |
| 5 | `flag` | `ReasonCode \| None = None` | `ReasonCode \| None = None` | 可空(None) |

#### `SensitivityStrategyRow` — 5 字段（裁决 25；依据 [L1018]、[L1624]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `stability_label` | `StabilityLabel` | `StabilityLabel` | 必填 |
| 4 | `flip_under_pct10` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |
| 5 | `flip_under_pct20` | `Ratio \| None = None` | `Ratio \| None = None` | 可空(None) |

#### `TriangulationStrategyRow` — 4 字段（裁决 26；依据 [L1028]）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `strategy_id` | `str` | `str` | 必填 |
| 2 | `version_id` | `str` | `str` | 必填 |
| 3 | `topsis_rank` | `StrictInt` | `StrictInt` | 必填 |
| 4 | `gra_rank` | `StrictInt` | `StrictInt` | 必填 |

### 3.5 运行上下文

#### `ScoringContext` — 16 字段（裁决 30；依据 ORCH-13 裁决 1 + A 组补 run_id）

| # | 字段 | 声明（逐字） | 契约类型（ORCH-22） | 形态 |
|---|---|---|---|---|
| 1 | `period` | `str` | `str` | 必填 |
| 2 | `run_at` | `datetime` | `datetime` | 必填 |
| 3 | `run_id` | `str` | `str` | 必填 |
| 4 | `seed` | `StrictInt \| None = None` | `StrictInt \| None = None` | 可空(None) |
| 5 | `weight_version_id` | `str` | `str` | 必填 |
| 6 | `evidence_mode` | `EvidenceMode` | `EvidenceMode` | 必填 |
| 7 | `cel_enabled` | `StrictBool` | `StrictBool` | 必填 |
| 8 | `input_fingerprints` | `InputFingerprints` | `InputFingerprints` | 必填 |
| 9 | `attainment` | `AttainmentFrame` | `AttainmentFrame` | 必填 |
| 10 | `normalized` | `NormalizedFrame` | `NormalizedFrame` | 必填 |
| 11 | `evidence` | `EvidenceFrame` | `EvidenceFrame` | 必填 |
| 12 | `redline` | `RedlineFrame` | `RedlineFrame` | 必填 |
| 13 | `score` | `ScoreFrame` | `ScoreFrame` | 必填 |
| 14 | `grade` | `GradeFrame` | `GradeFrame` | 必填 |
| 15 | `pool` | `PoolFrame` | `PoolFrame` | 必填 |
| 16 | `pool_stats` | `PoolStats` | `PoolStats` | 必填 |

`*` = C8 三列：契约写 `Alias | None = None`，实现写 `Annotated[Alias, PlainValidator(_none_or_member(Alias))]`（默认仍 `None`）；实测可接受输入集与契约写法**完全相同**（`L4-2`），判定见 §4。

## 4. C8 专项判定：PlainValidator 可空封闭集

**判定：✅ 等价于「可空 + 封闭取值」，不构成放宽；不需要 R6 修正。**理由全部来自实测：

1. 取值集合逐字对裁决 19/20/26/28：`_none_or_member` 内 `legal = tuple(get_args(closed_alias))`（`dsm/models.py` L687 def / L688 取值），合法值**直接读自别名本身**，未另抄清单 → 无双事实源（`L4-2`：`source uses get_args? True`；硬编码成员检索为空）。
2. 可空性：三列 `default=None`、`is_required=False`，显式传 `None` 被接受，`model_dump_json` 输出 `null`，序列化 0 warning → 裁决 32 第 3 条「null 与空串严格区分」未被破坏。
3. 封闭性：三列各自对近名串（`BOUNDARY` / `NOT_ASSESSED` 之于 GradeCode）、大小写变体、尾空格、空串、`1`/`0`、`True`/`False`、`1.0`、`Decimal("1")`、list、tuple、`Severity.INFO`（str-Enum 成员）全部 `value_error` 拒绝（`L4-2` 实测拒绝例数：stability_label 15 / agreement 14 / forced_grade 14）。`type(value) is str` 的写法比 `Literal | None` 的 lax 路径更严（连 str 子类 / Enum 成员都不放过）。
4. 与契约写法的实测对照：`L4-2` 末段把同一 12 个输入（None、三个合法成员、`l1`、`NOT_ASSESSED`、尾空格、空串、`L10`、1、True、1.0）同时喂给契约形态 `Literal[...] | None` 与实现形态 `Annotated[..., PlainValidator]`，accept/reject 边界 12/12 相同（该节末行给出布尔结论）；差异只在 pydantic 的 error type 名（`literal_error` vs `value_error`），而本仓判据不依赖 error type 字符串：实测 `tests/test_models_output.py`中 `literal_error` / `value_error` / `.type` 命中数均为 0，拒收一律写 `pytest.raises(ValidationError)`（14 处）。
5. 为什么没写成 `Alias | None`：只读测试 `tests/test_models_output.py`（sha256[:12] `42cbbc85e7a8`，L1 定稿，R4 不得改）的 b04 / c03 用 `_literal_values(model_fields[name].annotation)` 读封闭集来证「列取值 = 别名取值且未扩值」；该 helper（L142-153）只剥 `__metadata__`、不拆 Union。实测 `_literal_values(StabilityLabel | None) = ()`，即**契约写法会让这两条门禁失效**（空集等于放弃检查）。实现取「别名 + 只多一个 None 分支的校验器」，同时保住了门禁与语义 —— 这不是绕过失败路径，而是在不得改测试的约束下唯一不放宽的写法（H-11 优先）。
6. 唯一可观测副作用（不违反任何契约条款）：`model_json_schema()` 对该列退化为 `{"default": null, "title": ...}`，丢掉 enum/null 提示（`L4-2` 末段实测，契约形态为 `anyOf[enum, null]`）。本任务与全仓无 JSON Schema 消费者（`grep model_json_schema dsm/models.py` 空），SDD/ORCH-22 未要求 models 层出 schema；→ 转为 §6 建议 1，交 S6（audit.py 序列化器）处理，不回退本任务。

## 5. C9 专项判定：声明顺序与 S6 列序契约

* 事实：32 个新类的 `model_fields` 顺序与 ORCH-22 裁决 14/21/23/24/25/26/27/28/29/30 的表格行序（ScoringContext 的 B 组按其正文罗列序）**逐字相同**（`L4-1` 全 True）。
* 事实：`tests/test_models_output.py` 的 `EXPECTED_FIELDS` 32 个值**全部是 frozenset**（实测 `EXPECTED_FIELDS value types: {'frozenset': 32}`）。集合没有「罗列顺序」可言，其迭代序受哈希扰动影响 —— 这恰是裁决 28 在契约侧禁用 set/frozenset 的理由 —— 因此「N 个模型声明顺序 ≠ 测试罗列顺序」这类计数不可复现（同一台机器两次实测：9 同 23 异 / 7 同 25 异，两条都记在 `L4-1`），也不能作为列序证据；测试对列序无任何断言（d01 集合比较、d10 只比 len、j02 用 kind 字典）。
* 判定：**不构成需要修正的事项**（列序契约已由「声明序 == ORCH-22 序」这一实测事实完整满足，无模型需要重排）。S6 序列化器要落的 CSV 列序权威 = SDD/ORCH-22 表格序 = 当前声明序，现状即契约。若 R6 按测试罗列顺序去重排声明，反而会把列序改错。
* 交给 S6 的约束（写进 §3 清单即可执行）：CSV 列序取 `model_fields` 迭代序；`dict` 列（`per_metric` / `per_dim` / `attainment_coverage` / `evidence_structure` / `not_assessed_reasons` / `output_fingerprints` / `gra_by_metric` / `dim_absolute` / `dim_relative`）序列化前按 key 显式排序（`[L1053]`③）；`tuple` 列按业务主键排序（`[L1053]`④）；`Ratio` 先统一 q12 再转字符串、浮点先转 Decimal、None 与空串严格区分（`[L1053]`①②⑤）；新增 219 字段全部是 V-11 的同步对象（`[L1274]`）。

## 6. R6 待修清单

**阻塞项：无。** 以下 2 条为非阻塞建议（不改也判 PASS；不属于 H-11 违规）：

| # | 级别 | 事项 | 期望（契约出处） | 实际（实测） | 建议改法（由谁做） |
|---|---|---|---|---|---|
| 1 | 非阻塞 | C8 三列的 JSON Schema 可空提示退化 | 契约未要求 models 层出 schema（裁决 14/21/26/28 只约束取值与可空性；`[L1053]`/`[L1274]` 归 S6） | `model_json_schema()` 对 `stability_label` 给 `{"default": null}`，无 enum/null（`L4-2`） | S6 在 audit/reports 层自列「列名 → 可空 + 封闭集」映射并输出 `null`；实测 `model_dump_json` 已正确，无需改 `dsm/models.py`（若日后要改，须与测试的 `_literal_values` 门禁一并设计，属新 ADR，不在 S1-T04 范围） |
| 2 | 非阻塞 | 建议给 S6 的白名单纪律 | 裁决 33 已封闭授权名 | 实测无白名单外新增（`L4-1` surplus 为空） | 落库时把本文 §3 清单作为 V-11 序列化器待办清单；后续任务加字段须先扩裁决 33 白名单，不得反向改测试 |

## 7. 裁决 34 基线交叉验证（R4 自测，非引用）

| 基线项 | 裁决 34 记录 | R4 实测 | 一致 |
|---|---|---|---|
| 新增类数 | 32 | `new classes=32`（顶层类 48 = 15 HEAD + 32 + `_OutputModel`） | ✅ |
| ScoreCardRow | 35 | 35 | ✅ |
| GradeLedgerRow | 14 | 14 | ✅ |
| ScoringContext | 16 | 16 | ✅ |
| 新增字段合计 | 219 | `total new fields=219`（且 219/219 完成 ADR 类型文本对账） | ✅ |
| 既有公开模型 | 14 | `PREEXISTING_MODELS=14`；HEAD 15 类（含 `_InputRow`）源码段 15/15 byte-identical | ✅ |
| 全量 pytest | 主控 1268 passed | R4 复跑 `1268 passed in 1.43s`，rc=0，无 skipped/xfailed/error 行 | ✅ |
| 测试文件 | 602 collected / 77740 B / 1753 行 / 83 def | 同值，sha256[:12] `42cbbc85e7a8` | ✅ |

## 8. 复核边界声明

* 本文件与 `ops/evidence/S1-T04/L4-*.txt` 是 R4 在本任务中**唯一**新建的两个（组）文件；`dsm/`、`tests/`、`docs/adr/ORCH-22.md`、`docs/digest/*`、`ops/dag-state.json` 未触碰，未做任何 git 写操作（H-12，落库归 R5）。
* 未读取 `工行参考文件/` 下任何文档全文；SDD 原文只按行区间取用，本任务实际只用了 digest 的 `sed -n` 行区间（`docs/digest/S1-T04.md` 已给 `[L1050]`-`[L1055]`、`[L1061]`-`[L1064]`、`[L1218]`-`[L1226]`、`[L1896]`-`[L1902]` 摘录）。
* CampaignLab 只读区（m0-framework / `0cccb76cdee94689448b547b6f06254c51b75d72`）全程未触碰。
* 签认含义：S1-T04 输出侧契约层（32 类 / 219 字段）与 ORCH-22 裁决 14~34 逐字段一致，B-019 / B-020 / B-021 的「本任务不预建」边界同样成立。L4 通过，可进 R5 落库。
