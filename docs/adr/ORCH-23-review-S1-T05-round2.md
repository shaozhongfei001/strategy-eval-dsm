<!-- ADR: ORCH-23-review-S1-T05-round2 | task: S1-T05 | role: R4 independent review, L4 round 2 | 契约权威: docs/adr/ORCH-23.md（397 行 / 24 条裁决，含本轮新增裁决 23 / 24）| 日期: 2026-11-24 -->

# ORCH-23-review-S1-T05-round2：S1-T05 第 2 轮 R6 修复的 L4 增量复核签认

**角色**：R4（独立复核），本轮只判「F1 / F2 是否真关闭」与「有无『让它变绿』手段」，不修任何代码或测试。
**上一轮**：`docs/adr/ORCH-23-review-S1-T05.md`（312 行 / 32036 B / sha256[:12] `aeb4e2fb5346`，
本轮实测**未被改动**），判 `FAIL(2 项)`：F1 = `ConfigPlaceholderError.paths` 未套裁决 9 键；
F2 = 变异体 M09（裁决 19 无闸）/ M12（去重不可达）存活。
**本轮判定权威**：ORCH-23 裁决 1~22 + **裁决 23 / 裁决 24**（`docs/adr/ORCH-23.md` 第 297~355 行，R4 逐行读过原文）。
`docs/adr/ORCH-24.md`（S1-T06 契约，422 行 / 35784 B / `0327390ead34`）**不用于**判 T05，本轮未据其立任何结论。
**实测证据**：`ops/evidence/S1-T05/L4-round2-{probe,mutation,pytest,anticheat-diff,probe-api,probe-io,gates}.txt`
（全部由 R4 本人产出；`ops/evidence/S1-T05/L5-r6-fix2.txt` 一行未采信，仅在必要时作对照）。

---

## 0. 基线与指纹（R4 实测）

| 文件 | 行数 | 字节 | sha256[:12] | 主控给定 | 结论 |
|---|---|---|---|---|---|
| `docs/adr/ORCH-23.md` | 397 | 33914 | `08d5f97637e9` | `08d5f97637e9` | 一致（裁决 23/24 已追加） |
| `docs/adr/ORCH-24.md` | 422 | 35784 | `0327390ead34` | `0327390ead34` | 一致（不在本轮范围） |
| `docs/adr/ORCH-23-review-S1-T05.md` | 312 | 32036 | `aeb4e2fb5346` | `aeb4e2fb5346` | **R4 上轮产物未被改** |
| `docs/digest/S1-T05.md` | 115 | 14892 | `52c070190063` | `52c070190063` | 未变 |
| `ops/evidence/S1-T05/L1-red.txt` | 672 | 59352 | `c439084b33ac` | `c439084b33ac` | **未被改写** |
| `ops/evidence/S1-T05/L5-r6-fix.txt` | 164 | 9825 | `90199059de9a` | `90199059de9a` | 未变 |
| `ops/evidence/S1-T05/L5-r6-fix2.txt` | 1113 | 69942 | `dea379ed73f5` | `dea379ed73f5` | 一致（R6 本轮产物） |
| `dsm/config.py` | 480 | 22873 | `54e6813eeaca` | `54e6813eeaca` | 一致（原 `d8c49a1aeecc`） |
| `tests/test_config_placeholder.py` | 1623 | 68178 | `55f28652ad1b` | `55f28652ad1b` | 一致（原 `a81fb14e687c`） |
| `tests/test_config_properties.py` | 530 | 21886 | `01b53feeee94` | `01b53feeee94` | 一致（原 `912eb7f672a2`） |

**改前基线的取得方式（不依赖 R6 任何产物）**：R4 从前几轮遗留的 staging 树里取回原始副本，
自行去 BOM / CRLF→LF 后重算 sha256，三个文件分别与 R4 上一轮**亲手实测**的指纹逐字相符：
`dsm_stage_S1-T05_r2/dsm/config.py` → `d8c49a1aeecc`、
`dsm_stage_S1-T05_r6/tests/test_config_placeholder.py` → `a81fb14e687c`、
`dsm_stage_S1-T05_r3/tests/test_config_properties.py` → `912eb7f672a2`
（原文与字节数见 `L4-round2-anticheat-diff.txt` 头部）。
交叉验证：`dsm_stage_S1-T05_r3/tests/test_config_placeholder.py` 规范化后 = `e01bf605fdd3`，
正是 `L5-r6-fix.txt` §5 记录的「第 1 轮修复前」指纹，血缘自洽。

