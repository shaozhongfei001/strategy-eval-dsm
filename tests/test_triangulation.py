'''D4 triangulation.py -- 守护测试 T-TOP-01~03 / T-GRA-01~03 / T-TRI-01
（digest M12-triangulation，SDD 698-741 与 1022-1032）。

四条硬点各有归属：
  1) 不入分      -> test_t_tri_01_scores_and_grades_identical_with_triangulation_on_and_off
  2) 可关开关    -> test_t_tri_01_disabled_switch_emits_no_output_object
  3) 否决权      -> test_t_tri_01_veto_is_boolean_only_and_not_compensable
  4) 三个 Spearman -> test_t_tri_01_three_spearman_pairs_golden_with_average_ranks
所有 golden 期望值都来自构造与手算（R-14），输入一律用 pydantic 构造（R-2）。
'''
from dataclasses import fields as dc_fields
from datetime import date
from decimal import Decimal

import pytest

from dsm import aggregate, grading, numeric, triangulation
from dsm.models import (AttainmentFrame, AttainmentRow, EvidenceFrame, EvidenceRow,
                        GradeRuleRow, NormalizedFrame, NormalizedRow, PoolKey,
                        RedlineFrame, ScoreFrame, ScoreRow, TriangulationReport,
                        TriangulationStrategyRow, WeightVersionDoc)
from dsm.numeric import D, ZERO, eq_tol
from dsm.reason_codes import RC, Severity, severity

PERIOD = '2026Q1'
PERIOD2 = '2026Q2'
VER = 'v1'
POOL = PoolKey(biz_domain='RETAIL', evidence_class='A')
DIRS_UP = {'M1': 1, 'M2': 1}
RC_DISABLED = RC.TRIANGULATION_DISABLED.value
RC_AGREE = RC.METHOD_AGREEMENT.value
RC_DIVERGE = RC.METHOD_DIVERGENCE.value


# --------------------------------------------------------------------------
# 构造器：字段名逐字抄 dsm/models.py（R-2）
# --------------------------------------------------------------------------
def key(sid, period=PERIOD, version=VER):
    return (sid, version, period)


def mat(spec, period=PERIOD):
    '''{sid: {metric: 值}} -> run() 用的矩阵（键是定位三元组）。'''
    return {key(sid, period): {m: D(v) for m, v in sorted(row.items())}
            for sid, row in spec.items()}


def nframe(spec, period=PERIOD):
    rows = [NormalizedRow(strategy_id=sid, version_id=VER, period=period,
                          metric_id=m, pool_key=POOL, norm_value=D(v),
                          method='min_max', anchor_used=False, reason_code=None)
            for sid, row in spec.items() for m, v in sorted(row.items())]
    return NormalizedFrame(rows=tuple(rows))


def sframe(comps, period=PERIOD):
    rows = [ScoreRow(strategy_id=sid, version_id=VER, period=period,
                     composite_absolute=None if c is None else D(c),
                     composite_relative=None, dim_absolute={}, dim_relative={},
                     coverage=D('1'), weight_version_id='W2026', operator='LINEAR')
            for sid, c in comps.items()]
    return ScoreFrame(rows=tuple(rows))


def wdoc(level2, level1=None):
    dims = level1 if level1 is not None else {d: D('1') for d in level2}
    return WeightVersionDoc(
        weight_version_id='W2026', status='FROZEN', effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31), level1_weights=dims, level2_weights=level2,
        approved_by='评价管理委员会', approved_date=date(2026, 1, 1))


def cfg(enabled=True, rho='1', threshold='0.8', gra_norm='initial', **overrides):
    block = {'enabled': enabled, 'gra_norm': gra_norm}
    if rho is not None:
        block['rho'] = D(rho)
    if threshold is not None:
        block['divergence_threshold'] = D(threshold)
    block.update(overrides)
    return {'triangulation': block}


def weights_of(matrix, level2, level1=None):
    return triangulation.metric_weights(matrix, wdoc(level2, level1))


# 两个矩阵，全部 golden 都建立在它们上面（手算，R-14）。
# A：单指标，列平方和 0.25 -> 向量标准化后 r = (0.48, 0.64, 0.60)，全为精确小数。
SPEC_A = {'S1': {'M1': '0.24'}, 'S2': {'M1': '0.32'}, 'S3': {'M1': '0.30'}}
W_A = {'D1': {'M1': D('1')}}
# B：两指标，初值化后差序列全为精确小数（ρ=1 时 ξ = 3/(Δ+3)）。
SPEC_B = {'S1': {'M1': '2', 'M2': '3'}, 'S2': {'M1': '4', 'M2': '12'},
          'S3': {'M1': '8', 'M2': '9'}}
