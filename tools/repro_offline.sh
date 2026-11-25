#!/usr/bin/env bash
# tools/repro_offline.sh —— P3b 复现性签核工装（一键重跑，幂等）
#
# 把 SDD [L1640]「第二人在全新 clone + 断网单机 + 同 seed 下复跑，
# reproducibility_hash 必须精确相等」落成一条命令：
#
#   1) 从**本地路径**全新 clone 到 mktemp -d（本地提交未 push，故不走远端）
#   2) 建独立 venv，只用本地 wheelhouse 安装（--no-index，不碰任何网络索引）
#   3) 整个「装环境 + 连跑」都放进 network namespace（unshare -rn）里执行
#   4) 同一 seed 连跑 N 次（默认 2），逐次记录 64 位 sha256 并互比（自等性）
#   5) 打印 PASS/FAIL + 哈希 + HEAD + 脏树数 + HEAD 稳定性 + 隔离级别，exit 0/1
#
# 用法：
#   tools/repro_offline.sh                       # 用脚本所在仓库、默认 venv python
#   tools/repro_offline.sh --src /path/to/repo --python /path/to/python
#   tools/repro_offline.sh --wheelhouse /path/to/wheels --runs 2 --expect <64hex>
#   tools/repro_offline.sh --keep                # 保留临时目录以便取证
#   tools/repro_offline.sh --no-pytest           # 只跑探针，不跑 spine 断言
#   tools/repro_offline.sh --netns on|auto|off   # 断网手段（on = 不可用即失败）
#   tools/repro_offline.sh --strict-isolation    # 隔离级别非 L3-strong 即判 FAIL（正式签核必须加）
#
# 环境变量默认值：BASEPY=/home/szf/venvs/dsm/bin/python
#
# 诚实性边界（详见 docs/deliverables/P3b-REPRO-HARNESS.md）：
#   * 本脚本自身不联网；但 wheelhouse 的**首次预下载需要联网**，那一步不在本脚本内。
#     wheelhouse 必须预先在仓库外构建（不入库、不随 clone 走），命令：
#       /home/szf/venvs/dsm/bin/python -m pip download --only-binary=:all: \
#         -d /home/szf/dsm-wheelhouse -r requirements.txt pip setuptools wheel
#     缺/空 wheelhouse 时本脚本会打印**醒目 WARNING**（stderr）并把隔离级别如实降为
#     L2-wheelhouse-missing（netns 可用）或 L1-weak（netns 也不可用），--strict-isolation
#     下判 FAIL；绝不假装断网安装成功。
#   * unshare -rn 不可用（或 --netns off）时，断网降级为「清空 6 个代理变量 + 导出
#     PIP_NO_INDEX=1」（后者经 env 真实导出，与实现对齐），隔离级别如实降为
#     L2-netns-unavailable 并在 --strict-isolation 下判 FAIL，绝不宣称强隔离。
#     netns 可用时另做正向自检：netns 内 socket.create_connection(('pypi.org',443))
#     必须失败（DNS/TCP 双失败为预期）；若竟连通则标 LEAK 并按未隔离降级。
#   * L3-strong 只在「wheelhouse 可用」AND「netns 真实生效（自检通过）」两条件同时
#     成立时输出（V-14：任何降级都显式可见，禁止静默降级）。
#   * 复现哈希当前由 tests/test_integration_spine.py 的 _run_chain 产出（测试内合成
#     GOVERNANCE 配置），**不是** dsm score CLI 的真实运行：仓库 config/ 为 0 文件
#     （实测），dsm/config.py:449 load_all() 以 EXIT_CONFIG=3（dsm/config.py:71）拒绝，
#     dsm score 端到端不可跑（属设计而非回归）。CLI 侧 reproducibility_hash 已由
#     P2-wire-A 接真源（dsm/cli.py:243-288，:288 调 dsm/audit.py:242 的
#     reproducibility_hash 取真 digest），不再是 PLACEHOLDER。
#   * 源仓库工作区脏（DIRTY=n>0）时如实标注：clone 是 commit-exact，脏文件不进
#     clone、不影响哈希；但签核结论只覆盖 RESULT_COMMIT 本身，不覆盖未提交改动。
#   * clone 前后 HEAD 一致性校验（HEAD_STABLE）：运行期间在飞 lane 前移源仓库 HEAD
#     时，--strict-isolation 判 FAIL —— 此时 RESULT_COMMIT 非最终 HEAD，须待最终
#     HEAD 复跑，不得宣称为最终签核。
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
  awk 'NR==1 { next } /^set -uo pipefail/ { exit } { print }' "$0"
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
WHEELHOUSE_DEFAULTED=0
if [ -n "$WHEELHOUSE" ]; then
  :
