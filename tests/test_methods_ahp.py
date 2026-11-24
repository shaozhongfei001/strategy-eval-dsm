'''Guard tests T-AHP-01 .. T-AHP-06 for dsm/weights_ahp.py (SDD 2.4.1 / digest
M06-ahp, module table M42 row weights_ahp.py). Only the six guard numbers are
tested here (R-9).

Every golden number below is hand derived (R-14), never read back from the
implementation:

  * 3x3 consistent matrix [[1,2,4],[1/2,1,2],[1/4,1/2,1]]: the row products are
    8, 1 and 1/8, so the geometric means are 2, 1, 1/2 and the normalised
    weights are 4/7, 2/7, 1/7; a consistent matrix has lambda_max = n = 3,
    CI = 0 and CR = 0.
  * for a 3x3 reciprocal matrix with x = a12, y = a13, z = a23 the
    characteristic polynomial is det(A - lam I) = t^3 - 3t + u + 1/u with
    t = 1 - lam and u = x z / y, hence lambda_max = 1 + s where s is the root
    above 1 of s^3 - 3s = u + 1/u.
      x=2, y=8, z=2  -> u = 1/2, s ~ 2.053607, lambda_max ~ 3.053607,
                        CI ~ 0.0268035, CR = CI/0.58 ~ 0.046213 (< 0.1)
      x=8, y=1, z=8  -> u = 64,  s = 4.25 exactly, lambda_max = 5.25,
                        CI = 1.125, CR = 1.125/0.58 = 1.93965517241379...
  * the 4x4 cyclic matrix below has every row sum equal to 10.125 and every row
    product equal to 1, therefore lambda_max = 10.125 exactly with the uniform
    Perron vector 1/4, CI = (10.125 - 4)/3 = 2.041666666666..., and
    CR = CI/0.90 = 2.268518518518...; both weight methods return the uniform
    vector, so the pair deviations are |ln a_ij|, i.e. four pairs at ln 8 =
    2.0794415416798... and two pairs at 0.
  * a 2x2 reciprocal matrix has lambda_max = 2 = n, CI = 0 and RI(2) = 0, so
    CR is 0/0 and must land on the declared on_zero value 0, never raise.
  * for n = 3 the geometric-mean vector (LLSM) and the principal eigenvector
    (AIP) coincide identically, so no 3x3 matrix can trip the 1e-6 cross check;
    MILD_4 below is the smallest level that separates them. It is the consistent
    8/4/2/1 matrix with a14 pulled from 8 down to 4: three power iterations by
    hand give lambda_max ~ 4.0605, CI ~ 0.0202, CR ~ 0.0224 (< 0.1, accepted)
    and the geometric vector (0.483399, 0.287432, 0.143716, 0.085453) against
    the eigenvector (0.485687, 0.285333, 0.142667, 0.086308), i.e. a gap of
    about 2.3e-3, far above 1e-6.
'''
from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given, settings, strategies as st

from dsm import numeric
from dsm.numeric import D, eq_tol, from_float
from dsm.weights_ahp import (
    AhpError,
    AhpResult,
    ConsistencyFailedError,
    FrozenStatusError,
    MatrixNotReciprocalError,
    check_consistency,
    elicit,
    elicit_hierarchy,
    freeze,
    random_index,
)

GAP_TOL = D('0.000001')  # [L515]


def mat(spec):
    '''One pairwise comparison matrix: {row: {col: literal}} -> Decimal cells.'''
    return {i: {j: numeric.D(v) for j, v in row.items()} for i, row in spec.items()}


