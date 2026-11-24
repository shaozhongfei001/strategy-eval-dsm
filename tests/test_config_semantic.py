'''RED tests for the S1-T06 semantic half of dsm/config.py (L1, RED by design).

Contract authority = docs/adr/ORCH-24.md: the rulings plus the section 8
acceptance checklist. This file carries T06-A / B / C / D / E / F / G / K / L /
M / N / O / P / R; the version half (T06-H / I / J and its K L M N items) sits
in tests/test_config_weight_version.py, and T06-Q (the P-11 properties) was
appended to tests/test_config_properties.py. Case ids read
test_t06_<checklist letter><two digits>_<meaning>, so one group is one grep.

Why every case below is RED for exactly one reason: dsm/config.py exists since
S1-T05 but holds none of the eleven T06 public names of ruling 19, and every
reference is lazy (_config_module / cfg), so pytest collects this file with
zero errors and each failure is one of

  AttributeError  dsm.config has no attribute <X>          (ruling 19)
  TypeError       load_all does not take period / run_at   (ruling 19, last line)
  TypeError       a required keyword-only argument is missing (ruling 2)

Nothing here is a syntax error, an import-path error, a fixture error or an
expected value copied off an implementation. Per H-11 each expected value is
derived from the ruling text quoted in the comment of the assertion itself.

Scope discipline (ruling 1, over-reach = FAIL): load-time static validation
only. No C-02 re-normalisation, no C-03 orphan weights or is_redline /
dim_code matching, no C-10 anchor staleness / version_id / rank reversal, no
audit_bundle, no score_card suppression - those are S3 / S6 / S9.

Two checklist wordings are not executable as printed, so the enforceable
reading of the same ruling is used instead. Nothing is weakened:

  T06-O "dsm.models is not in sys.modules" - in a full pytest run
  tests/test_models_*.py import dsm.models into the very same interpreter, so
  the sys.modules form fails for reasons unrelated to config.py. Ruling 20
  states the enforceable rule ("T06 不得 import dsm.models"), so o02 scans the
  import graph of dsm/config.py through AST: dsm.models, dsm.io_loaders and
  the L0a / L0b modules are zero hits, which an import would violate.

  T06-O import envelope - section 8 writes "subset of {stdlib, yaml,
  pydantic, dsm.numeric, dsm.reason_codes}" while the task brief enumerates
  nine module names. The ADR is the authority (section 0), so o01 asserts both
  halves: every non-stdlib import is one of yaml / pydantic / dsm.numeric /
  dsm.reason_codes, and no dsm.* other than numeric / reason_codes appears.

Data (ruling 21 / H-5 / H-14): every tree is synthetic and every key carries
SYN-. The only numbers are the decimal strings that make a Sigma true
('0.25', '0.5', '0.9', ...) plus the declared type probes. No governance value
(K-01 .. K-20), threshold, floor, target or alpha / CR value is proposed; the
CR and alpha slots hold a parseable synthetic string solely because ruling 17
judges existence, not value. Everything is written under pytest tmp_path; the
repository config/ directory is never touched.
'''
import ast
import copy
import datetime
import importlib
import inspect
import re
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / 'dsm' / 'config.py'
THIS_PATH = Path(__file__).resolve()


# ---------------------------------------------------------------------------
# Lazy resolution. Attribute access only, so a missing T06 name raises
# AttributeError (feature not implemented) instead of breaking collection.
# ---------------------------------------------------------------------------
def _config_module():
    '''Import dsm.config inside the test body, never at module import time.'''
    return importlib.import_module('dsm.config')


def cfg(name):
    '''Resolve one public name of dsm.config (ORCH-24 ruling 19).'''
    module = _config_module()
    resolved = getattr(module, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.config has no attribute ' + name
            + ' (S1-T06 not implemented yet, ORCH-24 ruling 19)')
    return resolved


def _numeric_module():
    return importlib.import_module('dsm.numeric')


def RC():
    '''The registered reason_code enum (ORCH-24 ruling 5).'''
    return importlib.import_module('dsm.reason_codes').RC


# ---------------------------------------------------------------------------
# Contract constants, copied verbatim out of ORCH-24 rulings 4 / 19 and out of
# the frozen ORCH-23 rulings 3 / 8 / 9 / 10 / 11.
# ---------------------------------------------------------------------------
EXIT_BLOCK_EXPECTED = 2      # ruling 4 / [L1280] / [L900]
EXIT_CONFIG_EXPECTED = 3     # [L881] / [L1080], T05 value, must not move

NEW_NAMES = (
    'EXIT_BLOCK', 'SEMANTIC_CHECKS', 'WEIGHT_CHECKS', 'ConfigSemanticError',
    'WeightVersionInvalidError', 'to_decimal', 'period_key',
    'validate_semantics', 'validate_cross_file', 'select_weight_stem',
    'validate_weights')

T05_NAMES = (
    'EXIT_CONFIG', 'REQUIRED_CONFIG_STEMS', 'WEIGHTS_GLOB',
    'PLACEHOLDER_TOKENS', 'PLACEHOLDER_PREFIXES', 'ConfigTree', 'AppConfig',
    'ConfigPlaceholderError', 'is_placeholder_value', 'find_placeholders',
    'scan_config_trees', 'load_all')

# ruling 19 verbatim: [L879] order for the six semantic judgements plus the
# two pre-condition classes, then the five weight checks plus the same two.
SEMANTIC_CHECKS = ('SUM_LEVEL1', 'SUM_LEVEL2', 'FLOOR_MONOTONIC',
                   'REDLINE_METRIC_EXISTS', 'ACTION_NON_EMPTY',
                   'ANCHOR_MEMBER_EXISTS', 'STRUCTURE', 'NUMERIC')
WEIGHT_CHECKS = ('WEIGHT_COVERAGE', 'WEIGHT_STATUS_FROZEN',
                 'WEIGHT_WHATIF_RUN_ID', 'WEIGHT_PROVENANCE_COMPLETE',
                 'WEIGHT_APPROVAL', 'STRUCTURE', 'NUMERIC')

# ruling 3: the volume's two exception names are not built (ORCH-16 ruling 1).
NOT_BUILT_EXCEPTIONS = ('WeightSumError', 'WeightVersionNotFrozenError')

# ruling 18 message format, spelled out by the ADR because the SDD is silent.
MSG_SEM_HEAD = '配置语义校验失败 %d 项（退出码 %d）'
MSG_WEIGHT_HEAD = '权重版本校验失败 %d 项（退出码 %d，%s）'
MSG_ITEM_PREFIX = '  - '

# ORCH-23 ruling 10 / ruling 3, frozen by T05 and re-asserted in a02.
REQUIRED_STEMS = ('eval_config', 'redlines', 'grade_rules', 'anchor_set',
                  'ahp_matrices')
SIX_SLOTS = ('eval_config', 'weights', 'redlines', 'grade_rules',
             'anchor_set', 'ahp_matrices')
PLACEHOLDER_WORDS = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
WEIGHTS_GLOB_EXPECTED = 'weights_*.yaml'

# ruling 5: the five registered codes T06 may reference, and the bare spellings
# that must never appear as string literals in dsm/config.py.
T06_REASON_CODES = ('WEIGHT_VERSION_DRAFT', 'WEIGHT_VERSION_STALE',
                    'WEIGHT_MISSING_WHATIF_RUN_ID', 'WEIGHT_VERSION_INVALID',
                    'CONFIG_SEMANTIC_ERROR')

# ruling 20 / INV-1.
L0_MODULES = ('fixtures_gen', 'weights_ahp', 'weights_combine',
              'weights_calibrate', 'whatif')
AUTHORIZED_DSM_IMPORTS = ('dsm.numeric', 'dsm.reason_codes')
AUTHORIZED_THIRD_PARTY = ('yaml', 'pydantic')

# ---------------------------------------------------------------------------
# Synthetic configuration (ruling 21). Key names are verbatim from the SDD
# field tables cited by the rulings: level1_weights / level2_weights
# ([L1192], ruling 9), status / effective_from / effective_to / provenance
# ([L1190]-[L1194]), kind / whatif_run_id / approved_by / approved_date /
# ahp / comparison_matrices / cr / entropy / combine / alpha / alpha_basis
# ([L1228]-[L1245], ruling 17), grade_code / attainment_floor / actions /
# action_gate ([L1200]-[L1206], rulings 10 / 11), metric_id / level /
# comparator / threshold_value ([L1180]-[L1184], ruling 12), anchor_set_id /
# strategy_ids ([L1212], ruling 13).
# ---------------------------------------------------------------------------
WEIGHTS_STEM_A = 'weights_WV-SYN-0001'
WEIGHTS_STEM_B = 'weights_WV-SYN-0002'
DIMS = ('SYN-DIM-A', 'SYN-DIM-B', 'SYN-DIM-C', 'SYN-DIM-D')
METRICS = ('SYN-M-01', 'SYN-M-02')
STRATEGIES = ('SYN-S-001', 'SYN-S-002')
GHOST_METRIC = 'SYN-METRIC-GHOST'
GHOST_STRATEGY = 'SYN-STRATEGY-GHOST'
GRADES = ('L1', 'L2', 'L3', 'L4')

STATUS_FROZEN = 'FROZEN'      # [L1190] enum, not a business value
STATUS_DRAFT = 'DRAFT'        # [L1190] enum
STATUS_THIRD = 'SYN-STATUS-THIRD-VALUE'   # outside {DRAFT, FROZEN}

