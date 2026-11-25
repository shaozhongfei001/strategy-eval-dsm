# strategy-eval-dsm

策略评价「可辩护评分」模型（**DSM** = Defensible Scoring Model）**v1.1** 的离线批量实现。

> **读者须知（首屏声明）**：本仓库当前 **G5（D6 证据复核）与 G7（治理配置签认）两道门禁均未通过**，`config/` 目录实测 **0 文件**、K-01~K-35 全部为 `PLACEHOLDER`。因此本仓库**只能用于合成数据的全流程演练**，**不得输出任何可用于真实资源配置的分数或等级**（判据见 `docs/digest/M39-risks-gates.md` L45，即 SDD L1797）。详见下文[第 8 节「当前状态」](#8-当前状态诚实节)。

> **P3c-final 事实校正（必读：本节覆盖下文所有陈旧数字）**　观测 HEAD `da4d0a9`（P3b-FIX），`git tag -l` 实测 **0** 条。P3c-pre2 的校正节保留为上一版本。
> ① **KNOWN-GAPS 计数（P3c-final 重算）：合计 65 条、阻塞 14 / 非阻塞 51**（A10/B10/C8/D7/E8/F2/**G20**）；E-8／G-2／G-3 已 CLOSED（`111570a`／`31eb1b2`／`0d8afeb`），新登 **G-20**（全量唯一残留红）。旧数字 **19／24／16／48／64 一律不再引用**；D-DOC-01 验收条件（汇总数 == 正文逐条数）**已复核仍成立**。
> ② **K 清单已扩到 K-01~K-39**（39 个编号 / 43 个签认动作，K-21 拆 5 子项；新增 **K-36 权威哈希口径／K-37 G-10 hand 判据陈旧／K-38 G-14 hand 三口径留痕／K-39 P3b 工装 B1~B9 + `dsm_stage/` 归档风险**，编号由主控 ORCH-44 单点分配），全部仍为 PLACEHOLDER；`config/` 实测 **0 文件**，真跑以 `EXIT_CONFIG=3` 拒绝（**设计如此，非缺陷**）。
> ③ **`reproducibility_hash` 现值 = `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（@`42d5346`），**台账定稿（ORCH-44）**：`8083efc9…` → `4de4b8cb…`(`superseded_by_A1c`) → `e5fa8ae0…`(@A1c) → **`e5923465…`（权威值，@`42d5346`，复测同值于 `0d8afeb`／`31eb1b2`／`93abfee`／`da4d0a9`）**，旧值一律保留、**严禁修回**；ROB-1 的 `f437c0ea…` 是 **non-canonical 测试内自测值，不入台账**（→ K-36）。**P3b 判据 = 最终 HEAD 上全新 clone + `unshare -rn` 真断网 + 同 seed 两连跑精确自等，不是与任何旧值相等。**
> ④ **CLI 仍无 console script**（`D-CLI-01`，本 RUN 裁定不补）：唯一入口 `/home/szf/venvs/dsm/bin/python -m dsm.cli`，8 条叶子命令 + 公共 6 参数 + `--schemes`，退出码 0/2/3/4/5/6/7。**且 M29 九步 marshal（[L1330]-[L1358]）本体未落地**：`cli.py:_chain_gate` 在模块齐全时仍 `raise InvariantError`（退出码 5），P2-wire-A 落的两个 seam 目前**没有生产调用点、只由测试驱动** → **不得写成「CLI 已可用」**（`KNOWN-GAPS G-14` / `K-34`）。
> ⑤ **缺陷 27 条、勘误 11 条（ERRATUM-01~11）、教训 L-01~L-12**；P2 已拆两次：**P2 → P2-cli + P2-wire → P2-wire-A + P2-wire-B**（ORCH-36 第5条 / ORCH-39 第6.4条）。`reason_code` 注册数 **91**（R15B2 的 90 + CODES-2 @`32cafd0` 的 `EV_OUT_OF_EVAL_PERIOD`）。
> ⑥ **LOO-1 新增契约产出物 `SensitivityReport.loo_impact`**（L748/L1409/L1450 要求的「每指标 LOO 影响力排名」），实测 `loo_impact_max = M_REV_MINOR 0.120000000000` 与手算逐位相符；**MD 报告面出口已由 P2-wire-A @`53ed80c` 闭环**（`report.md` ⑦ 段），**CSV 面本 RUN 不做**（ORCH-42 第4条，扩列属契约变更），**CLI 摘要面**被 ④ 的 marshal 缺位挡住 → 在 ④ 落地前**不得声称该产出物在 CLI 面对用户可见**。
> ⑦ **最终数字（P3c-final 实测 @`da4d0a9`）**：全量 pytest = **1 failed／2301 passed／2302 collected**（0 error／0 skip／0 xfail；原 11 红**全部闭合**，唯一红由 A1c @`6299245` 的 D-A1-03 引入，已派 **CMB-1** → 「0 failed」= `PLACEHOLDER-TO-REFRESH(CMB-1)`）；权威 `reproducibility_hash` = **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（本包 `repro_offline.sh --strict-isolation` 实测 **PASS／L3-strong**）；`git rev-list --count origin/main..HEAD` = **54**（34 **作废**）；`git tag -l` = **0**。

- **唯一权威设计文档（SDD）**：`开发设计文档-策略评价可辩护评分模型DSM-v1.1.md`，共 **2003 行**（本包实测 `wc -l`），sha256 前 12 位 **`708679e9a83d`**（本包实测）。
- **本 README 的事实纪律**：下文每一个数字要么是本包亲自实测（标注「实测」），要么注明来源文件与 commit（标注「来源」）。查不到的一律写 `PLACEHOLDER`，**不猜、不编**（本 RUN 铁律 R-12）。

---

## 1. 项目定位

**DSM 是什么**：一个**离线批量**的策略评分与分级程序 —— 读入本期各策略的指标事实与评价设计卡，输出每条策略的综合得分、四级等级、应执行动作，以及「这个结论有多稳、能不能用于淘汰」的检验报告。（来源：SDD §4.1 一分钟速览 L1523，逐字摘录见 `docs/digest/M27-cli.md`）

**解决什么问题**：让「哪条策略该加码、哪条该淘汰」这个决定**可以被追问、可以被复算、可以被推翻**。SDD §4.1 L1529 把这一条写成「最关键的一条」：**分数不是终点** —— 报告首屏会告诉你本期结论能不能用来淘汰策略；一旦出现 `FLIP_RATE_UNUSABLE` 或 `METHOD_DIVERGENCE`，**本期暂停淘汰动作**（`usable_for_elimination = false`，SDD §3.15.1 L1352-L1354）。

**「可辩护」的含义**：一个分数要能辩护，必须同时满足四件事，SDD 各有专节：

| 要素 | 含义 | SDD 出处 |
|---|---|---|
| 入分的只有三件事 | **目标达成率、加权聚合、红线否决**；AHP 只用来造权重、熵权只作为 α 组合的一支、TOPSIS/GRA 只做三角验证并拥有否决权 —— 四种教科书方法**没有一个被允许直接决定一条策略的生死** | §3.3~§3.7、§3.12（digest M02/M03/M04/M06/M07/M08/M12） |
| 权重必须冻结且可出示证据链 | 任一 `FROZEN` 权重版本都能出示：AHP 比较矩阵 → CR → 标定窗口熵权 → α 及标定报告 → 组合权重对照表 → whatif run_id | §3.8（验收判据 V-15，L1508） |
| 任何降级都留痕 | 所有降级路径都有 `reason_code` **且出现在报告中**，**无静默降级** | §3.14 降级矩阵 L1280-L1305（实测 **26 行**）、验收判据 V-14（L1507） |
| 可被第二人复算 | 第二人在**全新 clone + 断网单机 + 同 seed** 下复跑，`reproducibility_hash` 必须**精确相等** | L1640、验收判据 V-3（L1496）/ V-10 |

**运行形态与边界**（SDD §4.1 L1524-L1530，逐字）：谁运行 = 评价管理部门的数据/运营分析岗（**1 人即可**，单机命令行）；多久跑一次 = **每期一次**（月或季，由配置定），权重构造**每年一次**；输入 = **8 张表（CSV）**；输出 = **5 张表 + report.md + 审计包**；**不需要**数据库、不需要联网、不需要新建系统、不需要采购件、**不接生产库**；性能上 SDD **明确不预估数字**（L1526）。

---

## 2. 安装

### 2.1 Python 版本

- 要求：`pyproject.toml` 实测 `requires-python = '>=3.11'`；SDD §3.1 L796 亦为「Python 3.11+」。
- 本 RUN 实测解释器：`/home/szf/venvs/dsm/bin/python -V` → **`Python 3.12.3`**。

### 2.2 建 venv 并装依赖

```bash
python3 -m venv ~/venvs/dsm
~/venvs/dsm/bin/pip install -r requirements.txt        # 实测锁定版本，见下
# 或（可编辑安装 + 开发依赖）
~/venvs/dsm/bin/pip install -e '.[dev]'
```

`requirements.txt`（本包实测逐字）：`pandas==3.1.1`、`numpy==2.5.5`、`pydantic==2.14.4`、`typer==0.29.2`、`PyYAML==6.0.4`、`pytest==9.2.0`、`hypothesis==6.170.17`。

### 2.3 optional extra（parquet / pyarrow）

`pyproject.toml` 实测：

```toml
[project.optional-dependencies]
dev     = ['pytest>=8.0', 'hypothesis>=6.90']
parquet = ['pyarrow']
```

读 Parquet 输入表时须装 extra：

```bash
~/venvs/dsm/bin/pip install -e '.[parquet]'
```

`parquet` extra 是缺陷 **D-C1-01** 的修复产物：commit **`6430e2b`**（C1b）在修 `dsm/io_loaders.py` 的 `read_parquet` 把 `dtype=str` 透传成 `TypeError` 的同时，按 ADJ-8 加了这个 extra（实测 `git show --stat 6430e2b` = `dsm/io_loaders.py` +11 / `pyproject.toml` +1 / `tests/test_io_loaders.py` +28）。D-C1-01 在 `ops/dag-state.json → defects` 中状态为 **CLOSED**（本包实测）。

### 2.4 断网（离线）安装

`tools/repro_offline.sh`（P3b-prep，commit `d228edd`）会建独立 venv 并**只从本地 wheelhouse 以 `--no-index` 安装**，全程放进 network namespace（`unshare -rn`）。
**诚实边界**（该脚本头部注释逐字）：脚本自身不联网，但 **wheelhouse 的首次预下载需要联网**，那一步不在脚本内；缺 wheelhouse 时脚本**不会假装断网成功**，而是降级为 `--system-site-packages` 并把隔离级别如实标成 `PLACEHOLDER`。

---

## 3. 目录结构

| 目录 | 职责（一句话） |
|---|---|
| `dsm/` | 模型代码，**26 个 `.py`**（实测），分层 L0a / L0b / L1-L7（层级与 23 模块职责见 `docs/digest/M15-modules-table.md`，SDD L809-L836） |
| `tests/` | 三层测试，**36 个 `.py`**（实测）：单元 / golden G-01~G-15 / 属性 P-01~P-15 / 方法学 T-\* / 架构守护 INV-\* |
| `fixtures/` | 合成数据与 golden 期望值，**17 个文件**（实测），冻结于 commit `ca31dd1`（896 事实行 / 5 期 / 12 策略 / 4 域，来源 `ops/dag-state.json → frozen_fixtures`）；**不含任何真实客户信息** |
| `config/` | 治理配置载体，须行方签认后填入 6 类文件；**当前实测 0 文件**（`find config -type f \| wc -l` = 0） |
| `tools/` | 开发/签核辅助脚本：`gen_golden.py`、`normalize.py`、`repro_offline.sh`（复现性签核工装） |
| `docs/` | `digest/`（**54 份** SDD 逐字摘录 + INDEX，唯一事实来源）、`adr/`（**32 份**裁决记录）、`deliverables/`（交付物）、RUN 宪章 |
| `ops/` | `dag-state.json`：RUN 的裁决、缺陷、基线、复现证据台账（**主控独占写**） |
| `reports/` | 运行产物根目录（`dsm/cli.py:31` 实测 `DEFAULT_OUT = 'reports'`），已在 `.gitignore`，**不入库** |
| `dsm_stage/` | 各 lane 的临时工作目录，已在 `.gitignore`，**不入库** |

---

## 4. 九步主流程

来源：`docs/digest/M29-mainflow.md`（SDD §3.15.1 **L1312-L1359** 逐字摘录）；模块名与层级来源 `docs/digest/M15-modules-table.md`（SDD L809-L836）。下表「SDD 行号」即 M29 digest 中的原文行号。

| 序 | 名称（原文逐字） | 模块文件 | SDD 行号 | 失败出口 |
|---|---|---|---|---|
| Step 0 | `dsm preflight --period P` → C-01~C-10 十项校验 | `dsm/preflight.py`（L2） | L1315、L1318 | `status=BLOCK` → 写 audit_bundle、**退出码 2**、**不产出 score_card**（L1322-L1326） |
| 前置 | `config.load_all()` → PLACEHOLDER? → 抛错，**退出码 3**，列出全部未填字段 | `dsm/config.py:449` | L1328 | 退出码 3 |
| 前置 | `io_loaders` → 8 表 + InputFingerprints（SHA256 / 行数） | `dsm/io_loaders.py`（L1） | L1330 | 退出码 4（数据错） |
| **Step 1** | `attainment` → 达成率矩阵 + coverage（**无目标值 → null，不用均值代替**） | `dsm/attainment.py`（L3） | L1332 | — |
| **Step 2** | `normalize` → 池内标准化 + 锚定集参照（失效 → 回退 + 首屏标注） | `dsm/normalize.py`（L3） | L1334 | — |
| 旁路 | `diagnostics` → 在线熵权 / CV / VIF / 相关（**不入分，出工单**） | `dsm/diagnostics.py`（L5） | L1336 | — |
| **Step 3** | `evidence` → A/B/C/D（短路判定；**C 缺解释限制 → D**） | `dsm/evidence.py`（L4） | L1338 | — |
| **Step 4** | `redline` → HARD 强制降级 / SOFT 独立扣减（**不进加权**） | `dsm/redline.py`（L4） | L1340 | — |
| **Step 5** | `aggregate` → `composite_absolute` + `composite_relative`（**只读 FROZEN 权重**） | `dsm/aggregate.py`（L3） | L1342 | — |
| **Step 6** | `grading` → 基础等级 → 证据封顶 → 目标封顶 → 红线覆盖 → 滞回 → 版本断点 | `dsm/grading.py`（L3） | L1344 | — |
| **Step 7** | `pooling` → 分池禁混排 + 一级库门禁 + 占比双报 + `NOT_ASSESSED` 单列 | `dsm/pooling.py`（L4） | L1346 | — |
| 旁路 | `triangulation` → TOPSIS / GRA / Spearman → `AGREE` or `DIVERGENCE` | `dsm/triangulation.py`（L5） | L1348 | — |
| **Step 8** | `sensitivity` → OAT / MC / LOO / NORM_SWAP → `flip_rate` + 稳定性标签 | `dsm/sensitivity.py`（L5） | L1350 | 首屏可用性判定：`flip_rate > review_max` 或 `METHOD_DIVERGENCE` → `usable_for_elimination = false`（L1352-L1354） |
| **Step 9** | `audit` → manifest + `reproducibility_hash` | `dsm/audit.py`（L6） | L1356 | — |
| 收尾 | `reports.render` → report.md（**10 段**）+ 5 张表 + audit.json | `dsm/reports.py`（L7） | L1358 | — |

> 通用纪律（SDD L1091，逐字）：任何命令失败都写 `audit_bundle`；退出码非 0 时**不得**产出 `score_card`；重跑生成新 `run_id` 目录，**不覆盖历史**。
---

## 5. CLI 子命令一览（**全部实测**）

### 5.1 真实入口

`pyproject.toml` 实测**没有** `[project.scripts]` 段，故 SDD L805/L836 说的「可执行入口 `dsm`」**尚未落成 console script**。当前唯一真实入口是模块入口：

```bash
/home/szf/venvs/dsm/bin/python -m dsm.cli <COMMAND> [<ACTION>] [公共参数…]
```

### 5.2 `--help` 实测原文

```console
$ /home/szf/venvs/dsm/bin/python -m dsm.cli --help
usage: dsm [-h] COMMAND ...

DSM v1.1 offline engine [L1076]

positional arguments:
  COMMAND

options:
  -h, --help  show this help message and exit
```

> **实测怪象（如实披露）**：`--help` 打印完 usage 后，还会多打一行 `dsm <cmd>: exit=5 status=INTERNAL run_id=-` / `error: SystemExit: 0` / `no score card is produced on a non-zero exit ([L1091])`。原因是 CLI 的异常包装把 argparse 自己抛出的 `SystemExit(0)` 当成了内部错误。**进程真实退出码仍是 0**（本包实测 `rc=0`）。不影响功能，但会让读者误判；修法归 P2（`dsm/cli.py` 写集）。

### 5.3 子命令清单

顶层 `COMMAND` 共 **8 个**（实测 `dsm/cli.py:117-131` 的 `add_parser` 调用逐一核对）：`preflight`、`score`、`sensitivity`、`ahp`、`combine`、`fixtures`、`calibrate`、`whatif`。其中 `ahp` / `combine` / `fixtures` 是**二级命令组**，各带一个必填 `ACTION`（实测 `dsm ahp --help` → `usage: dsm ahp [-h] {build} ...`，`combine` → `{build}`，`fixtures` → `{gen}`）。故**叶子命令 = 8 条**，与 SDD §3.10 表 L1080-L1087 的八子命令逐条对应：

| 叶子命令 | 用途（SDD L1080-L1087 逐字） | 频率 | 退出码（SDD 原文） | 实测 `--help` 参数 |
|---|---|---|---|---|
| `dsm preflight` | 数据体检（只跑 Step 0） | 每期（评分前） | 0 通过 / 2 BLOCK / 3 配置错 / 4 数据错 | 公共 6 参数 |
| `dsm score` | 评分与分级（全流程） | 每期 | 同上 **+ 5 内部不变量违反** | 公共 6 参数 |
| `dsm sensitivity` | 稳健性检验（可单独重跑） | 每期 | 同上 | 公共 6 参数 **+ `--schemes`**（默认 `OAT_10,OAT_20,LOO`，[L1554]） |
| `dsm ahp build` | 造主观权重 + CR 检验 | 年度 | 0 / 3 / **6（CR 不通过）** | 公共 6 参数 |
| `dsm calibrate` | α 标定 | 年度 | 0 / 3 / **7（可行集为空）** | 公共 6 参数 |
| `dsm combine build` | 组合权重出草稿（**DRAFT**） | 年度 | 0 / 3 | 公共 6 参数 |
| `dsm whatif` | 权重影响预演（签认前） | 年度 | 0 / 3 / 4 | 公共 6 参数 |
| `dsm fixtures gen` | 生成合成测试数据 | 开发 / 演示 | 0 | 公共 6 参数（`--out` 默认被改写为 `fixtures`，`dsm/cli.py:129`） |

**公共参数**（SDD L1089，实测 `dsm/cli.py:109-115`，`--help` 中分组标题即 `common parameters [L1089]`）：

| 参数 | 实测默认值 | 说明 |
|---|---|---|
| `--period` | 无默认 | 评价期；`preflight`/`score`/`sensitivity`/`whatif` 四条命令**必填**（`dsm/cli.py:32` `PERIOD_COMMANDS` + `:431` 校验） |
| `--config` | `config` | 配置目录 |
| `--data` | `data` | 数据根目录 |
| `--out` | `reports` | 输出根目录（`dsm/cli.py:31` `DEFAULT_OUT`） |
| `--run-at` | 无 | **显式注入运行时间**，程序内部不读系统时钟 |
| `--seed` | 无（`type=int`） | MC 用，**缺失则拒绝跑 MC** |

**退出码常量**（实测 `dsm/cli.py:26-27`）：`EXIT_OK=0`、`EXIT_BLOCK=2`、`EXIT_CONFIG=3`、`EXIT_DATA=4`、`EXIT_INTERNAL=5`、`EXIT_CONSISTENCY=6`、`EXIT_ALPHA=7`。

### 5.4 能否真实运行？**不能**（如实标注）

`config/` 实测 0 文件，任何需要配置的命令都会在 `dsm/config.py:449 load_all()` 处以退出码 **3** 拒绝。本包实测原文（输出目录指向 gitignore 的 `dsm_stage/P3C-draft/cli-probe/`，未污染仓库）：

```console
$ python -m dsm.cli preflight --period 2026-Q2 --config config --data fixtures/input --out dsm_stage/P3C-draft/cli-probe
dsm preflight: exit=3 status=CONFIG run_id=preflight-2026-Q2-20261125T070933-0105c503
  error: ConfigPlaceholderError: 配置含 0 个未签认占位值（退出码 3）

缺失必需配置文件 6 份：
  - eval_config
  - weights_*
  - redlines
  - grade_rules
  - anchor_set
  - ahp_matrices
  audit_bundle=dsm_stage/P3C-draft/cli-probe/failed/<run_id>/audit_bundle.json
```

`dsm score --period 2026-Q2 … --run-at 2026-11-25T09:00:00` 实测同为 `exit=3 status=CONFIG`，同样列出 6 份缺失文件并写出 `audit_bundle.json`（**符合 SDD L1091「任何命令失败都写 audit_bundle、退出码非 0 不得产出 score_card」**，实测 `find` 该目录只有 `audit_bundle.json`，无 score_card）。

- 未实测运行的子命令：`ahp build`、`calibrate`、`combine build`、`whatif`、`sensitivity`、`fixtures gen` —— 前四条同样依赖 `config/`，**预期同为退出码 3**（此处写「预期」而非「实测」，R-12）；`dsm fixtures gen` **本包刻意未运行**，因其 `--out` 默认为 `fixtures`，会覆盖受控冻结的 `fixtures/**`（违反 R-1 与 `frozen_fixtures.rule`）。

---

## 6. 如何跑测试

### 6.1 全量（**必须带 `--continue-on-collection-errors`**）

```bash
cd /home/szf/dev/strategy-eval-dsm
/home/szf/venvs/dsm/bin/python -m pytest --continue-on-collection-errors -o addopts= -q
```

`-o addopts=` 用于清掉 `pyproject.toml` 里的 `addopts = '-q'`，以便统计行完整可见；`--continue-on-collection-errors` 是本 RUN 的硬性要求（任一收集错误不得掩盖其余用例的结果）。

### 6.2 定向

```bash
PY=/home/szf/venvs/dsm/bin/python
$PY -m pytest tests/test_golden_a.py tests/test_golden_b.py -q   # golden G-01~G-15
$PY -m pytest tests/test_properties_all.py -q                    # 属性 P-01~P-15
$PY -m pytest tests/test_integration_spine.py -q                 # 九步贯通 + 复现哈希
$PY -m pytest tests/test_architecture.py -q                      # INV-1~INV-3 / 层级 / 碰撞 ratchet
$PY -m pytest tests/test_reason_codes.py -q                      # reason_code 注册表
$PY -m pytest tests/test_integration_spine.py -k reproducibility -o addopts= -q   # 只跑两连跑哈希断言
```

### 6.3 当前实测数字

**权威基线**（来源：`ops/dag-state.json → pytest_baseline.after_R15B2_and_P3aprep`；由 R15B2（`db13471`）与 P3a-prep（`358b4ea`）**双向独立实测一致**，并经 ORCH-34 第 6 条定为「当前权威基线」）：

```
13 failed, 2182 passed   |   0 error / 0 skipped / 0 xfailed   |   collected 2195
截至 commit 358b4ea
```

13 条红的逐条归责见[第 8.1 节](#81-全量测试13-条红的逐条归责)。

> **对账用的第二次实测（不作为基线）**：本包在观测 HEAD `d228edd` 又跑了一次全量，得 **`17 failed, 2178 passed`**。**该数字不得当作基线引用** —— 当时工作树带有在飞 lane **MODELS-1** 的未提交改动（实测 `git status --porcelain` = ` M dsm/models.py` / ` M dsm/normalize.py` / ` M dsm/pooling.py`），净差 = **+5 条新红**（`tests/test_models_output.py` 的 `test_d01_declared_columns_equal_the_ruling_table[NormalizedFrame]`、`test_e04_every_model_builds_from_its_synthetic_payload[NormalizedFrame]`、`test_j02_nullability_partition_matches_the_ruling_table[PoolKey]`，以及 `tests/test_normalize.py` 的 `test_p4_grade_gate_consumes_the_absolute_track_only`、`test_zero_variance_metric_is_inactive_and_never_rescaled_silently`）**−1 条转绿**（spine 的 `test_step2_pool_key_cannot_be_built_before_step3_evidence`，与 ORCH-32 第 4 条「`PoolKey.evidence_class` 改可选」方向一致）：13 − 1 + 5 = **17**，对账通过。这 6 处变动全部落在 MODELS-1 的写集上，属**中间态**，故本节仍以 `358b4ea` 的权威基线为准。

> **本包收尾时的第三次实测（干净提交树，最新观测）**：MODELS-1 于 commit **`cc18a38`**（"D-MODELS-01 池键顺序收口（Step2 松键 / Step7 严键）+ ORCH-32 frame 级披露通道（warnings / excluded）"）落地后，本包在**工作树干净**（`git status --porcelain` 仅本包两份文档）的状态下复跑全量，得 **`11 failed, 2190 passed in 12.32s`**（0 error / 0 skipped / 0 xfailed）。11 条红 = golden_a 2（g04/g08）+ golden_b 5（g05/g06/g07/g10/g14）+ **spine 4**（`test_step1_io_loaders_loads_the_frozen_design_card_table`、`test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures`、`test_step3_evidence_covers_the_m34_a3b3c4d2_distribution`、`test_step4_redline_runs_on_the_frozen_eval_period_fact_table`）；即 spine 由 6 → **4**（`test_step2_normalize_pool_and_anchor_from_step1_rows` 与 `test_step2_pool_key_cannot_be_built_before_step3_evidence` 已转绿，与 ORCH-32 第 3/4 条的分派一致）。
> **口径说明**：`ops/dag-state.json → pytest_baseline` 截至本包观测时**尚无** `cc18a38` 的新基线节点（末节点仍为 `after_R15B2_and_P3aprep` = 13/2182 @ `358b4ea`），故 **13/2182 仍是"已入账的权威基线"**，而 **11/2190 是本包亲测的最新观测值**；两者的差额已由上文逐条对账，不矛盾。新基线节点须由**主控**登记（本包禁写 `ops/dag-state.json`）。按本包写集避让规则，README 只以已入账的权威基线为准。

---

## 7. 可复现性

### 7.1 `reproducibility_hash` 的定义

来源：`docs/deliverables/P3b-REPRO-HARNESS.md` §1.1（该文件逐行引用了 `dsm/audit.py`）。

```
reproducibility_hash = sha256_text( canonical_text( hash_payload(score_card, grade_ledger, weight_version_id) ) )
hash_payload = {'schema': 'dsm.reproducibility/v1', 'weight_version_id': …,
                'score_card': _ordered(…), 'grade_ledger': _ordered(…)}
```

- 落点：`dsm/audit.py:231`（`hash_payload`）、`:43`（`HASH_SCHEMA`）、`:84`（`SCORE_CARD_HASH_FIELDS`，[L1612]-[L1626] 35 列中的 34 列）、`:100`（`GRADE_LEDGER_HASH_FIELDS`）、`:113`（`canonical_text`，[L1053] 五条规则：Decimal 走 q12 定点 12 位、float 先 `numeric.from_float`、mapping 键显式排序、sequence 走业务键序、None 写 `null`）、`:153`（`sha256_text`）、`:242`（`reproducibility_hash`）、`:272`（装配点）。载体字段 `dsm/models.py:1227 AuditBundle.reproducibility_hash`（[L1051] 第 15 项）。
- **环境量一律不入哈希**：`run_id`、`run_at`、绝对路径、主机名、输出文件名只留在 bundle 里（`dsm/audit.py` 模块 docstring 第 17-21 行）。

### 7.2 当前实测值

```
4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7
```

- 评价期 **2026-Q2**，**两连跑精确相等**，`exit_code` 0/0，长度 64（小写 hex）。
- 登记：`ops/dag-state.json → reproducibility_evidence.current_hash` / `current_hash_asof = 358b4ea`；ORCH-34 第 7 条纠正旧值 `8083efc9…`（已作废）。
- 交叉验证：P3b-prep（`d228edd`）用 `tools/repro_offline.sh` 在 **L3-strong** 隔离下四轮独立实跑（18/16/17/22 秒）得到同一哈希（来源：commit `d228edd` 的提交信息，本包未重跑该工装）。
- 断言载体：`tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs`；本包实测该单条 **`1 passed, 20 deselected in 0.69s`**。

### 7.3 **它将随 A1c 与 MODELS-1 落地而变 —— 属预期，不是回归**

`ops/dag-state.json → reproducibility_evidence.invalidation_log` 是本 RUN 的**失效台账**（ORCH-33 第 3 条把失效原因改为「双记」，纠正 ORCH-30 只预声明 A1c 的遗漏）：

| seq | 原因 | 前 → 后 | 预声明者 | 状态 |
|---|---|---|---|---|
| 1 | SEAM-1 commit `8f2eca3`：锚定参考尺改为不按池裁剪，normalize 输出变化 | `8083efc9…` → **`4de4b8cb…`** | 无（ORCH-30 遗漏，已由 ORCH-33 第 3 条纠正） | **已发生**（T+5.53h），SEAM-1 与 P3a-prep 双向独立实测一致 |
| 2 | MODELS-1：`NormalizedFrame` 增 frame 级披露通道 + `PoolKey.evidence_class` 可选 | `4de4b8cb…` → 待测 | ORCH-32 第 2/4 条 | pending |
| 3 | A1c 受控解冻 fixtures（D-A1-02/03/04/05/06/07/08） | 待测 → 待测 | ORCH-30 第 5 条 | pending |

**P3b 的最终判据**（`reproducibility_evidence.p3b_criterion` 逐字）：「最终判据 = A1c 与 MODELS-1 均落地后重测的哈希，在全新 clone + 断网单机 + 同 seed 下两连跑精确相等；**不是**与 `8083efc9` 相等」。

### 7.4 残留限制（不得宣称已覆盖）

当前唯一能产出真哈希的路径是**测试侧**的 `tests/test_integration_spine.py:146 _run_chain`（`:480` 调 `dsm/audit.py:242`），它读 `fixtures/input/**` 的冻结真数据、按 M29 L1330-L1358 跑真实九步，但治理入参来自该测试文件 `:74` 的 `GOVERNANCE` 字典 —— **不是 `dsm score` 的 CLI 端到端运行**：`dsm/cli.py:199` 的 `reproducibility_hash` 仍是 `PLACEHOLDER`，且 `config/` 为 0 文件时 CLI 根本跑不到 Step 1。因此「config/ 为空」不阻塞该哈希产出，但也意味着**该哈希尚未覆盖 CLI 端到端链路**，这是 V-10 的残留限制（来源：`docs/deliverables/P3b-REPRO-HARNESS.md` §1.2）。

### 7.5 第二人复跑怎么做

```bash
cd /home/szf/dev/strategy-eval-dsm
tools/repro_offline.sh --strict-isolation --expect <64 位期望哈希>
# 常用可选项（逐字摘自该脚本头部注释）：
#   --src /path/to/repo --python /path/to/python
#   --wheelhouse /path/to/wheels --runs 2 --keep --no-pytest
```

脚本做的事：从**本地路径**全新 `clone --no-hardlinks` 到 `mktemp -d`（本地提交未 push，故不走远端）→ 建独立 venv 只从本地 wheelhouse `--no-index` 安装 → 整个过程放进 `unshare -rn` 网络命名空间 → 同 seed 连跑 N 次（默认 2）逐次比对 64 位 sha256 → 打印 PASS/FAIL + 哈希 + 截至 commit，并以 exit code 0/1 表达；`mktemp -d` + `trap` 自清理故**幂等**。`--strict-isolation` 表示「隔离级别非 L3-strong 即判 FAIL」，**P3b 正式签核必须加**。
**未做的部分**（P3b-prep 自披露 6 项 `PLACEHOLDER`，见 `docs/deliverables/P3b-REPRO-HARNESS.md`）：其中包含「**未做异机第二人复跑**」—— 即 SDD L1640 的「第二人」目前仍是**同机同人**，V-3 因此维持 ⏳。
---

## 8. 当前状态（诚实节）

> 本节是全篇最重要的部分。**不掩饰、不美化、不推测**：凡未通过的一律写明「缺什么」，凡本包无法核实的一律写 `PLACEHOLDER`。

### 8.1 全量测试：13 条红的逐条归责

`13 failed / 2182 passed / 0 error / 0 skipped / 0 xfailed`（collected **2195**），截至 commit **`358b4ea`**。
来源：`ops/dag-state.json → pytest_baseline.after_R15B2_and_P3aprep`（`verified_by` = R15B2 `db13471` 与 P3a-prep `358b4ea` 双向独立实测一致；ORCH-34 第 6 条定为权威基线）。13 条红的归责照该节点的 `attribution` 逐字转录：

| # | 失败集合 | 条数 | 归责（`attribution` 原文） | 缺陷状态（本包实测 `defects`） |
|---|---|---|---|---|
| 1 | `tests/test_integration_spine.py` | **6** | MODELS-1（ORCH-32：D-MODELS-01 + 单值槽契约缺陷） | `D-MODELS-01` = **OPEN** |
| 2 | `tests/test_golden_a.py` g04 / g08 | **2** | A1c（D-A1-02） | `D-A1-02` = **OPEN** |
| 3 | `tests/test_golden_b.py` g05 | **1** | A1c（D-A1-08 anchor_set 覆盖不足） | `D-A1-08` = **OPEN** |
| 4 | `tests/test_golden_b.py` g06 | **1** | A1c（D-A1-02） | `D-A1-02` = **OPEN** |
| 5 | `tests/test_golden_b.py` g07 | **1** | D-D2-01（**本 RUN 不修，交下一版本**） | `D-D2-01` = **OPEN-WONTFIX-THIS-RUN** |
| 6 | `tests/test_golden_b.py` g10 | **1** | D-SPEC-G10（ADJ-G10 取证中，待 ORCH-35） | `D-SPEC-G10` = **CLOSED-BY-ORCH-35**（裁决已出，落地在 E3b 改测试期望 + P2 核验 `preflight.py:209-211`） |
| 7 | `tests/test_golden_b.py` g14 | **1** | D-A1-07 + `MIX_QUALITY_DEGRADED` 口径分歧（ADJ-G14 取证中） | `D-A1-07` = **OPEN** |

合计 6+2+1+1+1+1+1 = **13**（对账通过）。

> 关于 g10：ORCH-35（commit `82d5a6a`，ADR `docs/adr/RUN-ORCH-35-g10-dimension-emptied-conflict.md`）已裁「**规范判据取 M22 C-02（SDD L901）：实现正确、测试期望过严**」，即该条红属**测试构造错误**而非实现缺陷，修法归 E3b（改期望 + 改名 + **新增**「清空 ≥2 维 → BLOCK + exit_code 2」的测试，该分支此前零覆盖）。裁决前该测试**保持 RED，禁止任何一方反填**（R-14）。
> **最新观测（本包实测，供对账，不替代上表）**：MODELS-1 落地于 commit `cc18a38` 后，本包在干净提交树上复跑全量得 **`11 failed, 2190 passed`** —— spine 由 6 → 4（归责第 1 行的两条已由 MODELS-1 修掉），其余 7 条（golden_a 2 + golden_b 5）**归责不变**。`ops/dag-state.json → pytest_baseline` 尚未登记 `cc18a38` 的新基线节点（末节点仍为 13/2182 @ `358b4ea`），故上表仍是**已入账的权威归责**；新节点须由主控登记。
> 关于 g07：D-D2-01 的症状是「LOO 无『影响力』量度」——手算按「剔除后综合分跨度」排序得 `M_REV_MINOR`（S-009 1.268600000000 → 1.148600000000，跨度 0.120000000000 最大），实测按 flip 数排序得 `(M_CONTACT_FREQ_PER_30D, M_SATISFY_SCORE)`。处置（ORCH-33 第 5 条）：**本 RUN 不新增实现**（超范围 + 无剩余预算），写入 KNOWN-GAPS 与 V-ACCEPTANCE-EVIDENCE 的未覆盖项，**交下一版本**。

### 8.2 验收判据 V-1 ~ V-20

来源：`docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（P3a-prep，commit `358b4ea`）的「修订后汇总」节，逐字：

- ✅ **12 条**：V-4、V-5、V-6、V-8、V-9、V-11、V-12、V-13、V-16、V-17、V-18、V-19
- ❌ **3 条**：**V-1**（G-01~G-15 实测 7 条 RED，缺 A1c 补 fixtures + P2 归属裁决）、**V-7**（golden G-05 实测 FAIL：新增极值策略改变了存量 S-011 的 `composite_absolute` 0.967705891652 → 0.968545891652；**同一判据的属性层 P-4 与模块级 G-05 仍全绿，两者结论相反**，ORCH-34 第 5 项裁「采信 golden 层实测，根因登记 D-A1-08，不得以属性层绿掩盖」）、**V-14**（无 M28 26 行逐条遍历守护 + G-10 实测反例）
- ⏳ 待 P2 复测 **5 条**：V-2（hypothesis 500 例未跑，现档 `max_examples=25`）、V-3（第二人全新 clone + 断网复跑未做）、V-10（断网 clone 未做）、V-15（FROZEN 权重的**正向** provenance 实例不存在，`provenance = null`）、V-20（括注「G-01~G-15 全过」实测不成立）
- 合计 **20 条**（对账通过）。
- **四条不可砍底线**（该文件逐字）：V-9 数值口径 ✅ / **V-14 无静默降级 ❌** / V-6 + G-03 + P-2 红线非补偿 ✅ / G-02 + P-6 证据门禁与分池禁混排 ✅（但 **G-14 的 `MIX_QUALITY_DEGRADED` 口径分歧实测未决**）。
- **披露项 D-1 ~ D-12 全部在册**（该文件第二节），其中 D-11 是本表全部结论的**适用边界**：所有结论只在「**用合成数据跑通机制**」口径下成立，**不得输出任何可用于真实资源配置的分数或等级**（SDD M39 L1797）；D-12 是 P3a-prep 复跑时发现的 **5 处与既有上报不符**之处（含 SEAM-1 自报「10→9」实测为 8、ORCH-29「全文件无 lambda」实测 grep=8 但均为 `sorted` 排序键而非加权系数、dag-state 旧哈希 `8083efc9` 已失效等），ORCH-34 的 `p3a_discrepancies_accepted` 已逐条采信实测值。

### 8.3 `config/` 为 0 文件 → 任何真实运行按退出码 3 拒绝（**这不是 bug**）

- 实测：`find config -type f | wc -l` = **0**。
- 后果：`dsm/config.py:449` 的 `load_all()` 在缺失 `REQUIRED_CONFIG_STEMS`（5 个固定 stem + `weights_*.yaml` 通配，共 **6 类**）时抛 `ConfigPlaceholderError`，按 `dsm/config.py:71` 的 `EXIT_CONFIG = 3` 拒绝（实测输出见 §5.4；SDD M29 L1328 同口径）。
- **定性**：这是 **K-01~K-35 待业务签认**的直接后果，**不是缺陷**。SDD 的设计意图就是「任何业务数值未签认 → 配置加载直接失败，**不出分**」——宁可不评，不可错评。对应门禁 **G7「治理配置已签认」= 未完成且无载体**（`docs/deliverables/KNOWN-GAPS.md` F-2 行，逐字引 M39 L1794）。
- G7 未过时的合法动作（M39 L45）：**仅允许**合成数据全流程 / 演示报告 / whatif 预演；**不得**输出可用于真实资源配置的分数或等级。该声明必须进报告首屏，实测有守护：`tests/test_reports.py::test_gate_not_passed_puts_statement_on_first_screen`（PASS，来源 V-ACCEPTANCE-EVIDENCE D-11）。

### 8.4 K-01~K-35 全部 PLACEHOLDER；KNOWN-GAPS 计数

- **K-01 ~ K-20：20 项全部 `PLACEHOLDER`**，无一脱离。来源：`docs/deliverables/K-SIGNOFF-CHECKLIST.md`（P3c-prep，commit `fb68af8`），唯一事实来源为 `docs/digest/M38-k-params.md`（SDD L1734-L1760 逐字）。报告侧亦把 20 项全部渲染为 `PLACEHOLDER`（`dsm/reports.py:71 OPEN_PARAMETER_IDS` + `:467-468`）。
- 该清单自带计数小结（逐字）：有代码落点的 K 项 **19/20**，**无落点 = K-07**（`min_sample_size_for_A` / 显著性水平 / MDE 在 `dsm`、`tools`、`tests` 全部 grep 无命中 → **证据 A 类判定未实现该判据**）；M38 原文给了建议值的 **7 条**（K-05、K-08、K-11、K-15、K-18、K-19、K-20），其余 **12 条原文未给数值，一律未代拟**；K-11/K-15/K-20 存在「sensitivity 或 weights_combine 给默认 vs weights_calibrate 拒默认」的**双轨不一致**，备注为「半」，裁决归主控/行方。
- **KNOWN-GAPS.md：45 条**（A 10 + B 10 + C 8 + D 7 + E 8 + F 2，本包 grep 实测逐行计数一致）。
- **阻塞条数：本包实测 24 条，与该文件自称的「19 条」不符 —— 如实披露。** 该文件「汇总计数」节写「『是否阻塞交付』= 是：**19 条**」，但紧随其后自己列举的括号内条目为 A-10；B-2/3/4/5/7/8；C-1~C-6、C-8；D-1~D-6；E-6、E-8；F-1、F-2 = **24 条**；本包逐行 grep「阻塞交付」列为「是」（含 F-1/F-2 的加粗 `**是**`）也得 **24 行**。**三证中两证为 24**，故本 README 以 **24** 为准，并把「KNOWN-GAPS 汇总计数 19 与其逐行列举 24 自相矛盾」登记为**待 P3c 正式包更正项**（本包写集不含 `KNOWN-GAPS.md`，不得修改）。
- 其中**纯依赖行方签认**的：C-1~C-5、C-8、F-2，以及 K 清单全部 20 项。

### 8.5 文档勘误 ERRATUM-01 / 02 / 03

来源：`ops/dag-state.json → errata`（3 条，`at` = T+5.67h）与 `docs/adr/RUN-ORCH-35-g10-dimension-emptied-conflict.md`（commit `82d5a6a`）。

| ID | 位置 | 问题 | 处置 |
|---|---|---|---|
| **ERRATUM-01** | SDD **M31 L1412** 与 **§4.4 L1585** | 两处写「维度被清空 → BLOCK」，与规范判据 **M22 C-02（L901）**「未签认指标 → 剔除并重归一（WARN）；某维度被清空 → 该维度 W 置 0 重归一；**清空维度数 ≥ 2 → BLOCK**」不一致 | 本 RUN **以 L901 为准**（ORCH-35）；交业务签认。**若业务确认「单维清空即应阻断」，则属 C-02 阈值变更（≥2 改为 ≥1），须走契约变更流程**并同步改实现与该裁决，不得由本 RUN 单方决定 |
| **ERRATUM-02** | SDD **L911** 口径统一声明 | 其适用范围只逐字约束「C 表 vs DSN」，**对 M31 golden 表的权限未逐字明确** | ORCH-35 的裁决**不依赖** L911（改用内部一致性论证 + M28 L1286 第二来源），故不影响结论；该元规则争议**交签认** |
| **ERRATUM-03** | `dsm/reason_codes.py` 的 **`DIMENSION_EMPTIED`** | 该码名在 **SDD 全文 0 命中**，属工程自名 | 按 ADJ-3 **不改名、不删除**；其 severity / blocks_run 须服从 L901（单维清空场景 WARN / `blocks_run=False`）；P3a 披露「无原文依据」 |

ORCH-35 的**决定性理由**（ADR §2 逐字）：L901 同一句之内既规定「某维度被清空 → 该维度 W 置 0 重归一」，又规定「清空维度数 ≥ 2 → BLOCK」；**若单维清空即 BLOCK，则「W 置 0 重归一」一支永无执行机会而成为死条款**。原文在同句保留两支，证明单维清空被设计为可继续（WARN + 重归一），只有 ≥2 维才阻断；M28 L1286 同文构成第二来源印证。
> **本包收尾时的补充（存在性披露，不转述内容）**：本包观测末期，主控又入账了 **ORCH-36 / ORCH-37** 两条裁决（commit `a3a4701` / `bb89abc`），`ops/dag-state.json → errata` 实测已增至 **9 条**（`ERRATUM-01` ~ `ERRATUM-09`）。本 README 依派工范围只逐条展开 **ERRATUM-01/02/03**；**ERRATUM-04~09 的权威内容以 `ops/dag-state.json → errata` 与对应 ADR 为准**，本包未读取其正文，故不在此转述（R-12 不编造）。其中 ORCH-36 已就 **G-14 的 `MIX_QUALITY_DEGRADED` 口径分歧**作出裁决（提交信息逐字："分子改『C 类占比』（SDD L1416 唯一明文，C+D 零原文依据且使守护点 vacuous 违 V-14）"），即 §8.2 中 V-1 相关的那条未决口径**已有裁决、落地待 G14FIX**；ORCH-37 另立新参数 **K-21**（提交信息逐字），故 K 清单实际条目数可能已 >20，**以 `ops/dag-state.json → decisions.ORCH-36` 与 K-SIGNOFF-CHECKLIST 的正式定稿为准**。

另有两项原文缺口一并登记（ADR §1 补充事实）：`dsm/preflight.py:209-211` 的「全维清空也 BLOCK」分支**原文未找到独立依据**（归 P2 核验是否严格等价于 L901）；C-03「**孤儿**权重项」的定义**原文未找到**（保持实现现状不猜，登记 `PLACEHOLDER` 交签认）。

### 8.6 `reason_code` 注册数 90

- **90 码**（本包实测 `len(dsm.reason_codes.all_codes())` = **90**；来源交叉核对 `ops/dag-state.json → r15_batch_2.result`：改前实测 **79** + 新增 **11** = **90**，commit **`db13471`**）。
- 新增的 11 个码（`r15_batch_2.result.new_codes` 逐字）：`DESIGN_CARD_TABLE_ABSENT`、`DESIGN_CARD_DUPLICATE_KEY`、`SPEARMAN_ZERO_VARIANCE`、`H2_DIM_WEIGHT_BELOW_FLOOR`、`H3_METRIC_WEIGHT_BELOW_FLOOR`、`H5_SHIFT_FROM_AHP_EXCEEDED`、`REDLINE_EXCLUDED_FROM_ENTROPY`、`PRIMARY_POOL_REJECTED_GRADE`、`WEIGHT_DICT_MISALIGNED`、`APPROXIMATE_ATTRIBUTION`、`MISSING_FACT_RULE_APPLIED`。
- 严重度分布（**本包实测**）：**BLOCK 34 / WARN 42 / INFO 14** = 90。（对照：R15B2 之前为 BLOCK 28 / WARN 38 / INFO 13 = 79，见 V-ACCEPTANCE-EVIDENCE V-14 行。）
- **其中 2 个码的 severity 依据仍为 `PLACEHOLDER`，待业务签认**（本包实测 `dsm/reason_codes.py` 中 basis 文本以 `PLACEHOLDER:` 开头的码恰为这 2 个）：
  - **`SPEARMAN_ZERO_VARIANCE`**（当前暂定 **WARN**，`dsm/reason_codes.py:271-274`）：原文（M26 L1022-L1031、§2.6.4 L730-L740）只规定 mean_ρ 与阈值的两个结论与「可关 → `TRIANGULATION_DISABLED`（不得静默）」，**未给零方差情形的严重度列**。
  - **`APPROXIMATE_ATTRIBUTION`**（当前暂定 **WARN**，`dsm/reason_codes.py:322`）：M10 L674 只要求「标注」，**原文未给严重度列**。
  - 裁决：**ORCH-34 第 2 条** —— 维持暂定 **WARN**、**不得升格为 BLOCK**（ORCH-30：不得凭空升格严重级）；其正当性来源是 V-14（必须披露）而非门禁；P3a 必须把这两条列入「待业务签认」清单（与 K-01~K-35 同类）并在证据表披露节点名。
  - **勿混淆**：`CONFIG_PLACEHOLDER`（`dsm/reason_codes.py:35`，severity = **BLOCK**）是**码名**里带 PLACEHOLDER 的另一个码，含义是「配置中存在未签认的 PLACEHOLDER 字段，拒绝出分」，与上述「severity 依据为 PLACEHOLDER」不是一回事。
- 另需知道的口径更正：**`DESIGN_CARD_TABLE_ABSENT` 的退出码以 M21 L892 的 io 层 `4` 为准**（ORCH-34 第 1 条更正 ORCH-30 第 4 条的「退出码 2」笔误），且**不得**同时出现在 preflight 的 `RUN_BLOCKING_CODES`（退出码 2）里，否则一码两退出码属口径矛盾。
- KNOWN-GAPS B-10 曾记「实测 81 码」，`r15_batch_2.result.text_81_explained` 已查明：那是把 `_DYNAMIC_PREFIXES` 的 2 行前缀映射（`REDLINE_HARD_` / `REDLINE_SOFT_` → 模板码）误计为码，该 2 行不产生 RC 成员；**实测三证一致**（`_DEFS` 行数 = `len(list(RC))` = `len(all_codes())` = `len(_META)`）= 79（改前）。

### 8.7 其他本包实测到的、必须披露的事实

1. **`[project.scripts]` 缺失**：SDD L805/L836 要求「可执行入口 `dsm`」，实测 `pyproject.toml` 无该段 → 只能用 `python -m dsm.cli`（见 §5.1）。
2. **`--help` 误报 `exit=5 status=INTERNAL`**，但进程真实退出码为 0（见 §5.2）。
3. **`dsm/cli.py:199` 的 `reproducibility_hash` 仍是 `PLACEHOLDER`** → CLI 端到端链路不产出真哈希（见 §7.4）。
4. **KNOWN-GAPS 阻塞计数自相矛盾**（19 vs 24，见 §8.4）。
5. **架构碰撞 ratchet 白名单已失效 4 对**：`r15_batch_2.result.ratchet` 实测「改前 32 对 / 改后 32 对，fresh 碰撞 0；**实际仍发生 28 对，白名单中 4 对已失效（全在 `fixtures_gen`）**」；32 → 28 的收缩**排给 P2 且必须在 A1c 之后**（ORCH-34 第 3 条）。
6. **9 条 reason_code 接线待办未落地**：`dsm_stage/R15B2/CONSUMPTION-TODO.md` 共 9 条（含 `preflight.py:36-40 RUN_BLOCKING_CODES` 与 `:42-49 DISCLOSURE` 两个接线口），归属 A1c 或 P2（ORCH-34 第 4 条）；**强制检查项**：换 C-03 码（`WEIGHT_DICT_MISALIGNED`）时**必须同批**把该码加进 preflight 的 `DISCLOSURE`，否则 `_f()` 会抛 `PreflightError`。
7. **`models_questions` 4 项本 RUN 不做**（ORCH-31 第 3 条 / ORCH-34 第 5 条），已归 `dsm_stage/R15B2/MODELS-DEFERRED.md` 并交 P3a 归档进 KNOWN-GAPS。其中「A4 自述 whatif.py 有 8 个输出模型」**经实测为不实**（实测仅 1 个非异常输出类 `WhatifReport:232`），下一版本须按实测重写，**不得沿用 A4 的自述数字**。
8. **`dsm/pooling.py` 的调用点未接线**：MODELS-1 新增 kw-only `normalized` 参数，但 `dsm/cli.py` / `reports.py` / `whatif.py` 的调用点未传（ORCH-32 第 6 条，归 P2；MODELS-1 只登记 `dsm_stage/MODELS-1/HANDOFF-P2.md`，不改 `cli.py`）。
9. **邻仓只读基线本包已核验一致**：`/home/szf/dev/CampaignLab` → 分支 `m0-framework`、HEAD `0cccb76`、`git status --porcelain` 行数 **0**、`git rev-list --count HEAD` = **154**（四项全部与要求一致，本包未写该仓任何文件）。

---

## 9. 未覆盖范围与后续工作

### 9.1 本仓库**不**覆盖的范围（SDD 边界声明）

| 未覆盖 | 依据 | 现状 |
|---|---|---|
| **真实用户 / 真实客户数据** | SDD L1530「不需要数据库、不需要联网、不接生产库」；`frozen_fixtures.rule`「不使用任何真实客户数据」 | 全流程只用 **17 个合成 fixture 文件 / 896 事实行 / 5 期 / 12 策略 / 4 域**（冻结于 `ca31dd1`）。**未接任何真实数据源** |
| **行内授权 / 治理签认** | 门禁 **G7**「治理配置已签认」= 未完成（M39 L1794）；K-04 明文「红线阈值…**不得由模型方拟定**」 | `config/` 0 文件；K-01~K-35 全 PLACEHOLDER。签认动作属**行方（评价管理委员会）**，不属本 RUN |
| **争议来源复核** | 门禁 **G5**「D6 证据复核已完成」= **未完成 → 复核前全面禁用**（M39 L1792） | 本 RUN 无复核产物（`grep -rn D6 dsm/*.py` 无命中）；**任何争议来源结论禁止引用** |
| **生产对账 / 上线运行** | SDD L1526「实际耗时须**上线后实测**，本方案**不预估性能数字**」 | 无生产环境、无对账链路、无性能数字 |
| **因果增量（incrementality）** | 证据强度 A 类判据 = K-07（`min_sample_size_for_A` / 显著性水平 / MDE） | **未实现**：K-07 在 `dsm`、`tools`、`tests` 全部 grep **无命中**（K-SIGNOFF-CHECKLIST 计数小结）→ 当前无法据本仓库产出因果增量结论 |
| **CLI 端到端真实运行** | `dsm/cli.py:199` 的 `reproducibility_hash` 仍为 PLACEHOLDER；`config/` 空 → 退出码 3 | 九步真跑目前只在**测试内合成 GOVERNANCE** 下成立（§7.4） |
| **异机第二人复跑** | SDD L1640 | `tools/repro_offline.sh` 已具备全新 clone + 断网 + 同 seed 两连跑能力，但**尚未在异机由第二人执行**（P3b-prep 自披露 PLACEHOLDER）→ V-3 / V-10 维持 ⏳ |

### 9.2 后续工作（按已入账的分派，非本包拟定）

| 待办 | 归属 | 来源 |
|---|---|---|
| A1c 受控解冻并修 fixtures：D-A1-02 / 03 / 04 / 05 / 06 / 07 / 08 | **A1c** | `ops/dag-state.json → defects`（7 项 OPEN）；ORCH-33 第 2 条 |
| MODELS-1：`NormalizedFrame` 增 frame 级披露通道（warnings + excluded）、`PoolKey.evidence_class` 改可选、spine 改读 frame 级通道且**不得弱化原断言** | **MODELS-1** | ORCH-32 第 1~5 条 |
| P2 集成对齐 + 全量回归去红：**0 failed / 0 error / 0 新增 skip / 0 xfail** | **P2** | `docs/RUN-UNATTENDED-v3.0-PARALLEL.md` Phase 2 判据 |
| E3b：G-10 测试改期望 + 改名 + **新增 ≥2 维 BLOCK 测试**（该分支零覆盖） | **E3b** | ORCH-35 第 2 条 |
| P2：核验 `preflight.py:209-211`「全维清空也 BLOCK」是否严格等价于 L901；补「单维度体系被清空 → WARN 非 BLOCK」边界测试 | **P2** | ORCH-35 第 4 条 |
| P3a：V-1~V-20 证据表**定稿**（含 D-1~D-12 全部披露项 + ERRATUM-01/02/03） | **P3a** | ORCH-35 第 3 条、V 表前言 |
| P3b：A1c + MODELS-1 落地后**重测哈希**，全新 clone + 断网 + 同 seed 两连跑精确相等 | **P3b** | `reproducibility_evidence.p3b_criterion` |
| ratchet 白名单 32 → 28 收缩（须在 A1c 之后，且保留「只许缩短」方向） | **P2** | ORCH-34 第 3 条 |
| 9 条 reason_code 接线（fixtures 侧归 A1c，`cli.py`/`reports.py`/`whatif.py`/`preflight.py` 侧归 P2） | **A1c / P2** | ORCH-34 第 4 条 |
| **D-D2-01**：sensitivity 的 LOO「影响力」量度（按剔除后综合分跨度排序） | **下一版本** | ORCH-33 第 5 条，状态 `OPEN-WONTFIX-THIS-RUN` |
| `models_questions` 4 项（契约容器单点化） | **下一版本** | ORCH-34 第 5 条 |
| `[project.scripts]` console 入口、`cli.py:199` 真哈希接线、`--help` 的 `exit=5` 误报 | **P3c 正式包登记 / P2** | 本包实测（§8.7） |
| KNOWN-GAPS 汇总计数 19 → 24 更正 | **P3c 正式包** | 本包实测（§8.4） |

---

## 10. 纪律（实现层不可协商项）

- **数值口径**：金额与整数**精确相等**；比率与均值 **1e-12** 容差 —— **唯一实现点 `dsm/numeric.py`**（`numeric.TOL = 1E-12`），比较一律不走 pandas/numpy（SDD §3.1 L799）。守护：V-9 ✅（golden G-11 + P-07 + numeric 68 passed）。
- **PLACEHOLDER 拦截**：任何业务数值未签认 → 配置加载直接失败，**不出分**（`dsm/config.py:84-85` 词表 + `:71 EXIT_CONFIG=3` + `:449 load_all()`）。守护：P-10、V-5。
- **禁止静默降级**：任何降级都必须留 `reason_code` 与披露位置；`reason_code` 单一事实源 = `dsm/reason_codes.py`，**禁止散落字面量**（P-8 架构守护 + 碰撞 ratchet）。当前 V-14 仍 ❌（缺 M28 26 行逐条遍历守护）。
- **不读系统时钟**：运行时间由 `--run-at` **显式注入**（SDD L1089 / L1550）；MC 必须固定 `--seed`，**缺失则拒绝跑 MC**。
- **不覆盖历史**：重跑生成新 `run_id` 目录（`dsm/cli.py:135-138` 注释自述 `_new_dir` 追加 `-N`）。
- **不使用任何真实客户数据**（SDD L833）。
- **契约层**：pydantic v2 `frozen=True` + `extra=forbid`（SDD L797），未声明字段即报错。

---

## 11. 交付物索引

| 我想知道… | 去哪份文档 |
|---|---|
| 交付包由哪些文件构成、打 tag 的前置条件与发布步骤 | **`docs/deliverables/P3c-DELIVERY-PACKAGE.md`** |
| 某条验收判据 V-x 有没有实测证据 | `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`（四列表 + 披露 D-1~D-12） |
| 某个业务参数谁签认、代码落点在哪一行 | `docs/deliverables/K-SIGNOFF-CHECKLIST.md`（K-01~K-35） |
| 还有什么没做、是否阻塞交付 | `docs/deliverables/KNOWN-GAPS.md`（A~F 六类 45 条） |
| `reproducibility_hash` 怎么算、第二人怎么复跑 | `docs/deliverables/P3b-REPRO-HARNESS.md` + `tools/repro_offline.sh` |
| 为什么某处实现与原文不同 | `docs/adr/*.md`（32 份）+ `ops/dag-state.json → decisions` |
| 原文逐字与行号 | `docs/digest/*.md`（54 份摘录 + INDEX）—— **唯一事实来源**；本 RUN 铁律 R-5 禁止通读 SDD 2003 行全文 |
| 本 RUN 的宪章、铁律 R-1~R-18、包定义 | `docs/RUN-UNATTENDED-v3.0-PARALLEL.md` |

> **版本状态**：`v1.1.0` **尚未打 tag**。tag 必须在 **P2 全量转绿**之后由**主控**执行；打 tag 的可机械核验前置清单见 `docs/deliverables/P3c-DELIVERY-PACKAGE.md` 第 2 节。

---

## 12. P3c-pre2 事实校正与「只差最终数字刷新」清单（ORCH-39 ~ ORCH-42）

> 本节由 **P3c-pre2** 写入，目的是把 README 推到**只差最终数字刷新**的定稿状态。凡与上文冲突处，**以本节为准**（上文保留原样以便对账，不做静默改写）。观测 HEAD `f27334d`。

### 12.1 复现哈希台账（**严禁修回**）

| 顺序 | 值（64 位） | 产生于 | 状态 |
|---|---|---|---|
| 1 | `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` | `8cd222c` | **superseded**（SEAM-1 前）|
| 2 | `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7` | `82d5a6a`（台账 seq1 的 hash_after，因 SEAM-1 @`8f2eca3` 锚定参考尺改动而变）| **superseded_by_A1c** |
| 3 | `e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d` | `6299245`（A1c 受控解冻 fixtures；连跑两次精确相等）| **superseded_by_G14FIX** |
| 4 | `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` | `42d5346`（G14FIX：`reject_reason` 新增 `PRIMARY_POOL_REJECTED_GRADE` 经 `grade_ledger.l1_gate_reasons` 进入哈希面）| **当前实测值**（两跑相等）|
| 5 | **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`**（本包在 `da4d0a9` 用修好后的工装实测：exit 0／PASS／L3-strong／两跑同值） | 最终 HEAD 复测（A1d @`f27334d` 起四次落地均同值，因 spine 评价期 2026-Q2 事实表完整 180=12×15、`IMPUTE_MEDIAN` 不触发；`audit.py:242` 只吃 score_card／grade_ledger／weight_version_id） | **已定稿**；ROB-1 的 `f437c0ea…` 属 non-canonical 测试内自测值，**不入台账**（K-36） |

- **P3b 判据（`reproducibility_evidence.p3b_criterion` 逐字）**：「最终 HEAD 上全新 clone + `unshare -rn` 真断网 + 同 seed 两连跑精确自等；**不是**与任何旧值相等」。工装 = `tools/repro_offline.sh`（@`d228edd`）+ `docs/deliverables/P3b-REPRO-HARNESS.md`，隔离级别 **L3-strong**。

### 12.2 `invalidation_log` 的 9 项 PLACEHOLDER 清单重核（P3C-draft §5.5 → 本包逐项重核）

| 原 PLACEHOLDER 项 | 现状（本包重核） | 是否已消除 |
|---|---|---|
| `invalidation_log` 的 `hash_after`（seq2／seq3 曾为「待测」）| **已补齐**：seq1 `8083efc9…`→`4de4b8cb…`、seq3（A1c @`6299245`）`4de4b8cb…`→`e5fa8ae0…`、seq4（G14FIX @`42d5346`）`e5fa8ae0…`→`e5923465…`，均为实测 64 位；seq5（A1d／LOO-1／P2-wire-A）的 `hash_after` 仍为 PLACEHOLDER | **部分消除**（seq5 待 P2-wire-B）|
| 异机第二人复跑 | **仍在**：本 RUN 无法完成（依赖行方／第二人环境），P3b-prep 自披露的 PLACEHOLDER 未变 | ❌ 仍在 |
| tag 是否代表「可上线版本」的口径 | **仍在**：`git tag -l` 实测 **0** 条，`v1.1.0` 由主控在 P2-wire-B 全量转绿后统一执行；G5／G7 未过 → tag **不代表**可上线，只代表「合成数据演练版」（宪章 §3.2 第239行未要求 G7 先过才能打 tag）| ❌ 仍在（口径须主控与行方确认）|
| **G5**（D6 证据复核）| **仍在**：`grep -rn D6 dsm/*.py` 无命中，本 RUN 无复核产物 → 复核完成前争议来源结论**禁止引用** | ❌ 仍在（依赖行方）|
| **G7**（治理配置签认）| **仍在**：`config/` 实测 **0 文件**，K-01~K-35 全部 PLACEHOLDER；真跑在 `config.load_all()`（`dsm/config.py:449`）按 `EXIT_CONFIG=3`（`:71`）拒绝 | ❌ 仍在（依赖行方评价管理委员会）|
| **K-07**（`min_sample_size_for_A`／显著性水平／MDE）| **仍在**：在 `dsm`／`tools`／`tests` 全域 grep **无代码落点**，证据 A 类判据未实现 | ❌ 仍在 |
| `SPEARMAN_ZERO_VARIANCE` 与 `APPROXIMATE_ATTRIBUTION` 的 severity 依据 | **仍在**：ORCH-34 第2条维持暂定 WARN、不升格，转业务签认 → 本包已立 **K-30** | ❌ 仍在（已编号化）|
| C-03「孤儿权重项」定义 | **仍在**：原文未找到（ORCH-35 第7条）；另 P2-wire-A 上报 `preflight.py:215-237` 的 C-03 应由 `CONFIG_SEMANTIC_ERROR` 换 `WEIGHT_DICT_MISALIGNED`（M22 [L902] 逐字 BLOCK）→ 归 C2（`KNOWN-GAPS G-15 #7`）| ❌ 仍在 |
| ERRATUM-01／02 的业务确认结论 | **仍在**：若业务确认「单维清空即阻断」，属 C-02 阈值变更须走契约变更流程；勘误总数已由 3 条增至 **11 条**（新增 ERRATUM-04~09 见 ORCH-36/37、**ERRATUM-10** combine 退出码以 M21 L892 的 io 层 4 为准、**ERRATUM-11** G-14 三口径 12／11／9）| ❌ 仍在 |

### 12.3 本 RUN 明确不做／不补的项（如实披露，不得读成已完成）

- **无 console script**（`D-CLI-01`，ACCEPTED-DISCLOSED，ORCH-39 第3条）：不补 `[project.scripts]`，避免写集扩散并与 P2-cli／P2-wire-A 抢 `pyproject.toml`。
- **无前端界面**；本 RUN **未接入**真实用户／行内授权／生产对账／因果增量；`CEL` 增量层契约在 v1 **保留未接入**（`CEL_NOT_CONNECTED`，`cel_contract_version` 保持 PLACEHOLDER → **K-31**）。
- **LOO 影响力的 CSV 载体不做**（ORCH-42 第4条 → **K-32**）：`SENSITIVITY_COLUMNS` 13 列不扩 `metric_id`／`loo_impact`（`tests/test_reports.py:355` 已钉表头，扩列属契约变更）。
- **G-14 的上期 PoolStats 载体不做**（ORCH-42 第5条 → **K-33**）：`Inputs`([L891])／`AuditBundle`([L1051] 十六列) 不加列；`_previous_pool_stats()` 返回 None，报告显式披露「本期不可比」（符合 V-14：不造假基线）。
- **whatif 的 GEOMETRIC 近似归因不做**（`KNOWN-GAPS G-19`）：非 LINEAR 一律抛 `WhatifOperatorError(CONFIG_SEMANTIC_ERROR)`。⚠️ 派工单要求登记为 `D-A4-02`，但 `dag-state` 已存在同号且 **CLOSED** 的 `D-A4-02`（`whatif.py:571` 裸字面量，fix_commit `9078201`）→ **撞号**，本包不自占该号，请主控改号（同 **L-12**）。
- **`M_REPEAT_USE_COUNT` 等指标签认面**、**g09 守护力 vacuous（K-28）**、**g07 docstring 陈旧值（K-26）**：分别归 P3a 披露／E3b。

### 12.4 待刷新的最终数字（本包一律不填）

| 项 | 现值 | 终值 |
|---|---|---|
| 全量 pytest（failed／passed／collected）| **1／2301／2302** @`da4d0a9`（0 error／0 skip／0 xfail，15.48s；原 11 红全部闭合，逐条名单见 `KNOWN-GAPS.md` §H-1）| **「0 failed」= `PLACEHOLDER-TO-REFRESH(CMB-1)`**；唯一红 = `test_methods_combine.py::test_build_draft_on_the_frozen_a1_fixtures`（`:502 assert 8 == 9`），二分实测归因 **A1c @`6299245` 的 D-A1-03**，最小修法 = `:502` 9→8 + `:483` docstring 同步 + 附 D-A1-03 引文（**禁** `>=`／删断言／skip／xfail） |
| `reproducibility_hash` | **`e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`** @`42d5346`，复测同值于 `0d8afeb`／`31eb1b2`／`93abfee`／`da4d0a9` | **定稿**（本包 `repro_offline.sh --strict-isolation` 两跑 64 位逐字自等） |
| `output_fingerprints` | **spine 面不可观测**：`bundle.output_fingerprints = {}`（真实出口 `reports.write_report_set` 无生产调用点，M29 marshal 未落地）→ **不得写「已变更」** | 64 位生产台账 `PLACEHOLDER-TO-REFRESH(主控)`；P2-wire-B 已实算七件 sha256[:16]：`report_md 102d2d973c949ef2`／`score_card_csv bf583dc0da2da0a6`／`grade_ledger_csv 7afe10893ff2d366`／`sensitivity_report_csv 219b0880ff44d67f`／`triangulation_md ec8733e1f1b15ded`／`audit_json b81016fbd1eea897`／`entropy_diagnostic_csv 98207523a05e569f` |
| `git rev-list --count origin/main..HEAD` | **57**（实测 @`66481b1`/AUD-FINAL 落地后；本包在 `da4d0a9` 另测 54；P3C-draft 的 34 **作废**）；`git tag -l` 实测 **0** | 主控 push 前重测 |
| ratchet（架构碰撞白名单）| **32 → 28 已落地**（P2-wire-B @`93abfee`；本包复跑 `tests/test_architecture.py` = **11 passed／0 failed**）| **已收口**：fresh **0**、stale **4 → 0**；失效四对全在 `dsm/fixtures_gen.py`（`MONEY_NON_INTEGER`／`REDLINE_HARD_M_COMPLAINT_RATE`／`REDLINE_HARD_M_CONTACT_FREQ_PER_30D`／`REDLINE_SOFT_M_OPTOUT_RATE`，归因 A1b @`0547190` 换成注册表符号）；新增 `COLLISION_INVENTORY_CEILING = 28` + `pairs <= CEILING` 断言**封死增长**（收紧非弱化） |
| `defects`／`errata`／`orch_lessons` | **27／11／12**（L-01~L-12）| 主控 push 前再核 |

- **邻仓只读校验（本包实测）**：`/home/szf/dev/CampaignLab` = `m0-framework`／`0cccb76`／porcelain **0**／rev-list **154**，与本包开工前一致，**未触碰**。契约文件 `开发设计文档-策略评价可辩护评分模型DSM-v1.1.md` 的 sha256[:12] = `708679e9a83d`、行数 **2003**，核验通过。
