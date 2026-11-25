# P3b 复现性签核工装（REPRO HARNESS）—— 判据、台账与诚实性边界

**包号**：P3b-FIX（诚实性修复 + 正式签核；前身为 P3b-prep 工装包与 P3b-PRE 只读侦察包）
**性质**：工装修复 + 实测证据 + 最终 HEAD 断网两跑自等签核记录（§8）。
**本包写集**（只有两个文件）：`tools/repro_offline.sh`、`docs/deliverables/P3b-REPRO-HARNESS.md`（本文件）。自证日志留在 gitignore 的 `dsm_stage/P3b-FIX/`。
**未改动**：`dsm/**`、`tests/**`、`fixtures/**`、`config/**`、`ops/dag-state.json`、`tools/gen_golden.py`、`tools/normalize.py`。未 push、未 tag、未 amend、未动他 lane 脏文件。
**判据原文依据**：SDD [L1640]（契约文件 sha256[:12]=`708679e9a83d`，2003 行，只读复核一致）。

---

## 0. P3b-FIX 缺陷修复对照表（逐条，全部实测自证）

| 编号 | 缺陷（P3b-PRE 实测，file:line 为修复前旧行号） | 修复 | 自证 |
| --- | --- | --- | --- |
| **B1** | ISO_LEVEL 判 L3-strong 只看 HAVE_WH，不含 NETNS 判据 → `--netns off --strict-isolation` 仍输出 L3-strong 并假 PASS（违 V-14 与脚本自身承诺） | ISO_LEVEL 改由 **(wheelhouse 可用) AND (netns 真实生效)** 共同决定；netns 未生效（off/不可用/连通性自检 LEAK）→ 如实降为 `L2-netns-unavailable`，`--strict-isolation` 判 FAIL。另加**正向自检**：netns 内 `socket.create_connection(('pypi.org',443),5)` 必须失败，成功即 `netns_probe=LEAK` 并按未隔离降级 | SELFTEST-2：`--netns off --strict-isolation` → exit 1 / RESULT=FAIL / ISO=`L2-netns-unavailable…`（修前同命令是假 PASS），日志 `dsm_stage/P3b-FIX/selftest2.log` |
| **B7** | 文案声称降级路径含 `PIP_NO_INDEX=1`，但全脚本从未导出 | 降级 RUNNER 改为 `env -u <6个代理变量> PIP_NO_INDEX=1`，**真实导出**，自述与实现一致 | `tools/repro_offline.sh` 降级分支源码 + selftest2 日志 `net_isolation` 行 |
| **B4** | SRC_DIRTY 计算了却不进裁决 | DIRTY=n 进输出与 RESULT 行；脏树时打 WARNING 如实标注「clone 是 commit-exact，签核结论只覆盖 RESULT_COMMIT，不覆盖未提交改动」 | selftest1/2 日志 `dirty_files=5` + WARNING 行（当时他 lane 5 个脏文件） |
| **B9** | 未防「运行期间源仓库被在飞 lane 继续提交」（P3b-PRE 期间 HEAD 移动 3 次） | clone 后与裁决前各复核一次源 HEAD，`HEAD_STABLE=yes/no` 进输出与 RESULT 行；no 时打 WARNING，`--strict-isolation` 下判 FAIL | selftest1/2/3 日志 `head_stable=yes`（本轮运行窗口内 HEAD 未动） |
| **B6** | wheelhouse 判据仅「目录非空」，不用已存在的 sha256 清单 | 若 `$WHEELHOUSE/wheelhouse.sha256`（或旁挂 `<wheelhouse目录名>.sha256`）存在则 `sha256sum -c` 校验并把结果打进 `wh_manifest` 行；清单不存在→如实标 `absent-unverified`（**不**因此 FAIL）；校验不一致→`FAILED` 且入 FAILURES | selftest2 日志 `wh_manifest=verified(26 entries, sha256sum -c all OK)`（默认路径 prep 档带清单）；selftest1 `absent-unverified`（`/home/szf/dsm-wheelhouse` 无清单文件，如实标注） |
| **B5** | 默认 wheelhouse 落在 gitignored 目录，异机/全新 clone 会**静默**降级 | 缺/空 wheelhouse 时向 stderr 打**醒目 WARNING 块**（含「默认路径不随 clone 走」的说明与构建命令），ISO 如实降为 `L2-wheelhouse-missing`/`L1-weak`，`--strict-isolation` 判 FAIL；构建命令写入本文档 §4.4 | SELFTEST-3：以全新 clone 为 `--src` 且不传 `--wheelhouse`（默认目录必然不存在）→ 醒目 WARNING + ISO=`L2-wheelhouse-missing…` + RESULT=FAIL exit 1，日志 `dsm_stage/P3b-FIX/selftest3.log` |
| **B2** | 头注释称 `dsm/cli.py:199 的 reproducibility_hash 仍是 PLACEHOLDER`——已被证伪 | 头注释更新为当前事实：P2-wire-A（`53ed80c`）已在 `dsm/cli.py:243-288` 接真源，`:288` 调 `dsm/audit.py:242` 的 `reproducibility_hash` 取真 digest；但 `config/` 仍 0 文件 → `dsm score` 端到端仍不可跑（EXIT_CONFIG=3，属设计） | 本文档 §1.2；`dsm/cli.py:243-288` 只读复核 |
| **B3** | 本文档行号与哈希台账漂移（断言实在 `tests/test_integration_spine.py:1005` 而非 886/480；台账停在 4de4b8cb） | 行号引用校正并**以函数名为准**（该文件被在飞 lane 持续编辑，行号随 commit 漂移：886@82d5a6a → 1005@31eb1b2 → 1112@5d13ef3 → ROB-1 后再漂移）；台账补齐为 §2 四值全 64 位，**只追加，严禁修回** | 本文档 §1.2/§2 |
| **B8** | 「两跑比对」粒度自述易误读：脚本只比**单个 64hex** | 只披露不改语义：分工写入 §4.3——探针 N 跑互比 = 单哈希自等；多产物逐项自等由第⑤步 pytest 断言承担；RESULT 行新增 `ASSERTION=pytest\|skipped` 如实标注 | selftest1 `ASSERTION=pytest`；selftest3（--no-pytest）`ASSERTION=skipped` |