HEAD 仍 `17dd568ff18c4e48b126b5e1a5bb72b0e0bd6ae0`；`git diff --numstat` 与 `git diff --cached --numstat` 均为空。

---

## 1. 最终裁决

**R4 VERDICT: PASS**

F1、F2 **均已真正关闭**，且关闭方式是「实现改对 + 测试按契约重算期望 + 补可证伪的闸」，
**未发现任何**放宽断言、golden 跟随实现、删测试、加 skip/xfail、绕过分支或「只改测试不改实现」的手段。
T05-A~T05-M 13 条重新逐条判定全部满足；全量 `1487 passed`，既有 1268 项一条不坏。
裁决 23 / 24 与 SDD 原文、与 ORCH-23 既有裁决**无冲突**（唯一张力见 §4 O-R2-2，已由裁决 24 第 2 项在其自身权限内闭合）。

---

## 2. E1~E8 逐条判定

| 项 | 判定 | 关键实测数字 | 证据文件 |
|---|---|---|---|
| **E1** F1 是否真关闭 | ✅ | `.paths` == `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')`；`deduped == canonical` **0** 命中、`tuple(sorted(deduped))` **0**、`names no key` **0**、`order independent reading` **0**、`Both branches` **0**；`plain string sort` 仅 1 命中且是新写的**否定句**（L192「one order, not two, and no plain string sort anywhere in this class」）；`self.paths = canonical` 在 **L205**；`missing_files` 一支未动（仍恒用 `_missing_key`，实测顺序 `('eval_config','weights_*','redlines','grade_rules','anchor_set','ahp_matrices')`） | `L4-round2-probe.txt` §E1 |
| **E2** b05 期望值来源合法性 | ✅ | R4 **自行**从 digest 抽出 `[L1250]-[L1257]` 文件序 → 按裁决 9 插入 weights 得 rank 表 → 逐条算出 rank（eval_config=0 / redlines=2 / anchor_set=4）→ `(rank, path)` 升序 = `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')`，与 b05 新断言逐字相同；且与**旧实现的输出** `('anchor_set.SYN-a','eval_config.SYN-m','redlines.SYN-z')` **不同** → 不是跟着实现改的；b12 / b13 同法重算亦逐字吻合 | `L4-round2-probe.txt` §E2 |
| **E3** F2 是否真关闭（R4 自建变异体） | ✅ | **8/8 KILLED**：M09R（空串变命中）13 杀手（c02×3 + c12×3 + n01/n02/n03/p02/p05/p10/p11）；M12R（删 scan 去重）2 杀手（**b11 + j_p11**）；M11R（把双分支改回去）3 杀手（**b05 + b12 + b13**）；M17R（构造器只做纯字符串排序，R4 新造）4 杀手（b05/b12/b13/f02）；回归对照 M04R 2、M05R 26、M14R 26、M16R 43；pristine 复原后 `219 passed`；副本已删，仓库三文件 sha 复验 MATCH | `L4-round2-mutation.txt` |
| **E4** 反作弊全量重扫 | ✅ | ① skip/skipif/xfail：AST 节点 `[]`、`pytest.mark.skip` 0、`pytest.mark.xfail` 0、`@skip/@xfail` 0、`pytest.skip(` 0、`pytest.xfail(` 0（两文件皆是）；`assert True` 裸断言 0；`try:` 块仅 2 处且都在**未改动**的既有函数内（p04 等）。② collected **209 → 219**，**删除集 = `[]`**，新增 10 个 id 全列（b11/b12/b13、c12×3、c02 新增 3 参、j_p11）。③ 209 个既有 id 的**函数级源码逐行 diff**：`test_config_placeholder.py` 只有 **b05** 一个函数变（加 docstring + 期望值改裁决 9 序，属裁决 23 明令），其余 143 个顶层 def 逐字未变、删除 0；`test_config_properties.py` 只有 **`_join`** 变，17 个 `test_t05_j_*` **全部逐字相同**；模块常量只有 `MISS_STRINGS` / `FILLED_TEXTS` 各**追加** 3 值，无删除、无新增/移除常量。④ 实现侧唯一的分支变化是**删掉**双分支（减少绕过路径，非增加） | `L4-round2-anticheat-diff.txt`、`L4-round2-probe.txt` §E4 |
| **E5** properties oracle 改动合法性 | ✅ | 属**oracle 对齐契约**：改前 oracle 遇 int 键直接 `TypeError: can only concatenate str (not "int") to str`，没有这次改动就不可能实现裁决 24 第 3 项要求的碰撞策略；R4 自建 4000 棵**纯 str 键**随机树，改前/改后 oracle 输出**逐字节相同，mismatch = 0** → 既有 P-10 证伪力零损失；`p06` 源码 **identical = True**（逐字保留，未削弱）；其余 17 个属性/正控测试全部 `same` | `L4-round2-probe.txt` §E5 |
| **E6** T05-A~T05-M 重判 | ✅ | 13 个字母组共 **219** 个 id，accounted = collected，13 组 **rc 全 0**：A 9 / B 18 / C 58 / D 14 / E 13 / F 7 / G 13 / H 22 / I 19 / J 18 / K 13 / L 5 / M 10。实现侧在新代码上重跑 R4 的全套 D1~D11 探针：T05-F 排序确定性（8 stem 乱序 → `[L1250]-[L1257]` 序，正反插入序相同，两次 `repr` 相等）；T05-I 三纯函数 I/O 名集交集空、`global/nonlocal=[]`、墙钟 token 仅 2 处注释英文词、入参不变/幂等、`load_all` 参数仍 `['config_dir']`；T05-K import 仍只 5 项、`dsm.models/numeric/reason_codes` **不在 `sys.modules`**；T05-L float 字面量 **0**、非 docstring 数值仅 `(58,'3')`+`(131,'0')×2`、`K-nn` 全文件 **0** 处、业务键配数值 **0** | `L4-round2-pytest.txt` §7、`L4-round2-probe-api.txt`、`L4-round2-probe-io.txt` |
| **E7** 三层 pytest 本人复跑 | ✅ | 全量 **`1487 passed in 5.03s`** rc=0；两个 config 文件 **`219 passed in 3.80s`** rc=0；`-k i09` **`3 passed, 198 deselected in 0.20s`** rc=0；collected 全量 **1487** / 两文件 **219**；汇总行 token 布尔：failed=False、error=False、errors=False、skipped=False、xfailed=False、xpassed=False、warning=False；算术复算：1487−219=**1268**（既有一项不坏）、219−209=**10**（新增）、1487−1477=**10** | `L4-round2-pytest.txt` §1~§6 |
| **E8** 门禁 | ✅ | `tools/normalize.py --check` 首行 **`NEEDS_NORMALIZATION 0 of 73 files`**，rc=**0**；`git status --porcelain` 8 项全 `??`（无非 `??` 条目）；`git diff --numstat` **空**；HEAD 短哈希 **`17dd568`**；仓库 `config/` 仍**空**；只读区 `/home/szf/dev/CampaignLab`：`git --no-optional-locks status --porcelain` **空**、HEAD **`0cccb76cdee94689448b547b6f06254c51b75d72`**、分支 **`m0-framework`**（全程只读，未触碰其工作树） | `L4-round2-gates.txt` |

