# DSM v1.2 RUN —— 长程无人值守 DAG 交付提示词（Orchestrator 契约）

> 本文件是 v1.2 RUN 的**唯一权威派工契约**。任何子智能体开工前必须逐字读完 §0 与自己的 §3 小节。
> 观测基线：HEAD `b7a46df`（v1.1 已发布 `v1.1.0`，tag 指 `fd46872`）。契约文件
> `工行参考文件/开发设计文档-策略评价可辩护评分模型DSM-v1.1.md` sha256[:12]=`708679e9a83d` / 2003 行（**只读**）。
> 本 RUN 所有派工数字均由主控在 `b7a46df` 上实测取得（L-11：派工数字必须标观测 HEAD 与出处）。

---

## §0 身份、铁律与硬约束（不得改写）

**角色分工**：`Orchestrator`（主控）只派工 / 裁决 / 对账 / 实测，**永不写实现代码**；唯一例外是
`ops/dag-state-v1.2.json`（主控产物）与 `docs/**` 的收口定稿。子智能体只在自己的写集内动手。

**铁律**（沿用 v1.1 并在本 RUN 继续生效）：

- **R-12 禁编造**：拿不到实测值就写 `PLACEHOLDER-TO-REFRESH(<归属>)`，并写明缺什么。严禁第三方估价 / 性能数字 / 集成工作量。
- **R-13 提交纪律**：一包一 commit；`git add` **只点名自己的写集路径**，**严禁 `-A`**；禁 force / rebase / reset / amend / 切分支；`push` 与 `tag` **只有主控能做**，且在 RUN 末尾一次做完；遇 `index.lock` 重试 ≤10 次。
- **R-14 禁弱化**：**严禁把实现输出抄进 expects**；严禁删除/放宽断言、严禁用 `skip`/`xfail` 掩盖红条。允许「精确化」——但必须附手算或契约原文引用。
- **L-06 写链**：文本资产用 UTF-8 **无 BOM** + **LF** + 源码**无 TAB**；中文写完必须回读校验（不得出现 `?`）。
- **L-14 末尾 LF**：读改写文本资产必须**显式复用/补回末尾换行**；提交前必须以
  `python tools/normalize.py --check --changed-since <上一 commit>` 自跑门禁
  （默认形式在工作树干净时报 `changed 0 files`，**测不到自己刚提交的文件**）。
- **L-11 数字出处**：任何数字都要标「观测 HEAD + 命令」。包自述**不作为 ✅ 依据**，只有主控亲测才能上调验收三态。
- **只读邻居**：`/home/szf/dev/CampaignLab` 必须全程保持 `m0-framework` / `0cccb76` / porcelain 0 / rev-list 154；契约文件只读。每波次收工复核一次。
- **固定测试命令**：`/home/szf/venvs/dsm/bin/python -m pytest -ra --tb=short --continue-on-collection-errors`（`addopts` 已含 `-q`，**不要再加 `-q`**）。
- **槽位**：并发上限 **6**；包交付后**先 `close_agent` 再补位**。
- **模型路由（R-16）**：`spawn_agent` 必须显式传 `model` + `reasoning_effort`。C3→`qwen3.8-max`，C2/C1→`qwen3.8-flash`。
- **时间盒**：本 RUN 硬停 **6 小时**（预期 ~4h，依 v1.1 校准系数 k=0.2917）。到点未完成的包如实登记为遗留，**不得为赶点凑绿**。
- **PowerShell 陷阱**：`wsl bash -lc "..."` 双引号内**严禁** `$(...)`（PowerShell 会在错误 cwd 展开）；一律用单引号或落地 `.sh` 脚本文件再执行。

**升级规则**：同一包 + 同一错误签名 + 连续 2 次未过门禁 → close 原 agent → `qwen3.8-max`/high 重派同一包（附两次失败日志原文）。

---

## §1 目标与「不做」清单

**目标**：关掉 v1.1 移交的 **4 条工程阻塞项**与 **8 条 ⏳**，使 **V-14 具备由 ❌ 上调 ✅ 的四项齐备条件**。

**V-14 转正四项齐备判据（缺一不得上调）**：
1. M28 降级矩阵 **26 行**（契约 SDD **L1280–L1305**）逐条遍历断言落地且全绿； 【**DOC-FINAL-A 落地实况（@`50fa9e0`）**：已落地 = M28-1 `ecb5535`（26 行 × **5 列**／885 行／161 断言，采渲染层口径 ORCH-56，**非端到端**）；列数更正见 ERRATUM-V12-05。本项判据本身**不因此齐备**——V-14 仍 ❌（见 §1 第 3 项与 KNOWN-GAPS §I）。】
2. M29 **九步 marshal** 本体落地（契约 §3.15.1 流程图 L1325–L1358）：`dsm/cli.py:319 _chain_gate` 在模块齐全时**不再** `raise InvariantError`（现 `:333`）；
3. G-15 **reason_code 六条**接线完成（重复键不再静默取后一行等）； 【**实测 4/6（ORCH-63 维持阻塞）**：已接 = RC-1 `877b8fb`（#2 重复键出码 / #3 零方差 Spearman 带码入 flags / 三角 verdict 静默补披露）+ RC-2 `dcb6f21`（#4 熵权组合逐条 append / #7 C-03 换码 `WEIGHT_DICT_MISALIGNED`）；未接 = **#5** `REDLINE_EXCLUDED_FROM_ENTROPY` 逐指标披露、**#9** `attainment.py:524/:528/:532` 合成行换 `MISSING_FACT_RULE_APPLIED` ⇒ 延期 v1.3 = **NG-V12-19**；本项**未齐备**，本棒不改判。】
4. `dsm/cli.py` 约 `:918` 的 `except OSError: return None` 静默降级返工为**显式 reason_code + 报告披露**。

