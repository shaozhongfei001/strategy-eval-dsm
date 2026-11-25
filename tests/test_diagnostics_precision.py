'''B12-FIX · B1 守护 —— dsm/diagnostics.py `_pearson`（缺陷位 :223）的 Decimal 精度预算。

缺陷（真实生产阻断，不是夹具人工产物）：T3 事实表的钱款列以**最小货币单位**整数计
（[L887] / C-09），冻结 fixtures 的 M_CAMPAIGN_COST_MINOR 在 2026-Q2 的 12 个主体上量级
≈ 2.8e6；numeric.mean 量化到 1e-12，于是偏差 dx 带 7 位整数 + 12 位小数，实测
sxx*syy = 49016754199474433799.75（20 位整数），把它 quantize 到 1e-12 需要 32 个有效位
> decimal 默认上下文 prec=28 -> decimal.InvalidOperation -> `dsm score` 退出码 5、不产
任何结果（仍写 audit_bundle）。任何以最小货币单位计的真实银行数据都会撞上同一处。

修法（dsm/diagnostics.py `_pearson_prec` / `_pearson`）：整段计算放进
decimal.localcontext()，prec 由**入参本身**推导（宽度 w -> 平方 2w -> n 项求和 -> 两列
相乘 -> 再 quantize 到 1e-12），只升不降，InvalidOperation 陷阱保持武装；全程纯 Decimal
精确算术 —— 无 float（H-4）、不改成更粗的 quantize 绕过、不用 try/except 把异常吞成 0
或 None（那是静默降级，V-14）。

预言机独立性（R-14：期望值不得抄实现输出）——本文件的期望值一律不由被测实现产生：
  1) `_exact_r_squared`：只用 fractions.Fraction（精确整数比，标准库有理数算术），按
     Pearson 定义算出 r^2 = sxy^2 / (sxx*syy) 的**精确有理数**与 sxy 的精确符号，再把
     实现的 q12 结果精确转成 Fraction 平方后比对。Decimal 与 Fraction 无共享代码路径。
  2) 闭式手算：完全同向/反向线性列必为 +1 / -1；(1,2,3,4) x (1,3,2,5) 的
     sxy=11/2、sxx=5、syy=35/4 -> r^2 = (121/4)/(175/4) = 121/175，可笔算复核。
  3) 两条**数学不变量**交叉验证：正缩放 x -> c*x（c>0）与平移 x -> x + k 都不改变
     rho。平移 +1e24 这一条在修复前必红（prec=28 下整列塌成同一个数 -> 零方差 ->
     None），故断言非空洞。
  4) 负例：同一条数据在 prec=28 下**手工**重放未修版本的表达式必须抛
     InvalidOperation；把陷阱解除则 quantize 得到 NaN（不是数），证明「精度不够」这条
     路上根本不存在静默错值的出口。
'''
import json
import pathlib
from decimal import Decimal, InvalidOperation, getcontext, localcontext
from fractions import Fraction

import pytest

from dsm import diagnostics, numeric
from dsm.numeric import D, q12

REPO = pathlib.Path(__file__).resolve().parents[1]
FACTS = REPO / 'fixtures' / 'input' / 'metric_fact.jsonl'
PERIOD = '2026-Q2'                     # = tests/test_integration_spine.PERIOD
MONEY = 'M_CAMPAIGN_COST_MINOR'        # 最小货币单位的钱款列（缺陷触发列）
OTHER = 'M_REV_MINOR'                  # 同为钱款列，量级 7e3~1.3e4
DEFAULT_PREC = 28                      # decimal 出厂 prec；本文件永不改全局上下文
TINY = Decimal('1E-12')                # V-9 的输出分辨率


def _fixture_column(metric_id, period=PERIOD):
    '''冻结 fixtures 里某个指标在某一期的真实列（按 strategy_id 排序，确定性 V-3）。
    量级取自仓库自带数据，不是本文件拟的（R-12）。'''
    assert FACTS.is_file(), '冻结 fixtures 不在位：' + str(FACTS)
    cells = {}
    with FACTS.open(encoding='utf-8') as handle:
        for line in handle:
            row = json.loads(line)
            if row['metric_id'] == metric_id and row['period'] == period:
                cells[row['strategy_id']] = row['value']
    assert cells, metric_id + ' 在 ' + period + ' 没有事实行'
    return tuple(D(str(cells[sid])) for sid in sorted(cells))


