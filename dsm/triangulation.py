'''dsm.triangulation -- 旁路三角验证：TOPSIS / GRA / 三个 Spearman / 否决权 / 可关
（M-F、M-G；digest M12-triangulation，SDD 698-741 与 1022-1032）。

**旁路，不入分**：TOPSIS / GRA 是可补偿的排序类方法、输出相对名次，用于分级会重新
引入 F3/F4（SDD 702），所以这里的结果不进加权线性和、不改分数、不改等级；
**输出仅三角验证**，不产出可对外披露的排名（RK-5，T-TOP-03 守护）。本模块不
import aggregate / grading / diagnostics，run() 只读三个入参（INV-3）。可关
（SDD 1030）：enabled = false 时 run() 返回 None（连空对象都不给），关闭由 disabled_flag() 落
TRIANGULATION_DISABLED，不静默。否决权（SDD 740）：TriangulationVeto 照
sensitivity.SensitivityVeto，只有 bool 与 reason_code、无数值字段，故不可被加权补偿、
也不表现为扣分（P0-2）。三个 Spearman 严格是 SDD 732-734 的三对（composite_absolute
x TOPSIS / composite_absolute x GRA / TOPSIS x GRA），mean_rho 只取前两对（SDD 736），
并列秩走 numeric.rank_average（复用 numeric.spearman，不自写）。数值口径（V-9）：
除法 / 开方 / 均值 / 加权 / 量化全走 dsm.numeric；零分母走 safe_div 的 on_zero 语义
（贴近度 0/0 记 0 -> 全体并列；无量纲化参考值为 0、差序列全 0 属 genuinely
undefined -> 报错，不猜数）。纯函数（H-8）：无时钟、无随机、无 I/O。

digest 未给、因此做成必填入参 / 必填注入并登记为缺口（R-12、ADJ-2）：rho（分辨系数，
SDD 725）、divergence_threshold（SDD 737）、gra_norm（初值化 / 均值化的切换拼写，
SDD 723）、directions（metric_id -> +1/-1：理想解 SDD 713-714 与参考序列 SDD 722
都要方向，而三个入参都没有 direction 列，metric_dict 不在签名内也不得代读，故照
normalize.compute(pools=...) 的先例必填注入）、period（TriangulationReport 无
period 列，run() 只接受单期，多期报错）。
'''
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from dsm import numeric
from dsm.models import (NormalizedFrame, ScoreFrame, TriangulationReport,
                        TriangulationStrategyRow, WeightVersionDoc)
from dsm.reason_codes import RC

__all__ = [
    'TriangulationError', 'MissingConfigError', 'DirectionRequiredError',
    'MultiPeriodError', 'TriangulationVeto', 'RhoSet', 'CFG_SECTION',
    'CFG_ENABLED', 'CFG_RHO', 'CFG_THRESHOLD', 'CFG_GRA_NORM', 'CFG_KEYS',
    'GRA_NORM_INITIAL', 'GRA_NORM_MEAN', 'GRA_NORM_METHODS', 'is_enabled',
    'disabled_flag', 'present_metrics', 'metric_weights', 'vector_normalize',
    'weighted_matrix', 'ideal_solutions', 'topsis_closeness', 'dimensionless',
    'reference_sequence', 'gra_coefficients', 'gra_relatedness',
    'gra_by_metric', 'rank_desc', 'rhos', 'verdict', 'run', 'veto', 'is_vetoed',
    'zero_variance_metrics', 'drop_metrics',
]

# eval_config 路径：SDD 1030-1031 给了参数名但没给 yaml 键位，拼写在这里定一次
# （同 normalize.py 的 CFG_*）。四个键全部必填，无默认（R-12）；SDD 723 的两种
# 无量纲化都实现，拼写也在这里定一次；reason_code 一律用注册名（ADJ-3）。
CFG_SECTION = 'triangulation'
CFG_ENABLED = 'enabled'
CFG_RHO = 'rho'
CFG_THRESHOLD = 'divergence_threshold'
CFG_GRA_NORM = 'gra_norm'
CFG_KEYS = (CFG_ENABLED, CFG_RHO, CFG_THRESHOLD, CFG_GRA_NORM)
GRA_NORM_INITIAL = 'initial'
GRA_NORM_MEAN = 'mean'
GRA_NORM_METHODS = (GRA_NORM_INITIAL, GRA_NORM_MEAN)
RC_DISABLED = RC.TRIANGULATION_DISABLED.value
RC_AGREEMENT = RC.METHOD_AGREEMENT.value
RC_DIVERGENCE = RC.METHOD_DIVERGENCE.value
# 零方差列的显式降级码（见 zero_variance_metrics / _flags）：normalize.py:111 的
# CODE_INACTIVE 与 [L943] 给同一条零变异归一化行落的就是这一枚，
# 三角验证沿用同一口径，不新注册码（reason_codes.py 单点，R-15）。
RC_INACTIVE = RC.INACTIVE_METRIC.value
MIN_POPULATION = 2  # numeric.spearman 的下限，也是三角验证的最小有意义规模


