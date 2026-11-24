'''RED tests for the S1-T06 weight version half of dsm/config.py (RED by design).

Contract authority = docs/adr/ORCH-24.md rulings 8 / 15 / 16 / 17 / 18 / 19 /
21 plus the section 8 checklist rows T06-H, T06-I, T06-J and the version
related halves of T06-K / L / M / N. The SDD wording is carried by
docs/digest/S1-T06.md: [L880] (status 必须为 FROZEN; 评价期落在
[effective_from, effective_to]; 缺 whatif_run_id 而 status = FROZEN -> 加载
失败), [L1190]-[L1194], [L1228]-[L1245], [L1241]-[L1242], [L1280]-[L1282],
[L1372]-[L1374], [L1413] (G-11(a) preflight BLOCK code = STALE), [L1435]
(P-11), [L900] (C-01 BLOCK 退出码 2), [L150]-[L154], [L379]-[L380], [L386],
[L678]-[L679], [L1307]. The frozen T05 side is ORCH-23 rulings 3 / 8 / 9 / 11 /
19; nothing in that contract is redefined or re-asserted with a different value.

Case ids: test_t06_h.. / i.. / j.. for the three version rows, and 60+
numbering inside k / l / m / n so a group stays greppable and an id never
collides with tests/test_config_semantic.py.

Why every case is RED for exactly one reason: none of the eleven T06 public
names exists yet in dsm/config.py, and load_all does not take period / run_at
(ORCH-24 ruling 19). References are lazy (_config_module / cfg), so pytest
collects with zero errors and each failure is an AttributeError (a name of
ruling 19 is missing) or a TypeError (load_all rejects the new keyword, or a
required keyword-only argument is missing per ruling 2). No SyntaxError, no
NameError from a mistyped local, no fixture error, no inverted expectation.
Per H-11 every expected value is read off the ruling quoted next to the
assertion; no expectation was copied from a run.

Scope discipline (ruling 1): weight version validation at load time only. No
C-01 preflight orchestration, no C-02 re-normalisation, no C-03 orphan
weights, no C-10 anchor staleness / version_id / rank reversal, no
audit_bundle, no score_card suppression.

Data (ruling 21 / H-5 / H-14): synthetic SYN- keys everywhere. Periods are
calendar test data in the [L386] / [L1536] YYYY-MM shape plus the [L889] ISO
day shape that ruling 8 also accepts. The CR and alpha slots hold a parseable
synthetic string and nothing more, because ruling 17 judges existence only and
H-5 forbids inventing a CR threshold or an alpha range (B-041 / B-042). Files
are written under pytest tmp_path; the repository config/ directory is never
touched.
'''
import ast
import copy
import datetime
import importlib
import inspect
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / 'dsm' / 'config.py'
THIS_PATH = Path(__file__).resolve()


def _config_module():
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
    return importlib.import_module('dsm.reason_codes').RC


# ---------------------------------------------------------------------------
# Contract constants (rulings 4 / 5 / 15 / 17 / 18 / 19).
# ---------------------------------------------------------------------------
EXIT_BLOCK_EXPECTED = 2
EXIT_CONFIG_EXPECTED = 3
WEIGHT_CHECKS = ('WEIGHT_COVERAGE', 'WEIGHT_STATUS_FROZEN',
                 'WEIGHT_WHATIF_RUN_ID', 'WEIGHT_PROVENANCE_COMPLETE',
                 'WEIGHT_APPROVAL', 'STRUCTURE', 'NUMERIC')
SEMANTIC_CHECKS = ('SUM_LEVEL1', 'SUM_LEVEL2', 'FLOOR_MONOTONIC',
                   'REDLINE_METRIC_EXISTS', 'ACTION_NON_EMPTY',
                   'ANCHOR_MEMBER_EXISTS', 'STRUCTURE', 'NUMERIC')
MSG_WEIGHT_HEAD = '权重版本校验失败 %d 项（退出码 %d，%s）'

WEIGHTS_STEM_A = 'weights_WV-SYN-0001'
WEIGHTS_STEM_B = 'weights_WV-SYN-0002'
DIMS = ('SYN-DIM-A', 'SYN-DIM-B', 'SYN-DIM-C', 'SYN-DIM-D')
METRICS = ('SYN-M-01', 'SYN-M-02')
STRATEGIES = ('SYN-S-001', 'SYN-S-002')
GRADES = ('L1', 'L2', 'L3', 'L4')
FLOORS_OK = ('0.9', '0.75', '0.6', '0.4')
WEIGHT_EXACT = '0.25'
WEIGHT_HALF = '0.5'

STATUS_FROZEN = 'FROZEN'
STATUS_DRAFT = 'DRAFT'
STATUS_THIRD = 'SYN-STATUS-THIRD-VALUE'
KIND_AHP_ONLY = 'AHP_ONLY'
KIND_COMBINED = 'AHP_ENTROPY_COMBINED'
KIND_EXPERT_ONLY = 'EXPERT_ONLY'

PERIOD_OK = '2026-10'
PERIOD_FROM = '2026-01'
PERIOD_TO = '2026-12'
PERIOD_BEFORE_FROM = '2025-12'
PERIOD_AFTER_TO = '2026-11'
PERIOD_DAY_INSIDE = '2026-10-15'
PERIOD_MONTH_END = '2026-10'
PERIOD_INVALID_MONTH = '2026-13'
PERIOD_INVALID_DAY = '2026-10-32'
PERIOD_TWO_DIGIT_YEAR = '26-10'
PERIOD_BARE_INT = 202610      # type probe: not one of the three legal forms
DATE_IN_PERIOD = datetime.date(2026, 10, 1)
DATETIME_IN_PERIOD = datetime.datetime(2026, 10, 1, 9, 30)

