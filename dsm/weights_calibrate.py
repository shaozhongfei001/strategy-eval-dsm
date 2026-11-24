'''dsm.weights_calibrate -- alpha 标定：字典序可行集，不是加权目标函数 (SDD 2.4.4 [L604]-[L639],
digest M09). Layer L0b, offline annual tool.

[L606] forbids minimize lambda1*drift + lambda2*boundary + lambda3*(1-rho): it adds three
subjective parameters. The criterion of [L608]-[L609] is a CONJUNCTION of five constraints
plus ONE minimisation, on alpha itself: alpha* = the SMALLEST alpha satisfying every
stability constraint, with alpha* >= alpha_floor. Selection is therefore LEXICOGRAPHIC on
two keys and never a weighted score -- key 1 governance band membership (alpha >=
alpha_floor, [L609] / K-15), key 2 alpha ascending ([L608]). Key 1 dominates absolutely, so
a below-floor alpha is never traded against a better indicator value, and neither this file
nor CalibrationReport carries a lambda or an aggregate score column, only the five raw
indicators of [L617]-[L623]. [L625] 不得假设单调: the WHOLE grid is traversed and the feasible
minimum taken; a feasible set with a hole is reported with NON_MONOTONIC_WARNING plus the
full feasible list for a human choice -- a warning, never an error (T-CAL-02).

The five rows of [L617]-[L623], windowed over the calibration periods: weight_drift =
max_t || w(a,t) - w(a,t-1) ||_1 with each period using ITS OWN entropy weights (不冻结),
measured on the dimension layer AND the effective W_d * w_j layer with the larger one
constraining (as step5_hard_checks does for the equally unnamed layer of H-5), <= K-16;
boundary_ratio = window max of the share of assessed strategies whose composite_absolute
lies within +- boundary_epsilon K-18 of ANY attainment_floor, <= K-17; oat_flip_rate =
window max of sensitivity's OAT_10 overall_flip_rate ([L621] ±10%), <= stable_max K-11;
mean_spearman = MEAN over the periods of triangulation's mean_rho ([L622]), >=
divergence_threshold; hard_constraints = H-1~H-5 of [L593]-[L599] through the INJECTED
combine capability, EVERY period. Nothing another module owns is recomputed here (R-7): the
injected combine_fn, aggregate.compose, grading.assign, sensitivity.run and triangulation.run
are called, the last four wired by default_pipeline(), which a caller may replace with its own
pipeline of the same shape. [L294] lets L0b import L1-L5 and nothing else, so the L0a combine
capability is a keyword-only REQUIRED injection on CalibrationInputs (combine_fn, options_fn,
entropy_window_fn, insufficient_sample_error) that the caller hands in -- ORCH-29 ruling 3.
No import and no duck typing stands in for it, and a missing one raises HookRequiredError
rather than degrading into a locally re-implemented combine (V-14). This is what [L282] means
by L0b needing the full Step 1-7 pipeline: every step of that pipeline lives in L1-L5, and the
weight-combination CAPABILITY the backtest needs on top of it arrives by injection.

边界情形, all four non-silent ([L627]-[L634]): empty feasible set -> AlphaInfeasibleError
with the per-alpha x per-constraint violation matrix ([L631]), exit 7 in cli.py; alpha* = 1
-> normal output plus ALPHA_PURE_AHP and a first-page statement ([L632]); alpha* below the
floor -> take alpha_floor and verify it, infeasible -> AlphaFloorInfeasibleError ([L633]),
never a silent widen; entropy sample too thin -> skip, alpha = 1,
ENTROPY_INSUFFICIENT_SAMPLE ([L634]). 治理预算 (P-13 / [L638]): alpha_floor, drift_budget,
boundary_budget, boundary_epsilon, min_dim_weight, max_shift_from_ahp (K-15~K-20) plus
stable_max (K-11) and divergence_threshold come from the SIGNED config only, with no write
path -- frozen at entry, re-read from the same object at exit, any difference ->
GovernanceBudgetTamperError (T-CAL-04); an absent key or an unfilled slot
(config.is_placeholder_value) -> MissingBudgetError, so no governance number is invented
(R-12) and none is widened to reach a smaller alpha. V-9: ratios are Decimal via numeric.D
(floats refused) and q12, counts are int, every division goes through safe_div with an
explicit on_zero and an empty denominator is an error, never 0. H-8: no clock, no unseeded
generator, the seed is an input and mappings are traversed sorted, so one seed gives
byte-identical reports (T-CAL-03). INV-2: returns a report, writes nothing.

契约缺口 (R-1/R-15: models.py, config.py, cli.py, tests/** and ops/** are not this package's
to edit; declared for the orchestrator, and repeated in the A3 lane report):
  1. CalibrationReport lives HERE on purpose -- models.py reserves the name for this module
     -- and to_alpha_basis() is the [L636] write into provenance.alpha_basis.
  2. RESOLVED by ORCH-29 ruling 3 (A3b): [L294] reads L0b -> L1-L5 verbatim, so the one
     weights_combine import the A3 draft kept (D-A3-01) is gone and the capability is injected
     instead. `hierarchy` is no longer duck typed either -- it is the
     weights_combine.AhpHierarchySnapshot DATA the same caller injects (ruling 1). The public
     marshal calibrate(grid, window, inputs, config) is untouched, so dsm/cli.py cmd_calibrate
     and the test_integration_spine signature guard keep their shape; only the construction of
     CalibrationInputs gains four required keyword arguments, which P2 wires in cli.py.
  3. aggregate.compose gates on FROZEN ([L1190]) and weights_combine may only emit DRAFT
     ([L600]); a candidate is neither, so candidate_doc() builds an IN-MEMORY doc for the
     historical re-run, never returned or persisted (INV-2). boundary_ratio needs the
     attainment_floor set, so PeriodCase carries that period's grading.GradeRuleSet. shift
     ([L540]) and the window have no digest value, so both are required inputs (R-12).
  4. tests/test_properties_all.py::test_p13b (another lane's write set, gated behind
     importorskip, so it unlocked when this module landed) calls calibrate with inputs=None
     and a window dict, catching only TypeError: it cannot pass against any implementation
     that refuses to invent the inputs it was not given (V-14). Needs real CalibrationInputs.
'''
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict

