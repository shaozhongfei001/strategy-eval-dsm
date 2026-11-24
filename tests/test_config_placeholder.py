'''RED tests for the S1-T05 contract of dsm/config.py (L1, RED by design).

Contract authority = docs/adr/ORCH-23.md, rulings 1-15 plus the section 7
acceptance checklist T05-A .. T05-M, applied item by item. The SDD wording
behind it is carried by docs/digest/S1-T05.md: [L873]-[L882] (section 3.3.4),
[L1246]-[L1259] (section 3.12), [L1076]-[L1091] (exit codes), [L1276]-[L1282],
[L1325]-[L1328], [L1434]-[L1435] (P-10 / P-11), [L1498] (V-5),
[L1580]-[L1588], [L1734]-[L1759] (governance parameter list), and the
PLACEHOLDER discipline of [L78] / [L102] / [L1806].

dsm/config.py does not exist yet, and that is the whole point of this file.
Every reference to it is lazy: _config_module() imports inside the test body
and cfg() resolves one public name through getattr, so pytest collects this
file with zero collection errors and every RED failure is a
ModuleNotFoundError (module absent) or an AttributeError (name absent). The
source level gates (T05-I / T05-K / T05-L) read dsm/config.py through
_config_source(), which raises ModuleNotFoundError while the file is absent,
so they stay RED for exactly the same single reason.

Coverage map (checklist letters, for the R4 review):

  A  T05-A  EXIT_CONFIG == 3; ConfigPlaceholderError.exit_code == 3; the
            constructor is (paths, missing_files=()) and stores tuples.
  B  T05-B  N placeholder positions produce N paths, all of them at once,
            deduplicated and sorted, plus the ruling 9 message format.
  C  T05-C  the ruling 5 hit / miss tables, no substring false positive, dict
            keys are never scanned, PLACEHOLDER_TOKENS / _PREFIXES.
  D  T05-D  ruling 6: every None hits, an empty yaml file hits as its stem.
  E  T05-E  ruling 8 path notation: stem prefix, dotted dicts, [i] lists.
  F  T05-F  ruling 9 determinism and the fixed file order.
  G  T05-G  ruling 10: missing required files ride the very same single exit.
  H  T05-H  ruling 3 AppConfig: six slots, frozen, extra=forbid, and no
            invented field level schema for the [L1250]-[L1257] content keys.
  I  T05-I  H-8 purity: signatures, no I/O, no wall clock, no global state.
  K  T05-K  H-9 layering: no L0a/L0b import and, at the T05 stage, no
            dsm.models / dsm.numeric / dsm.reason_codes import.
  L  T05-L  H-5 self scan: no business number in dsm/config.py nor in the two
            new test files (the two self scans are positive controls).
  M  T05-M  the do-not-break gate: existing modules still import, no new
            skip/xfail, repo config/ stays empty, requirements stay pinned,
            the new files stay BOM free / LF / tab free.

Three points are under-determined by ORCH-23 itself. They are pinned here in
the conservative direction and flagged to the orchestrator instead of being
silently decided (H-10 forbids inventing contract to close a gap):

  (1) scan_config_trees(trees): ruling 11 calls the argument "several trees
      (including the stem to tree map of weights)" without naming its type.
      These tests pass a dict[str, ConfigTree] keyed by file stem, the only
      shape that carries the stems ruling 9 needs for its file order.
  (2) find_placeholders(tree, root=''): ruling 8 defines the notation with a
      stem prefix but never spells the empty prefix form. These tests assert
      the relative invariant (bare paths == rooted paths minus the prefix, and
      no path ever starts with a dot) rather than an absolute spelling.
  (3) the ordering of missing_files: ruling 10 says "sorted and deduplicated"
      without saying whether that means the [L1250]-[L1257] clause order of
      REQUIRED_CONFIG_STEMS or plain str ascending. These tests therefore
      assert content, deduplication and determinism, never the order, and the
      spelling of the missing weights entry is asserted only as "mentions
      weights".

All data is synthetic (SYN- prefix, H-5 / H-14). No weight, threshold, floor,
target, price, period, sample size or governance parameter value is proposed
anywhere: every such slot holds either the literal string PLACEHOLDER or a
SYN- token. The only numeric literals are the type probes 0 / 1 / -1 and
TYPE_PROBE_FLOAT, which exists solely to prove that a filled float is not
mistaken for a placeholder. Fixtures are built in memory or written under
pytest tmp_path; the repository config/ directory is never touched
(ruling 13).
'''
import ast
import copy
import importlib
import inspect
import re
from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import BaseModel, ValidationError

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / 'dsm' / 'config.py'
MODELS_PATH = REPO_ROOT / 'dsm' / 'models.py'
THIS_PATH = Path(__file__).resolve()
PROPERTIES_PATH = REPO_ROOT / 'tests' / 'test_config_properties.py'
REQUIREMENTS_PATH = REPO_ROOT / 'requirements.txt'
REPO_CONFIG_DIR = REPO_ROOT / 'config'
DSM_DIR = REPO_ROOT / 'dsm'


# ---------------------------------------------------------------------------
# Lazy resolution. Attribute access only, so a missing name raises
# AttributeError (feature not implemented) instead of breaking collection.
# ---------------------------------------------------------------------------
def _config_module():
    '''Import dsm.config inside the test body, never at module import time.'''
    return importlib.import_module('dsm.config')


def cfg(name):
    '''Resolve one public name of dsm.config (ORCH-23 ruling 11).'''
    module = _config_module()
    resolved = getattr(module, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.config has no attribute ' + name
            + ' (S1-T05 not implemented yet, ORCH-23 ruling 11)')
    return resolved


def _config_source():
    '''The text of dsm/config.py, or ModuleNotFoundError while it is absent.'''
    if not CONFIG_PATH.exists():
        raise ModuleNotFoundError(
            'dsm.config is not implemented yet: dsm/config.py is absent')
    return CONFIG_PATH.read_text(encoding='utf-8')


def _config_ast():
    return ast.parse(_config_source())


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


def _imported_names(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias_.name for alias_ in node.names]
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            found += [module + '.' + alias_.name for alias_ in node.names]
    return found


