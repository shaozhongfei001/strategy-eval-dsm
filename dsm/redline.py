'''dsm.redline -- Step 4 红线非补偿旁路否决（SDD 2.3.3 / 3.6.2，digest M04）。

四条语义，由 G-03 / P-2 / V-6 守护：

1. 旁路（不进加权）。红线指标整条移出加权体系（D2 约束①）：weighted_metric_ids()
   只返回 is_redline=False 的指标，红线既不进熵权组合，也不进加权线性和，更不以
   乘数或减分的形式出现。RedlineEvalRow 上唯一带数量的列是 soft_deduction，它按
   [L990] "在等级判定之外单列"，只有 SOFT 行会填；HARD 行恒为 None。所以同一策略
   在触发红线与未触发红线两种情况下综合分完全相同，差别只在等级被强制改写。

2. 非补偿（恒 forced_grade）。HARD 命中且无有效豁免 -> forced_grade 恒取 T5 行
   [L1182] 签认的那一级；综合分照算并披露但不生效（[L481] / [L989]）。本模块的
   入参里没有分数、证据、稳定性或三角验证，结构上不存在补偿通道。产出侧只打
   forced_grade 标记，消费侧由 grading.py 覆盖等级并落 RC.GR_REDLINE_FORCED。

3. HARD 与 SOFT 语义不同。HARD 旁路否决等级、恒不扣分；SOFT 只单列扣减、恒不改级
   （forced_grade 保持 None）。扣减幅度是治理值（[L484] 说由 grade_rules.yaml 配，
   但 GradeRuleRow 没有这一列），按 ADJ-2 做成必填入参 soft_deductions，缺失即抛错，
   绝不自定数（H-5）。

4. 豁免显式可审计。豁免生效时行上仍留 reason_code（签认行 [L1183] 的码）加
   approval_id / 有效期 / 范围四元组，不表现为静默不触发；豁免被拒时四元组照样
   留在行上，reason_code 按 WAIVER_EXPIRED > WAIVER_INVALID > 命中码 的优先序落码
   （[L991] / [L993]）。被拒的豁免不生效，等级照旧被强制。

比较符语义：RedlineRow.comparator 描述**越界（命中）条件**而不是安全条件，即
hit 当且仅当 value <comparator> threshold_value，取事实行的 value 列（[L1150]）。
金额与计数走 int 精确比较，比率走 Decimal 且边界用 numeric.eq_tol（1e-12，V-9）；
两侧类型不一致即不可比，直接抛错。

V-14 无静默降级：红线指标缺事实行、事实被标 SUSPECT、事实重复、阈值与事实单位
类型不符、字典 is_redline 与 T5 行不一致、SOFT 扣减幅度缺失、豁免重复或挂在没有
红线行的指标上 -> 一律抛 RedlineInputError，绝不默认"未触发"。

契约缺口（本模块不改契约，按 ADJ-4 本地声明）：
  * 豁免审批留痕在 8 张输入表内没有载体（A1 已登记），approval_id 只存在于输出侧
    RedlineEvalRow -> WaiverRow / WaiverSet / RedlineSet 在此本地声明。
  * 判定基准日不能取 datetime.now()（H-8）-> as_of 必填入参。
'''
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.models import (MetricDictRow, MetricFactRow, RedlineEvalRow,
                        RedlineFrame, RedlineRow)
from dsm.reason_codes import RC

COMPARATOR_SET = ('GT', 'GTE', 'LT', 'LTE')
_WAIVER_OK = 'OK'


class RedlineInputError(ValueError):
    '''红线判定的输入不成立：缺事实、单位不可比、豁免歧义、扣减幅度缺失。

    每一种都对应 V-14 禁止的静默降级路径，所以这里一律显式失败，而不是把红线
    判成"未触发"。
    '''


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class WaiverRow(_Frozen):
    '''一条豁免记录（[L991]：approval_id + 有效期 + 豁免范围）。

    契约层没有这张输入表（A1 缺口），按 ADJ-4 本地声明。approval_id 允许为 None，
    因为"没有审批留痕"本身就是 WAIVER_INVALID 的判据，不能在构造阶段就拒绝掉，
    否则被拒的豁免就不留痕了。定位键是 (metric_id, strategy_id, version_id)：
    豁免必须显式挂到一条策略的一个版本上，不支持通配，这样才审得出来。
    '''

    metric_id: str
    strategy_id: str
    version_id: str
    approval_id: str | None = None
    valid_from: date
    valid_to: date
    scope: str

    @model_validator(mode='after')
    def _window_not_reversed(self):
        if self.valid_to < self.valid_from:
            raise ValueError('豁免有效期倒挂: ' + self.metric_id)
        return self


