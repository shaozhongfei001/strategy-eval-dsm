'''dsm.weights_combine -- 档 2: AHP x entropy combined weights (SDD 2.4.3 [L556]-[L603]).

Layer L0a, offline annual tool. The six steps of [L570]-[L600] run in the order the
SDD writes them, and that order is part of the specification:
  Step 1  AHP weights + CR gate ([L572]-[L573]): CR >= 0.1 terminates here, before a
          single entropy number exists. AHP is the premise, not an option.
  Step 2  entropy weights over the calibration window ([L574]-[L580]), computed by
          dsm.entropy (L1), the ONE implementation (ORCH-03), never re-implemented
          here. Periods below entropy_min_strategies are dropped HERE, so the median
          and drift of [L579]-[L580] cover surviving periods only and Step 3 sees an
          already trimmed window.
  Step 3  INACTIVE fallback ([L581]-[L587]): w_j(combined) = w_j(AHP) verbatim.
  Step 4  alpha mixing + renormalisation of the NON-fallback metrics ([L588]-[L592]).
  Step 5  hard checks H-1..H-5 ([L593]-[L599]): a violation marks the alpha
          infeasible, it is never softened into a warning.
  Step 6  WeightVersionDoc, status = DRAFT ([L600]).
Step 3 before Step 4 is why a fallback metric is never scaled again: [L590]
redistributes only the RESIDUAL mass 1 - sum(w_j(AHP) of the fallback metrics of that
dimension) over the non-fallback ones. That is the only reading of [L588]-[L590] under
which P-14 (sum w_j = 1 per dimension) and P-15 (a fallback metric keeps its AHP
weight exactly, before the dimension renormalisation) both hold; scaling it with the
others would halve it at alpha 0.5, exactly the dilution [L585]-[L586] forbids.
INV-1 / ORCH-29: no L0 module is imported, and no L1-L5 business module either.
[L286] reads "L0a -> 无内部依赖（独立命令行工具）", so the "消费 L0a" of [L278] can only
mean consuming the L0a PRODUCT -- AHP snapshot DATA the caller hands in -- and never the
L0a module: that is the one reading under which [L276], [L278] and [L286] all hold, and
[L282] 拆分后依赖仍严格单向 confirms it. Step 1 therefore takes an AhpHierarchySnapshot
(declared here, pure data) and run_six_steps takes the elicitation itself as an injected
callable; the L0a -> L0a edge belongs to the caller, which owns both sides. dsm.entropy
(L1) stays the authorised exception (ORCH-03, SDD 2.4.2 六步两个计算者共用同一实现), and
models / reason_codes / numeric are the L1 contract and primitive layer this tool
publishes into. A missing injection raises; it never falls back to an import (V-14).
V-9: counts are int, every ratio is a Decimal built by numeric.D (floats refused
there), every division goes through safe_div with an explicit on_zero, every published
number passes q12, no float is accumulated. H-8: no clock, no randomness, mappings are
traversed sorted and dates are injected. Status can only be DRAFT ([L600], [L1071]), as
in weights_ahp (T-AHP-06).
'''
from __future__ import annotations

from datetime import date
from decimal import Decimal, localcontext
from typing import Callable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.entropy import entropy_weights
from dsm.models import (AhpSegment, CombineSegment, EntropySegment, MetricWeightComparison,
                        Ratio, WeightProvenance, WeightVersionDoc)
from dsm.numeric import D, ONE, TOL, ZERO, q12, safe_div
from dsm.reason_codes import RC

__all__ = ['AhpHierarchySnapshot', 'AhpInputError', 'AhpLayer', 'AhpLevelSnapshot',
           'AlphaFloorError', 'AlphaInfeasibleError', 'CombinedWeights', 'CombineError',
           'CombineOptions', 'ConsistencyGateError',
           'DraftHeader', 'EntropyInsufficientSample', 'EntropySnapshot', 'FrozenStatusError',
           'HardCheckReport', 'MetricWeightTrace', 'MixedWeights', 'assert_feasible',
           'build_draft', 'calibrate_entropy_window', 'combine', 'freeze',
           'run_six_steps', 'step1_ahp_gate', 'step3_inactive_fallback',
           'step4_combine_normalize', 'step5_hard_checks', 'step6_draft']

LAYER = 'L0a'
DRAFT = 'DRAFT'
WORK_PREC = 40                    # internal alpha mixing; published values pass q12
CR_THRESHOLD = D('0.1')           # [L573] / [L597] H-4, the gate weights_ahp uses
STEP1 = 'STEP1_AHP'
STEP2 = 'STEP2_ENTROPY_WINDOW'
STEP3 = 'STEP3_INACTIVE_FALLBACK'
STEP4 = 'STEP4_COMBINE_NORMALIZE'
STEP5 = 'STEP5_HARD_CHECKS'
STEP6 = 'STEP6_DRAFT'
STEP_IDS = (STEP1, STEP2, STEP3, STEP4, STEP5, STEP6)  # [L570]-[L600]: the order is the spec
HARD_CHECK_IDS = ('H-1', 'H-2', 'H-3', 'H-4', 'H-5')   # [L594]-[L598]
KIND_COMBINED = 'AHP_ENTROPY_COMBINED'                 # [L1231]
KIND_AHP_ONLY = 'AHP_ONLY'                             # [L1231], the [L577] degrade
SUSPECT = 'SUSPECT'                                    # [L1151] C-06, dropped by the caller


class CombineError(Exception):
    '''Base of every violation here. Not a ValueError: pydantic folds a ValueError from
    a validator into a ValidationError, and the guards must keep their own type.'''


class FrozenStatusError(CombineError):
    '''[L600] / [L1071]: this tool writes DRAFT and nothing else.'''


class AlphaFloorError(CombineError):
    '''[L562]: alpha lives in [alpha_floor, 1]; K-15 is never silently widened.'''


class ConsistencyGateError(CombineError):
    '''[L573] / [L597] H-4: CR >= 0.1 terminates Step 1, nothing is combined.'''


