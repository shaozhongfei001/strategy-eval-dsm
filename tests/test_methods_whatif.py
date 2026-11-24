'''tests/test_methods_whatif.py -- A4 守护测试：T-WIF-01~05 + V-18（M33 [L1453] / M36 [L1511]）。

全部期望值**手算**（R-14：绝不拿实现输出反填 golden），底稿写在下面；输入一律按 R-2 用
dsm.models 的 pydantic 契约构造；Step 5/6/7/8 一律调用真实邻居（aggregate / grading /
pooling / sensitivity），本文件不重实现任何算法（R-7）。

构造场景（2 维度 x 3 指标 x 4 策略；绝对轨与相对轨用同一组构造值，故两轨期望值相同）：

    基线 W0 = {D1: 0.6, D2: 0.4}   w0 = {D1: {m1: 0.5, m2: 0.5}, D2: {m3: 1.0}}
    候选 W1 = {D1: 0.4, D2: 0.6}   w1 = {D1: {m1: 0.8, m2: 0.2}, D2: {m3: 1.0}}

    sid  m1    m2    m3    | dim0_D1 dim1_D1 dim_D2 | comp0  compMid comp1  | 等级
    S1   0.80  0.60  0.55  | 0.70    0.76    0.55   | 0.640  0.676   0.634  | L3 -> L3
    S2   0.40  0.90  0.70  | 0.65    0.50    0.70   | 0.670  0.580   0.620  | L4 -> L4（HARD 红线）
    S3   0.95  0.95  0.95  | 0.95    0.95    0.95   | 0.950  0.950   0.950  | L1 -> L1
    S4   0.95  0.85  0.55  | 0.90    0.93    0.55   | 0.760  0.778   0.702  | L2 -> L3

    comp0 = 0.6·dim0_D1 + 0.4·dim_D2 ；compMid = 0.6·dim1_D1 + 0.4·dim_D2 ；
    comp1 = 0.4·dim1_D1 + 0.6·dim_D2 ；门槛 L1 0.9 / L2 0.75 / L3 0.6 / L4 0.4；
    S2 命中一条 HARD 红线（forced_grade=L4），Step 4 不消费权重 -> 两臂同为 L4。

三段分解（ΔW_D1 = −0.2，ΔW_D2 = +0.2）：

    S1 D1: 段1 = 0.6·0.06 = 0.036 ；段2 = −0.2·0.70 = −0.140 ；交叉 = −0.2·0.06 = −0.012
           小计 −0.116      S1 D2: 段1 = 0 ；段2 = 0.2·0.55 = 0.110 ；交叉 = 0 -> 0.110
           S1 合计 = −0.006 = 0.634 − 0.640 ✓
    S2 D1: 段1 = 0.6·(−0.15) = −0.090 ；段2 = −0.2·0.65 = −0.130 ；交叉 = +0.030 -> −0.190
           S2 D2: 段2 = 0.2·0.70 = 0.140 -> S2 合计 = −0.050 = 0.620 − 0.670 ✓
    S3 D1: 段2 = −0.2·0.95 = −0.190 ；S3 D2: 段2 = +0.190 -> 合计 0 ✓
    S4 D1: 段1 = 0.6·0.03 = 0.018 ；段2 = −0.2·0.90 = −0.180 ；交叉 = −0.2·0.03 = −0.006
           小计 −0.168      S4 D2: 段2 = 0.2·0.55 = 0.110 -> 0.110
           S4 合计 = −0.058 = 0.702 − 0.760 ✓ ；段1 之和 0.018 = 0.778 − 0.760 ✓
           段2+交叉 = −0.076 = 0.702 − 0.778 ✓ ；主驱动维度 = D1（|−0.168| > |0.110|）

    全场景每轨：Σ段1 = 0.036 − 0.090 + 0 + 0.018 = −0.036
                Σ段2 = (−0.140+0.110) + (−0.130+0.140) + 0 + (−0.180+0.110) = −0.090
                Σ交叉 = −0.012 + 0.030 + 0 − 0.006 = 0.012
                Σ三段 = −0.114 = Σ(comp1 − comp0) = −0.006 − 0.050 + 0 − 0.058 ✓
                Σ段1 + Σ段2 = −0.126 ≠ −0.114（差值正是 Σ交叉 0.012 -> 交叉项未被并入）
                Σ中间臂差 = 0.036 − 0.090 + 0 + 0.018 = −0.036 = Σ段1 ✓
                Σ候选臂差 = −0.042 + 0.040 + 0 − 0.076 = −0.078 = Σ段2 + Σ交叉 ✓
'''
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from dsm import aggregate, grading, numeric, pooling, sensitivity, whatif
from dsm.models import (AttainmentFrame, AttainmentRow, EvidenceFrame, EvidenceRow,
                        GradeFrame, GradeRow, GradeRuleRow, NormalizedFrame,
                        NormalizedRow, RedlineEvalRow, RedlineFrame, ScoreFrame,
                        StrategyMasterRow, WeightProvenance, WeightVersionDoc)
