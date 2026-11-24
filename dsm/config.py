'''dsm.config -- L1 configuration loading and PLACEHOLDER interception (S1-T05).

Contract authority is docs/adr/ORCH-23.md (rulings 1-20 plus the acceptance
checklist T05-A .. T05-M); the SDD wording behind it is carried by
docs/digest/S1-T05.md: [L873]-[L882] (section 3.3.4), [L1246]-[L1259]
(section 3.12), [L1076]-[L1091] (exit codes), [L1434]-[L1435] (P-10 / P-11),
[L1498] (V-5) and [L78] / [L102] / [L1806] (the PLACEHOLDER discipline).

Scope of this module, and only this scope (ruling 1, minimal L2 implementation):

    read the six yaml patterns of [L877]
    -> walk every tree recursively
    -> collect every unfilled path at once ([L878] forbids reporting only the
       first one, [L1259] asks for the complete list)
    -> raise ConfigPlaceholderError, exit code 3
    -> otherwise return AppConfig carrying the raw trees.

The semantic checks of [L879] and the weight version checks of [L880] are
S1-T06, landed in the second half of this file under docs/adr/ORCH-24.md as the
contract authority: the six judgements of [L879], the three of [L880] plus P-11
of [L1435], the two remaining exceptions of [L881] (ConfigSemanticError and
WeightVersionInvalidError, peers of ConfigPlaceholderError, ruling 3) and
EXIT_BLOCK = 2 for the version policy breaches (ruling 4). load_all keeps the
ORCH-23 ruling 1 order -- read the files, PLACEHOLDER scan, validation hook,
AppConfig -- and appends the two optional keyword arguments period / run_at of
ORCH-24 ruling 19.

Discipline this file carries:

  * H-5 / T05-L -- no business number anywhere. Nothing here proposes a weight,
    a threshold, a floor, a target, a price, a period or a sample size. The raw
    int / float scalars of a yaml file are handed on untouched (ruling 4) and
    may reach the computation layer only through the numeric gate of H-4, which
    S1-T06 lands (blocker B-022).
  * H-8 / T05-I -- is_placeholder_value, find_placeholders and scan_config_trees
    are pure: no I/O, no wall clock, no global state, no mutation of the
    argument, byte identical results for identical input. load_all is the only
    I/O entry point of the module and takes config_dir alone (ruling 11); T06
    appends --period / --run-at as optional keywords, which is not a break.
  * H-9 / T05-K -- L1 layer ([L355] / [L816]): no L0a / L0b import (INV-1) and,
    at the T05 stage, no dsm.models / dsm.numeric / dsm.reason_codes import
    either (ruling 12). Third party imports are yaml and pydantic only.
  * V-14 -- a missing required file is never papered over with an empty tree;
    missing files and placeholder paths leave through one and the same raise
    (ruling 10), so no AppConfig can reach a downstream stage ([L1091]).
  * ruling 13 -- this module never writes anything. The repository config/
    directory stays the property of the S2 fixtures.
'''
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

from . import numeric, reason_codes

# ruling 5 (H-6 / H-7): RC.<NAME> is the only legal spelling of a reason_code
# inside a business module, and ruling 20 authorises exactly these two L1 peers
# as the T06 dependencies. The alias keeps every reference below reading as
# RC.<NAME>, which is what the P-8 AST scan of S9-T02 looks for.
RC = reason_codes.RC

# ---------------------------------------------------------------------------
# Constants. The public ones are verbatim ruling 11; EXIT_CONFIG is the single
# source of truth for exit code 3 ([L881] / [L1080]), so S9-T01 cli.py imports
# it instead of writing its own literal (ruling 2, H-7). The integer is an exit
# code, not a business value.
# ---------------------------------------------------------------------------
EXIT_CONFIG = 3

# ruling 10: the five fixed required files, in the [L1250]-[L1257] clause
# order. weights_*.yaml is required too, but as a wildcard (ruling 18), so it
# is not a member of this tuple.
REQUIRED_CONFIG_STEMS = ('eval_config', 'redlines', 'grade_rules',
                         'anchor_set', 'ahp_matrices')

# [L877] spelling, which is a superset of the weights_WV-*.yaml of [L1252].
WEIGHTS_GLOB = 'weights_*.yaml'

# ruling 5: the four words of [L878], once as whole values and once as prefixes
# (branches (b) and (c) of the ruling, the conservative reading of "形如").
PLACEHOLDER_TOKENS = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')
PLACEHOLDER_PREFIXES = ('PLACEHOLDER', 'TODO', 'TBD', 'XXX')

# ruling 3: the raw safe_load tree, inner content deliberately unschematised.
ConfigTree = dict[str, Any]

# ruling 9 file order, used for the grouping of scan_config_trees and for the
# ordering of missing_files (ruling 18). Private: the SDD list is a fact about
# [L1250]-[L1257], not a fourth public constant of ruling 11.
_FILE_ORDER = ('eval_config', 'weights', 'redlines', 'grade_rules',
               'anchor_set', 'ahp_matrices')
_WEIGHTS_PREFIX = 'weights_'
# ruling 18: the literal spelling of the weights gap in missing_files, that is
# WEIGHTS_GLOB without its extension, so a wildcard gap stays recognisable.
_WEIGHTS_GAP = 'weights_*'
_YAML_SUFFIX = '.yaml'


class AppConfig(BaseModel):
    '''The six file level slots of ruling 3 -- and nothing else.

    [L1248]-[L1257] list the *contents* of every configuration file, but the
    SDD gives no field names, no nesting and no types for them, and AppConfig
    appears exactly once in the whole document ([L310]). So no field level
    schema is invented here (ruling 3, T05-H): each slot keeps the raw tree and
    S1-T06 reads the verbatim keys of [L1250]-[L1257] out of it by path.

    frozen=True plus extra='forbid' is the same discipline as the models layer
    (V-5, [L871]): an undeclared slot errors out instead of being dropped, and
    a loaded configuration cannot be edited behind the audit trail's back.
    '''

    model_config = ConfigDict(frozen=True, extra='forbid')

    eval_config: ConfigTree
    # weights is the only multi-file slot: one entry per weights_*.yaml, keyed
    # by the file stem so several frozen weight versions never mix ([L1252]).
    weights: dict[str, ConfigTree]
    redlines: ConfigTree
    grade_rules: ConfigTree
    anchor_set: ConfigTree
    ahp_matrices: ConfigTree


# ---------------------------------------------------------------------------
# The single exit of ruling 9 / ruling 10: message format and exception.
# ---------------------------------------------------------------------------
# The SDD is silent about the wording, so ruling 9 pins it: a head line with
# the total count, one dash line per path, and -- only when files are missing --
# a blank line followed by the missing block. Full width parentheses and colon
# are part of the pinned format.
_MESSAGE_HEAD = '配置含 %d 个未签认占位值（退出码 %d）'
_MESSAGE_MISSING_HEAD = '缺失必需配置文件 %d 份：'
_MESSAGE_ITEM = '  - %s'


def _stem_of(path):
    '''The file stem a path belongs to: everything before the first dot or the
    first bracket, so the bare stem path of an empty yaml file (ruling 6
    corollary) maps back onto its own stem as well.'''
    return path.split('.')[0].split('[')[0]


def _file_rank(stem):
    '''The ruling 9 position of one stem.

    Every weights_*.yaml shares the single weights rank, so the weight versions
    stay together as a block and are separated inside it by their path string
    (ruling 9: stem ascending). A stem outside the [L1250]-[L1257] list sorts
    last, which keeps the function total for the synthetic stems a caller or a
    property test may hand in (T05-I i13, ruling 16).
    '''
    if stem.startswith(_WEIGHTS_PREFIX):
        return _FILE_ORDER.index('weights')
    if stem in _FILE_ORDER:
        return _FILE_ORDER.index(stem)
    return len(_FILE_ORDER)


def _path_key(path):
    '''Sort key of ruling 9: file order first, path string ascending second.'''
    return (_file_rank(_stem_of(path)), path)


