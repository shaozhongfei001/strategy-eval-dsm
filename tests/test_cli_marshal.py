'''M29-1 九步 marshal 本体守护（契约 §3.15.1 流程图 L1325-L1358）+ V-14 第 4 项返工。

本文件钉三件事：
  1. `dsm/cli.py:_chain_gate` 在模块齐全时**返回**（不再 raise InvariantError），且九步
     的调用顺序与契约流程图逐行一致、产物齐备（report.md 十段 / 五张表 / audit.json，
     [L1062]-[L1063]）；每一步都是**真调 owning module**（钩子也不例外），shell 一行
     算法也没内联（INV-2 / R-7）。
  2. 治理载体缺失一律 [L1080] 退出码 3 并点名键位（H-5 / R-12 / K-01~K-20），
     shell 绝不拟定业务值、绝不塞默认值。
  3. V-14 第 4 项：`_write_failure_bundle` 的 `except OSError: return None` 已返工为
     显式 reason_code + 报告披露，审计包写不出来时**不再静默降级**（H-6）。

数据与治理值一律取自仓库既有载体，无一项本文件拟定（R-12）：
  * 输入八表 = 冻结 fixtures（fixtures/input/*.jsonl），经 test_integration_spine._stage
    摆成 [L888] 目录口径；评价期 2026-Q2 = 该文件 PERIOD（事实表完整的一期）。
  * 治理配置 = 仓库自带的 M29-3 演练 config（config/*.yaml，合成待签认，**不等于 G7**）。
  * [L484] SOFT 扣减比率载体：ORCH-61 裁决 = grade_rules.yaml 顶层 soft_deductions；
    CFG-1 正在并行补 config/，故本文件**自带**该载体（自包含，不依赖 CFG-1 是否落地），
    值出处逐字 = tests/test_integration_spine.py:84 GOVERNANCE['soft_deductions']。

两个**写集外**阻塞点（ORCH-49 第 3 条：不改，如实上报主控）：
  B1 dsm/diagnostics.py:223 `_pearson` 的 `numeric.sqrt(q12(sxx * syy))` —— 冻结 fixtures
     的钱款列（M_CAMPAIGN_COST_MINOR ≈ 2.8e6）使 sxx*syy ≈ 1e26，quantize 到 1e-12 需要
     38 位有效数字，超过 Decimal 默认上下文 prec=28 -> decimal.InvalidOperation。
  B2 dsm/triangulation.py:293 `dimensionless` —— M_AUM_MINOR 在 12 个主体上恒定，min_max
     归一后该列全 0，gra_norm=initial / mean 两种签认口径的参考值都是 0 -> 该模块按
     设计报错（「不回落成第三种口径，那是发明数值 R-12」）。
  二者都不在 M29-1 写集内，shell **不 cushion**（cmd_combine_build 的既有纪律：a bug must
  surface as one），故本文件对它们各钉一条「缺陷必须原样冒出来 + 不产分数 + 有
  audit_bundle」的测试；一旦上游修好，测试的 else 分支自动升级为「九步全通」的同等强度
  断言，不需要也不允许改成 skip / xfail（R-14）。
  成功路（test_score_end_to_end_*）因此把 triangulation 的 `enabled` 开关置为
  dsm/triangulation.py:66-73 认的**合法签面值 false**（run() 返回 None -> veto() 落
  TRIANGULATION_DISABLED，关闭不静默），并把 L5 旁路换成同形状的真实模型空载体 —— 这两处
  都是**旁路**（[L1336] / [L1348] 明文「不入分」），换掉它们不影响 Step1-9 的任何一格数值。
'''
import ast
import json
import pathlib
import re
import shutil
import types
from decimal import Decimal

import pytest

import dsm.cli as cli
import test_integration_spine as spine
from dsm import config as dsm_config
from dsm import diagnostics, reports
from dsm.reason_codes import RC

REPO = pathlib.Path(__file__).resolve().parents[1]
REPO_CONFIG = REPO / 'config'
PERIOD = spine.PERIOD                      # 2026-Q2，事实表完整的一期
RUN_AT = '2026-10-20T00:00:00+00:00'       # = spine.RUN_AT（注入时钟，H-8）
SEED = 20261020                            # [L1017] MC 必须有 seed
# ORCH-61 裁决的 [L484] 载体；值逐字取自 tests/test_integration_spine.py:84。
SOFT_CARRIER = '\nsoft_deductions:\n  M_OPTOUT_RATE: "0.05"\n'
# [L1062] 七件产物 = report.md + 五张表 + audit.json（契约 L1358 逐字）。
SEVEN = ('report.md', 'score_card.csv', 'grade_ledger.csv', 'sensitivity_report.csv',
         'entropy_diagnostic.csv', 'triangulation.md', 'audit.json')