class TriangulationError(ValueError):
    '''入参、配置值或矩阵形状违反 SDD 698-741 / 1022-1032 的契约。'''


class MissingConfigError(TriangulationError):
    '''缺配置块或配置键：digest 未给默认值，所以不猜（R-12 / ADJ-2）。'''


class DirectionRequiredError(TriangulationError):
    '''缺 metric_id -> +1/-1 的方向注入（理想解与参考序列都要方向）。'''


class MultiPeriodError(TriangulationError):
    '''TriangulationReport 无 period 列，多期入参无落点，拒绝而不是挑一期。'''


@dataclass(frozen=True)
class TriangulationVeto:
    '''SDD 740 的否决权。**只有 bool 与 reason_code，没有任何数值字段**：否决一旦
    带着数值就能被后续加权补偿掉，那就不是非补偿语义（P0-2）。形状照
    dsm/sensitivity.py 的 SensitivityVeto（只读参考，不 import）。'''
    vetoed: bool
    codes: tuple
    usable_for_elimination: bool


@dataclass(frozen=True)
class RhoSet:
    '''SDD 732-736 的三对相关 + mean_rho，只流向 TriangulationReport 的四个
    nullable Ratio 列；veto() 不读这里任何数值。'''
    rho_main_topsis: Decimal | None
    rho_main_gra: Decimal | None
    rho_topsis_gra: Decimal | None
    mean_rho: Decimal | None


def _get(node, key):
    if node is None:
        return None
    if isinstance(node, Mapping):
        return node.get(key)
    return getattr(node, key, None)


def _section(config):
    '''取 triangulation 配置段：AppConfig（.eval_config 树）、裸 eval_config 树或
    扁平写法都接受；缺块即报错，什么都不默认（R-12）。'''
    tree = _get(config, 'eval_config')
    if tree is None:
        tree = config
    block = _get(tree, CFG_SECTION)
    if block is not None:
        return block
    if _get(tree, CFG_ENABLED) is not None:
        return tree
    raise MissingConfigError('no ' + CFG_SECTION + ' block in the configuration')


def _need(section, key):
    value = _get(section, key)
    if value is None:
        raise MissingConfigError(
            CFG_SECTION + '.' + key + ' 必填；digest 未给默认值（R-12）')
    return value


def _number(section, key):
    value = _need(section, key)
    return numeric.from_float(value) if isinstance(value, float) else numeric.D(value)


def is_enabled(config) -> bool:
    '''可关开关（SDD 1030）。enabled 必须显式给 bool：缺键报错、非 bool 报错，因为
    「默认开」和「默认关」都是替行方选了行为（H-5）。'''
    value = _need(_section(config), CFG_ENABLED)
    if not isinstance(value, bool):
        raise TriangulationError(CFG_SECTION + '.' + CFG_ENABLED + ' 必须是 bool，got '
                                 + type(value).__name__)
    return value


def disabled_flag(config):
    '''关闭时必须落码（SDD 1030 不得静默）：关 -> TRIANGULATION_DISABLED，开 ->
    None。这是关闭状态下唯一的、明确定义的输出。'''
    return None if is_enabled(config) else RC_DISABLED

def _direction(directions, metric_id):
    '''metric_id -> +1/-1：必填注入，缺一个指标就报错，绝不按数据形状猜方向。'''
    if directions is None:
        raise DirectionRequiredError('directions 必填：理想解与参考序列都要方向')
    if metric_id not in directions:
        raise DirectionRequiredError('directions 缺指标: ' + str(metric_id))
    value = directions[metric_id]
    if isinstance(value, bool) or not isinstance(value, int) or value not in (1, -1):
        raise DirectionRequiredError('direction 必须是 +1 或 -1 的 int，got '
                                     + repr(value))
    return value


def _check_directions(directions, metrics) -> dict:
    return {m: _direction(directions, m) for m in metrics}


