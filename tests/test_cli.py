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
from decimal import Decimal
from pathlib import Path

import pytest

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
    # P2-cli #9: cmd_calibrate now builds a weights_calibrate.CalibrationInputs, whose
    # period_cases are the M29 L1330-1358 nine-step marshal -- a P2-wire deliverable
    # gated on A1c + MODELS-1, so _calibration_inputs refuses explicitly instead of
    # handing calibrate() an empty window. These three tests lock the L0b directory /
    # exit-code discipline only, so the marshal is stubbed here; the marshal and the
    # four ORCH-31 hook injections are locked by the P2-cli tests below. No assertion
    # in this test was changed or relaxed.
    monkeypatch.setattr(cli, '_calibration_inputs', lambda *a, **k: object())
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
    # P2-cli #9: cmd_calibrate now builds a weights_calibrate.CalibrationInputs, whose
    # period_cases are the M29 L1330-1358 nine-step marshal -- a P2-wire deliverable
    # gated on A1c + MODELS-1, so _calibration_inputs refuses explicitly instead of
    # handing calibrate() an empty window. These three tests lock the L0b directory /
    # exit-code discipline only, so the marshal is stubbed here; the marshal and the
    # four ORCH-31 hook injections are locked by the P2-cli tests below. No assertion
    # in this test was changed or relaxed.
    monkeypatch.setattr(cli, '_calibration_inputs', lambda *a, **k: object())
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
    # P2-cli #9: cmd_calibrate now builds a weights_calibrate.CalibrationInputs, whose
    # period_cases are the M29 L1330-1358 nine-step marshal -- a P2-wire deliverable
    # gated on A1c + MODELS-1, so _calibration_inputs refuses explicitly instead of
    # handing calibrate() an empty window. These three tests lock the L0b directory /
    # exit-code discipline only, so the marshal is stubbed here; the marshal and the
    # four ORCH-31 hook injections are locked by the P2-cli tests below. No assertion
    # in this test was changed or relaxed.
    monkeypatch.setattr(cli, '_calibration_inputs', lambda *a, **k: object())
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


# ===========================================================================
# P2-cli (ORCH-36 ruling 6): the six cli deltas that do not depend on fixtures.
# #5 _EXCEPTION_CODES three families / #8 cmd_combine_build elicit_hierarchy /
# #9 cmd_calibrate four L0a hooks / #10 cmd_whatif run_id+input_dir+directory_hash
# and --include-sensitivity / #14 --help exit 0 / #3 no silent pass in
# Run.audit_context. Everything below runs on the synthetic-config path of
# _app() / _stub_io(): config/ holds 0 files on purpose and no business value is
# invented here (K-01~K-20 stay PLACEHOLDER, R-12).
# ===========================================================================
WHATIF = 'dsm.whatif'
WCAL = 'dsm.weights_calibrate'
WCMB = 'dsm.weights_combine'
WAHP = 'dsm.weights_ahp'

HELP_ARGV = (['--help'], ['preflight', '--help'], ['score', '--help'],
             ['sensitivity', '--help'], ['ahp', '--help'], ['ahp', 'build', '--help'],
             ['combine', '--help'], ['combine', 'build', '--help'],
             ['calibrate', '--help'], ['whatif', '--help'], ['fixtures', '--help'],
             ['fixtures', 'gen', '--help'])