W_B = {'D1': {'M1': D('0.5'), 'M2': D('0.5')}}


# --------------------------------------------------------------------------
# T-TOP-01：TOPSIS 公式（SDD 709-718）golden
# --------------------------------------------------------------------------
def test_t_top_01_topsis_two_strategies_golden_is_exact():
    '''手算：r=(0.6,0.8)/(0.8,0.6)，w=(0.6,0.4) -> v: S1=(0.36,0.32) S2=(0.48,0.24)
    A+=(0.48,0.32) A-=(0.36,0.24)；D: S1=(0.12,0.08) S2=(0.08,0.12)
    -> C1=0.08/0.20=0.4，C2=0.12/0.20=0.6。'''
    matrix = {'S1': {'M1': D('3'), 'M2': D('4')}, 'S2': {'M1': D('4'), 'M2': D('3')}}
    w = weights_of(matrix, {'D1': {'M1': D('0.6'), 'M2': D('0.4')}})
    assert eq_tol(w['M1'], D('0.6')) and eq_tol(w['M2'], D('0.4'))
    keys, metrics = tuple(sorted(matrix)), ('M1', 'M2')
    assert eq_tol(w['M1'] + w['M2'], D('1'))  # SDD 954 口径：重归一到 1
    weighted = triangulation.weighted_matrix(matrix, w, keys, metrics)
    a_plus, a_minus = triangulation.ideal_solutions(weighted, DIRS_UP)
    assert eq_tol(a_plus['M1'], D('0.48')) and eq_tol(a_plus['M2'], D('0.32'))
    assert eq_tol(a_minus['M1'], D('0.36')) and eq_tol(a_minus['M2'], D('0.24'))
    close = triangulation.topsis_closeness(matrix, w, DIRS_UP)
    assert eq_tol(close['S1'], D('0.4')) and eq_tol(close['S2'], D('0.6'))
    assert triangulation.rank_desc(close) == {'S1': 2, 'S2': 1}  # SDD 717 降序
    # Step 7：输出前 q12，可复现
    assert all(value == numeric.q12(value) for value in close.values())


def test_t_top_01_closeness_is_the_range_ratio_on_one_metric():
    '''单指标时 C_i 就是 (x_i - min)/(max - min)：手算 (0, 1, 0.75)。'''
    matrix = mat(SPEC_A)
    w = weights_of(matrix, W_A)
    close = triangulation.topsis_closeness(matrix, w, DIRS_UP)
    assert eq_tol(close[key('S1')], ZERO)
    assert eq_tol(close[key('S2')], D('1'))
    assert eq_tol(close[key('S3')], D('0.75'))  # 0.12 / 0.16
    assert triangulation.rank_desc(close) == {key('S2'): 1, key('S3'): 2, key('S1'): 3}
    assert all(ZERO <= c <= D('1') for c in close.values())  # SDD 716 C ∈ [0,1]


# --------------------------------------------------------------------------
# T-TOP-02：负向指标翻转理想解；退化与零分母
# --------------------------------------------------------------------------
def test_t_top_02_negative_direction_flips_the_ideal_solution():
    '''direction = -1 时 A+ 取 min、A- 取 max（SDD 713-714），名次随之反转：
    手算 C = (1, 0, 0.25)，而正向是 (0, 1, 0.75)。'''
    matrix = mat(SPEC_A)
    w = weights_of(matrix, W_A)
    keys, metrics = tuple(sorted(matrix)), ('M1',)
    weighted = triangulation.weighted_matrix(matrix, w, keys, metrics)
    plus, minus = triangulation.ideal_solutions(weighted, {'M1': -1})
    assert eq_tol(plus['M1'], D('0.48')) and eq_tol(minus['M1'], D('0.64'))
    close = triangulation.topsis_closeness(matrix, w, {'M1': -1})
    assert eq_tol(close[key('S1')], D('1'))
    assert eq_tol(close[key('S2')], ZERO)
    assert eq_tol(close[key('S3')], D('0.25'))  # 0.04 / 0.16
    assert triangulation.rank_desc(close) == {key('S1'): 1, key('S3'): 2, key('S2'): 3}
    with pytest.raises(triangulation.DirectionRequiredError):
        triangulation.topsis_closeness(matrix, w, {'M9': 1})


