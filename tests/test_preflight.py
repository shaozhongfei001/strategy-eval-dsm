'''tests/test_preflight.py -- C2 守护测试。

覆盖：G-10（[L1412] 未签认指标）、G-11（[L1413] 权重版本过期 / 金额非整数）、
V-14（[L1507] 无静默降级，逐条断言 reason_code + 披露位置）、以及 [L917] 的三条
BLOCK 硬行为（只写 audit_bundle / 退出码 2 / 不产 score_card），每条独立成测。
判据一律引 digest M22（C-01~C-10）与 M28（降级矩阵），不自造业务数值：阈值、
签认取值集合、评价期基准日全部是构造入参。
'''
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

import pytest

from dsm import io_loaders, numeric, preflight
from dsm.io_loaders import Inputs
from dsm.models import (AnchorSetDoc, DesignCardRow, GradeLedgerRow, MetricDictRow,
                        MetricFactRow, RedlineRow, StrategyMasterRow, WeightProvenance,
                        WeightVersionDoc)
from dsm.reason_codes import RC, Severity, is_registered
from dsm.reason_codes import severity as rc_severity

PERIOD, REF = '2024Q1', date(2024, 3, 31)
SIGNED = ('SIGNED',)
CHECK_IDS = tuple('C-' + str(i).zfill(2) for i in range(1, 11))
STRATEGY_SCOPED = {'NOT_ASSESSED', 'MISSING_RATE_BLOCK', 'EVIDENCE_CARD_MISSING',
                   'EV_D_NOT_ASSESSED'}


def _provenance(**over):
    payload = dict(kind='AHP_ONLY', whatif_run_id='WIF-2024-01', approved_by='张三',
                   approved_date=date(2024, 1, 5), effective_from=date(2024, 1, 1),
                   effective_to=date(2024, 12, 31))
    payload.update(over)
    return WeightProvenance(**payload)


def _weights(**over):
    payload = dict(weight_version_id='WV-2024', status='FROZEN',
                   effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31),
                   level1_weights={'D1': Decimal('0.6'), 'D2': Decimal('0.4')},
                   level2_weights={'D1': {'M1': Decimal('0.5'), 'M2': Decimal('0.5')},
                                   'D2': {'M3': Decimal('1.0')}},
                   approved_by='李四', approved_date=date(2024, 1, 5),
                   provenance=_provenance())
    payload.update(over)
    return WeightVersionDoc(**payload)


def _metric(metric_id, dim_code='D1', unit='RATIO', signoff_status='SIGNED', **over):
    payload = dict(metric_id=metric_id, metric_name=metric_id, dim_code=dim_code,
                   numerator_def='分子口径', denominator_def=None, time_window='30D',
                   dedup_rule='USER', missing_rule='SKIP', outlier_rule='CLIP_P1_P99',
                   attainment_formula='RATIO_DIRECT', direction=1, unit=unit,
                   target_value=None, target_basis='budget', is_redline=False,
                   owner_name='王五', signoff_status=signoff_status,
                   signoff_date=date(2024, 1, 2), dim_signoff_status='SIGNED',
                   dict_version='DV-1', caliber_version='CAL-1')
    payload.update(over)
    return MetricDictRow(**payload)


def _fact(strategy_id, metric_id, value=Decimal('0.5'), **over):
    payload = dict(strategy_id=strategy_id, version_id='V1', period=PERIOD,
                   metric_id=metric_id, value_num=value, value_den=None, value=value,
                   data_quality_flag='OK', snapshot_time=datetime(2024, 3, 31, 8, 0, 0),
                   data_as_of=REF, source_table='dw.fact', caliber_version='CAL-1')
    payload.update(over)
    return MetricFactRow(**payload)


def _master(strategy_id, version_id='V1', **over):
    payload = dict(strategy_id=strategy_id, version_id=version_id, strategy_name=strategy_id,
                   biz_domain='信用卡', scene_code='SC1', segment_type='EXISTING',
                   online_date=date(2023, 6, 1), offline_date=None, owner_dept='部门',
                   owner_name='赵六', status='ACTIVE', version_change_note=None)
    payload.update(over)
    return StrategyMasterRow(**payload)


def _card(strategy_id, card_status='COMPLETE', version_id='V1', **over):
    payload = dict(strategy_id=strategy_id, version_id=version_id, direct_goal='提升转化',
                   process_metrics=('M1',), result_metrics=('M2',), observation_window='90D',
                   data_source='dw', data_timeliness='T+1', eval_method='AB_TEST',
                   control_arrangement='CONCURRENT_CONTROL', success_criteria='lift >= 1%',
                   risk_constraints='无', eval_owner='钱七', card_status=card_status)
    payload.update(over)
    return DesignCardRow(**payload)


def _ledger(strategy_id, version_id='V1'):
    return GradeLedgerRow(strategy_id=strategy_id, version_id=version_id, period='2023Q4',
                          grade='L2', ledger_complete=True, usable_for_elimination=True)


def _metrics():
    return (_metric('M1', 'D1', 'MONEY_MINOR'), _metric('M2', 'D1', 'RATIO'),
            _metric('M3', 'D2', 'COUNT'))


