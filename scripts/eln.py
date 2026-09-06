#!/usr/bin/env python3
"""
eln.py - the one tool for the lab research record.

    python3 scripts/eln.py init                      # once per person: initials, name, where files live
    python3 scripts/eln.py new experiment --title "..."
    python3 scripts/eln.py new sample --type plasmid --title "..."
    python3 scripts/eln.py new protocol --name WesternBlot
    python3 scripts/eln.py new project --id PRMT5-ChromatinRelease
    python3 scripts/eln.py validate                  # check every note against docs/CONVENTIONS.md
    python3 scripts/eln.py index                     # regenerate Inventory/*.csv from the notes
    python3 scripts/eln.py find --project X --status active
    python3 scripts/eln.py report                    # Markdown brief for lab meeting
    python3 scripts/eln.py export --project X        # one file to paste into ChatGPT

Everything this tool does is specified in docs/CONVENTIONS.md. If they
disagree, CONVENTIONS.md is right and this file has a bug.

Pure standard-library Python 3.9+. No dependencies, nothing to install.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

__version__ = "1.0.0"

# --------------------------------------------------------------------------
# The contract (mirrors docs/CONVENTIONS.md)
# --------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"

SUBFOLDERS = ["1-notes", "2-data_raw", "3-code", "4-data_processed", "5-figures"]
# Folders where "files start with the experiment ID" is enforced. 2-data_raw is exempt.
NAMED_SUBFOLDERS = ["1-notes", "3-code", "4-data_processed", "5-figures"]
EXEMPT_FILENAMES = {"readme.md", "thumbs.db", "desktop.ini", "__pycache__"}

KINDS = ("experiment", "protocol", "sample", "project")
KIND_DIR = {"experiment": "Experiments", "protocol": "Protocols", "sample": "Samples", "project": "Projects"}
ID_FIELD = {"experiment": "experiment_id", "protocol": "protocol_id", "sample": "sample_id", "project": "project_id"}

SAMPLE_LETTERS = {
    "p": "plasmid", "i": "oligo", "a": "antibody", "c": "cell-line", "m": "mouse-line",
    "t": "peptide", "r": "protein-prep", "s": "slide", "g": "gel",
}
SAMPLE_TYPES = {v: k for k, v in SAMPLE_LETTERS.items()}

STATUS = {
    "experiment": ("active", "complete", "paused", "abandoned"),
    "protocol": ("current", "archived"),
    "sample": ("active", "depleted", "retired"),
    "project": ("active", "complete", "paused"),
}

INITIALS = r"[A-Z]{2,4}"
RE_INITIALS = re.compile(rf"^{INITIALS}$")
RE_EXP_ID = re.compile(rf"^({INITIALS})e(\d{{4}})$")
RE_SAMPLE_ID = re.compile(rf"^({INITIALS})([{''.join(SAMPLE_LETTERS)}])(\d{{4}})$")
RE_PROTOCOL_ID = re.compile(r"^P_[A-Za-z0-9][A-Za-z0-9-]*$")
RE_PROTOCOL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*$")
RE_PROJECT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9-]*$")
RE_EXP_FOLDER = re.compile(rf"^({INITIALS}e\d{{4}})(?:_([A-Za-z0-9-]+))?$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RE_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
RE_PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")
RE_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

ID_PATTERN = {
    "experiment": RE_EXP_ID, "protocol": RE_PROTOCOL_ID,
    "sample": RE_SAMPLE_ID, "project": RE_PROJECT_ID,
}

REQUIRED = {
    "experiment": ["experiment_id", "title", "researcher", "date_started", "status"],
    "protocol": ["protocol_id", "title", "version", "status"],
    "sample": ["sample_id", "sample_type", "title", "date_created", "status"],
    "project": ["project_id", "title", "lead", "status", "date_started"],
}
# "Should" fields: warn when empty.
SHOULD = {
    "experiment": ["project", "protocols", "raw_data_path"],
    "protocol": [],
    "sample": ["source", "storage_location"],
    "project": [],
}
DATE_FIELDS = {
    "experiment": ["date_started", "date_completed"],
    "protocol": ["version"],
    "sample": ["date_created"],
    "project": ["date_started"],
}
# field -> kind of thing it references
REF_FIELDS = {
    "experiment": {"project": "project", "protocols": "protocol", "samples": "sample",
                   "related_experiments": "experiment"},
    "protocol": {"supersedes": "protocol"},
    "sample": {},
    "project": {},
}
REQUIRED_SECTIONS = {
    "experiment": ["Objective", "Experimental design", "Methods", "Deviations from protocol",
                   "Results", "Interpretation", "Decision", "Follow-up experiments", "Files"],
    "protocol": ["Purpose", "Materials", "Procedure", "Known failure modes / troubleshooting", "Change log"],
    "sample": ["Description", "Provenance", "Validation", "Notes"],
    "project": ["Aim / hypothesis", "Current state", "Experiments", "Reagents in use", "Figures",
                "Related protocols"],
}
MEETING_TAG = "meeting"


class ElnError(Exception):
    """A user-facing error. main() prints it and exits 1."""


def err(msg: str) -> None:
    print(msg, file=sys.stderr)


# --------------------------------------------------------------------------
# Front matter: the flat YAML subset
# --------------------------------------------------------------------------

def split_front_matter(text: str) -> Tuple[Optional[List[str]], str, Optional[str]]:
    """Return (header_lines, body, error). header_lines is None on error."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text, "no YAML header (file must start with a '---' line)"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:]), None
    return None, text, "unterminated YAML header (missing closing '---')"


def _strip_comment(s: str) -> str:
    """Drop a trailing ' # comment' that is outside quotes."""
    quote = None
    for i, ch in enumerate(s):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or s[i - 1] in " \t"):
            return s[:i].rstrip()
    return s


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        inner = s[1:-1]
        if s[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return s


def _split_list(inner: str) -> List[str]:
    """Split 'a, b, "c, d"' on commas that are outside quotes."""
    items, buf, quote = [], [], None
    for ch in inner:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch == ",":
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    items.append("".join(buf))
    return [_unquote(x) for x in items if x.strip()]


def parse_value(raw: str):
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        return _split_list(raw[1:-1])
    return _unquote(raw)


def parse_header_lines(lines: List[str]) -> Tuple[Dict[str, object], List[str]]:
    fields: Dict[str, object] = {}
    problems: List[str] = []
    for line in lines:
        raw = line.rstrip()
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw[0] in " \t":
            problems.append(f"indented line in header (nesting is not allowed): {raw.strip()!r}")
            continue
        if raw.startswith("- "):
            problems.append(f"block list in header (use [a, b] instead): {raw!r}")
            continue
        if ":" not in raw:
            problems.append(f"header line is not 'key: value': {raw!r}")
            continue
        key, _, rest = raw.partition(":")
        key = key.strip()
        if not RE_KEY.match(key):
            problems.append(f"bad header key {key!r} (use snake_case)")
            continue
        if key in fields:
            problems.append(f"duplicate header key {key!r}")
        fields[key] = parse_value(_strip_comment(rest))
    return fields, problems


def parse_front_matter(text: str) -> Tuple[Dict[str, object], str, List[str]]:
    header, body, error = split_front_matter(text)
    if header is None:
        return {}, body, [error or "bad header"]
    fields, problems = parse_header_lines(header)
    return fields, body, problems


def quote_if_needed(value: str) -> str:
    value = "" if value is None else str(value)
    if value == "":
        return ""
    needs = (
        ": " in value or " #" in value or "," in value or value[0] in "[]{}#&*!|>'\"%@`"
        or value != value.strip() or value.endswith(":")
    )
    if needs:
        return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return value


def format_value(value) -> str:
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(quote_if_needed(str(v)) for v in value if str(v).strip()) + "]"
    return quote_if_needed(str(value))


def csv_items(text: Optional[str]) -> List[str]:
    """'a, b,c' -> ['a', 'b', 'c']"""
    if not text:
        return []
    return [x.strip() for x in str(text).split(",") if x.strip()]


# --------------------------------------------------------------------------
# Templates
# --------------------------------------------------------------------------

def template_path(kind: str) -> Path:
    return TEMPLATES_DIR / f"{kind}.md"


def template_keys(kind: str) -> List[str]:
    """The header keys a note of this kind is allowed to have (= the template's keys)."""
    text = template_path(kind).read_text(encoding="utf-8")
    fields, _, _ = parse_front_matter(text)
    return list(fields.keys())


def _split_value_comment(rest: str) -> Tuple[str, str]:
    """'active   # a | b' -> ('active', '   # a | b')"""
    stripped = _strip_comment(rest)
    return stripped.strip(), rest[len(stripped):] if rest.startswith(stripped) else ""


def render_header_line(line: str, values: Dict[str, str]) -> str:
    m = re.match(r"^([a-z][a-z0-9_]*):(.*)$", line)
    if not m:
        return line
    key, rest = m.group(1), m.group(2)
    value, comment = _split_value_comment(rest)
    if not RE_PLACEHOLDER.search(value):
        return line

    def sub(s: str) -> str:
        return RE_PLACEHOLDER.sub(lambda mm: values.get(mm.group(1), ""), s)

    if value.startswith("[") and value.endswith("]"):
        rendered = format_value(csv_items(sub(value[1:-1])))
    else:
        rendered = quote_if_needed(sub(value))
    out = f"{key}: {rendered}".rstrip()
    if comment.strip():
        out = f"{out}{comment}" if rendered else f"{out} {comment.strip()}"
    return out


def render_template(kind: str, values: Dict[str, str]) -> str:
    text = template_path(kind).read_text(encoding="utf-8")
    header, body, error = split_front_matter(text)
    if header is None:
        raise ElnError(f"template {template_path(kind)} is broken: {error}")
    rendered_header = [render_header_line(line, values) for line in header]
    rendered_body = RE_PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), body)
    return "---\n" + "\n".join(rendered_header) + "\n---\n" + rendered_body.rstrip("\n") + "\n"


