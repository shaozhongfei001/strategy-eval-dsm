'''tests/test_reports.py -- G-14：report.md 十段结构与顺序、grade_ledger 建议/决定分列、
审计包与 audit.py 对齐、G5/G7 未签认时的首屏口径、V-14 不静默省略、V-9 数值口径。
输入一律按 R-2 用 pydantic 构造，产物一律写 tmp_path（R-3）。'''
from datetime import date, datetime, timezone
import csv
from decimal import Decimal

import pytest

from dsm import audit
from dsm.audit import RunContext
from dsm.models import (
    AttainmentFrame, AttainmentRow, DowngradeAction, EntropyDiagnosticRow,
    EvidenceFrame, EvidenceRow, GradeLedgerRow, InputTableFingerprint,
    PoolFrame, PoolKey, PoolRow, PoolStatRow, PoolStats, PreflightFinding,
    ScoreCardDimCell, ScoreCardMetricCell, ScoreCardRow, ScoreFrame, ScoreRow,
    SensitivityReport, SensitivitySchemeResult, SensitivityStrategyRow,
    TriangulationReport, TriangulationStrategyRow)
from dsm.numeric import NonIntegerAmountError
from dsm.reason_codes import Severity
from dsm.reports import (
    ARTIFACT_NAMES, CEL0, GATE_STATEMENT, GRADE_LEDGER_COLUMNS, NO_DATA,
    OPEN_PARAMETER_IDS, REPORT_SECTIONS, SCORE_CARD_COLUMNS, AllFrames,
    GateStatus, ReportError, assert_report_sections, fmt_int, fmt_ratio, ledger_missing_items,
    PLACEHOLDER, render, render_grade_ledger_csv, render_score_card_csv,
    section_titles, split_sections, write_report_set)

RUN_AT = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
HEX64 = 'ab' * 32
PERIOD = '2026Q1'


def _score_card_row(**over):
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
    base = dict(strategy_id='S-001', version_id='V-1', period=PERIOD,
                grade='L2', recommended_action='ADV-A', decided_action='ADV-A',
                ledger_complete=False, usable_for_elimination=True)
    base.update(over)
    return GradeLedgerRow(**base)


def _scheme_result(flag=None, rate='0.1'):
    return SensitivitySchemeResult(
        scheme='OAT_10', overall_flip_rate=Decimal(rate), flipped_count=1,
        assessed_count=10, flag=flag)


def _sensitivity(flag=None):
    return SensitivityReport(
        by_scheme=(_scheme_result(flag),),
        by_strategy=(SensitivityStrategyRow(
            strategy_id='S-001', version_id='V-1', stability_label='STABLE',
            flip_under_pct10=Decimal('0'), flip_under_pct20=Decimal('0')),),
        loo_dominant_metrics=('M-1',),
        norm_swap_rank_correlation=Decimal('1'), flags=(), seed=7)


def _triangulation(agreement='METHOD_AGREEMENT'):
    return TriangulationReport(
        rows=(TriangulationStrategyRow(
            strategy_id='S-001', version_id='V-1', topsis_rank=1, gra_rank=2),),
        rho_main_topsis=Decimal('0.9'), rho_main_gra=Decimal('0.8'),
        rho_topsis_gra=Decimal('0.95'), mean_rho=Decimal('0.88'),
        agreement=agreement, gra_by_metric={'M-1': Decimal('0.7')}, flags=())


def _pool_key(class_="B"):
    return PoolKey(biz_domain='CARD', evidence_class=class_)


