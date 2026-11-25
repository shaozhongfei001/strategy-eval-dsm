'''Tests for dsm.reason_codes -- registry completeness and lookup semantics.

Design doc 3.3.2 plus principles R5 (no silent downgrade) and P-8 (business code
must reference RC members, never string literals). A reason_code that is not in
this registry cannot be emitted, so the registry IS the disclosure contract.
'''
import pytest

from dsm.reason_codes import (
    RC,
    Severity,
    _BASIS,
    _BLOCKS_RUN,
    _DEFS,
    _META,
    batch2_codes,
    batch3_codes,
    blocks_run,
    blocks_run_codes,
    all_codes,
    basis,
    codes_by_severity,
    describe,
    is_registered,
    message,
    owner_hint,
    redline_hard,
    redline_soft,
    severity,
)

# These are the gates that must stay BLOCK: they stop scoring or stop a dismissal.
CONTRACT_BLOCK_CODES = (
    'WEIGHT_VERSION_INVALID',
    'WEIGHT_VERSION_DRAFT',
    'WEIGHT_VERSION_STALE',
    'WEIGHT_MISSING_WHATIF_RUN_ID',
    'CONFIG_PLACEHOLDER',
    'CONFIG_SEMANTIC_ERROR',
    'CALIBER_VERSION_MISMATCH',
    'MONEY_NON_INTEGER',
    'DIMENSION_EMPTIED',
    'INVARIANT_VIOLATION',
    'MISSING_RATE_BLOCK',
    'NOT_ASSESSED',
    'GR_REDLINE_FORCED',
    'REDLINE_HARD_HIT',
    'EVIDENCE_CARD_MISSING',
    'EVIDENCE_C_NO_LIMIT',
    'EV_D_NOT_ASSESSED',
    'WAIVER_INVALID',
    'WAIVER_EXPIRED',
    'FLIP_RATE_UNUSABLE',
    'METHOD_DIVERGENCE',
    'AHP_CR_FAILED',
    'AHP_NOT_RECIPROCAL',
    'AHP_DRAFT_ONLY',
    'ALPHA_INFEASIBLE',
    'ALPHA_FLOOR_INFEASIBLE',
    'CONFIG_INCONSISTENT',
    'CEL_DISABLED_DATA_PRESENT',
)

# R5: every downgrade or fallback path needs a code so it can disclose itself.
CONTRACT_DISCLOSURE_CODES = (
    'METRIC_NOT_SIGNED',
    'WEIGHT_REALLOCATED',
    'MISSING_RATE_WARN',
    'DATA_QUALITY_SUSPECT',
    'ANCHOR_SET_STALE',
    'RANK_REVERSAL_RISK',
    'GR_CAPPED_NO_TARGET',
    'GR_EVIDENCE_GATE_L1',
    'ENTROPY_INSUFFICIENT_SAMPLE',
    'ENTROPY_INACTIVE_FALLBACK',
    'ALPHA_FLOOR_APPLIED',
    'ALPHA_PURE_AHP',
    'TRIANGULATION_DISABLED',
    'LOO_SAMPLED',
    'CEL_NOT_CONNECTED',
)


def test_every_registered_code_carries_complete_metadata():
    for code in all_codes():
        assert severity(code) in Severity
        assert message(code).strip()
        assert owner_hint(code).strip()


def test_registry_rows_are_well_formed():
    for row in _DEFS:
        assert len(row) == 4
        code, sev, msg, owner = row
        assert code == code.upper()
        assert ' ' not in code
        assert sev in ('INFO', 'WARN', 'BLOCK')
        assert msg.strip()
        assert owner.strip()


def test_registry_has_no_duplicate_codes():
    names = [row[0] for row in _DEFS]
    assert len(names) == len(set(names))


def test_rc_enum_matches_the_registry_exactly():
    assert {m.value for m in RC} == set(all_codes())
    assert len(list(RC)) == len(all_codes()) == len(_META)


def test_members_compare_equal_to_bare_strings():
    assert RC.STABLE == 'STABLE'
    assert RC.STABLE.value == 'STABLE'
    assert hash(RC.STABLE) == hash('STABLE')
    assert {RC.STABLE: 1}['STABLE'] == 1


def test_str_of_a_member_is_qualified_so_serialization_must_use_value():
    # Pins a real trap: str()/f-string on a member yields RC.STABLE, not STABLE.
    # CSV writers and reproducibility_hash must therefore use .value.
    assert str(RC.STABLE) == 'RC.STABLE'
    assert '{}'.format(RC.STABLE) == 'RC.STABLE'
    assert RC.STABLE.value == 'STABLE'


