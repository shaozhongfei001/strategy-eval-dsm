'''RED tests for the S1-T04 output contract of dsm/models.py (L1, RED by design).

Contract authority = docs/adr/ORCH-22.md rulings 14-33, applied field by field.
The SDD wording behind it is carried by docs/digest/S1-T04.md (AuditBundle 15
items [L1051], the 7 report files [L1062], the section 3.11.3 grains
[L1218]-[L1226], V-8 [L1863], CEL-0 output side [L1896]-[L1902]) and
docs/digest/S1-T01d.md (Frame fields [L928], [L939]-[L945], [L952]-[L955],
[L964]-[L968], [L977]-[L994], [L1001]-[L1006]; output models [L1015]-[L1040];
section 4.6 [L1608]-[L1640]). docs/adr/ORCH-13.md rulings 1/2 supply the
ScoringContext / NormalizedRow / RedlineEvalRow closure, adopted and extended
by ORCH-22 rulings 28 and 30; ORCH-14 (unit polymorphism), ORCH-16 (verbatim
SDD names), ORCH-17/18 (StrictInt / StrictBool gates) and ORCH-20/21
(nullability precedent) constrain the shapes.

Coverage map (checklist letters, for the R4 review):

  A  33 model classes exist and subclass pydantic.BaseModel: 6 output models
     ([L867]) + 8 Frames + PoolStats + ScoringContext ([L868]) + 10 sub-models
     + 7 Frame row models (ORCH-22 rulings 14-30 and 33).
  B  the 9 new enum / alias names hold exactly the SDD value sets (ruling 33):
     SchemeName [L1015], StabilityLabel (ORCH-03: NEAR_BOUNDARY, never the
     [L1018] spelling BOUNDARY), FrameGrade [L964] (ruling 20), EntropyStatus
     [L1040] (ruling 27), MethodAgreement [L1028], NormalizationMethod [L940]
     lowercase verbatim, ScoreOperator [L953], EvidenceMode [L978], and the
     InputFingerprints type alias [L888] (ruling 15).
  C  the existing GradeCode [L1200] stays exactly L1..L4 - the anti-shortcut
     regression gate of ruling 20 (NOT_ASSESSED must not leak into it).
  D  per-model field-name sets equal the ruling tables, both directions
     (rulings 14-30): AuditBundle 16 (15 items, item 11 split), GradeLedgerRow
     with recommended_action / decided_action / decision_note as three separate
     columns [L1630] + V-8 [L1863], EntropyDiagnosticRow 10 with metric_code
     (ORCH-22 section 0 item 3, NOT metric_id), PoolStatRow reporting both
     shares [L1003], ScoreCardRow carrying evidence_source (ORCH-15) and the
     ruling-22 suffix split (value_captured_minor versus the three verbatim
     incremental_* names).
  E  frozen + extra=forbid on every model ([L865]/[L871], V-5), including the
     undeclared-column negative construction.
  F  a built instance refuses reassignment (frozen).
  G  H-4 [L1265]-[L1267]: no bare float, no bare int, no bare bool anywhere in
     the 33 models; every ratio-shaped column resolves to Decimal; plus the
     behavioural probes (exit_code, composite_absolute, PoolStatRow.count).
  H  H-6/H-7: every ReasonCode column accepts a registered RC member or its
     .value, and refuses a bare string as well as the str(RC.X) form, which is
     'RC.X' and therefore unregistered.
  I  ruling 27 closure: status='ENTROPY_UNSTABLE' is a ValidationError; the
     B-018 marker lives in flags only.
  J  H-5: no business-number default anywhere; the nullable / empty-container /
     required partition equals the ruling tables (rulings 14-30).
  K  H-8 [L1271]: no wall-clock read in dsm/models.py (AST scan).
  L  H-9 INV-1/INV-3: dsm/models.py imports no L0a/L0b module and no
     diagnostics.
  M  ruling 28: no set / frozenset annotation anywhere ([L1053] items 3/4, V-3).
  N  ruling 5 item 8: the registries and models.__all__ cover each other both
     ways (the S1-T02 R4 followup, institutionalised).
  O  ruling 29 / 15: one shared PoolKey class object and one shared
     InputFingerprints alias, not a private copy per model.
  P  ruling 30: the ScoringContext B group carries the 8 Frame classes itself
     and the A group scalars are datetime / str / StrictInt-nullable.

Two count discrepancies inside the contract authority itself, recorded here for
the orchestrator and NOT resolved by this file (H-10 forbids inventing a field
to close a gap, H-11 forbids bending a table to a headline number):

  (1) ruling 21 is titled "36 fields" and its closing line repeats the
      total 36, but the ruling-21 table enumerates 35 field names. The
      registry below copies the table verbatim (35). If a 36th column
      exists in the master intent it has to be ruled and named first.
  (2) the R4 checklist says "GradeLedgerRow = 13 fields", while the ruling-24
      table enumerates 14 (locator trio + grade + previous_grade + the three
      action/note columns + owner pair + deadline + archive_ref + ledger_complete
      + usable_for_elimination [L1019]). The registry copies the table (14).
      (3) the R4 checklist counts "33 model classes" while ORCH-22 authorises
      32 distinct ones: PoolStats is counted both inside the [L868] eight
      intermediate models and again as "+ PoolStats". The registries below
      therefore hold 32 classes (6 + 7 Frame + PoolStats + ScoringContext +
      10 sub + 7 row); no 33rd name is invented, because ruling 33 closes the
      surplus whitelist.

All data is synthetic (SYN- prefix, H-5/H-14): no real business value, no
K-01..K-20 governance number is proposed or hard-coded; ratios are Decimal built
from strings, money is an int in minor currency units, counts are plain ints.
Nothing in this file touches an unimplemented attribute at import time - every
reference goes through cls() / alias(), so the module always collects and each
RED failure is an AttributeError (feature not implemented) or a pydantic
ValidationError, matching the S1-T03 RED shape and ORCH section 7.2 L1.
'''
import ast
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, get_args, get_origin

import pytest
from pydantic import BaseModel, ValidationError

from dsm import models
from dsm.reason_codes import RC, Severity

MODELS_PATH = Path(models.__file__)


# ---------------------------------------------------------------------------
# Resolution helpers. Attribute access only, so a missing name raises
# AttributeError (feature not implemented) instead of breaking collection.
# ---------------------------------------------------------------------------
def cls(name):
    '''Resolve a model class out of dsm.models by name.'''
    resolved = getattr(models, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.models has no attribute ' + name
            + ' (S1-T04 output contract not implemented yet)')
    return resolved


def alias(name):
    '''Resolve a non-model public name (Literal alias, type alias) by name.'''
    resolved = getattr(models, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.models has no attribute ' + name
            + ' (S1-T04 alias not implemented yet)')
    return resolved


def build(name, **overrides):
    '''Construct a model from its synthetic payload, with column overrides.

    The class is resolved inside the call, so an unimplemented model fails
    with AttributeError, and only once it exists can a probe fail with a
    pydantic ValidationError.'''
    payload = dict(SYN_PAYLOADS[name])
    payload.update(overrides)
    return cls(name)(**payload)


def declared(name):
    '''The declared column-name set of a model.'''
    return set(cls(name).model_fields)


def _unwrap(annotation):
    '''Annotated[X, gate] -> X; pydantic gates wrap the real type.'''
    if hasattr(annotation, '__metadata__'):
        return _unwrap(get_args(annotation)[0])
    return annotation


def _literal_values(annotation):
    inner = _unwrap(annotation)
    if get_origin(inner) is Literal:
        return tuple(get_args(inner))
    return ()


def model_in(annotation):
    '''Pull the BaseModel subclass out of a (nullable) model annotation.'''
    inner = _unwrap(annotation)
    if isinstance(inner, type) and issubclass(inner, BaseModel):
        return inner
    for arg in get_args(inner):
        candidate = _unwrap(arg)
        if isinstance(candidate, type) and issubclass(candidate, BaseModel):
            return candidate
    raise AssertionError('annotation carries no BaseModel: ' + repr(annotation))


# ---------------------------------------------------------------------------
# Synthetic scalars (H-5 / H-14). Identifiers are SYN- tokens, money is an int
# in minor currency units, ratios are Decimal built from strings, dates and
# timestamps are fixed synthetic instants (never read from a clock, H-8).
# ---------------------------------------------------------------------------
S_ID = 'SYN-S-001'
S_ID_B = 'SYN-S-002'
V_ID = 'SYN-V-001'
PERIOD = 'SYN-P-2026Q1'
M_ID = 'SYN-M-001'
M_ID_B = 'SYN-M-002'
DIM = 'SYN-DIM-01'
WV_ID = 'SYN-WV-0001'
DICT_VERSION = 'SYN-DICTV-0001'
ANCHOR_SET_ID = 'SYN-ANCHOR-0001'
RUN_ID = 'SYN-RUN-0001'
DSM_VERSION = 'SYN-DSM-1.0.0'
DESIGN_VERSION = 'SYN-DESIGN-1'
CEL_CONTRACT_VERSION = 'SYN-CELCONTRACT-0'
OWNER_DEPT = 'SYN-DEPT-01'
OWNER_NAME = 'SYN-OWNER-01'
BIZ_DOMAIN = 'SYN-BD-01'
EVIDENCE_A = 'A'
SHA_A = 'SYN-SHA-A'
SHA_B = 'SYN-SHA-B'
TABLE_KEY = 'SYN-T-T1'
OUT_FILE = 'SYN-score_card.csv'
ACTION_1 = 'SYN-ACTION-01'
ACTION_2 = 'SYN-ACTION-02'
NOTE_TEXT = 'SYN-NOTE-01'
LIMIT_TEXT = 'SYN-LIMIT-01'
FINDING_CODE = 'SYN-C-01'
FINDING_MSG = 'SYN-MSG-01'
WAIVER_ID = 'SYN-WAIVER-01'
WAIVER_SCOPE = 'SYN-SCOPE-01'
TARGET_SOURCE = 'SYN-BASIS-01'
CONTROL_GROUP_ID = 'SYN-CG-01'
ESTIMATOR_METHOD = 'SYN-ESTIMATOR-01'
ARCHIVE_REF = 'SYN-ARCHIVE-01'
REASON_KEY = RC.NOT_ASSESSED.value
UNDECLARED_COLUMN = 'SYN_UNDECLARED_NOT_IN_CONTRACT'
UNREGISTERED = 'SYN_NOT_A_REGISTERED_RC'

