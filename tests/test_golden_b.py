'''E3 / tests.test_golden_b -- golden G-05 G-06 G-07 G-10 G-11 G-12 G-14（独立验证 lane）.

守护点（RUN-UNATTENDED-v3.0-PARALLEL.md 第 214 行 E3 行；G-09 G-13 G-15 属 E2，见
  tests/test_golden_a.py，本文件不重复覆盖）：
    G-05 新增极端策略（不入锚定集）重跑 -> 存量策略 norm / composite / grade 完全不变
    G-06 CONTRIB 权重 +20% 扰动 -> flip_rate 计算正确 / 至少一个 NEAR_BOUNDARY 策略翻转为 L3
         / stability_label 正确
    G-07 LOO 单指标过度影响 -> loo_impact 最大者为该指标 + DOMINANT_METRIC 警示
    G-10 未签认指标剔除 + coverage 下降 + METRIC_NOT_SIGNED；维度被清空 -> preflight BLOCK
    G-11 (a) 权重版本过期 (b) MONEY_MINOR 非整数 -> 均 preflight BLOCK，均不产出 score_card
    G-12 同 manifest 连续两次运行 -> reproducibility_hash 精确相等
    G-14 一级库 C 类占比上升 -> MIX_QUALITY_DEGRADED + 池内占比与合并占比分列

R-14 纪律（本文件的立身之本）：
  * 每一条期望值都来自 fixtures/（A1 已冻结）的构造 + 本包独立手算，没有任何一个期望值是从
    dsm/ 实现的输出反填的。手算探针 dsm_stage/E3/probe_sens.py 与 probe_loo.py（不入库）只用
    fixtures 的 target_value / direction / level1_weights / level2_weights，按 digest
    M02 [L443]-[L450]（正向 actual/target、负向 target/actual、clip 到 cap）、
    M03 [L464]-[L466] + [L954]（维度内重归一、composite = Σ W_d · dim_d）、
    M05 [L493]-[L494]（门槛只挂达成率；证据 C 压到 L2、D 转 NOT_ASSESSED）、
    M16 的数值口径（每步除法后 q12 = 1e-12 ROUND_HALF_UP，最后一项取残差使权重和恰为 1）重算，
    **不 import 任何 dsm 业务模块**。
  * 与 A1 golden_map 的 hand 字段逐位交叉核对（两个手算对拍点）：
      对拍点 1（G-06 权重扰动）：hand 写 S-002_base = 1.005000 = 0.30*0.90 + 0.70*1.05、
        S-002_oat20 = 0.996000 = 0.36*0.90 + 0.64*1.05、S-004_base = 0.905000、
        S-004_oat20 = 0.896000；本包独立重算（六维逐维手算后求和）得
        S-002 = 1.005000000000 / 0.996000000000、S-004 = 0.905000000000 / 0.896000000000，
        维度值 CONTRIB 0.900000000000、其余五维 1.050000000000（S-004 为 0.800000000000 /
        0.950000000000），与 hand 的两项简化式逐位一致。
      对拍点 2（G-14 占比）：hand 写 c_share_base 4/12 = 0.333333、c_share_variant
        6/12 = 0.500000；本包按 [L977] 五步短路对当前 fixtures 独立重算得评价期 12 个
        strategy x version 上 C = {S-003, S-006, S-008, S-011} = 4、
        变体 G14（S-005v2 / S-007 的卡改为 NONE + OBSERVATIONAL_ONLY + 已填
        interpretation_limit）后 C = 6 -> q12(4/12) = 0.333333333333、
        q12(6/12) = 0.500000000000，逐位一致。

在飞裁决口径（本包据此写 expects，不按当前实现旧行为）：
  * ORCH-28（docs/adr/RUN-ORCH-28-normalize-pooling-seam.md，SEAM-1 正在实施）：按 M43 [L941]
    归一统计量**优先取自 anchor_set**，故 anchor_set 有效时单例池仍能算出 composite_relative；
    [L943] 的两条边界互相独立 —— sd = 0 -> INACTIVE_METRIC 剔除并预警；池内样本数 <
    min_pool_size -> WARN + SMALL_POOL 标注（不是抛错、不是 null）。pooling 对「已显式标注的
    null」用 reject_reason 承载 + pool_rank = null，**不中断 M29 Step7**，只对「无标注的 null」
    抛错。-> G-05 / G-14 的 expects 按该语义写；当前实现仍按池内统计归一、并对有标注的 null
    一律抛错，故这两条保持 RED（修复归 SEAM-1）。
  * D-A1-02（fixtures 自相矛盾；受控解冻 A1c 已裁但**尚未执行**）：design_card.jsonl 里
    S-004 / S-005v1 / S-005v2 / S-007 四条 DID + CONCURRENT_CONTROL 卡缺 alt_method_note 与
    interpretation_limit，按 [L977] 实测证据分布为 A3 B0 C4 D6（评价期 12 个
    strategy x version 上为 A3 C4 D5），与 manifest 声明的 A3B3C4D2 不符。本包**按 fixtures
    当前实际内容手算**（这四条落 D -> NOT_ASSESSED），不假设 manifest 正确；受影响条目见缺口
    GAP-E3-03 与相关测试 docstring 的「A1c 后需重算（E3b）」标注。

V-9 数值口径：金额 / 计数为 int 精确比较；比率（Decimal）逐位精确相等，另附 1e-12 容差判据。
V-14：Step 7 的异常原文被 chain.pool_error 完整保留并由 expects 显式判 RED（与 E2 同一处置），
  不用 skip / xfail 掩盖，也不写「实现说了算」的期望值。

只读事实来源：docs/digest/M31-tests-golden.md（1405-1416 行）、docs/digest/M37-examples.md
  （E3 / E4 / E5）、docs/digest/M38-k-params.md（K-01~K-20）、docs/digest/M13-sensitivity.md
  （[L746]-[L751] / [L1014]-[L1021]）、docs/digest/M22-preflight.md（C-01~C-10 / [L917]）、
  docs/digest/M24-pooling.md（[L1000]-[L1006]）、docs/digest/M25-audit.md（[L1051]-[L1055] /
  [L1261]-[L1274] / [L1640]）、docs/digest/M43-normalize.md（[L941]-[L945] / [L233]-[L241]）、
  fixtures/manifest.json、fixtures/golden/golden_map.json、fixtures/input/*.jsonl、
  fixtures/variants/*.json、fixtures/negative/G11_money_non_integer.json、
  dsm/models.py（字段名逐字来源，R-2）。

缺口清单（只上报；不改 dsm/**、不改 fixtures/**、不改他人测试；归属请主控裁决）：
  GAP-E3-01 文档码名 vs 注册名：M31 G-11 写 code = STALE，注册名是 WEIGHT_VERSION_STALE；
     M31 G-04 写 GRADE_CAPPED_NO_TARGET / M37 E2 写 PL_L1_GATE_EVIDENCE（E2 已登记同名缺口）；
     而 G-07 DOMINANT_METRIC、G-10 METRIC_NOT_SIGNED、G-14 MIX_QUALITY_DEGRADED 与注册名一致。
     本包一律断言注册名（比对取 .value）。
  GAP-E3-02 M31 G-10「该维度被清空 -> preflight BLOCK」与 M22 C-02「清空维度数 >= 2 -> BLOCK」
     互斥：G10 变体只清空 SUST 一个维度，按 C-02 只有 WEIGHT_REALLOCATED（WARN），按 M31 应
     BLOCK + DIMENSION_EMPTIED。golden 的判据来源是 M31，故本包按 M31 写 expects，保持 RED。
  GAP-E3-03 D-A1-02（A1c 未执行）导致两处需 A1c 后重算：
     (a) G-06「至少一个 NEAR_BOUNDARY 策略翻转为 L3」的载体 S-004 当前落 D -> NOT_ASSESSED，
         不进 sensitivity 的 assessed 集（手算 assessed = 6：S-001 S-002 S-003 S-006 S-009
         S-011），翻转无从发生 -> test_g06_at_least_one_strategy_flips_to_l3 保持 RED；
     (b) G-14 的 C 类占比手算 4/12 -> 6/12 与 A1 hand 逐字相同、本身不依赖这四条卡，但
         pooling.low_evidence_share 的口径是 (C + D) / 已分类：当前 fixtures 下 9/12 -> 9/12
         不变（D 减 C 增相互抵消）-> MIX_QUALITY_DEGRADED 不触发；A1c 后为 6/12 -> 8/12
         （上升）才会触发 -> test_g14 保持 RED，且 **本条 expects 在 A1c 执行后需重新手算**。
  GAP-E3-04 G-07 判据载体：M13 [L748] 的 LOO 输出是「每指标的 LOO 影响力排名」，而
     sensitivity 只对外暴露基于 flip_rate 阈值的 loo_dominant_metrics，没有任何「影响力」量。
     本包用 fixtures 手算的综合分跨度判定 loo_impact 最大者：M_REV_MINOR 的直接权重
     0.30 * 0.80 = 0.240000 为全字典最大，剔除后 S-009 综合分 1.268600000000 ->
     1.148600000000，|Δ| = 0.120000000000，是 14 个签认指标中最大者。实测主导清单按翻转数
     排序，首位是 M_RETENTION_RATE（3/6）-> 该条保持 RED，归因 sensitivity（D2）的 LOO
     影响力度量，以及 fixtures 里 M_REPEAT_USE_COUNT 未签认使 SUST 维度只剩单指标
     （剔除即整维脱落）这一非预期构造。
  GAP-E3-05 preflight 在 A1 冻结件上必然 BLOCK，且与 G-10 / G-11 的判据无关：T7
     weight_version.jsonl 的 provenance = null，而 C-01 [L900] 要求 FROZEN 含 whatif_run_id，
     WEIGHT_MISSING_WHATIF_RUN_ID 又属 RUN_BLOCKING_CODES -> 基线 preflight status = BLOCK。
     test_g10 因此另用 R-2 构造一份带 whatif_run_id 的权重文档来隔离 C-02 机制，并保留对冻结件
     原文的断言；归属请主控裁（fixtures A1 / config 层 P-11 [L1435]）。
  GAP-E3-07 G-05 变体的事实值与 A1 hand 的口径不一致：fixtures/variants/G05_append_extreme.json
     把 15 个指标里的 8 个正向指标写成 1.9 倍目标、6 个负向指标写成等于目标，但**正向的
     M_AUM_MINOR 留成 10000 = 目标值**（达成率 1.0，不是 hand 说的「+1 指标一律 1.900000」）。
     本包按变体实际内容手算：CONTRIB = 0.80*1.9 + 0.10*1.0 + 0.10*1.9 = 1.810000000000、
     综合分 = 0.30*1.81 + 0.21*1.63 + 0.21*1.18 + 0.14*1.0 + 0.07*1.45 + 0.07*1.9
     = 1.507600000000（不是 0.30*1.9 起算的 1.5346）。归因 fixtures（A1 变体构造），
     请主控裁是改变体事实行还是改 golden_map 的 hand。
  GAP-E3-08 Step 3 的行数按**设计卡**出桥（13 行），评价期的**事实行**只有 12 个 pair
     （S-005 在本期只有 v2）：evidence.classify 会为 S-005/v1 也产出一行证据等级。本包
     G-14 的 pair 数按事实行取 12（与 A1 hand 的 4/12、6/12 同口径），并按 pair 过滤 Step 3
     的行；Step 5 之后的 universe 是 11 行（再减 G-09 BLOCK 载体 S-008），因此 pooling 的
     证据结构手算是 A3 B0 C3 D5（11）而不是 4/12。归因 evidence（D2）的出桥口径。
  GAP-E3-06 K-01~K-20 一律 PLACEHOLDER，本包不拟定单值：K-05 attainment_cap 取 [L1742] 建议
     区间上界 2（与 E2 一致，且被断言策略无 capped_flag，结论与取值无关）；K-06 下被断言策略
     的 coverage 手算为 1，六个候选值结论一致；K-10 在 5 组候选值下逐组同结论；K-11 只影响
     stability_label 的分带，本包把标签断言限定在 M13 [L746] 明文默认（0.05 / 0.15，与 K-11
     建议初值一致）并对三个候选组分别披露，核心断言（翻转数、flip_rate = 翻转数 / 参评数、
     逐策略翻转次数）与阈值无关；loo_dominant_flip_rate 与 norm_swap 相关阈值属 digest 未固定
     的必填项 -> 缺配置时断言 MissingConfigError，不猜数。
'''
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

from dsm import (aggregate, attainment, audit, evidence, grading, normalize, pooling, preflight,
                 redline, sensitivity)
from dsm import reason_codes
from dsm.io_loaders import Inputs
from dsm.models import (AnchorSetDoc, DesignCardRow, GradeFrame, GradeLedgerRow, GradeRuleRow,
                        MetricDictRow, MetricFactRow, PoolFrame, PoolKey, PoolStats, RedlineRow,
                        ScoreCardDimCell, ScoreCardMetricCell, ScoreCardRow, StrategyMasterRow,
                        WeightProvenance, WeightVersionDoc)
from dsm.reason_codes import RC

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'fixtures' / 'input'
VARIANTS = ROOT / 'fixtures' / 'variants'
NEGATIVE = ROOT / 'fixtures' / 'negative'

EVAL_PERIOD = '2026-Q3'
HISTORY_PERIODS = ('2025-Q3', '2025-Q4', '2026-Q1', '2026-Q2')
AS_OF = date(2026, 9, 30)                                       # fact data_as_of，逐字取自 fixtures
RUN_AT = datetime(2026, 10, 20, 0, 0, 0)                       # fact snapshot_time，逐字取自 fixtures
WEIGHT_VERSION_ID = 'WV-SYNTH-2026'                             # T7 逐字
OAT20_WEIGHT_VERSION_ID = 'WV-SYNTH-2026-OAT20'                 # 变体 G06 逐字
ANCHOR_SET_ID = 'AS-SYNTH-2026'                                 # T8 逐字
DICT_VERSION = 'MD-SYNTH-2026'                                  # T2 逐字
BLOCK_SUBJECT = 'S-008'                                         # G-09 BLOCK 载体（E2 口径差 3）

ATTAINMENT_CAP = Decimal(2)                                     # K-05，见 GAP-E3-06
ON_ZERO = None
NORM_METHOD = 'min_max'
MIN_POOL_SIZE = 2                                               # [L943] 契约允许的最小非平凡值
SD_DOF = 0
SIGNIFICANCE_KEYWORDS = ('SYNTH_SUCC_CRITERIA',)                # fixtures 字面量，非拟定
TOL = Decimal('1E-12')
MIN_COVERAGE_CANDIDATES = (Decimal('0.50'), Decimal('0.60'), Decimal('0.70'),
                           Decimal('0.80'), Decimal('0.90'), Decimal('1'))
K10_CANDIDATES = ((Decimal('0.05'), Decimal('0.20')), (Decimal('0.10'), Decimal('0.30')),
                  (Decimal('0.20'), Decimal('0.50')), (Decimal('0.25'), Decimal('0.75')),
                  (Decimal('0.95'), Decimal('0.99')))
K11_CANDIDATES = ((Decimal('0.05'), Decimal('0.15')), (Decimal('0.10'), Decimal('0.20')),
                  (Decimal('0.15'), Decimal('0.25')))
# G-14 分母三口径（ORCH-41 第2条 / ERRATUM-11；严禁混用，各自只服务自己的对象）：
# 口径一 evidence 侧「出桥」= 评价期有事实行且过 EVID-1 评价期过滤的 pair 数（13 -> 12，
#   ORCH-37 第9条）-> **只**服务 Step-3 分类断言（C 集合、4/12 -> 6/12、四类闭合）。
EVAL_PAIR_COUNT = 12
# 口径二 pooling 侧 universe = 出桥 12 - 1（M31 [L1411] G-09 BLOCK 载体 S-008 不产出分数）= 11
#   -> 服务 evidence_structure 四类闭合与 (C+D) 披露量。依据 M24 [L1003]「披露各池的证据结构
#   （A/B/C/D 计数）」+ M30 [L1063]⑥「证据结构（A/B/C/D 计数与 NOT_ASSESSED 明细）」并列
#   -> ORCH-37 第6条读法甲：四类全给、NOT_ASSESSED 另附明细。
DEN_POOL = EVAL_PAIR_COUNT - 1                          # = 11
# 口径三 pooling 侧已参评 = 11 - NOT_ASSESSED(2) = 9 -> 服务 c_class_share 与两列 share_*。
#   依据 M24 [L1004]「NOT_ASSESSED 单独计数，不计入分母」+ ORCH-36 第3条「分母必须与两列
#   share_* 同源」。NA = 证据 D 类（M05 [L494] / [L977]① D -> NOT_ASSESSED），A1c（D-A1-02
#   给 S-004/S-005v1/S-005v2/S-007 补 alt_method_note -> 判 B）后 D = {S-010/v1, S-012/v1} = 2。
NOT_ASSESSED_BASE = 2
NOT_ASSESSED_VARIANT = 2
DEN_ASSESSED = DEN_POOL - NOT_ASSESSED_BASE             # = 9
DEN_ASSESSED_VARIANT = DEN_POOL - NOT_ASSESSED_VARIANT  # = 9
# 参评集（等级 != NOT_ASSESSED 且有分数）：A1c 后 6 -> 9。独立探针 dsm_stage/E3b/probe_sens.py
# （只用 fixtures 的 target_value / direction / 两级权重 / grade_rule 门槛 + [L977] 五步判级，
# 不 import 任何 dsm 业务模块，R-14 合规）逐条算出：出桥 12 - D 类 2（S-010 / S-012）
# - G-09 BLOCK 载体 S-008 = 9。
ASSESSED_COUNT = 9
ASSESSED = ('S-001', 'S-002', 'S-003', 'S-004', 'S-005', 'S-006', 'S-007', 'S-009', 'S-011')
SIGNED_METRIC_COUNT = 14               # 15 个指标里 M_REPEAT_USE_COUNT 为 PENDING

ATT_PARAMS = attainment.AttainmentParams(attainment_cap=ATTAINMENT_CAP, on_zero=ON_ZERO,
                                         signed_off_statuses=('SIGNED',))
NRM_PARAMS = normalize.NormalizeParams(method=NORM_METHOD, min_pool_size=MIN_POOL_SIZE,
                                       on_zero=ON_ZERO, sd_dof=SD_DOF)
EV_PARAMS = evidence.EvidenceParams(evidence_mode='GATE_ONLY', cel_enabled=True,
                                    significance_keywords=SIGNIFICANCE_KEYWORDS)
POOL_PARAMS = pooling.PoolingParams(min_pool_size=MIN_POOL_SIZE)
NO_VETO_SENSITIVITY = None


def _code(value):
    '''ReasonCode 载体 -> 逐字码值（CONTEXT-BRIEF 5.1：比对 / 写 CSV 用 .value）。'''
    return getattr(value, 'value', value)


def _jsonl(path):
    text = Path(path).read_text(encoding='utf-8')
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def _rows(raw, model):
    return tuple(model(**item) for item in raw)


def _ratio_eq(actual, expected):
    '''V-9：比率既逐位精确相等，又满足 1e-12 容差；两者都过才算过。'''
    if actual is None or expected is None:
        return actual is expected
    return actual == expected and abs(actual - expected) <= TOL


def _q(value):
    return Decimal(value).quantize(TOL, rounding=ROUND_HALF_UP)


def _diffs(problems):
    '''把一次运行里全部「手算 vs 实测」不一致一次报完（不静默截断，V-14 / R-3）。'''
    assert not problems, ('手算与实测不一致（期望值来自 A1 构造 + 独立手算，R-14 不迁就实现）：'
                          + ' / '.join(problems))


@pytest.fixture(scope='module')
def fx():
    '''A1 冻结的 8 张输入表 -> dsm/models.py 契约行（R-2：字段名逐字抄）。'''
    raw = {name: _jsonl(INPUT / (name + '.jsonl')) for name in
           ('strategy_master', 'metric_dict', 'metric_fact', 'design_card',
            'redline', 'grade_rule', 'anchor_set', 'weight_version')}
    names = ('G05_append_extreme', 'G06_weight_oat20', 'G10_dim_emptied',
             'G11_stale_weight', 'G14_c_share_up')
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
        'variants': {name: json.loads((VARIANTS / (name + '.json')).read_text(encoding='utf-8'))
                     for name in names},
        'negative': json.loads((NEGATIVE / 'G11_money_non_integer.json').read_text(
            encoding='utf-8')),
    }


