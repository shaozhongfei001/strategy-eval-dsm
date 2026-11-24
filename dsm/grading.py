'''dsm.grading -- Step 6: 四级分级六步 + 滞回 + 版本断点 (SDD 2.3.4 / 3.5.4).

六步（digest M05 逐条对应）：

    Step 1  门槛映射：composite_absolute 对 grade_rules 的 attainment_floor
            取能达到的最好等级（L1 > L2 > L3 > L4 严格单调，[L879]）
    Step 2  证据封顶：evidence_class = C -> 最高二级；D -> NOT_ASSESSED
    Step 3  目标缺失封顶：绝对轨覆盖率低于 min_coverage_for_absolute_track
            -> 封到 max_grade_if_no_target，capped + cap_reason
    Step 4  红线覆盖：HARD 命中 -> forced_grade（非补偿，综合分不生效）
    Step 5  滞回：升级需连续 upgrade_consecutive_periods 期达标；
            demotion_immediate = true 时降级即时；红线单期即降
    Step 6  版本断点：version_id（或权重版本）变化 -> GR_VERSION_BREAK，
            滞回计数重置，且不做跨版本趋势比较（上期等级不作为保持基线）

三条关键约束：

  * 等级判定只看绝对轨（[L968]）。本模块从不读 ScoreRow.composite_relative，
    也不读 NormalizedFrame；composite_absolute 为 null 时直接 NOT_ASSESSED，
    相对轨再高也救不回来（P-1 / G-01 的行为面）。
  * 滞回是不对称的：升级要连续期数，降级即时（RK-7 的治理时效答复）。
  * 版本断点前后各自独立判定，promotion_streak 计数在断点处重置（G-08）。

契约缺口（不改 models.py / config.py，R-1、R-15）：

  * digest 签名里的 GradeRuleSet 在 dsm.models 中不存在（只有 T7 行模型
    GradeRuleRow），故在本模块内声明为 frozen pydantic 模型：rows + 两个
    [L965] 滞回参数 + K-06 的 min_coverage_for_absolute_track。
  * min_coverage_for_absolute_track（K-06）是 PLACEHOLDER 治理值，本模块不给
    默认、不猜数；upgrade_consecutive_periods = 2 与 demotion_immediate = true
    取 digest [L965] 明文默认值。
  * 连续达标期数在 GradeRow 上没有列，故由 plan() 以 StreakState 映射显式
    交回调用方（主流程按期串起来），assign() 保持 digest 签名只回 GradeFrame。
  * usable_for_elimination 只反映本模块可见的否决（NOT_ASSESSED）；flip_rate
    超 review_max 与方法分歧的否决属 sensitivity（[L1019]），不在本签名内。
  * 低于全部 attainment_floor 的归属 SDD 未规定，此处兜底取最差等级 L4
    （NOT_ASSESSED 的语义是"不可评价、不出分"，不是"表现差"）。

数值口径（V-9）：门槛与覆盖率比较全部走 dsm.numeric（Decimal + 1e-12 容差），
本模块不自写一套等值/比较逻辑。
'''
from __future__ import annotations

from typing import Mapping

from pydantic import BaseModel, ConfigDict

from dsm import numeric
from dsm.models import (AttainmentFrame, EvidenceFrame, FrameGrade, GradeFrame,
                        GradeRow, GradeRuleRow, Ratio, RedlineFrame, ScoreFrame,
                        StrictBool, StrictInt)
from dsm.reason_codes import RC

GRADE_ORDER = ('L1', 'L2', 'L3', 'L4')
NOT_ASSESSED = 'NOT_ASSESSED'
# Step 2 的封顶目标：C 类证据最高二级（[L494]）。
EVIDENCE_C_CAP = 'L2'
EVIDENCE_BLOCK_CLASS = 'D'
# [L965] 明文默认值：升级需连续 2 期，降级即时。
DEFAULT_UPGRADE_CONSECUTIVE_PERIODS = 2
DEFAULT_DEMOTION_IMMEDIATE = True
KEY_SEP = '|'
# 等级优劣序：数字越小越好，NOT_ASSESSED 排在四级之外。
_LEVEL = {'L1': 0, 'L2': 1, 'L3': 2, 'L4': 3, NOT_ASSESSED: 4}