CONSISTENT = mat({
    'A': {'A': 1, 'B': 2, 'C': 4},
    'B': {'A': '0.5', 'B': 1, 'C': 2},
    'C': {'A': '0.25', 'B': '0.5', 'C': 1},
})
# two experts whose geometric aggregate is exactly CONSISTENT:
#   a12 = (1*4)^(1/2) = 2, a13 = (2*8)^(1/2) = 4, a23 = (2*2)^(1/2) = 2
EXPERT_1 = mat({
    'A': {'A': 1, 'B': 1, 'C': 2},
    'B': {'A': 1, 'B': 1, 'C': 2},
    'C': {'A': '0.5', 'B': '0.5', 'C': 1},
})
EXPERT_2 = mat({
    'A': {'A': 1, 'B': 4, 'C': 8},
    'B': {'A': '0.25', 'B': 1, 'C': 2},
    'C': {'A': '0.125', 'B': '0.5', 'C': 1},
})
MILD = mat({      # CR ~ 0.046213 (accepted); n = 3 -> both methods identical
    'A': {'A': 1, 'B': 2, 'C': 8},
    'B': {'A': '0.5', 'B': 1, 'C': 2},
    'C': {'A': '0.125', 'B': '0.5', 'C': 1},
})
MILD_4 = mat({    # consistent 8/4/2/1 with a14 pulled from 8 to 4 (CR ~ 0.022)
    'A': {'A': 1, 'B': 2, 'C': 4, 'D': 4},
    'B': {'A': '0.5', 'B': 1, 'C': 2, 'D': 4},
    'C': {'A': '0.25', 'B': '0.5', 'C': 1, 'D': 2},
    'D': {'A': '0.25', 'B': '0.25', 'C': '0.5', 'D': 1},
})
GROSS_3 = mat({   # lambda_max = 5.25, CI = 1.125, CR ~ 1.9397 (rejected)
    'A': {'A': 1, 'B': 8, 'C': 1},
    'B': {'A': '0.125', 'B': 1, 'C': 8},
    'C': {'A': 1, 'B': '0.125', 'C': 1},
})
GROSS_4 = mat({   # lambda_max = 10.125, CI = 2.041666666667, CR ~ 2.2685
    'A': {'A': 1, 'B': 8, 'C': 1, 'D': '0.125'},
    'B': {'A': '0.125', 'B': 1, 'C': 8, 'D': 1},
    'C': {'A': 1, 'B': '0.125', 'C': 1, 'D': 8},
    'D': {'A': 8, 'B': 1, 'C': '0.125', 'D': 1},
})


# ------------------------------------------------------------------ T-AHP-01
def test_t_ahp_01_reciprocity_violation_is_refused():
    broken = mat({'A': {'A': 1, 'B': 2}, 'B': {'A': 3, 'B': 1}})
    with pytest.raises(MatrixNotReciprocalError):
        elicit({'e1': broken})


def test_t_ahp_01_non_positive_cell_is_refused():
    for bad in ('0', '-2'):
        broken = mat({'A': {'A': 1, 'B': bad}, 'B': {'A': '0.5', 'B': 1}})
        with pytest.raises(MatrixNotReciprocalError):
            check_consistency(broken)


def test_t_ahp_01_ragged_matrix_is_refused():
    ragged = {'A': {'A': D('1'), 'B': D('2')}, 'B': {'B': D('1')}}
    with pytest.raises(MatrixNotReciprocalError):
        check_consistency(ragged)


def test_t_ahp_01_experts_must_share_one_item_key_set():
    with pytest.raises(AhpError):
        elicit({'e1': CONSISTENT, 'e2': mat({'A': {'A': 1}})})


# ------------------------------------------------------------------ T-AHP-02
def test_t_ahp_02_two_expert_geometric_aggregation_is_hand_exact():
    res = elicit({'e1': EXPERT_1, 'e2': EXPERT_2},
                 interview_dates=[date(2026, 1, 5), date(2026, 1, 6)])
    agg = res.aggregated_matrix
    assert res.expert_count == 2
    assert res.expert_ids == ('e1', 'e2')
    assert eq_tol(agg['A']['B'], D('2'))       # (1 * 4) ^ (1/2)
    assert eq_tol(agg['A']['C'], D('4'))       # (2 * 8) ^ (1/2)
    assert eq_tol(agg['B']['C'], D('2'))       # (2 * 2) ^ (1/2)
    # Step 3: the aggregate of reciprocal matrices is reciprocal again
    for i in res.item_keys:
        for j in res.item_keys:
            assert eq_tol(agg[i][j] * agg[j][i], D('1'))
    assert eq_tol(res.weights_geometric['A'], D('4') / D('7'))
    assert eq_tol(res.weights_geometric['B'], D('2') / D('7'))
    assert eq_tol(res.weights_geometric['C'], D('1') / D('7'))