from dsm.reason_codes import RC

DAY = date(2026, 1, 1)
DAY_END = date(2026, 12, 31)
PERIOD = '2026Q1'
PREV_PERIOD = '2025Q4'
VER = 'v1'
RUN_ID = 'whatif-2026Q1-20260101T090000-deadbeef'
BASE_ID = 'WV-2026-01'
CAND_ID = 'WV-DRAFT-02'

LEVEL1_BASE = {'D1': Decimal('0.6'), 'D2': Decimal('0.4')}
LEVEL1_CAND = {'D1': Decimal('0.4'), 'D2': Decimal('0.6')}
LEVEL2_BASE = {'D1': {'m1': Decimal('0.5'), 'm2': Decimal('0.5')},
               'D2': {'m3': Decimal('1')}}
LEVEL2_CAND = {'D1': {'m1': Decimal('0.8'), 'm2': Decimal('0.2')},
               'D2': {'m3': Decimal('1')}}

VALUES = {'S1': {'m1': '0.80', 'm2': '0.60', 'm3': '0.55'},
          'S2': {'m1': '0.40', 'm2': '0.90', 'm3': '0.70'},
          'S3': {'m1': '0.95', 'm2': '0.95', 'm3': '0.95'},
          'S4': {'m1': '0.95', 'm2': '0.85', 'm3': '0.55'}}
DOMAIN = {'S1': 'CARD', 'S2': 'CARD', 'S3': 'CARD', 'S4': 'LOAN'}
PREV_GRADES = {'S1': 'L3', 'S2': 'L3', 'S3': 'L1', 'S4': 'L2'}
FLOOR = {'L1': '0.9', 'L2': '0.75', 'L3': '0.6', 'L4': '0.4'}
POOL_PARAMS = pooling.PoolingParams(min_pool_size=1)


class _Drop:
    def __repr__(self):
        return '<DROP>'


_DROP = _Drop()


def D(text):
    return numeric.D(text)


def weights(version_id, level1, level2, status='FROZEN', prior_run_id='WIF-2025Q4-0001'):
    prov = None
    if prior_run_id is not None:
        prov = WeightProvenance(
            kind='AHP_ONLY', whatif_run_id=prior_run_id, approved_by='评价管理委员会',
            approved_date=DAY, effective_from=DAY, effective_to=DAY_END)
    return WeightVersionDoc(
        weight_version_id=version_id, status=status, effective_from=DAY,
        effective_to=DAY_END, level1_weights=level1, level2_weights=level2,
        approved_by='评价管理委员会', approved_date=DAY, provenance=prov)


BASE = weights(BASE_ID, LEVEL1_BASE, LEVEL2_BASE)
CAND = weights(CAND_ID, LEVEL1_CAND, LEVEL2_CAND, status='DRAFT', prior_run_id=None)


def rule_rows():
    return tuple(GradeRuleRow(
        grade_code=g, grade_label=g + '级', attainment_floor=FLOOR[g],
        evidence_class_min='A', redline_pass_required=True, promotion_streak=2,
        actions=(g + '动作',), max_grade_if_no_target='L3')
        for g in ('L1', 'L2', 'L3', 'L4'))


def rules():
    return grading.GradeRuleSet(rows=rule_rows(),
                                min_coverage_for_absolute_track=D('0.6'),
                                upgrade_consecutive_periods=2, demotion_immediate=True)


def attainment_frame():
    rows = [AttainmentRow(strategy_id=sid, version_id=VER, period=PERIOD,
                          metric_id=m, attainment=D(VALUES[sid][m]), direction=1,
                          has_target=True, capped_flag=False)
            for sid in sorted(VALUES) for m in sorted(VALUES[sid])]
    return AttainmentFrame(rows=tuple(rows),
                           attainment_coverage=dict((sid, D('1')) for sid in sorted(VALUES)))


