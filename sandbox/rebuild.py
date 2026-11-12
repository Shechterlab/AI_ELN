#!/usr/bin/env python3
"""
rebuild.py - (re)create the sandbox: two small, entirely fictional notebooks
to practice on and to show what filled-in notes look like.

    python3 sandbox/rebuild.py        # wipes everything here except this file, README.md, PILOT.md

    sandbox/alex/      Alex Example (ALX): fractionation and western blots, RT-qPCR, an RNA-seq in progress,
                       one experiment adopted from an older folder, one older folder still waiting
    sandbox/jordan/    Jordan Example (JOR): a methyl-site mutant, immunofluorescence, a paused mass-spec
                       experiment, one older folder still waiting

Each is a notebook of its own with a notebook.md. Jordan's notes cite Alex's
samples and experiments by ID (ALXc0001, ALXe0002); those records are in
Alex's folder. Every number in the data files is made up; the Results text
is computed from those files here, so the two always agree. Point any tool
at one notebook with `--root sandbox/alex`, or open `sandbox/` in the
browser page to choose between them.
"""
from __future__ import annotations

import calendar
import os
import statistics
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import eln  # noqa: E402

KEEP = {"README.md", "PILOT.md", "rebuild.py"}
ALEX = HERE / "alex"
JORDAN = HERE / "jordan"
ALX = ("ALX", "Alex Example")
JOR = ("JOR", "Jordan Example")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def wipe() -> None:
    for p in HERE.iterdir():
        if p.name in KEEP or p.name.startswith("."):
            continue
        eln.shutil.rmtree(p) if p.is_dir() else p.unlink()


def backdate(path: Path, to: str) -> None:
    """The templates stamp today's date into a new note; make the whole file say `to` instead."""
    from datetime import date
    today = date.today().isoformat()
    if today != to:
        eln.write_text_lf(path, path.read_text(encoding="utf-8").replace(today, to))


set_field = eln.set_header_field  # line-level header edit, shared with the tool


def fill(path: Path, section: str, text: str) -> None:
    """Replace the text under a '## section' heading."""
    eln.write_text_lf(path, eln.write_section(path.read_text(encoding="utf-8"), section, text))


class Rand:
    """A small fixed random-number generator, so the made-up data is the same on every computer."""

    def __init__(self, seed: int):
        self.state = seed

    def next(self) -> float:
        self.state = (self.state * 1103515245 + 12345) % 2 ** 31
        return self.state / 2 ** 31

    def around(self, mean: float, spread: float) -> float:
        """Roughly bell-shaped around `mean`: the sum of four uniform numbers."""
        return mean + spread * (sum(self.next() for _ in range(4)) - 2.0)


def png(path: Path, bands, width: int = 520, height: int = 200) -> None:
    """A fake blot: white background, dark rectangles ('bands') at given (x0, x1, y0, y1, darkness) boxes."""
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            v = 245
            for x0, x1, y0, y1, dark in bands:
                if x0 <= x < x1 and y0 <= y < y1:
                    v = min(v, 245 - dark)
            if y % 50 == 49 or x % 130 == 129:
                v = min(v, 225)
            row += bytes([v, v, v])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def lanes(intensities, y0, y1):
    """Four lanes across the image with the given darkness values -> band boxes."""
    return [(20 + i * 130, 120 + i * 130, y0, y1, d) for i, d in enumerate(intensities)]


def folder_of(root: Path, exp_id: str) -> Path:
    return next((root / "Experiments").glob(f"{exp_id}_*"))


def raw_files(root: Path, exp_id: str, names) -> None:
    for name in names:
        (folder_of(root, exp_id) / "2-data_raw" / name).write_bytes(b"placeholder instrument file (sandbox)\n")


def run_script(script: Path) -> str:
    """Run an analysis script from a 3-code folder the way a person would; return what it printed."""
    out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, encoding="utf-8", check=True)
    return out.stdout.replace("\r\n", "\n")


def noon(y: int, m: int, d: int) -> int:
    """Noon UTC as a file time: the same calendar day in every time zone a lab is likely to be in."""
    return calendar.timegm((y, m, d, 12, 0, 0))


def old_folder(path: Path, files: dict, day=None) -> None:
    """A folder of files as someone kept them before the notebook. `day` = (y, m, d) of the first file."""
    for i, (name, content) in enumerate(files.items()):
        f = path / name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
        if day:
            os.utime(f, (noon(*day) + i * 86400,) * 2)


def experiment(root: Path, person, title: str, started: str, completed=None, status="active", **kw):
    ini, who = person
    r = eln.create_experiment(root, ini, who, title, index=False, today=started, **kw)
    if completed:
        set_field(r.path, "date_completed", completed)
    if status != "active":
        set_field(r.path, "status", status)
    return r


