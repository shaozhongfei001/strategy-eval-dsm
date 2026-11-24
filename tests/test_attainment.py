'''Tests for dsm.attainment -- guard tests G-01 and G-04 (SDD 3.16.2).

G-01 covers the four formulas of 2.3.1 against hand-computed values at 1e-12,
the governance clip of A-3, the coverage ratio of [L928] and A-4: the absolute
track must not move when the pool around it changes.
G-04 covers the boundary line of [L930]: missing target, missing interval
bounds, zero denominator, a negative actual under each missing_rule, an unknown
metric and a degenerate interval.

Every expected number below is hand-computed from the constructed input (R-14);
none of them was read off the implementation. Input rows are built directly
from dsm.models (R-2): metric_facts and metric_dict are pydantic rows, because
MetricFactFrame / MetricDict do not exist in the contract layer.
'''
import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from dsm import attainment, numeric
from dsm.attainment import (
    AttainmentBlockedError, AttainmentConfigError, AttainmentError,
    AttainmentImputeError, AttainmentParams)
from dsm.config import AppConfig
from dsm.models import AttainmentFrame, MetricDictRow, MetricFactRow
from dsm.numeric import D, ZERO, eq_tol
from dsm.reason_codes import RC

CAP = D('1.2')
SIGNED = ('SIGNED',)
DT = datetime.datetime(2026, 1, 31, 0, 0, 0)
DAY = datetime.date(2026, 1, 31)


def _metric(metric_id, formula, direction, unit, target, missing_rule='SKIP',
            signoff_status='SIGNED'):
    '''One T2 metric_dict row, field names copied from dsm.models (R-2).'''
    return MetricDictRow(
        metric_id=metric_id, metric_name=metric_id, dim_code='D1',
        numerator_def='numerator', time_window='MONTHLY', dedup_rule='NONE',
        missing_rule=missing_rule, outlier_rule='CLIP_P1_P99',
        attainment_formula=formula, direction=direction, unit=unit,
        target_value=target, target_basis='budget', is_redline=False,
        owner_name='owner', signoff_status=signoff_status,
        dim_signoff_status='SIGNED', dict_version='MD-1',
        caliber_version='CAL-1')


def _fact(strategy_id, metric_id, value, version_id='V1', period='2026-01'):
    '''One T3 metric_facts row.'''
    return MetricFactRow(
        strategy_id=strategy_id, version_id=version_id, period=period,
        metric_id=metric_id, value_num=value, value=value,
        data_quality_flag='OK', snapshot_time=DT, data_as_of=DAY,
        source_table='t_fact', caliber_version='CAL-1')


def _params(cap=CAP, on_zero=None, signed=SIGNED):
    return AttainmentParams(attainment_cap=cap, on_zero=on_zero,
                            signed_off_statuses=signed)


def _cfg(cap='1.2'):
    return AppConfig(
        eval_config={'attainment': {'cap': cap, 'on_zero': None,
                                    'signed_off_statuses': list(SIGNED)}},
        weights={}, redlines={}, grade_rules={}, anchor_set={}, ahp_matrices={})


def _compute(facts, metrics, **kw):
    params = kw.pop('params', None)
    return attainment.compute(facts, metrics, params=params or _params(), **kw)


def _row(frame, strategy_id, metric_id):
    for r in frame.rows:
        if r.strategy_id == strategy_id and r.metric_id == metric_id:
            return r
    raise AssertionError('row missing: ' + strategy_id + ' / ' + metric_id)


# ---------------------------------------------------------------------------
# G-01 -- the four formulas, the clip, the coverage ratio and A-4.
# ---------------------------------------------------------------------------
def test_g01_ratio_direct_positive():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    r = _row(_compute([_fact('S1', 'm_ratio', D('0.15'))], [m]), 'S1', 'm_ratio')
    # 0.15 / 0.20 = 0.75
    assert eq_tol(r.attainment, D('0.75'))
    assert r.direction == 1 and r.has_target is True and r.capped_flag is False
    assert r.reason_code is None and r.target_source == 'budget'


def test_g01_inverse_ratio_negative_direction():
    m = _metric('m_cost', 'INVERSE_RATIO', -1, 'MONEY_MINOR', 100000)
    fr = _compute([_fact('S1', 'm_cost', 80000)], [m], params=_params(cap=D('2')))
    r = _row(fr, 'S1', 'm_cost')
    # 100000 / 80000 = 1.25
    assert eq_tol(r.attainment, D('1.25'))
    assert r.direction == -1 and r.capped_flag is False