WHATIF_RUN_ID = 'SYN-WHATIF-RUN'
APPROVED_BY = 'SYN-APPROVER'
APPROVED_DATE = '2026-01-05'
CR_PRESENT = '0.25'      # parseable only, ruling 17
ALPHA_PRESENT = '0.25'   # parseable only, ruling 17
CR_LARGE = '0.99'        # existence is the whole judgement (B-041)
ALPHA_LARGE = '0.99'     # existence is the whole judgement (B-042)
NON_STRING_RUN_ID = ['SYN-NOT-A-STRING']   # ruling 18 type branch probe
WEIGHT_OVER_TOL = '0.250000000002'  # 0.25 + 2e-12, outside numeric.TOL
PERIOD_EXPIRED = '2026-06'   # an effective_to that is past its month
NUMERIC_GARBAGE = 'abc'      # unparsable decimal probe (ruling 7)
TYPE_PROBE_FLOAT_CR = 0.25   # 仅类型探针，非业务值 (ruling 7 float branch)
T06_VERSION_REASON_CODES = ('WEIGHT_VERSION_DRAFT',
                            'WEIGHT_VERSION_STALE',
                            'WEIGHT_MISSING_WHATIF_RUN_ID',
                            'WEIGHT_VERSION_INVALID')


def _level1():
    return {dim: WEIGHT_EXACT for dim in DIMS}


def _level2():
    return {dim: {METRICS[0]: WEIGHT_HALF, METRICS[1]: WEIGHT_HALF}
            for dim in DIMS}


def _provenance(kind=KIND_AHP_ONLY):
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


def _weights(stem=WEIGHTS_STEM_A, status=STATUS_FROZEN, kind=KIND_AHP_ONLY,
             effective_from=PERIOD_FROM, effective_to=PERIOD_TO):
    return {
        'weight_version_id': stem,
        'status': status,
        'effective_from': effective_from,
        'effective_to': effective_to,
        'level1_weights': _level1(),
        'level2_weights': _level2(),
        'provenance': _provenance(kind),
    }


def _grade_rule(grade, floor):
    return {'grade_code': grade, 'attainment_floor': floor,
            'actions': ['SYN-ACTION-01'], 'action_gate': 'SYN-ACTION-GATE'}


def _grade_rules():
    return {'levels': [_grade_rule(code, floor)
                       for code, floor in zip(GRADES, FLOORS_OK)]}


def _redlines():
    return {'rules': {'HARD': [{'metric_id': metric, 'level': 'HARD',
                                'threshold_value': 'SYN-THRESHOLD-REF'}
                               for metric in METRICS]}}


def _anchor():
    return {'anchor_set_id': 'SYN-ANCHOR-0001',
            'strategy_ids': list(STRATEGIES), 'effective_from': PERIOD_FROM,
            'effective_to': PERIOD_TO, 'rationale': 'SYN-RATIONALE'}


def payload(**overrides):
    built = {'eval_config': {'SYN-evidence_mode': 'SYN-EVIDENCE-MODE'},
             'weights': {WEIGHTS_STEM_A: _weights()},
             'redlines': _redlines(),
             'grade_rules': _grade_rules(),
             'anchor_set': _anchor(),
             'ahp_matrices': {'matrices': {'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'}}}
    built.update(overrides)
    return built


def appcfg(**overrides):
    return cfg('AppConfig')(**payload(**overrides))


def slot(tree, stem=WEIGHTS_STEM_A):
    return {stem: tree}


def one_tree(**segments):
    '''The default FROZEN covering tree with top level segments replaced.'''
    tree = _weights()
    tree.update(segments)
    return tree


def prov_of(tree):
    return tree['provenance']


def check_weights(weights, period=PERIOD_OK, app=None):
    '''validate_weights(cfg, *, period) (ruling 19, period required).'''
    return cfg('validate_weights')(appcfg(weights=weights), period=period)


def select_stem(weights, period=PERIOD_OK):
    return cfg('select_weight_stem')(appcfg(weights=weights), period=period)


def weight_error():
    return cfg('WeightVersionInvalidError')


def semantic_error():
    return cfg('ConfigSemanticError')


def ids_of(exc):
    return [item[0] for item in exc.violations]


def paths_of(exc):
    return [item[1] for item in exc.violations]


def assert_triples(exc, checks):
    for item in exc.violations:
        assert isinstance(item, tuple) and len(item) == 3, repr(item)
        assert all(isinstance(part, str) for part in item), repr(item)
    keys = [(checks.index(item[0]), item[1]) for item in exc.violations]
    assert keys == sorted(keys), repr(keys)
    assert len(exc.violations) == len(set(exc.violations))


def file_trees(**overrides):
    '''The {file stem: tree} view of the six slots (ORCH-23 ruling 3).'''
    built = {'eval_config': {'SYN-evidence_mode': 'SYN-EVIDENCE-MODE'},
             WEIGHTS_STEM_A: _weights(),
             'redlines': _redlines(),
             'grade_rules': _grade_rules(),
             'anchor_set': _anchor(),
             'ahp_matrices': {'matrices': {'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'}}}
    built.update(overrides)
    return built


def write_dir(base, **overrides):
    trees = file_trees(**overrides)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    for stem, tree in trees.items():
        (base / (stem + '.yaml')).write_text(
            yaml.safe_dump(tree, allow_unicode=True, sort_keys=False),
            encoding='utf-8')
    return base

# ---------------------------------------------------------------------------
# Scenario table for the parametrised reason_code / exit_code gates. The
# expected code of every branch is read straight off the fixed judgement
# order of ruling 15 (序 1 - 序 7); the period is always inside the interval
# except in the two coverage branches.
# ---------------------------------------------------------------------------
WEIGHT_SCENARIOS = (
    'stale_after_to', 'stale_before_from', 'no_weights_at_all',
    'two_versions_covering', 'selected_draft', 'third_status_value',
    'missing_whatif_key', 'blank_whatif_value', 'whitespace_whatif_value',
    'missing_approved_by', 'blank_approved_by', 'missing_approved_date',
    'missing_provenance_key', 'gap_ahp_segment', 'empty_comparison_matrices',
    'gap_cr', 'gap_entropy_segment', 'gap_combine_segment', 'gap_alpha',
    'gap_alpha_basis', 'kind_expert_without_ahp')