**R-14 自检**：以上修改只让 `--strict-isolation` 变严（新增 netns 生效、HEAD 稳定两个 FAIL 条件；L3-strong 判据收紧），未弱化任何断言。

---

## 1. `reproducibility_hash` 的确切定义与产出路径

### 1.1 定义（算法侧）

| 环节 | 位置 | 内容 |
| --- | --- | --- |
| 载荷拼装 | `dsm/audit.py:231` `hash_payload(score_card, grade_ledger, weight_version_id)` | `{'schema': HASH_SCHEMA, 'weight_version_id': …, 'score_card': _ordered(…), 'grade_ledger': _ordered(…)}` |
| schema 标签 | `dsm/audit.py:43` | `HASH_SCHEMA = 'dsm.reproducibility/v1'` |
| score_card 入哈希列 | `dsm/audit.py:84` `SCORE_CARD_HASH_FIELDS` | [L1612]-[L1626] 35 列中的 34 列（唯一例外见该处注释） |
| grade_ledger 入哈希列 | `dsm/audit.py:100` `GRADE_LEDGER_HASH_FIELDS` | 等级判定列 |
| 规范序列化 | `dsm/audit.py:113` `canonical_text(value)` | [L1053] 五条规则：Decimal 走 q12 定点 12 位、float 先 `numeric.from_float`、mapping 键显式排序、sequence 走业务键序（行按 `(strategy_id, version_id, period)`）、None 写 `null` |
| 取哈希 | `dsm/audit.py:242` `reproducibility_hash(...)` → `sha256_text(hash_payload(...))`（`dsm/audit.py:153`） | 64 位小写 hex |
| 载体字段 | `dsm/models.py` `AuditBundle.reproducibility_hash` | [L1051] 第 15 项 |
| 装配点 | `dsm/audit.py:272`（`build_manifest` 内） | 由 `RunContext.score_card / .grade_ledger / .weight_version_id` 算出 |
| 复跑四步文本 | `dsm/audit.py:283` `rerun_steps(bundle)` | 步骤三即「比对 `reproducibility_hash`，必须精确相等」 |

**环境量不入哈希**（`dsm/audit.py` 模块 docstring）：`run_id`（[L1091]）、`run_at`（[L1089]）、绝对路径、主机名、输出文件名一律只留在 bundle 里。测试级证据：`tests/test_audit.py`（home vs foreign 路径同哈希、两连跑相等、改一个语义位即变）。

### 1.2 产出路径（P3b-FIX 修订，B2/B3 校正）

> **当前唯一产出该真值的路径仍是测试侧 `_run_chain`，不是 CLI 真实运行。**

