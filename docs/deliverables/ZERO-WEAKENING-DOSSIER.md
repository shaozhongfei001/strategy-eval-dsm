# ZERO-WEAKENING-DOSSIER（零弱化卷宗）

包：AUD-FINAL（只读终审 + 补齐 ORCH-38 第 3 条明令要求但此前缺位的证据卷宗）
审计区间：`cc18a38`（MODELS-1，权威基线 after_MODELS1 = 11 failed / 2190 passed / 2201 collected）.. `da4d0a9`（审计时 HEAD）
本卷宗**未修改任何代码、测试、fixtures、tools、ops、README 或其它 docs**；写集仅本文件 + `dsm_stage/AUD-FINAL/`（gitignored 取证中间件）。

---

## ① 目的与判据

ORCH-38 第 3 条明令要求提交 `git diff -U0` 级卷宗以证明 R-14（零弱化）被逐包遵守。P3a-pre2 定稿时把 V-14 判为 ❌，理由之一即「该卷宗在可见范围内全部缺位」。本文件把这件事从「各包自述」升级为「主控可核验的卷宗」。

R-14 口径（本卷宗采用的判据，不放水）：**严禁把实现输出抄成期望；严禁弱化断言**。落到 diff 层面即：任何 `tests/` 删除行都必须能被证明为「同主题等强或更强」「语义零变化的重排」或「依已裁口径更新的期望常量」，否则即为真弱化。

四分类判据（含本包补充的执行细则）：

| 类 | 名称 | 判据 | 是否允许 |
| --- | --- | --- | --- |
| C1 | 精确化 | 宽泛断言改为更窄/更强的**同主题**断言，须能指出引文或裁决号 | 允许 |
| C2 | 同语句扩容重排 | import 合并、行拆分、逐字重现、注释/docstring/空行等**非可执行行** | 允许 |
| C3 | 常量随口径更新 | 期望常量因**已裁口径**而变，**必须写出裁决号 / ERRATUM 号** | 允许（须挂裁决号） |
| C4 | 真弱化 | 阈值放宽、`and`→`or`、删断言、加 `skip`/`xfail`/`skipif`、精确值改区间、`==` 改 `in` 掩盖差异 | **禁止，必须为 0** |

本包补充细则（写死，避免判读弹性）：
1. **非可执行行（注释 / docstring / import / 空行 / 测试函数重命名行）一律记 C2**；其实质影响由「该 hunk 内可执行断言是否等强或更强」单独判。
2. 一行删除若**同时**满足「更强」与「依裁决更新常量」，记 **C1 并附裁决号**（不重复计数）。
3. 写不出裁决号的常量变更一律**降级为 C4 待裁**并单列。本卷宗中 C3 的 81 行**全部**带裁决号或 ERRATUM 号。
4. 计数以 `git diff --numstat`（删除列）与 hunk 头 `-old,count` 为权威；`grep -c '^-[^-]'` 会漏计被删空行（本 RUN 实测 E3b 少计 5 行），故**不采用**。

---

## ② Task A：卷宗主表

`tests/` 删除行合计 **228** 行（`git diff --numstat` 权威口径，逐 commit 求和）。

