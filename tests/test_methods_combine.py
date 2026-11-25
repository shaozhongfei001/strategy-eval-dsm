'''tests/test_methods_combine.py -- A2 guards T-CMB-01~09 and P-14 / P-15 (digest M08).

Every test below carries the guard id it exists for; nothing else is asserted
(R-9). Golden numbers come from the frozen fixtures of A1 and from hand arithmetic
on the AHP weights, never from this implementation's own output (R-14): the AHP
matrices used here are perfectly consistent (a_ij = w_i / w_j), so weights_ahp
returns exactly the weights they were built from and CR = 0.
'''
import json
from datetime import date
from decimal import Decimal

import pytest
from pathlib import Path
from hypothesis import given, settings, strategies as st

from dsm import numeric, weights_ahp
from dsm import weights_combine as wc
from dsm.models import EntropySegment, MetricWeightComparison
from dsm.numeric import D, ONE, TOL, ZERO, eq_tol, q12
from dsm.reason_codes import RC

Q20 = Decimal('1E-20')
SHIFT = D('0.000001')          # [L540] technical epsilon: an input, no SDD value
DIMS = {'D1': '0.6', 'D2': '0.4'}
MW = {'D1': {'M1': '0.5', 'M2': '0.5'}, 'D2': {'M3': '1'}}
SPEC = {'M1': 'D1', 'M2': 'D1', 'M3': 'D2'}
COLS = {'M1': ['10', '20', '30'], 'M2': ['15', '16', '95'], 'M3': ['7', '8', '9']}
CONST = {'M1': ['10', '20', '30'], 'M2': ['5', '5', '5'], 'M3': ['7', '8', '9']}
IDS = ['S-1', 'S-2', 'S-3']
HDR = wc.DraftHeader(weight_version_id='WV-T-CMB', approved_by='SYNTH_APPROVER',
                     approved_date=date(2026, 1, 10), effective_from=date(2026, 1, 1),
                     effective_to=date(2026, 12, 31))
INCONSISTENT = {'D1': {'D1': '1', 'D2': '9', 'D3': '0.111111111111111111'},
                'D2': {'D1': '0.111111111111111111', 'D2': '1', 'D3': '9'},
                'D3': {'D1': '9', 'D2': '0.111111111111111111', 'D3': '1'}}


def matrix(weights):
    '''A perfectly consistent pairwise matrix: a_ij = w_i / w_j, so CR = 0 ([L518]).'''
    keys = sorted(weights)
    w = {k: D(weights[k]) for k in keys}
    return {i: {j: str((w[i] / w[j]).quantize(Q20)) for j in keys} for i in keys}


def snapshot(result):
    '''The AHP product carried as the DATA weights_combine consumes (ORCH-29 ruling 1:
    the 消费 L0a of [L278] is the L0a PRODUCT, [L286] forbids importing the module).
    Crossing that boundary is the CALLER's job: in production dsm/cli.py, here the test.'''
    return wc.AhpHierarchySnapshot(
        dimension=wc.AhpLevelSnapshot.from_payload(result.dimension.segment_payload(),
                                                   result.dimension.findings),
        metrics_by_dim={dim: wc.AhpLevelSnapshot.from_payload(level.segment_payload(),
                                                              level.findings)
                        for dim, level in sorted(result.metrics_by_dim.items())})


def elicit(dimension_matrices, metric_matrices_by_dim, interview_dates=()):
    '''The Step-1 elicitation injected into run_six_steps / build_draft: the L0a -> L0a
    edge stays here in the caller and never inside weights_combine ([L286]).'''
    return snapshot(weights_ahp.elicit_hierarchy(dimension_matrices, metric_matrices_by_dim,
                                                 tuple(interview_dates)))


def hierarchy(dim_weights=DIMS, metric_weights=MW):
    return elicit({'E1': matrix(dim_weights)},
                  {d: {'E1': matrix(metric_weights[d])} for d in sorted(metric_weights)})


def rows(spec=SPEC, redline=()):
    return [{'metric_id': m, 'dim_code': spec[m], 'direction': 1, 'is_redline': m in redline}
            for m in sorted(spec)]


def facts(columns, periods=('P1', 'P2'), strategies=IDS, drop=()):
    '''period -> metric_id -> strategy_id -> value; `drop` removes whole columns.'''
    out = {}
    for period in periods:
        out[period] = {}
        for metric_id in sorted(columns):
            if (period, metric_id) in drop:
                continue
            out[period][metric_id] = {s: columns[metric_id][i]
                                      for i, s in enumerate(strategies[:len(columns[metric_id])])}
    return out