class WaiverSet(_Frozen):
    '''豁免集合。空集合是合法状态：没有豁免时命中即生效。'''

    rows: tuple[WaiverRow, ...] = ()


class RedlineSet(_Frozen):
    '''T5 红线行集合（签认过的阈值定义），grain 是 metric。'''

    rows: tuple[RedlineRow, ...] = ()


# ---------------------------------------------------------------------------
# 旁路：红线整条移出加权体系（D2 约束①）
# ---------------------------------------------------------------------------
def weighted_metric_ids(metric_dict: Iterable[MetricDictRow]) -> tuple[str, ...]:
    '''允许进加权（熵权组合 + 加权线性和）的指标清单，红线整条排除。

    调用方必须把熵权与 aggregate 的输入裁剪到这个清单上：风险 / 合规 / 体验类
    指标常年低变异，参与数据驱动赋权会被系统性压低权重（[L488] F1），所以它们
    改走本模块的硬阈值旁路，而不是在加权里拿一个下限。
    '''
    return tuple(sorted(r.metric_id for r in metric_dict if not r.is_redline))


def bypassed_metric_ids(metric_dict: Iterable[MetricDictRow]) -> tuple[str, ...]:
    '''被旁路（不参与任何加权）的红线指标清单，用于披露与配置对账。'''
    return tuple(sorted(r.metric_id for r in metric_dict if r.is_redline))


# ---------------------------------------------------------------------------
# 越界判定
# ---------------------------------------------------------------------------
def crosses(comparator: str, value, threshold) -> bool:
    '''事实值是否越界（命中）。comparator 描述命中条件，不是安全条件。

    int（金额分 / 计数）走精确比较；Decimal（比率）走 numeric.eq_tol 的 1e-12
    容差，边界值按 comparator 的闭 / 开语义归属（V-9）。两侧类型不一致说明阈值
    与事实的单位口径不匹配，属配置错误：抛错，不默认未触发（V-14）。
    '''
    if comparator not in COMPARATOR_SET:
        raise RedlineInputError('未知比较符: ' + str(comparator))
    if isinstance(value, bool) or isinstance(threshold, bool):
        raise RedlineInputError('红线比较不接受 bool')
    both_int = isinstance(value, int) and isinstance(threshold, int)
    both_ratio = isinstance(value, Decimal) and isinstance(threshold, Decimal)
    if not (both_int or both_ratio):
        raise RedlineInputError(
            '红线阈值与事实值不可比（int 精确量 vs Decimal 比率）: threshold='
            + repr(threshold) + ' value=' + repr(value))
    if both_int:
        v, t = int(value), int(threshold)
        if comparator == 'GT':
            return v > t
        if comparator == 'GTE':
            return v >= t
        if comparator == 'LT':
            return v < t
        return v <= t
    v, t = numeric.D(value), numeric.D(threshold)
    same = numeric.eq_tol(v, t)
    if comparator == 'GT':
        return v > t and not same
    if comparator == 'GTE':
        return v > t or same
    if comparator == 'LT':
        return v < t and not same
    return v < t or same


# ---------------------------------------------------------------------------
# 索引与配置对账
# ---------------------------------------------------------------------------
def _index_redlines(redlines: RedlineSet) -> dict:
    index = {}
    for row in redlines.rows:
        if row.metric_id in index:
            raise RedlineInputError('T5 同一指标出现多行红线: ' + row.metric_id)
        index[row.metric_id] = row
    return index


def _index_waivers(waivers: WaiverSet) -> dict:
    index = {}
    for row in waivers.rows:
        key = (row.metric_id, row.strategy_id, row.version_id)
        if key in index:
            raise RedlineInputError(
                '同一 (指标, 策略, 版本) 出现多条豁免，无法判断哪条生效: '
                + ' / '.join(key))
        index[key] = row
    return index


