'''A1 / tests.test_fixtures -- fixtures_gen 的守护测试（15 个测试函数）。

守护判据：
  1. 同 seed 逐字节相等（G-12 的 fixtures 侧前提）
  2. G-01~G-15 每条的触发条件在 fixtures 里齐备（golden_map.probes 逐条求值）
  3. 无任何真实数据（全合成）
  4. R-14：golden 期望值可由 fixtures 的构造手算复现，且不预填实现输出
新增测试的判据是「SDD 哪个守护编号要求它」，没有编号对应的一律不写（R-9）。
'''
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import gen_golden                      # noqa: E402
from dsm import fixtures_gen as fg     # noqa: E402
from dsm import models                 # noqa: E402

SEED = fg.SEED_DEFAULT
GOLDEN_IDS = tuple('G-%02d' % i for i in range(1, 16))


# --------------------------------------------------------------------------
# session 级夹具与工具（不计入测试函数）
# --------------------------------------------------------------------------
@pytest.fixture(scope='session')
def bundle():
    return fg.build_bundle(SEED)


@pytest.fixture(scope='session')
def docs():
    return fg.build_documents(SEED, gen_golden.golden_map(SEED))[1]


@pytest.fixture(scope='session')
def gmap(docs):
    return json.loads(docs['fixtures/golden/golden_map.json'])


@pytest.fixture(scope='session')
def variants():
    return fg.build_variants()


@pytest.fixture(scope='session')
def negatives():
    return fg.build_negative()


def _eq(actual, expected):
    if actual == expected:
        return True
    try:
        return Decimal(str(actual)) == Decimal(str(expected))
    except Exception:
        return False


def _match(actual, expected):
    if isinstance(expected, dict):
        return (isinstance(actual, dict)
                and all(k in actual and _match(actual[k], v)
                        for k, v in expected.items()))
    if isinstance(expected, list):
        return (isinstance(actual, list) and len(actual) == len(expected)
                and all(_match(a, e) for a, e in zip(actual, expected)))
    return _eq(actual, expected)


def _scope_rows(bundle, variants, negatives, scope, table):
    kind, _, name = scope.partition(':')
    if kind == 'base':
        return [fg._enc(r) for r in bundle[table]]
    if kind == 'variant':
        doc = variants[name]
        rows = list(doc['replace'].get(table, [])) + list(doc['append'].get(table, []))
        return [fg._enc(r) for r in rows]
    if kind == 'negative':
        return [negatives[name]['row']]
    raise AssertionError('unknown probe scope: ' + scope)


def _probe_ok(probe, bundle, variants, negatives):
    rows = _scope_rows(bundle, variants, negatives, probe['scope'], probe['t'])
    hit = [r for r in rows if _match(r, probe['m'])]
    if probe.get('none'):
        return not hit
    if not hit:
        return False
    if 'n' in probe and len(hit) < probe['n']:
        return False
    if 'e' in probe and not any(_match(r, probe['e']) for r in hit):
        return False
    for field in probe.get('nonnull', ()):
        if not any(r.get(field) not in (None, '') for r in hit):
            return False
    for field, banned in (probe.get('notcontains') or {}).items():
        if any(banned in (r.get(field) or ()) for r in hit):
            return False
    return True


def _fact_map(bundle):
    return {(r['strategy_id'], r['version_id'], r['period'], r['metric_id']): r['value']
            for r in bundle['metric_fact']}


def _attainment(mid, value):
    m = fg.BY_ID[mid]
    target, val = Decimal(fg._target(m)), Decimal(value)
    return val / target if m[3] == 1 else target / val


def _score(bundle, l1, sid, vid='v1', period=None):
    '''按 fixtures 自己声明的 target / direction / level2 / level1 权重手算
    composite——这是 R-14 要求的「构造 + 手算」路径，不碰任何实现代码。'''
    fm = _fact_map(bundle)
    period = period or fg.EVAL_PERIOD
    l2 = bundle['weight_version'][0]['level2_weights']
    dims = {}
    for dim in fg.DIMS:
        acc = Decimal(0)
        for mid in sorted(l2[dim]):
            val = fm.get((sid, vid, period, mid))
            if val is not None:
                acc += Decimal(l2[dim][mid]) * _attainment(mid, val)
        dims[dim] = acc
    total = sum((Decimal(l1[d]) * dims[d] for d in fg.DIMS), Decimal(0))
    return total, dims


