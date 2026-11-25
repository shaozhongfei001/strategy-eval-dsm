'''dsm.diagnostics -- L5 bypass diagnostics: online entropy / CV / VIF / correlation / GRA.

SDD 2.5 [L684]-[L696] and 3.7.3 [L1033]-[L1042]: diagnostics runs every period,
changes no score of the current period, and reaches the next period's dictionary
only through the work-order columns suggested_action and owner of [L1041].

ORCH-03 sharing: [L537] gives the six entropy steps to two computers and the one
implementation lives at L1 in dsm.entropy, which this module calls through the
module object, copying only e_j / d_j into EntropyDiagnosticRow ([L1038]).
INV-3 isolation: L5 imports neither L0a nor L0b, and no output object here carries
a field aggregate.py could consume as a weight -- a weight is a metric -> Decimal
mapping summing to one, and no such field exists. VIF: [L1039] pins VIF_j to the
diagonal of the inverse of the correlation matrix, inverted here in Decimal by
Gauss-Jordan with numeric.TOL as the pivot tolerance, so a singular or near
singular matrix yields no VIF at all (None plus COLLINEAR plus an alert), never a
silent inf or 0. Pure (H-8), every threshold an input (H-5), every number through
dsm.numeric and every code through dsm.reason_codes (H-7).
'''
from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Literal, Mapping

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import entropy, numeric
from dsm.config import PLACEHOLDER_TOKENS
from dsm.models import EntropyDiagnosticRow, MetricDictRow, Ratio, ReasonCode, StrictInt
from dsm.numeric import D, ONE, TOL, ZERO, q12, safe_div
from dsm.reason_codes import RC

LAYER = 'L5'                       # module table: never imports L0a / L0b (INV-1)
GRA_METHOD = 'GRA'                 # [L694] relatedness against the best-value reference
PLACEHOLDER_OWNER = 'PLACEHOLDER'  # R-12: no invented person or department name
CFG_BLOCK = 'diagnostics'
CFG_KEYS = ('inactive_threshold', 'vif_max', 'corr_max', 'cv_min', 'entropy_shift',
            'corr_method', 'gra_rho', 'gra_min', 'gra_k_periods',
            'owner_signed_off_statuses')
# (field, exclusive floor, inclusive ceiling or None) of the params validator.
BOUNDS = (('inactive_threshold', ZERO, ONE), ('corr_max', ZERO, ONE),
          ('gra_rho', ZERO, ONE), ('gra_min', ZERO, ONE),
          ('vif_max', ONE, None), ('entropy_shift', ZERO, None))
CorrMethod = Literal['pearson', 'spearman']  # [L692] names both, the config picks one


class DiagnosticsError(ValueError): '''Base of every diagnostics contract violation.'''

class DiagnosticsConfigError(DiagnosticsError): '''eval_config.diagnostics incomplete.'''

class DiagnosticsInputError(DiagnosticsError): '''The period cannot carry the six steps.'''

class _Frozen(BaseModel):
    '''Snapshot semantics, the character-for-character config of models.py.'''

    model_config = ConfigDict(frozen=True, extra='forbid')


class DiagnosticsParams(_Frozen):
    '''The thresholds of [L690]-[L694], all mandatory: a hardcoded governance
    number would move the work orders silently (H-5), so even the 1e-4 default
    [L551] names arrives through the configuration. gra_k_periods is the k of
    [L694]; the history itself is caller supplied, because this module is single
    period and reads neither clock nor disk (H-8).'''

    inactive_threshold: Ratio      # [L690] d_j below it -> RETIRE_OR_REDLINE
    vif_max: Ratio                 # [L691] VIF_j above it -> MERGE_OR_DROP
    corr_max: Ratio                # [L692] abs(rho) above it -> MERGE_OR_DROP
    cv_min: Ratio                  # [L693] CV_j below it -> REDEFINE
    entropy_shift: Ratio           # [L540] the technical epsilon of Step 2
    corr_method: CorrMethod        # [L692] Pearson or Spearman
    gra_rho: Ratio                 # [L694] GRA distinguishing coefficient
    gra_min: Ratio                 # [L694] the floor of "tends to 0"
    gra_k_periods: StrictInt       # [L694] consecutive periods k
    owner_signed_off_statuses: tuple[str, ...]   # [L1141] what counts as signed

    @model_validator(mode='after')
    def _check(self):
        for name, low, high in BOUNDS:
            value = getattr(self, name)
            if value <= low or (high is not None and value > high):
                raise ValueError(name + ' out of range: ' + str(value))
        if self.cv_min < ZERO:
            raise ValueError('cv_min must not be negative')
        if self.gra_k_periods < 1:
            raise ValueError('gra_k_periods must be at least 1')
        if not self.owner_signed_off_statuses:
            raise ValueError('owner_signed_off_statuses must not be empty')
        return self


