'''DSM command line -- [L1076]-[L1092] eight subcommands, exit codes, run
directories (D5, L7 shell).
INV-2 (M00 L301): the shell calls lower layers, never reimplements them. Every
dsm dependency is resolved lazily through _import_dep inside command bodies, so
this package lands before pooling / weights_calibrate / whatif / triangulation
exist; a missing one is an explicit ModuleMissingError (exit 5, module named),
never a traceback nor a silent degradation (V-14).
Exit codes [L1080]-[L1087]: 0 OK / 2 preflight BLOCK / 3 config / 4 data /
5 internal invariant ([L1081]) / 6 ConsistencyFailed / 7 AlphaInfeasible.
Usage errors exit 3: argparse's native 2 would masquerade as BLOCK [L1080].
Directories [L1091] [L1550]: production <out>/<period>/<run_id>/; L0b ONLY
<out>/calibrate/<run_id>/ and <out>/whatif/<run_id>/, run_id also in the file
name [L301]; reruns get a fresh directory, never overwrite; a non-zero exit
produces no score card but leaves an audit_bundle. V-10: offline single
machine -- no network/db/scheduler import (AST-scanned by the tests). --run-at
injects the clock; _now() is the single clock point of the whole program.
'''
import argparse
import datetime
import hashlib
import importlib
import json
import sys
from pathlib import Path
import dsm  # version constants only; no algorithm import
EXIT_OK, EXIT_BLOCK, EXIT_CONFIG, EXIT_DATA = 0, 2, 3, 4
EXIT_INTERNAL, EXIT_CONSISTENCY, EXIT_ALPHA = 5, 6, 7
_CODE_STATUS = {0: 'OK', 2: 'BLOCK', 3: 'CONFIG', 4: 'DATA', 5: 'INTERNAL',
                6: 'CONSISTENCY_FAILED', 7: 'ALPHA_INFEASIBLE'}
PLACEHOLDER = 'PLACEHOLDER'  # [L878] spelling; unsigned values never invented
DEFAULT_OUT = 'reports'
PERIOD_COMMANDS = ('preflight', 'score', 'sensitivity', 'whatif')
_CHAIN_MODULES = ('dsm.attainment', 'dsm.normalize', 'dsm.aggregate', 'dsm.grading',
                  'dsm.evidence', 'dsm.redline', 'dsm.pooling', 'dsm.triangulation',
                  'dsm.sensitivity', 'dsm.audit', 'dsm.reports')
_L0B_GROUPS = ('calibrate', 'whatif')  # INV-2: the only L0b output groups
# M20 L881 / M42 L1070-1073 exception -> code, matched by class name so the map
# already holds for modules landing after this shell. exit_code_for walks
# type(exc).__mro__ OUTER FIRST, so a subclass entry always wins over the entry of
# its family base, whatever the order inside this tuple is.
# The three families of M27 [L1084]-[L1086] (calibrate 0/3/7, combine build 0/3,
# whatif 0/3/4) are now spelled out class by class. No code is invented: 3 = the
# signed configuration is absent / placeholder / inconsistent (dsm/config.py:71),
# 4 = an upstream io_loaders carrier is absent or mistyped (M21 L892, ORCH-34
# ruling 1), 5 = [L1081] internal invariant violation i.e. a program defect,
# 6 = [L1083] CR gate of "dsm ahp build", 7 = [L1084] empty feasible alpha set.
# NOT listed on purpose: weights_combine.EntropyInsufficientSample. M42 L1071 and
# the class docstring both say run_six_steps catches it and degrades to alpha = 1
# with a prominent label, so it never reaches this shell and the digest gives it no
# exit-code slot of its own. Keeping the documented [L1081] fallback is honest;
# inventing a slot for it would not be (R-12, P2PREP P-2 stays open).
_EXCEPTION_CODES = (('ConfigPlaceholderError', EXIT_CONFIG), ('ConfigSemanticError', 3),
                    ('WeightVersionInvalidError', 3), ('MatrixNotReciprocalError', 3),
                    ('FrozenStatusError', 3), ('ValidationError', 3),
                    ('DataLoadError', EXIT_DATA), ('CoercionError', 4),
                    ('ConsistencyFailedError', EXIT_CONSISTENCY),
                    ('AlphaInfeasibleError', EXIT_ALPHA),
                    ('AlphaFloorInfeasibleError', EXIT_ALPHA),
                    # dsm/whatif.py:97-151 -- M27 [L1086] whatif = 0 / 3 / 4. Each code
                    # follows the registered reason_code the class itself carries: a
                    # config / weights-document violation is 3, a missing or mistyped
                    # upstream Step 1-4 carrier is 4, and the three self-proof failures
                    # the docstrings call a program defect are [L1081] 5.
                    ('WhatifError', EXIT_INTERNAL),
                    ('WhatifRunIdError', EXIT_CONFIG),
                    ('WhatifBaselineError', EXIT_CONFIG),
                    ('WhatifInputError', EXIT_DATA),
                    ('WhatifPlaceholderError', EXIT_CONFIG),
                    ('WhatifStructureError', EXIT_CONFIG),
                    ('WhatifOperatorError', EXIT_CONFIG),
                    ('WhatifAttributionError', EXIT_INTERNAL),
                    ('WhatifConsistencyError', EXIT_INTERNAL),
                    ('WhatifReadonlyError', EXIT_INTERNAL),
                    # dsm/weights_calibrate.py:126-181 -- M27 [L1084] calibrate = 0/3/7.
                    # AlphaInfeasibleError / AlphaFloorInfeasibleError already sit above
                    # at 7 (M42 L1072); the grid / window / budget guards all read the
                    # signed config, so they are 3, and the two machine guards (P-13
                    # budget tamper, missing L0a hook) are [L1081] 5.
                    ('CalibrateError', EXIT_INTERNAL),
                    ('GridError', EXIT_CONFIG),
                    ('WindowError', EXIT_CONFIG),
                    ('MissingBudgetError', EXIT_CONFIG),
                    ('GovernanceBudgetTamperError', EXIT_INTERNAL),
                    ('HookRequiredError', EXIT_INTERNAL),
                    # dsm/weights_combine.py:80-112 -- M27 [L1085] combine build = 0 / 3.
                    # FrozenStatusError already sits above at 3 (M42 L1070). [L1083]
                    # gives exit 6 to "dsm ahp build" ONLY, so the CR gate that
                    # terminates Step 1 of a combine run takes the [L1080] config slot.
                    ('CombineError', EXIT_INTERNAL),
                    ('AlphaFloorError', EXIT_CONFIG),
                    ('ConsistencyGateError', EXIT_CONFIG),
                    ('AhpInputError', EXIT_CONFIG))
