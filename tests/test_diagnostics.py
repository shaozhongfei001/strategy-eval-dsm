'''Tests for dsm.diagnostics -- guard tests T-ENT-01 ~ T-ENT-03, G-07, INV-3.

Every expected number below is derived by hand from the constructed matrix and
never read off the module under test (R-14):

  column (3, 1, 0, 0), shift 1 -> p = (1/2, 1/4, 1/8, 1/8)
      e_j = 1.75 ln2 / (2 ln2) = 0.875 exactly, so d_j = 0.125 exactly
  columns (0,1,2,3) and (1,0,3,2) -> Sxy 3, Sxx Syy 5, rho = 3/5 = 0.6
      R inverse diagonal = 1 / (1 - 0.36) = 1.5625 exactly
  columns (0,2,1,3) (0,1,3,2) (0,1,2,3) -> rho = 0.4 / 0.8 / 0.8
      det R = 0.072, minors 0.36 / 0.36 / 0.84 -> VIF 5 / 5 / 35/3
  column (10,10,10,20) -> var 18.75, sd 5 sqrt(3) / 2, CV = 0.3464101615137754
  column (0,0,0,3), gra_rho 1/2 -> xi = (1/3, 1/3, 1/3, 1), gamma = 1/2 exactly

The Gauss-Jordan elimination of dsm.diagnostics quantizes every step to 1e-12
(V-9), so the three-metric VIF is asserted at 1e-9: that is the accumulated
rounding of the elimination, which no threshold comparison of [L691] observes.
'''
import ast
import pathlib
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from dsm import diagnostics, entropy
from dsm.models import EntropyDiagnosticRow, MetricDictRow, MetricFactRow
from dsm.numeric import D, ZERO, eq_tol
from dsm.reason_codes import RC, is_registered

SNAPSHOT = datetime(2026, 1, 31, 0, 0)
AS_OF = date(2026, 1, 31)
PERIOD = '2026-01'
LOOSE = D('1E-9')

# Every value here is a governance number of [L690]-[L694] and comes from the
# configuration, never from the module: the test picks them so that each fixture
# trips exactly the rule it is written for.
CFG = {
    'inactive_threshold': '0.0001',
    'vif_max': '10',
    'corr_max': '0.9',
    'cv_min': '0.05',
    'entropy_shift': '1',
    'corr_method': 'pearson',
    'gra_rho': '0.5',
    'gra_min': '0.4',
    'gra_k_periods': 1,
    'owner_signed_off_statuses': ['SIGNED'],
}

HUB = {'m_a': (0, 2, 1, 3), 'm_b': (0, 1, 3, 2), 'm_h': (0, 1, 2, 3)}


def _cfg(**override):
    block = dict(CFG)
    block.update(override)
    return {'diagnostics': block}


def _params(**override):
    block = dict(CFG)
    block.update(override)
    return diagnostics.DiagnosticsParams(**block)


def _metric(metric_id, direction=1, owner='OWNER_A', signoff='SIGNED', redline=False):
    return MetricDictRow(
        metric_id=metric_id, metric_name=metric_id, dim_code='D1',
        numerator_def='numerator of ' + metric_id, denominator_def=None,
        time_window='M1', dedup_rule='FIRST', missing_rule='SKIP',
        outlier_rule='CLIP_P1_P99', attainment_formula='RATIO_DIRECT',
        direction=direction, unit='COUNT', target_value=10, target_basis='budget',
        is_redline=redline, owner_name=owner, signoff_status=signoff,
        signoff_date=None, dim_signoff_status='SIGNED', dict_version='v1',
        caliber_version='c1')


def _fact(strategy_id, metric_id, value, period=PERIOD, flag='OK'):
    return MetricFactRow(
        strategy_id=strategy_id, version_id='V1', period=period,
        metric_id=metric_id, value_num=value, value_den=None, value=value,
        data_quality_flag=flag, snapshot_time=SNAPSHOT, data_as_of=AS_OF,
        source_table='t3', caliber_version='c1')


