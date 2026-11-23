'''RED tests for WeightProvenance / EvidenceSource in dsm/models.py (S1-T03, L1).

Single source of truth = docs/digest/S1-T03.md; every [LXXX] below points at an
SDD line reproduced there:

- [L1228]-[L1245] §3.11.4: kind [L1231]; the four segments ahp [L1232-L1233],
  entropy [L1234-L1235], combine [L1236-L1238], alpha_basis [L1239-L1240];
  whatif_run_id [L1241]; approved_by / approved_date / effective_from /
  effective_to [L1242].
- [L535] INV-3: WeightProvenance.entropy is a snapshot value, never a callable.
- [L636] / [L1072]: the whole CalibrationReport lands in provenance.alpha_basis.
- [L1193] / [L1194]: WeightVersionDoc.provenance wiring; the sign-off quartet
  exists BOTH on the doc ([L1191], [L1194]) and inside provenance ([L1242]) -
  the SDD duplicates it on purpose.
- [L880] / [L900] / [L1281] / [L1435]: "FROZEN but missing whatif_run_id" and
  the P-11 completeness checks are CONFIG-layer (S1-T06); the models layer
  must not pre-implement them, only carry the nullable column.
- [L1895] / [L870]: EvidenceSource = Literal {CARD_ONLY, CEL_ESTIMATED}; per
  ORCH-15 it is a verdict, not an input fact, so it never joins any input row.
- [L865] / [L871]: frozen + extra=forbid everywhere; V-5 undeclared fields
  must be rejected.
- [L1777] RK-13 names two entropy fields verbatim: per_period_entropy and
  drift_by_metric. Those two names are SDD-given; the remaining segment field
  names are the canonical mapping of the [L1232]-[L1240] prose items and part
  of this contract (R2 implements against them, R4 reviews against the digest).
- ORCH-20 (docs/adr/ORCH-20.md) rules: the four segments are nullable with
  a None default (ruling 1); alpha dict keys are Ratio/Decimal, never str
  (ruling 5); alpha_basis.seed and the entropy_weight comparison column are
  nullable (ruling 6); the CalibrationReport class name stays out of
  dsm/models.py (ruling 3); hard_check_results keeps no closed key set here
  (ruling 7, B-016).

All data is synthetic (SYN- prefix, H-5/H-14): no business value, no K-01~K-20
suggestion is hard-coded; numeric probes follow H-4 (ratios are Decimal built
from strings and reject float/bool; counts are exact int and reject lax forms).
The module never touches unimplemented attributes at import time, so the file
always collects; RED failures are AttributeError / ValidationError inside test
bodies (= feature not implemented), per ORCH 7.2 L1.
'''
import ast
import copy
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from dsm import models
from dsm.reason_codes import RC

# ---------------------------------------------------------------------------
# Synthetic payloads. Pure data at module level (RC exists since S0), so the
# file collects even while WeightProvenance is unimplemented.
# ---------------------------------------------------------------------------
METRIC_A = 'SYN-M-001'
METRIC_B = 'SYN-M-002'
EXPERT_1 = 'SYN-EXPERT-01'
EXPERT_2 = 'SYN-EXPERT-02'

AHP_SNAPSHOT = {
    # [L1232] expert pairwise matrices, lambda_max, CI, RI, CR, expert count,
    # interview dates; [L1233] both weight methods and their max gap.
    'comparison_matrices': {
        EXPERT_1: {
            METRIC_A: {METRIC_A: '1', METRIC_B: '3'},
            METRIC_B: {METRIC_A: '0.25', METRIC_B: '1'},
        },
        EXPERT_2: {
            METRIC_A: {METRIC_A: '1', METRIC_B: '2'},
            METRIC_B: {METRIC_A: '0.5', METRIC_B: '1'},
        },
    },
    'lambda_max': '2.1',
    'ci': '0.1',
    'ri': '0.2',
    'cr': '0.05',
    'expert_count': 2,
    'interview_dates': ['2026-01-05', '2026-01-06'],
    'weights_geometric': {METRIC_A: '0.6', METRIC_B: '0.4'},
    'weights_eigenvector': {METRIC_A: '0.62', METRIC_B: '0.38'},
    'max_method_gap': '0.02',
}

ENTROPY_SNAPSHOT = {
    # [L1234] calibration window list, per-period entropy weights, median
    # entropy weights, per-metric drift_j; [L1235] INACTIVE fallback metric
    # list, excluded periods and reasons. per_period_entropy / drift_by_metric
    # are the verbatim names of [L1777] (RK-13).
    'calibration_periods': ['2026-01', '2026-02', '2026-03', '2026-04'],
    'per_period_entropy': {
        '2026-01': {METRIC_A: '0.5', METRIC_B: '0.5'},
        '2026-02': {METRIC_A: '0.55', METRIC_B: '0.45'},
    },
    'median_entropy': {METRIC_A: '0.5', METRIC_B: '0.5'},
    'drift_by_metric': {METRIC_A: '0.01', METRIC_B: '0.02'},
    'inactive_fallback_metrics': [METRIC_B],
    'excluded_periods': {'2026-04': RC.ENTROPY_PERIOD_SKIPPED.value},
}

COMBINE_SNAPSHOT = {
    # [L1236] alpha value, alpha source (CALIBRATED | MANUAL), calibration
    # report reference; [L1237] per-metric four-column comparison; [L1238]
    # H-1~H-5 hard check results.
    'alpha': '0.7',
    'alpha_source': 'CALIBRATED',
    'calibration_report_ref': 'SYN-CAL-REPORT-001',
    'comparison_by_metric': {
        METRIC_A: {'ahp_weight': '0.6', 'entropy_weight': '0.5',
                   'combined_weight': '0.57', 'is_fallback': False},
        METRIC_B: {'ahp_weight': '0.4', 'entropy_weight': '0.5',
                   'combined_weight': '0.43', 'is_fallback': True},
    },
    'hard_check_results': {'H-1': True, 'H-2': True, 'H-3': True,
                           'H-4': True, 'H-5': True},
}

