'''tests/test_sensitivity.py -- D2 guards.

G-05  flip_rate golden: numerator / denominator / verdict thresholds [L746].
G-06  the [L1019] veto is an explicit non-compensatory BLOCK marker.
T-SEN-01  MC seed discipline [L1017].
T-SEN-02  LOO dominant metric list and the [L1020] sampling degradation.
T-SEN-03  NORM_SWAP is a method switch, not a re-run of the same method.

Every input is built with pydantic (R-2); the grading and normalization hooks
are test-owned callables, because grading.py / normalize.py are not this
package's to import. Their thresholds and formulas are test data, not business
numbers; the golden flip counts below are hand-computed from the constructed
attainments and the documented OAT rule (R-14).
'''
from datetime import date, datetime
from decimal import Decimal

import pytest

from dsm import numeric, sensitivity
from dsm.models import (AttainmentFrame, AttainmentRow, EvidenceFrame,
                        GradeFrame, GradeRow, NormalizedFrame, NormalizedRow,
                        PoolFrame, PoolStats, RedlineFrame, ScoringContext,
                        ScoreFrame, WeightVersionDoc)
from dsm.reason_codes import RC, Severity

DAY = date(2026, 1, 1)
DAY_END = date(2026, 12, 31)
RUN_AT = datetime(2026, 1, 1, 9, 0, 0)
PERIOD = '2026Q1'
SEED = 20260101
POOL = {'biz_domain': 'D1', 'evidence_class': 'A'}

CONFIG = {
    'stable_max': '0.05', 'review_max': '0.15', 'loo_sampling_threshold': 60,
    'mc_samples': 8, 'dirichlet_concentration': '20',
    'loo_dominant_flip_rate': '0.2', 'loo_sample_size_per_dim': 1,
    'norm_swap_method': 'z_score', 'norm_swap_min_rank_correlation': '0.9',
}

# 2 x 2 weight document, hand-computable OAT arithmetic.
LEVEL1 = {'A': Decimal('0.5'), 'B': Decimal('0.5')}
LEVEL2 = {'A': {'m1': Decimal('1')}, 'B': {'m2': Decimal('1')}}

GOLDEN_VALUES = {
    'S1': {'m1': '0.7', 'm2': '0.9'},
    'S2': {'m1': '0.95', 'm2': '0.95'},
    'S3': {'m1': '0.3', 'm2': '0.3'},
    'S4': {'m1': '0.6', 'm2': '0.6'},
}
GOLDEN_GRADES = {'S1': 'L1', 'S2': 'L1', 'S3': 'L3', 'S4': 'L2'}

REVIEW_VALUES = dict(GOLDEN_VALUES)
REVIEW_VALUES['S5'] = {'m1': '0.95', 'm2': '0.95'}
REVIEW_VALUES['S6'] = {'m1': '0.55', 'm2': '0.55'}
REVIEW_VALUES['S7'] = {'m1': '0.2', 'm2': '0.2'}
REVIEW_GRADES = {'S1': 'L1', 'S2': 'L1', 'S3': 'L3', 'S4': 'L2',
                 'S5': 'L1', 'S6': 'L2', 'S7': 'L3'}

VETO_VALUES = {'S1': {'m1': '0.9', 'm2': '0.7'},
               'S2': {'m1': '0.55', 'm2': '0.55'}}
VETO_GRADES = {'S1': 'L1', 'S2': 'L2'}

SWAP_VALUES = {'S1': {'m1': '1.0', 'm2': '0.0'},
               'S2': {'m1': '0.6', 'm2': '0.5'},
               'S3': {'m1': '0.0', 'm2': '1.0'}}
SWAP_GRADES = {'S1': 'L2', 'S2': 'L2', 'S3': 'L2'}
SWAP_LEVEL1 = {'A': Decimal('1')}
SWAP_LEVEL2 = {'A': {'m1': Decimal('0.5'), 'm2': Decimal('0.5')}}
SWAP_NORM = {'m1': {'S1': '1.0', 'S2': '0.6', 'S3': '0.0'},
             'm2': {'S1': '0.0', 'S2': '0.5', 'S3': '1.0'}}


