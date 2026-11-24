'''dsm.whatif -- L0b 权重变更影响预演：权重在**签认前**的后果显示器。

事实来源：M10 [L640]-[L683]（主）、M42 [L1073]（签名/异常）、M33 [L1453]（T-WIF-01~05）、
M36 [L1511]（V-18）、M29 [L1342]-[L1350]（Step 5-8）。

守护编号 -> 落点：
  T-WIF-01 归因精确性：Σ_d(段1+段2+交叉项) 与 Δcomposite **逐项**差 ≤ 1e-12；_attribute()
           运行时自证，残差超容差即抛 WhatifAttributionError，不把不精确结果交出去。
  T-WIF-02 只读 INV-2：run() 只返回对象、**零字节写盘**（写 reports/whatif/<run_id>/ 是
           D5 cli.py 的职责）；「运行前后目录哈希比对」的自证在 tests 里做，哈希只调用
           dsm.audit 的原语（sha256_bytes / canonical_text / sha256_text），本模块与测试
           都不重实现哈希（R-7）。
  T-WIF-03 与 score 一致：候选与冻结权重数值相同时三臂退化 -> Δcomposite=0、grade_changes
           空、attribution 全 0；调用方交来生产 Step 5/6 结果时 baseline 臂必须逐行精确
           复现（_crosscheck，不等即抛）。
  T-WIF-04 红线不变性：Step 4 不消费权重 -> redline_delta 恒空；非空即 warnings 追加
           CONFIG_INCONSISTENT 且 signoff_verdict() 建议拒绝签认（[L1370]/M10 用途 2）。
  T-WIF-05 两段归因交叉项分离：段1/段2/交叉项三列互不并入，并用**中间臂**（baseline
           level1 + candidate level2）独立测得段1 之和与代数分解对拍（[L672]-[L673]）。
  V-18     不污染生产输出 + 等权时与 score 完全一致（= T-WIF-02 + T-WIF-03）。

分解（LINEAR，[L663]-[L670]）：下标 0=基线、1=候选，W1·dim1 − W0·dim0 恒等拆成
    段1  seg_within_dim = W0_d · (dim1_d − dim0_d)      维度内权重变化
    段2  seg_dim_weight = (W1_d − W0_d) · dim0_d        维度权重变化
    交叉 cross_term     = (W1_d − W0_d) · (dim1_d − dim0_d)   独立成列，不并入任一段
三项之和逐维求和即 Δcomposite，**无任何近似**。交叉项单列正是 [L673]「避免交叉项归因
错误」的落地：并进段2 = M10 的串行口径，并进段1 = 另一套口径，两者都让单段数字说谎。

边界（逐条上报，未静默处理）：
  1 归因只支持 LINEAR。[L674] 的 GEOMETRIC 对数差分近似要标注 APPROXIMATE_ATTRIBUTION，
    但该码不在 reason_codes 注册表内（reason_codes.py 属主控写集，R-15 禁改）-> 非 LINEAR
    一律显式抛 WhatifOperatorError，绝不出近似值（R-12 / V-14）。
  2 段1/段2 可分离要求候选与基线的维度集合、各维度内指标集合**完全一致**；增删维度或
    指标是结构变化而非权重变化 -> WhatifStructureError。
  3 Step 1-4 与权重无关（[L671]），故复用调用方交来的 Step 1-4 帧（同 D2 复用 [L1016]
    的口径）；Step 5-7 每臂重跑。
  4 aggregate 的 [L1190] 门只放 FROZEN 进 Step 5，而预演臂（DRAFT 候选、段1 混合权重）
    都不是签认版本 -> _scorable() 复制一份 status=FROZEN 的**影子文档**仅供同一段 Step 5
    代码计算：不写盘、不返回、不进 config.weights、原文档零改动（AHP_DRAFT_ONLY：签认是
    人的动作）。
  5 [L954] 维度级重归一把 W_d 变成有效权重 W_d/ΣW；归因一律用**有效权重**（与 aggregate
    实际施加的同值同精度），故维度被清空时恒等式仍精确；发生重归一即披露 WEIGHT_REALLOCATED。
  6 本模块**零 L6 依赖**（ORCH-27 裁决 D-A4-01 的修法）：M00 L294 给 L0b 的授权是 L1-L5，
    故 whatif.py 不 import dsm.audit；INV-2 的目录哈希作为 **callable 注入**（run 的
    input_dir + directory_hash 两个 keyword-only 入参）。R-7 禁止本模块自行实现哈希，
    调用方（cli / tests）注入 audit.sha256_bytes + canonical_text + sha256_text 的组合；
    注入即在 run() 内部做前后比对并回吐 readonly_proof，不注入则 None（不冒充已验证）。
  7 段值保留精确乘积（≤24 位小数），**不中途量化**：逐列 q12 会把三列之和与总差推到
    1e-12 以上，直接违反 T-WIF-01；对外哈希由 audit.canonical_text rule 1 统一 q12。

V-9：全程 Decimal，除法只走 safe_div、比较只走 eq_tol/eq_exact、量化只走 q12，float 一步
不出现（Ratio 的 BeforeValidator 会拒）。V-14：run_id / 上期基线 / 签认治理值缺任一项一律
抛显式异常 + 已注册 reason_code，不兜底默认，不用 PLACEHOLDER 冒充已验证（K-01~K-20）。
H-8：无时钟、无写入、无全局状态、无随机。
'''
from __future__ import annotations

from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from dsm import aggregate, grading, numeric, pooling, redline, sensitivity
from dsm.config import AppConfig, is_placeholder_value
from dsm.models import (AttainmentFrame, EvidenceFrame, FrameGrade, GradeFrame,
                        NormalizedFrame, PoolStats, Ratio, RedlineFrame, ScoreFrame,
                        StrictBool, StrictInt, WeightVersionDoc)
from dsm.reason_codes import RC, is_registered

