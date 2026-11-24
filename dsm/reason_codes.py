'''dsm.reason_codes -- the single source of truth for every reason_code.

Business modules must reference RC.<NAME>. Raw string literals are forbidden and
are caught by the AST scan in tests/test_architecture.py (property P-8).

Every code carries four things so that reports can be written and work orders can
be dispatched without consulting the source:

    code        the stable identifier that lands in CSV output
    severity    INFO / WARN / BLOCK
    message     the Chinese sentence shown to the reader of the report
    owner_hint  who has to act on it

Design doc 3.3.2. Downgrade discipline (R5): no downgrade may happen without a
reason_code, and no reason_code may be emitted without a disclosure location.
'''
from __future__ import annotations

from enum import Enum


class Severity(str, Enum):
    INFO = 'INFO'
    WARN = 'WARN'
    BLOCK = 'BLOCK'


# (code, severity, message_zh, owner_hint)
_DEFS = (
    # ---- configuration and weight version -----------------------------------
    ('WEIGHT_VERSION_INVALID', 'BLOCK', '权重版本无效：status 必须为 FROZEN 且评价期落在生效区间内', '评价管理委员会'),
    ('WEIGHT_VERSION_DRAFT', 'BLOCK', '权重版本仍为 DRAFT，未经签认不得用于评分', '评价管理委员会'),
    ('WEIGHT_VERSION_STALE', 'BLOCK', '权重版本已过期：评价期超出 effective_to', '评价管理委员会'),
    ('WEIGHT_MISSING_WHATIF_RUN_ID', 'BLOCK', '权重版本为 FROZEN 但缺 whatif_run_id，签认前未做影响预演', '评价管理委员会'),
    ('CONFIG_PLACEHOLDER', 'BLOCK', '配置中存在未签认的 PLACEHOLDER 字段，拒绝出分', '评价管理委员会'),
    ('CONFIG_SEMANTIC_ERROR', 'BLOCK', '配置语义校验失败：权重未归一、门槛非单调或引用了不存在的指标', '评价管理部门'),
    ('CALIBER_VERSION_MISMATCH', 'BLOCK', '指标事实的口径版本与指标字典不一致', '数据部门'),
    ('MONEY_NON_INTEGER', 'BLOCK', '金额字段出现非整数值，金额必须为最小货币单位整数', '数据部门'),
    ('DIMENSION_EMPTIED', 'BLOCK', '有维度因指标全部被剔除而清空，且清空维度数达到阻断阈值', '指标负责人'),
    ('INVARIANT_VIOLATION', 'BLOCK', '内部不变量被违反，属程序缺陷，本次不产出任何结果', '开发'),

    # ---- metric dictionary and data quality --------------------------------
    ('METRIC_NOT_SIGNED', 'WARN', '指标未签认，已剔除并在维度内重归一权重', '指标负责人'),
    ('WEIGHT_REALLOCATED', 'WARN', '指标被剔除后权重已在维度内重新归一', '评价管理部门'),
    ('MISSING_RATE_WARN', 'WARN', '指标缺失率超过预警阈值，已按 missing_rule 处理', '数据部门'),
    ('MISSING_RATE_BLOCK', 'BLOCK', '指标缺失率超过阻断阈值，该策略记为不可评价', '数据部门'),
    ('DATA_STALE', 'WARN', '数据快照时间滞后于评价期', '数据部门'),
    ('DATA_QUALITY_SUSPECT', 'WARN', '上游数据质量标记为 SUSPECT，该指标已剔除', '数据部门'),
    ('ANCHOR_SET_STALE', 'WARN', '锚定基准集失效，已回退为仅当期归一化', '评价管理部门'),
    ('RANK_REVERSAL_RISK', 'WARN', '锚定集失效导致存在秩反转风险，本期相对排名仅供参考', '评价管理部门'),
    ('SMALL_POOL', 'WARN', '池内样本数低于下限，池内排名不稳定', '评价管理部门'),
    ('FIRST_PERIOD', 'INFO', '无上期等级记录，滞回与版本断点按首期处理', '评价管理部门'),

    # ---- attainment and grading -------------------------------------------
    ('NO_TARGET_VALUE', 'WARN', '指标缺少目标值，不计入绝对轨', '指标负责人'),
    ('LOW_TARGET_COVERAGE', 'WARN', '绝对轨目标值覆盖率偏低', '指标负责人'),
    ('ATTAINMENT_CAPPED', 'INFO', '达成率超过上限，已裁剪', '评价管理部门'),
    ('NEGATIVE_ACTUAL', 'WARN', '指标实际值为负，已按缺失规则处理', '数据部门'),
    ('INACTIVE_METRIC', 'WARN', '指标零变异，已剔除并预警', '指标负责人'),
    ('GR_CAPPED_NO_TARGET', 'WARN', '分数可能更高，但因缺少目标值被封顶', '指标负责人'),
    ('GR_EVIDENCE_GATE_L1', 'WARN', '分数达到一级但证据等级不足，已降为二级', '策略设计者'),
    ('GR_REDLINE_FORCED', 'BLOCK', '命中硬红线，等级被强制覆盖，综合分不生效', '风险合规部门'),
    ('GR_STREAK_NOT_MET', 'INFO', '分数达标但连续达标期数不足，本期不升级', '评价管理部门'),
    ('GR_VERSION_BREAK', 'INFO', '策略版本发生变更，升级计数已重置且不做跨版本趋势比较', '策略管理部门'),
    ('NOT_ASSESSED', 'BLOCK', '该策略本期不可评价，不出分，在台账单独计数', '评价管理部门'),

    # ---- evidence ---------------------------------------------------------
    ('EVIDENCE_CARD_MISSING', 'BLOCK', '评价设计卡缺失，证据等级判为 D', '策略设计者'),
    ('EVIDENCE_CARD_PARTIAL', 'WARN', '评价设计卡不完备，证据等级上限压至 C', '策略设计者'),
    ('EVIDENCE_C_NO_LIMIT', 'BLOCK', 'C 类证据未填写解释限制，已降为 D 且不出分', '策略设计者'),
    ('EV_A_RANDOMIZED', 'INFO', '随机分流且有对照组与事前成功判定，证据等级 A', '策略设计者'),
    ('EV_B_QUASI', 'INFO', '准实验设计，证据等级 B', '策略设计者'),
    ('EV_C_OBSERVATIONAL', 'INFO', '仅观测数据，证据等级 C', '策略设计者'),
    ('EV_D_NOT_ASSESSED', 'BLOCK', '不可评价，证据等级 D', '策略设计者'),

    # ---- redline ----------------------------------------------------------
    ('REDLINE_HARD_HIT', 'BLOCK', '命中硬红线，综合分照算并披露但不生效', '风险合规部门'),
    ('REDLINE_SOFT_HIT', 'WARN', '命中软红线，已独立扣减并单列，未进入加权', '风险合规部门'),
    ('WAIVER_INVALID', 'BLOCK', '红线豁免缺少审批留痕，视为未豁免', '风险合规部门'),
    ('WAIVER_EXPIRED', 'BLOCK', '红线豁免已过期，视为未豁免', '风险合规部门'),

    # ---- pooling ----------------------------------------------------------
    ('POOL_TOO_SMALL', 'WARN', '分池样本过小，池内排名仅供参考', '评价管理部门'),
    ('PRIMARY_POOL_REJECTED_EVIDENCE', 'WARN', '证据等级不满足一级库门禁', '策略设计者'),
    ('PRIMARY_POOL_REJECTED_ROBUST', 'WARN', '稳健性不满足一级库门禁', '评价管理部门'),
    ('MIX_QUALITY_DEGRADED', 'WARN', '一级库中低证据等级占比上升，池质量退化', '评价管理委员会'),

    # ---- robustness and method triangulation ------------------------------
    ('STABLE', 'INFO', '等级在全部扰动方案下稳定', '评价管理部门'),
    ('NEAR_BOUNDARY', 'WARN', '等级处于门槛边界，较大扰动下会变级', '评价管理部门'),
    ('UNSTABLE', 'WARN', '等级在小幅扰动下即变级，不得作为淘汰唯一依据', '评价管理委员会'),
    ('FLIP_RATE_REVIEW', 'WARN', '等级翻转率超过复核阈值，本期结论需人工复核', '评价管理委员会'),
    ('FLIP_RATE_UNUSABLE', 'BLOCK', '等级翻转率超过上限，本期结果不得用于淘汰决策', '评价管理委员会'),
    ('METHOD_AGREEMENT', 'INFO', '主排序与 TOPSIS 及 GRA 排序一致', '评价管理部门'),
    ('METHOD_DIVERGENCE', 'BLOCK', '三种方法排序分歧显著，等级结论可能由方法选择驱动，须人工复核', '评价管理委员会'),
    ('DOMINANT_METRIC', 'WARN', '单一指标对综合分影响过大', '指标负责人'),
    ('NORMALIZATION_SENSITIVE', 'WARN', '相对轨结果对归一化方法敏感', '评价管理部门'),
    ('LOO_SAMPLED', 'INFO', '指标数超过阈值，LOO 已改为按维度抽样', '评价管理部门'),
    ('TRIANGULATION_DISABLED', 'INFO', '方法三角验证已在配置中关闭', '评价管理部门'),

    # ---- weight construction (AHP, entropy, alpha, whatif) ----------------
    ('AHP_CR_FAILED', 'BLOCK', 'AHP 一致性比率 CR 达到 0.1，拒绝产出权重草稿', '评价管理委员会'),
    ('AHP_METHOD_MISMATCH', 'WARN', '几何平均法与特征向量法的权重差异超过 1e-6', '评价管理委员会'),
    ('AHP_NOT_RECIPROCAL', 'BLOCK', '两两比较矩阵不满足互反性', '评价管理委员会'),
    ('AHP_DRAFT_ONLY', 'BLOCK', '工具只能产出 DRAFT，签认是人的动作，代码不得代劳', '评价管理委员会'),
    ('ENTROPY_PERIOD_SKIPPED', 'WARN', '该期参评策略数不足，已从标定窗口剔除', '评价管理部门'),
    ('ENTROPY_INSUFFICIENT_SAMPLE', 'WARN', '标定窗口内无可用期，已回退纯 AHP 权重', '评价管理委员会'),
    ('ENTROPY_INACTIVE_FALLBACK', 'WARN', '指标零变异，组合权重回退为 AHP 权重，未被稀释', '指标负责人'),
    ('ENTROPY_UNSTABLE', 'WARN', '指标熵权在标定窗口内漂移过大，建议下期复核', '指标负责人'),
    ('ALPHA_INFEASIBLE', 'BLOCK', '全部候选 alpha 均违反稳定性约束，无法标定', '评价管理委员会'),
    ('ALPHA_FLOOR_INFEASIBLE', 'BLOCK', 'alpha_floor 自身不可行，且不允许静默放宽治理预算', '评价管理委员会'),
    ('ALPHA_FLOOR_APPLIED', 'WARN', '标定所得 alpha 低于 alpha_floor，已取 alpha_floor', '评价管理委员会'),
    ('ALPHA_PURE_AHP', 'INFO', '在当前稳定性预算下只有纯 AHP 可行，本期权重等价于纯 AHP', '评价管理委员会'),
    ('NON_MONOTONIC_WARNING', 'WARN', '稳定性指标随 alpha 变化非单调，已列出全部可行值供人工选择', '评价管理委员会'),
    ('CONFIG_INCONSISTENT', 'BLOCK', '候选权重下红线触发集合发生变化，说明配置有误', '开发'),

    # ---- metric diagnostics ----------------------------------------------
    ('LOW_VARIATION', 'WARN', '指标离散度过低，区分度不足', '指标负责人'),
    ('COLLINEAR', 'WARN', '指标与其他指标高度共线，存在重复计权', '指标负责人'),
    ('RETIRE_OR_REDLINE', 'WARN', '建议将该指标移出字典或改为红线硬阈值', '指标负责人'),
    ('MERGE_OR_DROP', 'WARN', '建议与相关指标合并或择一保留', '指标负责人'),
    ('REDEFINE', 'WARN', '建议重新定义口径或调整目标值区分度', '指标负责人'),
    ('CONTENT_VALIDITY_DOUBT', 'WARN', '指标与参考序列长期低关联，内容效度存疑', '指标负责人'),

    # ---- CEL (causal evidence layer, contract reserved in v1) -------------
    ('CEL_NOT_CONNECTED', 'INFO', '本期未接入增量估计，增量相关字段为空', '评价管理部门'),
    ('CEL_DISABLED_DATA_PRESENT', 'BLOCK', 'cel.enabled 为 false 但增量字段非空，拒绝参与判定', '开发'),

    # ---- R15B2 第 2 批（ops/dag-state.json r15_batch_2.codes_requested / ORCH-30 第 4 条）----
    # 每行的 severity 与 blocks_run 都另有逐字原文依据，登记在下面 _BASIS / _BLOCKS_RUN
    # 两张表里（ORCH-30 第 2 条：severity 是签认属性、不得改写；是否阻断只看 blocks_run）。
    # R-12：无原文依据的一律写 PLACEHOLDER 并在上报里点名，绝不猜测。
    # 消费点接线全部落在本包写集之外，逐条登记在 dsm_stage/R15B2/CONSUMPTION-TODO.md。
    ('DESIGN_CARD_TABLE_ABSENT', 'BLOCK', '评价设计卡表（T4）整体缺失，本轮无法判定 C-08，不产出 score_card', '数据部门'),
    ('DESIGN_CARD_DUPLICATE_KEY', 'BLOCK', '评价设计卡出现重复的 strategy_id × version 行，违反 T4 粒度声明，拒绝静默取后一行', '策略设计者'),
    ('SPEARMAN_ZERO_VARIANCE', 'WARN', '一对排序零方差，Spearman 相关系数无定义，三角验证本期不给一致性结论', '评价管理部门'),
    ('H2_DIM_WEIGHT_BELOW_FLOOR', 'BLOCK', '维度权重低于 min_dim_weight（H-2），该 alpha 判为不可行', '评价管理委员会'),
    ('H3_METRIC_WEIGHT_BELOW_FLOOR', 'BLOCK', '指标权重低于 min_metric_weight（H-3），该 alpha 判为不可行', '评价管理委员会'),
    ('H5_SHIFT_FROM_AHP_EXCEEDED', 'BLOCK', '组合权重与纯 AHP 的 L1 距离超过 max_shift_from_ahp（H-5），该 alpha 判为不可行', '评价管理委员会'),
    ('REDLINE_EXCLUDED_FROM_ENTROPY', 'INFO', '红线指标不参与熵权组合，其权重按 AHP 原值保留', '评价管理委员会'),
    ('PRIMARY_POOL_REJECTED_GRADE', 'WARN', '等级不是 L1，不满足一级库准入门禁', '评价管理部门'),
    ('WEIGHT_DICT_MISALIGNED', 'BLOCK', '权重配置与指标字典未对齐：签认指标缺权重项、存在孤儿权重项或两级权重未各自归一', '评价管理委员会'),
    ('APPROXIMATE_ATTRIBUTION', 'WARN', '非 LINEAR 算子无精确线性分解，归因改用对数差分近似并已标注', '评价管理委员会'),
    ('MISSING_FACT_RULE_APPLIED', 'WARN', '事实行缺失，已按该指标的 missing_rule 处置（ZERO / SKIP / IMPUTE_MEDIAN）', '数据部门'),
)


