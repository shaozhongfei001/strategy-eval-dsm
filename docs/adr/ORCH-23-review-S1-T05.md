<!-- ADR: ORCH-23-review-S1-T05 | task: S1-T05 | role: R4 independent review (L4) | 契约权威: docs/adr/ORCH-23.md（337 行 / 22 条裁决）| 日期: 2026-11-24 -->

# ORCH-23-review-S1-T05：`dsm/config.py` PLACEHOLDER 递归拦截 L4 独立复核签认

**角色**：R4（独立复核）。本文件只做判定，不含任何代码或测试修改（修复归 R6）。
**判定依据**（H-11 要求判定依据落 `docs/adr/`）：`docs/adr/ORCH-23.md` 裁决 1~22 与 §7 验收清单
T05-A~T05-M；SDD 原文一律经 `docs/digest/S1-T05.md` 的行号摘录引用，未读取
`工行参考文件/` 下任何文档全文。
**实测证据**：`ops/evidence/S1-T05/L4-pytest.txt` / `L4-probe-api.txt` / `L4-probe-io.txt` /
`L4-checklist.txt` / `L4-mutation.txt` / `L4-hygiene.txt`（全部由 R4 本人产出，未采信任何转述）。

---

## 0. 复核对象与输入指纹（R4 实测，非转述）

| 文件 | 行数 | 字节 | sha256[:12] | 与主控给定值 |
|---|---|---|---|---|
| `docs/adr/ORCH-23.md` | 337 | 28734 | `cb7d9222fa27` | 一致（337 行 / 22 条裁决） |
| `docs/digest/S1-T05.md` | 115 | 14892 | `52c070190063` | 一致（115 行） |
| `dsm/config.py` | 477 | 22730 | `d8c49a1aeecc` | **一致** |
| `tests/test_config_placeholder.py` | 1558 | 64209 | `a81fb14e687c` | **一致**（114 个 `def test_`） |
| `tests/test_config_properties.py` | 486 | 19455 | `912eb7f672a2` | **一致**（17 个 `def test_`） |
| `ops/evidence/S1-T05/L1-red.txt` | 672 | 59352 | `c439084b33ac` | **一致，未被改写** |
| `ops/evidence/S1-T05/L5-r6-fix.txt` | 164 | 9825 | `90199059de9a` | **一致** |

仓库状态：HEAD `17dd568`，`git diff --numstat` 为**空**（无 tracked 文件被改），
`git status --porcelain` 复核开始时仅 6 项未跟踪在制品（`L4-probe-io.txt` §D11 原文），R4 产物落库后为 7 项（§9 与 `L4-hygiene.txt` §5）。
R4 全量复跑：**`1477 passed in 4.93s`**，rc=0；两个 config 文件单跑 `209 passed`；
`-k i09` → `3 passed, 189 deselected`；collected 全量 1477 / 两文件 209；
1477 − 209 = **1268** 既有项，与 T05-M「既有 1268 项一条不坏」吻合。

---

## 1. 裁决

**R4 VERDICT: FAIL(2 项)**

拦截语义、路径表示法、排序去重、异常消息、`AppConfig` 形态、纯函数纪律、H-5/H-9/最小实现
**全部符合契约**；T05-A~T05-M **13 条全部满足**；H-11 反作弊审计**完全干净**（无质量事故）。
两项 ❌ 均**不是拦截行为的缺陷**，而是「契约条目 ↔ 测试闸」层面的可实测偏差，且二者的修复
都超出 R2/R6 现有授权，需主控裁决：

| 编号 | 严重度 | 一句话 | 归属 |
|---|---|---|---|
| **F1** | 中 | `ConfigPlaceholderError.paths` 对**调用方直接构造**的可迭代对象未套用裁决 9 的「文件顺序优先」键，而是退化为纯字符串排序；裁决 11 明写该属性「已按裁决 9 排序去重」 | 契约冲突：裁决 9/11 ↔ 测试 b05，需主控立裁决或改测试 |
| **F2** | 低 | 裁决 19（空串/纯空白串**不命中**）在两个测试文件中**零覆盖**，变异体 M09 存活；属性 p06 的去重断言在现有策略下**结构性恒真** | 测试闸缺口（R3 写集），需主控授权补测 |

**不构成 QUALITY_INCIDENT**：未发现任何「让它变绿」的手段（无 skip/xfail、无删测试、
无断言削弱、无 golden 改动、`dsm/config.py` 未被 R6 触碰、`L1-red.txt` 未被改写）。

---

## 2. D1~D14 逐条判定

