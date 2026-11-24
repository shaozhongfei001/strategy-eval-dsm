'''Tests for dsm.audit -- the F2 guard tests G-12 and V-11 ([L1055]).

G-12: the same input run twice gives the same reproducibility_hash, the hash
survives a change of machine / directory / run_id / run_at, and one changed
semantic bit changes it. V-11: a new output column that nobody decided into or
out of the serializer fails here.

The golden payload below is derived by hand from the five rules of [L1053] with
the field names copied out of dsm/models.py; it is never read back from the
implementation (R-14). The two sha256 literals are the published FIPS 180
examples for the empty string and for 'abc'.
'''
import ast
import hashlib
import pathlib
from datetime import datetime, timezone

import pytest

from dsm import audit, numeric
from dsm.models import (
    AuditBundle, DowngradeAction, GradeLedgerRow, InputTableFingerprint,
    PreflightFinding, ScoreCardMetricCell, ScoreCardRow)
from dsm.numeric import D
from dsm.reason_codes import RC, Severity

RUN_AT = datetime(2025, 4, 1, 9, 30, tzinfo=timezone.utc)
WV = 'WV-2025Q1'
CONFIG = {'alpha': D('0.5'), 'weight_version_id': WV}


def _card(**over):
    '''One score_card row, field names copied verbatim out of models.py.'''
    base = dict(
        strategy_id='S01', version_id='V1', period='2025Q1',
        weight_version_id=WV, dict_version='MD-1', anchor_set_id='AS-1',
        run_id='RUN-0001', per_metric={}, per_dim={},
        composite_absolute=D('0.625'), composite_relative=None,
        evidence_class='A', evidence_reason=RC.EVIDENCE_CARD_MISSING.value,
        evidence_source='CARD_ONLY', interpretation_limit=None,
        redline_pass=True, redline_flags=(), grade='L3', grade_reason_codes=(),
        capped_flag=False, cap_reason=None, ranking_pool=None,
        rank_in_pool=None, pool_size=None, eligible_for_L1_library=True,
        l1_gate_reasons=(), stability_label=None, flip_under_pct10=None,
        flip_under_pct20=None, usable_for_elimination=True,
        incremental_value=None, incremental_ci_lower=None,
        incremental_ci_upper=None, estimator_method=None,
        value_captured_minor=None)
    base.update(over)
    return ScoreCardRow(**base)


def _ledger(**over):
    '''One grade_ledger row. The three evidence codes of [L982] are all
    exception codes, so an A class row has no matching registered code and the
    fixture borrows one: audit.py only needs a registered code, S5 owns which.'''
    base = dict(strategy_id='S01', version_id='V1', period='2025Q1',
                grade='L3', previous_grade=None, ledger_complete=True,
                usable_for_elimination=True)
    base.update(over)
    return GradeLedgerRow(**base)


def _ctx(**over):
    base = dict(run_id='RUN-0001', run_at=RUN_AT, period='2025Q1',
                dsm_version='0.1.0', design_version='v1.1-FINAL',
                cel_contract_version='CEL-0', weight_version_id=WV,
                seed=20250401, sensitivity_schemes=('OAT_10', 'MC'),
                exit_code=0, score_card=(_card(),), grade_ledger=(_ledger(),))
    base.update(over)
    return audit.RunContext(**base)


def _write_inputs(tmp_path):
    '''Two stand-in input tables (io_loaders is not implemented yet).'''
    first = tmp_path / 'T1_strategy_master.csv'
    first.write_text('strategy_id,version_id\nS01,V1\nS02,V1\n',
                     encoding='utf-8')
    second = tmp_path / 'T2_metric_dict.csv'
    second.write_text('metric_id,unit\nM01,RATIO\n', encoding='utf-8')
    return {'T1_strategy_master': first, 'T2_metric_dict': second}