def _missing_key(stem):
    '''Sort key of ruling 18: the weights gap keeps its [L1252] position.'''
    return (_file_rank(stem), stem)


def _format_message(paths, missing_files, exit_code):
    '''Render the ruling 9 message. No path and no missing file is dropped:
    [L878] forbids reporting only the first one and ruling 9 forbids a limit.'''
    lines = [_MESSAGE_HEAD % (len(paths), exit_code)]
    lines += [_MESSAGE_ITEM % path for path in paths]
    if missing_files:
        lines.append('')
        lines.append(_MESSAGE_MISSING_HEAD % len(missing_files))
        lines += [_MESSAGE_ITEM % stem for stem in missing_files]
    return '\n'.join(lines)


class ConfigPlaceholderError(Exception):
    '''The one and only configuration exit of T05 ([L881], exit code 3).

    ruling 10 reuses this exception for missing required files instead of
    inventing a fourth name ([L881] gives three, H-10) and carries them in
    missing_files, so an unfilled value and an absent file leave through one and
    the same raise -- V-14 leaves no room for a silent second channel.

    Both arguments accept any iterable and are stored as tuples (ruling 11).
    Ordering and deduplication have exactly one reading each, and both of them
    are ruling 9:

      * missing_files is always deduplicated and sorted by the ruling 9 file
        order, the weights gap sitting at its [L1252] position (ruling 18). The
        result therefore never depends on the order the caller listed the gaps
        in (T05-G g11 determinism).
      * paths is deduplicated first, keeping the first occurrence, and then
        sorted unconditionally by _path_key: the fixed file order of
        [L1250]-[L1257] first, the path string ascending inside one file second.
        That is ruling 9, and ruling 23 makes it literal for the constructor as
        well -- one order, not two, and no plain string sort anywhere in this
        class. Ruling 9 does name its key, _path_key is that key, and it is the
        very key scan_config_trees already applies, so a caller-supplied
        iterable and a load_all result now come out in one and the same order
        (T05-B b04 / b05 / b12, T05-F f02). A stem outside the
        [L1250]-[L1257] list keeps the last file rank and stays path-sorted
        inside its own block, which keeps the key total for the synthetic stems
        a property test hands in (ruling 16, T05-B b13, T05-I i13).
    '''

    def __init__(self, paths: Iterable[str], missing_files: Iterable[str] = ()):
        deduped = tuple(dict.fromkeys(paths))
        canonical = tuple(sorted(deduped, key=_path_key))
        self.paths = canonical
        self.missing_files = tuple(
            sorted(dict.fromkeys(missing_files), key=_missing_key))
        # An instance attribute on purpose, so a caller can read err.exit_code
        # without importing the constant a second time (ruling 11).
        self.exit_code = EXIT_CONFIG
        super().__init__(
            _format_message(self.paths, self.missing_files, self.exit_code))


# ---------------------------------------------------------------------------
# The hit rule and the recursive walk. Pure functions (H-8 / T05-I): no I/O, no
# wall clock, no global state, no mutation of the argument, byte identical
# output for byte identical input.
# ---------------------------------------------------------------------------
def _join(root, rel):
    '''The one and only path join of ruling 17, in its three branches:
    root + '.' + rel when both are non-empty, root when rel is empty, and rel
    when root is empty.

    Those three branches are what keeps the prefix invariant

        find_placeholders(t, root=r)
            == tuple(_join(r, p) for p in find_placeholders(t))

    true for every tree and every root, and they are why no path ever starts
    with a dot when root is the empty string (T05-E e09, ruling 17).

    ORCH-23 ruling 22, carried into ORCH-24 ruling 22, completes the notation
    for the one shape those three branches leave open: when the tree root is
    itself a list, the relative path 以 [ 开头 ([0], [1][2]) and the joined path
    is root + rel with no dot in between, so a list tree under the root 'stem'
    yields stem[0] and stem[1] and never stem.[0]. _walk builds those bracket
    positions itself with the '%s[%d]' formatting and therefore never hands a
    rel that startswith a bracket to _join; this note documents the convention,
    the behaviour of _join and _walk is unchanged, and the T06 violation paths
    ride the very same notation (ORCH-24 ruling 14).
    '''
    if not rel:
        return root
    if not root:
        return rel
    return root + '.' + rel


def is_placeholder_value(value):
    '''True when one leaf value is an unfilled slot: rulings 5, 6 and 19.

    ruling 5 -- a string hits if and only if, with s = value.strip().upper(),
    s is one of PLACEHOLDER_TOKENS or s starts with one of
    PLACEHOLDER_PREFIXES. The test is case insensitive and whole-value-or-
    prefix; a mere substring never hits, so free text such as a rationale that
    happens to mention a token stays usable ([L878] "形如 TODO / TBD / XXX"
    read conservatively, prefix matching being what covers the PLACEHOLDER_...
    spelling the governance parameter list of [L1734]-[L1759] produces).
    Non-string scalars do not hit: an int, a float or a bool is a filled value,
    and whether it is a *plausible* value is S1-T06 semantic validation
    ([L879]), not T05. Containers do not hit either, they are walked instead.

    ruling 6 -- None always hits. [L878] would restrict null to fields
    "declared mandatory", but the SDD never says where such a declaration
    lives: AppConfig has no field level schema (ruling 3) and the contract table
    [L860]-[L873] has no AppConfig row. Every null is therefore treated as
    unfilled, and "optional and unset" is spelled by omitting the key, which
    yaml does not turn into a None. Blocker B-024.

    ruling 19 -- the empty string and whitespace-only strings do NOT hit. The
    if-and-only-if of ruling 5 is closed: for '' and for '   ' the stripped
    value is empty, so it is neither one of the four tokens nor does it start
    with one of them. The reasons are (a) [L878] lists three hit shapes and an
    empty string is none of them, so counting it would be a tightening rather
    than a conservative superset and would wound a deliberate empty note;
    (b) a key that is present but carries no value yields None in yaml, not '',
    and ruling 6 already blocks every None, so no unfilled value can slip
    through this gap; (c) writing '' explicitly is a deliberate statement. The
    wording is folded into blocker B-023 for sign-off: should the bank require
    '' to count as unfilled, the change is one extra branch here plus the
    parametrised hit table in the tests.

    ruling 5 also settles what is *not* looked at: dict keys are never scanned,
    a key is not a value, and a placeholder spelled as a key is a schema
    question for S1-T06.
    '''
    if value is None:
        return True
    if not isinstance(value, str):
        return False
    stripped = value.strip().upper()
    if stripped in PLACEHOLDER_TOKENS:
        return True
    return any(stripped.startswith(token) for token in PLACEHOLDER_PREFIXES)


def _walk(node, prefix, found):
    '''Depth first walk appending every hit path to found, in traversal order.

    The shape mirrors ruling 8: a dict contributes its keys with a dot, a list
    contributes a zero based bracket index chained for nested lists, and a None
    node contributes the prefix it arrived with -- which is the bare stem when
    the whole tree is None (ruling 6 corollary, ruling 17). Anything else is a
    leaf and is judged by is_placeholder_value. Sorting is deliberately not
    done here, it belongs to scan_config_trees (ruling 9 / ruling 11).
    '''
    if node is None:
        found.append(prefix)
        return
    if isinstance(node, dict):
        for key in node:
            # A yaml mapping may carry a non-string key; the path notation is
            # textual, so the key is spelled out instead of breaking the walk.
            name = key if isinstance(key, str) else str(key)
            _walk(node[key], _join(prefix, name), found)
        return
    if isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, '%s[%d]' % (prefix, index), found)
        return
    if is_placeholder_value(node):
        found.append(prefix)


def find_placeholders(tree: Any, *, root: str = '') -> tuple[str, ...]:
    '''Every unfilled path of one tree, in traversal order (rulings 8 and 11).

    root is the path prefix and is normally the file stem, which is what keeps
    the several weights_*.yaml files apart (ruling 8). The default root is the
    empty string and then no path starts with a dot (ruling 17). The result is
    *not* sorted and *not* deduplicated: this is the raw walk, the ordering of
    ruling 9 is the job of scan_config_trees (T05-F f07). Pure function.
    '''
    found = []
    _walk(tree, root, found)
    return tuple(found)


