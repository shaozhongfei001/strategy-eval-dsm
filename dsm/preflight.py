'''dsm.preflight -- Step 0 前置校验 C-01 ~ C-10（L2 门禁层）。

Authority: M22（[L896]-[L920]，C-01~C-10 唯一口径）、M28（[L1276]-[L1309] 降级矩阵
/ V-14）。守护 G-10（[L1412]）、G-11（[L1413]）。[L917] 三条 BLOCK 硬行为由
execute() 落地：只写 audit_bundle、退出码 2、不产 score_card（连空文件都不产）。
V-14（[L1307]）：降级 / 跳过 / 无从核验都产出带 registered reason_code + scope +
披露位置的 Finding；severity 取自 reason_codes.severity()，本模块不改写，故 BLOCK
码不可能被写成 WARN；coverage 的 None = 分母为 0（必伴 NOT_ASSESSED），不用 0 冒充。
run() 是纯函数：不读时钟（H-8 [L1271]）、不碰磁盘。config 是注入视图，缺字段抛
PreflightError 而不取默认值；AppConfig -> PreflightConfig 的映射属 config / cli 层。
'''
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from . import numeric
from .io_loaders import Inputs
from .models import (AnchorSetDoc, AuditBundle, DowngradeAction, PreflightFinding,
                     WeightVersionDoc)
from .reason_codes import RC, Severity
from .reason_codes import message as rc_message, owner_hint as rc_owner
from .reason_codes import severity as rc_severity

EXIT_OK, EXIT_BLOCK = 0, 2                       # [L917] BLOCK 退出码 2
AUDIT_FILE_NAME = 'audit.json'                   # [L1050] BLOCK 时唯一的产物
STATUS_PASS, STATUS_WARN, STATUS_BLOCK = 'PASS', 'WARN', 'BLOCK'      # [L916]
MONEY_UNIT, SUSPECT_FLAG = 'MONEY_MINOR', 'SUSPECT'   # [L1138] C-09 / [L1151] C-06
CARD_PARTIAL_CEILING, FROZEN, DRAFT = 'C', 'FROZEN', 'DRAFT'   # [L908] / [L1190]
RETIRED, EMPTIED_DIM_BLOCK = 'RETIRED', 2        # [L1123] / [L901] 清空维度数 >= 2
AUDIT_ONLY, LEDGER = 'audit + 退出码 2', '台账单独计数'    # [L1280]-[L1284] / [L1288]
# 只有这些码阻断整次运行；BLOCK 严重度但按策略降级的码（NOT_ASSESSED 等）只把该策略
# 记为不可评价，其余策略照出分（[L1288] / [L1292]），运行状态压到 WARN。
RUN_BLOCKING_CODES = frozenset((
    RC.WEIGHT_VERSION_INVALID.value, RC.WEIGHT_VERSION_DRAFT.value,
    RC.WEIGHT_VERSION_STALE.value, RC.WEIGHT_MISSING_WHATIF_RUN_ID.value,
    RC.CONFIG_SEMANTIC_ERROR.value, RC.CALIBER_VERSION_MISMATCH.value,
    RC.MONEY_NON_INTEGER.value, RC.DIMENSION_EMPTIED.value,
    # RC-1 / CONSUMPTION-TODO 第 2 条：设计卡重复键拒绝静默取后一行，显式拒绝
    # （M18 [L1102] T4 粒度 = 策略 × 版本；M22 [L917] BLOCK 只写 audit_bundle + 退出码 2）。
    RC.DESIGN_CARD_DUPLICATE_KEY.value))
