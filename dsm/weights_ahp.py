'''dsm.weights_ahp -- the ONE implementation of the AHP weight derivation
(SDD 2.4.1 [L501]-[L523], module table row weights_ahp.py [L1070]).

Layer L0b: an offline tool. INV-1 keeps this layer away from L1-L5, so the only
dsm dependency is dsm.numeric. The result models are declared here with every
field name copied verbatim from dsm.models.AhpSegment ([L1232]-[L1233]), which
lets weights_combine.py (L0a) build the frozen provenance segment with
AhpSegment(**result.segment_payload()) while this module never imports the
contract layer.

The seven steps of [L511]-[L520]:

  Step 1  read the pairwise comparison matrices A = [a_ij], 1-9 scale
  Step 2  reciprocity a_ij * a_ji = 1 within 1e-12 -> MatrixNotReciprocalError
  Step 3  multi-expert geometric aggregation a_ij = (prod_k a_ij(k)) ^ (1/K)
  Step 4  geometric-mean weights w_i = (prod_j a_ij) ^ (1/n), normalised
  Step 5  eigenvector cross check A w = lambda_max w; the two weight sets must
          agree within 1e-6, otherwise METHOD_MISMATCH is recorded
  Step 6  CI = (lambda_max - n)/(n - 1), CR = CI / RI(n). CR >= 0.1 rejects the
          draft and reports the five most inconsistent judgements
  Step 7  the product is an AhpResult whose status can only ever be DRAFT

Governance ([L522], T-AHP-06): sign-off is a human act. There is no code path
here that yields FROZEN -- freeze() raises, and building a result with a
non-DRAFT status raises FrozenStatusError.

Numeric discipline (V-9): every input cell goes through dsm.numeric.D (a raw
float is refused there, not silently coerced), every division goes through
safe_div with an explicit on_zero, and every published number passes q12. The
ln/exp work and the power iteration run inside a 60-digit localcontext. The
Step 3 aggregate is deliberately published at that working precision instead of
being quantised: rounding a_ij to 1e-12 would break the Step 2 reciprocity
re-check for large scale values (a_ij = 9 would move by 9 * 5e-13), while the
derivation stays deterministic because libmpdec ln/exp are correctly rounded.

RI(n) is Saaty's published random index table, n = 1..10 ([L518] names the
table, the digest carries no values); n > 10 raises, never extrapolates (H-5).

Deterministic and pure: no wall clock, no randomness, expert ids and item keys sorted.
'''
from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
from typing import Annotated, Literal, Mapping

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from dsm import numeric
from dsm.numeric import D, ONE, TOL, ZERO, q12, safe_div

__all__ = [
    'AhpError', 'AhpHierarchy', 'AhpResult', 'ConsistencyFailedError',
    'ConsistencyReport', 'FrozenStatusError', 'InconsistentPair',
    'MatrixNotReciprocalError', 'aggregate_matrices', 'check_consistency',
    'eigenvector_weights', 'elicit', 'elicit_hierarchy', 'freeze',
    'geometric_weights', 'random_index', 'validate_matrix', 'worst_pairs',
]

LAYER = 'L0b'
DRAFT = 'DRAFT'
CR_THRESHOLD = D('0.1')              # [L519] CR >= 0.1 rejects the draft
METHOD_GAP_TOL = D('0.000001')       # [L515] geometric vs eigenvector, 1e-6
METHOD_MISMATCH = 'METHOD_MISMATCH'  # [L515] recorded finding
WORST_PAIR_LIMIT = 5                 # [L519] the five most inconsistent pairs
WORK_PREC = 60                       # internal ln/exp and power iteration
POWER_ITERATIONS = 500
POWER_TOL = D('1E-30')
RI_MAX_N = 10

# Saaty random index table, RI(n) of [L518]. See the module docstring.
RANDOM_INDEX = {
    1: ZERO, 2: ZERO, 3: D('0.58'), 4: D('0.90'), 5: D('1.12'),
    6: D('1.24'), 7: D('1.32'), 8: D('1.41'), 9: D('1.45'), 10: D('1.49'),
}