WEIGHT_SCENARIO_REASONS = {
    'no_weights_at_all': 'WEIGHT_VERSION_INVALID',
    'two_versions_covering': 'WEIGHT_VERSION_INVALID',
    'stale_after_to': 'WEIGHT_VERSION_STALE',
    'stale_before_from': 'WEIGHT_VERSION_STALE',
    'selected_draft': 'WEIGHT_VERSION_DRAFT',
    'third_status_value': 'WEIGHT_VERSION_INVALID',
    'missing_whatif_key': 'WEIGHT_MISSING_WHATIF_RUN_ID',
    'blank_whatif_value': 'WEIGHT_MISSING_WHATIF_RUN_ID',
    'whitespace_whatif_value': 'WEIGHT_MISSING_WHATIF_RUN_ID',
    'missing_approved_by': 'WEIGHT_VERSION_INVALID',
    'blank_approved_by': 'WEIGHT_VERSION_INVALID',
    'missing_approved_date': 'WEIGHT_VERSION_INVALID',
    'missing_provenance_key': 'WEIGHT_VERSION_INVALID',
    'gap_ahp_segment': 'WEIGHT_VERSION_INVALID',
    'empty_comparison_matrices': 'WEIGHT_VERSION_INVALID',
    'gap_cr': 'WEIGHT_VERSION_INVALID',
    'gap_entropy_segment': 'WEIGHT_VERSION_INVALID',
    'gap_combine_segment': 'WEIGHT_VERSION_INVALID',
    'gap_alpha': 'WEIGHT_VERSION_INVALID',
    'gap_alpha_basis': 'WEIGHT_VERSION_INVALID',
    'kind_expert_without_ahp': 'WEIGHT_VERSION_INVALID',
}


def _breach_tree(name):
    '''A covering FROZEN weights tree carrying exactly the named breach.'''
    tree = _weights()
    if name == 'stale_after_to':
        tree['effective_to'] = PERIOD_EXPIRED
    elif name == 'stale_before_from':
        tree['effective_from'] = PERIOD_AFTER_TO
        tree['effective_to'] = '2026-12'
    elif name == 'selected_draft':
        tree['status'] = STATUS_DRAFT
    elif name == 'third_status_value':
        tree['status'] = STATUS_THIRD
    elif name == 'missing_whatif_key':
        tree['provenance'].pop('whatif_run_id')
    elif name == 'blank_whatif_value':
        tree['provenance']['whatif_run_id'] = ''
    elif name == 'whitespace_whatif_value':
        tree['provenance']['whatif_run_id'] = '   '
    elif name == 'missing_approved_by':
        tree['provenance'].pop('approved_by')
    elif name == 'blank_approved_by':
        tree['provenance']['approved_by'] = '  '
    elif name == 'missing_approved_date':
        tree['provenance'].pop('approved_date')
    elif name == 'missing_provenance_key':
        tree.pop('provenance')
    elif name == 'gap_ahp_segment':
        tree['provenance'].pop('ahp')
    elif name == 'empty_comparison_matrices':
        tree['provenance']['ahp'] = {'comparison_matrices': {},
                                     'cr': CR_PRESENT}
    elif name == 'gap_cr':
        tree['provenance']['ahp'] = {'comparison_matrices': {
            'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'}}
    elif name == 'gap_entropy_segment':
        tree = _weights(kind=KIND_COMBINED)
        tree['provenance'].pop('entropy')
    elif name == 'gap_combine_segment':
        tree = _weights(kind=KIND_COMBINED)
        tree['provenance'].pop('combine')
    elif name == 'gap_alpha':
        tree = _weights(kind=KIND_COMBINED)
        tree['provenance']['combine'] = {}
    elif name == 'gap_alpha_basis':
        tree = _weights(kind=KIND_COMBINED)
        tree['provenance'].pop('alpha_basis')
    elif name == 'kind_expert_without_ahp':
        tree = _weights(kind=KIND_EXPERT_ONLY)
        tree['provenance'].pop('ahp')
    else:
        raise KeyError(name)
    return tree


def _scenario(name):
    '''The (weights mapping, period) pair of one version level breach.'''
    if name == 'no_weights_at_all':
        return {}, PERIOD_OK
    if name == 'two_versions_covering':
        return ({WEIGHTS_STEM_A: _weights(),
                 WEIGHTS_STEM_B: _weights(WEIGHTS_STEM_B)}, PERIOD_OK)
    return slot(_breach_tree(name)), PERIOD_OK


def violating_weight_call(name):
    '''A zero argument callable that must raise WeightVersionInvalidError.'''
    weights, period = _scenario(name)
    return lambda: check_weights(weights, period)


# ---------------------------------------------------------------------------
# T06-H. Version judgement order, reason codes and exit code 2 (rulings 15 /
# 16 / 4, [L880] / [L1280] / [L1281] / [L1374] / [L1413]).
# ---------------------------------------------------------------------------
def test_t06_h01_no_version_covers_the_period_is_stale():
    '''Ruling 15 序 2: covering count 0 -> RC.WEIGHT_VERSION_STALE; [L1413]
    G-11(a) spells the same outcome for "period 超出 effective_to".'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(one_tree(effective_to=PERIOD_EXPIRED)))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_STALE
    assert exc.exit_code == EXIT_BLOCK_EXPECTED
    assert exc.exit_code == cfg('EXIT_BLOCK')
    assert len(exc.violations) >= 1
    assert set(ids_of(exc)) <= set(WEIGHT_CHECKS)
    assert exc.reason_code.value == 'WEIGHT_VERSION_STALE'


def test_t06_h02_no_weights_document_at_all_is_invalid():
    '''Ruling 15 序 1: an empty cfg.weights -> RC.WEIGHT_VERSION_INVALID, the
    defensive redundancy over ORCH-23 ruling 10.'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights({})
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_INVALID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h03_two_covering_versions_are_invalid_in_stem_order():
    '''Ruling 15 序 3 (B-039: 保守判失败) + ruling 16: several covering
    versions are one collection whose stem order follows ORCH-23 ruling 9.'''
    pair = {WEIGHTS_STEM_B: _weights(WEIGHTS_STEM_B),
            WEIGHTS_STEM_A: one_tree()}
    with pytest.raises(weight_error()) as excinfo:
        check_weights(pair)
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_INVALID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED
    assert len(exc.violations) == 2
    assert paths_of(exc)[0].startswith(WEIGHTS_STEM_A)
    assert paths_of(exc)[1].startswith(WEIGHTS_STEM_B)
    assert_triples(exc, WEIGHT_CHECKS)


def test_t06_h04_the_selected_version_in_draft_is_a_draft_breach():
    '''Ruling 15 序 4: [L880] / [L1190] / [L1280] -> WEIGHT_VERSION_DRAFT.'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(one_tree(status=STATUS_DRAFT)))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_DRAFT
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h05_a_third_status_value_is_a_version_breach():
    '''Ruling 15 序 4 right branch: "RC.WEIGHT_VERSION_INVALID (其他值)".'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(one_tree(status=STATUS_THIRD)))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_h06_frozen_without_whatif_run_id_is_blocked():
    '''[L1374] / [L678] / [L880] / [L1281] / ruling 15 序 5: the key is
    absent -> RC.WEIGHT_MISSING_WHATIF_RUN_ID, exit code 2 ([L900] C-01).'''
    tree = one_tree()
    tree['provenance'].pop('whatif_run_id')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_MISSING_WHATIF_RUN_ID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