def _build():
    names = {}
    meta = {}
    for code, sev, msg, owner in _DEFS:
        if code in names:
            raise ValueError('duplicate reason_code: ' + code)
        names[code] = code
        meta[code] = (Severity(sev), msg, owner)
    return names, meta


_NAMES, _META = _build()

RC = Enum('RC', _NAMES, type=str)

# Codes that are generated per metric at runtime resolve to a registered template.
_DYNAMIC_PREFIXES = (
    ('REDLINE_HARD_', 'REDLINE_HARD_HIT'),
    ('REDLINE_SOFT_', 'REDLINE_SOFT_HIT'),
)


def redline_hard(metric_id) -> str:
    '''Per-metric HARD redline code, e.g. REDLINE_HARD_CONTACT_FREQ_PER_30D.'''
    return 'REDLINE_HARD_' + str(metric_id)


def redline_soft(metric_id) -> str:
    '''Per-metric SOFT redline code.'''
    return 'REDLINE_SOFT_' + str(metric_id)


def _key(code) -> str:
    if isinstance(code, str):
        if code in _META:
            return code
        for prefix, fallback in _DYNAMIC_PREFIXES:
            if code.startswith(prefix):
                return fallback
        raise KeyError('unknown reason_code: ' + code)
    value = getattr(code, 'value', None)
    if isinstance(value, str):
        return _key(value)
    raise TypeError('reason_code must be an RC member or a str')


