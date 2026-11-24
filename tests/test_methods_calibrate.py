'''tests/test_methods_calibrate.py -- A3 guards T-CAL-01~04, P-11~P-13, V-19 (digest M09).

Every test carries the guard id it exists for; nothing else is asserted (R-9). Golden
numbers come from hand arithmetic on the constructed AHP weights and facts, never from
this implementation's own output (R-14).

The hand arithmetic behind the goldens below, all exact Decimal:
  AHP  W = (D1 0.6, D2 0.4); w(D1) = (M1 0.5, M2 0.3, M3 0.2); w(D2) = (M4 1).
  P1 facts  M1 = (10, 20, 30), M2 = (30, 20, 10), M3 = (7, 7, 7), M4 = (5, 5, 5).
       M1 and M2 are permutations of one another, so after the [L540] shift they carry
       the SAME multiset of proportions p_ij, hence the same e_j ([L542]) and the same
       d_j ([L543]); with d_3 = d_4 = 0 the normalisation of [L544] gives
       w(entropy) = (0.5, 0.5, 0, 0) exactly -- no logarithm has to be evaluated.
       M3 and M4 are zero variation, so [L584] makes them INACTIVE fallbacks that keep
       w_j(AHP) verbatim, and Step 4 redistributes only the residual 1 - 0.2 = 0.8:
         raw_1 = a*0.5 + (1-a)*0.5 = 0.5
         raw_2 = a*0.3 + (1-a)*0.5 = 0.5 - 0.2a
         w_1 = 0.8 * 0.5 / (1 - 0.2a), w_2 = 0.8 - w_1, w_3 = 0.2, w_4 = 1
         W_D1 = a*0.6 + (1-a)*1 = 1 - 0.4a, W_D2 = 0.4a     (sum is exactly 1)
       At a = 0.5:  W = (0.8, 0.2), w_1 = 4/9, w_2 = 16/45, w_3 = 0.2,
       effective W_d*w_j = (3.2/9, 12.8/45, 0.16, 0.2).
  P2 facts  every column constant -> d_j = 0 for all j -> [L545] emits no entropy
       weight -> the period is excluded and combine() degrades it to a = 1 ([L577]),
       i.e. EXACTLY the AHP weights: W = (0.6, 0.4), effective = (0.3, 0.18, 0.12, 0.4).
  weight_drift(0.5) = max(level1, effective) ([L619] names no layer):
       level1    = |0.8-0.6| + |0.2-0.4|                          = 0.4
       effective = |3.2/9-0.3| + |12.8/45-0.18| + |0.16-0.12| + |0.2-0.4|
                 = 0.5/9 + 4.7/45 + 0.04 + 0.2 = 2.5/45 + 4.7/45 + 0.24 = 0.4
       so weight_drift(0.5) = 0.4 exactly, and weight_drift(1) = 0 exactly.
  boundary_ratio: floors (0.80, 0.60, 0.40, 0.00), epsilon 0.02.
       P1 composites (0.80, 0.615, 0.50) -> hits 2 of 3 (0.80 on the floor, 0.615 within
       0.015 of 0.60); P2 (0.90, 0.70, 0.41) -> hits 1 of 3. Window max = 2/3.
  oat_flip_rate: P1 0.04, P2 0.02 -> window max 0.04 <= stable_max 0.05.
  mean_spearman: P1 0.90, P2 0.86 -> window mean 0.88 >= divergence_threshold 0.80.
'''
from datetime import date, datetime
from decimal import Decimal

import pytest

from dsm import numeric, weights_ahp
from dsm import weights_calibrate as wcal
from dsm import weights_combine as wc
from dsm.grading import GradeRuleSet
from dsm.models import (AttainmentFrame, EvidenceFrame, GradeFrame, NormalizedFrame,
                        PoolFrame, PoolStats, RedlineFrame, ScoreFrame, ScoringContext,
                        WeightProvenance)
from dsm.numeric import D, ONE, TOL, ZERO, eq_tol, q12
from dsm.reason_codes import RC