def test_g01_shortfall_clamped_never_exceeds_one():
    up = _metric('m_cnt', 'SHORTFALL_CLAMPED', 1, 'COUNT', 200)
    fr = _compute([_fact('S1', 'm_cnt', 300), _fact('S2', 'm_cnt', 150)], [up])
    # min(1, 300/200) = 1 ; min(1, 150/200) = 0.75
    assert eq_tol(_row(fr, 'S1', 'm_cnt').attainment, numeric.ONE)
    assert eq_tol(_row(fr, 'S2', 'm_cnt').attainment, D('0.75'))
    # the formula's own ceiling is not the governance cap, so no capped_flag
    assert _row(fr, 'S1', 'm_cnt').capped_flag is False
    down = _metric('m_cost2', 'SHORTFALL_CLAMPED', -1, 'MONEY_MINOR', 100000)
    fr2 = _compute([_fact('S1', 'm_cost2', 50000), _fact('S2', 'm_cost2', 200000)],
                   [down])
    # min(1, 100000/50000) = 1 ; min(1, 100000/200000) = 0.5
    assert eq_tol(_row(fr2, 'S1', 'm_cost2').attainment, numeric.ONE)
    assert eq_tol(_row(fr2, 'S2', 'm_cost2').attainment, D('0.5'))


def test_g01_interval_inside_outside_and_far_outside():
    m = _metric('m_iv', 'INTERVAL', 1, 'RATIO', D('15'))
    iv = {'m_iv': (D('10'), D('20'))}
    fr = _compute([_fact('S1', 'm_iv', D('15')), _fact('S2', 'm_iv', D('22')),
                   _fact('S3', 'm_iv', D('8')), _fact('S4', 'm_iv', D('30'))],
                  [m], intervals=iv)
    # halfwidth = (20 - 10) / 2 = 5
    assert eq_tol(_row(fr, 'S1', 'm_iv').attainment, numeric.ONE)   # dist 0
    assert eq_tol(_row(fr, 'S2', 'm_iv').attainment, D('0.6'))      # 1 - 2/5
    assert eq_tol(_row(fr, 'S3', 'm_iv').attainment, D('0.6'))      # 1 - 2/5
    far = _row(fr, 'S4', 'm_iv')
    assert eq_tol(far.attainment, ZERO)          # 1 - 10/5 = -1 -> clip to 0
    assert far.capped_flag is False and far.reason_code is None


def test_g01_cap_clips_and_sets_capped_flag():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    r = _row(_compute([_fact('S1', 'm_ratio', D('0.30'))], [m]), 'S1', 'm_ratio')
    # 0.30 / 0.20 = 1.5, above the 1.2 governance cap of A-3
    assert eq_tol(r.attainment, CAP)
    assert r.capped_flag is True and r.reason_code == RC.ATTAINMENT_CAPPED


def test_g01_coverage_counts_signed_off_metrics_only():
    metrics = [
        _metric('m_a', 'RATIO_DIRECT', 1, 'RATIO', D('0.2')),
        _metric('m_b', 'RATIO_DIRECT', 1, 'RATIO', D('0.4')),
        _metric('m_c', 'RATIO_DIRECT', 1, 'RATIO', None),
        _metric('m_d', 'RATIO_DIRECT', 1, 'RATIO', D('0.6'), signoff_status='PENDING'),
    ]
    facts = [_fact('S1', mid, D('0.1')) for mid in ('m_a', 'm_b', 'm_c', 'm_d')]
    facts.append(_fact('S2', 'm_a', D('0.1')))
    fr = _compute(facts, metrics)
    # denominator: m_a, m_b, m_c are SIGNED -> 3
    # S1 numerator: signed-off AND has a target -> m_a, m_b = 2 -> 2/3
    assert eq_tol(fr.attainment_coverage['S1'], D('0.666666666667'))
    assert eq_tol(fr.attainment_coverage['S2'], D('0.333333333333'))
    assert tuple(fr.attainment_coverage) == ('S1', 'S2')