def _facts_for(masters, metrics):
    return tuple(_fact(m.strategy_id, d.metric_id, 1000 if d.unit == 'MONEY_MINOR'
                       else Decimal('0.5')) for m in masters for d in metrics)


def _world(**over):
    metrics = over.pop('metric_dict', _metrics())
    masters = over.pop('strategy_master', (_master('S1'), _master('S2')))
    facts = over.pop('metric_facts', _facts_for(masters, metrics))
    cards = over.pop('design_cards', tuple(_card(m.strategy_id) for m in masters))
    redlines = over.pop('redlines', (RedlineRow(metric_id='M1', level='HARD', comparator='GT',
                                                threshold_value=1000, forced_grade='L4',
                                                reason_code='REDLINE_HARD_M1',
                                                waiver_allowed=False),))
    ledger = over.pop('previous_ledger', tuple(_ledger(m.strategy_id) for m in masters))
    anchor = over.pop('anchor_set', AnchorSetDoc(
        anchor_set_id='A1', strategy_ids=tuple(m.strategy_id for m in masters),
        effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31),
        rationale='覆盖各域的稳定策略'))
    weights = over.pop('weight_version', _weights())
    inputs = Inputs(strategy_master=masters, metric_dict=metrics, metric_facts=facts,
                    design_cards=cards, redlines=redlines, previous_ledger=ledger)
    config = preflight.PreflightConfig(
        period=PERIOD, period_ref_date=REF, weight_version=weights, anchor_set=anchor,
        signed_signoff_status=over.pop('signed_signoff_status', SIGNED),
        missing_rate_warn=over.pop('missing_rate_warn', Decimal('0.1')),
        missing_rate_block=over.pop('missing_rate_block', Decimal('0.3')))
    assert not over, over
    return inputs, config


def _ctx():
    return {'run_id': 'RUN-2024Q1-01', 'run_at': datetime(2024, 4, 1, 9, 0, 0),
            'dsm_version': 'v1.1', 'design_version': 'DSM-v1.1',
            'cel_contract_version': 'CEL-0', 'config_snapshot_sha256': 'ab' * 32,
            'input_fingerprints': {}, 'sensitivity_schemes': (), 'seed': None,
            'reproducibility_hash': 'cd' * 32}


def _find(result, reason_code):
    return tuple(f for f in result.findings if f.reason_code == reason_code)


def _only(result, reason_code):
    found = _find(result, reason_code)
    assert len(found) == 1, [f.reason_code for f in result.findings]
    return found[0]


def test_happy_path_all_ten_checks_pass():
    inputs, config = _world()
    result = preflight.run(inputs, config)
    assert result.status == preflight.STATUS_PASS
    assert result.exit_code == preflight.EXIT_OK == 0
    assert result.findings == () and result.downgrade_actions == ()
    assert result.not_assessed == () and result.dropped_metrics == ()
    assert result.emptied_dims == () and result.anchor_fallback is False
    assert result.coverage_after_drop == {'S1': Decimal('1'), 'S2': Decimal('1')}


def test_g11a_weight_version_stale_blocks():
    inputs, config = _world(weight_version=_weights(effective_to=date(2024, 3, 30)))
    result = preflight.run(inputs, config)
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2
    stale = _only(result, 'WEIGHT_VERSION_STALE')
    assert stale.code == 'C-01' and stale.severity is Severity.BLOCK
    assert stale.blocks_run is True and stale.disclosure == 'audit + 退出码 2'
    assert 'STALE' in stale.to_audit_finding().message


def test_c01_draft_window_and_whatif_block():
    draft = preflight.run(*_world(weight_version=_weights(status='DRAFT')))
    assert _only(draft, 'WEIGHT_VERSION_DRAFT').code == 'C-01'
    assert draft.status == preflight.STATUS_BLOCK and draft.exit_code == 2
    early = preflight.run(*_world(weight_version=_weights(effective_from=date(2024, 4, 1))))
    assert _only(early, 'WEIGHT_VERSION_INVALID').code == 'C-01'
    nowif = preflight.run(*_world(weight_version=_weights(provenance=None)))
    assert _only(nowif, 'WEIGHT_MISSING_WHATIF_RUN_ID').code == 'C-01'
    assert nowif.status == preflight.STATUS_BLOCK
    blank = preflight.run(*_world(weight_version=_weights(approved_by='  ')))
    assert _only(blank, 'WEIGHT_VERSION_INVALID').detail == 'approved_by 为空，未签认'


def test_g10_unsigned_metric_dropped_and_coverage_falls():
    metrics = (_metric('M1', 'D1', 'MONEY_MINOR'), _metric('M2', 'D1', signoff_status='PENDING'),
               _metric('M3', 'D2', 'COUNT'))
    result = preflight.run(*_world(metric_dict=metrics))
    dropped = _only(result, 'METRIC_NOT_SIGNED')
    assert dropped.code == 'C-02' and dropped.scope == 'metric:M2'
    assert dropped.severity is Severity.WARN and dropped.blocks_run is False
    assert dropped.disclosure == 'score_card flag + 报告附录'
    assert result.dropped_metrics == ('M2',) and result.emptied_dims == ()
    assert result.status == preflight.STATUS_WARN and result.exit_code == 0
    for sid in ('S1', 'S2'):
        assert numeric.eq_tol(result.coverage_after_drop[sid], Decimal(2) / Decimal(3))
    assert _find(result, 'DIMENSION_EMPTIED') == ()


