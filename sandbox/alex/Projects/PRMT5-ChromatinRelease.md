---
type: project
project_id: PRMT5-ChromatinRelease
title: PRMT5 inhibition and chromatin release of snRNP proteins
lead: Alex Example
contributors: [Jordan Example]
status: active            # active | complete | paused
date_started: 2026-05-20
grants: []
publications: []
tags: []
---

# PRMT5 inhibition and chromatin release of snRNP proteins

`PRMT5-ChromatinRelease`

## Aim / hypothesis

Hypothesis: PRMT5-dependent arginine methylation of Sm proteins (SNRPB in particular) is needed for snRNPs to be released from chromatin; inhibiting PRMT5 should increase the chromatin-bound fraction of SNRPB.

## Current state

<!-- Kept short and current. Update this section in place; don't append to it. -->

### Supported conclusions

- 48 h PRMT5 inhibition raises the chromatin-bound fraction of SNRPB in A549 from about 0.31 to about 0.56 (ALXe0002, n = 3, wide interval); the same direction is seen in HeLa (ALXe0003, n = 2).
- The fractionation protocol cleanly separates compartments at 300 mM KCl (ALXe0001).

### Open questions / conflicting observations

- Immunofluorescence shows no redistribution of SNRPB after PRMT5i (JORe0002, Jordan's notebook), which does not fit a simple relocalization model for the biochemical shift in ALXe0002. Extraction resistance is the leading alternative. A first pre-extraction experiment points that way (JORe0004, Jordan's notebook, preliminary and not scored blind).
- Whether the effect is mediated by SNRPB's own methylation is suggested by the R107K/R111K mutant (JORe0001, Jordan's notebook) but not established.
- MDM4 isoform switch after PRMT5i looks as predicted in a first qPCR plate (ALXe0005, preliminary, no-RT controls missing).

### Experiments needing replication

- JORe0001 (n = 1; mutant migrates slower, unexplained).

## Experiments

- ALXe0001 - fractionation validation - complete
- ALXe0002 - PRMT5i, A549 - complete
- ALXe0003 - PRMT5i, HeLa - complete
- ALXe0004 - RNA-seq - active
- ALXe0005 - MDM4 isoform qPCR - active
- In Jordan Example's notebook: JORe0001 (R107K/R111K mutant), JORe0002 (IF), JORe0004 (pre-extraction IF)

## Reagents in use

ALXc0001, ALXc0002, ALXa0001, ALXa0002, ALXa0003, ALXi0001; Jordan's plasmids JORp0001, JORp0002

## Figures

## Related protocols

P_CellularFractionation, P_WesternBlot, P_RNAextraction, P_RTqPCR