FIVE_TABLES = tuple(name for name in SEVEN
                    if name not in ('report.md', 'audit.json'))
# 契约 §3.15.1 流程图的调用顺序（每行标出契约行号），本文件用它做**行为式**断言：
# 用记录器包住每个 owning module 的入口，跑一遍真实链，比对首现顺序。
CONTRACT_ORDER = (
    ('preflight', 'execute'),            # [L1315]-[L1326] 判定点
    ('attainment', 'compute'),           # [L1332] Step1
    ('normalize', 'compute'),            # [L1334] Step2
    ('diagnostics', 'compute'),          # [L1336] 旁路（不入分）
    ('evidence', 'classify'),            # [L1338] Step3
    ('redline', 'evaluate'),             # [L1340] Step4
    ('aggregate', 'compose'),            # [L1342] Step5
    ('grading', 'assign'),               # [L1344] Step6
    ('pooling', 'build'),                # [L1346] Step7
    ('triangulation', 'run'),            # [L1348] 旁路（不入分）
    ('sensitivity', 'run'),              # [L1350] Step8
    ('audit', 'build_manifest'),         # [L1356] Step9
    ('reports', 'render'),               # [L1358] 出口
)
FIRST_ORDER = tuple(dict.fromkeys(CONTRACT_ORDER))


def _stage_data(tmp_path):
    '''冻结 fixtures -> [L888] 目录口径，并把仓库自带的演练 config/*.yaml 复制进同一个
    config 目录（io_loaders 从 config_dir 读 metric_dict.csv / redlines.csv，config.load_all
    从同一目录读六份 yaml，[L1248]-[L1257]）。返回 (config_dir, data_dir)。'''
    root = tmp_path / 'stage'
    conf, data = spine._stage(root, PERIOD, with_design_cards=True)
    for path in sorted(REPO_CONFIG.glob('*.yaml')):
        shutil.copyfile(path, conf / path.name)
    grade = conf / 'grade_rules.yaml'
    text = grade.read_text(encoding='utf-8')
    if 'soft_deductions' not in text:      # CFG-1 落地后本行自动失效，不改断言强度
        grade.write_text(text + SOFT_CARRIER, encoding='utf-8', newline='\n')
    return conf, data


def _app(conf, *, triangulation=True, drop_eval=(), drop_grade=()):
    '''真实 config.load_all 出来的 AppConfig（M29-3 演练 config，合成待签认）。
    triangulation=False -> 把 [L1030] 的 enabled 开关置为该模块自己认的合法签面值
    （dsm/triangulation.py:66-73），关闭由 veto() 落注册码披露，不静默。
    drop_eval / drop_grade -> 摘掉某个治理键，用来断言 shell 拒绝而非默认（H-5）。'''
    app = dsm_config.load_all(conf)
    tree = dict(app.eval_config)
    tree['triangulation'] = dict(tree['triangulation'], enabled=bool(triangulation))
    for key in drop_eval:
        tree.pop(key, None)
    grade_rules = dict(app.grade_rules)
    for key in drop_grade:
        grade_rules.pop(key, None)
    return app.model_copy(update={'eval_config': tree, 'grade_rules': grade_rules})


def _wire(monkeypatch, app, conf, data):
    '''把 config 注入 shell（照 tests/test_cli.py:59 _stub_io 的既有做法），数据加载
    走**真实** io_loaders.load_inputs（不 mock，八表与 InputFingerprints 都是真的）。'''
    monkeypatch.setattr(cli, '_load_config', lambda run: app)
    return ['score', '--period', PERIOD, '--config', str(conf), '--data', str(data),
            '--run-at', RUN_AT, '--seed', str(SEED)]


def _run_dirs(out):
    '''[L1091] 生产目录口径 = <out>/<period>/<run_id>/，最深的那一层才是本次运行的
    产物目录；外层 <out>/<period>/ 本身不放文件。'''
    return sorted((p for p in out.rglob('*') if p.is_dir()), key=lambda p: len(p.parts))


def _empty_l5_bypass(period):
    '''阻塞点 B1 的替身：形状与真实返回值一致（EntropyDiagnostic + CollinearityReport，
    都是 dsm/diagnostics.py 自己的冻结模型），只是不含任何行 —— 旁路不入分
    （[L1336]），故 Step1-9 的每一格数值都不受它影响。'''
    return (diagnostics.EntropyDiagnostic(period=period, strategy_count=0, rows=()),
            diagnostics.CollinearityReport(method='pearson'))