ALPHA_BASIS_SNAPSHOT = {
    # [L1239]-[L1240] / [L636]: the whole CalibrationReport - candidate alpha
    # x metric matrix, alpha star, binding constraints, excluded alphas with
    # reasons, window period list, run_id, seed. ORCH-20 ruling 5: alpha keys
    # are Ratio (Decimal), never str - a str key would dodge the numeric gate
    # (H-4) and break the lexicographic minimum-alpha search of [L1072].
    # ORCH-20 ruling 6: seed is nullable ([L636] seed only when MC is used).
    'candidate_alpha_matrix': {
        Decimal('0.3'): {METRIC_A: '0.01', METRIC_B: '0.02'},
        Decimal('0.7'): {METRIC_A: '0.04', METRIC_B: '0.05'},
    },
    'alpha_star': '0.7',
    'binding_constraints': ['drift_budget'],
    'excluded_alphas': {Decimal('0.3'): RC.ALPHA_INFEASIBLE.value},
    'window_periods': ['2026-01', '2026-02', '2026-03'],
    'run_id': 'SYN-RUN-001',
    'seed': 20260101,
}

PROVENANCE = {
    'kind': 'AHP_ENTROPY_COMBINED',
    'ahp': AHP_SNAPSHOT,
    'entropy': ENTROPY_SNAPSHOT,
    'combine': COMBINE_SNAPSHOT,
    'alpha_basis': ALPHA_BASIS_SNAPSHOT,
    'whatif_run_id': 'SYN-WHATIF-001',
    'approved_by': 'SYN-COMMITTEE',
    'approved_date': '2026-01-10',
    'effective_from': '2026-01-01',
    'effective_to': '2026-12-31',
}

# T6 doc payload, mirrors weight_version_payload() of test_models_input.py
# ([L1190]-[L1194]); provenance is attached only where a test says so.
WEIGHT_DOC = {
    'weight_version_id': 'SYN-W-2026',
    'status': 'DRAFT',
    'effective_from': '2026-01-01',
    'effective_to': '2026-12-31',
    'level1_weights': {'SYN-DIM-01': '0.5', 'SYN-DIM-02': '0.5'},
    'level2_weights': {'SYN-DIM-01': {METRIC_A: '1'}},
    'approved_by': 'SYN-COMMITTEE',
    'approved_date': '2026-01-10',
}

SEGMENTS = ('ahp', 'entropy', 'combine', 'alpha_basis')


def provenance_payload():
    return copy.deepcopy(PROVENANCE)


def build_provenance(**overrides):
    payload = provenance_payload()
    payload.update(overrides)
    return models.WeightProvenance(**payload)


def set_at(payload, path, value):
    # Path keys address the raw payload dict; alpha keys are Decimal
    # (ORCH-20 ruling 5) and hash-match the validated model keys in get_at.
    node = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    return payload


def build_with(path, value):
    return models.WeightProvenance(**set_at(provenance_payload(), path, value))


def get_at(obj, path):
    node = obj
    for key in path:
        node = node[key] if isinstance(node, dict) else getattr(node, key)
    return node


def _unwrap(annotation):
    '''Annotated[X, gate] -> X (pydantic gates wrap the real type).'''
    if hasattr(annotation, '__metadata__'):
        return _unwrap(get_args(annotation)[0])
    return annotation


def _literal_args(annotation):
    inner = _unwrap(annotation)
    if get_origin(inner) is Literal:
        return get_args(inner)
    return ()


def _segment_class(annotation):
    '''Pull the sub-model class out of a segment annotation, which ORCH-20
    ruling 1 makes Optional[<sub-model>] (X | None).'''
    inner = _unwrap(annotation)
    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return inner
    for arg in get_args(inner):
        candidate = _unwrap(arg)
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return candidate
    raise AssertionError(
        'segment annotation carries no BaseModel subclass: '
        + repr(annotation))


# ---------------------------------------------------------------------------
# 1. kind [L1231]: closed three-value Literal.
# ---------------------------------------------------------------------------
LEGAL_KINDS = ('AHP_ONLY', 'AHP_ENTROPY_COMBINED', 'EXPERT_ONLY')


@pytest.mark.parametrize('kind', LEGAL_KINDS)
def test_kind_accepts_exactly_the_three_legal_values(kind):
    '''[L1231] kind: AHP_ONLY | AHP_ENTROPY_COMBINED | EXPERT_ONLY.'''
    prov = build_provenance(kind=kind)
    assert prov.kind == kind


@pytest.mark.parametrize('kind', [
    'ahp_only', 'AHP', 'COMBINED', 'AHP_ENTROPY', 'EXPERT', 'ahp_ONLY',
    'AHP_ONLY ', '', None, 3, True,
])
def test_kind_rejects_everything_outside_the_literal_set(kind):
    '''[L1231]: lowercase, prefixes, blanks, None and non-text all rejected.'''
    with pytest.raises(ValidationError):
        build_provenance(kind=kind)


def test_kind_field_is_a_closed_literal_of_the_three_values():
    '''[L1231] + [L865]: enums are typing.Literal, and the set is exactly 3.'''
    ann = models.WeightProvenance.model_fields['kind'].annotation
    assert _literal_args(ann) == LEGAL_KINDS


def test_provenance_declares_exactly_the_ten_contract_columns():
    '''[L1230]-[L1242] name exactly these columns; frozen + extra=forbid
    ([L865]) makes any surplus a contract change, so the set stays closed
    (no status column: the FROZEN coupling lives on WeightVersionDoc [L1190]
    and its checks are config layer [L880], S1-T06).'''
    declared = set(models.WeightProvenance.model_fields)
    expected = set(SEGMENTS) | {
        'kind', 'whatif_run_id',
        'approved_by', 'approved_date', 'effective_from', 'effective_to',
    }
    assert declared == expected

