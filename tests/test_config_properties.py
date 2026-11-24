'''P-10 property tests for the S1-T05 contract of dsm/config.py (RED by design).

[L882] names the guard: "P-10 (property test: no configuration containing a
PLACEHOLDER may ever produce a score)". [L1434] restates it as "any unreplaced
PLACEHOLDER raises at the configuration loading stage and never enters the
computation". The scoring chain does not exist before S4, so ORCH-23 ruling 14
translates P-10 into four statements that are decidable at the T05 layer, and
this file pins all four of them plus the reverse direction:

  1  a generated tree with at least one hit makes find_placeholders non-empty;
  2  load_all raises ConfigPlaceholderError (exit code 3);
  3  no AppConfig instance ever escapes, so nothing downstream can score;
  4  the reported paths cover every hit position, not just the first;
  5  (reverse) a tree whose leaves are all filled produces no path at all and
     loads into an AppConfig.

dsm/config.py does not exist yet. Every reference is lazy (_config_module /
cfg), so pytest collects this file with zero errors and each RED failure is a
ModuleNotFoundError or an AttributeError, matching the S1-T03 / S1-T04 RED
shape.

Reproducibility (H-14 / ruling 13): the settings object follows
tests/test_numeric_properties.py (max_examples plus deadline=None) and adds
derandomize=True with database=None, because ruling 13 demands that a rerun be
byte identical and the numeric file's strategies are value-domain driven while
these are structure driven. test_t05_j_s01 asserts the alignment instead of
just claiming it.

The expected values come from _oracle_hits / _is_hit_oracle, an independent
reading of ORCH-23 rulings 5 (hit rule), 6 (None always hits) and 8 (path
notation). The oracle lives in this test file, is never imported by dsm, and
is itself pinned by two positive controls (s02, s03) so a wrong oracle cannot
silently redefine the contract.

All data is synthetic (SYN- prefix, H-5 / H-14). No weight, threshold, floor,
target, price, period, sample size or governance value is proposed anywhere;
every governance-shaped slot holds PLACEHOLDER or a SYN- token. The only
numeric literals are the type probes 0 / 1 / -1 and TYPE_PROBE_FLOAT. Every
fixture is written under a private tempfile directory, never into the
repository config/ directory (ruling 13).
'''
import ast
import copy
import importlib
import re
import tempfile
from pathlib import Path

import pytest
import yaml
from hypothesis import given, settings, strategies as st

REPO_ROOT = Path(__file__).resolve().parent.parent
THIS_PATH = Path(__file__).resolve()
NUMERIC_PROPERTIES_PATH = REPO_ROOT / 'tests' / 'test_numeric_properties.py'

OPTS = settings(max_examples=60, deadline=None, derandomize=True, database=None)

EXIT_CODE = 3
WEIGHTS_STEM_A = 'weights_WV-SYN-0001'
PLACEHOLDER_WORDS = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
SYN_STEM = 'SYN-ROOT'

# Type probes only, never business values: they pin the int / float / bool
# branches of ruling 5, which say a filled scalar is not a placeholder.
TYPE_PROBE_FLOAT = 0.5  # 仅类型探针，非业务值


# ---------------------------------------------------------------------------
# Lazy resolution, identical in spirit to tests/test_models_output.py: name
# lookups only, so an unimplemented contract fails as AttributeError and the
# module always collects.
# ---------------------------------------------------------------------------
def _config_module():
    return importlib.import_module('dsm.config')


def cfg(name):
    module = _config_module()
    resolved = getattr(module, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.config has no attribute ' + name
            + ' (S1-T05 not implemented yet, ORCH-23 ruling 11)')
    return resolved


def placeholder_error():
    return cfg('ConfigPlaceholderError')


# ---------------------------------------------------------------------------
# The oracle: rulings 5 / 6 / 8 written out independently of dsm.config.
# ---------------------------------------------------------------------------
def _join(prefix, key):
    # A yaml mapping may carry a non-string key and the implementation spells it
    # out textually, so the oracle does the same (ruling 24 item 2 / observation
    # O1). For the str keys every other strategy draws this is the identity.
    name = key if isinstance(key, str) else str(key)
    return name if prefix == '' else prefix + '.' + name


def _is_hit_oracle(value):
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    upper = value.strip().upper()
    if upper in PLACEHOLDER_WORDS:
        return True
    return any(upper.startswith(word) for word in PLACEHOLDER_WORDS)


