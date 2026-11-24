'''A1 / dsm.fixtures_gen -- 合成 fixtures 生成（digest M34 = SDD 1455-1463）。

产出 8 张输入表 + 6 个 golden 变体 + 1 个负向原始载荷 + manifest，全部**合成**：
id / 人名 / 机构 / 表名一律 SYNTH 前缀；数值要么是本文件写死的构造值（手算算式
见 tools/gen_golden.py 的 hand 段），要么来自 random.Random(seed)。零真实数据。
字段名逐字抄 dsm/models.py（R-2）。本模块不实现 attainment/aggregate/grading：
构造意图经 _designed_actual() 反推成事实值，不读任何实现输出（R-14）。
无副作用、不读时钟：snapshot_time / data_as_of / approved_date 全部写死。
'''
from __future__ import annotations

import hashlib
import json
import os
import random
from datetime import date, datetime
from decimal import Decimal

from dsm import models, reason_codes

_D = Decimal
GENERATOR_VERSION = 'fixtures_gen-1.0'
SCHEMA = 'dsm-fixtures-1'
SEED_DEFAULT = 20260101
RUN_ID = 'SYNTH-RUN-0001'
# M34 第 1462 行：标定窗口 >= 4 期历史事实数据；这里 4 期历史 + 1 期评价期。
EVAL_PERIOD = '2026-Q3'
HISTORY_PERIODS = ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')
ALL_PERIODS = HISTORY_PERIODS + (EVAL_PERIOD,)
SNAPSHOT_TIME = datetime(2026, 10, 20, 0, 0)
DATA_AS_OF = date(2026, 9, 30)
# M34 第 1457 行：4 域 x 3 类 segment = 12 策略，每格一条。
BIZ_DOMAINS = ('CARD', 'LOAN', 'WEALTH', 'PAY')
SEGMENT_TYPES = ('RETAIL_NEW', 'RETAIL_EXIST', 'SME')
# dim_code 是 config 驱动注册表（models.py L1131），仓库 config/ 为空 -> 6 个维度码
# 为本包构造值（缺口已上报）。CONTRIB 由 digest M31 G-03/G-06 逐字给出，其余按
# M37 E3/E4 的业务用语（效益度/体验/成本/可持续/过程）命名。
DIMS = ('CONTRIB', 'EFFIC', 'EXPER', 'COST', 'SUST', 'PROC')
# 一级权重取 0.07 的整数倍：G-06 的 OAT+20%（CONTRIB x1.2 后其余重归一）在 12 位
# 小数下精确闭合，于是 composite 手算值不需要容差。
LEVEL1_WEIGHTS = {'CONTRIB': _D('0.30'), 'EFFIC': _D('0.21'), 'EXPER': _D('0.21'),
                  'COST': _D('0.14'), 'SUST': _D('0.07'), 'PROC': _D('0.07')}
LEVEL1_WEIGHTS_OAT20 = {'CONTRIB': _D('0.36'), 'EFFIC': _D('0.192'),
                        'EXPER': _D('0.192'), 'COST': _D('0.128'),
                        'SUST': _D('0.064'), 'PROC': _D('0.064')}
