'''P2a 集成骨架 —— M29 每期评分主流程九步全链贯通守护（E1 skip 已清除）。

唯一事实来源（只读）：
  docs/digest/M29-mainflow.md  SDD 1312-1359 九步主流程 / 判定点 / 失败出口
  docs/digest/M26-reports.md   SDD 1057-1065 report.md 十段、1608-1635 score_card / grade_ledger
  docs/digest/M34-fixtures.md  SDD 1455-1463 合成 fixtures 生成规则
  dsm/models.py                47 个契约模型（本文件所有字段名逐字来源）

P2a 变更（相对 E1 首轮）：SKIP_REGISTRY 全部清空，九步一律用 fixtures/** 的**冻结真实
数据**驱动**真实模块**（不 mock、不自造 fixtures）。仅剩两处 skip，写在测试函数体内，
落地即自动解锁：
  pytest.importorskip('dsm.weights_calibrate')  -> A3 未落地（L0b 标定，M29 主流程外）
  pytest.importorskip('dsm.whatif')             -> A4 未落地（L0b 预演，M29 主流程外）

九步顺序逐字照 M29 L1330-1358：io_loaders -> Step1 attainment -> Step2 normalize ->
Step3 evidence -> Step4 redline -> Step5 aggregate -> Step6 grading -> Step7 pooling ->
Step8 sensitivity（flip_rate 回灌 Step7 准入）-> Step9 audit + reports.render。
preflight（M29 L1315-1326）是九步之前的判定点，BLOCK 出口单独守护。

评价期取 fixtures 的历史期 2026-Q2（M34 L1462：标定窗口 >= 4 期历史事实数据），因为主
评价期 2026-Q3 的 metric_fact 有 4 个刻意缺失单元格，其中一个落在 HARD 红线指标上
（S-008/v1/M_COMPLAINT_RATE），dsm/redline.py 按 V-14 拒绝默认 -> Step4 整步跑不起来；
该冲突与另外 4 条一并保持 RED 并上报，由主控裁决归属（P2「跨模块缺陷由主控裁决归属」）。

治理值纪律：仓库 config/ 为空、K-01~K-20 未签认，spine **不拟定任何业务值**。
GOVERNANCE 里每一项要么逐字来自冻结 fixtures（fixtures_gen 常量），要么与本仓库已落地
守护测试所用测试夹具同值，并在行内注明出处；缺配置时一律断言模块抛错（V-14），不喂默认值。
'''

import csv
import dataclasses
import inspect
import json
import pathlib
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from dsm import (aggregate, attainment, audit, evidence, fixtures_gen as fg, grading,
                 io_loaders, normalize, numeric, pooling, preflight, redline, reports,
                 sensitivity)
from dsm.models import (AnchorSetDoc, AttainmentRow, DesignCardRow, GradeLedgerRow,
                        GradeRuleRow, MetricDictRow, PoolKey, ScoreCardDimCell,
                        ScoreCardMetricCell, ScoreCardRow, ScoringContext, WeightVersionDoc)
from dsm.reason_codes import RC, is_registered, message

D = Decimal
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURES = REPO_ROOT / 'fixtures'
INPUT_DIR = FIXTURES / 'input'

# E1 的 SKIP_REGISTRY 已清空：M29 九步的模块全部在场，只留两处 L0b importorskip（文件尾）。
SPINE_MODULES = ('dsm.io_loaders', 'dsm.preflight', 'dsm.attainment', 'dsm.normalize',
                 'dsm.evidence', 'dsm.redline', 'dsm.aggregate', 'dsm.grading',
                 'dsm.pooling', 'dsm.sensitivity', 'dsm.audit', 'dsm.reports')
REMAINING_SKIPS = ('dsm.weights_calibrate', 'dsm.whatif')

# 评价期：fixtures 4 期历史窗口里事实表**完整**的一期（12 主体 x 15 指标 = 180 行）。
PERIOD = '2026-Q2'
PREVIOUS_PERIOD = '2026-Q1'
EVAL_PERIOD = fg.EVAL_PERIOD          # 2026-Q3，事实表有 4 个刻意缺失单元格
RUN_AT = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)   # = fg.SNAPSHOT_TIME，注入时钟（H-8）
RUN_ID = fg.RUN_ID
SEED = fg.SEED_DEFAULT

# 治理入参：全部有出处，无一项为 spine 拟定。
#   attainment_cap / on_zero / signed_off_statuses  -> tests/test_attainment.py:30,60 同值夹具
#   missing_rate_warn / missing_rate_block          -> tests/test_preflight.py:128-129 同值夹具
#   min_coverage_for_absolute_track (K-06)          -> tests/test_grading.py:49,274 同值夹具
#   significance_keywords ([L979] 外置清单)         -> 取冻结 fixtures 自己的 success_criteria
#                                                      词面，否则 M34 L1459 四类路径全不可达
#   soft_deductions                                 -> 0..1 比率，与 tests/test_redline.py 同量级
GOVERNANCE = {
    'attainment_cap': D('1.2'), 'on_zero': None, 'signed_off_statuses': ('SIGNED',),
    'missing_rate_warn': D('0.1'), 'missing_rate_block': D('0.3'),
    'normalize_method': 'min_max', 'min_pool_size': 1, 'normalize_on_zero': D('0'),
    'sd_dof': 1, 'evidence_mode': 'GATE_ONLY', 'cel_enabled': True,
    'significance_keywords': ('SYNTH_SUCC_CRITERIA',),
    'min_coverage_for_absolute_track': D('0.6'), 'upgrade_consecutive_periods': 2,
    'demotion_immediate': True, 'soft_deductions': {'M_OPTOUT_RATE': D('0.05')},
}
# sensitivity 配置键：与 tests/test_sensitivity.py:33-38 的测试夹具同值（digest 只固定
# stable_max 0.05 / review_max 0.15 / loo_sampling_threshold 60，其余必填无默认）。
SENSITIVITY_CONFIG = {
    'stable_max': '0.05', 'review_max': '0.15', 'loo_sampling_threshold': 60,
    'mc_samples': 8, 'dirichlet_concentration': '20', 'loo_dominant_flip_rate': '0.2',
    'loo_sample_size_per_dim': 1, 'norm_swap_method': 'z_score',
    'norm_swap_min_rank_correlation': '0.9',
}


def _jsonl(name):
    text = (INPUT_DIR / name).read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _cell(value):
    '''冻结 JSONL 的单元格 -> CSV 文本。只换容器，不改值（R-2）。'''
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple)):
        return ','.join(str(item) for item in value)
    return str(value)


def _write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    header = sorted({key for row in rows for key in row})
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        for row in rows:
            writer.writerow([_cell(row.get(column)) for column in header])
    return path


def _stage(root, period, with_design_cards):
    '''把冻结 fixtures 摆成 dsm/io_loaders.py 的 [L888] 目录口径：
    T2/T5 在 config 目录，T1/T3/T4 在 data/<period>/。'''
    conf, data = root / 'config', root / 'data'
    _write_csv(conf / 'metric_dict.csv', _jsonl('metric_dict.jsonl'))
    _write_csv(conf / 'redlines.csv', _jsonl('redline.jsonl'))
    _write_csv(data / period / 'strategy_master.csv', _jsonl('strategy_master.jsonl'))
    if with_design_cards:
        _write_csv(data / period / 'design_cards.csv', _jsonl('design_card.jsonl'))
    facts = [row for row in _jsonl('metric_fact.jsonl') if row['period'] == period]
    _write_csv(data / period / 'metric_facts.csv', facts)
    return conf, data


def _governance_docs():
    '''T6/T7/T8（weights / grade_rules / anchor_set）是 YAML、归 dsm/config.py（[L877]），
    但仓库 config/ 为空 -> 逐字用冻结 fixtures 的 JSONL 载荷按 R-2 构造成契约模型。'''
    return (WeightVersionDoc(**_jsonl('weight_version.jsonl')[0]),
            AnchorSetDoc(**_jsonl('anchor_set.jsonl')[0]),
            tuple(GradeRuleRow(**row) for row in _jsonl('grade_rule.jsonl')))


def _design_cards():
    return tuple(DesignCardRow(**row) for row in _jsonl('design_card.jsonl'))


