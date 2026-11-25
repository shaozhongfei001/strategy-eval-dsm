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

    def audit_context(self, loaded, app=None, *, weight_version_id=None,
                      score_card=(), grade_ledger=()):
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
        # [L1051] item 15 的 PLACEHOLDER 消除（P2-cli 上报第 11 条⑦）：真源是
        # dsm/audit.py:242 的 reproducibility_hash(score_card, grade_ledger,
        # weight_version_id)，本 shell 只调用不重算（R-7）。preflight 的 BLOCK 路径没有
        # score_card / grade_ledger（[L917] 连空文件都不产），故按 [L1054]「失败的运行也是
        # 一次普通输入」用本次真实的（空）产物 + 签认的 weight_version_id 算出该次运行的哈希；
        # weight_version_id 拿不到 -> [L1080] 退出码 3，绝不用 PLACEHOLDER 字面量冒充
        # （PLACEHOLDER 的意思是「未签认的业务值」[L878]，不是「shell 算不出」，V-14）。
        wvid = weight_version_id
        if wvid is None:
            wvid = _signed_weight_version_id(app if app is not None else self.args.config)
        if wvid is None:
            raise CliError('reproducibility_hash ([L1051] item 15 / [L1052]) needs the signed '
                           'weight_version_id: the caller passed none and --config '
                           + repr(self.args.config) + ' does not hold exactly one weights_*.yaml '
                           'to take it from; the CLI invents no version id (R-12) and writes no '
                           'PLACEHOLDER into a computable digest column (V-14)', EXIT_CONFIG)
        digest = _attr(audit, 'reproducibility_hash', 'audit_context')
        return {'run_id': self.run_id, 'run_at': self.run_at,
                'dsm_version': dsm.__version__, 'design_version': dsm.DESIGN_DOC_VERSION,
                # cel_contract_version 保持 PLACEHOLDER：SDD [L1897] 明文「首版固定为占位版本」，
                # 而 [L1795] G8 的「DSM 设计版本 + CEL 契约版本 + fixtures/golden 版本号」三者
                # 绑定尚未发布 -> 契约原文没有可取的版本串，编一个即违 R-12。
                'cel_contract_version': PLACEHOLDER, 'config_snapshot_sha256': snapshot,
                'seed': self.args.seed, 'input_fingerprints': dict(loaded.fingerprints),
                'sensitivity_schemes': (),
                'reproducibility_hash': digest(tuple(score_card), tuple(grade_ledger), wvid)}

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

def _anchor_set_doc(app):
    '''T8 anchor_set 在 shell 侧的**唯一**取法（A1d NEED-WIRING §3 / [L877]）：来源是
    config 层加载的 AnchorSetDoc，**不是** io_loaders.Inputs —— Inputs
    （dsm/io_loaders.py:149-159）只有 strategy_master / metric_dict / metric_facts /
    design_cards / redlines / previous_ledger 六项，没有 anchor_set；ATT-1
    NEED-WIRING 表格第 4 行「传 Step1 已加载的 inputs.anchor_set」的措辞有误，照抄
    会 AttributeError。spine 侧的同一对象由 tests/test_integration_spine.py:137 的
    _governance_docs() 给出（AnchorSetDoc(**anchor_set.jsonl[0])），Step1
    attainment.compute(anchor_set=...) 与 Step2 normalize.compute 的第 3 位入参用的
    就是它（[L941] 锚定集优先 / ERRATUM-08 / ORCH-40 R4），故两处必须同源同对象，
    shell 不另开第二个来源（口径唯一）。
    签认配置里没有 anchor_set -> 返回 None，由 dsm/preflight.py:344 显式披露
    「未提供 anchor_set（T8），无锚定基准」：降级带披露位，不是静默降级（V-14）。
    shell 绝不自己编一份锚定集顶上去（R-12）。
    ⚠️ Step1 的**生产调用点**尚不存在：M29 L1330-1358 九步 marshal 未落地，
    _chain_gate 在模块齐全时仍 raise InvariantError（退出码 5，INV-2 禁止 shell
    内联任何一步）。marshal 落地时必须把本函数的返回值同时喂给
    attainment.compute(anchor_set=...) 与 normalize.compute(..., anchor_set, ...)。'''
    models = _require('dsm.models')
    anchor = getattr(app, 'anchor_set', None)
    if not anchor:
        return None
    return models.AnchorSetDoc.model_validate(anchor)


