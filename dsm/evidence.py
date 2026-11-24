'''dsm.evidence -- Step 3 证据强度分级（A/B/C/D）：五步短路 + 默认 GATE_ONLY。

守护编号 G-02（证据门禁侧）；G-13（卡 PARTIAL 上限压至 C）由判定顺序承载。
唯一事实来源：M23-evidence [L972]-[L983]、M41-cel [L1886]-[L1924]、
M40-evidence-discipline。分池禁混排（P-6）属 pooling，本模块不做分池。

四条硬点，逐条对应 [L977]-[L979] 与 [L1894]-[L1898]：
  1) 五步**按序短路**：① 卡缺失 -> D（NOT_ASSESSED）；② randomized + 有对照组
     + 事前成功判定（含显著性口径）-> A；③ 准实验（须写方法名与假设）-> B；
     ④ 仅观测 -> C；⑤ C 类未写 interpretation_limit -> 降为 D。①②③ 任一命中
     即在 _verdict 的循环里 return，后面的步骤根本不执行。
  2) 默认 evidence_mode = GATE_ONLY：证据等级**只当门禁**（封顶 / 分池 / 一级库
     准入），**不乘入分数**。本模块不产出分数也不产出系数；DISCOUNT 只保留接口，
     启用须另立 ADR（[L978]），故直接拒绝，绝不静默给一个乘数（V-14）。
  3) A 类**保守**（宁低不高）：success_criteria 是自由文本，只能用**外置可审计的
     关键词清单**识别显著性口径，清单外一律不认 A，**禁止模型猜测**（RK-4，
     [L979]）；卡非 COMPLETE、对照非 RANDOMIZED 同样不认 A/B，落到更低等级。
  4) CEL-0 消费（[L1894]-[L1898]）：evidence_source 首版恒为 CARD_ONLY；
     cel.enabled = false 时七个预留字段一律不参与判定，非空即抛
     CelDisabledDataPresentError（RK-15）；单向 CEL -> T4 -> evidence.py，
     本模块不得反向调用 CEL（[L981]）。
  5) 出桥范围按**评价期**过滤（D-EVID-01 / ORCH-37 第 9 条）：本期评价范围
     （[L1063] ②）= 传入事实行覆盖到的 (strategy_id, version_id)；本期无事实行的
     设计卡不出证据行（否则「证据结构 A/B/C/D 计数」的分母会被已退役版本
     撑大，[L1003] / [L1459]），但**必须披露**（V-14，EvidenceScope.excluded），且卡
     本身不得删除 —— G-08 的版本断裂判定（[L1117]）要用 S-005/v1 这张退役卡。
'''
from __future__ import annotations

from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, model_validator

from dsm.config import AppConfig
from dsm.models import (DesignCardRow, EvidenceFrame, EvidenceMode, EvidenceRow,
                        EvidenceSource, MetricFactRow, StrictBool)
from dsm.reason_codes import RC

# eval_config 的路径。SDD 只给概念名（[L978] / [L1898]）没给 yaml 键名，拼写在
# 这里钉一次，与 attainment.params_from_config 的 CFG_* 同一处理办法。
CFG_EVIDENCE_KEY = 'evidence'
CFG_MODE_KEY = 'mode'
CFG_KEYWORDS_KEY = 'significance_keywords'
CFG_CEL_KEY = 'cel'
CFG_CEL_ENABLED_KEY = 'enabled'
CFG_KEYS = (CFG_MODE_KEY, CFG_KEYWORDS_KEY)

# [L1895] 首版恒为 CARD_ONLY：CEL_ESTIMATED 只能由二期 CEL-3 桥接产出，首版没有
# 桥接，所以本模块没有任何分支能把它改成别的值。
SOURCE_V1: EvidenceSource = 'CARD_ONLY'

# [L977] ② 的 randomized 设计：EvalMethod 九值里属随机分流的三个。
RANDOMIZED_METHODS = ('AB_TEST', 'RCT', 'HOLDOUT')
# [L977] ③ 准实验四类里在 EvalMethod 上有字面对应的三个。GEO / SWITCHBACK 与
# 时间断点的归属 digest 未给，一律不进 B（保守降到 ④ 的 C），已上报缺口。
QUASI_METHODS = ('DID', 'SYNTHETIC_CONTROL', 'PSM')