def test_severity_buckets_partition_the_whole_registry():
    buckets = [codes_by_severity(s) for s in Severity]
    flat = [c for b in buckets for c in b]
    assert len(flat) == len(set(flat)) == len(all_codes())
    assert all(b == tuple(sorted(b)) for b in buckets)


def test_registry_is_big_enough_to_cover_the_documented_paths():
    assert len(all_codes()) >= 70
    assert len(codes_by_severity(Severity.BLOCK)) >= 20
    assert len(codes_by_severity(Severity.WARN)) >= 25
    assert len(codes_by_severity(Severity.INFO)) >= 8


def test_the_governance_gates_are_block_level():
    blocks = set(codes_by_severity(Severity.BLOCK))
    missing = [c for c in CONTRACT_BLOCK_CODES if c not in blocks]
    assert not missing, missing


def test_every_downgrade_path_has_a_disclosure_code():
    missing = [c for c in CONTRACT_DISCLOSURE_CODES if not is_registered(c)]
    assert not missing, missing


def test_documented_severities_of_the_robustness_triad():
    assert severity(RC.STABLE) is Severity.INFO
    assert severity(RC.NEAR_BOUNDARY) is Severity.WARN
    assert severity(RC.UNSTABLE) is Severity.WARN
    assert severity(RC.METHOD_AGREEMENT) is Severity.INFO
    assert severity(RC.METHOD_DIVERGENCE) is Severity.BLOCK
    assert severity(RC.FLIP_RATE_REVIEW) is Severity.WARN
    assert severity(RC.FLIP_RATE_UNUSABLE) is Severity.BLOCK


def test_dynamic_redline_codes_resolve_to_their_registered_template():
    hard = redline_hard('CONTACT_FREQ_PER_30D')
    soft = redline_soft('CONTACT_FREQ_PER_30D')
    assert hard == 'REDLINE_HARD_CONTACT_FREQ_PER_30D'
    assert soft == 'REDLINE_SOFT_CONTACT_FREQ_PER_30D'
    assert severity(hard) is Severity.BLOCK
    assert severity(soft) is Severity.WARN
    assert message(hard) == message('REDLINE_HARD_HIT')
    assert message(soft) == message('REDLINE_SOFT_HIT')
    assert owner_hint(hard) == owner_hint('REDLINE_HARD_HIT')
    assert is_registered(hard) and is_registered(soft)


def test_lookup_accepts_rc_members_and_bare_strings_alike():
    assert severity(RC.CONFIG_PLACEHOLDER) is severity('CONFIG_PLACEHOLDER')
    assert message(RC.CONFIG_PLACEHOLDER) == message('CONFIG_PLACEHOLDER')
    assert owner_hint(RC.CONFIG_PLACEHOLDER) == owner_hint('CONFIG_PLACEHOLDER')
    assert describe(RC.CONFIG_PLACEHOLDER) == describe('CONFIG_PLACEHOLDER')


def test_unknown_codes_raise_instead_of_degrading_silently():
    with pytest.raises(KeyError):
        severity('NOT_A_CODE')
    with pytest.raises(KeyError):
        message('REDLINE_HARD')
    with pytest.raises(KeyError):
        describe('REDLINE_SOFT')
    with pytest.raises(TypeError):
        severity(42)
    with pytest.raises(TypeError):
        severity(None)
    with pytest.raises(TypeError):
        severity(3.5)


def test_is_registered_mirrors_the_lookup_contract():
    assert is_registered('STABLE')
    assert is_registered(RC.STABLE)
    assert is_registered(redline_soft('ANY_METRIC'))
    assert not is_registered('STABLE_')
    assert not is_registered('NOPE')
    assert not is_registered(3.5)
    assert not is_registered(None)


def test_describe_is_self_contained_for_a_report_line():
    text = describe(RC.MISSING_RATE_BLOCK)
    assert text.startswith('[BLOCK]')
    assert 'MISSING_RATE_BLOCK' in text
    assert message(RC.MISSING_RATE_BLOCK) in text


def test_messages_are_unique_so_one_report_line_maps_to_one_code():
    msgs = [message(c) for c in all_codes()]
    assert len(msgs) == len(set(msgs))


def test_all_codes_is_sorted_and_deterministic_for_hashing():
    codes = all_codes()
    assert codes == tuple(sorted(codes))
    assert all_codes() == codes
    assert isinstance(codes, tuple)