_Q = _D('0.000001')
# M34 第 1458 行：每维度 2-3 个占位指标（共 15 个），单位覆盖四种。
# 列: metric_id, dim, unit, direction, formula, target, missing_rule, is_redline, w2, signoff
METRICS = (
    ('M_REV_MINOR', 'CONTRIB', 'MONEY_MINOR', 1, 'RATIO_DIRECT', 10000, 'ZERO', False, '0.80', 'SIGNED'),
    ('M_CUST_GAIN', 'CONTRIB', 'COUNT', 1, 'RATIO_DIRECT', 100, 'SKIP', False, '0.10', 'SIGNED'),
    ('M_AUM_MINOR', 'CONTRIB', 'MONEY_MINOR', 1, 'RATIO_DIRECT', 10000, 'ZERO', False, '0.10', 'SIGNED'),
    ('M_ROI', 'EFFIC', 'RATIO', 1, 'RATIO_DIRECT', '0.100000', 'IMPUTE_MEDIAN', False, '0.40', 'SIGNED'),
    ('M_COST_PER_CONV_MINOR', 'EFFIC', 'MONEY_MINOR', -1, 'INVERSE_RATIO', 39900, 'ZERO', False, '0.30', 'SIGNED'),
    ('M_CONV_RATE', 'EFFIC', 'RATIO', 1, 'RATIO_DIRECT', '0.200000', 'SKIP', False, '0.30', 'SIGNED'),
    ('M_COMPLAINT_RATE', 'EXPER', 'RATIO', -1, 'INVERSE_RATIO', '0.002000', 'BLOCK', True, '0.40', 'SIGNED'),
    ('M_CONTACT_FREQ_PER_30D', 'EXPER', 'COUNT', -1, 'INVERSE_RATIO', 2, 'BLOCK', True, '0.40', 'SIGNED'),
    ('M_SATISFY_SCORE', 'EXPER', 'RATIO', 1, 'RATIO_DIRECT', '0.100000', 'IMPUTE_MEDIAN', False, '0.20', 'SIGNED'),
    ('M_CAMPAIGN_COST_MINOR', 'COST', 'MONEY_MINOR', -1, 'INVERSE_RATIO', 1995000, 'ZERO', False, '0.50', 'SIGNED'),
    ('M_HANDLE_SEC', 'COST', 'DURATION_SEC', -1, 'INVERSE_RATIO', 3990, 'SKIP', False, '0.50', 'SIGNED'),
    ('M_RETENTION_RATE', 'SUST', 'RATIO', 1, 'RATIO_DIRECT', '0.600000', 'IMPUTE_MEDIAN', False, '0.50', 'SIGNED'),
    ('M_REPEAT_USE_COUNT', 'SUST', 'COUNT', 1, 'RATIO_DIRECT', 100, 'ZERO', False, '0.50', 'PENDING'),
    ('M_REACH_RATE', 'PROC', 'RATIO', 1, 'RATIO_DIRECT', '0.800000', 'SKIP', False, '0.50', 'SIGNED'),
    ('M_OPTOUT_RATE', 'PROC', 'RATIO', -1, 'INVERSE_RATIO', '0.039900', 'ZERO', True, '0.50', 'SIGNED'),
)
METRIC_IDS = tuple(m[0] for m in METRICS)
BY_ID = {m[0]: m for m in METRICS}
REDLINE_METRICS = tuple(m[0] for m in METRICS if m[7])
ZERO_VARIATION_METRIC = 'M_AUM_MINOR'      # M34 构造 5 (T-ENT-02 / T-CMB-02)
ZERO_VARIATION_VALUE = 10000               # 12 策略 x 5 期恒等 -> d_j = 0
DOMINANT_METRIC = 'M_REV_MINOR'            # M34 构造 6 (T-SEN-02 / G-07)
DOMINANT_SHARE = _D('0.80')                # CONTRIB 内二级权重占比
DICT_VERSION = 'MD-SYNTH-2026'
CALIBER_VERSION = 'CAL-SYNTH-2026'
WEIGHT_VERSION_ID = 'WV-SYNTH-2026'
OAT20_WEIGHT_VERSION_ID = 'WV-SYNTH-2026-OAT20'
ANCHOR_SET_ID = 'AS-SYNTH-2026'
# M34 第 1459 行：证据分布 A x3 / B x3 / C x4 / D x2。
# 列: strategy_id, version_id, biz_domain, segment_type, evidence_intent, profile
STRATEGIES = (
    ('S-001', 'v1', 'CARD', 'RETAIL_NEW', 'A', 'G01_ALL_MET'),
    ('S-002', 'v1', 'CARD', 'RETAIL_EXIST', 'A', 'G06_NEAR_L1'),
    ('S-003', 'v1', 'CARD', 'SME', 'C', 'G02_C_HIGH'),
    ('S-004', 'v1', 'LOAN', 'RETAIL_NEW', 'B', 'G06_NEAR_L2'),
    ('S-005', 'v1', 'LOAN', 'RETAIL_EXIST', 'B', 'RANDOM'),
    ('S-005', 'v2', 'LOAN', 'RETAIL_EXIST', 'B', 'RANDOM'),
    ('S-006', 'v1', 'LOAN', 'SME', 'C', 'RANDOM'),
    ('S-007', 'v1', 'WEALTH', 'RETAIL_NEW', 'B', 'RANDOM'),
    ('S-008', 'v1', 'WEALTH', 'RETAIL_EXIST', 'C', 'RANDOM'),
    ('S-009', 'v1', 'WEALTH', 'SME', 'A', 'G03_CONTRIB_REDLINE'),
    ('S-010', 'v1', 'PAY', 'RETAIL_NEW', 'D', 'RANDOM'),
    ('S-011', 'v1', 'PAY', 'RETAIL_EXIST', 'C', 'RANDOM'),
    ('S-012', 'v1', 'PAY', 'SME', 'D', 'RANDOM'),
)
STRATEGY_IDS = tuple(sorted({s[0] for s in STRATEGIES}))
EVIDENCE_INTENT = {s[0]: s[4] for s in STRATEGIES}
PROFILE = {(s[0], s[1]): s[5] for s in STRATEGIES}
VERSION_BREAK_ID = 'S-005'                 # M34 构造 4 (G-08)
ANCHOR_IDS = ('S-001', 'S-002', 'S-003', 'S-004', 'S-005', 'S-007', 'S-008', 'S-011')
EXTREME_STRATEGY = ('S-901', 'v1', 'PAY', 'RETAIL_NEW', 'B')   # G-05，不入锚定集
EXTREME_ATTAINMENT = _D('1.90')
NO_TARGET_SUBJECT = 'S-007'                # G-04 载体
C_SHARE_UP_IDS = ('S-005', 'S-007')        # G-14: C 类占比 4/12 -> 6/12


