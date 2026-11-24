'''dsm.attainment -- Step 1, the absolute attainment track (SDD 2.3.1 / 3.5.1).

This module is the ONLY source a grade floor may read from. A-4 hangs the
grading thresholds on attainment and on nothing else, so nothing below ever
consults normalize.py, and no number produced here depends on which other
strategies happen to share the pool (guarded by G-01).

The four formulas of the [L1136] closed set, dispatched on
MetricDictRow.attainment_formula:

    RATIO_DIRECT       actual / target                       (2.3.1 direction +1)
    INVERSE_RATIO      target / actual                       (2.3.1 direction -1)
    SHORTFALL_CLAMPED  the ratio above ordered by direction, then floored at 1
    INTERVAL           1 - distance_to_interval / interval_halfwidth

Every quotient goes through numeric.safe_div with an explicit on_zero (A-1) and
every result through numeric.clip(value, 0, attainment_cap) (A-3) and
numeric.q12, so R6 stays a single implementation point. A metric without a
target keeps attainment null: A-2 forbids substituting a pool mean or a
historical mean, and the absence is disclosed by NO_TARGET_VALUE instead.

The [L930] boundary line:

  * target missing -- or, for INTERVAL, bounds missing -- gives null,
    has_target False and NO_TARGET_VALUE
  * actual < 0 gives NEGATIVE_ACTUAL and then the metric's own missing_rule
    decides: ZERO -> 0, SKIP -> null, IMPUTE_MEDIAN -> median of the clean
    actuals of the same (version, period, metric), BLOCK -> raise
  * a zero denominator gives whatever the caller declared as on_zero, or null
    when on_zero is None. reason_code stays null on that path: the registry of
    3.3.2 carries no code for "quotient undefined" and spelling a literal here
    is forbidden (H-7)

reason_code precedence when several apply: NO_TARGET_VALUE > NEGATIVE_ACTUAL >
ATTAINMENT_CAPPED. capped_flag is independent of the precedence and means
exactly "the clip to attainment_cap changed the value"; the internal ceiling of
SHORTFALL_CLAMPED and the lower clip to 0 belong to the formula and do not set
it.

Governance parameters. AppConfig keeps the raw yaml trees (S1-T05 ruling 3) and
names no field, so the three values this module needs are read out of
eval_config by params_from_config() under the CFG_* keys below, or are handed in
explicitly as AttainmentParams. All three are required; nothing here carries a
business default (H-5).

The interval bounds of the INTERVAL formula have no column in the contract layer
(MetricDictRow carries a single target_value), so they arrive through the
intervals keyword, keyed by metric_id. Absent bounds are treated exactly like a
missing target rather than guessed.
'''
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.config import AppConfig
from dsm.models import (AttainmentFrame, AttainmentRow, MetricDictRow,
                        MetricFactRow, Ratio)
from dsm.numeric import D, ONE, ZERO, q12
from dsm.reason_codes import RC

# ---------------------------------------------------------------------------
# The eval_config path of params_from_config(). The SDD names attainment_cap as
# a governance parameter but gives no yaml key, so the spelling is pinned here
# once and nowhere else.
# ---------------------------------------------------------------------------
CFG_ATTAINMENT_KEY = 'attainment'
CFG_CAP_KEY = 'cap'
CFG_ON_ZERO_KEY = 'on_zero'
CFG_SIGNOFF_KEY = 'signed_off_statuses'
CFG_KEYS = (CFG_CAP_KEY, CFG_ON_ZERO_KEY, CFG_SIGNOFF_KEY)

FORMULA_RATIO = 'RATIO_DIRECT'
FORMULA_INVERSE = 'INVERSE_RATIO'
FORMULA_SHORTFALL = 'SHORTFALL_CLAMPED'
FORMULA_INTERVAL = 'INTERVAL'
FORMULAS = (FORMULA_RATIO, FORMULA_INVERSE, FORMULA_SHORTFALL, FORMULA_INTERVAL)

RULE_ZERO = 'ZERO'
RULE_SKIP = 'SKIP'
RULE_IMPUTE = 'IMPUTE_MEDIAN'
RULE_BLOCK = 'BLOCK'