def _oracle_hits(node, prefix):
    if node is None:
        return [prefix]
    if isinstance(node, dict):
        found = []
        for key in node:
            found += _oracle_hits(node[key], _join(prefix, key))
        return found
    if isinstance(node, list):
        found = []
        for index, item in enumerate(node):
            found += _oracle_hits(item, '%s[%d]' % (prefix, index))
        return found
    if _is_hit_oracle(node):
        return [prefix]
    return []


# ---------------------------------------------------------------------------
# Strategies. FILLED_TEXTS are provably non-hitting under ruling 5 (no token
# equality, no token prefix, and the two embedded-token strings prove that
# substring matching stays off).
# ---------------------------------------------------------------------------
KEY_ALPHABET = 'abcdefghijklmnopqrstuvwxyz_'
# Ruling 19 / ruling 24 item 1: the empty string and whitespace-only strings are
# FILLED values, so they belong to the non-hitting alphabet. Carrying them here
# is what lets hypothesis falsify an over-tightened hit rule (mutant M09) on the
# property side as well; all three survive a yaml round trip byte for byte
# (safe_dump quotes them, safe_load returns them unchanged), so n03 still holds.
FILLED_TEXTS = ('SYN-OK', 'SYN-ACTIVE', 'SYN-SIGNED', 'SYN-FROZEN',
                'SYN-NOTE-01', 'SYN-abcTODOdef-not-a-token',
                'SYN-XPLACEHOLDER-not-a-token', '', '   ', '\t\n ')
PLACEHOLDER_VALUES = ('PLACEHOLDER', 'placeholder', '  PLACEHOLDER  ',
                      'PLACEHOLDER_K-01', 'TODO', 'TBD', 'XXX', None)

keys = st.text(alphabet=KEY_ALPHABET, min_size=1, max_size=4)
filled_leaf = st.one_of(
    st.sampled_from(FILLED_TEXTS),
    st.integers(min_value=-1, max_value=1),
    st.booleans(),
    st.just(TYPE_PROBE_FLOAT),
)
hit_leaf = st.sampled_from(PLACEHOLDER_VALUES)
mixed_leaf = st.one_of(filled_leaf, hit_leaf)


def _extend(children):
    return st.one_of(
        st.dictionaries(keys, children, min_size=1, max_size=3),
        st.lists(children, min_size=1, max_size=3),
    )


mixed_tree = st.recursive(mixed_leaf, _extend, max_leaves=8)
filled_tree = st.recursive(filled_leaf, _extend, max_leaves=8)
mixed_dict = st.dictionaries(keys, mixed_tree, min_size=1, max_size=3)
filled_dict = st.dictionaries(keys, filled_tree, min_size=1, max_size=3)


@st.composite
def tree_with_a_hit(draw):
    '''A random tree guaranteed to carry at least one hit, so no property
    below can pass vacuously and no assume() filter is needed.'''
    tree = draw(mixed_dict)
    tree[draw(keys)] = {'SYN-forced': draw(hit_leaf)}
    return tree


@st.composite
def colliding_dict(draw):
    '''A mapping that holds the int key 1 and the str key '1' side by side, both
    carrying a hit, plus up to two random extra keys so the shape stays random
    instead of fixed. That collision is the only reachable way two distinct
    positions can render to one and the same path string, which is what makes
    the ruling 9 deduplication falsifiable at all (ruling 24 items 2 and 3,
    mutant M12). The 1 is a key-collision probe, not a business value (H-5);
    the extra keys come from an alphabet without digits, so they can never
    collide with it by accident.'''
    tree = draw(st.dictionaries(keys, mixed_leaf, max_size=2))
    tree[1] = draw(hit_leaf)
    tree['1'] = draw(hit_leaf)
    return tree


# ---------------------------------------------------------------------------
# Synthetic on-disk fixtures (private tempdir only, ruling 13).
# ---------------------------------------------------------------------------
def _clean_slot(stem):
    return {'SYN-note': 'SYN-FILLED', 'SYN-status': 'SYN-FROZEN',
            'SYN-items': [{'SYN-code': 'SYN-C-01', 'SYN-flag': True}],
            'SYN-stem': stem}