def test_t_top_02_identical_strategies_tie_at_rank_one():
    '''全部策略取值相同：A+ = A-，D+ = D- = 0 -> safe_div 的 on_zero=ZERO，
    贴近度记 0，全体并列第 1（不发明名次，也不抛错）。'''
    matrix = {'S1': {'M1': D('2'), 'M2': D('5')}, 'S2': {'M1': D('2'), 'M2': D('5')}}
    w = weights_of(matrix, {'D1': {'M1': D('0.5'), 'M2': D('0.5')}})
    close = triangulation.topsis_closeness(matrix, w, DIRS_UP)
    assert eq_tol(close['S1'], ZERO) and eq_tol(close['S2'], ZERO)
    assert triangulation.rank_desc(close) == {'S1': 1, 'S2': 1}
    # GRA 在这种输入下 genuinely undefined：差序列全 0，报错而不是写死成 1
    with pytest.raises(triangulation.TriangulationError):
        triangulation.gra_coefficients(matrix, DIRS_UP, D('1'), 'initial')


def test_t_top_02_zero_column_goes_through_safe_div_on_zero():
    '''整列为 0 时向量标准化的分母为 0，走 safe_div(on_zero=ZERO)：该列 r 全 0，
    对距离无贡献，其余指标的 C 与单指标手算值一致（0, 1, 0.75）。'''
    spec = {'S1': {'M1': '0.24', 'M2': '0'}, 'S2': {'M1': '0.32', 'M2': '0'},
            'S3': {'M1': '0.30', 'M2': '0'}}
    matrix = mat(spec)
    assert eq_tol(triangulation.vector_normalize([D('0'), D('0')])[0], ZERO)
    w = weights_of(matrix, W_B)
    close = triangulation.topsis_closeness(matrix, w, DIRS_UP)
    assert eq_tol(close[key('S1')], ZERO)
    assert eq_tol(close[key('S2')], D('1'))
    assert eq_tol(close[key('S3')], D('0.75'))


# --------------------------------------------------------------------------
# T-TOP-03：RK-5 输出仅三角验证，不产出可对外披露的排名
# --------------------------------------------------------------------------
def test_t_top_03_output_is_bypass_only_and_carries_no_score_or_grade():
    assert '仅三角验证' in triangulation.__doc__
    assert '不得用于对外披露' in triangulation.run.__doc__
    assert '不入分' in triangulation.__doc__
    report_fields = set(TriangulationReport.model_fields)
    row_fields = set(TriangulationStrategyRow.model_fields)
    assert report_fields == {'rows', 'rho_main_topsis', 'rho_main_gra',
                             'rho_topsis_gra', 'mean_rho', 'agreement',
                             'gra_by_metric', 'flags'}
    assert row_fields == {'strategy_id', 'version_id', 'topsis_rank', 'gra_rank'}
    forbidden = {'grade', 'composite_absolute', 'composite_relative', 'score',
                 'attainment', 'usable_for_elimination', 'coverage'}
    assert not (forbidden & report_fields) and not (forbidden & row_fields)
    # 本模块不 import 入分链路（不入分的结构保证）
    for name in ('aggregate', 'grading', 'diagnostics', 'sensitivity'):
        assert not hasattr(triangulation, name)
    # 否决对象里也没有任何可乘权重的数值
    assert veto_fields() == {'vetoed', 'codes', 'usable_for_elimination'}


def veto_fields():
    return {f.name for f in dc_fields(triangulation.TriangulationVeto)}