RATIO = Decimal('0.5')
RATIO_B = Decimal('0.25')
MINOR = 1500
MINOR_B = 700
CNT = 7
CNT_B = 3
CNT_C = 11
RANK = 4
SEED = 11
EXIT_OK = 0
DIRECTION_UP = 1
RUN_AT = datetime(2026, 1, 15, 10, 30, 0)
DAY = date(2026, 1, 15)
DAY_B = date(2026, 2, 15)

FP_ROW = {'sha256': SHA_A, 'row_count': CNT}
POOL_KEY_ROW = {'biz_domain': BIZ_DOMAIN, 'evidence_class': EVIDENCE_A}
METRIC_CELL = {'actual_value': MINOR, 'target_value': MINOR_B,
               'attainment': RATIO}
DIM_CELL = {'attainment': RATIO, 'relative_score': RATIO_B,
            'coverage': RATIO, 'weight': RATIO}
SCHEME_RESULT = {'scheme': 'OAT_10', 'overall_flip_rate': RATIO,
                 'flipped_count': CNT_B, 'assessed_count': CNT,
                 'flag': RC.FLIP_RATE_REVIEW.value}
STRATEGY_SENS = {'strategy_id': S_ID, 'version_id': V_ID,
                 'stability_label': 'STABLE', 'flip_under_pct10': RATIO,
                 'flip_under_pct20': RATIO_B}
TRI_ROW = {'strategy_id': S_ID, 'version_id': V_ID, 'topsis_rank': RANK,
           'gra_rank': CNT_B}
POOL_STAT_ROW = {'pool_key': POOL_KEY_ROW, 'count': CNT,
                 'share_in_pool': RATIO, 'share_overall': RATIO_B}
PREFLIGHT_ROW = {'code': FINDING_CODE, 'severity': Severity.WARN,
                 'message': FINDING_MSG}
DOWNGRADE_ROW = {'reason_code': RC.WEIGHT_REALLOCATED.value,
                 'action': ACTION_1, 'subject': S_ID}
ATTAINMENT_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'metric_id': M_ID, 'attainment': RATIO, 'direction': DIRECTION_UP,
    'target_source': TARGET_SOURCE, 'has_target': True,
    'capped_flag': False, 'reason_code': RC.NO_TARGET_VALUE.value,
}
NORMALIZED_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'metric_id': M_ID, 'pool_key': POOL_KEY_ROW, 'norm_value': RATIO,
    'method': 'min_max', 'anchor_used': True,
    'reason_code': RC.ANCHOR_SET_STALE.value,
}
EVIDENCE_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'evidence_class': 'B',
    'evidence_reason': RC.EVIDENCE_CARD_MISSING.value,
    'evidence_source': 'CARD_ONLY', 'control_group_id': CONTROL_GROUP_ID,
    'interpretation_limit': LIMIT_TEXT,
}
REDLINE_EVAL_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'metric_id': M_ID, 'level': 'HARD', 'comparator': 'GTE',
    'threshold_value': MINOR, 'hit': True, 'forced_grade': 'L4',
    'waiver_approval_id': WAIVER_ID, 'waiver_valid_from': DAY,
    'waiver_valid_to': DAY_B, 'waiver_scope': WAIVER_SCOPE,
    'soft_deduction': RATIO, 'reason_code': RC.REDLINE_HARD_HIT.value,
}
SCORE_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'composite_absolute': RATIO, 'composite_relative': RATIO_B,
    'dim_absolute': {DIM: RATIO}, 'dim_relative': {DIM: RATIO_B},
    'coverage': RATIO, 'weight_version_id': WV_ID, 'operator': 'LINEAR',
}
GRADE_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'grade': 'L2', 'grade_reason_path': (RC.NOT_ASSESSED.value,),
    'capped': False, 'cap_reason': RC.ATTAINMENT_CAPPED.value,
    'action': (ACTION_1,), 'usable_for_elimination': True,
}
POOL_ROW = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'pool_key': POOL_KEY_ROW, 'pool_rank': RANK,
    'primary_pool_eligible': True,
    'reject_reason': RC.PRIMARY_POOL_REJECTED_EVIDENCE.value,
}

# ---------------------------------------------------------------------------
# Model registries. Key = class name, value = the field list copied verbatim
# from ORCH-22, each entry (field name, kind) where kind is
#   'req'   required, no default
#   'null'  nullable with a None default (H-5: None, never an empty string)
#   'empty' container with an empty () / {} default (ruling 32 item 3)
# ---------------------------------------------------------------------------
OUTPUT_MODELS = {
    # ruling 21 [L1612]-[L1626] + [L1220] grain, see the header note on 35/36.
    'ScoreCardRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('weight_version_id', 'req'), ('dict_version', 'req'),
        ('anchor_set_id', 'req'), ('run_id', 'req'),
        ('per_metric', 'req'), ('per_dim', 'req'),
        ('composite_absolute', 'null'), ('composite_relative', 'null'),
        ('evidence_class', 'req'), ('evidence_reason', 'req'),
        ('evidence_source', 'req'), ('interpretation_limit', 'null'),
        ('redline_pass', 'req'), ('redline_flags', 'empty'),
        ('grade', 'req'), ('grade_reason_codes', 'req'),
        ('capped_flag', 'req'), ('cap_reason', 'null'),
        ('ranking_pool', 'null'), ('rank_in_pool', 'null'),
        ('pool_size', 'null'),
        ('eligible_for_L1_library', 'req'), ('l1_gate_reasons', 'empty'),
        ('stability_label', 'null'), ('flip_under_pct10', 'null'),
        ('flip_under_pct20', 'null'), ('usable_for_elimination', 'req'),
        ('incremental_value', 'null'), ('incremental_ci_lower', 'null'),
        ('incremental_ci_upper', 'null'), ('estimator_method', 'null'),
        ('value_captured_minor', 'null'),
    ),
    # ruling 24 [L1221] grain + [L1630]-[L1634] + [L1019].
    'GradeLedgerRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('grade', 'req'), ('previous_grade', 'null'),
        ('recommended_action', 'null'), ('decided_action', 'null'),
        ('decision_note', 'null'), ('owner_dept', 'null'),
        ('owner_name', 'null'), ('deadline', 'null'),
        ('archive_ref', 'null'), ('ledger_complete', 'req'),
        ('usable_for_elimination', 'req'),
    ),
    # ruling 25 [L1018]-[L1020] + [L1222] grain.
    'SensitivityReport': (
        ('by_scheme', 'req'), ('by_strategy', 'req'),
        ('loo_dominant_metrics', 'empty'),
        ('norm_swap_rank_correlation', 'null'), ('flags', 'empty'),
        ('seed', 'null'),
        # LOO-1 (ORCH-40 / R-15): [L748] impact ranking carrier, appended last
        # so no ruling-25 column moves. Data-table sync only, zero assert change.
        ('loo_impact', 'empty'),
    ),
    # ruling 27 [L1040]-[L1041] + [L1223] grain + the B-018 flags carrier.
    'EntropyDiagnosticRow': (
        ('metric_code', 'req'), ('e_j', 'req'), ('d_j', 'req'),
        ('cv_j', 'req'), ('vif_j', 'null'), ('max_abs_corr', 'null'),
        ('status', 'req'), ('suggested_action', 'null'), ('owner', 'req'),
        ('flags', 'empty'),
    ),
    # ruling 26 [L1028]-[L1030] + [L1224] grain.
    'TriangulationReport': (
        ('rows', 'req'), ('rho_main_topsis', 'null'),
        ('rho_main_gra', 'null'), ('rho_topsis_gra', 'null'),
        ('mean_rho', 'null'), ('agreement', 'null'),
        ('gra_by_metric', 'req'), ('flags', 'empty'),
    ),
    # ruling 14: the 15 verbatim items of [L1051], item 11 split in two.
    'AuditBundle': (
        ('run_id', 'req'), ('run_at', 'req'), ('period', 'req'),
        ('dsm_version', 'req'), ('design_version', 'req'),
        ('cel_contract_version', 'req'), ('weight_version_id', 'req'),
        ('config_snapshot_sha256', 'req'), ('input_fingerprints', 'req'),
        ('output_fingerprints', 'req'), ('sensitivity_schemes', 'req'),
        ('seed', 'null'), ('preflight_findings', 'req'),
        ('downgrade_actions', 'req'), ('exit_code', 'req'),
        ('reproducibility_hash', 'req'),
    ),
}

FRAME_MODELS = {
    # ruling 28: row-shaped Frames, [L928] / [L945] / [L977] / [L988] /
    # [L952] / [L964] / [L1002], plus PoolStats [L1006] and ScoringContext
    # (ORCH-13 ruling 1 as amended by ruling 30).
    'AttainmentFrame': (
        ('rows', 'req'), ('attainment_coverage', 'req'),
    ),
    # MODELS-1 / ORCH-32 裁决 2+5：NormalizedFrame 增两条 frame 级披露列。
    # 这是经主控授权的 R-15 契约变更（dsm/models.py 在 MODELS-1 写集内），
    # 本表是该契约的登记镜像，故同步更新；两列都是 'empty'（空容器默认），
    # 不是 'null'，也不携带任何业务数值（H-5）。未新增任何模型类，
    # 故 SUB_MODELS 的 17 / ALL_MODELS 的 32 两个花名册计数一字未动。
    'NormalizedFrame': (
        ('rows', 'req'), ('warnings', 'empty'), ('excluded', 'empty'),
    ),
    'EvidenceFrame': (('rows', 'req'),),
    'RedlineFrame': (('rows', 'req'),),
    'ScoreFrame': (('rows', 'req'),),
    'GradeFrame': (('rows', 'req'),),
    'PoolFrame': (('rows', 'req'),),
    'PoolStats': (
        ('rows', 'req'), ('evidence_structure', 'req'),
        ('not_assessed_count', 'req'), ('not_assessed_reasons', 'req'),
    ),
    'ScoringContext': (
        ('period', 'req'), ('run_at', 'req'), ('run_id', 'req'),
        ('seed', 'null'), ('weight_version_id', 'req'),
        ('evidence_mode', 'req'), ('cel_enabled', 'req'),
        ('input_fingerprints', 'req'),
        ('attainment', 'req'), ('normalized', 'req'), ('evidence', 'req'),
        ('redline', 'req'), ('score', 'req'), ('grade', 'req'),
        ('pool', 'req'), ('pool_stats', 'req'),
    ),
}

