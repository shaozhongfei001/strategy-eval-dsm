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
