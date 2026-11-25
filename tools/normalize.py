#!/usr/bin/env python3
'''Normalize and encoding-gate the CONTROLLED files of this repository.

作用域（D-TOOLS-01 / P2-wire-A NEED-WIRING #7，ORCH-42 已裁）：只断言 `git ls-files`
列出的受控文件（HEAD 5d13ef3 实测 189 个）。旧实现用 os.walk(ROOT) 枚举，会把
gitignored 的 dsm_stage/ 一并扫进来，实测 --check 假红 `NEEDS_NORMALIZATION 38 of 666`
（抽样前 4 条全在 dsm_stage/ADJ-G07/）——会叫错狼的门禁等于没有门禁。

门禁口径（ORCH-36 第 11 条；定义出处 H-G3 docs/ORCH-TEMPLATE-v1.0.md:146 +
docs/CONTEXT-BRIEF-v1.0.md:33 + docs/RUN-UNATTENDED-v2.0.md:72 + docs/adr/ORCH-21.md:130）：
  * 四要素 = 全量受控文件**硬失败**：UTF-8 strict 可解码 / 无 BOM / 行尾 LF（全文无 CR）/ 无 TAB
    （CONTEXT-BRIEF:33 逐字为「仓库内文件必须 UTF-8 无 BOM + LF + 无 TAB」，未把 TAB 限于源码，
     故本实现按全量受控文件断言；HEAD 实测四要素违规 0）
  * 末尾换行 LF = **只对「本次变更文件」断言**；历史遗留缺末尾 LF 的受控文件**只披露不返工**
    （HEAD 实测 21 个，全在本包禁写范围：12 个 docs/** + README.md，9 个 dsm/ tests/ tools/。
     ORCH-36 第 11 条原写 20、移交单写 22，以本次实测 21 为准，差异已在 NOTES 披露）

「本次变更文件」= `git diff --name-only HEAD`（工作树 + 暂存区 vs HEAD）∪ 命令行点名的路径
∪ `--changed-since REF` 的 REF..HEAD 区间。dsm_stage/ 是 gitignored，git 根本不追踪，
所以 scratch 永远不会把门禁染红（V-14：不静默降级，历史项逐条披露在 DISCLOSURE 段）。

Usage:
    python3 tools/normalize.py                      修复受控文件的 BOM/CRLF（+ 变更文件的末尾 LF）
    python3 tools/normalize.py --check              只报告，有违规 exit 1（阶段末必跑）
    python3 tools/normalize.py --changed-since REF   把「本次变更」放宽到 REF..HEAD
    python3 tools/normalize.py --also-scratch       仅修复：连 gitignored scratch 一起规范化
                                                    （与 --check 互斥，永不参与门禁判定）
'''
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BOM = b'\xef\xbb\xbf'
# 四要素：全量受控文件硬失败（ORCH-36 第 11 条）
FOUR_ELEMENTS = ('UTF8_STRICT', 'NO_BOM', 'LF_LINE_ENDINGS', 'NO_TAB')
# 只对「本次变更文件」断言的一项
CHANGED_ONLY_ELEMENTS = ('TRAILING_LF',)

EXTS = {
    '.py', '.md', '.yaml', '.yml', '.toml', '.sh', '.csv', '.json', '.jsonl',
    '.txt', '.cfg', '.ini', '.tsv', '.rst',
}
EXACT_NAMES = {'.gitignore', '.gitattributes', 'Makefile', 'Dockerfile', 'LICENSE'}
SKIP_DIRS = {
    '.git', '__pycache__', '.pytest_cache', '.hypothesis', '.venv',
    'venv', '.tmp', 'build', 'dist', '.mypy_cache', '.ruff_cache',
}