def _frames(**over):
    pool_stats = PoolStats(
        rows=(PoolStatRow(pool_key=_pool_key(), count=2,
                          share_in_pool=Decimal('0.2'),
                          share_overall=Decimal('0.1')),),
        evidence_structure={'A': 1, 'B': 2, 'C': 0, 'D': 1},
        not_assessed_count=1, not_assessed_reasons={'NOT_ASSESSED': 1})
    base = dict(
        gate_status=GateStatus(g5_dispute_source_review_signed=True,
                               g7_governance_config_signed=True),
        attainment=AttainmentFrame(
            rows=(AttainmentRow(
                strategy_id='S-001', version_id='V-1', period=PERIOD,
                metric_id='M-2', direction=1, has_target=False,
                capped_flag=False),),
            attainment_coverage={'S-001': Decimal('0.5')}),
        evidence=EvidenceFrame(rows=(EvidenceRow(
            strategy_id='S-001', version_id='V-1', evidence_class='D',
            evidence_reason='EV_D_NOT_ASSESSED',
            evidence_source='CARD_ONLY'),),),
        redline=None, score=ScoreFrame(rows=(ScoreRow(
            strategy_id='S-001', version_id='V-1', period=PERIOD,
            dim_absolute={'DIM-1': Decimal('1.25')},
            dim_relative={'DIM-1': Decimal('0.5')}, coverage=Decimal('0.5'),
            weight_version_id='WV-1', operator='LINEAR'),),),
        pool=PoolFrame(rows=(PoolRow(
            strategy_id='S-001', version_id='V-1', period=PERIOD,
            pool_key=_pool_key(), pool_rank=3, primary_pool_eligible=False,
            reject_reason='PRIMARY_POOL_REJECTED_EVIDENCE'),),),
        pool_stats=pool_stats, sensitivity=_sensitivity(),
        triangulation=_triangulation(),
        entropy_diagnostics=(EntropyDiagnosticRow(
            metric_code='M-1', e_j=Decimal('0.5'), d_j=Decimal('0.5'),
            cv_j=Decimal('0.1'), status='LOW_VARIATION',
            suggested_action='LOW_VARIATION', owner='OWNER_X', flags=()),),
        score_card=(_score_card_row(),),
        grade_ledger=(_ledger_row(),), weight_provenance=None)
    base.update(over)
    return AllFrames(**base)


def _empty_frames(**over):
    base = {name: None for name in AllFrames.model_fields
            if name != 'gate_status'}
    base['gate_status'] = GateStatus(g5_dispute_source_review_signed=False,
                                     g7_governance_config_signed=False)
    base.update(over)
    return AllFrames(**base)


def _bundle(frames, findings=(), downgrades=()):
    rows = frames.score_card or ()
    ledger_rows = frames.grade_ledger or ()
    ctx = RunContext(
        run_id='RUN-1', run_at=RUN_AT, period=PERIOD, dsm_version='1.1.0',
        design_version='DSM-v1.1', cel_contract_version='CEL-0',
        weight_version_id='WV-1', seed=7, sensitivity_schemes=('OAT_10',),
        preflight_findings=findings, downgrade_actions=downgrades, exit_code=0,
        score_card=rows, grade_ledger=ledger_rows)
    inputs = {'T1': InputTableFingerprint(sha256=HEX64, row_count=3)}
    outputs = {name: HEX64 for name in ARTIFACT_NAMES}
    return audit.build_manifest(inputs, 'eval_config: {}', ctx, outputs)


WARN_FINDING = PreflightFinding(code='C-01', severity=Severity.WARN,
                                message='FINDING_TEXT')
BLOCK_FINDING = PreflightFinding(code='C-02', severity=Severity.BLOCK,
                                 message='BLOCKED_TEXT')
DOWNGRADE = DowngradeAction(reason_code='ENTROPY_INACTIVE_FALLBACK',
                            action='DOWNGRADE_TEXT', subject='S-001')


def _render(frames=None, findings=(), downgrades=(), config=None):
    frames = frames if frames is not None else _frames()
    return render(_bundle(frames, findings, downgrades), frames, config)


# ---- G-14：十段齐全且顺序固定 -------------------------------------------------
def test_report_has_ten_sections_in_fixed_order():
    text = _render().report_md
    assert section_titles(text) == REPORT_SECTIONS
    assert len(REPORT_SECTIONS) == 10
    assert assert_report_sections(text) == REPORT_SECTIONS
    for title in ('①首屏结论与可用性声明', '③等级分布与占比双报',
                  '⑧方法三角一致性'):
        assert title in text


def test_missing_or_reordered_section_is_rejected():
    text = _render().report_md
    dropped = text.replace('## ' + REPORT_SECTIONS[6], '## X')
    with pytest.raises(ReportError):
        assert_report_sections(dropped)
    blocks = split_sections(text)
    swapped = ('## ' + REPORT_SECTIONS[1] + '\n' + blocks[REPORT_SECTIONS[1]]
               + '\n## ' + REPORT_SECTIONS[0] + '\n'
               + blocks[REPORT_SECTIONS[0]])
    with pytest.raises(ReportError):
        assert_report_sections(swapped)
    with pytest.raises(ReportError):
        assert_report_sections('')


def test_first_screen_declares_usable_for_elimination_with_basis():
    body = split_sections(_render().report_md)[REPORT_SECTIONS[0]]
    assert 'usable_for_elimination = true' in body
    assert '- 依据：' in body


