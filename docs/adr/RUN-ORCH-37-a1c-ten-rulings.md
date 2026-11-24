# RUN-ORCH-37：A1CPREP §9.3 十项裁决（fixtures 受控解冻的授权边界）

- 状态：ACCEPTED（主控裁决，T+6.3h）
- 依据：A1CPREP 交付 `dsm_stage/A1CPREP/A1C-EXEC-SPEC.md`（1208 行 / 143439 B，§1-§9 + §6-A/B/C + 附录 A）
- 前置事实（A1CPREP 实测）：**probe_regen byte-identical 17/17**（`IDENTICAL_17_17`，`fixtures/` 零写入），`dsm/fixtures_gen.py` 未被 `9078201`/`8f2eca3`/`dbe96aa`/`db13471` 影响 → 重生成工装可信、A1c 可安全受控解冻

| # | 事项 | 裁决 | 理由 |
|---|---|---|---|
| 1 | 🔴 ORCH-29 第5条 D-A1-03 前提失效 | **追认 A1CPREP §4.4**：`M_COMPLAINT_RATE` ↔ `M_SATISFY_SCORE` 的 `missing_rule` 同维对调 + 洞迁到 `S-008/v1/M_SATISFY_SCORE`；**授权 A1c 改 `metric_dict`（经 `fixtures_gen.py`）** | 那 4 个缺格是 `fixtures_gen.py:136-141 MISSING_CELLS` 的**刻意 G-09 四分支构造**，B1b（`996e1c3`）靠它转绿；照字面「补格」会打回红。且两个 `BLOCK` 规则指标全是 HARD 红线指标，与 `dsm/redline.py:330` **数学上不可能共存**。属主控对 ORCH-29 的**自我纠错**（同 ORCH-30 撤回 ORCH-29 第3条的先例）。验收：`g09` 变红即回滚 R5 |
| 2 | D-A1-05 CSV 化的编排 | **拆出为 A1d，且降级为「条件执行」**；A1c 只做数据缺陷 | §9.4 查明 CSV 化还牵连 `dsm/io_loaders.py:274-279` 的 `data/<period>/` 目录布局（L888），远超换后缀；在硬停线内做会使 17/17 文件全变、golden 归因无法分离。**A1c 须实测并回答「当前是否有任何一条红测试专门因 JSONL 而红」**：有 → A1d 必须执行；无 → D-A1-05 作为**已披露遗留缺口**交 P3a，不阻塞交付 |
| 3 | 证据分布双口径 | **采纳**：`manifest.json` 与 dag-state **同时登记两个键**——主体级 `A3B3C4D2`、行级 `A3B4C4D2`，各注口径定义 | 两个口径都真实存在且各有用途；只登一个会让后续读者误判 |
| 4 | D-A1-02 只补 `alt_method_note`（偏离 ORCH-29 措辞） | **采纳，授权偏离**；**不补** `interpretation_limit` | 判定代码 `dsm/evidence.py:224-236` 只查 `card_status==COMPLETE` + `eval_method∈QUASI_METHODS` + `alt_method_note` 非空；`:248-249` 明写 A/B/D 不被 ⑤ 改写；L1172 / L1293 限定 `interpretation_limit` 只对 **C 类**有义务。补它属**过度规格化** |
| 5 | P-11 `WEIGHT_PROVENANCE_COMPLETE` | **采纳**：补 `whatif_run_id` 时**必须同时补 `ahp` 段**，否则阻塞只是从 C-01 挪到 config 层 | §3.4。`ahp` 段取值走 `PLACEHOLDER-A1C-01`：**必须沿用本 fixtures 既有合成命名约定**（`AS-SYNTH-2026` / `SYNTH-RUN-0001` / `WV-SYNTH-2026`），明确标注为合成、待业务签认，**不得伪造为业务真值**（R-12） |
| 6 | 🔴 占比双报分母 11 还是 9 | **裁为 11（读法甲）**：证据结构四类全给、`NOT_ASSESSED` 另附明细 | 若取 9 则 **D 类计数恒 0**，L1459「四类路径都被走到」失去意义。**与 ORCH-36 第2条独立得出的「占比双报分母 = 11、依 L1004 剔 `NOT_ASSESSED`」一致 → 双来源交叉印证** |
| 7 | G-14 分子 C vs C+D | **维持 ORCH-36 第1条：C 类占比**，不采 A1CPREP 倾向的 C+D | SDD **L1416** 是唯一明文且写「C 类占比」；「C+D」逐字原文**未找到**（ADJ-G14 已核 L1202 / L1722 / L1854）。A1CPREP 引 `dsm/reason_codes.py:86` 的 message「低证据等级占比上升」——该文本是**实现侧自撰**，以其为据属**循环引证**，不构成原文依据。且度量 C+D 会使守护点对 D→C 搬运完全失效（`(C+D)` 恒 `8/11`），违 V-14。附带：`:86` 的 message 须更正为「C 类证据占比上升」，归 **P2-wire**（`reason_codes.py` 单写者） |
| 8 | 🔴 `IMPUTE_MEDIAN` 的中位数参考集 | **采纳 A1CPREP 推荐：取自 `anchor_set`，失效时回退当期池 + `ANCHOR_SET_STALE`，与 L941 同口径**。落地在**新立 ATT-1 包** | **L1134 只枚举 `missing_rule` 名字，对参考集零字规定 → 原文缺口**，故依据等级为 **`derived:`** 而非 `verbatim:`，须记 **ERRATUM-08** 走 SDD 勘误 + 业务签认。**结构性论证**：只要填补参考集依赖当期池，追加任何策略都可能改变存量策略的填补值，则 G-05 不变性（**L1407 + L1428(P-4) + L1500(V-7)**）在结构上不可能满足；唯一能同时满足两者的参考集是与当期池无关的 `anchor_set`。A1CPREP 的 15 指标覆盖矩阵已证伪「anchor_set 覆盖不足」这一旧假设，并逐条证伪四条 fixtures 侧修法（§6-C.4） |
| 9 | 13 张设计卡 vs 12 个本期 pair | **归实现侧，新立 `D-EVID-01` / 包 EVID-1**；A1c 不动 fixtures | `_universe` 未按评价期过滤（`S-005/v1` RETIRED、`offline_date=2026-06-30`，本期以 v2 出值）。**硬约束**：不得给 `S-005/v1` 补本期事实（违 L1121/L1123/L1117 且毁 G-08）、不得删卡（G-08 的 `GR_VERSION_BREAK` 依赖该卡存在）。即「运行时按评价期过滤」而非「删数据」 |
| 10 | D-A1-08 的落地包 | **新立 ATT-1，不并入 MODELS-1** | MODELS-1 预算与范围已饱和（ORCH-32 扩权后含 frame 级披露通道 + 池键松严双口径 + spine 修法）；A1CPREP 已确认 ATT-1 与 MODELS-1 **写集零交集** |