class AhpInputError(CombineError):
    '''The AHP product handed to Step 1 is not a usable two-level hierarchy.'''


class EntropyInsufficientSample(CombineError):
    '''[L577] / [L1071]: every period of the window was dropped. Raised by Step 2, caught
    by run_six_steps, which degrades to alpha = 1 and labels the draft.'''


class AlphaInfeasibleError(CombineError):
    '''[L593] / [L1071]: H-1..H-5 reject this alpha. Thrown by the gate the calibration
    side calls; combine() returns the verdict so a grid can scan alphas.'''

    exit_code = 7                 # [L1072] owns the exit code; this gate only names it


class _Frozen(BaseModel):
    '''Snapshot semantics, character for character the config of models.py.'''

    model_config = ConfigDict(frozen=True, extra='forbid')


def _refuse_non_draft(data, who):
    '''Shared body of the status guards, the same discipline as weights_ahp.'''
    if isinstance(data, Mapping):
        status = data.get('status', DRAFT)
        if status != DRAFT:
            raise FrozenStatusError(
                who + ' produces status DRAFT only ([L600], [L1071]); got ' + str(status)
                + '. Sign-off is a human act on WeightVersionDoc (' + RC.AHP_DRAFT_ONLY.value
                + ').')
    return data


class CombineOptions(_Frozen):
    '''[L561]-[L568] verbatim: field names, defaults and the K-15/K-19/K-20 tags.'''

    alpha: Ratio                                    # [L562] business judgement share
    alpha_floor: Ratio = D('0.5')                   # [L563] K-15
    min_dim_weight: Ratio                           # [L564] K-19
    min_metric_weight: Ratio | None = None          # [L565] optional
    entropy_min_strategies: int = 10                # [L566]
    inactive_threshold: Ratio = D('0.0001')         # [L567] 1e-4
    max_shift_from_ahp: Ratio = D('0.30')           # [L568] K-20, used by H-5

    @model_validator(mode='after')
    def _alpha_in_governance_band(self):
        '''[L562]: alpha is in [alpha_floor, 1]. Refused, never relaxed -- raising a
        too-small alpha to the floor here would be the silent widening of the governance
        budget ALPHA_FLOOR_INFEASIBLE forbids (T-CMB-04).'''
        if not ZERO <= self.alpha_floor <= ONE or self.alpha > ONE:
            raise AlphaFloorError('alpha must lie in [alpha_floor, 1] ([L562]); got alpha = '
                                  + str(self.alpha) + ', alpha_floor = ' + str(self.alpha_floor))
        if self.alpha < self.alpha_floor:
            raise AlphaFloorError('alpha = ' + str(self.alpha) + ' is below alpha_floor = '
                                  + str(self.alpha_floor) + ' ([L562], K-15); the governance '
                                  'budget is never silently widened ('
                                  + RC.ALPHA_FLOOR_INFEASIBLE.value + ')')
        if not (ZERO <= self.min_dim_weight <= ONE and self.inactive_threshold >= ZERO
                and self.max_shift_from_ahp >= ZERO
                and (self.min_metric_weight is None or self.min_metric_weight >= ZERO)):
            raise CombineError('min_dim_weight / min_metric_weight / inactive_threshold / '
                               'max_shift_from_ahp must be non-negative ([L564]-[L568])')
        if self.entropy_min_strategies < 2:
            raise CombineError('entropy_min_strategies must be >= 2 ([L542] divides by ln n), '
                               'got ' + str(self.entropy_min_strategies))
        return self


# --- container types declared locally: models.py has none of them, and a package
# --- declares its own containers instead of editing the frozen contract layer. ---
class AhpLevelSnapshot(_Frozen):
    '''The Step-1 input for ONE comparison level: the AHP derivation carried as DATA.

    Every field name is copied verbatim from dsm.models.AhpSegment ([L1232]-[L1233]),
    which is exactly the keyword set the AHP tool publishes through its
    segment_payload(); `findings` ([L515] METHOD_MISMATCH) is the one column AhpSegment
    does not carry and Step 1 needs for the AHP_METHOD_MISMATCH notice. The CALLER
    builds one out of the AHP snapshot, per level:

        AhpLevelSnapshot.from_payload(result.segment_payload(), result.findings)

    ORCH-29 ruling 1: [L278] 消费 L0a is the consumption of the L0a PRODUCT, because
    [L276] and [L286] make L0a 无内部依赖 -- so this module imports no L0a module and
    offers no fallback to one (V-14). Nothing is quantised beyond numeric.D, so the
    Decimals the CR gate of [L573] reads are the published ones, never a re-rounded
    copy of them (V-9).'''

    comparison_matrices: dict[str, dict[str, dict[str, Ratio]]]  # [L1232] expert x item x item
    lambda_max: Ratio                                            # [L1232]
    ci: Ratio                                                    # [L1232] consistency index
    ri: Ratio                                                    # [L1232] random index
    cr: Ratio                                                    # [L1232] the [L573] gate
    expert_count: int                                            # [L1232] a count -> int
    interview_dates: tuple[date, ...]                            # [L1232] injected (H-8)
    weights_geometric: dict[str, Ratio]                          # [L1233] the published set
    weights_eigenvector: dict[str, Ratio]                        # [L1233] the cross check
    max_method_gap: Ratio                                        # [L1233]
    findings: tuple[str, ...] = ()                               # [L515] METHOD_MISMATCH

    @classmethod
    def from_payload(cls, payload: Mapping, findings: Sequence = ()) -> AhpLevelSnapshot:
        '''One level out of an AHP snapshot payload (the AhpSegment keyword set) plus that
        level's findings. Data in, data out: no L0a module is reached for (ORCH-29
        ruling 1), and an unusable payload raises instead of being padded with invented
        columns (R-12, V-14).'''
        if not isinstance(payload, Mapping):
            raise AhpInputError('the AHP snapshot payload must be a mapping carrying the '
                                'AhpSegment columns ([L1232]-[L1233]); got '
                                + type(payload).__name__)
        return cls(**dict(payload), findings=tuple(str(item) for item in findings))

    def segment_payload(self) -> dict:
        '''Exactly the keyword set of dsm.models.AhpSegment, nothing more, so step6_draft
        hands it straight to the contract layer ([L1232]-[L1233]).'''
        return {
            'comparison_matrices': {expert: {i: dict(row) for i, row in sorted(cells.items())}
                                    for expert, cells
                                    in sorted(self.comparison_matrices.items())},
            'lambda_max': self.lambda_max,
            'ci': self.ci,
            'ri': self.ri,
            'cr': self.cr,
            'expert_count': int(self.expert_count),
            'interview_dates': list(self.interview_dates),
            'weights_geometric': dict(self.weights_geometric),
            'weights_eigenvector': dict(self.weights_eigenvector),
            'max_method_gap': self.max_method_gap,
        }