---

## 3. 裁决 23 / 裁决 24 的逐项落实核对

### 裁决 23（关闭 F1）
| 要求（原文摘要） | 实测 | 判定 |
|---|---|---|
| 构造器改为无条件 `self.paths = canonical`，删除双分支 | L205 `self.paths = canonical`；全文件 `deduped == canonical` 0 命中；diff 仅 1 个 hunk（+15/−12，net +3） | ✅ |
| `missing_files` 一支不动 | L206-207 与改前逐字相同；实测顺序仍为裁决 18 序 | ✅ |
| docstring 改写为单一口径，不得保留辩解文字 | 类 docstring 第 181~199 行重写为「Ordering and deduplication have exactly one reading each, and both of them are ruling 9」；`names no key` / `order independent reading` / `Both branches` **各 0 命中** | ✅ |
| b05 期望改为 `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')`，docstring 注明裁决 9 / 23 | L552-553 逐字相符；docstring L543-549 明写「taken from the ADR text and NOT from what an implementation happens to return (H-11)」 | ✅ |
| 允许**新增**：① 逆文件序仍出文件序；② 未知 stem 排最后且内部路径升序 | 新增 b12（逆文件序 4 stem）、b13（`SYN-unknown` 排最后、内部 `SYN-a` < `SYN-b`），R4 独立重算两者期望值均吻合 | ✅ |
| 不得削弱既有用例断言强度 | 函数级 diff：144 个既有顶层 def 中只有 b05 变，且是**加强**（期望值从纯字符串序改为更强的裁决 9 序）；无任何断言被删或放宽 | ✅ |
| 连带影响核对：b04 / b06 / b07 / f02 / g11 期望值不变 | 五者源码**逐字未变**（E4.3 changed 列表只有 b05），且全部通过；所有经 `load_all` 抛错的用例期望值亦未变（diff 中无相关 hunk） | ✅ |

