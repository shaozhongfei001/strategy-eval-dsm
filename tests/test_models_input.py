'''RED tests for the eight DSM input models in dsm/models.py (S1-T02, layer L1).

Single source of truth = the digests (ORCH 1.2 forbids reading the SDD here):
- docs/digest/S1-T01.md: model_config frozen + extra=forbid [L865]; the 8 input
  rows T1..T8 field contracts [L1112-L1214]; CEL-0 seven nullable fields [L1174];
  interpretation_limit as a regular formal field [L1172]; V-5 guard [L871].
- docs/digest/S1-T01c.md: 3.13 numeric precision -- money is int in minor units
  with exact equality, no float anywhere in the chain [L1265]; ratios are Decimal
  built from strings with 1e-12 comparison tolerance [L1267]; run_at is injected
  by the CLI, the calculation layer never reads the system clock [L1271].
- docs/digest/S1-T01e.md: V-5 verbatim criterion [L1498]; P-10 [L1434].

Scope discipline (ORCH-13 / task scope): only the 8 input rows plus the Ratio and
MoneyMinor annotated types. WeightProvenance and the CEL-0 contract wiring belong
to S1-T03, output models and Frames to S1-T04, config.py PLACEHOLDER interception
to S1-T05/T06, so none of those branches are asserted here.

All data is synthetic (H-5/H-14); nothing here is a business value awaiting
signature, and no K-01..K-20 suggested value is hard-coded.
'''
import types
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Union, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from dsm import models
from dsm import numeric
from dsm import reason_codes
from dsm.models import (
    AnchorSetDoc,
    DesignCardRow,
    GradeRuleRow,
    MetricDictRow,
    MetricFactRow,
    MoneyMinor,
    Ratio,
    RedlineRow,
    StrategyMasterRow,
    WeightVersionDoc,
)
from dsm.reason_codes import RC

INPUT_ROWS = {
    'StrategyMasterRow': StrategyMasterRow,
    'MetricDictRow': MetricDictRow,
    'MetricFactRow': MetricFactRow,
    'DesignCardRow': DesignCardRow,
    'RedlineRow': RedlineRow,
    'WeightVersionDoc': WeightVersionDoc,
    'GradeRuleRow': GradeRuleRow,
    'AnchorSetDoc': AnchorSetDoc,
}

# CEL-0 reserved fields on DesignCardRow: the seven of [L1174], i.e. NOT
# interpretation_limit (formal field, [L1172] / ORCH-02 in S1-T01.md).
CEL0_RESERVED = (
    'incremental_value',
    'incremental_ci_lower',
    'incremental_ci_upper',
    'estimator_method',
    'experiment_id',
    'holdout_id',
    'mde_ok',
)


def strategy_master_payload():
    '''T1 strategy_master [L1116-L1124].'''
    return {
        'strategy_id': 'SYN-S-001',
        'version_id': 'SYN-V-001',
        'strategy_name': 'SYN-STRATEGY-NAME',
        'biz_domain': 'SYN-DOMAIN-A',
        'scene_code': 'SYN-SCENE-01',
        'segment_type': 'EXISTING',
        'online_date': '2026-01-05',
        'offline_date': '2026-12-31',
        'owner_dept': 'SYN-DEPT-01',
        'owner_name': 'SYN-OWNER-01',
        'status': 'ACTIVE',
        'version_change_note': 'SYN-VERSION-NOTE',
    }


def metric_dict_payload():
    '''T2 metric_dict [L1130-L1143].'''
    return {
        'metric_id': 'SYN-M-001',
        'metric_name': 'SYN-METRIC-NAME',
        'dim_code': 'SYN-DIM-01',
        'numerator_def': 'SYN-NUMERATOR-DEF',
        'denominator_def': 'SYN-DENOMINATOR-DEF',
        'time_window': 'SYN-P1M',
        'dedup_rule': 'SYN-DEDUP-RULE',
        'missing_rule': 'ZERO',
        'outlier_rule': 'CLIP_P1_P99',
        'attainment_formula': 'RATIO_DIRECT',
        'direction': 1,
        # [L1138] + [L1265]-[L1266]: the unit says what the target means, so a
        # MONEY_MINOR target is an int in minor units, never a Decimal.
        'unit': 'MONEY_MINOR',
        'target_value': 100,
        'target_basis': 'SYN-TARGET-BASIS',
        'is_redline': False,
        'owner_name': 'SYN-OWNER-02',
        'signoff_status': 'PENDING',
        'signoff_date': '2026-01-10',
        'dim_signoff_status': 'PENDING',
        'dict_version': 'SYN-MD-001',
        'caliber_version': 'SYN-CAL-001',
    }


def metric_fact_payload():
    '''T3 metric_facts long table [L1149-L1154].'''
    return {
        'strategy_id': 'SYN-S-001',
        'version_id': 'SYN-V-001',
        'period': 'SYN-2026Q1',
        'metric_id': 'SYN-M-001',
        'value_num': 12345,
        'value_den': 100,
        'value': 12345,
        'data_quality_flag': 'OK',
        'snapshot_time': '2026-04-01',
        'data_as_of': '2026-03-31',
        'source_table': 'SYN-SOURCE-TABLE',
        'caliber_version': 'SYN-CAL-001',
    }


def design_card_payload():
    '''T4 design_cards [L1162-L1173] plus interpretation_limit.'''
    return {
        'strategy_id': 'SYN-S-001',
        'version_id': 'SYN-V-001',
        'direct_goal': 'SYN-DIRECT-GOAL',
        'process_metrics': ['SYN-PM-01'],
        'result_metrics': ['SYN-RM-01'],
        'observation_window': 'SYN-P3M',
        'data_source': 'SYN-DATA-SOURCE',
        'data_timeliness': 'SYN-T-PLUS-7',
        'eval_method': 'AB_TEST',
        'control_arrangement': 'RANDOMIZED',
        'success_criteria': 'SYN-SUCCESS-CRITERIA',
        'risk_constraints': 'SYN-RISK-CONSTRAINTS',
        'eval_owner': 'SYN-EVAL-OWNER',
        'alt_method_note': 'SYN-ALT-METHOD-NOTE',
        'interpretation_limit': 'SYN-INTERPRETATION-LIMIT',
        'card_status': 'COMPLETE',
    }


def redline_payload():
    '''T5 redlines [L1180-L1184].'''
    return {
        'metric_id': 'SYN-M-001',
        'level': 'HARD',
        'comparator': 'GT',
        'threshold_value': Decimal('3'),
        'forced_grade': 'L4',
        'reason_code': RC.REDLINE_HARD_HIT.value,
        'waiver_allowed': False,
    }


