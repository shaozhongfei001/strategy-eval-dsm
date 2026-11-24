<!-- ADR: ORCH-23 | task: S1-T05 | 依据: docs/digest/S1-T05.md（SDD 708679e9a83d / 2003 行）| 日期: 2026-11-24 -->

# ORCH-23：`dsm/config.py` PLACEHOLDER 递归拦截契约（S1-T05）

**输入**：`docs/digest/S1-T05.md`（115 行 / 23 个行区间），核心判据 `[L873]-[L882]`（§3.3.4）、
`[L1246]-[L1259]`（§3.12）、`[L1076]-[L1091]`（§3.10 退出码全表）、`[L1276]-[L1282]`（§3.14）、
`[L1325]-[L1328]`（§3.15.1）、`[L1434]-[L1435]`（P-10 / P-11）、`[L1498]`（V-5）、`[L1580]-[L1588]`（§4.4）、
`[L1734]-[L1759]`（K-01~K-20）、`[L78]`（R4 不编造参数）、`[L102]`（PLACEHOLDER 术语）、
`[L310]`/`[L355]`/`[L816]`（config.py 位置与时机）。

**裁决原则**（ORCH §10.2-2 / §10.2-4）：原文沉默处一律取**保守超集**——宁可多拦（拒绝出分、要求填值），
不可漏拦（未签认业务数值混进出分）。凡属编造业务数值、编造 schema、编造异常名的一律不做（H-5 / H-10）。
每条沉默处均登记 blocker，写明缺什么、谁签认、完成条件。

---

## 1. 任务边界与调用时机

### 裁决 1：S1-T05 只做 PLACEHOLDER 拦截，语义校验归 S1-T06
- T05 实现：配置文件读取 → 递归扫描 → 一次性收集全部未填路径 → 抛 `ConfigPlaceholderError`（退出码 3）→ 返回 `AppConfig`。
- `[L879]` 的语义校验（Σ W_d = 1 / 维度内 Σ w_j = 1 / attainment_floor 单调 / 红线阈值引用的指标必须存在于
  metric_dict / grade_rules 的 action 非空 / anchor_set 成员必须存在于 strategy_master）与 `[L880]` 的权重版本校验
  （status 必须 FROZEN / 评价期落在生效区间 / FROZEN 缺 whatif_run_id 直接失败）属 **S1-T06**。
- `[L881]` 列了三个异常：`ConfigPlaceholderError`（退出码 3）、`ConfigSemanticError`、`WeightVersionInvalidError`。
  **T05 只定义并抛出第一个**；后两个由 T06 定义（L2 最小实现原则：不提前实现未要求的分支）。
- `load_all` 内部顺序固定为：读文件 → PLACEHOLDER 扫描（T05）→ 语义校验挂钩点（T06 填）→ 返回 `AppConfig`。
  T05 必须以注释标出挂钩点位置，使 T06 无需改函数骨架。

### 裁决 2：退出码 3 的时机（原文四处口径不一致）→ 裁定在配置加载阶段
`[L310]`（config.load_all 排在 preflight.run 之前）、`[L1325]-[L1328]`（先画 preflight 的退出码 2 出口，
再在 dsm score 分支内做 PLACEHOLDER 判定）、`[L1434]`（配置加载阶段即抛错）、`[L1582]`（启动即失败）。
**裁定**：扫描在 `load_all()` 内执行，即配置加载阶段；按 `[L310]` 的顺序它天然排在 preflight 之前；
`[L1325]-[L1328]` 的流程图不构成矛盾——`dsm score` 分支也先调 `load_all`。
因此 `[L1080]-[L1087]` 的**八个子命令只要加载配置就都会得到退出码 3**。
常量 `EXIT_CONFIG = 3` 定义在 `dsm/config.py` 作为单一事实源；S9-T01 的 `cli.py` **必须 import 它**，
不得另写数字字面量（H-7 单一事实源精神）。`[L1078]-[L1087]` 的完整退出码表（0/2/3/4/5/6/7）归 S9-T01，
T05 只负责 3。

---

## 2. `AppConfig` 形态（SDD 未给字段级 schema）

### 裁决 3：只建**文件级 6 槽**，不发明字段级 schema
事实：`AppConfig` 在 SDD 全文仅 `[L310]` 一处命中；§3.3.3 的 models 契约表 `[L860]-[L873]` 未列 AppConfig 字段；
`[L1248]-[L1257]` 只给**文件级**内容清单。→ 按 `[L877]` 的加载清单建 6 个槽，内层保持原始 YAML 树：

| 槽 | 类型 | 依据 |
|---|---|---|
| `eval_config` | `ConfigTree` | `[L877]`；`[L1250]` 内容清单；`[L1257]` weight_construction 在 eval_config 内 |
| `weights` | `dict[str, ConfigTree]`（键 = 文件 stem） | `[L877]` weights_*.yaml（通配，可多份）；`[L1252]` weights_WV-*.yaml |
| `redlines` | `ConfigTree` | `[L877]`；`[L1253]` |
| `grade_rules` | `ConfigTree` | `[L877]`；`[L1254]` |
| `anchor_set` | `ConfigTree` | `[L877]`；`[L1255]` |
| `ahp_matrices` | `ConfigTree` | `[L877]`；`[L1256]` |