def _num(text):
    return Decimal(str(text).split()[0])


def _all_strings(node, out):
    if isinstance(node, str):
        out.append(node)
    elif isinstance(node, dict):
        for key, val in node.items():
            out.append(key)
            _all_strings(val, out)
    elif isinstance(node, list):
        for item in node:
            _all_strings(item, out)
    return out


IDENTITY_FIELDS = (
    'strategy_name', 'metric_name', 'owner_name', 'owner_dept', 'eval_owner',
    'approved_by', 'scene_code', 'source_table', 'data_source', 'numerator_def',
    'denominator_def', 'dedup_rule', 'outlier_rule', 'target_basis', 'direct_goal',
    'success_criteria', 'risk_constraints', 'interpretation_limit', 'alt_method_note',
    'rationale', 'grade_label', 'action_gate', 'version_change_note',
    'estimator_method', 'experiment_id', 'holdout_id', 'actions')
PII_PATTERNS = (re.compile(r'\d{12,}'), re.compile(r'1[3-9]\d{9}'),
                re.compile(r'\d{17}[\dXx]'))
REAL_DATA_WORDS = ('ICBC', '工行', '工商银', '招商银行', '支付宝', '微信支付')


# --------------------------------------------------------------------------
# 守护 1：可复现（G-12 的 fixtures 侧前提）
# --------------------------------------------------------------------------
def test_same_seed_writes_byte_identical_files(tmp_path_factory):
    first = tmp_path_factory.mktemp('run1')
    second = tmp_path_factory.mktemp('run2')
    docs_a = fg.write_bundle(str(first), seed=SEED,
                             golden_map=gen_golden.golden_map(SEED))
    docs_b = fg.write_bundle(str(second), seed=SEED,
                             golden_map=gen_golden.golden_map(SEED))
    assert sorted(docs_a) == sorted(docs_b)
    for path in sorted(docs_a):
        assert docs_a[path] == docs_b[path], path
        assert (first / path).read_bytes() == (second / path).read_bytes(), path


def test_seed_controls_the_random_part_only(bundle):
    same = fg.build_bundle(SEED)
    other = fg.build_bundle(SEED + 1)
    assert fg.to_jsonl(bundle['metric_fact']) == fg.to_jsonl(same['metric_fact'])
    assert fg.to_jsonl(bundle['metric_fact']) != fg.to_jsonl(other['metric_fact'])
    for table in fg.TABLE_ORDER:
        if table != 'metric_fact':
            assert fg.to_jsonl(bundle[table]) == fg.to_jsonl(other[table]), table
    # 刻意构造的格子不随 seed 漂移，否则 golden 手算值就失去意义
    base, alt = _fact_map(bundle), _fact_map(other)
    for key in (('S-001', 'v1', fg.EVAL_PERIOD, 'M_REV_MINOR'),
                ('S-002', 'v1', fg.EVAL_PERIOD, 'M_SATISFY_SCORE'),
                ('S-009', 'v1', fg.EVAL_PERIOD, 'M_CONTACT_FREQ_PER_30D'),
                ('S-006', 'v1', fg.EVAL_PERIOD, 'M_COMPLAINT_RATE')):
        assert base[key] == alt[key], key


def test_manifest_hashes_match_written_files(docs):
    manifest = json.loads(docs['fixtures/manifest.json'])
    assert manifest['synthetic_only'] is True
    assert manifest['seed'] == SEED
    for path, meta in sorted(manifest['files'].items()):
        text = docs[path]
        assert fg.sha256_text(text) == meta['sha256'], path
        assert meta['bytes'] == len(text.encode('utf-8')), path
        # 仓库里已落盘的 fixtures/** 必须与生成器逐字节一致
        assert (ROOT / path).read_bytes() == text.encode('utf-8'), path