* **CLI 侧已接真源（旧文档「cli.py:199 仍是 PLACEHOLDER」已被证伪）**：P2-wire-A（commit `53ed80c`）在 `dsm/cli.py:243-288` 的 `audit_context()` 接了真源，`:288` 即 `digest(tuple(score_card), tuple(grade_ledger), wvid)`，digest 取自 `dsm/audit.py:242` 的 `reproducibility_hash`；`weight_version_id` 拿不到时以 EXIT_CONFIG=3 报错，绝不用 PLACEHOLDER 冒充（V-14）。
* 但 `config/` 实测仍 **0 文件**；`dsm/config.py:449` `load_all()` 在缺 `REQUIRED_CONFIG_STEMS` 时以 `EXIT_CONFIG = 3`（`dsm/config.py:71`）拒绝 → `dsm score` 端到端**仍不可跑**（属设计而非回归）。结论从「CLI 链路尚未产出真哈希」修订为「**CLI 已接线，但 config/ 未签认故 dsm score 端到端仍不可跑**」。
* 真值产出点：`tests/test_integration_spine.py` 的 `_run_chain(root, period)` —— 读 `fixtures/input/**` 冻结真数据，按 M29 [L1330]-[L1358] 九步跑真实模块，内部经 `audit.reproducibility_hash(score_card, grade_ledger, weight_version_id)` 产出。
* 断言载体：`tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs`（即 `ops/dag-state.json → reproducibility_evidence.assertion` 登记的那一条）。**行号以函数名为准**：该文件被在飞 lane（ROB-1 等）持续编辑，实测行号 886@`82d5a6a` → 1005@`31eb1b2` → 1112@`5d13ef3` → ROB-1（`111570a`）后继续漂移；旧文档写死的 886/480/1005 均已过时，本文件不再以裸行号作唯一引用。

**结论**：现有哈希是「**测试内合成 config** 驱动的九步真跑」产出的。治理入参来自 `tests/test_integration_spine.py` 文件头的 `GOVERNANCE` 字典（逐项有出处、非 spine 拟定），配置目录 `config/` **完全不参与**该哈希 → 「config/ 为空」不阻塞哈希产出，但该哈希**尚未覆盖 `dsm score` 端到端链路**（V-10 残留，§7 第 3/4 条），P3b 签核不得宣称已覆盖。

### 1.3 该哈希依赖的输入（逐项）

| 输入 | 取值 | 出处（以符号名为准） |
| --- | --- | --- |
| seed | `20260101` | `tests/test_integration_spine.py` `SEED = fg.SEED_DEFAULT` |
| 期次 period | `2026-Q2` | 同文件 `PERIOD`（历史窗口里事实表完整的一期；主评价期 `2026-Q3` 有刻意缺失单元格） |
| run_at | `2026-10-20T00:00:00+00:00`（注入时钟，H-8） | 同文件；**不入哈希** |
| run_id | `SYNTH-RUN-0001` | 同文件；**不入哈希** |
| fixtures | `fixtures/input/*.jsonl`、`fixtures/golden/**`、`fixtures/manifest.json` | 经 `_stage()` 落到临时目录后由 `io_loaders` 读取 |
| 权重版本 id | `fg.OAT20_WEIGHT_VERSION_ID`（冻结 fixtures，status=FROZEN） | `_governance_docs()` |
| 治理入参 | `GOVERNANCE` 字典（合成，逐项有出处） | 同文件文件头 |
| config 目录 | **不参与** | `config/` 为 0 文件 |

---

## 2. 哈希台账（**只追加，严禁把任何旧值修回或宣称被推翻**；全部 64 位）

| 序 | 哈希（64hex 全量） | 时代/归因 | 状态 |
| --- | --- | --- | --- |
| 1 | `8083efc940c648c460516291efe61ae35b6093671ae9b68f93fbab8bbc3a26b8` | 早期基线（SEAM-1 之前时代） | superseded_by_A1c（A1c commit message 明文双记） |
| 2 | `4de4b8cb63cbb29b66379bf3d96295ddfac11430d6432883713c8c5997a202d7` | SEAM-1（`8f2eca3`）锚定参考尺改动后；P3b-prep 时代 `82d5a6a` 实测 | superseded_by_A1c |
| 3 | `e5fa8ae01476ffd08c5812ea221988a97f06729481a072d94bf753e00275fd9d` | A1c（`6299245`）受控解冻 fixtures 后，连跑两次精确相等（A1c commit message 明文） | 被 4 取代（42d5346 时代起实测为 4） |
| 4 | `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` | @`42d5346`（G14FIX，G-14 分子改 C 类占比入 score_card）净树两跑相等；P3b-PRE 在 `0d8afeb`/`31eb1b2` 复测同值；P3b-FIX 在 `111570a`/`d46bf48` 复测同值（SELFTEST-1/2/3 三路同值） | **现行权威值**；最终签核记录见 §8 |
| 5 | `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904`（**与序 4 逐字符同值，未变**） | 最终 HEAD `3da51ab`（**ORCH-45 主控亲跑正式签核 PASS**，见 §8 追加记录）：该 HEAD 相对 `42d5346`/`93abfee` 的增量只落在 `tests/`（期望常量精确化）、`tools/`（工装修复）与 `docs/**`、`ops/**`，**均不属哈希输入面**；spine 评价期 2026-Q2 事实表完整 `180=12×15`、`IMPUTE_MEDIAN` 不触发 → 同值属预期 | **current / 已签核**（runs=2 两跑自等、`all_equal=1`、`DIRTY=0`、`HEAD_STABLE=yes`；权威哈希只认本工装 RESULT 行，K-36；`f437c0ead77b…` 仍为 non-canonical 不入台账） |

