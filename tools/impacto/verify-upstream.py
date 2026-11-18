#!/usr/bin/env python3
"""Require a complete checkout of the locked Impacto revision.

Default mode: the checkout is the pinned revision and pristine (no change at all).
--patched mode: the checkout's HEAD is the pinned revision, and its index and
worktree are exactly the pinned revision plus the audited patch series recorded
in source-lock.json (engine/impacto/patches/).
--series-only: no checkout; only the locked series itself is checked (names, order,
series file, SHA-256 of every patch).

This check never cleans, patches, checks out, or writes into the source tree
(tree objects it needs go to a scratch object directory, never to the checkout's
own object database). Build products and optional reports must live outside
that tree.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_URL = "https://github.com/CommitteeOfZero/impacto.git"

# Repository-local variables listed by `git rev-parse --local-env-vars`, plus
# hook/quarantine locations. Preserve transport/authentication and proxy setup.
GIT_LOCAL_ENV = {
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_OBJECT_DIRECTORY", "GIT_DIR",
    "GIT_WORK_TREE", "GIT_IMPLICIT_WORK_TREE", "GIT_COMMON_DIR", "GIT_INDEX_FILE",
    "GIT_GRAFT_FILE", "GIT_SHALLOW_FILE", "GIT_PREFIX", "GIT_INTERNAL_SUPER_PREFIX",
    "GIT_QUARANTINE_PATH", "GIT_CONFIG", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT",
    "GIT_NO_REPLACE_OBJECTS", "GIT_REPLACE_REF_BASE",
}

PATCH_NAME = re.compile(r"([0-9]{4})-[A-Za-z0-9][A-Za-z0-9._-]*\.patch")
SERIES_FILE = "series"
# Fixed so that user configuration (apply.whitespace=fix) can never alter patch results.
APPLY_OPTIONS = ("--whitespace=nowarn",)


def git_environment():
    return {key: value for key, value in os.environ.items()
            if key.upper() not in GIT_LOCAL_ENV
            and not key.upper().startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))}


def git(source, *arguments, env=None):
    environment = git_environment()
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment.update(env or {})
    result = subprocess.run(
        ["git", "-C", str(source), "--no-optional-locks", *arguments],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace").strip()
                           or f"Git command failed: {arguments[0]}")
    return result.stdout.decode("utf-8", errors="surrogateescape")


def parse_series(text):
    """Series file: one patch name per line; blank lines and `#` comment lines are ignored."""
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def resolve_patch_directory(lock, directory):
    """Absolute patch directory for `patches.directory`; it must stay below the lock's own directory."""
    if not isinstance(directory, str) or not directory:
        raise RuntimeError("patches.directory must be a relative path next to source-lock.json")
    base = Path(lock).resolve().parent
    resolved = (base / directory).resolve()
    if not resolved.is_relative_to(base) or resolved == base:
        raise RuntimeError(f"patches.directory escapes the lock directory: {directory}")
    return resolved


def patch_directory(lock, metadata):
    patches = metadata.get("patches")
    if not isinstance(patches, dict) or not isinstance(patches.get("series"), list):
        raise RuntimeError("source-lock.json has no patches object with a series list")
    return resolve_patch_directory(lock, patches.get("directory")), patches["series"]


def sha256_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_series(lock):
    """The locked patch series, after checking names, order, series file and SHA-256 of every patch."""
    lock = Path(lock)
    metadata = json.loads(lock.read_text(encoding="utf-8"))
    directory, entries = patch_directory(lock, metadata)
    series, previous = [], 0
    for entry in entries:
        name = entry.get("file") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not isinstance(name, str) or not PATCH_NAME.fullmatch(name):
            raise RuntimeError(f"Invalid patch name in source-lock.json: {name!r}")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise RuntimeError(f"Invalid patch SHA-256 in source-lock.json: {name}")
        number = int(name[:4])
        if number <= previous:
            raise RuntimeError(f"Patch numbers must strictly increase: {name}")
        previous = number
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Locked patch is missing or not a regular file: {name}")
        if sha256_file(path) != digest:
            raise RuntimeError(f"Patch SHA-256 differs from source-lock.json: {name}")
        series.append({"file": name, "sha256": digest, "path": path})
    listed = directory / SERIES_FILE
    if not listed.is_file():
        raise RuntimeError(f"Missing patch series file: {listed}")
    if parse_series(listed.read_text(encoding="utf-8")) != [item["file"] for item in series]:
        raise RuntimeError("Patch series file differs from the list in source-lock.json")
    names = {item["file"] for item in series}
    stray = sorted(p.name for p in directory.glob("*.patch") if p.name not in names)
    if stray:
        raise RuntimeError(f"Patch files not listed in source-lock.json: {stray[:8]!r}")
    return series


def describe_series(series):
    return [{"file": item["file"], "sha256": item["sha256"]} for item in series]


