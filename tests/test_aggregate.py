'''tests/test_aggregate.py -- B2 guards G-01 / T-CMB-06 / INV-3 (digest M03).

Inputs are built directly with the pydantic contract models (R-2, field
names verbatim from dsm/models.py); no attainment/normalize module import.
All golden expectations below come from hand calculation only (R-14):
  dim D1 abs = 0.5*0.8 + 0.5*0.6 = 0.7   dim D2 abs = 0.4*1.0 + 0.6*0.5 = 0.7
  composite abs = 0.6*0.7 + 0.4*0.7 = 0.7
  dim D1 rel = 0.5*0.9 + 0.5*0.7 = 0.8   dim D2 rel = 0.4*0.5 + 0.6*0.3 = 0.38
  composite rel = 0.6*0.8 + 0.4*0.38 = 0.632
'''
import ast
import builtins
import pathlib
import sys
from datetime import date
from decimal import Decimal

import pytest

from dsm import aggregate, numeric
from dsm.models import (AttainmentFrame, AttainmentRow, NormalizedFrame,
                        NormalizedRow, PoolKey, WeightVersionDoc)

ABS_METRICS = ('m1', 'm2', 'm3', 'm4')
DEFAULT_ABS = {'m1': '0.8', 'm2': '0.6', 'm3': '1.0', 'm4': '0.5'}
DEFAULT_REL = {'m1': '0.9', 'm2': '0.7', 'm3': '0.5', 'm4': '0.3'}
LEVEL1 = {'D1': '0.6', 'D2': '0.4'}
LEVEL2 = {'D1': {'m1': '0.5', 'm2': '0.5'}, 'D2': {'m3': '0.4', 'm4': '0.6'}}


def _weights(level1=None, level2=None, status='FROZEN'):
    return WeightVersionDoc(
        weight_version_id='WV-2026-01', status=status,
        effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
        level1_weights=LEVEL1 if level1 is None else level1,
        level2_weights=LEVEL2 if level2 is None else level2,
        approved_by='owner', approved_date=date(2026, 1, 1))


def _abs_row(sid, metric, value):
    return AttainmentRow(strategy_id=sid, version_id='v1', period='2026P1',
                         metric_id=metric, attainment=value, direction=1,
                         has_target=value is not None, capped_flag=False)


def _rel_row(sid, metric, value):
    return NormalizedRow(strategy_id=sid, version_id='v1', period='2026P1',
                         metric_id=metric,
                         pool_key=PoolKey(biz_domain='pay', evidence_class='A'),
                         norm_value=value, method='min_max', anchor_used=False)


def _attainment(rows):
    return AttainmentFrame(rows=tuple(rows), attainment_coverage={})


def _normalized(rows):
    return NormalizedFrame(rows=tuple(rows))


def _abs_rows(sid='s1', values=None, missing=()):
    values = DEFAULT_ABS if values is None else values
    return [_abs_row(sid, m, values.get(m)) for m in ABS_METRICS if m not in missing]


def _rel_rows(sid='s1', values=None, missing=()):
    values = DEFAULT_REL if values is None else values
    return [_rel_row(sid, m, values.get(m)) for m in ABS_METRICS if m not in missing]


def _compose(att, norm, weights=None, config=None):
    return aggregate.compose(att, norm, _weights() if weights is None else weights,
                             config)


def test_g01_linear_golden_absolute_and_relative_tracks():
    frame = _compose(_attainment(_abs_rows()), _normalized(_rel_rows()))
    row = frame.rows[0]
    assert numeric.eq_tol(row.composite_absolute, Decimal('0.7'))
    assert numeric.eq_tol(row.composite_relative, Decimal('0.632'))
    assert row.dim_absolute['D1'] == Decimal('0.7')
    assert row.dim_absolute['D2'] == Decimal('0.7')
    assert row.dim_relative['D1'] == Decimal('0.8')
    assert row.dim_relative['D2'] == Decimal('0.38')
    assert row.operator == 'LINEAR'


