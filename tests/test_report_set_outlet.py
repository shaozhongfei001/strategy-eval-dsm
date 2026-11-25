'''M29-2 / ORCH-59：audit.json 自指纹循环的「两遍渲染六键口径」生产出口守护。

期望值来源纪律（R-14）：本文件每一条期望值都来自**契约原文或主控裁决 ORCH-59**，
没有一条是把实现输出抄成期望；凡涉及业务数值一律由仓库既有载体（冻结 fixtures +
演练 config）派生，本文件不拟定任何数（R-12）。

钉住的事实：
1. 契约 §3.15.1（[L1325]-[L1358]）的次序是 Step9 `audit.build_manifest` ->
   `reports.render` -> [L1062] 七件产物（**含 audit.json**）。而 audit.json 的正文就是
   AuditBundle 的 canonical 序列化（dsm/reports.py:738 render_audit_json ->
   dsm/audit.py:276 serialize_bundle），所以 [L1046]「AuditBundle 内容含输出文件清单与
   SHA256」在字面上自指：audit.json **不可能**含自身终值的哈希（已登记 ERRATUM-V12-07 /
   NG-V12-20）。
2. 主控预裁决 ORCH-59 = 两遍渲染变体 (i-b)，六键口径：
     bundle0 = build_manifest(inputs_fp, config, run_ctx, {}) -> rs0 = render(bundle0, ...)
     fps6    = rs0 的 **6 件非 audit.json** 产物、按 write_report_set 完全相同的编码算 SHA256
     bundle1 = build_manifest(inputs_fp, config, run_ctx, fps6) -> rs1 = render(bundle1, ...)
     不变式  = rs0 与 rs1 的六件非 audit.json 产物**逐字节相等**（回填不自相矛盾）
     出口    = write_report_set(rs1, out_dir) **只写一次** 7 件；bundle1.output_fingerprints
               键集 == ARTIFACT_NAMES - {audit.json} == 6；audit.json 自身的 SHA256 只由
               write_report_set 的返回值 / CLI details 通道对外披露，**不进 audit.json 内部**。
3. ①逐值重算的理由：dsm/audit.py:162 `check_sha256` **只校验格式**（长度 64 + 全小写
   十六进制），假指纹 `'0'*64` 会被它照单全收 —— 格式校验**不等于**真对账。故本文件对
   bundle 里每一枚指纹都用 `hashlib.sha256` 对**落盘文件的字节**重算并逐值全等
   （[L1640] 步骤一「第二个人重跑后逐个校验 SHA256」的可核验性只能这么保证）。
4. ④BLOCK / 失败路的既有口径**原样保留、禁弱化**：`output_fingerprints == {}` 与「只写
   audit_bundle 一个文件」已由 tests/test_preflight.py:399/430、
   tests/test_integration_spine.py:523、tests/test_golden_b.py:1333 在 preflight 层钉死；
   本文件在 **CLI 层**以同等强度再钉一遍（BLOCK 时 build_manifest / render /
   write_report_set 一次都不跑，七件产物一件都不落盘）。两遍渲染只挂在成功路上。
5. ⑤G-8 关闭判据：CLI 实跑一条 WARN 不阻断的路径，report.md 的⑥段（[L1063]）出现
   `MIX_QUALITY_DEGRADED` 警示行，且退出码**不因该 WARN 改变**。出码点 dsm/pooling.py:305
   （判据 `mix_quality_verdict` 在 :284），注册 dsm/reason_codes.py:97（severity=WARN、
   不在 `_BLOCKS_RUN`），MD 渲染位 dsm/reports.py:482-512（`_mix_quality_lines` -> ⑥段）。
   「C 类占比上升」的构造参照 tests/test_golden_b.py:2024+ 的 3/9 -> 5/9（[L1416] 的分子
   唯一明文 = C 类占比）：把上期基线的 C 计数减一、A 计数加一（分母 = Σ四类 - NA 不变），
   于是 c_class_share(上期) < c_class_share(本期)，上升量 > numeric.TOL(1E-12) -> 必出码。
   基线的**载体**走 dsm/cli.py:_report_frames 明文的注入口（该函数 docstring：「已注入的
   同名产物一律不被覆盖」= P2-wire seam）；真实数据面的上期基线至今缺位（io_loaders.Inputs
   没有 previous_pool_stats 字段、[L1051] 十六列里没有 pool_stats 列），那是 GAP，不是本
   文件造出来的。基线的**数值**由当期 PoolStats 派生，本文件不拟定业务数（R-12）。
6. NG-V12-21（v1.1 遗留偏差，主控裁本 RUN 不修）：`render_audit_json` 产出的是
   canonical_text（形如 `obj:AuditBundle{s:...}`），**不是合法 JSON**（[L1225] 要求 JSON）。
   故本文件对成功路的 audit.json **不做 json.loads**，只按 canonical text 读它（判据唯一性，
   与 tests/test_reports.py:325 / tests/test_cli_marshal.py 同一读法）。BLOCK 路那一份由
   dsm/preflight.py 自己写成真 JSON，故那一条按 json.loads 读（与既有测试同口径）。
7. run_id 末段每次运行不同（[L1091] 一次运行一个目录），report.md / score_card.csv 的字节
   **跨运行不可复现**，所以两遍渲染的逐字节比较一律在**同一次运行内**做（同 run_id）。

数据与装置：复用 tests/test_cli_marshal.py 的 staged-data（冻结 fixtures
fixtures/input/*.jsonl + 仓库自带演练 config/*.yaml + [L484] soft_deductions 载体），
triangulation 置为 dsm/triangulation.py:66-73 自认的合法签面值 false（旁路不入分，
[L1348]，veto() 落 TRIANGULATION_DISABLED 披露），L5 旁路换成同形状空载体 —— 因为两个
**写集外**缺陷（B12-FIX 正在并行修）会让真跑退出码 5：dsm/diagnostics.py:223 `_pearson`
在钱款列上 decimal.InvalidOperation、dsm/triangulation.py:293 `dimensionless` 在恒定列上
TriangulationError。两个旁路都明文「不入分」（[L1336] / [L1348]），换掉它们不影响
Step1-9 的任何一格数值，也不影响本文件钉的产物面口径。
'''
import hashlib
import json
import pathlib
import re

