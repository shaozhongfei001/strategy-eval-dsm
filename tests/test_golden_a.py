'''E2 / tests.test_golden_a -- golden G-01 G-02 G-03 G-04 G-08 G-09 G-13 G-15.

守护点（RUN-UNATTENDED-v3.0 §4 Lane E / E2 行）：
    G-01 正常主路径（A 类证据 + 全指标达标 + 无红线 -> L1）
    G-02 C 类高分被证据门禁拦下 + 分池禁混排
    G-03 贡献极高但越 HARD 红线 -> 强制 L4（非补偿）
    G-04 目标值大面积缺失 -> 绝对轨覆盖不足 -> 封顶 L3
    G-08 策略版本变更 -> VERSION_BREAK / 趋势抑制 / streak 重置
    G-09 missing_rule 四分支（ZERO / SKIP / IMPUTE_MEDIAN / BLOCK）
    G-13 评价设计卡 PARTIAL -> 证据最高只能 C
    G-15 waiver_allowed=true 但缺 approval_id -> 视为未豁免 + WAIVER_INVALID

R-14 纪律（本文件的立身之本）：
  * 每一条期望值都来自 fixtures/（A1 已冻结）的构造 + 本包独立手算，没有任何一个
    期望值是从 dsm/ 实现的输出反填的。手算脚本是 dsm_stage/E2/probe5.py（不入库），
    它只用 fixtures 的 target_value / direction / level1_weights / level2_weights 与
    digest M16 明文的数值口径（每步除法后 q12 = 1e-12 ROUND_HALF_UP）重算，
    不 import 任何 dsm 业务模块。
  * 与 A1 golden_map 的 hand 字段交叉核对：G-01 composite 1.021930、G-02 1.084600、
    G-03 dim CONTRIB 1.900000 三处逐位相同（见各 docstring）。
  * 实现与手算不符时测试保持 RED，缺陷在最终上报里逐条列出，不改期望值迁就实现。

V-9 数值口径：金额/计数为 int 精确比较；比率（Decimal）逐位精确比较，
  另附 1e-12 容差判据，两者都过才算过。

只读事实来源：docs/digest/M31-tests-golden.md（1403-1417 行）、
  docs/digest/M37-examples.md（E1-E5）、docs/digest/M38-k-params.md（K-01~K-20）、
  fixtures/manifest.json、fixtures/golden/golden_map.json、fixtures/input/*.jsonl、
  fixtures/variants/G04_target_missing.json、dsm/models.py（字段名逐字来源）。
'''
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from dsm import aggregate, attainment, evidence, grading, normalize, pooling, redline
from dsm.models import (AnchorSetDoc, DesignCardRow, GradeFrame, GradeRuleRow,
                        MetricDictRow, MetricFactRow, PoolKey, RedlineRow,
                        SensitivityReport, StrategyMasterRow, WeightVersionDoc)
from dsm.reason_codes import RC

# ---------------------------------------------------------------------------
# 治理入参的出处（无一拟定；K-01~K-20 一律不猜，见 M38）
# ---------------------------------------------------------------------------
# * level1/level2 权重、attainment_floor、max_grade_if_no_target、promotion_streak、
#   红线阈值与 forced_grade、anchor_set、biz_domain、design_card 全部逐字取自 fixtures。
# * attainment_cap（K-05，PLACEHOLDER）取 Decimal(2)：A1 golden_map G-03 的 hand
#   「0.80*2.00 + 0.10*2.00 + 0.10*1.00 = 1.90」要求 2.00 处不被裁剪，故 cap >= 2.00；
#   M38 K-05 的建议区间是 1.5-2.0，取其上界。test_g01 另外断言被断言策略在评价期
#   没有任何 capped_flag，故 G-01/G-02/G-04 的期望值与 K-05 的取值无关。
# * min_coverage_for_absolute_track（K-06，PLACEHOLDER）：本包不拟定其值。
#   test_g04 对 0.50/0.60/0.70/0.80/0.90/1 六个候选值逐一断言同一结论
#   （coverage = 6/14 = 0.428571428571 < 门槛 -> 封顶 L3），
#   test_g01 断言 coverage = 1 的策略不被封顶，即结论对 K-06 在 (0.4286, 1] 上任意取值成立。
# * min_pool_size 取契约允许的最小非平凡值 2（[L943] / [L1005]，不属 K-01~K-20）：取 1 时
#   A1 fixtures 里的单例池（如 G-02 的 (CARD, C) 只有 S-003 一条）min-max 参照集零跨度，
#   normalize 判 INACTIVE 不出相对值 -> aggregate 的 composite_relative 为 null ->
#   pooling.build 对「已参评但 composite_relative 为 null」显式抛错，整条主流程走不完；
#   取 2 时单例池按 [L943] 回退到更宽的参照集并挂 SMALL_POOL。本包不断言
#   POOL_TOO_SMALL / SMALL_POOL 的披露面，也不断言任何 composite_relative 的具体数值，
#   故该取值不影响本文件任何被断言的期望值（唯一涉及的 pool_rank 断言是单例池内的第 1 名）。
# * significance_keywords（[L979] 外置可审计清单，非 K-01~K-20 数值）取 fixtures 里
#   design_card.success_criteria 的字面量 'SYNTH_SUCC_CRITERIA'：A1 manifest 的
#   intended_evidence_class 明确 S-001/S-002/S-009 = A，只有该字面量能触发 A 分支。
# * cel_enabled = True：fixtures 的 design_card 已填 experiment_id / incremental_ci_lower /
#   incremental_ci_upper（CEL-0 预留列），RK-15 要求此时 cel.enabled 必须为 true，
#   否则 evidence 层显式抛错（V-14）。这是 fixtures 逼出来的，不是本包选的；
#   evidence_source 仍恒为 CARD_ONLY（[L1895]，v1 无 CEL 计算）。
# * as_of = 2026-09-30：评价期 2026-Q3（fixtures/manifest.json periods.eval）的期末日，
#   H-8 要求由调用方注入而不是取当前时间。
# * soft_deductions = {}：SOFT 扣减幅度是 [L484] 的治理值且契约里没有载体；
#   本包评价期唯一可能越 SOFT 线的是 S-008（M_OPTOUT_RATE 0.095000 > 0.080000），
#   而 S-008 正是 G-09 BLOCK 分支的载体、按 M31 本就不该出分，故被排除在评价期运行之外，
#   其余策略的 M_OPTOUT_RATE 全部 <= 0.080000 -> 不需要任何扣减幅度。
#
# ---------------------------------------------------------------------------
# 已知口径差（只上报，不自行改契约 / 不改 fixtures / 不改他人测试）
# ---------------------------------------------------------------------------
# 1. M31/M37 写 GRADE_CAPPED_NO_TARGET、PL_L1_GATE_EVIDENCE；dsm/reason_codes.py 注册的是
#    GR_CAPPED_NO_TARGET、PRIMARY_POOL_REJECTED_EVIDENCE。models.py 的 ReasonCode 校验只接受
#    注册码，故本文件断言注册码（A1 golden_map 的 G-04 已登记同一缺口）。
# 2. A1 golden_map G-04 的 hand 写 coverage = 6/15 = 0.400000；按 M31 G-10 / P0-5
#    「未签认指标被剔除、coverage 下降」，分母应为已签认指标数 14（M_REPEAT_USE_COUNT 是
#    PENDING），故本包手算 6/14 = 0.428571428571。两个值都低于 K-06 门槛，
#    G-04 的 expects（L3 + capped）不受影响。
# 3. 评价期 2026-Q3 的 S-008 缺 M_COMPLAINT_RATE 事实行（A1 为 G-09 BLOCK 分支故意构造），
#    redline.evaluate 对红线指标缺事实行按 V-14 显式抛错，故除 test_g09 外的 golden 在剔除
#    S-008 的评价期子集上跑。S-008 属 WEALTH 域，composite_absolute / dim / grade / evidence
#    都是逐策略量，剔除它不改变本文件任何被断言的数值；它只影响 WEALTH 池的名次与占比，
#    而本文件不断言这两项。S-008 的 BLOCK 语义由 test_g09 在未剔除的全量评价期输入上守护。
# 4. Step 7 分池在 A1 冻结 fixtures 上无法完成：A1 的证据分布是 A3B3C4D2 跨 4 个业务域，
#    (biz_domain, evidence_class) 必然出现单例池（评价期 (CARD, C) 只有 S-003 一条）。
#    normalize 对单例池的每个指标都拿不到参照尺（min_max 宽度 = 0），按 M43 [L943]
#    「零变异指标 -> INACTIVE，剔除并预警」不出相对值 -> aggregate 的 composite_relative
#    为 null -> pooling.build 对「已参评但 composite_relative 为 null」按 V-14 显式抛错，
#    整条 M29 主流程在 Step 7 中断。两个模块各自都符合自己的 digest，冲突在接缝上，
#    属跨模块缺陷，按 R-1/R-15 只上报、不自行改 dsm/**，归属请主控裁决。
#    本文件的处置：Step1->Step6 的断言照常执行（G-01/G-02/G-03/G-04/G-08/G-09/G-13/G-15
#    的绝大多数期望值都在这一段），Step 7 的异常原文被 Chain.pool_error 完整保留，
#    由 expects 里确实要求 Step 7 的两条 golden（G-01 的 eligible_for_L1_library、
#    G-02 的 rank_in_pool 禁混排）显式判 RED；expects 不涉及分池的 golden
#    （G-03 / G-13 / G-15）按 M31「一条用例只验一个机制」不断言分池。
# 5. A1 fixtures 造不出自己声明的证据分布：fixtures/manifest.json 的 intended_evidence_class
#    是 A3 B3 C4 D2，但 design_card.jsonl 里三条 DID + CONCURRENT_CONTROL 的卡
#    （S-004/v1、S-005/v1、S-005/v2、S-007/v1）alt_method_note 全为 null，
#    interpretation_limit 也全为 null。按 evidence 的五步短路（[L977]）：
#    ③ 准实验要认 B 必须写明方法假设（SDD 没有独立的假设列，[L1171] 的 alt_method_note
#    是唯一载体）-> 判否；④ 落到 C；⑤ C 类未写 interpretation_limit -> 降 D。
#    实测证据分布因此是 A3 B0 C4 D6，B 类为 0，S-005/v2 与 S-007 都成了 NOT_ASSESSED。
#    两边各有依据：manifest 是 A1 自己声明的构造契约，evidence 的规则可追溯到 M23/[L977]；
#    本包判 fixtures 一侧缺口（design_card 少填 alt_method_note），因为 A1 内部自相矛盾，
#    而 evidence 的行为与其 digest 一致。R-1 禁改 fixtures/**，故处置是：
#    G-04 / G-08 先用 R-2 构造出与 manifest.intended_evidence_class 一致的 EvidenceFrame
#    把「封顶 L3」「VERSION_BREAK」两个机制验到底，最后再断言 fixtures 自身的证据分布
#    必须符合 manifest —— 这一条保持 RED，缺陷归 fixtures/input/design_card.jsonl（A1）。

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'fixtures' / 'input'
VARIANTS = ROOT / 'fixtures' / 'variants'