class AhpHierarchySnapshot(_Frozen):
    '''The Step-1 input in full (Step 7 of [L520], carried as a snapshot): the dimension
    layer W_d(AHP) plus one metric layer w_j(AHP) per dimension. H-1 of [L594] needs
    BOTH levels, which is why step1_ahp_gate accepts this carrier and nothing else. The
    caller builds it out of the AHP snapshot payloads; this module imports no L0a module
    and never falls back to one (ORCH-29 ruling 1, [L286], V-14).'''

    dimension: AhpLevelSnapshot
    metrics_by_dim: dict[str, AhpLevelSnapshot]


class EntropySnapshot(_Frozen):
    '''Step 2 product ([L579]-[L580]) and the `entropy` argument of [L558]. The
    contract-side shape is EntropySegment, which to_segment() fills. INV-3 / [L535]:
    a value snapshot -- no callable, no metric -> weight mapping a scoring run could
    consume, so aggregate.py can never recompute entropy out of it (T-CMB-06).'''

    calibration_periods: tuple[str, ...]               # [L1234] usable periods, sorted
    excluded_periods: dict[str, str]                   # [L1235] period -> registered code
    strategy_count_by_period: dict[str, int]           # n_t of [L575], a count -> int
    per_period_entropy: dict[str, dict[str, Ratio]]    # [L1234] w_j(entropy, t)
    median_entropy: dict[str, Ratio]                   # [L579] median_t w_j(entropy, t)
    drift_by_metric: dict[str, Ratio]                  # [L580] max_t - min_t
    median_d_j: dict[str, Ratio]                       # window d_j ([L543]), Step 3 input
    shift: Ratio                                       # [L540] technical epsilon, injected
    entropy_emitted: bool                              # False -> [L545] no entropy weight

    def to_segment(self, inactive_fallback_metrics: Sequence) -> EntropySegment:
        '''[L1234]-[L1235]: copy the snapshot into the contract provenance segment.'''
        return EntropySegment(
            calibration_periods=list(self.calibration_periods),
            per_period_entropy={p: dict(self.per_period_entropy[p])
                                for p in self.calibration_periods},
            median_entropy=dict(self.median_entropy),
            drift_by_metric=dict(self.drift_by_metric),
            inactive_fallback_metrics=[str(m) for m in inactive_fallback_metrics],
            excluded_periods=dict(self.excluded_periods))


class MetricWeightTrace(_Frozen):
    '''The four-column per-metric comparison, every column traceable ([L1237]):
    1 ahp_weight (AHP side), 2 entropy_weight (entropy side), 3 combined_raw_weight
    (alpha mixed, BEFORE the dimension renormalisation of [L590] -- the value P-15
    compares against), 4 final_weight (AFTER renormalisation, what enters
    level2_weights). is_fallback is the disclosure column of [L1237].'''

    metric_id: str
    dim_code: str
    ahp_weight: Ratio
    entropy_weight: Ratio | None = None
    combined_raw_weight: Ratio
    final_weight: Ratio
    is_fallback: bool
    fallback_reason: str | None = None


class HardCheckReport(_Frozen):
    '''Step 5 ([L593]-[L599]). results carries one bool per constraint id; a False is
    a rejection, never a warning, and violations names the rejected ids. The observed
    quantities stay beside the verdict so H-1..H-5 remain re-checkable.'''

    results: dict[str, bool]
    violations: tuple[str, ...]
    reasons: tuple[str, ...]                 # registered codes attached to the violations
    l1_shift_from_ahp: Ratio                 # the H-5 quantity of [L598]
    min_dim_observed: Ratio                  # H-2 evidence
    min_metric_observed: Ratio               # H-3 evidence
    cr_max: Ratio                            # H-4 evidence
    cr_by_level: dict[str, Ratio]            # every AHP level behind the gate


class AhpLayer(_Frozen):
    '''Step 1 product: the AHP weights of both levels, behind their CR gate.'''

    dim_weights: dict[str, Ratio]                    # W_d(AHP), sums to 1
    metric_weights: dict[str, dict[str, Ratio]]      # w_j(AHP) per dim, sums to 1
    dim_of_metric: dict[str, str]
    cr_max: Ratio
    cr_by_level: dict[str, Ratio]
    findings: tuple[str, ...]
    dim_segment: dict            # AhpSegment payload of the dimension level ([L1232])


class MixedWeights(_Frozen):
    '''Step 4 product ([L588]-[L592]). The dimension layer keeps its own four columns:
    ahp.dim_weights / dim_entropy_weight / dim_raw_weight / dim_weights.'''

    alpha_used: Ratio
    dim_weights: dict[str, Ratio]
    dim_entropy_weight: dict[str, Ratio]
    dim_raw_weight: dict[str, Ratio]
    metric_weights: dict[str, dict[str, Ratio]]
    metric_trace: dict[str, MetricWeightTrace]
    comparison_by_metric: dict[str, MetricWeightComparison]


