"""
The JavaScript library (docs/app/lib) must do exactly what scripts/eln.py does.

Both tools read and write the same notebook folders, sometimes on the same day, so every test here
runs one operation through Python and through Node and compares the results byte for byte: the files
created, the validator's messages, the index, the brief, the export, the snapshot and the manifest.
The tests are skipped when Node is not installed.
"""
import calendar
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from contextlib import redirect_stderr, redirect_stdout
from datetime import date as real_date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("eln", REPO_ROOT / "scripts" / "eln.py")
eln = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eln)

NODE = shutil.which("node")
TODAY = "2026-10-03"


class FixedDate(real_date):
    @classmethod
    def today(cls):
        return cls.fromisoformat(TODAY)


def js(name, *cases):
    """Run a library function on each argument list in `cases`; return the list of results."""
    out = subprocess.run([NODE, str(REPO_ROOT / "tests" / "js_helper.mjs"), name], input=json.dumps(list(cases)),
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


def tool(root, name, args=None, text=False, initials="", researcher="", ok_codes=(0,)):
    cmd = [NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(root), "--today", TODAY]
    if initials:
        cmd += ["--initials", initials, "--researcher", researcher]
    if text:
        cmd.append("--text")
    cmd += [name, json.dumps(args or {})]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if out.returncode not in ok_codes:
        raise AssertionError(f"{name} exited {out.returncode}: {out.stderr}")
    return out.stdout if text else json.loads(out.stdout)


def run_cli(*argv):
    """scripts/eln.py in-process with no saved settings: (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    saved = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("AI_ELN_")}
    os.environ["AI_ELN_CONFIG"] = os.path.join(tempfile.gettempdir(), "ai-eln-no-such-settings.json")
    try:
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = eln.main(list(argv))
            except SystemExit as e:
                code = e.code
    finally:
        del os.environ["AI_ELN_CONFIG"]
        os.environ.update(saved)
    return code, out.getvalue(), err.getvalue()


def tree(root: Path):
    """{relative path: bytes} for every file under root."""
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def py_validate_text(root: Path, strict=False) -> str:
    vault = eln.load_vault(root)
    buf = io.StringIO()
    with redirect_stdout(buf):
        eln.print_issues(vault, eln.validate_vault(vault), strict)
    return buf.getvalue()


@unittest.skipIf(NODE is None, "node not available")
class ParityCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._date = eln.date
        eln.date = FixedDate
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(lambda: setattr(eln, "date", self._date))

    def sandbox_copy(self, name: str, whose: str = "alex") -> Path:
        """A copy of one of the two sandbox notebooks (Alex's unless Jordan's is asked for)."""
        dst = self.tmp / name
        shutil.copytree(REPO_ROOT / "sandbox" / whose, dst, ignore=shutil.ignore_patterns("__pycache__"))
        return dst

    cli = staticmethod(run_cli)

    @staticmethod
    def cli_env(*argv):
        """scripts/eln.py in-process, keeping the AI_ELN_* environment as the test set it."""
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            try:
                code = eln.main(list(argv))
            except SystemExit as e:
                code = e.code
        return code, out.getvalue(), err.getvalue()

    def assertSameTree(self, a: Path, b: Path):
        ta, tb = tree(a), tree(b)
        self.assertEqual(sorted(ta), sorted(tb))
        for rel in ta:
            if ta[rel] != tb[rel]:
                self.assertEqual(ta[rel].decode("utf-8", "replace"), tb[rel].decode("utf-8", "replace"), rel)


class TestPureFunctions(ParityCase):
    def test_built_in_templates_are_current(self):
        out = subprocess.run([sys.executable, str(REPO_ROOT / "scripts" / "build_js_templates.py"), "--check"],
                             capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_slugify(self):
        titles = ["SNRPB chromatin retention after PRMT5 inhibition", "a: b, c", "  --weird__chars!!  ", "word " * 30,
                  "a" * 80, "FLAG-SNRPB R107K/R111K chromatin retention, n=3 with K107R/K111R revertant", "",
                  "été α-tubulin 37°C", "x" * 60 + "-tail", "-".join(["ab"] * 40)]
        self.assertEqual(js("slugify", *[[t] for t in titles]), [eln.slugify(t) for t in titles])
        self.assertEqual(js("subfolders", [])[0], eln.SUBFOLDERS)

    def test_front_matter_parsing(self):
        cases = [
            "---\ntype: experiment\ntitle: A: B\ntags: [a, \"b, c\", 'd']\nempty:\n---\n\n# Body\n\ntext\n",
            "---\ntitle: \"quoted \\\"inner\\\" \\\\ slash\"\nstatus: active   # active | complete\nurl: http://x/#frag\n---\nbody",
            "no header at all\n",
            "---\nunterminated: yes\n",
            "---\n  indented: x\n- block\nnot key value\nBadKey: 1\ndup: 1\ndup: 2\n# comment\n\nok_key: [ ]\n---\n",
            "---\r\ntitle: crlf\r\nlist: [x,y , z]\r\n---\r\nbody\r\nmore\r\n",
            "---\nsingle: 'it''s'\nhash: a #not comment\nhash2: a # comment\ncolon: a:b\nlead:  spaced  \n---",
            "---\ntitle: café α µM\nlist: [é, \"ü, x\"]\n---\n line sep",
            "",
            "---\n---\n",
            "﻿---\ntitle: bom\n---\n",
        ]
        got = js("parseFrontMatter", *[[c.replace("\r\n", "\n")] for c in cases])
        for case, g in zip(cases, got):
            fields, body, problems = eln.parse_front_matter(case.replace("\r\n", "\n"))
            self.assertEqual(g, {"fields": fields, "body": body, "problems": problems}, repr(case))

    def test_value_formatting(self):
        values = ["", "plain", "a: b", "a #b", "a,b", "[x", "'q", '"q', " lead", "trail ", "ends:", "back\\slash", 'has "q", comma',
                  "#hash", "&amp", "*star", "!bang", "|pipe", ">gt", "%pct", "@at", "`tick", "{brace", "café"]
        self.assertEqual(js("quoteIfNeeded", *[[v] for v in values]), [eln.quote_if_needed(v) for v in values])
        lists = [[], ["a"], ["a", "b, c", " ", ""], ['q"x', "y: z"]]
        self.assertEqual(js("formatValue", *[[v] for v in lists]), [eln.format_value(v) for v in lists])
        texts = ["", "a, b,c", " a ,, b ", "one"]
        self.assertEqual(js("csvItems", *[[t] for t in texts]), [eln.csv_items(t) for t in texts])

    def test_set_header_field(self):
        text = "---\ntype: experiment\nstatus: active            # active | complete | paused | abandoned\ntags: []          # add meeting\ndate_completed:\n---\n\n# T\n\nbody\n"
        for key, value in [("status", "complete"), ("date_completed", "2026-09-01"), ("tags", ["meeting", "a, b"]),
                           ("new_key", "added: value"), ("tags", [])]:
            p = self.tmp / "n.md"
            eln.write_text_lf(p, text)
            eln.set_header_field(p, key, value)
            self.assertEqual(js("setHeaderField", [text, key, value])[0], p.read_text(encoding="utf-8"), key)

    def test_templates_render_the_same(self):
        values = {"EXPERIMENT_ID": "JSRe0001", "TITLE": 'Tricky: title, with "quotes" #1', "RESEARCHER": "Jacob Roth",
                  "PROJECT": "A, B", "DATE": TODAY, "EXPERIMENT_TYPE": "", "PROTOCOL": "P_X", "SAMPLES": "",
                  "NOTEBOOK_REF": "", "RAW_DATA_PATH": "Experiments/x/2-data_raw", "RELATED": "", "TAGS": "meeting"}
        for path in sorted((REPO_ROOT / "templates").glob("*.md")):
            text = path.read_text(encoding="utf-8")
            self.assertEqual(js("renderTemplateText", [text, values])[0], eln.render_template("experiment", values, path=path), path.name)

    def test_markdown(self):
        doc = (REPO_ROOT / "tests" / "data_markdown_cases.md").read_text(encoding="utf-8")
        blocks = doc.split("\n=====\n")
        self.assertGreater(len(blocks), 20)
        for base in ("", "Experiments/JSRe0001_x/1-notes"):
            for link_ids in (True, False):
                got = js("mdToHtml", *[[b, base, link_ids] for b in blocks])
                for block, g in zip(blocks, got):
                    want = eln.md_to_html(block, img_base=base, link_ids=link_ids, img_src=lambda rel: "/file?p=" + rel)
                    self.assertEqual(g, want, block)
        notes = [p.read_text(encoding="utf-8") for p in sorted((REPO_ROOT / "sandbox").rglob("*.md"))]
        got = js("mdToHtml", *[[n, "x/y", True] for n in notes])
        for note, g in zip(notes, got):
            self.assertEqual(g, eln.md_to_html(note, img_base="x/y", link_ids=True, img_src=lambda rel: "/file?p=" + rel))

    def test_sections(self):
        bodies = ["# T\n\n## A\ntext\n\n## B \n\n<!-- hint -->\n\n## C\n- [ ]\n-\n### sub\n", "no sections", "## Only\n", ""]
        self.assertEqual(js("sections", *[[b] for b in bodies]), [[list(kv) for kv in eln.sections(b).items()] for b in bodies])
        texts = ["", "<!-- c -->", "- [ ]\n- \n* ", "### sub\n", "real text", "<!-- a -->\nx", "- item", "#notheader"]
        self.assertEqual(js("sectionIsEmpty", *[[t] for t in texts]), [eln.section_is_empty(t) for t in texts])

    def test_small_text_helpers(self):
        strings = ["plain", "it's", 'say "hi"', "both ' and \"", "tab\there", "nl\nx", "back\\slash", "café", " nbsp", "\x1b"]
        self.assertEqual(js("pyRepr", *[[s] for s in strings]), [repr(s) for s in strings])
        texts = ["", "a", "a\n", "a\n\nb", "\n", "a\r\nb\rc", "a\x0bb\x0cc", "a b c\x85d", "a\x1cb\x1dc\x1ed"]
        self.assertEqual(js("splitlines", *[[t] for t in texts]), [t.splitlines() for t in texts])
        paths = ["", "a/b", "a/./b", "a/../b", "../a", "a/b/../../..", "a//b/", "./x", "a/../../b"]
        self.assertEqual(js("normpath", *[[p] for p in paths]), [os.path.normpath(p).replace("\\", "/") for p in paths])
        dates = ["2026-02-29", "2024-02-29", "2026-13-01", "2026-00-10", "2026-04-31", "0000-01-01", "2026-1-1", "", "2026-12-31"]
        self.assertEqual(js("validDate", *[[d] for d in dates]), [eln._valid_date(d) for d in dates])
        self.assertEqual(js("daysBefore", ["2026-03-01", 30], ["2024-03-01", 1], ["2026-01-01", 1])[0:3],
                         ["2026-01-30", "2024-02-29", "2025-12-31"])

    def test_hashes(self):
        blobs = [b"", b"abc", b"a" * 55, b"a" * 56, b"a" * 63, b"a" * 64, b"a" * 65, bytes(range(256)) * 9, os.urandom(1000)]
        for chunk in (1, 7, 64, 100000):
            got = js("sha256", *[[b.hex(), chunk] for b in blobs])
            self.assertEqual(got, [hashlib.sha256(b).hexdigest() for b in blobs], chunk)
        self.assertEqual(js("crc32", *[[b.hex()] for b in blobs]), [zlib.crc32(b) for b in blobs])
        import base64
        for b, (encoded, back) in zip(blobs, js("base64", *[[b.hex()] for b in blobs])):
            self.assertEqual(encoded, base64.b64encode(b).decode())
            self.assertEqual(back, b.hex())

    def test_csv(self):
        import csv
        cols = ["a", "b", "c"]
        rows = [{"a": "plain", "b": "with, comma", "c": 'with "quote"'}, {"a": "", "b": " spaced ", "c": "semi;colon"},
                {"a": "line\nbreak", "b": "café", "c": ""}]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
        self.assertEqual(js("toCsv", [cols, rows])[0], buf.getvalue())


class TestOperations(ParityCase):
    def build_python(self, root: Path):
        root.mkdir()
        eln.create_project(root, "PRMT5-ChromatinRelease", title="PRMT5: chromatin release", lead="Jacob Roth")
        eln.create_project(root, "Second", tags="a, b")
        eln.create_protocol(root, "WesternBlot", title="Western blot (wet transfer, PVDF)")
        eln.create_protocol(root, "Cellular-Fractionation")
        eln.create_sample(root, "JSR", "plasmid", "pcDNA3-FLAG-SNRPB", source="Addgene #12345, lot 7", storage="Freezer B, box 3, A7")
        eln.create_sample(root, "JSR", "a", "anti-SNRPB (Y12)", source="in-house")
        eln.create_sample(root, "ABCD", "cell-line", "A549")
        eln.create_sample(root, "JSR", "plasmid", "second plasmid")
        eln.create_experiment(root, "JSR", "Jacob Roth", 'SNRPB chromatin retention: KCl titration, "pilot" #1',
                              project="PRMT5-ChromatinRelease", exp_type="WesternBlot, Fractionation",
                              protocol="P_WesternBlot, P_Cellular-Fractionation, P_Missing", samples="JSRp0001, JSRa0001",
                              notebook="NB02-153", tags="meeting")
        eln.create_experiment(root, "JSR", "Jacob Roth", "A plain second experiment with a title that is long enough to be cut on a word boundary somewhere")
        eln.create_experiment(root, "ABCD", "", "!!!", related="JSRe0001", raw_data_path="smb://server/share/run 7")
        eln.create_experiment(root, "JSR", "Jacob Roth", "Third", exp_type="qPCR", project="Second, PRMT5-ChromatinRelease")

    def build_js(self, root: Path):
        root.mkdir()
        who = {"initials": "JSR", "researcher": "Jacob Roth"}
        tool(root, "create_project", {"project_id": "PRMT5-ChromatinRelease", "title": "PRMT5: chromatin release", "lead": "Jacob Roth"})
        tool(root, "create_project", {"project_id": "Second", "tags": "a, b"})
        tool(root, "create_protocol", {"name": "WesternBlot", "title": "Western blot (wet transfer, PVDF)"})
        tool(root, "create_protocol", {"name": "Cellular-Fractionation"})
        tool(root, "create_sample", {"sample_type": "plasmid", "title": "pcDNA3-FLAG-SNRPB", "source": "Addgene #12345, lot 7",
                                     "storage": "Freezer B, box 3, A7", **who})
        tool(root, "create_sample", {"sample_type": "antibody", "title": "anti-SNRPB (Y12)", "source": "in-house", **who})
        tool(root, "create_sample", {"sample_type": "cell-line", "title": "A549", "initials": "ABCD"})
        tool(root, "create_sample", {"sample_type": "plasmid", "title": "second plasmid", **who})
        r = tool(root, "create_experiment", {
            "title": 'SNRPB chromatin retention: KCl titration, "pilot" #1', "project": "PRMT5-ChromatinRelease",
            "exp_type": "WesternBlot, Fractionation", "protocol": "P_WesternBlot, P_Cellular-Fractionation, P_Missing",
            "samples": "JSRp0001, JSRa0001", "notebook": "NB02-153", "tags": "meeting", **who})
        self.assertEqual(r["id"], "JSRe0001")
        self.assertEqual(len(r["extra"]), 2)
        self.assertEqual(len(r["warnings"]), 1)
        tool(root, "create_experiment", {"title": "A plain second experiment with a title that is long enough to be cut on a word boundary somewhere", **who})
        tool(root, "create_experiment", {"title": "!!!", "related": "JSRe0001", "raw_data_path": "smb://server/share/run 7", "initials": "ABCD"})
        tool(root, "create_experiment", {"title": "Third", "exp_type": "qPCR", "project": "Second, PRMT5-ChromatinRelease", **who})

    def test_creating_records_writes_identical_folders(self):
        py, node = self.tmp / "py", self.tmp / "js"
        self.build_python(py)
        self.build_js(node)
        self.assertSameTree(py, node)
        self.assertEqual(py_validate_text(py), tool(node, "check_notebook", text=True, ok_codes=(0, 2)))

    def test_each_tool_can_continue_the_other_tools_notebook(self):
        py = self.tmp / "py"
        self.build_python(py)
        r = tool(py, "create_experiment", {"title": "Made by the page", "initials": "JSR"})
        self.assertEqual(r["id"], "JSRe0004")
        self.assertEqual(eln.create_experiment(py, "JSR", "Jacob Roth", "Made by python again").id, "JSRe0005")
        self.assertEqual(tool(py, "create_sample", {"sample_type": "plasmid", "title": "x", "initials": "JSR"})["id"], "JSRp0003")
        self.assertEqual(py_validate_text(py), tool(py, "check_notebook", text=True, ok_codes=(0, 2)))

    def test_check_on_the_sandbox(self):
        for whose in ("alex", "jordan"):
            root = REPO_ROOT / "sandbox" / whose
            want = py_validate_text(root)
            self.assertIn("0 errors, 0 warnings", want, whose)
            self.assertEqual(want, tool(root, "check_notebook", text=True), whose)

    def test_records_in_someone_elses_notebook(self):
        """Jordan's notes cite Alex's samples and experiments. Those IDs carry initials Jordan's notebook has
        no records for, so they are not reported as missing; a wrong ID with Jordan's own initials still is."""
        py, node = self.sandbox_copy("py", "jordan"), self.sandbox_copy("js", "jordan")
        note = eln.load_vault(py).by_id["JORe0001"]
        self.assertTrue({"ALXc0001", "ALXa0003"} <= set(note.get_list("samples")))
        self.assertEqual(note.get_list("related_experiments"), ["ALXe0002"])
        self.assertEqual(eln.known_initials(py), {"JOR"})
        r_py = eln.create_experiment(py, "JOR", "Jordan Example", "Uses a sample of Alex's", samples="ALXc0002, JORp0009, QQa0001",
                                     related="ALXe0003, JORe0099", protocol="P_WesternBlot", project="PRMT5-ChromatinRelease")
        r_js = tool(node, "create_experiment", {"title": "Uses a sample of Alex's", "samples": "ALXc0002, JORp0009, QQa0001",
                                                 "related": "ALXe0003, JORe0099", "protocol": "P_WesternBlot",
                                                 "project": "PRMT5-ChromatinRelease"})
        self.assertEqual(r_js["id"], "JORe0005", "with no initials given, the owner in notebook.md is used")
        self.assertEqual(r_py.warnings, ["sample JORp0009 is not in Samples/ (check the ID, or create it with New sample)",
                                         "related experiment JORe0099 is not in Experiments/ (check the ID)"])
        self.assertEqual(r_js["warnings"], r_py.warnings)
        self.assertSameTree(py, node)
        want = py_validate_text(py)
        self.assertIn("'samples' refers to JORp0009, which does not exist in Samples/", want)
        self.assertIn("'related_experiments' refers to JORe0099", want)
        for elsewhere in ("ALXc0002", "ALXe0003", "QQa0001"):
            self.assertNotIn(elsewhere + ",", want)
        self.assertIn("0 errors, 2 warnings", want)
        self.assertEqual(want, tool(node, "check_notebook", text=True))
        # in a notebook that does hold ALX records, a missing ALX record is reported as before
        alex = self.sandbox_copy("alex")
        r = eln.create_experiment(alex, "ALX", "Alex Example", "Wrong sample", samples="ALXc0009", protocol="P_WesternBlot",
                                  project="PRMT5-ChromatinRelease")
        self.assertEqual(len(r.warnings), 1)
        self.assertIn("'samples' refers to ALXc0009", py_validate_text(alex))
        self.assertEqual(py_validate_text(alex), tool(alex, "check_notebook", text=True))

    def test_check_reports_the_same_problems(self):
        root = self.sandbox_copy("broken")
        exps = root / "Experiments"
        folders = sorted(p for p in exps.iterdir() if p.is_dir())
        a, b, c, d = folders[0], folders[1], folders[2], folders[3]
        (a / "5-figures" / "misnamed figure.png").write_bytes(b"x")
        (a / "3-code" / ".hidden").write_bytes(b"x")
        (a / "1-notes" / f"{a.name.split('_')[0]} (Alex's conflicted copy 2026-09-01).md").write_text("x", encoding="utf-8")
        shutil.rmtree(b / "4-data_processed")
        note_b = b / "1-notes" / f"{b.name.split('_')[0]}.md"
        text = note_b.read_text(encoding="utf-8")
        text = text.replace("status: complete", "status: finished").replace("date_started: 2026", "date_started: 26")
        text = text.replace("## Results", "## Findings").replace("tags: [", "tagz: [x], tags: [", 1)
        eln.write_text_lf(note_b, text.replace("\n---\n", "\nmystery_key: 1\n  indented: bad\nprotocols: [P_Nope, ALXp0001]\n---\n", 1))
        c.rename(exps / "not an experiment folder")
        note_d = d / "1-notes" / f"{d.name.split('_')[0]}.md"
        note_d.rename(d / "1-notes" / "wrong-name.md")
        (exps / "ZZZe0001_empty").mkdir()
        (exps / "ZZZe0002_binary" / "1-notes").mkdir(parents=True)
        (exps / "ZZZe0002_binary" / "1-notes" / "ZZZe0002.md").write_bytes(b"\xff\xfe not utf8")
        samples = sorted((root / "Samples").glob("*.md"))
        s = samples[0].read_text(encoding="utf-8")
        eln.write_text_lf(samples[0], s.replace("sample_type: ", "sample_type: gel #", 1).replace("storage_location:", "storage_location:  # none", 1))
        shutil.copy(samples[1], root / "Samples" / "Copy-of-sample.md")
        eln.write_text_lf(samples[2], "no header here\n")
        eln.write_text_lf(samples[3], samples[3].read_text(encoding="utf-8").replace("sample_type: ", "sample_type: unicorn-", 1))
        (root / "Inventory" / "experiments (conflicted copy).csv").write_text("x", encoding="utf-8")
        proto = sorted((root / "Protocols").glob("*.md"))[0]
        eln.write_text_lf(proto, proto.read_text(encoding="utf-8").replace("type: protocol", "type: sample").replace("version: 2026", "version: 2026-99", 1))
        proj = sorted((root / "Projects").glob("*.md"))[0]
        proj.rename(root / "Projects" / "Renamed.md")
        want = py_validate_text(root, strict=True)
        self.assertIn("ERROR", want)
        self.assertGreater(want.count("\n"), 30)
        self.assertEqual(tool(root, "check_notebook", {"strict": True}, text=True, ok_codes=(2,)), want)

    def test_index_brief_and_export(self):
        root = self.sandbox_copy("s")
        before = tree(root / "Inventory")
        shutil.rmtree(root / "Inventory")
        result = tool(root, "rebuild_index")
        self.assertTrue(all(f["written"] for f in result["files"]))
        self.assertEqual(tree(root / "Inventory"), before)
        self.assertFalse(any(f["written"] for f in tool(root, "rebuild_index")["files"]))

        vault = eln.load_vault(root)
        for days in (30, 400):
            self.assertEqual(tool(root, "meeting_brief", {"days": days})["markdown"], eln.build_report(vault, days=days))
        for choice, args in [({"all": True}, (None, [], None, True)),
                             ({"status": "active"}, (None, [], "active", False)),
                             ({"project": "prmt5-chromatinrelease", "related": False}, ("prmt5-chromatinrelease", [], None, False)),
                             ({"experiment_ids": ["ALXe0003", "ALXe0002"]}, (None, ["ALXe0003", "ALXe0002"], None, False))]:
            exps = eln.select_for_export(vault, *args)
            want = eln.build_export(vault, exps, related=choice.get("related", True))
            got = tool(root, "export_notes", choice)
            self.assertEqual(got["markdown"], want, choice)
            self.assertEqual(got["experiments"], [e.id for e in exps])
        found = tool(root, "find_notes", {"status": "COMPLETE", "researcher": "alex", "text": "chromatin"})
        self.assertEqual([n["id"] for n in found["notes"]],
                         [n.id for n in eln.find_notes(vault, "experiment", status="COMPLETE", researcher="alex", text="chromatin")])
        self.assertEqual([n["id"] for n in tool(root, "find_notes", {"kind": "sample"})["notes"]],
                         [n.id for n in eln.find_notes(vault, "sample")])

    def test_complete_verify_and_snapshot(self):
        py, node = self.sandbox_copy("py"), self.sandbox_copy("js")
        self.assertEqual(eln.verify_manifest(py / next(p for p in tree(py) if p.endswith("ALXe0002.md")).split("/1-notes")[0], "ALXe0002"), ([], [], []))
        self.assertTrue(tool(node, "verify_files", {"id": "ALXe0002"})["ok"], "the manifest python wrote verifies in javascript")

        with self.assertRaises(eln.ElnError):
            eln.complete_experiment(py, "ALXe0004")
        refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "complete_experiment", '{"id": "ALXe0004"}'],
                                 capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("still empty", refused.stderr)

        for exp, force in (("ALXe0004", True), ("ALXe0001", False), ("ALXe0002", False)):
            r_py = eln.complete_experiment(py, exp, when="2026-09-30", force=force)
            r_js = tool(node, "complete_experiment", {"id": exp, "date": "2026-09-30", "force": force})
            self.assertEqual(r_js["snapshot"], r_py["snapshot"].relative_to(py).as_posix())
            self.assertEqual(r_js["manifest"], r_py["manifest"].relative_to(py).as_posix())
            self.assertEqual(r_js["files"], r_py["files"])
        self.assertSameTree(py, node)

        for root in (py, node):
            folder = next(p for p in (root / "Experiments").iterdir() if p.name.startswith("ALXe0002"))
            (folder / "4-data_processed" / "ALXe0002_chromatin-fraction.csv").write_text("changed\n", encoding="utf-8")
            (folder / "5-figures" / "ALXe0002_extra.txt").write_text("new\n", encoding="utf-8")
            (folder / "3-code" / "README.md").unlink()
        folder = next(p for p in (py / "Experiments").iterdir() if p.name.startswith("ALXe0002"))
        missing, modified, added = eln.verify_manifest(folder, "ALXe0002")
        r = tool(node, "verify_files", {"id": "ALXe0002"}, ok_codes=(2,))["results"][0]
        self.assertEqual((r["missing"], r["modified"], r["added"]), (missing, modified, added))
        self.assertEqual(len(modified) + len(missing) + len(added), 3)
        everything = tool(node, "verify_files", {}, ok_codes=(2,))
        self.assertEqual(everything["drift"], 1)
        self.assertEqual(len(everything["results"]), 5, "every completed experiment in Alex's notebook")

        vault = eln.load_vault(py)
        for nid in ("ALXa0001", "P_WesternBlot", "ALXe0003", "ALXe0006"):
            note = vault.by_id[nid]
            want = eln.render_snapshot_html(vault, note, generated=TODAY)
            path = tool(node, "render_snapshot", {"id": nid})["path"]
            self.assertEqual((node / path).read_text(encoding="utf-8"), want, nid)

    def test_findings_from_the_role_play_stay_fixed(self):
        """Each block is a problem a role-played user found; both tools must now handle it, the same way."""
        py, node = self.sandbox_copy("py"), self.sandbox_copy("js")

        # line breaks in a title, accents in a folder name, a protocol typed without P_
        title = "R\u00e9sum\u00e9 of \u03b1-tubulin\nstatus: complete"
        r_py = eln.create_experiment(py, "ZZ", "Zed", title, protocol="WesternBlot, P_RTqPCR", project="Nope", samples="ALXa0001, ALXz9")
        r_js = tool(node, "create_experiment", {"title": title, "protocol": "WesternBlot, P_RTqPCR", "project": "Nope",
                                                 "samples": "ALXa0001, ALXz9", "initials": "ZZ", "researcher": "Zed"})
        self.assertEqual(r_py.path.parent.parent.name, "ZZe0001_Resume-of-tubulin-status-complete")
        self.assertEqual(r_js["warnings"], r_py.warnings)
        self.assertEqual(len(r_py.warnings), 2)
        fields, _, problems = eln.parse_front_matter(r_py.path.read_text(encoding="utf-8"))
        self.assertEqual((problems, fields["status"], fields["protocols"]), ([], "active", ["P_WesternBlot", "P_RTqPCR"]))
        for bad in ({"project": "two words"},):
            with self.assertRaises(eln.ElnError):
                eln.create_experiment(py, "ZZ", "Zed", "x", **bad)
        for call in (lambda: eln.create_protocol(py, "westernblot"), lambda: eln.create_project(py, "CON"),
                     lambda: eln.create_project(py, "prmt5-chromatinrelease"), lambda: eln.create_protocol(py, "B" * 200)):
            with self.assertRaises(eln.ElnError):
                call()

        # a note saved by Windows Notepad (byte-order mark, CRLF) is still a note
        for root in (py, node):
            note = next((root / "Experiments").glob("ALXe0001_*/1-notes/ALXe0001.md"))
            note.write_bytes(b"\xef\xbb\xbf" + note.read_bytes().replace(b"\n", b"\r\n"))
        self.assertEqual(eln.load_vault(py).by_id["ALXe0001"].get("status"), "complete")
        self.assertEqual(tool(node, "read_note", {"id": "ALXe0001"})["fields"]["status"], "complete")

        # sync copies under every name the services use; lock files are ignored
        for root in (py, node):
            folder = next(p for p in (root / "Experiments").iterdir() if p.name.startswith("ALXe0003"))
            for name in ("1-notes/ALXe0003-DESKTOP-AB12CD3.md", "1-notes/ALXe0003 (1).md", "5-figures/ALXe0003_fig (Case Conflict).png",
                         "2-data_raw/scan (1).tif", "3-code/~$ALXe0003_notes.docx", "2-data_raw/y.crswap"):
                (folder / name).write_text("x", encoding="utf-8")
            (root / "Inventory" / "samples (1).csv").write_text("x", encoding="utf-8")
            (root / "Projects" / "~$lock.md").write_text("x", encoding="utf-8")
            (root / "Experiments" / "ZZe0009_half-synced" / "1-notes").mkdir(parents=True)
        want = py_validate_text(py)
        self.assertEqual(tool(node, "check_notebook", text=True, ok_codes=(2,)), want)
        self.assertEqual(want.count("copy made by a sync service"), 3)
        self.assertEqual(want.count("copy of a generated file"), 1)
        self.assertNotIn("scan (1).tif", want)
        self.assertNotIn("~$", want)
        self.assertIn("wait for the sync to finish", want)

        # searching takes words in any order; the brief keeps tables and figures usable
        vault = eln.load_vault(py)
        self.assertEqual([n["id"] for n in tool(node, "find_notes", {"text": "retention chromatin SNRPB"})["notes"]],
                         [n.id for n in eln.find_notes(vault, "experiment", text="retention chromatin SNRPB")])
        self.assertGreater(len(eln.find_notes(vault, "experiment", text="retention chromatin SNRPB")), 2)
        for root in (py, node):
            note = next((root / "Experiments").glob("ALXe0004_*/1-notes/ALXe0004.md"))
            text = note.read_text(encoding="utf-8").replace("## Results\n", "## Results\n\n| lane | signal |\n|---|---|\n| 1 | 2.0 |\n\n![blot](../5-figures/ALXe0004_R_blot.png) and `_R_` stays code\n", 1)
            eln.write_text_lf(note, text)
        brief = eln.build_report(eln.load_vault(py))
        self.assertEqual(tool(node, "meeting_brief")["markdown"], brief)
        self.assertIn("**Results.**\n\n| lane | signal |", brief)
        self.assertIn("](../Experiments/ALXe0004_", brief)
        self.assertIn("<table>", eln.md_to_html(brief))
        self.assertEqual(js("mdToHtml", ["`_R_` and _i_ and `a*b*c`", "", False])[0], "<p><code>_R_</code> and <i>i</i> and <code>a*b*c</code></p>")
        self.assertEqual(eln.md_to_html("`_R_` and _i_ and `a*b*c`", link_ids=False), "<p><code>_R_</code> and <i>i</i> and <code>a*b*c</code></p>")

        # completing again keeps the completion date and says what changed since
        for root in (py, node):
            folder = next(p for p in (root / "Experiments").iterdir() if p.name.startswith("ALXe0002"))
            (folder / "4-data_processed" / "ALXe0002_late.csv").write_text("a\n", encoding="utf-8")
        r_py = eln.complete_experiment(py, "ALXe0002")
        r_js = tool(node, "complete_experiment", {"id": "ALXe0002"})
        self.assertEqual(eln.load_vault(py).by_id["ALXe0002"].get("date_completed"), "2026-07-08")
        self.assertEqual(r_js["warnings"], r_py["warnings"])
        self.assertIn("added 4-data_processed/ALXe0002_late.csv", r_py["warnings"][0])
        self.assertEqual(len(list((py / "Experiments").glob("ALXe0002_*/1-notes/*_snapshot_*.html"))), 1)

        # a manifest that was damaged does not verify; names ending in a space survive
        for root in (py, node):
            folder = next(p for p in (root / "Experiments").iterdir() if p.name.startswith("ALXe0002"))
            with open(folder / "1-notes" / "ALXe0002_MANIFEST.sha256", "a", encoding="utf-8") as f:
                f.write("garbage line\n")
        folder = next(p for p in (py / "Experiments").iterdir() if p.name.startswith("ALXe0002"))
        with self.assertRaises(eln.ElnError):
            eln.verify_manifest(folder, "ALXe0002")
        damaged = tool(node, "verify_files", {"id": "ALXe0002"}, ok_codes=(2,))["results"][0]
        self.assertIn("damaged", damaged["error"])

        # the two notebooks are still the same files
        for root in (py, node):
            for p in list(root.rglob("*MANIFEST.sha256")):
                pass
        self.assertSameTree(py, node)

    def test_notebook_md_remembers_the_last_ids(self):
        py, node = self.tmp / "py", self.tmp / "js"
        for root in (py, node):
            root.mkdir()
        a_py = eln.create_experiment(py, "ZZ", "Zed Zed", "first")
        a_js = tool(node, "create_experiment", {"title": "first", "initials": "ZZ", "researcher": "Zed Zed"})
        eln.create_sample(py, "ZZ", "antibody", "ab one")
        tool(node, "create_sample", {"sample_type": "antibody", "title": "ab one", "initials": "ZZ"})
        self.assertEqual((py / "notebook.md").read_text(encoding="utf-8").splitlines()[:6],
                         ["---", "type: notebook", "owner:", "initials:", "last_ids: [ZZa0001, ZZe0001]", "---"])
        self.assertFalse((py / "People").exists())
        # the owner writes their name in; the tools keep it, and use it when nobody else is named
        for root in (py, node):
            text = (root / "notebook.md").read_text(encoding="utf-8").replace("owner:", "owner: Zed Zed").replace("initials:", "initials: ZZ")
            eln.write_text_lf(root / "notebook.md", text + "\nMy own line stays.\n")
        # the folder and the sample are deleted (or lost by a sync): their numbers are not given out again
        shutil.rmtree(a_py.path.parent.parent)
        shutil.rmtree(node / a_js["folder"])
        (py / "Samples" / "ZZa0001.md").unlink()
        (node / "Samples" / "ZZa0001.md").unlink()
        code, out, err = self.cli("--root", str(py), "new", "experiment", "--title", "second")
        self.assertEqual(code, 0, err)
        b_js = tool(node, "create_experiment", {"title": "second"})
        self.assertIn("ZZe0002", out)
        self.assertEqual(b_js["id"], "ZZe0002")
        self.assertIn("researcher: Zed Zed", (node / b_js["path"]).read_text(encoding="utf-8"))
        self.assertEqual(eln.create_sample(py, "ZZ", "antibody", "ab two").id, "ZZa0002")
        self.assertEqual(tool(node, "create_sample", {"sample_type": "antibody", "title": "ab two"})["id"], "ZZa0002")
        self.assertIn("My own line stays.", (node / "notebook.md").read_text(encoding="utf-8"))
        self.assertIn("last_ids: [ZZa0002, ZZe0002]", (py / "notebook.md").read_text(encoding="utf-8"))
        self.assertSameTree(py, node)
        # a sync copy of notebook.md is pointed out
        for root in (py, node):
            shutil.copy(root / "notebook.md", root / "notebook (Zed's conflicted copy 2026-10-03).md")
        want = py_validate_text(py)
        self.assertIn("copy of notebook.md made by a sync service", want)
        self.assertEqual(want, tool(node, "check_notebook", text=True, ok_codes=(0, 2)))

    def test_adopting_an_older_folder(self):
        py, node = self.tmp / "py", self.tmp / "js"
        noon = calendar.timegm((2019, 3, 5, 12, 0, 0))
        for root in (py, node):
            old = root / "Experiments" / "2019-03-04_PRMT5 western"
            (old / "scans" / "empty").mkdir(parents=True)
            (old / "scans" / "gel 1.tif").write_bytes(b"\x00\x01gel")
            (old / "notes, final.txt").write_bytes(b"ran it\n")  # bytes, so the size is the same on Windows
            (old / "README.md").write_bytes(b"old readme\n")
            (old / ".DS_Store").write_bytes(b"x")
            (root / "blot run").mkdir()
            (root / "blot run" / "a.csv").write_bytes(b"a,b\n")
            # sorted by parts: the same order on Windows, where pathlib ignores case when comparing
            for i, f in enumerate(sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p: p.parts)):
                os.utime(f, (noon + i * 86400, noon + i * 86400))
        waiting = [p.relative_to(py).as_posix() for p in eln.adoptable_folders(py)]
        self.assertEqual(waiting, ["Experiments/2019-03-04_PRMT5 western", "blot run"])
        listed = tool(node, "adopt_folder", {})["folders"]
        self.assertEqual([f["path"] for f in listed], waiting)
        self.assertEqual(listed[0], {"path": waiting[0], "title": "PRMT5 western", "date": "2019-03-04"})
        self.assertEqual(tool(node, "notebook_overview")["folders_not_yet_records"], waiting)
        self.assertEqual(eln.guess_from_folder_name("20200115-KCl_titration (2)"), ("KCl titration (2)", "2020-01-15"))
        self.assertEqual(eln.guess_from_folder_name("run 20201341 x"), ("run 20201341 x", ""))

        a_py = eln.adopt_folder(py, py / waiting[0], "ZZ", "Zed Zed", today=TODAY)
        a_js = tool(node, "adopt_folder", {"folder": waiting[0], "initials": "ZZ", "researcher": "Zed Zed"})
        self.assertEqual((a_js["id"], a_js["path"]), ("ZZe0001", a_py.path.relative_to(py).as_posix()))
        self.assertEqual(a_js["extra"], [x.relative_to(py).as_posix() for x in a_py.extra])
        b_py = eln.adopt_folder(py, py / "blot run", "ZZ", "Zed Zed", title="Blot, second run", when="2020-01-15",
                                project="Some-Project", status="active", copy=True, today=TODAY)
        b_js = tool(node, "adopt_folder", {"folder": "blot run", "initials": "ZZ", "researcher": "Zed Zed", "title": "Blot, second run",
                                           "date": "2020-01-15", "project": "Some-Project", "status": "active", "copy": True})
        self.assertEqual((b_js["id"], b_js["warnings"]), (b_py.id, b_py.warnings))
        self.assertSameTree(py, node)

        for root in (py, node):
            self.assertFalse((root / waiting[0]).exists(), "the old folder was moved")
            self.assertTrue((root / "blot run" / "a.csv").exists(), "a copied folder stays where it was")
            kept = root / "Experiments" / "ZZe0001_PRMT5-western" / "2-data_raw" / "2019-03-04_PRMT5 western"
            self.assertEqual((kept / "scans" / "gel 1.tif").read_bytes(), b"\x00\x01gel")
            self.assertTrue((kept / "scans" / "empty").is_dir() and (kept / ".DS_Store").exists(), "moved whole")
            self.assertEqual(int((kept / "scans" / "gel 1.tif").stat().st_mtime), noon + 3 * 86400, "the file date is kept")
        note = (py / "Experiments" / "ZZe0001_PRMT5-western" / "1-notes" / "ZZe0001.md").read_text(encoding="utf-8")
        for line in ("title: PRMT5 western", "date_started: 2019-03-04", "date_completed: 2019-03-08", "tags: [adopted]",
                     "Not written. This record was made by adopting an older folder; see Files.",
                     "Adopted on 2026-10-03 from an older folder named `2019-03-04_PRMT5 western`. The folder was moved, as it was,"):
            self.assertIn(line, note)
        self.assertRegex(note, r"status: complete\b")
        listing = (py / "Experiments" / "ZZe0001_PRMT5-western" / "1-notes" / "ZZe0001_adopted-files.csv").read_text(encoding="utf-8")
        self.assertEqual(listing.splitlines()[:3], ["path,bytes,modified",
                                                     "2-data_raw/2019-03-04_PRMT5 western/.DS_Store,1,2019-03-05T12:00:00Z",
                                                     "2-data_raw/2019-03-04_PRMT5 western/README.md,11,2019-03-06T12:00:00Z"])
        self.assertIn('"2-data_raw/2019-03-04_PRMT5 western/notes, final.txt",7,', listing)
        self.assertEqual(eln.verify_manifest(py / "Experiments" / "ZZe0001_PRMT5-western", "ZZe0001"), ([], [], []))
        active = (py / b_py.path.relative_to(py)).read_text(encoding="utf-8")
        self.assertIn("date_started: 2020-01-15", active)
        self.assertIn("`date_started` is the date given. Correct", active)
        self.assertNotIn("Not written", active)
        want = py_validate_text(py)
        self.assertIn("0 errors", want)
        self.assertEqual(want, tool(node, "check_notebook", text=True))

        # what cannot be adopted is refused the same way
        for root in (py, node):
            (root / "hollow" / "inner").mkdir(parents=True)
        for folder, said in (("Experiments", "is part of the notebook"), ("Experiments/ZZe0001_PRMT5-western/2-data_raw", "already in an experiment record"),
                             ("hollow", "has no files in it"), ("nowhere", "there is no folder at")):
            with self.assertRaises(eln.ElnError) as cm:
                eln.adopt_folder(py, py / folder, "ZZ", "Zed Zed")
            self.assertIn(said, str(cm.exception))
            refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "--initials", "ZZ", "adopt_folder",
                                      json.dumps({"folder": folder})], capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1, folder)
            self.assertIn(said, refused.stderr)
        self.assertSameTree(py, node)

        # the command line: list what is waiting, then adopt by the path the list shows
        (py / "Experiments" / "third old one").mkdir()
        (py / "Experiments" / "third old one" / "x.txt").write_text("x\n", encoding="utf-8")
        code, out, _ = self.cli("--root", str(py), "adopt")
        self.assertEqual(code, 0)
        self.assertIn("Experiments/third old one    title: third old one", out)
        code, out, err = self.cli("--root", str(py), "adopt", "Experiments/third old one", "--initials", "ZZ", "--status", "active")
        self.assertEqual(code, 0, err)
        self.assertIn("Adopted third old one as ZZe0003", out)

    def test_export_as_a_folder_of_plain_files(self):
        py, node = self.sandbox_copy("py"), self.sandbox_copy("js")
        vault = eln.load_vault(py)
        chosen = eln.select_for_export(vault, "PRMT5-ChromatinRelease", [], None, False)
        r_py = eln.export_folder(vault, chosen, py / "Exports" / "export_PRMT5-ChromatinRelease_20261003", raw=False)
        r_js = tool(node, "export_notes", {"project": "PRMT5-ChromatinRelease", "format": "folder", "raw": False})
        self.assertEqual(r_js["path"], "Exports/export_PRMT5-ChromatinRelease_20261003")
        self.assertEqual((r_js["experiments"], r_js["notes"], r_js["files"], r_js["bytes"]),
                         (r_py["experiments"], r_py["notes"], r_py["files"], r_py["bytes"]))
        self.assertSameTree(py, node)
        out = py / "Exports" / "export_PRMT5-ChromatinRelease_20261003"
        names = set(tree(out))
        self.assertTrue({"README.md", "all-notes.md", "Inventory/experiments.csv", "Protocols/P_WesternBlot.md"} <= names)
        self.assertEqual((out / "all-notes.md").read_text(encoding="utf-8"), eln.build_export(vault, chosen))
        raw_kept = [n for n in names if "/2-data_raw/" in n]
        self.assertTrue(raw_kept and all(n.endswith("/2-data_raw/README.md") for n in raw_kept), "raw data left out")
        self.assertIn("Raw data was left out", (out / "README.md").read_text(encoding="utf-8"))
        # the export is itself a notebook folder: the check runs on it and finds no errors
        exported = py_validate_text(out)
        self.assertIn("0 errors", exported)
        self.assertEqual(exported, tool(node / "Exports" / "export_PRMT5-ChromatinRelease_20261003", "check_notebook", text=True, ok_codes=(0, 2)))
        # the notebook's own check does not read Exports/
        self.assertEqual(py_validate_text(py), py_validate_text(self.sandbox_copy("untouched")))

        # everything, raw data included; a second export to the same place is refused
        r_py = eln.export_folder(vault, eln.select_for_export(vault, None, [], None, True), py / "Exports" / "export_all_20261003")
        r_js = tool(node, "export_notes", {"all": True, "format": "folder"})
        self.assertEqual(r_js["path"], "Exports/export_all_20261003")
        self.assertEqual((r_js["files"], r_js["bytes"]), (r_py["files"], r_py["bytes"]))
        self.assertSameTree(py, node)
        self.assertTrue(any("/2-data_raw/" in n and not n.endswith("README.md") for n in tree(py / "Exports" / "export_all_20261003")))
        with self.assertRaises(eln.ElnError):
            eln.export_folder(vault, chosen, py / "Exports" / "export_all_20261003")
        # a second export on the same day does not overwrite and does not fail: it gets -2
        code, out_text, err = self.cli("--root", str(py), "export", "--all", "--format", "folder")
        self.assertEqual(code, 0, err)
        again = tool(node, "export_notes", {"all": True, "format": "folder"})
        self.assertEqual(again["path"], "Exports/export_all_20261003-2")
        self.assertSameTree(py, node)
        # a project and a status together narrow each other; everything together with a filter is refused
        both = tool(node, "export_notes", {"project": "PRMT5-ChromatinRelease", "status": "active"})
        self.assertEqual(both["experiments"], ["ALXe0004", "ALXe0005"])
        self.assertEqual(both["experiments"], [n.id for n in eln.select_for_export(vault, "PRMT5-ChromatinRelease", [], "active", False)])
        with self.assertRaises(eln.ElnError):
            eln.select_for_export(vault, "PRMT5-ChromatinRelease", [], None, True)
        refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "export_notes",
                                  '{"all": true, "status": "active"}'], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("not both", refused.stderr)
        code, out_text, err = self.cli("--root", str(py), "export", "--status", "active", "--format", "folder", "--no-raw")
        self.assertEqual(code, 0, err)
        self.assertIn("as a folder of plain files", out_text)
        self.assertTrue((py / "Exports" / "export_active_20261003" / "README.md").exists())

    def test_findings_from_the_second_review_stay_fixed(self):
        """Each block is a problem a reviewer found with made-up data; both tools must handle it the same way."""
        py, node = self.sandbox_copy("py"), self.sandbox_copy("js")

        # two programs creating records at the same moment: no ID is given out twice, no sample is overwritten
        script = ("import sys, importlib.util as u; s = u.spec_from_file_location('eln', sys.argv[1]); m = u.module_from_spec(s); "
                  "s.loader.exec_module(m); k = sys.argv[3]; "
                  "r = m.create_sample(m.Path(sys.argv[2]), 'ALX', 'plasmid', 'race ' + k) if k[0] == 's' else "
                  "m.create_experiment(m.Path(sys.argv[2]), 'ALX', 'Alex Example', 'race ' + k); print(r.id)")
        call = [NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(py)]
        jobs = []
        for i in range(4):
            jobs.append(subprocess.Popen([sys.executable, "-c", script, str(REPO_ROOT / "scripts" / "eln.py"), str(py), f"s{i}"], stdout=subprocess.PIPE, text=True))
            jobs.append(subprocess.Popen(call + ["create_sample", json.dumps({"sample_type": "plasmid", "title": f"race js {i}"})], stdout=subprocess.PIPE, text=True))
            jobs.append(subprocess.Popen([sys.executable, "-c", script, str(REPO_ROOT / "scripts" / "eln.py"), str(py), f"e{i}"], stdout=subprocess.PIPE, text=True))
            jobs.append(subprocess.Popen(call + ["create_experiment", json.dumps({"title": f"race js {i}"})], stdout=subprocess.PIPE, text=True))
        outs = [j.communicate()[0] for j in jobs]
        self.assertTrue(all(j.returncode == 0 for j in jobs))
        self.assertEqual(len(list((py / "Samples").glob("ALXp*.md"))), 8, "eight samples asked for, eight files")
        folders = [p.name[:8] for p in (py / "Experiments").iterdir() if p.name.startswith("ALXe")]
        self.assertEqual(len(folders), len(set(folders)), "no experiment ID twice")
        self.assertEqual(len(folders), 6 + 8)
        self.assertIn("0 errors", py_validate_text(py))
        self.assertFalse((py / ".eln-lock").exists())
        self.assertIn("last_ids: [ALXa0003, ALXc0002, ALXe0014, ALXi0001, ALXp0008]", (py / "notebook.md").read_text(encoding="utf-8"))
        shutil.rmtree(py)
        py = self.sandbox_copy("py")

        # hidden data files are in the manifest; operating-system litter is not
        for root in (py, node):
            raw = next((root / "Experiments").glob("ALXe0003_*")) / "2-data_raw"
            (raw / ".RData").write_bytes(b"workspace")
            (raw / ".DS_Store").write_bytes(b"x")
            (raw / "._resource").write_bytes(b"x")
        eln.complete_experiment(py, "ALXe0003")
        tool(node, "complete_experiment", {"id": "ALXe0003"})
        manifest = next((py / "Experiments").glob("ALXe0003_*/1-notes/ALXe0003_MANIFEST.sha256")).read_text(encoding="utf-8")
        self.assertIn("2-data_raw/.RData", manifest)
        self.assertNotIn(".DS_Store", manifest)
        self.assertNotIn("._resource", manifest)
        self.assertSameTree(py, node)
        for root in (py, node):
            (next((root / "Experiments").glob("ALXe0003_*")) / "2-data_raw" / ".RData").write_bytes(b"changed!!")
        self.assertEqual(eln.verify_manifest(next((py / "Experiments").glob("ALXe0003_*")), "ALXe0003")[1], ["2-data_raw/.RData"])
        self.assertEqual(tool(node, "verify_files", {"id": "ALXe0003"}, ok_codes=(2,))["results"][0]["modified"], ["2-data_raw/.RData"])

        # a completed experiment whose manifest was deleted is reported, not passed over
        for root in (py, node):
            next((root / "Experiments").glob("ALXe0001_*/1-notes/ALXe0001_MANIFEST.sha256")).unlink()
        code, out, _ = self.cli("--root", str(py), "verify")
        self.assertEqual(code, 1)
        self.assertIn("ALXe0001: is complete, but there is no manifest to compare with", out)
        self.assertEqual(tool(node, "verify_files", {}, text=True, ok_codes=(2,)).replace("mark the experiment complete again", "X"),
                         out.replace("re-run `eln.py complete ID`", "X"))

        # a snapshot lists the files of the experiment, not itself or the manifest, so writing it twice gives the same file
        snap = next((py / "Experiments").glob("ALXe0002_*/1-notes/ALXe0002_snapshot_20260708.html"))
        before = snap.read_bytes()
        self.assertNotIn(b"MANIFEST.sha256</td>", before)
        eln.complete_experiment(py, "ALXe0002")
        tool(node, "complete_experiment", {"id": "ALXe0002"})
        self.assertEqual(snap.read_bytes(), before)
        self.assertEqual(next((node / "Experiments").glob("ALXe0002_*/1-notes/ALXe0002_snapshot_20260708.html")).read_bytes(), before)

        # two experiment folders with the same ID (a hand merge): an export refuses instead of dropping one
        for root in (py, node):
            src = next((root / "Experiments").glob("ALXe0004_*"))
            shutil.copytree(src, src.with_name("ALXe0004_copied-by-hand"))
        with self.assertRaises(eln.ElnError) as cm:
            eln.select_for_export(eln.load_vault(py), None, [], None, True)
        self.assertIn("two experiments have the ID ALXe0004", str(cm.exception))
        refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "export_notes", '{"all": true}'], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("two experiments have the ID ALXe0004", refused.stderr)
        for root in (py, node):
            shutil.rmtree(next((root / "Experiments").glob("ALXe0004_copied-by-hand")))

        # notebook.md someone edited into a form the tools cannot keep: it is left alone, and Check says so
        for root in (py, node):
            eln.write_text_lf(root / "notebook.md", "---\ntype: notebook\nowner: Alex Example\ninitials: ALX\nlast_ids:\n  - ALXe0006\n---\nmine\n")
        r_py = eln.create_experiment(py, "ALX", "Alex Example", "after the edit")
        r_js = tool(node, "create_experiment", {"title": "after the edit"})
        self.assertEqual((r_py.id, r_js["id"]), ("ALXe0007", "ALXe0007"))
        self.assertIn("  - ALXe0006\n---\nmine\n", (py / "notebook.md").read_text(encoding="utf-8"))
        self.assertSameTree(py, node)
        want = py_validate_text(py)
        self.assertIn("notebook.md\n  WARN   indented line in header", want)
        self.assertIn("the last IDs are not being remembered", want)
        self.assertEqual(want, tool(node, "check_notebook", text=True))
        # a deleted notebook.md is made again from what the folders show, not from nothing
        for root in (py, node):
            (root / "notebook.md").unlink()
        eln.create_sample(py, "ALX", "plasmid", "after the loss")
        tool(node, "create_sample", {"sample_type": "plasmid", "title": "after the loss", "initials": "ALX"})
        self.assertIn("last_ids: [ALXa0003, ALXc0002, ALXe0007, ALXi0001, ALXp0001]", (py / "notebook.md").read_text(encoding="utf-8"))
        self.assertSameTree(py, node)

        # whose record: the notebook's owner comes before settings saved on the computer; a flag comes before both
        jordan = self.sandbox_copy("jordan-notebook", "jordan")
        made = tool(jordan, "create_experiment", {"title": "saved settings say someone else"}, initials="", researcher="")
        self.assertEqual(made["id"], "JORe0005")
        env = dict(os.environ, AI_ELN_INITIALS="ALX", AI_ELN_RESEARCHER="Alex Example", AI_ELN_CONFIG=str(self.tmp / "none.json"))
        saved = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(jordan), "create_experiment", '{"title": "env says ALX"}'],
                               capture_output=True, text=True, env=env)
        self.assertEqual(json.loads(saved.stdout)["id"], "JORe0006", saved.stderr)
        self.assertIn("researcher: Jordan Example", (jordan / json.loads(saved.stdout)["path"]).read_text(encoding="utf-8"))
        os.environ.update(AI_ELN_INITIALS="ALX", AI_ELN_RESEARCHER="Alex Example")
        try:
            code, out, err = self.cli_env("--root", str(jordan), "new", "experiment", "--title", "python, env says ALX")
            self.assertIn("JORe0007", out, err)
            code, out, err = self.cli_env("--root", str(jordan), "new", "experiment", "--title", "a flag wins", "--initials", "QQQ")
            self.assertIn("QQQe0001", out, err)
            self.assertIn("researcher: QQQ", next((jordan / "Experiments").glob("QQQe0001_*/1-notes/QQQe0001.md")).read_text(encoding="utf-8"))
        finally:
            del os.environ["AI_ELN_INITIALS"], os.environ["AI_ELN_RESEARCHER"]
        flagged = tool(jordan, "create_experiment", {"title": "js flag"}, initials="QQQ", researcher="")
        self.assertEqual(flagged["id"], "QQQe0002")

        # the folder that holds the notebooks is not a notebook
        lab = self.tmp / "lab"
        shutil.copytree(REPO_ROOT / "sandbox" / "jordan", lab / "jordan")
        shutil.copytree(REPO_ROOT / "sandbox" / "alex", lab / "alex")
        for argv in (("validate",), ("find", "--text", "SNRPB"), ("new", "experiment", "--title", "x", "--initials", "ZZZ")):
            code, out, err = self.cli("--root", str(lab), *argv)
            self.assertEqual(code, 1, argv)
            self.assertIn("is not a notebook. It holds 2 notebooks (alex, jordan)", err)
        for name, args in (("check_notebook", {}), ("find_notes", {"text": "SNRPB"}), ("create_experiment", {"title": "x", "initials": "ZZZ"})):
            refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(lab), name, json.dumps(args)], capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1, name)
            self.assertIn("is not a notebook. It holds 2 notebooks (alex, jordan)", refused.stderr)
        self.assertEqual(sorted(p.name for p in lab.iterdir()), ["alex", "jordan"], "nothing was created next to them")

    @unittest.skipIf(os.name == "nt", "symbolic links need extra rights on Windows")
    def test_links_are_never_followed_when_adopting(self):
        py, node = self.tmp / "py", self.tmp / "js"
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_bytes(b"not part of any notebook\n")
        for root in (py, node):
            other = root / "Experiments" / "other project"
            other.mkdir(parents=True)
            (other / "precious.csv").write_bytes(b"a,b\n1,2\n")
            old = root / "Experiments" / "2019-03-04 linked"
            old.mkdir()
            (old / "data.txt").write_bytes(b"data\n")
            os.symlink("../other project", old / "see_other")
            os.symlink(str(outside / "secret.txt"), old / "leak.txt")
            os.symlink("nowhere", old / "dangling")
        eln.adopt_folder(py, py / "Experiments" / "2019-03-04 linked", "ZZ", "Zed", today=TODAY)
        r = tool(node, "adopt_folder", {"folder": "Experiments/2019-03-04 linked", "initials": "ZZ", "researcher": "Zed"})
        self.assertEqual(r["warnings"], [])
        for root in (py, node):
            self.assertEqual((root / "Experiments" / "other project" / "precious.csv").read_bytes(), b"a,b\n1,2\n", "the other folder is untouched")
            self.assertFalse((root / "Experiments" / "2019-03-04 linked").exists())
            kept = root / "Experiments" / "ZZe0001_linked" / "2-data_raw" / "2019-03-04 linked"
            self.assertTrue((kept / "see_other").is_symlink() and (kept / "leak.txt").is_symlink() and (kept / "dangling").is_symlink())
            listing = (root / "Experiments" / "ZZe0001_linked" / "1-notes" / "ZZe0001_adopted-files.csv").read_text(encoding="utf-8")
            self.assertEqual(len(listing.splitlines()), 2, "only the real file is listed")
            manifest = (root / "Experiments" / "ZZe0001_linked" / "1-notes" / "ZZe0001_MANIFEST.sha256").read_text(encoding="utf-8")
            self.assertNotIn("leak.txt", manifest)
            self.assertNotIn("precious.csv", manifest)
        self.assertEqual((outside / "secret.txt").read_bytes(), b"not part of any notebook\n")
        # a link to a folder is not itself adopted
        for root in (py, node):
            os.symlink(str(outside), root / "Experiments" / "link to outside")
            os.symlink("other project", root / "Experiments" / "link inside")
        for name in ("link to outside", "link inside"):
            with self.assertRaises(eln.ElnError):
                eln.adopt_folder(py, py / "Experiments" / name, "ZZ", "Zed", today=TODAY)
            refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "--initials", "ZZ", "adopt_folder",
                                      json.dumps({"folder": f"Experiments/{name}"})], capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1, name)
        self.assertTrue((outside / "secret.txt").exists())
        # an export does not copy what a link points to
        for root in (py, node):
            os.symlink(str(outside / "secret.txt"), root / "Experiments" / "ZZe0001_linked" / "4-data_processed" / "ZZe0001_leak.txt")
        vault = eln.load_vault(py)
        eln.export_folder(vault, eln.select_for_export(vault, None, [], None, True), py / "Exports" / "export_all_20261003")
        tool(node, "export_notes", {"all": True, "format": "folder"})
        for root in (py, node):
            self.assertFalse(any("leak" in n for n in tree(root / "Exports")), "no linked file in the export")

    def test_eln_archive(self):
        root = self.sandbox_copy("s")
        vault = eln.load_vault(root)
        exps = eln.select_for_export(vault, None, ["ALXe0002", "ALXe0003"], None, False)
        py_bytes = eln.build_eln(vault, exps, root_name=f"export_ALXe0002-ALXe0003_{TODAY.replace('-', '')}")
        r = tool(root, "export_notes", {"experiment_ids": ["ALXe0002", "ALXe0003"], "format": "eln"})
        self.assertEqual(r["path"], f"Inventory/export_ALXe0002-ALXe0003_{TODAY.replace('-', '')}.eln")
        with zipfile.ZipFile(io.BytesIO(py_bytes)) as zp, zipfile.ZipFile(root / r["path"]) as zj:
            self.assertIsNone(zj.testzip())
            self.assertEqual(sorted(zp.namelist()), sorted(zj.namelist()))
            meta_name = next(n for n in zj.namelist() if n.endswith("ro-crate-metadata.json"))
            for name in zp.namelist():
                if name != meta_name:
                    self.assertEqual(zp.read(name), zj.read(name), name)
            mp, mj = json.loads(zp.read(meta_name)), json.loads(zj.read(meta_name))

            def without_media_type(crate):
                # Python asks the operating system for media types, so they differ between machines
                return [{k: v for k, v in node.items() if k != "encodingFormat"} for node in crate["@graph"]]
            self.assertEqual(without_media_type(mj), without_media_type(mp))
            self.assertEqual(mj["@context"], mp["@context"])
            formats = {n["name"].rsplit(".", 1)[-1]: n["encodingFormat"] for n in mj["@graph"] if n.get("@type") == "File"}
            self.assertEqual(formats["md"], "text/markdown")
            self.assertEqual(formats["png"], "image/png")
            self.assertEqual(formats["csv"], "text/csv")
            self.assertEqual(formats["sha256"], "application/octet-stream")


if __name__ == "__main__":
    unittest.main()
