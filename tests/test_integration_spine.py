'''E1 集成骨架 —— M29 每期评分主流程九步全链贯通守护。

唯一事实来源（只读）：
  docs/digest/M29-mainflow.md  SDD 1312-1359 九步主流程 / 判定点 / 失败出口
  docs/digest/M26-reports.md   SDD 1057-1065 report.md 十段、1608-1635 score_card 与 grade_ledger
  docs/digest/M34-fixtures.md  SDD 1455-1463 合成 fixtures 生成规则
  docs/CONTEXT-BRIEF-v1.0.md   已落地 API 与环境事实
  dsm/models.py                47 个契约模型（本文件所有字段名逐字来源）

本文件只守护「链路是否贯通」，不实现任何业务逻辑（E1 生产代码 0 行）。
step 所需模块未落地 -> pytest.skip；落地一个就从 SKIP_REGISTRY 对应条目删掉该路径。

首轮 skip 清单（HEAD b41d84b；当时仅 models/numeric/reason_codes/config/entropy 落地）：
  S0 fixtures              缺 fixtures_gen（tools/ 或 dsm/ 下均无），fixtures/ 目录为空
  S1 io                    缺 dsm/io_loaders.py
  S2 preflight             缺 dsm/preflight.py
  S3 attainment            缺 dsm/attainment.py
  S4 normalize             缺 dsm/normalize.py
  S5 aggregate             缺 dsm/aggregate.py
  S6 grading               缺 dsm/grading.py
  S7 evidence/redline/pooling  缺 dsm/evidence.py、dsm/redline.py、dsm/pooling.py
  S8 sensitivity           缺 dsm/sensitivity.py
  S9 audit/reports         缺 dsm/audit.py、dsm/reports.py
真跑（R-4）的两条：test_skip_registry_matches_worktree、test_spine_contract_layer_is_live。
'''

import importlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# M34 L1455 只给了文件名 fixtures_gen.py，未定路径，故按候选路径做「任一存在」判定。
FIXTURES_GENERATORS = ('tools/fixtures_gen.py', 'dsm/fixtures_gen.py')

# (step_id, 链路位置与出处, 需要的模块路径, 落地判定模式)；顺序即 M29 L1330-1358 数据流顺序。
SPINE = (
    ('S0', 'fixtures 合成数据（M34 L1457-1462：12 策略 / 4 域 / A3B3C4D2 / 7 构造 / >=4 期）',
     FIXTURES_GENERATORS, 'any'),
    ('S1', 'io_loaders 8 表 + InputFingerprints（M29 L1330）',
     ('dsm/io_loaders.py',), 'all'),
    ('S2', 'preflight C-01~C-10 + BLOCK 出口（M29 L1315-1326）',
     ('dsm/preflight.py',), 'all'),
    ('S3', 'Step1 attainment 达成率矩阵 + coverage（M29 L1332）',
     ('dsm/attainment.py',), 'all'),
    ('S4', 'Step2 normalize 池内标准化 + 锚定集参照（M29 L1334）',
     ('dsm/normalize.py',), 'all'),
    ('S5', 'Step5 aggregate composite_absolute / composite_relative（M29 L1342）',
     ('dsm/aggregate.py',), 'all'),
    ('S6', 'Step6 grading 基础等级->封顶->红线覆盖->滞回->版本断点（M29 L1344）',
     ('dsm/grading.py',), 'all'),
    ('S7', 'Step3 evidence + Step4 redline + Step7 pooling（M29 L1338-1346）',
     ('dsm/evidence.py', 'dsm/redline.py', 'dsm/pooling.py'), 'all'),
    ('S8', 'Step8 sensitivity OAT / MC / LOO / NORM_SWAP + 首屏可用性判定（M29 L1350-1354）',
     ('dsm/sensitivity.py',), 'all'),
    ('S9', 'Step9 audit manifest + reproducibility_hash、reports.render 十段（M29 L1356-1358）',
     ('dsm/audit.py', 'dsm/reports.py'), 'all'),
)

# 模块顶部集中登记的 skip 清单：step -> 该 step 依赖的模块路径。
SKIP_REGISTRY = {sid: paths for sid, _title, paths, _mode in SPINE}

