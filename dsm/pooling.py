'''dsm.pooling -- Step 7 分池禁混排 + 一级库门禁（C 类禁入）+ 占比双报。

守护编号：**G-02**（证据门禁侧：C/D 类永不进一级库，只能在自身池内排名）、
**P-6**（分池禁混排：pool_key = (biz_domain, evidence_class)，跨池只能并列报出，
永不合成单一序）、**G-14**（[L1854] 把 MIX_QUALITY_DEGRADED 判给 pooling，即
占比双报的防作弊面）。唯一事实来源 M24-pooling [L996]-[L1007]，旁证
M31 [L1404]、M26 [L1063]-[L1064]、M43 [L943]、M29 [L1346]。

本包裁决（digest 未定，按 [L1006] 的 B-020 授权定；每条都已写进缺口上报）：
  R1 pool_rank 只看**相对轨** composite_relative（[L945]：相对轨只喂排名，绝对轨
     只喂等级，P-1/G-01 的反面）；并列取**竞争名次** 1,2,2,4；等值判定走
     numeric.eq_tol（V-9：比率一律 Decimal + 1e-12，绝不用 float）。
  R2 占比双报的两个分母（B-020）：share_in_pool = 池计数 / **同 biz_domain 已参评
     数**（分池口径）；share_overall = 池计数 / **全体已参评数**（合并口径）。两个
     分母都按 [L1004] 剔除 NOT_ASSESSED；只给一套时另一套无法反推（见测试）。
  R3 evidence_structure 覆盖**全部策略**（含 D 类）：[L1003] 要的是结构披露，藏掉 D
     会低估不可评价占比；但 share_* 的分母只含已参评（[L1004] 不计入分母）。
  R4 reject_reason 单槽优先序（照 redline.py 的单槽办法，BLOCK 先于 WARN）：
     HARD 命中 > 不可评价（D 类用其自身 evidence_reason，其余用 NOT_ASSESSED）>
     PRIMARY_POOL_REJECTED_EVIDENCE > PRIMARY_POOL_REJECTED_ROBUST > None
     （只差 grade != L1 时落 None：[L1005] 没有对应注册码，见缺口 2）。
  R5 一级库准入是**举证制**：[L1002] 四条件必须全部正面成立才准入。第 4 条的载体
     （Step 8 的 SensitivityReport）在 [L1346]/[L1350] 的主流程里排在 Step 7 之后，
     首过必然缺；缺载体**不给准入**（V-14 禁兜底默认），落
     PRIMARY_POOL_REJECTED_ROBUST，待 Step 8 出结论后由主流程重跑本步。

契约缺口（R-1 / R-15：不改 models.py / config.py，逐条上报主控裁决）：
  1. [L1005] 要 POOL_TOO_SMALL，但 [L1006] 的 PoolFrame / PoolStats 没有任何 flags
     列可承载 -> 本包用 small_pools() 显式回吐给 reports / cli，绝不静默丢弃。
  2. [L1002] 四条件 vs [L1005] 两码：grade != L1 与 HARD 命中都没有专属注册码。
  3. [L1000] 签名里没有 FLIP_RATE_UNUSABLE 的载体 -> 加 keyword-only sensitivity。
  4. min_pool_size 的键位未签认：复用 [L943] 的 eval_config.normalize.min_pool_size，
     不为 pooling 另立第二个治理值（H-5）。
  5. MIX_QUALITY_DEGRADED 需要上期 PoolStats 作基线，签名里没有 -> 独立函数
     mix_quality_verdict()，基线缺失即抛（V-14）。

纯函数层：无时钟、无 I/O、无全局状态、无随机（H-8）；一切阈值只从入参或配置来。
'''
from __future__ import annotations

from typing import Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm import numeric
from dsm.config import AppConfig, is_placeholder_value
from dsm.models import (EvidenceFrame, GradeFrame, PoolFrame, PoolKey, PoolRow,
                        PoolStatRow, PoolStats, ScoreFrame, SensitivityReport,
                        StrategyMasterRow, StrictInt)
