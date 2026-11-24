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
    AttainmentParams)
from dsm.config import AppConfig
from dsm.models import MetricDictRow, MetricFactRow
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
