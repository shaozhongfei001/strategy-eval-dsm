'''A1 / tools.gen_golden -- 生成 fixtures/** 与 golden 期望值骨架（G-01~G-15）。

用法（仓库根目录）: python3 tools/gen_golden.py [--seed N] [--out DIR]

期望值纪律（R-14 / digest M31 第 1419 行）：expects 只来自 digest M31 的「期望输出」
列，hand 只来自 fixtures 里写死的 target/actual/权重的手算（算式已给全，可离线复核），
**不读任何实现输出**。value_status 标注来源；PENDING_IMPL 一律留空，等首次通过人工
评审的运行结果固化。
'''
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dsm import fixtures_gen as fg   # noqa: E402

SCHEMA = 'dsm-golden-skeleton-1'
E = fg.EVAL_PERIOD


def _p(t, m, e=None, n=None, none=False, nonnull=(), notcontains=None, scope='base'):
    probe = {'t': t, 'm': m, 'scope': scope}
    for key, val in (('e', e), ('n', n), ('none', none or None),
                     ('nonnull', list(nonnull) or None), ('notcontains', notcontains)):
        if val:
            probe[key] = val
    return probe


def _case(cid, src, scope, scenario, subject, probes, expects, hand, status, gap=None):
    row = {'id': cid, 'source': src, 'scope': scope, 'scenario': scenario,
           'subject': subject, 'probes': probes, 'expects': expects, 'hand': hand,
           'value_status': status}
    if gap:
        row['gap'] = gap
    return row