def present_metrics(matrix) -> tuple:
    '''矩阵里出现过的全部指标，排序后返回（确定性顺序，V-3）。'''
    seen = set()
    for row in matrix.values():
        seen.update(row)
    return tuple(sorted(seen))


def zero_variance_metrics(matrix) -> tuple:
    '''本次三角比对里「零方差」的指标：同一期内每个可评价策略的取值都在 numeric.TOL
    之内相同。真实数据里这种列很常见（诊断层本来就有 INACTIVE / LOW_VARIATION 两个
    状态，冻结 fixtures 的 M_AUM_MINOR 就是 12 个主体恒为 10000），而它在 GRA Step 2
    的**两种**签认口径下参考值都恒为 0 —— min_max 归一后整列为 0，初值化的首值与均值
    化的均值同为 0 —— 于是 dimensionless 按设计报错，且**不回落第三种口径**（发明
    数值，R-12）。

    所以正确的处置不是给恒定列编一个归一化，而是把它作为**显式降级**从本次比对的该列
    贡献中排除，并由 run() 带 RC_INACTIVE 进 report.flags 披露。这条处置链沿用
    SPEARMAN_ZERO_VARIANCE 的既有口径：模块出码 -> report.flags -> reports._section_8
    正文「三角标记」行（另在「GRA 关联系数（metric_id -> 均值）」一行可见地少掉该列），
    不进附录、不静默（V-14）。少于两个取值时无从判断方差，不列进来（MIN_POPULATION 与
    _check_shape 另行把关）。纯函数（H-8）：只读入参，顺序确定（V-3）。'''
    keys = tuple(sorted(matrix))
    out = []
    for metric in present_metrics(matrix):
        column = [numeric.D(matrix[key][metric]) for key in keys if metric in matrix[key]]
        if len(column) >= 2 and all(numeric.eq_tol(v, column[0]) for v in column[1:]):
            out.append(metric)
    return tuple(sorted(out))


def drop_metrics(matrix, dropped) -> dict:
    '''从矩阵**副本**里摘掉 dropped 的指标列。入参只读（INV-3），返回新字典；dropped
    为空时原样复制，故非零方差场景逐位不变（回归钉）。'''
    gone = frozenset(dropped)
    if not gone:
        return {key: dict(row) for key, row in matrix.items()}
    return {key: {m: v for m, v in sorted(row.items()) if m not in gone}
            for key, row in matrix.items()}


def _check_shape(matrix) -> tuple:
    '''要求矩形矩阵：每个策略的指标集完全一致。缺一格就报错，不拿 0 或均值补
    （补数等于发明业务数值，R-12）。'''
    keys = tuple(sorted(matrix))
    if not keys:
        raise TriangulationError('三角验证的矩阵为空')
    metrics = present_metrics(matrix)
    for key in keys:
        if tuple(sorted(matrix[key])) != metrics:
            raise TriangulationError('矩阵不是矩形：' + repr(key) + ' 指标集不一致')
    return keys, metrics


def metric_weights(matrix, weights) -> dict:
    '''SDD 712 / 1027：权重直接取**冻结的组合权重**，不另设。w_j = W_d · w_(j|d)
    （level1 x level2），再按 SDD 954 的同一口径在实际参评指标上重归一到 1
    （两法都只用相对权重，重归一不改变任何名次）。WeightVersionDoc 只读（INV-3）。'''
    if not isinstance(weights, WeightVersionDoc):
        raise TriangulationError('weights 必须是 WeightVersionDoc，got '
                                 + type(weights).__name__)
    combined = {}
    for dim in sorted(weights.level2_weights):
        if dim not in weights.level1_weights:
            raise TriangulationError('level1_weights 缺维度: ' + dim)
        w_dim = numeric.D(weights.level1_weights[dim])
        for metric in sorted(weights.level2_weights[dim]):
            if metric in combined:
                raise TriangulationError('metric belongs to two dimensions: ' + metric)
            combined[metric] = numeric.q12(
                w_dim * numeric.D(weights.level2_weights[dim][metric]))
    metrics = present_metrics(matrix)
    missing = tuple(m for m in metrics if m not in combined)
    if missing:
        raise TriangulationError('weights 缺指标: ' + ', '.join(missing))
    total = numeric.weighted_sum([(numeric.ONE, combined[m]) for m in metrics])
    if numeric.eq_tol(total, numeric.ZERO):
        raise TriangulationError('参评指标的组合权重合计为 0，三角验证未定义')
    return {m: numeric.safe_div(combined[m], total, on_zero=None) for m in metrics}