def normalized_frame():
    rows = [NormalizedRow(strategy_id=sid, version_id=VER, period=PERIOD, metric_id=m,
                          pool_key={'biz_domain': DOMAIN[sid], 'evidence_class': 'A'},
                          norm_value=D(VALUES[sid][m]), method='min_max',
                          anchor_used=False)
            for sid in sorted(VALUES) for m in sorted(VALUES[sid])]
    return NormalizedFrame(rows=tuple(rows))


def evidence_frame():
    return EvidenceFrame(rows=tuple(EvidenceRow(
        strategy_id=sid, version_id=VER, evidence_class='A',
        evidence_reason='EV_A_RANDOMIZED', evidence_source='CARD_ONLY')
        for sid in sorted(VALUES)))


def redline_frame():
    '''S2 命中一条 HARD 红线（forced_grade=L4）。Step 4 不消费权重（[L988]），故两臂的
    触发集合必然相同 —— 有了这条命中，redline_delta 为空才是「有内容的空」（T-WIF-04）。'''
    return RedlineFrame(rows=(RedlineEvalRow(
        strategy_id='S2', version_id=VER, period=PERIOD, metric_id='m1', level='HARD',
        comparator='LTE', threshold_value='0.05', hit=True, forced_grade='L4',
        reason_code='REDLINE_HARD_HIT'),))


def master_rows():
    return tuple(StrategyMasterRow(
        strategy_id=sid, version_id=VER, strategy_name=sid + ' 名称',
        biz_domain=DOMAIN[sid], scene_code='SC-01', segment_type='EXISTING',
        online_date=DAY, owner_dept='信用卡部', owner_name='张三', status='ACTIVE')
        for sid in sorted(VALUES))


def prev_frame(grades=None):
    grades = PREV_GRADES if grades is None else grades
    return GradeFrame(rows=tuple(GradeRow(
        strategy_id=sid, version_id=VER, period=PREV_PERIOD, grade=grades[sid],
        grade_reason_path=(), capped=False, usable_for_elimination=True)
        for sid in sorted(grades)))


def carriers(**overrides):
    '''Step 1-4 帧 + 分级治理值。必需载体一个不缺（V-14）；overrides 用来抽掉/污染。'''
    out = {'attainment': attainment_frame(), 'normalized': normalized_frame(),
           'evidence': evidence_frame(), 'redline': redline_frame(),
           'master': master_rows(), 'rules': rules(),
           'prev_grade': prev_frame(), 'streaks': None,
           'prev_weight_version_id': None, 'first_period': False,
           'pool_params': POOL_PARAMS}
    for key, value in overrides.items():
        if value is _DROP:
            out.pop(key, None)
        else:
            out[key] = value
    return out


def go(cand=CAND, base=BASE, config=None, run_id=RUN_ID, **overrides):
    return whatif.run(cand, base, carriers(**overrides), config, PERIOD, run_id=run_id)


def arm_grades(base_doc):
    '''测试自己调 B3 跑一臂的 Step 5-6（不重实现，只调用邻居），供红线集合对拍。'''
    carrier = carriers()
    score = aggregate.compose(carrier['attainment'], carrier['normalized'], base_doc, None)
    return carrier, grading.assign(score, carrier['attainment'], carrier['evidence'],
                                   carrier['redline'], carrier['prev_grade'],
                                   carrier['rules'], streaks=None,
                                   prev_weight_version_id=None)


def attr(report, sid, track, dim):
    hits = [r for r in report.attribution
            if r.strategy_id == sid and r.track == track and r.dim_code == dim]
    assert len(hits) == 1
    return hits[0]


def recon(report, track):
    hits = [r for r in report.reconciliation if r.track == track]
    assert len(hits) == 1
    return hits[0]


