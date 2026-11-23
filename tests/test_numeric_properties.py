'''Property tests for dsm.numeric (hypothesis).

Unit tests pin single examples; these pin the invariants that must hold for
EVERY input, which is what makes reproducibility_hash and the audit trail
trustworthy: all public results are quantized to exactly 1e-12, clipping stays
inside its bounds, ranks always sum to n(n+1)/2, and Spearman is bounded by 1.
'''
from decimal import Decimal

import pytest
from hypothesis import given, settings, strategies as st

from dsm.numeric import (
    clip,
    eq_tol,
    from_minor,
    l1_distance,
    mean,
    q12,
    rank_average,
    safe_div,
    spearman,
    to_minor,
    weighted_sum,
)

OPTS = settings(max_examples=60, deadline=None)

dec = st.decimals(min_value=-1000, max_value=1000, places=4, allow_nan=False, allow_infinity=False)
pos = st.decimals(min_value=Decimal('0.0001'), max_value=1000, places=4, allow_nan=False, allow_infinity=False)
minor = st.integers(min_value=-10 ** 12, max_value=10 ** 12)
unique_list = st.lists(dec, min_size=3, max_size=8, unique=True)


def _scale(value: Decimal) -> int:
    return -value.as_tuple().exponent


@OPTS
@given(value=dec)
def test_q12_always_lands_on_exactly_twelve_places_and_is_idempotent(value):
    out = q12(value)
    assert _scale(out) == 12
    assert q12(out) == out


@OPTS
@given(value=dec, lo=dec, hi=dec)
def test_clip_stays_inside_bounds_when_bounds_are_ordered(value, lo, hi):
    if lo > hi:
        lo, hi = hi, lo
    out = clip(value, lo, hi)
    assert lo <= out <= hi
    assert _scale(out) == 12
    assert clip(out, lo, hi) == out


@OPTS
@given(value=dec)
def test_eq_tol_is_reflexive(value):
    assert eq_tol(value, value)


@OPTS
@given(m=minor)
def test_minor_unit_round_trip_is_lossless(m):
    assert to_minor(from_minor(m)) == m


@OPTS
@given(a=dec, b=pos)
def test_safe_div_is_quantized_for_non_zero_denominators(a, b):
    out = safe_div(a, b)
    assert _scale(out) == 12


@OPTS
@given(values=st.lists(dec, min_size=1, max_size=6))
def test_mean_and_weighted_sum_outputs_are_quantized(values):
    assert _scale(mean(values)) == 12
    pairs = [(Decimal('1'), v) for v in values]
    assert _scale(weighted_sum(pairs)) == 12


@OPTS
@given(values=unique_list)
def test_ranks_are_a_permutation_of_average_ranks(values):
    ranks = rank_average(values)
    n = len(values)
    assert sorted(ranks) == list(range(n))
    total = sum(ranks.values(), Decimal('0'))
    assert total == Decimal(n * (n + 1)) / Decimal(2)


@OPTS
@given(values=unique_list)
def test_spearman_with_itself_is_exactly_one(values):
    assert spearman(values, list(values)) == Decimal('1')


@OPTS
@given(values=unique_list)
def test_spearman_with_a_rank_reversal_is_exactly_minus_one(values):
    # reversing the LIST is not reversing the RANKS: sort first, then flip
    asc = sorted(values)
    assert spearman(asc, asc[::-1]) == Decimal('-1')


@OPTS
@given(xs=unique_list, ys=unique_list)
def test_spearman_is_bounded_and_symmetric(xs, ys):
    n = min(len(xs), len(ys))
    if n < 3:
        pytest.skip('needs at least 3 observations')
    xs, ys = xs[:n], ys[:n]
    rho = spearman(xs, ys)
    assert Decimal('-1') <= rho <= Decimal('1')
    assert eq_tol(rho, spearman(ys, xs))
    assert _scale(rho) == 12


@OPTS
@given(w=st.lists(pos, min_size=2, max_size=5))
def test_l1_distance_is_symmetric_and_zero_for_identical_input(w):
    a = {('m%d' % i): v for i, v in enumerate(w)}
    b = dict(reversed(list(a.items())))
    assert l1_distance(a, a) == Decimal('0')
    assert l1_distance(a, b) == Decimal('0')
    shifted = {k: (v + Decimal('0.1')) for k, v in a.items()}
    assert eq_tol(l1_distance(a, shifted), l1_distance(shifted, a))
    assert l1_distance(a, shifted) > Decimal('0')