from dsm import aggregate, grading, numeric, sensitivity, triangulation
from dsm.config import is_placeholder_value
from dsm.models import (AlphaBasisSegment, GradeFrame, Ratio, ScoringContext, ScoreFrame,
                        StrictInt, WeightVersionDoc)
from dsm.numeric import D, ONE, TOL, ZERO, q12, safe_div
from dsm.reason_codes import RC

__all__ = ['AlphaFloorInfeasibleError', 'AlphaInfeasibleError', 'BOUNDARY',
           'CalibrateError', 'CalibrationInputs', 'CalibrationReport', 'DRIFT',
           'GovernanceBudget', 'GovernanceBudgetTamperError', 'GridError', 'HARD',
           'HOOK_NAMES', 'HookRequiredError', 'INDICATORS', 'IndicatorRow',
           'MissingBudgetError',
           'OAT', 'PeriodCase', 'PeriodRun', 'SPEARMAN', 'WindowError', 'alpha_grid',
           'calibrate', 'calibration_window', 'candidate_doc', 'default_grid',
           'default_pipeline', 'governance_budget']

LAYER = 'L0b'
DRIFT = 'weight_drift'          # [L619]
BOUNDARY = 'boundary_ratio'     # [L620]
OAT = 'oat_flip_rate'           # [L621]
SPEARMAN = 'mean_spearman'      # [L622]
HARD = 'hard_constraints'       # [L623]
INDICATORS = (DRIFT, BOUNDARY, OAT, SPEARMAN, HARD)   # the [L617]-[L623] table in order
GRID_LOW = D('0.50')            # [L613]
GRID_STEP = D('0.05')           # [L613]
OAT_SCHEME = 'OAT_10'           # [L621] OAT +-10%
REVIEW_MAX = D('0.15')          # [L746] verbatim digest default of the OAT verdict
_HARNESS = 'FROZEN'             # in-memory backtest doc only, never persisted (INV-2)
CALIBRATED = 'CALIBRATED'       # [L1236] alpha_source of a calibrated candidate
# Governance keys, read from the signed config and never defaulted here (P-13, R-12).
BUDGET_KEYS = ('alpha_floor', 'drift_budget', 'boundary_budget', 'boundary_epsilon',
               'stable_max', 'divergence_threshold', 'min_dim_weight',
               'max_shift_from_ahp')
OPTIONAL_BUDGET_KEYS = ('min_metric_weight',)
# The four L0a capabilities, injected by the caller (ORCH-29 ruling 3): [L294] allows
# L0b -> L1-L5 only, so nothing here imports weights_combine and nothing defaults to one.
HOOK_NAMES = ('combine_fn', 'options_fn', 'entropy_window_fn', 'insufficient_sample_error')
# Where a governance key may live: K-15~K-20 in weight_construction ([L1752]-[L1757]),
# K-11 in sensitivity, divergence_threshold in triangulation; a flat config is accepted
# too. First hit wins, nothing is invented.
BUDGET_SECTIONS = (('eval_config', 'weight_construction'), ('eval_config', 'sensitivity'),
                   ('eval_config', 'triangulation'), ('eval_config',), ())


class CalibrateError(Exception):
    '''Base of every violation here. Not a ValueError: pydantic folds one into a
    ValidationError, so the guards keep their own type (as CombineError does).'''


class GridError(CalibrateError):
    '''alpha_grid is absent, empty, out of [0, 1] or not a sequence of numbers.'''


class WindowError(CalibrateError):
    '''The window is absent, shorter than two periods, or names an unknown period. Two is
    the floor because [L619] distances ADJACENT periods; one period has no adjacent pair
    and reporting drift 0 for it would be a silent invention.'''


class MissingBudgetError(CalibrateError):
    '''A governance parameter is absent from the signed config or still an unfilled slot.
    K-11 / K-15~K-20 are governance values (R-12): never defaulted here.'''


class GovernanceBudgetTamperError(CalibrateError):
    '''P-13 machine guard: the budget read at exit differs from the one read at entry.
    calibrate() has no write path, so the configuration moved underneath it -- RK-12
    (标定被凑结果) is refused, not reported.'''


class HookRequiredError(CalibrateError):
    '''A Step 5-7 input was not injected, or an indicator came back undefined;
    substituting a number would be a silent degradation (V-14).'''


class AlphaInfeasibleError(CalibrateError):
    '''[L631] / [L1072]: every candidate alpha violates at least one constraint. Carries
    the violation matrix and the registered reason code; cli.py maps the class name to
    exit code 7 (V-14).'''

    reason_code = RC.ALPHA_INFEASIBLE.value

    def __init__(self, message, violation_matrix=None, rows=()):
        super().__init__(message)
        self.violation_matrix = dict(violation_matrix or {})
        self.rows = tuple(rows)


class AlphaFloorInfeasibleError(CalibrateError):
    '''[L633]: alpha_floor itself is infeasible and the only remaining candidates sit below
    the governance floor. Taking one would widen K-15 silently, so the run stops (exit 7).'''

    reason_code = RC.ALPHA_FLOOR_INFEASIBLE.value

    def __init__(self, message, violation_matrix=None, rows=()):
        super().__init__(message)
        self.violation_matrix = dict(violation_matrix or {})
        self.rows = tuple(rows)


