'''tests for dsm/io_loaders (S3-T01): CSV / Parquet loading, type forcing, the
[L888] input fingerprints and the [L890] previous-period ledger. Guard: G-12
(same inputs twice -> identical output). Also closes ops/blockers.md B-008 (a
MONEY_MINOR column must become an exact int, C-09 on failure) and B-010 (text
literals convert only through the explicit table, never to False / 0).
'''
from __future__ import annotations

from decimal import Decimal

import pytest

from dsm import io_loaders as L
from dsm.io_loaders import CoercionError, DataLoadError, cell_to_text, coerce, load_table
from dsm.models import StrategyMasterRow
from dsm.numeric import D, eq_exact, eq_tol
from dsm.reason_codes import RC

DICT_HEADER = ('metric_id', 'metric_name', 'dim_code', 'numerator_def', 'denominator_def',
               'time_window', 'dedup_rule', 'missing_rule', 'outlier_rule', 'attainment_formula',
               'direction', 'unit', 'target_value', 'target_basis', 'is_redline', 'owner_name',
               'signoff_status', 'signoff_date', 'dim_signoff_status', 'dict_version',
               'caliber_version')
FACT_HEADER = ('strategy_id', 'version_id', 'period', 'metric_id', 'value_num', 'value_den',
               'value', 'data_quality_flag', 'snapshot_time', 'data_as_of', 'source_table',
               'caliber_version')
MASTER_HEADER = ('strategy_id', 'version_id', 'strategy_name', 'biz_domain', 'scene_code',
                 'segment_type', 'online_date', 'offline_date', 'owner_dept', 'owner_name',
                 'status', 'version_change_note')
CARD_HEADER = ('strategy_id', 'version_id', 'direct_goal', 'process_metrics', 'result_metrics',
               'observation_window', 'data_source', 'data_timeliness', 'eval_method',
               'control_arrangement', 'success_criteria', 'risk_constraints', 'eval_owner',
               'alt_method_note', 'interpretation_limit', 'card_status', 'mde_ok')
REDLINE_HEADER = ('metric_id', 'level', 'comparator', 'threshold_value', 'forced_grade',
                  'reason_code', 'waiver_allowed')
LEDGER_HEADER = ('strategy_id', 'version_id', 'period', 'grade', 'previous_grade',
                 'recommended_action', 'decided_action', 'decision_note', 'owner_dept',
                 'owner_name', 'deadline', 'archive_ref', 'ledger_complete',
                 'usable_for_elimination')

DICT_ROWS = (
    ('M_ONE', '投放金额', 'MONEY', 'sum(cost)', '', 'MONTH', 'DEV', 'ZERO', 'CLIP_P1_P99',
     'RATIO_DIRECT', '1', 'MONEY_MINOR', '100000', 'budget', 'true', '张三', 'SIGNED',
     '2026-01-05', 'SIGNED', 'v1', 'c1'),
    ('M_RATE', '转化率', 'EFF', 'conv', 'reach', 'MONTH', 'DEV', 'SKIP', 'CLIP_P1_P99',
     'INVERSE_RATIO', '-1', 'RATIO', '0.35', 'history', 'no', '李四', 'PENDING', '', 'SIGNED',
     'v1', 'c1'),
    ('M_DUR', '时长', 'EFF', 'sec', '', 'MONTH', 'DEV', 'BLOCK', 'NONE', 'INTERVAL', '1',
     'DURATION_SEC', '', 'benchmark', '0', '王五', 'PENDING', '', 'SIGNED', 'v1', 'c1'),
)
FACT_ROWS = (
    ('S1', 'V1', '2026Q1', 'M_ONE', '120000', '', '120000', 'OK', '2026-04-01T10:00:00',
     '2026-03-31', 't_fact', 'c1'),
    ('S1', 'V1', '2026Q1', 'M_RATE', '30', '100', '0.3', 'OK', '2026-04-01T10:00:00',
     '2026-03-31', 't_fact', 'c1'),
    ('S2', 'V1', '2026Q1', 'M_ONE', '150000', '', '150000', 'PARTIAL', '2026-04-01 10:00:00',
     '2026-03-31', 't_fact', 'c1'),
)
MASTER_ROWS = (
    ('S1', 'V1', '春季营销', '零售', 'SC1', 'EXISTING', '2026-01-01', '', '零售部', '赵六',
     'ACTIVE', ''),
    ('S2', 'V1', '夏季营销', '对公', 'SC2', 'NEW', '2026-01-02', '2026-03-31', '对公部', '孙七',
     'PAUSED', 'first'),
)
CARD_ROWS = (('S1', 'V1', 'g1', 'pm1, pm2', 'rm1', '30D', 'dw', 'T1D', 'HOLDOUT',
              'CONCURRENT_CONTROL', 'sc', 'rc', 'owner', '', '', 'COMPLETE', 'yes'),)