def test_c02_single_emptied_dimension_reallocates():
    metrics = (_metric('M1', 'D1', 'MONEY_MINOR'), _metric('M2', 'D1'),
               _metric('M3', 'D2', 'COUNT', signoff_status='REJECTED'))
    result = preflight.run(*_world(metric_dict=metrics))
    reallocated = _only(result, 'WEIGHT_REALLOCATED')
    assert reallocated.code == 'C-02' and reallocated.scope == 'dim:D2'
    assert reallocated.disclosure == 'WEIGHT_REALLOCATED'
    assert result.emptied_dims == ('D2',) and result.dropped_metrics == ('M3',)
    assert result.status == preflight.STATUS_WARN
    assert _find(result, 'DIMENSION_EMPTIED') == ()


def test_c02_two_emptied_dimensions_block():
    metrics = tuple(_metric(m, d, u, signoff_status='PENDING') for m, d, u
                    in (('M1', 'D1', 'MONEY_MINOR'), ('M2', 'D1', 'RATIO'),
                        ('M3', 'D2', 'COUNT')))
    result = preflight.run(*_world(metric_dict=metrics))
    emptied = _only(result, 'DIMENSION_EMPTIED')
    assert emptied.code == 'C-02' and emptied.scope == 'run'
    assert emptied.severity is Severity.BLOCK and emptied.blocks_run is True
    assert result.emptied_dims == ('D1', 'D2')
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2
    assert result.not_assessed == ('S1', 'S2')
    unassessed = _find(result, 'NOT_ASSESSED')
    assert len(unassessed) == 2 and not any(f.blocks_run for f in unassessed)


def test_c03_weight_dict_misalignment_blocks():
    no_entry = _weights(level2_weights={'D1': {'M1': Decimal('1.0')},
                                        'D2': {'M3': Decimal('1.0')}})
    orphan = _weights(level2_weights={'D1': {'M1': Decimal('0.5'), 'M2': Decimal('0.25'),
                                             'M9': Decimal('0.25')},
                                      'D2': {'M3': Decimal('1.0')}})
    unnormalized = _weights(level1_weights={'D1': Decimal('0.5'), 'D2': Decimal('0.4')})
    for weights in (no_entry, orphan, unnormalized):
        result = preflight.run(*_world(weight_version=weights))
        found = _find(result, 'WEIGHT_DICT_MISALIGNED')
        assert found and result.status == preflight.STATUS_BLOCK
        assert result.exit_code == 2
        assert all(f.code == 'C-03' and f.blocks_run for f in found)
    assert 'M2' in _find(preflight.run(*_world(weight_version=no_entry)),
                         'WEIGHT_DICT_MISALIGNED')[0].scope
    assert 'M9' in _find(preflight.run(*_world(weight_version=orphan)),
                         'WEIGHT_DICT_MISALIGNED')[0].scope


def test_c04_missing_rate_warn_and_block_thresholds():
    masters = (_master('S1'), _master('S2'))
    metrics = _metrics()
    facts = (_fact('S1', 'M1', 1000), _fact('S1', 'M2'))
    inputs, config = _world(strategy_master=masters, metric_dict=metrics, metric_facts=facts,
                            missing_rate_warn=Decimal('0.1'),
                            missing_rate_block=Decimal('0.9'))
    result = preflight.run(inputs, config)
    warn = _only(result, 'MISSING_RATE_WARN')
    block = _only(result, 'MISSING_RATE_BLOCK')
    assert warn.code == block.code == 'C-04'
    assert warn.scope == 'strategy:S1' and block.scope == 'strategy:S2'
    assert warn.disclosure == 'preflight findings' and block.disclosure == '台账单独计数'
    assert 'M3=SKIP' in warn.detail and 'M2' in block.detail
    assert block.severity is Severity.BLOCK and block.blocks_run is False
    assert result.status == preflight.STATUS_WARN and result.exit_code == 0
    assert result.not_assessed == ('S2',)
    assert numeric.eq_tol(result.coverage_after_drop['S1'], Decimal(2) / Decimal(3))
    assert result.coverage_after_drop['S2'] == Decimal(0)
    assert {a.reason_code for a in result.downgrade_actions} == {'MISSING_RATE_WARN',
                                                                 'MISSING_RATE_BLOCK'}


def test_c05_data_as_of_lag_warns():
    metrics = _metrics()
    masters = (_master('S1'),)
    facts = tuple(_fact('S1', d.metric_id, 1000 if d.unit == 'MONEY_MINOR' else Decimal('0.5'),
                        data_as_of=date(2024, 3, 20)) for d in metrics)
    result = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=facts))
    stale = _only(result, 'DATA_STALE')
    assert stale.code == 'C-05' and stale.severity is Severity.WARN
    assert stale.disclosure == 'score_card'
    assert stale.scope == 'data_as_of:2024-03-20' and '11 天' in stale.detail
    assert result.status == preflight.STATUS_WARN and result.exit_code == 0