__all__ = ['WhatifError', 'WhatifRunIdError', 'WhatifBaselineError', 'WhatifInputError',
           'WhatifPlaceholderError', 'WhatifStructureError', 'WhatifOperatorError',
           'WhatifAttributionError', 'WhatifConsistencyError', 'WhatifReadonlyError',
           'GradeChange',
           'DimAttribution', 'AttributionReconciliation', 'OccupancyDelta',
           'SensitivitySchemeDelta', 'SensitivityDelta', 'WhatifReport', 'ArmBase',
           'run', 'signoff_verdict', 'is_refused']

KEY_SEP = pooling.KEY_SEP                    # '|'，与 Step 7 同一个分隔符
LINEAR = 'LINEAR'                            # [L953] 唯一可精确分解的算子
NOT_ASSESSED = RC.NOT_ASSESSED.value         # [L1004] 单列不进分母（H-7：不用裸字面量）
GRADE_ORDER = ('L1', 'L2', 'L3', 'L4', NOT_ASSESSED)
TRACKS = (('ABSOLUTE', 'dim_absolute', 'composite_absolute'),
          ('RELATIVE', 'dim_relative', 'composite_relative'))
# 上游载体：必需项缺一个即抛（V-14）；可空项也必须**显式**给出（None 是声明，不是缺省）。
REQUIRED_INPUT_KEYS = ('attainment', 'normalized', 'evidence', 'redline', 'master',
                       'rules', 'prev_grade', 'streaks', 'prev_weight_version_id',
                       'first_period')
OPTIONAL_INPUT_KEYS = ('score', 'grade', 'aggregate_config', 'pool_params',
                       'sensitivity_config', 'normalizer', 'seed')
_NULLABLE_KEYS = frozenset(REQUIRED_INPUT_KEYS[6:] + OPTIONAL_INPUT_KEYS)
_WARNING_ORDER = (RC.CONFIG_INCONSISTENT.value, RC.WEIGHT_REALLOCATED.value,
                  RC.FIRST_PERIOD.value, RC.NOT_ASSESSED.value)


# ---------------------------------------------------------------------------
# 异常：每条都带一个**已注册** reason_code（H-7），绝不静默降级（V-14）
# ---------------------------------------------------------------------------
class WhatifError(Exception):
    '''本模块全部契约违反的基类；reason_code 一律取注册表内的码。'''

    reason_code = RC.INVARIANT_VIOLATION.value

    def __init__(self, message, reason_code=None):
        code = self.reason_code if reason_code is None else reason_code
        self.reason_code = code if is_registered(code) else RC.INVARIANT_VIOLATION.value
        super().__init__(message + ' [reason_code=' + self.reason_code + ']')


class WhatifRunIdError(WhatifError):
    '''缺 whatif_run_id（[L1241] / M10 治理用途 1）。'''
    reason_code = RC.WEIGHT_MISSING_WHATIF_RUN_ID.value


class WhatifBaselineError(WhatifError):
    '''缺上期基线 / 基线权重版本非法（[L1190]）。'''
    reason_code = RC.WEIGHT_VERSION_INVALID.value


class WhatifInputError(WhatifError):
    '''上游载体缺失或类型不对：不猜、不默认、不跳过。'''


class WhatifPlaceholderError(WhatifError):
    '''载体仍是未签认占位值（K-01~K-20：严禁猜数）。'''
    reason_code = RC.CONFIG_PLACEHOLDER.value


class WhatifStructureError(WhatifError):
    '''候选与基线的维度/指标结构不一致，精确分解不成立（边界 2）。'''
    reason_code = RC.CONFIG_SEMANTIC_ERROR.value


class WhatifOperatorError(WhatifError):
    '''非 LINEAR 无精确线性分解，且 APPROXIMATE_ATTRIBUTION 未注册（边界 1）。'''
    reason_code = RC.CONFIG_SEMANTIC_ERROR.value


class WhatifAttributionError(WhatifError):
    '''归因自证失败：三段之和与总差 > 1e-12（T-WIF-01），属程序缺陷。'''


class WhatifConsistencyError(WhatifError):
    '''预演臂与生产 Step 5/6 不一致，或三臂行集不可比（T-WIF-03）。'''


class WhatifReadonlyError(WhatifError):
    '''INV-2 被违反：注入的目录哈希在预演前后不一致（只读自证失败，属程序缺陷）。'''


# ---------------------------------------------------------------------------
# 输出模型。models.py 是冻结契约（R-15）且无 WhatifReport，故按 M10 [L649]-[L661]
# 的字段名在本模块内声明（与 weights_combine.CombinedWeights 同一办法）。
# ---------------------------------------------------------------------------
class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class GradeChange(_Frozen):
    '''M10 [L653]-[L654] 逐字七列：谁升谁降 + 主驱动维度 + 解释。'''
    strategy_id: str
    version_id: str
    baseline_grade: FrameGrade
    whatif_grade: FrameGrade
    delta_composite: Ratio | None = None   # 绝对轨（[L968] 等级只看绝对轨）
    main_driver_dim: str | None = None     # |dim_total| 最大者，并列取字典序最小
    explanation: str                       # 只由已算出的数值拼成，无一个猜数


class DimAttribution(_Frozen):
    '''维度级贡献分解（[L659] + [L663]-[L673]）；交叉项独立成列（T-WIF-05）。'''
    strategy_id: str
    version_id: str
    period: str
    track: str                # ABSOLUTE / RELATIVE
    dim_code: str
    dim_baseline: Ratio       # dim0_d
    dim_candidate: Ratio      # dim1_d
    dim_delta: Ratio          # Δdim_d
    weight_baseline: Ratio    # 有效 W0_d（[L954]，边界 5）
    weight_candidate: Ratio   # 有效 W1_d
    weight_delta: Ratio       # ΔW_d
    seg_within_dim: Ratio     # 段1 = W0_d · Δdim_d
    seg_dim_weight: Ratio     # 段2 = ΔW_d · dim0_d
    cross_term: Ratio         # 交叉项 = ΔW_d · Δdim_d，不并入任一段
    dim_total: Ratio          # 三段之和 = W1·dim1 − W0·dim0