# ---------------------------------------------------------------------------
# 2. Four segments, all present, all data snapshots [L1232]-[L1240] + [L535].
# ---------------------------------------------------------------------------
def test_all_four_segments_are_declared():
    '''[L1232]/[L1234]/[L1236]/[L1239]: the four segments are the contract;
    ORCH §5.2 S1-T03 acceptance reads "§3.11.4 四段齐全".'''
    declared = set(models.WeightProvenance.model_fields)
    for name in SEGMENTS:
        assert name in declared, 'segment missing: ' + name


def test_segments_land_as_data_snapshots_not_callables():
    '''[L535] INV-3 type isolation: entropy (and its three siblings) are
    snapshot VALUES - pydantic sub-models - never callable objects, so a
    scoring run cannot recompute entropy weights through them.'''
    prov = build_provenance()
    for name in SEGMENTS:
        seg = getattr(prov, name)
        assert isinstance(seg, BaseModel), name + ' is not a data snapshot'
        assert callable(seg) is False, name + ' must not be callable'
        assert type(seg).__module__.startswith('dsm.'), (
            name + ' snapshot must live in the dsm package')


def test_segment_annotations_are_basemodel_subclasses():
    '''ORCH-20 ruling 1: a segment annotation is Optional[<sub-model>]; the
    sub-model class must be recoverable from it - never a dict/Any/callable
    ([L535] type isolation still holds per segment).'''
    for name in SEGMENTS:
        seg_cls = _segment_class(
            models.WeightProvenance.model_fields[name].annotation)
        assert issubclass(seg_cls, BaseModel), (
            name + ' must be typed as a sub-model, not a dict/Any/callable')


@pytest.mark.parametrize('name', SEGMENTS)
def test_every_segment_is_nullable_with_none_default(name):
    '''ORCH-20 ruling 1: all four segments are Optional[...] = None at the
    models layer. [L1435] P-11 obliges FROZEN versions to carry the full
    chain and fails at CONFIG LOADING ([L880], [L1281]); forcing EXPERT_ONLY
    / AHP_ONLY instances to fill an entropy snapshot would invent zero
    values, which H-5 forbids.'''
    info = models.WeightProvenance.model_fields[name]
    assert info.default is None
    assert info.is_required() is False
    prov = build_provenance(**{name: None})
    assert getattr(prov, name) is None


def test_ahp_only_provenance_builds_with_the_other_segments_absent():
    '''ORCH-20 ruling 1: kind=AHP_ONLY carries only the ahp segment; the
    other three stay None instead of being padded with invented data
    (H-5). The PROVENANCE snapshot above stays four-segment-complete for
    the AHP_ENTROPY_COMBINED case.'''
    payload = provenance_payload()
    payload['kind'] = 'AHP_ONLY'
    for name in ('entropy', 'combine', 'alpha_basis'):
        del payload[name]
    prov = models.WeightProvenance(**payload)
    assert prov.kind == 'AHP_ONLY'
    assert prov.ahp is not None
    assert prov.entropy is None
    assert prov.combine is None
    assert prov.alpha_basis is None


def test_segment_completeness_checks_belong_to_the_config_layer():
    '''ORCH-20 ruling 1 / S1-T06: "FROZEN must carry the complete
    provenance, and a combined version must carry alpha + alpha_basis +
    whatif_run_id" ([L1435] P-11, [L880], C-01 [L900]) is a LOADING-time
    rule. The models layer must accept an incomplete combined record so the
    config layer stays the only judge - same layering as the whatif_run_id
    guard below.'''
    prov = build_provenance(kind='AHP_ENTROPY_COMBINED', entropy=None,
                            combine=None, alpha_basis=None)
    assert prov.kind == 'AHP_ENTROPY_COMBINED'
    assert prov.entropy is None
    assert prov.combine is None
    assert prov.alpha_basis is None


def test_entropy_snapshot_holds_data_not_behaviour():
    '''[L535] concretely: the entropy segment exposes plain containers.'''
    ent = build_provenance().entropy
    assert isinstance(ent.per_period_entropy, dict)
    assert callable(ent.per_period_entropy) is False
    assert isinstance(ent.drift_by_metric[METRIC_A], Decimal)
    assert not any(callable(getattr(ent, f)) for f in type(ent).model_fields)


# ---------------------------------------------------------------------------
# 3. ahp segment contents [L1232]-[L1233].
# ---------------------------------------------------------------------------
AHP_FIELDS = (
    'comparison_matrices',   # [L1232] expert pairwise comparison matrices
    'lambda_max',            # [L1232]
    'ci',                    # [L1232]
    'ri',                    # [L1232]
    'cr',                    # [L1232]
    'expert_count',          # [L1232] expert head count
    'interview_dates',       # [L1232] interview dates
    'weights_geometric',     # [L1233] geometric-mean method weights
    'weights_eigenvector',   # [L1233] eigenvector method weights
    'max_method_gap',        # [L1233] max difference of the two weight sets
)


def test_ahp_segment_declares_exactly_the_chain_of_L1232_L1233():
    declared = set(type(build_provenance().ahp).model_fields)
    assert declared == set(AHP_FIELDS)


def test_ahp_snapshot_values_land_on_the_h4_types():
    '''H-4: ratios are Decimal (string-built), counts are int, dates are date;
    lambda_max / CI / RI / CR / gap / both weight sets / matrix cells.'''
    ahp = build_provenance().ahp
    for ratio in (ahp.lambda_max, ahp.ci, ahp.ri, ahp.cr, ahp.max_method_gap,
                  ahp.weights_geometric[METRIC_A],
                  ahp.weights_eigenvector[METRIC_B],
                  ahp.comparison_matrices[EXPERT_1][METRIC_A][METRIC_B]):
        assert isinstance(ratio, Decimal)
    assert type(ahp.expert_count) is int
    assert ahp.expert_count == 2
    assert len(ahp.interview_dates) == 2
    assert all(type(d) is date for d in ahp.interview_dates)


