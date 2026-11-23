'''dsm.numeric -- the single source of truth for numeric semantics.

Design doc 3.3.1 and 3.13. Rules enforced here and nowhere else:

  * money and counts are integers and compare EXACTLY
  * ratios, attainments, weights and means are Decimal and compare with 1e-12 tolerance
  * every division goes through safe_div with an explicit on_zero policy
  * a raw float never reaches the comparison layer (from_float is the audited escape hatch)
  * every result is quantized to 1e-12 before it leaves this module, so that
    reproducibility_hash is stable across runs and machines

No other module may implement its own equality, division or rounding.
'''
from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Iterable, Mapping, Sequence

TOL = Decimal('1E-12')
ZERO = Decimal('0')
ONE = Decimal('1')
MINOR_PER_UNIT = 100

_UNSET = object()


class NumericError(ValueError):
    '''Base class for every numeric contract violation.'''


class NonIntegerAmountError(NumericError):
    '''A money field carried a fractional value. Money must be minor-unit integers (C-09).'''


class DivisionUndefinedError(NumericError):
    '''Division by zero and the caller did not declare an on_zero policy.'''


class FloatNotAllowedError(NumericError):
    '''A raw float reached the numeric layer. Convert it with from_float() explicitly.'''


def D(value) -> Decimal:
    '''Coerce to Decimal. Accepts Decimal, int and str. Rejects float and bool.'''
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise NumericError('bool is not a numeric value in this model')
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, str):
        text = value.strip()
        if text == '':
            raise NumericError('empty string cannot be converted to Decimal')
        try:
            return Decimal(text)
        except InvalidOperation as exc:
            raise NumericError('not a decimal literal: ' + value) from exc
    if isinstance(value, float):
        raise FloatNotAllowedError('float is not allowed here; use from_float() explicitly')
    raise NumericError('unsupported type for Decimal conversion: ' + type(value).__name__)


def from_float(value: float, places: int = 12) -> Decimal:
    '''Explicit escape hatch for float / numpy scalars. Rounds to 1e-12.'''
    return Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def q12(value) -> Decimal:
    '''Quantize to 1e-12 with ROUND_HALF_UP. Every public result passes through here.'''
    return D(value).quantize(TOL, rounding=ROUND_HALF_UP)


def as_minor(value) -> int:
    '''Validate that value already is an integer amount in minor currency units.'''
    d = D(value)
    if d != d.to_integral_value():
        raise NonIntegerAmountError('money field must be an integer in minor units, got ' + str(value))
    return int(d)


def to_minor(value, minor_per_unit: int = MINOR_PER_UNIT) -> int:
    '''Convert a major-unit amount into minor units. The result must be exact.'''
    d = D(value) * Decimal(int(minor_per_unit))
    if d != d.to_integral_value():
        raise NonIntegerAmountError('amount does not convert to an exact minor-unit integer: ' + str(value))
    return int(d)


def from_minor(minor, minor_per_unit: int = MINOR_PER_UNIT) -> Decimal:
    '''Display layer only. Never feed the result back into a comparison.'''
    d = Decimal(as_minor(minor)) / Decimal(int(minor_per_unit))
    return q12(d)


def safe_div(numerator, denominator, on_zero=_UNSET, zero_tol: Decimal = TOL) -> Decimal | None:
    '''The only division entry point in the system.

    on_zero is mandatory semantics. Pass a Decimal to declare the value a zero
    denominator carries, or None to declare that the quotient is genuinely undefined
    (attainment then stays null; it is never silently 0 -- design doc 1.4.3 boundary).
    Omitting on_zero raises DivisionUndefinedError; silent defaults are forbidden by R5.
    '''
    a = D(numerator)
    b = D(denominator)
    if abs(b) <= zero_tol:
        if on_zero is _UNSET:
            raise DivisionUndefinedError('division by zero: caller must pass on_zero explicitly')
        if on_zero is None:
            return None
        return q12(D(on_zero))
    return q12(a / b)