class AttributionReconciliation(_Frozen):
    '''T-WIF-01 / T-WIF-05 的运行时证据：每轨一条对账。'''
    track: str
    checked_items: StrictInt            # 逐项校验过的 (策略 x 轨) 条数
    seg_within_dim_sum: Ratio
    seg_dim_weight_sum: Ratio
    cross_term_sum: Ratio
    total_sum: Ratio
    delta_composite_sum: Ratio          # Σ(composite1 − composite0)
    mid_arm_delta_sum: Ratio            # Σ(composite_mid − composite0)：独立测得段1
    candidate_arm_delta_sum: Ratio      # Σ(composite1 − composite_mid)
    max_residual: Ratio                 # 全部逐项残差的最大绝对值，必须 ≤ 1e-12


class OccupancyDelta(_Frozen):
    '''M10 [L656]：L1-L4 与 NOT_ASSESSED 计数变化 + 分池/合并占比双报的变化。'''
    grade_counts_baseline: dict[str, StrictInt]
    grade_counts_whatif: dict[str, StrictInt]
    grade_count_delta: dict[str, StrictInt]
    share_in_pool_baseline: dict[str, Ratio]   # 分池口径（[L1003] 双报之一）
    share_in_pool_whatif: dict[str, Ratio]
    share_in_pool_delta: dict[str, Ratio]
    share_overall_baseline: dict[str, Ratio]   # 合并口径（双报之二）
    share_overall_whatif: dict[str, Ratio]
    share_overall_delta: dict[str, Ratio]


class SensitivitySchemeDelta(_Frozen):
    '''一个方案下 flip_rate 的变化（[L660]）。'''
    scheme: str
    baseline_flip_rate: Ratio
    whatif_flip_rate: Ratio
    flip_rate_delta: Ratio


class SensitivityDelta(_Frozen):
    '''Step 8 的分布变化；只有 --include-sensitivity 时才非 None（否则不冒充已验证）。'''
    by_scheme: tuple[SensitivitySchemeDelta, ...]
    stability_counts_baseline: dict[str, StrictInt]
    stability_counts_whatif: dict[str, StrictInt]
    stability_count_delta: dict[str, StrictInt]
    baseline_vetoed: StrictBool
    whatif_vetoed: StrictBool


class WhatifReport(_Frozen):
    '''M10 [L649]-[L661] 的 WhatifReport + 四个可追溯补充列：run_id（治理用途 1 要求的
    预演编号）、operator（[L953] 从 ScoreRow 回读）、reconciliation（T-WIF-01 证据）、
    refuse_signoff（[L1370] 的拒绝签认结论）。'''
    run_id: str
    period: str
    candidate_weight_version_id: str
    baseline_weight_version_id: str
    operator: str
    grade_changes: tuple[GradeChange, ...]
    unchanged_count: StrictInt
    occupancy_delta: OccupancyDelta
    redline_delta: tuple[str, ...]           # 正常必为空（T-WIF-04）
    evidence_gate_delta: tuple[str, ...]     # 一级库准入集合变化
    attribution: tuple[DimAttribution, ...]
    reconciliation: tuple[AttributionReconciliation, ...]
    sensitivity_delta: SensitivityDelta | None = None
    warnings: tuple[str, ...]
    refuse_signoff: StrictBool
    readonly_proof: str | None = None   # 注入的目录哈希（前后同值）；未注入即 None，
                                      # 不用 None 冒充已验证（V-14）


class ArmBase(_Frozen):
    '''D2 sensitivity.run 只读 base 的四个属性，故预演臂用这个最小载体喂它，
    不必伪造一整个 ScoringContext（也不动 models.py，R-15）。'''
    attainment: AttainmentFrame
    normalized: NormalizedFrame
    grade: GradeFrame
    seed: StrictInt | None = None


# ---------------------------------------------------------------------------
# 入参解析：全部显式，缺即抛（V-14）
# ---------------------------------------------------------------------------
def _carrier(inputs, key, required=True):
    '''取一个上游载体。缺键 -> WhatifInputError；不可空载体是 None/PLACEHOLDER ->
    WhatifPlaceholderError。绝不返回自己发明的默认值。'''
    if isinstance(inputs, Mapping):
        present, value = key in inputs, inputs.get(key)
    else:
        present, value = hasattr(inputs, key), getattr(inputs, key, None)
    if not present:
        if not required:
            return None
        raise WhatifInputError('缺少上游载体 inputs[' + key + ']：whatif 不猜、不默认、'
                               '不跳过（V-14）；必需载体=' + ','.join(REQUIRED_INPUT_KEYS))
    if key in _NULLABLE_KEYS:
        if isinstance(value, str) and is_placeholder_value(value):
            raise WhatifPlaceholderError('载体 inputs[' + key + '] 仍是未签认占位值：'
                                         + str(value))
        return value
    if value is None or is_placeholder_value(value):
        raise WhatifPlaceholderError('载体 inputs[' + key + '] 缺签认值（None / '
                                     'PLACEHOLDER）：未签认数值一律 PLACEHOLDER 且拒绝'
                                     '出数（V-14 / K-01~K-20）')
    return value


def _weight_doc(value, config, label):
    '''候选/基线可以是构造好的 WeightVersionDoc，也可以是 config.weights 的文件 stem
    （D5 cli.py 的 cmd_whatif 就传 stem）。两条路最终都要拿到一个契约对象。'''
    if isinstance(value, WeightVersionDoc):
        return value
    if isinstance(value, str):
        tree = getattr(config, 'weights', None)
        if tree is None and isinstance(config, Mapping):
            tree = config.get('weights')
        tree = dict(tree or {})
        if value not in tree:
            raise WhatifInputError(label + ' 权重版本 ' + value + ' 不在 config.weights 里'
                                   '（现有：' + ','.join(sorted(tree)) + '）；不猜版本号')
        return WeightVersionDoc.model_validate(tree[value])
    raise WhatifInputError(label + ' 必须是 WeightVersionDoc 或 config.weights 的键，收到 '
                           + type(value).__name__ + '（构造输入照 dsm/models.py 逐字，R-2）')


def _check_run_id(run_id):
    '''run_id 是签认链上的预演编号，只能由调用方（cli 的 Run.run_id）注入：本模块无时钟
    （H-8），也不猜编号（V-14）。'''
    if not isinstance(run_id, str) or is_placeholder_value(run_id) or not run_id.strip():
        raise WhatifRunIdError('缺 whatif_run_id：签认申请必须附对应预演编号（M10 治理'
                               '用途 1 / [L1241]），收到 ' + repr(run_id))
    return run_id.strip()


