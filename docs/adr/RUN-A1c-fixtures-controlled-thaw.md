# RUN-A1c · fixtures 受控解冻（ORCH-29 第5条 / ORCH-37 十项裁决落地）

- 包号 **A1c**；施工单 `dsm_stage/A1CPREP/A1C-EXEC-SPEC.md`（1208 行 / 143439 B）§8 Step 0~10
- 观测 HEAD（Step 0）`a3a4701` → 落盘时 `ac12ed5` → 计数实测时 `897cad1`（在飞 lane 推进，正常）
- 契约原文 sha256[:12] = `708679e9a83d`、2003 行（**门禁通过**，全程只读）
- 邻仓 `/home/szf/dev/CampaignLab`：`m0-framework / 0cccb76 / porcelain 0 / rev-list 154`（**一致，未写**）
- 写集（实际）：`dsm/fixtures_gen.py`、`fixtures/**`、本 ADR。**未**写 `ops/dag-state.json`（ORCH-37：主控代登记）

## 0. Step 0 / Step 2 门禁实测
- `git status --porcelain fixtures` → 空（解冻前）
- BEFORE 指纹与 `dsm_stage/A1CPREP/before.sha256` **diff 为空**
- §2.3 probe 重跑（HEAD 原码 → `dsm_stage/A1c/baseline/`）：**`BASELINE_17_17_EQUAL`，17/17 sha256 全等**
  → 生成链未被并行 lane 污染，A1c 可解冻；AFTER 的一切 sha256 变化均可归因于 A1c 的补丁。

## 1. 三条数据缺陷的原文逐字依据（ADR 必含项 1）
**D-A1-04（provenance 缺失 → C-01 恒 BLOCK）**
- L900：`| C-01 | 权重版本有效性 | status = FROZEN；评价期在生效区间内；含 approved_by / approved_date / whatif_run_id | **BLOCK**，退出码 2 |`
- L1241：`        whatif_run_id:            # 权重影响预演运行号；FROZEN 而缺此项 → 配置加载直接失败`
- L1242：`        approved_by / approved_date / effective_from / effective_to`
- L1281：`| 权重 FROZEN 但缺 whatif_run_id | config | **加载失败** | 否 | 错误信息 |`
- L1231：`        kind: AHP_ONLY | AHP_ENTROPY_COMBINED | EXPERT_ONLY`
- L1232-1233：`        ahp:                      # 专家两两比较矩阵、λ_max、CI、RI、CR、专家人数、访谈日期、` / `                                  # 几何平均法与特征向量法两套权重及其最大差`
- L1435（P-11，经 `dsm/config.py:1205-1207` 转述）：FROZEN 权重版本须含 AHP 矩阵 + CR
- L1322-1326：`status=BLOCK → 写 audit_bundle / 退出码 2 / 不产出 score_card`；`status=PASS/WARN → dsm score --period P`
→ **实现照原文正确、是数据违约**，故不得降为 WARN（V-14）。

**D-A1-02（4 张 DID 卡缺 [L1171] 假设载体 → 证据分布塌成 A3B0C4D6）**
- L977 ③：`③ 准实验（DID / 合成对照 / 分层匹配 / 时间断点，须写方法名与假设）→ **B**`
- L1171：`| **alt_method_note** | 无严谨对照条件时用了什么替代方法 |`
- L1172：`| **interpretation_limit** | **解释限制** —— C 类策略**必须填**，否则降 D 不出分（D4） |`
- L1293：`| C 类无解释限制 | evidence Step 5 | 降为 D → NOT_ASSESSED | 否 | evidence_reason |`
- L1459：`- 证据分布：A×3、B×3、C×4、D×2（确保四类路径都被走到）`
→ **ORCH-37 第4条**：只补 `alt_method_note`；`interpretation_limit` **不补**（`dsm/evidence.py:248-249` 明写 A/B/D 不被 ⑤ 改写；L1172/L1293 把义务限定在 C 类；补它属过度规格化）。

**D-A1-03（BLOCK 缺格载体是 HARD 红线指标 → 与 `dsm/redline.py:330` 数学上不可能共存）**
- L1134：`| missing_rule | 缺数据处置：ZERO / SKIP / IMPUTE_MEDIAN / BLOCK |`
- L1184：`| waiver_allowed | 是否允许例外豁免（允许则**必须有审批留痕**，无留痕视为未豁免） |`
- L1411（G-09）：`missing_rule 四种分支各有一个真实缺格`
- `dsm/redline.py:326-332`：`if fact_row is None: raise RedlineInputError('红线指标缺事实行，不得默认未触发（V-14）: ' ...)`
- `fixtures/input/redline.jsonl` 第1/2行：`M_CONTACT_FREQ_PER_30D` 与 `M_COMPLAINT_RATE` **全是 HARD**
→ 两个 `BLOCK` 规则指标全是 HARD 红线指标 ⇒ 「BLOCK 分支需真实缺格」与「红线指标不得缺事实行」不可同时满足。

## 2. 🔴 ORCH-29 第5条 D-A1-03 前提失效的纠错声明（ADR 必含项 5 / ORCH-37 第1条追认）
ORCH-29 第5条要求「补 2026-Q3 缺失事实格（含 HARD 红线指标）」。**该前提已被证伪**：
1. 那 4 个缺格不是疏漏，而是 `dsm/fixtures_gen.py:136-141 OMITTED_FACTS` 的**刻意 G-09 四分支构造**（一格一分支、精确覆盖 L1134 的四个枚举值）；
2. **B1b（`996e1c3`）正是靠这 4 格才把 G-09 转绿**；照 ORCH-29 字面补格 ⇒ 四分支塌缩为三分支 ⇒ G-09 打回红（违 V-14：不得为通过测试而弱化既有绿测）；
3. 且补格无法解决死锁：两个 `BLOCK` 指标全是 HARD 红线指标。
∴ 主控 **ORCH-37 第1条追认采 §4.4**：`M_COMPLAINT_RATE ↔ M_SATISFY_SCORE` **同维（EXPER）对调 `missing_rule`** + BLOCK 洞迁到 `S-008/v1/M_SATISFY_SCORE`。此为**主控对 ORCH-29 的自我纠错**，与 ORCH-30 撤回 ORCH-29 第3条同一先例。`level2_weights.EXPER = {M_COMPLAINT_RATE:"0.40", M_CONTACT_FREQ_PER_30D:"0.40", M_SATISFY_SCORE:"0.20"}` **一字未动**（L1259 不得拟定权重）。

## 3. 实际改动（5 处，全在 `dsm/fixtures_gen.py`；`git diff --stat` 仅此一个 dsm 文件）
| # | 位置 | 改动 |
|---|---|---|
| 3.1 | 常量区（原 L77 后） | 新增 `SYNTH_WHATIF_RUN_ID='WIF-SYNTH-2026-01'`、`SYNTH_ALT_METHOD_NOTE='SYNTH-ALT-METHOD: DID 双重差分，假设为处理组与对照组平行趋势'`、`SYNTH_AHP_SEGMENT`（10 字段） |
| 3.2 | `weight_version()` | `'provenance': None` → 完整 7 键 provenance（kind/ahp/whatif_run_id/approved_by/approved_date/effective_from/effective_to） |
| 3.3 | `METRICS` 表 | `M_COMPLAINT_RATE`：`BLOCK`→`IMPUTE_MEDIAN`；`M_SATISFY_SCORE`：`IMPUTE_MEDIAN`→`BLOCK` |
| 3.4 | `OMITTED_FACTS` | 第4条 `M_COMPLAINT_RATE`→`M_SATISFY_SCORE`（S-008/v1 载体不变）+ 注释改写 |
| 3.5 | `design_card()` / `design_card_rows()` | 新增 kw `alt_note=None`；`'alt_method_note': alt_note`；`elif ev=='B'` 分支 `alt_method_note=alt_note or SYNTH_ALT_METHOD_NOTE`；`design_card_rows()` 对 `EVIDENCE_INTENT[sid]=='B'` 传 `alt_note`。**`interpretation_limit` 一律未动** |