def opts(**over):
    base = {'alpha': D('0.5'), 'min_dim_weight': D('0.05'), 'entropy_min_strategies': 3}
    base.update(over)
    return wc.CombineOptions(**base)


def window(columns=COLS, options=None, periods=('P1', 'P2'), metric_rows=None, strategies=IDS):
    '''Step 2 on synthetic facts; None is the [L577] insufficient-sample degrade.'''
    try:
        return wc.calibrate_entropy_window(facts(columns, periods, strategies),
                                           metric_rows or rows(), options or opts(), SHIFT)
    except wc.EntropyInsufficientSample:
        return None


def run(columns=COLS, options=None, periods=('P1', 'P2'), metric_rows=None, strategies=IDS):
    return wc.combine(hierarchy(), window(columns, options, periods, metric_rows, strategies),
                      options or opts())


def dim_sum(weights, dim):
    total = ZERO
    for key in sorted(weights[dim]):
        total = total + D(weights[dim][key])
    return q12(total)


# --- T-CMB-01: alpha endpoints ---------------------------------------------
def test_t_cmb_01_alpha_endpoints():
    '''[L589] at alpha = 1 the combination is pure AHP; at alpha = 0 it is the
    renormalised entropy weight. Both endpoints are hand-checkable.'''
    top = run(options=opts(alpha=ONE))
    for dim in sorted(MW):
        for metric_id in sorted(MW[dim]):
            assert eq_tol(top.metric_weights[dim][metric_id], D(MW[dim][metric_id]), TOL)
    for dim in sorted(DIMS):
        assert eq_tol(top.dim_weights[dim], D(DIMS[dim]), TOL)
    zero = run(options=opts(alpha=ZERO, alpha_floor=ZERO))
    ent = zero.entropy.median_entropy
    for dim in sorted(MW):
        total = sum((D(ent[m]) for m in sorted(MW[dim])), ZERO)
        for metric_id in sorted(MW[dim]):
            expected = q12(D(ent[metric_id]) / total)
            assert eq_tol(zero.metric_weights[dim][metric_id], expected, TOL)


# --- T-CMB-02 / P-15: INACTIVE fallback is never diluted -------------------
def test_t_cmb_02_p15_inactive_fallback_not_diluted():
    '''[L581]-[L587]. Contrast run: M2 is zero variation in one run and varies in the
    other. The fallback metric must end at EXACTLY its AHP weight (1e-12, V-9) while
    the varying metric absorbs the residual; the non-fallback run must move.'''
    with_inactive = run(columns=CONST)
    without = run(columns=COLS)
    assert 'M2' in with_inactive.inactive_fallback_metrics
    assert 'M2' not in without.inactive_fallback_metrics
    trace = with_inactive.metric_trace['M2']
    assert trace.is_fallback is True
    assert trace.fallback_reason == RC.ENTROPY_INACTIVE_FALLBACK.value
    assert eq_tol(trace.combined_raw_weight, D('0.5'), TOL)      # P-15: pre-renormalisation
    assert eq_tol(trace.final_weight, D('0.5'), TOL)             # not diluted by Step 4
    assert eq_tol(with_inactive.metric_weights['D1']['M2'], trace.ahp_weight, TOL)
    assert eq_tol(with_inactive.metric_weights['D1']['M1'], D('0.5'), TOL)   # residual 1 - 0.5
    assert not eq_tol(without.metric_weights['D1']['M2'], D('0.5'), TOL)     # it does move
    assert eq_tol(dim_sum(with_inactive.metric_weights, 'D1'), ONE, TOL)


# --- six step order, part 1: Step 1 before Step 2, Step 2 before Step 3 ----
def test_step_order_1_gate_runs_before_the_entropy_window():
    '''[L573]: CR >= 0.1 terminates Step 1 before Step 2 exists. Every metric is
    redline here, so a reordered Step 2 would raise CombineError first.'''
    redlined = rows(redline=tuple(SPEC))
    with pytest.raises(weights_ahp.ConsistencyFailedError):
        wc.run_six_steps({'dimension': {'E1': INCONSISTENT},
                          'metrics_by_dim': {'D1': {'E1': matrix(MW['D1'])},
                                             'D2': {'E1': matrix(MW['D2'])}}},
                         facts(CONST), redlined, opts(), HDR, SHIFT,
                         elicit_hierarchy=elicit)
    layer = hierarchy()
    with pytest.raises(wc.CombineError):
        wc.calibrate_entropy_window(facts(CONST), redlined, opts(), SHIFT)
    assert wc.step1_ahp_gate(layer).cr_max < D('0.1')