def _top_level_imports(tree):
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [alias_.name.split('.')[0] for alias_ in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append(node.module.split('.')[0])
    return sorted(set(found))


# ---------------------------------------------------------------------------
# Contract constants, copied verbatim out of ORCH-23 rulings 3 / 9 / 10 / 11
# and out of the [L1250]-[L1257] content list (ORCH-16 verbatim naming).
# ---------------------------------------------------------------------------
EXIT_CODE = 3
SIX_SLOTS = ('eval_config', 'weights', 'redlines', 'grade_rules',
             'anchor_set', 'ahp_matrices')
REQUIRED_STEMS = ('eval_config', 'redlines', 'grade_rules', 'anchor_set',
                  'ahp_matrices')
FILE_ORDER = ('eval_config', 'weights', 'redlines', 'grade_rules',
              'anchor_set', 'ahp_matrices')
WEIGHTS_GLOB = 'weights_*.yaml'
WEIGHTS_STEM_A = 'weights_WV-SYN-0001'
WEIGHTS_STEM_B = 'weights_WV-SYN-0002'
WEIGHTS_STEM_C = 'weights_WV-SYN-0003'
WEIGHTS_STEMS = (WEIGHTS_STEM_A, WEIGHTS_STEM_B, WEIGHTS_STEM_C)
PLACEHOLDER_WORDS = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
PURE_FUNCTIONS = ('is_placeholder_value', 'find_placeholders',
                  'scan_config_trees')

# ruling 9 message format, spelled out by the ADR because the SDD is silent.
MSG_HEAD = '配置含 %d 个未签认占位值（退出码 %d）'
MSG_MISSING_HEAD = '缺失必需配置文件 %d 份：'
MSG_ITEM = '  - %s'

# Type probes only. These are NOT business values: 0 / 1 / -1 pin the int and
# bool branches of ruling 5, TYPE_PROBE_FLOAT pins the float branch.
TYPE_PROBE_ZERO = 0
TYPE_PROBE_ONE = 1
TYPE_PROBE_MINUS_ONE = -1
TYPE_PROBE_FLOAT = 0.5  # 仅类型探针，非业务值

# Verbatim content keys of [L1250]-[L1257]. They may only ever appear as
# fixture key names or as PLACEHOLDER-bearing slots; T05-H asserts that none
# of them was promoted into an AppConfig field (ruling 3).
CONTENT_KEYS = (
    'evidence_mode', 'triangulation', 'cel', 'stable_max', 'review_max',
    'divergence_threshold', 'loo_sampling_threshold', 'dimensions',
    'provenance', 'status', 'forced_grade', 'attainment_floor',
    'evidence_class_min', 'promotion_streak', 'action', 'effective_from',
    'effective_to', 'rationale', 'alpha_floor', 'drift_budget',
    'boundary_budget', 'boundary_epsilon', 'min_dim_weight',
    'max_shift_from_ahp', 'alpha_grid', 'whatif_run_id',
)

# ruling 5: every one of these must hit.
HIT_STRINGS = (
    'PLACEHOLDER',
    'placeholder',
    'Placeholder',
    '  PLACEHOLDER  ',
    '\tPLACEHOLDER\n',
    'TODO',
    'todo',
    'TBD',
    'tbd',
    'XXX',
    'xxx',
    'PLACEHOLDER_K-01',
    'PLACEHOLDER_K-20',
    'PLACEHOLDER_SYN-AWAITING-SIGNOFF',
    'TODO_SYN-FILL',
    'TBD-SYN',
    'XXX_SYN',
)

# ruling 5: none of these may hit. This table used to leave the empty and the
# whitespace-only string out on purpose, because the ruling 5 iff did not
# mention them; ruling 19 has since closed that gap and ruling 24 item 1 turns
# it into a test gate, so both now sit at the end of the table and are pinned
# again, with their tree level consequences, by test_t05_c12 below.
MISS_STRINGS = (
    'OK',
    'ACTIVE',
    'SIGNED',
    'FROZEN',
    'DRAFT',
    'SYN-NOTE-01',
    'SYN-free text rationale about the scoring period',
    'abcTODOdef',
    'XPLACEHOLDER',
    'MY_TBD',
    'aXXXb',
    'PLACE',
    'HOLDERS',
    'TO_DO',
    'TO-DO',
    'SYN-OK',
    '',
    '   ',
    '\t\n ',
)
MISS_SCALARS = (TYPE_PROBE_ZERO, TYPE_PROBE_ONE, TYPE_PROBE_MINUS_ONE,
                TYPE_PROBE_FLOAT, True, False)
MISS_CONTAINERS = ({'SYN-KEY': 'SYN-OK'}, ['SYN-OK'])

EMPTY_FILE = object()  # sentinel: write a zero byte yaml file
COMMENT_ONLY_FILE = '# SYN-COMMENT-ONLY\n'


# ---------------------------------------------------------------------------
# Synthetic fixtures. Every governance slot holds a SYN- token, never a
# number, so nothing here can be read as a proposed business value (H-5).
# ---------------------------------------------------------------------------
def _clean_eval_config():
    return {
        'evidence_mode': 'SYN-EVIDENCE-MODE',
        'triangulation': {'enabled': True,
                          'thresholds': ['SYN-T-A', 'SYN-T-B', 'SYN-T-C']},
        'cel': {'enabled': False},
        'sensitivity': {'stable_max': 'SYN-STABLE-MAX',
                        'review_max': 'SYN-REVIEW-MAX',
                        'divergence_threshold': 'SYN-DIVERGENCE-THRESHOLD'},
        'loo_sampling_threshold': 'SYN-LOO-SAMPLING-THRESHOLD',
        'weight_construction': {
            'alpha_floor': 'SYN-ALPHA-FLOOR',
            'drift_budget': 'SYN-DRIFT-BUDGET',
            'boundary_budget': 'SYN-BOUNDARY-BUDGET',
            'boundary_epsilon': 'SYN-BOUNDARY-EPSILON',
            'min_dim_weight': 'SYN-MIN-DIM-WEIGHT',
            'max_shift_from_ahp': 'SYN-MAX-SHIFT-FROM-AHP',
            'alpha_grid': ['SYN-ALPHA-GRID-A', 'SYN-ALPHA-GRID-B'],
        },
    }


def _clean_weights(stem):
    return {
        'weight_version_id': stem,
        'status': 'SYN-FROZEN',
        'whatif_run_id': 'SYN-WHATIF-RUN',
        'effective_from': 'SYN-EFFECTIVE-FROM',
        'effective_to': 'SYN-EFFECTIVE-TO',
        'dimensions': [
            {'dimension_id': 'SYN-DIM-01',
             'weight': 'SYN-DIM-WEIGHT',
             'metrics': [{'metric_code': 'SYN-M-01',
                          'weight': 'SYN-METRIC-WEIGHT'}]},
        ],
        'provenance': {'ahp_basis': 'SYN-AHP-BASIS',
                       'alpha_basis': 'SYN-ALPHA-BASIS'},
    }


def _clean_redlines():
    return {
        'HARD': [{'metric_code': 'SYN-M-01',
                  'threshold': 'SYN-HARD-THRESHOLD',
                  'forced_grade': 'SYN-FORCED-GRADE',
                  'waiver_ref': 'SYN-WAIVER-REF'}],
        'SOFT': [{'metric_code': 'SYN-M-02',
                  'threshold': 'SYN-SOFT-THRESHOLD'}],
    }


def _clean_grade_rules():
    return {
        'levels': [
            {'grade_code': 'L1', 'attainment_floor': 'SYN-FLOOR-L1',
             'evidence_class_min': 'SYN-EVIDENCE-CLASS-MIN',
             'promotion_streak': 'SYN-PROMOTION-STREAK',
             'action': 'SYN-ACTION-L1'},
            {'grade_code': 'L2', 'attainment_floor': 'SYN-FLOOR-L2',
             'evidence_class_min': 'SYN-EVIDENCE-CLASS-MIN',
             'promotion_streak': 'SYN-PROMOTION-STREAK',
             'action': 'SYN-ACTION-L2'},
        ],
    }


def _clean_anchor_set():
    return {
        'anchor_set_id': 'SYN-ANCHOR-0001',
        'effective_from': 'SYN-EFFECTIVE-FROM',
        'effective_to': 'SYN-EFFECTIVE-TO',
        'members': [{'strategy_id': 'SYN-S-001',
                     'rationale': 'SYN-RATIONALE'}],
    }


def _clean_ahp_matrices():
    return {
        'matrices': [{'expert_id': 'SYN-EXPERT-01',
                      'interview_date': 'SYN-INTERVIEW-DATE',
                      'pairwise': [['SYN-CELL', 'SYN-CELL'],
                                   ['SYN-CELL', 'SYN-CELL']]}],
    }


def clean_trees():
    '''A complete six slot synthetic config set with no placeholder in it.'''
    return {
        'eval_config': _clean_eval_config(),
        WEIGHTS_STEM_A: _clean_weights(WEIGHTS_STEM_A),
        'redlines': _clean_redlines(),
        'grade_rules': _clean_grade_rules(),
        'anchor_set': _clean_anchor_set(),
        'ahp_matrices': _clean_ahp_matrices(),
    }


def write_trees(base, trees):
    '''Render {stem: tree} as <stem>.yaml under base (tmp_path only, H-14).'''
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    for stem, tree in trees.items():
        if tree is EMPTY_FILE:
            text = ''
        elif isinstance(tree, str):
            text = tree
        else:
            text = yaml.safe_dump(tree, allow_unicode=True, sort_keys=False)
        (base / (stem + '.yaml')).write_text(text, encoding='utf-8')
    return base


def full_dir(base, **overrides):
    '''A complete config dir, with individual stems overridden.'''
    trees = clean_trees()
    trees.update(overrides)
    return write_trees(base, trees)


def dir_without(base, *stems):
    '''A config dir with the named stems removed (ruling 10 missing files).'''
    trees = clean_trees()
    for stem in stems:
        trees.pop(stem, None)
    return write_trees(base, trees)


def hit_tree(count):
    '''A synthetic tree carrying exactly `count` placeholder positions.'''
    tree = {}
    for index in range(count):
        tree['slot_%02d' % index] = {'leaf': 'PLACEHOLDER'}
    return tree


def expected_hit_paths(count, stem='eval_config'):
    return tuple('%s.slot_%02d.leaf' % (stem, index) for index in range(count))


def appconfig_payload():
    return {
        'eval_config': _clean_eval_config(),
        'weights': {WEIGHTS_STEM_A: _clean_weights(WEIGHTS_STEM_A)},
        'redlines': _clean_redlines(),
        'grade_rules': _clean_grade_rules(),
        'anchor_set': _clean_anchor_set(),
        'ahp_matrices': _clean_ahp_matrices(),
    }


def build_appconfig(**overrides):
    '''Build an AppConfig lazily, so a missing class fails as AttributeError.'''
    payload = appconfig_payload()
    payload.update(overrides)
    return cfg('AppConfig')(**payload)


def load_all(base):
    return cfg('load_all')(str(base))


def placeholder_error():
    return cfg('ConfigPlaceholderError')


PURE_CALLS = {
    'is_placeholder_value': lambda fn: fn('PLACEHOLDER'),
    'find_placeholders': lambda fn: fn({'SYN-a': {'SYN-b': None}},
                                       root='eval_config'),
    'scan_config_trees': lambda fn: fn({'eval_config': {'SYN-a': 'TODO'},
                                        'redlines': {'SYN-b': None}}),
}


# ---------------------------------------------------------------------------
# T05-A. Exit code 3 is a single source of truth ([L881] / [L1080]).
# ---------------------------------------------------------------------------
def test_t05_a01_exit_config_constant_is_three():
    '''T05-A: EXIT_CONFIG == 3, defined in dsm/config.py so cli.py imports it
    instead of writing its own literal (ruling 2, H-7).'''
    assert cfg('EXIT_CONFIG') == EXIT_CODE


def test_t05_a02_error_instance_carries_exit_code_three():
    '''T05-A: ruling 11 declares exit_code as an instance attribute.'''
    err = placeholder_error()(['eval_config.SYN-a'])
    assert err.exit_code == EXIT_CODE


def test_t05_a03_exit_code_is_a_plain_int():
    err = placeholder_error()(['eval_config.SYN-a'])
    assert type(err.exit_code) is int


def test_t05_a04_the_error_is_an_exception_subclass():
    '''[L881] names three exceptions; ruling 1 forbids inventing a fourth and
    ruling 11 makes this one an Exception.'''
    resolved = cfg('ConfigPlaceholderError')
    assert isinstance(resolved, type)
    assert issubclass(resolved, Exception)


def test_t05_a05_paths_attribute_is_a_tuple():
    err = placeholder_error()(['eval_config.SYN-a', 'redlines.SYN-b'])
    assert type(err.paths) is tuple


def test_t05_a06_missing_files_defaults_to_an_empty_tuple():
    err = placeholder_error()(['eval_config.SYN-a'])
    assert type(err.missing_files) is tuple
    assert err.missing_files == ()


@pytest.mark.parametrize('paths_in', [
    ['eval_config.SYN-b', 'eval_config.SYN-a'],
    ('eval_config.SYN-b', 'eval_config.SYN-a'),
])
def test_t05_a07_the_constructor_accepts_any_iterable(paths_in):
    '''Ruling 11: both arguments accept an iterable and store a tuple.'''
    err = placeholder_error()(paths_in)
    assert type(err.paths) is tuple
    assert set(err.paths) == {'eval_config.SYN-a', 'eval_config.SYN-b'}


def test_t05_a08_load_all_raises_with_exit_code_three(tmp_path):
    '''T05-A end to end: the [L1434] "configuration loading stage" is inside
    load_all (ruling 2).'''
    base = full_dir(tmp_path / 'cfg', eval_config={'evidence_mode': 'PLACEHOLDER'})
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.exit_code == EXIT_CODE
    assert cfg('EXIT_CONFIG') == excinfo.value.exit_code


# ---------------------------------------------------------------------------
# T05-B. [L878] "not only the first one" + [L1259] / V-5 [L1498] "list them
# all at once".
# ---------------------------------------------------------------------------
def test_t05_b01_all_paths_are_listed_at_once(tmp_path):
    tree = hit_tree(7)
    base = full_dir(tmp_path / 'cfg', eval_config=tree)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    paths = excinfo.value.paths
    assert len(paths) == 7
    assert tuple(paths) == expected_hit_paths(7)


@pytest.mark.parametrize('count', [1, 2, 3, 5, 8, 13])
def test_t05_b02_the_path_count_equals_the_hit_count(count, tmp_path):
    base = full_dir(tmp_path / 'cfg', eval_config=hit_tree(count))
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert len(excinfo.value.paths) == count


def test_t05_b03_the_first_path_is_not_the_only_one_reported(tmp_path):
    tree = {'aaa_first': 'PLACEHOLDER', 'zzz_last': 'TODO'}
    base = full_dir(tmp_path / 'cfg', eval_config=tree)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    paths = excinfo.value.paths
    assert len(paths) == 2
    assert 'eval_config.aaa_first' in paths
    assert 'eval_config.zzz_last' in paths


def test_t05_b04_error_paths_are_deduplicated():
    '''Ruling 9: one path appears once even if it is handed in twice.'''
    err = placeholder_error()(['eval_config.SYN-a', 'eval_config.SYN-a',
                               'redlines.SYN-b', 'redlines.SYN-b'])
    assert err.paths == ('eval_config.SYN-a', 'redlines.SYN-b')


def test_t05_b05_error_paths_are_sorted():
    '''Ruling 9 + ruling 23: "sorted" means the ruling 9 key -- the fixed file
    order of [L1250]-[L1257] first, the path string ascending inside one file
    second. The expectation below is taken from the ADR text and NOT from what
    an implementation happens to return (H-11): eval_config is the first file of
    the list, redlines the third and anchor_set the fifth, so anchor_set comes
    last here even though a plain string sort would put it first. Ruling 23
    makes this the only order the constructor is allowed to produce.'''
    err = placeholder_error()(['redlines.SYN-z', 'eval_config.SYN-m',
                               'anchor_set.SYN-a'])
    assert err.paths == ('eval_config.SYN-m', 'redlines.SYN-z',
                         'anchor_set.SYN-a')


def test_t05_b06_the_message_first_line_carries_the_total_count():
    err = placeholder_error()(['eval_config.SYN-a', 'eval_config.SYN-b',
                               'redlines.SYN-c'])
    assert str(err).splitlines()[0] == MSG_HEAD % (3, EXIT_CODE)


def test_t05_b07_the_message_lists_every_path_on_its_own_dash_line():
    paths = ['eval_config.SYN-a', 'eval_config.SYN-b', 'redlines.SYN-c']
    err = placeholder_error()(paths)
    assert str(err).splitlines()[1:] == [MSG_ITEM % path for path in paths]


def test_t05_b08_scan_config_trees_collects_across_files():
    trees = {
        'eval_config': {'SYN-a': 'PLACEHOLDER'},
        WEIGHTS_STEM_A: {'SYN-b': ['TODO']},
        'redlines': {'SYN-c': None},
    }
    assert cfg('scan_config_trees')(trees) == (
        'eval_config.SYN-a', WEIGHTS_STEM_A + '.SYN-b[0]', 'redlines.SYN-c')


def test_t05_b09_hits_are_found_at_arbitrary_depth():
    tree = {'l1': {'l2': {'l3': [{'l4': {'l5': 'PLACEHOLDER'}}, None]}}}
    paths = cfg('find_placeholders')(tree, root='eval_config')
    assert sorted(paths) == ['eval_config.l1.l2.l3[0].l4.l5',
                             'eval_config.l1.l2.l3[1]']


def test_t05_b10_a_large_tree_is_not_truncated(tmp_path):
    '''[L878] forbids reporting only the first one; ruling 9 forbids any
    limit. Forty positions must all come out.'''
    count = 40
    base = full_dir(tmp_path / 'cfg', eval_config=hit_tree(count))
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    paths = excinfo.value.paths
    assert len(paths) == count
    assert tuple(paths) == expected_hit_paths(count)
    assert count == len(str(excinfo.value).splitlines()) - 1


def test_t05_b11_deduplication_is_reachable_through_a_key_collision():
    '''Ruling 24 item 2 / ruling 9: one path appears once. Under str keys alone
    two positions can never render to the same path string, so deduplication
    stays unfalsifiable there; yaml does let the int key 1 and the str key '1'
    sit in one mapping, and the walk spells a non-string key out textually, so
    those two hit positions collapse onto one path. The raw walk still reports
    both, because ruling 11 makes find_placeholders neither sort nor
    deduplicate, while scan_config_trees reports the path exactly once. The 1
    below is a key-collision probe, not a business value (H-5).'''
    tree = {1: 'TODO', '1': 'TBD'}
    assert cfg('find_placeholders')(tree, root='s') == ('s.1', 's.1')
    assert cfg('scan_config_trees')({'s': tree}) == ('s.1',)


def test_t05_b12_the_constructor_reorders_a_reverse_file_order_input():
    '''Ruling 23 allowed addition 1: the ruling 9 key applies to any iterable,
    so a caller that lists the paths in the reverse file order still gets the
    [L1250]-[L1257] order out -- eval_config, weights, grade_rules,
    ahp_matrices. Every weights_*.yaml stem shares the single weights rank and
    is separated inside it by its path string (ruling 9).'''
    err = placeholder_error()(['ahp_matrices.SYN-q', 'grade_rules.SYN-p',
                               'weights_WV-SYN-01.SYN-o', 'eval_config.SYN-n'])
    assert err.paths == ('eval_config.SYN-n', 'weights_WV-SYN-01.SYN-o',
                         'grade_rules.SYN-p', 'ahp_matrices.SYN-q')


def test_t05_b13_an_unknown_stem_sorts_last_and_is_path_sorted_inside():
    '''Ruling 23 allowed addition 2: a stem outside the [L1250]-[L1257] list
    keeps the last file rank, which keeps the ruling 9 key total for the
    synthetic stems a property test hands in (ruling 16, T05-I i13), and inside
    that trailing block the paths stay string ascending.'''
    err = placeholder_error()(['SYN-unknown.SYN-b', 'eval_config.SYN-a',
                               'SYN-unknown.SYN-a', 'redlines.SYN-c'])
    assert err.paths == ('eval_config.SYN-a', 'redlines.SYN-c',
                         'SYN-unknown.SYN-a', 'SYN-unknown.SYN-b')


# ---------------------------------------------------------------------------
# T05-C. Ruling 5 hit table: strip, case insensitive, whole value or prefix.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('value', HIT_STRINGS)
def test_t05_c01_ruling_5_hit_strings_are_placeholders(value):
    assert cfg('is_placeholder_value')(value) is True


@pytest.mark.parametrize('value', MISS_STRINGS)
def test_t05_c02_ruling_5_miss_strings_are_not_placeholders(value):
    assert cfg('is_placeholder_value')(value) is False


@pytest.mark.parametrize('value', MISS_SCALARS)
def test_t05_c03_non_string_scalars_are_filled_values(value):
    '''Ruling 5: int / float / bool never hit; their business plausibility is
    S1-T06 semantic validation, not T05.'''
    assert cfg('is_placeholder_value')(value) is False


@pytest.mark.parametrize('value', MISS_CONTAINERS)
def test_t05_c04_containers_are_not_placeholder_values_themselves(value):
    '''Ruling 5 covers strings and ruling 6 covers None; a dict or a list is
    neither, so is_placeholder_value must say False and let find_placeholders
    recurse into it.'''
    assert cfg('is_placeholder_value')(value) is False


def test_t05_c05_a_substring_is_not_a_hit_inside_a_real_tree():
    '''Ruling 5 explicitly refuses substring matching, so free text such as a
    rationale cannot be wounded by accident.'''
    tree = {'SYN-note': 'SYN-abcTODOdef', 'SYN-other': {'SYN-inner': 'XPLACEHOLDER'}}
    assert cfg('find_placeholders')(tree, root='eval_config') == ()


def test_t05_c06_dict_keys_are_never_scanned():
    '''Ruling 5: a key is not a value. A placeholder spelled key with a filled
    value is a schema question for S1-T06, not a T05 hit.'''
    tree = {'PLACEHOLDER_SYN-KEY': 'SYN-OK', 'TODO': 'SYN-OK',
            'TBD': ['SYN-OK'], 'XXX': {'SYN-inner': 'SYN-OK'}}
    assert cfg('find_placeholders')(tree, root='eval_config') == ()


def test_t05_c07_placeholder_tokens_hold_the_four_ruling_5_words():
    assert cfg('PLACEHOLDER_TOKENS') == PLACEHOLDER_WORDS


def test_t05_c08_placeholder_prefixes_hold_the_same_four_words():
    assert tuple(cfg('PLACEHOLDER_PREFIXES')) == PLACEHOLDER_WORDS


@pytest.mark.parametrize('name', ['PLACEHOLDER_TOKENS', 'PLACEHOLDER_PREFIXES'])
def test_t05_c09_the_token_constants_are_tuples_of_str(name):
    resolved = cfg(name)
    assert type(resolved) is tuple
    assert resolved
    assert all(type(word) is str for word in resolved)


@pytest.mark.parametrize('value', ['placeholder_k-01', 'Todo_SYN-FILL',
                                   'tbd-syn', 'XXX_SYN'])
def test_t05_c10_the_prefix_branch_is_case_insensitive(value):
    '''Ruling 5 (b) / (c): the prefix branch runs on v.strip().upper().'''
    assert cfg('is_placeholder_value')(value) is True


def test_t05_c11_a_prefixed_variant_survives_a_full_tree_scan():
    tree = {'weight_construction': {'alpha_floor': 'PLACEHOLDER_K-15'}}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.weight_construction.alpha_floor',)


@pytest.mark.parametrize('value', ['', '   ', '\t\n '])
def test_t05_c12_ruling_19_empty_and_whitespace_only_strings_are_not_placeholders(value):
    '''Ruling 19 / ruling 24 item 1: the ruling 5 if-and-only-if is closed, so
    the empty string and a whitespace-only string are filled values rather than
    placeholders -- stripping them leaves nothing, which is neither one of the
    four tokens nor a prefix of one. Pinning is_placeholder_value alone would
    leave the tree level behaviour ungated, so the same value is walked as a
    leaf too: it must produce no path at all, neither in the raw walk nor after
    the ruling 9 sort. This is the gate that falsifies an over-tightened hit
    rule (mutant M09 of the L4 mutation run).'''
    assert cfg('is_placeholder_value')(value) is False
    tree = {'SYN-note': value, 'SYN-deeper': {'SYN-leaf': value}}
    assert cfg('find_placeholders')(tree, root='eval_config') == ()
    assert cfg('scan_config_trees')({'eval_config': tree}) == ()


# ---------------------------------------------------------------------------
# T05-D. Ruling 6: None always hits, because the SDD never says where the
# "declared mandatory" bit would come from.
# ---------------------------------------------------------------------------
def test_t05_d01_is_placeholder_value_none_is_true():
    assert cfg('is_placeholder_value')(None) is True


def test_t05_d02_a_top_level_none_value_hits():
    tree = {'SYN-a': None, 'SYN-b': 'SYN-OK'}
    assert cfg('find_placeholders')(tree, root='eval_config') == ('eval_config.SYN-a',)


def test_t05_d03_a_nested_dict_none_hits():
    tree = {'weight_construction': {'alpha_floor': None}}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.weight_construction.alpha_floor',)


def test_t05_d04_a_list_element_none_hits():
    tree = {'thresholds': ['SYN-OK', None, 'SYN-OK']}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.thresholds[1]',)


def test_t05_d05_a_none_inside_a_list_of_dicts_hits():
    tree = {'levels': [{'action': 'SYN-OK'}, {'action': None}]}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.levels[1].action',)


def test_t05_d06_a_deeply_nested_none_hits():
    tree = {'a': {'b': [{'c': {'d': [None]}}]}}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.a.b[0].c.d[0]',)


@pytest.mark.parametrize('stem', REQUIRED_STEMS)
def test_t05_d07_an_empty_yaml_file_hits_as_its_bare_stem(stem, tmp_path):
    '''Ruling 6 corollary: safe_load of an empty file is None, so the whole
    tree hits and the path is the stem alone (ruling 8).'''
    base = full_dir(tmp_path / 'cfg', **{stem: EMPTY_FILE})
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.paths == (stem,)


def test_t05_d08_a_comment_only_yaml_file_hits_as_its_bare_stem(tmp_path):
    base = full_dir(tmp_path / 'cfg', redlines=COMMENT_ONLY_FILE)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.paths == ('redlines',)


def test_t05_d09_none_is_never_treated_as_an_optional_absence(tmp_path):
    '''Ruling 6: "optional and unset" is spelled by omitting the key. An
    explicit null is an unfilled slot and must be blocked.'''
    with_null = {'SYN-optional': None}
    without_key = {}
    base_hit = full_dir(tmp_path / 'hit', eval_config=with_null)
    base_ok = full_dir(tmp_path / 'ok', eval_config=without_key)
    with pytest.raises(placeholder_error()):
        load_all(base_hit)
    assert isinstance(load_all(base_ok), cfg('AppConfig'))


def test_t05_d10_every_none_in_a_tree_is_reported():
    tree = {'a': None, 'b': {'c': None}, 'd': [None, None]}
    paths = cfg('find_placeholders')(tree, root='eval_config')
    assert sorted(paths) == ['eval_config.a', 'eval_config.b.c',
                             'eval_config.d[0]', 'eval_config.d[1]']


# ---------------------------------------------------------------------------
# T05-E. Ruling 8 path notation.
# ---------------------------------------------------------------------------
def test_t05_e01_nested_dicts_are_joined_with_dots():
    tree = {'weight_construction': {'alpha_floor': 'PLACEHOLDER'}}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.weight_construction.alpha_floor',)


def test_t05_e02_list_indices_are_zero_based_and_bracketed():
    tree = {'thresholds': ['SYN-OK', 'SYN-OK', 'PLACEHOLDER']}
    assert cfg('find_placeholders')(tree, root='eval_config') == (
        'eval_config.thresholds[2]',)


def test_t05_e03_a_top_level_scalar_is_stem_dot_key():
    assert cfg('find_placeholders')({'status': 'TODO'}, root=WEIGHTS_STEM_A) == (
        WEIGHTS_STEM_A + '.status',)


def test_t05_e04_a_none_tree_reports_the_bare_stem():
    assert cfg('find_placeholders')(None, root='redlines') == ('redlines',)
    assert cfg('scan_config_trees')({'redlines': None}) == ('redlines',)


@pytest.mark.parametrize('stem', WEIGHTS_STEMS)
def test_t05_e05_each_weights_file_keeps_its_own_stem(stem, tmp_path):
    trees = clean_trees()
    trees[stem] = {'dimensions': [{'weight': 'PLACEHOLDER'}]}
    base = write_trees(tmp_path / 'cfg', trees)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.paths == (stem + '.dimensions[0].weight',)


def test_t05_e06_two_weights_files_do_not_mix_their_stems(tmp_path):
    trees = clean_trees()
    trees[WEIGHTS_STEM_A] = {'dimensions': [{'weight': 'PLACEHOLDER'}]}
    trees[WEIGHTS_STEM_B] = {'status': 'TODO'}
    base = write_trees(tmp_path / 'cfg', trees)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert set(excinfo.value.paths) == {
        WEIGHTS_STEM_A + '.dimensions[0].weight',
        WEIGHTS_STEM_B + '.status'}


def test_t05_e07_nested_lists_chain_their_indices():
    tree = {'pairwise': [['SYN-OK', None], [None, 'SYN-OK']]}
    assert cfg('find_placeholders')(tree, root='ahp_matrices') == (
        'ahp_matrices.pairwise[0][1]', 'ahp_matrices.pairwise[1][0]')


def test_t05_e08_the_root_argument_is_used_as_the_path_prefix():
    tree = {'SYN-a': 'PLACEHOLDER'}
    assert cfg('find_placeholders')(tree, root='grade_rules') == ('grade_rules.SYN-a',)
    assert cfg('find_placeholders')(tree, root=WEIGHTS_STEM_C) == (
        WEIGHTS_STEM_C + '.SYN-a',)


def test_t05_e09_the_default_root_produces_paths_without_a_leading_dot():
    tree = {'SYN-outer': {'SYN-inner': 'PLACEHOLDER'}, 'SYN-items': [None]}
    bare = cfg('find_placeholders')(tree)
    rooted = cfg('find_placeholders')(tree, root='eval_config')
    prefix = 'eval_config.'
    assert tuple(path[len(prefix):] for path in rooted) == tuple(bare)
    assert not any(path.startswith('.') for path in bare)


def test_t05_e10_paths_never_carry_the_yaml_extension(tmp_path):
    base = full_dir(tmp_path / 'cfg', eval_config={'alpha_floor': 'PLACEHOLDER'})
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    for path in excinfo.value.paths:
        assert '.yaml' not in path


def test_t05_e11_a_list_of_dicts_spells_key_index_key():
    '''The ruling 8 example shape: dimensions[0].metrics[3].weight.'''
    tree = {'dimensions': [{'metrics': ['SYN-OK', 'SYN-OK', 'SYN-OK',
                                        {'weight': 'PLACEHOLDER'}]}]}
    assert cfg('find_placeholders')(tree, root=WEIGHTS_STEM_A) == (
        WEIGHTS_STEM_A + '.dimensions[0].metrics[3].weight',)


# ---------------------------------------------------------------------------
# T05-F. Ruling 9 determinism, deduplication and the fixed file order.
# ---------------------------------------------------------------------------
def test_t05_f01_the_same_input_twice_is_byte_identical():
    trees = {
        'eval_config': {'b': 'TODO', 'a': {'z': None}},
        WEIGHTS_STEM_A: {'status': 'PLACEHOLDER'},
        'redlines': {'HARD': [{'threshold': 'XXX'}]},
    }
    first = cfg('scan_config_trees')(copy.deepcopy(trees))
    second = cfg('scan_config_trees')(copy.deepcopy(trees))
    assert first == second
    assert repr(first) == repr(second)


def test_t05_f02_files_are_reported_in_the_l1250_to_l1257_order(tmp_path):
    '''Ruling 9: eval_config, weights (stem ascending), redlines, grade_rules,
    anchor_set, ahp_matrices. The dict below is inserted backwards on
    purpose.'''
    trees = {
        'ahp_matrices': {'expert_id': 'PLACEHOLDER'},
        'anchor_set': {'rationale': 'TODO'},
        'grade_rules': {'levels': [{'action': 'TBD'}]},
        'redlines': {'HARD': [{'threshold': 'XXX'}]},
        WEIGHTS_STEM_B: {'status': 'PLACEHOLDER'},
        WEIGHTS_STEM_A: {'status': 'PLACEHOLDER'},
        'eval_config': {'evidence_mode': 'PLACEHOLDER'},
    }
    base = write_trees(tmp_path / 'cfg', trees)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    seen = []
    for path in excinfo.value.paths:
        stem = path.split('.')[0].split('[')[0]
        if not seen or seen[-1] != stem:
            seen.append(stem)
    assert seen == ['eval_config', WEIGHTS_STEM_A, WEIGHTS_STEM_B, 'redlines',
                    'grade_rules', 'anchor_set', 'ahp_matrices']
    assert seen[:1] + seen[3:] == [name for name in FILE_ORDER if name != 'weights']


def test_t05_f03_weights_stems_are_sorted_ascending():
    trees = {
        WEIGHTS_STEM_C: {'SYN-a': 'TODO'},
        WEIGHTS_STEM_A: {'SYN-a': 'TODO'},
        WEIGHTS_STEM_B: {'SYN-a': 'TODO'},
    }
    assert cfg('scan_config_trees')(trees) == (
        WEIGHTS_STEM_A + '.SYN-a',
        WEIGHTS_STEM_B + '.SYN-a',
        WEIGHTS_STEM_C + '.SYN-a')


def test_t05_f04_paths_inside_one_file_are_string_sorted():
    tree = {'zulu': 'PLACEHOLDER', 'alpha': 'TODO', 'Mike': 'TBD',
            'beta': {'SYN-x': None}}
    paths = cfg('scan_config_trees')({'eval_config': tree})
    assert paths == tuple(sorted(paths))
    assert tuple(paths) == ('eval_config.Mike', 'eval_config.alpha',
                            'eval_config.beta.SYN-x', 'eval_config.zulu')


def test_t05_f05_the_result_does_not_depend_on_dict_insertion_order():
    keys = ['k%02d' % index for index in range(6)]
    forward = {key: 'PLACEHOLDER' for key in keys}
    backward = {key: 'PLACEHOLDER' for key in reversed(keys)}
    first = cfg('scan_config_trees')({'eval_config': forward})
    second = cfg('scan_config_trees')({'eval_config': backward})
    assert first == second
    assert first == tuple('eval_config.' + key for key in sorted(keys))


def test_t05_f06_scan_config_trees_sorts_across_several_files():
    trees = {'redlines': {'z': 'PLACEHOLDER', 'a': 'TODO'},
             'eval_config': {'m': 'TBD', 'b': 'XXX'}}
    assert cfg('scan_config_trees')(trees) == (
        'eval_config.b', 'eval_config.m', 'redlines.a', 'redlines.z')


def test_t05_f07_find_placeholders_keeps_traversal_order_not_sorted_order():
    '''Ruling 11: find_placeholders is the raw walk, the sorting happens in
    scan_config_trees.'''
    tree = {'zeta': 'PLACEHOLDER', 'alpha': 'TODO', 'mid': None}
    assert cfg('find_placeholders')(tree, root='SYN-ROOT') == (
        'SYN-ROOT.zeta', 'SYN-ROOT.alpha', 'SYN-ROOT.mid')


# ---------------------------------------------------------------------------
# T05-G. Ruling 10 / V-14: a missing required file rides the very same single
# exit, never a silent empty tree.
# ---------------------------------------------------------------------------
def test_t05_g01_a_single_missing_required_file_is_reported(tmp_path):
    base = dir_without(tmp_path / 'cfg', 'redlines')
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert 'redlines' in excinfo.value.missing_files


def test_t05_g02_missing_files_is_a_tuple_of_stems(tmp_path):
    base = dir_without(tmp_path / 'cfg', 'redlines')
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert type(excinfo.value.missing_files) is tuple
    assert all(type(stem) is str for stem in excinfo.value.missing_files)


def test_t05_g03_all_five_missing_files_are_reported_at_once(tmp_path):
    base = write_trees(tmp_path / 'cfg',
                       {WEIGHTS_STEM_A: _clean_weights(WEIGHTS_STEM_A)})
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert set(REQUIRED_STEMS) <= set(excinfo.value.missing_files)
    assert len(excinfo.value.missing_files) == len(set(excinfo.value.missing_files))


def test_t05_g04_no_weights_file_at_all_counts_as_missing(tmp_path):
    '''Ruling 10: weights_*.yaml is a wildcard, but at least one must exist.'''
    base = dir_without(tmp_path / 'cfg', WEIGHTS_STEM_A)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.missing_files
    assert any('weights' in stem for stem in excinfo.value.missing_files)


def test_t05_g05_missing_files_and_placeholder_paths_share_one_exit(tmp_path):
    '''[L878] "not only the first one": both lists leave through one raise.'''
    trees = clean_trees()
    trees.pop('redlines')
    trees['eval_config'] = {'alpha_floor': 'PLACEHOLDER'}
    base = write_trees(tmp_path / 'cfg', trees)
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.paths == ('eval_config.alpha_floor',)
    assert 'redlines' in excinfo.value.missing_files


def test_t05_g06_no_appconfig_is_returned_when_a_file_is_missing(tmp_path):
    '''V-14: no silent degradation, so nothing is returned either.'''
    err = placeholder_error()
    appconfig = cfg('AppConfig')
    base = dir_without(tmp_path / 'cfg', 'grade_rules')
    produced = []
    try:
        produced.append(load_all(base))
    except err:
        pass
    assert produced == []
    assert not any(isinstance(item, appconfig) for item in produced)


def test_t05_g07_the_message_appends_the_missing_block_after_a_blank_line():
    err = placeholder_error()(['eval_config.SYN-a'], ['redlines'])
    lines = str(err).splitlines()
    assert lines[0] == MSG_HEAD % (1, EXIT_CODE)
    assert lines[1] == MSG_ITEM % 'eval_config.SYN-a'
    assert lines[2] == ''
    assert lines[3] == MSG_MISSING_HEAD % 1
    assert lines[4:] == [MSG_ITEM % 'redlines']


def test_t05_g08_an_empty_config_dir_reports_everything_missing(tmp_path):
    base = tmp_path / 'cfg'
    base.mkdir()
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    missing = excinfo.value.missing_files
    assert set(REQUIRED_STEMS) <= set(missing)
    assert any('weights' in stem for stem in missing)
    assert excinfo.value.paths == ()


def test_t05_g09_required_config_stems_hold_the_five_fixed_names_in_order():
    assert tuple(cfg('REQUIRED_CONFIG_STEMS')) == REQUIRED_STEMS


def test_t05_g10_the_weights_glob_constant_is_verbatim():
    assert cfg('WEIGHTS_GLOB') == WEIGHTS_GLOB


def test_t05_g11_missing_files_are_deduplicated_and_deterministic():
    '''The order of missing_files is not settled by ruling 10, so this asserts
    content, deduplication and determinism only (flagged to the orchestrator).'''
    err = placeholder_error()
    first = err((), ['redlines', 'redlines', 'grade_rules'])
    second = err((), ['grade_rules', 'redlines', 'grade_rules'])
    assert first.missing_files == second.missing_files
    assert set(first.missing_files) == {'redlines', 'grade_rules'}
    assert len(first.missing_files) == 2


def test_t05_g12_an_unrelated_yaml_file_is_not_required(tmp_path):
    trees = clean_trees()
    trees['SYN-unrelated'] = {'SYN-a': 'SYN-OK'}
    base = write_trees(tmp_path / 'cfg', trees)
    assert isinstance(load_all(base), cfg('AppConfig'))


def test_t05_g13_a_missing_file_is_never_replaced_by_an_empty_tree(tmp_path):
    base = dir_without(tmp_path / 'cfg', 'anchor_set')
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(base)
    assert excinfo.value.exit_code == EXIT_CODE
    assert 'anchor_set' in excinfo.value.missing_files


# ---------------------------------------------------------------------------
# T05-H. Ruling 3: six file level slots, frozen, extra=forbid, and no
# invented field level schema for the [L1250]-[L1257] content list.
# ---------------------------------------------------------------------------
def test_t05_h01_appconfig_declares_exactly_the_six_slots():
    assert set(cfg('AppConfig').model_fields) == set(SIX_SLOTS)
    assert len(cfg('AppConfig').model_fields) == 6


@pytest.mark.parametrize('slot', SIX_SLOTS)
def test_t05_h02_each_of_the_six_slot_names_is_verbatim(slot):
    assert slot in cfg('AppConfig').model_fields


@pytest.mark.parametrize('slot', SIX_SLOTS)
def test_t05_h03_a_built_appconfig_refuses_reassignment(slot):
    '''Ruling 3: frozen=True, the same discipline as the models layer
    (V-5 [L871]).'''
    built = build_appconfig()
    with pytest.raises(ValidationError):
        setattr(built, slot, {})


def test_t05_h04_an_undeclared_slot_is_rejected():
    '''Ruling 3 / V-5 [L871]: extra='forbid'.'''
    with pytest.raises(ValidationError):
        build_appconfig(**{'SYN_UNDECLARED_SLOT': {}})


def test_t05_h05_the_weights_slot_is_keyed_by_file_stem(tmp_path):
    trees = clean_trees()
    trees[WEIGHTS_STEM_B] = _clean_weights(WEIGHTS_STEM_B)
    base = write_trees(tmp_path / 'cfg', trees)
    loaded = load_all(base)
    assert set(loaded.weights) == {WEIGHTS_STEM_A, WEIGHTS_STEM_B}
    assert loaded.weights[WEIGHTS_STEM_B]['weight_version_id'] == WEIGHTS_STEM_B


def test_t05_h06_config_tree_is_the_dict_str_any_alias():
    assert cfg('ConfigTree') == dict[str, Any]


def test_t05_h07_no_field_level_schema_was_invented_for_the_content_keys():
    '''Ruling 3 forbids promoting any [L1250]-[L1257] content key into an
    AppConfig field: the SDD gives no field names, no nesting and no types.'''
    fields = set(cfg('AppConfig').model_fields)
    assert fields == set(SIX_SLOTS)
    invented = [key for key in CONTENT_KEYS if key in fields]
    assert not invented, 'invented field level schema: ' + repr(invented)


def test_t05_h08_appconfig_is_a_pydantic_basemodel():
    assert issubclass(cfg('AppConfig'), BaseModel)


def test_t05_h09_model_config_is_frozen_and_extra_forbid():
    conf = cfg('AppConfig').model_config
    assert conf.get('frozen') is True
    assert conf.get('extra') == 'forbid'


def test_t05_h10_raw_yaml_scalars_are_preserved_without_conversion(tmp_path):
    '''Ruling 4: int / float scalars stay exactly as safe_load returned them;
    T05 converts nothing (the numeric gate is S1-T06, blocker B-022).'''
    tree = {'type_probe_int': TYPE_PROBE_ONE,
            'type_probe_float': TYPE_PROBE_FLOAT,
            'type_probe_bool': True,
            'type_probe_text': 'SYN-OK'}
    base = full_dir(tmp_path / 'cfg', eval_config=tree)
    loaded = load_all(base)
    assert loaded.eval_config == tree
    assert type(loaded.eval_config['type_probe_int']) is int
    assert type(loaded.eval_config['type_probe_float']) is float
    assert type(loaded.eval_config['type_probe_bool']) is bool


def test_t05_h11_a_fully_filled_dir_loads_into_an_appconfig(tmp_path):
    base = full_dir(tmp_path / 'cfg')
    loaded = load_all(base)
    assert isinstance(loaded, cfg('AppConfig'))
    assert set(loaded.weights) == {WEIGHTS_STEM_A}
    assert loaded.eval_config == _clean_eval_config()


def test_t05_h12_every_one_of_the_six_slots_is_required():
    for slot in SIX_SLOTS:
        payload = appconfig_payload()
        del payload[slot]
        with pytest.raises(ValidationError):
            cfg('AppConfig')(**payload)


# ---------------------------------------------------------------------------
# T05-I. H-8 purity, checked on the source text (AST) and on the behaviour.
# ---------------------------------------------------------------------------
WALL_CLOCK_PATHS = (
    'datetime.now', 'datetime.utcnow', 'date.today', 'time.time',
    'time.localtime', 'time.gmtime', 'time.monotonic', 'time.time_ns',
    'datetime.today', 'datetime.now', 'time.perf_counter',
)
IO_CALL_NAMES = frozenset({
    'open', 'Path.open', 'Path.read_text', 'Path.write_text',
    'Path.read_bytes', 'Path.write_bytes', 'Path.glob', 'Path.rglob',
    'Path.iterdir', 'Path.exists', 'Path.is_file', 'Path.is_dir',
    'Path.mkdir', 'glob.glob', 'glob.iglob', 'os.listdir', 'os.walk',
    'os.scandir', 'yaml.safe_load', 'yaml.load', 'safe_load',
})
IO_LEAF_NAMES = frozenset({
    'open', 'read_text', 'write_text', 'read_bytes', 'write_bytes', 'glob',
    'rglob', 'iterdir', 'listdir', 'scandir', 'safe_load', 'mkdir',
})
CLOCK_LEAF_NAMES = frozenset({'now', 'utcnow', 'today', 'time', 'localtime',
                              'gmtime', 'monotonic', 'perf_counter',
                              'time_ns'})
FORBIDDEN_IMPORTS = ('subprocess', 'socket', 'urllib', 'requests', 'random',
                     'uuid', 'tempfile', 'time', 'datetime', 'os', 'sys',
                     'shutil', 'csv', 'json', 'pickle', 'glob', 'pandas',
                     'numpy', 'typer')
L0_MODULES = ('weights_ahp', 'weights_combine', 'fixtures_gen',
              'weights_calibrate', 'whatif')
L1_PEERS = ('models', 'numeric', 'reason_codes')


def _io_offenders(node):
    found = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            dotted = _dotted(child.func)
            if dotted in IO_CALL_NAMES or dotted.split('.')[-1] in IO_LEAF_NAMES:
                found.append(dotted or '<unknown call>')
    return found


def test_t05_i01_config_source_reads_no_wall_clock():
    '''H-8 / ruling 11: --run-at is injected ([L1089]); the config layer never
    asks the operating system what time it is.'''
    calls = [_dotted(node.func) for node in ast.walk(_config_ast())
             if isinstance(node, ast.Call)]
    offenders = [path for path in calls if path in WALL_CLOCK_PATHS]
    offenders += [path for path in calls
                  if path.split('.')[-1] in CLOCK_LEAF_NAMES]
    assert not offenders, 'wall-clock read in config.py: ' + repr(offenders)


def test_t05_i02_is_placeholder_value_takes_exactly_one_argument():
    signature = inspect.signature(cfg('is_placeholder_value'))
    assert list(signature.parameters) == ['value']
    param = signature.parameters['value']
    assert param.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    assert param.default is inspect.Parameter.empty


def test_t05_i03_find_placeholders_is_tree_plus_a_keyword_only_root():
    signature = inspect.signature(cfg('find_placeholders'))
    assert list(signature.parameters) == ['tree', 'root']
    assert signature.parameters['tree'].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    root = signature.parameters['root']
    assert root.kind is inspect.Parameter.KEYWORD_ONLY
    assert root.default == ''


def test_t05_i04_scan_config_trees_takes_exactly_one_argument():
    assert list(inspect.signature(cfg('scan_config_trees')).parameters) == ['trees']


def test_t05_i05_load_all_takes_only_config_dir():
    '''Ruling 11: the T05 signature is minimal; T06 adds --period / --run-at as
    optional keywords, which is not a breaking change.'''
    assert list(inspect.signature(cfg('load_all')).parameters) == ['config_dir']


@pytest.mark.parametrize('name', PURE_FUNCTIONS)
def test_t05_i06_the_pure_functions_perform_no_io(name):
    node = _function_nodes(_config_ast()).get(name)
    if node is None:
        raise AttributeError('dsm.config defines no function ' + name
                             + ' (ORCH-23 ruling 11)')
    offenders = _io_offenders(node)
    assert not offenders, name + ' performs I/O: ' + repr(offenders)


def test_t05_i07_config_module_declares_no_global_or_nonlocal_mutation():
    offenders = [node.lineno for node in ast.walk(_config_ast())
                 if isinstance(node, (ast.Global, ast.Nonlocal))]
    assert not offenders, 'global/nonlocal at lines ' + repr(offenders)


@pytest.mark.parametrize('name', PURE_FUNCTIONS)
def test_t05_i08_the_pure_functions_are_idempotent(name):
    fn = cfg(name)
    first = PURE_CALLS[name](fn)
    second = PURE_CALLS[name](fn)
    assert first == second
    assert repr(first) == repr(second)


@pytest.mark.parametrize('name', PURE_FUNCTIONS)
def test_t05_i09_the_pure_functions_do_not_mutate_their_input(name):
    fn = cfg(name)
    if name == 'is_placeholder_value':
        argument = {'SYN-a': ['PLACEHOLDER', None], 'SYN-c': 'TODO'}
    elif name == 'find_placeholders':
        argument = {'SYN-a': {'SYN-b': None}, 'SYN-c': ['TODO']}
    else:
        argument = {'eval_config': {'SYN-a': None}, 'redlines': {'SYN-b': 'TBD'}}
    before = copy.deepcopy(argument)
    if name == 'scan_config_trees':
        fn(argument)
    elif name == 'find_placeholders':
        fn(argument, root='eval_config')
    else:
        fn(argument['SYN-a'])
        fn(argument['SYN-c'])
    assert argument == before


def test_t05_i10_the_pure_calls_leave_the_module_globals_untouched():
    module = _config_module()
    before = {key: repr(value) for key, value in sorted(vars(module).items())}
    for name in PURE_FUNCTIONS:
        PURE_CALLS[name](cfg(name))
    after = {key: repr(value) for key, value in sorted(vars(module).items())}
    assert before == after


def test_t05_i11_load_all_is_the_only_public_io_entry_point():
    offenders = []
    for name, node in sorted(_function_nodes(_config_ast()).items()):
        if name.startswith('_') or name == 'load_all':
            continue
        offenders += [(name, call) for call in _io_offenders(node)]
    assert not offenders, 'I/O outside load_all: ' + repr(offenders)


def test_t05_i12_config_module_imports_no_clock_process_or_random_module():
    imports = _top_level_imports(_config_ast())
    offenders = [name for name in imports if name in FORBIDDEN_IMPORTS]
    assert not offenders, 'forbidden import in config.py: ' + repr(offenders)


def test_t05_i13_scan_config_trees_never_reads_the_filesystem():
    '''A pure function must work on a tree that exists nowhere on disk.'''
    trees = {'SYN-NOT-A-FILE': {'SYN-a': 'PLACEHOLDER'}}
    paths = cfg('scan_config_trees')(trees)
    assert paths == ('SYN-NOT-A-FILE.SYN-a',)


# ---------------------------------------------------------------------------
# T05-K. H-9 INV-1 layering, ruling 12.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize('forbidden_module', L0_MODULES)
def test_t05_k01_config_does_not_import_an_l0_module(forbidden_module):
    imports = _imported_names(_config_ast())
    offenders = [name for name in imports
                 if name.split('.')[-1] == forbidden_module]
    assert not offenders, 'config.py imports ' + forbidden_module + ': ' + repr(offenders)


@pytest.mark.parametrize('peer', L1_PEERS)
def test_t05_k02_the_t05_stage_does_not_import_its_l1_peers(peer):
    '''Ruling 12: T05 needs none of models / numeric / reason_codes; T06 may
    add them later as an authorised extension.'''
    offenders = []
    for node in ast.walk(_config_ast()):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module == 'dsm':
                offenders += ['dsm.' + alias_.name for alias_ in node.names
                              if alias_.name == peer]
            elif module == 'dsm.' + peer:
                offenders.append(module)
        elif isinstance(node, ast.Import):
            offenders += [alias_.name for alias_ in node.names
                          if alias_.name in ('dsm.' + peer, peer)]
    assert not offenders, 'config.py imports ' + peer + ': ' + repr(offenders)


def test_t05_k03_third_party_imports_are_only_yaml_and_pydantic():
    '''Ruling 12: stdlib plus yaml plus pydantic, nothing else.'''
    import sys as _sys
    imports = _top_level_imports(_config_ast())
    offenders = [name for name in imports
                 if name not in _sys.stdlib_module_names
                 and name not in ('yaml', 'pydantic')]
    assert not offenders, 'unexpected third party import: ' + repr(offenders)


def test_t05_k04_the_config_layer_lives_at_dsm_config_py():
    '''[L355] / [L816]: config.py is an L1 module inside the dsm package.'''
    module = _config_module()
    assert Path(module.__file__).resolve() == CONFIG_PATH


@pytest.mark.parametrize('as_path', [False, True])
def test_t05_k05_load_all_accepts_a_str_or_a_path(as_path, tmp_path):
    base = full_dir(tmp_path / 'cfg')
    loaded = cfg('load_all')(base if as_path else str(base))
    assert isinstance(loaded, cfg('AppConfig'))


def test_t05_k06_a_nonexistent_config_dir_is_a_missing_file_case(tmp_path):
    '''Ruling 10 / V-14: a directory that does not exist must not be waved
    through as an empty configuration.'''
    with pytest.raises(placeholder_error()) as excinfo:
        load_all(tmp_path / 'SYN-does-not-exist')
    assert set(REQUIRED_STEMS) <= set(excinfo.value.missing_files)


# ---------------------------------------------------------------------------
# T05-L. H-5 scanner. A business number is (a) any float literal outside a
# TYPE_PROBE assignment, (b) any numeric literal sitting under a business
# key / keyword / assignment name, (c) any non-docstring string that spells
# "business key: number", (d) any governance-parameter token (K-nn) that is
# not part of a PLACEHOLDER spelling.
# ---------------------------------------------------------------------------
_BUSINESS_WORD = ('weight|threshold|floor|budget|epsilon|alpha|target|price|'
                  'amount|period|cycle|sample|streak|divergence|shift|grid|'
                  'quota|attainment|ratio|rate')
BUSINESS_ASSIGNMENT = re.compile(
    r'(?i)\b(?:' + _BUSINESS_WORD + r')\w*\s*[:=]\s*[-+]?\d')
K_TOKEN = re.compile(r'K-[0-9][0-9]')
BUSINESS_KEY_SEGMENTS = (frozenset(_BUSINESS_WORD.split('|'))
                         | frozenset(key.lower() for key in CONTENT_KEYS))


def _is_business_name(name):
    if not isinstance(name, str) or not name:
        return False
    lowered = name.lower()
    if lowered in BUSINESS_KEY_SEGMENTS:
        return True
    parts = [part for part in re.split(r'[^a-z0-9]+', lowered) if part]
    return any(part in BUSINESS_KEY_SEGMENTS for part in parts)


def _is_number(node):
    if isinstance(node, ast.Constant):
        return type(node.value) in (int, float)
    if isinstance(node, ast.UnaryOp) and isinstance(node.operand, ast.Constant):
        return type(node.operand.value) in (int, float)
    return False


def _docstring_ids(tree):
    '''Docstrings are documentation, not values, so the H-5 scanner skips
    them; nothing a docstring says can reach a configuration file.'''
    holders = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = getattr(node, 'body', [])
        if not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
            if isinstance(first.value.value, str):
                found.add(id(first.value))
    return found


def _type_probe_ids(tree):
    allowed = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets
                 if isinstance(target, ast.Name)]
        if not any('TYPE_PROBE' in name for name in names):
            continue
        for child in ast.walk(node.value):
            if isinstance(child, ast.Constant):
                allowed.add(id(child))
    return allowed