| commit | 包 | tests/ 删除行 | C1 | C2 | C3（附裁决号） | C4 | 净增断言 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2313857` | P3C-draft | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `ac12ed5` | ORCH-38 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `897cad1` | EVID-1 | 0 | 0 | 0 | 0 | 0 | **+21** | ✅ 纯新增 |
| `313a0d6` | ORCH-39 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `2ee10ed` | P2-cli（impl） | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `da88ff7` | P2-cli（tests） | 1 | 0 | 1 | 0 | 0 | **+84** | ✅ |
| `dce1ac5` | ATT-1 | 0 | 0 | 0 | 0 | 0 | **+49** | ✅ 纯新增 |
| `6299245` | A1c | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 只动 fixtures/ |
| `42d5346` | G14FIX | 6 | 1 | 5 | 0 | 0 | **+39** | ✅ |
| `32cafd0` | CODES-2 | 8 | 2 | 3 | 3 | 0 | **+20** | ✅ |
| `858ebc8` | LOO-1 | 0 | 0 | 0 | 0 | 0 | **+21** | ✅ 纯新增 |
| `53ed80c` | P2-wire-A | 4 | 3 | 1 | 0 | 0 | **+50** | ✅ |
| `f4aaa6b` | ORCH-40+41 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `f27334d` | A1d | 26 | 3 | 18 | 5 | 0 | **+11** | ✅ |
| `0d8afeb` | E3b | 171 | 3 | 95 | 73 | 0 | **+13** | ✅（见 §2.2 逐组） |
| `31eb1b2` | E2b | 2 | 2 | 0 | 0 | 0 | 0 | ✅ |
| `5d13ef3` | P3a-pre2 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `111570a` | ROB-1 | 6 | 3 | 3 | 0 | 0 | **+23** | ✅ |
| `d46bf48` | P3c-pre2 | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 未触 tests/ |
| `93abfee` | P2-wire-B(1/2) | 4 | 3 | 1 | 0 | 0 | **+1** | ✅ ratchet 只缩不涨 |
| `da4d0a9` | P3b | 0 | 0 | 0 | 0 | 0 | 0 | ✅ 只动 docs/+tools/ |
| **合计** | **21 commits** | **228** | **20** | **127** | **81** | **0** | **+332** | **C4 合计 = 0 ✅** |

**明确判定：C4 合计 = 0。** 本 RUN `cc18a38..da4d0a9` 区间内，`tests/` 的 228 条删除行中没有任何一条构成真弱化：无阈值放宽、无 `and`→`or`、无断言被删而不补、无新增 `skip`/`xfail`/`skipif`、无精确值改区间、无以 `in` 掩盖 `==` 差异。
### 2.1 逐 commit 判读依据（可执行删除行，C1 / C3 必附引文或裁决号）

- **`da88ff7`（P2-cli，1 行）**：唯一删除行 `assert cli.PLACEHOLDER == 'PLACEHOLDER'  # [L878] no invented values` 在同 commit 内**逐字重现**（`git diff -U0` 新增侧第 40 行），属 C2；同批新增 22 个测试函数 / 85 条 assert，并新增 `assert digest != cli.PLACEHOLDER and len(digest) == 64`（更强）。
- **`42d5346`（G14FIX，6 行）**：`from dsm import pooling` → `from dsm import numeric, pooling, reason_codes`（C2 import 扩容）；`def test_non_l1_rejection_leaves_the_single_slot_empty` + 3 行 docstring → 重命名为 `..._falls_to_primary_pool_rejected_grade` + 10 行 docstring（C2）；`assert row.reject_reason is None` → `== RC.PRIMARY_POOL_REJECTED_GRADE` **且** `is not None` **且** `pool_rank == 2`（C1，1 条断言变 3 条；裁决号 **ORCH-36 第 7 条 / CONSUMPTION-TODO 第 6 条**，引文 M24 [L1002] 四条件之一「grade = L1」、[L1005] 同族两码同判）。
- **`32cafd0`（CODES-2，8 行）**：import 扩容 1 行（C2）；docstring 2 行（C2）；`assert dropped.reason_code == evidence.PLACEHOLDER_OUT_OF_PERIOD_CODE` → 5 条断言（同名 + `is_registered` + `severity is Severity.INFO` + `blocks_run is False`）= C1，裁决号 **ORCH-40 第 1 条 / CODES-2**（PLACEHOLDER 换真注册码）；`BATCH2_TOTAL` → `BATCH3_TOTAL` 2 行 = C3（同裁决号）；`still_there` 列表推导排除集由 `BATCH2_NEW` 扩为 `BATCH2_NEW + BATCH3_NEW`（C1，断言更强）；`_BASIS` 排序对拍集同步扩容 1 行 = C3（同裁决号）。
- **`53ed80c`（P2-wire-A，4 行）**：两处 `monkeypatch.setattr(cli, '_build_preflight_config', lambda app, period: object())` → 与真实 `_build_preflight_config` **同形**的 `weight_version` 载体（C1 精确化；裁决号 **ORCH-40 第 5 条 / P2-wire-A ⑤ [L1052] 哈希接线**；退出码与产物断言一字未改）；`ctx = run.audit_context(...)` → 同调用 + `weight_version_id='WV-1'`（C1，走真哈希路径）；`assert 'NOT_ASSESSED 计数（单独计数' in sixth and 'EV_D_NOT_ASSESSED' in sixth` → **逐字重现**（C2），同批 `test_reports.py` 新增 30 条 assert。
- **`f27334d`（A1d，26 行）**：`signed_off_statuses=...))` → 同行 + `anchor_set=anchor_set`（C1；**ERRATUM-08 / ORCH-37 第 8 条 / ORCH-40 R4**）；15 行 RED docstring（含 1 空行）→ 20 行已裁说明（C2；**ORCH-41 R1/R2**，RED 归因经 A1DPREP 净树实测证伪）；`result, config = chain['preflight'], ...` + 1 行 docstring → 用 `model_copy(update={'provenance': None})` 构造**负向载荷**真跑 `preflight.run`（C1；原 BLOCK 断言一条未删，裁决 **ORCH-40 R4 第 2 项 / ORCH-41 R5**）；`assert len(ev.rows) == 13` → `== 12`（C3；**D-EVID-01 / ORCH-37 第 9 条 / ORCH-40 R4**）；`assert len(assessed) == 7 and len(naive) == 5` → `== 10 and == 2`（C3；**ORCH-40 + ORCH-37 第 4 条**，引文 M34 [L1459] A×3 B×3 C×4 D×2 + M29 [L1346]）；`assessed_total == 12 - not_assessed == 7` → `== 10`（C3，同上）；`not_assessed_count == 5` → `== 2`（C3，同上）；`result.assessed_count == 7` → `== 10`（C3，同上）；2 行注释 + `assert chain['weight_version'].provenance is None` → 5 条断言（`status == 'FROZEN'`、`provenance is not None`、`whatif_run_id` 非空、`WEIGHT_MISSING_WHATIF_RUN_ID not in findings`）（注释 C2，断言 C1；**A1c D-A1-04 / ORCH-30 第 3 条 C2b / ORCH-40 §3 第 7 项**，原前提被 A1c 证伪，引文 [L880]「缺 whatif_run_id 而 status = FROZEN → 加载失败」）。
- **`31eb1b2`（E2b，2 行）**：两处 `attainment.compute(..., params=ATT_PARAMS)` → 同调用 + `anchor_set=fx['anchor']`（C1；**ORCH-40 第 9 条 / ORCH-41 / ORCH-37 第 8 条**，测试改为真走锚定集路径）。
- **`111570a`（ROB-1，6 行）**：3 行 `from dsm.models import (...)` → 6 行扩容（C2）；`robust = [...]` + `assert robust, '...'` + `assert all(... in ('A','B') ...)` → 42 行**分布闭合**断言（C1；**ORCH-43 §1**，契约 [L1002] 四条件「且」串联枚举序 → GRADE 先于 ROBUST，[L1006] 要求 ROBUST 码保持活性）：`len(after.rows) == 12 == sum(...)`、GRADE 6 行 + 策略 ID 集合逐字、EVIDENCE 4 行 + ID 集合、D 类两条各自钉到 `EVIDENCE_CARD_MISSING` / `EVIDENCE_C_NO_LIMIT`、`ROBUST not in by_reason`、`set(by_reason) == {四码}` 穷尽闭合；另在同函数新增段(ii) **有/无对照**（合成 `X-ROB`：A 类 × grade = L1，唯一变量 = 是否携带 `FLIP_RATE_UNUSABLE`）断言 `bad_row.reject_reason == RC.PRIMARY_POOL_REJECTED_ROBUST` / `primary_pool_eligible is False` / `pool_rank == 1` 与 `ok_row.reject_reason is None` / `eligible is True`，即 ROBUST 码的活性被**独立证明**而非被删。
- **`93abfee`（P2-wire-B(1/2)，4 行）**：1 行注释（C2）+ `COLLISION_INVENTORY['fixtures_gen']` 的 4 个字面量白名单条目（3 行，C1）被删除 = ratchet **收缩**（32 → 28），依据 **ORCH-34 第 3 条裁决 + R-14「ratchet 只许收紧」+ R-15**；同批新增数值上限 `COLLISION_INVENTORY_CEILING = 28` 与 `assert pairs <= CEILING`（增长即失败，只能缩短）。**「只许缩短」守住。**

