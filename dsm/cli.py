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
# already holds for modules landing after this shell.
_EXCEPTION_CODES = (('ConfigPlaceholderError', EXIT_CONFIG), ('ConfigSemanticError', 3),
                    ('WeightVersionInvalidError', 3), ('MatrixNotReciprocalError', 3),
                    ('FrozenStatusError', 3), ('ValidationError', 3),
                    ('DataLoadError', EXIT_DATA), ('CoercionError', 4),
                    ('ConsistencyFailedError', EXIT_CONSISTENCY),
                    ('AlphaInfeasibleError', EXIT_ALPHA),
                    ('AlphaFloorInfeasibleError', EXIT_ALPHA))
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
    sub.add_parser('whatif', parents=[common])
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
        snapshot = PLACEHOLDER
        try:
            snapshot = _import_dep('dsm.audit').config_snapshot_sha256(app or self.args.config)
        except (ImportError, OSError, ValueError, TypeError):
            pass
        return {'run_id': self.run_id, 'run_at': self.run_at,
                'dsm_version': dsm.__version__, 'design_version': dsm.DESIGN_DOC_VERSION,
                'cel_contract_version': PLACEHOLDER, 'config_snapshot_sha256': snapshot,
                'seed': self.args.seed, 'input_fingerprints': dict(loaded.fingerprints),
                'sensitivity_schemes': (), 'reproducibility_hash': PLACEHOLDER}

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
    app = _load_config(run)
    fn = _attr(_require('dsm.weights_combine'), 'build_draft', 'combine build')
    try:
        out = fn(_pick_draft(app), app)
    except TypeError as exc:
        raise InvariantError('combine build_draft marshal awaits P2 integration '
                             '(INV-2, no invented keys): ' + str(exc))
    run.tool_dir('combine')
    path = _write_report(run, 'weights_draft', out)
    return EXIT_OK, 'OK', ['weights draft artifact, status DRAFT only [L1368]: '
                           + str(path)]

def _pick_draft(app):
    weights = dict(app.weights or {})
    for stem in sorted(weights):
        if str((weights[stem] or {}).get('status')) == 'DRAFT':
            return stem
    raise CliError('no weights file with status DRAFT; run "dsm ahp build" then '
                   '"dsm combine build" ([L1367]-[L1368])', EXIT_CONFIG)

def cmd_calibrate(run):
    app, loaded = _load_config(run), _load_inputs(run)
    fn = _attr(_require('dsm.weights_calibrate'), 'calibrate', 'calibrate')
    wc = dict((app.eval_config or {}).get('weight_construction') or {})
    absent = [k for k in ('alpha_grid', 'window') if not wc.get(k)]
    if absent:
        raise CliError('eval_config.weight_construction lacks unsigned calibration '
                       'fields: ' + ', '.join(absent) + ' (K-15~K-20: no governance '
                       'value is invented)', EXIT_CONFIG)
    run.l0b_dir('calibrate')  # INV-2: the ONLY calibrate output location
    try:
        report = fn(grid=wc['alpha_grid'], window=wc['window'],
                    inputs=loaded.inputs, config=app)
    except TypeError as exc:
        raise InvariantError('calibrate marshal awaits P2 integration (INV-2): '
                             + str(exc))
    path = _write_report(run, 'calibration_report', report)
    return EXIT_OK, 'OK', ['L0b artifact in isolated dir [L301]: ' + str(path)]

def cmd_whatif(run):
    app, loaded = _load_config(run), _load_inputs(run)
    fn = _attr(_require('dsm.whatif'), 'run', 'whatif')
    candidate, baseline = _whatif_inputs(app)
    run.l0b_dir('whatif')  # INV-2: the ONLY whatif output location
    try:
        report = fn(candidate=candidate, baseline=baseline, inputs=loaded.inputs,
                    config=app, period=run.args.period)
    except TypeError as exc:
        raise InvariantError('whatif marshal awaits P2 integration (INV-2): ' + str(exc))
    path = _write_report(run, 'whatif_report', report)
    details = ['L0b artifact in isolated dir [L301]: ' + str(path)]
    delta = (report.redline_delta if hasattr(report, 'redline_delta')
             else report.get('redline_delta') if isinstance(report, dict) else None)
    if delta:
        details.append('CONFIG_INCONSISTENT: redline_delta non-empty, refusal of '
                       'sign-off recommended ([L1370])')
    return EXIT_OK, 'OK', details

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
        if isinstance(exc, KeyboardInterrupt):
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