**明确不做（本 RUN 范围外，违则判越界）**：
- ❌ 不做 **G5（F-1 D6 复核）** 与 **G7（F-2 治理配置签认）**：属行方，9 条阻塞项我方不可代闭合。
- ❌ 不做 **C-1~C-6 / C-8** 口径签认：只能送签，签认前一律标「推断 / 合成待签认」，**V 表不得记已验证**。
- ❌ 不做 LOO 的 **CSV 载体**扩列（`reports.SENSITIVITY_COLUMNS` 13 列被 `tests/test_reports.py:355` 钉死 = 契约面表头变更）。
- ❌ 不改 `dsm/models.py` 的冻结容器结构（R-15 单点化，v1.1 已定）。
- ❌ 不移动已发布的 `v1.1.0` tag；不改写 v1.1 台账 `ops/dag-state.json`（那是发布记录，只读）。
- ⚠️ **M29-3 的演练 config 只是「合成待签认」样例，绝不等于 G7 已签**；文档与 README 首屏的
  「G5/G7 未过 → 不得输出可用于真实资源配置的分数或等级」声明**一字不得改**，且必须有测试守护。

---

## §2 DAG（三波次 / 6 槽 / 高低搭配）

**写集互斥已主控校验**：`dsm/cli.py` 单写者 = M29-1（含 OSError 返工，故 CLI-1 并入 M29-1）；
`dsm/triangulation.py` 单写者 = RC-1；BK-3（补末尾 LF）触碰 9 个文件与 RC-1/V2-500 撞车，**必须排到末波单独执行**。

```
波次1 (6 槽并发, 2×max + 4×flash)
  M29-1 ─┬─> 波次2 M29-2 ─┬─> 波次3 收口
  RC-1  ─┴─> 波次2 M28-1 ─┘         (V-DOC-FINAL → 全量 pytest → 签核 → tag v1.2.0)
  V2-500 (独立)                     BK-3 (独立, 必须在所有代码包之后)
  V4-3L  (只读)                     BK-4 (docs, 依赖 V-DOC-FINAL 前序数据)
  V20-G  (只读)
  M29-3  (独立, config/ 新文件)
波次2 (≤6 槽)
  M29-2 (依赖 M29-1) · M28-1 (依赖 M29-1 + RC-1) · M29-3 · V15-PROV (只读)
波次3 (收口)
  BK-3 · BK-2(取证回填, 主控落盘) · BK-4 · V12-DOC-FINAL · 主控: 全量 pytest + 签核 + push + tag
```

| 波次 | 包 | 复杂度 | 模型 / effort | 写集（**互斥**） |
|---|---|---|---|---|
| 1 | **M29-1** | C3 | `qwen3.8-max` / xhigh | `dsm/cli.py`、`tests/test_cli_marshal.py`(新) |
| 1 | **RC-1** | C2 | `qwen3.8-flash` / high | `dsm/preflight.py`、`dsm/triangulation.py`、`tests/test_reason_codes.py` |
| 1 | **V2-500** | C1 | `qwen3.8-flash` / low | `tests/test_properties_all.py` |
| 1 | **V4-3L** | C2 | `qwen3.8-flash` / medium | 只读 → `dsm_stage/V12-V4-3L/` |
| 1 | **V20-G** | C2 | `qwen3.8-flash` / high | 只读 → `dsm_stage/V12-V20-G/` |
| 1 | **M29-3** | C2 | `qwen3.8-flash` / medium | `config/**`(新)、`tests/test_config_dryrun.py`(新) |
| 2 | **M29-2** | C2 | `qwen3.8-flash` / high | `dsm/cli.py`、`dsm/reports.py`、`tests/test_report_set_outlet.py`(新) |
| 2 | **M28-1** | C3 | `qwen3.8-max` / high | `tests/test_downgrade_matrix.py`(新) |
| 2 | **V15-PROV** | C2 | `qwen3.8-flash` / medium | 只读 → `dsm_stage/V12-V15-PROV/` |
| 3 | **BK-3** | C1 | `qwen3.8-flash` / low | 9 个非 docs 文件（**仅补末尾 LF**） |
| 3 | **BK-4** | C1 | `qwen3.8-flash` / low | `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` |
| 3 | **V12-DOC-FINAL** | C2 | `qwen3.8-flash` / medium | `README.md`、`docs/deliverables/{KNOWN-GAPS,P3b-REPRO-HARNESS,P3c-DELIVERY-PACKAGE}.md` |

---

## §3 逐包 brief