SUB_MODELS = {
    # the 10 sub-models and 7 Frame row models authorised by ruling 33.
    'InputTableFingerprint': (('sha256', 'req'), ('row_count', 'req')),
    'PreflightFinding': (
        ('code', 'req'), ('severity', 'req'), ('message', 'req'),
    ),
    'DowngradeAction': (
        ('reason_code', 'req'), ('action', 'req'), ('subject', 'null'),
    ),
    # D-MODELS-01 / ORCH-29 第 4 条 / ORCH-32 第 4 条：Step2 松键时 evidence_class
    # 尚不存在，故为可空（不填默认值伪造，V-14）；Step7 的严键由
    # pooling.step7_pool_key 强制。字段**名与个数**未变（test_o02 照旧钉住两列）。
    'PoolKey': (('biz_domain', 'req'), ('evidence_class', 'null')),
    'ScoreCardMetricCell': (
        ('actual_value', 'req'), ('target_value', 'null'),
        ('attainment', 'null'),
    ),
    'ScoreCardDimCell': (
        ('attainment', 'null'), ('relative_score', 'null'),
        ('coverage', 'req'), ('weight', 'req'),
    ),
    'SensitivitySchemeResult': (
        ('scheme', 'req'), ('overall_flip_rate', 'req'),
        ('flipped_count', 'req'), ('assessed_count', 'req'),
        ('flag', 'null'),
    ),
    'SensitivityStrategyRow': (
        ('strategy_id', 'req'), ('version_id', 'req'),
        ('stability_label', 'req'), ('flip_under_pct10', 'null'),
        ('flip_under_pct20', 'null'),
    ),
    'TriangulationStrategyRow': (
        ('strategy_id', 'req'), ('version_id', 'req'),
        ('topsis_rank', 'req'), ('gra_rank', 'req'),
    ),
    'PoolStatRow': (
        ('pool_key', 'req'), ('count', 'req'), ('share_in_pool', 'req'),
        ('share_overall', 'req'),
    ),
    'AttainmentRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('metric_id', 'req'), ('attainment', 'null'), ('direction', 'req'),
        ('target_source', 'null'), ('has_target', 'req'),
        ('capped_flag', 'req'), ('reason_code', 'null'),
    ),
    'NormalizedRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('metric_id', 'req'), ('pool_key', 'req'), ('norm_value', 'req'),
        ('method', 'req'), ('anchor_used', 'req'), ('reason_code', 'null'),
    ),
    'EvidenceRow': (
        ('strategy_id', 'req'), ('version_id', 'req'),
        ('evidence_class', 'req'), ('evidence_reason', 'req'),
        ('evidence_source', 'req'), ('control_group_id', 'null'),
        ('interpretation_limit', 'null'),
    ),
    'RedlineEvalRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('metric_id', 'req'), ('level', 'req'), ('comparator', 'req'),
        ('threshold_value', 'req'), ('hit', 'req'),
        ('forced_grade', 'null'), ('waiver_approval_id', 'null'),
        ('waiver_valid_from', 'null'), ('waiver_valid_to', 'null'),
        ('waiver_scope', 'null'), ('soft_deduction', 'null'),
        ('reason_code', 'null'),
    ),
    'ScoreRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('composite_absolute', 'null'), ('composite_relative', 'null'),
        ('dim_absolute', 'req'), ('dim_relative', 'req'),
        ('coverage', 'req'), ('weight_version_id', 'req'),
        ('operator', 'req'),
    ),
    'GradeRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('grade', 'req'), ('grade_reason_path', 'req'), ('capped', 'req'),
        ('cap_reason', 'null'), ('action', 'null'),
        ('usable_for_elimination', 'req'),
    ),
    'PoolRow': (
        ('strategy_id', 'req'), ('version_id', 'req'), ('period', 'req'),
        ('pool_key', 'req'), ('pool_rank', 'null'),
        ('primary_pool_eligible', 'req'), ('reject_reason', 'null'),
    ),
}
# Flattened view of the three registries. Roster-count note for R4: the task
# checklist reaches "33 model classes" by counting PoolStats twice - once
# inside the [L868] eight intermediate models (AttainmentFrame / NormalizedFrame
# / EvidenceFrame / RedlineFrame / ScoreFrame / GradeFrame / PoolFrame /
# PoolStats) and once again as "+ PoolStats". The number of DISTINCT classes
# ORCH-22 authorises is 32: 6 output + 7 Frame + PoolStats + ScoringContext
# + 10 sub-models + 7 Frame row models. No 33rd model is invented here,
# because ruling 33 closes the surplus whitelist.
ALL_MODELS = {}
for _table in (OUTPUT_MODELS, FRAME_MODELS, SUB_MODELS):
    for _name, _spec in _table.items():
        ALL_MODELS[_name] = _spec

MODEL_NAMES = tuple(sorted(ALL_MODELS))
EXPECTED_FIELDS = {
    name: frozenset(field for field, _kind in spec)
    for name, spec in ALL_MODELS.items()
}
FIELD_KINDS = {
    name: {field: kind for field, kind in spec}
    for name, spec in ALL_MODELS.items()
}

# ---------------------------------------------------------------------------
# One fully populated synthetic payload per model: every declared column gets
# a legal value, so the construction gate also proves that each column accepts
# its contract type. Nested models are plain dicts (pydantic validates them).
# ---------------------------------------------------------------------------
SCORE_CARD_PAYLOAD = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'weight_version_id': WV_ID, 'dict_version': DICT_VERSION,
    'anchor_set_id': ANCHOR_SET_ID, 'run_id': RUN_ID,
    'per_metric': {M_ID: METRIC_CELL}, 'per_dim': {DIM: DIM_CELL},
    'composite_absolute': RATIO, 'composite_relative': RATIO_B,
    'evidence_class': 'B',
    'evidence_reason': RC.EVIDENCE_CARD_MISSING.value,
    'evidence_source': 'CARD_ONLY', 'interpretation_limit': LIMIT_TEXT,
    'redline_pass': True, 'redline_flags': (RC.REDLINE_SOFT_HIT.value,),
    'grade': 'L2', 'grade_reason_codes': (RC.EVIDENCE_CARD_MISSING.value,),
    'capped_flag': False, 'cap_reason': RC.ATTAINMENT_CAPPED.value,
    'ranking_pool': POOL_KEY_ROW, 'rank_in_pool': RANK, 'pool_size': CNT,
    'eligible_for_L1_library': False,
    'l1_gate_reasons': (RC.PRIMARY_POOL_REJECTED_EVIDENCE.value,),
    'stability_label': 'NEAR_BOUNDARY', 'flip_under_pct10': RATIO,
    'flip_under_pct20': RATIO_B, 'usable_for_elimination': False,
    'incremental_value': MINOR, 'incremental_ci_lower': MINOR_B,
    'incremental_ci_upper': MINOR, 'estimator_method': ESTIMATOR_METHOD,
    'value_captured_minor': MINOR,
}
GRADE_LEDGER_PAYLOAD = {
    'strategy_id': S_ID, 'version_id': V_ID, 'period': PERIOD,
    'grade': 'L2', 'previous_grade': 'L3',
    'recommended_action': ACTION_1, 'decided_action': ACTION_2,
    'decision_note': NOTE_TEXT, 'owner_dept': OWNER_DEPT,
    'owner_name': OWNER_NAME, 'deadline': DAY_B,
    'archive_ref': ARCHIVE_REF, 'ledger_complete': True,
    'usable_for_elimination': False,
}
AUDIT_PAYLOAD = {
    'run_id': RUN_ID, 'run_at': RUN_AT, 'period': PERIOD,
    'dsm_version': DSM_VERSION, 'design_version': DESIGN_VERSION,
    'cel_contract_version': CEL_CONTRACT_VERSION,
    'weight_version_id': WV_ID, 'config_snapshot_sha256': SHA_A,
    'input_fingerprints': {TABLE_KEY: FP_ROW},
    'output_fingerprints': {OUT_FILE: SHA_B},
    'sensitivity_schemes': ('OAT_10', 'LOO'), 'seed': SEED,
    'preflight_findings': (PREFLIGHT_ROW,),
    'downgrade_actions': (DOWNGRADE_ROW,), 'exit_code': EXIT_OK,
    'reproducibility_hash': SHA_B,
}
CONTEXT_PAYLOAD = {
    'period': PERIOD, 'run_at': RUN_AT, 'run_id': RUN_ID, 'seed': SEED,
    'weight_version_id': WV_ID, 'evidence_mode': 'GATE_ONLY',
    'cel_enabled': False,
    'input_fingerprints': {TABLE_KEY: FP_ROW},
    'attainment': {'rows': (ATTAINMENT_ROW,),
                   'attainment_coverage': {S_ID: RATIO}},
    'normalized': {'rows': (NORMALIZED_ROW,)},
    'evidence': {'rows': (EVIDENCE_ROW,)},
    'redline': {'rows': (REDLINE_EVAL_ROW,)},
    'score': {'rows': (SCORE_ROW,)},
    'grade': {'rows': (GRADE_ROW,)},
    'pool': {'rows': (POOL_ROW,)},
    'pool_stats': {
        'rows': (POOL_STAT_ROW,),
        'evidence_structure': {'A': CNT_B, 'B': CNT_B, 'C': CNT_B,
                               'D': CNT_B},
        'not_assessed_count': CNT_B,
        'not_assessed_reasons': {REASON_KEY: CNT_B},
    },
}
SYN_PAYLOADS = {
    'ScoreCardRow': SCORE_CARD_PAYLOAD,
    'GradeLedgerRow': GRADE_LEDGER_PAYLOAD,
    'SensitivityReport': {
        'by_scheme': (SCHEME_RESULT,), 'by_strategy': (STRATEGY_SENS,),
        'loo_dominant_metrics': (M_ID,),
        'norm_swap_rank_correlation': RATIO,
        'flags': (RC.LOO_SAMPLED.value,), 'seed': SEED,
        'loo_impact': ((M_ID, RATIO),),
    },
    'EntropyDiagnosticRow': {
        'metric_code': M_ID, 'e_j': RATIO, 'd_j': RATIO_B, 'cv_j': RATIO,
        'vif_j': RATIO_B, 'max_abs_corr': RATIO, 'status': 'OK',
        'suggested_action': RC.RETIRE_OR_REDLINE.value,
        'owner': OWNER_NAME, 'flags': (RC.ENTROPY_UNSTABLE.value,),
    },
    'TriangulationReport': {
        'rows': (TRI_ROW,), 'rho_main_topsis': RATIO,
        'rho_main_gra': RATIO_B, 'rho_topsis_gra': RATIO,
        'mean_rho': RATIO_B, 'agreement': 'METHOD_AGREEMENT',
        'gra_by_metric': {M_ID: RATIO},
        'flags': (RC.TRIANGULATION_DISABLED.value,),
    },
    'AuditBundle': AUDIT_PAYLOAD,
    'AttainmentFrame': {
        'rows': (ATTAINMENT_ROW,),
        'attainment_coverage': {S_ID: RATIO},
    },
    'NormalizedFrame': {
        'rows': (NORMALIZED_ROW,),
        # 两条披露列各给一条合法元素，证明元素类型也能构造（同 e04 的口径）。
        'warnings': (DOWNGRADE_ROW,),
        'excluded': (ATTAINMENT_ROW,),
    },
    'EvidenceFrame': {'rows': (EVIDENCE_ROW,)},
    'RedlineFrame': {'rows': (REDLINE_EVAL_ROW,)},
    'ScoreFrame': {'rows': (SCORE_ROW,)},
    'GradeFrame': {'rows': (GRADE_ROW,)},
    'PoolFrame': {'rows': (POOL_ROW,)},
    'PoolStats': {
        'rows': (POOL_STAT_ROW,),
        'evidence_structure': {'A': CNT_B, 'B': CNT_B, 'C': CNT_B,
                               'D': CNT_B},
        'not_assessed_count': CNT_B,
        'not_assessed_reasons': {REASON_KEY: CNT_B},
    },
    'ScoringContext': CONTEXT_PAYLOAD,
    'InputTableFingerprint': FP_ROW,
    'PreflightFinding': PREFLIGHT_ROW,
    'DowngradeAction': DOWNGRADE_ROW,
    'PoolKey': POOL_KEY_ROW,
    'ScoreCardMetricCell': METRIC_CELL,
    'ScoreCardDimCell': DIM_CELL,
    'SensitivitySchemeResult': SCHEME_RESULT,
    'SensitivityStrategyRow': STRATEGY_SENS,
    'TriangulationStrategyRow': TRI_ROW,
    'PoolStatRow': POOL_STAT_ROW,
    'AttainmentRow': ATTAINMENT_ROW,
    'NormalizedRow': NORMALIZED_ROW,
    'EvidenceRow': EVIDENCE_ROW,
    'RedlineEvalRow': REDLINE_EVAL_ROW,
    'ScoreRow': SCORE_ROW,
    'GradeRow': GRADE_ROW,
    'PoolRow': POOL_ROW,
}