- `ConfigTree = dict[str, Any]`：YAML `safe_load` 的原始树（str / int / float / bool / None / dict / list）。
- `AppConfig` 一律 `frozen=True` + `extra='forbid'`（与 models 层同纪律，V-5 `[L871]` 精神）。
- **禁止**为 `[L1250]-[L1257]` 的内容项建 pydantic 字段（字段名、嵌套层级、类型 SDD 均未给，建了就是编造）。
  这些逐字键名（`attainment_floor` / `evidence_class_min` / `promotion_streak` / `alpha_floor` / `drift_budget` /
  `boundary_budget` / `boundary_epsilon` / `min_dim_weight` / `max_shift_from_ahp` / `alpha_grid` /
  `stable_max` / `review_max` / `divergence_threshold` / `loo_sampling_threshold` / `triangulation.enabled` /
  `cel.enabled` / `forced_grade` / `whatif_run_id` / `status` / `effective_from` / `effective_to`）
  只出现在**测试 fixture** 与文档中，供 T06 按路径取值（ORCH-16 逐字保真）。
- 通配口径：glob 用 `weights_*.yaml`（`[L877]` 写法，是 `[L1252]` weights_WV-*.yaml 的超集）。

### 裁决 4：数值入口不在 T05 转换（H-4 挂钩点转 T06）
原始树里的 int / float 标量**原样保留**，T05 不做任何数值转换、不做任何数值判定。
下游消费时必须经 `numeric.D`（Decimal 字符串构造）/ `numeric.as_minor` 闸门，float 只能经 `numeric.from_float()`
进入计算层（H-4）。**T06 落地该转换并加断言**，登记 B-022。

---

## 3. 命中判定（原文只写「凡值为字符串 PLACEHOLDER、null（且字段声明为必填）、或形如 TODO / TBD / XXX」）

### 裁决 5：字符串命中 = strip 后大小写不敏感的整值相等或前缀命中（保守超集）
对字符串值 `v`，令 `s = v.strip().upper()`，命中当且仅当：
- (a) `s` 属于 {`PLACEHOLDER`, `TODO`, `TBD`, `XXX`}；**或**
- (b) `s` 以 `PLACEHOLDER` 开头（覆盖 `PLACEHOLDER_K-01`、`PLACEHOLDER: 待行方签认` 等变体——
  `[L1734]-[L1759]` 的 K-01~K-20 清单惯例必然产生带后缀的占位写法）；**或**
- (c) `s` 以 `TODO` / `TBD` / `XXX` 开头（`[L878]`「形如」二字的保守读法）。

理由：`[L102]`「存在即拒绝出分」+ `[L78]` R4 不编造参数 → 漏拦的代价是未签认业务数值混进出分（不可接受），
误拦的代价只是要求填值（可接受）。原文对大小写、整值/子串、变体**全部沉默**，登记 B-023。
**不做子串命中**（如 `abcTODOdef` 不命中）：子串命中会误伤正常说明文字（rationale 等自由文本字段），
且原文「凡值为字符串 PLACEHOLDER」的主口径是整值；前缀命中已覆盖 K 清单变体这一唯一有据可查的写法。
非字符串标量（int / float / bool）**不命中**（它们是已填值，业务合理性归 T06 语义校验）。
dict 的**键不扫描**（键名不是「值」；键为占位属 schema 错误，归 T06）。

### 裁决 6：`None` 一律命中（必填性来源 SDD 未给 → 取保守超集）
`[L878]` 要求 null「且字段声明为必填」才命中，但**必填性的判定来源原文未给**（无 AppConfig 字段级 schema，
`[L860]-[L873]` 契约表也没有）。裁定：**配置树中任何 `None` 值一律命中**。
理由：①无 schema 即无法判定必填性，放行 `None` 等于放行「未签认的空值」，与 `[L102]`「存在即拒绝出分」冲突；
②表达「可选且未设」的正确方式是**省略键**（YAML 省略键不产生 `None`），写 `null` 视为未填；
③方向保守。若行方确认某些键允许显式 `null`，须先扩本 ADR 附录白名单再实现（属破坏性放宽），登记 B-024。
推论：文件内容为空或只有注释（`safe_load` 返回 `None`）→ 顶层命中，路径就是 file stem 本身（如 `eval_config`）。

---

## 4. 递归范围、路径表示法与输出纪律