# ---- 门禁未通过：首屏口径 + PLACEHOLDER ---------------------------------------
def test_gate_not_passed_puts_statement_on_first_screen():
    text = _render(_frames(gate_status=GateStatus(
        g5_dispute_source_review_signed=False,
        g7_governance_config_signed=True))).report_md
    assert GATE_STATEMENT in text
    assert text.index(GATE_STATEMENT) < text.index('## ' + REPORT_SECTIONS[1])
    assert '合成数据' in GATE_STATEMENT and '不得' in GATE_STATEMENT
    assert 'G5/G7 门禁未签认' in split_sections(text)[REPORT_SECTIONS[0]]


def test_gate_not_passed_blocks_elimination_and_keeps_placeholder():
    text = _render(_frames(gate_status=GateStatus(
        g5_dispute_source_review_signed=False,
        g7_governance_config_signed=False))).report_md
    blocks = split_sections(text)
    assert 'usable_for_elimination = false' in blocks[REPORT_SECTIONS[0]]
    assert '合成数据' in blocks[REPORT_SECTIONS[0]] and '不得据此配置真实资源' in blocks[REPORT_SECTIONS[0]]
    assert PLACEHOLDER in blocks[REPORT_SECTIONS[6]]
    assert PLACEHOLDER in blocks[REPORT_SECTIONS[9]]


def test_open_parameters_are_placeholder_and_no_invented_business_value():
    body = split_sections(_render(
        _empty_frames(gate_status=GateStatus(
            g5_dispute_source_review_signed=False,
            g7_governance_config_signed=False))).report_md)[REPORT_SECTIONS[9]]
    assert len(OPEN_PARAMETER_IDS) == 20
    for key in OPEN_PARAMETER_IDS:
        assert '| ' + key + ' | ' + PLACEHOLDER + ' |' in body


# ---- V-14：不得静默省略 --------------------------------------------------------
def test_every_section_survives_absent_upstream():
    text = _render(_empty_frames()).report_md
    blocks = split_sections(text)
    assert section_titles(text) == REPORT_SECTIONS
    for title in REPORT_SECTIONS:
        assert NO_DATA in blocks[title], title
        assert 'NOT_ASSESSED' in blocks[title], title


# ---- recommended_action 与 decided_action 分两列 -------------------------------
def test_recommended_and_decided_are_two_independent_columns():
    header = next(csv.reader([render_grade_ledger_csv(()).splitlines()[0]]))
    assert 'recommended_action' in header and 'decided_action' in header
    assert header.count('recommended_action') == 1
    assert header.count('decided_action') == 1
    rows = (_ledger_row(recommended_action='ADV-A', decided_action=None),
            _ledger_row(strategy_id='S-002', recommended_action=None,
                        decided_action='DEC-B'),
            _ledger_row(strategy_id='S-003', recommended_action=None,
                        decided_action=None))
    table = list(csv.reader(render_grade_ledger_csv(rows).splitlines()))[1:]
    idx_rec = header.index('recommended_action')
    idx_dec = header.index('decided_action')
    assert [row[idx_rec] for row in table] == ['ADV-A', 'null', 'null']
    assert [row[idx_dec] for row in table] == ['null', 'DEC-B', 'null']
    assert len(table[0]) == len(header)


def test_disagreement_needs_a_separate_decision_note():
    disagree = _ledger_row(recommended_action='ADV-A', decided_action='DEC-B')
    assert 'decision_note' in ledger_missing_items(disagree)
    assert 'decision_note' not in ledger_missing_items(
        _ledger_row(recommended_action='ADV-A', decided_action='DEC-B',
                    decision_note='NOTE'))
    assert 'decision_note' not in ledger_missing_items(
        _ledger_row(recommended_action='ADV-A', decided_action='ADV-A'))
    body = split_sections(_render(_frames(
        grade_ledger=(_ledger_row(grade='L2', recommended_action='ADV-A',
                                  decided_action='DEC-B'),))).report_md
        )[REPORT_SECTIONS[9]]
    assert '台账不完整' in body and 'decision_note' in body


def test_l3_needs_owner_and_deadline_l4_needs_archive_ref():
    l3 = _ledger_row(grade='L3')
    assert ledger_missing_items(l3) == ('owner_dept', 'owner_name', 'deadline')
    assert ledger_missing_items(_ledger_row(grade='L4')) == ('archive_ref',)
    assert ledger_missing_items(_ledger_row(
        grade='L3', owner_dept='DEPT_X', owner_name='PERSON_X',
        deadline=date(2026, 3, 31))) == ()