def _ordered_stems(trees):
    '''The stems of a mapping in ruling 9 order, never in insertion order.

    eval_config first, then every weights_* stem ascending (they share the one
    weights slot of [L1252]), then redlines, grade_rules, anchor_set and
    ahp_matrices, and finally any stem outside the [L1250]-[L1257] list in
    ascending order, so the result stays total and deterministic for a
    synthetic mapping too (ruling 16, T05-F f05, T05-I i13).
    '''
    stems = set(trees)
    ordered = []
    if 'eval_config' in stems:
        ordered.append('eval_config')
    ordered += sorted(stem for stem in stems if stem.startswith(_WEIGHTS_PREFIX))
    for name in _FILE_ORDER[_FILE_ORDER.index('redlines'):]:
        if name in stems:
            ordered.append(name)
    placed = set(ordered)
    ordered += sorted(stem for stem in stems if stem not in placed)
    return tuple(ordered)


def scan_config_trees(trees: Mapping[str, ConfigTree]) -> tuple[str, ...]:
    '''Every unfilled path of several trees, sorted and deduplicated.

    trees maps a file stem to its tree, one entry per weights_*.yaml file as
    well (ruling 16). The order is ruling 9 and does not depend on the
    insertion order of the mapping: file order first, path string ascending
    inside a file. The result is deduplicated and never truncated -- [L878]
    forbids reporting only the first one and ruling 9 forbids any limit, so a
    tree with forty hits yields forty paths (T05-B b10). Pure function: it
    reads no filesystem, a stem that exists nowhere on disk is scanned like any
    other (T05-I i13).
    '''
    found = []
    for stem in _ordered_stems(trees):
        found += sorted(find_placeholders(trees[stem], root=stem))
    return tuple(dict.fromkeys(found))


# ---------------------------------------------------------------------------
# The only I/O of the module (ruling 11 / T05-I i11): reading the six yaml
# patterns of [L877]. Every helper here is private, so load_all stays the one
# public entry point that touches the filesystem.
# ---------------------------------------------------------------------------
def _read_tree(path):
    '''yaml.safe_load of one file, handed back exactly as parsed.

    ruling 4: no numeric conversion, no type coercion, no default filling -- an
    int stays an int and a float stays a float, because the H-4 numeric gate is
    S1-T06 (blocker B-022). An empty file and a comment-only file both load as
    None, which ruling 6 turns into a hit on the bare stem (T05-D d07 / d08).
    '''
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def _weights_stems(directory):
    '''The stems of every weights_*.yaml that is there, ascending (ruling 18).

    The glob of [L877] is used verbatim, so the wider weights_WV-*.yaml naming
    of [L1252] is covered as well. A directory that does not exist simply has
    none, which is the missing case and not an error of its own (T05-K k06).
    '''
    if not directory.is_dir():
        return ()
    return tuple(sorted(path.stem for path in directory.glob(WEIGHTS_GLOB)
                        if path.is_file()))


def _read_config_dir(directory):
    '''Read what is there and name what is not: (trees, missing_stems).

    ruling 10 / V-14: a required file that is absent is *reported*, never
    replaced by an empty tree, so an absent file can never masquerade as a
    configuration that happens to be free of placeholders. The weights gap is
    spelled 'weights_*' (ruling 18) because the requirement is "at least one
    weights_*.yaml", not one particular version. A directory that does not
    exist is the same case with everything missing (T05-K k06), and a yaml file
    outside the [L877] list is not part of the configuration at all, so it is
    neither required nor scanned (T05-G g12; ruling 7 keeps the csv out).
    '''
    trees = {}
    missing = []
    for stem in REQUIRED_CONFIG_STEMS:
        path = directory / (stem + _YAML_SUFFIX)
        if not path.is_file():
            missing.append(stem)
            continue
        trees[stem] = _read_tree(path)
    weights_stems = _weights_stems(directory)
    if not weights_stems:
        missing.append(_WEIGHTS_GAP)
    for stem in weights_stems:
        trees[stem] = _read_tree(directory / (stem + _YAML_SUFFIX))
    return trees, tuple(missing)

def load_all(config_dir: str | Path, *, period=None, run_at=None) -> AppConfig:
    '''Load the configuration directory, or refuse to (rulings 11 / 15 / 19).

    config_dir alone was the T05 signature; S1-T06 appends the two optional
    keyword arguments reserved by ORCH-23 ruling 11 and pinned by ORCH-24
    ruling 19, both keyword only and both defaulting to None, so every T05 call
    site keeps working while a caller that knows the evaluation period gets the
    [L880] interval judgement as well. run_at is the injection point of [L1089]:
    this stage accepts it and does not use it, because H-8 keeps the wall clock
    out of every judgement and S3 is the first stage that needs it.

    The inner order is fixed by ORCH-23 ruling 1 and ORCH-24 ruling 2 and does
    not move:

        read the files  ->  PLACEHOLDER scan (T05)
                          ->  semantic validation ([L879]; ruling 2: always)
                          ->  weight version validation ([L880] plus P-11 of
                              [L1435]; ruling 15: validate_weights when a
                              period was injected, the period free version
                              constraints otherwise)
                          ->  AppConfig.

    Unfilled values and missing required files are collected first and leave
    through one single raise, so the operator sees the whole gap at once
    ([L878] / [L1259]) and nothing half-filled reaches a downstream stage. The
    two validation stages raise ConfigSemanticError (exit 3) and
    WeightVersionInvalidError (exit 2) before an AppConfig is handed back, so
    when this function raises, no AppConfig exists and hence no score can be
    produced ([L1091], [L1434], P-10 of [L882] and P-11 of [L1435]). Loading
    precedes preflight in the [L310] call order, so all eight subcommands of
    [L1080]-[L1087] see exit code 3 for a configuration gap and exit code 2 for
    a weight version breach (ruling 4).

    validate_cross_file is deliberately not called here: its two registries
    come from metric_dict.csv and strategy_master, and S1 has no csv loader
    (ruling 2; B-029 pins the S3 preflight wiring).
    '''
    directory = Path(config_dir)
    trees, missing_files = _read_config_dir(directory)
    paths = scan_config_trees(trees)
    if paths or missing_files:
        raise ConfigPlaceholderError(paths, missing_files)
    weights = {}
    for stem in sorted(trees):
        if stem.startswith(_WEIGHTS_PREFIX):
            weights[stem] = trees[stem]
    loaded = AppConfig(
        eval_config=trees['eval_config'],
        weights=weights,
        redlines=trees['redlines'],
        grade_rules=trees['grade_rules'],
        anchor_set=trees['anchor_set'],
        ahp_matrices=trees['ahp_matrices'],
    )

    # ---- the S1-T06 hook of ORCH-23 ruling 1, now filled ------------------
    validate_semantics(loaded)
    if period is None:
        _validate_weight_documents(loaded)
    else:
        validate_weights(loaded, period=period)
    return loaded


