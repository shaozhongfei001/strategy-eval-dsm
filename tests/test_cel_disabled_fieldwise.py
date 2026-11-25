'''CEL-EQ（ORCH-51）—— V-20 机制本体「输出逐字段一致」的专用端到端双基线 diff 用例。

本文件闭合 V20-G 只读取证包上报的缺口 GK-1（dsm_stage/V12-V20-G/REPORT.md §6）：
括注「G-01~G-15 全过」已由 V20-G 逐条实测闭合（15/15 全绿且有真实守护测试），但判据的
**前**半句「输出与关闭 CEL-0 预留字段的基线逐字段一致」在 tests/ 里从来没有专用用例。

判据原文（唯一事实来源，只读；契约 sha256[:12]=708679e9a83d / 2003 行）
----------------------------------------------------------------------
* 契约 §3.18 V 表 V-20 行 [L1513] 逐字：
  「cel.enabled = false 时，输出与关闭 CEL-0 预留字段的基线**逐字段一致**（G-01~G-15 全过）」
* 契约 §5.8.1 [L1894]（T4 预留行「首版取值规则」列）逐字：
  「全部可空；为空时 evidence.py 按现行规则判定，行为与无预留时完全一致」
* 契约 §5.8.1 [L1900]（守护用例 V-20）逐字：
  「cel.enabled = false 时，逐字段比对首版输出与关闭预留字段的基线，**必须完全一致**。
  这条用例是『范围不变、契约先行』的守护者。」
* 契约 §5.8.1 [L1898]（eval_config 行）：cel.enabled 单开关默认关闭，「关闭时 CEL 相关
  字段一律不参与任何判定；若非空则抛 CelDisabledDataPresentError（RK-15）」。
* 契约 §5.8.3 [L1918] + [L1923] 不变量②：「任何新增字段都不得改变现有 golden 用例的期望值」。

两个基线各自是什么（期望值只来自独立构造的基线 B 与契约原文，不是实现输出，R-14）
---------------------------------------------------------------------------------
* 基线 A（首版真实面）：T4 设计卡**声明**了 [L1894] 的七个 CEL-0 预留字段，
  cel.enabled = false，字段值一律为空 —— 这是首版契约要求的唯一合法状态。
* 基线 B（关闭预留字段的基线）：同一批策略 / 事实 / 治理值，但 CEL-0 预留字段
  **根本不存在**。两侧各跑一遍 M29 九步全链，再逐字段比对全部出口面。B 有两种实例化：
    - 记录面（model_absent_keys）：payload 里七个键整体缺席，由 models 层默认值补空。
      与基线 A 的**输入字节完全相同**，因此可零排除地比对包括输入指纹在内的一切出口面。
    - 线路面（csv_absent_columns）：T4 CSV 表头里预留列整体缺席，由 dsm/io_loaders
      真实读卡 —— [L1894] 意义上「无预留」的最字面实例。两侧 CSV 字节必然不同，
      故 T4 输入表的 SHA256 及其 canonical 序列化载体（audit.json 文本与落盘字节）
      属**输入出处面**，按声明排除；其余出口面逐字段零差异。

比对口径（项目校准规则，复用 dsm.numeric，不自写浮点比较）
----------------------------------------------------------
* 钱款与整数：numeric.eq_exact 精确相等。本仓库 MONEY_MINOR 在模型层就是 int
  （models.py L166 的 MoneyMinor 是 Annotated[int, BeforeValidator(numeric.as_minor)]，
  B-008 / H-4 [L1265]）；Decimal 形态的钱款列名一律以 _minor 结尾或属增量三列，同走 eq_exact。
* 比率 / 均值 / 权重 / 得分：numeric.eq_tol(TOL = Decimal('1E-12'))。
* 主用例另断言 tol_absorbed == 0：实测 3,278 个 Decimal 叶子（620 个走钱款口径
  eq_exact、2,658 个走比率口径 eq_tol）**逐位精确相等**，1e-12 容差一个差异也没有
  吸收 —— 防「靠容差蒙混过关」。

覆盖度自证（实测于开工 HEAD 22f8179；运行本文件即重算，见各例的阈值断言）
------------------------------------------------------------------------
22 个出口面 / 24,081 条比对路径 = 21,327 条值叶子 + 2,754 条容器类型标记叶子；
最深 6 层；未知类型叶子 0；float 叶子 0（H-4 [L1265] 全链无浮点）。
**未**纳入比对的出口面（如实登记，不写成「全字段覆盖」）：
  * CLI 产物面（dsm score 的九步 marshal 与 output_fingerprints 生产调用点）：
    dsm/cli.py 第 319 行 _chain_gate 在模块齐全时仍 raise InvariantError（第 333 行），
    端到端 CLI 不可达，归 M29-1 / M29-2，本包不改 dsm/**。替代口径：本文件把
    reports.render 的七件产物**真实落盘**（reports.write_report_set）并把落盘字节
    SHA256 纳入比对，覆盖 S6 写盘面。
  * 三角一致性面与熵诊断面：与本仓库既有守护测试 tests/test_integration_spine.py 同口径
    （frames.triangulation=None、entropy_diagnostics=()），九步主流程未接线，归 M29-1。

纪律：不新增也不修改 dsm/**；只用既有模块函数按 M29 L1330-1358 顺序串链；治理值全部有
出处（与 tests/test_integration_spine.py 第 77 行 GOVERNANCE 同值）；无 skip / xfail /
弱化断言（R-14）；三条负向对照 + 一条口径校准，反面就是 v1.1 的 K-28「断言 vacuous」先例。
'''
import csv
import dataclasses
import json
import pathlib
from collections.abc import Mapping as MappingType
from enum import Enum as EnumBase
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from dsm import (aggregate, attainment, audit, config as dsm_config, evidence,
                 fixtures_gen as fg, grading, io_loaders, normalize, numeric, pooling,
                 preflight, reason_codes, redline, reports, sensitivity)
from dsm.models import (AnchorSetDoc, AttainmentRow, DesignCardRow, GradeLedgerRow,
                        GradeRuleRow, MetricDictRow, PoolKey, ScoreCardDimCell,
                        ScoreCardMetricCell, ScoreCardRow, ScoringContext,
                        WeightVersionDoc)

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
INPUT_DIR = REPO_ROOT / 'fixtures' / 'input'

# 评价期口径与 tests/test_integration_spine.py 第 70-73 行逐字一致：取冻结 fixtures 里
# 事实表完整的一期 2026-Q2（主评价期 2026-Q3 有 4 个刻意缺失单元格，其一落在 HARD 红线
# 指标 S-008/v1/M_COMPLAINT_RATE 上，Step4 按 V-14 拒绝默认 -> 整步不可跑）。
PERIOD = '2026-Q2'
PREVIOUS_PERIOD = '2026-Q1'
RUN_AT = datetime(2026, 10, 20, 0, 0, tzinfo=timezone.utc)
RUN_ID = fg.RUN_ID
SEED = fg.SEED_DEFAULT

# [L1894] / [L1918] 逐字的七个 CEL-0 预留字段（T4 可空扩展）。interpretation_limit
# 首版**不是**预留字段而是 [L977] ⑤ 的判定材料（evidence.py 第 58-60 行同一口径），故
# 不在本表内 —— 该边界由 test_cel0_reserved_field_set_... 逐条钉住，不靠实现常量单定。
CEL0_RESERVED = ('incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
                 'estimator_method', 'experiment_id', 'holdout_id', 'mde_ok')
# [L1626] / [L1896]：score_card 侧五个 CEL-0 列（增量三列 + 方法 + value_captured 占位，
# ruling 22 的金额列带 _minor 后缀）。
CEL0_SCORE_CARD = ('incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
                   'estimator_method', 'value_captured_minor')