_TABLE_MODEL = {'strategy_master': StrategyMasterRow, 'metric_dict': MetricDictRow,
                'metric_fact': MetricFactRow, 'design_card': DesignCardRow}
_TABLE_KEY = {'strategy_master': ('strategy_id', 'version_id'),
              'metric_dict': ('metric_id',),
              'metric_fact': ('strategy_id', 'version_id', 'period', 'metric_id'),
              'design_card': ('strategy_id', 'version_id')}


def _variant_table(fx, table, name):
    '''变体的 replace（按业务主键替换）+ append（追加）；只改内存副本（R-1：不动 fixtures）。'''
    base = list(fx['raw'][table])
    spec = fx['variants'][name]
    keys = _TABLE_KEY[table]
    for item in spec.get('replace', {}).get(table, []):
        hit = tuple(item[k] for k in keys)
        for i, row in enumerate(base):
            if tuple(row[k] for k in keys) == hit:
                base[i] = item
                break
    base.extend(spec.get('append', {}).get(table, []))
    return _rows(base, _TABLE_MODEL[table])


def _variant_weights(fx, name, want_id):
    '''权重变体：按 weight_version_id 取文档（G-06 的 OAT20 文档、G-11 的过期文档）。'''
    raw = list(fx['raw']['weight_version'])
    spec = fx['variants'][name]
    for item in spec.get('replace', {}).get('weight_version', []):
        raw = [item if r['weight_version_id'] == item['weight_version_id'] else r for r in raw]
    raw.extend(spec.get('append', {}).get('weight_version', []))
    return WeightVersionDoc(**next(r for r in raw if r['weight_version_id'] == want_id))


def _pool_map(ev_frame, master):
    '''normalize.compute 的必填入参 pools（[L1001]）：biz_domain 取 T1，等级取 Step 3。'''
    domain = {}
    for row in master:
        domain.setdefault(row.strategy_id, row.biz_domain)
    return {r.strategy_id: PoolKey(biz_domain=domain[r.strategy_id],
                                   evidence_class=r.evidence_class)
            for r in ev_frame.rows}


def _live_master(master, facts):
    live = {(r.strategy_id, r.version_id) for r in facts}
    return tuple(r for r in master if (r.strategy_id, r.version_id) in live)


def _rules(fx, min_coverage):
    return grading.GradeRuleSet(rows=tuple(fx['grade_rules']),
                                min_coverage_for_absolute_track=min_coverage)


class Chain:
    '''一期 Step1->Step6（with_pools=True 时再尝试 Step7）的产物集合。'''

    def __init__(self, fx, att, nrm, scores, ev, rl, plan, prev, streaks, pools, stats, err):
        self.fx, self.att, self.nrm, self.scores = fx, att, nrm, scores
        self.ev, self.rl, self.prev = ev, rl, prev
        self.plan, self.grades, self.streaks = plan, plan.frame, plan.streaks
        self.pools, self.stats, self.pool_error = pools, stats, err

    def _pick(self, rows, sid, vid, period):
        return [r for r in rows if (r.strategy_id, r.version_id, r.period) == (sid, vid, period)]

    def one(self, rows, sid, vid, period, what):
        hits = self._pick(rows, sid, vid, period)
        assert len(hits) == 1, '期望唯一 ' + what + ' 行：' + str((sid, vid, period))
        return hits[0]

    def score(self, sid, vid='v1', period=EVAL_PERIOD):
        return self.one(self.scores.rows, sid, vid, period, 'score')

    def grade(self, sid, vid='v1', period=EVAL_PERIOD):
        return self.one(self.grades.rows, sid, vid, period, 'grade')

    def evidence(self, sid, vid='v1'):
        hits = [r for r in self.ev.rows if (r.strategy_id, r.version_id) == (sid, vid)]
        assert len(hits) == 1, '期望唯一 evidence 行'
        return hits[0]

    def norms(self, sid, vid='v1', period=EVAL_PERIOD):
        return {r.metric_id: r.norm_value for r in self._pick(self.nrm.rows, sid, vid, period)}

    def pool(self, sid, vid='v1', period=EVAL_PERIOD):
        return self.one(self.pools.rows, sid, vid, period, 'pool')

    def grade_fn(self, min_coverage=Decimal('0.60')):
        '''Step 8 的 grade_fn 钩子（[L1016]：只重跑 Step 5-6，Step 1-4 复用）。'''
        def run(score_frame):
            out = grading.assign(score_frame, self.att, self.ev, self.rl, self.prev,
                                 _rules(self.fx, min_coverage))
            frame = getattr(out, 'frame', out)
            return {(r.strategy_id, r.version_id, r.period): r.grade for r in frame.rows}
        return run


def _chain(fx, period, *, cards=None, metric_dict=None, facts=None, weights=None, prev=None,
           streaks=None, exclude=(BLOCK_SUBJECT,), min_coverage=Decimal('0.60'),
           master=None,
           with_pools=False, impute_anchor=True):
    md = fx['metric_dict'] if metric_dict is None else tuple(metric_dict)
    cards = fx['cards'] if cards is None else tuple(cards)
    weights = fx['weights'] if weights is None else weights
    source = fx['facts'] if facts is None else tuple(source_or(fx, facts))
    live = tuple(r for r in source if r.period == period and r.strategy_id not in exclude)
    base_master = fx['master'] if master is None else tuple(master)
    masters = _live_master(base_master, live)
    ev = evidence.classify(cards, live, params=EV_PARAMS)
    # ORCH-40 第9条 / ORCH-37 第8条 / ERRATUM-08：IMPUTE_MEDIAN 的统计量参考集优先取
    # anchor_set（与 M43 [L941]「min_max 的 min/max 与 z_score 的 mean/sd 优先取自 anchor_set」
    # 同口径）。ATT-1（commit dce1ac5）已给 attainment.compute() 加 keyword-only anchor_set=，
    # 并用只读 pytest 插件把冻结 anchor_set.jsonl 注入每个调用点后实跑：g05 由红转绿
    # （7 failed -> 6 failed，g05 出列），其余 6 条注入前后完全相同 -> 接线是唯一治法。
    # 不接线 => anchor_set=None => 参考集退回当期池 => 追加 S-901 会撑动 S-011/v1 的 M_ROI
    # 填补值 => M31 [L1407]（G-05）的不变性在结构上不可能满足。
    # 注意：anchor_set 是 compute() 的入参，**不得**塞进 AttainmentParams（A1DPREP 实测反例：
    # ValidationError @168）。impute_anchor=False 只用于复现旧的当期池回退分支做对照。
    att = attainment.compute(live, md, params=ATT_PARAMS,
                             anchor_set=(fx['anchor'] if impute_anchor else None))
    nrm = normalize.compute(att, md, fx['anchor'], params=NRM_PARAMS,
                            pools=_pool_map(ev, base_master))
    scores = aggregate.compose(att, nrm, weights, None)
    rl = redline.evaluate(live, redline.RedlineSet(rows=fx['redlines']),
                          redline.WaiverSet(rows=()), as_of=AS_OF, soft_deductions={},
                          metric_dict=md)
    plan = grading.plan(scores, att, ev, rl, prev, _rules(fx, min_coverage), streaks=streaks)
    pools = stats = err = None
    if with_pools:
        try:
            pools, stats = pooling.build(scores, plan.frame, ev, masters, None,
                                         sensitivity=NO_VETO_SENSITIVITY, normalized=nrm, params=POOL_PARAMS)
        except Exception as exc:  # noqa: BLE001  原文保留，由 expects 显式判 RED
            err = type(exc).__name__ + ': ' + str(exc)
    return Chain(fx, att, nrm, scores, ev, rl, plan, prev, streaks, pools, stats, err)


def source_or(fx, facts):
    return fx['facts'] if facts is None else facts


@pytest.fixture(scope='module')
def history(fx):
    '''A1 的 4 期历史串出上期台账与滞回状态（M29 按期串起来，同 E2 的用法）。'''
    prev, streaks = None, None
    for period in HISTORY_PERIODS:
        chain = _chain(fx, period, prev=prev, streaks=streaks)
        prev = GradeFrame(rows=tuple((prev.rows if prev else ()) + chain.grades.rows))
        streaks = chain.streaks
    return prev, streaks


@pytest.fixture(scope='module')
def base(fx, history):
    '''评价期基准运行（剔除 G-09 BLOCK 载体 S-008，见 E2 口径差 3）。'''
    prev, streaks = history
    return _chain(fx, EVAL_PERIOD, prev=prev, streaks=streaks)
from dsm.models import ScoringContext                       # Step 8 的 base 入参（[L1014]）

# --------------------------------------------------------------------------
# G-05  新增极端策略（不入锚定集）重跑 -> 存量策略 norm / composite / grade 完全不变
# --------------------------------------------------------------------------
def test_g05_appended_extreme_strategy_leaves_existing_norm_composite_grade_unchanged(
        fx, base, history):
    '''G-05（M31 1407 行 / M43 [L235]-[L239]、[L941]）：追加极端策略后存量结果完全不变。

    输入构造（全部取自 A1 变体 fixtures/variants/G05_append_extreme.json，本包不新造数据）：
      * append 一条 strategy_master（S-901 / v1，biz_domain = PAY，ACTIVE，online 2026-07-01）、
        一条 design_card（S-901 / v1，DID + CONCURRENT_CONTROL）、15 条评价期 2026-Q3 事实行。
      * 锚定集逐字不变（fixtures/input/anchor_set.jsonl：AS-SYNTH-2026 = S-001 S-002 S-003
        S-004 S-005 S-007 S-008 S-011），**S-901 不是成员**，这正是 M31 G-05 的构造要点。
    手算（判据是「不变量」而非绝对值，因此不需要任何治理签认值）：
      * 绝对轨：attainment 与 composite_absolute 都是逐策略量（M02 [L443]-[L450]、
        M03 [L464]-[L466]），新策略的加入不进入他人的算式 -> 存量 11 条（评价期 12 个
        strategy x version 减去 G-09 BLOCK 载体 S-008，见 E2 口径差 3）的
        composite_absolute 与 grade 必须逐位不变。
      * 相对轨：M43 [L941] 明文「min_max 的 min/max 优先取自 anchor_set」，而锚定集成员与
        其事实值逐字未变（S-901 不在集合内）-> 参照尺不变 -> 存量的每一个 norm_value、
        进而每一个 composite_relative 必须逐位不变（这正是 F5 秩反转的治理手段，
        M43 [L235]「标准化时以锚定集为参考尺」）。
      * 分池：M43 [L942] + M24 [L1001] 禁止跨池归一/混排；S-901 的池是 (PAY, D)（其卡
        alt_method_note 为空 -> 按 [L977] 落 D，GAP-E3-03），与存量 PAY 域池 (PAY, C) 的
        S-011 不同池，也不得与 (CARD, A) 等任何池合并排名 -> 存量池内名次不受影响。
      * 锚定集有效 -> 不得回退当期统计，故存量行不得出现 RANK_REVERSAL_RISK 标注，
        anchor_used 必须为 true（[L941] 「优先取自 anchor_set」）。
    实测与手算不符（当前 normalize 把 min/max 取在**当期池内**，S-901 进 (PAY, D) 后
      该池参照尺被撑开，存量 PAY 域策略的相对轨被拖动）= ORCH-28 裁决的 D3 缺陷本体，
      修复归 SEAM-1，本条保持 RED，期望值不迁就实现。
    '''
    prev, streaks = history
    cards = _variant_table(fx, 'design_card', 'G05_append_extreme')
    facts = _variant_table(fx, 'metric_fact', 'G05_append_extreme')
    masters = _variant_table(fx, 'strategy_master', 'G05_append_extreme')
    appended = _chain(fx, EVAL_PERIOD, cards=cards, facts=facts, master=masters, prev=prev, streaks=streaks)

    assert 'S-901' not in fx['anchor'].strategy_ids, '极端策略必须不入锚定集（构造要点）'
    existing = {(r.strategy_id, r.version_id) for r in base.scores.rows}
    assert len(existing) == EVAL_PAIR_COUNT - 1, '基准运行应含 12 - 1（S-008）条评分行'
    assert existing < {(r.strategy_id, r.version_id) for r in appended.scores.rows}, \
        '变体运行必须覆盖基准的全部存量策略'

    problems = []
    for sid, vid in sorted(existing):
        before, after = base.score(sid, vid), appended.score(sid, vid)
        if not _ratio_eq(after.composite_absolute, before.composite_absolute):
            problems.append('%s/%s composite_absolute: 手算=不变(%s) 实测=%s'
                            % (sid, vid, before.composite_absolute, after.composite_absolute))
        if not _ratio_eq(after.composite_relative, before.composite_relative):
            problems.append('%s/%s composite_relative: 手算=不变(%s) 实测=%s'
                            % (sid, vid, before.composite_relative, after.composite_relative))
        old_grade, new_grade = base.grade(sid, vid).grade, appended.grade(sid, vid).grade
        if _code(new_grade) != _code(old_grade):
            problems.append('%s/%s grade: 手算=不变(%s) 实测=%s'
                            % (sid, vid, old_grade, new_grade))
        norm_before, norm_after = base.norms(sid, vid), appended.norms(sid, vid)
        for metric in sorted(set(norm_before) | set(norm_after)):
            if not _ratio_eq(norm_after.get(metric), norm_before.get(metric)):
                problems.append('%s/%s norm %s: 手算=不变(%s) 实测=%s'
                                % (sid, vid, metric, norm_before.get(metric),
                                   norm_after.get(metric)))
    rows = [r for r in appended.nrm.rows if (r.strategy_id, r.version_id) in existing]
    if any(not r.anchor_used for r in rows):
        problems.append('anchor_used: 手算=true（[L941] 锚定集优先）实测=false 行数='
                        + str(sum(1 for r in rows if not r.anchor_used)))
    if any(_code(r.reason_code) == _code(RC.RANK_REVERSAL_RISK) for r in rows):
        problems.append('RANK_REVERSAL_RISK: 手算=不标注（锚定集有效）实测=已标注')
    _diffs(problems)

IMPUTE_METRIC = 'M_ROI'                 # fixtures/input/metric_dict.jsonl -> missing_rule = IMPUTE_MEDIAN
IMPUTE_CARRIER = ('S-011', 'v1')        # 评价期缺该指标事实行的载体（G-09 四分支之一）


def _att_of(chain, sid, vid, metric_id):
    '''从 AttainmentResult 里取单个 (sid, vid, period, metric_id) 的达成率（只读取值，不判期望）。'''
    for r in chain.att.rows:
        if (r.strategy_id, r.version_id, r.period, r.metric_id) == (sid, vid, EVAL_PERIOD, metric_id):
            return r.attainment
    return None


def test_g05_impute_median_reference_set_is_anchor_set_so_append_cannot_move_it(fx, history):
    '''G-05 x ORCH-40 第9条（ERRATUM-08）：IMPUTE_MEDIAN 的参考集 = anchor_set，故追加不改填补值。

    原文依据（逐字）：
      * M18 [L1134]「| missing_rule | 缺数据处置：ZERO / SKIP / IMPUTE_MEDIAN / BLOCK |」
        —— 只枚举四个规则名，**对中位数取自哪个集合零字规定** = 原文缺口，故本条依据等级为
        derived:（ERRATUM-08），不得当作 SDD 的明文要求引用。
      * M43 [L941]「min_max 的 min/max 与 z_score 的 mean/sd **优先取自 anchor_set**；锚定集失效
        → 回退当期池内统计 + 标注 RANK_REVERSAL_RISK」—— 同口径的原文锚点。
      * M31 [L1407]（G-05）「存量全部策略的 norm、composite、grade **完全不变**」。
    手算（符号化，不取任何实现输出）：
      SAMPLE(M_ROI, v1) = { actual_value | metric_id = M_ROI ∧ period = 2026-Q3 ∧ version_id = v1
                            ∧ strategy_id ∈ anchor_set.strategy_ids ∧ actual_value >= 0 ∧ 非 SUSPECT }
      anchor_set.strategy_ids = {S-001,S-002,S-003,S-004,S-005,S-007,S-008,S-011}（**S-901 ∉ 集合**）
      => S-901 的任何事实行都不进 SAMPLE => MED 不变 => ATT 不变 => norm/composite/grade 不变。
      样本成员手算 = {S-001,S-002,S-003,S-004,S-007,S-008} = 6（S-005/v1 RETIRED 且
      offline_date=2026-06-30、本期无事实行 -> 被 EVID-1 的 evaluation_scope() 排除；
      S-011 自身缺该行）=> 偶数个 => 中位数 = 升序第 3、第 4 项之和 / 2（Decimal 端到端，V-9）。
      填补后的 attainment / composite **绝对值** = PLACEHOLDER（GAPS P-02）：[L1134] 对参考集零字
      规定，参考集本身是 derived: 裁决，且 6 个样本 actual_value 属 A1c 刚重生成的数据 ->
      按 R-12/R-14 不硬编；本条用「追加前后逐位相同」的不变量替代，故不需要该绝对值。
    '''
    prev, streaks = history
    cards = _variant_table(fx, 'design_card', 'G05_append_extreme')
    facts = _variant_table(fx, 'metric_fact', 'G05_append_extreme')
    masters = _variant_table(fx, 'strategy_master', 'G05_append_extreme')
    sid, vid = IMPUTE_CARRIER

    assert 'S-901' not in fx['anchor'].strategy_ids, 'S-901 必须不入锚定集（M31 [L1407] 构造要点）'
    assert any(r.metric_id == IMPUTE_METRIC and r.missing_rule == 'IMPUTE_MEDIAN'
               for r in fx['metric_dict']), '载体指标的 missing_rule 必须是 IMPUTE_MEDIAN（[L1134]）'
    assert not [r for r in fx['facts']
                if (r.strategy_id, r.version_id, r.metric_id, r.period)
                == (sid, vid, IMPUTE_METRIC, EVAL_PERIOD)], '载体必须真的缺该事实行'

    base_anchored = _chain(fx, EVAL_PERIOD, prev=prev, streaks=streaks, impute_anchor=True)
    appended = _chain(fx, EVAL_PERIOD, cards=cards, facts=facts, master=masters,
                      prev=prev, streaks=streaks, impute_anchor=True)
    pooled = _chain(fx, EVAL_PERIOD, cards=cards, facts=facts, master=masters,
                    prev=prev, streaks=streaks, impute_anchor=False)
    problems = []
    # (1) 核心不变量：接锚定集后，追加 S-901 不得改动 S-011/v1 的填补达成率。
    before = _att_of(base_anchored, sid, vid, IMPUTE_METRIC)
    after = _att_of(appended, sid, vid, IMPUTE_METRIC)
    if before is None or after is None:
        problems.append('填补未产出（V-14：不得静默降级为 None）：追加前=%s 追加后=%s'
                        % (before, after))
    elif not _ratio_eq(after, before):
        problems.append('S-011/v1 M_ROI 填补达成率：手算=不变（参考集 anchor_set 不含 S-901，'
                        'ORCH-40 第9条 / M31 [L1407]）实测 追加前=%s 追加后=%s' % (before, after))
    # (2) 对照：不接锚定集（当期池回退）时该不变量在结构上无法保证 -> 只要求两者都被显式观测，
    #     不静默。真正的判据是 (1)。V-14：不用 skip/xfail 掩盖。
    if _att_of(pooled, sid, vid, IMPUTE_METRIC) is None:
        problems.append('当期池回退分支也没有产出填补值（V-14）')
    # (3) 关系式断言：任何填补/回退留痕都必须是**已注册码**（H-7），不硬编码名——
    #     ANCHOR_SET_STALE 的适用条件与 EVID-1 的 ScopeExclusion.reason_code 都可能变，
    #     用 is_registered(...) 才不会与主控注册结果冲突。
    for chain in (base_anchored, appended, pooled):
        for row in chain.att.rows:
            code = _code(getattr(row, 'reason_code', None))
            if code is not None and not reason_codes.is_registered(code):
                problems.append('attainment 产出了未注册码（H-7 / V-14）：' + str(code))
    _diffs(problems)


S901_HAND_19 = ('M_REV_MINOR', 'M_CUST_GAIN', 'M_ROI', 'M_CONV_RATE', 'M_SATISFY_SCORE',
                'M_RETENTION_RATE', 'M_REPEAT_USE_COUNT', 'M_REACH_RATE')
