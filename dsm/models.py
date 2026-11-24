'''dsm.models -- the DSM contract layer L1: the eight input rows (design doc
3.3.3), the WeightProvenance snapshot chain (3.11.4, [L1228]-[L1245]) and the
EvidenceSource literal ([L1895]).

Pure declaration layer: contracts only, no computation, no I/O, no defaults that
would smuggle in a business number.

Contract rules this module implements (all [LNNN] are docs/digest line refs):

  * [L865] every row is a pydantic v2 model with ConfigDict(frozen=True,
    extra='forbid'); an undeclared column therefore errors out instead of being
    dropped, which is the V-5 guard of [L871].
  * [L1265] money is an int in minor currency units and compares exactly, the
    chain never passes through float                -> MoneyMinor
  * [L1267] ratio / attainment / weight / mean is a Decimal built from a string
    and compares with a 1e-12 tolerance             -> Ratio
  * ORCH-07: a raw float is never coerced. It is rejected at the field boundary
    and may only enter through the audited bridge numeric.from_float(); bool is
    rejected as well, because it is an int subclass. Both helpers live in
    dsm/numeric.py, which is the single source of numeric semantics ([L1829]).
  * [L1138]-[L1139] target_value and [L1181] threshold_value are unit
    polymorphic columns, so neither is declared as a static Ratio: [L1265] money
    and [L1266] counts are ints, only [L1267] ratios are Decimal. MetricDictRow
    owns the unit column as well and cross-checks the shape of the target it
    carries; RedlineRow has no unit column ([L1180] names metric_id only), so
    the threshold-versus-unit agreement is left to the semantic checks of [L879]
    (S1-T06) and is not pre-implemented here. DURATION_SEC gets no shape rule:
    [L1265]-[L1267] close money, counts and ratios only, and 10.2-4 forbids
    inventing one for seconds.
  * [L1137] direction: strict=True cannot be bound to a Literal, so a type gate
    in front of Literal[1, -1] refuses bool, float, Decimal and digit strings
    instead of letting the lax int coercion turn True into 1 or 1.0 into 1.
  * ORCH-18: the same lax leak is closed on every remaining int-semantic and
    bool column by two reusable gates. StrictInt ([L1204] promotion_streak
    counts periods) lands only a real int -- bool, float, Decimal and digit
    strings are refused; StrictBool ([L1140][L1174][L1184][L1203]) lands only
    a Python bool, because reading 1 or 'yes' as True is a silent
    reinterpretation without a reason_code (H-6, V-14). CSV text to bool/int
    conversion is the explicit job of io_loaders ([L889], ORCH-18 ruling 3).
  * [L1183] reason_code: the code reaches the ledger and the report, so it has
    to resolve in the dsm.reason_codes registry (V-14, no silent degradation);
    is_registered also covers the per-metric dynamic codes of [L993]. Not one
    code is spelled out in this module (H-7).
  * [L1137][L1123][L1134][L1136][L1138][L1151][L1166][L1167][L1173][L1180]
    [L1181][L1190][L1200][L1895]: columns whose value set the digest closes are
    typing.Literal aliases. Columns the digest leaves open ('EXISTING, NEW 等'
    [L1120], 'CLIP_P1_P99' [L1135], the dim registry [L1131]) stay str: D7 makes
    them config driven, so no closed set is invented here.
  * [L889] date columns must be ISO: online_date / offline_date / signoff_date /
    effective_from / effective_to / approved_date are datetime.date and
    snapshot_time is datetime.datetime, so a non ISO literal fails validation.
    Nothing here reads the wall clock ([L1271], H-8): run time is injected by
    the CLI (--run-at [L1089]) and belongs to upper layers.
  * [L1174] the seven CEL-0 fields are reserved and nullable; they carry no
    behaviour in this version ([L1890]). interpretation_limit is a formal
    nullable field ([L1172], ORCH-02), not one of the seven.

WeightProvenance, its four segments and the EvidenceSource literal have now
landed (S1-T03), and the seven CEL-0 reserves were already declared on
DesignCardRow at HEAD (S1-T02), so neither is out of scope any more. Still
not in scope (ORCH-13): the six output models and the eight intermediate
Frames / PoolStats / ScoringContext (S1-T04),
PLACEHOLDER interception and the semantic checks of 3.3.4 [L879]-[L880]
(S1-T05/S1-T06). The digest wordings 'default L4' [L1182] and 'default L3'
[L1206] are therefore not modelled as defaults here (H-5): a field is either
required or nullable, and the loading layer supplies the signed-off value.

Layering (H-9): L1 may import L1 only, hence dsm.numeric and nothing above it.

S1-T04 landed that output half of the contract: the six output models,
the eight intermediate models, ScoringContext and the sub-models ORCH-22
ruling 33 authorises are appended below the input models, and no
pre-existing model changed (ruling 34). What stays out of scope is
unchanged: PLACEHOLDER interception and the semantic checks of 3.3.4
[L879]-[L880] (S1-T05/S1-T06), plus everything the rulings assign to a
higher layer - the [L1053] canonical serializer and the [L1052]
reproducibility_hash (audit.py, S6), the [L1040] status thresholds and
drift budget (S8-T01, B-018), the pool-share denominators (S5, B-020)
and the ReportSet of [L1062] (S6, B-021).
'''
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator

from dsm import numeric
from dsm import reason_codes

__all__ = [
    'AhpSegment',
    'AlphaBasisSegment',
    'AnchorSetDoc',
    'AttainmentFrame',
    'AttainmentRow',
    'AuditBundle',
    'CombineSegment',
    'DesignCardRow',
    'DowngradeAction',
    'EntropyDiagnosticRow',
    'EntropySegment',
    'EntropyStatus',
    'EvidenceFrame',
    'EvidenceMode',
    'EvidenceRow',
    'EvidenceSource',
    'FrameGrade',
    'GradeFrame',
    'GradeLedgerRow',
    'GradeRow',
    'GradeRuleRow',
    'InputFingerprints',
    'InputTableFingerprint',
    'MethodAgreement',
    'MetricDictRow',
    'MetricFactRow',
    'MetricWeightComparison',
    'MoneyMinor',
    'NormalizationMethod',
    'NormalizedFrame',
    'NormalizedRow',
    'PoolFrame',
    'PoolKey',
    'PoolRow',
    'PoolStatRow',
    'PoolStats',
    'PreflightFinding',
    'Ratio',
    'RedlineEvalRow',
    'RedlineFrame',
    'RedlineRow',
    'SchemeName',
    'ScoreCardDimCell',
    'ScoreCardMetricCell',
    'ScoreCardRow',
    'ScoreFrame',
    'ScoreOperator',
    'ScoreRow',
    'ScoringContext',
    'SensitivityReport',
    'SensitivitySchemeResult',
    'SensitivityStrategyRow',
    'StabilityLabel',
    'StrategyMasterRow',
    'StrictBool',
    'StrictInt',
    'TriangulationReport',
    'TriangulationStrategyRow',
    'WeightProvenance',
    'WeightVersionDoc',
]

# ---------------------------------------------------------------------------
# ORCH-07 annotated scalar types ([L1265]-[L1267]).
#
# numeric.as_minor already is the money contract of [L1265]: it refuses float and
# bool (through numeric.D), refuses a fractional Decimal, accepts an int, a
# lossless numeric string or an integral Decimal, and returns a plain int.
# numeric.D is the ratio contract of [L1267]: Decimal built from a string, never
# from a float. Wrapping them in BeforeValidator keeps both usable as type
# annotations -- a probe model can bind them directly, and any ValueError they
# raise is collected by pydantic into a ValidationError.
# ---------------------------------------------------------------------------
MoneyMinor = Annotated[int, BeforeValidator(numeric.as_minor)]
Ratio = Annotated[Decimal, BeforeValidator(numeric.D)]

# A fact value is unit dependent ([L1150] money in minor units, [L1138] unit can
# be RATIO), so the three value columns take either shape: money lands as an
# exact int, ratios as a Decimal. A float matches neither and is rejected.
FactValue = MoneyMinor | Ratio