def test_written_files_are_lf_without_bom_or_tab(docs):
    for path in sorted(docs):
        raw = (ROOT / path).read_bytes()
        assert not raw.startswith(b'\xef\xbb\xbf'), path
        assert b'\r' not in raw, path
        assert b'\t' not in raw, path
        raw.decode('utf-8')


# --------------------------------------------------------------------------
# 守护 2：M34 的形态要求（12 / 4 / A3B3C4D2 / 15 指标 / >=4 期）
# --------------------------------------------------------------------------
def test_shape_12_strategies_over_4_domains_and_3_segments(bundle):
    rows = bundle['strategy_master']
    ids = {r['strategy_id'] for r in rows}
    assert len(ids) == 12
    assert len(rows) == 13                       # S-005 多一个 v2（G-08）
    assert {r['biz_domain'] for r in rows} == set(fg.BIZ_DOMAINS)
    assert {r['segment_type'] for r in rows} == set(fg.SEGMENT_TYPES)
    cells = {(r['biz_domain'], r['segment_type']) for r in rows if r['version_id'] == 'v1'}
    assert len(cells) == 12                      # 4 域 x 3 类，每格恰好一条


def test_evidence_distribution_is_a3_b3_c4_d2(bundle, docs):
    manifest = json.loads(docs['fixtures/manifest.json'])
    assert manifest['evidence_distribution'] == {'A': 3, 'B': 3, 'C': 4, 'D': 2}
    intent = manifest['intended_evidence_class']
    assert len(intent) == 12
    cards = {(r['strategy_id'], r['version_id']): r for r in bundle['design_card']}
    for sid, ev in intent.items():
        card = cards[(sid, 'v1')]
        if ev == 'A':
            assert card['control_arrangement'] == 'RANDOMIZED'
            assert card['eval_method'] == 'AB_TEST' and card['mde_ok'] is True
        elif ev == 'B':
            assert card['control_arrangement'] == 'CONCURRENT_CONTROL'
        elif ev == 'C':
            assert card['control_arrangement'] == 'NONE' and card['interpretation_limit']
        else:
            assert (card['card_status'] == 'MISSING'
                    or not card['interpretation_limit'])


def test_metric_dictionary_shape_and_units(bundle):
    rows = bundle['metric_dict']
    assert len(rows) == 15
    per_dim = {}
    for row in rows:
        per_dim[row['dim_code']] = per_dim.get(row['dim_code'], 0) + 1
    assert set(per_dim) == set(fg.DIMS) and len(per_dim) == 6
    assert all(2 <= n <= 3 for n in per_dim.values()), per_dim
    assert {r['unit'] for r in rows} == {'MONEY_MINOR', 'COUNT', 'RATIO', 'DURATION_SEC'}
    assert {r['missing_rule'] for r in rows} == {'ZERO', 'SKIP', 'IMPUTE_MEDIAN',
                                                 'BLOCK'}
    weights = bundle['weight_version'][0]
    assert sum(weights['level1_weights'].values()) == Decimal(1)
    for dim in fg.DIMS:
        assert sum(weights['level2_weights'][dim].values()) == Decimal(1), dim


def test_calibration_window_has_at_least_4_history_periods(bundle):
    assert len(fg.HISTORY_PERIODS) >= 4
    periods = {r['period'] for r in bundle['metric_fact']}
    assert set(fg.HISTORY_PERIODS) <= periods
    for period in fg.HISTORY_PERIODS:
        rows = [r for r in bundle['metric_fact'] if r['period'] == period]
        assert len({r['strategy_id'] for r in rows}) == 12, period
        assert len(rows) == 12 * 15, period      # 每期每策略 15 个指标齐全


