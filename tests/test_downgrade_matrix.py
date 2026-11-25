'''tests/test_downgrade_matrix.py -- M28-1：契约 §3.14 降级矩阵（[L1276]-[L1307]）逐行裁判。

口径声明（主控 ORCH-56 裁决，纪律要求，不得省略）
--------------------------------------------------------------------------
1. 本模块走**渲染层口径**：用 dsm/reports.py:785 的纯函数
   render(bundle, frames, config=None) -> ReportSet 直接构造 AuditBundle 渲染，
   断言契约矩阵每一行的「降级动作 / 是否出分 / 披露位置」落在它自己的披露通道里
   （report.md 某段 / score_card.csv / entropy_diagnostic.csv /
   sensitivity_report.csv / triangulation.md / audit.json / 退出码 / config 层错误信息）。
   既有先例：tests/test_reports.py:147 与 :382 同样直构 bundle 绕开 cli。
2. **本包不覆盖端到端可达性**：真跑 dsm score 落盘七件产物依赖 M29-1 的九步
   marshal（dsm/cli.py:333 现仍 raise InvariantError）与 M29-2 的 write_report_set
   生产调用点。**严禁把本模块的绿读作「端到端已验证」**。
3. 矩阵形状实测（本包在开工 HEAD 上亲自复测契约原文，非转录）：数据行
   [L1280]-[L1305] = **26 行**，表头 [L1278] 逐字 = **5 列**
   （情形 | 检测点 | 降级动作 | 是否出分 | 披露位置）。docs/RUN-UNATTENDED-v1.2.md §3
   的「六列」是转述笔误（ERRATUM-V12-05，主控已确认）。
4. 已登记缺口（本包不写必红断言，只如实披露）：
   * GAP-M28-1-01（[L1298]）：dsm/reports.py 全文无「秩反转」/anchor 字面
     （grep 0 命中，实测），契约第 5 列「报告首屏」当前由 preflight finding/act
     -> audit.json + report.md ⑩段承载，①首屏本身不渲染该串。
   * GAP-M28-1-02（[L1299]）：dsm/sensitivity.py:581-583 veto() 只认 BLOCK 级 flag，
     review 档（FLIP_RATE_REVIEW = WARN）不把 usable_for_elimination 压成 false，
     与契约第 3 列「flip_rate 超 review_max -> 台账 usable_for_elimination = false」有差。
   * GAP-M28-1-03（[L1299]）：契约字面句「本期结果不得用于淘汰决策」在 reports.py
     无逐字对应，实得「本期结论不得作为淘汰唯一依据」。
   * GAP-M28-1-04（[L1303]，M28-PRE 风险 R-5）：[L1302] 与 [L1303] 共用退出码 7，
     而 dsm/cli.py:28-29 _CODE_STATUS 把 7 固定映射为单标签 ALPHA_INFEASIBLE，故
     「[L1303] 的报告披露含 ALPHA_FLOOR_INFEASIBLE」现实现给不出；闭合需改
     dsm/cli.py（M29-1 写集），本包不写该断言。
   * GAP-M28-1-05（[L1286]，R-3 同类）：契约 [L1286] 第 5 列写的是**码名**
     WEIGHT_REALLOCATED 而不是披露位置，dsm/preflight.py:54 已如实复刻。按契约原文
     断言等值，**不顺手修正**契约或实现。
   * GAP-M28-1-06（[L1284] / [L1290]）：实现侧披露串比契约第 5 列更具体
     （契约 audit -> 实现 audit + 退出码 2；契约 flag -> 实现 score_card flag）。
     本包按实现真值断言等值，同时断言契约字面被包含，差异登记不改实现。
   * GAP-M28-1-07（[L1280] / [L1281]）：config 层 WeightVersionInvalidError 自带
     exit_code = 2（dsm/config.py:696，与契约「退出码 2」一致），但 dsm/cli.py:56 的
     _EXCEPTION_CODES 把该类名映射到 3（CONFIG）。本包只断言 config 层与 preflight 层
     的 2，不断言 cli 外壳映射；dsm/cli.py 属 M29-1 写集（且本包施工期间正被并发修改），
     差异交主控登记。
   * 产物字节口径（实测）：dsm/reports.py:738-742 render_audit_json 的正文是
     audit.serialize_bundle 的 canonical_text（形如 obj:AuditBundle{s:...}，不是 JSON，
     非 ASCII 被转义），故中文披露串在 AuditBundle 载荷上断言、ASCII 码名在 audit.json
     字节上断言。
5. 码名来源（R-12 纪律）：契约 26 行原文**只字面给出 6 个码名**
   （WEIGHT_REALLOCATED / NOT_ASSESSED / WAIVER_INVALID / METHOD_DIVERGENCE /
   ENTROPY_INSUFFICIENT_SAMPLE，另 [L1297] 字面给出的是状态名 INACTIVE 而非码名）。
   其余行的码名系 M28-PRE 依契约第 1/2/3 列**语义推定**（dsm_stage/V12-M28-PRE/out/
   matrix_code_map.tbl 第 5 列），主控 ORCH-56 采纳；凡推定码名，本模块都在该行
   注释里逐字标注，并在交付回报 GAPS 里列出待业务语义确认。
6. 写集纪律：本文件是 M28-1 的唯一写集；dsm/reports.py、dsm/preflight.py、
   dsm/cli.py、dsm/reason_codes.py、dsm/models.py、config/**、docs/**、ops/** 与
   其余 tests/** 一律未改（R-14 零弱化：无 skip / xfail / try-except 兜底 / or 化断言）。
'''
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from dsm import (audit, cli, config, normalize, preflight, reason_codes, reports,
                 sensitivity, triangulation, weights_calibrate)
from dsm.audit import RunContext
from dsm.models import (DowngradeAction, EntropyDiagnosticRow, EvidenceFrame,
                        EvidenceRow, GradeLedgerRow, InputTableFingerprint, PoolKey,
                        PoolStats, PoolStatRow, RedlineEvalRow, RedlineFrame,
                        ScoreCardDimCell, ScoreCardMetricCell, ScoreCardRow,
                        SensitivityReport, SensitivitySchemeResult,
                        SensitivityStrategyRow, TriangulationReport,
                        TriangulationStrategyRow)
from dsm.reason_codes import RC, Severity
from dsm.reports import (ARTIFACT_NAMES, AllFrames, GateStatus, REPORT_SECTIONS,
                         split_sections)

RUN_AT = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
HEX64 = 'ab' * 32
PERIOD = '2026Q1'
# 契约 [L1278] 表头逐字（五列）；[L1279] 分隔行同为五列。
HEADER = ('情形', '检测点', '降级动作', '是否出分', '披露位置')
FIRST_LINE, LAST_LINE, ROW_COUNT = 1280, 1305, 26
S1, S5, S6, S7, S8, S9, S10 = 0, 4, 5, 6, 7, 8, 9      # REPORT_SECTIONS 下标


@dataclass(frozen=True)
class Row:
    '''契约矩阵一行的逐字转录 + 本包为它分派的披露通道。

    codes / severities 一一对应；literal 里的码名是契约原文逐字出现的（第 3 或第 5 列），
    不在 literal 里的码名是 M28-PRE 语义推定（见模块 docstring 第 5 条）。
    '''

    line: str
    situation: str
    checkpoint: str
    action: str
    scored: str
    disclosure: str
    codes: tuple
    literal: tuple
    severities: tuple

    @property
    def cells(self) -> tuple:
        return (self.situation, self.checkpoint, self.action, self.scored,
                self.disclosure)