def _exact_r_squared(xs, ys):
    '''独立预言机：r^2 与 sxy 符号的**精确有理数**值，只用 Fraction（精确整数比）。
    不碰 Decimal、不碰 float、不调用被测实现，故与实现无共享代码路径（R-14）。'''
    count = len(xs)
    fx = [Fraction(D(v)) for v in xs]
    fy = [Fraction(D(v)) for v in ys]
    mx = sum(fx) / count
    my = sum(fy) / count
    sxy = sum((a - mx) * (b - my) for a, b in zip(fx, fy))
    sxx = sum((a - mx) ** 2 for a in fx)
    syy = sum((b - my) ** 2 for b in fy)
    if sxx == 0 or syy == 0:
        return None, sxy
    return (sxy * sxy) / (sxx * syy), sxy


def _assert_matches_exact_oracle(got, xs, ys, tolerance=Decimal('2E-12')):
    '''把实现的 q12 结果与精确有理数预言机比对。实现输出量化到 1e-12，故
    |got| 的误差 <= 5e-13；|r| <= 1 时 |r^2 - got^2| = |r-got|*|r+got| <= 2*5e-13。
    容差取 2e-12 是这个推导的上界，不是从实现读数凑出来的。'''
    r_squared, sxy = _exact_r_squared(xs, ys)
    assert r_squared is not None, '预言机认为该列零方差，测试数据选错了'
    assert isinstance(got, Decimal) and not isinstance(got, float)
    assert got.is_finite() and not got.is_nan(), '无定义/静默降级都不允许（V-14）'
    assert abs(Fraction(got) ** 2 - r_squared) <= Fraction(tolerance), (
        'r^2 实测=' + str(Fraction(got) ** 2) + ' 精确预言机=' + str(r_squared))
    assert (got > 0) == (sxy > 0), '符号必须与精确 sxy 一致'
    assert abs(got) <= numeric.ONE + TINY, 'Pearson r 数学上 |r| <= 1'


def _unfixed_product(xs, ys):
    '''逐字重放**未修版本**的中间量：q12(sxx * syy)，在 prec=28 的上下文里跑。
    用来证明本文件的测试数据确实处在缺陷量级上（断言非空洞），也用来证明修复不是
    靠把 quantize 改粗换来的。'''
    with localcontext() as ctx:
        ctx.prec = DEFAULT_PREC
        dx = [D(v) - numeric.mean(xs) for v in xs]
        dy = [D(v) - numeric.mean(ys) for v in ys]
        sxx = sum((a * a for a in dx), numeric.ZERO)
        syy = sum((b * b for b in dy), numeric.ZERO)
        return q12(sxx * syy)


def test_the_fixture_money_column_is_really_beyond_the_default_context():
    '''前置事实钉：钱款列量级 ≈ 2.8e6（实测取自冻结 fixtures），未修表达式在 prec=28
    下确实抛 InvalidOperation，且推导出的精度预算 > 28。没有这一条，后面所有断言都可能
    是空洞的（数据根本没到缺陷量级）。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    assert len(cost) == len(rev) == 12
    assert max(cost) >= Decimal('1000000'), '钱款列必须是最小货币单位量级，实测 ' + str(max(cost))
    assert max(cost) < Decimal('10000000')
    with pytest.raises(InvalidOperation):
        _unfixed_product(cost, rev)                    # 修复前就是这一行炸的
    budget = diagnostics._pearson_prec(cost, rev)
    assert budget > DEFAULT_PREC, '预算必须超过默认 prec，否则等于没修：' + str(budget)
    assert isinstance(budget, int) and not isinstance(budget, bool)


def test_pearson_on_the_fixture_money_column_matches_the_exact_rational_oracle():
    '''B1 主断言：真实钱款量级下 `_pearson` 不抛，且与 Fraction 精确预言机一致。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    got = diagnostics._pearson(cost, rev)              # 修复前：InvalidOperation
    _assert_matches_exact_oracle(got, cost, rev)
    assert got.as_tuple().exponent == -12, 'V-9：输出必须量化到 1e-12'