### 2.2 E3b（`0d8afeb`）171 行删除的逐组判读

`tests/test_golden_b.py` 单文件；assert 计数 62 → 75（净增 13），测试函数 16 → 18（净增 2）。按 hunk 分组，行数以 hunk 头 `-old,count` 为准，七组合计恰为 171。

| 组 | hunk（旧行,删 / 新行,增） | 删除行 | C1 | C2 | C3 | 裁决号 / 依据 |
| --- | --- | --- | --- | --- | --- | --- |
| A 全局口径常量 | `-161,2` `-164,2` `-334` `-343` | 6 | 2 | 2 | 2 | ORCH-40 R4 / ORCH-41 ERRATUM-11；`ASSESSED_COUNT 6 → 9`、`ASSESSED` 6 → 9 个策略，由**独立探针** `dsm_stage/E3b/probe_sens.py`（不 import 任何 dsm 业务模块）手算，R-14 合规 |
| B G-06 flip_rate | `-617,2` `-620` `-622,2` `-625,8` `-634,2` `-637,2` `-642,3` `-661` `-667,3` `-671,3` `-685` `-687,2` `-702` | 31 | 0 | 20 | 11 | 同 A（分母 6 → 9）；20 行为手算 docstring；`assert _ratio_eq(got.overall_flip_rate, _q(Decimal(1)/Decimal(6)))` → `_q(Decimal(hand_flipped)/Decimal(ASSESSED_COUNT))`（**已逐字复核**，由常量单点驱动，等强） |
| C G-07 loo | `-751,9` | 9 | 0 | 9 | 0 | 9 行全为跨度上界手算 docstring（M31 G-07 / probe_loo.py） |
| D G-10 | `-859` `-867,4` `-907,20` `-929` `-933` `-935,2` `-938` `-940` `-943` `-946,5` | 37 | 1 | 22 | 14 | **ORCH-35 / ERRATUM-01**（G-10 原文互斥：规范判据取 M22 C-02 SDD [L901]，实现正确、原期望过严）+ **A1c / ORCH-30 第 3 条 C2b**（GAP-E3-05 关闭） |
| E G-12 结构/占比常量 | `-1462,17` | 17 | 0 | 0 | 17 | **ORCH-37 第 6 条（读法甲）/ ORCH-36 第 3 条（分母与 share_* 同源）/ ORCH-41 ERRATUM-11**；`STRUCTURE_*` 改 A3B3C4D2、`SHARES_*` 分母 6/8 → `DEN_*` 单点 |
| F G-14 C 类占比 | `-1506,18` `-1529` `-1545` `-1548,4` `-1554` | 25 | 0 | 19 | 6 | **ORCH-36（G-14 分子 = C 类占比，SDD [L1416] 唯一明文）/ ORCH-37 第 9 条（出桥 13 → 12）/ ORCH-41 ERRATUM-11（分母 12 → 9）**；18 行为旧手算 docstring |
| G G-14 mix_quality | `-1600,2` `-1662,22` `-1692,17` `-1711,4` `-1724` | 46 | 0 | 23 | 23 | 同上；`low_evidence_share` 口径改由 `pooling.c_class_share` + `DEN_ASSESSED(9)` / `DEN_POOL(11)` 单点驱动；`-1724` 删除的仅是 `problems.append` **文案行**，其 `if` 判据行未删（V-14「商无定义不得返回 0」的守护完整保留） |
| **合计** | | **171** | **3** | **95** | **73** | **C4 = 0** |