S901_HAND_10 = ('M_AUM_MINOR', 'M_COST_PER_CONV_MINOR', 'M_COMPLAINT_RATE',
                'M_CONTACT_FREQ_PER_30D', 'M_CAMPAIGN_COST_MINOR', 'M_HANDLE_SEC', 'M_OPTOUT_RATE')

def test_g05_appended_extreme_strategy_is_built_at_attainment_1_9_outside_anchor(fx, history):
    '''G-05 的输入侧手算：S-901 的达成率、六维值与综合分（全部按变体实际内容重算）。

    输入构造（逐字取自 A1 变体 fixtures/variants/G05_append_extreme.json 的 15 条
      metric_fact append 与 T2 的 target_value / direction；T7 的一二级权重；本包不新造数据）：
      * 正向（M02 [L444] actual/target）= 1.900000000000 的 8 个指标：
          M_REV_MINOR 19000/10000、M_CUST_GAIN 190/100、M_ROI 0.190000/0.100000、
          M_CONV_RATE 0.380000/0.200000、M_SATISFY_SCORE 0.190000/0.100000、
          M_RETENTION_RATE 1.140000/0.600000、M_REPEAT_USE_COUNT 190/100、
          M_REACH_RATE 1.520000/0.800000。
      * 负向（M02 [L446] target/actual）= 1.000000000000 的 6 个指标（值 = 目标值）：
          M_COST_PER_CONV_MINOR 39900、M_COMPLAINT_RATE 0.002000、
          M_CONTACT_FREQ_PER_30D 2、M_CAMPAIGN_COST_MINOR 1995000、M_HANDLE_SEC 3990、
          M_OPTOUT_RATE 0.039900。
      * **第 7 个 1.000000000000 = M_AUM_MINOR（direction = +1、值 10000 / 目标 10000）**：
          A1 golden_map G-05 的 hand 写「extreme_attainment = 1.900000（+1 指标）/
          1.000000（-1 指标）」，而变体事实行把正向的 M_AUM_MINOR 留成了 1.0 ->
          本包按**变体实际内容**手算（GAP-E3-07：该条与 hand 的口径不一致，归因 fixtures）。
      * 维度值（M03 [L464] Σ w_j · x_j，二级权重逐字取自 T7；SUST 因 M_REPEAT_USE_COUNT
        未签认 -> 维度内重归一 [L954]，只剩 M_RETENTION_RATE）：
          CONTRIB = 0.80*1.9 + 0.10*1.0 + 0.10*1.9
                  = 1.520000000000 + 0.100000000000 + 0.190000000000 = 1.810000000000
          EFFIC   = 0.40*1.9 + 0.30*1.0 + 0.30*1.9
                  = 0.760000000000 + 0.300000000000 + 0.570000000000 = 1.630000000000
          EXPER   = 0.40*1.0 + 0.40*1.0 + 0.20*1.9
                  = 0.400000000000 + 0.400000000000 + 0.380000000000 = 1.180000000000
          COST    = 0.50*1.0 + 0.50*1.0 = 1.000000000000
          PROC    = 0.50*1.9 + 0.50*1.0 = 0.950000000000 + 0.500000000000 = 1.450000000000
          SUST    = 1.900000000000（重归一后单指标）
      * 综合分（M03 [L465] Σ W_d · dim_d，一级权重 T7 逐字）：
          0.30*1.810000000000 + 0.21*1.630000000000 + 0.21*1.180000000000
          + 0.14*1.000000000000 + 0.07*1.450000000000 + 0.07*1.900000000000
          = 0.543000000000 + 0.342300000000 + 0.247800000000 + 0.140000000000
            + 0.101500000000 + 0.133000000000 = 1.507600000000
      * K-05（attainment_cap，PLACEHOLDER）隔离：最大达成率 1.9 < 建议区间上界 2，
        全部行 capped_flag = false -> 本条结论对 K-05 在 [1.9, 2] 内任意取值都成立。
      * Step 1 的行数 = 字典全量 15：未签认指标（M_REPEAT_USE_COUNT）的剔除是
        preflight C-02 [L901] 的门禁动作（见 test_g10_pending_metric_*），不是 Step 1 的行为。
    '''
    prev, streaks = history
    cards = _variant_table(fx, 'design_card', 'G05_append_extreme')
    facts = _variant_table(fx, 'metric_fact', 'G05_append_extreme')
    masters = _variant_table(fx, 'strategy_master', 'G05_append_extreme')
    run = _chain(fx, EVAL_PERIOD, cards=cards, facts=facts, master=masters, prev=prev,
                 streaks=streaks)
    index = {r.metric_id: r for r in fx['metric_dict']}

    rows = [r for r in run.att.rows if r.strategy_id == 'S-901']
    assert len(rows) == len(fx['metric_dict']), 'Step 1 的行数 = 字典全量 15，实测 ' \
        + str(len(rows))
    for row in rows:
        want = _q(Decimal('1.9')) if row.metric_id in S901_HAND_19 else _q(Decimal('1'))
        assert _ratio_eq(row.attainment, want), (
            '手算 attainment=%s 实测=%s（%s, direction=%s；1.9 组见本条 docstring 的'
            '逐项算式）' % (want, row.attainment, row.metric_id,
                          index[row.metric_id].direction))
        assert row.capped_flag is False
    assert sorted(m for m in S901_HAND_10 if index[m].direction > 0) == ['M_AUM_MINOR'], 'GAP-E3-07：1.0 组里唯一的正向指标必须是 M_AUM_MINOR（变体事实值 = 目标值 10000，而 A1 hand 写「+1 指标一律 1.9」）'
    assert (set(S901_HAND_19) | set(S901_HAND_10)) == set(index), '两组必须闭合覆盖字典'

    score = run.score('S-901')
    hand_dims = {'CONTRIB': '1.810000000000', 'EFFIC': '1.630000000000',
                 'EXPER': '1.180000000000', 'COST': '1.000000000000',
                 'PROC': '1.450000000000', 'SUST': '1.900000000000'}
    problems = []
    for dim, want in sorted(hand_dims.items()):
        if not _ratio_eq(score.dim_absolute[dim], _q(Decimal(want))):
            problems.append('S-901 ' + dim + '：手算=' + want + ' 实测='
                            + str(score.dim_absolute[dim]))
    if not _ratio_eq(score.composite_absolute, _q(Decimal('1.507600000000'))):
        problems.append('S-901 综合分：手算 0.30*1.81 + 0.21*1.63 + 0.21*1.18'
                        ' + 0.14*1.0 + 0.07*1.45 + 0.07*1.9 = 1.507600000000，实测='
                        + str(score.composite_absolute))
    _diffs(problems)


# --------------------------------------------------------------------------
# G-06  CONTRIB 权重 +20% 扰动 -> flip_rate / 翻转为 L3 / stability_label
# --------------------------------------------------------------------------
def test_g06_oat20_weight_document_and_s002_l1_to_l2_arithmetic(fx, history):
    '''G-06（M31 1408 行 / M37 E5）：CONTRIB W_d x1.2、其余重归一后的综合分与等级翻转。

    输入构造：变体 fixtures/variants/G06_weight_oat20.json 追加的第二份权重文档
      WV-SYNTH-2026-OAT20（status FROZEN，effective 区间与基线一致）：
      level1 = CONTRIB 0.36、COST 0.128、EFFIC 0.192、EXPER 0.192、PROC 0.064、SUST 0.064。
    手算（与 A1 golden_map G-06 的 hand 逐位对拍）：
      * 权重闭合：0.36 + 0.128 + 0.192 + 0.192 + 0.064 + 0.064 = 1.000000000000，
        其余五维合计 0.128+0.192+0.192+0.064+0.064 = 0.640000000000 = 1 - 0.36，
        即 hand 的「0.36 x … + 0.64 x …」形式；CONTRIB 0.30 x 1.2 = 0.36 与 hand 一致。
      * S-002 的维度值（M02 [L444] 正向 actual/target、[L446] 负向 target/actual；
        M03 [L464] 维度内二级权重 REV .80 / AUM .10 / CUST .10，逐字取自 T7）：
        CONTRIB = 0.8*0.900000000000（M_REV_MINOR 9000/10000）
                + 0.1*1.000000000000（M_AUM_MINOR 10000/10000）
                + 0.1*0.800000000000（M_CUST_GAIN 80/100）
                = 0.720000000000 + 0.100000000000 + 0.080000000000
                = 0.900000000000；
        其余五维各为 1.050000000000：正向 1.05 = actual/target（M_ROI、M_CONV_RATE、
        M_SATISFY_SCORE、M_RETENTION_RATE、M_REPEAT_USE_COUNT、M_REACH_RATE 的 T3 值与
        T2 target_value 之比都是 1.05）、负向 1.05 = target/actual（M_COST_PER_CONV_MINOR
        39900/38000、M_CAMPAIGN_COST_MINOR 1995000/1900000、M_HANDLE_SEC 3990/3800、
        M_OPTOUT_RATE 同理）；M_COMPLAINT_RATE 与 M_CONTACT_FREQ_PER_30D 都是
        1.000000000000，与同维其余指标按维度内权重合成后该维仍为 1.050000000000；
        逐指标达成率的中间量见探针 dsm_stage/E3/probe_sens.py 的 base comp 行。
      * 综合分：基线 0.30*0.900000000000 + 0.70*1.050000000000
          = 0.270000000000 + 0.735000000000 = 1.005000000000 -> 按 T5 门槛
          L1 attainment_floor = 1.00（逐字）>= 门槛 -> 基础等级 L1（证据 A，不封顶）。
          OAT20 0.36*0.900000000000 + 0.64*1.050000000000
          = 0.324000000000 + 0.672000000000 = 0.996000000000 < 1.000000000000
          且 >= L2 floor 0.90 -> L2。跨过的是 **L1 门槛**，不是 L2 门槛。
      * coverage 手算 = 1（S-002 的 14 个签认指标全部有 target_value 且有事实行），
        故 K-06 的六个候选值都不会触发 [L495] 的目标缺失封顶，等级结论与 K-06 无关。
    '''
    weights20 = _variant_weights(fx, 'G06_weight_oat20', OAT20_WEIGHT_VERSION_ID)
    total = sum((Decimal(str(v)) for v in weights20.level1_weights.values()), Decimal(0))
    assert total == Decimal('1.000000000000'), '一级权重必须精确闭合到 1，实测 ' + str(total)
    assert _ratio_eq(_q(Decimal(weights20.level1_weights['CONTRIB'])), _q(Decimal('0.36')))
    assert weights20.status == 'FROZEN'

    prev, streaks = history
    oat = _chain(fx, EVAL_PERIOD, weights=weights20, prev=prev, streaks=streaks)
    base, cand = fx['weights'], MIN_COVERAGE_CANDIDATES

    assert _ratio_eq(oat.score('S-002').composite_absolute, _q(Decimal('0.996000000000'))), \
        '手算 0.36*0.900000000000 + 0.64*1.050000000000 = 0.996000000000，实测=' \
        + str(oat.score('S-002').composite_absolute)
    assert _ratio_eq(oat.score('S-002').dim_absolute['CONTRIB'], _q(Decimal('0.900000000000')))
    for dim in ('COST', 'EFFIC', 'EXPER', 'PROC', 'SUST'):
        assert _ratio_eq(oat.score('S-002').dim_absolute[dim], _q(Decimal('1.050000000000')))

    for mc in cand:
        control = _chain(fx, EVAL_PERIOD, prev=prev, streaks=streaks, min_coverage=mc)
        perturbed = _chain(fx, EVAL_PERIOD, weights=weights20, prev=prev, streaks=streaks,
                           min_coverage=mc)
        assert _ratio_eq(control.score('S-002').composite_absolute,
                         _q(Decimal('1.005000000000'))), \
            '与 A1 hand 1.005000 = 0.30*0.90 + 0.70*1.05 逐位对拍失败，实测=' \
            + str(control.score('S-002').composite_absolute)
        assert control.grade('S-002').grade == 'L1', 'K-06=' + str(mc) + ' 时基线等级应为 L1'
        assert perturbed.grade('S-002').grade == 'L2', 'K-06=' + str(mc) + ' 时扰动等级应为 L2'
        assert perturbed.grade('S-002').capped is False
        assert perturbed.score('S-002').weight_version_id == OAT20_WEIGHT_VERSION_ID


def _sensitivity_ctx(chain, seed=None):
    '''Step 8 的 ScoringContext（R-2：字段名逐字抄 models.py，Step 1-4 复用 [L1016]）。'''
    return ScoringContext(
        period=EVAL_PERIOD, run_at=RUN_AT, run_id='SYNTH-RUN-E3-G06', seed=seed,
        weight_version_id=chain.scores.rows[0].weight_version_id, evidence_mode='GATE_ONLY',
        cel_enabled=True, input_fingerprints={}, attainment=chain.att,
        normalized=chain.nrm, evidence=chain.ev, redline=chain.rl, score=chain.scores,
        grade=chain.grades, pool=PoolFrame(rows=()),
        pool_stats=PoolStats(rows=(), evidence_structure={}, not_assessed_count=0,
                             not_assessed_reasons={}))


def test_g06_flip_rate_is_flipped_over_assessed_and_labels_are_correct(fx, base):
    '''G-06 的 flip_rate 手算（M13 [L746] OAT_20 / [L1018] 输出、[L1016] 只重跑 Step 5-6）。

    手算（OAT_20 = 6 个维度 x ±20% = 12 次扰动；每次扰动后按 [L954] 重归一（除法 q12、
      末位取残差使和恰为 1），再按 M05 Step 1 门槛（[L493]）+ Step 2 证据封顶（[L494]）重新定级）：
      * 参评集（assessed，等级非 NOT_ASSESSED 且有分数）手算 = **9**（A1c D-A1-02 给
        S-004 / S-005v1 / S-005v2 / S-007 四张 DID 卡补 [L1171] alt_method_note -> [L977]③ 判 B，
        这四条由 D（NOT_ASSESSED）回到参评域，A1CPREP §9.1 耦合点 3 已预声明）：
          S-001（A，1.021580000000 -> L1）、S-002（A，1.005000000000 -> L1）、
          S-003（C，1.084600000000 -> 证据封顶 L2）、S-004（B，0.905000000000 -> L2）、
          S-005/v2（B，0.843701606617 -> L3）、S-006（C，0.793501146975 -> L3，
          另越 M_COMPLAINT_RATE HARD 线 -> forced L4，见 E2 G-15）、
          S-007（B，1.011310171243 -> L1）、S-009（A，1.268600000000 -> L1）、
          S-011（C，0.960845891652 -> L2）。
        其余 3 条不进分母：2 条证据 D（S-010/v1 卡缺失、S-012/v1 C 未写 interpretation_limit）
        + S-008（G-09 BLOCK 载体，[L1411]，本期无分数）。
        取值途径 = 独立探针 dsm_stage/E3b/probe_sens.py（只用 fixtures 的 target_value /
        direction / 两级权重 / grade_rule 门槛 + [L977] 五步判级，**不 import 任何 dsm 业务
        模块**，R-14 合规；实测值 3 只作归因交叉核对，不作期望来源）。
      * 逐策略翻转次数（12 次扰动里等级发生变化的次数）手算：
          S-002 = 1（仅 CONTRIB +20%：CONTRIB 权重 0.30*1.2 后按 [L954] 重归一，
            综合分 1.005000000000 -> 0.999056603773 跌破 [L493] 的 L1 门槛 1.00 -> L2）
          S-004 = 1（仅 CONTRIB +20%：0.905000000000 -> 0.899056603775 跌破 L2 门槛 0.90 -> L3；
            这正是 #11 test_g06_at_least_one_near_boundary_strategy_flips_to_l3 的同一载体，
            A1c 已把该条修绿，本条不得破坏它）
          S-007 = 1（仅 EXPER -20%：1.011310171243 -> 0.994800831821 跌破 L1 门槛 1.00 -> L2）
          S-001 = 0（基线 1.021580000000 距 L1 门槛 1.00 有 0.021580 余量，12 次扰动始终 >= 1.00）
          S-003 / S-011 = 0（证据 C 封顶 L2，扰动不改等级）、S-006 = 0（HARD 强制 L4，
            扰动不改等级）、S-009 = 0（1.268600000000 距门槛最远）、S-005/v2 = 0（0.843701606617
            距 L3 门槛 0.70 有余量，且 +20% 方向只上不下）
      * flipped_count = #{翻转次数 > 0 的参评策略} = 3（S-002 / S-004 / S-007）
      * overall_flip_rate = 翻转策略数 / 参评数 = 3 / 9 -> q12 = 0.333333333333
        （改前的 1/6 = 0.166666666667 是 A1c 之前 6 条参评集的陈旧手算值）
      * OAT_10（±10%，12 次）手算：0 次翻转 -> overall_flip_rate = 0.000000000000
      * 逐策略 flip 比例（该策略翻转次数 / 扰动次数 12）：S-002 = S-004 = S-007 =
        1/12 = 0.083333333333，其余 6 条 = 0。
    K-11（stable_max / review_max，治理参数、PLACEHOLDER）的处置：本包不断言由阈值决定的
      档位标签为唯一结论，只对 **M13 [L746] 明文默认 0.05 / 0.15**（与 K-11 [L1748] 建议初值
      一致）断言 overall 与逐策略标签，并在三组候选值下把差异如实披露：
        overall 0.333333333333：候选组 (0.05,0.15) -> 超 review_max（FLIP_RATE_UNUSABLE）、
          (0.10,0.20) 与 (0.15,0.25) -> 同样超 review_max（0.333333333333 > 0.20 / 0.25）；
        S-002 / S-004 / S-007 逐策略 0.083333333333：(0.05,0.15) -> NEAR_BOUNDARY，
          (0.10,0.20) / (0.15,0.25) -> STABLE。
      阈值与档位的对应关系属 [L746] 明文，不是本包拟定。
    '''
    report10 = sensitivity.run(_sensitivity_ctx(base), ('OAT_10',), None,
                               weights=base.fx['weights'], grade_fn=base.grade_fn())
    report20 = sensitivity.run(_sensitivity_ctx(base), ('OAT_20',), None,
                               weights=base.fx['weights'], grade_fn=base.grade_fn())

    def scheme(report, name):
        hits = [s for s in report.by_scheme if s.scheme == name]
        assert len(hits) == 1, '期望唯一 ' + name + ' 方案结果'
        return hits[0]

    s10, s20 = scheme(report10, 'OAT_10'), scheme(report20, 'OAT_20')
    # 手算的逐策略翻转次数（探针 probe_sens.py 独立算出，见 docstring）：三条各恰 1 次。
    hand_flips = {'S-002': 1, 'S-004': 1, 'S-007': 1}
    hand_flipped = 3
    problems = []
    if s10.assessed_count != ASSESSED_COUNT:
        problems.append('assessed_count: 手算=%d（出桥 12 - D 类 2 - G-09 BLOCK 载体 S-008）'
                        ' 实测=%s' % (ASSESSED_COUNT, s10.assessed_count))
    if s20.assessed_count != ASSESSED_COUNT:
        problems.append('OAT_20 assessed_count: 手算=%d 实测=%s'
                        % (ASSESSED_COUNT, s20.assessed_count))
    if s10.flipped_count != 0:
        problems.append('OAT_10 flipped_count: 手算=0 实测=' + str(s10.flipped_count))
    if not _ratio_eq(s10.overall_flip_rate, _q(Decimal(0))):
        problems.append('OAT_10 overall_flip_rate: 手算=0.000000000000 实测='
                        + str(s10.overall_flip_rate))
    if s20.flipped_count != hand_flipped:
        problems.append('OAT_20 flipped_count: 手算=%d（S-002 / S-004 / S-007 各恰 1 次）实测=%s'
                        % (hand_flipped, s20.flipped_count))
    want20 = _q(Decimal(s20.flipped_count) / Decimal(s10.assessed_count))
    if not _ratio_eq(s20.overall_flip_rate,
                     _q(Decimal(hand_flipped) / Decimal(ASSESSED_COUNT))):
        problems.append('OAT_20 overall_flip_rate: 手算=%d/%d=%s 实测=%s'
                        % (hand_flipped, ASSESSED_COUNT,
                           _q(Decimal(hand_flipped) / Decimal(ASSESSED_COUNT)),
                           s20.overall_flip_rate))
    elif not _ratio_eq(want20, s20.overall_flip_rate):
        problems.append('flip_rate 恒等式（翻转数/参评数）不成立：' + str(want20)
                        + ' vs ' + str(s20.overall_flip_rate))
    labels = {r.strategy_id: r for r in report20.by_strategy}
    if sorted(labels) != sorted(ASSESSED):
        problems.append('by_strategy 集合: 手算=' + str(ASSESSED) + ' 实测='
                        + str(sorted(labels)))
    for sid in ASSESSED:
        row = labels.get(sid)
        if row is None:
            continue
        n_flip = hand_flips.get(sid, 0)
        want = _q(Decimal(n_flip) / Decimal(12))
        if not _ratio_eq(row.flip_under_pct20, want):
            problems.append('%s flip_under_pct20: 手算=%s（翻转 %d / 12 次扰动）实测=%s'
                            % (sid, want, n_flip, row.flip_under_pct20))
    _diffs(problems)

    s002 = labels['S-002']
    assert _code(s002.stability_label) == 'NEAR_BOUNDARY', \
        'K-11 取 [L746] 默认 0.05/0.15 时 0.083333333333 落 NEAR_BOUNDARY；' \
        '实测 ' + str(s002.stability_label) + '（候选组差异见 docstring）'
    for sid in ('S-004', 'S-007'):
        assert _code(labels[sid].stability_label) == 'NEAR_BOUNDARY', \
            ('K-11 取 [L746] 默认 0.05/0.15 时 ' + sid + ' 的 1/12 = 0.083333333333 也应落'
             ' NEAR_BOUNDARY；实测 ' + str(labels[sid].stability_label))
    assert scheme(report10, 'OAT_10').flag is None, \
        'OAT_10 手算 0 次翻转 -> overall_flip_rate = 0.000000000000，不触发任何 K-11 档位'
    for stable_max, review_max in K11_CANDIDATES:
        cfg = {'stable_max': str(stable_max), 'review_max': str(review_max)}
        again = sensitivity.run(_sensitivity_ctx(base), ('OAT_20',), cfg,
                                weights=base.fx['weights'], grade_fn=base.grade_fn())
        got = scheme(again, 'OAT_20')
        assert _ratio_eq(got.overall_flip_rate,
                         _q(Decimal(hand_flipped) / Decimal(ASSESSED_COUNT))), \
            'flip_rate 与 K-11 无关（候选组 ' + str((stable_max, review_max)) + '）'
