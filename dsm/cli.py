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
# ORCH-59（[L1046] / [L1051] item 10）：[L1062] 七件产物里唯一「正文就是 bundle 的
# canonical 序列化」的那件。它的哈希不可能出现在它自己的正文里（自指），故落盘的
# AuditBundle.output_fingerprints 键集恒为 reports.ARTIFACT_NAMES - {AUDIT_ARTIFACT}
# = 六键；audit.json 自身的 SHA256 只经 CLI details / write_report_set 返回值对外披露。
AUDIT_ARTIFACT = 'audit.json'

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

# ---------------------------------------------------------------------------
# M29 [L1325]-[L1358] 九步 marshal 本体（V-14 转正四项的第 2 项）。
#
# INV-2（M00 L301）在 marshal 落地之后含义没有变：shell 一步也不内联。下面每个
# _step* / _*_hook 只做两件事 —— ①把上一步的**真实产物**按 owning module 自己的
# 签名喂进去；②把签认配置里的治理值原样交到该模块手里。算法层（达成率、归一、
# 证据、红线、双轨合成、等级、分池、三角、敏感性、审计、渲染）一行也没重写（R-7）。
#
# 治理值纪律：签认配置里没有的值一律按 [L1080] 退出码 3 拒绝，绝不用默认值顶上去
# （H-5 / R-12 / K-01~K-20）。降级一律带码且进披露行，没有静默分支（V-14）。
# ---------------------------------------------------------------------------
_SCORE_INPUT_CARRIERS = ('strategy_master', 'metric_dict', 'metric_facts',
                         'design_cards', 'redlines')
_GRADE_ORDER = ('L1', 'L2', 'L3', 'L4')           # [L1200] / [L493] 等级枚举
_MC_PREFIX = 'MC'                # [L1017] MC 无 seed 即拒（dsm/sensitivity.py:79-80）
_POLICY_KEY = 'policy'           # T7 的全局滞回段（[L965] 明文默认的签认载体）
_HYSTERESIS_KEYS = ('upgrade_consecutive_periods', 'demotion_immediate')
_RULE_KEYS = ('grade_code', 'attainment_floor')   # dsm/config.py:987 认的同一对键
_SOFT_KEY = 'soft_deductions'     # [L484]「扣减幅度由 grade_rules.yaml 配置」
_K06_KEY = 'min_coverage_for_absolute_track'      # M38 [L1743]：位置 = eval_config
_SWAP_GRAIN = 'SWAP'              # NORM_SWAP 钩子合成载体的占位主键，不含业务语义


def _require_chain_modules():
    '''九步的前置闸（原 _chain_gate 前半，marshal 落地后一字未改）：owning module
    少一个就整条链不跑，逐模块点名、退出码 5（[L1081]），绝不产出半条链的分数
    （V-14 / [L1091]）。'''
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


def _score_inputs(loaded):
    '''[L1330] io_loaders 交出的表载体。少一张 -> [L1080] 退出码 4（M21 L892），
    不塞空元组冒充「本期无数据」（空表会被读成「评了个空期」，正是 V-14 禁止的
    静默降级）。T6/T7/T8 是 YAML，归 config 层（[L877]），不在这里取。'''
    inputs = getattr(loaded, 'inputs', None)
    absent = [name for name in _SCORE_INPUT_CARRIERS
              if getattr(inputs, name, None) is None]
    if absent:
        raise CliError('the nine-step marshal of [L1330]-[L1358] needs the [L891] '
                       'input carriers; io_loaders returned no ' + ', '.join(absent)
                       + ' and no empty tuple is substituted for them (V-14, M21 L892)',
                       EXIT_DATA)
    return inputs


def _eval_tree(app):
    tree = getattr(app, 'eval_config', None)
    if not isinstance(tree, dict) or not tree:
        raise CliError('the marshal reads every governance value out of the signed '
                       'eval_config tree ([L877]); the loaded configuration carries '
                       'no eval_config block, and the CLI invents none of the '
                       'K-01~K-20 values (H-5, R-12)', EXIT_CONFIG)
    return tree


def _governance_block(app, key, step):
    '''eval_config 下的一个签认治理段。缺段 / 空段 -> [L1080] 退出码 3，逐段点名。'''
    block = _eval_tree(app).get(key)
    if not isinstance(block, dict) or not block:
        raise CliError(step + ' needs the signed eval_config.' + key + ' block; the '
                       'configuration carries none and the CLI defaults no governance '
                       'value (H-5, R-12, K-01~K-20)', EXIT_CONFIG)
    return dict(block)


def _min_coverage(app):
    '''K-06（M38 [L1743]：位置 = eval_config，技术参数）。grading.GradeRuleSet 的这一项
    必填且无默认（dsm/grading.py:82-90：属 PLACEHOLDER 治理参数，H-5 不猜业务数），
    所以拿不到就 [L1080] 退出码 3，绝不上一个默认阈值（那会静默移动全系统的封顶线）。'''
    tree = _eval_tree(app)
    value = tree.get(_K06_KEY)
    if value in (None, ''):
        raise CliError('Step6 grading needs the signed K-06 eval_config.' + _K06_KEY
                       + ' ([L1743]); dsm/grading.py:90 makes it mandatory without a '
                       'default, and the CLI invents no coverage threshold (H-5, R-12)',
                       EXIT_CONFIG)
    return value


def _rule_mappings(node, found=None):
    '''grade_rules 树里的规则行收集，口径逐字跟 dsm/config.py:974-987（ruling 14）：
    SDD 从未命名 grade_rules.yaml 的顶层键，所以「任何同时带 grade_code 与
    attainment_floor 的映射，任意深度」就是一条规则行。shell 不另立第二套口径
    （判据唯一性），也不猜顶层键名（R-12）。'''
    found = [] if found is None else found
    if isinstance(node, dict):
        if all(key in node for key in _RULE_KEYS):
            found.append(node)
        for key in sorted(node, key=str):
            _rule_mappings(node[key], found)
    elif isinstance(node, (list, tuple)):
        for item in node:
            _rule_mappings(item, found)
    return found


def _grade_rule_rows(app):
    '''T7 -> Step6 的 GradeRuleRow 元组（[L1196]-[L1206]）。「四级各一条」是
    config.validate_semantics 已经判过的（dsm/config.py:997-1003），这里再点一次名，
    让失败信息说的是 marshal 缺什么，而不是从 Step6 内部抛出一个键错。'''
    models = _require('dsm.models')
    found = _rule_mappings(getattr(app, 'grade_rules', None) or {})
    codes = sorted(str(row.get(_RULE_KEYS[0])) for row in found)
    if codes != sorted(_GRADE_ORDER):
        raise CliError('Step6 grading needs exactly the four [L1200] grade rules '
                       '(L1/L2/L3/L4, one row each) in grade_rules.yaml; the signed '
                       'tree carries ' + (', '.join(codes) or 'nothing')
                       + ' and no grade rule is invented (R-12)', EXIT_CONFIG)
    return tuple(models.GradeRuleRow.model_validate(row) for row in found)

