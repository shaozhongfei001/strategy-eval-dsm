'''tests/test_pooling.py -- C5 守护测试：G-02（证据门禁）+ P-6（分池禁混排）+ 占比双报。

期望值全部手算（R-14：绝不拿实现输出反填）。手算底稿写在每个测试的 docstring 里，
输入一律按 R-2 用 dsm.models 的 pydantic 契约直接构造（上游 evidence/grading/
sensitivity 的实现不参与本文件的任何断言）。

主场景 SCENARIO（4 策略，全部已参评）：

    sid  biz_domain  class  composite_relative  grade
    S1   CARD        A      0.90                L1
    S2   CARD        B      0.80                L1
    S3   CARD        B      0.70                L2
    S4   LOAN        C      0.95                L2

手算：池 = (CARD,A)[S1] / (CARD,B)[S2,S3] / (LOAN,C)[S4]；
已参评 4，CARD 域 3，LOAN 域 1；
share_in_pool = 1/3, 2/3, 1/1；share_overall = 1/4, 2/4, 1/4；
准入（干净 sensitivity）= S1, S2 两条。
'''
from __future__ import annotations

from datetime import date

import pytest

from dsm import pooling
from dsm.config import AppConfig
from dsm.models import (AttainmentRow, EvidenceFrame, EvidenceRow, GradeFrame,
                        GradeRow, NormalizedFrame, NormalizedRow, PoolKey, PoolStats,
                        ScoreFrame, ScoreRow, SensitivityReport,
                        SensitivitySchemeResult, StrategyMasterRow)
from dsm.numeric import D
from dsm.reason_codes import RC

P = '2026Q1'
VER = 'v1'
LIMIT = '仅覆盖一线城市，外推需谨慎'
PARAMS = pooling.PoolingParams(min_pool_size=2)
CLEAN = SensitivityReport(
    by_scheme=(SensitivitySchemeResult(scheme='OAT_10', overall_flip_rate=D('0.02'),
                                       flipped_count=0, assessed_count=4, flag=None),),
    by_strategy=())
UNUSABLE = SensitivityReport(
    by_scheme=(SensitivitySchemeResult(scheme='OAT_10', overall_flip_rate=D('0.40'),
                                       flipped_count=4, assessed_count=4,
                                       flag=RC.FLIP_RATE_UNUSABLE),),
    by_strategy=())
REVIEW = SensitivityReport(
    by_scheme=(SensitivitySchemeResult(scheme='OAT_10', overall_flip_rate=D('0.10'),
                                       flipped_count=1, assessed_count=4,
                                       flag=RC.FLIP_RATE_REVIEW),),
    by_strategy=())

# (sid, biz_domain, evidence_class, composite_relative, grade)
SCENARIO = (('S1', 'CARD', 'A', '0.90', 'L1'),
            ('S2', 'CARD', 'B', '0.80', 'L1'),
            ('S3', 'CARD', 'B', '0.70', 'L2'),
            ('S4', 'LOAN', 'C', '0.95', 'L2'))
# 3 已参评 + 1 条 D 类不可评价（[L1004] 不进任何分母）
NA_SCENARIO = (('S1', 'CARD', 'A', '0.90', 'L1'),
               ('S2', 'CARD', 'B', '0.80', 'L1'),
               ('S3', 'CARD', 'D', None, 'NOT_ASSESSED'),
               ('S4', 'LOAN', 'C', '0.70', 'L2'))


def master_row(sid, domain, ver=VER):
    return StrategyMasterRow(
        strategy_id=sid, version_id=ver, strategy_name=sid + ' 名称',
        biz_domain=domain, scene_code='SC-01', segment_type='EXISTING',
        online_date=date(2025, 1, 1), owner_dept='信用卡部', owner_name='张三',
        status='ACTIVE')


def score_row(sid, rel, period=P, ver=VER):
    value = None if rel is None else D(rel)
    return ScoreRow(strategy_id=sid, version_id=ver, period=period,
                    composite_absolute=value, composite_relative=value,
                    dim_absolute={'D1': D('0.5')}, dim_relative={'D1': D('0.5')},
                    coverage=D('1'), weight_version_id='WV-2026Q1',
                    operator='LINEAR')


def grade_row(sid, grade, path=(RC.FIRST_PERIOD,), period=P, ver=VER):
    return GradeRow(strategy_id=sid, version_id=ver, period=period, grade=grade,
                    grade_reason_path=tuple(path), capped=False, cap_reason=None,
                    action=None, usable_for_elimination=(grade != 'NOT_ASSESSED'))


EV_REASON = {'A': RC.EV_A_RANDOMIZED, 'B': RC.EV_B_QUASI,
             'C': RC.EV_C_OBSERVATIONAL, 'D': RC.EVIDENCE_CARD_MISSING}


def ev_row(sid, cls, reason=None, ver=VER):
    return EvidenceRow(strategy_id=sid, version_id=ver, evidence_class=cls,
                       evidence_reason=reason or EV_REASON[cls],
                       evidence_source='CARD_ONLY',
                       interpretation_limit=LIMIT if cls in ('C', 'D') else None)


def parts(specs, period=P):
    '''R-2：把五元组规格摊成四个上游载体的 list，便于逐条删改做负向测试。'''
    scores, grades, ev, master = [], [], [], []
    for sid, domain, cls, rel, grade in specs:
        scores.append(score_row(sid, rel, period=period))
        grades.append(grade_row(sid, grade, period=period))
        ev.append(ev_row(sid, cls))
        master.append(master_row(sid, domain))
    return scores, grades, ev, master