# ---------------------------------------------------------------------------
# The hand-derived golden payload of [L1052] / [L1053] for the fixture above:
# keys sorted by ASCII, Decimal as fixed point with twelve decimals, None as
# null, empty containers as [] and {}, and run_id left out.
# ---------------------------------------------------------------------------
GOLDEN_SCORE_CARD = (
    '{s:anchor_set_id=s:AS-1'
    ',s:cap_reason=null'
    ',s:capped_flag=false'
    ',s:composite_absolute=n0.625000000000'
    ',s:composite_relative=null'
    ',s:dict_version=s:MD-1'
    ',s:eligible_for_L1_library=true'
    ',s:estimator_method=null'
    ',s:evidence_class=s:A'
    ',s:evidence_reason=s:EVIDENCE_CARD_MISSING'
    ',s:evidence_source=s:CARD_ONLY'
    ',s:flip_under_pct10=null'
    ',s:flip_under_pct20=null'
    ',s:grade=s:L3'
    ',s:grade_reason_codes=[]'
    ',s:incremental_ci_lower=null'
    ',s:incremental_ci_upper=null'
    ',s:incremental_value=null'
    ',s:interpretation_limit=null'
    ',s:l1_gate_reasons=[]'
    ',s:per_dim={}'
    ',s:per_metric={}'
    ',s:period=s:2025Q1'
    ',s:pool_size=null'
    ',s:rank_in_pool=null'
    ',s:ranking_pool=null'
    ',s:redline_flags=[]'
    ',s:redline_pass=true'
    ',s:stability_label=null'
    ',s:strategy_id=s:S01'
    ',s:usable_for_elimination=true'
    ',s:value_captured_minor=null'
    ',s:version_id=s:V1'
    ',s:weight_version_id=s:WV-2025Q1}')
GOLDEN_GRADE_LEDGER = (
    '{s:grade=s:L3'
    ',s:period=s:2025Q1'
    ',s:previous_grade=null'
    ',s:strategy_id=s:S01'
    ',s:version_id=s:V1}')
GOLDEN_PAYLOAD = (
    '{s:grade_ledger=[' + GOLDEN_GRADE_LEDGER + ']'
    ',s:schema=s:dsm.reproducibility/v1'
    ',s:score_card=[' + GOLDEN_SCORE_CARD + ']'
    ',s:weight_version_id=s:WV-2025Q1}')


def test_g12_same_input_twice_gives_the_same_hash(tmp_path):
    fingerprints = audit.fingerprint_inputs(_write_inputs(tmp_path))
    outputs = {'score_card.csv': 'b' * 64}
    one = audit.build_manifest(fingerprints, CONFIG, _ctx(), outputs)
    two = audit.build_manifest(dict(fingerprints), dict(CONFIG), _ctx(),
                               dict(outputs))
    assert one.reproducibility_hash == two.reproducibility_hash
    assert audit.serialize_bundle(one) == audit.serialize_bundle(two)
    assert len(one.reproducibility_hash) == 64