def _check_baseline(doc):
    '''基线必须 FROZEN，且自己带着上一次的 whatif_run_id：没做过影响预演就冻结的版本
    不能当预演基线（[L1241] + M10 治理用途 1）。'''
    if doc.status != 'FROZEN':
        raise WhatifBaselineError('基线权重版本必须 FROZEN（[L1190]），收到 status='
                                  + str(doc.status) + '，version=' + doc.weight_version_id)
    prov = doc.provenance
    prior = getattr(prov, 'whatif_run_id', None) if prov is not None else None
    if prior is None or is_placeholder_value(prior):
        raise WhatifRunIdError('基线权重版本 ' + doc.weight_version_id
                               + ' 的 provenance.whatif_run_id 缺失或仍是占位值：FROZEN '
                                 '版本必须附上一次预演编号（[L1241]），不替它编一个')
    return doc


def _structure(doc):
    '''(维度集合, 各维度内指标集合)：段1/段2 可分离的前提（边界 2）。'''
    level2 = doc.level2_weights
    return (tuple(sorted(doc.level1_weights)),
            tuple((d, tuple(sorted(level2.get(d, {})))) for d in sorted(doc.level1_weights)))


def _scorable(doc):
    '''预演臂的影子权重文档：只把 status 置 FROZEN，让 aggregate 的 [L1190] 门放行
    **同一段 Step 5 代码**。影子不写盘、不返回、不进 config.weights，原文档零改动
    （frozen + model_copy）；weight_version_id 原样保留（边界 4）。'''
    return doc.model_copy(update={'status': 'FROZEN'})


def _effective_weights(doc, dim_codes, where):
    '''[L954] 重归一后的**有效**维度权重 W_d / Σ_{可用维度} W_d，与 aggregate 在 Step 5
    实际施加的值同源同精度，故维度被清空时恒等式仍精确。返回 (有效权重表, 分母)。'''
    nominal = doc.level1_weights
    total = numeric.weighted_sum([(numeric.ONE, nominal[d]) for d in dim_codes])
    if numeric.eq_tol(total, numeric.ZERO):
        raise WhatifAttributionError('可用维度权重之和为 0，无法归因：' + where)
    out = {}
    for dim in dim_codes:
        weight = numeric.safe_div(nominal[dim], total, on_zero=None)
        if weight is None:
            raise WhatifAttributionError('维度权重不可归一：' + where + ' / ' + dim)
        out[dim] = weight
    return out, total


def _index(rows):
    return {(r.strategy_id, r.version_id, r.period): r for r in rows}


def _fmt(value) -> str:
    return ('+' if value > numeric.ZERO else '') + str(numeric.q12(value))

# ---------------------------------------------------------------------------
# 归因：三段臂 -> DimAttribution + 每轨对账（T-WIF-01 / T-WIF-05 的运行时自证）
# ---------------------------------------------------------------------------
def _attribute(baseline_doc, candidate_doc, score0, score_mid, score1, period):
    '''逐项自证：任一 (策略 x 轨) 的三段之和与 Δcomposite 差超过 1e-12 即抛，
    并把中间臂独立测得的段1 之和一并对拍（边界 7：全程不中途量化）。'''
    idx0, idxm, idx1 = _index(score0.rows), _index(score_mid.rows), _index(score1.rows)
    if sorted(idx0) != sorted(idx1) or sorted(idx0) != sorted(idxm):
        raise WhatifConsistencyError(
            '三个预演臂的行集不一致（Step 1-4 帧相同，行集必须相同）：baseline=%d '
            'mid=%d candidate=%d' % (len(idx0), len(idxm), len(idx1)))
    rows, reconciled, reallocated = [], [], False
    for track, dim_field, comp_field in TRACKS:
        sums = dict((k, numeric.ZERO) for k in
                    ('seg1', 'seg2', 'cross', 'total', 'delta', 'mid', 'cand'))
        residual, items = numeric.ZERO, 0
        for key in sorted(idx0):
            row0, rowm, row1 = idx0[key], idxm[key], idx1[key]
            dims0 = dict(getattr(row0, dim_field))
            dimsm = dict(getattr(rowm, dim_field))
            dims1 = dict(getattr(row1, dim_field))
            comp0, compm = getattr(row0, comp_field), getattr(rowm, comp_field)
            comp1 = getattr(row1, comp_field)
            if comp0 is None or compm is None or comp1 is None:
                if not (comp0 is None and compm is None and comp1 is None):
                    raise WhatifConsistencyError(
                        '三臂可评价性不一致（' + KEY_SEP.join(key) + ' / ' + track
                        + '）：composite 必须同为空或同非空（[L964] 不给不出分的策略编分值）')
                continue
            if row0.period != period:
                raise WhatifInputError('Step 5 行的评价期与 --period 不一致：'
                                       + row0.period + ' != ' + period)
            if sorted(dims0) != sorted(dims1) or sorted(dims0) != sorted(dimsm):
                raise WhatifConsistencyError('三臂的可用维度集合不一致（'
                                             + KEY_SEP.join(key) + ' / ' + track + '）')
            dim_codes = sorted(dims0)
            w0, tot0 = _effective_weights(baseline_doc, dim_codes, 'baseline')
            w1, tot1 = _effective_weights(candidate_doc, dim_codes, 'candidate')
            if not numeric.eq_tol(tot0, numeric.ONE) or not numeric.eq_tol(tot1, numeric.ONE):
                reallocated = True            # [L954] 维度级重归一 -> 披露
            seg1_sum = seg2_sum = cross_sum = numeric.ZERO
            for dim in dim_codes:
                d0, d1 = dims0[dim], dims1[dim]
                ddiff, wdiff = d1 - d0, w1[dim] - w0[dim]      # 精确差，不量化
                seg1 = w0[dim] * ddiff                         # 段1：维度内权重变化
                seg2 = wdiff * d0                              # 段2：维度权重变化
                cross = wdiff * ddiff                          # 交叉项：独立成列
                seg1_sum, seg2_sum = seg1_sum + seg1, seg2_sum + seg2
                cross_sum = cross_sum + cross
                rows.append(DimAttribution(
                    strategy_id=key[0], version_id=key[1], period=key[2], track=track,
                    dim_code=dim, dim_baseline=d0, dim_candidate=d1, dim_delta=ddiff,
                    weight_baseline=w0[dim], weight_candidate=w1[dim], weight_delta=wdiff,
                    seg_within_dim=seg1, seg_dim_weight=seg2, cross_term=cross,
                    dim_total=seg1 + seg2 + cross))
            for got, want, name in (
                    (seg1_sum, compm - comp0, '段1 vs 中间臂实测'),
                    (seg2_sum + cross_sum, comp1 - compm, '段2+交叉项 vs 候选臂实测'),
                    (seg1_sum + seg2_sum + cross_sum, comp1 - comp0, '三段之和 vs 总差')):
                if not numeric.eq_tol(got, want):
                    raise WhatifAttributionError(
                        '归因不精确（T-WIF-01）：' + KEY_SEP.join(key) + ' / ' + track
                        + ' / ' + name + ' 残差=' + str(numeric.q12(got - want)) + ' > 1e-12')
                residual = max(residual, abs(got - want))
            sums['seg1'] += seg1_sum
            sums['seg2'] += seg2_sum
            sums['cross'] += cross_sum
            sums['total'] += seg1_sum + seg2_sum + cross_sum
            sums['delta'] += comp1 - comp0
            sums['mid'] += compm - comp0
            sums['cand'] += comp1 - compm
            items += 1
        reconciled.append(AttributionReconciliation(
            track=track, checked_items=items, seg_within_dim_sum=sums['seg1'],
            seg_dim_weight_sum=sums['seg2'], cross_term_sum=sums['cross'],
            total_sum=sums['total'], delta_composite_sum=sums['delta'],
            mid_arm_delta_sum=sums['mid'], candidate_arm_delta_sum=sums['cand'],
            max_residual=residual))
    return tuple(rows), tuple(reconciled), reallocated


