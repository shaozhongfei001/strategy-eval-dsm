# CONTEXT-BRIEF-v1.0 · 新会话接手前必读（约 5 分钟）

> 目的：让接手的智能体**不必重新发现**已知事实。前一轮 13.6 小时里，相当一部分时间花在重新摸索环境、重新推导已有 API、以及产出无人会读的留档上。本文件把这三类浪费一次性堵掉。

## 1. 一句话现状

DSM v1.1 的 S1 契约层已完成 5/7 个任务（`models.py` 1,362 行 / 47 个模型、`config.py` 480 行），S1-T06 进行中；S2~S9 未开始；**代码质量没有问题，问题是速度**——非生产物与生产代码之比达 31:1。

## 2. 环境事实（全部实测，不要重测）

| 项 | 实测值 |
|---|---|
| 仓库真身 | `/home/szf/dev/strategy-eval-dsm`（WSL Ubuntu，**ext4**） |
| 宿主 shell | Windows PowerShell **5.1**（`Set-Content -Encoding UTF8` 会产 **BOM + CRLF**） |
| Python | `/home/szf/venvs/dsm/bin/python` = **3.12.3**（venv 在 ext4；Windows 侧 `python.exe` 是商店桩，Access denied） |
| 已装 | pandas 3.1.1 / numpy 2.5.5 / pydantic **2.14.4** / typer 0.29.2 / pytest **9.2.0** / hypothesis 6.170.17 / PyYAML 6.0.4 |
| pip | 直连 PyPI **超时**，必须走 venv 内已配的 aliyun + tsinghua 镜像 |
| 性能差 | ext4 vs `/mnt/d`：建 venv **4.98s vs 56.25s**；遍历 300 文件 **0.02s vs 2.75s** → venv 与缓存**绝不上 /mnt/d** |
| 测试基线 | 全量 pytest 目前 1,487 项（含 hypothesis 展开）/ 582 个测试函数，S0 基线为 86 项 / 0.65s |
| 远端 | `git@github.com:shaozhongfei001/strategy-eval-dsm.git`，分支 `main`，SSH 免密可用；push 前用 `git ls-remote origin` 探活 |
| git 配置 | `core.autocrlf=input`、`init.defaultbranch=main`、`pull.rebase=true` |

## 3. 写文件管线（唯一可靠方式）+ 已实测的坑

三步：① 宿主 PowerShell 用 literal here-string 写到独立 staging 根 → ② `rsync -a` 进仓库 + `python3 tools/normalize.py`（去 BOM / LF 化）→ ③ 用 venv 的 python 跑 pytest。

**已付过学费的坑**：

1. `wsl.exe -d Ubuntu -- bash -lc "..."` 的双引号里**禁用** `<` `>` `$` 反引号 —— PowerShell 会先解析。实测 `wc -l < file` 直接报 `RedirectionNotSupported`；`\$?` 被打成 `True`；内嵌 `\"` 会让 bash 报 `unexpected EOF`。
2. 需要重定向、变量、算术、哈希计算时，**一律写成 `.py` 脚本文件再用 WSL python 跑**，不要在命令行里拼。
3. Python 源码里**一律用单引号**；here-string 内不得出现以 `'@` 开头的行。
4. literal here-string（`@'...'@`）内 `$`、反引号、双引号都是字面量，安全；但**嵌套** `powershell -Command "..."` 就不安全。
5. 仓库内文件必须 **UTF-8 无 BOM + LF + 无 TAB**，`tools/normalize.py` 负责，每阶段末跑一次编码校验。
6. 复杂逻辑不要嵌套多层 `bash -lc`，引号会碎。

## 4. 已建成代码的公开 API（**直接调用，不要重新实现**）

### `dsm/numeric.py`（242 行，R6 数值口径的唯一实现点）

常量 `TOL=Decimal('1E-12')` `ZERO` `ONE` `MINOR_PER_UNIT=100`；异常 `NumericError` `NonIntegerAmountError` `DivisionUndefinedError` `FloatNotAllowedError`。