# --------------------------------------------------------------------------
# T-WIF-01 归因精确性（手算 golden + 1e-12 逐项对拍）
# --------------------------------------------------------------------------
def test_wif01_attribution_matches_hand_computed_golden():
    '''S1/S2/S4 的分量逐一等于上面手算底稿的数字（R-14），两轨独立算出且相同。'''
    report = go()
    s1d1, s1d2 = attr(report, 'S1', 'ABSOLUTE', 'D1'), attr(report, 'S1', 'ABSOLUTE', 'D2')
    assert (s1d1.dim_baseline, s1d1.dim_candidate, s1d1.dim_delta) == (
        D('0.70'), D('0.76'), D('0.06'))
    assert (s1d1.weight_baseline, s1d1.weight_candidate, s1d1.weight_delta) == (
        D('0.6'), D('0.4'), D('-0.2'))
    assert (s1d1.seg_within_dim, s1d1.seg_dim_weight, s1d1.cross_term) == (
        D('0.036'), D('-0.140'), D('-0.012'))
    assert numeric.eq_exact(s1d1.dim_total, D('-0.116'))
    assert numeric.eq_exact(s1d2.seg_dim_weight, D('0.110'))
    assert numeric.eq_exact(s1d2.seg_within_dim + s1d2.cross_term, D('0'))
    s2d1 = attr(report, 'S2', 'ABSOLUTE', 'D1')
    assert (s2d1.seg_within_dim, s2d1.seg_dim_weight, s2d1.cross_term) == (
        D('-0.090'), D('-0.130'), D('0.030'))
    s4d1 = attr(report, 'S4', 'ABSOLUTE', 'D1')
    assert (s4d1.seg_within_dim, s4d1.seg_dim_weight, s4d1.cross_term) == (
        D('0.018'), D('-0.180'), D('-0.006'))
    assert numeric.eq_exact(s4d1.dim_total, D('-0.168'))
    r4d1 = attr(report, 'S4', 'RELATIVE', 'D1')
    assert (r4d1.seg_within_dim, r4d1.seg_dim_weight, r4d1.cross_term) == (
        D('0.018'), D('-0.180'), D('-0.006'))


def test_wif01_segment_sums_equal_total_difference_within_1e12():
    '''Σ(段1+段2+交叉) 与 Σ(comp1 − comp0) 逐轨相等，残差 ≤ 1e-12（T-WIF-01）。'''
    report = go()
    for track in ('ABSOLUTE', 'RELATIVE'):
        line = recon(report, track)
        assert line.checked_items == 4                      # 四个策略全部参评
        assert numeric.eq_exact(line.total_sum, D('-0.114'))
        assert numeric.eq_exact(line.delta_composite_sum, D('-0.114'))
        assert numeric.eq_exact(line.seg_within_dim_sum, D('-0.036'))
        assert numeric.eq_exact(line.seg_dim_weight_sum, D('-0.090'))
        assert numeric.eq_exact(line.cross_term_sum, D('0.012'))
        assert numeric.eq_tol(line.total_sum, line.delta_composite_sum, numeric.TOL)
        assert line.max_residual <= numeric.TOL             # 1e-12 硬容差
    parts = [attr(report, 'S4', 'ABSOLUTE', d) for d in ('D1', 'D2')]
    total = sum((p.dim_total for p in parts), numeric.ZERO)
    assert numeric.eq_tol(total, D('-0.058'), numeric.TOL)  # = 0.702 − 0.760
    assert abs(total - D('-0.058')) <= numeric.TOL


# --------------------------------------------------------------------------
# T-WIF-02 只读性 INV-2（目录哈希比对自证；哈希只走 dsm.audit）
# --------------------------------------------------------------------------
def fingerprints(root):
    '''INV-2 自证用：目录内全部常规文件的 相对路径 -> SHA256。哈希**只调用 dsm.audit**
    （sha256_bytes），测试与生产代码都不重实现哈希（R-7）；相对路径做键，绝对路径是
    环境量（与 audit.fingerprint_outputs 同一口径）。只读：rglob + read_bytes。'''
    from dsm import audit
    paths = sorted((p for p in Path(root).rglob('*') if p.is_file()),
                   key=lambda p: p.relative_to(root).as_posix())
    return dict((p.relative_to(root).as_posix(), audit.sha256_bytes(p.read_bytes()))
                for p in paths)


def digest(root):
    '''整个目录的一个 64 位摘要 = audit.sha256_text(audit.canonical_text(指纹表))。'''
    from dsm import audit
    return audit.sha256_text(audit.canonical_text(fingerprints(root)))


def _input_dir(tmp_path):
    root = tmp_path / 'inputs'
    (root / 't1').mkdir(parents=True)
    (root / 'metric_fact.csv').write_text('strategy_id,metric_id\nS1,m1\n',
                                          encoding='utf-8', newline='\n')
    (root / 't1' / 'weights_WV-2026-01.yaml').write_text(
        'weight_version_id: WV-2026-01\nstatus: FROZEN\n', encoding='utf-8', newline='\n')
    return root