# --- R15B2 第 2 批（ops/dag-state.json r15_batch_2.codes_requested / ORCH-30 第 4 条）---
# 盘点实测：_DEFS 共 79 行注册码（另有 _DYNAMIC_PREFIXES 2 行前缀映射，不是码；
# KNOWN-GAPS.md B-10 记的『81 条』把这两行前缀映射一起数了进去）。本批新增 11 条，
# 故总数写死 79 + 11 = 90，任何漂移（多注册 / 少注册 / 改名）都会在这里炸出来。
BATCH2_PRE_EXISTING = 79
BATCH2_NEW = (
    'DESIGN_CARD_TABLE_ABSENT',
    'DESIGN_CARD_DUPLICATE_KEY',
    'SPEARMAN_ZERO_VARIANCE',
    'H2_DIM_WEIGHT_BELOW_FLOOR',
    'H3_METRIC_WEIGHT_BELOW_FLOOR',
    'H5_SHIFT_FROM_AHP_EXCEEDED',
    'REDLINE_EXCLUDED_FROM_ENTROPY',
    'PRIMARY_POOL_REJECTED_GRADE',
    'WEIGHT_DICT_MISALIGNED',
    'APPROXIMATE_ATTRIBUTION',
    'MISSING_FACT_RULE_APPLIED',
)
BATCH2_TOTAL = BATCH2_PRE_EXISTING + len(BATCH2_NEW)
# --- CODES-2 第 3 批（ORCH-40）：范围过滤披露码。总数钉子随之上移一层，
# 任何漂移（多注册 / 少注册 / 改名）依然会在这里炸出来。
BATCH3_NEW = (
    'EV_OUT_OF_EVAL_PERIOD',
)
BATCH3_TOTAL = BATCH2_TOTAL + len(BATCH3_NEW)
BATCH3_EXPECTED_SEVERITY = {'EV_OUT_OF_EVAL_PERIOD': 'INFO'}
# R-12：severity 原文无严重度列、只按 V-14『不得静默』暂登记的码。这个清单只许缩短
# （主控裁决后换成 verbatim 依据），不许悄悄变长。
BATCH2_PLACEHOLDER_SEVERITY = ('SPEARMAN_ZERO_VARIANCE', 'APPROXIMATE_ATTRIBUTION')
# ORCH-30 第 2 条：blocks_run=True 的只有轮级码。
BATCH2_EXPECTED_BLOCKING = ('DESIGN_CARD_TABLE_ABSENT', 'DESIGN_CARD_DUPLICATE_KEY',
                            'WEIGHT_DICT_MISALIGNED')
BATCH2_EXPECTED_SEVERITY = {
    'DESIGN_CARD_TABLE_ABSENT': 'BLOCK',
    'DESIGN_CARD_DUPLICATE_KEY': 'BLOCK',
    'SPEARMAN_ZERO_VARIANCE': 'WARN',
    'H2_DIM_WEIGHT_BELOW_FLOOR': 'BLOCK',
    'H3_METRIC_WEIGHT_BELOW_FLOOR': 'BLOCK',
    'H5_SHIFT_FROM_AHP_EXCEEDED': 'BLOCK',
    'REDLINE_EXCLUDED_FROM_ENTROPY': 'INFO',
    'PRIMARY_POOL_REJECTED_GRADE': 'WARN',
    'WEIGHT_DICT_MISALIGNED': 'BLOCK',
    'APPROXIMATE_ATTRIBUTION': 'WARN',
    'MISSING_FACT_RULE_APPLIED': 'WARN',
}


def test_batch2_total_code_count_is_pinned_against_drift():
    assert len(list(RC)) == len(all_codes()) == len(_META) == BATCH3_TOTAL
    assert len(_DEFS) == BATCH3_TOTAL, '每行 _DEFS 恰是一个码'
    assert len(batch2_codes()) == len(BATCH2_NEW) == 11


def test_batch2_codes_are_all_registered_with_unique_values():
    values = [row[0] for row in _DEFS]
    assert len(values) == len(set(values)), '重复注册（ADJ-3 禁止）'
    for name in BATCH2_NEW:
        assert is_registered(name), name
        assert getattr(RC, name).value == name
        assert RC[name].value == name


def test_batch2_does_not_rename_or_shadow_any_pre_existing_code():
    # ADJ-3：既有 79 个码一个不少、一个不改名 —— 新码名必须与旧码名完全不相交。
    assert not (set(BATCH2_NEW) & set(CONTRACT_BLOCK_CODES))
    assert not (set(BATCH2_NEW) & set(CONTRACT_DISCLOSURE_CODES))
    assert BATCH2_TOTAL - len(BATCH2_NEW) == BATCH2_PRE_EXISTING
    still_there = [c for c in all_codes()
                   if c not in BATCH2_NEW and c not in BATCH3_NEW]
    assert len(still_there) == BATCH2_PRE_EXISTING