# 治理入参：与 tests/test_integration_spine.py 第 77-90 行 GOVERNANCE 同值，出处沿用其
# 行内注释（attainment_cap / on_zero / signed_off_statuses -> tests/test_attainment.py
# 第 30,60 行；missing_rate_warn / block -> tests/test_preflight.py 第 128-129 行；
# min_coverage_for_absolute_track(K-06) -> tests/test_grading.py 第 49,274 行；
# significance_keywords -> 冻结 fixtures 自身 success_criteria 词面；soft_deductions ->
# tests/test_redline.py 同量级比率）。cel 开关不在这里：它是本判据的被测对象，逐例传入。
GOVERNANCE = {
    'attainment_cap': Decimal('1.2'), 'on_zero': None,
    'signed_off_statuses': ('SIGNED',),
    'missing_rate_warn': Decimal('0.1'), 'missing_rate_block': Decimal('0.3'),
    'normalize_method': 'min_max', 'min_pool_size': 1,
    'normalize_on_zero': Decimal('0'),
    'sd_dof': 1, 'evidence_mode': 'GATE_ONLY',
    'significance_keywords': ('SYNTH_SUCC_CRITERIA',),
    'min_coverage_for_absolute_track': Decimal('0.6'),
    'upgrade_consecutive_periods': 2, 'demotion_immediate': True,
    'soft_deductions': {'M_OPTOUT_RATE': Decimal('0.05')},
}
# sensitivity 配置键：与 tests/test_integration_spine.py 第 92-98 行同值。
SENSITIVITY_CONFIG = {
    'stable_max': '0.05', 'review_max': '0.15', 'loo_sampling_threshold': 60,
    'mc_samples': 8, 'dirichlet_concentration': '20', 'loo_dominant_flip_rate': '0.2',
    'loo_sample_size_per_dim': 1, 'norm_swap_method': 'z_score',
    'norm_swap_min_rank_correlation': '0.9',
}

# 比对的出口面：九步全链每一个真实产物 + 七件报告产物文本 + 落盘字节指纹。
ALL_FACES = ('loaded', 'disk', 'preflight', 'inputs', 'attain', 'normalized',
             'evidence', 'redline', 'scores', 'grades', 'pool', 'pool_stats',
             'pool_reflow', 'pool_stats_reflow', 'sensitivity', 'context',
             'score_card', 'grade_ledger', 'bundle', 'frames', 'report_set',
             'reproducibility_hash')
# 输出面 = 除「输入读入面 loaded / inputs」与「入参载体 context」以外的全部产物面。
OUTPUT_FACES = tuple(name for name in ALL_FACES
                     if name not in ('loaded', 'inputs', 'context'))


# ---------------------------------------------------------------------------
# 输入面构造：同一批冻结 fixtures（M34 L1457-1462），三种 T4 预留字段声明方式。
# ---------------------------------------------------------------------------
def _jsonl(name):
    return [json.loads(line) for line in
            (INPUT_DIR / name).read_text(encoding='utf-8').splitlines() if line.strip()]


def _cell(value):
    '''冻结 JSONL 的单元格 -> CSV 文本。只换容器，不改值（R-2）。'''
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple)):
        return ','.join(str(item) for item in value)
    return str(value)


def _write_csv(path, rows, header=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = tuple(header) if header is not None else tuple(
        sorted({key for row in rows for key in row}))
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([_cell(row.get(column)) for column in columns])
    return columns


T4_COLUMNS = tuple(sorted({key for row in _jsonl('design_card.jsonl') for key in row}))


def _card_payload(surface):
    '''基线 A / B 的 T4 载荷，独立构造，不读实现产出的任何字段值。

    model_explicit_none / csv_blank_columns = 基线 A：七个预留字段**存在且为空**
    （[L1898] 要求的唯一合法 cel-off 状态）；
    model_absent_keys / csv_absent_columns = 基线 B：七个预留字段**不存在**；
    csv_frozen / model_frozen = 冻结 fixtures 原样（预留字段带值，只用于 RK-15 用例
    与「带值不泄漏」用例）。
    '''
    rows = _jsonl('design_card.jsonl')
    if surface in ('csv_frozen', 'model_frozen'):
        return [dict(row) for row in rows]
    if surface in ('model_explicit_none', 'csv_blank_columns'):
        return [dict(row, **{name: None for name in CEL0_RESERVED}) for row in rows]
    if surface in ('model_absent_keys', 'csv_absent_columns'):
        return [{key: value for key, value in row.items()
                 if key not in CEL0_RESERVED} for row in rows]
    raise AssertionError('unknown T4 surface: ' + str(surface))


def _t4_header(surface):
    '''线路面表头。基线 B 的表头把预留列整体摘掉，但 **mde_ok 一列必须留下**：
    dsm/io_loaders.py 第 142 行把 mde_ok 声明为 design_cards 的类型列（TABLE_SPECS），
    第 250-252 行对声明列缺失记 MISSING_COLUMN，而 MISSING_COLUMN 在 BLOCKING_KINDS
    （第 43-45 行）里 -> 摘掉 mde_ok 会让 io_loaders 直接拒表，读不出任何卡。该事实由
    test_cel_disabled_output_fieldwise_identical_on_the_wire_surface 就地实测钉住。'''
    if surface == 'csv_absent_columns':
        return tuple(column for column in T4_COLUMNS
                     if column not in CEL0_RESERVED or column == 'mde_ok')
    return T4_COLUMNS


def _stage(root, surface=None, perturb_money=False):
    '''把冻结 fixtures 摆成 io_loaders [L888] 的目录口径（T2/T5 在 config，
    T1/T3/T4 在 data/<period>）。线路面才写 design_cards.csv；记录面一律不写，
    两侧（A 与 B）共用**同一个** staged 目录 —— io_loaders 的 TABLE_ABSENT 披露文本
    带 data 目录的绝对路径（io_loaders.py 第 344-348 行），跨目录对拍会比到环境量而不是
    字段，那会让「逐字段一致」的口径失真。'''
    conf, data = root / 'config', root / 'data'
    _write_csv(conf / 'metric_dict.csv', _jsonl('metric_dict.jsonl'))
    _write_csv(conf / 'redlines.csv', _jsonl('redline.jsonl'))
    _write_csv(data / PERIOD / 'strategy_master.csv', _jsonl('strategy_master.jsonl'))
    facts = [dict(row) for row in _jsonl('metric_fact.jsonl')
             if row['period'] == PERIOD]
    if perturb_money:
        # 负向对照（端到端）：主导权重指标 M_REV_MINOR（fixtures_gen DOMINANT_METRIC，
        # CONTRIB 内二级权重 0.80）在 S-001/v1 上多 1 个**最小货币单位**（money 精确口径，
        # 不是比率扰动），它必须一路穿到 attain / normalize / scores / score_card /
        # reproducibility_hash。
        hits = 0
        for row in facts:
            if ((row['strategy_id'], row['version_id'], row['metric_id'])
                    == ('S-001', 'v1', fg.DOMINANT_METRIC)):
                row['value'] = int(row['value']) + 1
                row['value_num'] = int(row['value_num']) + 1
                hits += 1
        assert hits == 1, 'perturbation carrier is not unique: ' + str(hits)
    _write_csv(data / PERIOD / 'metric_facts.csv', facts)
    if surface is not None and surface.startswith('csv_'):
        _write_csv(data / PERIOD / 'design_cards.csv', _card_payload(surface),
                   _t4_header(surface))
    return conf, data


def _governance_docs():
    '''T6/T7/T8 是 YAML、归 dsm/config.py（[L877]），仓库 config/ 由 M29-3 在飞 -> 本包
    不读它，逐字用冻结 fixtures 的 JSONL 载荷按 R-2 构造契约模型（spine 同一口径）。'''
    return (WeightVersionDoc(**_jsonl('weight_version.jsonl')[0]),
            AnchorSetDoc(**_jsonl('anchor_set.jsonl')[0]),
            tuple(GradeRuleRow(**row) for row in _jsonl('grade_rule.jsonl')))


# ---------------------------------------------------------------------------
# 九步全链（M29 L1330-1358）。每一步的入参都来自上一步的真实返回值，没有手填中间值，
# 也没有 mock；口径与 tests/test_integration_spine.py 的 _run_chain 一致。
# ---------------------------------------------------------------------------
def _assemble_card_and_ledger(inputs, attain, ev, red, scores, grades, pool, sens,
                              weight_version, anchor_set):
    '''M26 L1610-1626 / L1630-1634：score_card 与 grade_ledger 的每一格都取自九步真实
    产物。五个 CEL-0 输出列在两侧都留空（首版无人填它，[L1626] / [L1896]），报告面
    必须明写占位语，不得静默留白 —— 该点由主用例显式计数断言。'''
    fact_of = {(f.strategy_id, f.version_id, f.metric_id): f
               for f in inputs.metric_facts}
    dict_of = {m.metric_id: m for m in inputs.metric_dict}
    attain_of = {(r.strategy_id, r.version_id, r.metric_id): r for r in attain.rows}
    ev_of = {(r.strategy_id, r.version_id): r for r in ev.rows}
    grade_of = {(r.strategy_id, r.version_id, r.period): r for r in grades.rows}
    pool_of = {(r.strategy_id, r.version_id, r.period): r for r in pool.rows}
    stable_of = {(r.strategy_id, r.version_id): r for r in sens.by_strategy}
    vetoed = sensitivity.is_vetoed(sens)
    size_of = {}
    for row in pool.rows:
        size_key = (row.pool_key.biz_domain, row.pool_key.evidence_class)
        size_of[size_key] = size_of.get(size_key, 0) + 1
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
                continue
            row = attain_of.get((score.strategy_id, score.version_id, metric_id))
            per_metric[metric_id] = ScoreCardMetricCell(
                actual_value=fact.value, target_value=dict_of[metric_id].target_value,
                attainment=(row.attainment if row else None))
        per_dim = {dim: ScoreCardDimCell(
            coverage=score.coverage, weight=weight_version.level1_weights[dim],
            attainment=score.dim_absolute[dim],
            relative_score=score.dim_relative.get(dim))
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
            evidence_class=ev_row.evidence_class,
            evidence_reason=ev_row.evidence_reason,
            evidence_source=ev_row.evidence_source,
            interpretation_limit=ev_row.interpretation_limit,
            redline_pass=not hard, redline_flags=tuple(r.reason_code for r in hard),
            grade=grade.grade, grade_reason_codes=tuple(grade.grade_reason_path),
            capped_flag=grade.capped, cap_reason=grade.cap_reason,
            ranking_pool=pool_row.pool_key, rank_in_pool=pool_row.pool_rank,
            pool_size=size_of[(pool_row.pool_key.biz_domain,
                               pool_row.pool_key.evidence_class)],
            eligible_for_L1_library=pool_row.primary_pool_eligible,
            l1_gate_reasons=() if pool_row.reject_reason is None
            else (pool_row.reject_reason,),
            stability_label=(stable.stability_label if stable else None),
            flip_under_pct10=(stable.flip_under_pct10 if stable else None),
            flip_under_pct20=(stable.flip_under_pct20 if stable else None),
            usable_for_elimination=usable))
        master = [m for m in inputs.strategy_master
                  if m.strategy_id == score.strategy_id][0]
        row = GradeLedgerRow(
            strategy_id=score.strategy_id, version_id=score.version_id,
            period=score.period, grade=grade.grade, previous_grade=None,
            recommended_action=(' | '.join(grade.action) if grade.action else None),
            owner_dept=master.owner_dept, owner_name=master.owner_name,
            ledger_complete=True, usable_for_elimination=usable)
        ledger.append(row.model_copy(
            update={'ledger_complete': not reports.ledger_missing_items(row)}))
    return tuple(cards), tuple(ledger)


