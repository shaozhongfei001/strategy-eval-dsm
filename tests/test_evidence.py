'''tests/test_evidence.py -- C3 守护测试：G-02（证据门禁侧）+ G-13（卡 PARTIAL 上限）。

四条硬点各有专属测试：
  1) 五步**按序短路**：用"读到后续步骤字段就抛错"的构造证明根本没走到（探针），
     再用行为面证明 ② 命中后 ⑤ 不会把 A 改写成 D。
  2) 默认 GATE_ONLY、**不乘入分数**：同一策略同一批事实，卡在 A 与 B 两种判定下，
     走 landed L3 aggregate.compose 出来的 ScoreFrame 必须逐字段完全相同；
     另外断言 EvidenceRow 只有 [L980] 的七列，结构上就没有可乘的数值列；
     DISCOUNT 未立 ADR 时直接拒绝而不是给一个乘数。
  3) A 类**保守**：关键词清单外 / 清单为空 / 卡非 COMPLETE / 对照非 RANDOMIZED
     一律不认 A，全部落到更低等级。
  4) CEL-0 消费：evidence_source 恒为 CARD_ONLY；cel 关闭时预留字段非空即抛
     CelDisabledDataPresentError（RK-15）；预留字段不改变判定（V-20 风味）。

全部输入按 R-2 用 dsm.models 的 pydantic 契约模型构造；关键词清单、门槛等治理值
一律作为入参传入，期望值全部由 [L977]-[L980] 的规则手算得到（R-14），
没有一条来自实现输出反填。
'''
from __future__ import annotations

from datetime import date, datetime

import pytest

from dsm import aggregate, evidence
from dsm.config import AppConfig
from dsm.models import (AttainmentFrame, AttainmentRow, DesignCardRow,
                        EvidenceRow, MetricFactRow, NormalizedFrame,
                        NormalizedRow, PoolKey, WeightVersionDoc)
from dsm.numeric import D
from dsm.reason_codes import RC

P = '2026Q1'
VER = 'v1'
LIMIT = '样本仅覆盖一线城市，外推需谨慎'
# 构造用的 [L979] 外置可审计关键词清单（测试夹具，不是业务签认值）
KEYWORDS = ('显著', 'p<0.05', '置信区间')


def card(sid='S1', version=VER, status='COMPLETE', method='OBSERVATIONAL_ONLY',
         control='NONE', criteria='提升信用卡动卡率', note=None, limit=LIMIT,
         **cel):
    return DesignCardRow(
        strategy_id=sid, version_id=version, direct_goal='提升信用卡动卡率',
        process_metrics=('M1',), result_metrics=('M2',),
        observation_window=P, data_source='数仓 dws 层', data_timeliness='T+1',
        eval_method=method, control_arrangement=control,
        success_criteria=criteria, risk_constraints='不超频触达',
        eval_owner='策略团队', alt_method_note=note, interpretation_limit=limit,
        card_status=status, **cel)


def fact(sid='S1', version=VER, metric='M1', period=P):
    return MetricFactRow(
        strategy_id=sid, version_id=version, period=period, metric_id=metric,
        value_num=D('0.42'), value=D('0.42'), data_quality_flag='OK',
        snapshot_time=datetime(2026, 4, 1, 8, 0), data_as_of=date(2026, 3, 31),
        source_table='dws_strategy_metric', caliber_version='CAL-2026A')


def params(mode='GATE_ONLY', cel_enabled=False, keywords=KEYWORDS):
    return evidence.EvidenceParams(
        evidence_mode=mode, cel_enabled=cel_enabled,
        significance_keywords=tuple(keywords))


def run(cards, facts=None, **kw):
    if facts is None:
        facts = (fact(),)
    return evidence.classify(tuple(cards), tuple(facts), params=params(**kw))


def one(frame):
    assert len(frame.rows) == 1
    return frame.rows[0]


class _Probe:
    '''按序记录被读到的字段；读到 later 里的字段即抛错，用来证明短路发生了。'''

    def __init__(self, wrapped, later):
        object.__setattr__(self, '_wrapped', wrapped)
        object.__setattr__(self, '_later', later)
        object.__setattr__(self, 'read', [])

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        self.read.append(name)
        if name in self._later:
            raise AssertionError('短路被破坏：判定读到了后续步骤的 ' + name)
        return getattr(self._wrapped, name)


