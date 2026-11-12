# Sandbox

Two small, **entirely fictional** notebooks to practice on. Nothing here is
real data: every number was made up by `rebuild.py`.

| Folder | Whose | What is in it |
|---|---|---|
| `alex/` | Alex Example (`ALX`) | Fractionation and western blots, an RT-qPCR with a made-up plate export and the script that analyses it, an RNA-seq in progress, one experiment adopted from an older folder (`ALXe0006`), and one older folder still waiting to be adopted |
| `jordan/` | Jordan Example (`JOR`) | A methyl-site mutant, immunofluorescence with per-nucleus scores, a paused mass-spec experiment, and one older folder still waiting |

Each folder is a notebook of its own, with a `notebook.md` that says whose it
is. There is no shared list. Jordan's notes cite Alex's cell line, antibodies,
and experiments by ID (`ALXc0001`, `ALXe0002`); those records are in Alex's
folder, and Check does not flag them as missing.

Use it to:

- see what a filled-in experiment looks like before writing your own
  (`alex/Experiments/ALXe0002_*/1-notes/ALXe0002.md` is the best example; its
  Results are the output of the script in its `3-code/`);
- try the browser page: open <https://shechterlab.github.io/AI_ELN/app/>,
  click **Open notebook folder**, and choose this `sandbox` folder. The page
  lists the two notebooks. Or choose `alex` or `jordan` directly;
- try the launcher page: double-click **`launchers/Try the Sandbox`** (Alex's
  notebook), or `python3 scripts/eln_web.py --root sandbox/jordan`;
- try the terminal commands: add `--root sandbox/alex` to any `eln.py` command;
- try adopting an older folder: `python3 scripts/eln.py --root sandbox/alex
  adopt` lists the one that is waiting;
- try the AI features: `python3 scripts/eln.py export --root sandbox/alex
  --project PRMT5-ChromatinRelease`, or open Codex / Claude Code / Cowork
  here and ask "what do we know about SNRPB chromatin retention?" with
  `AI_ELN_ROOT=sandbox/alex` set. [`PILOT.md`](PILOT.md) shows what that
  produced when the sandbox was a single notebook.

Make a mess, then put it back:

```bash
python3 sandbox/rebuild.py
```

Both notebooks are checked in CI, so they always follow
`docs/CONVENTIONS.md`.