def params_from_config(config) -> DiagnosticsParams:
    '''Read eval_config.diagnostics, or refuse: an absent block, an absent key and
    a non-list of sign-off statuses all leave through DiagnosticsConfigError.
    config is an AppConfig, a raw eval_config tree or a built DiagnosticsParams.'''
    if isinstance(config, DiagnosticsParams):
        return config
    tree = getattr(config, 'eval_config', config)
    where = 'eval_config.' + CFG_BLOCK
    block = tree.get(CFG_BLOCK) if isinstance(tree, Mapping) else None
    if not isinstance(block, Mapping):
        raise DiagnosticsConfigError('no ' + where + ' block in the configuration')
    missing = tuple(key for key in CFG_KEYS if key not in block)
    if missing:
        raise DiagnosticsConfigError(where + ' is missing: ' + ', '.join(missing))
    statuses = block['owner_signed_off_statuses']
    if isinstance(statuses, (str, bytes)) or not isinstance(statuses, Iterable):
        raise DiagnosticsConfigError(where + '.owner_signed_off_statuses must be a list')
    payload = {key: block[key] for key in CFG_KEYS}
    payload['owner_signed_off_statuses'] = tuple(str(s) for s in statuses)
    return DiagnosticsParams(**payload)


class EntropyDiagnostic(_Frozen):
    '''entropy_diagnostic of [L686] / [L1040]: one period, one row per metric.'''

    period: str                                   # [L1149] the period diagnosed
    method: str = GRA_METHOD                      # [L694] GRA relatedness
    strategy_count: StrictInt                     # n of [L539]
    strategy_ids: tuple[str, ...] = ()            # sorted, the observation order
    rows: tuple[EntropyDiagnosticRow, ...] = ()   # sorted by metric_code
    sum_d_j: Ratio = ZERO                         # [L544] diagnostic only
    entropy_emitted: bool = True                  # False -> every metric INACTIVE
    inactive_metric_ids: tuple[str, ...] = ()     # [L545] zero variation
    excluded_metric_ids: tuple[str, ...] = ()     # incomplete column, so no row
    redline_metric_ids: tuple[str, ...] = ()      # [L1140] outside the entropy
    gamma_by_metric: dict[str, Ratio] = {}        # [L694] relatedness gamma_j
    gra_doubt_metric_ids: tuple[str, ...] = ()    # [L694] k consecutive periods
    alerts: tuple[ReasonCode, ...] = ()           # R5: nothing is silent

class CollinearityPair(_Frozen):
    '''One off-diagonal cell of [L692], kept so a work order names both metrics.'''

    metric_a: str
    metric_b: str
    corr: Ratio                 # signed rho of the configured method
    exceeds_max: bool           # abs(rho) > corr_max

class CollinearityReport(_Frozen):
    '''The correlation matrix and its inverse diagonal, [L692] and [L1039].'''

    method: CorrMethod
    metric_ids: tuple[str, ...] = ()              # matrix order, active metrics only
    matrix: tuple[tuple[Ratio, ...], ...] = ()    # m x m over metric_ids
    vif_by_metric: dict[str, Ratio] = {}          # inverse diagonal, defined only
    max_abs_corr_by_metric: dict[str, Ratio] = {}
    pairs: tuple[CollinearityPair, ...] = ()
    singular: bool = False                        # no inverse -> no VIF at all
    alerts: tuple[ReasonCode, ...] = ()


def _index_metric_dict(metric_dict) -> dict:
    index = {}
    for row in metric_dict:
        if row.metric_id in index:
            raise DiagnosticsInputError('metric_dict repeats metric_id ' + row.metric_id)
        index[row.metric_id] = row
    if not index:
        raise DiagnosticsInputError('metric_dict is empty')
    return index


def _resolve_period(facts, period):
    '''[L529] the online entropy is single period, so one period must be pinned.'''
    found = sorted({row.period for row in facts})
    if period is not None:
        if period not in found:
            raise DiagnosticsInputError('metric_facts holds no row for period ' + str(period))
        return str(period)
    if len(found) != 1:
        raise DiagnosticsInputError('metric_facts spans ' + str(len(found)) + ' periods;'
                                    ' [L529] is single period, so period= must name one')
    return found[0]