`maxlen = 116`（≤ A1b 既有上限 116）。幂等定点替换（每条 `assert src.count(old)==1`），脚本 `dsm_stage/A1c/apply.py`。

### 3.1 `PLACEHOLDER-A1C-01` 的解决（ORCH-37 第5条）
走 spec 路径 1：`ahp` 段**数值逐字复用** `tests/test_models_provenance.py:62-84 AHP_SNAPSHOT`（仓库既有合成载荷，**非本包拟定**，R-12）；标识符改为本 fixtures 的 `SYNTH-` 命名约定（`SYNTH-EXPERT-01/02`、`SYNTH-M-001/002`）。
**逐字段声明：全部为合成值、待业务签认，不得冒充业务真值、不填 K-01~K-20。**
`kind='AHP_ONLY'`（三者中要求最少，`dsm/config.py:1231-1232`；先例 `tests/test_preflight.py:33`）。`whatif_run_id='WIF-SYNTH-2026-01'`（合成；满足 `dsm/whatif.py:309-315` 三条，不落 `PLACEHOLDER_TOKENS/PREFIXES`，`dsm/config.py:84-85`）。
**对 spec §3.4 的一处改进（已核）**：`provenance.effective_to` 用形参 `eff_to` 而非硬编码 `date(2026,12,31)`，使 `G11_stale_weight`（doc `effective_to=2026-06-30`）的 provenance 与文档级自洽；实测 G-11 仍只走 STALE 分支。

### 3.2 `PLACEHOLDER-A1C-02` 的实测结论（G-14 安全）
`design_card_rows(downgrade_to_c=C_SHARE_UP_IDS)` 走 `eff='C'` → `design_card(...,'C')` → `eval_method='OBSERVATIONAL_ONLY'`、`control_arrangement='NONE'`、`interpretation_limit='SYNTH-LIMIT: 变体降级为 C 类'`。补 note 后**三张卡实测仍判 C**（`dsm/evidence.py:225` 的 ③ 要求 `eval_method ∈ QUASI_METHODS`，note 在 C 卡上惰性）。
**G-14 的 C 类降级仍成立，未被破坏。** note 按**声明意图** `EVIDENCE_INTENT` 补（spec §5.3 逐字），故变体卡带上该 note 但不改判定。

## 4. BEFORE / AFTER sha256 全表（ADR 必含项 2）
**⚠️ 实测为 10 变 / 7 不变，非 spec §8 Step 4 预期的 11 变 / 6 不变。**
`fixtures/golden/golden_map.json` **逐字节未变**：`tools/gen_golden.py` 的 G-09 probes 与 `hand.branch_map` 是**硬编码字面量**（`tools/gen_golden.py:179-187`：`('S-008','M_COMPLAINT_RATE')`、`BLOCK->S-008 M_COMPLAINT_RATE`），且它引用的 `fg.*` 常量（`EVAL_PERIOD/NO_TARGET_SUBJECT/EXTREME_STRATEGY/ANCHOR_SET_ID/WEIGHT_VERSION_ID/OAT20_WEIGHT_VERSION_ID/DOMINANT_METRIC`）**无一被 A1c 改动**。spec §8 Step 4 注「golden_map 会变是因为 gen_golden 会重算 probes/hand」**经实测证伪**。
∴ golden_map 的 G-09 载体修正**必须由 E2b 改 `tools/gen_golden.py:179-187`**（A1c 禁写 `tools/**`）；**不得手改 `fixtures/golden/golden_map.json`**——它是生成物，手改会在下次重生成时被覆盖并破坏「冻结件可由生成器复现」不变量。