# [L1051] items 1-16 (ruling 14): fixed audit_bundle manifest keys.
_BUNDLE_KEYS = ('run_id', 'run_at', 'period', 'dsm_version', 'design_version',
                'cel_contract_version', 'weight_version_id', 'config_snapshot_sha256',
                'input_fingerprints', 'output_fingerprints', 'sensitivity_schemes',
                'seed', 'preflight_findings', 'downgrade_actions', 'exit_code',
                'reproducibility_hash')

class CliError(Exception):
    exit_code = EXIT_INTERNAL
    def __init__(self, message, exit_code=None):
        if exit_code is not None:
            self.exit_code = exit_code
        super().__init__(message)

class CliUsage(CliError):
    exit_code = EXIT_CONFIG  # [L1080] "3 config error" is the parameter slot

class ModuleMissingError(CliError):
    exit_code = EXIT_INTERNAL

class InvariantError(CliError):
    exit_code = EXIT_INTERNAL  # [L1081] "5 internal invariant violation"

def _now():
    '''[L1550]: the single legal clock read, reached only when --run-at was
    omitted (H-8 keeps every lower layer clock-free).'''
    return datetime.datetime.now()

def _import_dep(dotted):
    '''The one seam to every other dsm module: lazy (INV-2 decoupling) and
    testable, so core assertions never skip because a sibling lane is missing.'''
    return importlib.import_module(dotted)

def _require(name):
    try:
        return _import_dep(name)
    except ImportError as exc:
        raise ModuleMissingError('dependency module not landed: ' + name
                                 + ' (' + str(exc) + '); the CLI refuses to inline it '
                                 '(INV-2) and to degrade silently (V-14)')

def _attr(mod, name, owner):
    fn = getattr(mod, name, None)
    if fn is None or not callable(fn):
        raise ModuleMissingError(owner + ': entry point ' + mod.__name__ + '.'
                                 + name + ' absent; wiring awaits P2 integration')
    return fn

def exit_code_for(exc):
    if isinstance(exc, CliError):
        return exc.exit_code
    for klass in type(exc).__mro__:
        for name, code in _EXCEPTION_CODES:
            if klass.__name__ == name:
                return code
    return EXIT_INTERNAL

class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise CliUsage('usage error: ' + message)

def build_parser():
    common = _Parser(add_help=False)
    group = common.add_argument_group('common parameters [L1089]')
    group.add_argument('--period')
    group.add_argument('--config', default='config')
    group.add_argument('--data', default='data')
    group.add_argument('--out', default=DEFAULT_OUT)
    group.add_argument('--run-at', dest='run_at')
    group.add_argument('--seed', type=int)
    parser = _Parser(prog='dsm', description='DSM v1.1 offline engine [L1076]')
    sub = parser.add_subparsers(dest='command', required=True, metavar='COMMAND',
                                parser_class=_Parser)
    sub.add_parser('preflight', parents=[common])
    sub.add_parser('score', parents=[common])
    sens = sub.add_parser('sensitivity', parents=[common])
    sens.add_argument('--schemes', default='OAT_10,OAT_20,LOO')  # [L1554]
    for name, action in (('ahp', 'build'), ('combine', 'build'), ('fixtures', 'gen')):
        inner = sub.add_parser(name).add_subparsers(
            dest='action', required=True, parser_class=_Parser)
        child = inner.add_parser(action, parents=[common])
        child.set_defaults(action=action)
        if name == 'fixtures':
            child.set_defaults(out='fixtures')  # [L1087] dev/demo tool
    sub.add_parser('calibrate', parents=[common])
    whatif = sub.add_parser('whatif', parents=[common])
    # [L645] verbatim: "dsm whatif ... [--include-sensitivity]". whatif.run refuses an
    # empty scheme list once the flag is on (dsm/whatif.py:754-755), so the [L1554] trio
    # is the default here too: a flag with no way to name its schemes would be a dead
    # option, and Step 8 must never run on a scheme list this shell invented.
    whatif.add_argument('--include-sensitivity', dest='include_sensitivity',
                        action='store_true')
    whatif.add_argument('--schemes', default='OAT_10,OAT_20,LOO')  # [L1554]
    return parser