def weight_version_payload():
    '''T6 weights [L1190-L1194].

    status stays DRAFT here: the FROZEN consistency checks (whatif_run_id etc.)
    belong to config.py loading per [L880], which is S1-T05/T06 scope, so no
    check is pre-implemented. provenance stays absent: the column is nullable
    (S1-T03, [L1193]); its FROZEN presence is config-layer policy [L1435].
    '''
    return {
        'weight_version_id': 'SYN-W-2026',
        'status': 'DRAFT',
        'effective_from': '2026-01-01',
        'effective_to': '2026-12-31',
        'level1_weights': {'SYN-DIM-01': Decimal('0.5'), 'SYN-DIM-02': Decimal('0.5')},
        'level2_weights': {'SYN-DIM-01': {'SYN-M-001': Decimal('1')}},
        'approved_by': 'SYN-COMMITTEE',
        'approved_date': '2026-01-10',
    }


def grade_rule_payload():
    '''T7 grade_rules [L1200-L1206].'''
    return {
        'grade_code': 'L3',
        'grade_label': 'SYN-GRADE-LABEL',
        'attainment_floor': Decimal('0.8'),
        'evidence_class_min': 'B',
        'redline_pass_required': True,
        'promotion_streak': 1,
        'max_grade_if_no_target': 'L3',
    }


def anchor_set_payload():
    '''T8 anchor_set [L1212-L1214].'''
    return {
        'anchor_set_id': 'SYN-ANCHOR-001',
        'strategy_ids': ['SYN-S-001', 'SYN-S-002'],
        'effective_from': '2026-01-01',
        'effective_to': '2026-12-31',
        'rationale': 'SYN-ANCHOR-RATIONALE',
    }


PAYLOAD_BUILDERS = {
    'StrategyMasterRow': strategy_master_payload,
    'MetricDictRow': metric_dict_payload,
    'MetricFactRow': metric_fact_payload,
    'DesignCardRow': design_card_payload,
    'RedlineRow': redline_payload,
    'WeightVersionDoc': weight_version_payload,
    'GradeRuleRow': grade_rule_payload,
    'AnchorSetDoc': anchor_set_payload,
}


def payload_for(row_name):
    return PAYLOAD_BUILDERS[row_name]()


def build(row_name, **overrides):
    payload = payload_for(row_name)
    payload.update(overrides)
    return INPUT_ROWS[row_name](**payload)


# Identity columns only: string-valued, so equality survives any date coercion.
KEY_FIELDS = {
    'StrategyMasterRow': ['strategy_id', 'version_id', 'biz_domain', 'status'],
    'MetricDictRow': ['metric_id', 'dim_code', 'missing_rule', 'unit'],
    'MetricFactRow': ['strategy_id', 'version_id', 'period', 'metric_id'],
    'DesignCardRow': ['strategy_id', 'version_id', 'eval_method', 'card_status'],
    'RedlineRow': ['metric_id', 'level', 'comparator', 'forced_grade'],
    'WeightVersionDoc': ['weight_version_id', 'status', 'approved_by'],
    'GradeRuleRow': ['grade_code', 'grade_label', 'max_grade_if_no_target'],
    'AnchorSetDoc': ['anchor_set_id', 'effective_from', 'rationale'],
}

# ---------------------------------------------------------------------------
# Literal enum tables -- every value copied verbatim from the digest.
# ---------------------------------------------------------------------------
LEGAL_ENUMS = [
    ('StrategyMasterRow', 'status', 'ACTIVE'),
    ('StrategyMasterRow', 'status', 'PAUSED'),
    ('StrategyMasterRow', 'status', 'RETIRED'),
    ('MetricDictRow', 'missing_rule', 'ZERO'),
    ('MetricDictRow', 'missing_rule', 'SKIP'),
    ('MetricDictRow', 'missing_rule', 'IMPUTE_MEDIAN'),
    ('MetricDictRow', 'missing_rule', 'BLOCK'),
    ('MetricDictRow', 'attainment_formula', 'RATIO_DIRECT'),
    ('MetricDictRow', 'attainment_formula', 'INVERSE_RATIO'),
    ('MetricDictRow', 'attainment_formula', 'SHORTFALL_CLAMPED'),
    ('MetricDictRow', 'attainment_formula', 'INTERVAL'),
    ('MetricDictRow', 'unit', 'MONEY_MINOR'),
    ('MetricDictRow', 'unit', 'COUNT'),
    ('MetricDictRow', 'unit', 'RATIO'),
    ('MetricDictRow', 'unit', 'DURATION_SEC'),
    ('MetricDictRow', 'direction', 1),
    ('MetricDictRow', 'direction', -1),
    ('MetricFactRow', 'data_quality_flag', 'OK'),
    ('MetricFactRow', 'data_quality_flag', 'PARTIAL'),
    ('MetricFactRow', 'data_quality_flag', 'SUSPECT'),
    ('MetricFactRow', 'data_quality_flag', 'STALE'),
    ('DesignCardRow', 'eval_method', 'AB_TEST'),
    ('DesignCardRow', 'eval_method', 'RCT'),
    ('DesignCardRow', 'eval_method', 'HOLDOUT'),
    ('DesignCardRow', 'eval_method', 'DID'),
    ('DesignCardRow', 'eval_method', 'SYNTHETIC_CONTROL'),
    ('DesignCardRow', 'eval_method', 'GEO'),
    ('DesignCardRow', 'eval_method', 'SWITCHBACK'),
    ('DesignCardRow', 'eval_method', 'PSM'),
    ('DesignCardRow', 'eval_method', 'OBSERVATIONAL_ONLY'),
    ('DesignCardRow', 'control_arrangement', 'NONE'),
    ('DesignCardRow', 'control_arrangement', 'HISTORICAL_BASELINE'),
    ('DesignCardRow', 'control_arrangement', 'CONCURRENT_CONTROL'),
    ('DesignCardRow', 'control_arrangement', 'RANDOMIZED'),
    ('DesignCardRow', 'card_status', 'COMPLETE'),
    ('DesignCardRow', 'card_status', 'PARTIAL'),
    ('DesignCardRow', 'card_status', 'MISSING'),
    ('RedlineRow', 'level', 'HARD'),
    ('RedlineRow', 'level', 'SOFT'),
    ('RedlineRow', 'comparator', 'GT'),
    ('RedlineRow', 'comparator', 'GTE'),
    ('RedlineRow', 'comparator', 'LT'),
    ('RedlineRow', 'comparator', 'LTE'),
    ('WeightVersionDoc', 'status', 'DRAFT'),
    ('WeightVersionDoc', 'status', 'FROZEN'),
    ('GradeRuleRow', 'grade_code', 'L1'),
    ('GradeRuleRow', 'grade_code', 'L2'),
    ('GradeRuleRow', 'grade_code', 'L3'),
    ('GradeRuleRow', 'grade_code', 'L4'),
    ('GradeRuleRow', 'evidence_class_min', 'A'),
    ('GradeRuleRow', 'evidence_class_min', 'B'),
    ('GradeRuleRow', 'evidence_class_min', 'C'),
    ('GradeRuleRow', 'evidence_class_min', 'D'),
]

