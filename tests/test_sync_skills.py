"""
Offline tests for scripts/sync_skills.py against a local git fixture:
an "upstream" repo with two skills, tagged v1.0.0 and v1.1.0.
"""
import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("sync_skills", REPO_ROOT / "scripts" / "sync_skills.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def sh(*args, cwd):
    return subprocess.run(list(args), cwd=str(cwd), check=True, capture_output=True, text=True).stdout


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = sync.main(list(argv))
    return code, out.getvalue(), err.getvalue()


@unittest.skipIf(shutil.which("git") is None, "git not available")
class TestSyncSkills(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sync-test-"))
        self.up = self.tmp / "upstream"
        self.up.mkdir()
        sh("git", "init", "-q", "-b", "main", cwd=self.up)
        sh("git", "config", "user.email", "t@t", cwd=self.up)
        sh("git", "config", "user.name", "t", cwd=self.up)
        sh("git", "config", "uploadpack.allowAnySHA1InWant", "true", cwd=self.up)
        (self.up / "skills" / "alpha").mkdir(parents=True)
        (self.up / "skills" / "beta").mkdir(parents=True)
        (self.up / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\nlicense: MIT\n---\n# alpha v1\n", encoding="utf-8")
        (self.up / "skills" / "alpha" / "helper.py").write_text("print('v1')\n", encoding="utf-8")
        (self.up / "skills" / "beta" / "SKILL.md").write_text("---\nname: beta\n---\n# beta\n", encoding="utf-8")
        (self.up / "LICENSE.md").write_text("MIT License\n", encoding="utf-8")
        sh("git", "add", "-A", cwd=self.up)
        sh("git", "commit", "-qm", "v1", cwd=self.up)
        sh("git", "tag", "v1.0.0", cwd=self.up)
        self.sha_v1 = sh("git", "rev-parse", "HEAD", cwd=self.up).strip()
        (self.up / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\nlicense: MIT\n---\n# alpha v2\n", encoding="utf-8")
        sh("git", "commit", "-qam", "v2", cwd=self.up)
        sh("git", "tag", "v1.1.0", cwd=self.up)
        self.sha_v2 = sh("git", "rev-parse", "HEAD", cwd=self.up).strip()

        self.vendor = self.tmp / "vendor"
        self.lock = self.tmp / "skills.lock.json"
        self.repo_url = self.up.as_uri()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_lock(self, **overrides):
        src = {"name": "up", "repo": self.repo_url, "ref": "v1.0.0", "path": "skills", "skills": ["alpha"]}
        src.update(overrides)
        self.lock.write_text(json.dumps({"sources": [src]}), encoding="utf-8")

    def lock_src(self):
        return json.loads(self.lock.read_text(encoding="utf-8"))["sources"][0]

    def alpha(self):
        return (self.vendor / "up" / "alpha" / "SKILL.md").read_text(encoding="utf-8")

    def args(self, *extra):
        return ("--lock", str(self.lock), "--vendor-dir", str(self.vendor), *extra)

    # ------------------------------------------------------------------

    def test_sync_at_tag_copies_only_named_skills(self):
        self.write_lock()
        code, out, err = run(*self.args())
        self.assertEqual(code, 0, err)
        self.assertIn("alpha v1", self.alpha())
        self.assertTrue((self.vendor / "up" / "alpha" / "helper.py").exists())
        self.assertFalse((self.vendor / "up" / "beta").exists())
        self.assertEqual((self.vendor / "up" / "LICENSE.upstream").read_text(encoding="utf-8"), "MIT License\n")
        notice = (self.vendor / "up" / "NOTICE.md").read_text(encoding="utf-8")
        self.assertIn("| `alpha` | MIT | `skills/alpha` |", notice)
        self.assertIn(self.sha_v1, notice)
        self.assertEqual(self.lock_src()["resolved"], self.sha_v1)
        self.assertIn("synced", self.lock_src())

    def test_resync_replaces_wholesale(self):
        self.write_lock()
        run(*self.args())
        stray = self.vendor / "up" / "alpha" / "local-edit.txt"
        stray.write_text("should be removed", encoding="utf-8")
        run(*self.args())
        self.assertFalse(stray.exists())

    def test_check_and_update_tag_mode(self):
        self.write_lock()
        run(*self.args())
        code, out, _ = run(*self.args("--check"))
        self.assertEqual(code, 1)
        self.assertIn("pinned v1.0.0", out)
        self.assertIn("latest v1.1.0", out)
        self.assertIn("UPDATE AVAILABLE", out)
        code, out, err = run(*self.args("--update"))
        self.assertEqual(code, 0, err)
        self.assertIn("v1.0.0 -> v1.1.0", out)
        self.assertEqual(self.lock_src()["ref"], "v1.1.0")
        self.assertEqual(self.lock_src()["resolved"], self.sha_v2)
        self.assertIn("alpha v2", self.alpha())
        code, out, _ = run(*self.args("--check"))
        self.assertEqual(code, 0)
        self.assertIn("up to date", out)

    def test_branch_mode_pins_by_resolved_sha(self):
        self.write_lock(ref="main", resolved=self.sha_v1)
        code, _, err = run(*self.args())
        self.assertEqual(code, 0, err)
        self.assertIn("alpha v1", self.alpha())  # not the branch head
        self.assertEqual(self.lock_src()["resolved"], self.sha_v1)
        code, out, _ = run(*self.args("--check"))
        self.assertEqual(code, 1)
        self.assertIn(f"main@{self.sha_v1[:7]}", out)
        self.assertIn(f"main@{self.sha_v2[:7]}", out)
        code, _, err = run(*self.args("--update"))
        self.assertEqual(code, 0, err)
        self.assertEqual(self.lock_src()["resolved"], self.sha_v2)
        self.assertIn("alpha v2", self.alpha())

    def test_branch_mode_without_resolved_takes_head(self):
        self.write_lock(ref="main")
        code, _, err = run(*self.args())
        self.assertEqual(code, 0, err)
        self.assertEqual(self.lock_src()["resolved"], self.sha_v2)

    def test_missing_skill_lists_what_exists(self):
        self.write_lock(skills=["alpha", "gamma"])
        code, _, err = run(*self.args())
        self.assertEqual(code, 1)
        self.assertIn("gamma", err)
        self.assertIn("alpha", err)
        self.assertFalse((self.vendor / "up").exists())

    def test_bad_inputs(self):
        self.write_lock(repo=(self.tmp / "nope").as_uri())
        self.assertEqual(run(*self.args())[0], 1)
        self.write_lock()
        code, _, err = run(*self.args("--source", "other"))
        self.assertEqual(code, 1)
        self.assertIn("unknown source", err)
        self.lock.write_text("{not json", encoding="utf-8")
        self.assertEqual(run(*self.args())[0], 1)
        self.lock.write_text(json.dumps({"sources": [{"name": "x"}]}), encoding="utf-8")
        code, _, err = run(*self.args())
        self.assertIn("missing", err)

    def test_version_ordering(self):
        self.assertGreater(sync.version_key("v2.10.0"), sync.version_key("v2.9.3"))
        self.assertTrue(sync.is_version_tag("2.66.0"))
        self.assertFalse(sync.is_version_tag("main"))
        self.assertFalse(sync.is_version_tag("v2.66.0-rc1"))


class TestRepoLock(unittest.TestCase):
    def test_repo_lock_is_well_formed_and_vendored(self):
        lock = sync.load_lock(sync.DEFAULT_LOCK)
        self.assertTrue(lock["sources"])
        for src in lock["sources"]:
            self.assertTrue(src["resolved"], f"{src['name']} has never been synced")
            for s in src["skills"]:
                self.assertTrue((sync.DEFAULT_VENDOR / src["name"] / s / "SKILL.md").is_file(),
                                f"{src['name']}/{s} is in the lock but not vendored - run sync_skills.py")
            self.assertTrue((sync.DEFAULT_VENDOR / src["name"] / "NOTICE.md").is_file())


if __name__ == "__main__":
    unittest.main()