| 路径 | BEFORE bytes | BEFORE 行数 | BEFORE sha256（全 64 位） | AFTER bytes | AFTER 行数 | AFTER sha256（全 64 位） | 变? | 变更原因 |
|---|---|---|---|---|---|---|---|---|
| `fixtures/golden/golden_map.json` | 22130 | 775 | `dcfffd6a657b4d029d526c3fb5a2ea48e7b9dc4f5825d22efbf91191920a6cfd` | 22130 | 775 | `dcfffd6a657b4d029d526c3fb5a2ea48e7b9dc4f5825d22efbf91191920a6cfd` | ❌ 不变 | 未变（见上方说明） |
| `fixtures/input/anchor_set.jsonl` | 210 | 1 | `a3f8385e788c376d843d3b8606a013cc96e04024322661c5a971dfc0579582c0` | 210 | 1 | `a3f8385e788c376d843d3b8606a013cc96e04024322661c5a971dfc0579582c0` | ❌ 不变 | §6-C.2 锚定覆盖无缺陷，不得改 |
| `fixtures/input/design_card.jsonl` | 8902 | 13 | `6a3c39dff04b53c263e6cdd26c535d745c67734f9e51a6cb6cf5aa0b787713ac` | 9210 | 13 | `db65d61cfc4952feff42506a0b06a55c7cf616be0ed8159e87f5487b5a222ab3` | ✅ 变 | §3 D-A1-02 四张 B 卡补 alt_method_note |
| `fixtures/input/grade_rule.jsonl` | 1037 | 4 | `aae583eda395ffdfd5d07c97dbbca7549b6b6ade7a8862561a8c2f4c6d775ef2` | 1037 | 4 | `aae583eda395ffdfd5d07c97dbbca7549b6b6ade7a8862561a8c2f4c6d775ef2` | ❌ 不变 | — |
| `fixtures/input/metric_dict.jsonl` | 9144 | 15 | `30a2502838b4984eae6cada1db1ccfe875718188ca9920dd0698e13e1e18475e` | 9144 | 15 | `a55e5c5822272c967ccc86cb24d4326ba474e997b507e5c2b68bcc4076ce4a11` | ✅ 变 | §2 D-A1-03 missing_rule 同维对调 |
| `fixtures/input/metric_fact.jsonl` | 273549 | 896 | `5fd7442f79ef9046a1bd09280dd99e3f4ddb2e45f38a0f47dda2a89f376296e2` | 273548 | 896 | `05efc9197fd265acd8a694ae7f93ed45afa5af01a8c7e3261df538dbb7a11900` | ✅ 变 | §2 D-A1-03 BLOCK 洞迁至 S-008/v1/M_SATISFY_SCORE |
| `fixtures/input/redline.jsonl` | 547 | 3 | `776d78525995ffe1d0bbc8e0893dd1cf88d1b4120a5f4d163552e738ed204e59` | 547 | 3 | `776d78525995ffe1d0bbc8e0893dd1cf88d1b4120a5f4d163552e738ed204e59` | ❌ 不变 | 红线阈值属治理配置，A1c 不动 |
| `fixtures/input/strategy_master.jsonl` | 4050 | 13 | `273ce1f746108a2d4e6f0ffb2aeb33968ea86db7c398cd8b80cb9a017c48e677` | 4050 | 13 | `273ce1f746108a2d4e6f0ffb2aeb33968ea86db7c398cd8b80cb9a017c48e677` | ❌ 不变 | §6-B.3 S-005/v1 不补事实、不删卡 |
| `fixtures/input/weight_version.jsonl` | 743 | 1 | `b403bfbced929c6863eb57a95d4926f8893fa451387388574655bade82b70a27` | 1465 | 1 | `83e9c0268347746e856baafe169466f2ede04769c0caa9831d21d91ab5c1ffbc` | ✅ 变 | §3 D-A1-04 provenance 补齐 |
| `fixtures/manifest.json` | 4716 | 171 | `b9e4a71ff6ccefdac0741b2935074e4ed4a9c28082440a3c4cba6ceebe4ff654` | 4717 | 171 | `6f7beed63ca104c97bc184158be376a488c0ccb5071a644d0842b72b4a346604` | ✅ 变 | 内嵌 files.sha256 随载体变 |
| `fixtures/negative/G11_money_non_integer.json` | 628 | 23 | `6071e7a2cd2a3f3f57c5bdd73a88689804e73692411d9e3626c01eeff96c469f` | 628 | 23 | `6071e7a2cd2a3f3f57c5bdd73a88689804e73692411d9e3626c01eeff96c469f` | ❌ 不变 | — |
| `fixtures/variants/G04_target_missing.json` | 7722 | 219 | `83bd2b5c1097c9043c16fd42931e9b7307eed2b6280b7f282eb939bc82f7b783` | 7722 | 219 | `ab15a7498e75c6dfa153013fc9b6bc9c102a59e4dbc07762bd0e862663a03fe5` | ✅ 变 | 内嵌 metric_dict replace 集含对调的两指标 |
| `fixtures/variants/G05_append_extreme.json` | 8291 | 271 | `eaae9cfb1b2c62ea4fb0b4ef385e650e66f8f700ed3e96b802a2bcd71bb6d23e` | 8368 | 271 | `c7e0f6f2c146e1655e2d5d8bb979fcd837f9b11a705eb93467e3fa31ba1226de` | ✅ 变 | 内嵌 S-901 design_card（EXTREME_STRATEGY 声明 ev=B）补 note |
| `fixtures/variants/G06_weight_oat20.json` | 1505 | 58 | `10986ae79aeafc0ff90e43bf9d6a661d53abc122ec32d784a346c14372612b96` | 2979 | 107 | `3a9ac9106fa87817f166471f8c62bd3347d6a8a18c8c33cc2cd7f40497f27830` | ✅ 变 | 内嵌 weight_version append（provenance） |
| `fixtures/variants/G10_dim_emptied.json` | 1075 | 35 | `4ef16ca47e430ca4aafa0479d29bcdb8f1e9df7f935c5ce2d7773168b02cdc7b` | 1075 | 35 | `4ef16ca47e430ca4aafa0479d29bcdb8f1e9df7f935c5ce2d7773168b02cdc7b` | ❌ 不变 | D-SPEC-G10 归主控（ORCH-35） |
| `fixtures/variants/G11_stale_weight.json` | 1500 | 58 | `d76fae33b608f7d4ea893f58adad6af43ece75dd62b82da806c823c3fc9fc56d` | 2974 | 107 | `7f9a3162bf379ab1f2f88e2b027e87a0efec23f9603890ec04e93e4c61296ac2` | ✅ 变 | 内嵌 weight_version replace（provenance，eff_to=2026-06-30 自洽） |
| `fixtures/variants/G14_c_share_up.json` | 3195 | 105 | `2fafad6dba75c322caef249d4e2150b069d5a17d60b0969aa16b9786ba13171f` | 3426 | 105 | `5ad6206dbcf138abb3afe2f7b11a8778ca1dcaf9aad6fd00cfa2fba494e20068` | ✅ 变 | 内嵌 design_card replace 集带 note（判定仍 C，§3.2） |

**合计 17 文件：10 变 / 7 不变（实测）。**
**变（10）**：`weight_version.jsonl`、`design_card.jsonl`、`metric_dict.jsonl`、`metric_fact.jsonl`、`manifest.json`、`G04_target_missing.json`、`G05_append_extreme.json`、`G06_weight_oat20.json`、`G11_stale_weight.json`、`G14_c_share_up.json`。
**不变（7）**：`golden/golden_map.json`、`input/anchor_set.jsonl`、`input/grade_rule.jsonl`、`input/redline.jsonl`、`input/strategy_master.jsonl`、`negative/G11_money_non_integer.json`、`variants/G10_dim_emptied.json`。
> 越界自检：`redline.jsonl` / `strategy_master.jsonl` / `grade_rule.jsonl` / `anchor_set.jsonl` **均未出现在 delta**（spec §8 Step 4 的硬边界）→ 补丁未越界。
> `manifest.json` 补齐 `PLACEHOLDER-A1CPREP-01`：BEFORE = **4716 字节 / 171 行**；`golden_map.json` 实为 **22130 字节 / 775 行**（spec §1 表记「1 行」有误）。

## 5. 新旧 `reproducibility_hash` 双记（ADR 必含项 3 / ORCH-30 第5条 + ORCH-32/33）
| 项 | 值 |
|---|---|
| **新哈希（A1c 后，连跑两次精确相等，len=64）** | `e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d` |
| 第 1 次 / 第 2 次 | 同上 / 同上 → **`HASH_EQUAL_TWICE True`**（V-3 / G-12 / L1640「必须精确相等」） |
| 旧哈希（P3b-prep `d228edd` 实测，HEAD `82d5a6a`） | `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7` → **`superseded_by_A1c`** |
| 更早旧哈希（SP-1 冻结期，评价期 2026-Q2） | `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` → **`superseded_by_A1c`** |
| 取法 | `dsm_stage/A1c/hash_probe.py` → `tests/test_integration_spine.py:146 _run_chain(root, PERIOD)['reproducibility_hash']`（九步真跑，`dsm/audit.py:242`） |
| ⚠️ 取数时的树状态 | HEAD `ac12ed5`；工作树含**他包在飞**脏：`dsm/attainment.py`(ATT-1)、`dsm/cli.py`(P2-cli)、`dsm/evidence.py`(EVID-1)、`tests/test_evidence.py`。**本哈希是「A1c fixtures + 上述在飞实现」的联合产物**，ATT-1/EVID-1/P2-cli 落地后必再变 → P3b 的最终判据须在三包全部落地后重测（ORCH-30 第5条：不得只报其一，故三值并列）。 |
| **严禁「修回」旧值** | 复现哈希**必变**（ORCH-30 已预声明）。A1c 未做任何试图复现旧哈希的动作。 |

## 6. 证据分布双口径（ADR 必含项 4 / ORCH-37 第3条）
| 口径 | 定义 | A | B | C | D | 合计 |
|---|---|---|---|---|---|---|
| **主体级 `evidence_distribution`** | 12 个 `strategy_id`（`EVIDENCE_INTENT`，S-005 v1/v2 同类合并） | 3 | 3 | 4 | 2 | **12** |
| **行级 `evidence_distribution_rowlevel`** | 13 张设计卡（S-005 v1+v2 分计，G-08 版本断点载体） | 3 | **4** | 4 | 2 | **13** |

