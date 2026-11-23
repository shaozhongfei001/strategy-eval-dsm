'''Tests for dsm.numeric -- the numeric contract of design doc 3.3.1 / 3.13 / R6.

Everything asserted here is a contract the other 22 modules rely on:
money and counts compare EXACTLY, ratios compare within 1e-12, no division is
ever silent, and a raw float can never enter the numeric layer unannounced.
'''
from decimal import Decimal

import pytest

from dsm.numeric import (
    TOL,
    D,
    DivisionUndefinedError,
    FloatNotAllowedError,
    NonIntegerAmountError,
    NumericError,
    as_minor,
    clip,
    eq_exact,
    eq_tol,
    from_float,
    from_minor,
    l1_distance,
    ln,
    mean,
    median,
    q12,
    rank_average,
    safe_div,
    spearman,
    sqrt,
    to_minor,
    weighted_sum,
)


class TestDecimalEntry:
    def test_accepts_decimal_int_and_str(self):
        assert D(Decimal('1.5')) == Decimal('1.5')
        assert D(3) == Decimal(3)
        assert D(' 2.25 ') == Decimal('2.25')

    def test_rejects_float_so_no_binary_error_leaks_in(self):
        with pytest.raises(FloatNotAllowedError):
            D(1.5)

    def test_rejects_bool(self):
        with pytest.raises(NumericError):
            D(True)
        with pytest.raises(NumericError):
            D(False)

    def test_rejects_junk_strings(self):
        with pytest.raises(NumericError):
            D('')
        with pytest.raises(NumericError):
            D('1,2')
        with pytest.raises(NumericError):
            D('nan-ish')

    def test_rejects_unknown_types(self):
        with pytest.raises(NumericError):
            D(object())

    def test_from_float_is_the_audited_escape_hatch_and_quantizes(self):
        assert from_float(0.1) == Decimal('0.1')
        assert from_float(1 / 3) == Decimal('0.333333333333')
        assert from_float(2 / 3) == Decimal('0.666666666667')


class TestQuantization:
    def test_tol_is_one_e_minus_twelve(self):
        assert TOL == Decimal('1E-12')

    def test_q12_rounds_half_up(self):
        assert q12('0.0000000000005') == Decimal('0.000000000001')
        assert q12('0.0000000000004') == Decimal('0')
        assert q12('-0.0000000000005') == Decimal('-0.000000000001')

    def test_q12_is_idempotent_so_reproducibility_hash_is_stable(self):
        once = q12('1.234567890123456')
        assert once == Decimal('1.234567890123')
        assert q12(once) == once
        assert str(q12(once)) == str(once)


class TestMoney:
    def test_to_minor_is_exact(self):
        assert to_minor('12.34') == 1234
        assert to_minor(7) == 700
        assert to_minor('-0.05') == -5
        assert to_minor('0') == 0

    def test_to_minor_rejects_sub_minor_precision(self):
        with pytest.raises(NonIntegerAmountError):
            to_minor('12.345')

    def test_to_minor_honours_minor_per_unit(self):
        assert to_minor('1.5', minor_per_unit=1000) == 1500

    def test_as_minor_validates_integers_only(self):
        assert as_minor(1234) == 1234
        assert as_minor('1234') == 1234
        with pytest.raises(NonIntegerAmountError):
            as_minor('12.5')

    def test_from_minor_is_display_only_and_round_trips(self):
        assert from_minor(1234) == Decimal('12.34')
        assert from_minor(-5) == Decimal('-0.05')
        assert from_minor(1500, minor_per_unit=1000) == Decimal('1.5')
        assert to_minor(from_minor(1234)) == 1234
        with pytest.raises(NonIntegerAmountError):
            from_minor('1.5')

    def test_money_compares_exactly_never_with_tolerance(self):
        assert eq_exact(1234, 1234)
        assert not eq_exact(1234, 1235)
        assert not eq_exact(Decimal('0.01'), Decimal('0.00'))


