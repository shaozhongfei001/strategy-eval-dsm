'''Tests for dsm.entropy -- guard tests T-ENT-01 ~ T-ENT-03 of SDD 2.4.2.

Every hand matrix below is built so that each proportion p_ij is exact at 1e-12,
which makes the closed form of [L542] comparable to the module output at 1e-12.
Reference entropies are computed at 60 decimal digits inside the test, never by
calling the module under test.
'''
import ast
import pathlib
from decimal import Decimal, localcontext

import pytest
from pydantic import ValidationError

from dsm import entropy, numeric
from dsm.numeric import D, ONE, TOL, ZERO, eq_tol
from dsm.reason_codes import RC

SHIFT = Decimal('0.5')
N = 4

# T-ENT-01 matrix: metric_id -> (direction, four per-strategy values).
#   m_reach  p = 0.01 / 0.01 / 0.01 / 0.97      (varies a lot)
#   m_cost   direction -1, p = 0.05 / 0.05 / 0.45 / 0.45
#   m_flat   p = 0.25 four times -> e_j = 1 and d_j = 0 exactly -> INACTIVE
HAND = {
    'm_cost': (-1, (D('24'), D('24'), D('20'), D('20'))),
    'm_flat': (1, (D('7'), D('7'), D('7'), D('7'))),
    'm_reach': (1, (D('100'), D('100'), D('100'), D('148'))),
}
HAND_P = {
    'm_cost': ('0.05', '0.05', '0.45', '0.45'),
    'm_flat': ('0.25', '0.25', '0.25', '0.25'),
    'm_reach': ('0.01', '0.01', '0.01', '0.97'),
}


def _split(spec):
    '''spec -> (values, directions) in the shape entropy_weights() takes.'''
    return ({k: v[1] for k, v in spec.items()}, {k: v[0] for k, v in spec.items()})


def _columns(vec):
    return {c.metric_id: c for c in vec.columns}


def _ref_entropy(props, n):
    '''Closed form of [L542] at 60 digits: -(1 / ln n) * sum_i p ln p.'''
    with localcontext() as ctx:
        ctx.prec = 60
        total = Decimal(0)
        for item in props:
            p = Decimal(item)
            if p != 0:
                total = total + p * p.ln()
        return -total / Decimal(n).ln()


def test_t_ent_01_six_steps_reproduce_the_closed_form():
    values, directions = _split(HAND)
    vec = entropy.entropy_weights(values, directions, SHIFT)
    cols = _columns(vec)

    cost = cols['m_cost']                                    # Step 1 + Step 2
    assert cost.oriented == (D('-24'), D('-24'), D('-20'), D('-20'))
    assert cost.column_min == D('-24')
    assert cost.shifted == (D('0.5'), D('0.5'), D('4.5'), D('4.5'))
    assert cost.column_sum == D('10')                        # Step 3
    assert cost.proportion == (D('0.05'), D('0.05'), D('0.45'), D('0.45'))
    reach = cols['m_reach']
    assert reach.shifted == (D('0.5'), D('0.5'), D('0.5'), D('48.5'))
    assert reach.proportion == (D('0.01'), D('0.01'), D('0.01'), D('0.97'))

    e_ref = {k: _ref_entropy(p, N) for k, p in sorted(HAND_P.items())}
    d_ref = {k: Decimal(1) - v for k, v in sorted(e_ref.items())}
    sum_d_ref = d_ref['m_cost'] + d_ref['m_flat'] + d_ref['m_reach']
    for metric_id in sorted(cols):                           # Steps 4 + 5 + 6
        col = cols[metric_id]
        assert eq_tol(col.e_j, e_ref[metric_id], TOL), metric_id
        assert eq_tol(col.d_j, d_ref[metric_id], TOL), metric_id
        assert eq_tol(col.entropy_w_j, d_ref[metric_id] / sum_d_ref, TOL), metric_id
    assert cols['m_flat'].e_j == ONE                         # exact, no rounding left
    assert cols['m_flat'].d_j == ZERO
    assert vec.entropy_emitted is True
    assert eq_tol(vec.sum_d_j, sum_d_ref, TOL)