class GradingError(ValueError):
    '''Base class for every grading contract violation.'''


class GradeRuleError(GradingError):
    '''grade_rules 表本身不成立（缺等级、门槛非严格单调、覆盖率越界）。'''


class GradingInputError(GradingError):
    '''上游 Frame 形状不成立（缺 evidence 行、缺覆盖率、HARD 命中无 forced_grade）。'''


class GradeRuleSet(BaseModel):
    '''Step 1-5 需要的全部治理值。models.py 只有 GradeRuleRow，没有这个集合体。

    min_coverage_for_absolute_track 是 K-06，属 PLACEHOLDER 治理参数，因此必填
    且无默认（H-5：不猜业务数）。upgrade_consecutive_periods / demotion_immediate
    取 [L965] 的明文默认；每级的 promotion_streak 来自 T7 行，优先于全局默认。
    '''

    model_config = ConfigDict(frozen=True, extra='forbid')

    rows: tuple[GradeRuleRow, ...]
    min_coverage_for_absolute_track: Ratio
    upgrade_consecutive_periods: StrictInt = DEFAULT_UPGRADE_CONSECUTIVE_PERIODS
    demotion_immediate: StrictBool = DEFAULT_DEMOTION_IMMEDIATE


class StreakState(BaseModel):
    '''一个 (strategy_id, version_id) 的连续达标计数，跨期由调用方串起来。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    grade: FrameGrade
    count: StrictInt


class GradePlan(BaseModel):
    '''assign() 的结果 + 需要带到下一期的滞回状态。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    frame: GradeFrame
    streaks: dict[str, StreakState]


def streak_key(strategy_id, version_id) -> str:
    '''滞回状态的键。version_id 进键，所以策略换版本天然是一份新状态。'''
    return str(strategy_id) + KEY_SEP + str(version_id)


def _better(a, b) -> bool:
    return _LEVEL[a] < _LEVEL[b]


def _worse(a, b) -> bool:
    return _LEVEL[a] > _LEVEL[b]


def _below(value, floor) -> bool:
    '''严格小于，1e-12 容差内的相等不算小于（V-9）。'''
    return value < floor and not numeric.eq_tol(value, floor)


def _locator(row):
    '''[L1149] 定位三元组，也是唯一的输出行序（不依赖 dict 迭代序）。'''
    return (row.strategy_id, row.version_id, row.period)


def _rule_index(rules: GradeRuleSet) -> dict:
    '''校验并索引 grade_rules：四级各一行，attainment_floor 严格单调递减。'''
    index = {}
    for row in rules.rows:
        if row.grade_code in index:
            raise GradeRuleError('grade_rules 出现重复等级行: ' + row.grade_code)
        index[row.grade_code] = row
    missing = tuple(g for g in GRADE_ORDER if g not in index)
    if missing:
        raise GradeRuleError('grade_rules 缺少等级行: ' + ', '.join(missing))
    for good, worse in zip(GRADE_ORDER, GRADE_ORDER[1:]):
        a = index[good].attainment_floor
        b = index[worse].attainment_floor
        if not (a > b) or numeric.eq_tol(a, b):
            raise GradeRuleError(
                'attainment_floor 必须严格单调 L1>L2>L3>L4，'
                + good + '=' + str(a) + ' 与 ' + worse + '=' + str(b) + ' 冲突')
    cov = rules.min_coverage_for_absolute_track
    if cov < numeric.ZERO or cov > numeric.ONE:
        raise GradeRuleError(
            'min_coverage_for_absolute_track 必须落在 [0,1]: ' + str(cov))
    return index


def _base_grade(value, index: Mapping) -> str:
    '''Step 1：取能达到的最好等级；一个门槛都不过时兜底为最差等级。'''
    for grade in GRADE_ORDER:
        floor = index[grade].attainment_floor
        if value > floor or numeric.eq_tol(value, floor):
            return grade
    return GRADE_ORDER[-1]


def _evidence_index(ev: EvidenceFrame) -> dict:
    index = {}
    for row in ev.rows:
        key = (row.strategy_id, row.version_id)
        if key in index:
            raise GradingInputError(
                'evidence 对同一 (strategy_id, version_id) 出现多行: '
                + key[0] + KEY_SEP + key[1])
        index[key] = row
    return index