# (module, class name, expected exit code). Code = the [L1080]-[L1087] slot the
# raising condition belongs to: 3 config, 4 data (M21 L892 / ORCH-34 ruling 1),
# 5 [L1081] internal invariant, 6 [L1083] CR gate of ahp build, 7 [L1084] alpha.
EXCEPTION_CODE_MAP = (
    (WHATIF, 'WhatifError', 5), (WHATIF, 'WhatifRunIdError', 3),
    (WHATIF, 'WhatifBaselineError', 3), (WHATIF, 'WhatifInputError', 4),
    (WHATIF, 'WhatifPlaceholderError', 3), (WHATIF, 'WhatifStructureError', 3),
    (WHATIF, 'WhatifOperatorError', 3), (WHATIF, 'WhatifAttributionError', 5),
    (WHATIF, 'WhatifConsistencyError', 5), (WHATIF, 'WhatifReadonlyError', 5),
    (WCAL, 'CalibrateError', 5), (WCAL, 'GridError', 3), (WCAL, 'WindowError', 3),
    (WCAL, 'MissingBudgetError', 3), (WCAL, 'GovernanceBudgetTamperError', 5),
    (WCAL, 'HookRequiredError', 5), (WCAL, 'AlphaInfeasibleError', 7),
    (WCAL, 'AlphaFloorInfeasibleError', 7),
    (WCMB, 'CombineError', 5), (WCMB, 'FrozenStatusError', 3),
    (WCMB, 'AlphaFloorError', 3), (WCMB, 'ConsistencyGateError', 3),
    (WCMB, 'AhpInputError', 3), (WCMB, 'AlphaInfeasibleError', 7))

DIM_W = {'D1': '0.6', 'D2': '0.3', 'D3': '0.1'}
METRIC_W = {'D1': {'M1': '0.7', 'M2': '0.3'}, 'D2': {'M3': '0.6', 'M4': '0.4'},
            'D3': {'M5': '0.5', 'M6': '0.5'}}
CAL_BUDGET = {'alpha_floor': '0.5', 'drift_budget': '0.10', 'boundary_budget': '0.10',
              'boundary_epsilon': '0.01', 'stable_max': '0.20',
              'divergence_threshold': '0.20', 'min_dim_weight': '0.05',
              'max_shift_from_ahp': '0.30'}
DRAFT_DOC = {'status': 'DRAFT', 'weight_version_id': 'WV-D', 'approved_by': 'tester',
             'approved_date': '2026-01-05', 'effective_from': '2026-01-01',
             'effective_to': '2026-12-31'}


def _consistent(weights):
    '''A perfectly consistent pairwise matrix, a_ij = w_i / w_j, so CR = 0 ([L518]).
    Synthetic test data only -- no signed judgement value is invented (R-12).'''
    keys = sorted(weights)
    w = {k: Decimal(weights[k]) for k in keys}
    return {'E1': {i: {j: str((w[i] / w[j]).quantize(Decimal('1.00000000000000000000')))
                    for j in keys} for i in keys}}


def _ahp_tree():
    return {'dimension': _consistent(DIM_W),
            'metrics_by_dim': {d: _consistent(METRIC_W[d]) for d in sorted(METRIC_W)},
            'interview_dates': []}


def _combine_app(**over):
    base = {'ahp_matrices': _ahp_tree(), 'weights': {'weights_WV-D': dict(DRAFT_DOC)},
            'eval_config': {'weight_construction': {'alpha': '1',
                                                    'min_dim_weight': '0.05',
                                                    'shift': '1'}}}
    base.update(over)
    return _app(**base)


def _stub_loaded(monkeypatch, app, metric_dict=None, metric_facts=()):
    monkeypatch.setattr(cli, '_load_config', lambda run: app)
    monkeypatch.setattr(cli, '_load_inputs', lambda run: types.SimpleNamespace(
        inputs=types.SimpleNamespace(
            metric_dict=({'metric_id': 'M1'},) if metric_dict is None else metric_dict,
            metric_facts=metric_facts),
        fingerprints={}))


# --------------------------------------------------------------- #14 --help
@pytest.mark.parametrize('argv', HELP_ARGV,
                         ids=lambda a: '_'.join(x.strip('-') for x in a[:-1]) or 'ROOT')
def test_help_exits_0_for_every_subcommand(argv, capsys):
    '''P2-cli #14: argparse answers -h/--help through parser.exit() -> SystemExit(0).
    main() caught it in "except BaseException" and exit_code_for had no slot for
    SystemExit, so all 12 invocations printed the help text and then reported
    exit=5 status=INTERNAL -- the help was dressed up as an [L1081] invariant
    violation, the same masquerade cli.py L10 forbids for argparse's native 2.
    A request to stop is re-raised with its own code, so --help exits 0.'''
    with pytest.raises(SystemExit) as excinfo:
        cli.main(list(argv))
    assert excinfo.value.code == 0, 'help must exit 0, not the mapped internal 5'
    assert capsys.readouterr().out.startswith('usage:'), 'the help text still prints'