def _clean_trees():
    # R-8 triage（依据见 commit message）：ORCH-24 line 43 定 validate_semantics
    # 由 load_all 一律调用，line 342 又要求既有 P-10 用例一条不改；二者对
    # test_t05_j_n03 直接冲突——T05 版 _clean_slot() 只保证「无占位」，在 T06
    # 语义门下必然被判 STRUCTURE 违规（grade_rules 无 levels），该用例将永远红。
    # 按 line 43 执行：只把本 fixture 的填充内容换成同文件 T06-Q 段已入册的合成
    # 树（全部取自既有 T06_Q_* 常量，不新增任何业务数），n03 的判定对象
    # 「[L1259] 不拦已填配置」与它的两条断言一字不改。
    return {'eval_config': _clean_slot('eval_config'),
            WEIGHTS_STEM_A: _t06_complete_tree('AHP_ONLY', WEIGHTS_STEM_A),
            'redlines': _t06_redlines(),
            'grade_rules': _t06_grade_rules(),
            'anchor_set': _t06_anchor(),
            'ahp_matrices': _t06_ahp_matrices()}


def _write_dir(base, **overrides):
    trees = _clean_trees()
    trees.update(overrides)
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    for stem, tree in trees.items():
        (base / (stem + '.yaml')).write_text(
            yaml.safe_dump(tree, allow_unicode=True, sort_keys=False),
            encoding='utf-8')
    return base


# ---------------------------------------------------------------------------
# H-5 scanner, the same gate this file applies to itself in s04. A business
# number is any float literal outside a TYPE_PROBE assignment, any numeric
# literal under a business key / keyword / assignment name, any non-docstring
# string spelling "business key: number", and any governance token (K-nn)
# that is not part of a PLACEHOLDER spelling.
# ---------------------------------------------------------------------------
_BUSINESS_WORD = ('weight|threshold|floor|budget|epsilon|alpha|target|price|'
                  'amount|period|cycle|sample|streak|divergence|shift|grid|'
                  'quota|attainment|ratio|rate')
_CONTENT_KEYS = ('evidence_mode', 'triangulation', 'cel', 'stable_max',
                 'review_max', 'divergence_threshold', 'loo_sampling_threshold',
                 'dimensions', 'provenance', 'status', 'forced_grade',
                 'attainment_floor', 'evidence_class_min', 'promotion_streak',
                 'action', 'effective_from', 'effective_to', 'rationale',
                 'alpha_floor', 'drift_budget', 'boundary_budget',
                 'boundary_epsilon', 'min_dim_weight', 'max_shift_from_ahp',
                 'alpha_grid', 'whatif_run_id')
BUSINESS_ASSIGNMENT = re.compile(
    r'(?i)\b(?:' + _BUSINESS_WORD + r')\w*\s*[:=]\s*[-+]?\d')
K_TOKEN = re.compile(r'K-[0-9][0-9]')
BUSINESS_KEY_SEGMENTS = (frozenset(_BUSINESS_WORD.split('|'))
                         | frozenset(key.lower() for key in _CONTENT_KEYS))


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


# ---------------------------------------------------------------------------
# Positive controls: they pass now, which proves the file collects, the
# settings are aligned and the oracle is the one the ADR wrote.
# ---------------------------------------------------------------------------
def test_t05_j_s01_the_hypothesis_settings_align_with_the_numeric_conventions():
    '''H-14 / ruling 13.'''
    source = NUMERIC_PROPERTIES_PATH.read_text(encoding='utf-8')
    assert 'max_examples=60' in source
    assert 'deadline=None' in source
    assert OPTS.max_examples == 60
    assert OPTS.deadline is None
    assert OPTS.derandomize is True
    assert OPTS.database is None


def test_t05_j_s02_the_oracle_reproduces_the_ruling_8_notation():
    tree = {'weight_construction': {'alpha_floor': 'PLACEHOLDER'},
            'triangulation': {'thresholds': ['SYN-OK', None, 'TODO']},
            'cel': {'enabled': True}}
    assert _oracle_hits(tree, 'eval_config') == [
        'eval_config.weight_construction.alpha_floor',
        'eval_config.triangulation.thresholds[1]',
        'eval_config.triangulation.thresholds[2]']


def test_t05_j_s03_the_oracle_leaf_rule_matches_the_ruling_5_and_6_tables():
    for value in PLACEHOLDER_VALUES:
        assert _is_hit_oracle(value) is True, repr(value)
    for value in FILLED_TEXTS:
        assert _is_hit_oracle(value) is False, repr(value)
    for value in (-1, 0, 1, True, False, TYPE_PROBE_FLOAT):
        assert _is_hit_oracle(value) is False, repr(value)