class Run:
    '''Per-invocation state: injected clock, run identity, directory helpers.
    run_id = command-period-<run_at>-sha256(command|period|run-at|seed|config|
    data)[:8]; _new_dir appends -N, so a rerun on identical bytes still gets a
    fresh directory and never overwrites ([L1091]).'''
    def __init__(self, args):
        self.args = args
        self.command = args.command
        self.run_at = self._parse_run_at(args.run_at)
        self.run_id = self._make_run_id(args)
        self.dir = None

    @staticmethod
    def _parse_run_at(text):
        if text is None:
            return _now()
        try:
            return datetime.datetime.fromisoformat(text)
        except ValueError:
            raise CliUsage('--run-at must be an ISO datetime ([L1089]): ' + text)

    def _make_run_id(self, args):
        seed_text = '|'.join((args.command + (getattr(args, 'action', None) or ''),
                              args.period or 'na', args.run_at or '', str(args.seed),
                              args.config, args.data))
        tag = hashlib.sha256(seed_text.encode('utf-8')).hexdigest()[:8]
        return '%s-%s-%s-%s' % (args.command, args.period or 'na',
                                self.run_at.strftime('%Y%m%dT%H%M%S'), tag)

    def _new_dir(self, group):
        base = Path(self.args.out) / group
        candidate = base / self.run_id
        n = 1
        while candidate.exists():
            n += 1
            candidate = base / (self.run_id + '-' + str(n))
        candidate.mkdir(parents=True)
        self.dir = candidate
        return candidate

    def prod_dir(self):
        if self.args.period in _L0B_GROUPS:
            raise InvariantError('INV-2: period collides with an L0b group: '
                                 + self.args.period)
        return self._new_dir(self.args.period)

    def l0b_dir(self, group):
        if group not in _L0B_GROUPS:
            raise InvariantError('INV-2: L0b output must live under a calibrate/ or '
                                 'whatif/ subdirectory, got: ' + group)
        return self._new_dir(group)

    def tool_dir(self, group):
        return self._new_dir(group)

    def audit_context(self, loaded, app=None):
        '''[L1051] item 8: config_snapshot_sha256 is a REQUIRED audit_bundle column. A
        failure to compute it is raised with the code its own exception type maps to,
        never folded into PLACEHOLDER -- PLACEHOLDER spells "unsigned value" ([L878]),
        not "the shell could not read it", and passing one off as the other is exactly
        the silent degradation V-14 forbids. A missing dsm.audit becomes a
        ModuleMissingError through _require (exit 5, module named), as everywhere else
        in this shell.'''
        audit = _require('dsm.audit')
        try:
            snapshot = audit.config_snapshot_sha256(
                app if app is not None else self.args.config)
        except CliError:
            raise
        except OSError as exc:
            # the signed config tree itself could not be read: [L1080] "3 config error"
            raise CliError(_snapshot_failure(self, exc), EXIT_CONFIG) from exc
        except Exception as exc:  # noqa: BLE001 - re-raised with its own mapped code
            raise CliError(_snapshot_failure(self, exc), exit_code_for(exc)) from exc
        return {'run_id': self.run_id, 'run_at': self.run_at,
                'dsm_version': dsm.__version__, 'design_version': dsm.DESIGN_DOC_VERSION,
                'cel_contract_version': PLACEHOLDER, 'config_snapshot_sha256': snapshot,
                'seed': self.args.seed, 'input_fingerprints': dict(loaded.fingerprints),
                'sensitivity_schemes': (), 'reproducibility_hash': PLACEHOLDER}

def _snapshot_failure(run, exc):
    '''The diagnosable text of a refused [L1051] item 8: which audit_bundle column,
    which --config, which exception type, and why PLACEHOLDER is not written in its
    place (V-14: an uncomputable digest is a failure, not an unsigned value).'''
    return ('config_snapshot_sha256 ([L1051] item 8) failed for --config '
            + repr(run.args.config) + ': ' + type(exc).__name__ + ': ' + str(exc)
            + '; the audit_bundle column stays uncomputed and the run stops instead of '
            'reporting PLACEHOLDER as though it were a digest (V-14)')


def _load_config(run):
    return _require('dsm.config').load_all(run.args.config)

def _load_inputs(run):
    return _require('dsm.io_loaders').load_inputs(run.args.data, run.args.period,
                                                  run.args.config)

def _plain(obj):
    if hasattr(obj, 'model_dump'):
        return obj.model_dump(mode='json')
    return obj if isinstance(obj, dict) else {'repr': str(obj)}

def _write_report(run, name, obj):
    payload = json.dumps(_plain(obj), sort_keys=True, ensure_ascii=False, indent=2,
                         default=str)
    path = run.dir / (name + '-' + run.run_id + '.json')  # run_id in name [L301]
    path.write_text(payload + '\n', encoding='utf-8', newline='\n')
    return path

def _chain_gate(run, app, loaded):
    '''M29 L1330-1358: the chain runs only with every owning module live; even a
    complete tree exits 5 until P2 lands the nine-step marshal, because the
    shell must not inline a step (INV-2).'''
    missing = []
    for name in _CHAIN_MODULES:
        try:
            _import_dep(name)
        except ImportError:
            missing.append(name)
    if missing:
        raise ModuleMissingError('score chain needs un-landed modules: '
                                 + ', '.join(missing)
                                 + '; no partial score is produced (V-14, [L1091])')
    raise InvariantError('chain modules are all present but the nine-step marshal of '
                         'M29 is a P2 integration deliverable; the shell refuses to '
                         'reimplement it (INV-2)')