class _Frozen(BaseModel):
    '''Snapshot semantics, character for character the config of models.py.'''
    model_config = ConfigDict(frozen=True, extra='forbid')


class GovernanceBudget(_Frozen):
    '''The signed governance parameters of [L638] / K-11 / K-15~K-20, frozen at entry and
    quoted back in the report so an auditor sees the budget alpha* was chosen under (P-13,
    V-19). No field has a default (H-5, R-12).'''

    alpha_floor: Ratio                 # K-15 [L609] / [L633]
    drift_budget: Ratio                # K-16 [L619]
    boundary_budget: Ratio             # K-17 [L620]
    boundary_epsilon: Ratio            # K-18 [L620]
    stable_max: Ratio                  # K-11 [L621]
    divergence_threshold: Ratio        # [L622]
    min_dim_weight: Ratio              # K-19, handed to H-2
    max_shift_from_ahp: Ratio          # K-20, handed to H-5
    min_metric_weight: Ratio | None = None    # [L565] optional, handed to H-3

    def fingerprint(self) -> tuple:
        '''The ordered value tuple P-13 compares entry against exit.'''
        return tuple((key, str(q12(D(getattr(self, key)))))
                     for key in BUDGET_KEYS + OPTIONAL_BUDGET_KEYS
                     if getattr(self, key) is not None)

@dataclass(frozen=True)
class PeriodRun:
    '''What one window period yields under one candidate alpha: the Step 5-7 products the
    four indicators of [L619]-[L622] read -- composite_absolute feeds boundary_ratio,
    oat_flip_rate is sensitivity's OAT_10 rate, mean_rho triangulation's mean Spearman.
    Both rates are Decimal or None, never a float (V-9).'''

    period: str
    scores: ScoreFrame | None = None
    grades: GradeFrame | None = None
    composite_absolute: Mapping = field(default_factory=dict)
    oat_flip_rate: Decimal | None = None
    mean_rho: Decimal | None = None


@dataclass(frozen=True)
class PeriodCase:
    '''One window period's inputs: facts is Step 2's metric -> strategy -> value slice
    (SUSPECT rows dropped, [L1151] C-06), context carries the Step 1-4 frames every
    perturbation reuses ([L1016], RK-6), rules supplies the attainment_floor set of
    [L620].'''

    period: str
    facts: Mapping
    context: ScoringContext
    rules: grading.GradeRuleSet
    prev: GradeFrame | None = None
    streaks: Mapping | None = None
    prev_weight_version_id: str | None = None

    def attainment_floors(self) -> tuple:
        '''The distinct grade-rule floors of [L620], sorted, Decimal.'''
        return tuple(sorted({q12(D(row.attainment_floor)) for row in self.rules.rows}))


@dataclass(frozen=True)
class CalibrationInputs:
    '''The `inputs` argument of [L1072]. Everything the digest leaves without a value is
    required here: shift ([L540]), the per-period cases, the AHP snapshot, the metric
    dictionary and the run identity. pipeline defaults to default_pipeline();
    option_overrides forwards the two technical option keys whose digest defaults already
    live in the injected L0a tool ([L566]-[L567]), so they are not restated here.

    The four L0a capabilities are keyword-only REQUIRED injections (ORCH-29 ruling 3), one
    per L0a symbol this backtest used to reach for:
      combine_fn                 the [L558] combination of one candidate alpha, per period
      options_fn                 builds that candidate's option set from the signed budget
      entropy_window_fn          Step 2 of [L574]-[L580] over one window period
      insufficient_sample_error  the [L577] / [L634] degrade signal Step 2 raises, so the
                                 "which exception means degrade" policy stays here instead
                                 of being re-decided by every caller
    They live on CalibrationInputs, beside the pipeline callable that was already injected
    there, so calibrate(grid, window, inputs, config) keeps its frozen marshal. None of the
    four has a default: calibrate() raises HookRequiredError rather than importing one
    (V-14).'''

    hierarchy: Any        # weights_combine.AhpHierarchySnapshot: AHP snapshot DATA (ruling 1)
    metric_dict: Any
    shift: Any
    period_cases: Mapping
    run_id: str
    seed: int | None = None
    draft_header: Any = None        # weights_combine.DraftHeader, injected DATA (H-8: no clock)
    pipeline: Callable | None = None
    directions: Mapping | None = None
    oat_scheme: str = OAT_SCHEME
    option_overrides: Mapping = field(default_factory=dict)
    combine_fn: Callable = field(kw_only=True)
    options_fn: Callable = field(kw_only=True)
    entropy_window_fn: Callable = field(kw_only=True)
    insufficient_sample_error: type[BaseException] = field(kw_only=True)


class IndicatorRow(_Frozen):
    '''One row of the [L636] candidate alpha x indicator matrix. A None indicator was NOT
    evaluated: the alpha either sits below the governance band ([L609], key 1) or the
    H-1~H-5 gate rejected it first. Counts are int (H-4 / V-9); there is deliberately no
    aggregate score column ([L606]).'''

    alpha: Ratio
    evaluated: bool
    alpha_floor_ok: bool
    weight_drift: Ratio | None = None
    weight_drift_level1: Ratio | None = None
    weight_drift_effective: Ratio | None = None
    boundary_ratio: Ratio | None = None
    boundary_hits_by_period: dict[str, StrictInt] = {}
    assessed_by_period: dict[str, StrictInt] = {}
    oat_flip_rate: Ratio | None = None
    mean_spearman: Ratio | None = None
    hard_constraints: bool = False
    hard_violations: tuple[str, ...] = ()
    violations: tuple[str, ...] = ()
    feasible: bool = False


