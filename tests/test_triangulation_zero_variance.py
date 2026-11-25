'''B12-FIX · B2 守护 —— dsm/triangulation.py 零方差列的**显式降级**（缺陷位 :293）。

缺陷（真实生产阻断）：冻结 fixtures 的 M_AUM_MINOR 在 12 个主体上恒为 10000，min_max
归一后整列为 0，于是 GRA Step 2 的**两种**签认口径参考值都是 0（初值化取首值 0、均值化
取均值 0），`dimensionless` 按模块自述报错且「不回落成第三种口径（那是发明数值 R-12）」
-> `dsm score` 退出码 5。真实数据里恒定列很常见（诊断层本就有 INACTIVE / LOW_VARIATION
两个状态），所以这是缺陷不是夹具人工产物。

修法（红线之内）：**没有**发明第三种归一化口径，**没有**把恒定列悄悄当成 0 或 1 塞进去，
`dimensionless` 对零参考值照旧报错（本文件钉住）。降级落在 run() 一层：零方差列被从
**本次**三角比对的贡献中显式排除（TOPSIS 侧一并排除——恒定列 A+ == A-、对 D+/D- 的贡献
恒为 0，本就无信息），并带**已注册**原因码 INACTIVE_METRIC 进 report.flags。

复用的注册码与语义匹配理由：`dsm/reason_codes.py:59`
    ('INACTIVE_METRIC', 'WARN', '指标零变异，已剔除并预警', '指标负责人')
注册表措辞「指标零变异，已剔除并预警」逐字就是这里做的三件事（零变异 / 剔除 / 预警），
且 normalize.py:111 CODE_INACTIVE 与 [L943] 给**同一条**零变异归一化行落的正是这一枚
（tests/test_integration_spine.py:622-625 已钉），pooling.py:111 也把它列进
COMPARABILITY_CODES —— 三角验证沿用同一口径，不新注册码（reason_codes.py 单点，R-15；
all_codes() 计数被 tests 钉住，本包禁写该文件）。
**不**复用 SPEARMAN_ZERO_VARIANCE：那枚码的措辞绑定「一对排序零方差、Spearman 相关系数
无定义」，而这里恒定列被排除后三对 rho 完全可能全有定义，挪用即虚报。两枚码语义不重叠，
_flags() 各自独立出码（本文件两条断言分别钉住）。

披露落点（正文，非附录）：flags -> dsm/reports.py:585-607 `_section_8` 的
「- 三角标记：」一行（report.md ⑧ 段正文 + triangulation.md），另在
「- GRA 关联系数（metric_id -> 均值）：」一行可见地少掉被排除的列；处置链与
SPEARMAN_ZERO_VARIANCE 完全同构（模块出码 -> report.flags -> _section_8 正文）。

golden 全部手算（R-14，不抄实现输出）。SPEC_DEAD 的 M2 恒为 5：
  live 只剩 M1，metric_weights 照 [L954] 在参评指标上重归一 -> w(M1) = 1
  GRA 初值化 (2,4,8)/2 = (1,2,4)，x0 = 4，Δ = (3,2,0)，minΔ=0 maxΔ=3，ρ=1
    -> ξ = (0+1*3)/(Δ+1*3) = 3/(Δ+3) = (0.5, 0.6, 1)
    -> γ = w·ξ = (0.5, 0.6, 1)
  TOPSIS 单指标：C_i = (x_i - min)/(max - min) = (0, 1/3, 1)
  两法名次同为 S3=1 / S2=2 / S1=3；main = (0.5, 0.6, 1) 同序
    -> 三对 rho 全为 1，mean_rho = 1 >= 0.8 -> METHOD_AGREEMENT
  flags = (METHOD_AGREEMENT, INACTIVE_METRIC)   ← 没有 SPEARMAN_ZERO_VARIANCE
'''
from datetime import date
from decimal import Decimal

import pytest

from dsm import aggregate, numeric, triangulation
from dsm.models import (AttainmentFrame, AttainmentRow, NormalizedFrame, NormalizedRow,
                        PoolKey, ScoreFrame, ScoreRow, TriangulationReport,
                        WeightVersionDoc)