# --------------------------------------------------------------------------
# T-GRA-01：GRA 公式（SDD 720-728）golden，初值化 + ρ=1
# --------------------------------------------------------------------------
def test_t_gra_01_initial_dimensionless_golden():
    '''手算：初值化 M1 (2,4,8)/2=(1,2,4)、M2 (3,12,9)/3=(1,4,3)；x_0=(4,4)
    Δ: S1=(3,3) S2=(2,0) S3=(0,1)；minΔ=0 maxΔ=3，ρ=1 -> ξ=3/(Δ+3)
    ξ: S1=(0.5,0.5) S2=(0.6,1) S3=(1,0.75)
    γ=w·ξ（w=0.5/0.5）= (0.5, 0.8, 0.875)。'''
    matrix = mat(SPEC_B)
    w = weights_of(matrix, W_B)
    xi, x0 = triangulation.gra_coefficients(matrix, DIRS_UP, D('1'), 'initial')
    assert eq_tol(x0['M1'], D('4')) and eq_tol(x0['M2'], D('4'))
    assert eq_tol(xi[key('S1')]['M1'], D('0.5'))
    assert eq_tol(xi[key('S1')]['M2'], D('0.5'))
    assert eq_tol(xi[key('S2')]['M1'], D('0.6'))
    assert eq_tol(xi[key('S2')]['M2'], D('1'))
    assert eq_tol(xi[key('S3')]['M1'], D('1'))
    assert eq_tol(xi[key('S3')]['M2'], D('0.75'))
    gamma = triangulation.gra_relatedness(matrix, w, DIRS_UP, D('1'), 'initial')
    assert eq_tol(gamma[key('S1')], D('0.5'))
    assert eq_tol(gamma[key('S2')], D('0.8'))
    assert eq_tol(gamma[key('S3')], D('0.875'))
    assert triangulation.rank_desc(gamma) == {key('S3'): 1, key('S2'): 2, key('S1'): 3}