def _columns(facts, index, period):
    '''The strategy x metric matrix of [L539] out of the long fact table. A missing
    metric is a missing row, so a column with a hole cannot enter the six steps
    (they divide by one shared n) and is disclosed as excluded. SUSPECT facts are
    dropped first ([L1151], C-06) and redline metrics never join ([L1140]).'''
    rows = tuple(row for row in facts if row.period == period)
    suspect = tuple(sorted((row.strategy_id, row.metric_id) for row in rows
                           if row.data_quality_flag == 'SUSPECT'))
    kept = tuple(row for row in rows if row.data_quality_flag != 'SUSPECT')
    strategy_ids = sorted({row.strategy_id for row in kept})
    cells = {}
    for row in kept:
        if row.metric_id not in index:
            continue            # a fact with no dictionary entry is preflight's business
        key = (row.strategy_id, row.metric_id)
        if key in cells:
            raise DiagnosticsInputError('metric_facts repeats ' + key[0] + ' / ' + key[1]
                                        + ' in period ' + period)
        cells[key] = row.value
    redline = tuple(sorted(m for m in index if index[m].is_redline))
    values = {}
    excluded = []
    for metric_id in sorted(index):
        if metric_id in redline:
            continue
        if strategy_ids and all((s, metric_id) in cells for s in strategy_ids):
            values[metric_id] = tuple(D(cells[(s, metric_id)]) for s in strategy_ids)
        else:
            excluded.append(metric_id)
    return strategy_ids, values, tuple(excluded), suspect, redline


def _cv(column) -> Decimal | None:
    '''[L693] CV_j = sd_j / mean_j on the raw column, population sd over the n
    strategies of the period; None when the mean is within TOL of zero, because
    that quotient is genuinely undefined and is never reported as a number.'''
    mu = numeric.mean(column)
    variance = numeric.mean([q12((D(v) - mu) ** 2) for v in column])
    return safe_div(numeric.sqrt(variance), mu, on_zero=None)


def _pearson(xs, ys) -> Decimal | None:
    '''Pearson rho in Decimal, None when either column has zero variance.'''
    dx = [D(v) - numeric.mean(xs) for v in xs]
    dy = [D(v) - numeric.mean(ys) for v in ys]
    sxy = sum((a * b for a, b in zip(dx, dy)), ZERO)
    sxx = sum((a * a for a in dx), ZERO)
    syy = sum((b * b for b in dy), ZERO)
    return safe_div(q12(sxy), numeric.sqrt(q12(sxx * syy)), on_zero=None)


def _corr_matrix(values, metric_ids, method: str):
    '''The symmetric matrix of [L692]; a None cell means rho is undefined.'''
    m = len(metric_ids)
    matrix = [[q12(ONE)] * m for _ in range(m)]
    for a in range(m):
        for b in range(a + 1, m):
            xs, ys = values[metric_ids[a]], values[metric_ids[b]]
            if method == 'spearman':
                try:
                    rho = q12(numeric.spearman(xs, ys))
                except numeric.DivisionUndefinedError:
                    rho = None      # a flat ranking has no agreement to report
            else:
                rho = _pearson(xs, ys)
            matrix[a][b] = rho
            matrix[b][a] = rho
    return matrix


def _invert(matrix):
    '''Gauss-Jordan in Decimal, None when a pivot is within numeric.TOL of zero.

    [L1039] makes this the VIF definition: VIF_j = (R^-1)_jj, equivalent to
    1 / (1 - R^2_j) and free of any regression library. Every step is quantized to
    1e-12 (V-9), so the diagonal carries the rounding of the elimination, which no
    threshold comparison of [L691] can observe; numeric.TOL is also the singularity
    test, so a near singular matrix is refused where an exact one would be.'''
    m = len(matrix)
    aug = []
    for i in range(m):
        row = [matrix[i][j] for j in range(m)]
        if any(cell is None for cell in row):
            return None         # an undefined correlation leaves the inverse undefined
        aug.append([q12(cell) for cell in row]
                   + [q12(ONE) if k == i else q12(ZERO) for k in range(m)])
    for col in range(m):
        pivot = max(range(col, m), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) <= TOL:
            return None         # singular or near singular: no VIF, never inf or 0
        aug[col], aug[pivot] = aug[pivot], aug[col]
        divisor = aug[col][col]
        aug[col] = [q12(safe_div(value, divisor, on_zero=None)) for value in aug[col]]
        for row in range(m):
            factor = aug[row][col]
            if row != col and factor != ZERO:
                aug[row] = [q12(aug[row][k] - factor * aug[col][k]) for k in range(2 * m)]
    return [[aug[i][m + j] for j in range(m)] for i in range(m)]


