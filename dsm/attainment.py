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

The boundary line, and the TWO triggers of the [L1134] missing_rule closed
set. A metric can be absent in two ways and the original text names both, so
both are dispatched -- answering only one of them is what made the four
branches collapse into each other (G-09 [L1411]):

  * target missing -- or, for INTERVAL, bounds missing -- gives null,
    has_target False and NO_TARGET_VALUE. This outranks both triggers below:
    [L451] keeps a metric without a target out of the absolute track, so no
    missing_rule is consulted for it and not even a BLOCK sinks the strategy.
  * TRIGGER_NEGATIVE, [L930]: a negative actual is recorded as
    NEGATIVE_ACTUAL and then handled per missing_rule. The row exists, so it
    stays and discloses
    NEGATIVE_ACTUAL. ZERO -> attainment 0; SKIP -> attainment null;
    IMPUTE_MEDIAN -> the formula run on the imputed median; BLOCK -> raise
    AttainmentBlockedError and stop the run.
  * TRIGGER_ROW_MISSING, [L1156] verbatim: the long table shows a missing
    metric as an absent row, not as an empty column. ZERO -> a row whose
    attainment is 0 (ji ru 0, [L1411]); SKIP -> no row, the metric drops out
    and [L954] renormalises inside its dimension; IMPUTE_MEDIAN -> a row from
    the imputed median; BLOCK -> the whole (strategy, version, period) yields no
    row at all, because [L1411] says BLOCK leaves that strategy without a score
    and aggregate.compose builds one ScoreRow per key it finds in this frame.
    The suppression is not silent: it leaves the module as a [L1051] item-13
    DowngradeAction on AttainmentResult.downgrades carrying the registered
    NOT_ASSESSED code.
  * a zero denominator gives whatever the caller declared as on_zero, or null
    when on_zero is None. reason_code stays null on that path: the registry of
    3.3.2 carries no code for "quotient undefined" and spelling a literal here
    is forbidden (H-7). The same holds for a synthesized ZERO / IMPUTE_MEDIAN
    row: 3.3.2 carries no code for a missing fact row handled by missing_rule
    either, and borrowing MISSING_RATE_WARN would claim a missing-rate threshold
    this module never evaluates, so their reason_code stays null and the
    registry gap is reported instead of papered over.

ZERO means "the attainment counts as 0" on BOTH triggers, never "the actual
counts as 0": on a direction -1 metric the latter runs target / 0, which lands
on on_zero or on null, and a null is indistinguishable from SKIP -- exactly the
collapse G-09 forbids.

The IMPUTE_MEDIAN sample. [L1134] names the rule and states no sample scope, so
the scope is an explicit input (impute_scope) rather than a guess (V-14).
ALL_ROWS takes every non-negative actual of the same (version_id, period,
metric_id) -- the reading G-09's hand computation pins: 10 values in the v1
bucket, the v2 row of the same metric outside it. SIGNED_OFF_ONLY drops the
metrics whose signoff_status is not in signed_off_statuses ([L1141]), which for
a single-metric sample means an unsigned metric has no sample and cannot be
imputed. Negative actuals never enter the sample on either scope: a negative is
the very thing being replaced. The median is Decimal end to end (V-9,
numeric.median), never a float mean.

WHICH SET that median is read from is a second question, and [L1134] does not
answer it either: the line only enumerates the four rule names (ZERO / SKIP /
IMPUTE_MEDIAN / BLOCK) and says not one word about the reference set. That is an
original-text gap, filed as ERRATUM-08, so the basis level of the answer below is
`derived:` and NOT `verbatim:` -- nothing here may be quoted as an explicit
requirement of the design doc. It is derived from two things that ARE in the
text: [L941], which already makes anchor_set the preferred reference for min/max
and mean/sd, and the invariance [L1407] (G-05), [L1428] (P-4) and [L1500] (V-7)
demand -- appending a strategy must leave every existing strategy's norm,
composite and grade untouched. A median read off the current-period pool can
never satisfy that: any appended row can move the pool median and with it the
value an existing strategy's hole is imputed with, which then rewrites its
attainment, norm, composite and grade. So the IMPUTE_MEDIAN reference set is the
anchor_set first (compute(anchor_set=...)), and the current-period pool only as
the fallback for a bucket the anchor set cannot serve at all -- a fallback that
is disclosed as ANCHOR_SET_STALE rather than taken silently (V-14).
anchor_set=None means the caller declared no anchor document at all; nothing can
then be "stale", so the pool stays the reference set exactly as it was, with no
code invented for it (H-7). Handing the real anchor document to every call site
is chain wiring and is not something this module may invent on its own.