### 裁决 24（关闭 F2；本裁决下 `dsm/config.py` 不得改动）
| 要求（原文摘要） | 实测 | 判定 |
|---|---|---|
| 本裁决下 `dsm/config.py` 不得因裁决 24 改动 | config.py 唯一 hunk 落在 `ConfigPlaceholderError` 的 docstring 与 `__init__`（裁决 23 范围）；`is_placeholder_value` / `_walk` / `scan_config_trees` / `_join` 逐字未变 | ✅ |
| 第 1 项：T05-C 组补 `''` / `'   '` / `'\t\n '` 三例，断言 `is False`；并加入属性侧「已填值」字母表 | 新增 c12（3 参，且**额外**在树层面断言 `find_placeholders(...) == ()` 与 `scan_config_trees(...) == ()`，比裁决要求更强）；`MISS_STRINGS` 追加同三值（c02 自动 +3 参）；`FILLED_TEXTS` 追加同三值 → p10 / n01 / n02 / n03 同时成为 M09 的杀手 | ✅ |
| 第 2 项：新增 `scan_config_trees({'s': {1:'TODO','1':'TBD'}}) == ('s.1',)` 作 M12 杀手 | 新增 b11，且**额外**断言 `find_placeholders(tree, root='s') == ('s.1','s.1')`（钉住裁决 11「raw walk 不去重」）；实测 M12R 被 b11 + j_p11 杀掉 | ✅ |
| 第 3 项：p06 **不得删除**，但必须补一条可达断言（策略允许 int/str 碰撞键，断言 `len(paths)==len(set(paths))` 且碰撞层只贡献一条） | p06 源码 identical=True（逐字保留）；新增 `colliding_dict` 策略 + p11，p11 断言 `walked.count(SYN_STEM+'.1')==2`、`len(paths)==len(set(paths))`、`paths.count(SYN_STEM+'.1')==1`、`paths==tuple(sorted(set(paths)))` | ✅ |
| 第 4 项：O1 定性为契约内行为，不再挂待办 | 本 ADR 不再把 O1 列为待修项 | ✅ |
| 第 5 项：`_join` 的裁决 22 注释顺延至 S1-T06，本轮不做 | `dsm/config.py` L220 `def _join(root, rel)` 及其 docstring **逐字未变**（diff 无该 hunk） | ✅ |

---

## 4. 观察项（不判 ❌，不需本轮处理）