class CalibrationReport(_Frozen):
    '''CalibrationReport of [L636] / [L1072]: the full candidate x indicator matrix, alpha*,
    the binding constraints, the excluded alphas with their registered reason, the window
    period list, run_id and seed. to_alpha_basis() is the [L636] write into
    provenance.alpha_basis. No aggregate score column, no lambda ([L606]).'''

    alpha_star: Ratio
    rows: tuple[IndicatorRow, ...]
    feasible_alphas: tuple[Ratio, ...]
    excluded_alphas: dict[Ratio, str]
    binding_constraints: tuple[str, ...]
    non_monotonic: tuple[str, ...]
    notices: tuple[str, ...]
    prominent_notice: str | None = None
    window_periods: tuple[str, ...]
    run_id: str
    seed: StrictInt | None = None
    budget: GovernanceBudget
    calibration_skipped: bool = False

    def row(self, alpha) -> IndicatorRow:
        '''The matrix row of one candidate, looked up within 1e-12 (V-9).'''
        wanted = q12(D(alpha))
        for row in self.rows:
            if numeric.eq_tol(row.alpha, wanted, TOL):
                return row
        raise GridError('alpha ' + str(wanted) + ' is not a candidate of this report')

    def violation_matrix(self) -> dict:
        '''[L631]: alpha -> constraint -> bool for every evaluated candidate. An
        unevaluated alpha maps to None, which is a statement, not a zero.'''
        out = {}
        for row in self.rows:
            if not row.evaluated:
                out[str(row.alpha)] = None
                continue
            passed = {name: True for name in INDICATORS}
            for name in row.violations:
                passed[name] = False
            for cid in row.hard_violations:
                passed[HARD + ':' + cid] = False
            out[str(row.alpha)] = passed
        return out

    def to_alpha_basis(self) -> AlphaBasisSegment:
        '''[L636] / [L1239]-[L1240]: the whole report as the contract provenance segment;
        alpha keys are Ratio (never str) and seed stays nullable, per models.py.'''
        matrix = {}
        for row in self.rows:
            columns = {'evaluated': ONE if row.evaluated else ZERO,
                       'alpha_floor_ok': ONE if row.alpha_floor_ok else ZERO,
                       HARD: ONE if row.hard_constraints else ZERO}
            for name, value in ((DRIFT, row.weight_drift), (BOUNDARY, row.boundary_ratio),
                                (OAT, row.oat_flip_rate), (SPEARMAN, row.mean_spearman)):
                if value is not None:
                    columns[name] = q12(D(value))
            matrix[q12(D(row.alpha))] = columns
        return AlphaBasisSegment(
            candidate_alpha_matrix=matrix, alpha_star=q12(D(self.alpha_star)),
            binding_constraints=[str(name) for name in self.binding_constraints],
            excluded_alphas={q12(D(key)): str(code)
                             for key, code in self.excluded_alphas.items()},
            window_periods=[str(item) for item in self.window_periods],
            run_id=str(self.run_id),
            seed=(None if self.seed is None else int(self.seed)))


def _dec(value):
    '''str / int / Decimal in; a float only enters through numeric.from_float, so no
    float arithmetic happens after this point (V-9).'''
    if isinstance(value, float):
        return numeric.from_float(value)
    return D(value)


def _get(node, key):
    if node is None:
        return None
    if isinstance(node, Mapping):
        return node.get(key)
    return getattr(node, key, None)


def _lookup(config, key):
    '''First signed occurrence of a governance key across BUDGET_SECTIONS.'''
    for path in BUDGET_SECTIONS:
        node = config
        for step in path:
            node = _get(node, step)
        value = _get(node, key)
        if value is not None:
            return value, ('.'.join(path + (key,)) if path else key)
    return None, key


def governance_budget(config) -> GovernanceBudget:
    '''Read K-11 / K-15~K-20 from the signed configuration and freeze them. An absent key or
    an unfilled slot (config.is_placeholder_value) raises MissingBudgetError: the R-12 half
    of P-13, neither inventing a governance number nor relaxing one.'''
    values = {}
    for key in BUDGET_KEYS + OPTIONAL_BUDGET_KEYS:
        raw, path = _lookup(config, key)
        if raw is None:
            if key in OPTIONAL_BUDGET_KEYS:
                continue
            raise MissingBudgetError('governance parameter ' + path + ' is required and has '
                                     'no default (K-11 / K-15~K-20, [L638], R-12, P-13)')
        if is_placeholder_value(raw):
            raise MissingBudgetError('governance parameter ' + path + ' is still an unfilled '
                                     'slot (' + repr(raw) + '), unsigned ([L638], P-13)')
        values[key] = _dec(raw)
    return GovernanceBudget(**values)


def default_grid() -> tuple:
    '''[L613] verbatim: {0.50, 0.55, ..., 1.00}, 11 points, step 0.05, Decimal only (V-9).'''
    out, alpha = [], GRID_LOW
    while alpha <= ONE:
        out.append(q12(alpha))
        alpha = alpha + GRID_STEP
    return tuple(out)


def alpha_grid(grid) -> tuple:
    '''Normalise the `grid` argument of [L1072]: a non-empty ascending sequence of alphas in
    [0, 1], deduplicated within 1e-12. Absent or empty is an error, never a default.'''
    if grid is None:
        raise GridError('alpha_grid is a required input ([L613] offers default_grid())')
    if isinstance(grid, (str, bytes)) or not isinstance(grid, Sequence):
        raise GridError('alpha_grid must be a sequence of numbers, got ' + type(grid).__name__)
    alphas = []
    for item in grid:
        value = q12(_dec(item))
        if not ZERO <= value <= ONE:
            raise GridError('alpha must lie in [0, 1] ([L562]); got ' + str(value))
        if not any(numeric.eq_tol(value, seen, TOL) for seen in alphas):
            alphas.append(value)
    if not alphas:
        raise GridError('alpha_grid is empty')
    return tuple(sorted(alphas))