def test_step1_unifies_the_direction_of_every_column():
    assert entropy.step1_orient((D('1'), D('-2')), 1) == (D('1'), D('-2'))
    assert entropy.step1_orient((D('1'), D('-2')), -1) == (D('-1'), D('2'))
    with pytest.raises(numeric.NumericError):
        entropy.step1_orient((D('1'),), 0)
    mirror = {'a': (1, (D('0'), D('1'), D('2'), D('3'))),
              'b': (-1, (D('3'), D('2'), D('1'), D('0')))}
    values, directions = _split(mirror)
    cols = _columns(entropy.entropy_weights(values, directions, SHIFT))
    assert cols['a'].shifted == cols['b'].shifted            # a cost is a flipped gain
    assert cols['a'].proportion == cols['b'].proportion
    assert cols['a'].e_j == cols['b'].e_j


def test_t_ent_03_shift_clears_zero_and_negative_values():
    spec = {'m': (1, (D('-3.0'), D('-0.5'), D('-0.5'), D('0')))}
    values, directions = _split(spec)
    col = entropy.entropy_weights(values, directions, SHIFT).columns[0]
    assert col.column_min == D('-3.0')
    assert col.shifted == (D('0.5'), D('3.0'), D('3.0'), D('3.5'))
    assert min(col.shifted) == SHIFT                         # nothing reaches ln() as 0
    assert col.proportion == (D('0.05'), D('0.3'), D('0.3'), D('0.35'))
    assert eq_tol(sum(col.proportion, ZERO), ONE, TOL)
    assert eq_tol(col.e_j, _ref_entropy(('0.05', '0.3', '0.3', '0.35'), N), TOL)
    assert ZERO <= col.e_j <= ONE


def test_step2_refuses_a_non_positive_shift():
    assert entropy.step2_shift((D('1'), D('2')), SHIFT) == ((D('0.5'), D('1.5')), D('1'))
    with pytest.raises(numeric.NumericError):
        entropy.step2_shift((D('1'), D('2')), ZERO)          # would leave a zero to ln()
    with pytest.raises(numeric.NumericError):
        entropy.step2_shift((D('1'), D('2')), Decimal('-0.5'))
    with pytest.raises(numeric.NumericError):
        entropy.step2_shift((), SHIFT)


def test_step4_counts_a_zero_proportion_as_zero():
    props = (D('0.25'), D('0.25'), D('0.5'), ZERO)
    e_j = entropy.step4_entropy(props, N)
    assert e_j == D('0.75')                                  # 1.5 ln2 / 2 ln2 = 3/4
    assert e_j == entropy.step4_entropy(props[:3], N)        # the zero term adds nothing
    assert eq_tol(entropy.step5_difference(e_j), D('0.25'), TOL)


def test_step4_needs_two_strategies_because_ln_n_must_be_positive():
    with pytest.raises(numeric.NumericError):
        entropy.step4_entropy((D('1'),), 1)
    with pytest.raises(numeric.NumericError):
        entropy.entropy_weights({'m': (D('1'),)}, {'m': 1}, SHIFT)


def test_step6_returns_none_when_every_difference_coefficient_is_zero():
    assert entropy.step6_weights({'a': ZERO, 'b': ZERO}) is None
    assert entropy.step6_weights({'a': D('1E-13')}) is None  # below the 1e-12 gate
    assert entropy.step6_weights({'a': D('0.25'), 'b': D('0.75')}) == {
        'a': D('0.25'), 'b': D('0.75')}


def test_t_ent_02_zero_variation_matrix_outputs_no_entropy_weight():
    spec = {'m_a': (1, (D('5'), D('5'), D('5'), D('5'))),
            'm_b': (-1, (D('-2'), D('-2'), D('-2'), D('-2')))}
    values, directions = _split(spec)
    vec = entropy.entropy_weights(values, directions, SHIFT)
    assert vec.entropy_emitted is False                      # no entropy weight at all
    assert vec.sum_d_j == ZERO
    assert vec.inactive_metric_ids == ('m_a', 'm_b')         # every metric INACTIVE
    assert vec.alerts == (RC.INACTIVE_METRIC.value,)         # and warned
    for col in vec.columns:
        assert col.status == 'INACTIVE'
        assert col.reason == RC.INACTIVE_METRIC.value
        assert col.d_j == ZERO
        assert col.entropy_w_j is None