def _sensitivity_config(app):
    '''Step8 的 config 入参。dsm/sensitivity.py:112-135 的 _cfg / _need / _number 直接
    按**块内**键名读 stable_max / review_max / mc_samples / loo_* / norm_swap_*，所以
    交出去的必须是签认的 eval_config.sensitivity 段本身，不是整棵树。K-11 载体 =
    eval_config.sensitivity（M38 [L1748]）。缺段 / 空段 -> [L1080] 退出码 3：自己发明
    一个 review_max 就等于替行方挪动 [L1019] 的首屏否决线（H-5 / R-12）。'''
    return _governance_block(app, 'sensitivity', 'Step8 sensitivity')


def _aggregate_config(app):
    '''Step5 的 config 入参。算子开关的键名 digest 未定，由 aggregate 自己按
    score_operator / operator 两个拼写从映射或命名空间上读（dsm/aggregate.py:20-28
    与 :49），读不到就落它自己的 LINEAR 默认。交出去的是签认的 eval_config 原始树：
    Step5 只读 FROZEN 权重文档（[L1342] / INV-3），算子开关将来若签认也只会有这一个
    落点，shell 不另立第二份口径（判据唯一性），更不在这里替行方选算子（R-12）。'''
    return _eval_tree(app)


def _soft_deductions(app):
    '''[L484]「SOFT 扣减幅度由 grade_rules.yaml 配置」，而 GradeRuleRow 没有这一列
    （dsm/redline.py:16-19 原话：按 ADJ-2 做成必填入参 soft_deductions，缺失即抛错，
    绝不自定数 H-5）。故 shell 从 grade_rules 树的 soft_deductions 映射逐字读出
    metric_id -> 扣减比率；没有这个块就 [L1080] 退出码 3 拒绝，绝不编一个扣减幅度
    顶上去（R-12 / K-01~K-20）。'''
    tree = getattr(app, 'grade_rules', None)
    block = tree.get(_SOFT_KEY) if isinstance(tree, dict) else None
    if not isinstance(block, dict) or not block:
        raise CliError('Step4 redline needs the [L484] SOFT deduction ratios out of '
                       'grade_rules.yaml (key ' + _SOFT_KEY + ', metric_id -> ratio); '
                       'the signed tree carries none and dsm/redline.py:243-249 refuses '
                       'a missing ratio, so the CLI invents no deduction (H-5, R-12)',
                       EXIT_CONFIG)
    numeric = _require('dsm.numeric')
    return dict((str(key), numeric.D(block[key])) for key in sorted(block, key=str))


def _directions(inputs):
    '''旁路 triangulation 的必填注入（dsm/triangulation.py:432-441：三个入参都没有
    direction 列，理想解与参考序列都要方向）。唯一合法来源是 T2 指标字典自己签认的
    direction 列（[L1137]）；shell 不按数据形状猜方向（R-12）。'''
    out = {}
    for row in inputs.metric_dict:
        out[row.metric_id] = int(row.direction)
    if not out:
        raise CliError('triangulation needs the [L1137] direction column of the T2 '
                       'metric_dict; io_loaders returned an empty dictionary and no '
                       'direction is guessed from the data shape (R-12, V-14)',
                       EXIT_DATA)
    return out


def _previous_grade_frame(loaded):
    '''Step6 的 prev（滞回 + 版本断点，[L1344]）。合法载体只有上期的 GradeFrame；
    io_loaders 的 previous_ledger 是 T9 的 GradeLedgerRow（[L890]），没有
    grade_reason_path / capped / cap_reason / usable_for_elimination 四列，转不成
    GradeRow，硬转就是编造（R-12）。当前 _load_inputs 不传 previous_period，故恒为空
    -> prev=None，由 grading 自己落 FIRST_PERIOD（注册 INFO 码；dsm/io_loaders.py:321-331
    「a missing one is FIRST_PERIOD and nothing else」）—— 有码的披露，不是静默。
    一旦出现非空的 previous_ledger，marshal 显式拒绝，而不是把滞回状态悄悄丢掉（V-14）。'''
    rows = tuple(getattr(getattr(loaded, 'inputs', None), 'previous_ledger', ()) or ())
    if rows:
        raise CliError('Step6 hysteresis needs the previous period as a GradeFrame; '
                       'io_loaders carried ' + str(len(rows)) + ' T9 grade_ledger rows '
                       'instead ([L890]), and those have no grade_reason_path / capped '
                       '/ cap_reason column, so the CLI converts no carrier it does '
                       'not own (R-12). Re-run the previous period or wire '
                       '--previous-period; dropping the streak state silently is the '
                       'degradation V-14 forbids', EXIT_DATA)
    return None


def _wanted_schemes(run, sensitivity):
    '''[L1089] / [L1554]：dsm score 没有 --schemes，跑 sensitivity.SCHEME_ORDER 的全部
    五个方案（[L1350] OAT / MC / LOO / NORM_SWAP）；dsm sensitivity 用它自己的
    --schemes（cmd_sensitivity 已校验非空）。方案名合不合法一律交给
    sensitivity._ordered_schemes 判（dsm/sensitivity.py:288-295），shell 不另立名单。'''
    text = getattr(run.args, 'schemes', None)
    if text is None:
        order = getattr(sensitivity, 'SCHEME_ORDER', None)
        if not isinstance(order, tuple) or not order:
            raise ModuleMissingError('Step8: dsm.sensitivity.SCHEME_ORDER is absent '
                                     'or empty; dsm score has no --schemes of its own '
                                     '([L1089]), so the shell would have to invent the '
                                     '[L1350] scheme list, and it does not (R-12)')
        return tuple(order)
    return tuple(part.strip() for part in str(text).split(',') if part.strip())


def _step6_hook(grading, attain, ev, red, prev, rules):
    '''Step8 注入的 Step6 钩子（dsm/sensitivity.py:30-33：grade_fn = ScoreFrame ->
    key -> FrameGrade）。真调 grading.assign，等级逻辑一行也不在 shell 里（R-7 / INV-2）。'''
    assign = _attr(grading, 'assign', 'Step6')

    def grade_fn(frame):
        rerun = assign(frame, attain, ev, red, prev, rules)
        return dict(((row.strategy_id, row.version_id, row.period), row.grade)
                    for row in rerun.rows)

    return grade_fn


