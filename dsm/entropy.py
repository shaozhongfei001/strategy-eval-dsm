'''dsm.entropy -- the ONE implementation of the entropy weight formula (SDD 2.4.2).

Layer L1 by ruling ORCH-03: [L537] requires the six steps to be shared by the two
entropy computers, weights_combine.py (L0a, offline calibration window) and
diagnostics.py (L5, online single period). INV-1 forbids L1-L5 to import L0a or
L0b, so the shared implementation cannot live in either consumer: it lives here.

INV-3 type isolation: EntropyWeightVector is a snapshot value with no metric ->
Decimal weight mapping and no callable member, so aggregate.py can never consume
it directly. Only weights_combine.py may copy entropy_w_j into the frozen
WeightProvenance.entropy; only diagnostics.py may copy e_j / d_j into
EntropyDiagnosticRow.

Pure and deterministic: no wall clock, no unseeded randomness, metric ids are
always traversed sorted. Every number goes through dsm.numeric -- Decimal built
from strings, safe_div with an explicit on_zero, q12 on every public result.
'''
from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from dsm import numeric
from dsm.models import EntropyStatus, MetricDirection, Ratio, ReasonCode
from dsm.numeric import D, ONE, TOL, ZERO, q12, safe_div
from dsm.reason_codes import RC

LAYER = 'L1'          # ORCH-03: the shared entropy implementation sits at L1
MIN_STRATEGIES = 2    # [L542] divides by ln n, so n >= 2 is a hard precondition


class _Frozen(BaseModel):
    '''Snapshot semantics, character for character the config of models.py.'''

    model_config = ConfigDict(frozen=True, extra='forbid')


class EntropyColumn(_Frozen):
    '''One metric: the six steps of [L539]-[L545] kept side by side for audit.'''

    metric_id: str
    direction: MetricDirection          # Step 1 input, +1 bigger / -1 smaller is better
    oriented: tuple[Ratio, ...]         # Step 1 result, direction unified
    column_min: Ratio                   # Step 2, min_i(x_ij)
    shifted: tuple[Ratio, ...]          # Step 2, x'_ij = x_ij - min_i(x_ij) + shift
    column_sum: Ratio                   # Step 3 denominator, sum_i x'_ij
    proportion: tuple[Ratio, ...]       # Step 3, p_ij
    e_j: Ratio                          # Step 4, entropy value
    d_j: Ratio                          # Step 5, differentiation coefficient
    entropy_w_j: Ratio | None = None    # Step 6, None when no entropy weight is emitted
    status: EntropyStatus = 'OK'        # INACTIVE when this column is zero variation
    reason: ReasonCode | None = None    # registered code only, never a bare literal


class EntropyWeightVector(_Frozen):
    '''Snapshot of one entropy computation. INV-3: not aggregate-consumable.'''

    strategy_count: int                 # n
    shift: Ratio                        # the caller's technical epsilon of [L540]
    columns: tuple[EntropyColumn, ...]  # sorted by metric_id
    sum_d_j: Ratio                      # sum_j d_j of [L544]
    entropy_emitted: bool               # False -> no entropy weight is output at all
    inactive_metric_ids: tuple[str, ...]
    alerts: tuple[ReasonCode, ...]      # the warning required by [L545]


def step1_orient(values: Sequence, direction) -> tuple[Decimal, ...]:
    '''[L539] Step 1: unify the column direction to bigger-is-better.'''
    factor = D(direction)
    if factor != ONE and factor != -ONE:
        raise numeric.NumericError('direction must be +1 or -1, got ' + str(direction))
    return tuple(q12(D(v) * factor) for v in values)


def step2_shift(oriented: Sequence, shift) -> tuple[tuple[Decimal, ...], Decimal]:
    '''[L540] Step 2: x'_ij = x_ij - min_i(x_ij) + shift, killing zeros and negatives.

    shift is the caller's technical epsilon; this module hardcodes no number of its
    own (H-5) and refuses a non-positive one, because only shift > 0 keeps ln(p_ij)
    of Step 4 defined. Returns (shifted column, column_min).
    '''
    column = [D(v) for v in oriented]
    if not column:
        raise numeric.NumericError('entropy needs at least one strategy value')
    epsilon = D(shift)
    if epsilon <= ZERO:
        raise numeric.NumericError('shift must be strictly positive, got ' + str(shift))
    column_min = min(column)
    return tuple(q12(v - column_min + epsilon) for v in column), column_min


