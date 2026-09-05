# Protocols

One living Markdown file per protocol, `P_{Name}.md`, from
[`templates/protocol.md`](../templates/protocol.md). Create one with
`launchers/New Protocol` or `python3 scripts/eln.py new protocol --name WesternBlot`.

**Edit it in place** as the procedure improves. When the *procedure*
changes, bump the `version` date in the header and add a line to the
**Change log**. Don't keep dated copies here; version history is git's job
and the experiment snapshots' job:

When an experiment is created with `--protocol P_WesternBlot`, the tool
copies this file into that experiment's `1-notes/` as
`{EXPERIMENT_ID}_P_WesternBlot_{YYYYMMDD}.md`. That copy is the permanent
record of what was actually followed on the day. Deviations on the day go
in the experiment note's **Deviations from protocol** section, never here.

`status: archived` marks a protocol the lab no longer uses. `supersedes:`
names an older protocol this one replaces, if any.

Which experiments used a protocol: `Inventory/protocols.csv`, or
`python3 scripts/eln.py find --protocol P_WesternBlot`.
