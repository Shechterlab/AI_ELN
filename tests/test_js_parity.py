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

    def sandbox_copy(self, name: str) -> Path:
        dst = self.tmp / name
        shutil.copytree(REPO_ROOT / "sandbox", dst, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
        for extra in ("README.md", "PILOT.md"):
            (dst / extra).unlink()
        return dst

    cli = staticmethod(run_cli)

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
        self.assertEqual(py_validate_text(REPO_ROOT / "sandbox"), tool(REPO_ROOT / "sandbox", "check_notebook", text=True))

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
                             ({"experiment_ids": ["JORe0002", "ALXe0002"]}, (None, ["JORe0002", "ALXe0002"], None, False))]:
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
        self.assertEqual(len(everything["results"]), 3)

        vault = eln.load_vault(py)
        for nid in ("ALXa0001", "P_WesternBlot", "JORe0001"):
            note = vault.by_id[nid]
            want = eln.render_snapshot_html(vault, note, generated=TODAY)
            path = tool(node, "render_snapshot", {"id": nid})["path"]
            self.assertEqual((node / path).read_text(encoding="utf-8"), want, nid)

    def test_findings_from_the_role_play_stay_fixed(self):
        """Each block is a problem a role-played user found; both tools must now handle it, the same way."""
        py, node = self.sandbox_copy("py"), self.sandbox_copy("js")

        # line breaks in a title, accents in a folder name, a protocol typed without P_
        title = "R\u00e9sum\u00e9 of \u03b1-tubulin\nstatus: complete"
        r_py = eln.create_experiment(py, "ZZ", "Zed", title, protocol="WesternBlot, P_Immunofluorescence", project="Nope", samples="ALXa0001, ALXz9")
        r_js = tool(node, "create_experiment", {"title": title, "protocol": "WesternBlot, P_Immunofluorescence", "project": "Nope",
                                                 "samples": "ALXa0001, ALXz9", "initials": "ZZ", "researcher": "Zed"})
        self.assertEqual(r_py.path.parent.parent.name, "ZZe0001_Resume-of-tubulin-status-complete")
        self.assertEqual(r_js["warnings"], r_py.warnings)
        self.assertEqual(len(r_py.warnings), 2)
        fields, _, problems = eln.parse_front_matter(r_py.path.read_text(encoding="utf-8"))
        self.assertEqual((problems, fields["status"], fields["protocols"]), ([], "active", ["P_WesternBlot", "P_Immunofluorescence"]))
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
            (old / "notes, final.txt").write_text("ran it\n", encoding="utf-8")
            (old / "README.md").write_text("old readme\n", encoding="utf-8")
            (old / ".DS_Store").write_bytes(b"x")
            (root / "blot run").mkdir()
            (root / "blot run" / "a.csv").write_text("a,b\n", encoding="utf-8")
            for i, f in enumerate(sorted(p for p in root.rglob("*") if p.is_file())):
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
        refused = subprocess.run([NODE, str(REPO_ROOT / "mcp" / "call.mjs"), "--root", str(node), "--today", TODAY, "export_notes",
                                  '{"all": true, "format": "folder"}'], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 1)
        self.assertIn("already exists", refused.stderr)
        code, out_text, err = self.cli("--root", str(py), "export", "--status", "active", "--format", "folder", "--no-raw")
        self.assertEqual(code, 0, err)
        self.assertIn("as a folder of plain files", out_text)
        self.assertTrue((py / "Exports" / "export_active_20261003" / "README.md").exists())

    def test_eln_archive(self):
        root = self.sandbox_copy("s")
        vault = eln.load_vault(root)
        exps = eln.select_for_export(vault, None, ["ALXe0002", "JORe0001"], None, False)
        py_bytes = eln.build_eln(vault, exps, root_name=f"export_ALXe0002-JORe0001_{TODAY.replace('-', '')}")
        r = tool(root, "export_notes", {"experiment_ids": ["ALXe0002", "JORe0001"], "format": "eln"})
        self.assertEqual(r["path"], f"Inventory/export_ALXe0002-JORe0001_{TODAY.replace('-', '')}.eln")
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