# ---------------------------------------------------------------------------
# Annotation scanners (H-4 [L1265]-[L1267] gate audit, ruling 28 tuple
# discipline, ruling 32 serialisation fitness).
#
# pydantic stores an Annotated[X, gate] in two shapes: nested inside a union or
# a container it keeps its __metadata__ wrapper, while a plain top-level
# Annotated[X, gate] is split into annotation=X plus FieldInfo.metadata. The
# scanner therefore takes the root gate flag separately, so a StrictInt /
# MoneyMinor / MinorUnits / StrictBool column is recognised as gated and a bare
# int / bool / float is reported as an H-4 leak.
# ---------------------------------------------------------------------------
RATIO_NAME_HINTS = (
    'rate', 'ratio', 'share', 'coverage', 'weight', 'rho', 'attainment',
    '_j', 'norm_value', 'flip_under', 'soft_deduction',
)


def _ratio_rule_applies(field_name):
    '''id / code columns are text even when the name carries a ratio hint
    (weight_version_id [L955], metric_code [L1040]), so they sit outside the
    Ratio rule of H-4.'''
    if field_name.endswith('_id') or field_name.endswith('_ids'):
        return False
    return any(hint in field_name for hint in RATIO_NAME_HINTS)


def scan_annotation(annotation, gated=False):
    facts = {
        'float': [], 'int_bare': [], 'int_gated': [], 'bool_bare': [],
        'bool_gated': [], 'decimal': False, 'origins': [], 'models': [],
    }

    def visit(node, is_gated):
        if node is None or node is type(None) or node is Ellipsis:
            return
        if hasattr(node, '__metadata__'):
            visit(get_args(node)[0], True)
            return
        origin = get_origin(node)
        if origin is not None:
            if origin is Literal:
                return
            facts['origins'].append(origin)
            for arg in get_args(node):
                visit(arg, False)
            return
        if isinstance(node, type) and issubclass(node, BaseModel):
            facts['models'].append(node)
            return
        if node is float:
            facts['float'].append(node)
            return
        if node is Decimal:
            facts['decimal'] = True
            return
        if node is int:
            facts['int_gated' if is_gated else 'int_bare'].append(node)
            return
        if node is bool:
            facts['bool_gated' if is_gated else 'bool_bare'].append(node)
            return

    visit(annotation, gated)
    return facts


def scan_field(model_name, field_name):
    field = cls(model_name).model_fields[field_name]
    return scan_annotation(field.annotation, bool(field.metadata))


def field_kind(field):
    ''''req' / 'null' / 'empty', derived the same way as the ruling tables.'''
    if field.is_required():
        return 'req'
    if field.default is None:
        return 'null'
    if isinstance(field.default, (tuple, dict, frozenset, set, bool)):
        return 'empty'
    if field.default_factory is not None:
        return 'empty'
    return 'other'


LEGAL_DEFAULT_TYPES = (type(None), tuple, dict, bool)


# ---------------------------------------------------------------------------
# A. The 32 contract classes exist and are pydantic models.
#    [L867] six output models, [L868] eight intermediate models, ScoringContext
#    (ORCH-13 ruling 1 + ruling 30), 10 sub-models + 7 Frame row models
#    (rulings 15-17, 23-29, 33).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_a01_model_class_exists_and_is_a_pydantic_model(name):
    klass = cls(name)
    assert isinstance(klass, type)
    assert issubclass(klass, BaseModel)


@pytest.mark.parametrize('table_name,expected_size', [
    ('OUTPUT_MODELS', 6), ('FRAME_MODELS', 9), ('SUB_MODELS', 17),
])
def test_a02_registry_sizes_match_the_roster(table_name, expected_size):
    table = {'OUTPUT_MODELS': OUTPUT_MODELS, 'FRAME_MODELS': FRAME_MODELS,
             'SUB_MODELS': SUB_MODELS}[table_name]
    assert len(table) == expected_size
    resolved = [cls(name) for name in table]
    assert len(resolved) == expected_size


def test_a03_registries_are_disjoint_and_complete():
    keys = list(OUTPUT_MODELS) + list(FRAME_MODELS) + list(SUB_MODELS)
    assert len(keys) == len(set(keys))
    assert len(ALL_MODELS) == len(set(keys)) == 32
    assert len([cls(name) for name in ALL_MODELS]) == 32

# ---------------------------------------------------------------------------
# B. The 9 new enum / alias names (ruling 33). Every value set is asserted by
# exact equality in both directions, so one extra or one missing member fails.
# ---------------------------------------------------------------------------
LITERAL_ENUMS = {
    'SchemeName': ('OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP'),  # [L1015]
    'StabilityLabel': ('STABLE', 'NEAR_BOUNDARY', 'UNSTABLE'),     # ORCH-03
    'FrameGrade': ('L1', 'L2', 'L3', 'L4', 'NOT_ASSESSED'),        # [L964]
    'EntropyStatus': ('OK', 'LOW_VARIATION', 'INACTIVE',
                      'COLLINEAR'),                                # [L1040]
    'MethodAgreement': ('METHOD_AGREEMENT',
                        'METHOD_DIVERGENCE'),                       # [L1028]
    'NormalizationMethod': ('min_max', 'z_score',
                            'rank_percentile'),                    # [L940]
    'ScoreOperator': ('LINEAR', 'GEOMETRIC',
                      'NON_COMPENSATORY'),                          # [L953]
    'EvidenceMode': ('GATE_ONLY', 'DISCOUNT'),                     # [L978]
}

LITERAL_CARRIERS = (
    ('SensitivitySchemeResult', 'scheme', 'SchemeName',
     ('OAT_10', 'NORM_SWAP'), 'OAT_5'),
    ('ScoreCardRow', 'stability_label', 'StabilityLabel',
     ('STABLE', 'UNSTABLE'), 'BOUNDARY'),
    ('GradeRow', 'grade', 'FrameGrade',
     ('L4', 'NOT_ASSESSED'), 'L5'),
    ('EntropyDiagnosticRow', 'status', 'EntropyStatus',
     ('INACTIVE', 'COLLINEAR'), 'OK '),
    ('TriangulationReport', 'agreement', 'MethodAgreement',
     ('METHOD_DIVERGENCE',), 'METHOD_PARTIAL'),
    ('NormalizedRow', 'method', 'NormalizationMethod',
     ('z_score', 'rank_percentile'), 'MIN_MAX'),
    ('ScoreRow', 'operator', 'ScoreOperator',
     ('GEOMETRIC', 'NON_COMPENSATORY'), 'linear'),
    ('ScoringContext', 'evidence_mode', 'EvidenceMode',
     ('DISCOUNT',), 'GATE'),
)


@pytest.mark.parametrize('alias_name', sorted(LITERAL_ENUMS))
def test_b01_new_literal_alias_holds_exactly_the_sdd_value_set(alias_name):
    declared_values = _literal_values(alias(alias_name))
    assert declared_values != ()
    assert sorted(declared_values) == sorted(LITERAL_ENUMS[alias_name])


@pytest.mark.parametrize('model_name,field_name,alias_name,legal,illegal',
                         LITERAL_CARRIERS)
def test_b02_carrier_column_accepts_the_legal_values(model_name, field_name,
                                                    alias_name, legal,
                                                    illegal):
    for value in legal:
        built = build(model_name, **{field_name: value})
        assert getattr(built, field_name) == value


@pytest.mark.parametrize('model_name,field_name,alias_name,legal,illegal',
                         LITERAL_CARRIERS)
