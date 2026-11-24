# RUN-ORCH-26 · H-9 / INV-1 架构违规裁决（weights_combine → weights_ahp）

- **时刻**：T+3.73h（ORCH-25 收口后，全量 pytest 唯一残留 RED）
- **裁决人**：主控（Orchestrator）
- **唯一残留失败**：`tests/test_config_placeholder.py::test_t05_m03_no_dsm_module_imports_an_l0_module`（line 1590）
  ```
  AssertionError: H-9 INV-1 violation: [('weights_combine.py', 'dsm.weights_ahp')]
  ```
- **事实**：A2（commit `1bf00d0`）落地的 `dsm/weights_combine.py`（L0a）存在 `from dsm.weights_ahp import ...`（L0b）。H-9 的判据是「**任何 dsm 模块都不得 import L0 模块**」，比 §3.2 第 266 行转述的 INV-1（「L1-L5 永不 import L0a/L0b」）更严；按更严者执行。

## 一、裁决

1. **H-9 断言不得弱化、不得删除、不得 skip/xfail。** 架构守护是本 run 四条不可砍底线之外的机器护栏，改断言迁就实现属 R-14 禁止的反填。
2. **违规方是 import 边，必须消除**，修法按 ORCH-03 先例排序：
   - **① 数据注入（首选）**：`weights_combine` 只消费 AHP 的**快照产物**（`WeightProvenance.ahp` / `AhpSegment` 数据，含 CR、λmax、向量），由调用方（`cli.py` 或集成骨架）传入；L0a 不 import L0b。与 ORCH-03 认定的类型隔离原则一致（provenance 是快照值，不是可调用对象）。
   - **② 算法上提 L1（次选）**：若确有必须共用的算法，照 entropy 先例上提到 L1，L0a/L0b 各自 import L1。
   - **③ 禁止**用 `TYPE_CHECKING`、`try/except ImportError`、`importlib` 动态导入等手段隐藏该边——AST 扫描仍视为违规，且构成 V-14 静默降级。
3. **时序约束（关键）**：修复包 **A2b 必须等 A3（calibrate）与 A4（whatif）落地后再派**。理由：A3/A4 此刻正在按 A2 的公开签名并行开发，签名变动会连带返工。A2b 的硬约束是**公开签名冻结**——只删 import 边、不改 `build_draft`/`build` 的参数与返回类型。若在冻结签名下无法消除该边，升级 SP-3 由主控重排并对 A3/A4 做回归。
4. **P2 门禁（全量 0 failed）必须在 A2b 落地后才判定**；在此之前该 1 条 RED 保持可见、逐次巡检点名，不得提前宣布达标。
5. **待 E5 补证**：E5（`tests/test_architecture.py`）被要求按 `docs/digest/M00-architecture.md` **原文**判定 INV-1 是否禁止 L0a→L0b。若 M00 逐字支持「L0a 可 import L0b」，则本裁决第 1 条改为**对 H-9 的扫描范围做文档级勘误**（排除 L0a→L0b 边），且必须附 M00 原文引文；**无逐字支持则维持本裁决**。缺引文一律不得放行（R-12）。

## 二、ADJ-10（同批裁决）· ORCH-25 越界自判予以核可

ORCH-25（commit `1c0d2fb`）除主控明列的 G1（`_clean_grade_rules`）/G2（`i05` 签名断言）外，另把同文件私有 fixture `_clean_weights()`（约 line 290）照抄为 `test_config_properties.py::_t06_complete_tree('AHP_ONLY')` 既有合成树，并自报「可能越界、可单独回退」。

**核可**，理由：① 与 ORCH-25 同一裁决精神（过时私有 fixture 的填充内容跟上已落地的生产语义）；② 零新数值、零新治理值，全部取自既有已入册合成树；③ 在授权写集（单文件）内；④ 断言零弱化可核（删除 27 行中仅 1 行为被更强断言取代的旧签名 assert，`pytest.raises`/`exit_code`/`reason_code` 相关删除 0 行）。
**附加要求**：该越界自判与 ORCH-24 的内部矛盾（line 43+320 vs line 36/342/406）必须一并写入 **P3a 的 V-1~V-20 验收证据表**如实披露，不得掩盖。

## 三、当前 pytest 账

| 时刻 | failed | 说明 |
|---|---|---|
| T0 基线 | 212 | 211 故意 RED + D-C1-01 |
| B4 后（`3fef4da`） | 10 | 211 RED 全绿 |
| C1b 后（`6430e2b`） | 9→8 | D-C1-01 关闭 |
| ORCH-25 后（`1c0d2fb`） | **1** | 仅 H-9/INV-1，待 A2b |
