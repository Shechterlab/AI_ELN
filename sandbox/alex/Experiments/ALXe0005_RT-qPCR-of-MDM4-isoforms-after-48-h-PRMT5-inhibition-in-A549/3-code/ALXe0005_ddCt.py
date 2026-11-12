"""Relative expression by the delta-delta-Ct method (ALXe0005).

Standard library only. Run it from anywhere:

    python3 3-code/ALXe0005_ddCt.py

It reads the plate export in 2-data_raw/, writes 4-data_processed/ALXe0005_ddCt.csv, and prints the
fold changes quoted in Results. Reference gene: ACTB. Calibrator: the mean dCt of the DMSO samples.
A technical replicate more than 0.5 Ct from the median of its three is left out (P_RTqPCR).
The fold change of a condition is 2^-(mean ddCt of its samples).
"""
import csv
import statistics
from pathlib import Path

folder = Path(__file__).resolve().parent.parent
with open(folder / "2-data_raw" / "QuantStudio_20260903_plate1.csv", newline="", encoding="utf-8") as f:
    wells = list(csv.DictReader(f))

dropped = 0
ct = {}  # (sample, target) -> mean Ct of the technical replicates that are kept
for sample in sorted({w["Sample"] for w in wells}):
    for target in sorted({w["Target"] for w in wells}):
        values = [float(w["Ct"]) for w in wells if w["Sample"] == sample and w["Target"] == target]
        middle = statistics.median(values)
        kept = [v for v in values if abs(v - middle) <= 0.5]
        dropped += len(values) - len(kept)
        ct[(sample, target)] = statistics.mean(kept)

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
    w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)

for target in ("MDM4-FL", "MDM4-S"):
    mine = [r for r in rows if r["target"] == target and r["condition"] == "PRMT5i"]
    fold = 2 ** -statistics.mean(float(r["ddct"]) for r in mine)
    print(f"{target}: PRMT5i / DMSO = {fold:.2f} (per sample: {', '.join(r['fold_change'] for r in mine)})")
print(f"technical replicates left out by the 0.5 Ct rule: {dropped} of {len(wells)}")