def _bypass_l5(monkeypatch):
    def compute(facts, metric_dict, config, *, period=None, prior_gamma=None):
        return _empty_l5_bypass(period)
    monkeypatch.setattr(diagnostics, 'compute', compute)


def _run_ok(monkeypatch, tmp_path, **kwargs):
    '''成功路的公共装配：返回 (code, printed, run_dir, recorded)。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, **kwargs)
    argv = _wire(monkeypatch, app, conf, data)
    out = tmp_path / 'out'
    argv += ['--out', str(out)]
    recorded = _record_order(monkeypatch)
    code = cli.main(argv)
    dirs = _run_dirs(out)
    return code, out, (dirs[-1] if dirs else None), recorded


def _record_order(monkeypatch):
    '''行为式顺序记录器：包住每个 owning module 的入口，**转调真实实现**，只记下调用
    先后。L5 旁路因阻塞点 B1 换成同形状空载体（见 _empty_l5_bypass 的说明）。'''
    recorded = []
    _bypass_l5_recording(monkeypatch, recorded)
    for module_name, function in (('preflight', 'execute'), ('attainment', 'compute'),
                                  ('normalize', 'compute'), ('evidence', 'classify'),
                                  ('redline', 'evaluate'), ('aggregate', 'compose'),
                                  ('grading', 'assign'), ('pooling', 'build'),
                                  ('triangulation', 'run'), ('sensitivity', 'run'),
                                  ('audit', 'build_manifest'), ('reports', 'render')):
        module = __import__('dsm.' + module_name, fromlist=[module_name])
        real = getattr(module, function)

        def wrap(*args, _real=real, _label=(module_name, function), **kwargs):
            recorded.append(_label)
            return _real(*args, **kwargs)

        monkeypatch.setattr(module, function, wrap)
    return recorded


def _bypass_l5_recording(monkeypatch, recorded):
    def compute(facts, metric_dict, config, *, period=None, prior_gamma=None):
        recorded.append(('diagnostics', 'compute'))
        return _empty_l5_bypass(period)
    monkeypatch.setattr(diagnostics, 'compute', compute)

# ---------------------------------------------------------------------------
# 1. _chain_gate 从「拒绝」变成「真串九步」
# ---------------------------------------------------------------------------
def test_chain_gate_returns_a_handler_triple_and_no_longer_refuses_a_full_tree():
    '''V-14 转正四项的第 2 项：模块齐全时 `_chain_gate` **返回**，不再 raise
    InvariantError（原 dsm/cli.py:333 的拒绝门已删除）；缺模块分支原样保留
    （[L1081] 退出码 5，逐模块点名，tests/test_cli.py:211 继续守护）。'''
    source = (REPO / 'dsm' / 'cli.py').read_text(encoding='utf-8')
    assert 'chain modules are all present' not in source, '旧的拒绝门必须删掉'
    assert 'P2 integration deliverable' not in source
    tree = ast.parse(source)
    functions = dict((n.name, n) for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    gate = functions['_chain_gate']
    returns = [n for n in ast.walk(gate) if isinstance(n, ast.Return)]
    assert returns, '_chain_gate 必须有 return'
    for node in returns:
        assert isinstance(node.value, ast.Tuple) and len(node.value.elts) == 3, \
            '_chain_gate 的每个出口都是 (exit_code, status, details)，与其余七个 handler 同形'
    calls = [n.func.id for n in ast.walk(gate) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name)]
    assert calls[0] == '_require_chain_modules', '前置闸必须第一件事就跑（缺模块 -> 5）'
    guard = functions['_require_chain_modules']
    assert any(isinstance(n, ast.Raise) for n in ast.walk(guard))
    assert '_import_dep' in ast.get_source_segment(source, guard), \
        '缺模块检测必须仍走 _import_dep 这个可测 seam（tests/test_cli.py:211 靠它）'


def test_nine_step_call_order_is_the_contract_flow_chart(monkeypatch, tmp_path, capsys):
    '''**行为式**顺序断言：用记录器包住每个 owning module 的入口并转调真实实现，
    跑一遍真实链，比对首现顺序与契约 §3.15.1 流程图（L1325-L1358）逐行一致；
    并断言 Step7 在 Step8 之后**回灌**一次、三个钩子（Step2 / Step5 / Step6）都是真调。'''
    code, out, run_dir, recorded = _run_ok(monkeypatch, tmp_path, triangulation=False)
    assert code == 0, recorded
    first = {}
    for index, label in enumerate(recorded):
        first.setdefault(label, index)
    missing = [label for label in FIRST_ORDER if label not in first]
    assert not missing, '契约流程图的这些调用一次都没发生：' + repr(missing)
    positions = [first[label] for label in FIRST_ORDER]
    assert positions == sorted(positions), \
        '首现顺序必须等于契约流程图顺序：' + repr([(label, first[label]) for label in FIRST_ORDER])
    reflow = [i for i, label in enumerate(recorded)
              if label == ('pooling', 'build') and i > first[('sensitivity', 'run')]]
    assert reflow, '[L1352]-[L1354]：Step8 之后必须回灌 Step7（一级库稳健性门禁）'
    assert recorded.count(('grading', 'assign')) >= 2, 'Step8 的 grade_fn 必须真调 grading.assign'
    assert recorded.count(('aggregate', 'compose')) >= 2, 'Step8 的方案必须真调 aggregate.compose'
    assert recorded.count(('normalize', 'compute')) >= 2, 'NORM_SWAP 的钩子必须真调 normalize.compute'
    printed = capsys.readouterr().out
    assert 'output_fingerprints' in printed
    for name in SEVEN:
        assert name + '=' in printed, '七件产物的实测指纹必须逐件披露（不静默，V-14）'
    assert 'usable_for_elimination=' in printed, '[L1352]-[L1354] 首屏可用性判定必须披露'


def test_score_end_to_end_writes_ten_sections_five_tables_and_audit_json(monkeypatch,
                                                                        tmp_path):
    '''[L1358] 出口真的被调用：report.md 十段（reports.assert_report_sections 亲自判）、
    五张表齐备、audit.json 是 [L1051] 的十六列且 reproducibility_hash 是 64 位十六进制；
    score_card 与 grade_ledger 行数相等且等于冻结 fixtures 的主体数；G5/G7 首屏声明
    逐字出现（本包不宣称已签，§1 明确不做 G5/G7）。'''
    code, out, run_dir, _recorded = _run_ok(monkeypatch, tmp_path, triangulation=False)
    assert code == 0
    assert run_dir is not None
    assert sorted(p.name for p in run_dir.iterdir() if p.is_file()) == sorted(SEVEN)
    report_md = (run_dir / 'report.md').read_text(encoding='utf-8')
    assert reports.assert_report_sections(report_md) == reports.REPORT_SECTIONS
    assert reports.GATE_STATEMENT in report_md, '首屏门禁声明一字不改（§1 不做 G5/G7）'
    for name in FIVE_TABLES:
        assert (run_dir / name).stat().st_size > 0, name + ' 是空文件'
    # audit.json 的正文 = audit.serialize_bundle 的 canonical text（**不是** JSON）：
    # dsm/reports.py:795 render_audit_json + tests/test_reports.py:325 已钉死该口径，
    # 本文件照它断言，不另立第二种读法（判据唯一性）。
    body = (run_dir / 'audit.json').read_text(encoding='utf-8')
    assert body.startswith('obj:AuditBundle{')
    absent = [key for key in cli._BUNDLE_KEYS if ('s:' + key + '=') not in body]
    assert not absent, '[L1051] 十六列缺列：' + repr(absent)
    found = re.search('s:reproducibility_hash=s:([0-9a-f]+)', body)
    assert found is not None and len(found.group(1)) == 64, \
        '[L1052] reproducibility_hash 必须是 64 位小写十六进制，实得 ' + repr(found)
    assert 's:exit_code=i0' in body and ('s:seed=i' + str(SEED)) in body, \
        '[L1017] seed 写入 audit_bundle；[L1051] item 14 exit_code=0'
    assert 's:weight_version_id=s:' in body and 's:config_snapshot_sha256=s:' in body
    # [L888] / [L1330]：io_loaders 给它实读的每个文件一枚 SHA256 + 行数，键按文件名
    # 排序后整体进 bundle（AuditBundle item 9）。下面的断言与排序无关，且期望值全部取自
    # **输入侧**（spine._stage 摆的文件名 + 冻结 fixtures 的行数），不是抄实现输出（R-14）。
    fingerprints = {}
    for name, inner in re.findall(
            r's:([A-Za-z0-9_.-]+[.]csv)=obj:InputTableFingerprint\{([^{}]*)\}', body):
        sha = re.search(r's:sha256=s:([0-9a-f]+)', inner)
        rows = re.search(r's:row_count=i(\d+)', inner)
        assert sha is not None and rows is not None, \
            '[L888] 指纹条目必须同时带 sha256 与 row_count，实得 ' + repr(inner)
        fingerprints[name] = (sha.group(1), int(rows.group(1)))
    expected_rows = {
        'metric_dict.csv': len(spine._jsonl('metric_dict.jsonl')),
        'redlines.csv': len(spine._jsonl('redline.jsonl')),
        'strategy_master.csv': len(spine._jsonl('strategy_master.jsonl')),
        'design_cards.csv': len(spine._jsonl('design_card.jsonl')),
        'metric_facts.csv': len([row for row in spine._jsonl('metric_fact.jsonl')
                                 if row['period'] == PERIOD]),
    }
    assert fingerprints, '[L1330] InputFingerprints 空着进 bundle = 静默降级（V-14）'
    assert sorted(fingerprints) == sorted(expected_rows), \
        '[L888] 被指纹的文件集必须等于 io_loaders 实读的那几张表，实得 ' \
        + repr(sorted(fingerprints))
    assert all(len(sha) == 64 for sha, _rows in fingerprints.values()), \
        '[L888] 每枚 sha256 都是 64 位小写十六进制，实得 ' + repr(fingerprints)
    got_rows = dict((name, rows) for name, (_sha, rows) in fingerprints.items())
    assert got_rows == expected_rows, \
        '[L888] row_count 必须等于冻结 fixtures 的行数（缺事实即缺格，不填 0），实得 ' \
        + repr(got_rows)
    assert 's:output_fingerprints={}' not in body and 's:output_fingerprints={' in body, \
        'M29-2 / ORCH-59 六键口径：bundle 内为 ARTIFACT_NAMES - {audit.json} 六键；' \
        'M29-1 过渡钉自述「生产出口归 M29-2」，其有效期前提已于 04cbe19 兑现（到期）' \
        ' -> ORCH-66 批准翻面，属口径补齐而非 R-14 弱化：六键精确性' \
        '（键集恰等 + 逐值落盘重算 + 正文六枚对账 + 自身哈希不入正文）' \
        '已由 tests/test_report_set_outlet.py 的 8 条断言承担'
    assert 's:preflight_findings=[]' not in body, '[L1542] WARN 全量进 bundle，不被静默吞'
    assert 's:downgrade_actions=[]' not in body, \
        '[L1051] item 13：preflight / Step1 / Step2 三个来源的降级动作全量进 bundle'
    assert 's:sensitivity_schemes=[s:LOO,s:MC,s:NORM_SWAP,s:OAT_10,s:OAT_20]' in body, \
        '[L1015] 五个方案一个不少（dsm score 无 --schemes，跑 SCHEME_ORDER 全量）'
    # [L1610]-[L1634]：两张表逐「本期评价范围内的主体」一行。行数不取 master 的总行数：
    # 冻结 fixtures 里 S-005 有两个版本（旧版 offline_date=2026-06-30、新版
    # online_date=2026-07-01），后者在 2026-Q2 之后上线，不在本期范围内。期望值取自
    # **输入侧**本期事实行的 strategy_id × version_id 对（与 dsm/evidence.py:218
    # _fact_pairs 同一口径），不是抄实现输出（R-14）。
    master_rows = spine._jsonl('strategy_master.jsonl')
    in_period_pairs = set((row['strategy_id'], row['version_id'])
                          for row in spine._jsonl('metric_fact.jsonl')
                          if row['period'] == PERIOD)
    card = (run_dir / 'score_card.csv').read_text(encoding='utf-8').strip().split('\n')
    ledger = (run_dir / 'grade_ledger.csv').read_text(encoding='utf-8').strip().split('\n')
    assert len(in_period_pairs) < len(master_rows), \
        '前提检查：冻结 fixtures 必须确实含一个跨期版本，否则本断言测不到范围过滤'
    assert len(card) - 1 == len(ledger) - 1 == len(in_period_pairs), \
        '[L1610]-[L1634]：两张表逐主体一行，行数取自本期事实表的主体数，不是本文件拟的数'
    sensitivity_csv = (run_dir / 'sensitivity_report.csv').read_text(encoding='utf-8')
    assert sensitivity_csv.split('\n')[0].count(',') == 12, \
        'reports.SENSITIVITY_COLUMNS 13 列表头不变（tests/test_reports.py:355 钉死）'


# ---------------------------------------------------------------------------
# 2. 两个写集外阻塞点：shell 不 cushion，缺陷原样冒出来（ORCH-49 第 3 条上报）
# ---------------------------------------------------------------------------
def test_blocker_b1_l5_diagnostics_precision_defect_surfaces_uncushioned(monkeypatch,
                                                                        tmp_path, capsys):
    '''B1（写集外，dsm/diagnostics.py:223）：`numeric.sqrt(q12(sxx * syy))` 在钱款列上
    把 ≈1e26 的乘积 quantize 到 1e-12，需要 38 位有效数字 > Decimal 默认 prec=28 ->
    decimal.InvalidOperation。降级矩阵 L1305「内部不变量违反 -> 退出码 5、不产出任何
    结果」+ [L1091] 仍写 audit_bundle，就是契约要求的行为，本测试钉住它；上游修好后
    else 分支不再进入，if 分支要求九步全通（同等强度），**不许改成 skip/xfail**（R-14）。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, triangulation=False)
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    code = cli.main(argv)
    printed = capsys.readouterr().out
    if code == 0:
        run_dir = _run_dirs(tmp_path / 'out')[-1]
        assert sorted(p.name for p in run_dir.iterdir() if p.is_file()) == sorted(SEVEN)
    else:
        assert code == 5, '只允许两种结局：缺陷原样冒出来（5）或已修好（0），实测 ' + repr(code)
        assert 'diagnostics' in printed and 'InvalidOperation' in printed, printed
        assert 'Traceback' not in printed, '[L1081] 必须是显式错误行，不是裸 traceback'
        assert not list((tmp_path / 'out').rglob('score_card.csv')), 'L1305：不产出任何结果'
        assert not list((tmp_path / 'out').rglob('report.md'))
        assert list((tmp_path / 'out').rglob('audit_bundle.json')), '[L1091] 失败也写 bundle'


