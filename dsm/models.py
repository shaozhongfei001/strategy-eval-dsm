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
    'CombineSegment',
    'DesignCardRow',
    'EntropySegment',
    'EvidenceSource',
    'GradeRuleRow',
    'MetricDictRow',
    'MetricFactRow',
    'MetricWeightComparison',
    'MoneyMinor',
    'Ratio',
    'RedlineRow',
    'StrategyMasterRow',
    'StrictBool',
    'StrictInt',
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