### 裁决 7：递归只覆盖 YAML 配置树，**不含 csv**
`[L877]` 的加载清单是 6 个 yaml 模式，**不含 metric_dict.csv**；`[L1251]` 把 metric_dict.csv 列在「配置体系」表内
（签认方 = 指标负责人 + 业务部门）。裁定：体系归属 不等于 加载归属，T05 的递归扫描只覆盖 YAML 树。
理由：①csv 是表形文件，其「字段路径」表示法（行号 + 列名）SDD 未给，发明即编造（H-10）；
②metric_dict.csv 的「签认状态」是**数据列**，拦截点属 S3 preflight 与输入表指纹链（`InputTableFingerprint`）；
③`[L879]`「红线阈值引用的指标必须存在于 metric_dict」这条交叉校验本身就在 T06/S3，不会因 config.py 不扫 csv 而漏。
登记 B-026（csv「签认状态」列的判据与拦截点待 S3 取 §3.4 原文确认）。

### 裁决 8：路径表示法 = file stem + 点号路径，列表下标 `[i]`（0 起）
原文只出现「未填字段路径」四字（`[L878]` / `[L1282]` / `[L1328]` / `[L1582]`），未定义写法、未给示例输出。裁定：
- 前缀 = 文件 stem（不带扩展名），保证跨文件唯一（`weights_*.yaml` 可能多份）；
- 嵌套 dict 用 `.` 连接；list 元素用 `键[i]`（0 起下标）；
- 顶层标量 = stem + `.` + 键名；整棵树为 `None` 时 = 仅 stem。

示例（仅示意格式，不含任何业务数值）：
```
eval_config.weight_construction.alpha_floor
eval_config.triangulation.thresholds[2]
weights_WV-PLACEHOLDER.dimensions[0].metrics[3].weight
redlines
grade_rules.levels[1].action
```

### 裁决 9：一次性列出全部——排序、去重、不截断
- **去重**：同一路径只出现一次。
- **排序**：先按文件在 `[L1250]-[L1257]` 清单中的固定顺序
  （eval_config → weights → redlines → grade_rules → anchor_set → ahp_matrices；weights 内按 stem 升序），
  再按路径字符串升序（Python 默认 str 排序）。排序必须确定性可复现（V-3 reproducibility 精神）。
- **不截断、不限量**：`[L878]`「不允许只报第一个」+ `[L1259]`「一次性列出全部未填字段路径」。
- 消息格式（SDD 未给，本 ADR 定死，供 V-5 与 P-10 断言）：
  首行 `配置含 N 个未签认占位值（退出码 3）`；随后每行 `  - <path>`；
  若有缺失文件，追加空行 + `缺失必需配置文件 M 份：` + 每行 `  - <stem>`。

### 裁决 10：必需文件缺失也走同一次性出口（V-14 无静默降级）
`[L877]` 要求加载 6 类文件。裁定：必需文件 = `eval_config.yaml` / `redlines.yaml` / `grade_rules.yaml` /
`anchor_set.yaml` / `ahp_matrices.yaml` 五份 + `weights_*.yaml` **至少一份**；缺失时：
- **不得**返回空树假装成功（V-14 禁静默降级；`[L1091]` 退出码非 0 时不得产出 score_card）；
- 与占位路径**一次性**一起报出（同一个异常、同一次出口，符合 `[L878]`「不允许只报第一个」）；
- 不新造第四个异常名（`[L881]` 只给三个，H-10）：复用 `ConfigPlaceholderError`，
  另设 `missing_files` 属性承载缺失清单（`[L1080]` 退出码 3 = 配置错，缺失属配置错，退出码口径正确）。
消息格式与异常名是否应拆分，SDD 未给 → 登记 B-025。

---

## 5. 公开契约（T05 必须逐字实现，R3 按此写 RED，R4 按此判定）

### 裁决 11：函数与异常签名
```
EXIT_CONFIG = 3                                   # [L881]/[L1080] 单一事实源，cli.py 必须 import

REQUIRED_CONFIG_STEMS: tuple[str, ...]            # 裁决 10 的五个固定 stem，按 [L1250]-[L1257] 顺序
WEIGHTS_GLOB = 'weights_*.yaml'                   # [L877]
PLACEHOLDER_TOKENS: tuple[str, ...]               # ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')  [L878]
PLACEHOLDER_PREFIXES: tuple[str, ...]             # 同上四词，用于裁决 5 的 (b)(c) 前缀命中

ConfigTree = dict[str, Any]                       # 裁决 3

class AppConfig(BaseModel):                       # frozen=True, extra='forbid'，6 槽见裁决 3
    ...

class ConfigPlaceholderError(Exception):
    def __init__(self, paths, missing_files=()):  # 两个参数都接受可迭代，内部转 tuple
        ...
    paths: tuple[str, ...]                        # 已按裁决 9 排序去重
    missing_files: tuple[str, ...]                # 已按裁决 10 排序去重
    exit_code: int                                # 等于 EXIT_CONFIG（实例属性，便于 cli 直接取）

def is_placeholder_value(value) -> bool           # 裁决 5 + 裁决 6，纯函数
def find_placeholders(tree, *, root='') -> tuple[str, ...]
                                                  # 递归单棵树，root 为路径前缀；纯函数，不排序（按遍历序）
def scan_config_trees(trees) -> tuple[str, ...]   # 多棵树（含 weights 的 stem 到 tree 映射），
                                                  # 按裁决 9 排序去重后返回；纯函数
def load_all(config_dir) -> AppConfig             # 唯一 I/O 入口；抛 ConfigPlaceholderError
```
- `is_placeholder_value` / `find_placeholders` / `scan_config_trees` **必须是纯函数**（H-8）：
  不读写全局状态、不 I/O、不取当前时间；输入相同则输出逐字节相同。