class CombinedWeights(_Frozen):
    '''combine() output ([L558]). models.py declares no CombinedWeights, so the
    contract-shaped part (comparison_by_metric, hard_check_results) is what
    step6_draft copies into CombineSegment; the rest stays here for the calibration
    side and the reports.'''

    status: Literal['DRAFT'] = DRAFT
    alpha: Ratio
    alpha_source: Literal['CALIBRATED', 'MANUAL'] = 'MANUAL'
    dim_weights: dict[str, Ratio]
    dim_entropy_weight: dict[str, Ratio]
    dim_raw_weight: dict[str, Ratio]
    metric_weights: dict[str, dict[str, Ratio]]
    metric_trace: dict[str, MetricWeightTrace]
    comparison_by_metric: dict[str, MetricWeightComparison]
    hard_checks: HardCheckReport
    feasible: bool
    inactive_fallback_metrics: tuple[str, ...]
    entropy_sufficient: bool
    kind: Literal['AHP_ENTROPY_COMBINED', 'AHP_ONLY']
    notices: tuple[str, ...] = ()
    prominent_notice: str | None = None
    ahp: AhpLayer
    entropy: EntropySnapshot | None = None
    step_trace: tuple[str, ...] = ()

    @model_validator(mode='before')
    @classmethod
    def _refuse_frozen_status(cls, data):
        return _refuse_non_draft(data, 'weights_combine')


class DraftHeader(_Frozen):
    '''What Step 6 needs besides the weights. Every date is injected by the caller
    (H-8: no clock here), which is why build_draft takes one argument more than the
    [L559] sketch.'''

    weight_version_id: str
    approved_by: str
    approved_date: date
    effective_from: date
    effective_to: date
    alpha_source: Literal['CALIBRATED', 'MANUAL'] = 'MANUAL'
    calibration_report_ref: str | None = None       # [L1236] nullable, never invented
    whatif_run_id: str | None = None                # [L1241]
    interview_dates: tuple[date, ...] = ()          # [L1232] injected, no clock


def _cell(row, name):
    return row[name] if isinstance(row, Mapping) else getattr(row, name)


def _split_matrices(ahp_matrices):
    '''ahp_matrices of [L559]: {dimension: {expert: A}, metrics_by_dim: {dim: {expert: A}}}.'''
    if not isinstance(ahp_matrices, Mapping):
        raise AhpInputError('ahp_matrices must be a mapping with the keys dimension '
                            'and metrics_by_dim')
    dimension = ahp_matrices.get('dimension')
    metrics = ahp_matrices.get('metrics_by_dim')
    if not isinstance(dimension, Mapping) or not isinstance(metrics, Mapping):
        raise AhpInputError('ahp_matrices needs dimension: {expert: matrix} and '
                            'metrics_by_dim: {dim: {expert: matrix}} ([L520], [L559])')
    return dimension, metrics


def _require_unit_sum(weights: Mapping, label: str) -> None:
    total = ZERO
    for key in sorted(weights):
        total = total + D(weights[key])
    if not numeric.eq_tol(total, ONE, TOL):
        raise AhpInputError(label + ' must sum to 1 within 1e-12 ([L594]), got ' + str(q12(total)))


# --- Step 1: [L572]-[L573] -------------------------------------------------
def step1_ahp_gate(ahp) -> AhpLayer:
    '''Step 1: take the AHP weights and re-run the CR gate before anything else.
    [L558] annotates the argument as AhpResult; H-1 of [L594] needs BOTH the dimension
    layer W_d and the metric layer w_j, so the accepted product is the Step 7 hierarchy
    of [L520] carried as DATA -- an AhpHierarchySnapshot whose .dimension and every
    .metrics_by_dim[d] is an AhpLevelSnapshot (ORCH-29 ruling 1: [L278] consumes the L0a
    product, [L286] forbids importing the L0a module). weights_geometric of [L514] is the
    published set; the eigenvector set stays in provenance as the cross check and
    resurfaces as an AHP_METHOD_MISMATCH notice when the two diverge.'''
    if not isinstance(ahp, AhpHierarchySnapshot):
        raise AhpInputError('step1_ahp_gate needs an AhpHierarchySnapshot (dimension layer '
                            'plus one metric layer per dimension) for H-1 of [L594]; got '
                            + type(ahp).__name__ + '. The AHP side crosses this boundary as '
                            'snapshot DATA the caller injects (ORCH-29 ruling 1, [L278] / '
                            '[L286]): AhpLevelSnapshot.from_payload(result.segment_payload(), '
                            'result.findings) per level. No import repairs a missing '
                            'injection (V-14).')
    levels = {'DIMENSION': ahp.dimension}
    for dim_id in sorted(ahp.metrics_by_dim):
        levels[dim_id] = ahp.metrics_by_dim[dim_id]
    cr_by_level = {}
    findings = []
    cr_max = ZERO
    for name in sorted(levels):
        cr_by_level[name] = q12(D(levels[name].cr))
        cr_max = max(cr_max, D(levels[name].cr))
        for item in levels[name].findings:
            if item not in findings:
                findings.append(item)
    if cr_max >= CR_THRESHOLD:
        raise ConsistencyGateError('CR = ' + str(q12(cr_max)) + ' >= ' + str(CR_THRESHOLD)
                                   + ': Step 1 terminates, nothing is combined ([L573], H-4 '
                                   + '[L597], ' + RC.AHP_CR_FAILED.value + ')')
    dim_weights = {d: q12(D(ahp.dimension.weights_geometric[d]))
                   for d in sorted(ahp.dimension.weights_geometric)}
    metric_weights = {}
    dim_of_metric = {}
    for dim_id in sorted(ahp.metrics_by_dim):
        weights = ahp.metrics_by_dim[dim_id].weights_geometric
        metric_weights[dim_id] = {m: q12(D(weights[m])) for m in sorted(weights)}
        for metric_id in sorted(weights):
            if metric_id in dim_of_metric:
                raise AhpInputError('metric ' + metric_id + ' appears in two dimensions')
            dim_of_metric[metric_id] = dim_id
    if sorted(dim_weights) != sorted(metric_weights):
        raise AhpInputError('the dimension layer compares ' + str(sorted(dim_weights))
                            + ' but the metric layer covers ' + str(sorted(metric_weights)))
    _require_unit_sum(dim_weights, 'the AHP dimension layer')
    for dim_id in sorted(metric_weights):
        _require_unit_sum(metric_weights[dim_id], 'the AHP metric layer of ' + dim_id)
    return AhpLayer(dim_weights=dim_weights, metric_weights=metric_weights,
                    dim_of_metric=dim_of_metric, cr_max=q12(cr_max), cr_by_level=cr_by_level,
                    findings=tuple(sorted(findings)),
                    dim_segment=ahp.dimension.segment_payload())