def test_step_order_2_exclusion_runs_before_the_fallback_decision():
    '''[L575] drops a period in Step 2, so the Step 3 INACTIVE decision sees the
    trimmed window only: M2 is constant in the usable period and varies in the
    excluded one. Reordering Steps 2 and 3 would clear the fallback flag.'''
    data = {'P1': {m: {s: CONST[m][i] for i, s in enumerate(IDS)} for m in sorted(CONST)},
            'P2': {m: {s: COLS[m][i] for i, s in enumerate(IDS[:2])} for m in sorted(COLS)}}
    snapshot = wc.calibrate_entropy_window(data, rows(), opts(), SHIFT)
    assert list(snapshot.excluded_periods) == ['P2']
    assert snapshot.excluded_periods['P2'] == RC.ENTROPY_PERIOD_SKIPPED.value
    assert snapshot.strategy_count_by_period == {'P1': 3, 'P2': 2}
    combined = wc.combine(hierarchy(), snapshot, opts())
    assert 'M2' in combined.inactive_fallback_metrics


# --- six step order, part 2: Step 4 before Step 5, Step 5 before Step 6 ----
def test_step_order_4_renormalisation_runs_before_the_hard_checks():
    '''[L590] then [L594]: the raw alpha mix of a dimension does not sum to 1 (the
    entropy side is global), so H-1 can only be True on the renormalised weights.'''
    combined = run()
    raw = ZERO
    for metric_id in sorted(MW['D1']):
        raw = raw + D(combined.metric_trace[metric_id].combined_raw_weight)
    assert not eq_tol(raw, ONE, TOL)                  # Step 4 input really is unnormalised
    assert combined.hard_checks.results['H-1'] is True
    assert eq_tol(dim_sum(combined.metric_weights, 'D1'), ONE, TOL)


def test_step_order_5_gate_runs_before_the_draft():
    '''[L593] then [L600]: an infeasible alpha never reaches Step 6, and a feasible
    one records all six step ids in the SDD order.'''
    blocked = run(options=opts(min_dim_weight=D('0.99')))
    assert blocked.feasible is False
    assert blocked.hard_checks.violations == ('H-2',)
    assert blocked.step_trace == wc.STEP_IDS[:5]
    with pytest.raises(wc.AlphaInfeasibleError):
        wc.build_draft({'dimension': {'E1': matrix(DIMS)},
                        'metrics_by_dim': {d: {'E1': matrix(MW[d])} for d in sorted(MW)}},
                       facts(COLS), rows(), opts(min_dim_weight=D('0.99')), HDR, SHIFT,
                       elicit_hierarchy=elicit)
    combined, doc = wc.run_six_steps({'dimension': {'E1': matrix(DIMS)},
                                      'metrics_by_dim': {d: {'E1': matrix(MW[d])}
                                                         for d in sorted(MW)}},
                                     facts(COLS), rows(), opts(), HDR, SHIFT,
                                     elicit_hierarchy=elicit)
    assert combined.step_trace == wc.STEP_IDS
    assert doc.status == 'DRAFT'


# --- H-1 ~ H-5, one test each ----------------------------------------------
def test_h1_normalisation_is_exact_and_a_broken_set_is_rejected():
    '''[L594]: sum W_d = 1 and sum w_j = 1 per dimension within 1e-12. A weight set
    that misses it is rejected as a violation, never warned about.'''
    combined = run()
    total = sum((D(combined.dim_weights[d]) for d in sorted(combined.dim_weights)), ZERO)
    assert eq_tol(q12(total), ONE, TOL)
    for dim in sorted(MW):
        assert eq_tol(dim_sum(combined.metric_weights, dim), ONE, TOL)
    assert combined.hard_checks.results['H-1'] is True
    broken = wc.MixedWeights(alpha_used=D('0.5'), dim_weights={'D1': D('0.5'), 'D2': D('0.4')},
                             dim_entropy_weight={}, dim_raw_weight={},
                             metric_weights={'D1': {'M1': D('0.4'), 'M2': D('0.4')},
                                             'D2': {'M3': D('0.9')}},
                             metric_trace={}, comparison_by_metric={})
    report = wc.step5_hard_checks(broken, wc.step1_ahp_gate(hierarchy()), opts())
    assert report.results['H-1'] is False
    assert 'H-1' in report.violations and RC.ALPHA_INFEASIBLE.value in report.reasons


