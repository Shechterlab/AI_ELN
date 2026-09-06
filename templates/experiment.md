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

## Objective

<!-- One or two sentences: what question does this experiment answer? -->

## Experimental design

<!-- Conditions, groups, replicates, controls. What would a positive result look like? -->

## Methods

<!-- The protocol you followed is snapshotted next to this file as {{EXPERIMENT_ID}}_P_... .
     Only write what is not in the protocol. Deviations go in the next section. -->

## Deviations from protocol

- None

## Results

<!-- What happened, not what it means. Link the summary figure:
     ![](../5-figures/{{EXPERIMENT_ID}}_R_short-description.png) -->

## Interpretation

<!-- What does this tell us? Does it support, contradict, or refine the hypothesis?
     Mark anything tentative as such ("Preliminary:", "n = 1"); an AI reading this later keeps your hedges. -->

## Decision

<!-- What happens next as a direct result of this experiment? -->

## Follow-up experiments

- [ ]

## Files

- Raw data: `{{RAW_DATA_PATH}}`
- Analysis: `3-code/`
- Processed data: `4-data_processed/`
- Figures: `5-figures/`