EVAL_PERIOD = '2026-Q3'                                      # manifest.periods.eval
HISTORY_PERIODS = ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')  # manifest.periods.history
AS_OF = date(2026, 9, 30)
BLOCK_SUBJECT = 'S-008'                                      # G-09 BLOCK 分支的载体

ATTAINMENT_CAP = Decimal(2)
ON_ZERO = None
SIGNED_OFF = ('SIGNED',)
NORM_METHOD = 'min_max'
MIN_POOL_SIZE = 2
SD_DOF = 0
SIGNIFICANCE_KEYWORDS = ('SYNTH_SUCC_CRITERIA',)
MIN_COVERAGE_CANDIDATES = (Decimal('0.50'), Decimal('0.60'), Decimal('0.70'),
                           Decimal('0.80'), Decimal('0.90'), Decimal('1'))
TOL = Decimal('1E-12')

ATT_PARAMS = attainment.AttainmentParams(attainment_cap=ATTAINMENT_CAP, on_zero=ON_ZERO,
                                         signed_off_statuses=SIGNED_OFF)
NRM_PARAMS = normalize.NormalizeParams(method=NORM_METHOD, min_pool_size=MIN_POOL_SIZE,
                                       on_zero=ON_ZERO, sd_dof=SD_DOF)
EV_PARAMS = evidence.EvidenceParams(evidence_mode='GATE_ONLY', cel_enabled=True,
                                    significance_keywords=SIGNIFICANCE_KEYWORDS)
POOL_PARAMS = pooling.PoolingParams(min_pool_size=MIN_POOL_SIZE)
# Step 8 的产物按 R-2 直接构造：pooling.flip_rate_unusable 只看 FLIP_RATE_UNUSABLE 标志，
# 本包不验稳健性（G-05/G-06 属 E3），故构造一份无否决标志的报告；K-11 不参与任何断言。
NO_VETO_SENSITIVITY = SensitivityReport(by_scheme=(), by_strategy=())

def _code(value):
    '''ReasonCode 载体 -> 逐字码值（CONTEXT-BRIEF 5.1：比对 / 写 CSV 用 .value）。'''
    return getattr(value, 'value', value)


def _jsonl(path):
    text = Path(path).read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _rows(raw, model):
    return tuple(model(**item) for item in raw)


def _ratio_close(actual, expected):
    '''V-9：比率既逐位精确相等，又满足 1e-12 容差；两者都过才算过。'''
    return actual == expected and abs(actual - expected) <= TOL


@pytest.fixture(scope='module')
def fx():
    '''A1 冻结的 8 张输入表，逐字构造为 dsm/models.py 的契约行（R-2：字段名逐字抄）。'''
    raw = {name: _jsonl(INPUT / (name + '.jsonl')) for name in
           ('strategy_master', 'metric_dict', 'metric_fact', 'design_card',
            'redline', 'grade_rule', 'anchor_set', 'weight_version')}
    return {
        'raw': raw,
        'master': _rows(raw['strategy_master'], StrategyMasterRow),
        'metric_dict': _rows(raw['metric_dict'], MetricDictRow),
        'facts': _rows(raw['metric_fact'], MetricFactRow),
        'cards': _rows(raw['design_card'], DesignCardRow),
        'redlines': _rows(raw['redline'], RedlineRow),
        'grade_rules': _rows(raw['grade_rule'], GradeRuleRow),
        'weights': WeightVersionDoc(**raw['weight_version'][0]),
        'anchor': AnchorSetDoc(**raw['anchor_set'][0]),
    }


def _rules(rows, min_coverage):
    return grading.GradeRuleSet(rows=tuple(rows),
                                min_coverage_for_absolute_track=min_coverage)


def _pool_map(ev_frame, master):
    '''normalize.compute 的必填入参 pools：strategy_id -> PoolKey（[L1001]）。
    biz_domain 取自 T1，evidence_class 取自 Step 3，两者都不是 normalize 能自己读的。'''
    domain = {}
    for row in master:
        domain.setdefault(row.strategy_id, row.biz_domain)
    return {r.strategy_id: PoolKey(biz_domain=domain[r.strategy_id],
                                   evidence_class=r.evidence_class)
            for r in ev_frame.rows}


class Chain:
    '''一期主流程 Step1->Step7 的产物集合（M29 九步里本包需要的七步）。'''

    def __init__(self, att, nrm, scores, ev, rl, plan, pools, stats, pool_error=None):
        self.att, self.nrm, self.scores = att, nrm, scores
        self.ev, self.rl, self.plan = ev, rl, plan
        self.grades, self.streaks = plan.frame, plan.streaks
        self.pools, self.stats = pools, stats
        # Step 7 的显式失败记录：None = 分池成功；非 None = pooling.build 抛出的原文。
        # 这不是静默降级（V-14）——异常原文被完整保留，并由 test_g01 / test_g02 的
        # `assert chain.pool_error is None` 逐条判 RED，缺陷在上报里点名。
        self.pool_error = pool_error

    def _one(self, rows, key, what):
        hits = [r for r in rows if key(r)]
        assert len(hits) == 1, '期望唯一 ' + what + ' 行'
        return hits[0]

    def score(self, sid, vid='v1', period=EVAL_PERIOD):
        return self._one(self.scores.rows,
                         lambda r: (r.strategy_id, r.version_id, r.period)
                         == (sid, vid, period), 'score')

    def grade(self, sid, vid='v1', period=EVAL_PERIOD):
        return self._one(self.grades.rows,
                         lambda r: (r.strategy_id, r.version_id, r.period)
                         == (sid, vid, period), 'grade')

    def pool(self, sid, vid='v1', period=EVAL_PERIOD):
        return self._one(self.pools.rows,
                         lambda r: (r.strategy_id, r.version_id, r.period)
                         == (sid, vid, period), 'pool')

    def evidence(self, sid, vid='v1'):
        return self._one(self.ev.rows,
                         lambda r: (r.strategy_id, r.version_id) == (sid, vid), 'evidence')

    def redline(self, sid, metric_id, vid='v1', period=EVAL_PERIOD):
        return self._one(self.rl.rows,
                         lambda r: (r.strategy_id, r.version_id, r.period, r.metric_id)
                         == (sid, vid, period, metric_id), 'redline')

    def attain(self, sid, metric_id, vid='v1', period=EVAL_PERIOD):
        return [r for r in self.att.rows if (r.strategy_id, r.version_id, r.period,
                                             r.metric_id) == (sid, vid, period, metric_id)]