else
  WHEELHOUSE=$SRC/dsm_stage/P3b-prep/wheelhouse
  WHEELHOUSE_DEFAULTED=1
fi

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
NETNS_PROBE=not-run
if [ "$NETNS" = on ]; then
  RUNNER=(unshare -rn)
  NET_MEANS="network namespace (unshare -rn): only 'lo' exists and is DOWN, DNS/TCP both fail"
  # 正向自检（B1）：netns 内必须**连不通** pypi.org:443，连通即隔离泄漏
  if "${RUNNER[@]}" "$BASEPY" -c 'import socket; socket.create_connection(("pypi.org", 443), 5)' >/dev/null 2>&1; then
    NETNS_PROBE=LEAK
  else
    NETNS_PROBE=offline-confirmed
  fi
else
  # B7：降级手段与自述对齐 —— PIP_NO_INDEX=1 在这里**真实导出**，不再只是文案
  RUNNER=(env -u http_proxy -u https_proxy -u HTTP_PROXY -u HTTPS_PROXY -u all_proxy -u ALL_PROXY PIP_NO_INDEX=1)
  NET_MEANS="PLACEHOLDER: no netns (mode=$NETNS_MODE) -> only proxy vars cleared + PIP_NO_INDEX=1 exported; network NOT blocked"
fi
NETNS_EFFECTIVE=0
if [ "$NETNS" = on ] && [ "$NETNS_PROBE" = offline-confirmed ]; then
  NETNS_EFFECTIVE=1
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
note "src_dirty_files = $SRC_DIRTY  (uncommitted changes are NOT cloned; the clone is commit-exact; signoff covers commit $SRC_HEAD7 only)"
note "base_python     = $BASEPY ($($BASEPY -V 2>&1))"
note "net_isolation   = $NET_MEANS"
note "netns_probe     = $NETNS_PROBE  (positive check: connect to pypi.org:443 inside netns must FAIL)"
note "wheelhouse      = $WHEELHOUSE"
note "tmpdir          = $TMP"

# ---- ① 全新 clone（本地路径，--no-hardlinks => 对象库也独立） --------------
CLONE=$TMP/clone
git clone --quiet --no-hardlinks "$SRC" "$CLONE" || die "git clone failed"
CLONE_HEAD=$(git -C "$CLONE" rev-parse HEAD) || die "clone rev-parse failed"
note "clone_head      = $CLONE_HEAD"
[ "$CLONE_HEAD" = "$SRC_HEAD" ] || die "clone HEAD != src HEAD ($CLONE_HEAD vs $SRC_HEAD)"
# B9：clone 前后再取一次源 HEAD，防「运行期间在飞 lane 继续提交」
SRC_HEAD_POSTCLONE=$(git -C "$SRC" rev-parse HEAD) || die "git rev-parse HEAD (post-clone) failed"
HEAD_STABLE=yes
if [ "$SRC_HEAD_POSTCLONE" != "$SRC_HEAD" ]; then
  HEAD_STABLE=no
  note "WARNING: src HEAD moved during clone ($SRC_HEAD -> $SRC_HEAD_POSTCLONE)"
fi

# ---- ② 隔离 python 环境 ---------------------------------------------------
VENV=$TMP/venv
HAVE_WH=0
if [ -d "$WHEELHOUSE" ] && [ -n "$(ls -A "$WHEELHOUSE" 2>/dev/null)" ]; then
  HAVE_WH=1
