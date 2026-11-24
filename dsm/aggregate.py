'''dsm.aggregate -- Step 5 dual-track aggregation (M-B; digest M03, SDD
[L462]-[L477] and [L947]-[L957]).

Weighted linear sum, dual track (composite_absolute from the attainment
matrix, composite_relative from the normalized matrix, disclosed separately
[L476]), and weight renormalisation after metric exclusion [L954].

INV-3 [L955]: this module only READS the FROZEN weights handed in as a
WeightVersionDoc argument. It does not import, call, produce or modify any
weight -- the diagnostics and weights-combine neighbours are forbidden and
are never referenced here (guards: T-CMB-06 and the tests/test_architecture
AST scan).

Numeric policy V-9: every arithmetic step goes through dsm.numeric primitives
(D / q12 / weighted_sum / safe_div / eq_tol). No local equality, division or
rounding is implemented here.

Declared gaps (reported to the orchestrator, not silently patched):
  * [L954] requires WEIGHT_REALLOCATED to be logged when a renormalisation
    happens, but ScoreFrame/ScoreRow ([L952]) carries no reason-code column;
    the renormalisation is computed here, its disclosure must land on the
    downstream score_card layer.
  * GEOMETRIC eps ([L473] dim_d <= 0 goes by eps): the digest never names the
    value, so numeric.TOL (1E-12) is used -- placeholder until signed off.
  * NON_COMPENSATORY ([L474], interface kept, off by default): implemented as
    min_d (dim_d) over the available dimensions.
  * The config key switching the operator is not named in the digest;
    'score_operator' is read from a mapping/namespace, default LINEAR.
'''
from __future__ import annotations

from dsm import numeric
from dsm.models import ScoreFrame, ScoreRow

__all__ = ['AggregateError', 'compose']

_DEFAULT_OPERATOR = 'LINEAR'
_ALLOWED_OPERATORS = ('LINEAR', 'GEOMETRIC', 'NON_COMPENSATORY')


class AggregateError(ValueError):
    '''Weight document or operator input violates the [L466]/[L1190] contract.'''


def _resolve_operator(config):
    '''Operator from the config switch [L468]; default LINEAR, closed set [L953].'''
    value = None
    if isinstance(config, dict):
        for key in ('score_operator', 'operator'):
            if config.get(key) is not None:
                value = config[key]
                break
    elif config is not None:
        for attr in ('score_operator', 'operator'):
            value = getattr(config, attr, None)
            if value is not None:
                break
    if value is None:
        return _DEFAULT_OPERATOR
    value = str(value)
    if value not in _ALLOWED_OPERATORS:
        raise AggregateError('unknown score operator: ' + value)
    return value


def _check_weights(weights):
    '''FROZEN gate [L1190] plus the [L466] sums (1e-12 via eq_tol) and the
    one-dimension-per-metric layout. Returns (dims, level1) with dims sorted
    by dimension code; weights stay the caller objects, never mutated (INV-3).'''
    if weights.status != 'FROZEN':
        raise AggregateError('only FROZEN weights may score [L1190]')
    level1 = weights.level1_weights
    level2 = weights.level2_weights
    if sorted(level1) != sorted(level2):
        raise AggregateError('level1/level2 dimension sets differ')
    if not numeric.eq_tol(
            numeric.weighted_sum([(numeric.ONE, level1[d]) for d in sorted(level1)]),
            numeric.ONE):
        raise AggregateError('level1 W_d sum is not 1 [L466]')
    dims = []
    seen = set()
    for dim in sorted(level1):
        mapping = level2[dim]
        if not mapping:
            raise AggregateError('dimension without metrics: ' + dim)
        if not numeric.eq_tol(
                numeric.weighted_sum([(numeric.ONE, mapping[m]) for m in sorted(mapping)]),
                numeric.ONE):
            raise AggregateError('level2 w_j sum is not 1 in dimension ' + dim)
        for metric in sorted(mapping):
            if metric in seen:
                raise AggregateError('metric belongs to two dimensions: ' + metric)
            seen.add(metric)
        dims.append((dim, dict(mapping)))
    return dims, level1


