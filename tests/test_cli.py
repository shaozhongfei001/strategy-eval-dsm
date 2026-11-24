'''D5 tests -- dsm/cli.py eight subcommands, exit-code mapping, L0b directory
discipline (INV-2), offline shell (V-10 / V-14).

Authority: docs/digest/M27-cli.md [L1076]-[L1092], M29 L1312-1359, M30
L1360-1374, M00 L301 (INV-2). Not-landed sibling modules are NOT a reason to
skip: they are forced through the lazy-import seam cli._import_dep or injected
into sys.modules, so every exit-code branch is executable today (R-2 spirit).
Landed modules (config, io_loaders, weights_ahp, fixtures_gen) are called for
real; the parquet defect D-C1-01 is sidestepped (CSV/no-parquet paths only).
Exit-code proof map: 0 -> test_exit0_* / preflight-pass / calibrate / whatif;
2 -> test_preflight_block_exit2_pass_exit0; 3 -> test_usage_error,
test_exit3_config_placeholder, test_mc_scheme_without_seed; 4 ->
test_exit4_data_load_error_real; 5 -> test_chain_gate_missing_modules_exit5;
6 -> test_exit6_ahp_consistency_failed; 7 -> test_alpha_infeasible_exit7.
INV-2 paths -> calibrate/whatif/alpha tests; INV-2 no-inline + V-10 offline ->
test_inv2_no_inlined_algorithms_v10_offline.
'''
import ast
import importlib
import json
import sys
import types
from pathlib import Path

import dsm.cli as cli

REPO = Path(__file__).resolve().parents[1]
EIGHT = [('preflight', None), ('score', None), ('sensitivity', None),
         ('ahp', 'build'), ('calibrate', None), ('combine', 'build'),
         ('whatif', None), ('fixtures', 'gen')]
CONSISTENT = {'e1': {'A': {'A': '1', 'B': '2', 'C': '4'},
                     'B': {'A': '0.5', 'B': '1', 'C': '2'},
                     'C': {'A': '0.25', 'B': '0.5', 'C': '1'}}}
CR_FAIL = {'e1': {'A': {'A': '1', 'B': '1', 'C': '8'},
                  'B': {'A': '1', 'B': '1', 'C': '1'},
                  'C': {'A': '0.125', 'B': '1', 'C': '1'}}}


def _first_line(capsys):
    out = capsys.readouterr().out.splitlines()
    assert out, 'CLI printed nothing'
    return out[0]


def _code(line):
    return int(line.split('exit=')[1].split()[0])


def _app(**over):
    base = {'eval_config': {}, 'weights': {}, 'redlines': {}, 'grade_rules': {},
            'anchor_set': {}, 'ahp_matrices': {}}
    base.update(over)
    return types.SimpleNamespace(**base)


def _stub_io(monkeypatch, app=None):
    monkeypatch.setattr(cli, '_load_config',
                        lambda run: app if app is not None else _app())
    monkeypatch.setattr(cli, '_load_inputs',
                        lambda run: types.SimpleNamespace(inputs=(), fingerprints={}))


def _fake_module(name, **attrs):
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def test_eight_subcommands_registered():
    '''M27 [L1080]-[L1087]: the eight registration names exist and dispatch.'''
    assert sorted(cli.HANDLERS) == sorted(EIGHT), 'subcommand set must match digest'
    parser = cli.build_parser()
    for command, action in EIGHT:
        argv = [command] + ([action] if action else []) + ['--period', '2026-10']
        args = parser.parse_args(argv)
        assert (args.command, getattr(args, 'action', None)) in cli.HANDLERS


def test_usage_error_exits_3_never_2(tmp_path, capsys):
    '''argparse native code 2 would masquerade as preflight BLOCK [L1080].'''
    assert cli.main(['no-such-command', '--out', str(tmp_path)]) == 3
    assert cli.main(['preflight', '--out', str(tmp_path)]) == 3
    assert cli.main(['score', '--period', '2026-10', '--bogus', 'x',
                     '--out', str(tmp_path)]) == 3
    out = capsys.readouterr().out
    assert 'status=CONFIG' in out and 'exit=2' not in out
    assert not any(p.is_dir() for p in tmp_path.iterdir()), \
        'a usage error must not create run directories'


def test_common_params_parse():
    '''[L1089]: --period/--config/--data/--out/--run-at/--seed all land.'''
    args = cli.build_parser().parse_args(
        ['preflight', '--period', '2026-10', '--config', 'c/', '--data', 'd/',
         '--out', 'o/', '--run-at', '2026-11-05T09:00:00', '--seed', '42'])
    assert (args.period, args.config, args.data, args.out) == \
        ('2026-10', 'c/', 'd/', 'o/')
    assert args.run_at == '2026-11-05T09:00:00' and args.seed == 42
    args = cli.build_parser().parse_args(['sensitivity', '--period', '2026-10'])
    assert args.schemes == 'OAT_10,OAT_20,LOO'  # [L1554] default trio