# Period probes. The shape is [L386] / [L1536] YYYY-MM; the day forms are the
# [L889] ISO shape that ruling 8 also accepts. Calendar test data, not a
# governance value.
PERIOD_OK = '2026-10'
PERIOD_FROM = '2026-01'
PERIOD_TO = '2026-12'
PERIOD_LATER_MONTH = '2026-11'
PERIOD_DAY_INSIDE = '2026-10-15'
PERIOD_INVALID_MONTH = '2026-13'
PERIOD_TWO_DIGIT_YEAR = '26-10'
PERIOD_BARE_INT = 202610      # type probe: not a date form at all

WHATIF_RUN_ID = 'SYN-WHATIF-RUN'
APPROVED_BY = 'SYN-APPROVER'
APPROVED_DATE = '2026-01-05'
KIND_AHP_ONLY = 'AHP_ONLY'                  # [L1231] enum
KIND_COMBINED = 'AHP_ENTROPY_COMBINED'      # [L1231] enum
KIND_EXPERT_ONLY = 'EXPERT_ONLY'            # [L1231] enum

# Decimal strings only (ruling 21: synthetic data that makes a Sigma true).
WEIGHT_EXACT = '0.25'                 # four of these sum to exactly 1
WEIGHT_AT_TOL = '0.250000000001'      # 0.25 + TOL, closed tolerance
WEIGHT_UNDER_TOL = '0.2500000000009'  # 0.25 + 9e-13, inside tolerance
WEIGHT_OVER_TOL = '0.250000000002'    # 0.25 + 2e-12, outside tolerance
WEIGHT_HALF = '0.5'
WEIGHT_SHORT_BY_TENTH = '0.4'
FLOORS_OK = ('0.9', '0.75', '0.6', '0.4')          # L1 > L2 > L3 > L4
FLOORS_EQUAL_PAIR = ('0.9', '0.75', '0.75', '0.4')  # [L879] monotonic breach
FLOORS_REVERSED = ('0.4', '0.6', '0.75', '0.9')
FLOORS_SUB_TOL_GAP = ('0.9', '0.75', '0.7499999999999999', '0.4')
FLOORS_THREE = ('0.9', '0.75', '0.6')               # L4 absent
FLOORS_FIVE = ('0.95', '0.9', '0.75', '0.6', '0.4')
CODES_FIVE = ('L1', 'L2', 'L3', 'L4', 'L5')
CODES_DOUBLED = ('L1', 'L1', 'L2', 'L3', 'L4')
FLOORS_DOUBLED = ('0.9', '0.85', '0.75', '0.6', '0.4')
CR_PRESENT = '0.25'      # parseable only; ruling 17 forbids judging the value
ALPHA_PRESENT = '0.25'   # same, [L1435] alpha existence gate only
CR_LARGE = '0.99'        # existence, not a threshold proposal (B-041)
ALPHA_LARGE = '0.99'     # existence, not a range proposal (B-042)
NUMERIC_GARBAGE = 'abc'  # unparsable decimal probe (ruling 7)

# Type probes only, never business values: they pin the float / bool branches
# of ruling 7, which says a float or bool in a weight slot is a NUMERIC
# violation and nothing else.
TYPE_PROBE_FLOAT = 0.25   # 仅类型探针，非业务值
TYPE_PROBE_ONE = 1        # int is accepted by ruling 7
TYPE_PROBE_LIST = ['SYN-NOT-A-STRING']  # non-str whatif_run_id probe (ruling 18)

ACTION_OK = ('SYN-ACTION-01',)
ACTION_BLANK_PROBES = ([], (), '', {}, ['   '])   # ruling 11 empty shapes


def _level1(value=WEIGHT_EXACT):
    return {dim: value for dim in DIMS}


def _level2(value=WEIGHT_HALF):
    return {dim: {METRICS[0]: value, METRICS[1]: value} for dim in DIMS}


def _provenance(kind=KIND_AHP_ONLY):
    '''A complete provenance for the kind (ruling 17 matrix).'''
    prov = {
        'kind': kind,
        'whatif_run_id': WHATIF_RUN_ID,
        'approved_by': APPROVED_BY,
        'approved_date': APPROVED_DATE,
        'ahp': {'comparison_matrices': {'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'},
                'cr': CR_PRESENT},
    }
    if kind == KIND_COMBINED:
        prov['entropy'] = {'SYN-ENTROPY-WEIGHTS': 'SYN-ENTROPY-PAYLOAD'}
        prov['combine'] = {'alpha': ALPHA_PRESENT}
        prov['alpha_basis'] = 'SYN-ALPHA-BASIS'
    return prov


def _weights(stem=WEIGHTS_STEM_A, status=STATUS_FROZEN, kind=KIND_AHP_ONLY):
    return {
        'weight_version_id': stem,           # [L1190]
        'status': status,                    # [L1190]
        'effective_from': PERIOD_FROM,       # [L1193]
        'effective_to': PERIOD_TO,           # [L1193]
        'level1_weights': _level1(),         # [L1192]
        'level2_weights': _level2(),         # [L1192]
        'provenance': _provenance(kind),     # [L1194]
    }


def _grade_rule(grade, floor, actions, gate):
    return {'grade_code': grade, 'grade_label': 'SYN-GRADE-LABEL',
            'attainment_floor': floor, 'evidence_class_min': 'SYN-EVIDENCE',
            'redline_pass_required': True, 'actions': actions,
            'action_gate': gate}


def _grade_rules(floors=FLOORS_OK, codes=GRADES, actions=list(ACTION_OK),
                 gate='SYN-ACTION-GATE'):
    levels = []
    for index, floor in enumerate(floors):
        code = codes[index] if index < len(codes) else 'L' + str(index + 1)
        levels.append(_grade_rule(code, floor, list(actions), gate))
    return {'levels': levels}


def _redlines(metric_ids=METRICS):
    rules = []
    for metric in metric_ids:
        rules.append({'metric_id': metric, 'level': 'HARD',
                      'comparator': 'SYN-COMPARATOR',
                      'threshold_value': 'SYN-THRESHOLD-REF',
                      'forced_grade': 'SYN-FORCED-GRADE',
                      'waiver_allowed': False})
    return {'rules': {'HARD': rules}}


def _anchor(members=STRATEGIES):
    return {'anchor_set_id': 'SYN-ANCHOR-0001', 'strategy_ids': list(members),
            'effective_from': PERIOD_FROM, 'effective_to': PERIOD_TO,
            'rationale': 'SYN-RATIONALE'}


def _eval_config():
    return {'SYN-evidence_mode': 'SYN-EVIDENCE-MODE',
            'SYN-triangulation': {'enabled': True, 'SYN-thresholds': ['SYN-T']}}


def _ahp_matrices():
    return {'matrices': {'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'}}


def payload(**overrides):
    '''The six AppConfig slots (ORCH-23 ruling 3), all valid for T06.'''
    built = {'eval_config': _eval_config(),
             'weights': {WEIGHTS_STEM_A: _weights()},
             'redlines': _redlines(),
             'grade_rules': _grade_rules(),
             'anchor_set': _anchor(),
             'ahp_matrices': _ahp_matrices()}
    built.update(overrides)
    return built


def appcfg(**overrides):
    '''Build an AppConfig lazily so a missing class fails as AttributeError.'''
    return cfg('AppConfig')(**payload(**overrides))


def frozen_weights(**segments):
    '''One FROZEN weights tree with the named top level segments replaced.'''
    tree = _weights()
    tree.update(segments)
    return tree


def slot(tree, stem=WEIGHTS_STEM_A):
    return {stem: tree}


def semantics(**overrides):
    '''validate_semantics over the synthetic AppConfig (ruling 19).'''
    return cfg('validate_semantics')(appcfg(**overrides))


def semantics_of(weights_slot, **overrides):
    overrides['weights'] = weights_slot
    return cfg('validate_semantics')(appcfg(**overrides))


def cross_file(**overrides):
    '''validate_cross_file with both registries injected (ruling 2).'''
    return cfg('validate_cross_file')(
        appcfg(**overrides), metric_ids=frozenset(METRICS),
        strategy_ids=frozenset(STRATEGIES))


def file_trees(**overrides):
    '''The {file stem: tree} view of the six slots: the weights slot is
    already keyed by stem, the other five are single documents.'''
    built = {'eval_config': _eval_config(),
             WEIGHTS_STEM_A: _weights(),
             'redlines': _redlines(),
             'grade_rules': _grade_rules(),
             'anchor_set': _anchor(),
             'ahp_matrices': _ahp_matrices()}
    built.update(overrides)
    return built


def write_dir(base, **overrides):
    '''Render {stem: tree} as <stem>.yaml under base (tmp_path only, H-14).'''
    trees = file_trees(**overrides)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    for stem, tree in trees.items():
        (base / (stem + '.yaml')).write_text(
            yaml.safe_dump(tree, allow_unicode=True, sort_keys=False),
            encoding='utf-8')
    return base


# ---------------------------------------------------------------------------
# Violation readers. A violation is the (check_id, path, detail) triple of
# ruling 18; these helpers make every assertion spell out the contract.
# ---------------------------------------------------------------------------
def semantic_error():
    return cfg('ConfigSemanticError')


def weight_error():
    return cfg('WeightVersionInvalidError')