def _run_chain(root, period):
    '''M29 L1330-1358 九步：全部真实模块、全部真实 fixtures 数据。

    每一步的入参都来自上一步的真实返回值，没有手填中间值。design_cards 走 R-2 构造，
    原因见 test_step1_io_loaders_loads_the_frozen_design_card_table（RED 冲突 #1）。
    '''
    weight_version, anchor_set, rule_rows = _governance_docs()
    conf, data = _stage(root, period, with_design_cards=False)
    loaded = io_loaders.load_inputs(data, period, conf, previous_period=PREVIOUS_PERIOD)
    inputs = dataclasses.replace(loaded.inputs, design_cards=_design_cards())

    # 判定点 preflight（M29 L1315-1326）
    preflight_config = preflight.PreflightConfig(
        period=period, period_ref_date=fg.DATA_AS_OF, weight_version=weight_version,
        anchor_set=anchor_set, signed_signoff_status=GOVERNANCE['signed_off_statuses'],
        missing_rate_warn=GOVERNANCE['missing_rate_warn'],
        missing_rate_block=GOVERNANCE['missing_rate_block'])
    preflight_result = preflight.run(inputs, preflight_config)

    # Step 1 attainment（M29 L1332）
    attain = attainment.compute(
        inputs.metric_facts, inputs.metric_dict,
        params=attainment.AttainmentParams(
            attainment_cap=GOVERNANCE['attainment_cap'], on_zero=GOVERNANCE['on_zero'],
            signed_off_statuses=GOVERNANCE['signed_off_statuses']))

    # Step 3 evidence（M29 L1338）。D-MODELS-01 已由 ORCH-29 第 4 条 / ORCH-32 第 4 条
    # 收口为「Step2 松键 / Step7 严键」：PoolKey.evidence_class 现为可选，Step2 可以
    # 只用 T1 的 biz_domain 构键而先于 Step3 跑（见下方松键专验测试）。本 chain 仍按
    # 严键走（九步贯通的参照口径不变，reproducibility_hash 因此不受松键影响）。
    ev = evidence.classify(
        inputs.design_cards, inputs.metric_facts,
        params=evidence.EvidenceParams(
            evidence_mode=GOVERNANCE['evidence_mode'],
            cel_enabled=GOVERNANCE['cel_enabled'],
            significance_keywords=GOVERNANCE['significance_keywords']))

    # Step 2 normalize（M29 L1334）
    domain_of = {row.strategy_id: row.biz_domain for row in inputs.strategy_master}
    class_of = {row.strategy_id: row.evidence_class for row in ev.rows}
    pools = {sid: PoolKey(biz_domain=domain_of[sid], evidence_class=class_of[sid])
             for sid in sorted(domain_of)}
    normalized = normalize.compute(
        attain, inputs.metric_dict, anchor_set,
        params=normalize.NormalizeParams(
            method=GOVERNANCE['normalize_method'],
            min_pool_size=GOVERNANCE['min_pool_size'],
            on_zero=GOVERNANCE['normalize_on_zero'], sd_dof=GOVERNANCE['sd_dof']),
        pools=pools)

    # Step 4 redline（M29 L1340）：HARD 强制降级 / SOFT 独立扣减，不进加权
    red = redline.evaluate(inputs.metric_facts, redline.RedlineSet(rows=inputs.redlines),
                           redline.WaiverSet(rows=()), as_of=fg.DATA_AS_OF,
                           soft_deductions=GOVERNANCE['soft_deductions'],
                           metric_dict=inputs.metric_dict)

    # Step 5 aggregate（M29 L1342）：只读 FROZEN 权重（INV-3）
    scores = aggregate.compose(attain, normalized, weight_version, None)

    # Step 6 grading（M29 L1344）
    rules = grading.GradeRuleSet(
        rows=rule_rows,
        min_coverage_for_absolute_track=GOVERNANCE['min_coverage_for_absolute_track'],
        upgrade_consecutive_periods=GOVERNANCE['upgrade_consecutive_periods'],
        demotion_immediate=GOVERNANCE['demotion_immediate'])
    grades = grading.assign(scores, attain, ev, red, None, rules)

    # Step 7 pooling（M29 L1346）：此时 Step 8 未跑，稳健性未知 -> 一级库全不准入
    pool, pool_stats = pooling.build(
        scores, grades, ev, inputs.strategy_master, None, sensitivity=None,
        params=pooling.PoolingParams(min_pool_size=GOVERNANCE['min_pool_size']))

    context = ScoringContext(
        period=period, run_at=RUN_AT, run_id=RUN_ID, seed=SEED,
        weight_version_id=weight_version.weight_version_id,
        evidence_mode=GOVERNANCE['evidence_mode'], cel_enabled=GOVERNANCE['cel_enabled'],
        input_fingerprints=loaded.fingerprints, attainment=attain, normalized=normalized,
        evidence=ev, redline=red, score=scores, grade=grades, pool=pool,
        pool_stats=pool_stats)

    def grade_fn(frame):
        '''Step 8 注入的 Step 6 钩子：真实 grading.assign，不是桩。'''
        rerun = grading.assign(frame, attain, ev, red, None, rules)
        return {(r.strategy_id, r.version_id, r.period): r.grade for r in rerun.rows}

    def normalizer(values, method):
        '''Step 8 NORM_SWAP 注入的 Step 2 钩子：换方法后由真实 normalize.compute 重算。'''
        dictionary = [MetricDictRow(
            metric_id='M_SWAP', metric_name='M_SWAP', dim_code='D_SWAP', numerator_def='n',
            time_window='MONTHLY', dedup_rule='NONE', missing_rule='SKIP',
            outlier_rule='NONE', attainment_formula='RATIO_DIRECT', direction=1,
            unit='RATIO', target_value=D('1'), target_basis='budget', is_redline=False,
            owner_name='o', signoff_status='SIGNED', dim_signoff_status='SIGNED',
            dict_version=fg.DICT_VERSION, caliber_version=fg.CALIBER_VERSION)]
        rows = [AttainmentRow(strategy_id='X%03d' % i, version_id='v1', period=period,
                              metric_id='M_SWAP', attainment=value, direction=1,
                              has_target=True, capped_flag=False)
                for i, value in enumerate(values)]
        key = PoolKey(biz_domain='D_SWAP', evidence_class='A')
        empty_anchor = AnchorSetDoc(anchor_set_id='AS-EMPTY', strategy_ids=(),
                                    effective_from=fg.DATA_AS_OF,
                                    effective_to=fg.DATA_AS_OF,
                                    rationale='no anchor for a method swap')
        frame = normalize.compute(
            rows, dictionary, empty_anchor,
            params=normalize.NormalizeParams(method=method, min_pool_size=1,
                                             on_zero=GOVERNANCE['normalize_on_zero'],
                                             sd_dof=GOVERNANCE['sd_dof']),
            pools={'X%03d' % i: key for i in range(len(values))})
        got = {row.strategy_id: row.norm_value for row in frame.rows}
        return [got['X%03d' % i] for i in range(len(values))]

    # Step 8 sensitivity（M29 L1350-1354）：四方案全跑，seed 由 ScoringContext 注入
    sens = sensitivity.run(context, sensitivity.SCHEME_ORDER, dict(SENSITIVITY_CONFIG),
                           weights=weight_version, grade_fn=grade_fn, normalizer=normalizer)

    # Step 8 -> Step 7 回灌：flip_rate 决定一级库准入（M29 L1352-1354）
    pool2, pool_stats2 = pooling.build(
        scores, grades, ev, inputs.strategy_master, None, sensitivity=sens,
        params=pooling.PoolingParams(min_pool_size=GOVERNANCE['min_pool_size']))

    # Step 9 audit + reports（M29 L1356-1358）：两张表由九步真实产物装配
    card_rows, ledger_rows = _assemble_outputs(inputs, attain, ev, red, scores, grades,
                                               pool2, sens, weight_version, anchor_set)
    run_context = audit.RunContext(
        run_id=RUN_ID, run_at=RUN_AT, period=period, dsm_version='1.1.0',
        design_version='DSM-v1.1', cel_contract_version='CEL-0',
        weight_version_id=weight_version.weight_version_id, seed=SEED,
        sensitivity_schemes=sensitivity.SCHEME_ORDER,
        preflight_findings=tuple(f.to_audit_finding() for f in preflight_result.findings),
        downgrade_actions=tuple(preflight_result.downgrade_actions), exit_code=0,
        score_card=card_rows, grade_ledger=ledger_rows)
    bundle = audit.build_manifest(loaded.fingerprints, {'eval_config': {}}, run_context, {})
    frames = reports.AllFrames(
        gate_status=reports.GateStatus(g5_dispute_source_review_signed=False,
                                       g7_governance_config_signed=False),
        attainment=attain, evidence=ev, redline=red, score=scores, pool=pool2,
        pool_stats=pool_stats2, sensitivity=sens, triangulation=None,
        entropy_diagnostics=(), score_card=card_rows, grade_ledger=ledger_rows,
        weight_provenance=None)
    report_set = reports.render(bundle, frames, None)
    return dict(loaded=loaded, inputs=inputs, weight_version=weight_version,
                anchor_set=anchor_set, rule_rows=rule_rows,
                preflight_config=preflight_config, preflight=preflight_result,
                attain=attain, normalized=normalized, evidence=ev, redline=red,
                scores=scores, grades=grades, rules=rules, pool=pool,
                pool_stats=pool_stats, pool_reflow=pool2, pool_stats_reflow=pool_stats2,
                sensitivity=sens, context=context, score_card=card_rows,
                grade_ledger=ledger_rows, bundle=bundle, frames=frames,
                report_set=report_set, reproducibility_hash=bundle.reproducibility_hash)