def cmd_preflight(run):
    app = _load_config(run)
    loaded = _load_inputs(run)
    pfc = _build_preflight_config(app, run.args.period)
    run_dir = run.prod_dir()
    code, result, _paths = _require('dsm.preflight').execute(
        loaded.inputs, pfc, str(run_dir), run.audit_context(loaded, app))
    details = ['preflight status=' + str(getattr(result, 'status', 'PASS'))]
    findings = tuple(getattr(result, 'findings', ()) or ())
    if findings:
        details.append('findings=%d kept for the report appendix, never swallowed '
                       '([L1542])' % len(findings))
    if code == EXIT_BLOCK:
        details.append('BLOCK: only audit.json written, no score card [L1091]')
    return code, ('BLOCK' if code == EXIT_BLOCK else 'OK'), details

def _build_preflight_config(app, period):
    config = _require('dsm.preflight')
    models = _require('dsm.models')
    ev = dict(app.eval_config or {})
    absent = [k for k in ('period_ref_date', 'signed_signoff_status',
                          'missing_rate_warn', 'missing_rate_block')
              if ev.get(k) in (None, '')]
    if absent:
        raise CliError('eval_config lacks unsigned preflight governance fields: '
                       + ', '.join(absent) + ' - the CLI invents no business values '
                       '(V-14, K-01~K-20)', EXIT_CONFIG)
    weights = dict(app.weights or {})
    if len(weights) != 1:
        raise CliError('exactly one weights_*.yaml is required for preflight, got %d '
                       '(%s)' % (len(weights), ', '.join(sorted(weights))), EXIT_CONFIG)
    anchor = app.anchor_set
    return config.PreflightConfig(
        period=period,
        period_ref_date=datetime.date.fromisoformat(str(ev['period_ref_date'])),
        weight_version=models.WeightVersionDoc.model_validate(weights[sorted(weights)[0]]),
        anchor_set=None if not anchor else models.AnchorSetDoc.model_validate(anchor),
        signed_signoff_status=tuple(ev['signed_signoff_status']),
        missing_rate_warn=ev['missing_rate_warn'], missing_rate_block=ev['missing_rate_block'])

def cmd_score(run):
    return _chain_gate(run, _load_config(run), _load_inputs(run))

def cmd_sensitivity(run):
    app, loaded = _load_config(run), _load_inputs(run)
    schemes = tuple(s.strip() for s in run.args.schemes.split(',') if s.strip())
    if not schemes:
        raise CliUsage('--schemes must list at least one scheme ([L1554])')
    if any(s.startswith('MC') for s in schemes) and run.args.seed is None:
        raise CliError('--seed missing: MC schemes refuse to run without it ([L1089]); '
                       'no unseeded rerun is produced (V-14)', EXIT_CONFIG)
    return _chain_gate(run, app, loaded)

def cmd_ahp_build(run):
    app = _load_config(run)
    tree = dict(app.ahp_matrices or {})
    matrices = tree.get('dimension_matrices') or tree.get('matrices')
    if not isinstance(matrices, dict) or not matrices:
        raise CliError('ahp_matrices.yaml must carry a non-empty "dimension_matrices" '
                       '(or "matrices") map of expert matrices ([L1256])', EXIT_CONFIG)
    result = _require('dsm.weights_ahp').elicit(matrices,
                                                tuple(tree.get('interview_dates', ())))
    run.tool_dir('ahp')
    path = _write_report(run, 'ahp_draft', result)
    return EXIT_OK, 'OK', ['draft status=' + str(getattr(result, 'status', 'DRAFT'))
                           + ' (the tool may only write DRAFT [L1083])',
                           'draft=' + str(path)]

def cmd_combine_build(run):
    '''[L559] build_draft, wired per ORCH-31 p2_signature_deltas_from_ARCH1 item 1:
    the six positional arguments of the landed signature plus the keyword-only
    elicit_hierarchy injection. The L0a -> L0a edge is owned HERE, because the shell
    is the only layer allowed to see both L0a modules (that is exactly why ORCH-26/27
    moved the edge out of L0). The old "except TypeError -> InvariantError" cushion is
    gone: a marshal that no longer fits is a bug and must surface as one (V-14).
    Nothing is invented -- every governance value the signed config does not carry is
    refused with [L1080] exit 3 (R-12, K-15~K-20).'''
    app, loaded = _load_config(run), _load_inputs(run)
    wc = _require('dsm.weights_combine')
    fn = _attr(wc, 'build_draft', 'combine build')
    stem = _pick_draft(app)
    cfg = dict((app.eval_config or {}).get('weight_construction') or {})
    absent = [k for k in ('alpha', 'min_dim_weight', 'shift') if cfg.get(k) in (None, '')]
    if absent:
        raise CliError('eval_config.weight_construction lacks unsigned combine fields: '
                       + ', '.join(absent) + ' ([L562] alpha, [L564] min_dim_weight K-19, '
                       '[L540] shift -- the technical epsilon the digest states no value '
                       'for); the CLI invents none of them (V-14, R-12, K-15~K-20)',
                       EXIT_CONFIG)
    metric_dict = getattr(loaded.inputs, 'metric_dict', None)
    if not metric_dict:
        raise CliError('combine build needs the T2 metric_dict of [L891] for the Step 2 '
                       'entropy window; io_loaders returned none and no empty dictionary '
                       'is substituted for it (V-14)', EXIT_DATA)
    matrices = _ahp_matrix_pair(app)
    out = fn(matrices, _facts_history(wc, loaded.inputs), metric_dict,
             _combine_options(wc, cfg), _draft_header(wc, app, stem), cfg['shift'],
             elicit_hierarchy=_elicit_hierarchy)
    run.tool_dir('combine')
    path = _write_report(run, 'weights_draft', out)
    return EXIT_OK, 'OK', ['weights draft artifact, status DRAFT only [L1368]: '
                           + str(path)]