def test_h2_min_dim_weight_is_a_hard_floor():
    '''[L595] K-19: a dimension crushed below min_dim_weight makes the alpha
    infeasible instead of producing a warning.'''
    ok = run(options=opts(min_dim_weight=D('0.10')))
    assert ok.hard_checks.results['H-2'] is True and ok.feasible is True
    bad = run(options=opts(min_dim_weight=D('0.45')))
    assert bad.hard_checks.results['H-2'] is False
    assert bad.hard_checks.violations == ('H-2',)
    assert bad.feasible is False
    assert bad.hard_checks.min_dim_observed < D('0.45')


def test_h3_min_metric_weight_only_when_configured():
    '''[L596]: min_metric_weight is optional; when it is set, a metric below it
    rejects the alpha.'''
    skipped = run(options=opts(min_metric_weight=None))
    assert skipped.hard_checks.results['H-3'] is True
    bad = run(options=opts(min_metric_weight=D('0.60')))
    assert bad.hard_checks.results['H-3'] is False
    assert 'H-3' in bad.hard_checks.violations
    assert bad.hard_checks.min_metric_observed < D('0.60')


def test_h4_cr_gate_rejects_instead_of_warning():
    '''[L573] / [L597]: CR >= 0.1 stops Step 1 outright, and a layer that somehow
    carries such a CR is rejected by H-4 rather than waved through.'''
    with pytest.raises(weights_ahp.ConsistencyFailedError):
        weights_ahp.elicit({'E1': INCONSISTENT})
    layer = wc.step1_ahp_gate(hierarchy())
    poisoned = layer.model_copy(update={'cr_max': D('0.1')})
    mixed = wc.step4_combine_normalize(layer, window(), {}, opts(), D('0.5'))
    report = wc.step5_hard_checks(mixed, poisoned, opts())
    assert report.results['H-4'] is False
    assert 'H-4' in report.violations and RC.AHP_CR_FAILED.value in report.reasons


def test_h5_t_cmb_07_max_shift_from_ahp():
    '''[L598]-[L599] K-20: the L1 distance from pure AHP is capped, so the entropy
    side cannot overturn the expert judgement.'''
    free = run(options=opts(max_shift_from_ahp=D('0.30')))
    assert free.hard_checks.results['H-5'] is True
    tight = run(options=opts(max_shift_from_ahp=D('0.001')))
    assert tight.hard_checks.results['H-5'] is False
    assert tight.hard_checks.violations == ('H-5',)
    assert tight.hard_checks.l1_shift_from_ahp > D('0.001')
    assert tight.feasible is False
    pure = run(options=opts(alpha=ONE, max_shift_from_ahp=ZERO))
    assert pure.hard_checks.results['H-5'] is True        # alpha = 1 does not move at all
    assert eq_tol(pure.hard_checks.l1_shift_from_ahp, ZERO, TOL)


# --- T-CMB-03 / T-CMB-04 / T-CMB-05 ----------------------------------------
def test_t_cmb_03_alpha_feasible_set_is_reported_not_guessed():
    '''[L593] hands the verdict to the calibration side: combine() reports an
    infeasible alpha instead of raising and never substitutes a neighbouring one, so
    a hole in the feasible set stays a human choice ([L593], [L1071]).'''
    verdicts = {}
    for alpha in (D('0.5'), D('0.6'), D('0.75'), ONE):
        candidate = run(options=opts(alpha=alpha, min_metric_weight=D('0.45')))
        verdicts[alpha] = candidate
        assert eq_tol(candidate.alpha, alpha, TOL)         # never silently replaced
        assert candidate.feasible == (not candidate.hard_checks.violations)
    assert any(c.feasible for c in verdicts.values())
    assert any(not c.feasible for c in verdicts.values())
    for candidate in verdicts.values():
        if not candidate.feasible:
            with pytest.raises(wc.AlphaInfeasibleError):
                wc.assert_feasible(candidate)