def _assemble_outputs(inputs, attain, ev, red, scores, grades, pool, sens,
                      weight_version, anchor_set):
    '''M26 L1610-1626 / L1630-1634：score_card 与 grade_ledger 的每一格都取自九步真实产物。'''
    fact_of = {(f.strategy_id, f.version_id, f.metric_id): f for f in inputs.metric_facts}
    dict_of = {m.metric_id: m for m in inputs.metric_dict}
    attain_of = {(r.strategy_id, r.version_id, r.metric_id): r for r in attain.rows}
    ev_of = {(r.strategy_id, r.version_id): r for r in ev.rows}
    grade_of = {(r.strategy_id, r.version_id, r.period): r for r in grades.rows}
    pool_of = {(r.strategy_id, r.version_id, r.period): r for r in pool.rows}
    stable_of = {(r.strategy_id, r.version_id): r for r in sens.by_strategy}
    vetoed = sensitivity.is_vetoed(sens)
    size_of = {}
    for row in pool.rows:
        size_of[(row.pool_key.biz_domain, row.pool_key.evidence_class)] = \
            size_of.get((row.pool_key.biz_domain, row.pool_key.evidence_class), 0) + 1
    dict_version = dict_of[sorted(dict_of)[0]].dict_version
    cards, ledger = [], []
    for score in sorted(scores.rows, key=lambda r: (r.strategy_id, r.version_id)):
        key = (score.strategy_id, score.version_id, score.period)
        grade, pool_row = grade_of[key], pool_of[key]
        ev_row = ev_of[(score.strategy_id, score.version_id)]
        per_metric = {}
        for metric_id in sorted(dict_of):
            fact = fact_of.get((score.strategy_id, score.version_id, metric_id))
            if fact is None:
                continue          # 缺事实 = 缺格，不填 0（V-14）
            row = attain_of.get((score.strategy_id, score.version_id, metric_id))
            per_metric[metric_id] = ScoreCardMetricCell(
                actual_value=fact.value, target_value=dict_of[metric_id].target_value,
                attainment=(row.attainment if row else None))
        per_dim = {dim: ScoreCardDimCell(
            coverage=score.coverage, weight=weight_version.level1_weights[dim],
            attainment=score.dim_absolute[dim], relative_score=score.dim_relative.get(dim))
            for dim in sorted(score.dim_absolute)}
        hard = [r for r in red.rows if r.strategy_id == score.strategy_id
                and r.version_id == score.version_id and r.level == 'HARD' and r.hit]
        stable = stable_of.get((score.strategy_id, score.version_id))
        usable = bool(grade.usable_for_elimination and not vetoed)
        cards.append(ScoreCardRow(
            strategy_id=score.strategy_id, version_id=score.version_id,
            period=score.period, weight_version_id=weight_version.weight_version_id,
            dict_version=dict_version, anchor_set_id=anchor_set.anchor_set_id,
            run_id=RUN_ID, per_metric=per_metric, per_dim=per_dim,
            composite_absolute=score.composite_absolute,
            composite_relative=score.composite_relative,
            evidence_class=ev_row.evidence_class, evidence_reason=ev_row.evidence_reason,
            evidence_source=ev_row.evidence_source,
            interpretation_limit=ev_row.interpretation_limit,
            redline_pass=not hard, redline_flags=tuple(r.reason_code for r in hard),
            grade=grade.grade, grade_reason_codes=tuple(grade.grade_reason_path),
            capped_flag=grade.capped, cap_reason=grade.cap_reason,
            ranking_pool=pool_row.pool_key, rank_in_pool=pool_row.pool_rank,
            pool_size=size_of[(pool_row.pool_key.biz_domain,
                               pool_row.pool_key.evidence_class)],
            eligible_for_L1_library=pool_row.primary_pool_eligible,
            l1_gate_reasons=() if pool_row.reject_reason is None else (pool_row.reject_reason,),
            stability_label=(stable.stability_label if stable else None),
            flip_under_pct10=(stable.flip_under_pct10 if stable else None),
            flip_under_pct20=(stable.flip_under_pct20 if stable else None),
            usable_for_elimination=usable))
        master = [m for m in inputs.strategy_master if m.strategy_id == score.strategy_id][0]
        row = GradeLedgerRow(
            strategy_id=score.strategy_id, version_id=score.version_id, period=score.period,
            grade=grade.grade, previous_grade=None,
            recommended_action=(' | '.join(grade.action) if grade.action else None),
            owner_dept=master.owner_dept, owner_name=master.owner_name,
            ledger_complete=True, usable_for_elimination=usable)
        ledger.append(row.model_copy(
            update={'ledger_complete': not reports.ledger_missing_items(row)}))
    return tuple(cards), tuple(ledger)


@pytest.fixture(scope='module')
def chain(tmp_path_factory):
    return _run_chain(tmp_path_factory.mktemp('p2a-spine'), PERIOD)


def test_spine_skip_registry_cleared_to_calibrate_and_whatif():
    '''P2 第一项交付：E1 的 SKIP_REGISTRY 全部清除，M29 九步模块全部在场。

    仅剩的两个 skip 门是 L0b 的 dsm.weights_calibrate（A3）与 dsm.whatif（A4），
    用 pytest.importorskip 写在测试函数体内，落地即自动解锁；本包执行期间二者均已落地
    （commit 9c45b81 之后），故 SKIP 实测为 0，见文件尾两条 test_l0b_*。
    '''
    import importlib.util
    for dotted in SPINE_MODULES:
        module = importlib.import_module(dotted)
        public = [n for n in dir(module) if not n.startswith('_')
                  and callable(getattr(module, n))]
        assert public, dotted + ' 未暴露任何公开入口，九步无法接线'
    assert len(SPINE_MODULES) == 12 and len(REMAINING_SKIPS) == 2
    landed = [d for d in REMAINING_SKIPS if importlib.util.find_spec(d) is not None]
    assert set(landed) <= set(REMAINING_SKIPS)
    # 除 L0b 两处 importorskip 外，本文件不允许任何别的 skip 门
    source = pathlib.Path(__file__).read_text(encoding='utf-8')
    gate = 'module = pytest.' + 'importorskip('
    assert source.count(gate) == 2
    assert ('pytest.' + 'skip(') not in source, 'spine 不许再有别的 skip 门'
    assert ('x' + 'fail') not in source, 'spine 不许用预期失败标记掩盖 RED'