def test_usage_error_still_exits_3_not_a_reraised_systemexit(tmp_path, capsys):
    '''The #14 fix must not reopen the hole cli.py L10 closes: _Parser.error raises
    CliUsage, so a bad invocation is still [L1080] exit 3 and never argparse's 2.'''
    assert cli.main(['score', '--period', '2026-10', '--nope', '--out',
                     str(tmp_path)]) == 3
    assert 'exit=2' not in capsys.readouterr().out


# ------------------------------------------------------- #5 _EXCEPTION_CODES
@pytest.mark.parametrize('module,name,code', EXCEPTION_CODE_MAP)
def test_exception_codes_cover_the_three_families(module, name, code):
    '''P2-cli #5: M27 [L1084]-[L1086] gives calibrate 0/3/7, combine build 0/3 and
    whatif 0/3/4, yet every class of those three modules used to fall through to
    EXIT_INTERNAL. Each is now mapped by NAME (so the map still holds for a module
    landing later) to the slot its own docstring / registered reason_code puts it
    in -- asserted against the REAL classes, not against look-alikes.'''
    klass = getattr(importlib.import_module(module), name)
    assert cli.exit_code_for(klass('P2-cli probe')) == code


def test_unmapped_family_member_keeps_the_base_slot():
    '''exit_code_for walks type(exc).__mro__ outer first, so a subclass entry wins
    over its family base and an unmapped subclass still lands on the base slot
    instead of on an unrelated code.'''
    whatif = importlib.import_module(WHATIF)
    assert cli.exit_code_for(whatif.WhatifReadonlyError('probe')) == 5
    assert cli.exit_code_for(whatif.WhatifError('probe')) == 5

    class UnmappedChild(whatif.WhatifError):
        pass

    assert cli.exit_code_for(UnmappedChild('probe')) == 5


def test_entropy_insufficient_sample_is_deliberately_unmapped():
    '''M42 L1071 / the class docstring: run_six_steps CATCHES EntropyInsufficientSample
    and degrades to alpha = 1 with a prominent label, so it never reaches this shell
    and the digest gives it no exit-code slot of its own. It stays out of the map and
    keeps the documented [L1081] fallback -- inventing a slot would be R-12, and
    P2PREP P-2 stays open for it.'''
    wc = importlib.import_module(WCMB)
    assert not any(n == 'EntropyInsufficientSample' for n, _ in cli._EXCEPTION_CODES)
    assert cli.exit_code_for(wc.EntropyInsufficientSample('probe')) == cli.EXIT_INTERNAL


def test_whatif_consistency_error_is_not_the_ahp_cr_gate():
    '''[L1083] gives exit 6 to "dsm ahp build" only. whatif's WhatifConsistencyError is
    a program defect (the preview arm disagrees with production Step 5/6), not a CR
    gate, so it must not inherit the 6 of ConsistencyFailedError.'''
    whatif = importlib.import_module(WHATIF)
    ahp = importlib.import_module(WAHP)
    assert cli.exit_code_for(whatif.WhatifConsistencyError('probe')) == 5
    assert cli.exit_code_for(ahp.ConsistencyFailedError('probe', None)) == 6, \
        'the [L1083] CR gate keeps its own slot 6 and does not bleed into whatif'


# --------------------------------------------------- #9 the four L0a hooks
def test_calibrate_injects_exactly_the_four_l0a_hooks():
    '''ORCH-31 p2_signature_deltas_from_ARCH1 item 2 verbatim: combine_fn / options_fn /
    entropy_window_fn / insufficient_sample_error, all four read off dsm.weights_combine
    -- the L0a side [L294] forbids weights_calibrate to import. The key set is
    HOOK_NAMES, so a rename on either side fails here instead of at run time.'''
    wc, wcal = importlib.import_module(WCMB), importlib.import_module(WCAL)
    hooks = cli._calibrate_hooks(wc)
    assert sorted(hooks) == sorted(wcal.HOOK_NAMES)
    assert hooks['combine_fn'] is wc.combine
    assert hooks['options_fn'] is wc.CombineOptions
    assert hooks['entropy_window_fn'] is wc.calibrate_entropy_window
    assert hooks['insufficient_sample_error'] is wc.EntropyInsufficientSample
    assert all(callable(v) for v in hooks.values()), 'a non-callable hook is a HookRequiredError'