def test_wif02_input_directory_hash_unchanged_before_and_after_run(tmp_path):
    '''运行前后逐文件指纹相等、整目录摘要相等（INV-2 只读的自证），且摘要确实由
    audit 的原语算出（本文件与 whatif 都不重实现哈希，R-7）。'''
    root = _input_dir(tmp_path)
    before_files = fingerprints(root)
    before = digest(root)
    report = go()
    after_files = fingerprints(root)
    after = digest(root)
    assert before == after and len(before) == 64
    assert before_files == after_files
    assert sorted(before_files) == ['metric_fact.csv', 't1/weights_WV-2026-01.yaml']
    assert report.run_id == RUN_ID
    from dsm import audit
    assert before == audit.sha256_text(audit.canonical_text(after_files))
    assert all(len(v) == 64 for v in after_files.values())


def test_wif02_directory_digest_detects_a_single_byte_change(tmp_path):
    '''负向：改一个字节摘要就变 —— 证明上面的「相等」不是恒真断言；同时确认 whatif
    没有在任何地方创建生产报告树（INV-2 / V-18）。'''
    root = _input_dir(tmp_path)
    before = digest(root)
    before_file = fingerprints(root)['metric_fact.csv']
    go()
    (root / 'metric_fact.csv').write_text('strategy_id,metric_id\nS1,m2\n',
                                          encoding='utf-8', newline='\n')
    assert digest(root) != before
    assert fingerprints(root)['metric_fact.csv'] != before_file
    assert not (root / 'reports').exists()
    assert sorted(p.name for p in root.iterdir()) == ['metric_fact.csv', 't1']


def test_wif02_run_writes_nothing_at_all(monkeypatch):
    '''INV-2 / V-18：把 Path 的全部写入原语打成必炸，run() 仍须成功返回对象。'''
    def boom(self, *args, **kwargs):
        raise AssertionError('whatif 不得写盘（INV-2）：Path.' + str(args))

    for name in ('mkdir', 'write_text', 'write_bytes', 'touch', 'rename', 'replace',
                 'unlink', 'rmdir'):
        monkeypatch.setattr(Path, name, boom)
    report = go()
    assert isinstance(report, whatif.WhatifReport)
    assert report.refuse_signoff is False


# --------------------------------------------------------------------------
# T-WIF-03 / V-18 与 score 一致（等权 + 生产帧逐行复现）
# --------------------------------------------------------------------------
def test_wif03_equal_weights_reproduce_score_exactly():
    '''候选权重与冻结权重数值相同 -> 三臂退化：Δ=0、无等级变化、归因全 0（V-18）。'''
    same = BASE.model_copy(update={'weight_version_id': 'WV-DRAFT-SAME',
                                   'status': 'DRAFT', 'provenance': None})
    report = go(cand=same)
    assert report.grade_changes == ()
    assert report.unchanged_count == 4
    assert report.redline_delta == () and report.evidence_gate_delta == ()
    assert report.refuse_signoff is False
    assert len(report.attribution) == 16
    for row in report.attribution:
        assert numeric.eq_exact(row.dim_delta, D('0'))
        assert numeric.eq_exact(row.weight_delta, D('0'))
        assert numeric.eq_exact(row.seg_within_dim, D('0'))
        assert numeric.eq_exact(row.seg_dim_weight, D('0'))
        assert numeric.eq_exact(row.cross_term, D('0'))
        assert numeric.eq_exact(row.dim_total, D('0'))
    for track in ('ABSOLUTE', 'RELATIVE'):
        line = recon(report, track)
        assert numeric.eq_exact(line.delta_composite_sum, D('0'))
        assert numeric.eq_exact(line.max_residual, D('0'))
    occ = report.occupancy_delta
    assert occ.grade_count_delta == dict((k, 0) for k in occ.grade_count_delta)
    assert all(numeric.eq_exact(v, D('0')) for v in occ.share_in_pool_delta.values())
    assert all(numeric.eq_exact(v, D('0')) for v in occ.share_overall_delta.values())


def test_wif03_baseline_arm_reproduces_production_step5_and_step6():
    '''交来生产 Step 5/6 结果时，baseline 臂必须逐行精确复现（T-WIF-03 正向面）。'''
    carrier = carriers()
    score = aggregate.compose(carrier['attainment'], carrier['normalized'], BASE, None)
    grade = grading.assign(score, carrier['attainment'], carrier['evidence'],
                           carrier['redline'], carrier['prev_grade'], carrier['rules'],
                           streaks=None, prev_weight_version_id=None)
    report = go(score=score, grade=grade)
    assert report.baseline_weight_version_id == BASE_ID
    assert report.unchanged_count == 3 and len(report.grade_changes) == 1


