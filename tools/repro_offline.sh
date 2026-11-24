#!/usr/bin/env bash
# tools/repro_offline.sh —— P3b 复现性签核工装（一键重跑，幂等）
#
# 把 SDD [L1640]「第二人在全新 clone + 断网单机 + 同 seed 下复跑，
# reproducibility_hash 必须精确相等」落成一条命令：
#
#   1) 从**本地路径**全新 clone 到 mktemp -d（本地提交未 push，故不走远端）
#   2) 建独立 venv，只用本地 wheelhouse 安装（--no-index，不碰任何网络索引）
#   3) 整个「装环境 + 连跑」都放进 network namespace（unshare -rn）里执行
#   4) 同一 seed 连跑 N 次（默认 2），逐次比对 64 位 sha256
#   5) 打印 PASS/FAIL + 哈希 + 截至 commit，并以 exit code 0/1 表达
#
# 用法：
#   tools/repro_offline.sh                       # 用脚本所在仓库、默认 venv python
#   tools/repro_offline.sh --src /path/to/repo --python /path/to/python
#   tools/repro_offline.sh --wheelhouse /path/to/wheels --runs 2 --expect <64hex>
#   tools/repro_offline.sh --keep                # 保留临时目录以便取证
#   tools/repro_offline.sh --no-pytest           # 只跑探针，不跑 spine 断言
#   tools/repro_offline.sh --strict-isolation    # 隔离级别非 L3-strong 即判 FAIL（P3b 正式签核必须加）
#
# 环境变量默认值：BASEPY=/home/szf/venvs/dsm/bin/python
#
# 诚实性边界（详见 docs/deliverables/P3b-REPRO-HARNESS.md）：
#   * 本脚本自身不联网；但 wheelhouse 的**首次预下载需要联网**，那一步不在本脚本内。
#     缺 wheelhouse 时脚本不会假装断网成功，而是降级为 --system-site-packages 并把
#     隔离级别如实标成 PLACEHOLDER。
#   * unshare -rn 不可用（无 user namespace 权限）时，断网降级为「清空代理变量 +
#     PIP_NO_INDEX=1」，隔离级别同样如实降级标注，绝不宣称为强隔离。
#   * 复现哈希当前由 tests/test_integration_spine.py 的 _run_chain 产出（测试内合成
#     GOVERNANCE 配置），**不是** dsm score CLI 的真实运行：仓库 config/ 为 0 文件，
#     dsm/config.py:449 load_all() 会以 EXIT_CONFIG=3（dsm/config.py:71）拒绝，且
#     dsm/cli.py:199 的 reproducibility_hash 仍是 PLACEHOLDER。
set -uo pipefail

PROG=${0##*/}
SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)

SRC=${SCRIPT_DIR%/tools}
BASEPY=${BASEPY:-/home/szf/venvs/dsm/bin/python}
WHEELHOUSE=
NETNS_MODE=auto
RUNS=2
KEEP=0
RUN_PYTEST=1
EXPECT=
STRICT_ISO=0

usage() {
  sed -n '2,32p' "$0"
}

while [ $# -gt 0 ]; do
  case $1 in
    --src)        SRC=$2; shift 2 ;;
    --python)     BASEPY=$2; shift 2 ;;
    --wheelhouse) WHEELHOUSE=$2; shift 2 ;;
    --netns)      NETNS_MODE=$2; shift 2 ;;
    --runs)       RUNS=$2; shift 2 ;;
    --expect)     EXPECT=$2; shift 2 ;;
    --keep)       KEEP=1; shift ;;
    --no-pytest)  RUN_PYTEST=0; shift ;;
    --strict-isolation) STRICT_ISO=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "$PROG: unknown argument: $1" >&2; exit 2 ;;
  esac
done

die() { echo "$PROG: FATAL: $*" >&2; exit 1; }
note() { printf '%s\n' "$*"; }

T0=$(date +%s)
[ -n "$RUNS" ] && [ "$RUNS" -ge 1 ] 2>/dev/null || die "--runs must be a positive integer"
command -v git >/dev/null 2>&1 || die "git not found"
[ -x "$BASEPY" ] || die "base python not executable: $BASEPY"
[ -d "$SRC/.git" ] || die "not a git repository: $SRC"
[ -f "$SRC/requirements.txt" ] || die "requirements.txt missing under $SRC"
[ -n "$WHEELHOUSE" ] || WHEELHOUSE=$SRC/dsm_stage/P3b-prep/wheelhouse

SRC_HEAD=$(git -C "$SRC" rev-parse HEAD) || die "git rev-parse HEAD failed"
SRC_HEAD7=${SRC_HEAD:0:7}
SRC_BRANCH=$(git -C "$SRC" rev-parse --abbrev-ref HEAD)
SRC_DIRTY=$(git -C "$SRC" status --porcelain | wc -l)

