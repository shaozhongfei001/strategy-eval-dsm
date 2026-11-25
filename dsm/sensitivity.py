'''dsm.sensitivity -- Step 8 sensitivity and robustness (M-I; digest
M13-sensitivity, SDD [L742]-[L752] and [L1010]-[L1021]).

Schemes ([L1015]): OAT_10 / OAT_20 / MC / LOO / NORM_SWAP. Step 1-4 results are
reused from the ScoringContext B group and only Step 5-6 are re-run per
perturbation ([L1016], RK-6), via dsm.aggregate.compose on base.attainment and
base.normalized.

flip_rate 口径 (ruling 25 / H-4, both counts are carried so the rate stays
recoverable): denominator = assessed_count, the strategies whose FROZEN base
grade is not NOT_ASSESSED ([L1004] keeps those out of every denominator);
numerator = flipped_count, the assessed strategies whose re-run grade differs
from the base grade in at least one perturbation of that scheme ([L746] counts
strategies, not runs). The quotient goes through numeric.safe_div(on_zero=None):
an empty denominator is undefined and raises FlipRateUndefinedError, never 0
([L930]). flip_under_pct10 / _pct20 divide that strategy's flips by the scheme's
perturbation count; stability_label reuses the same two [L746] thresholds on the
strategy's own flip share, so no new business number is invented (R-12).
models.py spells the middle label NEAR_BOUNDARY where the digest writes
BOUNDARY -- the contract wins (R-2). NORM_SWAP perturbs no grade (grading reads
the absolute track only, [L968]), so it labels nobody and its verdict is rho.

Veto ([L1019]): veto() returns a SensitivityVeto of booleans and reason codes
ONLY -- no number, so no weighting can trade against it and it is no deduction;
one BLOCK-severity flag vetoes the period even if every other scheme is STABLE.

MC ([L1017]): numpy plus a seed injected via ScoringContext.seed, no seed ->
SeedRequiredError. No clock, no unseeded generator (H-8); one seed, one report.

Injected hooks, since grading.py and normalize.py own those steps and are
neither imported nor duplicated here (R-1 / R-7): weights (the FROZEN
WeightVersionDoc, read only, INV-3), grade_fn (Step 6: ScoreFrame -> key ->
FrameGrade), normalizer (Step 2 under ANOTHER method: (raw Decimals of one pool
x metric group, method) -> Decimals). NORM_SWAP switches the method and
recomposes; it never re-normalizes the same data with the same method.

LOO carries two different things on two different fields, because [L748] puts
them in two different columns: loo_impact ranks EVERY target metric by
max |composite_LOO - composite_base| over the assessed strategies (descending,
so its head is the [L1409] loo_impact max and [L1450] T-SEN-02 impact order),
while loo_dominant_metrics keeps the judge-column membership -- flip_rate over
loo_dominant_flip_rate warns DOMINANT_METRIC -- and is ordered by that ranking.
The impact estimator itself is derived: the contract names the product but
gives no formula (disclosed gap, K-22 / ORCH-40 2.2).

Config: the digest fixes stable_max 0.05, review_max 0.15, loo_sampling_
threshold 60. Everything it leaves open is a required key with no invented
default (R-12): mc_samples, dirichlet_concentration, loo_dominant_flip_rate,
loo_sample_size_per_dim, norm_swap_method, norm_swap_min_rank_correlation.
'''
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import numpy

from dsm import aggregate, numeric, reason_codes
from dsm.models import (NormalizedFrame, SensitivityReport,
                        SensitivitySchemeResult, SensitivityStrategyRow)

__all__ = ['SensitivityError', 'SeedRequiredError', 'FlipRateUndefinedError',
           'MissingConfigError', 'HookRequiredError', 'SensitivityVeto',
           'SCHEME_ORDER', 'perturb_level1', 'drop_metric', 'run', 'veto',
           'is_vetoed']