@pytest.mark.parametrize('blank', ['', '   ', '\t'],
                         ids=['empty', 'spaces', 'tab'])
def test_t06_h07_a_blank_whatif_run_id_is_the_same_breach(blank):
    '''Ruling 15 序 5: "缺 whatif_run_id (或 strip 后为空)". The empty and the
    whitespace-only string are filled values for the T05 scan (ORCH-23
    ruling 19), so only T06 can be the one rejecting them.'''
    tree = one_tree()
    tree['provenance']['whatif_run_id'] = blank
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_MISSING_WHATIF_RUN_ID


def test_t06_h08_a_non_string_whatif_run_id_is_a_structure_breach():
    '''Ruling 18: "config 层要求 isinstance(value, str); 非 str -> STRUCTURE
    违规". A type problem, so exit code 3 per the ruling 15 dividing line
    ("结构/类型问题一律 3, 版本策略问题一律 2").'''
    tree = one_tree()
    tree['provenance']['whatif_run_id'] = NON_STRING_RUN_ID
    with pytest.raises(semantic_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert 'STRUCTURE' in ids_of(exc)


@pytest.mark.parametrize('name', WEIGHT_SCENARIOS)
def test_t06_h09_the_version_breach_exit_code_is_always_two(name):
    '''Ruling 4: every version policy breach exits 2 (EXIT_BLOCK), whatever
    the reason_code. [L1280] / [L900] / [L1413].'''
    registry = RC()
    with pytest.raises(weight_error()) as excinfo:
        violating_weight_call(name)()
    exc = excinfo.value
    assert exc.exit_code == EXIT_BLOCK_EXPECTED
    assert exc.exit_code == cfg('EXIT_BLOCK')
    assert isinstance(exc.reason_code, registry)
    assert exc.reason_code is registry[WEIGHT_SCENARIO_REASONS[name]]


def test_t06_h10_a_breached_version_never_reaches_an_appconfig(tmp_path):
    '''[L1091] "退出码非 0 不得产出 score_card" starts one stage earlier: the
    load entry returns nothing at all when the covering version is DRAFT
    ([L1190]).'''
    produced = []
    trees = file_trees()
    trees[WEIGHTS_STEM_A]['status'] = STATUS_DRAFT
    base = write_dir(tmp_path / 'cfg', **trees)
    with pytest.raises(weight_error()):
        produced.append(cfg('load_all')(str(base), period=PERIOD_OK))
    assert produced == []


def test_t06_h11_the_first_hit_decides_the_reason_code():
    '''Ruling 15: "全部违规一次性收集, 但 reason_code 取首个命中的那条" - 序 4
    (DRAFT) outranks 序 5 (missing whatif_run_id) and 序 6 (provenance gaps).'''
    tree = _weights(status=STATUS_DRAFT)
    tree['provenance'].pop('whatif_run_id')
    tree['provenance'].pop('ahp')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_DRAFT


def test_t06_h12_coverage_outranks_every_provenance_gap():
    '''Ruling 15 序 2 before 序 6: an expired period is reported as STALE
    even when the provenance is broken too.'''
    tree = _weights(effective_to=PERIOD_EXPIRED)
    tree['provenance'].pop('ahp')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_STALE


def test_t06_h13_a_missing_status_key_is_a_structure_breach():
    '''Ruling 15: "缺 effective_from / effective_to / status / provenance 键
    -> STRUCTURE 违规, 抛 ConfigSemanticError" - exit code 3.'''
    tree = one_tree()
    tree.pop('status')
    with pytest.raises(semantic_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert 'STRUCTURE' in ids_of(exc)


def test_t06_h14_a_missing_interval_key_is_a_structure_breach():
    tree = one_tree()
    tree.pop('effective_to')
    with pytest.raises(semantic_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert 'STRUCTURE' in ids_of(exc)


def test_t06_h15_select_weight_stem_returns_the_one_covering_stem():
    '''Ruling 16: the unique covering stem, i.e. the cfg.weights key, which is
    the file stem of the weights_*.yaml document (ORCH-23 ruling 3).'''
    assert select_stem(slot(one_tree())) == WEIGHTS_STEM_A
    other = _weights(WEIGHTS_STEM_B)
    assert select_stem(slot(other, stem=WEIGHTS_STEM_B)) == WEIGHTS_STEM_B


def test_t06_h16_select_weight_stem_blocks_zero_coverage():
    '''Ruling 16: "为可测性, select_weight_stem 自身在 0 份 / >= 2 份时抛
    WeightVersionInvalidError (reason_code 按裁决 15 序 2 / 序 3)".'''
    with pytest.raises(weight_error()) as excinfo:
        select_stem(slot(one_tree(effective_to=PERIOD_EXPIRED)))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_STALE
    assert excinfo.value.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h17_select_weight_stem_blocks_two_covering_versions():
    pair = {WEIGHTS_STEM_A: one_tree(), WEIGHTS_STEM_B: _weights(
        WEIGHTS_STEM_B)}
    with pytest.raises(weight_error()) as excinfo:
        select_stem(pair)
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID
    assert excinfo.value.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h18_validate_weights_requires_the_period():
    '''Ruling 2 / ruling 19: period is required without default, so forgetting
    it is a TypeError, never a silent skip (V-14 forbids the silent way).'''
    with pytest.raises(TypeError):
        cfg('validate_weights')(appcfg())
    with pytest.raises(TypeError):
        cfg('select_weight_stem')(appcfg())


def test_t06_h19_load_all_without_period_still_blocks_a_frozen_gap(tmp_path):
    '''Ruling 15: with period=None load_all does not call validate_weights but
    keeps the period free constraints, because [L1374] reads "下次 config
    加载直接失败", which is a statement about any load.'''
    trees = file_trees()
    trees[WEIGHTS_STEM_A]['provenance'].pop('whatif_run_id')
    base = write_dir(tmp_path / 'cfg', **trees)
    with pytest.raises(weight_error()) as excinfo:
        cfg('load_all')(str(base))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_MISSING_WHATIF_RUN_ID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h20_load_all_without_period_checks_the_status_enum(tmp_path):
    '''Ruling 15: "对每一份 weights 树校验 status 枚举合法 (属于 {DRAFT,
    FROZEN}, 否则 STRUCTURE)" - a type problem, so exit code 3.'''
    trees = file_trees()
    trees[WEIGHTS_STEM_A]['status'] = STATUS_THIRD
    base = write_dir(tmp_path / 'cfg', **trees)
    with pytest.raises(semantic_error()) as excinfo:
        cfg('load_all')(str(base))
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert 'STRUCTURE' in ids_of(exc)


def test_t06_h21_load_all_dispatches_validate_weights_for_a_period(tmp_path):
    '''Ruling 2 / ruling 15: "period is not None -> 调 validate_weights
    (其内部已含上述两项, 不得重复报)" - one exception, exit code 2.'''
    trees = file_trees()
    trees[WEIGHTS_STEM_A]['effective_to'] = PERIOD_EXPIRED
    base = write_dir(tmp_path / 'cfg', **trees)
    with pytest.raises(weight_error()) as excinfo:
        cfg('load_all')(str(base), period=PERIOD_OK)
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_STALE
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_h22_run_at_is_accepted_and_not_used(tmp_path):
    '''Ruling 15 / ORCH-23 ruling 11: run_at is the reserved injection point,
    "本期只接受不使用"; H-8 keeps the wall clock out of the judgement, so the
    two loads must agree byte for byte.'''
    base = write_dir(tmp_path / 'cfg')
    plain = cfg('load_all')(str(base), period=PERIOD_OK)
    injected = cfg('load_all')(str(base), period=PERIOD_OK,
                               run_at=DATETIME_IN_PERIOD)
    assert repr(injected.model_dump()) == repr(plain.model_dump())


def test_t06_h23_load_all_takes_period_as_a_keyword_only(tmp_path):
    '''Ruling 19: load_all(config_dir, *, period=None, run_at=None) - the star
    is part of the contract, so a positional period stays a TypeError while
    the keyword form is accepted. Today the keyword form is the missing half,
    hence TypeError: unexpected keyword argument period.'''
    base = write_dir(tmp_path / 'cfg')
    with pytest.raises(TypeError):
        cfg('load_all')(str(base), PERIOD_OK)
    assert cfg('load_all')(str(base), period=PERIOD_OK) is not None


# ---------------------------------------------------------------------------
# T06-I. Closed interval, three accepted shapes, strict month alignment
# (ruling 8: [L880] brackets, [L1413], [L889], [L386], [L1307]).
# ---------------------------------------------------------------------------
def test_t06_i01_a_period_equal_to_effective_from_is_inside():
    '''Ruling 8: 双闭区间 from <= period <= to ([L880] bracket notation).'''
    assert check_weights(slot(one_tree(effective_from=PERIOD_OK))) is None


def test_t06_i02_a_period_equal_to_effective_to_is_inside():
    '''[L1413] only calls "period 超出 effective_to" stale, so the very day
    of the end point is still inside.'''
    assert check_weights(slot(one_tree(effective_to=PERIOD_OK))) is None


def test_t06_i03_a_single_month_span_holds_its_own_period():
    '''[L1191] "期内权重不变": one month of validity is legal, and the period
    equal to it is inside on both sides at once.'''
    tree = one_tree(effective_from=PERIOD_OK, effective_to=PERIOD_OK)
    assert check_weights(slot(tree)) is None
    assert select_stem(slot(tree)) == WEIGHTS_STEM_A


def test_t06_i04_a_month_key_and_a_day_key_are_equivalent():
    '''Ruling 8: "YYYY-MM -> YYYY-MM-01", so the month form and the day form
    of the first of that month are the same key.'''
    key = cfg('period_key')
    assert key(PERIOD_OK) == key('2026-10-01')
    assert key('2026-10-01') == '2026-10-01'
    assert key(PERIOD_OK) == '2026-10-01'


def test_t06_i05_a_date_object_and_a_day_string_are_equivalent():
    '''Ruling 8: yaml.safe_load turns an ISO date into datetime.date, so both
    shapes have to normalise to the same key ("date/datetime -> isoformat").'''
    key = cfg('period_key')
    assert key(DATE_IN_PERIOD) == key('2026-10-01')
    assert key(DATE_IN_PERIOD) == DATE_IN_PERIOD.isoformat()


def test_t06_i06_a_datetime_normalises_through_isoformat():
    '''Ruling 8 keeps the full isoformat of a datetime; the comparison is
    lexicographic, so the time part neither breaks nor is invented away.'''
    assert cfg('period_key')(DATETIME_IN_PERIOD) == '2026-10-01T09:30:00'


@pytest.mark.parametrize('period', [PERIOD_OK, '2026-10-01', DATE_IN_PERIOD],
                         ids=['month', 'day-string', 'date-object'])
def test_t06_i07_the_three_accepted_shapes_all_select_the_version(period):
    '''Ruling 8: coverage must not depend on which of the three shapes the
    caller injected.'''
    assert check_weights(slot(one_tree()), period=period) is None
    assert select_stem(slot(one_tree()), period=period) == WEIGHTS_STEM_A


def test_t06_i08_a_period_after_a_month_end_is_stale():
    '''Ruling 8 worked example: period 2026-11 against to 2026-10 gives
    2026-11-01 > 2026-10-01, hence STALE.'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(one_tree(effective_from=PERIOD_FROM,
                                    effective_to=PERIOD_MONTH_END)),
                      period=PERIOD_AFTER_TO)
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_STALE


def test_t06_i09_a_daily_period_past_a_month_end_is_stale():
    '''Ruling 8 / B-033, the deliberately strict side: "仅在 period 为日粒度
    而端点为月粒度时偏严判 STALE". 2026-10-15 is inside October on a calendar
    but the month end normalises to 2026-10-01, and [L1307] "宁可不评, 不可
    错评" pins the strict reading.'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(one_tree(effective_from=PERIOD_FROM,
                                    effective_to=PERIOD_MONTH_END)),
                      period=PERIOD_DAY_INSIDE)
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_STALE
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