def _eval_config_tree(cel_enabled):
    '''[L1898] 的 eval_config 形状：evidence 块 + cel.enabled 单开关，逐字按
    dsm/evidence.py 第 41-46 行的键名。'''
    return {
        'evidence': {'mode': GOVERNANCE['evidence_mode'],
                     'significance_keywords':
                         list(GOVERNANCE['significance_keywords'])},
        'cel': {'enabled': cel_enabled},
    }


def _app_config(cel_enabled):
    '''只填 evidence.py 真正会读的那一路（eval_config），其余五路留空树：本包不
    拟定治理值，也不假装 config.load_all 已跑通。'''
    return dsm_config.AppConfig(
        eval_config=_eval_config_tree(cel_enabled), weights={}, redlines={},
        grade_rules={}, anchor_set={}, ahp_matrices={})


def _run_chain(root, surface, cel_enabled, perturb_money=False,
               switch_from_config=False, progress=None, label='run'):
    '''跑一遍九步，返回 22 个出口面的字典。progress 记录已走完的步号，用于证明
    RK-15 抛错时**没有**产出半成品分数（V-14）。'''
    steps = [] if progress is None else progress
    weight_version, anchor_set, rule_rows = _governance_docs()
    conf, data = _stage(root, surface, perturb_money=perturb_money)
    loaded = io_loaders.load_inputs(data, PERIOD, conf,
                                    previous_period=PREVIOUS_PERIOD)
    if surface.startswith('csv_'):
        inputs = loaded.inputs
    else:
        inputs = dataclasses.replace(
            loaded.inputs,
            design_cards=tuple(DesignCardRow(**row)
                               for row in _card_payload(surface)))
    steps.append('io')

    preflight_config = preflight.PreflightConfig(
        period=PERIOD, period_ref_date=fg.DATA_AS_OF, weight_version=weight_version,
        anchor_set=anchor_set, signed_signoff_status=GOVERNANCE['signed_off_statuses'],
        missing_rate_warn=GOVERNANCE['missing_rate_warn'],
        missing_rate_block=GOVERNANCE['missing_rate_block'])
    preflight_result = preflight.run(inputs, preflight_config)
    steps.append('preflight')

    attain = attainment.compute(
        inputs.metric_facts, inputs.metric_dict,
        params=attainment.AttainmentParams(
            attainment_cap=GOVERNANCE['attainment_cap'],
            on_zero=GOVERNANCE['on_zero'],
            signed_off_statuses=GOVERNANCE['signed_off_statuses']),
        anchor_set=anchor_set)
    steps.append('step1_attainment')

    if switch_from_config:
        ev = evidence.classify(inputs.design_cards, inputs.metric_facts,
                               config=_app_config(cel_enabled))
    else:
        ev = evidence.classify(
            inputs.design_cards, inputs.metric_facts,
            params=evidence.EvidenceParams(
                evidence_mode=GOVERNANCE['evidence_mode'],
                cel_enabled=cel_enabled,
                significance_keywords=GOVERNANCE['significance_keywords']))
    steps.append('step3_evidence')

    domain_of = {row.strategy_id: row.biz_domain for row in inputs.strategy_master}
    class_of = {row.strategy_id: row.evidence_class for row in ev.rows}
    pools = {sid: PoolKey(biz_domain=domain_of[sid], evidence_class=class_of[sid])
             for sid in sorted(domain_of)}
    normalized = normalize.compute(
        attain, inputs.metric_dict, anchor_set,
        params=normalize.NormalizeParams(
            method=GOVERNANCE['normalize_method'],
            min_pool_size=GOVERNANCE['min_pool_size'],
            on_zero=GOVERNANCE['normalize_on_zero'],
            sd_dof=GOVERNANCE['sd_dof']),
        pools=pools)
    steps.append('step2_normalize')

    red = redline.evaluate(inputs.metric_facts, redline.RedlineSet(rows=inputs.redlines),
                           redline.WaiverSet(rows=()), as_of=fg.DATA_AS_OF,
                           soft_deductions=GOVERNANCE['soft_deductions'],
                           metric_dict=inputs.metric_dict)
    steps.append('step4_redline')
    scores = aggregate.compose(attain, normalized, weight_version, None)
    steps.append('step5_aggregate')

    grade_rules = grading.GradeRuleSet(
        rows=rule_rows,
        min_coverage_for_absolute_track=
            GOVERNANCE['min_coverage_for_absolute_track'],
        upgrade_consecutive_periods=GOVERNANCE['upgrade_consecutive_periods'],
        demotion_immediate=GOVERNANCE['demotion_immediate'])
    grades = grading.assign(scores, attain, ev, red, None, grade_rules)
    steps.append('step6_grading')

    pool, pool_stats = pooling.build(
        scores, grades, ev, inputs.strategy_master, None, sensitivity=None,
        params=pooling.PoolingParams(min_pool_size=GOVERNANCE['min_pool_size']))
    steps.append('step7_pooling')

    context = ScoringContext(
        period=PERIOD, run_at=RUN_AT, run_id=RUN_ID, seed=SEED,
        weight_version_id=weight_version.weight_version_id,
        evidence_mode=GOVERNANCE['evidence_mode'], cel_enabled=cel_enabled,
        input_fingerprints=loaded.fingerprints, attainment=attain,
        normalized=normalized, evidence=ev, redline=red, score=scores,
        grade=grades, pool=pool, pool_stats=pool_stats)

    def grade_fn(frame):
        '''Step8 注入的 Step6 钩子：真实 grading.assign，不是桩。'''
        rerun = grading.assign(frame, attain, ev, red, None, grade_rules)
        return {(r.strategy_id, r.version_id, r.period): r.grade
                for r in rerun.rows}

    def normalizer(values, method):
        '''Step8 注入的 Step2 钩子：换方法后由真实 normalize.compute 重算。'''
        dictionary = [MetricDictRow(
            metric_id='M_SWAP', metric_name='M_SWAP', dim_code='D_SWAP',
            numerator_def='n', time_window='MONTHLY', dedup_rule='NONE',
            missing_rule='SKIP', outlier_rule='NONE',
            attainment_formula='RATIO_DIRECT', direction=1, unit='RATIO',
            target_value=Decimal('1'), target_basis='budget', is_redline=False,
            owner_name='o', signoff_status='SIGNED', dim_signoff_status='SIGNED',
            dict_version=fg.DICT_VERSION, caliber_version=fg.CALIBER_VERSION)]
        rows = [AttainmentRow(strategy_id='X%03d' % i, version_id='v1',
                              period=PERIOD, metric_id='M_SWAP', attainment=value,
                              direction=1, has_target=True, capped_flag=False)
                for i, value in enumerate(values)]
        swap_key = PoolKey(biz_domain='D_SWAP', evidence_class='A')
        empty_anchor = AnchorSetDoc(anchor_set_id='AS-EMPTY', strategy_ids=(),
                                    effective_from=fg.DATA_AS_OF,
                                    effective_to=fg.DATA_AS_OF,
                                    rationale='no anchor for a method swap')
        frame = normalize.compute(
            rows, dictionary, empty_anchor,
            params=normalize.NormalizeParams(method=method, min_pool_size=1,
                                             on_zero=GOVERNANCE['normalize_on_zero'],
                                             sd_dof=GOVERNANCE['sd_dof']),
            pools={'X%03d' % i: swap_key for i in range(len(values))})
        got = {row.strategy_id: row.norm_value for row in frame.rows}
        return [got['X%03d' % i] for i in range(len(values))]

    sens = sensitivity.run(context, sensitivity.SCHEME_ORDER,
                           dict(SENSITIVITY_CONFIG), weights=weight_version,
                           grade_fn=grade_fn, normalizer=normalizer)
    steps.append('step8_sensitivity')

    pool2, pool_stats2 = pooling.build(
        scores, grades, ev, inputs.strategy_master, None, sensitivity=sens,
        params=pooling.PoolingParams(min_pool_size=GOVERNANCE['min_pool_size']))
    card_rows, ledger_rows = _assemble_card_and_ledger(
        inputs, attain, ev, red, scores, grades, pool2, sens, weight_version,
        anchor_set)
    steps.append('score_card_and_ledger')

    run_context = audit.RunContext(
        run_id=RUN_ID, run_at=RUN_AT, period=PERIOD, dsm_version='1.1.0',
        design_version='DSM-v1.1', cel_contract_version='CEL-0',
        weight_version_id=weight_version.weight_version_id, seed=SEED,
        sensitivity_schemes=sensitivity.SCHEME_ORDER,
        preflight_findings=tuple(f.to_audit_finding()
                                 for f in preflight_result.findings),
        downgrade_actions=tuple(preflight_result.downgrade_actions), exit_code=0,
        score_card=card_rows, grade_ledger=ledger_rows)
    bundle = audit.build_manifest(loaded.fingerprints, {'eval_config': {}},
                                  run_context, {})
    frames = reports.AllFrames(
        gate_status=reports.GateStatus(g5_dispute_source_review_signed=False,
                                       g7_governance_config_signed=False),
        attainment=attain, evidence=ev, redline=red, score=scores, pool=pool2,
        pool_stats=pool_stats2, sensitivity=sens, triangulation=None,
        entropy_diagnostics=(), score_card=card_rows, grade_ledger=ledger_rows,
        weight_provenance=None)
    report_set = reports.render(bundle, frames, None)
    steps.append('step9_audit_and_reports')
    return {
        'loaded': loaded, 'preflight': preflight_result, 'inputs': inputs,
        'attain': attain, 'normalized': normalized, 'evidence': ev, 'redline': red,
        'scores': scores, 'grades': grades, 'pool': pool, 'pool_stats': pool_stats,
        'pool_reflow': pool2, 'pool_stats_reflow': pool_stats2, 'sensitivity': sens,
        'context': context, 'score_card': card_rows, 'grade_ledger': ledger_rows,
        'bundle': bundle, 'frames': frames, 'report_set': report_set,
        'disk': reports.write_report_set(report_set, root / ('disk-' + label)),
        'reproducibility_hash': bundle.reproducibility_hash,
    }


