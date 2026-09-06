"""
Tests for scripts/eln_web.py: start the server on an ephemeral port against a
throwaway root and drive it with urllib, the way a browser would.
"""
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


eln = load("eln")
web = load("eln_web")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class TestWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="eln-web-"))
        cls.root = cls.tmp / "root"
        cls.root.mkdir()
        cls._env = {k: os.environ.pop(k) for k in list(os.environ) if k.startswith("AI_ELN_")}
        os.environ["AI_ELN_CONFIG"] = str(cls.tmp / "config.json")
        os.environ["AI_ELN_INITIALS"] = "WEB"
        os.environ["AI_ELN_RESEARCHER"] = "Web Person"
        cls.server = web.serve(cls.root, 0, open_browser=False)
        cls.base = f"http://127.0.0.1:{cls.server.server_address[1]}"
        cls.opener = urllib.request.build_opener(NoRedirect)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        for k in list(os.environ):
            if k.startswith("AI_ELN_"):
                del os.environ[k]
        os.environ.update(cls._env)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def get(self, path):
        try:
            with self.opener.open(self.base + path) as r:
                return r.status, r.read().decode("utf-8", errors="replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace"), dict(e.headers)

    def post(self, path, data):
        body = urllib.parse.urlencode(data, doseq=True).encode()
        req = urllib.request.Request(self.base + path, data=body, method="POST")
        try:
            with self.opener.open(req) as r:
                return r.status, r.read().decode("utf-8"), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8"), dict(e.headers)

    # ------------------------------------------------------------------

    def test_01_home_and_forms_render(self):
        code, body, _ = self.get("/")
        self.assertEqual(code, 200)
        self.assertIn("Shechter Lab research record", body)
        self.assertIn("Web Person (WEB)", body)
        for path in ("/new/experiment", "/new/sample", "/new/protocol", "/new/project", "/setup", "/export"):
            code, body, _ = self.get(path)
            self.assertEqual(code, 200, path)
            self.assertIn("<form", body, path)
        for path in ("/experiments", "/samples", "/protocols", "/projects", "/validate", "/report"):
            code, body, _ = self.get(path)
            self.assertEqual(code, 200, path)
            self.assertIn("<h1>", body, path)

    def test_02_create_everything_through_forms(self):
        code, _, h = self.post("/new/project", {"project_id": "Proj-W", "title": "Web project", "lead": "Web Person"})
        self.assertEqual(code, 303)
        self.assertEqual(h["Location"], "/note/Proj-W?created=1")
        code, _, h = self.post("/new/protocol", {"name": "WesternBlot", "title": "Western blot"})
        self.assertEqual(code, 303)
        self.assertTrue((self.root / "Protocols" / "P_WesternBlot.md").exists())
        code, _, h = self.post("/new/sample", {"sample_type": "antibody", "title": "anti-X", "source": "Sigma", "storage": "Fridge"})
        self.assertEqual(code, 303)
        self.assertEqual(h["Location"], "/note/WEBa0001?created=1")
        code, _, h = self.post("/new/experiment", {
            "title": "Form-made experiment: with colon", "project": "Proj-W", "exp_type": "WesternBlot",
            "protocol": "P_WesternBlot", "samples": ["WEBa0001"], "notebook": "NB01-002", "meeting": "1"})
        self.assertEqual(code, 303)
        self.assertEqual(h["Location"], "/note/WEBe0001?created=1")
        folder = next((self.root / "Experiments").glob("WEBe0001_*"))
        fields, _, problems = eln.parse_front_matter((folder / "1-notes" / "WEBe0001.md").read_text(encoding="utf-8"))
        self.assertEqual(problems, [])
        self.assertEqual(fields["title"], "Form-made experiment: with colon")
        self.assertEqual(fields["samples"], ["WEBa0001"])
        self.assertEqual(fields["tags"], ["meeting"])
        self.assertEqual(len(list((folder / "1-notes").glob("WEBe0001_P_WesternBlot_*.md"))), 1)
        # the created note page renders, with the header table and the folder listing
        code, body, _ = self.get("/note/WEBe0001?created=1")
        self.assertEqual(code, 200)
        self.assertIn("Created. Open it in your editor", body)
        self.assertIn("Form-made experiment: with colon", body)
        self.assertIn("2-data_raw/", body)
        self.assertIn("Open in your editor", body)
        # the sample page shows where it was used
        code, body, _ = self.get("/note/WEBa0001")
        self.assertIn("Used in", body)
        self.assertIn("WEBe0001", body)

    def test_03_form_errors_come_back_to_the_form(self):
        code, body, _ = self.post("/new/experiment", {"title": "   "})
        self.assertEqual(code, 400)
        self.assertIn("needs a title", body)
        code, body, _ = self.post("/new/protocol", {"name": "bad name!"})
        self.assertEqual(code, 400)
        self.assertIn("letters, digits, and hyphens", body)
        code, body, _ = self.post("/new/project", {"project_id": "Proj-W"})
        self.assertEqual(code, 400)
        self.assertIn("already exists", body)
        code, _, h = self.post("/new/experiment", {"title": "x", "protocol": "P_Missing"})
        self.assertEqual(code, 303)
        self.assertIn("warn=", h["Location"])

    def test_04_validate_report_export(self):
        code, body, _ = self.get("/validate")
        self.assertEqual(code, 200)
        self.assertIn("Checked", body)
        self.assertIn("P_Missing", body)  # the dangling reference from test_03 is reported
        code, body, _ = self.get("/report")
        self.assertIn("Flagged for discussion", body)
        self.assertIn("WEBe0001", body)
        code, body, _ = self.get("/export?scope=project&project=Proj-W")
        self.assertEqual(code, 200)
        self.assertIn("==== Experiments/WEBe0001_", body)
        self.assertIn("Protocols/P_WesternBlot.md ====", body)
        code, body, _ = self.get("/export?scope=ids&ids=WEBe0099")
        self.assertIn("not found", body)
        code, body, _ = self.get("/experiments?q=colon&status=active")
        self.assertIn("WEBe0001", body)
        self.assertNotIn("WEBe0002", body)  # test_03 made WEBe0002 ("x"); filtered out by text

    def test_05_settings(self):
        code, body, _ = self.post("/setup", {"initials": "toolong5", "researcher": "x"})
        self.assertEqual(code, 400)
        code, _, h = self.post("/setup", {"initials": "abc", "researcher": "Some One"})
        self.assertEqual(code, 303)
        self.assertEqual(json.loads(Path(os.environ["AI_ELN_CONFIG"]).read_text(encoding="utf-8"))["initials"], "ABC")

    def test_06_file_serving_is_confined_to_root_and_images(self):
        folder = next((self.root / "Experiments").glob("WEBe0001_*"))
        (folder / "5-figures" / "WEBe0001_R_blot.png").write_bytes(b"\x89PNG fake")
        rel = f"Experiments/{folder.name}/5-figures/WEBe0001_R_blot.png"
        code, _, h = self.get("/file?p=" + urllib.parse.quote(rel))
        self.assertEqual(code, 200)
        self.assertEqual(h["Content-Type"], "image/png")
        self.assertEqual(self.get("/file?p=" + urllib.parse.quote(f"Experiments/{folder.name}/1-notes/WEBe0001.md"))[0], 404)
        self.assertEqual(self.get("/file?p=../../etc/passwd")[0], 404)
        self.assertEqual(self.get("/file?p=" + urllib.parse.quote(str(REPO_ROOT / "README.md")))[0], 404)
        self.assertEqual(self.post("/open", {"p": "../../etc"})[0], 404)
        # an image referenced from a note body is rewritten to /file?p=...
        note = folder / "1-notes" / "WEBe0001.md"
        note.write_text(note.read_text(encoding="utf-8").replace("## Results\n", "## Results\n\n![](../5-figures/WEBe0001_R_blot.png)\n"), encoding="utf-8")
        code, body, _ = self.get("/note/WEBe0001")
        self.assertIn("/file?p=Experiments/" + urllib.parse.quote(folder.name) + "/5-figures/WEBe0001_R_blot.png", body)

    def test_06b_edit_in_browser(self):
        code, body, _ = self.get("/edit/WEBe0001")
        self.assertEqual(code, 200)
        self.assertIn("<textarea", body)
        self.assertIn("experiment_id: WEBe0001", body)
        folder = next((self.root / "Experiments").glob("WEBe0001_*"))
        note = folder / "1-notes" / "WEBe0001.md"
        text = note.read_text(encoding="utf-8").replace("## Results\n", "## Results\n\nBands got brighter.\n")
        code, _, h = self.post("/edit/WEBe0001", {"text": text})
        self.assertEqual(code, 303)
        self.assertEqual(h["Location"], "/note/WEBe0001?saved=1")
        self.assertIn("Bands got brighter.", note.read_text(encoding="utf-8"))
        # a broken header is refused and the text comes back for fixing
        code, body, _ = self.post("/edit/WEBe0001", {"text": text.replace("experiment_id: WEBe0001", "experiment_id: WEBe0009")})
        self.assertEqual(code, 400)
        self.assertIn("must stay WEBe0001", body)
        code, body, _ = self.post("/edit/WEBe0001", {"text": "no header at all"})
        self.assertEqual(code, 400)
        self.assertIn("Header problem", body)
        self.assertIn("Bands got brighter.", note.read_text(encoding="utf-8"))  # untouched
        self.assertEqual(self.get("/edit/NOPE0001")[0], 404)

    def test_06c_cross_site_requests_are_refused(self):
        body = urllib.parse.urlencode({"title": "injected"}).encode()
        req = urllib.request.Request(self.base + "/new/experiment", data=body, method="POST",
                                     headers={"Origin": "http://evil.example"})
        try:
            self.opener.open(req)
            self.fail("cross-site POST was accepted")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)
        self.assertFalse(list((self.root / "Experiments").glob("*injected*")))
        req = urllib.request.Request(self.base + "/", headers={"Host": "evil.example"})
        try:
            self.opener.open(req)
            self.fail("wrong Host was accepted")
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 403)
        # same-origin still works (Origin sent by browsers on form posts)
        req = urllib.request.Request(self.base + "/new/protocol", data=urllib.parse.urlencode({"name": "SameOrigin"}).encode(),
                                     method="POST", headers={"Origin": self.base})
        try:
            self.opener.open(req)
        except urllib.error.HTTPError as e:
            self.assertEqual(e.code, 303)

    def test_06d_complete_verify_render_and_eln_export(self):
        folder = next((self.root / "Experiments").glob("WEBe0001_*"))
        note = folder / "1-notes" / "WEBe0001.md"
        # not finished yet: refused with a "Complete anyway" option
        code, body, _ = self.post("/complete/WEBe0001", {})
        self.assertEqual(code, 400)
        self.assertIn("Complete anyway", body)
        self.assertFalse((folder / "1-notes" / "WEBe0001_MANIFEST.sha256").exists())
        text = note.read_text(encoding="utf-8").replace("## Interpretation\n", "## Interpretation\n\nMeans something.\n")
        note.write_text(text, encoding="utf-8")
        code, body, _ = self.post("/complete/WEBe0001", {"date": "2026-09-12"})
        self.assertEqual(code, 200)
        self.assertIn("WEBe0001 is complete", body)
        self.assertTrue((folder / "1-notes" / "WEBe0001_MANIFEST.sha256").exists())
        self.assertTrue((folder / "1-notes" / "WEBe0001_snapshot_20260912.html").exists())
        code, body, _ = self.get("/note/WEBe0001")
        self.assertIn("Verify files", body)
        self.assertNotIn("Mark complete", body)
        code, body, _ = self.post("/verify/WEBe0001", {})
        self.assertIn("match the manifest", body)
        (folder / "3-code" / "WEBe0001_late.R").write_text("# late\n", encoding="utf-8")
        code, body, _ = self.post("/verify/WEBe0001", {})
        self.assertIn("Changed since completion", body)
        self.assertIn("WEBe0001_late.R", body)
        code, body, _ = self.post("/render/WEBe0001", {})
        self.assertIn("Saved and opened", body)
        self.assertTrue(list((folder / "1-notes").glob("WEBe0001_snapshot_*.html")))
        code, body, _ = self.post("/export/save", {"scope": "project", "project": "Proj-W", "format": "eln"})
        self.assertEqual(code, 200)
        self.assertIn(".eln archive", body)
        eln_files = list((self.root / "Inventory").glob("export_Proj-W_*.eln"))
        self.assertEqual(len(eln_files), 1)
        import zipfile
        with zipfile.ZipFile(eln_files[0]) as zf:
            self.assertTrue(any(n.endswith("ro-crate-metadata.json") for n in zf.namelist()))
        self.assertEqual(self.post("/complete/NOPE0001", {})[0], 404)
        self.assertEqual(self.post("/verify/NOPE0001", {})[0], 404)

    def test_07_unknown_routes(self):
        self.assertEqual(self.get("/nope")[0], 404)
        self.assertEqual(self.get("/note/NOPE0001")[0], 404)
        self.assertEqual(self.post("/nope", {})[0], 404)