# --- Step 2: [L574]-[L580]; the six entropy steps stay in dsm.entropy (L1) --
def calibrate_entropy_window(facts_history, metric_dict, opts, shift,
                             metric_ids=None) -> EntropySnapshot:
    '''Step 2: per-period entropy weights over the calibration window.

    facts_history is period -> metric_id -> strategy_id -> value; metric_dict is a
    sequence of MetricDictRow (or dicts) or a mapping keyed by metric_id. Redline
    metrics stay out of the entropy weights ([L1140], as recorded on
    models.MetricDictRow.is_redline) and return in Step 3 as AHP fallbacks, because a
    metric with no entropy weight has nothing to be mixed with. `shift` is the [L540]
    technical epsilon: the digest states no value, so it is an input, never a literal.

    Per period only the strategies carrying EVERY entropy metric form the matrix (a
    missing fact is a missing row, not a zero, [L1145]); n_t is that count and
    n_t < entropy_min_strategies drops the period with ENTROPY_PERIOD_SKIPPED
    ([L575]). A period where dsm.entropy emits no weight at all ([L545], every metric
    zero variation) is dropped too. When nothing survives, EntropyInsufficientSample
    is raised ([L577]) and build_draft degrades to alpha = 1 with a prominent label.'''
    rows = list(metric_dict.values()) if isinstance(metric_dict, Mapping) else list(metric_dict)
    if not rows:
        raise CombineError('metric_dict is empty')
    refs = {str(_cell(r, 'metric_id')): (int(_cell(r, 'direction')), bool(_cell(r, 'is_redline')))
            for r in rows}
    if metric_ids is None:
        metric_ids = sorted(m for m in refs if not refs[m][1])
    metric_ids = sorted(metric_ids)
    if not metric_ids:
        raise CombineError('the entropy window needs at least one non-redline metric ([L1140])')
    directions = {m: refs[m][0] for m in metric_ids}
    excluded = {}
    counts = {}
    per_period = {}
    d_by_period = {}
    shift_value = q12(D(shift))
    for period in sorted(facts_history):
        table = facts_history[period]
        present = [set(table.get(m, ())) for m in metric_ids]
        strategies = sorted(set.intersection(*present)) if present else []
        counts[period] = len(strategies)                          # n_t of [L575]
        if len(strategies) < int(opts.entropy_min_strategies):
            excluded[period] = RC.ENTROPY_PERIOD_SKIPPED.value
            continue
        values = {m: [table[m][s] for s in strategies] for m in metric_ids}
        vector = entropy_weights(values, directions, shift_value)  # dsm.entropy, the ONE impl
        if not vector.entropy_emitted:
            excluded[period] = RC.INACTIVE_METRIC.value            # [L545]
            continue
        per_period[period] = {c.metric_id: c.entropy_w_j for c in vector.columns
                              if c.entropy_w_j is not None}
        d_by_period[period] = {c.metric_id: c.d_j for c in vector.columns}
    if not per_period:
        raise EntropyInsufficientSample(
            'no usable period in the calibration window (' + str(len(counts)) + ' period(s), '
            'excluded: ' + str(sorted(excluded)) + ') -> fall back to pure AHP, equivalent to '
            'alpha = 1 ([L577], ' + RC.ENTROPY_INSUFFICIENT_SAMPLE.value + ')')
    usable = sorted(per_period)
    median_entropy = {}
    drift = {}
    median_d = {}
    for metric_id in metric_ids:
        series = [per_period[p][metric_id] for p in usable if metric_id in per_period[p]]
        d_series = [d_by_period[p][metric_id] for p in usable if metric_id in d_by_period[p]]
        if series:
            median_entropy[metric_id] = numeric.median(series)     # [L579]
            drift[metric_id] = q12(max(series) - min(series))      # [L580]
        if d_series:
            median_d[metric_id] = numeric.median(d_series)         # [L543]
    return EntropySnapshot(calibration_periods=tuple(usable), excluded_periods=excluded,
                           strategy_count_by_period=counts,
                           per_period_entropy={p: dict(per_period[p]) for p in usable},
                           median_entropy=median_entropy, drift_by_metric=drift,
                           median_d_j=median_d, shift=shift_value, entropy_emitted=True)


# --- Step 3: [L581]-[L587] -------------------------------------------------
def step3_inactive_fallback(layer: AhpLayer, entropy, opts) -> dict:
    '''Step 3, the rule the SDD calls the most important one of the whole scheme.
    Returns {metric_id: registered reason code} for the metrics that keep w_j(AHP).
    A metric whose window differentiation coefficient is below inactive_threshold
    (zero variation gives d_j = 0 by [L543]-[L545]), or that carries no entropy weight
    at all, keeps w_j(AHP) verbatim and is flagged ENTROPY_INACTIVE_FALLBACK; Step 4
    then never touches it, so a metric whose data does not move is not read as a
    metric that does not matter ([L585]-[L587]).'''
    fallback = {}
    for metric_id in sorted(layer.dim_of_metric):
        median_w = entropy.median_entropy.get(metric_id) if entropy is not None else None
        d_median = entropy.median_d_j.get(metric_id) if entropy is not None else None
        if median_w is None:
            fallback[metric_id] = RC.INACTIVE_METRIC.value
        elif d_median is None or D(d_median) < D(opts.inactive_threshold):
            fallback[metric_id] = RC.ENTROPY_INACTIVE_FALLBACK.value          # [L584]
    return fallback