def test_t05_j_s04_this_property_file_carries_no_business_number():
    offenders = _business_number_offenders(ast.parse(THIS_PATH.read_text(encoding='utf-8')))
    assert not offenders, 'H-5 violation in this file: ' + repr(offenders)


# ---------------------------------------------------------------------------
# T05-J / P-10. Ruling 14 items 1-4, the forward direction.
# ---------------------------------------------------------------------------
@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p01_a_tree_with_a_hit_yields_a_non_empty_path_list(tree):
    '''Ruling 14 item 1.'''
    assert _oracle_hits(tree, SYN_STEM)
    assert cfg('find_placeholders')(tree, root=SYN_STEM)


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p02_the_paths_cover_every_hit_position_exactly_once(tree):
    '''Ruling 14 item 4 / [L878] "not only the first one".'''
    expected = _oracle_hits(tree, SYN_STEM)
    paths = cfg('find_placeholders')(tree, root=SYN_STEM)
    assert len(paths) == len(expected)
    assert sorted(paths) == sorted(expected)
    assert len(paths) == len(set(paths))


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p03_load_all_raises_config_placeholder_error_with_exit_code_three(tree):
    '''Ruling 14 item 2 / [L1434]: the block happens at the loading stage.'''
    with tempfile.TemporaryDirectory() as raw:
        base = _write_dir(Path(raw), eval_config=tree)
        with pytest.raises(placeholder_error()) as excinfo:
            cfg('load_all')(str(base))
    assert excinfo.value.exit_code == EXIT_CODE


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p04_no_appconfig_instance_escapes_a_blocked_load(tree):
    '''Ruling 14 item 3: nothing is returned, so no downstream stage can
    produce a score ([L1091]).'''
    appconfig = cfg('AppConfig')
    err = placeholder_error()
    produced = []
    with tempfile.TemporaryDirectory() as raw:
        base = _write_dir(Path(raw), eval_config=tree)
        try:
            produced.append(cfg('load_all')(str(base)))
        except err:
            pass
    assert produced == []
    assert not any(isinstance(item, appconfig) for item in produced)


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p05_the_error_paths_cover_the_whole_tree(tree):
    '''Ruling 14 item 4 through the I/O entry point, after a yaml round trip.'''
    expected = _oracle_hits(tree, 'eval_config')
    with tempfile.TemporaryDirectory() as raw:
        base = _write_dir(Path(raw), eval_config=tree)
        with pytest.raises(placeholder_error()) as excinfo:
            cfg('load_all')(str(base))
    paths = excinfo.value.paths
    assert sorted(paths) == sorted(expected)
    assert len(paths) == len(expected)


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p06_scan_config_trees_is_sorted_and_deduplicated(tree):
    '''Ruling 9.'''
    paths = cfg('scan_config_trees')({SYN_STEM: tree})
    assert paths == tuple(sorted(set(paths)))


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p07_every_path_carries_the_file_stem_prefix(tree):
    '''Ruling 8: the stem prefix is what keeps weights_*.yaml apart.'''
    paths = cfg('scan_config_trees')({SYN_STEM: tree})
    assert paths
    for path in paths:
        assert path.startswith(SYN_STEM + '.'), path


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p08_two_identical_calls_are_byte_identical(tree):
    '''Ruling 9 determinism / V-3 reproducibility / H-14.'''
    first = cfg('scan_config_trees')({SYN_STEM: tree})
    second = cfg('scan_config_trees')({SYN_STEM: tree})
    assert first == second
    assert repr(first) == repr(second)


@OPTS
@given(tree=tree_with_a_hit())
def test_t05_j_p09_the_pure_functions_do_not_mutate_their_input(tree):
    '''H-8: the input tree belongs to the caller.'''
    before = copy.deepcopy(tree)
    cfg('find_placeholders')(tree, root=SYN_STEM)
    cfg('scan_config_trees')({SYN_STEM: tree})
    assert tree == before


@OPTS
@given(value=mixed_leaf)
def test_t05_j_p10_is_placeholder_value_agrees_with_the_ruling_5_leaf_rule(value):
    '''Rulings 5 and 6, decided leaf by leaf over the generated value domain.'''
    assert cfg('is_placeholder_value')(value) is _is_hit_oracle(value)


