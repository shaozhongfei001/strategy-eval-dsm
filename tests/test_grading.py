'''tests/test_grading.py -- B3 守护测试：G-04（目标缺失封顶）+ G-08（版本断点）。

三条语义硬点各有专属测试：
  1) 等级只看绝对轨（相对轨不参与判定）
  2) 滞回升降不对称（同一分数在升/降两个方向得到不同等级）
  3) 版本断点（不跨版本比较，promotion_streak 计数重置）

全部输入按 R-2 用 dsm.models 的 pydantic 契约模型构造；attainment_floor /
min_coverage 等治理值取自构造出来的 grade_rules 行与 GradeRuleSet 入参，
期望值全部由门槛手算得到（R-14），没有一条来自实现输出反填。
'''
from __future__ import annotations

import pytest

from dsm import grading
from dsm.models import (AttainmentFrame, EvidenceFrame, EvidenceRow, GradeFrame,
                        GradeRow, GradeRuleRow, RedlineEvalRow, RedlineFrame,
                        ScoreFrame, ScoreRow)
from dsm.reason_codes import RC

P0 = '2025Q4'
P1 = '2026Q1'
VER = 'v1'
WV = 'W2026A'

# 构造用的 T7 grade_rules 门槛（测试夹具，不是业务签认值）
FLOOR = {'L1': '0.9', 'L2': '0.75', 'L3': '0.6', 'L4': '0.4'}
STREAK = {'L1': 2, 'L2': 2, 'L3': 1, 'L4': 1}
ACTIONS = {'L1': ('扩大投放',), 'L2': ('维持并复核',),
           'L3': ('限期整改',), 'L4': ('纳入淘汰评估',)}


def _rule(grade_code, floor):
    return GradeRuleRow(
        grade_code=grade_code, grade_label=grade_code + '级',
        attainment_floor=floor, evidence_class_min='A',
        redline_pass_required=(grade_code != 'L4'),
        promotion_streak=STREAK[grade_code], actions=ACTIONS[grade_code],
        max_grade_if_no_target='L3')


def rule_rows():
    return tuple(_rule(g, FLOOR[g]) for g in ('L1', 'L2', 'L3', 'L4'))


def rules(min_cov='0.6'):
    return grading.GradeRuleSet(
        rows=rule_rows(), min_coverage_for_absolute_track=min_cov,
        upgrade_consecutive_periods=2, demotion_immediate=True)


def score(sid, absolute, relative='0.5', version=VER, period=P1, wv=WV):
    return ScoreRow(
        strategy_id=sid, version_id=version, period=period,
        composite_absolute=absolute, composite_relative=relative,
        dim_absolute={'D1': '0' if absolute is None else absolute},
        dim_relative={'D1': relative}, coverage='1',
        weight_version_id=wv, operator='LINEAR')


def evidence(sid, cls, version=VER):
    return EvidenceRow(
        strategy_id=sid, version_id=version, evidence_class=cls,
        evidence_reason='EVIDENCE_CARD_PARTIAL', evidence_source='CARD_ONLY',
        interpretation_limit='样本外推有限' if cls == 'C' else None)


def redline(sid, hit=True, forced='L4', level='HARD', version=VER, period=P1):
    hard = level == 'HARD'
    return RedlineEvalRow(
        strategy_id=sid, version_id=version, period=period, metric_id='M1',
        level=level, comparator='LTE', threshold_value='0.05', hit=hit,
        forced_grade=forced if hard else None,
        soft_deduction=None if hard else '0.05')


def prev_grade(sid, grade, version=VER, period=P0):
    return GradeRow(strategy_id=sid, version_id=version, period=period,
                    grade=grade, grade_reason_path=(), capped=False,
                    usable_for_elimination=True)


def run(score_rows, ev_rows, coverage, rl_rows=(), prev_rows=None, r=None,
        streaks=None, prev_wv=None):
    return grading.plan(
        ScoreFrame(rows=tuple(score_rows)),
        AttainmentFrame(rows=(), attainment_coverage=dict(coverage)),
        EvidenceFrame(rows=tuple(ev_rows)),
        RedlineFrame(rows=tuple(rl_rows)),
        None if prev_rows is None else GradeFrame(rows=tuple(prev_rows)),
        rules() if r is None else r,
        streaks=streaks, prev_weight_version_id=prev_wv)


def key(sid, version=VER):
    return grading.streak_key(sid, version)


def streak(grade, count):
    return grading.StreakState(grade=grade, count=count)