def _manifest_evidence(ev_frame):
    '''把 EvidenceFrame 修成 fixtures/manifest.json 声明的 intended_evidence_class（R-2）。

    只在实测等级与 manifest 不一致时改写该行（实测一致的逐字保留），改写后的
    evidence_reason 取该等级在 [L977] 五步里的注册码：B -> EV_B_QUASI。
    这是口径差 5 的隔离手段，不是迁就实现：manifest 是 A1 自己冻结的构造契约。
    '''
    intended = json.loads((ROOT / 'fixtures' / 'manifest.json').read_text(
        encoding='utf-8'))['intended_evidence_class']
    out = []
    for row in ev_frame.rows:
        want = intended.get(row.strategy_id)
        if want is None or want == row.evidence_class:
            out.append(row)
            continue
        out.append(row.model_copy(update={
            'evidence_class': want,
            'evidence_reason': RC.EV_B_QUASI.value if want == 'B' else row.evidence_reason,
        }))
    return type(ev_frame)(rows=tuple(out))


def _run_period(fx, period, *, metric_dict=None, facts=None, min_coverage=Decimal('0.60'),
                prev=None, streaks=None, waivers=(), exclude=(), with_pools=True,
                manifest_evidence=False):
    '''跑一期 Step1->Step7。exclude 里的 strategy_id 从事实表剔除（见口径差 3）；
    with_pools=False 时只跑到 Step6（历史期只需要上期台账与滞回状态）。'''
    md = tuple(metric_dict if metric_dict is not None else fx['metric_dict'])
    source = tuple(facts if facts is not None else fx['facts'])
    period_facts = tuple(r for r in source
                         if r.period == period and r.strategy_id not in exclude)
    ev = evidence.classify(fx['cards'], period_facts, params=EV_PARAMS)
    if manifest_evidence:
        ev = _manifest_evidence(ev)
    att = attainment.compute(period_facts, md, params=ATT_PARAMS,
                             anchor_set=fx['anchor'])
    nrm = normalize.compute(att, md, fx['anchor'], params=NRM_PARAMS,
                            pools=_pool_map(ev, fx['master']))
    scores = aggregate.compose(att, nrm, fx['weights'], None)
    rl = redline.evaluate(period_facts, redline.RedlineSet(rows=fx['redlines']),
                          redline.WaiverSet(rows=tuple(waivers)), as_of=AS_OF,
                          soft_deductions={}, metric_dict=md)
    plan = grading.plan(scores, att, ev, rl, prev,
                        _rules(fx['grade_rules'], min_coverage), streaks=streaks)
    pools = stats = None
    pool_error = None
    if with_pools:
        try:
            pools, stats = pooling.build(scores, plan.frame, ev, fx['master'], None,
                                         sensitivity=NO_VETO_SENSITIVITY,
                                         params=POOL_PARAMS)
        except pooling.PoolingInputError as exc:
            pool_error = type(exc).__name__ + ': ' + str(exc)
    return Chain(att, nrm, scores, ev, rl, plan, pools, stats, pool_error)


@pytest.fixture(scope='module')
def history(fx):
    '''用 A1 的 4 期历史（manifest.periods.history）按期串出上期台账与滞回状态。

    这是 M29「主流程按期串起来」的用法，也是 G-01「reason_codes 为空」的前提：
    fixtures 里没有上期 grade_ledger 文件，若 prev = None，grading 会按 io_loaders/M21
    的明文记 FIRST_PERIOD（INFO），G-01 的空 reason_codes 就无从谈起。
    历史期的等级由同一条链在历史事实表上算出，不是本包拟定的数。
    '''
    prev, streaks = None, None
    for period in HISTORY_PERIODS:
        chain = _run_period(fx, period, prev=prev, streaks=streaks, with_pools=False)
        prev = GradeFrame(rows=tuple((prev.rows if prev else ()) + chain.grades.rows))
        streaks = chain.streaks
    return prev, streaks


@pytest.fixture(scope='module')
def base(fx, history):
    '''评价期 2026-Q3 的基准运行（剔除 G-09 BLOCK 载体 S-008，见口径差 3）。'''
    prev, streaks = history
    return _run_period(fx, EVAL_PERIOD, prev=prev, streaks=streaks,
                       exclude=(BLOCK_SUBJECT,))

# --------------------------------------------------------------------------
# G-01  正常主路径：A 类证据 + 全指标达标 + 无红线 -> L1
# --------------------------------------------------------------------------
def test_g01_a_evidence_all_targets_met_no_redline_grades_l1(fx, base):
    '''G-01（M31 1403 行 / M37 E1）：A 类证据 + 全指标达标 + 无红线 -> grade = L1。

    手算（S-001/v1 在 2026-Q3 有 15 条事实行，全部有目标值；value / target_value /
    direction 逐字取自 fixtures，权重逐字取自 weight_version.jsonl；direction = +1 取
    actual/target，-1 取 target/actual，每步除法后 q12 ROUND_HALF_UP）：
      CONTRIB = 0.80*a(M_REV_MINOR) + 0.10*a(M_CUST_GAIN) + 0.10*a(M_AUM_MINOR)
              = 1.001000000000
      EFFIC   = 0.40*a(M_ROI) + 0.30*a(M_CONV_RATE) + 0.30*a(M_COST_PER_CONV_MINOR)
              = 1.027000000000
      EXPER   = 0.40*a(M_COMPLAINT_RATE) + 0.40*a(M_CONTACT_FREQ_PER_30D)
                + 0.20*a(M_SATISFY_SCORE) = 1.016000000000
      COST    = 0.50*a(M_CAMPAIGN_COST_MINOR) + 0.50*a(M_HANDLE_SEC) = 1.000000000000
      SUST    = 0.50*a(M_RETENTION_RATE) + 0.50*a(M_REPEAT_USE_COUNT) = 1.115000000000
      PROC    = 0.50*a(M_REACH_RATE) + 0.50*a(M_OPTOUT_RATE) = 1.065000000000
      composite_absolute
        = 0.30*1.001000000000 + 0.21*1.027000000000 + 0.21*1.016000000000
          + 0.14*1.000000000000 + 0.07*1.115000000000 + 0.07*1.065000000000
        = 0.300300000000 + 0.215670000000 + 0.213360000000 + 0.140000000000
          + 0.078050000000 + 0.074550000000
        = 1.021930000000
      与 A1 golden_map G-01 的 hand.composite_absolute = 1.021930 逐位相同。
      等级：grade_rule.jsonl 的 attainment_floor L1 = 1.00，1.021930000000 >= 1.00
        -> 基础等级 L1；证据 A 不触发 Step 2 封顶；coverage = 1 不低于 K-06 门槛
        -> 不触发 Step 3 封顶；三条红线均未越（M_CONTACT_FREQ_PER_30D 2 <= 4、
        M_COMPLAINT_RATE 0.002000 <= 0.005000、M_OPTOUT_RATE 0.039900 <= 0.080000）
        -> 无 Step 4 forced；上期（2026-Q2）同版本有台账 -> 非 FIRST_PERIOD、
        非 VERSION_BREAK；L1 行 promotion_streak = 1，含本期的连续达标期数 >= 1
        -> 不触发 GR_STREAK_NOT_MET。=> grade = L1 且 grade_reason_path 为空
        （M31「reason_codes 为空」）。
      coverage：分母 = metric_dict 里 signoff_status = SIGNED 的 14 个指标
        （M_REPEAT_USE_COUNT 是 PENDING，按 M31 G-10 / P0-5 剔除，不进分子也不进分母），
        分子 = 14（14 个已签认指标全部有目标值且全部产出 attainment）-> 14/14 = 1。
      aggregate 侧 coverage = 15/15 = 1（15 个指标全部产出绝对轨值）。
    '''
    score = base.score('S-001')
    assert _ratio_close(score.composite_absolute, Decimal('1.021930000000'))
    expected_dims = {'CONTRIB': Decimal('1.001000000000'),
                     'EFFIC': Decimal('1.027000000000'),
                     'EXPER': Decimal('1.016000000000'),
                     'COST': Decimal('1.000000000000'),
                     'SUST': Decimal('1.115000000000'),
                     'PROC': Decimal('1.065000000000')}
    assert set(score.dim_absolute) == set(expected_dims)
    for dim, value in expected_dims.items():
        assert _ratio_close(score.dim_absolute[dim], value), dim
    assert _ratio_close(score.coverage, Decimal(1))
    assert _ratio_close(base.att.attainment_coverage['S-001'], Decimal(1))

    ev = base.evidence('S-001')
    assert ev.evidence_class == 'A'
    assert _code(ev.evidence_reason) == _code(RC.EV_A_RANDOMIZED)
    assert ev.evidence_source == 'CARD_ONLY'

    for metric_id in ('M_CONTACT_FREQ_PER_30D', 'M_COMPLAINT_RATE', 'M_OPTOUT_RATE'):
        row = base.redline('S-001', metric_id)
        assert row.hit is False, metric_id
        assert row.reason_code is None, metric_id
        assert row.forced_grade is None, metric_id

    grade = base.grade('S-001')
    assert grade.grade == 'L1'
    assert grade.capped is False
    assert grade.cap_reason is None
    assert grade.grade_reason_path == ()
    assert grade.usable_for_elimination is True

    # eligible_for_L1_library = true 的载体是 PoolRow.primary_pool_eligible（[L1005]）。
    assert base.pool_error is None, 'Step 7 分池未能完成（口径差 4）：' + str(base.pool_error)
    pool_row = base.pool('S-001')
    assert pool_row.pool_key == PoolKey(biz_domain='CARD', evidence_class='A')
    assert pool_row.primary_pool_eligible is True
    assert pool_row.reject_reason is None
    # K-05 无关性：cap = 2 时 S-001 在评价期没有任何被裁剪的达成率。
    assert not any(r.capped_flag for r in base.att.rows if r.strategy_id == 'S-001')