A synthesized cell is not an observation, so it never widens
attainment_coverage: [L928] counts what the strategy reported with a target
over the signed-off metrics.

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
from typing import Iterable, Mapping, NamedTuple, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.config import AppConfig
from dsm.models import (AnchorSetDoc, AttainmentFrame, AttainmentRow,
                        DowngradeAction, MetricDictRow, MetricFactRow, Ratio)
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
RULES = (RULE_ZERO, RULE_SKIP, RULE_IMPUTE, RULE_BLOCK)

# The two ways a metric can be absent, both of them original text: [L930] for a
# negative actual, [L1156] for a row the long table does not carry at all.
# The value of TRIGGER_NEGATIVE is deliberately NOT spelled like the registered
# reason_code NEGATIVE_ACTUAL: P-8 forbids a bare literal equal to a registry
# code outside a reason_code position, and this is a dispatch tag, not a code.
TRIGGER_NEGATIVE = 'ACTUAL_IS_NEGATIVE'
TRIGGER_ROW_MISSING = 'ROW_MISSING'
TRIGGERS = (TRIGGER_NEGATIVE, TRIGGER_ROW_MISSING)

# What a rule decided. One flat set of actions, so the dispatch table inside
# _apply_missing_rule is the single place a rule name turns into behaviour.
ACT_ZERO = 'ZERO_ATTAINMENT'           # the metric counts as attainment 0
ACT_NULL_ROW = 'NULL_ROW'              # the row stays, its attainment is null
ACT_DROP_ROW = 'DROP_ROW'              # no row at all, [L954] renormalises
ACT_IMPUTE = 'IMPUTE_ACTUAL'           # the formula runs on the imputed median
ACT_BLOCK_STRATEGY = 'BLOCK_STRATEGY'  # this strategy yields no score ([L1411])

# IMPUTE_MEDIAN sample scope. [L1134] names the rule but no scope, so it is an
# input, never a default (V-14); see the module docstring.
IMPUTE_SCOPE_ALL = 'ALL_ROWS'
IMPUTE_SCOPE_SIGNED = 'SIGNED_OFF_ONLY'
IMPUTE_SCOPES = (IMPUTE_SCOPE_ALL, IMPUTE_SCOPE_SIGNED)

TWO = D(2)


class MissingRuleOutcome(NamedTuple):
    '''The decision of _apply_missing_rule: one ACT_* action plus, for
    ACT_IMPUTE, the Decimal median the formula has to run on.'''

    action: str
    actual: Decimal | None = None


class AttainmentError(ValueError):
    '''Base class for every attainment contract violation.'''


class AttainmentConfigError(AttainmentError):
    '''A governance parameter this module needs is absent from eval_config.'''


class AttainmentBlockedError(AttainmentError):
    '''missing_rule BLOCK: a negative actual must stop the run, not be scored.'''


class AttainmentImputeError(AttainmentError):
    '''IMPUTE_MEDIAN with no clean sample to impute from.

    Falling back to SKIP would be a silent degradation (V-14), and 3.3.2
    registers no code an empty imputation could be disclosed on, so a missing
    row refuses to produce a number at all.'''


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


