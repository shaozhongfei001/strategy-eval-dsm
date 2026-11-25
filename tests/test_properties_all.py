'''tests/test_properties_all.py -- E4: SDD 3.16.3 P-1~P-15 global property layer.

Sole source of truth: docs/digest/M32-tests-properties.md (SDD 1421-1440,
verbatim quotes in each docstring; the properties are not re-invented here).
Guard target: V-2. Dev-phase gauge is max_examples=25 per R-11; the 500-example
V-2 contract tier (P-1~P-15 each at 500 examples, contract L1495) is opt-in
via MAXEX_500 / DSM_HYPOTHESIS_EXAMPLES=500 so a plain regression run stays fast.

Independence (anti-cheat control): this is a verification-lane artifact. It
reads dsm/** only and never edits it; an implementation conflict stays RED
and is reported, never softened (RED-first whitelist includes every module
touched here).

Expected values derive from the SDD caliber (V-9: money/count exact, ratio
Decimal tolerance 1e-12 via numeric.TOL). No expected value is read back from
an implementation output (R-14). Every governance number used below is a
SYN-labelled test fixture value, never a business number (K-01~K-20 stay
PLACEHOLDER in production config; nothing here defaults a missing one).

Relationship to the pre-existing module-local property tests (none removed):
  P-2   tests/test_redline.py::test_p2_property_hard_crossing_always_forces_declared_grade
        (redline-internal layer)      -> the E4 global version runs through grading.assign
  P-4   tests/test_normalize.py::test_p4_adding_non_anchor_strategies_keeps_existing_norms
        (norm layer only)              -> the E4 global version also locks grade (full chain)
  P-6   tests/test_pooling.py P-6 cases (pool layer, hand-built frames)
        -> the E4 global version runs evidence.classify -> pooling.build end to end
  P-10  tests/test_config_properties.py::test_t05_j_p03_load_all_raises_config_placeholder_error_with_exit_code_three
        (single file eval_config)      -> the E4 global version spans ALL SIX config stems
  P-14  tests/test_methods_combine.py::test_p14_combined_weights_are_normalised
  P-15  tests/test_methods_combine.py::test_p15_fallback_keeps_the_ahp_weight
        (CombinedWeights object layer) -> the E4 global version checks the PUBLISHED
        WeightVersionDoc and its consumption by dsm.aggregate
P-13b calibration half: EFIX-1 (E4b) replaced the gated body (written
  against an EXPECTED signature -- inputs=None + window={'periods':
  [...]} + TypeError-only capture -- that no V-14-compliant
  implementation can pass; it now drives the real CalibrationInputs
  contract of dsm/weights_calibrate.py (A3, 2de42db).
P-11/P-12/P-13a are NOT gated: the FROZEN-provenance completeness rule of [L1435]
is config-layer policy already landed (config.validate_weights / _frozen_provenance
序5+6+7), and alpha governance invariance is drivable through the landed
weights_combine -- waiting for A3/A4 modules would only weaken these guards.
'''
import copy
import datetime as dt
import os
import tempfile
from decimal import Decimal

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from dsm import (aggregate, attainment, audit, config, evidence, grading,
                 normalize, numeric, pooling, redline, sensitivity,
                 weights_ahp, weights_calibrate, weights_combine)
from dsm.attainment import AttainmentParams
from dsm.evidence import EvidenceParams
from dsm.models import (AnchorSetDoc, AttainmentFrame, AttainmentRow,
                        DesignCardRow, EvidenceFrame, EvidenceRow,
                        GradeFrame, GradeLedgerRow, GradeRuleRow, GradeRow,
                        MetricDictRow, MetricFactRow, NormalizedFrame,
                        NormalizedRow, PoolFrame, PoolKey, PoolStats,
                        RedlineEvalRow, RedlineFrame,
                        ScoreCardRow, ScoreFrame, ScoreRow, ScoringContext,
                        SensitivityReport,
                        SensitivitySchemeResult, StrategyMasterRow,
                        WeightVersionDoc)
from dsm.numeric import (D, ONE, TOL, ZERO, eq_exact, eq_tol,
                      from_minor, q12, to_minor)
from dsm.normalize import NormalizeParams
from dsm.pooling import PoolingParams
from dsm.reason_codes import RC

wc = weights_combine
wcal = weights_calibrate
# V-2 contract tier: P-1~P-15 at hypothesis 500 examples each (contract L1495).
# It is OPT-IN so the default dev-phase gauge (R-11) stays fast: a plain
# pytest run keeps all 16 P-tests at 25 examples (~3s wall). This adds work
# only when requested; no example count is reduced to pass (R-14).
MAXEX_500 = settings(max_examples=500, deadline=None)  # contract tier
# Single-command trigger for the 500-example gate tier:
#   DSM_HYPOTHESIS_EXAMPLES=500 /home/szf/venvs/dsm/bin/python -m pytest tests/test_properties_all.py
# Unset -> dev gauge (25); set to 500 -> the 16 @MAXEX tests run at MAXEX_500.
_MAXEX_N = int(os.environ.get("DSM_HYPOTHESIS_EXAMPLES", "25"))
MAXEX = MAXEX_500 if _MAXEX_N == 500 else settings(max_examples=_MAXEX_N, deadline=None)

DAY1 = dt.date(2026, 1, 1)
DAY2 = dt.date(2026, 12, 31)
PERIOD = '2026-09'
VER = 'v1'
WV = 'WV-SYN-E4'
KW = ('显著', 'p<0.05', '置信区间')  # [L979] external keyword list (fixture)
LEVEL_RANK = {'L1': 0, 'L2': 1, 'L3': 2, 'L4': 3, 'NOT_ASSESSED': 4}


def unit(parts):
    '''Integer shares -> Decimal weights summing to exactly 1 (last key takes
    the residual). Construction helper, no business number.'''
    keys = sorted(parts)
    total = sum((D(parts[k]) for k in keys), ZERO)
    out = {}
    acc = ZERO
    for key in keys[:-1]:
        out[key] = q12(D(parts[key]) / total)
        acc = acc + out[key]
    out[keys[-1]] = q12(ONE - acc)
    return {k: str(v) for k, v in out.items()}


def frozen_doc(level1, level2, wv=WV):
    return WeightVersionDoc(
        weight_version_id=wv, status='FROZEN',
        effective_from=DAY1, effective_to=DAY2,
        level1_weights=dict(level1), level2_weights=dict(level2),
        approved_by='SYN-OWNER', approved_date=DAY1)


def abs_frame(sid, values, period=PERIOD):
    rows = tuple(
        AttainmentRow(strategy_id=sid, version_id=VER, period=period,
                      metric_id=m, attainment=D(values[m]), direction=1,
                      has_target=True, capped_flag=False)
        for m in sorted(values))
    return AttainmentFrame(rows=rows, attainment_coverage={sid: ONE})


def rel_frame(sid, values, period=PERIOD):
    rows = tuple(
        NormalizedRow(strategy_id=sid, version_id=VER, period=period,
                      metric_id=m, norm_value=D(values[m]), method='min_max',
                      pool_key=PoolKey(biz_domain='pay', evidence_class='A'),
                      anchor_used=False)
        for m in sorted(values))
    return NormalizedFrame(rows=rows)


EV_REASON = {'A': RC.EV_A_RANDOMIZED, 'B': RC.EV_B_QUASI,
             'C': RC.EV_C_OBSERVATIONAL, 'D': RC.EVIDENCE_CARD_MISSING}


def ev_row(sid, cls, period=PERIOD):
    return EvidenceRow(
        strategy_id=sid, version_id=VER, evidence_class=cls,
        evidence_reason=EV_REASON[cls], evidence_source='CARD_ONLY',
        interpretation_limit='SYN 外推限制' if cls in ('C', 'D') else None)


def ruleset(min_cov='0.6', ceiling='L3', floors=None):
    floors = floors or {'L1': '0.9', 'L2': '0.75', 'L3': '0.6', 'L4': '0.4'}
    rows = tuple(
        GradeRuleRow(grade_code=g, grade_label='SYN-' + g,
                     attainment_floor=floors[g], evidence_class_min='A',
                     redline_pass_required=(g != 'L4'), promotion_streak=1,
                     actions=('SYN-ACTION',), max_grade_if_no_target=ceiling)
        for g in ('L1', 'L2', 'L3', 'L4'))
    return grading.GradeRuleSet(
        rows=rows, min_coverage_for_absolute_track=min_cov,
        upgrade_consecutive_periods=2, demotion_immediate=True)


def score_row(sid, absolute, relative='0.5', dim=None, period=PERIOD, wv=WV):
    return ScoreRow(
        strategy_id=sid, version_id=VER, period=period,
        composite_absolute=absolute, composite_relative=relative,
        dim_absolute=dict(dim or {'D1': absolute}),
        dim_relative={'D1': relative}, coverage=ONE,
        weight_version_id=wv, operator='LINEAR')