def _operator(*frames):
    '''算子从 ScoreRow.operator 回读（[L953]）：三臂必须同一个算子，且只有 LINEAR 有
    精确线性分解（边界 1）。'''
    found = set(row.operator for frame in frames for row in frame.rows)
    if not found:
        raise WhatifInputError('本期 Step 5 没有任何行：无分值即无从预演（不猜空期结果）')
    if len(found) != 1:
        raise WhatifConsistencyError('三臂算子不一致：' + ','.join(sorted(found)))
    operator = found.pop()
    if operator != LINEAR:
        raise WhatifOperatorError(
            '算子 ' + operator + ' 无精确线性分解；[L674] 要求标注 '
            'APPROXIMATE_ATTRIBUTION，但该码不在 reason_codes 注册表内且该文件非本包写集'
            '（R-15）-> 拒绝出近似归因（R-12 / V-14）')
    return operator


def _crosscheck(score0, grade0, prod_score, prod_grade):
    '''T-WIF-03 的自证面：调用方交来生产 Step 5/6 结果时，baseline 臂必须逐行复现
    （比率 1e-12、其余精确）。任一行不等即说明预演与生产不是同一条路 -> 抛，不出报告。'''
    if prod_score is not None:
        got, want = _index(score0.rows), _index(prod_score.rows)
        if sorted(got) != sorted(want):
            raise WhatifConsistencyError(
                'baseline 臂与生产 Step 5 的行集不一致：%d vs %d' % (len(got), len(want)))
        for key in sorted(want):
            a, b = got[key], want[key]
            same = all(_same_ratio(getattr(a, f), getattr(b, f)) for f in
                       ('composite_absolute', 'composite_relative', 'coverage'))
            same = same and _same_map(a.dim_absolute, b.dim_absolute)
            same = same and _same_map(a.dim_relative, b.dim_relative)
            same = same and a.operator == b.operator
            same = same and a.weight_version_id == b.weight_version_id
            if not same:
                raise WhatifConsistencyError(
                    'baseline 臂未精确复现生产 Step 5（T-WIF-03 / V-18）：' + KEY_SEP.join(key))
    if prod_grade is not None:
        got, want = _index(grade0.rows), _index(prod_grade.rows)
        if sorted(got) != sorted(want):
            raise WhatifConsistencyError(
                'baseline 臂与生产 Step 6 的行集不一致：%d vs %d' % (len(got), len(want)))
        for key in sorted(want):
            a, b = got[key], want[key]
            if (a.grade != b.grade or a.capped != b.capped or a.cap_reason != b.cap_reason
                    or a.usable_for_elimination != b.usable_for_elimination):
                raise WhatifConsistencyError(
                    'baseline 臂未精确复现生产 Step 6（T-WIF-03 / V-18）：' + KEY_SEP.join(key))


def _same_ratio(a, b):
    if a is None or b is None:
        return a is None and b is None
    return numeric.eq_tol(a, b)


def _same_map(a, b):
    return sorted(a) == sorted(b) and all(_same_ratio(a[k], b[k]) for k in sorted(a))


# ---------------------------------------------------------------------------
# 差异列：等级 / 占比 / 红线 / 一级库准入 / Step 8
# ---------------------------------------------------------------------------
def _grade_counts(frame):
    counts = dict((g, 0) for g in GRADE_ORDER)
    for row in frame.rows:
        counts[row.grade] = counts.get(row.grade, 0) + 1
    return counts


def _shares(stats, field):
    return dict((KEY_SEP.join((r.pool_key.biz_domain, r.pool_key.evidence_class)),
                 getattr(r, field)) for r in stats.rows)


def _int_delta(base, whatif):
    return dict((k, int(whatif.get(k, 0)) - int(base.get(k, 0)))
                for k in sorted(set(base) | set(whatif)))


def _ratio_delta(base, whatif):
    '''某臂没有这个池 = 计数 0 = 占比 0（计数事实，不是猜数）。'''
    return dict((k, numeric.q12(whatif.get(k, numeric.ZERO) - base.get(k, numeric.ZERO)))
                for k in sorted(set(base) | set(whatif)))


