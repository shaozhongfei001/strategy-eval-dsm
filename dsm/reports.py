'''dsm.reports -- S6 渲染层：report.md 十段、score_card 各段、grade_ledger、稳健性/
诊断报告与审计包写盘。签名逐字取自 [L1061]，产物取自 [L1062]，段名逐字取自 [L1063]，
score_card 各段取自 [L1612]-[L1626]，grade_ledger 设计取自 [L1630]-[L1634]。

本层只渲染，不计算：
  * V-14：某段的上游数据缺失时，该段照样出现，写「本段无数据」加一个已注册原因码，
    绝不跳段、绝不用空串或 None 冒充已生成。
  * [L1630]：recommended_action 与 decided_action 是两个独立列，谁也不得覆盖谁，
    任何一方为空时不得用另一方填充；两者不一致时缺 decision_note 记为台账不完整。
  * [L1019]/[L1024]：sensitivity 的 veto 与 usable_for_elimination 在 models.py 里
    没有列，且 sensitivity.veto 的 docstring 把台账写明「归渲染层」，所以列在此处
    本地声明（ADJ-4），不改冻结契约。
  * G5/G7 未签认：首屏必写「只用合成数据跑通机制、不得用于真实资源配置」的声明；
    K-01~K-20 一律 PLACEHOLDER（R-12），本模块不拟定任何业务数值、人名、部门名。
  * V-9：钱款与计数走 numeric.as_minor 精确出整数，比率走 numeric.q12 / safe_div，
    本模块不自带任何四舍五入。
  * R-7：canonical 序列化与 reproducibility_hash 归 audit.py，本模块只调用
    audit.serialize_bundle 与 audit.fingerprint_outputs，不重新实现任何哈希。
  * H-8：无时钟、无随机；运行身份来自 AuditBundle，门禁状态与 frames 由调用方注入。
'''
from __future__ import annotations

import csv
import io
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict

from dsm import audit, numeric, pooling, sensitivity
# 范围披露位的载体类型（EVID-1）：直接取类名，避免与 AllFrames.evidence 字段名撞车。
from dsm.evidence import EvidenceScope
from dsm.models import (
    AuditBundle, AttainmentFrame, EntropyDiagnosticRow, EvidenceFrame,
    GradeLedgerRow, PoolFrame, PoolStats, RedlineFrame,
    ScoreCardRow, ScoreFrame, SensitivityReport, StrictBool, TriangulationReport,
    WeightProvenance)
from dsm import reason_codes
from dsm.reason_codes import RC, Severity

LAYER = 'S6'
NULL = 'null'
NO_DATA = '本段无数据'
NO_DATA_REASON = RC.NOT_ASSESSED
PLACEHOLDER = 'PLACEHOLDER'
# [L1063] ②：事实行为空时本期范围无从界定（dsm/evidence.py:182-184 的同名标志）。
SCOPE_UNESTABLISHED = '本期无法界定'
# [L748]：loo_impact 为空元组 = 本轮未执行 LOO，显式披露而非静默略过该段（V-14）。
LOO_NOT_RUN = '本轮未执行 LOO'
# [L1409] / G-07 逐字要求的警示文案（契约原文，不是业务码；业务码走 RC.DOMINANT_METRIC）。
DOMINANT_WARNING = '存在单一指标过度影响'
CEL0 = '本期末接入增量估计'
LEDGER_COMPLETE = '完整'
GATE_STATEMENT = (
    '【门禁声明】G5（争议来源复核）与 G7（治理配置签认）未全部签认：本报告只用合成'
    '数据跑通机制，不得输出可用于真实资源配置的分数或等级，不得作为淘汰、问责或退出'
    '管理的依据。')

REPORT_SECTIONS = (
    '①首屏结论与可用性声明（能否用于淘汰）',
    '②本期评价范围与覆盖率',
    '③等级分布与占比双报',
    '④一级库准入与拒绝清单',
    '⑤红线命中与豁免清单',
    '⑥证据结构（A/B/C/D 计数与 NOT_ASSESSED 明细）',
    '⑦稳健性结果（flip_rate / 稳定性标签分布 / LOO 主导指标）',
    '⑧方法三角一致性',
    '⑨指标健康度与字典工单',
    '⑩附录：preflight 全部 WARN、降级动作全量、权重版本与 provenance、复现指引')
ARTIFACT_NAMES = ('report.md', 'score_card.csv', 'grade_ledger.csv',
                  'sensitivity_report.csv', 'entropy_diagnostic.csv',
                  'triangulation.md', 'audit.json')
_ARTIFACT_FIELD = {'report.md': 'report_md', 'score_card.csv': 'score_card_csv',
                   'grade_ledger.csv': 'grade_ledger_csv',
                   'sensitivity_report.csv': 'sensitivity_report_csv',
                   'entropy_diagnostic.csv': 'entropy_diagnostic_csv',
                   'triangulation.md': 'triangulation_md',
                   'audit.json': 'audit_json'}
OPEN_PARAMETER_IDS = tuple('K-%02d' % n for n in range(1, 21))
FRAME_GRADES = ('L1', 'L2', 'L3', 'L4', 'NOT_ASSESSED')
EVIDENCE_CLASSES = ('A', 'B', 'C', 'D')
STABILITY_LABELS = ('STABLE', 'NEAR_BOUNDARY', 'UNSTABLE')


class ReportError(ValueError):
    '''报告结构契约被破坏：十段缺段或顺序错乱。'''


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class GateStatus(_Frozen):
    '''G5 / G7 冻结门禁的签认状态（SDD 1781 行）。必填、无默认：缺了就抛
    pydantic 校验错（ADJ-2），本模块不猜「大概已经签了」。'''

    g5_dispute_source_review_signed: StrictBool
    g7_governance_config_signed: StrictBool