@pytest.mark.parametrize('hook', ('combine_fn', 'options_fn', 'entropy_window_fn',
                                  'insufficient_sample_error'))
def test_calibrate_missing_hook_raises_hook_required(hook):
    '''The injection is load-bearing: hand the real CalibrationInputs a hole where one of
    the four belongs and the real weights_calibrate.calibrate refuses with
    HookRequiredError (V-14 -- nothing is imported to fill it, no indicator is skipped).
    CAL_BUDGET holds synthetic structural values so governance_budget() can be passed;
    no signed K-15~K-20 value is asserted or invented (R-12).'''
    wc, wcal = importlib.import_module(WCMB), importlib.import_module(WCAL)
    hooks = cli._calibrate_hooks(wc)
    hooks[hook] = None
    inputs = wcal.CalibrationInputs(hierarchy=None, metric_dict=(), shift='1',
                                    period_cases={}, run_id='cal-p2cli-1', **hooks)
    app = _app(eval_config={'weight_construction': dict(CAL_BUDGET)})
    with pytest.raises(wcal.HookRequiredError) as excinfo:
        wcal.calibrate(grid=['0.5'], window=['P1', 'P2'], inputs=inputs, config=app)
    assert hook in str(excinfo.value), 'the refusal must name the missing injection'


def test_calibrate_names_a_missing_l0a_symbol_instead_of_falling_back(tmp_path,
                                                                     monkeypatch,
                                                                     capsys):
    '''V-14 / ORCH-29 ruling 3: no import fallback. A weights_combine that lost one of the
    four L0a capabilities makes cmd_calibrate fail with an explicit ModuleMissingError
    naming the entry point, rather than handing calibrate() a None it would refuse
    later with a message that does not say which module is broken.'''
    app = _combine_app(eval_config={'weight_construction': {
        'alpha_grid': ['0.5'], 'window': ['P1', 'P2'], 'shift': '1'}})
    _stub_loaded(monkeypatch, app)
    monkeypatch.setattr(cli, '_elicit_hierarchy', lambda *a: object())
    monkeypatch.setitem(sys.modules, WCMB, _fake_module(
        WCMB, CombineOptions=object, calibrate_entropy_window=lambda *a: None,
        EntropyInsufficientSample=Exception))       # 'combine' is absent on purpose
    out = tmp_path / 'out'
    assert cli.main(['calibrate', '--period', '2026-10', '--out', str(out)]) == 5
    printed = capsys.readouterr().out
    assert 'dsm.weights_combine.combine' in printed and 'Traceback' not in printed


def test_calibrate_refuses_an_unsigned_shift(tmp_path, monkeypatch, capsys):
    '''R-9 / P-1: [L540] shift is a technical epsilon the digest states no value for, so
    the shell demands it from the signed config and refuses with [L1080] exit 3 when it
    is absent. weights_calibrate.py:708-709 says it in so many words: "no value is
    invented (R-12)".'''
    app = _combine_app(eval_config={'weight_construction': {'alpha_grid': ['0.5'],
                                                            'window': ['P1', 'P2']}})
    _stub_loaded(monkeypatch, app)
    out = tmp_path / 'out'
    assert cli.main(['calibrate', '--period', '2026-10', '--out', str(out)]) == 3
    printed = capsys.readouterr().out
    assert 'shift' in printed and '[L540]' in printed
    assert not list(out.rglob('calibration_report*')), 'a refused run writes no report'