REDLINE_ROWS = (('M_ONE', 'HARD', 'GT', '200000', 'L4', 'REDLINE_HARD_HIT', 'false'),)


def _write(path, header, rows):
    '''csv.writer rather than a join, so a list cell such as pm1 , pm2 stays
    inside its own quoted field.'''
    import csv
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle, lineterminator=chr(10))
        writer.writerow(header)
        writer.writerows(rows)
    return path


def _root(tmp_path, facts=FACT_ROWS, master=MASTER_ROWS, cards=CARD_ROWS,
          redlines=REDLINE_ROWS, dictionary=DICT_ROWS, period='2026Q1'):
    data, conf = tmp_path / 'data', tmp_path / 'config'
    _write(data / period / 'metric_facts.csv', FACT_HEADER, facts)
    _write(data / period / 'strategy_master.csv', MASTER_HEADER, master)
    if cards is not None:
        _write(data / period / 'design_cards.csv', CARD_HEADER, cards)
    _write(conf / 'metric_dict.csv', DICT_HEADER, dictionary)
    if redlines is not None:
        _write(conf / 'redlines.csv', REDLINE_HEADER, redlines)
    return data, conf


def test_load_inputs_happy_path(tmp_path):
    data, conf = _root(tmp_path)
    result = L.load_inputs(data, '2026Q1', conf)
    assert len(result.inputs.strategy_master) == 2  # [L1112]
    assert len(result.inputs.metric_dict) == 3  # [L1126]
    assert len(result.inputs.metric_facts) == 3  # [L1145]
    assert len(result.inputs.design_cards) == 1 and len(result.inputs.redlines) == 1
    assert sorted(result.fingerprints) == ['design_cards.csv', 'metric_dict.csv',
                                          'metric_facts.csv', 'redlines.csv',
                                          'strategy_master.csv']  # [L888]
    assert result.inputs.previous_ledger == ()
    codes = [issue.code for issue in result.issues]
    assert codes == [RC.FIRST_PERIOD.value]  # [L890]


def test_money_minor_becomes_exact_int(tmp_path):
    data, conf = _root(tmp_path)
    facts = L.load_inputs(data, '2026Q1', conf).inputs.metric_facts
    money = [row for row in facts if row.metric_id == 'M_ONE']
    for row in money:  # B-008 / [L889]: int, never Decimal, never truncated
        assert type(row.value) is int and type(row.value_num) is int
    assert money[0].value == 120000 and money[1].value == 150000
    rate = [row for row in facts if row.metric_id == 'M_RATE'][0]
    assert isinstance(rate.value, Decimal) and eq_exact(rate.value, D('0.3'))  # V-9
    assert rate.value_den == 100 or eq_tol(rate.value_den, D('100'))
    card = L.load_inputs(data, '2026Q1', conf).inputs.design_cards[0]
    assert card.process_metrics == ('pm1', 'pm2') and card.mde_ok is True  # [L1163], [L1174]