- 主体级 = `manifest.evidence_distribution` = 原文 **L1459** `A×3、B×3、C×4、D×2` = `intended_evidence_class`（`dsm/fixtures_gen.py:497-500` 以 `strategy_id` 为键 → 12 项）。
- 行级 `A3B4C4D2` 的 B=4 = `S-004/v1`、`S-005/v1`、`S-005/v2`、`S-007/v1`（四张 DID 卡）。派工单的 `A3B0C4D6` 是**修前行级**计数，与主体级不矛盾。
- **Step 5 隔离目录断言实测（`dsm_stage/A1c/assert_regen.py`，未落 `fixtures/` 即验完 6 组，全过）**：`ROWLEVEL {'A':3,'B':4,'C':4,'D':2} 13` / `SUBJECT {'A':3,'B':3,'C':4,'D':2} 12` / `Q3 pairs 12` / `Q3 HOLES 4 [('S-005','v2','M_CAMPAIGN_COST_MINOR'),('S-006','v1','M_CUST_GAIN'),('S-008','v1','M_SATISFY_SCORE'),('S-011','v1','M_ROI')]` / `metric_fact rows 896` / `ALL 6 ASSERT GROUPS PASS`。
  另：12 个本期 pair 的**三条红线指标事实行全部齐备**（`dsm/redline.py:330` 死锁已解）；`G05_append_extreme.json` 的 `M_AUM_MINOR` 仍为 `10000`（零变异构造 L1460 未被误修）。
- **对 spec §8 Step 5 组3 期望的一处更正**：实测 `MISSING_RULE COUNTS = {'BLOCK':2,'IMPUTE_MEDIAN':3,'SKIP':4,'ZERO':6}`，**与改前完全相同**（改前 BLOCK = `M_COMPLAINT_RATE`+`M_CONTACT_FREQ_PER_30D`，IMPUTE_MEDIAN = `M_ROI`+`M_SATISFY_SCORE`+`M_RETENTION_RATE`）。spec 注「对调后 BLOCK 只剩 1 个、IMPUTE_MEDIAN 变 2 个」**漏数了 `M_CONTACT_FREQ_PER_30D`(BLOCK) 与 `M_RETENTION_RATE`(IMPUTE_MEDIAN)**，属 spec 计数错误。∴ `golden_map` G-09 的 `{"m":{"missing_rule":"BLOCK"},"n":1}` 与 `{"m":{"missing_rule":"IMPUTE_MEDIAN"},"n":1}` **在 A1c 之前就已与数据不符**，不是 A1c 造成的失效；仍须 E2b 一并修正（连同 §4 的载体字面量）。

## 7. §6-B.4 逐类计数验算表 + 三个实测数（ADR 必含项 7 / ORCH-37 第6、9条）
**实测环境：HEAD `897cad1`**（EVID-1 已落地）。脚本 `dsm_stage/A1c/counts.py`，输入 = 落盘后的冻结 fixtures，`dsm.evidence.classify(cards, 2026-Q3 facts, params=tests.test_golden_a.EV_PARAMS)`：

| 量 | 期望（spec §6-B.4） | **实测** | 结论 |
|---|---|---|---|
| `evidence.classify` 出桥行数 | 13（spec 观测时刻） | **12** | ⚠️ **13 → 12**：EVID-1（`D-EVID-01`，ORCH-37 第9条新立）**已落地**并按评价期事实范围过滤设计卡，`S-005/v1`（`RETIRED` / `offline_date=2026-06-30` / 本期无事实行）不再出桥。**如实记录：观测值 12、观测时 HEAD `897cad1`。** fixtures 侧未做任何改动来消除 13（§6-B.3：不补事实、不删卡）。 |
| **证据结构**（L1003 / L1063⑥，分母 = 本期评价范围 pair） | 12 = `A3 B3 C4 D2` | **12 = {'A':3,'B':3,'C':4,'D':2}** | ✅ 精确成立，与 `manifest.evidence_distribution` 与 L1459 三处自洽 |
| **占比双报**（L1346 NOT_ASSESSED 单列后） | 11 = `A3 B3 C3 D2` | **11 = {'A':3,'B':3,'C':3,'D':2}**（S-008 单列） | ✅ 精确成立，与 spec 预测「改后 pooling 应报 `A3 B3 C3 D2 = 11`」逐字相符 |

**§6-B.4 逐类计数验算表（原样附，主体 = 2026-Q3 有事实的 12 个 pair）**

| subject | biz_domain | 改后证据类 | NOT_ASSESSED? | 计入证据结构(分母12) | 计入占比双报(分母11) |
|---|---|---|---|---|---|
| S-001/v1 | CARD | ② **A** | 否 | ✅ A | ✅ A |
| S-002/v1 | CARD | ② **A** | 否 | ✅ A | ✅ A |
| S-003/v1 | CARD | ④ **C** | 否 | ✅ C | ✅ C |
| S-004/v1 | LOAN | ③ **B**（note 已补） | 否 | ✅ B | ✅ B |
| S-005/v2 | LOAN | ③ **B**（note 已补） | 否 | ✅ B | ✅ B |
| S-006/v1 | LOAN | ④ **C** | 否 | ✅ C | ✅ C |
| S-007/v1 | WEALTH | ③ **B**（note 已补） | 否 | ✅ B | ✅ B |
| **S-008/v1** | WEALTH | ④ **C**（实测 bridge 值 = C） | **是**（`M_SATISFY_SCORE` 缺格 + `missing_rule=BLOCK` → 不产出分数） | ✅ C | ❌ **单列** |
| S-009/v1 | WEALTH | ② **A** | 否 | ✅ A | ✅ A |
| S-010/v1 | PAY | ① **D**（卡 MISSING） | 是（证据致） | ✅ D | ✅ D（读法甲） |
| S-011/v1 | PAY | ④ **C**（PARTIAL → 上限 C） | 否 | ✅ C | ✅ C |
| S-012/v1 | PAY | ⑤ **D**（C 无 limit） | 是（证据致） | ✅ D | ✅ D（读法甲） |
| **合计** | — | — | 3 | **A3 B3 C4 D2 = 12** | **A3 B3 C3 D2 = 11** |

**ORCH-37 第6条裁决登记（占比双报分母 = 11，读法甲）**：证据结构四类**全给**、`NOT_ASSESSED` **另附明细**（L1063⑥ `A/B/C/D 计数与 NOT_ASSESSED 明细` 分列）；只排除**非证据致**不出分者（S-008）。理由：若取 9 则 D 类计数恒 0，**L1459**「确保四类路径都被走到」失去意义；且 **L1292**「台账单独计数」= 另立计数器，非从四类计数里扣掉。

> **🔴 双来源交叉验证（ORCH-37 第6条要求点明）**：本裁决与 **ORCH-36 第2条**独立得出的「占比双报分母 = **11**、依 **L1004** 剔 `NOT_ASSESSED`」**完全一致**。两条裁决由不同 lane、不同原文入口（L1063⑥/L1346 vs L1004）分别推出同一分母 → 构成**双来源印证**，非孤证。
> **读法乙（分母 9）已驳回**，但如实登记其原文张力：L1292/L1346 严格字面下 S-010/S-012 也该单列。