def step3_proportion(shifted: Sequence) -> tuple[tuple[Decimal, ...], Decimal]:
    '''[L541] Step 3: p_ij = x'_ij / sum_i x'_ij. Returns (proportions, sum).'''
    column_sum = q12(sum((D(v) for v in shifted), ZERO))
    proportion = []
    for value in shifted:
        p = safe_div(value, column_sum, on_zero=None)
        if p is None:   # genuinely undefined, never silently 0 (R5)
            raise numeric.NumericError('proportion undefined: sum_i x_ij is zero')
        proportion.append(p)
    return tuple(proportion), column_sum


def step4_entropy(proportion: Sequence, strategy_count: int) -> Decimal:
    '''[L542] Step 4: e_j = -(1 / ln n) * sum_i p_ij ln p_ij, a zero p adds 0.'''
    n = int(strategy_count)
    if n < MIN_STRATEGIES:
        raise numeric.NumericError('entropy needs n >= 2 strategies, got ' + str(n))
    ln_n = numeric.ln(D(n))
    total = ZERO
    for item in proportion:
        p = D(item)
        if p <= ZERO:
            continue    # [L542] p_ij = 0 -> this term is 0, ln(0) is never called
        total = total + p * numeric.ln(p)
    e = safe_div(q12(total), ln_n, on_zero=None)
    if e is None:       # ln n == 0 would mean n == 1, already refused above
        raise numeric.NumericError('entropy undefined: ln n is zero')
    return q12(-e)


def step5_difference(e_j) -> Decimal:
    '''[L543] Step 5: d_j = 1 - e_j.'''
    return q12(ONE - D(e_j))


def step6_weights(d_by_metric: Mapping) -> dict | None:
    '''[L544]-[L545] Step 6: w_j = d_j / sum_j d_j, or None when sum_j d_j = 0.

    None is the SDD's "do not output entropy weights": every metric is zero
    variation, so no weight is defensible and the caller marks them INACTIVE.
    '''
    keys = sorted(d_by_metric)
    total = q12(sum((D(d_by_metric[k]) for k in keys), ZERO))
    weights = {}
    for key in keys:
        w = safe_div(D(d_by_metric[key]), total, on_zero=None)
        if w is None:
            return None
        weights[key] = w
    return weights


def entropy_weights(values: Mapping, directions: Mapping, shift) -> EntropyWeightVector:
    '''Run the six steps over one strategy x metric matrix of [L539].

    values: metric_id -> the n per-strategy values (Decimal / int / str, float is
    refused by numeric.D). directions: metric_id -> +1 or -1. shift: the caller's
    technical epsilon of [L540]. Pure: the same input always gives the same bytes.
    '''
    metric_ids = sorted(values)
    if not metric_ids:
        raise numeric.NumericError('entropy needs at least one metric')
    if sorted(directions) != metric_ids:
        raise numeric.NumericError('directions must cover exactly the metric ids of values')
    widths = {len(values[m]) for m in metric_ids}
    if len(widths) != 1:
        raise numeric.NumericError('every metric column needs the same strategy count')
    n = widths.pop()
    if n < MIN_STRATEGIES:
        raise numeric.NumericError('entropy needs n >= 2 strategies, got ' + str(n))
    epsilon = D(shift)

    trace = {}
    differences = {}
    for metric_id in metric_ids:
        oriented = step1_orient(values[metric_id], directions[metric_id])
        shifted, column_min = step2_shift(oriented, epsilon)
        proportion, column_sum = step3_proportion(shifted)
        e_j = step4_entropy(proportion, n)
        d_j = step5_difference(e_j)
        trace[metric_id] = (oriented, column_min, shifted, column_sum, proportion, e_j, d_j)
        differences[metric_id] = d_j

    weights = step6_weights(differences)
    sum_d_j = q12(sum((differences[m] for m in metric_ids), ZERO))
    columns = []
    inactive = []
    for metric_id in metric_ids:
        oriented, column_min, shifted, column_sum, proportion, e_j, d_j = trace[metric_id]
        dead = weights is None or numeric.eq_tol(d_j, ZERO) or d_j < ZERO
        if dead:
            inactive.append(metric_id)
        columns.append(EntropyColumn(
            metric_id=metric_id, direction=directions[metric_id], oriented=oriented,
            column_min=column_min, shifted=shifted, column_sum=column_sum,
            proportion=proportion, e_j=e_j, d_j=d_j,
            entropy_w_j=None if weights is None else weights[metric_id],
            status='INACTIVE' if dead else 'OK',
            reason=RC.INACTIVE_METRIC.value if dead else None))
    return EntropyWeightVector(
        strategy_count=n, shift=q12(epsilon), columns=tuple(columns), sum_d_j=sum_d_j,
        entropy_emitted=weights is not None, inactive_metric_ids=tuple(inactive),
        alerts=(RC.INACTIVE_METRIC.value,) if inactive else ())