from dsm.numeric import D, ZERO, eq_tol
from dsm.reason_codes import RC, Severity, blocks_run, is_registered, severity
from dsm.reports import AllFrames, GateStatus, render_triangulation_md

PERIOD, VER = '2026Q1', 'v1'
POOL = PoolKey(biz_domain='RETAIL', evidence_class='A')
DIRS = {'M1': 1, 'M2': 1}
RC_AGREE = RC.METHOD_AGREEMENT.value
RC_INACTIVE = RC.INACTIVE_METRIC.value
RC_SPEAR = RC.SPEARMAN_ZERO_VARIANCE.value

# M2 恒为 0 —— 这正是**真实缺陷的形状**：M_AUM_MINOR 在 12 个主体上恒定，min_max 归一后
# 整列就是 0（tests/test_integration_spine.py:622-625 钉住了这批行的存在），于是 GRA
# Step 2 的两种签认口径参考值都是 0。M1 = (2,4,8) 与 SPEC_B 同形，golden 见文件头手算。
SPEC_DEAD = {'S1': {'M1': '2', 'M2': '0'}, 'S2': {'M1': '4', 'M2': '0'},
             'S3': {'M1': '8', 'M2': '0'}}
# 非零的恒定列：min_max 之外的情形（例如参考尺未退化但取值恒定）。它不会让
# dimensionless 报错，但同样**零方差、无区分度**，降级必须照样生效 —— 检测按值面判
# 方差，不是按「参考值是否为 0」判，这样两种成因走同一条处置。
SPEC_DEAD_NONZERO = {'S1': {'M1': '2', 'M2': '5'}, 'S2': {'M1': '4', 'M2': '5'},
                     'S3': {'M1': '8', 'M2': '5'}}
# 对照组：同一批 M1，M2 换成非常定列 -> 零方差降级不得触发（回归钉 e）。
SPEC_LIVE = {'S1': {'M1': '2', 'M2': '3'}, 'S2': {'M1': '4', 'M2': '12'},
             'S3': {'M1': '8', 'M2': '9'}}
# 全部指标都零方差：没有任何可比对的信息，必须显式拒绝而不是编数。
SPEC_ALL_DEAD = {'S1': {'M1': '7', 'M2': '5'}, 'S2': {'M1': '7', 'M2': '5'},
                 'S3': {'M1': '7', 'M2': '5'}}
WEIGHTS = {'D1': {'M1': D('0.5'), 'M2': D('0.5')}}
MAIN_DEAD = {'S1': '0.5', 'S2': '0.6', 'S3': '1'}


def key(sid, period=PERIOD, version=VER):
    return (sid, version, period)


def mat(spec):
    return {key(sid): {m: D(v) for m, v in sorted(row.items())}
            for sid, row in spec.items()}


def nframe(spec):
    rows = [NormalizedRow(strategy_id=sid, version_id=VER, period=PERIOD, metric_id=m,
                          pool_key=POOL, norm_value=D(v), method='min_max',
                          anchor_used=False,
                          reason_code=RC_INACTIVE if m == 'M2' and spec is SPEC_DEAD else None)
            for sid, row in spec.items() for m, v in sorted(row.items())]
    return NormalizedFrame(rows=tuple(rows))


def sframe(comps):
    return ScoreFrame(rows=tuple(
        ScoreRow(strategy_id=sid, version_id=VER, period=PERIOD, composite_absolute=D(c),
                 composite_relative=None, dim_absolute={}, dim_relative={}, coverage=D('1'),
                 weight_version_id='W2026', operator='LINEAR')
        for sid, c in sorted(comps.items())))


def wdoc():
    return WeightVersionDoc(weight_version_id='W2026', status='FROZEN',
                            effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
                            level1_weights={'D1': D('1')}, level2_weights=WEIGHTS,
                            approved_by='评价管理委员会', approved_date=date(2026, 1, 1))


def cfg(enabled=True, gra_norm='initial', rho='1', threshold='0.8'):
    return {'triangulation': {'enabled': enabled, 'gra_norm': gra_norm, 'rho': D(rho),
                              'divergence_threshold': D(threshold)}}