**ORCH-37 第7条裁决登记（G-14 分子 = 「C 类占比」，不采 C+D）**：SDD **L1416** 是唯一明文且写「C 类占比」；「C+D」逐字原文**未找到**。A1CPREP 曾引 `dsm/reason_codes.py:86` 的 message「一级库中低证据等级占比上升」为据倾向 C+D —— 主控认定该 message 是**实现侧自撰**，以其为据属**循环引证**，不构成原文依据。且若度量 C+D，则 D→C 搬运时 `(C+D)` 恒 `8/11` 不变，守护点对其声称要防的情形**完全失效**，违 V-14。
→ **A1c 未为此做任何事**（落地在 **G14FIX**）。**登记待办**：`dsm/reason_codes.py:86` 的 message 需更正为「**C 类证据占比上升**」，归 **P2-wire**。
## 8. §6-C 锚定覆盖矩阵结论 + 7 步证据链（ADR 必含项 8 / ORCH-37 第8、10条）
**A1c 声明：全程未动 `dsm/attainment.py`、`dsm/normalize.py`、`dsm/pooling.py`、`dsm/models.py`、`dsm/evidence.py`、`tests/**`、`tools/**`。**（`git diff --stat` 中 A1c 只贡献 `dsm/fixtures_gen.py` + `fixtures/**` + 本 ADR。）
- **D-A1-08 根因结论：锚定集无缺陷。** `fixtures/input/anchor_set.jsonl`（8 名成员，2026-Q3 出值 7 名）**sha256 未变**。15 指标覆盖矩阵实测：唯一退化（sd=0）者是 `M_AUM_MINOR`，那是 **L1460** 原文强制的零变异构造（走 `INACTIVE_METRIC` 剔除，**不是**回退池内尺度）；`M_ROI`/`M_COMPLAINT_RATE`/`M_CAMPAIGN_COST_MINOR` 三个 7/8 覆盖指标锚定 min≠max、样本 7 ≥ `min_pool_size`，**均不满足 L941「锚定集失效」条件**。→ **E3「anchor_set 覆盖不足或取值退化 → 被迫回退池内尺度」的假设经覆盖矩阵实测证伪。**
- **真根因（7 步证据链，spec §6-C.3）**：`IMPUTE_MEDIAN` 的中位数取自**当期池**（G-05 变体追加 S-901 使 `M_ROI` 池由 11 → 12 个、中位数 `0.100 → 0.1015`），故存量 `S-011/v1` 的 norm/composite 被改写（`0.967705891652 → 0.968545891652`）→ 与 **L1407**「存量全部策略…完全不变」结构性冲突。
- **ORCH-37 第8条裁决登记**：插补参考集**取自 `anchor_set`**，失效时回退当期池 + `ANCHOR_SET_STALE`，与 **L941** 同口径（原文缺口 **L1134** 只给枚举名、零字规定参考集 → 记 **ERRATUM-08**）。**落地在 ATT-1（已在飞），不归 A1c。**
- **ORCH-37 第10条裁决登记**：D-A1-08 落地包 = **新立 ATT-1**，**不并入 MODELS-1**（MODELS-1 预算与范围已饱和，写集零交集）。
- `PLACEHOLDER-A1CPREP-06`（残差 `Δatt` 0.01 vs 0.015）**仍 OPEN**，归 ATT-1 精确对账，A1c 不下数值结论。

## 9. 双来源印证（ADR 必含项 9）
D-A1-04 由两个**互不相关**的 lane 独立撞到同一根因：
1. **C2b**（`dsm_stage/C2b/diag_c08.py`，ORCH-30 第3条采纳）：用冻结 fixtures 对 **2026-Q1/Q2/Q3 三期真跑**，三期完全一致 —— 唯一 `blocks_run=True` 的是 **C-01 `WEIGHT_MISSING_WHATIF_RUN_ID`**；C-08 的 `EVIDENCE_CARD_MISSING`(S-010)/`EVIDENCE_CARD_PARTIAL`(S-011) 均 `blocks_run=False`。
2. **E3 GAP-E3-05**（E3 `35a6635`，ORCH-33 转达）：独立确认「冻结权重文档 T**6** `provenance=null` → C-01 在冻结件上必 BLOCK」。（E3 原文写作「T7」属**笔误**：权重表在 **L1104 / L1186-1194** 是 **T6**，T7 是 `grade_rules`（**L1105 / L1196-1206**）。本 ADR 按 **T6** 记，并把该口径差登记进 spec 附录 A 清单。）

→ 与 ORCH-29 第5条「两个独立 lane 互相印证同一批 fixtures 缺陷，故认定非误报」同构。**实现照原文正确、是数据违约，故不得降为 WARN（V-14）。**
**修后实测印证**：`tests/test_integration_spine.py::test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures` 由 **RED → GREEN**，即主流程已能走到 **L1322** 的 `status=PASS/WARN` 右支。

## 10. D-A1-05（CSV 化）· ORCH-37 第2条：本包不做，**仍 OPEN**，拆出为 A1d（条件执行）
**🔴 实测结论：当前有且仅有 1 条红测试是「专门」因 JSONL 容器/格式而红 → 依 ORCH-37 第2条，A1d 必须执行。**
- 该测试 = **`tests/test_integration_spine.py::test_step1_io_loaders_loads_the_frozen_design_card_table`**（BEFORE / OTHERS-ONLY / AFTER 三次跑**均 RED**，A1c 未使其变化）。
- 其 docstring 自陈两条同源于「容器格式」的原因：① `dsm/io_loaders.py:182-190 read_table` 只认 `.csv`/`.parquet`，其它后缀 → `CoercionError MISSING_FILE`；`_resolve`（`dsm/io_loaders.py:274-279`）的后缀元组也不含 `.jsonl` → **冻结的 JSONL 容器一张表都读不了**（该测试自行 `_write_csv` 转换绕过，见 `tests/test_integration_spine.py:120-131 _stage`）；② 转成 CSV 后 `design_card.jsonl` 第 11/12 行（S-010 `card_status=MISSING`、S-011 `PARTIAL`）的 `success_criteria` 是**空串**，被 `NULL_LITERALS` 判成 `None`，而 `models.DesignCardRow.success_criteria` 是必填 `str` → `DataLoadError`（`kind=MODEL_ROW_REJECTED`，属 `BLOCKING_KINDS`）→ **T4 永远加载不出来**。
- ⚠️ **②不是纯格式问题**：CSV 化本身不解决 `'' → None` 的语义差。A1d 必须同时裁「fixtures 侧不用空串」或「`io_loaders` 的 `NULL_LITERALS` 口径」或「`models` 放宽 `success_criteria` 为可空」，否则 A1d 做完该测试仍红。**A1c 不代裁。**
- **确切改动面（含目录布局，ORCH-37 第2条要求）**：
  - `dsm/fixtures_gen.py`：`write_bundle`/`to_jsonl` 序列化改 CSV；**目录布局须由扁平 `fixtures/input/` 改为 `data/<period>/`（T1/T3/T4）+ `config/`（T2/T5/T6/T7/T8）**，依据 **L888** `按 period 读取 data/<period>/ 下的 T1/T3/T4，读取 config/ 下的 T2/T5/T6/T7/T8`；
  - `dsm/io_loaders.py:274-279` `_resolve` 的目录/后缀解析（L888）；
  - `fixtures/**` **17 文件全部重写**；`tools/gen_golden.py`、`tools/normalize.py`（若按后缀分派）；
  - `tests/test_fixtures.py`（28 条全读 JSONL，须全改）、`test_golden_a.py`/`test_golden_b.py`（`_jsonl()` 载体读取）、`test_integration_spine.py:120-131 _stage`（其 `_write_csv` 绕过层可删）、`test_io_loaders.py`（新增 CSV 端到端）。
  - **数值不需重算**（表内容一字不变，只换容器）；但 17/17 sha256 全变、复现哈希必再变。
