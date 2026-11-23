#!/usr/bin/env python3
'''Normalize text files in this repository: strip UTF-8 BOM and convert CRLF/CR to LF.

Why: source files are authored on the Windows side (PowerShell 5.1 Set-Content),
which emits UTF-8 with BOM and CRLF. Python tolerates both, but bash does not
tolerate CRLF and git diffs get noisy. This tool makes the ext4 working copy
canonical (UTF-8 no BOM, LF).

Usage:  python3 tools/normalize.py [--check]
        --check  only report, do not write (exit code 1 if any file needs change)
'''
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

EXTS = {
    '.py', '.md', '.yaml', '.yml', '.toml', '.sh', '.csv', '.json',
    '.txt', '.cfg', '.ini', '.tsv', '.rst',
}
EXACT_NAMES = {'.gitignore', '.gitattributes', 'Makefile', 'Dockerfile', 'LICENSE'}
SKIP_DIRS = {
    '.git', '__pycache__', '.pytest_cache', '.hypothesis', '.venv',
    'venv', 'reports', '.tmp', 'build', 'dist', '.mypy_cache', '.ruff_cache',
}
BOM = b'\xef\xbb\xbf'


def targets():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for fn in sorted(filenames):
            ext = os.path.splitext(fn)[1].lower()
            if ext in EXTS or fn in EXACT_NAMES:
                yield os.path.join(dirpath, fn)


def fix(path, write):
    with open(path, 'rb') as f:
        raw = f.read()
    new = raw
    if new.startswith(BOM):
        new = new[len(BOM):]
    new = new.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
    if new != raw:
        if write:
            with open(path, 'wb') as f:
                f.write(new)
        return True
    return False


def main():
    check = '--check' in sys.argv[1:]
    changed = []
    total = 0
    for p in targets():
        total += 1
        if fix(p, not check):
            changed.append(os.path.relpath(p, ROOT))
    verb = 'NEEDS_NORMALIZATION' if check else 'NORMALIZED'
    print(verb, len(changed), 'of', total, 'files')
    for c in changed:
        print('  ', c)
    if check and changed:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
