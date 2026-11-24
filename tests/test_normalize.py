'''D3 normalize.py -- guard tests G-05 / P-4 (digest M43, SDD 935-946 / 1407 / 1428).

四条硬点各有归属：
  1) 只用于排名不用于门槛 -> test_p4_grade_gate_consumes_the_absolute_track_only
  2) 池内归一 / 跨池混算即错 -> test_pool_local_normalisation_is_not_the_merged_pool
  3) 锚定集 -> test_changing_the_anchor_set_changes_the_norm_values 及两条退化用例
  4) 三方法显式切换 -> test_method_switch_is_explicit_never_inferred 等
所有 golden 期望值都来自构造与手算（R-14），输入一律用 pydantic 构造（R-2）。
'''
import inspect
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import BaseModel, ConfigDict

from dsm import grading, normalize
from dsm.models import (AnchorSetDoc, AttainmentFrame, AttainmentRow,
                        MetricDictRow, NormalizedFrame, NormalizedRow, PoolKey)
from dsm.numeric import D, eq_tol
from dsm.reason_codes import RC

POOL_A = PoolKey(biz_domain='RETAIL', evidence_class='A')
POOL_B = PoolKey(biz_domain='WHOLESALE', evidence_class='B')
PERIOD = '2026Q1'
CFG_BLOCK = {'method': 'z_score', 'min_pool_size': 3, 'on_zero': None, 'sd_dof': 0}


# --------------------------------------------------------------------------
# 构造器：字段名逐字抄 dsm/models.py
# --------------------------------------------------------------------------
def metric(mid, direction=1):
    return MetricDictRow(
        metric_id=mid, metric_name=mid, dim_code='DIM1', numerator_def='num',
        denominator_def='den', time_window='M1', dedup_rule='NONE',
        missing_rule='SKIP', outlier_rule='NONE',
        attainment_formula='RATIO_DIRECT', direction=direction, unit='RATIO',
        target_value=D('1.0'), target_basis='budget', is_redline=False,
        owner_name='owner', signoff_status='SIGNED', signoff_date=None,
        dim_signoff_status='SIGNED', dict_version='dv1', caliber_version='cv1')


def fact(sid, mid, value, period=PERIOD, direction=1, version='v1'):
    return AttainmentRow(
        strategy_id=sid, version_id=version, period=period, metric_id=mid,
        attainment=value, direction=direction, target_source='budget',
        has_target=True, capped_flag=False, reason_code=None)


def anchor(ids, aid='AS-2026'):
    return AnchorSetDoc(
        anchor_set_id=aid, strategy_ids=tuple(ids), effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
        rationale='baseline cohort signed off by the evaluation office')


def prm(method='min_max', min_pool_size=1, on_zero=D('0'), sd_dof=1):
    return normalize.NormalizeParams(
        method=method, min_pool_size=min_pool_size, on_zero=on_zero, sd_dof=sd_dof)


def pool_map(ids, key=POOL_A):
    return {sid: key for sid in ids}


def by_strategy(frame, mid='M1'):
    return {r.strategy_id: r for r in frame.rows if r.metric_id == mid}


def norm_of(frame, mid='M1'):
    return {r.strategy_id: r.norm_value for r in frame.rows if r.metric_id == mid}


