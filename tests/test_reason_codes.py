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
    assert len(list(RC)) == len(all_codes()) == len(_META) == BATCH2_TOTAL
    assert len(_DEFS) == BATCH2_TOTAL, '每行 _DEFS 恰是一个码'
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
    still_there = [c for c in all_codes() if c not in BATCH2_NEW]
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
    assert tuple(sorted(_BASIS)) == tuple(sorted(BATCH2_NEW))


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