def _track_maps(attainment, normalized):
    '''strategy key -> metric -> track value. Absolute keeps None rows (no
    target, [L930]); relative values are required Decimals [L940].'''
    abs_map = {}
    for row in attainment.rows:
        key = (row.strategy_id, row.version_id, row.period)
        abs_map.setdefault(key, {})[row.metric_id] = row.attainment
    rel_map = {}
    for row in normalized.rows:
        key = (row.strategy_id, row.version_id, row.period)
        rel_map.setdefault(key, {})[row.metric_id] = row.norm_value
    return abs_map, rel_map


def _dim_value(mapping, values):
    '''dim_d = Σ w_j · x_j over the PRESENT metrics [L464]; excluded metrics
    drop out and the remaining w_j renormalise within the dimension [L954].
    Returns (dim value or None, count of scored metrics).'''
    present = sorted(m for m in mapping if values.get(m) is not None)
    if not present:
        return None, 0
    total_w = numeric.weighted_sum([(numeric.ONE, mapping[m]) for m in present])
    if numeric.eq_tol(total_w, numeric.ZERO):
        return None, 0
    pairs = [(numeric.safe_div(mapping[m], total_w, on_zero=None), values[m])
             for m in present]
    return numeric.weighted_sum(pairs), len(present)


def _composite(dims, level1, values, operator):
    '''Per-track composite with the [L954] dimension-level renormalisation:
    a cleared dimension gets W_d = 0 and the remaining W_d renormalise.'''
    avail = []
    dim_map = {}
    for dim, mapping in dims:
        value, _count = _dim_value(mapping, values)
        if value is not None:
            avail.append((dim, level1[dim], value))
            dim_map[dim] = value
    if not avail:
        return None, dim_map
    total = numeric.weighted_sum([(numeric.ONE, w) for _, w, _ in avail])
    if numeric.eq_tol(total, numeric.ZERO):
        return None, dim_map
    pairs = sorted((numeric.safe_div(w, total, on_zero=None), value)
                   for _dim, w, value in avail)
    if operator == 'LINEAR':
        return numeric.weighted_sum(pairs), dim_map
    if operator == 'GEOMETRIC':
        product = numeric.ONE
        for weight, value in pairs:
            base = value if value > numeric.ZERO else numeric.TOL
            product = product * (numeric.D(base) ** numeric.D(weight))
        return numeric.q12(product), dim_map
    return numeric.q12(min(value for _w, value in pairs)), dim_map


def compose(attainment, normalized, weights, config=None):
    '''[L951] signature: two frames plus the frozen weight document in, one
    ScoreFrame row per strategy x version x period out ([L952]). Weights are
    read-only inputs (INV-3); the weight_version_id lands on every row [L955].'''
    operator = _resolve_operator(config)
    dims, level1 = _check_weights(weights)
    abs_map, rel_map = _track_maps(attainment, normalized)
    total_metrics = sum(len(mapping) for _dim, mapping in dims)
    rows = []
    for key in sorted(set(abs_map) | set(rel_map)):
        abs_vals = abs_map.get(key, {})
        rel_vals = rel_map.get(key, {})
        comp_abs, dim_abs = _composite(dims, level1, abs_vals, operator)
        comp_rel, dim_rel = _composite(dims, level1, rel_vals, operator)
        scored = sum(1 for _dim, mapping in dims
                     for m in mapping if abs_vals.get(m) is not None)
        coverage = numeric.safe_div(numeric.D(scored), numeric.D(total_metrics),
                                    on_zero=numeric.ZERO)
        rows.append(ScoreRow(
            strategy_id=key[0], version_id=key[1], period=key[2],
            composite_absolute=comp_abs, composite_relative=comp_rel,
            dim_absolute=dim_abs, dim_relative=dim_rel,
            coverage=coverage, weight_version_id=weights.weight_version_id,
            operator=operator))
    return ScoreFrame(rows=tuple(rows))