def _ahp_matrix_pair(app):
    '''The [L559] ahp_matrices mapping exactly as weights_combine._split_matrices reads
    it: {dimension: {expert: A}, metrics_by_dim: {dim: {expert: A}}}. The signed tree is
    handed over untouched -- judging matrix content is the owning module's job (INV-2) --
    but a tree without the two keys is refused here so the message names the config file
    instead of surfacing as a KeyError from inside Step 1.'''
    tree = dict(app.ahp_matrices or {})
    absent = [k for k in ('dimension', 'metrics_by_dim')
              if not isinstance(tree.get(k), dict) or not tree.get(k)]
    if absent:
        raise CliError('ahp_matrices.yaml must carry ' + ' and '.join(absent) + ' as '
                       '{expert: matrix} maps ([L520], [L559]); the signed file carries '
                       + (', '.join(sorted(tree)) or 'nothing'), EXIT_CONFIG)
    return {'dimension': tree['dimension'], 'metrics_by_dim': tree['metrics_by_dim']}


def _elicit_hierarchy(dim_mats, metric_mats_by_dim, interview_dates):
    '''The callable build_draft requires (ORCH-31 item 1), with the exact signature
    (dimension_matrices, metric_matrices_by_dim, interview_dates) ->
    weights_combine.AhpHierarchySnapshot. The elicitation itself stays in weights_ahp
    (R-7: the shell re-implements no algorithm and no CR gate); what the shell owns is
    the CONVERSION of the L0a product into the snapshot DATA weights_combine accepts,
    level by level, through AhpLevelSnapshot.from_payload(result.segment_payload(),
    result.findings) (ORCH-29 ruling 1). A level that cannot be converted stops the run
    instead of being padded with invented columns (R-12, V-14).'''
    ahp, wc = _require('dsm.weights_ahp'), _require('dsm.weights_combine')
    result = _attr(ahp, 'elicit_hierarchy', 'combine build')(
        dim_mats, metric_mats_by_dim, tuple(interview_dates or ()))
    dimension = _ahp_level(wc, getattr(result, 'dimension', None), 'dimension')
    per_dim = getattr(result, 'metrics_by_dim', None) or {}
    metrics = {d: _ahp_level(wc, per_dim[d], d) for d in sorted(per_dim)}
    carrier = _attr(wc, 'AhpHierarchySnapshot', 'combine build')
    snapshot = carrier(dimension=dimension, metrics_by_dim=metrics)
    if not isinstance(snapshot, carrier):
        raise InvariantError('combine build: elicit_hierarchy must hand build_draft a '
                             'weights_combine.AhpHierarchySnapshot -- the dimension layer '
                             'plus one metric layer per dimension, which is what H-1 of '
                             '[L594] accepts (ORCH-31 item 1); got '
                             + type(snapshot).__name__ + ' (V-14)')
    return snapshot


def _ahp_level(wc, result, label):
    '''One comparison level of [L1232]-[L1233] carried across the L0a edge as DATA.'''
    level = _attr(wc, 'AhpLevelSnapshot', 'combine build')
    payload = getattr(result, 'segment_payload', None)
    if not callable(payload):
        raise InvariantError('combine build: the weights_ahp product of the ' + str(label)
                             + ' level is ' + type(result).__name__ + ' and carries no '
                             'segment_payload(), so it cannot cross the L0a edge as the '
                             'snapshot DATA of [L1232]-[L1233] (ORCH-29 ruling 1); no '
                             'column is invented to fill the gap (R-12, V-14)')
    snapshot = _attr(level, 'from_payload', 'combine build')(
        payload(), tuple(getattr(result, 'findings', ()) or ()))
    if not isinstance(snapshot, level):
        raise InvariantError('combine build: the ' + str(label) + ' level converted to '
                             + type(snapshot).__name__ + ', not to an AhpLevelSnapshot, so '
                             'elicit_hierarchy would not return the AhpHierarchySnapshot '
                             'H-1 of [L594] requires (ORCH-31 item 1, V-14)')
    return snapshot


def _row_column(row, name):
    '''One column off an io_loaders row: an attribute on the pydantic contract rows of
    [L1149]-[L1154], a key on a mapping. Absent is an error, never a default (V-14).'''
    if hasattr(row, name):
        return getattr(row, name)
    try:
        return row[name]
    except (TypeError, KeyError, IndexError):
        raise InvariantError('combine build: a metric_facts row of [L1149]-[L1151] carries '
                             'no ' + name + ' column (got ' + type(row).__name__
                             + '); nothing is defaulted in its place (V-14)')


def _facts_history(wc, inputs):
    '''The Step 2 shape weights_combine.calibrate_entropy_window reads ([L813] of its
    docstring, [L1151] C-06): period -> metric_id -> strategy_id -> value, with the
    SUSPECT rows already dropped. The flag value comes from weights_combine.SUSPECT, not
    from a literal restated here (R-7 / P-8), and every value travels untouched -- no
    float, no re-rounding (V-9).'''
    suspect = getattr(wc, 'SUSPECT', None)
    if suspect is None:
        raise ModuleMissingError('combine build: dsm.weights_combine.SUSPECT ([L1151] C-06) '
                                 'is absent, so the SUSPECT rows cannot be filtered; the '
                                 'shell keeps no unfiltered fact and invents no flag value '
                                 '(V-14)')
    history = {}
    for row in tuple(getattr(inputs, 'metric_facts', ()) or ()):
        flag = _row_column(row, 'data_quality_flag')
        if str(getattr(flag, 'value', flag)) == str(suspect):
            continue
        period = str(_row_column(row, 'period'))
        metric = str(_row_column(row, 'metric_id'))
        table = history.setdefault(period, {}).setdefault(metric, {})
        table[str(_row_column(row, 'strategy_id'))] = _row_column(row, 'value')
    return history