D 组需单列说明（本卷宗唯一的判读难点，如实写出）：
1. 删除 `assert frozen.status == 'BLOCK', 'GAP-E3-05：冻结 T7 无 provenance -> C-01 阻断'` 与 `assert any(f.reason_code == _code(RC.WEIGHT_MISSING_WHATIF_RUN_ID) ...)`，替换为 `provenance is not None` + `whatif_run_id == 'WIF-SYNTH-2026-01'` + `not any(... WEIGHT_MISSING_WHATIF_RUN_ID ...)` + `not any(f.code == 'C-01' and f.blocks_run ...)` + `status != 'BLOCK' and exit_code == 0`（2 条 → 5 条）。原期望的**前提**（冻结件 provenance = null）已被 A1c 依 [L880] 补齐并证伪，故判 **C3**（裁决号 A1c D-A1-04 / ORCH-30 第 3 条 C2b / ORCH-37 第 5 条）。⚠️ **形式观察项**：`status != 'BLOCK'` 是非精确断言，可收紧为 `== 'WARN'`（现由 `exit_code == 0` 部分约束，且 BLOCK 出口已由 A1d 在 spine 侧用负向载荷精确守护）。本包**不将其判为 C4**（期望变更有裁决号、断言总量与强度净增、BLOCK 路径在别处被精确钉死），但如实登记为移交项 §⑥-2。
2. 删除 `def test_g10_sust_dimension_emptied_must_block_preflight` + 15 行 docstring + 12 行 body：依 **ORCH-35** 改名为 `test_g10_single_dimension_emptied_reweights_to_zero_and_warns_not_blocks`（单维清空 → W 置 0 重归一、WARN、exit_code 0，引文 SDD [L901]），并**新增** `test_g10_two_dimensions_emptied_blocks_preflight_with_exit_code_2` 覆盖此前零覆盖的 BLOCK 分支（ORCH-35 明令）。判 **C3 + C1**：期望随已裁口径更新，且分支覆盖净增。
---

## ③ 三项机械核查（独立复核，非引用各包自述）

**核查 1 — 区间内新增的 skip / xfail / skipif**

```
git diff cc18a38..HEAD -- tests/ | grep -nE '^\+.*(skip|xfail|skipif)'
```

命中 **2** 处，逐条判读均为**非可执行行**，无一是 pytest 标记：

| 命中 | 所在包 | 原文 | 判定 |
| --- | --- | --- | --- |
| 聚合 diff 第 553 行 | `da88ff7`（tests/test_cli.py docstring） | `HookRequiredError (V-14 -- nothing is imported to fill it, no indicator is skipped).` | 合法：docstring 中的英文单词 skipped，非标记 |
| 聚合 diff 第 1252 行 | `0d8afeb`（tests/test_golden_b.py 注释） | `# 不静默。真正的判据是 (1)。V-14：不用 skip/xfail 掩盖。` | 合法：声明**不使用** skip/xfail 的注释 |

逐 commit 复核 `skiphits`：仅 `da88ff7`=1、`0d8afeb`=1，其余 19 个 commit 均为 0。→ **新增 skip/xfail/skipif 标记数 = 0 ✅**

**核查 2 — 断言净增**