def test_blocker_b2_triangulation_gra_undefined_surfaces_uncushioned(monkeypatch,
                                                                    tmp_path, capsys):
    '''B2（写集外，dsm/triangulation.py:293）：M_AUM_MINOR 在 12 个主体上恒定，min_max
    归一后该列全 0，`dimensionless` 的两种签认口径（initial / mean）参考值都是 0 ->
    该模块按自己的设计报错（「不回落成第三种口径，那是发明数值 R-12」）。旁路也不许被
    shell 悄悄跳过：[L1348] 的关闭**只有** enabled=false 这一条合法路径，且必须由
    veto() 落注册码披露。'''
    _bypass_l5(monkeypatch)
    conf, data = _stage_data(tmp_path)
    app = _app(conf, triangulation=True)      # 演练 config 的签面值 enabled=true
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    code = cli.main(argv)
    printed = capsys.readouterr().out
    if code == 0:
        run_dir = _run_dirs(tmp_path / 'out')[-1]
        assert sorted(p.name for p in run_dir.iterdir() if p.is_file()) == sorted(SEVEN)
    else:
        assert code == 5, '只允许两种结局：缺陷原样冒出来（5）或已修好（0），实测 ' + repr(code)
        assert 'triangulation' in printed and 'GRA' in printed, printed
        assert not list((tmp_path / 'out').rglob('score_card.csv'))
        assert list((tmp_path / 'out').rglob('audit_bundle.json')), '[L1091]'