def test_c06_suspect_fact_dropped_and_coverage_falls():
    masters = (_master('S1'),)
    metrics = _metrics()
    facts = (_fact('S1', 'M1', 1000), _fact('S1', 'M2', data_quality_flag='SUSPECT'),
             _fact('S1', 'M3', Decimal('0.5')))
    result = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=facts))
    suspect = _only(result, 'DATA_QUALITY_SUSPECT')
    assert suspect.code == 'C-06' and suspect.scope == 'strategy:S1 metric:M2'
    assert suspect.disclosure == 'score_card flag' and suspect.severity is Severity.WARN
    assert numeric.eq_tol(result.coverage_after_drop['S1'], Decimal(2) / Decimal(3))
    assert 'M2' in _only(result, 'MISSING_RATE_BLOCK').detail
    assert result.not_assessed == ('S1',)
    assert _only(result, 'DATA_QUALITY_SUSPECT').owner_hint
    assert ('S1/M2',) == tuple(a.subject for a in result.downgrade_actions
                               if a.reason_code == 'DATA_QUALITY_SUSPECT')


def test_c07_caliber_mismatch_blocks():
    masters = (_master('S1'), _master('S2'))
    metrics = _metrics()
    facts = tuple(_fact(m.strategy_id, d.metric_id,
                        1000 if d.unit == 'MONEY_MINOR' else Decimal('0.5'),
                        caliber_version='CAL-2' if d.metric_id == 'M2' else 'CAL-1')
                  for m in masters for d in metrics)
    result = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=facts))
    mismatch = _find(result, 'CALIBER_VERSION_MISMATCH')
    assert len(mismatch) == 1 and mismatch[0].code == 'C-07'
    assert mismatch[0].scope == 'metric:M2' and mismatch[0].blocks_run is True
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2


def test_c08_partial_caps_evidence_and_missing_not_assessed():
    masters = (_master('S1'), _master('S2'))
    cards = (_card('S2', 'PARTIAL'),)
    result = preflight.run(*_world(strategy_master=masters, design_cards=cards))
    partial = _only(result, 'EVIDENCE_CARD_PARTIAL')
    missing = _only(result, 'EVIDENCE_CARD_MISSING')
    assert partial.code == missing.code == 'C-08'
    assert partial.scope == 'strategy:S2' and missing.scope == 'strategy:S1'
    assert result.evidence_ceiling == {'S2': 'C'}
    assert partial.disclosure == 'evidence_reason' and missing.disclosure == '台账单独计数'
    assert result.not_assessed == ('S1',)
    assert missing.severity is Severity.BLOCK and missing.blocks_run is False
    assert result.status == preflight.STATUS_WARN and result.exit_code == 0


def test_g11b_money_non_integer_blocks():
    masters = (_master('S1'),)
    metrics = _metrics()
    facts = (_fact('S1', 'M1', Decimal('10.5')), _fact('S1', 'M2'), _fact('S1', 'M3',
                                                                          Decimal('0.5')))
    result = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=facts))
    money = _find(result, 'MONEY_NON_INTEGER')
    assert money and all(f.code == 'C-09' and f.blocks_run for f in money)
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2
    assert money[0].disclosure == 'audit' and 'value' in money[0].scope
    redline = RedlineRow(metric_id='M1', level='HARD', comparator='GT',
                         threshold_value=Decimal('1.5'), forced_grade='L4',
                         reason_code='REDLINE_HARD_M1', waiver_allowed=False)
    second = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=_facts_for(masters, metrics),
                                   redlines=(redline,)))
    assert _only(second, 'MONEY_NON_INTEGER').scope == 'redline:M1.threshold_value'
    assert second.status == preflight.STATUS_BLOCK


def test_c10_anchor_invalid_falls_back_with_rank_reversal_risk():
    masters = (_master('S1'), _master('S2', status='RETIRED'))
    worlds = (
        dict(anchor_set=AnchorSetDoc(anchor_set_id='A1', strategy_ids=('S1', 'S9'),
                                     effective_from=date(2024, 1, 1),
                                     effective_to=date(2024, 12, 31), rationale='r')),
        dict(anchor_set=AnchorSetDoc(anchor_set_id='A1', strategy_ids=('S1', 'S2'),
                                     effective_from=date(2024, 1, 1),
                                     effective_to=date(2024, 12, 31), rationale='r')),
        dict(anchor_set=AnchorSetDoc(anchor_set_id='A1', strategy_ids=('S1',),
                                     effective_from=date(2024, 1, 1),
                                     effective_to=date(2024, 3, 1), rationale='r')),
        dict(anchor_set=None),
        dict(previous_ledger=(_ledger('S1', 'V0'), _ledger('S2', 'V1'))),
    )
    for over in worlds:
        result = preflight.run(*_world(strategy_master=masters, **over))
        stale = _only(result, 'ANCHOR_SET_STALE')
        risk = _only(result, 'RANK_REVERSAL_RISK')
        assert stale.code == risk.code == 'C-10'
        assert stale.severity is Severity.WARN and risk.severity is Severity.WARN
        assert stale.disclosure == risk.disclosure == '报告首屏'
        assert result.anchor_fallback is True
        assert result.status == preflight.STATUS_WARN and result.exit_code == 0
        assert {a.reason_code for a in result.downgrade_actions} >= {'ANCHOR_SET_STALE',
                                                                    'RANK_REVERSAL_RISK'}