# ---------------------------------------------------------------------------
# 4. entropy segment contents [L1234]-[L1235] + [L1777]; H-6/H-7 reasons.
# ---------------------------------------------------------------------------
ENTROPY_FIELDS = (
    'calibration_periods',        # [L1234] calibration window period list
    'per_period_entropy',         # [L1234] per-period entropy weights ([L1777] name)
    'median_entropy',             # [L1234] median entropy weights
    'drift_by_metric',            # [L1234] drift_j per metric ([L1777] name)
    'inactive_fallback_metrics',  # [L1235] INACTIVE fallback metric list
    'excluded_periods',           # [L1235] excluded periods and reasons
)


def test_entropy_segment_declares_exactly_the_window_contract():
    '''[L1234]-[L1235]; per_period_entropy and drift_by_metric are the
    verbatim field names of [L1777] (RK-13).'''
    declared = set(type(build_provenance().entropy).model_fields)
    assert declared == set(ENTROPY_FIELDS)


def test_excluded_period_reason_accepts_a_registered_code():
    '''H-6/H-7 + [L1235]: the exclusion reason resolves in reason_codes.'''
    ent = build_provenance().entropy
    assert ent.excluded_periods['2026-04'] == RC.ENTROPY_PERIOD_SKIPPED.value


@pytest.mark.parametrize('bad', [
    'MADE_UP_CODE',
    'entropy_period_skipped',        # registered code, wrong case
    'RC.ENTROPY_PERIOD_SKIPPED',     # str(RC.X) trap: prefixed form
    '',
    None,
    7,
])
def test_excluded_period_reason_rejects_unregistered_forms(bad):
    '''[L1235] + H-7: only registered codes; bare strings never pass. The
    third probe is the documented trap: str(RC.STABLE) == "RC.STABLE".'''
    with pytest.raises(ValidationError):
        build_with(('entropy', 'excluded_periods', '2026-04'), bad)


def test_rc_str_form_is_prefixed_and_value_is_the_code():
    '''Regression on the trap itself, so the probe above stays meaningful.'''
    assert str(RC.ENTROPY_PERIOD_SKIPPED) == 'RC.ENTROPY_PERIOD_SKIPPED'
    assert RC.ENTROPY_PERIOD_SKIPPED.value == 'ENTROPY_PERIOD_SKIPPED'


def test_inactive_fallback_metrics_is_a_sequence_of_ids():
    '''[L1235]: a list of metric ids, snapshot data (mirrors the T8
    strategy_ids discipline: a collection, not a bare string).'''
    ent = build_provenance().entropy
    assert list(ent.inactive_fallback_metrics) == [METRIC_B]
    with pytest.raises(ValidationError):
        build_with(('entropy', 'inactive_fallback_metrics'), METRIC_B)


# ---------------------------------------------------------------------------
# 5. combine segment contents [L1236]-[L1238].
# ---------------------------------------------------------------------------
COMBINE_FIELDS = (
    'alpha',                   # [L1236] alpha value
    'alpha_source',            # [L1236] CALIBRATED | MANUAL
    'calibration_report_ref',  # [L1236] calibration report reference
    'comparison_by_metric',    # [L1237] per-metric four-column comparison
    'hard_check_results',      # [L1238] H-1~H-5 check results
)

COMPARISON_COLUMNS = (
    'ahp_weight',       # [L1237] AHP value
    'entropy_weight',   # [L1237] entropy weight value
    'combined_weight',  # [L1237] combined value
    'is_fallback',      # [L1237] fallback flag
)


def test_combine_segment_declares_exactly_the_alpha_contract():
    declared = set(type(build_provenance().combine).model_fields)
    assert declared == set(COMBINE_FIELDS)


def test_alpha_source_is_a_closed_literal_of_two_values():
    '''[L1236]: alpha source is CALIBRATED | MANUAL, nothing else.'''
    ann = type(build_provenance().combine).model_fields['alpha_source'].annotation
    assert _literal_args(ann) == ('CALIBRATED', 'MANUAL')


@pytest.mark.parametrize('source', ['CALIBRATED', 'MANUAL'])
def test_alpha_source_accepts_both_legal_values(source):
    prov = build_with(('combine', 'alpha_source'), source)
    assert prov.combine.alpha_source == source


@pytest.mark.parametrize('source', [
    'calibrated', 'AUTO', 'CALIBRATED ', '', None, 1, True,
])
def test_alpha_source_rejects_everything_else(source):
    with pytest.raises(ValidationError):
        build_with(('combine', 'alpha_source'), source)


def test_comparison_entry_declares_exactly_the_four_columns():
    '''[L1237]: AHP value / entropy weight value / combined value / fallback.'''
    cmp_a = build_provenance().combine.comparison_by_metric[METRIC_A]
    assert isinstance(cmp_a, BaseModel)
    assert set(type(cmp_a).model_fields) == set(COMPARISON_COLUMNS)
    assert isinstance(cmp_a.ahp_weight, Decimal)
    assert isinstance(cmp_a.entropy_weight, Decimal)
    assert isinstance(cmp_a.combined_weight, Decimal)
    assert cmp_a.is_fallback is False
    cmp_b = build_provenance().combine.comparison_by_metric[METRIC_B]
    assert cmp_b.is_fallback is True


@pytest.mark.parametrize('probe', [1, 0, 'true', 'false', 'yes', 1.0, Decimal('1')])
def test_is_fallback_is_a_strict_bool_column(probe):
    '''H-4 / ORCH-18 discipline: bool columns take a Python bool only.'''
    with pytest.raises(ValidationError):
        build_with(('combine', 'comparison_by_metric', METRIC_A,
                    'is_fallback'), probe)


def test_fallback_entry_accepts_a_none_entropy_weight():
    '''ORCH-20 ruling 6 / [L1235]: an INACTIVE (zero-variance) metric has
    no mathematically defined entropy weight; forcing a value would invent
    a business number (H-5). The fallback semantics ride on the
    is_fallback column ([L1237]), so entropy_weight is nullable.'''
    prov = build_with(('combine', 'comparison_by_metric', METRIC_B,
                       'entropy_weight'), None)
    entry = prov.combine.comparison_by_metric[METRIC_B]
    assert entry.entropy_weight is None
    assert entry.is_fallback is True
    assert isinstance(entry.ahp_weight, Decimal)
    assert isinstance(entry.combined_weight, Decimal)


