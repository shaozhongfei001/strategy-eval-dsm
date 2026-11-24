'''tests/test_redline.py -- C4 守护测试：V-6 恒 forced_grade + G-03 红线旁路不进加权 + P-2 非补偿属性。

三条语义硬点对应的测试：
  1) G-03 旁路：红线指标整条移出加权线性和 -> 触发/未触发红线时综合分完全相同，
     差别只在等级被强制改写（test_g03_redline_bypass_keeps_the_score_identical）
  2) V-6 非补偿：除红线外一切完美（分数 0.99、证据 A 类、覆盖率 1）仍是 forced_grade
     （test_v6_adversarial_everything_else_perfect_still_forced），并用 hypothesis 表达
     P-2 属性：任意比较符/阈值/事实下 HARD 越界即恒 forced_grade
  3) HARD 与 SOFT 语义不同：SOFT 只单列扣减、绝不改级；HARD 恒不带扣减

输入一律按 R-2 用 dsm.models 的 pydantic 契约构造；期望值全部手算（R-14），
没有一条来自实现输出反填。业务数值（SOFT 扣减幅度、判定基准日 as_of）在契约里
没有载体，按 ADJ-2 做成必填入参，缺失即抛错而不是自定数。
'''
from __future__ import annotations

import datetime
from decimal import Decimal

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from dsm import grading, numeric, reason_codes
from dsm.models import (AttainmentFrame, EvidenceFrame, EvidenceRow,
                        GradeRuleRow, MetricDictRow, MetricFactRow, RedlineRow,
                        ScoreFrame, ScoreRow)
from dsm.redline import (RedlineInputError, RedlineSet, WaiverRow, WaiverSet,
                         bypassed_metric_ids, crosses, evaluate,
                         weighted_metric_ids)

D = numeric.D
RC = reason_codes.RC
AS_OF = datetime.date(2026, 1, 31)
SNAP = datetime.datetime(2026, 1, 31, 0, 0, 0)
SID, VER, PER = 'S1', 'V1', '2026-01'
HARD_M = 'CONTACT_FREQ_PER_30D'
SOFT_M = 'OPT_OUT_RATE'
PERF_M = 'ROI'
HARD_CODE = reason_codes.redline_hard(HARD_M)
SOFT_CODE = reason_codes.redline_soft(SOFT_M)
FLOOR = {'L1': '0.9', 'L2': '0.75', 'L3': '0.6', 'L4': '0.4'}


def fact(metric_id, value, flag='OK', sid=SID, ver=VER, period=PER):
    return MetricFactRow(strategy_id=sid, version_id=ver, period=period,
                         metric_id=metric_id, value_num=value, value=value,
                         data_quality_flag=flag, snapshot_time=SNAP,
                         data_as_of=AS_OF, source_table='t_fact',
                         caliber_version='CAL-1')


def redline(metric_id, level, comparator, threshold, code,
            waiver_allowed=True, forced='L4'):
    return RedlineRow(metric_id=metric_id, level=level, comparator=comparator,
                      threshold_value=threshold, forced_grade=forced,
                      reason_code=code, waiver_allowed=waiver_allowed)


def hard_row(comparator='GTE', threshold='0.05', waiver_allowed=True):
    return redline(HARD_M, 'HARD', comparator, D(threshold), HARD_CODE,
                   waiver_allowed=waiver_allowed)


def soft_row(metric_id=SOFT_M, comparator='GTE', threshold='0.10'):
    return redline(metric_id, 'SOFT', comparator, D(threshold),
                   reason_codes.redline_soft(metric_id))


def waiver(metric_id, sid=SID, ver=VER, approval='AP-2026-001',
           frm=datetime.date(2026, 1, 1), to=datetime.date(2026, 12, 31),
           scope='CONTACT_FREQ_PER_30D 单指标豁免'):
    return WaiverRow(metric_id=metric_id, strategy_id=sid, version_id=ver,
                     approval_id=approval, valid_from=frm, valid_to=to,
                     scope=scope)


