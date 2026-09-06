#!/usr/bin/env python3
"""
rebuild.py - (re)create the sandbox: a small, entirely fictional research
record to practice on and to show what filled-in notes look like.

    python3 sandbox/rebuild.py        # wipes everything here except this file, README.md, PILOT.md

Two made-up researchers (Alex Example, ALX; Jordan Example, JOR), two
projects, three protocols, seven samples, seven experiments in every
status. Nothing in it is real data. Point any tool at it with
`--root sandbox` (or `AI_ELN_ROOT=sandbox`), or double-click
`launchers/Try the Sandbox`.
"""
from __future__ import annotations

import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))
import eln  # noqa: E402

KEEP = {"README.md", "PILOT.md", "rebuild.py"}
ALX = ("ALX", "Alex Example")
JOR = ("JOR", "Jordan Example")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def wipe() -> None:
    for p in HERE.iterdir():
        if p.name in KEEP or p.name.startswith("."):
            continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()


def backdate(path: Path, to: str) -> None:
    """The templates stamp today's date into the body byline; make the whole file say `to` instead."""
    from datetime import date
    today = date.today().isoformat()
    if today != to:
        path.write_text(path.read_text(encoding="utf-8").replace(today, to), encoding="utf-8")


set_field = eln.set_header_field  # line-level header edit, shared with the tool


def fill(path: Path, section: str, text: str) -> None:
    """Replace the body of a '## section' with text (keeps the header line)."""
    t = path.read_text(encoding="utf-8")
    pattern = rf"(## {re.escape(section)}\n)(.*?)(?=\n## |\n---\n|\Z)"
    new, n = re.subn(pattern, lambda m: m.group(1) + "\n" + text.strip() + "\n", t, count=1, flags=re.S)
    if not n:
        raise KeyError(section)
    path.write_text(new, encoding="utf-8")


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


def folder_of(exp_id: str) -> Path:
    return next((HERE / "Experiments").glob(f"{exp_id}_*"))