# [L1894] CEL-0 预留的七个可空字段：cel 关闭时一律不参与判定（[L1898]）。
CEL_RESERVED_FIELDS = ('incremental_value', 'incremental_ci_lower',
                       'incremental_ci_upper', 'estimator_method',
                       'experiment_id', 'holdout_id', 'mde_ok')


class EvidenceError(ValueError):
    '''Base class for every evidence contract violation.'''


class EvidenceConfigError(EvidenceError):
    '''A governance value this module needs is absent from eval_config.'''


class EvidenceDiscountError(EvidenceError):
    '''evidence_mode = DISCOUNT 未立 ADR：本模块拒绝给出任何乘数（[L978]）。'''


class CelDisabledDataPresentError(EvidenceError):
    '''cel.enabled = false 但 CEL-0 预留字段非空（RK-15，[L1898]）。'''


class EvidenceParams(BaseModel):
    '''三个治理入参，全部必填、无默认值（H-5：默认 GATE_ONLY 属配置层）。

    significance_keywords 就是 [L979] 的外置可审计关键词清单：从配置进来，不写死
    在代码里；清单为空 -> 永不认 A；空串项会匹配一切 success_criteria，一并拒。
    '''

    model_config = ConfigDict(frozen=True, extra='forbid')

    evidence_mode: EvidenceMode  # [L978] GATE_ONLY | DISCOUNT
    cel_enabled: StrictBool  # [L1898] 单开关，默认关闭在配置层
    significance_keywords: tuple[str, ...]  # [L979] 外置可审计清单

    @model_validator(mode='after')
    def _check(self):
        for keyword in self.significance_keywords:
            if not keyword.strip():
                raise ValueError(
                    'significance_keywords 含空白项，会匹配一切 success_criteria')
        return self


def params_from_config(config: AppConfig) -> EvidenceParams:
    '''从 eval_config 原始树里读出 evidence / cel 两块，或缺失即拒。什么都不默认：
    缺块、缺键、类型不对一律从 EvidenceConfigError 出去，因为自己发明一个
    evidence_mode 或一份关键词清单就是发明业务口径（H-5 / R-12）。'''
    tree = config.eval_config
    if not isinstance(tree, Mapping):
        raise EvidenceConfigError('eval_config must be a mapping')
    where = 'eval_config.' + CFG_EVIDENCE_KEY
    block = tree.get(CFG_EVIDENCE_KEY)
    if not isinstance(block, Mapping):
        raise EvidenceConfigError('no ' + where + ' block in the configuration')
    missing = tuple(k for k in CFG_KEYS if k not in block)
    if missing:
        raise EvidenceConfigError(where + ' is missing: ' + ', '.join(missing))
    keywords = block[CFG_KEYWORDS_KEY]
    if isinstance(keywords, (str, bytes)) or not isinstance(keywords, Iterable):
        raise EvidenceConfigError(
            where + '.' + CFG_KEYWORDS_KEY + ' must be a list')
    cel = tree.get(CFG_CEL_KEY)
    enabled = cel.get(CFG_CEL_ENABLED_KEY) if isinstance(cel, Mapping) else None
    if not isinstance(enabled, bool):
        raise EvidenceConfigError(
            'eval_config.' + CFG_CEL_KEY + '.' + CFG_CEL_ENABLED_KEY
            + ' must be a bool')
    return EvidenceParams(
        evidence_mode=block[CFG_MODE_KEY], cel_enabled=enabled,
        significance_keywords=tuple(str(k) for k in keywords))