| 条目 | 判定 | 实测依据（证据位置） | 契约出处 |
|---|---|---|---|
| **D1** 公开契约 | ✅ | `L4-probe-api.txt` §D1：AST 统计**本模块定义**的公开名恰为 12 个，与裁决 11 逐字相同，`missing=[]` / `extra DEFINED=[]`；签名 `is_placeholder_value(value)`、`find_placeholders(tree: Any, *, root: str = '') -> tuple[str, ...]`、`scan_config_trees(trees: Mapping[str, dict[str, Any]]) -> tuple[str, ...]`、`load_all(config_dir: str | Path) -> AppConfig`、`ConfigPlaceholderError.__init__(self, paths: Iterable[str], missing_files: Iterable[str] = ())`；`ConfigTree == dict[str, Any]` → `True`（origin 为 `dict`）；构造器实测接受 list / tuple / set / generator，`paths`、`missing_files` 均为 `tuple` | 裁决 11、裁决 3、裁决 16 |
| **D2** 命中口径 | ✅ | `L4-probe-api.txt` §D2：自建 19 值命中表 + 31 值不命中表**零违例**（含 `placeholder` / `pLaCeHoLdEr` / `'  PLACEHOLDER  '` / `'\tPLACEHOLDER\n'` / `tbd` / `PLACEHOLDER_K-01` / `TODO: sign off` / `None` 全命中；`OK`/`FROZEN`/`abcTODOdef`/`XPLACEHOLDER`/`MY_TBD`/`TO-DO`/`''`/`'   '`/`'\t\n '`/`0`/`1`/`-1`/`0.5`/`True`/`False`/`{}`/`[]` 全不命中）；`find_placeholders({'PLACEHOLDER': 'OK'})` = `()` → **键不扫描**；返回值为真 `bool`；docstring 实测含 `ruling 19` / `do NOT hit` / `B-023` / `ruling 6` / `dict keys are never scanned` 五处 | 裁决 5 / 6 / 19 |
| **D3** 路径表示法 | ✅ | `L4-probe-api.txt` §D3：`{'a': {'b': [None,'OK',{'c':'TBD'}]}, 'd':'PLACEHOLDER_X'}` → `('a.b[0]','a.b[2].c','d')`，加 `root='eval_config'` 后逐条加前缀；`find_placeholders(None)` = `('',)`、`root='redlines'` → `('redlines',)`（无尾点）；`['TODO',None]` + `root='stem'` → `('stem[0]','stem[1]')`；嵌套 list → `s.x[0][0]`；**自建 5 树 × 5 root = 25 组前缀不变式（按裁决 22 的 join 口径）失败 0 组**；`root=''` 时以 `.` 开头的路径 = 0 条；路径不含 `.yaml` | 裁决 8 / 17 / 22 |
| **D4** 排序去重不截断 | ✅ | `L4-probe-api.txt` §D4：8 stem 乱序入参 → `eval_config.e → weights_WV-a.k → weights_WV-b.k → redlines.r → grade_rules.x → anchor_set.y → ahp_matrices.z → zzz_unrelated.q`，与 `[L1250]-[L1257]` 顺序逐项相符；正/反插入序结果 `True` 相同；两次调用 `repr` 逐字节相等；`len==len(set)`；40 命中 → 40 条，200×2 命中 → **400 条**、消息 **401 行**（不截断）；`scan_config_trees` 接受只读 `Mapping` | 裁决 9 / 16 / 18、`[L1250]-[L1257]` |
| **D5** 异常与消息 | ❌ **（F1）** | `L4-probe-api.txt` §D5 + `L4-probe-io.txt` §D5：消息逐字等于裁决 9/10 定死文本（`True`）；`EXIT_CONFIG == exit_code == 3`，全模块 int 字面量仅 `(58,'3')` 与 `(131,'0')×2`；`missing_files` = `('eval_config','weights_*','redlines','grade_rules','anchor_set','ahp_matrices')`，`weights_*` == `WEIGHTS_GLOB[:-5]`；缺失**不**用空树顶替（缺 `redlines.yaml` → 抛错、`returned an AppConfig? False`）；占位与缺失**同一次抛错**。**但** `ConfigPlaceholderError(['redlines.SYN-z','eval_config.SYN-m','anchor_set.SYN-a']).paths` 实测 = `('anchor_set.SYN-a','eval_config.SYN-m','redlines.SYN-z')`，裁决 9 应为 `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')` | 裁决 9 / 10 / 2 / 11、`[L878]` `[L1259]` `[L1080]` |
| **D6** `AppConfig` | ✅ | `L4-probe-io.txt` §D6：`model_fields` 键集恰为 6 槽且逐字相符、6 项全 required；`model_config = {'frozen': True, 'extra': 'forbid'}`；改赋值 / 未声明槽 `metric_dict` / 只给 5 槽 → 三种情形均 `ValidationError`；`[L1250]-[L1257]` 的 26 个内容键**零个**被提升为字段；模块内只定义 2 个类（`AppConfig` / `ConfigPlaceholderError`），无额外 pydantic 模型；原始标量原样保留（`7:int` / `-3:int` / `1.25:float` / `True:bool`，树内无 `Decimal`）；`weights` 键 = 文件 stem `['weights_WV-SYN-0001']` | 裁决 3 / 4、`[L871]` `[L877]` |
| **D7** 纯函数与 H-8 | ✅ | `L4-probe-io.txt` §D7：三个纯函数的调用集分别为 `{any,isinstance,startswith,strip,upper}` / `{_walk,tuple}` / `{_ordered_stems,find_placeholders,fromkeys,sorted,tuple}`，与 I/O 名集交集**均为空**，其私有辅助亦无 I/O；`global`/`nonlocal` = `[]`；墙钟/随机/环境 token 命中仅 2 处，均为 docstring/注释里的英文单词 “wall clock”（L32、L214），无一处调用；入参不变 `True`×3、幂等 `True`×2、模块 globals 前后相同 `True`；`scan_config_trees` 对磁盘上不存在的 stem 正常返回；`load_all` 参数列表实测 `['config_dir']`，`str` 与 `Path` 均可 | H-8、裁决 11 |
| **D8** H-5 / H-4 | ✅ | `L4-probe-io.txt` §D8：`dsm/config.py` 非 docstring 数值字面量仅 3 处 = `(58,'3')` 退出码、`(131,'0')×2`（`path.split('.')[0].split('[')[0]` 的下标）；**float 字面量 0 个**；业务键配数值 = `[]`；`K-[0-9][0-9]` 全文件（含 docstring）**0 处**；`PLACEHOLDER` 出现 13 次；两个测试文件 float 字面量（TYPE_PROBE 赋值之外）均为 `[]`，`TYPE_PROBE_FLOAT = 0.5  # 仅类型探针，非业务值` 各有 1 处 | `[L78]` `[L1259]` `[L1806]`、H-5 / H-4 |
| **D9** H-9 分层 | ✅ | `L4-probe-io.txt` §D9：全部 import = `collections.abc(Iterable,Mapping)` / `pathlib(Path)` / `typing(Any)` / `yaml` / `pydantic(BaseModel,ConfigDict)`；L0a/L0b 五个模块命中 `[]`；`dsm.models`/`dsm.numeric`/`dsm.reason_codes` 命中 `[]`，且 import `dsm.config` 后三者**均不在 `sys.modules`**；第三方仅 `yaml` 与 `pydantic` | H-9 INV-1、裁决 12、`[L355]` `[L816]` |
| **D10** 最小实现 | ✅ | `L4-probe-io.txt` §D10：`hasattr ConfigSemanticError = False`、`hasattr WeightVersionInvalidError = False`；`[L879]`/`[L880]` 的 7 个语义词（attainment_floor / metric_dict / FROZEN / effective_from / effective_to / whatif_run_id / strategy_master）在源码中出现 5 行，**全部为 `#` 注释**，无一行是可执行代码；`load_all` 内可执行顺序实测 = `READ FILES(25) → PLACEHOLDER SCAN(26) → RAISE(28) → T06 HOOK COMMENT(30) → RETURN AppConfig(47)`，挂钩点注释存在且位于扫描之后、返回之前 | 裁决 1、`[L879]` `[L880]` `[L881]` |
| **D11** H-11 反作弊 | ✅ | `L4-probe-io.txt` §D11：第 1221 行逐字 == 裁决 21 要求的 `argument = {'SYN-a': ['PLACEHOLDER', None], 'SYN-c': 'TODO'}`（比对结果 `True`）；`assert argument == before` 保留（L1234）；else 调用序列 `fn(argument['SYN-a'])` / `fn(argument['SYN-c'])` 保留（L1232-1233）；i09 全体 17 行内**无 `.values()`**、全仓无 `for value in argument.values()` 遍历式改法；两个测试文件 skip/xfail 标记 = `[]`；`def test_` 计数 114 + 17 与 L1 记录一致，collected 209 = L1 的 193 failed + 16 passed；`dsm/config.py` sha 仍 `d8c49a1aeecc`（R6 未触碰）；`L1-red.txt` sha 仍 `c439084b33ac`（未改写）；`git diff --numstat` **空**、`git diff --stat` **空**、HEAD 仍 `17dd568` | H-11、裁决 21 |
| **D12** P-10 证伪能力 | ❌ **（F2）** | `L4-mutation.txt`：16 个变异体 **14 killed / 2 survived**，pristine 复原后 209 passed。任务点名的三类缺陷全部被抓：漏拦占位值（M01 2 / M02 18 / M03 15 / M14 25 / M15 13）、排序不稳定（M04 3 / M16 41）、返回了 AppConfig（M05 26，含 `j_p04`）；另 M06 只报第一个 17、M07 截断 1、M08 下标 1 起 15、M10 空树顶替 8、M13 extra 放宽 2。**但**：M09（把空串变成命中，即违反裁决 19）**存活，209 passed 0 failed**；M12（去掉 `scan_config_trees` 的去重）**存活**，因为 p06 的 `paths == tuple(sorted(set(paths)))` 在现有策略下**结构性恒真**（str 键不可能产生重复路径） | `[L882]` `[L1434]`、裁决 14 / 13 |
| **D13** T05-A~T05-M | ✅ | `L4-checklist.txt`：13 个字母组共 209 个 test id **全部归属、无遗漏**（unaccounted = 0），逐组 rc=0：A 9 / B 15 / C 52 / D 14 / E 13 / F 7 / G 13 / H 22 / I 19 / J 17 / K 13 / L 5 / M 10；实现侧逐条见 §4 本文件 | ORCH-23 §7 |
| **D14** 必交产物 | ✅ | 本文件 §5 已抄入 12 个公开名的完整签名、5 个常量实测值、`AppConfig.model_fields`、3 条消息常量逐字文本、11 个私有辅助函数名清单 | 任务书 D14 |