- **裁决依据（spec §6.5，逐字判定成立）**：M21（**L884-893**）与 M18（**L1102 / L1158-1174**）**均未规定任何文件格式、尤其均未规定 JSONL** → 触发 ORCH-29 第5条第2点前半支 → **改 fixtures 格式，不立 C1c**。旁证：**L1251** `| metric_dict.csv | …`、**L1220-1226** 输出侧明写 CSV/MD/JSON；契约全文 `grep -i jsonl` **零命中**。
- **时序（spec §6.7）**：A1c（数据）→ E2b/E3b（golden 手算对齐）→ 全绿后再 A1d（容器迁移）。**若与数据修正同批做，AFTER 17/17 全变、golden 归因无法分离**，违 ORCH-29 第5条第4点。
- **ORCH-38（HEAD `ac12ed5`）已记「A1d 触发条件已满足必须执行且范围收紧（目录布局迁移不在内）」** —— 与本节实测结论一致；但**范围收紧与 L888 的目录布局要求存在张力**（`_resolve` 按 `data/<period>/` 找文件），请主控在派 A1d 时明确该张力如何处置。A1c 不代裁。

## 11. D-A1-06 · 🔴 R-14 硬边界遵守登记（只登记、不代填）
**A1c 未对 `golden_map.json` 做任何写入**（该文件 sha256 逐字节未变，见 §4）。派工单点名的 §6-A D-A1-06 修正**只登记**：

| 项 | 现值（`golden_map.json` G-05 `hand`） | **应改为** | 手算依据 | 原文行号 |
|---|---|---|---|---|
| `hand.dim_CONTRIB` | `1.900000` | **`1.810000000000`** | `CONTRIB = 0.80×1.9(M_REV_MINOR 19000/10000) + 0.10×1.0(M_AUM_MINOR 10000/10000) + 0.10×1.9(M_CUST_GAIN 190/100) = 1.52 + 0.10 + 0.19 = 1.81`（纯有理数精确）。`M_AUM_MINOR` 恒 10000 = target 是 **L1460** 强制的零变异构造，**不得改** | **L1407**（G-05 只写「attainment **极高**」，无任何数值）；**L1460**；**L943**；**L1446** |
| 综合分 | `1.5346` | **`1.507600000000`** | `Δcomposite = level1(CONTRIB) × ΔCONTRIB = 0.30 × (1.9 − 1.81) = 0.30 × 0.09 = 0.027`；`1.5346 − 0.027 = 1.5076` → 差异**只**来自 CONTRIB 一维，其余五维两侧一致 | **L1342**（Step5）；**L1407** |
| `hand.extreme_attainment` | `"1.900000（+1 指标）/ 1.000000（-1 指标）"` | 须反映 `M_AUM_MINOR` 达成率 **1.0**（措辞由 E3b 定） | spec §6-A.3 | **L1407** |
| `value_status` | `SPEC（需两次运行对比，期望值不预填）` | `SPEC+HAND_COMPUTED` | E3 已完成手算 | — |

> **`1.900000` 在原文中只挂在 G-03（L1405：`CONTRIB 维度 attainment = 1.9（接近 cap）`，说的是 S-009 的维度值）**；把它搬到 G-05 的 `hand` 属**跨用例串味、无原文依据**。**归 E3b 独立手算落笔，A1c 不代填（R-14）。**
> ⚠️ **D-A1-06 与 D-A1-08 必须分开归因**（spec §6-C.5）：只改 hand 值不会让 `expects.existing_norm_composite_grade = "完全不变"` 变绿（那要 ATT-1 修 `dsm/attainment.py`）；只修 attainment 也不会让 hand 的 1.9 对上。

## 12. Step 7 回归（本包 + 受影响邻包，**未跑全量** —— ORCH-29 第6条 / L-04②）
命令口径（L-07：`pyproject.toml` 的 `addopts` 已含 `-q`，**不再叠 `-q`**）：
`/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=no --continue-on-collection-errors tests/test_fixtures.py tests/test_models_provenance.py tests/test_config_weight_version.py tests/test_preflight.py tests/test_evidence.py tests/test_attainment.py tests/test_redline.py tests/test_golden_a.py tests/test_golden_b.py tests/test_integration_spine.py`
（spec §8 Step 7 写的 `tests/test_methods_evidence.py` / `test_methods_attainment.py` / `test_methods_redline.py` **在本仓库不存在**，实为 `test_evidence.py` / `test_attainment.py` / `test_redline.py`，已按实名执行。）

**⚠️ 归因基线的必要性**：A1c 执行期间他包在飞（ATT-1 改 `dsm/attainment.py`、EVID-1 改 `dsm/evidence.py`、P2-cli 改 `dsm/cli.py`），HEAD 由 `a3a4701` → `ac12ed5` → `897cad1`。故 A1c **额外做了一次「同 HEAD + 同在飞脏、只回退 A1c 写集」的对照跑**（`git checkout -- dsm/fixtures_gen.py fixtures` → 跑 → 复原；复原后 sha256 校验 `RESTORED_EQUAL`），使红/绿变化可**干净归因于 A1c**。

| 跑 | failed / passed |
|---|---|
| BEFORE（HEAD `a3a4701` + MODELS-1 在飞脏，A1c 未动手） | **11 failed / 495 passed** |
| **对照 OTHERS-ONLY（HEAD `ac12ed5` + ATT-1/EVID-1/P2-cli 在飞脏，A1c 写集已回退）** | **12 failed / 497 passed** |
| AFTER（同树 + A1c 落盘） | **15 failed / 494 passed** |

### 12.1 由 A1c 修好（RED → GREEN，共 **7** 条；以 OTHERS-ONLY 为基线）
| 测试 | 归因 |
|---|---|
| `test_integration_spine::test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures` | **D-A1-04**：C-01 恒 BLOCK 解除，主流程走到 L1322 右支（**主流程唯一真阻塞已解**） |
| `test_integration_spine::test_step3_evidence_covers_the_m34_a3b3c4d2_distribution` | **D-A1-02**：证据分布达 L1459 的 `A3B3C4D2` |
| `test_integration_spine::test_step4_redline_runs_on_the_frozen_eval_period_fact_table` | **D-A1-03**：`dsm/redline.py:330` 死锁解除 |
| `test_golden_a::test_g04_target_missing_caps_grade_to_l3_for_every_k06_candidate` | D-A1-02（S-007 D→B，G-04 subject 由 NOT_ASSESSED → 受评 + 目标封顶） |
| `test_golden_a::test_g08_version_change_marks_break_suppresses_trend_and_resets_streak` | D-A1-02（S-005 v1/v2 D→B；该测试 `:700`/`:724` 本就断言 `evidence_class == 'B'`） |
| `test_golden_b::test_g06_at_least_one_near_boundary_strategy_flips_to_l3` | D-A1-04（权重可加载后 OAT20 扰动链才走得通） |
| `test_golden_b::test_g07_loo_impact_max_is_the_dominant_weight_metric_m_rev_minor` | 同上 |