def ids_of(exc):
    return [item[0] for item in exc.violations]


def paths_of(exc):
    return [item[1] for item in exc.violations]


def details_of(exc):
    return [item[2] for item in exc.violations]


def assert_triples(exc, checks):
    '''Ruling 18: triples of str, sorted by (checks.index, path), deduped.'''
    for item in exc.violations:
        assert isinstance(item, tuple), repr(item)
        assert len(item) == 3, repr(item)
        assert all(isinstance(part, str) for part in item), repr(item)
    keys = [(checks.index(item[0]), item[1]) for item in exc.violations]
    assert keys == sorted(keys), repr(keys)
    assert len(exc.violations) == len(set(exc.violations)), 'not deduplicated'


def assert_item_lines(exc):
    '''Ruling 18: one "  - <check_id> <path>: <detail>" line per violation.'''
    lines = str(exc).splitlines()
    assert len(lines) == 1 + len(exc.violations), lines
    for line, item in zip(lines[1:], exc.violations):
        head = MSG_ITEM_PREFIX + item[0] + ' ' + item[1] + ': '
        assert line.startswith(head), line
        assert line[len(head):] != '', line

# ---------------------------------------------------------------------------
# Scenario dispatcher used by the parametrised reason_code / exit code gates.
# Every branch calls a T06 name, so each one is RED through AttributeError.
# ---------------------------------------------------------------------------
SEMANTIC_SCENARIOS = ('sum_level1', 'sum_level2', 'floor', 'actions',
                      'redline_metric', 'anchor_member', 'numeric_weight',
                      'numeric_floor', 'structure_missing_level1')


def violating_semantic_call(name):
    '''A zero argument callable that must raise ConfigSemanticError.'''
    tree = _weights()
    if name == 'sum_level1':
        tree['level1_weights']['SYN-DIM-D'] = WEIGHT_OVER_TOL
        return lambda: cfg('validate_semantics')(
            appcfg(weights=slot(tree)))
    if name == 'sum_level2':
        tree['level2_weights']['SYN-DIM-B'] = {
            METRICS[0]: WEIGHT_HALF, METRICS[1]: WEIGHT_SHORT_BY_TENTH}
        return lambda: cfg('validate_semantics')(
            appcfg(weights=slot(tree)))
    if name == 'floor':
        rules = _grade_rules(floors=FLOORS_EQUAL_PAIR)
        return lambda: cfg('validate_semantics')(appcfg(grade_rules=rules))
    if name == 'actions':
        rules = _grade_rules()
        rules['levels'][1]['actions'] = []
        return lambda: cfg('validate_semantics')(appcfg(grade_rules=rules))
    if name == 'redline_metric':
        return lambda: cfg('validate_cross_file')(
            appcfg(redlines=_redlines((GHOST_METRIC, METRICS[1]))),
            metric_ids=frozenset(METRICS), strategy_ids=frozenset(STRATEGIES))
    if name == 'anchor_member':
        return lambda: cfg('validate_cross_file')(
            appcfg(anchor_set=_anchor((STRATEGIES[0], GHOST_STRATEGY))),
            metric_ids=frozenset(METRICS), strategy_ids=frozenset(STRATEGIES))
    if name == 'numeric_weight':
        tree['level1_weights']['SYN-DIM-C'] = TYPE_PROBE_FLOAT
        return lambda: cfg('validate_semantics')(appcfg(weights=slot(tree)))
    if name == 'numeric_floor':
        rules = _grade_rules()
        rules['levels'][2]['attainment_floor'] = TYPE_PROBE_FLOAT
        return lambda: cfg('validate_semantics')(appcfg(grade_rules=rules))
    if name == 'structure_missing_level1':
        tree.pop('level1_weights')
        return lambda: cfg('validate_semantics')(appcfg(weights=slot(tree)))
    raise KeyError(name)


# ---------------------------------------------------------------------------
# T06-A. The eleven new public names and the twelve frozen T05 names
# (ruling 19, verbatim block).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('name', NEW_NAMES)
def test_t06_a01_the_eleven_new_public_names_exist(name):
    '''ORCH-24 ruling 19: eleven new public names, spelled verbatim.'''
    assert cfg(name) is not None


def test_t06_a02_the_twelve_t05_public_names_are_unchanged(tmp_path):
    '''Ruling 19: "T05 的 12 个公开名签名与行为一条不改, load_all 只追加可选
    kwarg" (ORCH-23 ruling 11). The last statement calls load_all with the new
    keyword, which is the extension T06 owes; today it is a TypeError.'''
    assert cfg('EXIT_CONFIG') == EXIT_CONFIG_EXPECTED
    assert cfg('REQUIRED_CONFIG_STEMS') == REQUIRED_STEMS
    assert cfg('WEIGHTS_GLOB') == WEIGHTS_GLOB_EXPECTED
    assert tuple(cfg('PLACEHOLDER_TOKENS')) == PLACEHOLDER_WORDS
    assert tuple(cfg('PLACEHOLDER_PREFIXES')) == PLACEHOLDER_WORDS
    assert cfg('ConfigTree') == dict[str, Any]
    assert tuple(cfg('AppConfig').model_fields) == SIX_SLOTS
    assert _parameter_names(cfg('is_placeholder_value')) == ['value']
    assert _parameter_names(cfg('find_placeholders')) == ['tree', 'root']
    assert _parameter_names(cfg('scan_config_trees')) == ['trees']
    root = inspect.signature(cfg('find_placeholders')).parameters['root']
    assert root.default == ''
    assert root.kind is inspect.Parameter.KEYWORD_ONLY
    base = write_dir(tmp_path / 'cfg')
    cfg('load_all')(str(base), period=PERIOD_OK)
    params = inspect.signature(cfg('load_all')).parameters
    assert list(params) == ['config_dir', 'period', 'run_at']
    for name in ('period', 'run_at'):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name
        assert params[name].default is None, name


def test_t06_a03_load_all_takes_period_as_a_keyword_only(tmp_path):
    '''Ruling 19 / ORCH-23 ruling 11: the two additions are keyword only, so
    a positional period must stay a TypeError while the keyword form loads.
    The second half is what is missing today (TypeError: unexpected keyword
    argument), so this case is RED for the signature extension, exactly like
    a02.'''
    base = write_dir(tmp_path / 'cfg')
    with pytest.raises(TypeError):
        cfg('load_all')(str(base), PERIOD_OK)
    loaded = cfg('load_all')(str(base), period=PERIOD_OK)
    assert loaded is not None
    assert cfg('AppConfig') is type(loaded)


def test_t06_a04_the_two_check_tuples_are_verbatim():
    '''Ruling 19: SEMANTIC_CHECKS in [L879] order plus STRUCTURE / NUMERIC,
    WEIGHT_CHECKS in the ruling 15 order plus STRUCTURE / NUMERIC.'''
    assert tuple(cfg('SEMANTIC_CHECKS')) == SEMANTIC_CHECKS
    assert tuple(cfg('WEIGHT_CHECKS')) == WEIGHT_CHECKS
    for name in ('SEMANTIC_CHECKS', 'WEIGHT_CHECKS'):
        value = cfg(name)
        assert isinstance(value, tuple), name
        assert all(isinstance(item, str) for item in value), name
        assert len(value) == len(set(value)), name


def test_t06_a05_the_six_new_function_signatures_are_verbatim():
    '''Ruling 19 signatures, parameter names in order.'''
    expected = {
        'to_decimal': ['value', 'path'],
        'period_key': ['value'],
        'validate_semantics': ['cfg'],
        'validate_cross_file': ['cfg', 'metric_ids', 'strategy_ids'],
        'select_weight_stem': ['cfg', 'period'],
        'validate_weights': ['cfg', 'period'],
    }
    for name, names in expected.items():
        assert _parameter_names(cfg(name)) == names, name
    assert callable(cfg('to_decimal'))
    assert callable(cfg('select_weight_stem'))


def test_t06_a06_the_injected_arguments_are_required_without_default():
    '''Ruling 2: "不得给 metric_ids / strategy_ids / period 设 None 默认后再
    若为 None 则跳过" - a missing default is what makes an omitted injection
    loud instead of silent.'''
    params = inspect.signature(cfg('validate_cross_file')).parameters
    for name in ('metric_ids', 'strategy_ids'):
        assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, name
        assert params[name].default is inspect.Parameter.empty, name
    for name in ('validate_weights', 'select_weight_stem'):
        period = inspect.signature(cfg(name)).parameters['period']
        assert period.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert period.default is inspect.Parameter.empty, name
    path = inspect.signature(cfg('to_decimal')).parameters['path']
    assert path.kind is inspect.Parameter.KEYWORD_ONLY
    assert path.default is inspect.Parameter.empty


def test_t06_a07_the_two_exception_constructors_are_verbatim():
    '''Ruling 19: ConfigSemanticError(violations) with no default, and
    WeightVersionInvalidError(reason_code, violations=()).'''
    sem = cfg('ConfigSemanticError')
    weight = cfg('WeightVersionInvalidError')
    sem_params = inspect.signature(sem.__init__).parameters
    assert list(sem_params) == ['self', 'violations']
    assert sem_params['violations'].default is inspect.Parameter.empty
    weight_params = inspect.signature(weight.__init__).parameters
    assert list(weight_params) == ['self', 'reason_code', 'violations']
    assert weight_params['reason_code'].default is inspect.Parameter.empty
    assert weight_params['violations'].default == ()


