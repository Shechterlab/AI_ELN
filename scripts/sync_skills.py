#!/usr/bin/env python3
"""
sync_skills.py - vendor pinned upstream Agent Skills into .agents/skills/vendor/.

    python3 scripts/sync_skills.py            # (re)copy every source at its pinned version
    python3 scripts/sync_skills.py --check    # exit 1 if any upstream has a newer release
    python3 scripts/sync_skills.py --update   # move every pin to the newest release, then sync
    python3 scripts/sync_skills.py --source k-dense-scientific --update

This is a maintainer tool. Lab members never need to run it: the vendored
skills are committed, so a checkout of this repo already has them.

Why pin instead of tracking upstream HEAD: a skill is a set of instructions
an AI agent will follow against the lab's own data. Updates land here as a
reviewable diff (bump the pin in skills.lock.json, run this, read `git diff`),
never silently.

Lock file (skills.lock.json at the repo root):

    {"sources": [{
        "name":     "k-dense-scientific",                # -> .agents/skills/vendor/<name>/
        "repo":     "https://github.com/K-Dense-AI/scientific-agent-skills.git",
        "ref":      "v2.66.0",       # a release tag (preferred) or a branch name
        "resolved": "<commit sha>",  # written by this script: what is on disk
        "path":     "skills",        # directory in the upstream repo that holds skill folders
        "skills":   ["experimental-design", "statistical-analysis"],
        "synced":   "2026-09-05"     # written by this script
    }]}

If `ref` is a branch, the pin is the `resolved` commit; --update moves it to
the branch's current head. If `ref` is a tag, --update moves it to the newest
tag that looks like a version number.

Requires git. Pure standard library otherwise. Never touches anything outside
.agents/skills/vendor/<name>/ and skills.lock.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOCK = REPO_ROOT / "skills.lock.json"
DEFAULT_VENDOR = REPO_ROOT / ".agents" / "skills" / "vendor"
RE_VERSION_TAG = re.compile(r"^v?(\d+(?:\.\d+)*)$")


class SyncError(Exception):
    pass


def git(*args: str, cwd: Optional[Path] = None) -> str:
    try:
        p = subprocess.run(["git", *args], cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    except FileNotFoundError:
        raise SyncError("git is not installed or not on PATH")
    if p.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed:\n{p.stderr.strip()}")
    return p.stdout


def version_key(tag: str) -> Tuple[int, ...]:
    m = RE_VERSION_TAG.match(tag)
    return tuple(int(x) for x in m.group(1).split(".")) if m else ()


def is_version_tag(ref: str) -> bool:
    return bool(RE_VERSION_TAG.match(ref))


def load_lock(path: Path) -> Dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SyncError(f"no lock file at {path}")
    except ValueError as e:
        raise SyncError(f"{path} is not valid JSON: {e}")
    for src in data.get("sources", []):
        for key in ("name", "repo", "ref", "skills"):
            if key not in src:
                raise SyncError(f"source {src.get('name', '?')!r} in {path} is missing {key!r}")
        src.setdefault("path", "skills")
        src.setdefault("resolved", "")
    return data


def save_lock(path: Path, data: Dict) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------

def remote_latest(src: Dict) -> Tuple[str, str]:
    """Return (kind, latest) where kind is 'tag' or 'branch'."""
    if is_version_tag(src["ref"]):
        out = git("ls-remote", "--tags", src["repo"])
        tags = []
        for line in out.splitlines():
            _, _, ref = line.partition("\t")
            if ref.endswith("^{}"):
                continue
            tag = ref.replace("refs/tags/", "")
            if is_version_tag(tag):
                tags.append(tag)
        if not tags:
            raise SyncError(f"{src['repo']} has no version-looking tags")
        return "tag", max(tags, key=version_key)
    out = git("ls-remote", src["repo"], f"refs/heads/{src['ref']}")
    if not out.strip():
        raise SyncError(f"{src['repo']} has no branch {src['ref']!r}")
    return "branch", out.split()[0]


def check_source(src: Dict) -> Tuple[bool, str, str]:
    """(update_available, pinned_description, latest_description)"""
    kind, latest = remote_latest(src)
    if kind == "tag":
        pinned = src["ref"]
        newer = version_key(latest) > version_key(pinned)
        return newer, pinned, latest
    pinned_sha = src.get("resolved") or ""
    pinned = f"{src['ref']}@{pinned_sha[:7] or '(unsynced)'}"
    return (pinned_sha != latest), pinned, f"{src['ref']}@{latest[:7]}"


def skill_license(skill_md: Path) -> str:
    """The `license:` line from a SKILL.md header, or '?'."""
    try:
        text = skill_md.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "?"
    if not text.startswith("---"):
        return "?"
    header = text.split("\n---", 2)[0]
    m = re.search(r"^license:\s*(.+?)\s*$", header, flags=re.MULTILINE)
    return m.group(1).strip("\"'") if m else "?"


def fetch_ref_for(src: Dict) -> str:
    if is_version_tag(src["ref"]):
        return f"refs/tags/{src['ref']}"
    return src["resolved"] or f"refs/heads/{src['ref']}"


def sync_source(src: Dict, vendor_dir: Path, quiet: bool = False) -> str:
    """Sparse-fetch the pinned ref, copy the named skill folders into vendor_dir/<name>/, return the sha."""
    name, repo, path, skills = src["name"], src["repo"], src["path"].strip("/"), src["skills"]
    if not skills:
        raise SyncError(f"source {name!r} lists no skills")
    tmp = Path(tempfile.mkdtemp(prefix="sync-skills-"))
    try:
        git("init", "-q", cwd=tmp)
        git("remote", "add", "origin", repo, cwd=tmp)
        git("sparse-checkout", "set", *[f"{path}/{s}" for s in skills], cwd=tmp)
        target = fetch_ref_for(src)
        # --filter keeps the download to the sparse paths on servers that support it (GitHub does);
        # others print a warning and send everything, which is still correct.
        git("fetch", "-q", "--depth", "1", "--filter=blob:none", "origin", target, cwd=tmp)
        git("checkout", "-q", "FETCH_HEAD", cwd=tmp)
        sha = git("rev-parse", "HEAD", cwd=tmp).strip()

        missing = [s for s in skills if not (tmp / path / s / "SKILL.md").is_file()]
        if missing:
            have = sorted(p.name for p in (tmp / path).iterdir() if p.is_dir()) if (tmp / path).is_dir() else []
            raise SyncError(f"{name}: skill(s) not found upstream at {target}: {', '.join(missing)}. "
                            f"Fetched: {', '.join(have) or '(nothing)'}")

        dest = vendor_dir / name
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for s in skills:
            shutil.copytree(tmp / path / s, dest / s, ignore=shutil.ignore_patterns(".git", "__pycache__", ".DS_Store"))
        for lic in sorted(tmp.glob("LICENSE*")):
            if lic.is_file():
                shutil.copyfile(lic, dest / "LICENSE.upstream")
                break

        rows = "\n".join(f"| `{s}` | {skill_license(dest / s / 'SKILL.md')} | `{path}/{s}` |" for s in skills)
        (dest / "NOTICE.md").write_text(
            f"# Vendored skills: {name}\n\n"
            f"- Upstream: {repo}\n"
            f"- Pinned ref: `{src['ref']}` (commit `{sha}`)\n"
            f"- Synced: {date.today().isoformat()} by `scripts/sync_skills.py`\n\n"
            f"**Do not edit files in this directory.** They are replaced wholesale on the next sync. "
            f"To change what is vendored or which version, edit `skills.lock.json` at the repo root "
            f"and re-run the sync; to change behaviour, override in `AGENTS.md` or a skill under "
            f"`.agents/skills/lab/`.\n\n"
            f"Each skill carries its own license (from its `SKILL.md` header); the upstream repository "
            f"license is in `LICENSE.upstream`.\n\n"
            f"| skill | license | upstream path |\n|---|---|---|\n{rows}\n",
            encoding="utf-8",
        )
        if not quiet:
            print(f"{name}: {len(skills)} skill(s) at {src['ref']} ({sha[:7]}) -> {dest}")
        return sha
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="sync_skills.py", description=__doc__.split("\n\n")[1],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="report whether newer upstream versions exist (exit 1 if so)")
    p.add_argument("--update", action="store_true", help="move pins to the newest upstream version, then sync")
    p.add_argument("--source", action="append", metavar="NAME", help="only this source (repeatable)")
    p.add_argument("--lock", default=str(DEFAULT_LOCK), help=argparse.SUPPRESS)
    p.add_argument("--vendor-dir", default=str(DEFAULT_VENDOR), help=argparse.SUPPRESS)
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args(argv)

    lock_path, vendor_dir = Path(args.lock), Path(args.vendor_dir)
    try:
        lock = load_lock(lock_path)
        sources = lock.get("sources", [])
        if args.source:
            unknown = set(args.source) - {s["name"] for s in sources}
            if unknown:
                raise SyncError(f"unknown source(s): {', '.join(sorted(unknown))}")
            sources = [s for s in sources if s["name"] in args.source]
        if not sources:
            raise SyncError("no sources selected")

        if args.check:
            any_newer = False
            for src in sources:
                newer, pinned, latest = check_source(src)
                any_newer |= newer
                print(f"{src['name']:<24} pinned {pinned:<22} latest {latest:<22} "
                      f"{'UPDATE AVAILABLE' if newer else 'up to date'}")
            if any_newer:
                print("\nTo update: python3 scripts/sync_skills.py --update, then review `git diff` before committing.")
            return 1 if any_newer else 0

        for src in sources:
            if args.update:
                kind, latest = remote_latest(src)
                if kind == "tag":
                    if version_key(latest) > version_key(src["ref"]):
                        if not args.quiet:
                            print(f"{src['name']}: {src['ref']} -> {latest}")
                        src["ref"] = latest
                else:
                    src["resolved"] = latest
            src["resolved"] = sync_source(src, vendor_dir, quiet=args.quiet)
            src["synced"] = date.today().isoformat()
        save_lock(lock_path, lock)
        if not args.quiet:
            print(f"Updated {lock_path.name}. Review `git diff` before committing.")
        return 0
    except SyncError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