| 编号 | 观察 | 实测 | 处置建议 |
|---|---|---|---|
| O-R2-1 | 构造器现在恒用 `_path_key` 排序，等于**替 `scan_config_trees` 兜底**：经 `load_all` 的排序类用例对「scan 侧排序缺陷」的灵敏度下降 | 同一变异体（scan 改用插入序）第 1 轮被 **3** 个用例杀（f02 / f03 / f06），本轮只被 **2** 个杀（f03 / f06）——f02 走 `load_all`，其顺序被构造器修正后不再报错 | 非缺陷（裁决 9 端到端仍成立，且排序被双重保证）；仅记录，S3/S9 若复用 `scan_config_trees` 需自带排序闸 |
| O-R2-2 | `[L878]`「收集**全部**未填字段路径」与裁决 9「同一路径只出现一次」在 int/str 键碰撞时存在字面张力（2 个未填值 → 消息首行 N=1） | `find_placeholders({1:'TODO','1':'TBD'}, root='s')` = `('s.1','s.1')`，`scan_config_trees` 后 = `('s.1',)` | 裁决 24 第 2 项已在其自身权限内裁定「去重按裁决 9 生效，N 为去重后计数」；路径表示法本就由 ADR 定义（digest 事实记录第 1 条：SDD 全文未给写法），且 `[L877]` 六份生产配置的键均为字符串 → **不构成与 SDD 的冲突**，无需上报变通 |
| O-R2-3 | R4 上一轮 ADR §7 表格中把第 1 轮 M04 的杀手写作「f02、f05、b08」，属**当时的推断而非实测**；实测（`L4-mutation.txt` L90-92）为 f02 / f03 / f06 | 本轮 `L4-round2-mutation.txt` 直接列出杀手 id 原文 | R4 自我更正，特此记录；上轮 ADR 按纪律**不回改**（其 sha 须保持 `aeb4e2fb5346`） |
| O-R2-4 | `test_config_properties.py` 的 int 字面量集合由 `[0,1,3,4,8,60]` 变为 `[0,1,2,3,4,8,60]`（新增 `max_size=2` 与碰撞键 `1`） | H-5 自扫描 l04 / l05 通过；b11 / p11 的 docstring 均明写「The 1 ... is a key-collision probe, not a business value (H-5)」 | 非业务数值，合规 |

---

## 5. 给 S1-T06 / S9-T01 的挂钩事实增量（本轮变更部分）

> 上一轮 ADR §5 的 12 个公开名清单、5 个常量实测值、`AppConfig.model_fields`、3 条消息常量逐字文本、
> 11 个私有辅助函数名清单**全部继续有效**（R4 在新代码上重跑同一探针：公开名仍恰为 12 个、
> 无增无减，四个函数签名与 `ConfigPlaceholderError.__init__` 签名逐字未变，
> `ConfigTree == dict[str, Any]` 仍为 True，`EXIT_CONFIG` 仍 3）。以下是**增量**。

1. **行为变更（唯一一处）**：`ConfigPlaceholderError(paths, missing_files)` 的 `paths` 属性
   现在**无条件**按裁决 9 的 `_path_key`（`[L1250]-[L1257]` 文件固定序 → 文件内路径字符串升序）
   排序去重；清单外 stem 取最后一名（`_file_rank` 返回 `len(_FILE_ORDER)`）并在其块内仍按路径升序。
   → **S9-T01 的 cli 可以直接把 `err.paths` 原序呈现，不必再排序**；消息文本仍由
   `_format_message` 生成，格式未变（首行 `配置含 N 个未签认占位值（退出码 3）`，N = 去重后计数）。
2. **`err.exit_code` 仍是实例属性且恒等于 `EXIT_CONFIG`（= 3）**，S9-T01 必须 `from dsm.config import EXIT_CONFIG`，
   不得另写字面量（裁决 2 / H-7）。