# step -> 该 step 输出必须具备的契约模型名（逐字抄 dsm/models.py 的 class 名）。
CONTRACT = {
    'S1': ('InputTableFingerprint',),
    'S2': ('PreflightFinding', 'DowngradeAction'),
    'S3': ('AttainmentRow', 'AttainmentFrame'),
    'S4': ('NormalizedRow', 'NormalizedFrame', 'AnchorSetDoc'),
    'S5': ('ScoreRow', 'ScoreFrame', 'WeightProvenance', 'WeightVersionDoc'),
    'S6': ('GradeRow', 'GradeFrame', 'GradeRuleRow'),
    'S7': ('EvidenceRow', 'EvidenceFrame', 'RedlineEvalRow', 'RedlineFrame', 'RedlineRow',
           'PoolRow', 'PoolFrame', 'PoolKey', 'PoolStats', 'PoolStatRow'),
    'S8': ('SensitivityReport', 'SensitivitySchemeResult', 'SensitivityStrategyRow'),
    'S9': ('AuditBundle', 'ScoreCardRow', 'GradeLedgerRow', 'TriangulationReport',
           'EntropyDiagnosticRow', 'ScoringContext'),
}

# M26 L1610-1626 score_card 各段（字段名逐字抄 dsm/models.py:997-1072）。
SCORE_CARD_FIELDS = (
    'weight_version_id', 'dict_version', 'anchor_set_id', 'run_id',
    'per_metric', 'per_dim', 'composite_absolute', 'composite_relative',
    'evidence_class', 'evidence_reason', 'interpretation_limit',
    'redline_pass', 'redline_flags', 'grade', 'grade_reason_codes',
    'capped_flag', 'cap_reason', 'ranking_pool', 'rank_in_pool', 'pool_size',
    'eligible_for_L1_library', 'l1_gate_reasons',
    'stability_label', 'flip_under_pct10', 'flip_under_pct20',
    'usable_for_elimination', 'value_captured_minor',
)

# M26 L1630-1634 grade_ledger 关键设计（字段名逐字抄 dsm/models.py:1073-1110）。
GRADE_LEDGER_FIELDS = (
    'recommended_action', 'decided_action', 'decision_note',
    'owner_dept', 'owner_name', 'deadline', 'archive_ref', 'ledger_complete',
)

# M29 L1356 audit 必备项（字段名逐字抄 dsm/models.py:1193-1234）。
AUDIT_FIELDS = (
    'run_id', 'run_at', 'period', 'dsm_version', 'design_version',
    'cel_contract_version', 'weight_version_id', 'config_snapshot_sha256',
    'input_fingerprints', 'output_fingerprints', 'sensitivity_schemes', 'seed',
    'preflight_findings', 'downgrade_actions', 'exit_code', 'reproducibility_hash',
)

# M29 L1350 sensitivity 四方案产物（字段名逐字抄 dsm/models.py:1111-1133）。
SENSITIVITY_FIELDS = (
    'by_scheme', 'by_strategy', 'loo_dominant_metrics',
    'norm_swap_rank_correlation', 'flags', 'seed',
)


def _present(rel):
    return (REPO_ROOT / rel).is_file()


def _fixtures_landed():
    if any(_present(p) for p in FIXTURES_GENERATORS):
        return True
    fx_dir = REPO_ROOT / 'fixtures'
    return fx_dir.is_dir() and any(p.is_file() for p in fx_dir.rglob('*'))


def _landed(step_id):
    for sid, _title, paths, mode in SPINE:
        if sid != step_id:
            continue
        if sid == 'S0':
            return _fixtures_landed()
        if mode == 'all':
            return all(_present(p) for p in paths)
        return any(_present(p) for p in paths)
    raise AssertionError('SPINE 未登记的 step: ' + step_id)


def _missing(step_id):
    paths = SKIP_REGISTRY[step_id]
    if _landed(step_id):
        return ()
    if step_id == 'S0':
        return paths + ('fixtures/ 内无生成文件',)
    return tuple(p for p in paths if not _present(p)) or paths


