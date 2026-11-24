# P3b 复现性签核工装（REPRO HARNESS）—— 前置实测与判据

**包号**：P3b-prep（可复现性签核的前置工装包）
**性质**：工装 + 实测证据，**不是** P3b 签核本身。P3b 正式签核必须在 A1c 与 MODELS-1 均落地后，重跑本包交付的同一条脚本。
**本包写集**（只有两个文件）：`tools/repro_offline.sh`（新增）、`docs/deliverables/P3b-REPRO-HARNESS.md`（本文件）。临时证据留在 gitignore 的 `dsm_stage/P3b-prep/`。
**未改动**：`dsm/**`、`tests/**`、`fixtures/**`、`config/**`、`ops/dag-state.json`、`tools/gen_golden.py`、`tools/normalize.py`。未 push、未 tag、未 amend。

---

## 1. `reproducibility_hash` 的确切定义与产出路径

### 1.1 定义（算法侧，逐行）

| 环节 | 位置 | 内容 |
| --- | --- | --- |
| 载荷拼装 | `dsm/audit.py:231` `hash_payload(score_card, grade_ledger, weight_version_id)` | `{'schema': HASH_SCHEMA, 'weight_version_id': …, 'score_card': _ordered(…), 'grade_ledger': _ordered(…)}` |
| schema 标签 | `dsm/audit.py:43` | `HASH_SCHEMA = 'dsm.reproducibility/v1'` |
| score_card 入哈希列 | `dsm/audit.py:84` `SCORE_CARD_HASH_FIELDS` | [L1612]-[L1626] 35 列中的 34 列（唯一例外见该处注释） |
| grade_ledger 入哈希列 | `dsm/audit.py:100` `GRADE_LEDGER_HASH_FIELDS` | 等级判定列 |
| 规范序列化 | `dsm/audit.py:113` `canonical_text(value)` | [L1053] 五条规则：Decimal 走 q12 定点 12 位、float 先 `numeric.from_float`、mapping 键显式排序、sequence 走业务键序（行按 `(strategy_id, version_id, period)`）、None 写 `null` |
| 取哈希 | `dsm/audit.py:242` `reproducibility_hash(...)` → `sha256_text(hash_payload(...))`（`dsm/audit.py:153`） | 64 位小写 hex |
| 载体字段 | `dsm/models.py:1227` `AuditBundle.reproducibility_hash` | [L1051] 第 15 项 |
| 装配点 | `dsm/audit.py:272`（`build_manifest` 内） | 由 `RunContext.score_card / .grade_ledger / .weight_version_id` 算出 |
| 复跑四步文本 | `dsm/audit.py:283` `rerun_steps(bundle)` | 步骤三即「比对 `reproducibility_hash`，必须精确相等」 |

**环境量不入哈希**（`dsm/audit.py` 模块 docstring 第 17-21 行）：`run_id`（[L1091]）、`run_at`（[L1089]）、绝对路径、主机名、输出文件名一律只留在 bundle 里。测试级证据：`tests/test_audit.py:167`（home vs foreign 路径同哈希）、`tests/test_audit.py:143`（两连跑相等）、`tests/test_audit.py:231-244`（改一个语义位即变）。

### 1.2 产出路径（本包实测查清，**如实记录，非臆断**）

> **当前唯一能产出真值的路径是测试侧的 `_run_chain`，不是 CLI 真实运行。**