def _step2_hook(normalize, models, params, anchor, inputs, period):
    '''Step8 NORM_SWAP 注入的 Step2 钩子（dsm/sensitivity.py:33-35 与 :436-441：
    (一个 pool x metric 组的原始达成率, 换用的方法) -> 归一值，且「the hook applies
    the pure method」）。三个归一公式归 normalize.py 所有，shell 只造它要求的载体：

      * 字典壳子由 T2 排序第一行 model_copy 出来（dict_version / caliber_version /
        unit / target_value / 签认状态全部沿用签认值），只换 metric_id，故没有任何
        业务数值被拟定（R-12）；
      * 锚定集用签认 T8 的 model_copy(strategy_ids=())，即 dsm/normalize.py:378-379
        说的「an empty strategy_ids tuple is the explicit no anchor case」，正好对上
        钩子「applies the pure method」的要求（[L941] 的锚定参考尺属 normalize 自己）；
      * params 与 Step2 同一份（从签认的 eval_config.normalize 读出来），只把 method
        换成钩子拿到的那一个，并经 NormalizeParams 重新校验（不接受未校验的拼写）。
    '''
    compute = _attr(normalize, 'compute', 'Step2')
    loose_key = _attr(normalize, 'step2_pool_key', 'Step2')
    carrier = _attr(normalize, 'NormalizeParams', 'Step2')
    template = sorted(inputs.metric_dict, key=lambda row: row.metric_id)[0]
    shell = template.model_copy(update={'metric_id': _SWAP_GRAIN})
    direction = int(template.direction)
    no_anchor = anchor.model_copy(update={'strategy_ids': ()})
    pool_key = loose_key(template.dim_code)
    base = params.model_dump()

    def normalizer(values, method):
        rows = tuple(models.AttainmentRow(
            strategy_id='%s-%05d' % (_SWAP_GRAIN, index), version_id=_SWAP_GRAIN,
            period=period, metric_id=_SWAP_GRAIN, attainment=value,
            direction=direction, has_target=True, capped_flag=False)
            for index, value in enumerate(values))
        frame = compute(rows, (shell,), no_anchor,
                        params=carrier(**dict(base, method=method)),
                        pools=dict((row.strategy_id, pool_key) for row in rows))
        got = dict((row.strategy_id, row.norm_value) for row in frame.rows)
        dropped = [index for index in range(len(values))
                   if '%s-%05d' % (_SWAP_GRAIN, index) not in got]
        if dropped:
            raise InvariantError('NORM_SWAP: the swapped Step2 frame returned no value '
                                 'for ' + str(len(dropped)) + ' of ' + str(len(values))
                                 + ' inputs (method=' + str(method) + '); a dropped '
                                 'value would silently shorten the [L749] Spearman '
                                 'rho, so the run stops instead (V-14)')
        return [got['%s-%05d' % (_SWAP_GRAIN, index)] for index in range(len(values))]

    return normalizer


def _gate_status(reports):
    '''reports.AllFrames 的必填 gate_status（dsm/reports.py:94-99：无默认，缺了就抛，
    「本模块不猜大概已经签了」ADJ-2）。契约里没有 G5/G7 的签认载体，本 RUN 也明确
    不做 G5/G7（属行方），故两项一律 False —— 首屏声明由 reports.GATE_STATEMENT
    （dsm/reports.py:55-58）逐字给出，shell 一个字也不改，更不宣称已签（R-12）。'''
    return _attr(reports, 'GateStatus', 'score')(
        g5_dispute_source_review_signed=False, g7_governance_config_signed=False)


def _dict_version(inputs):
    '''ScoreCardRow.dict_version（[L1616]）的唯一来源是 T2 自己签认的那一列。
    preflight C-06 已经判过全表一致；这里再确认一次，不一致就拒绝，绝不挑一行
    冒充全表（R-12）。'''
    values = sorted({str(row.dict_version) for row in inputs.metric_dict})
    if len(values) != 1:
        raise CliError('score_card.dict_version ([L1616]) needs one single T2 '
                       'dict_version; the loaded metric_dict carries '
                       + (', '.join(values) or 'nothing') + ' and the CLI picks no row '
                       'out of a disagreeing table (R-12, V-14)', EXIT_DATA)
    return values[0]

def _assemble_score_outputs(run, inputs, attain, ev, red, scores, grades, pool,
                            sens, weights, anchor, dict_version, usable):
    '''[L1610]-[L1626] 的 score_card 与 [L1630]-[L1634] 的 grade_ledger：每一格都取自
    九步的真实产物，没有任何一格是 shell 自己算出来的（INV-2 / R-7）。这里做的是
    **装配**而不是算法：定位三元组对齐、把 Step8 的稳定性标签与首屏可用性判定贴到
    对应行上、缺事实就缺格（不填 0，V-14）。池大小取 pooling.groups 的读侧接口
    （dsm/pooling.py:204-212），不在 shell 侧另数一遍（判据唯一性）；ledger_complete
    由 reports.ledger_missing_items 判（dsm/reports.py:225-237），shell 不自定
    「台账完整」的口径。'''
    models = _require('dsm.models')
    reports = _require('dsm.reports')
    pooling = _require('dsm.pooling')
    metric_cell = _attr(models, 'ScoreCardMetricCell', 'score_card')
    dim_cell = _attr(models, 'ScoreCardDimCell', 'score_card')
    card_row = _attr(models, 'ScoreCardRow', 'score_card')
    ledger_row = _attr(models, 'GradeLedgerRow', 'grade_ledger')
    missing_items = _attr(reports, 'ledger_missing_items', 'grade_ledger')
    groups = _attr(pooling, 'groups', 'Step7')(pool)

    fact_of = dict(((f.strategy_id, f.version_id, f.metric_id), f)
                   for f in inputs.metric_facts)
    dict_of = dict((m.metric_id, m) for m in inputs.metric_dict)
    attain_of = dict(((r.strategy_id, r.version_id, r.metric_id), r)
                     for r in attain.rows)
    ev_of = dict(((r.strategy_id, r.version_id), r) for r in ev.rows)
    grade_of = dict(((r.strategy_id, r.version_id, r.period), r) for r in grades.rows)
    pool_of = dict(((r.strategy_id, r.version_id, r.period), r) for r in pool.rows)
    stable_of = dict(((r.strategy_id, r.version_id), r) for r in sens.by_strategy)
    master_of = dict(((m.strategy_id, m.version_id), m) for m in inputs.strategy_master)
    hard_of = {}
    for row in red.rows:
        if row.level == 'HARD' and row.hit:
            hard_of.setdefault((row.strategy_id, row.version_id), []).append(row)

    cards, ledger = [], []
    for score in sorted(scores.rows, key=lambda r: (r.strategy_id, r.version_id)):
        key = (score.strategy_id, score.version_id, score.period)
        grade, pool_row = grade_of[key], pool_of[key]
        ev_row = ev_of[(score.strategy_id, score.version_id)]
        per_metric = {}
        for metric_id in sorted(dict_of):
            fact = fact_of.get((score.strategy_id, score.version_id, metric_id))
            if fact is None:
                continue          # 缺事实 = 缺格，不填 0（[L1613] / V-14）
            row = attain_of.get((score.strategy_id, score.version_id, metric_id))
            per_metric[metric_id] = metric_cell(
                actual_value=fact.value,
                target_value=dict_of[metric_id].target_value,
                attainment=(row.attainment if row is not None else None))
        per_dim = dict((dim, dim_cell(
            coverage=score.coverage, weight=weights.level1_weights[dim],
            attainment=score.dim_absolute[dim],
            relative_score=score.dim_relative.get(dim)))
            for dim in sorted(score.dim_absolute))
        hard = hard_of.get((score.strategy_id, score.version_id), [])
        stable = stable_of.get((score.strategy_id, score.version_id))
        row_usable = bool(grade.usable_for_elimination and usable)
        cards.append(card_row(
            strategy_id=score.strategy_id, version_id=score.version_id,
            period=score.period, weight_version_id=weights.weight_version_id,
            dict_version=dict_version, anchor_set_id=anchor.anchor_set_id,
            run_id=run.run_id, per_metric=per_metric, per_dim=per_dim,
            composite_absolute=score.composite_absolute,
            composite_relative=score.composite_relative,
            evidence_class=ev_row.evidence_class,
            evidence_reason=ev_row.evidence_reason,
            evidence_source=ev_row.evidence_source,
            interpretation_limit=ev_row.interpretation_limit,
            redline_pass=not hard,
            redline_flags=tuple(row.reason_code for row in hard),
            grade=grade.grade,
            grade_reason_codes=tuple(grade.grade_reason_path),
            capped_flag=grade.capped, cap_reason=grade.cap_reason,
            ranking_pool=pool_row.pool_key, rank_in_pool=pool_row.pool_rank,
            pool_size=len(groups.get(pool_row.pool_key, ())),
            eligible_for_L1_library=pool_row.primary_pool_eligible,
            l1_gate_reasons=() if pool_row.reject_reason is None
            else (pool_row.reject_reason,),
            stability_label=(stable.stability_label if stable is not None else None),
            flip_under_pct10=(stable.flip_under_pct10 if stable is not None else None),
            flip_under_pct20=(stable.flip_under_pct20 if stable is not None else None),
            usable_for_elimination=row_usable))
        master = master_of.get((score.strategy_id, score.version_id))
        row = ledger_row(
            strategy_id=score.strategy_id, version_id=score.version_id,
            period=score.period, grade=grade.grade, previous_grade=None,
            recommended_action=(' | '.join(grade.action) if grade.action else None),
            owner_dept=(master.owner_dept if master is not None else None),
            owner_name=(master.owner_name if master is not None else None),
            ledger_complete=True, usable_for_elimination=row_usable)
        ledger.append(row.model_copy(
            update={'ledger_complete': not missing_items(row)}))
    if not cards:
        raise CliError('the nine steps produced no score row for period '
                       + repr(run.args.period) + '; an empty score_card would read as '
                       '"nothing to assess" instead of "this period could not be '
                       'scored", so the run stops without artifacts (V-14, [L1091])',
                       EXIT_DATA)
    return tuple(cards), tuple(ledger)