def _facts(columns, period=PERIOD, suspect=()):
    '''columns: metric_id -> per-strategy values, strategies s1..sn in order.

    A None entry means the row is absent, because a missing metric is a missing
    row and never an empty column ([L1145]).
    '''
    rows = []
    for metric_id in sorted(columns):
        for position, value in enumerate(columns[metric_id]):
            if value is None:
                continue
            strategy_id = 's' + str(position + 1)
            flag = 'SUSPECT' if (strategy_id, metric_id) in suspect else 'OK'
            rows.append(_fact(strategy_id, metric_id, value, period, flag))
    return tuple(rows)


def _rows(diagnostic):
    return {row.metric_code: row for row in diagnostic.rows}


def test_t_ent_01_online_entropy_reproduces_the_hand_matrix():
    '''T-ENT-01: e_j = 0.875 and d_j = 0.125 by hand, byte-identical to L1.'''
    facts = _facts({'m_gain': (3, 1, 0, 0)})
    diagnostic, report = diagnostics.compute(facts, [_metric('m_gain')], _cfg())
    row = diagnostic.rows[0]
    assert eq_tol(row.e_j, D('0.875'))
    assert eq_tol(row.d_j, D('0.125'))
    shared = entropy.entropy_weights({'m_gain': (3, 1, 0, 0)}, {'m_gain': 1}, D('1'))
    assert row.e_j == shared.columns[0].e_j
    assert row.d_j == shared.columns[0].d_j
    assert diagnostic.period == PERIOD
    assert diagnostic.strategy_ids == ('s1', 's2', 's3', 's4')
    assert diagnostic.entropy_emitted is True
    assert report.metric_ids == ()          # a single metric has no matrix
    assert report.vif_by_metric == {}
    assert row.vif_j is None and row.max_abs_corr is None
    assert row.status == 'OK'


def test_t_ent_01_diagnostics_runs_the_l1_implementation(monkeypatch):
    '''T-ENT-01 / ORCH-03: the six steps are called at L1, not recomputed here.'''
    calls = []
    original = entropy.entropy_weights

    def spy(values, directions, shift):
        calls.append((dict(values), dict(directions), D(shift)))
        return original(values, directions, shift)

    monkeypatch.setattr(entropy, 'entropy_weights', spy)
    facts = _facts({'m_gain': (3, 1, 0, 0), 'm_cost': (5, 4, 3, 2)})
    dictionary = [_metric('m_gain'), _metric('m_cost', direction=-1)]
    diagnostic, _ = diagnostics.compute(facts, dictionary, _cfg(entropy_shift='0.25'))
    assert len(calls) == 1
    values, directions, shift = calls[0]
    assert sorted(values) == ['m_cost', 'm_gain']
    assert directions == {'m_cost': -1, 'm_gain': 1}
    assert shift == D('0.25')
    assert values['m_gain'] == (D('3'), D('1'), D('0'), D('0'))
    assert tuple(row.metric_code for row in diagnostic.rows) == ('m_cost', 'm_gain')


def test_t_ent_02_zero_variation_emits_no_entropy_weight():
    '''T-ENT-02: sum_j d_j = 0 -> every metric INACTIVE, no weight is emitted.'''
    facts = _facts({'m_a': (7, 7, 7, 7), 'm_b': (2, 2, 2, 2)})
    dictionary = [_metric('m_a'), _metric('m_b')]
    diagnostic, _ = diagnostics.compute(facts, dictionary, _cfg())
    assert diagnostic.entropy_emitted is False
    assert diagnostic.inactive_metric_ids == ('m_a', 'm_b')
    assert diagnostic.sum_d_j == ZERO
    assert RC.INACTIVE_METRIC.value in diagnostic.alerts
    for row in diagnostic.rows:
        assert row.status == 'INACTIVE'
        assert row.suggested_action == RC.RETIRE_OR_REDLINE.value
        assert eq_tol(row.e_j, D('1')) and eq_tol(row.d_j, ZERO)