def metric(metric_id, is_redline):
    return MetricDictRow(metric_id=metric_id, metric_name=metric_id,
                         dim_code='D1', numerator_def='numerator',
                         time_window='MONTHLY', dedup_rule='NONE',
                         missing_rule='SKIP', outlier_rule='CLIP_P1_P99',
                         attainment_formula='RATIO_DIRECT', direction=1,
                         unit='RATIO', target_value=D('1.0'),
                         target_basis='budget', is_redline=is_redline,
                         owner_name='owner', signoff_status='SIGNED',
                         dim_signoff_status='SIGNED', dict_version='MD-1',
                         caliber_version='CAL-1')


def run(facts, redlines, waivers=(), soft=None, metric_dict=None, as_of=AS_OF):
    return evaluate(tuple(facts), RedlineSet(rows=tuple(redlines)),
                    WaiverSet(rows=tuple(waivers)), as_of=as_of,
                    soft_deductions={} if soft is None else dict(soft),
                    metric_dict=None if metric_dict is None
                    else tuple(metric_dict))


def score_row(absolute, sid=SID):
    return ScoreRow(strategy_id=sid, version_id=VER, period=PER,
                    composite_absolute=D(absolute), composite_relative=D('0.5'),
                    dim_absolute={'D1': D(absolute)}, dim_relative={'D1': D('0.5')},
                    coverage=D('1'), weight_version_id='W2026A',
                    operator='LINEAR')


def evidence_row(cls='A', sid=SID):
    return EvidenceRow(strategy_id=sid, version_id=VER, evidence_class=cls,
                       evidence_reason='EVIDENCE_CARD_PARTIAL',
                       evidence_source='CARD_ONLY')


def rule_set():
    rows = tuple(GradeRuleRow(
        grade_code=g, grade_label=g + '级', attainment_floor=FLOOR[g],
        evidence_class_min='A', redline_pass_required=(g != 'L4'),
        promotion_streak=1, actions=('处置',), max_grade_if_no_target='L3')
        for g in ('L1', 'L2', 'L3', 'L4'))
    return grading.GradeRuleSet(
        rows=rows, min_coverage_for_absolute_track=D('0.6'),
        upgrade_consecutive_periods=1, demotion_immediate=True)


def grade_of(frame, absolute='0.99'):
    return grading.assign(ScoreFrame(rows=(score_row(absolute),)),
                          AttainmentFrame(rows=(),
                                          attainment_coverage={SID: D('1')}),
                          EvidenceFrame(rows=(evidence_row('A'),)),
                          frame, None, rule_set()).rows[0]


def composite(facts, metric_dict, weights):
    '''手算加权线性和：只用 weighted_metric_ids 给出的指标（红线整条旁路）。'''
    values = {f.metric_id: f.value for f in facts}
    pairs = sorted((weights[m], values[m])
                   for m in weighted_metric_ids(metric_dict) if m in values)
    return numeric.weighted_sum(pairs)


# ---------------------------------------------------------------------------
# V-6 恒 forced_grade（非补偿）
# ---------------------------------------------------------------------------
def test_v6_hard_crossing_forces_the_declared_grade():
    frame = run([fact(HARD_M, D('0.09'))], [hard_row()])
    row = frame.rows[0]
    assert (row.strategy_id, row.version_id, row.period, row.metric_id) == (
        SID, VER, PER, HARD_M)
    assert row.hit is True and row.level == 'HARD'
    assert row.comparator == 'GTE' and row.threshold_value == D('0.05')
    assert row.forced_grade == 'L4'          # 恒为 T5 行声明的 forced_grade
    assert row.reason_code == HARD_CODE      # 逐字用签认行上的注册码
    assert row.soft_deduction is None        # HARD 不得表现为扣分
    assert row.waiver_approval_id is None