def test_t_cmb_04_alpha_floor_is_never_widened():
    '''[L562]-[L563] K-15: alpha below alpha_floor (or above 1) is refused, not
    quietly lifted to the floor.'''
    with pytest.raises(wc.AlphaFloorError):
        wc.CombineOptions(alpha=D('0.3'), min_dim_weight=D('0.05'))
    with pytest.raises(wc.AlphaFloorError):
        wc.CombineOptions(alpha=D('1.2'), min_dim_weight=D('0.05'))
    ok = wc.CombineOptions(alpha=D('0.5'), min_dim_weight=D('0.05'))
    assert eq_tol(ok.alpha_floor, D('0.5'), TOL) and eq_tol(ok.alpha, ok.alpha_floor, TOL)
    moved = opts(alpha=D('0.6'), alpha_floor=D('0.6'))
    assert eq_tol(moved.alpha_floor, D('0.6'), TOL)
    assert eq_tol(run(options=moved).alpha, D('0.6'), TOL)


def test_t_cmb_05_insufficient_sample_degrades_to_pure_ahp():
    '''[L577]-[L578]: every period below entropy_min_strategies -> alpha = 1, kind
    AHP_ONLY, ENTROPY_INSUFFICIENT_SAMPLE plus a prominent first-screen label.'''
    short = facts(COLS, strategies=IDS[:2])
    with pytest.raises(wc.EntropyInsufficientSample):
        wc.calibrate_entropy_window(short, rows(), opts(), SHIFT)
    combined, doc = wc.run_six_steps(mats(), short, rows(), opts(), HDR, SHIFT,
                                     elicit_hierarchy=elicit)
    assert combined.entropy is None and combined.entropy_sufficient is False
    assert eq_tol(combined.alpha, ONE, TOL) and combined.kind == wc.KIND_AHP_ONLY
    assert doc.provenance.entropy is None and doc.provenance.kind == 'AHP_ONLY'
    assert RC.ENTROPY_INSUFFICIENT_SAMPLE.value in combined.notices
    assert RC.ALPHA_PURE_AHP.value in combined.notices
    assert combined.prominent_notice and 'L577' in combined.prominent_notice
    assert sorted(combined.inactive_fallback_metrics) == ['M1', 'M2', 'M3']
    for dim in sorted(MW):
        for metric_id in sorted(MW[dim]):
            assert eq_tol(combined.metric_weights[dim][metric_id], D(MW[dim][metric_id]), TOL)
    assert eq_tol(dim_sum(combined.metric_weights, 'D1'), ONE, TOL)
    assert combined.feasible is True and doc.status == 'DRAFT'


# --- T-CMB-06 / T-CMB-08 / T-CMB-09 ----------------------------------------
def test_t_cmb_06_entropy_provenance_is_a_frozen_snapshot():
    '''[L535] INV-3: WeightProvenance.entropy is a snapshot value -- no callable, no
    live mapping a scoring run could consume, and immutable once written.'''
    combined, doc = wc.run_six_steps(mats(), facts(COLS), rows(), opts(), HDR, SHIFT,
                                     elicit_hierarchy=elicit)
    segment = doc.provenance.entropy
    assert isinstance(segment, EntropySegment)
    assert isinstance(combined.entropy, wc.EntropySnapshot)
    for name in type(segment).model_fields:
        assert not callable(getattr(segment, name))
    for name in type(combined.entropy).model_fields:
        assert not callable(getattr(combined.entropy, name))
    for value in segment.median_entropy.values():
        assert isinstance(value, Decimal)
    assert segment.median_entropy == combined.entropy.median_entropy      # a copy, not a link
    with pytest.raises(Exception):
        segment.median_entropy = {}
    with pytest.raises(Exception):
        combined.entropy.median_entropy = {}