# --------------------------------------------------------------------------
# G-07  LOO 单指标过度影响 -> loo_impact 最大者为该指标 + DOMINANT_METRIC 警示
# --------------------------------------------------------------------------
def test_g07_loo_and_mc_and_norm_swap_refuse_missing_config_or_hooks(fx, base):
    '''G-07 前置纪律（R-12 / 不猜数）：digest 未固定的必填项与未注入的钩子一律显式抛错。

    手算依据（M13）：[L1017]「未设 seed 则拒绝运行 MC」-> SeedRequiredError；[L1020] LOO 的
      主导判据 loo_dominant_flip_rate 不在 digest 固定的三个值（stable_max 0.05 /
      review_max 0.15 / loo_sampling_threshold 60）之内 -> 必填注入，缺则 MissingConfigError，
      不得给默认值；[L749] NORM_SWAP 需要 Step 2 的另一种归一方法，钩子缺失 -> HookRequiredError
      （sensitivity 不得自己复制 normalize，R-1 / R-7）。
    '''
    ctx = _sensitivity_ctx(base)
    with pytest.raises(sensitivity.MissingConfigError) as excinfo:
        sensitivity.run(ctx, ('LOO',), None, weights=fx['weights'], grade_fn=base.grade_fn())
    assert 'loo_dominant_flip_rate' in str(excinfo.value)
    with pytest.raises(sensitivity.MissingConfigError):
        sensitivity.run(ctx, ('LOO',), {}, weights=fx['weights'], grade_fn=base.grade_fn())
    with pytest.raises(sensitivity.SeedRequiredError):
        sensitivity.run(ctx, ('MC',), {'mc_samples': '50', 'dirichlet_concentration': '1'},
                        weights=fx['weights'], grade_fn=base.grade_fn())
    with pytest.raises(sensitivity.HookRequiredError):
        sensitivity.run(ctx, ('NORM_SWAP',),
                        {'norm_swap_method': 'z_score', 'norm_swap_min_rank_correlation': '0.9'},
                        weights=fx['weights'], grade_fn=base.grade_fn())
    with pytest.raises(sensitivity.HookRequiredError):
        sensitivity.run(ctx, ('OAT_20',), None, weights=fx['weights'], grade_fn=None)


def test_g07_loo_impact_max_is_the_dominant_weight_metric_m_rev_minor(fx, base):
    '''G-07（M31 1409 行）：loo_impact 最大者为该指标，报告输出「存在单一指标过度影响」。

    输入构造（全部取自 A1 冻结件，manifest 的 deliberate_constructions 第 6 条明文
      「M_REV_MINOR：主导权重指标，CONTRIB 内 0.80，ref = T-SEN-02/G-07」）：
      T7 level2 CONTRIB = {M_REV_MINOR 0.80, M_AUM_MINOR 0.10, M_CUST_GAIN 0.10}，
      一级 CONTRIB = 0.30；14 个签认指标里唯一单项直接权重 0.30 * 0.80 = 0.240000。
    手算（LOO 影响力 = 剔除该指标、按 [L954] 维度内重归一后综合分的最大跨度；除法 q12）：
      * S-009 的 CONTRIB 构成：attainments M_REV_MINOR 2.000000000000（28000/10000 = 2.8
        触 K-05 上限 2 被裁剪）、M_AUM_MINOR 1.000000000000、M_CUST_GAIN 2.000000000000
        （300/100 = 3.0 触上限被裁剪）->
        CONTRIB = 0.8*2.0 + 0.1*1.0 + 0.1*2.0 = 1.600000000000 + 0.100000000000
                  + 0.200000000000 = 1.900000000000
        剔除 M_REV_MINOR -> CONTRIB = (0.10*1.000000000000 + 0.10*2.000000000000)
                                     / (0.10 + 0.10) = 0.300000000000/0.20
                                    = 1.500000000000
        综合分跨度 = 0.30 * (1.900000000000 - 1.500000000000) = 0.30*0.400000000000
                  = 0.120000000000，即 1.268600000000 -> 1.148600000000
      * **K-29（LOO-1 @ 858ebc8 实测）**：LOO targets 实为 **15** 条，含未签认指标
        M_REPEAT_USE_COUNT，不是本 docstring 旧版写的「14 个签认指标」；旧版逐指标跨度清单
        绑定 A1c 之前的 fixtures，已整体作废。
      * **K-26（LOO-1 @ 858ebc8 净树实测）**：[L748] 的 LOO 影响力排名列
        （ORCH-40 第7条已裁 + R-15 授权新增承载字段 SensitivityReport.loo_impact）中
        loo_impact_max = **M_REV_MINOR 0.120000000000**，与本条 assert 的手算跨度逐位相符；
        同列的 M_RETENTION_RATE 已由旧版的 0.098000000000 变为 **0.012950000000**
        （A1c 重冻后旧值失效）。
      * 本条 **assert 行一行未改**（包令 ⑥ / K-26 / K-29 只授权更新 docstring 文字与陈旧清单，
        改前改后均 2 passed）；assert 里的「综合分跨度」是测试内自算量（对 SIGNED 指标 x
        ASSESSED 策略取 |composite(剔除该指标) - composite(基线)| 的最大值），ASSESSED 已由
        6 扩为 9（A1c D-A1-02），候选变多而 M_REV_MINOR 仍以 0.120000000000 居首 ->
        断言是**加强**而非弱化。手算：0.30 * (1.900000000000 - 1.500000000000)
        = 0.120000000000（剔除后 CONTRIB = (0.10*1.000000000000 + 0.10*2.000000000000)
        / (0.10 + 0.10) = 1.500000000000，[L954] 维度内重归一）。
        -> loo_impact 最大者 = M_REV_MINOR（M31 [L1409] 的 loo_impact_max）。
      * DOMINANT_METRIC（[L748]「单指标剔除导致 flip_rate 超阈 -> 警示」）：把阈值取到区间
        下界 0（即「有任何翻转就算」，不引入任何治理签认值）时，主导清单必须非空且报告级
        flags 含 DOMINANT_METRIC，这就是 M31 要求的「存在单一指标过度影响」警示面。
    实测与手算不符（dominant 清单按**翻转计数**排序：M_RETENTION_RATE 3/6、
      M_SATISFY_SCORE 与 M_CONTACT_FREQ_PER_30D 各 1/6，而综合分跨度最大的 M_REV_MINOR
      翻转数为 0 -> 不在清单内）= GAP-E3-04，本条保持 RED，期望值不迁就实现。
    '''
    config = {'loo_dominant_flip_rate': '0'}
    report = sensitivity.run(_sensitivity_ctx(base), ('LOO',), config,
                             weights=fx['weights'], grade_fn=base.grade_fn())
    problems = []
    flags = [_code(f) for f in report.flags]
    if _code(RC.DOMINANT_METRIC) not in flags:
        problems.append('DOMINANT_METRIC 警示: 手算=必须出现（阈值取 0 时清单非空）实测=flags='
                        + str(flags))
    if _code(RC.LOO_SAMPLED) in flags:
        problems.append('LOO_SAMPLED: 手算=不标注（14 个指标 <= loo_sampling_threshold 60，'
                        '[L1020]）实测=已标注')
    if 'M_REV_MINOR' not in report.loo_dominant_metrics:
        problems.append('loo_impact 最大者: 手算=M_REV_MINOR（跨度 0.120000000000）实测='
                        'loo_dominant_metrics=' + str(report.loo_dominant_metrics))

    spans = {}
    for metric in sorted({r.metric_id for r in fx['metric_dict']
                          if r.signoff_status == 'SIGNED'}):
        doc = sensitivity.drop_metric(fx['weights'], metric)
        worst = Decimal(0)
        worst_at = None
        for sid in ASSESSED:
            frame = aggregate.compose(base.att, base.nrm, doc, None)
            hits = [r for r in frame.rows if r.strategy_id == sid and r.version_id == 'v1']
            if not hits:
                continue
            delta = abs(hits[0].composite_absolute - base.score(sid).composite_absolute)
            if delta > worst:
                worst, worst_at = delta, sid
        spans[metric] = (worst, worst_at)
    top = max(spans.items(), key=lambda item: item[1][0])
    if top[0] != 'M_REV_MINOR':
        problems.append('综合分跨度最大的指标: 手算=M_REV_MINOR 实测=' + str(top[0]))
    if not _ratio_eq(spans['M_REV_MINOR'][0], _q(Decimal('0.120000000000'))):
        problems.append('M_REV_MINOR 跨度: 手算=0.120000000000（0.30*(1.900000000000'
                        '-1.500000000000)）实测=' + str(spans['M_REV_MINOR'][0]))
    doc = sensitivity.drop_metric(fx['weights'], 'M_REV_MINOR')
    frame = aggregate.compose(base.att, base.nrm, doc, None)
    row = [r for r in frame.rows if r.strategy_id == 'S-009' and r.version_id == 'v1'][0]
    if not _ratio_eq(row.composite_absolute, _q(Decimal('1.148600000000'))):
        problems.append('S-009 剔除 M_REV_MINOR 后的 composite_absolute: 手算='
                        '1.268600000000-0.120000000000=1.148600000000 实测='
                        + str(row.composite_absolute))
    if not _ratio_eq(row.dim_absolute['CONTRIB'], _q(Decimal('1.500000000000'))):
        problems.append('S-009 剔除后的 CONTRIB: 手算=0.300000000000/0.20=1.500000000000 实测='
                        + str(row.dim_absolute['CONTRIB']))
    _diffs(problems)


# --------------------------------------------------------------------------
# G-10  未签认指标：剔除 + coverage 下降 + METRIC_NOT_SIGNED；维度清空 -> BLOCK
# --------------------------------------------------------------------------
def _preflight_inputs(fx, metric_dict=None, facts=None):
    return Inputs(strategy_master=fx['master'],
                  metric_dict=tuple(fx['metric_dict'] if metric_dict is None else metric_dict),
                  metric_facts=tuple(fx['facts'] if facts is None else facts),
                  design_cards=fx['cards'], redlines=fx['redlines'], previous_ledger=())


def _preflight_config(fx, weights, warn, block):
    return preflight.PreflightConfig(period=EVAL_PERIOD, period_ref_date=AS_OF,
                                     weight_version=weights, anchor_set=fx['anchor'],
                                     signed_signoff_status=('SIGNED',),
                                     missing_rate_warn=warn, missing_rate_block=block)


def _weights_with_whatif_run_id(fx):
    '''R-2 构造：给 T7 补 provenance.whatif_run_id，以隔离 C-02（GAP-E3-05）。

    只改内存副本，不动 fixtures 文件；kind 取 EXPERT_ONLY（[L1231] 三取一），签认四元组取
    T7 逐字的 approved_by / approved_date / effective_from / effective_to。'''
    raw = dict(fx['raw']['weight_version'][0])
    raw['provenance'] = WeightProvenance(
        kind='EXPERT_ONLY', whatif_run_id='SYNTH-WHATIF-E3-0001',
        approved_by=raw['approved_by'], approved_date=date.fromisoformat(raw['approved_date']),
        effective_from=date.fromisoformat(raw['effective_from']),
        effective_to=date.fromisoformat(raw['effective_to']))
    return WeightVersionDoc(**raw)


def test_g10_pending_metric_is_dropped_coverage_falls_and_reason_is_registered(fx):
    '''G-10（M31 1412 行 / C-02 [L901]）：未签认指标剔除 + coverage 下降 + METRIC_NOT_SIGNED。

    输入构造：T2 里 M_REPEAT_USE_COUNT（dim SUST，target 100，COUNT）的
      signoff_status = PENDING、signoff_date = null（fixtures/input/metric_dict.jsonl 逐字，
      A1 golden_map G-10 的 probe 也钉死这一点）；其余 14 个指标 SIGNED。
    手算（剔除后的 coverage 分母按 preflight 的口径取指标字典全量 15，分子取「签认且有可用
      事实行」的指标数；各策略评价期 2026-Q3 的事实行数逐字取自 T3）：
      * dropped_metrics = ('M_REPEAT_USE_COUNT',)；签认指标数 = 15 - 1 = 14。
      * S-001 / S-002 / S-003 / S-004 / S-007 / S-009 / S-010 / S-012 有 15 行事实，其中
        M_REPEAT_USE_COUNT 未签认 -> 分子 14 -> coverage = 14/15 = 0.933333333333。
      * S-006 另缺 M_CUST_GAIN（G-09 的 SKIP 分支）、S-011 缺 M_ROI（IMPUTE_MEDIAN 分支）、
        S-005/v2 缺 M_CAMPAIGN_COST_MINOR（ZERO 分支）、S-008 缺 M_SATISFY_SCORE（BLOCK
        分支）-> 分子 13 -> coverage = 13/15 = 0.866666666667。
      * 对照（把 M_REPEAT_USE_COUNT 改成 SIGNED 的内存副本，其余逐字不变）：分子 +1
        -> S-001 = 15/15 = 1.000000000000、S-006 = 14/15 = 0.933333333333
        -> 未签认剔除使 coverage 恰好下降 1/15 = 0.066666666667（M31「coverage 下降」）。
      * K-10（missing_rate_warn / block，PLACEHOLDER）：上列 5 组候选值下 C-02 的剔除结论、
        METRIC_NOT_SIGNED 码与 coverage 数值逐组相同（缺失率只影响 C-04 的 WARNING 面，
        不影响 C-02），故本条结论对 K-10 取值不敏感。
      * GAP-E3-05 已由 A1c（D-A1-04）关闭：冻结 T7 现已带 provenance 七键与
        whatif_run_id = WIF-SYNTH-2026-01 -> C-01（[L900]）三要件齐备、不再阻断，故尾部对照
        断言 status != BLOCK、exit_code = 0 且不出 WEIGHT_MISSING_WHATIF_RUN_ID；本条主体
        「未签认只 WARN」的判据与之无关，且未出现 DIMENSION_EMPTIED（SUST 仍有
        M_RETENTION_RATE 签认）。_weights_with_whatif_run_id 的 R-2 隔离支架因此已无必要，
        函数保留不删（避免弱化其它引用点）。
    '''
    signed_copy = tuple(row.model_copy(update={'signoff_status': 'SIGNED'})
                        for row in fx['metric_dict']
                        if row.metric_id == 'M_REPEAT_USE_COUNT')
    control_dict = tuple(signed_copy + tuple(row for row in fx['metric_dict']
                                             if row.metric_id != 'M_REPEAT_USE_COUNT'))
    weights = _weights_with_whatif_run_id(fx)
    for warn, block in K10_CANDIDATES:
        result = preflight.run(_preflight_inputs(fx), _preflight_config(fx, weights, warn, block))
        assert result.dropped_metrics == ('M_REPEAT_USE_COUNT',), \
            'K-10=' + str((warn, block)) + ' 时剔除集应恰为该未签认指标，实测 ' \
            + str(result.dropped_metrics)
        hits = [f for f in result.findings
                if f.code == 'C-02' and f.reason_code == _code(RC.METRIC_NOT_SIGNED)]
        assert len(hits) == 1, 'K-10=' + str((warn, block)) + ' 时应恰有一条 C-02 未签认判定'
        assert hits[0].scope == 'metric:M_REPEAT_USE_COUNT'
        assert hits[0].blocks_run is False, '未签认是 WARN，不阻断整次运行 [L901]'
        assert result.status == 'WARN', 'K-10=' + str((warn, block)) + ' 实测 ' + result.status
        assert result.exit_code == 0
        assert _ratio_eq(result.coverage_after_drop['S-001'], _q(Decimal(14) / Decimal(15))), \
            '手算 14/15 = 0.933333333333，实测 ' + str(result.coverage_after_drop['S-001'])
        assert _ratio_eq(result.coverage_after_drop['S-006'], _q(Decimal(13) / Decimal(15))), \
            '手算 13/15 = 0.866666666667（另缺 M_CUST_GAIN），实测 ' \
            + str(result.coverage_after_drop['S-006'])
        assert result.emptied_dims == (), 'SUST 仍有 M_RETENTION_RATE 签认，不得判清空'
        control = preflight.run(_preflight_inputs(fx, metric_dict=control_dict),
                                _preflight_config(fx, weights, warn, block))
        assert _ratio_eq(control.coverage_after_drop['S-001'], _q(Decimal(1))), \
            '对照（全部签认）应为 15/15 = 1，实测 ' + str(control.coverage_after_drop['S-001'])
        drop = control.coverage_after_drop['S-001'] - result.coverage_after_drop['S-001']
        assert _ratio_eq(drop, _q(Decimal(1) / Decimal(15))), \
            'coverage 下降量手算 = 1/15 = 0.066666666667，实测 = ' + str(drop)
        assert control.coverage_after_drop['S-001'] > result.coverage_after_drop['S-001']

    frozen = preflight.run(_preflight_inputs(fx), _preflight_config(
        fx, fx['weights'], Decimal('0.10'), Decimal('0.30')))
    # A1c（D-A1-04）已给冻结 T7 补齐 provenance 七键与 whatif_run_id = WIF-SYNTH-2026-01
    # -> C-01（M22 [L900]「status = FROZEN；评价期在生效区间内；含 approved_by /
    # approved_date / whatif_run_id」）三要件齐备，不再阻断。改前这两行断言的是
    # 「provenance = null -> 必 BLOCK」（GAP-E3-05），其前提已被 A1c 消除；按 [L900] 反转
    # 为正向断言（并要求 exit_code = 0），属**精确化而非弱化**（M31 [L1419] 要求显式说明）。
    assert fx['weights'].provenance is not None, \
        'A1c D-A1-04：冻结 T7 必须有 provenance（[L900] C-01 三要件之一）'
    assert fx['weights'].provenance.whatif_run_id == 'WIF-SYNTH-2026-01', \
        'fixtures/input/weight_version.jsonl 逐字 whatif_run_id = WIF-SYNTH-2026-01（[L900]）'
    assert not any(f.reason_code == _code(RC.WEIGHT_MISSING_WHATIF_RUN_ID)
                   for f in frozen.findings), \
        'GAP-E3-05 已关闭：补齐 whatif_run_id 后 C-01 不得再产 WEIGHT_MISSING_WHATIF_RUN_ID'
    assert not any(f.code == 'C-01' and f.blocks_run for f in frozen.findings), \
        '[L900] 三要件齐备 -> C-01 不得阻断，实测阻断 findings=' \
        + str([f.reason_code for f in frozen.findings if f.code == 'C-01'])
    assert frozen.status != 'BLOCK' and frozen.exit_code == 0, \
        'A1c 后冻结件不应因 C-01 被 BLOCK：实测 status=' + frozen.status \
        + ' exit_code=' + str(frozen.exit_code)