# --------------------------------------------------------------------------
# Config and root resolution
# --------------------------------------------------------------------------

def config_path() -> Path:
    override = os.environ.get("AI_ELN_CONFIG")
    return Path(override).expanduser() if override else Path.home() / ".ai_eln.json"


def load_config() -> Dict[str, str]:
    p = config_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ElnError(f"could not read config {p}: {e}")
    return data if isinstance(data, dict) else {}


def save_config(data: Dict[str, str]) -> Path:
    p = config_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return p


def resolve_root(flag: Optional[str], config: Optional[Dict[str, str]] = None) -> Path:
    """--root > $AI_ELN_ROOT > config['root'] > this repo."""
    config = load_config() if config is None else config
    chosen = flag or os.environ.get("AI_ELN_ROOT") or config.get("root")
    return Path(chosen).expanduser().resolve() if chosen else REPO_ROOT


def resolve_person(args, config: Dict[str, str], interactive: bool = False) -> Tuple[str, str]:
    """Who is creating this? --flags > env > ~/.ai_eln.json. In interactive mode,
    a missing config triggers first-run setup inline instead of an error."""
    initials = (getattr(args, "initials", None) or os.environ.get("AI_ELN_INITIALS")
                or config.get("initials") or "").strip().upper()
    researcher = (getattr(args, "researcher", None) or os.environ.get("AI_ELN_RESEARCHER")
                  or config.get("researcher") or "").strip()
    if not initials and interactive:
        print("First time here. Two quick questions (asked only once):")
        while not RE_INITIALS.match(initials):
            initials = _prompt("  Your initials (2-4 letters, e.g. JSR)").upper()
        researcher = _prompt("  Your full name", researcher or initials)
        config.update({"initials": initials, "researcher": researcher})
        save_config(config)
        print(f"  Saved to {config_path()}\n")
    if not initials:
        raise ElnError("No initials. Run 'eln.py init' once, or pass --initials JSR.")
    if not RE_INITIALS.match(initials):
        raise ElnError(f"--initials must be 2-4 letters, e.g. JSR (got {initials!r})")
    return initials, (researcher or initials)


def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        v = input(f"{label}{suffix}: ").strip()
    except EOFError:
        v = ""
    return v or default


def _prompt_yes(label: str, default: bool = False) -> bool:
    v = _prompt(f"{label} ({'Y/n' if default else 'y/N'})", "").lower()
    if not v:
        return default
    return v[0] == "y"


def _existing_ids(root: Path, kind: str) -> List[str]:
    d = root / KIND_DIR[kind]
    if not d.is_dir():
        return []
    if kind == "experiment":
        return sorted(m.group(1) for p in d.iterdir() if p.is_dir() for m in [RE_EXP_FOLDER.match(p.name)] if m)
    return sorted(p.stem for p in d.iterdir() if _is_note_file(p))


def _hint(ids: List[str], limit: int = 8) -> str:
    if not ids:
        return ""
    shown = ", ".join(ids[:limit]) + (", ..." if len(ids) > limit else "")
    return f" (existing: {shown})"


