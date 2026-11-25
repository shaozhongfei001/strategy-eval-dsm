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
from functools import lru_cache

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


G09_RULES = ('ZERO', 'SKIP', 'IMPUTE_MEDIAN', 'BLOCK')


@lru_cache(maxsize=4)
def _g09_branch(seed=fg.SEED_DEFAULT):
    '''G-09 四分支的载体与字典计数：从冻结 fixtures 的真实数据推导，不写死字面量。

    ORCH-40 第5条（A1c 明确移交）：A1c(6299245) D-A1-03 依 ORCH-37 第1条把 BLOCK 缺格
    载体由 M_COMPLAINT_RATE（HARD 红线）迁到 M_SATISFY_SCORE 并同维对调 missing_rule，
    而本文件旧版把四个载体写成字面量 -> golden_map 的 none:true 探针被证伪（红条
    tests/test_fixtures.py::test_golden_trigger_probes[G-09]）。改为按 [L1134] 的四个
    missing_rule 名 + [L1411]「四种分支各有一个真实缺格」在评价期事实表里重算载体，
    载体再迁移时无需改代码。返回 (branch_map 文本, subject 串, {rule: (sid, vid, mid)},
    {rule: 计数}, 计数文本)。
    '''
    bundle = fg.build_bundle(seed)
    rows = {r['metric_id']: r for r in bundle['metric_dict']}
    census = {r: sum(1 for x in rows.values() if x['missing_rule'] == r) for r in G09_RULES}
    have = {(f['strategy_id'], f['version_id'], f['metric_id'])
            for f in bundle['metric_fact'] if f['period'] == E}
    carriers = {}
    for sid, vid in sorted({(s, v) for (s, v, _m) in have}):
        for m in sorted(rows):
            rule = rows[m]['missing_rule']
            if rule in G09_RULES and rule not in carriers and (sid, vid, m) not in have:
                carriers[rule] = (sid, vid, m)
    missing = [r for r in G09_RULES if r not in carriers]
    if missing:
        raise SystemExit('G-09: no real missing cell for ' + ','.join(missing))

    def _sub(sid, vid):
        return sid + ('/' + vid if vid != 'v1' else '')

    branch_map = ', '.join('%s->%s %s' % (r, _sub(*carriers[r][:2]), carriers[r][2])
                           for r in G09_RULES)
    subject = ','.join(_sub(*carriers[r][:2]) for r in G09_RULES)
    census_text = (' / '.join('%s %d' % (r, census[r]) for r in G09_RULES)
                   + '（metric_dict 全表 %d 行实测计数；probe 的 n 是下限语义）'
                     % len(rows))
    return branch_map, subject, carriers, census, census_text