def vector_normalize(column: Sequence) -> tuple:
    '''TOPSIS Step 1（SDD 711）：r_ij = x_ij / sqrt(Σ_i x_ij²)。整列为 0 时分母为 0，
    走 safe_div 的 on_zero=ZERO：整列 r 记 0（该指标本期不区分任何策略）。'''
    vals = [numeric.D(v) for v in column]
    if not vals:
        raise TriangulationError('vector_normalize 收到空列')
    norm = numeric.sqrt(numeric.q12(sum(v * v for v in vals)))
    return tuple(numeric.safe_div(v, norm, on_zero=numeric.ZERO) for v in vals)


def weighted_matrix(matrix: Mapping, weights: Mapping, keys: Sequence,
                    metrics: Sequence) -> dict:
    '''TOPSIS Step 2（SDD 712）：v_ij = w_j · r_ij。'''
    r = {m: vector_normalize([matrix[k][m] for k in keys]) for m in metrics}
    return {k: {m: numeric.q12(numeric.D(weights[m]) * r[m][i]) for m in metrics}
            for i, k in enumerate(keys)}


def ideal_solutions(weighted: Mapping, directions: Mapping) -> tuple:
    '''TOPSIS Step 3（SDD 713-714 逐字）：A+ = (正向取 max / 负向取 min)，A− 反之。'''
    keys = tuple(sorted(weighted))
    a_plus = {}
    a_minus = {}
    for metric in present_metrics(weighted):
        column = [numeric.D(weighted[k][metric]) for k in keys]
        hi = numeric.q12(max(column))
        lo = numeric.q12(min(column))
        if _direction(directions, metric) < 0:
            hi, lo = lo, hi
        a_plus[metric] = hi
        a_minus[metric] = lo
    return a_plus, a_minus


def _euclidean(row: Mapping, target: Mapping, metrics: Sequence) -> Decimal:
    '''TOPSIS Step 4（SDD 715）：D = sqrt(Σ_j (v_ij − A_j)²)，numeric.sqrt 内部 q12。'''
    total = numeric.ZERO
    for metric in metrics:
        delta = numeric.D(row[metric]) - numeric.D(target[metric])
        total = total + delta * delta
    return numeric.sqrt(total)


def topsis_closeness(matrix: Mapping, weights: Mapping, directions: Mapping) -> dict:
    '''TOPSIS Step 1-7（SDD 709-718）-> {key: C_i}，C_i ∈ [0,1]，输出前 q12
    （Step 7：不入分，但须可复现）。Step 5 的零分母（D+ + D− = 0，只可能是全部
    策略在全部指标上取值相同）走 safe_div 的 on_zero=ZERO：C 记 0，于是全体并列、
    rank_desc 给同一名次；此时 Spearman 因零方差而 undefined（rho 记 None），
    不存在「悄悄给个名次」。'''
    keys, metrics = _check_shape(matrix)
    weighted = weighted_matrix(matrix, weights, keys, metrics)
    a_plus, a_minus = ideal_solutions(weighted, directions)
    out = {}
    for key in keys:
        d_plus = _euclidean(weighted[key], a_plus, metrics)
        d_minus = _euclidean(weighted[key], a_minus, metrics)
        out[key] = numeric.safe_div(d_minus, numeric.q12(d_plus + d_minus),
                                    on_zero=numeric.ZERO)
    return out


def dimensionless(column: Sequence, method: str) -> tuple:
    '''GRA Step 2（SDD 723）：initial = 初值化（除以序列首值），mean = 均值化（除以
    均值），两者都由配置显式切换（「两种都要跑并比对」属 NORM_SWAP 敏感性，在
    sensitivity.py 里做，本模块只负责可切）。参考值为 0 时除法 genuinely undefined
    -> 报错，不回落成第三种口径（那是发明数值，R-12）。'''
    vals = [numeric.D(v) for v in column]
    if not vals:
        raise TriangulationError('dimensionless 收到空列')
    if method == GRA_NORM_INITIAL:
        ref = vals[0]
    elif method == GRA_NORM_MEAN:
        ref = numeric.mean(vals)
    else:
        raise TriangulationError('gra_norm 必须是 ' + repr(GRA_NORM_METHODS)
                                 + ' 之一，got ' + repr(method))
    if numeric.eq_tol(ref, numeric.ZERO):
        raise TriangulationError('GRA 无量纲化参考值为 0（gra_norm=' + str(method)
                                 + '），关联度未定义')
    return tuple(numeric.safe_div(v, ref, on_zero=numeric.ZERO) for v in vals)