def _parameter_names(fn):
    return list(inspect.signature(fn).parameters)


# ---------------------------------------------------------------------------
# T06-B. Exit codes are single sources of truth (ruling 4).
# ---------------------------------------------------------------------------
def test_t06_b01_exit_block_is_two_and_exit_config_stays_three():
    '''Ruling 4: EXIT_BLOCK = 2 ([L1280] / [L900] / [L1413]); EXIT_CONFIG = 3
    is the T05 value and must not move ([L881] / [L1080]).'''
    assert cfg('EXIT_BLOCK') == EXIT_BLOCK_EXPECTED
    assert cfg('EXIT_CONFIG') == EXIT_CONFIG_EXPECTED
    assert isinstance(cfg('EXIT_BLOCK'), int)


def test_t06_b02_config_semantic_error_exit_code_is_three():
    '''Ruling 4 / ruling 19: exit_code is an instance attribute, 3.'''
    err = cfg('ConfigSemanticError')([('STRUCTURE', 'eval_config.SYN-a',
                                      'detail')])
    assert err.exit_code == cfg('EXIT_CONFIG')
    assert err.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_b03_weight_version_invalid_error_exit_code_is_two():
    '''Ruling 4: "结构/类型问题一律 3, 版本策略问题一律 2".'''
    err = cfg('WeightVersionInvalidError')(RC().WEIGHT_VERSION_STALE)
    assert err.exit_code == cfg('EXIT_BLOCK')
    assert err.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_b04_weight_error_stores_reason_code_and_violations():
    '''Ruling 19: __init__(reason_code, violations=()) keeps both.'''
    err = cfg('WeightVersionInvalidError')
    stale = RC().WEIGHT_VERSION_STALE
    bare = err(stale)
    assert bare.reason_code is stale
    assert bare.violations == ()
    filled = err(RC().WEIGHT_VERSION_INVALID,
                 [('WEIGHT_COVERAGE', WEIGHTS_STEM_A, 'detail')])
    assert filled.violations == (('WEIGHT_COVERAGE', WEIGHTS_STEM_A,
                                  'detail'),)


# ---------------------------------------------------------------------------
# T06-C. The volume's two exception names are not built; the three SDD names
# are peers under Exception (ruling 3).
# ---------------------------------------------------------------------------
def test_t06_c01_the_two_not_built_exception_names_are_absent():
    '''Ruling 3: WeightSumError / WeightVersionNotFrozenError must not exist
    (ORCH-16 ruling 1, H-10). R3 writing them would itself be a FAIL.'''
    module = _config_module()
    for name in NOT_BUILT_EXCEPTIONS:
        assert hasattr(module, name) is False, name
    assert cfg('ConfigSemanticError') is not None
    assert cfg('WeightVersionInvalidError') is not None


def test_t06_c02_the_three_exceptions_are_peers_under_exception():
    '''Ruling 3: "三个异常平级继承 Exception ... 不发明中间基类".'''
    peers = (cfg('ConfigPlaceholderError'), cfg('ConfigSemanticError'),
             cfg('WeightVersionInvalidError'))
    for err in peers:
        assert issubclass(err, Exception)
        assert err.__bases__ == (Exception,), err.__name__
    for left in peers:
        for right in peers:
            if left is not right:
                assert not issubclass(left, right)
                assert left is not right

# ---------------------------------------------------------------------------
# T06-D. Sigma W_d = 1 and per dimension Sigma w_j = 1, Decimal plus
# numeric.TOL on a closed interval (rulings 6 / 9, [L902] / [L1429] / [L1438]).
# ---------------------------------------------------------------------------
def test_t06_d01_four_quarter_weights_sum_to_one():
    '''Ruling 6: the comparison is numeric.eq_tol(total, numeric.ONE), and the
    tolerance itself is numeric.TOL, never a float written in config.py.'''
    numeric = _numeric_module()
    total = Decimal('0')
    for dim in DIMS:
        total += Decimal(WEIGHT_EXACT)
    assert total == numeric.ONE
    assert (Decimal(WEIGHT_AT_TOL) - Decimal(WEIGHT_EXACT)) == numeric.TOL
    assert (Decimal(WEIGHT_UNDER_TOL) - Decimal(WEIGHT_EXACT)) < numeric.TOL
    assert (Decimal(WEIGHT_OVER_TOL) - Decimal(WEIGHT_EXACT)) > numeric.TOL
    assert semantics() is None


def test_t06_d02_a_level1_sum_beyond_the_tolerance_is_reported():
    '''Ruling 9: eq_tol fails -> SUM_LEVEL1 at <stem>.level1_weights.'''
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': WEIGHT_EXACT, 'SYN-DIM-B': WEIGHT_EXACT,
        'SYN-DIM-C': WEIGHT_EXACT, 'SYN-DIM-D': WEIGHT_OVER_TOL})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['SUM_LEVEL1']
    assert paths_of(exc) == [WEIGHTS_STEM_A + '.level1_weights']
    assert details_of(exc)[0] != ''
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert_triples(exc, SEMANTIC_CHECKS)


def test_t06_d03_a_level1_sum_exactly_at_the_tolerance_passes():
    '''Ruling 6 / [L902]: the tolerance is closed, numeric.eq_tol uses <=, so
    a drift of exactly numeric.TOL is inside [L879] "Sigma W_d = 1".'''
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': WEIGHT_EXACT, 'SYN-DIM-B': WEIGHT_EXACT,
        'SYN-DIM-C': WEIGHT_EXACT, 'SYN-DIM-D': WEIGHT_AT_TOL})
    assert semantics_of(slot(tree)) is None


def test_t06_d04_a_level1_sum_just_under_the_tolerance_passes():
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': WEIGHT_EXACT, 'SYN-DIM-B': WEIGHT_EXACT,
        'SYN-DIM-C': WEIGHT_EXACT, 'SYN-DIM-D': WEIGHT_UNDER_TOL})
    assert semantics_of(slot(tree)) is None


def test_t06_d05_level2_is_normalized_inside_every_dimension():
    '''[L879] "每维度内 Sigma w_j = 1" / ruling 9: the object is
    level2_weights, checked per dimension key.'''
    assert semantics() is None
    tree = frozen_weights(level2_weights={
        'SYN-DIM-A': {METRICS[0]: '0.3', METRICS[1]: '0.7'},
        'SYN-DIM-B': {METRICS[0]: WEIGHT_HALF, METRICS[1]: WEIGHT_HALF},
        'SYN-DIM-C': {METRICS[0]: '1'},
        'SYN-DIM-D': {METRICS[0]: '0.2', METRICS[1]: '0.8'}})
    assert semantics_of(slot(tree)) is None


def test_t06_d06_only_the_off_dimension_is_reported_and_names_the_dimension():
    '''Ruling 9: one violation per offending dimension, path
    <stem>.level2_weights.<dim>; the compliant dimension stays silent.'''
    tree = frozen_weights(level2_weights={
        'SYN-DIM-A': {METRICS[0]: WEIGHT_HALF, METRICS[1]: WEIGHT_HALF},
        'SYN-DIM-B': {METRICS[0]: WEIGHT_HALF, METRICS[1]: '0.4'}})
    tree['level1_weights'] = {'SYN-DIM-A': WEIGHT_HALF,
                              'SYN-DIM-B': WEIGHT_HALF}
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['SUM_LEVEL2']
    assert paths_of(exc) == [WEIGHTS_STEM_A + '.level2_weights.SYN-DIM-B']


def test_t06_d07_an_empty_level1_mapping_is_a_violation():
    '''Ruling 9: "空 mapping 的 Sigma = 0 != 1 -> 自然违规, 不特判".'''
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(frozen_weights(level1_weights={})))
    exc = excinfo.value
    assert ids_of(exc) == ['SUM_LEVEL1']
    assert paths_of(exc) == [WEIGHTS_STEM_A + '.level1_weights']


def test_t06_d08_an_empty_dimension_in_level2_is_a_violation():
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(frozen_weights(level2_weights={
            'SYN-DIM-A': {}, 'SYN-DIM-B': {METRICS[0]: '1'}})))
    exc = excinfo.value
    assert ids_of(exc) == ['SUM_LEVEL2']
    assert paths_of(exc) == [WEIGHTS_STEM_A + '.level2_weights.SYN-DIM-A']


def test_t06_d09_a_missing_level1_key_is_a_structure_violation():
    '''Ruling 9 结构前置: the two keys sit at the top level of the weights
    tree ([L1190]-[L1194] are document columns), no recursive hunt.'''
    tree = frozen_weights()
    tree.pop('level1_weights')
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    exc = excinfo.value
    assert {item for item in ids_of(exc)} == {'STRUCTURE'}
    assert WEIGHTS_STEM_A in paths_of(exc)[0]


def test_t06_d10_a_missing_level2_key_is_a_structure_violation():
    tree = frozen_weights()
    tree.pop('level2_weights')
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    assert set(ids_of(excinfo.value)) == {'STRUCTURE'}


def test_t06_d11_a_draft_version_is_not_sum_checked():
    '''Ruling 9 校验范围: only FROZEN trees are sum checked, because [L1190]
    restricts scoring to FROZEN and [L379] makes DRAFT the intermediate
    product of combine build. This is the boundary of ruling 9.'''
    draft = _weights(WEIGHTS_STEM_B, status=STATUS_DRAFT)
    draft['level1_weights']['SYN-DIM-D'] = WEIGHT_OVER_TOL
    draft['level2_weights']['SYN-DIM-B'] = {METRICS[0]: WEIGHT_HALF,
                                            METRICS[1]: '0.4'}
    assert semantics_of({WEIGHTS_STEM_B: draft}) is None


