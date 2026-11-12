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
                target = DOCS / ("index.html" if path in ("./", "") else path)
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

    @unittest.skipIf(shutil.which("node") is None, "node not available")
    def test_naming_box_agrees_with_the_tool(self):
        titles = [
            "SNRPB chromatin retention after PRMT5 inhibition",
            "SNRPB chromatin retention after PRMT5 inhibition: KCl titration",
            "  --weird__chars!!  ",
            "word " * 30,
            "a" * 80,
            "FLAG-SNRPB R107K/R111K chromatin retention, n=3 with K107R/K111R revertant",
            "",
            "été α-tubulin 37°C",
        ]
        script = (
            "const N = require(process.argv[1]); const t = JSON.parse(process.argv[2]);"
            "console.log(JSON.stringify({slugs: t.map(x => N.slugify(x)), folders: t.map(x => N.folderName('JSRe0002', x)),"
            "ids: [N.experimentId('JSR', 2), N.experimentId('AB', '17'), N.experimentId('ABCD', 9999)],"
            "initials: ['jsr', ' ab ', 'toolong', 'j', 'J2'].map(N.cleanInitials), subfolders: N.SUBFOLDERS}))"
        )
        out = subprocess.run(["node", "-e", script, str(DOCS / "assets" / "names.js"), json.dumps(titles)],
                             capture_output=True, text=True, check=True).stdout
        got = json.loads(out)
        self.assertEqual(got["slugs"], [eln.slugify(t) for t in titles])
        self.assertEqual(got["folders"], [f"JSRe0002_{eln.slugify(t)}" if eln.slugify(t) else "JSRe0002" for t in titles])
        self.assertEqual(got["ids"], ["JSRe0002", "ABe0017", "ABCDe9999"])
        for experiment_id in got["ids"]:
            self.assertTrue(eln.RE_EXP_ID.match(experiment_id))
        self.assertEqual(got["initials"], ["JSR", "AB", "", "", ""])
        self.assertEqual(got["subfolders"], eln.SUBFOLDERS)


if __name__ == "__main__":
    unittest.main()