# ---------------------------------------------------------------------------
# S1-T06 -- semantic validation ([L879]) and weight version validation ([L880]
# plus P-11 of [L1435]). docs/adr/ORCH-24.md is the contract authority and
# every judgement below names the ruling it implements.
#
# Discipline this second half of the module carries:
#
#   * H-5 / T06-P -- still no business number. The only tolerance reachable
#     from here is numeric.TOL (ruling 6), the only tolerant comparison is
#     numeric.eq_tol, and no CR threshold, alpha range, floor value or weight
#     is proposed: ruling 17 judges existence and parsability, never magnitude
#     (B-041 / B-042 stay open on purpose).
#   * H-4 / ruling 7 -- every number leaves a yaml tree through to_decimal,
#     which is numeric.D wrapped so that a float, a bool, a blank or an
#     unparsable leaf becomes a NUMERIC violation of ConfigSemanticError
#     instead of an escaping NumericError. numeric.from_float is never called:
#     a float in a configuration is a breach, not a value to rescue.
#   * H-6 / H-7 / ruling 5 -- a reason_code is always an RC member, so none of
#     the five registered spellings ever appears as a string literal here.
#   * H-8 / ruling 19 -- to_decimal, period_key, validate_semantics,
#     validate_cross_file, select_weight_stem and validate_weights are pure:
#     no I/O, no wall clock (period and run_at arrive as arguments, ruling 8),
#     no global state, no mutation of an argument, byte identical results for
#     byte identical input.
#   * H-9 / ruling 20 -- still L1. The two added dependencies are the L1 peers
#     dsm.numeric and dsm.reason_codes, spelled in the intra package form; no
#     L0a / L0b (INV-1), no dsm.models (the judgements read the raw ConfigTree
#     dicts of ORCH-23 ruling 3), no io_loaders.
#   * V-14 / ruling 2 -- metric_ids, strategy_ids and period are required
#     keyword arguments without a default, so a forgotten injection is a loud
#     TypeError and never a silently skipped judgement.
# ---------------------------------------------------------------------------
# ruling 4: the single source of truth for exit code 2 ([L1080] / [L1280] /
# [L900] / [L1413]). S9-T01 cli.py imports it instead of writing the literal.
# The integer is an exit code, not a business value.
EXIT_BLOCK = 2

# ruling 19 verbatim: the six judgements of [L879] in the original order plus
# the two pre-condition classes, then the five version checks of ruling 15 plus
# the same two. The tuples are the sort key of ruling 18.
SEMANTIC_CHECKS = ('SUM_LEVEL1', 'SUM_LEVEL2', 'FLOOR_MONOTONIC',
                   'REDLINE_METRIC_EXISTS', 'ACTION_NON_EMPTY',
                   'ANCHOR_MEMBER_EXISTS', 'STRUCTURE', 'NUMERIC')
WEIGHT_CHECKS = ('WEIGHT_COVERAGE', 'WEIGHT_STATUS_FROZEN',
                 'WEIGHT_WHATIF_RUN_ID', 'WEIGHT_PROVENANCE_COMPLETE',
                 'WEIGHT_APPROVAL', 'STRUCTURE', 'NUMERIC')

# [L1190] status enum and [L1231] provenance kind enum, spelled verbatim. An
# enumeration member of the contract is not a governance value (H-5).
_STATUS_DRAFT = 'DRAFT'
_STATUS_FROZEN = 'FROZEN'
_STATUS_ENUM = (_STATUS_DRAFT, _STATUS_FROZEN)
_KIND_COMBINED = 'AHP_ENTROPY_COMBINED'
_KIND_ENUM = ('AHP_ONLY', _KIND_COMBINED, 'EXPERT_ONLY')

# Key names, verbatim out of the SDD field tables (rulings 9 / 11 / 12 / 13 /
# 15 / 17). No key is invented here and none is promoted into an AppConfig
# field (ORCH-23 ruling 3 stays untouched).
_LEVEL1_KEY = 'level1_weights'                       # [L1192]
_LEVEL2_KEY = 'level2_weights'                       # [L1192]
_STATUS_KEY = 'status'                               # [L1190]
_FROM_KEY = 'effective_from'                         # [L1193]
_TO_KEY = 'effective_to'                             # [L1193]
_PROVENANCE_KEY = 'provenance'                       # [L1194]
_WHATIF_KEY = 'whatif_run_id'                        # [L1241]
_APPROVAL_KEYS = ('approved_by', 'approved_date')    # [L1194] / [L1242]
_GRADE_CODE_KEY = 'grade_code'                       # [L1200]
_FLOOR_KEY = 'attainment_floor'                      # [L1201]
_ACTIONS_KEY = 'actions'                             # [L1205]
_METRIC_ID_KEY = 'metric_id'                         # [L1180]
_STRATEGY_IDS_KEY = 'strategy_ids'                   # [L1212]
_GRADE_ORDER = ('L1', 'L2', 'L3', 'L4')              # [L1200] / [L493]

# The AppConfig slot names (ORCH-23 ruling 3). A violation path that does not
# sit inside one of the weights_*.yaml documents is rooted at its slot, which
# is the very root scan_config_trees uses, so a T06 violation path and a T05
# placeholder path spell one and the same position identically (ruling 14).
_GRADE_RULES_SLOT = 'grade_rules'
_REDLINES_SLOT = 'redlines'
_ANCHOR_SLOT = 'anchor_set'
_WEIGHTS_SLOT = 'weights'
_PERIOD_PATH = 'period'

# ruling 18 message format, pinned by the ADR because the SDD is silent.
_SEMANTIC_HEAD = '配置语义校验失败 %d 项（退出码 %d）'
_WEIGHT_HEAD = '权重版本校验失败 %d 项（退出码 %d，%s）'
_VIOLATION_ITEM = '  - %s %s: %s'

# ruling 8: the two accepted string shapes of a period or of an interval end
# point, plus the calendar facts that reject a month or a day no calendar has.
# A calendar constant is not a governance value (H-5), and the wall clock is
# never read: a date arrives as an argument or as a yaml leaf.
_PERIOD_DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
_PERIOD_MONTH = re.compile(r'\d{4}-\d{2}')
_MONTH_FIRST_DAY = '-01'
_MONTHS_IN_YEAR = 12
_FEBRUARY = 2
_FEBRUARY_LEAP_DAY = 29
_MONTH_DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
# 名字里的 step 不是笔误：公历四年一步是历法常量，不是治理数值（H-5）；
# 用 cycle 拼写会被 T05 l01 的业务词扫描器按字面命中。
_LEAP_STEP = 4
_LEAP_CENTURY = 100
_LEAP_QUAD_CENTURY = 400


def _structure(path, detail):
    '''One STRUCTURE triple of ruling 18 (structure and type problems, which
    ruling 15 always exits with 3).'''
    return ('STRUCTURE', path, detail)


def _key_text(key):
    '''The textual spelling of a mapping key, so a yaml mapping with a
    non-string key still yields a readable path (ORCH-23 ruling 8).'''
    return key if isinstance(key, str) else str(key)


def _rank(checks, check_id):
    '''The ruling 18 position of one check id. An id outside the tuple sorts
    last, which keeps the key total for a caller supplied triple.'''
    return checks.index(check_id) if check_id in checks else len(checks)


def _normalise(violations, checks):
    '''ruling 18: (check_id, path, detail) triples of str, deduplicated with
    the first occurrence kept, sorted by (checks.index, path), never truncated
    and never limited -- the same discipline [L878] set for the placeholder
    paths.'''
    seen = {}
    for item in violations:
        check_id, path, detail = item
        seen.setdefault((str(check_id), str(path), str(detail)), None)
    return tuple(sorted(seen, key=lambda triple: (_rank(checks, triple[0]),
                                                  triple[1])))


def _violation_message(head, violations):
    '''ruling 18: the head line, then one item line per violation in the
    stored order, each spelled as two spaces, a dash, check_id, path, colon,
    detail.'''
    lines = [head]
    lines += [_VIOLATION_ITEM % item for item in violations]
    return '\n'.join(lines)


class ConfigSemanticError(Exception):
    '''The exit of the six semantic judgements of [L879] ([L881], exit code 3).

    ruling 3 keeps the SDD spelling and the three exceptions peers: no
    WeightSumError, no WeightVersionNotFrozenError, no shared intermediate base
    class. ruling 4 gives this one exit code 3 and ruling 5 gives it exactly
    one reason_code, RC.CONFIG_SEMANTIC_ERROR, whatever the breached judgement
    was -- the check_id of a violation carries the detail (ruling 18).

    The same class is the exit of every structure and type problem the version
    half finds, because ruling 15 draws its line as: structure and type
    problems always exit 3, version policy problems always exit 2 (T06-H h08 /
    h13 / h14, T06-M m62).
    '''

    def __init__(self, violations):
        self.violations = _normalise(violations, SEMANTIC_CHECKS)
        self.reason_code = RC.CONFIG_SEMANTIC_ERROR
        self.exit_code = EXIT_CONFIG
        super().__init__(_violation_message(
            _SEMANTIC_HEAD % (len(self.violations), self.exit_code),
            self.violations))