def _require(step_id):
    if not _landed(step_id):
        pytest.skip('step ' + step_id + ' 未落地；缺模块: ' + ', '.join(_missing(step_id))
                    + '（落地后请删除 SKIP_REGISTRY 对应条目）')


def _import_step_modules(step_id):
    mods = {}
    for rel in SKIP_REGISTRY[step_id]:
        if not _present(rel):
            continue
        dotted = rel[:-3].replace('/', '.')
        mods[dotted] = importlib.import_module(dotted)
    return mods


def _public_callables(mod):
    return sorted(n for n in dir(mod) if not n.startswith('_') and callable(getattr(mod, n)))


def test_skip_registry_matches_worktree():
    '''真跑：skip 清单与工作树自洽，九步编号齐全，地基模块在场。'''
    assert tuple(SKIP_REGISTRY) == tuple(sid for sid, _t, _p, _m in SPINE)
    assert len(SPINE) == 10, 'spine 必须覆盖 M29 九步 + fixtures/io/preflight/reports 前置后置'
    assert tuple(CONTRACT) == ('S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9')
    for sid, paths in SKIP_REGISTRY.items():
        assert paths, 'SKIP_REGISTRY[' + sid + '] 为空：模块已落地就不该再留在清单里'
        for rel in paths:
            if sid == 'S0':
                continue
            assert (REPO_ROOT / rel).parent.is_dir(), '登记路径的父目录不存在: ' + rel
    for sid in SKIP_REGISTRY:
        if _landed(sid):
            assert not _missing(sid), sid + ' 已落地但仍报缺: ' + str(_missing(sid))
        else:
            assert _missing(sid), sid + ' 未落地但 missing 为空，skip 理由会失真'
    for rel in ('dsm/models.py', 'dsm/numeric.py', 'dsm/reason_codes.py',
                'dsm/config.py', 'dsm/entropy.py'):
        assert _present(rel), '地基模块缺失: ' + rel
    landed = tuple(sid for sid in SKIP_REGISTRY if _landed(sid))
    assert isinstance(landed, tuple)


def test_spine_contract_layer_is_live():
    '''真跑：九步契约层（models.py）+ numeric / reason_codes 口径已在场。'''
    models = importlib.import_module('dsm.models')
    for sid, names in CONTRACT.items():
        for name in names:
            assert hasattr(models, name), 'step ' + sid + ' 缺契约模型: ' + name
    assert models.InputFingerprints is not None, 'M29 L1330 要求 InputFingerprints 别名'

    card = set(models.ScoreCardRow.model_fields)
    absent = tuple(f for f in SCORE_CARD_FIELDS if f not in card)
    assert not absent, 'score_card 缺段（M26 L1610-1626）: ' + ', '.join(absent)
    assert models.ScoreCardMetricCell is not None and models.ScoreCardDimCell is not None

    ledger = set(models.GradeLedgerRow.model_fields)
    absent = tuple(f for f in GRADE_LEDGER_FIELDS if f not in ledger)
    assert not absent, 'grade_ledger 缺列（M26 L1630-1634）: ' + ', '.join(absent)
    assert 'recommended_action' in ledger and 'decided_action' in ledger

    audit = set(models.AuditBundle.model_fields)
    absent = tuple(f for f in AUDIT_FIELDS if f not in audit)
    assert not absent, 'audit_bundle 缺项（M29 L1356）: ' + ', '.join(absent)

    sens = set(models.SensitivityReport.model_fields)
    absent = tuple(f for f in SENSITIVITY_FIELDS if f not in sens)
    assert not absent, 'sensitivity_report 缺项（M29 L1350）: ' + ', '.join(absent)

    numeric = importlib.import_module('dsm.numeric')
    # M29 L1332：无目标值 -> attainment = null，不得用均值或 0 代替。
    assert numeric.safe_div(numeric.D('3'), numeric.D('0'), on_zero=None) is None
    assert numeric.eq_tol(numeric.D('1'), numeric.D('1'))

    rc = importlib.import_module('dsm.reason_codes')
    # CONTEXT-BRIEF 5.1：写 CSV / 拼 message / 算 hash 必须用 .value。
    assert rc.RC.STABLE.value == 'STABLE'
    assert rc.severity(rc.RC.STABLE) in (rc.Severity.INFO, rc.Severity.WARN, rc.Severity.BLOCK)