def test_pearson_budget_is_derived_from_the_data_not_hardcoded():
    '''预算随量级单调上升、对正缩放不敏感于「够不够」，且任何列都 > 默认 28：
    证明它是从入参推导的，不是钉死的一个数（H-5：数据宽度不是治理值）。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    base = diagnostics._pearson_prec(cost, rev)
    scaled = tuple(v.scaleb(24) for v in cost)         # x 1e24
    huge = tuple(v.scaleb(30) for v in cost)           # x 1e30
    small = (D('1'), D('2'), D('3'), D('4'))
    assert base > DEFAULT_PREC
    assert diagnostics._pearson_prec(scaled, rev) > base
    assert diagnostics._pearson_prec(huge, rev) > diagnostics._pearson_prec(scaled, rev)
    # 最小可能的一列（两位小数、个位量级）也必须仍在 1e-12 分辨率下精确
    assert diagnostics._pearson_prec(small, small) > DEFAULT_PREC


def test_pearson_at_an_extreme_magnitude_is_still_exact_not_silently_rounded():
    '''负例（b）：构造远超任何真实钱款口径的量级（1e30 倍 -> ≈2.8e36），断言行为是
    **明确处理**且与精确预言机一致，而不是静默错值；同时证明同一条数据在 prec=28 下
    仍然炸、把陷阱解除则得到 NaN（不是数）——「精度不够」这条路上没有静默出口。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    huge = tuple(v.scaleb(30) for v in cost)
    with pytest.raises(InvalidOperation):
        _unfixed_product(huge, rev)                    # prec=28 明确报错
    with localcontext() as ctx:                        # 解除陷阱 -> NaN，不是数
        ctx.traps[InvalidOperation] = False
        dx = [D(v) - numeric.mean(huge) for v in huge]
        dy = [D(v) - numeric.mean(rev) for v in rev]
        sxx = sum((a * a for a in dx), numeric.ZERO)
        syy = sum((b * b for b in dy), numeric.ZERO)
        assert (sxx * syy).quantize(TINY).is_nan(), '陷阱解除只会得到 NaN，绝不会得到一个看起来对的数'
    got = diagnostics._pearson(huge, rev)              # 修复后：明确处理
    _assert_matches_exact_oracle(got, huge, rev)
    assert got.as_tuple().exponent == -12


