'''Step 2 of the scoring flow: the relative normalisation track ([L935]-[L946]).

口径全部来自 digest M43，本模块不新增任何业务数值：

  * 三方法 min_max / z_score / rank_percentile（[L940]）由配置**显式**切换，
    绝不按数据形状隐式推断；三者的公式是教科书定义，不是业务参数。
  * 锚定集优先（[L941] / [L237]）：min_max 的 min/max、z_score 的 mean/sd、
    rank_percentile 的参考分布都优先取自 anchor_set 成员在**本期**的取值。
    ORCH-28 裁决 1：锚定参考尺**不按池裁剪**。[L237] 的锚定集是签认过的固定基准
    队列，把它窄化到「本池」会让单例池的锚定子集只剩策略自己那一个值，于是
    [L943] 的 sd = 0 判据作用在错误的统计量上，整条相对轨被判 INACTIVE、
    composite_relative 变 null（D-SEAM-01 的根因）。锚定集失效才回退当期池内统计，
    并且必须落码，不静默。
  * [L942] 池内归一约束的是**被标准化的对象**与**回退用的统计量**：分组键里带着
    pool_key，回退永远只取本池当期统计，任何两池都不会被合并成一个参照集
    （P-6 / G-02 禁混排照旧守护）。锚定集不是「他池」，它是 [L237] 的基准尺。
  * [L943] 的两条边界互相独立（ORCH-28 裁决 1 / 2）：sd = 0 判的是**实际用于
    标准化的那一组统计量**（锚定集有效时即锚定集统计量）；池内样本数 <
    min_pool_size 只 WARN + 落 SMALL_POOL，既不抛错、不置 null，也不剔除该策略。
    WARN 这一级由注册表给（reason_codes.severity(SMALL_POOL) = WARN），披露面在
    reports / audit 读 reason_code，本模块不另设告警通道（NormalizedFrame 无该列）。
  * 池内归一（[L942]）：**被标准化的行**按 (period, pool_key, metric_id) 分组，
    回退用的参考统计量只在组内计算，跨池混算在本模块里没有入口——组键里带着
    pool_key；锚定参考尺是上面那条 [L941] 的基准队列，不按池裁剪。
  * 零变异指标（[L943]）走 numeric.safe_div 的 on_zero 语义：on_zero 是 Decimal
    时保留行并落 INACTIVE_METRIC（由下游排名剔除），on_zero 是 None 时该行
    不存在（NormalizedRow.norm_value 非空，契约里没有可落空值的位置）。
  * 池内样本数 < min_pool_size（[L943]）落 SMALL_POOL。

[L945] 的关键约束是行为约束：本模块的输出只喂排名与相对轨综合分，等级门槛
只看绝对轨（grading.py 明确不读 NormalizedFrame），由 G-05 / P-4 守护。

reason_code 只有一个槽位，四条码的优先级固定为：
INACTIVE_METRIC > ANCHOR_SET_STALE > RANK_REVERSAL_RISK > SMALL_POOL。
其中 ANCHOR_SET_STALE 表示锚定集本身失效（为空 / 本期没有任何成员出值），
RANK_REVERSAL_RISK 表示锚定集有成员但参考尺退化（单元素、零变异）而回退。

digest 未给、因此作为入参并登记为缺口的口径（R-12）：
  * sd 的自由度（总体 / 样本）-> NormalizeParams.sd_dof；
  * 池归属 (biz_domain, evidence_class) 的来源（T1 strategy_master 与 S5
    evidence，两者都不在本包）-> pools 入参，缺一个策略就报错，不猜；
  * min_pool_size 与零分母语义 on_zero -> 治理值，无默认（H-5）。
'''
from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.config import AppConfig
from dsm.models import (AnchorSetDoc, AttainmentFrame, AttainmentRow,
                        MetricDictRow, NormalizationMethod, NormalizedFrame,
                        NormalizedRow, PoolKey, Ratio, StrictInt)
from dsm.numeric import D, ONE, ZERO
from dsm.reason_codes import RC

__all__ = [
    'METHODS', 'METHOD_MIN_MAX', 'METHOD_Z_SCORE', 'METHOD_RANK_PERCENTILE',
    'NormalizeError', 'NormalizeConfigError', 'NormalizeInputError',
    'NormalizeParams', 'params_from_config', 'compute',
]