def go(scores, grades, ev, master, *, sensitivity=CLEAN, params=PARAMS, config=None,
       normalized=None):
    '''normalized 是 SEAM-1 加的 Step 2 标注载体（pooling 缺口 6）：默认 None，
    即「无从举证」，既有 19 条断言的语义一字不改。'''
    return pooling.build(ScoreFrame(rows=tuple(scores)), GradeFrame(rows=tuple(grades)),
                         EvidenceFrame(rows=tuple(ev)), tuple(master), config,
                         sensitivity=sensitivity, normalized=normalized,
                         params=params)


def run(specs, **kw):
    return go(*parts(specs), **kw)


def by_sid(frame):
    return {r.strategy_id: r for r in frame.rows}


def stats_by_pool(stats):
    return {(r.pool_key.biz_domain, r.pool_key.evidence_class): r for r in stats.rows}


def stat(structure, rows=(), na=0, reasons=None):
    return PoolStats(rows=tuple(rows), evidence_structure=dict(structure),
                     not_assessed_count=na,
                     not_assessed_reasons=dict(reasons or {}))


# ---------------------------------------------------------------------------
# P-6 分池禁混排
# ---------------------------------------------------------------------------
def test_pool_key_is_domain_times_evidence_class():
    '''P-6：pool_key 恒等于 (T1.biz_domain, Step3.evidence_class)。
    手算：S1 -> (CARD,A)、S2/S3 -> (CARD,B)、S4 -> (LOAN,C)，共 3 个池。'''
    frame, stats = run(SCENARIO)
    got = by_sid(frame)
    assert got['S1'].pool_key == PoolKey(biz_domain='CARD', evidence_class='A')
    assert got['S2'].pool_key == PoolKey(biz_domain='CARD', evidence_class='B')
    assert got['S3'].pool_key == PoolKey(biz_domain='CARD', evidence_class='B')
    assert got['S4'].pool_key == PoolKey(biz_domain='LOAN', evidence_class='C')
    assert sorted(stats_by_pool(stats)) == [('CARD', 'A'), ('CARD', 'B'), ('LOAN', 'C')]


def test_rank_never_crosses_pools():
    '''P-6 核心：S4 的相对轨 0.95 是全场最高，但它只在 (LOAN,C) 池里排第 1；
    S1 (0.90) 在 (CARD,A) 排第 1，S2 (0.80)/S3 (0.70) 在 (CARD,B) 排 1/2。
    手算：名次 1 出现 3 次 -> 不存在任何单一合并序；把 S4 拿掉，S1/S2/S3 的
    名次一字不变 -> 跨池互不影响。'''
    frame, _stats = run(SCENARIO)
    got = by_sid(frame)
    assert (got['S1'].pool_rank, got['S2'].pool_rank,
            got['S3'].pool_rank, got['S4'].pool_rank) == (1, 1, 2, 1)
    assert sum(1 for r in frame.rows if r.pool_rank == 1) == 3
    frame2, _ = run(tuple(s for s in SCENARIO if s[0] != 'S4'))
    got2 = by_sid(frame2)
    assert (got2['S1'].pool_rank, got2['S2'].pool_rank, got2['S3'].pool_rank) == (1, 1, 2)


def test_frame_rows_are_grouped_not_merged():
    '''P-6：输出行序按池分组（CARD,A -> CARD,B -> LOAN,C），池内按名次；
    groups() 只能并列取出，取不出一个跨池的序。手算：4 行的 sid 序为
    S1 | S2,S3 | S4，池内名次 1 | 1,2 | 1（非单调 -> 不是单一序）。'''
    frame, _stats = run(SCENARIO)
    assert [r.strategy_id for r in frame.rows] == ['S1', 'S2', 'S3', 'S4']
    assert [r.pool_rank for r in frame.rows] == [1, 1, 2, 1]
    groups = pooling.groups(frame)
    assert [k.biz_domain + k.evidence_class for k in groups] == ['CARDA', 'CARDB', 'LOANC']
    assert [len(v) for v in groups.values()] == [1, 2, 1]


# ---------------------------------------------------------------------------
# G-02 证据门禁 + 一级库四条件
# ---------------------------------------------------------------------------
def test_g02_c_class_barred_from_primary_library():
    '''G-02 / [L1404]：C 类即使等级给到 L1 也进不了一级库（现实里 grading Step 2
    会把 C 封到 L2，这里故意直接构造 L1，证明 pooling 的门禁不依赖上游封顶）。
    手算：S4 = C 类 + L1 -> eligible False，reject_reason = 证据码；S4 仍只在
    (LOAN,C) 池内排第 1（禁混排）。准入总数 = S1,S2 两条。'''
    specs = (('S1', 'CARD', 'A', '0.90', 'L1'),
             ('S2', 'CARD', 'B', '0.80', 'L1'),
             ('S4', 'LOAN', 'C', '0.95', 'L1'))
    frame, _ = run(specs)
    got = by_sid(frame)
    assert got['S4'].primary_pool_eligible is False
    assert got['S4'].reject_reason == RC.PRIMARY_POOL_REJECTED_EVIDENCE
    assert got['S4'].pool_rank == 1
    assert got['S4'].pool_key.evidence_class == 'C'
    assert sorted(s for s, r in got.items() if r.primary_pool_eligible) == ['S1', 'S2']