TWO = D(2)


class AttainmentError(ValueError):
    '''Base class for every attainment contract violation.'''


class AttainmentConfigError(AttainmentError):
    '''A governance parameter this module needs is absent from eval_config.'''


class AttainmentBlockedError(AttainmentError):
    '''missing_rule BLOCK: a negative actual must stop the run, not be scored.'''


class AttainmentParams(BaseModel):
    '''The three governance values of 2.3.1 / 3.5.1, all of them mandatory.

    attainment_cap is the A-3 clip ceiling, on_zero is the A-1 answer to "what
    does a zero denominator mean" (None declares the quotient genuinely
    undefined, which keeps attainment null), and signed_off_statuses is the
    [L1141] set that decides the denominator of attainment_coverage --
    PENDING / REJECTED rows never score, so they never widen the coverage base.
    '''

    model_config = ConfigDict(frozen=True, extra='forbid')

    attainment_cap: Ratio
    on_zero: Ratio | None
    signed_off_statuses: tuple[str, ...]

    @model_validator(mode='after')
    def _check(self):
        if self.attainment_cap <= ZERO:
            raise ValueError('attainment_cap must be strictly positive')
        if not self.signed_off_statuses:
            raise ValueError('signed_off_statuses must not be empty')
        return self


def params_from_config(config: AppConfig) -> AttainmentParams:
    '''Read the governance block out of the raw eval_config tree, or refuse.

    Nothing is defaulted: an absent block, an absent key or a non-list of
    sign-off statuses all leave through AttainmentConfigError, because
    inventing a cap or a sign-off set would be inventing a business number
    (H-5) and would silently move every grade floor in the system.
    '''
    tree = config.eval_config
    block = tree.get(CFG_ATTAINMENT_KEY) if isinstance(tree, Mapping) else None
    where = 'eval_config.' + CFG_ATTAINMENT_KEY
    if not isinstance(block, Mapping):
        raise AttainmentConfigError('no ' + where + ' block in the configuration')
    missing = tuple(k for k in CFG_KEYS if k not in block)
    if missing:
        raise AttainmentConfigError(
            where + ' is missing: ' + ', '.join(missing))
    statuses = block[CFG_SIGNOFF_KEY]
    if isinstance(statuses, (str, bytes)) or not isinstance(statuses, Iterable):
        raise AttainmentConfigError(where + '.' + CFG_SIGNOFF_KEY + ' must be a list')
    return AttainmentParams(
        attainment_cap=block[CFG_CAP_KEY],
        on_zero=block[CFG_ON_ZERO_KEY],
        signed_off_statuses=tuple(str(s) for s in statuses))


# ---------------------------------------------------------------------------
# Index builders. Pure: no clock, no I/O, no global state (H-8).
# ---------------------------------------------------------------------------
def _index_metric_dict(metric_dict) -> dict:
    '''metric_id -> MetricDictRow, rejecting a mapping handed in as a sequence
    and a duplicated metric_id, both of which would make the join ambiguous.'''
    if isinstance(metric_dict, Mapping):
        metric_dict = tuple(metric_dict.values())
    out = {}
    for row in metric_dict:
        if not isinstance(row, MetricDictRow):
            raise AttainmentError(
                'metric_dict entries must be MetricDictRow, got '
                + type(row).__name__)
        if row.metric_id in out:
            raise AttainmentError('duplicate metric_id in metric_dict: ' + row.metric_id)
        out[row.metric_id] = row
    return out


def _index_intervals(intervals) -> dict:
    '''metric_id -> (low, high) as Decimals, reversed bounds rejected.'''
    if not intervals:
        return {}
    out = {}
    for metric_id, bounds in intervals.items():
        seq = tuple(bounds)
        if len(seq) != 2:
            raise AttainmentError(
                'interval for ' + str(metric_id) + ' needs exactly two bounds')
        low = D(seq[0])
        high = D(seq[1])
        if low > high:
            raise AttainmentError(
                'interval bounds are reversed for ' + str(metric_id))
        out[str(metric_id)] = (low, high)
    return out


