'''tests/test_config_soft_deductions.py -- CFG-1（ORCH-61）：契约 L484 的 SOFT
扣减幅度是 config/grade_rules.yaml 的**顶层**键，不是 GradeRuleRow 的行字段。

期望值出处（R-14：绝不把实现输出抄成期望值）：
  * 契约《开发设计文档-策略评价可辩护评分模型DSM-v1.1.md》L484「SOFT 红线：命中 →
    独立扣减（在等级判定之外单列），**不进加权**……扣减幅度由 grade_rules.yaml
    配置」（该文件 sha256 前 12 位 708679e9a83d / 2003 行 / 177646 B，只读），
    以及同一张红线表 L990 的 SOFT 行；
  * tests/test_integration_spine.py:84 逐字
        GOVERNANCE['soft_deductions'] = {'M_OPTOUT_RATE': D('0.05')}
    ⇒ 键名 soft_deductions、唯一 metric_id M_OPTOUT_RATE、唯一数值 0.05；
  * config/redlines.yaml:27-31：演练 config 里 level: SOFT 的红线恰为一条
    M_OPTOUT_RATE（reason_code REDLINE_SOFT_M_OPTOUT_RATE），所以扣减比率的键集
    恰好覆盖它；再多一个键就是无出处的编造（R-12）。

标注纪律（与 config/grade_rules.yaml 文件头同一口径）：该键取值是**合成待签认
（DRILL ONLY）**，非行方签认治理值（F-2）；本文件任何断言都不宣称 G7 已签认。

本文件不改动任何既有断言（R-14），只新增。
'''
import shutil
from decimal import Decimal
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from dsm import config as cfgmod
from dsm import numeric, redline
from dsm.models import GradeRuleRow

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = REPO_ROOT / 'config'

# 契约 L484 指定的载体键名；ORCH-61 裁定它落在 grade_rules.yaml 顶层。
SOFT_KEY = 'soft_deductions'
# 逐字来自 tests/test_integration_spine.py:84（D = Decimal），不是实现输出（R-14）。
EXPECTED_SOFT = {'M_OPTOUT_RATE': Decimal('0.05')}
EXPECTED_METRIC_IDS = ('M_OPTOUT_RATE',)


def _load():
    '''仓库自带 config/ 的真实加载入口（dsm/config.py:449 load_all）。'''
    return cfgmod.load_all(CONFIG_DIR)


def _as_ratios(block):
    '''与消费点同形的定点化：dsm/cli.py:456 _soft_deductions 逐字读出后交给
    dsm/numeric.py 的 D()，dsm/redline.py:249 再过 q12。这里只做 D()，好让
    「YAML 里写的是字符串」这件事在断言里看得见。'''
    return dict((str(key), numeric.D(block[key])) for key in sorted(block, key=str))


def _copy_config_without_soft_key(tmp_path):
    '''一份去掉 soft_deductions 的临时 grade_rules 树（其余五份 yaml 原样）。'''
    dest = tmp_path / 'config'
    shutil.copytree(CONFIG_DIR, dest)
    path = dest / 'grade_rules.yaml'
    tree = yaml.safe_load(path.read_text(encoding='utf-8'))
    del tree[SOFT_KEY]
    path.write_text(yaml.safe_dump(tree, allow_unicode=True, sort_keys=False),
                    encoding='utf-8', newline='\n')
    return dest


# --------------------------------------------------------------------- #
# 1. 顶层键在场，键集与数值精确等于 spine:84                             #
# --------------------------------------------------------------------- #

def test_repo_grade_rules_carries_soft_deductions_as_a_top_level_key():
    app = _load()
    assert isinstance(app, cfgmod.AppConfig)
    # 顶层：与 grades / policy 平级的兄弟键（不是嵌套在某一行里）。
    assert SOFT_KEY in app.grade_rules, \
        '契约 L484 的扣减幅度载体缺失：grade_rules.yaml 顶层没有 ' + SOFT_KEY
    assert 'grades' in app.grade_rules and 'policy' in app.grade_rules, \
        '前置条件：grades / policy 两个既有顶层键仍在，soft_deductions 是其兄弟'
    block = app.grade_rules[SOFT_KEY]
    assert isinstance(block, dict) and block, 'L484 语义是 metric_id -> 比率 的映射'
    # 键集精确相等：多一个（无出处 = 编造，R-12）或少一个都红。
    assert tuple(sorted(block)) == EXPECTED_METRIC_IDS
    assert len(block) == len(EXPECTED_METRIC_IDS) == 1
    assert _as_ratios(block) == EXPECTED_SOFT


def test_the_ratio_is_written_as_a_string_like_attainment_floor_never_a_float():
    '''H-4：比率走 q12 定点，YAML 里写字符串（与同文件 attainment_floor: "1.00"
    同风格）；裸浮点会让 yaml 交出 float，numeric.D 直接 FloatNotAllowedError。'''
    block = _load().grade_rules[SOFT_KEY]
    leaf = block['M_OPTOUT_RATE']
    assert isinstance(leaf, str), '实得 ' + type(leaf).__name__ + '，应为字符串写法'
    assert not isinstance(leaf, float)
    assert leaf == '0.05', '逐字取 tests/test_integration_spine.py:84 的 D(\'0.05\')'
    with pytest.raises(numeric.FloatNotAllowedError):
        numeric.D(float(leaf))


# --------------------------------------------------------------------- #
# 2. 顶层键 vs 行字段：models 层 extra=forbid 反向钉                      #
# --------------------------------------------------------------------- #