class AllFrames(_Frozen):
    '''[L1061] 形参名，models.py 未声明容器（ADJ-4：本地声明）。每段的上游都可缺，
    缺了走 V-14 的「本段无数据 + 原因码」，不是静默省略。'''

    attainment: AttainmentFrame | None = None
    evidence: EvidenceFrame | None = None
    # EVID-1 / ORCH-37 第 9 条：[L1063] ②「本期评价范围与覆盖率」的范围过滤披露位。
    # 范围口径的唯一实现是 dsm/evidence.py:204 的 evaluation_scope（调用方注入），本层
    # 只渲染不重算（R-7 / INV-2）。未注入时 ②⑥ 显式披露「本段无数据 + 原因码」，
    # period_established=False 时显式披露「本期无法界定」，两者都不静默省略（V-14）。
    evaluation_scope: EvidenceScope | None = None
    redline: RedlineFrame | None = None
    score: ScoreFrame | None = None
    pool: PoolFrame | None = None
    pool_stats: PoolStats | None = None
    # GAP-06 / ORCH-36 第 4 条：G-14（MIX_QUALITY_DEGRADED）需要上期 PoolStats 作基线。
    # AllFrames 是 reports 本地声明的形参容器（ADJ-4），**不是** dsm/models.py 的冻结契约，
    # 故本包可加该可选字段（默认 None，向后兼容）。缺基线时 _section_6 显式披露「判据不可比」，
    # 绝不静默省略（V-14）。cli 侧的传参接线归 P2-wire，见 dsm_stage/G14FIX/HANDOFF-P2.md。
    previous_pool_stats: PoolStats | None = None
    sensitivity: SensitivityReport | None = None
    triangulation: TriangulationReport | None = None
    entropy_diagnostics: tuple[EntropyDiagnosticRow, ...] | None = None
    score_card: tuple[ScoreCardRow, ...] | None = None
    grade_ledger: tuple[GradeLedgerRow, ...] | None = None
    weight_provenance: WeightProvenance | None = None
    gate_status: GateStatus


class ReportSet(_Frozen):
    '''[L1062] 的七件产物，全部是文本；写盘由 write_report_set 完成。'''

    report_md: str
    score_card_csv: str
    grade_ledger_csv: str
    sensitivity_report_csv: str
    entropy_diagnostic_csv: str
    triangulation_md: str
    audit_json: str

    def artifacts(self) -> dict:
        return {name: getattr(self, _ARTIFACT_FIELD[name]) for name in ARTIFACT_NAMES}


# --------------------------------------------------------------------------- formatting
def fmt_ratio(value) -> str:
    '''比率：numeric.q12 定量到 1e-12，本模块不再四舍五入（V-9）。'''
    return NULL if value is None else str(numeric.q12(value))


def fmt_int(value) -> str:
    '''钱款与计数：精确整数，非整数直接抛 NonIntegerAmountError（V-9 / C-09）。'''
    return NULL if value is None else str(numeric.as_minor(value))


def fmt_bool(value) -> str:
    return 'true' if value else 'false'


def fmt_cell(value) -> str:
    if value is None:
        return NULL
    if isinstance(value, bool):
        return fmt_bool(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        return fmt_ratio(value)
    if isinstance(value, str):
        return value if value != '' else NULL
    return audit.canonical_text(value)


def share(numerator, denominator) -> str:
    '''唯一的除法出口：on_zero=None 表示真的无定义，绝不静默当 0（[L930] 口径）。'''
    return fmt_ratio(numeric.safe_div(numerator, denominator, on_zero=None))


def _cfg_get(config, key):
    if config is None:
        return None
    if isinstance(config, Mapping):
        return config.get(key)
    return getattr(config, key, None)


def fmt_config_value(config, key) -> str:
    '''未提供的门槛一律 PLACEHOLDER：K-01~K-20 未签认前不得拟定数值（R-12）。'''
    raw = _cfg_get(config, key)
    return PLACEHOLDER if raw is None else fmt_cell(raw)


def _table(header, rows) -> list:
    lines = ['| ' + ' | '.join(str(h) for h in header) + ' |']
    lines.append('|' + '---|' * len(header))
    lines += ['| ' + ' | '.join(str(c) for c in row) + ' |' for row in rows]
    return lines


def _csv(header, rows) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator='\n')
    writer.writerow([str(h) for h in header])
    for row in rows:
        writer.writerow([str(c) for c in row])
    return buf.getvalue()


def _no_data(what) -> list:
    '''V-14：缺数据的段落照样出现，明写无数据与原因码。'''
    return ['- ' + NO_DATA + '：上游 ' + what + ' 未产出',
            '- 原因码：' + str(NO_DATA_REASON) + '（本段保留，不跳段、不合并、不改名）']


def _locator(row):
    return (row.strategy_id, row.version_id, getattr(row, 'period', ''))


def _rows(frame):
    return () if frame is None else tuple(frame.rows)


# --------------------------------------------------------------------------- verdicts
def ledger_missing_items(row: GradeLedgerRow) -> tuple:
    '''[L1632]-[L1634]：三级要有责任部门/责任人/时限，四级要有归档号，建议与决定
    不一致时要有 decision_note。缺项即「台账不完整」。'''
    missing = []
    if row.grade == 'L3':
        for name in ('owner_dept', 'owner_name', 'deadline'):
            if getattr(row, name) is None:
                missing.append(name)
    if row.grade == 'L4' and row.archive_ref is None:
        missing.append('archive_ref')
    if row.recommended_action != row.decided_action and not row.decision_note:
        missing.append('decision_note')
    return tuple(missing)


def _cel_empty(row: ScoreCardRow) -> bool:
    return (row.incremental_value is None and row.incremental_ci_lower is None
            and row.incremental_ci_upper is None and row.estimator_method is None
            and row.value_captured_minor is None)