class _Cfg(BaseModel):
    '''params_from_config 只读 config.eval_config，这里用最小 pydantic 替身。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    eval_config: dict


BASE = [fact('S1', 'M1', D('0.8')), fact('S2', 'M1', D('1.0')),
        fact('S3', 'M1', D('1.2')), fact('S4', 'M1', D('0.9'))]
BASE_IDS = ('S1', 'S2', 'S3', 'S4')
EXTREME = fact('S9', 'M1', D('99.0'))


# --------------------------------------------------------------------------
# G-05 [L1407]：新增极端策略（不入锚定集）后，存量策略的 norm 完全不变
# --------------------------------------------------------------------------
def test_g05_min_max_anchor_scale_ignores_a_new_extreme_strategy():
    a = anchor(('S1', 'S2', 'S3'))
    base = normalize.compute(BASE, [metric('M1')], a, params=prm('min_max'),
                             pools=pool_map(BASE_IDS))
    # 锚定尺 lo=0.8 hi=1.2 width=0.4 -> 手算 0 / 0.5 / 1.0 / 0.25
    want = {'S1': D('0.0'), 'S2': D('0.5'), 'S3': D('1.0'), 'S4': D('0.25')}
    got = norm_of(base)
    for sid, expect in want.items():
        assert eq_tol(got[sid], expect)
    for row in base.rows:
        assert row.anchor_used is True
        assert row.reason_code is None

    pools2 = pool_map(BASE_IDS + ('S9',))
    after = normalize.compute(BASE + [EXTREME], [metric('M1')], a,
                              params=prm('min_max'), pools=pools2)
    rows_after = by_strategy(after)
    # (99.0-0.8)/0.4 = 245.5：锚定尺不裁剪，极端值被显式暴露在相对轨上
    assert eq_tol(rows_after['S9'].norm_value, D('245.5'))
    for row in base.rows:
        assert rows_after[row.strategy_id] == row  # 整行完全不变


def test_g05_z_score_and_rank_percentile_are_anchor_scale_invariant():
    facts = BASE + [fact('S5', 'M1', D('1.4'))]
    ids = BASE_IDS + ('S5',)
    pools2 = pool_map(ids + ('S9',))
    cases = (('z_score', anchor(('S1', 'S2', 'S3')), prm('z_score', sd_dof=1)),
             ('rank_percentile', anchor(('S1', 'S2', 'S3', 'S5')),
              prm('rank_percentile')))
    for name, a, p in cases:
        base = normalize.compute(facts, [metric('M1')], a, params=p,
                                 pools=pool_map(ids))
        after = normalize.compute(facts + [EXTREME], [metric('M1')], a, params=p,
                                  pools=pools2)
        rows_after = by_strategy(after)
        for row in base.rows:
            assert rows_after[row.strategy_id] == row, name


# --------------------------------------------------------------------------
# P-4 [L1428]：锚定不变性（属性）+ 等级门槛只吃绝对轨
# --------------------------------------------------------------------------
@settings(max_examples=25, deadline=None)
@given(extra=st.lists(st.decimals(min_value=0, max_value=50, places=3,
                                  allow_nan=False, allow_infinity=False),
                      min_size=1, max_size=4))
def test_p4_adding_non_anchor_strategies_keeps_existing_norms(extra):
    facts = BASE + [fact('S5', 'M1', D('1.4'))]
    ids = BASE_IDS + ('S5',)
    for method, a in (('min_max', anchor(('S1', 'S2', 'S3'))),
                      ('z_score', anchor(('S1', 'S2', 'S3'))),
                      ('rank_percentile', anchor(('S1', 'S2', 'S3', 'S5')))):
        p = prm(method, sd_dof=1)
        base = normalize.compute(facts, [metric('M1')], a, params=p,
                                 pools=pool_map(ids))
        newcomers = [fact('N' + str(i), 'M1', D(v)) for i, v in enumerate(extra)]
        grown = pool_map(ids + tuple('N' + str(i) for i in range(len(extra))))
        after = normalize.compute(facts + newcomers, [metric('M1')], a, params=p,
                                  pools=grown)
        rows_after = by_strategy(after)
        for row in base.rows:
            assert eq_tol(rows_after[row.strategy_id].norm_value, row.norm_value)
            assert rows_after[row.strategy_id].anchor_used is True


def test_p4_grade_gate_consumes_the_absolute_track_only():
    '''硬点 1：相对轨与绝对轨是两条独立数据路径，等级门槛拿不到 norm。'''
    for fn in (grading.plan, grading.assign):
        for p in inspect.signature(fn).parameters.values():
            assert 'Normalized' not in str(p.annotation)
    assert not ({'grade', 'attainment', 'attainment_floor', 'capped_flag'}
                & set(NormalizedRow.model_fields))
    assert not [n for n in vars(normalize)
                if not n.startswith('_')
                and ('grade' in n.lower() or 'floor' in n.lower())]
    frame = normalize.compute(BASE, [metric('M1')], anchor(('S1', 'S2', 'S3')),
                              params=prm('min_max'), pools=pool_map(BASE_IDS))
    with pytest.raises(grading.GradingInputError):
        grading.plan(frame, None, None, None, None, None)


# --------------------------------------------------------------------------
# 硬点 4：三方法各自独立可测，切换必须显式
# --------------------------------------------------------------------------
def test_z_score_golden_values_and_sd_dof_is_honoured():
    a = anchor(('S1', 'S2', 'S3'))
    got = norm_of(normalize.compute(BASE, [metric('M1')], a,
                                    params=prm('z_score', sd_dof=1),
                                    pools=pool_map(BASE_IDS)))
    # mean=1.0 ss=0.08 var=0.08/2=0.04 sd=0.2 -> 手算 -1 / 0 / 1 / -0.5
    want = {'S1': D('-1'), 'S2': D('0'), 'S3': D('1'), 'S4': D('-0.5')}
    for sid, expect in want.items():
        assert eq_tol(got[sid], expect)
    pop = norm_of(normalize.compute(BASE, [metric('M1')], a,
                                    params=prm('z_score', sd_dof=0),
                                    pools=pool_map(BASE_IDS)))
    assert eq_tol(pop['S2'], D('0'))
    assert eq_tol(pop['S1'], -pop['S3'])          # 对称
    assert abs(pop['S1']) > abs(got['S1'])        # 总体 sd 更小 -> z 更大


def test_rank_percentile_golden_values_average_ties():
    a = anchor(('S1', 'S2', 'S3', 'S5'))
    facts = BASE + [fact('S5', 'M1', D('1.4'))]
    got = norm_of(normalize.compute(facts, [metric('M1')], a,
                                    params=prm('rank_percentile'),
                                    pools=pool_map(BASE_IDS + ('S5',))))
    # 参考分布 0.8/1.0/1.2/1.4，n=4 -> (#less + 0.5*#equal)/4，全部手算
    want = {'S1': D('0.125'), 'S2': D('0.375'), 'S3': D('0.625'),
            'S4': D('0.25'), 'S5': D('0.875')}
    for sid, expect in want.items():
        assert eq_tol(got[sid], expect)


def test_method_switch_is_explicit_never_inferred():
    a = anchor(('S1', 'S2', 'S3'))
    kw = dict(pools=pool_map(BASE_IDS))
    md = [metric('M1')]
    with pytest.raises(normalize.NormalizeError):
        normalize.compute(BASE, md, a, **kw)          # 既无 config 也无 params
    with pytest.raises(normalize.NormalizeError):     # 两者都给 = 两种读法
        normalize.compute(BASE, md, a, _Cfg(eval_config={'normalize': CFG_BLOCK}),
                          params=prm('min_max'), **kw)
    with pytest.raises(Exception):                    # 三方法之外没有第四种
        normalize.NormalizeParams(method='minmax', min_pool_size=1,
                                  on_zero=D('0'), sd_dof=1)
    shapes = {}
    for m in ('min_max', 'z_score', 'rank_percentile'):
        frame = normalize.compute(BASE, md, a, params=prm(m, sd_dof=1), **kw)
        shapes[m] = norm_of(frame)
        assert all(row.method == m for row in frame.rows)
    assert shapes['min_max'] != shapes['z_score']
    assert shapes['z_score'] != shapes['rank_percentile']
    assert shapes['min_max'] != shapes['rank_percentile']


def test_zero_variance_metric_is_inactive_and_never_rescaled_silently():
    flat = [fact('S1', 'M1', D('1.0')), fact('S2', 'M1', D('1.0')),
            fact('S3', 'M1', D('1.0'))]
    ids = ('S1', 'S2', 'S3')
    a = anchor(ids)
    for method in ('min_max', 'z_score', 'rank_percentile'):
        tagged = normalize.compute(flat, [metric('M1')], a,
                                   params=prm(method, on_zero=D('0')),
                                   pools=pool_map(ids))
        assert {r.reason_code for r in tagged.rows} == {RC.INACTIVE_METRIC.value}
        assert all(eq_tol(r.norm_value, D('0')) for r in tagged.rows)
        dropped = normalize.compute(flat, [metric('M1')], a,
                                    params=prm(method, on_zero=None),
                                    pools=pool_map(ids))
        assert dropped == NormalizedFrame(rows=())   # on_zero=None -> 剔除，不编值


# --------------------------------------------------------------------------
# 硬点 2：池内归一，跨池混算即错
# --------------------------------------------------------------------------
def test_pool_local_normalisation_is_not_the_merged_pool():
    facts = [fact('S1', 'M1', D('0.8')), fact('S2', 'M1', D('1.0')),
             fact('S3', 'M1', D('1.2')), fact('T1', 'M1', D('2.0')),
             fact('T2', 'M1', D('3.0')), fact('T3', 'M1', D('4.0'))]
    md = [metric('M1')]
    no_anchor = anchor(())
    split = pool_map(('S1', 'S2', 'S3'), POOL_A)
    split.update(pool_map(('T1', 'T2', 'T3'), POOL_B))
    per_pool = normalize.compute(facts, md, no_anchor, params=prm('min_max'),
                                 pools=split)
    # 两池各自归一：每池都是 0 / 0.5 / 1.0（手算）
    want = {'S1': D('0'), 'S2': D('0.5'), 'S3': D('1'),
            'T1': D('0'), 'T2': D('0.5'), 'T3': D('1')}
    got = norm_of(per_pool)
    for sid, expect in want.items():
        assert eq_tol(got[sid], expect)
    for row in per_pool.rows:
        assert row.pool_key == split[row.strategy_id]

    merged = pool_map(('S1', 'S2', 'S3', 'T1', 'T2', 'T3'), POOL_A)
    cross = norm_of(normalize.compute(facts, md, no_anchor, params=prm('min_max'),
                                      pools=merged))
    # 合并后 lo=0.8 hi=4.0 width=3.2 -> S2=(1.0-0.8)/3.2=0.0625，与 0.5 不同
    assert eq_tol(cross['S2'], D('0.0625'))
    assert any(not eq_tol(cross[s], got[s]) for s in got)


def test_pool_membership_is_required_and_validated():
    md = [metric('M1')]
    a = anchor(('S1', 'S2', 'S3'))
    with pytest.raises(normalize.NormalizeInputError):
        normalize.compute(BASE, md, a, params=prm('min_max'),
                          pools=pool_map(('S1', 'S2', 'S3')))     # 缺 S4
    with pytest.raises(normalize.NormalizeInputError):
        normalize.compute(BASE, md, a, params=prm('min_max'), pools=None)
    with pytest.raises(normalize.NormalizeInputError):
        normalize.compute(BASE, [metric('M2')], a, params=prm('min_max'),
                          pools=pool_map(BASE_IDS))                # 字典外指标
    with pytest.raises(normalize.NormalizeInputError):
        normalize.compute(BASE, [metric('M1', direction=-1)], a,
                          params=prm('min_max'), pools=pool_map(BASE_IDS))
    with pytest.raises(normalize.NormalizeInputError):
        normalize.compute(BASE, md, None, params=prm('min_max'),
                          pools=pool_map(BASE_IDS))                # 锚定集必须显式给


# --------------------------------------------------------------------------
# 硬点 3：锚定集变化 -> 结果变化；退化情形有明确定义
# --------------------------------------------------------------------------
def test_changing_the_anchor_set_changes_the_norm_values():
    md = [metric('M1')]
    kw = dict(pools=pool_map(BASE_IDS))
    wide = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2', 'S3')),
                                     params=prm('min_max'), **kw))
    narrow = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2')),
                                       params=prm('min_max'), **kw))
    # 锚定尺 0.8~1.2 vs 0.8~1.0：S3 从 1.0 变成 2.0，S4 从 0.25 变成 0.5
    assert eq_tol(narrow['S3'], D('2.0'))
    assert eq_tol(narrow['S4'], D('0.5'))
    assert wide != narrow
    z_wide = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2', 'S3')),
                                       params=prm('z_score', sd_dof=1), **kw))
    z_narrow = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2')),
                                         params=prm('z_score', sd_dof=1), **kw))
    assert z_wide != z_narrow
    r_wide = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2', 'S3')),
                                       params=prm('rank_percentile'), **kw))
    r_narrow = norm_of(normalize.compute(BASE, md, anchor(('S1', 'S2')),
                                         params=prm('rank_percentile'), **kw))
    assert r_wide != r_narrow


def test_empty_anchor_set_falls_back_and_discloses_the_reversal_risk():
    md = [metric('M1')]
    base = normalize.compute(BASE, md, anchor(()), params=prm('min_max'),
                             pools=pool_map(BASE_IDS))
    assert {r.reason_code for r in base.rows} == {RC.ANCHOR_SET_STALE.value}
    assert all(r.anchor_used is False for r in base.rows)
    # 回退当期池内统计：lo=0.8 hi=1.2 -> 不是原值直传
    assert eq_tol(norm_of(base)['S4'], D('0.25'))
    assert not eq_tol(norm_of(base)['S1'], D('0.8'))
    grown = pool_map(BASE_IDS + ('S9',))
    after = normalize.compute(BASE + [EXTREME], md, anchor(()),
                              params=prm('min_max'), pools=grown)
    moved = by_strategy(after)
    # 锚定集为空 -> 秩反转真实发生：S2 由 0.5 掉到 (1.0-0.8)/(99.0-0.8)
    assert not eq_tol(moved['S2'].norm_value, D('0.5'))
    assert eq_tol(moved['S2'].norm_value, D('0.2') / D('98.2'))
    assert {r.reason_code for r in after.rows} == {RC.ANCHOR_SET_STALE.value}


def test_single_element_anchor_set_is_defined_not_a_passthrough():
    md = [metric('M1')]
    a = anchor(('S2',))                       # 锚定集只有一个成员：尺退化
    got = normalize.compute(BASE, md, a, params=prm('min_max'),
                            pools=pool_map(BASE_IDS))
    assert {r.reason_code for r in got.rows} == {RC.RANK_REVERSAL_RISK.value}
    assert all(r.anchor_used is False for r in got.rows)
    raw = {r.strategy_id: r.attainment for r in BASE}
    for row in got.rows:                      # 不得静默返回原值
        assert not eq_tol(row.norm_value, raw[row.strategy_id])
    assert eq_tol(norm_of(got)['S4'], D('0.25'))   # 回退到池内尺 0.8~1.2
    z = normalize.compute(BASE, md, a, params=prm('z_score', sd_dof=1),
                          pools=pool_map(BASE_IDS))
    assert {r.reason_code for r in z.rows} == {RC.RANK_REVERSAL_RISK.value}
    assert all(r.anchor_used is False for r in z.rows)


def test_small_pool_is_tagged_below_min_pool_size():
    md = [metric('M1')]
    a = anchor(('S1', 'S2', 'S3'))
    small = normalize.compute(BASE, md, a, params=prm('min_max', min_pool_size=6),
                              pools=pool_map(BASE_IDS))
    assert {r.reason_code for r in small.rows} == {RC.SMALL_POOL.value}
    ok = normalize.compute(BASE, md, a, params=prm('min_max', min_pool_size=4),
                           pools=pool_map(BASE_IDS))
    assert all(r.reason_code is None for r in ok.rows)


# --------------------------------------------------------------------------
# 输入契约与配置显式性
# --------------------------------------------------------------------------
def test_null_attainment_rows_are_skipped_not_imputed():
    md = [metric('M1')]
    a = anchor(('S1', 'S2', 'S3'))
    facts = BASE + [fact('S5', 'M1', None)]
    frame = normalize.compute(facts, md, a, params=prm('min_max'),
                              pools=pool_map(BASE_IDS + ('S5',)))
    assert 'S5' not in by_strategy(frame)
    assert len(frame.rows) == 4
    assert isinstance(frame, NormalizedFrame)
    assert frame == NormalizedFrame(rows=tuple(sorted(frame.rows, key=lambda r: (
        r.strategy_id, r.version_id, r.period, r.metric_id))))
    wrapped = normalize.compute(
        AttainmentFrame(rows=tuple(BASE), attainment_coverage={'S1': D('1')}),
        md, a, params=prm('min_max'), pools=pool_map(BASE_IDS))
    assert isinstance(wrapped, NormalizedFrame)
    assert len(wrapped.rows) == 4


def test_params_from_config_demands_an_explicit_normalize_block():
    p = normalize.params_from_config(_Cfg(eval_config={'normalize': CFG_BLOCK}))
    assert p.method == 'z_score' and p.min_pool_size == 3 and p.sd_dof == 0
    assert p.on_zero is None
    with pytest.raises(normalize.NormalizeConfigError):
        normalize.params_from_config(_Cfg(eval_config={}))
    partial = dict(CFG_BLOCK)
    partial.pop('method')                     # 方法永不默认，也不由数据形状推断
    with pytest.raises(normalize.NormalizeConfigError):
        normalize.params_from_config(_Cfg(eval_config={'normalize': partial}))
    with pytest.raises(Exception):
        normalize.NormalizeParams(method='min_max', min_pool_size=0,
                                  on_zero=D('0'), sd_dof=1)
    with pytest.raises(Exception):
        normalize.NormalizeParams(method='min_max', min_pool_size=1,
                                  on_zero=D('0'), sd_dof=2)
