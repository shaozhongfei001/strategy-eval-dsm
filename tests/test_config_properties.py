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
    return {'eval_config': _clean_slot('eval_config'),
            WEIGHTS_STEM_A: _clean_slot(WEIGHTS_STEM_A),
            'redlines': _clean_slot('redlines'),
            'grade_rules': _clean_slot('grade_rules'),
            'anchor_set': _clean_slot('anchor_set'),
            'ahp_matrices': _clean_slot('ahp_matrices')}


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