def _elimination_verdict(frames) -> tuple:
    '''首屏 usable_for_elimination 与其依据（[L1064] 硬要求、[L1625] 双重约束）。'''
    basis = []
    usable = True
    gate = frames.gate_status
    if not (gate.g5_dispute_source_review_signed
            and gate.g7_governance_config_signed):
        usable = False
        basis.append('G5/G7 门禁未签认（合成数据机制验证）')
    rep = frames.sensitivity
    if rep is None:
        usable = False
        basis.append('稳健性结果未产出')
    else:
        verdict = sensitivity.veto(rep)
        if verdict.vetoed:
            usable = False
            basis.append('稳健性非补偿否决：' + ','.join(str(c) for c in verdict.codes))
    tri = frames.triangulation
    if tri is None:
        usable = False
        basis.append('方法三角未产出')
    elif tri.agreement == 'METHOD_DIVERGENCE':
        usable = False
        basis.append('方法分歧：METHOD_DIVERGENCE')
    labels = [row.stability_label for row in (frames.score_card or ())]
    for tag in ('UNSTABLE', 'NEAR_BOUNDARY'):
        count = sum(1 for label in labels if label == tag)
        if count:
            basis.append(tag + ' ' + fmt_int(count) + ' 条：边界结论不得作为淘汰唯一依据')
    return usable, basis


def _grade_counts(rows) -> dict:
    counts = {}.fromkeys(FRAME_GRADES, 0)
    for row in rows:
        if row.grade in counts:
            counts[row.grade] += 1
    return counts


# --------------------------------------------------------------------------- report.md 十段
def _code_value(code) -> str:
    '''注册码的字符串口径：RC.<NAME> 走 .value，裸串原样（P-8：禁裸写字面量）。'''
    return str(getattr(code, 'value', code))


def _code_line(code, tail='') -> str:
    '''一条「码 + 注册表 message + severity + blocks_run」的披露行。severity 与 blocks_run 一律
    查注册表，本层不改写（V-14：BLOCK 码不可能被渲染成 WARN）。'''
    sev = reason_codes.severity(code)
    return ('- 原因码 ' + _code_value(code) + '：' + reason_codes.message(code)
            + '（severity ' + str(getattr(sev, 'value', sev)) + '，blocks_run='
            + fmt_bool(reason_codes.blocks_run(code)) + '）' + tail)


def _scope_lines(scope) -> list:
    '''[L1063] ②「本期评价范围与覆盖率」的范围过滤披露（EVID-1 / ORCH-37 第 9 条）。
    范围只由 dsm/evidence.py:204 的 evaluation_scope 算，本层不重算（R-7）；被过滤的设计卡
    不删除、不隐藏（G-08 的版本断裂判定还要用它，[L1117]），只是不进本期评价范围统计。
    scope 未注入 -> 「本段无数据 + 原因码」；period_established=False -> 明写「本期无法界定」
    并说明一张卡都没被过滤（V-14：既不静默收窄口径，也不把全部卡静默丢掉）。'''
    if scope is None:
        return _no_data('evaluation_scope（本期评价范围过滤披露，调用方未注入）')
    out = ['- 本期评价范围（in_period 的 strategy_id × version_id 对）：'
           + fmt_int(len(scope.in_period)) + ' 个；period_established='
           + fmt_bool(scope.period_established) + '（判据唯一实现 dsm/evidence.py:204）']
    if not scope.period_established:
        out.append('- ' + SCOPE_UNESTABLISHED + '：传入事实行为空，任何设计卡都判不出「不在本期'
                   '评价范围内」，故本期一张卡都未被过滤；该 0 不得读作「全部在范围内」的结论，'
                   '也不得静默丢卡（V-14）')
    if not scope.excluded:
        out.append('- 被范围过滤掉的设计卡：0 张' + ('（period_established=false，此 0 不可用，见上一行）'
                                              if not scope.period_established else ''))
        return out
    out.append('- 被范围过滤掉的设计卡：' + fmt_int(len(scope.excluded)) + ' 张，过滤依据 '
               + scope.excluded[0].basis + '；卡本身保留供 Step6 版本断裂判定（G-08 / [L1117]）')
    out.append(_code_line(scope.excluded[0].reason_code, '；明细如下')[2:])
    out += _table(('strategy_id', 'version_id', 'basis', 'reason_code'),
                  [(e.strategy_id, e.version_id, e.basis, str(e.reason_code))
                   for e in sorted(scope.excluded,
                                   key=lambda x: (x.strategy_id, x.version_id))])
    return out


def _scope_summary(scope) -> list:
    '''[L1063] ⑥ 段的同口径回指：A/B/C/D 计数只覆盖本期评价范围内的策略版本，被范围过滤掉的
    设计卡不计入（明细在②）。范围不在此重算，只披露计数口径与出处（V-14 不静默省略）。'''
    if scope is None:
        return ['- 范围过滤披露：本段未注入 evaluation_scope，A/B/C/D 计数覆盖的策略版本范围'
                + SCOPE_UNESTABLISHED + '（同名「本段无数据」行见②；V-14，不静默省略）']
    if not scope.period_established:
        return ['- 范围过滤披露：' + SCOPE_UNESTABLISHED + '（事实行为空，一张卡都未被过滤）；'
                'A/B/C/D 计数覆盖 ' + fmt_int(len(scope.in_period)) + ' 个策略版本']
    return ['- 范围过滤披露：A/B/C/D 计数覆盖本期评价范围内 ' + fmt_int(len(scope.in_period))
            + ' 个策略版本；被范围过滤掉 ' + fmt_int(len(scope.excluded)) + ' 张设计卡（'
            + (_code_value(scope.excluded[0].reason_code) if scope.excluded else '本期无')
            + '）未计入上表计数，明细见②']


def _flagged(rep, code) -> bool:
    return any(str(getattr(f, 'value', f)) == _code_value(code)
               for f in tuple(getattr(rep, 'flags', ()) or ()))