def test_batch2_severity_is_the_signed_off_value_and_was_not_rewritten():
    # V-14 / ORCH-30 第 2 条：severity 是签认属性，任何人不得为了跑通测试改写。
    for name, expected in BATCH2_EXPECTED_SEVERITY.items():
        assert severity(name) is Severity(expected), (name, severity(name))
        assert severity(RC[name]) is Severity(expected)


def test_batch2_blocks_run_is_registered_separately_from_severity():
    assert blocks_run_codes() == tuple(sorted(BATCH2_EXPECTED_BLOCKING))
    for name in BATCH2_EXPECTED_BLOCKING:
        assert blocks_run(name) is True and blocks_run(RC[name]) is True
    for name in BATCH2_NEW:
        if name not in BATCH2_EXPECTED_BLOCKING:
            assert blocks_run(name) is False, name
    # 三条 BLOCK 严重度但不阻断本轮的码（H-2 / H-3 / H-5 只判该 alpha 不可行）——
    # 这正是 ORCH-30 第 2 条要求分离登记的那一类，不得被『BLOCK 就该阻断』的直觉改掉。
    for name in ('H2_DIM_WEIGHT_BELOW_FLOOR', 'H3_METRIC_WEIGHT_BELOW_FLOOR',
                 'H5_SHIFT_FROM_AHP_EXCEEDED'):
        assert severity(name) is Severity.BLOCK and blocks_run(name) is False
    assert set(_BLOCKS_RUN) <= set(all_codes())


def test_batch2_every_code_carries_reason_owner_and_verbatim_basis():
    for name in BATCH2_NEW:
        assert message(name).strip(), name          # reason 文本非空
        assert owner_hint(name).strip(), name
        sev_basis, block_basis, consumer = basis(name)
        assert sev_basis.strip() and block_basis.strip() and consumer.strip(), name
        assert _BASIS[name] == basis(RC[name])
        # R-12：依据必须点名原文位置（Mxx Lnnn）或显式写 PLACEHOLDER，不许含糊。
        head = sev_basis.split(':', 1)[0]
        assert head in ('verbatim', 'derived', 'PLACEHOLDER'), (name, head)
        assert head != 'PLACEHOLDER' or 'L' in sev_basis, name
    assert tuple(sorted(_BASIS)) == tuple(sorted(BATCH2_NEW + BATCH3_NEW))


def test_batch2_placeholder_severities_are_disclosed_not_hidden():
    flagged = tuple(sorted(n for n in BATCH2_NEW if basis(n)[0].startswith('PLACEHOLDER')))
    assert flagged == tuple(sorted(BATCH2_PLACEHOLDER_SEVERITY)), flagged


def test_batch2_missing_fact_code_is_not_a_missing_rate_warn_clone():
    # B1b：ZERO / IMPUTE_MEDIAN 合成行不得挪用 MISSING_RATE_WARN（那是『缺失率超预警阈』）。
    assert message('MISSING_FACT_RULE_APPLIED') != message('MISSING_RATE_WARN')
    assert 'missing_rule' in message('MISSING_FACT_RULE_APPLIED')
    assert severity('MISSING_FACT_RULE_APPLIED') is Severity.WARN
    assert blocks_run('MISSING_FACT_RULE_APPLIED') is False


def test_batch2_seam1_preabsorption_keeps_the_orch28_semantics():
    # ORCH-28：池内样本 < min_pool_size 是 WARN + SMALL_POOL（非抛错）；sd = 0 走 INACTIVE。
    # 两码在第 2 批之前就已注册，故本批不重复注册（ADJ-3），只锁死语义防被后续改动。
    assert severity('SMALL_POOL') is Severity.WARN and blocks_run('SMALL_POOL') is False
    assert severity('INACTIVE_METRIC') is Severity.WARN
    assert severity('POOL_TOO_SMALL') is Severity.WARN
    assert 'SMALL_POOL' not in BATCH2_NEW and 'INACTIVE_METRIC' not in BATCH2_NEW


# --- CODES-2 第 3 批（ORCH-40）：EV_OUT_OF_EVAL_PERIOD ---------------------------
def test_batch3_total_code_count_is_pinned_against_drift():
    assert len(batch3_codes()) == len(BATCH3_NEW) == 1
    assert BATCH3_TOTAL == BATCH2_TOTAL + 1
    assert len(_DEFS) == len(all_codes()) == BATCH3_TOTAL