### 12.2 🔴 **`g09` 仍绿（R5 回滚门未触发）**
`tests/test_golden_a.py::test_g09_missing_rule_four_branches_are_each_other_different` —— **AFTER 仍 GREEN，不在 failed 清单内**。G-09 四分支**未塌**：`ZERO→S-005/v2 M_CAMPAIGN_COST_MINOR`、`SKIP→S-006 M_CUST_GAIN`、`IMPUTE_MEDIAN→S-011 M_ROI`、`BLOCK→S-008 M_SATISFY_SCORE`，四个可观测结果两两不同；`expects.BLOCK = "S-008 不产出分数"` 仍成立（S-008 载体未变）。**G-03**（S-009 三格事实一行未动）/ **G-15**（`S-006 M_COMPLAINT_RATE = 0.007000` 未变）**零影响**；`metric_fact` 行数仍 **896**。→ **无需回滚 R5。**

### 12.3 新增红（**10** 条）· 逐条归因（全部属「测试/golden 把缺陷当成期望」或「口径已由主控改判」；A1c 禁写 `tests/**` 与 golden 数值）
| # | 测试 | 根因 | 归属 |
|---|---|---|---|
| 1 | `test_fixtures::test_golden_trigger_probes[G-09]` | `tools/gen_golden.py:179-187` **硬编码**载体字面量 `('S-008','M_COMPLAINT_RATE')` 与 `hand.branch_map` 的 `BLOCK->S-008 M_COMPLAINT_RATE`；洞已迁到 `M_SATISFY_SCORE` → probe `none:true` 失效。另两条 `{"missing_rule":…,"n":1}` 与数据本就不符（§6 已证 BLOCK=2/IMPUTE_MEDIAN=3，**A1c 之前就错**）。spec §8 Step 5 注**明写**：「A1c **不得**自行改该 `n`，须在交付里显式移交 E2b」 | **E2b**（须改 `tools/gen_golden.py`，**不是**手改 `golden_map.json`，理由见 §4） |
| 2 | `test_golden_b::test_g14_c_class_share_rises_from_four_of_twelve_to_six_of_twelve` | 测试名即写死 `4/12 → 6/12`；ORCH-36 第2条 + ORCH-37 第6条已裁**分母 = 11**、ORCH-36 第1条 + ORCH-37 第7条已裁**分子 = C 类占比** → 应为 `3/11 → 5/11` | **G14FIX + E3b** |
| 3 | `test_golden_b::test_g14_pool_shares_are_reported_in_two_columns_and_step7_is_not_aborted` | 同上（占比双报分母口径） | **G14FIX + E3b** |
| 4 | `test_golden_b::test_g06_flip_rate_is_flipped_over_assessed_and_labels_are_correct` | `flip_rate` 分母 = assessed 集合；S-004/S-005/S-007 由 D（NOT_ASSESSED）→ B（受评）⇒ assessed 集合扩大（spec §9.1 耦合点 3 已预声明此类失效） | **E3b**（派工单记 D-D2-01） |
| 5 | `test_golden_b::test_g10_pending_metric_is_dropped_coverage_falls_and_reason_is_registered` | G-10 属 **D-SPEC-G10**（ORCH-35：原文互斥，`M28 L1286` 清空维度≥2 应 BLOCK 实走 WARN 且 `DIMENSION_EMPTIED` 未出现）；本条随评估范围/coverage 变化而暴露 | **ORCH-35 / E3b**（A1c 未碰 `G10_dim_emptied.json`，其 sha256 **未变**） |
| 6 | `test_integration_spine::test_step2_preflight_block_exit_writes_audit_bundle_and_no_score_card` | 该测试**逐字断言缺陷本身**：`assert ('C-01','WEIGHT_MISSING_WHATIF_RUN_ID') in codes`（`:466`）、`len(result.findings) == 6`（`:468`）、`not_assessed == ('S-005','S-010')`（`:472`）。D-A1-04 修好后该码不再出现、S-005 也不再 NOT_ASSESSED ⇒ 必然红 | **E2b / 主控**（`tests/**` 在 A1c 禁写集内）；BLOCK 出口机制本身仍由 **L1322-1326** 守护，**建议改用 G-11 STALE 或 negative 载荷触发 BLOCK** |
| 7 | `test_integration_spine::test_step6_grading_caps_by_evidence_without_touching_the_score` | 证据类 D→B ⇒ 证据封顶（**L1202** `evidence_class_min`、**L1344** Step6）路径改变 | **E2b** |
| 8 | `test_integration_spine::test_step7_pooling_never_ranks_across_pools` | 池键 `(biz_domain × evidence_class)`（**L942**）成员集变：D 池缩、B 池胀（spec §9.1 耦合点 3 逐字预声明） | **E2b**（与 MODELS-1 已落地的松/严键口径一并对账） |
| 9 | `test_integration_spine::test_step8_sensitivity_flip_rate_reflows_into_step7_gate` | 同 4/8（flip_rate 回流 Step7 门禁的分母与池成员都变了） | **E2b / E3b** |
| 10 | `test_integration_spine::test_l0b_whatif_step_unlocks_when_landed` | **归因未闭环**：疑随 `_run_chain` 上游步骤口径变化而连带，亦可能属 P2-cli 在飞（`dsm/cli.py` 脏）。A1c 未写 `dsm/whatif.py`/`dsm/cli.py`。如实登记，不硬凑 | **主控 / E2b**（**PLACEHOLDER-A1c-01**） |

### 12.4 允许仍红（BEFORE / OTHERS-ONLY / AFTER 同红，A1c 不负责）
| 测试 | 归因 | 归属 |
|---|---|---|
| `test_golden_b::test_g05_appended_extreme_strategy_leaves_existing_norm_composite_grade_unchanged` | 双根因：§11 D-A1-06（hand 串味 1.9）+ §8 D-A1-08（`IMPUTE_MEDIAN` 取当期池 ⇒ 存量 S-011 被改写） | **E3b + ATT-1** |
| `test_golden_b::test_g10_sust_dimension_emptied_must_block_preflight` | D-SPEC-G10（ORCH-35） | **主控 / E3b** |
| `test_golden_b::test_g14_mix_quality_degraded_warning_fires_when_c_share_rises` | 分子/分母口径（ORCH-36 第1、2条 + ORCH-37 第6、7条） | **G14FIX** |
| `test_integration_spine::test_step1_io_loaders_loads_the_frozen_design_card_table` | **D-A1-05（JSONL 容器 + `''→None`）** → 见 §10 | **A1d** |
| `test_integration_spine::test_step3_evidence_gate_only_does_not_enter_the_score` | 三次跑同红；**D-EVID-01 / EVID-1 在飞** | **EVID-1** |
| 池键类 spine 红 | D-MODELS-01 已由 MODELS-1（`cc18a38`）收口，ORCH-38 记「spine 6红→4红，余4红全归 fixtures」；A1c 落地后余红的池键部分已并入 §12.3 第8条 | **E2b** |