Q20 = Decimal('1E-20')
DAY = date(2026, 1, 1)
DAY_END = date(2026, 12, 31)
RUN_AT = datetime(2026, 1, 1, 9, 0, 0)
SHIFT = D('0.000001')          # [L540] technical epsilon: an input, the digest gives no value
SEED = 20260101
PERIODS = ('P1', 'P2')
IDS = ('S-1', 'S-2', 'S-3')
DIMS = {'D1': '0.6', 'D2': '0.4'}
MW = {'D1': {'M1': '0.5', 'M2': '0.3', 'M3': '0.2'}, 'D2': {'M4': '1'}}
SPEC = {'M1': 'D1', 'M2': 'D1', 'M3': 'D1', 'M4': 'D2'}
FACTS1 = {'M1': ('10', '20', '30'), 'M2': ('30', '20', '10'),
          'M3': ('7', '7', '7'), 'M4': ('5', '5', '5')}
FACTS2 = {'M1': ('4', '4', '4'), 'M2': ('4', '4', '4'),
          'M3': ('4', '4', '4'), 'M4': ('4', '4', '4')}
FLOORS = {'L1': '0.80', 'L2': '0.60', 'L3': '0.40', 'L4': '0.00'}
BASE_BUDGET = {'alpha_floor': '0.50', 'drift_budget': '0.50', 'boundary_budget': '0.70',
               'boundary_epsilon': '0.02', 'stable_max': '0.05',
               'divergence_threshold': '0.80', 'min_dim_weight': '0.05',
               'max_shift_from_ahp': '0.50'}
GRID = ('0.50', '0.75', '1.00')
COMPOSITE = {'P1': {'S-1': '0.80', 'S-2': '0.615', 'S-3': '0.50'},
             'P2': {'S-1': '0.90', 'S-2': '0.70', 'S-3': '0.41'}}
OAT = {'P1': '0.04', 'P2': '0.02'}
RHO = {'P1': '0.90', 'P2': '0.86'}


def matrix(weights):
    '''A perfectly consistent pairwise matrix a_ij = w_i / w_j, so CR = 0 ([L518]).'''
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


def hierarchy():
    return snapshot(weights_ahp.elicit_hierarchy(
        {'E1': matrix(DIMS)}, {d: {'E1': matrix(MW[d])} for d in sorted(MW)}))


def metric_rows():
    return [{'metric_id': m, 'dim_code': SPEC[m], 'direction': 1, 'is_redline': False}
            for m in sorted(SPEC)]


def facts(columns):
    return {m: {s: columns[m][i] for i, s in enumerate(IDS)} for m in sorted(columns)}


def cfg(**over):
    '''The signed governance budget (K-11 / K-15~K-20). Test data, never a default the
    module may pick for itself (R-12).'''
    block = dict(BASE_BUDGET)
    block.update(over)
    return {'eval_config': {'weight_construction': block}}


def rule_rows():
    from dsm.models import GradeRuleRow
    return tuple(GradeRuleRow(
        grade_code=code, grade_label=code, attainment_floor=D(FLOORS[code]),
        evidence_class_min='D', redline_pass_required=True, promotion_streak=0,
        max_grade_if_no_target='L4') for code in ('L1', 'L2', 'L3', 'L4'))


def ruleset():
    return GradeRuleSet(rows=rule_rows(), min_coverage_for_absolute_track=D('0.5'))


def context(period):
    '''A minimal ScoringContext: the Step 1-4 frames the injected pipeline reuses. Only
    `period` is read by the fake pipelines below, so the frames stay empty (R-2).'''
    return ScoringContext(
        period=period, run_at=RUN_AT, run_id='run-a3', seed=SEED,
        weight_version_id='WV-A3', evidence_mode='GATE_ONLY', cel_enabled=False,
        input_fingerprints={}, attainment=AttainmentFrame(rows=(), attainment_coverage={}),
        normalized=NormalizedFrame(rows=()), evidence=EvidenceFrame(rows=()),
        redline=RedlineFrame(rows=()), score=ScoreFrame(rows=()),
        grade=GradeFrame(rows=()), pool=PoolFrame(rows=()),
        pool_stats=PoolStats(rows=(), evidence_structure={'A': 0, 'B': 0, 'C': 0, 'D': 0},
                             not_assessed_count=0, not_assessed_reasons={}))


