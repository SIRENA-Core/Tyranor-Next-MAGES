#!/usr/bin/env bash
# DEVELOPER FAST PATH - NOT FOR RELEASES. Incrementally builds pinned upstream + the locked patch series so that
# engine patches can be iterated on. The result is staged as a "dev-candidate" (releaseReady:false) that Gradle
# only accepts with -PimpactoDevCandidate=true (and then labels the version "-dev"); release workflows use
# tools/impacto/build-upstream.sh, which insists on a fresh build root and never trusts reused build inputs.
#
# Differences from the release recipe (deliberate, and why the result is never publishable):
#   - one persistent root (IMPACTO_DEV_ROOT, default ~/impacto-dev); CMake/FetchContent/ninja state is reused;
#   - the vcpkg checkout, binary cache and downloads are seeded once by copying them from IMPACTO_DEV_SEED
#     (default ~/impacto-build/upstream, e.g. a finished release-recipe build). The seed is only read;
#   - the source is reset to the pinned revision and the series reapplied only when it is not already exactly
#     pinned + series, so an unchanged series keeps file times and ninja rebuilds only what you changed.
#
#   IMPACTO_DEV_ROOT   persistent dev root (default $HOME/impacto-dev)
#   IMPACTO_DEV_SEED   seed root with source/ vcpkg/ binary-cache/ downloads/ (default $HOME/impacto-build/upstream)
#   IMPACTO_DEV_JOBS   ninja parallel jobs (default min(nproc, 4); the build is memory hungry)
#   VCPKG_MAX_CONCURRENCY  vcpkg parallelism (default 2)
#   IMPACTO_DEV_RECONFIGURE=1  force a CMake configure (otherwise an existing build/build.ninja is reused;
#                      ninja reruns CMake itself when CMake inputs change)
#   ANDROID_NDK_HOME / IMPACTO_CMAKE: default to the setup-linux-tools.sh install under $HOME/impacto-tools
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
META="$ROOT/engine/impacto"
if [[ $(uname -s) != Linux ]]; then
    echo 'This recipe requires Linux and a Linux Android NDK.' >&2
    exit 2
fi
source "$ROOT/tools/impacto/build-tools.sh"
impacto_read_source_lock "$META/source-lock.json" || exit 2
NDK_REV=${LOCK[4]}

DEV=${IMPACTO_DEV_ROOT:-"$HOME/impacto-dev"}
SEED=${IMPACTO_DEV_SEED:-"$HOME/impacto-build/upstream"}
if [[ -e "$DEV" && ! -f "$DEV/.dev-root-v1" ]] && [[ -n $(ls -A "$DEV") ]]; then
    echo "Refusing a non-empty directory that is not a dev root: $DEV" >&2
    exit 2
fi
mkdir -p "$DEV"
DEV=$(cd "$DEV" && pwd)
[[ "$DEV" != "$ROOT" && "$DEV" != "${SEED:-/nonexistent}" ]] || { echo 'The dev root must be its own directory.' >&2; exit 2; }
printf 'impacto-dev-v1\n' > "$DEV/.dev-root-v1"
SOURCE="$DEV/source"
if ! impacto_lock_acquire "$DEV/.build.lock"; then
    echo "Dev root is locked by a running build: $DEV/.build.lock (owner: $(cat "$DEV/.build.lock/owner" 2>/dev/null || echo unknown))" >&2
    exit 2