# --------------------------------------------------------------------------
# G-02  C 类高分被证据门禁拦下 + 分池禁混排
# --------------------------------------------------------------------------
def test_g02_c_class_high_score_is_gated_to_l2_and_ranked_only_in_c_pool(fx, base):
    '''G-02（M31 1404 行 / M37 E2）：C 类高分 -> L2 + 不进一级库 + 只在 (CARD, C) 池内排名。

    手算（S-003/v1，2026-Q3，15 条事实行全部有目标值）：
      CONTRIB 1.135000000000 / EFFIC 1.105000000000 / EXPER 1.030000000000
      COST 1.000000000000 / SUST 1.150000000000 / PROC 1.075000000000
      composite_absolute
        = 0.30*1.135000000000 + 0.21*1.105000000000 + 0.21*1.030000000000
          + 0.14*1.000000000000 + 0.07*1.150000000000 + 0.07*1.075000000000
        = 0.340500000000 + 0.232050000000 + 0.216300000000 + 0.140000000000
          + 0.080500000000 + 0.075250000000
        = 1.084600000000
      与 A1 golden_map G-02 的 hand.composite_absolute = 1.084600 逐位相同；
      1.084600000000 >= L1 门槛 1.00 -> 基础等级 L1，所以降级只能来自证据门禁，不来自分数。
      证据：design_card 是 COMPLETE + control_arrangement NONE +
        eval_method OBSERVATIONAL_ONLY -> 五步短路 ①②③ 全判否 -> ④ 给 C；
        interpretation_limit 非空 -> ⑤ 不降 D。=> evidence_class = C。
      Step 2：C 类最高 L2 -> grade = L2，capped = true，cap_reason = GR_EVIDENCE_GATE_L1。
      Step 7：pool_key = (T1.biz_domain = CARD, Step3.evidence_class = C)；
        一级库门禁要求 evidence_class 属 GATE_EVIDENCE_CLASSES，C 不满足
        -> primary_pool_eligible = false，reject_reason = PRIMARY_POOL_REJECTED_EVIDENCE
        （M37 E2 写作 PL_L1_GATE_EVIDENCE，见口径差 1）。
      禁混排（P0-7 / P-6）：CARD 域三条策略的证据等级是 S-001 A、S-002 A、S-003 C
        （fixtures/manifest.json intended_evidence_class），所以 (CARD, C) 池里只有
        S-003 一条、pool_rank = 1；S-001 / S-002 必须落在 (CARD, A) 池，
        绝不与 S-003 同池同序。
    '''
    score = base.score('S-003')
    assert _ratio_close(score.composite_absolute, Decimal('1.084600000000'))
    l1_floor = [r for r in fx['grade_rules'] if r.grade_code == 'L1'][0].attainment_floor
    assert l1_floor == Decimal('1.00')
    assert score.composite_absolute >= l1_floor, '降级只能来自证据门禁，不来自分数'

    ev = base.evidence('S-003')
    assert ev.evidence_class == 'C'
    assert _code(ev.evidence_reason) == _code(RC.EV_C_OBSERVATIONAL)
    assert ev.interpretation_limit is not None and ev.interpretation_limit.strip()

    grade = base.grade('S-003')
    assert grade.grade == 'L2'
    assert grade.capped is True
    assert _code(grade.cap_reason) == _code(RC.GR_EVIDENCE_GATE_L1)
    assert tuple(_code(c) for c in grade.grade_reason_path) == (_code(RC.GR_EVIDENCE_GATE_L1),)

    assert base.pool_error is None, 'Step 7 分池未能完成（口径差 4）：' + str(base.pool_error)
    pool_row = base.pool('S-003')
    assert pool_row.pool_key == PoolKey(biz_domain='CARD', evidence_class='C')
    assert pool_row.primary_pool_eligible is False
    assert _code(pool_row.reject_reason) == _code(RC.PRIMARY_POOL_REJECTED_EVIDENCE)
    assert pool_row.pool_rank == 1

    groups = pooling.groups(base.pools)
    c_pool = groups[PoolKey(biz_domain='CARD', evidence_class='C')]
    assert tuple((r.strategy_id, r.version_id) for r in c_pool) == (('S-003', 'v1'),)
    a_pool = groups[PoolKey(biz_domain='CARD', evidence_class='A')]
    assert {r.strategy_id for r in a_pool} == {'S-001', 'S-002'}
    # 禁混排的读侧保证：任一池内所有行的证据等级恒等于池键的证据等级。
    for key, rows in groups.items():
        assert all(base.evidence(r.strategy_id, r.version_id).evidence_class
                   == key.evidence_class for r in rows), key