fi
# B6：wheelhouse.sha256 清单存在则校验；不存在则如实标注未校验（不因此 FAIL）
WH_MANIFEST=absent-unverified
if [ "$HAVE_WH" = 1 ]; then
  WH_MAN=
  if [ -f "$WHEELHOUSE/wheelhouse.sha256" ]; then
    WH_MAN=$WHEELHOUSE/wheelhouse.sha256
  elif [ -f "${WHEELHOUSE%/}.sha256" ]; then
    WH_MAN=${WHEELHOUSE%/}.sha256
  fi
  if [ -n "$WH_MAN" ]; then
    if ( cd "$WHEELHOUSE" && sha256sum -c --quiet "$WH_MAN" ) >"$TMP/wh-manifest.log" 2>&1; then
      WH_MANIFEST="verified($(grep -c . "$WH_MAN") entries, sha256sum -c all OK)"
    else
      WH_MANIFEST=FAILED
      cat "$TMP/wh-manifest.log" >&2
    fi
  fi
fi
note "wh_manifest     = $WH_MANIFEST"
# B5：缺 wheelhouse 必须**大声披露**（stderr 醒目告警），不许静默降级
if [ "$HAVE_WH" = 0 ]; then
  {
    echo ""
    echo "$PROG: !!!!!!!!!!!!!!!!!!!! WARNING: DEGRADED ISOLATION !!!!!!!!!!!!!!!!!!!!"
    echo "$PROG: !! wheelhouse missing or empty: $WHEELHOUSE"
    if [ "$WHEELHOUSE_DEFAULTED" = 1 ]; then
      echo "$PROG: !! this is the DEFAULT path; it lives under gitignored dsm_stage/ and does"
      echo "$PROG: !! NOT travel with a fresh clone -- on any other machine it is necessarily empty."
    fi
    echo "$PROG: !! offline install impossible -> probe falls back to the host interpreter"
    echo "$PROG: !! and reuses its site-packages; ISO_LEVEL is honestly degraded and"
    echo "$PROG: !! --strict-isolation will judge FAIL."
    echo "$PROG: !! build the wheelhouse OUTSIDE the repo first (needs network, one-time):"
    echo "$PROG: !!   $BASEPY -m pip download --only-binary=:all: -d /home/szf/dsm-wheelhouse -r requirements.txt pip setuptools wheel"
    echo "$PROG: !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo ""
  } >&2
fi
if [ "$HAVE_WH" = 1 ]; then
  ENV_MODE="dedicated venv (no system site-packages) installed from local wheelhouse with --no-index"
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
  VPY=$BASEPY
fi
# B1：ISO_LEVEL 由 (wheelhouse 可用) AND (netns 真实生效) 共同决定，
#     任何一条不满足都如实降级，绝不输出 L3-strong（V-14 禁止静默降级）
if [ "$HAVE_WH" = 1 ] && [ "$NETNS_EFFECTIVE" = 1 ]; then
  ISO_LEVEL="L3-strong: fresh clone + netns offline (connectivity self-check confirmed) + dedicated venv from local wheels"
elif [ "$HAVE_WH" = 1 ]; then
  ISO_LEVEL="L2-netns-unavailable: fresh clone + dedicated venv from local wheels (--no-index), but network NOT isolated (netns=$NETNS, probe=$NETNS_PROBE); offline-ness NOT proven"
elif [ "$NETNS_EFFECTIVE" = 1 ]; then
  ISO_LEVEL="L2-wheelhouse-missing: fresh clone + netns offline, but NO offline install (host interpreter + host site-packages reused)"
else
  ISO_LEVEL="L1-weak: fresh clone + host site-packages reused + no netns (offline install NOT achieved, network NOT isolated)"
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

# ---- ④ 同 seed 连跑 N 次，逐次记录（B8：这里比的是**单个 64hex 自等**；
#         多产物逐项自等由第⑤步的 spine pytest 断言承担） -------------------
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

# ---- ⑤ spine 的两连跑断言（同一条判据的 pytest 载体，兼多产物自等） ---------
PYTEST_RC=skip
ASSERT_TAG=skipped
if [ "$RUN_PYTEST" = 1 ]; then
  ( cd "$CLONE" && "${RUNNER[@]}" env PYTHONPATH= PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 \
    "$VPY" -m pytest -q \
    tests/test_integration_spine.py::test_reproducibility_hash_is_identical_across_two_runs \
  ) >"$TMP/pytest.log" 2>&1
  PYTEST_RC=$?
  ASSERT_TAG=pytest
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