- `load_all(config_dir)` 是 T05 唯一 I/O 入口；**签名只有 `config_dir` 一个参数**（最小实现）。
  `[L1089]` 的 `--period` / `--run-at` / `--seed` 注入由 **T06** 以关键字参数追加
  （`*, period=None, run_at=None`），追加可选 kwarg 不是破坏性变更。
  T05 内部**不得**出现 `datetime.now` / `time.time` / `date.today` 等墙钟调用（orch_verify 第 6 段会扫）。
- `config_dir` 接受 `str | Path`；内部用 `pathlib.Path`。
- YAML 读取用 `yaml.safe_load`（PyYAML 6.0.4，已在 requirements.txt）。

### 裁决 12：分层与写集（H-9）
- `dsm/config.py` 属 **L1**（`[L355]` / `[L816]`）。INV-1：不得 import L0a/L0b
  （`weights_ahp` / `weights_combine` / `fixtures_gen` / `weights_calibrate` / `whatif`）。
- T05 的 import 只允许：标准库（`pathlib` / `typing` / `dataclasses` 如需）、`yaml`、`pydantic`。
  **不得** import `dsm.models` / `dsm.numeric` / `dsm.reason_codes`（T05 用不到；T06 需要时再加，属授权扩展）。
- 写集：新建 `dsm/config.py`、`tests/test_config_placeholder.py`（单测）、`tests/test_config_properties.py`
  （P-10 属性测试，风格对齐既有 `tests/test_numeric_properties.py`）。
  **不得**改 `dsm/models.py` / `dsm/numeric.py` / `dsm/reason_codes.py` / 任何既有测试。
  （若 `dsm/__init__.py` 需导出 config，允许**追加**一行，不得改既有行。）

### 裁决 13：测试用配置一律合成，不占仓库 `config/` 目录（H-14）
- 仓库 `config/` 目前为空，且 `[L1250]-[L1257]` 的真实配置值**全部待行方签认**（一律 PLACEHOLDER，H-5）。
- T05 的测试配置一律合成：直接在测试里构造 dict 树，或用 pytest `tmp_path` 写临时 yaml。
- **禁止**在仓库 `config/` 下新增任何文件（那是 S2 fixtures 的写集）。
- 属性测试的随机性必须可复现（H-14 / `--seed` 纪律）：沿用 `tests/test_numeric_properties.py` 的既有做法
  （hypothesis profile / derandomize / 固定 seed），同 seed 逐字节相等。

### 裁决 14：P-10 在 T05 层的可判定形式（`[L882]` / `[L1434]`）
原文：「任意含 PLACEHOLDER 的配置都不得产出分数」。评分链在 S4 才存在，故 T05 层判定为：
对 hypothesis 生成的任意配置树，**若树中含至少一个命中值（裁决 5 / 裁决 6 口径），则**
① `find_placeholders` 返回非空；② `load_all` 抛 `ConfigPlaceholderError`；
③ **不返回任何 `AppConfig` 实例**（即下游无从出分）；④ `paths` 覆盖树中全部命中位置（数量相等，不只第一个）。
端到端形式（cli 退出码 3 且输出目录无 score_card，`[L1091]`）由 **S9-T03** 汇总补齐。

### 裁决 15：档位口径澄清（关闭 R1 提出的事实性出入）
R1 报「任务书写 C1 而 ORCH `[L180]` 写 C3/max」。澄清：**不冲突**。
C1/flash 指的是**L0 digest 这一步**（与 S1-T01 的 digest 步骤同档，ORCH §5.2 S1-T01 行即 C1/flash）；
S1-T05 **任务本体**按 dag-state.json 预置与 ORCH `[L180]` 一致 = **C3 / complexity_score 5 / qwen3.8-max / 预算 90k**，
角色轮次 R3→R2→R4。禁止把 C3 派给 flash「先试试」（§3.3）。

---

### 裁决 16：`scan_config_trees` 的参数形态（关闭 R3 疑点 1）
签名钉为 `scan_config_trees(trees: Mapping[str, ConfigTree]) -> tuple[str, ...]`，键 = 文件 stem
（`weights_*.yaml` 的每一份各占一个键）。输出顺序由**裁决 9 的文件顺序**决定
（eval_config → weights（stem 升序）→ redlines → grade_rules → anchor_set → ahp_matrices），
**与入参 dict 的插入顺序无关**（R3 的 f05 已就此设闸）。