def _loo_impact_lines(rep) -> list:
    '''[L748]「每指标的 LOO 影响力排名（主导指标清单）」+ [L1409]「loo_impact 最大者为该指标；
    报告输出「存在单一指标过度影响」警示」+ [L1858]「是否存在某一指标过度影响综合得分 →
    sensitivity_report」的渲染出口（LOO-1 NEED-WIRING 第 1/2/3 条）。

    只渲染不重算不重排：loo_impact 由 dsm/sensitivity.py 排好降序交来，本层保持原序（再排一次
    就是第二套口径）。ORCH-40 第 7 条：loo_impact 与 loo_dominant_metrics 是两个不同字段，
    不得合并、不得互相替代，故两者各自成行。数值走 fmt_ratio（numeric.q12，Decimal 原样，
    不经 float、不四舍五入到少于 q12，V-9）。空元组 = 本轮未执行 LOO -> 显式披露（V-14）。
    LOO_SAMPLED（[L1020] 抽样降级）与排名同区块披露：抽样时排名只覆盖被抽中的指标。'''
    impact = tuple(getattr(rep, 'loo_impact', ()) or ())
    if not impact:
        return ['- LOO 影响力排名（[L748] 输出列）：' + LOO_NOT_RUN + '（loo_impact = 空元组）；'
                '本段保留不静默省略，故「' + DOMINANT_WARNING + '」本轮无据可判（V-14）']
    out = ['- LOO 影响力排名（[L748] 输出列；降序由 dsm/sensitivity.py 排定，本层不重排）：']
    out += _table(('排名', 'metric_id', 'loo_impact'),
                  [(fmt_int(i + 1), str(metric), fmt_ratio(value))
                   for i, (metric, value) in enumerate(impact)])
    head, head_value = impact[0]
    out.append('- loo_impact 最大者（[L1409] 逐字）：' + str(head) + '，loo_impact='
               + fmt_ratio(head_value))
    if _flagged(rep, RC.LOO_SAMPLED):
        out.append('- ' + _code_value(RC.LOO_SAMPLED) + '（' + reason_codes.message(RC.LOO_SAMPLED)
                   + '）：上述排名只覆盖被抽中的指标，本排名不完整（[L1020]，V-14 不得静默降级）')
    if _flagged(rep, RC.DOMINANT_METRIC):
        out.append('- 警示：' + DOMINANT_WARNING + '（[L1409] / G-07 逐字文案）')
        out.append(_code_line(RC.DOMINANT_METRIC, '；判据是 flip_rate 超阈（[L748]），'
                              '与上面的影响力排名是两个字段，不互相替代（ORCH-40 第 7 条）'))
    else:
        out.append('- 本期未触发 ' + _code_value(RC.DOMINANT_METRIC) + '：flip_rate 判据（[L748]）'
                   '未超阈，故不输出「' + DOMINANT_WARNING + '」警示；影响力排名照常披露'
                   '（两字段独立，ORCH-40 第 7 条）')
    return out


def _section_1(bundle, frames) -> list:
    gate = frames.gate_status
    signed = gate.g5_dispute_source_review_signed and gate.g7_governance_config_signed
    out = ([] if signed else [GATE_STATEMENT])
    out.append('- 门禁状态：G5=' + fmt_bool(gate.g5_dispute_source_review_signed) + '，G7=' + fmt_bool(gate.g7_governance_config_signed))
    usable, basis = _elimination_verdict(frames)
    out.append('- usable_for_elimination = ' + fmt_bool(usable) + '（能否用于淘汰，[L1064] 要求首屏必写）')
    out.append('- 依据：' + ('；'.join(basis) if basis else '无门禁否决、无 BLOCK 级稳健性否决、无方法分歧'))
    rows = frames.score_card or ()
    if not rows:
        out += _no_data('score_card（等级与分数概览）')
    else:
        counts = _grade_counts(rows)
        out += _table(('grade', '条数'), [(g, fmt_int(counts[g])) for g in FRAME_GRADES])
        out.append('- 分数口径：composite_absolute 是整体目标达成率（1.0 = 刚好达标），composite_relative 仅供同池排名，不用于判达标')
        if not signed:
            out.append('- 上述数值全部来自合成数据，仅用于验证机制，不得据此配置真实资源或作淘汰依据')
    ledger = frames.grade_ledger or ()
    incomplete = sum(1 for row in ledger if ledger_missing_items(row) or not row.ledger_complete)
    out.append('- 台账不完整：' + fmt_int(incomplete) + ' 条（缺项清单见⑩附录）')
    return out


def _section_2(frames) -> list:
    rows = tuple(sorted(_rows(frames.score), key=_locator))
    # EVID-1 / ORCH-37 第 9 条：范围过滤披露位。score 缺行也照披露（V-14：两个「无数据」
    # 各说各的，谁也不吞掉谁）。
    scope = _scope_lines(frames.evaluation_scope)
    if not rows:
        return _no_data('score（本期评价范围与覆盖率）') + scope
    out = _table(('strategy_id', 'version_id', 'period', 'coverage', 'weight_version_id'),
                 [(r.strategy_id, r.version_id, r.period, fmt_ratio(r.coverage), r.weight_version_id) for r in rows])
    values = [r.coverage for r in rows]
    out.append('- 参评策略数：' + fmt_int(len(rows)) + '；coverage 最低 ' + fmt_ratio(min(values)) + '，均值 ' + fmt_ratio(numeric.mean(values)))
    att = _rows(frames.attainment)
    if att:
        out.append('- 无目标值的指标行数：' + fmt_int(sum(1 for r in att if not r.has_target)) + ' / ' + fmt_int(len(att)) + '（coverage 低即该维度评得不全，见⑨字典工单）')
    else:
        out += _no_data('attainment（目标值覆盖明细）')
    return out + scope