def _flat(default_by_dim, special):
    '''把「每维度一个 attainment + 若干单指标覆盖」摊平成 metric_id -> attainment。'''
    return {m[0]: special.get(m[0], default_by_dim[m[1]]) for m in METRICS}


# 评价期的手算构造；历史期一律走 seed 随机，给标定留变异。
_DESIGNED = {
    'G01_ALL_MET': {m[0]: (_D('1.00') + _D('0.01') * i if m[3] == 1 else _D('1.00'))
                    for i, m in enumerate(METRICS)},
    'G02_C_HIGH': {m[0]: (_D('1.15') if m[3] == 1 else _D('1.00')) for m in METRICS},
    'G06_NEAR_L1': _flat({d: _D('1.05') for d in DIMS}, {
        'M_REV_MINOR': _D('0.90'), 'M_CUST_GAIN': _D('0.80'), 'M_AUM_MINOR': _D('1.00'),
        'M_COMPLAINT_RATE': _D('1.00'), 'M_CONTACT_FREQ_PER_30D': _D('1.00'),
        'M_SATISFY_SCORE': _D('1.25')}),
    'G06_NEAR_L2': _flat({d: _D('0.95') for d in DIMS}, {
        'M_REV_MINOR': _D('0.80'), 'M_CUST_GAIN': _D('0.60'), 'M_AUM_MINOR': _D('1.00'),
        'M_COMPLAINT_RATE': _D('1.00'), 'M_CONTACT_FREQ_PER_30D': _D('1.00'),
        'M_SATISFY_SCORE': _D('0.75')}),
    'G03_CONTRIB_REDLINE': _flat({d: _D('1.40') for d in DIMS}, {
        'M_REV_MINOR': _D('2.00'), 'M_CUST_GAIN': _D('2.00'), 'M_AUM_MINOR': _D('1.00'),
        'M_COST_PER_CONV_MINOR': _D('1.00'), 'M_COMPLAINT_RATE': _D('1.00'),
        'M_CONTACT_FREQ_PER_30D': _D('1.00'), 'M_CAMPAIGN_COST_MINOR': _D('1.00'),
        'M_HANDLE_SEC': _D('1.00'), 'M_OPTOUT_RATE': _D('1.00')}),
}
# 红线判定看事实值 vs 阈值，故直接写死；未列出的一律取 target（落在阈值内）。
_REDLINE_ACTUAL = {
    ('S-009', 'M_CONTACT_FREQ_PER_30D'): 6,                 # M37 E3: 6 > HARD 阈值 4
    ('S-009', 'M_COMPLAINT_RATE'): _D('0.008000'),          # G-03: > HARD 阈值 0.005
    ('S-006', 'M_COMPLAINT_RATE'): _D('0.007000'),          # G-15: 越线且无豁免留痕
    ('S-008', 'M_OPTOUT_RATE'): _D('0.095000')}             # SOFT 越线（软扣分路径）
# G-09：四条 missing_rule 分支各需一个真实缺格（评价期）；BLOCK 落在 S-008。
OMITTED_FACTS = frozenset({
    ('S-005', 'v2', EVAL_PERIOD, 'M_CAMPAIGN_COST_MINOR'),
    ('S-006', 'v1', EVAL_PERIOD, 'M_CUST_GAIN'),
    ('S-011', 'v1', EVAL_PERIOD, 'M_ROI'),
    ('S-008', 'v1', EVAL_PERIOD, 'M_COMPLAINT_RATE')})