def test_scaling_and_huge_translation_leave_rho_mathematically_untouched():
    '''两条数学不变量做交叉预言机：正缩放与平移都不改变 Pearson r。平移 +1e24 在
    prec=28 下会把整列塌成同一个数（零方差 -> None），所以这条断言在修复前必红。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    plain = diagnostics._pearson(cost, rev)
    scaled = diagnostics._pearson(tuple(v.scaleb(24) for v in cost), rev)
    shifted = diagnostics._pearson(tuple(v + Decimal(10) ** 24 for v in cost), rev)
    assert plain is not None and scaled is not None and shifted is not None
    assert scaled == plain, 'rho 对正缩放不变：' + str(scaled) + ' vs ' + str(plain)
    assert shifted == plain, 'rho 对平移不变：' + str(shifted) + ' vs ' + str(plain)


def test_small_closed_form_columns_agree_with_hand_computed_values():
    '''闭式手算预言机（不是抄实现输出）：
      (1,2,3,4) x (2,4,6,8) 完全同向线性 -> r = +1
      (1,2,3,4) x (8,6,4,2) 完全反向线性 -> r = -1
      (1,2,3,4) x (1,3,2,5)：mx=5/2 my=11/4，sxy=11/2 sxx=5 syy=35/4
        -> r^2 = (121/4)/(175/4) = 121/175，r>0
    '''
    xs = (D('1'), D('2'), D('3'), D('4'))
    up = (D('2'), D('4'), D('6'), D('8'))
    down = (D('8'), D('6'), D('4'), D('2'))
    mixed = (D('1'), D('3'), D('2'), D('5'))
    assert diagnostics._pearson(xs, up) == q12(numeric.ONE)
    assert diagnostics._pearson(xs, down) == q12(-numeric.ONE)
    got = diagnostics._pearson(xs, mixed)
    assert Fraction(got) ** 2 == Fraction(121, 175) or \
        abs(Fraction(got) ** 2 - Fraction(121, 175)) <= Fraction(TINY)
    assert got > 0
    assert Fraction(121, 175) < 1, '手算 r^2 = 121/175 < 1，数据不是完全相关'


def test_zero_variance_column_still_returns_none_and_never_a_number():
    '''回归钉（R-14）：零方差列的既有语义一字不改 —— rho 无定义就是 None，不报 0、
    不报 1、不编数。恒定列在缺陷量级上同样如此。'''
    cost = _fixture_column(MONEY)
    flat = tuple(D('10000') for _ in cost)
    assert diagnostics._pearson(flat, cost) is None
    assert diagnostics._pearson(cost, flat) is None
    assert diagnostics._pearson(flat, flat) is None
    assert diagnostics._pearson(tuple(v.scaleb(24) for v in flat), cost) is None


def test_no_float_anywhere_and_the_default_context_is_left_alone():
    '''H-4「never float」+ 局部性：修完不许有 float 混进数值面，也不许把全局 decimal
    上下文改掉（localcontext 必须真的局部，否则会污染同进程后续所有算术）。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    before = getcontext().prec
    got = diagnostics._pearson(cost, rev)
    assert getcontext().prec == before == DEFAULT_PREC, 'localcontext 泄漏了'
    assert isinstance(got, Decimal) and not isinstance(got, float)
    for value in (got, D(cost[0]), numeric.mean(cost)):
        assert not isinstance(value, float)
    assert isinstance(diagnostics._digits_span(cost[0]), int)
    assert isinstance(diagnostics._ceil_log10(len(cost)), int)
    assert diagnostics._ceil_log10(1) == 0 and diagnostics._ceil_log10(12) == 2
    assert diagnostics._ceil_log10(100) == 2 and diagnostics._ceil_log10(101) == 3
    assert diagnostics._digits_span(Decimal('150E+2')) == 5
    assert diagnostics._digits_span(Decimal('0.005')) == 4


def test_corr_matrix_over_money_magnitude_columns_is_symmetric_and_honest():
    '''集成面：整张 [L692] 相关矩阵在钱款量级 + 一个恒定列上不再抛。有定义的格子与
    `_pearson` 逐格相等、矩阵对称、对角为 1；无定义的格子是 None（不填 0），这正是
    CollinearityReport 把该指标摘出上报子集的依据（见 diagnostics.compute 的 B3 段）。'''
    cost = _fixture_column(MONEY)
    rev = _fixture_column(OTHER)
    flat = tuple(D('10000') for _ in cost)
    values = {'m_flat': flat, 'm_cost': cost, 'm_rev': rev}
    metric_ids = ('m_cost', 'm_flat', 'm_rev')
    matrix = diagnostics._corr_matrix(values, metric_ids, 'pearson')
    assert len(matrix) == 3 and all(len(row) == 3 for row in matrix)
    for a in range(3):
        assert matrix[a][a] == q12(numeric.ONE)
        for b in range(3):
            assert matrix[a][b] == matrix[b][a]
    assert matrix[1][0] is None and matrix[1][2] is None, '恒定列的 rho 必须是 None，不是 0'
    assert matrix[0][2] == diagnostics._pearson(cost, rev)
    _assert_matches_exact_oracle(matrix[0][2], cost, rev)
    # spearman 口径不受本修影响（走 numeric.spearman，另一条代码路径）
    ranked = diagnostics._corr_matrix(values, metric_ids, 'spearman')
    assert ranked[1][0] is None and ranked[0][2] is not None