def _business_number_offenders(tree):
    docstrings = _docstring_ids(tree)
    probes = _type_probe_ids(tree)
    offenders = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            value = node.value
            if isinstance(value, str):
                if id(node) in docstrings:
                    continue
                if K_TOKEN.search(value):
                    if not value.strip().upper().startswith('PLACEHOLDER'):
                        offenders.append((node.lineno, 'K-token', value))
                if BUSINESS_ASSIGNMENT.search(value):
                    offenders.append((node.lineno, 'business text', value))
            elif type(value) is float and id(node) not in probes:
                offenders.append((node.lineno, 'float literal', value))
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and isinstance(key.value, str):
                    if _is_business_name(key.value) and _is_number(value):
                        offenders.append((node.lineno, 'business key', key.value))
        elif isinstance(node, ast.keyword):
            if _is_business_name(node.arg or '') and _is_number(node.value):
                offenders.append((node.lineno, 'business kwarg', node.arg))
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and _is_business_name(target.id):
                    if _is_number(node.value):
                        offenders.append((node.lineno, 'business name', target.id))
    return offenders


def test_t05_l01_config_source_carries_no_business_number():
    '''T05-L / [L78] / [L1259] / [L1806]: the config layer proposes nothing.'''
    offenders = _business_number_offenders(_config_ast())
    assert not offenders, 'H-5 violation in dsm/config.py: ' + repr(offenders)