# Out-of-enum values. AnchorSetDoc declares no Literal column in the digest
# ([L1212-L1214]), so it has no entry here; its contract is covered by the
# sequence-shape test below.
ILLEGAL_ENUMS = [
    ('StrategyMasterRow', 'status', 'CLOSED'),
    ('MetricDictRow', 'missing_rule', 'IMPUTE_MEAN'),
    ('MetricDictRow', 'attainment_formula', 'RATIO_REVERSE'),
    ('MetricDictRow', 'unit', 'MONEY'),
    ('MetricDictRow', 'direction', 0),
    ('MetricFactRow', 'data_quality_flag', 'DIRTY'),
    ('DesignCardRow', 'eval_method', 'SPLIT_TEST'),
    ('DesignCardRow', 'control_arrangement', 'PASSIVE_BASELINE'),
    ('DesignCardRow', 'card_status', 'DRAFT'),
    ('RedlineRow', 'level', 'CRITICAL'),
    ('RedlineRow', 'comparator', 'EQ'),
    ('WeightVersionDoc', 'status', 'ARCHIVED'),
    ('GradeRuleRow', 'grade_code', 'L5'),
    ('GradeRuleRow', 'evidence_class_min', 'E'),
]

FROZEN_TARGETS = [
    ('StrategyMasterRow', 'status', 'PAUSED'),
    ('MetricDictRow', 'unit', 'COUNT'),
    ('MetricFactRow', 'data_quality_flag', 'STALE'),
    ('DesignCardRow', 'card_status', 'PARTIAL'),
    ('RedlineRow', 'comparator', 'LT'),
    ('WeightVersionDoc', 'weight_version_id', 'SYN-W-2027'),
    ('GradeRuleRow', 'grade_code', 'L2'),
    ('AnchorSetDoc', 'anchor_set_id', 'SYN-ANCHOR-002'),
]


class _MoneyProbe(BaseModel):
    '''Binds the MoneyMinor annotated type so its own semantics are testable
    independently of which input column R2 eventually decorates with it
    (ORCH-07: money = int minor units, reject float / fractional Decimal / bool).
    '''

    amount_minor: MoneyMinor


class _RatioProbe(BaseModel):
    '''Binds the Ratio annotated type (ORCH-07: Decimal from string construction,
    reject float; float may only enter through numeric.from_float()).
    '''

    ratio_value: Ratio


# ---------------------------------------------------------------------------
# 1. Every input row builds from the digest contract.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('row_name', sorted(INPUT_ROWS))
def test_row_builds_from_digest_contract(row_name):
    row = build(row_name)
    assert isinstance(row, INPUT_ROWS[row_name])


@pytest.mark.parametrize('row_name', sorted(INPUT_ROWS))
def test_declared_key_fields_are_readable(row_name):
    row = build(row_name)
    for field_name in KEY_FIELDS[row_name]:
        expected = payload_for(row_name)[field_name]
        assert str(getattr(row, field_name)) == str(expected)


# ---------------------------------------------------------------------------
# 2. V-5 [L1498]/[L871] + [L865]: extra=forbid, undeclared field must error.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('row_name', sorted(INPUT_ROWS))
def test_undeclared_field_is_rejected(row_name):
    payload = payload_for(row_name)
    payload['syn_undeclared_field'] = 'SYN-NOT-DECLARED'
    with pytest.raises(ValidationError):
        INPUT_ROWS[row_name](**payload)


# ---------------------------------------------------------------------------
# 3. [L865]: frozen=True -- a constructed row rejects attribute assignment.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('row_name', sorted(INPUT_ROWS))
def test_model_config_is_frozen_and_forbid(row_name):
    row_cls = INPUT_ROWS[row_name]
    assert issubclass(row_cls, BaseModel)
    config = row_cls.model_config
    assert config.get('frozen') is True
    assert config.get('extra') == 'forbid'


@pytest.mark.parametrize('row_name,field_name,replacement', FROZEN_TARGETS)
def test_rows_are_frozen(row_name, field_name, replacement):
    row = build(row_name)
    with pytest.raises(ValidationError):
        setattr(row, field_name, replacement)


# ---------------------------------------------------------------------------
# 8. Literal enums: legal values accepted, out-of-enum values rejected.
# ---------------------------------------------------------------------------
# [L1138] makes target_value a unit-polymorphic column and [L1265]-[L1267] pin
# the shape per unit, so a probe that swaps the unit alone would trip the row
# cross-check. Every unit probe carries the matching target shape instead of
# the cross-check being relaxed.
UNIT_TARGET_SHAPE = {
    'MONEY_MINOR': 100,
    'COUNT': 7,
    'RATIO': Decimal('0.25'),
    'DURATION_SEC': None,
}


@pytest.mark.parametrize('row_name,field_name,value', LEGAL_ENUMS)
def test_legal_enum_value_is_accepted(row_name, field_name, value):
    overrides = {field_name: value}
    if row_name == 'MetricDictRow' and field_name == 'unit':
        overrides['target_value'] = UNIT_TARGET_SHAPE[value]
    row = build(row_name, **overrides)
    assert str(getattr(row, field_name)) == str(value)


@pytest.mark.parametrize('row_name,field_name,value', ILLEGAL_ENUMS)
def test_illegal_enum_value_is_rejected(row_name, field_name, value):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: value})
# ---------------------------------------------------------------------------
# 4/5/6/7/10. H-4 annotated types (ORCH-07) on the 3.13 rules [L1265-L1267].
# ---------------------------------------------------------------------------
def test_moneyminor_rejects_every_float_form():
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=1.5)
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=100.0)
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=Decimal('1.5'))
    probe = _MoneyProbe(amount_minor=12345)
    assert type(probe.amount_minor) is int