@OPTS
@given(tree=colliding_dict())
def test_t05_j_p11_a_key_collision_folds_into_exactly_one_path(tree):
    '''Ruling 24 item 3, the reachable assertion p06 cannot make on its own.
    Two hit positions render to the same path string, so the raw walk reports
    both while scan_config_trees reports the path once: len(paths) ==
    len(set(paths)) is then a statement about deduplication and no longer a
    structural truism. The invariant of p06 is repeated here on an input that
    can actually violate it, which is what kills the "deduplication removed
    from scan_config_trees" mutant (M12).'''
    walked = cfg('find_placeholders')(tree, root=SYN_STEM)
    paths = cfg('scan_config_trees')({SYN_STEM: tree})
    assert len(walked) == len(_oracle_hits(tree, SYN_STEM))
    assert walked.count(SYN_STEM + '.1') == 2
    assert len(paths) == len(set(paths))
    assert paths.count(SYN_STEM + '.1') == 1
    assert paths == tuple(sorted(set(paths)))


# ---------------------------------------------------------------------------
# The reverse direction: a fully filled configuration must load. Without it
# the interceptor could pass by rejecting everything.
# ---------------------------------------------------------------------------
@OPTS
@given(tree=filled_dict)
def test_t05_j_n01_a_fully_filled_tree_yields_no_path(tree):
    assert not _oracle_hits(tree, SYN_STEM)
    assert cfg('find_placeholders')(tree, root=SYN_STEM) == ()


@OPTS
@given(tree=filled_dict)
def test_t05_j_n02_scan_config_trees_of_a_filled_tree_is_empty(tree):
    assert cfg('scan_config_trees')({SYN_STEM: tree}) == ()


@OPTS
@given(tree=filled_dict)
def test_t05_j_n03_a_fully_filled_dir_loads_into_an_appconfig(tree):
    '''[L1259] blocks unfilled values, it does not block a filled config.'''
    appconfig = cfg('AppConfig')
    with tempfile.TemporaryDirectory() as raw:
        base = _write_dir(Path(raw), eval_config=tree)
        loaded = cfg('load_all')(str(base))
    assert isinstance(loaded, appconfig)
    assert loaded.eval_config == tree

# ---------------------------------------------------------------------------
# T06-Q / P-11. Appended by S1-T06 R3 under ORCH-24 ruling 19 and checklist
# row T06-Q ("任意 FROZEN 且 provenance 不完整的合成权重树必被拦、必不产出
# AppConfig; 同 seed 逐字节可复现"). Every line above this block is the frozen
# S1-T05 file and none of it was edited: ORCH-24 ruling 20 pins the write set
# to "tests/test_config_properties.py (追加 P-11 属性; 既有 P-10 用例一条不改)"
# and ruling 1 pins "T05 已冻结的 12 个公开名与既有用例一条不改".
#
# [L1435] P-11 verbatim: "任何 FROZEN 权重版本必须具备完整 provenance（AHP
# 矩阵 + CR；若 combined 则含 α + alpha_basis + whatif_run_id），缺任一项 ->
# 配置加载失败". The required segment matrix is ORCH-24 ruling 17; the
# reason_code split is ruling 15 fixed order (序 5 whatif before 序 6 other
# segments); the exit code is ruling 4 (EXIT_BLOCK = 2).
#
# RED mechanism: cfg_t06() resolves a name of ruling 19 lazily, so each case
# below fails as AttributeError "dsm.config has no attribute <X>", never as a
# collection error, never as a fixture error. Reproducibility follows the same
# OPTS the file already uses (max_examples / deadline=None / derandomize=True
# / database=None), which is what makes the two runs of q03 byte identical.
# ---------------------------------------------------------------------------
T06_Q_PERIOD = '2026-10'
T06_Q_FROM = '2026-01'
T06_Q_TO = '2026-12'
T06_Q_DIMS = ('SYN-DIM-A', 'SYN-DIM-B')
T06_Q_METRICS = ('SYN-M-01', 'SYN-M-02')
T06_Q_KINDS = ('AHP_ONLY', 'AHP_ENTROPY_COMBINED', 'EXPERT_ONLY')
T06_Q_GRADES = ('L1', 'L2', 'L3', 'L4')
T06_Q_FLOORS = ('0.9', '0.75', '0.6', '0.4')
T06_Q_RUN_ID = 'SYN-WHATIF-RUN'
T06_Q_APPROVED_BY = 'SYN-APPROVER'
T06_Q_APPROVED_DATE = '2026-01-05'
T06_Q_CR = '0.25'      # parseable only; ruling 17 forbids judging the value
T06_Q_ALPHA = '0.25'   # parseable only; ruling 17 forbids judging the range
T06_Q_MATRIX = 'SYN-MATRIX-PAYLOAD'
T06_Q_EXIT_BLOCK = 2   # ruling 4, the version policy exit code
T06_Q_WHATIF_BLANK = ''  # ruling 15 序 5: 缺 whatif_run_id 或 strip 后为空