def grade_row(sid, grade, period=PERIOD):
    return GradeRow(strategy_id=sid, version_id=VER, period=period,
                    grade=grade, grade_reason_path=(), capped=False,
                    cap_reason=None, action=None, usable_for_elimination=True)


def master_row(sid, domain='CARD'):
    return StrategyMasterRow(
        strategy_id=sid, version_id=VER, strategy_name='SYN-' + sid,
        biz_domain=domain, scene_code='SYN-SCENE', segment_type='EXISTING',
        online_date=DAY1, owner_dept='SYN-DEPT', owner_name='SYN-OWNER',
        status='ACTIVE')


def md_row(metric, dim, formula='RATIO_DIRECT', target='1', direction=1):
    return MetricDictRow(
        metric_id=metric, metric_name=metric, dim_code=dim,
        numerator_def='SYN-num', time_window='MONTHLY', dedup_rule='NONE',
        missing_rule='SKIP', outlier_rule='CLIP_P1_P99',
        attainment_formula=formula, direction=direction, unit='RATIO',
        target_value=D(target), target_basis='SYN-budget', is_redline=False,
        owner_name='SYN-OWNER', signoff_status='SIGNED',
        dim_signoff_status='SIGNED', dict_version='MD-SYN',
        caliber_version='CAL-SYN')


def fact_row(sid, metric, value, period=PERIOD):
    return MetricFactRow(
        strategy_id=sid, version_id=VER, period=period, metric_id=metric,
        value_num=D(value), value=D(value), data_quality_flag='OK',
        snapshot_time=dt.datetime(2026, 10, 1, 8, 0),
        data_as_of=DAY2, source_table='SYN-t_fact', caliber_version='CAL-SYN')


def clean_sens(n):
    return SensitivityReport(
        by_scheme=(SensitivitySchemeResult(
            scheme='OAT_10', overall_flip_rate=D('0.02'), flipped_count=0,
            assessed_count=n, flag=None),),
        by_strategy=())


def matrix(weights):
    '''Perfectly consistent pairwise matrix a_ij = w_i / w_j (CR = 0).'''
    keys = sorted(weights)
    w = {k: D(weights[k]) for k in keys}
    return {i: {j: str((w[i] / w[j]).quantize(Decimal('1E-20')))
                for j in keys} for i in keys}


def hierarchy(dim_weights, metric_weights):
    return weights_ahp.elicit_hierarchy(
        {'E1': matrix(dim_weights)},
        {d: {'E1': matrix(metric_weights[d])} for d in sorted(metric_weights)})


def ahp_snapshot(dim_weights, metric_weights):
    '''ORCH-29 ruling 1 ([L278] / [L286]): what crosses into weights_combine
    is the L0a ARTIFACT (AhpHierarchySnapshot), not the AhpHierarchy object
    -- the injection is the CALLER (cli / tests) job, the same construction
    the combine lane uses in tests/test_methods_combine.py::snapshot.'''
    result = hierarchy(dim_weights, metric_weights)
    return wc.AhpHierarchySnapshot(
        dimension=wc.AhpLevelSnapshot.from_payload(result.dimension.segment_payload(),
                                                   result.dimension.findings),
        metrics_by_dim={dim: wc.AhpLevelSnapshot.from_payload(
                            level.segment_payload(), level.findings)
                        for dim, level in sorted(result.metrics_by_dim.items())})

def metric_rows(spec):
    return [{'metric_id': m, 'dim_code': spec[m], 'direction': 1,
             'is_redline': False} for m in sorted(spec)]


def facts_history(columns, strategies, periods=('P1', 'P2')):
    out = {}
    for period in periods:
        out[period] = {}
        for metric_id in sorted(columns):
            out[period][metric_id] = {
                s: columns[metric_id][i]
                for i, s in enumerate(strategies[:len(columns[metric_id])])}
    return out


def window(columns, spec, strategies, options):
    try:
        return wc.calibrate_entropy_window(
            facts_history(columns, strategies), metric_rows(spec), options,
            D('0.000001'))
    except wc.EntropyInsufficientSample:
        return None

# ---------------------------------------------------------------------------
# P-1 [L1425] monotonicity
# ---------------------------------------------------------------------------
@st.composite
def _mono_case(draw):
    dim_w = unit({'D1': draw(st.integers(1, 9)), 'D2': draw(st.integers(1, 9))})
    met_w = {'D1': unit({'M1': draw(st.integers(1, 9)),
                         'M2': draw(st.integers(1, 9))}),
             'D2': unit({'M3': draw(st.integers(1, 9)),
                         'M4': draw(st.integers(1, 9))})}
    base = {m: Decimal(draw(st.integers(0, 150))) / Decimal(100)
            for m in ('M1', 'M2', 'M3', 'M4')}
    bump_metric = draw(st.sampled_from(('M1', 'M2', 'M3', 'M4')))
    bump = Decimal(draw(st.integers(1, 50))) / Decimal(100)
    return dim_w, met_w, base, bump_metric, bump


def _linear_reference(level1, level2, values):
    '''Hand-derived LINEAR composite of [L464]-[L466]: composite = sum W_d *
    sum w_j * a_j. Derived from the SDD formula and the inputs only (R-14).'''
    acc = ZERO
    for dim in sorted(level1):
        dimv = ZERO
        for m in sorted(level2[dim]):
            dimv = dimv + D(level2[dim][m]) * D(values[m])
        acc = acc + D(level1[dim]) * dimv
    return q12(acc)


@MAXEX
@given(_mono_case())
def test_p01_positive_metric_bump_never_lowers_composite_absolute(case):
    '''P-1 [L1425]: "任一正向指标值提升(其余不变)→ composite_absolute 不下降".
    Why it must hold: the absolute track aggregates positive-direction
    attainment; if improving one metric could lower the composite, every
    "improvement is rewarded" claim built on the score dies. Global layer:
    normalize rows + FROZEN weight doc + aggregate.compose together.
    Expectation: order relation on Decimals plus the hand-derived LINEAR
    reference at 1e-12 (V-9), never a captured implementation value.'''
    dim_w, met_w, base, metric, bump = case
    moved = dict(base)
    moved[metric] = base[metric] + bump
    doc = frozen_doc(dim_w, met_w)
    rel = {m: '0.5' for m in base}
    c0 = aggregate.compose(abs_frame('S1', base), rel_frame('S1', rel),
                           doc).rows[0].composite_absolute
    c1 = aggregate.compose(abs_frame('S1', moved), rel_frame('S1', rel),
                           doc).rows[0].composite_absolute
    assert c1 >= c0
    assert eq_tol(c0, _linear_reference(dim_w, met_w, base), TOL)


def _hand_base_grade(comp, floors=None):
    floors = floors or {'L1': '0.9', 'L2': '0.75', 'L3': '0.6'}
    for g in ('L1', 'L2', 'L3'):
        if D(comp) >= D(floors[g]):
            return g
    return 'L4'


# ---------------------------------------------------------------------------
# P-2 [L1426] non-compensability (global: through the grading layer)
# ---------------------------------------------------------------------------
@MAXEX
@given(forced=st.sampled_from(('L1', 'L2', 'L3', 'L4')),
       comp=st.sampled_from(('0.95', '0.91', '0.80', '0.62')))
def test_p02_hard_redline_grade_equals_forced_no_matter_how_good(comp, forced):
    '''P-2 [L1426]: "任一 HARD 红线违反 → grade 恒等于 forced_grade, 与其余指标
    多好无关". Why: redlines are governance vetoes; a compensable veto is no
    veto at all. Module-local version:
    tests/test_redline.py::test_p2_property_hard_crossing_always_forces_declared_grade
    stops at the redline frame; the E4 version drives grading.assign, so the
    grade itself (through cap/streak steps) must still equal forced.
    Expectation: hand-set: composite above the L1 floor means the base grade
    would be L1; the declared forced_grade is an INPUT of the redline row, so
    grade == forced is derived from [L962] step 4, not from output.'''
    scores = ScoreFrame(rows=(score_row('SV', D(comp)),
                              score_row('SN', D(comp))))
    att = AttainmentFrame(rows=(), attainment_coverage={'SV': ONE, 'SN': ONE})
    ev = EvidenceFrame(rows=(ev_row('SV', 'A'), ev_row('SN', 'A')))
    rl = RedlineFrame(rows=(RedlineEvalRow(
        strategy_id='SV', version_id=VER, period=PERIOD, metric_id='MR',
        level='HARD', comparator='LTE', threshold_value=D('0.05'),
        hit=True, forced_grade=forced, soft_deduction=None),))
    frame = grading.assign(scores, att, ev, rl, None, ruleset(
        floors={'L1': '0.9', 'L2': '0.75', 'L3': '0.6', 'L4': '0.4'}))
    got = {r.strategy_id: r for r in frame.rows}
    assert got['SV'].grade == forced
    # the clean twin keeps exactly the hand-implied base grade: the
    # forcing is about the violator, not a blanket clamp.
    assert got['SN'].grade == _hand_base_grade(comp)
    path = tuple(getattr(c, 'value', c) for c in
                 got['SV'].grade_reason_path)
    assert RC.GR_REDLINE_FORCED.value in path