def case(period, columns):
    return wcal.PeriodCase(period=period, facts=facts(columns), context=context(period),
                           rules=ruleset())


def header():
    return wc.DraftHeader(weight_version_id='WV-A3', approved_by='SYNTH_APPROVER',
                          approved_date=DAY, effective_from=DAY, effective_to=DAY_END)


def fake_pipeline(composite=None, oat=None, rho=None, seen=None):
    '''Test-owned Step 5-7 stub. The four indicators read only what it returns, so every
    golden below is hand-set arithmetic rather than an implementation echo (R-14).'''
    composite = COMPOSITE if composite is None else composite
    oat = OAT if oat is None else oat
    rho = RHO if rho is None else rho

    def pipeline(case, combined, alpha):
        if seen is not None:
            seen.append((str(alpha), case.period, id(case.context.redline),
                         id(case.context.evidence), id(case.rules),
                         {d: str(v) for d, v in sorted(combined.dim_weights.items())}))
        keys = sorted(composite[case.period])
        return wcal.PeriodRun(
            period=case.period,
            composite_absolute={(s, 'V1', case.period): D(composite[case.period][s])
                                for s in keys},
            oat_flip_rate=D(oat[case.period]), mean_rho=D(rho[case.period]))

    return pipeline


# ORCH-29 ruling 3: [L294] lets L0b import L1-L5 only, so weights_calibrate no longer
# imports weights_combine -- the four capabilities it needs are keyword-only REQUIRED
# injections on CalibrationInputs, wired here exactly the way dsm/cli.py wires them.
HOOKS = {'combine_fn': wc.combine, 'options_fn': wc.CombineOptions,
         'entropy_window_fn': wc.calibrate_entropy_window,
         'insufficient_sample_error': wc.EntropyInsufficientSample}


def inputs(pipeline=None, **over):
    kwargs = {'hierarchy': hierarchy(), 'metric_dict': metric_rows(), 'shift': SHIFT,
              'period_cases': {p: case(p, FACTS1 if p == 'P1' else FACTS2) for p in PERIODS},
              'run_id': 'cal-a3-1', 'seed': SEED, 'draft_header': header(),
              'pipeline': pipeline or fake_pipeline(),
              'option_overrides': {'entropy_min_strategies': 3}}
    kwargs.update(HOOKS)
    kwargs.update(over)
    return wcal.CalibrationInputs(**kwargs)


def run(grid=GRID, config=None, **over):
    return wcal.calibrate(grid, list(PERIODS), inputs(**over), config or cfg())


# --- T-CAL-01: the four stability indicators against hand arithmetic --------
def test_t_cal_01_weight_drift_matches_hand_arithmetic():
    '''[L619]. alpha = 0.5: level1 0.4 and effective 0.4 (see the module docstring
    arithmetic), so the constrained maximum is 0.4 exactly. alpha = 1: P1 collapses onto
    the AHP weights, which is what the degraded P2 already is, so the drift is 0.'''
    report = run()
    half = report.row(D('0.5'))
    assert eq_tol(half.weight_drift, D('0.4'), TOL)
    assert eq_tol(half.weight_drift_level1, D('0.4'), TOL)
    assert eq_tol(half.weight_drift_effective, D('0.4'), TOL)
    top = report.row(ONE)
    assert top.weight_drift == ZERO
    assert top.weight_drift_level1 == ZERO
    assert top.weight_drift_effective == ZERO