---

## 3. F1 详述：`paths` 排序键的契约冲突（严重度 中）

**期望（契约出处）**
- 裁决 9：「**排序**：先按文件在 `[L1250]-[L1257]` 清单中的固定顺序（eval_config → weights →
  redlines → grade_rules → anchor_set → ahp_matrices；weights 内按 stem 升序），再按路径字符串升序」。
- 裁决 11：`paths: tuple[str, ...]  # 已按裁决 9 排序去重`（无任何「仅当来自 load_all」的限定）。
- 裁决 18 的先例：「R3 的测试只钉内容 / 去重 / 确定性（不钉顺序），本裁决是**更强的实现要求**，
  与测试不冲突」——即测试弱于 ADR 时以 ADR 为准。

**实际（实测）**
```
ConfigPlaceholderError(['redlines.SYN-z', 'eval_config.SYN-m', 'anchor_set.SYN-a']).paths
  actual                    = ('anchor_set.SYN-a', 'eval_config.SYN-m', 'redlines.SYN-z')
  ruling 9 / ruling 11 want = ('eval_config.SYN-m', 'redlines.SYN-z', 'anchor_set.SYN-a')
ConfigPlaceholderError(['ahp_matrices.z', 'weights_WV-a.k', 'eval_config.e']).paths
  actual                    = ('ahp_matrices.z', 'eval_config.e', 'weights_WV-a.k')
```
源码根因（`dsm/config.py` 第 200~202 行，实测行号）：
```
deduped   = tuple(dict.fromkeys(paths))
canonical = tuple(sorted(deduped, key=_path_key))
self.paths = canonical if deduped == canonical else tuple(sorted(deduped))
```
`canonical if deduped == canonical` 分支在语义上等于 `deduped`，即**该分支恒为空操作**；
换言之构造器**从不真正套用** `_path_key`（裁决 9 键），只在入参已恰好是规范序时原样保留，
其余一律退化为纯 `str` 排序。