@pytest.mark.parametrize('bad', [PERIOD_INVALID_MONTH, PERIOD_INVALID_DAY,
                                 PERIOD_TWO_DIGIT_YEAR, PERIOD_BARE_INT],
                         ids=['month-13', 'day-32', 'two-digit-year',
                              'bare-int'])
def test_t06_i10_an_illegal_period_shape_is_a_structure_violation(bad):
    '''Ruling 8: a form that is neither date / datetime nor a calendar valid
    YYYY-MM / YYYY-MM-DD is STRUCTURE, raised as ConfigSemanticError because
    "结构/类型问题一律 3". Month 13 and day 32 satisfy the bare digit pattern
    but are not dates: the conservative superset of ruling 0 (2) / [L1307]
    decides against accepting a form no calendar can resolve.'''
    with pytest.raises(semantic_error()) as excinfo:
        cfg('period_key')(bad)
    exc = excinfo.value
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert set(ids_of(exc)) == {'STRUCTURE'}


def test_t06_i11_a_whitespace_wrapped_period_is_stripped_not_rejected():
    '''Ruling 8: "YYYY-MM-DD -> 原样 (strip 后)".'''
    assert cfg('period_key')('  2026-10-01  ') == '2026-10-01'
    assert cfg('period_key')(' 2026-10') == '2026-10-01'