def test_t_cal_01_boundary_ratio_counts_are_int_and_the_ratio_is_the_window_max():
    '''[L620]. P1 puts 2 of 3 assessed strategies within 0.02 of a floor (0.80 sits ON
    the 0.80 floor, 0.615 is 0.015 from 0.60, 0.50 is 0.10 from both 0.40 and 0.60);
    P2 puts 1 of 3 (0.41 is 0.01 from 0.40). Counts are int (H-4 / V-9), the constrained
    value is the window MAXIMUM 2/3, and the quotient never passes through a float.'''
    report = run()
    row = report.row(D('0.5'))
    assert row.boundary_hits_by_period == {'P1': 2, 'P2': 1}
    assert row.assessed_by_period == {'P1': 3, 'P2': 3}
    assert all(isinstance(v, int) for v in row.boundary_hits_by_period.values())
    assert all(isinstance(v, int) for v in row.assessed_by_period.values())
    assert eq_tol(row.boundary_ratio, D(2) / D(3), TOL)


def test_t_cal_01_oat_flip_rate_is_the_window_maximum_and_mean_spearman_the_mean():
    '''[L621] takes the OAT +-10% overall_flip_rate and [L622] the MEAN Spearman across
    the window periods: max(0.04, 0.02) = 0.04 and mean(0.90, 0.86) = 0.88.'''
    report = run()
    row = report.row(D('0.5'))
    assert eq_tol(row.oat_flip_rate, D('0.04'), TOL)
    assert eq_tol(row.mean_spearman, D('0.88'), TOL)


def test_t_cal_01_hard_constraints_come_from_weights_combine_not_from_here():
    '''[L623]. H-5 measures the same L1 shift as weight_drift against max_shift_from_ahp;
    tightening that SIGNED budget below the hand-computed 0.4 must flip hard_constraints
    to False and name H-5, with no re-implementation of Step 5 in this package (R-7).'''
    report = run(config=cfg(max_shift_from_ahp='0.30'))
    row = report.row(D('0.5'))
    assert row.hard_constraints is False
    assert row.hard_violations == ('H-5',)
    assert row.violations == (wcal.HARD,)
    assert row.feasible is False
    assert report.row(ONE).hard_constraints is True


# --- the lexicographic feasible set, NOT a weighted objective function ------
def test_lexicographic_not_a_weighted_objective():
    '''[L606] / [L608]. alpha = 0.50 has the SMALLEST weight_drift of the two feasible
    candidates on drift but is pushed out by boundary_ratio; a weighted objective
    lambda1*drift + lambda2*boundary + lambda3*(1-rho) would still pick it for a large
    enough lambda1. The lexicographic rule must pick 0.75 instead, and the report must
    expose no aggregate score column that anyone could re-weight.'''
    breach = {p: dict(COMPOSITE[p]) for p in PERIODS}
    for sid in IDS:            # at 0.50 every P1 strategy sits on a floor -> ratio 1 > 0.70
        breach['P1'][sid] = '0.80'

    def pipeline(case, combined, alpha):
        table = breach if str(alpha) == '0.500000000000' else COMPOSITE
        return wcal.PeriodRun(period=case.period,
                              composite_absolute={(s, 'V1', case.period):
                                                  D(table[case.period][s]) for s in IDS},
                              oat_flip_rate=D(OAT[case.period]),
                              mean_rho=D(RHO[case.period]))

    report = run(grid=('0.50', '0.75', '1.00'), config=cfg(boundary_budget='0.70'),
                 pipeline=pipeline)
    half = report.row(D('0.5'))
    assert half.violations == (wcal.BOUNDARY,)
    assert eq_tol(half.boundary_ratio, ONE, TOL)
    assert report.alpha_star == q12(D('0.75'))
    assert report.feasible_alphas == (q12(D('0.75')), ONE)
    assert report.excluded_alphas[q12(D('0.5'))] == RC.ALPHA_INFEASIBLE.value
    # No lambda, no aggregate score: the matrix carries only the five raw indicators.
    for row in report.rows:
        dumped = row.model_dump()
        assert not any(k for k in dumped if 'score' in k or 'lambda' in k
                       or 'objective' in k or 'cost' in k)
    basis = report.to_alpha_basis()
    for columns in basis.candidate_alpha_matrix.values():
        assert set(columns) <= {'evaluated', 'alpha_floor_ok', wcal.HARD, wcal.DRIFT,
                                wcal.BOUNDARY, wcal.OAT, wcal.SPEARMAN}