def eq_exact(a, b) -> bool:
    '''Exact equality. Use for money and counts only.'''
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        return D(a) == D(b)
    if isinstance(a, float) or isinstance(b, float):
        raise FloatNotAllowedError('eq_exact refuses floats; use eq_tol or convert first')
    return int(a) == int(b)


def eq_tol(a, b, tol: Decimal = TOL) -> bool:
    '''Tolerant equality (1e-12 by default). Use for ratios, weights and means.'''
    return abs(D(a) - D(b)) <= tol


def clip(value, lo, hi) -> Decimal:
    d = D(value)
    low = D(lo)
    high = D(hi)
    if low > high:
        raise NumericError('clip bounds are reversed')
    if d < low:
        return q12(low)
    if d > high:
        return q12(high)
    return q12(d)


def weighted_sum(pairs: Iterable) -> Decimal:
    '''pairs is an iterable of (weight, value). Order must be deterministic:
    callers pass sorted sequences, never dict iteration order (design doc 3.13).
    '''
    total = ZERO
    for w, v in pairs:
        total = total + D(w) * D(v)
    return q12(total)


def mean(values: Sequence) -> Decimal:
    vals = [D(v) for v in values]
    if not vals:
        raise NumericError('mean of an empty sequence is undefined')
    return q12(sum(vals) / Decimal(len(vals)))


def median(values: Sequence) -> Decimal:
    '''Used by the entropy calibration window (median across periods, design doc 2.4.3).'''
    vals = sorted(D(v) for v in values)
    n = len(vals)
    if n == 0:
        raise NumericError('median of an empty sequence is undefined')
    mid = n // 2
    if n % 2 == 1:
        return q12(vals[mid])
    return q12((vals[mid - 1] + vals[mid]) / Decimal(2))


def l1_distance(a: Mapping, b: Mapping) -> Decimal:
    '''L1 distance between two weight mappings. Used by H-5 and by weight_drift.'''
    total = ZERO
    for key in sorted(set(a) | set(b)):
        total = total + abs(D(a.get(key, ZERO)) - D(b.get(key, ZERO)))
    return q12(total)


def sqrt(value) -> Decimal:
    d = D(value)
    if d < ZERO:
        raise NumericError('sqrt of a negative value')
    return q12(d.sqrt())


def ln(value) -> Decimal:
    d = D(value)
    if d <= ZERO:
        raise NumericError('ln requires a strictly positive value, got ' + str(value))
    return q12(d.ln())


def rank_average(values: Sequence) -> dict:
    '''Average ranks for ties, ranks start at 1. Returns {index: Decimal rank}.'''
    n = len(values)
    decs = [D(v) for v in values]
    order = sorted(range(n), key=lambda i: (decs[i], i))
    ranks = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and eq_tol(decs[order[j + 1]], decs[order[i]]):
            j += 1
        avg = q12((Decimal(i + 1) + Decimal(j + 1)) / Decimal(2))
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(xs: Sequence, ys: Sequence) -> Decimal:
    '''Spearman rank correlation, Decimal end to end.

    Used by triangulation (method agreement) and by alpha calibration
    (mean_spearman). Raises DivisionUndefinedError when either ranking has
    zero variance, because in that case the agreement is genuinely undefined
    and must not be reported as a number.
    '''
    if len(xs) != len(ys):
        raise NumericError('spearman: length mismatch')
    n = len(xs)
    if n < 2:
        raise NumericError('spearman needs at least 2 observations')
    rx = rank_average(list(xs))
    ry = rank_average(list(ys))
    dx = [rx[i] for i in range(n)]
    dy = [ry[i] for i in range(n)]
    mx = mean(dx)
    my = mean(dy)
    num = ZERO
    denx = ZERO
    deny = ZERO
    for i in range(n):
        a = dx[i] - mx
        b = dy[i] - my
        num = num + a * b
        denx = denx + a * a
        deny = deny + b * b
    den = denx * deny
    if den <= ZERO:
        raise DivisionUndefinedError('spearman undefined: zero variance in one of the rankings')
    return q12(num / den.sqrt())