def test_v6_adversarial_everything_else_perfect_still_forced():
    # 对抗性：非红线指标 0.99（过 L1 门槛 0.9）、证据 A 类、覆盖率 1、无上期状态。
    facts = [fact(HARD_M, D('0.09')), fact(PERF_M, D('0.99'))]
    forced = grade_of(run(facts, [hard_row()]))
    assert forced.grade == 'L4'
    assert RC.GR_REDLINE_FORCED in forced.grade_reason_path
    # 同一条事实把红线值改成不越界 -> 同样的 0.99 拿 L1，说明补偿通道不存在。
    clean = grade_of(run([fact(HARD_M, D('0.01')), fact(PERF_M, D('0.99'))],
                         [hard_row()]))
    assert clean.grade == 'L1'
    assert RC.GR_REDLINE_FORCED not in clean.grade_reason_path


def test_v6_no_other_input_can_move_the_forced_grade():
    terrible = run([fact(HARD_M, D('0.09')), fact(PERF_M, D('0.00'))],
                   [hard_row()]).rows[0]
    perfect = run([fact(HARD_M, D('0.09')), fact(PERF_M, D('1.00'))],
                  [hard_row()]).rows[0]
    assert (terrible.hit, terrible.forced_grade, terrible.reason_code) == (
        perfect.hit, perfect.forced_grade, perfect.reason_code) == (
        True, 'L4', HARD_CODE)


_DEC = st.decimals(min_value=Decimal('0'), max_value=Decimal('10'), places=4,
                   allow_nan=False, allow_infinity=False)


@settings(max_examples=25, deadline=None)
@given(comparator=st.sampled_from(('GT', 'GTE', 'LT', 'LTE')),
       int_mode=st.booleans(), a=st.integers(min_value=0, max_value=10000),
       b=st.integers(min_value=0, max_value=10000), c=_DEC, d=_DEC)
def test_p2_property_hard_crossing_always_forces_declared_grade(
        comparator, int_mode, a, b, c, d):
    '''P-2 属性：任意比较符 / 阈值 / 事实组合下，HARD 越界即恒 forced_grade，
    且恒不以扣分形式出现；未越界则既不 forced 也不留码（不静默、不编造）。'''
    if int_mode:
        value, threshold = a, b
    else:
        value, threshold = numeric.D(c), numeric.D(d)
        # 契约把整值 Decimal 事实收成 int 分（FactValue = MoneyMinor | Ratio），
        # 那会与 Decimal 阈值不可比，属性只覆盖比率轨。
        assume(value != value.to_integral_value())
    frame = run([fact(HARD_M, value)],
                [redline(HARD_M, 'HARD', comparator, threshold, HARD_CODE)])
    row = frame.rows[0]
    assert row.hit is crosses(comparator, value, threshold)
    assert row.soft_deduction is None            # HARD 永不是乘数或减分
    if row.hit:
        assert row.level == 'HARD'
        assert row.forced_grade == 'L4'
        assert row.reason_code == HARD_CODE      # 恒有码
    else:
        assert row.forced_grade is None and row.reason_code is None
    assert row.reason_code is None or reason_codes.is_registered(row.reason_code)


# ---------------------------------------------------------------------------
# G-03 红线不参与加权（旁路）
# ---------------------------------------------------------------------------
def test_g03_redline_bypass_keeps_the_score_identical():
    md = (metric(PERF_M, False), metric(HARD_M, True))
    assert weighted_metric_ids(md) == (PERF_M,)      # 红线整条移出加权
    assert bypassed_metric_ids(md) == (HARD_M,)
    weights = {PERF_M: D('1')}
    crossed = [fact(PERF_M, D('0.80')), fact(HARD_M, D('0.09'))]
    clean = [fact(PERF_M, D('0.80')), fact(HARD_M, D('0.01'))]
    # 手算：0.80 x 1 = 0.800000000000，两种情况完全相同（红线不进线性和）
    assert composite(crossed, md, weights) == D('0.8')
    assert composite(clean, md, weights) == D('0.8')
    assert composite(crossed, md, weights) == composite(clean, md, weights)
    hit, miss = run(crossed, [hard_row()]).rows[0], run(clean, [hard_row()]).rows[0]
    assert (hit.hit, hit.forced_grade) == (True, 'L4')
    assert (miss.hit, miss.forced_grade) == (False, None)
    # 分数相同、只有等级被强制改写
    assert grade_of(run(crossed, [hard_row()]), absolute='0.80').grade == 'L4'
    assert grade_of(run(clean, [hard_row()]), absolute='0.80').grade == 'L2'