def _t06_rc():
    '''The registered reason_code enum (ORCH-24 ruling 5).'''
    return importlib.import_module('dsm.reason_codes').RC


def cfg_t06(name):
    '''Resolve a name of ORCH-24 ruling 19 (the T06 half of the contract).'''
    module = _config_module()
    resolved = getattr(module, name, None)
    if resolved is None:
        raise AttributeError(
            'dsm.config has no attribute ' + name
            + ' (S1-T06 not implemented yet, ORCH-24 ruling 19)')
    return resolved


def _t06_required_segments(kind):
    '''The ruling 17 matrix, written out as an independent oracle.'''
    base = ('ahp', 'ahp.comparison_matrices', 'ahp.cr', 'whatif_run_id',
            'approved_by', 'approved_date')
    if kind == 'AHP_ENTROPY_COMBINED':
        return base + ('entropy', 'combine', 'combine.alpha', 'alpha_basis')
    return base


def _t06_eval_config():
    return {'SYN-evidence_mode': 'SYN-EVIDENCE-MODE'}


def _t06_redlines():
    return {'rules': {'HARD': [{'metric_id': metric, 'level': 'HARD',
                                'threshold_value': 'SYN-THRESHOLD-REF'}
                               for metric in T06_Q_METRICS]}}


def _t06_grade_rules():
    levels = []
    for code, floor in zip(T06_Q_GRADES, T06_Q_FLOORS):
        levels.append({'grade_code': code, 'attainment_floor': floor,
                       'actions': ['SYN-ACTION-01'],
                       'action_gate': 'SYN-ACTION-GATE'})
    return {'levels': levels}


def _t06_anchor():
    return {'anchor_set_id': 'SYN-ANCHOR-0001',
            'strategy_ids': ['SYN-S-001', 'SYN-S-002'],
            'effective_from': T06_Q_FROM, 'effective_to': T06_Q_TO,
            'rationale': 'SYN-RATIONALE'}


def _t06_ahp_matrices():
    return {'matrices': {'SYN-DIM-A': T06_Q_MATRIX}}


def _t06_complete_tree(kind, stem=WEIGHTS_STEM_A):
    '''A FROZEN weights tree whose provenance is complete for the kind.'''
    prov = {
        'kind': kind,
        'whatif_run_id': T06_Q_RUN_ID,
        'approved_by': T06_Q_APPROVED_BY,
        'approved_date': T06_Q_APPROVED_DATE,
        'ahp': {'comparison_matrices': {'SYN-DIM-A': T06_Q_MATRIX},
                'cr': T06_Q_CR},
    }
    if kind == 'AHP_ENTROPY_COMBINED':
        prov['entropy'] = {'SYN-entropy_weights': 'SYN-ENTROPY-PAYLOAD'}
        prov['combine'] = {'alpha': T06_Q_ALPHA}
        prov['alpha_basis'] = 'SYN-ALPHA-BASIS'
    return {
        'weight_version_id': stem,
        'status': 'FROZEN',
        'effective_from': T06_Q_FROM,
        'effective_to': T06_Q_TO,
        'level1_weights': {dim: '0.5' for dim in T06_Q_DIMS},
        'level2_weights': {dim: {T06_Q_METRICS[0]: '0.5',
                                 T06_Q_METRICS[1]: '0.5'}
                           for dim in T06_Q_DIMS},
        'provenance': prov,
    }


def _t06_apply_gap(tree, gap):
    '''Remove or blank one required segment of the ruling 17 matrix. A gap
    under a parent that is already gone stays a no-op: the parent absence is
    the breach, and _t06_missing_segments still reports it.'''
    prov = tree.get('provenance')
    if not isinstance(prov, dict):
        return tree
    if gap == 'provenance':
        tree.pop('provenance', None)
        return tree
    if gap == 'whatif_run_id_blank':
        tree['provenance']['whatif_run_id'] = T06_Q_WHATIF_BLANK
        return tree
    if gap == 'ahp.comparison_matrices':
        if 'ahp' in prov:
            prov['ahp']['comparison_matrices'] = {}
        return tree
    if gap == 'ahp.cr':
        if 'ahp' in prov:
            prov['ahp'].pop('cr', None)
        return tree
    if gap == 'combine.alpha':
        if 'combine' in prov:
            prov['combine'].pop('alpha', None)
        return tree
    holder = prov
    if gap == 'ahp':
        holder.pop('ahp', None)
    elif gap == 'entropy':
        holder.pop('entropy', None)
    elif gap == 'combine':
        holder.pop('combine', None)
    else:
        holder.pop(gap, None)
    return tree