# ---------------------------------------------------------------------------
# ① 设计卡缺失 -> D
# ---------------------------------------------------------------------------
def test_step1_missing_card_is_d():
    '''硬点 1 / ①：卡整行缺失（有事实无卡）与 card_status=MISSING 都判 D，
    reason 用注册码 EVIDENCE_CARD_MISSING（[L977] NOT_ASSESSED 的证据侧）。'''
    frame = run([card(sid='S2', status='MISSING', method='RCT',
                      control='RANDOMIZED', criteria='差异显著')],
                (fact(sid='S1'), fact(sid='S2')))
    assert tuple((r.strategy_id, r.evidence_class) for r in frame.rows) == (
        ('S1', 'D'), ('S2', 'D'))
    assert {r.evidence_reason for r in frame.rows} == {RC.EVIDENCE_CARD_MISSING}
    assert frame.rows[0].interpretation_limit is None
    assert frame.rows[1].interpretation_limit == LIMIT


# ---------------------------------------------------------------------------
# ② randomized + 对照组 + 事前成功判定（含显著性口径）-> A
# ---------------------------------------------------------------------------
def test_step2_randomized_with_significance_is_a():
    '''R-4 happy path：四要件齐全 -> A。'''
    row = one(run([card(method='AB_TEST', control='RANDOMIZED',
                        criteria='动卡率提升 5 个百分点，双尾 p<0.05 显著')]))
    assert row.evidence_class == 'A'
    assert row.evidence_reason == RC.EV_A_RANDOMIZED
    assert row.evidence_source == 'CARD_ONLY'
    assert row.interpretation_limit == LIMIT
    # v1 没有对照组 ID 的输入来源（T4 无此列），恒为 None，已上报缺口
    assert row.control_group_id is None


def test_a_verdict_is_not_rewritten_by_step5():
    '''硬点 1 的行为面：② 命中即返回，⑤ 只对 C 生效，所以 A 即使没写
    interpretation_limit 也不会被降为 D。'''
    row = one(run([card(method='RCT', control='RANDOMIZED',
                        criteria='差异显著', limit=None)]))
    assert row.evidence_class == 'A'
    assert row.evidence_reason == RC.EV_A_RANDOMIZED
    assert row.interpretation_limit is None


def test_short_circuit_stops_at_the_first_deciding_step():
    '''硬点 1 的机械证明：探针在后续步骤要读的字段上一律抛错。
    ① 命中时只允许读到 card_status；② 命中时不允许读到 ③⑤ 的字段。'''
    step1 = _Probe(card(status='MISSING'),
                   ('control_arrangement', 'eval_method', 'success_criteria',
                    'alt_method_note', 'interpretation_limit'))
    assert evidence._verdict(step1, KEYWORDS) == ('D', RC.EVIDENCE_CARD_MISSING)
    assert set(step1.read) == {'card_status'}

    step2 = _Probe(card(method='RCT', control='RANDOMIZED',
                        criteria='差异显著', note='平行趋势假设已检验'),
                   ('alt_method_note', 'interpretation_limit'))
    assert evidence._verdict(step2, KEYWORDS) == ('A', RC.EV_A_RANDOMIZED)
    assert set(step2.read) == {'card_status', 'control_arrangement',
                               'eval_method', 'success_criteria'}


# ---------------------------------------------------------------------------
# ③ 准实验（须写方法名与假设）-> B
# ---------------------------------------------------------------------------
def test_step3_quasi_with_method_and_assumption_is_b():
    for method in ('DID', 'SYNTHETIC_CONTROL', 'PSM'):
        row = one(run([card(method=method, control='CONCURRENT_CONTROL',
                            note='平行趋势假设已检验', criteria='动卡率提升')]))
        assert (row.evidence_class, row.evidence_reason) == ('B', RC.EV_B_QUASI)


def test_step3_quasi_without_the_assumption_note_falls_to_c():
    '''硬点 3：③ 要求"须写方法名与假设"，没写假设就保守落到 ④ 的 C。'''
    for note in (None, '   '):
        row = one(run([card(method='SYNTHETIC_CONTROL',
                            control='CONCURRENT_CONTROL', note=note)]))
        assert (row.evidence_class, row.evidence_reason) == (
            'C', RC.EV_C_OBSERVATIONAL)


# ---------------------------------------------------------------------------
# ④ 仅观测 -> C ；⑤ C 类未写 interpretation_limit -> 降为 D
# ---------------------------------------------------------------------------
def test_step4_observational_only_is_c():
    row = one(run([card()]))
    assert (row.evidence_class, row.evidence_reason) == (
        'C', RC.EV_C_OBSERVATIONAL)
    assert row.interpretation_limit == LIMIT


def test_step5_c_without_interpretation_limit_is_d():
    '''G-02：C 类必须写 interpretation_limit，未写即降为 D（BLOCK 码），
    不出分的后果由下游 grading 承接，本模块只负责降级与披露。'''
    for limit in (None, '   '):
        row = one(run([card(limit=limit)]))
        assert (row.evidence_class, row.evidence_reason) == (
            'D', RC.EVIDENCE_C_NO_LIMIT)
        assert row.interpretation_limit == limit