def test_g02_clean_a_b_l1_rows_are_admitted():
    '''G-02 happy path（R-4 冒烟）：A/B + L1 + 无 HARD + 无 FLIP_RATE_UNUSABLE
    四条件全成立 -> 准入且 reject_reason 为 None。手算：SCENARIO 准入 = 2 条
    （S1 A/L1、S2 B/L1），S3 因 grade=L2 落榜，S4 因 C 类落榜。'''
    frame, _ = run(SCENARIO)
    got = by_sid(frame)
    assert [(s, got[s].primary_pool_eligible) for s in ('S1', 'S2', 'S3', 'S4')] == [
        ('S1', True), ('S2', True), ('S3', False), ('S4', False)]
    assert got['S1'].reject_reason is None and got['S2'].reject_reason is None


def test_not_assessed_is_counted_separately_and_out_of_denominators():
    '''[L1004] + R2/R3：D 类 S3 不可评价 -> 不进任何分母、不单独成池、pool_rank=None。
    手算：已参评 3（CARD 2 / LOAN 1）
      (CARD,A) 1 -> 1/2 = 0.5，1/3 = 0.333333333333
      (CARD,B) 1 -> 0.5，0.333333333333
      (LOAN,C) 1 -> 1/1 = 1，0.333333333333
    PoolStats 只有 3 行（没有 (CARD,D)），PoolFrame 有 4 行；
    not_assessed_count = 1，原因分布 = {EVIDENCE_CARD_MISSING: 1}（取 D 类自身的
    evidence_reason）；证据结构含 D -> {A:1,B:1,C:1,D:1}。'''
    frame, stats = run(NA_SCENARIO)
    got = by_sid(frame)
    assert len(frame.rows) == 4 and len(stats.rows) == 3
    assert got['S3'].pool_rank is None
    assert got['S3'].primary_pool_eligible is False
    assert got['S3'].reject_reason == RC.EVIDENCE_CARD_MISSING
    assert got['S3'].pool_key == PoolKey(biz_domain='CARD', evidence_class='D')
    assert ('CARD', 'D') not in stats_by_pool(stats)
    rows = stats_by_pool(stats)
    assert rows[('CARD', 'A')].share_in_pool == D('0.5')
    assert rows[('CARD', 'A')].share_overall == D('0.333333333333')
    assert rows[('LOAN', 'C')].share_in_pool == D('1')
    assert stats.not_assessed_count == 1
    assert stats.not_assessed_reasons == {'EVIDENCE_CARD_MISSING': 1}
    assert stats.evidence_structure == {'A': 1, 'B': 1, 'C': 1, 'D': 1}


def test_hard_redline_hit_outranks_other_reject_reasons():
    '''[L1002] 第 3 条 + R4 优先序：HARD 命中（grading 在 grade_reason_path 上留
    GR_REDLINE_FORCED）即否决，且 BLOCK 码优先于 WARN 码。
    手算：S1 = A 类 + L1 但命中 HARD -> eligible False，reject_reason =
    REDLINE_HARD_HIT（不是 None）；准入只剩 S2 一条。'''
    scores, grades, ev, master = parts(SCENARIO)
    grades = [grade_row('S1', 'L1', path=(RC.GR_REDLINE_FORCED,))] + grades[1:]
    frame, _ = go(scores, grades, ev, master)
    got = by_sid(frame)
    assert got['S1'].primary_pool_eligible is False
    assert got['S1'].reject_reason == RC.REDLINE_HARD_HIT
    assert [s for s, r in got.items() if r.primary_pool_eligible] == ['S2']


def test_flip_rate_unusable_closes_the_primary_library():
    '''[L1002] 第 4 条 / [L1019]：任一方案 flag = FLIP_RATE_UNUSABLE（或报告级
    flags 含该码）-> 本期不得用于淘汰，一级库整体不成立。
    手算：准入 0 条；S1（其余三条件全成立）落 PRIMARY_POOL_REJECTED_ROBUST；
    S4 仍落证据码（R4：证据先于稳健）；FLIP_RATE_REVIEW 是否决以外的码，
    不该关门 -> 准入仍是 S1,S2 两条。'''
    frame, _ = run(SCENARIO, sensitivity=UNUSABLE)
    got = by_sid(frame)
    assert sum(1 for r in frame.rows if r.primary_pool_eligible) == 0
    assert got['S1'].reject_reason == RC.PRIMARY_POOL_REJECTED_ROBUST
    assert got['S4'].reject_reason == RC.PRIMARY_POOL_REJECTED_EVIDENCE
    flagged = SensitivityReport(by_scheme=CLEAN.by_scheme, by_strategy=(),
                                flags=(RC.FLIP_RATE_UNUSABLE,))
    frame2, _ = run(SCENARIO, sensitivity=flagged)
    assert sum(1 for r in frame2.rows if r.primary_pool_eligible) == 0
    frame3, _ = run(SCENARIO, sensitivity=REVIEW)
    assert sorted(s for s, r in by_sid(frame3).items()
                  if r.primary_pool_eligible) == ['S1', 'S2']


def test_missing_robustness_carrier_withholds_admission():
    '''R5 举证制 + V-14：sensitivity=None（Step 8 尚未跑，[L1346] 在 [L1350] 之前）
    时第 4 条无法正面成立 -> 不给准入，且必须留显式 reason_code，绝不静默放行。
    手算：准入 0 条；S1 落 PRIMARY_POOL_REJECTED_ROBUST；池内名次照给（S1=1），
    占比照算（(CARD,A) 1/3 与 1/4），因为分池与占比不依赖稳健性。'''
    frame, stats = run(SCENARIO, sensitivity=None)
    got = by_sid(frame)
    assert sum(1 for r in frame.rows if r.primary_pool_eligible) == 0
    assert got['S1'].reject_reason == RC.PRIMARY_POOL_REJECTED_ROBUST
    assert got['S1'].pool_rank == 1
    assert stats_by_pool(stats)[('CARD', 'A')].share_in_pool == D('0.333333333333')