def test_t06_d12_the_frozen_sibling_in_the_same_dir_is_still_checked():
    '''Ruling 9, the other half of the boundary: a DRAFT next to a FROZEN
    never hides the FROZEN breach.'''
    draft = _weights(WEIGHTS_STEM_B, status=STATUS_DRAFT)
    draft['level1_weights']['SYN-DIM-D'] = WEIGHT_OVER_TOL
    frozen = frozen_weights(level1_weights={
        'SYN-DIM-A': WEIGHT_HALF, 'SYN-DIM-B': '0.3'})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of({WEIGHTS_STEM_B: draft, WEIGHTS_STEM_A: frozen})
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['SUM_LEVEL1']
    assert paths_of(exc) == [WEIGHTS_STEM_A + '.level1_weights']


def test_t06_d13_load_all_holds_the_semantic_hook(tmp_path):
    '''Ruling 2: load_all always calls validate_semantics (ORCH-23 ruling 11
    order: read -> PLACEHOLDER scan -> semantic hook -> return).'''
    trees = file_trees()
    trees[WEIGHTS_STEM_A]['level1_weights']['SYN-DIM-D'] = WEIGHT_OVER_TOL
    base = write_dir(tmp_path / 'cfg', **trees)
    with pytest.raises(semantic_error()) as excinfo:
        cfg('load_all')(str(base))
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert ids_of(exc) == ['SUM_LEVEL1']


# ---------------------------------------------------------------------------
# T06-E. attainment_floor strictly decreasing over exactly four grades, L1 >
# L2 > L3 > L4 (ruling 10, [L879] / [L493] / [L1200]-[L1201]).
# ---------------------------------------------------------------------------
def test_t06_e01_four_strictly_decreasing_floors_pass():
    '''Ruling 10: [L879] "attainment_floor 单调（L1 > L2 > L3 > L4）".'''
    assert semantics() is None


def test_t06_e02_two_equal_floors_are_reported():
    rules = _grade_rules(floors=FLOORS_EQUAL_PAIR)
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['FLOOR_MONOTONIC']
    assert paths_of(exc)[0].startswith('grade_rules')


def test_t06_e03_reversed_floors_are_reported():
    '''Ruling 10: any order breach is FLOOR_MONOTONIC, never STRUCTURE. The
    count per breach pair is not pinned by the ADR, the check id is.'''
    rules = _grade_rules(floors=FLOORS_REVERSED)
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    exc = excinfo.value
    assert set(ids_of(exc)) == {'FLOOR_MONOTONIC'}
    assert len(exc.violations) >= 1
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_e04_a_sub_tolerance_floor_gap_is_still_strictly_decreasing():
    '''Ruling 10: "比较用 Decimal 精确 > (序关系不引入容差)" - a gap smaller
    than numeric.TOL passes as long as the two floors are not equal.'''
    numeric = _numeric_module()
    gap = Decimal(FLOORS_OK[1]) - Decimal(FLOORS_OK[2])
    small = Decimal(FLOORS_SUB_TOL_GAP[1]) - Decimal(FLOORS_SUB_TOL_GAP[2])
    assert small > Decimal('0') and small < numeric.TOL
    assert gap > numeric.TOL
    assert semantics(grade_rules=_grade_rules(
        floors=FLOORS_SUB_TOL_GAP)) is None


def test_t06_e05_a_missing_fourth_grade_is_a_structure_violation():
    '''Ruling 10: "四级必须恰为 {L1, L2, L3, L4} 各一条 ([L1200]); 缺级 /
    重复级 -> STRUCTURE".'''
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=_grade_rules(floors=FLOORS_THREE))
    assert set(ids_of(excinfo.value)) == {'STRUCTURE'}


def test_t06_e06_a_duplicated_grade_code_is_a_structure_violation():
    '''Ruling 14: "同一 grade_code 被收集到多次 -> STRUCTURE 违规 (配置不自洽,
    不得静默取第一个)". The floors are strictly decreasing, so the only
    reportable breach is the duplication itself.'''
    rules = _grade_rules(floors=FLOORS_DOUBLED, codes=CODES_DOUBLED)
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    assert set(ids_of(excinfo.value)) == {'STRUCTURE'}


def test_t06_e07_a_fifth_grade_is_a_structure_violation():
    '''Ruling 10: exactly {L1, L2, L3, L4}; an L5 row makes the set wrong.'''
    rules = _grade_rules(floors=FLOORS_FIVE, codes=CODES_FIVE)
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    assert set(ids_of(excinfo.value)) == {'STRUCTURE'}


def test_t06_e08_the_rules_are_collected_recursively_not_by_top_key():
    '''Ruling 14: the SDD never names the top level key of grade_rules.yaml,
    so the collection rule is "any mapping carrying both grade_code and
    attainment_floor", at any depth.'''
    deep = {'SYN-bands': [{'SYN-group': [
        _grade_rule('L1', '0.9', list(ACTION_OK), 'SYN-ACTION-GATE'),
        _grade_rule('L2', '0.75', list(ACTION_OK), 'SYN-ACTION-GATE'),
        _grade_rule('L3', '0.75', list(ACTION_OK), 'SYN-ACTION-GATE'),
        _grade_rule('L4', '0.4', list(ACTION_OK), 'SYN-ACTION-GATE')]}]}
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=deep)
    exc = excinfo.value
    assert set(ids_of(exc)) == {'FLOOR_MONOTONIC'}
    assert paths_of(exc)[0].startswith('grade_rules.SYN-bands[0]')

# ---------------------------------------------------------------------------
# T06-F. Every grade_rule carries a non-empty actions ([L1205], ruling 11).
# ---------------------------------------------------------------------------
def test_t06_f01_non_empty_actions_pass():
    assert semantics() is None


@pytest.mark.parametrize('shape', ACTION_BLANK_PROBES,
                         ids=['empty-list', 'empty-tuple', 'empty-string',
                              'empty-dict', 'blank-only-sequence'])
def test_t06_f02_an_empty_actions_slot_is_reported(shape):
    '''Ruling 11: "空 list / 空 tuple / 空 dict / 空串 / 全为空白串的序列,
    一律 ACTION_NON_EMPTY 违规". None is not tested here because [L878] plus
    ORCH-23 ruling 6 already stop it one stage earlier.'''
    rules = _grade_rules()
    rules['levels'][1]['actions'] = shape
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['ACTION_NON_EMPTY']
    assert paths_of(exc)[0].startswith('grade_rules')
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_f03_every_rule_is_checked_and_each_breach_is_its_own_path():
    '''Ruling 11 "每条 grade_rule" + ruling 18: two empty rules are two
    violations, deduplicated only when the path really collides.'''
    rules = _grade_rules()
    rules['levels'][1]['actions'] = []
    rules['levels'][3]['actions'] = ''
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    exc = excinfo.value
    assert ids_of(exc) == ['ACTION_NON_EMPTY', 'ACTION_NON_EMPTY']
    assert len(set(paths_of(exc))) == 2
    assert_triples(exc, SEMANTIC_CHECKS)


def test_t06_f04_an_empty_action_gate_is_not_a_violation():
    '''Ruling 11: "action_gate 不做非空校验 ([L879] 只说 action; 最小实现,
    不提前扩判据)". The empty string is a filled value, not a placeholder,
    per ORCH-23 ruling 19.'''
    for gate in ('', '   ', []):
        rules = _grade_rules(gate=gate)
        assert semantics(grade_rules=rules) is None, repr(gate)


# ---------------------------------------------------------------------------
# T06-G. The two cross-file judgements take their registries as required
# keyword arguments (rulings 2 / 12 / 13, [L879] with [L1180] / [L1212]).
# ---------------------------------------------------------------------------
def test_t06_g01_omitting_strategy_ids_is_a_typeerror():
    '''Ruling 2: both registries are required without default, so forgetting
    one is loud. The same holds for metric_ids, asserted in g02.'''
    with pytest.raises(TypeError):
        cfg('validate_cross_file')(appcfg(), metric_ids=frozenset(METRICS))


def test_t06_g02_omitting_metric_ids_is_a_typeerror():
    with pytest.raises(TypeError):
        cfg('validate_cross_file')(appcfg(), strategy_ids=frozenset(STRATEGIES))


def test_t06_g03_a_deep_redline_reference_is_reported_by_index_path():
    '''Ruling 12: recurse the redlines tree, collect every mapping carrying a
    metric_id key; ruling 14 / ORCH-23 ruling 8: the path spells the list
    index in brackets, zero based.'''
    redlines = {'rules': {'HARD': [
        {'metric_id': METRICS[0], 'level': 'HARD',
         'threshold_value': 'SYN-THRESHOLD-REF'},
        {'metric_id': GHOST_METRIC, 'level': 'HARD',
         'threshold_value': 'SYN-THRESHOLD-REF'}]}}
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_cross_file')(appcfg(redlines=redlines),
                                   metric_ids=frozenset(METRICS),
                                   strategy_ids=frozenset(STRATEGIES))
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['REDLINE_METRIC_EXISTS']
    assert paths_of(exc) == ['redlines.rules.HARD[1].metric_id']
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_g04_a_ghost_anchor_member_is_reported_by_index_path():
    '''Ruling 13: strategy_ids is expanded member by member and the path ends
    with the member index, <loc>.strategy_ids[i].'''
    anchor = _anchor((STRATEGIES[0], GHOST_STRATEGY))
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_cross_file')(appcfg(anchor_set=anchor),
                                   metric_ids=frozenset(METRICS),
                                   strategy_ids=frozenset(STRATEGIES))
    exc = excinfo.value
    assert len(exc.violations) == 1
    assert ids_of(exc) == ['ANCHOR_MEMBER_EXISTS']
    assert paths_of(exc) == ['anchor_set.strategy_ids[1]']