def test_t_cmb_08_provenance_is_complete():
    '''[L600] + 3.11.4: the AHP, entropy and combine segments are all filled, the
    four-column table and the H-1..H-5 verdicts included.'''
    header = wc.DraftHeader(weight_version_id='WV-T-CMB-08', approved_by='SYNTH_APPROVER',
                            approved_date=date(2026, 1, 10), effective_from=date(2026, 1, 1),
                            effective_to=date(2026, 12, 31), alpha_source='MANUAL',
                            whatif_run_id='WIF-1', interview_dates=(date(2026, 1, 5),))
    combined, doc = wc.run_six_steps(mats(), facts(COLS), rows(), opts(alpha=D('0.6')),
                                     header, SHIFT, elicit_hierarchy=elicit)
    prov = doc.provenance
    assert prov is not None and prov.kind == 'AHP_ENTROPY_COMBINED'
    for field in ('comparison_matrices', 'lambda_max', 'ci', 'ri', 'cr', 'expert_count',
                  'interview_dates', 'weights_geometric', 'weights_eigenvector',
                  'max_method_gap'):
        assert getattr(prov.ahp, field) is not None
    assert prov.ahp.expert_count == 1 and prov.ahp.cr < D('0.1')
    assert list(prov.ahp.interview_dates) == [date(2026, 1, 5)]
    ent = prov.entropy
    assert ent.calibration_periods == ['P1', 'P2']
    assert sorted(ent.per_period_entropy) == ['P1', 'P2']
    assert sorted(ent.per_period_entropy['P1']) == ['M1', 'M2', 'M3']
    assert sorted(ent.median_entropy) == ['M1', 'M2', 'M3']
    assert sorted(ent.drift_by_metric) == ['M1', 'M2', 'M3']
    assert ent.inactive_fallback_metrics == [] and ent.excluded_periods == {}
    comb = prov.combine
    assert eq_tol(comb.alpha, D('0.6'), TOL) and comb.alpha_source == 'MANUAL'
    assert comb.calibration_report_ref is None and prov.whatif_run_id == 'WIF-1'
    assert sorted(comb.hard_check_results) == list(wc.HARD_CHECK_IDS)
    assert all(value is True for value in comb.hard_check_results.values())
    assert sorted(comb.comparison_by_metric) == ['M1', 'M2', 'M3']
    assert prov.approved_by == header.approved_by
    assert prov.effective_from == header.effective_from and prov.effective_to == header.effective_to
    assert prov.alpha_basis is None and combined.feasible is True


def test_t_cmb_09_weight_table_matches_the_combination():
    '''[L1192]: level1/level2 of the draft are exactly the combined weights, and the
    published four-column table agrees with them row by row.'''
    combined, doc = wc.run_six_steps(mats(), facts(CONST), rows(), opts(), HDR, SHIFT,
                                     elicit_hierarchy=elicit)
    assert doc.level1_weights == {d: combined.dim_weights[d] for d in sorted(combined.dim_weights)}
    for dim in sorted(combined.metric_weights):
        assert doc.level2_weights[dim] == combined.metric_weights[dim]
    for metric_id, row in sorted(combined.comparison_by_metric.items()):
        assert isinstance(row, MetricWeightComparison)
        dim = combined.metric_trace[metric_id].dim_code
        assert eq_tol(row.combined_weight, doc.level2_weights[dim][metric_id], TOL)
    assert eq_tol(q12(sum(doc.level1_weights.values(), ZERO)), ONE, TOL)
    for dim in sorted(doc.level2_weights):
        assert eq_tol(q12(sum(doc.level2_weights[dim].values(), ZERO)), ONE, TOL)


# --- four column table, DRAFT status, real fixtures ------------------------
def test_four_column_comparison_table_is_traceable():
    '''[L1237] plus the four columns: AHP side / entropy side / combined before
    renormalisation / final after it, for every metric and for the dimension layer.'''
    combined = run(columns=CONST)
    for metric_id in sorted(SPEC):
        trace = combined.metric_trace[metric_id]
        row = combined.comparison_by_metric[metric_id]
        assert trace.dim_code == SPEC[metric_id]
        assert eq_tol(trace.ahp_weight, D(MW[SPEC[metric_id]][metric_id]), TOL)
        assert eq_tol(row.ahp_weight, trace.ahp_weight, TOL)
        assert (row.entropy_weight is None) == (trace.entropy_weight is None)
        assert eq_tol(row.combined_weight, trace.final_weight, TOL)
        assert row.is_fallback == trace.is_fallback
        assert eq_tol(combined.metric_weights[trace.dim_code][metric_id], trace.final_weight, TOL)
    mixed = combined.metric_trace['M1']
    assert mixed.is_fallback is False and mixed.entropy_weight is not None
    assert eq_tol(mixed.combined_raw_weight,
                  q12(D('0.5') * mixed.ahp_weight + D('0.5') * mixed.entropy_weight), TOL)
    fell = combined.metric_trace['M2']
    assert fell.is_fallback is True and fell.entropy_weight is not None
    assert fell.fallback_reason == RC.ENTROPY_INACTIVE_FALLBACK.value
    assert eq_tol(fell.combined_raw_weight, fell.ahp_weight, TOL)     # never alpha mixed
    assert not eq_tol(fell.combined_raw_weight,
                      q12(D('0.5') * fell.ahp_weight + D('0.5') * fell.entropy_weight), TOL)
    for dim in sorted(DIMS):
        assert eq_tol(combined.dim_raw_weight[dim],
                      q12(D('0.5') * D(DIMS[dim]) + D('0.5') * combined.dim_entropy_weight[dim]),
                      TOL)
        assert eq_tol(combined.ahp.dim_weights[dim], D(DIMS[dim]), TOL)