# 单维/双维清空后的一级权重重归一手算（M22 C-02 [L901] / M22 异常处置表 [L1286]；取值来源
# fixtures/input/weight_version.jsonl -> T7 逐字 level1_weights）。每维 q12 = 1E-12 ROUND_HALF_UP。
L1_FROZEN = {'CONTRIB': Decimal('0.30'), 'COST': Decimal('0.14'), 'EFFIC': Decimal('0.21'),
             'EXPER': Decimal('0.21'), 'PROC': Decimal('0.07'), 'SUST': Decimal('0.07')}
REWEIGHT_ONE_DIM_EMPTIED = {                      # 手算：w / 0.93（1 - 0.07），SUST = 0
    'CONTRIB': '0.322580645161',                  # 10/31 = 0.3225806451612903...  第13位=2 -> 舍
    'COST':    '0.150537634409',                  # 14/93 = 0.1505376344086021...  第13位=6 -> 进
    'EFFIC':   '0.225806451613',                  #  7/31 = 0.2258064516129032...  第13位=9 -> 进
    'EXPER':   '0.225806451613',
    'PROC':    '0.075268817204',                  #  7/93 = 0.0752688172043010...  第13位=3 -> 舍
    'SUST':    '0',
}                                                 # Σ 逐位相加 = 1.000000000000（Decimal 精确）
REWEIGHT_TWO_DIMS_EMPTIED = {                     # PROC + SUST 置 0，剩余和 = 1 - 0.14 = 0.86
    'CONTRIB': '0.348837209302',                  # 15/43 = 0.3488372093023255...
    'COST':    '0.162790697674',                  #  7/43 = 0.1627906976744186...
    'EFFIC':   '0.244186046512',                  # 21/86 = 0.2441860465116279...
    'EXPER':   '0.244186046512',
    'PROC':    '0',
    'SUST':    '0',
}                                                 # Σ = 1.000000000000（Decimal 精确）


def _reweight_hand(table, zeroed):
    '''[L901]/[L1286] 的「该维度 W 置 0 重归一」手算：返回 {dim: q12 权重}，Σ 必须精确 = 1。

    这是**契约算式**的独立复算（V-9），不是从任何实现输出反填：分母 = 1 - Σ(被置 0 维度的 W)。
    '''
    keep = Decimal(1) - sum((table[d] for d in zeroed), Decimal(0))
    out = {d: (Decimal(0) if d in zeroed else _q(table[d] / keep)) for d in sorted(table)}
    assert sum(out.values(), Decimal(0)) == Decimal(1), \
        '重归一后权重和必须 Decimal 精确等于 1（V-9 / M16），实测 ' + str(sum(out.values()))
    return out


def test_g10_single_dimension_emptied_reweights_to_zero_and_warns_not_blocks(fx):
    '''G-10（规范判据 M22 C-02 = SDD [L901]；ORCH-35 裁决，替代按 M31 [L1412] 写的旧期望）。

    改名 + 改期望的原因（M31 [L1419]「期望值由首次通过人工评审的运行结果固化；之后任何变更都
    必须显式更新期望值并说明原因」）：
      旧名 test_g10_sust_dimension_emptied_must_block_preflight 按 M31 [L1412]「若该维度被清空
      → preflight BLOCK」写期望，与 M22 C-02（[L901]）「某维度被清空 → 该维度 W 置 0 重归一；
      清空维度数 ≥ 2 → BLOCK」互斥（GAP-E3-02）。ORCH-35 裁定 [L901] 为规范判据，决定性理由：
      [L901] 同句的「W 置 0 重归一」若单维即 BLOCK 则该支**成为死条款**（永远执行不到重归一）
      -> 实现正确、测试期望过严。M22 异常处置表 [L1286] 与 [L901] 同口径（双来源印证），并给出
      披露码 = WEIGHT_REALLOCATED。M31 [L1412] 与 §4.4 [L1585] 记 **ERRATUM-01**。
      DIMENSION_EMPTIED 码在 SDD 全文 **0 命中** = 工程自名（**ERRATUM-03**），不改名不删除，
      但其 severity / blocks_run 须服从 [L901]（单维清空场景 = WARN / blocks_run False）；
      本条**不把它当作规范判据**，只断言「阈值未达时不得出现」。
    输入构造：变体 fixtures/variants/G10_dim_emptied.json（subject = M_RETENTION_RATE）把 SUST
      的第二个指标也置 PENDING；基线里 M_REPEAT_USE_COUNT 已是 PENDING -> SUST 两指标全未签认。
      权重直接用冻结 T7：A1c（D-A1-04）已补 provenance 七键与 whatif_run_id = WIF-SYNTH-2026-01
      -> C-01（[L900]）不再阻断，_weights_with_whatif_run_id 的 R-2 隔离支架已无必要（函数保留
      不删，以免弱化其它引用点）。
    手算（逐条见 WORKSHEET §4.3）：
      * dropped_metrics = (M_REPEAT_USE_COUNT, M_RETENTION_RATE)（metric_id 升序）；
        emptied_dims = (SUST,)。
      * signed = 15 - 2 = 13；coverage 分母 = 指标字典全量 15 ->
        S-001 = q12(13/15) = 0.866666666667、S-006 = q12(12/15) = 0.800000000000（另缺
        M_CUST_GAIN，missing_rule = SKIP）。
      * [L901]「清空维度数 ≥ 2 → BLOCK」的反面：1 < 2 -> status = WARN、exit_code = 0。
      * [L1286] 明列披露码 = WEIGHT_REALLOCATED（恰 1 条，scope = dim:SUST）；未签认剔除 ->
        METRIC_NOT_SIGNED（恰 2 条，scope = metric:<id>）；两者 blocks_run 均 False。
      * W_SUST 置 0 后重归一 = REWEIGHT_ONE_DIM_EMPTIED，Σ Decimal 精确 = 1（V-9）。
      * K-10（missing_rate warn/block，PLACEHOLDER）不敏感性：5 组候选值下 C-02 的全部结论
        逐组相同（缺失率只影响 C-04 面）。
    '''
    metric_dict = _variant_table(fx, 'metric_dict', 'G10_dim_emptied')
    hand_w = _reweight_hand(L1_FROZEN, ('SUST',))
    for dim, want in sorted(REWEIGHT_ONE_DIM_EMPTIED.items()):
        assert hand_w[dim] == _q(Decimal(want)), \
            ('[L901]/[L1286] 重归一手算 W_' + dim + ' = ' + want + ' 实测算式得 '
             + str(hand_w[dim]))
    problems = []
    for warn, block in K10_CANDIDATES:
        result = preflight.run(_preflight_inputs(fx, metric_dict=metric_dict),
                               _preflight_config(fx, fx['weights'], warn, block))
        tag = 'K-10=' + str((warn, block)) + ' '
        if result.dropped_metrics != ('M_REPEAT_USE_COUNT', 'M_RETENTION_RATE'):
            problems.append(tag + 'dropped_metrics: 手算=(M_REPEAT_USE_COUNT, M_RETENTION_RATE)'
                            ' 实测=' + str(result.dropped_metrics))
        if result.emptied_dims != ('SUST',):
            problems.append(tag + 'emptied_dims: 手算=(SUST,) 实测=' + str(result.emptied_dims))
        if not _ratio_eq(result.coverage_after_drop['S-001'], _q(Decimal(13) / Decimal(15))):
            problems.append(tag + 'S-001 coverage: 手算=13/15=0.866666666667 实测='
                            + str(result.coverage_after_drop['S-001']))
        if not _ratio_eq(result.coverage_after_drop['S-006'], _q(Decimal(12) / Decimal(15))):
            problems.append(tag + 'S-006 coverage: 手算=12/15=0.800000000000（另缺 M_CUST_GAIN）'
                            ' 实测=' + str(result.coverage_after_drop['S-006']))
        if result.status != 'WARN':
            problems.append(tag + 'status: [L901] 手算=WARN（清空维度数 1 < 2）实测='
                            + result.status)
        if result.exit_code != 0:
            problems.append(tag + 'exit_code: [L900]/[L901] 手算=0（非 BLOCK）实测='
                            + str(result.exit_code))
        c02 = [f for f in result.findings if f.code == 'C-02']
        not_signed = [f for f in c02 if _code(f.reason_code) == _code(RC.METRIC_NOT_SIGNED)]
        realloc = [f for f in c02 if _code(f.reason_code) == _code(RC.WEIGHT_REALLOCATED)]
        emptied = [f for f in c02 if _code(f.reason_code) == _code(RC.DIMENSION_EMPTIED)]
        if len(not_signed) != 2 or sorted(f.scope for f in not_signed) != \
                ['metric:M_REPEAT_USE_COUNT', 'metric:M_RETENTION_RATE']:
            problems.append(tag + 'METRIC_NOT_SIGNED: 手算=恰 2 条且 scope 为两个未签认指标'
                            ' 实测=' + str(sorted(f.scope for f in not_signed)))
        if len(realloc) != 1 or realloc[0].scope != 'dim:SUST':
            problems.append(tag + 'WEIGHT_REALLOCATED: 手算=恰 1 条 scope=dim:SUST（[L1286]'
                            ' 明列披露码）实测=' + str([f.scope for f in realloc]))
        if emptied:
            problems.append(tag + 'DIMENSION_EMPTIED: 手算=不得出现（[L901] 阈值 ≥2 未达，'
                            'ERRATUM-03）实测出现 ' + str(len(emptied)) + ' 条')
        if any(f.blocks_run for f in c02):
            problems.append(tag + 'C-02 的 blocks_run: 手算=全 False（[L901] 单维清空只 WARN）'
                            ' 实测=' + str([(f.scope, f.blocks_run) for f in c02 if f.blocks_run]))
        for f in c02:
            if not reason_codes.is_registered(_code(f.reason_code)):
                problems.append(tag + 'C-02 产出未注册码（H-7）：' + str(f.reason_code))
    frozen = preflight.run(_preflight_inputs(fx), _preflight_config(
        fx, fx['weights'], Decimal('0.10'), Decimal('0.30')))
    if any(_code(f.reason_code) == _code(RC.WEIGHT_MISSING_WHATIF_RUN_ID) for f in frozen.findings):
        problems.append('冻结 T7 仍缺 whatif_run_id：A1c D-A1-04 应已补 WIF-SYNTH-2026-01（[L900]）')
    if frozen.status == 'BLOCK' and any(f.code == 'C-01' and f.blocks_run for f in frozen.findings):
        problems.append('C-01 仍阻断冻结件：A1c 后 [L900] 三要件（FROZEN / 生效区间 /'
                        ' whatif_run_id）应齐备，实测 findings='
                        + str([f.reason_code for f in frozen.findings if f.code == 'C-01']))
    _diffs(problems)


def test_g10_two_dimensions_emptied_blocks_preflight_with_exit_code_2(fx):
    '''G-10 的**真 BLOCK 分支**（SDD [L901]「清空维度数 ≥ 2 → BLOCK」）—— 此前无任何测试覆盖。

    新增理由（ORCH-35 第3条）：补上 [L901] 真正 BLOCK 分支的覆盖，用以证明单维改 WARN 不是
    「为了转绿而放宽」，而是加强。断言总数严格多于改前（改前 6 类 x 5 组 K-10；
    改前那条 + 本条 = 11 类 + 12 类 x 5 组 K-10）。
    输入构造：**R-2 内存构造**（model_copy，只改内存副本、不动 fixtures 文件），把 PROC 与 SUST
      两个维度的全部指标置 PENDING。选 PROC + SUST 的理由：两维各恰 2 个指标，且与已知缺格载体
      （S-006 缺 M_CUST_GAIN / S-005v2 缺 M_CAMPAIGN_COST_MINOR / S-008 缺 M_SATISFY_SCORE，
      后者为 A1c D-A1-03 迁移后的新载体）无交集 -> coverage 手算最干净。
      **不需要新的 fixtures variant 文件**；若主控希望固化为 variant，见 NEED-FIXTURES.md 第4条。
    手算（逐条见 WORKSHEET §4.4）：
      * dropped_metrics = (M_OPTOUT_RATE, M_REACH_RATE, M_REPEAT_USE_COUNT, M_RETENTION_RATE)
        （升序：M_O < M_REACH < M_REPEAT < M_RETENTION）；emptied_dims = (PROC, SUST)，len = 2。
      * signed = 15 - 4 = 11 -> S-001 = q12(11/15) = 0.733333333333、
        S-006 = q12(10/15) = 0.666666666667（另缺 M_CUST_GAIN，属 CONTRIB、仍签认）。
      * [L901] 阈值已达 -> status = BLOCK、exit_code = 2（M21 [L892] 同口径）；
        [L917]：BLOCK 只写 audit_bundle -> output_fingerprints 为空 = 本次无任何评分产物。
      * 披露：METRIC_NOT_SIGNED 恰 4 条；WEIGHT_REALLOCATED 恰 2 条（scope 集 =
        {dim:PROC, dim:SUST}）；阻断级披露**必须出现**且 blocks_run = True。按 ERRATUM-03
        DIMENSION_EMPTIED 码名无原文依据，故同时用 reason_codes.is_registered(...) 做
        **关系式**断言，不钉死码名语义。
      * W_PROC = W_SUST = 0，重归一 = REWEIGHT_TWO_DIMS_EMPTIED，Σ Decimal 精确 = 1（V-9）。
      * K-10（PLACEHOLDER）不敏感性：5 组候选值下 C-02 的全部结论逐组相同。
    '''
    empty_dims = ('PROC', 'SUST')
    metric_dict = tuple(
        row.model_copy(update={'signoff_status': 'PENDING', 'signoff_date': None})
        if row.dim_code in empty_dims else row
        for row in fx['metric_dict'])
    hand_w = _reweight_hand(L1_FROZEN, empty_dims)
    for dim, want in sorted(REWEIGHT_TWO_DIMS_EMPTIED.items()):
        assert hand_w[dim] == _q(Decimal(want)), \
            ('[L901]/[L1286] 重归一手算 W_' + dim + ' = ' + want + ' 实测算式得 '
             + str(hand_w[dim]))
    want_dropped = ('M_OPTOUT_RATE', 'M_REACH_RATE', 'M_REPEAT_USE_COUNT', 'M_RETENTION_RATE')
    problems = []
    for warn, block in K10_CANDIDATES:
        result = preflight.run(_preflight_inputs(fx, metric_dict=metric_dict),
                               _preflight_config(fx, fx['weights'], warn, block))
        tag = 'K-10=' + str((warn, block)) + ' '
        if result.dropped_metrics != want_dropped:
            problems.append(tag + 'dropped_metrics: 手算=' + str(want_dropped)
                            + ' 实测=' + str(result.dropped_metrics))
        if result.emptied_dims != empty_dims:
            problems.append(tag + 'emptied_dims: 手算=' + str(empty_dims)
                            + ' 实测=' + str(result.emptied_dims))
        if len(result.emptied_dims) < 2:
            problems.append(tag + '清空维度数手算=2（达到 [L901] 阈值）实测='
                            + str(len(result.emptied_dims)))
        if not _ratio_eq(result.coverage_after_drop['S-001'], _q(Decimal(11) / Decimal(15))):
            problems.append(tag + 'S-001 coverage: 手算=11/15=0.733333333333 实测='
                            + str(result.coverage_after_drop['S-001']))
        if not _ratio_eq(result.coverage_after_drop['S-006'], _q(Decimal(10) / Decimal(15))):
            problems.append(tag + 'S-006 coverage: 手算=10/15=0.666666666667 实测='
                            + str(result.coverage_after_drop['S-006']))
        if result.status != 'BLOCK':
            problems.append(tag + 'status: [L901]「清空维度数 ≥ 2 → BLOCK」手算=BLOCK 实测='
                            + result.status)
        if result.exit_code != 2:
            problems.append(tag + 'exit_code: 手算=2（[L900]/[L901] BLOCK）实测='
                            + str(result.exit_code))
        c02 = [f for f in result.findings if f.code == 'C-02']
        not_signed = [f for f in c02 if _code(f.reason_code) == _code(RC.METRIC_NOT_SIGNED)]
        realloc = [f for f in c02 if _code(f.reason_code) == _code(RC.WEIGHT_REALLOCATED)]
        emptied = [f for f in c02 if _code(f.reason_code) == _code(RC.DIMENSION_EMPTIED)]
        if len(not_signed) != 4:
            problems.append(tag + 'METRIC_NOT_SIGNED: 手算=恰 4 条 实测=' + str(len(not_signed)))
        if sorted(f.scope for f in realloc) != ['dim:PROC', 'dim:SUST']:
            problems.append(tag + 'WEIGHT_REALLOCATED: 手算=恰 2 条 scope={dim:PROC,dim:SUST}'
                            '（[L1286]）实测=' + str(sorted(f.scope for f in realloc)))
        if not emptied:
            problems.append(tag + 'DIMENSION_EMPTIED: [L901] 阈值已达，必须出现阻断级披露，'
                            '实测缺席')
        else:
            if not all(f.blocks_run for f in emptied):
                problems.append(tag + 'DIMENSION_EMPTIED 的 blocks_run: 手算=True 实测='
                                + str([f.blocks_run for f in emptied]))
            if not all(reason_codes.is_registered(_code(f.reason_code)) for f in emptied):
                problems.append(tag + '阻断码未注册（H-7 / V-14）')
        if not any(f.blocks_run for f in result.findings):
            problems.append(tag + 'BLOCK 却没有任何 blocks_run=True 的 finding（V-14：不得静默）')
    _diffs(problems)


# --------------------------------------------------------------------------
# G-11  权重版本过期 / 金额非整数 -> 均 BLOCK、退出码 2、只写审计包、不产 score_card
# --------------------------------------------------------------------------
def _run_context(fx, config, reproducibility_hash='0' * 64):
    '''audit_bundle 的注入上下文（[L1051]）；run_at / run_id 由调用方注入，不读时钟（H-8）。'''
    return {
        'run_id': 'SYNTH-RUN-E3-G11', 'run_at': RUN_AT, 'dsm_version': '1.1',
        'design_version': 'DSM-v1.1', 'cel_contract_version': 'CEL-0',
        'config_snapshot_sha256': audit.config_snapshot_sha256(
            {'period': config.period, 'weight_version_id': config.weight_version
             .weight_version_id}),
        'seed': None, 'input_fingerprints': {}, 'sensitivity_schemes': (),
        'reproducibility_hash': reproducibility_hash,
    }