函数：`D(v)`（接受 Decimal/int/str，**拒 float 与 bool**）、`from_float(v, places=12)`、`q12(v)`、`as_minor(v)->int`、`to_minor(v, minor_per_unit=100)->int`、`from_minor(m)->Decimal`（仅展示层）、`safe_div(a, b, on_zero=<必填>, zero_tol=TOL)`、`eq_exact(a,b)`、`eq_tol(a,b,tol=TOL)`、`clip(v,lo,hi)`、`weighted_sum(pairs)`、`mean(vs)`、`median(vs)`、`l1_distance(a,b)`、`sqrt(v)`、`ln(v)`、`rank_average(vs)->{index: Decimal}`、`spearman(xs,ys)->Decimal`。

### `dsm/reason_codes.py`（207 行，79 条码：28 BLOCK / 38 WARN / 13 INFO）

`Severity(INFO|WARN|BLOCK)`、`RC`（79 个成员的 str 混入 Enum）、`redline_hard(metric_id)`、`redline_soft(metric_id)`、`severity(code)`、`message(code)`、`owner_hint(code)`、`describe(code)`、`is_registered(code)`、`all_codes()`、`codes_by_severity(sev)`。动态码 `REDLINE_HARD_<METRIC>` / `REDLINE_SOFT_<METRIC>` 会回落到已注册模板。

### `dsm/models.py`（1,362 行，47 个 pydantic v2 模型，全部 `frozen=True` + `extra='forbid'`）

- 输入 8 表：`StrategyMasterRow` `MetricDictRow` `MetricFactRow` `DesignCardRow` `RedlineRow` `WeightVersionDoc` `GradeRuleRow` `AnchorSetDoc`
- provenance：`AhpSegment` `EntropySegment` `MetricWeightComparison` `CombineSegment` `AlphaBasisSegment` `WeightProvenance`
- 输出：`ScoreCardRow` `GradeLedgerRow` `SensitivityReport` `TriangulationReport` `EntropyDiagnosticRow` `AuditBundle`（+ `InputTableFingerprint` `PreflightFinding` `DowngradeAction` `PoolKey` `ScoreCardMetricCell` `ScoreCardDimCell` `SensitivitySchemeResult` `SensitivityStrategyRow` `TriangulationStrategyRow` `PoolStatRow`）
- 中间 Frame：`AttainmentRow/Frame` `NormalizedRow/Frame` `EvidenceRow/Frame` `RedlineEvalRow/Frame` `ScoreRow/Frame` `GradeRow/Frame` `PoolRow/Frame` `PoolStats` `ScoringContext`
- 数值闸门校验器：`_exact_minor_units` `_exact_direction` `_registered_reason_code` `_strict_int` `_strict_bool` `_none_or_member`

### `dsm/config.py`（480 行，S1-T06 仍在扩展语义校验与权重版本校验）

`AppConfig`、`ConfigPlaceholderError`、`is_placeholder_value(v)`、`find_placeholders(...)`、`scan_config_trees(...)`、`load_all(...)`。PLACEHOLDER 递归拦截**一次性列出全部未填路径**（V-5）。

## 5. 已付过学费的 5 个陷阱