def _clean_medians(facts, dictionary) -> dict:
    '''(version_id, period, metric_id) -> median of the non-negative actuals.

    Only built for metrics whose missing_rule is IMPUTE_MEDIAN, and only from
    the clean rows: a negative actual is the very thing being replaced, so it
    must not pull the median down with it. The map is computed before any row is
    evaluated, which keeps the result independent of the fact order.
    '''
    buckets = {}
    for fact in facts:
        metric = dictionary.get(fact.metric_id)
        if metric is None or metric.missing_rule != RULE_IMPUTE:
            continue
        value = D(fact.value)
        if value < ZERO:
            continue
        key = (fact.version_id, fact.period, fact.metric_id)
        buckets.setdefault(key, []).append(value)
    return {key: numeric.median(vals) for key, vals in buckets.items()}


# ---------------------------------------------------------------------------
# The four formulas.
# ---------------------------------------------------------------------------
def _ratio(metric, actual, target, params) -> Decimal | None:
    '''The direction decides who is the numerator, exactly as 2.3.1 writes it.'''
    if metric.direction == -1:
        return numeric.safe_div(target, actual, on_zero=params.on_zero)
    return numeric.safe_div(actual, target, on_zero=params.on_zero)


def _interval_value(actual, bounds, params) -> Decimal | None:
    '''1 - distance_to_interval / interval_halfwidth.

    A degenerate interval (low == high) has no halfwidth, so the formula is
    evaluated as its limit instead of dividing by zero: on the point it is 1,
    off the point it is 0. No on_zero policy is consulted for that, because the
    caller declared on_zero for a zero *actual*, not for a zero halfwidth.
    '''
    low, high = bounds
    half = q12((high - low) / TWO)
    distance = ZERO
    if actual < low:
        distance = low - actual
    elif actual > high:
        distance = actual - high
    if half <= ZERO:
        return ONE if distance <= ZERO else ZERO
    share = numeric.safe_div(distance, half, on_zero=params.on_zero)
    if share is None:
        return None
    return q12(ONE - share)


def _formula(metric, actual, target, bounds, params) -> Decimal | None:
    '''Dispatch on the [L1136] closed set. None means "genuinely undefined".'''
    kind = metric.attainment_formula
    if kind == FORMULA_RATIO:
        return numeric.safe_div(actual, target, on_zero=params.on_zero)
    if kind == FORMULA_INVERSE:
        return numeric.safe_div(target, actual, on_zero=params.on_zero)
    if kind == FORMULA_SHORTFALL:
        ratio = _ratio(metric, actual, target, params)
        if ratio is None:
            return None
        return ratio if ratio < ONE else q12(ONE)
    if kind == FORMULA_INTERVAL:
        return _interval_value(actual, bounds, params)
    raise AttainmentError('unknown attainment_formula: ' + str(kind))


def _apply_missing_rule(fact, metric, medians) -> Decimal | None:
    '''The [L930] treatment of a negative actual, per the metric's own rule.'''
    rule = metric.missing_rule
    if rule == RULE_ZERO:
        return ZERO
    if rule == RULE_SKIP:
        return None
    if rule == RULE_IMPUTE:
        return medians.get((fact.version_id, fact.period, fact.metric_id))
    if rule == RULE_BLOCK:
        raise AttainmentBlockedError(
            'metric ' + metric.metric_id + ' has a negative actual for strategy '
            + fact.strategy_id + ' and missing_rule BLOCK')
    raise AttainmentError('unknown missing_rule: ' + str(rule))


def _row(fact, metric, value, has_target, capped_flag, reason_code) -> AttainmentRow:
    '''One [L928] row. direction and target_source are copied from T2 so the
    output stays traceable to the signed dictionary ([L1139] target_basis).'''
    return AttainmentRow(
        strategy_id=fact.strategy_id,
        version_id=fact.version_id,
        period=fact.period,
        metric_id=fact.metric_id,
        attainment=value,
        direction=metric.direction,
        target_source=metric.target_basis,
        has_target=has_target,
        capped_flag=capped_flag,
        reason_code=reason_code)