def calibration_window(window, inputs: CalibrationInputs) -> tuple:
    '''Normalise the `window` argument of [L1072]: the sorted [L636] \u7a97\u53e3\u671f\u6e05\u5355, each period of
    which the inputs must carry. Fewer than two periods is refused: [L619] measures ADJACENT
    periods and one period would silently report a drift of 0.'''
    if window is None:
        raise WindowError('the calibration window is required; no default period list (R-12)')
    if isinstance(window, (str, bytes)) or not isinstance(window, Sequence):
        raise WindowError('window must be a sequence of period ids, got ' + type(window).__name__)
    periods = tuple(sorted({str(item) for item in window}))
    if len(periods) < 2:
        raise WindowError('weight_drift of [L619] distances adjacent periods, so the window '
                          'needs >= 2; got ' + str(len(periods)))
    absent = tuple(item for item in periods if item not in inputs.period_cases)
    if absent:
        raise WindowError('the window names periods the inputs do not carry: ' + ', '.join(absent))
    return periods


def _lex_key(alpha, alpha_floor):
    '''The lexicographic order of [L608]-[L609]: governance band first, alpha second. Key 1
    is never traded against key 2 -- that is what makes this a lexicographic feasible set
    and not a weighted objective function.'''
    return (0 if D(alpha) >= D(alpha_floor) else 1, q12(D(alpha)))


def _options(alpha, budget: GovernanceBudget, inputs: CalibrationInputs):
    '''The option set of one candidate, built by the INJECTED options_fn. Only governance
    values already frozen in the budget and the caller's technical overrides are forwarded;
    nothing is defaulted here and no option type is imported here ([L294], ORCH-29 r3).'''
    kwargs = dict(inputs.option_overrides or {})
    if budget.min_metric_weight is not None:
        kwargs.setdefault('min_metric_weight', budget.min_metric_weight)
    return inputs.options_fn(alpha=q12(D(alpha)), alpha_floor=q12(D(budget.alpha_floor)),
                             min_dim_weight=q12(D(budget.min_dim_weight)),
                             max_shift_from_ahp=q12(D(budget.max_shift_from_ahp)), **kwargs)


def _effective(combined) -> dict:
    '''W_d * w_j, the weight that actually reaches a score and the quantity H-5 of [L598]
    measures; built from the public metric_trace columns only.'''
    return {m: q12(D(combined.dim_weights[t.dim_code]) * D(t.final_weight))
            for m, t in sorted(combined.metric_trace.items())}


def _window_drift(combined_by_period, periods):
    '''[L619] max_t || w(a,t) - w(a,t-1) ||_1, each period keeping ITS OWN entropy weights.
    [L619] names no layer, so the dimension layer and the effective W_d * w_j layer are both
    measured and the larger constrains, as step5_hard_checks already does for H-5.'''
    level1 = effective = ZERO
    previous = None
    for period in periods:
        combined = combined_by_period[period]
        current = (dict(combined.dim_weights), _effective(combined))
        if previous is not None:
            level1 = max(level1, numeric.l1_distance(current[0], previous[0]))
            effective = max(effective, numeric.l1_distance(current[1], previous[1]))
        previous = current
    return q12(max(level1, effective)), q12(level1), q12(effective)


def _window_maximum(values, periods, name):
    '''Window maximum of a per-period rate, refusing an undefined period (V-14).'''
    out = {}
    for period in periods:
        if values[period] is None:
            raise HookRequiredError(name + ' of period ' + period + ' is undefined; the '
                                    'calibration refuses to substitute a number (V-14)')
        out[period] = q12(D(values[period]))
    return q12(max(out.values())), out


def _window_boundary(runs, periods, floors_by_period, epsilon):
    '''[L620]: per period the share of assessed strategies whose composite_absolute lies
    within +- boundary_epsilon of ANY attainment_floor; the window maximum constrains. An
    empty denominator is undefined, not 0 ([L930], V-9). Returns (max, hits, assessed).'''
    hits, assessed, ratios = {}, {}, {}
    for period in periods:
        values = runs[period].composite_absolute
        count = total = 0
        for key in sorted(values):
            if values[key] is None:
                continue                       # not assessed -> out of the denominator
            total += 1
            if any(abs(D(values[key]) - floor) <= D(epsilon) for floor in floors_by_period[period]):
                count += 1
        ratio = safe_div(D(count), D(total), on_zero=None)
        if ratio is None:
            raise CalibrateError('boundary_ratio of period ' + period + ' has an empty '
                                 'denominator: no assessed strategy carries a '
                                 'composite_absolute ([L930] refuses 0/0)')
        hits[period], assessed[period], ratios[period] = int(count), int(total), q12(ratio)
    return q12(max(ratios.values())), hits, assessed