# G-04：9/15 = 60% 指标无 target_value，跨 EFFIC/EXPER/COST/SUST 四个维度。
NO_TARGET_METRICS = ('M_ROI', 'M_COST_PER_CONV_MINOR', 'M_CONV_RATE',
                     'M_COMPLAINT_RATE', 'M_CONTACT_FREQ_PER_30D', 'M_SATISFY_SCORE',
                     'M_CAMPAIGN_COST_MINOR', 'M_HANDLE_SEC', 'M_REPEAT_USE_COUNT')
TABLE_MODELS = {
    'strategy_master': models.StrategyMasterRow, 'metric_dict': models.MetricDictRow,
    'metric_fact': models.MetricFactRow, 'design_card': models.DesignCardRow,
    'redline': models.RedlineRow, 'weight_version': models.WeightVersionDoc,
    'grade_rule': models.GradeRuleRow, 'anchor_set': models.AnchorSetDoc}
NATURAL_KEYS = {
    'strategy_master': ('strategy_id', 'version_id'),
    'metric_dict': ('metric_id', 'dict_version'),
    'metric_fact': ('strategy_id', 'version_id', 'period', 'metric_id'),
    'design_card': ('strategy_id', 'version_id'), 'redline': ('metric_id',),
    'weight_version': ('weight_version_id',), 'grade_rule': ('grade_code',),
    'anchor_set': ('anchor_set_id',)}
TABLE_ORDER = tuple(TABLE_MODELS)
DELIBERATE_CONSTRUCTIONS = (
    {'n': 1, 'ref': 'G-03', 'carrier': 'S-009',
     'what': 'CONTRIB 维度 1.90 + COMPLAINT_RATE/CONTACT_FREQ 越 HARD 红线'},
    {'n': 2, 'ref': 'G-02', 'carrier': 'S-003', 'what': 'C 类但 composite 手算 1.0846 > L1 门槛'},
    {'n': 3, 'ref': 'G-04', 'carrier': 'variants/G04_target_missing + S-007',
     'what': '9/15=60% 指标无 target_value，跨 4 个维度'},
    {'n': 4, 'ref': 'G-08', 'carrier': 'S-005 v1 -> v2',
     'what': '同 strategy_id 换 version_id 且 version_change_note 非空'},
    {'n': 5, 'ref': 'T-ENT-02/T-CMB-02', 'carrier': 'M_AUM_MINOR',
     'what': '零变异指标：12 策略 x 5 期恒为 10000'},
    {'n': 6, 'ref': 'T-SEN-02/G-07', 'carrier': 'M_REV_MINOR', 'what': '主导权重指标：CONTRIB 内 0.80'},
    {'n': 7, 'ref': 'G-15', 'carrier': 'S-006 + M_COMPLAINT_RATE',
     'what': 'waiver_allowed=true 且越线，8 表内无任何豁免审批留痕载体'})

# G-05 追加策略：+1 指标一律 1.90，-1 指标一律 1.00（不入锚定集）。
_DESIGNED['G05_EXTREME'] = {m[0]: (EXTREME_ATTAINMENT if m[3] == 1
                                    else _D('1.00')) for m in METRICS}


def _target(m):
    return _D(m[5]) if m[2] == 'RATIO' else int(m[5])


def _designed_actual(m, a):
    '''构造侧反推：+1 取 target*a，-1 取 target/a。不是 attainment 实现，只是把
    写死的构造值落进事实表；整数单位不闭合就报错，避免悄悄产出非整数金额。'''
    v = _target(m) * a if m[3] == 1 else _target(m) / a
    if m[2] == 'RATIO':
        return v.quantize(_Q)
    iv = int(v)
    if _D(iv) != v:
        raise ValueError('designed value not integral: ' + m[0] + ' a=' + str(a))
    return iv