def test_t06_g05_an_empty_metric_registry_blocks_every_reference():
    '''Ruling 12: "metric_ids 为空集合时任何 metric_id 引用都违规 (不静默
    放过)".'''
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_cross_file')(appcfg(), metric_ids=frozenset(),
                                   strategy_ids=frozenset(STRATEGIES))
    exc = excinfo.value
    assert len(exc.violations) == len(METRICS)
    assert set(ids_of(exc)) == {'REDLINE_METRIC_EXISTS'}
    assert paths_of(exc) == ['redlines.rules.HARD[0].metric_id',
                             'redlines.rules.HARD[1].metric_id']


def test_t06_g06_an_empty_strategy_registry_blocks_every_member():
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_cross_file')(appcfg(), metric_ids=frozenset(METRICS),
                                   strategy_ids=frozenset())
    exc = excinfo.value
    assert len(exc.violations) == len(STRATEGIES)
    assert set(ids_of(exc)) == {'ANCHOR_MEMBER_EXISTS'}
    assert paths_of(exc) == ['anchor_set.strategy_ids[0]',
                             'anchor_set.strategy_ids[1]']


def test_t06_g07_no_reference_means_no_violation():
    '''Ruling 12 / ruling 13 tails: "redlines 树无任何 metric_id -> 无违规",
    "strategy_ids 为空序列 -> 无违规" (an empty anchor set is a C-10
    effectiveness question, out of T06 by ruling 1).'''
    redlines = {'rules': {'HARD': [{'level': 'HARD',
                                    'threshold_value': 'SYN-THRESHOLD-REF'}]}}
    assert cfg('validate_cross_file')(
        appcfg(redlines=redlines, anchor_set=_anchor(())),
        metric_ids=frozenset(METRICS), strategy_ids=frozenset(STRATEGIES)) is None


def test_t06_g08_load_all_does_not_wire_the_cross_file_gate(tmp_path):
    '''Ruling 2: "validate_cross_file ... load_all 不调用 (S1 无 csv 加载器);
    由 S3 preflight 调用", while validate_semantics is wired. B-029 pins the
    preflight side of the wiring for S9-T02.'''
    cfg('validate_cross_file')
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    body = _function_nodes(tree)['load_all']
    called = {_dotted(node.func) for node in ast.walk(body)
              if isinstance(node, ast.Call)}
    assert 'validate_semantics' in called, sorted(called)
    assert 'validate_cross_file' not in called, sorted(called)


def _function_nodes(tree):
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            found[node.name] = node
    return found


def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return base + '.' + node.attr if base else node.attr
    return ''

# ---------------------------------------------------------------------------
# T06-K. All violations at once, sorted by (SEMANTIC_CHECKS.index, path),
# deduplicated, never truncated, and the ruling 18 message (ruling 18).
# ---------------------------------------------------------------------------
def _four_breach_config():
    '''SUM_LEVEL1 + SUM_LEVEL2 + two ACTION_NON_EMPTY. Each one is a single
    violating position, so the total is decidable from ruling 18.'''
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': WEIGHT_EXACT, 'SYN-DIM-B': WEIGHT_EXACT,
        'SYN-DIM-C': WEIGHT_EXACT, 'SYN-DIM-D': WEIGHT_OVER_TOL})
    tree['level2_weights']['SYN-DIM-B'] = {METRICS[0]: WEIGHT_HALF,
                                           METRICS[1]: WEIGHT_SHORT_BY_TENTH}
    rules = _grade_rules()
    rules['levels'][1]['actions'] = []
    rules['levels'][3]['actions'] = ''
    return appcfg(weights=slot(tree), grade_rules=rules)


def test_t06_k01_every_breach_is_listed_in_one_exception():
    '''[L878] "不允许只报第一个" / ruling 18: N breaches, N triples.'''
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_semantics')(_four_breach_config())
    exc = excinfo.value
    assert len(exc.violations) == 4
    assert ids_of(exc) == ['SUM_LEVEL1', 'SUM_LEVEL2', 'ACTION_NON_EMPTY',
                           'ACTION_NON_EMPTY']
    assert_triples(exc, SEMANTIC_CHECKS)
    assert paths_of(exc)[2] < paths_of(exc)[3]


def test_t06_k02_the_message_head_names_the_count_and_the_exit_code():
    '''Ruling 18 message format, verbatim: first line
    "配置语义校验失败 N 项（退出码 3）".'''
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_semantics')(_four_breach_config())
    exc = excinfo.value
    lines = str(exc).splitlines()
    assert lines[0] == MSG_SEM_HEAD % (len(exc.violations),
                                       EXIT_CONFIG_EXPECTED)
    assert lines[0] == '配置语义校验失败 4 项（退出码 3）'
    assert_item_lines(exc)


def test_t06_k03_the_constructor_sorts_a_shuffled_input():
    '''Ruling 19: violations is "已按裁决 18 排序去重", so the normalisation
    lives in the constructor, not in the caller.'''
    shuffled = [('NUMERIC', 'p', 'd'), ('SUM_LEVEL2', 'q', 'd'),
                ('STRUCTURE', 'a', 'd'), ('SUM_LEVEL2', 'a', 'd'),
                ('ACTION_NON_EMPTY', 'z', 'd')]
    exc = cfg('ConfigSemanticError')(list(reversed(shuffled)))
    assert exc.violations == tuple(sorted(
        shuffled, key=lambda item: (SEMANTIC_CHECKS.index(item[0]), item[1])))


def test_t06_k04_the_constructor_deduplicates():
    item = ('SUM_LEVEL1', WEIGHTS_STEM_A + '.level1_weights', 'detail')
    exc = cfg('ConfigSemanticError')([item, item, item])
    assert exc.violations == (item,)


def test_t06_k05_a_large_breach_set_is_not_truncated():
    '''Ruling 18: "不截断、不限量".'''
    dims = {}
    for index in range(9):
        dims['SYN-DIM-%02d' % index] = {METRICS[0]: WEIGHT_HALF,
                                        METRICS[1]: WEIGHT_SHORT_BY_TENTH}
    tree = frozen_weights(level1_weights={
        dim: WEIGHT_HALF for dim in list(dims)[:3]}, level2_weights=dims)
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    exc = excinfo.value
    assert len(exc.violations) == 10
    assert set(ids_of(exc)) == {'SUM_LEVEL1', 'SUM_LEVEL2'}
    assert len(exc.violations) == len(set(exc.violations))


# ---------------------------------------------------------------------------
# T06-L. Numeric discipline: float / bool / blank / unparsable are NUMERIC
# violations inside ConfigSemanticError, never a leaked NumericError
# (rulings 6 / 7, H-4, [L1267]).
# ---------------------------------------------------------------------------
def test_t06_l01_a_float_weight_is_a_numeric_violation_not_a_numeric_error():
    '''Ruling 7: "遇 float / bool / 空串 / 不可解析串 -> 记 NUMERIC 违规
    (不抛 NumericError 出圈, 一律转成 ConfigSemanticError)".'''
    numeric = _numeric_module()
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': TYPE_PROBE_FLOAT, 'SYN-DIM-B': WEIGHT_EXACT,
        'SYN-DIM-C': WEIGHT_EXACT, 'SYN-DIM-D': WEIGHT_EXACT})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    exc = excinfo.value
    assert not isinstance(exc, numeric.NumericError)
    assert 'NUMERIC' in ids_of(exc)
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


@pytest.mark.parametrize('probe', [True, False], ids=['bool-true',
                                                      'bool-false'])
def test_t06_l02_a_bool_weight_is_a_numeric_violation(probe):
    numeric = _numeric_module()
    tree = frozen_weights(level1_weights={
        'SYN-DIM-A': probe, 'SYN-DIM-B': '1'})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    assert not isinstance(excinfo.value, numeric.NumericError)
    assert 'NUMERIC' in ids_of(excinfo.value)


def test_t06_l03_a_blank_weight_is_a_numeric_violation():
    tree = frozen_weights(level1_weights={'SYN-DIM-A': '', 'SYN-DIM-B': '1'})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    assert 'NUMERIC' in ids_of(excinfo.value)


def test_t06_l04_an_unparsable_weight_is_a_numeric_violation():
    tree = frozen_weights(level1_weights={'SYN-DIM-A': NUMERIC_GARBAGE,
                                          'SYN-DIM-B': '1'})
    with pytest.raises(semantic_error()) as excinfo:
        semantics_of(slot(tree))
    assert 'NUMERIC' in ids_of(excinfo.value)


@pytest.mark.parametrize('value', ['1', TYPE_PROBE_ONE],
                         ids=['decimal-string', 'int-one'])