# ---------------------------------------------------------------------------
# A 类保守性（[L979] / RK-4）
# ---------------------------------------------------------------------------
def test_a_is_refused_outside_the_keyword_list():
    '''硬点 3：自由文本"看起来像显著"但清单外 -> 不认 A，禁止模型猜测。'''
    row = one(run([card(method='AB_TEST', control='RANDOMIZED',
                        criteria='效果明显提升，样本量充足，业务方已认可')]))
    assert row.evidence_class == 'C'
    hit = one(run([card(method='AB_TEST', control='RANDOMIZED',
                        criteria='动卡率提升且差异显著')]))
    assert hit.evidence_class == 'A'


def test_a_is_refused_when_the_keyword_list_is_empty():
    '''硬点 3：清单为空 = 没有任何可审计的显著性口径 -> 永不认 A。'''
    row = one(run([card(method='RCT', control='RANDOMIZED',
                        criteria='p<0.05 显著，已给置信区间')], keywords=()))
    assert row.evidence_class == 'C'
    assert row.evidence_reason == RC.EV_C_OBSERVATIONAL


def test_a_requires_a_randomized_control_arrangement():
    '''硬点 3：randomized=true 在契约里由 control_arrangement 承载，
    其余三种对照安排一律不认 A（保守降级到 C）。'''
    for control in ('NONE', 'HISTORICAL_BASELINE', 'CONCURRENT_CONTROL'):
        row = one(run([card(method='RCT', control=control,
                            criteria='差异显著')]))
        assert row.evidence_class == 'C'


def test_partial_card_caps_at_c():
    '''G-13：卡 PARTIAL 时上限压至 C，randomized + 显著性口径齐全也不给 A，
    准实验也不给 B；reason 用注册码 EVIDENCE_CARD_PARTIAL。'''
    top = one(run([card(status='PARTIAL', method='RCT', control='RANDOMIZED',
                        criteria='差异显著')]))
    assert (top.evidence_class, top.evidence_reason) == (
        'C', RC.EVIDENCE_CARD_PARTIAL)
    quasi = one(run([card(status='PARTIAL', method='DID',
                          control='CONCURRENT_CONTROL',
                          note='平行趋势假设已检验')]))
    assert (quasi.evidence_class, quasi.evidence_reason) == (
        'C', RC.EVIDENCE_CARD_PARTIAL)


def test_partial_card_without_limit_is_still_d():
    '''⑤ 对任何 C 都生效：PARTIAL 压到 C 之后仍要检查 interpretation_limit。'''
    row = one(run([card(status='PARTIAL', limit=None)]))
    assert (row.evidence_class, row.evidence_reason) == (
        'D', RC.EVIDENCE_C_NO_LIMIT)


# ---------------------------------------------------------------------------
# CEL-0 消费（[L1894]-[L1898]）
# ---------------------------------------------------------------------------
def test_evidence_source_is_card_only_for_every_verdict():
    '''硬点 4：四个等级的行一次跑齐，evidence_source 首版恒为 CARD_ONLY。'''
    cards = (
        card(sid='SA', method='RCT', control='RANDOMIZED', criteria='差异显著'),
        card(sid='SB', method='DID', control='CONCURRENT_CONTROL',
             note='平行趋势假设已检验', criteria='动卡率提升'),
        card(sid='SC', method='OBSERVATIONAL_ONLY', criteria='动卡率提升'),
        card(sid='SD', method='OBSERVATIONAL_ONLY', criteria='动卡率提升',
             limit=None),
        card(sid='SE', status='MISSING'),
    )
    facts = tuple(fact(sid=s) for s in ('SA', 'SB', 'SC', 'SD', 'SE'))
    frame = run(cards, facts)
    assert tuple(r.evidence_class for r in frame.rows) == (
        'A', 'B', 'C', 'D', 'D')
    assert {r.evidence_source for r in frame.rows} == {'CARD_ONLY'}
    assert tuple(r.evidence_reason for r in frame.rows) == (
        RC.EV_A_RANDOMIZED, RC.EV_B_QUASI, RC.EV_C_OBSERVATIONAL,
        RC.EVIDENCE_C_NO_LIMIT, RC.EVIDENCE_CARD_MISSING)


def test_cel_disabled_with_reserved_data_present_raises():
    '''硬点 4 / RK-15：cel.enabled=false 时预留字段非空必须抛错，不静默忽略；
    mde_ok=False 也是"非空"。'''
    with pytest.raises(evidence.CelDisabledDataPresentError):
        run([card(method='DID', note='平行趋势假设已检验', experiment_id='E1')])
    with pytest.raises(evidence.CelDisabledDataPresentError):
        run([card(mde_ok=False)])


