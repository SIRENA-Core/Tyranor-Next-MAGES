#!/usr/bin/env bash
# Source this file; tool resolution has no filesystem or network side effects.
impacto_clear_git_environment() {
    local variables name
    variables=$(git rev-parse --local-env-vars) || return 1
    while IFS= read -r name; do
        [[ -z "$name" ]] || unset "$name"
    done <<< "$variables"
    unset GIT_INTERNAL_SUPER_PREFIX GIT_QUARANTINE_PATH
    # Count/parameters were removed above; remove their now-inactive payload too.
    for name in "${!GIT_CONFIG_KEY_@}" "${!GIT_CONFIG_VALUE_@}"; do
        [[ -z "$name" ]] || unset "$name"
    done
}

impacto_resolve_program() {
    local requested=$1 label=$2 resolved directory name
    if ! resolved=$(command -v -- "$requested") || [[ ! -f "$resolved" || ! -x "$resolved" ]]; then
        printf 'Impacto build: %s executable not found: %s\n' "$label" "$requested" >&2
        return 1
    fi
    directory=${resolved%/*}
    name=${resolved##*/}
    [[ "$directory" != "$resolved" ]] || directory=.
    directory=$(cd -- "$directory" && pwd) || return 1
    printf '%s/%s\n' "$directory" "$name"
}

impacto_resolve_build_tools() {
    CMAKE=$(impacto_resolve_program "${IMPACTO_CMAKE:-cmake}" CMake) || return 1
    if [[ -n "${IMPACTO_NINJA:-}" ]]; then
        NINJA=$(impacto_resolve_program "$IMPACTO_NINJA" Ninja) || return 1
    elif [[ -f "${CMAKE%/*}/ninja" && -x "${CMAKE%/*}/ninja" ]]; then
        NINJA="${CMAKE%/*}/ninja"
    else
        NINJA=$(impacto_resolve_program ninja 'Ninja (set IMPACTO_NINJA or add ninja to PATH)') || return 1
    fi
}