def test_g03_hard_row_has_no_weight_or_deduction_hook():
    from dsm.models import RedlineEvalRow
    names = tuple(RedlineEvalRow.model_fields)
    assert not any('weight' in n or 'multiplier' in n or 'penalty' in n
                   for n in names)
    row = run([fact(HARD_M, D('0.09'))],
              [hard_row()], soft={HARD_M: D('0.05')}).rows[0]
    assert row.soft_deduction is None     # HARD 命中也不得变成扣分
    assert row.forced_grade == 'L4'


def test_g03_soft_crossing_deducts_alone_and_never_forces():
    frame = run([fact(SOFT_M, D('0.20'))], [soft_row()],
                soft={SOFT_M: D('0.05')})
    row = frame.rows[0]
    assert row.hit is True and row.level == 'SOFT'
    assert row.forced_grade is None            # SOFT 不改级
    assert row.soft_deduction == D('0.05')     # 单列，在等级判定之外
    assert row.reason_code == SOFT_CODE


def test_g03_metric_dict_flag_and_t5_row_must_agree():
    # 字典说不是红线，T5 却挂了红线行 -> 红线会漏进加权，属配置错误信号 [L992]
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09'))], [hard_row()],
            metric_dict=(metric(HARD_M, False),))
    # 字典说是红线，T5 没有阈值行 -> 阈值缺失，不得默认未触发（V-14）
    with pytest.raises(RedlineInputError):
        run([fact(SOFT_M, D('0.20'))], [hard_row()],
            metric_dict=(metric(SOFT_M, True), metric(HARD_M, True)))


def test_g03_soft_deduction_magnitude_is_required_not_invented():
    with pytest.raises(RedlineInputError):
        run([fact(SOFT_M, D('0.20'))], [soft_row()], soft={})
    with pytest.raises(RedlineInputError):
        run([fact(SOFT_M, D('0.20'))], [soft_row()], soft={SOFT_M: D('1.5')})


def test_hard_and_soft_stay_distinguishable_through_grading():
    facts = [fact(HARD_M, D('0.09')), fact(PERF_M, D('0.99'))]
    ded = {HARD_M: D('0.05')}
    hard_frame = run(facts, [redline(HARD_M, 'HARD', 'GTE', D('0.05'),
                                     HARD_CODE)], soft=ded)
    soft_frame = run(facts, [redline(HARD_M, 'SOFT', 'GTE', D('0.05'),
                                     reason_codes.redline_soft(HARD_M))],
                     soft=ded)
    h, s = hard_frame.rows[0], soft_frame.rows[0]
    assert (h.forced_grade, h.soft_deduction) == ('L4', None)
    assert (s.forced_grade, s.soft_deduction) == (None, D('0.05'))
    assert grade_of(hard_frame).grade == 'L4'
    assert grade_of(soft_frame).grade == 'L1'


@pytest.mark.parametrize('level', ('HARD', 'SOFT'))
def test_uncrossed_rows_carry_no_code_and_no_forcing(level):
    code = (reason_codes.redline_hard(HARD_M) if level == 'HARD'
            else reason_codes.redline_soft(HARD_M))
    frame = run([fact(HARD_M, D('0.01'))],
                [redline(HARD_M, level, 'GTE', D('0.05'), code)],
                soft={HARD_M: D('0.05')})
    row = frame.rows[0]
    assert (row.hit, row.forced_grade, row.soft_deduction) == (False, None, None)
    assert row.reason_code is None          # 干净的通过不需要码，也不编造
    assert row.waiver_approval_id is None