def _rule_set_kwargs(app):
    '''Step6 治理值集合（dsm/grading.py:79-92）的装配。K-06 必填且无默认 -> 取签认的
    eval_config.min_coverage_for_absolute_track（M38 [L1743]）；四级规则行取 T7；
    upgrade_consecutive_periods / demotion_immediate 是 [L965] 的明文默认，签认树里
    带了 grade_rules.policy（K-08 载体）就用签认值，没带就留给模块自己的 [L965] 默认
    —— 两种情况都不是 shell 拟出来的数（H-5 / R-12）。'''
    kwargs = {'rows': _grade_rule_rows(app),
              'min_coverage_for_absolute_track': _min_coverage(app)}
    tree = getattr(app, 'grade_rules', None)
    policy = tree.get(_POLICY_KEY) if isinstance(tree, dict) else None
    if isinstance(policy, dict):
        for key in _HYSTERESIS_KEYS:
            if policy.get(key) is not None:
                kwargs[key] = policy[key]
    return kwargs


def _downgrade_actions(gate, attain, normalized):
    '''[L1051] item 13 的**全量**降级动作台账（H-6：不带注册 reason_code 的降级根本
    记不进去，所以这里一条也不许丢，shell 也一条都不新造）。三个来源各有各的 owning
    module：判定点 preflight 的 downgrade_actions（dsm/preflight.py:410）、Step1 的
    BLOCK 抑制与缺失规则通知（dsm/attainment.py:735 与 :761，挂在
    AttainmentResult.downgrades）、Step2 逐行「适用但被优先序挤出单值槽」的 warnings
    （dsm/normalize.py:433）。shell 只汇总并按 (码, 动作, 对象) 去重，排序交
    audit.build_manifest（dsm/audit.py:270）。'''
    sources = (tuple(getattr(gate, 'downgrade_actions', ()) or ())
               + tuple(getattr(attain, 'downgrades', ()) or ())
               + tuple(warning for row in normalized.rows
                       for warning in (getattr(row, 'warnings', ()) or ())))
    seen, out = set(), []
    for item in sources:
        key = (str(getattr(item, 'reason_code', item)),
               str(getattr(item, 'action', '')), str(getattr(item, 'subject', '')))
        if key not in seen:
            seen.add(key)
            out.append(item)
    return tuple(out)