| 口径 | 新增 assert 行 | 删除 assert 行 | 净值 |
| --- | --- | --- | --- |
| 逐 commit 求和（`git diff -U0 <sha>^ <sha> -- tests/`，21 个 commit） | 350 | 18 | **+332** |
| 端到端聚合（`git diff cc18a38..da4d0a9 -- tests/`） | 348 | 17 | **+331** |

两口径差 1 的原因如实披露：聚合 diff 会把「先新增后在同区间内被再次改写」的行折叠，逐 commit 求和不折叠。两口径**均为净增**，满足「必须净增」的判据。→ **净增断言 = +332（逐包口径）/ +331（聚口径）✅**

**核查 3 — tests/ 现存 skip / xfail 存量**

```
grep -rnE 'pytest\.mark\.(skip|xfail|skipif)' tests/ | wc -l   ->  0
```

独立复核结果 **0**，与 E3b 自述「0 → 0」**一致** ✅。全 RUN 无任何被 skip/xfail 掩盖的测试。

---

## ④ Task B：最终 HEAD 四条不可谈判红线静态终审

前置检查：`git log --oneline -12` 中已出现首行以 `P2-wire-B` 开头的 commit（`93abfee P2-wire-B(1/2): ratchet 白名单 32->28 收缩 ...`），故未触发轮询超时。**审计 HEAD = `da4d0a9`**（`93abfee` 之后又落地了 `da4d0a9 P3b`）。⚠️ 如实标注：落地的是 **P2-wire-B(1/2)**，其 (2/2)（全量 0 failed 判定 / 复现哈希重登记）在本包审计时**尚未出现**，故本终审对象是「P2-wire-B 第 1 段之后、第 2 段之前」的 HEAD，**不是 P2 全量收口后的最终 HEAD**。

### V-9 数值纪律 → ✅（1 项观察，0 违例）

- `grep -rnE 'float\(' dsm/*.py`（排除注释与 `from_float`）命中 **2** 处：
  - `dsm/numeric.py:60/66`：审计桥本体（`FloatNotAllowedError` + `from_float(value, places=12)`，`Decimal(repr(float(value))).quantize(...)`）→ **合法**，这是契约允许的唯一入口。
  - `dsm/sensitivity.py:332`：`alpha.append(float(concentration * weight))` → **合法（观察项）**：乘法在 Decimal 域完成后仅用于构造 numpy Dirichlet 的 `alpha` 参数（随机数发生器的入参），**不参与任何金额/比率比较**；抽样结果在 `:337` 立即经 `numeric.from_float(draw[index])` + `_renormalize` 回到 Decimal 域。
- 其余 `float(` 命中（`weights_calibrate.py:375`、`sensitivity.py:108`、`triangulation.py:133/318/427`）全部是 `numeric.from_float(...)` 显式桥调用 → **合法**。
- 小数字面量扫描 `grep -rnE '(^|[^_a-zA-Z0-9''])0\.[0-9]' dsm/*.py`（排除 `Decimal(` / `D('` / `_D('` / `default='` / 注释）：命中项**全部**位于 docstring 或**字符串内**（如 `Decimal('0.10')`、`default='0.05'`、`'0.200000'`、`D('0.58')`），无一处是裸 float 参与运算 → **合法**。
- 整数精确相等 / 比率走 Decimal + `numeric.TOL`（1e-12）：`pooling.py:356`（分母 0 直接抛，不返回 0）、`aggregate.py:120/140`（`numeric.eq_tol(total, ZERO)` 判退化）、`normalize.py:248/254`（`sd <= numeric.TOL` / 极差 `<= TOL`）均以 Decimal + 容差实现 → **合法**。

### V-14 禁止静默降级 → ⚠️ 1 项可疑（0 确认违例）

- 存量：`except ` 32 处、`return None` 55 处、裸 `pass` **0** 处、裸 `except:` **0** 处。
- **P2-wire-A 新落的三个披露出口全部可达**（`dsm/reports.py`）：`_scope_lines`（定义 :302）被 `_section_2` 调用（:413）；`_scope_summary`（:331）被 `_section_6` 调用（:536）；`_loo_impact_lines`（:351）被 `_section_7` 调用（:574）。三个 `_section_N` 均在报告渲染主链上，且 `tests/test_reports.py`（`53ed80c` 新增 30 条 assert）对第二/六/七节做了内容级断言（`'本期评价范围'`、`'范围过滤披露'`、`'LOO 影响力排名'`、`'0.250000000005'` 不截断不过 float 等）→ **可达且被测试钉死 ✅**。
- `return None` 的降级语义已抽样核到调用方：`normalize.py:234/243/246/249/255/261`（尺度退化哨兵）在 `:307-314` 由调用方分别挂 `CODE_REVERSAL` / `CODE_STALE` 披露；`attainment.py:451/465`、`aggregate.py:118/121/138/141`、`diagnostics.py:308`、`evidence.py:284-290`、`reports.py:182`、`triangulation.py:103` 均为「真无定义 / 判据不满足」的哨兵返回，上游有码或抛错 → **合法**。
- ⚠️ **唯一可疑项**：`dsm/cli.py:918-919`，[L1091] 失败路径 audit_bundle 写盘器内 `except OSError: return None` —— **无 reason_code、无披露位**，OSError 被吞后调用方无法区分「未写」与「写失败」。本包在时间盒内未定位到其调用方（`grep '= _write_audit_bundle'` 无命中，函数名与调用形制不符），故**如实记为 ⚠️ 可疑而非 ❌ 违例**，列入移交 §⑥-1。
- 结论：**V-14 = ⚠️ 1 项可疑（cli.py:918-919）**，其余降级路径均带码或带披露。