### 裁决 17：`find_placeholders` 的 root 语义与路径拼接（关闭 R3 疑点 2）
- 拼接口径唯一：`join(root, rel)` = `root + '.' + rel`（root 与 rel 均非空）；= `root`（rel 为空）；= `rel`（root 为空）。
- 整棵树为 `None` 时（裁决 6 推论）相对路径为**空串**：`find_placeholders(None)` 返回 `('',)`，
  `find_placeholders(None, root='redlines')` 返回 `('redlines',)`（不是 `'redlines.'`）。
- 不变式（R2 必须实现、R4 必须核）：对任意树 `t` 与任意 root `r`，
  `find_placeholders(t, root=r)` 等于 `tuple(join(r, p) for p in find_placeholders(t))`。
- `root=''` 时路径**不得**以 `.` 开头（R3 的 e09 已就此设闸）。

### 裁决 18：`missing_files` 的顺序与 weights 缺口的字面拼写（关闭 R3 疑点 3、4）
- 顺序 = 裁决 9 的文件顺序：`REQUIRED_CONFIG_STEMS` 按 `[L1250]-[L1257]` 排列，weights 缺口排在其对应位置（第 2 位）；
  去重、确定性可复现。R3 的测试只钉内容 / 去重 / 确定性（不钉顺序），本裁决是**更强的实现要求**，与测试不冲突。
- weights 一份都没有时，`missing_files` 中该项的字面拼写钉为 **`weights_*`**（= `WEIGHTS_GLOB` 去掉 `.yaml` 后缀），
  满足 R3 的 g04「非空且含 weights」，且一眼可辨是通配缺口而非某个具体文件。

### 裁决 19：空串与纯空白串**不命中**（关闭 R3 疑点 5）
裁决 5 的 iff 是封闭的：令 `s = v.strip().upper()`，既不属四个整值、也不以四个前缀开头 → 不命中。
`''` 与 `'   '` 的 `s` 为空串，两个分支都不满足，故**不命中**。
理由：①`[L878]` 只列了三种命中形态，空串不在其中，把它加进去属**加严**而非保守超集，会误伤
`decision_note: ''` 这类有意的空文本；②YAML 里「键在但没填值」产出的是 `None` 而非 `''`，
已被裁决 6 全量拦下，不存在漏拦未签认值的通道；③显式写 `''` 是有意为之的表达。
口径并入 **B-023** 一并送行方签认（若行方要求空串也算未填，改动面 = 命中表加一个空串分支 + 测试参数化）。
R2 必须在 `is_placeholder_value` 的注释里写明本裁决，避免下游误读。

### 裁决 20：R3 五点疑议的处置汇总
| R3 疑点 | 处置 | 落点 |
|---|---|---|
| 1 `scan_config_trees` 参数类型未定 | 钉 `Mapping[str, ConfigTree]`，键 = stem，顺序按裁决 9 而非插入序 | 裁决 16 |
| 2 `find_placeholders` 空 root 的路径写法未定 | 钉 `join` 三分支口径 + None 树相对路径为空串 + 前缀不变式 | 裁决 17 |
| 3 `missing_files` 排序口径未定 | 钉裁决 9 的文件顺序（比测试更强，不冲突） | 裁决 18 |
| 4 weights 全缺时的字面拼写未定 | 钉 `weights_*` | 裁决 18 |
| 5 空串 / 纯空白串是否命中 | 钉**不命中**，口径并入 B-023 送签认 | 裁决 19 |

---

### 裁决 21：`test_t05_i09[is_placeholder_value]` 属 R3 测试缺陷，按「补 fixture 键」修复（非放宽断言）
**事实**（主控独立复核，非听信实现者转述）：`tests/test_config_placeholder.py:1233`。
参数化分支 `name == 'is_placeholder_value'` 只构造 `argument = {'SYN-a': ['PLACEHOLDER', None]}`，
而三分支共用的 else 调用序列是 `fn(argument['SYN-a'])` 后接 `fn(argument['SYN-c'])`
→ 在**任何断言执行之前**抛 `KeyError: 'SYN-c'`。
主控实测：`pytest tests/test_config_placeholder.py -k i09` → `1 failed, 2 passed, 189 deselected`，
报错为 `tests/test_config_placeholder.py:1233: KeyError`；被测函数从未收到第二个参数，与实现无关。

**判定**：这是**测试自身缺陷**（fixture 与调用序列不匹配），既不是 golden 期望值问题（H-11 不适用），
也不是实现问题——任何合法实现都不可能通过该用例。

**处置（最小、不削弱、可复核）**：在 `is_placeholder_value` 分支的 fixture 里补上缺失的键：
`argument = {'SYN-a': ['PLACEHOLDER', None], 'SYN-c': 'TODO'}`。
- 断言 `argument == before` **一字不改**；
- else 调用序列 **一字不改**；
- 修复后该用例才真正执行原作者意图：对同一纯函数分别以「容器」与「字符串命中值」两种形态各调用一次，
  再断言入参未被变更——覆盖面**不降反升**（修复前第二次调用永远不可能发生）。