def test_non_l1_rejection_leaves_the_single_slot_empty():
    '''缺口 2 钉死：[L1002] 四条件里"grade = L1"在 [L1005] 没有对应注册码，
    本包不编码（K-01~K-20 纪律）-> 单槽留 None，等级本身在台账里就是披露。
    手算：S3 = B 类 + L2 + 无 HARD + 稳健性干净 -> eligible False 且 reason None。'''
    frame, _ = run(SCENARIO)
    row = by_sid(frame)['S3']
    assert row.primary_pool_eligible is False
    assert row.reject_reason is None


# ---------------------------------------------------------------------------
# 占比双报（[L1003] / [L1006] / B-020）
# ---------------------------------------------------------------------------
def test_double_share_two_bases_hand_computed():
    '''R2 手算（分母都剔除 NOT_ASSESSED，本场景 4 条全已参评）：
      (CARD,A) 1 条：池内 1/3 = 0.333333333333（CARD 域 3 条），合并 1/4 = 0.25
      (CARD,B) 2 条：池内 2/3 = 0.666666666667，合并 2/4 = 0.5
      (LOAN,C) 1 条：池内 1/1 = 1，合并 1/4 = 0.25
    两套口径同时出现在同一行 PoolStatRow 上（[L1003] 禁止只报合并占比）。
    合并占比之和手算 = 0.25 + 0.5 + 0.25 = 1（已参评全体的一个划分）。'''
    _frame, stats = run(SCENARIO)
    rows = stats_by_pool(stats)
    assert rows[('CARD', 'A')].count == 1
    assert rows[('CARD', 'A')].share_in_pool == D('0.333333333333')
    assert rows[('CARD', 'A')].share_overall == D('0.25')
    assert rows[('CARD', 'B')].count == 2
    assert rows[('CARD', 'B')].share_in_pool == D('0.666666666667')
    assert rows[('CARD', 'B')].share_overall == D('0.5')
    assert rows[('LOAN', 'C')].share_in_pool == D('1')
    assert rows[('LOAN', 'C')].share_overall == D('0.25')
    assert sum(r.share_overall for r in stats.rows) == D('1')
    assert sum(r.share_in_pool for r in stats.rows
               if r.pool_key.biz_domain == 'CARD') == D('1')


def test_two_share_bases_are_not_mutually_derivable():
    '''占比双报的硬要求：两套口径互不可反推。
    手算：两个场景的 (CARD,A) 都是 1 条、合并占比都是 1/4 = 0.25，但
      X：CARD 域共 2 条 -> 池内 1/2 = 0.5
      Y：CARD 域共 3 条 -> 池内 1/3 = 0.333333333333
    只看合并占比完全分不出 X 与 Y；反之亦然（LOAN 域两场景不同）。'''
    spec_x = (('S1', 'CARD', 'A', '0.90', 'L1'), ('S2', 'CARD', 'B', '0.80', 'L1'),
              ('S3', 'LOAN', 'C', '0.70', 'L2'), ('S4', 'LOAN', 'C', '0.60', 'L2'))
    spec_y = (('S1', 'CARD', 'A', '0.90', 'L1'), ('S2', 'CARD', 'B', '0.80', 'L1'),
              ('S3', 'CARD', 'B', '0.75', 'L1'), ('S4', 'LOAN', 'C', '0.60', 'L2'))
    _fx, sx = run(spec_x)
    _fy, sy = run(spec_y)
    rx = stats_by_pool(sx)[('CARD', 'A')]
    ry = stats_by_pool(sy)[('CARD', 'A')]
    assert rx.share_overall == ry.share_overall == D('0.25')
    assert rx.share_in_pool == D('0.5')
    assert ry.share_in_pool == D('0.333333333333')
    assert stats_by_pool(sx)[('LOAN', 'C')].share_in_pool == D('1')
    assert stats_by_pool(sy)[('LOAN', 'C')].share_in_pool == D('1')
    assert stats_by_pool(sx)[('CARD', 'B')].share_in_pool == D('0.5')
    assert stats_by_pool(sy)[('CARD', 'B')].share_in_pool == D('0.666666666667')


def test_evidence_structure_discloses_all_four_classes():
    '''[L1003] 证据结构披露 + R3：四类闭合（缺的类给 0，不给缺键）。
    手算：SCENARIO -> {A:1, B:2, C:1, D:0}；NA_SCENARIO -> {A:1,B:1,C:1,D:1}。
    低证据占比 (C+D)/总数：SCENARIO = 1/4 = 0.25，NA_SCENARIO = 2/4 = 0.5。'''
    _f1, s1 = run(SCENARIO)
    assert s1.evidence_structure == {'A': 1, 'B': 2, 'C': 1, 'D': 0}
    assert s1.not_assessed_count == 0 and s1.not_assessed_reasons == {}
    assert pooling.low_evidence_share(s1) == D('0.25')
    _f2, s2 = run(NA_SCENARIO)
    assert pooling.low_evidence_share(s2) == D('0.5')