def _faces(run):
    return {name: run[name] for name in ALL_FACES}


# ---------------------------------------------------------------------------
# 递归逐字段 diff 引擎：把两侧全部出口面展开成「字段路径 -> 值」，逐叶子按校准口径比对，
# 失败时打印**完整差异路径清单**（如 chain['score_card'][3].per_metric['M_ROI'].attainment），
# 而不是只说「不相等」。不做 repr 整体比对，也不抽样。
# ---------------------------------------------------------------------------
_SCALAR_KINDS = frozenset({'NoneType', 'bool', 'int', 'str', 'Decimal', 'float',
                           'date', 'datetime', 'bytes'})
# 单位多态列（FactValue = MoneyMinor | Ratio）在 Decimal 形态下仍可能是钱款口径
# （[L1150] / ruling 22），一律按 eq_exact 收紧；收紧方向永不放宽判据。
_MONEY_LIKE_DECIMAL = frozenset({
    'incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
    'actual_value', 'target_value', 'threshold_value', 'value_num', 'value_den',
    'value', 'numerator', 'denominator',
})


@dataclasses.dataclass
class DiffStats:
    '''比对规模自证：叶子字段数、最深层级、钱款/比率口径各走了哪条路。'''

    leaves: int = 0
    depth: int = 0
    decimal_exact: int = 0
    decimal_tol: int = 0
    tol_absorbed: int = 0
    unknown_types: tuple = ()
    floats: tuple = ()