### V-6 + G-03 + P-2 红线不可补偿 → ✅（0 违例）

- `dsm/redline.py:11/16`：HARD 命中且无有效豁免 → `forced_grade` **恒**取 T5 行；HARD 旁路否决等级、**恒不扣分**（红线不是扣分），SOFT 只单列扣减、恒不改级 → 语义上不存在「用分数换等级」的通道。
- `dsm/grading.py:212-228`：多个 HARD 命中取**最严**的 `forced_grade`；命中但整张表未声明 `forced_grade` 时**直接抛错**（`'HARD 红线命中但未声明 forced_grade，且四级全部要求红线通过'`）→ 无静默兜底。
- `dsm/pooling.py:104-105/475/484`：HARD 命中在 `grade_reason_path` 上留下唯一痕迹 `CODE_HARD_FORCED = RC.GR_REDLINE_FORCED.value`，一级库门禁 `redline_ok = not any(code == CODE_HARD_FORCED ...)`，未过则 `reason = RC.REDLINE_HARD_HIT` → **综合分再高也进不了一级库**。
- 唯一旁路 = 显式豁免：`redline.py:21-24/70-94` 要求 `approval_id` + 有效期 + 豁免范围四元组、必须显式挂到 (metric_id, strategy_id, version_id)、不支持通配、豁免生效时**行上仍留 reason_code**、被拒的豁免不生效且照样留痕 → 属**治理签认路径**（可审计），不是加权/补偿路径。未发现任何以权重、归一、封顶或占比把 HARD 命中「救回」的代码路径。

### G-02 + P-6 证据门禁 + 禁止跨池混排 → ✅（0 违例）

- `pool_key = (biz_domain, evidence_class)` 全路径生效：`pooling.py:169`（键元组）、`:309-319`（`step7_pool_key`：`evidence_class is None` **直接抛**，绝不拿 None 当第五类混排）、`:439`（Step7 一律用严键，注释明示 P-6 / G-02 不松动）、`:512`（`rows.sort(key=lambda r: (r.pool_key.biz_domain, r.pool_key.evidence_class, ...))` → **排序路径生效**）、`:356`（占比分母为 0 直接抛，不返回 0 → **占比路径生效**）、`:534`（`structure[ev_row.evidence_class] += 1` 按池统计）。
- C 类不得进一级库：`pooling.py:90` `GATE_EVIDENCE_CLASSES = ('A', 'B')  # [L1002] 只有 A/B 有资格进一级库`，`:474` `evidence_ok = ev_row.evidence_class in GATE_EVIDENCE_CLASSES` → 与契约 §3.6.3（约 L1002，四条件以「且」串联）一致；`111570a` 的 spine 断言进一步在真实载荷上钉死「C 类 4 行全部落 `PRIMARY_POOL_REJECTED_EVIDENCE`」。
- Step2 松键 / Step7 严键的分工由 `cc18a38`（MODELS-1 / D-MODELS-01）收口，`pooling.py:48-49` 文档明示。

### P-8 reason_code 单一事实源 → 裸字面量 **0** 处（1 项观察）