## 13. Step 9 · 重新冻结登记格式（**A1c 未改 `ops/dag-state.json`**，ORCH-37：主控代登记）
建议写入 `frozen_fixtures`（只增改、不删既有键；`PLACEHOLDER-A1CPREP-05` 未取三段现值全文，键名以现值为准）：
```jsonc
"frozen_fixtures": {
  "commit": "<A1c 的 commit sha>",                 // 原 ca31dd1 -> 新值；ca31dd1 移入 superseded
  "frozen_at": "<ISO8601，由 CLI/主控注入；L1271 禁止计算层取系统时钟>",
  "file_count": 17, "fact_rows": 896,              // Step5 组5 实测：不变
  "periods": 5, "strategies": 12, "biz_domains": 4,
  "evidence_distribution": {"A":3,"B":3,"C":4,"D":2},           // 主体级（§6）
  "evidence_distribution_rowlevel": {"A":3,"B":4,"C":4,"D":2},  // 【新增键】行级，消除口径歧义
  "evidence_structure_denominator": 12,                         // 【新增键】§7：证据结构计数分母
  "pool_share_denominator": 11,                                 // 【新增键】§7：占比双报分母（NOT_ASSESSED 单列）
  "variants": 6, "negative": 1, "golden_cases": 15,
  "sha256": { /* 17 条 AFTER 全 64 位，见 §4 表 */ },
  "reproducibility_hash": "e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d",
  "reproducibility_hash_period": "2026-Q2",
  "reproducibility_hash_caveat": "取数时树含 ATT-1/EVID-1/P2-cli 在飞脏（HEAD ac12ed5）；三包落地后必再变，P3b 须重测",
  "superseded": {
    "commit": "ca31dd1",
    "reproducibility_hash": "8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8",
    "reproducibility_hash_pre_A1c": "4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7",
    "superseded_by": "A1c",
    "reason": "ORCH-29 第5条受控解冻（ORCH-37 第1条追认 §4.4）：D-A1-02 / D-A1-03 / D-A1-04",
    "sha256": { /* 17 条 BEFORE 全 64 位，见 §4 表 */ }
  },
  "unfreeze_adr": "docs/adr/RUN-A1c-fixtures-controlled-thaw.md",
  "defects_closed": ["D-A1-02","D-A1-03","D-A1-04"],
  "defects_deferred": {
    "D-A1-05": "仍 OPEN。裁 (a) CSV 化，拆出 A1d；触发条件已满足（§10 实测：test_step1_io_loaders 专门因 JSONL 而红）；改动面含 L888 目录布局，与 ORCH-38 的范围收紧存在张力，待主控裁",
    "D-A1-06": "OPEN。裁改 golden_map hand（不改 G05 变体），交 E3b；A1c 只在 §11 登记应改值 + 手算依据 + 原文行号，未代填（R-14）",
    "D-A1-07": "OPEN(实现侧)。三口径已裁：证据结构分母 12 / 占比双报分母 11 / 出桥行数实测已由 EVID-1 从 13 收敛为 12（§7）",
    "D-A1-08": "OPEN。非 fixtures 缺陷（锚定集无缺陷，E3 假设已证伪）；根因 IMPUTE_MEDIAN 取当期池，裁参考集 = anchor_set（失效回退 + ANCHOR_SET_STALE，ERRATUM-08），落地 ATT-1",
    "D-EVID-01": "EVID-1 已落地（出桥 13→12 实测印证），请主控核销"
  }
}
```
`defects` 段：`D-A1-02/03/04` → `CLOSED`（附 A1c commit）；`D-A1-05/06/07/08` 保持 `OPEN` 并写入上述去向。
**新登记待办（golden_map 侧，归 E2b）**：`tools/gen_golden.py:179-187` 的 G-09 载体字面量与 `hand.branch_map`、以及两条 `{"missing_rule":…,"n":1}` 探针（实测 `n` 应为 `BLOCK:2 / IMPUTE_MEDIAN:3 / SKIP:4 / ZERO:6`，或改用更精确的匹配条件）。

## 14. 铁律自检
- **R-12**：无原文依据处一律标 `PLACEHOLDER`。本 ADR 新立 **`PLACEHOLDER-A1c-01`**（§12.3 第10条 `test_l0b_whatif_step_unlocks_when_landed` 归因未闭环）；承继 `PLACEHOLDER-A1CPREP-02/03/04/06`（归 E2b/E3b/ATT-1）。`PLACEHOLDER-A1C-01`（AHP 段数值）与 `PLACEHOLDER-A1C-02`（G-14 downgrade 路径）**已闭环**（§3.1 / §3.2）；`PLACEHOLDER-A1CPREP-01`（manifest 字节/行数）**已补齐**（§4）；`PLACEHOLDER-A1CPREP-05`（dag-state 三段现值）**未取** —— ORCH-37 已把 dag-state 登记划归主控，A1c 不写该文件。
- **🔴 R-14**：`golden_map.json` **一个字节未改**（sha256 逐字节不变）。`expects` / `hand` / `probes[].e` 的任何数值**一律未由 A1c 填写**；§11 只做「应改为什么值 + 手算依据 + 原文行号」的**登记**。§6/§7 的三个计数是**实测观测值**（`dsm_stage/A1c/counts.py`），用于验证 fixtures 是否满足**原文 L1459 / L1003 / L1346** 的声明，**不用于充当 golden 期望**。
- **V-9**：全程未经 float 下结论；所有验算为有理数精确（`0.80×1.9+0.10×1.0+0.10×1.9 = 1.81`；`0.30×0.09 = 0.027`；`1.5346−0.027 = 1.5076`）。
- **V-14**：无静默降级。C-01 未降为 WARN；`g09` 未被弱化；10 条新增红**逐条归因并公开登记**，无一条被掩盖（含第10条「归因未闭环」也如实登记）。
- **R-13**：一包一提交（本包 **1** 个提交；无获批的格式类改动 → 未用第 2 个提交额度）。只显式 `git add dsm/fixtures_gen.py fixtures docs/adr/RUN-A1c-fixtures-controlled-thaw.md`；**未** `git add -A`（工作树含他包在飞脏：`dsm/attainment.py`/`dsm/cli.py`/`dsm/evidence.py`/`tests/test_evidence.py` 等，一律未入本包提交）；**未** push / tag / amend / force / rebase / reset / 切分支；提交信息前缀 `A1c:`。
- **写集**：未写 `dsm/models.py`、`normalize.py`、`pooling.py`（MODELS-1/G14FIX）、`dsm/attainment.py`（ATT-1）、`dsm/evidence.py`（EVID-1）、`dsm/cli.py`（P2-cli）、`reason_codes.py`、`io_loaders.py`、`tests/**`、`ops/dag-state.json`、`tools/**`。**未为了让 spine 转绿去碰 `models.py`/`normalize.py`/`pooling.py`**（A1CPREP §3 明示）。
- **只读**：契约原文（sha256[:12] `708679e9a83d` / 2003 行）与邻仓 `CampaignLab`（`m0-framework / 0cccb76 / porcelain 0 / rev-list 154`）全程只读、校验一致。
- 未调用 `request_user_input`；未 spawn 子 agent。
- 落盘证据（`dsm_stage/A1c/`，已 gitignore）：`before.sha256`、`before.sizes`、`baseline.sha256`、`baseline/`、`regen.sha256`、`regen.delta`、`regen/`、`after.sha256`、`after.sizes`、`apply.py`、`assert_regen.py`、`counts.py`、`hash_probe.py`、`mkadr.py`、`fixed.py`、`regress_before.log`、`regress_others_only.log`、`regress_after.log`、`failed_before.txt`、`failed_others_only.txt`、`failed_after.txt`。