# --------------------------------------------------------------------------
# T-GRA-02：ρ 与无量纲化方式都是必填配置，不编默认值
# --------------------------------------------------------------------------
def test_t_gra_02_rho_is_a_required_config_value_and_must_be_positive():
    matrix = mat(SPEC_B)
    norm = nframe(SPEC_B)
    doc = wdoc(W_B)
    scores = sframe({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    with pytest.raises(triangulation.MissingConfigError):
        triangulation.run(scores, norm, doc, cfg(rho=None), directions=DIRS_UP)
    with pytest.raises(triangulation.MissingConfigError):
        triangulation.run(scores, norm, doc, {'triangulation': {'enabled': True}},
                          directions=DIRS_UP)
    with pytest.raises(triangulation.TriangulationError):
        triangulation.gra_coefficients(matrix, DIRS_UP, D('0'), 'initial')
    with pytest.raises(triangulation.TriangulationError):
        triangulation.gra_coefficients(matrix, DIRS_UP, D('-0.5'), 'initial')
    with pytest.raises(triangulation.MissingConfigError):
        triangulation.is_enabled({'triangulation': {'rho': D('1')}})
    with pytest.raises(triangulation.TriangulationError):
        triangulation.is_enabled(cfg(enabled='true'))


def test_t_gra_02_mean_dimensionless_golden_and_differs_from_initial():
    '''均值化 golden（手算）：单指标 (2,4,6) 均值 4 -> (0.5,1,1.5)，x_0=1.5，
    Δ=(1,0.5,0)，ρ=1.5 -> ξ=(0.6,0.75,1)，w=1 -> γ=ξ。
    同一矩阵换成初值化，两指标以上的结果必须不同（SDD 723 两种都要跑并比对）。'''
    spec = {'S1': {'M1': '2'}, 'S2': {'M1': '4'}, 'S3': {'M1': '6'}}
    matrix = mat(spec)
    w = weights_of(matrix, W_A)
    gamma = triangulation.gra_relatedness(matrix, w, {'M1': 1}, D('1.5'), 'mean')
    assert eq_tol(gamma[key('S1')], D('0.6'))
    assert eq_tol(gamma[key('S2')], D('0.75'))
    assert eq_tol(gamma[key('S3')], D('1'))
    xi, x0 = triangulation.gra_coefficients(mat(SPEC_B), DIRS_UP, D('1'), 'mean')
    xi0, _ = triangulation.gra_coefficients(mat(SPEC_B), DIRS_UP, D('1'), 'initial')
    assert eq_tol(x0['M1'], D('1.714285714286'))  # 均值化：8 / (14/3) = 12/7
    differs = [k for k in sorted(xi) for m in ('M1', 'M2')
               if not eq_tol(xi[k][m], xi0[k][m])]
    assert differs, '初值化与均值化必须给出不同结果，否则 NORM_SWAP 无从比对'
    with pytest.raises(triangulation.TriangulationError):
        triangulation.dimensionless([D('1'), D('2')], 'z_score')
    with pytest.raises(triangulation.TriangulationError):
        triangulation.dimensionless([D('0'), D('0')], 'initial')


# --------------------------------------------------------------------------
# T-GRA-03：逐指标平均关联度（SDD 728 副产物）与负向参考序列
# --------------------------------------------------------------------------
def test_t_gra_03_by_metric_mean_relatedness_and_negative_reference():
    matrix = mat(SPEC_B)
    by_metric = triangulation.gra_by_metric(matrix, DIRS_UP, D('1'), 'initial')
    assert set(by_metric) == {'M1', 'M2'}
    assert eq_tol(by_metric['M1'], D('0.7'))   # mean(0.5, 0.6, 1)
    assert eq_tol(by_metric['M2'], D('0.75'))  # mean(0.5, 1, 0.75)
    # 负向指标的「当期最优」是 min（SDD 722）：x_0=1，Δ=(0,1,3) -> ξ=(1,0.75,0.5)
    one = {'S1': {'M1': '2'}, 'S2': {'M1': '4'}, 'S3': {'M1': '8'}}
    xi, x0 = triangulation.gra_coefficients(mat(one), {'M1': -1}, D('1'), 'initial')
    assert eq_tol(x0['M1'], D('1'))
    assert eq_tol(xi[key('S1')]['M1'], D('1'))
    assert eq_tol(xi[key('S2')]['M1'], D('0.75'))
    assert eq_tol(xi[key('S3')]['M1'], D('0.5'))
    gamma = triangulation.gra_relatedness(mat(one), weights_of(mat(one), W_A),
                                          {'M1': -1}, D('1'), 'initial')
    assert triangulation.rank_desc(gamma) == {key('S1'): 1, key('S2'): 2, key('S3'): 3}


# --------------------------------------------------------------------------
# T-TRI-01 硬点 1：不入分（开 / 关，分数与等级完全相同）
# --------------------------------------------------------------------------
def _scoring_inputs():
    attain_rows = tuple(
        AttainmentRow(strategy_id=sid, version_id=VER, period=PERIOD, metric_id='M1',
                      attainment=D(value), direction=1, target_source='budget',
                      has_target=True, capped_flag=False, reason_code=None)
        for sid, value in (('S1', '0.95'), ('S2', '0.75'), ('S3', '0.55')))
    attain = AttainmentFrame(rows=attain_rows, attainment_coverage={
        'S1': D('1'), 'S2': D('1'), 'S3': D('1')})
    ev = EvidenceFrame(rows=tuple(
        EvidenceRow(strategy_id=sid, version_id=VER, evidence_class='A',
                    evidence_reason=RC.EV_A_RANDOMIZED.value,
                    evidence_source='CARD_ONLY')
        for sid in ('S1', 'S2', 'S3')))
    rules = grading.GradeRuleSet(
        rows=tuple(GradeRuleRow(grade_code=g, grade_label=g, attainment_floor=D(f),
                                evidence_class_min='A', redline_pass_required=True,
                                promotion_streak=2, max_grade_if_no_target='L4')
                   for g, f in (('L1', '0.9'), ('L2', '0.7'), ('L3', '0.5'),
                                ('L4', '0.3'))),
        min_coverage_for_absolute_track=D('0.5'))
    return attain, nframe(SPEC_A), wdoc(W_A), ev, RedlineFrame(rows=()), rules


def test_t_tri_01_scores_and_grades_identical_with_triangulation_on_and_off():
    attain, norm, doc, ev, rl, rules = _scoring_inputs()
    on, off = cfg(enabled=True), cfg(enabled=False)
    scores_on = aggregate.compose(attain, norm, doc, on)
    scores_off = aggregate.compose(attain, norm, doc, off)
    assert scores_on == scores_off
    assert scores_on.model_dump() == scores_off.model_dump()
    grades_on = grading.assign(scores_on, attain, ev, rl, None, rules)
    grades_off = grading.assign(scores_off, attain, ev, rl, None, rules)
    assert grades_on == grades_off
    assert grades_on.model_dump() == grades_off.model_dump()
    # 断言不是空洞的：三个策略确实出了三个非 NOT_ASSESSED 的等级
    got = tuple(row.grade for row in grades_on.rows)
    assert 'NOT_ASSESSED' not in got and len(set(got)) == 3
    # 旁路跑完不改任何入分对象；关闭时连对象都没有
    report = triangulation.run(scores_on, norm, doc, on, directions={'M1': 1})
    assert isinstance(report, TriangulationReport)
    assert triangulation.run(scores_off, norm, doc, off, directions={'M1': 1}) is None
    assert aggregate.compose(attain, norm, doc, on) == scores_on
    assert grading.assign(scores_on, attain, ev, rl, None, rules) == grades_off
    assert isinstance(triangulation.veto(report), triangulation.TriangulationVeto)
    assert grading.assign(scores_on, attain, ev, rl, None, rules) == grades_on

# --------------------------------------------------------------------------
# T-TRI-01 硬点 2：可关开关（关闭时不产出任何三角验证对象）
# --------------------------------------------------------------------------
def test_t_tri_01_disabled_switch_emits_no_output_object():
    matrix = mat(SPEC_B)
    scores = sframe({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    norm, doc = nframe(SPEC_B), wdoc(W_B)
    off = cfg(enabled=False)
    assert triangulation.is_enabled(off) is False
    assert triangulation.is_enabled(cfg(enabled=True)) is True
    report = triangulation.run(scores, norm, doc, off, directions=DIRS_UP)
    assert report is None  # 不是空对象，是根本没有对象
    assert not isinstance(report, TriangulationReport)
    # 关闭不静默（SDD 1030）：唯一的、明确定义的输出是注册码
    assert triangulation.disabled_flag(off) == RC_DISABLED
    assert RC_DISABLED in RC._value2member_map_
    assert severity(RC_DISABLED) is Severity.INFO
    assert triangulation.disabled_flag(cfg(enabled=True)) is None
    # 关闭状态下调用否决接口的行为也是明确定义的
    verdict_off = triangulation.veto(None)
    assert verdict_off.vetoed is False
    assert verdict_off.codes == (RC_DISABLED,)
    assert verdict_off.usable_for_elimination is True
    assert triangulation.is_vetoed(None) is False
    with pytest.raises(triangulation.TriangulationError):
        triangulation.veto('not-a-report')


# --------------------------------------------------------------------------
# T-TRI-01 硬点 4：三个 Spearman 就是 SDD 732-734 的三对，平均秩处理并列
# --------------------------------------------------------------------------
def test_t_tri_01_three_spearman_pairs_golden_with_average_ranks():
    '''手算（并列取平均秩）：
    main (0.9,0.5,0.7) -> 平均秩 [3,1,2]（numeric.rank_average：秩 1 是最小值）
    topsis (0.25,0.5,0.5) -> 平均秩 [1,2.5,2.5]
    gra (0.5,0.25,0.5) -> 平均秩 [2.5,1,2.5]
    rho_main_topsis = -1.5/sqrt(3) = -0.866025403784
    rho_main_gra    = 1.5/sqrt(3) = 0.866025403784
    rho_topsis_gra  = -0.75/1.5 = -0.5
    mean_rho = (0.866025403784 - 0.866025403784)/2 = 0  # 不含第三对（SDD 736）'''
    main = {'S1': D('0.9'), 'S2': D('0.5'), 'S3': D('0.7')}
    topsis = {'S1': D('0.25'), 'S2': D('0.5'), 'S3': D('0.5')}
    gra = {'S1': D('0.5'), 'S2': D('0.25'), 'S3': D('0.5')}
    got = triangulation.rhos(main, topsis, gra)
    assert eq_tol(got.rho_main_topsis, D('-0.866025403784'))
    assert eq_tol(got.rho_main_gra, D('0.866025403784'))
    assert eq_tol(got.rho_topsis_gra, D('-0.5'))
    assert eq_tol(got.mean_rho, ZERO)
    assert not eq_tol(got.mean_rho, D('-0.166666666667'))  # 三个一起平均是错的
    # 三对的身份不可互换：把 topsis 与 gra 调换，两个 main 相关的 rho 随之互换
    swapped = triangulation.rhos(main, gra, topsis)
    assert eq_tol(swapped.rho_main_topsis, got.rho_main_gra)
    assert eq_tol(swapped.rho_main_gra, got.rho_main_topsis)
    assert eq_tol(swapped.rho_topsis_gra, got.rho_topsis_gra)
    # 平均秩而不是并列各给一名：完全同序（含并列）-> rho = 1
    tied = triangulation.rhos({'S1': D('1'), 'S2': D('2'), 'S3': D('2')},
                              {'S1': D('9'), 'S2': D('5'), 'S3': D('5')},
                              {'S1': D('0.1'), 'S2': D('0.2'), 'S3': D('0.2')})
    assert eq_tol(tied.rho_main_gra, D('1'))      # 两侧同样的并列 -> 平均秩一致
    assert eq_tol(tied.rho_main_topsis, D('-1'))  # 完全反序 -> -1
    with pytest.raises(triangulation.TriangulationError):
        triangulation.rhos(main, {'S1': D('1'), 'S2': D('2')}, gra)


def test_t_tri_01_zero_variance_rho_is_none_and_gives_no_verdict():
    '''某一对排序零方差 -> numeric.spearman 抛 DivisionUndefinedError -> rho 记
    None（models 的四个 rho 列都是 nullable），mean_rho 与 agreement 也是 None：
    未定义既不报一致也不报分歧，更不编一个数出来。'''
    main = {'S1': D('0.5'), 'S2': D('0.5'), 'S3': D('0.5')}
    topsis = {'S1': D('1'), 'S2': D('2'), 'S3': D('3')}
    gra = {'S1': D('3'), 'S2': D('2'), 'S3': D('1')}
    got = triangulation.rhos(main, topsis, gra)
    assert got.rho_main_topsis is None and got.rho_main_gra is None
    assert got.mean_rho is None
    assert eq_tol(got.rho_topsis_gra, D('-1'))  # 第三对仍然有定义
    assert triangulation.verdict(None, D('0.8')) is None


# --------------------------------------------------------------------------
# T-TRI-01 硬点 3：否决权（非补偿，不是扣分）
# --------------------------------------------------------------------------
def report_with(agreement, mean_rho, rho_topsis_gra=None):
    return TriangulationReport(
        rows=(TriangulationStrategyRow(strategy_id='S1', version_id=VER,
                                       topsis_rank=1, gra_rank=2),),
        rho_main_topsis=D(mean_rho), rho_main_gra=D(mean_rho),
        rho_topsis_gra=None if rho_topsis_gra is None else D(rho_topsis_gra),
        mean_rho=D(mean_rho), agreement=agreement, gra_by_metric={},
        flags=() if agreement is None else (agreement,))


def test_t_tri_01_veto_is_boolean_only_and_not_compensable():
    assert veto_fields() == {'vetoed', 'codes', 'usable_for_elimination'}
    for field in dc_fields(triangulation.TriangulationVeto):
        assert field.type in ('bool', 'tuple'), '否决对象不得携带数值字段'
    blocked = triangulation.veto(report_with(RC_DIVERGE, '-1'))
    assert blocked.vetoed is True
    assert blocked.codes == (RC_DIVERGE,)
    assert blocked.usable_for_elimination is False
    assert severity(RC_DIVERGE) is Severity.BLOCK
    # 非补偿：分歧多严重都不影响否决的形状，没有可被加权抵消的数值
    barely = triangulation.veto(report_with(RC_DIVERGE, '0.799999999999'))
    assert barely == blocked
    assert triangulation.veto(report_with(RC_AGREE, '1')).vetoed is False
    assert triangulation.veto(report_with(RC_AGREE, '1')).usable_for_elimination is True
    assert triangulation.veto(report_with(None, '0')).codes == ()
    assert triangulation.is_vetoed(report_with(RC_DIVERGE, '-1')) is True
    assert triangulation.is_vetoed(report_with(RC_AGREE, '1')) is False


def test_t_tri_01_threshold_is_required_and_boundary_is_inclusive():
    scores = sframe({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    norm, doc = nframe(SPEC_B), wdoc(W_B)
    with pytest.raises(triangulation.MissingConfigError):
        triangulation.run(scores, norm, doc, cfg(threshold=None), directions=DIRS_UP)
    assert triangulation.verdict(D('0.8'), D('0.8')) == RC_AGREE  # SDD 737 是 >=
    assert triangulation.verdict(D('0.799999999999'), D('0.8')) == RC_DIVERGE
    assert triangulation.verdict(ZERO, ZERO) == RC_AGREE


# --------------------------------------------------------------------------
# T-TRI-01：run() 端到端 golden（全部期望值手算）
# --------------------------------------------------------------------------
def test_t_tri_01_run_end_to_end_golden_report():
    '''SPEC_B + main=(0.5,0.8,0.875)：三个排序完全同序 ->
    rho_main_topsis = rho_main_gra = rho_topsis_gra = 1，mean_rho = 1 ->
    METHOD_AGREEMENT；γ 与逐指标平均关联度用 T-GRA-01/03 的手算值；
    TOPSIS 侧 S1 落在负理想解上，D- = 0 -> C_1 = 0（精确）。'''
    scores = sframe({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    norm, doc = nframe(SPEC_B), wdoc(W_B)
    report = triangulation.run(scores, norm, doc, cfg(rho='1', threshold='0.8'),
                              directions=DIRS_UP)
    assert isinstance(report, TriangulationReport)
    assert [row.strategy_id for row in report.rows] == ['S1', 'S2', 'S3']
    assert {row.strategy_id: row.topsis_rank for row in report.rows} == {
        'S1': 3, 'S2': 2, 'S3': 1}
    assert {row.strategy_id: row.gra_rank for row in report.rows} == {
        'S1': 3, 'S2': 2, 'S3': 1}
    assert eq_tol(report.rho_main_topsis, D('1'))
    assert eq_tol(report.rho_main_gra, D('1'))
    assert eq_tol(report.rho_topsis_gra, D('1'))
    assert eq_tol(report.mean_rho, D('1'))
    assert report.agreement == RC_AGREE
    assert report.flags == (RC_AGREE,)
    assert eq_tol(report.gra_by_metric['M1'], D('0.7'))
    assert eq_tol(report.gra_by_metric['M2'], D('0.75'))
    close = triangulation.topsis_closeness(mat(SPEC_B), weights_of(mat(SPEC_B), W_B),
                                           DIRS_UP)
    assert eq_tol(close[key('S1')], ZERO)
    assert not triangulation.veto(report).vetoed
    # 反向的 main -> 三个 rho 全为 -1 -> METHOD_DIVERGENCE -> 否决
    bad = triangulation.run(sframe({'S1': '0.875', 'S2': '0.8', 'S3': '0.5'}), norm,
                            doc, cfg(rho='1', threshold='0.8'), directions=DIRS_UP)
    assert eq_tol(bad.rho_main_topsis, D('-1'))
    assert eq_tol(bad.rho_main_gra, D('-1'))
    assert eq_tol(bad.mean_rho, D('-1'))
    assert bad.agreement == RC_DIVERGE and bad.flags == (RC_DIVERGE,)
    assert triangulation.veto(bad).usable_for_elimination is False


def test_t_tri_01_directions_single_period_and_shape_are_required():
    matrix = mat(SPEC_B)
    scores = sframe({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    norm, doc = nframe(SPEC_B), wdoc(W_B)
    run = triangulation.run
    with pytest.raises(triangulation.DirectionRequiredError):
        run(scores, norm, doc, cfg(), directions=None)
    with pytest.raises(triangulation.DirectionRequiredError):
        run(scores, norm, doc, cfg(), directions={'M1': 1})
    with pytest.raises(triangulation.DirectionRequiredError):
        run(scores, norm, doc, cfg(), directions={'M1': 0, 'M2': 1})
    with pytest.raises(triangulation.MultiPeriodError):
        run(ScoreFrame(rows=scores.rows + sframe({'S1': '0.5', 'S2': '0.6'},
                                                 PERIOD2).rows),
            norm, doc, cfg(), directions=DIRS_UP)
    with pytest.raises(triangulation.TriangulationError):
        run(scores, norm, wdoc(W_A), cfg(), directions=DIRS_UP)  # 权重缺 M2
    with pytest.raises(triangulation.TriangulationError):
        run(sframe({'S1': '0.5'}), nframe({'S1': {'M1': '1', 'M2': '2'}}), doc,
            cfg(), directions=DIRS_UP)  # 少于 2 个可评价策略
    with pytest.raises(triangulation.TriangulationError):
        run(scores, nframe({'S1': {'M1': '2'}, 'S2': {'M1': '4', 'M2': '12'},
                            'S3': {'M1': '8', 'M2': '9'}}), doc, cfg(),
            directions=DIRS_UP)  # 矩阵不矩形
    with pytest.raises(triangulation.TriangulationError):
        run('not-a-frame', norm, doc, cfg(), directions=DIRS_UP)
    # 不出分（composite_absolute 为 None）的策略不进任何分母
    partial = sframe({'S1': '0.5', 'S2': '0.8', 'S3': None})
    report = run(partial, norm, doc, cfg(), directions=DIRS_UP)
    assert [row.strategy_id for row in report.rows] == ['S1', 'S2']
    assert report.agreement in (RC_AGREE, RC_DIVERGE, None)