def test_g01_relative_track_change_leaves_absolute_untouched():
    att = _attainment(_abs_rows())
    base = _compose(att, _normalized(_rel_rows())).rows[0]
    moved = _compose(att, _normalized(_rel_rows(values={
        'm1': '0.9', 'm2': '0.7', 'm3': '0.5', 'm4': '0.9'}))).rows[0]
    assert base.composite_absolute == moved.composite_absolute
    assert not numeric.eq_tol(base.composite_relative, moved.composite_relative)


def test_g01_absolute_track_change_leaves_relative_untouched():
    norm = _normalized(_rel_rows())
    base = _compose(_attainment(_abs_rows()), norm).rows[0]
    moved = _compose(_attainment(_abs_rows(values={
        'm1': '0.2', 'm2': '0.6', 'm3': '1.0', 'm4': '0.5'})), norm).rows[0]
    assert base.composite_relative == moved.composite_relative
    assert not numeric.eq_tol(base.composite_absolute, moved.composite_absolute)


def test_g01_geometric_golden():
    frame = _compose(_attainment(_abs_rows()), _normalized(_rel_rows()),
                     config={'score_operator': 'GEOMETRIC'})
    assert frame.rows[0].operator == 'GEOMETRIC'
    assert numeric.eq_tol(frame.rows[0].composite_absolute, Decimal('0.7'))


def test_g01_geometric_nonpositive_dim_uses_eps():
    rel = _rel_rows(values={'m1': '0', 'm2': '-0.4', 'm3': '0.6', 'm4': '0.2'})
    frame = _compose(_attainment(_abs_rows()), _normalized(rel),
                     config={'score_operator': 'GEOMETRIC'})
    row = frame.rows[0]
    assert row.dim_relative['D1'] == Decimal('-0.2')
    assert Decimal('0') < row.composite_relative < Decimal('0.000001')


def test_g01_non_compensatory_min_dim():
    abs_rows = _abs_rows(values={'m1': '0.8', 'm2': '0.6', 'm3': '1.0', 'm4': '0.1'})
    frame = _compose(_attainment(abs_rows), _normalized(_rel_rows()),
                     config={'score_operator': 'NON_COMPENSATORY'})
    row = frame.rows[0]
    assert numeric.eq_tol(row.dim_absolute['D2'], Decimal('0.46'))
    assert numeric.eq_tol(row.composite_absolute, Decimal('0.46'))
    assert numeric.eq_tol(row.composite_relative, Decimal('0.38'))


def test_g01_dropped_metric_renormalizes_within_dim_and_coverage():
    att = _attainment(_abs_rows('s2', values={'m1': '0.8', 'm2': None, 'm3': '1.0'},
                                missing=('m4',)))
    frame = _compose(att, _normalized(_rel_rows('s2')))
    row = frame.rows[0]
    assert numeric.eq_tol(row.dim_absolute['D1'], Decimal('0.8'))
    assert numeric.eq_tol(row.dim_absolute['D2'], Decimal('1'))
    assert numeric.eq_tol(row.composite_absolute, Decimal('0.88'))
    assert numeric.eq_tol(row.coverage, Decimal('0.5'))


def test_g01_cleared_dim_zeroes_and_renormalizes_level1():
    att = _attainment(_abs_rows('s3', values={'m1': None, 'm2': None,
                                              'm3': '1.0', 'm4': '0.5'}))
    frame = _compose(att, _normalized(_rel_rows('s3')))
    row = frame.rows[0]
    assert 'D1' not in row.dim_absolute
    assert numeric.eq_tol(row.dim_absolute['D2'], Decimal('0.7'))
    assert numeric.eq_tol(row.composite_absolute, Decimal('0.7'))


def test_g01_all_metrics_dropped_composite_absolute_is_none():
    att = _attainment(_abs_rows('s4', values={m: None for m in ABS_METRICS}))
    frame = _compose(att, _normalized(_rel_rows('s4')))
    row = frame.rows[0]
    assert row.composite_absolute is None
    assert row.dim_absolute == {}
    assert numeric.eq_tol(row.composite_relative, Decimal('0.632'))