历史备注（保留不改写）：P3b-PRE 实测证伪了 `ops/dag-state.json → invalidation_log` seq5 的预声明（「A1d/LOO-1/P2-wire-A 必然再变」）——这些 commit 改的是报告文本/披露出口，未动哈希面（score_card 34 列 + grade_ledger + weight_version_id），故哈希自 `42d5346` 起不动。台账补记归主控，本包无权写 `ops/dag-state.json`。

---

## 3. P3b 的最终判据（照 `reproducibility_evidence.p3b_criterion`）

> **最终 HEAD 上：全新 clone + `unshare -rn` 真断网 + 同 seed 连跑两次自等。**
> 判据是**自等性**（self-equality），不是与任何历史值相等（与 §2 表值相等只是旁证）。

1. 前置：`git log --oneline -10` 可见 `P2-wire-B` 与 `ROB-1:` 的 commit（缺则轮询等待，超时则如实标注「非最终 HEAD」）。
2. 签核命令固定：`bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`。
3. 要求：exit 0、`RESULT=PASS`、`all_equal=1`、`isolation_level=L3-strong…`、`netns_probe=offline-confirmed`、`pytest_assertion rc=0`、`HEAD_STABLE=yes`、`meta … exit_code=0 len=64`。
4. 隔离级别必须 **L3-strong**：修后其判据 = wheelhouse 可用 **AND** netns 真实生效（含连通性正向自检）。任何弱隔离下的 PASS **不得**用于签核（`--strict-isolation` 自动拦截）。
5. 记录：HEAD sha（40 位）、是否脏树、ISO_LEVEL、两次哈希、自等与否、exit code、耗时。

---

## 4. 用法与输出契约（P3b-FIX 修订版）

```bash
tools/repro_offline.sh                                   # 默认：脚本所在仓库 + /home/szf/venvs/dsm/bin/python
tools/repro_offline.sh --src DIR --python PY             # 指定源仓库与基座解释器
tools/repro_offline.sh --wheelhouse DIR                  # 指定离线 wheel 目录（默认 <src>/dsm_stage/P3b-prep/wheelhouse，gitignored，异机必空→大声降级）
tools/repro_offline.sh --runs N                          # 连跑次数（默认 2）
tools/repro_offline.sh --expect <64hex>                  # 与第 1 跑哈希比对（不等则 FAIL；未给则不参与裁决）
tools/repro_offline.sh --strict-isolation                # 非 L3-strong 或 HEAD_STABLE=no 即 FAIL（**正式签核必须加**）
tools/repro_offline.sh --no-pytest                       # 只跑探针，不跑 spine 断言（RESULT 行如实打 ASSERTION=skipped）
tools/repro_offline.sh --netns on|auto|off               # 断网手段开关（on = 不可用即失败；off = 强制降级并如实标注）
tools/repro_offline.sh --keep                            # 保留临时目录取证（默认自动清理）
```

输出末行机器可读（P3b-FIX 扩展）：
`RESULT=PASS|FAIL HASH=<64hex> COMMIT=<sha7> ELAPSED=<n>s ISOLATION=<level> DIRTY=<n> HEAD_STABLE=<yes|no> ASSERTION=<pytest|skipped>`；exit `0`=PASS，`1`=FAIL。

**执行链**：① `git clone --quiet --no-hardlinks <本地路径> $(mktemp -d)/clone` + clone 前后 HEAD 一致性校验 → ② 隔离环境（netns 判定 + 连通性正向自检 + wheelhouse 判存/sha256 清单校验 + `python -m venv` + `pip install --no-index --find-links <wheelhouse> --no-cache-dir`，先 pip/setuptools/wheel 再 `requirements.txt`）→ ③ 生成探针（`import tests/test_integration_spine`，复用 `_run_chain`，**不重实现任何算法**）→ ④ 同 seed 连跑 N 次（每次独立进程、独立临时目录）→ ⑤ 跑 spine 两连跑断言（pytest）→ ⑥ 比对 + 裁决（FAILURES/WARNINGS）+ `trap` 清理。