def test_c10_first_period_records_unverified_version_baseline():
    result = preflight.run(*_world(previous_ledger=()))
    first = _only(result, 'FIRST_PERIOD')
    assert first.code == 'C-10' and first.severity is Severity.INFO
    assert first.disclosure == 'preflight findings' and '未核验' in first.detail
    assert result.anchor_fallback is False
    assert result.status == preflight.STATUS_PASS and result.exit_code == 0
    assert result.findings == (first,)


def test_block_writes_only_audit_bundle(tmp_path):
    inputs, config = _world(weight_version=_weights(status='DRAFT'))
    out = tmp_path / 'out'
    exit_code, result, written = preflight.execute(inputs, config, out, _ctx())
    assert exit_code == 2 and result.status == preflight.STATUS_BLOCK
    assert [p.name for p in written] == ['audit.json']
    assert sorted(p.name for p in out.rglob('*')) == ['audit.json']
    payload = json.loads((out / 'audit.json').read_text(encoding='utf-8'))
    assert payload['exit_code'] == 2 and payload['output_fingerprints'] == {}
    assert payload['period'] == PERIOD and payload['weight_version_id'] == 'WV-2024'
    assert any('WEIGHT_VERSION_DRAFT' in f['message'] and f['code'] == 'C-01'
               and f['severity'] == 'BLOCK' for f in payload['preflight_findings'])
    assert payload['run_id'] == 'RUN-2024Q1-01'


def test_block_exit_code_is_two(tmp_path):
    inputs, config = _world(weight_version=_weights(effective_to=date(2024, 3, 30)))
    exit_code, result, written = preflight.execute(inputs, config, tmp_path / 'out', _ctx())
    assert exit_code == 2 == preflight.EXIT_BLOCK == result.exit_code
    assert written and result.status == preflight.STATUS_BLOCK
    warn_inputs, warn_config = _world(previous_ledger=())
    out = tmp_path / 'pass_out'
    code2, result2, written2 = preflight.execute(warn_inputs, warn_config, out, _ctx())
    assert code2 == preflight.EXIT_OK == 0 and written2 == ()
    assert not out.exists() and result2.status == preflight.STATUS_PASS


def test_block_produces_no_score_card(tmp_path):
    inputs, config = _world(weight_version=_weights(provenance=None))
    out = tmp_path / 'out'
    exit_code, result, written = preflight.execute(inputs, config, out, _ctx())
    assert exit_code == 2
    assert not hasattr(result, 'score_card') and not hasattr(result, 'score_card_rows')
    assert not [p for p in out.rglob('*') if p.name.startswith('score_card')]
    assert not (out / 'score_card.csv').exists()
    assert not (out / 'score_card.parquet').exists()
    assert sorted(p.name for p in out.rglob('*')) == ['audit.json']
    assert [p.name for p in written] == ['audit.json']
    payload = json.loads((out / 'audit.json').read_text(encoding='utf-8'))
    assert payload['output_fingerprints'] == {}


def test_v14_every_finding_and_downgrade_is_disclosed():
    masters = (_master('S1'), _master('S2'), _master('S3', status='RETIRED'))
    metrics = (_metric('M1', 'D1', 'MONEY_MINOR'), _metric('M2', 'D1'),
               _metric('M3', 'D2', 'COUNT', signoff_status='REJECTED'))
    facts = (_fact('S1', 'M1', 1000, data_as_of=date(2024, 3, 20)),
             _fact('S2', 'M1', 1000, data_quality_flag='SUSPECT'),
             _fact('S2', 'M2'), _fact('S3', 'M3', Decimal('0.5')))
    cards = (_card('S1'), _card('S2', 'PARTIAL'), _card('S3'))
    inputs, config = _world(strategy_master=masters, metric_dict=metrics, metric_facts=facts,
                            design_cards=cards, missing_rate_warn=Decimal('0.1'),
                            missing_rate_block=Decimal('0.9'))
    result = preflight.run(inputs, config)
    assert result.status == preflight.STATUS_WARN and result.exit_code == 0
    assert result.findings, '十条检查全跑，降级必须留痕'
    for finding in result.findings:
        assert finding.code in CHECK_IDS
        assert is_registered(finding.reason_code)
        assert finding.severity is rc_severity(finding.reason_code)
        assert finding.blocks_run is (finding.reason_code in preflight.RUN_BLOCKING_CODES)
        assert finding.detail.strip() and finding.disclosure.strip()
        assert finding.owner_hint.strip() and finding.scope.strip()
        assert finding.disclosure == preflight.DISCLOSURE[finding.reason_code]
    for action in result.downgrade_actions:
        assert is_registered(action.reason_code)
        assert action.action.strip() and action.subject.strip()
    emitted = {f.reason_code for f in result.findings}
    assert {'METRIC_NOT_SIGNED', 'WEIGHT_REALLOCATED', 'DATA_STALE', 'DATA_QUALITY_SUSPECT',
            'MISSING_RATE_WARN', 'MISSING_RATE_BLOCK', 'EVIDENCE_CARD_PARTIAL',
            'ANCHOR_SET_STALE', 'RANK_REVERSAL_RISK'} <= emitted
    assert result.not_assessed == ('S3',)
    assert result.evidence_ceiling == {'S2': 'C'} and result.anchor_fallback is True
    assert numeric.eq_tol(result.coverage_after_drop['S2'], Decimal(1) / Decimal(3))