MATRIX = (
    Row('L1280', '权重版本过期或 DRAFT', 'C-01 / config', '**BLOCK**', '否',
        'audit + 退出码 2', ('WEIGHT_VERSION_STALE', 'WEIGHT_VERSION_DRAFT'), (),
        ('BLOCK', 'BLOCK')),
    Row('L1281', '权重 FROZEN 但缺 whatif_run_id', 'config', '**加载失败**', '否',
        '错误信息', ('WEIGHT_MISSING_WHATIF_RUN_ID',), (), ('BLOCK',)),
    Row('L1282', '配置含 PLACEHOLDER', 'config', '**抛错终止**', '否',
        '一次列出全部未填字段路径', ('CONFIG_PLACEHOLDER',), (), ('BLOCK',)),
    Row('L1283', '金额字段非整数', 'C-09 / io_loaders', '**BLOCK**', '否', 'audit',
        ('MONEY_NON_INTEGER',), (), ('BLOCK',)),
    Row('L1284', '口径版本不一致', 'C-07', '**BLOCK**', '否', 'audit',
        ('CALIBER_VERSION_MISMATCH',), (), ('BLOCK',)),
    Row('L1285', '指标未签认', 'C-02', '剔除该指标，权重重归一', '是（降 coverage）',
        'score_card flag + 报告附录', ('METRIC_NOT_SIGNED',), (), ('WARN',)),
    Row('L1286', '某维度指标被清空', 'C-02',
        '该维度 W 置 0 并重归一；清空维度数 ≥ 2 → **BLOCK**', '视情况',
        'WEIGHT_REALLOCATED', ('WEIGHT_REALLOCATED', 'DIMENSION_EMPTIED'),
        ('WEIGHT_REALLOCATED',), ('WARN', 'BLOCK')),
    Row('L1287', '缺失率超 warn 阈', 'C-04', 'WARN，按 missing_rule 处理', '是',
        'preflight findings', ('MISSING_RATE_WARN',), (), ('WARN',)),
    Row('L1288', '缺失率超 block 阈', 'C-04', '该策略 NOT_ASSESSED', '否',
        '台账单独计数', ('MISSING_RATE_BLOCK', 'NOT_ASSESSED'), ('NOT_ASSESSED',),
        ('BLOCK', 'BLOCK')),
    Row('L1289', '数据过期', 'C-05', 'WARN + 标注', '是', 'score_card',
        ('DATA_STALE',), (), ('WARN',)),
    Row('L1290', '数据质量 SUSPECT', 'C-06', '剔除该指标', '是（降 coverage）',
        'flag', ('DATA_QUALITY_SUSPECT',), (), ('WARN',)),
    Row('L1291', '评价设计卡 PARTIAL', 'C-08', '证据上限压到 C', '是',
        'evidence_reason', ('EVIDENCE_CARD_PARTIAL',), (), ('WARN',)),
    Row('L1292', '评价设计卡 MISSING', 'C-08', '证据 D → NOT_ASSESSED', '否',
        '台账单独计数',
        ('EVIDENCE_CARD_MISSING', 'EV_D_NOT_ASSESSED', 'NOT_ASSESSED'),
        ('NOT_ASSESSED',), ('BLOCK', 'BLOCK', 'BLOCK')),
    Row('L1293', 'C 类无解释限制', 'evidence Step 5', '降为 D → NOT_ASSESSED', '否',
        'evidence_reason', ('EVIDENCE_C_NO_LIMIT', 'NOT_ASSESSED'),
        ('NOT_ASSESSED',), ('BLOCK', 'BLOCK')),
    Row('L1294', 'HARD 红线违反且无有效豁免', 'redline',
        '**强制 L4**，分数照算但不生效', '是（不生效）', '红线清单 + 台账',
        ('REDLINE_HARD_HIT', 'GR_REDLINE_FORCED'), (), ('BLOCK', 'BLOCK')),
    Row('L1295', '豁免过期或范围不符', 'redline', '视为无豁免，记 WAIVER_INVALID',
        '是', '红线清单', ('WAIVER_INVALID', 'WAIVER_EXPIRED'),
        ('WAIVER_INVALID',), ('BLOCK', 'BLOCK')),
    Row('L1296', '目标值覆盖不足', 'attainment / grading',
        '等级封顶 max_grade_if_no_target', '是（封顶）', 'capped_flag + cap_reason',
        ('GR_CAPPED_NO_TARGET', 'ATTAINMENT_CAPPED'), (), ('WARN', 'INFO')),
    Row('L1297', '指标零变异（sd = 0）', 'normalize / diagnostics',
        'INACTIVE，剔除并预警；造权重阶段走 AHP 回退', '是', 'entropy_diagnostic',
        ('INACTIVE_METRIC',), (), ('WARN',)),
    Row('L1298', '锚定集失效', 'C-10', '回退为仅当期归一化 + **显著标注秩反转风险**',
        '是', '报告首屏', ('ANCHOR_SET_STALE', 'RANK_REVERSAL_RISK'), (),
        ('WARN', 'WARN')),
    Row('L1299', 'flip_rate 超 review_max', 'sensitivity',
        '报告首屏声明「本期结果不得用于淘汰决策」+ 台账 usable_for_elimination = false',
        '是', '首屏警示', ('FLIP_RATE_REVIEW', 'FLIP_RATE_UNUSABLE'), (),
        ('WARN', 'BLOCK')),
    Row('L1300', '三方法排序分歧', 'triangulation', 'METHOD_DIVERGENCE，要求人工复核',
        '是', '首屏警示', ('METHOD_DIVERGENCE',), ('METHOD_DIVERGENCE',),
        ('BLOCK',)),
    Row('L1301', '熵权样本不足（组合阶段）', 'weights_combine',
        '回退纯 AHP（α=1）+ 草稿首屏显著标注', '是（权重草稿）',
        'ENTROPY_INSUFFICIENT_SAMPLE', ('ENTROPY_INSUFFICIENT_SAMPLE',),
        ('ENTROPY_INSUFFICIENT_SAMPLE',), ('WARN',)),
    Row('L1302', 'α 可行集为空', 'weights_calibrate',
        '抛 AlphaInfeasibleError + 输出违反矩阵', '否（无权重草稿）', '退出码 7',
        ('ALPHA_INFEASIBLE',), (), ('BLOCK',)),
    Row('L1303', 'α* 低于 alpha_floor 且 floor 不可行', 'weights_calibrate',
        '抛 AlphaFloorInfeasibleError（**不静默降级**）', '否', '退出码 7',
        ('ALPHA_FLOOR_INFEASIBLE',), (), ('BLOCK',)),
    Row('L1304', 'CEL 字段存在但 cel.enabled = false', 'models / config',
        '字段一律不参与任何判定；报告显式写「本期末接入增量估计」，**不得静默留白**',
        '是', '报告', (), (), ()),
    Row('L1305', '内部不变量违反', '各模块断言',
        '抛 InvariantViolationError，退出码 5，**不产出任何结果**', '否', 'audit',
        ('INVARIANT_VIOLATION',), (), ('BLOCK',)),
)
BY_LINE = {row.line: row for row in MATRIX}