def reference_sequence(scaled: Mapping, directions: Mapping) -> dict:
    '''GRA Step 1（SDD 722）：x_0 = 各指标当期最优值构成的理想策略，「最优」由方向
    决定（正向 max / 负向 min）。顺序口径：先无量纲化再取 x_0（教科书口径；同一列
    的同一个单调线性变换不改变最优值的取法，与 SDD 的步骤编号先后无冲突）。'''
    keys = tuple(sorted(scaled))
    x0 = {}
    for metric in present_metrics(scaled):
        column = [numeric.D(scaled[k][metric]) for k in keys]
        x0[metric] = numeric.q12(min(column) if _direction(directions, metric) < 0
                                 else max(column))
    return x0


def gra_coefficients(matrix: Mapping, directions: Mapping, rho,
                     method: str = GRA_NORM_INITIAL) -> tuple:
    '''GRA Step 2-4（SDD 724-725 逐字）-> (ξ[key][metric], x_0[metric])：
    ξ_ij = (min Δ + ρ·max Δ) / (Δ_ij + ρ·max Δ)，min Δ / max Δ 取整张差序列的全局
    极值（教科书口径）。ρ 必填且必须 > 0（R-12：ρ=0 让 ξ 退化成 0/0，负 ρ 无定义）。
    差序列全为 0（每个策略在每个指标上都等于参考序列）时分母为 0，走 safe_div 的
    on_zero=None -> 报错：此时关联度 genuinely undefined，写死成 1 就是发明数值。'''
    rho_d = numeric.from_float(rho) if isinstance(rho, float) else numeric.D(rho)
    if rho_d <= numeric.ZERO:
        raise TriangulationError('GRA 分辨系数 rho 必须 > 0，got ' + str(rho_d))
    keys, metrics = _check_shape(matrix)
    scaled_cols = {m: dimensionless([matrix[k][m] for k in keys], method)
                   for m in metrics}
    scaled = {k: {m: scaled_cols[m][i] for m in metrics} for i, k in enumerate(keys)}
    x0 = reference_sequence(scaled, directions)
    deltas = {k: {m: numeric.q12(abs(scaled[k][m] - x0[m])) for m in metrics}
              for k in keys}
    flat = [deltas[k][m] for k in keys for m in metrics]
    lo = numeric.q12(min(flat))
    hi = numeric.q12(max(flat))
    numerator = numeric.q12(lo + rho_d * hi)
    xi = {}
    for key in keys:
        row = {}
        for metric in metrics:
            value = numeric.safe_div(
                numerator, numeric.q12(deltas[key][metric] + rho_d * hi), on_zero=None)
            if value is None:
                raise TriangulationError('GRA 关联系数未定义：差序列全为 0（指标 '
                                         + metric + '），拒绝写死成 1（R-12）')
            row[metric] = value
        xi[key] = row
    return xi, x0


def gra_relatedness(matrix: Mapping, weights: Mapping, directions: Mapping, rho,
                    method: str = GRA_NORM_INITIAL) -> dict:
    '''GRA Step 5-6（SDD 726-727）：γ_i = Σ_j w_j · ξ_ij，降序即 GRA 排名。'''
    xi, _x0 = gra_coefficients(matrix, directions, rho, method)
    return {key: numeric.weighted_sum(
        [(numeric.D(weights[m]), xi[key][m]) for m in sorted(xi[key])])
        for key in sorted(xi)}


def gra_by_metric(matrix: Mapping, directions: Mapping, rho,
                  method: str = GRA_NORM_INITIAL) -> dict:
    '''GRA Step 7 副产物（SDD 728 / 1028）：逐指标平均关联度，供 diagnostics 的指标
    效度诊断使用。本模块只算不判：CONTENT_VALIDITY_DOUBT 之类的结论属 diagnostics
    （在写的邻居模块，不 import、不代做，R-1 / R-7）。'''
    xi, _x0 = gra_coefficients(matrix, directions, rho, method)
    keys = tuple(sorted(xi))
    metrics = tuple(sorted(xi[keys[0]]))
    return {m: numeric.mean([xi[k][m] for k in keys]) for m in metrics}