def _combine_options(wc, cfg):
    '''[L561]-[L568]: only the keys the signed config actually carries are passed, so the
    digest defaults of [L563] / [L566]-[L568] stay the owning module's own and are not
    restated here. alpha ([L562]) and min_dim_weight ([L564] K-19) have no default and
    are refused by cmd_combine_build before this is reached.'''
    kwargs = {}
    for key in ('alpha', 'alpha_floor', 'min_dim_weight', 'min_metric_weight',
                'entropy_min_strategies', 'inactive_threshold', 'max_shift_from_ahp'):
        if cfg.get(key) not in (None, ''):
            kwargs[key] = cfg[key]
    return _attr(wc, 'CombineOptions', 'combine build')(**kwargs)


def _draft_header(wc, app, stem):
    '''The Step 6 identity of [L1232]-[L1241], taken from the DRAFT weights document the
    signed config already carries (T6, [L1190]-[L1194]). No date is read from a clock
    (H-8: interview_dates come from ahp_matrices, the rest from the document) and no
    sign-off value is invented (R-12). calibration_report_ref ([L1236]) and whatif_run_id
    ([L1241]) stay at their nullable default unless the document supplies them.'''
    doc = dict((app.weights or {}).get(stem) or {})
    tree = dict(app.ahp_matrices or {})
    kwargs = {'interview_dates': tuple(tree.get('interview_dates', ()) or ())}
    for key in ('weight_version_id', 'approved_by', 'approved_date', 'effective_from',
                'effective_to', 'alpha_source', 'calibration_report_ref', 'whatif_run_id'):
        if doc.get(key) not in (None, ''):
            kwargs[key] = doc[key]
    absent = [k for k in ('weight_version_id', 'approved_by', 'approved_date',
                          'effective_from', 'effective_to') if k not in kwargs]
    if absent:
        raise CliError('the DRAFT weights file ' + stem + ' lacks the Step 6 identity '
                       'columns of [L1190]-[L1194]: ' + ', '.join(absent) + '; the CLI '
                       'invents no sign-off value (V-14, R-12)', EXIT_CONFIG)
    return _attr(wc, 'DraftHeader', 'combine build')(**kwargs)


def _draft_header_or_none(wc, app):
    '''CalibrationInputs.draft_header is OPTIONAL and nullable ([L1236] "never
    invented"), so it is carried when the signed config holds exactly one DRAFT weights
    document to take the identity from and left at its None default when it does not.
    This is not a swallowed failure: _draft_header still refuses an incomplete one.'''
    weights = dict(app.weights or {})
    stems = [s for s in sorted(weights)
             if str((weights[s] or {}).get('status')) == 'DRAFT']
    return _draft_header(wc, app, stems[0]) if len(stems) == 1 else None

def _pick_draft(app):
    weights = dict(app.weights or {})
    for stem in sorted(weights):
        if str((weights[stem] or {}).get('status')) == 'DRAFT':
            return stem
    raise CliError('no weights file with status DRAFT; run "dsm ahp build" then '
                   '"dsm combine build" ([L1367]-[L1368])', EXIT_CONFIG)

def cmd_calibrate(run):
    '''[L1072] calibrate(grid, window, inputs, config): the marshal stays frozen and, per
    ORCH-31 p2_signature_deltas_from_ARCH1 item 2, the only delta is that `inputs` is a
    weights_calibrate.CalibrationInputs carrying the four keyword-only L0a injections.
    [L294] lets L0b import L1-L5 only, so weights_calibrate imports no L0a module and
    defaults to none of them; a hole is its HookRequiredError, and this shell closes all
    four (V-14). The old "except TypeError -> InvariantError" cushion is gone.'''
    app, loaded = _load_config(run), _load_inputs(run)
    wcal, wc = _require('dsm.weights_calibrate'), _require('dsm.weights_combine')
    fn = _attr(wcal, 'calibrate', 'calibrate')
    cfg = dict((app.eval_config or {}).get('weight_construction') or {})
    absent = [k for k in ('alpha_grid', 'window') if not cfg.get(k)]
    if absent:
        raise CliError('eval_config.weight_construction lacks unsigned calibration '
                       'fields: ' + ', '.join(absent) + ' (K-15~K-20: no governance '
                       'value is invented)', EXIT_CONFIG)
    run.l0b_dir('calibrate')  # INV-2: the ONLY calibrate output location
    report = fn(grid=cfg['alpha_grid'], window=cfg['window'],
                inputs=_calibration_inputs(wcal, wc, app, loaded, run, cfg),
                config=app)
    path = _write_report(run, 'calibration_report', report)
    return EXIT_OK, 'OK', ['L0b artifact in isolated dir [L301]: ' + str(path)]