def test_one_zero_variation_metric_is_inactive_while_the_others_stay_ok():
    values, directions = _split(HAND)
    vec = entropy.entropy_weights(values, directions, SHIFT)
    assert vec.entropy_emitted is True
    assert vec.inactive_metric_ids == ('m_flat',)
    assert vec.alerts == (RC.INACTIVE_METRIC.value,)
    cols = _columns(vec)
    assert cols['m_flat'].status == 'INACTIVE'
    assert cols['m_flat'].entropy_w_j == ZERO
    assert cols['m_cost'].status == 'OK'
    assert cols['m_cost'].reason is None
    assert cols['m_reach'].entropy_w_j > cols['m_cost'].entropy_w_j


def test_entropy_weights_of_a_period_sum_to_one():
    spec = {'a': (1, (D('0'), D('1'), D('2'), D('3'))),
            'b': (-1, (D('3'), D('2'), D('1'), D('0')))}
    values, directions = _split(spec)
    vec = entropy.entropy_weights(values, directions, SHIFT)
    total = sum((c.entropy_w_j for c in vec.columns), ZERO)
    assert eq_tol(total, ONE, TOL)                           # sum_j w_j = 1 at 1e-12
    for col in vec.columns:
        assert col.entropy_w_j == D('0.5')                   # mirror columns, equal d_j


def test_entropy_weights_is_a_pure_function():
    values, directions = _split(HAND)
    first = entropy.entropy_weights(values, directions, SHIFT)
    second = entropy.entropy_weights(dict(values), dict(directions), SHIFT)
    assert first.model_dump_json() == second.model_dump_json()
    reversed_input = {k: values[k] for k in reversed(sorted(values))}
    third = entropy.entropy_weights(reversed_input, dict(directions), SHIFT)
    assert third.model_dump_json() == first.model_dump_json()  # input order is irrelevant
    with pytest.raises(ValidationError):                     # a snapshot, not a live object
        first.entropy_emitted = False


def test_entropy_weights_validates_the_matrix_it_is_given():
    with pytest.raises(numeric.NumericError):
        entropy.entropy_weights({'a': (D('1'), D('2')), 'b': (D('1'),)},
                                {'a': 1, 'b': 1}, SHIFT)     # ragged columns
    with pytest.raises(numeric.NumericError):
        entropy.entropy_weights({'a': (D('1'), D('2'))}, {'b': 1}, SHIFT)
    with pytest.raises(numeric.NumericError):
        entropy.entropy_weights({}, {}, SHIFT)
    with pytest.raises(numeric.NumericError):
        entropy.entropy_weights({'a': (1.5, 2.5)}, {'a': 1}, SHIFT)   # raw float refused


def test_module_is_layer_l1_and_never_reads_the_clock_or_randomness():
    source = pathlib.Path(entropy.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or '')
    allowed = {'__future__', 'decimal', 'typing', 'pydantic',
               'dsm', 'dsm.numeric', 'dsm.models', 'dsm.reason_codes'}
    assert imported <= allowed, sorted(imported - allowed)   # INV-1: no L0a / L0b / L2-L7
    names = {n.func.id for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    forbidden = {'time', 'now', 'today', 'utcnow', 'random', 'urandom', 'seed', 'sleep'}
    assert not (forbidden & names), sorted(forbidden & names)  # pure function


def test_weight_vector_carries_no_aggregate_consumable_field():
    fields = entropy.EntropyWeightVector.model_fields
    assert 'weights' not in fields and 'weight_map' not in fields
    for name in sorted(fields):
        text = str(fields[name].annotation)
        for banned in ('dict', 'Mapping', 'Callable'):       # INV-3 type isolation
            assert banned not in text, name + ': ' + text
    assert entropy.EntropyWeightVector.model_config.get('frozen') is True
    assert entropy.EntropyColumn.model_config.get('frozen') is True
    assert entropy.EntropyColumn.model_config.get('extra') == 'forbid'