def _redline_index(rl: RedlineFrame) -> dict:
    index = {}
    for row in rl.rows:
        index.setdefault(_locator(row), []).append(row)
    return {k: tuple(v) for k, v in index.items()}


def _prev_index(prev: GradeFrame | None) -> dict:
    if prev is None:
        return {}
    index = {}
    for row in prev.rows:
        index.setdefault(row.strategy_id, []).append(row)
    return {k: tuple(sorted(v, key=_locator)) for k, v in index.items()}


def _required_streak(row: GradeRuleRow, rules: GradeRuleSet) -> int:
    '''升入该等级需要的连续达标期数：T7 行的 promotion_streak 优先（[L1204]），
    行上未给正数时回落到 [L965] 的全局 upgrade_consecutive_periods。'''
    n = row.promotion_streak
    return n if n >= 1 else rules.upgrade_consecutive_periods


def _consecutive(prior: StreakState | None, instant: str) -> int:
    '''含本期在内的连续达标期数：等级不同或无上期状态都从 1 重新数。'''
    if prior is None or prior.grade != instant:
        return 1
    return prior.count + 1


def _forced_grade(rows, index: Mapping):
    '''Step 4：返回 (forced_grade 或 None, 是否有 HARD 命中)。

    多个 HARD 命中取最严的 forced_grade；命中但整张表都没声明 forced_grade 时，
    退而用 [L1203] redline_pass_required 排除法取最好的一级"不要求红线通过"等级，
    四级全都要求时属配置缺口，直接报错而不是悄悄放过一次硬红线（P0-2 非补偿）。
    '''
    hits = tuple(r for r in rows if r.level == 'HARD' and r.hit)
    if not hits:
        return None, False
    declared = tuple(r.forced_grade for r in hits if r.forced_grade is not None)
    if declared:
        return max(declared, key=lambda g: _LEVEL[g]), True
    open_grades = tuple(g for g in GRADE_ORDER
                        if not index[g].redline_pass_required)
    if not open_grades:
        raise GradingInputError(
            'HARD 红线命中但未声明 forced_grade，且四级全部要求红线通过')
    return open_grades[0], True