def rank_desc(values: Mapping) -> dict:
    '''降序名次（SDD 717 / 727）：并列取同名次，competition ranking（名次 = 1 +
    严格更优的个数），因为 TriangulationStrategyRow 的两个 rank 列是 StrictInt
    （H-4）装不下平均秩；并列比较走 numeric.eq_tol（V-9 的 1e-12）。Spearman 用的
    **不是**这里的 int 名次，而是 numeric.rank_average 的平均秩。'''
    keys = tuple(sorted(values))
    vals = {k: numeric.D(values[k]) for k in keys}
    out = {}
    for key in keys:
        out[key] = 1 + sum(1 for other in keys
                           if vals[other] > vals[key]
                           and not numeric.eq_tol(vals[other], vals[key]))
    return out


def _pair(left: Mapping, right: Mapping, keys: Sequence):
    '''一对排序的 Spearman。某一侧零方差时 numeric.spearman 抛
    DivisionUndefinedError（相关性 genuinely undefined），这里回 None：
    TriangulationReport 的四个 rho 列都是 nullable（models.py 1149-1152），
    未定义的结论不报数、也不编一个数出来。'''
    # RC-1（CONSUMPTION-TODO 第 3 条·模块侧）：回 None 的「不编数」行为保持原样，
    # 但不再静默——run() 经 _flags() 把该 None 登记为 SPEARMAN_ZERO_VARIANCE 塞进 flags。
    try:
        return numeric.spearman([left[k] for k in keys], [right[k] for k in keys])
    except numeric.DivisionUndefinedError:
        return None


def rhos(main: Mapping, topsis: Mapping, gra: Mapping) -> RhoSet:
    '''SDD 732-736 的三对相关，**就是这三对，不换组合**：
    rho_main_topsis = spearman(composite_absolute, TOPSIS 贴近度)、
    rho_main_gra = spearman(composite_absolute, GRA 关联度)、
    rho_topsis_gra = spearman(TOPSIS 贴近度, GRA 关联度)，
    mean_rho = (rho_main_topsis + rho_main_gra) / 2（不含第三对）。入参都是
    key -> Decimal 的排序值，平均秩由 numeric 处理，故并列秩自动取平均秩。'''
    keys = tuple(sorted(main))
    for name, mapping in (('topsis', topsis), ('gra', gra)):
        if tuple(sorted(mapping)) != keys:
            raise TriangulationError('三对 Spearman 要求策略集完全一致，' + name
                                     + ' 不一致')
    if len(keys) < MIN_POPULATION:
        raise TriangulationError('三角验证至少需要 ' + str(MIN_POPULATION)
                                 + ' 个可评价策略，got ' + str(len(keys)))
    for name, mapping in (('main', main), ('topsis', topsis), ('gra', gra)):
        for key in keys:
            if mapping[key] is None:
                raise TriangulationError(name + ' 排序在 ' + repr(key)
                                         + ' 上是空值，无法做秩相关')
    r_mt = _pair(main, topsis, keys)
    r_mg = _pair(main, gra, keys)
    r_tg = _pair(topsis, gra, keys)
    mean_rho = None
    if r_mt is not None and r_mg is not None:
        mean_rho = numeric.mean([r_mt, r_mg])
    return RhoSet(r_mt, r_mg, r_tg, mean_rho)


def verdict(mean_rho, threshold):
    '''SDD 737-738：mean_rho >= divergence_threshold -> METHOD_AGREEMENT，否则
    METHOD_DIVERGENCE（首屏警示 + 人工复核 + 本期暂停淘汰）。threshold 是必填治理
    值，无默认（R-12）。mean_rho 为 None（某对排序零方差）时不给结论、回 None：
    models.py 1134 的注释正是「a disabled or incomplete run has no verdict」。'''
    # RC-1（CONSUMPTION-TODO 第 3 条·模块侧）：mean_rho 为 None（某对零方差）时不给
    # 结论、回 None 的行为保持原样，但由 run() 的 _flags() 带码披露，不静默。
    if mean_rho is None:
        return None
    limit = numeric.from_float(threshold) if isinstance(threshold, float) \
        else numeric.D(threshold)
    return RC_AGREEMENT if numeric.D(mean_rho) >= limit else RC_DIVERGENCE