def test_status_is_draft_only_and_frozen_is_refused():
    '''[L600] / [L1071]: the product is DRAFT, asking this module for FROZEN raises.'''
    combined, doc = wc.run_six_steps(mats(), facts(COLS), rows(), opts(), HDR, SHIFT,
                                     elicit_hierarchy=elicit)
    assert doc.status == 'DRAFT' and combined.status == 'DRAFT'
    payload = combined.model_dump()
    payload['status'] = 'FROZEN'
    with pytest.raises(wc.FrozenStatusError):
        wc.CombinedWeights(**payload)
    with pytest.raises(wc.FrozenStatusError):
        wc.freeze(combined)
    with pytest.raises(wc.FrozenStatusError):
        wc.freeze()


FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures' / 'input'


def _jsonl(name):
    text = (FIXTURES / name).read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def mats(dim_weights=DIMS, metric_weights=MW):
    return {'dimension': {'E1': matrix(dim_weights)},
            'metrics_by_dim': {d: {'E1': matrix(metric_weights[d])} for d in sorted(metric_weights)}}


def test_build_draft_on_the_frozen_a1_fixtures():
    '''R-4 happy path on the frozen fixtures (12 strategies / 15 metrics / 5 periods).
    A1 construction 5 makes M_AUM_MINOR constant 10000, so it must fall back to its
    AHP weight 0.10 undiluted; 2026-Q3 keeps only 8 complete strategies and is
    dropped by [L575]; redline metrics never enter the entropy weights ([L1140]).'''
    metric_dict = _jsonl('metric_dict.jsonl')
    version = _jsonl('weight_version.jsonl')[0]
    history = {}
    for row in sorted(_jsonl('metric_fact.jsonl'),
                      key=lambda r: (r['period'], r['version_id'], r['strategy_id'],
                                     r['metric_id'])):
        if row['data_quality_flag'] == 'SUSPECT':
            continue
        history.setdefault(row['period'], {}).setdefault(row['metric_id'], {})[
            row['strategy_id']] = row['value']
    ahp_matrices = mats(version['level1_weights'], version['level2_weights'])
    options = wc.CombineOptions(alpha=D('0.5'), min_dim_weight=D('0.05'))
    combined, doc = wc.run_six_steps(ahp_matrices, history, metric_dict, options, HDR,
                                     SHIFT, elicit_hierarchy=elicit)
    assert doc.status == 'DRAFT' and combined.feasible is True
    assert combined.step_trace == wc.STEP_IDS
    assert combined.entropy.calibration_periods == ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')
    assert combined.entropy.excluded_periods == {'2026-Q3': RC.ENTROPY_PERIOD_SKIPPED.value}
    # 依据：A1c@6299245 D-A1-03（ORCH-37 第1条追认）：BLOCK 缺格载体 M_COMPLAINT_RATE→M_SATISFY_SCORE
    # 同维对调 missing_rule，2026-Q3 完整策略数 9→8。CMB-1 只读探针自冻结 fixtures 独立推导（非抄实现输出，R-14）：
    # metric_fact 896 行/15 指标/SUSPECT 0；2026-Q3 仅 176 行，4 个缺格 S-005×M_CAMPAIGN_COST_MINOR、
    # S-006×M_CUST_GAIN、S-008×M_SATISFY_SCORE、S-011×M_ROI 全落在 entropy（非红线）指标且分属 4 个不同策略
    # → 完整策略 12−4=8；其余四期各 12（8<entropy_min_strategies → ENTROPY_PERIOD_SKIPPED，[L575]）。
    assert combined.entropy.strategy_count_by_period['2026-Q3'] == 8
    assert 'M_AUM_MINOR' in combined.inactive_fallback_metrics
    assert eq_tol(combined.metric_weights['CONTRIB']['M_AUM_MINOR'], D('0.10'), TOL)
    assert eq_tol(combined.metric_trace['M_AUM_MINOR'].ahp_weight, D('0.10'), TOL)
    for metric_id in ('M_COMPLAINT_RATE', 'M_CONTACT_FREQ_PER_30D', 'M_OPTOUT_RATE'):
        assert combined.metric_trace[metric_id].is_fallback is True
        assert combined.metric_trace[metric_id].entropy_weight is None
    assert eq_tol(combined.metric_weights['EXPER']['M_COMPLAINT_RATE'], D('0.40'), TOL)
    assert eq_tol(combined.metric_weights['EXPER']['M_SATISFY_SCORE'], D('0.20'), TOL)
    for dim in sorted(version['level2_weights']):
        assert eq_tol(dim_sum(combined.metric_weights, dim), ONE, TOL)
    assert eq_tol(q12(sum(combined.dim_weights.values(), ZERO)), ONE, TOL)
    assert doc.provenance.kind == 'AHP_ENTROPY_COMBINED'
    assert doc.provenance.entropy.inactive_fallback_metrics == list(
        combined.inactive_fallback_metrics)