def plan(scores: ScoreFrame,
         attain: AttainmentFrame,
         ev: EvidenceFrame,
         rl: RedlineFrame,
         prev: GradeFrame | None,
         rules: GradeRuleSet,
         *,
         streaks: Mapping[str, StreakState] | None = None,
         prev_weight_version_id: str | None = None) -> GradePlan:
    '''六步分级 + 需要带到下一期的滞回状态。行序按 [L1149] 定位三元组。'''
    if not isinstance(scores, ScoreFrame):
        raise GradingInputError('scores 必须是 ScoreFrame')
    if not isinstance(attain, AttainmentFrame):
        raise GradingInputError('attain 必须是 AttainmentFrame')
    if not isinstance(ev, EvidenceFrame):
        raise GradingInputError('ev 必须是 EvidenceFrame')
    if not isinstance(rl, RedlineFrame):
        raise GradingInputError('rl 必须是 RedlineFrame')
    if prev is not None and not isinstance(prev, GradeFrame):
        raise GradingInputError('prev 必须是 GradeFrame 或 None')
    if not isinstance(rules, GradeRuleSet):
        raise GradingInputError('rules 必须是 GradeRuleSet')

    index = _rule_index(rules)
    evidence = _evidence_index(ev)
    redlines = _redline_index(rl)
    previous = _prev_index(prev)
    coverage = attain.attainment_coverage
    carried = dict(streaks) if streaks else {}

    rows_out = []
    streaks_out = {}
    for score in sorted(scores.rows, key=_locator):
        sid = score.strategy_id
        ver = score.version_id
        period = score.period
        key = streak_key(sid, ver)
        prior = carried.get(key)
        if sid not in coverage:
            raise GradingInputError('attainment_coverage 缺少策略: ' + sid)
        ev_row = evidence.get((sid, ver))
        if ev_row is None:
            raise GradingInputError(
                'score 行没有对应的 evidence 行: ' + sid + KEY_SEP + ver)

        # ---- Step 6 的判定材料：版本断点与滞回基线（断点处两者都失效）----
        history = previous.get(sid, ())
        same_version = tuple(r for r in history if r.version_id == ver)
        version_break = bool(history) and not same_version
        if (prev_weight_version_id is not None
                and score.weight_version_id != prev_weight_version_id):
            version_break = True
        baseline = None
        if same_version and not version_break:
            last = same_version[-1].grade
            # 上期 NOT_ASSESSED 等于"无上期等级记录"，按首期处理（FIRST_PERIOD）
            baseline = None if last == NOT_ASSESSED else last

        path = []
        capped = False
        cap_reason = None

        # ---- Step 1 之前的短路：不出分的两种情形 ----
        if (score.composite_absolute is None
                or ev_row.evidence_class == EVIDENCE_BLOCK_CLASS):
            rows_out.append(GradeRow(
                strategy_id=sid, version_id=ver, period=period,
                grade=NOT_ASSESSED, grade_reason_path=(RC.NOT_ASSESSED,),
                capped=False, cap_reason=None, action=None,
                usable_for_elimination=False))
            # 不可评价的期不计入连续达标期数：不写 streaks_out，下一期从 1 重数
            continue

        # ---- Step 1 门槛挂达成率（只看绝对轨）----
        grade = _base_grade(score.composite_absolute, index)
        base = grade

        # ---- Step 2 证据封顶 ----
        if ev_row.evidence_class == 'C' and _better(grade, EVIDENCE_C_CAP):
            grade = EVIDENCE_C_CAP
            capped = True
            cap_reason = RC.GR_EVIDENCE_GATE_L1
            path.append(RC.GR_EVIDENCE_GATE_L1)

        # ---- Step 3 目标缺失封顶 ----
        if _below(coverage[sid], rules.min_coverage_for_absolute_track):
            ceiling = index[base].max_grade_if_no_target
            if _worse(ceiling, grade):
                grade = ceiling
                capped = True
                if cap_reason is None:
                    cap_reason = RC.GR_CAPPED_NO_TARGET
                path.append(RC.GR_CAPPED_NO_TARGET)

        # ---- Step 4 红线覆盖（非补偿，单期即降）----
        forced, hard_hit = _forced_grade(
            redlines.get((sid, ver, period), ()), index)
        if hard_hit:
            if _worse(forced, grade):
                capped = True
                cap_reason = RC.GR_REDLINE_FORCED
            grade = forced
            path.append(RC.GR_REDLINE_FORCED)

        # ---- Step 5 滞回：升级要连续期数，降级即时，红线不受保护 ----
        instant = grade
        final = instant
        if baseline is not None and not hard_hit:
            if _better(instant, baseline):
                need = _required_streak(index[instant], rules)
                if _consecutive(prior, instant) < need:
                    final = baseline
                    path.append(RC.GR_STREAK_NOT_MET)
            elif _worse(instant, baseline) and not rules.demotion_immediate:
                need = _required_streak(index[instant], rules)
                if _consecutive(prior, instant) < need:
                    final = baseline
                    path.append(RC.GR_STREAK_NOT_MET)

        # ---- Step 6 版本断点标注（断点处上面已经不做跨版本比较）----
        if version_break:
            path.append(RC.GR_VERSION_BREAK)
        elif not history:
            path.append(RC.FIRST_PERIOD)

        if version_break or prior is None or prior.grade != instant:
            count = 1
        else:
            count = prior.count + 1
        streaks_out[key] = StreakState(grade=instant, count=count)

        rows_out.append(GradeRow(
            strategy_id=sid, version_id=ver, period=period, grade=final,
            grade_reason_path=tuple(path), capped=capped, cap_reason=cap_reason,
            action=index[final].actions if final in index else None,
            usable_for_elimination=(final != NOT_ASSESSED)))

    return GradePlan(frame=GradeFrame(rows=tuple(rows_out)),
                     streaks=streaks_out)


def assign(scores: ScoreFrame,
           attain: AttainmentFrame,
           ev: EvidenceFrame,
           rl: RedlineFrame,
           prev: GradeFrame | None,
           rules: GradeRuleSet,
           *,
           streaks: Mapping[str, StreakState] | None = None,
           prev_weight_version_id: str | None = None) -> GradeFrame:
    '''digest [L962] 的签名：只回 GradeFrame。需要滞回状态时用 plan()。'''
    return plan(scores, attain, ev, rl, prev, rules, streaks=streaks,
                prev_weight_version_id=prev_weight_version_id).frame