def candidate_doc(combined, case: PeriodCase, header) -> WeightVersionDoc:
    '''The in-memory weight document one candidate alpha is scored with. aggregate.compose
    refuses anything but FROZEN ([L1190]) and the L0a combine side may only emit DRAFT
    ([L600]); a candidate is neither, so this doc lives for one pipeline call and is never
    returned, persisted or handed to the reports tree (INV-2). Declared as a contract gap
    above. `header` is the injected weights_combine.DraftHeader DATA -- its type is not
    imported here ([L294], ORCH-29 r3) and its absence raises instead of being filled from
    a clock (H-8, V-14).'''
    if header is None:
        raise HookRequiredError('candidate_doc needs the injected weights_combine.DraftHeader '
                                '(CalibrationInputs.draft_header); H-8 forbids reading any of '
                                'its dates from a clock')
    return WeightVersionDoc(
        weight_version_id=str(header.weight_version_id), status=_HARNESS,
        effective_from=header.effective_from, effective_to=header.effective_to,
        level1_weights={d: q12(D(v)) for d, v in sorted(combined.dim_weights.items())},
        level2_weights={d: {m: q12(D(v)) for m, v in sorted(metrics.items())}
                        for d, metrics in sorted(combined.metric_weights.items())},
        approved_by=str(header.approved_by), approved_date=header.approved_date,
        provenance=None)


def default_pipeline(inputs: CalibrationInputs, config, budget: GovernanceBudget):
    '''The Step 5-7 re-run of [L615] on the real modules: aggregate.compose (Step 5),
    grading.assign (Step 6), sensitivity.run for the OAT_10 flip rate ([L621]) and
    triangulation.run for the mean Spearman ([L622]). Steps 1-4 are reused from the period
    context ([L1016], RK-6), never recomputed (INV-3).'''

    def grade_hook(case: PeriodCase):
        def hook(frame):
            graded = _grade(frame, case)
            return {(r.strategy_id, r.version_id, r.period): r.grade for r in graded.rows}
        return hook

    def run_case(case: PeriodCase, combined, alpha) -> PeriodRun:
        doc = candidate_doc(combined, case, inputs.draft_header)
        context = case.context.model_copy(
            update={'weight_version_id': doc.weight_version_id, 'seed': inputs.seed})
        scores = aggregate.compose(context.attainment, context.normalized, doc, config)
        grades = _grade(scores, case)
        base = context.model_copy(update={'score': scores, 'grade': grades})
        report = sensitivity.run(base, (inputs.oat_scheme,),
                                 {'stable_max': str(budget.stable_max),
                                  'review_max': str(REVIEW_MAX)},
                                 weights=doc, grade_fn=grade_hook(case))
        line = [item for item in report.by_scheme if item.scheme == inputs.oat_scheme]
        if not line:
            raise HookRequiredError('sensitivity produced no ' + inputs.oat_scheme + ' line, '
                                    'so oat_flip_rate of [L621] is undefined')
        if inputs.directions is None:
            raise HookRequiredError('mean_spearman of [L622] needs metric directions; none')
        tri = triangulation.run(scores, context.normalized, doc, config,
                                directions=inputs.directions)
        if tri is None or tri.mean_rho is None:
            raise HookRequiredError('triangulation gave no mean_rho, so mean_spearman of '
                                    '[L622] is unevaluable; never skipped silently (V-14)')
        return PeriodRun(period=case.period, scores=scores, grades=grades,
                         composite_absolute={(r.strategy_id, r.version_id, r.period):
                                             r.composite_absolute for r in scores.rows},
                         oat_flip_rate=D(line[0].overall_flip_rate), mean_rho=D(tri.mean_rho))

    return run_case


def _grade(frame, case: PeriodCase):
    '''Step 6 through grading.py (B3), never re-implemented here (R-7).'''
    return grading.assign(frame, case.context.attainment, case.context.evidence,
                          case.context.redline, case.prev, case.rules, streaks=case.streaks,
                          prev_weight_version_id=case.prev_weight_version_id)


def _entropy_snapshots(inputs, periods, budget):
    '''Step 2 of [L574]-[L580] once per window period, through the INJECTED
    entropy_window_fn (never re-implemented here: INV-3 / ORCH-03 / R-7). Each period is
    calibrated on ITS OWN facts, the
    [L619] 各期用自己的熵权组合（不冻结）; a period with no usable sample yields None and
    the injected combine_fn degrades it to alpha = 1 ([L577]). The probe option set carries
    alpha = alpha_floor because Step 2 reads only entropy_min_strategies and
    inactive_threshold from it, and alpha_floor is a signed governance value rather than a
    number picked here.'''
    probe = _options(budget.alpha_floor, budget, inputs)
    snapshots = {}
    for period in periods:
        facts = {period: {m: dict(v) for m, v in sorted(inputs.period_cases[period].facts.items())}}
        try:
            snapshots[period] = inputs.entropy_window_fn(facts, inputs.metric_dict, probe,
                                                         inputs.shift)
        except inputs.insufficient_sample_error:
            snapshots[period] = None        # the [L577] degrade: a label, never a zero
    return snapshots