def test_t06_i12_a_mixed_month_and_day_span_is_compared_on_one_key():
    '''Ruling 8: coverage is period_key(from) <= period_key(period) <=
    period_key(to), string order on the normalised keys.'''
    tree = one_tree(effective_from='2026-10-01', effective_to='2026-12-31')
    assert check_weights(slot(tree)) is None
    assert check_weights(slot(tree), period='2026-12-31') is None
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree), period='2026-09-30')
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_STALE

# ---------------------------------------------------------------------------
# T06-J. P-11 provenance completeness: the kind conditional required-segment
# matrix (ruling 17, [L1435] verbatim "任何 FROZEN 权重版本必须具备完整
# provenance (AHP 矩阵 + CR; 若 combined 则含 alpha + alpha_basis +
# whatif_run_id), 缺任一项 -> 配置加载失败").
# ---------------------------------------------------------------------------
def test_t06_j01_ahp_only_with_a_complete_provenance_passes():
    tree = _weights(kind=KIND_AHP_ONLY)
    assert check_weights(slot(tree)) is None


def test_t06_j02_expert_only_with_a_complete_provenance_passes():
    '''Ruling 17: EXPERT_ONLY takes the AHP_ONLY row of the matrix (SDD gives
    no kind specific rule, so the conservative superset of [L1435] applies;
    the tension is registered as B-043).'''
    tree = _weights(kind=KIND_EXPERT_ONLY)
    assert check_weights(slot(tree)) is None


def test_t06_j03_combined_with_a_complete_provenance_passes():
    tree = _weights(kind=KIND_COMBINED)
    assert check_weights(slot(tree)) is None


def test_t06_j04_ahp_only_without_the_ahp_segment_is_blocked():
    tree = _weights(kind=KIND_AHP_ONLY)
    tree['provenance'].pop('ahp')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_INVALID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED
    assert len(exc.violations) >= 1
    assert set(ids_of(exc)) <= set(WEIGHT_CHECKS)


def test_t06_j05_empty_comparison_matrices_are_a_gap():
    '''Ruling 17: "ahp.comparison_matrices 必须非空 mapping" ("AHP 矩阵"
    [L1435] / [L1232]).'''
    tree = _weights(kind=KIND_AHP_ONLY)
    tree['provenance']['ahp'] = {'comparison_matrices': {}, 'cr': CR_PRESENT}
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j06_a_missing_cr_is_a_gap():
    '''Ruling 17: "ahp.cr 必须存在且可 numeric.D".'''
    tree = _weights(kind=KIND_AHP_ONLY)
    tree['provenance']['ahp'] = {'comparison_matrices': {
        'SYN-DIM-A': 'SYN-MATRIX-PAYLOAD'}}
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j07_a_large_cr_value_is_not_a_gap():
    '''Ruling 17 / H-5 / B-041: the CR threshold is not in the SDD, so T06
    judges existence and parsability only. A CR of 0.99, which any AHP
    textbook would reject, must still load - proposing a threshold here would
    be inventing a business number.'''
    tree = _weights(kind=KIND_AHP_ONLY)
    tree['provenance']['ahp']['cr'] = CR_LARGE
    assert check_weights(slot(tree)) is None


def test_t06_j08_combined_without_entropy_is_a_gap():
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('entropy')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j09_combined_without_the_combine_segment_is_a_gap():
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('combine')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j10_combined_without_alpha_is_a_gap():
    '''Ruling 17: "combine.alpha 必须存在且可 numeric.D".'''
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance']['combine'] = {}
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j11_combined_without_alpha_basis_is_a_gap():
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('alpha_basis')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_VERSION_INVALID


def test_t06_j12_a_large_alpha_value_is_not_a_gap():
    '''Ruling 17 / B-042: the alpha range is not in the SDD, so only
    existence is judged. An alpha outside 0..1 must still load.'''
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance']['combine']['alpha'] = ALPHA_LARGE
    assert check_weights(slot(tree)) is None


def test_t06_j13_extra_segments_are_not_penalised():
    '''Ruling 17: "多余的段 (如 AHP_ONLY 却带 entropy) 不报错 (最小实现,
    不发明禁止多余段判据)".'''
    tree = _weights(kind=KIND_AHP_ONLY)
    tree['provenance']['entropy'] = {'SYN-ENTROPY-WEIGHTS':
                                     'SYN-ENTROPY-PAYLOAD'}
    tree['provenance']['combine'] = {'alpha': ALPHA_PRESENT}
    tree['provenance']['alpha_basis'] = 'SYN-ALPHA-BASIS'
    assert check_weights(slot(tree)) is None


def test_t06_j14_a_frozen_version_without_the_provenance_key_is_blocked():
    '''Ruling 17: "provenance 键本身缺失 -> 对 FROZEN 版本是
    RC.WEIGHT_VERSION_INVALID (P-11 缺任一项 -> 加载失败)". models 层可空
    (ORCH-20 裁决 2) does not make the config layer optional; that is exactly
    what ORCH-20 L145 handed to T06.'''
    tree = one_tree()
    tree.pop('provenance')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert exc.reason_code is RC().WEIGHT_VERSION_INVALID
    assert exc.exit_code == EXIT_BLOCK_EXPECTED
    assert len(exc.violations) >= 1