@pytest.mark.parametrize('column', ['ahp_weight', 'combined_weight',
                                    'is_fallback'])
def test_the_other_three_comparison_columns_reject_none(column):
    '''ORCH-20 ruling 6: ahp_weight / combined_weight stay required Ratio -
    S8-T01 must be able to check that a fallback metric's combined weight
    equals its AHP weight exactly ([L1237]); is_fallback stays a required
    StrictBool (ORCH-18).'''
    with pytest.raises(ValidationError):
        build_with(('combine', 'comparison_by_metric', METRIC_A, column),
                   None)


def test_hard_check_results_carry_h1_to_h5_as_strict_bools():
    '''[L1238]: the five hard-constraint results of weights_combine
    ([L1071]) land as a snapshot mapping. ORCH-20 ruling 7 / B-016: the
    models layer fixes only "values are strict bools" (ORCH-18); the key
    set is NOT closed here - the SDD definition of H-1~H-5 is outside the
    authorised ranges and belongs to S8-T01.'''
    res = build_provenance().combine.hard_check_results
    assert {'H-1', 'H-2', 'H-3', 'H-4', 'H-5'} <= set(res)
    assert all(v is True for v in res.values())


@pytest.mark.parametrize('probe', [1, 'true', None, 1.0])
def test_hard_check_results_reject_non_bool_values(probe):
    with pytest.raises(ValidationError):
        build_with(('combine', 'hard_check_results', 'H-3'), probe)

# ---------------------------------------------------------------------------
# 6. alpha_basis segment contents [L1239]-[L1240] + [L636] + [L1072].
# ---------------------------------------------------------------------------
ALPHA_BASIS_FIELDS = (
    'candidate_alpha_matrix',  # [L636]/[L1239] candidate alpha x metric matrix
    'alpha_star',              # [L636]/[L1239] alpha*
    'binding_constraints',     # [L636]/[L1239] constraints that were hit
    'excluded_alphas',         # [L636]/[L1240] excluded alphas with reasons
    'window_periods',          # [L636]/[L1240] window period list
    'run_id',                  # [L636]/[L1240]
    'seed',                    # [L636]/[L1240] seed (when MC is involved)
)


def test_alpha_basis_declares_the_whole_calibration_report():
    '''[L1239]-[L1240] + [L636]: alpha_basis is the CalibrationReport as a
    whole - the audit chain closes here, so every report column is declared.'''
    declared = set(type(build_provenance().alpha_basis).model_fields)
    assert declared == set(ALPHA_BASIS_FIELDS)


def test_alpha_basis_values_land_on_the_h4_types():
    ab = build_provenance().alpha_basis
    assert isinstance(ab.alpha_star, Decimal)
    assert isinstance(ab.candidate_alpha_matrix[Decimal('0.3')][METRIC_A],
                      Decimal)
    assert all(type(k) is Decimal for k in ab.candidate_alpha_matrix)
    assert all(type(k) is Decimal for k in ab.excluded_alphas)
    assert type(ab.seed) is int
    assert ab.run_id == 'SYN-RUN-001'
    assert list(ab.window_periods) == ['2026-01', '2026-02', '2026-03']
    assert list(ab.binding_constraints) == ['drift_budget']


@pytest.mark.parametrize('probe', [True, False, '20260101', 20260101.0,
                                   Decimal('20260101'), b'7'])
def test_seed_rejects_every_lax_int_form(probe):
    '''H-4: seed is a count-like exact int column ([L1240]).'''
    with pytest.raises(ValidationError):
        build_with(('alpha_basis', 'seed'), probe)


def test_excluded_alpha_reason_accepts_a_registered_code():
    '''[L1240] + H-6/H-7: excluded alphas carry registered reasons.'''
    ab = build_provenance().alpha_basis
    assert ab.excluded_alphas[Decimal('0.3')] == RC.ALPHA_INFEASIBLE.value


@pytest.mark.parametrize('bad', [
    'MADE_UP', 'alpha_infeasible', 'RC.ALPHA_INFEASIBLE', '', None, 5,
])
def test_excluded_alpha_reason_rejects_unregistered_forms(bad):
    with pytest.raises(ValidationError):
        build_with(('alpha_basis', 'excluded_alphas', Decimal('0.3')), bad)


def test_alpha_string_keys_land_on_decimal_through_the_ratio_gate():
    '''ORCH-20 ruling 5 / H-4: an alpha key arriving as a numeric string
    passes the Ratio gate and lands as Decimal, so no ratio ever bypasses
    the numeric contract and [L1072]'s lexicographic alpha search stays
    correct ('0.10' < '0.3' is a str-order trap, Decimal order is not).'''
    payload = provenance_payload()
    payload['alpha_basis']['candidate_alpha_matrix'] = {
        '0.3': {METRIC_A: '0.01'},
    }
    payload['alpha_basis']['excluded_alphas'] = {
        '0.3': RC.ALPHA_INFEASIBLE.value,
    }
    prov = models.WeightProvenance(**payload)
    assert list(prov.alpha_basis.candidate_alpha_matrix) == [Decimal('0.3')]
    assert list(prov.alpha_basis.excluded_alphas) == [Decimal('0.3')]


@pytest.mark.parametrize('field_name', ['candidate_alpha_matrix',
                                        'excluded_alphas'])
def test_alpha_dict_keys_reject_float(field_name):
    '''ORCH-20 ruling 5: a float alpha key dodges the string-built Decimal
    contract (H-4) and the eq_tol comparison discipline (H-11).'''
    payload = provenance_payload()
    if field_name == 'candidate_alpha_matrix':
        payload['alpha_basis'][field_name] = {0.3: {METRIC_A: '0.01'}}
    else:
        payload['alpha_basis'][field_name] = {
            0.3: RC.ALPHA_INFEASIBLE.value}
    with pytest.raises(ValidationError):
        models.WeightProvenance(**payload)