def test_batch3_out_of_eval_period_is_info_and_does_not_block_the_run():
    # ORCH-30 第 2 条：severity 与 blocks_run 分离登记。本码是「正常换版/退役」的披露，
    # 不是缺陷也不是阻断；若被改成 BLOCK 就会把范围外主体又算回 NOT_ASSESSED 单列明细，
    # 污染 ORCH-36/ORCH-37 第 6 条裁定的「占比双报分母 11」口径。
    name = 'EV_OUT_OF_EVAL_PERIOD'
    assert is_registered(name) and getattr(RC, name).value == name
    assert BATCH3_EXPECTED_SEVERITY[name] == 'INFO'
    assert severity(name) is Severity.INFO
    assert severity(RC[name]) is Severity.INFO
    assert blocks_run(name) is False and blocks_run(RC[name]) is False
    assert name not in _BLOCKS_RUN
    assert message(name).strip() and owner_hint(name).strip()


def test_batch3_carries_a_citable_basis_and_is_not_a_clone_of_an_existing_code():
    # R-12：依据必须点名原文位置（Mxx Lnnn）或显式写 PLACEHOLDER。
    name = 'EV_OUT_OF_EVAL_PERIOD'
    sev_basis, block_basis, consumer = basis(name)
    assert _BASIS[name] == basis(RC[name])
    for text in (sev_basis, block_basis, consumer):
        assert text.strip()
    assert sev_basis.split(':', 1)[0] in ('verbatim', 'derived', 'PLACEHOLDER')
    assert block_basis.split(':', 1)[0] in ('verbatim', 'derived', 'PLACEHOLDER')
    assert 'L' in sev_basis and 'L' in block_basis
    # 不得挪用既有码的 message（挪用即虚报，同 MISSING_FACT_RULE_APPLIED 的先例）。
    for other in ('NOT_ASSESSED', 'EV_D_NOT_ASSESSED', 'GR_VERSION_BREAK',
                  'EVIDENCE_CARD_MISSING'):
        assert message(name) != message(other), other
# --- RC-1（v1.2 §3）G-15 reason_code 六条接线：消费点行为断言 -------------------
# 派工锚点：docs/RUN-UNATTENDED-v1.2.md §0/§3-RC-1 与 CONSUMPTION-TODO（R15B2 登记）
# 第 2/3(模块侧)/4/5/7/9 条。第 2 条（重复设计卡键，dsm/preflight.py:320 的字典推导
# 曾静默取后一行）与第 3 条模块侧（dsm/triangulation.py 的 _pair/verdict 回 None
# 不带码）就在 RC-1 写集内，下面按真实行为断言：码必须真的被记、真的进 flags、
# 真的被 audit.json / triangulation.md 消费。第 4/5 条消费点在 dsm/weights_combine.py、
# 第 9 条在 dsm/attainment.py、第 7 条换码还要求同步 tests/test_preflight.py:237-244
# 的 CONFIG_SEMANTIC_ERROR 检索行——四处均在 RC-1 写集之外（§0 铁律：写集外不改），
# 已按 §5 差异表上报主控；本节只钉死注册表侧已登记的消费点归属，不为写集外模块
# 编造行为断言（R-12），也不弱化任何既有断言（R-14）。

import json  # noqa: E402  （RC-1 追加节自含导入，不动节区外既有行）
from datetime import date, datetime  # noqa: E402
from decimal import Decimal  # noqa: E402

from dsm import preflight, triangulation  # noqa: E402
from dsm.io_loaders import Inputs  # noqa: E402
from dsm.models import (AnchorSetDoc, DesignCardRow, GradeLedgerRow,  # noqa: E402
                        MetricDictRow, MetricFactRow, NormalizedFrame, NormalizedRow,
                        PoolKey, RedlineRow, ScoreFrame, ScoreRow, StrategyMasterRow,
                        WeightProvenance, WeightVersionDoc)
from dsm.numeric import D, eq_tol  # noqa: E402
from dsm.reports import AllFrames, GateStatus, render_triangulation_md  # noqa: E402

RC1_G15_CODES = ('DESIGN_CARD_DUPLICATE_KEY', 'SPEARMAN_ZERO_VARIANCE',
                 'H2_DIM_WEIGHT_BELOW_FLOOR', 'H3_METRIC_WEIGHT_BELOW_FLOOR',
                 'H5_SHIFT_FROM_AHP_EXCEEDED', 'REDLINE_EXCLUDED_FROM_ENTROPY',
                 'WEIGHT_DICT_MISALIGNED', 'MISSING_FACT_RULE_APPLIED')