def test_t05_l02_config_source_contains_no_float_literal_at_all():
    offenders = [(node.lineno, node.value) for node in ast.walk(_config_ast())
                 if isinstance(node, ast.Constant) and type(node.value) is float]
    assert not offenders, 'float literal in config.py: ' + repr(offenders)


def test_t05_l03_config_source_spells_governance_slots_as_placeholder():
    '''If config.py carries any dict literal at all, a governance key inside
    it may only hold a PLACEHOLDER string, never a number and never a
    filled-in value (H-5 / H-10).'''
    offenders = []
    for node in ast.walk(_config_ast()):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                continue
            if not _is_business_name(key.value):
                continue
            if _is_number(value):
                offenders.append((node.lineno, key.value, 'number'))
            elif isinstance(value, ast.Constant) and isinstance(value.value, str):
                if not value.value.strip().upper().startswith('PLACEHOLDER'):
                    offenders.append((node.lineno, key.value, value.value))
    assert not offenders, 'invented governance value: ' + repr(offenders)


def test_t05_l04_this_test_file_carries_no_business_number():
    '''Positive control: the H-5 gate is applied to this file first, so the
    scanner itself is proven to run and to pass on synthetic data.'''
    tree = ast.parse(THIS_PATH.read_text(encoding='utf-8'))
    offenders = _business_number_offenders(tree)
    assert not offenders, 'H-5 violation in this file: ' + repr(offenders)