def test_seed_accepts_none_when_the_calibration_has_no_mc():
    '''ORCH-20 ruling 6 / [L636]: "seed (若含 MC)" - a calibration
    without Monte-Carlo has no seed; None is legal while every lax int
    form stays rejected by the gate above.'''
    prov = build_with(('alpha_basis', 'seed'), None)
    assert prov.alpha_basis.seed is None


# ---------------------------------------------------------------------------
# 7. whatif_run_id [L1241]; the FROZEN coupling stays in config (S1-T06).
# ---------------------------------------------------------------------------
def test_whatif_run_id_accepts_a_run_number():
    assert build_provenance().whatif_run_id == 'SYN-WHATIF-001'


def test_whatif_run_id_accepts_none():
    '''[L1241]: "FROZEN 而缺此项 → 配置加载直接失败" is a CONFIG loading rule
    ([L880], [L1281], C-01 [L900], P-11 [L1435]); S1-T06 owns it. The models
    layer only declares the nullable column - None constructs fine here.'''
    assert build_provenance(whatif_run_id=None).whatif_run_id is None


def test_models_layer_does_not_grow_a_status_column_for_the_frozen_rule():
    '''Guard fixing the layering: status lives on WeightVersionDoc [L1190];
    WeightProvenance must not re-declare it to "help" the config check.'''
    assert 'status' not in models.WeightProvenance.model_fields
    assert 'status' in models.WeightVersionDoc.model_fields


# ---------------------------------------------------------------------------
# 8. Sign-off quartet [L1242], deliberately duplicated per [L1191]/[L1194].
# ---------------------------------------------------------------------------
SIGNOFF = ('approved_by', 'approved_date', 'effective_from', 'effective_to')


def test_provenance_declares_the_signoff_quartet_with_typed_dates():
    prov = build_provenance()
    declared = set(type(prov).model_fields)
    assert set(SIGNOFF) <= declared
    assert prov.approved_by == 'SYN-COMMITTEE'
    assert type(prov.approved_date) is date
    assert type(prov.effective_from) is date
    assert type(prov.effective_to) is date


@pytest.mark.parametrize('field', ['approved_date', 'effective_from',
                                   'effective_to'])
def test_provenance_date_columns_reject_non_iso_literals(field):
    with pytest.raises(ValidationError):
        build_provenance(**{field: '10-01-2026'})


def test_interview_dates_land_as_dates_and_reject_junk():
    '''[L1232]: interview dates are date columns (ISO, [L889] discipline).'''
    prov = build_provenance()
    assert all(type(d) is date for d in prov.ahp.interview_dates)
    with pytest.raises(ValidationError):
        build_with(('ahp', 'interview_dates'), ['not-a-date'])


def test_signoff_quartet_exists_on_both_levels_by_design():
    '''[L1191]/[L1194] put the quartet on the T6 doc AND [L1242] repeats it
    inside provenance. The duplication is intentional in the SDD text, so
    both declarations must coexist (P-11 [L1435] reads the provenance copy
    for FROZEN completeness; C-01 [L900] reads the doc copy).'''
    doc_fields = set(models.WeightVersionDoc.model_fields)
    assert set(SIGNOFF) <= doc_fields  # S1-T02 asset, passes today
    prov_fields = set(models.WeightProvenance.model_fields)
    assert set(SIGNOFF) <= prov_fields


# ---------------------------------------------------------------------------
# 9. WeightVersionDoc.provenance wiring [L1193] + V-5 [L871].
# ---------------------------------------------------------------------------
def test_weight_version_doc_accepts_a_full_provenance():
    '''[L1193]: provenance.* see §3.11.4. RED shape today: extra=forbid
    ([L865]) rejects the undeclared column with a ValidationError.'''
    doc = models.WeightVersionDoc(
        **{**WEIGHT_DOC, 'provenance': provenance_payload()})
    assert isinstance(doc.provenance, models.WeightProvenance)
    assert doc.provenance.kind == 'AHP_ENTROPY_COMBINED'
    assert doc.provenance.ahp.expert_count == 2


def test_weight_version_doc_without_provenance_still_builds():
    '''The S1-T02 payload (no provenance) must keep building so the 341
    existing cases stay green: the column is nullable at the models layer,
    and "FROZEN must carry full provenance" is enforced by config loading
    ([L880], [L1435]; S1-T06), never by a models-layer default.'''
    doc = models.WeightVersionDoc(**WEIGHT_DOC)
    assert doc.provenance is None  # RED today: AttributeError, column absent


def test_provenance_column_rejects_a_non_model_value():
    '''[L1193]: the column is typed WeightProvenance, not free text/dict.'''
    with pytest.raises(ValidationError):
        models.WeightVersionDoc(
            **{**WEIGHT_DOC, 'provenance': 'SYN-NOT-A-MODEL'})


def test_provenance_model_is_frozen_and_forbid():
    '''[L865] unified config: frozen=True, extra=forbid (V-5, [L871]).'''
    cfg = models.WeightProvenance.model_config
    assert cfg.get('frozen') is True
    assert cfg.get('extra') == 'forbid'


def test_provenance_instance_is_immutable():
    prov = build_provenance()
    with pytest.raises(ValidationError):
        prov.whatif_run_id = 'SYN-WHATIF-002'


@pytest.mark.parametrize('name', SEGMENTS)
def test_segment_instances_are_immutable(name):
    prov = build_provenance()
    seg = getattr(prov, name)
    first = next(iter(type(seg).model_fields))
    with pytest.raises(ValidationError):
        setattr(seg, first, getattr(seg, first))


def test_provenance_rejects_an_undeclared_field():
    '''V-5 [L871]: an undeclared field must be an error, never a silent
    default ([L1902]: extra columns are breaking contract changes).'''
    with pytest.raises(ValidationError):
        build_provenance(bogus_field='SYN-NOPE')