class TestSafeDiv:
    def test_plain_division_is_quantized(self):
        assert safe_div(1, 3) == Decimal('0.333333333333')
        assert safe_div('10', '4') == Decimal('2.5')
        assert safe_div('-1', 4) == Decimal('-0.25')

    def test_zero_denominator_without_policy_raises(self):
        with pytest.raises(DivisionUndefinedError):
            safe_div(1, 0)

    def test_zero_denominator_with_numeric_policy(self):
        assert safe_div(1, 0, on_zero=Decimal('0')) == Decimal('0')
        assert safe_div(1, 0, on_zero='1') == Decimal('1')

    def test_zero_denominator_with_none_policy_returns_none_not_zero(self):
        assert safe_div(1, 0, on_zero=None) is None

    def test_near_zero_denominator_is_treated_as_zero_by_zero_tol(self):
        with pytest.raises(DivisionUndefinedError):
            safe_div(1, '1E-13')
        assert safe_div(1, '1E-6') == Decimal('1000000')

    def test_zero_numerator_is_fine(self):
        assert safe_div(0, 5) == Decimal('0')


class TestEquality:
    def test_eq_tol_is_inclusive_at_exactly_one_e_minus_twelve(self):
        assert eq_tol('1.0', '1.000000000001')
        assert not eq_tol('1.0', '1.0000000000011')

    def test_eq_tol_accepts_a_custom_tolerance(self):
        assert eq_tol('1.0', '1.001', tol=Decimal('0.01'))
        assert not eq_tol('1.0', '1.02', tol=Decimal('0.01'))

    def test_eq_exact_on_decimals_ignores_trailing_zeros_only(self):
        assert eq_exact(Decimal('2.50'), Decimal('2.5'))
        assert not eq_exact(Decimal('2.50'), Decimal('2.51'))

    def test_eq_exact_on_ints(self):
        assert eq_exact(3, 3)
        assert not eq_exact(3, 4)

    def test_eq_exact_refuses_floats_on_both_sides(self):
        with pytest.raises(FloatNotAllowedError):
            eq_exact(1.0, 1)
        with pytest.raises(FloatNotAllowedError):
            eq_exact(1, 1.0)


class TestAggregates:
    def test_clip_to_bounds(self):
        assert clip('1.5', 0, 1) == Decimal('1')
        assert clip('-0.2', 0, 1) == Decimal('0')
        assert clip('0.4', 0, 1) == Decimal('0.4')
        assert clip('2', '1.2', '1.8') == Decimal('1.8')

    def test_clip_rejects_reversed_bounds(self):
        with pytest.raises(NumericError):
            clip('0.5', 1, 0)

    def test_weighted_sum(self):
        pairs = [(Decimal('0.6'), Decimal('2')), (Decimal('0.4'), Decimal('3'))]
        assert weighted_sum(pairs) == Decimal('2.4')
        assert weighted_sum([]) == Decimal('0')

    def test_weighted_sum_quantizes(self):
        assert weighted_sum([('0.3333333333333', '1')]) == Decimal('0.333333333333')

    def test_mean(self):
        assert mean(['1', '2', '4']) == Decimal('2.333333333333')
        assert mean([Decimal('5')]) == Decimal('5')

    def test_mean_of_empty_raises(self):
        with pytest.raises(NumericError):
            mean([])

    def test_median_odd_and_even(self):
        assert median(['3', '1', '2']) == Decimal('2')
        assert median(['1', '2', '3', '4']) == Decimal('2.5')
        assert median(['4', '1', '3', '2']) == Decimal('2.5')
        assert median(['7']) == Decimal('7')

    def test_median_of_empty_raises(self):
        with pytest.raises(NumericError):
            median([])


class TestL1Distance:
    def test_identical_mappings_are_zero(self):
        w = {'a': Decimal('0.5'), 'b': Decimal('0.5')}
        assert l1_distance(w, dict(w)) == Decimal('0')

    def test_sums_absolute_differences(self):
        a = {'x': Decimal('0.6'), 'y': Decimal('0.4')}
        b = {'x': Decimal('0.4'), 'y': Decimal('0.6')}
        assert l1_distance(a, b) == Decimal('0.4')

    def test_missing_keys_count_as_zero(self):
        a = {'x': Decimal('0.5')}
        b = {'x': Decimal('0.2'), 'y': Decimal('0.3')}
        assert l1_distance(a, b) == Decimal('0.6')

    def test_is_symmetric_and_key_order_independent(self):
        a = {'b': Decimal('0.1'), 'a': Decimal('0.9')}
        b = {'a': Decimal('0.5'), 'b': Decimal('0.5')}
        assert l1_distance(a, b) == Decimal('0.8')
        assert l1_distance(a, b) == l1_distance(b, a)