def test_v14_run_block_is_never_downgraded_and_no_default_config():
    assert set(preflight.RUN_BLOCKING_CODES).isdisjoint(STRATEGY_SCOPED)
    blockers = (
        dict(weight_version=_weights(status='DRAFT')),
        dict(weight_version=_weights(effective_to=date(2024, 3, 30))),
        dict(weight_version=_weights(provenance=_provenance(whatif_run_id=None))),
        dict(weight_version=_weights(level1_weights={'D1': Decimal('0.5'),
                                                     'D2': Decimal('0.4')})),
    )
    for over in blockers:
        result = preflight.run(*_world(**over))
        assert result.status == preflight.STATUS_BLOCK, over
        assert result.exit_code == preflight.EXIT_BLOCK == 2
        assert any(f.blocks_run and f.severity is Severity.BLOCK for f in result.findings)
        assert not any(f.reason_code in preflight.RUN_BLOCKING_CODES
                       and f.severity is not Severity.BLOCK for f in result.findings)
    cards = (_card('S2'),)
    strategy_level = preflight.run(*_world(design_cards=cards))
    assert _only(strategy_level, 'EVIDENCE_CARD_MISSING').severity is Severity.BLOCK
    assert strategy_level.status == preflight.STATUS_WARN
    assert strategy_level.exit_code == preflight.EXIT_OK

    class Bare:
        pass

    inputs, _ = _world()
    with pytest.raises(preflight.PreflightError):
        preflight.run(inputs, Bare())
    blocked_inputs, blocked_config = _world(weight_version=_weights(status='DRAFT'))
    blocked = preflight.run(blocked_inputs, blocked_config)
    with pytest.raises(preflight.PreflightError):
        preflight.build_audit_bundle(blocked, blocked_config, {'run_id': 'RUN-X'})


def test_c08_single_subject_missing_card_does_not_block_the_round(tmp_path):
    '''ORCH-29 第 3 条「单主体缺卡」侧的独立负向测试（R-2 测试内构造，不碰 fixtures/**）。

    原文逐字：M22 [L907]『| C-08 | 评价设计卡完备性 | PARTIAL（缺对照安排或成功判定）→
      证据上限压到 C；MISSING → 证据 D → NOT_ASSESSED | 降级 |』——严重度与动作列只有
      「降级」，全行没有 BLOCK；M28 [L1292]『| 评价设计卡 MISSING | C-08 | 证据 D →
      NOT_ASSESSED | 否 | 台账单独计数 |』；M23 [L977] 判定顺序 ①『设计卡缺失 → D
      （NOT_ASSESSED）』；M29 [L1346]『Step 7 pooling → 分池禁混排 + 一级库门禁 +
      占比双报 + NOT_ASSESSED 单列』。
    断言：S2（strategy_id × version 无对应卡）落 NOT_ASSESSED —— 已注册 reason_code +
      降级台账 + 披露位置，是 V-14 的显式留痕而不是静默降级；整轮不 BLOCK（status =
      WARN、退出码 0、execute() 一个文件都不写，不进 [L1324]-[L1326] 的 BLOCK 出口）；
      S1 / S3 照常评价。finding.severity 仍取注册表原值 BLOCK，本模块不改写成 WARN
      （「BLOCK 不得降为 WARN」+ [L918] 任何 WARN 都不会被静默吞掉）；是否阻断整轮只由
      RUN_BLOCKING_CODES 决定，策略级码不在其中。
    占比双报分母：preflight 只交 result.not_assessed 这一个「剔除集」，[L1004] 的分母
      算术由 C5 冻结的 tests/test_pooling.py 里
      test_not_assessed_is_counted_separately_and_out_of_denominators 守护（其
      not_assessed_reasons 恰为 {EVIDENCE_CARD_MISSING: 1}）；此处刻意不 import
      dsm/pooling.py —— SEAM-1 在飞，避免跨包写集耦合。
    '''
    masters = (_master('S1'), _master('S2'), _master('S3'))
    cards = (_card('S1'), _card('S3'))       # S2 在 T4 里没有 strategy_id × version 行
    inputs, config = _world(strategy_master=masters, design_cards=cards)
    result = preflight.run(inputs, config)

    assert result.status == preflight.STATUS_WARN
    assert result.exit_code == preflight.EXIT_OK == 0
    assert not any(f.blocks_run for f in result.findings), '单主体缺卡不得阻断整轮'
    missing = _only(result, RC.EVIDENCE_CARD_MISSING.value)
    assert missing.code == 'C-08' and missing.scope == 'strategy:S2'
    assert is_registered(missing.reason_code)
    assert missing.reason_code == RC.EVIDENCE_CARD_MISSING.value
    assert missing.severity is Severity.BLOCK is rc_severity(missing.reason_code)
    assert missing.blocks_run is False
    assert missing.disclosure == '台账单独计数'
    assert missing.disclosure == preflight.DISCLOSURE[RC.EVIDENCE_CARD_MISSING.value]
    assert missing.owner_hint.strip() and '本期无对应设计卡行' in missing.detail
    assert result.not_assessed == ('S2',), 'NOT_ASSESSED 单列，且只单列它'
    assert (RC.EVIDENCE_CARD_MISSING.value, 'S2') in {
        (a.reason_code, a.subject) for a in result.downgrade_actions}
    # 其余主体照常评价：整轮只有 S2 这一条 finding，S1 / S3 无 C-08、无证据封顶
    assert {f.scope for f in result.findings} == {'strategy:S2'}
    assert result.evidence_ceiling == {}
    assert {'S1', 'S3'}.isdisjoint(result.not_assessed)
    # 缺卡不等于缺数据：事实齐全，coverage 不因 C-08 下降（分母是指标字典全量）
    assert all(result.coverage_after_drop[s] == Decimal(1) for s in ('S1', 'S2', 'S3'))
    # 占比双报（[L1004] / [L1346]）：剔除集恰好等于 not_assessed，已参评 = 全体 - 剔除
    assessed = tuple(s for s in ('S1', 'S2', 'S3') if s not in result.not_assessed)
    assert assessed == ('S1', 'S3')
    assert len(assessed) == len(masters) - len(result.not_assessed) == 2
    # 不取 BLOCK 出口：退出码 0、一个文件都不写（audit.json 也不写）、score_card 不存在
    out = tmp_path / 'out'
    exit_code, executed, written = preflight.execute(inputs, config, out, _ctx())
    assert exit_code == preflight.EXIT_OK == 0
    assert executed.status == preflight.STATUS_WARN and written == ()
    assert not out.exists() and not (out / 'audit.json').exists()
    assert not [p for p in tmp_path.rglob('*') if p.name.startswith('score_card')]