- **不得**改成 `for value in argument.values(): fn(value)` 之类遍历式写法：那会使 `is_placeholder_value`
  只被调用一次，属**削弱**，R4 一旦发现的按质量事故处理。

**归属与记账**：测试文件是 R3 的写集 → 由 R6（沿用原 R3 agent 实例）执行本次 1 行修复；
实现者 R2 与主控均不得触碰测试文件。本轮计入 `counters.rework_rounds`（+1），
**不计** `quality_incidents`（无作弊、无放宽断言、无删测试、无 skip/xfail、无 golden 改动）。

---

### 裁决 22：`join` 补口——相对路径以 `[` 开头时不插 `.`（树根本身是 list 的情形）
裁决 17 的三分支 `join(root, rel)` 在「树根本身是 list」时留下歧义：此时相对路径形如 `[0]` / `[1][2]`，
按字面 `root + '.' + rel` 会产出 `stem.[0]`，与裁决 8 的 `键[i]` 表示法冲突。
**裁定**：`rel` 以 `[` 开头时 `join(root, rel) = root + rel`（不插点）；`rel` 非空且不以 `[` 开头时仍为
`root + '.' + rel`；`rel` 为空时仍为 `root`；`root` 为空时仍为 `rel`。
即 `find_placeholders(['TODO', None], root='stem')` 返回 `('stem[0]', 'stem[1]')`。
**实测依据**（主控 probe，非听信实现者）：20 组（5 种树 × 4 种 root）前缀不变式检验中 17 组按裁决 17 原式通过，
3 组差异**全部**落在「树根为 list 且 root 非空」这一情形，实现给出 `stem[0]`；按本条修正口径后 20/20 通过。
本条为口径补全，**不改实现、不改测试**（既有测试未就该情形设闸，e02/e07/e11 覆盖的是 dict 之下的 list）。

附（主控确认，不属缺口）：`dsm/config.py` 未定义 `__all__`——裁决 11 未要求，测试 i11 以下划线前缀区分公开/私有，
实测 12 个公开名齐备、无多余公开名（私有辅助 11 个均以下划线开头）。

---

### 裁决 23：`ConfigPlaceholderError.paths` 只有一种排序——裁决 9 的文件序键（关闭 R4 F1）

**R4 实测偏差**（`ops/evidence/S1-T05/L4-probe-api.txt` §D5、`L4-mutation.txt` M11）：
`ConfigPlaceholderError(['redlines.SYN-z', 'eval_config.SYN-m', 'anchor_set.SYN-a']).paths`
实测 = `('anchor_set.SYN-a', 'eval_config.SYN-m', 'redlines.SYN-z')`（纯字符串序），
而裁决 9 + 裁决 11 要求 = `('eval_config.SYN-m', 'redlines.SYN-z', 'anchor_set.SYN-a')`
（eval_config 第 1 → redlines 第 3 → anchor_set 第 5，`[L1250]-[L1257]`）。

**根因两处，均判为缺陷**：
1. 实现：`dsm/config.py` 第 202 行 `canonical if deduped == canonical else tuple(sorted(deduped))`
   是一条双分支——输入恰为规范序时才用 `_path_key`，否则退回纯字符串序。因 `deduped == canonical`
   时二者相同，该分支等价于「构造器永不主动套用裁决 9 的键」，裁决 11 的
   「已按裁决 9 排序去重」在构造器侧落空。docstring 中「ruling 9 demands "sorted" but names
   no key」的辩解不成立：裁决 9 明写了键（文件固定序 → 路径字符串升序），`_path_key` 已实现该键
   并在 `scan_config_trees` 侧生效。
2. 测试：`tests/test_config_placeholder.py::test_t05_b05_error_paths_are_sorted` 的期望值取纯字符串序，
   与裁决 9 冲突。按 H-11「期望值不得跟随实现」，b05 属 R3 测试缺陷，期望值必须回到裁决 9 原文口径，
   **不得**以现实现输出为准。

**裁定**：
- `dsm/config.py` 构造器改为无条件 `self.paths = canonical`（恒用 `_path_key`），删除双分支；
  `missing_files` 一支不动（已恒用 `_missing_key`，符合裁决 18）。
- docstring 中描述双分支的那一段同步改写为单一口径（只留「一律按裁决 9 的 `_path_key` 排序去重」），
  不得保留「plain string sort is the only order independent reading」一类辩解文字。
- `test_t05_b05_error_paths_are_sorted` 期望值改为
  `('eval_config.SYN-m', 'redlines.SYN-z', 'anchor_set.SYN-a')`，docstring 注明依据为裁决 9 / 裁决 23。
- 允许**新增**（不得削弱既有用例断言强度）：① 构造器输入为逆文件序时输出仍为文件序；
  ② 未知 stem 经 `_file_rank` 排最后、其内部仍按路径升序。
- 连带影响核对（R6 必须实测回报）：`b04` / `b06` / `b07` / `f02` / `g11` 及所有经 `load_all`
  抛错的用例，其输入本已为规范序，期望值不变；若实测有变，一律以裁决 9 重算期望值，禁止反向迁就实现。