# ---------------------------------------------------------------------------
# eval_config 路径。SDD 给了参数名但没给 yaml 键位，拼写在这里定一次。
# ---------------------------------------------------------------------------
CFG_NORMALIZE_KEY = 'normalize'
CFG_METHOD_KEY = 'method'
CFG_MIN_POOL_SIZE_KEY = 'min_pool_size'
CFG_ON_ZERO_KEY = 'on_zero'
CFG_SD_DOF_KEY = 'sd_dof'
CFG_KEYS = (CFG_METHOD_KEY, CFG_MIN_POOL_SIZE_KEY, CFG_ON_ZERO_KEY, CFG_SD_DOF_KEY)

METHOD_MIN_MAX = 'min_max'
METHOD_Z_SCORE = 'z_score'
METHOD_RANK_PERCENTILE = 'rank_percentile'
METHODS = (METHOD_MIN_MAX, METHOD_Z_SCORE, METHOD_RANK_PERCENTILE)

CODE_INACTIVE = RC.INACTIVE_METRIC.value
CODE_STALE = RC.ANCHOR_SET_STALE.value
CODE_REVERSAL = RC.RANK_REVERSAL_RISK.value
CODE_SMALL_POOL = RC.SMALL_POOL.value


class NormalizeError(ValueError):
    '''Base class for every normalize contract violation.'''


class NormalizeConfigError(NormalizeError):
    '''A governance parameter this module needs is absent from eval_config.'''


class NormalizeInputError(NormalizeError):
    '''facts / metric_dict / anchor_set / pools cannot be joined unambiguously.'''


class NormalizeParams(BaseModel):
    '''The four governance values of 3.5.2, all of them mandatory.

    method 是 [L940] 的三选一，必须由调用方显式给出；min_pool_size 是 [L943]
    的池样本下限；on_zero 是零分母语义（None 表示商本身无定义，行直接不存在）；
    sd_dof 是 z_score 标准差自由度，0 = 总体、1 = 样本——digest 未给，故为入参。
    '''

    model_config = ConfigDict(frozen=True, extra='forbid')

    method: NormalizationMethod
    min_pool_size: StrictInt
    on_zero: Ratio | None
    sd_dof: StrictInt

    @model_validator(mode='after')
    def _check(self):
        if self.min_pool_size < 1:
            raise ValueError('min_pool_size must be at least 1')
        if self.sd_dof not in (0, 1):
            raise ValueError('sd_dof must be 0 (population) or 1 (sample)')
        return self


def params_from_config(config: AppConfig) -> NormalizeParams:
    '''Read the governance block out of the raw eval_config tree, or refuse.

    什么都不默认：缺块、缺键、方法拼写不在三方法内，一律从
    NormalizeConfigError 出去。给方法编一个默认值等于替行方选了标准化口径。
    '''
    tree = config.eval_config
    block = tree.get(CFG_NORMALIZE_KEY) if isinstance(tree, Mapping) else None
    where = 'eval_config.' + CFG_NORMALIZE_KEY
    if not isinstance(block, Mapping):
        raise NormalizeConfigError('no ' + where + ' block in the configuration')
    missing = tuple(k for k in CFG_KEYS if k not in block)
    if missing:
        raise NormalizeConfigError(where + ' is missing: ' + ', '.join(missing))
    return NormalizeParams(
        method=block[CFG_METHOD_KEY],
        min_pool_size=block[CFG_MIN_POOL_SIZE_KEY],
        on_zero=block[CFG_ON_ZERO_KEY],
        sd_dof=block[CFG_SD_DOF_KEY])


# ---------------------------------------------------------------------------
# Index builders. Pure: no clock, no I/O, no global state (H-8).
# ---------------------------------------------------------------------------
def _index_metric_dict(metric_dict) -> dict:
    '''metric_id -> MetricDictRow; a duplicated id would make the join ambiguous.'''
    if isinstance(metric_dict, Mapping):
        metric_dict = tuple(metric_dict.values())
    index = {}
    for row in metric_dict:
        if not isinstance(row, MetricDictRow):
            raise NormalizeInputError(
                'metric_dict entries must be MetricDictRow, got '
                + type(row).__name__)
        if row.metric_id in index:
            raise NormalizeInputError(
                'metric_dict has a duplicated metric_id: ' + row.metric_id)
        index[row.metric_id] = row
    return index


def _fact_rows(facts) -> tuple:
    '''Step-1 output is the input of step 2: an AttainmentFrame or its rows.'''
    if isinstance(facts, AttainmentFrame):
        facts = facts.rows
    rows = tuple(facts)
    for row in rows:
        if not isinstance(row, AttainmentRow):
            raise NormalizeInputError(
                'facts entries must be AttainmentRow (step-1 output), got '
                + type(row).__name__)
    return rows