def protocol(root: Path, name: str, title: str, version: str, purpose: str, materials, steps, log=None) -> None:
    r = eln.create_protocol(root, name, title=title, index=False)
    backdate(r.path, version)
    set_field(r.path, "version", version)
    fill(r.path, "Purpose", purpose)
    fill(r.path, "Materials", "\n".join(f"- {m}" for m in materials))
    fill(r.path, "Procedure", "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)))
    fill(r.path, "Change log", log or f"- {version}: current version\n- 2026-04-01: initial version")


def sample(root: Path, person, stype: str, title: str, source: str, storage: str, created: str):
    r = eln.create_sample(root, person[0], stype, title, source=source, storage=storage, index=False)
    backdate(r.path, created)
    set_field(r.path, "date_created", created)
    return r


FRACTIONATION = ("Sub-cellular fractionation (cytoplasm / nucleoplasm / chromatin)",
                 "Separate cytoplasm, nucleoplasm, and chromatin-bound protein from adherent cells "
                 "with a hypotonic lysis followed by a KCl extraction of the nuclear pellet.",
                 ["Hypotonic buffer: 10 mM HEPES pH 7.9, 10 mM KCl, 1.5 mM MgCl2, 0.34 M sucrose, "
                  "10% glycerol, 1 mM DTT, protease inhibitors",
                  "Nucleoplasm buffer: as above with KCl at the working concentration (300 mM validated in ALXe0001)",
                  "Chromatin release: benzonase in 2x Laemmli"],
                 ["Wash 1x 10 cm dish twice in ice-cold PBS; scrape into 500 uL hypotonic buffer + 0.1% Triton X-100.",
                  "Ice 8 min; spin 1,300 x g 5 min 4C. Supernatant = cytoplasm.",
                  "Resuspend pellet in 250 uL nucleoplasm buffer; ice 30 min; spin 1,700 x g 5 min. Supernatant = nucleoplasm.",
                  "Resuspend pellet in 200 uL 2x Laemmli + benzonase; 10 min RT. = chromatin.",
                  "Load equal cell-equivalents of each fraction."])
WESTERN = ("Western blot (wet transfer, PVDF)", "Standard SDS-PAGE and wet transfer for fraction analysis.",
           ["4-12% Bis-Tris gels", "PVDF, methanol-activated", "5% milk in TBST", "ECL (standard)"],
           ["Load 15 uL per lane; run 150 V 60 min.", "Transfer 30 V 90 min, 4C.",
            "Block 1 h RT; primary overnight 4C; secondary 1 h RT; image on ChemiDoc."])


# --------------------------------------------------------------------------
# Alex Example's notebook
# --------------------------------------------------------------------------

T_TEST = '''\
"""Paired comparison of the SNRPB chromatin fraction, DMSO versus PRMT5i (ALXe0002).

Standard library only. Run it from anywhere:

    python3 3-code/ALXe0002_paired-t-test.py

It reads 4-data_processed/ALXe0002_chromatin-fraction.csv and prints the numbers quoted in Results.
"""
import csv
import math
import statistics
from pathlib import Path

folder = Path(__file__).resolve().parent.parent
with open(folder / "4-data_processed" / "ALXe0002_chromatin-fraction.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

by = {c: [float(r["fraction"]) for r in rows if r["condition"] == c] for c in ("DMSO", "PRMT5i")}
diffs = [b - a for a, b in zip(by["DMSO"], by["PRMT5i"])]
n = len(diffs)
if n != 3:
    raise SystemExit("this script uses constants for exactly three pairs (2 degrees of freedom)")
mean = statistics.mean(diffs)
se = statistics.stdev(diffs) / math.sqrt(n)
t = mean / se
T_CRIT = 4.3027                       # two-sided 95%, 2 degrees of freedom
p = 1 - abs(t) / math.sqrt(t * t + 2)  # exact two-sided p for 2 degrees of freedom

for c in ("DMSO", "PRMT5i"):
    print(f"{c}: mean {statistics.mean(by[c]):.2f}, SD {statistics.stdev(by[c]):.2f}, n = {len(by[c])}")
print(f"paired difference: mean {mean:.2f}, 95% CI [{mean - T_CRIT * se:.2f}, {mean + T_CRIT * se:.2f}]")
print(f"paired t({n - 1}) = {t:.1f}, p = {p:.3f}")
'''

DDCT = '''\
"""Relative expression by the delta-delta-Ct method (ALXe0005).

Standard library only. Run it from anywhere:

    python3 3-code/ALXe0005_ddCt.py

It reads the plate export in 2-data_raw/, writes 4-data_processed/ALXe0005_ddCt.csv, and prints the
fold changes quoted in Results. Reference gene: ACTB. Calibrator: the mean dCt of the DMSO samples.
"""
import csv
import statistics
from pathlib import Path

folder = Path(__file__).resolve().parent.parent
with open(folder / "2-data_raw" / "QuantStudio_20260903_plate1.csv", newline="", encoding="utf-8") as f:
    wells = list(csv.DictReader(f))

ct = {}  # (sample, target) -> mean Ct of the technical replicates
for sample in sorted({w["Sample"] for w in wells}):
    for target in sorted({w["Target"] for w in wells}):
        values = [float(w["Ct"]) for w in wells if w["Sample"] == sample and w["Target"] == target]
        ct[(sample, target)] = statistics.mean(values)

rows = []
for target in ("MDM4-FL", "MDM4-S"):
    dct = {s: ct[(s, target)] - ct[(s, "ACTB")] for (s, t) in ct if t == target}
    calibrator = statistics.mean(v for s, v in dct.items() if s.startswith("DMSO"))
    for sample in sorted(dct):
        ddct = dct[sample] - calibrator
        rows.append({"target": target, "sample": sample, "condition": sample.split("_")[0],
                     "mean_ct": f"{ct[(sample, target)]:.2f}", "dct": f"{dct[sample]:.2f}",
                     "ddct": f"{ddct:.2f}", "fold_change": f"{2 ** -ddct:.2f}"})

out = folder / "4-data_processed" / "ALXe0005_ddCt.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\\n")
    w.writeheader()
    w.writerows(rows)

for target in ("MDM4-FL", "MDM4-S"):
    folds = [float(r["fold_change"]) for r in rows if r["target"] == target and r["condition"] == "PRMT5i"]
    print(f"{target}: PRMT5i / DMSO = {statistics.mean(folds):.2f} "
          f"(replicates {', '.join(f'{x:.2f}' for x in folds)})")
'''


def build_alex() -> None:
    root = ALEX
    root.mkdir()
    eln.ensure_vault_dirs(root)
    eln.set_notebook_owner(root, ALX[1], ALX[0])

    project = root / "Projects" / "PRMT5-ChromatinRelease.md"
    r = eln.create_project(root, "PRMT5-ChromatinRelease",
                           title="PRMT5 inhibition and chromatin release of snRNP proteins", lead=ALX[1], index=False)
    backdate(r.path, "2026-05-20")
    set_field(project, "date_started", "2026-05-20")
    set_field(project, "contributors", ["Jordan Example"])
    fill(project, "Aim / hypothesis",
         "Hypothesis: PRMT5-dependent arginine methylation of Sm proteins (SNRPB in particular) is needed for "
         "snRNPs to be released from chromatin; inhibiting PRMT5 should increase the chromatin-bound fraction of SNRPB.")

    protocol(root, "CellularFractionation", FRACTIONATION[0], "2026-06-10", *FRACTIONATION[1:])
    protocol(root, "WesternBlot", WESTERN[0], "2026-05-02", *WESTERN[1:])
    protocol(root, "RTqPCR", "RT-qPCR (SYBR, 384-well)", "2026-08-20",
             "Measure transcript and isoform levels relative to a reference gene.",
             ["RNA: column prep with on-column DNase", "cDNA: 1 ug RNA, random hexamers", "SYBR master mix, 10 uL reactions",
              "QuantStudio 6, 384-well block"],
             ["Reverse-transcribe 1 ug RNA; include a no-RT control per sample.",
              "Dilute cDNA 1:10; 2 uL per 10 uL reaction; technical triplicates.",
              "40 cycles, 60C annealing; melt curve on every run.",
              "Analyse by delta-delta-Ct against ACTB; discard a technical replicate more than 0.5 Ct from the other two."],
             log="- 2026-08-20: initial version")

    for stype, title, source, storage, created in [
        ("cell-line", "A549 (lung adenocarcinoma)", "ATCC CCL-185, passage 8 at thaw", "LN2 rack 2, box 4, A1-A6", "2026-05-22"),
        ("cell-line", "HeLa", "ATCC CCL-2", "LN2 rack 2, box 4, B1-B4", "2026-06-30"),
        ("antibody", "anti-SNRPB (mouse monoclonal, Sigma S0698)", "Sigma S0698, lot 0000123", "Fridge 4C, door, antibody box 1", "2026-05-25"),
        ("antibody", "anti-U1-70K (rabbit)", "gift, Dreyfuss lab (2025)", "Fridge 4C, door, antibody box 1", "2026-05-25"),
        ("antibody", "anti-histone H3 (rabbit, Abcam ab1791)", "Abcam ab1791", "Fridge 4C, door, antibody box 2", "2026-05-25"),
        ("oligo", "MDM4 isoform qPCR primers (full-length and exon-6-skipped)", "IDT, ordered 2026-08-18", "Freezer -20C A, primer box 2, row D", "2026-08-21"),
    ]:
        sample(root, ALX, stype, title, source, storage, created)
    fill(root / "Samples" / "ALXi0001.md", "Description",
         "Two primer pairs sharing a forward primer in exon 5. MDM4-FL: reverse primer inside exon 6 (full-length "
         "transcript). MDM4-S: reverse primer across the exon 5-7 junction (exon 6 skipped).")

    blots = "P_CellularFractionation, P_WesternBlot"
    e1 = experiment(root, ALX, "Fractionation protocol validation: KCl titration in A549", "2026-06-11", "2026-06-13", "complete",
                    project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot", protocol=blots,
                    samples="ALXc0001, ALXa0002, ALXa0003", notebook="NB03-041")
    fill(e1.path, "Objective", "Validate the fractionation protocol on A549 cells and find the KCl concentration in "
         "nucleoplasm buffer at which U1-70K is released from chromatin, so the protocol can be applied to PRMT5i-treated samples.")
    fill(e1.path, "Experimental design", "A549, untreated. Nucleoplasm buffer at 0, 150, 300, 450 mM KCl. Fractions: cytoplasm, "
         "nucleoplasm, chromatin. Blots: U1-70K (target), GAPDH (cytoplasmic control), histone H3 (chromatin control). n = 1.")
    titration = [(0, 0.88), (150, 0.79), (300, 0.27), (450, 0.08)]
    eln.write_text_lf(folder_of(root, "ALXe0001") / "4-data_processed" / "ALXe0001_U170K-chromatin-fraction.csv",
                      "kcl_mM,chromatin,nucleoplasm,chromatin_fraction\n"
                      + "".join(f"{k},{f:.2f},{1 - f:.2f},{f:.2f}\n" for k, f in titration))
    fill(e1.path, "Results", "GAPDH is cytoplasmic only and H3 chromatin only at every KCl concentration, so the fractionation is clean. "
         f"The chromatin-bound fraction of U1-70K is {titration[0][1]:.2f} without KCl, {titration[1][1]:.2f} at 150 mM, "
         f"{titration[2][1]:.2f} at 300 mM, and {titration[3][1]:.2f} at 450 mM: it moves to the nucleoplasm between 150 and 300 mM.\n\n"
         "![](../5-figures/ALXe0001_R_KCl-titration-U170K_20260613.png)\n\n"
         "Band intensities: `4-data_processed/ALXe0001_U170K-chromatin-fraction.csv`.")
    fill(e1.path, "Interpretation", "The protocol separates the compartments as intended and 300 mM KCl is a usable working "
         "concentration: enough to see salt-dependent release without stripping everything.")
    fill(e1.path, "Decision", "Protocol validated at 300 mM KCl (recorded in P_CellularFractionation). Apply to PRMT5i-treated A549 in ALXe0002.")
    fill(e1.path, "Follow-up experiments", "- [x] ALXe0002")
    raw_files(root, "ALXe0001", ["ChemiDoc_20260612_0931.scn", "ChemiDoc_20260612_0958.scn"])
    png(folder_of(root, "ALXe0001") / "5-figures" / "ALXe0001_R_KCl-titration-U170K_20260613.png",
        lanes([80, 70, 25, 8], 60, 85) + lanes([5, 20, 70, 90], 120, 145))

    e2 = experiment(root, ALX, "SNRPB chromatin retention after 48 h PRMT5 inhibition in A549", "2026-06-20", "2026-07-08", "complete",
                    project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot", protocol=blots,
                    samples="ALXc0001, ALXa0001, ALXa0002, ALXa0003", related="ALXe0001", notebook="NB03-047")
    f2 = folder_of(root, "ALXe0002")
    eln.write_text_lf(f2 / "4-data_processed" / "ALXe0002_chromatin-fraction.csv",
                      "replicate,condition,chromatin,nucleoplasm,fraction\n1,DMSO,0.29,0.71,0.29\n1,PRMT5i,0.55,0.45,0.55\n"
                      "2,DMSO,0.36,0.64,0.36\n2,PRMT5i,0.66,0.34,0.66\n3,DMSO,0.28,0.72,0.28\n3,PRMT5i,0.53,0.47,0.53\n")
    eln.write_text_lf(f2 / "3-code" / "ALXe0002_paired-t-test.py", T_TEST)
    stats = run_script(f2 / "3-code" / "ALXe0002_paired-t-test.py")
    eln.write_text_lf(f2 / "4-data_processed" / "ALXe0002_paired-t-test-output.txt", stats)
    fill(e2.path, "Objective", "Does PRMT5 inhibition increase the chromatin-bound fraction of SNRPB?")
    fill(e2.path, "Experimental design", "A549 treated 48 h with DMSO or PRMT5 inhibitor (EPZ015666, 1 uM). Fractionation at 300 mM KCl "
         "(ALXe0001). Blots: SNRPB, U1-70K, H3, GAPDH. Three independent biological replicates on separate days. "
         "Quantification: chromatin / (chromatin + nucleoplasm) signal per replicate.")
    fill(e2.path, "Results", "SNRPB chromatin fraction, DMSO against PRMT5i, three paired replicates "
         "(output of `3-code/ALXe0002_paired-t-test.py`):\n\n```\n" + stats + "```\n\n"
         "U1-70K shifted in the same direction but less (0.40 to 0.49). Loading controls behaved.\n\n"
         "![](../5-figures/ALXe0002_R_SNRPB-chromatin-fraction_20260708.png)\n\nQuantification: `4-data_processed/ALXe0002_chromatin-fraction.csv`.")
    fill(e2.path, "Interpretation", "Consistent with the hypothesis: loss of PRMT5 activity keeps more SNRPB on chromatin. "
         "Symmetric dimethyl-arginine loss was not directly confirmed in this experiment (no SDMA blot).")
    fill(e2.path, "Decision", "Repeat in a second cell line (ALXe0003) and test whether the methyl-site mutant phenocopies (JORe0001, in Jordan's notebook).")
    fill(e2.path, "Follow-up experiments", "- [x] ALXe0003 second cell line\n- [x] JORe0001 R107K/R111K mutant\n- [ ] SDMA blot on the same lysates")
    raw_files(root, "ALXe0002", ["ChemiDoc_20260706_1402.scn", "ChemiDoc_20260707_1015.scn", "ChemiDoc_20260708_0947.scn"])
    png(f2 / "5-figures" / "ALXe0002_R_SNRPB-chromatin-fraction_20260708.png",
        lanes([35, 90, 40, 95], 60, 85) + lanes([90, 90, 90, 90], 120, 145))

    e3 = experiment(root, ALX, "SNRPB chromatin retention after PRMT5 inhibition in HeLa", "2026-07-14", "2026-07-25", "complete",
                    project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot", protocol=blots,
                    samples="ALXc0002, ALXa0001, ALXa0003", related="ALXe0002", notebook="NB03-052")
    fill(e3.path, "Objective", "Is the PRMT5i effect on SNRPB chromatin retention (ALXe0002) specific to A549?")
    fill(e3.path, "Experimental design", "As ALXe0002 but in HeLa. n = 2.")
    fill(e3.path, "Results", "SNRPB chromatin fraction 0.28 and 0.30 (DMSO) vs 0.41 and 0.46 (PRMT5i). Same direction as A549, "
         "smaller magnitude. The second replicate had a weak H3 signal in the nucleoplasm lane, suggesting slight chromatin carry-over.\n\n"
         "![](../5-figures/ALXe0003_R_SNRPB-chromatin-fraction-HeLa_20260725.png)")
    fill(e3.path, "Interpretation", "Effect reproduces in a second cell line, so it is not an A549 peculiarity. With n = 2 and one "
         "imperfect fractionation this is supporting, not conclusive.")
    fill(e3.path, "Decision", "Treat the A549 result as the primary finding; HeLa as supporting. No further HeLa replicates planned unless a reviewer asks.")
    eln.write_text_lf(folder_of(root, "ALXe0003") / "4-data_processed" / "ALXe0003_chromatin-fraction.csv",
                      "replicate,condition,fraction\n1,DMSO,0.28\n1,PRMT5i,0.41\n2,DMSO,0.30\n2,PRMT5i,0.46\n")
    raw_files(root, "ALXe0003", ["ChemiDoc_20260724_1130.scn"])
    png(folder_of(root, "ALXe0003") / "5-figures" / "ALXe0003_R_SNRPB-chromatin-fraction-HeLa_20260725.png",
        lanes([30, 60, 32, 70], 60, 85) + lanes([90, 90, 90, 95], 120, 145))

    e4 = experiment(root, ALX, "RNA-seq after 48 h PRMT5 inhibition in A549", "2026-08-25", None, "active",
                    project="PRMT5-ChromatinRelease", exp_type="RNAseq", protocol="P_CellularFractionation",
                    samples="ALXc0001", related="ALXe0002", notebook="NB03-060", tags="meeting")
    set_field(e4.path, "raw_data_path", "smb://einstein-storage/shechterlab/rnaseq/2026-09_ALXe0004")
    fill(e4.path, "Objective", "Which transcripts change splicing or abundance when PRMT5 is inhibited under the same conditions "
         "that increase SNRPB chromatin retention (ALXe0002)?")
    fill(e4.path, "Experimental design", "A549, DMSO vs PRMT5i 48 h, 3 replicates each, poly-A RNA-seq, 50M paired-end reads per sample. "
         "Libraries submitted to the genomics core 2026-09-02.")
    fill(e4.path, "Results", "Awaiting sequencing (expected week of 2026-09-15).")
    fill(e4.path, "Decision", "Analysis plan to pre-register before data arrive: differential intron retention (rMATS) as the "
         "confirmatory test; everything else exploratory.")
    eln.write_text_lf(folder_of(root, "ALXe0004") / "2-data_raw" / "README.md",
                      "# 2-data_raw\n\nFASTQ files are on institutional storage (see `raw_data_path` in the note); "
                      "nothing is kept here.\n")

    # RT-qPCR: a made-up plate export, the script that analyses it, and Results written from the script's output
    e5 = experiment(root, ALX, "RT-qPCR of MDM4 isoforms after 48 h PRMT5 inhibition in A549", "2026-09-01", None, "active",
                    project="PRMT5-ChromatinRelease", exp_type="qPCR", protocol="P_RTqPCR",
                    samples="ALXc0001, ALXi0001", related="ALXe0002, ALXe0004", notebook="NB03-063", tags="meeting")
    f5 = folder_of(root, "ALXe0005")
    rand = Rand(20260903)
    centre = {("ACTB", "DMSO"): 17.0, ("ACTB", "PRMT5i"): 17.1, ("MDM4-FL", "DMSO"): 24.0, ("MDM4-FL", "PRMT5i"): 25.3,
              ("MDM4-S", "DMSO"): 27.6, ("MDM4-S", "PRMT5i"): 25.5}
    lines, well = ["Well,Sample,Target,Ct"], 0
    for condition in ("DMSO", "PRMT5i"):
        for rep in (1, 2, 3):
            shift = rand.around(0, 0.25)  # how much RNA went into this sample
            for target in ("ACTB", "MDM4-FL", "MDM4-S"):
                bio = rand.around(0, 0.18)
                for _tech in range(3):
                    ct = centre[(target, condition)] + shift + bio + rand.around(0, 0.08)
                    lines.append(f"{'ABCDEFGHIJKLMNOP'[well // 24]}{well % 24 + 1},{condition}_{rep},{target},{ct:.2f}")
                    well += 1
    eln.write_text_lf(f5 / "2-data_raw" / "QuantStudio_20260903_plate1.csv", "\n".join(lines) + "\n")
    eln.write_text_lf(f5 / "3-code" / "ALXe0005_ddCt.py", DDCT)
    folds = run_script(f5 / "3-code" / "ALXe0005_ddCt.py")
    fill(e5.path, "Objective", "Before the RNA-seq (ALXe0004) comes back: does PRMT5 inhibition shift MDM4 from the full-length "
         "isoform to the exon-6-skipped isoform in A549, as reported for other cell types?")
    fill(e5.path, "Experimental design", "A549, DMSO vs PRMT5i (EPZ015666, 1 uM) 48 h, three biological replicates per condition "
         "(the same RNA preparations as the RNA-seq libraries). Targets: MDM4-FL, MDM4-S (primers ALXi0001), reference ACTB. "
         "Technical triplicates. Prediction if the hypothesis holds: MDM4-FL goes down and MDM4-S goes up.")
    fill(e5.path, "Results", "Preliminary: one plate, analysed by delta-delta-Ct against ACTB "
         "(output of `3-code/ALXe0005_ddCt.py`, fold change relative to the mean of the DMSO samples):\n\n```\n" + folds + "```\n\n"
         "Per-sample values: `4-data_processed/ALXe0005_ddCt.csv`. Melt curves showed one peak for every target. "
         "No-RT controls have not been run yet.")
    fill(e5.path, "Interpretation", "Preliminary. The direction matches the prediction for both isoforms. Without the no-RT "
         "controls, a contribution of genomic DNA to the MDM4-FL signal is not ruled out.")
    fill(e5.path, "Follow-up experiments", "- [ ] no-RT controls on the same cDNA\n- [ ] compare with the junction counts from ALXe0004 when they arrive")

    fill(project, "Current state", """\
<!-- Kept short and current. Update this section in place; don't append to it. -->

### Supported conclusions

- 48 h PRMT5 inhibition roughly doubles the chromatin-bound fraction of SNRPB in A549 (ALXe0002, n = 3); the same direction is seen in HeLa (ALXe0003, n = 2).
- The fractionation protocol cleanly separates compartments at 300 mM KCl (ALXe0001).

### Open questions / conflicting observations

- Immunofluorescence shows no redistribution of SNRPB after PRMT5i (JORe0002, Jordan's notebook), which does not fit a simple relocalization model for the biochemical shift in ALXe0002. Extraction resistance is the leading alternative; JORe0004 tests it.
- Whether the effect is mediated by SNRPB's own methylation is suggested by the R107K/R111K mutant (JORe0001, Jordan's notebook) but not established.
- MDM4 isoform switch after PRMT5i looks as predicted in a first qPCR plate (ALXe0005, preliminary, no-RT controls missing).

### Experiments needing replication

- JORe0001 (n = 1; mutant migrates slower, unexplained).
""")
    fill(project, "Experiments",
         "- ALXe0001 - fractionation validation - complete\n- ALXe0002 - PRMT5i, A549 - complete\n- ALXe0003 - PRMT5i, HeLa - complete\n"
         "- ALXe0004 - RNA-seq - active\n- ALXe0005 - MDM4 isoform qPCR - active\n- ALXe0006 - growth curve, adopted from an older folder\n"
         "- In Jordan Example's notebook: JORe0001 (R107K/R111K mutant), JORe0002 (IF), JORe0004 (pre-extraction IF)")
    fill(project, "Reagents in use", "ALXc0001, ALXc0002, ALXa0001, ALXa0002, ALXa0003, ALXi0001; Jordan's plasmids JORp0001, JORp0002")
    fill(project, "Related protocols", "P_CellularFractionation, P_WesternBlot, P_RTqPCR")

    # ALXe0002 closed out the way the tool does it: snapshot + manifest, dated to its completion.
    eln.complete_experiment(root, "ALXe0002", when="2026-07-08")

    # An older folder, from before the notebook, adopted as it was: it becomes ALXe0006.
    rand = Rand(20251118)
    counts = ["day,dose_uM,well,cells_x1e4"]
    for day in range(5):
        for dose, rate in ((0, 0.62), (0.1, 0.60), (1, 0.52), (10, 0.31)):
            for well in (1, 2, 3):
                counts.append(f"{day},{dose},{well},{2.0 * 2.718281828 ** (rate * day) * (1 + rand.around(0, 0.06)):.1f}")
    old = root / "2025-11-18_A549 growth curve EPZ015666 dose"
    old_folder(old, {
        "counts.csv": "\n".join(counts) + "\n",
        "plate map.txt": "12-well plates, one per day. Rows: 0, 0.1, 1, 10 uM EPZ015666. Three wells per dose.\nSeeded 2 x 10^4 cells per well on day 0.\n",
        "notes.txt": "Counted on the Countess, trypan blue. Day 3 plate was out of the incubator ~20 min while the scope was busy.\n",
        "photos/day4_10uM.png": b"",
    }, day=(2025, 11, 18))
    png(old / "photos" / "day4_10uM.png", lanes([30, 20, 25, 15], 40, 160))
    os.utime(old / "photos" / "day4_10uM.png", (noon(2025, 11, 22),) * 2)
    eln.adopt_folder(root, old, ALX[0], ALX[1], project="PRMT5-ChromatinRelease", today="2026-03-02")

    # ... and one that has not been adopted yet. Home shows "Adopt older folders" because of it.
    old_folder(root / "2026-02-10_HeLa transfection test", {
        "lipofectamine ratios.csv": "ratio_ul_per_ug,GFP_positive_percent\n1.5,22\n2.0,41\n3.0,58\n4.0,55\n",
        "notes.txt": "GFP plasmid, 24 h, counted 200 cells per well by eye. 3:1 looked best; 4:1 had more floating cells.\n",
    })

    eln.write_index(eln.load_vault(root), quiet=True)


# --------------------------------------------------------------------------
# Jordan Example's notebook
# --------------------------------------------------------------------------

SUMMARISE = '''\
"""Per-condition summary of the pre-extraction immunofluorescence scores (JORe0004).

Standard library only. Run it from anywhere:

    python3 3-code/JORe0004_summarise.py

It reads 4-data_processed/JORe0004_retained-signal.csv and prints the numbers quoted in Results.
"""
import csv
import statistics
from pathlib import Path

folder = Path(__file__).resolve().parent.parent
with open(folder / "4-data_processed" / "JORe0004_retained-signal.csv", newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for condition in ("DMSO", "PRMT5i"):
    values = [float(r["snrpb_over_dapi"]) for r in rows if r["condition"] == condition]
    q = statistics.quantiles(values, n=4)
    print(f"{condition}: median {statistics.median(values):.2f}, quartiles {q[0]:.2f} to {q[2]:.2f}, {len(values)} nuclei")
'''


def build_jordan() -> None:
    root = JORDAN
    root.mkdir()
    eln.ensure_vault_dirs(root)
    eln.set_notebook_owner(root, JOR[1], JOR[0])

    methyl = root / "Projects" / "SNRPB-ArginineMethylation.md"
    r = eln.create_project(root, "SNRPB-ArginineMethylation",
                           title="Mapping arginine methylation sites on SNRPB", lead=JOR[1], index=False)
    backdate(r.path, "2026-07-01")
    set_field(methyl, "date_started", "2026-07-01")
    fill(methyl, "Aim / hypothesis",
         "Which arginines on SNRPB are methylated by PRMT5 in cells, and which of them matter for chromatin release?")
    release = root / "Projects" / "PRMT5-ChromatinRelease.md"
    r = eln.create_project(root, "PRMT5-ChromatinRelease",
                           title="PRMT5 inhibition and chromatin release of snRNP proteins (Jordan's part)", lead="Alex Example", index=False)
    backdate(r.path, "2026-07-20")
    set_field(release, "date_started", "2026-07-20")
    set_field(release, "contributors", ["Jordan Example"])
    fill(release, "Aim / hypothesis",
         "Alex Example leads this project; the full project page is in Alex's notebook. This page covers the experiments "
         "in this notebook: does the methyl-site mutant of SNRPB behave like PRMT5 inhibition, and is the chromatin shift visible by microscopy?")

    protocol(root, "CellularFractionation", FRACTIONATION[0], "2026-06-10", *FRACTIONATION[1:],
             log="- 2026-07-18: copied from Alex Example's notebook at version 2026-06-10, unchanged")
    protocol(root, "WesternBlot", WESTERN[0], "2026-05-02", *WESTERN[1:],
             log="- 2026-07-18: copied from Alex Example's notebook at version 2026-05-02, unchanged")
    protocol(root, "Immunofluorescence", "Immunofluorescence on coverslips", "2026-08-18",
             "Fix, permeabilize, and stain adherent cells on coverslips for confocal imaging.",
             ["4% PFA in PBS", "0.2% Triton X-100", "3% BSA", "DAPI", "ProLong Glass",
              "Pre-extraction buffer (optional): CSK with 0.1% Triton X-100, on ice"],
             ["Optional pre-extraction: CSK + 0.1% Triton X-100, 3 min on ice, before fixing. Removes soluble protein.",
              "Fix 10 min RT; permeabilize 5 min; block 30 min.",
              "Primary 1 h RT; secondary 45 min RT in the dark; DAPI 5 min; mount."],
             log="- 2026-08-18: added the optional pre-extraction step (first used in JORe0004)\n- 2026-07-15: initial version")
    protocol(root, "FLAG-IP", "Anti-FLAG immunoprecipitation for mass spectrometry", "2026-08-10",
             "Purify FLAG-tagged protein from transfected cells with as little keratin and antibody carry-over as possible.",
             ["Anti-FLAG M2 magnetic beads", "Lysis buffer: 50 mM Tris pH 7.5, 150 mM NaCl, 0.5% NP-40, protease and phosphatase inhibitors",
              "3x FLAG peptide", "Low-bind tubes"],
             ["Lyse 4x 15 cm dishes per condition in 1 mL each; clear 16,000 x g 10 min 4C.",
              "Bind to 40 uL beads 2 h 4C; wash 4x lysis buffer, 2x 50 mM ammonium bicarbonate.",
              "Elute with 3x FLAG peptide or digest on bead; freeze at -80C."],
             log="- 2026-08-10: initial version")

    sample(root, JOR, "plasmid", "pcDNA3-FLAG-SNRPB wild type", "in-house, cloned 2026-06 (see NB04-012)", "Freezer -20C B, box 3, C4", "2026-06-18")
    sample(root, JOR, "plasmid", "pcDNA3-FLAG-SNRPB R107K/R111K", "in-house, site-directed mutagenesis from JORp0001", "Freezer -20C B, box 3, C5", "2026-06-25")
    fill(root / "Samples" / "JORp0002.md", "Description",
         "SNRPB with both arginines of the C-terminal RG-rich region that PRMT5 is reported to methylate "
         "(R107, R111) changed to lysine. Sequence-verified 2026-06-25.")
    fill(root / "Samples" / "JORp0002.md", "Validation", "Expression confirmed by anti-FLAG western in JORe0001.")

    # ALXc0001 (A549), ALXa0001 and ALXa0003 (antibodies) are Alex's records: cited by ID, kept in Alex's notebook.
    j1 = experiment(root, JOR, "Chromatin retention of FLAG-SNRPB R107K/R111K versus wild type", "2026-07-20", "2026-07-29", "complete",
                    project="PRMT5-ChromatinRelease, SNRPB-ArginineMethylation", exp_type="Fractionation, WesternBlot",
                    protocol="P_CellularFractionation, P_WesternBlot", samples="ALXc0001, JORp0001, JORp0002, ALXa0003",
                    related="ALXe0002", notebook="NB04-018")
    fill(j1.path, "Objective", "Does removing the PRMT5 target arginines on SNRPB (R107K/R111K) phenocopy PRMT5 inhibition (ALXe0002, Alex's notebook)?")
    fill(j1.path, "Experimental design", "A549 (ALXc0001, from Alex) transfected with FLAG-SNRPB WT (JORp0001) or R107K/R111K (JORp0002); 24 h; "
         "fractionation at 300 mM KCl; anti-FLAG blot. n = 1.")
    fill(j1.path, "Results", "FLAG signal chromatin fraction: WT 0.33, mutant 0.55. Expression of both constructs comparable in whole-cell input.\n\n"
         "![](../5-figures/JORe0001_R_FLAG-SNRPB-WT-vs-RK_20260729.png)\n\nBand intensities: `4-data_processed/JORe0001_FLAG-chromatin-fraction.csv`.")
    fill(j1.path, "Interpretation", "The methyl-site mutant is more chromatin-bound, the same direction as PRMT5 inhibition. "
         "Single replicate; the mutant also migrates slightly slower, which needs an explanation before this is trusted.")
    fill(j1.path, "Decision", "Repeat with n = 3 and include a K107R/K111R revertant control before this goes in a figure.")
    fill(j1.path, "Follow-up experiments", "- [ ] n = 3 repeat with revertant control")
    eln.write_text_lf(folder_of(root, "JORe0001") / "4-data_processed" / "JORe0001_FLAG-chromatin-fraction.csv",
                      "construct,chromatin,nucleoplasm,fraction\nWT,0.33,0.67,0.33\nR107K/R111K,0.55,0.45,0.55\n")
    raw_files(root, "JORe0001", ["ChemiDoc_20260728_1607.scn"])
    png(folder_of(root, "JORe0001") / "5-figures" / "JORe0001_R_FLAG-SNRPB-WT-vs-RK_20260729.png",
        lanes([40, 85, 0, 0], 60, 85) + lanes([90, 90, 0, 0], 120, 145))

    j2 = experiment(root, JOR, "SNRPB localization by immunofluorescence after PRMT5 inhibition", "2026-08-04", "2026-08-12", "complete",
                    project="PRMT5-ChromatinRelease", exp_type="IF, Microscopy",
                    protocol="P_Immunofluorescence", samples="ALXc0001, ALXa0001", related="ALXe0002", notebook="NB04-023")
    rand = Rand(20260811)
    scores = {"DMSO": [], "PRMT5i": []}
    for condition, speckles, diffuse in (("DMSO", 18.0, 0.42), ("PRMT5i", 18.8, 0.44)):
        for nucleus in range(1, 31):
            scores[condition].append((nucleus, round(rand.around(speckles, 5.0)), rand.around(diffuse, 0.07)))
    eln.write_text_lf(folder_of(root, "JORe0002") / "4-data_processed" / "JORe0002_speckle-scores.csv",
                      "nucleus,condition,speckles,diffuse_fraction\n"
                      + "".join(f"{n},{c},{s},{d:.2f}\n" for c in scores for n, s, d in scores[c]))
    med = {c: statistics.median(s for _, s, _ in scores[c]) for c in scores}
    dif = {c: statistics.mean(d for _, _, d in scores[c]) for c in scores}
    fill(j2.path, "Objective", "Is the increased chromatin fraction of SNRPB after PRMT5i (ALXe0002) visible as a change in nuclear distribution?")
    fill(j2.path, "Experimental design", "A549, 48 h DMSO vs PRMT5i (1 uM), anti-SNRPB IF, DAPI, confocal, 30 nuclei per condition, "
         "two coverslips per condition on two days. Scored: speckle count per nucleus and fraction of signal outside speckles.")
    fill(j2.path, "Results", f"No clear change in speckle number (median {med['DMSO']:g} in DMSO, {med['PRMT5i']:g} after PRMT5i) or in the "
         f"diffuse nucleoplasmic signal fraction (mean {dif['DMSO']:.2f} and {dif['PRMT5i']:.2f}); 30 nuclei per condition. "
         "Speckles looked slightly larger after PRMT5i but this was not quantified.\n\n"
         "Scores per nucleus: `4-data_processed/JORe0002_speckle-scores.csv`.")
    fill(j2.path, "Interpretation", "Conflicts with the simple reading of ALXe0002: a biochemical shift to the chromatin fraction is "
         "not accompanied by a visible redistribution. Either the change is below IF resolution, or the fractionation shift "
         "reflects extraction resistance rather than localization.")
    fill(j2.path, "Decision", "Discussed at lab meeting 2026-08-14. Next: pre-extraction IF (0.1% Triton before fixation) to ask about extraction resistance directly: JORe0004.")
    fill(j2.path, "Follow-up experiments", "- [x] pre-extraction IF: JORe0004")
    raw_files(root, "JORe0002", ["LSM980_20260811_slide01.czi", "LSM980_20260811_slide02.czi", "LSM980_20260812_slide03.czi"])

    j3 = experiment(root, JOR, "Arginine methylation sites on SNRPB by mass spectrometry", "2026-08-15", None, "paused",
                    project="SNRPB-ArginineMethylation", exp_type="MassSpec, IP", protocol="P_FLAG-IP",
                    samples="ALXc0001, JORp0001", notebook="NB04-030")
    fill(j3.path, "Objective", "Identify methylated arginines on FLAG-SNRPB immunoprecipitated from A549, with and without PRMT5i.")
    fill(j3.path, "Experimental design", "FLAG IP from 4x 15 cm dishes per condition; on-bead trypsin and Arg-C digests; LC-MS/MS at the proteomics core.")
    fill(j3.path, "Decision", "Paused 2026-09-01: proteomics core queue is 6 weeks; IP eluates are at -80C (JOR box 7). Resume when a slot is confirmed.")

    # Pre-extraction IF: made-up per-nucleus intensities, a script that summarises them, Results from its output
    j4 = experiment(root, JOR, "Pre-extraction immunofluorescence of SNRPB after PRMT5 inhibition", "2026-08-24", None, "active",
                    project="PRMT5-ChromatinRelease", exp_type="IF, Microscopy", protocol="P_Immunofluorescence",
                    samples="ALXc0001, ALXa0001", related="JORe0002, ALXe0002", notebook="NB04-034", tags="meeting")
    f4 = folder_of(root, "JORe0004")
    rand = Rand(20260902)
    rows = ["nucleus,condition,snrpb_over_dapi"]
    for condition, level in (("DMSO", 0.34), ("PRMT5i", 0.51)):
        for nucleus in range(1, 26):
            rows.append(f"{nucleus},{condition},{max(0.05, rand.around(level, 0.16)):.2f}")
    eln.write_text_lf(f4 / "4-data_processed" / "JORe0004_retained-signal.csv", "\n".join(rows) + "\n")
    eln.write_text_lf(f4 / "3-code" / "JORe0004_summarise.py", SUMMARISE)
    summary = run_script(f4 / "3-code" / "JORe0004_summarise.py")
    fill(j4.path, "Objective", "JORe0002 saw no redistribution of SNRPB after PRMT5i. Is more SNRPB left in the nucleus after "
         "soluble protein is extracted before fixation, as the fractionation result (ALXe0002) would predict?")
    fill(j4.path, "Experimental design", "A549, 48 h DMSO vs PRMT5i (1 uM). Pre-extraction: CSK + 0.1% Triton X-100, 3 min on ice, then fix "
         "(P_Immunofluorescence, optional step). Anti-SNRPB, DAPI, confocal, same settings for both conditions. Measured: mean nuclear "
         "SNRPB intensity divided by mean DAPI intensity, 25 nuclei per condition. So far one coverslip per condition, one day.")
    fill(j4.path, "Results", "Preliminary: one coverslip per condition (output of `3-code/JORe0004_summarise.py`):\n\n```\n" + summary + "```\n\n"
         "Values per nucleus: `4-data_processed/JORe0004_retained-signal.csv`. The images were scored knowing which coverslip was which.")
    fill(j4.path, "Interpretation", "Preliminary, n = 1 coverslip per condition and not scored blind. More SNRPB signal survives pre-extraction after "
         "PRMT5i, which is what extraction resistance would look like and would reconcile JORe0002 with ALXe0002.")
    fill(j4.path, "Follow-up experiments", "- [ ] two more days, coverslips coded by someone else before scoring\n- [ ] H3 as a pre-extraction-resistant control")
    raw_files(root, "JORe0004", ["LSM980_20260902_preext_DMSO.czi", "LSM980_20260902_preext_PRMT5i.czi"])

    fill(release, "Current state", """\
<!-- Kept short and current. Update this section in place; don't append to it. -->

### Supported conclusions

- None from this notebook alone yet. The primary finding (PRMT5i increases the chromatin-bound fraction of SNRPB) is ALXe0002, in Alex's notebook.

### Open questions / conflicting observations

- No redistribution of SNRPB by standard immunofluorescence (JORe0002).
- More SNRPB survives pre-extraction after PRMT5i in a first, unblinded coverslip pair (JORe0004, preliminary).
- The R107K/R111K mutant is more chromatin-bound than wild type (JORe0001, n = 1; it also migrates slower, unexplained).

### Experiments needing replication

- JORe0001 (n = 1).
- JORe0004 (one coverslip per condition, not blind).
""")
    fill(release, "Experiments", "- JORe0001 - R107K/R111K mutant - complete (n = 1)\n- JORe0002 - IF localization - complete\n"
         "- JORe0004 - pre-extraction IF - active\n- In Alex Example's notebook: ALXe0001 to ALXe0005")
    fill(release, "Reagents in use", "JORp0001, JORp0002; from Alex's notebook: ALXc0001, ALXa0001, ALXa0003")
    fill(release, "Related protocols", "P_CellularFractionation, P_WesternBlot, P_Immunofluorescence")
    fill(methyl, "Experiments", "- JORe0001 - R107K/R111K mutant - complete (n = 1)\n- JORe0003 - methylation sites by mass spectrometry - paused")
    fill(methyl, "Reagents in use", "JORp0001, JORp0002")
    fill(methyl, "Related protocols", "P_FLAG-IP, P_WesternBlot")

    eln.complete_experiment(root, "JORe0001", when="2026-07-29")

    # An older folder that has not been adopted yet.
    old = root / "2026-05-28_colony PCR FLAG-SNRPB clones"
    old_folder(old, {
        "clones.txt": "Clones 1-8 picked from the FLAG-SNRPB ligation plate. Expected band 1.1 kb.\nPositive: 2, 3, 5, 8. Clone 3 sent for sequencing -> became JORp0001.\n",
        "gel.png": b"",
    })
    png(old / "gel.png", lanes([0, 80, 85, 0], 90, 110) + lanes([75, 0, 0, 80], 90, 110))

    eln.write_index(eln.load_vault(root), quiet=True)


if __name__ == "__main__":
    wipe()
    build_alex()
    build_jordan()
    print(f"Rebuilt the sandbox notebooks at {ALEX} and {JORDAN}")
