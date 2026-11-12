"""
The browser notebook, driven in headless Chromium by tests/e2e_app.mjs, then checked by Python.

Creates a notebook from nothing through the page (project, protocol, sample, experiment, edit, add
files, complete, verify, check, brief, export), copies the result to disk, and runs scripts/eln.py on
it: the folder the browser made has to pass the Python validator and the Python manifest check.
Skipped unless Node and the `playwright` package (with its Chromium) are installed.
"""
import importlib.util
import io
import json
import re
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("eln", REPO_ROOT / "scripts" / "eln.py")
eln = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eln)
NODE = shutil.which("node")


def have_playwright() -> bool:
    if NODE is None:
        return False
    probe = "try { require('playwright'); } catch (e) { process.exit(1); }"
    return subprocess.run([NODE, "-e", probe], capture_output=True, cwd=REPO_ROOT).returncode == 0


@unittest.skipUnless(have_playwright(), "node with the playwright package is not available")
class TestBrowserNotebook(unittest.TestCase):
    def test_a_notebook_made_in_the_browser_passes_the_python_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "nb"
            root.mkdir()
            out = subprocess.run([NODE, str(REPO_ROOT / "tests" / "e2e_app.mjs"), "--dump", str(root)],
                                 capture_output=True, text=True, encoding="utf-8", timeout=300)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("all passed", out.stdout)

            vault = eln.load_vault(root)
            self.assertEqual([i.message for i in eln.validate_vault(vault)], [])
            note = vault.by_id["JSRe0001"]
            self.assertEqual(note.get("status"), "complete")
            self.assertEqual(note.get_list("tags"), ["meeting"])
            self.assertEqual(eln.verify_manifest(note.folder, "JSRe0001"), ([], [], []))
            names = sorted(p.name for p in (note.folder / "5-figures").iterdir())
            self.assertEqual(names, ["JSRe0001_R_blot-summary.png", "README.md"])
            self.assertTrue((note.folder / "2-data_raw" / "ChemiDoc 2026-09-04.scn").exists())
            snapshot = next((note.folder / "1-notes").glob("JSRe0001_snapshot_*.html")).read_text(encoding="utf-8")
            # the file list shows sizes as they were when the snapshot was written (it lists itself), so leave them out
            sizes = re.compile(r"<td>[\d,]+</td>")
            self.assertEqual(sizes.sub("", snapshot),
                             sizes.sub("", eln.render_snapshot_html(vault, note, generated=note.get("date_completed"))),
                             "the snapshot the browser wrote is the one Python would write")
            self.assertIn("data:image/png;base64,", snapshot)
            before = {p.name: p.read_bytes() for p in (root / "Inventory").glob("*.csv")}
            eln.write_index(vault, quiet=True)
            self.assertEqual({p.name: p.read_bytes() for p in (root / "Inventory").glob("*.csv")}, before)
            self.assertIn("AI_ELN", (root / "AGENTS.md").read_text(encoding="utf-8"))

            with zipfile.ZipFile(io.BytesIO((Path(tmp) / "e2e-export.eln").read_bytes())) as z:
                self.assertIsNone(z.testzip())
                meta = json.loads(z.read(next(n for n in z.namelist() if n.endswith("ro-crate-metadata.json"))))
                ids = {node.get("identifier") for node in meta["@graph"] if node.get("@type") == "Dataset"}
                self.assertTrue({"JSRe0001", "P_WesternBlot", "JSRa0001", "PRMT5-ChromatinRelease"} <= ids)


if __name__ == "__main__":
    unittest.main()