def _random_actual(rng, m):
    '''seed 控制的随机事实值（M34 第 1461 行）。-1 方向的整数单位直接抽整数，
    保证 MONEY_MINOR / COUNT / DURATION_SEC 恒为 int。'''
    target = _target(m)
    if m[2] == 'RATIO':
        lo, hi = (100, 130) if m[3] == -1 else (70, 130)
        return (target * _D(rng.randint(lo, hi)) / _D(100)).quantize(_Q)
    if m[3] == -1:
        lo, hi = max(1, target * 10 // 13), max(2, target * 10 // 7)
    else:
        lo, hi = max(1, target * 7 // 10), max(2, target * 13 // 10)
    return rng.randint(lo, max(hi, lo + 1))


def _fact_values(m, actual):
    if m[2] != 'RATIO':
        return {'value_num': actual, 'value_den': None, 'value': actual}
    den = _D('1000000')
    return {'value_num': actual * den, 'value_den': den, 'value': actual}


def _fact_shell(sid, vid, period, mid):
    return {'strategy_id': sid, 'version_id': vid, 'period': period, 'metric_id': mid,
            'data_quality_flag': 'OK', 'snapshot_time': SNAPSHOT_TIME,
            'data_as_of': DATA_AS_OF, 'source_table': 'SYNTH_FACT_TABLE',
            'caliber_version': CALIBER_VERSION}


def _periods_for(sid, vid):
    if sid == EXTREME_STRATEGY[0]:
        return (EVAL_PERIOD,)      # G-05：追加策略只出现在评价期
    if sid == VERSION_BREAK_ID:
        return (EVAL_PERIOD,) if vid == 'v2' else HISTORY_PERIODS
    return ALL_PERIODS


def strategy_master_rows():
    rows = []
    for i, (sid, vid, dom, seg, _ev, _pf) in enumerate(STRATEGIES):
        old = sid == VERSION_BREAK_ID and vid == 'v1'
        rows.append({
            'strategy_id': sid, 'version_id': vid,
            'strategy_name': 'SYNTH-STRATEGY-' + sid[2:], 'biz_domain': dom,
            'scene_code': 'SYNTH_SCENE_%02d' % (i % 4 + 1), 'segment_type': seg,
            'online_date': date(2026, 7, 1) if vid == 'v2' else date(2025, 3, 1),
            'offline_date': date(2026, 6, 30) if old else None,
            'owner_dept': 'SYNTH_DEPT_%02d' % (i % 3 + 1),
            'owner_name': 'SYNTH_OWNER_%02d' % (i % 5 + 1),
            'status': 'RETIRED' if old else 'ACTIVE',
            'version_change_note': ('SYNTH-VERSION-BREAK: 触达方式与客群规则调整'
                                    if vid == 'v2' else None)})
    return tuple(rows)


def metric_dict_rows(no_target=(), pending=()):
    rows = []
    for mid, dim, unit, direction, formula, target, mrule, red, w2, sign in METRICS:
        unsign = mid in pending or sign == 'PENDING'
        rows.append({
            'metric_id': mid, 'metric_name': 'SYNTH-METRIC-' + mid[2:], 'dim_code': dim,
            'numerator_def': 'SYNTH_NUM_' + mid,
            'denominator_def': ('SYNTH_DEN_' + mid) if unit == 'RATIO' else None,
            'time_window': 'P30D', 'dedup_rule': 'SYNTH_DEDUP_CUST_ID',
            'missing_rule': mrule, 'outlier_rule': 'SYNTH_WINSOR_P1_P99',
            'attainment_formula': formula, 'direction': direction, 'unit': unit,
            'target_value': None if mid in no_target else _target(BY_ID[mid]),
            'target_basis': 'SYNTH_BUDGET_2026', 'is_redline': red,
            'owner_name': 'SYNTH_OWNER_01',
            'signoff_status': 'PENDING' if unsign else 'SIGNED',
            'signoff_date': None if unsign else date(2026, 1, 10),
            'dim_signoff_status': 'SIGNED', 'dict_version': DICT_VERSION,
            'caliber_version': CALIBER_VERSION})
    return tuple(rows)


def design_card(sid, vid, ev, card_status='COMPLETE', limit=None,
                criteria='SYNTH_SUCC_CRITERIA'):
    row = {'strategy_id': sid, 'version_id': vid, 'direct_goal': 'SYNTH_GOAL_' + sid,
           'process_metrics': ('M_REACH_RATE', 'M_CONV_RATE'),
           'result_metrics': ('M_REV_MINOR', 'M_ROI'), 'observation_window': 'P30D',
           'data_source': 'SYNTH_DW_TABLE', 'data_timeliness': 'T+1',
           'eval_owner': 'SYNTH_OWNER_02', 'alt_method_note': None,
           'card_status': card_status, 'estimator_method': None, 'experiment_id': None,
           'holdout_id': None, 'mde_ok': None, 'incremental_value': None,
           'incremental_ci_lower': None, 'incremental_ci_upper': None,
           'interpretation_limit': limit, 'risk_constraints': 'SYNTH_RISK_CONSTRAINT',
           'success_criteria': criteria, 'eval_method': 'OBSERVATIONAL_ONLY',
           'control_arrangement': 'NONE'}
    if ev == 'A':      # 随机对照 + 显著性判定 -> 证据 A
        row.update(eval_method='AB_TEST', control_arrangement='RANDOMIZED', mde_ok=True,
                   estimator_method='SYNTH_DIFF_IN_MEANS',
                   experiment_id='SYNTH-EXP-' + sid, incremental_value=120000,
                   incremental_ci_lower=60000, incremental_ci_upper=180000)
    elif ev == 'B':    # 准实验 -> 证据 B
        row.update(eval_method='DID', control_arrangement='CONCURRENT_CONTROL',
                   estimator_method='SYNTH_DID', holdout_id='SYNTH-HOLD-' + sid,
                   incremental_value=90000, incremental_ci_lower=30000,
                   incremental_ci_upper=150000)
    elif ev == 'C':    # 纯观察 + 解释边界非空 -> 证据 C
        row['interpretation_limit'] = limit or 'SYNTH-LIMIT: 无对照组，增量不可识别'
    return row


def design_card_rows(downgrade_to_c=()):
    rows = []
    for sid, vid, _d, _s, ev, _pf in STRATEGIES:
        eff = 'C' if sid in downgrade_to_c else ev
        kw = {'card_status': 'COMPLETE', 'limit': None,
              'criteria': 'SYNTH_SUCC_CRITERIA'}
        if sid in downgrade_to_c:
            kw['limit'] = 'SYNTH-LIMIT: 变体降级为 C 类'
        if sid == 'S-010':       # D 类路径 1：评价设计卡 MISSING
            kw.update(card_status='MISSING', criteria='')
        elif sid == 'S-011':     # G-13：PARTIAL，缺成功判定
            kw.update(card_status='PARTIAL', criteria='')
        rows.append(design_card(sid, vid, eff, **kw))
    return tuple(rows)


def redline_rows():
    return ({'metric_id': 'M_CONTACT_FREQ_PER_30D', 'level': 'HARD', 'comparator': 'GT',
             'threshold_value': 4, 'forced_grade': 'L4',
             'reason_code': reason_codes.redline_hard('M_CONTACT_FREQ_PER_30D'), 'waiver_allowed': True},
            {'metric_id': 'M_COMPLAINT_RATE', 'level': 'HARD', 'comparator': 'GT',
             'threshold_value': _D('0.005000'), 'forced_grade': 'L4',
             'reason_code': reason_codes.redline_hard('M_COMPLAINT_RATE'), 'waiver_allowed': True},
            {'metric_id': 'M_OPTOUT_RATE', 'level': 'SOFT', 'comparator': 'GT',
             'threshold_value': _D('0.080000'), 'forced_grade': 'L4',
             'reason_code': reason_codes.redline_soft('M_OPTOUT_RATE'), 'waiver_allowed': False})


def weight_version(wid, l1, eff_to, status='FROZEN'):
    return {'weight_version_id': wid, 'status': status,
            'effective_from': date(2026, 1, 1), 'effective_to': eff_to,
            'level1_weights': dict(l1),
            'level2_weights': {d: {m[0]: _D(m[8]) for m in METRICS if m[1] == d}
                               for d in DIMS},
            'approved_by': 'SYNTH_APPROVER', 'approved_date': date(2025, 12, 20),
            'provenance': None}


def weight_version_rows():
    return (weight_version(WEIGHT_VERSION_ID, LEVEL1_WEIGHTS, date(2026, 12, 31)),)


def grade_rule_rows():
    # 门槛/连续期数均为合成治理值：PLACEHOLDER 字符串过不了 pydantic 类型门（缺口已上报）。
    # L1 门槛 1.00 / L2 门槛 0.90 是 G-06 手算翻转点的依据。
    spec = (('L1', '1.00', 'A', True, 1, 'L3'), ('L2', '0.90', 'B', True, 0, 'L3'),
            ('L3', '0.70', 'C', True, 0, 'L3'), ('L4', '0.00', 'D', False, 0, 'L4'))
    return tuple({'grade_code': g, 'grade_label': 'SYNTH_' + g,
                  'attainment_floor': _D(fl), 'evidence_class_min': ev,
                  'redline_pass_required': rp, 'promotion_streak': st,
                  'actions': ('SYNTH_ACTION_' + g, 'SYNTH_ACTION_MONITOR'),
                  'action_gate': 'SYNTH_GATE_' + g, 'max_grade_if_no_target': mx}
                 for g, fl, ev, rp, st, mx in spec)


def anchor_set_rows():
    return ({'anchor_set_id': ANCHOR_SET_ID, 'strategy_ids': ANCHOR_IDS,
             'effective_from': date(2026, 1, 1), 'effective_to': date(2026, 12, 31),
             'rationale': 'SYNTH-ANCHOR-RATIONALE'},)


def metric_fact_rows(seed, subjects=None):
    rng = random.Random(seed)
    rows = []
    for sid, vid, _d, _s, _e, profile in (subjects if subjects is not None
                                          else STRATEGIES):
        designed = _DESIGNED.get(profile, {})
        for period in _periods_for(sid, vid):
            for m in METRICS:
                if (sid, vid, period, m[0]) in OMITTED_FACTS:
                    continue
                if m[0] == ZERO_VARIATION_METRIC:
                    actual = ZERO_VARIATION_VALUE
                elif (period == EVAL_PERIOD and m[0] in REDLINE_METRICS
                        and (sid, m[0]) in _REDLINE_ACTUAL):
                    actual = _REDLINE_ACTUAL[(sid, m[0])]
                elif period == EVAL_PERIOD and m[0] in designed:
                    actual = _designed_actual(m, designed[m[0]])
                else:
                    actual = _random_actual(rng, m)
                row = _fact_shell(sid, vid, period, m[0])
                row.update(_fact_values(m, actual))
                rows.append(row)
    return tuple(rows)


def _enc(v):
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_enc(x) for x in v]
    if isinstance(v, dict):
        return {k: _enc(x) for k, x in v.items()}
    return v


def to_jsonl(rows):
    return ''.join(json.dumps(_enc(r), sort_keys=True, ensure_ascii=False,
                              separators=(',', ':')) + '\n' for r in rows)


def to_json(doc):
    return json.dumps(_enc(doc), sort_keys=True, ensure_ascii=False, indent=2) + '\n'


def sha256_text(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def validate_bundle(bundle):
    '''逐行过一次 pydantic（R-2：字段名/类型必须真能落进契约模型）。'''
    for table in TABLE_ORDER:
        for row in bundle[table]:
            TABLE_MODELS[table](**row)
    return sum(len(bundle[t]) for t in TABLE_ORDER)


def build_bundle(seed=SEED_DEFAULT):
    bundle = {
        'strategy_master': strategy_master_rows(), 'metric_dict': metric_dict_rows(),
        'metric_fact': metric_fact_rows(seed), 'design_card': design_card_rows(),
        'redline': redline_rows(), 'weight_version': weight_version_rows(),
        'grade_rule': grade_rule_rows(), 'anchor_set': anchor_set_rows()}
    validate_bundle(bundle)
    return bundle


def build_variants():
    sid, vid, dom, seg, ev = EXTREME_STRATEGY
    sm = {'strategy_id': sid, 'version_id': vid, 'strategy_name': 'SYNTH-STRATEGY-901',
          'biz_domain': dom, 'scene_code': 'SYNTH_SCENE_01', 'segment_type': seg,
          'online_date': date(2026, 7, 1), 'offline_date': None,
          'owner_dept': 'SYNTH_DEPT_01', 'owner_name': 'SYNTH_OWNER_01',
          'status': 'ACTIVE', 'version_change_note': None}
    extreme = metric_fact_rows(SEED_DEFAULT, subjects=(
        (sid, vid, dom, seg, ev, 'G05_EXTREME'),))
    return {
        'G04_target_missing': {
            'golden_refs': ('G-04',), 'subject': NO_TARGET_SUBJECT,
            'purpose': '9/15=60% 指标 target_value 置空，跨 4 个维度 -> 绝对轨覆盖不足',
            'replace': {'metric_dict': [
                r for r in metric_dict_rows(no_target=NO_TARGET_METRICS)
                if r['metric_id'] in NO_TARGET_METRICS]}, 'append': {}},
        'G05_append_extreme': {
            'golden_refs': ('G-05',), 'subject': sid,
            'purpose': '基线后追加 attainment=1.90 的极端策略，且不入锚定集',
            'replace': {},
            'append': {'strategy_master': [sm], 'design_card': [design_card(sid, vid, ev)],
                       'metric_fact': list(extreme)}},
        'G06_weight_oat20': {
            'golden_refs': ('G-06',), 'subject': 'S-002,S-004',
            'purpose': 'CONTRIB x1.2 后其余重归一（12 位小数精确闭合）',
            'replace': {},
            'append': {'weight_version': [weight_version(
                OAT20_WEIGHT_VERSION_ID, LEVEL1_WEIGHTS_OAT20, date(2026, 12, 31))]}},
        'G10_dim_emptied': {
            'golden_refs': ('G-10',), 'subject': 'M_RETENTION_RATE',
            'purpose': 'SUST 第二个指标也置 PENDING -> 维度被清空 -> preflight BLOCK',
            'replace': {'metric_dict': [
                r for r in metric_dict_rows(pending=('M_RETENTION_RATE',))
                if r['metric_id'] == 'M_RETENTION_RATE']}, 'append': {}},
        'G11_stale_weight': {
            'golden_refs': ('G-11',), 'subject': WEIGHT_VERSION_ID,
            'purpose': 'effective_to=2026-06-30 早于评价期 2026-Q3 -> STALE -> BLOCK',
            'replace': {'weight_version': [weight_version(
                WEIGHT_VERSION_ID, LEVEL1_WEIGHTS, date(2026, 6, 30))]}, 'append': {}},
        'G14_c_share_up': {
            'golden_refs': ('G-14',), 'subject': ','.join(C_SHARE_UP_IDS),
            'purpose': '两条 B 类降为 C 类 -> C 类占比 4/12 升到 6/12',
            'replace': {'design_card': [
                r for r in design_card_rows(downgrade_to_c=C_SHARE_UP_IDS)
                if r['strategy_id'] in C_SHARE_UP_IDS]}, 'append': {}}}


def build_negative():
    '''故意**不合法**的原始载荷：不进 pydantic，供 preflight BLOCK 分支使用。'''
    row = _fact_shell('S-007', 'v1', EVAL_PERIOD, 'M_REV_MINOR')
    row.update({'value_num': 100.5, 'value_den': None, 'value': 100.5,
                'snapshot_time': SNAPSHOT_TIME.isoformat(),
                'data_as_of': DATA_AS_OF.isoformat()})
    return {'G11_money_non_integer': {
        'golden_refs': ('G-11',), 'table': 'metric_fact',
        'expect_rejected_by': 'models.MetricFactRow',
        'expect_reason_code': reason_codes.RC.MONEY_NON_INTEGER.value,
        'purpose': 'MONEY_MINOR 字段传入非整数 -> preflight BLOCK，不产出 score_card',
        'row': row}}


def build_manifest(seed, bundle, docs):
    files = {}
    for path in sorted(docs):
        text = docs[path]
        files[path] = {'sha256': sha256_text(text),
                       'bytes': len(text.encode('utf-8')),
                       'rows': text.count('\n') if path.endswith('.jsonl') else 1}
    return {'schema': SCHEMA, 'generator': GENERATOR_VERSION, 'seed': seed,
            'synthetic_only': True,
            'periods': {'history': list(HISTORY_PERIODS), 'eval': EVAL_PERIOD},
            'intended_evidence_class': dict(sorted(EVIDENCE_INTENT.items())),
            'evidence_distribution': {
                c: sum(1 for v in EVIDENCE_INTENT.values() if v == c)
                for c in ('A', 'B', 'C', 'D')},
            'counts': {t: len(bundle[t]) for t in TABLE_ORDER},
            'deliberate_constructions': list(DELIBERATE_CONSTRUCTIONS),
            'files': files}


def build_documents(seed=SEED_DEFAULT, golden_map=None):
    bundle = build_bundle(seed)
    docs = {'fixtures/input/' + t + '.jsonl': to_jsonl(bundle[t]) for t in TABLE_ORDER}
    for name, doc in sorted(build_variants().items()):
        docs['fixtures/variants/' + name + '.json'] = to_json(doc)
    for name, doc in sorted(build_negative().items()):
        docs['fixtures/negative/' + name + '.json'] = to_json(doc)
    if golden_map is not None:
        docs['fixtures/golden/golden_map.json'] = to_json(golden_map)
    docs['fixtures/manifest.json'] = to_json(build_manifest(seed, bundle, docs))
    return bundle, docs


def write_bundle(root, seed=SEED_DEFAULT, golden_map=None):
    '''落盘 fixtures/**（LF / 无 BOM / 无 TAB），返回 {相对路径: 文本}。'''
    _bundle, docs = build_documents(seed, golden_map)
    for path in sorted(docs):
        full = os.path.join(root, path.replace('/', os.sep))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(docs[path])
    return docs