def test_t05_l05_the_property_test_file_carries_no_business_number():
    tree = ast.parse(PROPERTIES_PATH.read_text(encoding='utf-8'))
    offenders = _business_number_offenders(tree)
    assert not offenders, 'H-5 violation in the property file: ' + repr(offenders)


# ---------------------------------------------------------------------------
# T05-M. The do-not-break half of the gate. The other half ("the existing
# 1268 tests stay green") is a property of a full pytest run and is recorded
# in ops/evidence/S1-T05/L1-red.txt.
# ---------------------------------------------------------------------------
def test_t05_m01_the_existing_dsm_modules_still_import():
    for name in ('dsm.models', 'dsm.numeric', 'dsm.reason_codes'):
        assert importlib.import_module(name) is not None


def test_t05_m02_the_models_layer_still_reads_no_wall_clock():
    '''Positive control mirroring the existing S1-T04 gate, so a regression
    in the baseline shows up here too.'''
    tree = ast.parse(MODELS_PATH.read_text(encoding='utf-8'))
    calls = [_dotted(node.func) for node in ast.walk(tree)
             if isinstance(node, ast.Call)]
    offenders = [path for path in calls if path in WALL_CLOCK_PATHS]
    offenders += [path for path in calls
                  if path.endswith(('.now', '.utcnow', '.today', '.time'))]
    assert not offenders, 'wall-clock read in models.py: ' + repr(offenders)