def _calibrate_hooks(wc):
    '''The four keyword-only injections of ORCH-31 item 2, verbatim: combine_fn,
    options_fn, entropy_window_fn, insufficient_sample_error, all four read off
    dsm.weights_combine (the L0a side weights_calibrate may not import, [L294]).
    Each is resolved through _attr, so a renamed or absent L0a symbol is an explicit
    ModuleMissingError naming the entry point, never an import fallback and never a
    None that would only surface as HookRequiredError deep inside the backtest.'''
    return {'combine_fn': _attr(wc, 'combine', 'calibrate'),
            'options_fn': _attr(wc, 'CombineOptions', 'calibrate'),
            'entropy_window_fn': _attr(wc, 'calibrate_entropy_window', 'calibrate'),
            'insufficient_sample_error': _attr(wc, 'EntropyInsufficientSample',
                                               'calibrate')}


def _calibration_inputs(wcal, wc, app, loaded, run, cfg):
    '''Build the `inputs` argument of [L1072]. Everything the digest leaves without a
    value is demanded from the signed config or from the run identity and refused when
    absent (R-12): shift is the [L540] technical epsilon, hierarchy is the Step-1
    snapshot H-1 of [L594] reads, run_id is the [L636] audit-chain identity, and
    period_cases are the Step 1-7 frames of every window period.'''
    ctor = _attr(wcal, 'CalibrationInputs', 'calibrate')
    hooks = _calibrate_hooks(wc)  # first: a broken L0a symbol is named, not masked
    if cfg.get('shift') in (None, ''):
        raise CliError('eval_config.weight_construction.shift -- the [L540] technical '
                       'epsilon -- is absent; calibrate() refuses a None shift and this '
                       'shell invents no value (R-12, V-14, K-15~K-20)', EXIT_CONFIG)
    metric_dict = getattr(loaded.inputs, 'metric_dict', None)
    if not metric_dict:
        raise CliError('calibrate needs the T2 metric_dict of [L891] for the Step 2 '
                       'entropy window; io_loaders returned none and no empty dictionary '
                       'is substituted for it (V-14)', EXIT_DATA)
    tree = dict(app.ahp_matrices or {})
    matrices = _ahp_matrix_pair(app)
    kwargs = dict(hooks)
    kwargs.update({'hierarchy': _elicit_hierarchy(matrices['dimension'],
                                                  matrices['metrics_by_dim'],
                                                  tuple(tree.get('interview_dates', ())
                                                        or ())),
                   'metric_dict': metric_dict,
                   'shift': cfg['shift'],
                   'period_cases': _period_cases(run, loaded),
                   'run_id': run.run_id,
                   'seed': run.args.seed,
                   'draft_header': _draft_header_or_none(wc, app)})
    return ctor(**kwargs)


def _period_cases(run, loaded):
    '''period -> weights_calibrate.PeriodCase: the [L619]-[L622] indicators read the Step
    5-7 products of every window period, so each case needs the Step 1-4 frames, the
    attainment floors of [L620] and the prior ledger. Assembling those is the M29
    L1330-1358 nine-step marshal, which this shell must not inline (INV-2) and which is
    a P2-wire deliverable gated on A1c + MODELS-1 -- the same gate _chain_gate states for
    score / sensitivity. An EMPTY mapping is deliberately not passed: calibrate() would
    answer it with the [L634] alpha = 1 degrade and hand back a report that looks
    calibrated while no period was ever backtested (V-14, no silent degradation).'''
    raise InvariantError('calibrate needs one weights_calibrate.PeriodCase per window '
                         'period, i.e. the Step 1-7 frames of M29 L1330-1358; that '
                         'nine-step marshal is a P2-wire deliverable gated on A1c + '
                         'MODELS-1 and the shell refuses to fake an empty calibration '
                         'window (INV-2, V-14)')

def cmd_whatif(run):
    app, loaded = _load_config(run), _load_inputs(run)
    fn = _attr(_require('dsm.whatif'), 'run', 'whatif')
    candidate, baseline = _whatif_inputs(app)
    schemes = tuple(s.strip() for s in str(run.args.schemes or '').split(',') if s.strip())
    if run.args.include_sensitivity and not schemes:
        # raised before l0b_dir: a usage error creates no run directory at all
        raise CliUsage('--include-sensitivity needs a non-empty --schemes list ([L645]); '
                       'whatif.run refuses Step 8 without one and this shell names no '
                       'scheme of its own (V-14)')
    run.l0b_dir('whatif')  # INV-2: the ONLY whatif output location
    # dsm/whatif.py:664-665 keyword-only set, all five now supplied: run_id is the
    # sign-off-chain preview id (_check_run_id refuses None, [L1241]); input_dir +
    # directory_hash are the INV-2 read-only self-proof pair, given together or not at
    # all, the hash being an INJECTED callable built from dsm.audit primitives only
    # (ORCH-27 D-A4-01, whatif.py:814-817); include_sensitivity / schemes are [L645].
    report = fn(candidate=candidate, baseline=baseline, inputs=loaded.inputs,
                config=app, period=run.args.period, run_id=run.run_id,
                include_sensitivity=bool(run.args.include_sensitivity), schemes=schemes,
                input_dir=run.args.data, directory_hash=_directory_hash)
    path = _write_report(run, 'whatif_report', report)
    details = ['L0b artifact in isolated dir [L301]: ' + str(path)]
    delta = (report.redline_delta if hasattr(report, 'redline_delta')
             else report.get('redline_delta') if isinstance(report, dict) else None)
    if delta:
        details.append('CONFIG_INCONSISTENT: redline_delta non-empty, refusal of '
                       'sign-off recommended ([L1370])')
    return EXIT_OK, 'OK', details