class TestMathFunctions:
    def test_sqrt(self):
        assert sqrt('4') == Decimal('2')
        assert sqrt('0') == Decimal('0')
        assert sqrt('2') == Decimal('1.414213562373')

    def test_sqrt_of_negative_raises(self):
        with pytest.raises(NumericError):
            sqrt('-1')

    def test_ln(self):
        assert ln('1') == Decimal('0')
        assert ln('2') == Decimal('0.693147180560')

    def test_ln_of_non_positive_raises(self):
        with pytest.raises(NumericError):
            ln('0')
        with pytest.raises(NumericError):
            ln('-1')


class TestRankAverage:
    def test_distinct_values_get_consecutive_ranks_from_one(self):
        ranks = rank_average([Decimal('10'), Decimal('30'), Decimal('20')])
        assert ranks == {0: Decimal('1'), 1: Decimal('3'), 2: Decimal('2')}

    def test_ties_share_the_average_rank(self):
        ranks = rank_average(['5', '5', '9'])
        assert ranks[0] == Decimal('1.5')
        assert ranks[1] == Decimal('1.5')
        assert ranks[2] == Decimal('3')

    def test_all_equal(self):
        ranks = rank_average(['1', '1', '1', '1'])
        assert set(ranks.values()) == {Decimal('2.5')}

    def test_ties_use_the_1e_12_tolerance(self):
        ranks = rank_average(['1.0000000000001', '1.0'])
        assert ranks[0] == ranks[1] == Decimal('1.5')

    def test_ranks_are_quantized_for_stable_hashing(self):
        ranks = rank_average(['5', '5', '9'])
        assert str(ranks[0]) == '1.500000000000'


class TestSpearman:
    def test_identical_rankings_give_plus_one(self):
        xs = [Decimal('1'), Decimal('2'), Decimal('3'), Decimal('4')]
        assert spearman(xs, list(xs)) == Decimal('1')

    def test_reversed_rankings_give_minus_one(self):
        xs = [Decimal('1'), Decimal('2'), Decimal('3'), Decimal('4')]
        ys = [Decimal('4'), Decimal('3'), Decimal('2'), Decimal('1')]
        assert spearman(xs, ys) == Decimal('-1')

    def test_known_value_from_the_textbook_formula(self):
        # ranks 1..5 against 2,1,5,3,4 -> sum d^2 = 8 -> rho = 1 - 48/120 = 0.6
        rho = spearman(['1', '2', '3', '4', '5'], ['2', '1', '5', '3', '4'])
        assert rho == Decimal('0.6')

    def test_result_stays_inside_minus_one_to_one(self):
        rho = spearman(['3', '1', '4', '1', '5'], ['2', '7', '1', '8', '3'])
        assert Decimal('-1') <= rho <= Decimal('1')

    def test_is_symmetric(self):
        xs = ['3', '1', '4', '1', '5']
        ys = ['2', '7', '1', '8', '3']
        assert spearman(xs, ys) == spearman(ys, xs)

    def test_ties_are_handled_with_average_ranks(self):
        assert spearman(['1', '1', '2'], ['5', '5', '9']) == Decimal('1')

    def test_zero_variance_is_undefined_and_must_not_be_reported_as_a_number(self):
        with pytest.raises(DivisionUndefinedError):
            spearman(['1', '1', '1'], ['1', '2', '3'])
        with pytest.raises(DivisionUndefinedError):
            spearman(['1', '2', '3'], ['9', '9', '9'])

    def test_shape_violations_raise(self):
        with pytest.raises(NumericError):
            spearman(['1', '2'], ['1'])
        with pytest.raises(NumericError):
            spearman(['1'], ['1'])
        with pytest.raises(NumericError):
            spearman([], [])

    def test_floats_are_rejected(self):
        with pytest.raises(FloatNotAllowedError):
            spearman([1.0, 2.0], [1.0, 2.0])

    def test_is_deterministic_for_reproducibility_hash(self):
        xs = ['3', '1', '2']
        ys = ['9', '4', '7']
        assert str(spearman(xs, ys)) == str(spearman(xs, ys))