def golden_cases():
    return (
        _case('G-01', 'digest M31 第 1403 行', 'base',
              'A 类证据 + 全指标达标 + 无红线 -> 一级', 'S-001',
              [_p('design_card', {'strategy_id': 'S-001'},
                  {'control_arrangement': 'RANDOMIZED', 'eval_method': 'AB_TEST',
                   'card_status': 'COMPLETE', 'mde_ok': True},
                  nonnull=['experiment_id', 'incremental_ci_lower']),
               _p('metric_fact', {'strategy_id': 'S-001', 'period': E}, n=15),
               _p('metric_fact', {'strategy_id': 'S-001', 'period': E,
                                  'metric_id': 'M_CONTACT_FREQ_PER_30D'}, {'value': 2}),
               _p('metric_fact', {'strategy_id': 'S-001', 'period': E,
                                  'metric_id': 'M_COMPLAINT_RATE'},
                  {'value': '0.002000'})],
              {'grade': 'L1', 'evidence_class': 'A', 'eligible_for_L1_library': True,
               'reason_codes': []},
              {'attainment_min': '1.000000',
               'composite_absolute': '1.021930',
               'arithmetic': '15 个指标 attainment 全 >= 1.00（+1 取 1.00+0.01*i，-1 取 '
                             '1.00）；维度值 CONTRIB 1.0010 / EFFIC 1.0270 / EXPER 1.0160'
                             ' / COST 1.0000 / SUST 1.1150 / PROC 1.0650；'
                             '0.30*1.0010+0.21*1.0270+0.21*1.0160+0.14*1.0000'
                             '+0.07*1.1150+0.07*1.0650 = 1.021930 >= L1 门槛 1.00'},
              'SPEC+HAND_COMPUTED'),
        _case('G-02', 'digest M31 第 1404 行 / M37 E2', 'base',
              'C 类高分策略被证据门禁拦下，只在 (biz_domain, C) 池内排名', 'S-003',
              [_p('design_card', {'strategy_id': 'S-003'},
                  {'control_arrangement': 'NONE', 'eval_method': 'OBSERVATIONAL_ONLY',
                   'card_status': 'COMPLETE'}, nonnull=['interpretation_limit']),
               _p('metric_fact', {'strategy_id': 'S-003', 'period': E,
                                  'metric_id': 'M_REV_MINOR'}, {'value': 11500})],
              {'grade': 'L2', 'reason_code': 'GR_EVIDENCE_GATE_L1',
               'eligible_for_L1_library': False,
               'l1_gate_reason': 'PL_L1_GATE_EVIDENCE',
               'rank_in_pool': '仅 (biz_domain=CARD, evidence_class=C) 池内'},
              {'composite_absolute': '1.084600',
               'arithmetic': 'CONTRIB 1.1350 / EFFIC 1.1050 / EXPER 1.0300 / COST 1.0000'
                             ' / SUST 1.1500 / PROC 1.0750；0.30*1.1350+0.21*1.1050+'
                             '0.21*1.0300+0.14*1.0000+0.07*1.1500+0.07*1.0750 = 1.0846',
               'note': '1.0846 > L1 门槛 1.00 -> 降级只能来自证据门禁，不来自分数'},
              'SPEC+HAND_COMPUTED'),
        _case('G-03', 'digest M31 第 1405 行 / M37 E3', 'base',
              '贡献极高但红线越线 -> 强制四级（非补偿）', 'S-009',
              [_p('metric_fact', {'strategy_id': 'S-009', 'period': E,
                                  'metric_id': 'M_CONTACT_FREQ_PER_30D'}, {'value': 6}),
               _p('metric_fact', {'strategy_id': 'S-009', 'period': E,
                                  'metric_id': 'M_COMPLAINT_RATE'},
                  {'value': '0.008000'}),
               _p('metric_fact', {'strategy_id': 'S-009', 'period': E,
                                  'metric_id': 'M_REV_MINOR'}, {'value': 20000}),
               _p('redline', {'metric_id': 'M_CONTACT_FREQ_PER_30D'},
                  {'level': 'HARD', 'comparator': 'GT', 'threshold_value': 4,
                   'forced_grade': 'L4'})],
              {'grade': 'L4', 'forced': True, 'redline_pass': False,
               'reason_code': 'REDLINE_HARD_M_CONTACT_FREQ_PER_30D',
               'composite_absolute': '仍输出但不生效'},
              {'dim_CONTRIB': '1.900000',
               'arithmetic': '0.80*2.00 + 0.10*2.00 + 0.10*1.00 = 1.90（M31 要求 1.9）；'
                             'CONTACT_FREQ 6 > 4 且 COMPLAINT_RATE 0.008 > 0.005 双越线'},
              'SPEC+HAND_COMPUTED'),
        _case('G-04', 'digest M31 第 1406 行 / M37 E4', 'variant:G04_target_missing',
              '目标值大面积缺失 -> 绝对轨覆盖不足 -> 封顶三级', fg.NO_TARGET_SUBJECT,
              [_p('metric_dict', {'target_value': None}, n=9,
                  scope='variant:G04_target_missing'),
               _p('metric_dict', {'target_value': None}, none=True),
               _p('metric_fact', {'strategy_id': fg.NO_TARGET_SUBJECT, 'period': E},
                  n=15)],
              {'grade': 'L3', 'capped_flag': True,
               'cap_reason': 'GR_CAPPED_NO_TARGET',
               'composite_relative': '仍给出（池内参考）'},
              {'null_target_share': '9/15 = 0.600000（M31 要求 60%）',
               'coverage_count': '0.400000 = 6/15',
               'coverage_weighted': '0.405000 = 0.30 + 0.07*0.50 + 0.07',
               'dims_without_target': 'EFFIC / EXPER / COST / SUST（6 个维度中的 4 个）'},
              'SPEC+HAND_COMPUTED',
              gap='digest M31/M37 写作 GRADE_CAPPED_NO_TARGET，dsm/reason_codes.py 注册'
                  '的是 GR_CAPPED_NO_TARGET；本骨架按注册码记录，口径差请主控裁决'),
        _case('G-05', 'digest M31 第 1407 行', 'variant:G05_append_extreme',
              '基线后追加极端策略（不入锚定集）重跑，存量结果完全不变',
              fg.EXTREME_STRATEGY[0],
              [_p('strategy_master', {'strategy_id': fg.EXTREME_STRATEGY[0]},
                  scope='variant:G05_append_extreme'),
               _p('metric_fact', {'strategy_id': fg.EXTREME_STRATEGY[0], 'period': E},
                  n=15, scope='variant:G05_append_extreme'),
               _p('anchor_set', {'anchor_set_id': fg.ANCHOR_SET_ID},
                  notcontains={'strategy_ids': fg.EXTREME_STRATEGY[0]}),
               _p('strategy_master', {'strategy_id': fg.EXTREME_STRATEGY[0]}, none=True)],
              {'existing_norm_composite_grade': '完全不变', 'rank_reversal': '不出现'},
              {'extreme_attainment': '1.900000（+1 指标）/ 1.000000（-1 指标）',
               'periods': '仅评价期 ' + E},
              'SPEC（需两次运行对比，期望值不预填）'),
        _case('G-06', 'digest M31 第 1408 行 / M37 E5', 'variant:G06_weight_oat20',
              'CONTRIB 权重 x1.2 其余重归一 -> flip_rate / stability_label',
              'S-002,S-004',
              [_p('weight_version', {'weight_version_id': fg.OAT20_WEIGHT_VERSION_ID},
                  scope='variant:G06_weight_oat20'),
               _p('weight_version', {'weight_version_id': fg.WEIGHT_VERSION_ID},
                  {'status': 'FROZEN'})],
              {'flip_rate': '计算正确', 'at_least_one': 'NEAR_BOUNDARY 策略翻转为 L3',
               'stability_label': '正确'},
              {'S-002_base': '1.005000 = 0.30*0.90 + 0.70*1.05 -> L1',
               'S-002_oat20': '0.996000 = 0.36*0.90 + 0.64*1.05 -> 跌破 1.00 -> L2',
               'S-004_base': '0.905000 = 0.30*0.80 + 0.70*0.95 -> L2',
               'S-004_oat20': '0.896000 = 0.36*0.80 + 0.64*0.95 -> 跌破 0.90 -> L3',
               'weight_closure': '一级权重取 0.07 整数倍，x1.2 重归一后 12 位小数精确闭合'},
              'SPEC+HAND_COMPUTED'),
        _case('G-07', 'digest M31 第 1409 行', 'base',
              'LOO：构造权重占比过大的单一指标', fg.DOMINANT_METRIC,
              [_p('weight_version', {'weight_version_id': fg.WEIGHT_VERSION_ID},
                  {'level2_weights': {'CONTRIB': {fg.DOMINANT_METRIC: '0.80'}}})],
              {'loo_impact_max': fg.DOMINANT_METRIC,
               'report_warning': '存在单一指标过度影响',
               'reason_code': 'DOMINANT_METRIC'},
              {'dominant_share': '0.800000（CONTRIB 内）；CONTRIB 一级权重 0.30 -> '
                                 '该指标对 composite 的直接权重 0.240000'},
              'SPEC+HAND_COMPUTED'),
        _case('G-08', 'digest M31 第 1410 行', 'base',
              '同 strategy_id 版本变更 -> VERSION_BREAK / 趋势抑制 / streak 重置',
              fg.VERSION_BREAK_ID,
              [_p('strategy_master', {'strategy_id': fg.VERSION_BREAK_ID,
                                      'version_id': 'v2'}, {'status': 'ACTIVE'},
                  nonnull=['version_change_note']),
               _p('strategy_master', {'strategy_id': fg.VERSION_BREAK_ID,
                                      'version_id': 'v1'},
                  {'status': 'RETIRED', 'offline_date': '2026-06-30'}),
               _p('metric_fact', {'strategy_id': fg.VERSION_BREAK_ID,
                                  'version_id': 'v1', 'period': E}, none=True),
               _p('metric_fact', {'strategy_id': fg.VERSION_BREAK_ID,
                                  'version_id': 'v2', 'period': E}, n=14)],
              {'version_break': True, 'reason_code': 'GR_VERSION_BREAK',
               'cross_version_trend': '抑制', 'promotion_streak': '重置'},
              {'v1_periods': '4 期历史 2025-Q3..2026-Q2', 'v2_periods': '评价期 ' + E},
              'SPEC+HAND_COMPUTED'),
        _case('G-09', 'digest M31 第 1411 行', 'base',
              'missing_rule 四种分支各有一个真实缺格', 'S-005/v2,S-006,S-011,S-008',
              [_p('metric_dict', {'missing_rule': r}, n=1) for r in
               ('ZERO', 'SKIP', 'IMPUTE_MEDIAN', 'BLOCK')] +
              [_p('metric_fact', {'strategy_id': s, 'period': E, 'metric_id': m},
                  none=True) for s, m in
               (('S-005', 'M_CAMPAIGN_COST_MINOR'), ('S-006', 'M_CUST_GAIN'),
                ('S-011', 'M_ROI'), ('S-008', 'M_COMPLAINT_RATE'))],
              {'ZERO': '按 0 计入', 'SKIP': '剔除并重归一', 'IMPUTE_MEDIAN': '中位数填补',
               'BLOCK': 'S-008 不产出分数', 'four_branches_distinct': True},
              {'branch_map': 'ZERO->S-005/v2 M_CAMPAIGN_COST_MINOR, SKIP->S-006 '
                             'M_CUST_GAIN, IMPUTE_MEDIAN->S-011 M_ROI, BLOCK->S-008 '
                             'M_COMPLAINT_RATE'},
              'SPEC+HAND_COMPUTED'),
        _case('G-10', 'digest M31 第 1412 行', 'base+variant:G10_dim_emptied',
              '未签认指标被剔除；维度被清空 -> preflight BLOCK',
              'M_REPEAT_USE_COUNT,M_RETENTION_RATE',
              [_p('metric_dict', {'metric_id': 'M_REPEAT_USE_COUNT'},
                  {'signoff_status': 'PENDING'}),
               _p('metric_dict', {'metric_id': 'M_RETENTION_RATE'},
                  {'signoff_status': 'PENDING'}, scope='variant:G10_dim_emptied')],
              {'base': '该指标剔除；coverage 下降；reason = METRIC_NOT_SIGNED',
               'variant': 'SUST 维度被清空 -> preflight BLOCK',
               'reason_code_variant': 'DIMENSION_EMPTIED'},
              {'sust_metrics': 'SUST 仅 2 个指标，变体把两个都置 PENDING'},
              'SPEC+HAND_COMPUTED'),
        _case('G-11', 'digest M31 第 1413 行',
              'variant:G11_stale_weight+negative:G11_money_non_integer',
              '(a) 权重版本过期 (b) MONEY_MINOR 非整数 -> 均 BLOCK，不出 score_card',
              fg.WEIGHT_VERSION_ID,
              [_p('weight_version', {'weight_version_id': fg.WEIGHT_VERSION_ID},
                  {'effective_to': '2026-06-30'}, scope='variant:G11_stale_weight'),
               _p('row', {'metric_id': 'M_REV_MINOR'}, {'value_num': '100.5'},
                  scope='negative:G11_money_non_integer')],
              {'a_preflight': 'BLOCK', 'a_code': 'WEIGHT_VERSION_STALE',
               'b_preflight': 'BLOCK', 'b_code': 'MONEY_NON_INTEGER',
               'score_card': '均不产出'},
              {'eval_period': E, 'effective_to': '2026-06-30 早于评价期起点 2026-07-01'},
              'SPEC+HAND_COMPUTED',
              gap='digest M31 写作 code = STALE，注册码为 WEIGHT_VERSION_STALE；'
                  '按注册码记录'),
        _case('G-12', 'digest M31 第 1414 行', 'base',
              '同 manifest 连续两次运行 -> reproducibility_hash 精确相等', fg.RUN_ID,
              [_p('metric_fact', {'period': E}, n=1),
               _p('strategy_master', {'strategy_id': 'S-001'}, n=1)],
              {'reproducibility_hash': '两次精确相等',
               'money_and_int_fields': '精确相等', 'ratio_fields': '差值 <= 1e-12'},
              {'fixture_side_guarantee': 'fixtures_gen 无时钟、无全局状态、无 dict 无序'
                                         '依赖，同 seed 逐字节相等'},
              'SPEC'),
        _case('G-13', 'digest M31 第 1415 行', 'base',
              '评价设计卡 PARTIAL（缺成功判定）-> 证据最高只能 C', 'S-011',
              [_p('design_card', {'strategy_id': 'S-011'},
                  {'card_status': 'PARTIAL', 'control_arrangement': 'NONE',
                   'eval_method': 'OBSERVATIONAL_ONLY', 'success_criteria': ''},
                  nonnull=['interpretation_limit'])],
              {'evidence_class_max': 'C', 'evidence_reason': 'EVIDENCE_CARD_PARTIAL'},
              {}, 'SPEC'),
        _case('G-14', 'digest M31 第 1416 行', 'variant:G14_c_share_up',
              '一级库中 C 类占比上升 -> MIX_QUALITY_DEGRADED，占比双报分列',
              ','.join(fg.C_SHARE_UP_IDS),
              [_p('design_card', {'strategy_id': s},
                  {'control_arrangement': 'NONE',
                   'eval_method': 'OBSERVATIONAL_ONLY'},
                  scope='variant:G14_c_share_up') for s in fg.C_SHARE_UP_IDS],
              {'warning': 'MIX_QUALITY_DEGRADED', 'report': '池内占比与合并占比分列'},
              {'c_share_base': '4/12 = 0.333333', 'c_share_variant': '6/12 = 0.500000'},
              'SPEC+HAND_COMPUTED'),
        _case('G-15', 'digest M31 第 1417 行', 'base',
              'waiver_allowed=true 但缺 approval_id -> 视为未豁免，照常强制降级', 'S-006',
              [_p('redline', {'metric_id': 'M_COMPLAINT_RATE'},
                  {'level': 'HARD', 'waiver_allowed': True,
                   'threshold_value': '0.005000'}),
               _p('metric_fact', {'strategy_id': 'S-006', 'period': E,
                                  'metric_id': 'M_COMPLAINT_RATE'},
                  {'value': '0.007000'})],
              {'treated_as': '未豁免', 'grade': 'L4', 'forced': True,
               'reason_code': 'WAIVER_INVALID'},
              {'threshold': '0.005000', 'actual': '0.007000 > 0.005000 -> HARD 越线'},
              'SPEC+HAND_COMPUTED',
              gap='8 张输入表内没有豁免审批留痕的载体（approval_id / 有效期 / 范围只存在'
                  '于输出侧 RedlineEvalRow）；本包用 waiver_allowed=true + 越线 + 全库无'
                  '审批记录构造，输入侧载体缺口请主控裁决'))