def test_wif03_tampered_production_score_is_refused():
    '''负向：生产 Step 5 被改一个数 -> WhatifConsistencyError，不出报告。'''
    carrier = carriers()
    score = aggregate.compose(carrier['attainment'], carrier['normalized'], BASE, None)
    rows = list(score.rows)
    rows[0] = rows[0].model_copy(update={'composite_absolute': D('0.123')})
    with pytest.raises(whatif.WhatifConsistencyError) as exc:
        go(score=ScoreFrame(rows=tuple(rows)))
    assert exc.value.reason_code == RC.INVARIANT_VIOLATION.value


# --------------------------------------------------------------------------
# T-WIF-04 红线不变性（redline_delta 必为空，且不是空洞的空）
# --------------------------------------------------------------------------
def test_wif04_redline_delta_is_empty():
    report = go()
    assert report.redline_delta == ()
    assert report.refuse_signoff is False
    assert RC.CONFIG_INCONSISTENT.value not in report.warnings
    assert whatif.is_refused(report) is False
    assert whatif.signoff_verdict(report) == (False, ())
    # 非空洞证明：红线在两臂都真的触发了（命中行 + HARD 否决 + 等级路径痕迹各一条），
    # 两个集合内容相同，所以差集为空是「有内容的空」。
    _carrier, grade0 = arm_grades(BASE)
    _carrier, grade1 = arm_grades(whatif._scorable(CAND))
    base_set = whatif._redline_set(_carrier['redline'], grade0)
    whatif_set = whatif._redline_set(_carrier['redline'], grade1)
    assert base_set == whatif_set and len(base_set) == 3
    assert 'S2|v1|m1|HIT' in base_set
    assert 'S2|v1|m1|HARD_VETO' in base_set
    assert 'S2|v1|GR_REDLINE_FORCED' in base_set
    assert dict((r.strategy_id, r.grade) for r in grade0.rows)['S2'] == 'L4'
    assert dict((r.strategy_id, r.grade) for r in grade1.rows)['S2'] == 'L4'


def test_wif04_nonempty_redline_delta_refuses_signoff():
    '''负向：一旦 redline_delta 非空 -> CONFIG_INCONSISTENT + 建议拒绝签认（[L1370]）。'''
    report = go()
    broken = report.model_copy(
        update={'redline_delta': ('WHATIF_ONLY|S1|v1|m1|HIT',)})
    refuse, codes = whatif.signoff_verdict(broken)
    assert refuse is True
    assert codes == (RC.CONFIG_INCONSISTENT.value,)
    assert whatif.is_refused(broken) is True


# --------------------------------------------------------------------------
# T-WIF-05 两段归因交叉项分离
# --------------------------------------------------------------------------
def test_wif05_cross_term_is_its_own_column():
    '''交叉项独立成列：段1+段2 之和不等于总差，差值恰为交叉项之和（未被并入任一段）。'''
    report = go()
    for track in ('ABSOLUTE', 'RELATIVE'):
        line = recon(report, track)
        merged = line.seg_within_dim_sum + line.seg_dim_weight_sum
        assert numeric.eq_exact(merged, D('-0.126'))
        assert not numeric.eq_tol(merged, line.total_sum, numeric.TOL)   # 两段之和 ≠ 总差
        assert numeric.eq_exact(line.total_sum - merged, line.cross_term_sum)
        assert numeric.eq_exact(line.cross_term_sum, D('0.012'))
        assert numeric.eq_exact(line.seg_within_dim_sum + line.seg_dim_weight_sum
                                + line.cross_term_sum, line.total_sum)
    row = attr(report, 'S1', 'ABSOLUTE', 'D1')
    assert numeric.eq_exact(row.cross_term, D('-0.012'))                 # 逐行也非零
    assert not numeric.eq_tol(row.seg_within_dim + row.seg_dim_weight, row.dim_total)


def test_wif05_two_segment_serial_matches_the_mid_arm():
    '''中间臂（基线 level1 + 候选 level2）独立测得段1；候选臂减中间臂 = 段2+交叉。'''
    report = go()
    for track in ('ABSOLUTE', 'RELATIVE'):
        line = recon(report, track)
        assert numeric.eq_exact(line.mid_arm_delta_sum, D('-0.036'))
        assert numeric.eq_tol(line.seg_within_dim_sum, line.mid_arm_delta_sum, numeric.TOL)
        assert numeric.eq_exact(line.candidate_arm_delta_sum, D('-0.078'))
        assert numeric.eq_tol(line.seg_dim_weight_sum + line.cross_term_sum,
                              line.candidate_arm_delta_sum, numeric.TOL)
    s4 = [attr(report, 'S4', 'ABSOLUTE', d) for d in ('D1', 'D2')]
    assert numeric.eq_tol(sum((r.seg_within_dim for r in s4), numeric.ZERO),
                          D('0.018'), numeric.TOL)          # = 0.778 − 0.760
    assert numeric.eq_tol(sum((r.seg_dim_weight + r.cross_term for r in s4), numeric.ZERO),
                          D('-0.076'), numeric.TOL)           # = 0.702 − 0.778