def test_exit0_fixtures_gen_real(tmp_path):
    '''exit 0, REAL dsm.fixtures_gen [L1087]: writes fixtures under --out root.'''
    code = cli.main(['fixtures', 'gen', '--out', str(tmp_path), '--seed', '7'])
    assert code == 0
    assert any(p.is_file() for p in tmp_path.rglob('*')), 'fixtures gen wrote nothing'


def test_exit0_ahp_build_real_draft_only(tmp_path, monkeypatch, capsys):
    '''exit 0 + DRAFT-only artifact [L1083] via the REAL weights_ahp CR gate.'''
    monkeypatch.setattr(cli, '_load_config',
                        lambda run: _app(ahp_matrices={'dimension_matrices':
                                                       CONSISTENT}))
    code = cli.main(['ahp', 'build', '--config', 'x', '--out', str(tmp_path)])
    assert code == 0
    run_id = _first_line(capsys).split('run_id=')[1].split()[0]
    report = next((tmp_path / 'ahp').rglob('ahp_draft-*.json'))
    assert run_id in report.name, 'run_id must be in the file name [L301]'
    doc = json.loads(report.read_text(encoding='utf-8'))
    assert doc['status'] == 'DRAFT', 'the tool may never write FROZEN [L522]'


def test_exit6_ahp_consistency_failed(tmp_path, monkeypatch, capsys):
    '''exit 6 [L1083]/M42 L1070; failure leaves an audit_bundle and never a
    score card ([L1091]).'''
    monkeypatch.setattr(cli, '_load_config',
                        lambda run: _app(ahp_matrices={'dimension_matrices': CR_FAIL}))
    code = cli.main(['ahp', 'build', '--config', 'x', '--out', str(tmp_path)])
    assert code == 6
    assert 'CONSISTENCY_FAILED' in capsys.readouterr().out
    bundles = list(tmp_path.rglob('audit_bundle.json'))
    assert bundles, 'failing command must write an audit_bundle [L1091]'
    assert json.loads(bundles[0].read_text(encoding='utf-8'))['exit_code'] == 6
    assert not list(tmp_path.rglob('score_card*')), 'non-zero exit forbids score_card'


def test_exit3_config_placeholder_and_missing_real(tmp_path, capsys):
    '''exit 3 via REAL dsm.config: placeholder paths listed at once ([L878]),
    missing required files ride the same single exit (ruling 10).'''
    cfg = tmp_path / 'config'
    cfg.mkdir()
    (cfg / 'eval_config.yaml').write_text('operator: PLACEHOLDER\n', encoding='utf-8')
    for stem in ('redlines', 'grade_rules', 'anchor_set', 'ahp_matrices',
                 'weights_WV-001'):
        (cfg / (stem + '.yaml')).write_text('meta: signed\n', encoding='utf-8')
    out = tmp_path / 'out'
    code = cli.main(['preflight', '--period', '2026-10', '--config', str(cfg),
                     '--out', str(out)])
    assert code == 3
    assert 'eval_config.operator' in capsys.readouterr().out
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert cli.main(['preflight', '--period', '2026-10', '--config', str(empty),
                     '--out', str(out)]) == 3


def test_exit4_data_load_error_real(tmp_path, monkeypatch, capsys):
    '''exit 4 via REAL dsm.io_loaders: MISSING_FILE is blocking [L892]; the
    parquet defect D-C1-01 is untouched (no parquet on this path).'''
    monkeypatch.setattr(cli, '_load_config', lambda run: _app())
    code = cli.main(['preflight', '--period', '2026-01', '--config',
                     str(tmp_path / 'noconf'), '--data', str(tmp_path / 'nodata'),
                     '--out', str(tmp_path / 'out')])
    assert code == 4
    assert 'status=DATA' in capsys.readouterr().out


