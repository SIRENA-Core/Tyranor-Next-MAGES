#!/usr/bin/env python3
"""Snapshots of the resolved game profiles: catch changes to games that are already ported without their game data.

    python -I tools/impacto/profile-snapshot.py --source <patched checkout> [--update] [profile ...]

Every profile of engine/impacto/profiles.json is loaded the way the engine loads it (gamedefinitions.lua, the
profile's game.lua and everything it includes), with the Lua the engine embeds (vendor/minilua of the checkout, built
with the C compiler `cc`), and its `root` table is expanded to sorted "path = value" lines. tools/impacto/profile-snapshots/<id>.txt keeps, per
top-level section (Sprites, Dialogue, TitleMenu, ...), the SHA-256 and the line count of those lines; the checkout
has to give the same. A change to shared profile files (profiles/common/*.lua, a sheet or layout another profile
includes) shows up in every profile it touches. To see the changed lines, compare with another checkout (e.g. the
previous series applied to a clean checkout): --diff-against <checkout>. When the change is intended, accept it with
--update and commit the snapshots together with the patch.

Enum values print as "Type.Name": the snapshot does not depend on the numbering of the engine's enums. Behaviour that
lives in C++ is not covered: keep such changes behind profile fields or instruction set checks (AGENTS.md).
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent / "profile-snapshot"
SNAPSHOTS = Path(__file__).resolve().parent / "profile-snapshots"
PROFILES = ROOT / "engine/impacto/profiles.json"


def profile_ids():
    return [p["id"] for p in json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]]


def build_runner(source, workdir):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if cc is None:
        raise RuntimeError("no C compiler (cc / gcc / clang) to build the Lua runner")
    exe = Path(workdir) / "luarun"
    subprocess.run([cc, "-O1", "-w", "-I", str(Path(source) / "vendor"), str(HERE / "luarun.c"),
                    str(Path(source) / "vendor/minilua/minilua_impl.c"), "-lm", "-o", str(exe)], check=True)
    return exe


def snapshot(runner, source, profile):
    r = subprocess.run([str(runner), str(HERE / "snapshot.lua"), str(Path(source).resolve()), profile],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError(f"{profile}: {r.stderr.strip()}")
    return r.stdout


def sections(text):
    """'<section> <sha256> <lines>' per top-level key of root, sorted."""
    groups = {}
    for line in text.splitlines():
        key = line.split(" = ", 1)[0].split(".", 1)[0].split("[", 1)[0]
        groups.setdefault(key, []).append(line)
    return "".join(f"{key} {hashlib.sha256(chr(10).join(lines).encode()).hexdigest()} {len(lines)}\n"
                   for key, lines in sorted(groups.items()))


def print_diff(old, new, a, b, out, limit=80):
    diff = list(difflib.unified_diff(old.splitlines(), new.splitlines(), a, b, lineterm="", n=1))
    print("\n".join(diff[:limit] + ([f"... {len(diff) - limit} more lines"] if len(diff) > limit else [])), file=out)


def check(source, profiles, update=False, diff_against=None, out=sys.stdout):
    """Returns the ids whose snapshot differs (or is missing); with update, writes the snapshots instead."""
    differing = []
    with tempfile.TemporaryDirectory() as tmp:
        runner = build_runner(source, tmp)
        for profile in profiles:
            text = snapshot(runner, source, profile)
            summary = sections(text)
            path = SNAPSHOTS / f"{profile}.txt"
            if update:
                SNAPSHOTS.mkdir(exist_ok=True)
                path.write_text(summary, encoding="utf-8", newline="\n")
                continue
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            if old != summary:
                differing.append(profile)
                print_diff(old, summary, f"snapshot/{profile}", f"checkout/{profile}", out)
            if diff_against:
                base = snapshot(runner, diff_against, profile)
                if base != text:
                    print_diff(base, text, f"{diff_against}/{profile}", f"{source}/{profile}", out)
    return differing


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=os.environ.get("IMPACTO_PATCHED_SOURCE"),
                        help="checkout of the pinned revision with the patch series applied")
    parser.add_argument("--update", action="store_true", help="write the snapshots instead of comparing")
    parser.add_argument("--diff-against", metavar="CHECKOUT", help="also print the changed lines against this checkout")
    parser.add_argument("profiles", nargs="*", help="profile ids (default: all of profiles.json)")
    args = parser.parse_args()
    if not args.source:
        parser.error("--source (or IMPACTO_PATCHED_SOURCE) is required")
    profiles = args.profiles or profile_ids()
    differing = check(args.source, profiles, update=args.update, diff_against=args.diff_against)
    if args.update:
        print(f"wrote {len(profiles)} snapshots to {SNAPSHOTS}")
        return 0
    if differing:
        print(f"profile snapshots differ: {', '.join(differing)} (if intended: --update and commit the snapshots)")
        return 1
    print(f"{len(profiles)} profile snapshots unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