def test_money_minor_fraction_records_c09(tmp_path):
    data, conf = _root(tmp_path, facts=(('S1', 'V1', '2026Q1', 'M_ONE', '100.50', '', '100.50',
                                        'OK', '2026-04-01T10:00:00', '2026-03-31', 't', 'c1'),))
    with pytest.raises(DataLoadError) as caught:
        L.load_inputs(data, '2026Q1', conf)
    issues = [i for i in caught.value.issues if i.kind == 'MONEY_NOT_INTEGER']
    assert len(issues) == 2  # value_num and value, both refused
    assert {i.code for i in issues} == {RC.MONEY_NON_INTEGER.value}  # C-09
    assert '100.50' in issues[0].message  # the cell is reported, not truncated to 100
    assert issues[0].table == 'metric_facts' and issues[0].row == 1
    assert caught.value.exit_code == 4  # [L892]


def test_money_minor_count_unit_and_target_follow_the_unit_column(tmp_path):
    data, conf = _root(tmp_path)
    rows = {row.metric_id: row for row in L.load_inputs(data, '2026Q1', conf).inputs.metric_dict}
    assert type(rows['M_ONE'].target_value) is int and rows['M_ONE'].target_value == 100000
    assert isinstance(rows['M_RATE'].target_value, Decimal)
    assert rows['M_DUR'].direction == 1 and rows['M_RATE'].direction == -1  # [L1137]


def test_bool_literal_table_is_explicit_and_auditable():
    # B-010: these literals, and only these, convert.
    assert L.TRUE_LITERALS and L.FALSE_LITERALS
    for text in L.TRUE_LITERALS:
        assert coerce('bool', text, 'x') is True
    for text in L.FALSE_LITERALS:
        assert coerce('bool', text, 'x') is False
    assert coerce('bool', '  TRUE ', 'x') is True and coerce('bool', 'Y', 'x') is True
    for junk in ('2', '1.0', 'yep', 'yes-no', 'tru', 'enabled', '-', '00', 'TRUE2', ''):
        with pytest.raises(CoercionError) as caught:
            coerce('bool', junk, 'x')
        assert caught.value.kind == 'UNRECOGNIZED_LITERAL'


def test_unrecognized_bool_literal_is_an_error_not_false(tmp_path):
    bad = list(DICT_ROWS[0])
    bad[14] = 'maybe'  # is_redline
    data, conf = _root(tmp_path, dictionary=(tuple(bad),))
    with pytest.raises(DataLoadError) as caught:
        L.load_inputs(data, '2026Q1', conf)
    issues = [i for i in caught.value.issues if i.kind == 'UNRECOGNIZED_LITERAL']
    assert len(issues) == 1 and issues[0].column == 'is_redline'  # B-010
    assert 'maybe' in issues[0].message and 'False' not in issues[0].message
    with pytest.raises(CoercionError):  # no silent default anywhere either
        coerce('bool', 'maybe', 'x')


def test_null_cells_stay_null(tmp_path):
    data, conf = _root(tmp_path)
    loaded = L.load_inputs(data, '2026Q1', conf)
    master = {row.strategy_id: row for row in loaded.inputs.strategy_master}
    assert master['S1'].offline_date is None and master['S2'].offline_date.year == 2026
    assert master['S1'].version_change_note is None  # empty is absent, not ''
    dicts = {row.metric_id: row for row in loaded.inputs.metric_dict}
    assert dicts['M_DUR'].target_value is None  # [L1139] absent, not zero
    assert dicts['M_ONE'].denominator_def is None
    assert dicts['M_DUR'].outlier_rule == 'NONE'  # a literal, not an absent cell
    fact = loaded.inputs.metric_facts[0]
    assert fact.value_den is None and fact.data_as_of.month == 3


def test_non_iso_date_is_refused(tmp_path):
    bad = list(MASTER_ROWS[0])
    bad[6] = chr(48) + '5/01/2026'  # [L889] ISO only, not day-first
    data, conf = _root(tmp_path, master=(tuple(bad), MASTER_ROWS[1]))
    with pytest.raises(DataLoadError) as caught:
        L.load_inputs(data, '2026Q1', conf)
    kinds = [i.kind for i in caught.value.issues]
    assert 'NON_ISO_DATE' in kinds  # [L889] dates must be ISO