def _section_3(frames) -> list:
    rows = frames.score_card or ()
    out = _no_data('score_card（等级分布）') if not rows else []
    if rows:
        counts = _grade_counts(rows)
        assessed = len(rows) - counts['NOT_ASSESSED']
        out += _table(('grade', '条数', '占参评比', '占已出分比'),
                      [(g, fmt_int(counts[g]), share(counts[g], len(rows)), share(counts[g], assessed)) for g in FRAME_GRADES])
    stats = frames.pool_stats
    if stats is None or not stats.rows:
        out += _no_data('pool_stats（池内占比 / 全局占比）')
    else:
        out += _table(('biz_domain', 'evidence_class', '条数', '池内占比', '全局占比'),
                      [(r.pool_key.biz_domain, r.pool_key.evidence_class, fmt_int(r.count),
                        fmt_ratio(r.share_in_pool), fmt_ratio(r.share_overall)) for r in stats.rows])
    out.append('- 占比双报：本段同时给出池内占比与全局占比，[L1064] 禁止只报合并占比')
    return out


def _section_4(frames) -> list:
    rows = tuple(sorted(_rows(frames.pool), key=_locator))
    if not rows:
        return _no_data('pool（一级库准入与拒绝清单）')
    gate = {(r.strategy_id, r.version_id): r for r in (frames.score_card or ())}
    out = ['- 准入 ' + fmt_int(sum(1 for r in rows if r.primary_pool_eligible)) + ' 条；拒绝 '
           + fmt_int(sum(1 for r in rows if not r.primary_pool_eligible)) + ' 条']
    out += _table(('strategy_id', 'version_id', 'period', 'eligible_for_L1_library', 'reject_reason', 'l1_gate_reasons'),
                  [(r.strategy_id, r.version_id, r.period, fmt_bool(r.primary_pool_eligible),
                    str(r.reject_reason) if r.reject_reason else NULL,
                    ','.join(str(c) for c in gate[(r.strategy_id, r.version_id)].l1_gate_reasons)
                    if (r.strategy_id, r.version_id) in gate else NULL) for r in rows])
    return out


def _section_5(frames) -> list:
    rows = tuple(sorted(_rows(frames.redline), key=_locator))
    if not rows:
        return _no_data('redline（红线命中与豁免清单）')
    hits = [r for r in rows if r.hit]
    out = ['- 命中行数：' + fmt_int(len(hits)) + ' / 评估行数 ' + fmt_int(len(rows))
           + '；HARD 命中为非补偿否决，分数照算但不生效，等级由红线强制']
    if not hits:
        return out + ['- 本期无红线命中']
    out += _table(('strategy_id', 'version_id', 'metric_id', 'level', 'comparator', 'threshold_value', 'forced_grade', '豁免审批号', '原因码'),
                  [(r.strategy_id, r.version_id, r.metric_id, r.level, r.comparator,
                    fmt_cell(r.threshold_value), str(r.forced_grade) if r.forced_grade else NULL,
                    r.waiver_approval_id or NULL, str(r.reason_code) if r.reason_code else NULL) for r in hits])
    out.append('- 有豁免审批留痕的命中：' + fmt_int(sum(1 for r in hits if r.waiver_approval_id))
               + ' 条；无留痕一律按未豁免处理。SOFT 扣分单列：'
               + '；'.join(r.metric_id + '=' + fmt_ratio(r.soft_deduction)
                           for r in hits if r.level == 'SOFT' and r.soft_deduction is not None) or '本期无')
    return out


def _mix_quality_lines(stats, previous) -> list:
    '''G-14 的披露（GAP-06 / D-G14-01 / ORCH-36 第 4 条）：算出来就必须出现在报告里，
    算出而不披露 = 静默降级（V-14）。

    分子 verbatim: SDD [L1416]「构造一级库中 C 类占比上升的场景」；分母 derived: 与占比双报
    share_* 同源并按 [L1004] 剔除 NOT_ASSESSED（pooling.assessed_denominator）。阈值 1E-12
    是**工程默认、非业务签认值**（PLACEHOLDER：建议新立 K-21），报告里如实写明，不伪装成签认值。
    上期基线缺失时不猜「没上升」：显式披露判据不可比（V-14）。
    '''
    now = pooling.c_class_share(stats)
    out = ['- G-14 C 类占比（分子 = C 类计数，[L1416]；分母 = 已参评数，与占比双报 share_* 同源、'
           '按 [L1004] 剔除 NOT_ASSESSED）：' + fmt_ratio(now)]
    if previous is None:
        out.append('- G-14 MIX_QUALITY_DEGRADED 判据：本期**不可比** —— 无上期 pool_stats 基线'
                   '（V-14：不得当作「没上升」静默略过；接线见 P2-wire）')
        return out
    before = pooling.c_class_share(previous)
    verdict = pooling.mix_quality_verdict(stats, previous)
    out.append('- G-14 上期 C 类占比：' + fmt_ratio(before) + ' -> 本期 ' + fmt_ratio(now)
               + '；判据阈值 1E-12 为**工程默认、非业务签认值**（PLACEHOLDER：建议新立 K-21）')
    if verdict is None:
        out.append('- G-14 判据结论：C 类占比未上升 -> 本期无 MIX_QUALITY_DEGRADED 警示')
    else:
        sev = reason_codes.severity(verdict)
        out.append('- G-14 判据结论：**' + str(getattr(verdict, 'value', verdict)) + '** '
                   + reason_codes.message(verdict) + '（severity '
                   + str(getattr(sev, 'value', sev))
                   + '，blocks_run=' + fmt_bool(reason_codes.blocks_run(verdict))
                   + '，不中断 Step 7）')
    return out


