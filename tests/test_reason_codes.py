'''Tests for dsm.reason_codes -- registry completeness and lookup semantics.

Design doc 3.3.2 plus principles R5 (no silent downgrade) and P-8 (business code
must reference RC members, never string literals). A reason_code that is not in
this registry cannot be emitted, so the registry IS the disclosure contract.
'''
import pytest

from dsm.reason_codes import (
    RC,
    Severity,
    _DEFS,
    _META,
    all_codes,
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