_Ratio = Annotated[Decimal, BeforeValidator(numeric.D)]


class AhpError(Exception):
    '''Base class of every AHP contract violation. Deliberately not a ValueError:
    pydantic folds a ValueError raised inside a validator into a ValidationError,
    and T-AHP-06 needs the real exception type to surface.'''


class MatrixNotReciprocalError(AhpError):
    '''Step 2 [L512]: a_ij * a_ji != 1 within 1e-12. A matrix that is not square
    over one item key set, or that carries a non-positive cell, cannot be
    reciprocal either, so those refusals use the same named exception.'''


class ConsistencyFailedError(AhpError):
    '''Step 6 [L519]: CR >= 0.1, no weight draft is produced. The full
    ConsistencyReport travels on the exception, so the experts get the worst
    judgements without a second run.'''

    exit_code = 6                    # [L1070]

    def __init__(self, message, report):
        super().__init__(message)
        self.report = report


class FrozenStatusError(AhpError):
    '''Governance [L522]: the tool output status can only ever be DRAFT.'''


class _Frozen(BaseModel):
    '''Snapshot semantics, character for character the config of models.py.'''

    model_config = ConfigDict(frozen=True, extra='forbid')


def _refuse_non_draft(data):
    '''Shared body of the two status guards: anything but DRAFT is refused with a
    real exception type, never with a silent rewrite ([L520], T-AHP-06).'''
    if isinstance(data, Mapping):
        status = data.get('status', DRAFT)
        if status != DRAFT:
            raise FrozenStatusError(
                'weights_ahp produces status DRAFT only ([L520]-[L522], T-AHP-06); got '
                + str(status) + '. Sign-off is a human act, code must not do it.')
    return data


class InconsistentPair(_Frozen):
    '''One judgement (i, j) ranked by |ln(a_ij * w_j / w_i)|: the log distance
    between the elicited ratio and the ratio the derived weights imply. Zero
    means the weights reproduce the judgement exactly; the larger the value, the
    earlier the experts should refill this pair ([L519]).'''

    item_i: str
    item_j: str
    a_ij: _Ratio
    deviation: _Ratio


class ConsistencyReport(_Frozen):
    '''check_consistency(A) output ([L1070]): the whole Step 4-6 chain side by
    side, so an auditor can recompute CR from this one object alone.'''

    item_keys: tuple[str, ...]
    lambda_max: _Ratio
    ci: _Ratio
    ri: _Ratio
    cr: _Ratio
    passed: bool
    weights_geometric: dict[str, _Ratio]
    weights_eigenvector: dict[str, _Ratio]
    max_method_gap: _Ratio
    worst_pairs: tuple[InconsistentPair, ...] = ()
    findings: tuple[str, ...] = ()


class AhpResult(_Frozen):
    '''Step 7 product for ONE comparison level. The provenance field names are
    copied verbatim from dsm.models.AhpSegment ([L1232]-[L1233]).'''

    status: Literal['DRAFT'] = DRAFT
    expert_ids: tuple[str, ...]
    expert_count: int                              # [L1232] expert head count
    interview_dates: tuple[date, ...] = ()         # [L1232] injected, no clock
    item_keys: tuple[str, ...]
    comparison_matrices: dict[str, dict[str, dict[str, _Ratio]]]  # [L1232]
    aggregated_matrix: dict[str, dict[str, _Ratio]]               # Step 3
    lambda_max: _Ratio                             # [L1232]
    ci: _Ratio                                     # [L1232] consistency index
    ri: _Ratio                                     # [L1232] random index
    cr: _Ratio                                     # [L1232] consistency ratio
    weights_geometric: dict[str, _Ratio]           # [L1233]
    weights_eigenvector: dict[str, _Ratio]         # [L1233]
    max_method_gap: _Ratio                         # [L1233]
    worst_pairs: tuple[InconsistentPair, ...] = ()
    findings: tuple[str, ...] = ()

    @model_validator(mode='before')
    @classmethod
    def _refuse_frozen_status(cls, data):
        return _refuse_non_draft(data)

    def segment_payload(self) -> dict:
        '''Exactly the keyword set of dsm.models.AhpSegment, nothing more, so
        weights_combine.py can hand it straight to the contract layer.'''
        return {
            'comparison_matrices': self.comparison_matrices,
            'lambda_max': self.lambda_max,
            'ci': self.ci,
            'ri': self.ri,
            'cr': self.cr,
            'expert_count': self.expert_count,
            'interview_dates': list(self.interview_dates),
            'weights_geometric': dict(self.weights_geometric),
            'weights_eigenvector': dict(self.weights_eigenvector),
            'max_method_gap': self.max_method_gap,
        }