def test_t_ent_03_no_output_carries_an_aggregate_consumable_weight():
    '''T-ENT-03 / INV-3: the diagnostic holds no weight field of any shape.'''
    forbidden = ('weight', 'w_j', 'alpha')
    models = (diagnostics.EntropyDiagnostic, diagnostics.CollinearityReport,
              diagnostics.CollinearityPair, EntropyDiagnosticRow)
    annotations = []
    for model in models:
        for name, field in model.model_fields.items():
            assert not any(token in name.lower() for token in forbidden), \
                model.__name__ + '.' + name
            annotations.append(str(field.annotation))
    assert not any('EntropyWeightVector' in text for text in annotations)
    facts = _facts({'m_gain': (3, 1, 0, 0), 'm_cost': (5, 4, 3, 2)})
    dictionary = [_metric('m_gain'), _metric('m_cost', direction=-1)]
    diagnostic, report = diagnostics.compute(facts, dictionary, _cfg())
    payload = (diagnostic.model_dump_json() + report.model_dump_json()).lower()
    assert 'entropy_w_j' not in payload
    assert 'weight' not in payload


def test_inv3_l5_never_imports_l0a_or_l0b():
    '''INV-3 / INV-1: no weights_combine, weights_calibrate or whatif import.'''
    source = pathlib.Path(diagnostics.__file__).read_text(encoding='utf-8')
    forbidden = {'dsm.weights_combine', 'dsm.weights_calibrate', 'dsm.whatif',
                 'weights_combine', 'weights_calibrate', 'whatif'}
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            imported.add(module)
            imported.update(module + '.' + alias.name for alias in node.names)
    assert not imported & forbidden
    assert 'dsm.entropy' in imported        # ORCH-03: the shared L1 implementation


def test_vif_is_the_inverse_diagonal_of_the_correlation_matrix():
    '''[L1039]: rho = 0.6 by hand, VIF = 1 / (1 - 0.36) = 1.5625 by hand.'''
    facts = _facts({'m_x': (0, 1, 2, 3), 'm_y': (1, 0, 3, 2)})
    dictionary = [_metric('m_x'), _metric('m_y')]
    _, report = diagnostics.compute(facts, dictionary, _cfg())
    assert report.singular is False
    assert report.metric_ids == ('m_x', 'm_y')
    assert eq_tol(report.matrix[0][1], D('0.6'))
    assert eq_tol(report.matrix[1][0], D('0.6'))
    assert eq_tol(report.matrix[0][0], D('1'))
    assert eq_tol(report.vif_by_metric['m_x'], D('1.5625'))
    assert eq_tol(report.vif_by_metric['m_y'], D('1.5625'))
    assert eq_tol(report.max_abs_corr_by_metric['m_x'], D('0.6'))


def test_singular_correlation_matrix_reports_no_vif_at_all():
    '''Hard point 3: a duplicated column is singular -> None, never inf or 0.'''
    facts = _facts({'m_x': (0, 1, 2, 3), 'm_y': (0, 2, 4, 6)})
    dictionary = [_metric('m_x'), _metric('m_y')]
    diagnostic, report = diagnostics.compute(facts, dictionary, _cfg())
    assert report.singular is True
    assert report.vif_by_metric == {}
    assert RC.COLLINEAR.value in report.alerts
    assert RC.COLLINEAR.value in diagnostic.alerts
    rows = _rows(diagnostic)
    for metric_id in ('m_x', 'm_y'):
        assert rows[metric_id].vif_j is None
        assert rows[metric_id].status == 'COLLINEAR'
        assert rows[metric_id].suggested_action == RC.MERGE_OR_DROP.value
        assert eq_tol(rows[metric_id].max_abs_corr, D('1'))