from dsm.reason_codes import RC

KEY_SEP = '|'

# eval_config 路径（缺口 4）：[L943] 只在 normalize 块下给了 min_pool_size，
# [L1005] 的 POOL_TOO_SMALL 用的是同一个池样本下限，故复用同一键位。
CFG_NORMALIZE_KEY = 'normalize'
CFG_MIN_POOL_SIZE_KEY = 'min_pool_size'

EVIDENCE_CLASSES = ('A', 'B', 'C', 'D')       # [L1003] 闭合四类
GATE_EVIDENCE_CLASSES = ('A', 'B')            # [L1002] 只有 A/B 有资格进一级库
LOW_EVIDENCE_CLASSES = ('C', 'D')             # [L1854] G-14 的"低证据等级"
GATE_GRADE = 'L1'                             # [L1002] grade = L1
NOT_ASSESSED = 'NOT_ASSESSED'                 # [L1004] 单独计数，不进任何分母
# grading Step 4 命中 HARD 时在 grade_reason_path 上留下的唯一痕迹（[L989] 非补偿）。
CODE_HARD_FORCED = RC.GR_REDLINE_FORCED.value
CODE_UNUSABLE = RC.FLIP_RATE_UNUSABLE.value


class PoolingError(ValueError):
    '''Base class for every pooling contract violation.'''


class PoolingConfigError(PoolingError):
    '''A governance value this module needs is absent from eval_config.'''


class PoolingInputError(PoolingError):
    '''四个上游载体无法无歧义连接，或本期不可比（V-14：显式抛，不兜底）。'''