def test_whole_grid_is_traversed_and_never_short_circuited():
    '''[L625] 必须遍历全网格. A feasible alpha smaller than another feasible one does not
    stop the scan: every candidate has a row, the larger feasible alphas stay listed, and
    alpha* is the minimum -- not the first hit of a walk that stopped early.'''
    report = run(grid=('0.50', '0.60', '0.75', '1.00'))
    assert tuple(str(row.alpha) for row in report.rows) == ('0.500000000000',
                                                            '0.600000000000',
                                                            '0.750000000000',
                                                            '1.000000000000')
    assert all(row.evaluated for row in report.rows)
    assert len(report.feasible_alphas) == 4
    assert report.alpha_star == q12(D('0.5'))
    assert report.binding_constraints == ()


# --- T-CAL-02: monotonicity is checked empirically, a counter-example warns -
def test_t_cal_02_hole_in_the_feasible_set_warns_without_raising():
    '''[L625]. A feasible set with a hole must be reported, listing every feasible alpha
    for a human choice, and must NOT raise: NON_MONOTONIC_WARNING is a warning.'''
    oat = {'P1': '0.04', 'P2': '0.30'}    # only P2 breaches, and only for one alpha
    def pipeline(case, combined, alpha):
        rate = '0.30' if (case.period == 'P2' and str(alpha) == '0.750000000000') else '0.02'
        return wcal.PeriodRun(period=case.period,
                              composite_absolute={(s, 'V1', case.period):
                                                  D(COMPOSITE[case.period][s]) for s in IDS},
                              oat_flip_rate=D(rate), mean_rho=D(RHO[case.period]))
    report = run(grid=('0.50', '0.75', '1.00'), pipeline=pipeline)
    del oat
    assert report.row(D('0.75')).feasible is False
    assert report.feasible_alphas == (q12(D('0.5')), ONE)
    assert RC.NON_MONOTONIC_WARNING.value in report.notices
    assert any('not a contiguous interval' in text for text in report.non_monotonic)
    assert report.alpha_star == q12(D('0.5'))      # still the minimum, never an error


def test_t_cal_02_a_monotone_run_does_not_warn():
    '''[L625] conversely: a contiguous feasible suffix raises no NON_MONOTONIC_WARNING,
    so the warning of the test above is earned rather than always on.'''
    report = run(grid=('0.50', '0.75', '1.00'), config=cfg(drift_budget='0.05'))
    assert report.feasible_alphas == (ONE,)
    assert RC.NON_MONOTONIC_WARNING.value not in report.notices
    assert report.non_monotonic == ()


# --- T-CAL-03: the same seed gives byte-identical reports -------------------
def test_t_cal_03_same_seed_is_byte_identical_and_a_different_seed_is_not():
    '''[L636] records the seed; H-8 keeps the clock and every unseeded generator out, so
    one seed must reproduce the report byte for byte and another seed must not.'''
    first = run().model_dump_json()
    second = run().model_dump_json()
    assert first == second
    other = wcal.calibrate(list(GRID), list(PERIODS),
                           inputs(seed=SEED + 1), cfg()).model_dump_json()
    assert other != first


# --- T-CAL-04 / P-13: the governance budget cannot be touched by calibrate --
def test_t_cal_04_p13_the_config_object_is_never_modified():
    '''[L638] / P-13. calibrate() reads K-11 / K-15~K-20 and must leave the signed
    configuration byte-identical, and the report must quote the same values back.'''
    import copy
    config = cfg()
    before = copy.deepcopy(config)
    report = run(config=config)
    assert config == before
    for key, value in BASE_BUDGET.items():
        assert eq_tol(getattr(report.budget, key), D(value), TOL)
    assert report.budget.min_metric_weight is None