class WeightVersionInvalidError(Exception):
    '''The exit of the weight version judgements of [L880] ([L881], exit 2).

    ruling 15 fixes the judgement order and takes the reason_code from the
    FIRST hit, so one exception carries one code that G-11 and the audit_bundle
    can assert on, while ruling 18 still lists every breach in violations.
    ruling 4 gives exit code 2 (EXIT_BLOCK) for every version policy breach,
    because [L900] C-01 and [L1280] both end in BLOCK.
    '''

    def __init__(self, reason_code, violations=()):
        self.reason_code = reason_code
        self.violations = _normalise(violations, WEIGHT_CHECKS)
        self.exit_code = EXIT_BLOCK
        super().__init__(_violation_message(
            _WEIGHT_HEAD % (len(self.violations), self.exit_code,
                            reason_code.value),
            self.violations))


# ---------------------------------------------------------------------------
# The numeric gate (ruling 7, H-4) and the period gate (ruling 8, H-8).
# ---------------------------------------------------------------------------
def to_decimal(value, *, path):
    '''numeric.D behind one explicit gate: the H-4 entry point of the config
    layer (blocker B-022 closed).

    A weight, an attainment_floor, a CR or an alpha has to be an int, a str or
    a Decimal. A float, a bool, a blank or an unparsable string is a NUMERIC
    violation at the path the caller names, raised as ConfigSemanticError so
    that no NumericError ever escapes the config layer (ruling 7, exit code 3).
    Pure function.
    '''
    try:
        return numeric.D(value)
    except numeric.NumericError as exc:
        raise ConfigSemanticError((
            ('NUMERIC', path,
             '数值口径非法（H-4）：期望 int / str / Decimal，实得 %s'
             % type(value).__name__),)) from exc


def _is_leap_year(year):
    '''The Gregorian leap year rule: a calendar fact, not a governance value.'''
    if year % _LEAP_STEP:
        return False
    if year % _LEAP_CENTURY:
        return True
    return not year % _LEAP_QUAD_CENTURY


def _month_length(year, month):
    if month == _FEBRUARY and _is_leap_year(year):
        return _FEBRUARY_LEAP_DAY
    return _MONTH_DAYS[month - 1]


def _calendar_day(text, path):
    '''Reject an ISO day string that no calendar has (ruling 8, T06-I i10).

    The digit pattern alone would accept month 13 and day 32, and [L1307]
    (宁可不评, 不可错评) decides against waving through a date that cannot
    exist, so month and day are checked against the calendar. The datetime
    module is deliberately not imported -- ORCH-23 ruling 12 keeps every clock
    and calendar module out of this file (H-8) -- and the four integers of the
    leap year rule are all that is needed in its place.
    '''
    parts = text.split('-')
    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    except (IndexError, ValueError):
        raise ConfigSemanticError((_structure(
            path, '不是日历可解析的 ISO 日期：%s' % text),)) from None
    if month < 1 or month > _MONTHS_IN_YEAR:
        raise ConfigSemanticError((_structure(
            path, '月份超出日历范围：%s' % text),))
    if day < 1 or day > _month_length(year, month):
        raise ConfigSemanticError((_structure(
            path, '日超出该月天数：%s' % text),))


def _period_key(value, path):
    '''period_key with a caller supplied violation path (ruling 8).

    Three shapes are accepted and all three normalise onto one comparable
    string: a date / datetime object through its isoformat, a YYYY-MM-DD string
    as it stands (stripped) and a YYYY-MM string left aligned to the first day
    of that month. The coverage test that follows is then a plain string
    comparison, because ISO order is time order. Anything else is a STRUCTURE
    breach at path.
    '''
    isoformat = getattr(value, 'isoformat', None)
    if callable(isoformat) and not isinstance(value, str):
        # datetime.date and datetime.datetime. The value arrives as an argument
        # or as a yaml leaf, so no wall clock is ever read here (H-8).
        return isoformat()
    if isinstance(value, str):
        text = value.strip()
        if _PERIOD_DAY.fullmatch(text):
            _calendar_day(text, path)
            return text
        if _PERIOD_MONTH.fullmatch(text):
            day_form = text + _MONTH_FIRST_DAY
            _calendar_day(day_form, path)
            return day_form
    raise ConfigSemanticError((_structure(
        path,
        '评价期形态非法：只接受 YYYY-MM / YYYY-MM-DD / date / datetime，实得 %s'
        % type(value).__name__),))


def period_key(value):
    '''The comparable key of one evaluation period or interval end point.

    ruling 8: a YYYY-MM string, a YYYY-MM-DD string and a date / datetime
    object all normalise onto a day aligned ISO string, which turns the closed
    interval test of [L880] into a string comparison. Pure function; an illegal
    shape is a STRUCTURE breach of ConfigSemanticError (ruling 15, exit 3).
    '''
    return _period_key(value, _PERIOD_PATH)


# ---------------------------------------------------------------------------
# The recursive key collection of ruling 14. The SDD never names the top level
# key of redlines.yaml / grade_rules.yaml / anchor_set.yaml, so a judgement
# collects the mappings that carry the key it is about, at any depth, and the
# path notation is the frozen one of ORCH-23 ruling 8 (stem, dots, zero based
# bracket index).
# ---------------------------------------------------------------------------
def _walk_mappings(node, prefix, visit):
    '''Depth first walk calling visit(path, mapping) for every mapping.

    The notation is the T05 one byte for byte: a key joins with a dot through
    _join, and a list index is appended as a bracketed position by this walk
    itself, which is exactly the ruling 22 bracket completion _join documents.
    Pure: it reads no filesystem and changes nothing.
    '''
    if isinstance(node, dict):
        visit(prefix, node)
        for key in node:
            _walk_mappings(node[key], _join(prefix, _key_text(key)), visit)
        return
    if isinstance(node, list):
        for index, item in enumerate(node):
            _walk_mappings(item, '%s[%d]' % (prefix, index), visit)


def _collect_mappings(tree, root, keys):
    '''Every mapping under root that carries all of keys, with its path.'''
    found = []

    def visit(path, node):
        if all(key in node for key in keys):
            found.append((path, node))

    _walk_mappings(tree, root, visit)
    return tuple(found)


# ---------------------------------------------------------------------------
# Rulings 6 / 9: the two Sigma judgements.
# ---------------------------------------------------------------------------
def _sum_of(path, mapping, check_id):
    '''One Sigma: numeric.eq_tol(sum of the values, numeric.ONE), the tolerance
    being numeric.TOL on a closed interval (ruling 6, [L902]).

    The sum is a Decimal sum and never a float accumulation (H-4). A leaf that
    does not pass to_decimal is a NUMERIC violation and replaces the Sigma
    judgement for this mapping, because a sum over values one of which is
    illegal is no statement about the configuration (ruling 7). An empty
    mapping sums to numeric.ZERO and therefore breaches naturally, with no
    special case (ruling 9).
    '''
    total = numeric.ZERO
    illegal = []
    for name in sorted(mapping, key=_key_text):
        try:
            total += to_decimal(mapping[name],
                                path=_join(path, _key_text(name)))
        except ConfigSemanticError as exc:
            illegal += exc.violations
    if illegal:
        return tuple(illegal)
    if numeric.eq_tol(total, numeric.ONE):
        return ()
    return ((check_id, path,
             '权重之和为 %s，与 1 之差超出 numeric.TOL（[L879] / [L902]）'
             % total),)