# _BASIS 消费点列的期望归属文件（登记事实，非接线承诺；接线归属见上节说明）。
RC1_G15_CONSUMERS = {
    'DESIGN_CARD_DUPLICATE_KEY': 'preflight.py',        # CONSUMPTION-TODO 第 2 条
    'SPEARMAN_ZERO_VARIANCE': 'triangulation.py',       # 第 3 条（模块侧）
    'H2_DIM_WEIGHT_BELOW_FLOOR': 'weights_combine.py',  # 第 4 条（RC-1 写集外）
    'H3_METRIC_WEIGHT_BELOW_FLOOR': 'weights_combine.py',
    'H5_SHIFT_FROM_AHP_EXCEEDED': 'weights_combine.py',
    'REDLINE_EXCLUDED_FROM_ENTROPY': 'weights_combine.py',   # 第 5 条（写集外）
    'WEIGHT_DICT_MISALIGNED': 'preflight.py',           # 第 7 条（写集外测试未同步前不换码）
    'MISSING_FACT_RULE_APPLIED': 'attainment.py',       # 第 9 条（写集外）
}


def test_rc1_g15_six_wiring_codes_all_carry_registered_consumer_pointers():
    for name in RC1_G15_CODES:
        assert is_registered(name), name
        sev_basis, block_basis, consumer = basis(name)
        assert RC1_G15_CONSUMERS[name] in consumer, (name, consumer)


def test_rc1_preflight_tables_wire_the_duplicate_key_code():
    value = RC.DESIGN_CARD_DUPLICATE_KEY.value
    assert value in preflight.RUN_BLOCKING_CODES
    assert preflight.DISCLOSURE[value] == preflight.AUDIT_ONLY == 'audit + 退出码 2'
    assert blocks_run(value) is True
    assert severity(value) is Severity.BLOCK


# ---- preflight 构造器（字段逐字照 dsm/models.py，R-2；数值为手算构造，R-14）----
_P_REF = date(2024, 3, 31)


def _p_weights():
    return WeightVersionDoc(
        weight_version_id='WV-2024', status='FROZEN',
        effective_from=date(2024, 1, 1), effective_to=date(2024, 12, 31),
        level1_weights={'D1': Decimal('0.6'), 'D2': Decimal('0.4')},
        level2_weights={'D1': {'M1': Decimal('0.5'), 'M2': Decimal('0.5')},
                        'D2': {'M3': Decimal('1.0')}},
        approved_by='李四', approved_date=date(2024, 1, 5),
        provenance=WeightProvenance(kind='AHP_ONLY', whatif_run_id='WIF-2024-01',
                                    approved_by='张三', approved_date=date(2024, 1, 5),
                                    effective_from=date(2024, 1, 1),
                                    effective_to=date(2024, 12, 31)))


def _p_metric(metric_id, dim_code='D1'):
    return MetricDictRow(metric_id=metric_id, metric_name=metric_id, dim_code=dim_code,
                         numerator_def='分子口径', denominator_def=None, time_window='30D',
                         dedup_rule='USER', missing_rule='SKIP',
                         outlier_rule='CLIP_P1_P99', attainment_formula='RATIO_DIRECT',
                         direction=1, unit='RATIO', target_value=None,
                         target_basis='budget', is_redline=False, owner_name='王五',
                         signoff_status='SIGNED', signoff_date=date(2024, 1, 2),
                         dim_signoff_status='SIGNED', dict_version='DV-1',
                         caliber_version='CAL-1')


def _p_fact(metric_id):
    return MetricFactRow(strategy_id='S1', version_id='V1', period='2024Q1',
                         metric_id=metric_id, value_num=Decimal('0.5'), value_den=None,
                         value=Decimal('0.5'), data_quality_flag='OK',
                         snapshot_time=datetime(2024, 3, 31, 8, 0, 0),
                         data_as_of=_P_REF, source_table='dw.fact',
                         caliber_version='CAL-1')


def _p_card(card_status):
    return DesignCardRow(strategy_id='S1', version_id='V1', direct_goal='提升转化',
                         process_metrics=('M1',), result_metrics=('M2',),
                         observation_window='90D', data_source='dw',
                         data_timeliness='T+1', eval_method='AB_TEST',
                         control_arrangement='CONCURRENT_CONTROL',
                         success_criteria='lift >= 1%', risk_constraints='无',
                         eval_owner='钱七', card_status=card_status)


def _p_world(cards):
    inputs = Inputs(
        strategy_master=(StrategyMasterRow(
            strategy_id='S1', version_id='V1', strategy_name='S1', biz_domain='信用卡',
            scene_code='SC1', segment_type='EXISTING', online_date=date(2023, 6, 1),
            offline_date=None, owner_dept='部门', owner_name='赵六', status='ACTIVE',
            version_change_note=None),),
        metric_dict=(_p_metric('M1'), _p_metric('M2'), _p_metric('M3', 'D2')),
        metric_facts=tuple(_p_fact(m) for m in ('M1', 'M2', 'M3')),
        design_cards=cards,
        redlines=(RedlineRow(metric_id='M1', level='HARD', comparator='GT',
                             threshold_value=Decimal('0.5'), forced_grade='L4',
                             reason_code='REDLINE_HARD_M1', waiver_allowed=False),),
        previous_ledger=(GradeLedgerRow(strategy_id='S1', version_id='V1',
                                        period='2023Q4', grade='L2', ledger_complete=True,
                                        usable_for_elimination=True),))
    config = preflight.PreflightConfig(
        period='2024Q1', period_ref_date=_P_REF, weight_version=_p_weights(),
        anchor_set=AnchorSetDoc(anchor_set_id='A1', strategy_ids=('S1',),
                                effective_from=date(2024, 1, 1),
                                effective_to=date(2024, 12, 31),
                                rationale='覆盖各域的稳定策略'),
        signed_signoff_status=('SIGNED',),
        missing_rate_warn=Decimal('0.1'), missing_rate_block=Decimal('0.3'))
    return inputs, config


