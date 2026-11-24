'''dsm.audit -- L6 Step 9: manifest, fingerprints, the canonical serialization of
[L1053] and the reproducibility_hash of [L1052]. Signature verbatim from [L1050];
AuditBundle already carries the fifteen [L1051] items as sixteen columns, so this
module fills them in and re-declares no contract.

The five rules of [L1053] live in ONE function, canonical_text, and every hash here
is a sha256 over its output:
  1 Decimal: q12 then stringify -- fixed point, twelve decimals, never an exponent
  2 float: numeric.from_float first ([L1268]), so no float byte is ever hashed
  3 mappings: keys explicitly sorted ([L1272]), independent of insertion order and
    of PYTHONHASHSEED
  4 sequences: business key order, never insertion order -- rows sort on
    (strategy_id, version_id, period), the canonical text breaking a tie
  5 None writes null, the empty string writes empty, and the two never collide

Environment quantities never enter the hash: [L1640] makes it the criterion of a
second person's re-run on a fresh clone with no network, so run_id ([L1091]), run_at
([L1089]), paths, host names and output file names stay in the bundle only, and the
payload is exactly what [L1052] names -- score_card core columns, grade_ledger grade
columns, weight version id -- plus a schema tag. H-8: no clock, no randomness; run_at
/ period / seed arrive through RunContext, which ruling 31 keeps out of models.py.
[L1054]: exit_code is an ordinary input, so a failed run still yields a full bundle.
Guards: G-12 (same input twice -> same hash), V-11 (an undecided new column fails).
'''
from __future__ import annotations

import hashlib
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict

from dsm import numeric
from dsm.models import (
    AuditBundle, DowngradeAction, GradeLedgerRow, InputFingerprints,
    InputTableFingerprint, PreflightFinding, ScoreCardRow, SchemeName, StrictInt)
from dsm.numeric import q12

LAYER = 'L6'                            # [L809] module table: audit sits at L6
HASH_SCHEMA = 'dsm.reproducibility/v1'  # tagged so a payload change stays visible
ENCODING = 'utf-8'                      # fixed: no hash depends on the locale
SHA256_HEX = '0123456789abcdef'
SHA256_LENGTH = 64


class AuditError(ValueError):
    '''An audit contract violation: an unserializable type, a malformed SHA256, a
    file that is not UTF-8. Never a silent fallback (R5).'''


class RunContext(BaseModel):
    '''What the CLI injects for one run: [L1089] --run-at / --period / --seed, the
    run identity and version quartet of [L1051] items 1-7, the findings / downgrades
    / exit_code of items 12-14 and the two key results the [L1052] hash is taken
    over. models.py ruling 31 deliberately models no RunContext, so the carrier
    lives here at L6; exit_code keeps the open set of [L1080]-[L1087].'''

    model_config = ConfigDict(frozen=True, extra='forbid')

    run_id: str
    run_at: datetime
    period: str
    dsm_version: str
    design_version: str
    cel_contract_version: str
    weight_version_id: str
    seed: StrictInt | None = None
    sensitivity_schemes: tuple[SchemeName, ...] = ()
    preflight_findings: tuple[PreflightFinding, ...] = ()
    downgrade_actions: tuple[DowngradeAction, ...] = ()
    exit_code: StrictInt = 0
    score_card: tuple[ScoreCardRow, ...] = ()
    grade_ledger: tuple[GradeLedgerRow, ...] = ()


# [L1052] "the core columns of score_card": 34 of the 35 columns of
# [L1612]-[L1626], each one a reproducible business result; the single exception is
# run_id ([L1091] a new directory per run). V-11 reads both tuples against
# ScoreCardRow.model_fields, so a new column nobody decided about fails the tests
# instead of silently staying out of the hash.
SCORE_CARD_HASH_FIELDS = (
    'anchor_set_id', 'cap_reason', 'capped_flag', 'composite_absolute',
    'composite_relative', 'dict_version', 'eligible_for_L1_library',
    'estimator_method', 'evidence_class', 'evidence_reason', 'evidence_source',
    'flip_under_pct10', 'flip_under_pct20', 'grade', 'grade_reason_codes',
    'incremental_ci_lower', 'incremental_ci_upper', 'incremental_value',
    'interpretation_limit', 'l1_gate_reasons', 'per_dim', 'per_metric', 'period',
    'pool_size', 'rank_in_pool', 'ranking_pool', 'redline_flags', 'redline_pass',
    'stability_label', 'strategy_id', 'usable_for_elimination',
    'value_captured_minor', 'version_id', 'weight_version_id')
SCORE_CARD_NON_HASHED = ('run_id',)
# [L1052] "the grade columns of grade_ledger": the locator trio plus grade and
# previous_grade, the change the [L1221] grain is about. The other nine stay out:
# the [L1630]-[L1633] human sign-off columns do not exist yet when a second person
# re-runs (V-8), ledger_complete is the S6 marker of [L1634], and
# usable_for_elimination is already hashed on the score_card row ([L1625]).
GRADE_LEDGER_HASH_FIELDS = (
    'grade', 'period', 'previous_grade', 'strategy_id', 'version_id')
