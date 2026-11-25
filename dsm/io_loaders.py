'''dsm.io_loaders -- L1 CSV / Parquet loading, type forcing, input fingerprints.

Authority: digest M21 ([L884]-[L893]) and M18 ([L1093]-[L1215]). Two registered
acceptance items close here. B-008 / [L889]: a column whose T2 unit is MONEY_MINOR
must parse to an exact int, a fractional cell failing under reason_code C-09
(RC.MONEY_NON_INTEGER) - no truncation, no Decimal pass-through. B-010: text
literals convert only through TRUE_LITERALS / FALSE_LITERALS below; anything else
is an error with its own LoadIssue, never a default False or 0. T1 / T3 / T4 come from data/<period>/, T2 / T5 from the
config dir ([L888]); T6-T8 are YAML and stay in config.py ([L877]). A missing
previous grade_ledger is FIRST_PERIOD and nothing else ([L890]). V-9 numbers come
from dsm/numeric.py only, DataLoadError carries the [L892] exit code 4 and the
fingerprints are the [L891] second-reader baseline.
'''
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas
from pydantic import ValidationError

from . import numeric
from .models import (DesignCardRow, GradeLedgerRow, InputTableFingerprint, MetricDictRow,
                     MetricFactRow, RedlineRow, StrategyMasterRow)
from .reason_codes import RC

MONEY_MINOR, COUNT = 'MONEY_MINOR', 'COUNT'  # the int shapes of [L1138], [L1265]-[L1266]
# B-010: the complete set of literals a boolean column may carry, matched on the
# stripped lower-cased cell. TRUE / Yes / 1 land on True and nothing else does;
# there is deliberately no fallback value - an unknown literal is an error.
TRUE_LITERALS = ('true', 't', 'yes', 'y', '1')
FALSE_LITERALS = ('false', 'f', 'no', 'n', '0')
# Only these cells mean absent. 'NONE' is deliberately NOT one of them: it is a
# business literal of outlier_rule [L1135] and control_arrangement [L1167], so reading
# it as null would delete a real value.
NULL_LITERALS = ('', 'na', 'n/a', 'null')  # absent stays absent, never False / 0
LIST_SEPARATOR = ','  # [L1163] in-cell separator of the two T4 lists
BLOCKING_KINDS = ('MONEY_NOT_INTEGER', 'UNRECOGNIZED_LITERAL', 'FLOAT_IN_SOURCE',
                  'UNPARSEABLE_NUMBER', 'NON_ISO_DATE', 'MODEL_ROW_REJECTED',
                  'MISSING_FILE', 'MISSING_COLUMN')
_ISO_DATE = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}')
_ISO_DATETIME = re.compile('[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}(:[0-9]{2}([.][0-9]+)?)?')


class DataLoadError(Exception):
    '''[L892]: the load failed, the CLI of [L1089] exits with code 4.'''
    exit_code = 4  # [L892]

    def __init__(self, issues=()):
        self.issues = tuple(issues)
        super().__init__('; '.join(i.message for i in self.issues[:3]) or 'data load failed')


class CoercionError(Exception):
    '''One cell does not carry the shape its column declares.'''

    def __init__(self, kind, message, code=None):
        self.kind, self.code, self.message = kind, code, message
        super().__init__(message)


@dataclass(frozen=True)
class LoadIssue:
    table: str
    row: int  # 1-based data row; 0 marks a file level finding
    column: str
    kind: str
    code: str | None  # a registered reason_code where one exists ([L889] names C-09 only)
    message: str


def _decimal(text, where):
    '''numeric.D is the only Decimal constructor used here (V-9, [L1267]).'''
    try:
        return numeric.D(text.strip())
    except (numeric.NumericError, ArithmeticError, ValueError) as exc:
        raise CoercionError('UNPARSEABLE_NUMBER', where + ' is not a number: ' + text) from exc


def _exact_int(text, where, kind, code):
    value = _decimal(text, where)
    if value != value.to_integral_value():
        raise CoercionError(kind, where + ' must be an exact integer, got ' + text, code)
    return int(value)


def _iso(text, where, pattern, factory, label):
    cell = text.strip()
    if pattern.fullmatch(cell) is None:
        raise CoercionError('NON_ISO_DATE', where + ' ' + label + ' is not ISO: ' + text)
    try:
        return factory(cell)
    except ValueError as exc:
        raise CoercionError('NON_ISO_DATE', where + ' ' + label + ' is not a real value') from exc


