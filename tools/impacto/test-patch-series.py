#!/usr/bin/env python3
"""Exercise export-patches.py, apply-patches.py and verify-upstream.py --patched on temporary Git repositories."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parent
UPSTREAM_URL = "https://github.com/CommitteeOfZero/impacto.git"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, TOOLS / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


verifier = load("verify_upstream", "verify-upstream.py")
applier = load("apply_patches", "apply-patches.py")
exporter = load("export_patches", "export-patches.py")


class PatchSeriesTest(unittest.TestCase):
    def setUp(self):
        self.environment = verifier.git_environment()
        temporary = tempfile.TemporaryDirectory(prefix="impacto-series-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.upstream = self.root / "upstream"
        self.upstream.mkdir()
        self.git(self.upstream, "init", "--quiet")
        self.configure(self.upstream)
        (self.upstream / "engine.cpp").write_text("int main() { return 0; }\n", encoding="utf-8", newline="\n")
        (self.upstream / "profiles").mkdir()
        (self.upstream / "profiles/game.lua").write_text("name = 'game'\n", encoding="utf-8", newline="\n")
        (self.upstream / ".gitignore").write_text("build/\n", encoding="utf-8")
        self.commit(self.upstream, "fixture")
        self.revision = self.git(self.upstream, "rev-parse", "HEAD").strip()
        self.lock_dir = self.root / "engine/impacto"
        self.patches = self.lock_dir / "patches"
        self.patches.mkdir(parents=True)
        self.lock = self.lock_dir / "source-lock.json"
        self.write_lock([])
        (self.patches / "series").write_text("# empty\n", encoding="utf-8")
        self.dev = None

    # --- fixtures ---------------------------------------------------------------------------------------------
    def git(self, repo, *args, check=True):
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                                encoding="utf-8", env=self.environment)
        if check and result.returncode:
            raise AssertionError(result.stderr)
        return result.stdout

    def configure(self, repo):
        for key, value in [("user.email", "fixture@example.invalid"), ("user.name", "Patch fixture"),
                           ("core.autocrlf", "false"), ("commit.gpgsign", "false")]:
            self.git(repo, "config", key, value)

    def commit(self, repo, message):
        self.git(repo, "add", "-A")
        self.git(repo, "commit", "--quiet", "-m", message)

    def clone(self, name):
        target = self.root / name
        subprocess.run(["git", "clone", "--quiet", "--no-hardlinks", "--config", "core.autocrlf=false",
                        str(self.upstream), str(target)], check=True, env=self.environment)
        self.git(target, "checkout", "--quiet", "--detach", self.revision)
        return target

    def write_lock(self, series, revision=None):
        self.lock.write_text(json.dumps({
            "version": 1, "impacto": {"url": UPSTREAM_URL, "revision": revision or self.revision},
            "patches": {"directory": "patches", "series": series}}, indent=2) + "\n", encoding="utf-8")

    def patch_branch(self):
        """A patch branch with two commits on top of the pinned revision; returns the dev checkout."""
        dev = self.clone("dev")
        self.configure(dev)
        self.git(dev, "checkout", "--quiet", "-b", "tyn")
        (dev / "engine.cpp").write_text("int main() { return 42; }\n", encoding="utf-8", newline="\n")
        self.commit(dev, "Return 42 from main")
        (dev / "profiles/extra.lua").write_text("name = 'extra'\n", encoding="utf-8", newline="\n")
        (dev / "profiles/game.lua").write_text("name = 'game'\nextra = true\n", encoding="utf-8", newline="\n")
        self.commit(dev, "Add extra profile")
        self.dev = dev
        return dev

    def export(self, dev=None, branch="tyn"):
        return exporter.export(dev or self.dev, self.lock, branch)

    def exported(self):
        self.export(self.patch_branch())
        return self.clone("work")

    def run_tool(self, script, *args):
        return subprocess.run([sys.executable, "-I", str(TOOLS / script), "--lock", str(self.lock), *args],
                              capture_output=True, text=True, encoding="utf-8", env=self.environment)

    def apply_cli(self, source):
        return self.run_tool("apply-patches.py", "--source", str(source))

    def verify_cli(self, source, *extra):
        return self.run_tool("verify-upstream.py", "--source", str(source), *extra)

    def object_files(self, repo):
        return sorted(p.relative_to(repo).as_posix() for p in (repo / ".git/objects").rglob("*") if p.is_file())

    # --- export -----------------------------------------------------------------------------------------------
    def test_export_writes_series_lock_and_stable_patches(self):
        result = self.export(self.patch_branch())
        names = sorted(p.name for p in self.patches.glob("*.patch"))
        self.assertEqual(names, ["0001-Return-42-from-main.patch", "0002-Add-extra-profile.patch"])
        self.assertEqual(verifier.parse_series((self.patches / "series").read_text()), names)
        locked = json.loads(self.lock.read_text())["patches"]
        self.assertEqual(locked["directory"], "patches")
        self.assertEqual([item["file"] for item in locked["series"]], names)
        for item in locked["series"]:
            self.assertEqual(item["sha256"], hashlib.sha256((self.patches / item["file"]).read_bytes()).hexdigest())
        text = (self.patches / names[0]).read_text()
        self.assertTrue(text.startswith("From " + "0" * 40 + " "), "commit ids must be zeroed")
        self.assertNotIn("\n-- \n", text, "no Git version signature")
        self.assertEqual(result["tree"], self.git(self.dev, "rev-parse", "tyn^{tree}").strip())
        before = {name: (self.patches / name).read_bytes() for name in [*names, "series"]}
        lock_text = self.lock.read_bytes()
        self.export()
        self.assertEqual(before, {name: (self.patches / name).read_bytes() for name in [*names, "series"]})
        self.assertEqual(lock_text, self.lock.read_bytes())
        verifier.load_series(self.lock)

    def test_export_with_no_commits_empties_the_series_and_removes_old_patches(self):
        self.export(self.patch_branch())
        self.git(self.dev, "branch", "empty", self.revision)
        self.export(branch="empty")
        self.assertEqual(list(self.patches.glob("*.patch")), [])
        self.assertEqual(json.loads(self.lock.read_text())["patches"]["series"], [])
        self.assertEqual(verifier.load_series(self.lock), [])

    def test_export_rejects_branch_not_based_on_pinned_revision(self):
        dev = self.clone("dev")
        self.configure(dev)
        self.git(dev, "checkout", "--quiet", "--orphan", "unrelated")
        self.commit(dev, "Unrelated history")
        with self.assertRaisesRegex(RuntimeError, "not based on the pinned revision"):
            exporter.export(dev, self.lock, "unrelated")
        self.assertEqual(list(self.patches.glob("*.patch")), [])

    def test_export_rejects_merge_commits(self):
        dev = self.patch_branch()
        self.git(dev, "checkout", "--quiet", "-b", "side", self.revision)
        (dev / "side.txt").write_text("side\n", encoding="utf-8", newline="\n")
        self.commit(dev, "Side change")
        self.git(dev, "checkout", "--quiet", "tyn")
        self.git(dev, "merge", "--quiet", "--no-ff", "-m", "Merge side", "side")
        with self.assertRaisesRegex(RuntimeError, "linear"):
            exporter.export(dev, self.lock, "tyn")

    def test_failed_export_leaves_the_published_series_untouched(self):
        dev = self.patch_branch()
        self.export(dev)
        snapshot = {p.name: p.read_bytes() for p in self.patches.iterdir()}
        lock_text = self.lock.read_bytes()
        (dev / "late.txt").write_text("late" + chr(10), encoding="utf-8", newline=chr(10))
        self.commit(dev, "!!!")  # no ASCII word in the subject: the file name is unusable
        with self.assertRaisesRegex(RuntimeError, "Unusable patch name"):
            self.export(dev)
        self.assertEqual(snapshot, {p.name: p.read_bytes() for p in self.patches.iterdir()})
        self.assertEqual(lock_text, self.lock.read_bytes())

    def test_export_leaves_no_temporary_files_behind(self):
        self.export(self.patch_branch())
        self.assertEqual(sorted(p.name for p in self.patches.iterdir()),
                         ["0001-Return-42-from-main.patch", "0002-Add-extra-profile.patch", "series"])
        self.assertEqual(sorted(p.name for p in self.lock_dir.iterdir()), ["patches", "source-lock.json"])

    def test_series_only_verification_needs_no_checkout(self):
        self.export(self.patch_branch())
        result = self.run_tool("verify-upstream.py", "--series-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["seriesOnly"])
        self.assertEqual(len(report["patches"]), 2)
        patch = self.patches / "0001-Return-42-from-main.patch"
        patch.write_bytes(patch.read_bytes() + bytes([10]))
        self.assertEqual(self.run_tool("verify-upstream.py", "--series-only").returncode, 1)

    # --- apply ------------------------------------------------------------------------------------------------
    def test_apply_produces_the_branch_tree(self):
        work = self.exported()
        result = self.apply_cli(work)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        branch_tree = self.git(self.dev, "rev-parse", "tyn^{tree}").strip()
        self.assertEqual(report["state"], "applied")
        self.assertEqual(report["resultTree"], branch_tree)
        self.assertEqual(report["patchedTree"], branch_tree)
        self.assertEqual(self.git(work, "write-tree").strip(), branch_tree)
        self.assertEqual(self.git(work, "rev-parse", "HEAD").strip(), self.revision)
        self.assertEqual((work / "engine.cpp").read_text(), "int main() { return 42; }\n")
        self.assertEqual(self.git(work, "log", "--oneline").count("\n"), 1, "nothing may be committed")
        self.assertEqual(len(report["patches"]), 2)
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 0)
        self.assertEqual(self.verify_cli(work).returncode, 1, "a patched tree is not pristine")

    def test_apply_is_idempotent_for_exactly_applied_checkouts(self):
        work = self.exported()
        self.assertEqual(self.apply_cli(work).returncode, 0)
        before = (self.git(work, "write-tree"), (work / "engine.cpp").stat().st_mtime_ns)
        second = self.apply_cli(work)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(json.loads(second.stdout)["state"], "already-applied")
        self.assertEqual(before, (self.git(work, "write-tree"), (work / "engine.cpp").stat().st_mtime_ns))

    def test_apply_with_empty_series_is_a_no_op(self):
        work = self.clone("work")
        result = self.apply_cli(work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "no-patches")
        self.assertEqual(self.verify_cli(work).returncode, 0)
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 0)

    def test_apply_rejects_extra_modification_after_application(self):
        work = self.exported()
        self.apply_cli(work)
        (work / "engine.cpp").write_text("tampered\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.apply_cli(work).returncode, 1)
        self.assertEqual((work / "engine.cpp").read_text(), "tampered\n")

    def test_apply_rejects_partially_applied_checkout(self):
        work = self.exported()
        first = verifier.load_series(self.lock)[0]["path"]
        self.git(work, "apply", "--index", str(first))
        before = self.git(work, "write-tree")
        result = self.apply_cli(work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("neither pristine nor", result.stderr)
        self.assertEqual(before, self.git(work, "write-tree"))
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)

    def test_apply_rejects_untracked_and_wrong_revision_checkouts(self):
        work = self.exported()
        (work / "stray.txt").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.apply_cli(work).returncode, 1)
        (work / "stray.txt").unlink()
        self.assertEqual(self.apply_cli(work).returncode, 0)
        other = self.clone("other")
        self.write_lock(json.loads(self.lock.read_text())["patches"]["series"], revision="0" * 40)
        self.assertEqual(self.apply_cli(other).returncode, 1)

    def test_apply_rejects_tampered_patch_before_touching_the_worktree(self):
        work = self.exported()
        patch = self.patches / "0001-Return-42-from-main.patch"
        patch.write_bytes(patch.read_bytes().replace(b"42", b"43"))
        result = self.apply_cli(work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("SHA-256", result.stderr)
        self.assertEqual(self.verify_cli(work).returncode, 0, "worktree must stay pristine")

    def test_apply_rejects_patch_that_does_not_apply_and_leaves_checkout_pristine(self):
        work = self.clone("work")
        bad = ("From " + "0" * 40 + " Mon Sep 17 00:00:00 2001\nFrom: A <a@example.invalid>\n"
               "Date: Thu, 1 Jan 2026 00:00:00 +0000\nSubject: [PATCH] Bad context\n\n---\n"
               " engine.cpp | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)\n\n"
               "diff --git a/engine.cpp b/engine.cpp\nindex 0000000..1111111 100644\n"
               "--- a/engine.cpp\n+++ b/engine.cpp\n@@ -1 +1 @@\n-nothing like the file\n+replacement\n")
        (self.patches / "0001-bad-context.patch").write_text(bad, encoding="utf-8", newline="\n")
        digest = hashlib.sha256((self.patches / "0001-bad-context.patch").read_bytes()).hexdigest()
        (self.patches / "series").write_text("0001-bad-context.patch\n", encoding="utf-8")
        self.write_lock([{"file": "0001-bad-context.patch", "sha256": digest}])
        result = self.apply_cli(work)
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not apply", result.stderr)
        self.assertEqual(self.verify_cli(work).returncode, 0)

    def test_apply_does_not_write_into_a_report_inside_the_source(self):
        work = self.exported()
        result = self.run_tool("apply-patches.py", "--source", str(work), "--report", str(work / "report.json"))
        self.assertEqual(result.returncode, 2)
        self.assertFalse((work / "report.json").exists())

    # --- verify --patched -------------------------------------------------------------------------------------
    def test_patched_verify_rejects_pristine_checkout_when_series_is_not_empty(self):
        work = self.exported()
        self.assertEqual(self.verify_cli(work).returncode, 0)
        result = self.verify_cli(work, "--patched")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Index differs", result.stderr)

    def test_patched_verify_report_lists_series_and_expected_tree(self):
        work = self.exported()
        self.apply_cli(work)
        report = json.loads(self.verify_cli(work, "--patched").stdout)
        self.assertTrue(report["clean"] and report["patched"])
        self.assertEqual(report["patchedTree"], self.git(self.dev, "rev-parse", "tyn^{tree}").strip())
        self.assertEqual(report["tree"], self.git(work, "rev-parse", "HEAD^{tree}").strip())
        self.assertEqual([p["file"] for p in report["patches"]],
                         ["0001-Return-42-from-main.patch", "0002-Add-extra-profile.patch"])
        self.assertNotEqual(report["tree"], report["patchedTree"])

    def test_patched_verify_rejects_unstaged_staged_untracked_and_ignored_changes(self):
        work = self.exported()
        self.apply_cli(work)
        engine = work / "engine.cpp"
        good = engine.read_text()
        engine.write_text("unstaged\n", encoding="utf-8", newline="\n")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)
        self.git(work, "add", "engine.cpp")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)
        engine.write_text(good, encoding="utf-8", newline="\n")
        self.git(work, "add", "engine.cpp")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 0)
        (work / "host.h").write_text("injected\n", encoding="utf-8")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)
        (work / "host.h").unlink()
        (work / "build").mkdir()
        (work / "build/generated.h").write_text("injected\n", encoding="utf-8")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)

    def test_patched_verify_rejects_skip_worktree_and_deleted_inputs(self):
        work = self.exported()
        self.apply_cli(work)
        self.git(work, "update-index", "--skip-worktree", "profiles/extra.lua")
        (work / "profiles/extra.lua").unlink()
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)

    def test_patched_verify_rejects_committed_patch(self):
        work = self.exported()
        self.apply_cli(work)
        self.configure(work)
        self.git(work, "commit", "--quiet", "-m", "committed series")
        result = self.verify_cli(work, "--patched")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Revision mismatch", result.stderr)

    def test_patched_verify_rejects_unlisted_or_missing_series_inputs(self):
        work = self.exported()
        self.apply_cli(work)
        (self.patches / "0003-stray.patch").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)
        (self.patches / "0003-stray.patch").unlink()
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 0)
        series = self.patches / "series"
        original = series.read_text()
        series.write_text("0002-Add-extra-profile.patch\n0001-Return-42-from-main.patch\n", encoding="utf-8")
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)
        series.write_text(original, encoding="utf-8")
        (self.patches / "0002-Add-extra-profile.patch").unlink()
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)

    def test_patched_verify_requires_a_patches_object_in_the_lock(self):
        work = self.clone("work")
        self.lock.write_text(json.dumps({"impacto": {"url": UPSTREAM_URL, "revision": self.revision}}),
                             encoding="utf-8")
        self.assertEqual(self.verify_cli(work).returncode, 0)
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 1)

    def test_patched_verify_does_not_write_into_the_checkout_object_database(self):
        work = self.exported()
        self.apply_cli(work)
        before = self.object_files(work)
        self.assertEqual(self.verify_cli(work, "--patched").returncode, 0)
        self.assertEqual(before, self.object_files(work))

    def test_series_names_and_directory_are_validated(self):
        for bad in ["../0001-x.patch", "0001-x.txt", "1-x.patch", "0001-.patch", "0001-a/b.patch"]:
            self.write_lock([{"file": bad, "sha256": "0" * 64}])
            with self.assertRaisesRegex(RuntimeError, "Invalid patch name"):
                verifier.load_series(self.lock)
        content = b"a" + bytes([10])
        (self.patches / "0001-a.patch").write_bytes(content)
        (self.patches / "0001-b.patch").write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        good = {"file": "0001-a.patch", "sha256": digest}
        self.write_lock([good, {**good, "file": "0001-b.patch"}])
        with self.assertRaisesRegex(RuntimeError, "strictly increase"):
            verifier.load_series(self.lock)
        self.lock.write_text(json.dumps({"patches": {"directory": "..", "series": []}}), encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "escapes"):
            verifier.load_series(self.lock)


class RepositorySeriesTest(unittest.TestCase):
    def test_committed_series_matches_the_lock(self):
        lock = TOOLS.parents[1] / "engine/impacto/source-lock.json"
        series = verifier.load_series(lock)
        names = [item["file"] for item in series]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), len(set(names)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