def test_g11a_stale_weight_version_blocks_with_exit_code_2_and_writes_only_audit(fx, tmp_path):
    '''G-11(a)（M31 1413 行 / C-01 [L900] / [L917]）：period 超出 effective_to -> BLOCK。

    输入构造：变体 fixtures/variants/G11_stale_weight.json 把 WV-SYNTH-2026 的
      effective_to 改为 2026-06-30（status 仍 FROZEN、approved_by / approved_date 逐字保留）。
    手算（A1 golden_map G-11 的 hand：effective_to 2026-06-30 早于评价期起点 2026-07-01）：
      * 评价期 2026-Q3 = 2026-07-01..2026-09-30，日期基准日取事实行 data_as_of = 2026-09-30
        （逐字取自 T3，非本包拟定）；2026-09-30 > 2026-06-30 -> 超出 effective_to -> C-01
        BLOCK，注册码 WEIGHT_VERSION_STALE（M31 写作 STALE，见 GAP-E3-01），作用位
        scope = weight_version:WV-SYNTH-2026。
      * [L917] 三条硬行为：status = BLOCK、exit_code = 2、BLOCK 时**只写 audit_bundle**，
        不产出 score_card（连空文件都不产）；K-10 的 5 组候选值不改变该结论。
    '''
    weights = _variant_weights(fx, 'G11_stale_weight', WEIGHT_VERSION_ID)
    assert weights.effective_to == date(2026, 6, 30) and weights.status == 'FROZEN'
    inputs = _preflight_inputs(fx)
    for warn, block in K10_CANDIDATES:
        config = _preflight_config(fx, weights, warn, block)
        result = preflight.run(inputs, config)
        assert result.status == 'BLOCK', 'K-10=' + str((warn, block)) + ' 实测 ' + result.status
        assert result.exit_code == 2, 'BLOCK 的退出码是 [L917] 的 2，实测 ' \
            + str(result.exit_code)
        hits = [f for f in result.findings
                if f.reason_code == _code(RC.WEIGHT_VERSION_STALE)]
        assert len(hits) == 1, '期望唯一一条过期判定，实测 ' + str(
            [f.reason_code for f in result.findings])
        assert hits[0].code == 'C-01' and hits[0].scope == 'weight_version:' + WEIGHT_VERSION_ID
        assert hits[0].blocks_run is True

    out_dir = tmp_path / 'g11a'
    config = _preflight_config(fx, weights, Decimal('0.10'), Decimal('0.30'))
    code, result, written = preflight.execute(inputs, config, out_dir,
                                              _run_context(fx, config))
    assert code == 2
    assert [Path(p).name for p in written] == ['audit.json'], \
        'BLOCK 时唯一产物是 audit_bundle（[L917]），实测 ' + str(written)
    names = sorted(p.name for p in Path(out_dir).iterdir())
    assert names == ['audit.json'], '目录里除审计包外不得有任何文件，实测 ' + str(names)
    assert not any('score_card' in name for name in names), '不得产出 score_card'
    body = json.loads(Path(out_dir, 'audit.json').read_text(encoding='utf-8'))
    assert body['exit_code'] == 2 and body['output_fingerprints'] == {}, \
        '审计包要记录「本次没有任何评分产物」'
    assert any(item['message'].find(_code(RC.WEIGHT_VERSION_STALE)) >= 0
               for item in body['preflight_findings'])


def test_g11b_non_integer_money_blocks_preflight_and_produces_no_score_card(fx, tmp_path):
    '''G-11(b)（M31 1413 行 / C-09 [L908] / V-9）：MONEY_MINOR 非整数 -> BLOCK，不出分。

    输入构造：fixtures/negative/G11_money_non_integer.json 的 row（A1 逐字）：
      (S-007, v1, 2026-Q3, M_REV_MINOR) 的 value = 100.5、value_num = 100.5（M_REV_MINOR
      的 unit = MONEY_MINOR，T2 逐字），该文件的 expect_rejected_by = models.MetricFactRow、
      expect_reason_code = MONEY_NON_INTEGER。
    手算（两道关卡都要拦住，且都不产出 score_card）：
      * 契约层（V-9：金额 = int 最小货币单位）：100.5 非整数 -> MetricFactRow 构造必被拒；
      * 门禁层（C-09）：把该值绕过模型注入（model_construct，只为让 preflight 真的看到
        一个非整数金额，不改 fixtures）-> unit = MONEY_MINOR 的三个值列（value / value_num /
        value_den）逐个按 [L908] 复核 -> MONEY_NON_INTEGER（BLOCK、属 RUN_BLOCKING_CODES），
        作用位含 metric_facts:S-007/v1/2026-Q3/M_REV_MINOR；value = 100.5 与 value_num =
        100.5 两处各一条，value_den = null 合格（_minor_ok 对 None 放行）。
      * [L917]：status = BLOCK、exit_code = 2、只写 audit.json。
    '''
    row = fx['negative']['row']
    assert fx['negative']['expect_reason_code'] == _code(RC.MONEY_NON_INTEGER)
    with pytest.raises(Exception) as excinfo:
        MetricFactRow(**row)
    assert 'value' in str(excinfo.value) or 'minor' in str(excinfo.value).lower(), \
        '模型层拒收非整数金额时报文要点名金额列，实测 ' + str(excinfo.value)[:200]

    weights = _weights_with_whatif_run_id(fx)
    bad = MetricFactRow.model_construct(**dict(row, data_as_of=AS_OF, snapshot_time=RUN_AT))
    facts = tuple(r for r in fx['facts']
                  if not (r.strategy_id == row['strategy_id'] and r.version_id == row['version_id']
                          and r.period == row['period'] and r.metric_id == row['metric_id']))
    inputs = _preflight_inputs(fx, facts=facts + (bad,))
    config = _preflight_config(fx, weights, Decimal('0.10'), Decimal('0.30'))
    result = preflight.run(inputs, config)
    hits = [f for f in result.findings if f.reason_code == _code(RC.MONEY_NON_INTEGER)]
    assert len(hits) == 2, '手算 value 与 value_num 两处非整数，实测 ' + str(
        [(f.scope, f.detail) for f in hits])
    assert all('M_REV_MINOR' in f.scope for f in hits), str([f.scope for f in hits])
    assert all('metric_facts:S-007' in f.scope for f in hits), str([f.scope for f in hits])
    assert result.status == 'BLOCK' and result.exit_code == 2

    out_dir = tmp_path / 'g11b'
    code, _, written = preflight.execute(inputs, config, out_dir, _run_context(fx, config))
    assert code == 2
    assert [Path(p).name for p in written] == ['audit.json']
    names = sorted(p.name for p in Path(out_dir).iterdir())
    assert names == ['audit.json'], '不得产出 score_card，实测 ' + str(names)

# --------------------------------------------------------------------------
# G-06（M31 1408 行中段）至少一个 NEAR_BOUNDARY 策略翻转为 L3
# --------------------------------------------------------------------------
def test_g06_at_least_one_near_boundary_strategy_flips_to_l3(fx, base, history):
    '''G-06 判据「至少一个 NEAR_BOUNDARY 策略翻转为 L3」的载体 S-004 手算。

    手算（输入取自 T2 target_value / T3 事实值 / T5 门槛 / 变体 OAT20 权重文档，
      未读任何实现输出；与 A1 golden_map G-06 的 hand S-004_base = 0.905000、
      S-004_oat20 = 0.896000 逐位对拍）：
      * CONTRIB（M03 [L464]，二级权重 REV .80 / AUM .10 / CUST .10 逐字取自 T7）：
          达成率 = 8000/10000 = 0.800000000000、10000/10000 = 1.000000000000、
                   60/100 = 0.600000000000
          CONTRIB = 0.8*0.800000000000 + 0.1*1.000000000000 + 0.1*0.600000000000
                  = 0.640000000000 + 0.100000000000 + 0.060000000000
                  = 0.800000000000
      * 其余五维各 0.950000000000（逐指标达成率由 T3 事实值与 T2 target_value 按 M02
        正向 actual/target、负向 target/actual 独立重算，中间量见探针
        dsm_stage/E3/probe_sens.py 的 base comp 行）。
      * 基线综合分 = 0.30*0.800000000000 + 0.70*0.950000000000
          = 0.240000000000 + 0.665000000000 = 0.905000000000
        -> 落在 T5 逐字门槛 [L2 floor 0.900000, L1 floor 1.000000) -> 基础等级 L2。
      * CONTRIB 权重 x 1.2（其余重归一合计 0.640000000000）后：
          0.36*0.800000000000 + 0.64*0.950000000000
          = 0.288000000000 + 0.608000000000 = 0.896000000000
        < L2 floor 0.900000000000 且 >= L3 floor 0.700000000000 -> L3。
      * 该策略在 [L746] 默认 0.05/0.15 下的逐策略翻转比例 = 1/12 = 0.083333333333
        落在 NEAR_BOUNDARY 带 -> 判据载体成立（与 test_g06_flip_rate_* 同一口径）。
    与实现的偏差（保持 RED，不迁就实现）：按 fixtures **当前实际内容**手算，S-004 的
      DID + CONCURRENT_CONTROL 卡缺 alt_method_note 与 interpretation_limit，
      M24 [L977] 第 5 步短路落证据 D -> NOT_ASSESSED，既不进 sensitivity 的 assessed 集
      （手算 assessed = 6，不含 S-004），也无从产生「翻转为 L3」的等级路径。
      归因：fixtures（D-A1-02，受控解冻 A1c 已裁未执行），不是 dsm 的定级缺陷；
      A1c 补齐这四条卡后本条改为 L2 -> L3，且需按 A3 B3 C4 D2 重新手算
      （GAP-E3-03(a)：本条 expects 在 A1c 执行后需重算，已登记 E3b）。
      分数轨（composite_absolute）不依赖证据等级，故综合分三条断言现在就应成立。
    '''
    weights20 = _variant_weights(fx, 'G06_weight_oat20', OAT20_WEIGHT_VERSION_ID)
    prev, streaks = history
    oat = _chain(fx, EVAL_PERIOD, weights=weights20, prev=prev, streaks=streaks)
    problems = []

    got_base = base.score('S-004').composite_absolute
    if not _ratio_eq(got_base, _q(Decimal('0.905000000000'))):
        problems.append('S-004 基线综合分：手算 0.30*0.800000000000 + 0.70*0.950000000000'
                        ' = 0.905000000000 实测=' + str(got_base))
    got_oat = oat.score('S-004').composite_absolute
    if not _ratio_eq(got_oat, _q(Decimal('0.896000000000'))):
        problems.append('S-004 扰动综合分：手算 0.36*0.800000000000 + 0.64*0.950000000000'
                        ' = 0.896000000000 实测=' + str(got_oat))
    dim_base = base.score('S-004').dim_absolute['CONTRIB']
    if not _ratio_eq(dim_base, _q(Decimal('0.800000000000'))):
        problems.append('S-004 CONTRIB：手算 0.640000000000 + 0.100000000000'
                        ' + 0.060000000000 = 0.800000000000 实测=' + str(dim_base))

    got_grade_base = base.grade('S-004').grade
    got_grade_oat = oat.grade('S-004').grade
    if got_grade_base != 'L2':
        problems.append('S-004 基线等级：M31 G-06 手算=L2（0.905000000000 落 [0.90, 1.00)）'
                        '实测=' + str(got_grade_base) + '（D-A1-02 使证据落 D -> NOT_ASSESSED）')
    if got_grade_oat != 'L3':
        problems.append('S-004 扰动等级：M31 G-06 手算=L3（0.896000000000 跌破 L2 floor 0.90'
                        '、仍 >= L3 floor 0.70）实测=' + str(got_grade_oat))
    report = sensitivity.run(_sensitivity_ctx(base), ('OAT_20',), None,
                            weights=fx['weights'], grade_fn=base.grade_fn())
    labels = sorted(r.strategy_id for r in report.by_strategy)
    if 'S-004' not in labels:
        problems.append('assessed 集：M31 G-06 要求 NEAR_BOUNDARY 载体进入敏感性分母'
                        '（手算 assessed 应含 S-004）实测 by_strategy=' + str(labels))
    _diffs(problems)


# ==========================================================================
# G-12  第二人复跑（M31 1414 行 / M25 [L1052]-[L1055] / [L1261]-[L1274] / [L1640]）
# ==========================================================================
def _att_index(chain, period):
    return {(r.strategy_id, r.version_id, r.metric_id): r for r in chain.att.rows
            if r.period == period}


def _fact_index(fx, period):
    return {(r.strategy_id, r.version_id, r.metric_id): r for r in fx['facts']
            if r.period == period}


def _card_index(cards):
    return {(r.strategy_id, r.version_id): r for r in cards}


def _cells_for(chain, score, weights, period, reverse=False, bump_money=False):
    '''per_metric / per_dim 两个内嵌块（[L1613]-[L1614]，键 = metric_id / dim_code）。

    实际值 / 目标值逐字取自 T3 的 value 与 T2 的 target_value（A1 构造，R-14），达成率取
    Step 1 的行。reverse 只改**插入顺序**（M25 rule 3 的键序无关性探针）；bump_money 只在
    内存里把 S-002 的 M_REV_MINOR 实际值 +1（证明哈希对这一位敏感）。
    per_dim.coverage 取该行整体 coverage（ScoreRow 只带一个 coverage，[L952]），
    per_dim.weight 取 T7 一级权重逐字 -> 这两处是本包的行构造选择，不参与 G-12 判据。
    '''
    md = {r.metric_id: r for r in chain.fx['metric_dict']}
    facts, att = _fact_index(chain.fx, period), _att_index(chain, period)
    pair = (score.strategy_id, score.version_id)
    per_metric = {}
    for key in sorted(facts):
        if key[:2] != pair:
            continue
        metric_id = key[2]
        actual = facts[key].value
        if bump_money and pair == ('S-002', 'v1') and metric_id == 'M_REV_MINOR':
            actual = actual + 1
        row = att.get(key)
        per_metric[metric_id] = ScoreCardMetricCell(
            actual_value=actual, target_value=md[metric_id].target_value,
            attainment=None if row is None else row.attainment)
    if reverse:
        per_metric = {k: per_metric[k] for k in reversed(list(per_metric))}
    dims = sorted(score.dim_absolute)
    if reverse:
        dims = list(reversed(dims))
    per_dim = {}
    for dim in dims:
        per_dim[dim] = ScoreCardDimCell(
            attainment=score.dim_absolute[dim],
            relative_score=None if not score.dim_relative else score.dim_relative.get(dim),
            coverage=score.coverage,
            weight=_q(Decimal(str(weights.level1_weights[dim]))))
    return per_metric, per_dim


def _score_card_rows(chain, weights, run_id, period, reverse=False, bump_money=False):
    '''score_card 的 35 列（列名逐字抄 dsm/models.py，R-2）。

    本包的行构造选择（不参与 G-12 判据，在此公开以免被当成期望值）：
      * ranking_pool / rank_in_pool / pool_size 取 Step 7 的行；pool_size 取同池行数
        （[L1622] the pool's size，按 pool_key 分组计数，int）。
      * redline_pass = 该 pair 全部红线行 hit 均为 False；redline_flags = 命中行 reason_code
        的去重升序（[L1619]：命中时分数照算但不生效，不改写分数）。
      * stability_label / flip_under_pct10 / flip_under_pct20 留 None：[L1624] 明文允许
        Step 8 未跑时为 null；G-12 的判据是两次独立复跑逐位相等，不依赖 Step 8。
      * value_captured_minor / incremental_* / estimator_method：CEL-0 一律 null
        （[L1626] + [L1896]：首版全空，null 不得填 0）。
    '''
    rl_rows = {}
    for row in chain.rl.rows:
        key = (row.strategy_id, row.version_id, row.period)
        rl_rows.setdefault(key, []).append(row)
    ev_by_pair = {(r.strategy_id, r.version_id): r for r in chain.ev.rows}
    pool_by_pair, pool_size = {}, {}
    if chain.pools is not None:
        for row in chain.pools.rows:
            pool_by_pair[(row.strategy_id, row.version_id, row.period)] = row
            group = (row.pool_key.biz_domain, row.pool_key.evidence_class)
            pool_size[group] = pool_size.get(group, 0) + 1
    cards = _card_index(chain.fx['cards'])
    rows = []
    for score in chain.scores.rows:
        if score.period != period:
            continue
        pair = (score.strategy_id, score.version_id)
        grade = chain.grade(score.strategy_id, score.version_id, period)
        ev = ev_by_pair[pair]
        hits = rl_rows.get(pair + (period,), [])
        pool = pool_by_pair.get(pair + (period,))
        card = cards.get(pair)
        per_metric, per_dim = _cells_for(chain, score, weights, period,
                                         reverse=reverse, bump_money=bump_money)
        group = None if pool is None else (pool.pool_key.biz_domain,
                                           pool.pool_key.evidence_class)
        rows.append(ScoreCardRow(
            strategy_id=score.strategy_id, version_id=score.version_id, period=period,
            weight_version_id=score.weight_version_id, dict_version=DICT_VERSION,
            anchor_set_id=ANCHOR_SET_ID, run_id=run_id,
            per_metric=per_metric, per_dim=per_dim,
            composite_absolute=score.composite_absolute,
            composite_relative=score.composite_relative,
            evidence_class=ev.evidence_class, evidence_reason=ev.evidence_reason,
            evidence_source=ev.evidence_source, interpretation_limit=ev.interpretation_limit,
            redline_pass=all(not r.hit for r in hits),
            redline_flags=tuple(sorted({str(_code(r.reason_code)) for r in hits if r.hit})),
            grade=grade.grade,
            grade_reason_codes=tuple(str(_code(x)) for x in grade.grade_reason_path),
            capped_flag=grade.capped, cap_reason=grade.cap_reason,
            ranking_pool=None if pool is None else pool.pool_key,
            rank_in_pool=None if pool is None else pool.pool_rank,
            pool_size=None if pool is None else pool_size[group],
            eligible_for_L1_library=False if pool is None else pool.primary_pool_eligible,
            l1_gate_reasons=() if (pool is None or pool.reject_reason is None)
            else (str(_code(pool.reject_reason)),),
            usable_for_elimination=grade.usable_for_elimination,
            incremental_value=None if card is None else card.incremental_value,
            incremental_ci_lower=None if card is None else card.incremental_ci_lower,
            incremental_ci_upper=None if card is None else card.incremental_ci_upper,
            estimator_method=None if card is None else card.estimator_method,
            value_captured_minor=None))
    return tuple(reversed(rows)) if reverse else tuple(rows)


def _ledger_rows(chain, fx, period, reverse=False):
    '''grade_ledger 的 14 列：recommended / decided 两列并存（ruling 24 / V-8 [L1863]）。

    decided_action / decision_note / deadline / archive_ref 留 None：模型只建议、人来定并
    签字（[L1630]），本包不代人决策；ledger_complete=False 同理（人工签认未完成）。
    owner_dept / owner_name 逐字取自 T1；previous_grade 取上一期（2026-Q2）同 pair 的等级。
    '''
    master = {(r.strategy_id, r.version_id): r for r in fx['master']}
    previous = {}
    for row in (chain.prev.rows if chain.prev is not None else ()):
        if row.period == '2026-Q2':
            previous[(row.strategy_id, row.version_id)] = row.grade
    rows = []
    for grade in chain.grades.rows:
        if grade.period != period:
            continue
        pair = (grade.strategy_id, grade.version_id)
        owner = master.get(pair)
        rows.append(GradeLedgerRow(
            strategy_id=grade.strategy_id, version_id=grade.version_id, period=period,
            grade=grade.grade, previous_grade=previous.get(pair),
            recommended_action=None if not grade.action else ' / '.join(grade.action), decided_action=None, decision_note=None,
            owner_dept=None if owner is None else owner.owner_dept,
            owner_name=None if owner is None else owner.owner_name,
            deadline=None, archive_ref=None, ledger_complete=False,
            usable_for_elimination=grade.usable_for_elimination))
    return tuple(reversed(rows)) if reverse else tuple(rows)


def _g12_chain(fx, history, period=EVAL_PERIOD):
    prev, streaks = history
    return _chain(fx, period, prev=prev, streaks=streaks, with_pools=True)