**幂等性**：每次运行新建 `mktemp -d`，`trap cleanup EXIT INT TERM` 清理；不写源仓库任何受控文件（只读 `git status`/`rev-parse`）。

### 4.1 隔离级别分级（修后判据，脚本每次运行都如实打印自己所处级别）

| 级别 | 判据（修后） | `--strict-isolation` |
| --- | --- | --- |
| **L3-strong** | 全新本地 clone（commit-exact）+ **netns 真实生效**（`unshare -rn` 可用 **且** netns 内连通 pypi.org:443 的正向自检失败=真断网）+ 独立 venv（无 system site-packages）+ 仅本地 wheel 离线安装 | PASS 的唯一通道 |
| **L2-netns-unavailable** | wheelhouse 可用、离线 venv 装成，但 netns 未生效（`--netns off`/宿主不允许/自检 LEAK）→ **网络未被切断，离线性未被证明** | FAIL |
| **L2-wheelhouse-missing** | netns 真断网，但 wheelhouse 缺/空 → 未做离线安装，宿主解释器 + 宿主 site-packages 复用 | FAIL |
| **L1-weak** | 两者皆无：宿主 site-packages 复用 + 无 netns | FAIL |

wheelhouse 内容校验（B6）：`wheelhouse.sha256` 清单存在则 `sha256sum -c`，结果打进 `wh_manifest=`（verified(n entries)/absent-unverified/FAILED）；absent 不 FAIL（不把可跑环境挡死），FAILED 入 FAILURES。

### 4.2 断网手段与实际做到什么（逐项，与实现对齐）

1. **`unshare -rn`**（user namespace + network namespace）：装环境与连跑**全部**在其内执行；本机实测 `unshare -n`（不带 `-r`）`Operation not permitted`，必须靠 user namespace 映射 root。修后另跑**正向自检**：netns 内 `socket.create_connection(('pypi.org',443),5)` 必须抛错，否则 `netns_probe=LEAK` 并按未隔离降级（不得输出 L3-strong）。
2. **`pip install --no-index --find-links <wheelhouse> --no-cache-dir`**：无网络索引、无缓存命中，只认本地 wheel。
3. **降级手段（仅 netns 不可用时）**：`env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY PIP_NO_INDEX=1` —— B7 修后 `PIP_NO_INDEX=1` **真实导出**（修前只存在于文案）。降级不是断网：仅堵 pip 索引与代理，其余联网途径未封，故 ISO 只能是 L2-netns-unavailable。
4. **`git clone <本地路径> --no-hardlinks`**：本地领先提交未 push，不走远端；对象库也独立。

### 4.3 「两跑自等」的分工（B8 披露，语义未改）

* 脚本第④步：N 次探针运行，各打印**单个 64 位** `reproducibility_hash`，第⑥步互比 —— 这是**单哈希自等**。
* 脚本第⑤步：`pytest tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs`（行号漂移见 §1.2，以函数名为准）—— **多产物逐项自等**由它承担：input fingerprints + 11 项中间产物（attain/normalized/evidence/redline/scores/grades/pool_reflow/pool_stats_reflow/sensitivity/score_card/grade_ledger）+ exit_code 均等。
* `--no-pytest` 时只剩单哈希自等，RESULT 行以 `ASSERTION=skipped` 如实标注，读者不得把它当成多产物自等。

### 4.4 wheelhouse 的构建（B5，联网一次性，仓库外）

```bash
/home/szf/venvs/dsm/bin/python -m pip download --only-binary=:all: \
  -d /home/szf/dsm-wheelhouse -r requirements.txt pip setuptools wheel
```

实测产物：26 个 wheel / 约 37MB / 0 失败，含 pip-26.3、setuptools-84.2.1、wheel-0.48.0。**平台绑定**：numpy/pandas/pydantic_core/PyYAML/hypothesis 均为 cp312 + manylinux x86_64 二进制轮 → 换 Python 主次版本或换架构即失效，须按目标机重下。wheelhouse **不入库**（默认路径 `dsm_stage/P3b-prep/wheelhouse` 是 gitignored 的，不随 clone 走；缺它时脚本大声披露降级，见 §0 B5）。

---

## 5. 本质上无法断网完成的步骤（PLACEHOLDER 清单，P3b-FIX 修订）