def test_b03_carrier_column_rejects_values_outside_the_set(model_name,
                                                           field_name,
                                                           alias_name, legal,
                                                           illegal):
    with pytest.raises(ValidationError):
        build(model_name, **{field_name: illegal})


@pytest.mark.parametrize('model_name,field_name,alias_name,legal,illegal',
                         LITERAL_CARRIERS)
def test_b04_carrier_column_reuses_the_alias_value_set(model_name, field_name,
                                                       alias_name, legal,
                                                       illegal):
    from_alias = sorted(_literal_values(alias(alias_name)))
    on_field = sorted(_literal_values(
        cls(model_name).model_fields[field_name].annotation))
    assert on_field == from_alias


def test_b05_input_fingerprints_is_one_open_key_dict_alias():
    '''Ruling 15: dict[str, InputTableFingerprint], keys NOT closed to 8
    ([L877] weights_*.yaml is a wildcard).'''
    ann = alias('InputFingerprints')
    assert get_origin(ann) is dict
    assert _unwrap(get_args(ann)[1]) is cls('InputTableFingerprint')


# ---------------------------------------------------------------------------
# C. The existing GradeCode [L1200] must not be widened to make FrameGrade
# cheap (ruling 20). T7 grade rules would otherwise carry a meaningless row.
# ---------------------------------------------------------------------------
def test_c01_existing_gradecode_stays_at_four_levels():
    assert get_args(models.GradeCode) == ('L1', 'L2', 'L3', 'L4')
    assert 'NOT_ASSESSED' not in get_args(models.GradeCode)


def test_c02_framegrade_is_a_separate_alias_not_a_widened_gradecode():
    assert sorted(_literal_values(alias('FrameGrade'))) == sorted(
        ('L1', 'L2', 'L3', 'L4', 'NOT_ASSESSED'))
    assert _literal_values(alias('FrameGrade')) != get_args(models.GradeCode)


def test_c03_redline_forced_grade_stays_on_gradecode():
    '''Ruling 28: a redline forces L1..L4 ([L989] default L4), never
    NOT_ASSESSED, so forced_grade keeps GradeCode.'''
    forced = _literal_values(
        cls('RedlineEvalRow').model_fields['forced_grade'].annotation)
    assert sorted(forced) == sorted(get_args(models.GradeCode))

# ---------------------------------------------------------------------------
# D. Field-name sets, copied verbatim from ORCH-22 rulings 14-30. The
# parametrized gate below is the strongest single check: a missing column, a
# surplus column and a rename all fail it. The named specials below repeat the
# individual rulings R4 has to see spelled out ([L1630], [L1040], [L1003],
# [L1896], ORCH-15, ruling 22, ruling 28 naming, [L1051]).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_d01_declared_columns_equal_the_ruling_table(name):
    expected = set(EXPECTED_FIELDS[name])
    actual = set(cls(name).model_fields)
    missing = sorted(expected - actual)
    surplus = sorted(actual - expected)
    assert not missing, name + ' is missing contract columns: ' + repr(missing)
    assert not surplus, (
        name + ' declares columns outside the contract: ' + repr(surplus))


FRAME_TO_ROW = {
    'AttainmentFrame': 'AttainmentRow',
    'NormalizedFrame': 'NormalizedRow',
    'EvidenceFrame': 'EvidenceRow',
    'RedlineFrame': 'RedlineEvalRow',
    'ScoreFrame': 'ScoreRow',
    'GradeFrame': 'GradeRow',
    'PoolFrame': 'PoolRow',
    'PoolStats': 'PoolStatRow',
}


@pytest.mark.parametrize('frame_name', sorted(FRAME_TO_ROW))
def test_d02_every_frame_is_row_shaped_over_its_own_row_model(frame_name):
    '''Ruling 28: rows: tuple[<XxxRow>, ...], one row model per Frame.'''
    rows_field = cls(frame_name).model_fields['rows']
    element = _unwrap(get_args(rows_field.annotation)[0])
    assert element is cls(FRAME_TO_ROW[frame_name])


def test_d03_grade_ledger_splits_recommended_from_decided_action():
    '''[L1630] + V-8 [L1863]: two independent columns, the model only advises,
    a human decides and signs. Collapsing them into one column fails V-8.'''
    fields = cls('GradeLedgerRow').model_fields
    assert 'recommended_action' in fields
    assert 'decided_action' in fields
    assert fields['recommended_action'] is not fields['decided_action']
    assert _nullable_scalar(fields['recommended_action'].annotation) is str
    assert _nullable_scalar(fields['decided_action'].annotation) is str
    assert fields['recommended_action'].annotation is not None
    assert 'action' not in fields


def test_d04_grade_ledger_keeps_the_decision_note_column():
    '''[L1630]: a disagreement between the two actions must be explainable,
    so decision_note exists as its own nullable column.'''
    fields = cls('GradeLedgerRow').model_fields
    assert 'decision_note' in fields
    assert not fields['decision_note'].is_required()


def test_d05_entropy_diagnostic_names_metric_code_not_metric_id():
    '''ORCH-22 section 0 item 3 + [L1040]: the SDD writes metric_code here and
    metric_id everywhere else; ORCH-16 ruling 1 forbids "beautifying" it.'''
    fields = declared('EntropyDiagnosticRow')
    assert 'metric_code' in fields
    assert 'metric_id' not in fields
    assert 'flags' in fields


def test_d06_pool_stat_row_reports_both_shares():
    '''[L1003] forbids reporting the merged share alone, [L1006] requires the
    double report, so both columns must coexist (B-020 covers the denominator
    semantics, not the column).'''
    fields = declared('PoolStatRow')
    assert {'share_in_pool', 'share_overall'} <= fields


def test_d07_score_card_carries_evidence_source():
    '''ORCH-15: evidence_source belongs to S1-T04, [L870] / [L980].'''
    assert 'evidence_source' in declared('ScoreCardRow')
    assert 'evidence_source' in declared('EvidenceRow')


def test_d08_cel0_value_captured_takes_the_minor_suffix():
    '''Ruling 22: value_captured is a pure money column, so H-4 requires the
    _minor suffix; the verbatim name must be gone.'''
    fields = declared('ScoreCardRow')
    assert 'value_captured_minor' in fields
    assert 'value_captured' not in fields


@pytest.mark.parametrize('verbatim', [
    'incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
    'estimator_method',
])
def test_d09_cel0_incremental_columns_keep_their_verbatim_names(verbatim):
    '''Ruling 22: unit-polymorphic columns keep the SDD name, no _minor.'''
    fields = declared('ScoreCardRow')
    assert verbatim in fields
    assert verbatim + '_minor' not in fields


def test_d10_score_card_column_count_matches_the_ruling_table():
    fields = cls('ScoreCardRow').model_fields
    assert len(fields) == len(EXPECTED_FIELDS['ScoreCardRow'])


def test_d11_redline_frame_row_model_is_not_the_input_redline_row():
    '''Ruling 28 warning: RedlineRow is taken by the T5 input table ([L866]),
    so the RedlineFrame row model is RedlineEvalRow ([L988] evaluate).'''
    assert cls('RedlineFrame').model_fields['rows'] is not None
    assert model_in(cls('RedlineFrame').model_fields['rows'].annotation) \
        is cls('RedlineEvalRow')
    assert cls('RedlineRow') is not cls('RedlineEvalRow')


def test_d12_audit_bundle_maps_the_15_verbatim_items_onto_16_columns():
    '''Ruling 14: [L1051] enumerates 15 items, item 11 splits into
    sensitivity_schemes + seed.'''
    items_to_columns = {
        'run_id': ('run_id',),
        'run_at': ('run_at',),
        'period': ('period',),
        'dsm_version': ('dsm_version',),
        'design_version': ('design_version',),
        'cel_contract_version': ('cel_contract_version',),
        'weight_version_id': ('weight_version_id',),
        'config_sha256': ('config_snapshot_sha256',),
        'input_tables_sha256_and_rows': ('input_fingerprints',),
        'output_files_sha256': ('output_fingerprints',),
        'schemes_and_seed': ('sensitivity_schemes', 'seed'),
        'preflight_findings': ('preflight_findings',),
        'downgrade_actions': ('downgrade_actions',),
        'exit_code': ('exit_code',),
        'reproducibility_hash': ('reproducibility_hash',),
    }
    assert len(items_to_columns) == 15
    columns = [col for group in items_to_columns.values() for col in group]
    assert len(columns) == 16
    assert set(columns) == declared('AuditBundle')


def test_d13_grade_reason_column_names_stay_divergent_as_the_sdd_is():
    '''ORCH-16 ruling 1 + ruling 21: [L1620] writes grade_reason_codes, [L964]
    writes grade_reason_path; neither is renamed to match the other.'''
    assert 'grade_reason_codes' in declared('ScoreCardRow')
    assert 'grade_reason_path' in declared('GradeRow')
    assert 'grade_reason_codes' not in declared('GradeRow')
    assert 'grade_reason_path' not in declared('ScoreCardRow')

def _nullable_scalar(annotation):
    '''str | None -> str, X | None -> X, a bare X comes back unchanged. Used by
    the nullable-column specials above.'''
    inner = _unwrap(annotation)
    args = [arg for arg in get_args(inner) if arg is not type(None)]
    if not args:
        return inner
    return _unwrap(args[0])


# ---------------------------------------------------------------------------
# E. V-5 [L871] / [L865]: frozen + extra=forbid on all 32 models, and an
# undeclared column must raise instead of being dropped. Ruling 5 item 1 also
# demands the config to match the existing _InputRow verbatim.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_e01_model_config_is_frozen_and_extra_forbid(name):
    conf = cls(name).model_config
    assert conf.get('frozen') is True
    assert conf.get('extra') == 'forbid'


def test_e02_new_config_matches_the_existing_input_row_base():
    base = models._InputRow.model_config
    for name in MODEL_NAMES:
        conf = cls(name).model_config
        assert conf.get('frozen') == base.get('frozen')
        assert conf.get('extra') == base.get('extra')


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_e03_undeclared_column_is_rejected(name):
    with pytest.raises(ValidationError):
        build(name, **{UNDECLARED_COLUMN: 'SYN'})


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_e04_every_model_builds_from_its_synthetic_payload(name):
    '''Every declared column accepts a legal synthetic value, and the built
    instance exposes exactly the contract columns.'''
    built = build(name)
    assert isinstance(built, cls(name))
    assert set(type(built).model_fields) == set(EXPECTED_FIELDS[name])