def test_moneyminor_rejects_fractional_decimal_but_keeps_exact_int():
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=Decimal('100.50'))
    probe = _MoneyProbe(amount_minor=Decimal('12345'))
    assert type(probe.amount_minor) is int
    assert probe.amount_minor == 12345


def test_moneyminor_rejects_bool_because_bool_is_an_int_subclass():
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=True)
    with pytest.raises(ValidationError):
        _MoneyProbe(amount_minor=False)
    probe = _MoneyProbe(amount_minor=1)
    assert isinstance(probe.amount_minor, int)
    assert not isinstance(probe.amount_minor, bool)


def test_ratio_rejects_float_and_lands_on_decimal():
    with pytest.raises(ValidationError):
        _RatioProbe(ratio_value=0.5)
    with pytest.raises(ValidationError):
        _RatioProbe(ratio_value=1.0)
    from_string = _RatioProbe(ratio_value='0.5')
    assert isinstance(from_string.ratio_value, Decimal)
    assert from_string.ratio_value == Decimal('0.5')
    from_decimal = _RatioProbe(ratio_value=Decimal('0.5'))
    assert isinstance(from_decimal.ratio_value, Decimal)
    assert from_decimal.ratio_value == Decimal('0.5')


def test_ratio_accepts_float_only_through_the_explicit_from_float_bridge():
    '''[L1267]: ratio comparison tolerance is 1e-12, so a plain 2-digit ratio is
    stored without any hidden rounding, and float only enters via from_float.
    '''
    with pytest.raises(ValidationError):
        _RatioProbe(ratio_value=0.1)
    probe = _RatioProbe(ratio_value=numeric.from_float(0.1))
    assert type(probe.ratio_value) is Decimal
    assert numeric.eq_tol(probe.ratio_value, Decimal('0.1'))


def test_metric_fact_rejects_fractional_float_in_the_value_columns():
    '''[L1150] money uses minor-unit integers and [L1265] forbids float in the
    chain, so a float fact value is a contract violation, not a coercion.
    '''
    with pytest.raises(ValidationError):
        build('MetricFactRow', value_num=1.5)
    with pytest.raises(ValidationError):
        build('MetricFactRow', value=1.5)


def test_metric_dict_rejects_float_target_value():
    with pytest.raises(ValidationError):
        build('MetricDictRow', target_value=0.5)


def test_money_bearing_fact_fields_never_land_as_float():
    row = build('MetricFactRow')
    for field_name in ('value_num', 'value_den', 'value'):
        stored = getattr(row, field_name)
        assert not isinstance(stored, float)
        assert not isinstance(stored, bool)


# ---------------------------------------------------------------------------
# 9. CEL-0 [L1174]/[L1894-L1896]: seven reserved fields, all nullable.
# ---------------------------------------------------------------------------
def test_cel0_reserved_fields_are_declared_and_default_to_none():
    payload = design_card_payload()
    for field_name in CEL0_RESERVED:
        assert field_name not in payload
    row = DesignCardRow(**payload)
    for field_name in CEL0_RESERVED:
        assert getattr(row, field_name) is None


def test_cel0_reserved_fields_are_settable_without_changing_the_rest():
    row = build(
        'DesignCardRow',
        incremental_value=12345,
        incremental_ci_lower=11000,
        incremental_ci_upper=13000,
        estimator_method='SYN-DIFF-IN-DIFF',
        experiment_id='SYN-EXP-001',
        holdout_id='SYN-HOLDOUT-001',
        mde_ok=True,
    )
    assert not isinstance(row.incremental_value, float)
    assert row.experiment_id == 'SYN-EXP-001'
    assert row.holdout_id == 'SYN-HOLDOUT-001'
    assert row.mde_ok is True
    assert row.interpretation_limit == 'SYN-INTERPRETATION-LIMIT'


def test_interpretation_limit_is_a_regular_nullable_field_not_a_cel0_reserve():
    '''ORCH-02: interpretation_limit [L1172] is a formal nullable field; it is
    not one of the 7 CEL-0 reserves [L1174].
    '''
    payload = design_card_payload()
    del payload['interpretation_limit']
    row = DesignCardRow(**payload)
    assert row.interpretation_limit is None
    assert 'interpretation_limit' not in CEL0_RESERVED


# ---------------------------------------------------------------------------
# T8 shape contract: strategy_ids is a collection of ids, not a bare string.
# ---------------------------------------------------------------------------
def test_anchor_strategy_ids_must_be_a_sequence_of_ids():
    row = build('AnchorSetDoc')
    assert list(row.strategy_ids) == ['SYN-S-001', 'SYN-S-002']
    with pytest.raises(ValidationError):
        build('AnchorSetDoc', strategy_ids='SYN-S-001')


# ---------------------------------------------------------------------------
# 11. H-8 static audit: models.py is a pure data layer, it never reads the
# wall clock ([L1271] run_at is injected by the CLI; [L1089] --run-at).
# ---------------------------------------------------------------------------
def test_models_layer_reads_no_wall_clock():
    source = Path(models.__file__).read_text(encoding='utf-8')
    for forbidden in ('datetime.now', 'utcnow', 'time.time', 'date.today'):
        assert forbidden not in source
    for row_name in sorted(INPUT_ROWS):
        assert issubclass(INPUT_ROWS[row_name], BaseModel)