class AttainmentResult(AttainmentFrame):
    '''The [L928] frame plus the disclosure a BLOCK suppression needs.

    AttainmentFrame carries rows and coverage only, and a blocked strategy has
    no rows at all ([L1411]: BLOCK leaves that strategy without a score), so the
    frame on its own cannot say why a strategy vanished. That would be a silent
    degradation (V-14), and H-6 refuses to let a removal go unrecorded.
    DowngradeAction is the [L1051] item-13 landing point built for exactly that,
    so the notices ride here.

    This IS an AttainmentFrame -- no field of the frozen contract is touched,
    renamed or reinterpreted, and every consumer that types its input as
    AttainmentFrame (normalize, aggregate, grading, whatif, reports) keeps
    working unchanged. Whether the field belongs on AttainmentFrame itself is a
    contract question under R-15 and is registered as a gap, not decided here.
    '''

    downgrades: tuple[DowngradeAction, ...] = ()


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


def _clean_medians(facts, dictionary, scope=IMPUTE_SCOPE_ALL, signed=(),
                   only_ids=None) -> dict:
    '''(version_id, period, metric_id) -> median of the non-negative actuals.

    Only built for metrics whose missing_rule is IMPUTE_MEDIAN, and only from
    the clean rows: a negative actual is the very thing being replaced, so it
    must not pull the median down with it. The map is computed before any row is
    evaluated, which keeps the result independent of the fact order, and every
    step of it is Decimal (numeric.median, V-9): a float mean of two Decimals
    does not survive a 1e-12 comparison.

    scope is the [L1134] gap made explicit instead of guessed. ALL_ROWS samples
    every non-negative actual of that metric; SIGNED_OFF_ONLY samples only the
    metrics signed off per [L1141], which for a single-metric sample leaves an
    unsigned metric with no sample at all. Rows of a strategy a BLOCK later
    suppresses stay in the sample on both scopes: the sample is a property of
    the metric and the period, and G-09's hand computation counts them.

    only_ids restricts the sample to one set of strategy_ids and is how the
    anchor_set reference sample is built (ORCH-37 ruling 8; basis level
    `derived:` -- [L1134] names IMPUTE_MEDIAN and says nothing about which set
    the median is read from, ERRATUM-08; see the module docstring). None samples
    every strategy, i.e. the current-period pool, which is the fallback. The
    bucket grain, the sign-off filter and the clean-row filter are deliberately
    IDENTICAL for both samples: only the membership changes, so [L1134]'s scope
    semantics and G-09's hand computation stay exactly as pinned and the two
    samples stay comparable.
    '''
    if scope not in IMPUTE_SCOPES:
        raise AttainmentError('unknown impute_scope: ' + str(scope))
    buckets = {}
    for fact in facts:
        metric = dictionary.get(fact.metric_id)
        if metric is None or metric.missing_rule != RULE_IMPUTE:
            continue
        if scope == IMPUTE_SCOPE_SIGNED and metric.signoff_status not in signed:
            continue
        if only_ids is not None and fact.strategy_id not in only_ids:
            # Outside the reference set: its actual must not move the median
            # another strategy's hole is imputed from. This is the whole point of
            # the anchor-first reading -- an appended strategy is not a member,
            # so it cannot reach an existing strategy's imputed value ([L1407]).
            continue
        value = D(fact.value)
        if value < ZERO:
            continue
        key = (fact.version_id, fact.period, fact.metric_id)
        buckets.setdefault(key, []).append(value)
    return {key: numeric.median(vals) for key, vals in buckets.items()}