def test_t05_m03_no_dsm_module_imports_an_l0_module():
    offenders = []
    for path in sorted(DSM_DIR.glob('*.py')):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for name in _imported_names(tree):
            if name.split('.')[-1] in L0_MODULES:
                offenders.append((path.name, name))
    assert not offenders, 'H-9 INV-1 violation: ' + repr(offenders)


def test_t05_m04_the_repository_config_directory_stays_empty():
    '''Ruling 13: the config dir belongs to the S2 fixtures write set, so no
    T05 test may leave a file behind in it.'''
    assert REPO_CONFIG_DIR.is_dir()
    assert sorted(REPO_CONFIG_DIR.iterdir()) == []


@pytest.mark.parametrize('pin', ['PyYAML==', 'hypothesis=='])
def test_t05_m05_requirements_still_pin_the_config_dependencies(pin):
    text = REQUIREMENTS_PATH.read_text(encoding='utf-8')
    assert any(line.startswith(pin) for line in text.splitlines()), text


def test_t05_m06_the_new_test_files_carry_no_skip_or_xfail_marker():
    '''T05-M "no new skip": an RED test must fail loudly, never be skipped or
    xfailed away.'''
    offenders = []
    for path in (THIS_PATH, PROPERTIES_PATH):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                if node.attr in ('skip', 'skipif', 'xfail'):
                    offenders.append((path.name, node.lineno, node.attr))
    assert not offenders, 'skip/xfail marker: ' + repr(offenders)


@pytest.mark.parametrize('path', [THIS_PATH, PROPERTIES_PATH])
def test_t05_m07_the_new_test_files_are_bom_free_lf_and_tab_free(path):
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf'), path.name + ' carries a BOM'
    assert raw.count(b'\r') == 0, path.name + ' carries a CR'
    assert raw.count(b'\t') == 0, path.name + ' carries a TAB'


def test_t05_m08_the_new_test_files_never_import_dsm_config_at_module_level():
    '''The RED gate itself: a top level import of dsm.config would turn every
    failure into a collection error, which is exactly what this file must not
    do (lazy naming, after tests/test_models_output.py).'''
    offenders = []
    for path in (THIS_PATH, PROPERTIES_PATH):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.Import):
                offenders += [alias_.name for alias_ in node.names
                              if alias_.name.startswith('dsm')]
            elif isinstance(node, ast.ImportFrom):
                if (node.module or '').startswith('dsm'):
                    offenders.append(node.module)
    assert not offenders, 'top level dsm import: ' + repr(offenders)