def _flags(agreement, rho_set, dropped=()):
    '''三角标记的构造（RC-1 / CONSUMPTION-TODO 第 3 条·模块侧）：有结论记结论码；
    三对 rho 或 mean_rho 任何一列为 None（_pair/verdict 的零方差回 None，不编数）就
    加记 SPEARMAN_ZERO_VARIANCE，供 reports._section_8 的「三角标记」与「Spearman
    相关无定义」披露位消费（V-14）。本码 WARN 且不阻断（M26 [L1022] 不入分，
    blocks_run=False），与 verdict 一致时结论码照旧单独成 flag。

    dropped = 本次被显式排除的零方差指标（zero_variance_metrics）。排除是降级，降级
    必须带注册码（V-14），故加记 INACTIVE_METRIC —— 与 normalize.py:111 的
    CODE_INACTIVE / [L943] 给同一条零变异归一化行落的码同一口径，注册表措辞「指标零
    变异，已剔除并预警」逐字就是这里做的事，不新注册码（reason_codes.py 单点，R-15）。
    两枚码语义不重叠、也不互相顶替：SPEARMAN_ZERO_VARIANCE 说的是**一对排序**无秩
    相关可言，INACTIVE_METRIC 说的是**一个指标列**无变异可比；恒定列被排除后三对 rho
    仍可能全有定义，那时只出后者，挪用前者即虚报。默认 dropped=() 让既有非零方差路径
    逐位不变（tests/test_reason_codes.py 钉死 flags 元组，R-14）。
    '''
    codes = [] if agreement is None else [agreement]
    if (rho_set.rho_main_topsis is None or rho_set.rho_main_gra is None
            or rho_set.rho_topsis_gra is None or rho_set.mean_rho is None):
        codes.append(RC.SPEARMAN_ZERO_VARIANCE.value)
    if dropped:
        codes.append(RC_INACTIVE)
    return tuple(codes)