class _MedianTable:
    '''Which median one IMPUTE_MEDIAN cell runs on: anchor_set first, pool second.

    ORCH-37 ruling 8. Basis level `derived:`, NOT `verbatim:` -- [L1134] only
    enumerates the four missing_rule names and says not one word about the
    reference set the median comes from, so this is an original-text gap filed as
    ERRATUM-08 and needs an SDD erratum plus business sign-off. It is derived
    from [L941] (anchor_set is already the preferred reference for min/max and
    mean/sd -- same reading, same governance philosophy: a fixed reference scale
    is what stops a rank reversal) and from the invariance [L1407] (G-05) /
    [L1428] (P-4) / [L1500] (V-7) impose. A pool-sourced median moves whenever a
    strategy is appended, so it structurally cannot leave an existing strategy's
    imputed hole -- and therefore its attainment, norm, composite and grade --
    untouched. The anchor set is signed off and frozen for its effective period
    ([L1213], RK-8), which is what makes it usable as that fixed scale.

    `declared` separates two situations, and only the second is a degradation:

      * anchor_set=None -- the caller declared no anchor document at all. There
        is nothing that could be stale, so the pool is the reference set exactly
        as it was before this ruling and no code is invented for it (H-7).
      * an anchor document that cannot serve one bucket -- it has no member, or
        no member with a clean non-negative actual, in that (version_id, period,
        metric_id). That IS the "[L941] anchor set failed" case: the pool takes
        over and the takeover is recorded on `pool_fallbacks` so compute() can
        disclose it as ANCHOR_SET_STALE (V-14: never a silent fallback).

    Expiry is deliberately NOT judged here: effective_from / effective_to
    ([L1213]) can only be read against an as-of date, and this module reads no
    clock (H-8); normalize.py, the [L941] precedent, does not judge expiry
    either. "Stale" here means "cannot serve this bucket", the same reading
    normalize uses for an anchor set with no member reporting this period.

    Read-only apart from `pool_fallbacks`. `get` keeps the plain-mapping call
    signature _apply_missing_rule already used, so the [L1134] dispatch table --
    the one place a rule name turns into behaviour -- is untouched.
    '''

    def __init__(self, pool: Mapping, anchor: Mapping | None, declared: bool):
        self._pool = pool
        self._anchor = {} if anchor is None else anchor
        self._declared = declared
        self.pool_fallbacks = []      # bucket keys, in first-use order

    def get(self, key):
        '''The Decimal median for one (version_id, period, metric_id), or None.'''
        if not self._declared:
            return self._pool.get(key)
        if key in self._anchor:
            return self._anchor[key]
        value = self._pool.get(key)
        if value is not None and key not in self.pool_fallbacks:
            self.pool_fallbacks.append(key)
        return value


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


def _apply_missing_rule(rule, trigger, locator, medians) -> MissingRuleOutcome:
    '''The [L1134] closed set, dispatched for BOTH ways a metric can be absent.

    rule is the metric's own missing_rule, trigger one of TRIGGERS and locator
    the [L1149] key (strategy_id, version_id, period, metric_id) the rule is
    applied to. Two triggers x four rules, decided in this one table and nowhere
    else -- that is what keeps the four branches from collapsing into one
    another (G-09 [L1411]). A rule name outside the closed set raises: falling
    back to SKIP would be a silent degradation (V-14).
    '''
    if trigger not in TRIGGERS:
        raise AttainmentError('unknown missing_rule trigger: ' + str(trigger))
    if rule not in RULES:
        raise AttainmentError('unknown missing_rule: ' + str(rule))
    strategy_id, version_id, period, metric_id = locator

    if rule == RULE_ZERO:
        # Counted as 0: the ATTAINMENT is 0. Substituting 0 for the actual
        # instead would run target / 0 on a direction -1 metric and land on
        # on_zero or on null -- and null is indistinguishable from SKIP.
        return MissingRuleOutcome(ACT_ZERO)

    if rule == RULE_SKIP:
        # A negative actual sits on a row that exists and discloses
        # NEGATIVE_ACTUAL, so the row stays with a null attainment. A missing
        # row has nothing to disclose on: it stays missing, the metric drops out
        # and [L954] renormalises the weights inside its dimension.
        return MissingRuleOutcome(ACT_NULL_ROW if trigger == TRIGGER_NEGATIVE
                                  else ACT_DROP_ROW)

    if rule == RULE_IMPUTE:
        median = medians.get((version_id, period, metric_id))
        if median is not None:
            return MissingRuleOutcome(ACT_IMPUTE, median)
        if trigger == TRIGGER_NEGATIVE:
            # The row is still there and still says NEGATIVE_ACTUAL, so the
            # failed imputation stays disclosed instead of being swallowed.
            return MissingRuleOutcome(ACT_NULL_ROW)
        raise AttainmentImputeError(
            'metric ' + metric_id + ' has no clean sample in (' + version_id
            + ', ' + period + ') to impute the missing row of strategy '
            + strategy_id + ' from, and IMPUTE_MEDIAN may not degrade to SKIP')

    if trigger == TRIGGER_NEGATIVE:
        raise AttainmentBlockedError(
            'metric ' + metric_id + ' has a negative actual for strategy '
            + strategy_id + ' and missing_rule BLOCK')
    # [L1411]: the caller drops every row of this (strategy, version, period)
    # and records NOT_ASSESSED on the way out.
    return MissingRuleOutcome(ACT_BLOCK_STRATEGY)


