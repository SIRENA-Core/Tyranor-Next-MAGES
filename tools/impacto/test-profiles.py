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
            # The app recognises games with these rules (read from the installed host), so every profile needs one.
            self.assertIsNotNone(p["detect"], p["id"])
            self.assertTrue(p["detect"]["allOf"])
            for name in p["detect"]["allOf"] + [p["detect"].get("textArchive")] * ("textArchive" in p["detect"]):
                self.assert_entry(name)
            # optional: entries that must not exist (apps that do not know the field ignore it)
            none_of = p["detect"].get("noneOf", [])
            self.assertIsInstance(none_of, list, p["id"])
            for name in none_of:
                self.assert_entry(name)
            self.assertFalse(set(none_of) & set(p["detect"]["allOf"]), p["id"])

    def test_no_two_games_match_the_same_folder(self):
        # The app treats a folder matched by two unrelated profiles as ambiguous and recognises neither. A folder
        # holding exactly the entries of B also matches A when A needs a subset of B's entries and none of A's
        # excluded entries is among them; that only works for language variants of one game.
        profiles = load()
        family = {p["id"]: p.get("variantOf", p["id"]) for p in profiles}
        for a in profiles:
            for b in profiles:
                if a is b or family[a["id"]] == family[b["id"]]:
                    continue
                folder = set(b["detect"]["allOf"]) | {b["detect"].get("textArchive")} - {None}
                da = a["detect"]
                needed = set(da["allOf"]) | {da.get("textArchive")} - {None}
                hit = needed <= folder and not set(da.get("noneOf", [])) & folder
                self.assertFalse(hit, f"a {b['id']} folder also matches {a['id']}")

    def assert_entry(self, name):
        # relative, at most one directory level, no empty / dot segments: the app's scanner looks one level deep
        parts = name.split("/")
        self.assertTrue(1 <= len(parts) <= 2 and all(parts) and not set(parts) & {".", ".."}, name)

    def test_unsupported_layouts_are_well_formed(self):
        data = json.loads(PROFILES.read_text(encoding="utf-8"))
        ids = {p["id"] for p in data["profiles"]}
        layouts = data["unsupportedLayouts"]
        self.assertTrue(layouts)
        self.assertEqual(len({u["id"] for u in layouts}), len(layouts), "duplicate layout id")
        for u in layouts:
            self.assertIn(u["tryProfile"], ids, u["id"])
            # one common archive name is shared with other CRI-based games; ask for at least two
            self.assertGreaterEqual(len(set(u["allOf"])), 2, u["id"])
            for name in u["allOf"]:
                self.assert_entry(name)

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

    def test_profiles_match_their_snapshots(self):
        # Games stay ported without their data at hand: every profile, as the engine resolves it, has to equal its
        # committed snapshot (tools/impacto/profile-snapshot.py; --update after an intended change).
        import importlib.util
        import io
        import shutil
        if not (shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")):
            self.skipTest("no C compiler for the Lua runner")
        spec = importlib.util.spec_from_file_location("profile_snapshot", ROOT / "tools/impacto/profile-snapshot.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = io.StringIO()
        differing = module.check(SOURCE, module.profile_ids(), out=report)
        self.assertEqual(differing, [], report.getvalue())


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if "--source" in arguments:
        index = arguments.index("--source")
        SOURCE = Path(arguments[index + 1])
        del sys.argv[index + 1 : index + 3]
    elif os.environ.get("IMPACTO_PATCHED_SOURCE"):
        SOURCE = Path(os.environ["IMPACTO_PATCHED_SOURCE"])
    unittest.main(verbosity=2)