class AhpHierarchy(_Frozen):
    '''Step 7 in full ([L520]): the dimension layer W_d(AHP) plus the metric
    layer w_j(AHP) of every dimension. Each level is an ordinary AhpResult with
    its own CR gate, so each maps 1:1 onto one dsm.models.AhpSegment.'''

    status: Literal['DRAFT'] = DRAFT
    dimension: AhpResult
    metrics_by_dim: dict[str, AhpResult]
    interview_dates: tuple[date, ...] = ()

    @model_validator(mode='before')
    @classmethod
    def _refuse_frozen_status(cls, data):
        return _refuse_non_draft(data)

    def dimension_segment_payload(self) -> dict:
        return self.dimension.segment_payload()

    def metric_segment_payload(self, dim_id: str) -> dict:
        return self.metrics_by_dim[dim_id].segment_payload()


def random_index(n: int) -> Decimal:
    '''RI(n) of [L518]: Saaty's published random index table for n = 1..10.
    Above that it raises instead of inventing a value nobody signed off.'''
    count = int(n)
    if count < 1:
        raise AhpError('a comparison matrix needs at least one item, got n = ' + str(n))
    if count not in RANDOM_INDEX:
        raise AhpError('no RI(n) table entry for n = ' + str(count)
                       + '; the table stops at ' + str(RI_MAX_N))
    return RANDOM_INDEX[count]


def validate_matrix(matrix, label: str = 'matrix'):
    '''Step 1 + Step 2. Returns (sorted item keys, Decimal cells). Raises
    MatrixNotReciprocalError when the matrix is not a square, strictly positive,
    reciprocal mapping over one single item key set.'''
    if not isinstance(matrix, Mapping) or len(matrix) == 0:
        raise MatrixNotReciprocalError(label + ': a comparison matrix must be a non-empty mapping')
    keys = sorted(matrix)
    for i in keys:
        row = matrix[i]
        if not isinstance(row, Mapping) or sorted(row) != keys:
            raise MatrixNotReciprocalError(label + ': row ' + str(i)
                                           + ' is not square over the item key set ' + str(keys))
    cells = {i: {j: D(matrix[i][j]) for j in keys} for i in keys}
    for i in keys:
        for j in keys:
            value = cells[i][j]
            if value <= ZERO:
                raise MatrixNotReciprocalError(label + ': a_ij must be strictly positive, got '
                                               + str(value) + ' at ' + str(i) + '/' + str(j))
            product = value * cells[j][i]
            if not numeric.eq_tol(product, ONE, TOL):
                raise MatrixNotReciprocalError(label + ': reciprocity a_ij * a_ji = 1 violated at '
                                               + str(i) + '/' + str(j) + ', product = ' + str(product))
    return keys, cells


