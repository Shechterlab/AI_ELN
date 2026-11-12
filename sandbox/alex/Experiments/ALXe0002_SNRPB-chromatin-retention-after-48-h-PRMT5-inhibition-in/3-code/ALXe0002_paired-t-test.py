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