**冲突来源**：`tests/test_config_placeholder.py:537-541` 的 `test_t05_b05_error_paths_are_sorted`
用三个**不同文件**的路径断言纯字符串序。变异体 **M11**（把该行改成无条件 `self.paths = canonical`，
即严格照裁决 9/11 实现）实测**只被 b05 一个用例杀掉**（`1 failed, 208 passed`）——
证明「按 ADR 字面实现」与「b05 通过」互斥，二者不可能同时成立。
该测试文件头部自陈只写了「rulings 1-15」，b05 成文早于裁决 16~22，属**契约演进遗留冲突**，
不是 R2 的偷工，也不是 R3 的作弊。

**影响面**：生产路径（`load_all` → `scan_config_trees` → 构造器）本身合规，因为
`scan_config_trees` 已按裁决 9 排好序，构造器的 `deduped == canonical` 分支原样透传
（实测 `('eval_config.e','weights_WV-a.k','ahp_matrices.z')` 不变）。故 **T05 行为无功能缺陷**；
风险在于 ①`paths` 作为公开属性对 S9-T01 的 cli 消息呈现不保证裁决 9 顺序；
②`weights_WV.yaml` 与 `weights_WV-a.yaml` 并存这类边界下，`'-'(0x2D) < '.'(0x2E)` 会使
透传分支判定失败、把 `scan_config_trees` 的规范序**重排成纯字符串序**（可实测复现的隐患）。

**建议改法（二选一，均需主控授权，R4 不自行修复）**
1. 立**裁决 23**：`paths` 无条件按裁决 9 键排序（`self.paths = tuple(sorted(dict.fromkeys(paths), key=_path_key))`），
   同时把 b05 的期望改为 `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')`；
   与裁决 18 对 `missing_files` 的处理对称，S9-T01 的消息顺序即可完全确定。
2. 或立**裁决 23'**：明确「裁决 9 的文件顺序只约束 `scan_config_trees` / `load_all` 的产出，
   构造器对调用方直接传入的可迭代对象只做去重 + 纯字符串排序」，并把该口径写进 b05 的 docstring，
   同时删掉恒为空操作的 `canonical if deduped == canonical` 分支（保留死逻辑本身也是可维护性缺陷）。

---

## 4. F2 详述与观察项

### F2（严重度 低）：裁决 19 零测试闸 + 属性 p06 结构性恒真
- 变异体 **M09**（在 `is_placeholder_value` 里加 `if stripped == '': return True`，即违反裁决 19）
  **存活**：`209 passed`。实测原因：`MISS_STRINGS` / `HIT_STRINGS` / `FILLED_TEXTS` /
  `PLACEHOLDER_VALUES` 四个表中**均不含**空串或纯空白串；`filled_leaf` 策略只从
  `FILLED_TEXTS` / `integers(-1,1)` / `booleans` / `just(TYPE_PROBE_FLOAT)` 取值，
  `st.text()` 只用于生成**键**，从不生成叶子值。