@contextmanager
def scratch_objects(source):
    """Redirect new Git objects to a scratch directory while still reading the checkout's own."""
    objects = Path(source) / git(source, "rev-parse", "--git-path", "objects").strip()
    with tempfile.TemporaryDirectory(prefix="impacto-tree-") as temporary:
        temporary = Path(temporary)
        (temporary / "objects").mkdir()
        yield temporary, {"GIT_OBJECT_DIRECTORY": str(temporary / "objects"),
                          "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(objects)}


def expected_tree(source, series, base="HEAD"):
    """Tree of `base` plus the series, computed in a scratch index; the checkout is not touched."""
    with scratch_objects(source) as (temporary, env):
        env = {**env, "GIT_INDEX_FILE": str(temporary / "index")}
        git(source, "read-tree", base, env=env)
        for patch in series:
            try:
                git(source, "apply", "--cached", *APPLY_OPTIONS, "--", str(patch["path"]), env=env)
            except RuntimeError as error:
                raise RuntimeError(f"Patch does not apply: {patch['file']}: {error}") from error
        return git(source, "write-tree", env=env).strip()


def index_tree(source):
    """`git write-tree` of the checkout's real index (fails on unmerged entries); objects go to scratch."""
    with scratch_objects(source) as (_, env):
        return git(source, "write-tree", env=env).strip()


def verify_tree(source, revision, series=None):
    if Path(git(source, "rev-parse", "--show-toplevel").strip()).resolve() != source:
        raise RuntimeError(f"Source must be the checkout root: {source}")
    actual = git(source, "rev-parse", "HEAD").strip()
    if actual != revision:
        raise RuntimeError(f"Revision mismatch: expected {revision}, found {actual}")
    patched_tree = None
    if series is not None:
        # Index == pinned revision + series. The status check below then proves worktree == index
        # and rejects every untracked or ignored file.
        patched_tree = expected_tree(source, series)
        if index_tree(source) != patched_tree:
            raise RuntimeError("Index differs from the pinned revision plus the patch series")

    # Git status intentionally respects skip-worktree and assume-unchanged bits.
    # Reject those bits so sparse/missing or hidden modified inputs cannot pass.
    flags = git(source, "ls-files", "-v", "-z").split("\0")
    hidden = [entry for entry in flags if entry and entry[0] != "H"]
    if hidden:
        raise RuntimeError(f"Sparse or hidden index entries are not allowed: {hidden[:8]!r}")
    status = git(source, "status", "--porcelain=v1", "-z", "--no-renames", "--untracked-files=all",
                 "--ignored=matching", "--ignore-submodules=none")
    entries = [entry for entry in status.split(chr(0)) if entry]
    if series is not None:
        # The series is applied to the index (`git apply --index`), so staged-only entries ("M ", "A ")
        # are expected; the index equals pinned + series (checked above). Anything else is a change on
        # top of it: worktree edits, deletions, untracked ("??") or ignored ("!!") files.
        entries = [entry for entry in entries if entry[1] != " "]
    if entries:
        raise RuntimeError(f"Source checkout is not clean: {entries[:12]!r}")

    submodules = []
    for entry in git(source, "ls-files", "--stage", "-z").split("\0"):
        if not entry:
            continue
        metadata, name = entry.split("\t", 1)
        mode, object_id, stage = metadata.split()
        if stage != "0":
            raise RuntimeError(f"Unmerged index entry: {name}")
        if mode == "160000":
            child = (source / name).resolve()
            if not child.is_relative_to(source):
                raise RuntimeError(f"Submodule escaped source checkout: {name}")
            # Also rejects uninitialized submodules (whose Git root is the parent)
            # and ignored build inputs that top-level status does not enumerate.
            submodules.append({"path": name, **verify_tree(child, object_id)})
    report = {"revision": actual, "tree": git(source, "rev-parse", "HEAD^{tree}").strip(),
              "clean": True, "submodules": submodules}
    if series is not None:
        report.update({"patched": True, "patches": describe_series(series),
                       "patchedTree": patched_tree})
    return report


def verify(source, lock, patched=False):
    source = source.resolve()
    metadata = json.loads(lock.read_text(encoding="utf-8"))
    upstream = metadata["impacto"]
    if upstream.get("url") != UPSTREAM_URL:
        raise RuntimeError(f"Expected official Impacto URL: {UPSTREAM_URL}")
    revision = upstream.get("revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise RuntimeError("Impacto revision must be a full lowercase 40-character Git SHA")
    series = load_series(lock) if patched else None
    return {"version": 1, "url": UPSTREAM_URL, **verify_tree(source, revision, series)}


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import impacto_common
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--lock", type=Path, default=ROOT / "engine/impacto/source-lock.json")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--patched", action="store_true",
                        help="accept pinned revision + the locked patch series instead of a pristine checkout")
    parser.add_argument("--series-only", action="store_true",
                        help="only check the locked series itself (names, order, series file, SHA-256 of every "
                             "patch); needs no --source")
    args = parser.parse_args()
    if args.series_only:
        if args.source or args.patched:
            parser.error("--series-only takes neither --source nor --patched")
        return impacto_common.run_cli(
            lambda: {"version": 1, "seriesOnly": True, "patches": describe_series(load_series(args.lock))},
            failure="Impacto patch series verification failed", report=args.report)
    if not args.source:
        parser.error("--source is required")
    report = args.report.resolve() if args.report else None
    if report and report.is_relative_to(args.source.resolve()):
        parser.error("Report must be outside the source checkout")
    return impacto_common.run_cli(lambda: verify(args.source, args.lock, args.patched),
                                  failure="Impacto source verification failed", report=report)


if __name__ == "__main__":
    sys.exit(main())