def test_cel_reserved_fields_never_change_the_verdict():
    '''硬点 4 / V-20 风味：字段全空 + cel 关闭 == 无预留时的行为；
    cel 开启时首版也没有 CEL 计算，填满预留字段判定与 reason 完全不变，
    evidence_source 仍是 CARD_ONLY（CEL_ESTIMATED 只能由二期桥接产出）。'''
    plain = one(run([card(method='RCT', control='RANDOMIZED',
                          criteria='差异显著')]))
    filled = one(run([card(method='RCT', control='RANDOMIZED',
                           criteria='差异显著', incremental_value=D('1200'),
                           incremental_ci_lower=D('900'),
                           incremental_ci_upper=D('1500'),
                           estimator_method='AB', experiment_id='E1',
                           holdout_id='H1', mde_ok=True)], cel_enabled=True))
    assert plain.evidence_class == filled.evidence_class == 'A'
    assert plain.evidence_reason == filled.evidence_reason
    assert filled.evidence_source == 'CARD_ONLY'
    assert filled.control_group_id is None


# ---------------------------------------------------------------------------
# 默认 GATE_ONLY：证据等级不乘入分数（本包最核心的语义）
# ---------------------------------------------------------------------------
def weights():
    return WeightVersionDoc(
        weight_version_id='W2026A', status='FROZEN',
        effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
        level1_weights={'D1': D(1)}, level2_weights={'D1': {'M1': D(1)}},
        approved_by='评价管理委员会', approved_date=date(2026, 1, 1))


def attain():
    return AttainmentFrame(rows=(AttainmentRow(
        strategy_id='S1', version_id=VER, period=P, metric_id='M1',
        attainment=D('0.8'), direction=1, has_target=True, capped_flag=False,
        target_source='年度计划'),), attainment_coverage={'S1': D(1)})


def norm(evidence_class):
    return NormalizedFrame(rows=(NormalizedRow(
        strategy_id='S1', version_id=VER, period=P, metric_id='M1',
        pool_key=PoolKey(biz_domain='零售', evidence_class=evidence_class),
        norm_value=D('0.7'), method='min_max', anchor_used=False),))


def test_gate_only_evidence_class_never_enters_the_score():
    '''硬点 2 / G-02：同一策略、同一批事实，只在设计卡上分别拿到 A 与 B，
    走 landed L3 aggregate.compose 出来的分数必须**完全相同**（手算：单维度
    单指标、权重全为 1、LINEAR，绝对轨 = 达成率 0.8，相对轨 = 0.7）。
    另外断言 EvidenceRow 只有 [L980] 的七列，结构上不存在可乘的数值列。'''
    facts = (fact(),)
    ev_a = run([card(method='RCT', control='RANDOMIZED',
                     criteria='差异显著')], facts)
    ev_b = run([card(method='DID', control='CONCURRENT_CONTROL',
                     note='平行趋势假设已检验',
                     criteria='动卡率提升')], facts)
    assert ev_a.rows[0].evidence_class == 'A'
    assert ev_b.rows[0].evidence_class == 'B'

    score_a = aggregate.compose(attain(), norm(ev_a.rows[0].evidence_class),
                               weights())
    score_b = aggregate.compose(attain(), norm(ev_b.rows[0].evidence_class),
                               weights())
    assert score_a == score_b
    assert score_a.rows[0].composite_absolute == D('0.8')
    assert score_a.rows[0].composite_relative == D('0.7')
    assert set(EvidenceRow.model_fields) == {
        'strategy_id', 'version_id', 'evidence_class', 'evidence_reason',
        'evidence_source', 'control_group_id', 'interpretation_limit'}


def test_evidence_mode_defaults_to_gate_only_and_discount_is_refused():
    '''硬点 2：GATE_ONLY 是配置层的默认（H-5，本模块不给默认值）；
    DISCOUNT 只保留接口，未立 ADR 时直接拒绝，绝不返回一个乘数。'''
    cfg = AppConfig(
        eval_config={'evidence': {'mode': 'GATE_ONLY',
                                  'significance_keywords': ['显著', 'p<0.05']},
                     'cel': {'enabled': False}},
        weights={}, redlines={}, grade_rules={}, anchor_set={}, ahp_matrices={})
    resolved = evidence.params_from_config(cfg)
    assert resolved.evidence_mode == 'GATE_ONLY'
    assert resolved.cel_enabled is False
    assert resolved.significance_keywords == ('显著', 'p<0.05')
    assert evidence.classify((card(),), (fact(),), cfg).rows[0].evidence_class == 'C'

    empty = AppConfig(eval_config={}, weights={}, redlines={}, grade_rules={},
                      anchor_set={}, ahp_matrices={})
    with pytest.raises(evidence.EvidenceConfigError):
        evidence.params_from_config(empty)
    with pytest.raises(evidence.EvidenceDiscountError):
        run([card()], mode='DISCOUNT')
    with pytest.raises(evidence.EvidenceError):
        evidence.classify((card(),), (fact(),), cfg, params=params())