# --- P-14 / P-15 ------------------------------------------------------------
def unit(parts):
    '''Integer shares -> Decimal weights summing to exactly 1 (anchor on the last).'''
    keys = sorted(parts)
    total = sum((D(parts[k]) for k in keys), ZERO)
    out = {}
    acc = ZERO
    for key in keys[:-1]:
        out[key] = q12(D(parts[key]) / total)
        acc = acc + out[key]
    out[keys[-1]] = q12(ONE - acc)
    return {k: str(v) for k, v in out.items()}


@st.composite
def scenario(draw):
    dim_weights = unit({'D1': draw(st.integers(1, 9)), 'D2': draw(st.integers(1, 9))})
    metric_weights = {'D1': unit({'M1': draw(st.integers(1, 9)),
                                  'M2': draw(st.integers(1, 9))}),
                      'D2': unit({'M3': draw(st.integers(1, 9))})}
    columns = {}
    for metric_id in ('M1', 'M2', 'M3'):
        if draw(st.booleans()):
            base = str(draw(st.integers(1, 50)))
            columns[metric_id] = [base, base, base]        # zero variation -> INACTIVE
        else:
            columns[metric_id] = [str(draw(st.integers(1, 999))) for _ in range(3)]
    alpha = draw(st.decimals(min_value=D('0.5'), max_value=ONE, places=3,
                             allow_nan=False, allow_infinity=False))
    options = wc.CombineOptions(alpha=alpha, min_dim_weight=ZERO, entropy_min_strategies=3)
    return hierarchy(dim_weights, metric_weights), window(columns, options), options


@settings(max_examples=25, deadline=None)
@given(scenario())
def test_p14_combined_weights_are_normalised(case):
    '''P-14 [L1438]: for any alpha and any fallback combination, sum W_d = 1 and
    sum w_j = 1 per dimension within 1e-12.'''
    ahp, snapshot, options = case
    combined = wc.combine(ahp, snapshot, options)
    assert eq_tol(q12(sum((D(combined.dim_weights[d]) for d in sorted(combined.dim_weights)),
                          ZERO)), ONE, TOL)
    for dim in sorted(combined.metric_weights):
        assert eq_tol(dim_sum(combined.metric_weights, dim), ONE, TOL)
    assert combined.hard_checks.results['H-1'] is True
    assert all(v >= ZERO for v in combined.dim_weights.values())


@settings(max_examples=25, deadline=None)
@given(scenario())
def test_p15_fallback_keeps_the_ahp_weight(case):
    '''P-15 [L1439]: a metric flagged ENTROPY_INACTIVE_FALLBACK keeps its AHP weight
    exactly (1e-12), both before and after the dimension renormalisation.'''
    ahp, snapshot, options = case
    combined = wc.combine(ahp, snapshot, options)
    for metric_id in combined.inactive_fallback_metrics:
        trace = combined.metric_trace[metric_id]
        assert trace.is_fallback is True
        assert trace.fallback_reason in (RC.ENTROPY_INACTIVE_FALLBACK.value,
                                         RC.INACTIVE_METRIC.value)
        assert eq_tol(trace.combined_raw_weight, trace.ahp_weight, TOL)
        assert eq_tol(trace.final_weight, trace.ahp_weight, TOL)
        assert eq_tol(combined.metric_weights[trace.dim_code][metric_id],
                      combined.ahp.metric_weights[trace.dim_code][metric_id], TOL)
        assert eq_tol(combined.comparison_by_metric[metric_id].combined_weight,
                      combined.comparison_by_metric[metric_id].ahp_weight, TOL)
    if snapshot is None:
        assert eq_tol(combined.alpha, ONE, TOL)
        assert len(combined.inactive_fallback_metrics) == 3