- R3 自己在文件头（L231 附近）写明「Empty and whitespace-only strings are deliberately absent —
  the ADR iff does not mention them, so this file does not decide them either」，
  而**裁决 19 成文在后**，测试未随之补闸。
- 实现本身**正确**（实测 `is_placeholder_value('') = False`、`'   ' → False`、`'\t\n ' → False`），
  且裁决 19 要求的「在 `is_placeholder_value` 注释里写明本裁决及理由」已落实（docstring 含
  `ruling 19` / 三条理由 / `B-023`）。
- 变异体 **M12**（删掉 `scan_config_trees` 末尾的 `dict.fromkeys`）**存活**：p06 的
  `paths == tuple(sorted(set(paths)))` 在 str 键前提下不可能被违反，属**恒真断言**。
  去重本身在**可达处已有闸**（b04 钉构造器去重，M12 不影响它）。
- 建议：经主控授权后在 R3 写集内补 3 个参数化用例（`''` / `'   '` / `'\t\n '` → `is False`，
  归入 T05-C 组），并给 p06 换一个可达的断言（例如对同一 stem 传入两棵共享路径的树，
  或直接改为断言 `len(paths) == len(_oracle_hits(...))`，该断言已由 p02/p05 覆盖，故也可仅删除 p06 的
  恒真部分）。**不得**为此改动 `dsm/config.py`。

### 观察项（不判 ❌，供 T06 / S9-T01 参考）
| 编号 | 观察 | 实测 | 处置 |
|---|---|---|---|
| O1 | 非字符串 YAML 键与同值 str 键相撞时，两个命中位置会折叠成一条路径 | `find_placeholders({1:'TODO','1':'TBD'}, root='s')` = `('s.1','s.1')`，`scan_config_trees` 后 = `('s.1',)` | `[L877]` 的六份配置不会产生；SDD 从未设想非字符串键。仅作记录，不建议 T05 加防御 |
| O2 | `_stem_of` 以第一个 `.` 或 `[` 截断，含点的文件 stem（如 `eval_config.v2.yaml`）会被误归到 `eval_config` 排序位 | 源码 `path.split('.')[0].split('[')[0]` | 六个固定 stem 与 `weights_*` 通配均不含点，不可达；若 S2 fixtures 引入含点 stem 须回看 |
| O3 | `_join` 的 docstring 只写了裁决 17 的三分支，未提裁决 22 的 `[` 补口（该口径实际由 `_walk` 的 `'%s[%d]'` 实现） | `L4-probe-api.txt` §D3：25 组不变式按裁决 22 join 全通过 | 裁决 22 明写「不改实现、不改测试」，故非缺陷；建议 T06 动该文件时顺手补一行注释 |
| O4 | 模块命名空间里可见 6 个 import 进来的公开符号（`Any`/`BaseModel`/`ConfigDict`/`Iterable`/`Mapping`/`Path`）；未定义 `__all__` | `L4-probe-api.txt` §D1 | 裁决 11 只约束**本模块定义**的名字（实测恰 12 个），ORCH-23 附亦确认无 `__all__` 不属缺口 |
| O5 | `scan_config_trees` 的组内去重发生在跨文件拼接之后，因此不同 stem 的路径不可能互相吞并 | 路径均以 stem 为前缀 | 符合裁决 9 |

---

## 5. D14 必交产物：`dsm/config.py` 公开 API 逐字清单

> 本节是 **S1-T06**（语义校验挂钩）与 **S9-T01**（cli 退出码）的**输入事实**，
> 全部由 R4 实测抄录（`L4-probe-api.txt` §D1），非转述。对应文件指纹：
> `dsm/config.py` 477 行 / 22730 B / sha256[:12] `d8c49a1aeecc`。

### 5.1 12 个公开名（完整签名，`inspect.signature` 原文）
```
EXIT_CONFIG = 3
REQUIRED_CONFIG_STEMS = ('eval_config', 'redlines', 'grade_rules', 'anchor_set', 'ahp_matrices')
WEIGHTS_GLOB = 'weights_*.yaml'
PLACEHOLDER_TOKENS = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
PLACEHOLDER_PREFIXES = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
ConfigTree = dict[str, Any]          # typing.get_origin -> dict, get_args -> (str, typing.Any)

class AppConfig(BaseModel):          # model_config = ConfigDict(frozen=True, extra='forbid')
class ConfigPlaceholderError(Exception):
    def __init__(self, paths: Iterable[str], missing_files: Iterable[str] = ())

def is_placeholder_value(value)                                                     -> bool（实测返回真 bool，无注解）
def find_placeholders(tree: Any, *, root: str = '')                                  -> tuple[str, ...]
def scan_config_trees(trees: Mapping[str, ConfigTree])                               -> tuple[str, ...]
def load_all(config_dir: str | Path)                                                 -> AppConfig
```
- `AppConfig` 的 6 个字段（`model_fields` 实测，全部 required、无默认值）：
  `eval_config: dict[str, Any]` / `weights: dict[str, dict[str, Any]]` / `redlines: dict[str, Any]` /
  `grade_rules: dict[str, Any]` / `anchor_set: dict[str, Any]` / `ahp_matrices: dict[str, Any]`。