def coerce(kind, text, where, unit=None):
    '''[L889] type forcing. A unit-shaped column follows the T2 unit [L1138]:
    MONEY_MINOR is an exact int (C-09 on a fraction, B-008), COUNT is an int, the
    rest a Decimal; enum columns stay text and the model closes them (H-7).'''
    if kind in ('unit_value', 'unit_ref'):
        kind = 'money' if unit == MONEY_MINOR else ('int' if unit == COUNT else 'ratio')
    if kind == 'money':  # B-008: exact minor-unit int or C-09, never a Decimal
        return _exact_int(text, where, 'MONEY_NOT_INTEGER', RC.MONEY_NON_INTEGER.value)
    if kind == 'int':
        return _exact_int(text, where, 'UNPARSEABLE_NUMBER', None)
    if kind == 'bool':  # B-010: the two literal tables are the whole truth
        key = text.strip().lower()
        if key in TRUE_LITERALS:
            return True
        if key in FALSE_LITERALS:
            return False
        raise CoercionError('UNRECOGNIZED_LITERAL', where + ' literal ' + text
                            + ' is in neither B-010 table; no default is applied')
    if kind == 'date':
        return _iso(text, where, _ISO_DATE, date.fromisoformat, 'date')  # [L1121], [L889]
    if kind == 'datetime':
        return _iso(text, where, _ISO_DATETIME, datetime.fromisoformat, 'timestamp')  # [L1152]
    if kind == 'list':
        parts = tuple(part.strip() for part in text.split(LIST_SEPARATOR) if part.strip())
        if not parts:
            raise CoercionError('UNRECOGNIZED_LITERAL', where + ' list cell carries no item')
        return parts
    return _decimal(text, where)  # 'ratio'


# Only columns carrying more than text are listed; the row model closes the rest.
TABLE_MODELS = {'strategy_master': StrategyMasterRow, 'metric_dict': MetricDictRow,
                'metric_facts': MetricFactRow, 'design_cards': DesignCardRow,
                'redlines': RedlineRow, 'grade_ledger': GradeLedgerRow}
TABLE_SPECS = {
    'strategy_master': {'online_date': 'date', 'offline_date': 'date'},  # [L1121]
    'metric_dict': {'direction': 'int', 'target_value': 'unit_value',
                    'is_redline': 'bool', 'signoff_date': 'date'},  # [L1137]-[L1141]
    'metric_facts': {'value_num': 'unit_ref', 'value_den': 'unit_ref', 'value': 'unit_ref',
                     'snapshot_time': 'datetime', 'data_as_of': 'date'},  # [L1150]-[L1152]
    'design_cards': {'process_metrics': 'list', 'result_metrics': 'list', 'mde_ok': 'bool'},
    'redlines': {'threshold_value': 'unit_ref', 'waiver_allowed': 'bool'},  # [L1181], [L1184]
    'grade_ledger': {'ledger_complete': 'bool', 'usable_for_elimination': 'bool',
                     'deadline': 'date'},  # [L1019], [L1632]-[L1634]
}


def _required_text_columns():
    '''ORCH-41 R2 (column level, never a global NULL_LITERALS change): a column whose
    row model declares a **required** plain `str` keeps the empty cell as the legal
    value '' instead of upgrading it to None. Authority: [L1168] makes T4
    success_criteria a payload column ("成功判定（含显著性水平与最小效应，若有）") while
    [L1173] card_status is where an incomplete card is recorded; the empty
    success_criteria of design_cards rows 11/12 (S-010 card_status=MISSING, S-011
    PARTIAL) is a deliberate M34 L1460 construction and the very material of an
    incomplete design card, so reading it as absent would delete a real value - the
    same reason 'NONE' is kept out of NULL_LITERALS above. The set is derived from
    the model field annotations (required + exactly `str`), not hardcoded, so a
    nullable / Literal / numeric column is untouched and '' still reads as None
    there. Keeps one caliber with tests/test_golden_a.py:885 (`== ''`).'''
    columns = set()
    for table, model in TABLE_MODELS.items():
        for name, field in model.model_fields.items():
            if field.is_required() and field.annotation is str:
                columns.add((table, name))
    return frozenset(columns)