# --------------------------------------------------------------------------
# G-03  非补偿：贡献极高但越 HARD 红线 -> 强制 L4
# --------------------------------------------------------------------------
def test_g03_hard_redline_forces_l4_and_composite_stays_but_does_not_count(fx, base):
    '''G-03（M31 1405 行 / M37 E3）：CONTRIB 1.9 + 双越 HARD 红线 -> 强制 L4，分数照算不生效。

    手算（S-009/v1，2026-Q3）：
      a(M_REV_MINOR) = 20000/10000 = 2.000000000000；a(M_AUM_MINOR) = 20000/10000
        = 2.000000000000；a(M_CUST_GAIN) = 100/100 = 1.000000000000
      CONTRIB = 0.80*2.000000000000 + 0.10*2.000000000000 + 0.10*1.000000000000
              = 1.600000000000 + 0.200000000000 + 0.100000000000 = 1.900000000000
      与 A1 golden_map G-03 的 hand.dim_CONTRIB = 1.900000 逐位相同（M31 要求 1.9）。
      EXPER = 0.40*(0.002000/0.008000) + 0.40*(2/6) + 0.20*1.400000000000
            = 0.40*0.250000000000 + 0.40*0.333333333333 + 0.280000000000
            = 0.100000000000 + 0.133333333333 + 0.280000000000 = 0.513333333333
      EFFIC 1.280000000000 / COST 1.000000000000 / SUST 1.400000000000 / PROC 1.200000000000
      composite_absolute
        = 0.30*1.900000000000 + 0.21*1.280000000000 + 0.21*0.513333333333
          + 0.14*1.000000000000 + 0.07*1.400000000000 + 0.07*1.200000000000
        = 0.570000000000 + 0.268800000000 + 0.107800000000 + 0.140000000000
          + 0.098000000000 + 0.084000000000
        = 1.268600000000
      红线（阈值逐字取自 fixtures/input/redline.jsonl，comparator 均为 GT）：
        M_CONTACT_FREQ_PER_30D 实际 6 > HARD 阈值 4            -> 越线，forced_grade L4
        M_COMPLAINT_RATE       实际 0.008000 > HARD 阈值 0.005000 -> 越线，forced_grade L4
        M_OPTOUT_RATE          实际 0.039900 <= SOFT 阈值 0.080000 -> 未越线
      Step 4 非补偿：两条 HARD 命中取最严 forced_grade = L4 -> grade = L4，
        capped = true，cap_reason = GR_REDLINE_FORCED；
        而 composite_absolute = 1.268600000000 照样输出（M31「仍输出但不生效」）。
      Step 7：redline_ok 不成立 -> primary_pool_eligible = false，
        reject_reason = REDLINE_HARD_HIT（BLOCK 先于 WARN 的单槽优先序）。
    '''
    score = base.score('S-009')
    assert _ratio_close(score.composite_absolute, Decimal('1.268600000000'))
    assert _ratio_close(score.dim_absolute['CONTRIB'], Decimal('1.900000000000'))
    assert _ratio_close(score.dim_absolute['EXPER'], Decimal('0.513333333333'))

    contact = base.redline('S-009', 'M_CONTACT_FREQ_PER_30D')
    assert contact.level == 'HARD'
    assert contact.hit is True
    assert contact.forced_grade == 'L4'
    assert _code(contact.reason_code) == 'REDLINE_HARD_M_CONTACT_FREQ_PER_30D'
    assert int(contact.threshold_value) == 4                 # 计数：int 精确（V-9）

    complaint = base.redline('S-009', 'M_COMPLAINT_RATE')
    assert complaint.level == 'HARD' and complaint.hit is True
    assert complaint.forced_grade == 'L4'
    assert _code(complaint.reason_code) == 'REDLINE_HARD_M_COMPLAINT_RATE'
    assert complaint.threshold_value == Decimal('0.005000')  # 比率：Decimal 精确

    optout = base.redline('S-009', 'M_OPTOUT_RATE')
    assert optout.level == 'SOFT' and optout.hit is False

    grade = base.grade('S-009')
    assert grade.grade == 'L4'
    assert grade.capped is True
    assert _code(grade.cap_reason) == _code(RC.GR_REDLINE_FORCED)
    assert _code(RC.GR_REDLINE_FORCED) in tuple(_code(c) for c in grade.grade_reason_path)
    # 非补偿（P0-2 / V-6）的关键断言：分数在，但等级不由分数决定。
    assert score.composite_absolute >= Decimal('1.00') and grade.grade == 'L4'

    # M31 G-03 的 expects 只有 grade/redline_pass/composite「仍输出但不生效」，
    # 不含分池，故按「一条用例只验一个机制」不断言 Step 7（见口径差 4）。
    assert tuple(r.metric_id for r in redline.hard_vetoes(base.rl)
                 if r.strategy_id == 'S-009') == ('M_COMPLAINT_RATE',
                                                  'M_CONTACT_FREQ_PER_30D')


# --------------------------------------------------------------------------
# G-04  目标值大面积缺失 -> 绝对轨覆盖不足 -> 封顶 L3
# --------------------------------------------------------------------------
def test_g04_target_missing_caps_grade_to_l3_for_every_k06_candidate(fx, history):
    '''G-04（M31 1406 行 / M37 E4）：variant G04_target_missing 下 S-007 封顶 L3。

    输入构造（fixtures/variants/G04_target_missing.json 的 replace.metric_dict 逐字使用，
    本包不新造也不修改 fixtures）：9/15 = 0.600000 的指标 target_value 置空，跨
      EFFIC（M_ROI / M_CONV_RATE / M_COST_PER_CONV_MINOR）、
      EXPER（M_COMPLAINT_RATE / M_CONTACT_FREQ_PER_30D / M_SATISFY_SCORE）、
      COST（M_CAMPAIGN_COST_MINOR / M_HANDLE_SEC）、SUST（M_REPEAT_USE_COUNT）四个维度；
    仍有目标值的 6 个是 M_REV_MINOR / M_CUST_GAIN / M_AUM_MINOR（CONTRIB）、
      M_RETENTION_RATE（SUST）、M_REACH_RATE / M_OPTOUT_RATE（PROC）。
    手算（S-007/v1，2026-Q3）：
      a(M_REV_MINOR) = 9354/10000 = 0.935400000000；a(M_CUST_GAIN) = 96/100
        = 0.960000000000；a(M_AUM_MINOR) = 10000/10000 = 1.000000000000
        -> CONTRIB = 0.80*0.935400000000 + 0.10*0.960000000000 + 0.10*1.000000000000
                   = 0.748320000000 + 0.096000000000 + 0.100000000000 = 0.944320000000
      a(M_RETENTION_RATE) = 0.486000/0.600000 = 0.810000000000；M_REPEAT_USE_COUNT 无目标值
        -> SUST 只剩一个指标，按 [L954] 维度内重归一 0.50/0.50 = 1 -> SUST = 0.810000000000
      a(M_REACH_RATE) = 0.616000/0.800000 = 0.770000000000；a(M_OPTOUT_RATE)
        = 0.039900/0.040698 = 0.980392156863（direction = -1，故 target/actual）
        -> PROC = 0.50*0.770000000000 + 0.50*0.980392156863
                = 0.385000000000 + 0.490196078432 = 0.875196078432
      EFFIC / EXPER / COST 三个维度被清空 -> 按 [L954] W_d = 0，其余 W_d 重归一：
        可用权重合计 = 0.30 + 0.07 + 0.07 = 0.44；0.30/0.44 = 0.681818181818；
        0.07/0.44 = 0.159090909091
        composite_absolute = 0.681818181818*0.944320000000
                             + 0.159090909091*0.810000000000
                             + 0.159090909091*0.875196078432
                           = 0.643854545455 + 0.128863636364 + 0.139235739750
                           = 0.911953921569
      attainment_coverage：分子 = 6（6 个有目标值的指标全部 SIGNED 且全部产出 attainment），
        分母 = 14（metric_dict 里 SIGNED 的指标数；M_REPEAT_USE_COUNT 是 PENDING，按
        M31 G-10 / P0-5 既不进分子也不进分母）-> 6/14 = 0.428571428571。
        A1 golden_map 的 hand 写 6/15 = 0.400000，差异见口径差 2；两个值都低于 K-06
        候选区间的下界 0.50，故本条 expects 与该口径差无关。
      等级：0.90 <= 0.911953921569 < 1.00 -> 基础等级 L2（floor 逐字取自 grade_rule.jsonl）；
        证据 B（COMPLETE + CONCURRENT_CONTROL + DID + alt_method_note 非空）不触发 Step 2；
        coverage 0.428571428571 < K-06 -> Step 3 封到基础等级所在行的
        max_grade_if_no_target，L2 行逐字为 "max_grade_if_no_target":"L3"；
        L3 比 L2 差 -> grade = L3，capped = true，cap_reason = GR_CAPPED_NO_TARGET。
      composite_relative 仍给出（M31「仍给出（池内参考）」）：相对轨不依赖 target_value。
      无目标值的指标必须留 null 并挂 NO_TARGET_VALUE，绝不用均值或 0 代替（[L930] / H-6）。
    K-06 是 PLACEHOLDER 治理参数（M38），本包不拟定其值：对 0.50/0.60/0.70/0.80/0.90/1
    六个候选值逐一重跑 Step 6，结论必须完全一致。
    '''
    variant = json.loads((VARIANTS / 'G04_target_missing.json').read_text(encoding='utf-8'))
    replaced = {row['metric_id']: row for row in variant['replace']['metric_dict']}
    assert len(replaced) == 9, 'A1 构造：9/15 指标 target_value 置空'
    assert all(row['target_value'] is None for row in replaced.values())
    md = tuple(MetricDictRow(**replaced.get(row['metric_id'], row))
               for row in fx['raw']['metric_dict'])

    prev, streaks = history
    # manifest_evidence=True：隔离口径差 5（fixtures 造不出 B 类证据），先把 G-04 的
    # 封顶机制本身验到底；fixtures 自身的证据分布缺陷在本测试最后单独判 RED。
    chain = _run_period(fx, EVAL_PERIOD, metric_dict=md, prev=prev, streaks=streaks,
                        exclude=(BLOCK_SUBJECT,), with_pools=False, manifest_evidence=True)

    assert _ratio_close(chain.att.attainment_coverage['S-007'], Decimal('0.428571428571'))
    score = chain.score('S-007')
    assert _ratio_close(score.composite_absolute, Decimal('0.911953921569'))
    assert set(score.dim_absolute) == {'CONTRIB', 'PROC', 'SUST'}
    assert _ratio_close(score.dim_absolute['CONTRIB'], Decimal('0.944320000000'))
    assert _ratio_close(score.dim_absolute['SUST'], Decimal('0.810000000000'))
    assert _ratio_close(score.dim_absolute['PROC'], Decimal('0.875196078432'))
    nulled = {r.metric_id for r in chain.att.rows
              if r.strategy_id == 'S-007' and r.period == EVAL_PERIOD and r.attainment is None}
    assert nulled == set(replaced), 'null 集合必须恰为被置空的 9 个指标'
    assert all(_code(r.reason_code) == _code(RC.NO_TARGET_VALUE) and r.has_target is False
               for r in chain.att.rows if r.strategy_id == 'S-007'
               and r.period == EVAL_PERIOD and r.metric_id in replaced)

    for min_coverage in MIN_COVERAGE_CANDIDATES:
        plan = grading.plan(chain.scores, chain.att, chain.ev, chain.rl, prev,
                            _rules(fx['grade_rules'], min_coverage), streaks=streaks)
        row = [r for r in plan.frame.rows
               if (r.strategy_id, r.period) == ('S-007', EVAL_PERIOD)][0]
        assert row.grade == 'L3', 'K-06 = ' + str(min_coverage)
        assert row.capped is True, 'K-06 = ' + str(min_coverage)
        assert _code(row.cap_reason) == _code(RC.GR_CAPPED_NO_TARGET), 'K-06 = ' + str(min_coverage)

    # M31 G-04 expects 的第 4 项「composite_relative 仍给出（池内参考）」：
    # 相对轨不依赖 target_value，本应非空；实测为 null 的根因是口径差 4
    # （(WEALTH, B) 是单例池 -> 全部指标 INACTIVE -> 相对轨无定义）。
    assert score.composite_relative is not None, (
        'M31 G-04：composite_relative 仍给出（池内参考）；实测 null（dim_relative = '
        + str(score.dim_relative) + '），根因见口径差 4：(WEALTH, B) 是单例池，'
        'normalize 按 M43 [L943] 判全部指标 INACTIVE，相对轨无定义')

    # 口径差 5：fixtures 自身的证据分布必须符合 A1 冻结的 manifest.intended_evidence_class。
    raw_ev = evidence.classify(
        fx['cards'],
        tuple(r for r in fx['facts']
              if r.period == EVAL_PERIOD and r.strategy_id != BLOCK_SUBJECT),
        params=EV_PARAMS)
    intended = json.loads((ROOT / 'fixtures' / 'manifest.json').read_text(
        encoding='utf-8'))['intended_evidence_class']
    mismatch = sorted((r.strategy_id, r.version_id, r.evidence_class, intended[r.strategy_id])
                      for r in raw_ev.rows
                      if intended.get(r.strategy_id) not in (None, r.evidence_class))
    assert not mismatch, (
        'fixtures/input/design_card.jsonl 造不出 manifest.intended_evidence_class '
        '（A1 内部自相矛盾，口径差 5）；(strategy, version, 实测, 应为) = ' + str(mismatch))