def test_g01_absolute_track_ignores_the_pool():
    '''A-4: the grade floors hang on attainment, so attainment must be a
    function of the fact and the target alone -- never of the peers.'''
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    solo = _row(_compute([_fact('S1', 'm_ratio', D('0.15'))], [m]), 'S1', 'm_ratio')
    pool = _row(_compute([_fact('S1', 'm_ratio', D('0.15')),
                          _fact('S2', 'm_ratio', D('0.19')),
                          _fact('S3', 'm_ratio', D('0.01'))], [m]), 'S1', 'm_ratio')
    assert eq_tol(solo.attainment, pool.attainment)
    assert eq_tol(pool.attainment, D('0.75'))
    assert solo.capped_flag == pool.capped_flag and solo.reason_code == pool.reason_code


def test_g01_rows_are_sorted_by_the_locator_key():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S2', 'm_ratio', D('0.10')),
             _fact('S1', 'm_ratio', D('0.10'), period='2026-02'),
             _fact('S1', 'm_ratio', D('0.10'), period='2026-01')]
    fr = _compute(facts, [m])
    keys = [(r.strategy_id, r.version_id, r.period, r.metric_id) for r in fr.rows]
    assert len(keys) == 3 and keys == sorted(keys)


def test_g01_config_entry_point_reads_the_governance_block():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    fr = attainment.compute([_fact('S1', 'm_ratio', D('0.15'))], [m], _cfg())
    assert eq_tol(_row(fr, 'S1', 'm_ratio').attainment, D('0.75'))
    assert fr.attainment_coverage['S1'] == numeric.ONE


# ---------------------------------------------------------------------------
# G-04 -- the boundary line of [L930].
# ---------------------------------------------------------------------------
def test_g04_missing_target_stays_null():
    '''A-2: no pool mean, no historical mean -- null plus the registered code.'''
    m = _metric('m_nt', 'RATIO_DIRECT', 1, 'RATIO', None)
    r = _row(_compute([_fact('S1', 'm_nt', D('0.15'))], [m]), 'S1', 'm_nt')
    assert r.attainment is None and r.has_target is False
    assert r.capped_flag is False and r.reason_code == RC.NO_TARGET_VALUE
    assert r.direction == 1 and r.target_source == 'budget'


def test_g04_missing_interval_bounds_stay_null():
    m = _metric('m_iv', 'INTERVAL', 1, 'RATIO', D('15'))
    r = _row(_compute([_fact('S1', 'm_iv', D('15'))], [m]), 'S1', 'm_iv')
    assert r.attainment is None and r.has_target is False
    assert r.reason_code == RC.NO_TARGET_VALUE


def test_g04_zero_denominator_follows_the_declared_on_zero():
    m = _metric('m_cost', 'INVERSE_RATIO', -1, 'MONEY_MINOR', 100000)
    facts = [_fact('S1', 'm_cost', 0)]
    undefined = _row(_compute(facts, [m]), 'S1', 'm_cost')
    assert undefined.attainment is None and undefined.has_target is True
    assert undefined.reason_code is None   # the registry carries no code for this
    declared = _row(_compute(facts, [m], params=_params(on_zero=D('1'))), 'S1', 'm_cost')
    assert eq_tol(declared.attainment, numeric.ONE)


@pytest.mark.parametrize('rule, expected', [
    ('SKIP', None), ('ZERO', ZERO), ('IMPUTE_MEDIAN', numeric.ONE)])
def test_g04_negative_actual_follows_the_metric_missing_rule(rule, expected):
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'), missing_rule=rule)
    facts = [_fact('S1', 'm_ratio', D('-0.05')), _fact('S2', 'm_ratio', D('0.10')),
             _fact('S3', 'm_ratio', D('0.30'))]
    r = _row(_compute(facts, [m]), 'S1', 'm_ratio')
    if expected is None:
        assert r.attainment is None
    else:
        # IMPUTE_MEDIAN: median(0.10, 0.30) = 0.20 -> 0.20 / 0.20 = 1
        assert eq_tol(r.attainment, expected)
    assert r.reason_code == RC.NEGATIVE_ACTUAL and r.has_target is True
    peer = _row(_compute(facts, [m]), 'S2', 'm_ratio')
    assert eq_tol(peer.attainment, D('0.5')) and peer.reason_code is None


def test_g04_negative_actual_with_block_rule_raises():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'), missing_rule='BLOCK')
    with pytest.raises(AttainmentBlockedError):
        _compute([_fact('S1', 'm_ratio', D('-0.05'))], [m])