# B9：收工前再核一次源 HEAD（整个运行窗口内 HEAD 是否被在飞 lane 前移）
SRC_HEAD_END=$(git -C "$SRC" rev-parse HEAD) || die "git rev-parse HEAD (end) failed"
[ "$SRC_HEAD_END" = "$SRC_HEAD" ] || HEAD_STABLE=no

FAILURES=()
WARNINGS=()
[ "$EQUAL" = 1 ]   || FAILURES+=("hashes differ across $RUNS runs")
[ "$HEXOK" = 1 ]   || FAILURES+=("hash is not 64 lowercase hex chars")
[ "$PYTEST_RC" = skip ] || [ "$PYTEST_RC" = 0 ] || FAILURES+=("spine pytest assertion failed (rc=$PYTEST_RC)")
[ "$EXPECT_RC" = ok ]   || FAILURES+=("hash != --expect value")
[ "$WH_MANIFEST" != FAILED ] || FAILURES+=("wheelhouse sha256 manifest verification FAILED")
if [ "$NETNS" = on ] && [ "$NETNS_PROBE" = LEAK ]; then
  WARNINGS+=("netns connectivity LEAK: pypi.org:443 reachable inside netns; isolation NOT proven")
fi
if [ "$SRC_DIRTY" != 0 ]; then
  WARNINGS+=("source worktree dirty ($SRC_DIRTY file(s)): clone is commit-exact, so the hash and this signoff cover commit $SRC_HEAD7 ONLY; uncommitted changes are out of scope")
fi
if [ "$HEAD_STABLE" != yes ]; then
  WARNINGS+=("src HEAD moved during run ($SRC_HEAD -> $SRC_HEAD_END): RESULT_COMMIT is not the final HEAD; rerun on the final HEAD before claiming signoff")
fi
if [ "$HAVE_WH" = 0 ]; then
  WARNINGS+=("wheelhouse absent: degraded env (host site-packages reused), see the WARNING block above")
fi
if [ "$STRICT_ISO" = 1 ]; then
  case $ISO_LEVEL in L3-strong*) ;; *) FAILURES+=("--strict-isolation: isolation is not L3-strong ($ISO_LEVEL)") ;; esac
  [ "$HEAD_STABLE" = yes ] || FAILURES+=("--strict-isolation: src HEAD moved during run ($SRC_HEAD -> $SRC_HEAD_END)")
fi

T1=$(date +%s)
note ""
note "meta            = $META_LAST"
note "runs            = $RUNS"
note "all_equal       = $EQUAL"
note "isolation_level = $ISO_LEVEL"
note "netns_probe     = $NETNS_PROBE"
note "wh_manifest     = $WH_MANIFEST"
note "dirty_files     = $SRC_DIRTY"
note "head_stable     = $HEAD_STABLE (src_head_end=$SRC_HEAD_END)"
note "assertion       = $ASSERT_TAG (single-hash self-equality: probe runs above; multi-artifact self-equality: spine pytest)"
note "elapsed_seconds = $((T1 - T0))"
note "RESULT_HASH     = $FIRST"
note "RESULT_COMMIT   = $CLONE_HEAD"
for W in ${WARNINGS+"${WARNINGS[@]}"}; do note "WARNING: $W"; done
if [ ${#FAILURES[@]} -eq 0 ]; then
  note "RESULT=PASS HASH=$FIRST COMMIT=$SRC_HEAD7 ELAPSED=$((T1 - T0))s ISOLATION=$ISO_LEVEL DIRTY=$SRC_DIRTY HEAD_STABLE=$HEAD_STABLE ASSERTION=$ASSERT_TAG"
  exit 0
fi
for F in "${FAILURES[@]}"; do note "FAILURE: $F"; done
note "RESULT=FAIL HASH=$FIRST COMMIT=$SRC_HEAD7 ELAPSED=$((T1 - T0))s ISOLATION=$ISO_LEVEL DIRTY=$SRC_DIRTY HEAD_STABLE=$HEAD_STABLE ASSERTION=$ASSERT_TAG"
exit 1