- `grep -rnE "'[A-Z][A-Z0-9_]{4,}'" dsm/ | grep -v reason_codes.py` 原始命中 **323** 处；逐族判读后**全部**不是 reason_code：`config.py` 的 `SEMANTIC_CHECKS` / `WEIGHT_CHECKS` 检查项 ID（:553-558、:622、:720、:882-1226 等）、状态与种类枚举（`_STATUS_DRAFT/_FROZEN`、`_KIND_*` :562-566）、`PLACEHOLDER_TOKENS`（:84-85）、`normalize.py:90-91` 的 `__all__` 导出名、`entropy.py:191` 的 `status='INACTIVE'/'OK'`、`fixtures_gen.py` 的指标元数据字段值。
- 真·reason_code 赋值点复核：`grep -rnE 'reason_code\s*=\s*.[A-Z]' dsm/ --include=*.py | grep -v reason_codes.py` 命中 12 处，其中 11 处为 `RC.*` / `RC.*.value`；唯一非 `RC.` 直写的是 `dsm/evidence.py:225 reason_code=OUT_OF_PERIOD_CODE`，而该常量在 `evidence.py:161` 定义为 `OUT_OF_PERIOD_CODE = RC.EV_OUT_OF_EVAL_PERIOD.value`（`32cafd0` / CODES-2 落地的**派生别名**，单一事实源仍是 `dsm/reason_codes.py`）→ **裸 reason_code 字面量 = 0 处 ✅**。
- ratchet 白名单（`93abfee`）：`COLLISION_INVENTORY` 由 32 → 28（删掉 `fixtures_gen` 的 4 个已失效条目，因 A1b @`0547190` 已把它们迁到 `RC.*.value` / `redline_hard()` / `redline_soft()`；**失效白名单本身就是 ratchet 的洞**，删除是收紧），并新增 `COLLISION_INVENTORY_CEILING = 28` 与 `assert pairs <= COLLISION_INVENTORY_CEILING`（任何增长即失败，抬上限须主控书面理由，R-15 / M16 [L855]）→ **「只许缩短」守住 ✅**。
- ⚠️ 观察项：`dsm/config.py:676 self.reason_code = RC.CONFIG_SEMANTIC_ERROR` 赋的是**枚举对象**而非 `.value`，与其余 11 处（`.value` 字符串）不同形；消费侧若按字符串比较需兼容。列入移交 §⑥-5。

---

## ⑤ 静态审计的诚实边界（R-12）

1. 本审计**全部为静态 grep + 人工判读 + `git diff` 取证**，**不构成形式化证明**；未运行任何测试（全量 pytest 归 P2-wire-B 独占，本包按令未跑，连单文件也未跑）。
2. 「C4 = 0」的含义是：**在 `cc18a38..da4d0a9` 区间内、`tests/` 路径下的 228 条删除行中，未发现真弱化**。它不等于「所有断言都足够强」，也不覆盖 `dsm/`、`tools/`、`fixtures/` 侧可能存在的隐性放宽（那属 V-9/V-14 等条目）。
3. E3b 171 行删除中，**每一组的行数取自 hunk 头**（可复核），组内 C1/C2/C3 拆分由本包逐行阅读删除侧 + 抽读替换侧得出；B 组 `-702` 的替换行已逐字复核，D/E/F/G 组的替换行为**抽样复核**（每组至少 1 处逐字），未做 100% 逐字对读。
4. V-14 的 55 处 `return None` 中，本包**核到调用方披露闭环的仅 6 族（约 20 处）**；其余按语义判读为哨兵返回，未逐一追调用链（时间盒）。
5. Task B 的对象是 `da4d0a9`，**不是 P2-wire-B(2/2) 收口后的最终 HEAD**；若 (2/2) 改动 `dsm/`，本终审需重跑。
6. 拿不到的数据一律不编造：本卷宗无任何 `PLACEHOLDER` 占位数字，所有计数均来自上文可复现的命令。

---

## ⑥ Task C：移交清单（现象 + file:line + 归属 + 建议）

| # | 现象 | file:line | 归属 | 建议 |
| --- | --- | --- | --- | --- |
| 1 | 失败路径 audit_bundle 写盘器吞掉 `OSError` 后 `return None`，无 reason_code、无披露位；调用方无法区分「未写」与「写失败」。V-14 语义上的静默降级嫌疑（本包未定位调用方，故记 ⚠️ 非 ❌） | `dsm/cli.py:918-919` | P2-wire-B / 主控 | 改为带码披露（如 `AUDIT_BUNDLE_WRITE_FAILED` 走 reason_codes 单点注册）或向上抛；至少在 `_emit` 的 details 里留痕 |
| 2 | `assert frozen.status != 'BLOCK' and frozen.exit_code == 0` 为非精确断言，可收紧为 `== 'WARN'`。期望变更本身有裁决号（A1c / ORCH-30 第 3 条 C2b），BLOCK 出口已由 A1d 在 spine 侧精确守护，故**不是** C4 | `tests/test_golden_b.py:1056` 附近（`0d8afeb` 新增段） | E3b / 主控 | 收紧为 `status == 'WARN'`（+ 保留 `exit_code == 0`），使 golden 侧也精确钉死右支 |
| 3 | 口径张力：A1d 在 spine 侧断言 `assessed_total == 12 - not_assessed == 10`，E3b 在 golden_b 侧以 `DEN_POOL = 12 - 1 = 11`、`DEN_ASSESSED = 11 - 2 = 9` 为权威口径。两者各自都挂了裁决号，但是否指**同一个量**在本包静态判读下无法确证 | `tests/test_integration_spine.py:889/901/918` 对比 `tests/test_golden_b.py:166-184` | 主控（ERRATUM-11 三口径的适用面） | 请主控在 KNOWN-GAPS / ERRATUM 中明确「spine 的 assessed_total(10)」与「golden 的 DEN_ASSESSED(9)」的口径边界（是否含 G-09 BLOCK 载体 S-008），避免两个绿断言指向互相矛盾的口径 |
| 4 | V-14 的 `return None` 哨兵中，约 35 处未逐一追到调用方披露闭环（本包时间盒所限） | `dsm/entropy.py:141`、`dsm/models.py:692`、`dsm/weights_calibrate.py:381/396`、`dsm/sensitivity.py:114`、`dsm/attainment.py:451/465/608`、`dsm/aggregate.py:121/138/141`、`dsm/diagnostics.py:308`、`dsm/triangulation.py:103`、`dsm/reports.py:182`、`dsm/cli.py:372/919`、`dsm/normalize.py:234-261` | 主控 / P2-wire-B | 全量转绿后做一次「哨兵返回 → 调用方是否挂码或抛错」的闭环复核，把结论写进 V-ACCEPTANCE-EVIDENCE 的 V-14 条 |
| 5 | `reason_code` 赋的是枚举对象而非 `.value`，与其余 11 处不同形，消费侧若按字符串比较需兼容 | `dsm/config.py:676` | 主控（P-8 单一事实源） | 统一为 `.value`（或在消费侧显式 `_code()` 归一）并加一条同形性断言 |
| 6 | **非缺陷确认（请勿误报）**：`config/` 为 0 文件、真跑以 `EXIT_CONFIG=3` 退出属**设计**（`dsm/config.py:449 load_all` / `:71`），非缺陷；CLI 唯一入口为 `python -m dsm.cli`，无 console script = **D-CLI-01**（ORCH-39 已入册，本 RUN 不补以免写集扩散） | `config/`、`dsm/cli.py`、`dsm/config.py:71/449` | — | 交付文档中保持「设计事实」表述，不得写成缺陷或待修项 |
| 7 | 本卷宗的 Task B 对象非 P2-wire-B 全量收口后的最终 HEAD | `da4d0a9` | 主控 | P2-wire-B(2/2) 落地后，若其改动 `dsm/`，请指派一次增量静态终审（本卷宗 §④ 可原样复用命令） |