def severity(code) -> Severity:
    return _META[_key(code)][0]


def message(code) -> str:
    return _META[_key(code)][1]


def owner_hint(code) -> str:
    return _META[_key(code)][2]


def describe(code) -> str:
    key = _key(code)
    return '[' + severity(key).value + '] ' + key + ' ' + message(key)


def is_registered(code) -> bool:
    try:
        _key(code)
        return True
    except (KeyError, TypeError):
        return False


def all_codes() -> tuple:
    return tuple(sorted(_META))


def codes_by_severity(sev: Severity) -> tuple:
    return tuple(sorted(c for c in _META if _META[c][0] is sev))


# --- R15B2 · ORCH-30 第 2 条：severity 与 blocks_run 分离登记 -----------------
# severity 属签认属性（V-14：任何 lane 与主控都不得为通过测试而改写）；「本轮是否
# 被阻断」只由 blocks_run 决定，与 severity 字面无关（EVIDENCE_CARD_MISSING 就是
# severity=BLOCK / blocks_run=False 的既有先例）。
# _BASIS 是 R-12 的落地：每个第 2 批新码都登记 (severity 依据, blocks_run 依据,
# 消费点)。依据分三档，逐字引文写 'verbatim:'，由逐字条文推出来的写 'derived:'，
# 原文没有的写 'PLACEHOLDER'（= 未决，须主控裁决，严禁填猜测值）。
# 消费点文件都在本包写集之外，故此处只登记不接线（见 CONSUMPTION-TODO.md）。
_BATCH2 = (
    'DESIGN_CARD_TABLE_ABSENT',
    'DESIGN_CARD_DUPLICATE_KEY',
    'SPEARMAN_ZERO_VARIANCE',
    'H2_DIM_WEIGHT_BELOW_FLOOR',
    'H3_METRIC_WEIGHT_BELOW_FLOOR',
    'H5_SHIFT_FROM_AHP_EXCEEDED',
    'REDLINE_EXCLUDED_FROM_ENTROPY',
    'PRIMARY_POOL_REJECTED_GRADE',
    'WEIGHT_DICT_MISALIGNED',
    'APPROXIMATE_ATTRIBUTION',
    'MISSING_FACT_RULE_APPLIED',
)