def test_g12_two_independent_reruns_have_identical_reproducibility_hash(fx, history):
    '''G-12（M31 1414 行 / R2 验收硬门槛）：同 manifest 两次独立复跑哈希精确相等。

    判据与手算（M25 [L1052]-[L1055] + [L1261]-[L1274] + [L1640]）：
      * payload = score_card 的 34 个核心列 + grade_ledger 的 5 个等级列 + weight_version_id；
        run_id 属 SCORE_CARD_NON_HASHED，grade_ledger 的 9 个人工列属
        GRADE_LEDGER_NON_HASHED -> **第二次复跑故意换 run_id**，哈希仍须逐字符相等
        （相等同时说明 run_id 没有混进 payload，见下一条测试的 payload 文本探针）。
      * rule 1（Decimal 先 q12）手算锚点：S-002 的 M_REV_MINOR = 9000/10000，
        actual_value 是 int 9000、target_value 是 int 10000（V-9 金额精确相等），
        attainment = _q(9/10) = 0.900000000000；两次复跑逐位相等，比率差 <= 1e-12。
      * rule 3（映射按键排序）/ rule 4（行按 [L1220] 业务主键排序）：第二次复跑把
        per_metric / per_dim 的插入序反接、两张表的行序整体反接 -> 哈希仍须相等。
      * 手算 score_card 行数 = 11：评价期 12 个 pair 去掉 G-09 的 BLOCK 载体 S-008
        （E2 同一口径差 3），与 Step 5 的行数一致。
      * 判别力（防「两次都算成空 payload 所以相等」）：内存里把 S-002 的 M_REV_MINOR
        实际值 +1（唯一一位变化）-> 哈希必须不同；换 weight_version_id 入参 -> 必须不同。
      * 综合分手算 0.30*0.900000000000 + 0.70*1.050000000000 = 1.005000000000。
    '''
    run_a = _g12_chain(fx, history)
    run_b = _g12_chain(fx, history)
    problems = []
    if run_a.pool_error is not None or run_b.pool_error is not None:
        problems.append('Step 7 抛错 -> score_card 的名次三列（ranking_pool / rank_in_pool /'
                        ' pool_size）无从取值。ORCH-28 R6 要求「已标注的 null」用'
                        ' reject_reason 承载、不中断 Step 7：'
                        + ' / '.join([str(run_a.pool_error), str(run_b.pool_error)]))

    rows_a = _score_card_rows(run_a, fx['weights'], 'SYNTH-RUN-E3-G12-A', EVAL_PERIOD)
    rows_b = _score_card_rows(run_b, fx['weights'], 'SYNTH-RUN-E3-G12-B', EVAL_PERIOD,
                              reverse=True)
    ledger_a = _ledger_rows(run_a, fx, EVAL_PERIOD)
    ledger_b = _ledger_rows(run_b, fx, EVAL_PERIOD, reverse=True)
    if (len(rows_a), len(rows_b)) != (11, 11):
        problems.append('score_card 行数：手算=11（12 个 pair 减 S-008）实测='
                        + str((len(rows_a), len(rows_b))))

    hash_a = audit.reproducibility_hash(rows_a, ledger_a, WEIGHT_VERSION_ID)
    hash_b = audit.reproducibility_hash(rows_b, ledger_b, WEIGHT_VERSION_ID)
    if hash_a != hash_b:
        problems.append('两次独立复跑的 reproducibility_hash 不逐字符相等（R2 硬门槛）：'
                        + str(hash_a) + ' vs ' + str(hash_b))
    if len(hash_a) != 64 or any(ch not in '0123456789abcdef' for ch in hash_a):
        problems.append('[L1055] 要求 64 位小写十六进制，实测 ' + repr(hash_a))

    cell_a = next(r.per_metric['M_REV_MINOR'] for r in rows_a if r.strategy_id == 'S-002')
    cell_b = next(r.per_metric['M_REV_MINOR'] for r in rows_b if r.strategy_id == 'S-002')
    if not (isinstance(cell_a.actual_value, int) and cell_a.actual_value == 9000):
        problems.append('金额列 V-9 手算：M_REV_MINOR 实际值应为 int 9000（T3 逐字），实测 '
                        + repr(cell_a.actual_value))
    if not (isinstance(cell_a.target_value, int) and cell_a.target_value == 10000):
        problems.append('金额列 V-9 手算：M_REV_MINOR 目标值应为 int 10000（T2 逐字），实测 '
                        + repr(cell_a.target_value))
    if (cell_a.actual_value, cell_a.target_value) != (cell_b.actual_value,
                                                      cell_b.target_value):
        problems.append('金额 / 整数字段两次复跑不精确相等：' + repr((cell_a, cell_b)))
    if not _ratio_eq(cell_a.attainment, _q(Decimal(9) / Decimal(10))):
        problems.append('达成率手算 9000/10000 = 0.900000000000，实测 '
                        + str(cell_a.attainment))
    if abs(cell_a.attainment - cell_b.attainment) > TOL:
        problems.append('比率字段两次复跑差值超 1e-12：' + str(cell_a.attainment) + ' vs '
                        + str(cell_b.attainment))
    score_a = next(r for r in rows_a if r.strategy_id == 'S-002')
    score_b = next(r for r in rows_b if r.strategy_id == 'S-002')
    if score_a.composite_absolute != score_b.composite_absolute:
        problems.append('综合分两次复跑不逐位相等：' + str(score_a.composite_absolute)
                        + ' vs ' + str(score_b.composite_absolute))
    if not _ratio_eq(score_a.composite_absolute, _q(Decimal('1.005000000000'))):
        problems.append('S-002 综合分手算 0.30*0.900000000000 + 0.70*1.050000000000 ='
                        ' 1.005000000000，实测 ' + str(score_a.composite_absolute))
    if score_a.run_id == score_b.run_id:
        problems.append('两次复跑的 run_id 必须不同（[L1091] 不许覆盖），实测同为 '
                        + str(score_a.run_id))

    bumped = _score_card_rows(run_a, fx['weights'], 'SYNTH-RUN-E3-G12-C', EVAL_PERIOD,
                              bump_money=True)
    hash_c = audit.reproducibility_hash(bumped, ledger_a, WEIGHT_VERSION_ID)
    if hash_c == hash_a:
        problems.append('改一位金额（9000 -> 9001）后哈希不变 -> payload 未覆盖金额列，'
                        '哈希无判别力：' + str(hash_c))
    hash_d = audit.reproducibility_hash(rows_a, ledger_a, 'WV-SYNTH-OTHER')
    if hash_d == hash_a:
        problems.append('换 weight_version_id 入参后哈希不变 -> INV-3 [L955] 的权重版本'
                        '没进 payload：' + str(hash_d))
    _diffs(problems)


def test_g12_canonical_text_rules_and_hash_field_coverage(fx, history):
    '''G-12 的规范化五规则与 V-11 列闭合（M25 [L1053] / [L1261]-[L1274] / ruling 32）。

    手算（每条都给出期望的字面序列化，来源是 M25 的规则原文，不是实现输出）：
      * rule 1（Decimal -> q12，1e-12 ROUND_HALF_UP）：
          0.9000000000004 -> n0.900000000000（第 13 位是 4，舍）
          0.9000000000005 -> n0.900000000001（第 13 位是 5，HALF_UP 入）
          0.9           -> n0.900000000000；9000 -> i9000（整数不带小数位，V-9）
      * rule 2（float 必须先过 numeric.from_float，不得直接 repr）：
          0.1 与 Decimal('0.1') 的规范文本相同 = n0.100000000000
      * rule 3（映射按键排序）：{a:1, b:2} 与 {b:2, a:1} 相同
      * rule 4（序列按规范文本排序 -> 插入序无关）：[1,2] 与 [2,1] 相同
      * rule 5（null 与空串是两种东西）：None -> null，'' -> empty，二者不相等
      * 未覆盖类型必须抛 AuditError（V-14：不静默用 str() 兜底）
      * V-11 / ruling 32：SCORE_CARD_HASH_FIELDS(34) 并 SCORE_CARD_NON_HASHED(1)
        == ScoreCardRow 的 35 列；GRADE_LEDGER_HASH_FIELDS(5) 并
        GRADE_LEDGER_NON_HASHED(9) == GradeLedgerRow 的 14 列（列名逐字，不重命名）
      * rule 4 的业务主键 = [L1220]-[L1221] 定位三元组
        (strategy_id, version_id, period)
    '''
    run = _g12_chain(fx, history)
    problems = []
    cases = ((Decimal('0.9000000000004'), 'n0.900000000000'),
             (Decimal('0.9000000000005'), 'n0.900000000001'),
             (Decimal('0.9'), 'n0.900000000000'),
             (9000, 'i9000'),
             (0.1, 'n0.100000000000'),
             (None, 'null'),
             ('', 'empty'))
    for value, want in cases:
        got = audit.canonical_text(value)
        if got != want:
            problems.append('canonical_text(' + repr(value) + ')：手算=' + repr(want)
                            + ' 实测=' + repr(got))
    if audit.canonical_text({'a': 1, 'b': 2}) != audit.canonical_text({'b': 2, 'a': 1}):
        problems.append('rule 3 失效：dict 键插入序影响了规范文本')
    if audit.canonical_text([1, 2]) != audit.canonical_text([2, 1]):
        problems.append('rule 4 失效：序列插入序影响了规范文本')
    if audit.canonical_text(None) == audit.canonical_text(''):
        problems.append('rule 5 失效：null 与空串被当成同一种东西')
    try:
        audit.canonical_text(object())
        problems.append('未覆盖类型没有抛 AuditError（V-14 禁静默 str() 兜底）')
    except audit.AuditError:
        pass

    score_fields = set(ScoreCardRow.model_fields)
    ledger_fields = set(GradeLedgerRow.model_fields)
    score_split = set(audit.SCORE_CARD_HASH_FIELDS) | set(audit.SCORE_CARD_NON_HASHED)
    if score_split != score_fields:
        problems.append('V-11：score_card 的哈希列 + 非哈希列 != ScoreCardRow 全列，缺 '
                        + str(sorted(score_fields - score_split)) + '，多 '
                        + str(sorted(score_split - score_fields)))
    if len(audit.SCORE_CARD_HASH_FIELDS) != 34 or audit.SCORE_CARD_NON_HASHED != ('run_id',):
        problems.append('M25 [L1052] 手算 = 35 列里 34 列入哈希、只有 run_id 不入；实测 '
                        + str(len(audit.SCORE_CARD_HASH_FIELDS)) + ' 列 + '
                        + str(audit.SCORE_CARD_NON_HASHED))
    ledger_split = set(audit.GRADE_LEDGER_HASH_FIELDS) | set(audit.GRADE_LEDGER_NON_HASHED)
    if ledger_split != ledger_fields:
        problems.append('V-11：grade_ledger 的哈希列 + 非哈希列 != GradeLedgerRow 全列，缺 '
                        + str(sorted(ledger_fields - ledger_split)) + '，多 '
                        + str(sorted(ledger_split - ledger_fields)))
    if len(audit.GRADE_LEDGER_HASH_FIELDS) != 5 or len(audit.GRADE_LEDGER_NON_HASHED) != 9:
        problems.append('M25 手算 = 14 列里 5 列（定位三元组 + grade + previous_grade）入哈希、'
                        '9 列人工列不入；实测 ' + str(len(audit.GRADE_LEDGER_HASH_FIELDS))
                        + ' + ' + str(len(audit.GRADE_LEDGER_NON_HASHED)))
    if audit.ROW_SORT_KEY != ('strategy_id', 'version_id', 'period'):
        problems.append('rule 4 的业务主键手算 = [L1220]-[L1221] 定位三元组，实测 '
                        + str(audit.ROW_SORT_KEY))

    rows = _score_card_rows(run, fx['weights'], 'SYNTH-RUN-E3-G12-D', EVAL_PERIOD)
    payload = audit.hash_payload(rows, _ledger_rows(run, fx, EVAL_PERIOD),
                                 WEIGHT_VERSION_ID)
    if 'SYNTH-RUN-E3-G12-D' in payload:
        problems.append('run_id 泄漏进 payload（SCORE_CARD_NON_HASHED 没被排除）')
    if WEIGHT_VERSION_ID not in payload:
        problems.append('weight_version_id 不在 payload 里（INV-3 [L955] 要求逐行留版本）')
    if 'NOT_ASSESSED' not in payload or 'L2' not in payload:
        problems.append('payload 里没有等级信息，哈希与定级无关：' + payload[:200])
    _diffs(problems)


# ==========================================================================
# G-14  一级库 C 类占比上升（M31 1416 行 / M37 E4 / M24 [L1000]-[L1006] / [L1854]）
# ==========================================================================
C_BASE_STEP3 = ('S-003/v1', 'S-006/v1', 'S-008/v1', 'S-011/v1')            # 不变（A1c 不影响 C 集合）
C_VARIANT_STEP3 = ('S-003/v1', 'S-005/v2', 'S-006/v1', 'S-007/v1',
                   'S-008/v1', 'S-011/v1')                                  # 不变
# 四类闭合：evidence 侧（DEN_EV = EVAL_PAIR_COUNT = 12）。A1c（D-A1-02）给 S-004 / S-005v1 /
# S-005v2 / S-007 补 [L1171] 的 alt_method_note -> [L977]③ 判 B；D 只剩 S-010/v1（① 卡缺失）
# 与 S-012/v1（⑤ C 未写 interpretation_limit）。改前 {A3,B0,C3,D5} 是绑定 A1c 之前 fixtures 的
# 陈旧手算值（R-14 允许按独立手算更新，不是照抄实现）。
STRUCTURE_STEP3_BASE = {'A': 3, 'B': 3, 'C': 4, 'D': 2}        # 闭合 12，与 SDD [L1459] 逐字一致
STRUCTURE_STEP3_VARIANT = {'A': 3, 'B': 1, 'C': 6, 'D': 2}     # S-005/v2、S-007/v1 由 B -> C
# 证据结构披露：pooling 侧（DEN_POOL = 11 = 12 - S-008）。ORCH-37 第6条读法甲：四类全给。
STRUCTURE_BASE = {'A': 3, 'B': 3, 'C': 3, 'D': 2}
STRUCTURE_VARIANT = {'A': 3, 'B': 1, 'C': 5, 'D': 2}
# 占比双报（[L1003]）：share_in_pool = 池内 / 同 biz_domain 已参评；share_overall = 池内 / 9。
# biz_domain 取值来源 fixtures/input/strategy_master.jsonl -> T1 逐字：
#   CARD={S-001,S-002,S-003} LOAN={S-004,S-005v1,S-005v2,S-006}
#   WEALTH={S-007,S-008,S-009} PAY={S-010,S-011,S-012}
# 基线各域已参评：CARD=3（S-001 A,S-002 A,S-003 C）LOAN=3（S-004 B,S-005v2 B,S-006 C）
#                 WEALTH=2（S-007 B,S-009 A；S-008 被 G-09 BLOCK 剔出 universe）PAY=1（S-011 C）
SHARES_BASE = {
    ('CARD', 'A'):   (2, Decimal(2) / Decimal(3), Decimal(2) / Decimal(DEN_ASSESSED)),
    ('CARD', 'C'):   (1, Decimal(1) / Decimal(3), Decimal(1) / Decimal(DEN_ASSESSED)),
    ('LOAN', 'B'):   (2, Decimal(2) / Decimal(3), Decimal(2) / Decimal(DEN_ASSESSED)),
    ('LOAN', 'C'):   (1, Decimal(1) / Decimal(3), Decimal(1) / Decimal(DEN_ASSESSED)),
    ('WEALTH', 'A'): (1, Decimal(1) / Decimal(2), Decimal(1) / Decimal(DEN_ASSESSED)),
    ('WEALTH', 'B'): (1, Decimal(1) / Decimal(2), Decimal(1) / Decimal(DEN_ASSESSED)),
    ('PAY', 'C'):    (1, Decimal(1),              Decimal(1) / Decimal(DEN_ASSESSED)),
}
# 变体：S-005/v2、S-007/v1 由 B -> C（[L977]④ 短路到 C，⑤ 因 interpretation_limit 已填不再降 D）。
# 各域已参评数不变（B->C 是同级搬运，都属已参评）：CARD=3 LOAN=3 WEALTH=2 PAY=1
SHARES_VARIANT = {
    ('CARD', 'A'):   (2, Decimal(2) / Decimal(3), Decimal(2) / Decimal(DEN_ASSESSED_VARIANT)),
    ('CARD', 'C'):   (1, Decimal(1) / Decimal(3), Decimal(1) / Decimal(DEN_ASSESSED_VARIANT)),
    ('LOAN', 'B'):   (1, Decimal(1) / Decimal(3), Decimal(1) / Decimal(DEN_ASSESSED_VARIANT)),
    ('LOAN', 'C'):   (2, Decimal(2) / Decimal(3), Decimal(2) / Decimal(DEN_ASSESSED_VARIANT)),
    ('WEALTH', 'A'): (1, Decimal(1) / Decimal(2), Decimal(1) / Decimal(DEN_ASSESSED_VARIANT)),
    ('WEALTH', 'C'): (1, Decimal(1) / Decimal(2), Decimal(1) / Decimal(DEN_ASSESSED_VARIANT)),
    ('PAY', 'C'):    (1, Decimal(1),              Decimal(1) / Decimal(DEN_ASSESSED_VARIANT)),
}
# SMALL_POOL（[L943]：池内样本数 < min_pool_size=2 -> WARN + 标注，不是抛错、不是把名次置 null）
SMALL_BASE = {('CARD', 'C'), ('LOAN', 'C'), ('WEALTH', 'A'), ('WEALTH', 'B'), ('PAY', 'C')}
SMALL_VARIANT = {('CARD', 'C'), ('LOAN', 'B'), ('WEALTH', 'A'), ('WEALTH', 'C'), ('PAY', 'C')}
# G-14 判据（ORCH-36 第1条：分子 = C 类计数，M31 [L1416] 唯一明文；「C+D」零原文依据已驳回，
# 以 dsm/reason_codes.py:86 的 message 为据属循环引证亦已驳回 —— ORCH-37 第7条）。
# 分母 = DEN_ASSESSED = 9（ORCH-36 第3条：与两列 share_* 同源 + [L1004] 剔 NOT_ASSESSED）。
C_SHARE_BASE = Decimal(STRUCTURE_BASE['C']) / Decimal(DEN_ASSESSED)                  # 3/9
C_SHARE_VARIANT = Decimal(STRUCTURE_VARIANT['C']) / Decimal(DEN_ASSESSED_VARIANT)    # 5/9
# 披露量（**不是**判据分子）：(C+D) / 四类合计 = / DEN_POOL（ORCH-37 第6条读法甲 + [L1003]）
LOW_EVIDENCE_BASE = Decimal(STRUCTURE_BASE['C'] + STRUCTURE_BASE['D']) / Decimal(DEN_POOL)           # 5/11
LOW_EVIDENCE_VARIANT = Decimal(STRUCTURE_VARIANT['C'] + STRUCTURE_VARIANT['D']) / Decimal(DEN_POOL)  # 7/11


def _step3_classes(fx, name=None):
    '''只用 Step 3（评价设计卡 + 事实行）判证据等级，不碰 Step 1 / 红线。

    手算输入 = 评价期 2026-Q3 有事实行的 12 个 strategy x version（逐字数自 T3）。
    '''
    cards = fx['cards'] if name is None else _variant_table(fx, 'design_card', name)
    live = tuple(r for r in fx['facts'] if r.period == EVAL_PERIOD)
    frame = evidence.classify(cards, live, params=EV_PARAMS)
    live_pairs = {(r.strategy_id, r.version_id) for r in live}
    return {(r.strategy_id + '/' + r.version_id): r for r in frame.rows
             if (r.strategy_id, r.version_id) in live_pairs}


def _pool_chain(fx, history, name=None):
    prev, streaks = history
    cards = fx['cards'] if name is None else _variant_table(fx, 'design_card', name)
    return _chain(fx, EVAL_PERIOD, cards=cards, prev=prev, streaks=streaks,
                  with_pools=True)


def _stats_map(stats):
    return {(r.pool_key.biz_domain, r.pool_key.evidence_class): r for r in stats.rows}