| 编号 | 缺口 | 为什么断网做不到 | 现状 |
| --- | --- | --- | --- |
| **P-1** | wheelhouse **首次预下载**需联网 | `pip download` 必须访问索引 | 已在仓库外 `/home/szf/dsm-wheelhouse` 建好（§4.4 命令）；异机需照此重建 |
| **P-2** | 基座 python 解释器 | `python -m venv` 需宿主已有 3.11+ 解释器，解释器本身离线装不出来 | 实测 `/home/szf/venvs/dsm/bin/python`（Python 3.12.3）；目标单机须自备同版本 |
| **P-3** | 「单机」≠「异机/第二人」 | 全部轮次都在同一台 WSL2 主机（t16）完成 | V-3「第二人复跑」半边**仍是 PLACEHOLDER**（§7 第 1 条） |
| **P-4** | CLI 真实运行链路未覆盖 | `config/` 0 文件 → `load_all()` EXIT_CONFIG=3 拒绝 | CLI 侧哈希已接真源（B2 修订），但 `dsm score` 端到端仍不可跑；哈希仍出自 spine 测试内合成 GOVERNANCE 配置（§7 第 3/4 条） |
| **P-5** | pytest 自身临时目录 | `tmp_path_factory` 在 `/tmp/pytest-of-<user>/` 留最近 3 次目录（pytest 默认行为） | `--no-pytest` 可完全避免；脚本自身 `$TMP` 与 `PROBE_TMP` 实测零残留 |
| **P-6** | 「断网」不覆盖主机层 | netns 只切断本进程树的网络，宿主其他进程仍可联网 | `--no-index --no-cache-dir` 关闭索引与缓存旁路；修后正向自检 + `--netns on` 硬失败 + LEAK 降级三重兜底 |

---

## 6. P3b 正式签核执行清单（P3b-FIX 版）

- [ ] 前置：`git log --oneline -10` 可见 `P2-wire-B` 首行 commit **且** `ROB-1:` 首行 commit；缺则每 60s 轮询（≤12 分钟），超时则在当时 HEAD 签核并**如实标注「非最终 HEAD，签核结论待最终 HEAD 复跑」**。
- [ ] 记录 HEAD sha（40 位）与 `git status --porcelain`（脏树时签核结论只覆盖该 commit，见 §0 B4）。
- [ ] 目标单机备好 wheelhouse（§4.4），有清单则确认 `wh_manifest=verified`。
- [ ] 确认 `unshare -rn true` 可用且 `netns_probe=offline-confirmed`。
- [ ] 执行固定命令：`bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`。
- [ ] 判定：exit 0、RESULT=PASS、all_equal=1、ISO=L3-strong、HEAD_STABLE=yes、pytest rc=0。
- [ ] 完整输出存档 `dsm_stage/P3b-FIX/`（gitignored）；摘要由**主控**写入 `ops/dag-state.json → reproducibility_evidence`（lane 不得改该文件）。
- [ ] V-3「第二人复跑」仍无法执行 → 保持 PLACEHOLDER + 写明缺什么，不得用同机多轮冒充。
- [ ] **不打 tag**（`v1.1.0` 属 P3c）。

---

## 7. 诚实边界四条（必读，不得掩盖）

1. **第二人/异机复跑仍是 PLACEHOLDER**：本文件全部实测在同一台 WSL2 主机（t16）、同一 Python 3.12.3 完成；哈希的环境无关性只有测试级证据（`tests/test_audit.py` home vs foreign 同哈希、环境量不入哈希），无真异机/第二人实测。
2. **wheelhouse 不入库且平台绑定**：26 wheel / 37MB，cp312-manylinux_x86_64 专用；异机或换 Python 版本必须按 §4.4 重新联网构建，本包无法代证。
3. **`config/` 实测 0 文件 → `dsm score` 端到端仍不可跑**：`dsm/config.py:449` `load_all()` 以 `EXIT_CONFIG=3`（`dsm/config.py:71`）拒绝，**属设计而非缺陷回归**；P3b 签核不得宣称「dsm score 端到端跑出同一哈希」。
4. **哈希出自 spine 测试内合成的 GOVERNANCE 配置**：`_run_chain` 用 `tests/test_integration_spine.py` 文件头 `GOVERNANCE` 字典（逐项有出处）+ 冻结 fixtures 驱动九步真跑；`config/` 完全不参与该哈希，故该哈希未覆盖 CLI 配置装载链路（V-10 残留）。

---

## 8. P3b-FIX 正式签核记录

**前置核对**（2026-11-25，本机时间约 09:02）：`git log --oneline -10` 同时可见 `P2-wire-B(1/2)`（首行 `93abfee`）与 `ROB-1:`（`111570a`）→ 按任务书判据，最终 HEAD = `93abfee425c4e19791abf0c5a80e4f48e4566700`。

**签核命令**（固定形态）：`bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`