# ------------------------------------------------------------------ T-AHP-03
def test_t_ahp_03_geometric_weights_are_four_sevenths_and_sum_to_one():
    res = elicit({'e1': CONSISTENT})
    total = sum(res.weights_geometric[i] for i in res.item_keys)
    assert eq_tol(total, D('1'))
    assert eq_tol(res.weights_geometric['A'], D('4') / D('7'))
    assert eq_tol(res.weights_geometric['B'], D('2') / D('7'))
    assert eq_tol(res.weights_geometric['C'], D('1') / D('7'))
    assert res.status == 'DRAFT'


def test_t_ahp_03_hierarchy_yields_dimension_and_metric_layer():
    hier = elicit_hierarchy({'e1': CONSISTENT},
                            {'A': {'e1': CONSISTENT}, 'B': {'e1': MILD_4}},
                            interview_dates=[date(2026, 3, 1)])
    assert hier.status == 'DRAFT'
    assert sorted(hier.metrics_by_dim) == ['A', 'B']
    assert eq_tol(hier.dimension.weights_geometric['A'], D('4') / D('7'))
    payload = hier.metric_segment_payload('A')
    assert payload['expert_count'] == 1
    assert eq_tol(payload['cr'], D('0'))


# ------------------------------------------------------------------ T-AHP-04
def test_t_ahp_04_consistent_matrix_cross_validates_within_one_millionth():
    res = elicit({'e1': CONSISTENT})
    assert res.max_method_gap <= GAP_TOL
    assert 'METHOD_MISMATCH' not in res.findings
    assert eq_tol(res.lambda_max, D('3'))
    assert eq_tol(res.ci, D('0'))
    assert eq_tol(res.cr, D('0'))
    assert eq_tol(res.weights_eigenvector['A'], D('4') / D('7'))


def test_t_ahp_04_mild_three_by_three_still_cross_validates():
    res = elicit({'e1': MILD})
    assert res.max_method_gap == D('0')     # n = 3: LLSM and AIP coincide
    assert 'METHOD_MISMATCH' not in res.findings
    assert D('3.05') < res.lambda_max < D('3.06')      # hand: 3.053607
    assert D('0.04') < res.cr < D('0.05')              # hand: 0.046213
    total = sum(res.weights_geometric[i] for i in res.item_keys)
    assert abs(total - D('1')) <= D('1.5E-12')         # three q12 roundings


def test_t_ahp_04_four_by_four_records_method_mismatch():
    res = elicit({'e1': MILD_4})
    assert res.max_method_gap > GAP_TOL
    assert 'METHOD_MISMATCH' in res.findings
    assert res.lambda_max > D('4')          # inconsistent, so above n
    assert res.cr < D('0.05')               # hand: 0.0224 -> still accepted
    assert res.status == 'DRAFT'


@settings(max_examples=25, deadline=None)
@given(st.lists(st.floats(min_value=0.2, max_value=9.0, allow_nan=False,
                          allow_infinity=False), min_size=3, max_size=4))
def test_t_ahp_04_matrix_built_from_a_weight_vector_is_consistent(raw):
    vals = [from_float(v) for v in raw]
    keys = ['i0', 'i1', 'i2', 'i3'][:len(vals)]
    spec = {}
    for a, i in enumerate(keys):
        spec[i] = {keys[b]: numeric.q12(vals[a]) / numeric.q12(vals[b])
                   for b in range(len(keys))}
    res = elicit({'e1': mat(spec)})
    assert res.max_method_gap <= GAP_TOL
    assert abs(sum(res.weights_geometric[i] for i in keys) - D('1')) <= D('2E-12')
    assert abs(res.lambda_max - D(len(keys))) <= D('0.000001')
    assert res.cr < D('0.01')
    assert res.status == 'DRAFT'


