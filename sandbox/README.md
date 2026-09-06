# Sandbox

A small, **entirely fictional** research record to practice on. Two made-up
researchers (Alex Example `ALX`, Jordan Example `JOR`), two projects, three
protocols, seven samples, and seven experiments covering every status, with
filled-in notes, fake blot images, and a project page written the way the
AI skill writes them. Nothing here is real data.

Use it to:

- see what a *filled-in* experiment looks like before writing your own
  (`Experiments/ALXe0002_*/1-notes/ALXe0002.md` is the best example);
- click around the web page without touching the lab's real record:
  double-click **`launchers/Try the Sandbox`**, or
  `python3 scripts/eln_web.py --root sandbox`;
- try the terminal commands: add `--root sandbox` to any `eln.py` command;
- try the AI features: `python3 scripts/eln.py export --root sandbox
  --project PRMT5-ChromatinRelease`, or open Codex / Claude Code / Cowork
  here and ask "what do we know about SNRPB chromatin retention?" with
  `AI_ELN_ROOT=sandbox` set. [`PILOT.md`](PILOT.md) shows what that produced.

Make a mess, then put it back:

```bash
python3 sandbox/rebuild.py
```

The sandbox is validated in CI like the real example, so it always follows
`docs/CONVENTIONS.md`.