| 项 | 实测值 |
| --- | --- |
| HEAD sha（40 位） | `93abfee425c4e19791abf0c5a80e4f48e4566700`（clone_head 同值，commit-exact） |
| 脏树 | 3 项：本包写集 2 个文件的未提交修复（tools/repro_offline.sh、本文件）+ P3a 在飞的 `docs/deliverables/V-ACCEPTANCE-EVIDENCE.md`。脏文件不进 clone（clone 是 commit-exact），签核结论**只覆盖 `93abfee` 本身**，不覆盖任何未提交改动 |
| net_isolation | `network namespace (unshare -rn): only 'lo' exists and is DOWN, DNS/TCP both fail`；`netns_probe=offline-confirmed`（B1 正向自检：netns 内连 pypi.org:443 必须失败，实测失败） |
| ISO_LEVEL（原文） | `L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels` |
| run#1 哈希 | `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` |
| run#2 哈希 | `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` |
| 自等 | **是**（all_equal=1；meta：period=2026-Q2 seed=20260101 run_id=SYNTH-RUN-0001 exit_code=0 len=64） |
| pytest 断言 | rc=0（`test_reproducibility_hash_is_identical_across_two_runs`，多产物逐项自等载体） |
| HEAD_STABLE | yes（src_head_end=`93abfee4…`，B9 校验：运行窗口内无在飞提交） |
| wh_manifest | absent-unverified（`/home/szf/dsm-wheelhouse` 无清单文件，B6 如实标注，不因此 FAIL） |
| exit code / 耗时 | 0 / 14s |
| RESULT 行（原文） | `RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=93abfee ELAPSED=14s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=3 HEAD_STABLE=yes ASSERTION=pytest` |
| 日志 | `dsm_stage/P3b-FIX/signoff.log`（gitignored）；同目录 `selftest1.log`/`selftest2.log`/`selftest3.log` 为 B1/B5 验收对照 |

**结论**：最终 HEAD（按任务书前置判据 = `93abfee`）上，全新 clone + `unshare -rn` 真断网 + 同 seed 连跑两次**自等** → SDD [L1640] 复现性判据在本机、该 commit 上 **PASS**。哈希与 §2 台账现行权威值 `e5923465…` 逐字符一致（旁证，判据是自等而非与旧值相等；P2-wire-B(1/2) 改 ratchet/编码门禁/anchor_set 传参未动哈希面）。

**适用范围与残留**：① 签核结论只覆盖 commit `93abfee`，后续任何 lane 再前移 HEAD 须复跑；② V-3「第二人/异机复跑」半边仍 PLACEHOLDER（§7 第 1 条）；③ 签核所用 `tools/repro_offline.sh` 为修复后版本，与本文件同 commit 原样入库（签核时在工作区、随即提交，逐字节同一）；④ `P2-wire-B(1/2)` 标注为两分之一个包，若其 (2/2) 落地后 HEAD 前移，本签核按 ① 失效待复跑。


### 8-追加（**V1-FINAL / ORCH-45**）：主控在**最终 HEAD `3da51ab`** 的正式签核记录

> 本小节为**追加记录**；上文 `93abfee` 那次签核的**全部原文（含表格、RESULT 行、适用范围与残留四条）逐字保留，未删除、未改写、未标作废**。两次记录并存，各注明自己的适用 HEAD。

**签核命令**（固定形态，与上文同）：`bash tools/repro_offline.sh --wheelhouse /home/szf/dsm-wheelhouse --runs 2 --strict-isolation`

| 项 | 主控亲测原文（观测 HEAD = 最终 HEAD `3da51ab`，T+8.4h） |
| --- | --- |
| RESULT 行（原文） | `RESULT=PASS HASH=e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904 COMMIT=3da51ab ELAPSED=15s ISOLATION=L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels DIRTY=0 HEAD_STABLE=yes ASSERTION=pytest` |
| clone_head | `3da51ab325a535525c20fe25a96b33182edf08b9`（commit-exact） |
| run_#1 / run_#2 | 两者均为 `e59234654f4e760b76a661ea4f25b0bdc32987e941f9fecca51762e3c9180904` |
| all_equal | **1**（两跑 64 位逐字符自等） |
| netns_probe | `offline-confirmed`（netns 内连 pypi.org:443 必须失败，实测失败） |
| ISOLATION | **L3-strong**：fresh clone + netns offline（connectivity self-check confirmed）+ dedicated venv from local wheels |
| env_mode | `dedicated venv (no system site-packages) installed from local wheelhouse with --no-index` |
| env_python | `Python 3.12.3` |
| wh_manifest | `absent-unverified`（wheelhouse 无清单文件，B6 如实标注，不因此 FAIL） |
| DIRTY / dirty_files | `DIRTY=0` / `dirty_files=0`（签核时点工作树干净，优于 `93abfee` 那次的 3 项） |
| HEAD_STABLE | `yes`（`head_stable=yes (src_head_end=3da51ab325a535525c20fe25a96b33182edf08b9…)`，B9：运行窗口内无在飞提交） |
| pytest_assertion | `rc=0` |
| meta | `period=2026-Q2 seed=20260101 run_id=SYNTH-RUN-0001 exit_code=0 len=64` |
| runs / elapsed | `runs=2` / `elapsed_seconds=15`（RESULT 行 `ELAPSED=15s`） |
| tmpdir | `/tmp/p3b-repro.WQQSlx8P` |