* `dsm/cli.py:199`：`audit_context()` 返回的字典里 `'reproducibility_hash': PLACEHOLDER` —— CLI 链路**尚未**产出真哈希。
* `config/` 实测 **0 文件**（`find config -type f | wc -l` = 0）；`dsm/config.py:449` `load_all()` 在缺失 `REQUIRED_CONFIG_STEMS`（`dsm/config.py` 五个固定 stem + `weights_*.yaml` 通配）时以 `EXIT_CONFIG = 3`（`dsm/config.py:71`）拒绝。故 `dsm score` 的真实端到端运行**跑不起来**。
* 真值产出点：`tests/test_integration_spine.py:146` `_run_chain(root, period)` —— 读 `fixtures/input/**` 的冻结真数据，按 M29 [L1330]-[L1358] 九步跑真实模块，在 `tests/test_integration_spine.py:480` 调 `audit.reproducibility_hash(score_card, grade_ledger, weight_version_id)`。
* 断言载体：`tests/test_integration_spine.py:886` `test_reproducibility_hash_is_identical_across_two_runs`（即 `ops/dag-state.json → reproducibility_evidence.assertion` 登记的那一条）。

**结论**：现有哈希是「**测试内合成 config** 驱动的九步真跑」产出的，**不是** CLI 真实运行产出的。治理入参来自 `tests/test_integration_spine.py:74` 的 `GOVERNANCE` 字典（该文件 docstring 已声明每一项都有出处、非 spine 拟定），配置目录 `config/` **完全不参与**该哈希。→ 因此「config/ 为空」不阻塞该哈希产出，但也意味着 **该哈希尚未覆盖 `dsm score` 端到端链路**，这是 V-10 的残留限制（见 §5.3 P-4），P3b 签核不得宣称已覆盖。

### 1.3 该哈希依赖的输入（逐项）

| 输入 | 取值 | 出处 |
| --- | --- | --- |
| seed | `20260101` | `tests/test_integration_spine.py:65` `SEED = fg.SEED_DEFAULT` |
| 期次 period | `2026-Q2` | `tests/test_integration_spine.py:60`（历史窗口里事实表完整的一期；主评价期 `2026-Q3` 有 4 个刻意缺失单元格，Step4 跑不起来） |
| run_at | `2026-10-20T00:00:00+00:00`（注入时钟，H-8） | `tests/test_integration_spine.py:63`；**不入哈希** |
| run_id | `SYNTH-RUN-0001` | `tests/test_integration_spine.py:64`；**不入哈希** |
| fixtures | `fixtures/input/*.jsonl`、`fixtures/golden/**`、`fixtures/manifest.json` | 经 `_stage()`（`tests/test_integration_spine.py:120`）落到临时目录后由 `io_loaders` 读取 |
| 权重版本 id | `fg.OAT20_WEIGHT_VERSION_ID`（冻结 fixtures，status=FROZEN） | `_governance_docs()`（`tests/test_integration_spine.py:134`） |
| 治理入参 | `GOVERNANCE` 字典（合成，逐项有出处） | `tests/test_integration_spine.py:74` |
| config 目录 | **不参与** | `config/` 为 0 文件 |

---

## 2. 当前实测哈希与截至 commit（本包亲自复跑，未采信 P3a-prep 结论）

```
截至 commit   82d5a6a6174dd30f6316a4231c497a01c98eaf2f  (82d5a6a, branch main)
复现哈希      4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7
期次 / seed   2026-Q2 / 20260101        exit_code 0 / 0        len 64
两连跑相等    是（每次调用内部两跑相等；跨调用亦相等）
```

本包全部实测轮次（均在同一台 WSL2 主机）：