SCHEME_ORDER = ('OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP')
_OAT_PCT = {'OAT_10': Decimal('0.10'), 'OAT_20': Decimal('0.20')}
_NOT_ASSESSED = 'NOT_ASSESSED'
_FLAG_ORDER = ('FLIP_RATE_UNUSABLE', 'FLIP_RATE_REVIEW', 'DOMINANT_METRIC',
               'NORMALIZATION_SENSITIVE', 'LOO_SAMPLED')
_RC = reason_codes.RC


class SensitivityError(ValueError):
    '''An input, config value or hook violates the [L1010]-[L1021] contract.'''


class SeedRequiredError(SensitivityError):
    '''[L1017] MC refuses to run without an injected seed.'''


class FlipRateUndefinedError(SensitivityError):
    '''assessed_count is 0: safe_div(on_zero=None) says the rate is undefined.'''


class MissingConfigError(SensitivityError):
    '''A scheme needs a config value the digest does not fix (R-12).'''


class HookRequiredError(SensitivityError):
    '''Step 6 (grading) or Step 2 (normalize) was not injected by the caller.'''


@dataclass(frozen=True)
class SensitivityVeto:
    '''The [L1019] verdict. It has no numeric field on purpose: a veto stored
    as a score delta could be compensated by a later weighting (P0-2).'''

    vetoed: bool
    codes: tuple
    usable_for_elimination: bool


def _dec(value):
    '''str / int / Decimal in; a float only enters via numeric.from_float.'''
    if isinstance(value, float):
        return numeric.from_float(value)
    return numeric.D(value)


def _cfg(config, key):
    if config is None:
        return None
    if isinstance(config, dict):
        return config.get(key)
    return getattr(config, key, None)


def _need(config, key, scheme):
    value = _cfg(config, key)
    if value is None:
        raise MissingConfigError('scheme ' + scheme + ' requires config key ' +
                                 key + '; the digest fixes no default (R-12)')
    return value


def _number(config, key, scheme, default=None):
    value = _cfg(config, key)
    if value is not None:
        return _dec(value)
    if default is None:
        raise MissingConfigError('scheme ' + scheme + ' requires numeric key ' + key)
    return numeric.D(default)


def _count(config, key, scheme):
    value = int(_need(config, key, scheme))
    if value <= 0:
        raise SensitivityError(key + ' must be a positive integer, got ' + str(value))
    return value


def _key(row):
    return (row.strategy_id, row.version_id, row.period)


def _renormalize(mapping):
    '''Rescale a weight mapping to sum EXACTLY one ([L954]): the last key in
    sorted order takes the residual, so the sum is 1 with no rounding argument
    left over and the result never depends on dict order.'''
    keys = sorted(mapping)
    if not keys:
        raise SensitivityError('cannot renormalize an empty weight mapping')
    total = numeric.weighted_sum([(numeric.ONE, mapping[k]) for k in keys])
    if total <= numeric.ZERO:
        raise SensitivityError('weight total is not positive: ' + str(total))
    out = {}
    acc = numeric.ZERO
    for key in keys[:-1]:
        share = numeric.safe_div(mapping[key], total, on_zero=None)
        if share is None:
            raise SensitivityError('renormalization undefined for ' + key)
        out[key] = share
        acc = acc + share
    residual = numeric.q12(numeric.ONE - acc)
    if residual < numeric.ZERO:
        raise SensitivityError('renormalization produced a negative residual')
    out[keys[-1]] = residual
    return out


def perturb_level1(level1, dim, pct, sign=1):
    '''[L746] OAT: scale ONE dimension weight by (1 + sign * pct), renormalize
    all of them, return a new mapping. The input mapping is never touched.'''
    if dim not in level1:
        raise SensitivityError('dimension not in the weight document: ' + str(dim))
    if sign not in (1, -1):
        raise SensitivityError('OAT sign must be +1 or -1')
    if numeric.D(pct) <= numeric.ZERO:
        raise SensitivityError('OAT perturbation must be positive: ' + str(pct))
    factor = numeric.ONE + numeric.D(sign) * numeric.D(pct)
    scaled = {key: numeric.q12(numeric.D(level1[key]) * factor) if key == dim
              else numeric.q12(numeric.D(level1[key])) for key in sorted(level1)}
    return _renormalize(scaled)