**结论**：**tag 前置 ③ 在最终 HEAD `3da51ab` 判「满足」**（exit 0 + RESULT=PASS + L3-strong + 两跑逐字符自等），不再限于 `93abfee` / `da4d0a9`。**同时维持不变的两条诚实边界**：① 本次仍是**同机、同 Python 3.12.3**，**第二人 / 异机复跑仍为 PLACEHOLDER** → **V-3 / V-10 维持 ⏳，不因本笔上调**；② wheelhouse 不入库且绑定 cp312-manylinux-x86_64，本次 `wh_manifest=absent-unverified`；③ `config/` 实测 0 文件 → 本哈希仍出自 spine 测试内合成 GOVERNANCE，**不得宣称「`dsm score` 端到端跑出同一哈希」**（§7 第 3/4 条照旧适用）。

**签核适用域论证（为何签核 HEAD 与被 tag 的 HEAD 可以不同）**：本笔签核完成后，HEAD 还会因 **V1-FINAL 包的 docs 提交**（`docs/deliverables/**` + `README.md`）与**主控的 ledger 提交**（`ops/dag-state.json`）而前移。`reproducibility_hash` 的输入面是 **seed `20260101` / period `2026-Q2` / `fixtures/input` + `fixtures/golden` / 冻结权重版本 id**（出处：`ops/dag-state.json → reproducibility_evidence.harness.inputs`），**不含 `docs/**` 与 `ops/**`**，故这些后续提交不改变任何被哈希的输入，本签核结论对最终被 tag 的 commit 仍然适用。**该结论由主控在 push 前用 `git diff --name-only 3da51ab..HEAD` 实测核验**，核验输出记入 `ops/dag-state.json` 与主控最终报告；**本包按派工纪律未代跑、未代填结果**（本包亦未触碰 `ops/dag-state.json`）。若核验发现任何超出 `docs/**` 与 `ops/dag-state.json` 的触及面（尤其 `dsm/**`、`fixtures/**`、`tools/repro_offline.sh`），本论证立即失效，须在新 HEAD 重跑本工装后再打 tag。

---

## 9. 本包自检

| 项 | 结果 |
| --- | --- |
| R-12 不编造 | §5/§7 PLACEHOLDER 逐条保留；降级隔离绝不宣称为强隔离（B1 修复即为此） |
| R-14 不弱化断言 | `--strict-isolation` 只增不减 FAIL 条件（netns 生效、HEAD 稳定、L3-strong 判据收紧）；spine 断言原样保留 |
| V-14 降级显式可见 | 所有降级路径均有 stderr WARNING/ISO 级别/RESULT 行字段三重披露 |
| 写集纪律 | 只 `git add tools/repro_offline.sh docs/deliverables/P3b-REPRO-HARNESS.md`；未 `git add -A`；未 push/tag/amend/stash/checkout/reset；他 lane 脏文件未触碰 |
| 邻仓只读 | `/home/szf/dev/CampaignLab`：m0-framework / 0cccb76 / porcelain 0 / rev-list 154（开工校验一致；收工再核） |
| 契约只读 | sha256[:12]=`708679e9a83d`、2003 行，开工实测一致 |
| 编码与行尾（**V1-FINAL 追记**） | 本包追加 §8-追加 与 §2 序 5 后，为全文件**补齐末尾 LF**——该 blob 原缺末尾 LF（属 §7／`KNOWN-GAPS.md` 披露的 **17 个 @`da4d0a9`** 受控文件之一，非本包引入）；据此该计数推算为 **16**（余 **9 个非 `docs/**`** 项清零仍需**主控单独授权**，本包未动），精确值由主控 push 前以 `tools/normalize.py --check` 复测。全文 UTF-8 无 BOM、LF、无 TAB |
| 未跑全量 pytest | 是（归 P2-wire-B 独占）；本包只跑工装第⑤步的单条 spine 断言 |