def _directory_hash(root):
    '''The INV-2 read-only self-proof whatif.run asks its caller to inject
    (dsm/whatif.py:814-817): one digest of every file under `root`, built ONLY out of
    dsm.audit primitives -- sha256_bytes per file, then canonical_text for the
    deterministic key ordering of [L1053] rules 3-4, then sha256_text over that. The
    shell re-implements no hash (R-7) and whatif.py imports no L6 module (M00 L294).
    A root that does not exist is refused rather than hashed as an empty manifest: a
    proof over nothing would certify nothing and still read as a passed self-proof
    (V-14).'''
    audit = _require('dsm.audit')
    base = Path(root)
    if not base.is_dir():
        raise CliError('whatif --data ' + repr(str(root)) + ' is not a readable directory, '
                       'so the INV-2 read-only self-proof of [L1073] cannot be taken; no '
                       'vacuous directory hash is substituted for it (V-14)', EXIT_DATA)
    manifest = {}
    for path in sorted(base.rglob('*')):
        if path.is_file():
            manifest[path.relative_to(base).as_posix()] = audit.sha256_bytes(
                path.read_bytes())
    return audit.sha256_text(audit.canonical_text(manifest))


def _whatif_inputs(app):
    weights = dict(app.weights or {})
    status = {s: str((weights[s] or {}).get('status')) for s in sorted(weights)}
    candidate = [s for s in status if status[s] == 'DRAFT']
    baseline = [s for s in status if status[s] == 'FROZEN']
    if len(candidate) != 1 or len(baseline) != 1:
        raise CliError('whatif needs exactly one DRAFT candidate and one FROZEN '
                       'baseline weights file ([L1369]), found candidate=%d '
                       'baseline=%d' % (len(candidate), len(baseline)), EXIT_CONFIG)
    return candidate[0], baseline[0]

def cmd_fixtures_gen(run):
    kwargs = {'root': run.args.out}
    if run.args.seed is not None:
        kwargs['seed'] = run.args.seed
    docs = _require('dsm.fixtures_gen').write_bundle(**kwargs)  # no clock, fixed seed
    return EXIT_OK, 'OK', ['wrote %d fixture files under %s ([L1087] exit 0)'
                           % (len(docs), run.args.out)]

HANDLERS = {('preflight', None): cmd_preflight, ('score', None): cmd_score,
            ('sensitivity', None): cmd_sensitivity, ('ahp', 'build'): cmd_ahp_build,
            ('calibrate', None): cmd_calibrate,
            ('combine', 'build'): cmd_combine_build, ('whatif', None): cmd_whatif,
            ('fixtures', 'gen'): cmd_fixtures_gen}

def _write_failure_bundle(run, exc, code):
    '''[L1091]: a failing command leaves an audit_bundle; values the failure
    prevented are PLACEHOLDER, never invented [L878]. L0b failures stay inside
    their calibrate/whatif group (INV-2).'''
    if run is None:
        return None
    try:
        if run.dir is None:
            group = run.command if run.command in _L0B_GROUPS else 'failed'
            run_dir = (run.l0b_dir(group) if group in _L0B_GROUPS
                       else run.tool_dir(group))
        else:
            run_dir = run.dir
        doc = {k: PLACEHOLDER for k in _BUNDLE_KEYS}
        doc.update({'run_id': run.run_id, 'run_at': run.run_at.isoformat(),
                    'period': run.args.period or PLACEHOLDER,
                    'dsm_version': dsm.__version__,
                    'design_version': dsm.DESIGN_DOC_VERSION, 'seed': run.args.seed,
                    'exit_code': code, 'error_type': type(exc).__name__,
                    'error': str(exc), 'output_fingerprints': {}})
        path = run_dir / 'audit_bundle.json'
        path.write_text(json.dumps(doc, sort_keys=True, ensure_ascii=False, indent=2)
                        + '\n', encoding='utf-8', newline='\n')
        return path
    except OSError:
        return None

def _emit(command, code, status, run_id, details):
    print('dsm %s: exit=%d status=%s run_id=%s'
          % (command, code, status, run_id or '-'))
    for line in details:
        print('  ' + line)

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    run = None
    command = argv[0] if argv and not argv[0].startswith('-') else 'usage'
    try:
        args = build_parser().parse_args(argv)
        action = getattr(args, 'action', None)
        command = args.command + (' ' + action if action else '')
        if args.command in PERIOD_COMMANDS and not args.period:
            raise CliUsage(command + ' requires --period ([L1089])')
        run = Run(args)
        code, status, details = HANDLERS[(args.command, action)](run)
    except BaseException as exc:  # noqa: BLE001 - one mapping for every failure
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            # argparse answers -h/--help through parser.exit() -> SystemExit(0). Swallowing
            # it here made exit_code_for fall through to EXIT_INTERNAL, so all twelve
            # --help invocations printed the help text and then claimed an [L1081] internal
            # invariant violation (exit 5). A request to stop is re-raised, never reported
            # as a failed run; usage errors still exit 3 because _Parser.error raises
            # CliUsage instead of calling exit(2) ([L1080]).
            raise
        code = exit_code_for(exc)
        status = _CODE_STATUS.get(code, 'FAILED')
        details = ['error: %s: %s' % (type(exc).__name__, exc)]
        bundle = _write_failure_bundle(run, exc, code)
        if bundle is not None:
            details.append('audit_bundle=' + str(bundle))
        if code not in (EXIT_BLOCK, EXIT_CONFIG, EXIT_DATA):
            details.append('no score card is produced on a non-zero exit ([L1091])')
    _emit(command, code, status, run.run_id if run else None, details)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