def golden_cases(seed=fg.SEED_DEFAULT):
    (g09_branch_map, g09_subject, g09_carriers, g09_census,
     g09_census_text) = _g09_branch(seed)
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
              # A1c(6299245) ADR §11 D-A1-06（只登记未代填，R-14 交本包独立手算）：
              # 旧值 extreme_attainment「+1 指标一律 1.900000」与变体事实行不自洽 ——
              # [L1460] 强制的零变异构造把 M_AUM_MINOR 恒留成 10000 = target，达成率
              # 只能是 1.0；[L1407] 原文只写「attainment 极高」，无任何数值，故 1.9
              # 在 G-05 侧无原文依据（1.9 的原文出处是 [L1405] 的 G-03，不得跨用例串味）。
              # 手算（纯有理数精确，V-9 全程不经 float）：
              #   CONTRIB = 0.80*1.9(M_REV_MINOR 19000/10000)
              #           + 0.10*1.0(M_AUM_MINOR 10000/10000)
              #           + 0.10*1.9(M_CUST_GAIN 190/100) = 1.52+0.10+0.19 = 1.81
              #   EFFIC 1.63 / EXPER 1.18 / COST 1.00 / SUST 1.90 / PROC 1.45
              #   composite = 0.30*1.81 + 0.21*1.63 + 0.21*1.18 + 0.14*1.00
              #             + 0.07*1.90 + 0.07*1.45
              #           = 0.543 + 0.3423 + 0.2478 + 0.14 + 0.133 + 0.1015
              #           = 1.5076（q12 = 1.507600，与 ADR §11 的 1.507600000000
              #             精确相等，尾 6 位为零）   （[L1342] Step5；旧记 1.5346
              #             起算于 0.30*1.9，差 0.30*0.09 = 0.027）
              {'extreme_attainment': '除 M_AUM_MINOR 外：+1 指标 1.900000、'
                                     '-1 指标 1.000000（实际值 = target）；'
                                     'M_AUM_MINOR 恒 10000 = target（[L1460] 零变异构造，'
                                     '不得改）-> 达成率 1.000000',
               'dim_CONTRIB': '1.810000',
               'composite_absolute': '1.507600',
               'arithmetic': 'CONTRIB = 0.80*1.9 + 0.10*1.0 + 0.10*1.9 = 1.81；'
                             'composite = 0.30*1.81 + 0.21*1.63 + 0.21*1.18 + 0.14*1.00'
                             ' + 0.07*1.90 + 0.07*1.45 = 1.5076（q12 精确，尾 6 位为零）',
               'precision_note': '两个 hand 值都是精确有理数，6 位小数即 q12 全值；'
                                 '本文件不连写 12 位小数，因 tests/test_fixtures.py:408 '
                                 '的 PII 正则会把 12 位连写数字判成身份证号（该测试非本包写集）',
               'periods': '仅评价期 ' + E},
              'SPEC+HAND_COMPUTED'),
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
              'missing_rule 四种分支各有一个真实缺格', g09_subject,
              # [L1134] 四条 missing_rule 在 metric_dict 全表 15 行里的**实测计数**
              # （ZERO 6 / SKIP 4 / IMPUTE_MEDIAN 3 / BLOCK 2）。probe 的 n 语义是
              # 「匹配行数下限」，故下界取实测计数即最强且不越界。旧版四条一律 n=1：
              # A1CPREP 的「BLOCK 只剩 1 个」漏数 M_CONTACT_FREQ_PER_30D 与
              # M_RETENTION_RATE，这两条在 A1c(6299245) 之前就已错（ORCH-40 第9条 ③）。
              [_p('metric_dict', {'missing_rule': r}, n=g09_census[r]) for r in G09_RULES] +
              # 更精确的匹配条件：把每个分支的载体 metric_id 与规则名一起钉死，
              # 使「四种分支各有一个真实缺格」[L1411] 可被 probe 直接证伪。
              [_p('metric_dict', {'metric_id': g09_carriers[r][2], 'missing_rule': r})
               for r in G09_RULES] +
              [_p('metric_fact', {'strategy_id': g09_carriers[r][0],
                                  'version_id': g09_carriers[r][1], 'period': E,
                                  'metric_id': g09_carriers[r][2]}, none=True)
               for r in G09_RULES],
              {'ZERO': '按 0 计入', 'SKIP': '剔除并重归一', 'IMPUTE_MEDIAN': '中位数填补',
               'BLOCK': g09_carriers['BLOCK'][0] + ' 不产出分数',
               'four_branches_distinct': True},
              {'branch_map': g09_branch_map,
               'missing_rule_census': g09_census_text},
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
              {'c_share_base': '3/9 = 0.333333',
               'c_share_variant': '5/9 = 0.555556',
               # G14FIX(42d5346) 已把判据改成「分子 = C 类占比」（[L1416] verbatim
               # 「构造一级库中 C 类占比上升的场景」），分母依 [L1004]「NOT_ASSESSED
               # 单独计数，不计入分母」与 share_* 同源剔 NOT_ASSESSED -> 已参评 9。
               # 旧记 4/12、6/12 是 A1 期口径（分母取评价期事实 pair 12），A1c 补
               # alt_method_note 后证据结构由 B0D5 变 B3D2、NOT_ASSESSED 由 5 变 2，
               # 该口径已过期。ORCH-37 第3条：双口径禁混用 ——
               #   主体级证据结构 A3 B3 C4 D2 = 12（评价期事实 pair）
               #   行级           A3 B4 C4 D2 = 13（design_card 全表，含 S-005/v1）
               #   池/占比级      A3 B3 C3 D2 = 11（S-008 因 BLOCK 不产出分数，不入池）
               #   NOT_ASSESSED = 2（S-010 卡缺失、S-012 C 类未写 interpretation_limit）
               #   -> 已参评 = 11 - 2 = 9
               # 变体把 S-005/v2 与 S-007 由 B 降 C（变体卡已写 interpretation_limit，
               # 故不再被 [L977] 第⑤步降 D）-> C = 5，B = 1，已参评仍 9 -> 5/9 触发
               # MIX_QUALITY_DEGRADED。手算见 dsm_stage/E2b/probe_hand_e2b_p2.py（零
               # dsm import，按 [L977] 五步短路独立重算）。
               'share_numerator': '一级库 C 类条数：基线 3（S-003 / S-006 / S-011）-> '
                                  '变体 5（再加 S-005/v2、S-007）',
               'share_denominator': '已参评 9 = 池级 11（A3 B3 C3 D2）剔 NOT_ASSESSED 2',
               'share_precision': '判据量按 V-9 用 Decimal q12（1e-12）算：q12(3/9) 与 '
                                  'q12(5/9) 是纯循环小数，12 位展开在本文件一律不连写'
                                  '（tests/test_fixtures.py:408 的 PII 正则 \\d{12,} 会误判，'
                                  '该测试非本包写集）；精确值以分数 3/9、5/9 为准，'
                                  '6 位小数为 ROUND_HALF_UP 展示值'},
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
    cases = golden_cases(seed)
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
