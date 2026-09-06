#!/usr/bin/env python3
"""
eln_web.py - a point-and-click page for the lab research record.

    python3 scripts/eln_web.py            # opens http://127.0.0.1:8765 in your browser
    python3 scripts/eln_web.py --root PATH --port 8765 --no-browser

It is the same tool as eln.py with buttons and forms instead of questions
in a terminal: create experiments, samples, protocols, and projects; browse
and read notes (figures included); run the checker; build the lab-meeting
brief; build the ChatGPT export. It only ever listens on your own machine
(127.0.0.1), needs nothing installed beyond Python 3, and writes the same
plain files eln.py writes. Close the window that started it to stop it.
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import eln  # noqa: E402

md_to_html = eln.md_to_html  # the renderer lives in eln.py so snapshots and .eln archives share it

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".tif", ".tiff"}
MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
        ".svg": "image/svg+xml", ".webp": "image/webp", ".bmp": "image/bmp", ".tif": "image/tiff", ".tiff": "image/tiff"}

CSS = """
:root{--ink:#1f2933;--muted:#5f6b7a;--line:#e3e8ee;--bg:#f7f9fb;--card:#fff;--accent:#1f6feb;--ok:#1a7f37;--warn:#9a6700;--err:#cf222e}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{background:#fff;border-bottom:1px solid var(--line)}header .in{max-width:1040px;margin:0 auto;padding:10px 20px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header .brand{font-weight:700;font-size:17px;margin-right:auto}header nav a{padding:6px 10px;border-radius:6px;color:var(--ink)}header nav a.active,header nav a:hover{background:var(--bg);text-decoration:none}
main{max-width:1040px;margin:0 auto;padding:22px 20px 60px}
h1{font-size:24px;margin:0 0 14px}h2{font-size:18px;margin:26px 0 10px}h3{font-size:16px;margin:18px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:0 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}
.tile{display:block;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;color:var(--ink);text-decoration:none}
.tile:hover{border-color:var(--accent);text-decoration:none}.tile b{display:block;font-size:17px;margin-bottom:4px}.tile span{color:var(--muted);font-size:14px}
.btn{display:inline-block;background:var(--accent);color:#fff;border:0;border-radius:7px;padding:9px 16px;font:inherit;font-weight:600;cursor:pointer}
.btn.secondary{background:#fff;color:var(--ink);border:1px solid var(--line)}.btn:hover{filter:brightness(.95)}
form.stack label{display:block;margin:12px 0 4px;font-weight:600}form.stack input[type=text],form.stack textarea,form.stack select{width:100%;padding:9px 10px;border:1px solid var(--line);border-radius:7px;font:inherit}
form.stack .hint{color:var(--muted);font-size:13px;margin-top:3px}form.stack .row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.checks{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:4px 16px;margin-top:6px}.checks label{font-weight:400;margin:0;display:flex;gap:8px;align-items:baseline}
table{border-collapse:collapse;width:100%;margin:8px 0 14px}th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}th{font-size:13px;color:var(--muted);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;background:#eef2f6;color:var(--muted)}
.pill.active{background:#dcfce7;color:var(--ok)}.pill.complete{background:#dbeafe;color:#1e40af}.pill.paused,.pill.abandoned{background:#fef3c7;color:var(--warn)}
.msg{padding:12px 14px;border-radius:8px;margin:0 0 16px}.msg.ok{background:#dcfce7;color:var(--ok)}.msg.err{background:#ffe1e3;color:var(--err)}.msg.warn{background:#fef3c7;color:var(--warn)}
.issue{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;margin:2px 0}.issue .lvl{display:inline-block;width:56px;font-weight:700}.lvl.ERROR{color:var(--err)}.lvl.WARN{color:var(--warn)}
.note img{max-width:100%;border:1px solid var(--line);border-radius:6px}.note pre{background:#f1f5f9;padding:10px;border-radius:6px;overflow-x:auto}.note code{background:#f1f5f9;padding:1px 4px;border-radius:4px;font-size:13px}
.note h1{font-size:22px}.note h2{border-bottom:1px solid var(--line);padding-bottom:4px;margin-top:24px}
.meta{display:grid;grid-template-columns:max-content 1fr;gap:3px 14px;font-size:14px}.meta div:nth-child(odd){color:var(--muted)}
.path{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;color:var(--muted);word-break:break-all}
textarea.export{width:100%;height:420px;font:12px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace}
.actions{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:10px 0}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:end}.filters label{font-size:13px;color:var(--muted);display:block}.filters input,.filters select{padding:7px 9px;border:1px solid var(--line);border-radius:7px;font:inherit}
footer{max-width:1040px;margin:0 auto;padding:0 20px 30px;color:var(--muted);font-size:13px}
"""

NAV = [("/", "Home"), ("/experiments", "Experiments"), ("/samples", "Samples"), ("/protocols", "Protocols"),
       ("/projects", "Projects"), ("/validate", "Check"), ("/report", "Meeting brief"), ("/export", "Export")]


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def page(title: str, body: str, active: str = "", root: Optional[Path] = None) -> str:
    nav = "".join(f'<a href="{h}" class="{"active" if h == active else ""}">{esc(t)}</a>' for h, t in NAV)
    return (f"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{esc(title)} - AI_ELN</title><style>{CSS}</style></head><body>"
            f"<header><div class=in><span class=brand>AI_ELN</span><nav>{nav}</nav></div></header>"
            f"<main>{body}</main><footer>Files live in <span class=path>{esc(root)}</span>. "
            f"Everything here is a plain file you can open in any editor. Close the window that started this page to stop it.</footer>"
            f"<script>function cp(id){{var t=document.getElementById(id);t.select();document.execCommand('copy');"
            f"var b=document.getElementById(id+'-btn');if(b){{b.textContent='Copied';setTimeout(function(){{b.textContent='Copy all'}},1500)}}}}</script>"
            f"</body></html>")


# --------------------------------------------------------------------------
# The application
# --------------------------------------------------------------------------

class App:
    def __init__(self, root: Path):
        self.root = root.resolve()

    # -- helpers ----------------------------------------------------------

    def person(self) -> Tuple[str, str]:
        cfg = eln.load_config()
        initials = (os.environ.get("AI_ELN_INITIALS") or cfg.get("initials") or "").upper()
        researcher = os.environ.get("AI_ELN_RESEARCHER") or cfg.get("researcher") or ""
        return initials, researcher

    def inside_root(self, p: Path) -> bool:
        try:
            p.resolve().relative_to(self.root)
            return True
        except ValueError:
            return False

    def rel(self, p: Path) -> str:
        try:
            return p.resolve().relative_to(self.root).as_posix()
        except ValueError:
            return str(p)

    def status_pill(self, s: str) -> str:
        return f'<span class="pill {esc(s)}">{esc(s or "-")}</span>'

    def need_setup(self) -> Optional[str]:
        initials, _ = self.person()
        if initials:
            return None
        return ("<div class='msg warn'>First time here: tell the record who you are, once. "
                "<a href='/setup'>Set up initials and name</a>.</div>")

    # -- pages ------------------------------------------------------------

    def home(self) -> str:
        v = eln.load_vault(self.root)
        exps = sorted((n for n in v.notes["experiment"] if n.id), key=lambda n: n.id, reverse=True)
        active = [e for e in exps if e.get("status") == "active"]
        flagged = [e for e in exps if eln._ci_in(eln.MEETING_TAG, e.get_list("tags"))]
        initials, researcher = self.person()
        who = f"{esc(researcher)} ({esc(initials)})" if initials else "not set up yet"
        tiles = [
            ("/new/experiment", "New experiment", "One form. Creates the folder, the note, the protocol snapshot."),
            ("/new/sample", "New sample", "Plasmid, oligo, antibody, cell line, gel..."),
            ("/new/protocol", "New protocol", "One living file per protocol."),
            ("/new/project", "New project", "The rolled-up state of a research thread."),
            ("/validate", "Check everything", "What breaks the conventions, if anything."),
            ("/report", "Lab meeting brief", "From everything flagged for the meeting."),
            ("/export", "Export for ChatGPT", "One file to paste into a chat."),
        ]
        body = [self.need_setup() or "", "<h1>Shechter Lab research record</h1>",
                f"<p>You are <b>{who}</b> &middot; {len(exps)} experiments, {len(active)} active, "
                f"{len(flagged)} flagged for lab meeting &middot; <a href='/setup'>settings</a></p>",
                "<div class=grid>" + "".join(f"<a class=tile href='{h}'><b>{esc(t)}</b><span>{esc(d)}</span></a>"
                                             for h, t, d in tiles) + "</div>"]
        if flagged:
            body.append("<h2>Flagged for lab meeting</h2>" + self.exp_table(v, flagged))
        body.append("<h2>Recent experiments</h2>" + (self.exp_table(v, exps[:12]) if exps else
                                                     "<p class=path>None yet. Start with <a href='/new/experiment'>New experiment</a>.</p>"))
        return page("Home", "\n".join(body), "/", self.root)

    def exp_table(self, v, exps) -> str:
        rows = "".join(
            f"<tr><td><a href='/note/{esc(e.id)}'>{esc(e.id)}</a></td><td>{esc(e.get('title'))}</td>"
            f"<td>{esc(e.get('researcher'))}</td><td>{esc(', '.join(e.get_list('project')))}</td>"
            f"<td>{esc(e.get('date_started'))}</td><td>{self.status_pill(e.get('status'))}</td></tr>" for e in exps)
        return ("<table><tr><th>ID</th><th>Title</th><th>Who</th><th>Project</th><th>Started</th><th>Status</th></tr>"
                f"{rows}</table>")

    def experiments(self, q: Dict[str, str]) -> str:
        v = eln.load_vault(self.root)
        hits = eln.find_notes(v, "experiment", project=q.get("project") or None, status=q.get("status") or None,
                              researcher=q.get("researcher") or None, text=q.get("q") or None,
                              tag=q.get("tag") or None)
        projects = sorted({p for e in v.notes["experiment"] for p in e.get_list("project")})
        opts = "".join(f"<option value='{esc(p)}' {'selected' if p == q.get('project') else ''}>{esc(p)}</option>" for p in projects)
        sopts = "".join(f"<option value='{s}' {'selected' if s == q.get('status') else ''}>{s}</option>" for s in eln.STATUS["experiment"])
        form = (f"<form class=filters method=get><div><label>Search text</label><input name=q value='{esc(q.get('q'))}'></div>"
                f"<div><label>Project</label><select name=project><option value=''>any</option>{opts}</select></div>"
                f"<div><label>Status</label><select name=status><option value=''>any</option>{sopts}</select></div>"
                f"<div><label>Researcher</label><input name=researcher value='{esc(q.get('researcher'))}'></div>"
                f"<div><label>Tag</label><input name=tag value='{esc(q.get('tag'))}' placeholder='meeting'></div>"
                f"<div><button class=btn>Filter</button></div></form>")
        body = f"<h1>Experiments</h1>{form}<p class=path>{len(hits)} shown</p>" + \
               (self.exp_table(v, hits) if hits else "<p>No matches.</p>")
        return page("Experiments", body, "/experiments", self.root)

    def simple_list(self, kind: str, title: str, cols: List[Tuple[str, str]]) -> str:
        v = eln.load_vault(self.root)
        notes = sorted((n for n in v.notes[kind] if n.id), key=lambda n: n.id)
        head = "".join(f"<th>{esc(c)}</th>" for _, c in cols)
        rows = "".join("<tr>" + "".join(
            f"<td><a href='/note/{esc(n.id)}'>{esc(n.id)}</a></td>" if f == "id" else
            f"<td>{self.status_pill(n.get('status'))}</td>" if f == "status" else f"<td>{esc(n.get(f))}</td>"
            for f, _ in cols) + "</tr>" for n in notes)
        body = (f"<h1>{esc(title)}</h1><div class=actions><a class=btn href='/new/{kind}'>New {esc(kind)}</a></div>"
                f"<table><tr>{head}</tr>{rows}</table>" if notes else
                f"<h1>{esc(title)}</h1><p>None yet.</p><a class=btn href='/new/{kind}'>New {esc(kind)}</a>")
        return page(title, body, f"/{kind}s", self.root)

    def note(self, nid: str, msg: str = "") -> Optional[str]:
        v = eln.load_vault(self.root)
        n = v.by_id.get(nid)
        if n is None:
            return None
        text = n.path.read_text(encoding="utf-8", errors="replace")
        _, body_md, _ = eln.split_front_matter(text)
        img_base = self.rel(n.path.parent)
        meta = "".join(f"<div>{esc(k)}</div><div>{esc(', '.join(val) if isinstance(val, list) else val) or '-'}</div>"
                       for k, val in n.fields.items() if k != "type")
        folder = n.folder if n.folder else n.path.parent
        files_html = ""
        if n.kind == "experiment" and n.folder:
            parts = []
            for sub in eln.SUBFOLDERS:
                d = n.folder / sub
                names = sorted(p.name for p in d.iterdir() if p.is_file() and not p.name.startswith(".")
                               and p.name.lower() != "readme.md") if d.is_dir() else []
                parts.append(f"<b>{esc(sub)}/</b> " + (", ".join(esc(x) for x in names) if names else "<i>empty</i>"))
            files_html = "<h2>Files</h2><div class=card>" + "<br>".join(parts) + "</div>"
        usage = ""
        if n.kind in ("sample", "protocol", "project"):
            key = {"sample": "sample", "protocol": "protocol", "project": "project"}[n.kind]
            used = eln.find_notes(v, "experiment", **{key: n.id})
            usage = "<h2>Used in</h2>" + (self.exp_table(v, used) if used else "<p>No experiment yet.</p>")
        actions = (f"<form class=actions method=post action='/open'>"
                   f"<a class=btn href='/edit/{esc(n.id)}'>Edit here</a>"
                   f"<input type=hidden name=p value='{esc(self.rel(n.path))}'>"
                   f"<button class='btn secondary'>Open in your editor</button>"
                   f"<button class='btn secondary' name=folder value=1>Show folder</button>"
                   f"<span class=path>{esc(self.rel(n.path))}</span></form>")
        if n.kind == "experiment" and n.folder is not None:
            if n.get("status") != "complete":
                actions += (f"<form class=actions method=post action='/complete/{esc(n.id)}'>"
                            f"<button class='btn secondary'>Mark complete</button>"
                            f"<span class=hint>sets status and date, writes an HTML snapshot and a file manifest</span></form>")
            else:
                has_manifest = eln.manifest_path(n.folder, n.id).exists()
                actions += (f"<div class=actions>"
                            f"<form method=post action='/verify/{esc(n.id)}' style='display:inline'>"
                            f"<button class='btn secondary' {'' if has_manifest else 'disabled'}>Verify files</button></form>"
                            f"<form method=post action='/complete/{esc(n.id)}' style='display:inline'>"
                            f"<input type=hidden name=force value=1><button class='btn secondary'>Refresh snapshot &amp; manifest</button></form>"
                            f"<form method=post action='/render/{esc(n.id)}' style='display:inline'>"
                            f"<button class='btn secondary'>Save HTML snapshot</button></form>"
                            f"</div>")
        body = (f"{msg}<h1>{esc(n.id)} <small style='font-weight:400;color:var(--muted)'>{esc(n.get('title'))}</small></h1>"
                f"{actions}<div class=card><div class=meta>{meta}</div></div>"
                f"<div class='card note'>{md_to_html(body_md, img_base)}</div>{files_html}{usage}")
        return page(n.id, body, f"/{n.kind}s", self.root)

    def edit(self, nid: str, err: str = "", text: Optional[str] = None) -> Optional[str]:
        v = eln.load_vault(self.root)
        n = v.by_id.get(nid)
        if n is None:
            return None
        if text is None:
            text = n.path.read_text(encoding="utf-8", errors="replace")
        body = f"""
        <h1>Edit {esc(n.id)}</h1>{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <p class=hint>This is the whole file. Keep the header between the <code>---</code> lines and the <code>##</code> section titles;
        write anything you like under them. Saving re-checks the header and re-indexes.</p>
        <form method=post class=stack>
          <textarea name=text class=export style='height:70vh;font-size:13px' spellcheck=true>{esc(text)}</textarea>
          <div class=actions style='margin-top:12px'><button class=btn>Save</button><a class='btn secondary' href='/note/{esc(n.id)}'>Cancel</a>
          <span class=path>{esc(self.rel(n.path))}</span></div>
        </form>"""
        return page(f"Edit {n.id}", body, f"/{n.kind}s", self.root)

    def save_edit(self, nid: str, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Write the note if its header still parses. Returns (error, redirect)."""
        v = eln.load_vault(self.root)
        n = v.by_id.get(nid)
        if n is None:
            return "no such note", None
        text = text.replace("\r\n", "\n")
        fields, _, problems = eln.parse_front_matter(text)
        if problems:
            return "Header problem: " + "; ".join(problems), None
        if fields.get(eln.ID_FIELD[n.kind]) != nid:
            return f"The header's {eln.ID_FIELD[n.kind]} must stay {nid}.", None
        n.path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")
        eln.write_index(eln.load_vault(self.root), quiet=True)
        return None, f"/note/{nid}?saved=1"

    # -- forms ------------------------------------------------------------

    def form_experiment(self, err: str = "", vals: Optional[Dict[str, str]] = None) -> str:
        vals = vals or {}
        v = eln.load_vault(self.root)
        projects = sorted(n.id for n in v.notes["project"] if n.id)
        protocols = sorted(n.id for n in v.notes["protocol"] if n.id)
        samples = sorted((n for n in v.notes["sample"] if n.id), key=lambda n: n.id)
        types = ["WesternBlot", "Fractionation", "IP", "IF", "qPCR", "RNAseq", "ChIPseq", "MassSpec", "Cloning",
                 "CellCulture", "MouseWork", "Microscopy", "Purification", "Kinetics"]
        dl = lambda name, items: f"<datalist id={name}>" + "".join(f"<option value='{esc(x)}'>" for x in items) + "</datalist>"  # noqa: E731
        chosen = set(eln.csv_items(vals.get("samples")))
        sample_boxes = "".join(
            f"<label><input type=checkbox name=samples value='{esc(s.id)}' {'checked' if s.id in chosen else ''}> "
            f"{esc(s.id)} <span class=path>{esc(s.get('title'))}</span></label>" for s in samples)
        body = f"""
        <h1>New experiment</h1>{self.need_setup() or ''}{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <form class=stack method=post>
          <label>Title <span class=path>(the only thing you must fill in)</span></label>
          <input type=text name=title required autofocus value='{esc(vals.get('title'))}' placeholder='e.g. SNRPB chromatin retention after PRMT5 inhibition: KCl titration'>
          <div class=row><div>
            <label>Project</label><input type=text name=project list=projects value='{esc(vals.get('project'))}'>{dl('projects', projects)}
            <div class=hint>Pick an existing one or type a new ID. {len(projects)} exist.</div>
          </div><div>
            <label>Experiment type</label><input type=text name=exp_type list=types value='{esc(vals.get('exp_type'))}'>{dl('types', types)}
            <div class=hint>Comma-separate several: WesternBlot, Fractionation</div>
          </div></div>
          <div class=row><div>
            <label>Protocol</label><input type=text name=protocol list=protocols value='{esc(vals.get('protocol'))}'>{dl('protocols', protocols)}
            <div class=hint>A dated copy is placed next to your note.</div>
          </div><div>
            <label>Physical notebook page</label><input type=text name=notebook value='{esc(vals.get('notebook'))}' placeholder='NB02-153'>
          </div></div>
          <label>Samples used</label>
          {f"<div class=checks>{sample_boxes}</div>" if samples else "<div class=hint>No samples recorded yet. <a href='/new/sample'>Add one</a>.</div>"}
          <label style='margin-top:16px'><input type=checkbox name=meeting value=1 {'checked' if vals.get('meeting') else ''}> Flag for the next lab meeting</label>
          <details style='margin-top:12px'><summary class=hint>Advanced</summary>
            <label>Related experiments</label><input type=text name=related value='{esc(vals.get('related'))}' placeholder='JSRe0002, JSRe0004'>
            <label>Raw data lives elsewhere</label><input type=text name=raw_data_path value='{esc(vals.get('raw_data_path'))}' placeholder='leave blank to use 2-data_raw/'>
          </details>
          <div class=actions style='margin-top:18px'><button class=btn>Create experiment</button><a href='/' class='btn secondary'>Cancel</a></div>
        </form>"""
        return page("New experiment", body, "/experiments", self.root)

    def form_sample(self, err: str = "", vals: Optional[Dict[str, str]] = None) -> str:
        vals = vals or {}
        opts = "".join(f"<option value='{t}' {'selected' if t == vals.get('sample_type') else ''}>{t} ({l})</option>"
                       for l, t in eln.SAMPLE_LETTERS.items())
        body = f"""
        <h1>New sample</h1>{self.need_setup() or ''}{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <form class=stack method=post>
          <label>Type</label><select name=sample_type>{opts}</select>
          <label>Title</label><input type=text name=title required autofocus value='{esc(vals.get('title'))}' placeholder='e.g. pcDNA3-FLAG-SNRPB'>
          <div class=row><div><label>Source</label><input type=text name=source value='{esc(vals.get('source'))}' placeholder='vendor + catalog no., or in-house (which experiment?), or gift from whom'></div>
          <div><label>Storage location</label><input type=text name=storage value='{esc(vals.get('storage'))}' placeholder='Freezer B, box 3, A7'></div></div>
          <div class=actions style='margin-top:18px'><button class=btn>Create sample</button><a href='/samples' class='btn secondary'>Cancel</a></div>
        </form>"""
        return page("New sample", body, "/samples", self.root)

    def form_protocol(self, err: str = "", vals: Optional[Dict[str, str]] = None) -> str:
        vals = vals or {}
        body = f"""
        <h1>New protocol</h1>{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <form class=stack method=post>
          <label>Short name</label><input type=text name=name required autofocus value='{esc(vals.get('name'))}' placeholder='WesternBlot'>
          <div class=hint>Letters, digits, hyphens. Becomes <b>P_Name</b>. One living file per protocol; bump its version when the procedure changes.</div>
          <label>Full title</label><input type=text name=title value='{esc(vals.get('title'))}' placeholder='Western blot (wet transfer, PVDF)'>
          <div class=actions style='margin-top:18px'><button class=btn>Create protocol</button><a href='/protocols' class='btn secondary'>Cancel</a></div>
        </form>"""
        return page("New protocol", body, "/protocols", self.root)

    def form_project(self, err: str = "", vals: Optional[Dict[str, str]] = None) -> str:
        vals = vals or {}
        _, researcher = self.person()
        body = f"""
        <h1>New project</h1>{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <form class=stack method=post>
          <label>Short ID</label><input type=text name=project_id required autofocus value='{esc(vals.get('project_id'))}' placeholder='PRMT5-ChromatinRelease'>
          <div class=hint>Letters, digits, hyphens; starts with a letter. Experiments join it by listing this ID.</div>
          <label>Full title</label><input type=text name=title value='{esc(vals.get('title'))}'>
          <label>Lead</label><input type=text name=lead value='{esc(vals.get('lead') or researcher)}'>
          <div class=actions style='margin-top:18px'><button class=btn>Create project</button><a href='/projects' class='btn secondary'>Cancel</a></div>
        </form>"""
        return page("New project", body, "/projects", self.root)

    def form_setup(self, err: str = "", saved: bool = False) -> str:
        initials, researcher = self.person()
        body = f"""
        <h1>Settings</h1>{f"<div class='msg err'>{esc(err)}</div>" if err else ''}{"<div class='msg ok'>Saved.</div>" if saved else ''}
        <form class=stack method=post>
          <label>Your initials (2-4 letters)</label><input type=text name=initials required value='{esc(initials)}' placeholder='JSR'>
          <div class=hint>Your IDs will look like {esc(initials or 'JSR')}e0001. Numbering is per person, so nobody collides.</div>
          <label>Your full name</label><input type=text name=researcher value='{esc(researcher)}'>
          <div class=hint>Files live in <span class=path>{esc(self.root)}</span>. To change that, run <code>python3 scripts/eln.py init --root PATH</code>.</div>
          <div class=actions style='margin-top:18px'><button class=btn>Save</button><a href='/' class='btn secondary'>Back</a></div>
        </form>"""
        return page("Settings", body, "", self.root)

    def validate(self) -> str:
        v = eln.load_vault(self.root)
        issues = eln.validate_vault(v)
        n_err = sum(1 for i in issues if i.level == "ERROR")
        n_warn = len(issues) - n_err
        by_path: Dict[str, List] = {}
        for i in issues:
            by_path.setdefault(i.path, []).append(i)
        counts = ", ".join(f"{len(v.notes[k])} {k}{'s' if len(v.notes[k]) != 1 else ''}" for k in eln.KINDS)
        summary = (f"<div class='msg {'err' if n_err else 'warn' if n_warn else 'ok'}'>Checked {counts}: "
                   f"<b>{n_err} error{'s' if n_err != 1 else ''}</b>, {n_warn} warning{'s' if n_warn != 1 else ''}. "
                   + ("Everything follows the conventions." if not issues else "ERROR must be fixed; WARN is advice.") + "</div>")
        blocks = "".join(
            f"<div class=card><div class=path>{esc(p)}</div>" +
            "".join(f"<div class=issue><span class='lvl {i.level}'>{i.level}</span>{esc(i.message)}</div>" for i in by_path[p]) +
            "</div>" for p in sorted(by_path))
        return page("Check everything", f"<h1>Check everything</h1>{summary}{blocks}", "/validate", self.root)

    def report(self, saved: Optional[Path] = None) -> str:
        v = eln.load_vault(self.root)
        md = eln.build_report(v)
        msg = f"<div class='msg ok'>Saved to <span class=path>{esc(self.rel(saved))}</span> and opened.</div>" if saved else ""
        body = (f"<h1>Lab meeting brief</h1>{msg}<form class=actions method=post action='/report/save'>"
                f"<button class=btn>Save as a file and open it</button>"
                f"<span class=hint>Built from every experiment with <code>meeting</code> in its tags.</span></form>"
                f"<div class='card note'>{md_to_html(md)}</div>")
        return page("Lab meeting brief", body, "/report", self.root)

    def export_form(self, q: Dict[str, str], err: str = "") -> str:
        v = eln.load_vault(self.root)
        projects = sorted(n.id for n in v.notes["project"] if n.id)
        opts = "".join(f"<option value='{esc(p)}'>{esc(p)}</option>" for p in projects)
        result = ""
        scope = q.get("scope") or ""
        if scope:
            try:
                experiments = eln.select_for_export(
                    v, q.get("project") if scope == "project" else None,
                    eln.csv_items((q.get("ids") or "").replace(" ", ",")) if scope == "ids" else [],
                    "active" if scope == "active" else None, scope == "all")
                if not experiments:
                    err = "Nothing matched."
                else:
                    text = eln.build_export(v, experiments, related=True)
                    result = (f"<div class='msg ok'>{len(experiments)} experiment(s), {len(text):,} characters. "
                              f"Copy it all and paste into ChatGPT, or save it and attach the file.</div>"
                              f"<div class=actions><button class=btn id=exp-btn onclick=\"cp('exp')\">Copy all</button>"
                              f"<form method=post action='/export/save' style='display:inline'>"
                              f"<input type=hidden name=scope value='{esc(scope)}'><input type=hidden name=project value='{esc(q.get('project'))}'>"
                              f"<input type=hidden name=ids value='{esc(q.get('ids'))}'><button class='btn secondary'>Save as a file</button></form>"
                              f"<form method=post action='/export/save' style='display:inline'>"
                              f"<input type=hidden name=scope value='{esc(scope)}'><input type=hidden name=project value='{esc(q.get('project'))}'>"
                              f"<input type=hidden name=ids value='{esc(q.get('ids'))}'><input type=hidden name=format value=eln>"
                              f"<button class='btn secondary' title='RO-Crate archive that eLabFTW, RSpace, Kadi4Mat and others import'>Save as .eln archive</button></form></div>"
                              f"<textarea id=exp class=export readonly>{esc(text)}</textarea>")
            except eln.ElnError as e:
                err = str(e)
        body = f"""
        <h1>Export for ChatGPT</h1>{f"<div class='msg err'>{esc(err)}</div>" if err else ''}
        <form class=stack method=get>
          <label><input type=radio name=scope value=active {'checked' if scope in ('', 'active') else ''}> Every active experiment</label>
          <label><input type=radio name=scope value=project {'checked' if scope == 'project' else ''}> One project:
            <select name=project style='width:auto'>{opts}</select></label>
          <label><input type=radio name=scope value=ids {'checked' if scope == 'ids' else ''}> Specific experiments:
            <input type=text name=ids style='width:auto;min-width:320px' value='{esc(q.get('ids'))}' placeholder='JSRe0002, JSRe0007'></label>
          <label><input type=radio name=scope value=all {'checked' if scope == 'all' else ''}> Everything</label>
          <div class=actions><button class=btn>Build export</button></div>
        </form>
        <p class=hint>Paste <code>docs/ai-briefing.md</code> once into your ChatGPT Project's instructions so every chat already knows how to read this.</p>
        {result}"""
        return page("Export", body, "/export", self.root)


# --------------------------------------------------------------------------
# HTTP plumbing
# --------------------------------------------------------------------------

def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AI_ELN/" + eln.__version__

        def log_message(self, fmt, *args):  # quiet
            pass

        def send_html(self, body: str, code: int = 200):
            data = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def redirect(self, url: str):
            self.send_response(303)
            self.send_header("Location", url)
            self.end_headers()

        def not_found(self, what: str = "Not found"):
            self.send_html(page("Not found", f"<h1>{esc(what)}</h1><p><a href='/'>Home</a></p>", "", app.root), 404)

        def guard(self) -> bool:
            """Only the browser tab this page opened may talk to it. Rejects requests whose Host is not
            this server (DNS rebinding) and cross-site POSTs (a page on another site submitting a form
            to 127.0.0.1 from inside your browser)."""
            port = self.server.server_address[1]
            hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            if self.headers.get("Host", "") not in hosts:
                return self.forbid("wrong host")
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://{h}" for h in hosts}:
                return self.forbid("cross-site request")
            site = self.headers.get("Sec-Fetch-Site")
            if site and site not in ("same-origin", "none"):
                return self.forbid("cross-site request")
            return True

        def forbid(self, why: str) -> bool:
            data = f"403 Forbidden: {why}".encode("utf-8")
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return False

        def query(self) -> Dict[str, str]:
            return {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}

        def form(self) -> Dict[str, object]:
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            data = parse_qs(raw, keep_blank_values=True)
            return {k: (v if len(v) > 1 else v[0]) for k, v in data.items()}

        def do_GET(self):
            if not self.guard():
                return
            path = urlparse(self.path).path
            q = self.query()
            try:
                if path == "/":
                    return self.send_html(app.home())
                if path == "/experiments":
                    return self.send_html(app.experiments(q))
                if path == "/samples":
                    return self.send_html(app.simple_list("sample", "Samples", [("id", "ID"), ("sample_type", "Type"), ("title", "Title"), ("storage_location", "Storage"), ("status", "Status")]))
                if path == "/protocols":
                    return self.send_html(app.simple_list("protocol", "Protocols", [("id", "ID"), ("title", "Title"), ("version", "Version"), ("status", "Status")]))
                if path == "/projects":
                    return self.send_html(app.simple_list("project", "Projects", [("id", "ID"), ("title", "Title"), ("lead", "Lead"), ("status", "Status")]))
                if path.startswith("/note/"):
                    nid = path[len("/note/"):]
                    msg = ""
                    if q.get("created"):
                        msg = "<div class='msg ok'>Created. Open it in your editor and fill in the Objective; everything else can wait.</div>"
                    if q.get("warn"):
                        msg += f"<div class='msg warn'>{esc(q['warn'])}</div>"
                    if q.get("saved"):
                        msg += "<div class='msg ok'>Saved.</div>"
                    out = app.note(nid, msg)
                    return self.send_html(out) if out else self.not_found(f"No note with ID {nid}")
                if path.startswith("/edit/"):
                    out = app.edit(path[len("/edit/"):])
                    return self.send_html(out) if out else self.not_found("No such note")
                if path == "/new/experiment":
                    return self.send_html(app.form_experiment())
                if path == "/new/sample":
                    return self.send_html(app.form_sample())
                if path == "/new/protocol":
                    return self.send_html(app.form_protocol())
                if path == "/new/project":
                    return self.send_html(app.form_project())
                if path == "/setup":
                    return self.send_html(app.form_setup(saved=bool(q.get("saved"))))
                if path == "/validate":
                    return self.send_html(app.validate())
                if path == "/report":
                    return self.send_html(app.report())
                if path == "/export":
                    return self.send_html(app.export_form(q))
                if path == "/file":
                    return self.serve_file(q.get("p") or "")
                return self.not_found()
            except eln.ElnError as e:
                return self.send_html(page("Error", f"<h1>Something went wrong</h1><div class='msg err'>{esc(e)}</div>", "", app.root), 400)

        def serve_file(self, rel: str):
            p = (app.root / rel)
            if not rel or ".." in Path(rel).parts or not app.inside_root(p) or not p.is_file() \
                    or p.suffix.lower() not in IMAGE_EXT:
                return self.not_found("No such file")
            data = p.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(p.suffix.lower(), "application/octet-stream"))
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            if not self.guard():
                return
            path = urlparse(self.path).path
            f = self.form()
            g = lambda k: (f.get(k) if isinstance(f.get(k), str) else (f.get(k) or [""])[0]) or ""  # noqa: E731
            try:
                if path == "/setup":
                    initials = g("initials").strip().upper()
                    if not eln.RE_INITIALS.match(initials):
                        return self.send_html(app.form_setup(err="Initials are 2-4 letters, e.g. JSR."), 400)
                    cfg = eln.load_config()
                    cfg.update({"initials": initials, "researcher": g("researcher").strip() or initials})
                    eln.save_config(cfg)
                    return self.redirect("/setup?saved=1")
                if path == "/new/experiment":
                    initials, researcher = app.person()
                    if not initials:
                        return self.redirect("/setup")
                    samples = f.get("samples") or []
                    samples = ", ".join(samples if isinstance(samples, list) else [samples])
                    try:
                        r = eln.create_experiment(app.root, initials, researcher, g("title"), project=g("project"),
                                                  exp_type=g("exp_type"), protocol=g("protocol"), samples=samples,
                                                  related=g("related"), notebook=g("notebook"),
                                                  tags=eln.MEETING_TAG if g("meeting") else "",
                                                  raw_data_path=g("raw_data_path"))
                    except eln.ElnError as e:
                        vals = {k: g(k) for k in ("title", "project", "exp_type", "protocol", "notebook", "related", "raw_data_path", "meeting")}
                        vals["samples"] = samples
                        return self.send_html(app.form_experiment(str(e), vals), 400)
                    warn = "&warn=" + quote(" ".join(r.warnings)) if r.warnings else ""
                    return self.redirect(f"/note/{r.id}?created=1{warn}")
                if path == "/new/sample":
                    initials, _ = app.person()
                    if not initials:
                        return self.redirect("/setup")
                    try:
                        r = eln.create_sample(app.root, initials, g("sample_type"), g("title"), source=g("source"), storage=g("storage"))
                    except eln.ElnError as e:
                        return self.send_html(app.form_sample(str(e), {k: g(k) for k in ("sample_type", "title", "source", "storage")}), 400)
                    return self.redirect(f"/note/{r.id}?created=1")
                if path == "/new/protocol":
                    try:
                        r = eln.create_protocol(app.root, g("name"), title=g("title"))
                    except eln.ElnError as e:
                        return self.send_html(app.form_protocol(str(e), {k: g(k) for k in ("name", "title")}), 400)
                    return self.redirect(f"/note/{r.id}?created=1")
                if path == "/new/project":
                    try:
                        r = eln.create_project(app.root, g("project_id"), title=g("title"), lead=g("lead"))
                    except eln.ElnError as e:
                        return self.send_html(app.form_project(str(e), {k: g(k) for k in ("project_id", "title", "lead")}), 400)
                    return self.redirect(f"/note/{r.id}?created=1")
                if path.startswith("/edit/"):
                    nid = path[len("/edit/"):]
                    error, redirect = app.save_edit(nid, g("text"))
                    if error:
                        out = app.edit(nid, err=error, text=g("text"))
                        return self.send_html(out, 400) if out else self.not_found("No such note")
                    return self.redirect(redirect)
                if path.startswith("/complete/"):
                    nid = path[len("/complete/"):]
                    try:
                        r = eln.complete_experiment(app.root, nid, when=g("date") or None, force=bool(g("force")))
                    except eln.ElnError as e:
                        retry = (f"<form method=post action='/complete/{esc(nid)}' style='display:inline'>"
                                 f"<input type=hidden name=force value=1><button class='btn secondary'>Complete anyway</button></form>")
                        out = app.note(nid, f"<div class='msg err'>{esc(e)} {retry}</div>")
                        return self.send_html(out, 400) if out else self.not_found("No such experiment")
                    msg = (f"<div class='msg ok'>{esc(nid)} is complete. Snapshot <span class=path>{esc(app.rel(r['snapshot']))}</span>; "
                           f"manifest of {r['files']} files <span class=path>{esc(app.rel(r['manifest']))}</span>.</div>")
                    for w in r["warnings"]:
                        msg += f"<div class='msg warn'>{esc(w)}</div>"
                    return self.send_html(app.note(nid, msg))
                if path.startswith("/verify/"):
                    nid = path[len("/verify/"):]
                    v = eln.load_vault(app.root)
                    n = v.by_id.get(nid)
                    if n is None or n.kind != "experiment" or n.folder is None:
                        return self.not_found("No such experiment")
                    missing, modified, added = eln.verify_manifest(n.folder, nid)
                    if not (missing or modified or added):
                        msg = f"<div class='msg ok'>All {len(eln.read_manifest(n.folder, nid) or {})} files match the manifest written at completion.</div>"
                    else:
                        items = "".join(f"<li>{esc(kind)}: <span class=path>{esc(p)}</span></li>"
                                        for kind, lst in (("modified", modified), ("missing", missing), ("added", added)) for p in lst)
                        msg = (f"<div class='msg warn'>Changed since completion:<ul>{items}</ul>"
                               f"That is allowed; use <b>Refresh snapshot &amp; manifest</b> when the changes are intentional.</div>")
                    return self.send_html(app.note(nid, msg))
                if path.startswith("/render/"):
                    nid = path[len("/render/"):]
                    v = eln.load_vault(app.root)
                    n = v.by_id.get(nid)
                    if n is None:
                        return self.not_found("No such note")
                    when = date.today().isoformat()
                    out = eln.snapshot_path(n, when)
                    out.write_text(eln.render_snapshot_html(v, n, generated=when), encoding="utf-8")
                    eln.open_path(out)
                    return self.send_html(app.note(nid, f"<div class='msg ok'>Saved and opened <span class=path>{esc(app.rel(out))}</span>. "
                                                        f"It is one file with the images inside; print it to PDF from the browser.</div>"))
                if path == "/open":
                    p = app.root / g("p")
                    if not app.inside_root(p) or not p.exists():
                        return self.not_found("No such file")
                    eln.open_path(p.parent if g("folder") else p)
                    return self.redirect(self.headers.get("Referer") or "/")
                if path == "/report/save":
                    (app.root / "Inventory").mkdir(parents=True, exist_ok=True)
                    out = app.root / "Inventory" / f"meeting-brief_{date.today().strftime('%Y%m%d')}.md"
                    out.write_text(eln.build_report(eln.load_vault(app.root)), encoding="utf-8")
                    eln.open_path(out)
                    return self.send_html(app.report(saved=out))
                if path == "/export/save":
                    v = eln.load_vault(app.root)
                    scope = g("scope")
                    experiments = eln.select_for_export(
                        v, g("project") if scope == "project" else None,
                        eln.csv_items(g("ids").replace(" ", ",")) if scope == "ids" else [],
                        "active" if scope == "active" else None, scope == "all")
                    label = g("project") if scope == "project" else scope
                    (app.root / "Inventory").mkdir(parents=True, exist_ok=True)
                    if g("format") == "eln":
                        out = app.root / "Inventory" / f"export_{label}_{date.today().strftime('%Y%m%d')}.eln"
                        out.write_bytes(eln.build_eln(v, experiments, root_name=out.stem))
                        eln.open_path(out.parent)
                        note_text = ("an .eln archive (RO-Crate). Import it into eLabFTW, RSpace, Kadi4Mat, PASTA, SampleDB, "
                                     "OpenSemanticLab, or SciLog; the folder it is in was opened.")
                    else:
                        out = app.root / "Inventory" / f"export_{label}_{date.today().strftime('%Y%m%d')}.md"
                        out.write_text(eln.build_export(v, experiments), encoding="utf-8")
                        eln.open_path(out)
                        note_text = "a Markdown file, opened. Attach it to a chat or copy its contents."
                    return self.send_html(page("Export", f"<h1>Export saved</h1><div class='msg ok'>Saved "
                                               f"<span class=path>{esc(app.rel(out))}</span>: {note_text}</div>"
                                               f"<a class=btn href='/export'>Back</a>", "/export", app.root))
                return self.not_found()
            except eln.ElnError as e:
                return self.send_html(page("Error", f"<h1>Something went wrong</h1><div class='msg err'>{esc(e)}</div>", "", app.root), 400)

    return Handler


def serve(root: Path, port: int = 8765, open_browser: bool = True) -> ThreadingHTTPServer:
    """Start the server (in a background thread) and return it. Tries the next few ports if busy."""
    app = App(root)
    last_error = None
    for p in ([port] if port == 0 else range(port, port + 10)):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), make_handler(app))
            break
        except OSError as e:
            last_error = e
    else:
        raise eln.ElnError(f"could not open a port near {port}: {last_error}")
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    return server


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="eln_web.py", description="Point-and-click page for the lab research record (local only).")
    p.add_argument("--root", default=None, help="where Experiments/ etc. live (default: same resolution as eln.py)")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args(argv)
    eln.lenient_console()
    try:
        root = eln.resolve_root(args.root)
        eln.ensure_vault_dirs(root)
        server = serve(root, args.port, open_browser=not args.no_browser)
    except eln.ElnError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"AI_ELN is open at {url}")
    print(f"Files: {root}")
    print("Leave this window open while you use it. Close it (or press Ctrl+C) to stop.")
    try:
        while True:
            threading.Event().wait(3600)
    except KeyboardInterrupt:
        pass
    server.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