def drop_metric(weights, metric_id):
    '''[L748] LOO: remove one metric and renormalize. The survivors renormalize
    within their dimension ([L954]); a dimension left empty drops out and level
    1 renormalizes over the rest. Returns a copy, the FROZEN document is never
    mutated (INV-3).'''
    level2 = {dim: dict(mapping) for dim, mapping in weights.level2_weights.items()}
    owners = [dim for dim in sorted(level2) if metric_id in level2[dim]]
    if not owners:
        raise SensitivityError('metric not in the weight document: ' + str(metric_id))
    if len(owners) > 1:
        raise SensitivityError('metric belongs to two dimensions: ' + str(metric_id))
    dim = owners[0]
    del level2[dim][metric_id]
    level1 = dict(weights.level1_weights)
    if level2[dim]:
        level2[dim] = _renormalize(level2[dim])
    else:
        del level2[dim]
        del level1[dim]
        if not level1:
            raise SensitivityError('dropping ' + str(metric_id) + ' empties the document')
        level1 = _renormalize(level1)
    return weights.model_copy(update={'level1_weights': level1, 'level2_weights': level2})


def _flip_rate(flipped, assessed):
    '''The one flip_rate 口径 here: safe_div with an explicit on_zero=None,
    because [L930] forbids reporting an undefined quotient as 0.'''
    rate = numeric.safe_div(numeric.D(int(flipped)), numeric.D(int(assessed)),
                            on_zero=None)
    if rate is None:
        raise FlipRateUndefinedError(
            'flip_rate undefined: assessed_count is 0, safe_div(on_zero=None) '
            'declares it undefined and it is never reported as 0')
    return rate


def _verdict(rate, stable_max, review_max):
    '''[L746]: <= stable_max STABLE and unflagged, <= review_max NEAR_BOUNDARY /
    FLIP_RATE_REVIEW, above review_max UNSTABLE / FLIP_RATE_UNUSABLE ([L1019]).'''
    if rate <= stable_max:
        return None, 'STABLE'
    if rate <= review_max:
        return _RC.FLIP_RATE_REVIEW.value, 'NEAR_BOUNDARY'
    return _RC.FLIP_RATE_UNUSABLE.value, 'UNSTABLE'


def _frame_and_grades(base, weights, config, grade_fn):
    '''Step 5-6 re-run on the reused Step 1-4 frames; base.grade stays the
    frozen baseline and is never recomputed here ([L1016]). The Step-5 frame is
    returned next to the grades so LOO reads its composite off the very same
    compose call it graded: one 口径 per metric, no second compose (RK-6).'''
    frame = aggregate.compose(base.attainment, base.normalized, weights, config)
    result = grade_fn(frame)
    if result is None:
        raise HookRequiredError('grade_fn returned nothing')
    return frame, {tuple(key): str(grade) for key, grade in result.items()}


def _grades_of(base, weights, config, grade_fn):
    '''Grades only; _frame_and_grades also hands back the Step-5 frame.'''
    return _frame_and_grades(base, weights, config, grade_fn)[1]


def _composites(frame, keys):
    '''composite_absolute per assessed key out of ONE Step-5 frame. A key the
    frame does not carry is an explicit error, never a silent 0 (V-14).'''
    values = {_key(row): row.composite_absolute for row in frame.rows}
    out = {}
    for key in keys:
        value = values.get(key)
        if value is None:
            raise SensitivityError(
                'no composite_absolute for ' + str(key[0]) + '/' + str(key[1]) +
                ': the LOO impact needs the absolute track of every assessed '
                'strategy ([L748], [L1018])')
        out[key] = value
    return out