# ---------------------------------------------------------------------------
# 豁免路径：显式、可审计，不得静默不触发
# ---------------------------------------------------------------------------
def test_valid_waiver_leaves_trail_and_lifts_the_veto():
    row = run([fact(HARD_M, D('0.09'))], [hard_row()],
              waivers=[waiver(HARD_M)]).rows[0]
    assert row.hit is False and row.forced_grade is None
    assert row.waiver_approval_id == 'AP-2026-001'
    assert row.waiver_valid_from == datetime.date(2026, 1, 1)
    assert row.waiver_valid_to == datetime.date(2026, 12, 31)
    assert row.waiver_scope == 'CONTACT_FREQ_PER_30D 单指标豁免'
    assert row.reason_code == HARD_CODE      # 留痕：码 + 豁免依据都在行上
    assert grade_of(run([fact(HARD_M, D('0.09')), fact(PERF_M, D('0.99'))],
                        [hard_row()], waivers=[waiver(HARD_M)])).grade == 'L1'


def test_expired_waiver_is_refused_and_still_traced():
    row = run([fact(HARD_M, D('0.09'))], [hard_row()],
              waivers=[waiver(HARD_M)],
              as_of=datetime.date(2027, 1, 1)).rows[0]
    assert row.hit is True and row.forced_grade == 'L4'
    assert row.reason_code == RC.WAIVER_EXPIRED
    assert row.waiver_approval_id == 'AP-2026-001'   # 被拒的豁免同样留痕
    assert row.waiver_valid_to == datetime.date(2026, 12, 31)


def test_waiver_without_approval_id_is_refused():
    row = run([fact(HARD_M, D('0.09'))], [hard_row()],
              waivers=[waiver(HARD_M, approval=None)]).rows[0]
    assert row.hit is True and row.forced_grade == 'L4'
    assert row.reason_code == RC.WAIVER_INVALID
    assert row.waiver_approval_id is None


def test_waiver_not_yet_effective_is_refused():
    row = run([fact(HARD_M, D('0.09'))], [hard_row()],
              waivers=[waiver(HARD_M)],
              as_of=datetime.date(2025, 12, 31)).rows[0]
    assert row.hit is True and row.forced_grade == 'L4'
    assert row.reason_code == RC.WAIVER_INVALID
    assert row.waiver_valid_from == datetime.date(2026, 1, 1)


def test_waiver_on_a_non_waivable_redline_is_refused():
    row = run([fact(HARD_M, D('0.09'))],
              [hard_row(waiver_allowed=False)],
              waivers=[waiver(HARD_M)]).rows[0]
    assert row.hit is True and row.forced_grade == 'L4'
    assert row.reason_code == RC.WAIVER_INVALID
    assert row.waiver_approval_id == 'AP-2026-001'


# ---------------------------------------------------------------------------
# V-14 无静默降级
# ---------------------------------------------------------------------------
def test_v14_missing_fact_for_a_redline_raises():
    with pytest.raises(RedlineInputError):
        run([fact(PERF_M, D('0.99'))], [hard_row()])


def test_v14_suspect_fact_raises_instead_of_passing():
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09'), flag='SUSPECT')], [hard_row()])


def test_v14_threshold_unit_type_mismatch_raises():
    # 阈值是 int 精确量（分/计数），事实是 Decimal 比率 -> 不可比，不得默认未触发
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09'))],
            [redline(HARD_M, 'HARD', 'GTE', 5, HARD_CODE)])
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, 9)], [hard_row()])


def test_v14_duplicate_fact_and_duplicate_waiver_raise():
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09')), fact(HARD_M, D('0.02'))], [hard_row()])
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09'))], [hard_row()],
            waivers=[waiver(HARD_M), waiver(HARD_M, approval='AP-2026-002')])
    with pytest.raises(RedlineInputError):
        run([fact(HARD_M, D('0.09'))], [hard_row()],
            waivers=[waiver(SOFT_M)])