def _evaluate(alpha, budget, periods, snapshots, inputs, pipeline, floors_by_period):
    '''One row of the [L636] matrix. Every constraint is evaluated with no short circuit so
    the [L631] matrix stays complete; only the H-1~H-5 gate stops the run early, because
    Step 5 already rejected this alpha before a score existed to perturb.'''
    base = {'alpha': q12(D(alpha)), 'evaluated': True, 'alpha_floor_ok': True}
    if D(alpha) < D(budget.alpha_floor):
        # Key 1 of the lexicographic order: below the governance band, never evaluated and
        # never traded against a better indicator value ([L609], K-15).
        return IndicatorRow(alpha=base['alpha'], evaluated=False, alpha_floor_ok=False)
    combined = {p: inputs.combine_fn(inputs.hierarchy, snapshots[p],
                                     _options(alpha, budget, inputs), CALIBRATED)
                for p in periods}
    drift, drift_l1, drift_eff = _window_drift(combined, periods)
    base.update(weight_drift=drift, weight_drift_level1=drift_l1,
                weight_drift_effective=drift_eff)
    hard = sorted({cid for p in periods for cid in combined[p].hard_checks.violations})
    if hard:
        return IndicatorRow(hard_constraints=False, hard_violations=tuple(hard),
                            violations=(HARD,), **base)
    runs = {p: pipeline(inputs.period_cases[p], combined[p], q12(D(alpha))) for p in periods}
    boundary, hits, assessed = _window_boundary(runs, periods, floors_by_period,
                                                budget.boundary_epsilon)
    oat = _window_maximum({p: runs[p].oat_flip_rate for p in periods}, periods, OAT)[0]
    rho_by = _window_maximum({p: runs[p].mean_rho for p in periods}, periods, SPEARMAN)[1]
    rho = q12(numeric.mean([rho_by[p] for p in periods]))
    violations = [name for name, broken in (
        (DRIFT, drift > D(budget.drift_budget)),                 # [L619] <= K-16
        (BOUNDARY, boundary > D(budget.boundary_budget)),        # [L620] <= K-17
        (OAT, oat > D(budget.stable_max)),                       # [L621] <= K-11
        (SPEARMAN, rho < D(budget.divergence_threshold)))        # [L622] >= threshold
        if broken]
    return IndicatorRow(boundary_ratio=boundary, boundary_hits_by_period=hits,
                        assessed_by_period=assessed, oat_flip_rate=oat, mean_spearman=rho,
                        hard_constraints=True, violations=tuple(violations),
                        feasible=not violations, **base)


def _monotonic_findings(rows, feasible_alphas):
    '''[L625]: the empirical monotonicity check. A counter-example is a WARNING carrying the
    full feasible list for a human choice, never an error (T-CAL-02). Two readings are
    reported: indicator trends across the evaluated band, and holes in the feasible set.'''
    band = sorted((row for row in rows if row.evaluated and row.alpha_floor_ok),
                  key=lambda row: D(row.alpha))
    findings = []
    for name, rises in ((DRIFT, True), (BOUNDARY, True), (SPEARMAN, False)):
        series = [(r.alpha, getattr(r, name)) for r in band if getattr(r, name) is not None]
        for left, right in zip(series, series[1:]):
            if (right[1] > left[1]) == rises and right[1] != left[1]:
                findings.append(name + (' rises from alpha ' if rises else ' falls from alpha ')
                                + str(left[0]) + ' to ' + str(right[0])
                                + ', against the [L625] expectation')
                break
    ordered = sorted(feasible_alphas, key=lambda item: D(item))
    positions = [i for alpha in ordered for i, row in enumerate(band)
                 if numeric.eq_tol(row.alpha, D(alpha), TOL)]
    holes = [right for left, right in zip(positions, positions[1:]) if right != left + 1]
    if holes:
        findings.append('the feasible set is not a contiguous interval (the [L625] \u6d1e): band '
                        'position(s) ' + ', '.join(str(h) for h in holes) + ' are infeasible '
                        'while larger alphas are feasible; all feasible alphas are '
                        + ', '.join(str(q12(D(a))) for a in ordered)
                        + ' and require a human choice')
    return tuple(findings)