fi
finish() {
    local result=$?
    trap - EXIT
    if [[ $result != 0 && -d "$DEV/candidate" ]]; then
        printf '{"version":1,"status":"build-failed","releaseReady":false}\n' > "$DEV/candidate/candidate.json" || true
    fi
    rm -f -- "$DEV/.build.lock/owner" || true
    rmdir "$DEV/.build.lock" 2>/dev/null || true
    exit "$result"
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mkdir -p "$DEV/candidate"
printf '{"version":1,"status":"build-in-progress","releaseReady":false}\n' > "$DEV/candidate/candidate.json"

: "${ANDROID_NDK_HOME:=$HOME/impacto-tools/ndk/$NDK_REV}"
export ANDROID_NDK_HOME
if [[ -z "${IMPACTO_CMAKE:-}" && -x "$HOME/impacto-tools/cmake-3.31.1-linux-x86_64/bin/cmake" ]]; then
    export IMPACTO_CMAKE="$HOME/impacto-tools/cmake-3.31.1-linux-x86_64/bin/cmake"
fi
impacto_check_ndk "$META/source-lock.json" "$ANDROID_NDK_HOME"
impacto_clear_git_environment
export GIT_NO_REPLACE_OBJECTS=1
impacto_resolve_build_tools
export VCPKG_ROOT="$DEV/vcpkg"
JOBS=${IMPACTO_DEV_JOBS:-$(( $(nproc) < 4 ? $(nproc) : 4 ))}
export VCPKG_MAX_CONCURRENCY=${VCPKG_MAX_CONCURRENCY:-2}
export VCPKG_DISABLE_METRICS=1
export VCPKG_DEFAULT_BINARY_CACHE="$DEV/binary-cache"
export VCPKG_BINARY_SOURCES="clear;files,$DEV/binary-cache,readwrite"
export VCPKG_DOWNLOADS="$DEV/downloads"
export PATH="${CMAKE%/*}:$PATH"

# Seed a missing directory once: copy from the seed root when present, else fetch from upstream.
seed_git() {
    local name=$1 url=$2 rev=$3
    if [[ ! -e "$DEV/$name" ]]; then
        if [[ -d "$SEED/$name/.git" ]]; then
            # --no-hardlinks: the dev checkout must never share mutable files with the seed.
            if [[ $name == vcpkg ]]; then cp -a "$SEED/$name" "$DEV/$name"; else git clone --no-hardlinks --no-checkout "$SEED/$name" "$DEV/$name"; fi
        else
            git init "$DEV/$name"
            git -C "$DEV/$name" remote add origin "$url"
        fi
        git -C "$DEV/$name" config core.autocrlf false
    fi
    [[ $(git -C "$DEV/$name" rev-parse --show-toplevel) == "$DEV/$name" ]] || {
        echo "Not an independent checkout: $DEV/$name" >&2; exit 2;
    }
    git -C "$DEV/$name" remote set-url origin "$url" 2>/dev/null || git -C "$DEV/$name" remote add origin "$url"
    if ! git -C "$DEV/$name" cat-file -e "$rev^{commit}" 2>/dev/null; then
        git -C "$DEV/$name" fetch --depth 1 origin "$rev"
    fi
}
seed_dir() {
    local name=$1
    if [[ ! -e "$DEV/$name" ]]; then
        if [[ -d "$SEED/$name" ]]; then cp -a "$SEED/$name" "$DEV/$name"; else mkdir -p "$DEV/$name"; fi
    fi
}
seed_git source "${LOCK[0]}" "${LOCK[1]}"
seed_git vcpkg "${LOCK[2]}" "${LOCK[3]}"
seed_dir binary-cache
seed_dir downloads

# vcpkg must sit exactly on its pinned revision (tracked files only; its buildtrees/packages are caches).
git -C "$VCPKG_ROOT" checkout --quiet --detach "${LOCK[3]}"
[[ $(git -C "$VCPKG_ROOT" rev-parse HEAD) == "${LOCK[3]}" ]]
if [[ $(git -C "$VCPKG_ROOT" rev-parse --is-shallow-repository) == true ]]; then
    git -C "$VCPKG_ROOT" fetch --unshallow origin "${LOCK[3]}"
fi
if [[ ! -x "$VCPKG_ROOT/vcpkg" ]]; then
    "$VCPKG_ROOT/bootstrap-vcpkg.sh" -disableMetrics
fi

# Source: keep it as-is when it is already exactly pinned + series; otherwise reset it (this directory is ours
# alone, marked by .dev-root-v1) and apply the series. Patch hashes are checked either way.
if python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" >/dev/null 2>&1; then
    echo 'Source already is the pinned revision plus the series; keeping it for an incremental build.'
else
    git -C "$SOURCE" reset --hard --quiet "${LOCK[1]}"
    git -C "$SOURCE" clean -ffdxq
    python3 "$ROOT/tools/impacto/apply-patches.py" --source "$SOURCE" --report "$DEV/patches-applied.json" >/dev/null
fi
python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" --report "$DEV/source-before.json" >/dev/null

impacto_export_vulkan_sdk
if [[ ${IMPACTO_DEV_RECONFIGURE:-0} == 1 || ! -f "$DEV/build/build.ninja" ]]; then
    impacto_cmake_configure "$SOURCE" "$DEV/build"
fi
if [[ ${IMPACTO_DEV_CONFIGURE_ONLY:-0} == 1 ]]; then
    echo 'Configure succeeded (IMPACTO_DEV_CONFIGURE_ONLY=1): skipping build and staging.'
    printf '{"version":1,"status":"configure-only","releaseReady":false}\n' > "$DEV/candidate/candidate.json"
    exit 0
fi
"$CMAKE" --build "$DEV/build" --parallel "$JOBS"
python3 "$ROOT/tools/impacto/verify-upstream.py" --patched --source "$SOURCE" --report "$DEV/source-after.json" >/dev/null
python3 "$ROOT/tools/impacto/stage-upstream.py" --build-root "$DEV" --ndk "$ANDROID_NDK_HOME" --build-lock-owner "$$" --dev
cat <<EOF
Dev candidate (NOT releasable). Use it with:
  -PimpactoSource=$SOURCE -PimpactoCandidate=$DEV/candidate -PimpactoDevCandidate=true -PimpactoNdk=$ANDROID_NDK_HOME
EOF