# ---------------------------------------------------------------------------
# 12. Digest field completeness gate (ORCH review of the L1 pass).
#
# Every field the digest names for an input row must actually be declared,
# otherwise R2 could satisfy "make the tests green" by silently omitting a
# column (7.2 L2 minimal-implementation discipline). Field names below are
# copied verbatim from docs/digest/S1-T01.md, line refs inline.
#
# Deliberate scope cuts: the WeightProvenance sub-models are asserted in
# tests/test_models_provenance.py (S1-T03, [L1193]/[L1228-L1244]); the
# provenance column itself is digest-named below. DesignCardRow's
# strategy_id/version_id locator keys are not named in [L1162-L1174] (they come
# from the table grain "策略×版本" [L1102]) so they stay out of this set and are
# instead gated by the construction / extra=forbid tests above, which already
# pass them. The reverse direction IS asserted too (see the surplus gate
# below): declared minus expected must fit an explicit whitelist, so an extra
# column in a frozen + extra=forbid model can no longer slip in unexplained.
# ---------------------------------------------------------------------------
DIGEST_FIELDS = {
    'StrategyMasterRow': {
        # [L1116-L1124]
        'strategy_id', 'version_id', 'strategy_name', 'biz_domain', 'scene_code',
        'segment_type', 'online_date', 'offline_date', 'owner_dept', 'owner_name',
        'status', 'version_change_note',
    },
    'MetricDictRow': {
        # [L1130-L1143]
        'metric_id', 'metric_name', 'dim_code', 'numerator_def', 'denominator_def',
        'time_window', 'dedup_rule', 'missing_rule', 'outlier_rule',
        'attainment_formula', 'direction', 'unit', 'target_value', 'target_basis',
        'is_redline', 'owner_name', 'signoff_status', 'signoff_date',
        'dim_signoff_status', 'dict_version', 'caliber_version',
    },
    'MetricFactRow': {
        # [L1149-L1154] locator keys [L1149]; values [L1150]
        'strategy_id', 'version_id', 'period', 'metric_id', 'value_num',
        'value_den', 'value', 'data_quality_flag', 'snapshot_time', 'data_as_of',
        'source_table', 'caliber_version',
    },
    'DesignCardRow': {
        # [L1162-L1173] formal fields + the 7 CEL-0 reserves [L1174]
        'direct_goal', 'process_metrics', 'result_metrics', 'observation_window',
        'data_source', 'data_timeliness', 'eval_method', 'control_arrangement',
        'success_criteria', 'risk_constraints', 'eval_owner', 'alt_method_note',
        'interpretation_limit', 'card_status',
    } | set(CEL0_RESERVED),
    'RedlineRow': {
        # [L1180-L1184]
        'metric_id', 'level', 'comparator', 'threshold_value', 'forced_grade',
        'reason_code', 'waiver_allowed',
    },
    'WeightVersionDoc': {
        # [L1190-L1194]; provenance named per [L1193] (S1-T03, §3.11.4)
        'weight_version_id', 'status', 'effective_from', 'effective_to',
        'level1_weights', 'level2_weights', 'approved_by', 'approved_date',
        'provenance',
    },
    'GradeRuleRow': {
        # [L1200-L1206] including actions / action_gate [L1205]
        'grade_code', 'grade_label', 'attainment_floor', 'evidence_class_min',
        'redline_pass_required', 'promotion_streak', 'actions', 'action_gate',
        'max_grade_if_no_target',
    },
    'AnchorSetDoc': {
        # [L1212-L1214]
        'anchor_set_id', 'strategy_ids', 'effective_from', 'effective_to',
        'rationale',
    },
}


@pytest.mark.parametrize('row_name', sorted(DIGEST_FIELDS))
def test_every_digest_named_field_is_declared(row_name):
    row_cls = INPUT_ROWS[row_name]
    declared = set(row_cls.model_fields)
    missing = DIGEST_FIELDS[row_name] - declared
    assert not missing, (
        row_name + ' is missing digest-named fields: '
        + ', '.join(sorted(missing))
    )


# Reverse gate. A declared column the digest does not name is tolerated only
# when it is justified here: frozen + extra=forbid ([L865]) makes every surplus
# column a contract change, so it must carry a digest ref and not a habit.
DECLARED_BUT_NOT_DIGEST_NAMED = {
    # DesignCardRow locator keys: the grain is strategy x version ([L1102])
    # while [L1162]-[L1174] names the payload columns only.
    'DesignCardRow': {'strategy_id', 'version_id'},
}


@pytest.mark.parametrize('row_name', sorted(DIGEST_FIELDS))
def test_no_declared_field_outside_the_digest_and_the_whitelist(row_name):
    declared = set(INPUT_ROWS[row_name].model_fields)
    surplus = declared - DIGEST_FIELDS[row_name]
    # A row with nothing to forgive has an empty surplus; the whitelist above is
    # the only place a surplus can be explained, never a silent default.
    allowed = DECLARED_BUT_NOT_DIGEST_NAMED.get(row_name, set())
    unexplained = surplus - allowed
    assert not unexplained, (
        row_name + ' declares columns no digest line signed off: '
        + ', '.join(sorted(unexplained))
    )


def test_the_surplus_whitelist_only_covers_declared_input_rows():
    assert set(DECLARED_BUT_NOT_DIGEST_NAMED) <= set(INPUT_ROWS)


def test_grade_rule_actions_and_action_gate_are_declared_and_nullable():
    '''[L1205] names actions / action_gate; the digest gives no type for either,
    and S1-T06 semantic check "grade_rules 的 action 必须非空" ([L879]) reads them
    later. Per ORCH 10.2-4 they are declared and nullable now; no type is
    pinned here (R2 decides, R4 reviews against the digest).
    '''
    declared = set(GradeRuleRow.model_fields)
    assert {'actions', 'action_gate'} <= declared
    payload = grade_rule_payload()
    assert 'actions' not in payload
    assert 'action_gate' not in payload
    row = GradeRuleRow(**payload)
    assert row.actions is None
    assert row.action_gate is None


def test_all_eight_input_rows_are_frozen_forbid_base_models():
    '''Anti-regression aggregate: 8/8 rows, both config keys, one place.'''
    assert len(INPUT_ROWS) == 8
    for row_name in sorted(INPUT_ROWS):
        row_cls = INPUT_ROWS[row_name]
        assert issubclass(row_cls, BaseModel), row_name
        config = row_cls.model_config
        assert config.get('frozen') is True, row_name
        assert config.get('extra') == 'forbid', row_name


# ---------------------------------------------------------------------------
# 13. [L1138]-[L1139] + [L1265]-[L1267]: target_value is a unit-polymorphic
# column, not a static Ratio. The unit declares what the number means, so the
# contract must refuse a shape the unit contradicts; only MetricDictRow owns
# both columns, so only MetricDictRow can cross-check them.
#
# DURATION_SEC gets no shape rule: [L1265]-[L1267] close money, counts and
# ratios only, the digest is silent on seconds, and ORCH 10.2-4 forbids
# inventing a rule here (the orchestrator logged it as a gap).
# ---------------------------------------------------------------------------
INT_SHAPE_UNITS = ('MONEY_MINOR', 'COUNT')


@pytest.mark.parametrize('unit', INT_SHAPE_UNITS)
@pytest.mark.parametrize('raw', [Decimal('100'), Decimal('100.50'), 100.0])
def test_int_shaped_unit_rejects_decimal_and_float_target(unit, raw):
    '''[L1265]-[L1266]: money is an int in minor units and a count is an int, so
    a Decimal or a float target is a contract violation even when the digits are
    integral -- accepting one would announce "money is a Decimal" in the model.
    '''
    with pytest.raises(ValidationError):
        build('MetricDictRow', unit=unit, target_value=raw)