def _leaf_name(path):
    '''取路径最后一段的字段名，覆盖 .name / ['key'] / [idx] 三种写法。'''
    if path.endswith(']'):
        body = path[:-1]
        open_at = body.rfind('[')
        if open_at < 0:
            return body
        return body[open_at + 1:].strip(chr(39))
    return path.rsplit('.', 1)[-1].split('[')[0]


def _kind_of(value):
    if isinstance(value, EnumBase):
        return 'str'
    if value is None:
        return 'NoneType'
    if isinstance(value, bool):
        return 'bool'
    if isinstance(value, int):
        return 'int'
    if isinstance(value, float):
        return 'float'
    if isinstance(value, Decimal):
        return 'Decimal'
    if isinstance(value, str):
        return 'str'
    if isinstance(value, datetime):
        return 'datetime'
    if isinstance(value, date):
        return 'date'
    if isinstance(value, bytes):
        return 'bytes'
    if isinstance(value, MappingType):
        return 'Mapping'
    if hasattr(type(value), 'model_fields'):
        return 'Model'
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return 'Dataclass'
    if isinstance(value, (set, frozenset)):
        return 'Set'
    if isinstance(value, (list, tuple)):
        return 'Sequence'
    return 'UNKNOWN'


def _short(value):
    text = repr(value)
    return text if len(text) <= 96 else text[:96] + '...'


def _flatten(value, path, out, stats, depth=0):
    '''递归展开：pydantic 模型按 model_fields 逐字段（与 audit.canonical_text 同一口径，
    不看 model_fields_set，也不接受未声明字段），dataclass 按 fields，Mapping 按排序键，
    序列按下标。任何无法识别的类型都记入 stats.unknown_types，由用例断言其为 0
    ——「全部字段」必须是数出来的，不是宣称的。'''
    kind = _kind_of(value)
    stats.depth = max(stats.depth, depth)
    if kind in _SCALAR_KINDS:
        out[path] = (kind, value)
        return
    if kind == 'str':
        out[path] = ('str', str(value.value))
        return
    if kind == 'UNKNOWN':
        stats.unknown_types = stats.unknown_types + (
            path + ':' + type(value).__name__,)
        out[path] = ('repr', repr(value))
        return
    if kind == 'Set':
        for index, item in enumerate(sorted(str(member) for member in value)):
            _flatten(item, path + '[' + str(index) + ']', out, stats, depth + 1)
        return
    if kind == 'Mapping':
        for key in sorted(value, key=str):
            _flatten(value[key], path + '[' + repr(key) + ']', out, stats, depth + 1)
        return
    if kind == 'Model':
        out[path + '.__type__'] = ('str', type(value).__name__)
        for name in type(value).model_fields:
            _flatten(getattr(value, name), path + '.' + name, out, stats, depth + 1)
        return
    if kind == 'Dataclass':
        out[path + '.__type__'] = ('str', type(value).__name__)
        for field in dataclasses.fields(value):
            _flatten(getattr(value, field.name), path + '.' + field.name,
                     out, stats, depth + 1)
        return
    for index, item in enumerate(value):
        _flatten(item, path + '[' + str(index) + ']', out, stats, depth + 1)


def _leaf_problem(path, a, b, stats):
    '''单叶子比对。返回 None = 一致；返回字符串 = 差异说明。'''
    if 'float' in (_kind_of(a), _kind_of(b)):
        stats.floats = stats.floats + (path,)
        return 'float leaf, H-4 [L1265] 禁止浮点进入链路'
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        exact = numeric.eq_exact(a, b)
        name = _leaf_name(path)
        if name.endswith('_minor') or name in _MONEY_LIKE_DECIMAL:
            stats.decimal_exact += 1
            if not exact:
                return '钱款列按 eq_exact 精确比对，A=' + _short(a) + ' B=' + _short(b)
            return None
        stats.decimal_tol += 1
        if not numeric.eq_tol(a, b, numeric.TOL):
            return ('比率/均值超出 1e-12 容差，A=' + _short(a) + ' B=' + _short(b))
        if not exact:
            stats.tol_absorbed += 1
        return None
    if a is None or b is None:
        return None if (a is None and b is None) else (
            '一侧为空一侧非空，A=' + _short(a) + ' B=' + _short(b))
    if isinstance(a, bool) or isinstance(b, bool):
        return None if a is b else 'bool 不同，A=' + _short(a) + ' B=' + _short(b)
    if isinstance(a, int) or isinstance(b, int):
        if type(a) is not type(b):
            return '整数一侧类型不同，A=' + _short(a) + ' B=' + _short(b)
        return None if a == b else '整数/计数不同，A=' + _short(a) + ' B=' + _short(b)
    if isinstance(a, str) or isinstance(b, str):
        if not (isinstance(a, str) and isinstance(b, str)):
            return '文本一侧类型不同，A=' + _short(a) + ' B=' + _short(b)
        if a == b:
            return None
        if len(a) > 160 or len(b) > 160:
            lines_a, lines_b = a.split('\n'), b.split('\n')
            first = next((i for i, (x, y) in enumerate(zip(lines_a, lines_b))
                          if x != y), min(len(lines_a), len(lines_b)))
            return ('长文本首个不同在第 %d 行（A %d 行 / B %d 行）'
                    % (first + 1, len(lines_a), len(lines_b)))
        return '文本不同，A=' + _short(a) + ' B=' + _short(b)
    if isinstance(a, (date, datetime)) or isinstance(b, (date, datetime)):
        return None if (type(a) is type(b) and a == b) else (
            '日期/时间戳不同，A=' + _short(a) + ' B=' + _short(b))
    if isinstance(a, bytes) or isinstance(b, bytes):
        return None if a == b else '字节不同'
    return None if a == b else '值不同，A=' + _short(a) + ' B=' + _short(b)


@dataclasses.dataclass
class PairDiff:
    '''一次双基线逐字段比对的结果：差异路径清单 + 覆盖度自证。'''

    problems: tuple
    stats: DiffStats
    leaves: int

    @property
    def paths(self):
        return tuple(problem.split(' :')[0] for problem in self.problems)

    def face_of(self, path):
        '''chain['attain'].rows[12].attainment 与 chain['disk']['audit.json'] 的面名都是 attain / disk。'''
        head = path.split('.', 1)[0]
        if not head.startswith("chain['"):
            return path
        return head[len("chain['"):].split("'", 1)[0]

    def faces_hit(self):
        return sorted({self.face_of(path) for path in self.paths})

    def report(self, limit=25):
        head = ['逐字段差异 %d 条（已展开叶子 %d 条，最深 %d 层）：'
                % (len(self.problems), self.leaves, self.stats.depth)]
        head += ['  ' + problem for problem in self.problems[:limit]]
        if len(self.problems) > limit:
            head.append('  ...另 %d 条' % (len(self.problems) - limit))
        return '\n'.join(head)


def _diff_maps(map_a, map_b, stats):
    problems = []
    for path, (kind, value) in map_a.items():
        if path not in map_b:
            problems.append(path + ' : 只在基线 A 出现（' + kind + '='
                            + _short(value) + '）')
    for path, (kind, value) in map_b.items():
        if path not in map_a:
            problems.append(path + ' : 只在基线 B 出现（' + kind + '='
                            + _short(value) + '）')
    for path, (kind, value) in map_a.items():
        if path not in map_b:
            continue
        other_kind, other = map_b[path]
        if kind != other_kind and not {kind, other_kind} <= {'int', 'Decimal'}:
            problems.append(path + ' : 容器/类型不同 A=' + _short(value) + ' B='
                            + _short(other) + '（' + kind + ' vs ' + other_kind + '）')
            continue
        note = _leaf_problem(path, value, other, stats)
        if note:
            problems.append(path + ' : ' + note)
    return tuple(problems)


def flatten_faces(run, root='chain'):
    out, stats = {}, DiffStats()
    _flatten(_faces(run), root, out, stats)
    return out, stats