def _p_ctx():
    return {'run_id': 'RUN-2024Q1-RC1', 'run_at': datetime(2024, 4, 1, 9, 0, 0),
            'dsm_version': 'v1.2', 'design_version': 'DSM-v1.2',
            'cel_contract_version': 'CEL-0', 'config_snapshot_sha256': 'ab' * 32,
            'input_fingerprints': {}, 'sensitivity_schemes': (), 'seed': None,
            'reproducibility_hash': 'cd' * 32}


def _p_dup(result):
    return tuple(f for f in result.findings
                 if f.reason_code == RC.DESIGN_CARD_DUPLICATE_KEY.value)


def test_rc1_duplicate_design_card_key_records_code_and_unmasks_missing():
    '''CONSUMPTION-TODO 第 2 条（M18 [L1102]）：同 (strategy_id, version_id) 两张卡
    必须真的出码，不得再静默取后一行——MISSING 在前时旧推导会把缺失卡盖成 COMPLETE。'''
    inputs, config = _p_world((_p_card('MISSING'), _p_card('COMPLETE')))
    result = preflight.run(inputs, config)
    dup = _p_dup(result)
    assert len(dup) == 1, '重复键必须逐键出码，不许零码也不许双码'
    finding = dup[0]
    assert finding.code == 'C-08'
    assert finding.scope == 'strategy:S1 version:V1'
    assert finding.severity is Severity.BLOCK and finding.blocks_run is True
    assert finding.disclosure == preflight.AUDIT_ONLY
    assert '出现 2' in finding.detail and 'MISSING' in finding.detail \
        and 'COMPLETE' in finding.detail
    missing = tuple(f for f in result.findings
                    if f.reason_code == RC.EVIDENCE_CARD_MISSING.value)
    assert len(missing) == 1, 'MISSING 卡不得被后一行 COMPLETE 静默盖掉（V-14）'
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2


def test_rc1_duplicate_key_reversed_order_blocks_with_first_row_kept():
    inputs, config = _p_world((_p_card('COMPLETE'), _p_card('MISSING')))
    result = preflight.run(inputs, config)
    assert len(_p_dup(result)) == 1
    assert result.status == preflight.STATUS_BLOCK and result.exit_code == 2
    assert not tuple(f for f in result.findings
                     if f.reason_code == RC.EVIDENCE_CARD_MISSING.value), \
        '索引以首行为准：拒绝的是重复键本身，不反报一个不存在的缺失'
    inputs, config = _p_world((_p_card('COMPLETE'),))
    result = preflight.run(inputs, config)
    assert _p_dup(result) == () and result.findings == ()
    assert result.status == preflight.STATUS_PASS and result.exit_code == 0


def test_rc1_duplicate_key_finding_is_consumed_by_audit_outlet(tmp_path):
    '''每个降级都能被出口消费：BLOCK 码的出口是 audit.json（M22 [L917] 三条硬行为），
    execute 必须只产 audit.json、退出码 2，且文件内逐字可见 reason_code + message。'''
    inputs, config = _p_world((_p_card('MISSING'), _p_card('COMPLETE')))
    exit_code, result, paths = preflight.execute(inputs, config, tmp_path, _p_ctx())
    assert exit_code == 2 and len(paths) == 1 and paths[0].name == 'audit.json'
    payload = json.loads(paths[0].read_text(encoding='utf-8'))
    flat = '\n'.join(f['message'] for f in payload['preflight_findings'])
    assert RC.DESIGN_CARD_DUPLICATE_KEY.value in flat
    assert message(RC.DESIGN_CARD_DUPLICATE_KEY.value) in flat
    assert '披露=audit + 退出码 2' in flat


