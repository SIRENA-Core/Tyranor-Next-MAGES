#!/usr/bin/env python3
"""Check engine/impacto/profiles.json, and (with a patched checkout) that it matches the profiles the engine defines.

    python -I tools/impacto/test-profiles.py [--source <checkout of pinned revision + patch series>]

The checkout can also be given through IMPACTO_PATCHED_SOURCE. Without it the checkout tests are skipped; the
host-side half (ImpactoRequest.PROFILES == profiles.json) is a JVM test in ImpactoRequestTest.
"""
import json
import os
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROFILES = ROOT / "engine/impacto/profiles.json"
SOURCE = None


def load():
    return json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]


class ProfilesJsonTest(unittest.TestCase):
    def test_entries_are_well_formed(self):
        profiles = load()
        ids = [p["id"] for p in profiles]
        self.assertEqual(len(ids), len(set(ids)), "duplicate profile id")
        for p in profiles:
            self.assertRegex(p["id"], r"[a-z0-9]+(-[a-z0-9]+)*")
            self.assertIn(p["source"], {"upstream", "tyn-patch"})
            self.assertTrue(p["name"])
            self.assertIn("language", p)
            if p["detect"] is not None:
                self.assertTrue(p["detect"]["allOf"])
                for name in p["detect"]["allOf"]:
                    self.assertFalse(name.startswith("/") or ".." in name.split("/"), name)

    def test_pc_variants_differ_by_language_and_text_archive(self):
        pc = {p["id"]: p for p in load() if p["id"].startswith("mo6tw-pc")}
        self.assertEqual(set(pc), {"mo6tw-pc", "mo6tw-pc-zhs", "mo6tw-pc-zht"})
        self.assertEqual({k: v["language"] for k, v in pc.items()},
                         {"mo6tw-pc": "ja", "mo6tw-pc-zhs": "zh-Hans", "mo6tw-pc-zht": "zh-Hant"})
        self.assertEqual(len({tuple(v["detect"]["allOf"]) for v in pc.values()}), 1,
                         "variants share one detection; the text archive picks the language")
        self.assertEqual(len({v["detect"]["textArchive"] for v in pc.values()}), 3)
        for p in pc.values():
            self.assertEqual(p["source"], "tyn-patch")


class PatchedSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE is None:
            raise unittest.SkipTest("no patched checkout (--source / IMPACTO_PATCHED_SOURCE)")

    def test_pc_game_lua_dir_equals_folder_name(self):
        for p in load():
            if not p["id"].startswith("mo6tw-pc"):
                continue
            text = (SOURCE / "profiles" / p["id"] / "game.lua").read_text(encoding="utf-8")
            match = re.search(r'root\.Mo6Pc\s*=\s*\{[^}]*\bDir\s*=\s*"([^"]+)"', text)
            self.assertIsNotNone(match, f"{p['id']}: no root.Mo6Pc.Dir")
            self.assertEqual(match.group(1), p["id"])
            archive = re.search(r'\bMes\s*=\s*"([^"]+)"', text)
            self.assertIsNotNone(archive)
            self.assertEqual(f"data/{archive.group(1)}.cpk", p["detect"]["textArchive"])

    def test_every_profile_is_defined_by_the_engine(self):
        definitions = (SOURCE / "gamedefinitions.lua").read_text(encoding="utf-8")
        for p in load():
            self.assertRegex(definitions, r'(?m)^\s*(?:\["%s"\]|%s)\s*=\s*\{' % (re.escape(p["id"]), re.escape(p["id"])),
                             p["id"])
            self.assertTrue((SOURCE / "profiles" / p["id"] / "game.lua").is_file(), p["id"])


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if "--source" in arguments:
        index = arguments.index("--source")
        SOURCE = Path(arguments[index + 1])
        del sys.argv[index + 1 : index + 3]
    elif os.environ.get("IMPACTO_PATCHED_SOURCE"):
        SOURCE = Path(os.environ["IMPACTO_PATCHED_SOURCE"])
    unittest.main(verbosity=2)