def test_small_pools_is_the_pool_too_small_carrier():
    '''缺口 1：POOL_TOO_SMALL 在 [L1006] 没有列可落，由 small_pools() 显式回吐。
    手算（min_pool_size = 2）：(CARD,A) 1 条 < 2 -> 小池；(LOAN,C) 1 条 < 2 ->
    小池；(CARD,B) 2 条 = 2 -> 不是。min_pool_size = 1 时一个都没有。
    小池**不影响**名次与准入（[L1005] 只说"池内排名仅供参考"）。'''
    frame, stats = run(SCENARIO)
    assert pooling.small_pools(stats, PARAMS) == (
        PoolKey(biz_domain='CARD', evidence_class='A'),
        PoolKey(biz_domain='LOAN', evidence_class='C'))
    assert pooling.small_pools(stats, pooling.PoolingParams(min_pool_size=1)) == ()
    assert pooling.small_pools(
        stats, pooling.PoolingParams(min_pool_size=3)) == (
        PoolKey(biz_domain='CARD', evidence_class='A'),
        PoolKey(biz_domain='CARD', evidence_class='B'),
        PoolKey(biz_domain='LOAN', evidence_class='C'))
    assert sorted(s for s, r in by_sid(frame).items() if r.primary_pool_eligible) == ['S1', 'S2']


def test_mix_quality_degraded_needs_a_signed_baseline():
    '''G-14 / [L1854]：低证据（C+D）占比**上升**才告警，且必须有基线。
    手算（分母 = 四类之和）：当期 4/10 = 0.4；
      上期 3/10 = 0.3 -> 0.4 - 0.3 = 0.1 > 1e-12 -> MIX_QUALITY_DEGRADED
      上期 4/10 = 0.4 -> 差 0 -> None（不告警）
      上期 3/10 且当期 3/10 -> None
    基线缺失（None）= 不可比 -> 抛 PoolingInputError（V-14，不猜"没上升"）；
    四类全 0 -> 占比无定义 -> 同样抛，不返回 0。'''
    current = stat({'A': 3, 'B': 3, 'C': 4, 'D': 0})
    assert pooling.mix_quality_verdict(current, stat({'A': 4, 'B': 3, 'C': 3, 'D': 0})) \
        == RC.MIX_QUALITY_DEGRADED
    assert pooling.mix_quality_verdict(current, stat({'A': 3, 'B': 3, 'C': 4, 'D': 0})) is None
    assert pooling.mix_quality_verdict(current, stat({'A': 2, 'B': 3, 'C': 5, 'D': 0})) is None
    assert pooling.mix_quality_verdict(stat({'A': 5, 'B': 2, 'C': 3, 'D': 0}), current) is None
    with pytest.raises(pooling.PoolingInputError):
        pooling.mix_quality_verdict(current, None)
    with pytest.raises(pooling.PoolingInputError):
        pooling.mix_quality_verdict(current, stat({'A': 0, 'B': 0, 'C': 0, 'D': 0}))
    assert pooling.low_evidence_share(stat({'A': 0, 'B': 0, 'C': 0, 'D': 0})) is None


# ---------------------------------------------------------------------------
# V-9 数值口径 / V-14 无静默降级 / 治理值不拟定
# ---------------------------------------------------------------------------
def test_ties_use_competition_ranking_under_tol():
    '''R1 + V-9：并列取竞争名次 1,1,3；同值判定用 1e-12 容差。
    手算：0.80 与 0.7999999999999 差 1e-13 <= 1e-12 -> 并列 -> 名次 1,1，
    第三条 0.79 差 0.01 -> 名次 3（跳号，不是 2）；
    换成 0.79999999999（差 1e-11 > 1e-12）-> 不并列 -> 名次 1,2,3。'''
    tie = (('S1', 'CARD', 'A', '0.80', 'L1'),
           ('S2', 'CARD', 'A', '0.7999999999999', 'L1'),
           ('S3', 'CARD', 'A', '0.79', 'L1'))
    frame, _ = run(tie)
    got = by_sid(frame)
    assert (got['S1'].pool_rank, got['S2'].pool_rank, got['S3'].pool_rank) == (1, 1, 3)
    near = (('S1', 'CARD', 'A', '0.80', 'L1'),
            ('S2', 'CARD', 'A', '0.79999999999', 'L1'),
            ('S3', 'CARD', 'A', '0.79', 'L1'))
    got2 = by_sid(run(near)[0])
    assert (got2['S1'].pool_rank, got2['S2'].pool_rank, got2['S3'].pool_rank) == (1, 2, 3)


def test_params_from_config_never_invents_a_threshold():
    '''V-14 / H-5 / K 纪律：min_pool_size 只能从配置来。
    手算：eval_config.normalize.min_pool_size = 5 -> params.min_pool_size == 5；
    缺块、缺键、值为 PLACEHOLDER -> PoolingConfigError；min_pool_size = 0 -> 校验失败；
    config 与 params 同时给 / 同时不给 -> PoolingError。'''
    cfg = AppConfig(eval_config={'normalize': {'min_pool_size': 5}}, weights={},
                    redlines={}, grade_rules={}, anchor_set={}, ahp_matrices={})
    assert pooling.params_from_config(cfg).min_pool_size == 5
    scores, grades, ev, master = parts(SCENARIO)
    frame, stats = pooling.build(ScoreFrame(rows=tuple(scores)),
                                 GradeFrame(rows=tuple(grades)),
                                 EvidenceFrame(rows=tuple(ev)), tuple(master), cfg,
                                 sensitivity=CLEAN)
    assert len(stats.rows) == 3 and len(frame.rows) == 4
    empty = AppConfig(eval_config={}, weights={}, redlines={}, grade_rules={},
                      anchor_set={}, ahp_matrices={})
    with pytest.raises(pooling.PoolingConfigError):
        pooling.params_from_config(empty)
    placeholder = AppConfig(eval_config={'normalize': {'min_pool_size': 'PLACEHOLDER'}},
                            weights={}, redlines={}, grade_rules={}, anchor_set={},
                            ahp_matrices={})
    with pytest.raises(pooling.PoolingConfigError):
        pooling.params_from_config(placeholder)
    with pytest.raises(ValueError):
        pooling.PoolingParams(min_pool_size=0)
    with pytest.raises(pooling.PoolingError):
        go(scores, grades, ev, master, config=cfg)
    with pytest.raises(pooling.PoolingError):
        pooling.build(ScoreFrame(rows=tuple(scores)), GradeFrame(rows=tuple(grades)),
                      EvidenceFrame(rows=tuple(ev)), tuple(master),
                      sensitivity=CLEAN)