def test_t_cal_04_p13_a_tighter_budget_moves_alpha_star_and_not_the_budget():
    '''RK-12: the ONLY way to a smaller alpha* is a signed budget change, never a
    relaxation inside the run. drift(0.5) = 0.4 by hand, so drift_budget 0.40 keeps 0.50
    feasible while 0.39 pushes alpha* to 0.75 (drift 0.2 by hand) and 0.19 to 1.0.'''
    assert run(config=cfg(drift_budget='0.40')).alpha_star == q12(D('0.5'))
    mid = run(config=cfg(drift_budget='0.39'))
    assert mid.alpha_star == q12(D('0.75'))
    assert eq_tol(mid.row(D('0.75')).weight_drift, D('0.2'), TOL)
    assert wcal.DRIFT in mid.binding_constraints
    top = run(config=cfg(drift_budget='0.19'))
    assert top.alpha_star == ONE
    for report in (mid, top):
        for key, value in BASE_BUDGET.items():
            if key != 'drift_budget':
                assert eq_tol(getattr(report.budget, key), D(value), TOL)


def test_p13_a_placeholder_budget_is_refused_not_guessed():
    '''R-12 / K-15~K-20: an unsigned slot must stop the run rather than be filled in.'''
    for key in wcal.BUDGET_KEYS:
        with pytest.raises(wcal.MissingBudgetError):
            run(config=cfg(**{key: 'PLACEHOLDER'}))
        with pytest.raises(wcal.MissingBudgetError):
            run(config=cfg(**{key: None}))


def test_p13_a_missing_budget_is_refused_not_defaulted():
    '''R-12: no key of [L638] has a default in this module, so an absent one raises.'''
    for key in wcal.BUDGET_KEYS:
        block = {k: v for k, v in BASE_BUDGET.items() if k != key}
        with pytest.raises(wcal.MissingBudgetError):
            wcal.calibrate(list(GRID), list(PERIODS), inputs(),
                           {'eval_config': {'weight_construction': block}})


def test_p13_a_budget_that_moves_underneath_the_run_is_refused():
    '''P-13 machine guard: the budget is frozen at entry and re-read from the SAME config
    object at exit, so a configuration widened while calibrate() runs -- the RK-12 attack,
    buying a smaller alpha* by loosening drift_budget -- is refused, never reported.'''
    config = cfg()
    block = config['eval_config']['weight_construction']
    calls = []

    def widening(case, combined, alpha):
        calls.append(str(alpha))
        if len(calls) == 1:
            block['drift_budget'] = '0.99'      # widened mid-run, behind calibrate's back
        return fake_pipeline()(case, combined, alpha)

    with pytest.raises(wcal.GovernanceBudgetTamperError) as info:
        wcal.calibrate(list(GRID), list(PERIODS), inputs(pipeline=widening), config)
    assert 'drift_budget' in str(info.value)
    assert eq_tol(run(config=cfg()).budget.drift_budget, D('0.5'), TOL)


# --- V-19: alpha_floor is applied or refused, never silently widened --------
def test_v19_a_candidate_below_the_floor_is_clamped_up_to_the_floor():
    '''[L609] / [L633]. 0.40 is below alpha_floor 0.50, so key 1 of the lexicographic
    order excludes it WITHOUT evaluation (weights_combine refuses it too, [L562]); the
    result is the floor itself, labelled with the registered ALPHA_FLOOR_APPLIED.'''
    report = run(grid=('0.40', '0.50', '1.00'))
    assert report.alpha_star == q12(D('0.5'))
    low = report.row(D('0.40'))
    assert (low.evaluated, low.alpha_floor_ok, low.feasible) == (False, False, False)
    assert low.weight_drift is None and low.boundary_ratio is None
    assert report.excluded_alphas[q12(D('0.40'))] == RC.ALPHA_FLOOR_INFEASIBLE.value
    assert RC.ALPHA_FLOOR_APPLIED.value in report.notices