# Reads source-lock.json into the global array LOCK:
#   [0] impacto url  [1] impacto revision  [2] vcpkg url  [3] vcpkg revision  [4] Android NDK revision
# Shared by build-upstream.sh (release) and dev-build.sh so both always parse the lock the same way.
impacto_read_source_lock() {
    readarray -t LOCK < <(python3 - "$1" <<'PY'
import json, re, sys
from pathlib import Path
d = json.loads(Path(sys.argv[1]).read_text())
for name, url in [('impacto', 'https://github.com/CommitteeOfZero/impacto.git'),
                  ('vcpkg', 'https://github.com/microsoft/vcpkg.git')]:
    if d[name]['url'] != url or not re.fullmatch('[0-9a-f]{40}', d[name]['revision']):
        raise SystemExit('Invalid upstream source lock')
    print(url)
    print(d[name]['revision'])
print(d['android']['ndk'])
PY
)
    [[ ${#LOCK[@]} == 5 ]] || { echo 'Unable to read source lock' >&2; return 1; }
}

# impacto_check_ndk <source-lock.json> <ndk home>: the NDK must be the revision the lock pins.
impacto_check_ndk() {
    python3 - "$1" "$2/source.properties" <<'PY'
import json, re, sys
from pathlib import Path
lock = json.loads(Path(sys.argv[1]).read_text())
ndk = Path(sys.argv[2]).read_text()
if not re.search(r'^Pkg\.Revision\s*=\s*' + re.escape(lock['android']['ndk']) + r'\s*$', ndk, re.M):
    raise SystemExit('Android NDK revision differs from source-lock.json')
PY
}

# Upstream's CMake finds Vulkan through the NDK sysroot; ninja also needs it when it re-runs CMake by itself.
impacto_export_vulkan_sdk() {
    export VULKAN_SDK="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/linux-x86_64/sysroot/usr"
}

# impacto_cmake_configure <source dir> <build dir>
# The one CMake configure of the engine, for the release and the dev recipe alike. Needs the caller's environment:
# CMAKE, NINJA (impacto_resolve_build_tools), VCPKG_ROOT, ANDROID_NDK_HOME and META (= <repo>/engine/impacto).
impacto_cmake_configure() {
    local source=$1 build=$2
    impacto_export_vulkan_sdk
    "$CMAKE" -S "$source" -B "$build" -G Ninja \
        -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="$NINJA" \
        -DCMAKE_TOOLCHAIN_FILE="$VCPKG_ROOT/scripts/buildsystems/vcpkg.cmake" \
        -DVCPKG_CHAINLOAD_TOOLCHAIN_FILE="$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake" \
        -DVCPKG_TARGET_TRIPLET=arm64-android-impacto \
        -DVCPKG_OVERLAY_TRIPLETS="$META/triplets" \
        -DVCPKG_OVERLAY_PORTS="$source/portfiles" \
        -DCMAKE_PROJECT_impacto_INCLUDE="$META/host-build/pin-dependencies.cmake" \
        -DTYRANOR_IMPACTO_SOURCE_LOCK="$META/source-lock.json" \
        -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 -DANDROID_STL=c++_static \
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON -DCMAKE_CXX_FLAGS= -DCMAKE_C_FLAGS= \
        -DCMAKE_SHARED_LINKER_FLAGS="-Wl,--build-id=sha1,-z,max-page-size=16384,-z,common-page-size=16384" \
        -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DIMPACTO_GL_DEBUG=OFF -DIMPACTO_WARNINGS=ON
}

# --- dev-build lock -------------------------------------------------------------------------------------------
# Owner file: "<pid> <process start time>" (field 22 of /proc/<pid>/stat). The start time tells a recycled pid
# from the process that really took the lock. Without /proc only the pid is recorded and checked.
impacto_process_start() {
    local stat
    stat=$(cat "/proc/$1/stat" 2>/dev/null) || return 1
    stat=${stat##*) }            # drop "pid (comm) "; what is left starts at field 3 (state)
    # shellcheck disable=SC2086
    set -- $stat
    [[ -n ${20:-} ]] || return 1 # field 22
    printf '%s\n' "${20}"
}

# impacto_lock_acquire <lock dir> [pid]: creates the lock directory and records the owner. If it exists but its
# owner is gone (dead pid, another process under that pid, or - after 10 s - no owner file at all) the lock is
# stale: it is removed with a message and taken. A live owner is left alone and the function returns 1.
impacto_lock_acquire() {
    local lock=$1 pid=${2:-$$} owner owner_pid owner_start now_start age stale moved
    if ! mkdir "$lock" 2>/dev/null; then
        owner=$(cat "$lock/owner" 2>/dev/null) || owner=
        read -r owner_pid owner_start <<< "$owner" || true
        if [[ -z ${owner_pid:-} ]]; then
            age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || date +%s) ))
            (( age > 10 )) || return 1   # another attempt is probably still writing its owner file
            echo "Removing stale build lock without an owner: $lock" >&2
        elif [[ $owner_pid =~ ^[0-9]+$ ]] && kill -0 "$owner_pid" 2>/dev/null &&
             { now_start=$(impacto_process_start "$owner_pid" 2>/dev/null) || now_start=
               [[ -z ${owner_start:-} || -z $now_start || $owner_start == "$now_start" ]]; }; then
            return 1
        else
            echo "Removing stale build lock of dead process ${owner_pid:-?}: $lock" >&2
        fi
        # Rename first: of several cleaners only one wins the atomic rename, and it can check what it took.
        stale="$lock.stale.$$"
        mv -- "$lock" "$stale" 2>/dev/null || return 1
        moved=$(cat "$stale/owner" 2>/dev/null) || moved=
        if [[ $moved != "$owner" ]]; then   # somebody re-created the lock in between: put it back
            mv -- "$stale" "$lock" 2>/dev/null || true
            return 1
        fi
        rm -rf -- "$stale"
        mkdir "$lock" 2>/dev/null || return 1
    fi
    now_start=$(impacto_process_start "$pid" 2>/dev/null) || now_start=
    printf '%s\n' "$pid${now_start:+ $now_start}" > "$lock/owner"
}