GRADE_LEDGER_NON_HASHED = (
    'archive_ref', 'decided_action', 'decision_note', 'deadline',
    'ledger_complete', 'owner_dept', 'owner_name', 'recommended_action',
    'usable_for_elimination')
ROW_SORT_KEY = ('strategy_id', 'version_id', 'period')  # rule 4, [L1220]-[L1221]
# Rule 5 needs an injective text form: the structural characters are escaped.
_ESCAPES = str.maketrans({
    '\\': '\\\\', ',': '\\,', '=': '\\=',
    '{': '\\{', '}': '\\}', '[': '\\[', ']': '\\]'})


def canonical_text(value) -> str:
    '''The one canonical serializer of [L1053]. Pure: the same value gives the same
    bytes on any machine, in any dict order, under any PYTHONHASHSEED.'''
    if value is None:
        return 'null'                                       # rule 5
    if isinstance(value, BaseModel):
        return ('obj:' + type(value).__name__ + canonical_text(
            {n: getattr(value, n) for n in type(value).model_fields}))
    if isinstance(value, Enum):
        return canonical_text(value.value)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, Decimal):
        return 'n' + str(q12(value))                        # rule 1
    if isinstance(value, float):
        return canonical_text(numeric.from_float(value))    # rule 2
    if isinstance(value, int):
        return 'i' + str(value)
    if isinstance(value, str):
        return 'empty' if value == '' else 's:' + value.translate(_ESCAPES)
    if isinstance(value, (datetime, date)):
        return ('dt:' if isinstance(value, datetime) else 'd:') + value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return 'x:' + bytes(value).hex()
    if isinstance(value, Mapping):
        return '{' + ','.join(
            canonical_text(k) + '=' + canonical_text(value[k])
            for k in _sorted_keys(value)) + '}'             # rule 3
    if isinstance(value, (list, tuple)):
        return '[' + ','.join(
            sorted(canonical_text(v) for v in value)) + ']'  # rule 4
    raise AuditError('canonical_text has no rule for ' + type(value).__name__)


def _sorted_keys(mapping):
    '''Rule 3: sort on the key's own text rather than on its type tag.'''
    return sorted(mapping, key=lambda k: str(k.value) if isinstance(k, Enum)
                  else (k if isinstance(k, str) else canonical_text(k)))


def sha256_text(text: str) -> str:
    '''sha256 over the fixed encoding; no payload carries a newline of its own.'''
    return hashlib.sha256(text.encode(ENCODING)).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_sha256(value, where: str) -> str:
    '''The 64-hex format check models.py hands to audit.py; without it the [L1640]
    step-1 verification of a re-run would be meaningless.'''
    text = str(value)
    if len(text) != SHA256_LENGTH or any(c not in SHA256_HEX for c in text):
        raise AuditError(where + ' needs a 64 char lowercase hex sha256, got: '
                         + text)
    return text


def file_fingerprint(path, *, has_header: bool = True) -> InputTableFingerprint:
    '''[L888] one file, one SHA256 plus a row count, over the raw bytes: a CRLF copy
    of the same table hashes differently, which is what a re-run verification wants.
    Rows count on LF, a trailing newline adds none, has_header drops the header.'''
    data = Path(path).read_bytes()
    try:
        text = data.decode(ENCODING)
    except UnicodeDecodeError as exc:
        raise AuditError('input file is not ' + ENCODING + ': ' + str(path)) from exc
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    rows = len(lines) - (1 if has_header else 0)
    return InputTableFingerprint(sha256=sha256_bytes(data), row_count=max(rows, 0))


def fingerprint_inputs(paths, *, has_header: bool = True) -> InputFingerprints:
    '''[L891] ruling 15 alias, keyed sorted. Which names the eight tables carry is
    io_loaders' decision (S3), so this module invents no file name.'''
    return {name: file_fingerprint(paths[name], has_header=has_header)
            for name in _sorted_keys(paths)}


def fingerprint_outputs(paths) -> dict:
    '''[L1051] item 10: file name -> SHA256. The key is Path.name and never the
    directory, because an absolute path is an environment quantity: the second
    person re-runs in another clone and audit.json still has to line up.'''
    items = list(paths.values()) if isinstance(paths, Mapping) else list(paths)
    found = {}
    for item in items:
        found[Path(item).name] = sha256_bytes(Path(item).read_bytes())
    return {name: found[name] for name in sorted(found)}