# ---------------------------------------------------------------------------
# P-3 [L1427] idempotence -> reproducibility_hash
# ---------------------------------------------------------------------------
@MAXEX
@given(k=st.integers(0, 40),
       dims=st.integers(2, 3))
def test_p03_same_input_same_config_twice_same_reproducibility_hash(k, dims):
    '''P-3 [L1427]: "同输入同配置运行两次 → reproducibility_hash 相等".
    Why: the audit chain promises any reviewer byte-identical results; if two
    runs of one input disagree, the hash proves nothing. Global: runs the WHOLE
    landed chain (attainment -> normalize -> aggregate -> grading) twice and
    hashes the resulting score_card / grade_ledger via dsm.audit -- the module
   -local tests (test_audit G-12) hash hand-built rows instead.
    Expectation: equality of the two independently produced hashes; the hash
    itself is a sha256 (64 hex chars), checked, not captured.'''
    dim_w = unit({'D1': str(3 + k % 5), 'D2': str(2 + k % 3)})
    met_w = {'D1': unit({'M1': '1', 'M2': str(2 + k % 4)}),
             'D2': unit({'M3': '1',
                         **({'M4': str(1 + k % 6)} if dims == 3 else {})})}
    metrics = sorted(m for mm in met_w.values() for m in mm)
    values = {sid: {m: D((si * 31 + mi * 7 + k) % 100 + 1) / D(100)
                    for mi, m in enumerate(metrics)}
              for si, sid in enumerate(('S1', 'S2', 'S3'))}

    def one_run():
        md = [md_row(m, dim) for dim, mm in sorted(met_w.items()) for m in mm]
        facts = [fact_row(sid, m, values[sid][m])
                 for sid in sorted(values) for m in sorted(values[sid])]
        att = attainment.compute(
            facts, md, params=AttainmentParams(attainment_cap=D('3'),
                                               on_zero=None,
                                               signed_off_statuses=('SIGNED',)))
        pools = {sid: PoolKey(biz_domain='pay', evidence_class='A')
                 for sid in values}
        nrm = normalize.compute(
            att, md,
            AnchorSetDoc(anchor_set_id='AS-SYN', strategy_ids=('S1', 'S2', 'S3'),
                         effective_from=DAY1, effective_to=DAY2,
                         rationale='SYN'),
            params=NormalizeParams(method='min_max', min_pool_size=2,
                                   on_zero=None, sd_dof=1),
            pools=pools)
        scores = aggregate.compose(att, nrm, frozen_doc(dim_w, met_w))
        grades = grading.assign(
            scores, att,
            EvidenceFrame(rows=tuple(ev_row(s, 'A') for s in sorted(values))),
            RedlineFrame(rows=()), None, ruleset())
        cards = tuple(_card_from(r, grades) for r in
                      sorted(scores.rows, key=lambda x: x.strategy_id))
        ledger = tuple(_ledger_from(r) for r in
                       sorted(grades.rows, key=lambda x: x.strategy_id))
        return audit.reproducibility_hash(cards, ledger, WV)

    h1 = one_run()
    h2 = one_run()
    assert h1 == h2
    assert len(h1) == 64 and all(c in '0123456789abcdef' for c in h1)


def _card_from(score_row_, grades):
    g = {r.strategy_id: r for r in grades.rows}[score_row_.strategy_id]
    return ScoreCardRow(
        strategy_id=score_row_.strategy_id, version_id=VER, period=PERIOD,
        weight_version_id=WV, dict_version='MD-SYN', anchor_set_id='AS-SYN',
        run_id='RUN-SYN-1', per_metric={}, per_dim={},
        composite_absolute=score_row_.composite_absolute,
        composite_relative=score_row_.composite_relative,
        evidence_class='A', evidence_reason=RC.EV_A_RANDOMIZED.value,
        evidence_source='CARD_ONLY', interpretation_limit=None,
        redline_pass=True, redline_flags=(), grade=g.grade,
        grade_reason_codes=(), capped_flag=g.capped, cap_reason=None,
        ranking_pool=PoolKey(biz_domain='pay', evidence_class='A'),
        rank_in_pool=None, pool_size=None,
        eligible_for_L1_library=(g.grade in ('L1', 'L2')),
        l1_gate_reasons=(), stability_label=None, flip_under_pct10=None,
        flip_under_pct20=None, usable_for_elimination=True,
        value_captured_minor=None)


def _ledger_from(g):
    return GradeLedgerRow(strategy_id=g.strategy_id, version_id=VER,
                          period=PERIOD, grade=g.grade,
                          ledger_complete=True, usable_for_elimination=True)


# ---------------------------------------------------------------------------
# P-4 [L1428] anchor invariance (global: norm AND grade through the chain)
# ---------------------------------------------------------------------------
@MAXEX
@given(k=st.integers(0, 30), newv=st.integers(1, 400))
def test_p04_adding_non_anchor_strategy_keeps_existing_norm_and_grade(k, newv):
    '''P-4 [L1428]: "向当期集合新增一个不在锚定集的策略 → 存量策略的 norm 与
    grade 不变". Why: the anchor set freezes the scale; newcomers must never
    re-shade last quarter''s standings (retroactive ranking changes are
    indefensible). Module-local version:
    tests/test_normalize.py::test_p4_adding_non_anchor_strategies_keeps_existing_norms
    stops at norm_value; the E4 version re-runs aggregate AND grading and also
    locks the grade column. Expectation: per-sid equality between run A and
    run B (pairwise on two chain executions, values never hand-pinned).'''
    dim_w = {'D1': '1'}
    met_w = {'D1': {'M1': '1'}}
    base_vals = {sid: D(20 + si * 30 + k) / D(100)
                 for si, sid in enumerate(('S1', 'S2', 'S3'))}
    base_vals['S9'] = D(newv) / D(100)

    def run(values):
        md = [md_row('M1', 'D1')]
        facts = [fact_row(sid, 'M1', v) for sid, v in sorted(values.items())]
        att = attainment.compute(
            facts, md, params=AttainmentParams(attainment_cap=D('5'),
                                               on_zero=None,
                                               signed_off_statuses=('SIGNED',)))
        pools = {sid: PoolKey(biz_domain='pay', evidence_class='A')
                 for sid in values}
        nrm = normalize.compute(
            att, md,
            AnchorSetDoc(anchor_set_id='AS-SYN', strategy_ids=('S1', 'S2', 'S3'),
                         effective_from=DAY1, effective_to=DAY2,
                         rationale='SYN'),
            params=NormalizeParams(method='min_max', min_pool_size=2,
                                   on_zero=None, sd_dof=1),
            pools=pools)
        scores = aggregate.compose(att, nrm, frozen_doc(dim_w, met_w))
        grades = grading.assign(
            scores, att,
            EvidenceFrame(rows=tuple(ev_row(s, 'A') for s in sorted(values))),
            RedlineFrame(rows=()), None, ruleset())
        return ({r.strategy_id: r.norm_value for r in nrm.rows},
                {r.strategy_id: r.grade for r in grades.rows})

    without = run({s: v for s, v in base_vals.items() if s != 'S9'})
    withn = run(base_vals)
    for sid in ('S1', 'S2', 'S3'):
        assert withn[0][sid] == without[0][sid]      # norm untouched
        assert withn[1][sid] == without[1][sid]      # grade untouched


# ---------------------------------------------------------------------------
# P-5 [L1429] perturbation schemes keep sum W_d = 1
# ---------------------------------------------------------------------------
@MAXEX
@given(parts=st.lists(st.integers(1, 9), min_size=2, max_size=4),
       pct=st.sampled_from(('0.1', '0.2')), sign=st.sampled_from((1, -1)))