# ---------------------------------------------------------------------------
# 索引与 CEL-0 契约守卫。纯函数：无时钟、无 I/O、无全局状态（H-8）。
# ---------------------------------------------------------------------------
def _card_index(design_cards) -> dict:
    '''(strategy_id, version_id) -> DesignCardRow。T4 的粒度就是策略 x 版本
    （[L1102]），重复行会让判定有二义，直接拒。'''
    index = {}
    for card in design_cards:
        if not isinstance(card, DesignCardRow):
            raise EvidenceError(
                'design_cards entries must be DesignCardRow, got '
                + type(card).__name__)
        key = (card.strategy_id, card.version_id)
        if key in index:
            raise EvidenceError('duplicate design_cards row: ' + str(key))
        index[key] = card
    return index


# 评价期范围过滤的判据标识与披露码槽。
# derived: [L1063] ②「本期评价范围与覆盖率」+ ⑥「证据结构（A/B/C/D 计数与
#   NOT_ASSESSED 明细）」+ [L942]「标准化在**池内**进行（biz_domain ×
#   evidence_class）」+ [L1117]「跨版本不做趋势比较」；裁决 ORCH-37 第 9 条、
#   A1CPREP §6-B.2 / §6-B.3。原文给了「本期评价范围」这个量，但没有逐字规定它
#   等于「本期有事实行的 (strategy_id, version_id) 对」，故判据等级 = derived，
#   待主控签认。
# PLACEHOLDER: dsm/reason_codes.py 现有注册码里没有「本期无事实行 -> 不在评价期
#   范围」这一类（NOT_ASSESSED 是 BLOCK 级「本期不可评价」，GR_VERSION_BREAK 是
#   Step6 的版本断点标注，语义都不等于范围过滤），本包不得自行注册（主控单点
#   管理）。需求见 dsm_stage/EVID-1/NEED-CODES.md；签认后把这个常量换成注册码。
SCOPE_BASIS_NO_FACT_ROW = 'NO_FACT_ROW_IN_EVAL_PERIOD'
PLACEHOLDER_OUT_OF_PERIOD_CODE = 'PLACEHOLDER'


class ScopeExclusion(BaseModel):
    '''一条「设计卡存在但不在本期评价范围」的披露（V-14：过滤不得静默丢弃）。

    reason_code 目前是 PLACEHOLDER，但它**必须是显式字段**：调用侧（spine / cli /
    report.md ②⑥ 段）拿这个元组去披露，而不是自己猜哪些卡被过滤掉了。basis 记
    判据本身，便于第二人复算（V-3）。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    strategy_id: str
    version_id: str
    basis: str
    reason_code: str


class EvidenceScope(BaseModel):
    '''本期评价范围（[L1063] ②）+ 被范围过滤掉的设计卡披露位。

    period_established = False 表示传入的事实行为空：此时「本期」根本无法界定，
    任何卡都判不出「不在本期范围内」，于是一张都不过滤（V-14：既不静默收窄口径，
    也不把全部卡静默丢掉）。这个标志同样是披露，不是内部细节。'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    in_period: tuple[tuple[str, str], ...]
    excluded: tuple[ScopeExclusion, ...]
    period_established: bool


def _fact_pairs(facts) -> frozenset:
    '''T3 事实行覆盖到的 (strategy_id, version_id) 集合 = 本期评价范围的载体。'''
    pairs = set()
    for fact in facts:
        if not isinstance(fact, MetricFactRow):
            raise EvidenceError(
                'facts entries must be MetricFactRow, got ' + type(fact).__name__)
        pairs.add((fact.strategy_id, fact.version_id))
    return frozenset(pairs)


