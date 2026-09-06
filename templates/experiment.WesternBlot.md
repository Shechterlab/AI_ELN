---
type: experiment
experiment_id: {{EXPERIMENT_ID}}
title: {{TITLE}}
researcher: {{RESEARCHER}}
project: [{{PROJECT}}]
date_started: {{DATE}}
date_completed:
status: active            # active | complete | paused | abandoned
experiment_type: [{{EXPERIMENT_TYPE}}]
protocols: [{{PROTOCOL}}]
samples: [{{SAMPLES}}]
notebook_reference: {{NOTEBOOK_REF}}
raw_data_path: {{RAW_DATA_PATH}}
related_experiments: [{{RELATED}}]
tags: [{{TAGS}}]          # add meeting to flag this for the next lab meeting
---

# {{TITLE}}

`{{EXPERIMENT_ID}}` · {{RESEARCHER}} · {{DATE}}

<!-- This note came from templates/experiment.WesternBlot.md: the same header and sections as
     every experiment, with blot-specific prompts. Copy that file to make a template for another
     experiment type (templates/experiment.IF.md, .qPCR.md, ...); keep the header keys unchanged. -->

## Objective

<!-- One or two sentences: what question does this blot answer? -->

## Experimental design

<!-- Samples and conditions per lane, in lane order. Loading control. Biological vs technical replicates.
     What would a positive result look like? -->

## Methods

<!-- Only what is not in the snapshotted protocol:
     lysate amount per lane, gel %, transfer, blocking, primary antibodies with sample IDs and dilutions,
     secondary, detection, exposure time(s). -->

## Deviations from protocol

- None

## Results

<!-- What happened, not what it means. Band sizes vs expected; which exposure the figure shows;
     quantification method if any. Link the summary figure:
     ![](../5-figures/{{EXPERIMENT_ID}}_R_short-description.png) -->

## Interpretation

<!-- What does this tell us? Mark anything preliminary as such ("Preliminary:", "n = 1"). -->

## Decision

<!-- What happens next as a direct result of this blot? -->

## Follow-up experiments

- [ ]

## Files

- Raw data: `{{RAW_DATA_PATH}}` (imager output, original filenames)
- Analysis: `3-code/`
- Processed data: `4-data_processed/` (quantification table)
- Figures: `5-figures/` (the `_R_` summary figure)