1. **`str(RC.STABLE)` 得到 `'RC.STABLE'` 而不是 `'STABLE'`**（Python 3.12 的 str 混入 Enum 行为）。写 CSV、拼 message、算 `reproducibility_hash` **必须用 `.value``。已有测试钉死。
2. **`safe_div` 的 `on_zero` 是必填语义**：不传 → `DivisionUndefinedError`；传 `None` → 返回 `None`（对应「目标值缺失 → attainment = null，不得用均值代替」，SDD 1156 行）；传 Decimal → 返回该值。**禁止默认 0**。
3. **`spearman` 必须是 `num / sqrt(den)`**。首版写成 `sqrt(num/den)`，导致完全同序算不出 1、负相关直接抛 `sqrt of negative`，而三角验证阈值是 `mean_ρ ≥ 0.8`——公式错则整条否决权失效。已修，并有 hypothesis 属性钉死（同序恒 1、秩反向恒 −1）。
4. **`rank_average` 的输出已 `q12`**（并列取平均秩），可直接进哈希；不要自己再量化。
5. **Decimal 一律字符串构造**，禁止 `Decimal(0.1)`；float 只能经 `from_float()` 进入数值层。

## 6. SDD 行号索引（`开发设计文档-...-v1.1.md`，sha256[:12] `708679e9a83d`，2003 行）

**用 `sed -n 'A,Bp'` 直接取，不要搜索、更不要通读。**

| 行 | 内容 | 行 | 内容 |
|---|---|---|---|
| 55 | §0.3 D1–D7 七项裁决 | 1046 | §3.8.1 audit.py（manifest + 序列化五规则） |
| 71 | §0.4 设计原则 R1–R6 | 1057 | §3.8.2 reports.py（report.md 十段） |
| 82 | §0.5 术语缩写 | 1066 | §3.9 L0a/L0b 离线工具层 |
| 156 | §1.2.3 一次评分的九步流水线 | 1076 | §3.10 cli.py 八子命令与退出码 |
| 208–241 | §1.5 双轨制 / 四层作用位 / 秩反转治理 | 1095 | §3.11.1 输入 8 表总览 |
| 244–305 | §1.6 分层、依赖方向、INV-1/2/3 | 1110 | §3.11.2 各表关键字段（T1 1112 / T2 1128 / T3 1146 / T4 1158 / T5 1178 / T6 1188 / T7 1198 / T8 1210） |
| 346 | §1.8 工程目录结构 | 1216 | §3.11.3 输出 5 表 + 报告 |
| 408 | §2.1 四层作用位 | 1228 | §3.11.4 WeightProvenance 四段 |
| 421 | §2.2 方法定位矩阵 M-A~M-K（谁入分） | 1246 | §3.12 配置体系与 PLACEHOLDER 拦截 |
| 441 | §2.3.1 attainment 四公式（446 公式行） | 1261 | §3.13 数值精度与可复现（1267 口径表） |
| 462 | §2.3.2 aggregate 加权线性和 | 1276 | §3.14 **降级矩阵**（V-14 逐条断言用） |
| 478 | §2.3.3 redline 非补偿 | 1312 | §3.15.1 每期评分主流程（1348 数据流） |
| 490 | §2.3.4 grading 六步 | 1360 | §3.15.2 年度权重构造五步 |
| 501 | §2.4.1 AHP（最入分的一个） | 1387 | §3.16.1 三层测试结构（**单元 60–80 个**） |
| 524 | §2.4.2 熵权（540 平移消零） | 1399 | §3.16.2 **G-01~G-15** golden 用例 |
| 556 | §2.4.3 档 2 组合权重 8 步 | 1421 | §3.16.3 **P-1~P-15** 属性不变量 |
| 604 | §2.4.4 α 标定（622 mean_ρ，625 单调性说明） | 1441 | §3.16.4 方法学专项 T-AHP/ENT/TOP/GRA/TRI/SEN/CMB/CAL/WIF |
| 640 | §2.4.5 whatif 影响预演 | 1455 | §3.16.5 **fixtures 生成规则**（12 策略 / 4 域 / A3B3C4D2 / 7 个刻意构造 / ≥4 期） |
| 684 | §2.5 旁路诊断（692 冗余判定） | 1466 | §3.17.1 里程碑 M1~M4b |
| 698 | §2.6 三角验证（709 TOPSIS / 720 GRA / 730 判定） | 1479 | §3.17.2 **开工顺序 8 步** |
| 742 | §2.7 稳健性方案 | 1490 | §3.18 **V-1~V-20 验收判据** |
| 753 | §2.8 方法盲区对照表 | 1608 | §4.6.1 score_card 各段业务含义 |
| 769 | §2.9 明确不实现的方法 | 1628 | §4.6.2 grade_ledger 设计（recommended vs decided 分列） |
| 792 | §3.1 技术选型 | 1636 | §4.6.3 audit.json 复跑步骤 |
| 809 | §3.2 **模块清单总表（23 模块 + 守护测试）** | 1642–1680 | §4.7 五个端到端示例 E1~E5 |
| 840 | §3.3.1 numeric（845 关键函数 / 846 规则） | 1734 | §5.1 **K-01~K-20 开放参数**（须行方签认） |
| 851 | §3.3.2 reason_codes | 1761 | §5.2 RK-1~RK-15 风险 |
| 860 | §3.3.3 models（CEL-0 预留） | 1781 | §5.3 **G0~G8 冻结门禁**（G5/G7 未通过） |
| 873 | §3.3.4 config | 1817 | §5.5 证据边界与引用纪律 |
| 884 | §3.3.5 io_loaders | 1841 | §5.6 追溯矩阵 |
| 896 | §3.4.1 preflight C-01~C-10（900 C-01 / 905 C-06） | 1865 | §5.7 编号统一映射表 |
| 923 | §3.5.1 attainment（930 边界） | 1886 | §5.8 CEL（1888 **CEL-0 七字段** / 1904 二期 / 1914 契约增量） |
| 935 | §3.5.2 normalize（锚定集 / 池内归一） | 1943 | §5.9 待办与需行方确认项 |
| 947 | §3.5.3 aggregate（954 权重重归一） | | |
| 958 | §3.5.4 grading 六步 | | |
| 972 | §3.6.1 evidence 五步短路 | | |
| 984 | §3.6.2 redline | | |
| 996 | §3.6.3 pooling（1002 一级库门禁） | | |
| 1010 | §3.7.1 sensitivity | | |
| 1022 | §3.7.2 triangulation | | |
| 1033 | §3.7.3 diagnostics（VIF 用相关矩阵求逆对角元） | | |

## 7. 规模校准（写代码前先对表）

全项目生产代码 **6,000–9,000 行**；单个算法模块 **200–500 行**；全项目单元测试 **60–80 个函数** + 15 条属性；单份 digest ≤120 行；单份 ADR ≤60 行；单个证据文件 ≤200 行。
**新增测试的判据不是「还能测什么」，而是「SDD 哪个守护编号要求它」**（§3.2 的模块表已给每个模块指定了守护测试）。没有编号对应的测试不要写。

## 8. 前 13 小时的 6 条教训（不要重复）

1. 不要为「附证据」自创验证层（mutation / anti-cheat / probe）——产出 120 KB 档案，发现 0 个缺陷。
2. 不要把 pytest 全量输出落盘——单个 1.3 MB / 32,129 行文件没有任何读者。
3. 不要对声明式契约层做 RED-first——models.py 先写 602 个失败测试是负价值。
4. 不要一个任务开 9 份 ADR——裁决要点写进 commit message 即可。
5. 不要把 evidence 文本块塞进 dag-state.json——它从 6.8 KB 涨到 59 KB，每次读写都烧 token。
6. 不要在阶段中途留下脏工作树跨会话——交接前必须提交或回退。

## 9. 只读区与红线

- `/home/szf/dev/CampaignLab` **全程只读**（有无人值守 DAG）。实测快照：branch `m0-framework` / HEAD `0cccb76` / porcelain 空 / rev-list 154。**注意**：我原先给的 tag `R19-S14add` 经实测**不存在**（已登记为 B-001），校验只比对 porcelain 与 HEAD。
- `D:\ws\codex_rd\ss_campaignlab\工行参考文件\` 下 7 份文档**不得修改**，只可按行区间读取。
- 不编造任何业务数值；权重 / 门槛 / 阈值 / 目标值一律 `PLACEHOLDER`（K-01~K-20 见 SDD 1734 行）。
- G5（争议来源复核）与 G7（治理配置签认）**未通过** → 只能用合成数据跑通机制，**不得输出可用于真实资源配置的分数或等级**，此声明须进每份报告首屏。