| 轮次 | 方式 | 截至 commit | 哈希 | 两跑相等 | 隔离级别 | 耗时 | 日志 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 直接探针 `dsm_stage/P3b-prep/hash_probe.py`（连跑 2 次进程） | `f358aa6` | `4de4b8cb…a202d7` | 是 | 宿主 venv（无 clone） | 3.3s | 会话记录 |
| 1 | `bash tools/repro_offline.sh` | `82d5a6a` | `4de4b8cb…a202d7` | 是 | **L3-strong** | 18s | `dsm_stage/P3b-prep/run-1.log` |
| 2 | `bash tools/repro_offline.sh --expect 4de4b8cb…` | `82d5a6a` | `4de4b8cb…a202d7` | 是 | **L3-strong** | 16s | `dsm_stage/P3b-prep/run-2.log` |
| 3 | 同上（探针临时目录清理补丁后） | `82d5a6a` | `4de4b8cb…a202d7` | 是 | **L3-strong** | 17s | `dsm_stage/P3b-prep/run-3.log` |
| 4 | 弱隔离降级验证 `--wheelhouse /nonexistent-wh --runs 1 --no-pytest` | `82d5a6a` | `4de4b8cb…a202d7` | 单跑 | **L1-weak（PLACEHOLDER）** | 1s | `dsm_stage/P3b-prep/run-4-degraded.log` |
| 5 | 同上 + `--strict-isolation` | `82d5a6a` | 同上 | 单跑 | L1-weak → **判 FAIL** | 1s | `dsm_stage/P3b-prep/run-5-strict.log` |
| 6 | **canonical 签核形态** `bash tools/repro_offline.sh --strict-isolation --expect 4de4b8cb…` | `82d5a6a` | `4de4b8cb…a202d7` | 是（+ pytest 断言 rc=0） | **L3-strong** | 22s | `dsm_stage/P3b-prep/run-6.log` |

**与 P3a-prep 报告的 `4de4b8cb…` 一致**：HEAD 已从 `358b4ea` 前进到 `82d5a6a`（在飞 lane 推进，属正常），期间该哈希**未变**。`ops/dag-state.json` 登记的旧值 `8083efc9…` 已早于 A1c 失效（见 §3）。

命令原文（可逐字重放）：

```bash
cd /home/szf/dev/strategy-eval-dsm
bash tools/repro_offline.sh --strict-isolation \
  --expect 4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7
# exit code 0 => PASS
```

---

## 3. 哈希失效台账（照 `ops/dag-state.json → reproducibility_evidence.invalidation_log` 三条）

| seq | hash_before | hash_after | 造成者（commit） | 时点 | 是否预声明 |
| --- | --- | --- | --- | --- | --- |
| 1 | `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` | **`4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7`**（本包实测补全 64 位；dag-state 原文为「`4de4b8cb(P3a/P3b 须补全 64 位)`」） | **SEAM-1 `8f2eca3`**：锚定参考尺改为不按池裁剪 → `normalize` 输出变化 | A1c **之前**（T+5.53h） | **无**。ORCH-30 第 5 条只预声明了 A1c，属**遗漏**，已由 **ORCH-33 第 3 条**纠正为「双记」口径 |
| 2 | `4de4b8cb…a202d7` | 待测 | **MODELS-1**：`NormalizedFrame` 增 frame 级披露通道 + `PoolKey.evidence_class` 变可选 | pending | ORCH-32 第 2/4 条 |
| 3 | 待测 | 待测 | **A1c 受控解冻 fixtures**（D-A1-02/03/04/05/06/07/08） | pending | ORCH-30 第 5 条 |

**纪律**：P3a/P3b 必须逐条记明「哪个 commit 造成哪次变化」，否则会把 SEAM-1 的变更错误归给 A1c。本包在 `f358aa6` 与 `82d5a6a` 两个 HEAD 上实测同值，说明 seq2/seq3 **都还没有发生**（A1c 与 MODELS-1 均未落地）。

---

## 4. P3b 的最终判据（照 `reproducibility_evidence.p3b_criterion`）

> **A1c 与 MODELS-1 均落地后重测的哈希，在「全新 clone + 断网单机 + 同 seed」下两连跑精确相等。**
> **不是**与 `8083efc9…` 相等，也不是与 `4de4b8cb…` 相等。

判据是**自等性**（self-equality），不是与任何历史值相等。因此：