# ---------------------------------------------------------------------------
# G-04 目标值缺失导致绝对轨覆盖不足 -> 封顶 max_grade_if_no_target
# ---------------------------------------------------------------------------
def test_g04_low_target_coverage_caps_grade_to_max_grade_if_no_target():
    # 手算：composite_absolute 0.95 过 L1 门槛 0.9；覆盖率 0.42 < 0.6 -> 封顶 L3
    row = run([score('S1', '0.95')], [evidence('S1', 'A')],
              {'S1': '0.42'}).frame.rows[0]
    assert row.grade == 'L3'
    assert row.capped is True
    assert row.cap_reason == RC.GR_CAPPED_NO_TARGET
    assert RC.GR_CAPPED_NO_TARGET in row.grade_reason_path
    assert row.usable_for_elimination is True
    assert row.action == ('限期整改',)


def test_g04_cap_does_not_bind_when_grade_already_worse():
    # 手算：0.5 只过 L4 门槛 0.4；封顶 L3 不生效 -> capped 保持 false
    row = run([score('S1', '0.5')], [evidence('S1', 'A')],
              {'S1': '0.42'}).frame.rows[0]
    assert row.grade == 'L4'
    assert row.capped is False
    assert row.cap_reason is None
    assert RC.GR_CAPPED_NO_TARGET not in row.grade_reason_path


# ---------------------------------------------------------------------------
# 硬点 1：等级只看绝对轨
# ---------------------------------------------------------------------------
def test_grade_reads_absolute_track_only():
    plan = run([score('S1', '0.95', relative='0.99'),
                score('S2', '0.95', relative='0.01')],
               [evidence('S1', 'A'), evidence('S2', 'A')],
               {'S1': '1', 'S2': '1'})
    first, second = plan.frame.rows
    assert first.grade == 'L1'
    assert second.grade == 'L1'
    assert tuple(first.grade_reason_path) == tuple(second.grade_reason_path)


def test_null_absolute_composite_is_not_assessed_even_with_top_relative():
    row = run([score('S1', None, relative='0.99')], [evidence('S1', 'A')],
              {'S1': '1'}).frame.rows[0]
    assert row.grade == 'NOT_ASSESSED'
    assert row.grade_reason_path == (RC.NOT_ASSESSED,)
    assert row.usable_for_elimination is False
    assert row.capped is False
    assert row.cap_reason is None
    assert row.action is None


# ---------------------------------------------------------------------------
# 硬点 2：滞回（升降不对称）
# ---------------------------------------------------------------------------
def test_same_score_is_held_on_upgrade_but_demotes_immediately():
    # 同一个 composite_absolute 0.80（瞬时等级 L2），只看方向不同
    up = run([score('S1', '0.80')], [evidence('S1', 'A')], {'S1': '1'},
             prev_rows=[prev_grade('S1', 'L3')]).frame.rows[0]
    down = run([score('S1', '0.80')], [evidence('S1', 'A')], {'S1': '1'},
               prev_rows=[prev_grade('S1', 'L1')]).frame.rows[0]
    assert up.grade == 'L3'          # 升级需连续 2 期达标，本期是第 1 期 -> 保持
    assert RC.GR_STREAK_NOT_MET in up.grade_reason_path
    assert down.grade == 'L2'        # demotion_immediate = true -> 单期即降
    assert RC.GR_STREAK_NOT_MET not in down.grade_reason_path
    assert up.grade != down.grade


def test_upgrade_is_granted_on_the_second_consecutive_period():
    plan = run([score('S1', '0.80')], [evidence('S1', 'A')], {'S1': '1'},
               prev_rows=[prev_grade('S1', 'L3')],
               streaks={key('S1'): streak('L2', 1)})
    row = plan.frame.rows[0]
    assert row.grade == 'L2'
    assert RC.GR_STREAK_NOT_MET not in row.grade_reason_path
    assert plan.streaks[key('S1')].count == 2


def test_first_period_has_no_baseline_and_holds_nothing():
    plan = run([score('S1', '0.80')], [evidence('S1', 'A')], {'S1': '1'})
    row = plan.frame.rows[0]
    assert row.grade == 'L2'
    assert RC.FIRST_PERIOD in row.grade_reason_path
    assert plan.streaks[key('S1')].count == 1