import dsm.audit as audit
import dsm.cli as cli
import dsm.reports as reports
import test_cli_marshal as marshal
from dsm import numeric, pooling, reason_codes
from dsm.reason_codes import RC

REPO = pathlib.Path(__file__).resolve().parents[1]
# [L1062] 七件产物里唯一「正文即 bundle 的 canonical 序列化」的那件：它的自指纹不可能
# 进它自己的正文（ORCH-59），故 output_fingerprints 的键集恒为 SEVEN - {AUDIT_ARTIFACT}。
AUDIT_ARTIFACT = 'audit.json'
FAILURE_BUNDLE = 'audit_bundle.json'      # [L1091] 失败路唯一的产物（dsm/cli.py:_write_failure_bundle）
SEVEN = reports.ARTIFACT_NAMES            # 口径唯一：文件名清单只从 reports 取，本文件不另列
SIX = tuple(name for name in SEVEN if name != AUDIT_ARTIFACT)     # ORCH-59 六键
SECTION_1 = reports.REPORT_SECTIONS[0]    # [L1063] ①首屏结论与可用性声明
SECTION_6 = reports.REPORT_SECTIONS[5]    # [L1063] ⑥证据结构（G-14 与本判据同段披露）
DEGRADED = RC.MIX_QUALITY_DEGRADED        # dsm/reason_codes.py:97（WARN / 不在 _BLOCKS_RUN）
DEGRADED_MESSAGE = reason_codes.message(DEGRADED)   # 注册表里的 message 文本（判据已触发的标识）
# 记录器一律从**模块导入时的真实现**包起，绝不让两次 _score 的记录器互相套娃
# （同一个测试里要跑对照 + 实验两次实跑）。
_REAL_BUILD = audit.build_manifest
_REAL_RENDER = reports.render
_REAL_WRITE = reports.write_report_set
_REAL_EMIT = cli._emit
_REAL_FRAMES = cli._report_frames