def evaluation_scope(design_cards, facts) -> EvidenceScope:
    '''按评价期过滤设计卡（D-EVID-01 的修法，ORCH-37 第 9 条）。

    判据只有一条：**该 (strategy_id, version_id) 在传入的事实行里有没有本期事实**。
    有 -> 在本期评价范围内；没有 -> 不在范围内，但**卡本身不被删除、不被隐藏**，
    而是原样进 excluded 披露位（V-14）。G-08 的版本断裂判定要用的正是 S-005/v1
    这张已退役卡（[L1117] / [L1121] / [L1123]），所以过滤只作用于「本期评价范围
    统计」这一个口径，绝不作用于卡的可见性。

    不采用「status = RETIRED + offline_date 早于评价期」这条判据：T4 设计卡上没有
    status / offline_date 两列（它们在 T2 strategy_master，[L1121] / [L1123]），
    本层按分层纪律不得反向去取 T2，[L976] 的签名里也没有 master 入参。两条判据
    只用一条，不叠加凑数。'''
    card_keys = tuple(sorted(_card_index(design_cards)))
    in_period = _fact_pairs(facts)
    if not in_period:
        return EvidenceScope(in_period=card_keys, excluded=(),
                             period_established=False)
    excluded = tuple(
        ScopeExclusion(strategy_id=sid, version_id=ver,
                       basis=SCOPE_BASIS_NO_FACT_ROW,
                       reason_code=PLACEHOLDER_OUT_OF_PERIOD_CODE)
        for sid, ver in card_keys if (sid, ver) not in in_period)
    return EvidenceScope(in_period=tuple(sorted(in_period)), excluded=excluded,
                         period_established=True)


def _cel_guard(card: DesignCardRow, cel_enabled: bool) -> None:
    '''[L1898] RK-15：cel.enabled = false 时预留字段非空必须抛错，不得静默忽略
    （V-14）。开启时首版也没有 CEL 计算（[L1895] 恒 CARD_ONLY），所以这些字段在
    两个方向上都不参与判定。'''
    if cel_enabled:
        return
    for field in CEL_RESERVED_FIELDS:
        if getattr(card, field) is not None:
            raise CelDisabledDataPresentError(
                'cel.enabled 为 false 但 ' + card.strategy_id + '/'
                + card.version_id + ' 的 CEL-0 预留字段 ' + field
                + ' 非空，按 RK-15 拒绝参与判定')


def _significance_hit(success_criteria: str, keywords: Iterable[str]) -> bool:
    '''[L979] 的关键词识别：casefold 后的子串命中，不用正则、不用模型猜测。
    清单为空 -> 恒 False -> 永不认 A（保守方向）。'''
    text = success_criteria.casefold()
    for keyword in keywords:
        needle = keyword.casefold()
        if needle and needle in text:
            return True
    return False


def _row(locator, evidence_class, reason, limit) -> EvidenceRow:
    '''[L980] 的五列 + 定位键。evidence_source 首版恒为 CARD_ONLY（[L1895]）；
    control_group_id 在 v1 没有输入来源（T4 无对照组 ID 列，holdout_id /
    experiment_id 属 CEL-0 预留且 cel 关闭时不得参与判定），故恒为 None，
    已上报缺口，不自行编造一个 ID。'''
    return EvidenceRow(
        strategy_id=locator[0], version_id=locator[1],
        evidence_class=evidence_class, evidence_reason=reason,
        evidence_source=SOURCE_V1, control_group_id=None,
        interpretation_limit=limit)


# ---------------------------------------------------------------------------
# [L977] 的五步。前三步命中即短路，后两步只在前三步全部判否时执行。
# ---------------------------------------------------------------------------
def _step1_card_missing(card, keywords):
    '''① 设计卡缺失 -> D（NOT_ASSESSED）。'''
    if card.card_status == 'MISSING':
        return ('D', RC.EVIDENCE_CARD_MISSING)
    return None


def _step2_randomized_a(card, keywords):
    '''② randomized=true 且有对照组与事前成功判定（含显著性口径）-> A。四要件全中
    才给 A，缺一即判否（返回 None 继续走 ③）：卡必须 COMPLETE（不完备的卡无法核对
    全部要件，G-13）、对照必须 RANDOMIZED、方法必须在随机分流集合里、
    success_criteria 必须命中外置清单（[L979]）。'''
    if card.card_status != 'COMPLETE':
        return None
    if card.control_arrangement != 'RANDOMIZED':
        return None
    if card.eval_method not in RANDOMIZED_METHODS:
        return None
    if not _significance_hit(card.success_criteria, keywords):
        return None
    return ('A', RC.EV_A_RANDOMIZED)