def test_low_cv_triggers_redefine_with_the_hand_cv():
    '''[L693]: CV = 5 sqrt(3) / 2 / 12.5 = 0.3464101615137754 by hand.'''
    facts = _facts({'m_low': (10, 10, 10, 20)})
    diagnostic, _ = diagnostics.compute(facts, [_metric('m_low')], _cfg(cv_min='0.5'))
    row = diagnostic.rows[0]
    assert eq_tol(row.cv_j, D('0.3464101615137754'))
    assert row.status == 'LOW_VARIATION'
    assert row.suggested_action == RC.REDEFINE.value
    assert row.owner == 'OWNER_A'


def test_correlation_above_corr_max_triggers_merge_or_drop():
    '''[L692]: abs(rho) = 0.6 > corr_max names both metrics of the pair.'''
    facts = _facts({'m_x': (0, 1, 2, 3), 'm_y': (1, 0, 3, 2)})
    dictionary = [_metric('m_x'), _metric('m_y')]
    diagnostic, report = diagnostics.compute(facts, dictionary, _cfg(corr_max='0.5'))
    assert len(report.pairs) == 1
    pair = report.pairs[0]
    assert (pair.metric_a, pair.metric_b) == ('m_x', 'm_y')
    assert pair.exceeds_max is True
    assert RC.MERGE_OR_DROP.value in report.alerts
    rows = _rows(diagnostic)
    for metric_id in ('m_x', 'm_y'):
        assert rows[metric_id].status == 'COLLINEAR'
        assert rows[metric_id].suggested_action == RC.MERGE_OR_DROP.value
    calm, calm_report = diagnostics.compute(facts, dictionary, _cfg(corr_max='0.9'))
    assert calm_report.pairs[0].exceeds_max is False
    assert calm_report.alerts == ()
    assert calm.alerts == ()


def test_gra_relatedness_and_the_consecutive_k_rule():
    '''[L694]: gamma = 1/2 by hand against the period best, k periods in a row.'''
    facts = _facts({'m_g': (0, 0, 0, 3)})
    dictionary = [_metric('m_g')]
    one = _cfg(gra_min='0.6')
    diagnostic, _ = diagnostics.compute(facts, dictionary, one)
    assert eq_tol(diagnostic.gamma_by_metric['m_g'], D('0.5'))
    assert diagnostic.method == 'GRA'
    assert diagnostic.gra_doubt_metric_ids == ('m_g',)
    assert RC.CONTENT_VALIDITY_DOUBT.value in diagnostic.alerts
    row = diagnostic.rows[0]
    assert row.status == 'OK'
    assert row.suggested_action == RC.CONTENT_VALIDITY_DOUBT.value
    assert row.flags == ()          # the winning rule is the work order, not a flag
    crowded, _ = diagnostics.compute(facts, dictionary, _cfg(gra_min='0.6', cv_min='9'))
    crowded_row = crowded.rows[0]
    assert crowded_row.suggested_action == RC.REDEFINE.value
    assert crowded_row.status == 'LOW_VARIATION'
    assert RC.CONTENT_VALIDITY_DOUBT.value in crowded_row.flags
    two = _cfg(gra_k_periods=2, gra_min='0.6')
    rich, _ = diagnostics.compute(facts, dictionary, two,
                                  prior_gamma={'m_g': (D('0.9'),)})
    assert rich.gra_doubt_metric_ids == ()
    poor, _ = diagnostics.compute(facts, dictionary, two,
                                  prior_gamma={'m_g': (D('0.55'),)})
    assert poor.gra_doubt_metric_ids == ('m_g',)