TEXT_AS_IS_COLUMNS = _required_text_columns()


@dataclass(frozen=True)
class Inputs:
    '''[L891] Inputs: the five tabular tables io_loaders owns plus the prior ledger
    [L890]. T6 / T7 / T8 are YAML and come from dsm/config.py ([L877]).'''

    strategy_master: tuple
    metric_dict: tuple
    metric_facts: tuple
    design_cards: tuple
    redlines: tuple
    previous_ledger: tuple


@dataclass(frozen=True)
class LoadResult:
    inputs: Inputs
    fingerprints: dict  # [L891] InputFingerprints: file name -> SHA256 + row count
    issues: tuple


def cell_to_text(value):
    '''A parquet cell is flattened to the text a CSV cell carries, so the coercion
    path stays single. A float is refused, not stringified: str(0.1) would smuggle
    a float past H-4 [L1265]. NaN / NaT reads as absent.'''
    if value is None:
        return ''
    if isinstance(value, float):
        if value != value:
            return ''
        raise CoercionError('FLOAT_IN_SOURCE', 'float cell is refused by H-4 [L1265]')
    return str(value)


def read_table(path):
    '''[L888] the CSV / Parquet reader pair; both yield header + text rows.'''
    suffix = Path(path).suffix.lower()
    if suffix == '.csv':
        with open(path, 'r', encoding='utf-8-sig', newline='') as handle:
            rows = list(csv.reader(handle))
        return tuple(rows[0]) if rows else (), tuple(tuple(r) for r in rows[1:])
    if suffix != '.parquet':
        raise CoercionError('MISSING_FILE', 'unsupported file type ' + suffix)
    try:
        # D-C1-01: dtype is not a read_parquet parameter - pandas 3.1.1 forwards
        # it to pyarrow read_table, which rejects it (TypeError: read_table() got
        # an unexpected keyword argument 'dtype'). It was also the wrong shape:
        # dtype=str would stringify a float column and smuggle it past the H-4
        # guard. Cells stay native and cell_to_text flattens each one to the
        # text a CSV cell carries, so both branches share the one coerce path.
        frame = pandas.read_parquet(path)
    except ImportError as exc:
        raise CoercionError('MISSING_FILE', 'no parquet engine for ' + str(path)
                            + ': pyarrow is required, install the parquet extra') from exc
    header = tuple(str(name) for name in frame.columns)
    rows = tuple(tuple(cell_to_text(cell) for cell in record)
                 for record in frame.itertuples(index=False, name=None))
    return header, rows


def fingerprint_of(path, row_count):
    '''[L888] SHA256 of the bytes plus the row count: no mtime, no absolute path, so
    the same bytes always give the same record - the L1 half of G-12.'''
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        block = handle.read(65536)
        while block:
            digest.update(block)
            block = handle.read(65536)
    return InputTableFingerprint(sha256=digest.hexdigest(), row_count=row_count)


def load_table(path, table, unit_map=None):
    '''Read one file, force the declared types, fingerprint it, build the rows. A cell
    that fails coercion is recorded and its row dropped: nothing is repaired on the
    way and no half-typed row reaches the model layer (B-008, B-010).'''
    path = Path(path)
    try:
        header, raw_rows = read_table(path)
    except CoercionError as exc:
        raise DataLoadError([LoadIssue(table, 0, '', exc.kind, exc.code,
                                       str(path) + ': ' + exc.message)]) from exc
    specs, model, typed = TABLE_SPECS[table], TABLE_MODELS[table], []
    issues = [LoadIssue(table, 0, column, 'MISSING_COLUMN', None,
                        table + ' file lacks column ' + column)
              for column in specs if column not in header]
    for number, cells in enumerate(raw_rows, start=1):
        record, payload, broken = dict(zip(header, cells)), {}, False
        for column, text in record.items():
            if ((table, column) not in TEXT_AS_IS_COLUMNS
                    and text.strip().lower() in NULL_LITERALS):
                payload[column] = None  # null is null: never '', False or 0
                continue
            kind = specs.get(column)
            if kind is None:
                payload[column] = text  # the model closes str / Literal / ReasonCode
                continue
            where = table + ' row ' + str(number) + ' column ' + column
            unit = None
            if kind == 'unit_ref':
                unit = (unit_map or {}).get(record.get('metric_id', ''))
                if unit is None:
                    issues.append(LoadIssue(table, number, column, 'UNIT_UNKNOWN', None,
                                            where + ' metric_id has no unit in metric_dict; read '
                                                    'as a Decimal, preflight decides'))
            elif kind == 'unit_value':
                unit = record.get('unit')
            try:
                payload[column] = coerce(kind, text, where, unit)
            except CoercionError as exc:
                issues.append(LoadIssue(table, number, column, exc.kind, exc.code,
                                        where + ': ' + exc.message))
                broken = True
        if broken:
            continue
        try:
            typed.append(model(**payload))
        except ValidationError as exc:
            issues.append(LoadIssue(table, number, '', 'MODEL_ROW_REJECTED', None,
                                    table + ' row ' + str(number) + ' refused by '
                                    + model.__name__ + ': ' + str(exc).splitlines()[1]))
    blocking = [issue for issue in issues if issue.kind in BLOCKING_KINDS]
    if blocking:
        raise DataLoadError(blocking)
    return tuple(typed), path.name, fingerprint_of(path, len(raw_rows)), tuple(issues)


