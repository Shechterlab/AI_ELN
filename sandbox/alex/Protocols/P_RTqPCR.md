---
type: protocol
protocol_id: P_RTqPCR
title: "RT-qPCR (SYBR, 384-well)"
version: 2026-08-20         # bump this date whenever the procedure changes; add a Change log line
status: current           # current | archived
supersedes:
references: []
tags: []
---

# RT-qPCR (SYBR, 384-well)

`P_RTqPCR` · version 2026-08-20

## Purpose

Measure transcript and isoform levels relative to a reference gene.

## Materials

- RNA: column prep with on-column DNase
- cDNA: 1 ug RNA, random hexamers
- SYBR master mix, 10 uL reactions
- QuantStudio 6, 384-well block

## Procedure

1. Reverse-transcribe 1 ug RNA; include a no-RT control per sample.
2. Dilute cDNA 1:10; 2 uL per 10 uL reaction; technical triplicates.
3. 40 cycles, 60C annealing; melt curve on every run.
4. Analyse by delta-delta-Ct against ACTB; discard a technical replicate more than 0.5 Ct from the other two.

## Known failure modes / troubleshooting

<!-- Add to this over time. This is where institutional memory actually lives. -->

## Change log

- 2026-08-20: initial version