def run(spec, comps, **kwargs):
    return triangulation.run(sframe(comps), nframe(spec), wdoc(), cfg(**kwargs),
                             directions=DIRS)


def attainment(spec):
    rows = [AttainmentRow(strategy_id=sid, version_id=VER, period=PERIOD, metric_id=m,
                          attainment=D(v), direction=DIRS[m], target_source='budget',
                          has_target=True, capped_flag=False, reason_code=None)
            for sid, row in spec.items() for m, v in sorted(row.items())]
    return AttainmentFrame(rows=tuple(rows),
                           attainment_coverage={sid: D('1') for sid in spec})


# ---------------------------------------------------------------------------
# (c) 恒定列不再抛 TriangulationError，而是产出带注册码的显式降级 + 披露
# ---------------------------------------------------------------------------
def test_constant_column_degrades_explicitly_with_a_registered_code_instead_of_raising():
    report = run(SPEC_DEAD, MAIN_DEAD)          # 修复前：TriangulationError -> 退出码 5
    assert isinstance(report, TriangulationReport)
    assert RC_INACTIVE in report.flags, '降级必须带注册码，不静默（V-14）：' + str(report.flags)
    assert is_registered(RC_INACTIVE)
    assert severity(RC_INACTIVE) is Severity.WARN
    assert blocks_run(RC_INACTIVE) is False, '[L1022] 不入分 -> 不阻断本轮'
    # 手算 golden（文件头推导）：γ = (0.5, 0.6, 1)，两法名次一致 -> METHOD_AGREEMENT
    assert report.agreement == RC_AGREE
    assert eq_tol(report.rho_main_gra, D('1')) and eq_tol(report.rho_main_topsis, D('1'))
    assert eq_tol(report.mean_rho, D('1'))
    # 恒定列被排除后三对 rho 全有定义 -> **不得**顺手扣上 SPEARMAN_ZERO_VARIANCE（挪用即虚报）
    assert RC_SPEAR not in report.flags
    assert report.flags == (RC_AGREE, RC_INACTIVE)
    assert not triangulation.is_vetoed(report)


def test_the_exclusion_is_visible_in_the_report_body_not_only_in_an_appendix():
    '''披露落点核验：flags 里的码经 reports._section_8 落在正文「三角标记」行
    （report.md ⑧ 段 / triangulation.md 同一渲染函数），且被排除的列在
    「GRA 关联系数」一行可见地缺席。渲染层 dsm/reports.py 本包禁写，此处只读消费。'''
    report = run(SPEC_DEAD, MAIN_DEAD)
    assert sorted(report.gra_by_metric) == ['M1'], '被排除的 M2 必须可见地不在逐指标关联度里'
    assert eq_tol(report.gra_by_metric['M1'], numeric.mean([D('0.5'), D('0.6'), D('1')]))
    md = render_triangulation_md(AllFrames(
        gate_status=GateStatus(g5_dispute_source_review_signed=True,
                               g7_governance_config_signed=True),
        triangulation=report))
    assert '- 三角标记：' + RC_AGREE + '、' + RC_INACTIVE in md
    assert 'M2' not in md.split('GRA 关联系数')[1].split('\n')[0], '关联度行必须少掉 M2'
    # blocks_run 由注册表决定，不由渲染层拟（reason_codes.blocks_run 已在上一条钉住）
    assert blocks_run(RC_INACTIVE) is False


def test_both_signed_off_gra_norm_calibers_are_covered_by_the_same_degradation():
    '''SDD 723 的两种签认口径（initial / mean）在恒定列上参考值都是 0，降级必须对
    两者同样生效 —— 修法不许只挑一种口径绕过（那等于变相发明第三种口径）。'''
    for gra_norm in triangulation.GRA_NORM_METHODS:
        report = run(SPEC_DEAD, MAIN_DEAD, gra_norm=gra_norm)
        assert RC_INACTIVE in report.flags, gra_norm
        assert sorted(report.gra_by_metric) == ['M1'], gra_norm


