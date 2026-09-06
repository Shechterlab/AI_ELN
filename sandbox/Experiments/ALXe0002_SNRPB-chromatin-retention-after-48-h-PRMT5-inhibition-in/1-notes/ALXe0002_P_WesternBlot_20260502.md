---
type: protocol
protocol_id: P_WesternBlot
title: "Western blot (wet transfer, PVDF)"
version: 2026-05-02         # bump this date whenever the procedure changes; add a Change log line
status: current           # current | archived
supersedes:
references: []
tags: []
---

# Western blot (wet transfer, PVDF)

`P_WesternBlot` · version 2026-05-02

## Purpose

Standard SDS-PAGE and wet transfer for fraction analysis.

## Materials

- 4-12% Bis-Tris gels
- PVDF, methanol-activated
- 5% milk in TBST
- ECL (standard)

## Procedure

1. Load 15 uL per lane; run 150 V 60 min.
2. Transfer 30 V 90 min, 4C.
3. Block 1 h RT; primary overnight 4C; secondary 1 h RT; image on ChemiDoc.

## Known failure modes / troubleshooting

<!-- Add to this over time. This is where institutional memory actually lives. -->

## Change log

- 2026-05-02: current version
- 2026-04-01: initial version

---
This is the living copy: one file per protocol, edited in place. When an
experiment uses it, `eln.py` copies this file into that experiment's
`1-notes/` as `{EXPERIMENT_ID}_P_WesternBlot_{date}.md` - that snapshot is the
record of what was actually followed. Note deviations on the day in the
experiment note, not here.
