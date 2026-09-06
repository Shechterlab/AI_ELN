"""
Tests for scripts/eln.py. Standard library only:

    python3 -m unittest discover -s tests -v

Every test runs against a throwaway root and a throwaway config file, so
nothing here touches ~/.ai_eln.json or the repo's own example vault (except
TestRepoExample, which only reads it).
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("eln", REPO_ROOT / "scripts" / "eln.py")
eln = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eln)


def run(*argv):
    """Run eln.main(argv) capturing (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = eln.main(list(argv))
        except SystemExit as e:  # argparse usage errors / --help
            code = e.code if isinstance(e.code, int) else 1
    return code, out.getvalue(), err.getvalue()


class TempVault(unittest.TestCase):
    """A fresh root + config per test, with AI_ELN_* env cleared."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eln-test-"))
        self.root = self.tmp / "root"
        self.root.mkdir()
        self.config = self.tmp / "config.json"
        self._env = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("AI_ELN_")}
        os.environ["AI_ELN_CONFIG"] = str(self.config)
        os.environ["AI_ELN_ROOT"] = str(self.root)
        os.environ["AI_ELN_INITIALS"] = "TST"
        os.environ["AI_ELN_RESEARCHER"] = "Test Person"

    def tearDown(self):
        for k in list(os.environ):
            if k.startswith("AI_ELN_"):
                del os.environ[k]
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- helpers -----------------------------------------------------------

    def ok(self, *argv):
        code, out, err = run(*argv)
        self.assertEqual(code, 0, f"{argv}\nstdout:\n{out}\nstderr:\n{err}")
        return out, err

    def fail(self, *argv):
        code, out, err = run(*argv)
        self.assertNotEqual(code, 0, f"{argv} unexpectedly succeeded:\n{out}")
        return out, err

    def make_clean_vault(self):
        """Project + protocol + 2 samples + 1 experiment that validates with zero warnings."""
        self.ok("new", "project", "--id", "Proj-A", "--title", "Project A", "--lead", "Test Person")
        self.ok("new", "protocol", "--name", "WesternBlot", "--title", "Western blot")
        self.ok("new", "sample", "--type", "plasmid", "--title", "pFLAG-X", "--source", "in-house",
                "--storage", "Freezer B, box 3")
        self.ok("new", "sample", "--type", "antibody", "--title", "anti-X", "--source", "Sigma S1",
                "--storage", "Fridge 4C")
        out, _ = self.ok("new", "experiment", "--title", "X retention after Y: KCl titration",
                         "--project", "Proj-A", "--protocol", "P_WesternBlot", "--samples", "TSTp0001, TSTa0001",
                         "--notebook", "NB01-001", "--type", "WesternBlot", "--tags", "meeting")
        self.assertIn("Created TSTe0001", out)
        return self.exp_folder("TSTe0001")

    def exp_folder(self, exp_id):
        matches = [p for p in (self.root / "Experiments").iterdir() if p.name.startswith(exp_id)]
        self.assertEqual(len(matches), 1, matches)
        return matches[0]

    def note(self, exp_id):
        return self.exp_folder(exp_id) / "1-notes" / f"{exp_id}.md"

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{old!r} not in {path}")
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def issues(self, *extra):
        code, out, _ = run("validate", *extra)
        return code, out


# ---------------------------------------------------------------------------
# Front matter parsing / formatting
# ---------------------------------------------------------------------------

class TestFrontMatter(unittest.TestCase):
    def test_scalars_lists_empty_comments_quotes(self):
        text = (
            "---\n"
            "type: experiment\n"
            "title: \"A: with colon\"   # trailing comment\n"
            "project: [P1, P2]\n"
            "tags: []\n"
            "empty:\n"
            "quoted_list: ['a, b', c]\n"
            "url: https://x.org/#frag\n"
            "---\n"
            "# body\n"
        )
        fields, body, problems = eln.parse_front_matter(text)
        self.assertEqual(problems, [])
        self.assertEqual(fields["title"], "A: with colon")
        self.assertEqual(fields["project"], ["P1", "P2"])
        self.assertEqual(fields["tags"], [])
        self.assertEqual(fields["empty"], "")
        self.assertEqual(fields["quoted_list"], ["a, b", "c"])
        self.assertEqual(fields["url"], "https://x.org/#frag")  # '#' without a preceding space is not a comment
        self.assertEqual(body.strip(), "# body")

    def test_missing_and_unterminated_header(self):
        self.assertIn("no YAML header", eln.parse_front_matter("# no header\n")[2][0])
        self.assertIn("unterminated", eln.parse_front_matter("---\na: 1\n")[2][0])

    def test_rejects_nesting_block_lists_bad_keys(self):
        fields, _, problems = eln.parse_front_matter("---\nok: 1\n  nested: 2\n- item\nBadKey: x\nnocolon\n---\n")
        self.assertEqual(fields, {"ok": "1"})
        joined = "\n".join(problems)
        for needle in ("indented", "block list", "bad header key", "not 'key: value'"):
            self.assertIn(needle, joined)

    def test_format_roundtrip(self):
        for value in ["plain", "with: colon", "hash # inside", "[looks like list]", "", "  spaced  ",
                      "Freezer B, box 3", 'say "hi"', "back\\slash"]:
            self.assertEqual(eln.parse_value(eln.format_value(value)), value)
        self.assertEqual(eln.parse_value(eln.format_value(["a", "b, c", ""])), ["a", "b, c"])
        self.assertEqual(eln.format_value([]), "[]")
        self.assertEqual(eln.format_value("Freezer B, box 3"), '"Freezer B, box 3"')

    def test_usage_errors_are_exit_code_2(self):
        code, _, err = run("new", "experiment", "--no-such-flag")
        self.assertEqual(code, 2)
        self.assertIn("unrecognized", err)
        code, out, _ = run()
        self.assertEqual(code, 2)
        self.assertIn("usage:", out)

    def test_template_render_keeps_comments_and_quotes(self):
        text = eln.render_template("experiment", {
            "EXPERIMENT_ID": "ABe0001", "TITLE": "T: colon", "RESEARCHER": "R", "PROJECT": "P1, P2",
            "DATE": "2026-01-02", "EXPERIMENT_TYPE": "", "PROTOCOL": "", "SAMPLES": "", "NOTEBOOK_REF": "",
            "RAW_DATA_PATH": "x/y", "RELATED": "", "TAGS": "meeting",
        })
        fields, body, problems = eln.parse_front_matter(text)
        self.assertEqual(problems, [])
        self.assertEqual(fields["title"], "T: colon")
        self.assertEqual(fields["project"], ["P1", "P2"])
        self.assertEqual(fields["tags"], ["meeting"])
        self.assertEqual(fields["experiment_type"], [])
        self.assertIn("# active | complete | paused | abandoned", text)  # inline hint preserved
        self.assertIn("ABe0001_P_", body)  # body placeholders rendered
        self.assertNotIn("{{", text)


# ---------------------------------------------------------------------------
# IDs and slugs
# ---------------------------------------------------------------------------

class TestIds(TempVault):
    def test_slugify(self):
        self.assertEqual(eln.slugify("SNRPB chromatin retention: KCl titration"), "SNRPB-chromatin-retention-KCl-titration")
        self.assertEqual(eln.slugify("  --weird__chars!!  "), "weird-chars")
        long = eln.slugify("word " * 30)
        self.assertLessEqual(len(long), 60)
        self.assertFalse(long.endswith("-"))
        self.assertEqual(len(eln.slugify("a" * 80)), 60)  # no boundary to cut on

    def test_next_experiment_id_counts_folders_and_notes(self):
        self.assertEqual(eln.next_experiment_id(self.root, "TST"), "TSTe0001")
        (self.root / "Experiments" / "TSTe0007_hand-made").mkdir(parents=True)
        self.assertEqual(eln.next_experiment_id(self.root, "TST"), "TSTe0008")
        # a note whose folder name is wrong still counts, via its front matter
        d = self.root / "Experiments" / "misnamed" / "1-notes"
        d.mkdir(parents=True)
        (d / "TSTe0020.md").write_text("---\ntype: experiment\nexperiment_id: TSTe0020\n---\n", encoding="utf-8")
        self.assertEqual(eln.next_experiment_id(self.root, "TST"), "TSTe0021")
        # other initials are a separate namespace
        self.assertEqual(eln.next_experiment_id(self.root, "ABC"), "ABCe0001")

    def test_next_sample_id_per_letter(self):
        self.ok("new", "sample", "--type", "plasmid", "--title", "a")
        self.ok("new", "sample", "--type", "p", "--title", "b")
        self.ok("new", "sample", "--type", "oligo", "--title", "c")
        self.assertEqual(eln.next_sample_id(self.root, "TST", "p"), "TSTp0003")
        self.assertEqual(eln.next_sample_id(self.root, "TST", "i"), "TSTi0002")
        self.assertEqual(eln.next_sample_id(self.root, "TST", "a"), "TSTa0001")


# ---------------------------------------------------------------------------
# new / init / config precedence
# ---------------------------------------------------------------------------

class TestNew(TempVault):
    def test_new_experiment_creates_everything(self):
        folder = self.make_clean_vault()
        self.assertEqual(folder.name, "TSTe0001_X-retention-after-Y-KCl-titration")
        for sub in eln.SUBFOLDERS:
            self.assertTrue((folder / sub).is_dir(), sub)
            readme = (folder / sub / "README.md").read_text(encoding="utf-8")
            self.assertTrue(readme.startswith(f"# {sub}"), sub)  # keeps the folder alive in git
        self.assertIn("TSTe0001_R_", (folder / "5-figures" / "README.md").read_text(encoding="utf-8"))
        note = folder / "1-notes" / "TSTe0001.md"
        fields, body, problems = eln.parse_front_matter(note.read_text(encoding="utf-8"))
        self.assertEqual(problems, [])
        self.assertEqual(fields["experiment_id"], "TSTe0001")
        self.assertEqual(fields["title"], "X retention after Y: KCl titration")
        self.assertEqual(fields["researcher"], "Test Person")
        self.assertEqual(fields["project"], ["Proj-A"])
        self.assertEqual(fields["protocols"], ["P_WesternBlot"])
        self.assertEqual(fields["samples"], ["TSTp0001", "TSTa0001"])
        self.assertEqual(fields["notebook_reference"], "NB01-001")
        self.assertEqual(fields["tags"], ["meeting"])
        self.assertEqual(fields["date_started"], date.today().isoformat())
        self.assertEqual(fields["raw_data_path"], f"Experiments/{folder.name}/2-data_raw")
        self.assertIn("## Objective", body)
        # protocol snapshot copied with the protocol's version date
        snaps = list((folder / "1-notes").glob("TSTe0001_P_WesternBlot_*.md"))
        self.assertEqual(len(snaps), 1)
        self.assertEqual(snaps[0].name, f"TSTe0001_P_WesternBlot_{date.today().strftime('%Y%m%d')}.md")
        # inventory regenerated
        csv_text = (self.root / "Inventory" / "experiments.csv").read_text(encoding="utf-8")
        self.assertIn("TSTe0001,X retention after Y: KCl titration,Test Person,Proj-A,WesternBlot,P_WesternBlot,TSTp0001;TSTa0001,NB01-001", csv_text)

    def test_ids_increment_and_missing_protocol_warns(self):
        self.make_clean_vault()
        out, err = self.ok("new", "experiment", "--title", "second", "--protocol", "P_Nope")
        self.assertIn("Created TSTe0002", out)
        self.assertIn("P_Nope not found", err)
        self.assertEqual(list(self.exp_folder("TSTe0002").glob("1-notes/*_P_*")), [])

    def test_dry_run_creates_nothing(self):
        out, _ = self.ok("new", "experiment", "--title", "dry", "--dry-run")
        self.assertIn("Would create TSTe0001", out)
        self.assertFalse((self.root / "Experiments").exists())
        self.ok("new", "sample", "--type", "gel", "--title", "g", "--dry-run")
        self.assertFalse((self.root / "Samples").exists())

    def test_missing_title_without_interactive_is_an_error(self):
        _, err = self.fail("new", "experiment")
        self.assertIn("--title", err)
        _, err = self.fail("new", "sample", "--title", "x")
        self.assertIn("--type", err)

    def test_duplicate_protocol_and_project_refuse_to_overwrite(self):
        self.ok("new", "protocol", "--name", "WesternBlot")
        _, err = self.fail("new", "protocol", "--name", "P_WesternBlot")
        self.assertIn("already exists", err)
        self.ok("new", "project", "--id", "P1")
        self.fail("new", "project", "--id", "P1")

    def test_bad_inputs(self):
        self.fail("new", "sample", "--type", "unicorn", "--title", "x")
        self.fail("new", "protocol", "--name", "bad name!")
        self.fail("new", "project", "--id", "1-starts-with-digit")
        os.environ["AI_ELN_INITIALS"] = "toolong5"
        self.fail("new", "experiment", "--title", "x")

    def test_protocol_title_derived_from_name(self):
        self.ok("new", "protocol", "--name", "CellularFractionation-KCl")
        fields, _, _ = eln.parse_front_matter((self.root / "Protocols" / "P_CellularFractionation-KCl.md").read_text(encoding="utf-8"))
        self.assertEqual(fields["title"], "Cellular Fractionation KCl")
        self.assertEqual(fields["version"], date.today().isoformat())

    def test_config_precedence_flag_env_file(self):
        self.config.write_text(json.dumps({"initials": "CFG", "researcher": "Config Person"}), encoding="utf-8")
        del os.environ["AI_ELN_INITIALS"]
        del os.environ["AI_ELN_RESEARCHER"]
        out, _ = self.ok("new", "experiment", "--title", "from config")
        self.assertIn("Created CFGe0001", out)
        os.environ["AI_ELN_INITIALS"] = "ENV"
        out, _ = self.ok("new", "experiment", "--title", "from env")
        self.assertIn("Created ENVe0001", out)
        out, _ = self.ok("new", "experiment", "--title", "from flag", "--initials", "flg", "--researcher", "Flag Person")
        self.assertIn("Created FLGe0001", out)
        fields, _, _ = eln.parse_front_matter(self.note("FLGe0001").read_text(encoding="utf-8"))
        self.assertEqual(fields["researcher"], "Flag Person")

    def test_root_precedence(self):
        other = self.tmp / "other"
        other.mkdir()
        self.ok("new", "experiment", "--title", "env root")
        self.assertTrue((self.root / "Experiments").is_dir())
        self.ok("new", "experiment", "--title", "flag root", "--root", str(other))
        self.assertTrue((other / "Experiments").is_dir())
        # --root before the command works too, and is not clobbered by the per-command default
        before = self.tmp / "before"
        self.ok("--root", str(before), "new", "experiment", "--title", "root first")
        self.assertTrue((before / "Experiments").is_dir())
        out, _ = self.ok("--root", str(before), "find", "--ids")
        self.assertEqual(out.split(), ["TSTe0001"])
        del os.environ["AI_ELN_ROOT"]
        cfg_root = self.tmp / "cfg"
        self.config.write_text(json.dumps({"root": str(cfg_root)}), encoding="utf-8")
        self.ok("new", "experiment", "--title", "config root")
        self.assertTrue((cfg_root / "Experiments").is_dir())

    def test_init_writes_config_dirs_and_pointer(self):
        out, _ = self.ok("init", "--yes", "--initials", "abc", "--researcher", "A B", "--root", str(self.root))
        data = json.loads(self.config.read_text(encoding="utf-8"))
        self.assertEqual(data, {"initials": "ABC", "researcher": "A B", "root": str(self.root.resolve())})
        for d in ("Experiments", "Protocols", "Samples", "Projects", "Inventory"):
            self.assertTrue((self.root / d).is_dir(), d)
        pointer = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn(str(REPO_ROOT), pointer)
        # re-running init keeps existing values when flags are omitted
        self.ok("init", "--yes")
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["initials"], "ABC")
        # but with no config and no flags there is nothing to save
        self.config.unlink()
        _, err = self.fail("init", "--yes")
        self.assertIn("initials are required", err)
        self.fail("init", "--yes", "--initials", "toolong5")

    def test_interactive_first_run_then_wizard(self):
        del os.environ["AI_ELN_INITIALS"]
        del os.environ["AI_ELN_RESEARCHER"]
        self.ok("new", "project", "--id", "Proj-A", "--lead", "x")
        answers = iter([
            "jsr", "Jacob Roth",                     # first-run setup
            "My wizard experiment",                   # title
            "Proj-A", "WesternBlot", "", "", "NB09-001", "y",   # project, type, protocol, samples, notebook, meeting?
        ])
        with mock.patch("builtins.input", lambda _prompt="": next(answers)):
            out, _ = self.ok("new", "experiment", "--interactive")
        self.assertIn("Created JSRe0001", out)
        self.assertEqual(json.loads(self.config.read_text(encoding="utf-8"))["initials"], "JSR")
        fields, _, _ = eln.parse_front_matter(self.note("JSRe0001").read_text(encoding="utf-8"))
        self.assertEqual(fields["title"], "My wizard experiment")
        self.assertEqual(fields["project"], ["Proj-A"])
        self.assertEqual(fields["experiment_type"], ["WesternBlot"])
        self.assertEqual(fields["notebook_reference"], "NB09-001")
        self.assertEqual(fields["tags"], ["meeting"])

    def test_interactive_sample_by_number(self):
        answers = iter(["3", "anti-X", "Sigma", "Fridge"])  # 3 = antibody
        with mock.patch("builtins.input", lambda _prompt="": next(answers)):
            out, _ = self.ok("new", "sample", "-i")
        self.assertIn("Created TSTa0001", out)
        fields, _, _ = eln.parse_front_matter((self.root / "Samples" / "TSTa0001.md").read_text(encoding="utf-8"))
        self.assertEqual(fields["sample_type"], "antibody")
        self.assertEqual(fields["storage_location"], "Fridge")


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

class TestValidate(TempVault):
    def test_generated_vault_is_clean_under_strict(self):
        self.make_clean_vault()
        code, out = self.issues("--strict")
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors, 0 warnings", out)

    def test_empty_root(self):
        code, out = self.issues()
        self.assertEqual(code, 0)
        self.assertIn("0 experiments", out)

    def assert_issue(self, level, needle, *extra):
        code, out = self.issues(*extra)
        self.assertIn(needle, out)
        self.assertIn(level, out)
        return code, out

    def test_bad_folder_name(self):
        folder = self.make_clean_vault()
        folder.rename(folder.parent / "TSTe0001 has spaces")
        code, _ = self.assert_issue("ERROR", "does not match {ID}_{slug}")
        self.assertEqual(code, 1)

    def test_missing_subfolder(self):
        folder = self.make_clean_vault()
        shutil.rmtree(folder / "5-figures")
        self.assert_issue("ERROR", "missing subfolder(s): 5-figures")

    def test_missing_note(self):
        folder = self.make_clean_vault()
        (folder / "1-notes" / "TSTe0001.md").unlink()
        self.assert_issue("ERROR", "no note at 1-notes/TSTe0001.md")

    def test_id_mismatch(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "experiment_id: TSTe0001", "experiment_id: TSTe0009")
        self.assert_issue("ERROR", "does not match folder")

    def test_bad_status_and_date(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "status: active", "status: done")
        self.edit(self.note("TSTe0001"), "date_started: ", "date_started: 09/05/2026 ")
        _, out = self.assert_issue("ERROR", "status 'done' is not one of")
        self.assertIn("must be YYYY-MM-DD", out)

    def test_missing_required_field(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "researcher: Test Person", "researcher:")
        self.assert_issue("ERROR", "required field 'researcher'")

    def test_unknown_key_and_missing_section_warn(self):
        self.make_clean_vault()
        note = self.note("TSTe0001")
        self.edit(note, "notebook_reference:", "reseacher_typo: x\nnotebook_reference:")
        self.edit(note, "## Decision", "## Decisions")
        _, out = self.assert_issue("WARN", "unknown header key 'reseacher_typo'")
        self.assertIn("missing the '## Decision' section", out)

    def test_dangling_and_wrong_kind_references_warn(self):
        self.make_clean_vault()
        note = self.note("TSTe0001")
        self.edit(note, "protocols: [P_WesternBlot]", "protocols: [P_WesternBlot, P_Missing]")
        self.edit(note, "related_experiments: []", "related_experiments: [TSTp0001]")
        _, out = self.assert_issue("WARN", "refers to P_Missing, which does not exist")
        self.assertIn("is a sample, not a experiment", out)

    def test_duplicate_id(self):
        folder = self.make_clean_vault()
        shutil.copytree(folder, folder.parent / "TSTe0001_copy")
        self.assert_issue("ERROR", "duplicate ID TSTe0001")

    def test_filename_rule_with_exemptions(self):
        folder = self.make_clean_vault()
        (folder / "5-figures" / "blot.png").write_bytes(b"")                 # WARN
        (folder / "5-figures" / "TSTe0001_R_blot.png").write_bytes(b"")      # ok
        (folder / "5-figures" / "TSTe0001.pdf").write_bytes(b"")             # ok (ID.ext)
        (folder / "3-code" / "README.md").write_text("x", encoding="utf-8")   # exempt
        (folder / "3-code" / ".DS_Store").write_bytes(b"")                   # exempt
        (folder / "2-data_raw" / "Image_0001.tif").write_bytes(b"")          # raw is never checked
        code, out = self.issues()
        self.assertEqual(code, 0, out)  # only warnings
        self.assertIn("5-figures/blot.png", out)
        self.assertIn("should start with TSTe0001_", out)
        for ok_name in ("TSTe0001_R_blot.png", "TSTe0001.pdf", "README.md", "Image_0001.tif"):
            self.assertNotIn(ok_name, out)
        self.assertIn("1 warning", out)

    def test_complete_without_results_warns(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "status: active", "status: complete")
        _, out = self.assert_issue("WARN", "date_completed is empty")
        self.assertIn("'## Results' section is empty", out)
        self.assertIn("'## Interpretation' section is empty", out)

    def test_strict_turns_warnings_into_failure(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "project: [Proj-A]", "project: []")
        code, out = self.issues()
        self.assertEqual(code, 0)
        self.assertIn("'project' is empty", out)
        code, out = self.issues("--strict")
        self.assertEqual(code, 1)
        self.assertIn("strict", out)

    def test_protocol_sample_project_file_rules(self):
        self.make_clean_vault()
        (self.root / "Protocols" / "P_WesternBlot.md").rename(self.root / "Protocols" / "P_Blot.md")
        self.edit(self.root / "Samples" / "TSTp0001.md", "sample_type: plasmid", "sample_type: oligo")
        self.edit(self.root / "Samples" / "TSTa0001.md", "sample_type: antibody", "sample_type: unicorn")
        self.edit(self.root / "Projects" / "Proj-A.md", "status: active", "status: archived")
        code, out = self.issues()
        self.assertEqual(code, 1)
        self.assertIn("filename should be P_WesternBlot.md", out)
        self.assertIn("ID letter 'p' means plasmid, but sample_type is 'oligo'", out)
        self.assertIn("sample_type 'unicorn' is not one of", out)
        self.assertIn("status 'archived' is not one of active | complete | paused", out)

    def test_unparsable_and_non_utf8_notes(self):
        self.make_clean_vault()
        (self.root / "Samples" / "TSTp0001.md").write_text("no header here\n", encoding="utf-8")
        (self.root / "Protocols" / "P_WesternBlot.md").write_bytes(b"\xff\xfe\x00bad")
        _, out = self.assert_issue("ERROR", "no YAML header")
        self.assertIn("not UTF-8", out)

    def test_wrong_type_field(self):
        self.make_clean_vault()
        self.edit(self.note("TSTe0001"), "type: experiment", "type: protocol")
        self.assert_issue("ERROR", "type is 'protocol', expected 'experiment'")

    def test_sync_conflict_copies_are_flagged(self):
        folder = self.make_clean_vault()
        note = folder / "1-notes" / "TSTe0001.md"
        shutil.copyfile(note, folder / "1-notes" / "TSTe0001 (Jordan's conflicted copy 2026-09-06).md")
        shutil.copyfile(self.root / "Inventory" / "experiments.csv",
                        self.root / "Inventory" / "experiments (conflicted copy 2026-09-06).csv")
        code, out = self.issues()
        self.assertEqual(code, 0)  # warnings only
        self.assertIn("sync-conflict copy", out)
        self.assertIn("conflicted copy 2026-09-06).md", out)
        self.assertIn("then re-run index", out)
        # the conflict copy is not mistaken for a second note
        self.assertNotIn("duplicate ID", out)

    def test_index_rewrites_only_when_changed(self):
        self.make_clean_vault()
        out, _ = self.ok("index")
        self.assertIn("Up to date Inventory/experiments.csv", out)
        self.ok("new", "experiment", "--title", "another", "--project", "Proj-A", "--protocol", "P_WesternBlot", "--no-index")
        out, _ = self.ok("index")
        self.assertIn("Wrote Inventory/experiments.csv (2 rows)", out)
        self.assertIn("Up to date Inventory/samples.csv", out)


# ---------------------------------------------------------------------------
# index / find / report / export
# ---------------------------------------------------------------------------

class TestIndexFindReportExport(TempVault):
    def setUp(self):
        super().setUp()
        self.make_clean_vault()
        self.ok("new", "experiment", "--title", "Second one", "--project", "Proj-A", "--protocol", "P_WesternBlot")
        note = self.note("TSTe0002")
        self.edit(note, "status: active", "status: complete")
        self.edit(note, "date_completed:", f"date_completed: {date.today().isoformat()}")
        self.edit(note, "## Results\n", "## Results\n\nBands were brighter.\n")
        self.edit(note, "## Interpretation\n", "## Interpretation\n\nSupports the hypothesis.\n")
        self.ok("new", "experiment", "--title", "Paused thing")
        self.edit(self.note("TSTe0003"), "status: active", "status: paused")
        self.ok("index", "--quiet")

    def test_index_columns_and_derived_usage(self):
        inv = self.root / "Inventory"
        exps = (inv / "experiments.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(exps[0], ",".join(eln.INDEX_COLUMNS["experiments"]))
        self.assertEqual(len(exps), 4)
        samples = (inv / "samples.csv").read_text(encoding="utf-8")
        self.assertIn("TSTp0001,plasmid,pFLAG-X,in-house,\"Freezer B, box 3\"", samples)
        self.assertIn(",TSTe0001\n", samples)  # used_in_experiments derived from the experiment note
        protocols = (inv / "protocols.csv").read_text(encoding="utf-8")
        self.assertIn("P_WesternBlot,Western blot,", protocols)
        self.assertIn("TSTe0001;TSTe0002", protocols)
        projects = (inv / "projects.csv").read_text(encoding="utf-8")
        self.assertIn("Proj-A,Project A,Test Person,active,", projects)
        self.assertIn("TSTe0001;TSTe0002", projects)

    def test_index_is_deterministic(self):
        a = (self.root / "Inventory" / "experiments.csv").read_bytes()
        self.ok("index", "--quiet")
        self.assertEqual(a, (self.root / "Inventory" / "experiments.csv").read_bytes())

    def test_find_filters(self):
        out, _ = self.ok("find", "--status", "active", "--ids")
        self.assertEqual(out.split(), ["TSTe0001"])
        out, _ = self.ok("find", "--project", "proj-a", "--ids")
        self.assertEqual(out.split(), ["TSTe0001", "TSTe0002"])
        out, _ = self.ok("find", "--tag", "meeting", "--ids")
        self.assertEqual(out.split(), ["TSTe0001"])
        out, _ = self.ok("find", "--sample", "TSTa0001", "--ids")
        self.assertEqual(out.split(), ["TSTe0001"])
        out, _ = self.ok("find", "--protocol", "P_WesternBlot", "--ids")
        self.assertEqual(out.split(), ["TSTe0001", "TSTe0002"])
        out, _ = self.ok("find", "--text", "brighter", "--ids")
        self.assertEqual(out.split(), ["TSTe0002"])
        out, _ = self.ok("find", "--kind", "sample", "--text", "flag")
        self.assertIn("TSTp0001\tactive\tplasmid\tpFLAG-X\tSamples/TSTp0001.md", out)
        out, _ = self.ok("find", "--researcher", "test", "--type", "westernblot", "--ids")
        self.assertEqual(out.split(), ["TSTe0001"])
        out, _ = self.ok("find", "--status", "complete", "--json")
        data = json.loads(out)
        self.assertEqual(data[0]["experiment_id"], "TSTe0002")
        self.assertTrue(data[0]["path"].endswith("TSTe0002.md"))
        _, err = self.ok("find", "--status", "abandoned")
        self.assertIn("no matches", err)

    def test_report_sections(self):
        out, _ = self.ok("report")
        self.assertIn("## Flagged for discussion", out)
        self.assertIn("### TSTe0001 - X retention after Y: KCl titration", out)
        self.assertIn("**Objective.** _(not written yet)_", out)
        self.assertIn("| TSTe0001 | X retention", out)
        self.assertNotIn("| TSTe0002 |", out)  # complete, not in the active table
        self.assertIn("**TSTe0002** Second one (Test Person, completed", out)
        self.assertIn("**TSTe0003** Paused thing - paused", out)
        out, _ = self.ok("report", "--days", "0")
        self.assertIn("_None._", out)
        self.ok("report", "--out", str(self.tmp / "brief.md"))
        self.assertTrue((self.tmp / "brief.md").exists())

    def test_report_with_nothing_flagged(self):
        self.edit(self.note("TSTe0001"), "tags: [meeting]", "tags: []")
        out, _ = self.ok("report")
        self.assertIn("Nothing flagged", out)

    def test_export_selection_and_related(self):
        out, err = self.ok("export", "--experiment", "TSTe0001")
        self.assertIn("Exported 1 experiment(s)", err)
        for path in ("1-notes/TSTe0001.md", "Projects/Proj-A.md", "Protocols/P_WesternBlot.md",
                     "Samples/TSTp0001.md", "Samples/TSTa0001.md"):
            self.assertIn(f"{path} ====", out)
        self.assertNotIn("TSTe0002.md ====", out)
        self.assertIn("Cite the experiment ID", out)
        out, _ = self.ok("export", "--experiment", "TSTe0001", "--no-related")
        self.assertEqual(sum(1 for line in out.splitlines() if line.startswith("==== ")), 1)
        out, _ = self.ok("export", "--project", "Proj-A")
        self.assertIn("TSTe0001.md ====", out)
        self.assertIn("TSTe0002.md ====", out)
        self.assertNotIn("TSTe0003.md ====", out)
        out, _ = self.ok("export", "--all", "--out", str(self.tmp / "all.md"))
        self.assertIn("TSTe0003.md ====", (self.tmp / "all.md").read_text(encoding="utf-8"))
        self.fail("export")
        _, err = self.fail("export", "--experiment", "TSTe0099")
        self.assertIn("not found", err)

    def test_export_interactive_defaults_to_active(self):
        with mock.patch("builtins.input", lambda _prompt="": ""):
            out, _ = self.ok("export", "-i")
        self.assertIn("TSTe0001.md ====", out)
        self.assertNotIn("TSTe0002.md ====", out)


# ---------------------------------------------------------------------------
# The repo's own example vault must satisfy its own rules
# ---------------------------------------------------------------------------

class TestRepoExample(unittest.TestCase):
    def test_example_vault_validates_strict(self):
        code, out, _ = run("validate", "--strict", "--root", str(REPO_ROOT))
        self.assertEqual(code, 0, out)
        self.assertIn("0 errors, 0 warnings", out)

    def test_sandbox_validates_strict(self):
        code, out, _ = run("validate", "--strict", "--root", str(REPO_ROOT / "sandbox"))
        self.assertEqual(code, 0, out)
        self.assertIn("7 experiments", out)
        self.assertIn("0 errors, 0 warnings", out)

    def test_templates_parse_and_match_schema(self):
        for kind in eln.KINDS:
            keys = eln.template_keys(kind)
            self.assertIn("type", keys, kind)
            self.assertIn(eln.ID_FIELD[kind], keys, kind)
            for req in eln.REQUIRED[kind]:
                self.assertIn(req, keys, f"{kind} template lacks required key {req}")
            text = eln.template_path(kind).read_text(encoding="utf-8")
            _, body, _ = eln.split_front_matter(text)
            secs = eln.sections(body)
            for name in eln.REQUIRED_SECTIONS[kind]:
                self.assertIn(name, secs, f"{kind} template lacks '## {name}'")

    def test_inventory_in_repo_is_current(self):
        vault = eln.load_vault(REPO_ROOT)
        rows = eln.build_index(vault)
        for name, cols in eln.INDEX_COLUMNS.items():
            path = REPO_ROOT / "Inventory" / f"{name}.csv"
            self.assertTrue(path.exists(), f"{path} missing - run eln.py index")
            buf = io.StringIO()
            import csv as _csv
            w = _csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            for r in rows[name]:
                w.writerow(r)
            self.assertEqual(path.read_text(encoding="utf-8"), buf.getvalue(), f"{path} is stale - run eln.py index")


if __name__ == "__main__":
    unittest.main()