def _step3_quasi_b(card, keywords):
    '''③ 准实验（DID / 合成对照 / 分层匹配 / 时间断点，须写方法名与假设）-> B。
    方法名由 eval_method 承载，假设写在 alt_method_note（[L1171]，SDD 没有另给
    假设列，已上报缺口）。没写假设就不认 B，保守落到 ④ 的 C；卡 PARTIAL 同样不认
    B（G-13）。'''
    if card.card_status != 'COMPLETE':
        return None
    if card.eval_method not in QUASI_METHODS:
        return None
    note = card.alt_method_note
    if note is None or not note.strip():
        return None
    return ('B', RC.EV_B_QUASI)


def _step4_observational_c(card):
    '''④ 仅观测 -> C。走到这里说明 ①②③ 全部判否。
    卡 PARTIAL 时 reason 用注册码 EVIDENCE_CARD_PARTIAL（G-13 上限压至 C）。'''
    if card.card_status == 'PARTIAL':
        return ('C', RC.EVIDENCE_CARD_PARTIAL)
    return ('C', RC.EV_C_OBSERVATIONAL)


def _step5_c_without_limit(provisional, reason, card):
    '''⑤ C 类未写 interpretation_limit -> 降为 D。只对 ④ 产出的 C 生效：
    ①②③ 命中时早已 return，A/B/D 不会被本步改写。'''
    limit = card.interpretation_limit
    if limit is None or not limit.strip():
        return ('D', RC.EVIDENCE_C_NO_LIMIT)
    return (provisional, reason)


_SHORT_CIRCUIT_STEPS = (_step1_card_missing, _step2_randomized_a, _step3_quasi_b)


def _verdict(card, keywords) -> tuple:
    '''[L977] 的判定顺序，**按序短路**：①②③ 任一命中立即 return，④⑤ 不再执行；
    三步全部判否才走 ④ 给出 C，再由 ⑤ 决定要不要降为 D。返回 (等级, 注册码)。'''
    for step in _SHORT_CIRCUIT_STEPS:
        hit = step(card, keywords)
        if hit is not None:
            return hit
    provisional, reason = _step4_observational_c(card)
    return _step5_c_without_limit(provisional, reason, card)


def classify(design_cards: Sequence[DesignCardRow],
             facts: Sequence[MetricFactRow],
             config: AppConfig | None = None,
             *,
             params: EvidenceParams | None = None) -> EvidenceFrame:
    '''Step 3 的 [L976] 签名：设计卡 + 事实 + 配置，出一个 EvidenceFrame。
    config 与 params 必须且只能给一个。GATE_ONLY 语义（[L978]）在这里表现为：
    返回值只有 EvidenceFrame，没有分数、没有系数、没有任何可乘的东西。

    出桥范围 = evaluation_scope(design_cards, facts).in_period，即**本期评价范围**
    （[L1063] ②）：本期没有事实行的设计卡（如已退役的 S-005/v1）不出证据行，但由
    EvidenceScope.excluded 显式披露（V-14），卡本身仍留在 T4 里供 Step6 的版本断裂
    判定使用（G-08）。调用侧要披露时请调 evaluation_scope，不要自己重算范围，
    避免两处口径漂移。'''
    if (config is None) == (params is None):
        raise EvidenceError('pass exactly one of config or params')
    resolved = params if params is not None else params_from_config(config)
    if resolved.evidence_mode != 'GATE_ONLY':
        raise EvidenceDiscountError(
            'evidence_mode=' + str(resolved.evidence_mode)
            + ' 需另立 ADR 并纳入敏感性扰动维度（[L978]）；本模块不给任何乘数')

    scope = evaluation_scope(design_cards, facts)
    cards = _card_index(design_cards)
    keywords = resolved.significance_keywords
    rows = []
    for locator in scope.in_period:
        card = cards.get(locator)
        if card is None:
            # ① 卡整行缺失：连判定的材料都没有，D / NOT_ASSESSED。
            rows.append(_row(locator, 'D', RC.EVIDENCE_CARD_MISSING, None))
            continue
        _cel_guard(card, resolved.cel_enabled)
        evidence_class, reason = _verdict(card, keywords)
        rows.append(_row(locator, evidence_class, reason, card.interpretation_limit))
    return EvidenceFrame(rows=tuple(rows))