def weights_doc(level1=None, level2=None):
    return WeightVersionDoc(
        weight_version_id='WV-1', status='FROZEN', effective_from=DAY,
        effective_to=DAY_END,
        level1_weights=LEVEL1 if level1 is None else level1,
        level2_weights=LEVEL2 if level2 is None else level2,
        approved_by='tester', approved_date=DAY)


def attainment_rows(values):
    rows = []
    for sid in sorted(values):
        for metric in sorted(values[sid]):
            rows.append(AttainmentRow(
                strategy_id=sid, version_id='V1', period=PERIOD,
                metric_id=metric, attainment=Decimal(values[sid][metric]),
                direction=1, has_target=True, capped_flag=False))
    return rows


def grade_rows(grades):
    return [GradeRow(strategy_id=sid, version_id='V1', period=PERIOD,
                     grade=grades[sid], grade_reason_path=(), capped=False,
                     usable_for_elimination=True) for sid in sorted(grades)]


def normalized_rows():
    rows = []
    for metric in sorted(SWAP_NORM):
        for sid in sorted(SWAP_NORM[metric]):
            rows.append(NormalizedRow(
                strategy_id=sid, version_id='V1', period=PERIOD,
                metric_id=metric, pool_key=POOL,
                norm_value=Decimal(SWAP_NORM[metric][sid]), method='min_max',
                anchor_used=False))
    return rows


def context(values, grades, normalized=(), seed=SEED):
    return ScoringContext(
        period=PERIOD, run_at=RUN_AT, run_id='run-d2', seed=seed,
        weight_version_id='WV-1', evidence_mode='GATE_ONLY', cel_enabled=False,
        input_fingerprints={},
        attainment=AttainmentFrame(rows=tuple(attainment_rows(values)),
                                   attainment_coverage={}),
        normalized=NormalizedFrame(rows=tuple(normalized)),
        evidence=EvidenceFrame(rows=()), redline=RedlineFrame(rows=()),
        score=ScoreFrame(rows=()), grade=GradeFrame(rows=tuple(grade_rows(grades))),
        pool=PoolFrame(rows=()),
        pool_stats=PoolStats(
            rows=(), evidence_structure={'A': 0, 'B': 0, 'C': 0, 'D': 0},
            not_assessed_count=0, not_assessed_reasons={}))


def make_grader(top):
    '''Test-owned Step 6 stub: composite_absolute against two thresholds.'''
    ceiling = Decimal(top)

    def grader(frame):
        out = {}
        for row in frame.rows:
            value = row.composite_absolute
            if value is None:
                grade = 'NOT_ASSESSED'
            elif value >= ceiling:
                grade = 'L1'
            elif value >= Decimal('0.5'):
                grade = 'L2'
            else:
                grade = 'L3'
            out[(row.strategy_id, row.version_id, row.period)] = grade
        return out

    return grader


GRADE_FN = make_grader('0.8')
LENIENT_FN = make_grader('0.75')


def make_normalizer(calls):
    '''Test-owned Step 2 stub: min_max and z_score over one pool x metric.'''

    def normalizer(values, method):
        calls.append(method)
        if method == 'min_max':
            low = min(values)
            high = max(values)
            return [numeric.safe_div(v - low, high - low, on_zero=None)
                    for v in values]
        if method == 'z_score':
            mu = numeric.mean(values)
            sigma = numeric.sqrt(numeric.mean([(v - mu) ** 2 for v in values]))
            return [numeric.safe_div(v - mu, sigma, on_zero=None) for v in values]
        raise AssertionError('unexpected normalization method: ' + str(method))

    return normalizer


def swap_context():
    return context(SWAP_VALUES, SWAP_GRADES, normalized=normalized_rows())