# ---------------------------------------------------------------------------
# 3. 治理载体缺失一律 [L1080] 退出码 3 并点名键位（H-5 / R-12 / K-01~K-20）
# ---------------------------------------------------------------------------
def test_missing_l484_soft_deduction_carrier_exits_3_naming_the_key(monkeypatch,
                                                                   tmp_path, capsys):
    '''[L484]「扣减幅度由 grade_rules.yaml 配置」，而 dsm/redline.py:296 的
    soft_deductions 必填无默认、:245 缺比率即抛。载体缺失时 shell 必须按 [L1080]
    退出码 3 点名键位，绝不传一个空映射把 SOFT 命中变成 redline 内部的抛错
    （那会被 exit_code_for 映射成 5「程序缺陷」，是**错的退出码**），更不自定比率。
    ORCH-61 已裁决载体 = grade_rules.yaml 顶层 soft_deductions，CFG-1 并行补齐中。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, drop_grade=('soft_deductions',))
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    assert cli.main(argv) == 3
    printed = capsys.readouterr().out
    assert 'soft_deductions' in printed and 'grade_rules' in printed and '[L484]' in printed
    assert not list((tmp_path / 'out').rglob('score_card.csv')), '[L1091] 非 0 退出不产分数'
    assert list((tmp_path / 'out').rglob('audit_bundle.json')), '[L1091] 失败也写 bundle'


def test_missing_k06_min_coverage_exits_3_naming_the_key(monkeypatch, tmp_path, capsys):
    '''K-06（M38 [L1743]，载体 = eval_config）：dsm/grading.py:90 必填无默认，
    拿不到就退出码 3，绝不上一个默认阈值（那会静默移动全系统的封顶线）。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, drop_eval=('min_coverage_for_absolute_track',))
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    assert cli.main(argv) == 3
    printed = capsys.readouterr().out
    assert 'min_coverage_for_absolute_track' in printed and 'K-06' in printed