def _row(locator, metric, value, has_target, capped_flag, reason_code) -> AttainmentRow:
    '''One [L928] row. direction and target_source are copied from T2 so the
    output stays traceable to the signed dictionary ([L1139] target_basis). The
    locator is the [L1149] key rather than a MetricFactRow, because a cell the
    long table never carried has no fact row to read those four from.'''
    strategy_id, version_id, period, metric_id = locator
    return AttainmentRow(
        strategy_id=strategy_id,
        version_id=version_id,
        period=period,
        metric_id=metric_id,
        attainment=value,
        direction=metric.direction,
        target_source=metric.target_basis,
        has_target=has_target,
        capped_flag=capped_flag,
        reason_code=reason_code)


def _target(metric, iv_index):
    '''(bounds, has_target) per [L451]: an INTERVAL metric is targeted by its
    bounds, every other formula by MetricDictRow.target_value.'''
    if metric.attainment_formula == FORMULA_INTERVAL:
        bounds = iv_index.get(metric.metric_id)
        return bounds, bounds is not None
    return None, metric.target_value is not None


def _evaluate_fact(fact, metric, params, iv_index, medians):
    '''(AttainmentRow, counted_towards_coverage) for one fact row.'''
    locator = _locator(fact)
    bounds, has_target = _target(metric, iv_index)
    if not has_target:
        # A-2: null, never a substituted mean. This branch wins over a negative
        # actual, because with no target there is no attainment to speak of.
        return _row(locator, metric, None, False, False, RC.NO_TARGET_VALUE), False

    actual = D(fact.value)
    negative = actual < ZERO
    if negative:
        outcome = _apply_missing_rule(metric.missing_rule, TRIGGER_NEGATIVE,
                                      locator, medians)
        if outcome.action == ACT_ZERO:
            return _row(locator, metric, ZERO, True, False, RC.NEGATIVE_ACTUAL), True
        if outcome.action == ACT_NULL_ROW:
            return _row(locator, metric, None, True, False, RC.NEGATIVE_ACTUAL), True
        actual = outcome.actual

    raw = _formula(metric, actual, metric.target_value, bounds, params)
    if raw is None:
        # A zero denominator with on_zero=None: the quotient is undefined, and
        # the registry of 3.3.2 carries no code for it, so none is claimed.
        code = RC.NEGATIVE_ACTUAL if negative else None
        return _row(locator, metric, None, True, False, code), True

    capped = raw > params.attainment_cap
    value = numeric.clip(raw, ZERO, params.attainment_cap)
    if negative:
        code = RC.NEGATIVE_ACTUAL
    elif capped:
        code = RC.ATTAINMENT_CAPPED
    else:
        code = None
    return _row(locator, metric, value, True, capped, code), True


def _evaluate_missing(locator, metric, params, iv_index, medians):
    '''(AttainmentRow or None, blocked) for a cell the long table never carried.

    counted_towards_coverage is deliberately not part of the answer: a
    synthesized cell is not an observation, so it never widens the [L928]
    coverage numerator -- coverage stays "what the strategy reported with a
    target over the signed-off metrics".
    '''
    bounds, has_target = _target(metric, iv_index)
    if not has_target:
        # A-2 / [L451] outrank the missing_rule here for the same reason as on
        # the fact path: with no target there is no attainment to speak of, so
        # not even a BLOCK may sink the strategy over this cell.
        return _row(locator, metric, None, False, False, RC.NO_TARGET_VALUE), False

    outcome = _apply_missing_rule(metric.missing_rule, TRIGGER_ROW_MISSING,
                                  locator, medians)
    if outcome.action == ACT_BLOCK_STRATEGY:
        return None, True
    if outcome.action == ACT_DROP_ROW:
        # SKIP: no row, so the metric drops out of its dimension and [L954]
        # renormalises the remaining w_j -- the observable G-09 asks for.
        return None, False
    if outcome.action == ACT_ZERO:
        # reason_code stays null: 3.3.2 carries no code for a missing row
        # counted as zero and spelling a literal here is forbidden (H-7). The
        # registry gap is reported; the zero itself is not -- G-09 needs both
        # the row and the 0 on it.
        return _row(locator, metric, ZERO, True, False, None), False

    raw = _formula(metric, outcome.actual, metric.target_value, bounds, params)
    if raw is None:
        return _row(locator, metric, None, True, False, None), False
    capped = raw > params.attainment_cap
    value = numeric.clip(raw, ZERO, params.attainment_cap)
    code = RC.ATTAINMENT_CAPPED if capped else None
    return _row(locator, metric, value, True, capped, code), False