# --------------------------------------------------------------------- 渲染层夹具
def _score_card_row(**over):
    '''直构 ScoreCardRow（写法先例：tests/test_reports.py:36-53）。'''
    base = dict(
        strategy_id='S-001', version_id='V-1', period=PERIOD,
        weight_version_id='WV-1', dict_version='DICT-1', anchor_set_id='ANCH-1',
        run_id='RUN-1',
        per_metric={'M-1': ScoreCardMetricCell(
            actual_value=Decimal('0.5'), target_value=Decimal('0.4'),
            attainment=Decimal('1.25'))},
        per_dim={'DIM-1': ScoreCardDimCell(
            attainment=Decimal('1.25'), relative_score=Decimal('0.5'),
            coverage=Decimal('1'), weight=Decimal('1'))},
        composite_absolute=Decimal('1.02'), composite_relative=Decimal('0.5'),
        evidence_class='B', evidence_reason='EV_B_QUASI',
        evidence_source='CARD_ONLY', redline_pass=True, grade='L2',
        grade_reason_codes=('GR_EVIDENCE_GATE_L1',), capped_flag=False,
        eligible_for_L1_library=False, usable_for_elimination=True)
    base.update(over)
    return ScoreCardRow(**base)


def _ledger_row(**over):
    base = dict(strategy_id='S-001', version_id='V-1', period=PERIOD, grade='L2',
                recommended_action='ADV-A', decided_action='ADV-A',
                ledger_complete=False, usable_for_elimination=True)
    base.update(over)
    return GradeLedgerRow(**base)


def _pool_stats():
    '''⑥段「NOT_ASSESSED 单独计数」的上游（契约第 5 列「台账单独计数」）。'''
    return PoolStats(
        rows=(PoolStatRow(pool_key=PoolKey(biz_domain='CARD', evidence_class='B'),
                          count=1, share_in_pool=Decimal('1'),
                          share_overall=Decimal('1')),),
        evidence_structure={'A': 0, 'B': 1, 'C': 0, 'D': 0},
        not_assessed_count=1, not_assessed_reasons={'NOT_ASSESSED': 1})


def _sensitivity(flag=None, label='STABLE'):
    return SensitivityReport(
        by_scheme=(SensitivitySchemeResult(
            scheme='OAT_10', overall_flip_rate=Decimal('0.4'), flipped_count=4,
            assessed_count=10, flag=flag),),
        by_strategy=(SensitivityStrategyRow(
            strategy_id='S-001', version_id='V-1', stability_label=label,
            flip_under_pct10=Decimal('0'), flip_under_pct20=Decimal('0')),),
        loo_dominant_metrics=('M-1',), norm_swap_rank_correlation=Decimal('1'),
        flags=(), seed=7)


def _triangulation(agreement='METHOD_AGREEMENT'):
    return TriangulationReport(
        rows=(TriangulationStrategyRow(strategy_id='S-001', version_id='V-1',
                                       topsis_rank=1, gra_rank=2),),
        rho_main_topsis=Decimal('0.9'), rho_main_gra=Decimal('0.8'),
        rho_topsis_gra=Decimal('0.95'), mean_rho=Decimal('0.88'),
        agreement=agreement, gra_by_metric={'M-1': Decimal('0.7')}, flags=())


def _frames(**over):
    base = dict(gate_status=GateStatus(g5_dispute_source_review_signed=True,
                                       g7_governance_config_signed=True))
    base.update(over)
    return AllFrames(**base)


def _bundle(frames, findings=(), downgrades=(), exit_code=0, outputs=None):
    ctx = RunContext(
        run_id='RUN-1', run_at=RUN_AT, period=PERIOD, dsm_version='1.1.0',
        design_version='DSM-v1.1', cel_contract_version='CEL-0',
        weight_version_id='WV-1', seed=7, sensitivity_schemes=('OAT_10',),
        preflight_findings=tuple(findings), downgrade_actions=tuple(downgrades),
        exit_code=exit_code, score_card=tuple(frames.score_card or ()),
        grade_ledger=tuple(frames.grade_ledger or ()))
    inputs = {'T1': InputTableFingerprint(sha256=HEX64, row_count=3)}
    prints = ({name: HEX64 for name in ARTIFACT_NAMES} if outputs is None
              else dict(outputs))
    return audit.build_manifest(inputs, 'eval_config: {}', ctx, prints)


def _render(frames=None, findings=(), downgrades=(), exit_code=0, outputs=None):
    '''渲染层口径（ORCH-56）：reports.render 是纯函数，不需要 cli 九步 marshal。'''
    used = _frames() if frames is None else frames
    return reports.render(_bundle(used, findings, downgrades, exit_code, outputs),
                          used)


def _render_pair(frames=None, findings=(), downgrades=(), exit_code=0, outputs=None):
    '''同 _render，但同时交回 AuditBundle。实测：dsm/reports.py:738-742
    render_audit_json 的正文是 audit.serialize_bundle 的 canonical_text
    （形如 obj:AuditBundle{s:...}，不是 JSON，且非 ASCII 会被转义），故中文披露串
    一律在 AuditBundle 载荷上断言，ASCII 码名在 audit.json 字节上断言。'''
    used = _frames() if frames is None else frames
    bundle = _bundle(used, findings, downgrades, exit_code, outputs)
    return reports.render(bundle, used), bundle


def _section(report_md, index):
    return split_sections(report_md)[REPORT_SECTIONS[index]]


def _csv_rows(text) -> list:
    return list(csv.reader(text.splitlines()))


def _csv_row(text, index=1) -> dict:
    rows = _csv_rows(text)
    return dict(zip(rows[0], rows[index]))


def _finding(check, code, scope='run', detail='M28-1 矩阵行裁判'):
    '''镜像 dsm/preflight.py:77-84 _f() 的唯一 Finding 构造口（逐条对齐实测）：
    severity / owner_hint / 披露位置 / blocks_run 全部查表，本测试不改写。
    只对 DISCLOSURE 表内码可用；表外码走 _act()（dsm/preflight.py:177-180）。'''
    value = getattr(code, 'value', code)
    return preflight.Finding(
        code=check, reason_code=value, severity=reason_codes.severity(value),
        scope=scope, detail=detail, owner_hint=reason_codes.owner_hint(value),
        disclosure=preflight.DISCLOSURE[value],
        blocks_run=value in preflight.RUN_BLOCKING_CODES)


def _act(code, action, subject='S-001'):
    '''镜像 dsm/preflight.py:177-180 act()：不经 _f()、不受 DISCLOSURE 门禁，
    只受 models.DowngradeAction.reason_code 的注册性校验（dsm/models.py:730-740）。'''
    return DowngradeAction(reason_code=getattr(code, 'value', code), action=action,
                           subject=subject)