- `ConfigPlaceholderError` 的实例属性（实测类型）：`paths: tuple` / `missing_files: tuple` / `exit_code: int`（= 3）；
  MRO = `ConfigPlaceholderError → Exception → BaseException → object`；两个入参均接受任意可迭代
  （list / tuple / set / generator 实测均转成 `tuple`）。

### 5.2 5 个公开常量的实测值
| 常量 | 实测值 | 类型 | 出处 |
|---|---|---|---|
| `EXIT_CONFIG` | `3` | `int` | `[L881]` `[L1080]`，**S9-T01 的 `cli.py` 必须 import 此名，不得另写字面量**（裁决 2） |
| `REQUIRED_CONFIG_STEMS` | `('eval_config', 'redlines', 'grade_rules', 'anchor_set', 'ahp_matrices')` | `tuple` | 裁决 10；按 `[L1250]-[L1257]` 顺序，**不含** weights（weights 是通配要求） |
| `WEIGHTS_GLOB` | `'weights_*.yaml'` | `str` | `[L877]` 逐字，是 `[L1252]` `weights_WV-*.yaml` 的超集 |
| `PLACEHOLDER_TOKENS` | `('PLACEHOLDER', 'TODO', 'TBD', 'XXX')` | `tuple` | 裁决 5(a) 整值表，`[L878]` 四词 |
| `PLACEHOLDER_PREFIXES` | `('PLACEHOLDER', 'TODO', 'TBD', 'XXX')` | `tuple` | 裁决 5(b)(c) 前缀表；行方若改判为严格整值相等，改动面 = 本常量置空（B-023） |

### 5.3 三条消息常量的逐字文本（裁决 9 定死，供 V-5 / P-10 / S9-T01 呈现）
```
_MESSAGE_HEAD         = '配置含 %d 个未签认占位值（退出码 %d）'
_MESSAGE_MISSING_HEAD = '缺失必需配置文件 %d 份：'
_MESSAGE_ITEM         = '  - %s'
```
拼装规则（`_format_message`）：首行 head（`%d` 依次填 `len(paths)` 与 `exit_code`）→ 每条路径一行
`  - <path>` → **仅当** `missing_files` 非空时追加一个空行 + missing head（填 `len(missing_files)`）
+ 每份缺失一行 `  - <stem>`。全角括号与全角冒号属定死格式。
实测样例（2 条路径 + 2 份缺失）：
```
配置含 2 个未签认占位值（退出码 3）
  - a.path
  - b.path

缺失必需配置文件 2 份：
  - eval_config
  - redlines
```

### 5.4 私有辅助（11 个函数 + 7 个私有常量，全部下划线开头）
```
函数(11): _file_rank  _format_message  _join  _missing_key  _ordered_stems
          _path_key  _read_config_dir  _read_tree  _stem_of  _walk  _weights_stems
常量(7) : _FILE_ORDER = ('eval_config','weights','redlines','grade_rules','anchor_set','ahp_matrices')
          _WEIGHTS_PREFIX = 'weights_'      _WEIGHTS_GAP = 'weights_*'      _YAML_SUFFIX = '.yaml'
          _MESSAGE_HEAD / _MESSAGE_MISSING_HEAD / _MESSAGE_ITEM（见 5.3）
```
**给 S1-T06 的挂钩事实**：`load_all` 内可执行语句顺序实测为
`_read_config_dir(25) → scan_config_trees(26) → raise ConfigPlaceholderError(28) → 「---- S1-T06 hook (ruling 1) ----」注释块(30) → return AppConfig(47)`；
T06 的 `[L879]` 语义校验与 `[L880]` 权重版本校验应插在第 30 行起的注释块位置，
`ConfigSemanticError` / `WeightVersionInvalidError` 由 T06 定义（当前 `hasattr` 均为 `False`），
`--period` / `--run-at` 以**可选关键字参数**追加到 `load_all`（当前参数列表实测恰为 `['config_dir']`）。

---

## 6. T05-A ~ T05-M 逐条（13/13 满足）