1. seq2/seq3 落地后哈希**必然改变**，属预期非回归；
2. 签核只看：同一 commit 下，全新 clone + 断网 + 同 seed 的两次运行哈希逐字符相等，且 `bundle.exit_code` 均为 0；
3. 附带条件（本包脚本已内建）：`pytest tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs` 同时为绿；
4. 隔离级别必须是 **L3-strong**（`--strict-isolation` 强制），弱隔离下的 PASS **不得**用于签核。

---

## 5. `tools/repro_offline.sh`：用法、断网手段与限制

### 5.1 用法

```bash
tools/repro_offline.sh                                   # 默认：脚本所在仓库 + /home/szf/venvs/dsm/bin/python
tools/repro_offline.sh --src DIR --python PY             # 指定源仓库与基座解释器
tools/repro_offline.sh --wheelhouse DIR                  # 指定离线 wheel 目录（默认 <src>/dsm_stage/P3b-prep/wheelhouse）
tools/repro_offline.sh --runs N                          # 连跑次数（默认 2）
tools/repro_offline.sh --expect <64hex>                  # 与上一轮哈希比对（不等则 FAIL）
tools/repro_offline.sh --strict-isolation                # 隔离级别非 L3-strong 即 FAIL（**P3b 正式签核必须加**）
tools/repro_offline.sh --no-pytest                       # 只跑探针，不跑 spine 断言
tools/repro_offline.sh --netns on|auto|off               # 断网手段开关（on = 不可用即失败）
tools/repro_offline.sh --keep                            # 保留临时目录取证（默认自动清理）
```

输出末行为机器可读：`RESULT=PASS|FAIL HASH=<64hex> COMMIT=<sha7> ELAPSED=<n>s ISOLATION=<level>`；exit code `0` = PASS，`1` = FAIL。

**执行链**：① `git clone --quiet --no-hardlinks <本地路径> $(mktemp -d)/clone` → ② 在 netns 内 `python -m venv` + `pip install --no-index --find-links <wheelhouse> --no-cache-dir`（先 pip/setuptools/wheel，再 `requirements.txt`）→ ③ 生成探针（`import tests/test_integration_spine`，复用 `_run_chain`，**不重实现任何算法**）→ ④ 同 seed 连跑 N 次（每次独立进程、独立临时目录）→ ⑤ 跑 spine 两连跑断言 → ⑥ 比对 + 裁决 + `trap` 清理。

**幂等性**：每次运行新建 `mktemp -d`，`trap cleanup EXIT INT TERM` 清理；不写源仓库任何文件（只读 `git status`）。实测连跑 4 轮（run-1/2/3/6）结果一致，运行后 `ls -d /tmp/p3b-repro.* /tmp/p3b-probe-*` 均为 **0**（探针的临时目录通过 `PROBE_TMP` 收进本轮 `$TMP` 一并清理）。

### 5.2 断网手段与实际做到的隔离级别（本包最重要的一节）

**实测可用：真 network namespace（不是模拟）。** 证据 `dsm_stage/P3b-prep/netprobe.log`：

| 探测 | netns 外 | `unshare -rn` 内 |
| --- | --- | --- |
| `socket.create_connection(('pypi.org',443),5)` | `NETWORK=ONLINE` | `NETWORK=DOWN gaierror` |
| `pip download --no-deps pip` | 成功 | `Temporary failure in name resolution` → `No matching distribution found` |
| `ip -o link` | 多网卡 | 只有 `1: lo: <LOOPBACK> … state DOWN` |

脚本用到的四种手段（逐项）：

1. **`unshare -rn`**（user namespace + network namespace）：装环境与连跑**全部**在其内执行。注意 `unshare -n`（不带 `-r`）在本机实测 `Operation not permitted`，必须靠 user namespace 映射 root 才拿得到 netns。
2. **`pip install --no-index --find-links <wheelhouse> --no-cache-dir`**：无网络索引、无缓存命中，只认本地 wheel。
3. **`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY` + `PIP_NO_INDEX=1`**：netns 不可用时的降级手段（脚本会自动降级并在 `net_isolation` 行打 `PLACEHOLDER`）。
4. **`git clone <本地路径>`**：本地领先提交**未 push**，故不走 `git@github.com:shaozhongfei001/strategy-eval-dsm.git`；`--no-hardlinks` 使 clone 的对象库也独立（不只是共享硬链接）。

