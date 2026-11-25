'''tests/test_architecture.py -- E5: the machine guard for INV-1 / INV-2 / INV-3, P-8, H-8 and ORCH-03.

Write set of package E5 (docs/RUN-UNATTENDED-v3.0-PARALLEL.md L174): this file
only, PROD 0, TF <= 12. Every check below is a static AST scan of dsm/*.py. This
file never imports a dsm module, so a half-landed or broken sibling module can
not turn an architecture guard into a collection error while six lanes share this
working tree (A3 weights_calibrate.py and A4 whatif.py do not exist yet).

Sources (the digest is the only source of truth, R-1):
  * docs/digest/M00-architecture.md L244-L305 -- the layer table (1.6.1), the
    dependency direction table (1.6.2) and INV-1/2/3 (1.6.3), quoted verbatim.
  * docs/digest/M15-modules-table.md L809-L836 -- the 23 module rows + cli.py.
  * docs/digest/M16-numeric-reasoncodes.md L851-L858 -- P-8: one enum holds every
    reason_code, bare literals in business code are forbidden, AST-scanned.
  * docs/RUN-UNATTENDED-v3.0-PARALLEL.md L264-L272 -- ruling ORCH-03: dsm/entropy.py
    sits at L1 and is the ONE implementation of SDD 2.4.2, imported by
    weights_combine (L0a) and by diagnostics (L5).

Which test guards what (the NOTES of the report line):
  INV-1   test_inv1_l1_through_l5_never_import_l0a_or_l0b  (M00 L300 verbatim)
          test_inv1_dependency_direction_follows_the_m00_table (M00 L284-L294 plus
          the L3-must-not-reach-L4 supplement of M00 L303)
  INV-2   test_inv2_l0b_output_paths_stay_in_their_own_run_id_subdir (M00 L301)
  INV-3   test_inv3_score_runtime_never_reaches_an_entropy_recompute_module
          (M00 L302, static half; the dynamic half is T-CMB-06 in package A2)
  P-8     test_p8_no_bare_reason_code_literal_in_a_reason_code_position
          test_p8_registry_name_collisions_stay_inside_the_reviewed_inventory
  H-8     test_h8_no_wall_clock_read_outside_the_single_injection_point
          test_h8_no_unseeded_random_generator
  ORCH-03 test_orch03_entropy_is_l1_and_the_only_implementation
          test_orch03_l5_never_imports_l0a_or_l0b_and_diagnostics_uses_l1_entropy

Modules that do not exist yet are covered automatically (E5 card L174 and the
note at L177): every scan is existence-gated, it walks the dsm/*.py files that
are on disk and matches them against LAYERS below. LAYERS already carries all 24
modules (M15 L809-L836 plus entropy by ORCH-03), so weights_calibrate.py (A3)
and whatif.py (A4) enter every assertion here the moment they land, with no edit
to this file; the Phase 2 full regression then covers all 24. And
test_layer_map_covers_every_module_on_disk fails loudly if a new file appears
that LAYERS does not know, so nothing can slip past the scan unmapped. Today 22
of 24 exist, so the L0b rows (INV-2, part of the direction table) are vacuous;
each such test carries a synthetic positive control, which proves the scanner
fires before the real module arrives.

Overlap, resolved in favour of this file (E5 card: repeated assertions belong to
E5): tests/test_diagnostics.py::test_inv3_l5_never_imports_l0a_or_l0b asserts the
same two facts, but scoped to diagnostics.py only. The ORCH-03 test here scans
every L5 module (sensitivity, triangulation, diagnostics) and is the
authoritative copy; the F3 one is redundant from this commit on and can be
dropped at a sync point (that file is not in the E5 write set).

--------------------------------------------------------------------------
The L0a dispute -- CLOSED by ruling ORCH-29 (EFIX-1, 主控 第 2 条裁).
Verbatim digest lines, re-read by this lane in
docs/digest/M00-architecture.md (L276, L277-L279, L282, L286, L294, L300;
the extracted lines are staged in dsm_stage/EFIX-1/ORCH-29-LINES.md):

  L276|     | L0a 离线无依赖工具（不依赖任何内部层）                           |
  L278|     |     weights_combine.py     组合权重（消费 L0a 与熵权快照）        |
  L286|     L0a → 无内部依赖（独立命令行工具）
  L294|     L0b → L1-L5（单向调用；反向禁止）
  L300| | **INV-1** | L0b 可 import L1–L5；**L1–L5 不得 import L0a / L0b** |

ORCH-29 rules: L278 says weights_combine CONSUMES A PRODUCT SNAPSHOT (the
L0a artifact and the entropy snapshot), NOT that it imports a sibling L0a
module; L276/L286 both keep L0a 不依赖任何内部层 (L282 explains only why L0
was split: L0b needs the full pipeline). Therefore:
  * ALLOWED['L0a'] is TIGHTENED from ('L0a', 'L1') to ('L1',). The
    surviving L0a -> L1 edge stands on ORCH-03 + SDD 2.4.2 L537 (熵权六步的
    两个计算者共用 dsm/entropy.py 同一实现) plus numeric.py as the single
    numeric caliber (M16 L844); INV-1 (L300) itself binds only L1-L5.
  * ALLOWED['L0b'] stays verbatim L294 (L1-L5, 单向调用；反向禁止). E5's
    proposed widening with 'L0a'/'L6' was REJECTED by 主控 -- do not
    re-add it. Tightening is an allowed action, weakening is not.
  * The two edges this tightening targets: weights_combine -> weights_ahp
    (L0a -> L0a) was removed by package A2b (41f0e13, snapshot injection)
    and weights_calibrate -> weights_combine (L0b -> L0a, verbatim L294)
    by the ruling-3 dependency-injection rework of weights_calibrate. The
    scan stays ARMED for both: re-introduce either edge and the direction
    test goes RED on the spot. The whitelist sits exactly at the ruling,
    never softer (weakening banned), never wider than the digest allows.
    whatif -> audit is GONE: A4 per ORCH-27 (9078201) injects the
    directory hash as a callable and imports zero L6 -- re-proved by the
    no-L6-edge assertion inside the direction test below.
'''
import ast
import pathlib
import re

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DSM_DIR = REPO_ROOT / 'dsm'
PACKAGE = 'dsm'