def test_missing_sensitivity_block_exits_3_naming_the_key(monkeypatch, tmp_path, capsys):
    '''K-11（M38 [L1748]，载体 = eval_config.sensitivity）：缺段即退出码 3。
    自己发明一个 review_max 就等于替行方挪动 [L1019] 的首屏否决线。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, drop_eval=('sensitivity',))
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    assert cli.main(argv) == 3
    assert 'eval_config.sensitivity' in capsys.readouterr().out


def test_missing_anchor_set_exits_3_instead_of_fabricating_one(monkeypatch, tmp_path,
                                                             capsys):
    '''[L1334] 锚定集参照 + [L941] 锚定集优先：签认配置里没有 T8 就退出码 3，
    shell 绝不编一份锚定成员顶上去（R-12 / K-12）。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf).model_copy(update={'anchor_set': {}})
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    assert cli.main(argv) == 3
    assert 'anchor_set' in capsys.readouterr().out


def test_soft_deductions_are_read_verbatim_never_invented(tmp_path):
    '''载体在时，[L484] 的比率逐字读出（Decimal），一个数也不改、不补、不猜。'''
    conf, _data = _stage_data(tmp_path)
    got = cli._soft_deductions(dsm_config.load_all(conf))
    assert got == {'M_OPTOUT_RATE': Decimal('0.05')}
    assert all(isinstance(value, Decimal) for value in got.values())