def test_soft_deductions_is_not_a_grade_rule_row_field():
    app = _load()
    rows = app.grade_rules['grades']
    assert [row['grade_code'] for row in rows] == ['L1', 'L2', 'L3', 'L4'], \
        '前置条件：四级定级规则未被本包动过'
    assert all(SOFT_KEY not in row for row in rows), \
        SOFT_KEY + ' 是 grades 的兄弟顶层键，不得出现在任何一行定级规则里'
    # dsm/models.py:557 GradeRuleRow（frozen + extra=forbid）反向钉死这一点：
    # 往某一行塞 soft_deductions 必须抛错，而不是被静默丢掉。
    polluted = dict(rows[0])
    polluted[SOFT_KEY] = {'M_OPTOUT_RATE': '0.05'}
    with pytest.raises(ValidationError) as excinfo:
        GradeRuleRow(**polluted)
    text = str(excinfo.value)
    assert SOFT_KEY in text and 'extra_forbidden' in text, \
        'GradeRuleRow 未按 extra=forbid 拒绝该键：' + text
    # 未被污染的原行仍然构造得起来（证明上面的红确实来自新增键）。
    assert GradeRuleRow(**rows[0]).grade_code == rows[0]['grade_code']


# --------------------------------------------------------------------- #
# 3. q12 定点不丢精度；0..1 之外的值必须被拒绝，不得静默截断              #
# --------------------------------------------------------------------- #

def test_the_ratio_survives_q12_and_out_of_range_values_are_refused():
    block = _load().grade_rules[SOFT_KEY]
    value = numeric.q12(numeric.D(block['M_OPTOUT_RATE']))
    # 不丢精度：q12 定点后仍逐字等于 spine:84 的 D('0.05')。
    assert value == Decimal('0.050000000000')
    assert value == Decimal('0.05')
    assert value.as_tuple().exponent == -12, '应落在 q12 定点标度上'
    assert numeric.ZERO <= value <= numeric.ONE, 'L484 的扣减比率语义是 0..1'
    # 同一个值过消费点的 0..1 闸门必须是放行的（dsm/redline.py:243-249）。
    assert redline._deduction('M_OPTOUT_RATE', block) == value
    # 非数值字面量：numeric 层拒绝，不静默变 0。
    with pytest.raises(numeric.NumericError):
        numeric.D('abc')
    # 越界值：q12 不得把它悄悄截断成 1（那就是静默降级，V-14 禁止），
    # 而 0..1 闸门在消费点必须是关的。
    assert numeric.q12(numeric.D('1.5')) == Decimal('1.500000000000')
    with pytest.raises(redline.RedlineInputError):
        redline._deduction('M_OPTOUT_RATE', {'M_OPTOUT_RATE': '1.5'})
    with pytest.raises(redline.RedlineInputError):
        redline._deduction('M_OPTOUT_RATE', {'M_OPTOUT_RATE': '-0.05'})
    # 缺失即抛错（ADJ-2 / H-5：绝不自定数）。
    with pytest.raises(redline.RedlineInputError):
        redline._deduction('M_NOT_CONFIGURED', block)


def test_the_key_set_covers_exactly_the_soft_redlines_of_the_drill_config():
    '''config/redlines.yaml 里 level: SOFT 的红线，每一条都必须在这里有扣减比率
    （否则 Step4 必抛缺失），且不得有多出来的无出处键（R-12）。'''
    app = _load()
    soft_ids = tuple(sorted(
        row['metric_id'] for row in app.redlines['redlines']
        if row['level'] == 'SOFT'))
    assert soft_ids == EXPECTED_METRIC_IDS, \
        '演练 config 的 SOFT 红线集合与预期不符，本断言的出处需重新核对'
    assert tuple(sorted(app.grade_rules[SOFT_KEY])) == soft_ids
    for metric_id in soft_ids:
        assert redline._deduction(metric_id, app.grade_rules[SOFT_KEY]) == \
            EXPECTED_SOFT[metric_id]


# --------------------------------------------------------------------- #
# 4. 键缺失时的真实行为：明确缺席，绝不静默补 0                           #
# --------------------------------------------------------------------- #

def test_a_grade_rules_tree_without_the_key_reports_a_clear_absence(tmp_path):
    '''实测口径：dsm/config.py 的语义闸门（[L879]）只管权重求和、四级 floor 严格
    递减、actions 非空，**没有**为 soft_deductions 设必填校验，所以缺键时 load_all
    仍然成功，配置层给出的是「明确缺席」——不是 None、不是空映射、更不是 0。
    M29-1 的 shell 侧对此走 [L1080] 退出码 3 点名键位（dsm/cli.py:456
    _soft_deductions：缺块即 CliError(EXIT_CONFIG=3)），绝不自定数（H-5）。
    本断言的对象是配置层的真实行为，不把 shell 的退出码抄进来（cli.py 是
    M29-1 的单写者文件，本包禁写）。'''
    directory = _copy_config_without_soft_key(tmp_path)
    app = cfgmod.load_all(directory)
    assert SOFT_KEY not in app.grade_rules, '删掉的键不该自己回来'
    assert app.grade_rules.get(SOFT_KEY) is None, '缺席必须是 None，不得是 {} 或 0'
    with pytest.raises(KeyError):
        app.grade_rules[SOFT_KEY]
    # 其余顶层键与四级规则不受影响：缺的是这一个键，不是整棵树。
    assert sorted(app.grade_rules) == ['grades', 'policy']
    assert [row['grade_code'] for row in app.grade_rules['grades']] == \
        ['L1', 'L2', 'L3', 'L4']
    # 对照：仓库自带的 config/ 有这个键（本包补上的那一个）。
    assert SOFT_KEY in _load().grade_rules