def _chain_gate(run, app, loaded):
    '''M29 [L1325]-[L1358] 的九步 marshal 本体（V-14 转正四项的第 2 项）。

    顺序逐字照契约流程图，一步也不换位、一步也不内联（INV-2 / M00 L301）：
    config.load_all() 与 io_loaders 由调用方（cmd_score / cmd_sensitivity）先做完 ->
    判定点 preflight（[L1315]-[L1326]：BLOCK -> 只写 audit_bundle、退出码 2、不产
    score_card）-> Step1 attainment -> Step2 normalize（松键，ORCH-29 第 4 条）->
    旁路 diagnostics -> Step3 evidence -> Step4 redline -> Step5 aggregate（只读
    FROZEN 权重，[L1342]）-> Step6 grading -> Step7 pooling -> 旁路 triangulation ->
    Step8 sensitivity -> [L1352]-[L1354] 首屏可用性判定 + Step7 回灌 -> Step9 audit
    （manifest + reproducibility_hash）-> reports.render（report.md 十段 + 五张表 +
    audit.json）。返回 (exit_code, status, details)，与其余七个 handler 同一形状；
    details 是披露面：每一条降级都带码，每一个旁路都说清「不入分」（V-14 / [L1542]）。'''
    _require_chain_modules()
    inputs = _score_inputs(loaded)
    models = _require('dsm.models')
    attainment = _require('dsm.attainment')
    normalize = _require('dsm.normalize')
    diagnostics = _require('dsm.diagnostics')
    evidence = _require('dsm.evidence')
    redline = _require('dsm.redline')
    aggregate = _require('dsm.aggregate')
    grading = _require('dsm.grading')
    pooling = _require('dsm.pooling')
    triangulation = _require('dsm.triangulation')
    sensitivity = _require('dsm.sensitivity')
    audit = _require('dsm.audit')
    reports = _require('dsm.reports')

    # ---- 治理载体：全部来自签认配置，一个也不现编（H-5 / R-12）----------------
    # PreflightConfig 是 cmd_preflight 已在用的同一个构造口（:492），marshal 复用它，
    # 于是 T6 权重文档、T8 锚定集（经 :337 _anchor_set_doc 的唯一取法）与 [L900] C-01
    # 的 period_ref_date 三者在 preflight 与九步之间恒为同一对象（口径唯一）。
    pfc = _build_preflight_config(app, run.args.period)
    weights = pfc.weight_version
    anchor = pfc.anchor_set
    if anchor is None:
        raise CliError('Step2 normalize ([L1334] 锚定集参照) needs the signed T8 '
                       'anchor_set, and dsm/normalize.py:376-380 refuses anything '
                       'that is not an AnchorSetDoc; --config '
                       + repr(run.args.config) + ' carries no anchor_set and the CLI '
                       'fabricates no anchor member (R-12, K-12)', EXIT_CONFIG)
    ev_params = _attr(evidence, 'params_from_config', 'Step3')(app)
    norm_params = _attr(normalize, 'params_from_config', 'Step2')(app)
    sens_config = _sensitivity_config(app)
    soft = _soft_deductions(app)
    directions = _directions(inputs)
    prev = _previous_grade_frame(loaded)
    dict_version = _dict_version(inputs)
    # Step6 的 GradeRuleSet 也在这一段装配完（fail fast）：治理载体的缺口一律在跑第
    # 一步之前就按 [L1080] 退出码 3 点名键位（[L1328]「列出全部未填字段」的精神），
    # 而不是等九步跑到一半才从某个 owning module 内部抛一个键错出来。
    rules = _attr(grading, 'GradeRuleSet', 'Step6')(**_rule_set_kwargs(app))

    # ---- 判定点 preflight（[L1315]-[L1326]）----------------------------------
    # [L1542]：WARN 全部进最终报告附录，不会被静默吞掉 -> findings 与降级台账全量进
    # Step9 的 audit_bundle（[L1051] item 12 / 13）。BLOCK 走 preflight.execute 自己
    # 的出口：只写 audit.json、退出码 2、不产 score_card（[L917] / [L1091]）。
    run_dir = run.prod_dir()
    gate_context = run.audit_context(loaded, app,
                                     weight_version_id=weights.weight_version_id)
    code, gate, _paths = _attr(_require('dsm.preflight'), 'execute', 'preflight')(
        inputs, pfc, str(run_dir), gate_context)
    findings = tuple(getattr(gate, 'findings', ()) or ())
    if code == EXIT_BLOCK:
        return code, 'BLOCK', [
            'preflight status=BLOCK: no score card is produced ([L917] / [L1091]), '
            'the only artifact is the audit_bundle under ' + str(run_dir),
            'findings=%d kept in that audit_bundle, never swallowed ([L1542])'
            % len(findings)]

    # ---- Step 1 attainment（[L1332]）-----------------------------------------
    attain = _attr(attainment, 'compute', 'Step1')(
        inputs.metric_facts, inputs.metric_dict, app, anchor_set=anchor)

    # ---- Step 2 normalize（[L1334]）：松键 —— Step3 还没跑，evidence_class 不存在，
    # 故用 normalize.step2_pool_key（dsm/normalize.py:342-351，ORCH-29 第 4 条），
    # 绝不填默认值伪造严键（V-14）。params 与 NORM_SWAP 钩子共用同一份。
    loose_key = _attr(normalize, 'step2_pool_key', 'Step2')
    pools = dict((row.strategy_id, loose_key(row.biz_domain))
                 for row in inputs.strategy_master)
    normalized = _attr(normalize, 'compute', 'Step2')(
        attain, inputs.metric_dict, anchor, params=norm_params, pools=pools)

    # ---- 旁路 diagnostics（[L1336]：在线熵权 / CV / VIF / 相关，不入分，出工单）--
    # INV-3（M00 L302）在这里不破：Step5 只读 FROZEN 权重文档（下面 compose 的第三个
    # 入参就是 pfc.weight_version），diagnostics 的 d_j / gamma_j 只进
    # entropy_diagnostic.csv 的工单，从不回流成分数或权重。
    entropy, collinearity = _attr(diagnostics, 'compute', 'diagnostics')(
        inputs.metric_facts, inputs.metric_dict, app, period=run.args.period)
    entropy_rows = tuple(getattr(entropy, 'rows', ()) or ())
    collin_pairs = tuple(getattr(collinearity, 'pairs', ()) or ())

    # ---- Step 3 evidence（[L1338]）-------------------------------------------
    ev = _attr(evidence, 'classify', 'Step3')(inputs.design_cards,
                                              inputs.metric_facts, app)

    # ---- Step 4 redline（[L1340]：HARD 强制降级 / SOFT 独立扣减，不进加权）-----
    # 豁免：8 张输入表里没有豁免审批的载体（dsm/redline.py:36-37 已登记 A1），故
    # WaiverSet 恒为空 —— 这是「没有载体」的如实陈述，并在 details 里显式披露，
    # 不表现为静默不触发（V-14）。as_of 取 C-01 同一份签认的 period_ref_date
    # （H-8：不读时钟；口径唯一）。
    red = _attr(redline, 'evaluate', 'Step4')(
        inputs.metric_facts,
        _attr(redline, 'RedlineSet', 'Step4')(rows=inputs.redlines),
        _attr(redline, 'WaiverSet', 'Step4')(rows=()),
        as_of=pfc.period_ref_date, soft_deductions=soft,
        metric_dict=inputs.metric_dict)

    # ---- Step 5 aggregate（[L1342]：只读 FROZEN 权重，INV-3）------------------
    scores = _attr(aggregate, 'compose', 'Step5')(attain, normalized, weights,
                                                  _aggregate_config(app))

    # ---- Step 6 grading（[L1344]）-------------------------------------------
    # GradeRuleSet 已在上面的治理载体段装配完（K-06 取签认的 eval_config，M38
    # [L1743]；upgrade_consecutive_periods / demotion_immediate 取 grade_rules.policy
    # 或 dsm/grading.py:91-92 的 [L965] 明文默认；每级 promotion_streak 来自 T7 行
    # 本身，K-08 —— 没有一个值是 shell 拟的）。这里只调 grading.assign：基础等级 ->
    # 证据封顶 -> 目标封顶 -> 红线覆盖 -> 滞回 -> 版本断点，六段全在 grading 内部。
    grades = _attr(grading, 'assign', 'Step6')(scores, attain, ev, red, prev, rules)
    # ---- Step 7 pooling（[L1346]：分池禁混排 + 一级库门禁 + 占比双报 +
    #      NOT_ASSESSED 单列）。此刻 Step8 还没跑，稳健性无从举证 -> 举证制（R5，
    #      dsm/pooling.py:389-392 与 :461）下一律不给一级库准入；normalized 是
    #      [L943] 的可比性标注载体，R6 靠它把「有留痕的不可比」与「真契约违规的
    #      null」分开。config 交签认的 AppConfig，min_pool_size 由 pooling 自己从
    #      eval_config.normalize 读（dsm/pooling.py:140-151），shell 不另拟池下限。
    build_pool = _attr(pooling, 'build', 'Step7')
    pool, pool_stats = build_pool(scores, grades, ev, inputs.strategy_master, app,
                                  sensitivity=None, normalized=normalized)

    # ---- 旁路 triangulation（[L1348]：TOPSIS / GRA / Spearman -> AGREE or
    #      DIVERGENCE）。不入分（RK-5）：该模块不产出任何等级、分数或综合分列，
    #      对分数与等级的影响恒等于零。directions 是必填注入
    #      （dsm/triangulation.py:450-459：三个入参都没有 direction 列，而理想解与
    #      参考序列都要方向），唯一合法来源是 T2 自己签认的 direction 列（[L1137]）。
    #      enabled=false -> run() 返回 None，veto() 落注册码披露「已关闭」，不静默。
    tri = _attr(triangulation, 'run', 'triangulation')(
        scores, normalized, weights, app, directions=directions)
    tri_veto = _attr(triangulation, 'veto', 'triangulation')(tri)

    # ---- Step 8 sensitivity（[L1350]：OAT / MC / LOO / NORM_SWAP -> flip_rate +
    #      稳定性标签）。Step1-4 的产物按 [L1016] 经 ScoringContext 在各方案间复用，
    #      只重跑 Step5-6：grade_fn 真调 grading.assign、normalizer 真调
    #      normalize.compute（见 _step6_hook / _step2_hook），算法层一行也不在
    #      shell 里（R-7 / INV-2）。
    schemes = _wanted_schemes(run, sensitivity)
    if any(name.startswith(_MC_PREFIX) for name in schemes) and run.args.seed is None:
        raise CliError('--seed missing: MC schemes refuse to run without it ([L1089] '
                       '/ [L1017]); dsm score runs the whole [L1350] scheme list, so '
                       'the run is refused instead of silently dropping the MC scheme '
                       '(V-14) and no unseeded rerun is produced', EXIT_CONFIG)
    scoring = _attr(models, 'ScoringContext', 'Step8')(
        period=run.args.period, run_at=run.run_at, run_id=run.run_id,
        seed=run.args.seed, weight_version_id=weights.weight_version_id,
        evidence_mode=ev_params.evidence_mode, cel_enabled=ev_params.cel_enabled,
        input_fingerprints=dict(loaded.fingerprints), attainment=attain,
        normalized=normalized, evidence=ev, redline=red, score=scores, grade=grades,
        pool=pool, pool_stats=pool_stats)
    sens = _attr(sensitivity, 'run', 'Step8')(
        scoring, schemes, sens_config, weights=weights,
        grade_fn=_step6_hook(grading, attain, ev, red, prev, rules),
        normalizer=_step2_hook(normalize, models, norm_params, anchor, inputs,
                               run.args.period))
    sens_veto = _attr(sensitivity, 'veto', 'Step8')(sens)

    # ---- [L1352]-[L1354] 首屏可用性判定 -------------------------------------
    # flip_rate > review_max（sensitivity.veto 落 BLOCK 级 flag）或三角不一致
    # （triangulation.veto）-> usable_for_elimination = false，本期暂停淘汰。两个
    # 阈值判据与两个码都归各自的 owning module；shell 只做「两个非补偿否决相与」这
    # 一件装配事（P0-2：否决一旦带数值就能被后续加权补偿掉，所以 SensitivityVeto 与
    # TriangulationVeto 都只有 bool 与 reason_code，没有可乘的东西）。
    usable = bool(sens_veto.usable_for_elimination and tri_veto.usable_for_elimination)

    # ---- Step 7 回灌（[L1352]-[L1354] -> [L1346]）---------------------------
    # 一级库门禁的稳健性条件只有 Step8 跑完才存在，故 pooling.build 带 sensitivity
    # 再跑一次；判据仍在 pooling 内部（dsm/pooling.py:461 flip_rate_unusable），
    # shell 不复制那套判据（判据唯一性，ORCH-36 第 2/4 条）。
    pool, pool_stats = build_pool(scores, grades, ev, inputs.strategy_master, app,
                                  sensitivity=sens, normalized=normalized)

    # 池数披露走 pooling.groups 的读侧接口（dsm/pooling.py:204-212），shell 不另数一遍。
    pool_groups = _attr(pooling, 'groups', 'Step7')(pool)
    # ---- Step 9 audit（[L1356]：manifest + reproducibility_hash）-------------
    # score_card（[L1610]-[L1626]）与 grade_ledger（[L1630]-[L1634]）由九步真实产物
    # 装配（_assemble_score_outputs），[L1052] 哈希的真源是 dsm/audit.py:242 的
    # reproducibility_hash，shell 一个字节也不重算（R-7）。cel_contract_version 保持
    # PLACEHOLDER：[L1897] 明文「首版固定为占位版本」，与 Run.audit_context 同口径。
    cards, ledger = _assemble_score_outputs(
        run, inputs, attain, ev, red, scores, grades, pool, sens, weights, anchor,
        dict_version, usable)
    downgrades = _downgrade_actions(gate, attain, normalized)
    run_context = _attr(audit, 'RunContext', 'Step9')(
        run_id=run.run_id, run_at=run.run_at, period=run.args.period,
        dsm_version=dsm.__version__, design_version=dsm.DESIGN_DOC_VERSION,
        cel_contract_version=PLACEHOLDER,
        weight_version_id=weights.weight_version_id, seed=run.args.seed,
        sensitivity_schemes=tuple(item.scheme for item in sens.by_scheme),
        preflight_findings=tuple(item.to_audit_finding() for item in findings),
        downgrade_actions=downgrades, exit_code=EXIT_OK,
        score_card=cards, grade_ledger=ledger)
    # output_fingerprints（[L1051] item 10）的生产出口 = ORCH-59 裁决的**两遍渲染六键
    # 口径**：契约 §3.15.1 的次序是 Step9 audit.build_manifest -> reports.render -> 七件
    # 产物（含 audit.json），而 audit.json 的正文就是 bundle 的 canonical 序列化，故它
    # **不可能**含自身终值的哈希（[L1046] 字面自指，已登记 ERRATUM-V12-07 / NG-V12-20）。
    # 裁决口径（不得改写）：第一遍 bundle0（output_fingerprints={}）-> rs0；对 rs0 的
    # **6 件非 audit.json** 产物按 reports.write_report_set 完全相同的编码算 SHA256 ->
    # fps6；第二遍 bundle1（fps6）-> rs1；钉住 rs0/rs1 六件逐字节相等之后**只写盘一次**
    # （7 件）。bundle1.output_fingerprints 键集 == reports.ARTIFACT_NAMES - {audit.json}
    # == 6。两遍的装配全在 _render_reports（唯一出口）里，此处只交出第一遍的 bundle0 与
    # 两遍共用的三个入参（loaded.fingerprints / app / run_context），shell 一个字节也不
    # 重算哈希（R-7）。
    bundle0 = _attr(audit, 'build_manifest', 'Step9')(
        loaded.fingerprints, app, run_context, {})

    # ---- reports.render（[L1358]：report.md 十段 + 五张表 + audit.json）-------
    frames = _report_frames(
        loaded, gate_status=_gate_status(reports), attainment=attain, evidence=ev,
        redline=red, score=scores, pool=pool, pool_stats=pool_stats,
        sensitivity=sens, triangulation=tri, entropy_diagnostics=entropy_rows,
        score_card=cards, grade_ledger=ledger,
        weight_provenance=getattr(weights, 'provenance', None))
    bundle, fingerprints, render_details = _render_reports(
        run, bundle0, frames, app, loaded.fingerprints, run_context)

    # ---- 披露面（details）：每一步一行，每条降级都带码，每个旁路都说清「不入分」----
    entropy_count = len(entropy_rows)
    details = [
        'nine-step marshal of [L1325]-[L1358] ran to completion, in this order: '
        'preflight gate / Step1 attainment / Step2 normalize (loose pool key) / '
        'diagnostics bypass / Step3 evidence / Step4 redline / Step5 aggregate / '
        'Step6 grading / Step7 pooling / triangulation bypass / Step8 sensitivity / '
        'Step7 reflow / Step9 audit / reports.render',
        'preflight status=' + str(getattr(gate, 'status', 'PASS')) + '，findings='
        + str(len(findings)) + ' 条全量进 audit_bundle（[L1542] 不静默吞）；'
        'downgrade_actions=' + str(len(downgrades)) + ' 条（[L1051] item 13，'
        'preflight + Step1 + Step2 三个来源汇总去重）',
        'Step1 attainment：anchor_set=' + str(anchor.anchor_set_id) + '（[L941] 锚定集'
        '优先，与 Step2 同一个对象；_anchor_set_doc 是 shell 侧唯一取法）；rows='
        + str(len(attain.rows)),
        'Step2 normalize：松键构池（[L1334] 排在 [L1338] 之前，evidence_class 尚不'
        '存在 -> dsm/normalize.py:342-351 的 step2_pool_key，绝不填默认值伪造严键）；'
        'method=' + str(norm_params.method) + '；rows=' + str(len(normalized.rows)),
        'diagnostics 旁路（[L1336]，不入分、只出工单）：entropy ' + str(entropy_count)
        + ' 行 / collinearity ' + str(len(collin_pairs)) + ' 对；Step5 只读 FROZEN 权重 '
        + str(weights.weight_version_id) + '（[L1342] / INV-3），d_j 与 gamma_j 一律'
        '不回流成分数或权重',
        'Step3 evidence：mode=' + str(ev_params.evidence_mode) + '，cel_enabled='
        + str(ev_params.cel_enabled) + '；A/B/C/D 短路判定归 evidence.classify'
        '（[L1338]），shell 不复算',
        'Step4 redline：SOFT 扣减幅度逐字取自 grade_rules.soft_deductions（[L484]）；'
        'WaiverSet 恒空 = 8 张输入表里没有豁免审批载体（dsm/redline.py:36-37 已登记）'
        '的如实陈述，不表现为静默不触发（V-14）；as_of=' + str(pfc.period_ref_date)
        + '（与 C-01 同一份签认值，H-8 不读时钟）',
        'Step6 grading：K-06 min_coverage_for_absolute_track='
        + str(rules.min_coverage_for_absolute_track) + '；上期 GradeFrame 载体='
        + ('无（--previous-period 未接线，滞回状态由 grading 自己按首期处理并带注册码'
           '披露，shell 不造假基线 R-12）' if prev is None else '已注入'),
        'Step7 pooling：池数=' + str(len(pool_groups)) + '，pool_rows='
        + str(len(pool.rows)) + '；Step8 回灌后重跑一次，一级库门禁判据始终在 '
        'pooling 内部（判据唯一性）',
        'triangulation 旁路（[L1348]，不入分）：codes='
        + (', '.join(str(item) for item in tri_veto.codes) or 'none') + '；vetoed='
        + str(tri_veto.vetoed) + '；usable_for_elimination='
        + str(tri_veto.usable_for_elimination),
        'Step8 sensitivity：schemes=' + ','.join(schemes) + '；[L1019] veto codes='
        + (', '.join(str(item) for item in sens_veto.codes) or 'none') + '；vetoed='
        + str(sens_veto.vetoed) + '；usable_for_elimination='
        + str(sens_veto.usable_for_elimination) + '；seed=' + str(run.args.seed)
        + '（[L1017] 写入 audit_bundle）',
        '[L1352]-[L1354] 首屏可用性判定：usable_for_elimination=' + str(usable)
        + '（阈值判据归 sensitivity.veto / triangulation.veto，shell 只把两个非补偿'
        '否决相与）',
        'Step9 audit：reproducibility_hash=' + str(bundle.reproducibility_hash)
        + '（[L1052]）；input_fingerprints=' + str(len(bundle.input_fingerprints))
        + ' 张表；score_card ' + str(len(cards)) + ' 行 / grade_ledger '
        + str(len(ledger)) + ' 行（[L1610]-[L1634]，每格取自九步真实产物，缺事实即'
        '缺格、不填 0）',
        'output_fingerprints（[L1051] item 10）：ORCH-59 两遍渲染六键口径 -> bundle 内为 '
        + str(len(bundle.output_fingerprints)) + ' 件非 audit.json 产物的 SHA256，键集 = '
        'reports.ARTIFACT_NAMES - {' + AUDIT_ARTIFACT + '}（六键，逐值等于落盘文件的字节'
        '哈希，不是格式合法的假指纹）；audit.json 的正文即 bundle 的序列化，其自指纹不可能'
        '进自身（ERRATUM-V12-07 / NG-V12-20），故只在本披露面给出；本次七件产物的实测 '
        'SHA256 逐件披露如下，不静默（V-14）']
    details += ['  ' + name + '=' + digest
                for name, digest in sorted(fingerprints.items())]
    details.append('G5/G7 未签认 -> ' + reports.GATE_STATEMENT
                   + '（声明逐字取自 dsm/reports.py:55-58，shell 一字未改，更不宣称已签）')
    details += render_details
    return EXIT_OK, 'OK', details

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
    生产调用点（M29-1 已落地）：_chain_gate 经 _build_preflight_config 拿到本函数的
    返回值之后，把**同一个对象**同时喂给 attainment.compute(anchor_set=...)（[L1332]）
    与 normalize.compute(..., anchor_set, ...)（[L1334]），并作为 score_card
    .anchor_set_id（[L1616]）与 Step8 NORM_SWAP 钩子里那份「无锚定」副本的母本；
    四处同源，shell 不另开第二个锚定集（口径唯一）。'''
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
    重算，或上期 audit_bundle 的 pool_stats。九步 marshal（M29-1）已落地，但一次调用只跑
    本期，第一个来源要的是**上期那一次运行**留下的 pool_stats；而 [L1051] 的 audit_bundle
    十六列里没有 pool_stats 列，io_loaders.Inputs（dsm/io_loaders.py:149-159）也没有
    previous_pool_stats 字段 -> 两个来源都仍然不存在，
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


def _render_reports(run, bundle, frames, config, inputs_fp, run_ctx):
    '''S6 产物的渲染与写盘 —— ORCH-59「两遍渲染六键口径」的**唯一**生产出口。

    第一遍：调用方交进来的 bundle0（output_fingerprints={}）-> rs0 = reports.render；
    对 rs0 的 6 件非 audit.json 产物、按 reports.write_report_set **完全相同的编码**算
    SHA256 -> fps6（write_report_set 走 Path.write_text(text, encoding='utf-8')，落盘
    字节就是 text.encode('utf-8')，故 fps6 = audit.sha256_text(text)；哈希本身归
    audit.py，R-7：shell 一个字节也不重算）。
    第二遍：bundle1 = audit.build_manifest(inputs_fp, config, run_ctx, fps6) -> rs1。
    写盘只发生一次：reports.write_report_set(rs1, run.dir) 写出 [L1062] 的 7 件。

    两道不变式，任一被破坏就 InvariantError（[L1081] 退出码 5、不产出自相矛盾的产物，
    绝不静默降级 V-14）：
      INV-A rs0 与 rs1 的 6 件非 audit.json 产物**逐字节相等** —— 证明把 fps6 回填进
            bundle 不自相矛盾。若不等，说明某件产物内嵌了 output_fingerprints，此时
            ORCH-59 明文要求停手上报主控，**不许**改成两遍写盘去伪造 audit.json 的
            自指纹。
      INV-B write_report_set 返回的 6 枚落盘指纹与 fps6 逐值全等 —— 把「内存编码 ==
            落盘编码」这条平台假设变成实测对账（dsm/audit.py:162 check_sha256 只校验
            64 位小写十六进制的**格式**，假指纹 '0'*64 照样通过，故格式校验不等于真对账）。

    返回 (bundle1, fingerprints, details)：bundle1 是**落盘那份 audit.json 的母本**，
    fingerprints 是 write_report_set 的 7 枚落盘指纹（含 audit.json 自身，只对外披露、
    不进 audit.json 内部）；details 把两个 V-14 载体的接线结果逐条说出来 —— G-14 基线
    有无、范围过滤几张卡 —— 不静默（[L1051] item 14 降级动作全量 / V-14）。
    '''
    reports = _require('dsm.reports')
    audit = _require('dsm.audit')
    if run.dir is None:
        run.prod_dir()
    render = _attr(reports, 'render', 'score')
    write_set = _attr(reports, 'write_report_set', 'score')
    build_manifest = _attr(audit, 'build_manifest', 'score')
    sha_text = _attr(audit, 'sha256_text', 'score')
    # 六键的键集只从 reports.ARTIFACT_NAMES 派生（口径唯一，shell 不另列一份文件名）。
    six = tuple(name for name in reports.ARTIFACT_NAMES if name != AUDIT_ARTIFACT)

    # ---- 第一遍：bundle0 -> rs0 -> fps6 ----------------------------------------
    rs0 = render(bundle, frames, config)
    texts0 = rs0.artifacts()
    fps6 = dict((name, sha_text(texts0[name])) for name in six)

    # ---- 第二遍：fps6 回填进 bundle -> rs1 -------------------------------------
    bundle1 = build_manifest(inputs_fp, config, run_ctx, fps6)
    rs1 = render(bundle1, frames, config)
    texts1 = rs1.artifacts()
    drifted = tuple(name for name in six if texts0[name] != texts1[name])
    if drifted:
        raise InvariantError('ORCH-59 INV-A: re-rendering with the six output '
                             'fingerprints filled back into the AuditBundle changed '
                             + str(len(drifted)) + ' non-audit artifact(s): '
                             + ', '.join(drifted) + ' -- an artifact therefore embeds '
                             'output_fingerprints, and audit.json can never carry the '
                             'digest of the very file it is written into ([L1046] is '
                             'self-referential; ERRATUM-V12-07 / NG-V12-20). The ruling '
                             'forbids faking that self fingerprint with a second pass '
                             'over the disk, so the run stops without artifacts (V-14)',
                             EXIT_INTERNAL)

    # ---- 只写盘一次：[L1062] 七件 ---------------------------------------------
    fingerprints = write_set(rs1, run.dir)
    mismatched = tuple(name for name in six
                       if fingerprints.get(name) != fps6[name])
    if mismatched:
        raise InvariantError('ORCH-59 INV-B: the digest taken over the rendered text '
                             'is not the digest of the bytes reports.write_report_set '
                             'landed for: ' + ', '.join(mismatched) + ' -- audit.json '
                             'would then disclose a fingerprint that the [L1640] step-1 '
                             'verification of a re-run cannot reproduce, so the run '
                             'stops (V-14)', EXIT_INTERNAL)

    details = ['report set written to ' + str(run.dir) + ': '
               + ', '.join(sorted(fingerprints))]
    details.append('ORCH-59 两遍渲染六键口径已执行：bundle.output_fingerprints 键集 = '
                   + ', '.join(six) + '（= reports.ARTIFACT_NAMES - {' + AUDIT_ARTIFACT
                   + '}，共 ' + str(len(six)) + ' 键）；INV-A rs0/rs1 六件逐字节相等已核；'
                   'INV-B 回填指纹与落盘指纹逐值全等已核；写盘只发生一次（7 件）。'
                   + AUDIT_ARTIFACT + ' 自身 SHA256='
                   + str(fingerprints.get(AUDIT_ARTIFACT))
                   + '，只在本披露面给出、不进 audit.json 内部（自指不可能，'
                   'ERRATUM-V12-07 / NG-V12-20）')
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
    return bundle1, fingerprints, details


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
    their calibrate/whatif group (INV-2).

    V-14 第 4 项返工（M29-1）：返回 (path_or_None, notes)，不再用
    `except OSError: return None` 把「审计包写不出来」吞成一个静默的 None。写不出来
    时 notes 里带注册 reason_code、目标路径、异常类型与原文，并明说本次审计链不完整；
    run 还没建起来（连目录都没有）同样出一行披露。降级必须带码且可见（H-6），
    静默降级正是 V-14 禁止的那件事。'''
    if run is None:
        return None, ('audit_bundle NOT written: the failure happened before a Run '
                      'existed, so there is no run directory to put it in ([L1091]); '
                      'the error line above is the entire audit trail of this '
                      'invocation -- disclosed, not silently dropped (V-14)',)
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
        return path, ()
    except OSError as write_exc:
        # 这里曾是 `except OSError: return None`：[L1091]「任何命令失败都写
        # audit_bundle」被无声地破掉，调用方只会看到 details 里少了一行
        # audit_bundle=...。码取自注册表（R-15 单点，shell 不自造码，也不写字面量
        # P-8）；注册表里没有「审计包写盘失败」的专码，故用 [L1081] 的
        # INVARIANT_VIOLATION —— 写不出审计包正是本 shell 自己的不变量被破，
        # 是否需要专码已上报主控裁决（GAPS）。
        codes = _require('dsm.reason_codes')
        reason = _attr(codes, 'RC', 'audit_bundle').INVARIANT_VIOLATION
        say = _attr(codes, 'message', 'audit_bundle')
        target = (run.dir if run.dir is not None else
                  Path(run.args.out) / (run.command if run.command in _L0B_GROUPS
                                        else 'failed') / run.run_id)
        return None, ('reason_code=' + reason.value + ': ' + say(reason.value)
                      + ' -- [L1091] requires an audit_bundle for EVERY failed '
                      'command, and writing ' + str(target / 'audit_bundle.json')
                      + ' failed with ' + type(write_exc).__name__ + ': '
                      + str(write_exc) + '; the audit trail of this run is '
                      'INCOMPLETE, all that survives is the ' + type(exc).__name__
                      + ' (exit=' + str(code) + ') above. Disclosed, never silently '
                      'degraded (V-14, H-6).',)

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
        bundle, bundle_notes = _write_failure_bundle(run, exc, code)
        if bundle is not None:
            details.append('audit_bundle=' + str(bundle))
        details.extend(bundle_notes)
        if code not in (EXIT_BLOCK, EXIT_CONFIG, EXIT_DATA):
            details.append('no score card is produced on a non-zero exit ([L1091])')
    _emit(command, code, status, run.run_id if run else None, details)
    return code

if __name__ == '__main__':
    raise SystemExit(main())