| 编号 | 测试覆盖（实测 id 数 / rc） | 实现是否满足 | 证据 |
|---|---|---|---|
| T05-A | 9 / rc=0 | ✅ `EXIT_CONFIG == 3`、`exit_code == 3`、构造器 `(paths, missing_files=())` 存 tuple | `L4-probe-api.txt` §D1、§D5 |
| T05-B | 15 / rc=0 | ✅ N 处占位 → N 条路径，40 命中 → 40 条，200×2 → 400 条、消息 401 行 | `L4-probe-api.txt` §D4 |
| T05-C | 52 / rc=0 | ✅ 命中/不命中表 19+31 值零违例（含 `PLACEHOLDER_K-01`、带空格、int/float/bool） | `L4-probe-api.txt` §D2 |
| T05-D | 14 / rc=0 | ✅ `None` 一律命中；空 yaml 与只有注释的 yaml → 路径 == bare stem（`('eval_config',)` / `('anchor_set',)`） | `L4-probe-io.txt` §D5 |
| T05-E | 13 / rc=0 | ✅ 点号嵌套、`[i]` 0 起、stem 前缀、多份 weights 互不混淆、路径无 `.yaml` | `L4-probe-api.txt` §D3；变异体 M08/M16 被杀（15 / 41） |
| T05-F | 7 / rc=0 | ✅ 两次调用逐字节相等；文件顺序 = `[L1250]-[L1257]`；weights stem 升序；与插入序无关 | `L4-probe-api.txt` §D4；M04 被杀（3） |
| T05-G | 13 / rc=0 | ✅ 缺失与占位同一次抛错；`missing_files` 正确（含 `weights_*`）；不返回 AppConfig；不静默成功 | `L4-probe-io.txt` §D5；M10 被杀（8） |
| T05-H | 22 / rc=0 | ✅ 6 槽逐字、`model_fields` 恰 6、frozen、extra=forbid、26 个内容键零提升、原始标量不转换 | `L4-probe-io.txt` §D6；M13 被杀（2） |
| T05-I | 19 / rc=0 | ✅ 三纯函数无 I/O / 无全局变更 / 不变更入参 / 幂等；`load_all` 唯一 I/O 入口且只有 `config_dir` | `L4-probe-io.txt` §D7 |
| T05-J | 17 / rc=0 | ✅ p01~p10 + n01~n03 + s01~s04 全绿；`derandomize=True` / `database=None` / `max_examples=60` 与 `test_numeric_properties.py` 对齐（s01 断言）；同 seed 可复现 | `L4-mutation.txt`（M05 被 `j_p04` 等 26 项杀掉）；**唯 p06 恒真、裁决 19 未覆盖 → 见 F2** |
| T05-K | 13 / rc=0 | ✅ 无 L0a/L0b import；无 `dsm.models`/`numeric`/`reason_codes`；第三方仅 `yaml`+`pydantic` | `L4-probe-io.txt` §D9 |
| T05-L | 5 / rc=0 | ✅ 源码 float 字面量 0、非 docstring 数值仅 3/0/0、`K-nn` 0 处、业务键配数值 0 处；两测试文件同样干净 | `L4-probe-io.txt` §D8 |
| T05-M | 10 / rc=0 | ✅ R4 全量复跑 `1477 passed in 4.93s`，rc=0，无 failed/error/skipped/xfailed；既有 1268 项一条不坏 | `L4-pytest.txt` §1、§5 |

---

## 7. 变异测试摘要（D12，`L4-mutation.txt` 全文）

方法：把整仓复制到 `/mnt/c/Users/szf/AppData/Local/Temp/dsm_ops/S1-T05-r4/mut/repo`
（**仓库本体从未被修改**，脚本末尾附 3 个文件的 sha 自证），逐个注入单点缺陷后只跑两个 config
测试文件，每轮之间写回 pristine。命令：`pytest tests/test_config_placeholder.py
tests/test_config_properties.py --tb=no -rf -p no:cacheprovider`（未再加 `-q`）。

| 变异体 | 注入的缺陷 | 结果 | 杀手数 |
|---|---|---|---|
| M01 | `is_placeholder_value` 的 `None` 分支返回 False | KILLED | 2（d01、j_p10；`_walk` 另有独立 None 分支，故杀伤面小） |
| M02 | 删掉前缀命中分支（`PLACEHOLDER_K-01` 漏拦） | KILLED | 18 |
| M03 | 命中判定变成大小写敏感（去掉 `.upper()`） | KILLED | 15 |
| M04 | `scan_config_trees` 改用入参插入序 | KILLED | 3（f02、f05、b08） |
| M05 | `load_all` 只在缺文件时抛错，占位路径照样返回 AppConfig | KILLED | 26（含 j_p03、j_p04、j_p05） |
| M06 | 只报第一个命中 | KILLED | 17 |
| M07 | 消息截断到 5 条 | KILLED | 1（b10） |
| M08 | list 下标改成 1 起 | KILLED | 15 |
| **M09** | **空串/纯空白串变成命中（违反裁决 19）** | **SURVIVED** | **0 → F2** |
| M10 | 缺失文件用空树顶替（静默降级） | KILLED | 8 |
| M11 | 构造器无条件套用裁决 9 文件顺序键 | KILLED | 1（**仅 b05** → F1） |
| **M12** | **删掉 `scan_config_trees` 的去重** | **SURVIVED** | **0 → F2（p06 恒真）** |
| M13 | `AppConfig` 的 `extra` 放宽为 `ignore` | KILLED | 2（h04、h09） |
| M14 | `_walk` 静默跳过 `None` 节点 | KILLED | 25 |
| M15 | 每个 list 的第 0 个元素不走（漏拦一个占位值） | KILLED | 13 |
| M16 | 丢掉 root/stem 前缀（多份 weights 无法区分） | KILLED | 41 |