def config_snapshot_sha256(config) -> str:
    '''[L1051] item 8. config may be a pydantic model, a Mapping, raw text (one
    whole YAML) or anything with a __dict__; all go through canonical_text, so one
    configuration hashes identically everywhere.'''
    if isinstance(config, str):
        return sha256_text(config)
    if isinstance(config, (bytes, bytearray)):
        return sha256_bytes(bytes(config))
    if isinstance(config, (BaseModel, Mapping)):
        return sha256_text(canonical_text(config))
    if hasattr(config, '__dict__'):
        return sha256_text(canonical_text(vars(config)))
    raise AuditError('config snapshot cannot be canonicalized: '
                     + type(config).__name__)


def _ordered(rows, fields):
    '''Rule 4: the [L1220]-[L1221] business key first, the canonical text as
    tie-break, so the payload is insertion-order independent throughout.'''
    items = [(tuple(getattr(row, n) for n in ROW_SORT_KEY),
              {name: getattr(row, name) for name in fields}) for row in rows]
    items.sort(key=lambda item: (item[0], canonical_text(item[1])))
    return tuple(projection for _, projection in items)


def hash_payload(score_card, grade_ledger, weight_version_id) -> str:
    '''The [L1052] payload under a schema tag: score_card core columns,
    grade_ledger grade columns, weight version id. No run_id, no run_at, no path,
    no host name, no output file name.'''
    return canonical_text({
        'schema': HASH_SCHEMA,
        'weight_version_id': str(weight_version_id),
        'score_card': _ordered(score_card, SCORE_CARD_HASH_FIELDS),
        'grade_ledger': _ordered(grade_ledger, GRADE_LEDGER_HASH_FIELDS)})


def reproducibility_hash(score_card, grade_ledger, weight_version_id) -> str:
    '''[L1052] and [L1640] step 3: the value a second person compares exactly.'''
    return sha256_text(hash_payload(score_card, grade_ledger, weight_version_id))


def build_manifest(inputs_fp, config, run_ctx, outputs_fp) -> AuditBundle:
    '''[L1050] verbatim. Fills the sixteen columns out of the four arguments and
    nothing else: no clock, no I/O beyond what the caller fingerprinted, no business
    number invented. Both maps are re-keyed sorted (rule 3), every digest is format
    checked, and a failed run is an ordinary input ([L1054]).'''
    inputs = {n: inputs_fp[n] for n in _sorted_keys(inputs_fp)}
    outputs = {n: outputs_fp[n] for n in _sorted_keys(outputs_fp)}
    for name in _sorted_keys(inputs):
        check_sha256(inputs[name].sha256, 'input_fingerprints[' + str(name) + ']')
    for name in _sorted_keys(outputs):
        check_sha256(outputs[name], 'output_fingerprints[' + str(name) + ']')
    config_sha = config_snapshot_sha256(config)
    check_sha256(config_sha, 'config_snapshot_sha256')
    return AuditBundle(
        run_id=run_ctx.run_id, run_at=run_ctx.run_at, period=run_ctx.period,
        dsm_version=run_ctx.dsm_version, design_version=run_ctx.design_version,
        cel_contract_version=run_ctx.cel_contract_version, seed=run_ctx.seed,
        weight_version_id=run_ctx.weight_version_id, exit_code=run_ctx.exit_code,
        config_snapshot_sha256=config_sha, input_fingerprints=inputs,
        output_fingerprints=outputs,
        sensitivity_schemes=tuple(sorted(run_ctx.sensitivity_schemes)),
        preflight_findings=tuple(sorted(run_ctx.preflight_findings,
                                        key=canonical_text)),
        downgrade_actions=tuple(sorted(run_ctx.downgrade_actions,
                                       key=canonical_text)),
        reproducibility_hash=reproducibility_hash(
            run_ctx.score_card, run_ctx.grade_ledger, run_ctx.weight_version_id))


def serialize_bundle(bundle) -> str:
    '''The audit.json body: the bundle's canonical text, UTF-8, no trailing newline;
    writing it out is the CLI's job (S6). V-11: a new AuditBundle column appears
    automatically, an unserializable one raises AuditError instead of vanishing.'''
    return canonical_text(bundle)


def rerun_steps(bundle) -> tuple:
    '''The four re-run steps of [L1640]. Every value in them comes out of the bundle
    itself, so they read the same on any machine: no local path, no host name, no
    current time.'''
    seed = 'null' if bundle.seed is None else str(bundle.seed)
    tables = ','.join(str(n) for n in _sorted_keys(bundle.input_fingerprints))
    return (
        '步骤一 取同一批输入文件与配置目录，逐个校验 SHA256 与行数同 audit.json 的 '
        'input_fingerprints 一致（表：' + tables + '），并校验配置全量快照 '
        'config_snapshot_sha256=' + bundle.config_snapshot_sha256,
        '步骤二 用同一 --run-at 与 --seed 执行 dsm score：--period ' + bundle.period
        + ' --run-at ' + bundle.run_at.isoformat() + ' --seed ' + seed,
        '步骤三 比对 reproducibility_hash，必须精确相等：' + bundle.reproducibility_hash,
        '步骤四 金额与整数字段精确相等，比率字段差值不大于 1e-12（V-3 / G-12）')