class _Outcome:
    '''一次 `dsm score` 实跑的可断言面：退出码、产物目录、三个生产入口的调用记录、
    CLI 的披露面（details）。'''

    def __init__(self, code, out, run_dir, seen):
        self.code = code
        self.out = out
        self.run_dir = run_dir
        self.seen = seen

    @property
    def bundles(self):
        return self.seen['bundles']

    @property
    def sets(self):
        return self.seen['sets']

    @property
    def writes(self):
        return self.seen['writes']

    @property
    def details(self):
        return self.seen['details'][-1] if self.seen['details'] else []

    @property
    def bundle(self):
        '''落盘那份 audit.json 的母本 = 第二遍的 bundle1（ORCH-59 第 3 条）。'''
        assert self.bundles, 'build_manifest 一次都没跑：成功路必须两遍装配（ORCH-59）'
        return self.bundles[-1]

    def landed(self):
        '''本次运行目录里的文件名（[L1091] 的最深一层）。'''
        if self.run_dir is None:
            return []
        return sorted(p.name for p in self.run_dir.iterdir() if p.is_file())

    def every_landed_name(self):
        '''--out 之下所有落盘文件的文件名（跨 <period>/<run_id> 层级）。'''
        if not self.out.exists():
            return []
        return sorted(p.name for p in self.out.rglob('*') if p.is_file())

    def bytes_of(self, name):
        return (self.run_dir / name).read_bytes()

    def text_of(self, name):
        return self.bytes_of(name).decode('utf-8')

    def section(self, title):
        blocks = reports.split_sections(self.text_of('report.md'))
        assert title in blocks, '[L1063] 十段结构里没有 ' + title
        return blocks[title]

    def find(self, name):
        hits = [p for p in self.out.rglob(name)] if self.out.exists() else []
        assert len(hits) == 1, '期望恰好一个 ' + name + '，实测 ' + str(hits)
        return hits[0]


def _capture(monkeypatch, *, second_render=None, previous_pool_stats=None):
    '''把三个生产入口（audit.build_manifest / reports.render / reports.write_report_set）
    与 CLI 的披露面包一层记录器：**转调真实实现**，只记调用次序、入参与返回值，行为一字不改。

    second_render      只给 INV-A 守护测试用：把**第二遍**的 ReportSet 换成一个「内嵌了
                       output_fingerprints」的变体，看 shell 是否按裁决停手。
    previous_pool_stats G-8 的上期基线工厂：收当期 PoolStats，返回上期 PoolStats。
    '''
    seen = {'bundles': [], 'sets': [], 'writes': [], 'details': [], 'g14': []}

    def build(*args, **kwargs):
        bundle = _REAL_BUILD(*args, **kwargs)
        seen['bundles'].append(bundle)
        return bundle
    monkeypatch.setattr(audit, 'build_manifest', build)

    calls = {'render': 0}

    def render(*args, **kwargs):
        report_set = _REAL_RENDER(*args, **kwargs)
        calls['render'] += 1
        if second_render is not None and calls['render'] > 1:
            report_set = second_render(report_set)
        seen['sets'].append(report_set)
        return report_set
    monkeypatch.setattr(reports, 'render', render)

    def write(report_set, out_dir):
        seen['writes'].append((report_set, pathlib.Path(out_dir)))
        return _REAL_WRITE(report_set, out_dir)
    monkeypatch.setattr(reports, 'write_report_set', write)

    def emit(command, code, status, run_id, details):
        seen['details'].append(list(details))
        return _REAL_EMIT(command, code, status, run_id, details)
    monkeypatch.setattr(cli, '_emit', emit)

    if previous_pool_stats is not None:
        def frames(loaded, **products):
            stats = products.get('pool_stats')
            if stats is not None and products.get('previous_pool_stats') is None:
                baseline = previous_pool_stats(stats)
                seen['g14'].append((stats, baseline))
                products['previous_pool_stats'] = baseline
            return _REAL_FRAMES(loaded, **products)
        monkeypatch.setattr(cli, '_report_frames', frames)
    return seen