- 定性：**契约澄清**（裁决 9 早有明文），不计质量事故——R4 的 H-11 反作弊审计判定干净
  （偏差在 docstring 公开披露、未改 golden、未加 skip/xfail、未删测试）；计返工 +1（T05 第 2 轮 R6）。
- ORCH-23.md 因裁决 23 / 24 追加而变更指纹，属主控在 L6 落库前的正常修订；R4 复核 ADR 记录的
  `cb7d9222fa27` 为追加前指纹，落库指纹以 L6 实测为准。

### 裁决 24：裁决 19 与去重必须有可证伪的测试闸（关闭 R4 F2 / M09 / M12）

**R4 实测**（`L4-mutation.txt`）：16 个变异体 14 killed，M09（空串变为命中，违反裁决 19）与
M12（删 `scan_config_trees` 去重）存活、0 杀手。存活原因均为**测试覆盖空洞**，非实现缺陷
（实现侧 `''` / `'   '` / 制表换行空白串实测均返回 False；去重逻辑存在且正确）。

**裁定（本裁决下只扩测试写集，`dsm/config.py` 不得因本裁决改动）**：
1. 裁决 19 正面闸：T05-C 组补 `''`、`'   '`、`'\t\n '` 三例，断言 `is_placeholder_value(...) is False`；
   并把这三个值加入属性测试的「已填值」叶子字母表（`FILLED_TEXTS` 或等价策略），
   使 P-10 在 hypothesis 侧同样能证伪 M09。
2. 去重可达闸：纯 str 键下同一棵树不可能产出重复路径，M12 在该空间内是等价变异体；
   但 YAML 允许同层并存 int 键 `1` 与 str 键 `'1'`，二者经 `_walk` 的 str 化后折叠为同一路径。
   裁定**去重按裁决 9 生效**（同一路径只出现一次，消息首行 N 为去重后计数），并新增用例
   `scan_config_trees({'s': {1: 'TODO', '1': 'TBD'}}) == ('s.1',)`，该用例即 M12 的杀手。
3. `tests/test_config_properties.py` p06 中 `paths == tuple(sorted(set(paths)))` 属结构性恒真断言，
   裁定**不得删除**（仍是排序/去重的必要不变式），但必须**补一条可达断言**：属性策略中允许生成
   上述 int/str 同层碰撞键，断言 `len(paths) == len(set(paths))` 且碰撞层只贡献一条路径。
   禁止以「删掉恒真部分」代替「补可达断言」。
4. R4 观察项 O1（非字符串键碰撞）由第 2 项定性为**契约内行为**，不再挂待办；`[L877]` 六份生产配置
   的键均为字符串，实际不可达，仅作合成用例存在。
5. R4 极低项 4（`_join` docstring 未提裁决 22 的 `[` 补口）**顺延至 S1-T06**：T06 首次触碰
   `dsm/config.py` 时顺手补注释，本轮 R6 不做，以收窄写集。

---

## 6. 本 ADR 新登记的 blocker（随 S1-T05 落库写入 ops/blockers.md）

| 编号 | 缺什么 | 谁签认 | 完成条件 | 阻塞? |
|---|---|---|---|---|
| B-022 | config 层数值入口口径：YAML 的 int/float 标量如何经 numeric 闸门进入计算层，SDD 未给（`[L1250]-[L1257]` 只给内容清单，`[L878]` 只管占位值） | Orchestrator + S1-T06 实现者 | T06 语义校验时对取出的数值强制走 `numeric.D` / `numeric.as_minor`，float 只能经 `numeric.from_float()`（H-4），并加断言 | 否 |
| B-023 | 占位值命中口径：大小写是否敏感、整值相等还是子串命中、`PLACEHOLDER_xxx` 变体是否算，原文全沉默（`[L878]` 只有「凡值为字符串 PLACEHOLDER」「形如 TODO / TBD / XXX」） | 行方（评价管理部门）+ Orchestrator | 本 ADR 裁决 5 按保守超集实现（strip + 大小写不敏感 + 整值或前缀）；行方签认后若要求严格整值相等，改动面 = `PLACEHOLDER_PREFIXES` 常量置空 + 测试参数化 | 否 |
| B-024 | `null` 的必填性判定来源：`[L878]` 要求「null 且字段声明为必填」，但 AppConfig 字段级 schema SDD 未给（全文 AppConfig 仅 `[L310]` 命中） | 行方（评价管理委员会）+ Orchestrator | 本 ADR 裁决 6 按保守超集把一切 `None` 视为未填；行方若确认某些键允许显式 `null`，须先在本 ADR 附录加白名单（属破坏性放宽，须再立 ADR） | 否 |
| B-025 | 必需配置文件缺失时是否应有独立异常名与消息格式：`[L881]` 只给三个异常名，`[L1080]` 只给退出码 3 = 配置错 | Orchestrator + S9-T01 cli 实现者 | 本 ADR 裁决 10 复用 `ConfigPlaceholderError` + `missing_files` 属性；S9-T01 定 cli 侧消息呈现，如需拆分异常须再立 ADR | 否 |
| B-026 | `metric_dict.csv` 的「签认状态」列判据与拦截点：`[L1251]` 把它列入配置体系，`[L877]` 的加载清单不含它，`[L878]` 只说「配置树」 | Orchestrator + S3 preflight 实现者 | 本 ADR 裁决 7 定为不入 config.py 扫描；S3 取 §3.4 preflight 原文后确认 csv 侧「签认状态」的判据与退出码 | 否 |
| B-027 | 「单价」在 config 层无键名：`[L78]` / `[L1259]` / `[L1806]` 点名单价一律 PLACEHOLDER，但 `[L1250]-[L1257]` 的内容清单未列单价字段（仅 §5.8 CEL-4 `[L1911]` / `[L1921]` 相关） | Orchestrator + S7 方法层实现者 | S7 取 §5.8 CEL-4 原文后定单价的载体（config 键 or DesignCardRow 字段），在此之前**不得**发明键名（H-5 / H-10） | 否 |