def test_closed_literal_column_is_closed_by_the_model(tmp_path):
    bad = list(MASTER_ROWS[0])
    bad[10] = 'ON'  # status is not in [L1123]
    data, conf = _root(tmp_path, master=(tuple(bad),))
    with pytest.raises(DataLoadError) as caught:
        L.load_inputs(data, '2026Q1', conf)
    issue = caught.value.issues[0]
    assert issue.kind == 'MODEL_ROW_REJECTED' and StrategyMasterRow.__name__ in issue.message


def test_missing_required_file_is_a_load_error(tmp_path):
    data, conf = tmp_path / 'data', tmp_path / 'config'
    conf.mkdir(parents=True)
    (data / '2026Q1').mkdir(parents=True)
    with pytest.raises(DataLoadError) as caught:
        L.load_inputs(data, '2026Q1', conf)
    kinds = [i.kind for i in caught.value.issues]
    assert kinds.count('MISSING_FILE') == 3  # T1 / T2 / T3 are required [L888]
    assert caught.value.exit_code == 4


def test_fingerprints_are_sha256_and_row_count(tmp_path):
    import hashlib
    data, conf = _root(tmp_path)
    loaded = L.load_inputs(data, '2026Q1', conf)
    facts = data / '2026Q1' / 'metric_facts.csv'
    entry = loaded.fingerprints['metric_facts.csv']
    assert entry.sha256 == hashlib.sha256(facts.read_bytes()).hexdigest()  # [L888]
    assert len(entry.sha256) == 64 and type(entry.row_count) is int
    assert entry.row_count == 3  # header line is not a data row
    with open(facts, 'a', encoding='utf-8', newline='') as handle:
        handle.write(','.join(('S3', 'V1', '2026Q1', 'M_ONE', '1', '', '1', 'OK',
                               '2026-04-01T10:00:00', '2026-03-31', 't', 'c1')) + chr(10))
    after = L.load_inputs(data, '2026Q1', conf).fingerprints['metric_facts.csv']
    assert after.row_count == 4 and after.sha256 != entry.sha256


def test_repeat_load_is_identical_guard_g12(tmp_path):
    # G-12 at the L1 boundary: the same bytes, loaded twice, fingerprint the the
    # same and type to the same values, in the same map order.
    data, conf = _root(tmp_path)
    first, second = (L.load_inputs(data, '2026Q1', conf) for _ in range(2))
    assert list(first.fingerprints) == list(second.fingerprints)
    assert first.fingerprints == second.fingerprints
    for name, entry in first.fingerprints.items():
        assert entry == second.fingerprints[name], name
    left = {row.metric_id + row.strategy_id: row for row in first.inputs.metric_facts}
    right = {row.metric_id + row.strategy_id: row for row in second.inputs.metric_facts}
    assert set(left) == set(right)
    for key in left:
        assert eq_exact(left[key].value, right[key].value)  # int exact, ratio exact
        assert type(left[key].value) is type(right[key].value)
    assert eq_tol(D('0'), D('0'))
    third = L.load_inputs(data, '2026Q1', conf)
    assert third.inputs == first.inputs and third.issues == first.issues


def test_previous_ledger_absent_is_first_period_present_is_loaded(tmp_path):
    data, conf = _root(tmp_path)
    absent = L.load_inputs(data, '2026Q1', conf, previous_period='2025Q4')
    assert absent.inputs.previous_ledger == ()  # [L890] no grade is invented
    kinds = [(i.kind, i.code) for i in absent.issues]
    assert ('NO_PREVIOUS_LEDGER', RC.FIRST_PERIOD.value) in kinds
    assert 'L4' not in str(kinds)  # the fallback is never the lowest grade
    _write(data / '2025Q4' / 'grade_ledger.csv', LEDGER_HEADER,
           (('S1', 'V1', '2025Q4', 'L2', '', 'act', 'act', '', '零售部', '赵六', '2026-04-30',
             '', 'yes', '0'),))
    loaded = L.load_inputs(data, '2026Q1', conf, previous_period='2025Q4')
    rows = loaded.inputs.previous_ledger
    assert len(rows) == 1 and rows[0].grade == 'L2' and rows[0].previous_grade is None
    assert rows[0].ledger_complete is True and rows[0].usable_for_elimination is False
    assert rows[0].deadline.year == 2026
    assert 'grade_ledger.csv' in loaded.fingerprints  # [L891] it is an input too
    assert not [i for i in loaded.issues if i.kind == 'NO_PREVIOUS_LEDGER']