def _score(monkeypatch, root, name, *, app_kwargs=None, mutate_app=None, **capture_kwargs):
    '''一次**真实**的 `dsm score` 实跑（九步全真、写盘全真、config 真加载、io_loaders
    真读八表；只有两个明文「不入分」的旁路按 test_cli_marshal 的既有装置换掉，见模块
    docstring 末段）。返回 _Outcome。'''
    work = pathlib.Path(root) / name
    work.mkdir(parents=True, exist_ok=True)
    conf, data = marshal._stage_data(work)
    app = marshal._app(conf, **(app_kwargs or {'triangulation': False}))
    if mutate_app is not None:
        app = mutate_app(app)
    argv = marshal._wire(monkeypatch, app, conf, data)
    out = work / 'out'
    argv += ['--out', str(out)]
    marshal._bypass_l5(monkeypatch)          # 写集外缺陷 B1 的旁路（[L1336] 不入分）
    seen = _capture(monkeypatch, **capture_kwargs)
    code = cli.main(argv)
    dirs = marshal._run_dirs(out) if out.exists() else []
    return _Outcome(code, out, (dirs[-1] if dirs else None), seen)


def _draft_weights(app):
    '''把签认的 weights 文档 status 置为 DRAFT -> C-01 WEIGHT_VERSION_DRAFT（BLOCK）。
    构造口径与 tests/test_preflight.py:391 `_world(weight_version=_weights(status='DRAFT'))`
    同一条（值取自该既有测试，不是本文件拟的）。'''
    weights = dict(app.weights)
    key = sorted(weights)[0]
    doc = dict(weights[key])
    doc['status'] = 'DRAFT'
    weights[key] = doc
    return app.model_copy(update={'weights': weights})


def _previous_period_with_lower_c_share(stats):
    '''G-8 的上期基线：C 计数 -1、A 计数 +1（Σ四类不变 -> 判据分母 assessed_denominator
    不变），于是 c_class_share(上期) < c_class_share(本期) = [L1416]「C 类占比上升」，
    与 tests/test_golden_b.py:2024+ 的 3/9 -> 5/9 同构。数值全部由当期结构派生（R-12）。'''
    structure = dict(stats.evidence_structure)
    assert int(structure.get('C', 0)) >= 1, \
        '前提检查：本期必须有 C 类证据，否则「C 占比上升」无从构造（数据面问题，非本判据缺陷）'
    structure['C'] = int(structure['C']) - 1
    structure['A'] = int(structure.get('A', 0)) + 1
    return stats.model_copy(update={'evidence_structure': structure})


def _digests_in_audit_json(body):
    '''从 canonical text 里读出 output_fingerprints 的 name -> sha256（NG-V12-21：这份正文
    **不是** JSON，故不做 json.loads；读法与 tests/test_cli_marshal.py 同一口径）。'''
    block = re.search(r's:output_fingerprints=\{([^{}]*)\}', body)
    assert block is not None, 'audit.json 正文里没有 output_fingerprints 列（[L1051] item 10）'
    return dict(re.findall(r's:([A-Za-z0-9_.-]+)=s:([0-9a-f]{64})', block.group(1)))


def _verdict_lines(section):
    '''⑥段里「判据已触发」的警示行：必须同时带注册码与 dsm/reason_codes.py **注册表里**的
    message 文本（message 由 reason_codes.message 取出，不是从渲染输出里抄的）。
    「本期不可比」那类披露行只有码、没有 message，故不会被误判成已触发。'''
    return [line for line in section.split('\n')
            if DEGRADED.value in line and DEGRADED_MESSAGE in line]