def open_path(path: Path) -> bool:
    """Open a file or folder in whatever the OS uses by default. Never raises."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:  # noqa: BLE001 - opening an editor is a convenience, never a failure
        return False


# --------------------------------------------------------------------------
# Reading the vault
# --------------------------------------------------------------------------

class Note:
    __slots__ = ("kind", "path", "folder", "fields", "body", "problems")

    def __init__(self, kind: str, path: Path, folder: Optional[Path] = None):
        self.kind = kind
        self.path = path
        self.folder = folder  # experiment folder, for experiments
        self.fields: Dict[str, object] = {}
        self.body = ""
        self.problems: List[str] = []

    @property
    def id(self) -> str:
        v = self.fields.get(ID_FIELD[self.kind], "")
        return v if isinstance(v, str) else ""

    def get(self, key: str, default: str = "") -> str:
        v = self.fields.get(key, default)
        if isinstance(v, list):
            return ", ".join(v)
        return v if isinstance(v, str) else default

    def get_list(self, key: str) -> List[str]:
        v = self.fields.get(key, [])
        if isinstance(v, list):
            return [str(x) for x in v]
        return [v] if v else []


def read_note(kind: str, path: Path, folder: Optional[Path] = None) -> Note:
    note = Note(kind, path, folder)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        note.problems.append("file is not UTF-8 text")
        return note
    except OSError as e:
        note.problems.append(f"cannot read: {e}")
        return note
    note.fields, note.body, problems = parse_front_matter(text)
    note.problems.extend(problems)
    return note


class Vault:
    def __init__(self, root: Path):
        self.root = root
        self.notes: Dict[str, List[Note]] = {k: [] for k in KINDS}
        self.by_id: Dict[str, Note] = {}
        self.folder_issues: List[Tuple[Path, str]] = []

    def all_notes(self) -> Iterable[Note]:
        for kind in KINDS:
            for n in self.notes[kind]:
                yield n

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return str(path)


def _is_note_file(p: Path) -> bool:
    return p.is_file() and p.suffix == ".md" and not p.name.startswith((".", "_")) \
        and p.name.lower() != "readme.md"


def load_vault(root: Path) -> Vault:
    vault = Vault(root)
    exp_dir = root / KIND_DIR["experiment"]
    if exp_dir.is_dir():
        for folder in sorted(p for p in exp_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
            m = RE_EXP_FOLDER.match(folder.name)
            folder_id = m.group(1) if m else None
            if not m:
                vault.folder_issues.append((folder, "folder name does not match {ID}_{slug}"))
            notes_dir = folder / "1-notes"
            note_path = notes_dir / f"{folder_id}.md" if folder_id else None
            if note_path is None or not note_path.exists():
                # Fall back to any note in 1-notes so its problems are still reported.
                candidates = sorted(p for p in notes_dir.glob("*.md") if _is_note_file(p)) if notes_dir.is_dir() else []
                if note_path is not None and not candidates:
                    vault.folder_issues.append((folder, f"no note at 1-notes/{folder_id}.md"))
                    continue
                if not candidates:
                    continue
                note_path = candidates[0]
                if folder_id:
                    vault.folder_issues.append((folder, f"note should be named 1-notes/{folder_id}.md, found {note_path.name}"))
            note = read_note("experiment", note_path, folder)
            vault.notes["experiment"].append(note)
    for kind in ("protocol", "sample", "project"):
        d = root / KIND_DIR[kind]
        if d.is_dir():
            for p in sorted(x for x in d.iterdir() if _is_note_file(x)):
                vault.notes[kind].append(read_note(kind, p))
    for note in vault.all_notes():
        if note.id and note.id not in vault.by_id:
            vault.by_id[note.id] = note
    return vault


# --------------------------------------------------------------------------
# Sections of a note body
# --------------------------------------------------------------------------

def sections(body: str) -> Dict[str, str]:
    """{'Objective': 'text...', ...} for every '## ' header in the body."""
    out: Dict[str, str] = {}
    current = None
    buf: List[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


def section_is_empty(text: str) -> bool:
    text = RE_HTML_COMMENT.sub("", text or "")
    text = re.sub(r"^#+\s.*$", "", text, flags=re.MULTILINE)  # drop sub-headers
    text = re.sub(r"[-*]\s*(\[ \])?\s*$", "", text, flags=re.MULTILINE)  # empty bullets / checkboxes
    return not text.strip()


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------

class Issue:
    __slots__ = ("level", "path", "message")

    def __init__(self, level: str, path: str, message: str):
        self.level, self.path, self.message = level, path, message


def _valid_date(s: str) -> bool:
    if not RE_DATE.match(s):
        return False
    try:
        date.fromisoformat(s)
        return True
    except ValueError:
        return False


def validate_vault(vault: Vault) -> List[Issue]:
    issues: List[Issue] = []
    E = lambda path, msg: issues.append(Issue("ERROR", path, msg))  # noqa: E731
    W = lambda path, msg: issues.append(Issue("WARN", path, msg))  # noqa: E731

    for folder, msg in vault.folder_issues:
        E(vault.rel(folder), msg)

    known_keys = {kind: set(template_keys(kind)) | {"type"} for kind in KINDS}
    seen_ids: Dict[str, str] = {}

    for note in vault.all_notes():
        rel = vault.rel(note.path)
        kind = note.kind
        for p in note.problems:
            E(rel, p)
        if not note.fields:
            continue

        typ = note.get("type")
        if typ != kind:
            E(rel, f"type is {typ!r}, expected {kind!r}")

        for key in REQUIRED[kind]:
            if not note.get(key).strip():
                E(rel, f"required field '{key}' is missing or empty")
        for key in SHOULD[kind]:
            if key in note.fields and not note.get(key).strip():
                W(rel, f"'{key}' is empty")
        for key in note.fields:
            if key not in known_keys[kind]:
                W(rel, f"unknown header key '{key}' (not in templates/{kind}.md - typo?)")

        nid = note.id
        if nid:
            if not ID_PATTERN[kind].match(nid):
                E(rel, f"{ID_FIELD[kind]} {nid!r} does not match the {kind} ID pattern")
            if nid in seen_ids:
                E(rel, f"duplicate ID {nid} (also in {seen_ids[nid]})")
            else:
                seen_ids[nid] = rel

        status = note.get("status")
        if status and status not in STATUS[kind]:
            E(rel, f"status {status!r} is not one of {' | '.join(STATUS[kind])}")
        for key in DATE_FIELDS[kind]:
            v = note.get(key)
            if v and not _valid_date(v):
                E(rel, f"'{key}' must be YYYY-MM-DD (got {v!r})")

        for key, target_kind in REF_FIELDS[kind].items():
            for ref in note.get_list(key):
                target = vault.by_id.get(ref)
                if target is None:
                    W(rel, f"'{key}' refers to {ref}, which does not exist in {KIND_DIR[target_kind]}/")
                elif target.kind != target_kind:
                    W(rel, f"'{key}' refers to {ref}, which is a {target.kind}, not a {target_kind}")

        secs = sections(note.body)
        for name in REQUIRED_SECTIONS[kind]:
            if name not in secs:
                W(rel, f"body is missing the '## {name}' section")

        if kind == "experiment":
            _validate_experiment(vault, note, secs, E, W)
        elif kind == "sample":
            m = RE_SAMPLE_ID.match(nid) if nid else None
            stype = note.get("sample_type")
            if stype and stype not in SAMPLE_TYPES:
                E(rel, f"sample_type {stype!r} is not one of {', '.join(SAMPLE_TYPES)}")
            elif m and stype and SAMPLE_LETTERS[m.group(2)] != stype:
                E(rel, f"ID letter '{m.group(2)}' means {SAMPLE_LETTERS[m.group(2)]}, but sample_type is {stype!r}")
            if nid and note.path.stem != nid:
                E(rel, f"filename should be {nid}.md")
        elif kind in ("protocol", "project"):
            if nid and note.path.stem != nid:
                E(rel, f"filename should be {nid}.md")

    return issues


def _validate_experiment(vault: Vault, note: Note, secs: Dict[str, str], E, W) -> None:
    rel = vault.rel(note.path)
    folder = note.folder
    nid = note.id
    if folder is not None:
        m = RE_EXP_FOLDER.match(folder.name)
        folder_id = m.group(1) if m else None
        if folder_id and nid and folder_id != nid:
            E(rel, f"experiment_id {nid} does not match folder {folder.name}")
        missing = [s for s in SUBFOLDERS if not (folder / s).is_dir()]
        if missing:
            E(vault.rel(folder), f"missing subfolder(s): {', '.join(missing)}")
        check_id = folder_id or nid
        if check_id:
            for sub in NAMED_SUBFOLDERS:
                d = folder / sub
                if not d.is_dir():
                    continue
                for f in sorted(d.iterdir()):
                    name = f.name
                    if not f.is_file() or name.startswith(".") or name.lower() in EXEMPT_FILENAMES:
                        continue
                    if not (name.startswith(check_id + "_") or name.startswith(check_id + ".")):
                        W(vault.rel(f), f"filename should start with {check_id}_ (see CONVENTIONS.md section 3)")
    if note.get("status") == "complete":
        if not note.get("date_completed"):
            W(rel, "status is complete but date_completed is empty")
        for name in ("Results", "Interpretation"):
            if name in secs and section_is_empty(secs[name]):
                W(rel, f"status is complete but the '## {name}' section is empty")


def print_issues(vault: Vault, issues: List[Issue], strict: bool) -> int:
    by_path: Dict[str, List[Issue]] = {}
    for i in issues:
        by_path.setdefault(i.path, []).append(i)
    for path in sorted(by_path):
        print(path)
        for i in by_path[path]:
            print(f"  {i.level:<5}  {i.message}")
    n_err = sum(1 for i in issues if i.level == "ERROR")
    n_warn = sum(1 for i in issues if i.level == "WARN")
    counts = ", ".join(f"{len(vault.notes[k])} {k}{'s' if len(vault.notes[k]) != 1 else ''}" for k in KINDS)
    print(f"Checked {counts}: {n_err} error{'s' if n_err != 1 else ''}, "
          f"{n_warn} warning{'s' if n_warn != 1 else ''}"
          + (" (strict: warnings count as errors)" if strict and n_warn else ""))
    return 1 if n_err or (strict and n_warn) else 0


# --------------------------------------------------------------------------
# index
# --------------------------------------------------------------------------

INDEX_COLUMNS = {
    "experiments": ["experiment_id", "title", "researcher", "project", "experiment_type", "protocols",
                    "samples", "notebook_reference", "date_started", "date_completed", "status", "tags", "folder"],
    "samples": ["sample_id", "sample_type", "title", "source", "storage_location", "date_created", "status",
                "used_in_experiments"],
    "protocols": ["protocol_id", "title", "version", "status", "used_in_experiments"],
    "projects": ["project_id", "title", "lead", "status", "date_started", "experiments"],
}


def _join(items: List[str]) -> str:
    return ";".join(items)


def build_index(vault: Vault) -> Dict[str, List[Dict[str, str]]]:
    exps = sorted((n for n in vault.notes["experiment"] if n.id), key=lambda n: n.id)
    used_by: Dict[str, List[str]] = {}
    for e in exps:
        for key in ("protocols", "samples", "project"):
            for ref in e.get_list(key):
                used_by.setdefault(ref, []).append(e.id)

    rows: Dict[str, List[Dict[str, str]]] = {k: [] for k in INDEX_COLUMNS}
    for e in exps:
        rows["experiments"].append({
            "experiment_id": e.id, "title": e.get("title"), "researcher": e.get("researcher"),
            "project": _join(e.get_list("project")), "experiment_type": _join(e.get_list("experiment_type")),
            "protocols": _join(e.get_list("protocols")), "samples": _join(e.get_list("samples")),
            "notebook_reference": e.get("notebook_reference"), "date_started": e.get("date_started"),
            "date_completed": e.get("date_completed"), "status": e.get("status"),
            "tags": _join(e.get_list("tags")),
            "folder": vault.rel(e.folder) if e.folder else vault.rel(e.path.parent),
        })
    for s in sorted((n for n in vault.notes["sample"] if n.id), key=lambda n: n.id):
        rows["samples"].append({
            "sample_id": s.id, "sample_type": s.get("sample_type"), "title": s.get("title"),
            "source": s.get("source"), "storage_location": s.get("storage_location"),
            "date_created": s.get("date_created"), "status": s.get("status"),
            "used_in_experiments": _join(used_by.get(s.id, [])),
        })
    for p in sorted((n for n in vault.notes["protocol"] if n.id), key=lambda n: n.id):
        rows["protocols"].append({
            "protocol_id": p.id, "title": p.get("title"), "version": p.get("version"),
            "status": p.get("status"), "used_in_experiments": _join(used_by.get(p.id, [])),
        })
    for p in sorted((n for n in vault.notes["project"] if n.id), key=lambda n: n.id):
        rows["projects"].append({
            "project_id": p.id, "title": p.get("title"), "lead": p.get("lead"), "status": p.get("status"),
            "date_started": p.get("date_started"), "experiments": _join(used_by.get(p.id, [])),
        })
    return rows


def write_index(vault: Vault, quiet: bool = False) -> None:
    inv = vault.root / "Inventory"
    inv.mkdir(parents=True, exist_ok=True)
    rows = build_index(vault)
    for name, cols in INDEX_COLUMNS.items():
        path = inv / f"{name}.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            for r in rows[name]:
                w.writerow(r)
        if not quiet:
            print(f"Wrote {vault.rel(path)} ({len(rows[name])} row{'s' if len(rows[name]) != 1 else ''})")


# --------------------------------------------------------------------------
# new
# --------------------------------------------------------------------------

def slugify(text: str, max_len: int = 60) -> str:
    """'SNRPB chromatin retention: KCl' -> 'SNRPB-chromatin-retention-KCl'. Case kept; cut on a word boundary."""
    slug = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    if len(slug) > max_len:
        cut = slug[:max_len + 1]
        slug = cut[:cut.rfind("-")] if "-" in cut else slug[:max_len]
    return slug.strip("-")


def next_number(existing: Iterable[str], pattern: re.Pattern, initials: str, letter: str = "e") -> int:
    highest = 0
    for candidate in existing:
        m = pattern.match(candidate)
        if m and m.group(1) == initials and (letter == "e" or m.group(2) == letter):
            highest = max(highest, int(m.group(m.lastindex)))
    return highest + 1


def next_experiment_id(root: Path, initials: str) -> str:
    seen: List[str] = []
    exp_dir = root / "Experiments"
    if exp_dir.is_dir():
        for folder in exp_dir.iterdir():
            if folder.is_dir():
                m = RE_EXP_FOLDER.match(folder.name)
                if m:
                    seen.append(m.group(1))
                for note_path in (folder / "1-notes").glob("*.md") if (folder / "1-notes").is_dir() else []:
                    fields, _, _ = parse_front_matter(note_path.read_text(encoding="utf-8", errors="replace"))
                    v = fields.get("experiment_id")
                    if isinstance(v, str):
                        seen.append(v)
    return f"{initials}e{next_number(seen, RE_EXP_ID, initials):04d}"


def next_sample_id(root: Path, initials: str, letter: str) -> str:
    seen: List[str] = []
    d = root / "Samples"
    if d.is_dir():
        for p in d.glob("*.md"):
            seen.append(p.stem)
            fields, _, _ = parse_front_matter(p.read_text(encoding="utf-8", errors="replace"))
            v = fields.get("sample_id")
            if isinstance(v, str):
                seen.append(v)
    return f"{initials}{letter}{next_number(seen, RE_SAMPLE_ID, initials, letter):04d}"


def ensure_vault_dirs(root: Path) -> None:
    for d in list(KIND_DIR.values()) + ["Inventory"]:
        (root / d).mkdir(parents=True, exist_ok=True)


SUBFOLDER_READMES = {
    "1-notes": "Your experiment note `{ID}.md` lives here, next to the protocol snapshot(s) `{ID}_P_...md`\n"
               "the tool copied in. Extra notes are welcome; name them `{ID}_something.md`.\n",
    "2-data_raw": "Instrument output goes here **with its original filename**. Never edit, rename, or\n"
                  "reorganize anything in this folder. If the data is too large to live here, leave it on\n"
                  "institutional storage and put that location in `raw_data_path` in the note.\n",
    "3-code": "Analysis scripts and notebooks, named `{ID}_what-it-does.R` / `.py` / `.ipynb`.\n",
    "4-data_processed": "Anything derived from the raw data by a script or by hand (quantification tables,\n"
                        "cropped images, normalized values), named `{ID}_what-it-is.csv` and the like.\n",
    "5-figures": "Exported panels. The results summary you show in lab meeting is\n"
                 "`{ID}_R_what-it-shows_YYYYMMDD.png` (the `R` is what makes it findable in one search).\n",
}


def write_subfolder_readmes(folder: Path, exp_id: str) -> None:
    """A one-paragraph README in each subfolder: tells people what goes there, and keeps the
    folder alive in git, which does not track empty directories."""
    for sub, text in SUBFOLDER_READMES.items():
        p = folder / sub / "README.md"
        if not p.exists():
            p.write_text(f"# {sub}\n\n{text.replace('{ID}', exp_id)}", encoding="utf-8")


def _wizard_experiment(args, root: Path) -> None:
    """Fill in args by asking plain questions. Enter skips anything optional."""
    print("New experiment. Only the title is required; press Enter to skip the rest.\n")
    while not (args.title or "").strip():
        args.title = _prompt("  Title (what are you doing?)")
    args.project = args.project or _prompt("  Project ID" + _hint(_existing_ids(root, "project")))
    args.exp_type = args.exp_type or _prompt("  Experiment type (e.g. WesternBlot, IF, qPCR)")
    args.protocol = args.protocol or _prompt("  Protocol ID" + _hint(_existing_ids(root, "protocol")))
    args.samples = args.samples or _prompt("  Sample IDs, comma-separated" + _hint(_existing_ids(root, "sample")))
    args.notebook = args.notebook or _prompt("  Physical notebook page (e.g. NB02-153)")
    if not args.tags and _prompt_yes("  Flag this for the next lab meeting?"):
        args.tags = MEETING_TAG
    print()


class Created:
    """What a create_* call produced: the ID, the note path, extra files, and any warnings."""
    __slots__ = ("id", "path", "extra", "warnings")

    def __init__(self, id_: str, path: Path):
        self.id, self.path = id_, path
        self.extra: List[Path] = []
        self.warnings: List[str] = []


def create_experiment(root: Path, initials: str, researcher: str, title: str, project: str = "",
                      exp_type: str = "", protocol: str = "", samples: str = "", related: str = "",
                      notebook: str = "", tags: str = "", raw_data_path: str = "", index: bool = True) -> Created:
    """The one way an experiment comes into existence. Used by the CLI, the wizard, and the web page."""
    title = (title or "").strip()
    if not title:
        raise ElnError("an experiment needs a title")
    if not RE_INITIALS.match(initials or ""):
        raise ElnError(f"initials must be 2-4 letters, e.g. JSR (got {initials!r})")
    today = date.today().isoformat()
    exp_id = next_experiment_id(root, initials)
    slug = slugify(title)
    folder_name = f"{exp_id}_{slug}" if slug else exp_id
    folder = root / "Experiments" / folder_name
    if folder.exists():
        raise ElnError(f"{folder} already exists. Aborting.")
    ensure_vault_dirs(root)
    for sub in SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    write_subfolder_readmes(folder, exp_id)

    note_path = folder / "1-notes" / f"{exp_id}.md"
    note_path.write_text(render_template("experiment", {
        "EXPERIMENT_ID": exp_id, "TITLE": title, "RESEARCHER": researcher or initials,
        "PROJECT": project or "", "DATE": today, "EXPERIMENT_TYPE": exp_type or "",
        "PROTOCOL": protocol or "", "SAMPLES": samples or "", "NOTEBOOK_REF": notebook or "",
        "RAW_DATA_PATH": raw_data_path or f"Experiments/{folder_name}/2-data_raw",
        "RELATED": related or "", "TAGS": tags or "",
    }), encoding="utf-8")
    result = Created(exp_id, note_path)

    for pid in csv_items(protocol):
        src = root / "Protocols" / f"{pid}.md"
        if not src.exists():
            result.warnings.append(f"{pid} not found in Protocols/, no snapshot copied "
                                   f"(create it with: eln.py new protocol --name {pid[2:] if pid.startswith('P_') else pid})")
            continue
        fields, _, _ = parse_front_matter(src.read_text(encoding="utf-8"))
        version = str(fields.get("version") or today).replace("-", "")
        name = pid[2:] if pid.startswith("P_") else pid
        dst = folder / "1-notes" / f"{exp_id}_P_{name}_{version}.md"
        shutil.copyfile(src, dst)
        result.extra.append(dst)

    if index:
        write_index(load_vault(root), quiet=True)
    return result


def create_sample(root: Path, initials: str, sample_type: str, title: str, source: str = "",
                  storage: str = "", tags: str = "", index: bool = True) -> Created:
    if not RE_INITIALS.match(initials or ""):
        raise ElnError(f"initials must be 2-4 letters, e.g. JSR (got {initials!r})")
    stype = (sample_type or "").strip().lower()
    if stype in SAMPLE_LETTERS:
        letter, stype = stype, SAMPLE_LETTERS[stype]
    elif stype in SAMPLE_TYPES:
        letter = SAMPLE_TYPES[stype]
    else:
        raise ElnError(f"type must be one of {', '.join(SAMPLE_TYPES)} (or a letter {', '.join(SAMPLE_LETTERS)})")
    if not (title or "").strip():
        raise ElnError("a sample needs a title")
    sample_id = next_sample_id(root, initials, letter)
    path = root / "Samples" / f"{sample_id}.md"
    ensure_vault_dirs(root)
    path.write_text(render_template("sample", {
        "SAMPLE_ID": sample_id, "SAMPLE_TYPE": stype, "TITLE": title.strip(), "DATE": date.today().isoformat(),
        "SOURCE": source or "", "STORAGE": storage or "", "TAGS": tags or "",
    }), encoding="utf-8")
    if index:
        write_index(load_vault(root), quiet=True)
    return Created(sample_id, path)


def create_protocol(root: Path, name: str, title: str = "", tags: str = "", index: bool = True) -> Created:
    name = (name or "").strip()
    if name.startswith("P_"):
        name = name[2:]
    if not RE_PROTOCOL_NAME.match(name):
        raise ElnError("a protocol name is letters, digits, and hyphens, e.g. WesternBlot or Cellular-Fractionation")
    pid = f"P_{name}"
    path = root / "Protocols" / f"{pid}.md"
    if path.exists():
        raise ElnError(f"{path} already exists. Edit it in place and bump its version instead.")
    title = (title or "").strip() or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name).replace("-", " ")
    ensure_vault_dirs(root)
    path.write_text(render_template("protocol", {
        "NAME": name, "TITLE": title, "DATE": date.today().isoformat(), "TAGS": tags or "",
    }), encoding="utf-8")
    if index:
        write_index(load_vault(root), quiet=True)
    return Created(pid, path)


def create_project(root: Path, project_id: str, title: str = "", lead: str = "", tags: str = "",
                   index: bool = True) -> Created:
    pid = (project_id or "").strip()
    if not RE_PROJECT_ID.match(pid):
        raise ElnError("a project ID starts with a letter and contains only letters, digits, and hyphens")
    path = root / "Projects" / f"{pid}.md"
    if path.exists():
        raise ElnError(f"{path} already exists.")
    ensure_vault_dirs(root)
    path.write_text(render_template("project", {
        "PROJECT_ID": pid, "TITLE": (title or "").strip() or pid, "LEAD": lead or "",
        "DATE": date.today().isoformat(), "TAGS": tags or "",
    }), encoding="utf-8")
    if index:
        write_index(load_vault(root), quiet=True)
    return Created(pid, path)


def _report_created(root: Path, result: Created, label: Optional[str] = None) -> None:
    print(f"Created {result.id}")
    print(f"  {result.path.relative_to(root).as_posix()}")
    for p in result.extra:
        print(f"  {p.relative_to(root).as_posix()}  (snapshot)")
    for w in result.warnings:
        err(f"  warning: {w}")


def cmd_new_experiment(args) -> int:
    config = load_config()
    root = resolve_root(args.root, config)
    interactive = bool(args.interactive)
    if not (args.title or "").strip() and not interactive:
        raise ElnError("give a title with --title \"...\", or run with --interactive to be asked")
    initials, researcher = resolve_person(args, config, interactive=interactive)
    if interactive:
        _wizard_experiment(args, root)
    if args.dry_run:
        exp_id = next_experiment_id(root, initials)
        folder_name = f"{exp_id}_{slugify(args.title)}"
        print(f"Root:   {root}")
        print(f"Would create {exp_id}:")
        print(f"  Experiments/{folder_name}/{{{','.join(SUBFOLDERS)}}}")
        print(f"  Experiments/{folder_name}/1-notes/{exp_id}.md")
        for pid in csv_items(args.protocol):
            print(f"  snapshot of {pid} into 1-notes/ (if Protocols/{pid}.md exists)")
        print("  then re-index Inventory/*.csv")
        return 0
    result = create_experiment(root, initials, researcher, args.title, project=args.project or "",
                               exp_type=args.exp_type or "", protocol=args.protocol or "",
                               samples=args.samples or "", related=args.related or "",
                               notebook=args.notebook or "", tags=args.tags or "",
                               raw_data_path=args.raw_data_path or "", index=not args.no_index)
    _report_created(root, result)
    if args.open and open_path(result.path):
        print("Opening the note. Fill in the Objective; everything else can wait.")
    else:
        print("Open the note and fill in the Objective. Everything else can wait.")
    return 0


def _wizard_sample(args, root: Path) -> None:
    print("New sample record (a plasmid, oligo, antibody, cell line, ...).\n")
    types = list(SAMPLE_TYPES)
    while not (args.sample_type or "").strip():
        print("  Type: " + "  ".join(f"{i + 1}={t}" for i, t in enumerate(types)))
        v = _prompt("  Number or name")
        if v.isdigit() and 1 <= int(v) <= len(types):
            v = types[int(v) - 1]
        args.sample_type = v
    while not (args.title or "").strip():
        args.title = _prompt("  Title (what is it, unambiguously?)")
    args.source = args.source or _prompt("  Source (vendor / made in-house in which experiment / gift from whom)")
    args.storage = args.storage or _prompt("  Storage location (freezer / box / position)")
    print()


def cmd_new_sample(args) -> int:
    config = load_config()
    root = resolve_root(args.root, config)
    interactive = bool(args.interactive)
    initials, _ = resolve_person(args, config, interactive=interactive)
    if interactive:
        _wizard_sample(args, root)
    if not (args.sample_type or "").strip() or not (args.title or "").strip():
        raise ElnError("give --type and --title, or run with --interactive to be asked")
    if args.dry_run:
        stype = args.sample_type.strip().lower()
        letter = stype if stype in SAMPLE_LETTERS else SAMPLE_TYPES.get(stype)
        if not letter:
            raise ElnError(f"--type must be one of {', '.join(SAMPLE_TYPES)}")
        sample_id = next_sample_id(root, initials, letter)
        print(f"Root:   {root}\nWould create {sample_id} ({SAMPLE_LETTERS[letter]}) at Samples/{sample_id}.md")
        return 0
    result = create_sample(root, initials, args.sample_type, args.title, source=args.source or "",
                           storage=args.storage or "", tags=args.tags or "", index=not args.no_index)
    _report_created(root, result)
    if args.open:
        open_path(result.path)
    return 0


def cmd_new_protocol(args) -> int:
    root = resolve_root(args.root)
    if args.interactive:
        print("New protocol. One living file per protocol; bump its version when the procedure changes.\n")
        while not (args.name or "").strip():
            args.name = _prompt("  Short name, letters/digits/hyphens (e.g. WesternBlot)" + _hint(_existing_ids(root, "protocol")))
        args.title = args.title or _prompt("  Full title", "")
        print()
    if not (args.name or "").strip():
        raise ElnError("give --name, or run with --interactive to be asked")
    if args.dry_run:
        name = args.name.strip()
        name = name[2:] if name.startswith("P_") else name
        if not RE_PROTOCOL_NAME.match(name):
            raise ElnError("--name must be letters, digits, and hyphens, e.g. WesternBlot or Cellular-Fractionation")
        print(f"Root:   {root}\nWould create P_{name} at Protocols/P_{name}.md")
        return 0
    result = create_protocol(root, args.name, title=args.title or "", tags=args.tags or "", index=not args.no_index)
    _report_created(root, result)
    if args.open:
        open_path(result.path)
    return 0


def cmd_new_project(args) -> int:
    config = load_config()
    root = resolve_root(args.root, config)
    if args.interactive:
        print("New project page (the rolled-up current state of one research thread).\n")
        while not (args.project_id or "").strip():
            args.project_id = _prompt("  Short ID, letters/digits/hyphens (e.g. PRMT5-ChromatinRelease)"
                                      + _hint(_existing_ids(root, "project")))
        args.title = args.title or _prompt("  Full title", "")
        args.lead = args.lead or _prompt("  Lead", config.get("researcher", ""))
        print()
    if not (args.project_id or "").strip():
        raise ElnError("give --id, or run with --interactive to be asked")
    if args.dry_run:
        pid = args.project_id.strip()
        if not RE_PROJECT_ID.match(pid):
            raise ElnError("--id must start with a letter and contain only letters, digits, and hyphens")
        print(f"Root:   {root}\nWould create {pid} at Projects/{pid}.md")
        return 0
    result = create_project(root, args.project_id, title=args.title or "",
                            lead=args.lead or config.get("researcher") or "", tags=args.tags or "",
                            index=not args.no_index)
    _report_created(root, result)
    if args.open:
        open_path(result.path)
    return 0


# --------------------------------------------------------------------------
# find
# --------------------------------------------------------------------------

def _ci_in(needle: str, items: List[str]) -> bool:
    return needle.lower() in [x.lower() for x in items]


def find_notes(vault: Vault, kind: str, project: Optional[str] = None, status: Optional[str] = None,
               researcher: Optional[str] = None, tag: Optional[str] = None, sample: Optional[str] = None,
               protocol: Optional[str] = None, exp_type: Optional[str] = None,
               text: Optional[str] = None) -> List[Note]:
    out = []
    for n in vault.notes[kind]:
        if not n.id:
            continue
        if project and not _ci_in(project, n.get_list("project")):
            continue
        if status and n.get("status").lower() != status.lower():
            continue
        if researcher and researcher.lower() not in (n.get("researcher") + " " + n.get("lead")).lower():
            continue
        if tag and not _ci_in(tag, n.get_list("tags")):
            continue
        if sample and not _ci_in(sample, n.get_list("samples")):
            continue
        if protocol and not _ci_in(protocol, n.get_list("protocols")):
            continue
        if exp_type and not _ci_in(exp_type, n.get_list("experiment_type")):
            continue
        if text and text.lower() not in (n.get("title") + "\n" + n.body).lower():
            continue
        out.append(n)
    return sorted(out, key=lambda n: n.id)


def cmd_find(args) -> int:
    vault = load_vault(resolve_root(args.root))
    hits = find_notes(vault, args.kind, args.project, args.status, args.researcher, args.tag,
                      args.sample, args.protocol, args.exp_type, args.text)
    if args.json:
        print(json.dumps([dict(n.fields, path=vault.rel(n.path)) for n in hits], indent=2))
        return 0
    for n in hits:
        if args.ids:
            print(n.id)
        else:
            who = n.get("researcher") or n.get("lead") or n.get("sample_type") or "-"
            print(f"{n.id}\t{n.get('status')}\t{who}\t{n.get('title')}\t{vault.rel(n.path)}")
    if not hits and not args.ids:
        err("(no matches)")
    return 0


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def _clean(text: str) -> str:
    return RE_HTML_COMMENT.sub("", text or "").strip() or "_(not written yet)_"


def build_report(vault: Vault, days: int = 30, today: Optional[date] = None) -> str:
    today = today or date.today()
    exps = sorted((n for n in vault.notes["experiment"] if n.id), key=lambda n: n.id)
    out = [f"# Lab meeting brief - {today.isoformat()}", ""]

    flagged = [e for e in exps if _ci_in(MEETING_TAG, e.get_list("tags"))]
    out.append(f"## Flagged for discussion (`tags: [{MEETING_TAG}]`)")
    out.append("")
    if not flagged:
        out.append(f"_Nothing flagged. Add `{MEETING_TAG}` to an experiment's `tags` to put it here._")
        out.append("")
    for e in flagged:
        secs = sections(e.body)
        proj = ", ".join(e.get_list("project")) or "-"
        out.append(f"### {e.id} - {e.get('title')}")
        out.append(f"{e.get('researcher')} | project: {proj} | status: {e.get('status')} | "
                   f"started {e.get('date_started')} | `{vault.rel(e.path)}`")
        out.append("")
        for name in ("Objective", "Results", "Interpretation", "Decision"):
            out.append(f"**{name}.** {_clean(secs.get(name, ''))}")
            out.append("")

    out.append("## Active experiments by project")
    out.append("")
    active = [e for e in exps if e.get("status") == "active"]
    by_project: Dict[str, List[Note]] = {}
    for e in active:
        for p in e.get_list("project") or ["(no project)"]:
            by_project.setdefault(p, []).append(e)
    if not active:
        out.append("_No active experiments._")
        out.append("")
    for p in sorted(by_project):
        out.append(f"### {p}")
        out.append("")
        out.append("| ID | Title | Researcher | Started | Notebook |")
        out.append("|---|---|---|---|---|")
        for e in by_project[p]:
            out.append(f"| {e.id} | {e.get('title')} | {e.get('researcher')} | {e.get('date_started')} | "
                       f"{e.get('notebook_reference') or '-'} |")
        out.append("")

    cutoff = today - timedelta(days=days)
    recent = []
    for e in exps:
        if e.get("status") == "complete" and _valid_date(e.get("date_completed")):
            if date.fromisoformat(e.get("date_completed")) >= cutoff:
                recent.append(e)
    out.append(f"## Completed in the last {days} days")
    out.append("")
    if not recent:
        out.append("_None._")
    for e in recent:
        out.append(f"- **{e.id}** {e.get('title')} ({e.get('researcher')}, completed {e.get('date_completed')})")
    out.append("")
    paused = [e for e in exps if e.get("status") in ("paused", "abandoned")]
    if paused:
        out.append("## Paused / abandoned")
        out.append("")
        for e in paused:
            out.append(f"- **{e.id}** {e.get('title')} - {e.get('status')}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_report(args) -> int:
    root = resolve_root(args.root)
    vault = load_vault(root)
    text = build_report(vault, days=args.days)
    out = args.out
    if not out and args.open:
        (root / "Inventory").mkdir(parents=True, exist_ok=True)
        out = str(root / "Inventory" / f"meeting-brief_{date.today().strftime('%Y%m%d')}.md")
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"Wrote {out}")
        if args.open:
            open_path(Path(out))
    else:
        print(text, end="")
    return 0


# --------------------------------------------------------------------------
# export (a bundle to paste into ChatGPT or upload to a chat)
# --------------------------------------------------------------------------

EXPORT_PRIMER = """\
This is an export from a lab research record (AI_ELN, Shechter Lab). Each note
below is a Markdown file with a small YAML header; the file path is given on
the `==== ... ====` line above it.