def _occupancy(grade0, grade1, stats0, stats1):
    c0, c1 = _grade_counts(grade0), _grade_counts(grade1)
    ip0, ip1 = _shares(stats0, 'share_in_pool'), _shares(stats1, 'share_in_pool')
    ov0, ov1 = _shares(stats0, 'share_overall'), _shares(stats1, 'share_overall')
    return OccupancyDelta(
        grade_counts_baseline=c0, grade_counts_whatif=c1, grade_count_delta=_int_delta(c0, c1),
        share_in_pool_baseline=ip0, share_in_pool_whatif=ip1,
        share_in_pool_delta=_ratio_delta(ip0, ip1),
        share_overall_baseline=ov0, share_overall_whatif=ov1,
        share_overall_delta=_ratio_delta(ov0, ov1))


def _redline_set(rl, grades):
    '''红线触发集合：Step 4 的命中行 + redline.hard_vetoes 的 HARD 否决 + Step 6 里留下
    GR_REDLINE_FORCED 痕迹的行。前两项与权重无关（[L988] 不消费权重），第三项来自等级
    路径，故这个集合在两臂之间**只可能**因为配置错误而不同（T-WIF-04）。'''
    items = set(KEY_SEP.join((r.strategy_id, r.version_id, r.metric_id, 'HIT'))
                for r in rl.rows if r.hit)
    items |= set(KEY_SEP.join((r.strategy_id, r.version_id, r.metric_id, 'HARD_VETO'))
                 for r in redline.hard_vetoes(rl))
    items |= set(KEY_SEP.join((r.strategy_id, r.version_id, RC.GR_REDLINE_FORCED.value))
                 for r in grades.rows
                 if RC.GR_REDLINE_FORCED.value in tuple(r.grade_reason_path))
    return tuple(sorted(items))


def _admitted(pool_frame):
    '''一级库准入集合（[L1002] 四条件门禁的结果列）。'''
    return tuple(sorted(KEY_SEP.join((r.strategy_id, r.version_id))
                        for r in pool_frame.rows if r.primary_pool_eligible))


def _set_delta(base_set, whatif_set, added, removed):
    out = [added + KEY_SEP + item for item in sorted(set(whatif_set) - set(base_set))]
    out += [removed + KEY_SEP + item for item in sorted(set(base_set) - set(whatif_set))]
    return tuple(sorted(out))


def _explain(baseline_grade, whatif_grade, delta, driver):
    text = ('等级 ' + baseline_grade + '→' + whatif_grade + '；Δcomposite(绝对轨)='
            + ('无可比值' if delta is None else _fmt(delta)))
    if driver is None:
        return text + '；无维度归因（该策略本期无绝对轨分值）'
    return (text + '；主驱动维度 ' + driver[0] + '（段1 维度内=' + _fmt(driver[2])
            + '，段2 维度权重=' + _fmt(driver[3]) + '，交叉项=' + _fmt(driver[4]) + '）')


def _grade_changes(grade0, grade1, score0, score1, attribution):
    g0, g1 = _index(grade0.rows), _index(grade1.rows)
    s0, s1 = _index(score0.rows), _index(score1.rows)
    if sorted(g0) != sorted(g1):
        raise WhatifConsistencyError('两臂 Step 6 行集不一致：%d vs %d' % (len(g0), len(g1)))
    drivers = {}
    for row in attribution:
        if row.track != 'ABSOLUTE':
            continue                          # 等级只看绝对轨（[L968]）
        key = (row.strategy_id, row.version_id, row.period)
        best = drivers.get(key)
        if (best is None or abs(row.dim_total) > abs(best[1])
                or (abs(row.dim_total) == abs(best[1]) and row.dim_code < best[0])):
            drivers[key] = (row.dim_code, row.dim_total, row.seg_within_dim,
                            row.seg_dim_weight, row.cross_term)
    changes, unchanged = [], 0
    for key in sorted(g0):
        base_grade, whatif_grade = g0[key].grade, g1[key].grade
        if base_grade == whatif_grade:
            unchanged += 1
            continue
        c0, c1 = s0[key].composite_absolute, s1[key].composite_absolute
        delta = None if (c0 is None or c1 is None) else c1 - c0
        driver = drivers.get(key)
        changes.append(GradeChange(
            strategy_id=key[0], version_id=key[1], baseline_grade=base_grade,
            whatif_grade=whatif_grade, delta_composite=delta,
            main_driver_dim=None if driver is None else driver[0],
            explanation=_explain(base_grade, whatif_grade, delta, driver)))
    return tuple(changes), unchanged


def _labels(report):
    out = {}
    for row in report.by_strategy:
        out[row.stability_label] = out.get(row.stability_label, 0) + 1
    return out


def _sensitivity_delta(rep0, rep1):
    by0 = dict((r.scheme, r) for r in rep0.by_scheme)
    by1 = dict((r.scheme, r) for r in rep1.by_scheme)
    if sorted(by0) != sorted(by1):
        raise WhatifConsistencyError('两臂 Step 8 方案集合不一致：' + ','.join(sorted(by0))
                                     + ' vs ' + ','.join(sorted(by1)))
    lab0, lab1 = _labels(rep0), _labels(rep1)
    return SensitivityDelta(
        by_scheme=tuple(SensitivitySchemeDelta(
            scheme=s, baseline_flip_rate=by0[s].overall_flip_rate,
            whatif_flip_rate=by1[s].overall_flip_rate,
            flip_rate_delta=by1[s].overall_flip_rate - by0[s].overall_flip_rate)
            for s in sorted(by0)),
        stability_counts_baseline=lab0, stability_counts_whatif=lab1,
        stability_count_delta=_int_delta(lab0, lab1),
        baseline_vetoed=sensitivity.is_vetoed(rep0),
        whatif_vetoed=sensitivity.is_vetoed(rep1))