### M29-1 —— 九步 marshal 本体（**关键路径**，C3 / max / xhigh）
- **实测锚点**：`dsm/cli.py` 共 **960** 行；`_chain_gate` @`:319`，`:333` 现 `raise InvariantError('chain modules are all present but the nine-step marshal of ...')`；调用点 `:516`、`:526`；已有 seams `_anchor_set_doc`@`:337`、`_report_frames`@`:416`、`_render_reports`@`:431`。
- **契约依据**：§3.15.1 流程图（契约 L1325–L1358）逐字给出顺序：`config.load_all()` → `io_loaders`（8 表 + InputFingerprints）→ Step1 attainment → Step2 normalize → 旁路 diagnostics → Step3 evidence → Step4 redline → Step5 aggregate → Step6 grading → Step7 pooling → 旁路 triangulation → Step8 sensitivity（首屏可用性判定：`flip_rate > review_max` 或 `METHOD_DIVERGENCE` → `usable_for_elimination=false`）→ Step9 audit（manifest + reproducibility_hash）→ `reports.render`（report.md 10 段 + 5 张表 + audit.json）。
- **要做**：把 `_chain_gate` 从「拒绝」改为「真正串起九步」，复用**既有模块函数**（不得重写算法层）；顺带把 **`:918` 附近 `except OSError: return None`** 的静默降级返工为显式 reason_code + 披露（V-14 第 4 项）。
- **禁**：不得改 `dsm/models.py`、`dsm/evidence.py`、`dsm/reports.py`（M29-2 的写集）、`config/`（M29-3 的写集）。不得让 `dsm score` 宣称「可用于真实资源配置」。
- **验收**：新增 `tests/test_cli_marshal.py` 断言九步顺序与产物齐备；`_chain_gate` 在模块齐全时返回而非 raise；OSError 路径有 reason_code；**全量 pytest 0 failed**；`--changed-since` 编码门禁 RC=0。

### RC-1 —— G-15 reason_code 六条接线（C2 / flash / high）
- **实测锚点**：`dsm/preflight.py:320` `by_key = {(c.strategy_id, c.version_id): c for c in self.cards}` —— 字典推导**重复键静默取后一行**，`DESIGN_CARD_DUPLICATE_KEY` 从未触发（违 M18 [L1102] T4 粒度=策略×版本）；`dsm/triangulation.py:380-388 _pair` 捕 `DivisionUndefinedError` 后 `return None` **未带 `SPEARMAN_ZERO_VARIANCE`**；`:420-426 verdict` 在 `mean_rho is None` 时 `return None` 同样静默；`CONTRACT_DISCLOSURE_CODES` 定义在 `tests/test_reason_codes.py:65`（**15 个码**），该文件 390 行。
- **要做**：把 CONSUMPTION-TODO 第 2/3(模块侧)/4/5/7/9 条的消费点逐一落地，**每个降级都必须带码并能在报告中出现**。
- **禁**：不得改 `dsm/evidence.py`（v1.1 ORCH-41 禁改令；本 RUN 由 ORCH-49 有条件解除——**若确需改，先报 blocked 附差异表，由主控裁**）；不得改 `dsm/cli.py`。
- **验收**：`tests/test_reason_codes.py` 新增断言覆盖六条；重复键用例必须**真的抛/记码**；全量 pytest 0 failed。

### V2-500 —— hypothesis 500 例档（C1 / flash / low）
- **实测锚点**：`tests/test_properties_all.py:75` `MAXEX = settings(max_examples=25, deadline=None)  # R-11 dev-phase gauge`；该文件 **1276** 行、`def test_p*` **16** 个；`:5` docstring 已写明 500 例档待跑。注意 `tests/test_config_properties.py:350` 有 `assert 'max_examples=60' in source` 这类**自守护断言**——改档位前先 grep 是否有守护 25 的断言。
- **要做**：①先测 25 例档墙钟基线；②按线性外推**预估** 500 例墙钟并写入报告（预估≠实测，必须标注）；③落 500 例档（建议新增独立档位而非改掉开发档，避免拖垮日常回归）；④实跑 P-1~P-15 并记录**实测墙钟 + 结果**。
- **验收**：V-2 判据「P-1 至 P-15 全部通过（hypothesis 各 500 例）」有实测证据；开发档仍可快速回归。

### V4-3L / V20-G / V15-PROV —— 只读取证包（不写仓库）
- **V4-3L**：重建 3 层回溯抽查载体（A1c @`6299245` 重冻 fixtures 后原载体失效）。抽查任一分数判定路径 L1 `score_card.per_metric` → L2 `AttainmentRow` → L3 `fixtures/input/metric_fact.jsonl` + `metric_dict.jsonl`。
- **V20-G**：V-1 已 ✅，故 V-20 括注「G-01~G-15 全过」现可判。逐条实跑 G-01~G-15 守护测试并记录命令与输出。
- **V15-PROV**：provenance **七键**终值逐键抽查（`dsm/models.py:513-533 WeightProvenance`：`kind`/`ahp`/`entropy`/`combine`/`alpha_basis`/`whatif_run_id` + 签认四件套 `approved_by`/`approved_date`/`effective_from`），**逐键标注「合成值待业务签认」**（现值如 `whatif_run_id=WIF-SYNTH-2026-01`），严禁冒充签认真值、严禁填 K-01~K-20。
- 产物一律落 `dsm_stage/<PKG>/`（**gitignored**，不进 commit），并在回报里给出可复跑命令。