# --------------------------------------------------------------------------
# G-08  版本断点
# --------------------------------------------------------------------------
def test_g08_version_change_marks_break_suppresses_trend_and_resets_streak(fx, base,
                                                                          history):
    '''G-08（M31 1410 行）：S-005 同 strategy_id 换 version_id -> VERSION_BREAK。

    输入构造（A1 deliberate_constructions n=4，全部逐字来自 fixtures）：
      strategy_master 里 S-005 有两行：v1 status = RETIRED、offline_date = 2026-06-30；
      v2 status = ACTIVE、version_change_note = 'SYNTH-VERSION-BREAK: 触达方式与客群规则调整'。
      metric_fact 里 S-005/v1 只有 4 期历史（2025-Q3..2026-Q2，各 15 条），
      S-005/v2 只有评价期 2026-Q3（14 条，M_CAMPAIGN_COST_MINOR 缺格 = G-09 ZERO 载体）。
    手算 / 推导：
      上期台账（由同一条链在 4 期历史事实表上按期算出）里 S-005 的 4 行 version_id 全是 v1，
      评价期的 score 行是 v2 -> 「同 strategy_id 的历史存在、但没有同 version_id 的历史」
      => version_break = true => 记 GR_VERSION_BREAK。
      趋势抑制：version_break 为真时上期等级不作为保持基线（baseline = None），
        所以 Step 5 滞回不参与、GR_STREAK_NOT_MET 不得出现，本期等级只由本期
        composite_absolute 决定：
        coverage = 13/14 = 0.928571428571（14 条事实行里 M_REPEAT_USE_COUNT 是 PENDING，
          不进分子；分母 = 14 个 SIGNED 指标）>= K-06 候选区间下界 0.50 -> 不触发 Step 3；
        证据 B（COMPLETE + CONCURRENT_CONTROL + DID + alt_method_note 非空）-> 不触发 Step 2；
        三条红线均未越 -> 无 Step 4 forced；
        composite_absolute 落在 [0.70, 0.90) -> 基础等级 L3 => grade = L3。
        本条不断言 composite_absolute 的具体值：它取决于 G-09 的 ZERO 分支是否被实现
        （属 test_g09 的守护面），而两个候选值 0.826551606617（ZERO 按 0 计入）与
        0.882433959559（缺格被当 SKIP 重归一）都落在 [0.70, 0.90)，故 grade = L3 与该缺陷无关。
      streak 重置：滞回状态的键是 strategy_id|version_id（grading.streak_key），v2 是新键
        -> 含本期在内的连续达标期数从 1 重新数；S-005/v1 在 4 期历史里已积累过计数，
        故 v2 的 count 必须恰为 1，且 v1 的键不得出现在评价期的 streaks 里。
    '''
    master = {(r.strategy_id, r.version_id): r for r in fx['master']}
    assert master[('S-005', 'v1')].status == 'RETIRED'
    assert master[('S-005', 'v1')].offline_date == date(2026, 6, 30)
    assert master[('S-005', 'v2')].status == 'ACTIVE'
    note = master[('S-005', 'v2')].version_change_note
    assert note is not None and note.strip()

    prev, streaks = history
    prior = [r for r in prev.rows if r.strategy_id == 'S-005']
    assert len(prior) == 4, 'A1 构造：4 期历史'
    assert {r.version_id for r in prior} == {'v1'}
    assert all(r.period in HISTORY_PERIODS for r in prior)
    assert not [r for r in fx['facts'] if r.strategy_id == 'S-005'
                and r.version_id == 'v1' and r.period == EVAL_PERIOD]

    # manifest_evidence=True：隔离口径差 5（S-005/v2 在 fixtures 上被判 D -> NOT_ASSESSED，
    # 版本断点的代码路径根本走不到），先把 G-08 的机制验到底；fixtures 缺陷在本测试最后判 RED。
    own = _run_period(fx, EVAL_PERIOD, prev=prev, streaks=streaks,
                      exclude=(BLOCK_SUBJECT,), with_pools=False, manifest_evidence=True)
    assert own.evidence('S-005', 'v2').evidence_class == 'B'

    grade = own.grade('S-005', 'v2')
    path_codes = tuple(_code(c) for c in grade.grade_reason_path)
    assert _code(RC.GR_VERSION_BREAK) in path_codes
    assert _code(RC.GR_STREAK_NOT_MET) not in path_codes, '断点处不得做跨版本趋势比较'
    assert _code(RC.FIRST_PERIOD) not in path_codes, '同 strategy_id 有历史，不是首期'
    assert grade.grade == 'L3'
    assert grade.capped is False and grade.cap_reason is None
    assert _ratio_close(own.att.attainment_coverage['S-005'], Decimal('0.928571428571'))

    key_v2 = grading.streak_key('S-005', 'v2')
    assert key_v2 == 'S-005|v2'
    assert own.streaks[key_v2].count == 1, 'promotion_streak 计数在断点处重置'
    assert own.streaks[key_v2].grade == 'L3'
    assert grading.streak_key('S-005', 'v1') not in own.streaks

    # 口径差 5：fixtures 自身的证据分布必须符合 A1 冻结的 manifest.intended_evidence_class。
    raw_ev = evidence.classify(
        fx['cards'],
        tuple(r for r in fx['facts']
              if r.period == EVAL_PERIOD and r.strategy_id != BLOCK_SUBJECT),
        params=EV_PARAMS)
    row = [r for r in raw_ev.rows if (r.strategy_id, r.version_id) == ('S-005', 'v2')][0]
    assert row.evidence_class == 'B', (
        'fixtures/input/design_card.jsonl 的 S-005/v2（COMPLETE + CONCURRENT_CONTROL + DID）'
        '缺 alt_method_note 与 interpretation_limit，实测被判 ' + str(row.evidence_class)
        + '（' + _code(row.evidence_reason) + '），与 manifest.intended_evidence_class 的 B 冲突'
        '（A1 内部自相矛盾，口径差 5）')