def _weight_sum_violations(stem, tree):
    '''ruling 9: level1_weights and level2_weights sit at the TOP level of a
    weights document ([L1190]-[L1194] are document columns), so they are read
    directly and never hunted recursively. A missing key is a STRUCTURE breach;
    the per dimension Sigma of level2 is judged dimension by dimension and
    reported under its own path.'''
    found = []
    for key, check_id in ((_LEVEL1_KEY, 'SUM_LEVEL1'),
                          (_LEVEL2_KEY, 'SUM_LEVEL2')):
        path = _join(stem, key)
        if key not in tree:
            found.append(_structure(
                path, '权重文件顶层缺 %s（[L1192]，ruling 9 结构前置）' % key))
            continue
        node = tree[key]
        if not isinstance(node, dict):
            found.append(_structure(path, '%s 必须是一份映射' % key))
            continue
        if check_id == 'SUM_LEVEL1':
            found += _sum_of(path, node, check_id)
            continue
        for dim in sorted(node, key=_key_text):
            dim_path = _join(path, _key_text(dim))
            inner = node[dim]
            if not isinstance(inner, dict):
                found.append(_structure(dim_path, '维度内指标权重必须是一份映射'))
                continue
            found += _sum_of(dim_path, inner, check_id)
    return tuple(found)


# ---------------------------------------------------------------------------
# Rulings 10 / 11: attainment_floor monotone over exactly four grades, and a
# non-empty actions on every grade rule.
# ---------------------------------------------------------------------------
def _actions_are_empty(value):
    '''ruling 11: None, an empty list / tuple / dict, an empty string and a
    sequence whose every member is blank all count as empty. A filled scalar
    and a sequence carrying one non-blank member do not. action_gate is never
    looked at, because [L879] names the action only.'''
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ''
    if isinstance(value, Mapping):
        return not value
    if isinstance(value, Iterable):
        return all(isinstance(item, str) and item.strip() == ''
                   for item in value)
    return False


def _action_violations(path, rule):
    '''One grade rule, one judgement. A missing actions key is the same breach
    as an empty one: [L879] requires a non-empty action for every level, and a
    level that carries no actions key carries no action at all.'''
    leaf = _join(path, _ACTIONS_KEY)
    if _ACTIONS_KEY not in rule:
        return (('ACTION_NON_EMPTY', leaf,
                 'grade_rule 缺 %s（[L879] action 必须非空，ruling 11）'
                 % _ACTIONS_KEY),)
    if _actions_are_empty(rule[_ACTIONS_KEY]):
        return (('ACTION_NON_EMPTY', leaf,
                 'actions 为空（ruling 11：空 list / tuple / dict / 空串 / '
                 '全为空白串的序列）'),)
    return ()


def _floor_violations(by_code):
    '''ruling 10: L1 > L2 > L3 > L4 strictly, compared as Decimal with NO
    tolerance -- an order relation is exact, so two floors differing by less
    than numeric.TOL are still strictly decreasing while two equal floors are a
    breach however small the intended gap was. The breach is reported at the
    path of the lower grade of the pair.'''
    ordered = []
    illegal = []
    for code in _GRADE_ORDER:
        path, rule = by_code[code]
        try:
            value = to_decimal(rule[_FLOOR_KEY],
                               path=_join(path, _FLOOR_KEY))
        except ConfigSemanticError as exc:
            illegal += exc.violations
            continue
        ordered.append((code, path, value))
    if illegal:
        return tuple(illegal)
    found = []
    for index in range(1, len(ordered)):
        higher_code, _, higher = ordered[index - 1]
        lower_code, lower_path, lower = ordered[index]
        if higher > lower:
            continue
        found.append(('FLOOR_MONOTONIC', lower_path,
                      'attainment_floor 必须严格递减（[L879]）：%s = %s 未大于 '
                      '%s = %s' % (higher_code, higher, lower_code, lower)))
    return tuple(found)


def _grade_rule_violations(tree):
    '''ruling 14 collection plus rulings 10 and 11.

    A grade rule is any mapping carrying both grade_code and attainment_floor,
    at any depth, because the SDD never names the top level key of
    grade_rules.yaml. The four grades have to be exactly L1, L2, L3 and L4, one
    row each ([L1200], [L493]): a missing grade, a grade_code collected twice or
    a fifth grade is a STRUCTURE breach, and only a structurally sound four row
    set has a decidable order to check monotonicity on.
    '''
    found = []
    by_code = {}
    for path, rule in _collect_mappings(
            tree, _GRADE_RULES_SLOT, (_GRADE_CODE_KEY, _FLOOR_KEY)):
        code = _key_text(rule[_GRADE_CODE_KEY])
        if code in by_code:
            found.append(_structure(
                path,
                'grade_code %s 被收集到多次，配置不自洽且不得静默取第一个'
                '（ruling 14）' % code))
            continue
        by_code[code] = (path, rule)
        found += _action_violations(path, rule)
    if set(by_code) != set(_GRADE_ORDER):
        listed = ', '.join(sorted(by_code)) if by_code else '（一条也没有）'
        found.append(_structure(
            _GRADE_RULES_SLOT,
            'attainment_floor 必须恰为 L1 / L2 / L3 / L4 四级各一条'
            '（[L879] / [L493] / [L1200]），实得：%s' % listed))
        return tuple(found)
    if any(item[0] == 'STRUCTURE' for item in found):
        return tuple(found)
    return tuple(found) + _floor_violations(by_code)


def validate_semantics(cfg):
    '''The four judgements of [L879] that need no external registry (ruling 2).

    Sigma W_d = 1 and, inside every dimension, Sigma w_j = 1 (rulings 6 / 9);
    attainment_floor strictly decreasing over exactly four grades (ruling 10);
    a non-empty actions on every grade rule (ruling 11). The two cross file
    judgements live in validate_cross_file, which load_all does not call
    because S1 has no csv loader (ruling 2, T06-G g08).

    Only a FROZEN weights document is sum checked: [L1190] restricts scoring to
    FROZEN and [L379] makes DRAFT the intermediate product of combine build, so
    a draft is left alone while a FROZEN sibling next to it still is checked
    (ruling 9). Pure function; every breach is listed in one exception
    (ruling 18).
    '''
    found = []
    for stem in sorted(cfg.weights):
        tree = cfg.weights[stem]
        if not isinstance(tree, dict):
            found.append(_structure(stem, '权重文件不是一份映射'))
            continue
        if tree.get(_STATUS_KEY) != _STATUS_FROZEN:
            continue
        found += _weight_sum_violations(stem, tree)
    found += _grade_rule_violations(cfg.grade_rules)
    if found:
        raise ConfigSemanticError(found)


def validate_cross_file(cfg, *, metric_ids, strategy_ids):
    '''The two judgements of [L879] that need a registry (rulings 2 / 12 / 13).

    Every metric_id a redline threshold refers to has to exist in metric_dict,
    and every member of an anchor set has to exist in strategy_master. Both
    registries are required keyword arguments with no default, because a None
    default plus skipping when None is the silent degradation V-14 forbids; S3
    preflight injects them (B-029 pins that wiring).

    An empty registry blocks every reference instead of waving it through
    (ruling 12), while a tree without any reference and an empty member
    sequence are no breach at all -- whether an anchor set is too small or
    stale is the C-10 effectiveness question of S3, not a config self
    consistency one (ruling 13). Pure function.
    '''
    found = []
    for path, node in _collect_mappings(cfg.redlines, _REDLINES_SLOT,
                                        (_METRIC_ID_KEY,)):
        reference = node[_METRIC_ID_KEY]
        if isinstance(reference, str) and reference in metric_ids:
            continue
        found.append(('REDLINE_METRIC_EXISTS', _join(path, _METRIC_ID_KEY),
                      '红线阈值引用的指标不在 metric_dict 注册表内'
                      '（[L879] / [L1180]）'))
    for path, node in _collect_mappings(cfg.anchor_set, _ANCHOR_SLOT,
                                        (_STRATEGY_IDS_KEY,)):
        members = node[_STRATEGY_IDS_KEY]
        leaf = _join(path, _STRATEGY_IDS_KEY)
        if isinstance(members, str) or not isinstance(members, Iterable):
            found.append(_structure(
                leaf, 'strategy_ids 必须是一份序列（[L1212]）'))
            continue
        for index, member in enumerate(members):
            if isinstance(member, str) and member in strategy_ids:
                continue
            found.append(('ANCHOR_MEMBER_EXISTS', '%s[%d]' % (leaf, index),
                          '锚定集成员不在 strategy_master 注册表内'
                          '（[L879] / [L1212]）'))
    if found:
        raise ConfigSemanticError(found)