@pytest.mark.parametrize('unit', INT_SHAPE_UNITS)
@pytest.mark.parametrize('raw', [True, False])
def test_int_shaped_unit_rejects_bool_target(unit, raw):
    with pytest.raises(ValidationError):
        build('MetricDictRow', unit=unit, target_value=raw)


@pytest.mark.parametrize('unit', INT_SHAPE_UNITS)
def test_int_shaped_unit_lands_target_on_an_exact_int(unit):
    row = build('MetricDictRow', unit=unit, target_value=100)
    assert type(row.target_value) is int
    assert not isinstance(row.target_value, bool)
    assert numeric.eq_exact(row.target_value, 100)


@pytest.mark.parametrize('raw', [1, 0, 0.25, 1.0, True])
def test_ratio_unit_rejects_int_and_float_target_value(raw):
    '''[L1267]: a ratio is a Decimal built from a string, so an int is refused
    instead of being silently re-typed into a Decimal.
    '''
    with pytest.raises(ValidationError):
        build('MetricDictRow', unit='RATIO', target_value=raw)


def test_ratio_unit_lands_target_on_a_decimal():
    row = build('MetricDictRow', unit='RATIO', target_value=Decimal('0.25'))
    assert type(row.target_value) is Decimal
    assert numeric.eq_tol(row.target_value, Decimal('0.25'))


@pytest.mark.parametrize('raw', [90, Decimal('90')])
def test_duration_sec_unit_declares_no_target_shape(raw):
    row = build('MetricDictRow', unit='DURATION_SEC', target_value=raw)
    assert type(row.target_value) in (int, Decimal)


@pytest.mark.parametrize('raw', [90.0, True])
def test_duration_sec_unit_still_rejects_float_and_bool(raw):
    '''The unit cross-check says nothing about seconds; H-4 still says no.'''
    with pytest.raises(ValidationError):
        build('MetricDictRow', unit='DURATION_SEC', target_value=raw)


@pytest.mark.parametrize('unit', ['MONEY_MINOR', 'COUNT', 'RATIO', 'DURATION_SEC'])
def test_absent_target_value_is_legal_for_every_unit(unit):
    '''[L930]: a metric without a target is a legal row -- attainment stays null
    and the absence is disclosed upstream by its own registered code, so the
    contract must not invent a number and must not reject the absence of one.
    '''
    row = build('MetricDictRow', unit=unit, target_value=None)
    assert row.target_value is None


# ---------------------------------------------------------------------------
# 14. [L1137]: direction is the closed set {+1, -1}. pydantic lax mode coerces
# bool, float, Decimal and digit strings into the int behind a Literal, which
# leaks an undeclared value through the contract (H-4).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('raw', [True, False, 1.0, -1.0, Decimal('1'), '1', 0, 2])
def test_direction_rejects_every_lax_coercion(raw):
    with pytest.raises(ValidationError):
        build('MetricDictRow', direction=raw)


@pytest.mark.parametrize('raw', [1, -1])
def test_direction_accepts_only_the_two_exact_ints(raw):
    row = build('MetricDictRow', direction=raw)
    assert type(row.direction) is int
    assert not isinstance(row.direction, bool)
    assert numeric.eq_exact(row.direction, raw)

# ---------------------------------------------------------------------------
# 15. [L1183] + V-14: the redline reason_code must be a registered code, and the
# registry is the only source of code spellings (H-7): nothing below writes an
# expected code as a bare string, every one is taken from RC or from the
# redline_hard / redline_soft builders that produce [L993] shaped codes.
# ---------------------------------------------------------------------------
def test_the_registry_resolves_dynamic_per_metric_redline_codes():
    '''Premise of the contract: reason_codes.is_registered already resolves the
    per-metric hard and soft redline forms that [L993] states, so an
    unregistered code really is a typo and not a form the registry hides.'''
    hard = reason_codes.redline_hard('SYN_M01')
    soft = reason_codes.redline_soft('SYN_M01')
    assert reason_codes.is_registered(hard) is True
    assert reason_codes.is_registered(soft) is True
    assert reason_codes.is_registered(RC.REDLINE_HARD_HIT.value) is True
    assert reason_codes.is_registered('TOTALLY_MADE_UP_CODE') is False


def test_redline_reason_code_rejects_an_unregistered_code():
    with pytest.raises(ValidationError):
        build('RedlineRow', reason_code='TOTALLY_MADE_UP_CODE')


def test_redline_reason_code_rejects_a_registered_code_in_the_wrong_case():
    wrong_case = RC.REDLINE_HARD_HIT.value.lower()
    assert reason_codes.is_registered(wrong_case) is False
    with pytest.raises(ValidationError):
        build('RedlineRow', reason_code=wrong_case)


@pytest.mark.parametrize('raw', [None, 7, ''])
def test_redline_reason_code_rejects_a_missing_or_non_text_code(raw):
    with pytest.raises(ValidationError):
        build('RedlineRow', reason_code=raw)


@pytest.mark.parametrize('member', [RC.REDLINE_HARD_HIT, RC.REDLINE_SOFT_HIT])
def test_redline_reason_code_accepts_a_registered_static_code(member):
    row = build('RedlineRow', reason_code=member.value)
    assert row.reason_code == member.value
    assert reason_codes.is_registered(row.reason_code) is True


def test_redline_reason_code_accepts_a_dynamic_per_metric_code():
    code = reason_codes.redline_hard('SYN_M01')
    row = build('RedlineRow', reason_code=code)
    assert row.reason_code == code


def test_redline_reason_code_gate_is_a_registry_check_only():
    '''Any registered code passes: which code may hang on a HARD versus a SOFT
    redline is a semantic question, [L879] assigns it to the config checks of
    S1-T06, and this task must not pre-implement it.
    '''
    row = build('RedlineRow', reason_code=RC.NO_TARGET_VALUE.value)
    assert row.reason_code == RC.NO_TARGET_VALUE.value


# ---------------------------------------------------------------------------
# 16. [L1181]: threshold_value is unit-polymorphic as well, but RedlineRow
# carries no unit column -- [L1180] names metric_id only and the unit lives in
# metric_dict -- so the row shape is gated, not the unit agreement.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('raw', [3, 300])
def test_redline_threshold_int_lands_on_int(raw):
    row = build('RedlineRow', threshold_value=raw)
    assert type(row.threshold_value) is int
    assert numeric.eq_exact(row.threshold_value, raw)