def _signed_weight_version_id(app):
    '''[L1052] 的 weight_version_id 只从签认配置树里取：恰好一份 weights 文档时取它的
    weight_version_id；0 份或多份一律 None，由调用方按 [L1080] 退出码 3 拒绝。shell 不挑一份、
    不编一个（R-12 / V-14）。'''
    weights = dict(getattr(app, 'weights', None) or {})
    if len(weights) != 1:
        return None
    doc = weights[sorted(weights)[0]] or {}
    value = (doc.get('weight_version_id') if isinstance(doc, dict)
             else getattr(doc, 'weight_version_id', None))
    return None if value in (None, '') else str(value)


def _context_weight_version_id(preflight_config):
    '''cmd_preflight 已经把签认的 WeightVersionDoc 解析进 PreflightConfig（[L900] C-01 的
    载体），audit_context 的 [L1052] 哈希就从这里取同一个 id，不另开一个来源（口径唯一）。'''
    doc = getattr(preflight_config, 'weight_version', None)
    value = getattr(doc, 'weight_version_id', None)
    return None if value in (None, '') else str(value)


def _evaluation_scope(loaded):
    '''EVID-1 / ORCH-37 第 9 条的范围披露接线（[L1063] ②「本期评价范围与覆盖率」与 ⑥
    「证据结构」）：范围口径的唯一实现是 dsm/evidence.py:204 的 evaluation_scope，本 shell 只把
    T4 设计卡与 T3 事实行两个 [L891] 载体交给它，绝不自己重算一遍范围（INV-2 / R-7，也正是
    evidence.classify docstring 要求的「调用侧要披露时请调 evaluation_scope」）。
    载体缺列 -> [L1080] 退出码 4（M21 L892），不塞空元组冒充「本期无卡」（V-14）。'''
    ev = _require('dsm.evidence')
    inputs = getattr(loaded, 'inputs', None)
    cards = getattr(inputs, 'design_cards', None)
    facts = getattr(inputs, 'metric_facts', None)
    absent = [n for n, v in (('design_cards', cards), ('metric_facts', facts)) if v is None]
    if absent:
        raise CliError('evaluation_scope ([L1063] ②) needs the T4 design_cards and the T3 '
                       'metric_facts carriers of [L891]; io_loaders returned no '
                       + ', '.join(absent) + ' and no empty tuple is substituted for them, '
                       'because an empty scope would read as "nothing was filtered out" '
                       'instead of "the period could not be established" (V-14)', EXIT_DATA)
    return _attr(ev, 'evaluation_scope', 'score')(tuple(cards), tuple(facts))


def _previous_pool_stats(loaded):
    '''G-14 的上期基线（dsm_stage/G14FIX/HANDOFF-P2.md §2）：只有两个合法来源 —— 上期同链路
    重算，或上期 audit_bundle 的 pool_stats。九步 marshal（M29 L1330-1358）未落地前第一个来源
    不存在，[L1051] 的 audit_bundle 十六列里也没有 pool_stats 列，故第二个来源同样不存在 ->
    返回 None，由 reports._mix_quality_lines 显式披露「本期不可比」。
    绝不在 shell 侧造假基线，也绝不另写一套 C 占比比较：判据唯一性是
    pooling.mix_quality_verdict（ORCH-36 第 2/4 条），MIX_QUALITY_DEGRADED 是 WARN /
    blocks_run=False，不改退出码、不中断九步。'''
    inputs = getattr(loaded, 'inputs', None)
    carried = getattr(inputs, 'previous_pool_stats', None)
    return None if carried is None else carried