### M29-3 —— 演练用 config 样例集（C2 / flash / medium）
- **实测锚点**：`git ls-files config` = **0 文件**；`dsm/config.py:449 load_all()` 以 `EXIT_CONFIG=3`（`:71`）拒绝 → `dsm score` 端到端不可跑。 【**v1.2 实况更正（本棒 @`50fa9e0` 亲测）**：`git ls-files -- config` = **6 个跟踪文件**（`ahp_matrices.yaml`／`anchor_set.yaml`／`eval_config.yaml`／`grade_rules.yaml`／`redlines.yaml`／`weights_WV-SYNTH-2026.yaml`；M29-3 `ae2ca02` 入库 + CFG-1 `42a4084` 增 `soft_deductions` 顶层键），属**合成待签认演练样例，不等于 G7 签认**；「0 文件」为 v1.1 口径，保留为历史。】
- **要做**：造一套**完整但显式标注「合成待签认」**的演练 config，使端到端可跑通；每个治理值必须可追溯到 K 编号（K-01~K-40）并标 PLACEHOLDER 属性。
- **红线**：这**不是** G7 签认。README 首屏与交付包声明一字不改。

### M29-2 / M28-1 / BK-3 / BK-4 / V12-DOC-FINAL
- **M29-2**：给 `dsm/reports.py:799 write_report_set` 接**生产调用点**，使 `bundle.output_fingerprints`（`dsm/models.py:1247`，[L1051] item 10，file→SHA256；`dsm/audit.py:257` 校验）不再是 spine 面实测的 `{}`；同时闭合 **G-8**（`MIX_QUALITY_DEGRADED` 端到端可达）。
- **M28-1**：新建 `tests/test_downgrade_matrix.py`，对契约 **SDD L1280–L1305 的 26 行 × 六列**逐条参数化断言，且断言「**出现在报告中**」。现状（实测）：`grep -rn 'M28' tests/*.py` 仅 3 处命中且全在 `test_preflight.py` 的 docstring/注释（L6/L506/L596），**零断言**。依赖 M29-1 + RC-1。 【**ERRATUM-V12-05 更正（ORCH-56 · 本棒 @`50fa9e0` 亲验契约）**：契约 L1278 表头逐字 = `| 情形 | 检测点 | 降级动作 | 是否出分 | 披露位置 |` ⇒ **5 列**，不是六列；「六列」是 RUN doc 转录错误。M28-1 已按 **26 行 × 5 列** 落地 `ecb5535`（本棒实测 `wc -l tests/test_downgrade_matrix.py` = **885**、`grep -c assert` = **161**，非「断言零、无包领取」）。本行原句保留为派工单历史。】
- **BK-3**：给这 **9 个非 docs 文件**补末尾 LF（**纯字节追加、零内容改写**）：`dsm/diagnostics.py`、`dsm/triangulation.py`、`dsm/whatif.py`、`tests/test_diagnostics.py`、`tests/test_golden_a.py`、`tests/test_methods_whatif.py`、`tests/test_sensitivity.py`、`tests/test_triangulation.py`、`tools/repro_offline.sh`。目标：披露项 **16 → 7**。需主控授权（已在 ORCH-49 授权），**必须在所有代码包之后单独执行**。【**生效口径纠正（BK-3 `2db67aa` 本棒实测）**：`git show --stat 2db67aa` = **8 files changed**，非 docs 文件 = **8 个**（`dsm/diagnostics.py`／`dsm/whatif.py`／`tests/test_diagnostics.py`／`tests/test_golden_a.py`／`tests/test_methods_whatif.py`／`tests/test_sensitivity.py`／`tests/test_triangulation.py`／`tools/repro_offline.sh`），披露项由 **15 → 7**；「9 个文件、16→7」为派工单时点的过期口径，原句保留为历史。本棒 @`50fa9e0` 独立复扫（Python 逐文件读末字节）= **7 个缺末尾 LF，全部在 `docs/**`、非 docs 面 0 个**：`docs/adr/ORCH-19.md`、`docs/adr/RUN-A1c-fixtures-controlled-thaw.md`、`docs/digest/S1-T01{,b,c,d,e}.md`；与 `python3 tools/normalize.py --check` 的 `DISCLOSURE TRAILING_LF_HISTORICAL 7 of 204` 同源。本棒**未在**这 7 个文件上动笔（避免把披露项变成强制违规）。】
- **BK-4**：结掉 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md` 中残留的 6 处 `PLACEHOLDER-TO-REFRESH`（索引 #2/#3/#4/#6/#8/#10），每条写明「已定值」或「仍缺什么 + 归属」。
- **V12-DOC-FINAL**：V 三态重判（**只依主控亲测**）、KNOWN-GAPS 机械重算并与汇总节自证相等、README 与交付包刷新、tag 前置 ①~⑦ 逐条落稿。

---

## §4 v1.2 门禁（tag `v1.2.0` 前置，①~⑦ 一律不得放宽）

1. **①** 全量 pytest **0 failed / 0 error / 0 skip / 0 xfail**，标准形式与 `-o addopts= -q` 门禁形式**双跑**，由主控在最终 HEAD 亲测。
2. **②** V-1~V-20 全 20 条在册；每条 ❌/⏳ 有归属包 + K 编号 + 下一版条件；**V-14 只有在四项齐备时才允许上调**，否则维持 ❌ 并逐字保留原因。
3. **③** `tools/repro_offline.sh --strict-isolation --expect <新哈希>` 在**最终 HEAD** PASS，`L3-strong`、两跑 64 位逐字自等、`DIRTY=0`、`HEAD_STABLE=yes`。
4. **④** **权威哈希必变**（实现面改动）→ 必须重新登记，并在 v1.2 台账 `invalidation_log` 追加新 seq，写明新旧两值与归因；`v1.1` 的 `e5923465…` 作为历史保留，**不得沿用**。

> **④ 更正追记（ORCH-57 / ERRATUM-V12-06，主控已裁；原句保留为派工单历史，不改写）**：不再预设「哈希必变」，改为**登记最终 HEAD 上的实测值 + 未变更的机理说明 + 4 条正对照**。机理 = 复现哈希输入面是**值面**：`dsm/audit.py:231-239` 的 `canonical_text({schema, weight_version_id, score_card, grade_ledger})`，其中 `HASH_SCHEMA` = `dsm.reproducibility/v1`、`SCORE_CARD_HASH_FIELDS` = **34 列**（非 30；**ERRATUM-V12-08**）、`GRADE_LEDGER_HASH_FIELDS` = 5 列，**零源码指纹**（无 run_id／run_at／路径／主机名／输出文件名）⇒ 实现面改动与哈希变化**无必然关系**。实测值 = `实测值 = `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`（**ORCH-69 主控亲测 @`a81730d`**，与 v1.1 冻结值逐字相同 = **未变更**）`（PH-06；取门禁③阶段 A 的 RESULT 行 `HASH=`）；v1.1 冻结值 `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` 保留为历史；4 条正对照建议面 = ①改 `weight_version_id` ②改 score_card 任一入列值 ③改 grade_ledger 任一 grade ④越出 34 列改列集合。重登记安全性：`grep -rn e59234654f4e tests/ dsm/` = **0 命中**（主控亲测）。
5. **⑤** 只读邻居四项一致（`m0-framework`/`0cccb76`/porcelain 0/rev-list 154）+ 契约 `708679e9a83d`/2003 行未变。
6. **⑥** KNOWN-GAPS 机械清点与汇总节逐字相等；阻塞数从 **13** 下降的每条都要给关闭依据（commit / 裁决）。
7. **⑦** 工作树 porcelain 为空；编码门禁**三形式**（默认 / `--changed-since` / 提交后复跑）RC 全 0，四要素违规 0。

---

## §5 上报格式（每包收工必须逐字段回报，缺字段视为未交付）

```
PKG=<id> STATUS=done|blocked|partial COMMIT=<sha7> MIN=<墙钟分钟> HEAD_AT_COMMIT=<sha7>
WRITESET_OK=yes|no  WRITESET_ACTUAL=<逗号分隔实际改动路径>
PYTEST=<n passed / n failed>  TARGETED=<定向测试命令与结果>
GATE_CHANGED_SINCE_RC=<0|n>  LF_BOM_TAB=合规|违规明细
ACCEPTANCE=<逐条对照 §3 验收判据，写明实测命令与输出摘要>
GAPS=<新发现缺口：条件 + 缺什么 + 归属>
NOTES=<越界/超支/驳回建议/需主控裁决事项，如实写>
```

**纪律**：包**不得**自行 push / tag / `git add -A` / 改 `ops/dag-state*.json` / 改他人写集 / 改契约与邻居。
需要跨写集改动时 → `STATUS=blocked` 并附差异表，由主控裁决（v1.1 的 A1DPREP 驳回先例：主控曾驳回
`models.py:373` 改动建议，因双值串味 + 写集冲突 + 连带改 evidence.py）。

## §6 停止条件

- 达成：①~⑦ 全满足 + `v1.2.0` 已推送 → 出最终报告后停止。
- 未达成但到 6h 硬停：如实登记遗留（缺什么 / 归属 / 下一版条件），**不 push 半成品 tag**，出报告后停止。
- 任一核验失败（邻居被动、契约被改、哈希不可复现、门禁染红且无法在不弱化断言的前提下修复）→ **立即停止并上报，严禁自行强行凑绿**。


## §7 落地实况追记（DOC-FINAL-A 落笔 · 只追加不改写历史 · 观测 HEAD `50fa9e0`）

- **本 RUN 已落地（本棒 @`50fa9e0` 亲验 commit 存在 + 锚点复测）**：M28-1 `ecb5535`（降级矩阵 26 行 × **5 列**／885 行／161 断言）· CFG-1 `42a4084`（`config/grade_rules.yaml` 顶层键 `soft_deductions`，值取自 `tests/test_integration_spine.py:84`，**合成待签认**）· BK-3 `2db67aa`（8 files，披露 15→7）· T05-FIX `cba7320`（T05-M04 由字面 `== []` 改为三条泄漏检测，零弱化）· RC-1 `877b8fb`（G-15 #2/#3 + 三角披露；⚠️ subject 首字符混入 BOM = **ERRATUM-V12-03**，文件内容零影响）· RC-2 `dcb6f21`（G-15 #4/#7；#5/#9 明确不做）· CEL-EQ `b157e00`（`tests/test_cel_disabled_fieldwise.py` 1119 行插入）· M29-1 `a432ef6`（`_chain_gate` 真串九步 marshal + V-14 第 4 项返工）· M29-3 `ae2ca02`（config/ 6 件入库）
- **M29-1 调用链锚点（本棒 `git show 50fa9e0:dsm/cli.py` 与 `a432ef6` 双测同值）**：`:953 frames = _report_frames(` → `:959 fingerprints, render_details = _render_reports(...)` → `:1120 def _render_reports(...)` → `:1129 ...write_report_set(...)(report_set, run.dir)` ⇒ `cmd_score` 成功路真实写出七件产物；旧 raise 串已删（`grep -c "chain modules are all present" dsm/cli.py` = **0**）。v1.1 文本的 `cli.py:391`／`:406` 系过期行号（现值 `:1105`／`:1120`）。
- **在飞（本棒一律不预填结果）**：M29-2（`dsm/cli.py`／`dsm/reports.py`／新建 `tests/test_report_set_outlet.py`）状态 = `**`04cbe19`**（+ 翻面补钉 **`a81730d`**）`（PH-03／PH-21；取值命令 `git log --oneline -6`）；B12-FIX（`dsm/diagnostics.py`／`dsm/triangulation.py` + 两个新测试）状态 = `**`f213c1e`**`（PH-21；取值命令 `git log --oneline -6` 后跑 `python -m dsm.cli … score …` 并 `echo $?`，期望 RC=0，未修 = 5）。开工实测 `git status --porcelain` = ` M dsm/cli.py`（属 M29-2 在飞，本棒未触碰、未 add、未 stash）。
- **门禁终态登记**：① 全量 = `**`2444 passed in 20.67s`**（门禁① 标准形式，**ORCH-69 主控亲测 @`a81730d`**：独立 clone、porcelain 0、rc=0、`grep -c '^FAILED'` = **0**；第二形式 `-m pytest --continue-on-collection-errors -o addopts= -q` = **`2444 passed in 17.28s`**、rc=0；账目自洽 = `a432ef6` 基线 2418 + M29-2 新增 8 + B12-FIX 新增 18 = **2444**；v1.1 的 CMB-1 终值 2302 @`037b862` 保留为历史）`（PH-02；参考值 2418 passed / 0 failed @`a432ef6`，主控独立 clone）② V-2 500 例档 = `**`2444 passed in 20.67s`**（门禁① 标准形式，**ORCH-69 主控亲测 @`a81730d`**：独立 clone、porcelain 0、rc=0、`grep -c '^FAILED'` = **0**；第二形式 `-m pytest --continue-on-collection-errors -o addopts= -q` = **`2444 passed in 17.28s`**、rc=0；账目自洽 = `a432ef6` 基线 2418 + M29-2 新增 8 + B12-FIX 新增 18 = **2444**；v1.1 的 CMB-1 终值 2302 @`037b862` 保留为历史）`（PH-01）③ 阶段 A/B = `**ORCH-69 主控亲测 @`a81730d`**：RESULT 行逐字 = `RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=a81730d ELAPSED=18s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`；附属原文 `netns_probe = offline-confirmed` / `wh_manifest = verified(26 entries, sha256sum -c all OK)` / `run_#1 == run_#2 == e5923465…80904` / `RESULT_COMMIT = a81730dbb400a23bc50b81c5c8d7fd3bbfc069a9` / `stageA_rc=0` / 跑前跑后 porcelain 均 **0**；**载体 = 主仓库原地跑（非 clone）**，日志 `dsm_stage/V12-REPRO-PRE/out/prefinal_runA.log`。**PH-05 阶段 B 留坑** = `PLACEHOLDER-TO-REFRESH(主控@台账commit后的最终HEAD)`，原因：阶段 B 须与阶段 A 同 HEAD，而发版权威一跑在台账 commit 之后 ⇒ 其 RESULT 行与 `RESULT_COMMIT` **只记入 `v1.2.0` tag 消息、不回写文档**（避免移动 HEAD；ORCH-67）`（PH-04／PH-05，RESULT 行原文整行粘贴）④ 权威哈希 = PH-06（按 §1 第 4 项追记口径：实测值 + 机理 + 4 条正对照，**不预设必变**）⑤ 邻库／契约只读 = 本棒开工亲验：CampaignLab = `m0-framework`／`0cccb76`／porcelain `0`／rev-list `154`；契约 = `708679e9a83d`／**2003 行**／**177646 B** 三项逐位相符 ⑥ 阻塞数下降逐条依据 = 见 `docs/deliverables/KNOWN-GAPS.md` 汇总节（本棒落笔后机械清点）⑦ 编码门禁 = 本棒三形式实测均 **exit 0**：`NEEDS_NORMALIZATION 0 of <**ahead = 25 @`a81730d`**、**tag 计数 = 1**（仅 `v1.1.0`，`v1.2.0` 未打）；`git rev-list --count HEAD` = **143**（**ORCH-69 主控亲测 @`a81730d`**）。**push 前实测值以 `v1.2.0` tag 消息为准**（台账 commit 会使本数再变；ORCH-67）>`（开工 @`50fa9e0` = 204）＋ `DISCLOSURE TRAILING_LF_HISTORICAL 7 of <同上>`（**分母一律不写死**，取值命令 `python3 tools/normalize.py --check | head -4`）。
- **ERRATUM-V12-09（本棒登记 · 主控已裁）**：`_EXCEPTION_CODES` 中把 `WeightVersionInvalidError` 映射到退出码 **3** 的那一行，锚点 = **`dsm/cli.py:53`**（本棒逐 HEAD 实测 `git show <h>:dsm/cli.py | grep -n WeightVersionInvalidError`：`617e7a5`／`b157e00`／`a432ef6`／`50fa9e0` **四个 HEAD 同值 `:53`**；字典声明 `^_EXCEPTION_CODES = ` 起于 `:52`）。M28-1 自述与派工单／dag-state `carry_gaps_v12[NG-V12-23]` 所写「`cli.py:56`」有误。**本棒不改 M28-1 已提交测试文件的注释**（R-13 禁 amend／禁改 `tests/**`），`ops/**` 零写入 ⇒ 台账侧更正归主控。
- **收口次序（ORCH-58）**：内容包 → DOC-FINAL → 台账 commit → porcelain 0 → 门禁① 全量 → 门禁③ 阶段 A 取哈希 + 阶段 B `--expect` 复验 → `git tag -a v1.2.0 -F <tagmsg.txt>`（**四要素写进标签消息**，禁用 `-m` 防码页损毁）→ push main → push tag。**门禁③载体禁用 `git archive` 导出树**：`tools/repro_offline.sh:92` 逐字 `[ -d "$SRC/.git" ] || die "not a git repository: $SRC"`，导出树无 `.git` 会直接 die（本棒实测该行）。
- **三态裁定边界**：本棒（DOC-FINAL-A）**未改任何 V 项 ✅／⏳／❌**；三态裁定权只属主控（L-11／ORCH-49 第 6 条）。本棒仅在证据列补事实与写「具备上调条件，裁定待主控」。

### §7-B 收口终值与裁决转录（DOC-FINAL-B 落笔 · 只追加 · **ORCH-66／67／68／69 主控亲测 @内容面最终 HEAD `a81730d`**）

- **ORCH-67 HEAD 口径**：本节及全仓文档的「最终 HEAD」= **内容面最终 HEAD `a81730d`**（全 40 位 `a81730dbb400a23bc50b81c5c8d7fd3bbfc069a9`；porcelain **0**、`git rev-list --count HEAD` = **143**）；**发版权威 `RESULT_COMMIT` = 本棒之后的台账 commit**（主控提交），**记于 `v1.2.0` tag 消息、不回写本文档**（文档不得自指一个尚不存在的 commit）。落地链（新→旧）= `a81730d`(M29-2b) → `f213c1e`(B12-FIX) → `04cbe19`(M29-2) → `adc97fb`(DOC-FINAL-A) → `50fa9e0`(台账)。
- **§7 上方两条在飞坑位现已闭合**：M29-2 = **`04cbe19`**（+ 翻面补钉 **`a81730d`**）、B12-FIX = **`f213c1e`**；A 棒所写「在飞／待 B 棒实测」原句保留为其写入时刻实况。
- **门禁终态（转录，本棒未代跑）**：① 全量两形式 = **`2444 passed in 20.67s`**（标准形式）／**`2444 passed in 17.28s`**（`-o addopts= -q`），均 rc=0、`grep -c '^FAILED'` = **0**（独立 clone @`a81730d`，porcelain 0；账目自洽 = 2418 + M29-2 的 8 + B12-FIX 的 18）② V-2 的 500 例档 = **`16 passed in 14.71s`**、rc=0，且 `tests/test_properties_all.py:81 MAXEX_500 = settings(max_examples=500, deadline=None)`／`:86` 的三元选择证明 500 档**真的挂上** ③ 门禁③阶段 A（**主仓库原地**跑，非 clone；日志 `dsm_stage/V12-REPRO-PRE/out/prefinal_runA.log`）RESULT 行逐字 = `RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=a81730d ELAPSED=18s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest`，附属 `netns_probe = offline-confirmed`／`wh_manifest = verified(26 entries, sha256sum -c all OK)`／`run_#1 == run_#2 == e5923465…80904`／`RESULT_COMMIT = a81730dbb400a23bc50b81c5c8d7fd3bbfc069a9`／`stageA_rc=0`／跑前跑后 porcelain 均 **0**；**阶段 B = `PLACEHOLDER-TO-REFRESH(主控@台账commit后的最终HEAD)`**（原因：阶段 B 须与阶段 A 同 HEAD，而发版权威一跑在台账 commit 之后 ⇒ 只入 tag 消息）④ 权威哈希 = `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`（PERIOD=`2026-Q2`，**与 v1.1 冻结值逐字相同 = 未变更**）；机理 = 值面（`dsm/audit.py:231-239`；`HASH_SCHEMA = dsm.reproducibility/v1`／`SCORE_CARD_HASH_FIELDS = 34 列`／`GRADE_LEDGER_HASH_FIELDS = 5 列`；`grep -rn e59234654f4e tests/ dsm/` = **0 命中**）；**4 条正对照** = 改 1 处 fixture 数值 → `0e7716eb…`、改 `weight_version_id` → `d846ffc4…`、改 `HASH_SCHEMA` → `9d5ca8ab…`、改 PERIOD→`2026-Q3` → `e73e4b9b…`（证明屏非恒假）；反面对照 = 加注释／加末尾 LF／改 `SEED` → 不变 ⇒ **实现面变更由 `RESULT_COMMIT` 表达，不由 `reproducibility_hash` 表达**（ORCH-57／ERRATUM-V12-06）⑤ 只读复核 = 邻库 `m0-framework`／`0cccb76`／porcelain **0**／rev-list **154**（本棒开工、收工各亲验，两次同值）+ 契约 `708679e9a83d…`／**2003 行**／**177646 B** 三项全符 ⑥ 阻塞数下降逐条依据 = G-8 **CLOSED @`04cbe19`** 三件套（CLI 实跑 RC 对照 0／实验 0 ⇒ `UNCHANGED=True`；`report.md` ⑥ 段 `MIX_QUALITY_DEGRADED` 命中行逐字；交叉核对 `severity=WARN`、`blocks_run=False`、不在 `blocks_run_codes()`）+ E-6／G-14 的 A 棒改判未回退 ⇒ **阻塞 10／非阻塞 55／合计 65**（`count_gaps.py` 与正文同源）⑦ 编码门禁 = **`NEEDS_NORMALIZATION 0 of 207`** + `DISCLOSURE TRAILING_LF_HISTORICAL 7 of 207`（本棒三形式 rc 全 **0**；分母链 201→203→204→205→**207**）。
- **ORCH-69 三态裁定（本棒仅转录符号，未自行裁定）**：**✅15／❌1／⏳4**（合计 20；净上调 **+4** = V-2、V-4、V-10、V-20）；**V-14 维持 ❌、严禁上调**（六项接线 4/6，残项 #5／#9 = NG-V12-19 → v1.3）；**V-3／V-7／V-8／V-15 维持 ⏳**（本 RUN 无新的主控亲测证据，按「包自述不作 ✅ 依据」纪律，不得因相关测试已在 2444 条绿测内就上调）。**ORCH-69 更正**：ORCH-45 曾把 V-10[L1503]（断网单机可跑通）与 V-3[L1496]（第二人复跑）混为一谈而压住 V-10；二者判据不同，第二人／异机栏属 **V-3** 且仍为外部缺口。
- **ORCH-66 过渡钉翻面（非 R-14 弱化）**：`tests/test_cli_marshal.py:296` 的钉原为 M29-1 **自述有效期**（commit message 原文「bundle 内如实为 `{}`：生产出口归 M29-2（ORCH-59 预裁决），本包只保留 seam + 披露」）；M29-2 于 `04cbe19` 落地 ⇒ 前提按其自身声明**到期**，ORCH-66 批准翻面为六键口径（**`a81730d`，+6/−2，仅此一处**）。新钉 = 非空映射下界 `'s:output_fingerprints={}' not in body and 's:output_fingerprints={' in body`；六键**精确性**（键集恰等 `ARTIFACT_NAMES − {audit.json}`、逐值落盘重算、正文六枚对账、`audit.json` 自身哈希不入正文）由 `tests/test_report_set_outlet.py` 的 **8 条**断言承担 ⇒ 套件总强度**上升**。另 INV-A 非装饰：投毒第二遍 `report.md` ⇒ 退出码 5、`write_report_set` 调用 0 次、七件一件不落盘、只留 `audit_bundle.json`（`output_fingerprints={}`）。
- **ORCH-68（B4 裁决，照此口径不得软化也不得加码）**：**B4 不构成 V-14 违规** —— 退出码 5 + 点名注册错误 = **显式拒绝**，正是 [L1507]／[L1512]「无静默降级」所要求的行为，**不是**静默错值 ⇒ **不因此下调任何三态**；但它是**真实的开箱可用性缺口** ⇒ 新登 **NG-V12-29**（另非阻塞 NG-V12-30／31）。**PH-21 两口径必须并写**：签认 `gra_norm=initial` → **RC=5**（错误原文 `TriangulationError: GRA 无量纲化参考值为 0（gra_norm=initial），关联度未定义`）、签认 `mean` → **RC=0** 且七件齐备（`audit.json`／`entropy_diagnostic.csv`／`grade_ledger.csv`／`report.md`／`score_card.csv`／`sensitivity_report.csv`／`triangulation.md`）—— **禁止只写 RC=0 造成「开箱即用」的错觉**。本 RUN 不修三条理由 = (a) 诚实修法需**新注册码**、会打破 `all_codes()` = **91** 的钉子且 severity 需行方签认；(b) 改 `config/**` = 改**已签认业务值**（R-12 禁止）；(c) 时间盒。
- **ERRATUM-V12-10（本棒新立，PH-09 据此结案）**：派工单转述的 CEL-EQ 规模「**24081 比对路径／6 层**」**主控实测不予采信**（`grep -no '24081' tests/test_cel_disabled_fieldwise.py` = **0 命中**；`grep -nE 'LAYERS|_LAYER|layer'` = **0 命中**）；一律改用该文件自述实测口径 = `:39`「**3,278 个 Decimal 叶子**（**620** 个走钱款口径）」、`:544 tol_absorbed: int = 0`、`:870 assert diff.stats.tol_absorbed == 0`、定向 **`7 passed in 1.85s`** rc=0。勘误链 = v1.1 **12** 条 + v1.2 **9** 条（ERRATUM-V12-01…09）+ 本棒 **ERRATUM-V12-10** = **22 条**；台账入册归主控（本棒对 `ops/**` 零写入）。
- **PH-22 口径裁定 = 采纳 A 棒声明**：KNOWN-GAPS §I 的 `NG-V12-*` 行（现 **13** 行，NG-V12-19…31）**不计入** A~H 总账合计 **65**（`count_gaps.py` 行首正则本就不匹配），避免与 G-15／G-8 同源双计；此口径现为**主控裁定**，不再列为待定。
- **收口动作归主控（ORCH-58，本棒不执行）**：台账 commit → porcelain 0 → 门禁③阶段 B `--expect` 复验 → `git tag -a v1.2.0 -F <tagmsg.txt>`（四要素 + 阶段 B RESULT 行写进标签消息；**禁用 `-m`**）→ push main → push tag。