# --- Step 4: [L588]-[L592] -------------------------------------------------
def _scale_to(keys: Sequence, raw: Mapping, target: Decimal) -> dict:
    '''Scale raw over `keys` so that the published sum is EXACTLY target. The
    lexicographically last key absorbs the residual: rounding every member on its own
    would leave the sum at target +/- n * 5e-13, which for a three metric dimension
    can exceed the 1e-12 tolerance H-1 of [L594] allows. Deterministic: keys sorted.'''
    ordered = sorted(keys)
    if not ordered:
        return {}
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        total = ZERO
        for key in ordered:
            total = total + D(raw[key])
        scale = safe_div(D(target), total, on_zero=ZERO)
        out = {}
        acc = ZERO
        for key in ordered[:-1]:
            value = q12(D(raw[key]) * scale)
            out[key] = value
            acc = acc + value
        out[ordered[-1]] = q12(D(target) - acc)
    return out


def step4_combine_normalize(layer: AhpLayer, entropy, fallback: Mapping, opts,
                            alpha_used) -> MixedWeights:
    '''Step 4, for the NON-fallback metrics ([L588]-[L592]).

    Metric layer: w_j(raw) = alpha * w_j(AHP) + (1 - alpha) * w_j(entropy), where
    w_j(entropy) is the window median of [L579] on the GLOBAL entropy scale -- that is
    what [L592] means by "the dimension entropy weight is the sum of the metric
    entropy weights inside the dimension". The dimension renormalisation of [L590]
    then redistributes only the residual mass 1 - sum(fallback w_j(AHP)), which keeps
    a fallback metric at its AHP weight (P-15) while the dimension still sums to 1
    (P-14 / H-1). Dimension layer: W_d(raw) = alpha * W_d(AHP) + (1 - alpha) *
    W_d(entropy), renormalised to sum 1 ([L591]-[L592]).'''
    alpha_used = D(alpha_used)
    complement = ONE - alpha_used
    median_entropy = entropy.median_entropy if entropy is not None else {}
    metric_final = {}
    metric_trace = {}
    for dim_id in sorted(layer.metric_weights):
        ahp_dim = layer.metric_weights[dim_id]
        metrics = sorted(ahp_dim)
        keep_ids = [m for m in metrics if m not in fallback]
        fallback_sum = ZERO
        for metric_id in metrics:
            if metric_id in fallback:
                fallback_sum = fallback_sum + D(ahp_dim[metric_id])
        residual = max(ZERO, ONE - fallback_sum)   # AHP sums to 1 within 1e-12: dust only
        raw = {}
        with localcontext() as ctx:
            ctx.prec = WORK_PREC
            for metric_id in keep_ids:                                 # [L589]
                raw[metric_id] = q12(alpha_used * D(ahp_dim[metric_id])
                                     + complement * D(median_entropy.get(metric_id, ZERO)))
        scaled = _scale_to(keep_ids, raw, residual)                    # [L590]
        final_dim = {}
        for metric_id in metrics:
            ent_w = median_entropy.get(metric_id)
            if metric_id in fallback:
                final_dim[metric_id] = q12(D(ahp_dim[metric_id]))      # [L583] verbatim
                raw_value = final_dim[metric_id]
            else:
                final_dim[metric_id] = scaled[metric_id]
                raw_value = raw[metric_id]
            metric_trace[metric_id] = MetricWeightTrace(
                metric_id=metric_id, dim_code=dim_id, ahp_weight=q12(D(ahp_dim[metric_id])),
                entropy_weight=None if ent_w is None else q12(D(ent_w)),
                combined_raw_weight=raw_value, final_weight=final_dim[metric_id],
                is_fallback=metric_id in fallback,
                fallback_reason=fallback.get(metric_id))
        metric_final[dim_id] = {m: final_dim[m] for m in metrics}
    comparison = {m: MetricWeightComparison(ahp_weight=t.ahp_weight,
                                            entropy_weight=t.entropy_weight,
                                            combined_weight=t.final_weight,
                                            is_fallback=t.is_fallback)
                  for m, t in metric_trace.items()}                    # [L1237]
    ent_sum = {}
    raw_dim = {}
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        for dim_id in sorted(layer.dim_weights):
            total = ZERO
            for metric_id in sorted(layer.metric_weights[dim_id]):
                total = total + D(median_entropy.get(metric_id, ZERO))
            ent_sum[dim_id] = q12(total)                               # [L592]
            raw_dim[dim_id] = q12(alpha_used * D(layer.dim_weights[dim_id])
                                  + complement * ent_sum[dim_id])      # [L591]
    dim_final = _scale_to(sorted(raw_dim), raw_dim, ONE)               # [L592] sum W_d = 1
    return MixedWeights(alpha_used=q12(alpha_used), dim_weights=dim_final,
                        dim_entropy_weight=ent_sum, dim_raw_weight=raw_dim,
                        metric_weights=metric_final, metric_trace=metric_trace,
                        comparison_by_metric=comparison)


# --- Step 5: [L593]-[L599] -------------------------------------------------
def _effective(dim_weights: Mapping, metric_weights: Mapping) -> dict:
    '''The weight that actually reaches a score: W_d * w_j ([L592] plus aggregate).'''
    out = {}
    with localcontext() as ctx:
        ctx.prec = WORK_PREC
        for dim_id in sorted(metric_weights):
            for metric_id in sorted(metric_weights[dim_id]):
                out[metric_id] = q12(D(dim_weights[dim_id]) * D(metric_weights[dim_id][metric_id]))
    return out