def _evaluate(fact, metric, params, iv_index, medians):
    '''(AttainmentRow, counted_towards_coverage) for one fact row.'''
    if metric.attainment_formula == FORMULA_INTERVAL:
        bounds = iv_index.get(metric.metric_id)
        has_target = bounds is not None
    else:
        bounds = None
        has_target = metric.target_value is not None
    if not has_target:
        # A-2: null, never a substituted mean. This branch wins over a negative
        # actual, because with no target there is no attainment to speak of.
        return _row(fact, metric, None, False, False, RC.NO_TARGET_VALUE), False

    actual = D(fact.value)
    negative = actual < ZERO
    if negative:
        replaced = _apply_missing_rule(fact, metric, medians)
        if replaced is None:
            return _row(fact, metric, None, True, False, RC.NEGATIVE_ACTUAL), True
        actual = replaced

    raw = _formula(metric, actual, metric.target_value, bounds, params)
    if raw is None:
        # A zero denominator with on_zero=None: the quotient is undefined, and
        # the registry of 3.3.2 carries no code for it, so none is claimed.
        code = RC.NEGATIVE_ACTUAL if negative else None
        return _row(fact, metric, None, True, False, code), True

    capped = raw > params.attainment_cap
    value = numeric.clip(raw, ZERO, params.attainment_cap)
    if negative:
        code = RC.NEGATIVE_ACTUAL
    elif capped:
        code = RC.ATTAINMENT_CAPPED
    else:
        code = None
    return _row(fact, metric, value, True, capped, code), True


def _locator(row):
    '''The [L1149] grain, used as the one and only row order.'''
    return (row.strategy_id, row.version_id, row.period, row.metric_id)


def compute(facts: Sequence[MetricFactRow],
            metric_dict: Sequence[MetricDictRow] | Mapping[str, MetricDictRow],
            config: AppConfig | None = None,
            *,
            params: AttainmentParams | None = None,
            intervals: Mapping[str, Sequence] | None = None) -> AttainmentFrame:
    '''Step 1 of the scoring flow: the absolute attainment track ([L927]).

    Exactly one of config / params must be given: config is resolved through
    params_from_config, params is used as is. Asking for neither would mean
    inventing a cap, asking for both would leave two readings of the same run.

    Complexity is O(strategies x metrics), one pass over the long fact table.
    '''
    if (config is None) == (params is None):
        raise AttainmentError('pass exactly one of config or params')
    resolved = params if params is not None else params_from_config(config)

    dictionary = _index_metric_dict(metric_dict)
    iv_index = _index_intervals(intervals)
    fact_rows = tuple(facts)
    for fact in fact_rows:
        if not isinstance(fact, MetricFactRow):
            raise AttainmentError(
                'facts entries must be MetricFactRow, got ' + type(fact).__name__)
    medians = _clean_medians(fact_rows, dictionary)

    signed = resolved.signed_off_statuses
    rows = []
    numerator = {}
    for fact in fact_rows:
        metric = dictionary.get(fact.metric_id)
        if metric is None:
            # A fact outside the dictionary has no direction and no target, so
            # no row can be built for it at all; guessing one is forbidden.
            raise AttainmentError(
                'metric_facts references a metric outside metric_dict: '
                + fact.metric_id)
        row, counted = _evaluate(fact, metric, resolved, iv_index, medians)
        rows.append(row)
        if counted and metric.signoff_status in signed:
            numerator[fact.strategy_id] = numerator.get(fact.strategy_id, 0) + 1

    rows.sort(key=_locator)
    denominator = sum(1 for m in dictionary.values() if m.signoff_status in signed)
    coverage = {}
    for strategy_id in sorted(numerator.keys() | {f.strategy_id for f in fact_rows}):
        coverage[strategy_id] = numeric.safe_div(
            numerator.get(strategy_id, 0), denominator, on_zero=ZERO)
    return AttainmentFrame(rows=tuple(rows), attainment_coverage=coverage)