def test_step0_fixtures_frozen_bundle_matches_m34():
    '''Step 0 fixtures（M34 L1457-1462）：12 策略 / 4 域 / A3B3C4D2 / 7 构造 / >= 4 期。'''
    manifest = json.loads((FIXTURES / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['counts']['strategy_master'] == 13      # 12 策略，S-005 有 v1/v2 两版
    assert len(set(fg.STRATEGY_IDS)) == 12
    assert len(fg.BIZ_DOMAINS) == 4 and len(fg.SEGMENT_TYPES) == 3
    assert manifest['counts']['metric_dict'] == 15
    assert manifest['counts']['metric_fact'] == 896
    assert len(fg.HISTORY_PERIODS) >= 4, 'M34 L1462 要求 >= 4 期历史事实数据'
    assert len(manifest['deliberate_constructions']) == 7, 'M34 L1460 的 7 个刻意构造'
    intent = list(fg.EVIDENCE_INTENT.values())
    assert (intent.count('A'), intent.count('B'), intent.count('C'),
            intent.count('D')) == (3, 3, 4, 2), 'M34 L1459 的证据分布（构造意图）'
    assert {row['period'] for row in _jsonl('metric_fact.jsonl')} == set(fg.ALL_PERIODS)


def test_step1_io_loaders_real_tables_and_fingerprints(chain):
    '''io（M29 L1330）：8 表 + InputFingerprints（SHA256 / 行数），空值就是空值。'''
    loaded, inputs = chain['loaded'], chain['inputs']
    assert sorted(loaded.fingerprints) == ['metric_dict.csv', 'metric_facts.csv',
                                           'redlines.csv', 'strategy_master.csv']
    for fingerprint in loaded.fingerprints.values():
        assert len(fingerprint.sha256) == 64
        assert isinstance(fingerprint.row_count, int) and fingerprint.row_count > 0
    assert loaded.fingerprints['metric_facts.csv'].row_count == 180   # 12 主体 x 15 指标
    assert len(inputs.strategy_master) == 13 and len(inputs.metric_dict) == 15
    assert len(inputs.metric_facts) == 180 and len(inputs.redlines) == 3
    assert len(inputs.design_cards) == 13
    # [L890]：无上期 grade_ledger -> FIRST_PERIOD，不臆造上期等级
    assert inputs.previous_ledger == ()
    first = [i for i in loaded.issues if i.code == RC.FIRST_PERIOD.value]
    assert first and first[0].table == 'grade_ledger'
    # V-9：MONEY_MINOR 走 int、RATIO 走 Decimal，一个 float 都不许有
    money = [f for f in inputs.metric_facts if f.metric_id == 'M_REV_MINOR']
    assert money and all(isinstance(f.value, int) for f in money)
    ratio = [f for f in inputs.metric_facts if f.metric_id == 'M_ROI']
    assert ratio and all(isinstance(f.value, Decimal) for f in ratio)
    assert not any(isinstance(f.value, float) for f in inputs.metric_facts)


def test_step1_io_loaders_loads_the_frozen_design_card_table(tmp_path):
    '''RED（跨模块契约冲突 #1，归属待主控裁决）。

    原文：M29 L1330「io_loaders -> 8 表 + InputFingerprints（SHA256 / 行数）」；
          M34 L1455-1463 冻结的 fixtures 落在 fixtures/input/*.jsonl。
    实测：dsm/io_loaders.py:read_table 只认 .csv / .parquet（其它后缀 -> CoercionError
          MISSING_FILE），冻结的 JSONL 容器一张表都读不了；转成 CSV 后
          design_card.jsonl 第 11/12 行（S-010 card_status=MISSING、S-011 PARTIAL）的
          success_criteria 是空串，被 NULL_LITERALS 判成 None，而
          models.DesignCardRow.success_criteria 是必填 str ->
          DataLoadError「design_cards row 11/12 refused by DesignCardRow:
          success_criteria」（kind=MODEL_ROW_REJECTED，属 BLOCKING_KINDS），
          8 表里的 T4 永远加载不出来。
    归属判定：dsm/fixtures_gen.py（A1：容器为 JSONL、空串取值）与 dsm/io_loaders.py
          （C1：只支持 CSV/Parquet，'' 即 null）之间。请主控裁决是 A1 补 CSV 变体、
          io_loaders 支持 JSONL，还是 models 放宽 success_criteria 为可空。
    '''
    conf, data = _stage(tmp_path, PERIOD, with_design_cards=True)
    loaded = io_loaders.load_inputs(data, PERIOD, conf, previous_period=PREVIOUS_PERIOD)
    assert len(loaded.inputs.design_cards) == 13


def test_step2_preflight_block_exit_writes_audit_bundle_and_no_score_card(chain):
    '''preflight BLOCK 出口（M29 L1322-1326）：写 audit_bundle、退出码 2、不产 score_card。'''
    result, config = chain['preflight'], chain['preflight_config']
    assert result.status == 'BLOCK' and result.exit_code == 2
    codes = {(f.code, f.reason_code) for f in result.findings}
    assert ('C-01', 'WEIGHT_MISSING_WHATIF_RUN_ID') in codes
    # V-14 / [L1282]：十条检查全部执行、不短路，BLOCK 时也一次列出全部违规
    assert len(result.findings) == 6
    assert {f.code for f in result.findings} == {'C-01', 'C-02', 'C-04', 'C-08', 'C-10'}
    # 降级台账真实产出：未签认指标被剔除、不可评价主体单列（M29 L1346 NOT_ASSESSED）
    assert result.dropped_metrics == ('M_REPEAT_USE_COUNT',)
    assert result.not_assessed == ('S-005', 'S-010')
    assert result.emptied_dims == ()
    assert result.coverage_after_drop and all(
        isinstance(v, Decimal) for v in result.coverage_after_drop.values())
    context = {'run_id': RUN_ID, 'run_at': RUN_AT, 'dsm_version': '1.1.0',
               'design_version': 'DSM-v1.1', 'cel_contract_version': 'CEL-0',
               'config_snapshot_sha256': 'ab' * 32, 'seed': SEED,
               'input_fingerprints': chain['loaded'].fingerprints,
               'sensitivity_schemes': sensitivity.SCHEME_ORDER,
               'reproducibility_hash': audit.reproducibility_hash(
                   (), (), config.weight_version.weight_version_id)}
    bundle = preflight.build_audit_bundle(result, config, context)
    assert bundle.exit_code == 2
    assert bundle.output_fingerprints == {}, 'M29 L1326：BLOCK 不产出 score_card'
    assert len(bundle.preflight_findings) == 6 and bundle.downgrade_actions
    assert 'score_card' not in type(bundle).model_fields
    # V-14：run_context 缺 audit 注入字段 -> 抛错，不喂默认值让它通过
    broken = dict(context)
    broken.pop('reproducibility_hash')
    with pytest.raises(preflight.PreflightError):
        preflight.build_audit_bundle(result, config, broken)


def test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures(chain):
    '''RED（跨模块契约冲突 #2，归属待主控裁决）。

    原文：M29 L1322「status=PASS/WARN」才进 dsm score 的九步；L1324-1326「status=BLOCK
          -> 写 audit_bundle / 退出码 2 / 不产出 score_card」。
    实测：冻结 fixtures 在任何一期都是 BLOCK，三条互相独立的阻塞项：
      (a) C-01 WEIGHT_MISSING_WHATIF_RUN_ID —— fixtures/input/weight_version.jsonl 的
          status=FROZEN 而 provenance=null；whatif_run_id 只能由 A4 whatif 产出，A4 此刻
          未落地，而 dsm/aggregate.py:_check_weights 又要求「only FROZEN weights may
          score [L1190]」-> 冻结 fixtures 无法同时满足 C-01 与 Step5。
      (b) C-08 EVIDENCE_CARD_MISSING（S-010 card_status=MISSING，M34 的 D 类构造）被判为
          整轮 BLOCK，而 M29 L1346 要求 NOT_ASSESSED 单列而不是停跑；preflight 自己也已
          把 S-010 记进 not_assessed，等于同一事实两处口径。
      (c) C-04 MISSING_RATE_BLOCK（strategy_master 同时有 S-005 v1/v2，评价期 2026-Q3
          只有 v2 的事实行，v1 缺失率 14/14 = 1.0 > 0.3），同样只是单主体不可评价。
    归属判定：(a) dsm/fixtures_gen.py（A1，FROZEN 权重缺 provenance/whatif_run_id），
          或由主控裁定「A4 落地前 C-01 降为 WARN」；(b)(c) dsm/preflight.py（C2，
          blocks_run 的口径）与 M29 L1346 冲突。
    '''
    assert chain['preflight'].status in ('PASS', 'WARN')


def test_step1_attainment_matrix_and_coverage_from_real_facts(chain):
    '''Step 1（M29 L1332）：达成率矩阵 + coverage，无目标值 -> null，不用均值代替。'''
    attain, inputs = chain['attain'], chain['inputs']
    assert len(attain.rows) == 180 == len(inputs.metric_facts)
    assert len(attain.attainment_coverage) == 12
    for value in attain.attainment_coverage.values():
        assert isinstance(value, Decimal) and numeric.ZERO <= value <= numeric.ONE
    cap = GOVERNANCE['attainment_cap']
    assert any(r.capped_flag and r.reason_code == RC.ATTAINMENT_CAPPED.value
               for r in attain.rows), '冻结 fixtures 应有被封顶的行'
    for row in attain.rows:
        if row.attainment is not None:
            assert row.attainment <= cap, '达成率上限就是注入的 attainment_cap'
        if row.capped_flag:
            assert numeric.eq_tol(row.attainment, cap)
        assert row.reason_code is None or is_registered(row.reason_code)
    # 入参确实来自 io 的真实产物：定位键与事实表逐一对应（不得手填中间值）
    assert {(r.strategy_id, r.version_id, r.period, r.metric_id) for r in attain.rows} == \
        {(f.strategy_id, f.version_id, f.period, f.metric_id) for f in inputs.metric_facts}
    # 未签认指标 M_REPEAT_USE_COUNT（signoff_status=PENDING）不进 coverage 分母（G-10）
    assert 'M_REPEAT_USE_COUNT' in chain['preflight'].dropped_metrics


def test_step2_normalize_pool_and_anchor_from_step1_rows(chain):
    '''Step 2（M29 L1334）：池内标准化 + 锚定集参照，失效 -> 回退 + 首屏标注。'''
    normalized, attain = chain['normalized'], chain['attain']
    assert normalized.rows, 'Step2 的入参是 Step1 的真实产物，不得为空'
    attain_keys = {(r.strategy_id, r.version_id, r.period, r.metric_id)
                   for r in attain.rows if r.attainment is not None}
    norm_keys = {(r.strategy_id, r.version_id, r.period, r.metric_id)
                 for r in normalized.rows}
    assert norm_keys <= attain_keys, 'Step2 不得凭空产生 Step1 没有的行'
    # ORCH-32 裁决 5：Step2 少掉的每一行都必须在 frame 级 excluded 逐条留痕，
    # 不得有任何一行惄惄消失（V-14）。本 chain 的 on_zero = Decimal('0')，
    # 两边都应为空集；该不变式在 on_zero = None 时同样成立（见 test_normalize.py）。
    excluded_keys = {(r.strategy_id, r.version_id, r.period, r.metric_id)
                     for r in normalized.excluded}
    assert excluded_keys == attain_keys - norm_keys, '剔除必须逐行留痕'
    assert all(is_registered(r.reason_code) for r in normalized.excluded)
    assert all(isinstance(r.norm_value, Decimal) for r in normalized.rows)
    # 锚定集参照命中 -> anchor_used True；失效 -> 回退 + 标注码（不静默降级）
    assert any(r.anchor_used for r in normalized.rows)
    assert any(not r.anchor_used for r in normalized.rows)
    # ORCH-32 裁决 3（唯一指定修法）：回退改**读 frame 级披露通道**举证。
    # 主控已明确否决「放宽为 anchor_used=False 落任一已注册降级码」（属弱化）：
    # row 单值槽按冻结优先序（INACTIVE_METRIC > ANCHOR_SET_STALE >
    # RANK_REVERSAL_RISK > SMALL_POOL）只装得下第一枚，而 M_AUM_MINOR 的锚定
    # 参考尺退化后又零变异 -> 单值槽读 INACTIVE_METRIC，第二枚 RANK_REVERSAL_RISK
    # 必须在 NormalizedFrame.warnings 里逐行可读（ORCH-32 裁决 2，V-14）。
    fallback_locators = {(r.strategy_id, r.version_id, r.period, r.metric_id)
                         for r in normalized.rows if not r.anchor_used}
    assert fallback_locators, '锚定尺退化路径必须可达（不得靠放宽断言绕过）'
    disclosed = set()
    for w in normalized.warnings:
        key = tuple(w.subject.split(normalize.SUBJECT_SEP))
        assert is_registered(w.reason_code), '只允许已注册 reason_code'
        assert w.action == message(w.reason_code), '措辞归注册表，模块不拟话术'
        if key in fallback_locators:
            disclosed.add(w.reason_code)
    assert RC.RANK_REVERSAL_RISK.value in disclosed, (
        '锚定参考尺退化回退当期池内统计时必须披露 RANK_REVERSAL_RISK')
    # 单值槽优先序未被为迎合本断言而上调（ORCH-32 裁决 1）
    assert RC.RANK_REVERSAL_RISK.value not in {
        r.reason_code for r in normalized.rows
        if r.metric_id == fg.ZERO_VARIATION_METRIC}
    assert all(r.reason_code is None or is_registered(r.reason_code)
               for r in normalized.rows), '只允许已注册 reason_code'
    # 零变异指标 M_AUM_MINOR（M34 构造 5）-> INACTIVE_METRIC，不填 0（V-14）
    inactive = [r for r in normalized.rows if r.metric_id == fg.ZERO_VARIATION_METRIC]
    assert inactive
    assert all(r.reason_code == RC.INACTIVE_METRIC.value for r in inactive)
    # 池键逐字来自 T1 的 biz_domain x Step3 的 evidence_class，不跨池混标
    class_of = {row.strategy_id: row.evidence_class for row in chain['evidence'].rows}
    assert {r.pool_key for r in normalized.rows} == {
        PoolKey(biz_domain=m.biz_domain, evidence_class=class_of[m.strategy_id])
        for m in chain['inputs'].strategy_master}


def test_step2_pool_key_cannot_be_built_before_step3_evidence():
    '''D-MODELS-01 已关（ORCH-29 第 4 条 / ORCH-32 第 4 条）：本断言现在守护的是
    「PoolKey.evidence_class 必须保持可选」，即 Step2 能先于 Step3 构键。
    函数名保留原缺陷场景的叙述，以免打断 ops/dag-state.json 与
    docs/deliverables/V-ACCEPTANCE-EVIDENCE.md 对该测试名的交叉引用；断言本身
    一字未改（RED -> GREEN，不属放宽）。松键/严键的行为验证另见
    test_step2_loose_key_at_step2_and_strict_key_at_step7。

    以下为原 RED 上报原文（保留作缺陷史料）：

    原文：M29 L1334「Step 2 normalize -> 池内标准化 + 锚定集参照」排在 L1338
          「Step 3 evidence -> A/B/C/D（短路判定；C 缺解释限制 -> D）」之前。
    实测：dsm/normalize.py:compute 的 pools 是**必填**入参（非 Mapping 即抛
          NormalizeInputError），而 models.PoolKey.evidence_class 是必填字段
          （本断言实测 is_required() == True）；normalize.py 自己的 docstring 亦写明
          「the pool key (biz_domain x evidence_class) comes from T1 and from the S5
          evidence layer」。-> Step 2 无法只凭 Step 1 与 T1 构造池键，必须先跑 Step 3。
          spine 因此在数据流上先算 Step3 evidence 再算 Step2 normalize，与 M29
          L1334/L1338 的绘制顺序相反。
    归属判定：dsm/normalize.py（B 链，池键口径）与 M29 L1334-1338 的顺序口径之间。
          请主控裁决是改 normalize 的池键为「Step2 只用 biz_domain、Step7 再按证据分池」，
          还是在 M29 数据流里把 evidence 提到 normalize 之前。
    '''
    assert not PoolKey.model_fields['evidence_class'].is_required()


def test_step2_loose_key_at_step2_and_strict_key_at_step7(chain):
    '''ORCH-32 裁决 3 允许的**补充**测试（不替代原断言）：松键/严键分工。

    Step2 松键：只用 T1 的 biz_domain 构键，evidence_class 留 None（**不得**填默认
    值伪造，V-14），且 Step2 确实能在 Step3 之前跑完（只读 Step1 产物 + T1）。
    锚定参考尺不按池裁剪（ORCH-28 裁决 1），故锚定命中的行 norm_value 与严键
    逐位相同；松键只改「回退当期池内统计」的分区口径（ORCH-29 第 4 条）。
    Step7 严键：缺 evidence_class 即抛，绝不拿 None 当第五类混排（P-6 / G-02）。
    '''
    inputs, attain = chain['inputs'], chain['attain']
    domain_of = {row.strategy_id: row.biz_domain for row in inputs.strategy_master}
    loose = {sid: normalize.step2_pool_key(domain_of[sid]) for sid in sorted(domain_of)}
    assert all(k.evidence_class is None for k in loose.values())
    frame = normalize.compute(
        attain, inputs.metric_dict, chain['anchor_set'],
        params=normalize.NormalizeParams(
            method=GOVERNANCE['normalize_method'],
            min_pool_size=GOVERNANCE['min_pool_size'],
            on_zero=GOVERNANCE['normalize_on_zero'], sd_dof=GOVERNANCE['sd_dof']),
        pools=loose)
    assert frame.rows, '松键下 Step2 仍须产出行（不依赖 Step3）'
    assert {r.pool_key.evidence_class for r in frame.rows} == {None}
    assert {r.pool_key.biz_domain for r in frame.rows} == set(domain_of.values())
    strict = {(r.strategy_id, r.version_id, r.period, r.metric_id): r
              for r in chain['normalized'].rows}
    for row in frame.rows:
        assert row.pool_key == normalize.step2_pool_key(domain_of[row.strategy_id])
        if row.anchor_used:
            ref = strict[(row.strategy_id, row.version_id, row.period, row.metric_id)]
            assert numeric.eq_tol(row.norm_value, ref.norm_value), (
                '锚定尺与分区无关，松键不得改变锚定命中行的 norm_value')
    # Step7 严键：evidence_class 缺失即抛，不回退成松键、不填默认值
    with pytest.raises(pooling.PoolingInputError):
        pooling.step7_pool_key('CARD', None)
    assert pooling.step7_pool_key('CARD', 'A') == PoolKey(biz_domain='CARD',
                                                          evidence_class='A')


def test_step3_evidence_gate_only_does_not_enter_the_score(chain):
    '''Step 3（M29 L1338 + M26 L1617-1618）：GATE_ONLY 只做门禁，不乘进分数。'''
    assert chain['context'].evidence_mode == 'GATE_ONLY'
    ev, scores, wv = chain['evidence'], chain['scores'], chain['weight_version']
    assert len(ev.rows) == 13
    assert {row.evidence_class for row in ev.rows} <= {'A', 'B', 'C', 'D'}
    for row in ev.rows:
        assert is_registered(row.evidence_reason)
        if row.evidence_class == 'C':
            assert row.interpretation_limit, 'M26 L1618：C 类必填解释限制'
        if row.evidence_reason == 'EVIDENCE_C_NO_LIMIT':
            assert row.evidence_class == 'D', 'M29 L1338：C 缺解释限制 -> D'
    # GATE_ONLY 的守护点：证据不以任何系数形式乘进分数。
    # (1) Step5 的签名里没有证据入参，ScoreRow 里也没有证据列；
    assert 'evidence' not in inspect.signature(aggregate.compose).parameters
    assert not ({'evidence_class', 'evidence_reason', 'evidence_discount'}
                & set(type(scores.rows[0]).model_fields))
    # (2) DISCOUNT 模式被 dsm/evidence.py 直接拒绝 -> 不存在可乘入的折减系数；
    with pytest.raises(evidence.EvidenceDiscountError):
        evidence.classify(chain['inputs'].design_cards, chain['inputs'].metric_facts,
                          params=evidence.EvidenceParams(
                              evidence_mode='DISCOUNT',
                              cel_enabled=GOVERNANCE['cel_enabled'],
                              significance_keywords=GOVERNANCE['significance_keywords']))
    # (3) 把整份证据帧的等级改成 D 再重跑 Step5，composite 一字不变（差分证明）。
    flattened = type(ev)(rows=tuple(
        r.model_copy(update={'evidence_class': 'D'}) for r in ev.rows))
    assert {r.evidence_class for r in flattened.rows} == {'D'}
    again = aggregate.compose(chain['attain'], chain['normalized'], wv, None)
    assert [(r.strategy_id, r.composite_absolute, r.composite_relative)
            for r in again.rows] == [(r.strategy_id, r.composite_absolute,
                                      r.composite_relative) for r in scores.rows]
    # (4) 证据只在 Step6 当门禁用：A 与 D 并存，等级差来自封顶而不是分数差。
    # 证据等级 A 与 D 并存，却共用同一个 composite 口径 -> 分数不含证据因子
    classes = {row.evidence_class for row in ev.rows}
    assert 'A' in classes and 'D' in classes


def test_step3_evidence_covers_the_m34_a3b3c4d2_distribution(chain):
    '''RED（跨模块契约冲突 #4，归属待主控裁决）。

    原文：M34 L1459「证据分布：A x3、B x3、C x4、D x2（确保四类路径都被走到）」。
    实测：用冻结 fixtures 的 13 张 design_card 跑真实 dsm/evidence.py:classify，
          按主体去重得 A x3 / B x0 / C x4 / D x5 —— B 类一条都走不到。三张准实验卡
          （S-004 / S-005 / S-007，eval_method=DID、control_arrangement=
          CONCURRENT_CONTROL，fixtures_gen.EVIDENCE_INTENT 标为 B）的
          interpretation_limit 为 null，被 evidence 第 5 步「C 缺解释限制 -> D」压到 D
          （evidence_reason=EVIDENCE_C_NO_LIMIT）；fixtures 只给 OBSERVATIONAL_ONLY 卡
          填了 interpretation_limit。四类路径因此只走到三类。
    归属判定：dsm/fixtures_gen.py（A1，B 类卡缺 interpretation_limit / 缺 B 路径判据）；
          次要嫌疑 dsm/evidence.py 的 B 判据口径。请主控裁决。
    '''
    subjects = {}
    for row in chain['evidence'].rows:
        subjects.setdefault(row.strategy_id, row.evidence_class)
    by_subject = {key: sum(1 for v in subjects.values() if v == key)
                  for key in ('A', 'B', 'C', 'D')}
    assert by_subject == {'A': 3, 'B': 3, 'C': 4, 'D': 2}, by_subject


def test_step4_redline_runs_on_the_frozen_eval_period_fact_table(tmp_path):
    '''RED（跨模块契约冲突 #5，归属待主控裁决）。

    原文：M29 L1340「Step 4 redline -> HARD 强制降级 / SOFT 独立扣减（不进加权）」；
          M34 L1461「随机数全部由 --seed 控制」；V-14 无静默降级。
    实测：主评价期 2026-Q3（fixtures_gen.EVAL_PERIOD）的 metric_fact 只有 176 行，
          12 主体 x 15 指标 = 180，缺 4 格：S-005/v2 M_CAMPAIGN_COST_MINOR、
          S-006/v1 M_CUST_GAIN、S-008/v1 M_COMPLAINT_RATE、S-011/v1 M_ROI；
          其中 M_COMPLAINT_RATE 是 HARD 红线指标 -> dsm/redline.py:evaluate 抛
          RedlineInputError「红线指标缺事实行，不得默认未触发（V-14）:
          S-008 / v1 / 2026-Q3 / M_COMPLAINT_RATE」。Step 4 在主评价期整步跑不起来，
          Step5~Step9 随之全断；spine 只能改用事实表完整的历史期 2026-Q2 贯通九步。
    归属判定：dsm/fixtures_gen.py（A1，随机缺失单元格落在红线指标上）。redline 的拒绝
          本身是 V-14 的正确行为，不应改。请主控裁决由 A1 补齐红线指标的事实行。
    '''
    conf, data = _stage(tmp_path, EVAL_PERIOD, with_design_cards=False)
    loaded = io_loaders.load_inputs(data, EVAL_PERIOD, conf, previous_period=PREVIOUS_PERIOD)
    inputs = dataclasses.replace(loaded.inputs, design_cards=_design_cards())
    frame = redline.evaluate(inputs.metric_facts, redline.RedlineSet(rows=inputs.redlines),
                             redline.WaiverSet(rows=()), as_of=fg.DATA_AS_OF,
                             soft_deductions=GOVERNANCE['soft_deductions'],
                             metric_dict=inputs.metric_dict)
    assert frame.rows


def test_step4_redline_changes_grade_not_score(chain):
    '''Step 4 守护点（M29 L1340 / M26 L1619）：红线不改分数、只改等级，且不进加权。'''
    red, scores, grades = chain['redline'], chain['scores'], chain['grades']
    assert len(red.rows) == 36 == 12 * len(chain['inputs'].redlines)
    # 红线判定与业绩解耦：RedlineEvalRow 里没有任何分数列（P0-2 非补偿）
    assert not ({'composite_absolute', 'composite_relative', 'score', 'attainment'}
                & set(type(red.rows[0]).model_fields))
    # Step 5 的签名里根本没有 redline 入参 -> 红线不进加权
    assert 'redline' not in inspect.signature(aggregate.compose).parameters
    assert 'rl' not in inspect.signature(aggregate.compose).parameters
    # Step 6 才吃红线：grading.assign 的入参里有 rl（HARD 强制降级 / SOFT 独立扣减）
    assert 'rl' in inspect.signature(grading.assign).parameters
    # 分数与红线无关：重跑 Step5（完全不引用 red）输出一字不差
    again = aggregate.compose(chain['attain'], chain['normalized'],
                              chain['weight_version'], None)
    assert [(r.strategy_id, r.composite_absolute, r.composite_relative)
            for r in again.rows] == [(r.strategy_id, r.composite_absolute,
                                      r.composite_relative) for r in scores.rows]
    for row in red.rows:
        assert row.reason_code is None or is_registered(row.reason_code)
        assert row.level in ('HARD', 'SOFT')
        if row.level == 'SOFT' and row.hit:
            assert row.soft_deduction is not None
    # 豁免必须有留痕：冻结 fixtures 无豁免表 -> 全部为空，不静默当成已豁免（G-15）
    assert all(r.waiver_approval_id is None for r in red.rows)
    for row in grades.rows:
        assert all(is_registered(code) for code in row.grade_reason_path)


def test_step5_aggregate_dual_track_reads_only_frozen_weights(chain):
    '''Step 5（M29 L1342 / M26 L1615-1616）：双轨聚合，只读 FROZEN 权重（INV-3）。'''
    scores, wv = chain['scores'], chain['weight_version']
    assert len(scores.rows) == 12
    assert numeric.eq_tol(sum((numeric.D(w) for w in wv.level1_weights.values()),
                              numeric.ZERO), numeric.ONE)
    for row in scores.rows:
        assert row.weight_version_id == wv.weight_version_id      # [L955]
        assert row.operator == 'LINEAR'
        assert isinstance(row.composite_absolute, Decimal)
        assert isinstance(row.composite_relative, Decimal)
    # 主分数用于定级、辅分数只用于同池排名（M26 L1615-1616）：两轨不同源
    assert any(r.composite_absolute != r.composite_relative for r in scores.rows)
    # INV-3 / [L1190]：非 FROZEN 权重直接拒绝，不降级
    with pytest.raises(aggregate.AggregateError):
        aggregate.compose(chain['attain'], chain['normalized'],
                          wv.model_copy(update={'status': 'DRAFT'}), None)
    # 入参来自 Step1 / Step2 的真实产物：定位键一致
    assert {(r.strategy_id, r.version_id, r.period) for r in scores.rows} == \
        {(r.strategy_id, r.version_id, r.period) for r in chain['attain'].rows}


def test_step6_grading_caps_by_evidence_without_touching_the_score(chain):
    '''Step 6（M29 L1344）：基础等级 -> 证据封顶 -> 目标封顶 -> 红线覆盖 -> 滞回 -> 版本断点。'''
    grades, scores = chain['grades'], chain['scores']
    assert len(grades.rows) == len(scores.rows) == 12
    grade_of = {(r.strategy_id, r.version_id, r.period): r for r in grades.rows}
    score_of = {(r.strategy_id, r.version_id, r.period): r for r in scores.rows}
    # 证据封顶：S-003 的 composite_absolute 全场最高，却因 C 类被压到 L2 且 capped=True
    top = max(scores.rows, key=lambda r: r.composite_absolute)
    assert top.strategy_id == 'S-003'
    capped = grade_of[(top.strategy_id, top.version_id, top.period)]
    assert capped.grade == 'L2' and capped.capped is True
    assert RC.GR_EVIDENCE_GATE_L1.value in tuple(capped.grade_reason_path)
    # 守护点：封顶只改等级，分数一字未动（M26 L1620-1621）
    assert numeric.eq_tol(score_of[(top.strategy_id, top.version_id, top.period)]
                          .composite_absolute, top.composite_absolute)
    # 滞回 / 版本断点：无上期台账 -> FIRST_PERIOD 进判定路径，不臆造上期等级
    assert all(RC.FIRST_PERIOD.value in tuple(r.grade_reason_path)
               for r in grades.rows if r.grade != 'NOT_ASSESSED')
    # NOT_ASSESSED 单列，不给最低等级（M29 L1346）
    assessed = [r for r in grades.rows if r.grade != 'NOT_ASSESSED']
    naive = [r for r in grades.rows if r.grade == 'NOT_ASSESSED']
    assert len(assessed) == 7 and len(naive) == 5
    assert all(r.usable_for_elimination is False for r in naive)
    assert all(r.grade in ('L1', 'L2', 'L3', 'L4') for r in assessed)
    for row in grades.rows:
        assert all(is_registered(code) for code in row.grade_reason_path)
        if row.capped:
            assert row.cap_reason is None or is_registered(row.cap_reason)


def test_step7_pooling_never_ranks_across_pools(chain):
    '''Step 7（M29 L1346 / M26 L1622）：分池禁混排 + 一级库门禁 + 占比双报 + NOT_ASSESSED 单列。'''
    pool, stats, scores = chain['pool'], chain['pool_stats'], chain['scores']
    assert len(pool.rows) == 12
    score_of = {(r.strategy_id, r.version_id, r.period): r for r in scores.rows}
    master = {m.strategy_id: m.biz_domain for m in chain['inputs'].strategy_master}
    groups = pooling.groups(pool)
    assert groups and sum(len(rows) for rows in groups.values()) == 12
    for key, rows in groups.items():
        assert isinstance(key, PoolKey)
        assert all(r.pool_key == key for r in rows), '不得跨池混排'
        assert all(master[r.strategy_id] == key.biz_domain for r in rows)
        ranked = sorted(r.pool_rank for r in rows if r.pool_rank is not None)
        assert ranked == list(range(1, len(ranked) + 1))
        ordered = sorted((r for r in rows if r.pool_rank is not None),
                         key=lambda r: r.pool_rank)
        relatives = [score_of[(r.strategy_id, r.version_id, r.period)].composite_relative
                     for r in ordered]
        assert relatives == sorted(relatives, reverse=True), '池内名次必须由本池相对分决定'
    # 占比双报（[L1006] / M26 L1614）：池内占比分母是本域，全局占比分母是已参评总数
    assessed_total = sum(r.count for r in stats.rows)
    assert assessed_total == 12 - stats.not_assessed_count == 7
    for row in stats.rows:
        assert numeric.eq_tol(row.share_overall,
                              numeric.safe_div(D(row.count), D(assessed_total),
                                               on_zero=None))
        assert row.share_in_pool is not None
    # 证据结构四类闭合 + NOT_ASSESSED 单列，禁止只报合并占比（M26 L1064）
    assert set(stats.evidence_structure) == {'A', 'B', 'C', 'D'}
    assert sum(stats.evidence_structure.values()) == 12
    assert stats.not_assessed_count == 5
    assert all(is_registered(code) for code in stats.not_assessed_reasons)
    # Step 8 还没回灌时，一级库一个都不准入（稳健性未知 -> 举证制，[L1002]）
    assert not any(r.primary_pool_eligible for r in pool.rows)


def test_step8_sensitivity_flip_rate_reflows_into_step7_gate(chain):
    '''Step 8（M29 L1350-1354）：四方案 -> flip_rate + 稳定性标签，回灌 Step 7 一级库准入。'''
    sens, before, after = chain['sensitivity'], chain['pool'], chain['pool_reflow']
    assert [s.scheme for s in sens.by_scheme] == list(sensitivity.SCHEME_ORDER)
    assert list(sensitivity.SCHEME_ORDER) == ['OAT_10', 'OAT_20', 'MC', 'LOO', 'NORM_SWAP']
    assert sens.seed == SEED, '[L1017]：seed 由 ScoringContext 注入，一个 seed 一份报告'
    for result in sens.by_scheme:
        assert isinstance(result.overall_flip_rate, Decimal)
        assert numeric.eq_tol(result.overall_flip_rate,
                              numeric.safe_div(D(result.flipped_count),
                                               D(result.assessed_count), on_zero=None))
        assert result.assessed_count == 7      # 12 主体去掉 5 个 NOT_ASSESSED
        assert result.flag is None or is_registered(result.flag)
    assert sens.loo_dominant_metrics, 'M34 构造 6：主导权重指标必须被 LOO 点出来'
    assert sens.norm_swap_rank_correlation is not None
    assert all(is_registered(code) for code in sens.flags)
    for row in sens.by_strategy:
        assert row.stability_label in ('STABLE', 'NEAR_BOUNDARY', 'UNSTABLE')
    # 首屏可用性判定（M29 L1352-1354）：flip_rate > review_max -> 本期暂停淘汰
    verdict = sensitivity.veto(sens)
    over = [s for s in sens.by_scheme
            if s.overall_flip_rate > numeric.D(SENSITIVITY_CONFIG['review_max'])]
    assert over and verdict.vetoed is True and verdict.usable_for_elimination is False
    assert RC.FLIP_RATE_UNUSABLE.value in verdict.codes
    # [L1019]：否决权只有布尔与码，没有分数字段，不能被加权抵消
    assert not ({f.name for f in dataclasses.fields(verdict)}
                & {'score', 'delta', 'deduction', 'points'})
    # 回灌：Step7 用同一份 Step5/Step6 产物重跑，准入结论随 flip_rate 变化
    assert {(r.strategy_id, r.version_id) for r in before.rows} == \
        {(r.strategy_id, r.version_id) for r in after.rows}
    assert not any(r.primary_pool_eligible for r in after.rows)
    robust = [r for r in after.rows if r.reject_reason == RC.PRIMARY_POOL_REJECTED_ROBUST]
    assert robust, 'A/B 类且已参评的策略必须被 flip_rate 挡在一级库外'
    assert all(r.pool_key.evidence_class in ('A', 'B') for r in robust)
    gate = [r for r in after.rows if r.reject_reason == RC.PRIMARY_POOL_REJECTED_EVIDENCE]
    assert gate and all(r.pool_key.evidence_class == 'C' for r in gate)
    # 稳定性标签与可用性落到 score_card（M26 L1624-1625）
    assert {row.usable_for_elimination for row in chain['score_card']} == {False}
    assert any(row.stability_label is not None for row in chain['score_card'])


def test_step9_audit_manifest_and_reports_ten_sections(chain):
    '''Step 9（M29 L1356-1358 / M26 L1061-1064）：manifest 十六项 + report.md 十段 + 七件产物。'''
    bundle, report_set = chain['bundle'], chain['report_set']
    for field in ('run_id', 'run_at', 'period', 'dsm_version', 'design_version',
                  'cel_contract_version', 'weight_version_id', 'config_snapshot_sha256',
                  'input_fingerprints', 'output_fingerprints', 'sensitivity_schemes',
                  'seed', 'preflight_findings', 'downgrade_actions', 'exit_code',
                  'reproducibility_hash'):
        assert field in type(bundle).model_fields, 'M29 L1356 缺 audit 项: ' + field
    assert bundle.period == PERIOD and bundle.seed == SEED and bundle.exit_code == 0
    assert bundle.weight_version_id == fg.WEIGHT_VERSION_ID
    assert len(bundle.config_snapshot_sha256) == 64
    assert tuple(bundle.sensitivity_schemes) == tuple(sorted(sensitivity.SCHEME_ORDER))
    assert bundle.input_fingerprints == chain['loaded'].fingerprints
    assert len(bundle.reproducibility_hash) == 64
    # 可复算：hash 只由 score_card + grade_ledger + weight_version_id 决定（[L1052]）
    assert bundle.reproducibility_hash == audit.reproducibility_hash(
        chain['score_card'], chain['grade_ledger'], bundle.weight_version_id)
    # report.md 十段固定结构与顺序（M26 L1063）+ 七件产物（M26 L1062）
    assert reports.section_titles(report_set.report_md) == reports.REPORT_SECTIONS
    assert len(reports.assert_report_sections(report_set.report_md)) == 10
    assert len(reports.ARTIFACT_NAMES) == 7
    for name in ('report_md', 'score_card_csv', 'grade_ledger_csv',
                 'sensitivity_report_csv', 'entropy_diagnostic_csv', 'triangulation_md',
                 'audit_json'):
        assert getattr(report_set, name), name
    # 首屏第一段必须写 usable_for_elimination 与其依据（M26 L1064）
    first = reports.split_sections(report_set.report_md)[reports.REPORT_SECTIONS[0]]
    assert ('usable_for_elimination' in first or '淘汰' in first or '可用性' in first)
    # G5 / G7 未签认 -> 首屏声明必须在场，不得只放附录（CONTEXT-BRIEF §9）
    assert reports.GATE_STATEMENT in report_set.report_md
    # K-01~K-20 一律 PLACEHOLDER，报告不得把它们写成已签认值
    assert reports.OPEN_PARAMETER_IDS == tuple('K-%02d' % i for i in range(1, 21))
    assert (reports.PLACEHOLDER in report_set.report_md
            or reports.OPEN_PARAMETER_IDS[0] in report_set.report_md)
    # 两张表的每一格都来自九步真实产物，行数与 Step5 一致
    assert len(chain['score_card']) == len(chain['grade_ledger']) == 12
    for row in chain['score_card']:
        assert row.run_id == RUN_ID and row.dict_version == fg.DICT_VERSION
        assert row.anchor_set_id == fg.ANCHOR_SET_ID
        assert isinstance(row.ranking_pool, PoolKey)
        assert row.per_metric
        assert all(isinstance(c.actual_value, (int, Decimal))
                   for c in row.per_metric.values())
        assert set(row.per_dim) <= set(chain['weight_version'].level1_weights)
        assert all(isinstance(c.weight, Decimal) and c.coverage is not None
                   for c in row.per_dim.values())
        assert row.evidence_class in ('A', 'B', 'C', 'D')
        assert is_registered(row.evidence_reason)
    # M26 L1630：recommended_action 与 decided_action 分两列，人做决定并签字
    for row in chain['grade_ledger']:
        assert 'recommended_action' in type(row).model_fields
        assert 'decided_action' in type(row).model_fields
        assert row.decided_action is None, '模型只给建议，决定必须留给人签字'
        assert isinstance(row.ledger_complete, bool)


def test_reproducibility_hash_is_identical_across_two_runs(tmp_path_factory):
    '''V-3 / G-12：同一 fixtures + 同一 seed 连跑两次，reproducibility_hash 精确相等。'''
    first = _run_chain(tmp_path_factory.mktemp('p2a-run-1'), PERIOD)
    second = _run_chain(tmp_path_factory.mktemp('p2a-run-2'), PERIOD)
    assert first['reproducibility_hash'] == second['reproducibility_hash']
    assert len(first['reproducibility_hash']) == 64
    # G-12 的 L1 半边：输入指纹（SHA256 / 行数）同样逐字节相等
    assert first['loaded'].fingerprints == second['loaded'].fingerprints
    # 不只比最后一个哈希：九步中间产物逐项相等
    for key in ('attain', 'normalized', 'evidence', 'redline', 'scores', 'grades',
                'pool_reflow', 'pool_stats_reflow', 'sensitivity', 'score_card',
                'grade_ledger'):
        assert first[key] == second[key], key
    # [L1053]：换一个语义位（权重版本）哈希必须变，证明它不是常量
    assert audit.reproducibility_hash(
        first['score_card'], first['grade_ledger'],
        fg.OAT20_WEIGHT_VERSION_ID) != first['reproducibility_hash']
    assert first['bundle'].exit_code == second['bundle'].exit_code == 0


def test_l0b_calibrate_step_unlocks_when_landed(chain):
    '''A3 weights_calibrate 的 skip 门（importorskip 在函数体内，落地即自动解锁）。

    L0b 标定是 Step5 只读的那份 FROZEN 权重的上游；M29 主流程九步不含它，故本包
    不把它接进 _run_chain，只守护入口在场与标定窗口口径。
    '''
    module = pytest.importorskip('dsm.weights_calibrate')
    assert callable(module.calibrate)
    assert {'grid', 'window', 'inputs', 'config'} <= set(
        inspect.signature(module.calibrate).parameters)
    # M34 L1462：标定窗口需 >= 4 期历史事实数据，冻结 fixtures 已备齐
    assert len(fg.HISTORY_PERIODS) >= 4
    periods = {row['period'] for row in _jsonl('metric_fact.jsonl')}
    assert set(fg.HISTORY_PERIODS) <= periods
    assert chain['weight_version'].status == 'FROZEN'


def test_l0b_whatif_step_unlocks_when_landed(chain):
    '''A4 whatif 的 skip 门（importorskip 在函数体内，落地即自动解锁）。

    preflight C-01 要的 whatif_run_id 只能由本模块产出（[L900] / [L1281]），
    因此 A4 落地是解开 RED 冲突 #2(a) 的必要条件之一。
    '''
    module = pytest.importorskip('dsm.whatif')
    assert callable(module.run) and callable(module.signoff_verdict)
    assert {'candidate', 'baseline', 'inputs', 'config', 'period'} <= set(
        inspect.signature(module.run).parameters)
    # 冻结 fixtures 的 FROZEN 权重 provenance 仍是 null -> C-01 仍 BLOCK，
    # 归属与实测见 test_step2_preflight_reaches_pass_or_warn_on_the_frozen_fixtures。
    assert chain['weight_version'].provenance is None