def step5_hard_checks(mixed: MixedWeights, layer: AhpLayer, opts) -> HardCheckReport:
    '''Step 5. Any False makes this alpha infeasible ([L593]) and the verdict travels
    to the calibration side ([L1071]); none of it is softened into a warning. H-5 is
    measured on both layers (dimension weights and the effective W_d * w_j that enters
    the score) and the larger L1 distance is the one compared with max_shift_from_ahp,
    because [L598] does not name a layer.'''
    sum_dim = ZERO
    for dim_id in sorted(mixed.dim_weights):
        sum_dim = sum_dim + D(mixed.dim_weights[dim_id])
    h1 = numeric.eq_tol(q12(sum_dim), ONE, TOL)                        # [L594] sum W_d = 1
    for dim_id in sorted(mixed.metric_weights):
        total = ZERO
        for metric_id in sorted(mixed.metric_weights[dim_id]):
            total = total + D(mixed.metric_weights[dim_id][metric_id])
        h1 = h1 and numeric.eq_tol(q12(total), ONE, TOL)               # [L594] sum w_j = 1
    min_dim = min((D(mixed.dim_weights[d]) for d in sorted(mixed.dim_weights)), default=ZERO)
    h2 = min_dim >= D(opts.min_dim_weight)                             # [L595]
    flat = [D(mixed.metric_weights[d][m]) for d in sorted(mixed.metric_weights)
            for m in sorted(mixed.metric_weights[d])]
    min_metric = min(flat, default=ZERO)
    h3 = True if opts.min_metric_weight is None else min_metric >= D(opts.min_metric_weight)
    h4 = D(layer.cr_max) < CR_THRESHOLD                                # [L597]
    l1_shift = q12(max(numeric.l1_distance(mixed.dim_weights, layer.dim_weights),
                       numeric.l1_distance(_effective(mixed.dim_weights, mixed.metric_weights),
                                           _effective(layer.dim_weights, layer.metric_weights))))
    h5 = l1_shift <= D(opts.max_shift_from_ahp)                        # [L598]-[L599]
    results = {'H-1': bool(h1), 'H-2': bool(h2), 'H-3': bool(h3), 'H-4': bool(h4),
               'H-5': bool(h5)}
    violations = tuple(cid for cid in HARD_CHECK_IDS if not results[cid])
    reasons = []
    if not h4:
        reasons.append(RC.AHP_CR_FAILED.value)
    if violations:
        reasons.append(RC.ALPHA_INFEASIBLE.value)
    return HardCheckReport(results=results, violations=violations, reasons=tuple(reasons),
                           l1_shift_from_ahp=l1_shift, min_dim_observed=q12(min_dim),
                           min_metric_observed=q12(min_metric), cr_max=q12(D(layer.cr_max)),
                           cr_by_level=dict(layer.cr_by_level))


# --- Step 6: [L600] --------------------------------------------------------
def assert_feasible(combined: CombinedWeights) -> CombinedWeights:
    '''The gate [L593] hands to the calibration side: an infeasible alpha never becomes
    a draft weight document. Raises AlphaInfeasibleError ([L1071]).'''
    if not combined.feasible:
        raise AlphaInfeasibleError('alpha = ' + str(combined.alpha) + ' violates '
                                   + ', '.join(combined.hard_checks.violations)
                                   + ' ([L593]); this alpha is infeasible, no DRAFT is produced ('
                                   + RC.ALPHA_INFEASIBLE.value + ')')
    return combined


def step6_draft(combined: CombinedWeights, header: DraftHeader) -> WeightVersionDoc:
    '''Step 6: a WeightVersionDoc with status = DRAFT and the provenance of 3.11.4.
    WeightProvenance.ahp holds ONE AhpSegment ([L1232]) while a hierarchy carries a
    dimension level plus one metric level per dimension, so the dimension level is the
    published segment and every level CR travels in hard_checks.cr_by_level.
    alpha_basis stays None: it is the CalibrationReport of [L1239], owned by
    weights_calibrate.py (L0b), and nothing is invented here.'''
    assert_feasible(combined)
    provenance = WeightProvenance(
        kind=combined.kind,
        ahp=AhpSegment(**combined.ahp.dim_segment),
        entropy=(None if combined.entropy is None
                 else combined.entropy.to_segment(combined.inactive_fallback_metrics)),
        combine=CombineSegment(
            alpha=combined.alpha, alpha_source=combined.alpha_source,
            calibration_report_ref=header.calibration_report_ref,
            comparison_by_metric=dict(combined.comparison_by_metric),
            hard_check_results={k: bool(v) for k, v in combined.hard_checks.results.items()}),
        alpha_basis=None,
        whatif_run_id=header.whatif_run_id,
        approved_by=header.approved_by, approved_date=header.approved_date,
        effective_from=header.effective_from, effective_to=header.effective_to)
    return WeightVersionDoc(
        weight_version_id=header.weight_version_id,
        status=DRAFT,                                    # [L600]: never FROZEN
        effective_from=header.effective_from, effective_to=header.effective_to,
        level1_weights={d: combined.dim_weights[d] for d in sorted(combined.dim_weights)},
        level2_weights={d: {m: combined.metric_weights[d][m]
                            for m in sorted(combined.metric_weights[d])}
                        for d in sorted(combined.metric_weights)},
        approved_by=header.approved_by, approved_date=header.approved_date,
        provenance=provenance)


def freeze(combined=None) -> None:
    '''There is no such operation ([L600], [L1071]), the same discipline as
    weights_ahp.freeze: sign-off is a named human act on the weight version doc.'''
    raise FrozenStatusError('weights_combine cannot write status FROZEN ([L600], [L1071]); '
                            'sign-off is a human act on WeightVersionDoc ('
                            + RC.AHP_DRAFT_ONLY.value + ')')