def test_preflight_block_exit2_pass_exit0(tmp_path, monkeypatch, capsys):
    '''exit 2 BLOCK audit-only ([L1541]); exit 0 PASS writes nothing ([L917]);
    mapping proven through the lazy seam (real BLOCK fixtures are C2-owned).'''
    _stub_io(monkeypatch)
    monkeypatch.setattr(cli, '_build_preflight_config', lambda app, period: object())

    def block_execute(inputs, cfg, out_dir, ctx):
        path = Path(out_dir) / 'audit.json'
        path.write_text('{"stub": true}', encoding='utf-8')
        return 2, types.SimpleNamespace(status='BLOCK', findings=(),
                                        downgrade_actions=()), (path,)

    monkeypatch.setitem(sys.modules, 'dsm.preflight',
                        _fake_module('dsm.preflight', execute=block_execute))
    out = tmp_path / 'o1'
    assert cli.main(['preflight', '--period', '2026-10', '--out', str(out)]) == 2
    line = _first_line(capsys)
    assert _code(line) == 2 and 'status=BLOCK' in line
    files = sorted(p.name for p in out.rglob('*') if p.is_file())
    assert files == ['audit.json'], 'BLOCK writes only the audit bundle [L1541]'

    monkeypatch.setitem(sys.modules, 'dsm.preflight', _fake_module(
        'dsm.preflight', execute=lambda i, c, d, x: (0, types.SimpleNamespace(
            status='PASS', findings=(object(),), downgrade_actions=()), ())))
    out2 = tmp_path / 'o2'
    assert cli.main(['preflight', '--period', '2026-10', '--out', str(out2)]) == 0
    printed = capsys.readouterr().out
    assert 'status=OK' in printed and 'findings=1' in printed, \
        'findings are disclosed, never swallowed ([L1542], V-14)'
    assert not [p for p in out2.rglob('*') if p.is_file()], \
        'PASS preflight produces no score artifacts ([L917])'


def test_chain_gate_missing_modules_exit5(tmp_path, monkeypatch, capsys):
    '''exit 5 [L1081]: score/sensitivity name every un-landed module via the
    lazy seam: explicit message, no traceback, no partial score (V-14).'''
    _stub_io(monkeypatch)

    def fake_import(dotted):
        if dotted in ('dsm.pooling', 'dsm.triangulation'):
            raise ModuleNotFoundError('No module named ' + repr(dotted))
        return importlib.import_module(dotted)

    monkeypatch.setattr(cli, '_import_dep', fake_import)
    out = tmp_path / 'out'
    assert cli.main(['score', '--period', '2026-10', '--seed', '3',
                     '--out', str(out)]) == 5
    assert cli.main(['sensitivity', '--period', '2026-10', '--seed', '3',
                     '--out', str(out)]) == 5
    printed = capsys.readouterr().out
    assert 'dsm.pooling' in printed and 'dsm.triangulation' in printed
    assert 'Traceback' not in printed
    assert not list(out.rglob('score_card*'))


def test_mc_scheme_without_seed_exit3(tmp_path, monkeypatch, capsys):
    '''[L1089] "seed missing -> refuse MC": exit 3, explicit, no unseeded run.'''
    _stub_io(monkeypatch)
    code = cli.main(['sensitivity', '--period', '2026-10', '--schemes',
                     'OAT_10,MC_100', '--out', str(tmp_path)])
    assert code == 3
    assert '--seed' in capsys.readouterr().out


def test_calibrate_l0b_dir_discipline(tmp_path, monkeypatch, capsys):
    '''INV-2 [L301]: calibrate artifacts ONLY under <out>/calibrate/<run_id>/,
    never the period production dir; run_id also in the file name.'''
    app = _app(eval_config={'weight_construction': {'alpha_grid': ['1'],
                                                    'window': 4}})
    _stub_io(monkeypatch, app)
    monkeypatch.setitem(sys.modules, 'dsm.weights_calibrate', _fake_module(
        'dsm.weights_calibrate',
        calibrate=lambda **kw: {'alpha_star': 'PLACEHOLDER', 'n_grid': len(kw['grid'])}))
    out = tmp_path / 'out'
    code = cli.main(['calibrate', '--period', '2026-10', '--out', str(out)])
    assert code == 0
    assert not (out / '2026-10').exists(), 'L0b must not write the production dir'
    groups = {p.relative_to(out).parts[0] for p in out.rglob('*') if p.is_file()}
    assert groups == {'calibrate'}
    report = next((out / 'calibrate').rglob('calibration_report-*.json'))
    assert 'calibrate-' in report.name
    assert 'PLACEHOLDER' in report.read_text(encoding='utf-8'), \
        'unsigned alpha stays PLACEHOLDER, never invented (V-14, K-15~K-20)'


def test_alpha_infeasible_exit7(tmp_path, monkeypatch, capsys):
    '''exit 7 [L1084]/M42 L1072; failure bundle stays inside calibrate/<run_id>/
    (INV-2) and never a whatif/ production path.'''
    app = _app(eval_config={'weight_construction': {'alpha_grid': [1, 2],
                                                    'window': 4}})
    _stub_io(monkeypatch, app)

    class AlphaInfeasibleError(Exception):
        pass

    def raise_infeasible(**kw):
        raise AlphaInfeasibleError('feasible set empty over the grid [L1084]')

    monkeypatch.setitem(sys.modules, 'dsm.weights_calibrate',
                        _fake_module('dsm.weights_calibrate',
                                     calibrate=raise_infeasible))
    out = tmp_path / 'out'
    assert cli.main(['calibrate', '--period', '2026-10', '--out', str(out)]) == 7
    printed = capsys.readouterr().out
    assert 'ALPHA_INFEASIBLE' in printed and 'exit=7' in printed
    bundles = list((out / 'calibrate').rglob('audit_bundle.json'))
    assert bundles, 'failure audit_bundle inside the L0b dir [L1091]'
    assert json.loads(bundles[0].read_text(encoding='utf-8'))['exit_code'] == 7
    assert not (out / 'whatif').exists()


