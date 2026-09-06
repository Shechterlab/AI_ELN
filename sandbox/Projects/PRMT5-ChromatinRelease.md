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

- 48 h PRMT5 inhibition roughly doubles the chromatin-bound fraction of SNRPB in A549 (ALXe0002, n = 3); the same direction is seen in HeLa (ALXe0003, n = 2).
- The fractionation protocol cleanly separates compartments at 300 mM KCl (ALXe0001).

### Open questions / conflicting observations

- Immunofluorescence shows no redistribution of SNRPB after PRMT5i (JORe0002), which does not fit a simple relocalization model for the biochemical shift in ALXe0002. Extraction resistance is the leading alternative.
- Whether the effect is mediated by SNRPB's own methylation is suggested by the R107K/R111K mutant (JORe0001) but not established.

### Experiments needing replication

- JORe0001 (n = 1; mutant migrates slower, unexplained).

## Experiments

- ALXe0001 - fractionation validation - complete
- ALXe0002 - PRMT5i, A549 - complete
- ALXe0003 - PRMT5i, HeLa - complete
- JORe0001 - R107K/R111K mutant - complete (n = 1)
- JORe0002 - IF localization - complete
- ALXe0004 - RNA-seq - active

## Reagents in use

ALXc0001, ALXc0002, ALXa0001, ALXa0002, ALXa0003, JORp0001, JORp0002

## Figures

## Related protocols

P_CellularFractionation, P_WesternBlot, P_Immunofluorescence