def _pairs_and_max(matrix, metric_ids, corr_max):
    pairs = []
    max_corr = {}
    for a in range(len(metric_ids)):
        for b in range(a + 1, len(metric_ids)):
            rho = matrix[a][b]
            if rho is None:
                continue
            magnitude = q12(abs(rho))
            pairs.append(CollinearityPair(metric_a=metric_ids[a], metric_b=metric_ids[b],
                                          corr=q12(rho), exceeds_max=magnitude > corr_max))
            for metric_id in (metric_ids[a], metric_ids[b]):
                if magnitude > max_corr.get(metric_id, ZERO):
                    max_corr[metric_id] = magnitude
    return tuple(pairs), max_corr


def _gamma(column, direction, rho) -> Decimal | None:
    '''[L694] GRA relatedness against the period's best value. The reference
    sequence is the current period optimum, so the best strategy attains it and the
    smallest distance is 0: xi reduces to rho * delta_max / (delta_i + rho *
    delta_max) and gamma_j is the mean over the n strategies. Step 1 orientation
    comes from the L1 implementation, not from a local copy.'''
    oriented = entropy.step1_orient(column, direction)
    deltas = [abs(value - max(oriented)) for value in oriented]
    delta_max = max(deltas)
    if delta_max <= TOL:
        return None             # a constant column has no distance to rank
    numerator = q12(D(rho) * delta_max)
    coefficients = []
    for delta in deltas:
        xi = safe_div(numerator, q12(delta + D(rho) * delta_max), on_zero=None)
        if xi is None:
            return None
        coefficients.append(xi)
    return numeric.mean(coefficients)


def _gra_doubt(gamma_j, prior_gamma, metric_id, params) -> bool:
    '''[L694] gamma_j tends to 0 for k consecutive periods, this one included.'''
    if gamma_j is None:
        return False
    sequence = tuple(D(v) for v in (prior_gamma or {}).get(metric_id, ())) + (D(gamma_j),)
    k = int(params.gra_k_periods)
    if len(sequence) < k:
        return False            # not enough observed periods to claim a trend
    return all(value < params.gra_min for value in sequence[-k:])


def _owner(metric: MetricDictRow, params) -> tuple:
    '''[L1041] owner comes from T2 owner_name [L1141] or stays a placeholder: R-12
    forbids an invented person or department, so the gap is flagged, not filled.'''
    name = str(metric.owner_name).strip()
    signed = str(metric.signoff_status) in params.owner_signed_off_statuses
    if not signed or not name or name.upper().startswith(PLACEHOLDER_TOKENS):
        return PLACEHOLDER_OWNER, True
    return name, False


def _decide(inactive, low_d, collinear, low_cv, undefined_cv, doubt, placeholder):
    '''The five diagnostic rows of [L690]-[L694] into one status and one work order.

    [L1040] closes status at four values and models.py keeps a single
    suggested_action, so several rules firing at once need an order: the table
    order of [L690]-[L694]. The winning rule becomes suggested_action and every
    other triggered code stays in flags, so nothing is lost (R5). Returns
    (status, suggested_action, flags).'''
    rules = []
    if inactive:
        rules.append((RC.INACTIVE_METRIC.value, RC.RETIRE_OR_REDLINE.value))
    elif low_d or undefined_cv:
        rules.append((RC.LOW_VARIATION.value, RC.RETIRE_OR_REDLINE.value))
    if collinear:
        rules.append((RC.COLLINEAR.value, RC.MERGE_OR_DROP.value))
    if low_cv or undefined_cv:
        rules.append((RC.REDEFINE.value, RC.REDEFINE.value))
    if doubt:
        rules.append((RC.CONTENT_VALIDITY_DOUBT.value, RC.CONTENT_VALIDITY_DOUBT.value))
    codes = {code for code, _ in rules}
    if rules:
        codes.discard(rules[0][0])
    if placeholder:
        codes.add(RC.CONFIG_PLACEHOLDER.value)
    status = 'INACTIVE' if inactive else 'COLLINEAR' if collinear else \
        'LOW_VARIATION' if (low_d or low_cv or undefined_cv) else 'OK'
    return status, (rules[0][1] if rules else None), tuple(sorted(codes))


