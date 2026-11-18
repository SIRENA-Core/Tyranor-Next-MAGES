#!/usr/bin/env python3
"""Apply the locked patch series (engine/impacto/patches/) to a pristine pinned Impacto checkout.

Fails closed: the checkout must be the pinned revision and pristine, or already exactly
pinned + series (then nothing is reapplied). Every patch must match its SHA-256 in
source-lock.json. The series is first dry-run in a scratch index, so a series that does
not apply never touches the worktree. Patches are applied with `git apply --index`,
which needs no committer identity and leaves nothing committed.
"""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import impacto_common  # noqa: E402

ROOT = impacto_common.ROOT
verifier = impacto_common.load_verifier()


def rollback(source):
    # Only reached from a verified pristine state, so restoring HEAD loses nothing of the user's.
    verifier.git(source, "read-tree", "--reset", "-u", "HEAD")


def apply_series(source, lock):
    source = source.resolve()
    series = verifier.load_series(lock)
    try:
        verifier.verify(source, lock)
    except RuntimeError as pristine_error:
        try:
            result = verifier.verify(source, lock, patched=True)
        except RuntimeError as patched_error:
            raise RuntimeError("Checkout is neither pristine nor exactly the pinned revision plus the series "
                               f"(pristine check: {pristine_error}; patched check: {patched_error})") from None
        return {**result, "state": "already-applied", "resultTree": verifier.index_tree(source)}
    if series:
        verifier.expected_tree(source, series)  # dry run in a scratch index: fail before touching the worktree
        try:
            for patch in series:
                verifier.git(source, "apply", "--index", *verifier.APPLY_OPTIONS, "--", str(patch["path"]))
        except RuntimeError as error:
            try:
                rollback(source)
            except RuntimeError as restore_error:
                raise RuntimeError(f"{error}; restoring the checkout also failed, discard it: {restore_error}") from None
            raise
    result = verifier.verify(source, lock, patched=True)
    state = "applied" if series else "no-patches"
    return {**result, "state": state, "resultTree": verifier.index_tree(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--lock", type=Path, default=ROOT / "engine/impacto/source-lock.json")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = args.report.resolve() if args.report else None
    if report and report.is_relative_to(args.source.resolve()):
        parser.error("Report must be outside the source checkout")
    return impacto_common.run_cli(lambda: apply_series(args.source, args.lock),
                                  failure="Impacto patch application failed", report=report)


if __name__ == "__main__":
    sys.exit(main())