def test_step0_fixtures_ready():
    '''S0 fixtures：M34 L1457-1462 的 12 策略 / 4 域 / A3B3C4D2 / 7 构造 / >=4 期。

    内容级不变量由 A1 自己的守护测试负责；本 step 只确认骨架能拿到 fixtures 产物。
    '''
    _require('S0')
    fx_dir = REPO_ROOT / 'fixtures'
    assert fx_dir.is_dir(), 'M34 要求 fixtures/ 承载合成数据'
    assert any(p.is_file() for p in fx_dir.rglob('*')) or any(
        _present(p) for p in FIXTURES_GENERATORS), 'fixtures 产物与生成器均不可见'


def test_step1_io_loaders():
    '''S1 io：8 表 + InputFingerprints（SHA256 / 行数）（M29 L1330）。'''
    _require('S1')
    mods = _import_step_modules('S1')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step2_preflight():
    '''S2 preflight：C-01~C-10 十项校验；BLOCK -> 写 audit_bundle + 退出码 2（M29 L1318-1326）。'''
    _require('S2')
    mods = _import_step_modules('S2')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step3_attainment():
    '''S3 attainment：达成率矩阵 + coverage，无目标值 -> null（M29 L1332）。'''
    _require('S3')
    mods = _import_step_modules('S3')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step4_normalize():
    '''S4 normalize：池内标准化 + 锚定集参照，失效 -> 回退 + 首屏标注（M29 L1334）。'''
    _require('S4')
    mods = _import_step_modules('S4')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step5_aggregate():
    '''S5 aggregate：composite_absolute + composite_relative，只读 FROZEN 权重（M29 L1342）。'''
    _require('S5')
    mods = _import_step_modules('S5')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step6_grading():
    '''S6 grading：基础等级->证据封顶->目标封顶->红线覆盖->滞回->版本断点（M29 L1344）。'''
    _require('S6')
    mods = _import_step_modules('S6')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step7_evidence_redline_pooling():
    '''S7 evidence(A/B/C/D 短路) + redline(HARD/SOFT) + pooling(分池禁混排)（M29 L1338-1346）。'''
    _require('S7')
    mods = _import_step_modules('S7')
    assert set(mods) == {'dsm.evidence', 'dsm.redline', 'dsm.pooling'}
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step8_sensitivity():
    '''S8 sensitivity：OAT / MC / LOO / NORM_SWAP -> flip_rate + 稳定性标签；
    flip_rate > review_max 或 METHOD_DIVERGENCE -> usable_for_elimination = false（M29 L1350-1354）。'''
    _require('S8')
    mods = _import_step_modules('S8')
    assert mods
    for name, mod in mods.items():
        assert _public_callables(mod), name + ' 未暴露任何公开入口，spine 无法接线'


def test_step9_audit_reports_full_chain():
    '''S9 audit + reports，并在此做「九步全贯通」终检（M29 L1356-1358 / M26 L1061-1064）。'''
    not_ready = [(sid, _missing(sid)) for sid in SKIP_REGISTRY if not _landed(sid)]
    if not_ready:
        detail = '; '.join(sid + ' 缺 ' + ', '.join(miss) for sid, miss in not_ready)
        pytest.skip('九步未全贯通，仍缺: ' + detail)
    for sid in ('S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8', 'S9'):
        mods = _import_step_modules(sid)
        assert mods, 'step ' + sid + ' 登记路径存在但导入不到模块'
        for name, mod in mods.items():
            assert _public_callables(mod), name + ' 未暴露任何公开入口，九步无法串联'
    reports = importlib.import_module('dsm.reports')
    assert hasattr(reports, 'render'), 'M26 L1061 要求 def render(bundle, frames, config) -> ReportSet'
    cfg = importlib.import_module('dsm.config')
    assert hasattr(cfg, 'load_all'), 'M29 L1328 要求 config.load_all() 并在 PLACEHOLDER 时抛错'