# ---------------------------------------------------------------------------
# Rulings 15 / 16 / 17 / 18: the weight version half.
# ---------------------------------------------------------------------------
def _weight_stems(cfg):
    '''The weights stems in ORCH-23 ruling 9 order (ascending), which is what
    makes the listing of a multi coverage breach deterministic (ruling 16).'''
    return tuple(sorted(cfg.weights))


def _interval_structure(stem, tree):
    '''The structure and type pre-conditions of one weights document: the three
    status / interval keys of [L1190]-[L1193] present, the two end points of a
    shape period_key accepts, status a string. ruling 15 exits all of them with
    code 3, so they are collected before any coverage judgement runs.'''
    if not isinstance(tree, dict):
        return (_structure(stem, '权重文件不是一份映射'),)
    found = []
    for key in (_STATUS_KEY, _FROM_KEY, _TO_KEY):
        if key not in tree:
            found.append(_structure(
                _join(stem, key),
                '权重版本缺必需键 %s（[L1190]-[L1193]，ruling 15）' % key))
    for key in (_FROM_KEY, _TO_KEY):
        if key in tree:
            try:
                _period_key(tree[key], _join(stem, key))
            except ConfigSemanticError as exc:
                found += exc.violations
    if _STATUS_KEY in tree and not isinstance(tree[_STATUS_KEY], str):
        found.append(_structure(
            _join(stem, _STATUS_KEY),
            'status 必须是 [L1190] 的字符串枚举 DRAFT / FROZEN'))
    return tuple(found)


def _select(cfg, period):
    '''(normalised period key, covering stems ascending), or a
    ConfigSemanticError when a document is structurally unfit to judge.

    The coverage test is ruling 8s closed interval on the normalised keys:
    period_key(effective_from) <= period_key(period) <= period_key(effective_to).
    Both end points count as inside, because [L880] writes a bracket and
    [L1413] calls only a period beyond effective_to stale.
    '''
    key = _period_key(period, _PERIOD_PATH)
    structure = []
    covering = []
    for stem in _weight_stems(cfg):
        tree = cfg.weights[stem]
        hits = _interval_structure(stem, tree)
        if hits:
            structure += hits
            continue
        low = _period_key(tree[_FROM_KEY], _join(stem, _FROM_KEY))
        high = _period_key(tree[_TO_KEY], _join(stem, _TO_KEY))
        if low <= key <= high:
            covering.append(stem)
    if structure:
        raise ConfigSemanticError(structure)
    return key, tuple(covering)


def _coverage_violations(stems, detail):
    '''One WEIGHT_COVERAGE triple per stem, so a multi coverage breach names
    every version that fought for the period (ruling 16, T06-K k62).'''
    return tuple(('WEIGHT_COVERAGE', stem, detail) for stem in stems)


def _stale_detail(key):
    return ('评价期 %s 不落在任何权重版本的 [effective_from, effective_to] 内'
            '（[L880] / [L1413] G-11(a)）' % key)


def _ambiguous_detail(key, count):
    return ('评价期 %s 同时被 %d 份权重版本覆盖，期内权重必须唯一'
            '（[L1191]，B-039 保守判失败）' % (key, count))


def select_weight_stem(cfg, *, period):
    '''The one weights stem that covers the evaluation period (ruling 16).

    Exposed on its own so that S3 preflight and the whatif chain can name the
    version they scored with. Zero covering versions raise with
    RC.WEIGHT_VERSION_STALE and two or more with RC.WEIGHT_VERSION_INVALID,
    which are the ruling 15 序 2 / 序 3 codes, so this helper and
    validate_weights can never disagree about one and the same directory. Pure
    function; period is required and has no default (ruling 2).
    '''
    key, covering = _select(cfg, period)
    if not covering:
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_STALE,
            _coverage_violations(_weight_stems(cfg), _stale_detail(key)))
    if len(covering) > 1:
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_INVALID,
            _coverage_violations(covering,
                                 _ambiguous_detail(key, len(covering))))
    return covering[0]


def _require_number(holder, key, base_path, version, structure):
    '''ruling 17: a provenance number has to exist and to be parsable, and its
    VALUE is never judged -- the CR threshold and the alpha range are governance
    parameters the SDD does not give (B-041 / B-042), so proposing one here
    would be inventing a business number (H-5). A key that is absent is a
    WEIGHT_PROVENANCE_COMPLETE breach; a key that is present but illegal is a
    NUMERIC breach and therefore exits 3 (rulings 7 / 15).'''
    path = _join(base_path, key)
    if key not in holder:
        version.append(('WEIGHT_PROVENANCE_COMPLETE', path,
                        'P-11 缺 %s（[L1435]；只判存在与可解析，不判数值）'
                        % key))
        return
    try:
        to_decimal(holder[key], path=path)
    except ConfigSemanticError as exc:
        structure += exc.violations


def _provenance_segments(prov_path, prov, version, structure):
    '''The kind conditional required segment matrix of ruling 17 (序 6).

    AHP_ONLY and EXPERT_ONLY need the ahp segment with a non empty
    comparison_matrices and a cr; AHP_ENTROPY_COMBINED needs all of that plus
    entropy, combine carrying an alpha, and alpha_basis ([L1435]: 若 combined
    则含 alpha + alpha_basis + whatif_run_id). EXPERT_ONLY takes the AHP_ONLY
    row because [L1435] says 任何 FROZEN 权重版本 without a kind condition --
    the conservative superset, with the tension registered as B-043. An extra
    segment is never a breach (ruling 17, minimal implementation).
    '''
    kind = prov.get('kind')
    if not isinstance(kind, str) or kind not in _KIND_ENUM:
        structure.append(_structure(
            _join(prov_path, 'kind'),
            'provenance.kind 必须是 [L1231] 枚举 AHP_ONLY / '
            'AHP_ENTROPY_COMBINED / EXPERT_ONLY 之一'))
        return
    ahp_path = _join(prov_path, 'ahp')
    ahp = prov.get('ahp')
    if not isinstance(ahp, dict):
        version.append(('WEIGHT_PROVENANCE_COMPLETE', ahp_path,
                        'P-11 缺 AHP 段（[L1435] AHP 矩阵 + CR）'))
    else:
        matrices = ahp.get('comparison_matrices')
        if not isinstance(matrices, dict) or not matrices:
            version.append(('WEIGHT_PROVENANCE_COMPLETE',
                            _join(ahp_path, 'comparison_matrices'),
                            'P-11 ahp.comparison_matrices 必须是非空映射'
                            '（[L1435] / [L1232]）'))
        _require_number(ahp, 'cr', ahp_path, version, structure)
    if kind != _KIND_COMBINED:
        return
    if 'entropy' not in prov:
        version.append(('WEIGHT_PROVENANCE_COMPLETE',
                        _join(prov_path, 'entropy'),
                        'P-11 combined 缺 entropy 段（[L1435]）'))
    combine_path = _join(prov_path, 'combine')
    combine = prov.get('combine')
    if not isinstance(combine, dict):
        version.append(('WEIGHT_PROVENANCE_COMPLETE', combine_path,
                        'P-11 combined 缺 combine 段（[L1435]）'))
    else:
        _require_number(combine, 'alpha', combine_path, version, structure)
    if 'alpha_basis' not in prov:
        version.append(('WEIGHT_PROVENANCE_COMPLETE',
                        _join(prov_path, 'alpha_basis'),
                        'P-11 combined 缺 alpha_basis（[L1435]）'))