def test_dimensionless_still_refuses_a_zero_reference_no_third_normalization():
    '''红线钉（R-14 不得弱化）：`dimensionless` 对零参考值照旧显式报错，两种口径都报。
    降级发生在 run() 的「排除该列」一层，绝不是给恒定列编一个归一化数值。'''
    zero_column = (ZERO, ZERO, ZERO)            # min_max 归一后的恒定列就是这个形状
    for method in triangulation.GRA_NORM_METHODS:
        with pytest.raises(triangulation.TriangulationError):
            triangulation.dimensionless(zero_column, method)
    with pytest.raises(triangulation.TriangulationError):
        triangulation.dimensionless((D('0'), D('0')), 'initial')
    with pytest.raises(triangulation.TriangulationError):
        triangulation.dimensionless((D('1'), D('2')), 'z_score')
    # 直接喂「归一后整列为 0」的矩阵给 GRA 也照旧报错：降级只发生在 run() 的比对层，
    # 公开函数的契约一行未改（既有 tests/test_triangulation.py:274 同时钉住 dimensionless）
    with pytest.raises(triangulation.TriangulationError):
        triangulation.gra_coefficients(mat(SPEC_DEAD), DIRS, D('1'), 'initial')
    # 非零的恒定列压根走不到那个报错（ref=5 != 0），但它同样零方差：降级照样生效
    assert triangulation.zero_variance_metrics(mat(SPEC_DEAD_NONZERO)) == ('M2',)
    report = run(SPEC_DEAD_NONZERO, MAIN_DEAD)
    assert RC_INACTIVE in report.flags and sorted(report.gra_by_metric) == ['M1']
    assert eq_tol(report.gra_by_metric['M1'], D('0.7')), '手算：γ(M1) = mean(0.5, 0.6, 1) = 0.7'


def test_a_wholly_constant_period_is_refused_explicitly_not_zero_filled():
    '''全部指标都零方差时没有任何可比对的信息：显式拒绝并点名注册码，绝不把恒定列
    当成 0 或 1 塞进去凑出一张表（R-12 / V-14）。'''
    with pytest.raises(triangulation.TriangulationError) as info:
        run(SPEC_ALL_DEAD, {'S1': '0.5', 'S2': '0.6', 'S3': '1'})
    message = str(info.value)
    assert RC_INACTIVE in message and 'M1' in message and 'M2' in message


# ---------------------------------------------------------------------------
# (d) 零方差列不得改变任何入分数值（score 面）
# ---------------------------------------------------------------------------
def test_the_zero_variance_degradation_never_touches_the_scoring_face():
    '''[L1348] 不入分的硬点，在**恒定列在场**时重钉一遍（既有
    tests/test_triangulation.py:326 只覆盖了非零方差数据）。对照组 = 同一批 M1、把 M2
    换成非常定列。判据：score 面只由入分链路的入参决定，与 triangulation 的开/关、
    与零方差降级是否触发**完全无关**；且 run() 不许改动任何入参（INV-3）。'''
    doc = wdoc()
    for spec in (SPEC_DEAD, SPEC_LIVE):
        attain, norm = attainment(spec), nframe(spec)
        before_scores = aggregate.compose(attain, norm, doc, cfg(enabled=True))
        before_norm = norm.model_dump()
        before_scores_dump = before_scores.model_dump()
        report = triangulation.run(before_scores, norm, doc, cfg(enabled=True),
                                   directions=DIRS)
        assert isinstance(report, TriangulationReport)
        assert (RC_INACTIVE in report.flags) is (spec is SPEC_DEAD)
        # 旁路跑完，入分面逐格不变；入参一个字节都没被改（INV-3）
        assert aggregate.compose(attain, norm, doc, cfg(enabled=True)) == before_scores
        assert before_scores.model_dump() == before_scores_dump
        assert norm.model_dump() == before_norm
        assert doc.model_dump() == wdoc().model_dump()
        # 开 / 关（enabled=false -> run() 返回 None）两路的 score 面逐格相同
        off = aggregate.compose(attain, norm, doc, cfg(enabled=False))
        assert off == before_scores and off.model_dump() == before_scores_dump
        assert triangulation.run(before_scores, norm, doc, cfg(enabled=False),
                                 directions=DIRS) is None


