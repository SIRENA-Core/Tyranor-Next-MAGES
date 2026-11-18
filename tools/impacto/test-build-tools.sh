#!/usr/bin/env bash
# Focused hermetic tests. No CMake, Ninja, network or Android build is invoked.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
source "$ROOT/tools/impacto/build-tools.sh"
TEST_TEMP=$(mktemp -d)
trap 'rm -rf "$TEST_TEMP"' EXIT
mkdir -p "$TEST_TEMP/sdk" "$TEST_TEMP/standalone" "$TEST_TEMP/path" "$TEST_TEMP/override" "$TEST_TEMP/empty"
for program in sdk/cmake sdk/ninja standalone/cmake path/ninja override/ninja; do
    printf '#!/bin/sh\nexit 0\n' > "$TEST_TEMP/$program"
    chmod +x "$TEST_TEMP/$program"
done
expect() {
    local label=$1 cmake=$2 ninja=$3 search=$4 expected=$5
    local actual
    actual=$(export IMPACTO_CMAKE="$cmake" IMPACTO_NINJA="$ninja" PATH="$search"; impacto_resolve_build_tools; printf '%s' "$NINJA")
    [[ "$actual" == "$expected" ]] || { printf 'FAIL %s: %s\n' "$label" "$actual" >&2; exit 1; }
}
reject() {
    local label=$1 cmake=$2 ninja=$3 search=$4
    if (export IMPACTO_CMAKE="$cmake" IMPACTO_NINJA="$ninja" PATH="$search"; impacto_resolve_build_tools) > "$TEST_TEMP/error" 2>&1; then
        printf 'FAIL %s unexpectedly resolved\n' "$label" >&2; exit 1
    fi
    grep -q 'executable not found' "$TEST_TEMP/error"
}
expect 'explicit override wins' "$TEST_TEMP/sdk/cmake" "$TEST_TEMP/override/ninja" "$TEST_TEMP/empty" "$TEST_TEMP/override/ninja"
expect 'SDK adjacent Ninja' "$TEST_TEMP/sdk/cmake" '' "$TEST_TEMP/path" "$TEST_TEMP/sdk/ninja"
expect 'standalone CMake with PATH Ninja' "$TEST_TEMP/standalone/cmake" '' "$TEST_TEMP/path" "$TEST_TEMP/path/ninja"
expect 'CMake command resolved from PATH' cmake '' "$TEST_TEMP/sdk:$TEST_TEMP/path" "$TEST_TEMP/sdk/ninja"
expect 'Ninja override command resolved from PATH' "$TEST_TEMP/sdk/cmake" ninja "$TEST_TEMP/path" "$TEST_TEMP/path/ninja"
reject 'explicit missing Ninja is not silently replaced' "$TEST_TEMP/sdk/cmake" "$TEST_TEMP/missing" "$TEST_TEMP/path"
reject 'missing Ninja explains setup' "$TEST_TEMP/standalone/cmake" '' "$TEST_TEMP/empty"
reject 'missing CMake' "$TEST_TEMP/missing-cmake" '' "$TEST_TEMP/path"
printf 'PASS: 8 Impacto CMake/Ninja resolution cases\n'

# --- dev-build lock ownership ---
LOCKDIR="$TEST_TEMP/lock"
if impacto_process_start $$ > /dev/null 2>&1; then HAVE_PROC=1; else HAVE_PROC=0; fi
sleep 30 &
LIVE=$!
trap 'kill "$LIVE" 2>/dev/null || true; rm -rf "$TEST_TEMP"' EXIT
impacto_lock_acquire "$LOCKDIR" $$ || { echo 'FAIL: fresh lock not acquired' >&2; exit 1; }
[[ $(cut -d' ' -f1 "$LOCKDIR/owner") == "$$" ]] || { echo 'FAIL: owner pid not recorded' >&2; exit 1; }
# a live owner keeps the lock
if (impacto_lock_acquire "$LOCKDIR" 4242) 2>/dev/null; then echo 'FAIL: live lock was taken over' >&2; exit 1; fi
# dead owner: the stale lock is removed and taken
dead=$(sh -c 'echo $$')
printf '%s\n' "$dead 1" > "$LOCKDIR/owner"
impacto_lock_acquire "$LOCKDIR" $$ 2> "$TEST_TEMP/stale.log" || { echo 'FAIL: stale lock not removed' >&2; exit 1; }
grep -q 'stale build lock' "$TEST_TEMP/stale.log" || { echo 'FAIL: no stale-lock message' >&2; exit 1; }
[[ $(cut -d' ' -f1 "$LOCKDIR/owner") == "$$" ]] || { echo 'FAIL: stale lock owner not replaced' >&2; exit 1; }
# recycled pid: a live process with a different start time is not the owner
if [[ $HAVE_PROC == 1 ]]; then
    printf '%s\n' "$LIVE 1" > "$LOCKDIR/owner"
    impacto_lock_acquire "$LOCKDIR" $$ 2> /dev/null || { echo 'FAIL: recycled pid kept the lock' >&2; exit 1; }
fi
# owner file missing: a young lock is left alone, an old one is stale
rm -f "$LOCKDIR/owner"
if (impacto_lock_acquire "$LOCKDIR" $$) 2>/dev/null; then echo 'FAIL: young ownerless lock was taken' >&2; exit 1; fi
touch -d '2000-01-01' "$LOCKDIR"
impacto_lock_acquire "$LOCKDIR" $$ 2> /dev/null || { echo 'FAIL: old ownerless lock not removed' >&2; exit 1; }
printf 'PASS: Impacto dev-build lock ownership cases\n'