def test_calibrate_refuses_an_empty_window_rather_than_degrading(tmp_path, monkeypatch,
                                                                 capsys):
    '''V-14: an empty period_cases mapping would make calibrate() answer with the [L634]
    alpha = 1 degrade, i.e. a report that looks calibrated although no period was ever
    backtested. The shell refuses explicitly ([L1081] exit 5) and names the gate.'''
    app = _combine_app(eval_config={'weight_construction': {'alpha_grid': ['0.5'],
                                                            'window': ['P1', 'P2'],
                                                            'shift': '1'}})
    _stub_loaded(monkeypatch, app)
    out = tmp_path / 'out'
    assert cli.main(['calibrate', '--period', '2026-10', '--out', str(out)]) == 5
    printed = capsys.readouterr().out
    assert 'PeriodCase' in printed and 'P2-wire' in printed
    assert not list(out.rglob('calibration_report*'))


# ------------------------------------------------- #8 cmd_combine_build
def test_combine_build_owns_the_l0a_edge(monkeypatch, tmp_path, capsys):
    '''ORCH-31 item 1: build_draft takes six positional arguments plus the keyword-only
    elicit_hierarchy, and the shell -- the only layer allowed to see both L0a modules
    (ORCH-26/27) -- owns that edge. The real weights_ahp.elicit_hierarchy product is
    converted per level with the real AhpLevelSnapshot.from_payload(res.segment_payload(),
    res.findings), so what build_draft receives IS a real AhpHierarchySnapshot.'''
    wc = importlib.import_module(WCMB)
    captured = {}

    def fake_build_draft(matrices, facts, metric_dict, opts, header, shift, *,
                         elicit_hierarchy):
        captured['call'] = (matrices, facts, metric_dict, opts, header, shift)
        captured['hierarchy'] = elicit_hierarchy(
            matrices['dimension'], matrices['metrics_by_dim'], ())
        return {'status': 'DRAFT', 'weight_version_id': header.weight_version_id}

    monkeypatch.setattr(wc, 'build_draft', fake_build_draft)
    facts = (types.SimpleNamespace(period='P1', metric_id='M1', strategy_id='S1',
                                   value=Decimal('3'), data_quality_flag='OK'),
             types.SimpleNamespace(period='P1', metric_id='M1', strategy_id='S2',
                                   value=Decimal('9'), data_quality_flag='SUSPECT'))
    _stub_loaded(monkeypatch, _combine_app(), metric_facts=facts)
    out = tmp_path / 'out'
    assert cli.main(['combine', 'build', '--out', str(out)]) == 0

    hierarchy = captured['hierarchy']
    assert isinstance(hierarchy, wc.AhpHierarchySnapshot), \
        'elicit_hierarchy must return wc.AhpHierarchySnapshot (ORCH-31 item 1)'
    assert isinstance(hierarchy.dimension, wc.AhpLevelSnapshot)
    assert sorted(hierarchy.metrics_by_dim) == sorted(METRIC_W)
    assert all(isinstance(v, wc.AhpLevelSnapshot) for v in hierarchy.metrics_by_dim.values())
    assert hierarchy.dimension.cr < Decimal('0.1'), 'the real CR gate ran ([L573])'

    matrices, facts_history, metric_dict, opts, header, shift = captured['call']
    assert facts_history == {'P1': {'M1': {'S1': Decimal('3')}}}, \
        'SUSPECT rows are dropped ([L1151] C-06) and values travel untouched (V-9)'
    assert isinstance(opts, wc.CombineOptions) and opts.alpha == Decimal(1)
    assert isinstance(header, wc.DraftHeader)
    assert header.weight_version_id == 'WV-D' and header.approved_by == 'tester'
    assert header.effective_from.isoformat() == '2026-01-01', 'no clock is read (H-8)'
    assert shift == '1', 'shift is forwarded from the signed config, never a literal'
    report = next((out / 'combine').rglob('weights_draft-*.json'))
    assert {p.relative_to(out).parts[0] for p in out.rglob('*') if p.is_file()} == {'combine'}
    run_id = _first_line(capsys).split('run_id=')[1].split()[0]
    assert run_id in report.name, 'run_id must be in the file name [L301]'