# ---------------------------------------------------------------------------
# F. frozen really means immutable ([L865]).
# ---------------------------------------------------------------------------
IMMUTABLE_PROBES = (
    ('ScoreCardRow', 'composite_absolute', RATIO_B),
    ('AuditBundle', 'exit_code', CNT_B),
    ('ScoringContext', 'evidence_mode', 'DISCOUNT'),
    ('NormalizedRow', 'anchor_used', False),
    ('PoolStats', 'not_assessed_count', CNT_C),
    ('GradeLedgerRow', 'ledger_complete', False),
)


@pytest.mark.parametrize('model_name,field_name,replacement', IMMUTABLE_PROBES)
def test_f01_frozen_instance_refuses_reassignment(model_name, field_name,
                                                  replacement):
    built = build(model_name)
    with pytest.raises(ValidationError):
        setattr(built, field_name, replacement)


# ---------------------------------------------------------------------------
# G. H-4 [L1265]-[L1267] / [L1272]: annotation-level and behaviour-level
# numeric gates over all 32 models.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_g01_no_bare_float_int_or_bool_column_anywhere(name):
    '''float is never a contract type; int columns go through StrictInt /
    MoneyMinor / MinorUnits; bool columns go through StrictBool (ORCH-17/18).'''
    leaks = []
    fields = cls(name).model_fields
    for field_name in sorted(fields):
        facts = scan_annotation(fields[field_name].annotation,
                                bool(fields[field_name].metadata))
        if facts['float']:
            leaks.append((field_name, 'float'))
        if facts['int_bare']:
            leaks.append((field_name, 'bare int'))
        if facts['bool_bare']:
            leaks.append((field_name, 'bare bool'))
    assert not leaks, name + ' breaks H-4: ' + repr(leaks)


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_g02_ratio_shaped_columns_are_decimal_gated(name):
    '''Every rate / ratio / share / coverage / weight / rho / attainment /
    e_j-style / norm_value / flip_under / soft_deduction column must carry
    Decimal (the Ratio gate), so no ratio ever bypasses numeric.D.'''
    offenders = []
    fields = cls(name).model_fields
    for field_name in sorted(fields):
        if not _ratio_rule_applies(field_name):
            continue
        facts = scan_annotation(fields[field_name].annotation,
                                bool(fields[field_name].metadata))
        if facts['models']:
            continue
        if not facts['decimal']:
            offenders.append(field_name)
    assert not offenders, (
        name + ' ratio-shaped columns without Decimal: ' + repr(offenders))


@pytest.mark.parametrize('probe', [1.0, '1', True, Decimal('1'), b'1'])
def test_g03_audit_exit_code_rejects_every_lax_int_form(probe):
    '''StrictInt gate, [L1080]-[L1087] exit_code.'''
    with pytest.raises(ValidationError):
        build('AuditBundle', exit_code=probe)


@pytest.mark.parametrize('probe', [0.5, True, 'x', b'0.5'])
def test_g04_composite_absolute_rejects_float_and_bool(probe):
    with pytest.raises(ValidationError):
        build('ScoreCardRow', composite_absolute=probe)


def test_g05_composite_absolute_lands_on_decimal():
    built = build('ScoreCardRow', composite_absolute=Decimal('0.5'))
    assert isinstance(built.composite_absolute, Decimal)
    assert built.composite_absolute == Decimal('0.5')


@pytest.mark.parametrize('probe', [Decimal('3'), '3', 3.0, True])
def test_g06_pool_stat_count_rejects_lax_int_forms(probe):
    '''[L1006] counts are int, [L1266] makes them exact.'''
    with pytest.raises(ValidationError):
        build('PoolStatRow', count=probe)


@pytest.mark.parametrize('probe', [1.5, 'SYN', True])
def test_g07_money_column_rejects_fractional_and_text_amounts(probe):
    '''value_captured_minor is a pure money column (ruling 22), so a fractional
    or textual amount is a contract violation, not a coercion.'''
    with pytest.raises(ValidationError):
        build('ScoreCardRow', value_captured_minor=probe)


@pytest.mark.parametrize('probe', [1, 0, 'true', 'yes', Decimal('1')])
def test_g08_strict_bool_columns_reject_lax_bool_forms(probe):
    with pytest.raises(ValidationError):
        build('AttainmentRow', has_target=probe)

# ---------------------------------------------------------------------------
# H. H-6 / H-7: every reason_code column goes through the ReasonCode gate, i.e.
# it must resolve in dsm.reason_codes. Bare strings are refused at construction
# (no silent degradation, V-14). str(RC.X) is 'RC.X', NOT the code, so that form
# has to be refused as well; the RC member itself is accepted (it carries
# .value).
# ---------------------------------------------------------------------------
REASON_COLUMNS = (
    ('DowngradeAction', 'reason_code', RC.WEIGHT_REALLOCATED.value),
    ('AttainmentRow', 'reason_code', RC.NO_TARGET_VALUE.value),
    ('NormalizedRow', 'reason_code', RC.SMALL_POOL.value),
    ('RedlineEvalRow', 'reason_code', RC.REDLINE_SOFT_HIT.value),
    ('EvidenceRow', 'evidence_reason', RC.EVIDENCE_CARD_MISSING.value),
    ('ScoreCardRow', 'cap_reason', RC.ATTAINMENT_CAPPED.value),
    ('ScoreCardRow', 'evidence_reason', RC.EVIDENCE_C_NO_LIMIT.value),
    ('GradeRow', 'cap_reason', RC.ATTAINMENT_CAPPED.value),
    ('PoolRow', 'reject_reason', RC.POOL_TOO_SMALL.value),
    ('EntropyDiagnosticRow', 'suggested_action', RC.RETIRE_OR_REDLINE.value),
    ('SensitivitySchemeResult', 'flag', RC.FLIP_RATE_UNUSABLE.value),
)

REASON_SEQUENCE_COLUMNS = (
    ('GradeRow', 'grade_reason_path', (RC.NOT_ASSESSED.value,)),
    ('ScoreCardRow', 'grade_reason_codes', (RC.NOT_ASSESSED.value,)),
    ('ScoreCardRow', 'redline_flags', (RC.REDLINE_HARD_HIT.value,)),
    ('ScoreCardRow', 'l1_gate_reasons',
     (RC.PRIMARY_POOL_REJECTED_ROBUST.value,)),
    ('SensitivityReport', 'flags', (RC.LOO_SAMPLED.value,)),
    ('TriangulationReport', 'flags', (RC.TRIANGULATION_DISABLED.value,)),
    ('EntropyDiagnosticRow', 'flags', (RC.ENTROPY_UNSTABLE.value,)),
)


@pytest.mark.parametrize('model_name,field_name,good', REASON_COLUMNS)
def test_h01_registered_reason_code_is_accepted(model_name, field_name, good):
    built = build(model_name, **{field_name: good})
    assert getattr(built, field_name) == good


@pytest.mark.parametrize('model_name,field_name,good', REASON_COLUMNS)
def test_h02_bare_unregistered_string_is_refused(model_name, field_name, good):
    with pytest.raises(ValidationError):
        build(model_name, **{field_name: UNREGISTERED})


@pytest.mark.parametrize('model_name,field_name,good',
                         REASON_SEQUENCE_COLUMNS)
def test_h03_reason_code_sequence_accepts_registered_codes(model_name,
                                                            field_name, good):
    built = build(model_name, **{field_name: good})
    assert tuple(getattr(built, field_name)) == good


@pytest.mark.parametrize('model_name,field_name,good',
                         REASON_SEQUENCE_COLUMNS)
def test_h04_reason_code_sequence_refuses_an_unregistered_member(model_name,
                                                                 field_name,
                                                                 good):
    with pytest.raises(ValidationError):
        build(model_name, **{field_name: (good[0], UNREGISTERED)})


def test_h05_the_str_form_of_an_rc_member_is_not_a_registered_code():
    '''str(RC.NOT_ASSESSED) == 'RC.NOT_ASSESSED' - the pitfall. Only the code
    itself registers, so the prefixed spelling must be rejected, not silently
    accepted as a code.'''
    with pytest.raises(ValidationError):
        build('GradeRow', grade_reason_path=(str(RC.NOT_ASSESSED),))
    with pytest.raises(ValidationError):
        build('AttainmentRow', reason_code=str(RC.NO_TARGET_VALUE))


@pytest.mark.parametrize('model_name,field_name,member', [
    ('AttainmentRow', 'reason_code', RC.NEGATIVE_ACTUAL),
    ('PoolRow', 'reject_reason', RC.PRIMARY_POOL_REJECTED_EVIDENCE),
])
def test_h06_an_rc_member_lands_on_its_registered_code_value(model_name,
                                                             field_name,
                                                             member):
    built = build(model_name, **{field_name: member})
    assert getattr(built, field_name) == member.value


def test_h07_downgrade_action_reason_code_is_mandatory():
    '''H-6: a downgrade without a reason_code cannot be recorded, so the column
    is required (ruling 17).'''
    payload = dict(DOWNGRADE_ROW)
    del payload['reason_code']
    with pytest.raises(ValidationError):
        cls('DowngradeAction')(**payload)


def test_h08_flags_column_carries_the_b018_marker_next_to_a_closed_status():
    '''Ruling 27: ENTROPY_UNSTABLE is stackable, so it lands in flags while
    status keeps one of the four closed values.'''
    built = build('EntropyDiagnosticRow', status='INACTIVE',
                  flags=(RC.ENTROPY_UNSTABLE.value,))
    assert built.status == 'INACTIVE'
    assert RC.ENTROPY_UNSTABLE.value in tuple(built.flags)


# ---------------------------------------------------------------------------
# I. Ruling 27 closure, the single most error-prone point of this contract:
# status is a closed 4-value Literal; ENTROPY_UNSTABLE must NOT be added to it.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('legal', ('OK', 'LOW_VARIATION', 'INACTIVE',
                                   'COLLINEAR'))
def test_i01_entropy_status_accepts_the_four_closed_values(legal):
    built = build('EntropyDiagnosticRow', status=legal)
    assert built.status == legal


def test_i02_entropy_unstable_is_not_a_status_value():
    with pytest.raises(ValidationError):
        build('EntropyDiagnosticRow', status='ENTROPY_UNSTABLE')