def test_the_degradation_is_real_not_a_no_op_that_hides_the_column():
    '''反向钉：降级必须真的改变了旁路输出（否则「不抛」可能只是把整条旁路悄悄吞掉）。
    对照组 M2 有方差 -> 不出码、逐指标关联度含 M2；实验组 M2 恒定 -> 出码、少掉 M2。'''
    dead = run(SPEC_DEAD, MAIN_DEAD)
    live = run(SPEC_LIVE, MAIN_DEAD)
    assert RC_INACTIVE not in live.flags and live.flags == (RC_AGREE,)
    assert sorted(live.gra_by_metric) == ['M1', 'M2']
    assert sorted(dead.gra_by_metric) == ['M1']
    assert dead.rows and live.rows
    assert {r.strategy_id for r in dead.rows} == {r.strategy_id for r in live.rows} == {'S1', 'S2', 'S3'}
    # 手算：live 的 M2 初值化 (3,12,9)/3 = (1,4,3)，ξ 与 γ 与 dead 不同 -> 降级确有后果
    assert not eq_tol(live.gra_by_metric['M1'], dead.gra_by_metric['M1']) or \
        sorted(live.gra_by_metric) != sorted(dead.gra_by_metric)


# ---------------------------------------------------------------------------
# (e) 非零方差场景行为完全不变（回归钉）+ 纯函数性质
# ---------------------------------------------------------------------------
def test_non_zero_variance_paths_are_bit_for_bit_unchanged():
    '''回归钉（R-14）：无零方差列时，检测器返回空、drop_metrics 原样复制、_flags 的
    dropped 默认参数让既有元组逐位不变，run() 的 golden 与既有手算一致。'''
    assert triangulation.zero_variance_metrics(mat(SPEC_LIVE)) == ()
    assert triangulation.zero_variance_metrics(mat(SPEC_DEAD)) == ('M2',)
    assert triangulation.zero_variance_metrics(mat(SPEC_ALL_DEAD)) == ('M1', 'M2')
    original = mat(SPEC_LIVE)
    copy = triangulation.drop_metrics(original, ())
    assert copy == original and copy is not original
    assert all(copy[k] is not original[k] for k in original), '必须返回副本，入参只读（INV-3）'
    dropped = triangulation.drop_metrics(original, ('M2',))
    assert all(sorted(row) == ['M1'] for row in dropped.values())
    assert all(sorted(row) == ['M1', 'M2'] for row in original.values()), '入参被改了'
    report = run(SPEC_LIVE, MAIN_DEAD)
    assert report.flags == (RC_AGREE,)          # 与既有 tests 钉的口径逐字一致
    # SPEC_LIVE 的手算 golden（与 tests/test_triangulation.py:209 同一构造、同一推导）
    xi, x0 = triangulation.gra_coefficients(mat(SPEC_LIVE), DIRS, D('1'), 'initial')
    assert eq_tol(x0['M1'], D('4')) and eq_tol(x0['M2'], D('4'))
    assert eq_tol(xi[key('S2')]['M1'], D('0.6')) and eq_tol(xi[key('S2')]['M2'], D('1'))


def test_spearman_zero_variance_and_inactive_metric_stay_two_distinct_codes():
    '''两枚码语义不重叠：main 排序零方差（Spearman 无定义）+ 指标列零方差（剔除）同时
    发生时，两枚码都要出；只有其一时只出其一。杜绝「挪用一枚顶另一枚」的虚报。'''
    flat_main = {'S1': '0.5', 'S2': '0.5', 'S3': '0.5'}
    both = run(SPEC_DEAD, flat_main)
    assert RC_SPEAR in both.flags and RC_INACTIVE in both.flags
    assert both.agreement is None and both.mean_rho is None
    only_spear = run(SPEC_LIVE, flat_main)
    assert only_spear.flags == (RC_SPEAR,) and RC_INACTIVE not in only_spear.flags
    only_inactive = run(SPEC_DEAD, MAIN_DEAD)
    assert only_inactive.flags == (RC_AGREE, RC_INACTIVE)
    assert severity(RC_INACTIVE) is Severity.WARN and severity(RC_SPEAR) is Severity.WARN