def test_work_order_columns_exist_and_are_never_empty():
    '''[L1041]: a diagnosis that lands on nobody is white noise, so both columns
    are projected for every row, and an unsigned owner stays a placeholder.'''
    dictionary = [_metric('m_ok'), _metric('m_pending', signoff='PENDING'),
                  _metric('m_todo', owner='TODO: unsigned')]
    facts = _facts({'m_ok': (3, 1, 0, 0), 'm_pending': (7, 7, 7, 7),
                    'm_todo': (1, 2, 3, 4)})
    diagnostic, _ = diagnostics.compute(facts, dictionary,
                                        _cfg(corr_max='0.95', vif_max='100'))
    assert len(diagnostic.rows) == 3
    assert {'suggested_action', 'owner'} <= set(EntropyDiagnosticRow.model_fields)
    for row in diagnostic.rows:
        assert row.owner.strip()            # [L1041] never empty, placeholder or not
        if row.status != 'OK':
            assert row.suggested_action is not None
            assert is_registered(row.suggested_action)
    rows = _rows(diagnostic)
    assert rows['m_ok'].owner == 'OWNER_A'
    assert rows['m_ok'].status == 'OK'
    assert rows['m_ok'].suggested_action is None   # a healthy metric has no order
    assert rows['m_todo'].suggested_action is None
    assert rows['m_pending'].owner == diagnostics.PLACEHOLDER_OWNER
    assert rows['m_todo'].owner == diagnostics.PLACEHOLDER_OWNER
    assert rows['m_pending'].status == 'INACTIVE'
    assert RC.CONFIG_PLACEHOLDER.value in rows['m_pending'].flags
    assert RC.CONFIG_PLACEHOLDER.value in diagnostic.alerts


def test_g07_the_over_influencing_metric_is_named():
    '''G-07 on the diagnostics side: one metric carries the whole redundancy.

    The LOO half of G-07 (loo_impact plus the stability warning) is the golden
    case of sensitivity; what the bypass contributes is naming the metric every
    exceeding pair goes through and the only one breaching vif_max. Hand values:
    rho(a,b) = 0.4, rho(a,h) = rho(b,h) = 0.8, det R = 0.072, so
    VIF = (0.36, 0.36, 0.84) / 0.072 = (5, 5, 35/3).
    '''
    dictionary = [_metric(metric_id) for metric_id in sorted(HUB)]
    diagnostic, report = diagnostics.compute(_facts(HUB), dictionary,
                                             _cfg(corr_max='0.75', vif_max='10'))
    exceeding = [(pair.metric_a, pair.metric_b) for pair in report.pairs
                 if pair.exceeds_max]
    assert sorted(exceeding) == [('m_a', 'm_h'), ('m_b', 'm_h')]
    assert set(exceeding[0]) & set(exceeding[1]) == {'m_h'}
    assert eq_tol(report.vif_by_metric['m_a'], D('5'), tol=LOOSE)
    assert eq_tol(report.vif_by_metric['m_b'], D('5'), tol=LOOSE)
    assert eq_tol(report.vif_by_metric['m_h'], D('35') / D('3'), tol=LOOSE)
    assert report.vif_by_metric['m_h'] > D('10')
    rows = _rows(diagnostic)
    assert eq_tol(rows['m_h'].vif_j, D('35') / D('3'), tol=LOOSE)
    assert rows['m_h'].suggested_action == RC.MERGE_OR_DROP.value
    breached = [m for m in sorted(report.vif_by_metric)
                if report.vif_by_metric[m] > D('10')]
    assert breached == ['m_h']


def test_incomplete_columns_and_suspect_facts_are_disclosed():
    '''[L1151] / C-06: a hole or a SUSPECT flag removes the column, not the run.'''
    columns = {'m_ok': (1, 2, 3, 4), 'm_gap': (1, 2, 3, None), 'm_sus': (1, 2, 3, 4)}
    facts = _facts(columns, suspect=(('s2', 'm_sus'),))
    dictionary = [_metric(metric_id) for metric_id in sorted(columns)]
    diagnostic, _ = diagnostics.compute(facts, dictionary, _cfg())
    assert diagnostic.excluded_metric_ids == ('m_gap', 'm_sus')
    assert tuple(row.metric_code for row in diagnostic.rows) == ('m_ok',)
    assert RC.MISSING_RATE_WARN.value in diagnostic.alerts
    assert RC.DATA_QUALITY_SUSPECT.value in diagnostic.alerts
    assert diagnostic.rows[0].vif_j is None