def calibrate(grid, window, inputs, config) -> CalibrationReport:
    '''calibrate(grid, window, inputs, config) -> CalibrationReport ([L1072]). Traverses the
    WHOLE grid ([L625] \u4e0d\u5f97\u5047\u8bbe\u5355\u8c03), evaluates the five rows of [L617]-[L623] per candidate
    and returns the lexicographic minimum of the feasible set. Raises AlphaInfeasibleError
    ([L631]) and AlphaFloorInfeasibleError ([L633]), both exit code 7 in cli.py, plus
    MissingBudgetError / GovernanceBudgetTamperError (P-13), GridError, WindowError and
    HookRequiredError. Writes nothing (INV-2) and widens no governance budget ([L638]).'''
    budget = governance_budget(config)
    entered = budget.fingerprint()
    if not isinstance(inputs, CalibrationInputs):
        raise CalibrateError('inputs must be a CalibrationInputs, got ' + type(inputs).__name__)
    if inputs.shift is None:
        raise CalibrateError('shift (the [L540] epsilon) is required; no value is invented (R-12)')
    if not inputs.run_id:
        raise CalibrateError('run_id is required for the [L636] audit chain')
    for name in HOOK_NAMES:
        hook = getattr(inputs, name, None)
        if not callable(hook):
            raise HookRequiredError(
                name + ' is a required injection on CalibrationInputs: [L294] lets L0b '
                'import L1-L5 only, so the L0a combine capability is handed in by the caller '
                '(ORCH-29 ruling 3); got ' + type(hook).__name__ + '. Nothing is imported '
                'here to fill the hole and no indicator is silently skipped (V-14).')
    periods = calibration_window(window, inputs)
    candidates = list(alpha_grid(grid))
    floor = q12(D(budget.alpha_floor))
    if not any(numeric.eq_tol(a, floor, TOL) for a in candidates):
        # [L609]: alpha_floor is the lower endpoint of the governance band, so it stays a
        # candidate even when the configured grid steps over it.
        candidates = sorted(candidates + [floor])
    sub_floor = tuple(a for a in candidates if D(a) < D(floor))
    band = tuple(sorted((a for a in candidates if D(a) >= D(floor)), key=D))
    pipeline = inputs.pipeline or default_pipeline(inputs, config, budget)
    snapshots = _entropy_snapshots(inputs, periods, budget)
    if all(snapshots[p] is None for p in periods):
        # [L634]: no usable entropy sample anywhere in the window -> skip the calibration
        # entirely, alpha = 1, prominently labelled. Never silent.
        return CalibrationReport(
            alpha_star=ONE, rows=(), feasible_alphas=(ONE,), excluded_alphas={},
            binding_constraints=(), non_monotonic=(),
            notices=(RC.ENTROPY_INSUFFICIENT_SAMPLE.value, RC.ALPHA_PURE_AHP.value),
            prominent_notice='[L634] \u6807\u5b9a\u7a97\u53e3\u5185\u65e0\u53ef\u7528\u71b5\u6743\u6837\u672c\uff1a\u5df2\u8df3\u8fc7\u6807\u5b9a\uff0c\u76f4\u63a5\u53d6 alpha = 1\uff08\u7b49\u4ef7\u7eaf '
                             'AHP\uff09\u5e76\u5728\u62a5\u544a\u9996\u5c4f\u663e\u8457\u6807\u6ce8\u3002\u7b7e\u8ba4\u524d\u987b\u4eba\u5de5\u786e\u8ba4\u6807\u5b9a\u7a97\u53e3\u3002',
            window_periods=periods, run_id=inputs.run_id, seed=inputs.seed, budget=budget,
            calibration_skipped=True)
    floors = {p: inputs.period_cases[p].attainment_floors() for p in periods}
    rows = [_evaluate(a, budget, periods, snapshots, inputs, pipeline, floors)
            for a in sorted(candidates, key=lambda a: _lex_key(a, floor))]
    rows.sort(key=lambda row: _lex_key(row.alpha, floor))
    by_alpha = {q12(D(row.alpha)): row for row in rows}
    feasible = [q12(D(row.alpha)) for row in rows if row.feasible]
    matrix = {str(row.alpha): row.violations for row in rows if row.evaluated}
    if not feasible:
        rendered = '; '.join(str(a) + ' -> ' + (', '.join(by_alpha[q12(D(a))].violations)
                                               or 'feasible') for a in band)
        tail = ' Violation matrix ([L631]): ' + rendered
        floor_row = by_alpha.get(floor)
        if sub_floor and floor_row is not None and not floor_row.feasible:
            raise AlphaFloorInfeasibleError(
                'alpha_floor = ' + str(floor) + ' is itself infeasible and the remaining '
                'candidates (' + ', '.join(str(q12(D(a))) for a in sub_floor) + ') sit below '
                'the governance floor of [L609] / K-15. Taking one would widen alpha_floor '
                'silently, which [L633] forbids (' + RC.ALPHA_FLOOR_INFEASIBLE.value + ').'
                + tail, violation_matrix=matrix, rows=tuple(rows))
        raise AlphaInfeasibleError(
            'no candidate alpha satisfies every stability constraint of [L617]-[L623] under '
            'the SIGNED governance budget ' + str(entered) + '; the budgets are NOT widened '
            'to produce a result ([L638], P-13, ' + RC.ALPHA_INFEASIBLE.value + ').' + tail,
            violation_matrix=matrix, rows=tuple(rows))
    alpha_star = min(feasible, key=lambda a: _lex_key(a, floor))
    binding = sorted({name for a in band if D(a) < D(alpha_star)
                      for name in by_alpha[q12(D(a))].violations})
    excluded = {q12(D(row.alpha)): (RC.ALPHA_FLOOR_INFEASIBLE.value
                                    if not row.alpha_floor_ok else RC.ALPHA_INFEASIBLE.value)
                for row in rows if not row.feasible}
    notices, prominent = [], None
    if sub_floor and numeric.eq_tol(alpha_star, floor, TOL):
        # [L633]: the statistical minimum sat below the governance floor, so the floor was
        # taken -- and it was verified feasible above, otherwise this run had raised.
        notices.append(RC.ALPHA_FLOOR_APPLIED.value)
    if numeric.eq_tol(alpha_star, ONE, TOL):
        notices.append(RC.ALPHA_PURE_AHP.value)
        prominent = ('[L632] \u5728\u5f53\u524d\u7a33\u5b9a\u6027\u9884\u7b97\u4e0b\uff0c\u6570\u636e\u9a71\u52a8\u6210\u5206\u65e0\u6cd5\u5f15\u5165\uff0c\u672c\u671f\u6743\u91cd\u7b49\u4ef7\u4e8e\u7eaf AHP'
                     '\uff08alpha* = 1\uff09\u3002\u8fd9\u672c\u8eab\u662f\u6709\u4ef7\u503c\u7684\u7ed3\u8bba\uff1a\u6307\u6807\u6570\u636e\u7684\u79bb\u6563\u7ed3\u6784\u5c1a\u4e0d\u8db3\u4ee5\u652f\u6491\u5ba2\u89c2\u8d4b\u6743\u3002'
                     '\u987b\u5728\u62a5\u544a\u9996\u5c4f\u58f0\u660e\u3002')
    non_monotonic = _monotonic_findings(rows, feasible)
    if non_monotonic:
        notices.append(RC.NON_MONOTONIC_WARNING.value)
    if any(snapshots[p] is None for p in periods):
        notices.append(RC.ENTROPY_PERIOD_SKIPPED.value)
    report = CalibrationReport(
        alpha_star=q12(D(alpha_star)), rows=tuple(rows),
        feasible_alphas=tuple(sorted(feasible, key=D)), excluded_alphas=excluded,
        binding_constraints=tuple(binding), non_monotonic=non_monotonic,
        notices=tuple(dict.fromkeys(notices)), prominent_notice=prominent,
        window_periods=periods, run_id=inputs.run_id, seed=inputs.seed, budget=budget)
    exited = governance_budget(config).fingerprint()
    if exited != entered:
        raise GovernanceBudgetTamperError(
            'the governance budget changed while calibrating (entry ' + str(entered) + ', exit '
            + str(exited) + '); calibrate() has no write path into K-11 / K-15~K-20, so the '
            'configuration moved underneath it (P-13, RK-12, '
            + RC.ALPHA_FLOOR_INFEASIBLE.value + ')')
    return report