def test_wanted_schemes_never_invents_a_scheme_list():
    '''[L1089] dsm score 没有 --schemes -> 跑 dsm/sensitivity.py:67 SCHEME_ORDER 的全部
    方案（[L1350]）；dsm sensitivity 用它自己的 --schemes。SCHEME_ORDER 不在场就
    ModuleMissingError（退出码 5），shell 不自己拟一份方案名单（R-12）。'''
    from dsm import sensitivity
    score = types.SimpleNamespace(args=types.SimpleNamespace(schemes=None))
    assert cli._wanted_schemes(score, sensitivity) == sensitivity.SCHEME_ORDER
    assert set(sensitivity.SCHEME_ORDER) == {'OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP'}
    one = types.SimpleNamespace(args=types.SimpleNamespace(schemes='OAT_10, LOO ,'))
    assert cli._wanted_schemes(one, sensitivity) == ('OAT_10', 'LOO')
    bare = types.SimpleNamespace(__name__='dsm.sensitivity')
    with pytest.raises(cli.ModuleMissingError):
        cli._wanted_schemes(score, bare)


def test_previous_grade_frame_refuses_a_carrier_it_does_not_own():
    '''Step6 滞回的 prev 只认上期 GradeFrame；io_loaders 的 previous_ledger 是 T9 的
    GradeLedgerRow（[L890]），缺 grade_reason_path / capped / cap_reason 三列，硬转就是
    编造（R-12）-> 显式退出码 4，而不是把滞回状态悄悄丢掉（V-14）。'''
    carried = types.SimpleNamespace(inputs=types.SimpleNamespace(previous_ledger=('r1',)))
    with pytest.raises(cli.CliError) as info:
        cli._previous_grade_frame(carried)
    assert info.value.exit_code == 4 and 'GradeFrame' in str(info.value)
    assert cli._previous_grade_frame(types.SimpleNamespace(inputs=None)) is None


def test_downgrade_actions_are_collected_from_all_three_owners():
    '''[L1051] item 13 全量：判定点 preflight + Step1 AttainmentResult.downgrades +
    Step2 逐行 warnings，三个来源汇总去重，shell 一条也不新造、一条也不丢（H-6）。'''
    from dsm.models import DowngradeAction
    one = DowngradeAction(reason_code=RC.MISSING_FACT_RULE_APPLIED.value, action='a',
                          subject='S-001')
    two = DowngradeAction(reason_code=RC.NO_TARGET_VALUE.value, action='b', subject=None)
    gate = types.SimpleNamespace(downgrade_actions=(one,))
    attain = types.SimpleNamespace(downgrades=(one, two))       # one 重复 -> 去重
    row = types.SimpleNamespace(warnings=(two,))
    normalized = types.SimpleNamespace(rows=(row, types.SimpleNamespace(warnings=())))
    got = cli._downgrade_actions(gate, attain, normalized)
    assert got == (one, two)
    assert cli._downgrade_actions(None, None, types.SimpleNamespace(rows=())) == ()