def test_p05_every_perturbation_scheme_stays_on_the_weight_simplex(parts, pct,
                                                                   sign):
    '''P-5 [L1429]: "任何扰动方案下 Σ W_d = 1(1e-12 容差)". Why: flip_rate
    measures grade churn; if a perturbed scheme drifted off the simplex the
    churn would be a scale artefact, poisoning G-05/D2. Global layer:
    dsm.sensitivity public perturbators (OAT level-1, LOO metric drop) feeding
    the same renormalisation the schemes run on. Tolerance is numeric.TOL
    (1e-12), derived from the [L954] renormalise spec (last key residual).'''
    keys = ['D%d' % i for i in range(len(parts))]
    level1 = unit(dict(zip(keys, (str(p) for p in parts))))
    before = dict(level1)
    dim = keys[len(keys) // 2]
    out = sensitivity.perturb_level1(level1, dim, D(pct), sign)
    assert eq_tol(sum((D(out[k]) for k in sorted(out)), ZERO), ONE, TOL)
    assert all(D(v) >= ZERO for v in out.values())
    assert level1 == before                        # input never mutated
    l1w = unit({'D1': str(parts[0]), 'D2': str(parts[-1])})
    doc = frozen_doc(l1w, {'D1': unit({'M1': '3', 'M2': '4'}),
                           'D2': unit({'M3': '1', 'M4': '2'})})
    l1_before = {k: D(v) for k, v in doc.level1_weights.items()}
    l2_before = {d: {m: D(v) for m, v in w.items()}
                 for d, w in doc.level2_weights.items()}
    dropped = sensitivity.drop_metric(doc, 'M3')
    assert eq_tol(sum((D(dropped.level1_weights[d])
                       for d in sorted(dropped.level1_weights)), ZERO),
                  ONE, TOL)
    for d in sorted(dropped.level2_weights):
        assert eq_tol(sum((D(dropped.level2_weights[d][m])
                           for m in sorted(dropped.level2_weights[d])),
                      ZERO), ONE, TOL)
    assert {k: D(v) for k, v in doc.level1_weights.items()} == l1_before
    assert {d: {m: D(v) for m, v in w.items()}
            for d, w in doc.level2_weights.items()} == l2_before  # untouched


# ---------------------------------------------------------------------------
# P-6 [L1430] evidence gate monotonicity (global: classify -> pooling)
# ---------------------------------------------------------------------------
def _card(sid, cls):
    if cls == 'A':
        method, control, note, crit = 'AB_TEST', 'RANDOMIZED', None, \
            '显著(p<0.05)提升动卡率'
    elif cls == 'B':
        method, control, note, crit = 'DID', 'NONE', 'SYN 平行趋势假设', \
            '提升动卡率'
    else:
        method, control, note, crit = 'OBSERVATIONAL_ONLY', 'NONE', None, \
            '提升动卡率'
    return DesignCardRow(
        strategy_id=sid, version_id=VER, direct_goal='SYN-goal',
        process_metrics=('M1',), result_metrics=('M2',),
        observation_window=PERIOD, data_source='SYN-dws',
        data_timeliness='T+1', eval_method=method, control_arrangement=control,
        success_criteria=crit, risk_constraints='SYN', eval_owner='SYN',
        alt_method_note=note, interpretation_limit='SYN 外推限制',
        card_status='COMPLETE')


@MAXEX
@given(cls=st.sampled_from(('A', 'B')), which=st.sampled_from((0, 1, 2)))
def test_p06_downgrading_evidence_to_C_never_relaxes_the_L1_library_gate(
        cls, which):
    '''P-6 [L1430]: "evidence_class 由 A/B 降为 C 时, eligible_for_L1_library
    只可能由 true 变 false, 绝不反向放宽". Why: the library gate is an
    evidence promise; letting a weaker class pass where the stronger one
    failed turns the gate into an obstacle to route around. Module-local
    versions: tests/test_pooling.py P-6 cases (pool keys/ranks, hand frames).
    The E4 global version really runs evidence.classify then pooling.build.
    Expectation: monotone direction on the eligibility pair only (true->false
    allowed, false->true forbidden) -- derived from the gate semantics, and
    the C rows are asserted to actually be C so the check is not vacuous.'''
    sids = ('S1', 'S2', 'S3')
    cards_before = [_card(s, cls if i == which else 'C')
                    for i, s in enumerate(sids)]
    cards_after = [_card(s, 'OBSERVATIONAL_ONLY' and 'C') for s in sids]
    prm = EvidenceParams(evidence_mode='GATE_ONLY', cel_enabled=False,
                         significance_keywords=KW)
    ev_before = evidence.classify(tuple(cards_before), (), params=prm)
    ev_after = evidence.classify(tuple(cards_after), (), params=prm)
    cls_before = {r.strategy_id: r.evidence_class for r in ev_before.rows}
    assert cls_before[sids[which]] == cls          # upgrade really in place
    assert all(r.evidence_class == 'C' for r in ev_after.rows)

    def library(ev):
        scores = ScoreFrame(rows=tuple(
            score_row(s, D('0.95'), relative=D(90 - 10 * i) / D(100))
            for i, s in enumerate(sids)))
        grades = GradeFrame(rows=tuple(grade_row(s, 'L1') for s in sids))
        master = tuple(master_row(s) for s in sids)
        frame, _stats = pooling.build(scores, grades, ev, master, None,
                                      sensitivity=clean_sens(len(sids)),
                                      params=PoolingParams(min_pool_size=1))
        return {r.strategy_id: r.primary_pool_eligible for r in frame.rows}

    before = library(ev_before)
    after = library(ev_after)
    for sid in sids:
        assert not (after[sid] and not before[sid]), \
            'gate relaxed after downgrade: ' + sid


# ---------------------------------------------------------------------------
# P-7 [L1431] money stays exact ints / equals the Decimal reference
# ---------------------------------------------------------------------------
@MAXEX
@given(minors=st.lists(st.integers(min_value=0, max_value=10 ** 12),
                       min_size=1, max_size=6),
       weights=st.lists(st.integers(min_value=1, max_value=9),
                        min_size=6, max_size=6))
def test_p07_money_minor_int_pipeline_equals_decimal_reference_exactly(
        minors, weights):
    '''P-7 [L1431]: "MONEY_MINOR 字段全程整数运算, 结果与 Decimal 参考实现精确
    相等". Why: a bank reconciliation that drifts by a cent is worthless; ints
    are exact, binary floats never are. Global: exercises numeric aggregate
    paths (round-trip of an int SUM, weighted_sum over from_minor values,
    safe_div ratio), beyond the single-value round trip in
    tests/test_numeric_properties.py::test_minor_unit_round_trip_is_lossless.
    Expectation: hand-derived int sums and exact Decimal products (V-9: money
    eq_exact; only the division case carries the 1e-12 tolerance).'''
    w = weights[:len(minors)]
    total = sum(minors)                            # hand: pure int arithmetic
    assert isinstance(total, int)
    assert isinstance(to_minor(from_minor(total)), int)
    assert to_minor(from_minor(total)) == total    # aggregate round trip lossless
    ref = sum((Decimal(k) * from_minor(m) for k, m in zip(w, minors)), ZERO)
    got = numeric.weighted_sum(
        [(Decimal(k), from_minor(m)) for k, m in zip(w, minors)])
    assert eq_exact(got, q12(ref))                 # exact, no tolerance here
    ratio = numeric.safe_div(total, len(minors), on_zero=None)
    exact_ref = D(total) / D(len(minors))          # Decimal reference quotient
    assert eq_tol(ratio, exact_ref, TOL)           # ratio track: 1e-12 gauge


# ---------------------------------------------------------------------------
# P-8 [L1432] attainment cap always effective
# ---------------------------------------------------------------------------
@MAXEX
@given(formula=st.sampled_from(('RATIO_DIRECT', 'INVERSE_RATIO')),
       actuals=st.lists(st.integers(1, 1000), min_size=3, max_size=3),
       target=st.integers(1, 500), capk=st.integers(1, 25))
def test_p08_attainment_never_exceeds_the_cap(formula, actuals, target, capk):
    '''P-8 [L1432]: "任一指标 attainment ≤ attainment_cap". Why: the cap is the
    A-3 governance clip that keeps one runaway metric from buying the whole
    composite; an uncapped row means the governance block was bypassed.
    Expectation: cap comes from the INPUT AttainmentParams (SYN fixture
    value), compared with exact Decimal <=, never with a recorded output.
    INTERVAL is not covered here -- its bounds structure awaits signed config
    (GAPS: registered on the report line), no defaults are invented (V-14).'''
    cap = Decimal(capk) / Decimal(10)
    direction = 1 if formula == 'RATIO_DIRECT' else -1
    md = [md_row('M1', 'D1', formula=formula, target=str(Decimal(target) /
                                                         Decimal(100)),
                 direction=direction)]
    facts = [fact_row('S%d' % (i + 1), 'M1', D(a) / D(100))
             for i, a in enumerate(actuals)]
    frame = attainment.compute(
        facts, md, params=AttainmentParams(attainment_cap=cap, on_zero=None,
                                           signed_off_statuses=('SIGNED',)))
    assert frame.rows
    for row in frame.rows:
        if row.attainment is not None:
            assert row.attainment <= cap
            if row.capped_flag:
                assert eq_exact(row.attainment, q12(cap))

# ---------------------------------------------------------------------------
# P-9 [L1433] honest downgrade when the absolute track is thin
# ---------------------------------------------------------------------------
@MAXEX
@given(ceiling=st.sampled_from(('L2', 'L3', 'L4')),
       compk=st.integers(91, 120), covk=st.integers(5, 59))
def test_p09_low_coverage_grade_never_beats_max_grade_if_no_target(
        compk, ceiling, covk):
    '''P-9 [L1433]: "绝对轨覆盖率不足时, grade 必不优于 max_grade_if_no_target".
    Why: a grade built on a mostly-missing target column would pretend to know
    more than the data does; the ceiling is the disclosed honesty brake.
    Expectation: ceiling is an INPUT of the grade rule table (SYN fixture),
    the ordering L1<L2<L3<L4 is [L962] semantics -- the compared pair is
    (hand rule value, grade), never (rule, captured grade).'''
    comp = Decimal(compk) / Decimal(100)
    cov = Decimal(covk) / Decimal(100)
    scores = ScoreFrame(rows=(score_row('S1', comp), score_row('S2', comp)))
    att = AttainmentFrame(rows=(), attainment_coverage={'S1': cov, 'S2': ONE})
    ev = EvidenceFrame(rows=(ev_row('S1', 'A'), ev_row('S2', 'A')))
    frame = grading.assign(scores, att, ev, RedlineFrame(rows=()), None,
                           ruleset(min_cov='0.6', ceiling=ceiling))
    got = {r.strategy_id: r for r in frame.rows}
    thin = got['S1'].grade
    if thin != 'NOT_ASSESSED':
        assert LEVEL_RANK[thin] >= LEVEL_RANK[ceiling]
    # the full-coverage twin shows the cap actually bites: hand-implied base
    # grade for comp >= 0.9 with floors (0.9/0.75/0.6/0.4) is L1.
    assert got['S2'].grade == 'L1'
    assert LEVEL_RANK[got['S2'].grade] < LEVEL_RANK[ceiling]


# ---------------------------------------------------------------------------
# P-10 [L1434] no silent default -- global across ALL SIX config files
# ---------------------------------------------------------------------------
@MAXEX
@given(token=st.sampled_from(('PLACEHOLDER', 'TODO', 'TBD', 'XXX',
                              'PLACEHOLDER_K16', None)),
       shape=st.integers(0, 1))
def test_p10_placeholder_in_any_config_file_blocks_load(token, shape):
    '''P-10 [L1434]: "任一 PLACEHOLDER 未替换 → 配置加载阶段即抛错, 不进入计算".
    Why: a defaulted governance threshold is an unsigned business number
    wearing a computed score's clothes (H-5 / V-14). Module-local version:
    tests/test_config_properties.py::test_t05_j_p03... walks ONE synthetic
    stem (eval_config); the E4 global version writes ALL SIX on-disk files
    (eval_config, weights_*, redlines, grade_rules, anchor_set, ahp_matrices)
    and demands one hit per file to appear in the single raise.
    Expectation: exception type + exit code 3 (ruling 4 constant, not a
    business number) + per-stem coverage of err.paths.'''
    stems = ('eval_config', 'weights_WVS1', 'redlines', 'grade_rules',
             'anchor_set', 'ahp_matrices')

    def tree(i):
        hit = {'SYN-hit': token}          # ruling 6: None always counts
        if (i + shape) % 2 == 0:
            return {'SYN-note': 'SYN-filled', 'SYN-deep': hit}
        return {'SYN-note': 'SYN-filled', 'SYN-list': [hit]}

    with tempfile.TemporaryDirectory() as raw:
        base = __import__('pathlib').Path(raw)
        for i, stem in enumerate(stems):
            (base / (stem + '.yaml')).write_text(
                yaml.safe_dump(tree(i), allow_unicode=True,
                               sort_keys=False), encoding='utf-8')
        with pytest.raises(config.ConfigPlaceholderError) as excinfo:
            config.load_all(str(base))
        err = excinfo.value
        assert err.exit_code == 3
        for stem in stems:
            assert any(p.startswith(stem + '.') for p in err.paths), stem
        # V-14: a blocked load returns nothing -- no AppConfig escapes.
        assert not hasattr(err, 'config')


# ---------------------------------------------------------------------------
# P-11 [L1435] FROZEN provenance completeness (config layer, live)
# ---------------------------------------------------------------------------
def _frozen_wv_tree(kind):
    return {
        'weight_version_id': 'WVS1', 'status': 'FROZEN',
        'effective_from': '2026-01-01', 'effective_to': '2026-12-31',
        'level1_weights': {'D1': '0.6', 'D2': '0.4'},
        'level2_weights': {'D1': {'M1': '0.5', 'M2': '0.5'},
                           'D2': {'M3': '1'}},
        'approved_by': 'SYN-OWNER', 'approved_date': '2026-01-05',
        'provenance': {
            'kind': kind,
            'ahp': {'comparison_matrices': {'E1': 'SYN-matrix'}, 'cr': '0.0123'},
            'entropy': {'window_id': 'SYN-W1'},
            'combine': {'alpha': '0.6'},
            'alpha_basis': {'alpha_star': '0.6'},
            'whatif_run_id': 'WI-SYN-0001',
            'approved_by': 'SYN-OWNER', 'approved_date': '2026-01-05'}}


def _drop_dotted(holder, dotted):
    parts = dotted.split('.')
    node = holder
    for p in parts[:-1]:
        node = node[p]
    node.pop(parts[-1])


@MAXEX
@given(kind=st.sampled_from(('AHP_ONLY', 'AHP_ENTROPY_COMBINED')),
       victim=st.data())
def test_p11_frozen_weight_version_without_full_provenance_fails_the_load(
        kind, victim):
    '''P-11 [L1435]: "任何 FROZEN 权重版本必须具备完整 provenance(AHP 矩阵 + CR;
    若 combined 则含 α + alpha_basis + whatif_run_id), 缺任一项 → 配置加载失败".
    Why: provenance is the only answer to "why does this contribution weigh
    X"; a FROZEN version without it is an unsigned business decision stamped
    as data. Lives at the config layer today (validate_weights 序5/6/7 =
    [L1435] policy, per the WeightProvenance docstring in models.py), so it
    does NOT wait for A3/A4 module bodies. Expectation: the required-segment
    matrix is taken VERBATIM from [L1435]; both the positive control (a full
    FROZEN version loads) and the drop-one negative are asserted.'''
    required = ['ahp', 'ahp.comparison_matrices', 'ahp.cr', 'whatif_run_id',
                'approved_by']
    if kind == 'AHP_ENTROPY_COMBINED':
        required += ['entropy', 'combine', 'combine.alpha', 'alpha_basis']
    path = victim.draw(st.sampled_from(tuple(required)))
    cfg_ok = config.AppConfig(
        eval_config={}, weights={'weights_WVS1': _frozen_wv_tree(kind)},
        redlines={}, grade_rules={}, anchor_set={}, ahp_matrices={})
    config.validate_weights(cfg_ok, period='2026-06-15')   # positive control
    broken = _frozen_wv_tree(kind)
    _drop_dotted(broken['provenance'], path)
    cfg_bad = config.AppConfig(
        eval_config={}, weights={'weights_WVS1': broken},
        redlines={}, grade_rules={}, anchor_set={}, ahp_matrices={})
    with pytest.raises(config.WeightVersionInvalidError) as excinfo:
        config.validate_weights(cfg_bad, period='2026-06-15')
    assert path.split('.')[-1] in str(excinfo.value)


# ---------------------------------------------------------------------------
# P-12 [L1436] alpha never moves a governance gate (combine drives it live)
# ---------------------------------------------------------------------------
DIMS12 = {'D1': '0.6', 'D2': '0.4'}
MW12 = {'D1': {'M1': '0.4', 'M2': '0.6'}, 'D2': {'M3': '1'}}
SPEC12 = {'M1': 'D1', 'M2': 'D1', 'M3': 'D2'}
COLS12 = {'M1': ['10', '25', '37'], 'M2': ['5', '80', '12'],
          'M3': ['7', '9', '31']}
SIDS12 = ('S-1', 'S-2', 'S-3')


@st.composite
def _alpha_triple(draw):
    fk = draw(st.integers(10, 80))
    a1k = draw(st.integers(fk, 95))
    a2k = draw(st.integers(a1k + 1, 100))
    return (Decimal(fk) / 100, Decimal(a1k) / 100, Decimal(a2k) / 100)


def _governance_at(alpha, floor, snapshot):
    opts = wc.CombineOptions(alpha=D(alpha), alpha_floor=D(floor),
                             min_dim_weight=ZERO, entropy_min_strategies=3,
                             max_shift_from_ahp=D('5'))
    combined = wc.combine(ahp_snapshot(DIMS12, MW12), snapshot, opts)
    assert all(combined.hard_checks.results[k] is True
               for k in sorted(combined.hard_checks.results))
    doc = frozen_doc({d: str(combined.dim_weights[d])
                      for d in sorted(combined.dim_weights)},
                     {d: {m: str(combined.metric_weights[d][m])
                          for m in sorted(combined.metric_weights[d])}
                      for d in sorted(combined.metric_weights)})
    vals = {m: D('1') for m in sorted(SPEC12)}
    att = abs_frame('__', vals)
    srows = tuple(score_row(s, D('1'), relative=D('0.5'),
                            dim={d: D('1') for d in ('D1', 'D2')})
                  for s in ('SV', 'SC', 'SD'))
    scores = ScoreFrame(rows=srows)
    att = AttainmentFrame(rows=(), attainment_coverage={s: ONE
                                                       for s in ('SV', 'SC',
                                                                  'SD')})
    ev = EvidenceFrame(rows=(ev_row('SV', 'A'), ev_row('SC', 'C'),
                             ev_row('SD', 'D')))
    rl = RedlineFrame(rows=(RedlineEvalRow(
        strategy_id='SV', version_id=VER, period=PERIOD, metric_id='MR',
        level='HARD', comparator='LTE', threshold_value=D('0.05'),
        hit=True, forced_grade='L4', soft_deduction=None),))
    grades = grading.assign(scores, att, ev, rl, None, ruleset())
    frame, _stats = pooling.build(scores, grades, ev,
                                  tuple(master_row(s) for s in
                                        ('SV', 'SC', 'SD')), None,
                                  sensitivity=clean_sens(3),
                                  params=PoolingParams(min_pool_size=1))
    gm = {r.strategy_id: r.grade for r in grades.rows}
    em = {r.strategy_id: r.primary_pool_eligible for r in frame.rows}
    return gm, em, doc


@MAXEX
@given(_alpha_triple())
def test_p12_alpha_changes_no_redline_or_evidence_gate(triple):
    '''P-12 [L1436]: "对任意 α ∈ [alpha_floor,1]: 红线违反恒为 forced_grade;
    C 类恒不得进一级库; D 类恒不出分(权重变化不得成为绕过门禁的通道)".
    Why: if a weight knob could re-open a closed gate, the governance layer
    would be negotiable through arithmetic -- the exact failure R4 forbids.
    Live through the landed weights_combine + grading + pooling chain (the
    calibrate-produced α* is A3's own guard, T-CAL-*). Expectation derived
    from the gate rules and the INPUT forced_grade: SV == 'L4' (declared),
    SC ineligible, SD NOT_ASSESSED -- at BOTH alphas, plus the two triples
    are pairwise identical (gate invariance across the whole drawn interval).'''
    floor, a1, a2 = triple
    snap = window(COLS12, SPEC12, SIDS12,
                  wc.CombineOptions(alpha=D(a1), alpha_floor=D(floor),
                                    min_dim_weight=ZERO,
                                    entropy_min_strategies=3,
                                    max_shift_from_ahp=D('5')))
    assert snap is not None, 'entropy window vanished on varying columns'
    g1, e1, _doc1 = _governance_at(a1, floor, snap)
    g2, e2, _doc2 = _governance_at(a2, floor, snap)
    assert g1 == g2 and e1 == e2
    assert g1['SV'] == 'L4' and g2['SV'] == 'L4'        # forced == declared
    assert g1['SD'] == 'NOT_ASSESSED'                   # D never scores
    assert e1['SC'] is False and e2['SC'] is False      # C never in the library
    assert g1['SC'] == 'L2'                             # hand: L1 capped by CEL

# ---------------------------------------------------------------------------
# P-13 [L1437] governance budgets untouchable by calibration/combination
# ---------------------------------------------------------------------------
HDR13 = wc.DraftHeader(weight_version_id='WV-T-E4', approved_by='SYN-OWNER',
                       approved_date=DAY1, effective_from=DAY1,
                       effective_to=DAY2)


@MAXEX
@given(ak=st.integers(30, 100))
def test_p13a_combine_run_never_mutates_governance_budgets(ak):
    '''P-13 [L1437] (combine half): "calibrate / combine 的运行不得修改
    alpha_floor、drift_budget、boundary_budget、boundary_epsilon、
    min_dim_weight、max_shift_from_ahp 的取值". Why: those six are the signed
    governance envelope (K-15~K-20); a run that relaxed them to fit a smaller
    α would be the algorithm grading its own homework. Expectation: deep
    equality of every INPUT dump taken before the run (frozen pydantic docs
    included) and provenance.combine.alpha == the passed alpha (no silent
    re-clamp). drift/boundary budgets live in eval_config (config side), so
    the positive control here is that combine never even receives them:
    it gets CombineOptions and returns a DRAFT doc.'''
    alpha = Decimal(ak) / Decimal(100)
    opts = wc.CombineOptions(alpha=alpha, alpha_floor=D('0.25'),
                             min_dim_weight=ZERO, entropy_min_strategies=3,
                             max_shift_from_ahp=D('0.30'))
    snap = window(COLS12, SPEC12, SIDS12, opts)
    ahp = ahp_snapshot(DIMS12, MW12)
    opts_before = opts.model_dump()
    ahp_before = ahp.model_dump()
    snap_before = snap.model_dump()
    hdr_before = HDR13.model_dump()
    combined = wc.combine(ahp, snap, opts)
    doc = wc.step6_draft(combined, HDR13)
    assert opts.model_dump() == opts_before
    assert ahp.model_dump() == ahp_before
    assert snap.model_dump() == snap_before
    assert HDR13.model_dump() == hdr_before
    assert D(doc.provenance.combine.alpha) == D(alpha)
    assert doc.status == 'DRAFT'          # sign-off stays a human act [L600]


# ---------------------------------------------------------------------------
# P-13 [L1437] governance budgets untouchable -- CALIBRATION half, EFIX-1 (E4b).
# The gated body written against the expected signature (inputs=None +
# window={'periods': [...]} + TypeError-only capture) is replaced with the
# REAL dsm.weights_calibrate contract (A3, 2de42db): a V-14 compliant
# implementation raises CalibrateError for inputs=None and WindowError for a
# mapping window -- never TypeError -- so the old shape could only be passed
# by breaking V-14 / R-12. Module-local versions: tests/test_methods_
# calibrate.py::test_p13_* and ::test_t_cal_04_p13_*; THIS is the cross-module
# global version (config.AppConfig + weights_calibrate + the real
# weights_combine entropy-snapshot path, ORCH-03).
#
# R-2 synthetic inputs, built here (fixtures/** frozen). Hand arithmetic,
# all test-owned SYN numbers -- the K-15~K-20 business values stay
# PLACEHOLDER in the signed config until sign-off (no number guessing):
#   AHP  W = (D1 0.6, D2 0.4); w(D1) = (M1 0.4, M2 0.4, M3 0.2); w(D2) = 1.
#   P1 (2026-01): M1 (2,6,9), M2 (9,2,6) are proportional permutations -> the
#     [L542] d_j are equal and [L544] normalises the pair entropy to
#     (1/2, 1/2); M3 (4,4,4), M4 (8,8,8) zero variation -> d = 0, and [L584]
#     keeps their AHP weights verbatim (INACTIVE fallbacks).
#   P2 (2026-02): M1 (6,2,9), M2 (2,9,6), M3 (9,6,2) are three permutations of
#     the SAME multiset -> entropy (1/3, 1/3, 1/3); M4 (5,5,5) fallback 1.
#   Both periods: D2 has no varying metric -> entropy dimension (1, 0), so
#     W_D1 = 1 - 0.4a, W_D2 = 0.4a in BOTH periods -> level-1 drift = 0; the
#     effective W_d*w_j layer ([L619] takes the larger of the two layers):
#       P1:  a=0.50 -> (0.32, 0.32, 0.16, 0.20);  a=0.75 -> (0.28, 0.28, 0.14, 0.30)
#       P2:  a=0.50 -> (22/75, 22/75, 16/75, 15/75); a=0.75 -> (16.1/60, 16.1/60, 9.8/60, 0.30)
#       a=1.00: pure AHP in both periods ([L632]) -> drift = 0 EXACTLY.
#     drift(0.50) = 8/75 = 0.10666... -> bracketed in (0.10, 0.11);
#     drift(0.75) = 7/150 = 0.04666... -> bracketed in (0.04, 0.05).
#     (Brackets, not equalities, because weights_combine chains q12 rounding;
#     the decision margins 0.0033..0.0067 are far larger than any 1e-12
#     accumulation, so the golden table below is rounding-proof.)
#   With drift_budget = k/100 the ONLY binding constraint:
#     k >= 11 -> alpha* = 0.50 | 5 <= k <= 10 -> alpha* = 0.75 | k <= 4 -> 1.00
#   Every other constraint is hand-set loose: composites sit 0.05..0.14 away
#   from every attainment_floor (epsilon 0.02 -> boundary hits 0 of 3, ratio
#   0 <= 0.70); OAT 0.03 <= stable_max 0.10; mean rho (0.88+0.92)/2 = 0.90
#   >= 0.70; H-5 effective L1 shift <= 0.46 <= 0.60; min dim weight on the
#   band is 0.4*0.5 = 0.20 >= 0.05. alpha_grid carries 0.20 BELOW
#   alpha_floor 0.30: it is excluded WITHOUT evaluation ([L609] key 1), the
#   floor itself (0.30, auto-injected per [L609]) IS evaluated and stays
#   drift-infeasible for EVERY drawn budget: drift(0.30) = 308/1875 =
#   0.16426..., while k is drawn from 0..16 -- so the floor row never
#   wins either, and the golden table below is exhaustive.
# ---------------------------------------------------------------------------
CAL_GRID = ('0.20', '0.50', '0.75', '1.00')
CAL_PERIODS = ('2026-01', '2026-02')
CAL_SIDS = ('S-1', 'S-2', 'S-3')
CAL_DIMS = {'D1': '0.6', 'D2': '0.4'}
CAL_METRICS = {'D1': {'M1': '0.4', 'M2': '0.4', 'M3': '0.2'},
               'D2': {'M4': '1'}}
CAL_SPEC = {'M1': 'D1', 'M2': 'D1', 'M3': 'D1', 'M4': 'D2'}
CAL_COLS = {'2026-01': {'M1': ['2', '6', '9'], 'M2': ['9', '2', '6'],
                        'M3': ['4', '4', '4'], 'M4': ['8', '8', '8']},
            '2026-02': {'M1': ['6', '2', '9'], 'M2': ['2', '9', '6'],
                        'M3': ['9', '6', '2'], 'M4': ['5', '5', '5']}}
CAL_BUDGET = {'alpha_floor': '0.30', 'drift_budget': '0.30',
              'boundary_budget': '0.70', 'boundary_epsilon': '0.02',
              'stable_max': '0.10', 'divergence_threshold': '0.70',
              'min_dim_weight': '0.05', 'max_shift_from_ahp': '0.60'}
CAL_FLOORS = {'L1': '0.80', 'L2': '0.60', 'L3': '0.40', 'L4': '0.00'}
CAL_COMPOSITE = {'2026-01': ('0.85', '0.72', '0.94'),
                 '2026-02': ('0.86', '0.75', '0.90')}
CAL_OAT = '0.03'
CAL_RHO = {'2026-01': '0.88', '2026-02': '0.92'}
CAL_SHIFT = D('0.000001')      # [L540] technical epsilon: an input, no digest value
CAL_SEED = 20260101


def _cal_rules():
    return grading.GradeRuleSet(
        rows=tuple(GradeRuleRow(
            grade_code=c, grade_label=c, attainment_floor=D(CAL_FLOORS[c]),
            evidence_class_min='D', redline_pass_required=True,
            promotion_streak=0, max_grade_if_no_target='L4')
            for c in ('L1', 'L2', 'L3', 'L4')),
        min_coverage_for_absolute_track=D('0.5'))


def _cal_context(period):
    '''Step 1-4 frames the injected pipeline would reuse ([L1016], RK-6). The
    fake pipeline below reads only case.period, so the frames stay empty (R-2).'''
    return ScoringContext(
        period=period, run_at=dt.datetime(2026, 1, 1, 9, 0, 0), run_id='run-e4b',
        seed=CAL_SEED, weight_version_id='WV-T-E4B', evidence_mode='GATE_ONLY',
        cel_enabled=False, input_fingerprints={},
        attainment=AttainmentFrame(rows=(), attainment_coverage={}),
        normalized=NormalizedFrame(rows=()), evidence=EvidenceFrame(rows=()),
        redline=RedlineFrame(rows=()), score=ScoreFrame(rows=()),
        grade=GradeFrame(rows=()), pool=PoolFrame(rows=()),
        pool_stats=PoolStats(rows=(), evidence_structure={'A': 0, 'B': 0, 'C': 0,
                                                          'D': 0},
                             not_assessed_count=0, not_assessed_reasons={}))


def _cal_case(period):
    cols = CAL_COLS[period]
    facts = {m: {s: cols[m][i] for i, s in enumerate(CAL_SIDS)}
             for m in sorted(cols)}
    return wcal.PeriodCase(period=period, facts=facts,
                           context=_cal_context(period), rules=_cal_rules())


def _cal_pipeline():
    '''Test-owned Step 5-7 stub ([L615] slot, the injection the module itself
    documents): the four indicators read only hand-set numbers (R-14), so no
    golden below is an implementation echo. The REAL entropy snapshot path
    (weights_combine -> dsm.entropy, ORCH-03) still runs for every period.'''
    def run(case, combined, alpha):
        return wcal.PeriodRun(
            period=case.period,
            composite_absolute={(s, VER, case.period): D(v) for s, v in
                                zip(CAL_SIDS, CAL_COMPOSITE[case.period])},
            oat_flip_rate=D(CAL_OAT), mean_rho=D(CAL_RHO[case.period]))
    return run


def _cal_hooks():
    '''ORCH-29 ruling 3: the four L0a capabilities weights_calibrate used to
    import are keyword-only REQUIRED injections on CalibrationInputs -- the
    sanctioned caller hands in the same bindings the production cli will.
    Detected via HOOK_NAMES so the body stays valid against the pre-ruling
    contract too (a TypeError here would mask the real guard).'''
    if not getattr(wcal, 'HOOK_NAMES', ()):
        return {}
    return dict(combine_fn=wc.combine, options_fn=wc.CombineOptions,
                entropy_window_fn=wc.calibrate_entropy_window,
                insufficient_sample_error=wc.EntropyInsufficientSample)


def _cal_inputs(pipeline=None):
    return wcal.CalibrationInputs(
        hierarchy=ahp_snapshot(CAL_DIMS, CAL_METRICS),
        metric_dict=metric_rows(CAL_SPEC), shift=CAL_SHIFT,
        period_cases={p: _cal_case(p) for p in CAL_PERIODS},
        run_id='cal-e4b-1', seed=CAL_SEED, draft_header=HDR13,
        pipeline=pipeline if pipeline is not None else _cal_pipeline(),
        option_overrides={'entropy_min_strategies': 3},
        **_cal_hooks())


def _cal_app(**over):
    block = dict(CAL_BUDGET)
    block.update(over)
    return config.AppConfig(eval_config={'weight_construction': block},
                            weights={}, redlines={}, grade_rules={},
                            anchor_set={}, ahp_matrices={})


def _cal_run(app, pipeline=None):
    '''The cli-frozen marshal, kept as KEYWORD arguments (dsm/cli.py
    cmd_calibrate): calibrate(grid=..., window=..., inputs=..., config=...).
    window is the SEQUENCE of period ids the real contract demands, not the
    {'periods': [...]} mapping the expected-signature body guessed.'''
    return wcal.calibrate(grid=list(CAL_GRID), window=list(CAL_PERIODS),
                          inputs=_cal_inputs(pipeline=pipeline), config=app)


def _cal_expected_alpha(k):
    '''Hand table above: alpha* as a function of drift_budget = k/100.'''
    if k >= 11:
        return q12(D('0.50'))
    if k >= 5:
        return q12(D('0.75'))
    return q12(ONE)


@st.composite
def _p13b_pair(draw):
    k1 = draw(st.integers(0, 16))          # ceiling: drift(0.30) = 0.16426...
    return k1, draw(st.integers(k1, 16))


@MAXEX
@given(_p13b_pair())
def test_p13b_calibration_run_never_mutates_governance_budgets(pair):
    '''P-13 [L1437] (calibration half): "calibrate / combine 的运行不得修改
    alpha_floor、drift_budget、boundary_budget、boundary_epsilon、
    min_dim_weight、max_shift_from_ahp 的取值" -- extended to all EIGHT
    governance keys weights_calibrate actually reads (K-11 stable_max and
    divergence_threshold included: guarding 6 of 8 keys is a hole).
    [L638] 标定不得自行放宽这些预算来凑出更小的 α. Module-local versions:
    tests/test_methods_calibrate.py::test_p13_* / ::test_t_cal_04_p13_*;
    this is the cross-module GLOBAL version driving the real
    CalibrationInputs / PeriodCase / GovernanceBudget containers. Guards:
    1 the signed config is byte-identical across a full run (both budgets);
    2 the report echoes the entered budget key for key, optional stays None;
    3 alpha* moves ONLY when the signed drift budget moves (hand table);
    4 monotone in tightening: k1 <= k2 -> alpha*(k1) >= alpha*(k2);
    5 [L609] key-1 governance: the below-floor candidate is excluded
      WITHOUT evaluation; every band candidate is evaluated; the drift
      values match the hand brackets 8/75 and 7/150, drift(1.00) = 0 exact;
    6 inputs=None raises the V-14 business exception, never a TypeError
      swallowed by the old gated body (that is what no-number-guessing
      looks like from the test side);
    7 every missing or PLACEHOLDER governance key is refused outright
      (MissingBudgetError, 8 keys x 2 variants) and the config is untouched;
    8 a budget widened mid-run trips GovernanceBudgetTamperError; an
      all-infeasible budget raises instead of relaxing, config untouched.'''
    k1, k2 = pair
    b1, b2 = str(Decimal(k1) / 100), str(Decimal(k2) / 100)
    app1 = _cal_app(drift_budget=b1)
    dump1 = app1.model_dump()
    r1 = _cal_run(app1)
    assert app1.model_dump() == dump1                        # guard 1
    app2 = _cal_app(drift_budget=b2)
    dump2 = app2.model_dump()
    r2 = _cal_run(app2)
    assert app2.model_dump() == dump2                        # guard 1
    for report, budget in ((r1, b1), (r2, b2)):              # guard 2
        signed = dict(CAL_BUDGET, drift_budget=budget)
        for key, signed_value in signed.items():
            assert eq_tol(D(getattr(report.budget, key)), D(signed_value), TOL)
        assert report.budget.min_metric_weight is None
    assert r1.alpha_star == _cal_expected_alpha(k1)          # guard 3
    assert r2.alpha_star == _cal_expected_alpha(k2)
    assert D(r1.alpha_star) >= D(r2.alpha_star)              # guard 4
    assert len(r1.rows) == 5                                 # guard 5
    floor_row = r1.row(D('0.30'))
    assert floor_row.evaluated is True and floor_row.alpha_floor_ok is True
    assert floor_row.feasible is False                        # never wins
    below = r1.row(D('0.20'))
    assert below.evaluated is False and below.alpha_floor_ok is False
    assert (r1.excluded_alphas[q12(D('0.20'))]
            == RC.ALPHA_FLOOR_INFEASIBLE.value)
    assert all(row.evaluated for row in r1.rows if D(row.alpha) >= D('0.30'))
    assert D(r1.alpha_star) >= D(CAL_BUDGET['alpha_floor'])
    assert D('0.10') < D(r1.row(D('0.50')).weight_drift) < D('0.11')   # 8/75
    assert D('0.04') < D(r1.row(D('0.75')).weight_drift) < D('0.05')   # 7/150
    assert eq_tol(D(r1.row(ONE).weight_drift), ZERO, TOL)              # pure AHP
    with pytest.raises(wcal.CalibrateError) as none_inputs:            # guard 6
        wcal.calibrate(grid=list(CAL_GRID), window=list(CAL_PERIODS),
                       inputs=None, config=app1)
    assert not isinstance(none_inputs.value, TypeError)
    assert app1.model_dump() == dump1
    for key in wcal.BUDGET_KEYS:                                     # guard 7
        gone = {k: v for k, v in CAL_BUDGET.items() if k != key}
        with pytest.raises(wcal.MissingBudgetError):
            wcal.calibrate(grid=list(CAL_GRID), window=list(CAL_PERIODS),
                           inputs=_cal_inputs(),
                           config={'eval_config': {'weight_construction': gone}})
        slot = dict(CAL_BUDGET)
        slot[key] = 'PLACEHOLDER'
        with pytest.raises(wcal.MissingBudgetError):
            wcal.calibrate(grid=list(CAL_GRID), window=list(CAL_PERIODS),
                           inputs=_cal_inputs(),
                           config={'eval_config': {'weight_construction': slot}})
    widened = {'eval_config': {'weight_construction':
                               dict(CAL_BUDGET, drift_budget='0.05')}}   # guard 8
    hits = []

    def tamper(case, combined, alpha):
        hits.append(str(alpha))
        if len(hits) == 1:
            (widened['eval_config']['weight_construction']
             ['drift_budget']) = '0.99'      # RK-12 attack behind calibrate's back
        return _cal_pipeline()(case, combined, alpha)

    with pytest.raises(wcal.GovernanceBudgetTamperError) as moved:
        _cal_run(widened, pipeline=tamper)
    assert 'drift_budget' in str(moved.value)
    tight = _cal_app(stable_max='0.01')               # every OAT 0.03 > 0.01
    dump_t = tight.model_dump()
    with pytest.raises(wcal.CalibrateError) as bad:
        _cal_run(tight)
    assert 'widen' in str(bad.value)                  # refuses, never relaxes
    assert tight.model_dump() == dump_t


# ---------------------------------------------------------------------------
# P-14 [L1438] combined weights normalised -- published document layer
# ---------------------------------------------------------------------------
@st.composite
def _comb_scenario(draw):
    dim_w = unit({'D1': str(draw(st.integers(1, 9))),
                  'D2': str(draw(st.integers(1, 9)))})
    met_w = {'D1': unit({'M1': str(draw(st.integers(1, 9))),
                         'M2': str(draw(st.integers(1, 9)))}),
             'D2': unit({'M3': str(draw(st.integers(1, 9)))})}
    columns = {}
    for metric_id in ('M1', 'M2', 'M3'):
        if draw(st.booleans()):
            base = str(draw(st.integers(1, 50)))
            columns[metric_id] = [base, base, base]     # zero variation
        else:
            columns[metric_id] = [str(draw(st.integers(1, 999)))
                                  for _ in range(3)]
    fk = draw(st.integers(0, 90))
    ak = draw(st.integers(fk, 100))
    return dim_w, met_w, columns, Decimal(fk) / 100, Decimal(ak) / 100


@MAXEX
@given(_comb_scenario())
def test_p14_published_weight_version_doc_is_normalised_and_consumable(case):
    '''P-14 [L1438]: "任意 α、任意回退组合下, Σ W_d = 1 且每维度内 Σ w_j = 1
    (1e-12)". Why: every downstream composite assumes the simplex; a published
    document off it silently rescales all grades. Module-local version:
    tests/test_methods_combine.py::test_p14_combined_weights_are_normalised
    checks the CombinedWeights object; the E4 global version checks the
    PUBLISHED WeightVersionDoc (the artifact that actually ships) and that
    dsm.aggregate consumes it (compose succeeds and, with every attainment
    hand-set to 1, the composite must equal exactly 1 -- [L464] collapses to
    Σ W_d Σ w_j = 1, a hand-derived expectation).'''
    dim_w, met_w, columns, floor, alpha = case
    spec = dict(SPEC12)
    opts = wc.CombineOptions(alpha=D(alpha), alpha_floor=D(floor),
                             min_dim_weight=ZERO, entropy_min_strategies=3,
                             max_shift_from_ahp=D('5'))
    snap = window(columns, spec, SIDS12, opts)
    combined = wc.combine(ahp_snapshot(dim_w, met_w), snap, opts)
    doc = wc.step6_draft(combined, HDR13)
    assert eq_tol(sum((D(doc.level1_weights[d])
                       for d in sorted(doc.level1_weights)), ZERO), ONE, TOL)
    for d in sorted(doc.level2_weights):
        assert eq_tol(sum((D(doc.level2_weights[d][m])
                           for m in sorted(doc.level2_weights[d])), ZERO),
                      ONE, TOL)
    shipped = frozen_doc({d: doc.level1_weights[d]
                          for d in doc.level1_weights},
                         doc.level2_weights, wv='WV-SHIP')
    ones = {m: D('1') for m in ('M1', 'M2', 'M3')}
    frame = aggregate.compose(abs_frame('S1', ones), rel_frame('S1', ones),
                              shipped)
    assert eq_tol(frame.rows[0].composite_absolute, ONE, TOL)


# ---------------------------------------------------------------------------
# P-15 [L1439] fallback keeps the AHP weight -- published document layer
# ---------------------------------------------------------------------------
@MAXEX
@given(rnd=st.integers(1, 9))
def test_p15_fallback_metric_keeps_its_ahp_weight_in_the_published_doc(rnd):
    '''P-15 [L1439]: "命中 ENTROPY_INACTIVE_FALLBACK 的指标, 其组合权重严格等于
    AHP 权重(未经维度归一前)". Why: an INACTIVE metric carries no information
    for the entropy track; silently letting the renormalisation move its
    fallback weight would let "no data" masquerade as a data-driven vote.
    Module-local version: tests/test_methods_combine.py::
    test_p15_fallback_keeps_the_ahp_weight (CombinedWeights object layer);
    the E4 global version asserts the equality on the step6_draft PUBLISHED
    document -- what every consumer actually reads. Tolerance numeric.TOL.'''
    dim_w = {'D1': '0.6', 'D2': '0.4'}
    met_w = {'D1': unit({'M1': str(rnd), 'M2': str(10 - rnd)}),
             'D2': {'M3': '1'}}
    columns = {'M1': ['4', '90', str(rnd + 1)], 'M2': ['77', '77', '77'],
               'M3': ['6', '60', '600']}
    opts = wc.CombineOptions(alpha=D('0.5'), alpha_floor=D('0.3'),
                             min_dim_weight=ZERO, entropy_min_strategies=3,
                             max_shift_from_ahp=D('5'))
    snap = window(columns, SPEC12, SIDS12, opts)
    assert snap is not None
    combined = wc.combine(ahp_snapshot(dim_w, met_w), snap, opts)
    assert 'M2' in combined.inactive_fallback_metrics  # zero-variation column
    doc = wc.step6_draft(combined, HDR13)
    for metric_id in combined.inactive_fallback_metrics:
        dim = combined.metric_trace[metric_id].dim_code
        assert eq_tol(D(doc.level2_weights[dim][metric_id]),
                      D(combined.ahp.metric_weights[dim][metric_id]), TOL)
        assert combined.metric_trace[metric_id].is_fallback is True