def aggregate_matrices(matrices):
    '''Step 3 [L513]: a_ij(aggregate) = (prod_k a_ij(k)) ^ (1/K), evaluated as
    exp(mean_k ln a_ij(k)), which keeps the aggregate reciprocal. Every expert
    matrix is validated first and all of them must compare the same item key
    set. Returns (expert_ids, item_keys, per-expert cells, aggregate).'''
    if not isinstance(matrices, Mapping) or len(matrices) == 0:
        raise AhpError('elicit needs at least one expert comparison matrix')
    expert_ids = sorted(matrices)
    per_expert = {}
    keys = None
    for expert in expert_ids:
        found, cells = validate_matrix(matrices[expert], 'expert ' + str(expert))
        if keys is None:
            keys = found
        elif found != keys:
            raise AhpError('expert ' + str(expert) + ' compares the item set ' + str(found)
                           + ', the other experts compare ' + str(keys) + '; cannot aggregate')
        per_expert[expert] = cells
    head_count = Decimal(len(expert_ids))
    aggregate = {}
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        for i in keys:
            row = {}
            for j in keys:
                total = ZERO
                for expert in expert_ids:
                    total = total + per_expert[expert][i][j].ln()
                row[j] = (total / head_count).exp()
            aggregate[i] = row
    return expert_ids, keys, per_expert, aggregate


def geometric_weights(keys, matrix) -> dict:
    '''Step 4 [L514]: w_i = (prod_j a_ij) ^ (1/n), then normalised to sum 1.
    Every published weight passes q12.'''
    count = Decimal(len(keys))
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        raw = {}
        for i in keys:
            total = ZERO
            for j in keys:
                total = total + D(matrix[i][j]).ln()
            raw[i] = (total / count).exp()
        denominator = ZERO
        for i in keys:
            denominator = denominator + raw[i]
        return {i: q12(raw[i] / denominator) for i in keys}


def eigenvector_weights(keys, matrix):
    '''Step 5 [L515]: solve A w = lambda_max w by power iteration in Decimal,
    return (normalised weights, lambda_max). A strictly positive matrix has a
    unique positive Perron vector, so the iteration is deterministic; a perfectly
    consistent matrix has a zero sub-dominant eigenvalue and lands in one step.
    lambda_max is sum_i (A w)_i, valid because sum_i w_i = 1.'''
    count = Decimal(len(keys))
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        weights = {i: ONE / count for i in keys}
        for _ in range(POWER_ITERATIONS):
            image = {}
            total = ZERO
            for i in keys:
                acc = ZERO
                for j in keys:
                    acc = acc + D(matrix[i][j]) * weights[j]
                image[i] = acc
                total = total + acc
            delta = ZERO
            for i in keys:
                nxt = image[i] / total
                delta = max(delta, abs(nxt - weights[i]))
                weights[i] = nxt
            if delta <= POWER_TOL:
                break
        lambda_max = ZERO
        for i in keys:
            for j in keys:
                lambda_max = lambda_max + D(matrix[i][j]) * weights[j]
        return {i: q12(weights[i]) for i in keys}, q12(lambda_max)


def worst_pairs(keys, matrix, weights, limit: int = WORST_PAIR_LIMIT) -> tuple:
    '''The Step 6 companion report [L519]: rank the n(n-1)/2 distinct judgements
    by |ln(a_ij * w_j / w_i)| and keep the `limit` most inconsistent ones. Ties
    break on the sorted item index pair, so the report is reproducible.'''
    ranked = []
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        for a, i in enumerate(keys):
            for b, j in enumerate(keys):
                if a >= b:
                    continue
                implied = D(matrix[i][j]) * D(weights[j]) / D(weights[i])
                ranked.append((q12(abs(implied.ln())), a, b, i, j, q12(D(matrix[i][j]))))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]))
    return tuple(InconsistentPair(item_i=r[3], item_j=r[4], a_ij=r[5], deviation=r[0])
                 for r in ranked[:limit])