def _report_frames(loaded, **products):
    '''M29 L1330-1358 九步 marshal 的**唯一** reports 形参构造口（HANDOFF-P2 §2）：Step1-8 的
    产物由调用方按名注入，本函数只负责把两个披露载体接上 —— previous_pool_stats（G-14 基线，
    reports.py:419 的 _mix_quality_lines 消费）与 evaluation_scope（[L1063] ②/⑥ 的范围过滤
    披露，reports._section_2 / _section_6 消费）。gate_status 必填（G5/G7 未签认 -> 首屏声明），
    shell 不猜签认状态（R-12）。已注入的同名产物一律不被覆盖（调用方口径优先）。'''
    reports = _require('dsm.reports')
    kwargs = dict(products)
    if kwargs.get('previous_pool_stats', None) is None:
        kwargs['previous_pool_stats'] = _previous_pool_stats(loaded)
    if kwargs.get('evaluation_scope', None) is None:
        kwargs['evaluation_scope'] = _evaluation_scope(loaded)
    return _attr(reports, 'AllFrames', 'score')(**kwargs)


def _render_reports(run, bundle, frames, config):
    '''S6 产物的渲染与写盘：reports.render -> reports.write_report_set（R-7：canonical 序列化、
    产出指纹与 reproducibility_hash 全归 audit.py，shell 一个字节也不重算）。返回
    (fingerprints, details)；details 把两个 V-14 载体的接线结果逐条说出来 —— G-14 基线有无、
    范围过滤几张卡 —— 不静默（[L1051] item 14 降级动作全量 / V-14）。'''
    reports = _require('dsm.reports')
    if run.dir is None:
        run.prod_dir()
    report_set = _attr(reports, 'render', 'score')(bundle, frames, config)
    fingerprints = _attr(reports, 'write_report_set', 'score')(report_set, run.dir)
    details = ['report set written to ' + str(run.dir) + ': '
               + ', '.join(sorted(fingerprints))]
    scope = getattr(frames, 'evaluation_scope', None)
    if scope is None:
        details.append('evaluation_scope: 未注入 -> report.md ②/⑥ 显式披露「本段无数据」'
                       '（V-14，不静默省略）')
    elif not scope.period_established:
        details.append('evaluation_scope: 本期无法界定（事实行为空，一张卡都未被过滤）')
    else:
        details.append('evaluation_scope: in_period=%d，被范围过滤 %d 张设计卡（%s，'
                       'INFO / blocks_run=false，卡本身保留供 G-08）'
                       % (len(scope.in_period), len(scope.excluded),
                          _attr(_require('dsm.reason_codes'), 'RC', 'score')
                          .EV_OUT_OF_EVAL_PERIOD.value))
    previous = getattr(frames, 'previous_pool_stats', None)
    if previous is None:
        details.append('G-14: 无上期 pool_stats 基线 -> report.md ⑥ 显式披露「本期不可比」，'
                       '不得当作「没上升」（V-14；判据唯一性归 pooling.mix_quality_verdict）')
    elif getattr(frames, 'pool_stats', None) is None:
        details.append('G-14: 当期 pool_stats 缺失 -> 判据无从计算，report.md ⑥ 走「本段无数据」'
                       '披露（V-14），shell 不另算一套 C 占比')
    else:
        pooling = _require('dsm.pooling')
        verdict = _attr(pooling, 'mix_quality_verdict', 'score')(frames.pool_stats, previous)
        details.append('G-14: ' + ('C 类占比未上升，无 MIX_QUALITY_DEGRADED 警示'
                                   if verdict is None else
                                   str(getattr(verdict, 'value', verdict))
                                   + '（WARN / blocks_run=false，只披露，不改退出码、'
                                     '不中断九步）'))
    return fingerprints, details


def cmd_preflight(run):
    app = _load_config(run)
    loaded = _load_inputs(run)
    pfc = _build_preflight_config(app, run.args.period)
    run_dir = run.prod_dir()
    code, result, _paths = _require('dsm.preflight').execute(
        loaded.inputs, pfc, str(run_dir),
        # [L1052] 的 weight_version_id 与 C-01 校验用的是同一份签认文档（口径唯一）。
        run.audit_context(loaded, app,
                          weight_version_id=_context_weight_version_id(pfc)))
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
    return config.PreflightConfig(
        period=period,
        period_ref_date=datetime.date.fromisoformat(str(ev['period_ref_date'])),
        weight_version=models.WeightVersionDoc.model_validate(weights[sorted(weights)[0]]),
        anchor_set=_anchor_set_doc(app),
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