# ---------------------------------------------------------------------------
# 硬点 3 / G-08：版本断点
# ---------------------------------------------------------------------------
def test_g08_version_break_suppresses_cross_version_compare_and_resets_streak():
    plan = run([score('S1', '0.80', version='v2')],
               [evidence('S1', 'A', version='v2')], {'S1': '1'},
               prev_rows=[prev_grade('S1', 'L3', version='v1')],
               streaks={key('S1', 'v1'): streak('L2', 1)})
    row = plan.frame.rows[0]
    assert RC.GR_VERSION_BREAK in row.grade_reason_path
    assert RC.GR_STREAK_NOT_MET not in row.grade_reason_path
    assert RC.FIRST_PERIOD not in row.grade_reason_path
    assert row.grade == 'L2'                     # 不按上期 v1 的 L3 做跨版本保持
    assert plan.streaks[key('S1', 'v2')].count == 1   # 计数重置后本期为第 1 期
    assert key('S1', 'v1') not in plan.streaks


def test_weight_version_change_is_also_a_break():
    plan = run([score('S1', '0.80')], [evidence('S1', 'A')], {'S1': '1'},
               prev_rows=[prev_grade('S1', 'L3')],
               streaks={key('S1'): streak('L2', 1)}, prev_wv='W2025B')
    row = plan.frame.rows[0]
    assert RC.GR_VERSION_BREAK in row.grade_reason_path
    assert plan.streaks[key('S1')].count == 1    # 权重版本切换处不累计
    assert row.grade == 'L2'


# ---------------------------------------------------------------------------
# Step 2 证据封顶 / Step 4 红线覆盖
# ---------------------------------------------------------------------------
def test_evidence_class_c_caps_the_grade_at_l2():
    row = run([score('S1', '0.95')], [evidence('S1', 'C')],
              {'S1': '1'}).frame.rows[0]
    assert row.grade == 'L2'
    assert row.capped is True
    assert row.cap_reason == RC.GR_EVIDENCE_GATE_L1


def test_evidence_class_d_is_not_assessed():
    row = run([score('S1', '0.95')], [evidence('S1', 'D')],
              {'S1': '1'}).frame.rows[0]
    assert row.grade == 'NOT_ASSESSED'
    assert row.grade_reason_path == (RC.NOT_ASSESSED,)
    assert row.usable_for_elimination is False


def test_hard_redline_forces_the_grade_in_a_single_period():
    plan = run([score('S1', '0.95')], [evidence('S1', 'A')], {'S1': '1'},
               rl_rows=[redline('S1', hit=True, forced='L4')],
               prev_rows=[prev_grade('S1', 'L1')],
               streaks={key('S1'): streak('L1', 5)})
    row = plan.frame.rows[0]
    assert row.grade == 'L4'                     # 红线单期即降，不受滞回保护
    assert RC.GR_REDLINE_FORCED in row.grade_reason_path
    assert row.capped is True
    assert row.cap_reason == RC.GR_REDLINE_FORCED


# ---------------------------------------------------------------------------
# R-4 冒烟：happy path + 负向
# ---------------------------------------------------------------------------
def test_happy_path_clean_run_keeps_grade_action_and_streak():
    plan = run([score('S1', '0.95')], [evidence('S1', 'A')], {'S1': '1'},
               rl_rows=[redline('S1', hit=False),
                        redline('S1', level='SOFT', hit=True)],
               prev_rows=[prev_grade('S1', 'L1')],
               streaks={key('S1'): streak('L1', 3)})
    row = plan.frame.rows[0]
    assert row.grade == 'L1'
    assert row.grade_reason_path == ()
    assert row.capped is False
    assert row.cap_reason is None
    assert row.action == ('扩大投放',)
    assert row.usable_for_elimination is True
    assert plan.streaks[key('S1')].count == 4
    assert grading.assign(
        ScoreFrame(rows=(score('S1', '0.95'),)),
        AttainmentFrame(rows=(), attainment_coverage={'S1': '1'}),
        EvidenceFrame(rows=(evidence('S1', 'A'),)), RedlineFrame(rows=()),
        None, rules()).rows[0].grade == 'L1'


def test_non_monotone_attainment_floors_are_rejected():
    bad = grading.GradeRuleSet(
        rows=(_rule('L1', '0.5'), _rule('L2', '0.6'), _rule('L3', '0.4'),
              _rule('L4', '0.3')),
        min_coverage_for_absolute_track='0.6')
    with pytest.raises(grading.GradeRuleError):
        run([score('S1', '0.95')], [evidence('S1', 'A')], {'S1': '1'}, r=bad)


def test_missing_evidence_row_is_rejected():
    with pytest.raises(grading.GradingInputError):
        run([score('S1', '0.95')], [], {'S1': '1'})