# [L1278] 披露位置列，按 reason_code 查表；查不到就抛，不给默认值（V-14）。
DISCLOSURE = {
    RC.WEIGHT_VERSION_INVALID.value: AUDIT_ONLY, RC.WEIGHT_VERSION_DRAFT.value: AUDIT_ONLY,
    RC.WEIGHT_VERSION_STALE.value: AUDIT_ONLY, RC.CONFIG_SEMANTIC_ERROR.value: AUDIT_ONLY,
    RC.WEIGHT_MISSING_WHATIF_RUN_ID.value: AUDIT_ONLY, RC.DIMENSION_EMPTIED.value: AUDIT_ONLY,
    RC.CALIBER_VERSION_MISMATCH.value: AUDIT_ONLY, RC.MONEY_NON_INTEGER.value: 'audit',
    RC.METRIC_NOT_SIGNED.value: 'score_card flag + 报告附录', RC.DATA_STALE.value: 'score_card',
    RC.WEIGHT_REALLOCATED.value: 'WEIGHT_REALLOCATED', RC.ANCHOR_SET_STALE.value: '报告首屏',
    RC.MISSING_RATE_WARN.value: 'preflight findings', RC.RANK_REVERSAL_RISK.value: '报告首屏',
    RC.FIRST_PERIOD.value: 'preflight findings', RC.DATA_QUALITY_SUSPECT.value: 'score_card flag',
    RC.EVIDENCE_CARD_PARTIAL.value: 'evidence_reason', RC.MISSING_RATE_BLOCK.value: LEDGER,
    RC.NOT_ASSESSED.value: LEDGER, RC.EVIDENCE_CARD_MISSING.value: LEDGER,
    RC.DESIGN_CARD_DUPLICATE_KEY.value: AUDIT_ONLY}
CONFIG_FIELDS = ('period', 'period_ref_date', 'weight_version', 'anchor_set',
                 'signed_signoff_status', 'missing_rate_warn', 'missing_rate_block')
# audit_bundle 注入键（H-8：run_id / run_at 不由本模块读时钟；reproducibility_hash
# 的算法属 audit.py [L1052]，本包不重算）。
AUDIT_CONTEXT_FIELDS = ('run_id', 'run_at', 'dsm_version', 'design_version',
                        'cel_contract_version', 'config_snapshot_sha256', 'seed',
                        'input_fingerprints', 'sensitivity_schemes', 'reproducibility_hash')


class PreflightError(ValueError):
    '''拒绝继续（config 视图缺字段 / reason_code 无披露位置）；退出码归 cli.py。'''


def _f(code, reason, scope, detail):
    # Finding 唯一构造口：severity / owner_hint / 披露位置 / blocks_run 全由注册表推导，
    # 调用方无法把 BLOCK 码写成 WARN，也无法漏掉披露位置（V-14）。
    value = getattr(reason, 'value', reason)
    if value not in DISCLOSURE:
        raise PreflightError('reason_code ' + value + ' 没有登记的披露位置')
    return Finding(code, value, rc_severity(value), scope, detail, rc_owner(value),
                   DISCLOSURE[value], value in RUN_BLOCKING_CODES)


def _minor_ok(value) -> bool:
    # [L908] C-09：最小货币单位整数；小数与非数值（float / bool / 非数字串）都不合格，
    # 只走 numeric.as_minor（V-9），本模块不自建口径。
    if value is None:
        return True
    try:
        numeric.as_minor(value)
        return True
    except (numeric.NumericError, ArithmeticError, TypeError, ValueError):
        return False


def _sum(weights) -> Decimal:
    return sum((numeric.D(w) for w in weights), numeric.ZERO)


@dataclass(frozen=True)
class Finding:
    # 一条 C-0x 判定。契约的 PreflightFinding 只有 code / severity / message 三列
    # （B-019 待裁决），其余四列由本类承载并压进 to_audit_finding() 的 message。
    code: str            # [L900] C-01 ~ C-10
    reason_code: str     # RC.<NAME>.value（V-14）
    severity: Severity   # 取自 reason_codes.severity()，本模块不改写
    scope: str           # run / weight_version:x / dim:x / metric:x / strategy:x
    detail: str
    owner_hint: str
    disclosure: str      # [L1278] 披露位置
    blocks_run: bool

    def to_audit_finding(self) -> PreflightFinding:
        # [L1051] item 12：code 是检查编号（models.py 明示它不是 reason_code）
        return PreflightFinding(code=self.code, severity=self.severity, message=' | '.join(
            (self.reason_code, rc_message(self.reason_code), 'scope=' + self.scope,
             self.detail, '披露=' + self.disclosure, 'owner=' + self.owner_hint)))


@dataclass(frozen=True)
class PreflightConfig:
    # run() 的 config 入参（[L915]）；digest 未给的业务数值一律必填注入、无默认。
    period: str
    period_ref_date: date          # 评价期日期基准（C-01 / C-05 / C-10）
    weight_version: WeightVersionDoc
    anchor_set: AnchorSetDoc | None
    signed_signoff_status: tuple   # C-02「已签认」取值集合（[L1141] open code set）
    missing_rate_warn: Decimal     # C-04 warn 阈
    missing_rate_block: Decimal    # C-04 block 阈