# ----------------------------------------------------------------- 逐行裁判（26 行）
def _case_l1280(row):
    '''实测依据：dsm/preflight.py:36-46 RUN_BLOCKING_CODES 含两码；:49-50 DISCLOSURE
    两码 = AUDIT_ONLY = 契约第 5 列逐字；:188/:192 C-01 发射点；dsm/config.py:1341/:1359
    权重版本层发射点（契约第 2 列 C-01 / config 两条通道都在）。两个码名均系语义推定。'''
    stale, draft = RC.WEIGHT_VERSION_STALE.value, RC.WEIGHT_VERSION_DRAFT.value
    assert preflight.AUDIT_ONLY == 'audit + 退出码 2' == row.disclosure
    assert preflight.DISCLOSURE[stale] == row.disclosure
    assert preflight.DISCLOSURE[draft] == row.disclosure
    assert stale in preflight.RUN_BLOCKING_CODES
    assert draft in preflight.RUN_BLOCKING_CODES
    assert preflight.EXIT_BLOCK == 2
    findings = tuple(_finding('C-01', c, scope='weight_version:WV-1',
                              detail='status = DRAFT，只有 FROZEN 可用于评分')
                     .to_audit_finding() for c in (stale, draft))
    report, bundle = _render_pair(exit_code=preflight.EXIT_BLOCK, findings=findings)
    assert stale in report.audit_json and draft in report.audit_json
    assert 'C-01' in report.audit_json
    assert len(bundle.preflight_findings) == 2
    assert all('披露=audit + 退出码 2' in f.message
               for f in bundle.preflight_findings)     # 契约第 5 列逐字进 audit 载荷
    assert bundle.exit_code == preflight.EXIT_BLOCK == 2
    assert 'exit_code=2' in _section(report.report_md, S10)
    err = config.WeightVersionInvalidError(
        RC.WEIGHT_VERSION_STALE,
        (('WEIGHT_COVERAGE', 'weights.period', '无覆盖评价期的 FROZEN 版本'),))
    assert err.exit_code == 2                          # GAP-M28-1-07：cli 外壳映射为 3
    assert stale in str(err)


def _case_l1281(row):
    '''契约第 5 列 = 「错误信息」：通道是 config 层异常消息，不是 report.md。
    实测依据：dsm/config.py:683-700 WeightVersionInvalidError 携 reason_code +
    violations 并渲染进消息；:1297/:1309 该码的发射点；dsm/preflight.py:200 C-01 亦发
    （注释逐字写明「[L1281] 归 config 层」）。码名系语义推定。'''
    code = RC.WEIGHT_MISSING_WHATIF_RUN_ID.value
    path = 'weights_w1.provenance.whatif_run_id'
    err = config.WeightVersionInvalidError(
        RC.WEIGHT_MISSING_WHATIF_RUN_ID,
        (('WEIGHT_WHATIF_RUN_ID', path, 'FROZEN 而缺 whatif_run_id'),))
    assert err.reason_code is RC.WEIGHT_MISSING_WHATIF_RUN_ID
    assert code in str(err) and path in str(err)      # 「错误信息」逐条列出违规位
    assert err.exit_code == 2                          # GAP-M28-1-07：cli 外壳映射为 3
    assert code in preflight.RUN_BLOCKING_CODES       # 是否出分 = 否
    assert preflight.DISCLOSURE[code] == preflight.AUDIT_ONLY
    assert reason_codes.severity(code) is Severity.BLOCK


def _case_l1282(row):
    '''契约第 5 列 = 「一次列出全部未填字段路径」。实测依据：dsm/config.py:173-182
    _format_message 逐条列出 paths（docstring 逐字：No path and no missing file is
    dropped）；:185-226 ConfigPlaceholderError 去重 + 定序 + exit_code = EXIT_CONFIG = 3；
    dsm/cli.py:56 (ConfigPlaceholderError, EXIT_CONFIG)。码名系语义推定。
    注：该码不在 preflight.DISCLOSURE 表内（实测 :48-63 仅 22 码），故本行走 config
    层错误信息通道，不走 report.md ⑩段（R-2 逐行分派）。'''
    paths = ('eval_config.yaml:period', 'weights_w1.yaml:status',
             'weights_w1.yaml:approval.date')
    err = config.ConfigPlaceholderError(paths)
    text = str(err)
    for path in paths:
        assert path in text                    # 一次列出全部，不是只报第一个
    assert len(err.paths) == 3 and set(err.paths) == set(paths)
    assert err.exit_code == config.EXIT_CONFIG == 3
    assert cli.exit_code_for(err) == 3
    assert reason_codes.severity(RC.CONFIG_PLACEHOLDER.value) is Severity.BLOCK


def _case_l1283(row):
    '''实测依据：dsm/preflight.py:52 DISCLOSURE[MONEY_NON_INTEGER] = audit =
    契约第 5 列逐字；:40 RUN_BLOCKING_CODES；:326 C-09 发射点；dsm/io_loaders.py:109
    同码在装载层的第二发射点（契约第 2 列 C-09 / io_loaders）。码名系语义推定。'''
    code = RC.MONEY_NON_INTEGER.value
    assert preflight.DISCLOSURE[code] == row.disclosure == 'audit'
    assert code in preflight.RUN_BLOCKING_CODES
    finding = _finding('C-09', code, scope='metric:M-1.target_value',
                       detail='target_value 应为最小货币单位整数').to_audit_finding()
    report, bundle = _render_pair(exit_code=preflight.EXIT_BLOCK, findings=(finding,))
    assert code in report.audit_json
    assert 'C-09' in report.audit_json
    assert bundle.preflight_findings[0].code == 'C-09'
    assert '披露=audit' in bundle.preflight_findings[0].message
    assert bundle.exit_code == 2
    assert 'exit_code=2' in _section(report.report_md, S10)


def _case_l1284(row):
    '''实测依据：dsm/preflight.py:52 DISCLOSURE = AUDIT_ONLY；:314 C-07 发射点。
    GAP-M28-1-06：契约第 5 列写 audit，实现写 audit + 退出码 2（更具体），
    本包按实现真值断言等值，并断言契约字面被包含，不顺手修正任何一侧。码名系语义推定。'''
    code = RC.CALIBER_VERSION_MISMATCH.value
    assert preflight.DISCLOSURE[code] == preflight.AUDIT_ONLY == 'audit + 退出码 2'
    assert row.disclosure in preflight.DISCLOSURE[code]
    assert code in preflight.RUN_BLOCKING_CODES
    finding = _finding('C-07', code, scope='metric:M-1',
                       detail='metric_facts 口径 != metric_dict 口径').to_audit_finding()
    report, bundle = _render_pair(exit_code=preflight.EXIT_BLOCK, findings=(finding,))
    assert code in report.audit_json and 'C-07' in report.audit_json
    assert '披露=audit + 退出码 2' in bundle.preflight_findings[0].message
    assert bundle.exit_code == preflight.EXIT_BLOCK


def _case_l1285(row):
    '''实测依据：dsm/preflight.py:53 DISCLOSURE = 契约第 5 列逐字；:209 C-02 发射点；
    dsm/reports.py:624-627 ⑩段 WARN 表（severity is WARN 才进表，实测）。码名系语义推定。'''
    code = RC.METRIC_NOT_SIGNED.value
    assert preflight.DISCLOSURE[code] == row.disclosure
    finding = _finding('C-02', code, scope='metric:M-9',
                       detail='signoff_status = UNSIGNED').to_audit_finding()
    tenth = _section(_render(findings=(finding,)).report_md, S10)
    assert code in tenth and 'C-02' in tenth and 'WARN' in tenth
    assert '披露=score_card flag + 报告附录' in tenth