**14 / 16 killed**；pristine 复原后对照跑 `209 passed`（rc=0）。
任务点名的三类缺陷全部被抓到：漏拦一个占位值（M01/M02/M03/M14/M15）、排序不稳定（M04/M16）、
返回了 AppConfig（M05）。两个存活体均已实测解释，非「测试写错」而是「该口径无闸 / 该断言不可达」。

---

## 8. R6 待修清单（按严重度；R4 未做任何修复）

| # | 严重度 | 期望（契约出处） | 实际（实测） | 建议改法 | 前置授权 |
|---|---|---|---|---|---|
| 1 | 中 | 裁决 9 + 裁决 11：`ConfigPlaceholderError.paths` 一律「文件顺序优先、再路径字符串升序」 | `(['redlines.SYN-z','eval_config.SYN-m','anchor_set.SYN-a']).paths` = `('anchor_set.SYN-a','eval_config.SYN-m','redlines.SYN-z')`；源码第 202 行的 `canonical if deduped == canonical` 恒为空操作 | 首选：主控立裁决 23 后，把第 202 行改为 `self.paths = canonical`，并同步改 `tests/test_config_placeholder.py:540-541` 的期望为 `('eval_config.SYN-m','redlines.SYN-z','anchor_set.SYN-a')`；次选：立裁决 23' 认可纯字符串序，则删掉恒空的 canonical 分支并在 b05 docstring 写明口径 | **需主控裁决**（涉及改 R3 测试期望，超出裁决 21 的 1 行授权） |
| 2 | 低 | 裁决 19：空串与纯空白串不命中，且应有测试闸；裁决 14 / `[L882]`：P-10 属性不得空洞 | 变异体 M09 存活（`209 passed`）；`MISS_STRINGS` / `FILLED_TEXTS` 均不含空串；p06 的 `paths == tuple(sorted(set(paths)))` 结构性恒真（M12 存活） | 在 T05-C 组补 3 个参数化用例（`''` / `'   '` / `'\t\n '` → `is False`），并把 p06 改为可达断言（如 `len(paths) == len(_oracle_hits(tree, SYN_STEM))`）或直接删去恒真部分；**不动 `dsm/config.py`** | **需主控授权**扩 R3 写集 |
| 3 | 极低（记录） | `[L878]`：命中位置与路径一一对应 | 非字符串 YAML 键与同值 str 键相撞时两个位置折叠成一条路径（`{1:'TODO','1':'TBD'}` → `('s.1',)`） | 不建议在 T05 修（`[L877]` 六份配置不可能产生）；若 S2 fixtures 引入非字符串键，由 T06 一并处理并回写本 ADR | 无（仅登记） |
| 4 | 极低（记录） | 裁决 22 是口径补全 | `_join` docstring 未提 `[` 补口（口径实际由 `_walk` 承载） | T06 下次触碰该文件时顺手补一行注释即可，本轮不必单独开工单 | 无 |

---

## 9. 复核纪律自证

- R4 未修改 `dsm/`、`tests/`、`docs/adr/ORCH-23.md`、`docs/digest/*`、`ops/dag-state.json`、
  `ops/blockers.md` 中任何一个字节：`git diff --numstat` 与 `git diff --stat` 均为空，
  `dsm/config.py` sha256[:12] 仍为 `d8c49a1aeecc`，两个测试文件 sha 仍为 `a81fb14e687c` / `912eb7f672a2`
  （原文见 `L4-probe-io.txt` §D11 与 `L4-mutation.txt` 末尾）。
- 未执行任何 `git add` / `commit` / `push` / `amend` / `force`（H-12）；HEAD 仍 `17dd568`。
- 本轮新增文件仅 7 个：本 ADR + `ops/evidence/S1-T05/L4-{pytest,probe-api,probe-io,checklist,mutation,hygiene}.txt`。
  落库走 H-2 管线（staging `C:\Users\szf\AppData\Local\Temp\dsm_stage_S1-T05_r4\` → `rsync -a` →
  `python3 tools/normalize.py`），`tools/normalize.py --check` 结束态见 `L4-hygiene.txt`。
- 未读取 `工行参考文件/` 下任何文档全文；SDD 原文一律经 `docs/digest/S1-T05.md` 的行号摘录引用。
  未触碰邻仓 `/home/szf/dev/CampaignLab`。
- 变异实验全部在仓库外的 `/mnt/c/Users/szf/AppData/Local/Temp/dsm_ops/S1-T05-r4/` 内进行，
  实验结束该目录已删除（`scratch tree removed : True`）。
- 本文件的行数 / 字节数 / sha256[:12] / BOM / CR / TAB 于 rsync + normalize **之后**从磁盘实测，
  结果记于 `ops/evidence/S1-T05/L4-hygiene.txt` 与 R4 回报正文（文件无法自载自身最终哈希）。