# ---- 断网手段判定：真 network namespace 优先，不可用则如实降级 -------------
NETNS=off
if [ "$NETNS_MODE" != off ] && unshare -rn true >/dev/null 2>&1; then
  NETNS=on
fi
if [ "$NETNS_MODE" = on ] && [ "$NETNS" = off ]; then
  die "--netns on requested, but 'unshare -rn' is not permitted on this host"
fi
if [ "$NETNS" = on ]; then
  RUNNER=(unshare -rn)
  NET_MEANS="network namespace (unshare -rn): only 'lo' exists and is DOWN, DNS/TCP both fail"
else
  RUNNER=(env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY)
  NET_MEANS="PLACEHOLDER: no netns (unshare -rn not permitted) -> proxy vars cleared + PIP_NO_INDEX=1 only"
fi

# ---- 临时目录（每次运行新建，退出即清理 => 幂等可重复） --------------------
TMP=$(mktemp -d "${TMPDIR:-/tmp}/p3b-repro.XXXXXXXX") || die "mktemp -d failed"
cleanup() { if [ "$KEEP" != 1 ]; then rm -rf "$TMP"; else echo "$PROG: kept temp dir: $TMP"; fi; }
trap cleanup EXIT
trap 'exit 1' INT TERM

note "== P3b reproducibility harness =="
note "src_repo        = $SRC"
note "src_branch      = $SRC_BRANCH"
note "src_head        = $SRC_HEAD ($SRC_HEAD7)"
note "src_dirty_files = $SRC_DIRTY  (uncommitted changes are NOT cloned; the clone is commit-exact)"
note "base_python     = $BASEPY ($($BASEPY -V 2>&1))"
note "net_isolation   = $NET_MEANS"
note "wheelhouse      = $WHEELHOUSE"
note "tmpdir          = $TMP"

# ---- ① 全新 clone（本地路径，--no-hardlinks => 对象库也独立） --------------
CLONE=$TMP/clone
git clone --quiet --no-hardlinks "$SRC" "$CLONE" || die "git clone failed"
CLONE_HEAD=$(git -C "$CLONE" rev-parse HEAD) || die "clone rev-parse failed"
note "clone_head      = $CLONE_HEAD"
[ "$CLONE_HEAD" = "$SRC_HEAD" ] || die "clone HEAD != src HEAD ($CLONE_HEAD vs $SRC_HEAD)"

# ---- ② 隔离 python 环境 ---------------------------------------------------
VENV=$TMP/venv
HAVE_WH=0
if [ -d "$WHEELHOUSE" ] && [ -n "$(ls -A "$WHEELHOUSE" 2>/dev/null)" ]; then
  HAVE_WH=1
fi
if [ "$HAVE_WH" = 1 ]; then
  ENV_MODE="dedicated venv (no system site-packages) installed from local wheelhouse with --no-index"
  ISO_LEVEL="L3-strong: fresh clone + netns offline + dedicated venv from local wheels"
  "${RUNNER[@]}" "$BASEPY" -m venv "$VENV" >"$TMP/venv.log" 2>&1 || { cat "$TMP/venv.log" >&2; die "venv creation failed"; }
  VPY=$VENV/bin/python
  PIPCOMMON=(--no-index --find-links "$WHEELHOUSE" --no-cache-dir --disable-pip-version-check)
  "${RUNNER[@]}" "$VPY" -m pip install --quiet "${PIPCOMMON[@]}" pip setuptools wheel >>"$TMP/pip.log" 2>&1 \
    || { cat "$TMP/pip.log" >&2; die "offline bootstrap install failed"; }
  "${RUNNER[@]}" "$VPY" -m pip install --quiet "${PIPCOMMON[@]}" -r "$CLONE/requirements.txt" >>"$TMP/pip.log" 2>&1 \
    || { cat "$TMP/pip.log" >&2; die "offline requirements install failed"; }
else
  # 实测：从宿主 venv 再建 --system-site-packages 的 venv **不会**继承宿主的
  # site-packages（venv 不链式继承），探针会 ModuleNotFoundError。因此弱隔离档
  # 直接用宿主解释器跑，并把「复用宿主 site-packages、未做离线安装」如实标注。
  ENV_MODE="PLACEHOLDER: wheelhouse absent -> probe runs on the host interpreter and reuses its site-packages; no offline install was performed"
  ISO_LEVEL="L1-weak: fresh clone + host site-packages reused (offline install NOT achieved)"
  VPY=$BASEPY
fi
note "env_mode        = $ENV_MODE"
note "env_python      = $VPY ($(${RUNNER[@]} "$VPY" -V 2>&1))"