def test_combine_build_refuses_an_elicit_hierarchy_that_is_no_snapshot(monkeypatch,
                                                                      tmp_path, capsys):
    '''The error path of ORCH-31 item 1: a level that converts to something other than an
    AhpLevelSnapshot would make H-1 of [L594] read a carrier that is not an
    AhpHierarchySnapshot. The shell refuses it at the boundary with an explicit
    [L1081] exit 5 instead of passing the wrong type down (V-14).'''
    class FakeLevel:
        @staticmethod
        def from_payload(payload, findings=()):
            return {'not': 'a snapshot'}          # the wrong product, on purpose

    class FakeCarrier:
        def __init__(self, dimension, metrics_by_dim):
            self.dimension, self.metrics_by_dim = dimension, metrics_by_dim

    class FakeResult:
        findings = ()

        def segment_payload(self):
            return {}

    class FakeHierarchy:
        dimension = FakeResult()
        metrics_by_dim = {'D1': FakeResult()}

    monkeypatch.setitem(sys.modules, WCMB, _fake_module(
        WCMB, AhpLevelSnapshot=FakeLevel, AhpHierarchySnapshot=FakeCarrier,
        SUSPECT='SUSPECT', CombineOptions=lambda **kw: object(),
        DraftHeader=lambda **kw: object(),
        build_draft=lambda *a, **kw: kw['elicit_hierarchy'](a[0]['dimension'],
                                                            a[0]['metrics_by_dim'], ())))
    monkeypatch.setitem(sys.modules, WAHP, _fake_module(
        WAHP, elicit_hierarchy=lambda *a, **k: FakeHierarchy()))
    _stub_loaded(monkeypatch, _combine_app())
    out = tmp_path / 'out'
    assert cli.main(['combine', 'build', '--out', str(out)]) == 5
    printed = capsys.readouterr().out
    assert 'AhpLevelSnapshot' in printed and 'ORCH-31' in printed
    assert not list(out.rglob('weights_draft*')), 'no draft is written on a refusal'


def test_combine_build_refuses_an_ahp_tree_without_the_two_keys(monkeypatch, tmp_path,
                                                                capsys):
    '''[L559] / [L520]: ahp_matrices is {dimension: {expert: A}, metrics_by_dim: ...}.
    A signed tree that carries neither is refused by the shell with the config file
    named, instead of surfacing as a KeyError from inside Step 1.'''
    app = _combine_app(ahp_matrices={'dimension_matrices': _consistent(DIM_W)})
    _stub_loaded(monkeypatch, app)
    out = tmp_path / 'out'
    assert cli.main(['combine', 'build', '--out', str(out)]) == 3
    printed = capsys.readouterr().out
    assert 'dimension' in printed and 'metrics_by_dim' in printed


def test_combine_build_refuses_an_unsigned_shift(tmp_path, monkeypatch, capsys):
    '''R-9: the same [L540] epsilon discipline as calibrate -- demanded from the signed
    config, refused with exit 3, never written as a literal in the shell.'''
    app = _combine_app(eval_config={'weight_construction': {'alpha': '1',
                                                            'min_dim_weight': '0.05'}})
    _stub_loaded(monkeypatch, app)
    out = tmp_path / 'out'
    assert cli.main(['combine', 'build', '--out', str(out)]) == 3
    assert '[L540]' in capsys.readouterr().out


def test_combine_build_refuses_a_missing_metric_dict(tmp_path, monkeypatch, capsys):
    '''V-14: Step 2 reads T2 ([L891]). An empty dictionary is not substituted for a
    metric_dict io_loaders did not return -- that would silently produce the [L577]
    pure-AHP degrade and label it a combined draft.'''
    _stub_loaded(monkeypatch, _combine_app(), metric_dict=())
    out = tmp_path / 'out'
    assert cli.main(['combine', 'build', '--out', str(out)]) == 4
    assert 'metric_dict' in capsys.readouterr().out


# ------------------------------------------------- #10 cmd_whatif
def _stub_whatif(monkeypatch, captured):
    def fake_run(**kw):
        captured.update(kw)
        return {'redline_delta': []}

    monkeypatch.setitem(sys.modules, WHATIF, _fake_module(WHATIF, run=fake_run))
    app = _app(weights={'weights_WV-D': {'status': 'DRAFT'},
                        'weights_WV-F': {'status': 'FROZEN'}})
    _stub_io(monkeypatch, app)