# ---------------------------------------------------------------------------
# ① + ②：六键逐值重算 == 落盘字节；键集精确相等；磁盘上恰好七件
# ---------------------------------------------------------------------------
def test_output_fingerprints_equal_the_sha256_of_the_landed_bytes_value_by_value(
        monkeypatch, tmp_path):
    '''①：端到端成功跑一次，bundle.output_fingerprints 的**每一个值**都用 hashlib.sha256
    对**落盘文件的字节**重算并逐值全等（不是「格式合法」就算过）。
    ②：键集精确等于 reports.ARTIFACT_NAMES - {audit.json}（6 个），磁盘上产物文件恰为 7 个。

    为什么必须逐值重算：dsm/audit.py:162 的 `check_sha256` **只校验格式**（长度 64 + 全
    小写十六进制），假指纹 `'0'*64` 会被它照单全收 —— 本测试第一条断言就是实测这件事。
    格式校验不等于真对账，[L1640] 步骤一的可核验性只能靠逐值重算来保证。
    '''
    assert audit.check_sha256('0' * 64, 'probe') == '0' * 64, \
        '前提检查：check_sha256 只查格式，假指纹必须能过它（否则本测试的理由不成立）'
    run = _score(monkeypatch, tmp_path, 'recompute')
    assert run.code == cli.EXIT_OK
    assert len(run.bundles) == 2, \
        'ORCH-59 是两遍装配：bundle0（output_fingerprints={}）与 bundle1（fps6），实测 ' \
        + str(len(run.bundles))
    fingerprints = run.bundle.output_fingerprints
    assert set(fingerprints) == set(reports.ARTIFACT_NAMES) - {AUDIT_ARTIFACT}, \
        '键集必须精确等于 ARTIFACT_NAMES - {audit.json}（ORCH-59 第 5 条六键），实测 ' \
        + repr(sorted(fingerprints))
    assert len(fingerprints) == 6
    assert run.landed() == sorted(SEVEN), \
        '[L1062] 磁盘上恰好七件产物（report.md + 五张表 + audit.json），实测 ' + str(run.landed())
    for name in SIX:
        landed = run.bytes_of(name)
        assert hashlib.sha256(landed).hexdigest() == fingerprints[name], \
            name + ' 的指纹与落盘字节重算的 SHA256 不等（假指纹 / 编码不一致 / 写盘后又改）'
        assert len(fingerprints[name]) == 64
    assert AUDIT_ARTIFACT not in fingerprints, \
        'audit.json 的自指纹不可能进它自己的正文（[L1046] 自指，ERRATUM-V12-07 / NG-V12-20）'


def test_landed_audit_json_carries_the_six_digests_and_its_own_only_in_details(
        monkeypatch, tmp_path):
    '''②的落盘面：写出去的 audit.json 正文里带的就是那六枚（逐值等于磁盘重算），而它
    自身的 SHA256 只出现在 CLI 披露面（ORCH-59 第 6 条），**不出现在它自己的正文里**。'''
    run = _score(monkeypatch, tmp_path, 'landed')
    assert run.code == cli.EXIT_OK
    body = run.text_of(AUDIT_ARTIFACT)
    assert body.startswith('obj:AuditBundle{'), \
        'NG-V12-21：正文是 canonical text（本 RUN 不修），本文件按同一读法断言，不 json.loads'
    carried = _digests_in_audit_json(body)
    assert set(carried) == set(SIX), 'audit.json 正文里的键集必须是六键，实测 ' + repr(sorted(carried))
    for name in SIX:
        assert carried[name] == hashlib.sha256(run.bytes_of(name)).hexdigest(), \
            name + '：audit.json 里那枚与落盘字节重算不等'
    own = hashlib.sha256(run.bytes_of(AUDIT_ARTIFACT)).hexdigest()
    assert own not in body, 'audit.json 不得含自身终值的哈希（自指不可能，ORCH-59 第 6 条）'
    assert any(AUDIT_ARTIFACT + '=' + own in line for line in run.details), \
        'audit.json 自身的 SHA256 必须经 details 通道对外披露（write_report_set 的返回值），实测无'