# ---- score_card 各段与数值口径 -------------------------------------------------
def test_score_card_columns_cover_every_segment():
    header = render_score_card_csv(()).split('\n')[0].split(',')
    assert SCORE_CARD_COLUMNS == tuple(ScoreCardRow.model_fields)
    for column in ('weight_version_id', 'dict_version', 'anchor_set_id', 'run_id',
                   'per_metric', 'per_dim', 'composite_absolute',
                   'composite_relative', 'evidence_class', 'evidence_reason',
                   'interpretation_limit', 'redline_pass', 'redline_flags',
                   'grade', 'grade_reason_codes', 'capped_flag', 'cap_reason',
                   'ranking_pool', 'rank_in_pool', 'pool_size',
                   'eligible_for_L1_library', 'l1_gate_reasons',
                   'stability_label', 'flip_under_pct10', 'flip_under_pct20',
                   'usable_for_elimination', 'incremental_value', 'value_captured_minor'):
        assert column in header, column


def test_cel0_columns_are_never_silently_blank():
    line = render_score_card_csv((_score_card_row(),)).split('\n')[1]
    assert CEL0 in line
    filled = render_score_card_csv((_score_card_row(
        incremental_value=Decimal('1'), estimator_method='DID'),),)
    assert '本期末接入增量估计' not in filled
    assert 'DID' in filled


def test_money_and_counts_are_exact_ints_ratios_are_decimal():
    text = render_score_card_csv((_score_card_row(
        value_captured_minor=12345, incremental_value=Decimal('1'),
        estimator_method='DID'),),)
    header = next(csv.reader([text.splitlines()[0]]))
    cells = next(csv.reader([text.splitlines()[1]]))
    assert cells[header.index('value_captured_minor')] == '12345'
    assert cells[header.index('composite_absolute')] == '1.020000000000'
    assert cells[header.index('pool_size')] == 'null'
    assert fmt_ratio(Decimal('0.3333333333333')) == '0.333333333333'
    assert fmt_int(7) == '7'
    with pytest.raises(NonIntegerAmountError):
        fmt_int(Decimal('1.5'))


# ---- 审计包与 audit.py 对齐 ---------------------------------------------------
def test_audit_json_is_exactly_the_serialized_bundle():
    frames = _frames()
    bundle = _bundle(frames)
    report = render(bundle, frames)
    assert report.audit_json == audit.serialize_bundle(bundle)
    body = split_sections(report.report_md)[REPORT_SECTIONS[9]]
    assert bundle.reproducibility_hash in body
    for step in audit.rerun_steps(bundle):
        assert step in body


def test_write_report_set_writes_all_artifacts_with_audit_fingerprints(tmp_path):
    report = _render()
    prints = write_report_set(report, tmp_path)
    assert sorted(prints) == sorted(ARTIFACT_NAMES)
    for name, digest in prints.items():
        assert len(digest) == 64 and name not in digest
        raw = (tmp_path / name).read_bytes()
        assert not raw.startswith(b'\xef\xbb\xbf') and b'\r' not in raw
    assert (tmp_path / 'audit.json').read_text('utf-8') == report.audit_json
    assert audit.check_sha256(prints['report.md'], 'report.md')


# ---- 稳健性：veto 与 usable_for_elimination 的报告列 ---------------------------
def test_sensitivity_veto_has_report_columns():
    frames = _frames(sensitivity=_sensitivity(flag='FLIP_RATE_UNUSABLE'))
    report = render(_bundle(frames), frames)
    body = split_sections(report.report_md)[REPORT_SECTIONS[6]]
    assert 'usable_for_elimination' in body and '非补偿否决' in body
    assert 'false' in body and 'FLIP_RATE_UNUSABLE' in body
    header = report.sensitivity_report_csv.split('\n')[0]
    assert 'vetoed' in header and 'usable_for_elimination' in header
    assert 'false' in report.sensitivity_report_csv.split('\n')[1]


def test_grade_distribution_and_evidence_structure_are_double_reported():
    blocks = split_sections(_render().report_md)
    third = blocks[REPORT_SECTIONS[2]]
    assert '池内占比' in third and '全局占比' in third and '占已出分比' in third
    sixth = blocks[REPORT_SECTIONS[5]]
    for class_ in ('A', 'B', 'C', 'D'):
        assert '| ' + class_ + ' |' in sixth
    assert 'NOT_ASSESSED 计数（单独计数' in sixth and 'EV_D_NOT_ASSESSED' in sixth