def diff_runs(run_a, run_b, faces=None):
    '''两侧各展开全部（或指定）出口面后逐字段比对。'''
    map_a, map_b = {}, {}
    stats = DiffStats()
    for side, target in ((run_a, map_a), (run_b, map_b)):
        values = _faces(side) if faces is None else {k: side[k] for k in faces}
        _flatten(values, 'chain', target, stats)
    stats.leaves = len(map_a)
    problems = _diff_maps(map_a, map_b, stats)
    return PairDiff(problems=problems, stats=stats, leaves=len(map_a))


def _is_input_provenance_path(path):
    '''线路面比对里唯一合法的差异位置：T4 输入表的 SHA256 叶子本身，以及按
    [L1053] canonical 序列化把该 SHA 原样带出去的 audit.json 载体（文本面与落盘字节面）。
    出处面不是输出面：基线 B 的 CSV 少了预留列，字节必然不同，SHA 必然不同。'''
    if "fingerprints['design_cards.csv'].sha256" in path:
        return True
    return path.endswith("['report_set'].audit_json") or (
        path.endswith("['disk']['audit.json']"))


def _find_leaf(flat_map, suffix):
    hits = sorted(path for path in flat_map if path.endswith(suffix))
    assert hits, '被比对面上找不到叶子 ' + suffix + '，比对面缩水了'
    return hits[0]


def _in_period_subjects():
    '''从冻结 fixtures 的**事实表**独立推导本期评价范围（[L1063] ② / evidence.py
    evaluation_scope 的口径），作为 score_card 行数的期望值 —— 不是抄实现输出。'''
    return {(row['strategy_id'], row['version_id'])
            for row in _jsonl('metric_fact.jsonl') if row['period'] == PERIOD}


# ---------------------------------------------------------------------------
# 双基线夹具：同一 root 内的四个 run 共用 staged 目录（loaded 的 TABLE_ABSENT 披露文本
# 带 data 目录绝对路径，跨目录对拍会比到环境量而不是字段）。
# ---------------------------------------------------------------------------
@pytest.fixture(scope='module')
def record_surface(tmp_path_factory):
    '''记录面（输入字节两侧完全相同）：基线 A / 基线 B / 带值+开关开 / 钱款扰动。'''
    root = tmp_path_factory.mktemp('cel-eq-record')
    baseline_a = _run_chain(root, 'model_explicit_none', False, label='A')
    baseline_b = _run_chain(root, 'model_absent_keys', False, label='B')
    populated = _run_chain(root, 'model_frozen', True, label='POP')
    perturbed = _run_chain(root, 'model_explicit_none', False,
                           perturb_money=True, label='PERT')
    return {'root': root, 'a': baseline_a, 'b': baseline_b,
            'populated': populated, 'perturbed': perturbed,
            'diff': diff_runs(baseline_a, baseline_b)}


@pytest.fixture(scope='module')
def wire_surface(tmp_path_factory):
    '''线路面（两侧 CSV 字节不同）：基线 A 预留列存在但全空 / 基线 B 预留列整体缺席。'''
    root = tmp_path_factory.mktemp('cel-eq-wire')
    baseline_a = _run_chain(root, 'csv_blank_columns', False, label='WIRE-A')
    baseline_b = _run_chain(root, 'csv_absent_columns', False, label='WIRE-B')
    return {'root': root, 'a': baseline_a, 'b': baseline_b,
            'diff': diff_runs(baseline_a, baseline_b)}


# ---------------------------------------------------------------------------
# 用例 0：比对范围（预留字段集合）先由契约原文钉住，不让实现常量单方定义口径。
# ---------------------------------------------------------------------------
def test_cel0_reserved_field_set_is_the_seven_of_L1894_and_L1918():
    '''[L1894] / [L1918] 的 T4 预留恰为七个，且全部可空、默认 None；score_card 侧
    CEL-0 恰为五列（[L1626] / [L1896]，ruling 22 的金额列带 _minor 后缀）。
    interpretation_limit **不是**预留字段而是 [L977] ⑤ 的判定材料。'''
    assert len(CEL0_RESERVED) == 7
    assert len(set(CEL0_RESERVED)) == 7
    assert set(CEL0_RESERVED) == set(evidence.CEL_RESERVED_FIELDS)
    card_fields = DesignCardRow.model_fields
    for name in CEL0_RESERVED:
        assert name in card_fields, name + ' 不在 T4 契约模型上'
        assert not card_fields[name].is_required(), name + ' 必须可空（[L1894]）'
        assert card_fields[name].default is None, name + ' 默认必须是 None 而不是 0'
    assert 'interpretation_limit' not in CEL0_RESERVED
    assert not card_fields['interpretation_limit'].is_required()
    score_fields = ScoreCardRow.model_fields
    assert set(CEL0_SCORE_CARD) == set(reports.CEL0_COLUMNS)
    for name in CEL0_SCORE_CARD:
        assert name in score_fields, name + ' 不在 score_card 契约模型上'
        assert score_fields[name].default is None, name + ' 首版留空（[L1626]）'
    assert 'value_captured_minor'.endswith('_minor'), 'ruling 22 的金额列名口径'


# ---------------------------------------------------------------------------
# 用例 1（判据主体）：cel 关闭时，首版输出与「无 CEL-0 预留字段」基线逐字段一致。
# ---------------------------------------------------------------------------
def test_disabled_cel_output_is_fieldwise_identical_to_baseline_without_reserved_fields(
        record_surface):
    '''契约 [L1513] / [L1900] 的前半句：递归展开全部出口面逐字段比对，差异集合必须为空。

    基线 A = T4 声明七个预留字段、值全空（[L1898] 唯一合法 cel-off 状态）；
    基线 B = 同一批 payload 里七个键整体缺席（"无预留"），两侧输入字节相同、同跑九步。
    '''
    pair_a, pair_b, diff = (record_surface['a'], record_surface['b'],
                            record_surface['diff'])
    # 开关两侧都是关闭态（否则比的不是本判据）
    assert pair_a['context'].cel_enabled is False
    assert pair_b['context'].cel_enabled is False
    assert len(pair_a['evidence'].rows) == len(pair_b['evidence'].rows) > 0
    # A 侧预留字段确实「声明且为空」，B 侧确实「不存在」（由 models 默认值补空）
    card_rows_expected = len(_jsonl('design_card.jsonl'))
    for run in (pair_a, pair_b):
        cards = run['inputs'].design_cards
        assert len(cards) == card_rows_expected
        for card in cards:
            for name in CEL0_RESERVED:
                assert getattr(card, name) is None, name
    assert diff.problems == (), diff.report()
    # ---- 覆盖度自证：比对必须真的展开这么多字段，而不是比了一个空集合 ----
    assert len(ALL_FACES) == 22 and len(OUTPUT_FACES) == 19
    assert diff.leaves >= 20000, '比对面缩水：只展开了 ' + str(diff.leaves) + ' 个叶子'
    assert diff.stats.depth >= 5, '比对没穿透到深层字段：' + str(diff.stats.depth)
    assert diff.stats.unknown_types == (), '存在未识别类型，逐字段覆盖不成立'
    assert diff.stats.floats == (), '链路里出现浮点，H-4 [L1265] 被破坏'
    assert diff.stats.decimal_exact > 0 and diff.stats.decimal_tol > 0
    # 1e-12 容差没有吸收任何差异：全部 Decimal 叶子逐位精确相等
    assert diff.stats.tol_absorbed == 0, (
        '有 ' + str(diff.stats.tol_absorbed) + ' 个 Decimal 叶子只靠容差才相等，'
        '逐字段一致必须逐位一致')
    # ---- 反空真：被比对的面上确实带着 CEL-0 输出列，且按 [L1896] 明写占位语 ----
    rows = len(pair_a['score_card'])
    assert rows == len(pair_b['score_card']) == len(_in_period_subjects()), (
        'score_card 行数与「本期有事实行的 (策略, 版本)」不一致：'
        + str(rows) + ' vs ' + str(len(_in_period_subjects())))
    assert rows >= 10
    for row in pair_a['score_card']:
        for name in CEL0_SCORE_CARD:
            assert getattr(row, name) is None, name + ' 首版必须留空（[L1626]）'
    placeholder_a = pair_a['report_set'].score_card_csv.count(reports.CEL0)
    placeholder_b = pair_b['report_set'].score_card_csv.count(reports.CEL0)
    assert placeholder_a == placeholder_b == len(CEL0_SCORE_CARD) * rows, (
        'CEL-0 列未逐格明写「' + reports.CEL0 + '」：静默留白违 [L1896]')
    # 七件产物落盘面的逐字节对拍也包含在上面（disk / report_set 两个面）
    assert set(pair_a['disk']) == set(pair_b['disk']) == {
        'report.md', 'score_card.csv', 'grade_ledger.csv', 'sensitivity_report.csv',
        'entropy_diagnostic.csv', 'triangulation.md', 'audit.json'}


