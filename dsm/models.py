'''dsm.models -- the eight input rows of the DSM (layer L1, design doc 3.3.3).

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

Not in scope for S1-T02 (ORCH-13): WeightProvenance and the CEL-0 contract
wiring (S1-T03), the output rows and the eight intermediate Frames (S1-T04),
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
    'AnchorSetDoc',
    'DesignCardRow',
    'GradeRuleRow',
    'MetricDictRow',
    'MetricFactRow',
    'MoneyMinor',
    'Ratio',
    'RedlineRow',
    'StrategyMasterRow',
    'StrictBool',
    'StrictInt',
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


class WeightVersionDoc(_InputRow):
    '''T6 weights, grain version; annual sign-off, frozen within a period
    ([L1104], [L1186]-[L1194]). provenance [L1193] is S1-T03 scope (ORCH-13),
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