def test_whatif_supplies_run_id_input_dir_and_directory_hash(monkeypatch, tmp_path,
                                                             capsys):
    '''P2-cli #10: dsm/whatif.py:664-665 has five keyword-only parameters and the shell
    passed none. run_id is the sign-off-chain preview id (_check_run_id refuses None,
    [L1241]); input_dir + directory_hash are the INV-2 read-only pair, given together,
    the hash an INJECTED callable (ORCH-27 D-A4-01, whatif.py:814-817).'''
    captured = {}
    _stub_whatif(monkeypatch, captured)
    data = tmp_path / 'data'
    data.mkdir()
    (data / 't3.csv').write_text('a,b\n1,2\n', encoding='utf-8', newline='\n')
    out = tmp_path / 'out'
    assert cli.main(['whatif', '--period', '2026-10', '--data', str(data),
                     '--out', str(out)]) == 0
    run_id = _first_line(capsys).split('run_id=')[1].split()[0]
    assert captured['run_id'] == run_id and captured['run_id'].strip()
    assert captured['input_dir'] == str(data)
    assert callable(captured['directory_hash']), 'the hash must be injected, not built in L0b'
    assert (captured['candidate'], captured['baseline']) == ('weights_WV-D', 'weights_WV-F')
    assert captured['include_sensitivity'] is False and captured['schemes'] == \
        ('OAT_10', 'OAT_20', 'LOO'), '[L1554] trio, and Step 8 stays off unless asked'
    digest = captured['directory_hash'](str(data))
    assert len(digest) == 64 and digest == captured['directory_hash'](str(data))
    (data / 't3.csv').write_text('a,b\n1,3\n', encoding='utf-8', newline='\n')
    assert captured['directory_hash'](str(data)) != digest, \
        'the read-only proof must notice a single changed byte (INV-2)'


def test_whatif_include_sensitivity_flag(monkeypatch, tmp_path, capsys):
    '''[L645] "[--include-sensitivity]": the flag reaches whatif.run as include_sensitivity
    with the scheme list it names, and an empty list is a usage error -- whatif.py:754-755
    refuses it, and the shell refuses it earlier so no run directory is created.'''
    captured = {}
    _stub_whatif(monkeypatch, captured)
    out = tmp_path / 'o1'
    assert cli.main(['whatif', '--period', '2026-10', '--include-sensitivity',
                     '--schemes', 'OAT_10, LOO', '--out', str(out)]) == 0
    assert captured['include_sensitivity'] is True
    assert captured['schemes'] == ('OAT_10', 'LOO')
    out2 = tmp_path / 'o2'
    assert cli.main(['whatif', '--period', '2026-10', '--include-sensitivity',
                     '--schemes', ' , ', '--out', str(out2)]) == 3
    assert '--schemes' in capsys.readouterr().out
    assert not list(out2.rglob('whatif_report*')), 'a refused run writes no report'
    # [L1091]: a failing command DOES leave an audit_bundle and INV-2 keeps it inside the
    # whatif/ group; what the earlier check buys is that no Step 8 artifact of a run
    # nobody asked for is produced before the refusal.
    groups = {p.relative_to(out2).parts[0] for p in out2.rglob('*') if p.is_file()}
    assert groups <= {'whatif'}, 'the failure bundle stays in the L0b group: ' + repr(groups)


def test_directory_hash_is_built_from_audit_primitives_only(tmp_path):
    '''P-3: the digest convention is fixed and reproducible -- sha256_bytes per file, then
    canonical_text ([L1053] rules 3-4 give the deterministic ordering) and sha256_text
    over that. The shell re-implements no hash (R-7) and whatif.py imports no L6.'''
    audit = importlib.import_module('dsm.audit')
    roots = []
    for name in ('a', 'b'):
        root = tmp_path / name
        root.mkdir()
        roots.append(root)
    for first, second in ((roots[0], 'x'), (roots[1], 'y')):
        pass
    (roots[0] / 'z.csv').write_text('2\n', encoding='utf-8', newline='\n')
    (roots[0] / 'a.csv').write_text('1\n', encoding='utf-8', newline='\n')
    (roots[1] / 'a.csv').write_text('1\n', encoding='utf-8', newline='\n')
    (roots[1] / 'z.csv').write_text('2\n', encoding='utf-8', newline='\n')
    assert cli._directory_hash(roots[0]) == cli._directory_hash(roots[1]), \
        'the digest is creation-order independent (canonical_text sorts)'
    assert cli._directory_hash(roots[0]) == audit.sha256_text(audit.canonical_text(
        {'a.csv': audit.sha256_bytes(b'1\n'), 'z.csv': audit.sha256_bytes(b'2\n')}))