def _pool_of(pools, strategy_id) -> PoolKey:
    key = pools.get(strategy_id)
    if not isinstance(key, PoolKey):
        raise NormalizeInputError(
            'pools must map every strategy_id to a PoolKey, missing for: '
            + str(strategy_id))
    return key


def _locator(row):
    return (row.strategy_id, row.version_id, row.period, row.metric_id)


# ---------------------------------------------------------------------------
# The three reference scales. Each returns None when the reference set cannot
# serve as a scale at all, which is the [L943] zero-variance case: the metric
# has no discriminating power, so it is INACTIVE rather than rescaled by a
# second method nobody asked for (硬点 4).
# ---------------------------------------------------------------------------
def _min_max_scale(ref: Sequence[Decimal]):
    lo = min(ref)
    hi = max(ref)
    if hi - lo <= numeric.TOL:
        return None
    return (lo, hi - lo)


def _z_scale(ref: Sequence[Decimal], sd_dof: int):
    m = numeric.mean(ref)
    ss = sum(((v - m) * (v - m) for v in ref), ZERO)
    denom = D(len(ref)) - D(sd_dof)
    if denom <= ZERO:
        return None
    var = numeric.safe_div(ss, denom, on_zero=None)
    if var is None:
        return None
    sd = numeric.sqrt(var)
    if sd <= numeric.TOL:
        return None
    return (m, sd)


def _rank_scale(ref: Sequence[Decimal]):
    if max(ref) - min(ref) <= numeric.TOL:
        return None
    return tuple(ref)


def _build_scale(method: str, ref: Sequence[Decimal], sd_dof: int):
    if not ref:
        return None
    if method == METHOD_MIN_MAX:
        return _min_max_scale(ref)
    if method == METHOD_Z_SCORE:
        return _z_scale(ref, sd_dof)
    return _rank_scale(ref)


def _norm_value(method: str, scale, x: Decimal, on_zero):
    '''One normalised value. Every division goes through numeric.safe_div, so
    a zero denominator always answers with the configured on_zero semantics
    and never with a silently invented number (V-9).
    '''
    if scale is None:
        # INACTIVE: the quotient is 0/0 by construction, the answer is on_zero.
        return numeric.safe_div(ZERO, ZERO, on_zero=on_zero)
    if method == METHOD_MIN_MAX:
        lo, width = scale
        return numeric.safe_div(x - lo, width, on_zero=on_zero)
    if method == METHOD_Z_SCORE:
        m, sd = scale
        return numeric.safe_div(x - m, sd, on_zero=on_zero)
    # rank_percentile: the position of x inside the reference distribution.
    # rank_average(ref + [x]) of the appended x is #less + 1 + #equal/2, so
    # (rank - 1) / len(ref) is exactly (#less + 0.5*#equal) / len(ref).
    combined = list(scale)
    combined.append(x)
    rank = numeric.rank_average(combined)[len(combined) - 1]
    return numeric.safe_div(rank - ONE, D(len(scale)), on_zero=on_zero)


def _choose_scale(pool_vals, anchor_vals, method: str, sd_dof: int):
    '''Anchor first ([L941]), current-period pool only as a disclosed fallback.

    pool_vals are the attainment values of ONE (period, pool, metric) group;
    anchor_vals are the anchor_set members' values for the same
    (period, metric) -- the whole signed-off cohort, deliberately NOT narrowed
    to the pool (ORCH-28 ruling 1, see the module docstring). Narrowing it
    would make the [L943] sd = 0 test run on the pool's own single value in a
    singleton pool, i.e. on the wrong statistic set, and would drop the whole
    relative track instead of ranking it against the benchmark scale.

    Returns (scale, anchor_used, fallback_code); scale is None when even the
    pool cannot serve, i.e. the metric is INACTIVE ([L943]).
    '''
    if anchor_vals:
        scale = _build_scale(method, anchor_vals, sd_dof)
        if scale is not None:
            return scale, True, None
        # 锚定集有成员但参考尺退化（单元素 / 零变异）-> 回退并标注秩反转风险。
        # 回退只取本池当期统计（[L942]），此时单例池才会 sd = 0 -> INACTIVE。
        return _build_scale(method, pool_vals, sd_dof), False, CODE_REVERSAL
    # 锚定集为空，或本期一个成员都没有出值 -> 锚定集失效（[L239]）。
    return _build_scale(method, pool_vals, sd_dof), False, CODE_STALE


