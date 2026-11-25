# P3c 交付包清单与发布前置条件（v1.1.0）

> **P3c-pre2 事实校正（必读：本节覆盖下文所有陈旧数字）**　观测 HEAD `f27334d`（A1d），`git tag -l` 实测 **0** 条。
> ① **KNOWN-GAPS 阻塞数已由 24 改为 16**（D-DOC-01 已修）：合计 **64 条**（A10/B10/C8/D7/E8/F2/**G19**）、**阻塞 16 / 非阻塞 48**，汇总节与正文逐条列举**已回读自证相等**；旧的「19 条」与「24 条」两个数字**都不要再引用**。
> ② **K 清单已扩到 K-01~K-35**（35 个编号 / 39 个签认动作，K-21 拆 5 子项），全部仍为 PLACEHOLDER；`config/` 实测 **0 文件**，真跑以 `EXIT_CONFIG=3` 拒绝（**设计如此，非缺陷**）。 【**v1.2 实况更正（DOC-FINAL-A @`50fa9e0` 亲测）**：`git ls-files -- config` = **6 个跟踪文件**（`ahp_matrices.yaml`／`anchor_set.yaml`／`eval_config.yaml`／`grade_rules.yaml`／`redlines.yaml`／`weights_WV-SYNTH-2026.yaml`；M29-3 `ae2ca02` 入库 + CFG-1 `42a4084` 增顶层键 `soft_deductions`），属**合成待签认演练样例，不等于 G7 签认**；G5／G7 未过与「不得输出可用于真实资源配置的分数或等级」的首屏声明**一字未改**。本句「0 文件」= **v1.1 口径，保留为历史**。】
> ③ **`reproducibility_hash` 现值 = `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（@`42d5346`），**台账定稿（ORCH-44）**：`8083efc9…` → `4de4b8cb…`(`superseded_by_A1c`) → `e5fa8ae0…`(@A1c) → **`e5923465…`（权威值，@`42d5346`；复测同值于 `0d8afeb`／`31eb1b2`／`93abfee`／`da4d0a9`）**，旧值一律保留、**严禁修回**；ROB-1 上报的 `f437c0ea…` 定性为 **non-canonical（测试内自测值）**，**不入台账**（见 `K-SIGNOFF-CHECKLIST.md` K-36）。**P3b 判据 = 最终 HEAD 上全新 clone + `unshare -rn` 真断网 + 同 seed 两连跑精确自等，不是与任何旧值相等。**
> ④ **CLI 仍无 console script**（`D-CLI-01`，本 RUN 裁定不补）：唯一入口 `/home/szf/venvs/dsm/bin/python -m dsm.cli`，8 条叶子命令 + 公共 6 参数 + `--schemes`，退出码 0/2/3/4/5/6/7。**且 M29 九步 marshal（[L1330]-[L1358]）本体未落地**：`cli.py:_chain_gate` 在模块齐全时仍 `raise InvariantError`（退出码 5），P2-wire-A 落的两个 seam 目前**没有生产调用点、只由测试驱动** → **不得写成「CLI 已可用」**（`KNOWN-GAPS G-14` / `K-34`）。
> ⑤ **缺陷 27 条、勘误 11 条（ERRATUM-01~11）、教训 L-01~L-12**；P2 已拆两次：**P2 → P2-cli + P2-wire → P2-wire-A + P2-wire-B**（ORCH-36 第5条 / ORCH-39 第6.4条）。`reason_code` 注册数 **91**（R15B2 的 90 + CODES-2 @`32cafd0` 的 `EV_OUT_OF_EVAL_PERIOD`）。
> ⑥ **LOO-1 新增契约产出物 `SensitivityReport.loo_impact`**（L748/L1409/L1450 要求的「每指标 LOO 影响力排名」），实测 `loo_impact_max = M_REV_MINOR 0.120000000000` 与手算逐位相符；**MD 报告面出口已由 P2-wire-A @`53ed80c` 闭环**（`report.md` ⑦ 段），**CSV 面本 RUN 不做**（ORCH-42 第4条，扩列属契约变更），**CLI 摘要面**被 ④ 的 marshal 缺位挡住 → 在 ④ 落地前**不得声称该产出物在 CLI 面对用户可见**。
> ⑦ **最终数字（P3c-final 实测 @`da4d0a9`）**：全量 pytest = **1 failed／2301 passed／2302 collected**（0 error／0 skip／0 xfail；原 11 红已**全部闭合**，唯一红是 A1c @`6299245` 的 D-A1-03 引入之新红，；**DOC-FINAL 终值 = 0 failed／2302 passed／2302 collected**（CMB-1 @`037b862`；① 原文命令 `... -m pytest --continue-on-collection-errors -o addopts= -q 2>&1 | tail -3` → **`2302 passed in 10.98s`**，标准形式 `... -ra --tb=short --continue-on-collection-errors` → **`2302 passed in 12.50s`**；0 error／0 skip／0 xfail；观测工作树 `a396e0a`、CMB-1 提交后 HEAD `037b862`；追记：1 failed／2301／2302 @`da4d0a9` 时该项为 `PLACEHOLDER-TO-REFRESH(CMB-1)`，现撤销））；权威 `reproducibility_hash` = **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（本包 `repro_offline.sh --strict-isolation` 实测 PASS／L3-strong）；`git rev-list --count origin/main..HEAD` = **59**（DOC-FINAL 亲测 @`037b862`；追记 54 @`da4d0a9` → 57 @`66481b1`；P3C-draft 的 34 **作废**；本包提交后 60，push 前由主控重测）；`git tag -l` 实测 **0**。 【**口径标注（DOC-FINAL-A）**：本句 = **v1.1 发布时终值，历史事实保留、不改写**；**v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-02；取值命令 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone，本棒未复跑）。】

- **包号**：`P3C-draft`（交付包与 README **前移件**）
- **性质**：`docs/RUN-UNATTENDED-v3.0-PARALLEL.md` §3.2 第 239 行 **P3c** 交付物中「README + 交付包」部分的**前移完成件**。**本包不打 tag、不 push**（tag 必须在 P2 全量转绿之后）。
- **本包写集**（只有两个文件）：`README.md`（重写定稿）、`docs/deliverables/P3c-DELIVERY-PACKAGE.md`（本文件，新增）。临时探针留在 gitignore 的 `dsm_stage/P3C-draft/`。
- **本包未改动**：`dsm/**`、`tests/**`、`fixtures/**`、`config/**`、`ops/dag-state.json`、`tools/**`、`docs/adr/**`，以及三份由 P3a / P3c 正式包最终定稿的文件 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`、`docs/deliverables/K-SIGNOFF-CHECKLIST.md`、`docs/deliverables/KNOWN-GAPS.md`（本包**只引用、不修改**）。
- **观测点**：HEAD 起于 **`a3a4701`**、收尾于 **`cc18a38`**（在飞 lane 持续推进，属正常；期间 MODELS-1 与 ORCH-36/37 落地）；观测时刻 2026-11-25（Asia/Shanghai）；解释器 `/home/szf/venvs/dsm/bin/python` = **Python 3.12.3**（实测）。
- **事实纪律**：下文每个数字要么本包亲自实测（标「实测」），要么注明来源文件与 commit（标「来源」）；查不到的一律 `PLACEHOLDER`（铁律 R-12）。

---

## 1. 交付包清单（构成 v1.1.0 交付的全部文件/目录）

| # | 路径 | 内容 | 是否已定稿 | 归属包 | 截至 commit |
|---|---|---|---|---|---|
| 1 | `README.md` | 项目定位 / 安装 / 目录 / 九步主流程 / CLI 实测 / 测试 / 可复现性 / **当前状态（诚实节）** / 未覆盖范围 / 纪律 / 交付物索引 | **本次前移件已定稿**（数字全部可追溯）；**正式定稿须由 P3c 在 P2 收口后复核**（届时 13 条红应归零、V 表应更新） | **P3C-draft**（本包） | 本包提交 |
| 2 | `docs/deliverables/P3c-DELIVERY-PACKAGE.md` | 本文件：交付包清单 + 打 tag 前置条件 + 发布步骤 + 交叉引用表 | **本次前移件已定稿**；「本地领先提交数」等瞬时量须在发布前**重测** | **P3C-draft**（本包） | 本包提交 |
| 3 | `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` | V-1~V-20 全量验收证据表（四列）+ 披露项 **D-1~D-12** | **未定稿**（前移建表）。当前 ✅12 / ❌3（V-1、V-7、V-14）/ ⏳5（V-2、V-3、V-10、V-15、V-20）；须由 P3a 在 P2 收口后复测并补入 ERRATUM-01/02/03 | **P3a**（建表 P3a-prep） | `358b4ea` |
| 4 | `docs/deliverables/K-SIGNOFF-CHECKLIST.md` | 待行方签认清单 **K-01~K-35**（原文含义 / 建议区间 / 代码落点 / 当前状态 / 谁在等它 / 行方需签认什么）+ G5/G7 门禁 | **表已定稿，值全部 `PLACEHOLDER`**（20/20）。表本身可交付；**K 值的填定属行方（评价管理委员会），不属本 RUN** | P3c-prep 建表 → **P3c 正式包复核** | `fb68af8` |
| 5 | `docs/deliverables/KNOWN-GAPS.md` | 已知缺口 A~F 六类共 **45 条**（A10/B10/C8/D7/E8/F2，实测） | **未定稿**：汇总计数节自称「阻塞 19 条」，但其自身列举与本包逐行 grep 均为 **24 条** → 须更正后再定稿 | P3c-prep 建表 → **P3c 正式包更正** | `fb68af8` |
| 6 | `docs/deliverables/P3b-REPRO-HARNESS.md` | `reproducibility_hash` 的逐行定义、产出路径、输入依赖、隔离级别与 6 项 `PLACEHOLDER` 自披露 | **已定稿（工装 + 前置实测）**，但**不是 P3b 签核本身**；P3b 正式签核须在 A1c 与 MODELS-1 落地后重跑同一脚本 | **P3b-prep** → P3b | `d228edd` |
| 7 | `tools/repro_offline.sh` | 复现性签核工装：全新本地 `clone --no-hardlinks` + `unshare -rn` 真断网 netns + 独立 venv 仅本地 wheelhouse `--no-index` 离线安装 + 同 seed 连跑两次比对 + PASS/FAIL 以 exit 0/1 表达 + `mktemp -d`/`trap` 自清理（幂等）+ `--strict-isolation` | **已定稿并实跑通**（四轮 L3-strong PASS，18/16/17/22s，实测哈希 `4de4b8cb…`） | **P3b-prep** | `d228edd` |
| 8 | `dsm/` | 模型代码 **26 个 `.py`**（实测），共 **13466 行**（实测 `wc -l dsm/*.py`），分层 L0a/L0b/L1-L7 | **未定稿**：**MODELS-1 已于观测末期落地**（commit `cc18a38`：D-MODELS-01 池键顺序收口 Step2 松键 / Step7 严键 + ORCH-32 frame 级披露通道 warnings/excluded）；A1c（+ ORCH-37 新编排的 ATT-1 / EVID-1 / A1d）、P2-cli / P2-wire、E3b、G14FIX 仍待落地 | MODELS-1（已交）/ A1c / ATT-1 / EVID-1 / P2 / E3b / G14FIX | `cc18a38`（后续在飞） |
| 9 | `tests/` | **36 个 `.py`**（实测）：单元 / golden G-01~G-15 / 属性 P-01~P-15 / 方法学 T-\* / 架构守护 INV-\* | **未定稿**：E3b 须改 G-10 期望 + 改名 + 新增「≥2 维清空 → BLOCK」测试；P2 须去红至 0 failed | E3b / P2 | 在飞 |
| 10 | `fixtures/` | 合成数据与 golden 期望值 **17 个文件**（实测），896 事实行 / 5 期 / 12 策略 / 4 域 | **已冻结但将受控解冻**：冻结于 `ca31dd1`；A1c 须修 D-A1-02/03/04/05/06/07/08（7 项 OPEN）。解冻须走「主控单点改 + 全量回归 + ADR」并披露解冻前后 sha256 清单 | **A1c** | `ca31dd1`（冻结点） |
| 11 | `config/` | 治理配置载体，须 6 类文件：`eval_config` / `weights_*` / `redlines` / `grade_rules` / `anchor_set` / `ahp_matrices` | **空（实测 0 文件）**，G7 未过。**交付形态 = 空目录 + K-01~K-35 签认清单**；由行方填值后才能真正出分 | **行方（评价管理委员会）** | —  【**v1.2 实况更正（DOC-FINAL-A @`50fa9e0` 亲测）**：`git ls-files -- config` = **6 个跟踪文件**（`ahp_matrices.yaml`／`anchor_set.yaml`／`eval_config.yaml`／`grade_rules.yaml`／`redlines.yaml`／`weights_WV-SYNTH-2026.yaml`；M29-3 `ae2ca02` 入库 + CFG-1 `42a4084` 增顶层键 `soft_deductions`），属**合成待签认演练样例，不等于 G7 签认**；G5／G7 未过与「不得输出可用于真实资源配置的分数或等级」的首屏声明**一字未改**。本句「0 文件」= **v1.1 口径，保留为历史**。】 |
| 12 | `pyproject.toml` | 构建/依赖/optional extra（`dev`、`parquet`）/ pytest 配置（`testpaths=['tests']`、`pythonpath=['.']`、`addopts='-q'`） | **已定稿**；**缺 `[project.scripts]`**（SDD L805/L836 要求的可执行入口 `dsm` 未落成）→ 后续工作 | C1b | `6430e2b`（parquet extra） |
| 13 | `requirements.txt` | 实测锁定：pandas 3.1.1 / numpy 2.5.5 / pydantic 2.14.4 / typer 0.29.2 / PyYAML 6.0.4 / pytest 9.2.0 / hypothesis 6.170.17 | **已定稿** | — | 已提交 |
| 14 | `docs/digest/` | **54 份** SDD 逐字摘录（M00~M44 + S1-T01~T06）+ `INDEX.md`，合计 55 个 `.md`（实测） | **已冻结**（唯一事实来源；铁律 R-5：禁读 SDD 2003 行全文） | 前序 RUN | 已提交 |
| 15 | `docs/adr/` | **32 份**裁决记录（实测），含 `RUN-ORCH-35-g10-dimension-emptied-conflict.md` | **已入账**；新裁决继续追加 | 主控 | `82d5a6a`（最新一份） |
| 16 | `docs/RUN-UNATTENDED-v3.0-PARALLEL.md` | 本 RUN 宪章：§3.2 包定义（P2/P3a/P3b/P3c）、§5 铁律 R-1~R-18、九步主流程纪律 | **已定稿（只读）** | 主控 | 已提交 |
| 17 | `ops/dag-state.json` | RUN 状态机：`decisions`（ORCH-06~ORCH-35）、`defects`（本包实测：观测初期 **19** 条 @ `a3a4701` → 收尾 **23** 条 @ `cc18a38`）、`pytest_baseline`、`reproducibility_evidence`（含 `invalidation_log` 失效台账）、`errata`（本包实测：观测初期 **3** 条 ERRATUM-01~03 → 收尾 **9** 条 ERRATUM-01~09）、`frozen_fixtures`、`r15_batch_2.result` | **活文档**，由**主控独占写**；交付时须随包归档（阶段对账单合集的权威来源） | 主控 | 持续更新 |
| 18 | `tools/gen_golden.py`、`tools/normalize.py` | golden 期望值生成 / 文本规范化工具 | **已定稿（开发辅助）**，不属运行时链路 | E 系列 | 已提交 |
| 19 | `reports/` | 运行产物根（`dsm/cli.py:31` 实测 `DEFAULT_OUT='reports'`），按 period/run_id 分层 | **不入库**（`.gitignore`）。当前仓库**无该目录**（实测 `ls -d reports` 不存在） | — | — |
| 20 | `dsm_stage/` | 各 lane 临时工作目录与证据（含 `R15B2/CONSUMPTION-TODO.md`、`MODELS-DEFERRED.md`、`ADJ-G10/G10-EVIDENCE.md` 等被裁决引用的档案） | **不入库**（`.gitignore`）。**风险披露**：多份裁决引用了其中的文件，交付归档时须由主控决定是否破例随包留存 | 各 lane | — |

> 契约原文（**只读**，不属交付包）：`开发设计文档-策略评价可辩护评分模型DSM-v1.1.md`，实测 **2003 行**、sha256 前 12 位 **`708679e9a83d`**（与 `docs/digest/*.md` 头部登记一致）。

---

## 2. 打 tag 的前置条件（**可机械核验的勾选清单**）

> 全部 5 项（+2 项本包建议项）**必须逐条跑命令核验**，不得凭记忆或凭 lane 自述打勾。**任一项不满足 → 不得打 tag。**
>
> **ORCH-45（V1-FINAL）落稿说明**：下列 ①~⑦ 每项之后的「**ORCH-45 落稿**」行是**主控亲测后的最终口径**（观测 HEAD = 最终 HEAD `3da51ab`），各项**原文「当前状态」照留不作历史改写**；复选框由**主控在 push 前实测时**亲自勾选，本包不代勾。逐项结论：**① 满足／② 满足（按 ORCH-44 重述判据，原文 ❌=0 未被满足之事实逐字保留）／③ 满足（最终 HEAD `3da51ab`）／④ 哈希侧满足、台账侧已由主控 ORCH-45 修复／⑤ 满足／⑥ 满足（65／13／52）／⑦ 满足（@`3da51ab` porcelain 空，push 前再实测一次）**。

- [ ] **① P2 全量转绿：0 failed / 0 error / 0 新增 skip / 0 xfail**
  ```bash
  cd /home/szf/dev/strategy-eval-dsm
  /home/szf/venvs/dsm/bin/python -m pytest --continue-on-collection-errors -o addopts= -q 2>&1 | tail -3
  ```
  判据：统计行形如 `N passed in Xs`，**不得出现** `failed` / `error` / `skipped` / `xfailed` 字样。
  当前状态（P3c-final 追记）：**当时未满足** —— 已入账权威基线 `13 failed / 2182 passed / 0 error / 0 skip / 0 xfail`（collected 2195，截至 `358b4ea`，来源 `ops/dag-state.json → pytest_baseline.after_R15B2_and_P3aprep`）；本包收尾时在**干净提交树** HEAD `cc18a38` 亲测得 **`11 failed, 2190 passed in 12.32s`**（MODELS-1 落地使 spine 由 6 → 4；`pytest_baseline` 尚无 `cc18a38` 节点，须由主控登记）。**两者均不为 0 failed，故 ① 未满足。**
  附加要求：`SKIP_REGISTRY` 保持全清（P3a-prep 实测 0 skipped，来源 V-ACCEPTANCE-EVIDENCE D-12(e)）。
  **ORCH-45 落稿（主控亲测，最终 HEAD `3da51ab`）：① 满足** —— 两种形式均由主控本人亲跑：标准形式 `-m pytest -ra --tb=short --continue-on-collection-errors` → 统计行原文 **`2302 passed in 11.22s`**；① 原文命令形式 `-m pytest --continue-on-collection-errors -o addopts= -q` 尾接 tail 取末三行 → 统计行原文 **`2302 passed in 10.84s`**；**0 failed / 0 error / 0 skip / 0 xfail**、collected **2302**。`SKIP_REGISTRY` 全清（现存 skip／xfail = 0，AUD-FINAL `66481b1` 复核）。**追记保留（不得抹去）**：`1 failed / 2301 passed / 2302 collected` 实测于 `93abfee` / `da4d0a9`；更早 **13 failed / 2182 passed / collected 2195** @`358b4ea`、**11 failed / 2190 passed** @`cc18a38`。 【**口径标注（DOC-FINAL-A）**：本句 = **v1.1 发布时终值，历史事实保留、不改写**；**v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-02；取值命令 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone，本棒未复跑）。】

- [ ] **② P3a 证据表定稿并含全部披露项**
  ```bash
  grep -c 'ERRATUM-0[123]' docs/deliverables/V-ACCEPTANCE-EVIDENCE.md          # 须 >= 3
  grep -oE '\*\*D-[0-9]+' docs/deliverables/V-ACCEPTANCE-EVIDENCE.md | sort -u | wc -l   # 须 = 12（D-1~D-12）
  grep -nE '✅ \*\*[0-9]+\*\*|❌ \*\*[0-9]+\*\*|⏳' docs/deliverables/V-ACCEPTANCE-EVIDENCE.md | tail -3
  ```
  判据：V-1~V-20 汇总行合计 **20 条**，且 **❌ = 0**（当前 ❌3 = V-1 / V-7 / V-14，**未满足**）；披露项 **D-1~D-12 全在册**；**ERRATUM-01/02/03** 已写入披露节并列为**待业务签认项**（ORCH-35 第 5 条要求）；D-D2-01 与 `models_questions` 4 项已列入「未覆盖 / 交下一版本」（ORCH-33 第 5 条、ORCH-34 第 5 条）。
  **ORCH-45 落稿：② 满足（按 ORCH-44 重述判据）** —— V-1~V-20 全 20 条在册（现为 ✅11 / ❌1 / ⏳8）；每条 ❌／⏳ 均有归属包 + K 编号 + 下一版完成条件；AUD-FINAL `66481b1` 卷宗佐证 C4（真弱化）= 0。**且逐字保留：原文 ❌=0 判据未被满足，因 V-14 仍 ❌**（M28 降级矩阵 26 行×六列逐条遍历断言至今零断言 + M29 九步 marshal 本体未落地，已裁为本 RUN 范围外）；诚实性优先于凑数，**V-14 维持 ❌、严禁上调**。

- [ ] **③ P3b 全新 clone + 断网 + 同 seed 两连跑哈希精确相等**
  ```bash
  tools/repro_offline.sh --strict-isolation --expect <64 位期望哈希> ; echo "exit=$?"
  ```
  判据：`exit=0` 且打印 **PASS** + 隔离级别 **L3-strong**（`--strict-isolation` 下非 L3-strong 即判 FAIL）；两次连跑的 64 位 sha256 **逐字符相等**。
  当前状态：**未满足**（P3b-prep 已实跑通工装并四轮 L3-strong PASS，但那是**前置实测**，非 P3b 正式签核；且「**异机第二人复跑**」仍是 P3b-prep 自披露的 `PLACEHOLDER` → V-3 / V-10 维持 ⏳）。
  **ORCH-45 落稿：③ 满足（最终 HEAD `3da51ab`，不再限于 `93abfee` / `da4d0a9`）** —— 主控亲跑 `--strict-isolation` 正式签核 **PASS**，RESULT 行原文：`RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=3da51ab ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`；`clone_head=3da51ab325a535525c20fe25a96b33182edf08b9`、`run_#1=run_#2=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`、`all_equal=1`、`netns_probe=offline-confirmed`、`DIRTY=0`、`HEAD_STABLE=yes`、`runs=2`、`elapsed_seconds=15`、`wh_manifest=absent-unverified`、`env_python=Python 3.12.3`、`tmpdir=/tmp/p3b-repro.WQQSlx8P`（全字段见 `P3b-REPRO-HARNESS.md` §8 追加记录与本文件 §6.4）。**V-3 / V-10 仍维持 ⏳**：第二人 / 异机复跑仍是 PLACEHOLDER（同机、同 Python 3.12.3、wheelhouse cp312-manylinux-x86_64 绑定）。

- [ ] **④ `reproducibility_hash` 在 A1c 与 MODELS-1 落地后**重新测定并登记**
  ```bash
  python3 - <<'EOF'
  import json; e=json.load(open("ops/dag-state.json"))["reproducibility_evidence"]
  print("current_hash     =", e["current_hash"])
  print("current_hash_asof=", e["current_hash_asof"])
  for s in e["invalidation_log"]: print(" seq",s["seq"],"at=",s["at"],"after=",s["hash_after"])
  EOF
  ```
  判据：`invalidation_log` 的 **seq2（MODELS-1）与 seq3（A1c）的 `at` 不再是 `pending`**，且其 `hash_after` 为**实测 64 位**十六进制；`current_hash_asof` 指向 **A1c 与 MODELS-1 均已落地之后**的 commit；③ 的 `--expect` 用的就是这个新值。
  当前状态：**未满足**（实测 seq2/seq3 的 `at` = `pending`、`hash_after` = `待测`；现值 `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7` @ `358b4ea`）。
  **ORCH-45 落稿：④ 哈希侧满足；台账侧已由主控修复** —— 哈希侧：`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` 于最终 HEAD `3da51ab` 复测**同值**且两跑自等（`all_equal=1`）。台账侧：`current_hash_asof` / `current_hash_commit` / `current_hash` 三字段矛盾、`invalidation_log` seq2 的**重复键**、`defects` 状态滞后 3 处、`D-A4-02` 撞号 → **已由主控 ORCH-45 修复，见 `ops/dag-state.json`**（该文件属主控写集，本包全程未触碰、未 add）。`--expect` 用的期望值即本行 64 位权威哈希。
  **口径提醒**（`reproducibility_evidence.p3b_criterion` 逐字）：最终判据是「A1c 与 MODELS-1 均落地后**重测**的哈希…两连跑精确相等；**不是**与 `8083efc9` 相等」。

- [ ] **⑤ 邻仓 CampaignLab 基线未变（只读核验，不符立即停机上报，不得自行修复）**
  ```bash
  cd /home/szf/dev/CampaignLab
  git branch --show-current ; git rev-parse --short HEAD ; git status --porcelain | wc -l ; git rev-list --count HEAD
  ```
  判据：四行输出须**精确**为 `m0-framework` / `0cccb76` / `0` / `154`。
  当前状态：**满足** —— 本包实测四项全部一致，且本包未写该仓任何文件。
  **ORCH-45 复核：⑤ 仍满足** —— 主控亲测四项一致 = `m0-framework` / `0cccb76` / porcelain `0` / rev-list `154`；本包开工 / 收工各校验一次，四项同样一致，邻仓全程只读未触碰。

- [ ] **⑥（本包建议项）KNOWN-GAPS 阻塞计数自洽**
  ```bash
  grep -E '^\| [A-Z]-[0-9]+ ' docs/deliverables/KNOWN-GAPS.md | grep -cE '\| (\*\*)?是(\*\*)? \|'   # 实测 24
  grep -n '是否阻塞交付.*= 是' docs/deliverables/KNOWN-GAPS.md                                        # 文件自称 19
  ```
  判据：两数须相等。当前 **24 ≠ 19**，属该文件「汇总计数」节与其自身逐行列举（A-10；B-2/3/4/5/7/8；C-1~C-6、C-8；D-1~D-6；E-6、E-8；F-1、F-2 = 24）**自相矛盾** → 须由 P3c 正式包更正（本包写集不含该文件）。
  **ORCH-45 落稿：⑥ 满足（自洽）** —— KNOWN-GAPS 正文表格行 **65** / 阻塞 **13** / 非阻塞 **52**，与「汇总计数」节及 §G「DOC-FINAL 权威计数」逐字相等（原 24 ≠ 19 的矛盾已由 P3c-final 修毕）。

- [ ] **⑦（本包建议项）工作树干净且未误改只读集**
  ```bash
  git status --porcelain           # 须为空
  git log --oneline -1             # 记录打 tag 的确切 commit
  ```
  判据：`git status --porcelain` **空**（当前实测非空：MODELS-1 在飞改 `dsm/models.py`、`dsm/normalize.py`、`dsm/pooling.py`、`tests/test_integration_spine.py`、`tests/test_models_output.py`、`tests/test_normalize.py`、`tests/test_pooling.py`）。
  **ORCH-45 落稿：⑦ 满足（@ 最终 HEAD `3da51ab` 主控实测 porcelain 为空）** —— 注明：**主控随后还有 docs 与 ledger 提交，push 前会再实测一次**（该条判据的核验时刻须为打 tag 当下）。本包自身即是在该干净点之后追加 docs 提交的包，故本包不代主控勾选 §2 复选框，最终勾选时刻以主控 push 前实测为准。

> **关于 G5 / G7 与 tag 的关系（重要口径）**：宪章 §3.2 第 239 行的 P3c 交付物是「README + `git tag v1.1.0` + 交付包（含 **K-01~K-20 + G5/G7 门禁**）　← 宪章原文逐字为 K-01~K-20，**本包不改引文**；本 RUN 实际清单已扩至 **K-01~K-35**，见 §6 与 ^^K-SIGNOFF-CHECKLIST.md^^」，**并未要求 G7 先通过才能打 tag**；M39 L45 亦允许门禁未过时做合成数据演练。因此 **tag 可以打在「合成数据演练版」上**，但**必须**同时满足：README 首屏与本文件均写明「**G5 / G7 未过，不得输出可用于真实资源配置的分数或等级**」（该声明另有测试守护 `tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen`，实测 PASS）。若行方要求 tag 代表「可上线版本」，则 ①~⑦ 之外还须追加「G7 已签认（`config/` 6 类文件齐备且无 PLACEHOLDER）」——**该口径须由主控与行方确认，本包不代拟**（`PLACEHOLDER`）。

---

## 3. 发布步骤

> **执行人：只有主控可以 push / tag。** 子 agent（含本包）**禁 push、禁 tag、禁 amend / force / rebase / reset / 切分支**（铁律 R-13 与本包派工单）。

### 3.1 当前本地领先 origin/main 的提交数（**实测**）

```
本地领先 origin/main = 33 个提交（不含本包提交）
实测命令：git rev-list --count origin/main..HEAD
实测时刻：2026-11-25，HEAD = cc18a38
远端：origin = git@github.com:shaozhongfei001/strategy-eval-dsm.git（实测 git remote -v）
```

**该数字是瞬时量**：本包工作期间 HEAD 由 `82d5a6a` → `d228edd`（P3b-prep）→ `a3a4701`（ORCH-36）→ `bb89abc`（ORCH-37）→ `cc18a38`（MODELS-1），领先数相应由 **29 → 30 → 31 → 33**。**发布前必须重测**；本包提交后该数会再 +1（即预期 **34**，仍须实测确认）。

### 3.2 确切命令序列（主控执行）

```bash
cd /home/szf/dev/strategy-eval-dsm

# --- 0. 前置核验：§2 的 ①~⑦ 全部打勾，任一不满足即停止 ---
git status --porcelain                                  # 须为空
git rev-list --count origin/main..HEAD                  # 记录领先数（重测，勿沿用本文件的 31）
git log --oneline -1                                    # 记录打 tag 的确切 commit sha

# --- 1. 打 tag（宪章 §3.2 第 239 行逐字命令）---
git tag v1.1.0

# 1'. 可选：带注记 tag（若行方要求 tag 携带元数据，用这条替代上面那条）
# git tag -a v1.1.0 -m "DSM v1.1.0 —— 合成数据演练版；G5/G7 未过，不得用于真实资源配置"

# --- 2. 核验 tag ---
git tag -l 'v1.1.*'                                     # 须列出 v1.1.0
git rev-list -n1 v1.1.0                                 # 须等于第 0 步记录的 commit sha

# --- 3. push（只主控执行；先推分支再推 tag）---
git push origin main
git push origin v1.1.0

# --- 4. push 后核验 ---
git rev-list --count origin/main..HEAD                  # 须为 0
git ls-remote --tags origin | grep v1.1.0               # 须命中
```

### 3.3 回滚（仅在出错时，且只能由主控执行）

```bash
git tag -d v1.1.0                       # 仅本地 tag、尚未 push 时
git push origin :refs/tags/v1.1.0       # 已 push 后删除远端 tag（破坏性操作，须主控批准）
```

**禁止**：`git commit --amend`、`git push --force`、`git rebase`、`git reset`、切换分支（铁律 R-13）。`index.lock` 冲突时**重试 ≤ 10 次**，不得删锁文件。

### 3.4 提交信息规范（本 RUN）

一包一提交；只显式 `git add` 本包写集；**禁 `git add -A`**；提交信息前缀 = 包号，本包为 **`P3C-draft:`**。

---

## 4. 交叉引用表：读者从哪份文档能找到哪类信息

| 我想查… | 去这份文档 | 具体位置 | 状态 |
|---|---|---|---|
| 交付包由哪些文件构成、能否打 tag、怎么发布 | **本文件** `docs/deliverables/P3c-DELIVERY-PACKAGE.md` | §1 清单 / §2 前置条件 / §3 发布步骤 | 前移件已定稿 |
| 项目怎么装、怎么跑、CLI 有哪些子命令、当前多少红 | `README.md` | §2 安装 / §5 CLI（实测）/ §6 测试 / §8 当前状态 | 前移件已定稿 |
| 某条验收判据 V-x 有没有**实测证据**、缺什么 | `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` | §一 四列表（V-1~V-20 逐行）；§二 披露项 **D-1~D-12**；「修订后汇总」行 | 未定稿（P3a） |
| 四条不可砍底线现在什么状态 | 同上 | 末节「四条不可砍底线（修订）」 | 未定稿（P3a） |
| 本 RUN 与既有上报不符之处（对账） | 同上 | **D-12**（5 处不符逐条）+ `ops/dag-state.json → decisions.ORCH-34.p3a_discrepancies_accepted` | 已采信实测值 |
| 某个业务参数（权重/门槛/红线阈值/α/预算…）谁签认、代码落点在哪一行 | `docs/deliverables/K-SIGNOFF-CHECKLIST.md` | K-01~K-35 逐行六列 + 「计数小结」 | 表定稿、值全 PLACEHOLDER |
| G5 / G7 门禁的原文判据与当前状态 | 同上 F 节 + `docs/digest/M39-risks-gates.md` | KNOWN-GAPS **F-1 / F-2** 行（引 M39 L40 / L42 = SDD L1792 / L1794） | 均未通过 |
| 还有什么没做、是否阻塞交付、谁负责闭合 | `docs/deliverables/KNOWN-GAPS.md` | A 契约容器 / B reason_code / C 配置口径 / D 缺陷 / E 文档矛盾 / F 门禁，共 45 条 | 未定稿（阻塞计数须更正） |
| `reproducibility_hash` 怎么算、由哪条路径产出、哪些环境量不入哈希 | `docs/deliverables/P3b-REPRO-HARNESS.md` | §1.1 逐行定义（引 `dsm/audit.py:43/84/100/113/153/231/242/272`）；§1.2 产出路径 | 已定稿（工装） |
| 第二人复跑的确切命令与隔离级别 | `tools/repro_offline.sh` + 同上 | 脚本头部注释「用法」段；§5.3 P-4 残留限制 | 已定稿（异机第二人复跑仍 PLACEHOLDER） |
| 哈希为什么变了、下一次会因什么变 | `ops/dag-state.json` | `reproducibility_evidence.invalidation_log`（seq1 已发生 / seq2 MODELS-1 / seq3 A1c）+ `p3b_criterion` | 活文档 |
| 某处实现为什么与原文不同（裁决理由） | `docs/adr/*.md`（32 份） | 例：G-10 维度清空互斥 → `RUN-ORCH-35-g10-dimension-emptied-conflict.md`；C-08 撤回与 R15B2 → `RUN-ORCH-30-…md` | 已入账 |
| 裁决的机器可读台账（decisions / defects / 基线 / errata） | `ops/dag-state.json` | `decisions.ORCH-31~ORCH-35`、`defects`（19 条）、`pytest_baseline.after_R15B2_and_P3aprep`、`errata`（3 条）、`frozen_fixtures`、`r15_batch_2.result` | 活文档（主控独占写） |
| 原文逐字与**行号** | `docs/digest/*.md`（54 份 + INDEX） | 例：九步主流程 `M29-mainflow.md`（L1312-L1359）；CLI `M27-cli.md`（L1076-L1092、L1519-L1557）；降级矩阵 `M28-downgrade-matrix.md`（L1280-L1305，26 行）；K 参数 `M38-k-params.md`（L1734-L1760）；验收 `M36-acceptance.md`（L1490-L1513）；模块表 `M15-modules-table.md`（L792-L838） | 已冻结（唯一事实来源） |
| 本 RUN 的宪章、包定义、铁律 R-1~R-18 | `docs/RUN-UNATTENDED-v3.0-PARALLEL.md` | §3.2 Phase 2/3 表（P2 / P3a / P3b / P3c 的产物·判据·预算·时间窗）；§5 铁律表 | 只读 |
| reason_code 注册表（90 码）与严重度依据 | `dsm/reason_codes.py` + `ops/dag-state.json → r15_batch_2.result` | 代码为单一事实源；`result.new_codes`（11 个新增码）、`result.codes_before_measured=79`、`result.codes_after=90`、`result.text_81_explained`、`result.ratchet` | 已入账 |
| 待接线 / 待下一版本的事项清单 | `dsm_stage/R15B2/CONSUMPTION-TODO.md`（9 条）、`dsm_stage/R15B2/MODELS-DEFERRED.md`（4 项）、`dsm_stage/MODELS-1/HANDOFF-P2.md` | —— | **在 gitignore 的 `dsm_stage/` 内，不入库** → 交付归档时须主控决定是否随包留存 |

---

## 5. 本包的边界与遗留（诚实披露）

1. **未打 tag、未 push、未 amend**（派工单要求 + 铁律 R-13）。`v1.1.0` 目前**不存在**（可核：`git tag -l 'v1.1.*'` 为空）。
2. **未修改任何只读集**：`dsm/**`、`tests/**`、`fixtures/**`、`config/**`、`ops/dag-state.json`、`docs/adr/**`、`tools/**`，以及 V / K / KNOWN-GAPS 三份文件。本包写集 = `README.md` + 本文件。
3. **在飞 lane 造成的观测漂移**：本包工作期间 HEAD 由 `82d5a6a` → `d228edd`（P3b-prep 落地 `tools/repro_offline.sh` + `P3b-REPRO-HARNESS.md`）→ `a3a4701`（ORCH-36，裁 G-14）→ `bb89abc`（ORCH-37，A1CPREP 十项裁决 + 三包并发编排）→ `cc18a38`（MODELS-1 落地）；`git status` 一度由「仅 `?? tools/repro_offline.sh`」变为 MODELS-1 的 7 个 ` M` 文件，随后随 `cc18a38` 提交而复归干净。`ops/dag-state.json` 的 `errata` 由 3 条增至 **9** 条、`defects` 由 19 条增至 **23** 条、`decisions` 增 ORCH-36/ORCH-37。因此：
   - 派工单所说「`tools/repro_offline.sh` 可能尚未提交」在观测末期**已不成立**（已提交于 `d228edd`），本文件按**已提交事实**引用它，未编造其内容（其头部注释与 `P3b-REPRO-HARNESS.md` 均为本包亲自读取）。
   - 本包在 HEAD `d228edd`（MODELS-1 未提交改动中）跑的一次全量得 `17 failed / 2178 passed`，**明确不作为基线**；MODELS-1 提交为 `cc18a38` 后本包在干净树上复跑得 **`11 failed / 2190 passed`**，两次实测与差额对账均已写入 README §6.3 与 §8.1。
   - ORCH-36 / ORCH-37 新增的 **ERRATUM-04~09** 与 **K-21**、以及 P2 拆分为 `P2-cli` / `P2-wire`、新编排的 `ATT-1` / `EVID-1` / `A1d` / `G14FIX` 诸包，**本包未读取其正文**，故本文件只在「存在性」层面披露并指向 `ops/dag-state.json → decisions / errata` 与对应 ADR 作为权威来源（R-12 不编造）。§2 的 ①~⑦ 勾选清单**不受影响**（判据均为可机械核验的命令）。
4. **本包未实测的项目（如实标注，不猜）**：
   - `tools/repro_offline.sh` **未由本包重跑**（其四轮 L3-strong PASS 与哈希值来源 = commit `d228edd` 的提交信息与 `P3b-REPRO-HARNESS.md`）。
   - CLI 的 `ahp build` / `calibrate` / `combine build` / `whatif` / `sensitivity` **未实跑**（`config/` 为空，预期退出码 3，README 中写「预期」而非「实测」）。
   - `dsm fixtures gen` **刻意未跑**（其 `--out` 默认 `fixtures`，会覆盖受控冻结数据，违 R-1）。
   - 「异机第二人复跑」「G7 签认后的真实端到端运行」**无法在本 RUN 内完成**（依赖行方）。
5. **`PLACEHOLDER` 清单（本包标注的、缺什么）**：
   - G5（D6 证据复核）完成状态 —— 缺行方/复核方产物。
   - G7（治理配置签认）—— 缺 `config/` 6 类文件与 K-01~K-35 全部 **35 项（39 个签认动作，K-21 拆 5 子项）** 签认值。
   - K-07（`min_sample_size_for_A` / 显著性水平 / MDE）—— 无代码落点，证据 A 类判据未实现。
   - `SPEARMAN_ZERO_VARIANCE` 与 `APPROXIMATE_ATTRIBUTION` 的 severity 依据（现暂定 WARN，ORCH-34 第 2 条不升格，转业务签认）。
   - C-03「孤儿权重项」定义（原文未找到，ORCH-35 第 7 条）。
   - ERRATUM-01 / 02 的业务确认结论（若确认单维清空即阻断，属 C-02 阈值变更，须走契约变更流程）。
   - `reproducibility_evidence.invalidation_log` seq2 / seq3 的 `hash_after`（现为 `待测`）。
   - tag 是否代表「可上线版本」的口径（须主控与行方确认）。
   - P3b 的异机第二人复跑结论。

---

## 6. P3c-pre2 重核（交付包 20 项 / tag 前置 ①~⑦ / 发布数字）

> 本节由 **P3c-pre2** 写入，把本文件推到**只差最终数字刷新**的定稿状态；与上文冲突处以本节为准。观测 HEAD `f27334d`，`git tag -l` 实测 **0** 条，未 push。

### 6.1 交付包 20 项逐项重核（**已定稿或状态已确定 12 项 / 未定稿待并发包 8 项**）

| # | 路径 | 本包重核状态 | 归属 |
|---|---|---|---|
| 1 | `README.md` | **P3c-final 定稿**：§12 事实校正 + 首屏校正横幅 + 最终数字按 `da4d0a9` 实测刷新；仅余 64 位 `output_fingerprints` 台账与「0 failed」两处 PLACEHOLDER | P3c-final（本包）|
| 2 | `docs/deliverables/P3c-DELIVERY-PACKAGE.md` | **本包定稿**（本节）| P3c-pre2 |
| 3 | `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` | **未定稿**：归并发的 **P3a-pre2**，本包**未写**（写集边界）| P3a-pre2 |
| 4 | `docs/deliverables/K-SIGNOFF-CHECKLIST.md` | **本包定稿**：K-01~**K-35**（35 编号／39 签认动作，K-21 拆 5 子项；K-23 撞号已按 L-12 改记 K-29）| P3c-pre2 |
| 5 | `docs/deliverables/KNOWN-GAPS.md` | **本包定稿**：**D-DOC-01 已修**，合计 **64 条**（A10/B10/C8/D7/E8/F2/**G19**）、**阻塞 16／非阻塞 48**，汇总与正文已回读自证相等 | P3c-pre2 |
| 6 | `docs/deliverables/P3b-REPRO-HARNESS.md` | 工装文档已在册（@`d228edd`），但 **P3b 正式签核未做** → pending；本包**未写** | P3b |
| 7 | `tools/repro_offline.sh` | 同上：6 轮实跑（4× L3-strong PASS／1× 弱隔离 PASS／1× `--strict-isolation` 按设计 FAIL）为**前置实测**，非正式签核 | P3b |
| 8 | `dsm/` | **未定稿**：A1d @`f27334d`（`io_loaders` 列级口径）、P2-wire-A @`53ed80c`（`reports`／`cli` 接线）已落；E2b／E3b／P2-wire-B 在飞 | E2b／E3b／P2-wire-B |
| 9 | `tests/` | **未定稿**：`test_golden_a.py`（E2b）、`test_golden_b.py`（E3b）、`test_integration_spine.py`（A1d 已落）| E2b／E3b |
| 10 | `fixtures/` | A1c @`6299245` 已**重新冻结**（前后 sha256 全 64 位入册，896 事实行不变）；A1d **零改动**；`golden/golden_map.json` 是 `tools/gen_golden.py` 的生成物，**单写者 = E2b**（严禁手改）| E2b |
| 11 | `config/` | **实测 0 文件**（`find config -type f` = 0）→ 真跑被 `EXIT_CONFIG=3` 拒绝，**设计如此非缺陷** | 行方（G7 签认）  【**v1.2 实况更正（DOC-FINAL-A @`50fa9e0` 亲测）**：`git ls-files -- config` = **6 个跟踪文件**（`ahp_matrices.yaml`／`anchor_set.yaml`／`eval_config.yaml`／`grade_rules.yaml`／`redlines.yaml`／`weights_WV-SYNTH-2026.yaml`；M29-3 `ae2ca02` 入库 + CFG-1 `42a4084` 增顶层键 `soft_deductions`），属**合成待签认演练样例，不等于 G7 签认**；G5／G7 未过与「不得输出可用于真实资源配置的分数或等级」的首屏声明**一字未改**。本句「0 文件」= **v1.1 口径，保留为历史**。】 |
| 12 | `pyproject.toml` | 定稿，但**无 `[project.scripts]`** → `D-CLI-01`（ACCEPTED-DISCLOSED，本 RUN 不补）| — |
| 13 | `requirements.txt` | 定稿（锁定版本实测在案）| — |
| 14 | `docs/digest/` | **已冻结**（唯一事实来源，本 RUN 不改）| — |
| 15 | `docs/adr/` | 原文写「32 份」；ORCH-36~ORCH-42 期间是否新增 ADR **本包未实测** → `PLACEHOLDER-TO-REFRESH(主控)`（`docs/adr/**` 属本包禁写面）| 主控 |
| 16 | `docs/RUN-UNATTENDED-v3.0-PARALLEL.md` | 定稿（宪章只读）| — |
| 17 | `ops/dag-state.json` | **主控独占写**，本包只读：`decisions` ORCH-01~**ORCH-42**、`defects` **27**、`errata` **11**、`contract_gaps_pending` **49**（含 K-22~K-29）、`orch_lessons` **12**（L-01~L-12）| 主控 |
| 18 | `tools/gen_golden.py`、`tools/normalize.py` | **未定稿**：`gen_golden.py` 的 G-09 载体硬编码（`:179-187`）修正归 **E2b**（A1c 裁定，严禁手改 golden_map）；`normalize.py` 的门禁作用域收窄归 **P2-wire-B**（`D-TOOLS-01`）| E2b／P2-wire-B |
| 19 | `reports/` | **不入库**（gitignore）；**`output_fingerprints` 实测为「spine 面不可观测」（ORCH-44 第4条，不得写「已变更」）**：`bundle.output_fingerprints = {}`，七件产物指纹的真实出口 `reports.write_report_set` **无生产调用点**（M29 marshal 未落地）。P2-wire-B 已实算七件 sha256[:16]：`report_md 102d2d973c949ef2`／`score_card_csv bf583dc0da2da0a6`／`grade_ledger_csv 7afe10893ff2d366`／`sensitivity_report_csv 219b0880ff44d67f`／`triangulation_md ec8733e1f1b15ded`／`audit_json b81016fbd1eea897`／`entropy_diagnostic_csv 98207523a05e569f`；64 位生产台账 → `PLACEHOLDER-TO-REFRESH(主控)` | P2-wire-B（已给 sha256[:16]）+ 主控（64 位台账）|
| 20 | `dsm_stage/` | **不入库**（gitignore）：含 `R15B2/CONSUMPTION-TODO.md`（9 条）、`G14FIX/K-21-PROPOSAL.md`、`LOO-1/NEED-WIRING.md`、`P2-wire-A/NEED-WIRING.md`（13 项）等被裁决引用的证据 → 交付归档时须**主控决定**是否随包留存 | 主控 |

### 6.2 tag 前置 ①~⑦ 重核（**P3c-final 逐条真跑命令核验**，观测 HEAD `da4d0a9`）

> 纪律重申（本文件 §2 原文）：**必须逐条跑命令核验，不得凭记忆或凭 lane 自述打勾；任一项不满足 → 不得打 tag。** 下表「实测」列全部是本包亲自跑出的命令输出摘要（完整对照见 `KNOWN-GAPS.md` §H-13）。

| 项 | 判据（§2 原文口径） | **P3c-final 实测命令 → 输出摘要** | 结论 |
|---|---|---|---|
| ① P2 全量转绿 | 0 failed／0 error／0 skip／0 xfail | `pytest -o addopts= -q -p no:cacheprovider --tb=no -rfE` → **`1 failed, 2301 passed in 15.48s`**（collected 2302；0 error／0 skip／0 xfail）。唯一红 `tests/test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502 assert 8 == 9`）；`git archive` 二分实测引入点 = **A1c @`6299245`**（`cc18a38`／`dce1ac5` 绿、`6299245` 起红）。**DOC-FINAL 终值（转录 CMB-1 实测，两种形式）**：标准形式 `... -m pytest -ra --tb=short --continue-on-collection-errors` → **`2302 passed in 12.50s`**；① 原文命令形式 → **`2302 passed in 10.98s`**（统计行形如 `N passed in Xs`，无 failed/error/skipped/xfailed 字样），即 **0 failed／2302 passed／2302 collected、0 error／0 skip／0 xfail**；观测 HEAD = 工作树 `a396e0a`（CMB-1 提交前）／提交后 `037b862`，docs 变更不参与测试收集故终值有效。本包另**亲跑**定向复核 `tests/test_methods_combine.py` → **22 passed in 0.67s**，并复跑只读探针 `dsm_stage/CMB-1/probe_q3_count.py` → **`DERIVED_Q3_COUNT = 8`**（其余四期 12）。 | **满足（DOC-FINAL 改判：硬门禁已因唯一红闭合而解除）**。**追记（不得抹去）：① 此前未满足** —— `1 failed／2301 passed／2302 collected` 实测于 `93abfee`／`da4d0a9`（15.48s；唯一红 `test_methods_combine.py:502 assert 8 == 9`），更早 `13 failed／2182 passed／collected 2195` @`358b4ea`、`11 failed／2190 passed` @`cc18a38`；闭合由 **CMB-1 @`037b862`** 完成  **ORCH-45 终值（主控亲跑 @ 最终 HEAD `3da51ab`）**：标准形式 **`2302 passed in 11.22s`**、① 原文命令形式 **`2302 passed in 10.84s`**，均 0 failed / 0 error / 0 skip / 0 xfail → **满足，且依据由「包自述」升级为「主控亲测」**；曾未满足的历史值逐条保留于左列。|
| ② P3a 证据表定稿 | **原文**：V-1~V-20 合计 20 条且 **❌ = 0** | `grep -c ERRATUM-0[123] docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`／`V-ACCEPTANCE-EVIDENCE.md` 的 ✅❌⏳ 汇总行 → **本包无权写该文件**（P3a-final 在飞，唯一脏文件），故只能转录：V-14 实测为 ❌，❌ ≠ 0 | **原文判据未满足，此事实不得抹去**。**主控 ORCH-44 重述**（逐字）：「V-1~V-20 全 20 条在册；每条 ❌／⏳ 均有归属包 + K 缺口编号 + 下一版完成条件；且有 AUD-FINAL 的零弱化卷宗佐证 C4（真弱化）= 0」。按重述判定：**满足（按 ORCH-44 重述判据；DOC-FINAL 改判）**（三子句现均成立：20 条在册／每条 ❌ 或 ⏳ 有归属包+K 编号+完成条件／AUD-FINAL @`66481b1` 佐证 C4 = 0）—— V-14 的三项登记已齐（缺口 = M28 26 行降级矩阵逐条遍历断言零断言 + M29 九步 marshal 未落地，归属包 = 主控／下一版，K 编号 = **K-34**，完成条件 = marshal 落地后 CLI 按九步跑通并产出 [L1062] 七件产物）；**V-1 现已具备转 ✅ 的实测依据**（全量 0 failed ⇒ G-01~G-15 全通过，契约 L1494；见 ①）；**AUD-FINAL 卷宗已入账 @`66481b1`**（区间 `cc18a38..da4d0a9`，21 commits／12 个触及 `tests/`／228 条删除行，**C4 真弱化 = 0**、C3 常量随口径更新 = 81 且每行带裁决号或 ERRATUM 号；AUD-FINAL 自述边界：「C4 = 0」不等于「所有断言都足够强」，且该区间**止于 `da4d0a9`**，其后的 commit 未覆盖）。**DOC-FINAL 必留事实（逐字）：原文 ❌=0 判据未被满足**，因 V-14 仍为 ❌ 且本 RUN 无法闭环（M28 降级矩阵 26 行逐条遍历断言至今零断言 + M29 九步 marshal 本体未落地，后者已裁为本 RUN 范围外）；在诚实性规则 R-12／R-14／V-14 与「凑 ❌=0」冲突时诚实性优先，故重述判据而非上调 V-14 —— **V-14 维持 ❌，严禁上调**  **ORCH-45 刷新**：三态现为 ✅**11** / ❌**1** / ⏳**8**（合计 20）；V-1 依主控亲测上调 ✅，**❌ 仍 = 1（V-14）→ 原文 ❌=0 判据依旧未被满足**（此事实逐字保留），重述判据下满足。|
| ③ P3b 全新 clone + 断网 + 同 seed 两连跑哈希精确相等 | exit 0 + PASS + **L3-strong** + 两次 64 位逐字符相等 | `bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --keep --strict-isolation` → **exit 0**、`RESULT=PASS HASH=`+H+` COMMIT=da4d0a9 ELAPSED=15s ISOLATION=L3-strong DIRTY=1 HEAD_STABLE=yes ASSERTION=pytest`；`netns_probe = offline-confirmed`；`clone_head` == `src_head`（commit-exact） | **满足（限 `93abfee`／`da4d0a9` 本次签核）**。**适用范围限定（P3b-FIX 自述 + ORCH-44）**：B1／B7 已修好 → L3-strong 自述现在可信；但**若 CMB-1 或任何后续包使 HEAD 前移，须按 §8 在最终 HEAD 复跑签核后再打 tag**（由主控在 push/tag 前执行）。**诚实边界四条保留**：第二人／异机复跑仍 PLACEHOLDER（同机同 Python 3.12.3）→ **V-3／V-10 维持 ⏳**；wheelhouse 不入库且 cp312-manylinux-x86_64 绑定；`config/` 实测 0 文件 → `dsm score` 端到端不可跑（`EXIT_CONFIG=3` **属设计非缺陷**）；权威哈希出自探针内合成的 GOVERNANCE 配置。**DOC-FINAL 追加**：CMB-1（`037b862`）与本轮文档提交使 HEAD 前移，本包按派工单**未复跑** `tools/repro_offline.sh`；**主控将在最终 HEAD 复跑 `bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`，结果记入 `ops/dag-state.json` 与最终报告**；复跑前 ③ 的最终态标注 = **`PLACEHOLDER-TO-REFRESH(主控最终签核)`**；**V-3／V-10 维持 ⏳**（第二人／异机复跑仍 PLACEHOLDER）  **ORCH-45 改判：满足（最终 HEAD `3da51ab`）** —— RESULT 行原文：`RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=3da51ab ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`；`clone_head=3da51ab325a535525c20fe25a96b33182edf08b9` / `run_#1=run_#2=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` / `all_equal=1` / `netns_probe=offline-confirmed` / `DIRTY=0` / `HEAD_STABLE=yes` / `runs=2` / `elapsed_seconds=15` / `wh_manifest=absent-unverified` / `env_python=Python 3.12.3` / `tmpdir=/tmp/p3b-repro.WQQSlx8P`。**`93abfee` 那次记录未删未改**；V-3 / V-10 维持 ⏳（第二人 / 异机仍 PLACEHOLDER）。 。**DOC-FINAL-A 追记**：v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`（PH-04／PH-05，门禁③在最终 HEAD 复跑的 RESULT 行原文）；`wh_manifest` 两路并存 —— 默认路径 `dsm_stage/P3b-prep/wheelhouse` 带旁挂清单（26 行，`sha256sum -c --quiet` rc=0）= `verified(26 entries, all OK)`，显式路径 `/home/szf/dsm-wheelhouse` 无清单 = `absent-unverified`；另 `git rev-list --count origin/main..HEAD` 的 v1.1 值 62 @`3da51ab` 保留为历史，本棒 @`50fa9e0` 实测 = 20（v1.2 收口值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`，PH-13）。 |
| ④ 哈希重测并登记 | `invalidation_log` 的 `at` 不再 pending、`hash_after` 为实测 64 位 | 转录 + 本包复测：seq1／seq3／seq4 的 `hash_after` 已是实测 64 位；`current_hash` = **`e5923465…80904`**，本包在 `da4d0a9` 复测**同值**（③ 那条命令） | **部分满足** —— 哈希侧已闭合；**`ops/dag-state.json` 侧仍不满足**：`current_hash_asof` 仍写 `358b4ea`、`invalidation_log` 有**两个 `seq = 3`**、`defects` 状态滞后 3 处、`D-A4-02` 撞号 → **属主控写集，本包只披露不修改**（见 §5 与 `KNOWN-GAPS.md` §H-11）。**DOC-FINAL**：哈希侧闭合维持（`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`，多 HEAD 复测同值；`f437c0ea…` 按 ORCH-44／K-36 定性 non-canonical 不入台账）；台账侧四项 **主控正在本轮修复**（属主控写集，本包不改）  **ORCH-45 落稿**：哈希侧满足（`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` 于 `3da51ab` 复测同值、两跑自等）；台账侧三字段矛盾 / seq2 重复键 / defects 滞后 / `D-A4-02` 撞号 **已由主控 ORCH-45 修复，见 `ops/dag-state.json`**（本包未写该文件）。|
| ⑤ 邻仓基线未变 | `m0-framework`／`0cccb76`／porcelain 0／rev-list 154 | 开工 09:04 与收工各跑一次 `cd /home/szf/dev/CampaignLab && git branch --show-current; git rev-parse --short HEAD; git status --porcelain \| wc -l; git rev-list --count HEAD` → 四次输出全部为 `m0-framework`／`0cccb76`／**0**／**154**；契约文件 sha256[:12] = **`708679e9a83d`**、行数 **2003** | **满足**（P3c-final 未写邻仓任何文件）。**DOC-FINAL 本包亲跑一次**（开工即跑，HEAD `037b862`）：`cd /home/szf/dev/CampaignLab` 后 `git branch --show-current`／`git rev-parse --short HEAD`／`git status --porcelain \| wc -l`／`git rev-list --count HEAD` → 输出 **`m0-framework`／`0cccb76`／`0`／`154`**；契约 sha256[:12] = **`708679e9a83d`**、行数 **2003** → **四项一致**（收工再复测一次）  **ORCH-45 复核**：主控亲测与本包开工 / 收工实测同为 `m0-framework` / `0cccb76` / `0` / `154`，四项一致 → 满足。|
| ⑥ KNOWN-GAPS 计数自洽 | 汇总数 == 正文逐条列举数 | `grep -cE "^\\| [A-G]-[0-9]+ " docs/deliverables/KNOWN-GAPS.md` = **65**；同前缀再筛 flag「是」= **14**（P3c-final 追记）。**DOC-FINAL 亲跑同一口径** = 正文表格行 **65**／flag「是」**13**／flag「否」**52** | **满足**（DOC-FINAL 重测后仍自洽：阻塞 **13**／非阻塞 **52**／合计 **65**；上一版 14／51 随 G-20 于 CMB-1 `037b862` CLOSED 而转为追记；再上一版 16／48／64 已随 E-8／G-2／G-3 闭合与 G-20 新增而作废）  **ORCH-45 复核**：正文表格行 **65** / 阻塞 **13** / 非阻塞 **52** 仍自洽（本包只追加 §H-15 追记节，未改 A~G 与 H-1~H-14 表格行，计数不变）→ 满足。|
| ⑦ 工作树干净 | `git status --porcelain` 为空 | 本包实测 ` M docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（P3a-final 在飞）。**该条判据与命令照抄 §2，核验时刻须为打 tag 当下** | **待主控在 push 前实测（工作树须为空）**（P3c-final 本包施工期不可能满足）。**DOC-FINAL 实测追记**：开工时 `git status --porcelain` = ` M docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（P3a-final 仍在飞）→ 本包按写集条件**跳过该文件**（`V_ACC_TOUCHED=no(在飞)`），只显式 `git add` 本包实际改动的文档，未 stash／checkout／restore／reset／clean，未 push、未 tag  **ORCH-45 落稿：满足（@ 最终 HEAD `3da51ab` 主控实测 porcelain 为空）**；主控随后还有 docs 与 ledger 提交，**push 前再实测一次**。|

**tag 结论（DOC-FINAL 刷新）**：**门禁侧硬阻塞 ① 已解除** —— ① **满足**（0 failed／2302 passed／2302 collected；① 原文命令统计行 `2302 passed in 10.98s`；**追记：曾未满足 @`93abfee`／`da4d0a9`**）、② **满足（按 ORCH-44 重述判据）**（**原文 ❌=0 判据未被满足**之事实逐字保留：V-14 仍 ❌ 且本 RUN 无法闭环；诚实性优先，重述判据而非上调 V-14）、③ **满足（限 `93abfee`／`da4d0a9` 本次签核）**，最终态 = `PLACEHOLDER-TO-REFRESH(主控最终签核)`（HEAD 已前移，须由主控在最终 HEAD 复跑 `repro_offline.sh`）、⑤ **满足**（本包亲跑四项一致）、⑥ **满足**（65／13／52 自洽）；④ 哈希侧闭合、台账侧属主控（主控本轮正在修复）；⑦ 待主控在 push 前实测。**是否打 `v1.1.0` 由主控决**：本包 **未 push、未 tag**（R-13）。

**tag 结论（V1-FINAL / ORCH-45 最终落稿，观测 HEAD = 最终 HEAD `3da51ab`）**：① **满足**（主控亲跑两种形式均 `2302 passed`，`11.22s` / `10.84s`；追记：曾未满足 @`93abfee` / `da4d0a9` 的 1/2301/2302 保留）；② **满足（按 ORCH-44 重述判据）**，且**原文 ❌=0 判据未被满足，因 V-14 仍 ❌** 之事实逐字保留；③ **满足（最终 HEAD `3da51ab`）**，不再限于 `93abfee` / `da4d0a9`；④ **哈希侧满足，台账侧已由主控 ORCH-45 修复（见 `ops/dag-state.json`）**；⑤ **满足**；⑥ **满足**（65 / 13 / 52）；⑦ **满足**（@`3da51ab` porcelain 空，push 前再实测一次）。签核适用域论证见 §6.4 与 `P3b-REPRO-HARNESS.md` §8 追加记录。**是否打 tag 由主控决**：本包 **未 push、未 tag**（R-13）。

**G5／G7 与 tag 的关系（保持不变）**：宪章 §3.2 第 239 行未要求 G7 先过才能打 tag，**tag 可以打在「合成数据演练版」上**；但 README 首屏与本文件均须写明「**G5／G7 未过，不得输出可用于真实资源配置的分数或等级**」。该声明的守护测试本包**实测确认仍 PASS**：`pytest -o addopts= -q "tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen"` → **`1 passed in 0.58s`**（只跑该文件，未跑全量）。

### 6.3 发布数字（P3c-final 刷新）

- `git tag -l` 实测 **0** 条；`v1.1.0` **不存在**，由主控在 P2-wire-B 全量转绿后统一执行（R-13：子包禁 tag／禁 push）。
- `git rev-list --count origin/main..HEAD` = **59**（DOC-FINAL 亲测 @`037b862`；`origin/main` = `3616f9722213f6da2cb0b4ff6fcf55cd947ed648`，本包实测 `git merge-base --is-ancestor origin/main HEAD` 为真 → **push 是 fast-forward**）；追记 54 @`da4d0a9` → 57 @`66481b1`；P3C-draft 的 34 **作废**；本包提交后 60，push 前**必须重测**。
- 全量 pytest 终值（DOC-FINAL 转录 CMB-1 实测）= **0 failed／2302 passed／2302 collected**（0 error／0 skip／0 xfail）；① 原文命令统计行 **`2302 passed in 10.98s`**、标准形式 **`2302 passed in 12.50s`**；观测工作树 `a396e0a`／提交后 HEAD `037b862`。唯一红 `test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502`）已由 **CMB-1 @`037b862`** 精确化收口；本包亲跑定向复核 **22 passed in 0.67s**、复跑只读探针得 **`DERIVED_Q3_COUNT = 8`**。缺口计数 = **阻塞 13／非阻塞 52／合计 65**，K 编号 **39**、签认动作 **43**。 【**口径标注（DOC-FINAL-A）**：本句 = **v1.1 发布时终值，历史事实保留、不改写**；**v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-02；取值命令 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone，本棒未复跑）。】
- 契约核验（本包第一步实测）：sha256[:12] = `708679e9a83d`、行数 = **2003**，与派工单一致。
- **ORCH-45 终值刷新（V1-FINAL）**：`git rev-list --count origin/main..HEAD` = **62** @ 最终 HEAD `3da51ab`（`origin/main` = `3616f972…`，实测为 HEAD 祖先 → **push 为 fast-forward**）；`git tag -l` 计数 = **0**；全量终值（主控亲跑）= **0 failed / 2302 passed / 2302 collected**，统计行原文 **`2302 passed in 11.22s`**（标准形式）与 **`2302 passed in 10.84s`**（① 原文命令形式）；追记 54 @`da4d0a9` → 57 @`66481b1` → 59 @`037b862` → **62 @`3da51ab`**，本包提交后由主控 push 前重测。 【**口径标注（DOC-FINAL-A）**：本句 = **v1.1 发布时终值，历史事实保留、不改写**；**v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-02；取值命令 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone，本棒未复跑）。】
- **G5／G7 与 tag 的关系**：宪章 §3.2 第239行未要求 G7 先通过才能打 tag；但 tag **不代表可上线版本**，只代表「合成数据演练版」——G7 未过时按 M39 L45 仅允许合成数据全流程／演示报告／whatif 预演，**不得**输出可用于真实资源配置的分数或等级。

---

## 6.4 V1-FINAL（ORCH-45）最终落稿：tag 前置 ①~⑦ + P3b 签核 + 适用域论证

**观测 HEAD = 最终 HEAD `3da51ab`（短 `3da51ab`），T+8.4h，全部数字为主控亲测**（非任何包的自述）。本小节只追加，§2 与 §6.1~§6.3 的原文（含「当时未满足」「24 ≠ 19」「限 `93abfee`／`da4d0a9`」等历史表述）**逐字保留**，供追溯每个判据的演进。

### 6.4.1 P3b 正式签核 RESULT 行（原文照录）

```
RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=3da51ab ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest
```

**其余字段原文**：`clone_head=3da51ab325a535525c20fe25a96b33182edf08b9`、`run_#1=run_#2=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`、`all_equal=1`、`netns_probe=offline-confirmed`、`env_mode=dedicated venv (no system site-packages) installed from local wheelhouse with --no-index`、`env_python=Python 3.12.3`、`wh_manifest=absent-unverified`、`dirty_files=0`、`head_stable=yes (src_head_end=3da51ab325a535525c20fe25a96b33182edf08b9…)`、`pytest_assertion=rc=0`、`meta=period=2026-Q2 seed=20260101 run_id=SYNTH-RUN-0001 exit_code=0 len=64`、`runs=2`、`elapsed_seconds=15`、`tmpdir=/tmp/p3b-repro.WQQSlx8P`。权威哈希**只认 `tools/repro_offline.sh` 的 RESULT 行**（K-36；`f437c0ead77b…` 为 non-canonical，不入台账）。

### 6.4.2 tag 前置 ①~⑦ 最终态

| 项 | 最终态 | 一句话依据 |
|---|---|---|
| ① | **满足** | 主控亲跑全量两种形式：`2302 passed in 11.22s` / `2302 passed in 10.84s`，0 failed / 0 error / 0 skip / 0 xfail @`3da51ab`（追记：曾未满足 1/2301/2302 @`93abfee`／`da4d0a9`，更早 13/2182 @`358b4ea`、11/2190 @`cc18a38`）  【**口径标注（DOC-FINAL-A）**：本句 = **v1.1 发布时终值，历史事实保留、不改写**；**v1.2 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-02；取值命令 `/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone，本棒未复跑）。】 |
| ② | **满足（按 ORCH-44 重述判据）** | **原文 ❌=0 判据未被满足，因 V-14 仍 ❌**（逐字保留）：M28 26 行×六列逐条遍历断言至今零断言 + M29 九步 marshal 本体未落地 。**DOC-FINAL-A 追记**：矩阵断言已随 M28-1 `ecb5535` 落地（26 行 × **5 列**／161 断言，ERRATUM-V12-05）、九步 marshal 本体已随 M29-1 `a432ef6` 落地（调用链 `dsm/cli.py:953 → :959 → :1120 → :1129 write_report_set`，本棒复测）⇒ 本行两处「至今零断言／本体未落地」自该两 commit 起过期，原句保留为 v1.1 历史；**② 的判据结论不变（V-14 仍 ❌，残留 = NG-V12-19 + G-8 + NG-V12-27／28）** |
| ③ | **满足（最终 HEAD `3da51ab`）** | RESULT 行见 6.4.1；`93abfee` / `da4d0a9` 两次既有记录未删未改；V-3 / V-10 仍 ⏳ |
| ④ | **哈希侧满足；台账侧已由主控修复** | 同值复测 + 两跑自等；`current_hash_asof`／`current_hash_commit`／`current_hash` 三字段矛盾、`invalidation_log` seq2 重复键、defects 状态滞后、`D-A4-02` 撞号 → **已由主控 ORCH-45 修复，见 `ops/dag-state.json`** |
| ⑤ | **满足** | 邻仓四项 = `m0-framework`／`0cccb76`／porcelain `0`／rev-list `154`（本包开工／收工各校验一次，一致，只读未触碰） |
| ⑥ | **满足** | KNOWN-GAPS 正文表格行 **65**／阻塞 **13**／非阻塞 **52** 自洽 |
| ⑦ | **满足（@`3da51ab` porcelain 为空）** | 主控实测该时点工作树干净；**主控随后还有 docs 与 ledger 提交，push 前会再实测一次**（核验时刻 = 打 tag 当下） |

### 6.4.3 签核适用域论证

`reproducibility_hash` 的输入面 = **seed `20260101` / period `2026-Q2` / `fixtures/input` + `fixtures/golden` / 冻结权重版本 id**（出处 `ops/dag-state.json → reproducibility_evidence.harness.inputs`），**不含 `docs/**` 与 `ops/**`**。签核 HEAD 之后的提交只触及 `docs/deliverables/**` + `README.md`（V1-FINAL 包）与 `ops/dag-state.json`（主控 ledger），因此**不进入哈希输入面，6.4.1 的签核结论对最终被 tag 的 commit 仍然适用**。**该结论由主控在 push 前用 `git diff --name-only 3da51ab..HEAD` 实测核验**，核验输出记入 `ops/dag-state.json` 与主控最终报告；本包按纪律**未代跑、未代填**。若发现任何超出 `docs/**` 与 `ops/dag-state.json` 的触及面，本论证失效，须重跑签核后再打 tag。

### 6.4.4 交付数字终态与仍挂置项

- **验收三态（V-1~V-20）**：✅ **11**（V-1、V-5、V-6、V-9、V-11、V-12、V-13、V-16、V-17、V-18、V-19）／❌ **1**（**V-14，ORCH-45 裁定维持 ❌、严禁上调**）／⏳ **8**（V-2、V-3、V-4、V-7、V-8、V-10、V-15、V-20）；合计 **20**；净上调 **+1（仅 V-1，依据 = 主控亲测）**。 （v1.2 收口三态 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`，PH-14；本串 11/1/8 为 v1.1 终态、保留为历史；**V-14 维持 ❌（预声明，DOC-FINAL 不得翻案）**，V-2 具备上调条件但须主控在最终 HEAD 亲测后裁定 —— 裁定权只属主控 L-11／ORCH-49 第 6 条）
- **仍挂置的 PLACEHOLDER（不得读成已完成）**：hypothesis **500 例档**未跑（V-2）；**第二人 / 异机**复跑（V-3 / V-10）；**3 层回溯重抽**（V-4）；`write_report_set` **生产出口待 M29**（V-8）；**provenance 七键终值抽查**（V-15，七键全为合成待签认）；**M28 26 行×六列断言零认领**；`cel_contract_version` 保持 PLACEHOLDER（[L1897]/[L1795]）；`bundle.output_fingerprints` spine 面 = `{}`；LOO 影响力 CSV 载体与 G-14 上期 PoolStats 载体本 RUN 不做（ORCH-42）；缺末尾 LF 的受控文件 **17 @`da4d0a9`**（其中 9 个非 `docs/**`，清零需主控单独授权）。（**v1.2 实况**：M29-1 `a432ef6` 已让 `_render_reports` 进入生产路径（本棒复测 `dsm/cli.py:959`，内部 `:1129` 调 `reports.write_report_set`）⇒「无生产调用点」自该 commit 起过期；但**六键口径的 `bundle.output_fingerprints` 终值 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`**（PH-11，M29-2 落地后 CLI 实跑取值），且 `audit.json` 自身 SHA256 不在这六键内（**NG-V12-20／ERRATUM-V12-07**，须显式披露、不得静默））；ahead／tag 计数 = `PLACEHOLDER-TO-REFRESH(主控@最终HEAD)`（PH-13；取值命令 `git rev-list --count origin/main..HEAD; git tag -l | wc -l`；本棒开工 @`50fa9e0` 实测 `rev-list --count HEAD` = 139、`git tag -l` = 1（仅 `v1.1.0`，`v1.2.0` 未打））
- **门禁口径不变**：**G5 / G7 未过**，README 首屏与本文件的「**G5 / G7 未过，不得输出可用于真实资源配置的分数或等级**」声明**一字未改**（守护测试 `tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen`）；tag 只代表「**合成数据演练版**」，不代表可上线（宪章 §3.2 第 239 行 + M39 L45）。
- **本包纪律**：只显式 `git add` 本包实际改动的五份 docs（含本文件）；**未写、未 add `ops/dag-state.json`**；未 `git add -A`；未跑 pytest、未跑 `tools/repro_offline.sh`；未 push、未 tag、未 amend / stash / checkout / reset / clean。