def _case_l1286(row):
    '''GAP-M28-1-05（R-3）：契约第 5 列逐字就是码名 WEIGHT_REALLOCATED，
    dsm/preflight.py:54 如实复刻 —— 按契约原文断言等值，不修正。
    实测依据：:215 C-02 WEIGHT_REALLOCATED（WARN，「视情况」＝单维度清空仍出分）；
    :218-221 C-02 DIMENSION_EMPTIED（BLOCK）；:32 EMPTIED_DIM_BLOCK = 2；
    :40 RUN_BLOCKING_CODES 含 DIMENSION_EMPTIED；:51 DISCLOSURE = AUDIT_ONLY。
    码名 DIMENSION_EMPTIED 系 M28-PRE 依契约第 1/2/3 列语义推定，非契约字面指定。'''
    realloc = RC.WEIGHT_REALLOCATED.value
    emptied = RC.DIMENSION_EMPTIED.value
    assert realloc in row.literal
    assert preflight.DISCLOSURE[realloc] == row.disclosure == realloc
    assert reason_codes.severity(realloc) is Severity.WARN
    assert reason_codes.severity(emptied) is Severity.BLOCK
    assert preflight.EMPTIED_DIM_BLOCK == 2
    assert emptied in preflight.RUN_BLOCKING_CODES
    warn = _render(findings=(_finding('C-02', realloc, scope='dim:DIM-1',
                                      detail='W_DIM-1 置 0 并重归一')
                             .to_audit_finding(),))
    assert realloc in _section(warn.report_md, S10)
    block, block_bundle = _render_pair(
        exit_code=preflight.EXIT_BLOCK,
        findings=(_finding('C-02', emptied, scope='run',
                           detail='清空维度数 2').to_audit_finding(),))
    assert emptied in block.audit_json
    assert '披露=audit + 退出码 2' in block_bundle.preflight_findings[0].message
    assert block_bundle.exit_code == preflight.EXIT_BLOCK


def _case_l1287(row):
    '''实测依据：dsm/preflight.py:55 DISCLOSURE = 契约第 5 列逐字；:275 C-04 add；
    :278 act 的动作串逐字 = 按 missing_rule 处理缺失指标（契约第 3 列同义）；
    dsm/reports.py:627-629 ⑩段「降级动作全量」表。码名系语义推定。'''
    code = RC.MISSING_RATE_WARN.value
    assert preflight.DISCLOSURE[code] == row.disclosure == 'preflight findings'
    report = _render(
        findings=(_finding('C-04', code, scope='strategy:S-001',
                           detail='缺失率超过预警阈，按 missing_rule 处理')
                  .to_audit_finding(),),
        downgrades=(_act(code, '按 missing_rule 处理缺失指标'),))
    tenth = _section(report.report_md, S10)
    assert code in tenth and '披露=preflight findings' in tenth
    assert '降级动作全量 1 条' in tenth
    assert '按 missing_rule 处理缺失指标' in tenth


def _case_l1288(row):
    '''实测依据：dsm/preflight.py:33 LEDGER = 契约第 5 列逐字「台账单独计数」；
    :57-58 DISCLOSURE 两码 = LEDGER；:268/:271 C-04 add + act（动作串逐字）；
    dsm/reports.py:531-535 ⑥段「NOT_ASSESSED 计数（单独计数，不得并入任何等级）」。
    码名 MISSING_RATE_BLOCK 系语义推定；NOT_ASSESSED 是契约字面。'''
    block, na = RC.MISSING_RATE_BLOCK.value, RC.NOT_ASSESSED.value
    assert na in row.literal
    assert preflight.LEDGER == row.disclosure == '台账单独计数'
    assert preflight.DISCLOSURE[block] == preflight.LEDGER
    assert preflight.DISCLOSURE[na] == preflight.LEDGER
    report = _render(
        frames=_frames(pool_stats=_pool_stats()),
        findings=(_finding('C-04', block, scope='strategy:S-001',
                           detail='缺失率超过阻断阈').to_audit_finding(),),
        downgrades=(_act(block, '缺失率超阻断阈，记为不可评价'),))
    sixth = _section(report.report_md, S6)
    assert 'NOT_ASSESSED 计数（单独计数，不得并入任何等级）：1' in sixth
    assert 'NOT_ASSESSED 明细（原因码 → 条数）：' + na + ' 1' in sixth
    assert block in report.audit_json                  # BLOCK 级 finding 走 audit.json
    tenth = _section(report.report_md, S10)
    assert '缺失率超阻断阈，记为不可评价' in tenth and block in tenth


def _case_l1289(row):
    '''实测依据：dsm/preflight.py:53 DISCLOSURE = 契约第 5 列逐字；:288 C-05 发射点。
    码名系语义推定。'''
    code = RC.DATA_STALE.value
    assert preflight.DISCLOSURE[code] == row.disclosure == 'score_card'
    report = _render(findings=(_finding(
        'C-05', code, scope='data_as_of:2025-12-31',
        detail='data_as_of 早于评价期基准日').to_audit_finding(),))
    tenth = _section(report.report_md, S10)
    assert code in tenth and 'C-05' in tenth and '披露=score_card' in tenth


def _case_l1290(row):
    '''实测依据：dsm/preflight.py:56 DISCLOSURE = score_card flag；:295/:298 C-06
    add + act（动作串逐字）。GAP-M28-1-06：契约第 5 列写 flag，实现更具体。码名系语义推定。'''
    code = RC.DATA_QUALITY_SUSPECT.value
    assert preflight.DISCLOSURE[code] == 'score_card flag'
    assert row.disclosure in preflight.DISCLOSURE[code]
    report = _render(
        findings=(_finding('C-06', code, scope='strategy:S-001 metric:M-1',
                           detail='SUSPECT，该事实已剔除').to_audit_finding(),),
        downgrades=(_act(code, '剔除 SUSPECT 事实并降 coverage', 'S-001/M-1'),))
    tenth = _section(report.report_md, S10)
    assert code in tenth and '披露=score_card flag' in tenth
    assert '剔除 SUSPECT 事实并降 coverage' in tenth


def _case_l1291(row):
    '''实测依据：dsm/preflight.py:57 DISCLOSURE = 契约第 5 列逐字；:31
    CARD_PARTIAL_CEILING = C（契约第 3 列「证据上限压到 C」）；:361/:363 C-08
    add + act；dsm/evidence.py:313 return (C, RC.EVIDENCE_CARD_PARTIAL)；
    dsm/reports.py:539-542 ⑥段 evidence_reason 列。码名系语义推定。'''
    code = RC.EVIDENCE_CARD_PARTIAL.value
    assert preflight.DISCLOSURE[code] == row.disclosure == 'evidence_reason'
    assert preflight.CARD_PARTIAL_CEILING == 'C'
    frames = _frames(
        evidence=EvidenceFrame(rows=(EvidenceRow(
            strategy_id='S-001', version_id='V-1', evidence_class='C',
            evidence_reason=code, evidence_source='CARD_ONLY'),)),
        score_card=(_score_card_row(evidence_class='C', evidence_reason=code),))
    report = _render(frames=frames,
                     findings=(_finding('C-08', code, scope='strategy:S-001',
                                        detail='card_status = PARTIAL')
                               .to_audit_finding(),),
                     downgrades=(_act(code, '证据等级上限压到 C'),))
    sixth = _section(report.report_md, S6)
    assert code in sixth and 'evidence_reason' in sixth
    assert code in report.score_card_csv
    tenth = _section(report.report_md, S10)
    assert '证据等级上限压到 C' in tenth and code in tenth