def test_g12_run_environment_never_enters_the_hash(tmp_path):
    inputs = _write_inputs(tmp_path)
    fingerprints = audit.fingerprint_inputs(inputs)
    elsewhere = tmp_path / 'elsewhere'
    elsewhere.mkdir()
    for folder in (tmp_path, elsewhere):
        (folder / 'score_card.csv').write_text('a\n', encoding='utf-8')
    away = _ctx(run_id='RUN-9999-other-host',
                run_at=datetime(2031, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                sensitivity_schemes=('MC', 'OAT_10'),
                score_card=(_card(run_id='RUN-9999-other-host'),))
    home = audit.build_manifest(
        fingerprints, CONFIG, _ctx(),
        audit.fingerprint_outputs([tmp_path / 'score_card.csv']))
    foreign = audit.build_manifest(
        fingerprints, CONFIG, away,
        audit.fingerprint_outputs([elsewhere / 'score_card.csv']))
    assert home.run_id != foreign.run_id
    assert home.run_at != foreign.run_at
    assert home.reproducibility_hash == foreign.reproducibility_hash
    assert home.output_fingerprints == foreign.output_fingerprints
    assert all('/' not in name for name in foreign.output_fingerprints)
    payload = audit.hash_payload(away.score_card, away.grade_ledger, WV)
    for environment in ('RUN-9999-other-host', away.run_at.isoformat(),
                        str(tmp_path), 'score_card.csv', 'elsewhere'):
        assert environment not in payload


def test_g12_hash_is_the_sha256_of_the_hand_written_payload():
    payload = audit.hash_payload((_card(),), (_ledger(),), WV)
    assert payload == GOLDEN_PAYLOAD
    expected = hashlib.sha256(GOLDEN_PAYLOAD.encode('utf-8')).hexdigest()
    assert audit.reproducibility_hash((_card(),), (_ledger(),), WV) == expected
    assert audit.sha256_text('') == (
        'e3b0c44298fc1c149afbf4c8996fb924'
        '27ae41e4649b934ca495991b7852b855')
    assert audit.sha256_text('abc') == (
        'ba7816bf8f01cfea414140de5dae2223'
        'b00361a396177a9cb410ff61f20015ad')


def test_g12_decimal_and_float_collapse_to_one_fixed_point_text():
    assert audit.canonical_text(D('0.625')) == 'n0.625000000000'
    assert audit.canonical_text(D('0.6250000000')) == 'n0.625000000000'
    assert audit.canonical_text(0.625) == 'n0.625000000000'
    assert audit.canonical_text(D('1E+2')) == 'n100.000000000000'
    assert 'E' not in audit.canonical_text(D('1E+2'))
    base = audit.hash_payload((_card(),), (_ledger(),), WV)
    bridged = _card(composite_absolute=numeric.from_float(0.625))
    widened = _card(composite_absolute=D('0.625000000000'))
    assert audit.hash_payload((bridged,), (_ledger(),), WV) == base
    assert audit.hash_payload((widened,), (_ledger(),), WV) == base


def test_g12_row_and_key_order_never_change_the_payload():
    one = _card(strategy_id='S01')
    two = _card(strategy_id='S02', composite_absolute=D('0.5'))
    ledger_one = _ledger()
    ledger_two = _ledger(strategy_id='S02', grade='L4')
    assert audit.hash_payload((one, two), (ledger_one, ledger_two), WV) == (
        audit.hash_payload((two, one), (ledger_two, ledger_one), WV))
    cell = ScoreCardMetricCell(actual_value=D('10'), target_value=D('20'),
                               attainment=D('0.5'))
    forward = _card(per_metric={'M01': cell, 'M02': cell})
    backward = _card(per_metric={'M02': cell, 'M01': cell})
    assert audit.hash_payload((forward,), (), WV) == (
        audit.hash_payload((backward,), (), WV))
    assert audit.config_snapshot_sha256({'a': 1, 'b': 2}) == (
        audit.config_snapshot_sha256({'b': 2, 'a': 1}))


def test_g12_none_and_empty_string_stay_different():
    assert audit.canonical_text(None) == 'null'
    assert audit.canonical_text('') == 'empty'
    assert audit.canonical_text('null') == 's:null'
    assert audit.canonical_text('empty') == 's:empty'
    assert audit.hash_payload((_card(interpretation_limit=None),), (), WV) != (
        audit.hash_payload((_card(interpretation_limit=''),), (), WV))
    assert audit.hash_payload((_card(estimator_method=None),), (), WV) != (
        audit.hash_payload((_card(estimator_method=''),), (), WV))


def test_g12_one_changed_semantic_bit_changes_the_hash():
    base = audit.reproducibility_hash((_card(),), (_ledger(),), WV)
    assert audit.reproducibility_hash((_card(),), (_ledger(grade='L4'),),
                                      WV) != base
    assert audit.reproducibility_hash((_card(),),
                                      (_ledger(previous_grade='L4'),),
                                      WV) != base
    assert audit.reproducibility_hash((_card(grade='L4'),), (_ledger(),),
                                      WV) != base
    assert audit.reproducibility_hash(
        (_card(composite_absolute=D('0.625000000001')),), (_ledger(),),
        WV) != base
    assert audit.reproducibility_hash((_card(),), (_ledger(),), 'WV-2025Q2') != base
    # the human sign-off columns of [L1630]-[L1633] and run_id stay out
    assert audit.reproducibility_hash(
        (_card(run_id='RUN-XYZ'),),
        (_ledger(decided_action='keep', owner_name='Zhang', deadline=None),),
        WV) == base


def test_g12_manifest_records_verifiable_fingerprints(tmp_path):
    paths = _write_inputs(tmp_path)
    fingerprints = audit.fingerprint_inputs(paths)
    assert sorted(fingerprints) == ['T1_strategy_master', 'T2_metric_dict']
    assert fingerprints['T1_strategy_master'].row_count == 2
    assert fingerprints['T2_metric_dict'].row_count == 1
    assert fingerprints['T1_strategy_master'].sha256 == hashlib.sha256(
        paths['T1_strategy_master'].read_bytes()).hexdigest()
    assert audit.check_sha256(fingerprints['T2_metric_dict'].sha256,
                              'T2') == fingerprints['T2_metric_dict'].sha256
    with pytest.raises(audit.AuditError):
        audit.check_sha256('z' * 64, 'input_fingerprints[T1]')
    with pytest.raises(audit.AuditError):
        audit.check_sha256('deadbeef', 'input_fingerprints[T1]')
    broken = {'T1_strategy_master': InputTableFingerprint(sha256='deadbeef',
                                                          row_count=2)}
    with pytest.raises(audit.AuditError):
        audit.build_manifest(broken, CONFIG, _ctx(), {})


def test_g12_failed_run_still_yields_a_bundle_and_rerun_steps(tmp_path):
    ctx = _ctx(exit_code=3, seed=None, score_card=(), grade_ledger=(),
               preflight_findings=(PreflightFinding(
                   code='C-01', severity=Severity.BLOCK,
                   message='input table is missing a column'),),
               downgrade_actions=(DowngradeAction(
                   reason_code=RC.EVIDENCE_CARD_MISSING.value,
                   action='judged D, no score', subject='S01'),))
    bundle = audit.build_manifest(
        audit.fingerprint_inputs(_write_inputs(tmp_path)), CONFIG, ctx, {})
    assert bundle.exit_code == 3
    assert bundle.seed is None
    assert len(bundle.preflight_findings) == 1
    assert len(bundle.downgrade_actions) == 1
    assert bundle.reproducibility_hash == audit.reproducibility_hash((), (), WV)
    steps = audit.rerun_steps(bundle)
    assert len(steps) == 4
    assert bundle.config_snapshot_sha256 in steps[0]
    assert '--run-at ' + RUN_AT.isoformat() in steps[1]
    assert '--seed null' in steps[1]
    assert bundle.reproducibility_hash in steps[2]
    assert '1e-12' in steps[3]


def test_v11_serializer_decision_covers_every_output_column():
    assert set(audit.SCORE_CARD_HASH_FIELDS) | set(
        audit.SCORE_CARD_NON_HASHED) == set(ScoreCardRow.model_fields)
    assert not set(audit.SCORE_CARD_HASH_FIELDS) & set(
        audit.SCORE_CARD_NON_HASHED)
    assert 'run_id' not in audit.SCORE_CARD_HASH_FIELDS
    assert set(audit.GRADE_LEDGER_HASH_FIELDS) | set(
        audit.GRADE_LEDGER_NON_HASHED) == set(GradeLedgerRow.model_fields)
    assert not set(audit.GRADE_LEDGER_HASH_FIELDS) & set(
        audit.GRADE_LEDGER_NON_HASHED)
    for name in audit.ROW_SORT_KEY:
        assert name in audit.SCORE_CARD_HASH_FIELDS
        assert name in audit.GRADE_LEDGER_HASH_FIELDS


def test_v11_serialized_bundle_carries_every_audit_column(tmp_path):
    bundle = audit.build_manifest(
        audit.fingerprint_inputs(_write_inputs(tmp_path)), CONFIG, _ctx(), {})
    text = audit.serialize_bundle(bundle)
    assert text == audit.canonical_text(bundle)
    for name in AuditBundle.model_fields:
        assert 's:' + name + '=' in text
    assert bundle.reproducibility_hash in text
    assert 's:run_at=dt:' + RUN_AT.isoformat() in text


def test_v11_canonical_text_refuses_a_type_it_has_no_rule_for():
    class Opaque:
        pass

    with pytest.raises(audit.AuditError):
        audit.canonical_text(Opaque())
    with pytest.raises(audit.AuditError):
        audit.canonical_text({'k': object()})
    with pytest.raises(audit.AuditError):
        audit.config_snapshot_sha256(object())


def test_g12_module_reads_no_clock_and_no_randomness():
    source = pathlib.Path(audit.__file__).read_text(encoding='utf-8')
    tree = ast.parse(source)
    banned_modules = {'time', 'random', 'os', 'socket', 'platform', 'uuid',
                      'subprocess'}
    banned_attrs = {'now', 'today', 'utcnow', 'time', 'urandom', 'gethostname',
                    'cwd', 'abspath'}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split('.')[0] not in banned_modules
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or '').split('.')[0] not in banned_modules
        elif isinstance(node, ast.Attribute):
            assert node.attr not in banned_attrs
    assert audit.LAYER == 'L6'