def test_g14_c_class_share_rises_from_four_of_twelve_to_six_of_twelve(fx):
    '''G-14 输入侧手算：C 类占比 4/12 -> 6/12（evidence 侧口径，DEN_EV = 12）。

    **分子/分母/C 集合常量一律不动**，只改四类闭合与 docstring：A1c（D-A1-02）把 S-004 /
    S-005v1 / S-005v2 / S-007 四张 DID 卡补上 [L1171] 的 alt_method_note -> [L977]③ 判 B，
    于是 B 由 0 变 3、D 由 5 变 2；但 C 集合 {S-003,S-006,S-008,S-011} 与变体新增的两条
    {S-005/v2, S-007/v1} **完全不受影响**（它们本来就在 C / 本来就被变体改成 C），
    故 4/12 -> 6/12 与 A1 golden_map 的 hand 仍然逐位一致。
    口径提示（ORCH-41 第2条 / ERRATUM-11）：本条用 **12**（evidence 侧出桥），**不得**换成
    pooling 侧的 11 / 9；11 只服务 evidence_structure 与 (C+D) 披露，9 只服务 c_class_share
    与两列 share_*。
    变体改判路径复核（NEED-FIXTURES 第6条）：A1c 后 S-005/v2、S-007/v1 在基线是 B，变体把
    control_arrangement 改 NONE + eval_method 改 OBSERVATIONAL_ONLY + 已填 interpretation_limit
    -> [L977] 第①步（无对照）短路到 C，即 **B -> C**（pre-A1c 时是 D -> C）。
    '''
    base_rows = _step3_classes(fx)
    variant_rows = _step3_classes(fx, 'G14_c_share_up')
    problems = []
    if len(base_rows) != EVAL_PAIR_COUNT:
        problems.append('评价期出桥 pair 数：手算=12（[L1459] A*3+B*3+C*4+D*2；EVID-1 按评价期'
                        ' 过滤使 13->12，ORCH-37 第9条）实测=' + str(len(base_rows)))
    got_c = sorted(k for k, r in base_rows.items() if r.evidence_class == 'C')
    if got_c != list(C_BASE_STEP3):
        problems.append('基线 C 类集合：手算=' + str(C_BASE_STEP3) + ' 实测=' + str(got_c))
    got_variant_c = sorted(k for k, r in variant_rows.items() if r.evidence_class == 'C')
    if got_variant_c != list(C_VARIANT_STEP3):
        problems.append('变体 C 类集合：手算=' + str(C_VARIANT_STEP3) + ' 实测='
                        + str(got_variant_c))
    if not _ratio_eq(_q(Decimal(len(got_c)) / Decimal(EVAL_PAIR_COUNT)),
                     _q(Decimal(4) / Decimal(12))):
        problems.append('基线 C 占比：手算 4/12 = 0.333333333333 实测 '
                        + str(_q(Decimal(len(got_c)) / Decimal(EVAL_PAIR_COUNT))))
    if not _ratio_eq(_q(Decimal(len(got_variant_c)) / Decimal(EVAL_PAIR_COUNT)),
                     _q(Decimal(6) / Decimal(12))):
        problems.append('变体 C 占比：手算 6/12 = 0.500000000000 实测 '
                        + str(_q(Decimal(len(got_variant_c)) / Decimal(EVAL_PAIR_COUNT))))
    counts, vcounts = {}, {}
    for row in base_rows.values():
        counts[row.evidence_class] = counts.get(row.evidence_class, 0) + 1
    for row in variant_rows.values():
        vcounts[row.evidence_class] = vcounts.get(row.evidence_class, 0) + 1
    if {k: counts.get(k, 0) for k in STRUCTURE_STEP3_BASE} != STRUCTURE_STEP3_BASE:
        problems.append('基线四类闭合：手算=' + str(STRUCTURE_STEP3_BASE) + '（SDD [L1459] 逐字'
                        ' A*3、B*3、C*4、D*2）实测='
                        + str({k: counts.get(k, 0) for k in STRUCTURE_STEP3_BASE}))
    if {k: vcounts.get(k, 0) for k in STRUCTURE_STEP3_VARIANT} != STRUCTURE_STEP3_VARIANT:
        problems.append('变体四类闭合：手算=' + str(STRUCTURE_STEP3_VARIANT)
                        + '（B->C 两条搬运，闭合仍 12）实测='
                        + str({k: vcounts.get(k, 0) for k in STRUCTURE_STEP3_VARIANT}))
    for key in ('S-005/v2', 'S-007/v1'):
        if base_rows[key].evidence_class == 'C':
            problems.append('变体的两条改判对象在基线里本应不是 C（A1c 后应为 B，[L977]③）：'
                            + key)
        if base_rows[key].evidence_class != 'B':
            problems.append('基线 ' + key + ' 手算=B（[L977]③ 准实验 DID + alt_method_note'
                            ' 非空，A1c D-A1-02 已补）实测='
                            + str(base_rows[key].evidence_class))
        if not variant_rows[key].interpretation_limit:
            problems.append('变体已填 interpretation_limit，改判为 C 后该列不得为空'
                            '（[L977] 第 5 步 / [L1618]）：' + key)
    _diffs(problems)


def test_g14_pool_shares_are_reported_in_two_columns_and_step7_is_not_aborted(fx, history):
    '''G-14 后半「池内占比与合并占比分列」+ ORCH-28 R6「Step 7 不中断」的手算。

    手算（分池维度 = [L1001] 业务领域（T1 逐字）x 证据等级（Step 3）；
      占比双报 = [L1003]-[L1004]，分母只含**已参评**（NOT_ASSESSED 单独计数，不入池、
      不占名次，rank 为 null 而不是 0），[L1006] 各池计数）：
      * 基线 universe = Step 5 的 11 行（12 减 G-09 BLOCK 载体 S-008）；
        已参评 = 6（S-001 S-002 S-003 S-006 S-009 S-011），NOT_ASSESSED = 5（证据 D）。
        证据结构（全部策略）= A3 B0 C3 D5，闭合 11。
        各池（count, share_in_pool = 池内 / 同领域已参评, share_overall = 池内 / 6）：
          CARD/A 2 -> 2/3 = 0.666666666667 与 2/6 = 0.333333333333（两列不相等 -> 分列可判）
          CARD/C 1 -> 1/3 = 0.333333333333 与 1/6 = 0.166666666667
          LOAN/C 1、WEALTH/A 1、PAY/C 1 -> 1.000000000000 与 1/6 = 0.166666666667
      * 变体 G14：已参评 = 8（S-005v2、S-007 由 D 转 C 后进入参评），证据结构 A3 B0 C5 D3；
          CARD/A 2 -> 0.666666666667 与 2/8 = 0.250000000000
          LOAN/C 2 -> 2/2 = 1.000000000000 与 0.250000000000
          WEALTH/A 1、WEALTH/C 1 -> 1/2 = 0.500000000000 与 1/8 = 0.125000000000
          CARD/C 1 -> 0.333333333333 与 1/8 = 0.125000000000；PAY/C 1 -> 1 与 0.125000000000
      * [L943]（ORCH-28：两条边界互相独立）：池内样本数 1 < min_pool_size=2 只应
        WARN + SMALL_POOL 标注，**不是抛错、不是把名次置 null** -> 手算 SMALL_POOL 池 =
        基线 4 个（CARD/C、LOAN/C、WEALTH/A、PAY/C）、变体 4 个（CARD/C、PAY/C、
        WEALTH/A、WEALTH/C），且这些池里已参评行的 pool_rank 必须仍为 1、
        reject_reason 必须为 None。
      * 名次不跨池（P-6）：每个池的非空 pool_rank 恰为 1..池内已参评数，
        不存在把两个池合成一个单一序的出口。
    ORCH-28 未落地时的偏差（保持 RED）：当前实现在单例池 / 不可比 null 上仍走抛错或
      置 null，Step 7 无法产出名次三列。归因：normalize x pooling 接缝（SEAM-1 在飞）。
    '''
    run = _pool_chain(fx, history)
    variant = _pool_chain(fx, history, 'G14_c_share_up')
    problems = []
    for name, chain in (('基线', run), ('变体', variant)):
        if chain.pool_error is not None:
            problems.append(name + ' Step 7 抛错（ORCH-28 R6：有标注的 null 用 reject_reason'
                            ' 承载、不中断 Step 7）：' + chain.pool_error)
    if problems:
        _diffs(problems)

    for name, chain, want_structure, want_shares, want_small, want_assessed, want_na in (
            ('基线', run, STRUCTURE_BASE, SHARES_BASE, SMALL_BASE, DEN_ASSESSED, NOT_ASSESSED_BASE),
            ('变体', variant, STRUCTURE_VARIANT, SHARES_VARIANT, SMALL_VARIANT, DEN_ASSESSED_VARIANT, NOT_ASSESSED_VARIANT)):
        if chain.stats is None:
            problems.append(name + '：stats 为 None，Step 7 没有产出')
            continue
        got_structure = {k: int(v) for k, v in (chain.stats.evidence_structure or {}).items()}
        if got_structure != want_structure:
            problems.append(name + ' 证据结构：手算=' + str(want_structure) + ' 实测='
                            + str(got_structure))
        if int(chain.stats.not_assessed_count) != want_na:
            problems.append(name + ' NOT_ASSESSED 计数：手算=' + str(want_na) + ' 实测='
                            + str(chain.stats.not_assessed_count))
        got_shares = _stats_map(chain.stats)
        if set(got_shares) != set(want_shares):
            problems.append(name + ' 池集合：手算=' + str(sorted(want_shares)) + ' 实测='
                            + str(sorted(got_shares)))
        for group, (count, in_pool, overall) in sorted(want_shares.items()):
            row = got_shares.get(group)
            if row is None:
                continue
            if int(row.count) != count:
                problems.append(name + ' ' + str(group) + ' count：手算=' + str(count)
                                + ' 实测=' + str(row.count))
            if not _ratio_eq(row.share_in_pool, _q(in_pool)):
                problems.append(name + ' ' + str(group) + ' share_in_pool：手算='
                                + str(_q(in_pool)) + '（池内 ' + str(count) + ' / 同领域已参评）'
                                ' 实测=' + str(row.share_in_pool))
            if not _ratio_eq(row.share_overall, _q(overall)):
                problems.append(name + ' ' + str(group) + ' share_overall：手算='
                                + str(_q(overall)) + '（池内 ' + str(count) + ' / 已参评 '
                                + str(want_assessed) + '）实测=' + str(row.share_overall))
            if in_pool != overall and _ratio_eq(row.share_in_pool, row.share_overall):
                problems.append(name + ' ' + str(group)
                                + ' 两列被算成同一个数（占比双报失效，P0-7）')
        got_small = {(_k.biz_domain, _k.evidence_class)
                     for _k in pooling.small_pools(chain.stats, POOL_PARAMS)}
        if got_small != want_small:
            problems.append(name + ' SMALL_POOL 池集（min_pool_size=2）：手算='
                            + str(sorted(want_small)) + ' 实测=' + str(sorted(got_small)))
        groups = pooling.groups(chain.pools)
        ranked = {}
        for group, rows in groups.items():
            ranks = sorted(r.pool_rank for r in rows if r.pool_rank is not None)
            if ranks != list(range(1, len(ranks) + 1)):
                problems.append(name + ' 池 ' + str(group) + ' 的名次不闭合 1..n（跨池合并'
                                '名次嫌疑）：' + str(ranks))
            ranked[group] = ranks
        for row in chain.pools.rows:
            group = (row.pool_key.biz_domain, row.pool_key.evidence_class)
            assessed_row = row.pool_rank is not None
            if not assessed_row:
                if row.reject_reason is None:
                    problems.append(name + ' ' + row.strategy_id
                                    + ' 无名次但 reject_reason 为 None（V-14：不可比必须留痕）')
            elif group in want_small and _code(row.reject_reason) == _code(RC.SMALL_POOL):
                problems.append(name + ' ' + str(group) + ' 是 SMALL_POOL，按 [L943] 只应'
                                ' WARN + 标注，不得当作拒绝理由：实测 reject_reason='
                                + str(row.reject_reason))
    _diffs(problems)


def test_g14_mix_quality_degraded_warning_fires_when_c_share_rises(fx, history):
    '''G-14 判据：C 类占比上升 -> MIX_QUALITY_DEGRADED（ORCH-36 第1/3/4条 + ORCH-37 第7条）。

    原文依据（逐字）：
      * M31 [L1416]「构造一级库中 **C 类占比**上升的场景」->「报告出现 MIX_QUALITY_DEGRADED
        警示」= **分子的唯一明文**。「一级库中」这个限定语记 ERRATUM-04（[L1002] / [L137] /
        [L1436] 明文 C 类不得进一级库，一级库内 C 恒 0，字面不可满足），不据其字面实现。
        「C+D」零原文依据已驳回；以 dsm/reason_codes.py:86 的 message 为据属**循环引证**亦已
        驳回（ORCH-37 第7条）。
      * M24 [L1004]「NOT_ASSESSED 单独计数，**不计入分母**」+ ORCH-36 第3条「分母必须与两列
        share_* 同源」-> 判据分母 = DEN_ASSESSED = DEN_POOL - not_assessed_count = 11 - 2 = **9**。
        分母的正向定义原文缺位 = ERRATUM-05，依据等级 derived:。
      * M24 [L1003]「同时报池内占比与合并占比，并披露各池的证据结构（A/B/C/D 计数）」+
        M30 [L1063] 第⑥段「证据结构（A/B/C/D 计数与 NOT_ASSESSED 明细）」-> 披露口径分母 =
        **11**（ORCH-37 第6条读法甲）。**11 用于披露、9 用于判据、12 用于 Step-3，不得混用**
        （ORCH-41 第2条 / ERRATUM-11）。
      * M45 [L1854]「占比双报 + MIX_QUALITY_DEGRADED 防作弊」只给目的，不给分子/分母。
    独立手算（先算后测；探针 dsm_stage/E3b/probe_sens.py，只用 fixtures 的 T2/T3/T4/T7 与
    [L977] 五步判级，不 import 任何 dsm 业务模块，R-14 合规）：
      * 基线 pooling 侧结构 A3 B3 C3 D2 = 11，NOT_ASSESSED = 2（S-010/v1 卡缺失、S-012/v1
        C 未写 interpretation_limit -> [L977]① / ⑤ 降 D -> M05 [L494] D = NOT_ASSESSED）
        -> 已参评 9 -> C 占比 = q12(3/9) = 0.333333333333
      * 变体（S-005/v2、S-007/v1 由 B -> C）-> A3 B1 C5 D2 = 11 -> C 占比 = q12(5/9)
        = 0.555555555556
      * 上升量 = 2/9 = 0.222222222222 > numeric.TOL(1E-12) -> 必出 MIX_QUALITY_DEGRADED
      * 对照披露量 (C+D)/DEN_POOL：基线 5/11 = 0.454545454545、变体 7/11 = 0.636363636364
        （改前的 8/11 是绑定 A1c 之前 fixtures 的陈旧手算值，其 docstring 自述「A1c 执行后需
        重新手算（E3b）」）—— 它**不是**判据分子：拿 C+D 度量 C 上升，在 D->C 搬运下恒定不变，
        守护点 vacuous，违 V-14（ORCH-36 第1条）；此处只做披露对账。
    阈值：numeric.TOL（1E-12）= **工程默认，非业务签认值**，语义「任何上升都警示」。
      PLACEHOLDER：原文未给数字、不在 config、不属 K-01~K-20（[L1734]-[L1757] 已逐条核过）
      -> 新立 **K-21**（ORCH-36 第4条），本包**不自拟单值**（R-12），5 条待签认项见
      dsm_stage/G14FIX/K-21-PROPOSAL.md。
    K-23（G14FIX 上报的数据巧合）：当前 NA 中 C 类 = 0，使分子（全体口径 evidence_structure）
      与分母（已参评口径）的 population 巧合一致 —— **这是数据巧合、非契约保证**，故本条把
      分母写成**关系式**（== Σevidence_structure - not_assessed_count）而不是只钉常量 9。
    V-14：基线缺失 = 不可比 -> 必抛；已参评数为 0 时商无定义 -> 必抛，**不得返回 0**。
    GAP-06（ORCH-36 第5条）：G14FIX 已把 mix_quality_verdict 接进 dsm/reports.py:419
      （_section_6，[L1063]⑥）；**cli 侧接线在 P2-wire-A**，不属 golden_b 写集，见
      dsm_stage/E3b/NEED-WIRING 上报（本条只断言 verdict 值）。
    '''
    run = _pool_chain(fx, history)
    variant = _pool_chain(fx, history, 'G14_c_share_up')
    problems = []
    if run.pool_error is not None or variant.pool_error is not None:
        problems.append('Step 7 未产出 PoolStats（ORCH-28 R6 要求不中断）：'
                        + ' / '.join([str(run.pool_error), str(variant.pool_error)]))
        _diffs(problems)
    for name, chain, want_structure, want_na in (
            ('基线', run, STRUCTURE_BASE, NOT_ASSESSED_BASE),
            ('变体', variant, STRUCTURE_VARIANT, NOT_ASSESSED_VARIANT)):
        got = {k: int(v) for k, v in (chain.stats.evidence_structure or {}).items()}
        if got != want_structure:
            problems.append(name + ' 证据结构（DEN_POOL=' + str(DEN_POOL) + ' 口径，ORCH-37'
                            ' 第6条读法甲：四类全给）：手算=' + str(want_structure)
                            + ' 实测=' + str(got))
        if sum(int(v) for v in got.values()) != DEN_POOL:
            problems.append(name + ' 四类合计：手算=' + str(DEN_POOL) + ' 实测='
                            + str(sum(int(v) for v in got.values())))
        if int(chain.stats.not_assessed_count) != want_na:
            problems.append(name + ' NOT_ASSESSED 计数（[L1004] 单独计数）：手算=' + str(want_na)
                            + ' 实测=' + str(chain.stats.not_assessed_count))
        # K-23 关系式（不钉常量）：判据分母 == 四类合计 - NOT_ASSESSED，且 == 手算的 9。
        if pooling.assessed_denominator(chain.stats) != \
                sum(int(v) for v in got.values()) - int(chain.stats.not_assessed_count):
            problems.append(name + ' 分母关系式不成立（[L1004] + ORCH-36 第3条：与 share_*'
                            ' 同源）：assessed_denominator='
                            + str(pooling.assessed_denominator(chain.stats))
                            + ' Σevidence_structure - not_assessed_count='
                            + str(sum(int(v) for v in got.values())
                                  - int(chain.stats.not_assessed_count)))
        want_den = DEN_ASSESSED if name == '基线' else DEN_ASSESSED_VARIANT
        if pooling.assessed_denominator(chain.stats) != want_den:
            problems.append(name + ' 判据分母：手算=' + str(want_den) + '（= 11 - 2）实测='
                            + str(pooling.assessed_denominator(chain.stats)))
    c_now = pooling.c_class_share(variant.stats)
    c_before = pooling.c_class_share(run.stats)
    if not _ratio_eq(c_before, _q(C_SHARE_BASE)):
        problems.append('基线 C 占比：手算 ' + str(STRUCTURE_BASE['C']) + '/' + str(DEN_ASSESSED)
                        + ' = 0.333333333333 实测 ' + str(c_before))
    if not _ratio_eq(c_now, _q(C_SHARE_VARIANT)):
        problems.append('变体 C 占比：手算 ' + str(STRUCTURE_VARIANT['C']) + '/'
                        + str(DEN_ASSESSED_VARIANT) + ' = 0.555555555556 实测 ' + str(c_now))
    if c_now is None or c_before is None or not c_now > c_before:
        problems.append('变体的 C 占比没有上升，与手算矛盾：' + str(c_now) + ' vs ' + str(c_before))
    elif not _ratio_eq(c_now - c_before, _q(C_SHARE_VARIANT) - _q(C_SHARE_BASE)):
        problems.append('上升量：手算 q12(5/9) - q12(3/9) = 0.555555555556 - 0.333333333333'
                        ' = 0.222222222223（两个已按 M16 q12 定标的占比相减，末位 +1e-12 属'
                        ' q12 口径的必然结果，非 2/9 的无穷小数截断；仍 > numeric.TOL）实测 '
                        + str(c_now - c_before))
    if not _ratio_eq(pooling.low_evidence_share(run.stats), _q(LOW_EVIDENCE_BASE)):
        problems.append('基线 (C+D) 披露量：手算 5/11 = 0.454545454545 实测 '
                        + str(pooling.low_evidence_share(run.stats)))
    if not _ratio_eq(pooling.low_evidence_share(variant.stats), _q(LOW_EVIDENCE_VARIANT)):
        problems.append('变体 (C+D) 披露量：手算 7/11 = 0.636363636364 实测 '
                        + str(pooling.low_evidence_share(variant.stats)))
    verdict = pooling.mix_quality_verdict(variant.stats, run.stats)
    if _code(verdict) != _code(RC.MIX_QUALITY_DEGRADED):
        problems.append('M31 [L1416] 判据：C 类占比由 3/9 = 0.333333333333 升到'
                        ' 5/9 = 0.555555555556（+2/9 = 0.222222222222 > numeric.TOL）-> 应出'
                        ' MIX_QUALITY_DEGRADED；实测 verdict=' + str(verdict))
    elif not reason_codes.is_registered(_code(verdict)):
        problems.append('verdict 码未注册（H-7）：' + str(verdict))
    try:
        pooling.mix_quality_verdict(variant.stats, None)
        problems.append('无上期基线却返回了值（V-14：不可比不得当作没上升）')
    except pooling.PoolingInputError:
        pass
    empty = PoolStats(rows=(), evidence_structure={'A': 0, 'B': 0, 'C': 0, 'D': 0},
                      not_assessed_count=0, not_assessed_reasons={})
    try:
        pooling.mix_quality_verdict(empty, empty)
        problems.append('已参评数为 0 时商无定义却返回了值（V-14：不得返回 0）')
    except pooling.PoolingInputError:
        pass
    _diffs(problems)