@pytest.mark.parametrize('name', SEGMENTS)
def test_segments_reject_an_undeclared_field(name):
    payload = provenance_payload()
    payload[name]['bogus_field'] = 'SYN-NOPE'
    with pytest.raises(ValidationError):
        models.WeightProvenance(**payload)

# ---------------------------------------------------------------------------
# 10. H-4 numeric discipline, parametrized per column: every ratio-shaped
#     field rejects float/bool and lands on Decimal from strings; every
#     count-shaped field rejects lax int forms.
# ---------------------------------------------------------------------------
RATIO_PATHS = (
    ('ahp', 'lambda_max'),                                            # [L1232]
    ('ahp', 'ci'),                                                    # [L1232]
    ('ahp', 'ri'),                                                    # [L1232]
    ('ahp', 'cr'),                                                    # [L1232]
    ('ahp', 'max_method_gap'),                                        # [L1233]
    ('ahp', 'weights_geometric', METRIC_A),                           # [L1233]
    ('ahp', 'weights_eigenvector', METRIC_B),                         # [L1233]
    ('ahp', 'comparison_matrices', EXPERT_1, METRIC_A, METRIC_B),     # [L1232]
    ('entropy', 'per_period_entropy', '2026-01', METRIC_A),           # [L1234]
    ('entropy', 'median_entropy', METRIC_A),                          # [L1234]
    ('entropy', 'drift_by_metric', METRIC_A),                         # [L1234]
    ('combine', 'alpha'),                                             # [L1236]
    ('combine', 'comparison_by_metric', METRIC_A, 'ahp_weight'),      # [L1237]
    ('combine', 'comparison_by_metric', METRIC_A, 'entropy_weight'),  # [L1237]
    ('combine', 'comparison_by_metric', METRIC_B, 'combined_weight'), # [L1237]
    ('alpha_basis', 'alpha_star'),                                    # [L1239]
    ('alpha_basis', 'candidate_alpha_matrix', Decimal('0.3'), METRIC_A),  # [L1239]
)


@pytest.mark.parametrize('path', RATIO_PATHS)
@pytest.mark.parametrize('bad', [0.5, 1.0, 0.7, True, False])
def test_every_ratio_shaped_column_rejects_float_and_bool(path, bad):
    '''H-4: ratios/weights are Decimal built from strings (numeric.D gate);
    float enters the system only via numeric.from_float, never via a model
    column. [L1923] ④ repeats the exact-numeric invariant for CEL too.'''
    with pytest.raises(ValidationError):
        build_with(path, bad)


@pytest.mark.parametrize('path', RATIO_PATHS)
def test_every_ratio_shaped_column_lands_on_decimal_from_a_string(path):
    prov = build_with(path, '0.5')
    landed = get_at(prov, path)
    assert type(landed) is Decimal
    assert landed == Decimal('0.5')


INT_PATHS = (
    ('ahp', 'expert_count'),   # [L1232] expert head count
    ('alpha_basis', 'seed'),   # [L1240]
)


@pytest.mark.parametrize('path', INT_PATHS)
@pytest.mark.parametrize('bad', [True, False, 3.0, '3', Decimal('3'), b'3'])
def test_every_count_column_rejects_lax_int_forms(path, bad):
    '''H-4 / ORCH-18: count columns take a real Python int only.'''
    with pytest.raises(ValidationError):
        build_with(path, bad)


@pytest.mark.parametrize('path', INT_PATHS)
def test_every_count_column_lands_on_an_exact_int(path):
    prov = build_with(path, 4)
    landed = get_at(prov, path)
    assert type(landed) is int
    assert landed == 4


# ---------------------------------------------------------------------------
# 11. H-5 AST scan: the provenance classes are pure containers - no business
#     literal defaults anywhere (static audit style of test_models_input.py).
# ---------------------------------------------------------------------------
def _provenance_class_names():
    '''Resolve the class names at runtime from the contract itself, so the
    scan cannot drift from what the fields actually declare. Segment
    annotations are Optional[...] per ORCH-20 ruling 1, hence the Union
    unwrapping in _segment_class.'''
    cls = models.WeightProvenance
    names = [cls.__name__]
    for seg in SEGMENTS:
        names.append(
            _segment_class(cls.model_fields[seg].annotation).__name__)
    combine_cls = _segment_class(cls.model_fields['combine'].annotation)
    entry_ann = combine_cls.model_fields['comparison_by_metric'].annotation
    names.append(_unwrap(get_args(entry_ann)[1]).__name__)
    return names


def test_no_provenance_class_carries_a_business_literal_default():
    '''H-5: weights/thresholds/targets are PLACEHOLDER governance values, so
    every column of WeightProvenance and its segments is a container whose
    only legal default is None. Numeric or scalar defaults would smuggle in
    invented business values.'''
    names = set(_provenance_class_names())
    source = Path(models.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    found = set()
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name in names):
            continue
        found.add(node.name)
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign) or stmt.value is None:
                continue
            default = stmt.value
            legal = isinstance(default, ast.Constant) and default.value is None
            assert legal, (
                node.name + ' carries a non-None field default (H-5): '
                + ast.unparse(default))
    assert found == names, (
        'provenance classes missing from models.py: '
        + ', '.join(sorted(names - found)))


def test_calibration_report_name_is_not_occupied_in_models():
    '''ORCH-20 ruling 3: [L1072] CalibrationReport is the return type of
    weights_calibrate.py (L0b, S7); dsm/models.py must not occupy the name
    (H-9 layer clarity). The alpha_basis segment class is named apart.
    Regression guard: passes today and must keep passing after R2.'''
    assert not hasattr(models, 'CalibrationReport')