**隔离级别分级**（脚本每次运行都会打印自己处在哪一级，弱隔离绝不宣称为强隔离）：

| 级别 | 含义 | 本包是否实测达到 |
| --- | --- | --- |
| **L3-strong** | 全新本地 clone（commit-exact）+ netns 真断网 + **独立 venv（无 system site-packages）** + 仅本地 wheel 离线安装 | **是**（run-1/2/3/6，18/16/17/22s，全部 PASS） |
| L2-medium | 无 netns，仅清代理变量 + `PIP_NO_INDEX=1` + 独立 venv | 否（本机 netns 可用，未触发） |
| L1-weak | wheelhouse 缺失 → 直接用宿主解释器跑，**复用宿主 site-packages，未做离线安装** | 是（run-4，脚本如实打 `PLACEHOLDER`；run-5 证明 `--strict-isolation` 会把它判 FAIL） |

> 实测细节（诚实披露）：L1-weak 档最初实现为 `python -m venv --system-site-packages`，但**从宿主 venv 再建 venv 不会链式继承宿主的 site-packages**，探针直接 `ModuleNotFoundError: No module named 'pytest'`（见 `run-4-degraded.log` 的早期版本）。已改为直接用宿主解释器，并把「复用宿主 site-packages」如实写进 `env_mode`。

### 5.3 本质上无法断网完成的步骤（PLACEHOLDER 清单）

| 编号 | 缺口 | 为什么断网做不到 | 可行替代 / 现状 |
| --- | --- | --- | --- |
| **P-1** | wheelhouse 的**首次预下载**需要联网 | `pip download` 必须访问索引；wheel 不可能凭空产生 | 已在本包 prep 阶段联网下载：26 个 wheel / 37MB（`dsm_stage/P3b-prep/wheelhouse-download.log`），sha256 清单 `dsm_stage/P3b-prep/wheelhouse.sha256`。**但 `dsm_stage/` 已 gitignore，不随 clone 传播**；P3b 正式执行人必须先把 wheelhouse 复制到目标单机，或用 `--wheelhouse` 指路。缺什么：一个**允许入库**的离线 wheel 载体（本包无权新增二进制目录，且 R-13 只允许写本包写集） |
| **P-2** | 基座 python 解释器 | `python -m venv` 需要宿主已有 3.11+ 解释器（`ensurepip` 随标准库，离线可用；解释器本身离线装不出来） | 实测用 `/home/szf/venvs/dsm/bin/python`（Python 3.12.3，`ensurepip` 24.0）。目标单机须自备同版本解释器 |
| **P-3** | 「**单机**」≠「**异机/第二人**」 | 本包全部轮次都在同一台 WSL2 主机（`t16`）上完成，未做第二人/第二台机器复跑 | V-3 的「第二人复跑」半边**仍是 PLACEHOLDER**。哈希的环境无关性目前只有**测试级**证据（`tests/test_audit.py:167` home vs foreign、audit.py 环境量排除），不是真异机实测 |
| **P-4** | CLI 真实运行链路未覆盖 | `dsm/cli.py:199` 仍是 `PLACEHOLDER`，且 `config/` 为 0 文件 → `load_all()` 以 `EXIT_CONFIG=3` 拒绝 | 当前哈希来自 spine `_run_chain`（测试内合成 config）。P3b 签核**不得**宣称「`dsm score` 端到端跑出同一哈希」 |
| **P-5** | pytest 自身的临时目录 | `tmp_path_factory` 会在 `/tmp/pytest-of-<user>/` 留最近 3 次目录（pytest 默认行为，非本脚本泄漏） | 用 `--no-pytest` 可完全避免；脚本自身 `$TMP` 与 `PROBE_TMP` 实测零残留 |
| **P-6** | 「断网」不覆盖**主机层** | netns 只切断本进程树的网络，宿主其他进程仍可联网；也不排除本地 DNS 缓存/本地 pip 镜像等旁路 | 已通过 `--no-index --no-cache-dir` 关闭索引与缓存两条旁路；`--netns on` 可在 netns 不可用时**直接失败**而不是静默降级 |