def test_redline_threshold_decimal_lands_on_decimal():
    row = build('RedlineRow', threshold_value=Decimal('1.75'))
    assert type(row.threshold_value) is Decimal
    assert numeric.eq_tol(row.threshold_value, Decimal('1.75'))


@pytest.mark.parametrize('raw', [3.0, 1.05, True, False])
def test_redline_threshold_rejects_float_and_bool(raw):
    with pytest.raises(ValidationError):
        build('RedlineRow', threshold_value=raw)


def test_redline_row_declares_no_unit_column():
    '''The threshold-vs-unit check needs metric_dict ([L1180]) and therefore
    belongs to the semantic checks of [L879] (S1-T06), not to this model.
    '''
    assert 'unit' not in RedlineRow.model_fields


# ---------------------------------------------------------------------------
# 17. [L889]: date columns must be ISO. dsm/models.py has claimed this in its
# module docstring since the L1 pass without a single negative case behind it.
# ---------------------------------------------------------------------------
NON_ISO_DATE_CASES = [
    ('StrategyMasterRow', 'online_date', '2026/01/01'),
    ('StrategyMasterRow', 'online_date', 'not-a-date'),
    ('StrategyMasterRow', 'online_date', '31-12-2026'),
    ('WeightVersionDoc', 'effective_from', '2026/01/01'),
    ('WeightVersionDoc', 'effective_from', 'not-a-date'),
    ('WeightVersionDoc', 'effective_from', '31-12-2026'),
    ('AnchorSetDoc', 'effective_from', '2026/01/01'),
    ('AnchorSetDoc', 'effective_from', 'not-a-date'),
    ('AnchorSetDoc', 'effective_from', '31-12-2026'),
    ('MetricFactRow', 'snapshot_time', '2026/01/01'),
    ('MetricFactRow', 'snapshot_time', 'not-a-date'),
    ('MetricFactRow', 'snapshot_time', '31-12-2026'),
]


@pytest.mark.parametrize('row_name,field_name,raw', NON_ISO_DATE_CASES)
def test_non_iso_date_literal_is_rejected(row_name, field_name, raw):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: raw})


def test_iso_date_and_datetime_literals_still_load():
    master = build('StrategyMasterRow', online_date='2026-01-05')
    assert type(master.online_date) is date
    weights = build('WeightVersionDoc', effective_from='2026-01-01')
    assert type(weights.effective_from) is date
    fact = build('MetricFactRow', snapshot_time='2026-04-01T10:30:00')
    assert type(fact.snapshot_time) is datetime
    assert fact.snapshot_time.isoformat().startswith('2026-04-01')


# ---------------------------------------------------------------------------
# 18. ORCH-18 rulings 1/2/4: lax coercion is closed on EVERY int-semantic and
# bool column, proven by a full-field scan instead of a spot check (the miss
# this section exists to prevent: promotion_streak [L1204]). The field classes
# below are derived from Model.model_fields at import time, so any column a
# later task adds lands in the matching probe set automatically.
#
# Class rules ([L1265]-[L1267] + ORCH-18):
#   INT   plain int column (optionally | None): only a real Python int lands;
#         bool is an int subclass and is refused explicitly, float / Decimal /
#         digit strings are refused ([L1266] counts are ints, H-4).
#   BOOL  bool column (optionally | None): only True / False land ([L1140]
#         [L1174][L1184][L1203]); 1 / 0 / 'true' / 'yes' / 'Y' are silent
#         reinterpretations without a reason_code and are refused (H-6, V-14).
#   POLY  unit-polymorphic value columns ([L1139][L1150][L1174][L1181]) whose
#         int and Decimal branches are already gated by _exact_minor_units /
#         numeric.as_minor plus numeric.D (R4 judged them pass, so the gates
#         stay untouched): the scan re-proves that bool and float land on
#         NEITHER branch. A numeric string may still land on the Decimal
#         branch -- that is the audited string constructor of [L1267], not a
#         lax coercion, and CSV text conversion belongs to io_loaders
#         (ORCH-18 ruling 3, B-010).
#   RATIO Decimal-only columns ([L1201], [L1267]): gated by numeric.D; the
#         scan proves float and bool are refused and a string lands as
#         Decimal. The weight dicts of [L1192] carry Ratio values behind a
#         container and are pinned by an explicit case at the end.
# ---------------------------------------------------------------------------
def _gate_name(item):
    func = getattr(item, 'func', None)
    func_name = getattr(func, '__name__', '')
    if func_name:
        return type(item).__name__ + ':' + func_name
    return type(item).__name__


def _walk_annotation(ann, bases, gates):
    '''Unwrap Annotated metadata and unions down to the bare carrier types.
    pydantic moves a top-level BeforeValidator into FieldInfo.metadata, so
    _classify_field merges both sources.
    '''
    metadata = getattr(ann, '__metadata__', ())
    if metadata:
        for item in metadata:
            gates.append(_gate_name(item))
        ann = ann.__origin__
    origin = get_origin(ann)
    if origin is Union or origin is types.UnionType:
        for arg in get_args(ann):
            _walk_annotation(arg, bases, gates)
        return
    bases.add(ann)


def _classify_field(info):
    bases, gates = set(), []
    _walk_annotation(info.annotation, bases, gates)
    for item in info.metadata:
        gates.append(_gate_name(item))
    kinds = bases - {type(None)}
    nullable = type(None) in bases
    if kinds == {bool}:
        kind = 'BOOL'
    elif kinds == {int}:
        kind = 'INT'
    elif kinds == {int, Decimal}:
        kind = 'POLY'
    elif kinds == {Decimal}:
        kind = 'RATIO'
    else:
        kind = 'OTHER'
    return kind, nullable, tuple(sorted(set(gates)))


def _scan_columns(kind):
    '''(row_name, field_name, nullable, gates) of every column of that kind.'''
    found = []
    for row_name, row in INPUT_ROWS.items():
        for field_name, info in row.model_fields.items():
            field_kind, nullable, gates = _classify_field(info)
            if field_kind == kind:
                found.append((row_name, field_name, nullable, gates))
    return found


INT_COLUMNS = _scan_columns('INT')
BOOL_COLUMNS = _scan_columns('BOOL')
POLY_COLUMNS = _scan_columns('POLY')
RATIO_COLUMNS = _scan_columns('RATIO')