def _case_l1292(row):
    '''实测依据：dsm/preflight.py:58 DISCLOSURE[EVIDENCE_CARD_MISSING] = LEDGER =
    契约第 5 列逐字；:355/:358 C-08 add + act；dsm/evidence.py:274 证据 D 判定。
    码名 EVIDENCE_CARD_MISSING / EV_D_NOT_ASSESSED 系语义推定；NOT_ASSESSED 是契约字面。'''
    missing = RC.EVIDENCE_CARD_MISSING.value
    ev_d = RC.EV_D_NOT_ASSESSED.value
    assert preflight.DISCLOSURE[missing] == preflight.LEDGER == row.disclosure
    frames = _frames(
        pool_stats=_pool_stats(),
        evidence=EvidenceFrame(rows=(EvidenceRow(
            strategy_id='S-002', version_id='V-1', evidence_class='D',
            evidence_reason=ev_d, evidence_source='CARD_ONLY'),)),
        score_card=(_score_card_row(strategy_id='S-002', grade='NOT_ASSESSED',
                                    evidence_class='D', evidence_reason=ev_d,
                                    composite_absolute=None,
                                    composite_relative=None),))
    report = _render(frames=frames,
                     findings=(_finding('C-08', missing, scope='strategy:S-002',
                                        detail='card_status = MISSING，证据判为 D')
                               .to_audit_finding(),),
                     downgrades=(_act(missing, '证据 D，记为不可评价', 'S-002'),))
    sixth = _section(report.report_md, S6)
    assert ev_d in sixth and '| D |' in sixth
    assert 'NOT_ASSESSED 计数（单独计数，不得并入任何等级）：1' in sixth
    assert missing in report.audit_json
    assert '证据 D，记为不可评价' in _section(report.report_md, S10)
    assert 'NOT_ASSESSED' in report.score_card_csv

def _case_l1293(row):
    '''实测依据：dsm/evidence.py:322 return (D, RC.EVIDENCE_C_NO_LIMIT)（契约第 2 列
    evidence Step 5）；dsm/reports.py:539-542 ⑥段 evidence_reason 列 = 契约第 5 列；
    score_card.csv 同名列（dsm/models.py:1058）。
    码名 EVIDENCE_C_NO_LIMIT 系语义推定；NOT_ASSESSED 是契约字面（第 3 列）。'''
    code = RC.EVIDENCE_C_NO_LIMIT.value
    frames = _frames(
        pool_stats=_pool_stats(),
        evidence=EvidenceFrame(rows=(EvidenceRow(
            strategy_id='S-003', version_id='V-1', evidence_class='D',
            evidence_reason=code, evidence_source='CARD_ONLY'),)),
        score_card=(_score_card_row(strategy_id='S-003', grade='NOT_ASSESSED',
                                    evidence_class='D', evidence_reason=code,
                                    interpretation_limit=None,
                                    composite_absolute=None,
                                    composite_relative=None),))
    report = _render(frames=frames)
    sixth = _section(report.report_md, S6)
    assert code in sixth and '| D |' in sixth          # 降为 D
    assert code in report.score_card_csv               # 披露位置 = evidence_reason
    assert 'NOT_ASSESSED 计数（单独计数' in sixth


def _case_l1294(row):
    '''实测依据：dsm/reports.py:462-478 ⑤段红线清单表（原因码列）与「HARD 命中为
    非补偿否决，分数照算但不生效，等级由红线强制」（契约第 3 列逐字同句）；
    dsm/grading.py:332-334 cap_reason = RC.GR_REDLINE_FORCED；dsm/redline.py:14
    「forced_grade 标记，消费侧由 grading.py 覆盖等级并落 RC.GR_REDLINE_FORCED」；
    dsm/pooling.py:484 RC.REDLINE_HARD_HIT。两个码名均系语义推定。'''
    hard, forced = RC.REDLINE_HARD_HIT.value, RC.GR_REDLINE_FORCED.value
    frames = _frames(
        redline=RedlineFrame(rows=(RedlineEvalRow(
            strategy_id='S-001', version_id='V-1', period=PERIOD, metric_id='M-1',
            level='HARD', comparator='GTE', threshold_value=Decimal('1'),
            hit=True, forced_grade='L4', reason_code=hard),)),
        score_card=(_score_card_row(redline_pass=False, redline_flags=(hard,),
                                    grade='L4', grade_reason_codes=(forced,)),),
        grade_ledger=(_ledger_row(grade='L4'),))
    report = _render(frames=frames)
    fifth = _section(report.report_md, S5)
    assert hard in fifth and 'HARD' in fifth and 'L4' in fifth
    assert '分数照算但不生效' in fifth
    cells = _csv_row(report.score_card_csv)
    assert cells['grade'] == 'L4' and cells['redline_pass'] == 'false'
    assert forced in report.score_card_csv and hard in report.score_card_csv
    assert 'L4' in report.grade_ledger_csv             # 台账


def _case_l1295(row):
    '''实测依据：dsm/reports.py:474-478 ⑤段「无留痕一律按未豁免处理」（契约第 3 列
    「视为无豁免」）；dsm/redline.py:231-239 豁免判定返回 WAIVER_INVALID，:237 过期档
    返回 WAIVER_EXPIRED。WAIVER_INVALID 是契约字面；WAIVER_EXPIRED 系语义推定。'''
    invalid, expired = RC.WAIVER_INVALID.value, RC.WAIVER_EXPIRED.value
    assert invalid in row.literal and invalid in row.action
    frames = _frames(redline=RedlineFrame(rows=(RedlineEvalRow(
        strategy_id='S-001', version_id='V-1', period=PERIOD, metric_id='M-1',
        level='HARD', comparator='GTE', threshold_value=Decimal('1'), hit=True,
        forced_grade='L4', waiver_approval_id=None, reason_code=invalid),)))
    fifth = _section(_render(frames=frames).report_md, S5)
    assert invalid in fifth                            # 红线清单
    assert '无留痕一律按未豁免处理' in fifth
    assert reason_codes.severity(expired) is Severity.BLOCK


def _case_l1296(row):
    '''实测依据：dsm/grading.py:323-324 cap_reason = RC.GR_CAPPED_NO_TARGET；
    dsm/models.py:1065-1066 ScoreCardRow.capped_flag / cap_reason 两列 = 契约第 5 列
    逐字；dsm/attainment.py:584/:625 RC.ATTAINMENT_CAPPED（attainment 层同族码，推定；
    AttainmentRow 无 reason_code 承载列，故本行不在该产物上断言，如实披露）。'''
    code = RC.GR_CAPPED_NO_TARGET.value
    frames = _frames(score_card=(_score_card_row(capped_flag=True, cap_reason=code),),
                     grade_ledger=(_ledger_row(),))
    report = _render(frames=frames)
    cells = _csv_row(report.score_card_csv)
    assert cells['capped_flag'] == 'true' and cells['cap_reason'] == code
    header = _csv_rows(report.score_card_csv)[0]
    assert 'capped_flag' in header and 'cap_reason' in header
    assert reason_codes.severity(RC.ATTAINMENT_CAPPED.value) is Severity.INFO


def _case_l1297(row):
    '''实测依据：dsm/normalize.py:111 CODE_INACTIVE = RC.INACTIVE_METRIC.value；
    dsm/entropy.py:187-196 status = INACTIVE + alerts 携同码；dsm/models.py:642
    EntropyStatus 闭集含 INACTIVE（契约第 3 列字面 INACTIVE 是**状态名**，不是码名）；
    dsm/reports.py:719-723 render_entropy_csv（契约第 5 列 entropy_diagnostic）与
    :609-621 ⑨段「建议动作原因码」列。码名 INACTIVE_METRIC 系语义推定。'''
    code = RC.INACTIVE_METRIC.value
    assert normalize.CODE_INACTIVE == code
    assert 'INACTIVE' in row.action
    diag = EntropyDiagnosticRow(metric_code='M-1', e_j=Decimal('1'),
                                d_j=Decimal('0'), cv_j=Decimal('0'),
                                status='INACTIVE', suggested_action=code,
                                owner='OWNER_X')
    report = _render(frames=_frames(entropy_diagnostics=(diag,)))
    assert code in report.entropy_diagnostic_csv
    assert 'INACTIVE' in report.entropy_diagnostic_csv
    assert code in _section(report.report_md, S9)