def _rank_impact(impact):
    '''[L748] output column: the per-metric LOO impact ranking. Descending by
    impact, so the head IS the [L1409] loo_impact 最大者. An equal-impact tie
    keeps metric_id ascending order: that is a serialisation determinism rule
    (two runs, one byte string, [L1052]) and NOT a business tie-break -- both
    tied metrics stay listed with their equal value and no unique leader is
    invented (ORCH-40 2.2 forbids a home-made tie-break).'''
    return tuple(sorted(impact.items(), key=lambda item: (-item[1], item[0])))


def _hits(assessed, grades):
    '''Per strategy 0/1: did this perturbation move the grade? A strategy the
    re-run does not return a row for is not counted as a flip.'''
    out = {}
    for key in assessed:
        grade = grades.get(key)
        out[key] = 1 if (grade is not None and grade != assessed[key]) else 0
    return out


def _ordered_schemes(schemes):
    wanted = tuple(str(name) for name in schemes)
    if not wanted:
        raise SensitivityError('no sensitivity scheme requested')
    for name in wanted:
        if name not in SCHEME_ORDER:
            raise SensitivityError('unknown sensitivity scheme: ' + name)
    return tuple(name for name in SCHEME_ORDER if name in wanted)


# The four methods. Each returns (per_strategy_flips, perturbation_count, extra).
def _run_oat(scheme, base, weights, grade_fn, config, assessed):
    pct = _OAT_PCT[scheme]
    totals = dict.fromkeys(assessed, 0)
    runs = 0
    for dim in sorted(weights.level1_weights):
        for sign in (1, -1):
            level1 = perturb_level1(weights.level1_weights, dim, pct, sign)
            doc = weights.model_copy(update={'level1_weights': level1})
            grades = _grades_of(base, doc, config, grade_fn)
            runs += 1
            for key, hit in _hits(assessed, grades).items():
                totals[key] += hit
    return totals, runs, {}


def _run_mc(base, weights, grade_fn, config, assessed):
    '''[L747] Dirichlet around the frozen weights, [L1017] fixed seed. Flipped
    means the MODAL grade over the samples differs from the base grade; a mode
    tie breaks on the sorted grade string so the verdict is reproducible. The
    [L747] distribution and CI have no column on SensitivityReport -- a declared
    gap, not an invented field.'''
    if base.seed is None:
        raise SeedRequiredError('[L1017] MC refuses to run without a seed')
    samples = _count(config, 'mc_samples', 'MC')
    concentration = _number(config, 'dirichlet_concentration', 'MC')
    if concentration <= numeric.ZERO:
        raise SensitivityError('dirichlet_concentration must be positive')
    dims = sorted(weights.level1_weights)
    alpha = []
    for dim in dims:
        weight = numeric.D(weights.level1_weights[dim])
        if weight <= numeric.ZERO:
            raise SensitivityError('Dirichlet needs a positive weight for ' + dim)
        alpha.append(float(concentration * weight))
    draws = numpy.random.default_rng(int(base.seed)).dirichlet(alpha, size=samples)
    totals = dict.fromkeys(assessed, 0)
    seen = {key: {} for key in assessed}
    for draw in draws:
        level1 = _renormalize({dim: numeric.from_float(draw[index])
                               for index, dim in enumerate(dims)})
        doc = weights.model_copy(update={'level1_weights': level1})
        grades = _grades_of(base, doc, config, grade_fn)
        for key in assessed:
            grade = grades.get(key)
            if grade is not None:
                seen[key][grade] = seen[key].get(grade, 0) + 1
    for key in assessed:
        if seen[key]:
            mode = sorted(seen[key].items(), key=lambda item: (-item[1], item[0]))[0][0]
            totals[key] = 1 if mode != assessed[key] else 0
    return totals, samples, {}