def _grade_hook(attainment, evidence, rl, prev, rules, streaks, prev_wv):
    '''D2 要求注入 Step 6 钩子（grading.py 拥有分级，D2 不 import 它）；whatif 是 L0b，
    两层都可直接调用，故这里把 B3 的 assign 包成 D2 期望的 frame -> {定位三元组: 等级}。'''
    def hook(frame):
        out = grading.assign(frame, attainment, evidence, rl, prev, rules,
                             streaks=streaks, prev_weight_version_id=prev_wv)
        return dict(((r.strategy_id, r.version_id, r.period), r.grade) for r in out.rows)
    return hook


def _pool_args(config, params):
    '''pooling.build 要求 config 与 params **只给一个**（C5 的口径）。'''
    if params is not None:
        return None, params
    if isinstance(config, AppConfig):
        return config, None
    raise WhatifInputError('Step 7 需要 AppConfig（走 eval_config.normalize.min_pool_size）'
                           '或 inputs[pool_params] 之一；两者都缺即抛，不自设池样本下限'
                           '（H-5 / V-14）')

# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------
def run(candidate, baseline, inputs, config, period, *, run_id=None,
        include_sensitivity=False, schemes=(), input_dir=None, directory_hash=None):
    '''M42 [L1073] 的签名：run(candidate, baseline, inputs, config, period) -> WhatifReport。

    **只返回对象、一个字节都不写盘**（INV-2 / V-18）：写 reports/whatif/<run_id>/ 是
    D5 cli.py 的职责，L0b 永不写生产报告树。

    candidate / baseline：WeightVersionDoc，或 config.weights 的文件 stem（cli 的传法）。
    inputs：携带 Step 1-4 帧与分级治理值的 Mapping 或对象，键名见 REQUIRED_INPUT_KEYS /
      OPTIONAL_INPUT_KEYS（Step 1-4 与权重无关，[L671]，故复用而不重算 —— 边界 3）。
    config：AppConfig（Step 7 从中读 min_pool_size）或 None（此时必须给 pool_params）。
    run_id：签认链上的预演编号，必填（缺即抛 WhatifRunIdError，见 _check_run_id）。
    include_sensitivity / schemes：[L645] 的 --include-sensitivity 与其方案清单；不开时
      sensitivity_delta 恒为 None，**不用 None 冒充已验证**（ORCH-09 边界）。
    input_dir + directory_hash：INV-2 只读自证的**注入**对（ORCH-27 D-A4-01 的修法）。
      两者要么都给要么都不给；给了就在预演前后各算一次目录哈希，不等即抛
      WhatifReadonlyError，相等则把该哈希写进 readonly_proof。哈希本身由调用方注入
      （只应是 dsm.audit 原语的组合），本模块不实现、也不 import L6（R-7 / M00 L294）。
    '''
    run_id = _check_run_id(run_id)
    proof_before = _readonly_before(input_dir, directory_hash)
    cand = _weight_doc(candidate, config, 'candidate')
    base = _check_baseline(_weight_doc(baseline, config, 'baseline'))
    if not isinstance(period, str) or is_placeholder_value(period) or not period.strip():
        raise WhatifInputError('--period 缺失或仍是未签认占位值：' + repr(period))

    carrier = dict((k, _carrier(inputs, k)) for k in REQUIRED_INPUT_KEYS)
    optional = dict((k, _carrier(inputs, k, required=False)) for k in OPTIONAL_INPUT_KEYS)
    attainment, normalized = carrier['attainment'], carrier['normalized']
    evidence, rl_frame = carrier['evidence'], carrier['redline']
    master, rules = carrier['master'], carrier['rules']
    prev, streaks = carrier['prev_grade'], carrier['streaks']
    prev_wv, first = carrier['prev_weight_version_id'], carrier['first_period']
    for key, value in list(carrier.items()) + list(optional.items()):
        if not isinstance(value, (str, bool)) and not isinstance(value, Sequence) \
                and not isinstance(value, Mapping) and not isinstance(value, BaseModel) \
                and value is not None:
            raise WhatifInputError('载体 inputs[' + key + '] 类型不可用：'
                                   + type(value).__name__)
    for key, kind in (('attainment', AttainmentFrame), ('normalized', NormalizedFrame),
                      ('evidence', EvidenceFrame), ('redline', RedlineFrame),
                      ('score', ScoreFrame), ('grade', GradeFrame)):
        value = carrier.get(key, optional.get(key))
        if value is not None and not isinstance(value, kind):
            raise WhatifInputError('inputs[' + key + '] 必须是 ' + kind.__name__
                                   + '（R-2：字段名逐字抄 dsm/models.py）')
    if not isinstance(rules, grading.GradeRuleSet):
        raise WhatifInputError('inputs[rules] 必须是 grading.GradeRuleSet：分级门槛只能来自'
                               '签认过的 T7 行，whatif 不自设治理值（H-5 / V-14）')
    if not isinstance(first, bool):
        raise WhatifInputError('inputs[first_period] 必须是 bool（上期基线缺失时的显式'
                               '声明），收到 ' + type(first).__name__)
    if prev is None and not first:
        raise WhatifBaselineError(
            '缺上期基线：inputs[prev_grade] 为 None 却没有同时声明 first_period=True。'
            '滞回（[L965]）需要上期等级，首期必须由调用方显式声明，whatif 不从 None '
            '推断（V-14）', RC.FIRST_PERIOD.value)
    if _structure(base) != _structure(cand):
        raise WhatifStructureError(
            '候选与基线的维度/指标结构不一致，两段精确分解不成立（边界 2）：'
            'baseline=' + str(_structure(base)) + ' candidate=' + str(_structure(cand)))

    # ---- Step 5：三臂。基线臂 / 中间臂（基线 level1 + 候选 level2）/ 候选臂 ----
    agg_config = optional['aggregate_config']
    cand_arm = _scorable(cand)
    mid_arm = base.model_copy(update={'level2_weights': cand.level2_weights})
    score0 = aggregate.compose(attainment, normalized, base, agg_config)
    score_mid = aggregate.compose(attainment, normalized, mid_arm, agg_config)
    score1 = aggregate.compose(attainment, normalized, cand_arm, agg_config)
    operator = _operator(score0, score_mid, score1)
    for row in score0.rows:
        if row.period != period:
            raise WhatifInputError('Step 5 行的评价期与 --period 不一致：' + row.period
                                   + ' != ' + period)

    # ---- Step 6：两臂同一套治理值与同一份滞回状态，差异只可能来自权重 ----
    grade0 = grading.assign(score0, attainment, evidence, rl_frame, prev, rules,
                            streaks=streaks, prev_weight_version_id=prev_wv)
    grade1 = grading.assign(score1, attainment, evidence, rl_frame, prev, rules,
                            streaks=streaks, prev_weight_version_id=prev_wv)
    _crosscheck(score0, grade0, optional['score'], optional['grade'])

    # ---- Step 8（可选，[L645]）：两臂各跑一次 D2，钩子用 B3 的真实分级 ----
    sens0 = sens1 = sens_delta = None
    if include_sensitivity:
        sens_config = optional['sensitivity_config']
        if sens_config is None:
            raise WhatifInputError('include_sensitivity=True 需要 inputs[sensitivity_config]'
                                   '（D2 的 stable_max / review_max / mc_samples 等治理值），'
                                   'whatif 不自设（H-5 / V-14）')
        if not tuple(schemes):
            raise WhatifInputError('include_sensitivity=True 需要非空 schemes（[L645]）')
        hook = _grade_hook(attainment, evidence, rl_frame, prev, rules, streaks, prev_wv)
        seed, normalizer = optional['seed'], optional['normalizer']
        sens0 = sensitivity.run(
            ArmBase(attainment=attainment, normalized=normalized, grade=grade0, seed=seed),
            tuple(schemes), sens_config, weights=base, grade_fn=hook, normalizer=normalizer)
        sens1 = sensitivity.run(
            ArmBase(attainment=attainment, normalized=normalized, grade=grade1, seed=seed),
            tuple(schemes), sens_config, weights=cand_arm, grade_fn=hook,
            normalizer=normalizer)
        sens_delta = _sensitivity_delta(sens0, sens1)

    # ---- Step 7：两臂。sensitivity 载体按 C5 的举证制传入（没跑 Step 8 就是 None，
    #      两臂同规则，故准入差异只来自权重）----
    pool_config, params = _pool_args(config, optional['pool_params'])
    pool0, stats0 = pooling.build(score0, grade0, evidence, master, pool_config,
                                  sensitivity=sens0, params=params)
    pool1, stats1 = pooling.build(score1, grade1, evidence, master, pool_config,
                                  sensitivity=sens1, params=params)

    # ---- 归因（含 T-WIF-01 / T-WIF-05 的运行时自证）与六项差异 ----
    attribution, reconciliation, reallocated = _attribute(
        base, cand, score0, score_mid, score1, period)
    changes, unchanged = _grade_changes(grade0, grade1, score0, score1, attribution)
    redline_delta = _set_delta(_redline_set(rl_frame, grade0),
                               _redline_set(rl_frame, grade1), 'WHATIF_ONLY', 'BASELINE_ONLY')
    gate_delta = _set_delta(_admitted(pool0), _admitted(pool1), 'ADDED', 'REMOVED')

    found = set()
    if redline_delta:
        found.add(RC.CONFIG_INCONSISTENT.value)     # [L1370] / M10 治理用途 2
    if reallocated:
        found.add(RC.WEIGHT_REALLOCATED.value)      # [L954] 有效权重与名义权重不同
    if prev is None:
        found.add(RC.FIRST_PERIOD.value)            # 显式声明的首期，不静默
    if _grade_counts(grade1).get(NOT_ASSESSED, 0) or _grade_counts(grade0).get(NOT_ASSESSED, 0):
        found.add(RC.NOT_ASSESSED.value)            # [L1004] 单列披露
    readonly_proof = _readonly_after(input_dir, directory_hash, proof_before)
    return WhatifReport(
        run_id=run_id, period=period,
        candidate_weight_version_id=cand.weight_version_id,
        baseline_weight_version_id=base.weight_version_id, operator=operator,
        grade_changes=changes, unchanged_count=unchanged,
        occupancy_delta=_occupancy(grade0, grade1, stats0, stats1),
        redline_delta=redline_delta, evidence_gate_delta=gate_delta,
        attribution=attribution, reconciliation=reconciliation,
        sensitivity_delta=sens_delta,
        warnings=tuple(c for c in _WARNING_ORDER if c in found),
        refuse_signoff=bool(redline_delta), readonly_proof=readonly_proof)