def test_seven_deliberate_constructions_have_carriers(bundle, docs, variants):
    manifest = json.loads(docs['fixtures/manifest.json'])
    built = manifest['deliberate_constructions']
    assert len(built) == 7
    assert [c['n'] for c in built] == [1, 2, 3, 4, 5, 6, 7]
    assert all(c['carrier'] and c['ref'] for c in built)
    facts = _fact_map(bundle)
    ids = {r['strategy_id'] for r in bundle['strategy_master']}
    # 1 高贡献 + 红线违反
    assert ('S-009' in ids and facts[('S-009', 'v1', fg.EVAL_PERIOD,
                                       'M_CONTACT_FREQ_PER_30D')] == 6)
    # 2 C 类超 L1 门槛
    assert facts[('S-003', 'v1', fg.EVAL_PERIOD, 'M_REV_MINOR')] == 11500
    # 3 目标值大面积缺失
    assert len(variants['G04_target_missing']['replace']['metric_dict']) == 9
    # 4 版本变更
    versions = {r['version_id'] for r in bundle['strategy_master']
                if r['strategy_id'] == fg.VERSION_BREAK_ID}
    assert versions == {'v1', 'v2'}
    # 5 零变异指标
    zero = {v for (s, _vid, _p, mid), v in facts.items()
            if mid == fg.ZERO_VARIATION_METRIC}
    assert zero == {fg.ZERO_VARIATION_VALUE}
    assert len([1 for (s, _v, _p, mid) in facts
                if mid == fg.ZERO_VARIATION_METRIC]) == 12 * 5
    # 6 主导权重指标
    l2 = bundle['weight_version'][0]['level2_weights']
    assert l2['CONTRIB'][fg.DOMINANT_METRIC] == fg.DOMINANT_SHARE
    assert fg.DOMINANT_SHARE >= Decimal('0.50')
    # 7 豁免无留痕
    assert facts[('S-006', 'v1', fg.EVAL_PERIOD, 'M_COMPLAINT_RATE')] == \
        Decimal('0.007000')
    assert [r for r in bundle['redline'] if r['metric_id'] == 'M_COMPLAINT_RATE'][0][
        'waiver_allowed'] is True


# --------------------------------------------------------------------------
# 守护 3：G-01~G-15 触发条件齐备 + R-14 手算复核
# --------------------------------------------------------------------------
@pytest.mark.parametrize('case_id', GOLDEN_IDS)
def test_golden_trigger_probes(case_id, gmap, bundle, variants, negatives):
    case = next(c for c in gmap['cases'] if c['id'] == case_id)
    assert case['probes'], case_id
    for probe in case['probes']:
        assert _probe_ok(probe, bundle, variants, negatives), (case_id, probe)