def _t06_missing_segments(tree, kind):
    '''The oracle: which required segments the tree really lacks.'''
    required = _t06_required_segments(kind)
    prov = tree.get('provenance')
    if not isinstance(prov, dict):
        return ('provenance',) + required
    missing = []
    for segment in required:
        node = prov
        ok = True
        for part in segment.split('.'):
            if not isinstance(node, dict) or part not in node:
                ok = False
                break
            node = node[part]
        if not ok:
            missing.append(segment)
        elif segment.endswith('comparison_matrices') and node == {}:
            missing.append(segment)
        elif segment == 'whatif_run_id' and str(node).strip() == '':
            missing.append(segment)
    return tuple(missing)


@st.composite
def frozen_incomplete_case(draw):
    '''A FROZEN weights tree that provably lacks at least one required
    provenance segment of its own kind (no assume() filter, so nothing can
    pass vacuously). One mandatory gap first, then zero to two extra ones.'''
    kind = draw(st.sampled_from(T06_Q_KINDS))
    tree = _t06_complete_tree(kind)
    pool = list(_t06_required_segments(kind)) + ['whatif_run_id_blank',
                                                 'provenance']
    first = draw(st.sampled_from(pool))
    tree = _t06_apply_gap(tree, first)
    extras = draw(st.lists(st.sampled_from(pool), max_size=2, unique=True))
    for gap in extras:
        if 'provenance' not in tree:
            break
        if 'combine' not in tree['provenance'] and gap in ('combine',
                                                           'combine.alpha'):
            continue
        tree = _t06_apply_gap(tree, gap)
    return kind, tree, (first,) + tuple(extras)


def _t06_appcfg(tree):
    return cfg_t06('AppConfig')(**{
        'eval_config': _t06_eval_config(),
        'weights': {WEIGHTS_STEM_A: tree},
        'redlines': _t06_redlines(),
        'grade_rules': _t06_grade_rules(),
        'anchor_set': _t06_anchor(),
        'ahp_matrices': _t06_ahp_matrices()})


def _t06_write_dir(base, tree):
    base = Path(base)
    base.mkdir(parents=True, exist_ok=True)
    trees = {WEIGHTS_STEM_A: tree, 'eval_config': _t06_eval_config(),
             'redlines': _t06_redlines(), 'grade_rules': _t06_grade_rules(),
             'anchor_set': _t06_anchor(), 'ahp_matrices': _t06_ahp_matrices()}
    for stem, item in trees.items():
        (base / (stem + '.yaml')).write_text(
            yaml.safe_dump(item, allow_unicode=True, sort_keys=False),
            encoding='utf-8')
    return base


@OPTS
@given(case=frozen_incomplete_case())
def test_t06_q01_an_incomplete_frozen_provenance_is_always_blocked(case):
    '''[L1435] / T06-Q: any FROZEN version with a missing provenance segment
    fails the load, and it fails as a version policy breach, exit code 2
    (ORCH-24 ruling 4), never as a silent pass.'''
    kind, tree, gaps = case
    err = cfg_t06('WeightVersionInvalidError')
    assert _t06_missing_segments(tree, kind), (kind, gaps)
    with pytest.raises(err) as excinfo:
        cfg_t06('validate_weights')(_t06_appcfg(tree), period=T06_Q_PERIOD)
    assert excinfo.value.exit_code == T06_Q_EXIT_BLOCK


@OPTS
@given(case=frozen_incomplete_case())
def test_t06_q02_an_incomplete_frozen_provenance_never_produces_appconfig(case):
    '''[L1435] "配置加载失败" plus [L1091]: nothing escapes, so no downstream
    stage can score, and P-11 rides the same single exit as P-10.'''
    kind, tree, gaps = case
    err = cfg_t06('WeightVersionInvalidError')
    appconfig = cfg_t06('AppConfig')
    produced = []
    with tempfile.TemporaryDirectory() as raw:
        base = _t06_write_dir(Path(raw), tree)
        try:
            produced.append(cfg_t06('load_all')(str(base),
                                                period=T06_Q_PERIOD))
        except err:
            pass
    assert produced == []
    assert not any(isinstance(item, appconfig) for item in produced)