# ------------------------------------------------------------------ T-AHP-05
def test_t_ahp_05_cr_below_threshold_is_accepted():
    rep = check_consistency(MILD)
    assert rep.passed is True
    assert eq_tol(rep.ri, D('0.58'))
    assert eq_tol(rep.ci, (rep.lambda_max - D('3')) / D('2'))
    assert D('0.04') < rep.cr < D('0.05')              # hand: 0.046213
    assert rep.worst_pairs[0].deviation >= rep.worst_pairs[-1].deviation


def test_t_ahp_05_cr_at_or_above_threshold_rejects_the_draft():
    with pytest.raises(ConsistencyFailedError) as excinfo:
        elicit({'e1': GROSS_3})
    rep = excinfo.value.report
    assert ConsistencyFailedError.exit_code == 6
    assert rep.passed is False
    assert eq_tol(rep.lambda_max, D('5.25'))
    assert eq_tol(rep.ci, D('1.125'))
    assert eq_tol(rep.cr, D('1.939655172414'))
    assert len(rep.worst_pairs) == 3                   # n = 3 has 3 pairs only


def test_t_ahp_05_worst_five_pairs_are_ordered_by_deviation():
    with pytest.raises(ConsistencyFailedError) as excinfo:
        elicit({'e1': GROSS_4})
    rep = excinfo.value.report
    assert eq_tol(rep.lambda_max, D('10.125'))
    assert eq_tol(rep.ci, D('2.041666666667'))
    assert eq_tol(rep.cr, D('2.268518518519'))
    assert [(p.item_i, p.item_j) for p in rep.worst_pairs] == [
        ('A', 'B'), ('A', 'D'), ('B', 'C'), ('C', 'D'), ('A', 'C')]
    devs = [p.deviation for p in rep.worst_pairs]
    assert devs == sorted(devs, reverse=True)
    assert D('2.07') < devs[0] < D('2.09')             # ln 8 = 2.0794415...
    assert eq_tol(devs[0], devs[3])
    assert eq_tol(devs[4], D('0'))
    assert eq_tol(rep.worst_pairs[0].a_ij, D('8'))


def test_t_ahp_05_random_index_table_and_two_by_two_boundary():
    assert eq_tol(random_index(1), D('0'))
    assert eq_tol(random_index(2), D('0'))
    assert eq_tol(random_index(3), D('0.58'))
    assert eq_tol(random_index(4), D('0.90'))
    assert eq_tol(random_index(9), D('1.45'))
    assert eq_tol(random_index(10), D('1.49'))
    with pytest.raises(AhpError):
        random_index(11)
    rep = check_consistency(mat({'A': {'A': 1, 'B': 4}, 'B': {'A': '0.25', 'B': 1}}))
    assert eq_tol(rep.lambda_max, D('2'))
    assert eq_tol(rep.ci, D('0'))
    assert eq_tol(rep.cr, D('0'))                      # 0/0 -> declared 0
    assert rep.passed is True
    assert eq_tol(rep.weights_geometric['A'], D('0.8'))
    assert eq_tol(rep.weights_geometric['B'], D('0.2'))


# ------------------------------------------------------------------ T-AHP-06
def test_t_ahp_06_elicit_only_ever_produces_draft():
    res = elicit({'e1': CONSISTENT})
    assert res.status == 'DRAFT'
    payload = res.segment_payload()
    assert sorted(payload) == sorted([
        'comparison_matrices', 'lambda_max', 'ci', 'ri', 'cr', 'expert_count',
        'interview_dates', 'weights_geometric', 'weights_eigenvector',
        'max_method_gap'])
    assert payload['interview_dates'] == []


def test_t_ahp_06_writing_frozen_raises():
    res = elicit({'e1': CONSISTENT}, interview_dates=[date(2026, 2, 1)])
    with pytest.raises(FrozenStatusError):
        freeze(res)
    payload = res.model_dump()
    payload['status'] = 'FROZEN'
    with pytest.raises(FrozenStatusError):
        AhpResult(**payload)
    assert res.segment_payload()['interview_dates'] == [date(2026, 2, 1)]