# --------------------------------------------------------------------------
# G-09  missing_rule 四分支
# --------------------------------------------------------------------------
def test_g09_missing_rule_four_branches_are_each_other_different(fx):
    '''G-09（M31 1411 行）：ZERO / SKIP / IMPUTE_MEDIAN / BLOCK 四分支各不相同且与规则一致。

    输入构造（A1 golden_map G-09 的 branch_map，四个载体在评价期 2026-Q3 各缺一个事实行，
    probes 用 none:true 逐条钉死「该行不存在」）：
      ZERO           -> S-005/v2  M_CAMPAIGN_COST_MINOR（missing_rule ZERO，target 1995000）
      SKIP           -> S-006/v1  M_CUST_GAIN（missing_rule SKIP，target 100）
      IMPUTE_MEDIAN  -> S-011/v1  M_ROI（missing_rule IMPUTE_MEDIAN，target 0.100000）
      BLOCK          -> S-008/v1  M_COMPLAINT_RATE（missing_rule BLOCK，target 0.002000）
    手算（按 M31「四种分支结果各不相同且与规则一致」逐分支推）：
      ZERO「按 0 计入」：必须存在一条 attainment 行且 attainment = 0/1995000 = 0；
        COST = 0.50*0 + 0.50*a(M_HANDLE_SEC)，a(M_HANDLE_SEC) = 3990/4998
          = 0.798319327731 -> COST = 0.399159663866；六维齐全，
        composite_absolute
          = 0.30*0.834160000000 + 0.21*0.996027482823 + 0.21*0.856960629921
            + 0.14*0.399159663866 + 0.07*1.025000000000 + 0.07*0.850625000000
          = 0.250248000000 + 0.209165771393 + 0.179961732283 + 0.055882352941
            + 0.071750000000 + 0.059543750000
          = 0.826551606617
      SKIP「剔除并重归一」：不得有 M_CUST_GAIN 的 attainment 行；CONTRIB 维度内权重按
        [L954] 重归一：(0.80*a(M_REV_MINOR) + 0.10*a(M_AUM_MINOR)) / (0.80 + 0.10)
        = (0.80*0.727200000000 + 0.10*1.000000000000) / 0.90
        = (0.581760000000 + 0.100000000000) / 0.90 = 0.681760000000 / 0.90
        = 0.757511111111
      IMPUTE_MEDIAN「中位数填补」：必须存在 M_ROI 的 attainment 行。中位数取自同一
        (version_id = v1, period = 2026-Q3) 下 M_ROI 的 10 个非负实际值
        （0.070000 0.076000 0.095000 0.096000 0.100000 0.103000 0.105000 0.115000
         0.124000 0.140000），n = 10 为偶数 -> 取第 5、6 个的均值
        = (0.100000 + 0.103000)/2 = 0.101500000000；
        attainment = 0.101500000000/0.100000 = 1.015000000000；
        EFFIC = 0.30*0.980000000000（M_CONV_RATE 0.196000/0.200000）
                + 0.30*0.858212165534（M_COST_PER_CONV_MINOR 39900/46492）
                + 0.40*1.015000000000
              = 0.294000000000 + 0.257463649660 + 0.406000000000 = 0.957463649660；
        composite_absolute = 0.30*0.816160000000 + 0.21*0.957463649660
                + 0.21*1.297692307692 + 0.14*0.796224218628
                + 0.07*0.770625000000 + 0.07*1.180000000000
              = 0.244848000000 + 0.201067366429 + 0.272515384615 + 0.111471390608
                + 0.053943750000 + 0.082600000000
              = 0.966445891652
      BLOCK「该策略不产出分数」：ScoreFrame 里不得出现 S-008 在 2026-Q3 的行。
      四分支互不相同：ZERO 有行且值为 0、SKIP 无行且维度内重归一、IMPUTE_MEDIAN 有行且值为
        中位数商、BLOCK 整条策略不出分 —— 四种可观测结果两两不同。
    '''
    facts = tuple(r for r in fx['facts'] if r.period == EVAL_PERIOD)
    ev = evidence.classify(fx['cards'], facts, params=EV_PARAMS)
    att = attainment.compute(facts, fx['metric_dict'], params=ATT_PARAMS,
                             anchor_set=fx['anchor'])
    nrm = normalize.compute(att, fx['metric_dict'], fx['anchor'], params=NRM_PARAMS,
                            pools=_pool_map(ev, fx['master']))
    scores = aggregate.compose(att, nrm, fx['weights'], None)

    def one(sid, metric_id, vid='v1'):
        return [r for r in att.rows if (r.strategy_id, r.version_id, r.metric_id)
                == (sid, vid, metric_id)]

    def score_of(sid, vid='v1'):
        return [r for r in scores.rows if (r.strategy_id, r.version_id) == (sid, vid)]

    # 四个分支逐条对拍；不遇错即停，好让一次运行把四条分支的实测值全部报出来。
    problems = []

    def check(label, ok, hand, actual):
        if not ok:
            problems.append('%s: 手算=%s 实测=%s' % (label, hand, actual))

    def show(value):
        return 'None' if value is None else str(value)

    # ---- 分支 1：ZERO -> 按 0 计入，不是当缺格剔除 ----
    zero_rows = one('S-005', 'M_CAMPAIGN_COST_MINOR', 'v2')
    zero_att = zero_rows[0].attainment if zero_rows else None
    check('ZERO 有 attainment 行', len(zero_rows) == 1, '1 行 attainment = 0',
          '%d 行' % len(zero_rows))
    check('ZERO attainment = 0', zero_att == Decimal(0), '0', show(zero_att))
    s005 = score_of('S-005', 'v2')
    cost005 = s005[0].dim_absolute.get('COST') if s005 else None
    comp005 = s005[0].composite_absolute if s005 else None
    check('ZERO 下 S-005/v2 的 COST 维度', cost005 == Decimal('0.399159663866'),
          '0.399159663866', show(cost005))
    check('ZERO 下 S-005/v2 的 composite_absolute',
          comp005 == Decimal('0.826551606617'), '0.826551606617', show(comp005))

    # ---- 分支 2：SKIP -> 剔除并在维度内重归一 ----
    skip_rows = one('S-006', 'M_CUST_GAIN')
    check('SKIP 无 attainment 行', skip_rows == [], '0 行', '%d 行' % len(skip_rows))
    s006 = score_of('S-006')
    contrib006 = s006[0].dim_absolute.get('CONTRIB') if s006 else None
    check('SKIP 下 S-006 的 CONTRIB 维度（0.80/0.90 重归一）',
          contrib006 == Decimal('0.757511111111'), '0.757511111111', show(contrib006))

    # ---- 分支 3：IMPUTE_MEDIAN -> 中位数填补 ----
    imp_rows = one('S-011', 'M_ROI')
    imp_att = imp_rows[0].attainment if imp_rows else None
    check('IMPUTE_MEDIAN 有 attainment 行', len(imp_rows) == 1, '1 行', '%d 行' % len(imp_rows))
    check('IMPUTE_MEDIAN attainment = 0.101500000000/0.100000',
          imp_att == Decimal('1.015000000000'), '1.015000000000', show(imp_att))
    s011 = score_of('S-011')
    effic011 = s011[0].dim_absolute.get('EFFIC') if s011 else None
    comp011 = s011[0].composite_absolute if s011 else None
    check('IMPUTE_MEDIAN 下 S-011 的 EFFIC 维度', effic011 == Decimal('0.957463649660'),
          '0.957463649660', show(effic011))
    check('IMPUTE_MEDIAN 下 S-011 的 composite_absolute',
          comp011 == Decimal('0.966445891652'), '0.966445891652', show(comp011))

    # ---- 分支 4：BLOCK -> 该策略不产出分数 ----
    s008 = score_of(BLOCK_SUBJECT)
    check('BLOCK 下 S-008 不产出分数', s008 == [], '0 行 ScoreRow',
          '%d 行 composite=%s' % (len(s008), show(s008[0].composite_absolute if s008 else None)))

    # ---- 四分支互不相同（M31：four_branches_distinct）----
    observable = {
        'ZERO': (len(zero_rows), show(zero_att)),
        'SKIP': (len(skip_rows), 'dropped+renormalised'),
        'IMPUTE_MEDIAN': (len(imp_rows), show(imp_att)),
        'BLOCK': (len(s008), 'no_score_row'),
    }
    check('four_branches_distinct', len(set(observable.values())) == 4,
          '四种可观测结果两两不同', str(observable))

    assert not problems, 'G-09 四分支对拍失败 ' + str(len(problems)) + ' 条：\n  ' \
        + '\n  '.join(problems)