def test_missing_or_ambiguous_carriers_raise():
    '''V-14 负向（R-4）：缺载体/歧义/不可比一律显式抛，绝不兜底。
    六条：缺 grade 行、缺 evidence 行、缺 master 行、master 重复键、
    已参评但 composite_relative 为 null、一次 build 收到两个评价期。'''
    scores, grades, ev, master = parts(SCENARIO)
    with pytest.raises(pooling.PoolingInputError):
        go(scores, [g for g in grades if g.strategy_id != 'S2'], ev, master)
    with pytest.raises(pooling.PoolingInputError):
        go(scores, grades, [e for e in ev if e.strategy_id != 'S2'], master)
    with pytest.raises(pooling.PoolingInputError):
        go(scores, grades, ev, [m for m in master if m.strategy_id != 'S2'])
    with pytest.raises(pooling.PoolingInputError):
        go(scores, grades, ev, master + [master_row('S1', 'LOAN')])
    null_rel = [score_row('S1', None)] + scores[1:]
    with pytest.raises(pooling.PoolingInputError):
        go(null_rel, grades, ev, master)
    mixed = [score_row('S1', '0.90', period='2025Q4')] + scores[1:]
    mixed_grades = [grade_row('S1', 'L1', period='2025Q4')] + grades[1:]
    with pytest.raises(pooling.PoolingInputError):
        go(mixed, mixed_grades, ev, master)
    with pytest.raises(pooling.PoolingInputError):
        go(scores, grades, ev, master, sensitivity='OAT_10')


def test_build_is_deterministic_and_order_independent():
    '''H-8 / V-3 风味：同一批载体乱序喂进去，PoolFrame 与 PoolStats 逐字段相同
    （行序只由 [L1149] 定位三元组与池序决定，不由输入顺序决定）。
    手算：两种顺序下 (CARD,B) 的 count=2、池内 2/3、合并 2/4 都相同。'''
    scores, grades, ev, master = parts(SCENARIO)
    frame_a, stats_a = go(scores, grades, ev, master)
    frame_b, stats_b = go(scores[::-1], grades[::-1], ev[::-1], master[::-1])
    assert frame_a.model_dump() == frame_b.model_dump()
    assert stats_a.model_dump() == stats_b.model_dump()
    assert stats_by_pool(stats_b)[('CARD', 'B')].count == 2


# ---------------------------------------------------------------------------
# SEAM-1 / ORCH-28 裁决 3：composite_relative 为 null 的已参评行分两种
#   有 normalize 的 [L943] 标注（SMALL_POOL / INACTIVE_METRIC / RANK_REVERSAL_RISK）
#     -> 显式降级留痕：reject_reason 承载该码、pool_rank = null、不予一级库准入，
#        但**照旧计入占比双报的分母**（C5 冻结口径），Step 7 不中断；
#   没有任何标注 -> 真契约违规，照 V-14 抛 PoolingInputError。
# 标注载体是 keyword-only 的 normalized（缺口 6）；不给载体 = 无从举证 = 抛错。
# ---------------------------------------------------------------------------
# 手算（SEAM_NULL：S3 的 composite_relative 为 null，其余同 SCENARIO）：
#   已参评 4 -> 池 (CARD,A) 1 / (CARD,B) 2 / (LOAN,C) 1；CARD 域 3、LOAN 域 1
#   share_in_pool = 1/3 = 0.333333333333、2/3 = 0.666666666667、1/1 = 1
#   share_overall = 1/4 = 0.25、2/4 = 0.5、1/4 = 0.25
#   名次：S1 = 1、S2 = 1（(CARD,B) 里只有它可比）、S3 = null、S4 = 1
#   若把 S3 剔出分母则会得到 1/2 与 1/3，下面的断言把这两个值显式判为错误
SEAM_NULL = (('S1', 'CARD', 'A', '0.90', 'L1'),
             ('S2', 'CARD', 'B', '0.80', 'L1'),
             ('S3', 'CARD', 'B', None, 'L2'),
             ('S4', 'LOAN', 'C', '0.95', 'L2'))


def nrow(sid, mid, code=None, domain='CARD', cls='B', period=P, ver=VER):
    '''Step 2 的载体行（R-2：字段名逐字抄 dsm/models.py NormalizedRow）。'''
    return NormalizedRow(
        strategy_id=sid, version_id=ver, period=period, metric_id=mid,
        pool_key=PoolKey(biz_domain=domain, evidence_class=cls),
        norm_value=D('0.5'), method='min_max', anchor_used=True, reason_code=code)