def _approval(prov_path, prov, version, structure):
    '''序 7: approved_by and approved_date ([L900] C-01, [L1194], [L1242]).
    A missing key and a blank one are the same breach; a value that is neither
    a string nor a date is a type problem and therefore exits 3 (ruling 15).'''
    for key in _APPROVAL_KEYS:
        path = _join(prov_path, key)
        if key not in prov:
            version.append(('WEIGHT_APPROVAL', path,
                            'C-01 缺 %s（[L900] / [L1242]）' % key))
            continue
        value = prov[key]
        if callable(getattr(value, 'isoformat', None)):
            continue
        if not isinstance(value, str):
            structure.append(_structure(
                path, '%s 必须是字符串或 ISO 日期（[L889]）' % key))
            continue
        if value.strip() == '':
            version.append(('WEIGHT_APPROVAL', path,
                            'C-01 %s strip 后为空（[L900]）' % key))


def _missing_provenance_violation(prov_path):
    '''ruling 17: the provenance key itself absent on a FROZEN version is
    RC.WEIGHT_VERSION_INVALID -- P-11 says 缺任一项 then the load fails, and
    the models layer allowing an empty provenance (ORCH-20 ruling 2) is exactly
    why ORCH-20 L145 handed this gate to the config layer.'''
    return ('WEIGHT_PROVENANCE_COMPLETE', prov_path,
            'FROZEN 版本必须具备完整 provenance（[L1435] P-11，ruling 17）')


def _frozen_provenance(prov_path, prov, version, structure):
    '''序 5, 序 6 and 序 7 over one FROZEN provenance.

    Returns the reason_code of the FIRST hit in the ruling 15 order and appends
    every breach to version (or to structure for the type problems), so that one
    exception carries one code and the whole gap list at once (rulings 15 / 18).
    序 5 is what [L880] / [L678] / [L1281] / [L1374] say five times over: a
    FROZEN version without a whatif_run_id fails the load, and it is neither a
    warning nor a downgrade (V-14).
    '''
    reason = None
    whatif_path = _join(prov_path, _WHATIF_KEY)
    if _WHATIF_KEY not in prov:
        version.append(('WEIGHT_WHATIF_RUN_ID', whatif_path,
                        'FROZEN 而缺 %s，签认前未做影响预演（[L880] / [L678] / '
                        '[L1281] / [L1374]）' % _WHATIF_KEY))
        reason = RC.WEIGHT_MISSING_WHATIF_RUN_ID
    else:
        run_id = prov[_WHATIF_KEY]
        if not isinstance(run_id, str):
            structure.append(_structure(
                whatif_path,
                '%s 必须是字符串（ruling 18，models.WeightProvenance 口径）'
                % _WHATIF_KEY))
        elif run_id.strip() == '':
            version.append(('WEIGHT_WHATIF_RUN_ID', whatif_path,
                            'FROZEN 而 %s strip 后为空（ruling 15 序 5）'
                            % _WHATIF_KEY))
            reason = RC.WEIGHT_MISSING_WHATIF_RUN_ID
    marks = len(version)
    _provenance_segments(prov_path, prov, version, structure)
    if len(version) > marks and reason is None:
        reason = RC.WEIGHT_VERSION_INVALID
    marks = len(version)
    _approval(prov_path, prov, version, structure)
    if len(version) > marks and reason is None:
        reason = RC.WEIGHT_VERSION_INVALID
    return reason


def validate_weights(cfg, *, period):
    '''The three version judgements of [L880] plus P-11, in the fixed order of
    ruling 15: no weights document at all (序 1), no version covering the period
    (序 2), more than one covering it (序 3), a selected version that is not
    FROZEN (序 4), a FROZEN version without a whatif_run_id (序 5), an
    incomplete provenance (序 6) and a missing approval (序 7). Every breach is
    collected; the reason_code is the first hit.

    A structure or type problem leaves through ConfigSemanticError (exit 3) and
    a version policy problem through WeightVersionInvalidError (exit 2), which
    is the dividing line ruling 15 draws. period is a required keyword argument,
    so a caller without a period takes the period free branch of load_all
    instead of silently skipping the interval judgement (V-14). Pure function.
    '''
    stems = _weight_stems(cfg)
    if not stems:
        # 序 1, the defensive redundancy over ORCH-23 ruling 10.
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_INVALID,
            (('WEIGHT_COVERAGE', _WEIGHTS_SLOT,
              '配置目录里没有任何 weights_*.yaml（[L877]，ruling 15 序 1）'),))
    key, covering = _select(cfg, period)
    if not covering:
        # 序 2: [L880] plus [L1413] G-11(a), code STALE.
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_STALE,
            _coverage_violations(stems, _stale_detail(key)))
    if len(covering) > 1:
        # 序 3: [L1191] wants one version per period, B-039.
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_INVALID,
            _coverage_violations(covering,
                                 _ambiguous_detail(key, len(covering))))
    stem = covering[0]
    tree = cfg.weights[stem]
    status = tree[_STATUS_KEY]
    if status != _STATUS_FROZEN:
        # 序 4: [L880] / [L1190] / [L1280] -- only a FROZEN version may score.
        code = (RC.WEIGHT_VERSION_DRAFT if status == _STATUS_DRAFT
                else RC.WEIGHT_VERSION_INVALID)
        raise WeightVersionInvalidError(
            code,
            (('WEIGHT_STATUS_FROZEN', _join(stem, _STATUS_KEY),
              'status 必须为 FROZEN 才能用于评分（[L880] / [L1190] / '
              '[L1280]），实得 %s' % status),))
    prov_path = _join(stem, _PROVENANCE_KEY)
    prov = tree.get(_PROVENANCE_KEY)
    if not isinstance(prov, dict):
        # 序 6 head: ruling 17 makes the absent key itself a version breach.
        raise WeightVersionInvalidError(
            RC.WEIGHT_VERSION_INVALID,
            (_missing_provenance_violation(prov_path),))
    version = []
    structure = []
    reason = _frozen_provenance(prov_path, prov, version, structure)
    if structure:
        raise ConfigSemanticError(structure)
    if version:
        raise WeightVersionInvalidError(reason, version)


def _validate_weight_documents(cfg):
    '''The period free version constraints of ruling 15, i.e. the load_all
    branch that runs when no period was injected.

    [L1374] reads: 缺 whatif_run_id 而写 FROZEN then the next config load fails
    outright, which is a statement about ANY load, so no period is needed for
    it. Every weights document has to carry a legal [L1190] status, and every
    FROZEN one has to satisfy 序 5 / 序 6 / 序 7. The interval judgement of
    [L880] is the one thing that genuinely needs a period; without one it is
    not executed at all, instead of being executed against a wall clock (H-8) or
    waved through (V-14).
    '''
    structure = []
    version = []
    reason = None
    for stem in _weight_stems(cfg):
        tree = cfg.weights[stem]
        status_path = _join(stem, _STATUS_KEY)
        if not isinstance(tree, dict) or _STATUS_KEY not in tree:
            structure.append(_structure(
                status_path, '权重版本缺 %s 键（[L1190]）' % _STATUS_KEY))
            continue
        status = tree[_STATUS_KEY]
        if not isinstance(status, str) or status not in _STATUS_ENUM:
            structure.append(_structure(
                status_path,
                'status 必须属于 [L1190] 枚举 DRAFT / FROZEN，实得 %s'
                % (status,)))
            continue
        if status != _STATUS_FROZEN:
            continue
        prov_path = _join(stem, _PROVENANCE_KEY)
        prov = tree.get(_PROVENANCE_KEY)
        if not isinstance(prov, dict):
            version.append(_missing_provenance_violation(prov_path))
            if reason is None:
                reason = RC.WEIGHT_VERSION_INVALID
            continue
        hit = _frozen_provenance(prov_path, prov, version, structure)
        if hit is not None and reason is None:
            reason = hit
    if structure:
        raise ConfigSemanticError(structure)
    if version:
        raise WeightVersionInvalidError(reason, version)