def test_c08_missing_card_is_keyed_by_strategy_id_and_version():
    '''卡的存在性按 strategy_id × version 判（ORCH-29 第 3 条的粒度）。

    S1 本期是 V2，T4 里只有 S1 的 V1 卡 -> 该 strategy_id × version 无对应卡 ->
    NOT_ASSESSED；同表里 S2@V1 有卡 -> 照常评价。证明「缺卡」既不会按 strategy_id
    粗粒度放过（别的版本有卡不算有卡），也不会牵连其它主体（V-14）。
    '''
    metrics = _metrics()
    masters = (_master('S1', 'V2'), _master('S2', 'V1'))
    cards = (_card('S1', 'COMPLETE', version_id='V1'), _card('S2'))
    ledger = (_ledger('S1', 'V2'), _ledger('S2', 'V1'))
    # 事实行也必须按 version_id 对齐：否则 C-04 会以 MISSING_RATE_BLOCK 混进本测试
    facts = tuple(_fact(m.strategy_id, d.metric_id,
                        1000 if d.unit == 'MONEY_MINOR' else Decimal('0.5'),
                        version_id=m.version_id) for m in masters for d in metrics)
    result = preflight.run(*_world(strategy_master=masters, metric_dict=metrics,
                                   metric_facts=facts, design_cards=cards,
                                   previous_ledger=ledger))
    assert result.status == preflight.STATUS_WARN
    assert result.exit_code == preflight.EXIT_OK == 0
    assert {f.reason_code for f in result.findings} == {RC.EVIDENCE_CARD_MISSING.value}
    missing = _only(result, RC.EVIDENCE_CARD_MISSING.value)
    assert missing.code == 'C-08' and missing.scope == 'strategy:S1'
    assert '本期无对应设计卡行' in missing.detail and missing.blocks_run is False
    assert result.not_assessed == ('S1',) and result.evidence_ceiling == {}
    assert _find(result, RC.EVIDENCE_CARD_PARTIAL.value) == ()
    assert {'S2'}.isdisjoint(result.not_assessed)