def _locator(row):
    '''The [L1149] grain, used as the one and only row order.'''
    return (row.strategy_id, row.version_id, row.period, row.metric_id)


def compute(facts: Sequence[MetricFactRow],
            metric_dict: Sequence[MetricDictRow] | Mapping[str, MetricDictRow],
            config: AppConfig | None = None,
            *,
            params: AttainmentParams | None = None,
            intervals: Mapping[str, Sequence] | None = None,
            impute_scope: str = IMPUTE_SCOPE_ALL,
            anchor_set: AnchorSetDoc | None = None) -> AttainmentResult:
    '''Step 1 of the scoring flow: the absolute attainment track ([L927]).

    Exactly one of config / params must be given: config is resolved through
    params_from_config, params is used as is. Asking for neither would mean
    inventing a cap, asking for both would leave two readings of the same run.

    The grid is the [L1149] locator crossed with the dictionary over every
    (strategy_id, version_id, period) the fact table actually carries, so a cell
    with no row is the missing metric [L1156] describes and goes through
    _apply_missing_rule exactly like a negative actual does. Nothing is invented
    the other way round: a strategy, version or period the table does not carry
    stays absent from the output.

    impute_scope picks the IMPUTE_MEDIAN sample (module docstring); it is an
    input because [L1134] states no scope and guessing one is forbidden (V-14).

    anchor_set picks the IMPUTE_MEDIAN REFERENCE SET (ORCH-37 ruling 8, basis
    level `derived:` -- [L1134] says nothing about it, ERRATUM-08). Keyword-only
    and optional, so no existing call site changes meaning: an AnchorSetDoc makes
    the median come from the anchor members first, with the current-period pool
    only as the fallback for a bucket the anchor set cannot serve, disclosed as
    ANCHOR_SET_STALE on AttainmentResult.downgrades; None keeps the pool as the
    reference set and invents no code (_MedianTable). Same reading as [L941] and
    as normalize.compute, which takes the anchor document as a mandatory
    positional -- here it cannot be mandatory without rewriting every call site,
    which is chain wiring and outside this module's write set.

    Complexity is O(strategies x metrics), one pass over the long fact table.
    '''
    if (config is None) == (params is None):
        raise AttainmentError('pass exactly one of config or params')
    if impute_scope not in IMPUTE_SCOPES:
        raise AttainmentError('unknown impute_scope: ' + str(impute_scope))
    resolved = params if params is not None else params_from_config(config)

    dictionary = _index_metric_dict(metric_dict)
    iv_index = _index_intervals(intervals)
    fact_rows = tuple(facts)
    for fact in fact_rows:
        if not isinstance(fact, MetricFactRow):
            raise AttainmentError(
                'facts entries must be MetricFactRow, got ' + type(fact).__name__)
    anchor_ids = None
    if anchor_set is not None:
        if not isinstance(anchor_set, AnchorSetDoc):
            # An EMPTY strategy_ids tuple is the explicit "no anchor" case and is
            # a declared anchor set (normalize.compute reads it the same way, and
            # it must be allowed to reach the ANCHOR_SET_STALE fallback instead
            # of being refused). Anything that is not an AnchorSetDoc at all is a
            # caller error: guessing membership would be inventing a reference
            # set (V-14).
            raise AttainmentError(
                'anchor_set must be an AnchorSetDoc or None, got '
                + type(anchor_set).__name__)
        anchor_ids = frozenset(anchor_set.strategy_ids)
    pool_medians = _clean_medians(fact_rows, dictionary, impute_scope,
                                  resolved.signed_off_statuses)
    anchor_medians = None if anchor_ids is None else _clean_medians(
        fact_rows, dictionary, impute_scope, resolved.signed_off_statuses,
        only_ids=anchor_ids)
    medians = _MedianTable(pool_medians, anchor_medians, anchor_ids is not None)

    signed = resolved.signed_off_statuses
    rows = []
    numerator = {}       # (strategy, version, period) -> counted metrics
    seen = set()         # the locator keys the fact table carries
    blocked = {}         # (strategy, version, period) -> the metric_ids that blocked
    downgrades = []
    for fact in fact_rows:
        metric = dictionary.get(fact.metric_id)
        if metric is None:
            # A fact outside the dictionary has no direction and no target, so
            # no row can be built for it at all; guessing one is forbidden.
            raise AttainmentError(
                'metric_facts references a metric outside metric_dict: '
                + fact.metric_id)
        locator = _locator(fact)
        seen.add(locator)
        row, counted = _evaluate_fact(fact, metric, resolved, iv_index, medians)
        rows.append(row)
        if counted and metric.signoff_status in signed:
            key = locator[:3]
            numerator[key] = numerator.get(key, 0) + 1

    for key in sorted({locator[:3] for locator in seen}):
        for metric_id in sorted(dictionary):
            locator = key + (metric_id,)
            if locator in seen:
                continue
            row, is_blocked = _evaluate_missing(locator, dictionary[metric_id],
                                                resolved, iv_index, medians)
            if is_blocked:
                blocked.setdefault(key, []).append(metric_id)
                downgrades.append(DowngradeAction(
                    reason_code=RC.NOT_ASSESSED,
                    action='missing_rule BLOCK: ' + metric_id
                           + ' 的事实行缺失，该策略本期不可评价、不产出分数（[L1411]）',
                    subject='|'.join(key)))
                continue
            if row is not None:
                rows.append(row)

    if blocked:
        # [L1411]: a blocked strategy produces no score, so it produces no
        # attainment row either -- aggregate.compose builds one ScoreRow per key
        # it finds in this frame, and one leftover row would score it.
        rows = [row for row in rows
                if (row.strategy_id, row.version_id, row.period) not in blocked]
        numerator = {k: v for k, v in numerator.items() if k not in blocked}

    surviving = {(row.version_id, row.period, row.metric_id) for row in rows}
    for key in sorted(k for k in medians.pool_fallbacks if k in surviving):
        # V-14: falling back to the current-period pool is a downgrade, so it
        # rides out as a [L1051] item-13 DowngradeAction, one per bucket that
        # really did land a row (a bucket whose only imputation belonged to a
        # BLOCK-suppressed strategy is dropped with that strategy, and disclosing
        # an imputation that never reached the frame would be a false claim).
        # ANCHOR_SET_STALE is registered WARN with blocks_run False
        # (dsm/reason_codes.py:49), so the run still produces scores.
        downgrades.append(DowngradeAction(
            reason_code=RC.ANCHOR_SET_STALE,
            action='IMPUTE_MEDIAN 的锚定参考集对该 (version, period, metric) 桶无有效'
                   '出值，已回退当期池中位数（ORCH-37 第 8 条；依据等级 derived:，'
                   '[L1134] 对参考集零字规定 -> ERRATUM-08）',
            subject='|'.join(key)))

    rows.sort(key=_locator)
    denominator = sum(1 for m in dictionary.values() if m.signoff_status in signed)
    coverage = {}
    strategies = {key[0] for key in numerator} | {f.strategy_id for f in fact_rows}
    for strategy_id in sorted(strategies):
        total = sum(value for key, value in numerator.items()
                    if key[0] == strategy_id)
        coverage[strategy_id] = numeric.safe_div(total, denominator, on_zero=ZERO)
    return AttainmentResult(rows=tuple(rows), attainment_coverage=coverage,
                            downgrades=tuple(downgrades))