def _report(keys, cells) -> ConsistencyReport:
    '''Steps 4, 5 and 6 on one already validated matrix.'''
    weights_geometric = geometric_weights(keys, cells)
    weights_eigenvector, lambda_max = eigenvector_weights(keys, cells)
    gap = ZERO
    for i in keys:
        gap = max(gap, abs(weights_geometric[i] - weights_eigenvector[i]))
    gap = q12(gap)
    findings = ()
    if gap > METHOD_GAP_TOL:
        findings = (METHOD_MISMATCH,)
    count = Decimal(len(keys))
    ci = q12(safe_div(lambda_max - count, count - ONE, on_zero=ZERO))
    ri = random_index(len(keys))
    cr = q12(safe_div(ci, ri, on_zero=ZERO))
    return ConsistencyReport(
        item_keys=tuple(keys),
        lambda_max=lambda_max,
        ci=ci,
        ri=ri,
        cr=cr,
        passed=cr < CR_THRESHOLD,
        weights_geometric=weights_geometric,
        weights_eigenvector=weights_eigenvector,
        max_method_gap=gap,
        worst_pairs=worst_pairs(keys, cells, weights_geometric),
        findings=findings,
    )


def check_consistency(matrix) -> ConsistencyReport:
    '''check_consistency(A) -> ConsistencyReport ([L1070]). A bad CR does not
    raise here: passed is False and the caller decides. Only Step 2 raises.'''
    keys, cells = validate_matrix(matrix, 'check_consistency')
    return _report(keys, cells)


def elicit(matrices, interview_dates=()) -> AhpResult:
    '''Steps 1-7 for ONE comparison level ([L1070]).

    matrices is {expert_id: {item_i: {item_j: a_ij}}}; interview_dates is
    injected by the caller ([L1232], H-8: nothing here reads the wall clock).
    Raises MatrixNotReciprocalError (Step 2), AhpError (the experts do not share
    one item set) and ConsistencyFailedError with the report attached (Step 6).
    The status of a returned result is always DRAFT.
    '''
    expert_ids, keys, per_expert, aggregate = aggregate_matrices(matrices)
    report = _report(keys, aggregate)
    if not report.passed:
        raise ConsistencyFailedError(
            'CR = ' + str(report.cr) + ' >= ' + str(CR_THRESHOLD)
            + ': the weight draft is rejected; the ' + str(len(report.worst_pairs))
            + ' most inconsistent judgements are attached for the experts to refill ([L519])',
            report)
    return AhpResult(
        expert_ids=tuple(expert_ids),
        expert_count=len(expert_ids),
        interview_dates=tuple(interview_dates),
        item_keys=tuple(keys),
        comparison_matrices={e: per_expert[e] for e in expert_ids},
        aggregated_matrix=aggregate,
        lambda_max=report.lambda_max,
        ci=report.ci,
        ri=report.ri,
        cr=report.cr,
        weights_geometric=report.weights_geometric,
        weights_eigenvector=report.weights_eigenvector,
        max_method_gap=report.max_method_gap,
        worst_pairs=report.worst_pairs,
        findings=report.findings,
    )


def elicit_hierarchy(dimension_matrices, metric_matrices_by_dim, interview_dates=()) -> AhpHierarchy:
    '''Step 7 [L520] in full: the dimension layer W_d(AHP) and the metric layer
    w_j(AHP) of every dimension, each level behind its own CR gate.'''
    dimension = elicit(dimension_matrices, interview_dates)
    metrics = {}
    for dim_id in sorted(metric_matrices_by_dim):
        metrics[dim_id] = elicit(metric_matrices_by_dim[dim_id], interview_dates)
    return AhpHierarchy(dimension=dimension, metrics_by_dim=metrics,
                        interview_dates=tuple(interview_dates))


def freeze(result) -> None:
    '''There is no such operation. [L522]: the tool status can only be DRAFT and
    writing FROZEN raises. Sign-off is a named human act on the weight version
    document, never something this module performs (T-AHP-06).'''
    raise FrozenStatusError('weights_ahp cannot write status FROZEN ([L522], T-AHP-06); '
                            'sign-off is a human act on WeightVersionDoc')