def _section_6(frames) -> list:
    stats = frames.pool_stats
    ev = tuple(sorted(_rows(frames.evidence), key=_locator))
    if stats is None and not ev:
        return _no_data('pool_stats / evidence（证据结构）')
    out = []
    if stats is None:
        out += _no_data('pool_stats（A/B/C/D 计数与 NOT_ASSESSED 明细）')
    else:
        structure = stats.evidence_structure or {}
        total = sum(int(structure.get(c, 0)) for c in EVIDENCE_CLASSES)
        out += _table(('evidence_class', '条数', '占已分类比'),
                      [(c, fmt_int(structure.get(c, 0)), share(structure.get(c, 0), total)) for c in EVIDENCE_CLASSES])
        out.append('- NOT_ASSESSED 计数（单独计数，不得并入任何等级）：' + fmt_int(stats.not_assessed_count))
        out.append('- NOT_ASSESSED 明细（原因码 → 条数）：' + ('；'.join(
            str(code) + ' ' + fmt_int(n) for code, n in sorted((stats.not_assessed_reasons or {}).items()))
            or '本期无记录'))
        # [L1004] / ORCH-37 第 3、6 条：证据结构占比的分母（已分类合计）与 G-14 判据量的
        # 分母（assessed_denominator，剔 NOT_ASSESSED）是两个口径，报告里分开写明，严禁混用。
        out.append('- 计数口径：上表占比分母 = A/B/C/D 已分类合计 ' + fmt_int(total)
                   + '；G-14 判据量分母 = 已参评数（Σevidence_structure - not_assessed_count，'
                   '[L1004] 剔 NA，pooling.assessed_denominator）。两个分母口径不同，不得混用')
        out += _scope_summary(frames.evaluation_scope)
        # GAP-06 / ORCH-36 第 4 条：G-14 判据必须出现在报告里（本段就是 [L1063] 的
        # ⑥「证据结构（A/B/C/D 计数与 NOT_ASSESSED 明细）」，与 C 类占比同段披露）。
        out += _mix_quality_lines(stats, frames.previous_pool_stats)
    if ev:
        out += _table(('strategy_id', 'version_id', 'evidence_class', 'evidence_reason', '解释限制已填'),
                      [(r.strategy_id, r.version_id, r.evidence_class, str(r.evidence_reason),
                        fmt_bool(bool(r.interpretation_limit))) for r in ev])
    return out


def _section_7(frames, config) -> list:
    rep = frames.sensitivity
    if rep is None:
        return _no_data('sensitivity（稳健性结果）')
    verdict = sensitivity.veto(rep)
    out = ['- flip_rate 复核 / 否决门槛（K 类参数，未签认）：review=' + fmt_config_value(config, 'flip_rate_review_max')
           + '，unusable=' + fmt_config_value(config, 'flip_rate_unusable_max')]
    if rep.by_scheme:
        out += _table(('scheme', 'overall_flip_rate', 'flipped_count', 'assessed_count', '方案原因码', '非补偿否决', 'usable_for_elimination'),
                      [(r.scheme, fmt_ratio(r.overall_flip_rate), fmt_int(r.flipped_count), fmt_int(r.assessed_count),
                        str(r.flag) if r.flag else NULL, fmt_bool(verdict.vetoed),
                        fmt_bool(verdict.usable_for_elimination)) for r in rep.by_scheme])
    else:
        out += _no_data('sensitivity.by_scheme（逐方案 flip_rate）')
    if rep.by_strategy:
        counts = {}.fromkeys(STABILITY_LABELS, 0)
        for row in rep.by_strategy:
            counts[row.stability_label] += 1
        out += _table(('stability_label', '条数'), [(tag, fmt_int(counts[tag])) for tag in STABILITY_LABELS])
        out += _table(('strategy_id', 'version_id', 'stability_label', 'flip_under_pct10', 'flip_under_pct20'),
                      [(r.strategy_id, r.version_id, r.stability_label, fmt_ratio(r.flip_under_pct10),
                        fmt_ratio(r.flip_under_pct20)) for r in sorted(rep.by_strategy, key=_locator)])
    else:
        out += _no_data('sensitivity.by_strategy（稳定性标签分布）')
    out.append('- LOO 主导指标：' + ('、'.join(rep.loo_dominant_metrics) or '本期无记录'))
    # ORCH-40 第 7 条：loo_dominant_metrics（[L1018] flip_rate 判据）与 loo_impact
    # （[L748] 影响力排名）是两个字段，各自独立呈现，不合并、不互相替代。
    out += _loo_impact_lines(rep)
    out.append('- NORM_SWAP 秩相关：' + fmt_ratio(rep.norm_swap_rank_correlation))
    out.append('- 稳健性标记：' + ('、'.join(str(f) for f in rep.flags) or '无'))
    if verdict.vetoed:
        out.append('- 稳健性非补偿否决已触发（' + ','.join(str(c) for c in verdict.codes) + '）：本期结论不得作为淘汰唯一依据')
    return out


def _section_8(frames) -> list:
    tri = frames.triangulation
    if tri is None:
        return _no_data('triangulation（方法三角一致性）')
    out = ['- 判定：' + (str(tri.agreement) if tri.agreement else NULL),
           '- rho_main_topsis=' + fmt_ratio(tri.rho_main_topsis) + '，rho_main_gra=' + fmt_ratio(tri.rho_main_gra)
           + '，rho_topsis_gra=' + fmt_ratio(tri.rho_topsis_gra) + '，mean_rho=' + fmt_ratio(tri.mean_rho),
           '- 三角标记：' + ('、'.join(str(f) for f in tri.flags) or '无'),
           '- GRA 关联系数（metric_id → 均值）：' + ('；'.join(k + '=' + fmt_ratio(v) for k, v in sorted(tri.gra_by_metric.items())) or '本期无记录')]
    # CONSUMPTION-TODO 第 3 条的披露位：dsm/triangulation.py:380-388 / :420-426 把零方差的
    # 那一对 rho 与 agreement 置 None 而不带码，渲染层不得让 null 静默出报告（V-14）。
    undefined = tuple(name for name, value in (('rho_main_topsis', tri.rho_main_topsis),
                                              ('rho_main_gra', tri.rho_main_gra),
                                              ('rho_topsis_gra', tri.rho_topsis_gra),
                                              ('mean_rho', tri.mean_rho)) if value is None)
    if undefined or not tri.agreement:
        out.append('- Spearman 相关无定义：' + ('、'.join(undefined) if undefined else '四个 rho 均有值')
                   + '；agreement=' + (str(tri.agreement) if tri.agreement else NULL)
                   + '（本期不给一致性结论，[L1022] 不入分）—— 「无定义」不得读作 0 相关，'
                   + '也不得静默省略（V-14）')
        out.append(_code_line(RC.SPEARMAN_ZERO_VARIANCE))
    out += _table(('strategy_id', 'version_id', 'topsis_rank', 'gra_rank', '名次差'),
                  [(r.strategy_id, r.version_id, fmt_int(r.topsis_rank), fmt_int(r.gra_rank),
                    fmt_int(r.topsis_rank - r.gra_rank)) for r in sorted(tri.rows, key=_locator)]) if tri.rows else _no_data('triangulation.rows（逐策略名次）')
    return out