def _index_facts(facts: Sequence[MetricFactRow]) -> dict:
    index = {}
    for row in facts:
        key = (row.strategy_id, row.version_id, row.period, row.metric_id)
        if key in index:
            raise RedlineInputError('T3 同一事实键出现多行: ' + ' / '.join(key))
        index[key] = row
    return index


def _check_bypass(metric_dict, redline_index: Mapping) -> None:
    '''字典的 is_redline 与 T5 的红线行必须一一对应。

    两个方向都是配置错误：T5 有行而字典 is_redline=False，说明这条红线还会留在
    加权体系里（[L992] whatif 中 redline_delta 非空即配置错误信号）；字典说红线
    而 T5 没有阈值行，说明阈值缺失 —— 按 V-14 抛错，不默认未触发。
    '''
    if metric_dict is None:
        return
    flags = {row.metric_id: row.is_redline for row in metric_dict}
    for metric_id in sorted(redline_index):
        if metric_id not in flags:
            raise RedlineInputError('红线指标不在指标字典里: ' + metric_id)
        if not flags[metric_id]:
            raise RedlineInputError(
                'T5 声明了红线但字典 is_redline=False，该指标仍会进加权'
                '（[L992] 配置错误信号）: ' + metric_id)
    for metric_id in sorted(flags):
        if flags[metric_id] and metric_id not in redline_index:
            raise RedlineInputError(
                '字典 is_redline=True 但 T5 没有阈值行，阈值缺失不得默认未触发'
                '（V-14）: ' + metric_id)


def _waiver_verdict(rl: RedlineRow, waiver, as_of: date):
    '''None = 没提交豁免；_WAIVER_OK = 豁免有效；否则是被拒的注册码。

    被拒的三种情形：红线本身不允许豁免（[L1184]）、没有审批留痕或没有豁免范围
    （[L991]）-> WAIVER_INVALID；已过有效期 -> WAIVER_EXPIRED；尚未生效 -> 视同
    无效（[L991] 的"过期或范围不符 -> 视为无豁免"）。
    '''
    if waiver is None:
        return None
    if not rl.waiver_allowed:
        return RC.WAIVER_INVALID
    if waiver.approval_id is None or not waiver.approval_id.strip():
        return RC.WAIVER_INVALID
    if not waiver.scope.strip():
        return RC.WAIVER_INVALID
    if as_of > waiver.valid_to:
        return RC.WAIVER_EXPIRED
    if as_of < waiver.valid_from:
        return RC.WAIVER_INVALID
    return _WAIVER_OK


def _deduction(metric_id: str, soft_deductions: Mapping) -> Decimal:
    '''SOFT 扣减幅度（[L484] / [L990]）。治理值，必填入参，缺失即抛错（ADJ-2）。'''
    if metric_id not in soft_deductions:
        raise RedlineInputError(
            'SOFT 红线扣减幅度缺失，且契约里没有载体（[L484] 说由 grade_rules.yaml '
            '配置）；不自定数（ADJ-2 / H-5）: ' + metric_id)
    value = numeric.q12(numeric.D(soft_deductions[metric_id]))
    if value < numeric.ZERO or value > numeric.ONE:
        raise RedlineInputError(
            'SOFT 扣减幅度必须在 0..1 之间: ' + metric_id + ' = ' + str(value))
    return value