3. **新行号（供 T06 定位，`dsm/config.py` 现 480 行）**：`EXIT_CONFIG = 3` @L58；
   `_MESSAGE_HEAD` @L122、`_MESSAGE_MISSING_HEAD` @L123、`_MESSAGE_ITEM` @L124；
   `class ConfigPlaceholderError` 的 `__init__` @L202、`self.paths = canonical` @L205；
   `_join` @L220；`def load_all(config_dir: str | Path) -> AppConfig` @L427、
   `paths = scan_config_trees(trees)` @L452、`raise ConfigPlaceholderError(...)` @L454、
   **`# ---- S1-T06 hook (ruling 1) ----` @L456**、`return AppConfig(` @L473。
   → T06 的 `[L879]` 语义校验与 `[L880]` 权重版本校验插在 **L456 起的注释块**位置，
   `load_all` 骨架（读文件 → 扫描 → 挂钩点 → 返回）不变；`--period` / `--run-at`
   以**可选关键字参数**追加（当前参数列表实测仍恰为 `['config_dir']`）。
4. **`ConfigSemanticError` / `WeightVersionInvalidError` 仍未定义**（`hasattr` 双 False），由 T06 定义。
5. **T06 首次触碰 `dsm/config.py` 时的顺手事项（裁决 24 第 5 项顺延）**：给 `_join` 的 docstring
   补一行裁决 22 的 `[` 补口说明（当前口径由 `_walk` 的 `'%s[%d]'` 承载，行为已正确，仅缺注释）。
6. **数值入口仍不转换**（裁决 4 / B-022）：实测 `7:int` / `-3:int` / `1.25:float` / `True:bool` 原样保留，
   树内无 `Decimal`；T06 取数必须走 `numeric.D` / `numeric.as_minor` / `numeric.from_float`（H-4）。
7. **非字符串 YAML 键**：`_walk` 以 `str(key)` 拼路径，同层 int `1` 与 str `'1'` 会折叠成同一路径
   （裁决 24 第 2 项已定性为契约内行为）；T06 若按路径反查取值，需注意该路径不可逆。

---

## 6. 复核纪律自证（本轮）

- R4 未修改 `dsm/`、`tests/`、`docs/adr/ORCH-23.md`、`docs/adr/ORCH-24.md`、`docs/digest/`、
  `ops/blockers.md`、`ops/dag-state.json`、`ops/evidence/S1-T05/L1-red.txt`、`L5-r6-fix.txt`、
  `L5-r6-fix2.txt`、`docs/adr/ORCH-23-review-S1-T05.md` 中任何一个字节：
  `git diff --numstat` 与 `--cached --numstat` 均空，上述文件 sha256[:12] 全部与主控给定值相符（§0 表）。
- 未执行任何 `git add` / `commit` / `push` / `amend` / `force`（H-12）；HEAD 仍 `17dd568ff18c4e48b126b5e1a5bb72b0e0bd6ae0`。
- 本轮 R4 新增文件仅 8 个：本 ADR + `ops/evidence/S1-T05/L4-round2-{probe,mutation,pytest,anticheat-diff,probe-api,probe-io,gates}.txt`。
  落库走 H-2 三步管线：staging `C:\Users\szf\AppData\Local\Temp\dsm_stage_S1-T05_r4b\`（根内只放待落库文件）
  → `rsync -a` → `/home/szf/venvs/dsm/bin/python tools/normalize.py` → `--check` = `NEEDS_NORMALIZATION 0`。
- 变异实验在仓库外副本 `/mnt/c/Users/szf/AppData/Local/Temp/dsm_ops/S1-T05-r4b/mut2` 内进行，
  跑完已删（`scratch tree removed : True`），并在同一证据文件末尾以 sha256 自证仓库三文件未被污染。
- 未读取 `工行参考文件/` 下任何文档全文（SDD 一律经 `docs/digest/S1-T05.md` 行号摘录引用）；
  邻仓 `/home/szf/dev/CampaignLab` 仅执行 `git --no-optional-locks status/rev-parse` 只读查询，未触碰其工作树。
- pytest 全程未再加 `-q`（pyproject `addopts` 已含）；所有计数均由 `.py` + `subprocess` 取得，未在 bash 里 `pytest | grep`。
- 本文件的行数 / 字节数 / sha256[:12] / BOM / CR / TAB 于 rsync + normalize **之后**从磁盘实测，
  记于 `ops/evidence/S1-T05/L4-round2-gates.txt` 与 R4 回报正文。