def _readonly_before(input_dir, directory_hash):
    '''INV-2 自证的注入对校验 + 运行前哈希。半给（只给一个）即抛：不静默跳过自证。'''
    if (input_dir is None) != (directory_hash is None):
        raise WhatifInputError('INV-2 只读自证的 input_dir 与 directory_hash 必须**同时**'
                               + ' 给出（ORCH-27 D-A4-01：哈希只能注入，本模块不实现、'
                                 '不 import L6）')
    if input_dir is None:
        return None
    if not callable(directory_hash):
        raise WhatifInputError('directory_hash 必须是 callable（例如由 dsm.audit 的 '
                               'sha256_bytes / canonical_text / sha256_text 组合而成）')
    return directory_hash(input_dir)


def _readonly_after(input_dir, directory_hash, before):
    '''运行后再取一次哈希：与运行前不等 -> INV-2 被违反，抛而不是出报告。'''
    if before is None:
        return None
    after = directory_hash(input_dir)
    if after != before:
        raise WhatifReadonlyError('INV-2 只读自证失败：输入目录 ' + str(input_dir)
                                  + ' 在预演前后哈希不同（before=' + str(before)
                                  + ' after=' + str(after) + '）')
    return after


def signoff_verdict(report):
    '''[L1370] / M10 治理用途 2：redline_delta 非空 -> 建议**直接拒绝**签认并标注
    CONFIG_INCONSISTENT（红线判定与权重无关，出现变化只能是配置有误）。返回
    (是否拒绝, 标注的注册码)。红线不参与加权，所以正常预演恒为 (False, ())。'''
    delta = tuple(report.redline_delta)
    return (bool(delta), (RC.CONFIG_INCONSISTENT.value,) if delta else ())


def is_refused(report) -> bool:
    return signoff_verdict(report)[0]