# ---------------------------------------------------------------------------
# 用例 2：线路面（CSV 表头里预留列整体缺席）的同一条判据。
# ---------------------------------------------------------------------------
def test_disabled_cel_output_is_fieldwise_identical_on_the_wire_surface_modulo_sha(
        wire_surface):
    '''基线 B 的最字面实例：T4 CSV 没有预留列，由 dsm/io_loaders 真实读卡。
    两侧 CSV 字节必然不同 -> 输入出处面按声明排除，其余输出面逐字段零差异。'''
    pair_a, pair_b, diff = (wire_surface['a'], wire_surface['b'],
                           wire_surface['diff'])
    assert pair_a['context'].cel_enabled is False
    assert pair_b['context'].cel_enabled is False
    # 两侧都真的走完了 io_loaders（13 张卡全在，预留字段全空）
    card_rows_expected = len(_jsonl('design_card.jsonl'))
    assert len(pair_a['inputs'].design_cards) == card_rows_expected
    assert len(pair_b['inputs'].design_cards) == card_rows_expected
    for run in (pair_a, pair_b):
        for card in run['inputs'].design_cards:
            for name in CEL0_RESERVED:
                assert getattr(card, name) is None, name
    # 表头实测：A 侧带七列，B 侧只剩 mde_ok（其余六列摘除）
    header_a, header_b = _wire_headers(wire_surface['root'])
    assert set(CEL0_RESERVED) <= set(header_a)
    assert set(CEL0_RESERVED) - set(header_b) == set(CEL0_RESERVED) - {'mde_ok'}
    assert 'mde_ok' in header_b
    assert len(header_a) == len(T4_COLUMNS)
    assert len(header_b) == len(T4_COLUMNS) - (len(CEL0_RESERVED) - 1), (
        '线路面 B 只允许摘掉除 mde_ok 以外的六个预留列：' + str(header_b))
    # ---- 输出面逐字段零差异：全部差异都必须被声明的输入出处面吸收 ----
    assert diff.leaves >= 20000, '线路面比对缩水：' + str(diff.leaves)
    assert diff.stats.unknown_types == () and diff.stats.floats == ()
    assert diff.stats.tol_absorbed == 0, '容差吸收了差异，逐字段一致不成立'
    # ---- 报告七件产物：除 audit.json 载体外逐字节相同（含落盘指纹） ----
    for name in ('report_md', 'score_card_csv', 'grade_ledger_csv',
                 'sensitivity_report_csv', 'entropy_diagnostic_csv',
                 'triangulation_md'):
        assert getattr(pair_a['report_set'], name) == getattr(
            pair_b['report_set'], name), name + ' 文本不同'
    for artifact in ('report.md', 'score_card.csv', 'grade_ledger.csv',
                     'sensitivity_report.csv', 'entropy_diagnostic.csv',
                     'triangulation.md'):
        assert pair_a['disk'][artifact] == pair_b['disk'][artifact], artifact
    assert (pair_a['reproducibility_hash'] == pair_b['reproducibility_hash']), (
        '[L1052] 复现哈希必须逐字相等，它与输入指纹无关')
    # ---- 全量面：差异只允许出现在声明的输入出处面，而且必须真的出现（防排除口径空真） ----
    provenance_hits = tuple(path for path in diff.paths
                            if _is_input_provenance_path(path))
    unexpected = tuple(path for path in diff.paths
                       if not _is_input_provenance_path(path))
    assert unexpected == (), '输出面之外还多出未声明的差异：' + diff.report(40)
    assert provenance_hits, '线路面两侧输入 SHA 竟相同 -> 本用例的排除口径为空真'
    for path in ("chain['loaded'].fingerprints['design_cards.csv'].sha256",
                 "chain['context'].input_fingerprints['design_cards.csv'].sha256",
                 "chain['bundle'].input_fingerprints['design_cards.csv'].sha256"):
        assert path in provenance_hits, '缺少预期的出处差异 ' + path
    assert sorted({diff.face_of(path) for path in provenance_hits}) == [
        'bundle', 'context', 'disk', 'loaded', 'report_set']
    # 列增减不改行数：两侧 design_cards.csv 的 row_count 必须相同（[L888] 指纹含行数）
    for table, fp_a in pair_a['loaded'].fingerprints.items():
        assert fp_a.row_count == pair_b['loaded'].fingerprints[table].row_count, table
    assert (pair_a['loaded'].fingerprints['design_cards.csv'].row_count
            == card_rows_expected)


def _wire_headers(root):
    '''两侧 T4 CSV 的表头实测：A 带七个预留列，B 摘掉六个（mde_ok 必须留）。
    探针文件写在 root/probe 下，只为取表头，不参与任何字段比对。'''
    headers = {}
    for label, surface in (('A', 'csv_blank_columns'),
                           ('B', 'csv_absent_columns')):
        headers[label] = _write_csv(root / 'probe' / label / 'design_cards.csv',
                                    _card_payload(surface), _t4_header(surface))
    return headers['A'], headers['B']


# ---------------------------------------------------------------------------
# 用例 3：cel 关闭 + 预留字段非空 -> 必抛（RK-15 / [L1898]），且整链中止不出半成品。
# ---------------------------------------------------------------------------
def test_cel_disabled_with_reserved_data_present_refuses_the_whole_chain(tmp_path):
    '''冻结 fixtures 的 T4 预留列本来就带值（[L1894] 的可空扩展），把这条真实数据喂进
    cel.enabled = false 的链路：Step3 必须抛 CelDisabledDataPresentError，且不得产出
    任何半成品分数（V-14）。开关从 eval_config 树经 params_from_config 读入，与
    [L1898] 的字面口径同一路径。'''
    carriers = {(row['strategy_id'], row['version_id'])
                for row in _jsonl('design_card.jsonl')
                if any(row.get(name) is not None for name in CEL0_RESERVED)}
    assert carriers, '冻结 fixtures 没有带值的预留字段，本用例无从判定'
    progress = []
    with pytest.raises(evidence.CelDisabledDataPresentError) as raised:
        _run_chain(tmp_path, 'csv_frozen', False, switch_from_config=True,
                   progress=progress)
    # 抛在 Step3：Step1 已跑，Step3 之后的每一步都没有跑
    assert 'step1_attainment' in progress
    assert 'step3_evidence' not in progress
    assert not [step for step in progress
                if step.startswith(('step4', 'step5', 'step6', 'step7', 'step8',
                                    'step9', 'score_card'))], progress
    message = str(raised.value)
    assert 'cel.enabled' in message and 'RK-15' in message, message
    assert any(strategy + '/' + version in message
               for strategy, version in carriers), message
    assert any(name in message for name in CEL0_RESERVED), message
    # 码在册且为 BLOCK：这不是静默降级
    assert reason_codes.severity(reason_codes.RC.CEL_DISABLED_DATA_PRESENT) == 'BLOCK'
    # 开关本身不可缺省：eval_config 没有 cel 块 -> 配置层拒绝，不自造默认值（H-5）
    tree = _eval_config_tree(False)
    tree.pop('cel')
    bare = dsm_config.AppConfig(eval_config=tree, weights={}, redlines={},
                                grade_rules={}, anchor_set={}, ahp_matrices={})
    with pytest.raises(evidence.EvidenceConfigError):
        evidence.params_from_config(bare)
    assert evidence.params_from_config(_app_config(False)).cel_enabled is False


