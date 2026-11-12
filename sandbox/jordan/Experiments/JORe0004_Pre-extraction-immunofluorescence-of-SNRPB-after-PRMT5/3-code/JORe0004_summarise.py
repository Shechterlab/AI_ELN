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