# ---------------------------------------------------------------------------
# J. H-5 / nullability. No default may smuggle a business number, and the
# req / null / empty partition has to equal the ruling tables ([L1053] item 5
# separates None from '', and an empty container is () or {}, never None).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_j01_no_field_default_is_a_business_number(name):
    fields = cls(name).model_fields
    offenders = []
    for field_name in sorted(fields):
        field = fields[field_name]
        if field.is_required():
            continue
        if field.default_factory is not None:
            if field.default_factory not in (tuple, dict):
                offenders.append((field_name, field.default_factory))
            continue
        default = field.default
        if type(default) not in LEGAL_DEFAULT_TYPES:
            offenders.append((field_name, default))
        elif isinstance(default, bool) and default is True:
            offenders.append((field_name, True))
    assert not offenders, (
        name + ' carries a default outside None / () / {} / False: '
        + repr(offenders))


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_j02_nullability_partition_matches_the_ruling_table(name):
    fields = cls(name).model_fields
    expected = FIELD_KINDS[name]
    mismatches = []
    for field_name in sorted(expected):
        if field_name not in fields:
            mismatches.append((field_name, 'absent'))
            continue
        actual = field_kind(fields[field_name])
        if actual != expected[field_name]:
            mismatches.append((field_name, expected[field_name], actual))
    assert not mismatches, (
        name + ' nullability differs from ORCH-22: ' + repr(mismatches))


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_j03_nullable_columns_accept_an_explicit_none(name):
    fields = cls(name).model_fields
    for field_name in sorted(FIELD_KINDS[name]):
        if FIELD_KINDS[name][field_name] != 'null':
            continue
        built = build(name, **{field_name: None})
        assert getattr(built, field_name) is None


def test_j04_nullable_columns_never_default_to_the_empty_string():
    '''[L1053] item 5: null and empty are strictly different, so an 'empty'
    marker must never be spelled as ''.'''
    for name in MODEL_NAMES:
        fields = cls(name).model_fields
        for field_name in sorted(fields):
            assert fields[field_name].default != '', (
                name + '.' + field_name + ' uses an empty string as empty')


def test_j05_audit_bundle_has_exactly_one_nullable_column():
    '''Ruling 14: 15 items are mandatory, only seed may be absent ([L1270]
    "no seed" is a legal state, it only forbids MC).'''
    fields = cls('AuditBundle').model_fields
    nullable = sorted(n for n in fields if not fields[n].is_required())
    assert nullable == ['seed']
    assert fields['seed'].default is None


def test_j06_scoring_context_cel_enabled_has_no_default():
    '''Ruling 30: the default (false, [L1898]) belongs to the config layer, so
    the contract column is required without a default (H-5).'''
    field = cls('ScoringContext').model_fields['cel_enabled']
    assert field.is_required()


def test_j07_grade_ledger_advice_and_signoff_columns_are_all_nullable():
    '''Ruling 24: forcing them would make the model invent wording (H-5),
    which [L1631] reserves for volume A chapter 3 (seven).'''
    fields = cls('GradeLedgerRow').model_fields
    for field_name in ('recommended_action', 'decided_action',
                       'decision_note', 'owner_dept', 'owner_name',
                       'deadline', 'archive_ref', 'previous_grade'):
        assert field_name in fields
        assert not fields[field_name].is_required(), field_name
        assert fields[field_name].default is None, field_name


def test_j08_score_card_main_and_aux_scores_stay_nullable():
    '''Rulings 21 / 9 of ORCH-21: NOT_ASSESSED ([L964]) means "no score at
    all", so a mandatory score column would force a fabricated number.'''
    fields = cls('ScoreCardRow').model_fields
    for field_name in ('composite_absolute', 'composite_relative',
                       'ranking_pool', 'rank_in_pool', 'pool_size',
                       'stability_label', 'cap_reason'):
        assert not fields[field_name].is_required(), field_name


def test_j09_empty_columns_default_to_an_empty_container_not_none():
    '''Ruling 32 item 3: a redline_flags column with no hit is (), not None.'''
    field = cls('ScoreCardRow').model_fields['redline_flags']
    assert not field.is_required()
    empty = field.default if field.default_factory is None else (
        field.default_factory())
    assert empty == ()


# ---------------------------------------------------------------------------
# K / L. H-8 and H-9 are properties of the source text, guarded by AST.
# ---------------------------------------------------------------------------
WALL_CLOCK_PATHS = (
    'datetime.now', 'datetime.utcnow', 'date.today', 'time.time',
    'time.localtime', 'time.gmtime', 'time.monotonic', 'time.time_ns',
)


def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return base + '.' + node.attr if base else node.attr
    return ''