def nframe(*rows):
    return NormalizedFrame(rows=tuple(rows))


def test_seam1_annotated_null_is_carried_by_reject_reason_not_raised():
    """ORCH-28 裁决 3 正面：normalize 已标注 SMALL_POOL -> Step 7 不中断。"""
    carrier = nframe(nrow('S3', 'M1', RC.SMALL_POOL.value))
    frame, stats = run(SEAM_NULL, normalized=carrier)
    got = by_sid(frame)
    # 该行：码落在 reject_reason 单槽上，pool_rank = null，一级库不予准入（举证制）
    assert got['S3'].pool_rank is None
    assert got['S3'].reject_reason == RC.SMALL_POOL
    assert got['S3'].primary_pool_eligible is False
    assert got['S3'].pool_key == PoolKey(biz_domain='CARD', evidence_class='B')
    # 其余行不受影响：名次、准入、拒绝理由全部照旧（手算见上）
    assert [r.strategy_id for r in frame.rows] == ['S1', 'S2', 'S3', 'S4']
    assert (got['S1'].pool_rank, got['S2'].pool_rank, got['S4'].pool_rank) == (1, 1, 1)
    assert got['S1'].reject_reason is None and got['S2'].reject_reason is None
    assert got['S4'].reject_reason == RC.PRIMARY_POOL_REJECTED_EVIDENCE
    assert [(s, got[s].primary_pool_eligible) for s in ('S1', 'S2', 'S4')] == [
        ('S1', True), ('S2', True), ('S4', False)]
    # 占比双报的分母**仍含** S3（已参评口径，[L1004] 只剔 NOT_ASSESSED）
    rows = stats_by_pool(stats)
    assert rows[('CARD', 'B')].count == 2
    assert rows[('CARD', 'B')].share_in_pool == D('0.666666666667')   # 2/3，不是 1/2
    assert rows[('CARD', 'B')].share_overall == D('0.5')             # 2/4，不是 2/3
    assert rows[('CARD', 'A')].share_in_pool == D('0.333333333333')   # 1/3，不是 1/2
    assert rows[('CARD', 'A')].share_overall == D('0.25')
    assert rows[('LOAN', 'C')].share_in_pool == D('1')
    assert rows[('LOAN', 'C')].share_overall == D('0.25')
    assert stats.not_assessed_count == 0
    assert stats.evidence_structure == {'A': 1, 'B': 2, 'C': 1, 'D': 0}


def test_seam1_unannotated_null_is_still_a_contract_breach():
    """ORCH-28 裁决 3 反面：没有 SMALL_POOL / INACTIVE_METRIC / RANK_REVERSAL_RISK
    任一标注的 null 仍必须抛（V-14）。四种「无从举证」的情形逐条判：
    不给载体、载体里该行 reason_code 为空、只标了 ANCHOR_SET_STALE（不在裁决三码内）、
    载体里根本没有该策略的行。"""
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL)                                            # normalized=None
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL, normalized=nframe(nrow('S3', 'M1', None)))
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL, normalized=nframe(
            nrow('S3', 'M1', RC.ANCHOR_SET_STALE.value)))
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL, normalized=nframe(nrow('S2', 'M1', RC.SMALL_POOL.value)))
    # 载体类型不对也抛，不静默当成「没有标注」
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL, normalized=[nrow('S3', 'M1', RC.SMALL_POOL.value)])


def test_models1_all_inactive_strategy_is_disclosed_by_excluded_not_raised():
    """MODELS-1 / ORCH-32 裁决 5：某策略**全部**指标 INACTIVE 且 on_zero=None 时，
    Step2 的 rows 里根本没有它，只有 frame 级 excluded 有。Step7 必须读得到该
    标注 -> 走 WARN/降级（reject_reason = INACTIVE_METRIC、pool_rank = null、
    不予一级库准入、仍计入占比双报分母），绝不因为「rows 里查无此人」而误判为
    无标注的 null 抛错（那就是 SEAM-1 GAP(3) 的静默断链）。
    手算同 SEAM_NULL：S3 的 composite_relative 为 null，其余 3 条可比。
    反面：excluded 里放一枚**不在** ORCH-28 裁决 3 三码内的标注（ANCHOR_SET_STALE）
    仍必须抛 -> 不自行放宽举证口径。"""
    dropped = AttainmentRow(
        strategy_id='S3', version_id=VER, period=P, metric_id='M1',
        attainment=D('1.0'), direction=1, target_source='budget',
        has_target=True, capped_flag=False,
        reason_code=RC.INACTIVE_METRIC.value)
    carrier = NormalizedFrame(rows=(), excluded=(dropped,))
    frame, stats = run(SEAM_NULL, normalized=carrier)
    got = by_sid(frame)
    assert got['S3'].pool_rank is None
    assert got['S3'].reject_reason == RC.INACTIVE_METRIC
    assert got['S3'].primary_pool_eligible is False
    assert got['S3'].pool_key == PoolKey(biz_domain='CARD', evidence_class='B')
    assert stats_by_pool(stats)[('CARD', 'B')].count == 2      # 仍计入分母
    assert stats_by_pool(stats)[('CARD', 'B')].share_in_pool == D('0.666666666667')
    stale = dropped.model_copy(update={'reason_code': RC.ANCHOR_SET_STALE.value})
    with pytest.raises(pooling.PoolingInputError):
        run(SEAM_NULL, normalized=NormalizedFrame(rows=(), excluded=(stale,)))