def _reason_code(inactive: bool, fallback, small_pool: bool):
    '''Fixed precedence for the single reason_code slot of NormalizedRow.'''
    if inactive:
        return CODE_INACTIVE
    if fallback is not None:
        return fallback
    if small_pool:
        return CODE_SMALL_POOL
    return None


def compute(facts: Sequence[AttainmentRow] | AttainmentFrame,
            metric_dict: Sequence[MetricDictRow] | Mapping[str, MetricDictRow],
            anchor_set: AnchorSetDoc,
            config: AppConfig | None = None,
            *,
            params: NormalizeParams | None = None,
            pools: Mapping[str, PoolKey] | None = None) -> NormalizedFrame:
    '''Step 2: the relative track ([L939]). Ranking and the relative composite
    only ([L945]) -- nothing here decides a grade floor.

    Exactly one of config / params must be given, exactly like step 1: asking
    for neither would mean inventing a method, asking for both would leave two
    readings of the same run. pools is mandatory because the pool key
    (biz_domain x evidence_class) comes from T1 and from the S5 evidence layer,
    neither of which this module may read.

    Complexity is O(rows) plus one reference-scale build per
    (period, pool, metric) group.
    '''
    if (config is None) == (params is None):
        raise NormalizeError('pass exactly one of config or params')
    resolved = params if params is not None else params_from_config(config)
    if not isinstance(anchor_set, AnchorSetDoc):
        raise NormalizeInputError(
            'anchor_set must be an AnchorSetDoc (an empty strategy_ids tuple is '
            'the explicit "no anchor" case), got '
            + type(anchor_set).__name__)
    if not isinstance(pools, Mapping):
        raise NormalizeInputError('pools must be a Mapping of strategy_id -> PoolKey')

    dictionary = _index_metric_dict(metric_dict)
    rows = _fact_rows(facts)
    anchor_ids = frozenset(anchor_set.strategy_ids)

    groups: dict = {}
    members_of_pool: dict = {}
    anchor_ref: dict = {}
    for row in rows:
        metric = dictionary.get(row.metric_id)
        if metric is None:
            raise NormalizeInputError(
                'facts references a metric outside metric_dict: ' + row.metric_id)
        if int(metric.direction) != int(row.direction):
            raise NormalizeInputError(
                'direction of ' + row.metric_id + ' disagrees with metric_dict')
        pool_key = _pool_of(pools, row.strategy_id)
        members_of_pool.setdefault((row.period, pool_key), []).append(row.strategy_id)
        if row.attainment is None:
            # Step 1 already disclosed the absence with its own code; a value
            # that does not exist cannot be normalised and is not imputed.
            continue
        groups.setdefault((row.period, pool_key, row.metric_id), []).append(row)
        if row.strategy_id in anchor_ids:
            # [L941] 锚定参考尺：同期同指标的**全部**锚定集成员取值，不按池裁剪
            # （ORCH-28 裁决 1）。排序只为确定性，min/max/mean/sd 与序无关。
            anchor_ref.setdefault((row.period, row.metric_id), []).append(
                D(row.attainment))
    for ref_values in anchor_ref.values():
        ref_values.sort()

    sample_count = {k: len(set(v)) for k, v in members_of_pool.items()}
    out = []
    for (period, pool_key, metric_id), members in groups.items():
        values = [D(r.attainment) for r in members]
        scale, anchor_used, fallback = _choose_scale(
            values, anchor_ref.get((period, metric_id), ()),
            resolved.method, resolved.sd_dof)
        code = _reason_code(scale is None, fallback,
                            sample_count[(period, pool_key)] < resolved.min_pool_size)
        for row in members:
            value = _norm_value(resolved.method, scale, D(row.attainment),
                                resolved.on_zero)
            if value is None:
                # on_zero=None: the quotient is genuinely undefined, so there is
                # no row -- the metric is dropped instead of being zero-filled.
                continue
            out.append(NormalizedRow(
                strategy_id=row.strategy_id, version_id=row.version_id,
                period=row.period, metric_id=row.metric_id, pool_key=pool_key,
                norm_value=value, method=resolved.method,
                anchor_used=anchor_used, reason_code=code))
    out.sort(key=_locator)
    return NormalizedFrame(rows=tuple(out))