def test_t06_j15_a_combined_kind_loses_the_run_id_check_too():
    '''Ruling 17 AHP_ENTROPY_COMBINED row: "上述全部 + entropy + combine +
    alpha_basis", and whatif_run_id belongs to 上述全部.'''
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('whatif_run_id')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    assert excinfo.value.reason_code is RC().WEIGHT_MISSING_WHATIF_RUN_ID


def test_t06_j16_several_gaps_are_collected_at_once():
    '''Ruling 18: one exception lists every gap, deduplicated and sorted on
    the WEIGHT_CHECKS order, never truncated.'''
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('entropy')
    tree['provenance'].pop('combine')
    tree['provenance'].pop('alpha_basis')
    tree['provenance']['ahp'].pop('cr')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert len(exc.violations) >= 4
    assert_triples(exc, WEIGHT_CHECKS)
    assert len(exc.violations) == len(set(exc.violations))


def test_t06_j17_the_version_message_head_names_count_code_and_reason():
    '''Ruling 18: first line "权重版本校验失败 N 项（退出码 2，<RC.value>）",
    then one "  - <check_id> <path>: <detail>" line per violation.'''
    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('entropy')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    registry = RC()
    lines = str(exc).splitlines()
    assert lines[0] == MSG_WEIGHT_HEAD % (len(exc.violations),
                                          EXIT_BLOCK_EXPECTED,
                                          exc.reason_code.value)
    assert lines[0].startswith('权重版本校验失败 ')
    assert lines[0].endswith('（退出码 2，' + exc.reason_code.value + '）')
    assert len(lines) == 1 + len(exc.violations)
    for line, item in zip(lines[1:], exc.violations):
        head = '  - ' + item[0] + ' ' + item[1] + ': '
        assert line.startswith(head), line
        assert line[len(head):] != '', line
    assert exc.reason_code is registry.WEIGHT_VERSION_INVALID


def test_t06_j18_the_provenance_path_carries_the_file_stem():
    '''ORCH-23 ruling 8 / ORCH-24 ruling 14: a violation path starts with the
    weights file stem, so two weights_*.yaml documents never blur each other.'''
    pair = {WEIGHTS_STEM_B: _weights(WEIGHTS_STEM_B, kind=KIND_COMBINED)}
    pair[WEIGHTS_STEM_B]['provenance'].pop('alpha_basis')
    with pytest.raises(weight_error()) as excinfo:
        check_weights(pair)
    for path in paths_of(excinfo.value):
        assert path.startswith(WEIGHTS_STEM_B), path

# ---------------------------------------------------------------------------
# T06-K (version half). Ruling 18: the whole list at once, sorted on the
# WEIGHT_CHECKS order, deduplicated, never truncated.
# ---------------------------------------------------------------------------
def test_t06_k60_the_weight_constructor_sorts_a_shuffled_input():
    '''Ruling 18 / ruling 19: violations arrives unordered and is stored
    sorted by (WEIGHT_CHECKS.index(check_id), path).'''
    shuffled = [('NUMERIC', 'p', 'd'), ('WEIGHT_COVERAGE', 'q', 'd'),
                ('STRUCTURE', 'a', 'd'), ('WEIGHT_COVERAGE', 'a', 'd'),
                ('WEIGHT_APPROVAL', 'z', 'd')]
    err = cfg('WeightVersionInvalidError')
    exc = err(RC().WEIGHT_VERSION_INVALID, list(reversed(shuffled)))
    assert exc.violations == tuple(sorted(
        shuffled, key=lambda item: (WEIGHT_CHECKS.index(item[0]), item[1])))
    assert exc.exit_code == EXIT_BLOCK_EXPECTED


def test_t06_k61_the_weight_constructor_deduplicates():
    item = ('WEIGHT_PROVENANCE_COMPLETE', WEIGHTS_STEM_A + '.provenance.ahp',
            'detail')
    exc = cfg('WeightVersionInvalidError')(RC().WEIGHT_VERSION_INVALID,
                                            [item, item])
    assert exc.violations == (item,)


def test_t06_k62_three_covering_versions_yield_three_ordered_entries():
    '''Ruling 16: "多份 weights 的 stem 序沿用 ORCH-23 裁决 9 (stem 升序),
    保证 >= 2 份时 violations 的列出顺序确定" + ruling 18 不截断.'''
    stem_c = 'weights_WV-SYN-0003'
    triple = {WEIGHTS_STEM_A: one_tree(),
              WEIGHTS_STEM_B: _weights(WEIGHTS_STEM_B),
              stem_c: _weights(stem_c)}
    with pytest.raises(weight_error()) as excinfo:
        check_weights(triple)
    exc = excinfo.value
    assert len(exc.violations) == 3
    assert [path.split('.')[0] for path in paths_of(exc)] == [
        WEIGHTS_STEM_A, WEIGHTS_STEM_B, stem_c]
    assert_triples(exc, WEIGHT_CHECKS)


# ---------------------------------------------------------------------------
# T06-L (version half). Ruling 7: a float, a bool or an unparsable string in
# a provenance number slot is a NUMERIC violation inside
# ConfigSemanticError, and no NumericError ever leaves the config layer.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('segment, probe', [
    ('cr', TYPE_PROBE_FLOAT_CR), ('alpha', TYPE_PROBE_FLOAT_CR)],
    ids=['cr-float', 'alpha-float'])
def test_t06_l60_a_float_provenance_number_is_numeric_not_an_escaping_error(
        segment, probe):
    numeric = _numeric_module()
    tree = _weights(kind=KIND_COMBINED)
    if segment == 'cr':
        tree['provenance']['ahp']['cr'] = probe
    else:
        tree['provenance']['combine']['alpha'] = probe
    with pytest.raises(semantic_error()) as excinfo:
        check_weights(slot(tree))
    exc = excinfo.value
    assert not isinstance(exc, numeric.NumericError)
    assert not isinstance(exc, numeric.FloatNotAllowedError)
    assert 'NUMERIC' in ids_of(exc)
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


# Ruling 17: cr must be parseable by numeric.D. Ruling 7: every D failure
# becomes a NUMERIC violation inside ConfigSemanticError, at the path the
# caller supplied, and no NumericError ever escapes the config layer.
@pytest.mark.parametrize(
    'bad', [TYPE_PROBE_FLOAT_CR, True, '', NUMERIC_GARBAGE],
    ids=['float', 'bool', 'blank', 'garbage'])