# ---------------------------------------------------------------------------
# ③：rs0 / rs1 六件逐字节相等 + 写盘只发生一次
# ---------------------------------------------------------------------------
def test_two_pass_render_is_byte_identical_on_the_six_and_writes_the_set_once(
        monkeypatch, tmp_path):
    '''③ ORCH-59 第 4/5 条：**同一次运行内**（同 run_id）比较 rs0 与 rs1 —— 六件非
    audit.json 产物逐字节相等（证明把 fps6 回填进 bundle 不自相矛盾），audit.json 必然
    不同（它正文里多了六枚指纹），write_report_set 只跑一次、写的就是 rs1。

    跨运行不可比：run_id 末段每次运行不同（[L1091]），report.md / score_card.csv 的字节
    因此跨运行不可复现，所以本条只在同一次运行的两个 ReportSet 之间比。
    '''
    run = _score(monkeypatch, tmp_path, 'twopass')
    assert run.code == cli.EXIT_OK
    assert len(run.sets) == 2, '两遍渲染：rs0 与 rs1（ORCH-59 第 1/3 条），实测 ' + str(len(run.sets))
    assert run.bundles[0].output_fingerprints == {}, \
        '第一遍必须用空映射建 bundle0（ORCH-59 第 1 条）'
    first, second = run.sets[0].artifacts(), run.sets[1].artifacts()
    for name in SIX:
        assert first[name].encode('utf-8') == second[name].encode('utf-8'), \
            name + ' 在两遍之间变了 -> 某件产物内嵌了 output_fingerprints，按 ORCH-59 第 4 条' \
            '必须停手上报主控（不许两遍写盘伪造自指纹）'
    assert first[AUDIT_ARTIFACT] != second[AUDIT_ARTIFACT], \
        'audit.json 必须随 bundle1 变（正文里多了六枚指纹），否则回填根本没进产物'
    for name in SIX:
        assert run.bundle.output_fingerprints[name] == audit.sha256_text(first[name]), \
            name + '：回填的指纹必须等于 rs0 那件按 write_report_set 同一编码算出的 SHA256'
    assert len(run.writes) == 1, \
        'write_report_set 只准跑一次（ORCH-59 第 5 条：一次写出 7 件），实测 ' + str(len(run.writes))
    assert run.writes[0][0] is run.sets[1], '落盘的必须是第二遍的 rs1'
    assert run.writes[0][1] == run.run_dir
    for name, text in second.items():
        assert run.bytes_of(name) == text.encode('utf-8'), name + ' 落盘字节与 rs1 不一致'
    assert run.landed() == sorted(SEVEN)


def test_inv_a_guard_stops_the_run_instead_of_writing_a_self_contradicting_set(
        monkeypatch, tmp_path):
    '''ORCH-59 第 4 条的守护必须是**真的**（不是装饰）：若某件非 audit.json 产物内嵌了
    output_fingerprints（=> rs0/rs1 六件不再逐字节相等），shell 必须停手 —— [L1081] 退出码 5、
    write_report_set 一次都不跑、七件产物一件都不落盘，并点名不变式（V-14 不静默）。
    构造：只把**第二遍**的 report.md 尾部追加一枚假指纹，第一遍不动。'''
    def poison(report_set):
        return report_set.model_copy(
            update={'report_md': report_set.report_md + '<!-- ' + 'f' * 64 + ' -->\n'})

    run = _score(monkeypatch, tmp_path, 'inv_a', second_render=poison)
    assert run.code == cli.EXIT_INTERNAL == 5, '不变量被破 -> [L1081] 退出码 5，实测 ' + str(run.code)
    assert run.writes == [], 'INV-A 被破时绝不写盘（写出来就是对不上账的七件）'
    landed = run.every_landed_name()
    assert not [name for name in SEVEN if name in landed], \
        '七件产物一件都不该落盘，实测 ' + str(landed)
    assert landed == [FAILURE_BUNDLE], \
        '[L1091]：失败的运行仍留一份 audit_bundle，实测 ' + str(landed)
    assert any('ORCH-59 INV-A' in line for line in run.details), \
        '停手必须点名不变式（V-14：降级必须带码且可见，不静默）'
    doc = json.loads(run.find(FAILURE_BUNDLE).read_text(encoding='utf-8'))
    assert doc['output_fingerprints'] == {} and doc['exit_code'] == cli.EXIT_INTERNAL


# ---------------------------------------------------------------------------
# ④：BLOCK / 失败路的既有断言原样保留、禁弱化
# ---------------------------------------------------------------------------
def test_block_path_writes_only_the_audit_bundle_and_never_renders_the_seven(
        monkeypatch, tmp_path):
    '''④（BLOCK 路，CLI 层）：[L917] / [L1326] 的既有口径一个字也不许松 —— BLOCK ->
    只写 audit_bundle、退出码 2、不产出 score_card，`output_fingerprints` 恒为 {}；
    九步的 build_manifest / reports.render / write_report_set 一次都不跑，七件产物一件都
    不落盘（两遍渲染只挂在成功路上）。既有守护：tests/test_preflight.py:399/430、
    tests/test_integration_spine.py:523、tests/test_golden_b.py:1333（preflight 层）。'''
    run = _score(monkeypatch, tmp_path, 'block', mutate_app=_draft_weights)
    assert run.code == cli.EXIT_BLOCK == 2
    assert run.every_landed_name() == [AUDIT_ARTIFACT], \
        'BLOCK 时目录里除审计包外不得有任何文件（[L917]），实测 ' + str(run.every_landed_name())
    assert not [name for name in SEVEN if name != AUDIT_ARTIFACT and name in run.every_landed_name()]
    assert run.bundles == [], 'BLOCK 在 Step9 之前返回：九步的 build_manifest 一次都不跑'
    assert run.sets == [] and run.writes == [], 'BLOCK 绝不渲染、绝不写七件产物（[L1326]）'
    payload = json.loads(run.find(AUDIT_ARTIFACT).read_text(encoding='utf-8'))
    assert payload['output_fingerprints'] == {}, '[L917]：BLOCK 的审计包如实记「本次没有任何评分产物」'
    assert payload['exit_code'] == 2