# --------------------------------------------------------------------------
# G-05 -- flip_rate golden: 口径, counts and the [L746] verdict thresholds
# --------------------------------------------------------------------------
def test_g05_oat10_flip_rate_golden():
    '''S1 (0.7 / 0.9) sits exactly on the 0.80 floor: it drops to L2 under
    A-10% and B-10%, S2/S3/S4 have equal metric values so no weight vector
    moves them. 1 flipped strategy of 4 assessed = 0.25 > review_max.'''
    report = sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('OAT_10',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    line = report.by_scheme[0]
    assert line.scheme == 'OAT_10'
    assert line.flipped_count == 1
    assert line.assessed_count == 4
    assert line.overall_flip_rate == Decimal('0.25')
    assert numeric.eq_tol(line.overall_flip_rate,
                          numeric.safe_div(Decimal(1), Decimal(4), on_zero=None))
    assert line.flag == RC.FLIP_RATE_UNUSABLE.value
    row = [item for item in report.by_strategy if item.strategy_id == 'S1'][0]
    assert row.flip_under_pct10 == Decimal('0.5')  # 2 of the 4 OAT_10 runs
    assert row.flip_under_pct20 is None  # OAT_20 was not requested
    assert row.stability_label == 'UNSTABLE'
    assert [item.stability_label for item in report.by_strategy
            if item.strategy_id != 'S1'] == ['STABLE', 'STABLE', 'STABLE']


def test_g05_review_band_between_the_two_thresholds():
    '''1 flip over 7 assessed = 0.142857142857, above stable_max but inside
    review_max: FLIP_RATE_REVIEW, which is a WARN and therefore no veto.'''
    report = sensitivity.run(context(REVIEW_VALUES, REVIEW_GRADES), ('OAT_10',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    line = report.by_scheme[0]
    assert line.flipped_count == 1
    assert line.assessed_count == 7
    assert line.overall_flip_rate == Decimal('0.142857142857')
    assert line.flag == RC.FLIP_RATE_REVIEW.value
    assert sensitivity.is_vetoed(report) is False


def test_g05_oat20_flip_under_pct20_golden():
    report = sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('OAT_20',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    row = [item for item in report.by_strategy if item.strategy_id == 'S1'][0]
    assert row.flip_under_pct20 == Decimal('0.5')
    assert row.flip_under_pct10 is None


# --------------------------------------------------------------------------
# G-06 -- the [L1019] veto: explicit, BLOCK severity, non-compensatory
# --------------------------------------------------------------------------
def test_g06_veto_is_explicit_and_non_compensatory():
    '''OAT_10 is clean (0 flips, no flag) while LOO flips S1 -> 0.5. A STABLE
    scheme must not offset a BLOCK-severity one: that is the non-compensatory
    reading of [L1019], and it is why the veto is a marker and not a score.'''
    report = sensitivity.run(context(VETO_VALUES, VETO_GRADES),
                             ('OAT_10', 'LOO'), dict(CONFIG),
                             weights=weights_doc(), grade_fn=LENIENT_FN)
    flags = {line.scheme: line.flag for line in report.by_scheme}
    assert flags['OAT_10'] is None
    assert flags['LOO'] == RC.FLIP_RATE_UNUSABLE.value
    verdict = sensitivity.veto(report)
    assert verdict.vetoed is True
    assert verdict.codes == (RC.FLIP_RATE_UNUSABLE.value,)
    assert verdict.usable_for_elimination is False
    assert RC.FLIP_RATE_UNUSABLE.value in report.flags
    assert sensitivity.is_vetoed(report) is True


def test_g06_veto_carries_no_numeric_channel():
    '''No field of the veto object is a number, so no later weighting can
    trade against it, and it cannot be read as a deduction.'''
    report = sensitivity.run(context(VETO_VALUES, VETO_GRADES), ('LOO',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=LENIENT_FN)
    verdict = sensitivity.veto(report)
    assert reason_severity_is_block(verdict.codes[0])
    for name in verdict.__dataclass_fields__:
        value = getattr(verdict, name)
        assert not isinstance(value, (Decimal, int, float)) or isinstance(value, bool)
    assert isinstance(verdict.vetoed, bool)
    assert isinstance(verdict.usable_for_elimination, bool)


def reason_severity_is_block(code):
    return severity_of(code) is Severity.BLOCK


def severity_of(code):
    from dsm import reason_codes
    return reason_codes.severity(code)


def test_g06_clean_period_is_not_vetoed():
    report = sensitivity.run(context(REVIEW_VALUES, REVIEW_GRADES), ('OAT_10',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    verdict = sensitivity.veto(report)
    assert verdict.vetoed is False
    assert verdict.codes == ()
    assert verdict.usable_for_elimination is True


# --------------------------------------------------------------------------
# flip_rate denominator discipline (hard point 2)
# --------------------------------------------------------------------------
def test_flip_rate_denominator_zero_is_undefined_not_zero():
    grades = {sid: 'NOT_ASSESSED' for sid in GOLDEN_VALUES}
    with pytest.raises(sensitivity.FlipRateUndefinedError):
        sensitivity.run(context(GOLDEN_VALUES, grades), ('OAT_10',),
                        dict(CONFIG), weights=weights_doc(), grade_fn=GRADE_FN)
    assert issubclass(sensitivity.FlipRateUndefinedError,
                      sensitivity.SensitivityError)


def test_not_assessed_stays_out_of_denominator_and_labels():
    values = dict(GOLDEN_VALUES)
    values['S5'] = {'m1': '0.9', 'm2': '0.9'}
    grades = dict(GOLDEN_GRADES)
    grades['S5'] = 'NOT_ASSESSED'
    report = sensitivity.run(context(values, grades), ('OAT_10',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    assert report.by_scheme[0].assessed_count == 4
    assert report.by_scheme[0].flipped_count == 1
    assert sorted(item.strategy_id for item in report.by_strategy) == [
        'S1', 'S2', 'S3', 'S4']


# --------------------------------------------------------------------------
# T-SEN-01 -- MC seed discipline
# --------------------------------------------------------------------------
def test_tsen01_mc_refuses_to_run_without_a_seed():
    with pytest.raises(sensitivity.SeedRequiredError):
        sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES, seed=None),
                        ('MC',), dict(CONFIG), weights=weights_doc(),
                        grade_fn=GRADE_FN)
    assert issubclass(sensitivity.SeedRequiredError, sensitivity.SensitivityError)


def test_tsen01_mc_same_seed_is_byte_identical():
    ctx = context(GOLDEN_VALUES, GOLDEN_GRADES)
    first = sensitivity.run(ctx, ('MC',), dict(CONFIG), weights=weights_doc(),
                            grade_fn=GRADE_FN)
    second = sensitivity.run(ctx, ('MC',), dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    assert first.model_dump_json() == second.model_dump_json()
    assert first.seed == SEED
    assert second.seed == SEED


def test_tsen01_mc_rate_is_recoverable_and_decimal():
    report = sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('MC',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    line = report.by_scheme[0]
    assert line.assessed_count == 4
    assert 0 <= line.flipped_count <= 4
    assert isinstance(line.overall_flip_rate, Decimal)
    assert numeric.eq_tol(line.overall_flip_rate,
                          numeric.safe_div(Decimal(line.flipped_count),
                                           Decimal(line.assessed_count),
                                           on_zero=None))
    for row in report.by_strategy:
        assert row.stability_label in ('STABLE', 'NEAR_BOUNDARY', 'UNSTABLE')


# --------------------------------------------------------------------------
# T-SEN-02 -- LOO dominant metrics and the [L1020] sampling degradation
# --------------------------------------------------------------------------
def test_tsen02_loo_dominant_metric_is_named():
    '''Dropping m2 empties dimension B, so the composite collapses onto m1 and
    S1 (0.7) falls from L1 to L2: 1 of 4 = 0.25 > 0.2. Dropping m1 leaves S1 at
    0.9 -> L1, so m1 is not dominant.'''
    report = sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('LOO',),
                             dict(CONFIG), weights=weights_doc(),
                             grade_fn=GRADE_FN)
    assert report.loo_dominant_metrics == ('m2',)
    assert RC.DOMINANT_METRIC.value in report.flags
    assert report.by_scheme[0].flipped_count == 1
    assert report.by_scheme[0].overall_flip_rate == Decimal('0.25')


def test_tsen02_loo_degrades_to_dimension_sampling_over_threshold():
    level2 = {}
    for dim, prefix in (('A', 'm_a_'), ('B', 'm_b_')):
        mapping = {prefix + '00': Decimal('0.4')}
        for index in range(1, 31):
            mapping[prefix + format(index, '02d')] = Decimal('0.02')
        level2[dim] = mapping
    doc = weights_doc({'A': Decimal('0.5'), 'B': Decimal('0.5')}, level2)
    values = {'S1': {}, 'S2': {}}
    for dim in level2:
        for metric in level2[dim]:
            values['S1'][metric] = '0.9'
            values['S2'][metric] = '0.9'
    ctx = context(values, {'S1': 'L1', 'S2': 'L1'})
    calls = []

    def counting(frame):
        calls.append(len(frame.rows))
        return GRADE_FN(frame)

    config = dict(CONFIG)
    config['loo_sample_size_per_dim'] = 1
    sampled = sensitivity.run(ctx, ('LOO',), config, weights=doc,
                              grade_fn=counting)
    assert RC.LOO_SAMPLED.value in sampled.flags
    assert len(calls) == 2  # one metric per dimension, not 62
    calls.clear()
    config['loo_sampling_threshold'] = 100
    full = sensitivity.run(ctx, ('LOO',), config, weights=doc,
                           grade_fn=counting)
    assert RC.LOO_SAMPLED.value not in full.flags
    assert len(calls) == 62


# --------------------------------------------------------------------------
# T-SEN-03 -- NORM_SWAP switches the method, it does not re-normalize
# --------------------------------------------------------------------------
def test_tsen03_norm_swap_needs_the_normalizer_hook():
    with pytest.raises(sensitivity.HookRequiredError):
        sensitivity.run(swap_context(), ('NORM_SWAP',), dict(CONFIG),
                        weights=weights_doc(SWAP_LEVEL1, SWAP_LEVEL2),
                        grade_fn=GRADE_FN, normalizer=None)


def test_tsen03_norm_swap_moves_the_ranking_when_the_method_changes():
    '''Base is min_max; the hook is asked for z_score, so the pool x metric
    groups are recomputed under a DIFFERENT method. Hand-computed Spearman over
    the three constructed strategies is 0.866025..., below the 0.9 floor.'''
    calls = []
    config = dict(CONFIG)
    config['norm_swap_method'] = 'z_score'
    report = sensitivity.run(swap_context(), ('NORM_SWAP',), config,
                             weights=weights_doc(SWAP_LEVEL1, SWAP_LEVEL2),
                             grade_fn=GRADE_FN,
                             normalizer=make_normalizer(calls))
    assert calls == ['z_score', 'z_score']  # one call per pool x metric group
    rho = report.norm_swap_rank_correlation
    assert isinstance(rho, Decimal)
    assert Decimal('0.8') < rho < Decimal('0.9')
    assert not numeric.eq_tol(rho, numeric.ONE)
    assert RC.NORMALIZATION_SENSITIVE.value in report.flags


def test_tsen03_same_method_is_the_identity_control():
    '''Swapping min_max for min_max reproduces the frozen Step 2 values and the
    ranking does not move: rho == 1. That is the control which proves the test
    above measures a METHOD switch and not a recomputation of the same data.'''
    calls = []
    config = dict(CONFIG)
    config['norm_swap_method'] = 'min_max'
    report = sensitivity.run(swap_context(), ('NORM_SWAP',), config,
                             weights=weights_doc(SWAP_LEVEL1, SWAP_LEVEL2),
                             grade_fn=GRADE_FN,
                             normalizer=make_normalizer(calls))
    assert calls == ['min_max', 'min_max']
    assert numeric.eq_tol(report.norm_swap_rank_correlation, numeric.ONE)
    assert RC.NORMALIZATION_SENSITIVE.value not in report.flags


# --------------------------------------------------------------------------
# contract-level guards shared by every scheme
# --------------------------------------------------------------------------
def test_run_happy_path_all_five_schemes():
    calls = []
    report = sensitivity.run(swap_context(), sensitivity.SCHEME_ORDER,
                             dict(CONFIG),
                             weights=weights_doc(SWAP_LEVEL1, SWAP_LEVEL2),
                             grade_fn=GRADE_FN,
                             normalizer=make_normalizer(calls))
    assert tuple(line.scheme for line in report.by_scheme) == sensitivity.SCHEME_ORDER
    assert report.seed == SEED
    assert len(report.by_strategy) == 3
    assert report.norm_swap_rank_correlation is not None
    assert set(calls) == {'z_score'}
    for line in report.by_scheme:
        assert line.assessed_count == 3
        assert isinstance(line.overall_flip_rate, Decimal)


def test_run_requires_the_config_values_the_digest_does_not_fix():
    config = dict(CONFIG)
    del config['mc_samples']
    with pytest.raises(sensitivity.MissingConfigError):
        sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('MC',), config,
                        weights=weights_doc(), grade_fn=GRADE_FN)


def test_run_rejects_an_unknown_scheme():
    with pytest.raises(sensitivity.SensitivityError):
        sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('OAT_30',),
                        dict(CONFIG), weights=weights_doc(), grade_fn=GRADE_FN)


def test_run_never_mutates_the_frozen_weight_document():
    doc = weights_doc()
    before_level1 = {k: doc.level1_weights[k] for k in sorted(doc.level1_weights)}
    before_level2 = {d: dict(doc.level2_weights[d]) for d in sorted(doc.level2_weights)}
    sensitivity.run(context(GOLDEN_VALUES, GOLDEN_GRADES), ('OAT_10', 'LOO'),
                    dict(CONFIG), weights=doc, grade_fn=GRADE_FN)
    assert {k: doc.level1_weights[k] for k in sorted(doc.level1_weights)} == before_level1
    assert {d: dict(doc.level2_weights[d]) for d in sorted(doc.level2_weights)} == before_level2
    assert doc.status == 'FROZEN'


def test_perturb_level1_renormalizes_to_exactly_one():
    out = sensitivity.perturb_level1(LEVEL1, 'A', Decimal('0.10'), 1)
    assert out == {'A': Decimal('0.523809523810'), 'B': Decimal('0.476190476190')}
    total = numeric.weighted_sum([(numeric.ONE, out[k]) for k in sorted(out)])
    assert numeric.eq_exact(total, numeric.ONE)


def test_drop_metric_renormalizes_within_and_across_dimensions():
    two = weights_doc({'A': Decimal('1')},
                      {'A': {'m1': Decimal('0.5'), 'm2': Decimal('0.5')}})
    inner = sensitivity.drop_metric(two, 'm1')
    assert inner.level2_weights == {'A': {'m2': Decimal('1.000000000000')}}
    assert two.level2_weights == {'A': {'m1': Decimal('0.5'), 'm2': Decimal('0.5')}}
    emptied = sensitivity.drop_metric(weights_doc(), 'm1')
    assert 'A' not in emptied.level2_weights
    assert emptied.level1_weights == {'B': Decimal('1.000000000000')}
    total = numeric.weighted_sum(
        [(numeric.ONE, emptied.level1_weights[k]) for k in sorted(emptied.level1_weights)])
    assert numeric.eq_exact(total, numeric.ONE)