# blocks_run=True 的码：本轮不产出 score_card（M22 L917）。
_BLOCKS_RUN = frozenset((
    'DESIGN_CARD_TABLE_ABSENT',
    'DESIGN_CARD_DUPLICATE_KEY',
    'WEIGHT_DICT_MISALIGNED',
))

_BASIS = {
    'DESIGN_CARD_TABLE_ABSENT': (
        "derived: M21 L892 逐字『异常 | DataLoadError（退出码 4）』是 io 层唯一出口，无 WARN 分支；"
        "M22 L918 逐字『宁可不评，不可错评』；ORCH-30 第 1 条裁定表级故障走 io 层退出码 4（非 C-08 的轮级 BLOCK）",
        "derived: M22 L917 逐字『BLOCK 行为 | 只写 audit_bundle（记录为什么没跑出结果）…不产出 score_card』；"
        "退出码按 M21 L892 为 4（与 ORCH-30 第 4 条表格写的『退出码 2』不一致，已上报）",
        'dsm/io_loaders.py:285-287（design_cards 走 TABLE_ABSENT，非阻断 kind）→ 归属 P2'),
    'DESIGN_CARD_DUPLICATE_KEY': (
        "derived: M18 L1102 逐字『T4 | design_cards | 评价设计卡… | 策略 × 版本』声明了唯一粒度；"
        "M21 L892 io 层唯一出口是 DataLoadError（退出码 4），无 WARN 分支；M22 L918『宁可不评，不可错评』。"
        "原文未逐字写 BLOCK，属推定链，已按 R-12 上报待主控确认",
        "derived: M22 L917『不产出 score_card』；静默取后一行是 V-14 禁止的静默降级，只能显式拒绝",
        'dsm/preflight.py:320（by_key = {(c.strategy_id, c.version_id): c for c in self.cards} 静默覆盖）'
        '与 dsm/io_loaders.py:_collect → 归属 A1c（唯一性更可能在 io/models 层落地）'),
    'SPEARMAN_ZERO_VARIANCE': (
        "PLACEHOLDER: 原文（M26 L1022-L1031、§2.6.4 L730-L740）只规定 mean_ρ 与阈值的两个结论"
        "（METHOD_AGREEMENT / METHOD_DIVERGENCE）与『可关 → TRIANGULATION_DISABLED（不得静默）』，"
        "未给零方差情形的严重度列。按 V-14『不得静默』+ M22 L918『任何 WARN 都进最终报告附录，"
        "不会被静默吞掉』暂登记为 WARN，severity 依据仍为 PLACEHOLDER，须主控裁决",
        "verbatim: M26 L1022 标题逐字『triangulation.py —— TOPSIS / GRA 三角验证（M-F、M-G，不入分）』"
        "+ L761『只作独立视角参与三角验证，不入分』→ 不入分即不阻断本轮",
        'dsm/triangulation.py:380-388（_pair 捕获 DivisionUndefinedError 回 None）、'
        ':420-426（verdict 在 mean_rho 为 None 时不给结论）→ 归属 D4 / P2'),
    'H2_DIM_WEIGHT_BELOW_FLOOR': (
        "verbatim: §2.4.3 L593『Step 5 硬约束校验（任一不满足 → 该 α 判为不可行，交给 §2.4.4 处理）』"
        "+ L595『H-2 每个维度 W_d ≥ min_dim_weight（防某维度被熵权整体压没）』；"
        "同层 H-4 的专用码 AHP_CR_FAILED 在注册表里已是 BLOCK（同类同判）",
        "verbatim: L631『可行集为空 | 所有 α 都违反至少一条约束 | 抛 AlphaInfeasibleError』→ 单条 H-2 "
        "只判该 α 不可行，整轮阻断由已注册的 ALPHA_INFEASIBLE 承担，故本码 blocks_run=False",
        'dsm/weights_combine.py:683-690（results/violations 已算出 H-2，reasons 只 append 泛码 '
        'ALPHA_INFEASIBLE）→ 归属 A2b / P2'),
    'H3_METRIC_WEIGHT_BELOW_FLOOR': (
        "verbatim: L593『硬约束校验（任一不满足 → 该 α 判为不可行…）』+ L596『H-3 任一指标 w_j ≥ "
        "min_metric_weight（若配置了）』；同层 H-4 → AHP_CR_FAILED 已是 BLOCK",
        "verbatim: L631（只有可行集为空才抛 AlphaInfeasibleError）→ blocks_run=False",
        'dsm/weights_combine.py:677 / 683-690 → 归属 A2b / P2'),
    'H5_SHIFT_FROM_AHP_EXCEEDED': (
        "verbatim: L593『硬约束校验（任一不满足 → 该 α 判为不可行…）』+ L598-L599『H-5 组合后权重与纯 AHP "
        "权重的 L1 距离 ≤ max_shift_from_ahp（默认 0.30）→ 防止熵权把专家判断整体推翻，保证「业务判断主导」』",
        "verbatim: L631（可行集为空才 AlphaInfeasibleError）→ blocks_run=False；"
        "L625『若可行集非区间（存在空洞），报告须显式列出全部可行 α 并要求人工选择』也说明单点违反不终止本轮",
        'dsm/weights_combine.py:679-684 / 690 → 归属 A2b / P2'),
    'REDLINE_EXCLUDED_FROM_ENTROPY': (
        "derived: L62（D2 约束①）逐字『组合仅作用于非红线指标，风险度 / 体验度 / 合规类指标一律走红线硬阈值，"
        "不参与熵权组合』+ L1140『is_redline | 是否红线指标（true 则不参与熵权组合，D2 约束①）』。"
        "这是设计内的既定行为而非故障，故按注册表既有先例（ALPHA_PURE_AHP / CEL_NOT_CONNECTED / "
        "TRIANGULATION_DISABLED 均为 INFO）登记为 INFO；原文无严重度列，已上报",
        "derived: 排除是常态动作，结果照常产出（L62 只说不参与组合）→ blocks_run=False",
        'dsm/weights_combine.py:475-481（refs 取 is_redline 并过滤，仅在无非红线指标时抛 CombineError，'
        '排除本身无码）→ 归属 A2b / P2'),
    'PRIMARY_POOL_REJECTED_GRADE': (
        "derived: M24 L1002 逐字『一级库门禁 | 准入条件：evidence_class ∈ {A, B} 且 grade = L1 且 无 HARD "
        "红线命中 且 无 FLIP_RATE_UNUSABLE；C 类不得进一级库』+ L1005 逐字列出同族码 "
        "『POOL_TOO_SMALL、PRIMARY_POOL_REJECTED_EVIDENCE、PRIMARY_POOL_REJECTED_ROBUST』，"
        "注册表里这两个同族码均为 WARN → 同类同判",
        "verbatim: M24 L1006『输出 | PoolFrame（逐策略 pool_key、pool_rank、primary_pool_eligible、"
        "reject_reason）…』→ 拒绝理由是一列输出，不中断 Step 7（M29 L1346）",
        'dsm/pooling.py:396-397（else: reason = None —— 只差 grade != L1 时单槽留 None）→ 归属 C5 / P2'),
    'WEIGHT_DICT_MISALIGNED': (
        "verbatim: M22 L902 逐字『C-03 | 权重与指标字典对齐 | 每个签认指标在权重配置中有对应项；无孤儿权重项；"
        "两级权重各自归一（1e-12）| **BLOCK**』",
        "verbatim: M22 L917『BLOCK 行为 | 只写 audit_bundle…+ 退出码 2，不产出 score_card』→ blocks_run=True；"
        "接线时须同时进 dsm/preflight.py 的 RUN_BLOCKING_CODES 与 DISCLOSURE（本包禁写）",
        'dsm/preflight.py:215-237（C-03 现沿用泛码 CONFIG_SEMANTIC_ERROR，注释自述『注册表无 C-03 专用码』）'
        '→ 归属 C2 / P2'),
    'APPROXIMATE_ATTRIBUTION': (
        "PLACEHOLDER: M10 L674 逐字『GEOMETRIC 算子下无精确线性分解 → 改用对数差分近似并标注 "
        "APPROXIMATE_ATTRIBUTION』与 L473 同口径只要求『标注』，原文未给严重度列。按 R5（无 reason_code "
        "不得降级）+ M22 L918（任何 WARN 都进报告附录）暂登记为 WARN，须主控裁决",
        "derived: L674 的处置是『改用近似并标注』＝照常出数 + 披露，不是拒算；且 whatif 是 L0b 离线工具"
        "（M00 L294 / ORCH-27），不在评分主流程上 → blocks_run=False",
        'dsm/whatif.py:452-463（operator != LINEAR 一律抛 WhatifOperatorError，注释自述该码未注册）'
        '→ 归属 A4 / P2'),
    'MISSING_FACT_RULE_APPLIED': (
        "derived: M22 L903 逐字『C-04 | 缺失率 | 超 warn 阈 → WARN 并按 missing_rule 处理；超 block 阈 → "
        "该策略 NOT_ASSESSED（台账单独计数）| WARN / 策略级降级』+ M18 L1134 逐字『missing_rule | 缺数据处置："
        "ZERO / SKIP / IMPUTE_MEDIAN / BLOCK』+ M02 L930『actual < 0 → 记 NEGATIVE_ACTUAL 并按 missing_rule "
        "处理』。处置动作与 WARN 同级披露，故登记 WARN（原文无独立严重度列，已上报）。"
        "不得挪用 MISSING_RATE_WARN：其 message 绑定『缺失率超过预警阈值』，挪用即虚报",
        "verbatim: M22 L903『WARN / 策略级降级』→ 策略级，不阻断本轮；超 block 阈的轮内后果由已注册的 "
        "MISSING_RATE_BLOCK / NOT_ASSESSED 承担",
        'dsm/attainment.py:524（ZERO 合成行 reason_code=None）、:528（SKIP 行 None）、:532（IMPUTE 分支）'
        '→ 归属 B1b / A1c'),
}


def blocks_run(code) -> bool:
    # 本轮是否被阻断（ORCH-30 第 2 条：只看这里，不看 severity 字面）。
    return _key(code) in _BLOCKS_RUN


def basis(code) -> tuple:
    # (severity 依据, blocks_run 依据, 消费点)，第 2 批新码逐字可查（R-12）。
    return _BASIS[_key(code)]


def batch2_codes() -> tuple:
    return _BATCH2


def blocks_run_codes() -> tuple:
    return tuple(sorted(_BLOCKS_RUN))