def test_t06_l05_a_decimal_string_and_an_int_are_accepted(value):
    '''Ruling 7: "权重值 ... 必须是 int / str / Decimal". One dimension whose
    weight is the string one or the int one sums to exactly 1, so the only
    thing this case exercises is the accepted type, not the tolerance.'''
    tree = frozen_weights(level1_weights={'SYN-DIM-A': value},
                          level2_weights={'SYN-DIM-A': {METRICS[0]: '1'}})
    assert semantics_of(slot(tree)) is None


def test_t06_l06_to_decimal_returns_a_decimal_built_from_the_string():
    '''Ruling 19 / H-4 "字符串构造".'''
    assert cfg('to_decimal')(WEIGHT_EXACT, path='p') == Decimal('0.25')
    assert isinstance(cfg('to_decimal')(WEIGHT_EXACT, path='p'), Decimal)
    assert cfg('to_decimal')(TYPE_PROBE_ONE, path='p') == Decimal('1')


def test_t06_l07_to_decimal_rejects_a_float_with_config_semantic_error():
    numeric = _numeric_module()
    with pytest.raises(semantic_error()) as excinfo:
        cfg('to_decimal')(TYPE_PROBE_FLOAT, path='p')
    assert not isinstance(excinfo.value, numeric.NumericError)
    assert set(ids_of(excinfo.value)) == {'NUMERIC'}


@pytest.mark.parametrize('probe', [True, '', NUMERIC_GARBAGE],
                         ids=['bool', 'blank', 'garbage'])
def test_t06_l08_to_decimal_rejects_every_other_illegal_leaf(probe):
    with pytest.raises(semantic_error()) as excinfo:
        cfg('to_decimal')(probe, path='p')
    assert set(ids_of(excinfo.value)) == {'NUMERIC'}


def test_t06_l09_to_decimal_reports_the_path_it_was_given():
    '''Ruling 19: to_decimal(value, *, path) - the path is the violation
    position, so the caller owns the notation.'''
    with pytest.raises(semantic_error()) as excinfo:
        cfg('to_decimal')(TYPE_PROBE_FLOAT,
                          path=WEIGHTS_STEM_A + '.level1_weights.SYN-DIM-A')
    assert paths_of(excinfo.value)[0] == (
        WEIGHTS_STEM_A + '.level1_weights.SYN-DIM-A')


def test_t06_l10_a_float_attainment_floor_is_a_numeric_violation():
    '''Ruling 7 covers attainment_floor as well as the two weight levels.'''
    rules = _grade_rules()
    rules['levels'][0]['attainment_floor'] = TYPE_PROBE_FLOAT
    with pytest.raises(semantic_error()) as excinfo:
        semantics(grade_rules=rules)
    assert 'NUMERIC' in ids_of(excinfo.value)


def test_t06_l11_a_yaml_float_leaf_is_caught_at_the_load_hook(tmp_path):
    '''Ruling 7 / B-032: a bare decimal in the bank yaml is a NUMERIC
    violation raised by config, not a FloatNotAllowedError escaping it.'''
    numeric = _numeric_module()
    tree = _weights()
    tree['level1_weights']['SYN-DIM-A'] = TYPE_PROBE_FLOAT
    base = write_dir(tmp_path / 'cfg',
                       **file_trees(**{WEIGHTS_STEM_A: tree}))
    with pytest.raises(semantic_error()) as excinfo:
        cfg('load_all')(str(base))
    assert not isinstance(excinfo.value, numeric.FloatNotAllowedError)
    assert 'NUMERIC' in ids_of(excinfo.value)

# ---------------------------------------------------------------------------
# T06-M. Every raised reason_code is a registered RC member; dsm/config.py
# never spells a reason as a bare string (ruling 5, H-6 / H-7 / P-8).
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('scenario', SEMANTIC_SCENARIOS)
def test_t06_m01_semantic_violations_carry_the_registered_reason_code(scenario):
    '''Ruling 5: 六条语义判据任一违规、结构缺失、数值类型非法 ->
    RC.CONFIG_SEMANTIC_ERROR; ruling 19: reason_code is an attribute.'''
    with pytest.raises(semantic_error()) as excinfo:
        violating_semantic_call(scenario)()
    exc = excinfo.value
    registry = RC()
    assert isinstance(exc.reason_code, registry)
    assert exc.reason_code in list(registry)
    assert exc.reason_code is registry.CONFIG_SEMANTIC_ERROR
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_m02_config_source_never_spells_a_reason_code_as_a_string():
    '''Ruling 5: "禁止出现 'WEIGHT_VERSION_DRAFT' 一类裸字符串字面量"; the
    only legal spelling is the RC.<NAME> attribute access.'''
    cfg('ConfigSemanticError')
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    bare = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in T06_REASON_CODES:
                bare.add((node.lineno, node.value))
    assert bare == set()
    chains = {_dotted(node.value) for node in ast.walk(tree)
              if isinstance(node, ast.Attribute)}
    assert any(name == 'RC' or name.startswith('RC.') for name in chains), \
        sorted(chains)


def test_t06_m03_the_reason_code_keeps_the_rc_spelling_and_the_value():
    '''Ruling 5: str(RC.X) == 'RC.X' while CSV / hash output needs .value.'''
    registry = RC()
    with pytest.raises(semantic_error()) as excinfo:
        violating_semantic_call('sum_level1')()
    code = excinfo.value.reason_code
    assert str(code) == 'RC.CONFIG_SEMANTIC_ERROR'
    assert code.value == registry.CONFIG_SEMANTIC_ERROR.value
    assert code.value == 'CONFIG_SEMANTIC_ERROR'


# ---------------------------------------------------------------------------
# T06-N. The six new callables are pure (ruling 19 / H-8): no I/O, no wall
# clock, no global state, no input mutation, byte identical on rerun.
# ---------------------------------------------------------------------------
PURE_NAMES = ('to_decimal', 'period_key', 'validate_semantics',
              'validate_cross_file', 'select_weight_stem', 'validate_weights')

FORBIDDEN_CALLS = ('open', 'print', 'input', 'exec', 'eval', 'Path')
FORBIDDEN_PREFIXES = ('os.', 'io.', 'yaml.', 'pathlib.', 'time.',
                      'datetime.datetime.now', 'datetime.date.today')
WALL_CLOCKS = ('datetime.datetime.now', 'datetime.date.today', 'datetime.now',
               'date.today', 'time.time', 'time.monotonic', 'time.perf_counter')


def _call_paths(node):
    return [_dotted(sub.func) for sub in ast.walk(node)
            if isinstance(sub, ast.Call) and sub.func is not None]


def _purity_offenders(name):
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    fn = _function_nodes(tree).get(name)
    if fn is None:
        return [(name, 'not defined in dsm/config.py')]
    offenders = []
    for path in _call_paths(fn):
        if path in FORBIDDEN_CALLS or path in WALL_CLOCKS:
            offenders.append((name, path))
        elif any(path.startswith(prefix) for prefix in FORBIDDEN_PREFIXES):
            offenders.append((name, path))
    for sub in ast.walk(fn):
        if isinstance(sub, (ast.Global, ast.Nonlocal)):
            offenders.append((name, 'global state'))
    return offenders


def test_t06_n01_the_six_pure_functions_touch_no_io_no_clock_no_state():
    '''Ruling 19: "三个 validate_* 与 to_decimal / period_key /
    select_weight_stem 必须是纯函数 (H-8): 不 I/O、不读写全局状态、不取墙钟".'''
    for name in PURE_NAMES:
        assert callable(cfg(name)), name
    offenders = []
    for name in PURE_NAMES:
        offenders += _purity_offenders(name)
    assert offenders == [], repr(offenders)


def test_t06_n02_the_pure_functions_do_not_mutate_their_input():
    '''Ruling 19 "不修改入参": the caller keeps its own tree, byte for byte.'''
    app = appcfg()
    before = repr(app.model_dump())
    cfg('validate_semantics')(app)
    cfg('validate_cross_file')(app, metric_ids=frozenset(METRICS),
                               strategy_ids=frozenset(STRATEGIES))
    cfg('select_weight_stem')(app, period=PERIOD_OK)
    cfg('validate_weights')(app, period=PERIOD_OK)
    assert repr(app.model_dump()) == before
    tree = _weights()
    snapshot = copy.deepcopy(tree)
    cfg('validate_semantics')(appcfg(weights=slot(tree)))
    assert tree == snapshot


def test_t06_n03_two_identical_calls_are_byte_identical():
    '''Ruling 19 "同输入逐字节同输出" / V-3 reproducibility.'''
    err = semantic_error()
    app = _four_breach_config()

    def once():
        try:
            cfg('validate_semantics')(app)
        except err as caught:
            return repr(caught.violations) + '|' + str(caught.reason_code)
        raise AssertionError('the four breaches did not raise')

    assert once() == once()
    assert repr(cfg('period_key')(PERIOD_OK)) == repr(
        cfg('period_key')(PERIOD_OK))
    assert repr(cfg('to_decimal')(WEIGHT_EXACT, path='p')) == repr(
        cfg('to_decimal')(WEIGHT_EXACT, path='p'))
    assert cfg('select_weight_stem')(appcfg(), period=PERIOD_OK) == \
        cfg('select_weight_stem')(appcfg(), period=PERIOD_OK)