# --------------------------------------------------------------------------
# V-18 变更清单 / 占比双报 / 报告身份
# --------------------------------------------------------------------------
def test_v18_grade_change_occupancy_and_main_driver():
    '''S4 由 L2 降 L3（降级即时），主驱动维度 D1；L2 −1 / L3 +1；权重不改池归属，故
    占比双报的变化为 0，等级计数才是主信号；Step 8 未跑 -> 举证制两臂都不准入。'''
    report = go()
    assert report.unchanged_count == 3 and len(report.grade_changes) == 1
    change = report.grade_changes[0]
    assert (change.strategy_id, change.version_id) == ('S4', VER)
    assert (change.baseline_grade, change.whatif_grade) == ('L2', 'L3')
    assert change.main_driver_dim == 'D1'
    assert numeric.eq_exact(change.delta_composite, D('-0.058'))
    assert 'L2→L3' in change.explanation and '-0.058' in change.explanation
    assert 'D1' in change.explanation and '交叉项' in change.explanation
    occ = report.occupancy_delta
    assert occ.grade_counts_baseline == {'L1': 1, 'L2': 1, 'L3': 1, 'L4': 1,
                                         'NOT_ASSESSED': 0}
    assert occ.grade_counts_whatif == {'L1': 1, 'L2': 0, 'L3': 2, 'L4': 1,
                                       'NOT_ASSESSED': 0}
    assert occ.grade_count_delta['L2'] == -1 and occ.grade_count_delta['L3'] == 1
    assert occ.grade_count_delta['L4'] == 0
    assert occ.share_in_pool_delta == dict((k, D('0')) for k in occ.share_in_pool_delta)
    assert numeric.eq_exact(occ.share_overall_baseline['CARD|A'], D('0.75'))
    assert numeric.eq_exact(occ.share_overall_baseline['LOAN|A'], D('0.25'))
    assert report.evidence_gate_delta == ()


def test_v18_report_identity_and_operator_are_read_back():
    report = go()
    assert report.run_id == RUN_ID and report.period == PERIOD
    assert report.candidate_weight_version_id == CAND_ID
    assert report.baseline_weight_version_id == BASE_ID
    assert report.operator == 'LINEAR'
    assert report.sensitivity_delta is None      # 默认不跑 Step 8：不用 None 冒充已验证
    assert len(report.attribution) == 16         # 4 策略 x 2 维度 x 2 轨
    assert report.warnings == ()


# --------------------------------------------------------------------------
# V-14 无静默降级：run_id / 上期基线 / 签认值 / 结构 / 算子
# --------------------------------------------------------------------------
def test_run_id_is_mandatory_and_never_invented():
    for bad in (None, '', 'PLACEHOLDER', 'TODO-1'):
        with pytest.raises(whatif.WhatifRunIdError) as exc:
            go(run_id=bad)
        assert exc.value.reason_code == RC.WEIGHT_MISSING_WHATIF_RUN_ID.value


def test_baseline_gate_needs_frozen_and_a_prior_whatif_run_id():
    draft = BASE.model_copy(update={'status': 'DRAFT'})
    with pytest.raises(whatif.WhatifBaselineError) as exc:
        go(base=draft)
    assert exc.value.reason_code == RC.WEIGHT_VERSION_INVALID.value
    for bad in (None, 'PLACEHOLDER'):
        with pytest.raises(whatif.WhatifRunIdError) as exc:
            go(base=weights(BASE_ID, LEVEL1_BASE, LEVEL2_BASE, prior_run_id=bad))
        assert exc.value.reason_code == RC.WEIGHT_MISSING_WHATIF_RUN_ID.value