def _resolve(directory, stem):
    for suffix in ('.csv', '.parquet'):  # [L888]
        candidate = Path(directory) / (stem + suffix)
        if candidate.is_file():
            return candidate
    return None


def _collect(table, directory, unit_map, loads, issues, fingerprints):
    path = _resolve(directory, table)
    if path is None:
        issues.append(LoadIssue(table, 0, '', 'MISSING_FILE' if table in ('strategy_master',
                                'metric_dict', 'metric_facts') else 'TABLE_ABSENT', None,
                                'no ' + table + ' file under ' + Path(directory).as_posix()))
        loads[table] = ()
        return
    rows, file_name, fingerprint, table_issues = load_table(path, table, unit_map)
    loads[table] = rows
    issues.extend(table_issues)
    fingerprints[file_name] = fingerprint


def load_previous_ledger(data_dir, previous_period=None):
    '''[L890]: hysteresis and the version break need the previous grade_ledger. A
    missing one is FIRST_PERIOD - registered INFO - and nothing else: no grade is
    invented, in particular not the lowest one.'''
    if previous_period is not None:
        path = _resolve(Path(data_dir) / str(previous_period), 'grade_ledger')
        if path is not None:
            rows, file_name, fingerprint, issues = load_table(path, 'grade_ledger')
            return rows, issues, (file_name, fingerprint)
    return (), (LoadIssue('grade_ledger', 0, '', 'NO_PREVIOUS_LEDGER', RC.FIRST_PERIOD.value,
                          'no previous grade_ledger; treated as FIRST_PERIOD'),), None


def load_inputs(data_dir, period, config_dir, previous_period=None):
    '''[L888] / [L891]: Inputs plus InputFingerprints, every declared type forced. An
    empty / NA cell is None (never '', False or 0). The map is keyed by file name and
    sorted, so the same bytes reproduce it - the L1 half of G-12. Blocking issues -
    the kinds in BLOCKING_KINDS - raise DataLoadError with the [L892] exit code.'''
    data_root, conf_root, loads, issues, fingerprints = Path(data_dir) / str(period), \
        Path(config_dir), {}, [], {}
    _collect('metric_dict', conf_root, None, loads, issues, fingerprints)
    unit_map = {row.metric_id: row.unit for row in loads['metric_dict']}
    for table, root in (('strategy_master', data_root), ('metric_facts', data_root),
                        ('design_cards', data_root), ('redlines', conf_root)):
        _collect(table, root, unit_map, loads, issues, fingerprints)
    ledger, ledger_issues, ledger_key = load_previous_ledger(data_dir, previous_period)
    issues.extend(ledger_issues)
    if ledger_key is not None:
        fingerprints[ledger_key[0]] = ledger_key[1]
    blocking = [i for i in issues if i.kind in BLOCKING_KINDS]
    if blocking:
        raise DataLoadError(blocking)  # [L892]
    inputs = Inputs(strategy_master=loads['strategy_master'], metric_dict=loads['metric_dict'],
                    metric_facts=loads['metric_facts'], design_cards=loads['design_cards'],
                    redlines=loads['redlines'], previous_ledger=ledger)
    return LoadResult(inputs=inputs, fingerprints=dict(sorted(fingerprints.items())),
                      issues=tuple(issues))