def test_c08_all_subjects_cardless_is_disclosed_and_not_run_blocking_gap():
    '''ORCH-29 第 3 条「表级/轮级」侧：GAP 上报，本包不擅自新造 BLOCK。

    裁决要求「所评价期全部主体都无卡 -> 整轮 BLOCK（保留）」。核对原文后：C-08 名下
    没有这条 BLOCK。M22 [L907] 逐字『| C-08 | 评价设计卡完备性 | PARTIAL（缺对照安排
    或成功判定）→ 证据上限压到 C；MISSING → 证据 D → NOT_ASSESSED | 降级 |』——严重度
    与动作列只有「降级」；M28 [L1292] 同口径（是否出分 = 否 / 披露 = 台账单独计数）；
    M22 [L917] 只规定了 BLOCK 的三条硬行为，没有规定触发情形，触发情形写在 C-01 /
    C-02（清空维度数 >= 2）/ C-03 / C-07 / C-09 各自的严重度列里（**BLOCK**）。所以在
    C-08 里新增轮级 BLOCK 是无原文授权的新规则；且 dsm/reason_codes.py 没有「设计卡表
    整体缺失」的注册码（只有策略级 EVIDENCE_CARD_MISSING / EVIDENCE_CARD_PARTIAL /
    NOT_ASSESSED），R-15 批量注册归主控，本包不得自行改 reason_codes.py；把策略级码塞
    进 RUN_BLOCKING_CODES 又会直接弱化 C2 既有断言（test_c08_partial_caps_evidence_and_
    missing_not_assessed 的 blocks_run is False、test_v14_run_block_is_never_downgraded_
    and_no_default_config 的 RUN_BLOCKING_CODES.isdisjoint(STRATEGY_SCOPED) 与其末尾
    status == WARN），红线不许。
    本测试因此刻画当前行为并锁死 V-14 底线：全员无卡时逐主体留痕、绝不静默、运行状态
    是 WARN 而不是 BLOCK。若主控经 SDD 勘误 + R-15 注册新码后裁定轮级要 BLOCK，只需
    翻转末尾三条断言，其余 V-14 断言不变。
    '''
    masters = (_master('S1'), _master('S2'))
    result = preflight.run(*_world(strategy_master=masters, design_cards=()))
    missing = _find(result, RC.EVIDENCE_CARD_MISSING.value)
    assert len(missing) == 2, '每个无卡主体各留一条痕，不许并成一条轮级 finding'
    assert {f.scope for f in missing} == {'strategy:S1', 'strategy:S2'}
    assert all(f.code == 'C-08' and is_registered(f.reason_code) for f in missing)
    assert all(f.severity is rc_severity(f.reason_code) for f in missing)
    assert all(f.disclosure == '台账单独计数' and f.owner_hint.strip()
               and f.detail.strip() for f in missing)
    assert result.not_assessed == ('S1', 'S2'), '全员单列，一个都没被吞掉'
    assert {a.subject for a in result.downgrade_actions} == {'S1', 'S2'}
    assert all(a.reason_code == RC.EVIDENCE_CARD_MISSING.value
               for a in result.downgrade_actions)
    # 缺卡不等于缺数据：事实齐全时 coverage 仍是 1，不用 0 或 None 冒充（[L916]）
    assert all(v == Decimal(1) for v in result.coverage_after_drop.values())
    # GAP：当前不 BLOCK（原文未授权 + 无注册码），退出码 0，不写 audit bundle
    assert not any(f.blocks_run for f in result.findings)
    assert result.status == preflight.STATUS_WARN and result.exit_code == preflight.EXIT_OK


def test_c08_table_level_faults_fail_at_io_layer_with_exit_code_four(tmp_path):
    '''「表级/文件级」缺陷的真实归属是 io_loaders（[L888] / [L889] / [L892]），不是 C-08。

    M21 [L891]『输出 | Inputs（8 表）+ InputFingerprints（写入 audit.json，是第二人复跑
    的比对基准）』、[L892]『异常 | DataLoadError（退出码 4）』；M29 [L1330]『io_loaders
    → 8 表 + InputFingerprints（SHA256 / 行数）』。
    实测（R-2 测试内构造 CSV，不碰 fixtures/**）：
      1) T4 缺必需列（mde_ok，属 [L889] 类型强制要读的列）-> DataLoadError，退出码 4，
         在 preflight 之前就硬失败，绝不会被降级成 NOT_ASSESSED；
      2) 容器不可读（.jsonl 不是 [L888] 的 CSV / Parquet）-> 同样 DataLoadError 退出码 4；
      3) 但 T4 文件整体不存在时 io_loaders 记的是 kind = TABLE_ABSENT，而 TABLE_ABSENT
         不在 BLOCKING_KINDS 里（只有 strategy_master / metric_dict / metric_facts 才记
         MISSING_FILE）-> 交出空表继续跑，于是全主体 NOT_ASSESSED（见上一条测试）。
         「表整体缺失该不该整轮硬失败、走退出码 4（[L892]）还是 2（[L917]）」是跨层归属
         问题，已随本包上报主控裁决；本测试只固定当前事实，不替主控定规则。
    '''
    broken = tmp_path / 'design_cards.csv'
    broken.write_text('strategy_id,version_id,card_status,process_metrics,result_metrics\n'
                      'S1,V1,COMPLETE,M1,M2\n', encoding='utf-8')
    with pytest.raises(io_loaders.DataLoadError) as no_column:
        io_loaders.load_table(broken, 'design_cards')
    assert no_column.value.exit_code == 4
    assert no_column.value.exit_code != preflight.EXIT_BLOCK, '退出码 4（[L892]）不是 2'
    kinds = {i.kind for i in no_column.value.issues}
    assert 'MISSING_COLUMN' in kinds
    assert any('mde_ok' in i.message for i in no_column.value.issues)

    alien = tmp_path / 'design_cards.jsonl'
    alien.write_text('unsupported container: neither csv nor parquet\n', encoding='utf-8')
    with pytest.raises(io_loaders.DataLoadError) as unreadable:
        io_loaders.load_table(alien, 'design_cards')
    assert unreadable.value.exit_code == 4
    assert {i.kind for i in unreadable.value.issues} == {'MISSING_FILE'}

    assert 'MISSING_FILE' in io_loaders.BLOCKING_KINDS
    assert 'MISSING_COLUMN' in io_loaders.BLOCKING_KINDS
    assert 'TABLE_ABSENT' not in io_loaders.BLOCKING_KINDS   # 第 3 点的根据（GAP 待裁决）