def _section_9(frames) -> list:
    rows = frames.entropy_diagnostics
    if not rows:
        return _no_data('entropy_diagnostic（指标健康度与字典工单）')
    out = _table(('metric_code', 'e_j', 'd_j', 'cv_j', 'vif_j', 'max_abs_corr', 'status', '建议动作'),
                 [(r.metric_code, fmt_ratio(r.e_j), fmt_ratio(r.d_j), fmt_ratio(r.cv_j), fmt_ratio(r.vif_j),
                   fmt_ratio(r.max_abs_corr), r.status, str(r.suggested_action) if r.suggested_action else NULL)
                  for r in sorted(rows, key=lambda x: x.metric_code)])
    tickets = [r for r in rows if r.suggested_action is not None]
    out.append('- 字典工单 ' + fmt_int(len(tickets)) + ' 张（责任人取自 T2 字典表，本模块不拟定人名）' if tickets else '- 本期无字典工单：全部指标健康度 OK')
    out += _table(('metric_code', '建议动作原因码', '责任人'),
                  [(r.metric_code, str(r.suggested_action), r.owner) for r in tickets])
    return out


def _section_10(bundle, frames, config) -> list:
    warn = [f for f in bundle.preflight_findings if f.severity is Severity.WARN]
    out = _table(('编号', '严重度', '内容'), [(f.code, f.severity.value, f.message) for f in warn]) if warn else _no_data('preflight WARN（本期无 WARN 记录）')
    if bundle.downgrade_actions:
        out += ['- 降级动作全量 ' + fmt_int(len(bundle.downgrade_actions)) + ' 条：']
        out += _table(('原因码', '动作', '对象'), [(str(a.reason_code), a.action, a.subject or NULL) for a in bundle.downgrade_actions])
    else:
        out += _no_data('降级动作（本期无降级）')
    out.append('- 权重版本 ' + bundle.weight_version_id + '；dsm_version=' + bundle.dsm_version + '；design_version='
               + bundle.design_version + '；cel_contract_version=' + bundle.cel_contract_version)
    if frames.weight_provenance is None:
        out += _no_data('weight provenance（四段权重溯源未随附）')
    else:
        prov = frames.weight_provenance
        out.append('- 权重 provenance：kind=' + prov.kind + '，生效期 ' + prov.effective_from.isoformat()
                   + ' 至 ' + prov.effective_to.isoformat() + '（签认人与日期取自权重版本文件，本模块不拟定人名）')
    out.append('- 配置全量快照 SHA256：' + bundle.config_snapshot_sha256)
    out.append('- exit_code=' + fmt_int(bundle.exit_code) + '；reproducibility_hash=' + bundle.reproducibility_hash)
    out += ['- 复现指引：' + step for step in audit.rerun_steps(bundle)]
    out.append('- 开放参数 K-01~K-20（须行方签认，未签认前一律 PLACEHOLDER，本模块不拟定任何业务数值）：')
    out += _table(('开放参数编号', '取值'), [(k, PLACEHOLDER) for k in OPEN_PARAMETER_IDS])
    incomplete = [(r, ledger_missing_items(r)) for r in (frames.grade_ledger or ()) if ledger_missing_items(r)]
    if incomplete:
        out += ['- 台账不完整清单：']
        out += _table(('strategy_id', 'version_id', 'grade', '缺项'),
                      [(r.strategy_id, r.version_id, r.grade, '、'.join(items)) for r, items in incomplete])
    return out


# --------------------------------------------------------------------------- score_card
SCORE_CARD_COLUMNS = tuple(ScoreCardRow.model_fields)
CEL0_COLUMNS = ('incremental_value', 'incremental_ci_lower', 'incremental_ci_upper',
                'estimator_method', 'value_captured_minor')
GRADE_LEDGER_COLUMNS = tuple(GradeLedgerRow.model_fields)
LEDGER_MISSING_COLUMN = 'ledger_missing_items'
SENSITIVITY_COLUMNS = ('grain', 'strategy_id', 'version_id', 'scheme',
                       'overall_flip_rate', 'flipped_count', 'assessed_count',
                       'scheme_flag', 'vetoed', 'usable_for_elimination',
                       'stability_label', 'flip_under_pct10', 'flip_under_pct20')
ENTROPY_COLUMNS = tuple(EntropyDiagnosticRow.model_fields)


def _score_card_cells(row: ScoreCardRow) -> tuple:
    '''[L1612]-[L1626] 十五段逐段落列：版本四元组、per_metric、per_dim、双 composite、
    证据三列、解释限制、红线、等级、封顶、池、一级库、稳定性、淘汰可用性、CEL-0。
    CEL-0 为空时明写「本期末接入增量估计」，不得静默留白。'''
    empty = _cel_empty(row)
    cells = []
    for name in SCORE_CARD_COLUMNS:
        if empty and name in CEL0_COLUMNS:
            cells.append(CEL0)
        else:
            cells.append(fmt_cell(getattr(row, name)))
    return tuple(cells)


def render_score_card_csv(rows) -> str:
    ordered = sorted(rows or (), key=_locator)
    return _csv(SCORE_CARD_COLUMNS, [_score_card_cells(row) for row in ordered])