def _git_z(*args):
    '''One git call, NUL-split. The controlled surface is enumerated by git and by
    nothing else: a hand-kept file list would drift the moment a package adds one.'''
    proc = subprocess.run(('git',) + args + ('-z',), cwd=ROOT,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise SystemExit('git ' + ' '.join(args) + ' failed: '
                         + proc.stderr.decode('utf-8', 'replace').strip())
    return [name for name in proc.stdout.decode('utf-8').split('\0') if name]


def controlled_files():
    return sorted(set(_git_z('ls-files')))


def relative(path):
    rel = os.path.relpath(os.path.abspath(path), ROOT)
    return rel.replace(os.sep, '/')


def changed_files(since=(), explicit=()):
    names = set(_git_z('diff', '--name-only', 'HEAD'))
    for ref in since:
        names.update(_git_z('diff', '--name-only', ref, 'HEAD'))
    for path in explicit:
        names.add(relative(path))
    return names


def scratch_files(controlled):
    '''--also-scratch 专用（只修复、不判定）：gitignored 的 scratch 树里的文本文件。'''
    keep = set(controlled)
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            rel = relative(os.path.join(dirpath, fn))
            ext = os.path.splitext(fn)[1].lower()
            if rel not in keep and (ext in EXTS or fn in EXACT_NAMES):
                yield rel


def inspect_bytes(raw):
    '''四要素 + 末尾 LF 的逐字节判定。返回 (violations, lacks_trailing_lf)。'''
    violations = []
    if raw.startswith(BOM):
        violations.append('NO_BOM')
    if b'\r' in raw:
        violations.append('LF_LINE_ENDINGS')
    try:
        raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        violations.append('UTF8_STRICT')
    if b'\t' in raw:
        violations.append('NO_TAB')
    return violations, bool(raw) and not raw.endswith(b'\n')


def repair_bytes(raw, lacks_trailing_lf, assert_trailing):
    new = raw
    if new.startswith(BOM):
        new = new[len(BOM):]
    new = new.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    if lacks_trailing_lf and assert_trailing:
        new += b'\n'
    return new


UNFIXABLE = ('NO_TAB', 'UTF8_STRICT')


def parse(argv):
    check = '--check' in argv
    also_scratch = '--also-scratch' in argv
    since, explicit, skip = [], [], False
    for arg in argv:
        if skip:
            since.append(arg)
            skip = False
        elif arg == '--changed-since':
            skip = True
        elif arg.startswith('--'):
            continue
        else:
            explicit.append(arg)
    if check and also_scratch:
        raise SystemExit('--also-scratch is repair-only and never gates; '
                         'it cannot be combined with --check')
    if skip:
        raise SystemExit('--changed-since needs a git ref')
    return check, also_scratch, tuple(since), tuple(explicit)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    check, also_scratch, since, explicit = parse(argv)
    controlled = controlled_files()
    changed = changed_files(since, explicit)

    violations, historical, repaired, unfixable, absent = [], [], [], [], []
    for rel in controlled:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            absent.append(rel)   # 索引里还在、工作树已删：归 git status 披露，不算编码违规
            continue
        with open(path, 'rb') as handle:
            raw = handle.read()
        found, lacks_lf = inspect_bytes(raw)
        violations += [(rel, element) for element in found]
        if lacks_lf:
            if rel in changed:
                violations.append((rel, 'TRAILING_LF'))
            else:
                historical.append(rel)
        if not check:
            new = repair_bytes(raw, lacks_lf, rel in changed)
            if new != raw:
                with open(path, 'wb') as handle:
                    handle.write(new)
                repaired.append(rel)
            unfixable += [(rel, element) for element in found if element in UNFIXABLE]

    if also_scratch and not check:
        for rel in scratch_files(controlled):
            path = os.path.join(ROOT, rel)
            with open(path, 'rb') as handle:
                raw = handle.read()
            new = repair_bytes(raw, False, False)
            if new != raw:
                with open(path, 'wb') as handle:
                    handle.write(new)
                repaired.append(rel)

    bad_files = sorted({rel for rel, _ in violations})
    print('SCOPE git ls-files:', len(controlled), 'controlled files; gitignored '
          'scratch (dsm_stage/ ...) is NOT scanned (D-TOOLS-01)')
    print('FOUR_ELEMENTS', '/'.join(FOUR_ELEMENTS), 'asserted on all',
          len(controlled), 'controlled files;', '/'.join(CHANGED_ONLY_ELEMENTS),
          'asserted on the', len(changed & set(controlled)), 'changed file(s) only')
    verb = 'NEEDS_NORMALIZATION' if check else 'NORMALIZED'
    print(verb, len(bad_files) if check else len(repaired), 'of', len(controlled), 'files')
    for rel, element in violations:
        print('  ', rel, element)
    for rel in repaired:
        print('  ', rel)
    print('DISCLOSURE TRAILING_LF_HISTORICAL', len(historical), 'of', len(controlled),
          '-- disclosed, deliberately NOT reworked (ORCH-36 ruling 11; the owners of '
          'docs/** and README.md are outside this gate)')
    for rel in historical:
        print('  ', rel)
    if absent:
        print('DISCLOSURE ABSENT_FROM_WORKTREE', len(absent), '-- indexed but deleted; '
              'git status owns this, not the encoding gate')
        for rel in absent:
            print('  ', rel)
    if unfixable:
        print('UNFIXABLE', len(unfixable), '-- TAB / non-UTF-8 bytes are never rewritten '
              'automatically (a blind TAB->space pass would reindent Python); fix by hand')
        for rel, element in unfixable:
            print('  ', rel, element)
    if check:
        return 1 if violations else 0
    return 1 if (violations or unfixable) else 0


if __name__ == '__main__':
    sys.exit(main())