def test_g04_no_target_wins_over_negative_actual():
    m = _metric('m_nt', 'RATIO_DIRECT', 1, 'RATIO', None, missing_rule='ZERO')
    r = _row(_compute([_fact('S1', 'm_nt', D('-1'))], [m]), 'S1', 'm_nt')
    assert r.attainment is None and r.has_target is False
    assert r.reason_code == RC.NO_TARGET_VALUE


def test_g04_unknown_metric_in_facts_raises():
    m = _metric('m_known', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    with pytest.raises(AttainmentError):
        _compute([_fact('S1', 'm_ghost', D('0.10'))], [m])


def test_g04_degenerate_interval_is_a_point_test():
    m = _metric('m_iv', 'INTERVAL', 1, 'RATIO', D('15'))
    iv = {'m_iv': (D('15'), D('15'))}
    fr = _compute([_fact('S1', 'm_iv', D('15')), _fact('S2', 'm_iv', D('16'))], [m],
                  intervals=iv)
    assert eq_tol(_row(fr, 'S1', 'm_iv').attainment, numeric.ONE)
    assert eq_tol(_row(fr, 'S2', 'm_iv').attainment, ZERO)


def test_g04_reversed_interval_bounds_raise():
    m = _metric('m_iv', 'INTERVAL', 1, 'RATIO', D('15'))
    with pytest.raises(AttainmentError):
        _compute([_fact('S1', 'm_iv', D('15'))], [m],
                 intervals={'m_iv': (D('20'), D('10'))})


def test_g04_exactly_one_parameter_source_is_required():
    m = _metric('m_ratio', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_ratio', D('0.15'))]
    with pytest.raises(AttainmentError):
        attainment.compute(facts, [m])
    with pytest.raises(AttainmentError):
        attainment.compute(facts, [m], _cfg(), params=_params())
    with pytest.raises(ValidationError):
        _params(cap=ZERO)
    with pytest.raises(ValidationError):
        AttainmentParams(attainment_cap=CAP, on_zero=None, signed_off_statuses=())


def test_g04_params_from_config_rejects_an_incomplete_block():
    empty = AppConfig(eval_config={'attainment': {}}, weights={}, redlines={},
                      grade_rules={}, anchor_set={}, ahp_matrices={})
    with pytest.raises(AttainmentConfigError):
        attainment.params_from_config(empty)
    absent = AppConfig(eval_config={}, weights={}, redlines={}, grade_rules={},
                       anchor_set={}, ahp_matrices={})
    with pytest.raises(AttainmentConfigError):
        attainment.params_from_config(absent)


# ---------------------------------------------------------------------------
# G-09 -- the second trigger of the [L1134] closed set: a row the long table
# never carried ([L1156] shows a missing metric as an absent row, not as an
# empty column). Each of the four branches gets its own test, and one test pins
# that the four observables are pairwise different, which is what G-09 [L1411]
# asks for.
# ---------------------------------------------------------------------------
def test_g09_missing_row_zero_is_a_scored_zero_not_a_dropped_row():
    '''ZERO on a missing row: one attainment row carrying 0, not a hole.'''
    m_zero = _metric('m_zero', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'),
                     missing_rule='ZERO')
    m_peer = _metric('m_peer', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_peer', D('0.10')),          # S1 misses the m_zero cell
             _fact('S2', 'm_zero', D('0.10')), _fact('S2', 'm_peer', D('0.10'))]
    fr = _compute(facts, [m_zero, m_peer])
    rows = [r for r in fr.rows if r.metric_id == 'm_zero']
    assert len(rows) == 2 and {r.strategy_id for r in rows} == {'S1', 'S2'}
    made = _row(fr, 'S1', 'm_zero')
    assert made.attainment == ZERO and made.has_target is True
    assert made.capped_flag is False
    # 3.3.2 registers no code for a missing row counted as zero, and spelling a
    # literal is H-7 territory, so the row stays uncovered and the gap is filed.
    assert made.reason_code is None
    assert made.direction == 1 and made.target_source == 'budget'
    assert fr.downgrades == ()


def test_g09_missing_row_zero_on_an_inverse_metric_is_zero_not_null():
    '''ZERO counts the ATTAINMENT as 0. Substituting a zero actual instead would
    run target / 0 here and land on on_zero None -> null, which is the SKIP
    observable and would collapse two of the four branches.'''
    m = _metric('m_cost', 'INVERSE_RATIO', -1, 'MONEY_MINOR', 100000,
                missing_rule='ZERO')
    keep = _metric('m_keep', 'INVERSE_RATIO', -1, 'MONEY_MINOR', 100000)
    facts = [_fact('S1', 'm_keep', 80000),
             _fact('S2', 'm_cost', 80000), _fact('S2', 'm_keep', 80000)]
    fr = _compute(facts, [m, keep], params=_params(cap=D('2'), on_zero=None))
    assert _row(fr, 'S1', 'm_cost').attainment == ZERO
    assert eq_tol(_row(fr, 'S2', 'm_cost').attainment, D('1.25'))


def test_g09_missing_row_skip_drops_the_row_and_leaves_the_peers_alone():
    '''SKIP on a missing row: no row at all, so [L954] renormalises inside the
    dimension, and the coverage numerator does not widen -- [L928] counts what
    the strategy reported with a target, not what was invented for it.'''
    m_skip = _metric('m_skip', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'),
                     missing_rule='SKIP')
    m_other = _metric('m_other', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_other', D('0.10')),
             _fact('S2', 'm_skip', D('0.10')), _fact('S2', 'm_other', D('0.10'))]
    fr = _compute(facts, [m_skip, m_other])
    assert [r for r in fr.rows
            if (r.strategy_id, r.metric_id) == ('S1', 'm_skip')] == []
    assert eq_tol(_row(fr, 'S1', 'm_other').attainment, D('0.5'))
    assert eq_tol(fr.attainment_coverage['S1'], D('0.5'))     # 1 of 2 signed
    assert eq_tol(fr.attainment_coverage['S2'], numeric.ONE)  # 2 of 2 signed
    assert fr.downgrades == ()


def test_g09_missing_row_impute_median_is_decimal_and_stays_in_its_bucket():
    '''IMPUTE_MEDIAN on a missing row: median of the non-negative actuals of the
    same (version_id, period, metric_id), Decimal end to end (V-9).

    10000000000.1 and 10000000000.3 are not representable in binary floating
    point, so a float mean of them carries a 7.6e-7 tail that survives q12; the
    Decimal median is exactly 10000000000.2. The negative actual and the v2 row
    are both outside the sample: the negative is the very thing being replaced,
    the v2 row is another [L1149] bucket.
    '''
    m = _metric('m_roi', 'RATIO_DIRECT', 1, 'RATIO', D('1'),
                missing_rule='IMPUTE_MEDIAN')
    anchor = _metric('m_anchor', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_roi', D('10000000000.1')),
             _fact('S2', 'm_roi', D('10000000000.3')),
             _fact('S3', 'm_roi', D('-5')),
             _fact('S4', 'm_roi', D('99'), version_id='V2'),
             _fact('S5', 'm_anchor', D('0.10'))]        # S5 misses the m_roi cell
    fr = _compute(facts, [m, anchor], params=_params(cap=D('100000000000')))
    made = _row(fr, 'S5', 'm_roi')
    assert isinstance(made.attainment, Decimal)
    assert made.attainment == D('10000000000.200000000000')
    assert made.has_target is True and made.capped_flag is False


def test_g09_missing_row_block_suppresses_the_strategy_and_records_not_assessed():
    '''BLOCK on a missing row: [L1411] says the strategy produces no score, so
    the whole (strategy, version, period) leaves the frame -- aggregate.compose
    builds one ScoreRow per key it finds here, and a single leftover row would
    score it. The removal is disclosed as a [L1051] item-13 DowngradeAction with
    the registered NOT_ASSESSED code, never silently (V-14 / H-6).'''
    blocked = _metric('m_red', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'),
                      missing_rule='BLOCK')
    other = _metric('m_other', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_other', D('0.10')),          # S1 misses the BLOCK cell
             _fact('S2', 'm_red', D('0.10')), _fact('S2', 'm_other', D('0.10'))]
    fr = _compute(facts, [blocked, other])
    assert [r for r in fr.rows if r.strategy_id == 'S1'] == []
    assert len([r for r in fr.rows if r.strategy_id == 'S2']) == 2
    assert isinstance(fr, AttainmentFrame)          # the contract type still holds
    assert len(fr.downgrades) == 1
    assert fr.downgrades[0].reason_code == RC.NOT_ASSESSED
    assert fr.downgrades[0].subject == 'S1|V1|2026-01'
    assert 'm_red' in fr.downgrades[0].action
    assert fr.attainment_coverage['S1'] == ZERO      # nothing of S1 was scored


def test_g09_missing_row_four_branches_are_pairwise_different():
    '''G-09 [L1411]: four carriers, identical formula / direction / target, one
    missing cell each -> four observables, no two alike.'''
    tags = ('zero', 'skip', 'impute', 'block')
    rules = {'zero': 'ZERO', 'skip': 'SKIP', 'impute': 'IMPUTE_MEDIAN',
             'block': 'BLOCK'}
    metrics = [_metric('m_' + tag, 'RATIO_DIRECT', 1, 'RATIO', D('0.20'),
                       missing_rule=rules[tag]) for tag in tags]
    anchor = _metric('m_anchor', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = []
    for tag in tags:
        facts.append(_fact('S_' + tag, 'm_anchor', D('0.10')))
        for other in tags:
            if other != tag:
                facts.append(_fact('S_' + tag, 'm_' + other, D('0.10')))
    # P1 is a complete peer: a peer with holes of its own would drag the other
    # three branches into this test.
    facts.append(_fact('P1', 'm_impute', D('0.30')))
    facts.append(_fact('P1', 'm_anchor', D('0.10')))
    for tag in tags:
        if tag != 'impute':
            facts.append(_fact('P1', 'm_' + tag, D('0.10')))
    fr = _compute(facts, metrics + [anchor])

    def cells(sid, mid):
        return [r for r in fr.rows if (r.strategy_id, r.metric_id) == (sid, mid)]

    zero = cells('S_zero', 'm_zero')
    skip = cells('S_skip', 'm_skip')
    imp = cells('S_impute', 'm_impute')
    observable = {
        'ZERO': (len(zero), zero[0].attainment),
        'SKIP': (len(skip), 'no row, dimension renormalised'),
        # sample = [0.10, 0.10, 0.10, 0.30] -> median 0.10 -> 0.10 / 0.20 = 0.5
        'IMPUTE_MEDIAN': (len(imp), imp[0].attainment),
        'BLOCK': (len([r for r in fr.rows if r.strategy_id == 'S_block']),
                  'the strategy produced no row at all'),
    }
    assert observable['ZERO'] == (1, ZERO)
    assert observable['SKIP'] == (0, 'no row, dimension renormalised')
    assert observable['IMPUTE_MEDIAN'] == (1, D('0.500000000000'))
    assert observable['BLOCK'][0] == 0
    assert len(set(observable.values())) == 4, observable
    assert [d.subject for d in fr.downgrades] == ['S_block|V1|2026-01']


def test_g09_missing_target_outranks_the_missing_rule_even_for_block():
    '''[L451] / A-2 first: a metric with no target is out of the absolute track,
    so there is no attainment for any missing_rule to dispose of -- not even a
    BLOCK may sink a strategy over it.'''
    m = _metric('m_nt', 'RATIO_DIRECT', 1, 'RATIO', None, missing_rule='BLOCK')
    other = _metric('m_other', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('S1', 'm_other', D('0.10')),
             _fact('S2', 'm_nt', D('0.10')), _fact('S2', 'm_other', D('0.10'))]
    fr = _compute(facts, [m, other])
    made = _row(fr, 'S1', 'm_nt')
    assert made.attainment is None and made.has_target is False
    assert made.reason_code == RC.NO_TARGET_VALUE
    assert len([r for r in fr.rows if r.strategy_id == 'S1']) == 2
    assert fr.downgrades == ()


def test_g09_the_grid_invents_no_strategy_version_or_period():
    '''The synthesized cells are the dictionary crossed with the (strategy,
    version, period) keys the fact table carries -- nothing beyond that.'''
    m = _metric('m_a', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'), missing_rule='ZERO')
    n = _metric('m_b', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'), missing_rule='ZERO')
    fr = _compute([_fact('S1', 'm_a', D('0.10'), period='2026-01')], [m, n])
    assert {(r.strategy_id, r.version_id, r.period, r.metric_id)
            for r in fr.rows} == {('S1', 'V1', '2026-01', 'm_a'),
                                  ('S1', 'V1', '2026-01', 'm_b')}
    assert tuple(fr.attainment_coverage) == ('S1',)


def test_g09_unknown_missing_rule_raises_on_both_triggers():
    '''V-14: a name outside the [L1134] closed set raises, on a missing row and
    on a negative actual alike. Defaulting to SKIP is exactly the silent
    degradation that let the four branches collapse.'''
    m = _metric('m_x', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'), missing_rule='SKIP')
    object.__setattr__(m, 'missing_rule', 'IMPUTE_MEAN')   # past the Literal gate
    anchor = _metric('m_anchor', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    with pytest.raises(AttainmentError, match='unknown missing_rule'):
        _compute([_fact('S1', 'm_anchor', D('0.10'))], [m, anchor])
    with pytest.raises(AttainmentError, match='unknown missing_rule'):
        _compute([_fact('S1', 'm_x', D('-1')), _fact('S1', 'm_anchor', D('0.10'))],
                 [m, anchor])


def test_g09_impute_without_a_clean_sample_refuses_to_degrade_to_skip():
    '''A missing row with nothing to impute from raises instead of vanishing; a
    negative actual with nothing to impute from keeps its row and its registered
    NEGATIVE_ACTUAL, because there the disclosure channel exists.'''
    m = _metric('m_roi', 'RATIO_DIRECT', 1, 'RATIO', D('0.10'),
                missing_rule='IMPUTE_MEDIAN')
    anchor = _metric('m_anchor', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    with pytest.raises(AttainmentImputeError):
        _compute([_fact('S1', 'm_anchor', D('0.10'))], [m, anchor])
    fr = _compute([_fact('S1', 'm_roi', D('-1')),
                   _fact('S1', 'm_anchor', D('0.10'))], [m, anchor])
    r = _row(fr, 'S1', 'm_roi')
    assert r.attainment is None and r.reason_code == RC.NEGATIVE_ACTUAL


def test_g09_impute_sample_scope_is_an_explicit_input_not_a_default():
    '''[L1134] names IMPUTE_MEDIAN and states no sample scope, so the scope is an
    input (V-14). ALL_ROWS samples every non-negative actual of the metric;
    SIGNED_OFF_ONLY applies [L1141], which for a single-metric sample leaves an
    unsigned metric with no sample at all -- and that refuses to impute rather
    than quietly falling back.'''
    signed = _metric('m_roi', 'RATIO_DIRECT', 1, 'RATIO', D('0.10'),
                     missing_rule='IMPUTE_MEDIAN')
    pending = _metric('m_pending', 'RATIO_DIRECT', 1, 'RATIO', D('0.10'),
                      missing_rule='IMPUTE_MEDIAN', signoff_status='PENDING')
    anchor = _metric('m_anchor', 'RATIO_DIRECT', 1, 'RATIO', D('0.20'))
    facts = [_fact('P1', 'm_roi', D('0.30')), _fact('P1', 'm_pending', D('0.30')),
             _fact('P1', 'm_anchor', D('0.10')),
             _fact('S1', 'm_anchor', D('0.10'))]       # S1 misses both cells
    wide = _compute(facts, [signed, pending, anchor], params=_params(cap=D('5')))
    assert eq_tol(_row(wide, 'S1', 'm_pending').attainment, D('3'))
    assert eq_tol(_row(wide, 'S1', 'm_roi').attainment, D('3'))
    with pytest.raises(AttainmentImputeError):
        _compute(facts, [signed, pending, anchor], params=_params(cap=D('5')),
                 impute_scope=attainment.IMPUTE_SCOPE_SIGNED)
    with pytest.raises(AttainmentError, match='impute_scope'):
        _compute(facts, [signed, pending, anchor], impute_scope='MEDIAN_OF_THE_POOL')


def test_g04_negative_actual_zero_counts_zero_on_an_inverse_metric_too():
    '''The [L930] trigger obeys the same reading of ZERO as the missing-row one:
    the attainment is 0. A zero actual here would be target / 0 -> on_zero None
    -> null, i.e. the SKIP observable.'''
    m = _metric('m_cost', 'INVERSE_RATIO', -1, 'MONEY_MINOR', 100000,
                missing_rule='ZERO')
    r = _row(_compute([_fact('S1', 'm_cost', -80000)], [m]), 'S1', 'm_cost')
    assert r.attainment == ZERO and r.reason_code == RC.NEGATIVE_ACTUAL
    assert r.has_target is True and r.capped_flag is False