---

## 6. P3b 正式执行时的重跑清单（逐条勾选）

- [ ] **前置 A**：确认 `MODELS-1` 已落地（frame 级披露通道 + `PoolKey.evidence_class` 可选）——`git log --oneline | grep MODELS-1`
- [ ] **前置 B**：确认 `A1c` 受控解冻已执行（D-A1-02/03/04/05/06/07/08）——`git log --oneline | grep A1c`
- [ ] **前置 C**：确认 P2 全量转绿（`pytest -q` → `0 failed`）；带病不签核
- [ ] 记录截至 commit：`git rev-parse HEAD`（并确认工作区 `git status --porcelain` 干净）
- [ ] 记录 fixtures 解冻后 sha256 清单，与 `dsm_stage/P3a-prep/fixtures-sha256-pre-thaw.txt`、`dsm_stage/A1CPREP/before.sha256` 对比归档
- [ ] 在目标单机备好 wheelhouse（复制 `dsm_stage/P3b-prep/wheelhouse/` 并用 `wheelhouse.sha256` 校验 26 个文件）
- [ ] 确认 `unshare -rn true` 在目标单机可用；不可用则记录降级为 L2 并写明原因（此时**不得**签核为 L3）
- [ ] 确认目标单机有 Python ≥3.11 基座解释器，并记录 `--python` 实际取值
- [ ] 执行：`bash tools/repro_offline.sh --strict-isolation`（首轮无 `--expect`；复测轮加 `--expect <上一轮 64 位哈希>`）
- [ ] 要求：exit code `0`、`RESULT=PASS`、`all_equal=1`、`isolation_level=L3-strong…`、`pytest_assertion rc=0`、`meta … exit_code=0 len=64`
- [ ] 完整输出存档（不入库）：`dsm_stage/P3b/run-signoff.log`；摘要由**主控**写入 `ops/dag-state.json → reproducibility_evidence`（lane 不得改该文件）
- [ ] 按 §3 台账把 seq2 / seq3 的 `hash_before` / `hash_after` 补成 64 位，并写明「哪个 commit 造成哪次变化」
- [ ] V-3「第二人复跑」：若仍无法在第二人/第二机执行，写 `PLACEHOLDER` + 缺什么，**不得**用同机多轮冒充
- [ ] **不打 tag**（`v1.1.0` 属 P3c，且必须在 P2 全量转绿后）

---

## 7. 本包自检

| 项 | 结果 |
| --- | --- |
| R-12 不编造 | §5.3 列出 6 项 PLACEHOLDER；弱隔离档由脚本自动打 `PLACEHOLDER` 字样，`--strict-isolation` 会判 FAIL |
| R-13 一包一提交 | 只 `git add tools/repro_offline.sh docs/deliverables/P3b-REPRO-HARNESS.md`；未用 `git add -A`；未 push / amend / force / rebase / reset / 切分支 |
| 邻仓只读 | `/home/szf/dev/CampaignLab` 实测 `m0-framework` / `0cccb76` / porcelain `0` / rev-list `154`，与基线一致，未改动 |
| 未改禁写区 | `dsm/**`、`tests/**`、`fixtures/**`、`config/**`、`ops/dag-state.json`、`tools/gen_golden.py`、`tools/normalize.py` 全部零改动（`git status --porcelain` 仅 `?? tools/repro_offline.sh`） |
| 未打 tag | 是 |