# ---------------------------------------------------------------------------
# Unit-polymorphic columns ([L1138]-[L1139], [L1181]).
#
# target_value and threshold_value carry the shape their unit declares, so they
# cannot be a static Ratio. MoneyMinor accepts an integral Decimal and returns
# an int, which would let a Decimal arrive in a money column and erase exactly
# the mismatch the unit column states, so the money branch here is gated on the
# raw type first and only then handed to numeric.as_minor: int lands on int,
# Decimal lands on Decimal, float and bool land on neither (H-4).
# ---------------------------------------------------------------------------
def _exact_minor_units(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise numeric.NumericError(
            'minor-unit column needs an int, got ' + type(value).__name__)
    return numeric.as_minor(value)


MinorUnits = Annotated[int, BeforeValidator(_exact_minor_units)]
UnitValue = MinorUnits | Ratio

# The unit values [L1265]-[L1266] close to int. DURATION_SEC is deliberately
# absent: the digest states no shape rule for seconds.
INT_SHAPE_UNITS = ('MONEY_MINOR', 'COUNT')

# [L1137]: +1 / -1 and nothing else. strict=True cannot be applied to a Literal,
# so the gate removes the lax coercion that maps True, 1.0, Decimal('1') and
# '1' onto the int 1.
def _exact_direction(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise numeric.NumericError(
            'direction needs an int, got ' + type(value).__name__)
    return value


# [L1183]: a reason_code is a governance identifier, so it must resolve in the
# registry of dsm.reason_codes -- which also resolves the per-metric dynamic
# codes of [L993]. This module spells no code out on its own (H-7).
def _registered_reason_code(value):
    if not reason_codes.is_registered(value):
        raise ValueError('unregistered reason_code: ' + str(value))
    return value


ReasonCode = Annotated[str, BeforeValidator(_registered_reason_code)]

# ---------------------------------------------------------------------------
# Closed enum sets, copied verbatim from the digest.
# ---------------------------------------------------------------------------
StrategyStatus = Literal['ACTIVE', 'PAUSED', 'RETIRED']  # [L1123]
MissingRule = Literal['ZERO', 'SKIP', 'IMPUTE_MEDIAN', 'BLOCK']  # [L1134]
AttainmentFormula = Literal[
    'RATIO_DIRECT', 'INVERSE_RATIO', 'SHORTFALL_CLAMPED', 'INTERVAL']  # [L1136]
# [L1137] +1 bigger is better, -1 smaller, wrapped in the type gate above.
MetricDirection = Annotated[
    Literal[1, -1], BeforeValidator(_exact_direction)]

# ORCH-18 rulings 1/2: reusable strict gates for the plain int and bool
# columns. A bare annotation keeps pydantic's lax coercion (True -> 1,
# 1.0 -> 1, 'yes' -> True) and Field(strict=True) cannot bind a Literal, so
# both gates run in front of the type as BeforeValidator, exactly like the
# direction gate above. bool is an int subclass, hence the explicit
# isinstance check; Decimal, float, str and bytes are refused as well (H-4).
def _strict_int(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise numeric.NumericError(
            'int column needs an int, got ' + type(value).__name__)
    return value


def _strict_bool(value):
    if not isinstance(value, bool):
        raise numeric.NumericError(
            'bool column needs a Python bool, got ' + type(value).__name__)
    return value


StrictInt = Annotated[int, BeforeValidator(_strict_int)]
StrictBool = Annotated[bool, BeforeValidator(_strict_bool)]
MetricUnit = Literal['MONEY_MINOR', 'COUNT', 'RATIO', 'DURATION_SEC']  # [L1138]
DataQualityFlag = Literal['OK', 'PARTIAL', 'SUSPECT', 'STALE']  # [L1151]
EvalMethod = Literal[
    'AB_TEST', 'RCT', 'HOLDOUT', 'DID', 'SYNTHETIC_CONTROL', 'GEO',
    'SWITCHBACK', 'PSM', 'OBSERVATIONAL_ONLY']  # [L1166]
ControlArrangement = Literal[
    'NONE', 'HISTORICAL_BASELINE', 'CONCURRENT_CONTROL', 'RANDOMIZED']  # [L1167]
CardStatus = Literal['COMPLETE', 'PARTIAL', 'MISSING']  # [L1173]
RedlineLevel = Literal['HARD', 'SOFT']  # [L1180]
Comparator = Literal['GT', 'GTE', 'LT', 'LTE']  # [L1181]
WeightVersionStatus = Literal['DRAFT', 'FROZEN']  # [L1190]
GradeCode = Literal['L1', 'L2', 'L3', 'L4']  # [L1200]
EvidenceClass = Literal['A', 'B', 'C', 'D']  # [L1895]
EvidenceSource = Literal['CARD_ONLY', 'CEL_ESTIMATED']  # [L1895]


class _InputRow(BaseModel):
    '''Shared config of the eight input rows: frozen + extra=forbid [L865].'''

    model_config = ConfigDict(frozen=True, extra='forbid')


class StrategyMasterRow(_InputRow):
    '''T1 strategy_master, grain strategy x version ([L1099], [L1112]-[L1124]).'''

    strategy_id: str  # [L1116] identity, stable across versions
    version_id: str  # [L1117] any content change is a new version
    strategy_name: str  # [L1118]
    biz_domain: str  # [L1119] first pooling dimension
    scene_code: str  # [L1120] open code set
    segment_type: str  # [L1120] EXISTING, NEW etc: open, not a Literal
    online_date: date  # [L1121] ISO [L889]
    offline_date: date | None = None  # [L1121] still on line -> no value
    owner_dept: str  # [L1122]
    owner_name: str  # [L1122]
    status: StrategyStatus  # [L1123]
    version_change_note: str | None = None  # [L1124] feeds VERSION_BREAK


class MetricDictRow(_InputRow):
    '''T2 metric_dict, grain metric ([L1100], [L1126]-[L1143]).'''

    metric_id: str  # [L1130]
    metric_name: str  # [L1130]
    dim_code: str  # [L1131] config driven registry, no Literal (D7)
    numerator_def: str  # [L1132] verbatim, signable
    denominator_def: str | None = None  # [L1132] mandatory for ratio metrics
    time_window: str  # [L1133] open code set
    dedup_rule: str  # [L1133] open code set
    missing_rule: MissingRule  # [L1134]
    outlier_rule: str  # [L1135] e.g. CLIP_P1_P99: open, not a Literal
    attainment_formula: AttainmentFormula  # [L1136]
    direction: MetricDirection  # [L1137] +1 bigger is better, -1 smaller
    unit: MetricUnit  # [L1138] decides the shape of target_value
    target_value: UnitValue | None  # [L1139] int or Decimal, per unit, or absent
    target_basis: str  # [L1139] budget / history / benchmark, traceable
    is_redline: StrictBool  # [L1140] true -> excluded from the entropy weights (D2)
    owner_name: str  # [L1141]
    signoff_status: str  # [L1141] open code set
    signoff_date: date | None = None  # [L1141] absent while unsigned
    dim_signoff_status: str  # [L1142] v1.1, open code set
    dict_version: str  # [L1143]
    caliber_version: str  # [L1143] must match the facts, C-07

    @model_validator(mode='after')
    def _target_shape_matches_unit(self):
        '''[L1138]-[L1139]: the unit column says what target_value means, so the
        row cross-checks the two columns it owns against [L1265]-[L1267] instead
        of letting a Decimal announce "money is a Decimal". A missing target is
        a legal state and is skipped: [L930] keeps attainment null and the
        absence is disclosed upstream by its own registered code, so nothing is
        invented here (H-5).
        '''
        target = self.target_value
        if target is None:
            return self
        if self.unit in INT_SHAPE_UNITS:
            if type(target) is not int:
                raise ValueError('unit ' + self.unit + ' needs an int target')
        elif self.unit == 'RATIO':
            if type(target) is not Decimal:
                raise ValueError('unit RATIO needs a Decimal target')
        return self


class MetricFactRow(_InputRow):
    '''T3 metric_facts, long table, grain strategy x version x period x metric
    ([L1145]-[L1156]). A missing metric is a missing row, not an empty column.
    '''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    metric_id: str  # [L1149] locator key
    value_num: FactValue  # [L1150] numerator, money in minor units
    value_den: FactValue | None = None  # [L1150] denominator of a ratio metric
    value: FactValue  # [L1150] the fact itself
    data_quality_flag: DataQualityFlag  # [L1151] SUSPECT is dropped, C-06
    snapshot_time: datetime  # [L1152] ISO [L889]; freshness C-05
    data_as_of: date  # [L1152] ISO [L889]
    source_table: str  # [L1153]
    caliber_version: str  # [L1154] must equal metric_dict, C-07


class DesignCardRow(_InputRow):
    '''T4 design_cards, grain strategy x version ([L1102], [L1158]-[L1174]).

    strategy_id / version_id are the table grain of [L1102]; the field list of
    [L1162]-[L1174] names the payload columns.
    '''

    strategy_id: str  # [L1102]
    version_id: str  # [L1102]
    direct_goal: str  # [L1162]
    process_metrics: tuple[str, ...]  # [L1163]
    result_metrics: tuple[str, ...]  # [L1163]
    observation_window: str  # [L1164]
    data_source: str  # [L1165]
    data_timeliness: str  # [L1165]
    eval_method: EvalMethod  # [L1166]
    control_arrangement: ControlArrangement  # [L1167]
    success_criteria: str  # [L1168]
    risk_constraints: str  # [L1169] fed to the redline judgement
    eval_owner: str  # [L1170]
    alt_method_note: str | None = None  # [L1171]
    interpretation_limit: str | None = None  # [L1172] formal, C class must fill
    card_status: CardStatus  # [L1173]
    # CEL-0 reserved, all nullable, no behaviour in v1 ([L1174], [L1894]-[L1896])
    incremental_value: FactValue | None = None
    incremental_ci_lower: FactValue | None = None
    incremental_ci_upper: FactValue | None = None
    estimator_method: str | None = None
    experiment_id: str | None = None
    holdout_id: str | None = None
    mde_ok: StrictBool | None = None


class RedlineRow(_InputRow):
    '''T5 redlines, grain metric ([L1103], [L1176]-[L1184]).'''

    metric_id: str  # [L1180]
    level: RedlineLevel  # [L1180] HARD vetoes, SOFT deducts
    comparator: Comparator  # [L1181]
    threshold_value: UnitValue  # [L1181] unit polymorphic; compared via numeric
    forced_grade: GradeCode  # [L1182]
    reason_code: ReasonCode  # [L1183] registered code, never a free string
    waiver_allowed: StrictBool  # [L1184] needs an approval trail to count


# ---------------------------------------------------------------------------
# S1-T03: WeightProvenance and its four snapshot segments ([L1228]-[L1245]),
# plus the EvidenceSource Literal ([L1895]).
#
# Each segment is an independent frozen + extra=forbid sub-model - a data
# snapshot, never a callable (INV-3 type isolation, [L535]). Per ORCH-20:
#   * ruling 1: the four segments are nullable (Optional[...] = None) at the
#     models layer; the FROZEN completeness / kind-conditional presence checks
#     are config-layer policy ([L880], [L1281], [L1435] P-11; S1-T06), never a
#     models-layer default (forcing EXPERT_ONLY / AHP_ONLY to pad an entropy
#     snapshot would invent zero values, H-5).
#   * ruling 3: the alpha_basis class is NOT named CalibrationReport - [L1072]
#     reserves that name for weights_calibrate.py (L0b, S7); it stays out of
#     dsm/models.py (H-9). per_period_entropy / drift_by_metric are the verbatim
#     names of [L1777] (RK-13, ORCH-16).
#   * ruling 5: alpha dict keys are Ratio (Decimal), never str - a str key would
#     dodge the numeric gate (H-4), inflate the candidate set ('0.5' != '0.50')
#     and break the lexicographic minimum-alpha search of [L1072].
#   * ruling 6: alpha_basis.seed ([L636] "seed when MC is involved") and the
#     entropy_weight comparison column ([L1235] INACTIVE zero-variance has no
#     defined entropy weight) are nullable; ahp_weight / combined_weight stay
#     required Ratio and is_fallback stays a required StrictBool so S8-T01 can
#     check "a fallback metric's combined weight equals its AHP weight".
#   * ruling 7 (B-016): hard_check_results fixes only "values are strict bools"
#     (ORCH-18); its key set is NOT closed here (the SDD H-1~H-5 definitions are
#     outside the authorised ranges and belong to S8-T01).
# No business literal default appears in any of these classes (H-5): every
# column is either required or defaults to None.
# ---------------------------------------------------------------------------
class AhpSegment(_InputRow):
    '''AHP derivation snapshot [L1232]-[L1233]: expert pairwise comparison
    matrices, the consistency chain (lambda_max / CI / RI / CR), expert head
    count, interview dates, and both weight methods with their max gap.'''

    comparison_matrices: dict[str, dict[str, dict[str, Ratio]]]  # [L1232] expert x metric x metric
    lambda_max: Ratio  # [L1232]
    ci: Ratio  # [L1232] consistency index
    ri: Ratio  # [L1232] random index
    cr: Ratio  # [L1232] consistency ratio
    expert_count: StrictInt  # [L1232] expert head count (a count, H-4)
    interview_dates: list[date]  # [L1232] ISO [L889]; injected, never wall clock (H-8)
    weights_geometric: dict[str, Ratio]  # [L1233] geometric-mean method weights
    weights_eigenvector: dict[str, Ratio]  # [L1233] eigenvector method weights
    max_method_gap: Ratio  # [L1233] max difference of the two weight sets


class EntropySegment(_InputRow):
    '''Entropy calibration snapshot [L1234]-[L1235]. per_period_entropy and
    drift_by_metric are the verbatim field names of [L1777] (RK-13, ORCH-16).
    excluded_periods values pass the ReasonCode gate (H-6/H-7); period ids stay
    str (ORCH-20 ruling 8).'''

    calibration_periods: list[str]  # [L1234] window period list (identifiers, str)
    per_period_entropy: dict[str, dict[str, Ratio]]  # [L1234]/[L1777] period -> metric -> weight
    median_entropy: dict[str, Ratio]  # [L1234] median entropy weight per metric
    drift_by_metric: dict[str, Ratio]  # [L1234]/[L1777] drift_j per metric
    inactive_fallback_metrics: list[str]  # [L1235] INACTIVE fallback metric ids
    excluded_periods: dict[str, ReasonCode]  # [L1235] excluded period id -> registered reason


class MetricWeightComparison(_InputRow):
    '''One row of the per-metric four-column comparison table [L1237]: AHP
    weight / entropy weight / combined weight / fallback flag. Per ORCH-20
    ruling 6 entropy_weight is nullable (an INACTIVE zero-variance metric has no
    mathematically defined entropy weight; forcing one would invent a business
    number, H-5), while ahp_weight / combined_weight stay required Ratio and
    is_fallback stays a required StrictBool.'''

    ahp_weight: Ratio  # [L1237] AHP value
    entropy_weight: Ratio | None = None  # [L1237] entropy weight value (nullable, ORCH-20 r6)
    combined_weight: Ratio  # [L1237] combined value
    is_fallback: StrictBool  # [L1237] fallback flag (ORCH-18)


class CombineSegment(_InputRow):
    '''AHP/entropy combine snapshot [L1236]-[L1238]: the chosen alpha and its
    source, the calibration report reference, the per-metric four-column
    comparison table, and the H-1~H-5 hard-check results. Per ORCH-20 ruling 7
    (B-016) the models layer fixes only "values are strict bools"; the hard-check
    key set is not closed here (S8-T01).'''

    alpha: Ratio  # [L1236] alpha value
    alpha_source: Literal['CALIBRATED', 'MANUAL']  # [L1236] alpha origin
    # [L1236]/[L634] nullable (ORCH-21 ruling 9): when the calibration is
    # skipped (alpha=1, ENTROPY_INSUFFICIENT_SAMPLE [L634]) or alpha_source is
    # MANUAL [L1236], no CalibrationReport [L636] exists to cite; a required
    # str would force fabricating an audit-looking ref and pollute the [L636]
    # audit chain, so the column is nullable and never invents a reference.
    calibration_report_ref: str | None = None  # [L1236]/[L634] no report to cite
    comparison_by_metric: dict[str, MetricWeightComparison]  # [L1237] metric -> four columns
    hard_check_results: dict[str, StrictBool]  # [L1238] H-1~H-5 results (open key set, r7)


class AlphaBasisSegment(_InputRow):
    '''The whole CalibrationReport snapshot that lands in provenance.alpha_basis
    ([L636]/[L1072]/[L1239]-[L1240]): candidate alpha x metric matrix, alpha*,
    binding constraints, excluded alphas with reasons, window periods, run_id and
    seed. Per ORCH-20 ruling 5 the alpha keys are Ratio (Decimal), never str; per
    ruling 6 seed is nullable ([L636] "seed when MC is involved"). The class is
    deliberately NOT named CalibrationReport - [L1072] reserves that name for
    weights_calibrate.py (L0b, S7), so it stays out of dsm/models.py (ruling 3,
    H-9). Identifier columns (constraint names, period ids, run_id) stay str.'''

    candidate_alpha_matrix: dict[Ratio, dict[str, Ratio]]  # [L636]/[L1239] alpha x metric
    alpha_star: Ratio  # [L636]/[L1239] alpha*
    binding_constraints: list[str]  # [L636]/[L1239] constraint names (identifiers, str)
    excluded_alphas: dict[Ratio, ReasonCode]  # [L636]/[L1240] excluded alpha -> reason
    window_periods: list[str]  # [L636]/[L1240] window period list (identifiers, str)
    run_id: str  # [L636]/[L1240] calibration run id
    seed: StrictInt | None = None  # [L636]/[L1240] seed only when MC is involved (nullable, r6)


class WeightProvenance(_InputRow):
    '''3.11.4 WeightProvenance [L1228]-[L1245] (v1.1 extends AhpProvenance,
    backward compatible): the full derivation chain answering "on what basis does
    this contribution weigh X" - AHP + CR + entropy + alpha calibration - plus
    the whatif run and the sign-off quartet. frozen + extra=forbid ([L865], V-5
    [L871]). The four segments are independent sub-models and nullable at the
    models layer (ORCH-20 ruling 1); their kind-conditional presence and the
    FROZEN completeness rule are config-layer policy ([L880], [L1281], [L1435]
    P-11; S1-T06), never a models-layer default (H-5). No status column here:
    status lives on WeightVersionDoc [L1190], and re-declaring it to "help" the
    FROZEN check would cross the layer boundary.'''

    kind: Literal['AHP_ONLY', 'AHP_ENTROPY_COMBINED', 'EXPERT_ONLY']  # [L1231]
    ahp: AhpSegment | None = None  # [L1232]-[L1233] AHP snapshot (nullable, ORCH-20 r1)
    entropy: EntropySegment | None = None  # [L1234]-[L1235] entropy snapshot (nullable, r1)
    combine: CombineSegment | None = None  # [L1236]-[L1238] combine snapshot (nullable, r1)
    alpha_basis: AlphaBasisSegment | None = None  # [L1239]-[L1240] CalibrationReport snapshot (nullable, r1)
    whatif_run_id: str | None = None  # [L1241] whatif run number; FROZEN-missing check is config layer (S1-T06)
    approved_by: str  # [L1242] sign-off owner
    approved_date: date  # [L1242] ISO [L889]
    effective_from: date  # [L1242] ISO [L889]
    effective_to: date  # [L1242] ISO [L889]


class WeightVersionDoc(_InputRow):
    '''T6 weights, grain version; annual sign-off, frozen within a period
    ([L1104], [L1186]-[L1194]). provenance [L1193] carries the 3.11.4
    WeightProvenance snapshot and is nullable at the models layer (ORCH-20
    ruling 2); its FROZEN-presence rule ([L1435] P-11) is config-layer policy
    (S1-T06),
    and the FROZEN consistency checks of [L880] belong to the loading layer.
    '''

    weight_version_id: str  # [L1190]
    status: WeightVersionStatus  # [L1190] only FROZEN may score
    effective_from: date  # [L1191] ISO [L889]
    effective_to: date  # [L1191]
    level1_weights: dict[str, Ratio]  # [L1192] dim weights, sum 1
    level2_weights: dict[str, dict[str, Ratio]]  # [L1192] weights within a dim
    approved_by: str  # [L1194]
    approved_date: date  # [L1194]
    provenance: WeightProvenance | None = None  # [L1193] 3.11.4; nullable per ORCH-20 r2


class GradeRuleRow(_InputRow):
    '''T7 grade_rules, grain grade ([L1105], [L1196]-[L1206]).'''

    grade_code: GradeCode  # [L1200]
    grade_label: str  # [L1200] verbatim from volume A
    attainment_floor: Ratio  # [L1201] absolute attainment floor
    evidence_class_min: EvidenceClass  # [L1202]
    redline_pass_required: StrictBool  # [L1203]
    promotion_streak: StrictInt  # [L1204] periods of stability before an upgrade
    actions: tuple[str, ...] | None = None  # [L1205] verbatim actions
    action_gate: str | None = None  # [L1205] level-1 library action gate
    max_grade_if_no_target: GradeCode  # [L1206]


class AnchorSetDoc(_InputRow):
    '''T8 anchor_set, grain set ([L1106], [L1208]-[L1214]).'''

    anchor_set_id: str  # [L1212]
    strategy_ids: tuple[str, ...]  # [L1212] a collection of ids, not a string
    effective_from: date  # [L1213] ISO [L889]
    effective_to: date  # [L1213]
    rationale: str  # [L1214] the selection must be defensible
# ===========================================================================
# S1-T04: the six output models and the eight intermediate models ([L867],
# [L868]) plus the sub-models ORCH-22 ruling 33 authorises. Everything from
# here on is additive: none of the fourteen input models above changed
# (ORCH-22 ruling 34, tests/test_models_output.py PREEXISTING_MODELS).
#
# Contract authority = docs/adr/ORCH-22.md rulings 14-34. Each field carries
# the SDD line it comes from; closed value sets are copied verbatim and the
# two name divergences the SDD itself has are kept as they are (ORCH-16
# ruling 1): metric_code [L1040] versus metric_id, grade_reason_codes [L1620]
# versus grade_reason_path [L964].
#
# Rules honoured by every class in this section:
#   * frozen + extra=forbid ([L865], V-5 [L871], ruling 5 item 1)
#   * H-4 [L1265]-[L1267]: money MoneyMinor / MinorUnits, counts StrictInt,
#     ratios and weights Ratio (Decimal), flags StrictBool - never float,
#     never a bare int, never a bare bool
#   * H-5: no business number is proposed here; every default is None, () or
#     {}, and the weights / floors / redline thresholds / K-01..K-20 values
#     stay PLACEHOLDER in config (S1-T05, S1-T06)
#   * H-6 / H-7: every reason-code column is a ReasonCode, so an unregistered
#     spelling fails at construction instead of degrading silently (V-14)
#   * H-8 [L1271]: run_at / period / seed are injected by the CLI ([L1089]);
#     this module reads no clock
#   * ruling 28 / 32: ordered sequences are tuple, maps are dict, and no
#     set / frozenset appears anywhere, so the [L1052] hash cannot depend on
#     PYTHONHASHSEED (V-3)
#   * ruling 31: AllFrames, ReportSet and RunContext are deliberately NOT
#     modelled - the B group of ScoringContext carries the Frames and the
#     seven [L1062] files are the S6 reports task (B-021)
# ===========================================================================

# The two names the section below needs were not in the S1-T02 import block.
# They are imported here instead of added above so that every pre-existing
# line of this file stays byte-identical for the R4 diff gate.
from typing import get_args

from pydantic import PlainValidator


class _OutputModel(BaseModel):
    '''Shared config of the S1-T04 models: frozen + extra=forbid ([L865],
    V-5 [L871]). Kept apart from _InputRow so an output row is tellable from
    an input row in a traceback; the config itself is the character-for-
    character one on _InputRow, as ORCH-22 ruling 5 item 1 requires.'''

    model_config = ConfigDict(frozen=True, extra='forbid')


# ---------------------------------------------------------------------------
# The nine new closed sets / aliases of ORCH-22 ruling 33, copied verbatim.
# ---------------------------------------------------------------------------
SchemeName = Literal['OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP']  # [L1015]
# [L1018] writes BOUNDARY, but [L1624] and reason_codes.py both use
# NEAR_BOUNDARY; ORCH-03 closed the set on the registered spelling (ruling 19).
StabilityLabel = Literal['STABLE', 'NEAR_BOUNDARY', 'UNSTABLE']
# [L964] five values. GradeCode above stays at four: it is the T7 grade-rule
# code ([L1200]) and a threshold row hanging on NOT_ASSESSED would be meaningless,
# so widening it is forbidden (ruling 20, test C).
FrameGrade = Literal['L1', 'L2', 'L3', 'L4', 'NOT_ASSESSED']
# [L1040] verbatim four values, closed. ENTROPY_UNSTABLE is stackable (a metric
# can be INACTIVE and drifting at once), so it is a flags entry, not a fifth
# status (ruling 27, B-018, test I).
EntropyStatus = Literal['OK', 'LOW_VARIATION', 'INACTIVE', 'COLLINEAR']
MethodAgreement = Literal['METHOD_AGREEMENT', 'METHOD_DIVERGENCE']  # [L1028]
# [L940] spells the three methods in lowercase; verbatim, not upper-cased.
NormalizationMethod = Literal['min_max', 'z_score', 'rank_percentile']
ScoreOperator = Literal['LINEAR', 'GEOMETRIC', 'NON_COMPENSATORY']  # [L953]
# [L978] GATE_ONLY is the default at the config layer, not here (H-5);
# enabling DISCOUNT needs its own ADR - behaviour, not contract.
EvidenceMode = Literal['GATE_ONLY', 'DISCOUNT']


class InputTableFingerprint(_OutputModel):
    '''One entry of the [L888] input fingerprint step: "every file gets a
    SHA256 and a row count". A sha256 column stays a plain str at the contract
    layer - the 64-hex format check is audit.py's job (S6), and a regex here
    would state a constraint the SDD never wrote (ruling 14). row_count is a
    count, so it is an exact int (H-4, [L1266]).'''

    sha256: str  # [L888] SHA256 of the file as loaded
    row_count: StrictInt  # [L888] rows in that file (a count, H-4)


# [L891], ruling 15: ONE alias for both AuditBundle item 9 and the
# ScoringContext A group, never a private copy per model. The key set is
# deliberately open: [L877] carries the weights_*.yaml wildcard and which
# files are fingerprinted is io_loaders' decision (S3), so closing it to
# exactly eight keys would turn every added file into a breaking change
# (same reasoning as ORCH-20 ruling 7, B-016).
InputFingerprints = dict[str, InputTableFingerprint]


# ---------------------------------------------------------------------------
# Three columns carry a closed value set AND can legitimately be absent:
# [L1624] stability_label (no label before the sensitivity run), [L1028]
# agreement (no verdict while triangulation is off) and [L989] forced_grade
# (nothing is forced when no redline was hit). ORCH-22 spells all three
# "<Alias> | None", which is exactly this value set; it is declared here as
# the alias plus a validator whose only extra branch is None, because
# tests/test_models_output.py reads the closed set off
# model_fields[name].annotation (b04, c03) to prove the column set equals the
# alias set and stayed closed, and an Optional wrapper hides it. Nothing is
# relaxed by this: the legal spellings are read off the alias with get_args
# rather than re-listed (H-7), the default stays None (ruling 32 item 3 -
# null is null, never an empty string), and anything outside the set,
# including a bool, a number or a near-miss spelling, is still refused.
# ---------------------------------------------------------------------------
def _none_or_member(closed_alias):
    legal = tuple(get_args(closed_alias))

    def _check(value):
        if value is None:
            return None
        if type(value) is str and value in legal:
            return value
        raise ValueError(
            'needs None or one of ' + repr(legal) + ', got ' + repr(value))

    return PlainValidator(_check)


# [L1624] / ruling 19.
_NullableStabilityLabel = Annotated[
    StabilityLabel, _none_or_member(StabilityLabel)]
# [L1028] / ruling 26.
_NullableMethodAgreement = Annotated[
    MethodAgreement, _none_or_member(MethodAgreement)]
# [L989] / ruling 28: a redline forces one of L1..L4, so the closed set here
# is GradeCode and never FrameGrade - NOT_ASSESSED is not a forced grade.
_NullableForcedGrade = Annotated[GradeCode, _none_or_member(GradeCode)]


# ---------------------------------------------------------------------------
# The sub-models of ORCH-22 ruling 33. Each is a data snapshot, frozen and
# extra=forbid, with no behaviour and no business number.
# ---------------------------------------------------------------------------
class PreflightFinding(_OutputModel):
    '''One [L1051] item-12 finding, cut to the smallest closure the SDD
    supports (ruling 16): code, severity, message. The code is a gate or check
    number ([L900] C-01, G-01..G-15) and not a reason_code, so it stays a str
    rather than passing the ReasonCode gate. severity reuses the single source
    of truth in dsm.reason_codes (INFO / WARN / BLOCK) instead of a second
    enum being invented here (H-7). The richer finding shape the SDD never
    states is B-019, to be ruled when S3 reads the preflight section.'''

    code: str  # [L900] gate / check identifier, open set
    severity: reason_codes.Severity  # [L1063] existing enum, not a new one
    message: str  # [L1051] item 12, the finding text


class DowngradeAction(_OutputModel):
    '''One [L1051] item-13 downgrade action - the data-structure landing point
    of H-6: a downgrade, fallback, removal or cap that carries no registered
    reason_code cannot be recorded at all, so reason_code is mandatory and
    gated, and a bare string fails at construction (H-7, V-14). [L1054]
    "every failed command still writes an audit_bundle" is behaviour, so it
    gets no column here (ruling 17).'''

    reason_code: ReasonCode  # [L1051] item 13; H-6 makes it mandatory
    action: str  # [L1051] what was done, wording owned by the report layer
    subject: str | None = None  # strategy_id / metric_id / period it applies to


class PoolKey(_OutputModel):
    '''[L1001] verbatim pool_key = (biz_domain, evidence_class). ONE class is
    shared by NormalizedRow, PoolRow, PoolStatRow and ScoreCardRow.ranking_pool
    (ruling 29) - a per-model copy would let the pooling key drift apart.
    biz_domain is the first pooling dimension ([L1119]) and stays a str: the
    domain registry is config driven (D7), so no closed set is invented.
    [L1001] "no ranking across pools" is behaviour (P-6 / G-02).

    evidence_class is nullable by D-MODELS-01 (ORCH-29 ruling 4, restated by
    ORCH-32 ruling 4): [L1334] puts Step 2 normalize BEFORE [L1338] Step 3
    evidence, so the second pooling dimension does not exist yet when Step 2
    has to partition. The two readings are reconciled as a LOOSE key at Step 2
    (normalize.step2_pool_key: biz_domain only, evidence_class left None --
    never a fabricated default, V-14) and the FULL key at Step 7
    (pooling.step7_pool_key refuses None), so P-6 / G-02 keep ranking inside
    one biz_domain x evidence_class pool and [L942] is not weakened.'''

    biz_domain: str  # [L1119] first pooling dimension, config driven
    # [L1001] second pooling dimension [L1895]; None = the Step-2 loose key
    evidence_class: EvidenceClass | None = None


class ScoreCardMetricCell(_OutputModel):
    '''The per-metric block of score_card [L1613] "actual value / target value
    / attainment side by side". Nested rather than flattened into metric_X_*
    prefix columns (ruling 23): [L1272] requires iterating a sorted mapping
    and the metric set is config driven ([L1131] / D7). actual_value takes the
    same unit-polymorphic type as MetricFactRow.value ([L1150]); target_value
    the same type as MetricDictRow.target_value (ORCH-14). attainment is
    nullable because [L930] makes a missing target an explicit null, never a
    mean substituted in its place.'''

    actual_value: FactValue  # [L1613] money in minor units, or a Decimal
    target_value: UnitValue | None = None  # [L1613] absent target [L930]
    attainment: Ratio | None = None  # [L1613] null when no target exists


class ScoreCardDimCell(_OutputModel):
    '''The per-dimension block of score_card [L1614] "attainment, relative
    score, coverage, W". Keys are dim_code ([L1131]), a config driven
    registry, so the container is a dict and the set is not closed here. The
    two nullables follow [L930] the same way the metric cell does; coverage
    and the dimension weight W_d ([L879], [L1192]) are always computable, so
    they are required Ratio.'''

    attainment: Ratio | None = None  # [L1614] dim attainment, [L930] nullable
    relative_score: Ratio | None = None  # [L1614] relative track only
    coverage: Ratio  # [L1614] share of signed-off metrics that scored
    weight: Ratio  # [L1614] W_d, the dimension weight [L879] / [L1192]


class SensitivitySchemeResult(_OutputModel):
    '''One scheme's line of the sensitivity report ([L1018] overall_flip_rate
    per scheme). The two counts are added by ruling 25: [L1018] states only
    the rate, and a rate whose numerator and denominator cannot be recovered
    is not defensible ([L1613] "keep everything, no black box") and could not
    be re-derived from the [L1052] hash. flag carries [L1019]
    FLIP_RATE_REVIEW / FLIP_RATE_UNUSABLE through the ReasonCode gate.'''

    scheme: SchemeName  # [L1015] one of the five schemes
    overall_flip_rate: Ratio  # [L1018] grade flips / assessed strategies
    flipped_count: StrictInt  # ruling 25: the rate's numerator (H-4)
    assessed_count: StrictInt  # ruling 25: the rate's denominator (H-4)
    flag: ReasonCode | None = None  # [L1019] review / unusable verdict code


class SensitivityStrategyRow(_OutputModel):
    '''One strategy's stability verdict ([L1018] "per-strategy stability
    label"). The two flip columns are required to exist here because the
    identically named ScoreCardRow columns ([L1624]) have to have a source;
    stability_label is not nullable at this grain - a strategy that was
    assessed got a label, and [L1004] NOT_ASSESSED strategies are counted
    separately instead of being labelled.'''

    strategy_id: str  # [L1149] locator
    version_id: str  # [L1149] locator
    stability_label: StabilityLabel  # [L1624] / ruling 19
    flip_under_pct10: Ratio | None = None  # [L1624] verbatim name
    flip_under_pct20: Ratio | None = None  # [L1624] verbatim name


class TriangulationStrategyRow(_OutputModel):
    '''One strategy's rank under the two cross-check methods ([L1028]
    topsis_rank / gra_rank). Ranks are counts, so StrictInt (H-4). The
    Spearman rhos are report level and live on TriangulationReport.'''

    strategy_id: str  # [L1149] locator
    version_id: str  # [L1149] locator
    topsis_rank: StrictInt  # [L1028] rank under TOPSIS (a count, H-4)
    gra_rank: StrictInt  # [L1028] rank under GRA (a count, H-4)


class PoolStatRow(_OutputModel):
    '''One pool's line of [L1006] "counts and the double share". Both shares
    are mandatory side by side: [L1003] forbids reporting the merged share
    alone, so a model that offered only one of them would permit the breach.
    The exact denominator of share_in_pool is not stated by [L1006] - B-020,
    ruled by S5 pooling; the columns are the conservative superset that
    ORCH-22 section 10.2-2 asks for.'''

    pool_key: PoolKey  # [L1001] the shared pooling key, ruling 29
    count: StrictInt  # [L1006] strategies in this pool (a count, H-4)
    share_in_pool: Ratio  # [L1006] pool share of its own base
    share_overall: Ratio  # [L1003] / [L1006] merged share, never alone


# ---------------------------------------------------------------------------
# The seven Frame row models of ORCH-22 ruling 28. A Frame is row-shaped,
# because [L1156] makes a missing metric a missing row rather than an empty
# column, a pydantic dict key cannot carry the composite
# (strategy_id, metric_id) key, and CSV is the carrier of record
# ([L1220]-[L1223]).
# ---------------------------------------------------------------------------
class AttainmentRow(_OutputModel):
    '''One step-1 attainment fact, grain strategy x version x period x metric
    ([L928]). attainment is nullable by [L930]: a metric without a target has
    no attainment, and replacing it with a mean would be an unlogged
    invention; the absence is disclosed by reason_code instead ([L931], H-6).
    direction reuses the existing MetricDirection gate ([L1137]), and
    target_source is the traceability column behind [L1139] target_basis.
    has_target and capped_flag are flags, so StrictBool (ORCH-18).'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    metric_id: str  # [L1149] locator key, long table [L1156]
    attainment: Ratio | None = None  # [L928] / [L930] null when no target
    direction: MetricDirection  # [L928] / [L1137] +1 or -1, existing gate
    target_source: str | None = None  # [L1139] target_basis, open code set
    has_target: StrictBool  # [L928]
    capped_flag: StrictBool  # [L928] [L931] attainment clamped
    reason_code: ReasonCode | None = None  # [L931] three codes, H-6/H-7


class NormalizedRow(_OutputModel):
    '''One step-2 normalised value, ORCH-13 ruling 2 adopted verbatim by
    ruling 28: locator keys [L1149], pool_key [L942], norm_value [L940],
    method [L940], anchor_used [L941], reason_code [L944]. The relative track
    only feeds ranking and the relative composite ([L945]); that ban on using
    it for grade floors is a behaviour guard (P-1 / G-01), stated on
    NormalizedFrame. pool_key is the shared PoolKey class, not a copy.'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    metric_id: str  # [L1149] locator key
    pool_key: PoolKey  # [L942] / [L1001] ruling 29 shared class
    norm_value: Ratio  # [L940]
    method: NormalizationMethod  # [L940] lowercase verbatim three values
    anchor_used: StrictBool  # [L941] anchor set applied rather than pure min-max
    reason_code: ReasonCode | None = None  # [L944] four codes


class EvidenceRow(_OutputModel):
    '''One step-3 evidence verdict, [L980] verbatim five columns plus the
    locator pair: class, reason, source, control_group_id,
    interpretation_limit. evidence_source is part of this task by ORCH-15
    ([L870], [L980]); the [L977] decision order, the [L979] keyword list and
    the [L981] one-way call are evidence.py behaviour (S5), not columns.'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    evidence_class: EvidenceClass  # [L980] A / B / C / D [L1895]
    evidence_reason: ReasonCode  # [L980] / [L982] one of three registered codes
    evidence_source: EvidenceSource  # [L980] / ORCH-15 CARD_ONLY | CEL_ESTIMATED
    control_group_id: str | None = None  # [L980] absent when there is none
    interpretation_limit: str | None = None  # [L980] C class must fill it [L977]


class RedlineEvalRow(_OutputModel):
    '''One step-4 redline evaluation, ORCH-13 ruling 2 adopted verbatim by
    ruling 28. The name is RedlineEvalRow, never RedlineRow: RedlineRow is the
    T5 input table ([L866], landed in S1-T02), and reusing it would fuse the
    signed-off definition with this period's verdict ("evaluate" from the
    [L988] signature). threshold_value stays unit polymorphic ([L1181]); the
    threshold-versus-unit agreement is a semantic check of S1-T06 ([L879]).
    forced_grade is a GradeCode, not a FrameGrade: [L989] forces one of
    L1..L4 and never NOT_ASSESSED. The waiver quartet comes from [L991];
    whether a waiver is still in date is redline.py's judgement (S5, G-03),
    and the non-compensatory semantics of [L1870] are behaviour.'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    metric_id: str  # [L988] the metric whose redline was evaluated
    level: RedlineLevel  # [L989] HARD vetoes, SOFT deducts [L1180]
    comparator: Comparator  # [L1181]
    threshold_value: UnitValue  # [L1181] compared through dsm.numeric only
    hit: StrictBool  # [L988] this period's verdict
    forced_grade: _NullableForcedGrade = None  # [L989] ruling 28, GradeCode set
    waiver_approval_id: str | None = None  # [L991] approval trail reference
    waiver_valid_from: date | None = None  # [L991] ISO date [L889], injected
    waiver_valid_to: date | None = None  # [L991] ISO date [L889], injected
    waiver_scope: str | None = None  # [L991] what the waiver covers
    soft_deduction: Ratio | None = None  # [L990] SOFT deduction, listed alone
    reason_code: ReasonCode | None = None  # [L993] per-metric dynamic codes


class ScoreRow(_OutputModel):
    '''One step-5 composite, [L952] verbatim: composite_absolute /
    composite_relative / the per-dimension dim_d on BOTH tracks / coverage /
    weight_version_id / operator. Two dictionaries rather than flattened
    prefix columns, for the [L1272] sorted-mapping rule (ruling 23). Both
    composites are nullable per [L964] and RC.NOT_ASSESSED: a strategy with no
    score must not be handed an invented one (same logic as ORCH-21 ruling 9).
    weight_version_id is required on the ROW because [L955] INV-3 puts the
    weight version on every score_card line; the [L954] renormalisation and
    its WEIGHT_REALLOCATED code are aggregate behaviour (S4).'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    composite_absolute: Ratio | None = None  # [L952] main track, null [L964]
    composite_relative: Ratio | None = None  # [L952] ranking track only
    dim_absolute: dict[str, Ratio]  # [L952] per dim, absolute track, key dim_code
    dim_relative: dict[str, Ratio]  # [L952] per dim, relative track
    coverage: Ratio  # [L952] share of signed-off metrics that scored
    weight_version_id: str  # [L955] INV-3, on every row
    operator: ScoreOperator  # [L953]


class GradeRow(_OutputModel):
    '''One step-6 grade, [L964] verbatim six items: grade,
    grade_reason_path, capped, cap_reason, action, usable_for_elimination.
    grade_reason_path is an ORDERED tuple so the decision path can be walked
    back after the fact; the name is kept divergent from ScoreCardRow's
    grade_reason_codes ([L1620]) because the SDD is divergent (ORCH-16
    ruling 1, ruling 21). action is a tuple of strings and nullable: [L1631]
    reserves the wording for volume A, so the model layer invents none (H-5).
    The [L965] hysteresis numbers are governance values and stay PLACEHOLDER
    in config (S1-T05/T06); [L966] VERSION_BREAK and [L968] absolute-track-
    only grading belong to grading (S4/S5).'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    grade: FrameGrade  # [L964] ruling 20
    grade_reason_path: tuple[ReasonCode, ...]  # [L964] ordered, replayable
    capped: StrictBool  # [L964]
    cap_reason: ReasonCode | None = None  # [L964] None when nothing capped
    action: tuple[str, ...] | None = None  # [L964] wording owned by volume A
    usable_for_elimination: StrictBool  # [L964] / [L1019]


class PoolRow(_OutputModel):
    '''One strategy's pooling verdict, [L1006] verbatim four columns plus the
    locator trio. pool_rank is nullable because [L1004] leaves NOT_ASSESSED
    strategies out of both the denominator and the ranking, so a rank of 0
    would be a lie; primary_pool_eligible is the outcome of the [L1002]
    four-condition gate, whose evaluation is pooling behaviour (S5, G-02).'''

    strategy_id: str  # [L1149] locator key
    version_id: str  # [L1149] locator key
    period: str  # [L1149] locator key
    pool_key: PoolKey  # [L1001] ruling 29 shared class
    pool_rank: StrictInt | None = None  # [L1006] rank inside the pool, [L1004]
    primary_pool_eligible: StrictBool  # [L1005] first-level library gate
    reject_reason: ReasonCode | None = None  # [L1005] two rejection codes


# ---------------------------------------------------------------------------
# The six output models of [L867]. Grains are copied verbatim from the
# [L1220]-[L1224] "one row means" column (ORCH-22 section 0 item 2).
# ---------------------------------------------------------------------------
class ScoreCardRow(_OutputModel):
    '''score_card, grain [L1220] verbatim "one strategy's complete scoring
    detail for one evaluation period". Ruling 21 fixes the 35 columns: the
    locator trio of [L1149] without metric_id, because the metric dimension is
    carried by per_metric, and then the six blocks [L1612]-[L1626] in order.

    Provenance first: [L1612] asks every row to name the rule set that scored
    it, which is the first entry point for an appeal or a re-run, and [L955]
    INV-3 makes the weight version mandatory on every line.

    Both composites are nullable ([L964] / RC.NOT_ASSESSED: no score at all
    this period), and so is the whole ranking block: [L1004] counts
    NOT_ASSESSED strategies separately instead of putting them in a pool.

    evidence_class is required because [L977] judges D even for a missing
    design card, so every strategy has one; evidence_reason ([L982]) and
    evidence_source (ORCH-15, [L980]) name why on the same row. The C-class
    rule behind interpretation_limit ([L977] item 5) is grading behaviour, so
    this layer only offers the nullable column.

    Redline: [L1619] keeps the score computed but inactive when a line is hit,
    so redline_pass is a flag next to the reason codes, never a rewrite of the
    score. Cap and library gates follow [L1621] and [L1623].

    Stability is nullable because sensitivity may not have run ([L1624]); the
    two flip columns keep the SDD's verbatim names.

    The five CEL-0 columns ([L1626], [L1896]) are all nullable and default to
    None, never to 0: [L1626] states the first version leaves them empty and
    requires the report to say so out loud, which is S6 behaviour. Their names
    follow ruling 22 - incremental_value / incremental_ci_lower /
    incremental_ci_upper are unit polymorphic and keep the verbatim spelling,
    while value_captured is a pure money column and therefore takes the
    _minor suffix (H-4), the one point where ORCH-16 ruling 1 and ruling 2
    met and the ADR resolved it.

    [L1274] / ruling 32: every column here is a to-do item for the S6 serializer;
    G-12 and V-11 hold it to account.'''

    strategy_id: str  # [L1149] locator, [L1220] grain
    version_id: str  # [L1149] locator
    period: str  # [L1149] locator
    weight_version_id: str  # [L1612] version quartet, INV-3 [L955]
    dict_version: str  # [L1612] which metric dictionary scored this
    anchor_set_id: str  # [L1612] which anchor set normalised it
    run_id: str  # [L1612] which run produced it, [L1091] no overwriting
    per_metric: dict[str, ScoreCardMetricCell]  # [L1613] key metric_id [L1272]
    per_dim: dict[str, ScoreCardDimCell]  # [L1614] key dim_code [L1131]
    composite_absolute: Ratio | None = None  # [L1615] main score, null [L964]
    composite_relative: Ratio | None = None  # [L1616] ranking only, not a floor
    evidence_class: EvidenceClass  # [L1617] always present, [L977]
    evidence_reason: ReasonCode  # [L1617] / [L982] one of three codes
    evidence_source: EvidenceSource  # ORCH-15 [L870] / [L980]
    interpretation_limit: str | None = None  # [L1618] C class rule is [L977]
    redline_pass: StrictBool  # [L1619] score stands but is inactive on a hit
    redline_flags: tuple[ReasonCode, ...] = ()  # [L1619] hard / soft / waiver
    grade: FrameGrade  # [L1620] ruling 20
    grade_reason_codes: tuple[ReasonCode, ...]  # [L1620] verbatim, not renamed
    capped_flag: StrictBool  # [L1621] no target or C-class cap
    cap_reason: ReasonCode | None = None  # [L1621] None when nothing capped
    ranking_pool: PoolKey | None = None  # [L1622] [L1001] ruling 29, [L1004]
    rank_in_pool: StrictInt | None = None  # [L1622] a count (H-4)
    pool_size: StrictInt | None = None  # [L1622] the pool's size (H-4)
    eligible_for_L1_library: StrictBool  # [L1623] verbatim name, capital L1
    l1_gate_reasons: tuple[ReasonCode, ...] = ()  # [L1623] / [L1005] two codes
    stability_label: _NullableStabilityLabel = None  # [L1624] ruling 19
    flip_under_pct10: Ratio | None = None  # [L1624] verbatim name
    flip_under_pct20: Ratio | None = None  # [L1624] verbatim name
    usable_for_elimination: StrictBool  # [L1625] flip rate AND method spread
    incremental_value: FactValue | None = None  # [L1626] / [L1896] CEL-0 point
    incremental_ci_lower: FactValue | None = None  # [L1626] / [L1896] CI low
    incremental_ci_upper: FactValue | None = None  # [L1626] / [L1896] CI high
    estimator_method: str | None = None  # [L1626] CEL-0 method, open set
    value_captured_minor: MoneyMinor | None = None  # [L1896] ruling 22 suffix


class GradeLedgerRow(_OutputModel):
    '''grade_ledger, grain [L1221] verbatim "one strategy's grade change and
    the action to be executed". Ruling 24 is the point of this table:
    [L1630] requires the recommended action and the decided action as TWO
    columns, because V-8 [L1863] checks exactly that pair - the model may only
    advise, a human decides and signs, and a single column would erase the
    difference between the two. decision_note is the third, separate column
    [L1630] asks for when they disagree; the agreement check itself is
    grading / reports behaviour (L2 minimum), so no cross-column validator
    lives here.

    previous_grade exists because the grain says CHANGE, which needs a from
    and a to; it is nullable because [L890] treats a missing prior ledger as
    FIRST_PERIOD. The action wording stays str and nullable: [L1631] reserves
    the verbatim action text for volume A chapter three (seven), which this
    task may not read, so a required column would force invented wording
    (H-5). owner_dept / owner_name are the [L1632] sign-off pair, deadline an
    ISO date ([L889], injected - H-8), archive_ref the [L1633] fourth-level
    exit reference. ledger_complete is the carrier [L1634] marks as "ledger
    incomplete"; the marking is S6's job. usable_for_elimination is the
    [L1019] verbatim column that carries "false" when stability forbids it.'''

    strategy_id: str  # [L1149] locator, [L1221] grain
    version_id: str  # [L1149] locator
    period: str  # [L1149] locator
    grade: FrameGrade  # [L1620] ruling 20
    previous_grade: FrameGrade | None = None  # [L1221] from, null [L890]
    recommended_action: str | None = None  # [L1630] first of the two columns
    decided_action: str | None = None  # [L1630] second column, V-8 [L1863]
    decision_note: str | None = None  # [L1630] mandatory when they disagree
    owner_dept: str | None = None  # [L1632] three-level actions need an owner
    owner_name: str | None = None  # [L1632] same name as T1 [L1122]
    deadline: date | None = None  # [L1632] ISO [L889], injected (H-8)
    archive_ref: str | None = None  # [L1633] fourth-level exit
    ledger_complete: StrictBool  # [L1634] carrier of the incomplete marker
    usable_for_elimination: StrictBool  # [L1019] verbatim column name


class SensitivityReport(_OutputModel):
    '''sensitivity_report, grain [L1222] "one scheme's grade flips". Ruling 25
    makes this a report-level container rather than a row model, because
    [L1018] asks for two grains at once - the per-scheme overall_flip_rate and
    the per-strategy stability label - and one row model cannot hold both
    without repeating itself. The two carriers of the same report ([L1222] CSV
    plus MD) are not split into two models either: [L1061]-[L1062] is S6
    rendering (B-021).

    flags is where the [L1020] LOO_SAMPLED annotation lands; "the first page
    must say the result may not drive elimination" ([L1019], [L1064]) is a
    rendering rule, so it gets no column. seed is nullable because [L1270]
    makes an unset seed a legal state that only forbids MC; the
    SeedRequiredError that [L1017] mentions is sensitivity.py behaviour (S6).'''

    by_scheme: tuple[SensitivitySchemeResult, ...]  # [L1018] per scheme
    by_strategy: tuple[SensitivityStrategyRow, ...]  # [L1018] per strategy
    loo_dominant_metrics: tuple[str, ...] = ()  # [L1018] LOO leading metrics
    norm_swap_rank_correlation: Ratio | None = None  # [L1018] Spearman, no bound
    flags: tuple[ReasonCode, ...] = ()  # [L1020] LOO_SAMPLED carrier
    seed: StrictInt | None = None  # [L1017] / [L1270] a count (H-4)


class TriangulationReport(_OutputModel):
    '''triangulation, grain [L1224] "the agreement of the three rankings".
    Ruling 26 keeps the four rhos and the verdict at report level and the two
    per-strategy ranks in TriangulationStrategyRow. The column names are the
    [L1028] verbatim rho_main_topsis / rho_main_gra / rho_topsis_gra /
    mean_rho: the SDD writes a Greek letter, which is not a legal Python
    identifier, so the ASCII norm maps it to rho_ (ORCH-16 ruling 1).
    gra_by_metric keeps the [L1028] per-metric mean relatedness, keyed by
    metric_id and sorted at serialisation time ([L1053] item 3).

    agreement is nullable because a disabled or incomplete run has no verdict;
    flags is the carrier of [L1030] TRIANGULATION_DISABLED, which the ADR
    singles out as a must-not-be-silent case (H-6).'''

    rows: tuple[TriangulationStrategyRow, ...]  # [L1028] per strategy
    rho_main_topsis: Ratio | None = None  # [L1028]
    rho_main_gra: Ratio | None = None  # [L1028]
    rho_topsis_gra: Ratio | None = None  # [L1028]
    mean_rho: Ratio | None = None  # [L1028] mean_rho
    agreement: _NullableMethodAgreement = None  # [L1028] two RC-backed values
    gra_by_metric: dict[str, Ratio]  # [L1028] metric_id -> mean relatedness
    flags: tuple[ReasonCode, ...] = ()  # [L1030] never silent when disabled


class EntropyDiagnosticRow(_OutputModel):
    '''entropy_diagnostic, grain [L1223] "one metric's health and the suggested
    action". Ruling 27 keeps the [L1040] list at nine columns and adds exactly
    one carrier, flags, for the B-018 annotation.

    metric_code is [L1040] verbatim and is NOT tidied into metric_id even
    though the rest of the SDD uses metric_id ([L1130], [L1149], [L1180]) -
    ORCH-22 section 0 item 3 with ORCH-16 ruling 1 forbids the beautification.

    status stays the closed four ([L1040]); ENTROPY_UNSTABLE ([L1777] RK-13)
    is stackable with any status, so it lands in flags as a registered code
    rather than becoming a fifth status. vif_j and max_abs_corr are nullable
    because a single-metric correlation matrix has no inverse - genuinely
    undefined, not zero (same logic as ORCH-21 and the on_zero=None policy of
    numeric.safe_div). suggested_action runs through the ReasonCode gate,
    because the four codes [L1041] names are registered ones (H-7).

    When the marker is set and which drift budget triggers it (K-16,
    PLACEHOLDER) is S8-T01's decision (B-018). [L1038] INV-3 "the online
    entropy weight only writes this diagnostic table and never feeds back into
    the weights" and the [L1042] type-and-call isolation are behaviour, guarded
    by S9-T02 architecture tests; nothing here imports diagnostics (H-9).'''

    metric_code: str  # [L1040] verbatim, NOT metric_id
    e_j: Ratio  # [L1040] entropy value
    d_j: Ratio  # [L1040] differentiation coefficient
    cv_j: Ratio  # [L1040] coefficient of variation
    vif_j: Ratio | None = None  # [L1040] undefined for a single metric
    max_abs_corr: Ratio | None = None  # [L1040] undefined for a single metric
    status: EntropyStatus  # [L1040] closed four, ruling 27
    suggested_action: ReasonCode | None = None  # [L1040] / [L1041] registered
    owner: str  # [L1040] / [L1041] from T2 owner_name [L1141]
    flags: tuple[ReasonCode, ...] = ()  # B-018 carrier, [L1777] RK-13


class AuditBundle(_OutputModel):
    '''audit.json, [L1050]-[L1055]. Ruling 14 maps the 15 verbatim items of
    [L1051] onto 16 columns: item 11 "enabled sensitivity schemes and seed"
    carries two independent values and becomes sensitivity_schemes plus seed;
    the other fourteen items take one column each. The mapping is a naming
    ruling, not a rename of the SDD, and R4 checks it row by row.

    Everything is required except seed: [L1270] makes an unset seed a legal
    state (it only refuses MC), while [L1080]-[L1087] exit codes vary per
    command, so the models layer keeps exit_code a required StrictInt and does
    not close the set. The SHA256 columns are plain str: a 64-hex format
    validator is audit.py's job (S6), and adding one here would invent a
    constraint the SDD never states. output_fingerprints is a filename ->
    SHA256 map because [L1051] item 10 states no byte counts.

    H-8: run_at arrives from --run-at ([L1089]) and this model never asks the
    OS for a time; [L1054] "write an audit_bundle even when the command
    failed" is cli / audit behaviour (S6) and gets no column.'''

    run_id: str  # [L1051] item 1, new directory per run [L1091]
    run_at: datetime  # [L1051] item 2, injected by --run-at [L1089] (H-8)
    period: str  # [L1051] item 3, [L1149]
    dsm_version: str  # [L1051] item 4
    design_version: str  # [L1051] item 5
    cel_contract_version: str  # [L1051] item 6, [L1897]
    weight_version_id: str  # [L1051] item 7, [L1190]
    config_snapshot_sha256: str  # [L1051] item 8, full config snapshot
    input_fingerprints: InputFingerprints  # [L1051] item 9, ruling 15 alias
    output_fingerprints: dict[str, str]  # [L1051] item 10, file -> SHA256
    sensitivity_schemes: tuple[SchemeName, ...]  # [L1051] item 11a, [L1015]
    seed: StrictInt | None = None  # [L1051] item 11b, [L1270] may be absent
    preflight_findings: tuple[PreflightFinding, ...]  # [L1051] item 12, [L1063]
    downgrade_actions: tuple[DowngradeAction, ...]  # [L1051] item 13, H-6
    exit_code: StrictInt  # [L1051] item 14, [L1080]-[L1087] open set
    reproducibility_hash: str  # [L1051] item 15, produced by [L1052]



# ---------------------------------------------------------------------------
# The eight intermediate models of [L868], row-shaped per ruling 28, and
# ScoringContext (ORCH-13 ruling 1 as amended by ruling 30).
# ---------------------------------------------------------------------------
class AttainmentFrame(_OutputModel):
    '''Step 1 output ([L928]). rows is the long table; attainment_coverage is
    the per-strategy ratio of that same line, "metrics with a target over
    signed-off metrics", keyed by strategy_id and sorted at serialisation time
    ([L1053] item 3). The denominator counts only signed-off metrics ([L1141]
    PENDING / REJECTED never score); computing it is attainment.py's job
    (S4), so this layer builds the column and no threshold next to it (H-5).'''

    rows: tuple[AttainmentRow, ...]  # [L928] [L1156] long table
    attainment_coverage: dict[str, Ratio]  # [L928] strategy_id -> coverage


class NormalizedFrame(_OutputModel):
    '''Step 2 output ([L939]-[L945]). [L945] is a behaviour ban rather than a
    column: the relative track feeds ranking and the relative composite only
    and must never decide a grade floor - P-1 / G-01 guard that in
    normalize.py (S4), and this layer states it here rather than modelling it
    (ruling 31: no extra wrapper, no invented guard field).

    warnings / excluded are the FRAME-LEVEL disclosure channel added by
    ORCH-32 ruling 2 (V-14: no silent downgrade). NormalizedRow.reason_code is
    ONE slot with the frozen precedence INACTIVE_METRIC > ANCHOR_SET_STALE >
    RANK_REVERSAL_RISK > SMALL_POOL ([L944]), so a row that is both
    zero-variance and measured against a degenerate anchor scale could only
    keep the first code and the second one vanished without a trace. Both
    columns are additive: no NormalizedRow column changes meaning, and an empty
    pair is the "nothing to disclose" state, never a default that hides one.

      warnings  every applicable code the single row slot could not take, as
                [L1051] item-13 DowngradeAction records. subject is the
                four-part locator joined by normalize.SUBJECT_SEP; action is
                the registry message, so the wording stays owned by
                reason_codes rather than being invented per module.
      excluded  the Step-1 rows Step 2 refused to normalise at all (on_zero is
                None, so the quotient is undefined and there is no row --
                [L943] "drop and warn"), re-stamped with the Step-2 exclusion
                code. ORCH-32 ruling 5: without it a strategy whose metrics
                are ALL inactive yields zero rows and Step 7 can no longer tell
                "disclosed downgrade" from "unannotated null". AttainmentRow
                is reused because a dropped row IS a Step-1 row; Step-1's own
                reason_code stays authoritative on AttainmentFrame.'''

    rows: tuple[NormalizedRow, ...]  # [L945] [L1156] long table
    warnings: tuple[DowngradeAction, ...] = ()  # ORCH-32 r2: secondary codes
    excluded: tuple[AttainmentRow, ...] = ()  # ORCH-32 r5: dropped rows [L943]


class EvidenceFrame(_OutputModel):
    '''Step 3 output ([L977]-[L982]). The [L977] decision order, the [L979]
    keyword list and the [L981] one-way call into the evidence layer are
    evidence.py behaviour (S5); this frame only carries the verdicts.'''

    rows: tuple[EvidenceRow, ...]  # [L980] [L1156] long table


class RedlineFrame(_OutputModel):
    '''Step 4 output ([L988]-[L994]). The rows are RedlineEvalRow, never the
    T5 input RedlineRow (ruling 28). Redlines are non-compensatory ([L1870]
    P0-2): a hit cannot be paid off by a good score elsewhere, which G-03
    guards in redline.py (S5) and which no field of this model can express.'''

    rows: tuple[RedlineEvalRow, ...]  # [L988] one row per evaluated metric


class ScoreFrame(_OutputModel):
    '''Step 5 output ([L952]-[L955]). operator records which aggregation
    produced the composites; NON_COMPENSATORY is a legal value of [L953] whose
    enablement is an aggregate-layer decision, not a contract default (H-5).
    The [L954] renormalisation of redistributed weights and its
    WEIGHT_REALLOCATED code are aggregate behaviour (S4).'''

    rows: tuple[ScoreRow, ...]  # [L952] one row per strategy x version x period


class GradeFrame(_OutputModel):
    '''Step 6 output ([L964]-[L968]). The [L965] hysteresis numbers
    (upgrade_consecutive_periods, demotion_immediate) are governance values:
    H-5 keeps them out of this file entirely, and they are configured in
    S1-T05 / S1-T06, never defaulted here. [L966] VERSION_BREAK and [L968]
    "grading reads the absolute track only" are grading behaviour (S4 / S5).'''

    rows: tuple[GradeRow, ...]  # [L964] one row per strategy x version x period


class PoolFrame(_OutputModel):
    '''Step 7 output ([L1001]-[L1006]). The four first-level-library gate
    conditions of [L1002] are evaluated in pooling.py (S5, G-02); this frame
    carries the outcome per strategy, and [L1001] "no ranking across pools" is
    enforced by the PoolKey on every row.'''

    rows: tuple[PoolRow, ...]  # [L1006] one row per pooled strategy


class PoolStats(_OutputModel):
    '''The pooled structure report of [L1006], one of the eight intermediate
    models of [L868]. evidence_structure is the [L1003] A/B/C/D count; unlike
    the fingerprint map its key set IS closed, because [L1003] enumerates the
    four classes verbatim, so the column is keyed by EvidenceClass rather than
    by str (ruling 28).

    not_assessed_count and not_assessed_reasons implement [L1004]: a
    NOT_ASSESSED strategy is counted on its own, stays out of every
    denominator, and has to show its reason distribution rather than
    disappearing into the pool totals. The reason keys are identifiers, not
    free text, and the values are counts (H-4).'''

    rows: tuple[PoolStatRow, ...]  # [L1006] one row per pool
    evidence_structure: dict[EvidenceClass, StrictInt]  # [L1003] closed four
    not_assessed_count: StrictInt  # [L1004] counted separately, H-4
    not_assessed_reasons: dict[str, StrictInt]  # [L1004] reason -> count


class ScoringContext(_OutputModel):
    '''The single object the pipeline threads through steps 1-7 and the
    renderer, ORCH-13 ruling 1 as completed by ORCH-22 ruling 30: sixteen
    columns in two groups.

    Group A is the run context, eight columns - the seven of ORCH-13 plus
    run_id, which ruling 30 adds because [L1051] makes it the first audit
    item, [L1612] puts it on every score_card row and [L1091] gives every re-
    run a new one; without it the [L1016] reuse of steps 1-4 could not carry
    the run identity to the sensitivity report. run_at is a datetime here, the
    notation correction of ruling 30, the same shape as the already landed
    MetricFactRow.snapshot_time ([L1152]) - the semantics and the source lines
    are unchanged. cel_enabled is REQUIRED with no default even though
    [L1898] describes a default of false, because a default belongs to the
    config layer (H-5).

    Group B is the eight intermediate models themselves, so the Step 1-4
    results can be reused across every perturbation scheme ([L1016]) instead
    of being recomputed; the columns are the Frame classes, not copies of
    their rows.

    Forbidden by ruling 30 and not present here: any business number (H-5),
    any current time (H-8). Forbidden by ruling 31 and not present anywhere:
    an AllFrames or ReportSet wrapper - [L1061] names parameters, not types.'''

    period: str  # [L1089] --period, [L1149]
    run_at: datetime  # [L1089] --run-at, injected (H-8, [L1271])
    run_id: str  # [L1051] / [L1612] / [L1091], ruling 30 addition
    seed: StrictInt | None = None  # [L1089] / [L1017] / [L1270] (H-4)
    weight_version_id: str  # [L1190] / [L955] INV-3
    evidence_mode: EvidenceMode  # [L978] GATE_ONLY or DISCOUNT
    cel_enabled: StrictBool  # [L1898] required, no default here (H-5)
    input_fingerprints: InputFingerprints  # [L891] ruling 15 alias, V-3
    attainment: AttainmentFrame  # B group, step 1 [L928]
    normalized: NormalizedFrame  # B group, step 2 [L939], reused [L1016]
    evidence: EvidenceFrame  # B group, step 3 [L977]
    redline: RedlineFrame  # B group, step 4 [L988]
    score: ScoreFrame  # B group, step 5 [L952]
    grade: GradeFrame  # B group, step 6 [L964]
    pool: PoolFrame  # B group, step 7 [L1002]
    pool_stats: PoolStats  # B group, [L1006]