---

## 7. 验收清单（R3 写 RED / R4 判定，逐条可判定）

| 编号 | 判据 | 依据 |
|---|---|---|
| T05-A | `EXIT_CONFIG` 等于 3，且 `ConfigPlaceholderError(...).exit_code` 等于 3 | `[L881]` `[L1080]` |
| T05-B | 单个含 N 处占位的树 → `paths` 长度 == N，**全部**列出（不只第一个），已排序去重 | `[L878]` `[L1259]` V-5 `[L1498]` |
| T05-C | 命中口径：`PLACEHOLDER` / `placeholder` / 带空格的 `PLACEHOLDER` / `TODO` / `TBD` / `XXX` / `PLACEHOLDER_K-01` 全命中；`OK` / `ACTIVE` / 正常文本 / int / float / bool 不命中 | 裁决 5 |
| T05-D | `None` 一律命中；空 yaml 文件（树为 None）命中且路径 == stem | 裁决 6 |
| T05-E | 路径格式：嵌套 dict 点号、list `[i]` 0 起、前缀为 file stem；weights 多份时 stem 各异且互不混淆 | 裁决 8 |
| T05-F | 排序确定性：同一输入两次调用 `paths` 逐字节相等；文件顺序为 eval_config → weights → redlines → grade_rules → anchor_set → ahp_matrices | 裁决 9 |
| T05-G | 必需文件缺失：与占位路径一次性一起报出，`missing_files` 正确，不返回 AppConfig，不静默成功 | 裁决 10 / V-14 |
| T05-H | `AppConfig` 6 槽、`frozen=True`、`extra='forbid'`（未声明槽必报错）；无字段级 schema 被发明 | 裁决 3 / V-5 `[L871]` |
| T05-I | 纯函数：`is_placeholder_value` / `find_placeholders` / `scan_config_trees` 无 I/O、无全局状态、无墙钟；`load_all` 是唯一 I/O 入口 | H-8 |
| T05-J | P-10 属性测试：任意含占位的合成树必拦、必不产出 AppConfig、`paths` 覆盖全部命中位置；同 seed 可复现 | `[L882]` `[L1434]` 裁决 14 |
| T05-K | 分层：`dsm/config.py` 不 import L0a/L0b，T05 阶段不 import dsm.models / numeric / reason_codes | H-9 INV-1 / 裁决 12 |
| T05-L | H-5：`dsm/config.py` 与两个测试文件中**不得出现任何业务数值**（权重/门槛/阈值/目标值/单价/周期/样本量/K-01~K-20 的具体值）；测试 fixture 的这些位置一律写 `PLACEHOLDER` | `[L78]` `[L1259]` |
| T05-M | 全量 pytest 0 failed / 0 error / 无新增 skip；既有 1268 项一条不坏 | ORCH §6 S1 门禁 |

---

## 8. 依据行号汇总

SDD `[L78]` `[L102]` `[L198]` `[L310]` `[L355]` `[L816]` `[L860]-[L873]` `[L873]-[L882]` `[L1076]-[L1091]`
`[L1246]-[L1259]` `[L1276]-[L1282]` `[L1325]-[L1328]` `[L1434]-[L1435]` `[L1470]` `[L1498]` `[L1580]-[L1588]`
`[L1734]-[L1759]` `[L1766]` `[L1794]` `[L1806]` `[L1911]` `[L1921]` `[L1947]-[L1951]`
仓内：`docs/digest/S1-T05.md`（含「事实记录（原文沉默处）」8 条）、ORCH-16（SDD 逐字名优先）、
ORCH-20 / ORCH-21（可空性判例）、ORCH-22 裁决 31（不预建未要求的聚合模型）；
ORCH §2 H-4 / H-5 / H-7 / H-8 / H-9 / H-10 / H-11 / H-14；§3.3 升降级；§5.2 S1-T05 行；§10.2-2、§10.2-4。