def test_failure_path_writes_only_audit_bundle_with_empty_output_fingerprints(
        monkeypatch, tmp_path):
    '''④（失败路，CLI 层）：治理键缺失 -> [L1080] 退出码 3，只写 audit_bundle.json，其
    output_fingerprints 恒为 {}（dsm/cli.py:_write_failure_bundle，本包一字未改），
    七件产物一件都不落盘，render / write_report_set 一次都不跑。'''
    run = _score(monkeypatch, tmp_path, 'failure',
                 app_kwargs={'triangulation': False,
                             'drop_eval': ('min_coverage_for_absolute_track',)})
    assert run.code == cli.EXIT_CONFIG == 3
    assert run.every_landed_name() == [FAILURE_BUNDLE], \
        '失败路唯一的产物是 audit_bundle（[L1091]），实测 ' + str(run.every_landed_name())
    assert run.sets == [] and run.writes == [], '失败路绝不渲染、绝不写七件产物'
    doc = json.loads(run.find(FAILURE_BUNDLE).read_text(encoding='utf-8'))
    assert doc['output_fingerprints'] == {} and doc['exit_code'] == cli.EXIT_CONFIG


# ---------------------------------------------------------------------------
# ⑤：G-8 关闭判据 —— MIX_QUALITY_DEGRADED 是 WARN，不改退出码
# ---------------------------------------------------------------------------
def test_g8_mix_quality_degraded_shows_in_section_six_without_moving_the_exit_code(
        monkeypatch, tmp_path):
    '''⑤ G-8：CLI 实跑一条 WARN 不阻断的路径，report.md 的⑥段出现 MIX_QUALITY_DEGRADED
    警示行，且退出码**不因该 WARN 改变**（对照组 = 同一条链、只差一个上期基线）。
    判据唯一性：报告里的结论必须等于 pooling.mix_quality_verdict 对同一对 PoolStats 的判定
    （ORCH-36 第 2/4 条：shell 与渲染层都不另算一套 C 占比）。'''
    control = _score(monkeypatch, tmp_path, 'g8-control')
    warned = _score(monkeypatch, tmp_path, 'g8-warn',
                    previous_pool_stats=_previous_period_with_lower_c_share)
    # 码本身：注册属性（dsm/reason_codes.py:97）severity=WARN、不在 _BLOCKS_RUN。
    assert DEGRADED.value == 'MIX_QUALITY_DEGRADED'
    assert reason_codes.severity(DEGRADED) is reason_codes.Severity.WARN
    assert reason_codes.blocks_run(DEGRADED) is False
    assert DEGRADED.value not in reason_codes.blocks_run_codes()
    # 退出码不因该 WARN 改变（两次实跑唯一的差别就是上期基线有无）。
    assert control.code == cli.EXIT_OK, '对照组必须先跑通，否则本条测不到 WARN 的影响'
    assert warned.code == control.code, \
        'WARN 不改退出码（dsm/reason_codes.py:97 severity=WARN、blocks_run=False），实测 ' \
        + str(warned.code) + ' vs ' + str(control.code)
    # 对照组：基线缺位 -> ⑥段如实披露「本期不可比」，且**不**出现 MIX_QUALITY_DEGRADED
    # （V-14：不得当作「没上升」静默略过）。
    baseline_section = control.section(SECTION_6)
    assert '不可比' in baseline_section, '基线缺位必须显式披露「不可比」（V-14）'
    fired = _verdict_lines(baseline_section)
    assert not fired, \
        '没有基线就不该有已触发的判据结论行（⑥段只准披露「不可比」），实测 ' + repr(fired)
    # 实验组：⑥段出现 MIX_QUALITY_DEGRADED 警示行，且自带 severity / blocks_run 披露。
    lines = _verdict_lines(warned.section(SECTION_6))
    assert lines, 'G-8 关闭判据：⑥段（[L1063]）必须出现 MIX_QUALITY_DEGRADED 警示行（[L1416]）'
    assert any('WARN' in line and 'blocks_run=false' in line for line in lines), \
        '警示行必须自带 severity=WARN 与 blocks_run=false（dsm/reason_codes.py:97 的注册属性），' \
        '实测 ' + repr(lines)
    disclosed = '\n'.join(warned.details)
    assert DEGRADED.value in disclosed and '不改退出码' in disclosed, \
        'CLI 披露面同样要说明「只披露、不改退出码、不中断九步」（V-14）'
    # 判据唯一性 + 场景构造成立：C 类占比确实上升，且上升量 > numeric.TOL（1E-12）。
    assert warned.seen['g14'], '上期基线没有经 _report_frames 注进去，本条测不到判据'
    current, previous = warned.seen['g14'][-1]
    assert pooling.mix_quality_verdict(current, previous) is DEGRADED
    assert pooling.c_class_share(previous) < pooling.c_class_share(current)
    assert pooling.c_class_share(current) - pooling.c_class_share(previous) > numeric.TOL
    assert pooling.assessed_denominator(previous) == pooling.assessed_denominator(current), \
        '构造口径：只搬 C->A，判据分母（Σ四类 - NA）不变，与 tests/test_golden_b.py:2024+ 同构'
    # WARN 不截断产物：七件齐、十段齐（[L1062] / [L1063]）。
    assert warned.landed() == sorted(SEVEN)
    assert reports.assert_report_sections(warned.text_of('report.md')) == reports.REPORT_SECTIONS
    # 六键口径在 WARN 路上同样成立（WARN 不是绕过对账的理由）。
    assert set(warned.bundle.output_fingerprints) == set(SIX)
    for name in SIX:
        assert hashlib.sha256(warned.bytes_of(name)).hexdigest() \
            == warned.bundle.output_fingerprints[name]