def test_whatif_l0b_dir_and_redline_delta(tmp_path, monkeypatch, capsys):
    '''INV-2: whatif writes ONLY <out>/whatif/<run_id>/; non-empty
    redline_delta surfaces CONFIG_INCONSISTENT [L1370].'''
    app = _app(weights={'weights_WV-D': {'status': 'DRAFT'},
                        'weights_WV-F': {'status': 'FROZEN'}})
    _stub_io(monkeypatch, app)
    monkeypatch.setitem(sys.modules, 'dsm.whatif', _fake_module(
        'dsm.whatif', run=lambda **kw: {'redline_delta': ['RL-1'],
                                        'period': kw['period']}))
    out = tmp_path / 'out'
    code = cli.main(['whatif', '--period', '2026-10', '--out', str(out)])
    assert code == 0
    assert 'CONFIG_INCONSISTENT' in capsys.readouterr().out, \
        'redline_delta must be disclosed (V-14)'
    files = [p for p in out.rglob('*') if p.is_file()]
    assert files and all(p.relative_to(out).parts[0] == 'whatif' for p in files)
    assert not (out / '2026-10').exists()


def test_run_id_fresh_dir_never_overwrites(tmp_path, monkeypatch):
    '''[L1091]: identical rerun bytes -> NEW directory; old bytes untouched.'''
    app = _app(eval_config={'weight_construction': {'alpha_grid': [1], 'window': 4}})
    _stub_io(monkeypatch, app)
    monkeypatch.setitem(sys.modules, 'dsm.weights_calibrate', _fake_module(
        'dsm.weights_calibrate', calibrate=lambda **kw: {'alpha_star': '1'}))
    out = tmp_path / 'out'
    argv = ['calibrate', '--period', '2026-10', '--out', str(out),
            '--run-at', '2026-11-05T09:00:00']
    assert cli.main(argv) == 0
    first = sorted(p for p in (out / 'calibrate').iterdir() if p.is_dir())
    before = {p.name: p.read_bytes() for p in first[0].rglob('*.json')}
    assert cli.main(argv) == 0
    second = sorted(p for p in (out / 'calibrate').iterdir() if p.is_dir())
    assert len(second) == 2 and second[0] == first[0], 'rerun must not reuse a dir'
    for name, blob in before.items():
        assert (second[0] / name).read_bytes() == blob, 'history was overwritten'


FORBIDDEN_IMPORTS = frozenset((
    'decimal', 'math', 'statistics', 'random', 'numpy', 'fractions',  # INV-2
    'socket', 'urllib', 'http', 'ftplib', 'smtplib', 'poplib', 'imaplib',  # V-10
    'sqlite3', 'subprocess', 'threading', 'multiprocessing', 'asyncio',
    'sched', 'time'))


def test_inv2_no_inlined_algorithms_v10_offline():
    '''Source guards: INV-2 (no numeric algorithm packages; every dsm dep
    lazy) + V-10 (offline: no net/db/scheduler) + H-8 (single _now() clock
    point, injected via --run-at otherwise).'''
    source = (REPO / 'dsm' / 'cli.py').read_text(encoding='utf-8')
    tree = ast.parse(source)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(a.name.split('.')[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split('.')[0])
    assert not (roots & FORBIDDEN_IMPORTS), 'forbidden import roots: ' + repr(
        sorted(roots & FORBIDDEN_IMPORTS))
    assert 'dsm' in roots
    for node in ast.walk(tree):
        assert not (isinstance(node, ast.ImportFrom)
                    and (node.module or '').startswith('dsm.')), \
            'INV-2: cross-dsm imports must go through the lazy _import_dep seam'
    now_attrs = [n for n in ast.walk(tree)
                 if isinstance(n, ast.Attribute) and n.attr == 'now']
    assert len(now_attrs) == 1, 'exactly one clock read: _now() ([L1550], H-8)'
    now_fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == '_now')
    assert any(isinstance(n, ast.Attribute) and n.attr == 'now' for n in ast.walk(now_fn))
    assert cli.PLACEHOLDER == 'PLACEHOLDER'  # [L878] no invented values