## 并发编排（本 ORCH 同时生效）

写集两两不相交，故 **A1c / ATT-1 / EVID-1 三包并发**，与在飞的 MODELS-1 / P2-cli 同时运行（6 槽满）：

| 包 | 写集 | 修的红 |
|---|---|---|
| **A1c** | `dsm/fixtures_gen.py` + `fixtures/**` + 本 ADR 同级 ADR | golden_a `g04`/`g08`、golden_b `g06`、`g09` 保绿 |
| **ATT-1** | `dsm/attainment.py` + 其测试 | golden_b `g05`（D-A1-08） |
| **EVID-1** | `dsm/evidence.py` + 其测试 | 证据结构 13→12（D-EVID-01），为 `g14` 与 golden 分母对账铺路 |
| **MODELS-1**（在飞） | `dsm/models.py` + `dsm/normalize.py` + `tests/test_integration_spine.py`（条件含 pooling） | spine×6（D-MODELS-01 + 单值槽契约缺陷） |
| **P2-cli**（在飞） | `dsm/cli.py` + `tests/test_cli.py` | cli 6 项 delta（不依赖 fixtures） |
| **G14FIX**（待 MODELS-1 落地） | `dsm/pooling.py` + `dsm/reports.py` + `tests/test_pooling.py` | golden_b `g14`（D-G14-01/02）+ CONSUMPTION-TODO 第6条 |

**串行尾**：A1c + ATT-1 + EVID-1 + MODELS-1 + G14FIX 全落地 → **E2b**（golden_a expects）→ **E3b**（golden_b expects，含 ORCH-35 的 g10 改名 + 新增 ≥2 维 BLOCK 测试）→ **P2-wire**（接线 + preflight:209-211 核验 + ratchet 32→28 + 编码校验门禁收窄 + 全量 0 failed 判定 + 哈希重登记）→ **P3a / P3b / P3c** 并行 → 主控统一 `git push` + `git tag v1.1.0`。

## R-14 边界（对 A1c 的硬约束，重申）
A1c **只允许改 `golden_map.json` 的载体指纹类字段**（sha256 / 路径 / 行数等随重生成而变的元数据）。`expects` / `hand` / `probes[].e` 的**任何数值改动**一律留给 E2b / E3b 独立手算——**包括 §6-A 的 D-A1-06 修正**（`dim_CONTRIB` `1.900000` → `1.810000000000`、综合分 `1.5346` → `1.507600000000`；依据：`1.9` 的原文出处是 **L1405（G-03）**，而 **L1407（G-05）只写「attainment 极高」无数值**，「零变异指标恒 10000」是 **L1460** 强制；验算 `CONTRIB = 0.80×1.9 + 0.10×1.0 + 0.10×1.9 = 1.81`、`Δcomposite = 0.30×0.09 = 0.027 = 1.5346 − 1.5076`）。A1c 只在 ADR 里登记该结论，不代填。

## 新增勘误与缺陷登记
- **ERRATUM-07**：`dsm/reason_codes.py:86` 的 message「低证据等级占比上升」与 ORCH-36 裁定的分子口径（C 类占比）不符，须更正为「C 类证据占比上升」（归 P2-wire）。
- **ERRATUM-08**：SDD **L1134** 只枚举 `missing_rule` 名称，**未规定 `IMPUTE_MEDIAN` 的中位数参考集**；本 RUN 按 `derived:` 取自 `anchor_set`（与 L941 同口径），须走 SDD 勘误 + 业务签认。
- **ERRATUM-09**：SDD **L982** 写 `EVIDENCE_DOWNGRADED_PARTIAL`，而注册名是 `EVIDENCE_CARD_PARTIAL`（`dsm/reason_codes.py:69`）。按 ADJ-3 以注册名为准，文档须更正（交 P3a，附录 A 已给 36 行对照表）。
- **D-EVID-01**：`dsm/evidence.py` 的 `_universe` 未按评价期过滤设计卡 → 出桥 13 行 ≠ 本期 12 pair。归 EVID-1。
- **D-A1-08 根因更正**：不是 anchor_set 覆盖不足（E3 的假设经 A1CPREP 覆盖矩阵**实测证伪**），而是 `IMPUTE_MEDIAN` 参考集依赖当期池。归 ATT-1。