How to read it:
- IDs: experiments are `{INITIALS}e{NNNN}` (e.g. JSRe0002); samples are
  `{INITIALS}{letter}{NNNN}` (p plasmid, i oligo, a antibody, c cell-line,
  m mouse-line, t peptide, r protein-prep, s slide, g gel); protocols are
  `P_{Name}`; projects are named. A bare ID anywhere is a reference.
- Experiment notes always have these sections: Objective, Experimental
  design, Methods, Deviations from protocol, Results, Interpretation,
  Decision, Follow-up experiments, Files.
- `status` is active | complete | paused | abandoned.

Rules for answering questions about this material:
1. Cite the experiment ID (e.g. "JSRe0002") for every factual claim about a result.
2. If the notes don't contain the answer, say so. Do not fill gaps with plausible guesses.
3. Never invent data, numbers, figures, or experiments that are not in the notes.
4. Treat a single experiment as preliminary unless a note says it was replicated.
"""


def select_for_export(vault: Vault, project: Optional[str], experiment_ids: List[str], status: Optional[str],
                      all_: bool) -> List[Note]:
    exps = [n for n in vault.notes["experiment"] if n.id]
    if all_:
        chosen = exps
    else:
        chosen = []
        if project:
            chosen += find_notes(vault, "experiment", project=project)
        if status:
            chosen += find_notes(vault, "experiment", status=status)
        for eid in experiment_ids:
            n = vault.by_id.get(eid)
            if n is None or n.kind != "experiment":
                raise ElnError(f"experiment {eid} not found")
            chosen.append(n)
    seen, out = set(), []
    for n in sorted(chosen, key=lambda n: n.id):
        if n.id not in seen:
            seen.add(n.id)
            out.append(n)
    return out


def build_export(vault: Vault, experiments: List[Note], related: bool = True,
                 today: Optional[date] = None) -> str:
    today = today or date.today()
    extras: List[Note] = []
    if related:
        seen = {e.id for e in experiments}
        for e in experiments:
            for key, kind in REF_FIELDS["experiment"].items():
                for ref in e.get_list(key):
                    t = vault.by_id.get(ref)
                    if t is not None and t.id not in seen:
                        seen.add(t.id)
                        extras.append(t)
    order = {"project": 0, "protocol": 1, "sample": 2, "experiment": 3}
    extras.sort(key=lambda n: (order[n.kind], n.id))

    out = [f"# AI_ELN export - {today.isoformat()}", "", EXPORT_PRIMER, "## Inventory of exported experiments", "",
           "| ID | Title | Researcher | Project | Status | Started | Completed |", "|---|---|---|---|---|---|---|"]
    for e in experiments:
        out.append(f"| {e.id} | {e.get('title')} | {e.get('researcher')} | {', '.join(e.get_list('project')) or '-'} | "
                   f"{e.get('status')} | {e.get('date_started')} | {e.get('date_completed') or '-'} |")
    out += ["", "## Notes", ""]
    for n in experiments + extras:
        out.append(f"==== {vault.rel(n.path)} ====")
        out.append(n.path.read_text(encoding="utf-8").rstrip())
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def cmd_export(args) -> int:
    root = resolve_root(args.root)
    vault = load_vault(root)
    scope = "export"
    if args.interactive and not (args.project or args.experiment or args.status or args.all):
        print("Export notes into one file you can paste into ChatGPT (or attach to a chat).\n")
        projects = _existing_ids(root, "project")
        v = _prompt("  A project ID, one or more experiment IDs, or Enter for all active experiments"
                    + _hint(projects))
        if not v:
            args.status = "active"
        elif v in projects:
            args.project = v
        else:
            args.experiment = csv_items(v.replace(" ", ","))
        print()
    if not (args.project or args.experiment or args.status or args.all):
        raise ElnError("choose what to export: --project ID, --experiment ID [ID...], --status active, or --all")
    experiments = select_for_export(vault, args.project, args.experiment or [], args.status, args.all)
    if not experiments:
        raise ElnError("nothing matched")
    if args.project:
        scope = args.project
    elif args.experiment:
        scope = "-".join(args.experiment[:3])
    elif args.status:
        scope = args.status
    text = build_export(vault, experiments, related=not args.no_related)
    out = args.out
    if not out and args.open:
        (root / "Inventory").mkdir(parents=True, exist_ok=True)
        out = str(root / "Inventory" / f"export_{scope}_{date.today().strftime('%Y%m%d')}.md")
    if out:
        Path(out).write_text(text, encoding="utf-8")
        print(f"Exported {len(experiments)} experiment(s), {len(text):,} characters -> {out}")
        if args.open:
            open_path(Path(out))
            print("Select all, copy, and paste into a ChatGPT conversation (or attach the file).")
    else:
        print(text, end="")
        err(f"Exported {len(experiments)} experiment(s), {len(text):,} characters")
    return 0


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------

POINTER_AGENTS_MD = """\
# Agent instructions - lab research record (data root)