---

## ⑦ 审计现场取证

- **审计时 HEAD**：`da4d0a9`（`P3b: 复现性工装诚实性修复(B1 netns 纳入 ...`）；分支 `main`。
- **审计区间**：`cc18a38..da4d0a9`，共 **21** 个 commit，其中 **12** 个触及 `tests/`（`897cad1` `da88ff7` `dce1ac5` `42d5346` `32cafd0` `858ebc8` `53ed80c` `f27334d` `0d8afeb` `31eb1b2` `111570a` `93abfee`）。
- **工作树**：**脏树 1 项** —— `M docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（并发在飞的 P3a-final 写集，非本包所为；本包开工时另有 `README.md` / `KNOWN-GAPS.md` / `K-SIGNOFF-CHECKLIST.md` / `P3c-DELIVERY-PACKAGE.md` 4 项 modified，收工时已由 P3c-pre2 `d46bf48` 落地）。本包只 `git add docs/deliverables/ZERO-WEAKENING-DOSSIER.md`，未 `git add -A`/`.`，未 push、未 tag、未 stash/checkout/restore/reset/clean/amend、未切分支。
- **邻仓 `/home/szf/dev/CampaignLab`（只读，开工与收工各校验一次）**：分支 `m0-framework` ✅ / HEAD `0cccb76` ✅ / `git status --porcelain` 行数 **0** ✅ / `git rev-list --count HEAD` **154** ✅ —— 开工与收工**两次四项全一致**，未做任何写操作。
- **契约（只读）**：`/mnt/d/ws/codex_rd/ss_campaignlab/工行参考文件/开发设计文档-策略评价可辩护评分模型DSM-v1.1.md`，`sha256[:12] = 708679e9a83d` ✅、`wc -l = 2003` ✅ —— 恒定。
- **本卷宗格式**：UTF-8 无 BOM、行尾 LF、无 TAB、末尾有换行；写后回读确认中文无 `?` 乱码（回读结果见提交说明与本包 NOTES）。
- **取证中间件**（gitignored，不入库）：`dsm_stage/AUD-FINAL/` 下 8 份 `d_<sha>.diff`（各 commit 的 `git diff -U0 <sha>^ <sha> -- tests/` 原文）、`hunk_<sha>.txt`（仅含删除行的 hunk 视图）、`e3b.diff`（E3b 全量 diff）、`t1.sh`（计数脚本）。所有表格数字均可由这些文件 + 本文列出的命令复现。

---

**卷宗结论**：`cc18a38..da4d0a9` 区间内 R-14 被逐包遵守，**C4 合计 = 0**；四条不可谈判红线静态终审为 **V-9 ✅ / V-14 ⚠️1 / V-6+G-03+P-2 ✅ / G-02+P-6 ✅**，**P-8 裸 reason_code 字面量 0 处**、ratchet「只许缩短」守住。本审计为静态取证，不构成形式化证明。