def note_of(exp_id: str) -> Path:
    return folder_of(exp_id) / "1-notes" / f"{exp_id}.md"


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def build() -> None:
    root = HERE
    eln.ensure_vault_dirs(root)

    # projects
    r = eln.create_project(root, "PRMT5-ChromatinRelease",
                           title="PRMT5 inhibition and chromatin release of snRNP proteins", lead=ALX[1], index=False)
    backdate(r.path, "2026-05-20")
    set_field(root / "Projects" / "PRMT5-ChromatinRelease.md", "date_started", "2026-05-20")
    set_field(root / "Projects" / "PRMT5-ChromatinRelease.md", "contributors", ["Jordan Example"])
    fill(root / "Projects" / "PRMT5-ChromatinRelease.md", "Aim / hypothesis",
         "Hypothesis: PRMT5-dependent arginine methylation of Sm proteins (SNRPB in particular) is needed for "
         "snRNPs to be released from chromatin; inhibiting PRMT5 should increase the chromatin-bound fraction of SNRPB.")
    r = eln.create_project(root, "SNRPB-ArginineMethylation",
                           title="Mapping arginine methylation sites on SNRPB", lead=JOR[1], index=False)
    backdate(r.path, "2026-07-01")
    set_field(root / "Projects" / "SNRPB-ArginineMethylation.md", "date_started", "2026-07-01")
    fill(root / "Projects" / "SNRPB-ArginineMethylation.md", "Aim / hypothesis",
         "Which arginines on SNRPB are methylated by PRMT5 in cells, and which of them matter for chromatin release?")

    # protocols (set versions before experiments so snapshots carry the right date)
    protocols = {
        "CellularFractionation": ("Sub-cellular fractionation (cytoplasm / nucleoplasm / chromatin)", "2026-06-10",
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
                                   "Load equal cell-equivalents of each fraction."]),
        "WesternBlot": ("Western blot (wet transfer, PVDF)", "2026-05-02",
                        "Standard SDS-PAGE and wet transfer for fraction analysis.",
                        ["4-12% Bis-Tris gels", "PVDF, methanol-activated", "5% milk in TBST", "ECL (standard)"],
                        ["Load 15 uL per lane; run 150 V 60 min.", "Transfer 30 V 90 min, 4C.",
                         "Block 1 h RT; primary overnight 4C; secondary 1 h RT; image on ChemiDoc."]),
        "Immunofluorescence": ("Immunofluorescence on coverslips", "2026-07-15",
                               "Fix, permeabilize, and stain adherent cells on coverslips for confocal imaging.",
                               ["4% PFA in PBS", "0.2% Triton X-100", "3% BSA", "DAPI", "ProLong Glass"],
                               ["Fix 10 min RT; permeabilize 5 min; block 30 min.",
                                "Primary 1 h RT; secondary 45 min RT in the dark; DAPI 5 min; mount."]),
    }
    for name, (title, version, purpose, materials, steps) in protocols.items():
        r = eln.create_protocol(root, name, title=title, index=False)
        backdate(r.path, version)
        set_field(r.path, "version", version)
        fill(r.path, "Purpose", purpose)
        fill(r.path, "Materials", "\n".join(f"- {m}" for m in materials))
        fill(r.path, "Procedure", "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps)))
        fill(r.path, "Change log", f"- {version}: current version\n- 2026-04-01: initial version")

    # samples
    samples = [
        (ALX, "cell-line", "A549 (lung adenocarcinoma)", "ATCC CCL-185, passage 8 at thaw", "LN2 rack 2, box 4, A1-A6", "2026-05-22"),
        (ALX, "cell-line", "HeLa", "ATCC CCL-2", "LN2 rack 2, box 4, B1-B4", "2026-06-30"),
        (ALX, "antibody", "anti-SNRPB (mouse monoclonal, Sigma S0698)", "Sigma S0698, lot 0000123", "Fridge 4C, door, antibody box 1", "2026-05-25"),
        (ALX, "antibody", "anti-U1-70K (rabbit)", "gift, Dreyfuss lab (2025)", "Fridge 4C, door, antibody box 1", "2026-05-25"),
        (ALX, "antibody", "anti-histone H3 (rabbit, Abcam ab1791)", "Abcam ab1791", "Fridge 4C, door, antibody box 2", "2026-05-25"),
        (JOR, "plasmid", "pcDNA3-FLAG-SNRPB wild type", "in-house, cloned 2026-06 (see NB04-012)", "Freezer -20C B, box 3, C4", "2026-06-18"),
        (JOR, "plasmid", "pcDNA3-FLAG-SNRPB R107K/R111K", "in-house, site-directed mutagenesis from JORp0001", "Freezer -20C B, box 3, C5", "2026-06-25"),
    ]
    for (ini, who), stype, title, source, storage, created in samples:
        r = eln.create_sample(root, ini, stype, title, source=source, storage=storage, index=False)
        backdate(r.path, created)
        set_field(r.path, "date_created", created)
    fill(root / "Samples" / "JORp0002.md", "Description",
         "SNRPB with both arginines of the C-terminal RG-rich region that PRMT5 is reported to methylate "
         "(R107, R111) changed to lysine. Sequence-verified 2026-06-25.")
    fill(root / "Samples" / "JORp0002.md", "Validation", "Expression confirmed by anti-FLAG western in JORe0001.")

    # experiments
    def exp(person, title, started, completed=None, status="active", **kw):
        ini, who = person
        r = eln.create_experiment(root, ini, who, title, index=False, **kw)
        backdate(r.path, started)
        set_field(r.path, "date_started", started)
        if completed:
            set_field(r.path, "date_completed", completed)
        if status != "active":
            set_field(r.path, "status", status)
        return r

    e1 = exp(ALX, "Fractionation protocol validation: KCl titration in A549", "2026-06-11", "2026-06-13", "complete",
             project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot",
             protocol="P_CellularFractionation, P_WesternBlot", samples="ALXc0001, ALXa0002, ALXa0003", notebook="NB03-041")
    fill(e1.path, "Objective", "Validate the fractionation protocol on A549 cells and find the KCl concentration in "
         "nucleoplasm buffer at which U1-70K is released from chromatin, so the protocol can be applied to PRMT5i-treated samples.")
    fill(e1.path, "Experimental design", "A549, untreated. Nucleoplasm buffer at 0, 150, 300, 450 mM KCl. Fractions: cytoplasm, "
         "nucleoplasm, chromatin. Blots: U1-70K (target), GAPDH (cytoplasmic control), histone H3 (chromatin control). n = 1.")
    fill(e1.path, "Results", "GAPDH is cytoplasmic only and H3 chromatin only at every KCl concentration, so the fractionation is clean. "
         "U1-70K moves from the chromatin fraction to the nucleoplasm between 150 and 300 mM KCl; at 450 mM the chromatin "
         "fraction is nearly empty.\n\n![](../5-figures/ALXe0001_R_KCl-titration-U170K_20260613.png)")
    fill(e1.path, "Interpretation", "The protocol separates the compartments as intended and 300 mM KCl is a usable working "
         "concentration: enough to see salt-dependent release without stripping everything.")
    fill(e1.path, "Decision", "Protocol validated at 300 mM KCl (recorded in P_CellularFractionation). Apply to PRMT5i-treated A549 in ALXe0002.")
    fill(e1.path, "Follow-up experiments", "- [x] ALXe0002")

    e2 = exp(ALX, "SNRPB chromatin retention after 48 h PRMT5 inhibition in A549", "2026-06-20", "2026-07-08", "complete",
             project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot",
             protocol="P_CellularFractionation, P_WesternBlot", samples="ALXc0001, ALXa0001, ALXa0002, ALXa0003",
             related="ALXe0001", notebook="NB03-047")
    fill(e2.path, "Objective", "Does PRMT5 inhibition increase the chromatin-bound fraction of SNRPB?")
    fill(e2.path, "Experimental design", "A549 treated 48 h with DMSO or PRMT5 inhibitor (EPZ015666, 1 uM). Fractionation at 300 mM KCl "
         "(ALXe0001). Blots: SNRPB, U1-70K, H3, GAPDH. Three independent biological replicates on separate days. "
         "Quantification: chromatin / (chromatin + nucleoplasm) signal per replicate.")
    fill(e2.path, "Results", "SNRPB chromatin fraction rose from 0.31 +/- 0.04 (DMSO) to 0.58 +/- 0.07 (PRMT5i), mean +/- SD, n = 3; "
         "mean paired difference 0.27, 95% CI [0.20, 0.34], paired t(2) = 17.7, p = 0.003. U1-70K shifted in the same "
         "direction but less (0.40 to 0.49). Loading controls behaved.\n\n"
         "![](../5-figures/ALXe0002_R_SNRPB-chromatin-fraction_20260708.png)\n\nQuantification: `4-data_processed/ALXe0002_chromatin-fraction.csv`.")
    fill(e2.path, "Interpretation", "Consistent with the hypothesis: loss of PRMT5 activity keeps more SNRPB on chromatin. "
         "Symmetric dimethyl-arginine loss was not directly confirmed in this experiment (no SDMA blot).")
    fill(e2.path, "Decision", "Repeat in a second cell line (ALXe0003) and test whether the methyl-site mutant phenocopies (JORe0001).")
    fill(e2.path, "Follow-up experiments", "- [x] ALXe0003 second cell line\n- [x] JORe0001 R107K/R111K mutant\n- [ ] SDMA blot on the same lysates")

    e3 = exp(ALX, "SNRPB chromatin retention after PRMT5 inhibition in HeLa", "2026-07-14", "2026-07-25", "complete",
             project="PRMT5-ChromatinRelease", exp_type="Fractionation, WesternBlot",
             protocol="P_CellularFractionation, P_WesternBlot", samples="ALXc0002, ALXa0001, ALXa0003",
             related="ALXe0002", notebook="NB03-052")
    fill(e3.path, "Objective", "Is the PRMT5i effect on SNRPB chromatin retention (ALXe0002) specific to A549?")
    fill(e3.path, "Experimental design", "As ALXe0002 but in HeLa. n = 2.")
    fill(e3.path, "Results", "SNRPB chromatin fraction 0.28 and 0.30 (DMSO) vs 0.41 and 0.46 (PRMT5i). Same direction as A549, "
         "smaller magnitude. The second replicate had a weak H3 signal in the nucleoplasm lane, suggesting slight chromatin carry-over.")
    fill(e3.path, "Interpretation", "Effect reproduces in a second cell line, so it is not an A549 peculiarity. With n = 2 and one "
         "imperfect fractionation this is supporting, not conclusive.")
    fill(e3.path, "Decision", "Treat the A549 result as the primary finding; HeLa as supporting. No further HeLa replicates planned unless a reviewer asks.")

    j1 = exp(JOR, "Chromatin retention of FLAG-SNRPB R107K/R111K versus wild type", "2026-07-20", "2026-07-29", "complete",
             project="PRMT5-ChromatinRelease, SNRPB-ArginineMethylation", exp_type="Fractionation, WesternBlot",
             protocol="P_CellularFractionation, P_WesternBlot", samples="ALXc0001, JORp0001, JORp0002, ALXa0003",
             related="ALXe0002", notebook="NB04-018")
    fill(j1.path, "Objective", "Does removing the PRMT5 target arginines on SNRPB (R107K/R111K) phenocopy PRMT5 inhibition?")
    fill(j1.path, "Experimental design", "A549 transfected with FLAG-SNRPB WT (JORp0001) or R107K/R111K (JORp0002); 24 h; "
         "fractionation at 300 mM KCl; anti-FLAG blot. n = 1.")
    fill(j1.path, "Results", "FLAG signal chromatin fraction: WT 0.33, mutant 0.55. Expression of both constructs comparable in whole-cell input.")
    fill(j1.path, "Interpretation", "The methyl-site mutant is more chromatin-bound, the same direction as PRMT5 inhibition. "
         "Single replicate; the mutant also migrates slightly slower, which needs an explanation before this is trusted.")
    fill(j1.path, "Decision", "Repeat with n = 3 and include a K107R/K111R revertant control before this goes in a figure.")
    fill(j1.path, "Follow-up experiments", "- [ ] n = 3 repeat with revertant control")

    j2 = exp(JOR, "SNRPB localization by immunofluorescence after PRMT5 inhibition", "2026-08-04", "2026-08-12", "complete",
             project="PRMT5-ChromatinRelease", exp_type="IF, Microscopy",
             protocol="P_Immunofluorescence", samples="ALXc0001, ALXa0001", related="ALXe0002", notebook="NB04-023")
    fill(j2.path, "Objective", "Is the increased chromatin fraction of SNRPB after PRMT5i visible as a change in nuclear distribution?")
    fill(j2.path, "Experimental design", "A549, 48 h DMSO vs PRMT5i (1 uM), anti-SNRPB IF, DAPI, confocal, 30 nuclei per condition, "
         "two coverslips per condition on two days. Scored: speckle count per nucleus and fraction of signal outside speckles.")
    fill(j2.path, "Results", "No change in speckle number (median 18 vs 19) or in diffuse nucleoplasmic signal fraction (0.42 vs 0.44). "
         "Speckles looked slightly larger after PRMT5i but this was not quantified.")
    fill(j2.path, "Interpretation", "Conflicts with the simple reading of ALXe0002: a biochemical shift to the chromatin fraction is "
         "not accompanied by a visible redistribution. Either the change is below IF resolution, or the fractionation shift "
         "reflects extraction resistance rather than localization.")
    fill(j2.path, "Decision", "Discuss at lab meeting. Candidate next step: pre-extraction (0.1% Triton before fixation) IF to ask about extraction resistance directly.")
    fill(j2.path, "Follow-up experiments", "- [ ] pre-extraction IF")

    e4 = exp(ALX, "RNA-seq after 48 h PRMT5 inhibition in A549", "2026-08-25", None, "active",
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

    j3 = exp(JOR, "Arginine methylation sites on SNRPB by mass spectrometry", "2026-08-15", None, "paused",
             project="SNRPB-ArginineMethylation", exp_type="MassSpec, IP", protocol="P_WesternBlot",
             samples="ALXc0001, JORp0001", notebook="NB04-030")
    fill(j3.path, "Objective", "Identify methylated arginines on FLAG-SNRPB immunoprecipitated from A549, with and without PRMT5i.")
    fill(j3.path, "Experimental design", "FLAG IP from 4x 15 cm dishes per condition; on-bead trypsin and Arg-C digests; LC-MS/MS at the proteomics core.")
    fill(j3.path, "Decision", "Paused 2026-09-01: proteomics core queue is 6 weeks; IP eluates are at -80C (JOR box 7). Resume when a slot is confirmed.")

    # files: raw placeholders, processed tables, results figures
    def add_files(exp_id, raw_names, processed=None, figure=None, bands=None):
        f = folder_of(exp_id)
        for r in raw_names:
            (f / "2-data_raw" / r).write_bytes(b"placeholder instrument file (sandbox)\n")
        if processed:
            (f / "4-data_processed" / processed[0]).write_text(processed[1], encoding="utf-8")
        if figure:
            png(f / "5-figures" / figure, bands or [])

    add_files("ALXe0001", ["ChemiDoc_20260612_0931.scn", "ChemiDoc_20260612_0958.scn"],
              figure="ALXe0001_R_KCl-titration-U170K_20260613.png",
              bands=lanes([80, 70, 25, 8], 60, 85) + lanes([5, 20, 70, 90], 120, 145))
    add_files("ALXe0002", ["ChemiDoc_20260706_1402.scn", "ChemiDoc_20260707_1015.scn", "ChemiDoc_20260708_0947.scn"],
              processed=("ALXe0002_chromatin-fraction.csv",
                         "replicate,condition,chromatin,nucleoplasm,fraction\n1,DMSO,0.29,0.71,0.29\n1,PRMT5i,0.55,0.45,0.55\n"
                         "2,DMSO,0.36,0.64,0.36\n2,PRMT5i,0.66,0.34,0.66\n3,DMSO,0.28,0.72,0.28\n3,PRMT5i,0.53,0.47,0.53\n"),
              figure="ALXe0002_R_SNRPB-chromatin-fraction_20260708.png",
              bands=lanes([35, 90, 40, 95], 60, 85) + lanes([90, 90, 90, 90], 120, 145))
    add_files("ALXe0003", ["ChemiDoc_20260724_1130.scn"],
              figure="ALXe0003_R_SNRPB-chromatin-fraction-HeLa_20260725.png",
              bands=lanes([30, 60, 32, 70], 60, 85) + lanes([90, 90, 90, 95], 120, 145))
    add_files("JORe0001", ["ChemiDoc_20260728_1607.scn"],
              figure="JORe0001_R_FLAG-SNRPB-WT-vs-RK_20260729.png",
              bands=lanes([40, 85, 0, 0], 60, 85) + lanes([90, 90, 0, 0], 120, 145))
    add_files("JORe0002", ["LSM980_20260811_slide01.czi", "LSM980_20260811_slide02.czi", "LSM980_20260812_slide03.czi"],
              processed=("JORe0002_speckle-scores.csv", "nucleus,condition,speckles,diffuse_fraction\n1,DMSO,17,0.41\n2,DMSO,19,0.43\n1,PRMT5i,20,0.44\n2,PRMT5i,18,0.45\n"))
    (folder_of("ALXe0004") / "2-data_raw" / "README.md").write_text(
        "# 2-data_raw\n\nFASTQ files are on institutional storage (see `raw_data_path` in the note); "
        "nothing is kept here.\n", encoding="utf-8")

    # project pages: current state written the way the eln-project-synthesis skill would
    fill(root / "Projects" / "PRMT5-ChromatinRelease.md", "Current state", """\
<!-- Kept short and current. Update this section in place; don't append to it. -->

### Supported conclusions

- 48 h PRMT5 inhibition roughly doubles the chromatin-bound fraction of SNRPB in A549 (ALXe0002, n = 3); the same direction is seen in HeLa (ALXe0003, n = 2).
- The fractionation protocol cleanly separates compartments at 300 mM KCl (ALXe0001).

### Open questions / conflicting observations

- Immunofluorescence shows no redistribution of SNRPB after PRMT5i (JORe0002), which does not fit a simple relocalization model for the biochemical shift in ALXe0002. Extraction resistance is the leading alternative.
- Whether the effect is mediated by SNRPB's own methylation is suggested by the R107K/R111K mutant (JORe0001) but not established.

### Experiments needing replication

- JORe0001 (n = 1; mutant migrates slower, unexplained).
""")
    fill(root / "Projects" / "PRMT5-ChromatinRelease.md", "Experiments",
         "- ALXe0001 - fractionation validation - complete\n- ALXe0002 - PRMT5i, A549 - complete\n- ALXe0003 - PRMT5i, HeLa - complete\n"
         "- JORe0001 - R107K/R111K mutant - complete (n = 1)\n- JORe0002 - IF localization - complete\n- ALXe0004 - RNA-seq - active")
    fill(root / "Projects" / "PRMT5-ChromatinRelease.md", "Reagents in use",
         "ALXc0001, ALXc0002, ALXa0001, ALXa0002, ALXa0003, JORp0001, JORp0002")
    fill(root / "Projects" / "PRMT5-ChromatinRelease.md", "Related protocols",
         "P_CellularFractionation, P_WesternBlot, P_Immunofluorescence")

    # ALXe0002 closed out the way the tool does it: snapshot + manifest, dated to its completion.
    eln.complete_experiment(root, "ALXe0002", when="2026-07-08")

    eln.write_index(eln.load_vault(root), quiet=True)


if __name__ == "__main__":
    wipe()
    build()
    print(f"Rebuilt sandbox at {HERE}")