This folder holds the lab's experiment, protocol, sample, and project notes.
The tooling, templates, and full rules live in the AI_ELN repository at:

    {repo}

Read `{repo}/AGENTS.md` and `{repo}/docs/CONVENTIONS.md` before changing
anything here. Create experiments only with:

    python3 "{repo}/scripts/eln.py" new experiment --root "{root}" --title "..."

Never hand-create an experiment folder; never edit files in `2-data_raw/`;
cite experiment IDs for any factual claim about a result.
"""


def cmd_init(args) -> int:
    config = load_config()
    interactive = sys.stdin.isatty() and not args.yes
    initials = (args.initials or config.get("initials") or "")
    researcher = (args.researcher or config.get("researcher") or "")
    root_in = args.root or config.get("root") or ""
    if interactive:
        print("AI_ELN setup. Press Enter to keep a default.")
        initials = _prompt("Your initials (2-4 letters, e.g. JSR)", initials)
        researcher = _prompt("Your full name", researcher)
        root_in = _prompt("Where should Experiments/ etc. live? (blank = this repo)", root_in)
    initials = initials.strip().upper()
    if not initials or not RE_INITIALS.match(initials):
        raise ElnError("initials are required: 2-4 letters, e.g. --initials JSR")
    researcher = researcher.strip() or initials
    root = Path(root_in).expanduser().resolve() if root_in.strip() else REPO_ROOT

    data = {"initials": initials, "researcher": researcher}
    if root != REPO_ROOT:
        data["root"] = str(root)
    p = save_config(data)
    ensure_vault_dirs(root)
    if root != REPO_ROOT and not (root / "AGENTS.md").exists():
        (root / "AGENTS.md").write_text(POINTER_AGENTS_MD.format(repo=REPO_ROOT, root=root), encoding="utf-8")
    print(f"Saved {p}")
    print(f"  initials:   {initials}")
    print(f"  researcher: {researcher}")
    print(f"  root:       {root}{'' if root != REPO_ROOT else '  (this repo)'}")
    print("Next: python3 scripts/eln.py new experiment --title \"what you're doing today\"")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def cmd_validate(args) -> int:
    vault = load_vault(resolve_root(args.root))
    issues = validate_vault(vault)
    return print_issues(vault, issues, args.strict)


def cmd_index(args) -> int:
    root = resolve_root(args.root)
    write_index(load_vault(root), quiet=args.quiet)
    return 0


def build_parser() -> argparse.ArgumentParser:
    root_help = "where Experiments/ etc. live (default: $AI_ELN_ROOT, then ~/.ai_eln.json, then this repo)"
    # --root is accepted both before and after the subcommand. SUPPRESS on the per-command copy
    # keeps argparse from overwriting a value given before the subcommand with None.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", default=argparse.SUPPRESS, help=root_help)

    p = argparse.ArgumentParser(
        prog="eln.py", description="The one tool for the lab research record. See docs/CONVENTIONS.md.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="examples:\n"
               "  eln.py init\n"
               "  eln.py new experiment --title \"SNRPB chromatin retention after PRMT5i\" --project PRMT5-ChromatinRelease --protocol P_WesternBlot\n"
               "  eln.py new sample --type plasmid --title \"pcDNA3-FLAG-SNRPB\"\n"
               "  eln.py validate --strict\n"
               "  eln.py find --status active --tag meeting\n"
               "  eln.py --root sandbox find --text SNRPB      # --root works before or after the command\n"
               "  eln.py export --project PRMT5-ChromatinRelease --out brief.md\n")
    p.add_argument("--version", action="version", version=f"eln.py {__version__}")
    p.add_argument("--root", default=None, help=root_help)
    sub = p.add_subparsers(dest="command", metavar="command")

    s = sub.add_parser("init", parents=[common], help="one-time setup: your initials, name, and where files live")
    s.add_argument("--initials")
    s.add_argument("--researcher")
    s.add_argument("--yes", action="store_true", help="do not prompt; use flags and existing config only")
    s.set_defaults(func=cmd_init)

    n = sub.add_parser("new", help="create an experiment, sample, protocol, or project")
    nsub = n.add_subparsers(dest="kind", metavar="kind")

    wizard = argparse.ArgumentParser(add_help=False)
    wizard.add_argument("-i", "--interactive", action="store_true",
                        help="ask questions instead of requiring flags (what the double-click launchers use)")
    wizard.add_argument("--open", action="store_true", help="open the new note in your default editor")
    wizard.add_argument("--no-index", action="store_true", help=argparse.SUPPRESS)
    wizard.add_argument("--dry-run", action="store_true")

    e = nsub.add_parser("experiment", parents=[common, wizard], help="new experiment (assigns the next ID for you)")
    e.add_argument("--title")
    e.add_argument("--initials", help="override the initials from init")
    e.add_argument("--researcher", help="override the name from init")
    e.add_argument("--project", help="project ID(s), comma-separated")
    e.add_argument("--type", dest="exp_type", help="experiment type(s), e.g. WesternBlot")
    e.add_argument("--protocol", help="protocol ID(s), e.g. P_WesternBlot; a snapshot is copied into 1-notes/")
    e.add_argument("--samples", help="sample ID(s), comma-separated")
    e.add_argument("--related", help="related experiment ID(s), comma-separated")
    e.add_argument("--notebook", help="physical notebook page, e.g. NB02-153")
    e.add_argument("--tags", help="tags, comma-separated (use 'meeting' to flag for lab meeting)")
    e.add_argument("--raw-data-path", help="where raw data lives if not in 2-data_raw/")
    e.set_defaults(func=cmd_new_experiment)

    sm = nsub.add_parser("sample", parents=[common, wizard], help="new sample record (plasmid, oligo, antibody, ...)")
    sm.add_argument("--type", dest="sample_type",
                    help="one of: " + ", ".join(f"{v} ({k})" for k, v in SAMPLE_LETTERS.items()))
    sm.add_argument("--title")
    sm.add_argument("--initials")
    sm.add_argument("--source")
    sm.add_argument("--storage", help="freezer / box / position")
    sm.add_argument("--tags")
    sm.set_defaults(func=cmd_new_sample)

    pr = nsub.add_parser("protocol", parents=[common, wizard], help="new living protocol file")
    pr.add_argument("--name", help="e.g. WesternBlot -> Protocols/P_WesternBlot.md")
    pr.add_argument("--title")
    pr.add_argument("--tags")
    pr.set_defaults(func=cmd_new_protocol)

    pj = nsub.add_parser("project", parents=[common, wizard], help="new project page")
    pj.add_argument("--id", dest="project_id", help="e.g. PRMT5-ChromatinRelease")
    pj.add_argument("--title")
    pj.add_argument("--lead")
    pj.add_argument("--tags")
    pj.set_defaults(func=cmd_new_project)

    v = sub.add_parser("validate", parents=[common], help="check every note and folder against docs/CONVENTIONS.md")
    v.add_argument("--strict", action="store_true", help="treat warnings as errors")
    v.set_defaults(func=cmd_validate)

    i = sub.add_parser("index", parents=[common], help="regenerate Inventory/*.csv from the notes")
    i.add_argument("--quiet", action="store_true")
    i.set_defaults(func=cmd_index)

    f = sub.add_parser("find", parents=[common], help="list notes matching filters")
    f.add_argument("--kind", choices=KINDS, default="experiment")
    f.add_argument("--project")
    f.add_argument("--status")
    f.add_argument("--researcher", help="substring, case-insensitive")
    f.add_argument("--tag")
    f.add_argument("--sample", help="experiments that used this sample ID")
    f.add_argument("--protocol", help="experiments that used this protocol ID")
    f.add_argument("--type", dest="exp_type", help="experiment type")
    f.add_argument("--text", help="substring in title or body, case-insensitive")
    f.add_argument("--ids", action="store_true", help="print IDs only")
    f.add_argument("--json", action="store_true", help="print full header fields as JSON")
    f.set_defaults(func=cmd_find)

    r = sub.add_parser("report", parents=[common], help="Markdown brief for lab meeting")
    r.add_argument("--out", help="write to a file instead of stdout")
    r.add_argument("--open", action="store_true", help="write to Inventory/meeting-brief_<date>.md and open it")
    r.add_argument("--days", type=int, default=30, help="window for 'recently completed'")
    r.set_defaults(func=cmd_report)

    x = sub.add_parser("export", parents=[common],
                       help="bundle notes into one Markdown file to paste into ChatGPT or attach to a chat")
    x.add_argument("--project", help="every experiment in this project")
    x.add_argument("--experiment", nargs="+", metavar="ID", help="specific experiment ID(s)")
    x.add_argument("--status", help="every experiment with this status")
    x.add_argument("--all", action="store_true", help="every experiment")
    x.add_argument("--no-related", action="store_true", help="do not include referenced protocols/samples/projects")
    x.add_argument("--out", help="write to a file instead of stdout")
    x.add_argument("-i", "--interactive", action="store_true", help="ask what to export")
    x.add_argument("--open", action="store_true", help="write to Inventory/export_<scope>_<date>.md and open it")
    x.set_defaults(func=cmd_export)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        if getattr(args, "command", None) == "new":
            parser.parse_args(["new", "--help"])
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except ElnError as e:
        err(f"error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
