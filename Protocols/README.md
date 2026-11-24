# Protocols

In a notebook, `Protocols/` holds one Markdown file per protocol,
`P_{Name}.md`, made from [`templates/protocol.md`](../templates/protocol.md).
Create one with **New protocol** on the page, `launchers/New Protocol`, or
`python3 scripts/eln.py new protocol --name WesternBlot`.

**Edit the file in place.** When the *procedure* changes, change the
`version` date in the header (the `key: value` lines at the top of the
file) and add a line to the **Change log**. Do not keep dated copies here.

When an experiment is created with a protocol (`--protocol P_WesternBlot`),
the tool copies the protocol file into that experiment's `1-notes/` as
`{EXPERIMENT_ID}_P_WesternBlot_{YYYYMMDD}.md`. That copy is the record of
what was followed. Deviations on the day go in the experiment note's
**Deviations from protocol** section, never in the protocol file.

`status: archived` marks a protocol that is no longer used. `supersedes:`
names an older protocol that this one replaces, if any.

Which experiments used a protocol: `Inventory/protocols.csv`, or
`python3 scripts/eln.py find --protocol P_WesternBlot`.

This copy of the folder, in the tools folder, is empty unless the tools
folder itself is used as the notebook.