def test_redline_metrics_stay_out_of_the_online_entropy():
    '''[L1140]: a redline metric never joins the entropy matrix.'''
    columns = {'m_ok': (3, 1, 0, 0), 'm_red': (9, 8, 7, 6)}
    dictionary = [_metric('m_ok'), _metric('m_red', redline=True)]
    diagnostic, report = diagnostics.compute(_facts(columns), dictionary, _cfg())
    assert diagnostic.redline_metric_ids == ('m_red',)
    assert tuple(row.metric_code for row in diagnostic.rows) == ('m_ok',)
    assert diagnostic.excluded_metric_ids == ()
    assert report.metric_ids == ()


def test_params_from_config_refuses_every_invented_number():
    '''H-5: an absent block, an absent key or an out-of-range value all refuse.'''
    with pytest.raises(diagnostics.DiagnosticsConfigError):
        diagnostics.params_from_config({})
    partial = {key: value for key, value in CFG.items() if key != 'vif_max'}
    with pytest.raises(diagnostics.DiagnosticsConfigError) as info:
        diagnostics.params_from_config({'diagnostics': partial})
    assert 'vif_max' in str(info.value)
    with pytest.raises(diagnostics.DiagnosticsConfigError):
        diagnostics.params_from_config({'diagnostics': dict(
            CFG, owner_signed_off_statuses='SIGNED')})
    with pytest.raises(ValidationError):
        _params(vif_max='0.5')
    with pytest.raises(ValidationError):
        _params(corr_max='1.5')
    with pytest.raises(ValidationError):
        _params(entropy_shift='0')
    with pytest.raises(ValidationError):
        _params(gra_k_periods=0)
    with pytest.raises(ValidationError):
        _params(inactive_threshold='0')
    assert diagnostics.params_from_config(_params()) is not None


def test_compute_refuses_a_period_it_cannot_diagnose():
    '''[L542] divides by ln n, and [L529] pins the online entropy to one period.'''
    dictionary = [_metric('m_a')]
    with pytest.raises(diagnostics.DiagnosticsInputError):
        diagnostics.compute(_facts({'m_a': (3,)}), dictionary, _cfg())
    two = (_facts({'m_a': (3, 1, 0, 0)}, period='2026-01')
           + _facts({'m_a': (4, 2, 1, 0)}, period='2026-02'))
    with pytest.raises(diagnostics.DiagnosticsInputError):
        diagnostics.compute(two, dictionary, _cfg())
    with pytest.raises(diagnostics.DiagnosticsInputError):
        diagnostics.compute(two, dictionary, _cfg(), period='2026-03')
    diagnostic, _ = diagnostics.compute(two, dictionary, _cfg(), period='2026-02')
    assert diagnostic.period == '2026-02'
    with pytest.raises(diagnostics.DiagnosticsInputError):
        diagnostics.compute(_facts({'m_a': (3, 1, 0, 0)}),
                            [_metric('m_a'), _metric('m_a')], _cfg())


def test_output_is_sorted_and_byte_reproducible():
    '''H-8: no clock, no randomness, the same input gives the same bytes.'''
    dictionary = [_metric(metric_id) for metric_id in sorted(HUB)]
    facts = _facts(HUB)
    first, first_report = diagnostics.compute(facts, dictionary, _cfg())
    second, second_report = diagnostics.compute(facts, dictionary, _cfg())
    assert first.model_dump_json() == second.model_dump_json()
    assert first_report.model_dump_json() == second_report.model_dump_json()
    codes = tuple(row.metric_code for row in first.rows)
    assert codes == tuple(sorted(codes)) == ('m_a', 'm_b', 'm_h')
    assert first.strategy_count == 4