def golden_map(seed):
    cases = golden_cases()
    return {'schema': SCHEMA, 'seed': seed, 'generated_by': 'tools/gen_golden.py',
            'discipline': 'R-14：expects 来自 digest M31，hand 来自 fixtures 构造手算，'
                          '严禁用实现输出反填；PENDING_IMPL 一律留空',
            'value_status_legend': {
                'SPEC': '逐字来自 digest M31 G-01~G-15 期望输出列',
                'HAND_COMPUTED': '由 fixtures 写死的 target/actual/权重手算，算式见 hand',
                'SPEC+HAND_COMPUTED': '两者皆有',
                'PENDING_IMPL': '待实现产出并经人工评审后固化（当前为空）'},
            'fixtures_ref': 'fixtures/manifest.json',
            'probe_semantics': {
                't': '表名（negative scope 下固定为 row）', 'm': '行子集匹配',
                'e': '该行必须满足的字段值', 'n': '匹配行数下限',
                'none': '匹配行数必须为 0', 'nonnull': '这些字段必须非空',
                'notcontains': '字段 -> 该值不得出现在其列表值里',
                'scope': 'base / variant:<name> / negative:<name>'},
            'case_count': len(cases), 'cases': cases}


def main(argv=None):
    ap = argparse.ArgumentParser(description='生成 fixtures/** 与 golden 期望值骨架')
    ap.add_argument('--seed', type=int, default=fg.SEED_DEFAULT)
    ap.add_argument('--out', default=os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    args = ap.parse_args(argv)
    docs = fg.write_bundle(args.out, seed=args.seed, golden_map=golden_map(args.seed))
    print('seed=' + str(args.seed) + ' cases=' + str(len(golden_cases()))
          + ' files=' + str(len(docs)))
    for path in sorted(docs):
        print('  ' + path + ' ' + str(len(docs[path].encode('utf-8'))) + 'B')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