def test_directory_hash_refuses_a_missing_root(tmp_path):
    '''V-14: a root that does not exist is refused, not hashed as an empty manifest --
    a proof over nothing would certify nothing and still read as a passed self-proof.'''
    with pytest.raises(cli.CliError) as excinfo:
        cli._directory_hash(tmp_path / 'absent')
    assert excinfo.value.exit_code == cli.EXIT_DATA
    assert 'INV-2' in str(excinfo.value)


# ------------------------------------------------- #3 no silent pass
def _stub_preflight(monkeypatch):
    _stub_io(monkeypatch)
    monkeypatch.setattr(cli, '_build_preflight_config', lambda app, period: object())
    monkeypatch.setitem(sys.modules, 'dsm.preflight', _fake_module(
        'dsm.preflight',
        execute=lambda i, c, d, x: (0, types.SimpleNamespace(status='PASS',
                                                             findings=()), ())))


def test_audit_context_carries_a_real_digest_never_a_placeholder(monkeypatch):
    '''[L1051] item 8 is computable from the signed config, so it is computed: the old
    "except (...): pass" left PLACEHOLDER in the column whenever anything at all went
    wrong, which reads as "unsigned value" ([L878]) and hides the failure (V-14).'''
    run = cli.Run(cli.build_parser().parse_args(['preflight', '--period', '2026-10']))
    ctx = run.audit_context(types.SimpleNamespace(fingerprints={}), _app())
    digest = ctx['config_snapshot_sha256']
    assert digest != cli.PLACEHOLDER and len(digest) == 64
    assert int(digest, 16) >= 0, 'a sha256 hex digest'


def test_audit_context_raises_with_the_mapped_code(tmp_path, monkeypatch, capsys):
    '''P2-cli #3: each failure of config_snapshot_sha256 now surfaces with the code its
    own type maps to and names the column, the --config and the exception type. The last
    case is an exception the map does not know: it must fail explicitly on [L1081] 5,
    never pass silently.'''
    _stub_preflight(monkeypatch)

    def boom_oserror(config):
        raise OSError('EACCES reading the signed config tree')

    def boom_runtime(config):
        raise RuntimeError('unclassifiable failure')

    out = tmp_path / 'o1'
    monkeypatch.setitem(sys.modules, 'dsm.audit',
                        _fake_module('dsm.audit', config_snapshot_sha256=boom_oserror))
    assert cli.main(['preflight', '--period', '2026-10', '--out', str(out)]) == 3
    printed = capsys.readouterr().out
    assert 'config_snapshot_sha256' in printed and 'OSError' in printed
    assert 'status=CONFIG' in printed

    out2 = tmp_path / 'o2'
    monkeypatch.setitem(sys.modules, 'dsm.audit',
                        _fake_module('dsm.audit', config_snapshot_sha256=boom_runtime))
    assert cli.main(['preflight', '--period', '2026-10', '--out', str(out2)]) == 5
    printed = capsys.readouterr().out
    assert 'RuntimeError' in printed and 'config_snapshot_sha256' in printed
    assert 'uncomputed' in printed, \
        'the refusal says the column is uncomputed, not that it holds a value'

    out3 = tmp_path / 'o3'
    real_import = importlib.import_module

    def no_audit(dotted):
        if dotted == 'dsm.audit':
            raise ModuleNotFoundError("No module named 'dsm.audit'")
        return real_import(dotted)

    monkeypatch.setattr(cli, '_import_dep', no_audit)
    assert cli.main(['preflight', '--period', '2026-10', '--out', str(out3)]) == 5
    printed = capsys.readouterr().out
    assert 'dsm.audit' in printed and 'Traceback' not in printed
