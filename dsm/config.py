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

The semantic checks of [L879] and the weight version checks of [L880] belong to
S1-T06. load_all marks that hook with a comment so T06 can fill it without
touching the function skeleton, and ConfigSemanticError /
WeightVersionInvalidError are deliberately not defined here: [L881] names three
exceptions and T05 owns exactly one (ruling 1).

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
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict

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


def load_all(config_dir: str | Path) -> AppConfig:
    '''Load the configuration directory, or refuse to (ruling 11, exit code 3).

    This is the only I/O entry point of the module and the T05 signature is
    minimal on purpose: config_dir alone, as str or Path. S1-T06 appends the
    --period / --run-at injection of [L1089] as optional keywords, which is not
    a breaking change (ruling 11).

    The inner order is fixed by ruling 1 and does not move:

        read the files  ->  PLACEHOLDER scan (T05)
                          ->  semantic validation hook (S1-T06, comment only)
                          ->  AppConfig.

    Unfilled values and missing required files are collected first and leave
    through one single raise, so the operator sees the whole gap at once
    ([L878] / [L1259]) and nothing half-filled reaches a downstream stage:
    when this function raises, no AppConfig exists, hence no score can be
    produced ([L1091], [L1434], P-10 of [L882]). The scan happens here, in the
    configuration loading stage, which by the [L310] call order precedes
    preflight, so all eight subcommands of [L1080]-[L1087] get exit code 3
    (ruling 2).
    '''
    directory = Path(config_dir)
    trees, missing_files = _read_config_dir(directory)
    paths = scan_config_trees(trees)
    if paths or missing_files:
        raise ConfigPlaceholderError(paths, missing_files)

    # ---- S1-T06 hook (ruling 1) -------------------------------------------
    # Semantic validation ([L879]) and weight version validation ([L880]) run
    # right here, after the PLACEHOLDER scan and before the AppConfig is built:
    # the dimension weights summing to one, the metric weights inside every
    # dimension summing to one, attainment_floor monotone over the grades,
    # every metric a redline threshold refers to present in metric_dict, a
    # non-empty action in grade_rules, every anchor_set member present in
    # strategy_master; and for the weight files a FROZEN status, the evaluation
    # period inside effective_from .. effective_to, plus a FROZEN version
    # without a whatif_run_id failing the load. Those checks raise
    # ConfigSemanticError and WeightVersionInvalidError ([L881]), which S1-T06
    # defines; T05 implements neither, and the skeleton below does not change
    # when they land.
    weights = {}
    for stem in sorted(trees):
        if stem.startswith(_WEIGHTS_PREFIX):
            weights[stem] = trees[stem]
    return AppConfig(
        eval_config=trees['eval_config'],
        weights=weights,
        redlines=trees['redlines'],
        grade_rules=trees['grade_rules'],
        anchor_set=trees['anchor_set'],
        ahp_matrices=trees['ahp_matrices'],
    )
