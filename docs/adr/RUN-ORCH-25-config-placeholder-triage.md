# RUN-ORCH-25 · tests/test_config_placeholder.py triage 裁决

- **时刻**：T+3.60h（wave-1 收口、wave-2 齐发之后）
- **裁决人**：主控（Orchestrator）
- **触发**：B4（commit `3fef4da`）上报缺口 G1/G2/G3。B4 把 `dsm/config.py` 语义校验 + 权重版本校验落地后，211 条故意 RED 全绿，全量 pytest 由 213 failed 降至 **10 failed**；其中 8 条落在 `tests/test_config_placeholder.py`——该文件不在 B4 写集内，故未被处理。

## 一、根因认定（属测试侧过时，非实现缺陷）

1. **G1（7 条：`d09` 后半 / `g12` / `h05` / `h10` / `h11` / `k05[False]` / `k05[True]`）**
   该文件私有 fixture `_clean_grade_rules()`（约 line 319）只造 **L1/L2 两级**，且用**单数 `action` 键**。而 ORCH-24 裁决与 `dsm/config.py` 已落地的语义门要求 **四级 L1~L4 + floor 单调 L1>L2>L3>L4 + 每级非空 `actions`（复数键）**。因此这 7 条的「干净树」在语义门下被判 STRUCTURE，属 fixture 过时。
2. **G2（1 条：`i05`）**
   该测试断言 `load_all` 只有 `config_dir` 一个参数，与 ORCH-24 line 320 / 裁决 19 钉死的签名 `load_all(config_dir, *, period=None, run_at=None)` 直接互斥；并被 T06 自身的 `test_t06_h19_load_all_without_period_still_blocks_a_frozen_gap`（无 period 也必须拦 FROZEN 缺口）反证。

## 二、裁决

**生产语义优先，测试侧跟随。**

- `_clean_grade_rules()` 改为四级 L1~L4、floor 单调、每级带非空 `actions`，**照抄 `tests/test_config_properties.py::_t06_grade_rules` 的既有合成树构造**；不得自创数值、不得引入任何新治理值（K-01~K-20 一律 PLACEHOLDER）。
- `i05` 的参数断言改为 `['config_dir', 'period', 'run_at']`。
- **断言一条不减**：占位值必须被拦、退出码、reason_code 等业务断言不得弱化或删除。若某条无法在不弱化断言的前提下变绿 → 保持 RED 并上报 BLOCKING。
- **`test_t05_m03` 不在本裁决范围**：其根因是 `dsm/weights_combine.py`（L0a）`from dsm.weights_ahp import ...`（L0b）是否违反 INV-1 的架构争议，已交 E5 按 `docs/digest/M00-architecture.md` 原文判定，主控将另出 **ORCH-26**。该条**保持 RED**，禁删禁改禁 skip 禁 xfail。

## 三、授权写集与纪律

- 授权写集：**`tests/test_config_placeholder.py` 单文件**（承接 lane = ORCH-25 / Dewey / qwen3.8-flash·medium）。
- 禁改 `dsm/**`、`ops/**`、`docs/**`、`fixtures/**`、`config/**` 及他人测试。
- 收口标准：全量 `--continue-on-collection-errors` 由 10 failed 降至 **2 failed**（`test_t05_m03` + D-C1-01；D-C1-01 由 C1b 并行修，若其先落地则剩 1）。

## 四、文档勘误（遗留披露项）

ORCH-24 存在内部矛盾：line 43 + line 320（`validate_semantics` 一律经 `load_all` 调用、签名三参）与 line 36 / line 342 / line 406（T05 既有用例一条不改、T06-S「T05 既有一条不坏」）**四条不可能同时成立**，必然产生 G1/G2 共 8 条红。本裁决按前者（生产口径）执行。**该矛盾必须在 P3a 的 V-1~V-20 验收证据表中如实披露，不得掩盖。**