def test_missing_carriers_raise_and_first_period_must_be_declared():
    with pytest.raises(whatif.WhatifInputError) as exc:
        go(prev_grade=_DROP)
    assert 'prev_grade' in str(exc.value)
    assert exc.value.reason_code == RC.INVARIANT_VIOLATION.value
    with pytest.raises(whatif.WhatifBaselineError) as exc:
        go(prev_grade=None, first_period=False)     # 不从 None 推断首期
    assert exc.value.reason_code == RC.FIRST_PERIOD.value
    report = go(prev_grade=None, first_period=True)  # 显式声明首期 -> 跑通并披露
    assert RC.FIRST_PERIOD.value in report.warnings
    assert report.unchanged_count == 3 and len(report.grade_changes) == 1
    with pytest.raises(whatif.WhatifInputError):
        go(rules=_DROP)


def test_unsigned_governance_values_are_refused():
    with pytest.raises(whatif.WhatifPlaceholderError) as exc:
        go(prev_weight_version_id='PLACEHOLDER')
    assert exc.value.reason_code == RC.CONFIG_PLACEHOLDER.value
    with pytest.raises(whatif.WhatifPlaceholderError):
        go(attainment=None)
    with pytest.raises(whatif.WhatifInputError):
        go(rules={'rows': ()})                      # 不是 GradeRuleSet：不自设门槛
    with pytest.raises(whatif.WhatifInputError):
        whatif.run(CAND, BASE, carriers(), None, 'PLACEHOLDER', run_id=RUN_ID)
    with pytest.raises(whatif.WhatifInputError):
        whatif.run(CAND, BASE, carriers(), None, None, run_id=RUN_ID)


def test_structure_change_and_non_linear_operator_are_refused():
    odd = weights(CAND_ID, LEVEL1_CAND,
                  {'D1': {'m1': Decimal('0.5'), 'm2': Decimal('0.5')},
                   'D2': {'m3': Decimal('0.5'), 'm4': Decimal('0.5')}},
                  status='DRAFT', prior_run_id=None)
    with pytest.raises(whatif.WhatifStructureError) as exc:
        go(cand=odd)
    assert exc.value.reason_code == RC.CONFIG_SEMANTIC_ERROR.value
    with pytest.raises(whatif.WhatifOperatorError) as exc:
        go(aggregate_config={'score_operator': 'GEOMETRIC'})
    assert 'APPROXIMATE_ATTRIBUTION' in str(exc.value)
    with pytest.raises(whatif.WhatifOperatorError):
        go(aggregate_config={'score_operator': 'NON_COMPENSATORY'})


# --------------------------------------------------------------------------
# Step 8（可选）：直接调用 D2，不重实现
# --------------------------------------------------------------------------
def test_sensitivity_delta_calls_d2_and_is_off_by_default():
    assert go().sensitivity_delta is None
    cfg = {'stable_max': '0.05', 'review_max': '0.15'}
    report = whatif.run(CAND, BASE, carriers(sensitivity_config=cfg), None, PERIOD,
                        run_id=RUN_ID, include_sensitivity=True, schemes=('OAT_10',))
    delta = report.sensitivity_delta
    assert delta is not None
    assert [line.scheme for line in delta.by_scheme] == ['OAT_10']
    line = delta.by_scheme[0]
    assert D('0') <= line.baseline_flip_rate <= D('1')
    assert D('0') <= line.whatif_flip_rate <= D('1')
    assert numeric.eq_tol(line.flip_rate_delta,
                          line.whatif_flip_rate - line.baseline_flip_rate, numeric.TOL)
    # 与直接调用 D2 对拍：同一 ArmBase、同一 Step 6 钩子、同一份治理值（不是重实现）
    carrier, grade0 = arm_grades(BASE)
    hook = whatif._grade_hook(carrier['attainment'], carrier['evidence'],
                              carrier['redline'], carrier['prev_grade'],
                              carrier['rules'], None, None)
    direct = sensitivity.run(
        whatif.ArmBase(attainment=carrier['attainment'], normalized=carrier['normalized'],
                       grade=grade0, seed=None),
        ('OAT_10',), cfg, weights=BASE, grade_fn=hook)
    assert numeric.eq_exact(direct.by_scheme[0].overall_flip_rate, line.baseline_flip_rate)
    assert delta.baseline_vetoed == sensitivity.is_vetoed(direct)
    with pytest.raises(whatif.WhatifInputError):
        whatif.run(CAND, BASE, carriers(), None, PERIOD, run_id=RUN_ID,
                   include_sensitivity=True, schemes=('OAT_10',))   # 缺 D2 治理值
    with pytest.raises(whatif.WhatifInputError):
        whatif.run(CAND, BASE, carriers(sensitivity_config=cfg), None, PERIOD,
                   run_id=RUN_ID, include_sensitivity=True)         # 缺方案清单