def test_t06_n04_period_key_never_reads_the_wall_clock():
    '''Ruling 8: "不得用 datetime.now() / date.today() 推断当前期"; period
    arrives as a parameter only (H-8).'''
    cfg('period_key')
    offenders = _purity_offenders('period_key')
    assert offenders == [], repr(offenders)
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    body = _function_nodes(tree)['period_key']
    assert not [path for path in _call_paths(body)
                if path in WALL_CLOCKS], _call_paths(body)

# ---------------------------------------------------------------------------
# T06-O. Layering (ruling 20, H-9 / INV-1): dsm/config.py stays L1 and keeps
# its import envelope. The names must also be hosted by that module.
# ---------------------------------------------------------------------------
def _imported_modules(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module != '__future__':
                found.append(node.module)
    return sorted(set(found))


def _imported_paths(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                found.append((node.module + '.' + alias.name)
                             if node.module else alias.name)
    return sorted(set(found))


def test_t06_o01_the_import_envelope_stays_inside_the_authorised_set():
    '''Ruling 20: config.py is L1; T06 may add dsm.numeric / dsm.reason_codes
    and nothing else outside the standard library, yaml and pydantic.'''
    for name in PURE_NAMES:
        assert callable(cfg(name)), name
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    offenders = []
    for module in _imported_modules(tree):
        top = module.split('.')[0]
        if module in AUTHORIZED_DSM_IMPORTS or module in AUTHORIZED_THIRD_PARTY:
            continue
        if top == 'dsm':
            offenders.append(module)
            continue
        if top in sys.stdlib_module_names:
            continue
        offenders.append(module)
    assert offenders == [], repr(offenders)


def test_t06_o02_models_l0a_l0b_and_io_loaders_are_zero_hits():
    '''Ruling 20 / INV-1: no dsm.models (the validation runs on the raw
    ConfigTree dicts), no L0a / L0b, no dsm.io_loaders (which does not exist
    in S1). Checked in the import graph and again in the identifier graph,
    because a bare `whatif` identifier would mean a real dependency.'''
    cfg('validate_semantics')
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    paths = _imported_paths(tree)
    for banned in ('dsm.models', 'dsm.io_loaders'):
        assert not any(item == banned or item.startswith(banned + '.')
                       for item in paths), repr(paths)
    offenders = []
    for item in paths:
        if item.split('.')[-1] in L0_MODULES:
            offenders.append(item)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    offenders += sorted(names & set(L0_MODULES))
    assert offenders == [], repr(offenders)


def test_t06_o03_the_new_names_are_hosted_by_dsm_config():
    '''Ruling 19: all eleven names belong to dsm/config.py, not to a helper
    module, so the single source of truth stays in one place.'''
    module = _config_module()
    for name in ('SEMANTIC_CHECKS', 'WEIGHT_CHECKS', 'EXIT_BLOCK'):
        assert cfg(name) is not None
        assert getattr(module, name) is not None
    for name in ('to_decimal', 'period_key', 'validate_semantics',
                 'validate_cross_file', 'select_weight_stem',
                 'validate_weights'):
        assert callable(cfg(name)), name
    for name in ('ConfigSemanticError', 'WeightVersionInvalidError'):
        assert cfg(name).__module__ == 'dsm.config', name


# ---------------------------------------------------------------------------
# T06-P. H-5 inside the config layer: zero business numbers, zero float
# literals, the tolerance only ever numeric.TOL, no K-nn token, and no
# PLACEHOLDER / K-nn default value in a T06 signature.
# ---------------------------------------------------------------------------
K_TOKEN = re.compile(r'K-[0-9][0-9]')
TOLERANCE_SPELLINGS = ('1e-12', '1E-12', '0.000000000001')


def _config_tree():
    return ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))


def _docstring_ids(tree):
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, 'body', [])
        if body:
            first = body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str):
                    found.add(id(first.value))
    return found


def test_t06_p01_config_source_carries_no_float_literal_at_all():
    '''Ruling 6: "禁止在 config.py 内出现 1e-12 / 0.000000000001 一类 float
    字面量 (H-4 + R4 的 float 扫描)". The T06 check tuple is what makes the
    tolerance necessary, so it is resolved first.'''
    cfg('SEMANTIC_CHECKS')
    cfg('WEIGHT_CHECKS')
    floats = [(node.lineno, node.value) for node in ast.walk(_config_tree())
              if isinstance(node, ast.Constant) and type(node.value) is float]
    assert floats == []


def test_t06_p02_the_tolerance_is_never_spelled_as_a_number():
    '''Ruling 6: the tolerance is numeric.TOL and nothing else, so neither a
    float literal nor a Decimal string of the same value may appear.'''
    cfg('SEMANTIC_CHECKS')
    source = CONFIG_PATH.read_text(encoding='utf-8')
    for spelling in TOLERANCE_SPELLINGS:
        assert source.count(spelling) == 0, spelling


def test_t06_p03_config_source_proposes_no_governance_number():
    '''Ruling 21 / [L78] / [L1259]: no K-nn token in a string literal, and no
    PLACEHOLDER / K-nn spelling used as a default value.'''
    cfg('SEMANTIC_CHECKS')
    tree = _config_tree()
    docstrings = _docstring_ids(tree)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings:
                continue
            if K_TOKEN.search(node.value):
                hits.append((node.lineno, node.value))
    assert hits == []
    for name in PURE_NAMES:
        fn = cfg(name)
        for parameter in inspect.signature(fn).parameters.values():
            if isinstance(parameter.default, str):
                assert not K_TOKEN.search(parameter.default), name
                assert 'PLACEHOLDER' not in parameter.default.upper(), name


def test_t06_p04_the_tolerance_is_only_ever_reached_through_numeric():
    '''Ruling 6 / ruling 20: any tolerance reference must be the numeric
    module's own TOL, so config.py can never drift away from S1-T01.'''
    cfg('SEMANTIC_CHECKS')
    tree = _config_tree()
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ('TOL', 'ONE',
                                                             'ZERO', 'eq_tol',
                                                             'D',
                                                             'weighted_sum'):
            base = _dotted(node.value)
            if base not in ('numeric', 'dsm.numeric', ''):
                offenders.append((node.lineno, base + '.' + node.attr))
    assert offenders == [], repr(offenders)


# ---------------------------------------------------------------------------
# T06-R. Ruling 22: the _join docstring gains the bracket completion note and
# nothing about _join / _walk behaviour changes.
# ---------------------------------------------------------------------------
def test_t06_r01_the_join_docstring_carries_the_bracket_completion_note():
    '''ORCH-23 ruling 22 / ORCH-24 ruling 22: "rel 以 [ 开头时
    join(root, rel) = root + rel (不插点)". The note must now be in the
    docstring; the behaviour itself is frozen and re-probed below, and T06
    violation paths ride the very same _join (ruling 14), which is why the
    first statement resolves a T06 name.'''
    cfg('validate_cross_file')
    tree = _config_tree()
    doc = ast.get_docstring(_function_nodes(tree)['_join']) or ''
    assert '[' in doc, doc
    assert ('开头' in doc or 'startswith' in doc.lower()
            or 'begins' in doc.lower()), doc
    assert cfg('find_placeholders')(['TODO', None], root='stem') == (
        'stem[0]', 'stem[1]')


@pytest.mark.parametrize('tree, root, expected', [
    ({'weight_construction': {'alpha_floor': 'PLACEHOLDER'}}, 'eval_config',
     ('eval_config.weight_construction.alpha_floor',)),
    ({'thresholds': ['SYN-OK', 'SYN-OK', 'PLACEHOLDER']}, 'eval_config',
     ('eval_config.thresholds[2]',)),
    ({'pairwise': [['SYN-OK', None], [None, 'SYN-OK']]}, 'ahp_matrices',
     ('ahp_matrices.pairwise[0][1]', 'ahp_matrices.pairwise[1][0]')),
    ({'dimensions': [{'metrics': ['SYN-OK', 'SYN-OK', 'SYN-OK',
                                 {'weight': 'PLACEHOLDER'}]}]},
     WEIGHTS_STEM_A, (WEIGHTS_STEM_A + '.dimensions[0].metrics[3].weight',)),
], ids=['nested-dict', 'list-index', 'nested-list', 'key-index-key'])
def test_t06_r02_the_walk_paths_are_unchanged(tree, root, expected):
    '''ORCH-23 ruling 8 / 22 regression: the T05 path notation cases still
    produce byte-identical paths after the ruling 22 docstring edit.'''
    cfg('SEMANTIC_CHECKS')
    assert cfg('find_placeholders')(tree, root=root) == expected


def test_t06_r03_a_violation_path_and_a_placeholder_path_agree():
    '''Ruling 14: "递归收集到的定位路径一律沿用 ORCH-23 裁决 8 的表示法", so
    the same position in the same tree is spelled identically by the T06
    violation path and by the frozen T05 placeholder walk.'''
    redlines = {'rules': {'HARD': [{'metric_id': GHOST_METRIC,
                                    'level': 'HARD',
                                    'threshold_value': 'SYN-THRESHOLD-REF'}]}}
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_cross_file')(appcfg(redlines=redlines),
                                   metric_ids=frozenset(METRICS),
                                   strategy_ids=frozenset(STRATEGIES))
    violation_path = paths_of(excinfo.value)[0]
    probe = copy.deepcopy(redlines)
    probe['rules']['HARD'][0]['metric_id'] = 'PLACEHOLDER'
    walked = cfg('find_placeholders')(probe, root='redlines')
    assert walked == (violation_path,), walked