def _case_l1298(row):
    '''实测依据：dsm/preflight.py:54-55 DISCLOSURE 两码 = 报告首屏 = 契约第 5 列逐字；
    :391/:393 C-10 add；:395-396 act 的两条动作串逐字。两个码名均系语义推定。
    GAP-M28-1-01：dsm/reports.py 全文无「秩反转」/anchor 字面（grep 0 命中），
    ①首屏当前不渲染该串，披露经 finding/act -> audit.json + ⑩段。'''
    stale, reversal = RC.ANCHOR_SET_STALE.value, RC.RANK_REVERSAL_RISK.value
    assert preflight.DISCLOSURE[stale] == row.disclosure == '报告首屏'
    assert preflight.DISCLOSURE[reversal] == row.disclosure
    report = _render(
        findings=tuple(_finding('C-10', c, scope='anchor_set:ANCH-1',
                                detail='锚定集失效').to_audit_finding()
                       for c in (stale, reversal)),
        downgrades=(_act(stale, '回退为仅当期归一化', 'anchor_set:ANCH-1'),
                    _act(reversal, '报告首屏标注秩反转风险', 'anchor_set:ANCH-1')))
    tenth = _section(report.report_md, S10)
    assert stale in tenth and reversal in tenth
    assert '回退为仅当期归一化' in tenth
    assert '报告首屏标注秩反转风险' in tenth
    assert '披露=报告首屏' in tenth
    assert stale in report.audit_json and reversal in report.audit_json


def _case_l1299(row):
    '''实测依据：dsm/sensitivity.py:231-232 flip_rate 档位 -> (FLIP_RATE_REVIEW,
    NEAR_BOUNDARY) / (FLIP_RATE_UNUSABLE, UNSTABLE)；:575-586 veto() 只把 BLOCK 级
    flag 计为否决；dsm/reports.py:386-392 ①首屏 usable_for_elimination 与依据行；
    :547-580 ⑦段「稳健性非补偿否决已触发（…）」；:701-717 sensitivity_report.csv 的
    vetoed / usable_for_elimination 两列。两个码名均系语义推定。
    GAP-M28-1-02 / GAP-M28-1-03 见模块 docstring。'''
    review, unusable = RC.FLIP_RATE_REVIEW.value, RC.FLIP_RATE_UNUSABLE.value
    blocked = _render(frames=_frames(sensitivity=_sensitivity(flag=unusable,
                                                             label='UNSTABLE')))
    first = _section(blocked.report_md, S1)
    assert 'usable_for_elimination = false' in first    # 首屏必写（台账同名列）
    assert unusable in first                            # 首屏警示携码
    assert '稳健性非补偿否决已触发（' + unusable + '）' in _section(blocked.report_md, S7)
    cells = _csv_row(blocked.sensitivity_report_csv)
    assert cells['vetoed'] == 'true' and cells['usable_for_elimination'] == 'false'
    verdict = sensitivity.veto(_sensitivity(flag=unusable, label='UNSTABLE'))
    assert verdict.codes == (unusable,)
    assert verdict.usable_for_elimination is False
    # 实测 dsm/reports.py:270-274：①首屏的稳定性标签计数取自 frames.score_card 的
    # stability_label 列（不是 sensitivity.by_strategy），故两处都要给。
    reviewed = _render(frames=_frames(
        sensitivity=_sensitivity(flag=review, label='NEAR_BOUNDARY'),
        score_card=(_score_card_row(stability_label='NEAR_BOUNDARY'),)))
    assert ('NEAR_BOUNDARY 1 条：边界结论不得作为淘汰唯一依据'
            in _section(reviewed.report_md, S1))


def _case_l1300(row):
    '''实测依据：dsm/triangulation.py:61 RC_DIVERGENCE = RC.METHOD_DIVERGENCE.value；
    dsm/reports.py:266-268 ①首屏依据行「方法分歧：METHOD_DIVERGENCE」+ usable = false；
    :582-586 ⑧段判定行；:725-737 triangulation.md 同段正文。码名是契约字面。'''
    code = RC.METHOD_DIVERGENCE.value
    assert code in row.literal and code in row.action
    assert triangulation.RC_DIVERGENCE == code
    report = _render(frames=_frames(triangulation=_triangulation(agreement=code)))
    first = _section(report.report_md, S1)
    assert '方法分歧：' + code in first                 # 首屏警示
    assert 'usable_for_elimination = false' in first
    assert '- 判定：' + code in _section(report.report_md, S8)
    assert code in report.triangulation_md


def _case_l1301(row):
    '''实测依据：dsm/weights_combine.py:523/:786 与 dsm/weights_calibrate.py:737 的
    notices 携该码（契约第 2 列 weights_combine）；dsm/reports.py:627-629 ⑩段
    「降级动作全量」表是 ReportSet 内唯一的全量降级披露位。码名是契约字面
    （契约第 5 列逐字就是码名，与 [L1286] 同类缺陷）。
    口径限定：生产发射点在**权重草稿层**，不在 ReportSet 七件产物内；下面的断言只证明
    「该码一旦作为降级动作进入 audit_bundle，渲染层就会全量披露它」，端到端可达性依赖
    M29-1 / M29-2，本包不覆盖。'''
    code = RC.ENTROPY_INSUFFICIENT_SAMPLE.value
    assert code in row.literal and code == row.disclosure
    assert reason_codes.severity(code) is Severity.WARN      # 是（权重草稿）
    report = _render(downgrades=(_act(
        code, '回退纯 AHP（alpha = 1）+ 草稿首屏显著标注', 'weights_draft'),))
    tenth = _section(report.report_md, S10)
    assert code in tenth
    assert '回退纯 AHP（alpha = 1）+ 草稿首屏显著标注' in tenth


def _case_l1302(row):
    '''实测依据：dsm/weights_calibrate.py:157-168 AlphaInfeasibleError.reason_code =
    RC.ALPHA_INFEASIBLE.value 且携 violation_matrix（契约第 3 列「输出违反矩阵」）；
    dsm/cli.py:26-27 EXIT_ALPHA = 7、:57 (AlphaInfeasibleError, EXIT_ALPHA)、
    :141-148 exit_code_for；dsm/reports.py:645 ⑩段 exit_code 行。码名系语义推定。
    R-7 纪律：该码另有 dsm/weights_combine.py:84 的 H-1 残余发射源（ORCH-55 裁决保留，
    NG-V12-15，已由 tests/test_methods_combine.py:265/280/295/313/324 钉住），
    本行**只做正向断言**，不写任何排他断言。'''
    code = RC.ALPHA_INFEASIBLE.value
    matrix = {Decimal('0.500000000000'): (code, 'H2_DIM_WEIGHT_BELOW_FLOOR')}
    err = weights_calibrate.AlphaInfeasibleError('全部候选 alpha 均违反约束',
                                                violation_matrix=matrix)
    assert weights_calibrate.AlphaInfeasibleError.reason_code == code
    assert err.violation_matrix == matrix
    assert cli.EXIT_ALPHA == 7 and cli.exit_code_for(err) == 7
    assert 'exit_code=7' in _section(_render(exit_code=7).report_md, S10)
    assert reason_codes.severity(code) is Severity.BLOCK     # 否（无权重草稿）