# ---------------------------------------------------------------------------
# ⑥：M29-1 已声明的红线原样保留
# ---------------------------------------------------------------------------
def test_gate_statement_redline_survives_the_six_key_outlet(monkeypatch, tmp_path):
    '''⑥：G5/G7 未签认的门禁声明逐字不动 —— dsm/reports.py:55-58 的 GATE_STATEMENT 必须
    原样出现在 CLI 披露面与 report.md ①首屏（[L1063]①），「不得输出可用于真实资源配置的
    分数或等级」这类表述一个字也不许改；本包新增的 ORCH-59 披露行**不得**宣称可用于真实
    资源配置（H-5 / R-12：G5/G7 未签认，只用合成数据跑通机制）。'''
    run = _score(monkeypatch, tmp_path, 'redline')
    assert run.code == cli.EXIT_OK
    joined = '\n'.join(run.details)
    assert reports.GATE_STATEMENT in joined, '门禁声明必须逐字出现在 CLI 披露面（M29-1 红线）'
    assert '不得输出可用于真实资源配置' in joined
    assert reports.GATE_STATEMENT in run.section(SECTION_1), \
        '①首屏必写可用性声明（[L1063]① / G5、G7 未签认）'
    orch = [line for line in run.details if 'ORCH-59' in line]
    assert orch, '两遍渲染六键口径必须在披露面留痕（V-14：口径变更不静默）'
    for line in orch:
        assert '可用于真实资源配置' not in line, \
            'ORCH-59 的披露行不得宣称可用于真实资源配置（G5/G7 未签认）：' + line
    assert any(line.strip().startswith(name + '=') for name in SEVEN for line in run.details), \
        '七件产物的实测 SHA256 仍逐件披露（M29-1 的披露面不许因六键口径而缩水）'
    for name in SEVEN:
        assert any(line.strip().startswith(name + '=') for line in run.details), \
            name + ' 的指纹必须在披露面出现（含 audit.json 自身，它只在披露面、不进正文）'