def run(scores, normalized, weights, config, *, directions):
    '''SDD 1026 的签名 def run(scores, normalized, weights, config) ->
    TriangulationReport；directions 是必填注入（keyword-only），因为三个入参都没有
    direction 列，而理想解与参考序列都要方向（缺口见模块 docstring）。

    **输出仅三角验证，不得用于对外披露排名（RK-5）**：不产出任何等级、分数或综合分
    列，报告只有名次、rho、结论与逐指标平均关联度；它对分数与等级的影响恒等于零
    （不入分）。可关（SDD 1030）：enabled = false 时返回 **None**，不构造任何三角
    验证对象，关闭由 disabled_flag(config) 落 TRIANGULATION_DISABLED，不静默。
    入参全部只读（INV-3）：weights 只被读取，scores / normalized 是 frozen 模型。'''
    if not is_enabled(config):
        return None
    if not isinstance(scores, ScoreFrame):
        raise TriangulationError('scores 必须是 ScoreFrame，got '
                                 + type(scores).__name__)
    if not isinstance(normalized, NormalizedFrame):
        raise TriangulationError('normalized 必须是 NormalizedFrame，got '
                                 + type(normalized).__name__)
    section = _section(config)
    rho = _number(section, CFG_RHO)
    threshold = _number(section, CFG_THRESHOLD)
    method = str(_need(section, CFG_GRA_NORM))
    if method not in GRA_NORM_METHODS:
        raise TriangulationError(CFG_SECTION + '.' + CFG_GRA_NORM + ' 必须是 '
                                 + repr(GRA_NORM_METHODS) + ' 之一，got ' + repr(method))
    periods = sorted({row.period for row in scores.rows})
    if len(periods) > 1:
        raise MultiPeriodError('TriangulationReport 没有 period 列，run() 只接受单期，'
                               'got ' + ', '.join(periods))
    main = {}
    for row in scores.rows:
        if row.composite_absolute is None:
            continue  # 不出分的策略不进任何分母（SDD 1004 同一口径）
        key = (row.strategy_id, row.version_id, row.period)
        if key in main:
            raise TriangulationError('scores 出现重复行: ' + repr(key))
        main[key] = row.composite_absolute
    matrix = {}
    for row in normalized.rows:
        key = (row.strategy_id, row.version_id, row.period)
        if key in main:  # 不可评价策略的归一化行不进三角验证矩阵
            matrix.setdefault(key, {})[row.metric_id] = row.norm_value
    absent = tuple(k for k in sorted(main) if k not in matrix)
    if absent:
        raise TriangulationError('normalized 缺策略行: '
                                 + ', '.join(repr(k) for k in absent))
    if len(main) < MIN_POPULATION:
        raise TriangulationError('三角验证至少需要 ' + str(MIN_POPULATION)
                                 + ' 个可评价策略，got ' + str(len(main)))
    # 零方差列的显式降级（见 zero_variance_metrics）：GRA 的两种签认口径在这种列上参考
    # 值恒为 0，dimensionless 按自己的设计拒绝且**不回落第三种口径**。处置不是给恒定列
    # 编一个归一化、也不是把它当成 0 或 1 塞进去，而是把该列从**本次**比对的贡献中排除
    # 并带 RC_INACTIVE 进 flags 披露。TOPSIS 侧一并排除：恒定列的 A+ 与 A- 相同、对
    # D+ / D- 的贡献恒为 0，本就无信息，一并摘掉只是让两法看同一组指标（对 TOPSIS 名次
    # 无任何数值影响，见 tests/test_triangulation_zero_variance.py 的对照断言）。
    # metric_weights 照 [L954] 既有口径在「实际参评指标」上重归一到 1，被排除的列不是
    # 参评列 —— 与 normalize 给 INACTIVE_METRIC 行落码、Step5 不计入的处置同一口径，
    # 不新设权重规则（R-12）。
    # 不入分（[L1348]）：以上只影响本旁路的名次与 rho，Step1-7 的任何一格数值都不经过
    # 这里，故 score_card / grade_ledger 与 reproducibility_hash 的值面不变。
    dropped = zero_variance_metrics(matrix)
    live = drop_metrics(matrix, dropped)
    if dropped and not present_metrics(live):
        raise TriangulationError(
            '本期参评的 ' + str(len(dropped)) + ' 个指标全部零方差（'
            + '、'.join(dropped) + '）：TOPSIS / GRA 没有任何可比对的信息，三角验证'
            + '未定义（' + RC_INACTIVE + '）。不编造第三种归一化口径，也不把恒定列'
            + '当成 0 或 1（R-12）')
    w = metric_weights(live, weights)
    dirs = _check_directions(directions, present_metrics(live))
    closeness = topsis_closeness(live, w, dirs)
    relatedness = gra_relatedness(live, w, dirs, rho, method)
    r = rhos(main, closeness, relatedness)
    agreement = verdict(r.mean_rho, threshold)
    topsis_rank = rank_desc(closeness)
    gra_rank = rank_desc(relatedness)
    rows = tuple(TriangulationStrategyRow(
        strategy_id=key[0], version_id=key[1], topsis_rank=topsis_rank[key],
        gra_rank=gra_rank[key]) for key in sorted(main))
    return TriangulationReport(
        rows=rows, rho_main_topsis=r.rho_main_topsis, rho_main_gra=r.rho_main_gra,
        rho_topsis_gra=r.rho_topsis_gra, mean_rho=r.mean_rho, agreement=agreement,
        gra_by_metric=gra_by_metric(live, dirs, rho, method),
        flags=_flags(agreement, r, dropped))


def veto(report) -> TriangulationVeto:
    '''把三角验证结论翻成**显式的、不可被加权补偿的**否决标记（SDD 740）。非补偿语义
    由数据形状保证：TriangulationVeto 只有 bool 与 reason_code，没有任何数值字段，
    所以既不能进加权线性和（没有数可乘权重），也不能表现成扣分（没有 delta 可减）；
    一票即否决，别的方法多一致也抵不掉。usable_for_elimination 镜像 grade_ledger
    同名列（SDD 740：台账写着 false 就是真否决），写台账本身属渲染层。

    关闭状态下的明确定义行为：report 为 None -> 不否决，但 codes 带
    TRIANGULATION_DISABLED，关闭不静默。agreement 为 None（某对排序零方差，无结论）
    -> 不否决、codes 为空，「无结论」由报告里的 mean_rho / agreement = None 自己
    披露，不伪装成一致。'''
    if report is None:
        return TriangulationVeto(False, (RC_DISABLED,), True)
    if not isinstance(report, TriangulationReport):
        raise TriangulationError('veto 只接受 TriangulationReport 或 None，got '
                                 + type(report).__name__)
    if report.agreement == RC_DIVERGENCE:
        return TriangulationVeto(True, (RC_DIVERGENCE,), False)
    if report.agreement == RC_AGREEMENT:
        return TriangulationVeto(False, (RC_AGREEMENT,), True)
    return TriangulationVeto(False, (), True)


def is_vetoed(report) -> bool:
    '''便捷判定：本期是否因方法分歧而不得据此淘汰策略。'''
    return veto(report).vetoed
