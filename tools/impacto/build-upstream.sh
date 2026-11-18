#!/usr/bin/env bash
# Build a release candidate from the pinned upstream revision plus the audited patch series
# (engine/impacto/patches, locked in source-lock.json). Never install it into the TYN APK.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
META="$ROOT/engine/impacto"
if [[ $(uname -s) != Linux ]]; then
    echo 'This recipe requires Linux and a Linux Android NDK.' >&2
    exit 2
fi
source "$ROOT/tools/impacto/build-tools.sh"
impacto_read_source_lock "$META/source-lock.json" || exit 2

# Keep this route separate from the old patched engine and SDL binary caches.
BUILD=${IMPACTO_UPSTREAM_BUILD_ROOT:-"$ROOT/.impacto-upstream-build/${LOCK[1]}"}
mkdir -p "$BUILD"
BUILD=$(cd "$BUILD" && pwd)
SOURCE="$BUILD/source"
# Serialize complete attempts. A rejected overlapping attempt must not overwrite
# the active build's candidate state. A crash leaves a fail-closed lock directory.
if ! mkdir "$BUILD/.build.lock" 2>/dev/null; then
    echo 'Build root is locked; confirm no build is running before removing a stale .build.lock.' >&2
    exit 2
fi
printf '%s\n' "$$" > "$BUILD/.build.lock/owner"
SOURCE_VALIDATED=0
verify_on_exit() {
    local result=$?
    trap - EXIT
    if [[ $SOURCE_VALIDATED == 1 ]] &&
       ! python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" --report "$BUILD/source-after.json"; then
        result=1
    fi
    if [[ $result != 0 ]]; then
        printf '{"version":1,"status":"build-failed","releaseReady":false}\n' > "$BUILD/candidate/candidate.json"
    fi
    rm -- "$BUILD/.build.lock/owner"
    rmdir "$BUILD/.build.lock"
    exit "$result"
}
mkdir -p "$BUILD/candidate"
trap verify_on_exit EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
printf '{"version":1,"status":"build-in-progress","releaseReady":false}\n' > "$BUILD/candidate/candidate.json"

# Cached FetchContent trees are mutable. Until they have a dedicated source
# audit, require a fresh build root instead of trusting their pinned GIT_TAG.
if [[ -e "$BUILD/build/_deps" || -e "$BUILD/build/CMakeCache.txt" ]]; then
    echo 'Refusing reused FetchContent/CMake inputs; choose a fresh IMPACTO_UPSTREAM_BUILD_ROOT.' >&2
    exit 2
fi
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to Android NDK 28.0.13004108}"
impacto_check_ndk "$META/source-lock.json" "$ANDROID_NDK_HOME"
impacto_clear_git_environment
export GIT_NO_REPLACE_OBJECTS=1
impacto_resolve_build_tools
export VCPKG_ROOT="$BUILD/vcpkg"
export VCPKG_MAX_CONCURRENCY=${VCPKG_MAX_CONCURRENCY:-4}
export VCPKG_DISABLE_METRICS=1
export VCPKG_DEFAULT_BINARY_CACHE="$BUILD/binary-cache"
export VCPKG_BINARY_SOURCES="clear;files,$BUILD/binary-cache,readwrite"
export VCPKG_DOWNLOADS="$BUILD/downloads"
export PATH="${CMAKE%/*}:$PATH"
if [[ ! -f "$BUILD/.upstream-only-v1" ]] &&
   [[ -e "$BUILD/build" || -e "$BUILD/binary-cache" || -e "$BUILD/ports" ]]; then
    echo 'Refusing pre-existing build/cache inputs without an upstream-only recipe marker.' >&2
    echo 'Choose a fresh IMPACTO_UPSTREAM_BUILD_ROOT.' >&2
    exit 2
fi

checkout() {
    local dir=$1 url=$2 rev=$3 patched=${4:-}
    if [[ ! -e "$dir" ]]; then
        git init "$dir"
        git -C "$dir" config core.autocrlf false
        git -C "$dir" remote add origin "$url"
        git -C "$dir" fetch --depth 1 origin "$rev"
        git -C "$dir" checkout --detach "$rev"
    fi
    [[ $(git -C "$dir" rev-parse --show-toplevel) == "$dir" ]] || {
        echo "Not an independent checkout: $dir" >&2; exit 2;
    }
    [[ $(git -C "$dir" remote get-url origin) == "$url" ]] || {
        echo "Unexpected checkout origin: $dir" >&2; exit 2;
    }
    [[ $(git -C "$dir" rev-parse HEAD) == "$rev" ]] || {
        echo "Revision mismatch: choose a fresh IMPACTO_UPSTREAM_BUILD_ROOT ($dir)" >&2; exit 2;
    }
    # The engine source may already carry the series from an interrupted attempt; apply-patches.py
    # below accepts only "pristine" or "exactly pinned + series" and rejects everything else.
    [[ -n $patched ]] || [[ -z $(git -C "$dir" status --porcelain --untracked-files=no) ]] || {
        echo "Modified checkout: $dir" >&2; exit 2;
    }
}
# The trailing `patched` is a positional flag, not a revision: it lets this one checkout already carry the series
# (an interrupted earlier attempt). Every other checkout (vcpkg) is called without it and must be unmodified.
checkout "$SOURCE" "${LOCK[0]}" "${LOCK[1]}" patched
# Verifies the checkout is pristine (or already exactly pinned + series), checks every patch against its
# locked SHA-256, applies the series with `git apply --index`, and records the resulting tree.
python3 "$ROOT/tools/impacto/apply-patches.py" --source "$SOURCE" --report "$BUILD/patches-applied.json"
python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" --report "$BUILD/source-before.json"
SOURCE_VALIDATED=1
checkout "$VCPKG_ROOT" "${LOCK[2]}" "${LOCK[3]}"
mkdir -p "$VCPKG_DEFAULT_BINARY_CACHE" "$VCPKG_DOWNLOADS"
printf 'upstream-only-v1\n' > "$BUILD/.upstream-only-v1"
if [[ $(git -C "$VCPKG_ROOT" rev-parse --is-shallow-repository) == true ]]; then
    git -C "$VCPKG_ROOT" fetch --unshallow origin "${LOCK[3]}"
fi
if [[ ! -x "$VCPKG_ROOT/vcpkg" ]]; then
    "$VCPKG_ROOT/bootstrap-vcpkg.sh" -disableMetrics
fi
impacto_cmake_configure "$SOURCE" "$BUILD/build"
"$CMAKE" --build "$BUILD/build" --parallel "$VCPKG_MAX_CONCURRENCY"
python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" --report "$BUILD/source-after.json"
# Upstream Android install paths point inside its source checkout. Do not install.
# The old package-runtime.py requires a patched SDL namespace; do not use it here.
python3 "$ROOT/tools/impacto/stage-upstream.py" --build-root "$BUILD" --ndk "$ANDROID_NDK_HOME" --build-lock-owner "$$"