@OPTS
@given(case=frozen_incomplete_case())
def test_t06_q03_the_block_is_reproduced_byte_for_byte_on_a_rerun(case):
    '''H-14 / V-3: the randomness is the hypothesis seed alone (derandomize),
    so the same generated tree yields the identical message and reason_code.'''
    kind, tree, gaps = case
    err = cfg_t06('WeightVersionInvalidError')

    def once():
        try:
            cfg_t06('validate_weights')(_t06_appcfg(tree),
                                        period=T06_Q_PERIOD)
        except err as caught:
            return (str(caught), repr(caught.violations),
                    caught.reason_code.value, caught.exit_code)
        raise AssertionError('an incomplete provenance passed: ' + repr(gaps))

    assert once() == once()


@OPTS
@given(case=frozen_incomplete_case())
def test_t06_q04_the_reason_code_follows_the_ruling_15_fixed_order(case):
    '''Ruling 15: reason_code takes the FIRST hit, 序 5 (whatif_run_id)
    before 序 6 (every other required segment), so a blank run id outranks a
    missing AHP segment and both are BLOCK / exit code 2.'''
    kind, tree, gaps = case
    registry = _t06_rc()
    err = cfg_t06('WeightVersionInvalidError')
    missing = _t06_missing_segments(tree, kind)
    assert missing, gaps
    with pytest.raises(err) as excinfo:
        cfg_t06('validate_weights')(_t06_appcfg(tree), period=T06_Q_PERIOD)
    code = excinfo.value.reason_code
    assert isinstance(code, registry)
    if missing[0] == 'provenance':
        # ruling 17: the provenance key itself absent on a FROZEN version is
        # RC.WEIGHT_VERSION_INVALID, the more specific of the two sentences.
        assert code is registry.WEIGHT_VERSION_INVALID, missing
    elif 'whatif_run_id' in missing:
        assert code is registry.WEIGHT_MISSING_WHATIF_RUN_ID, missing
    else:
        assert code is registry.WEIGHT_VERSION_INVALID, missing
    assert excinfo.value.exit_code == T06_Q_EXIT_BLOCK


def test_t06_q05_the_ruling_17_matrix_is_blocked_segment_by_segment():
    '''The non-vacuous half of P-11: one generated case cannot hide a segment
    the checker never looks at, so every (kind, required segment) pair of the
    ruling 17 table is falsified explicitly here, plus the provenance key
    itself.'''
    err = cfg_t06('WeightVersionInvalidError')
    blocked = []
    for kind in T06_Q_KINDS:
        for segment in _t06_required_segments(kind) + ('whatif_run_id_blank',
                                                      'provenance'):
            tree = _t06_apply_gap(_t06_complete_tree(kind), segment)
            assert _t06_missing_segments(tree, kind), (kind, segment)
            with pytest.raises(err):
                cfg_t06('validate_weights')(_t06_appcfg(tree),
                                            period=T06_Q_PERIOD)
            blocked.append((kind, segment))
    assert len(blocked) == 28, blocked  # (6+2) + (10+2) + (6+2)


def test_t06_q06_a_complete_frozen_provenance_is_not_blocked():
    '''The reverse direction of P-11, without which the gate above could pass
    by rejecting everything: [L1435] demands the segments, it does not forbid
    a FROZEN version that has them (ruling 17: 多余的段不报错).'''
    for kind in T06_Q_KINDS:
        tree = _t06_complete_tree(kind)
        assert _t06_missing_segments(tree, kind) == ()
        assert cfg_t06('validate_weights')(_t06_appcfg(tree),
                                           period=T06_Q_PERIOD) is None


def test_t06_q07_the_p11_cases_join_the_frozen_p10_conventions():
    '''T06-Q "同 seed 逐字节可复现" is the same discipline ruling 13 / H-14
    set for P-10, so the settings object must be the one s01 already pins.'''
    assert OPTS.deadline is None
    assert OPTS.derandomize is True
    assert OPTS.database is None
    source = THIS_PATH.read_text(encoding='utf-8')
    assert source.count('@OPTS') >= 18
    assert cfg_t06('WeightVersionInvalidError').__name__ == \
        'WeightVersionInvalidError'
