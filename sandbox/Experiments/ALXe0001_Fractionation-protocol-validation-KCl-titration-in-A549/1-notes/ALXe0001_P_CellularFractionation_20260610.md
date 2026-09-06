---
type: protocol
protocol_id: P_CellularFractionation
title: Sub-cellular fractionation (cytoplasm / nucleoplasm / chromatin)
version: 2026-06-10         # bump this date whenever the procedure changes; add a Change log line
status: current           # current | archived
supersedes:
references: []
tags: []
---

# Sub-cellular fractionation (cytoplasm / nucleoplasm / chromatin)

`P_CellularFractionation` · version 2026-06-10

## Purpose

Separate cytoplasm, nucleoplasm, and chromatin-bound protein from adherent cells with a hypotonic lysis followed by a KCl extraction of the nuclear pellet.

## Materials

- Hypotonic buffer: 10 mM HEPES pH 7.9, 10 mM KCl, 1.5 mM MgCl2, 0.34 M sucrose, 10% glycerol, 1 mM DTT, protease inhibitors
- Nucleoplasm buffer: as above with KCl at the working concentration (300 mM validated in ALXe0001)
- Chromatin release: benzonase in 2x Laemmli

## Procedure

1. Wash 1x 10 cm dish twice in ice-cold PBS; scrape into 500 uL hypotonic buffer + 0.1% Triton X-100.
2. Ice 8 min; spin 1,300 x g 5 min 4C. Supernatant = cytoplasm.
3. Resuspend pellet in 250 uL nucleoplasm buffer; ice 30 min; spin 1,700 x g 5 min. Supernatant = nucleoplasm.
4. Resuspend pellet in 200 uL 2x Laemmli + benzonase; 10 min RT. = chromatin.
5. Load equal cell-equivalents of each fraction.

## Known failure modes / troubleshooting

<!-- Add to this over time. This is where institutional memory actually lives. -->

## Change log

- 2026-06-10: current version
- 2026-04-01: initial version

---
This is the living copy: one file per protocol, edited in place. When an
experiment uses it, `eln.py` copies this file into that experiment's
`1-notes/` as `{EXPERIMENT_ID}_P_CellularFractionation_{date}.md` - that snapshot is the
record of what was actually followed. Note deviations on the day in the
experiment note, not here.