def test_g01_relative_absent_metric_renormalizes_relative_track():
    norm = _normalized(_rel_rows('s5', missing=('m4',)))
    frame = _compose(_attainment([]), norm)
    row = frame.rows[0]
    assert numeric.eq_tol(row.dim_relative['D2'], Decimal('0.5'))
    assert numeric.eq_tol(row.composite_relative, Decimal('0.68'))
    assert row.composite_absolute is None
    assert numeric.eq_tol(row.coverage, Decimal('0'))


def test_g01_level1_weight_sum_violation_raises():
    with pytest.raises(ValueError):
        _compose(_attainment(_abs_rows()), _normalized(_rel_rows()),
                 weights=_weights(level1={'D1': '0.7', 'D2': '0.4'}))


def test_g01_level2_weight_sum_violation_raises():
    with pytest.raises(ValueError):
        _compose(_attainment(_abs_rows()), _normalized(_rel_rows()),
                 weights=_weights(level2={'D1': {'m1': '0.5', 'm2': '0.4'},
                                          'D2': LEVEL2['D2']}))


def test_g01_metric_in_two_dimensions_raises():
    with pytest.raises(ValueError):
        _compose(_attainment(_abs_rows()), _normalized(_rel_rows()),
                 weights=_weights(level2={'D1': {'m1': '0.5', 'm2': '0.5'},
                                          'D2': {'m1': '0.4', 'm4': '0.6'}}))


def test_g01_non_frozen_weights_rejected():
    with pytest.raises(ValueError):
        _compose(_attainment(_abs_rows()), _normalized(_rel_rows()),
                 weights=_weights(status='DRAFT'))


def test_g01_one_row_per_strategy_version_period():
    att = _attainment(_abs_rows('s1') + _abs_rows('s2', values={
        'm1': '0.8', 'm2': None, 'm3': '1.0'}, missing=('m4',)))
    norm = _normalized(_rel_rows('s1'))
    frame = _compose(att, norm)
    keys = [(r.strategy_id, r.version_id, r.period) for r in frame.rows]
    assert keys == [('s1', 'v1', '2026P1'), ('s2', 'v1', '2026P1')]
    assert numeric.eq_tol(frame.rows[0].composite_absolute, Decimal('0.7'))
    assert frame.rows[1].composite_relative is None


def test_t_cmb_06_no_import_or_attribute_of_forbidden_neighbours():
    src = pathlib.Path(aggregate.__file__).read_text(encoding='utf-8')
    tree = ast.parse(src)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or '')
    assert not any('diagnostics' in m or 'weights_combine' in m for m in imported)
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            assert node.attr not in ('diagnostics', 'weights_combine')


def test_t_cmb_06_compose_works_when_forbidden_modules_unavailable():
    blocked = ('dsm.diagnostics', 'dsm.weights_combine')
    real_import = builtins.__import__

    def guard(name, *args, **kwargs):
        if name in blocked:
            raise AssertionError('aggregate reached for ' + name)
        return real_import(name, *args, **kwargs)

    saved = {name: sys.modules.pop(name, None) for name in blocked}
    builtins.__import__ = guard
    try:
        frame = _compose(_attainment(_abs_rows()), _normalized(_rel_rows()))
    finally:
        builtins.__import__ = real_import
        for name, module in saved.items():
            if module is not None:
                sys.modules[name] = module
    assert numeric.eq_tol(frame.rows[0].composite_absolute, Decimal('0.7'))


def test_inv3_weight_version_on_every_row_and_weights_not_mutated():
    att = _attainment(_abs_rows('s1') + _abs_rows('s2'))
    norm = _normalized(_rel_rows('s1') + _rel_rows('s2'))
    weights = _weights()
    snapshot = (dict(weights.level1_weights),
                {d: dict(w) for d, w in weights.level2_weights.items()})
    frame = _compose(att, norm, weights=weights)
    assert len(frame.rows) == 2
    assert all(r.weight_version_id == 'WV-2026-01' for r in frame.rows)
    assert weights.level1_weights == snapshot[0]
    assert weights.level2_weights == snapshot[1]