def _imported_names(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias_.name for alias_ in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            found += [module + '.' + alias_.name for alias_ in node.names]
    return found


def _models_tree():
    return ast.parse(MODELS_PATH.read_text(encoding='utf-8'))


def test_k01_models_layer_reads_no_wall_clock():
    '''[L1271] + H-8: run_at / period / seed are injected ([L1089]), the
    contract layer never asks the OS for the time.'''
    tree = _models_tree()
    calls = [_dotted(node.func) for node in ast.walk(tree)
             if isinstance(node, ast.Call)]
    offenders = [path for path in calls if path in WALL_CLOCK_PATHS]
    offenders += [path for path in calls
                  if path.endswith(('.now', '.utcnow', '.today', '.time'))]
    assert not offenders, 'wall-clock read in models.py: ' + repr(offenders)


@pytest.mark.parametrize('forbidden_module', [
    'weights_ahp', 'weights_combine', 'fixtures_gen', 'weights_calibrate',
    'whatif', 'diagnostics',
])
def test_l01_models_layer_does_not_import_l0_modules(forbidden_module):
    '''H-9 INV-1 / INV-3: L1 may import L1 only.'''
    imports = _imported_names(_models_tree())
    offenders = [name for name in imports
                 if name.split('.')[-1] == forbidden_module]
    assert not offenders, (
        'dsm/models.py imports ' + forbidden_module + ': ' + repr(offenders))


def test_l02_models_layer_reaches_no_dsm_module_above_l1():
    L1_PEERS = ('numeric', 'reason_codes')
    offenders = []
    for node in ast.walk(_models_tree()):
        if isinstance(node, ast.ImportFrom) and node.module == 'dsm':
            offenders += ['dsm.' + a.name for a in node.names
                          if a.name not in L1_PEERS]
        elif isinstance(node, ast.ImportFrom) and (node.module or '').startswith('dsm.'):
            parts = node.module.split('.')
            if parts[1] not in L1_PEERS:
                offenders.append(node.module)
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith('dsm.'):
                    if a.name.split('.')[1] not in L1_PEERS:
                        offenders.append(a.name)
    assert not offenders, (
        'L1 importing above its layer: ' + repr(sorted(set(offenders))))

# ---------------------------------------------------------------------------
# M. Ruling 28 item 3: ordered sequences are tuple, maps are dict. A set /
# frozenset annotation would make the [L1052] reproducibility_hash depend on
# PYTHONHASHSEED, which breaks V-3 ("the second person re-runs it identically").
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', MODEL_NAMES)
def test_m01_no_set_or_frozenset_annotation(name):
    fields = cls(name).model_fields
    offenders = []
    for field_name in sorted(fields):
        facts = scan_annotation(fields[field_name].annotation,
                                bool(fields[field_name].metadata))
        for origin in facts['origins']:
            if origin in (set, frozenset):
                offenders.append((field_name, origin))
    assert not offenders, name + ' uses set/frozenset: ' + repr(offenders)


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_m02_sequence_columns_are_tuples_not_lists(name):
    '''[L1053] items 3/4 demand a stable traversal order; a frozen contract
    layer therefore exposes tuples (lists would also break frozen-ness when a
    row model is reused as a value).'''
    fields = cls(name).model_fields
    offenders = []
    for field_name in sorted(fields):
        facts = scan_annotation(fields[field_name].annotation,
                                bool(fields[field_name].metadata))
        for origin in facts['origins']:
            if origin is list:
                offenders.append(field_name)
    assert not offenders, name + ' uses list columns: ' + repr(offenders)


# ---------------------------------------------------------------------------
# N. Ruling 5 item 8: the registries and models.__all__ cover each other, so a
# later task cannot add a model without registering it (the S1-T02 R4 followup,
# institutionalised here).
# ---------------------------------------------------------------------------
PREEXISTING_MODELS = (
    'AhpSegment', 'AlphaBasisSegment', 'AnchorSetDoc', 'CombineSegment',
    'DesignCardRow', 'EntropySegment', 'GradeRuleRow', 'MetricDictRow',
    'MetricFactRow', 'MetricWeightComparison', 'RedlineRow',
    'StrategyMasterRow', 'WeightProvenance', 'WeightVersionDoc',
)


def test_n01_every_public_model_class_is_registered_in_this_file():
    registered = set(ALL_MODELS) | set(PREEXISTING_MODELS)
    strays = []
    for public_name in models.__all__:
        obj = getattr(models, public_name)
        if isinstance(obj, type) and issubclass(obj, BaseModel):
            if public_name not in registered:
                strays.append(public_name)
    assert not strays, (
        'model class in dsm.models.__all__ missing from OUTPUT_MODELS / '
        'FRAME_MODELS / SUB_MODELS: ' + repr(sorted(strays)))


@pytest.mark.parametrize('name', MODEL_NAMES)
def test_n02_every_registered_class_is_public_in_dunder_all(name):
    assert cls(name).__name__ in models.__all__


def test_n03_the_three_registries_partition_the_contract():
    assert len(OUTPUT_MODELS) + len(FRAME_MODELS) + len(SUB_MODELS) == 32
    assert len(EXPECTED_FIELDS) == 32
    assert [cls(name) for name in MODEL_NAMES]


# ---------------------------------------------------------------------------
# O. Ruling 29 / ruling 15: PoolKey and InputFingerprints are single shared
# definitions, not a private copy per model.
# ---------------------------------------------------------------------------
POOL_KEY_HOLDERS = (
    ('NormalizedRow', 'pool_key'),
    ('PoolRow', 'pool_key'),
    ('PoolStatRow', 'pool_key'),
    ('ScoreCardRow', 'ranking_pool'),
)


def test_o01_pool_key_is_one_shared_class():
    '''[L1001] pool_key = (biz_domain, evidence_class); ruling 29 forbids
    re-inventing it per model.'''
    shared = cls('PoolKey')
    for model_name, field_name in POOL_KEY_HOLDERS:
        field = cls(model_name).model_fields[field_name]
        assert model_in(field.annotation) is shared, (
            model_name + '.' + field_name + ' does not reuse PoolKey')


def test_o02_pool_key_carries_exactly_the_two_pooling_dimensions():
    fields = cls('PoolKey').model_fields
    assert sorted(fields) == ['biz_domain', 'evidence_class']
    assert _unwrap(fields['evidence_class'].annotation) is not None


def test_o03_input_fingerprints_alias_is_shared_by_audit_and_context():
    '''Ruling 15: AuditBundle item 9 and the ScoringContext A group are the
    SAME alias instance, keys open ([L877] weights_*.yaml).'''
    declared_alias = alias('InputFingerprints')
    holders = (('AuditBundle', 'input_fingerprints'),
               ('ScoringContext', 'input_fingerprints'))
    for model_name, field_name in holders:
        field = cls(model_name).model_fields[field_name]
        assert get_origin(field.annotation) is dict, (
            model_name + '.' + field_name + ' is not InputFingerprints')
        assert get_args(field.annotation) == get_args(declared_alias)


# ---------------------------------------------------------------------------
# P. Ruling 30: the ScoringContext A group is the run context (8 columns,
# run_id added, run_at is a datetime), the B group is the 8 intermediate
# models themselves (16 columns in total).
# ---------------------------------------------------------------------------
CONTEXT_B_GROUP = (
    ('attainment', 'AttainmentFrame'),
    ('normalized', 'NormalizedFrame'),
    ('evidence', 'EvidenceFrame'),
    ('redline', 'RedlineFrame'),
    ('score', 'ScoreFrame'),
    ('grade', 'GradeFrame'),
    ('pool', 'PoolFrame'),
    ('pool_stats', 'PoolStats'),
)


@pytest.mark.parametrize('field_name,class_name', CONTEXT_B_GROUP)
def test_p01_b_group_column_is_the_frame_class_itself(field_name, class_name):
    '''[L1016] Step 1-4 results are reused across schemes; the column type is
    the Frame model, not a copy of its rows.'''
    field = cls('ScoringContext').model_fields[field_name]
    assert model_in(field.annotation) is cls(class_name)


def test_p02_a_group_scalars_have_the_ruled_types():
    fields = cls('ScoringContext').model_fields
    assert _nullable_scalar(fields['run_at'].annotation) is datetime
    for name in ('period', 'run_id', 'weight_version_id'):
        assert _nullable_scalar(fields[name].annotation) is str, name
    seed_facts = scan_annotation(fields['seed'].annotation,
                                 bool(fields['seed'].metadata))
    assert not fields['seed'].is_required()
    assert seed_facts['int_bare'] == []
    assert seed_facts['int_gated']
    cel_facts = scan_annotation(fields['cel_enabled'].annotation,
                                bool(fields['cel_enabled'].metadata))
    assert cel_facts['bool_bare'] == []
    assert cel_facts['bool_gated']


def test_p03_scoring_context_has_sixteen_columns_in_two_groups():
    fields = cls('ScoringContext').model_fields
    assert len(fields) == 16 == len(EXPECTED_FIELDS['ScoringContext'])
    a_group = ('period', 'run_at', 'run_id', 'seed', 'weight_version_id',
               'evidence_mode', 'cel_enabled', 'input_fingerprints')
    b_group = tuple(name for name, _cls in CONTEXT_B_GROUP)
    assert sorted(fields) == sorted(a_group + b_group)

# ---------------------------------------------------------------------------
# Q. Container shapes and the remaining ruling-level specifics that the
# traversals above cannot express as a per-model rule.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('frame_name', sorted(FRAME_TO_ROW))
def test_q01_frame_rows_column_is_a_tuple_sequence(frame_name):
    '''Ruling 28 / ruling 32 item 2: rows: tuple[<Row>, ...].'''
    annotation = cls(frame_name).model_fields['rows'].annotation
    assert get_origin(_unwrap(annotation)) is tuple


def test_q02_attainment_coverage_is_a_decimal_map():
    '''[L928] per-strategy attainment_coverage = covered / signed-off metric
    count; the numerator/denominator semantics live in attainment.py (S4).'''
    field = cls('AttainmentFrame').model_fields['attainment_coverage']
    annotation = _unwrap(field.annotation)
    assert get_origin(annotation) is dict
    facts = scan_annotation(annotation, bool(field.metadata))
    assert facts['decimal']
    assert facts['float'] == []


def test_q03_evidence_structure_keys_stay_the_closed_four():
    '''Ruling 28 (PoolStats): A/B/C/D is an SDD-given closed key set ([L1003]),
    unlike the open InputFingerprints keys (ruling 15).'''
    field = cls('PoolStats').model_fields['evidence_structure']
    annotation = _unwrap(field.annotation)
    assert get_origin(annotation) is dict
    key_ann, value_ann = get_args(annotation)
    assert sorted(_literal_values(key_ann)) == ['A', 'B', 'C', 'D']
    facts = scan_annotation(value_ann)
    assert facts['int_bare'] == []


def test_q04_not_assessed_reasons_count_by_reason():
    '''[L1004]: NOT_ASSESSED is counted separately, with the reason
    distribution spelled out, counts as int.'''
    fields = cls('PoolStats').model_fields
    assert 'not_assessed_count' in fields and 'not_assessed_reasons' in fields
    reasons = _unwrap(fields['not_assessed_reasons'].annotation)
    assert get_origin(reasons) is dict
    facts = scan_annotation(reasons, bool(fields['not_assessed_reasons'].metadata))
    assert facts['int_bare'] == []
    assert facts['decimal'] is False


def test_q05_sha256_columns_are_plain_strings_at_the_contract_layer():
    '''Ruling 14: no 64-hex format validator here, that belongs to audit.py
    (S6); inventing one would add a constraint the SDD never states.'''
    built = build('AuditBundle', config_snapshot_sha256=SHA_A,
                  reproducibility_hash=SHA_B)
    assert built.config_snapshot_sha256 == SHA_A
    assert isinstance(built.reproducibility_hash, str)


def test_q06_cel0_columns_default_to_none_not_to_zero():
    '''[L1626] + ruling 21: the first version leaves all five CEL-0 columns
    empty; a zero default would read as a measured value (H-5).'''
    fields = cls('ScoreCardRow').model_fields
    for field_name in ('incremental_value', 'incremental_ci_lower',
                       'incremental_ci_upper', 'estimator_method',
                       'value_captured_minor'):
        assert not fields[field_name].is_required(), field_name
        assert fields[field_name].default is None, field_name


def test_q07_scored_and_ledged_grains_keep_the_locator_keys():
    '''[L1149] four-part locator; [L1220] / [L1221] grains drop metric_id only
    because the metric dimension lives in per_metric.'''
    for name in ('ScoreCardRow', 'GradeLedgerRow', 'AttainmentRow',
                 'NormalizedRow', 'RedlineEvalRow', 'ScoreRow', 'GradeRow',
                 'PoolRow'):
        fields = declared(name)
        assert 'strategy_id' in fields and 'version_id' in fields, name
        assert 'period' in fields, name
    for name in ('AttainmentRow', 'NormalizedRow', 'RedlineEvalRow'):
        assert 'metric_id' in declared(name), name
    assert 'metric_id' not in declared('ScoreCardRow')
    assert 'metric_id' not in declared('GradeLedgerRow')


def test_q08_evidence_row_and_score_card_share_the_evidence_triple():
    '''[L980] / [L1617]: class, reason and source are the same three concepts
    on both levels, spelled identically.'''
    row = declared('EvidenceRow')
    card = declared('ScoreCardRow')
    for field_name in ('evidence_class', 'evidence_reason',
                       'evidence_source'):
        assert field_name in row and field_name in card, field_name

# ---------------------------------------------------------------------------
# R. Self-checks of this file's own tables and scanners. They touch no
# unimplemented attribute, so they pass at HEAD; their job is to let R2 / R4
# tell "the expectation is wrong" apart from "the contract is missing", and to
# prove the H-4 scanner really recognises the gates that already landed.
# ---------------------------------------------------------------------------
def test_r01_payload_table_covers_every_registered_model():
    assert len(MODEL_NAMES) == 32
    assert set(SYN_PAYLOADS) == set(MODEL_NAMES)


def test_r02_every_payload_matches_its_expected_column_set():
    offenders = []
    for name in MODEL_NAMES:
        if set(SYN_PAYLOADS[name]) != set(EXPECTED_FIELDS[name]):
            offenders.append(name)
    assert not offenders, 'payload/column-table drift: ' + repr(offenders)


def test_r03_kind_partition_covers_every_expected_column():
    offenders = []
    for name in MODEL_NAMES:
        if set(FIELD_KINDS[name]) != set(EXPECTED_FIELDS[name]):
            offenders.append(name)
        for field_name, kind in sorted(FIELD_KINDS[name].items()):
            if kind not in ('req', 'null', 'empty'):
                offenders.append((name, field_name, kind))
    assert not offenders, 'nullability table drift: ' + repr(offenders)


def test_r04_scanner_recognises_the_gates_that_already_landed():
    '''Positive controls: StrictInt, StrictBool inside an Optional, MoneyMinor
    / Ratio inside a union and the MinorUnits | Ratio column all read as gated
    and decimal-bearing, so a RED from the G traversal is never a scanner
    artefact.'''
    facts = scan_field('GradeRuleRow', 'promotion_streak')
    assert facts['int_gated'] and not facts['int_bare']
    facts = scan_field('DesignCardRow', 'mde_ok')
    assert facts['bool_gated'] and not facts['bool_bare']
    facts = scan_field('MetricFactRow', 'value')
    assert facts['decimal'] and not facts['float'] and not facts['int_bare']
    facts = scan_field('MetricDictRow', 'target_value')
    assert facts['decimal'] and not facts['int_bare'] and not facts['float']
    facts = scan_field('MetricDictRow', 'unit')
    assert facts['float'] == []


def test_r05_helpers_read_the_existing_literal_and_model_annotations():
    assert _literal_values(models.GradeCode) == ('L1', 'L2', 'L3', 'L4')
    assert model_in(
        models.WeightVersionDoc.model_fields['provenance'].annotation) \
        is models.WeightProvenance
    assert _nullable_scalar(
        models.DesignCardRow.model_fields['alt_method_note'].annotation) \
        is str