def test_t06_l61_numeric_reaches_the_provenance_number(bad):
    numeric = _numeric_module()
    path = WEIGHTS_STEM_A + '.provenance.ahp.cr'
    with pytest.raises(semantic_error()) as excinfo:
        cfg('to_decimal')(bad, path=path)
    exc = excinfo.value
    assert not isinstance(exc, numeric.NumericError)
    assert set(ids_of(exc)) == {'NUMERIC'}
    assert paths_of(exc) == [path]
    assert exc.exit_code == EXIT_CONFIG_EXPECTED


def test_t06_l62_a_parsable_provenance_number_passes_to_decimal():
    assert cfg('to_decimal')(CR_PRESENT, path='p') == Decimal('0.25')
    assert cfg('to_decimal')(CR_LARGE, path='p') == Decimal('0.99')


# ---------------------------------------------------------------------------
# T06-M (version half). Ruling 5: every version path raises a registered
# RC member, with the BLOCK severity the registry itself carries.
# ---------------------------------------------------------------------------
def test_t06_m60_every_version_reason_code_is_a_registered_block_member():
    registry = RC()
    codes = importlib.import_module('dsm.reason_codes')
    allowed = set(T06_VERSION_REASON_CODES)
    for name in WEIGHT_SCENARIOS:
        with pytest.raises(weight_error()) as excinfo:
            violating_weight_call(name)()
        code = excinfo.value.reason_code
        assert isinstance(code, registry), name
        assert code in list(registry), name
        assert code.name in allowed, (name, code.name)
        assert code.name == WEIGHT_SCENARIO_REASONS[name], name
        assert codes.severity(code) == codes.Severity.BLOCK, name


def test_t06_m61_the_reason_code_spelling_stays_the_s0_one():
    '''Ruling 5: str(RC.X) == 'RC.X' while CSV / hash output needs .value.'''
    with pytest.raises(weight_error()) as excinfo:
        check_weights({})
    code = excinfo.value.reason_code
    assert str(code) == 'RC.WEIGHT_VERSION_INVALID'
    assert code.value == 'WEIGHT_VERSION_INVALID'
    assert code.name == 'WEIGHT_VERSION_INVALID'


def test_t06_m62_the_structural_branch_never_borrows_a_version_code():
    '''Ruling 5 table: STRUCTURE and NUMERIC map to RC.CONFIG_SEMANTIC_ERROR,
    never to a WEIGHT_* code, because ruling 15 draws its dividing line as
    "结构/类型问题一律 3, 版本策略问题一律 2" and says R4 judges on it.'''
    tree = one_tree()
    tree.pop('effective_from')
    with pytest.raises(semantic_error()) as excinfo:
        cfg('validate_weights')(appcfg(weights=slot(tree)), period=PERIOD_OK)
    exc = excinfo.value
    assert exc.reason_code is RC().CONFIG_SEMANTIC_ERROR
    assert exc.reason_code.name not in T06_VERSION_REASON_CODES
    assert exc.exit_code == EXIT_CONFIG_EXPECTED
    assert 'STRUCTURE' in ids_of(exc)


# ---------------------------------------------------------------------------
# T06-N (version half). Ruling 19: validate_weights / select_weight_stem /
# period_key are pure - no I/O, no wall clock, no global state, no input
# mutation, byte identical on a rerun.
# ---------------------------------------------------------------------------
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


def _call_paths(name):
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    fn = _function_nodes(tree).get(name)
    if fn is None:
        raise AssertionError(name + ' is not defined in dsm/config.py')
    return [_dotted(node.func) for node in ast.walk(fn)
            if isinstance(node, ast.Call)]


def _binding_offenders(name):
    tree = ast.parse(CONFIG_PATH.read_text(encoding='utf-8'))
    fn = _function_nodes(tree).get(name)
    if fn is None:
        return [(name, 'not defined in dsm/config.py')]
    found = []
    for node in ast.walk(fn):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            found.append((name, 'global state'))
    return found


VERSION_PURE_NAMES = ('validate_weights', 'select_weight_stem', 'period_key')


def test_t06_n60_the_version_helpers_touch_no_io_no_clock_no_state():
    '''Ruling 19 / H-8: the four forbidden families are I/O, wall clock,
    global binding and input mutation; period comes from the caller only.'''
    for name in VERSION_PURE_NAMES:
        assert callable(cfg(name)), name
    offenders = []
    for name in VERSION_PURE_NAMES:
        offenders += _binding_offenders(name)
        for path in _call_paths(name):
            if path in ('open', 'print', 'input', 'Path'):
                offenders.append((name, path))
            elif path.startswith(('os.', 'io.', 'yaml.', 'pathlib.',
                                 'time.', 'datetime.datetime.now',
                                 'datetime.date.today', 'datetime.now',
                                 'date.today')):
                offenders.append((name, path))
    assert offenders == [], repr(offenders)


def test_t06_n61_the_version_helpers_do_not_mutate_their_input():
    '''Ruling 19 "不修改入参": the weights tree the caller built stays
    byte for byte the same, gaps included.'''
    app = appcfg(weights=slot(one_tree()))
    before = repr(app.model_dump())
    with pytest.raises(weight_error()):
        cfg('validate_weights')(app, period=PERIOD_OK)
    assert repr(app.model_dump()) == before
    tree = _weights()
    tree['provenance'].pop('ahp')
    snapshot = copy.deepcopy(tree)
    with pytest.raises(weight_error()):
        check_weights(slot(tree))
    assert tree == snapshot


def test_t06_n62_two_identical_calls_are_byte_identical():
    '''Ruling 18 / V-3: the listing is deterministic, so the same broken
    input yields the very same message twice.'''
    err = weight_error()

    def once(tree):
        try:
            cfg('validate_weights')(appcfg(weights=slot(copy.deepcopy(tree))),
                                    period=PERIOD_OK)
        except err as caught:
            return str(caught)
        raise AssertionError('the gap did not raise')

    tree = _weights(kind=KIND_COMBINED)
    tree['provenance'].pop('entropy')
    tree['provenance'].pop('combine')
    assert once(tree) == once(tree)
    assert repr(cfg('period_key')(PERIOD_OK)) == repr(
        cfg('period_key')(PERIOD_OK))