def _loo_targets(weights, config):
    '''[L748] every metric, or [L1020] a deterministic per-dimension sample
    once the metric count passes loo_sampling_threshold: the first metric of
    each dimension and then a stride, so no generator is needed.'''
    pairs = [(metric, dim) for dim in sorted(weights.level2_weights)
             for metric in sorted(weights.level2_weights[dim])]
    threshold = int(_number(config, 'loo_sampling_threshold', 'LOO', default=60))
    if len(pairs) <= threshold:
        return pairs, False
    per_dim = _count(config, 'loo_sample_size_per_dim', 'LOO')
    picked = []
    for dim in sorted(weights.level2_weights):
        metrics = sorted(weights.level2_weights[dim])
        if per_dim >= len(metrics):
            picked.extend(metrics)
            continue
        stride = -(-len(metrics) // per_dim)
        picked.extend(metrics[i] for i in range(0, len(metrics), stride)[:per_dim])
    owner = dict((metric, dim) for metric, dim in pairs)
    return [(metric, owner[metric]) for metric in sorted(picked)], True


def _loo_impact(baseline, frame, keys):
    '''[L748] the LOO impact of one dropped metric (evidence level derived: the
    contract names the product -- the per-metric LOO impact ranking -- but gives
    no formula, so this estimator is a DISCLOSED specification gap, ORCH-40 2.2
    / K-22, not a signed-off business number):

        loo_impact[m] = max over the assessed strategies s of
                        | composite_LOO(m, s) - composite_base(s) |

    composite_LOO(m, s) is Step 4-5 re-run on the [L954] within-dimension
    renormalised document drop_metric(m) returns. Absolute track only ([L968]:
    grading reads that one), q12 Decimals end to end, never a float (V-9). A
    metric that flips nobody still gets its impact measured: the judge column
    (flip_rate over loo_dominant_flip_rate) and this output column are two
    different fields and neither replaces the other ([L748], [L1409]).'''
    moved = _composites(frame, keys)
    worst = numeric.ZERO
    for key in keys:
        delta = abs(numeric.q12(moved[key] - baseline[key]))
        if delta > worst:
            worst = delta
    return numeric.q12(worst)


def _run_loo(base, weights, grade_fn, config, assessed):
    '''[L748] both columns of the LOO row, kept apart on purpose:
      * the JUDGE column -- a metric whose drop pushes flip_rate over
        loo_dominant_flip_rate warns DOMINANT_METRIC and files a dictionary
        ticket (semantics unchanged);
      * the OUTPUT column -- every target metric's impact, ranked descending,
        which is what names the leading metric and the [L1409] loo_impact max.
    loo_dominant_metrics keeps the judge-column membership and is ORDERED by the
    output column, so its leading entry is the most influential metric rather
    than whichever one the loop happened to trip over first.'''
    targets, sampled = _loo_targets(weights, config)
    threshold = _number(config, 'loo_dominant_flip_rate', 'LOO')
    keys = sorted(assessed)
    baseline = _composites(
        aggregate.compose(base.attainment, base.normalized, weights, config),
        keys)
    totals = dict.fromkeys(assessed, 0)
    dominant = []
    impact = {}
    runs = 0
    for metric, _dim in targets:
        doc = drop_metric(weights, metric)
        frame, grades = _frame_and_grades(base, doc, config, grade_fn)
        runs += 1
        hits = _hits(assessed, grades)
        for key, hit in hits.items():
            totals[key] += hit
        if _flip_rate(sum(hits.values()), len(assessed)) > threshold:
            dominant.append(metric)  # [L748] DOMINANT_METRIC, dictionary ticket
        impact[metric] = _loo_impact(baseline, frame, keys)
    ranking = _rank_impact(impact)
    position = dict((metric, index)
                    for index, (metric, _value) in enumerate(ranking))
    dominant.sort(key=lambda metric: position[metric])
    return totals, runs, {'dominant': tuple(dominant), 'sampled': sampled,
                          'impact': ranking}


def _swap_frame(base, method, normalizer):
    '''Recompute Step 2 under ANOTHER method ([L749]). Raw values are the reused
    Step 1 attainments and the pool x metric groups come from the frozen
    NormalizedFrame, so this is a method switch over the same comparison set,
    not a second pass of the same method. anchor_used is forced False: the hook
    applies the pure method, the [L941] anchor set belongs to normalize.py.'''
    raw = {(_key(row), row.metric_id): row.attainment for row in base.attainment.rows}
    groups = {}
    for row in base.normalized.rows:
        groups.setdefault((row.pool_key, row.metric_id), []).append(row)
    if not groups:
        raise SensitivityError('NORM_SWAP needs a non-empty base.normalized frame')
    rows = []
    for pool_key, metric_id in sorted(
            groups, key=lambda item: (item[0].biz_domain, item[0].evidence_class, item[1])):
        members = sorted(groups[(pool_key, metric_id)], key=_key)
        values = []
        for member in members:
            value = raw.get((_key(member), metric_id))
            if value is None:
                raise SensitivityError('NORM_SWAP has no raw value for ' + str(metric_id))
            values.append(value)
        swapped = tuple(normalizer(tuple(values), method))
        if len(swapped) != len(values):
            raise SensitivityError('normalizer returned the wrong length')
        for member, value in zip(members, swapped):
            rows.append(member.model_copy(update={'norm_value': _dec(value),
                                                  'method': method,
                                                  'anchor_used': False}))
    return NormalizedFrame(rows=tuple(rows))


def _relative(frame, keys):
    values = {_key(row): row.composite_relative for row in frame.rows}
    out = []
    for key in keys:
        if values.get(key) is None:
            raise SensitivityError('NORM_SWAP needs a relative composite for ' + str(key))
        out.append(values[key])
    return out


def _run_norm_swap(base, weights, grade_fn, config, assessed, normalizer):
    '''[L749]: swap the method, re-run the relative track, report the Spearman
    rho against the frozen relative ranking. runs is 0 on purpose -- grading
    reads the absolute track only ([L968]), so the swap perturbs no grade and
    adds no per-strategy stability evidence.'''
    if normalizer is None:
        raise HookRequiredError('NORM_SWAP needs the Step 2 normalizer hook: '
                                'normalize.py owns the three formulas (R-7)')
    method = str(_need(config, 'norm_swap_method', 'NORM_SWAP'))
    floor = _number(config, 'norm_swap_min_rank_correlation', 'NORM_SWAP')
    swapped = _swap_frame(base, method, normalizer)
    baseline = aggregate.compose(base.attainment, base.normalized, weights, config)
    moved = aggregate.compose(base.attainment, swapped, weights, config)
    keys = sorted(key for key in assessed if any(_key(row) == key for row in moved.rows))
    if len(keys) < 2:
        raise SensitivityError('NORM_SWAP needs at least two ranked strategies')
    rho = numeric.spearman(_relative(baseline, keys), _relative(moved, keys))
    totals = _hits(assessed, _grades_of(base, weights, config, grade_fn))
    return totals, 0, {'rho': rho, 'sensitive': rho < floor}


def run(base, schemes, config, *, weights, grade_fn, normalizer=None):
    '''[L1014] signature plus the three injected hooks of the module docstring.
    One SensitivityReport out: per-scheme overall_flip_rate ([L1018]), the
    per-strategy labels, the LOO dominant list plus the [L748] LOO impact
    ranking, the NORM_SWAP rho, the [L1020] flags and the [L1017] seed.'''
    if weights is None:
        raise HookRequiredError('the FROZEN WeightVersionDoc must be injected')
    if grade_fn is None:
        raise HookRequiredError('grade_fn (Step 6) must be injected; grading.py '
                                'owns it and is not imported here (R-1)')
    wanted = _ordered_schemes(schemes)
    stable_max = _number(config, 'stable_max', 'sensitivity', default='0.05')
    review_max = _number(config, 'review_max', 'sensitivity', default='0.15')
    if review_max < stable_max:
        raise SensitivityError('review_max is below stable_max')
    base_grades = {_key(row): row.grade for row in base.grade.rows}
    assessed = {key: base_grades[key] for key in sorted(base_grades)
                if base_grades[key] != _NOT_ASSESSED}
    by_scheme = []
    per_strategy = {}
    totals = {key: [0, 0] for key in assessed}
    flags = []
    dominant = ()
    impact = ()
    rho = None
    for scheme in wanted:
        if scheme in _OAT_PCT:
            flips, runs, extra = _run_oat(scheme, base, weights, grade_fn, config, assessed)
        elif scheme == 'MC':
            flips, runs, extra = _run_mc(base, weights, grade_fn, config, assessed)
        elif scheme == 'LOO':
            flips, runs, extra = _run_loo(base, weights, grade_fn, config, assessed)
            dominant = extra['dominant']
            impact = extra['impact']
            if extra['sampled']:
                flags.append(_RC.LOO_SAMPLED.value)
            if dominant:
                flags.append(_RC.DOMINANT_METRIC.value)
        else:
            flips, runs, extra = _run_norm_swap(base, weights, grade_fn, config,
                                                assessed, normalizer)
            rho = extra['rho']
            if extra['sensitive']:
                flags.append(_RC.NORMALIZATION_SENSITIVE.value)
        flipped = sum(1 for key in assessed if flips.get(key, 0) > 0)
        rate = _flip_rate(flipped, len(assessed))
        flag, _label = _verdict(rate, stable_max, review_max)
        if flag is not None:
            flags.append(flag)
        by_scheme.append(SensitivitySchemeResult(
            scheme=scheme, overall_flip_rate=rate, flipped_count=int(flipped),
            assessed_count=int(len(assessed)), flag=flag))
        if runs == 0:
            continue  # NORM_SWAP perturbed no grade, so it labels nobody
        for key in assessed:
            per_strategy.setdefault(key, {})[scheme] = _flip_rate(flips.get(key, 0), runs)
            totals[key][0] += flips.get(key, 0)
            totals[key][1] += runs
    rows = []
    for key in sorted(assessed):
        flips, runs = totals[key]
        if runs == 0:
            continue
        label = _verdict(_flip_rate(flips, runs), stable_max, review_max)[1]
        rows.append(SensitivityStrategyRow(
            strategy_id=key[0], version_id=key[1], stability_label=label,
            flip_under_pct10=per_strategy[key].get('OAT_10'),
            flip_under_pct20=per_strategy[key].get('OAT_20')))
    return SensitivityReport(
        by_scheme=tuple(by_scheme), by_strategy=tuple(rows),
        loo_dominant_metrics=tuple(dominant), norm_swap_rank_correlation=rho,
        loo_impact=impact,
        flags=tuple(code for code in _FLAG_ORDER if code in set(flags)),
        seed=base.seed)


def veto(report):
    '''The [L1019] first-page verdict, non-compensatory by construction: one
    BLOCK-severity scheme flag vetoes the period, no STABLE scheme offsets it,
    and nothing numeric is exposed for a later weighting to trade against.
    usable_for_elimination mirrors the grade_ledger column; writing that ledger
    belongs to the renderer, not to this module.'''
    codes = tuple(item.flag for item in report.by_scheme
                  if item.flag is not None and
                  reason_codes.severity(item.flag) is reason_codes.Severity.BLOCK)
    blocked = bool(codes)
    return SensitivityVeto(vetoed=blocked, codes=codes,
                           usable_for_elimination=not blocked)


def is_vetoed(report):
    return veto(report).vetoed