# --------------------------------------------------------------------------- grade_ledger
def render_grade_ledger_csv(rows) -> str:
    '''recommended_action 与 decided_action 是表头里的两个独立列：各写各的值，
    各自可为 null，谁也不得被另一个填充（[L1630] / V-8）。'''
    header = GRADE_LEDGER_COLUMNS + (LEDGER_MISSING_COLUMN,)
    ordered = sorted(rows or (), key=_locator)
    out = []
    for row in ordered:
        cells = [fmt_cell(getattr(row, name)) for name in GRADE_LEDGER_COLUMNS]
        missing = ledger_missing_items(row)
        cells.append('、'.join(missing) if missing else LEDGER_COMPLETE)
        out.append(cells)
    return _csv(header, out)


# --------------------------------------------------------------------------- 稳健性 / 诊断
def render_sensitivity_csv(rep) -> str:
    if rep is None:
        return _csv(SENSITIVITY_COLUMNS, [])
    verdict = sensitivity.veto(rep)
    rows = []
    for item in rep.by_scheme:
        rows.append(('SCHEME', NULL, NULL, item.scheme, fmt_ratio(item.overall_flip_rate),
                     fmt_int(item.flipped_count), fmt_int(item.assessed_count),
                     str(item.flag) if item.flag else NULL, fmt_bool(verdict.vetoed),
                     fmt_bool(verdict.usable_for_elimination), NULL, NULL, NULL))
    for item in rep.by_strategy:
        rows.append(('STRATEGY', item.strategy_id, item.version_id, NULL, NULL, NULL,
                     NULL, NULL, fmt_bool(verdict.vetoed),
                     fmt_bool(verdict.usable_for_elimination), item.stability_label,
                     fmt_ratio(item.flip_under_pct10), fmt_ratio(item.flip_under_pct20)))
    return _csv(SENSITIVITY_COLUMNS, rows)


def render_entropy_csv(rows) -> str:
    ordered = sorted(rows or (), key=lambda x: x.metric_code)
    return _csv(ENTROPY_COLUMNS, [[fmt_cell(getattr(row, name)) for name in ENTROPY_COLUMNS]
                                  for row in ordered])


def render_triangulation_md(frames) -> str:
    body = _section_8(frames)
    rows = () if frames.triangulation is None else frames.triangulation.rows
    table = _table(('strategy_id', 'version_id', 'topsis_rank', 'gra_rank',
                    '主分名次偏差'),
                   [(r.strategy_id, r.version_id, fmt_int(r.topsis_rank),
                     fmt_int(r.gra_rank), fmt_int(r.topsis_rank - r.gra_rank))
                    for r in sorted(rows, key=_locator)]) if rows else _no_data(
                        'triangulation.rows（逐策略名次）')
    return '\n'.join(['# 方法三角一致性报告（triangulation.md）', '']
                     + body + table + ['']) + '\n'


def render_audit_json(bundle) -> str:
    '''R-7：正文就是 audit.serialize_bundle 的输出，一个字节也不改；写盘归本层。'''
    return audit.serialize_bundle(bundle)


# --------------------------------------------------------------------------- report.md
def render_report_md(bundle, frames, config=None) -> str:
    parts = (_section_1(bundle, frames), _section_2(frames), _section_3(frames),
             _section_4(frames), _section_5(frames), _section_6(frames),
             _section_7(frames, config), _section_8(frames), _section_9(frames),
             _section_10(bundle, frames, config))
    if len(parts) != len(REPORT_SECTIONS):
        raise ReportError('段数与十段标题不一致')
    lines = ['# DSM 策略评价报告（report.md）', '',
             'run_id：' + bundle.run_id, 'period：' + bundle.period,
             'weight_version_id：' + bundle.weight_version_id, '']
    for title, body in zip(REPORT_SECTIONS, parts):
        lines += ['## ' + title, ''] + list(body) + ['']
    return '\n'.join(lines).rstrip('\n') + '\n'


def section_titles(report_md) -> tuple:
    return tuple(line[3:] for line in report_md.split('\n') if line[:3] == '## ')


def assert_report_sections(report_md) -> tuple:
    '''G-14：十段齐全且顺序固定，缺任一段或顺序错乱即失败。'''
    got = section_titles(report_md)
    if got != REPORT_SECTIONS:
        raise ReportError('report.md 十段结构与 [L1063] 不符：实得 ' + repr(got)
                          + '，应为 ' + repr(REPORT_SECTIONS))
    return got


def split_sections(report_md) -> dict:
    assert_report_sections(report_md)
    blocks = {}
    current = None
    for line in report_md.split('\n'):
        if line[:3] == '## ':
            current = line[3:]
            blocks[current] = []
        elif current is not None:
            blocks[current].append(line)
    return {title: '\n'.join(body) for title, body in blocks.items()}


def render(bundle: AuditBundle, frames: AllFrames, config=None) -> ReportSet:
    '''[L1061] 签名逐字。产出 [L1062] 的七件产物文本，写盘见 write_report_set。'''
    report_md = render_report_md(bundle, frames, config)
    assert_report_sections(report_md)
    return ReportSet(
        report_md=report_md,
        score_card_csv=render_score_card_csv(frames.score_card),
        grade_ledger_csv=render_grade_ledger_csv(frames.grade_ledger),
        sensitivity_report_csv=render_sensitivity_csv(frames.sensitivity),
        entropy_diagnostic_csv=render_entropy_csv(frames.entropy_diagnostics),
        triangulation_md=render_triangulation_md(frames),
        audit_json=render_audit_json(bundle))


def write_report_set(report_set: ReportSet, out_dir) -> dict:
    '''写盘 + 产出指纹。指纹走 audit.fingerprint_outputs，本模块不实现哈希。'''
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, text in report_set.artifacts().items():
        path = root / name
        path.write_text(text, encoding='utf-8')
        paths[name] = path
    return audit.fingerprint_outputs(paths)