# ---- triangulation 构造器（与 tests/test_triangulation.py 的 golden 输入同源：
# 数值手算构造，R-14；字段名逐字照 dsm/models.py，R-2）----
_T_PERIOD, _T_VER = '2026Q1', 'v1'
_T_SPEC = {'S1': {'M1': '2', 'M2': '3'}, 'S2': {'M1': '4', 'M2': '12'},
           'S3': {'M1': '8', 'M2': '9'}}
_T_DIRS = {'M1': 1, 'M2': 1}


def _t_nframe():
    rows = [NormalizedRow(strategy_id=sid, version_id=_T_VER, period=_T_PERIOD,
                          metric_id=m,
                          pool_key=PoolKey(biz_domain='RETAIL', evidence_class='A'),
                          norm_value=D(v), method='min_max', anchor_used=False,
                          reason_code=None)
            for sid, row in _T_SPEC.items() for m, v in sorted(row.items())]
    return NormalizedFrame(rows=tuple(rows))


def _t_sframe(comps):
    rows = [ScoreRow(strategy_id=sid, version_id=_T_VER, period=_T_PERIOD,
                     composite_absolute=D(c), composite_relative=None,
                     dim_absolute={}, dim_relative={}, coverage=D('1'),
                     weight_version_id='W2026', operator='LINEAR')
            for sid, c in comps.items()]
    return ScoreFrame(rows=tuple(rows))


def _t_wdoc():
    return WeightVersionDoc(
        weight_version_id='W2026', status='FROZEN',
        effective_from=date(2026, 1, 1), effective_to=date(2026, 12, 31),
        level1_weights={'D1': D('1')},
        level2_weights={'D1': {'M1': D('0.5'), 'M2': D('0.5')}},
        approved_by='评价管理委员会', approved_date=date(2026, 1, 1))


def _t_cfg(rho='1', threshold='0.8'):
    return {'triangulation': {'enabled': True, 'gra_norm': 'initial',
                              'rho': D(rho), 'divergence_threshold': D(threshold)}}


def _t_run(comps):
    return triangulation.run(_t_sframe(comps), _t_nframe(), _t_wdoc(), _t_cfg(),
                             directions=_T_DIRS)


def test_rc1_zero_variance_run_flags_spearman_code_instead_of_silence():
    '''CONSUMPTION-TODO 第 3 条（模块侧，triangulation.py:380-388/:420-426 实测位）：
    main 零方差 -> _pair 捕 DivisionUndefinedError 回 None、verdict 在 mean_rho None
    时回 None——两处 None 现在必须带 SPEARMAN_ZERO_VARIANCE 进 flags；「不编数」的
    正确行为逐字保留（rho/agreement 仍为 None，verdict(None) 仍回 None）。'''
    report = _t_run({'S1': '0.5', 'S2': '0.5', 'S3': '0.5'})
    assert report.rho_main_topsis is None and report.rho_main_gra is None
    assert report.mean_rho is None and report.agreement is None
    assert report.rho_topsis_gra is not None
    assert report.flags == (RC.SPEARMAN_ZERO_VARIANCE.value,)
    assert severity(RC.SPEARMAN_ZERO_VARIANCE.value) is Severity.WARN
    assert blocks_run(RC.SPEARMAN_ZERO_VARIANCE.value) is False
    assert triangulation.verdict(None, D('0.8')) is None
    assert not triangulation.is_vetoed(report)


def test_rc1_spearman_code_reaches_rendered_triangulation_report():
    '''消费出口核验（§3 验收第 2 条）：flags 里的码必须出现在 triangulation.md，
    三角标记与「Spearman 相关无定义」两处披露位都在，渲染层 blocks_run 照注册表。'''
    report = _t_run({'S1': '0.5', 'S2': '0.5', 'S3': '0.5'})
    md = render_triangulation_md(AllFrames(
        gate_status=GateStatus(g5_dispute_source_review_signed=True,
                               g7_governance_config_signed=True),
        triangulation=report))
    assert '- 三角标记：' + RC.SPEARMAN_ZERO_VARIANCE.value in md
    assert 'Spearman 相关无定义' in md
    assert md.count(RC.SPEARMAN_ZERO_VARIANCE.value) >= 2
    assert 'blocks_run=false' in md  # fmt_bool 小写口径（reports.py:157-158）


def test_rc1_defined_run_flags_stay_conclusion_code_only():
    '''不过度出码：三对 rho 全有值且达阈（同序 -> rho=1 >= 0.8）时 flags 只含结论码，
    与基线行为逐字一致（R-14：补码不许把正常路径也染色）。'''
    report = _t_run({'S1': '0.5', 'S2': '0.8', 'S3': '0.875'})
    assert eq_tol(report.rho_main_topsis, D('1'))
    assert report.agreement == RC.METHOD_AGREEMENT.value
    assert report.flags == (RC.METHOD_AGREEMENT.value,)
