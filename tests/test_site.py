"""
Tests for the website in docs/ (GitHub Pages serves that folder as it is).

They keep the site honest with the rest of the repository: links point at files that exist, the guide
menu matches the Markdown files, the launchers it names are real, and the "name an experiment" box
produces exactly what scripts/eln.py produces.
"""
import importlib.util
import json
import re
import shutil
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS = REPO_ROOT / "docs"
SPEC = importlib.util.spec_from_file_location("eln", REPO_ROOT / "scripts" / "eln.py")
eln = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eln)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ("href", "src") and value:
                self.refs.append(value)


def refs_of(page: str):
    parser = Links()
    parser.feed((DOCS / page).read_text(encoding="utf-8"))
    return parser.refs


def guide_ids():
    return re.findall(r"\{ id: '([A-Za-z0-9_-]+)'", (DOCS / "assets" / "guide.js").read_text(encoding="utf-8"))


class TestSite(unittest.TestCase):
    PAGES = ("index.html", "guide.html")

    def test_pages_and_nojekyll_exist(self):
        for name in self.PAGES + (".nojekyll", "assets/site.css", "assets/marked.min.js", "assets/shechterlab-icon.svg"):
            self.assertTrue((DOCS / name).exists(), name)

    def test_every_local_link_points_at_a_real_file(self):
        ids = set(guide_ids())
        for page in self.PAGES:
            for ref in refs_of(page):
                if re.match(r"^(https?:|mailto:|#|data:)", ref):
                    continue
                path, _, query = ref.partition("?")
                path = path.split("#")[0]
                target = DOCS / (path + "index.html" if path.endswith("/") or path == "" else path)
                self.assertTrue(target.is_file(), f"{page}: {ref} -> {target} does not exist")
                m = re.match(r"d=([A-Za-z0-9_-]+)", query)
                if path == "guide.html" and m:
                    self.assertIn(m.group(1), ids, f"{page}: {ref} names a guide that is not in guide.js")

    def test_guide_menu_matches_the_markdown_files(self):
        listed = guide_ids()
        self.assertEqual(len(listed), len(set(listed)), "duplicate guide id")
        on_disk = sorted(p.stem for p in DOCS.glob("*.md") if p.name != "README.md")
        self.assertEqual(sorted(listed), on_disk, "docs/*.md and the DOCS list in assets/guide.js differ")

    def test_links_into_the_repository_name_this_repository_and_real_paths(self):
        for page in self.PAGES:
            for ref in refs_of(page):
                if "github.com/Shechterlab" not in ref:
                    continue
                self.assertIn("github.com/Shechterlab/AI_ELN", ref, ref)
                m = re.search(r"/(?:blob|tree)/main/(.+?)(?:#.*)?$", ref)
                if m:
                    self.assertTrue((REPO_ROOT / m.group(1)).exists(), f"{page}: {ref} points at a path that is not in the repo")

    def test_things_the_landing_page_names_exist(self):
        text = (DOCS / "index.html").read_text(encoding="utf-8")
        for launcher in ("Open ELN", "Try the Sandbox"):
            self.assertIn(launcher, text)
            self.assertTrue((REPO_ROOT / "launchers" / f"{launcher}.command").exists(), launcher)
            self.assertTrue((REPO_ROOT / "launchers" / f"{launcher}.cmd").exists(), launcher)
        for image in re.findall(r'src="(img/[^"]+)"', text):
            self.assertTrue((DOCS / image).exists(), image)
        self.assertNotIn("—", text, "house style: no em dashes on the landing page")

    def test_naming_box_uses_the_notebook_library(self):
        # the box cannot drift from the tool: it imports the library the notebook page runs on,
        # and tests/test_js_parity.py checks that library against scripts/eln.py
        site_js = (DOCS / "assets" / "site.js").read_text(encoding="utf-8")
        self.assertIn("from '../app/lib/names.js'", site_js)
        self.assertFalse((DOCS / "assets" / "names.js").exists())
        for page in ("index.html", "guide.html"):
            self.assertRegex((DOCS / page).read_text(encoding="utf-8"), r'<script type="module" src="assets/site\.js')


class TestApp(unittest.TestCase):
    """docs/app/: the notebook page that runs in the browser."""

    APP = DOCS / "app"

    def modules(self):
        return sorted(p.relative_to(self.APP).as_posix() for d in ("lib", "store") for p in (self.APP / d).glob("*.js"))

    def test_every_import_points_at_a_real_file(self):
        sources = [self.APP / "ui.js", self.APP / "sw.js", DOCS / "assets" / "site.js",
                   REPO_ROOT / "mcp" / "server.mjs", REPO_ROOT / "mcp" / "call.mjs", REPO_ROOT / "mcp" / "config.mjs",
                   REPO_ROOT / "tests" / "js_helper.mjs"] + [self.APP / m for m in self.modules()]
        for src in sources:
            for target in re.findall(r"""(?:from|import)\s*\(?\s*['"](\.{1,2}/[^'"]+)['"]""", src.read_text(encoding="utf-8")):
                self.assertTrue((src.parent / target).resolve().is_file(), f"{src.relative_to(REPO_ROOT)} imports {target}")

    def test_browser_code_does_not_load_node_modules(self):
        # anything the page can reach must run in a browser: no node: imports outside store/node.js
        for m in self.modules() + ["ui.js"]:
            if m != "store/node.js":
                self.assertNotIn("node:", (self.APP / m).read_text(encoding="utf-8"), m)

    def test_offline_list_matches_the_files(self):
        sw = (self.APP / "sw.js").read_text(encoding="utf-8")
        listed = json.loads(re.search(r"const FILES = (\[.*?\]);", sw, re.S).group(1))
        expected = ["./", "app.css", "ui.js", "manifest.webmanifest", "../assets/site.css", "../assets/shechterlab-icon.svg"]
        expected += [m for m in self.modules() if m != "store/node.js"]
        self.assertEqual(sorted(listed), sorted(expected), "update FILES in docs/app/sw.js")
        for rel in listed:
            self.assertTrue((self.APP / rel).resolve().exists(), rel)

    def test_page_links_and_manifest(self):
        parser = Links()
        parser.feed((self.APP / "index.html").read_text(encoding="utf-8"))
        for ref in parser.refs:
            if re.match(r"^(https?:|#|data:)", ref):
                continue
            path = ref.split("?")[0].split("#")[0]
            target = (self.APP / path).resolve()
            self.assertTrue(target.is_file() or (target.is_dir() and (target / "index.html").is_file()), ref)
        manifest = json.loads((self.APP / "manifest.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["start_url"], "./")
        self.assertTrue((self.APP / manifest["icons"][0]["src"]).resolve().is_file())
        self.assertEqual(json.loads((self.APP / "package.json").read_text(encoding="utf-8"))["type"], "module")

    def test_no_stray_line_separators(self):
        # U+2028/U+2029 inside a regex or string literal break the script in some engines
        for m in self.modules() + ["ui.js", "sw.js"]:
            text = (self.APP / m).read_text(encoding="utf-8")
            self.assertFalse(any(ch in text for ch in "\u2028\u2029\x85\x0b\x0c"), m)

    @unittest.skipIf(shutil.which("node") is None, "node not available")
    def test_every_script_parses(self):
        for m in self.modules() + ["ui.js", "sw.js"]:
            out = subprocess.run(["node", "--check", str(self.APP / m)], capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)


if __name__ == "__main__":
    unittest.main()