def test_v19_an_infeasible_floor_raises_instead_of_degrading():
    '''[L633] / V-14. With divergence_threshold 0.95 no candidate reaches mean_spearman
    0.88, so the floor itself is infeasible while 0.40 sits below it: taking 0.40 would
    widen K-15 silently, so the run raises with the registered reason code.'''
    with pytest.raises(wcal.AlphaFloorInfeasibleError) as info:
        run(grid=('0.40', '0.50', '1.00'), config=cfg(divergence_threshold='0.95'))
    assert info.value.reason_code == RC.ALPHA_FLOOR_INFEASIBLE.value
    assert info.value.violation_matrix['0.500000000000'] == (wcal.SPEARMAN,)
    assert info.value.violation_matrix['1.000000000000'] == (wcal.SPEARMAN,)


def test_v14_an_empty_feasible_set_raises_with_the_whole_violation_matrix():
    '''[L631] / V-14. No candidate may pass silently: the error carries which constraint
    every alpha broke, and cli.py maps the class name to exit code 7.'''
    with pytest.raises(wcal.AlphaInfeasibleError) as info:
        run(config=cfg(divergence_threshold='0.95'))
    error = info.value
    assert error.reason_code == RC.ALPHA_INFEASIBLE.value
    assert sorted(error.violation_matrix) == ['0.500000000000', '0.750000000000',
                                              '1.000000000000']
    for alpha, violations in error.violation_matrix.items():
        assert wcal.SPEARMAN in violations
    assert wcal.SPEARMAN in error.rows[0].violations


def test_l632_alpha_star_one_declares_pure_ahp_on_the_first_page():
    '''[L632]. alpha* = 1 is a normal, valuable result, but it must be declared on the
    first page rather than buried: ALPHA_PURE_AHP plus a prominent statement.'''
    report = run(config=cfg(drift_budget='0.05'))
    assert report.alpha_star == ONE
    assert RC.ALPHA_PURE_AHP.value in report.notices
    assert report.prominent_notice and '纯 AHP' in report.prominent_notice
    assert report.calibration_skipped is False


def test_l634_an_unusable_entropy_window_skips_the_calibration_to_alpha_one():
    '''[L634]. Every column of every period is constant, so [L545] emits no entropy weight
    anywhere: the calibration is skipped, alpha = 1, ENTROPY_INSUFFICIENT_SAMPLE, and the
    grid is never scanned (no rows at all) rather than quietly returning a feasible set.'''
    both = {'P1': FACTS2, 'P2': FACTS2}
    report = wcal.calibrate(list(GRID), list(PERIODS),
                            inputs(period_cases={p: case(p, both[p]) for p in PERIODS}),
                            cfg())
    assert report.calibration_skipped is True
    assert report.alpha_star == ONE
    assert report.rows == ()
    assert RC.ENTROPY_INSUFFICIENT_SAMPLE.value in report.notices
    assert report.prominent_notice and '跳过标定' in report.prominent_notice


# --- P-11 / P-12 ------------------------------------------------------------
def test_p11_alpha_basis_closes_the_provenance_chain():
    '''[L636] / [L1435] P-11 / V-15: the whole report becomes the alpha_basis segment of
    WeightProvenance, carrying alpha*, the candidate x indicator matrix, the excluded
    alphas with registered reasons, the window periods, run_id and seed. Nothing is
    invented: run_id and seed are the caller's.'''
    report = run()
    basis = report.to_alpha_basis()
    provenance = WeightProvenance(
        kind='AHP_ENTROPY_COMBINED', approved_by='SYNTH_APPROVER', approved_date=DAY,
        effective_from=DAY, effective_to=DAY_END, alpha_basis=basis,
        whatif_run_id='WIF-1')
    assert provenance.alpha_basis.alpha_star == q12(D('0.5'))
    assert provenance.alpha_basis.run_id == 'cal-a3-1'
    assert provenance.alpha_basis.seed == SEED
    assert provenance.alpha_basis.window_periods == ['P1', 'P2']
    assert sorted(provenance.alpha_basis.candidate_alpha_matrix) == [q12(D('0.5')),
                                                                    q12(D('0.75')), ONE]
    columns = provenance.alpha_basis.candidate_alpha_matrix[q12(D('0.5'))]
    assert eq_tol(columns[wcal.DRIFT], D('0.4'), TOL)
    assert columns[wcal.HARD] == ONE
    assert provenance.alpha_basis.binding_constraints == []