@dataclass(frozen=True)
class PreflightResult:
    # [L916] status + findings + coverage_after_drop + 降级台账，不含任何 score_card
    # 载荷（[L917]）。coverage 分母取指标字典全量，故剔除未签认（G-10）、剔除 SUSPECT
    # （C-06）与缺失（C-04）都会让它下降。重归一后的权重不在本包产出（[L954] 归
    # aggregate），此处只交 dropped_metrics / emptied_dims。
    status: str
    exit_code: int
    findings: tuple
    downgrade_actions: tuple
    coverage_after_drop: dict
    dropped_metrics: tuple
    emptied_dims: tuple
    not_assessed: tuple
    evidence_ceiling: dict
    anchor_fallback: bool


class _Checks:
    # 一次 preflight 的累加器；执行顺序见 run()，findings 最后统一去重定序（V-3）。
    def __init__(self, inputs, config):
        if not isinstance(config, PreflightConfig):   # 缺字段就抛，不取默认值（V-14）
            missing = [n for n in CONFIG_FIELDS if not hasattr(config, n)]
            if missing:
                raise PreflightError('config 缺 preflight 字段：' + ', '.join(missing))
        self.config, self.anchor_fallback = config, False
        self.warn_at, self.block_at = (numeric.D(config.missing_rate_warn),
                                       numeric.D(config.missing_rate_block))
        self.masters, self.redlines = tuple(inputs.strategy_master), tuple(inputs.redlines)
        self.cards, self.previous = tuple(inputs.design_cards), tuple(inputs.previous_ledger)
        self.metrics = {r.metric_id: r for r in tuple(inputs.metric_dict)}
        self.signed_set = frozenset(m for m, r in self.metrics.items()
                                    if r.signoff_status in tuple(config.signed_signoff_status))
        self.signed = tuple(sorted(self.signed_set))
        self.facts = tuple(f for f in tuple(inputs.metric_facts) if f.period == config.period)
        self.findings, self.downgrades, self.not_assessed = [], [], set()
        self.dropped, self.emptied = (), ()
        self.usable, self.coverage, self.ceiling = {}, {}, {}

    def add(self, code, reason, scope, detail):
        self.findings.append(_f(code, reason, scope, detail))

    def act(self, reason, action, subject):
        # [L1051] item 13；H-6：没有 reason_code 的降级根本不成立
        self.downgrades.append(DowngradeAction(reason_code=getattr(reason, 'value', reason),
                                               action=action, subject=subject))

    def c01(self):
        # [L900] FROZEN + 评价期在生效区间内 + approved_by / whatif_run_id 齐全；违者
        # BLOCK，退出码 2。G-11(a) 走 STALE 分支。
        wv, ref = self.config.weight_version, self.config.period_ref_date
        scope, day = 'weight_version:' + wv.weight_version_id, ref.isoformat()
        if wv.status != FROZEN:
            self.add('C-01', RC.WEIGHT_VERSION_DRAFT if wv.status == DRAFT
                     else RC.WEIGHT_VERSION_INVALID, scope,
                     'status = ' + wv.status + '，只有 FROZEN 可用于评分')
        if ref > wv.effective_to:
            self.add('C-01', RC.WEIGHT_VERSION_STALE, scope, '评价期基准日 ' + day
                     + ' 超出 effective_to ' + wv.effective_to.isoformat())
        elif ref < wv.effective_from:
            self.add('C-01', RC.WEIGHT_VERSION_INVALID, scope, '评价期基准日 ' + day
                     + ' 早于 effective_from ' + wv.effective_from.isoformat())
        if not str(wv.approved_by).strip():
            self.add('C-01', RC.WEIGHT_VERSION_INVALID, scope, 'approved_by 为空，未签认')
        if not str((wv.provenance.whatif_run_id if wv.provenance else '') or '').strip():
            self.add('C-01', RC.WEIGHT_MISSING_WHATIF_RUN_ID, scope, 'FROZEN 但缺 '
                     'whatif_run_id（[L900] 归 C-01、[L1281] 归 config 层）')

    def c02(self):
        # [L901] 未签认 -> 剔除并重归一（WARN）；维度被清空 -> W 置 0 重归一；清空维度
        # 数 >= 2（或全部维度清空）-> BLOCK。G-10 走这里；重归一的执行归 aggregate。
        self.dropped = tuple(sorted(set(self.metrics) - self.signed_set))
        for mid in self.dropped:
            row = self.metrics[mid]
            self.add('C-02', RC.METRIC_NOT_SIGNED, 'metric:' + mid, 'signoff_status = '
                     + row.signoff_status + '，未签认，已从 ' + row.dim_code + ' 剔除')
        dims = sorted({row.dim_code for row in self.metrics.values()})
        self.emptied = tuple(sorted(d for d in dims if not [m for m in self.signed_set
                                                            if self.metrics[m].dim_code == d]))
        for dim in self.emptied:
            self.add('C-02', RC.WEIGHT_REALLOCATED, 'dim:' + dim, 'W_' + dim
                     + ' 置 0 并在其余维度重归一（维度内指标全部被剔除）')
        if len(self.emptied) >= EMPTIED_DIM_BLOCK:
            self.add('C-02', RC.DIMENSION_EMPTIED, 'run', '清空维度数 ' + str(len(self.emptied))
                     + ' 达到阻断阈值 ' + str(EMPTIED_DIM_BLOCK) + '：' + ', '.join(self.emptied))
        elif dims and len(self.emptied) == len(dims):
            self.add('C-02', RC.DIMENSION_EMPTIED, 'run',
                     '全部维度被清空（' + ', '.join(self.emptied) + '），无法重归一')

    def c03(self):
        # [L902] 签认指标有权重项、无孤儿权重项、两级各自归一（1e-12），全部 BLOCK。
        # 注册表无 C-03 专用码，沿用 CONFIG_SEMANTIC_ERROR（message 已含「权重未归一
        # …引用了不存在的指标」），缺口已登记。
        wv, sem = self.config.weight_version, RC.CONFIG_SEMANTIC_ERROR
        l1, l2 = wv.level1_weights, wv.level2_weights
        dims = {r.dim_code for r in self.metrics.values()}
        scope, one = 'weight_version:' + wv.weight_version_id, _sum(l1.values())
        bad = [('dim:' + d, '一级与二级权重的维度键不一致') for d in sorted(set(l1) ^ set(l2))]
        bad += [('dim:' + d, '指标字典的维度在一级权重中无对应项') for d in sorted(dims - set(l1))]
        bad += [('dim:' + d, '孤儿一级权重项：指标字典中无该维度') for d in sorted(set(l1) - dims)]
        bad += [('metric:' + m, '签认指标在 ' + self.metrics[m].dim_code + ' 无二级权重项')
                for m in self.signed if m not in l2.get(self.metrics[m].dim_code, {})]
        bad += [('dim:' + d + ' metric:' + m, '孤儿二级权重项：指标字典中无该指标')
                for d in sorted(l2) for m in sorted(l2[d]) if m not in self.metrics]
        if not numeric.eq_tol(one, numeric.ONE):
            bad.append((scope, '一级权重之和 = ' + str(one) + '，未按 1e-12 归一到 1'))
        for dim in sorted(l2):
            if not numeric.eq_tol(_sum(l2[dim].values()), numeric.ONE):
                bad.append(('dim:' + dim, '二级权重之和 = ' + str(_sum(l2[dim].values()))
                            + '，未按 1e-12 归一到 1'))
        bad += [('metric:' + m, 'metric_facts 引用了字典中不存在的 metric_id')
                for m in sorted({f.metric_id for f in self.facts} - set(self.metrics))]
        for where, detail in bad:
            self.add('C-03', sem, where, detail)

    def c04(self):
        # [L903] 缺失率 = 签认指标中无可用事实的比例（含被 C-06 剔除的）。超 warn 阈
        # -> WARN + 按 missing_rule 处理；超 block 阈 -> 该策略 NOT_ASSESSED（[L1288]，
        # 不升级为运行级 BLOCK）。分母为 0 -> coverage None + NOT_ASSESSED。
        for row in self.masters:
            sid, scope = row.strategy_id, 'strategy:' + row.strategy_id
            have = self.usable.get((sid, row.version_id), frozenset())
            missing = tuple(m for m in self.signed if m not in have)
            self.coverage[sid] = numeric.safe_div(len(have), len(self.metrics), on_zero=None)
            rate = (numeric.safe_div(len(missing), len(self.signed), on_zero=numeric.ZERO)
                    if self.signed else None)
            if rate is None:
                self.not_assessed.add(sid)
                self.add('C-04', RC.NOT_ASSESSED, scope, '无签认指标，缺失率无定义（分母 0）')
                self.act(RC.NOT_ASSESSED, '签认指标集为空，记为不可评价', sid)
            elif rate > self.block_at:
                self.not_assessed.add(sid)
                self.add('C-04', RC.MISSING_RATE_BLOCK, scope, '缺失率 ' + str(rate)
                         + ' 超过阻断阈 ' + str(self.block_at) + '，缺失 ' + str(len(missing))
                         + ' / ' + str(len(self.signed)) + '：' + ', '.join(missing))
                self.act(RC.MISSING_RATE_BLOCK, '缺失率超阻断阈，记为不可评价', sid)
            elif rate > self.warn_at:
                rules = ', '.join(sorted(m + '=' + self.metrics[m].missing_rule
                                         for m in missing))
                self.add('C-04', RC.MISSING_RATE_WARN, scope, '缺失率 ' + str(rate)
                         + ' 超过预警阈 ' + str(self.warn_at) + '，按 missing_rule 处理（'
                         + rules + '）')
                self.act(RC.MISSING_RATE_WARN, '按 missing_rule 处理缺失指标', sid)

    def c0506(self):
        # [L904] + [L905]：data_as_of 与评价期一致（滞后 -> WARN + score_card 标注）；
        # SUSPECT -> 剔除该指标（降 coverage）+ WARN，并建可用事实索引。
        ref = self.config.period_ref_date
        for as_of in sorted({f.data_as_of for f in self.facts}):
            if as_of == ref:
                continue
            lag, rows = (ref - as_of).days, sum(1 for f in self.facts if f.data_as_of == as_of)
            self.add('C-05', RC.DATA_STALE, 'data_as_of:' + as_of.isoformat(),
                     'data_as_of ' + ('早于' if lag > 0 else '晚于') + '评价期基准日 '
                     + str(abs(lag)) + ' 天，涉及 ' + str(rows) + ' 行事实')
        for fact in self.facts:
            if fact.metric_id not in self.signed_set:
                continue                              # 未签认已由 C-02 记录，不重复计
            if fact.data_quality_flag == SUSPECT_FLAG:
                self.add('C-06', RC.DATA_QUALITY_SUSPECT,
                         'strategy:' + fact.strategy_id + ' metric:' + fact.metric_id,
                         'SUSPECT，该事实已剔除，coverage 相应下降')
                self.act(RC.DATA_QUALITY_SUSPECT, '剔除 SUSPECT 事实并降 coverage',
                         fact.strategy_id + '/' + fact.metric_id)
            else:
                self.usable.setdefault((fact.strategy_id, fact.version_id),
                                       set()).add(fact.metric_id)
        self.usable = {k: frozenset(v) for k, v in sorted(self.usable.items())}

    def c0709(self):
        # [L906] + [L908]：facts 的 caliber_version 必须等于 metric_dict 的（BLOCK，按
        # metric_id + 两个版本号去重）；*_minor 出现小数或非数值 -> BLOCK，作用位是
        # unit = MONEY_MINOR 的 target_value / threshold_value / facts 三个 value 列
        # （后三者是 unit 多态列，小数会落进 Ratio 分支，必须在此按 unit 复核）。
        for key in sorted({(f.metric_id, f.caliber_version,
                            self.metrics[f.metric_id].caliber_version) for f in self.facts
                           if f.metric_id in self.metrics
                           and f.caliber_version != self.metrics[f.metric_id].caliber_version}):
            self.add('C-07', RC.CALIBER_VERSION_MISMATCH, 'metric:' + key[0],
                     'metric_facts 口径 ' + key[1] + ' != metric_dict 口径 ' + key[2])
        money = {m for m, row in self.metrics.items() if row.unit == MONEY_UNIT}
        slots = [('metric:' + m, 'target_value', self.metrics[m].target_value)
                 for m in sorted(money)]
        slots += [('redline:' + r.metric_id, 'threshold_value', r.threshold_value)
                  for r in self.redlines if r.metric_id in money]
        slots += [('metric_facts:' + f.strategy_id + '/' + f.version_id + '/' + f.period
                   + '/' + f.metric_id, c, getattr(f, c)) for f in self.facts
                  if f.metric_id in money for c in ('value', 'value_num', 'value_den')]
        for scope, column, value in slots:
            if not _minor_ok(value):
                self.add('C-09', RC.MONEY_NON_INTEGER, scope + '.' + column, column
                         + ' 应为最小货币单位整数，实得 ' + repr(value))

    def c08(self):
        # [L907] PARTIAL -> 证据上限压到 C；MISSING（含根本没有卡）-> 证据 D ->
        # NOT_ASSESSED，台账单独计数；策略级降级，不阻断其余策略（[L1292]）。
        # RC-1（CONSUMPTION-TODO 第 2 条 / M18 [L1102] T4 粒度 = 策略 × 版本）：原字典推导
        # 遇重复键静默取后一行 = V-14 静默降级（MISSING 卡可被后行 COMPLETE 盖掉）。改为
        # 建索引前显式查重并出 DESIGN_CARD_DUPLICATE_KEY（BLOCK，audit + 退出码 2，[L917]），
        # 索引保留首行、后行不再参与判定——宁可不评不可错评（M22 [L918]），拒绝仍是有码的拒绝。
        by_key, dup_rows = {}, {}
        for card in self.cards:
            dup_key = (card.strategy_id, card.version_id)
            if dup_key in by_key:
                dup_rows.setdefault(dup_key, [by_key[dup_key]]).append(card)
                continue
            by_key[dup_key] = card
        for (dup_sid, dup_vid), dup_list in sorted(dup_rows.items()):
            self.add('C-08', RC.DESIGN_CARD_DUPLICATE_KEY,
                     'strategy:' + dup_sid + ' version:' + dup_vid,
                     '同一 (strategy_id, version_id) 出现 ' + str(len(dup_list))
                     + ' 条设计卡行（card_status = '
                     + ', '.join(str(r.card_status) for r in dup_list)
                     + '），违 [L1102] T4 粒度=策略×版本，拒绝静默取后一行；索引以首行为准')
        for row in self.masters:
            sid, scope = row.strategy_id, 'strategy:' + row.strategy_id
            card = by_key.get((sid, row.version_id))
            if card is None or card.card_status == 'MISSING':
                self.not_assessed.add(sid)
                self.add('C-08', RC.EVIDENCE_CARD_MISSING, scope, 'card_status = MISSING'
                         + ('（本期无对应设计卡行）' if card is None else '')
                         + '，证据判为 D，本期不可评价')
                self.act(RC.EVIDENCE_CARD_MISSING, '证据 D，记为不可评价', sid)
            elif card.card_status == 'PARTIAL':
                self.ceiling[sid] = CARD_PARTIAL_CEILING
                self.add('C-08', RC.EVIDENCE_CARD_PARTIAL, scope, 'card_status = PARTIAL'
                         '（缺对照安排或成功判定），证据上限压到 ' + CARD_PARTIAL_CEILING)
                self.act(RC.EVIDENCE_CARD_PARTIAL, '证据等级上限压到 C', sid)

    def c10(self):
        # [L909] 成员存在 / 未被淘汰 / 未换 version_id；失效 -> 回退仅当期归一化 + 报告
        # 首屏标注秩反转风险。「未被淘汰」digest 未给判据，实现取 RETIRED 或 offline_date
        # 非空；version_id 基准取上期台账，无台账时记 FIRST_PERIOD（不静默放过）。
        anchor, ref = self.config.anchor_set, self.config.period_ref_date
        by_id = {m.strategy_id: m for m in self.masters}
        prev = {r.strategy_id: r.version_id for r in self.previous}
        scope = 'anchor_set:' + (anchor.anchor_set_id if anchor else 'none')
        bad = [] if anchor else ['未提供 anchor_set（T8），无锚定基准']
        if anchor and not anchor.effective_from <= ref <= anchor.effective_to:
            bad.append('评价期基准日 ' + ref.isoformat() + ' 不在生效区间内')
        for sid in (anchor.strategy_ids if anchor else ()):
            master, base = by_id.get(sid), prev.get(sid)
            if master is None:
                bad.append('成员 ' + sid + ' 不在本期 strategy_master 中')
            elif master.status == RETIRED or master.offline_date is not None:
                bad.append('成员 ' + sid + ' 已淘汰（status = ' + master.status + '）')
            if master and base is not None and base != master.version_id:
                bad.append('成员 ' + sid + ' version_id 由 ' + base + ' 变更为 '
                           + master.version_id)
        if not bad:
            if not prev:
                self.add('C-10', RC.FIRST_PERIOD, scope, '无上期 grade_ledger，version_id '
                         '基线不可用，「未换 version_id」子判据本期未核验')
            return
        self.anchor_fallback = True
        self.add('C-10', RC.ANCHOR_SET_STALE, scope,
                 '锚定集失效：' + '；'.join(bad) + ' → 回退为仅当期归一化')
        self.add('C-10', RC.RANK_REVERSAL_RISK, scope,
                 '锚定集失效，存在秩反转风险，报告首屏须显著标注')
        self.act(RC.ANCHOR_SET_STALE, '回退为仅当期归一化', scope)
        self.act(RC.RANK_REVERSAL_RISK, '报告首屏标注秩反转风险', scope)

    def build(self) -> PreflightResult:
        # [L916] status：BLOCK 只由 RUN_BLOCKING_CODES 决定；只有 INFO 时是 PASS，但
        # INFO finding 仍进审计包，不被吞掉。findings 去重后定序（V-3）。
        status = (STATUS_BLOCK if any(f.blocks_run for f in self.findings) else
                  STATUS_WARN if any(f.severity is not Severity.INFO
                                     for f in self.findings) else STATUS_PASS)
        unique = {}
        for item in self.findings:
            unique.setdefault((item.code, item.reason_code, item.scope, item.detail), item)
        return PreflightResult(
            status=status, exit_code=EXIT_BLOCK if status == STATUS_BLOCK else EXIT_OK,
            findings=tuple(unique[k] for k in sorted(unique)),
            downgrade_actions=tuple(self.downgrades),
            coverage_after_drop={k: self.coverage[k] for k in sorted(self.coverage)},
            dropped_metrics=self.dropped, emptied_dims=self.emptied,
            not_assessed=tuple(sorted(self.not_assessed)), anchor_fallback=self.anchor_fallback,
            evidence_ceiling={k: self.ceiling[k] for k in sorted(self.ceiling)})