# ---------------------------------------------------------------------------
# 4. V-14 第 4 项：`except OSError: return None` 返工为显式 reason_code + 披露
# ---------------------------------------------------------------------------
def _run_for_failure(tmp_path):
    return cli.Run(cli.build_parser().parse_args(
        ['score', '--period', PERIOD, '--out', str(tmp_path / 'o')]))


def test_write_failure_bundle_oserror_carries_a_reason_code_not_a_silent_none(monkeypatch,
                                                                             tmp_path):
    '''返工前这里是 `except OSError: return None`：[L1091]「任何命令失败都写
    audit_bundle」被无声破掉，调用方只看到 details 少了一行。现在必须给出注册
    reason_code（R-15 单点取码，shell 不自造码、不写字面量 P-8）+ 目标路径 +
    异常类型与原文 + 「审计链不完整」。'''
    run = _run_for_failure(tmp_path)

    def raiser(*args, **kwargs):
        raise OSError(28, 'No space left on device')

    monkeypatch.setattr(pathlib.Path, 'write_text', raiser)
    path, notes = cli._write_failure_bundle(run, ValueError('upstream boom'), 5)
    assert path is None and len(notes) == 1
    note = notes[0]
    assert 'reason_code=' + RC.INVARIANT_VIOLATION.value in note
    assert 'audit_bundle.json' in note and 'OSError' in note
    assert 'No space left on device' in note and 'INCOMPLETE' in note
    # P-8 口径与 tests/test_architecture.py:326 reason_code_literals 一致：AST 扫字符串
    # 常量，注释/docstring 是散文不是发射值（_docstring_ids :189-199），故这里也只扫常量。
    literals = set()
    for node in ast.walk(ast.parse((REPO / 'dsm' / 'cli.py').read_text(encoding='utf-8'))):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)
    assert RC.INVARIANT_VIOLATION.value not in literals, \
        'P-8：reason_code 只能从注册表取（RC.<NAME>.value），cli.py 的字符串常量里不许出现'


def test_write_failure_bundle_without_a_run_still_discloses(tmp_path):
    '''run is None（连 Run 都没建起来）也出一行披露，而不是无声无息地 return None。'''
    path, notes = cli._write_failure_bundle(None, ValueError('boom'), 3)
    assert path is None and len(notes) == 1
    assert 'before a Run existed' in notes[0] and '[L1091]' in notes[0]


def test_write_failure_bundle_success_returns_the_path_and_no_notes(tmp_path):
    '''写成功时 notes 为空（不制造噪声），bundle 仍是 [L1051] 十六列，算不出的列
    保持 PLACEHOLDER（[L878]），绝不用一个假摘要冒充。'''
    run = _run_for_failure(tmp_path)
    path, notes = cli._write_failure_bundle(run, ValueError('boom'), 4)
    assert notes == () and path is not None and path.name == 'audit_bundle.json'
    doc = json.loads(path.read_text(encoding='utf-8'))
    assert set(cli._BUNDLE_KEYS) <= set(doc)
    assert doc['exit_code'] == 4 and doc['error_type'] == 'ValueError'
    assert doc['error'] == 'boom' and doc['output_fingerprints'] == {}
    assert doc['reproducibility_hash'] == cli.PLACEHOLDER


def test_main_prints_the_audit_bundle_write_failure_instead_of_hiding_it(monkeypatch,
                                                                        tmp_path, capsys):
    '''端到端：命令失败（[L484] 载体缺失 -> 3）**且**审计包写盘失败时，main() 必须
    把 reason_code 打到披露面，并且**不**打印 `audit_bundle=`（不假装写成功）。'''
    conf, data = _stage_data(tmp_path)
    app = _app(conf, drop_grade=('soft_deductions',))
    argv = _wire(monkeypatch, app, conf, data) + ['--out', str(tmp_path / 'out')]
    real = pathlib.Path.write_text

    def patched(self, *args, **kwargs):
        if self.name == 'audit_bundle.json':
            raise OSError(13, 'Permission denied')
        return real(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, 'write_text', patched)
    assert cli.main(argv) == 3
    printed = capsys.readouterr().out
    assert 'audit_bundle=' not in printed, '写失败了就不许报告一个不存在的路径'
    assert 'reason_code=' + RC.INVARIANT_VIOLATION.value in printed
    assert 'Permission denied' in printed and 'INCOMPLETE' in printed