# --------------------------------------------------------------------------
# G-13  评价设计卡 PARTIAL -> 证据最高只能 C
# --------------------------------------------------------------------------
def test_g13_partial_design_card_caps_evidence_at_c(fx, base):
    '''G-13（M31 1415 行）：设计卡 PARTIAL（缺成功判定）-> 证据最高只能 C。

    输入构造（逐字来自 fixtures/input/design_card.jsonl 的 S-011/v1 行，A1 golden_map
    G-13 的 probe 用 e + nonnull 钉死）：card_status = PARTIAL、control_arrangement = NONE、
    eval_method = OBSERVATIONAL_ONLY、success_criteria = ''（缺成功判定）、
    interpretation_limit 非空。
    手算（evidence 的五步短路，[L977]）：
      ① card_status != MISSING -> 判否；
      ② A 的四要件要求 card_status = COMPLETE，PARTIAL 直接判否（不完备的卡无法核对全部要件）；
      ③ B 要求 card_status = COMPLETE 且 eval_method 属准实验集合，OBSERVATIONAL_ONLY
         不在集合内 -> 判否；
      ④ 仅观测 -> C；card_status = PARTIAL -> reason 取注册码 EVIDENCE_CARD_PARTIAL；
      ⑤ 只有 C 类未写 interpretation_limit 才降 D，本行 limit 非空 -> 保持 C。
      => evidence_class = C（上限），evidence_reason = EVIDENCE_CARD_PARTIAL。
      另：success_criteria = '' 意味着 [L979] 的显著性关键词清单不可能命中（空串项被
      EvidenceParams 拒绝，清单里的任何非空关键词都不是空串的子串），
      即使把 control_arrangement 换成 RANDOMIZED 也拿不到 A —— 这就是「最高只能 C」。
      下游后果：Step 2 证据封顶使 grade 不可能好于 L2；Step 7 的池键证据等级为 C，
      一级库门禁不成立。
    '''
    card = [c for c in fx['cards'] if (c.strategy_id, c.version_id) == ('S-011', 'v1')][0]
    assert card.card_status == 'PARTIAL'
    assert card.control_arrangement == 'NONE'
    assert card.eval_method == 'OBSERVATIONAL_ONLY'
    assert card.success_criteria == ''
    assert card.interpretation_limit is not None and card.interpretation_limit.strip()

    ev = base.evidence('S-011')
    assert ev.evidence_class == 'C'
    assert ev.evidence_class not in ('A', 'B'), 'PARTIAL 卡的证据上限是 C'
    assert _code(ev.evidence_reason) == _code(RC.EVIDENCE_CARD_PARTIAL)
    assert ev.interpretation_limit == card.interpretation_limit

    # 上限 C 的下游后果（Step 2 证据封顶）：grade 不可能好于 L2。
    # M31 G-13 的 expects 只有 evidence_class_max / evidence_reason，不含分池，
    # 故按「一条用例只验一个机制」不断言 Step 7（见口径差 4）。
    grade = base.grade('S-011')
    assert grade.grade in ('L2', 'L3', 'L4', grading.NOT_ASSESSED)
    assert grade.grade != 'L1'


# --------------------------------------------------------------------------
# G-15  豁免无审批留痕 -> 视为未豁免
# --------------------------------------------------------------------------
def test_g15_waiver_without_approval_id_is_invalid_and_still_forces_l4(fx, history):
    '''G-15（M31 1417 行）：waiver_allowed = true 但缺 approval_id -> 未豁免 + WAIVER_INVALID。

    输入构造：
      * 红线定义逐字取自 fixtures/input/redline.jsonl 的 M_COMPLAINT_RATE 行：
        level = HARD、comparator = GT、threshold_value = 0.005000、forced_grade = L4、
        waiver_allowed = true。
      * 实际值逐字取自 fixtures/input/metric_fact.jsonl：
        (S-006, v1, 2026-Q3, M_COMPLAINT_RATE) 的 value = 0.007000。
      * 豁免记录按 R-2 直接构造 WaiverRow：8 张输入表里没有豁免审批留痕的载体
        （A1 golden_map G-15 已登记该缺口，approval_id / 有效期 / 范围只在输出侧
        RedlineEvalRow 上），故用 approval_id = None 表达「waiver_allowed = true 但缺
        approval_id」；有效期取权重版本的生效区间 2026-01-01..2026-12-31（逐字取自
        fixtures/input/weight_version.jsonl），使 as_of = 2026-09-30 落在窗口内 ——
        这样唯一的缺陷就是没有审批留痕，不会与 WAIVER_EXPIRED 混在一起。
    手算：
      越线判定：comparator GT，0.007000 > 0.005000 -> 越线成立。
      豁免判定（[L991]）：waiver_allowed = true 通过；approval_id 为空 -> WAIVER_INVALID，
        视为未豁免 -> hit = true、forced_grade = L4 照常生效、reason_code 取 WAIVER_INVALID
        （被拒的豁免码优先于 T5 行上的签认码，且豁免四元组必须留痕，不得表现为「没有豁免」）。
      Step 4 非补偿：HARD 命中 -> grade = forced_grade = L4，capped = true，
        cap_reason = GR_REDLINE_FORCED。S-006 的 composite_absolute 落在 [0.70, 0.90)
        （基础等级 L3），L4 比 L3 差 -> 封顶成立。
      Step 7：redline_ok 不成立 -> primary_pool_eligible = false，
        reject_reason = REDLINE_HARD_HIT。
      注：S-006 同时是 G-09 SKIP 分支的载体（M_CUST_GAIN 缺格），本条只断言红线与等级，
      不断言其 composite_absolute，以免与 G-09 的缺陷面耦合。
    '''
    rl_row = [r for r in fx['redlines'] if r.metric_id == 'M_COMPLAINT_RATE'][0]
    assert rl_row.level == 'HARD' and rl_row.comparator == 'GT'
    assert rl_row.threshold_value == Decimal('0.005000')
    assert rl_row.waiver_allowed is True and rl_row.forced_grade == 'L4'
    fact = [r for r in fx['facts'] if (r.strategy_id, r.version_id, r.period, r.metric_id)
            == ('S-006', 'v1', EVAL_PERIOD, 'M_COMPLAINT_RATE')][0]
    assert fact.value == Decimal('0.007000') and fact.value > rl_row.threshold_value

    waiver = redline.WaiverRow(metric_id='M_COMPLAINT_RATE', strategy_id='S-006',
                               version_id='v1', approval_id=None,
                               valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31),
                               scope='SYNTH-WAIVER-SCOPE')
    prev, streaks = history
    chain = _run_period(fx, EVAL_PERIOD, prev=prev, streaks=streaks,
                        waivers=(waiver,), exclude=(BLOCK_SUBJECT,), with_pools=False)

    row = chain.redline('S-006', 'M_COMPLAINT_RATE')
    assert row.hit is True, '缺 approval_id -> 视为未豁免，HARD 红线照常强制降级'
    assert _code(row.reason_code) == 'WAIVER_INVALID'
    assert _code(row.reason_code) == _code(RC.WAIVER_INVALID)
    assert row.level == 'HARD' and row.forced_grade == 'L4'
    assert row.waiver_approval_id is None
    # 豁免必须留痕（V-14 禁静默）：被拒的豁免也要把四元组留在行上。
    assert row.waiver_valid_from == date(2026, 1, 1)
    assert row.waiver_valid_to == date(2026, 12, 31)
    assert row.waiver_scope == 'SYNTH-WAIVER-SCOPE'

    grade = chain.grade('S-006')
    assert grade.grade == 'L4'
    assert grade.capped is True
    assert _code(grade.cap_reason) == _code(RC.GR_REDLINE_FORCED)
    assert _code(RC.GR_REDLINE_FORCED) in tuple(_code(c) for c in grade.grade_reason_path)

    # M31 G-15 的 expects 是 forced / grade L4 / WAIVER_INVALID / 视为未豁免，不含分池，
    # 故按「一条用例只验一个机制」不断言 Step 7（见口径差 4）。