class PoolingParams(BaseModel):
    '''唯一的治理入参：池样本下限。无默认值（H-5），也不接受占位值（K-01~K-20）。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    min_pool_size: StrictInt  # [L943] / [L1005] POOL_TOO_SMALL 的阈值

    @model_validator(mode='after')
    def _check(self):
        if self.min_pool_size < 1:
            raise ValueError('min_pool_size must be at least 1')
        return self


def params_from_config(config: AppConfig) -> PoolingParams:
    '''从 eval_config 原始树里读出池样本下限，或缺失/占位即拒。什么都不默认：
    自己发明一个 min_pool_size 就是替行方拟定了治理值（H-5 / R-12 / V-14）。'''
    tree = config.eval_config
    where = ('eval_config.' + CFG_NORMALIZE_KEY + '.' + CFG_MIN_POOL_SIZE_KEY)
    block = tree.get(CFG_NORMALIZE_KEY) if isinstance(tree, Mapping) else None
    if not isinstance(block, Mapping) or CFG_MIN_POOL_SIZE_KEY not in block:
        raise PoolingConfigError('no ' + where + ' in the configuration')
    raw = block[CFG_MIN_POOL_SIZE_KEY]
    if is_placeholder_value(raw):
        raise PoolingConfigError(where + ' 仍是未签认占位值：' + str(raw))
    return PoolingParams(min_pool_size=raw)


# ---------------------------------------------------------------------------
# 索引与纯查询。全部是纯函数（H-8）。
# ---------------------------------------------------------------------------
def _locator(row) -> tuple:
    '''[L1149] 定位三元组，也是本模块唯一的行序键。'''
    return (row.strategy_id, row.version_id, row.period)


def _pair(row) -> tuple:
    '''strategy x version：evidence 与 strategy_master 的粒度（无 period 列）。'''
    return (row.strategy_id, row.version_id)


def _pool_sort(key: PoolKey) -> tuple:
    '''池的确定序：先业务领域，再证据等级（[L1001] 的两个维度按此先后）。'''
    return (key.biz_domain, key.evidence_class)


def _index(rows, key_of, what: str) -> dict:
    '''载体 -> 唯一索引。重复键即歧义连接，抛错而不是取最后一个（V-14）。'''
    out = {}
    for row in rows:
        key = key_of(row)
        if key in out:
            raise PoolingInputError(
                what + ' 存在重复键，无法唯一连接：' + KEY_SEP.join(str(k) for k in key))
        out[key] = row
    return out


def _master_index(master) -> dict:
    rows = tuple(master)
    for row in rows:
        if not isinstance(row, StrategyMasterRow):
            raise PoolingInputError(
                'master 的每一项必须是 StrategyMasterRow，收到 ' + type(row).__name__)
    return _index(rows, _pair, 'strategy_master')


def flip_rate_unusable(sensitivity: SensitivityReport) -> bool:
    '''[L1019] 首屏否决：任一方案的 flag 或报告级 flags 含 FLIP_RATE_UNUSABLE，
    即"本期结果不得用于淘汰决策"，[L1002] 第 4 条门禁不成立。'''
    if not isinstance(sensitivity, SensitivityReport):
        raise PoolingInputError('sensitivity 必须是 SensitivityReport')
    if any(s.flag is not None and s.flag == CODE_UNUSABLE
           for s in sensitivity.by_scheme):
        return True
    return any(code == CODE_UNUSABLE for code in sensitivity.flags)


def groups(frame: PoolFrame) -> dict:
    '''P-6 的读侧接口：pool_key -> 该池的 PoolRow 元组（按池内名次）。
    跨池只能这样**并列取出**；本模块不提供、也不允许任何合成单一序的出口。'''
    if not isinstance(frame, PoolFrame):
        raise PoolingInputError('frame 必须是 PoolFrame')
    out = {}
    for row in frame.rows:
        out.setdefault(row.pool_key, []).append(row)
    return {k: tuple(out[k]) for k in sorted(out, key=_pool_sort)}


def small_pools(stats: PoolStats, params: PoolingParams) -> tuple:
    '''[L1005] POOL_TOO_SMALL 的显式载体（缺口 1）：count < min_pool_size 的池。
    池内排名照给，只是"仅供参考"，因此它既不是拒绝理由也不是 NOT_ASSESSED，
    不能塞进 reject_reason；由 reports / cli 调本函数拿到后自行披露（V-14）。'''
    if not isinstance(stats, PoolStats):
        raise PoolingInputError('stats 必须是 PoolStats')
    if not isinstance(params, PoolingParams):
        raise PoolingInputError('params 必须是 PoolingParams')
    return tuple(sorted((r.pool_key for r in stats.rows
                         if r.count < params.min_pool_size), key=_pool_sort))


def low_evidence_share(stats: PoolStats):
    '''(C + D) / 已分类总数，取自 evidence_structure（R3）。商无定义时返回 None
    （numeric.safe_div(on_zero=None) 的既有约定），绝不返回 0（V-14）。'''
    if not isinstance(stats, PoolStats):
        raise PoolingInputError('stats 必须是 PoolStats')
    structure = stats.evidence_structure or {}
    low = sum(int(structure.get(c, 0)) for c in LOW_EVIDENCE_CLASSES)
    total = sum(int(structure.get(c, 0)) for c in EVIDENCE_CLASSES)
    return numeric.safe_div(low, total, on_zero=None)


def mix_quality_verdict(current: PoolStats, previous: PoolStats | None):
    '''G-14 / [L1854]：低证据等级占比**上升**即 MIX_QUALITY_DEGRADED（防作弊面：
    只报合并占比时，C 类占比上升会被 A 类的体量掩盖）。
    基线缺失 = 不可比 -> 抛错，不猜"没上升"（V-14）。'''
    if previous is None:
        raise PoolingInputError(
            '无上期 PoolStats 基线，无法判定低证据占比是否上升（V-14 禁静默降级）')
    now = low_evidence_share(current)
    before = low_evidence_share(previous)
    if now is None or before is None:
        raise PoolingInputError('已分类策略数为 0，低证据占比无定义，不可比较')
    if now - before > numeric.TOL:
        return RC.MIX_QUALITY_DEGRADED
    return None


def _share(count: int, base: int, key: PoolKey):
    '''R2 的一套口径。分母为 0 属不可比：safe_div 回 None，这里把它变成显式异常，
    绝不退回 0（V-14）。返回的 Decimal 已 q12。'''
    value = numeric.safe_div(count, base, on_zero=None)
    if value is None:
        raise PoolingInputError(
            '占比分母为 0，商无定义：' + key.biz_domain + KEY_SEP + key.evidence_class)
    return value


def _competition_ranks(items) -> dict:
    '''R1：池内按相对轨降序取**竞争名次**（并列同名次、后续跳号 1,2,2,4）。
    同值判定用 numeric.eq_tol（1e-12）；排序键再带定位二元组，保证同输入同输出。'''
    ordered = sorted(items, key=lambda it: (-it[0].composite_relative,
                                            it[0].strategy_id, it[0].version_id))
    out = {}
    leader = None
    rank = 0
    for position, item in enumerate(ordered, start=1):
        value = item[0].composite_relative
        if leader is None or not numeric.eq_tol(value, leader):
            leader = value
            rank = position
        out[_locator(item[0])] = rank
    return out


# ---------------------------------------------------------------------------
# Step 7 主入口
# ---------------------------------------------------------------------------
def build(scores: ScoreFrame,
          grades: GradeFrame,
          ev: EvidenceFrame,
          master: Sequence[StrategyMasterRow],
          config: AppConfig | None = None,
          *,
          sensitivity: SensitivityReport | None,
          params: PoolingParams | None = None) -> tuple[PoolFrame, PoolStats]:
    '''[L1000] 的签名 + 两个 keyword-only 补充（缺口 3）：sensitivity 是 [L1002]
    第 4 条的载体，必须显式给出（None = Step 8 尚未跑，按 R5 举证制不给准入）；
    config 与 params 必须且只能给一个（同 evidence.classify 的办法）。

    输出恒为 (PoolFrame, PoolStats)：PoolFrame 逐策略给 pool_key / pool_rank /
    primary_pool_eligible / reject_reason，行序按池分组（P-6）；PoolStats 给各池
    计数、占比双报（R2）、证据结构（R3）与 NOT_ASSESSED 的条数与原因分布（[L1004]）。
    '''
    if not isinstance(scores, ScoreFrame):
        raise PoolingInputError('scores 必须是 ScoreFrame')
    if not isinstance(grades, GradeFrame):
        raise PoolingInputError('grades 必须是 GradeFrame')
    if not isinstance(ev, EvidenceFrame):
        raise PoolingInputError('ev 必须是 EvidenceFrame')
    if sensitivity is not None and not isinstance(sensitivity, SensitivityReport):
        raise PoolingInputError('sensitivity 必须是 SensitivityReport 或 None')
    if (config is None) == (params is None):
        raise PoolingError('pass exactly one of config or params')
    resolved = params if params is not None else params_from_config(config)

    periods = sorted({r.period for r in scores.rows})
    if len(periods) > 1:
        raise PoolingInputError(
            '一次 build 只处理一个评价期（跨期不可比），收到：' + ', '.join(periods))

    grade_index = _index(grades.rows, _locator, 'grade')
    ev_index = _index(ev.rows, _pair, 'evidence')
    master_index = _master_index(master)

    # ---- 判定材料：行序 = [L1149] 定位三元组，缺任一载体即抛（V-14）----
    universe = []
    for score in sorted(scores.rows, key=_locator):
        loc = _locator(score)
        grade = grade_index.get(loc)
        if grade is None:
            raise PoolingInputError('score 行没有对应的 grade 行：' + KEY_SEP.join(loc))
        ev_row = ev_index.get(_pair(score))
        if ev_row is None:
            raise PoolingInputError(
                'score 行没有对应的 evidence 行：' + KEY_SEP.join(_pair(score)))
        master_row = master_index.get(_pair(score))
        if master_row is None:
            raise PoolingInputError(
                'score 行没有对应的 strategy_master 行：' + KEY_SEP.join(_pair(score)))
        # [L1001] 分池维度：业务领域来自 T1，证据等级来自 Step 3。
        key = PoolKey(biz_domain=master_row.biz_domain,
                      evidence_class=ev_row.evidence_class)
        universe.append((score, grade, ev_row, key))

    assessed = tuple(u for u in universe if u[1].grade != NOT_ASSESSED)
    by_pool = {}
    for score, grade, ev_row, key in assessed:
        if score.composite_relative is None:
            raise PoolingInputError(
                '已参评但 composite_relative 为 null，池内不可比：'
                + KEY_SEP.join(_locator(score)))
        by_pool.setdefault(key, []).append((score, grade, ev_row, key))
    ranks = {}
    for items in by_pool.values():
        ranks.update(_competition_ranks(items))

    # ---- [L1002] 一级库门禁四条件（举证制，R5）----
    robust_blocked = sensitivity is None or flip_rate_unusable(sensitivity)
    rows = []
    not_assessed_reasons = {}
    for score, grade, ev_row, key in universe:
        na = grade.grade == NOT_ASSESSED
        evidence_ok = ev_row.evidence_class in GATE_EVIDENCE_CLASSES
        redline_ok = not any(code == CODE_HARD_FORCED
                             for code in grade.grade_reason_path)
        eligible = (not na and evidence_ok and redline_ok
                    and grade.grade == GATE_GRADE and not robust_blocked)
        # R4 单槽优先序：BLOCK 先于 WARN，最后才是"只差等级"的 None。
        if not redline_ok:
            reason = RC.REDLINE_HARD_HIT
        elif na:
            reason = (ev_row.evidence_reason if ev_row.evidence_class == 'D'
                      else RC.NOT_ASSESSED)
        elif not evidence_ok:
            reason = RC.PRIMARY_POOL_REJECTED_EVIDENCE
        elif robust_blocked:
            reason = RC.PRIMARY_POOL_REJECTED_ROBUST
        else:
            reason = None
        if na:
            name = getattr(reason, 'value', reason)
            not_assessed_reasons[name] = not_assessed_reasons.get(name, 0) + 1
        rows.append(PoolRow(
            strategy_id=score.strategy_id, version_id=score.version_id,
            period=score.period, pool_key=key,
            pool_rank=None if na else ranks[_locator(score)],
            primary_pool_eligible=eligible, reject_reason=reason))

    # P-6：输出按池分组，池内按名次；并列时按定位二元组，绝不合成单一序。
    rows.sort(key=lambda r: (r.pool_key.biz_domain, r.pool_key.evidence_class,
                             r.pool_rank is None, r.pool_rank or 0,
                             r.strategy_id, r.version_id))

    # ---- [L1006] 各池计数 + R2 占比双报（分母只含已参评，[L1004]）----
    pool_count = {}
    domain_count = {}
    for score, grade, ev_row, key in assessed:
        pool_count[key] = pool_count.get(key, 0) + 1
        domain_count[key.biz_domain] = domain_count.get(key.biz_domain, 0) + 1
    grand = len(assessed)
    stat_rows = []
    for key in sorted(pool_count, key=_pool_sort):
        count = pool_count[key]
        stat_rows.append(PoolStatRow(
            pool_key=key, count=count,
            share_in_pool=_share(count, domain_count[key.biz_domain], key),
            share_overall=_share(count, grand, key)))

    # ---- [L1003] 证据结构（R3：全部策略，四类闭合）+ [L1004] NOT_ASSESSED ----
    structure = {c: 0 for c in EVIDENCE_CLASSES}
    for score, grade, ev_row, key in universe:
        structure[ev_row.evidence_class] += 1
    not_assessed_count = len(universe) - grand

    return (PoolFrame(rows=tuple(rows)),
            PoolStats(rows=tuple(stat_rows), evidence_structure=structure,
                      not_assessed_count=not_assessed_count,
                      not_assessed_reasons=dict(sorted(not_assessed_reasons.items()))))