def test_models1_step7_pool_key_refuses_a_missing_evidence_class():
    """R7 严键（ORCH-29 第 4 条 / ORCH-32 第 4 条）：Step7 一律用完整
    (biz_domain x evidence_class)。evidence_class 缺失 = 无从举证属哪一池 ->
    显式抛（V-14），绝不把 None 当成第五类池去混排（P-6 / G-02 不松动）。"""
    with pytest.raises(pooling.PoolingInputError):
        pooling.step7_pool_key('CARD', None)
    assert pooling.step7_pool_key('CARD', 'C') == PoolKey(biz_domain='CARD',
                                                          evidence_class='C')
    assert pooling.step7_pool_key('CARD', 'C').evidence_class == 'C'


def test_seam1_incomparable_code_precedence_in_the_single_slot():
    """R6 的取码优先序：同一策略多枚标注时取 INACTIVE_METRIC > RANK_REVERSAL_RISK
    > SMALL_POOL（与 normalize 自己的单槽优先序一致，同一条 null 两模块读出同码）。
    手算：S3 两行标注 (M1 INACTIVE_METRIC, M2 SMALL_POOL) -> reject_reason =
    INACTIVE_METRIC；换序构造 (M1 SMALL_POOL, M2 RANK_REVERSAL_RISK) ->
    RANK_REVERSAL_RISK。"""
    frame, _ = run(SEAM_NULL, normalized=nframe(
        nrow('S3', 'M2', RC.SMALL_POOL.value),
        nrow('S3', 'M1', RC.INACTIVE_METRIC.value)))
    assert by_sid(frame)['S3'].reject_reason == RC.INACTIVE_METRIC
    frame2, _ = run(SEAM_NULL, normalized=nframe(
        nrow('S3', 'M1', RC.SMALL_POOL.value),
        nrow('S3', 'M2', RC.RANK_REVERSAL_RISK.value)))
    assert by_sid(frame2)['S3'].reject_reason == RC.RANK_REVERSAL_RISK
    assert by_sid(frame2)['S3'].pool_rank is None


def test_seam1_incomparable_outranks_the_evidence_gate_but_not_a_hard_hit():
    """R4 + R6 的单槽优先序：BLOCK 先于 WARN，WARN 内部「不可比」这一事实判定先于
    「即使可比也不准入」的政策判定（否则裁决要求的码会被门禁码盖掉，等于没承载）。

    手算 A：S3 改成 C 类 + null + RANK_REVERSAL_RISK 标注 -> reject_reason =
      RANK_REVERSAL_RISK（不是 PRIMARY_POOL_REJECTED_EVIDENCE），eligible False；
      池变为 (CARD,A) 1 / (CARD,B) 1 / (CARD,C) 1 / (LOAN,C) 1，CARD 域 3、全体 4
      -> 三个 CARD 池的 share_in_pool 都是 1/3 = 0.333333333333，share_overall 1/4。
    手算 B：S1 命中 HARD（grade_reason_path 带 GR_REDLINE_FORCED）+ null +
      SMALL_POOL 标注 -> reject_reason = REDLINE_HARD_HIT（BLOCK 压过 WARN），
      pool_rank = null，(CARD,A) 仍计 1 条进分母。
    """
    c_specs = (('S1', 'CARD', 'A', '0.90', 'L1'),
               ('S2', 'CARD', 'B', '0.80', 'L1'),
               ('S3', 'CARD', 'C', None, 'L2'),
               ('S4', 'LOAN', 'C', '0.95', 'L2'))
    frame, stats = run(c_specs, normalized=nframe(
        nrow('S3', 'M1', RC.RANK_REVERSAL_RISK.value, domain='CARD', cls='C')))
    got = by_sid(frame)
    assert got['S3'].reject_reason == RC.RANK_REVERSAL_RISK
    assert got['S3'].primary_pool_eligible is False
    assert got['S3'].pool_key.evidence_class == 'C'      # C 类仍禁入一级库（G-02）
    assert got['S4'].reject_reason == RC.PRIMARY_POOL_REJECTED_EVIDENCE
    rows = stats_by_pool(stats)
    for key in (('CARD', 'A'), ('CARD', 'B'), ('CARD', 'C')):
        assert rows[key].count == 1
        assert rows[key].share_in_pool == D('0.333333333333')
        assert rows[key].share_overall == D('0.25')

    hard_specs = (('S1', 'CARD', 'A', None, 'L4'),
                  ('S2', 'CARD', 'B', '0.80', 'L1'),
                  ('S3', 'CARD', 'B', '0.70', 'L2'),
                  ('S4', 'LOAN', 'C', '0.95', 'L2'))
    scores, grades, ev, master = parts(hard_specs)
    grades = [grade_row('S1', 'L4', path=(RC.GR_REDLINE_FORCED,))] + grades[1:]
    frame2, stats2 = go(scores, grades, ev, master,
                        normalized=nframe(nrow('S1', 'M1', RC.SMALL_POOL.value,
                                               domain='CARD', cls='A')))
    got2 = by_sid(frame2)
    assert got2['S1'].reject_reason == RC.REDLINE_HARD_HIT
    assert got2['S1'].pool_rank is None
    assert got2['S1'].primary_pool_eligible is False
    assert (got2['S2'].pool_rank, got2['S3'].pool_rank) == (1, 2)
    assert stats_by_pool(stats2)[('CARD', 'A')].count == 1     # 仍计入分母
    assert stats_by_pool(stats2)[('CARD', 'B')].share_in_pool == D('0.666666666667')