# ---- ③ 探针：复用 spine 测试的 _run_chain，不重实现任何算法 ----------------
PROBE=$TMP/probe_hash.py
cat > "$PROBE" <<'PYEOF'
"""P3b offline reproducibility probe (generated by tools/repro_offline.sh).

Reuses tests/test_integration_spine.py::_run_chain verbatim; prints the 64-hex
reproducibility_hash on stdout and the run metadata on stderr. No repo writes.
"""
import os
import pathlib
import sys
import tempfile

REPO = os.path.abspath(os.environ.get('PROBE_REPO', '.'))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'tests'))
import test_integration_spine as T  # noqa: E402

root = pathlib.Path(tempfile.mkdtemp(prefix='p3b-probe-',
                                       dir=os.environ.get('PROBE_TMP') or None))
res = T._run_chain(root / 'run', T.PERIOD)
h = res['reproducibility_hash']
sys.stderr.write(
    'meta period=%s seed=%s run_id=%s exit_code=%s len=%d repo=%s\n' % (
        T.PERIOD, T.SEED, T.RUN_ID, res['bundle'].exit_code, len(h), REPO))
print(h)
PYEOF

# ---- ④ 同 seed 连跑 N 次，逐次记录 ---------------------------------------
HASHES=()
META_LAST=
i=1
while [ "$i" -le "$RUNS" ]; do
  mkdir -p "$TMP/probe-$i"
  if ! OUT=$("${RUNNER[@]}" env PROBE_REPO="$CLONE" PROBE_TMP="$TMP/probe-$i" \
             PYTHONPATH= PYTHONNOUSERSITE=1 \
             PYTHONDONTWRITEBYTECODE=1 "$VPY" "$PROBE" 2>"$TMP/meta.$i"); then
    cat "$TMP/meta.$i" >&2
    die "probe run #$i failed"
  fi
  H=$(printf '%s' "$OUT" | tail -n 1 | tr -d ' \r\n')
  HASHES+=("$H")
  META_LAST=$(cat "$TMP/meta.$i")
  note "run_#$i          = $H"
  i=$((i + 1))
done

# ---- ⑤ spine 的两连跑断言（同一条判据的 pytest 载体） ---------------------
PYTEST_RC=skip
if [ "$RUN_PYTEST" = 1 ]; then
  ( cd "$CLONE" && "${RUNNER[@]}" env PYTHONPATH= PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    "$VPY" -m pytest -q \
    tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs \
  ) >"$TMP/pytest.log" 2>&1
  PYTEST_RC=$?
  note "pytest_assertion = rc=$PYTEST_RC :: $(tail -n 1 "$TMP/pytest.log")"
fi

# ---- ⑥ 比对与裁决 ---------------------------------------------------------
FIRST=${HASHES[0]}
EQUAL=1
for H in "${HASHES[@]}"; do
  [ "$H" = "$FIRST" ] || EQUAL=0
done
case $FIRST in
  *[!0-9a-f]*) HEXOK=0 ;;
  *) HEXOK=1 ;;
esac
[ ${#FIRST} -eq 64 ] || HEXOK=0

EXPECT_RC=ok
if [ -n "$EXPECT" ]; then
  [ "$FIRST" = "$EXPECT" ] || EXPECT_RC=mismatch
fi

FAILURES=()
[ "$EQUAL" = 1 ]   || FAILURES+=("hashes differ across $RUNS runs")
[ "$HEXOK" = 1 ]   || FAILURES+=("hash is not 64 lowercase hex chars")
[ "$PYTEST_RC" = skip ] || [ "$PYTEST_RC" = 0 ] || FAILURES+=("spine pytest assertion failed (rc=$PYTEST_RC)")
[ "$EXPECT_RC" = ok ]   || FAILURES+=("hash != --expect value")
if [ "$STRICT_ISO" = 1 ]; then
  case $ISO_LEVEL in L3-strong*) ;; *) FAILURES+=("--strict-isolation: isolation is not L3-strong ($ISO_LEVEL)") ;; esac
fi

T1=$(date +%s)
note ""
note "meta            = $META_LAST"
note "runs            = $RUNS"
note "all_equal       = $EQUAL"
note "isolation_level = $ISO_LEVEL"
note "elapsed_seconds = $((T1 - T0))"
note "RESULT_HASH     = $FIRST"
note "RESULT_COMMIT   = $CLONE_HEAD"
if [ ${#FAILURES[@]} -eq 0 ]; then
  note "RESULT=PASS HASH=$FIRST COMMIT=$SRC_HEAD7 ELAPSED=$((T1 - T0))s ISOLATION=$ISO_LEVEL"
  exit 0
fi
for F in "${FAILURES[@]}"; do note "FAILURE: $F"; done
note "RESULT=FAIL HASH=$FIRST COMMIT=$SRC_HEAD7 ELAPSED=$((T1 - T0))s ISOLATION=$ISO_LEVEL"
exit 1