# ---------------------------------------------------------------------------
# 12. EvidenceSource [L1895]/[L870] + ORCH-15: defined, but never an input.
# ---------------------------------------------------------------------------
def test_evidence_source_literal_is_declared():
    '''[L1895]: evidence_source ∈ {CARD_ONLY, CEL_ESTIMATED}. S1-T03 only
    defines the Literal contract; consumers are ScoreCardRow (S1-T04,
    [L870]) and EvidenceFrame (S5-T01, ORCH-15).'''
    assert get_args(models.EvidenceSource) == ('CARD_ONLY', 'CEL_ESTIMATED')


ALL_INPUT_ROWS = (
    'StrategyMasterRow', 'MetricDictRow', 'MetricFactRow', 'DesignCardRow',
    'RedlineRow', 'WeightVersionDoc', 'GradeRuleRow', 'AnchorSetDoc',
)


def test_evidence_source_never_joins_an_input_row():
    '''ORCH-15: evidence_source is a verdict computed by evidence.py, not an
    input fact; it must not appear on any of the 8 input rows (regression:
    passes today and must keep passing after S1-T03 lands).'''
    for row_name in ALL_INPUT_ROWS:
        row_cls = getattr(models, row_name)
        assert 'evidence_source' not in row_cls.model_fields, row_name


DESIGN_CARD_FIELDS_S1_T02 = frozenset({
    'strategy_id', 'version_id', 'direct_goal', 'process_metrics',
    'result_metrics', 'observation_window', 'data_source', 'data_timeliness',
    'eval_method', 'control_arrangement', 'success_criteria',
    'risk_constraints', 'eval_owner', 'alt_method_note',
    'interpretation_limit', 'card_status',
    'incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
    'estimator_method', 'experiment_id', 'holdout_id', 'mde_ok',
})


def test_design_card_row_field_set_is_unchanged_from_s1_t02():
    '''Regression: S1-T03 adds no column to DesignCardRow - the CEL-0 reserve
    was completed in S1-T02 and ORCH-15 forbids the evidence_source addition.
    Passes today; any drift means a breaking contract change ([L1902]).'''
    assert frozenset(models.DesignCardRow.model_fields) == DESIGN_CARD_FIELDS_S1_T02


CEL0_RESERVED = (
    'incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
    'estimator_method', 'experiment_id', 'holdout_id', 'mde_ok',
)


def test_cel0_reserve_stays_at_exactly_seven_fields():
    '''[L1918] + ORCH-02: the T4 extension is the SEVEN fields of §5.8.1;
    interpretation_limit is a formal field ([L1172]), not a CEL-0 reserve,
    notwithstanding the eight-item row of [L1894].'''
    declared = set(models.DesignCardRow.model_fields)
    assert set(CEL0_RESERVED) <= declared
    assert len(CEL0_RESERVED) == 7
    assert 'interpretation_limit' in declared
    assert 'interpretation_limit' not in CEL0_RESERVED


@pytest.mark.parametrize('field_name', CEL0_RESERVED)
def test_cel0_reserve_fields_stay_nullable_with_none_default(field_name):
    '''[L1890]/[L1894]: reserve fields are all nullable, no logic in v1;
    regression guard so S1-T03 cannot tighten the S1-T02 asset.'''
    info = models.DesignCardRow.model_fields[field_name]
    assert info.default is None


# ---------------------------------------------------------------------------
# 13. ORCH-21 targeted fixes: pin the ORCH-20 ruling-3 naming table (13-3),
#     and the nullable calibration_report_ref column (ruling 9).
# ---------------------------------------------------------------------------
def test_orch20_ruling3_naming_table_is_pinned():
    '''ORCH-21 disposition 13-3 / ORCH-20 ruling 3: every other test reaches
    the segment classes through _segment_class(annotation), so the approved
    naming table has no test pinning it and a future rename would stay green.
    Pin it: the five class names exist, the four segments resolve to them in
    order, the comparison entry is MetricWeightComparison, and CalibrationReport
    stays unoccupied ([L1072], ORCH-20 ruling 3-3).'''
    for name in ('AhpSegment', 'EntropySegment', 'MetricWeightComparison',
                 'CombineSegment', 'AlphaBasisSegment'):
        assert hasattr(models, name), 'missing class: ' + name
    ordered = ('ahp', 'entropy', 'combine', 'alpha_basis')
    expected = ('AhpSegment', 'EntropySegment', 'CombineSegment',
                'AlphaBasisSegment')
    resolved = tuple(
        _segment_class(
            models.WeightProvenance.model_fields[s].annotation).__name__
        for s in ordered)
    assert resolved == expected
    combine_cls = _segment_class(
        models.WeightProvenance.model_fields['combine'].annotation)
    entry_ann = combine_cls.model_fields['comparison_by_metric'].annotation
    assert _unwrap(get_args(entry_ann)[1]).__name__ == 'MetricWeightComparison'
    assert hasattr(models, 'CalibrationReport') is False


def test_calibration_report_ref_accepts_none_when_alpha_is_manual():
    '''ORCH-21 ruling 9 / [L634] + [L1236]: when the calibration is skipped
    (alpha = 1, ENTROPY_INSUFFICIENT_SAMPLE [L634]) or alpha_source is MANUAL
    ([L1236] closes the set to CALIBRATED | MANUAL), no CalibrationReport
    ([L636]) exists to reference, so calibration_report_ref is nullable and no
    audit-looking ref string is fabricated (H-5). A MANUAL combine with
    calibration_report_ref=None builds and lands as None; a provided str still
    lands as that str (positive direction preserved).'''
    payload = provenance_payload()
    payload['combine']['alpha_source'] = 'MANUAL'
    payload['combine']['calibration_report_ref'] = None
    prov = models.WeightProvenance(**payload)
    assert prov.combine.alpha_source == 'MANUAL'
    assert prov.combine.calibration_report_ref is None
    prov2 = build_with(('combine', 'calibration_report_ref'),
                       'SYN-CAL-REPORT-002')
    assert isinstance(prov2.combine.calibration_report_ref, str)
    assert prov2.combine.calibration_report_ref == 'SYN-CAL-REPORT-002'