def run(inputs: Inputs, config: PreflightConfig) -> PreflightResult:
    # [L915] Step 0 入口：十条检查全部执行、不短路——BLOCK 时也要一次列出全部违规
    # （[L1282]）。复杂度 O(策略数 × 指标数)（[L919]）。
    checks = _Checks(inputs, config)
    for step in (checks.c0709, checks.c01, checks.c02, checks.c03, checks.c0506, checks.c04,
                 checks.c08, checks.c10):
        step()
    return checks.build()


def build_audit_bundle(result, config, run_context) -> AuditBundle:
    # [L917] BLOCK 只写 audit_bundle：记录为什么没跑出结果。output_fingerprints 为空 =
    # 本次没有任何评分产物（不是「忘了填」）；序列化的权威实现是 audit.py。
    missing = [k for k in AUDIT_CONTEXT_FIELDS if k not in run_context]
    if missing:
        raise PreflightError('run_context 缺 audit 注入字段：' + ', '.join(missing))
    return AuditBundle(
        period=config.period, output_fingerprints={},
        weight_version_id=config.weight_version.weight_version_id,
        preflight_findings=tuple(f.to_audit_finding() for f in result.findings),
        downgrade_actions=tuple(result.downgrade_actions), exit_code=result.exit_code,
        **{k: run_context[k] for k in AUDIT_CONTEXT_FIELDS})


def execute(inputs, config, out_dir, run_context) -> tuple:
    # [L917] 三条硬行为：BLOCK -> 只写 audit.json + 退出码 2 + 不产 score_card；
    # PASS / WARN 时一个文件都不写（评分产物与常规 audit 归主流程 / audit.py）。
    result = run(inputs, config)
    if result.status != STATUS_BLOCK:
        return result.exit_code, result, ()
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / AUDIT_FILE_NAME
    path.write_text(build_audit_bundle(result, config, run_context).model_dump_json(indent=2)
                    + '\n', encoding='utf-8')
    return result.exit_code, result, (path,)