def _row(locator, rl: RedlineRow, fact_row: MetricFactRow, waiver, verdict,
         soft_deductions: Mapping) -> RedlineEvalRow:
    '''一条 (策略 x 版本 x 期 x 红线指标) 的判定结果。

    hit 的含义是"本期这条否决生效"（[L989] 命中且无有效豁免），所以有效豁免下
    hit=False，但 reason_code 与豁免四元组照样留在行上 —— 豁免必须留痕，不得
    表现为静默不触发。HARD 行恒不填 soft_deduction（红线不是扣分），SOFT 行恒
    不填 forced_grade（SOFT 不改级）。
    '''
    crossed = crosses(rl.comparator, fact_row.value, rl.threshold_value)
    hard = rl.level == 'HARD'
    waived = verdict == _WAIVER_OK
    if not crossed:
        reason = None
    elif verdict is None or waived:
        reason = rl.reason_code          # [L1183] 签认行上的注册码，逐字透传
    else:
        reason = verdict                 # WAIVER_EXPIRED / WAIVER_INVALID 优先
    deduction = None
    if crossed and not hard and not waived:
        deduction = _deduction(rl.metric_id, soft_deductions)
    return RedlineEvalRow(
        strategy_id=locator[0], version_id=locator[1], period=locator[2],
        metric_id=rl.metric_id, level=rl.level, comparator=rl.comparator,
        threshold_value=rl.threshold_value,
        hit=crossed and not waived,
        forced_grade=(rl.forced_grade if (crossed and hard and not waived)
                      else None),
        waiver_approval_id=None if waiver is None else waiver.approval_id,
        waiver_valid_from=None if waiver is None else waiver.valid_from,
        waiver_valid_to=None if waiver is None else waiver.valid_to,
        waiver_scope=None if waiver is None else waiver.scope,
        soft_deduction=deduction, reason_code=reason)


def evaluate(facts: Sequence[MetricFactRow],
             redlines: RedlineSet,
             waivers: WaiverSet,
             *,
             as_of: date,
             soft_deductions: Mapping[str, Decimal],
             metric_dict: Sequence[MetricDictRow] | None = None
             ) -> RedlineFrame:
    '''Step 4 红线判定（[L988] 签名 + 三个必填治理入参）。

    返回 RedlineFrame，每个 (策略 x 版本 x 期) 对每条红线出一行。本函数不读任何
    分数 / 证据 / 稳定性 / 三角验证输入，所以红线判定与业绩完全解耦（P0-2 非补偿，
    [L992] 红线判定与权重完全无关）。

    as_of 是豁免有效期的判定基准日，必须由调用方给（H-8：本模块不取当前时间）；
    soft_deductions 是 metric_id -> 扣减比率；metric_dict 给定时顺带做 is_redline
    与 T5 的一致性对账。
    '''
    if not isinstance(redlines, RedlineSet):
        raise RedlineInputError('redlines 必须是 RedlineSet')
    if not isinstance(waivers, WaiverSet):
        raise RedlineInputError('waivers 必须是 WaiverSet')
    if not isinstance(as_of, date):
        raise RedlineInputError('as_of 必须是 date（H-8：不许取当前时间）')
    if not isinstance(soft_deductions, Mapping):
        raise RedlineInputError('soft_deductions 必须是 metric_id -> 比率 的映射')
    redline_index = _index_redlines(redlines)
    _check_bypass(metric_dict, redline_index)
    waiver_index = _index_waivers(waivers)
    for key in sorted(waiver_index):
        if key[0] not in redline_index:
            raise RedlineInputError('豁免挂在没有红线行的指标上: ' + key[0])
    fact_index = _index_facts(facts)
    locators = sorted({(r.strategy_id, r.version_id, r.period) for r in facts})
    rows = []
    for locator in locators:
        for metric_id in sorted(redline_index):
            key = locator + (metric_id,)
            fact_row = fact_index.get(key)
            if fact_row is None:
                raise RedlineInputError(
                    '红线指标缺事实行，不得默认未触发（V-14）: ' + ' / '.join(key))
            if fact_row.data_quality_flag == 'SUSPECT':
                raise RedlineInputError(
                    '红线事实被标 SUSPECT：剔除等于静默放过一条红线（V-14），'
                    '上游必须先修数或改判: ' + ' / '.join(key))
            waiver = waiver_index.get(
                (metric_id, locator[0], locator[1]))
            verdict = _waiver_verdict(redline_index[metric_id], waiver, as_of)
            rows.append(_row(locator, redline_index[metric_id], fact_row,
                             waiver, verdict, soft_deductions))
    return RedlineFrame(rows=tuple(rows))


def hard_vetoes(frame: RedlineFrame) -> tuple[RedlineEvalRow, ...]:
    '''本期真正生效的 HARD 否决行（消费侧只读便利，不改任何语义）。'''
    return tuple(r for r in frame.rows if r.level == 'HARD' and r.hit)