def combine(ahp, entropy, opts, alpha_source: str = 'MANUAL') -> CombinedWeights:
    '''combine(ahp, entropy, opts) -> CombinedWeights ([L558]).

    Steps 1, 3, 4 and 5 run here in that order. Step 2 is already materialised in
    `entropy` (calibrate_entropy_window is its implementation), so its id is recorded
    as consumed, never recomputed: INV-3 forbids a second entropy run. `entropy` may be
    None -- that is the [L577] degrade, alpha becomes 1 and every metric falls back to
    its AHP weight. combine() REPORTS an infeasible alpha instead of raising so a
    calibration grid can scan candidates; assert_feasible / step6_draft are the gate.'''
    layer = step1_ahp_gate(ahp)
    trace = [STEP1, STEP2]
    sufficient = entropy is not None and bool(entropy.entropy_emitted)
    alpha_used = D(opts.alpha) if sufficient else ONE      # [L577] equivalent to alpha = 1
    fallback = step3_inactive_fallback(layer, entropy, opts)
    trace.append(STEP3)
    mixed = step4_combine_normalize(layer, entropy, fallback, opts, alpha_used)
    trace.append(STEP4)
    checks = step5_hard_checks(mixed, layer, opts)
    trace.append(STEP5)
    notices = []
    prominent = None
    if not sufficient:
        notices.extend([RC.ENTROPY_INSUFFICIENT_SAMPLE.value, RC.ALPHA_PURE_AHP.value])
        prominent = ('[L577]-[L578] 标定窗口内无可用期：本草稿已回退纯 AHP（等价 alpha = 1），'
                     '熵权未参与组合。须在草稿首屏显著标注，签认前须人工确认标定窗口。')
    elif entropy.excluded_periods:
        notices.append(RC.ENTROPY_PERIOD_SKIPPED.value)
    if fallback:
        notices.append(RC.ENTROPY_INACTIVE_FALLBACK.value)
    if 'METHOD_MISMATCH' in layer.findings:
        notices.append(RC.AHP_METHOD_MISMATCH.value)
    return CombinedWeights(alpha=mixed.alpha_used, alpha_source=alpha_source,
                           dim_weights=mixed.dim_weights,
                           dim_entropy_weight=mixed.dim_entropy_weight,
                           dim_raw_weight=mixed.dim_raw_weight,
                           metric_weights=mixed.metric_weights, metric_trace=mixed.metric_trace,
                           comparison_by_metric=mixed.comparison_by_metric, hard_checks=checks,
                           feasible=not checks.violations,
                           inactive_fallback_metrics=tuple(sorted(fallback)),
                           entropy_sufficient=sufficient,
                           kind=KIND_COMBINED if sufficient else KIND_AHP_ONLY,
                           notices=tuple(notices), prominent_notice=prominent, ahp=layer,
                           entropy=entropy, step_trace=tuple(trace))


def run_six_steps(ahp_matrices, facts_history, metric_dict, opts, header: DraftHeader, shift,
                  *, elicit_hierarchy: Callable):
    '''All six steps out of raw inputs, returning (CombinedWeights, WeightVersionDoc).

    `elicit_hierarchy` is the INJECTED Step-1 elicitation of [L572]: a callable taking
    (dimension_matrices, metric_matrices_by_dim, interview_dates) and returning an
    AhpHierarchySnapshot. It is keyword-only and required -- [L286] makes L0a 无内部依赖,
    so the L0a -> L0a edge belongs to the caller (dsm/cli.py, the integration skeleton),
    which owns both sides and converts the AHP product into snapshot DATA. A missing or
    non-callable injection raises; nothing is imported here to fill the hole (V-14).

    Step 1 elicits the hierarchy through that callable and gates CR BEFORE Step
    2 touches a single fact. Step 2 builds the calibration window; the [L577] degrade
    leaves it empty and alpha becomes 1. STEP6 joins the trace only after the draft
    exists, so an infeasible alpha (Step 5) never claims to have reached Step 6.

    ahp_matrices is {dimension: {expert: A}, metrics_by_dim: {dim: {expert: A}}};
    facts_history is period -> metric_id -> strategy_id -> value with SUSPECT rows
    already dropped ([L1151], C-06); metric_dict is a sequence or mapping of
    MetricDictRow; shift is the [L540] technical epsilon, for which the digest states
    no value, so it is never a literal here.'''
    if not callable(elicit_hierarchy):
        raise AhpInputError('run_six_steps needs the Step-1 elicitation injected as '
                            'elicit_hierarchy (keyword-only, required): a callable '
                            '(dimension_matrices, metric_matrices_by_dim, interview_dates) '
                            '-> AhpHierarchySnapshot ([L572], [L286], ORCH-29 ruling 1); '
                            'got ' + type(elicit_hierarchy).__name__)
    dimension_matrices, metric_matrices = _split_matrices(ahp_matrices)
    hierarchy = elicit_hierarchy(dimension_matrices, metric_matrices,
                                 tuple(header.interview_dates))
    step1_ahp_gate(hierarchy)                    # Step 1 CR gate, before any entropy work
    try:
        snapshot = calibrate_entropy_window(facts_history, metric_dict, opts, shift)
    except EntropyInsufficientSample:
        snapshot = None                          # Step 2 -> the [L577] degrade
    combined = combine(hierarchy, snapshot, opts, header.alpha_source)
    doc = step6_draft(combined, header)          # Step 6, raises when Step 5 rejected
    combined = combined.model_copy(update={'step_trace': combined.step_trace + (STEP6,)})
    return combined, doc


def build_draft(ahp_matrices, facts_history, metric_dict, opts, header: DraftHeader,
                shift, *, elicit_hierarchy: Callable) -> WeightVersionDoc:
    '''build_draft(ahp_matrices, facts_history, metric_dict, opts) -> WeightVersionDoc
    ([L559], status = DRAFT). `header` carries the identity and the dates H-8 forbids
    this module to read from a clock, and `elicit_hierarchy` is the injected Step-1
    elicitation of run_six_steps, which is why the signature has two arguments more
    than the [L559] sketch. Raises ConsistencyGateError (or the ConsistencyFailedError
    the injected Step-1 elicitation raises, [L573]) and AlphaInfeasibleError when
    H-1..H-5 reject this alpha ([L593]).'''
    return run_six_steps(ahp_matrices, facts_history, metric_dict, opts, header, shift,
                         elicit_hierarchy=elicit_hierarchy)[1]