# The layer map, verbatim from M00 L246-L280 and M15 L811-L836, plus entropy at
# L1 by ruling ORCH-03 (run doc L264-L272). cli.py has no layer row (M15 L836)
# and __init__.py is the package facade: both are UNLAYERED, still scanned by
# P-8 and H-8, never a target of a layer assertion.
LAYERS = {
    'weights_ahp': 'L0a', 'weights_combine': 'L0a', 'fixtures_gen': 'L0a',
    'weights_calibrate': 'L0b', 'whatif': 'L0b',
    'numeric': 'L1', 'reason_codes': 'L1', 'models': 'L1', 'config': 'L1',
    'io_loaders': 'L1', 'entropy': 'L1',
    'preflight': 'L2',
    'attainment': 'L3', 'normalize': 'L3', 'aggregate': 'L3', 'grading': 'L3',
    'evidence': 'L4', 'redline': 'L4', 'pooling': 'L4',
    'sensitivity': 'L5', 'triangulation': 'L5', 'diagnostics': 'L5',
    'audit': 'L6', 'reports': 'L7',
}
UNLAYERED = ('__init__', 'cli')
ALL_LAYERS = ('L0a', 'L0b', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7')
L0A_L0B = ('L0a', 'L0b')
PENDING = ('weights_calibrate', 'whatif')   # A3 / A4, mapped, not on disk yet

# M00 L284-L294 (1.6.2 依赖方向，严格单向，禁止环), widened by each layer to
# itself: intra-layer imports are what M16 L844 orders (every module goes
# through numeric.py) and what M00 L278 orders for L0a, so 无内部依赖 is read as
# 不依赖其它层, never as 层内互不引用. L6 / L7 read 全部（只读）. The L0a row is
# the ORCH-29 RULING: L1 only -- L278 consumes a product snapshot, not a
# sibling module, so intra-L0a edges are forbidden; the surviving
# L0a -> L1 exception is ORCH-03 + SDD 2.4.2 L537 + M16 numeric.
ALLOWED = {
    'L0a': ('L1',),
    'L0b': ('L0b', 'L1', 'L2', 'L3', 'L4', 'L5'),
    'L1': ('L1',),
    'L2': ('L1', 'L2'),
    'L3': ('L1', 'L2', 'L3'),
    'L4': ('L1', 'L3', 'L4'),
    'L5': ('L1', 'L3', 'L4', 'L5'),
    'L6': ALL_LAYERS,
    'L7': ALL_LAYERS,
}

# ---------------------------------------------------------------------------
# Scanners. Every one of them takes source text, so the synthetic positive
# controls below run them exactly the way the real modules are run.
# ---------------------------------------------------------------------------
def _read(path):
    return path.read_text(encoding='utf-8')


def package_modules():
    '''Every dsm/*.py, the facade included: P-8 and H-8 apply to all of them.'''
    return [(path.stem, path) for path in sorted(DSM_DIR.glob('*.py'))]


def layered_modules():
    '''Every dsm/*.py that M00 puts in a layer AND that exists on disk. The
    existence gate is what makes A3 / A4 join this file without an edit.'''
    return [(stem, path) for stem, path in package_modules() if stem in LAYERS]


def _dotted(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return '.'.join(reversed(parts))


def _alias_map(tree):
    '''Bound name -> fully qualified origin, so rom datetime import datetime
    plus datetime.now() resolves to datetime.datetime.now.'''
    amap = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                amap[alias.asname or alias.name] = alias.name
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            for alias in node.names:
                amap[alias.asname or alias.name] = node.module + '.' + alias.name
    return amap


def _expand(dotted, amap):
    head, sep, tail = dotted.partition('.')
    return amap[head] + sep + tail if head in amap else dotted


def _parents(tree):
    parent = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent.setdefault(id(child), node)
    return parent


def _docstring_ids(tree):
    '''Prose is not an emitted value, so docstrings never count as literals.'''
    ids = set()
    kinds = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in ast.walk(tree):
        if isinstance(node, kinds) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                if isinstance(first.value.value, str):
                    ids.add(id(first.value))
    return ids


def _enclosing_names(tree):
    owner = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for child in ast.walk(node):
                owner.setdefault(id(child), node.name)
    return owner


def internal_imports(source):
    '''[(lineno, dotted, target_stem)] for every import edge into the dsm
    package. Relative imports resolve against the flat dsm package (it has no
    sub-packages); a bare import dsm is the facade and is no edge.'''
    edges = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            edges += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = PACKAGE + '.' + (node.module + '.' if node.module else '')
                edges += [(node.lineno, base + alias.name) for alias in node.names]
            elif node.module == PACKAGE:
                edges += [(node.lineno, PACKAGE + '.' + alias.name) for alias in node.names]
            elif node.module:
                edges.append((node.lineno, node.module))
    resolved = []
    for lineno, dotted in edges:
        parts = dotted.split('.')
        if parts[0] != PACKAGE:
            continue
        stem = next((part for part in parts[1:]
                     if part in LAYERS or part in UNLAYERED), None)
        if stem is None or stem == '__init__':
            continue
        resolved.append((lineno, dotted, stem))
    return resolved


def inv1_offenders(stem, source):
    '''M00 L300 verbatim: L1-L5 不得 import L0a / L0b. The caller picks the L1-L5
    modules; this only reports the forbidden targets.'''
    return [(stem, lineno, dotted, target, LAYERS[target])
            for lineno, dotted, target in internal_imports(source)
            if LAYERS.get(target) in L0A_L0B]


def layer_offenders(stem, source):
    '''Every import edge leaving stem whose target layer is not in ALLOWED.'''
    allowed = ALLOWED[LAYERS[stem]]
    offenders = []
    for lineno, dotted, target in internal_imports(source):
        if target == stem or target not in LAYERS:
            continue                      # self reference, or the unlayered cli
        if LAYERS[target] not in allowed:
            offenders.append((stem, LAYERS[stem], lineno, dotted, target, LAYERS[target]))
    return offenders


REASON_CODE_NAME = re.compile('reason[_]?code', re.IGNORECASE)


def registry():
    '''The reason_code registry read out of dsm/reason_codes.py with AST only
    (M16 L855: one enum, no literal anywhere else). Returns (codes, prefixes);
    prefixes are the per-metric REDLINE_HARD_ / REDLINE_SOFT_ families of
    M16 L856, which resolve to a registered template at runtime.'''
    codes, prefixes = set(), set()
    for node in ast.walk(ast.parse(_read(DSM_DIR / 'reason_codes.py'))):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, (ast.Tuple, ast.List)):
            continue
        names = {target.id for target in node.targets if isinstance(target, ast.Name)}
        for row in node.value.elts:
            if not isinstance(row, (ast.Tuple, ast.List)) or not row.elts:
                continue
            head = row.elts[0]
            if not (isinstance(head, ast.Constant) and isinstance(head.value, str)):
                continue
            if '_DEFS' in names:
                codes.add(head.value)
            if '_DYNAMIC_PREFIXES' in names:
                prefixes.add(head.value)
    return codes, tuple(sorted(prefixes))


def _is_registry_code(text, codes, prefixes):
    return text in codes or any(text.startswith(prefix) for prefix in prefixes)


def _reason_code_position(node, parent):
    '''Why this literal sits in a reason_code position, or None. A position is a
    binding whose own name says reason_code (keyword argument, dict key,
    assignment target), a comparison against RC.* or a reason_code named value,
    or an element of a container that is itself in such a position. Anything else
    is a name collision with another closed string domain (StabilityLabel,
    FrameGrade, EntropyStatus, MethodAgreement of models.py) and is inventoried by
    the ratchet test instead of being guessed at here.'''
    par = parent.get(id(node))
    if par is None:
        return None
    if isinstance(par, ast.keyword) and REASON_CODE_NAME.search(par.arg or ''):
        return 'keyword argument ' + str(par.arg)
    if isinstance(par, ast.Dict):
        for key, value in zip(par.keys, par.values):
            if value is node and isinstance(key, ast.Constant):
                if isinstance(key.value, str) and REASON_CODE_NAME.search(key.value):
                    return 'value of the dict key ' + key.value
    if isinstance(par, (ast.Assign, ast.AnnAssign)):
        targets = par.targets if isinstance(par, ast.Assign) else [par.target]
        for target in targets:
            name = target.id if isinstance(target, ast.Name) else getattr(target, 'attr', '')
            if REASON_CODE_NAME.search(name or ''):
                return 'assigned to ' + name
    if isinstance(par, ast.Compare):
        for other in [par.left] + list(par.comparators):
            if other is node:
                continue
            dotted = _dotted(other)
            if REASON_CODE_NAME.search(dotted) or dotted.split('.')[0] == 'RC':
                return 'compared against ' + dotted
    if isinstance(par, (ast.Tuple, ast.List, ast.Set)):
        return _reason_code_position(par, parent)
    return None


def reason_code_literals(source, codes, prefixes):
    '''(hard hits, every collision) for one module source.'''
    tree = ast.parse(source)
    skip = _docstring_ids(tree)
    parent = _parents(tree)
    hard, collisions = [], set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in skip or not _is_registry_code(node.value, codes, prefixes):
            continue
        collisions.add(node.value)
        position = _reason_code_position(node, parent)
        if position:
            hard.append((node.lineno, node.value, position))
    return hard, collisions


# H-8: the clock is injected, never read. dsm/cli.py L69-L72 keeps the one legal
# read inside _now(), reached only when --run-at was omitted; every lower layer is
# clock-free (dsm/redline.py L38, dsm/audit.py L20, dsm/entropy.py L14).
CLOCK_CALLS = frozenset({
    'time.time', 'time.time_ns', 'time.monotonic', 'time.monotonic_ns',
    'time.perf_counter', 'time.perf_counter_ns', 'time.localtime', 'time.gmtime',
    'time.strftime', 'time.clock_gettime', 'datetime.datetime.now',
    'datetime.datetime.utcnow', 'datetime.datetime.today', 'datetime.date.today',
    'uuid.uuid1', 'os.urandom',
})
CLOCK_INJECTION_POINT = ('cli', '_now')
RANDOM_ROOTS = ('random.', 'numpy.random.')
# A generator is legal only when it is constructed with a seed (M15 L800: MC 必须
# 固定 seed; dsm/sensitivity.py L291 numpy.random.default_rng(int(base.seed)),
# dsm/fixtures_gen.py L359 random.Random(seed)). random.SystemRandom and
# os.urandom are deliberately absent: OS entropy is not reproducible.
SEEDED_CONSTRUCTORS = frozenset({
    'random.Random', 'random.seed', 'numpy.random.default_rng',
    'numpy.random.Generator', 'numpy.random.PCG64', 'numpy.random.MT19937',
    'numpy.random.Philox', 'numpy.random.SFC64', 'numpy.random.SeedSequence',
    'numpy.random.seed', 'numpy.random.RandomState',
})


def clock_hits(source):
    tree = ast.parse(source)
    amap, owner = _alias_map(tree), _enclosing_names(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        path = _expand(_dotted(node.func), amap)
        if path in CLOCK_CALLS:
            hits.append((node.lineno, path, owner.get(id(node), '<module level>')))
    return hits


def random_hits(source):
    tree = ast.parse(source)
    amap, owner = _alias_map(tree), _enclosing_names(tree)
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        path = _expand(_dotted(node.func), amap)
        if not path.startswith(RANDOM_ROOTS):
            continue
        seeded = bool(node.keywords) or any(
            not (isinstance(arg, ast.Constant) and arg.value is None) for arg in node.args)
        if path in SEEDED_CONSTRUCTORS and seeded:
            continue
        kind = 'unseeded generator constructor' if path in SEEDED_CONSTRUCTORS else 'global rng call'
        hits.append((node.lineno, path, kind, owner.get(id(node), '<module level>')))
    return hits


# INV-2 (M00 L301): L0b 的运行不得写生产输出目录；reports/ 下按 whatif/ 与
# calibrate/ 独立子目录，文件名含 run_id. Only literals that carry a path
# separator are judged, and only in a write context: a bare file name is scoped by
# the join around it, which no static scan can resolve.
L0B_GROUP = {'weights_calibrate': 'calibrate', 'whatif': 'whatif'}
PRODUCTION_ROOT = 'reports'
WRITE_LEAVES = frozenset({'write_text', 'write_bytes', 'open', 'mkdir', 'makedirs',
                          'touch', 'to_csv', 'to_parquet', 'to_json', 'dump',
                          'save', 'savez', 'rename', 'replace', 'copy', 'copyfile'})
PATH_SUFFIXES = ('.md', '.csv', '.json', '.jsonl', '.parquet', '.txt', '.yaml', '.yml')
OUT_NAME_HINTS = ('out', 'path', 'dir', 'file', 'dest', 'target')


def _is_path_literal(text):
    if not text or len(text) > 120 or any(char.isspace() for char in text):
        return False
    return '/' in text or text.endswith(PATH_SUFFIXES)


def _scoped_to_group(text, group):
    parts = [part for part in text.split('/') if part not in ('', '.')]
    if not parts:
        return True
    if parts[0] == PRODUCTION_ROOT:
        return len(parts) > 1 and parts[1] == group
    return parts[0] == group


def _write_context(node, parent):
    current = node
    while current is not None:
        par = parent.get(id(current))
        if par is None:
            return False
        if isinstance(par, ast.Call) and _dotted(par.func).split('.')[-1] in WRITE_LEAVES:
            return True
        if isinstance(par, (ast.Assign, ast.AnnAssign)):
            targets = par.targets if isinstance(par, ast.Assign) else [par.target]
            for target in targets:
                name = target.id if isinstance(target, ast.Name) else getattr(target, 'attr', '')
                if any(hint in (name or '').lower() for hint in OUT_NAME_HINTS):
                    return True
            return False
        current = par
    return False


def l0b_output_offenders(stem, source):
    group = L0B_GROUP[stem]
    tree = ast.parse(source)
    skip, parent = _docstring_ids(tree), _parents(tree)
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value
        if id(node) in skip or not _is_path_literal(text) or '/' not in text:
            continue
        if _write_context(node, parent) and not _scoped_to_group(text, group):
            offenders.append((node.lineno, text, 'not under ' + group + '/'))
    writes = any(_dotted(node.func).split('.')[-1] in WRITE_LEAVES
                 for node in ast.walk(tree) if isinstance(node, ast.Call))
    if writes and 'run_id' not in source:
        offenders.append((0, '<module>', 'writes but never names run_id (M00 L301)'))
    return offenders


# INV-3 (M00 L302): 评分运行时（dsm score）不得触发任何熵权重算；权重只从 FROZEN
# 配置读取. The score path is the chain cli.py L34-L36 loads (attainment,
# normalize, aggregate, grading, evidence, redline, pooling, triangulation,
# sensitivity, audit, reports) plus the L1 contracts and the L2 gate. Outside it
# stay the shell itself (cli dispatches to L0a/L0b by design), the two entropy
# computers and the offline tools.
SCORE_RUNTIME = ('numeric', 'reason_codes', 'models', 'config', 'io_loaders',
                 'preflight', 'attainment', 'normalize', 'aggregate', 'grading',
                 'evidence', 'redline', 'pooling', 'sensitivity', 'triangulation',
                 'audit', 'reports')
ENTROPY_RECOMPUTE = ('entropy', 'diagnostics')
OFFLINE_TOOLS = ('weights_ahp', 'weights_combine', 'fixtures_gen',
                 'weights_calibrate', 'whatif')
FORBIDDEN_AT_SCORE_TIME = ENTROPY_RECOMPUTE + OFFLINE_TOOLS


def score_runtime_offenders(stem, source):
    '''Import edges and lazy import-by-name strings: cli.py resolves its
    dependencies through importlib, so a dotted string is an edge too.'''
    offenders = [(stem, lineno, dotted, 'import')
                 for lineno, dotted, target in internal_imports(source)
                 if target in FORBIDDEN_AT_SCORE_TIME]
    lazy = {PACKAGE + '.' + name for name in FORBIDDEN_AT_SCORE_TIME}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value in lazy:
                offenders.append((stem, node.lineno, node.value, 'lazy import by name'))
    return offenders

# ---------------------------------------------------------------------------
# Synthetic sources for the positive controls. A guard that can not fail is not a
# guard, so every scanner is proven to fire on these before the real modules --
# or, for INV-2, before A3 / A4 exist at all.
# ---------------------------------------------------------------------------
SYN_L3_IMPORTS_L0A = '''from dsm.weights_combine import combine
'''
SYN_L3_IMPORTS_L4 = '''from dsm.redline import apply_redline
'''
SYN_L0A_IMPORTS_L0B = '''from dsm.whatif import preview
'''
SYN_L5_IMPORTS_L0B = '''import dsm.weights_calibrate
'''
SYN_SCORE_IMPORTS_ENTROPY = '''from dsm.entropy import entropy_weights
'''
SYN_SCORE_LAZY_DIAGNOSTICS = '''import importlib
mod = importlib.import_module('dsm.diagnostics')
'''
SYN_L0B_WRITES_PRODUCTION = '''OUT = 'reports/2026-10/score_card.md'
open(OUT, 'w')
'''
SYN_L0B_SCOPED = '''OUT = 'reports/whatif/{run_id}/whatif.md'
open(OUT, 'w')
'''
SYN_CLOCK_READ = '''import datetime
def stamp():
    return datetime.datetime.now()
'''
SYN_UNSEEDED_RANDOM = '''import random
def pick(rows):
    return random.choice(rows)
'''
SYN_UNSEEDED_GENERATOR = '''import numpy
def draw():
    return numpy.random.default_rng().random(3)
'''
SYN_SEEDED_RANDOM = '''import random
def pick(seed, rows):
    rng = random.Random(seed)
    return rng.choice(rows)
'''
SYN_BARE_REASON_CODE = '''row = {'reason_code': 'MONEY_NON_INTEGER'}
'''

# Reviewed 2026-11-25 at commit 5d13ef3, 28 (module, literal) pairs. P2-wire-B
# shrank 32 -> 28 (ORCH-34 ruling 3, scheduled after A1c): the four fixtures_gen
# pairs -- MONEY_NON_INTEGER, REDLINE_HARD_M_COMPLAINT_RATE,
# REDLINE_HARD_M_CONTACT_FREQ_PER_30D, REDLINE_SOFT_M_OPTOUT_RATE -- were
# re-measured against the live scanner (fresh collisions 0, stale allowances 4)
# and no longer occur, because A1b @0547190 moved all four to registry symbols:
# fixtures_gen.py:537 RC.MONEY_NON_INTEGER.value, :360/:363 redline_hard(...),
# :366 redline_soft(...). A stale allowance is a HOLE in the ratchet -- it would
# let fixtures_gen hand-spell those four codes again without tripping anything --
# so dropping them tightens the gate. The direction is unchanged and now pinned
# numerically by COLLISION_INVENTORY_CEILING below: the inventory may only shrink.
# These are
# bare literals that equal a registered reason_code but do NOT sit in a
# reason_code position, so the P-8 test above does not fail on them. Three
# groups, and the ratchet below is what keeps the list from growing:
#   1. type domains of models.py: Literal['STABLE', 'NEAR_BOUNDARY', 'UNSTABLE']
#      and friends declare the closed domain of a *different* field
#      (StabilityLabel, FrameGrade, EntropyStatus, MethodAgreement, M17/M19);
#      the registry happens to carry the same spelling because the report also
#      emits those values as flags.
#   2. module level domain constants that collide by name: grading.NOT_ASSESSED,
#      pooling.NOT_ASSESSED, sensitivity._NOT_ASSESSED, diagnostics status
#      literals, the cli exit-status names, and the preflight DISCLOSURE value
#      at L48 (that one reads like a placeholder for a real disclosure
#      location -- worth a look by C2's owner, filed in GAPS-E5.md).
#   3. hand-spelled reason codes that are NOT in a reason_code position and
#      should move to RC.*: sensitivity._FLAG_ORDER (L61-L62, five codes) and
#      reports.STABILITY_LABELS / the tag tuple at L253. Filed in GAPS-E5.md;
#      not failed here because the same literal is a StabilityLabel elsewhere,
#      so a blanket rule would punish the wrong modules.
# Only 主控 may grow this inventory (R-15: reason_codes.py and the contract layer
# are single-point), and growing it needs a written reason.
COLLISION_INVENTORY = {
    'cli': frozenset({'ALPHA_INFEASIBLE'}),
    'diagnostics': frozenset({'COLLINEAR', 'LOW_VARIATION'}),
    'grading': frozenset({'NOT_ASSESSED'}),
    'models': frozenset({'COLLINEAR', 'LOW_VARIATION', 'METHOD_AGREEMENT',
                         'METHOD_DIVERGENCE', 'NEAR_BOUNDARY', 'NOT_ASSESSED',
                         'STABLE', 'UNSTABLE'}),
    'pooling': frozenset({'NOT_ASSESSED'}),
    'preflight': frozenset({'WEIGHT_REALLOCATED'}),
    'reports': frozenset({'METHOD_DIVERGENCE', 'NEAR_BOUNDARY', 'NOT_ASSESSED',
                          'STABLE', 'UNSTABLE'}),
    'sensitivity': frozenset({'DOMINANT_METRIC', 'FLIP_RATE_REVIEW',
                              'FLIP_RATE_UNUSABLE', 'LOO_SAMPLED', 'NEAR_BOUNDARY',
                              'NORMALIZATION_SENSITIVE', 'NOT_ASSESSED', 'STABLE',
                              'UNSTABLE'}),
}

# P2-wire-B ratchet cap, measured 28 pairs at 5d13ef3 (the reviewed inventory held
# 32 at 3fef4da; the four fixtures_gen pairs above went stale at A1b @0547190). The
# guard test fails on ANY growth past this number, so shrinking is the only
# unattended direction left and growing the inventory needs 主控 to raise the cap
# with a written reason (R-15: reason_codes.py and the contract layer are
# single-point; R-14: a ratchet may only tighten).
COLLISION_INVENTORY_CEILING = 28


def test_layer_map_covers_every_module_on_disk():
    '''The auto-inclusion mechanism itself: no dsm/*.py may escape the scans by
    being unknown here, the two modules still in flight stay pre-mapped, and the
    layer map agrees with the facade docstring that 主控 keeps (dsm/__init__.py
    L3-L16, ORCH-03 added entropy to the L1 row).'''
    on_disk = {path.stem for path in sorted(DSM_DIR.glob('*.py'))}
    unknown = sorted(on_disk - set(LAYERS) - set(UNLAYERED))
    assert not unknown, (
        'unmapped module(s) ' + repr(unknown) + ': add them to LAYERS with the '
        'layer M00 L246-L280 / M15 L811-L836 gives them, otherwise every '
        'architecture scan in this file silently skips them')
    assert set(PENDING) <= set(LAYERS), 'A3 / A4 must stay pre-mapped'
    assert {LAYERS[stem] for stem in PENDING} == {'L0b'}
    missing = sorted(stem for stem in PENDING if not (DSM_DIR / (stem + '.py')).is_file())
    facade = {}
    for line in _read(DSM_DIR / '__init__.py').splitlines():
        tokens = [token for token in line.split('(')[0].split() if token != '/']
        if tokens and tokens[0] in ALL_LAYERS:
            facade[tokens[0]] = set(tokens[1:])
    mine = {}
    for stem, layer in LAYERS.items():
        mine.setdefault(layer, set()).add(stem)
    assert facade == mine, (
        'dsm/__init__.py layer table and LAYERS disagree; not on disk yet: '
        + repr(missing) + '; facade=' + repr(facade) + ' map=' + repr(mine))


def test_inv1_l1_through_l5_never_import_l0a_or_l0b():
    '''INV-1, M00 L300 verbatim: L0b 可 import L1-L5；L1-L5 不得 import L0a / L0b.
    Scanned over every L1-L5 module that exists; weights_calibrate.py and whatif.py
    are L0b, so they are the importing side of this rule, never the target.'''
    offenders, scanned = [], []
    for stem, path in layered_modules():
        if LAYERS[stem] not in ('L1', 'L2', 'L3', 'L4', 'L5'):
            continue
        scanned.append(stem)
        offenders += inv1_offenders(stem, _read(path))
    assert not offenders, 'INV-1 violation (M00 L300): ' + repr(offenders)
    assert len(scanned) >= 15, 'the INV-1 scan saw only ' + repr(scanned)
    assert inv1_offenders('aggregate', SYN_L3_IMPORTS_L0A), 'INV-1 scanner is vacuous'


def test_inv1_dependency_direction_follows_the_m00_table():
    '''M00 L284-L294 (1.6.2 依赖方向，严格单向，禁止环) plus the supplement at
    L303 (L3 计算层不得引用 L4 门禁层). One edge matrix over every mapped module
    on disk; the L0a row is the ORCH-29 ruling argued in the module
    docstring (tightened; weakening the whitelist to go green is banned).
    Both edges the tightening targeted were removed before this run
    (A2b 41f0e13 killed weights_combine -> weights_ahp; ruling 3 DI
    killed weights_calibrate -> weights_combine); the scan stays armed.
    whatif must show NO L0/L6 edge (A4 / ORCH-27, 9078201).'''
    whatif_path = DSM_DIR / 'whatif.py'
    if whatif_path.is_file():
        l0_l6_edges = [(lineno, dotted, target)
                       for lineno, dotted, target in
                       internal_imports(_read(whatif_path))
                       if LAYERS.get(target) in L0A_L0B + ('L6',)]
        assert not l0_l6_edges, (
            'A4 (ORCH-27) removed the whatif -> audit edge; it must '
            'stay gone (L0b -> L1-L5 only, M00 L294): ' + repr(l0_l6_edges))
    offenders, scanned = [], []
    for stem, path in layered_modules():
        scanned.append(stem)
        offenders += layer_offenders(stem, _read(path))
    assert not offenders, (
        'dependency direction violation (M00 L284-L294 / L303), rows are '
        '(module, layer, lineno, import, target, target layer): ' + repr(offenders))
    assert len(scanned) >= 20, 'the edge scan saw only ' + repr(scanned)
    assert layer_offenders('weights_combine', SYN_L0A_IMPORTS_L0B), 'L0a -> L0b must fail'
    assert layer_offenders('aggregate', SYN_L3_IMPORTS_L4), 'L3 -> L4 must fail'


def test_inv2_l0b_output_paths_stay_in_their_own_run_id_subdir():
    '''INV-2, M00 L301 verbatim: L0b 的运行不得写生产输出目录；reports/ 下按
    whatif/ 与 calibrate/ 独立子目录，文件名含 run_id. Static half: every
    multi-segment path literal an L0b module writes must sit under its own group
    directory, and a module that writes at all must name run_id. The behavioural
    half (目录哈希比对自证, A4 card) belongs to T-CAL-* / T-WIF-*. Vacuous until
    A3 / A4 land, hence the two controls.'''
    offenders, scanned = [], []
    for stem, path in layered_modules():
        if LAYERS[stem] != 'L0b':
            continue
        scanned.append(stem)
        offenders += [(stem,) + row for row in l0b_output_offenders(stem, _read(path))]
    assert not offenders, 'INV-2 violation (M00 L301): ' + repr(offenders)
    assert l0b_output_offenders('whatif', SYN_L0B_WRITES_PRODUCTION), 'INV-2 scanner is vacuous'
    assert not l0b_output_offenders('whatif', SYN_L0B_SCOPED), 'INV-2 scanner rejects a legal path'
    assert sorted(scanned) == sorted(
        stem for stem in PENDING if (DSM_DIR / (stem + '.py')).is_file())


def test_inv3_score_runtime_never_reaches_an_entropy_recompute_module():
    '''INV-3, M00 L302 verbatim: 评分运行时（dsm score）不得触发任何熵权重算；
    权重只从 FROZEN 配置读取. Static half: no module on the score path may reach
    entropy.py or diagnostics.py (the two entropy computers, ORCH-03) nor any
    offline tool, by import or by an importlib string. The dynamic half is
    T-CMB-06 (mock the entropy function, score must never call it) in package A2.'''
    offenders, scanned = [], []
    for stem in SCORE_RUNTIME:
        path = DSM_DIR / (stem + '.py')
        if not path.is_file():
            continue
        scanned.append(stem)
        offenders += score_runtime_offenders(stem, _read(path))
    assert not offenders, 'INV-3 violation (M00 L302): ' + repr(offenders)
    assert len(scanned) >= 15, 'the score-path scan saw only ' + repr(scanned)
    assert score_runtime_offenders('aggregate', SYN_SCORE_IMPORTS_ENTROPY)
    assert score_runtime_offenders('aggregate', SYN_SCORE_LAZY_DIAGNOSTICS)
    assert score_runtime_offenders('aggregate', SYN_L3_IMPORTS_L0A)


def test_p8_no_bare_reason_code_literal_in_a_reason_code_position():
    '''P-8, M16 L855 verbatim: 用枚举集中定义全部 reason_code，禁止在业务代码里
    写字面量字符串（P-8 用 AST 扫描守护）. Scope per the E5 card: dsm/** minus
    reason_codes.py itself. A literal fails when it spells a registered code (or a
    REDLINE_HARD_ / REDLINE_SOFT_ per-metric code) and sits in a reason_code
    position; RC.<NAME>.value and reason_codes.redline_hard(...) are the only
    legal spellings.'''
    codes, prefixes = registry()
    assert len(codes) >= 70 and prefixes, 'the registry was not parsed: ' + repr(
        (len(codes), prefixes))
    offenders = []
    for stem, path in package_modules():
        if stem == 'reason_codes':
            continue
        hard, _ = reason_code_literals(_read(path), codes, prefixes)
        offenders += [(stem, lineno, value, why) for lineno, value, why in hard]
    assert not offenders, (
        'P-8 violation (M16 L855), bare reason_code literal in a reason_code '
        'position, use RC.<NAME>.value / reason_codes.redline_hard(): ' + repr(offenders))
    assert reason_code_literals(SYN_BARE_REASON_CODE, codes, prefixes)[0], 'P-8 scanner is vacuous'


def test_p8_registry_name_collisions_stay_inside_the_reviewed_inventory():
    '''The ratchet behind P-8: a bare literal that equals a registered code but
    sits outside a reason_code position is tolerated only where it is already
    reviewed (COLLISION_INVENTORY). A new module starts with an empty allowance,
    so A3 / A4 must reference RC.* from day one, and no delivered module may add
    a new hand-spelled code without 主控 triage.'''
    codes, prefixes = registry()
    fresh = []
    for stem, path in package_modules():
        if stem == 'reason_codes':
            continue
        _, collisions = reason_code_literals(_read(path), codes, prefixes)
        allowed = COLLISION_INVENTORY.get(stem, frozenset())
        fresh += [(stem, value) for value in sorted(collisions - allowed)]
    assert not fresh, (
        'new bare literal equal to a registered reason_code (M16 L855): use '
        'RC.<NAME>.value, or 主控 adds it to COLLISION_INVENTORY with a reason: '
        + repr(fresh))
    pairs = sum(len(literals) for literals in COLLISION_INVENTORY.values())
    assert pairs <= COLLISION_INVENTORY_CEILING, (
        'COLLISION_INVENTORY holds ' + repr(pairs) + ' (module, literal) pairs, the '
        'reviewed cap is ' + repr(COLLISION_INVENTORY_CEILING) + ': this ratchet only '
        'shrinks, 主控 must raise the cap with a written reason (R-15, M16 L855)')
    hard_control, collisions_control = reason_code_literals(SYN_BARE_REASON_CODE, codes, prefixes)
    assert hard_control and 'MONEY_NON_INTEGER' in collisions_control, 'control is vacuous'
    assert 'MONEY_NON_INTEGER' not in COLLISION_INVENTORY.get('whatif', frozenset()), (
        'a module that does not exist yet must start with an empty allowance')


def test_h8_no_wall_clock_read_outside_the_single_injection_point():
    '''H-8: no module reads a clock except the single injection point _now() of
    dsm/cli.py (cli.py L16 and L69-L72: --run-at injects the clock, _now() is the
    single clock point of the whole program). run_at / run_id travel as arguments
    from there (preflight.py L54-L56, audit.py L20, redline.py L38).'''
    offenders, injected = [], []
    for stem, path in package_modules():
        for lineno, dotted, owner in clock_hits(_read(path)):
            if (stem, owner) == CLOCK_INJECTION_POINT:
                injected.append((stem, lineno, dotted, owner))
            else:
                offenders.append((stem, lineno, dotted, owner))
    assert not offenders, (
        'H-8 violation, wall-clock read outside dsm/cli.py _now(): ' + repr(offenders))
    assert len(injected) <= 1, 'H-8 单点注入 broken, clock reads: ' + repr(injected)
    assert clock_hits(SYN_CLOCK_READ), 'H-8 clock scanner is vacuous'


def test_h8_no_unseeded_random_generator():
    '''H-8: randomness is seeded at one injected point (M15 L800: MC 必须固定 seed
    并写入 audit_bundle). Legal: random.Random(seed), numpy.random.default_rng(seed)
    and the other seeded constructors, as in sensitivity.py L291 and
    fixtures_gen.py L359. Illegal: any global rng call (random.choice,
    numpy.random.rand, ...) and any generator constructed without a seed, plus
    random.SystemRandom / os.urandom, which are not reproducible at all.'''
    offenders = []
    for stem, path in package_modules():
        offenders += [(stem,) + row for row in random_hits(_read(path))]
    assert not offenders, 'H-8 violation, unseeded randomness: ' + repr(offenders)
    assert random_hits(SYN_UNSEEDED_RANDOM), 'H-8 random scanner is vacuous'
    assert random_hits(SYN_UNSEEDED_GENERATOR), 'H-8 unseeded default_rng passes'
    assert not random_hits(SYN_SEEDED_RANDOM), 'H-8 scanner rejects a seeded rng'


def test_orch03_entropy_is_l1_and_the_only_implementation():
    '''ORCH-03 (run doc L264-L272): dsm/entropy.py is L1 and holds the ONE
    implementation of the SDD 2.4.2 six steps; weights_combine (L0a) and
    diagnostics (L5) import it. Guarded four ways: the file exists at L1, the
    facade docstring carries it at L1, entropy.py itself obeys the L1 row of the
    direction table, no other module defines an entropy-weight callable, and
    every caller of entropy_weights imports dsm.entropy.'''
    path = DSM_DIR / 'entropy.py'
    assert path.is_file(), 'ORCH-03: dsm/entropy.py is missing'
    assert LAYERS['entropy'] == 'L1'
    assert not layer_offenders('entropy', _read(path)), 'ORCH-03: entropy.py left L1'
    rows = [line for line in _read(DSM_DIR / '__init__.py').splitlines()
            if line.split() and line.split()[0] == 'L1']
    assert rows and 'entropy' in rows[0], 'ORCH-03 not broadcast into the facade L1 row'
    definitions, callers = [], []
    for stem, module in package_modules():
        source = _read(module)
        tree = ast.parse(source)
        if stem != 'entropy':
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    low = node.name.lower()
                    if 'entropy' in low and 'weight' in low:
                        definitions.append((stem, node.lineno, node.name))
        calls = [_dotted(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        if any(call.split('.')[-1] == 'entropy_weights' for call in calls):
            callers.append(stem)
            imported = {dotted for _, dotted, _ in internal_imports(source)}
            assert any(dotted == 'dsm.entropy' or dotted.startswith('dsm.entropy.')
                       for dotted in imported), (
                stem + '.py calls entropy_weights without importing dsm.entropy '
                '(ORCH-03: the L1 implementation is the only one)')
    assert not definitions, 'second entropy-weight implementation: ' + repr(definitions)
    assert set(callers) == {'diagnostics', 'weights_combine'}, (
        'ORCH-03 consumers changed: ' + repr(sorted(callers)))


def test_orch03_l5_never_imports_l0a_or_l0b_and_diagnostics_uses_l1_entropy():
    '''The repo-wide copy of the F3 assertion, and the authoritative one: no L5
    module (sensitivity, triangulation, diagnostics) imports L0a or L0b, and
    diagnostics imports the L1 entropy implementation.
    tests/test_diagnostics.py::test_inv3_l5_never_imports_l0a_or_l0b checks the
    same two facts for diagnostics.py only; per the E5 card the repeated
    assertion is maintained here.'''
    offenders, entropy_consumers, scanned = [], [], []
    for stem, path in layered_modules():
        if LAYERS[stem] != 'L5':
            continue
        scanned.append(stem)
        source = _read(path)
        offenders += inv1_offenders(stem, source)
        if any(target == 'entropy' for _, _, target in internal_imports(source)):
            entropy_consumers.append(stem)
    assert not offenders, 'ORCH-03 / INV-1 violation in L5 (M00 L300): ' + repr(offenders)
    assert inv1_offenders('diagnostics', SYN_L5_IMPORTS_L0B), 'L5 scanner is vacuous'
    assert set(scanned) == {'sensitivity', 'triangulation', 'diagnostics'}, repr(scanned)
    assert 'diagnostics' in entropy_consumers, (
        'ORCH-03: diagnostics.py must import dsm.entropy (L1), consumers seen: '
        + repr(entropy_consumers))