def test_parquet_dispatch_and_float_guard(tmp_path):
    with pytest.raises(CoercionError) as caught:
        cell_to_text(0.1)  # H-4 [L1265]: a float never enters the pipeline
    assert caught.value.kind == 'FLOAT_IN_SOURCE'
    assert cell_to_text(float('nan')) == '' and cell_to_text(None) == ''
    stub = tmp_path / 'metric_dict.parquet'
    stub.write_bytes(b'not a parquet file')
    try:
        import pyarrow  # noqa
    except ImportError:
        with pytest.raises(DataLoadError) as caught:  # loud, never a silent empty table
            load_table(stub, 'metric_dict')
        assert 'parquet' in str(caught.value)
        return
    import pandas
    frame = pandas.DataFrame([dict(zip(DICT_HEADER, DICT_ROWS[0]))])
    real = tmp_path / 'metric_dict.parquet'
    frame.to_parquet(real)
    header, rows = L.read_table(real)
    assert header == DICT_HEADER and len(rows) == 1
    rows_out, name, fingerprint, issues = load_table(real, 'metric_dict')
    assert name == 'metric_dict.parquet' and rows_out[0].metric_id == 'M_ONE'
    assert type(rows_out[0].target_value) is int and rows_out[0].is_redline is True
    assert fingerprint.row_count == 1 and not issues

    # D-C1-01 float guard at the file level, not only at cell_to_text: a real
    # parquet float column must be refused as FLOAT_IN_SOURCE, never stringified.
    floaty = tmp_path / 'floaty.parquet'
    pandas.DataFrame({'metric_id': ['M_ONE'], 'target_value': [0.5]}).to_parquet(floaty)
    with pytest.raises(CoercionError) as caught:
        L.read_table(floaty)
    assert caught.value.kind == 'FLOAT_IN_SOURCE'


def test_parquet_and_csv_branches_type_identically(tmp_path):
    # D-C1-01 regression (V-9): both reader branches feed the one coerce path,
    # so identical cells produce identical typed rows, value and type per field.
    import pandas
    frame = pandas.DataFrame([dict(zip(DICT_HEADER, row)) for row in DICT_ROWS])
    pq = tmp_path / 'metric_dict.parquet'
    frame.to_parquet(pq)
    csv_rows, _, _, csv_issues = load_table(_write(tmp_path / 'c' / 'metric_dict.csv',
                                                   DICT_HEADER, DICT_ROWS), 'metric_dict')
    pq_rows, _, _, pq_issues = load_table(pq, 'metric_dict')
    assert not csv_issues and not pq_issues
    assert len(csv_rows) == len(pq_rows) == len(DICT_ROWS)
    for left, right in zip(csv_rows, pq_rows):
        assert left == right
        for field in type(left).model_fields:
            a, b = getattr(left, field), getattr(right, field)
            assert type(a) is type(b), (field, type(a), type(b))
            assert a == b, field


def test_unit_lookup_gap_leaves_the_row_to_preflight(tmp_path):
    data, conf = _root(tmp_path, facts=(('S9', 'V1', '2026Q1', 'M_GONE', '5', '', '5', 'OK',
                                        '2026-04-01T10:00:00', '2026-03-31', 't', 'c1'),))
    loaded = L.load_inputs(data, '2026Q1', conf)
    row = loaded.inputs.metric_facts[0]
    assert row.value == 5  # no unit, so no money claim is invented (B-008)
    units = [i for i in loaded.issues if i.kind == 'UNIT_UNKNOWN']
    assert len(units) == 2 and {i.column for i in units} == {'value_num', 'value'}
    assert loaded.fingerprints['metric_facts.csv'].row_count == 1