def _case_l1303(row):
    '''实测依据：dsm/weights_calibrate.py:170-180 AlphaFloorInfeasibleError.reason_code
    = RC.ALPHA_FLOOR_INFEASIBLE.value；dsm/cli.py:58 (AlphaFloorInfeasibleError,
    EXIT_ALPHA) + :141-148 exit_code_for -> 7（契约第 5 列「退出码 7」）。码名系语义推定。
    GAP-M28-1-04（R-5）：[L1302] 与 [L1303] 共用退出码 7，而 dsm/cli.py:28-29
    _CODE_STATUS 把 7 固定映射为单标签 ALPHA_INFEASIBLE，故「本行报告披露含
    ALPHA_FLOOR_INFEASIBLE」现实现给不出 —— 本包**不写该断言**（写即必红），
    缺口交主控记入 KNOWN-GAPS；闭合需改 dsm/cli.py（M29-1 写集）。'''
    code = RC.ALPHA_FLOOR_INFEASIBLE.value
    err = weights_calibrate.AlphaFloorInfeasibleError(
        'alpha_floor 本身不可行，不静默降级',
        violation_matrix={Decimal('0.100000000000'): (code,)})
    assert weights_calibrate.AlphaFloorInfeasibleError.reason_code == code
    assert err.violation_matrix == {Decimal('0.100000000000'): (code,)}
    assert cli.exit_code_for(err) == cli.EXIT_ALPHA == 7
    assert 'exit_code=7' in _section(_render(exit_code=7).report_md, S10)
    assert reason_codes.severity(code) is Severity.BLOCK


def _case_l1304(row):
    '''实测依据：dsm/reports.py:53 CEL0 = 本期末接入增量估计（契约「末」字逐字，
    不是「未」）；:654-656 CEL0_COLUMNS 五列；:666-678 _score_card_cells 在 CEL 空值时
    逐列写明该串（契约第 3 列「不得静默留白」）。
    职责划界（主控裁定）：本行**端到端**面归在飞包 CEL-EQ
    （tests/test_cel_disabled_fieldwise.py），本包只断言该字面串存在且被渲染进产物，
    不断言 CEL 端到端行为。本行是 26 行中唯一契约不挂 reason_code 的行。'''
    assert reports.CEL0 == '本期末接入增量估计'
    assert reports.CEL0 in row.action
    assert row.codes == ()
    report = _render(frames=_frames(score_card=(_score_card_row(),)))
    cells = _csv_row(report.score_card_csv)
    for column in reports.CEL0_COLUMNS:
        assert cells[column] == reports.CEL0           # 五列一律写明，不留白


def _case_l1305(row):
    '''实测依据：dsm/cli.py:26 EXIT_INTERNAL = 5、:141-148 exit_code_for 的兜底分支
    return EXIT_INTERNAL（契约第 3 列「退出码 5」）；dsm/whatif.py:100/:104
    RC.INVARIANT_VIOLATION.value 是不变量违反的注册码；dsm/preflight.py:404-412
    build_audit_bundle 的 output_fingerprints = {} 即「不产出任何结果」；
    dsm/reports.py:645 ⑩段 exit_code 行 + :738-742 audit.json。码名系语义推定。'''
    code = RC.INVARIANT_VIOLATION.value
    assert reason_codes.severity(code) is Severity.BLOCK
    assert cli.EXIT_INTERNAL == 5
    assert cli.exit_code_for(TypeError('内部不变量违反')) == cli.EXIT_INTERNAL
    report, bundle = _render_pair(exit_code=cli.EXIT_INTERNAL, outputs={})
    assert 'exit_code=5' in _section(report.report_md, S10)
    assert bundle.output_fingerprints == {}            # 不产出任何结果
    assert bundle.exit_code == cli.EXIT_INTERNAL == 5
    assert 's:exit_code=i5' in report.audit_json       # canonical_text 的整数口径


CASES = {
    'L1280': _case_l1280, 'L1281': _case_l1281, 'L1282': _case_l1282,
    'L1283': _case_l1283, 'L1284': _case_l1284, 'L1285': _case_l1285,
    'L1286': _case_l1286, 'L1287': _case_l1287, 'L1288': _case_l1288,
    'L1289': _case_l1289, 'L1290': _case_l1290, 'L1291': _case_l1291,
    'L1292': _case_l1292, 'L1293': _case_l1293, 'L1294': _case_l1294,
    'L1295': _case_l1295, 'L1296': _case_l1296, 'L1297': _case_l1297,
    'L1298': _case_l1298, 'L1299': _case_l1299, 'L1300': _case_l1300,
    'L1301': _case_l1301, 'L1302': _case_l1302, 'L1303': _case_l1303,
    'L1304': _case_l1304, 'L1305': _case_l1305,
}


# --------------------------------------------------------------------- 参数化裁判
def test_matrix_is_26_rows_by_5_columns_verbatim():
    '''形状实测（ERRATUM-V12-05）：26 行 × 5 列，列名逐字取自契约 [L1278] 表头，
    行号连续覆盖 [L1280]-[L1305]，且每行都有专属裁判函数（一行不漏）。'''
    assert len(HEADER) == 5
    assert HEADER == ('情形', '检测点', '降级动作', '是否出分', '披露位置')
    assert len(MATRIX) == ROW_COUNT == 26
    assert ([int(row.line[1:]) for row in MATRIX]
            == list(range(FIRST_LINE, LAST_LINE + 1)))
    assert len(CASES) == 26
    for row in MATRIX:
        assert len(row.cells) == 5
        assert all(cell.strip() for cell in row.cells)      # 无空单元格
        assert len(row.codes) == len(row.severities)
        assert row.line in CASES


@pytest.mark.parametrize('row', MATRIX, ids=[row.line for row in MATRIX])
def test_row_is_disclosed_through_its_own_channel(row):
    '''26 行逐行裁判：每行只按它**自己的**披露通道断言（R-2：13 行的码不在
    dsm/preflight.py:48-63 DISCLOSURE 表内，不得一刀切要求进 report.md ⑩段）。'''
    CASES[row.line](row)


@pytest.mark.parametrize('row', MATRIX, ids=[row.line for row in MATRIX])
def test_row_codes_are_registered_and_match_the_scored_column(row):
    '''契约第 4 列「是否出分」与注册表 severity 的一致性：不出分的行必须是 BLOCK 级；
    其余行按实测逐码钉住 severity（含 [L1286] 的「视情况」＝ WARN + BLOCK 并存）。
    另断言 literal 里的码名确实在契约该行原文（第 3 或第 5 列）里逐字出现，
    以区分「契约字面码」与「M28-PRE 语义推定码」（R-12）。'''
    for name, expected in zip(row.codes, row.severities):
        assert reason_codes.is_registered(name) is True
        assert reason_codes.severity(name).value == expected
    for name in row.literal:
        assert name in row.codes
        assert name in row.action + row.disclosure
    if row.scored.startswith('否'):
        assert {reason_codes.severity(c).value for c in row.codes} == {'BLOCK'}
    if row.line == 'L1286':
        assert ({reason_codes.severity(c).value for c in row.codes}
                == {'WARN', 'BLOCK'})