class TestMarkdown(unittest.TestCase):
    def test_renderer_basics(self):
        md = ("# T\n\nPara with **bold**, `code`, JSRe0002 and P_WesternBlot.\n\n"
              "## L\n\n- one\n- [ ] todo\n- [x] done\n\n1. a\n2. b\n\n| h1 | h2 |\n|---|---|\n| c1 | c2 |\n\n"
              "![](../5-figures/x.png)\n\n<!-- hidden -->\n\n```\nraw <b>\n```\n")
        out = web.md_to_html(md, "Experiments/E_x/1-notes")
        self.assertIn("<h1>T</h1>", out)
        self.assertIn("<b>bold</b>", out)
        self.assertIn("<code>code</code>", out)
        self.assertIn('<a href="/note/JSRe0002">JSRe0002</a>', out)
        self.assertIn('<a href="/note/P_WesternBlot">P_WesternBlot</a>', out)
        self.assertIn("&#9744; todo", out)
        self.assertIn("&#9745; done", out)
        self.assertIn("<ol>", out)
        self.assertIn("<th>h1</th>", out)
        self.assertIn('src="/file?p=Experiments/E_x/5-figures/x.png"', out)
        self.assertNotIn("hidden", out)
        self.assertIn("raw &lt;b&gt;", out)  # code is escaped, never rendered as HTML

    def test_html_is_escaped(self):
        out = web.md_to_html("<script>alert(1)</script> and a <b>tag</b>")
        self.assertNotIn("<script>", out)
        self.assertIn("&lt;script&gt;", out)


if __name__ == "__main__":
    unittest.main()