# The probe forms of ORCH-18 ruling 4 plus their closest relatives.
INT_LAX_PROBES = [True, False, 1.0, 3.0, Decimal('3'), '3', '3.0', b'3']
BOOL_LAX_PROBES = [1, 0, 'true', 'false', 'yes', 'no', 'Y', 'N', '1', '0',
                   1.0, 0.0, Decimal('1')]
POLY_FLOAT_PROBES = [True, False, 1.0, -1.0, 0.5]
RATIO_LAX_PROBES = [True, False, 1.0, 0.8, 0.5]


def test_the_scan_sees_every_int_and_bool_column_named_by_the_digest():
    '''Meta-guard on the classifier itself: the columns ORCH-18 names must be
    in the scan sets. Subset assertions only, so later tasks just widen them.
    '''
    int_pairs = {(r, f) for r, f, _, _ in INT_COLUMNS}
    assert ('GradeRuleRow', 'promotion_streak') in int_pairs
    bool_pairs = {(r, f) for r, f, _, _ in BOOL_COLUMNS}
    for pair in (('MetricDictRow', 'is_redline'), ('DesignCardRow', 'mde_ok'),
                 ('RedlineRow', 'waiver_allowed'),
                 ('GradeRuleRow', 'redline_pass_required')):
        assert pair in bool_pairs
    poly_pairs = {(r, f) for r, f, _, _ in POLY_COLUMNS}
    for pair in (('MetricDictRow', 'target_value'), ('MetricFactRow', 'value'),
                 ('RedlineRow', 'threshold_value')):
        assert pair in poly_pairs
    ratio_pairs = {(r, f) for r, f, _, _ in RATIO_COLUMNS}
    assert ('GradeRuleRow', 'attainment_floor') in ratio_pairs


@pytest.mark.parametrize('row_name,field_name,nullable,gates', INT_COLUMNS)
def test_every_scanned_int_column_carries_a_before_validator_gate(row_name, field_name, nullable, gates):
    assert any(g.startswith('BeforeValidator') for g in gates)


@pytest.mark.parametrize('row_name,field_name,nullable,gates', INT_COLUMNS)
@pytest.mark.parametrize('probe', INT_LAX_PROBES)
def test_scanned_int_column_rejects_every_lax_form(row_name, field_name, nullable, gates, probe):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: probe})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', INT_COLUMNS)
def test_scanned_int_column_lands_a_real_int_and_honours_nullability(row_name, field_name, nullable, gates):
    stored = getattr(build(row_name, **{field_name: 2}), field_name)
    assert type(stored) is int
    assert not isinstance(stored, bool)
    assert numeric.eq_exact(stored, 2)
    if nullable:
        assert getattr(build(row_name, **{field_name: None}), field_name) is None
    else:
        with pytest.raises(ValidationError):
            build(row_name, **{field_name: None})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', BOOL_COLUMNS)
def test_every_scanned_bool_column_carries_a_before_validator_gate(row_name, field_name, nullable, gates):
    assert any(g.startswith('BeforeValidator') for g in gates)


@pytest.mark.parametrize('row_name,field_name,nullable,gates', BOOL_COLUMNS)
@pytest.mark.parametrize('probe', BOOL_LAX_PROBES)
def test_scanned_bool_column_rejects_every_non_python_bool(row_name, field_name, nullable, gates, probe):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: probe})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', BOOL_COLUMNS)
def test_scanned_bool_column_lands_a_real_bool_and_honours_nullability(row_name, field_name, nullable, gates):
    for probe in (True, False):
        stored = getattr(build(row_name, **{field_name: probe}), field_name)
        assert type(stored) is bool
        assert stored is probe
    if nullable:
        assert getattr(build(row_name, **{field_name: None}), field_name) is None
    else:
        with pytest.raises(ValidationError):
            build(row_name, **{field_name: None})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', POLY_COLUMNS)
def test_every_scanned_poly_column_keeps_both_branch_gates(row_name, field_name, nullable, gates):
    assert any('as_minor' in g or '_exact_minor_units' in g for g in gates)
    assert any(g.endswith(':D') for g in gates)


@pytest.mark.parametrize('row_name,field_name,nullable,gates', POLY_COLUMNS)
@pytest.mark.parametrize('probe', POLY_FLOAT_PROBES)
def test_scanned_poly_column_rejects_bool_and_float_on_both_branches(row_name, field_name, nullable, gates, probe):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: probe})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', POLY_COLUMNS)
def test_scanned_poly_column_lands_an_int_probe_on_the_int_branch(row_name, field_name, nullable, gates):
    stored = getattr(build(row_name, **{field_name: 7}), field_name)
    assert type(stored) is int
    assert numeric.eq_exact(stored, 7)


@pytest.mark.parametrize('row_name,field_name,nullable,gates', RATIO_COLUMNS)
def test_every_scanned_ratio_column_keeps_the_numeric_d_gate(row_name, field_name, nullable, gates):
    assert 'BeforeValidator:D' in gates


@pytest.mark.parametrize('row_name,field_name,nullable,gates', RATIO_COLUMNS)
@pytest.mark.parametrize('probe', RATIO_LAX_PROBES)
def test_scanned_ratio_column_rejects_float_and_bool(row_name, field_name, nullable, gates, probe):
    with pytest.raises(ValidationError):
        build(row_name, **{field_name: probe})


@pytest.mark.parametrize('row_name,field_name,nullable,gates', RATIO_COLUMNS)
def test_scanned_ratio_column_lands_a_decimal_from_a_string(row_name, field_name, nullable, gates):
    stored = getattr(build(row_name, **{field_name: '0.8'}), field_name)
    assert type(stored) is Decimal
    assert numeric.eq_tol(stored, Decimal('0.8'))


def test_weight_dict_values_stay_behind_the_ratio_gate():
    '''level1_weights / level2_weights [L1192] are containers, so the field
    scan sees dict; this pins their Ratio value gate explicitly ([L1267]).
    '''
    with pytest.raises(ValidationError):
        build('WeightVersionDoc', level1_weights={'SYN-DIM-01': 0.5})
    with pytest.raises(ValidationError):
        build('WeightVersionDoc', level2_weights={'SYN-DIM-01': {'SYN-M-001': True}})
    row = build('WeightVersionDoc', level1_weights={'SYN-DIM-01': Decimal('1')})
    assert type(row.level1_weights['SYN-DIM-01']) is Decimal