def compute(facts, metric_dict, config, *, period=None, prior_gamma=None):
    '''[L1037] compute(facts, metric_dict, config) -> (EntropyDiagnostic,
    CollinearityReport), the whole L5 bypass for one period.

    facts is the T3 long table, metric_dict the T2 dictionary, config an AppConfig
    / eval_config tree / DiagnosticsParams. period pins the single period when
    facts carry more than one; prior_gamma carries the gamma_j of earlier periods
    for the k-period rule of [L694], oldest first.'''
    params = params_from_config(config)
    index = _index_metric_dict(metric_dict)
    resolved = _resolve_period(facts, period)
    strategy_ids, values, excluded, suspect, redline = _columns(facts, index, resolved)
    if len(strategy_ids) < entropy.MIN_STRATEGIES:
        raise DiagnosticsInputError('period ' + resolved + ' holds ' + str(len(strategy_ids))
                                    + ' strategies; [L542] divides by ln n, so the online'
                                    + ' entropy needs ' + str(entropy.MIN_STRATEGIES))
    if not values:
        raise DiagnosticsInputError('period ' + resolved
                                    + ' has no complete non-redline metric column')
    directions = {m: index[m].direction for m in values}
    vector = entropy.entropy_weights(values, directions, params.entropy_shift)
    columns = {c.metric_id: c for c in vector.columns}
    active = tuple(m for m in sorted(values) if m not in vector.inactive_metric_ids)

    matrix = _corr_matrix(values, active, params.corr_method) if len(active) >= 2 else []
    inverse = _invert(matrix) if matrix else None
    singular = bool(matrix) and inverse is None
    vif = {}
    if inverse is not None:
        for position, metric_id in enumerate(active):
            vif[metric_id] = q12(inverse[position][position])   # [L1039] the diagonal
    pairs, max_corr = _pairs_and_max(matrix, active, params.corr_max) if matrix else ((), {})
    gammas = {}
    for metric_id in active:
        gamma_j = _gamma(values[metric_id], directions[metric_id], params.gra_rho)
        if gamma_j is not None:
            gammas[metric_id] = q12(gamma_j)
    doubt = tuple(sorted(m for m in gammas if _gra_doubt(gammas[m], prior_gamma, m, params)))

    alerts = set(vector.alerts)
    for code, triggered in ((RC.MISSING_RATE_WARN.value, excluded),
                            (RC.DATA_QUALITY_SUSPECT.value, suspect),
                            (RC.COLLINEAR.value, singular),
                            (RC.CONTENT_VALIDITY_DOUBT.value, doubt)):
        if triggered:
            alerts.add(code)

    rows = []
    for metric_id in sorted(values):
        column = columns[metric_id]
        inactive = column.status == 'INACTIVE'
        raw_cv = _cv(values[metric_id])
        undefined_cv = raw_cv is None
        collinear = metric_id in active and (
            singular or vif.get(metric_id, ZERO) > params.vif_max
            or max_corr.get(metric_id, ZERO) > params.corr_max)
        owner, placeholder = _owner(index[metric_id], params)
        if placeholder:
            alerts.add(RC.CONFIG_PLACEHOLDER.value)
        status, action, flags = _decide(
            inactive, (not inactive) and column.d_j < params.inactive_threshold, collinear,
            (not undefined_cv) and raw_cv < params.cv_min, undefined_cv,
            metric_id in doubt, placeholder)
        rows.append(EntropyDiagnosticRow(
            metric_code=metric_id, e_j=column.e_j, d_j=column.d_j,
            cv_j=q12(ZERO) if undefined_cv else q12(raw_cv), vif_j=vif.get(metric_id),
            max_abs_corr=max_corr.get(metric_id), status=status,
            suggested_action=action, owner=owner, flags=flags))

    diagnostic = EntropyDiagnostic(
        period=resolved, strategy_count=len(strategy_ids), strategy_ids=tuple(strategy_ids),
        rows=tuple(rows), sum_d_j=vector.sum_d_j, entropy_emitted=vector.entropy_emitted,
        inactive_metric_ids=tuple(vector.inactive_metric_ids), excluded_metric_ids=excluded,
        redline_metric_ids=redline, gamma_by_metric=gammas, gra_doubt_metric_ids=doubt,
        alerts=tuple(sorted(alerts)))
    report_alerts = set()
    if singular:
        report_alerts.add(RC.COLLINEAR.value)
    if any(pair.exceeds_max for pair in pairs):
        report_alerts.add(RC.MERGE_OR_DROP.value)
    report = CollinearityReport(
        method=params.corr_method, metric_ids=active if matrix else (),
        matrix=tuple(tuple(q12(cell) for cell in row) for row in matrix),
        vif_by_metric=vif, max_abs_corr_by_metric=max_corr, pairs=pairs,
        singular=singular, alerts=tuple(sorted(report_alerts)))
    return diagnostic, report