def test_golden_hand_arithmetic_matches_fixtures(gmap, bundle, variants):
    hand = {c['id']: c['hand'] for c in gmap['cases']}
    floors = {r['grade_code']: Decimal(r['attainment_floor'])
              for r in bundle['grade_rule']}
    oat20 = fg.LEVEL1_WEIGHTS_OAT20
    # G-01：15 个指标 attainment 全 >= 1，composite 手算 1.021930
    g01 = [_attainment(m, _fact_map(bundle)[('S-001', 'v1', fg.EVAL_PERIOD, m)])
           for m in fg.METRIC_IDS]
    assert min(g01) >= Decimal(1)
    comp, _dims = _score(bundle, fg.LEVEL1_WEIGHTS, 'S-001')
    assert comp == _num(hand['G-01']['composite_absolute'])
    # G-02：C 类但 composite 高于 L1 门槛
    comp, _dims = _score(bundle, fg.LEVEL1_WEIGHTS, 'S-003')
    assert comp == _num(hand['G-02']['composite_absolute'])
    assert comp > floors['L1']
    # G-03：CONTRIB 维度 = 1.90
    _comp, dims = _score(bundle, fg.LEVEL1_WEIGHTS, 'S-009')
    assert dims['CONTRIB'] == _num(hand['G-03']['dim_CONTRIB'])
    # G-06：两条 NEAR_BOUNDARY 策略的翻转点，基线与 OAT+20% 都手算闭合
    base2, _ = _score(bundle, fg.LEVEL1_WEIGHTS, 'S-002')
    pert2, _ = _score(bundle, oat20, 'S-002')
    assert base2 == _num(hand['G-06']['S-002_base'])
    assert pert2 == _num(hand['G-06']['S-002_oat20'])
    assert base2 >= floors['L1'] and pert2 < floors['L1']
    base4, _ = _score(bundle, fg.LEVEL1_WEIGHTS, 'S-004')
    pert4, _ = _score(bundle, oat20, 'S-004')
    assert base4 == _num(hand['G-06']['S-004_base'])
    assert pert4 == _num(hand['G-06']['S-004_oat20'])
    assert base4 >= floors['L2'] and pert4 < floors['L2'] and pert4 >= floors['L3']
    # G-04：9/15 无目标值 -> 计数覆盖 0.400，权重覆盖 0.405
    kept = {r['metric_id'] for r in bundle['metric_dict']
            if r['target_value'] is not None}
    dropped = {r['metric_id']
               for r in variants['G04_target_missing']['replace']['metric_dict']}
    assert len(kept) == 15 and len(dropped) == 9
    assert dropped == set(fg.NO_TARGET_METRICS) <= kept
    l1 = bundle['weight_version'][0]['level1_weights']
    l2 = bundle['weight_version'][0]['level2_weights']
    count_cov = Decimal(len(kept) - len(dropped)) / Decimal(len(fg.METRIC_IDS))
    weight_cov = sum((Decimal(l1[d]) * Decimal(l2[d][m]) for d in fg.DIMS
                      for m in l2[d] if m not in dropped), Decimal(0))
    assert count_cov == _num(hand['G-04']['coverage_count'])
    assert weight_cov == _num(hand['G-04']['coverage_weighted'])


def test_golden_skeleton_discipline(gmap):
    assert tuple(c['id'] for c in gmap['cases']) == GOLDEN_IDS
    assert gmap['case_count'] == 15
    assert 'R-14' in gmap['discipline']
    for case in gmap['cases']:
        assert case['source'] and case['scenario'] and case['expects'], case['id']
        assert case['value_status']
        assert not case['value_status'].startswith('PENDING_IMPL'), case['id']
        if 'HAND_COMPUTED' in case['value_status']:
            assert case['hand'], case['id']


# --------------------------------------------------------------------------
# 守护 4：全合成，无任何真实数据（M34 第 1461 行）
# --------------------------------------------------------------------------
def test_fixtures_contain_no_real_data(bundle, docs):
    for table in fg.TABLE_ORDER:
        for row in bundle[table]:
            for field in IDENTITY_FIELDS:
                value = row.get(field)
                values = value if isinstance(value, (list, tuple)) else [value]
                for item in values:
                    assert item in (None, '') or str(item).startswith('SYNTH'), \
                        (table, field, item)
            assert re.fullmatch(r'S-\d{3}', row.get('strategy_id', 'S-000')), table
    for path, text in docs.items():
        if 'manifest' in path:
            continue
        for value in _all_strings(json.loads(text) if not path.endswith('.jsonl')
                                  else [json.loads(x) for x in text.splitlines()], []):
            assert not any(p.search(value) for p in PII_PATTERNS), (path, value)
            assert not any(w in value for w in REAL_DATA_WORDS), (path, value)


# --------------------------------------------------------------------------
# 自带冒烟（R-4）：happy path 已在上面各条覆盖，这里是负向一条
# --------------------------------------------------------------------------
def test_negative_payload_is_rejected_by_contract(negatives):
    payload = negatives['G11_money_non_integer']
    assert payload['expect_reason_code'] == 'MONEY_NON_INTEGER'
    row = dict(payload['row'])
    with pytest.raises((ValidationError, ValueError)):
        models.MetricFactRow(**row)
    row['value_num'] = 100          # 正对照：换成整数就能过契约
    row['value'] = 100
    assert models.MetricFactRow(**row).value_num == 100