# ---------------------------------------------------------------------------
# 用例 4（负向对照之一，防 vacuous）：diff 引擎必须抓得住每一种人为注入的差异，
# 同时按校准规则放过 1e-13 的比率差（放过的口径本身就是项目规则）。
# ---------------------------------------------------------------------------
def test_negative_control_injected_differences_are_all_caught_by_the_fieldwise_diff(
        record_surface):
    flat_a, stats_a = flatten_faces(record_surface['a'])
    flat_b, stats_b = flatten_faces(record_surface['b'])
    assert len(flat_a) == len(flat_b) == record_surface['diff'].leaves
    assert stats_a.depth == stats_b.depth >= 5
    assert record_surface['diff'].problems == (), '前提塌了：两基线本应零差异'

    def mutate(path, value, kind):
        injected = dict(flat_b)
        assert path in injected, path
        injected[path] = (kind, value)
        return _diff_maps(flat_a, injected, DiffStats())

    # (1) 整数 / 计数叶子 +1（钱款与整数走 eq_exact，无容差）
    rank_path = _find_leaf(flat_a, '.pool_size')
    caught = mutate(rank_path, flat_a[rank_path][1] + 1, 'int')
    assert any(problem.startswith(rank_path + ' :') for problem in caught), caught
    # (2) 比率叶子 +1e-9 必须抓到
    ratio_path = _find_leaf(flat_a, '.composite_absolute')
    assert flat_a[ratio_path][0] == 'Decimal'
    caught = mutate(ratio_path, flat_a[ratio_path][1] + Decimal('1E-9'), 'Decimal')
    assert any(problem.startswith(ratio_path + ' :') for problem in caught), caught
    # (3) 文本叶子改写必须抓到
    grade_path = _find_leaf(flat_a, '.evidence_source')
    caught = mutate(grade_path, 'CEL_ESTIMATED', 'str')
    assert any(problem.startswith(grade_path + ' :') for problem in caught), caught
    # (4) 少一个字段 / 多一个字段都必须抓到（叶子集合本身也在比对范围内）
    dropped = dict(flat_b)
    dropped.pop(_find_leaf(flat_a, '.reproducibility_hash'))
    caught = tuple(_diff_maps(flat_a, dropped, DiffStats()))
    assert any('只在基线 A 出现' in problem for problem in caught), caught
    added = dict(flat_b)
    added["chain['injected.leaf_that_baseline_a_does_not_have']"] = ('int', 1)
    caught = tuple(_diff_maps(flat_a, added, DiffStats()))
    assert any('只在基线 B 出现' in problem for problem in caught), caught
    # (5) 容器类型变化（模型名改写）必须抓到
    renamed = dict(flat_b)
    renamed[_find_leaf(flat_a, ".__type__")] = ('str', 'NotScoreCardRow')
    caught = tuple(_diff_maps(flat_a, renamed, DiffStats()))
    assert any('__type__' in problem for problem in caught), caught
    # (6) 数值口径本身的校准边界：钱款/整数精确，比率 1e-12
    money = _leaf_problem('x.chain.value_captured_minor', Decimal('120000'),
                          Decimal('120000.0000000000001'), DiffStats())
    assert money, '钱款列被放过了 -> 校准规则未实现'
    assert _leaf_problem('x.chain.incremental_value', 120000, 120001,
                         DiffStats()), '金额整数被放过了'
    assert _leaf_problem('x.chain.composite_absolute', Decimal('0.5'),
                         Decimal('0.5') + Decimal('1E-13'), DiffStats()) is None, (
        '1e-13 的比率差按项目校准规则应当放过（TOL=1E-12）')
    assert _leaf_problem('x.chain.composite_absolute', Decimal('0.5'),
                         Decimal('0.5') + Decimal('1E-11'), DiffStats()) is not None
    # (7) 反空真总检查：以上注入都只动了副本，两基线的真实差异集合仍然为空
    assert record_surface['diff'].problems == ()


# ---------------------------------------------------------------------------
# 用例 5（负向对照之二）：真实链路扰动。1 个最小货币单位必须一路穿到每个产物面，
# 证明逐字段比对不是"比了两个空对象"。
# ---------------------------------------------------------------------------
def test_negative_control_one_minor_unit_propagates_through_every_output_face(
        record_surface):
    diff = diff_runs(record_surface['a'], record_surface['perturbed'])
    assert diff.problems, '扰动 1 个最小货币单位后逐字段差异仍为空 -> 比对是空真的'
    baseline_a = record_surface['a']
    target = next(index for index, row in enumerate(baseline_a['inputs'].metric_facts)
                  if (row.strategy_id, row.version_id, row.metric_id)
                  == ('S-001', 'v1', fg.DOMINANT_METRIC))
    money_path = "chain['inputs'].metric_facts[%d].value" % target
    assert money_path in diff.paths, diff.report(60)
    assert len(flatten_faces(baseline_a)[0]) == diff.leaves
    hits = diff.faces_hit()
    expected_hits = ('attain', 'bundle', 'context', 'disk', 'frames', 'inputs',
                     'loaded', 'normalized', 'report_set', 'reproducibility_hash',
                     'score_card', 'scores')
    for face in expected_hits:
        assert face in hits, '扰动没有穿到输出面 ' + str(face) + '，实为 ' + str(hits)
    assert len(hits) >= len(expected_hits)
    # 差异里必须点名 money 与比率两条口径，以及 [L1052] 的复现哈希
    paths = '\n'.join(diff.problems)
    assert 'chain[\'reproducibility_hash\']' in paths
    assert ".per_metric['" in paths or '.attainment' in paths
    assert any('.composite_absolute' in problem
               for problem in diff.problems), paths[:400]


# ---------------------------------------------------------------------------
# 用例 6（负向对照之三）：开关打开 + 预留字段带值时，差异必须**只**停在输入面 ——
# 既证明 diff 看得见真差异，也证明预留数据不参与任何输出判定（[L1895] 恒 CARD_ONLY）。
# ---------------------------------------------------------------------------
def test_negative_control_populated_reserved_data_stops_at_the_input_face(
        record_surface):
    populated = record_surface['populated']
    assert populated['context'].cel_enabled is True
    diff = diff_runs(record_surface['a'], populated)
    assert diff.problems, '带值 vs 空值没有任何差异 -> 本用例空真'
    allowed = ("chain['inputs'].design_cards", "chain['context'].cel_enabled")
    offenders = tuple(path for path in diff.paths if not path.startswith(allowed))
    assert offenders == (), (
        '预留字段带值泄漏到了输出面：\n' + '\n'.join(offenders[:20]))
    reserved_paths = tuple(path for path in diff.paths
                           if path.startswith("chain['inputs'].design_cards"))
    assert reserved_paths
    for path in reserved_paths:
        name = _leaf_name(path)
        assert name in CEL0_RESERVED, path
    # 开关本身也是差异之一（否则两侧根本不是不同状态）
    assert "chain['context'].cel_enabled" in diff.paths
    # 输出面的逐字段一致在这里再次成立（与用例 1 同口径，但这一侧带着 CEL-0 真值）
    output_diff = diff_runs(record_surface['a'], populated, faces=OUTPUT_FACES)
    assert output_diff.problems == (), output_diff.report()