def test_p12_alpha_moves_only_the_weights_and_never_a_gate_input():
    '''[L1436] P-12: a weight change must never become a way around a gate. Across the
    whole grid the redline frame, the evidence frame and the grade rule set handed to
    Step 5-7 are the SAME objects (identity, not equality) while only the weights move.'''
    seen = []
    report = run(grid=('0.50', '0.75', '1.00'), pipeline=fake_pipeline(seen=seen))
    assert len(seen) == 6                            # 3 alphas x 2 periods, nothing skipped
    gates = {}
    for alpha, period, redline_id, evidence_id, rules_id, dim_weights in seen:
        gates.setdefault(period, set()).add((redline_id, evidence_id, rules_id))
    assert sorted(gates) == ['P1', 'P2']
    # Within a period the gate inputs are the SAME objects for every alpha: identity,
    # not equality, so no alpha can reach a different redline / evidence / rule gate.
    assert all(len(ids) == 1 for ids in gates.values())
    weights = {tuple(sorted(item[5].items())) for item in seen if item[1] == 'P1'}
    assert len(weights) == 3                         # only the weights move
    assert report.alpha_star == q12(D('0.5'))


# --- inputs are required, never defaulted (R-12) ----------------------------
def test_grid_window_and_shift_are_required_inputs():
    '''R-12 / [L613] / [L540]: the digest fixes no window and no shift, so an absent one
    raises instead of being filled in; an out-of-band alpha or a one-period window too.'''
    with pytest.raises(wcal.GridError):
        wcal.calibrate(None, list(PERIODS), inputs(), cfg())
    with pytest.raises(wcal.GridError):
        wcal.calibrate((), list(PERIODS), inputs(), cfg())
    with pytest.raises(wcal.GridError):
        wcal.calibrate(('1.5',), list(PERIODS), inputs(), cfg())
    with pytest.raises(wcal.WindowError):
        wcal.calibrate(list(GRID), None, inputs(), cfg())
    with pytest.raises(wcal.WindowError):
        wcal.calibrate(list(GRID), ['P1'], inputs(), cfg())
    with pytest.raises(wcal.WindowError):
        wcal.calibrate(list(GRID), ['P1', 'P9'], inputs(), cfg())
    with pytest.raises(wcal.CalibrateError):
        wcal.calibrate(list(GRID), list(PERIODS), inputs(shift=None), cfg())
    with pytest.raises(wcal.HookRequiredError):
        run(pipeline=lambda c, w, a: wcal.PeriodRun(
            period=c.period,
            composite_absolute={(s, 'V1', c.period): D(COMPOSITE[c.period][s]) for s in IDS},
            oat_flip_rate=None, mean_rho=D('0.9')))


def test_default_grid_is_the_digest_eleven_points():
    '''[L613] verbatim: {0.50, 0.55, ..., 1.00}, 11 points, step 0.05, Decimal only.'''
    grid = wcal.default_grid()
    assert len(grid) == 11
    assert grid[0] == D('0.5') and grid[-1] == ONE
    assert all(isinstance(value, Decimal) for value in grid)
    assert all(right - left == D('0.05') for left, right in zip(grid, grid[1:]))


def test_v9_no_report_value_is_a_float():
    '''V-9: every published number is a Decimal (ratios, 1e-12) or an int (counts). A
    float anywhere in the report would mean an approximation entered the audit chain.'''

    def walk(node):
        if isinstance(node, float):
            raise AssertionError('a float reached the report: ' + repr(node))
        if isinstance(node, dict):
            for key, value in node.items():
                walk(key)
                walk(value)
        elif isinstance(node, (list, tuple)):
            for item in node:
                walk(item)

    walk(run().model_dump())
