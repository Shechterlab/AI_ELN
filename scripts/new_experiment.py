#!/usr/bin/env python3
"""
new_experiment.py — the one command that creates an experiment.

Assigns the next experiment ID for a researcher, creates the standard
1-notes / 2-data_raw / 3-code / 4-data_processed / 5-figures folder set,
writes a Markdown+YAML experiment note from templates/experiment.md, and
appends a row to Inventory/experiments.csv.

No dependencies beyond the Python 3 standard library.

Where the data actually lives is configurable — see --root below. The
templates this script renders always come from this repo, so a lab can
point --root at whatever shared storage it has already chosen (a synced
OneDrive/Dropbox folder, an Obsidian vault, a server mount) without this
script needing to know or care which one.

Example:
    python3 scripts/new_experiment.py \\
        --initials JSR \\
        --researcher "Jacob Roth" \\
        --project PRMT5-ChromatinRelease \\
        --type WesternBlot \\
        --title "SNRPB chromatin retention after PRMT5 inhibition" \\
        --protocol P_WesternBlot_v2026-07-16
"""
import argparse
import csv
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "templates" / "experiment.md"
CSV_FIELDS = [
    "experiment_id", "title", "researcher", "project", "experiment_type",
    "protocol", "samples", "notebook_reference", "date", "status", "folder",
]
SUBFOLDERS = ["1-notes", "2-data_raw", "3-code", "4-data_processed", "5-figures"]


def resolve_data_root(root_arg: Optional[str]) -> Path:
    """Where Experiments/ and Inventory/ live.

    Priority: --root flag > AI_ELN_ROOT env var > this repo (default, so
    nothing changes for a lab that's just using the repo itself as its vault).
    """
    chosen = root_arg or os.environ.get("AI_ELN_ROOT")
    return Path(chosen).expanduser().resolve() if chosen else REPO_ROOT


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-")
    return slug[:max_len].strip("-")


def next_experiment_number(inventory_csv: Path, initials: str) -> int:
    pattern = re.compile(rf"^{re.escape(initials)}e(\d+)$")
    highest = 0
    if inventory_csv.exists():
        with open(inventory_csv, newline="") as f:
            for row in csv.DictReader(f):
                m = pattern.match(row.get("experiment_id", ""))
                if m:
                    highest = max(highest, int(m.group(1)))
    return highest + 1


def render_template(text: str, values: dict) -> str:
    for key, val in values.items():
        text = text.replace("{{" + key + "}}", val)
    return text


def append_to_inventory(inventory_csv: Path, row: dict) -> None:
    is_new = not inventory_csv.exists()
    inventory_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(inventory_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if is_new:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Create a new experiment record.")
    parser.add_argument("--initials", required=True, help="Researcher initials, e.g. JSR")
    parser.add_argument("--title", required=True, help="Short experiment title")
    parser.add_argument("--researcher", default=None, help="Full name (defaults to initials)")
    parser.add_argument("--project", default="", help="Project ID this experiment belongs to")
    parser.add_argument("--type", dest="exp_type", default="", help="Experiment type, e.g. WesternBlot")
    parser.add_argument("--protocol", default="", help="Protocol ID used, e.g. P_WesternBlot_v2026-07-16")
    parser.add_argument("--samples", default="", help="Comma-separated sample IDs")
    parser.add_argument("--related", default="", help="Comma-separated related experiment IDs")
    parser.add_argument("--notebook", default="", help="Physical notebook reference, e.g. NB06-051")
    parser.add_argument(
        "--root", default=None,
        help="Where Experiments/ and Inventory/ live (defaults to $AI_ELN_ROOT, "
             "then to this repo). Point this at your lab's shared storage — "
             "a synced OneDrive/Dropbox folder, an Obsidian vault, a server mount.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print what would happen, create nothing")
    args = parser.parse_args()

    initials = args.initials.strip().upper()
    if not initials.isalpha():
        parser.error("--initials must be letters only, e.g. JSR")

    data_root = resolve_data_root(args.root)
    experiments_dir = data_root / "Experiments"
    inventory_csv = data_root / "Inventory" / "experiments.csv"

    researcher = args.researcher or initials
    number = next_experiment_number(inventory_csv, initials)
    experiment_id = f"{initials}e{number:04d}"
    slug = slugify(args.title)
    folder_name = f"{experiment_id}_{slug}" if slug else experiment_id
    folder_path = experiments_dir / folder_name
    today = date.today().isoformat()

    if args.dry_run:
        print(f"Root:    {data_root}")
        print(f"Would create: {experiment_id}")
        print(f"  Folder:  Experiments/{folder_name}/")
        print(f"  Note:    Experiments/{folder_name}/1-notes/{experiment_id}.md")
        print(f"  Inventory row appended to Inventory/experiments.csv")
        return

    if folder_path.exists():
        sys.exit(f"Error: {folder_path} already exists. Aborting.")

    for sub in SUBFOLDERS:
        (folder_path / sub).mkdir(parents=True, exist_ok=True)

    template_text = TEMPLATE_PATH.read_text()
    note_text = render_template(template_text, {
        "EXPERIMENT_ID": experiment_id,
        "TITLE": args.title,
        "RESEARCHER": researcher,
        "PROJECT": args.project,
        "DATE": today,
        "EXPERIMENT_TYPE": args.exp_type,
        "PROTOCOL": args.protocol,
        "SAMPLES": args.samples,
        "NOTEBOOK_REF": args.notebook,
        "RAW_DATA_PATH": f"Experiments/{folder_name}",
        "RELATED": args.related,
    })
    note_path = folder_path / "1-notes" / f"{experiment_id}.md"
    note_path.write_text(note_text)

    append_to_inventory(inventory_csv, {
        "experiment_id": experiment_id,
        "title": args.title,
        "researcher": researcher,
        "project": args.project,
        "experiment_type": args.exp_type,
        "protocol": args.protocol,
        "samples": args.samples,
        "notebook_reference": args.notebook,
        "date": today,
        "status": "active",
        "folder": f"Experiments/{folder_name}",
    })

    print(f"Created {experiment_id}")
    print(f"  {note_path.relative_to(data_root)}")
    print(f"Open that file and fill in the Objective — everything else can wait.")


if __name__ == "__main__":
    main()
