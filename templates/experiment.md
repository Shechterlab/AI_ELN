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
tags: []
---

# {{TITLE}}

`{{EXPERIMENT_ID}}` · {{RESEARCHER}} · {{DATE}}

## Objective

<!-- One or two sentences: what question does this experiment answer? -->

## Experimental design

<!-- Conditions, groups, replicates, controls. -->

## Methods

<!-- Link the protocol version actually used. Note any deviations below, not here. -->

## Deviations from protocol

- None

## Results

<!-- Link figures/tables in 5-figures/. Describe what happened, not what it means yet. -->

## Interpretation

<!-- What does this tell us? Does it support, contradict, or refine a hypothesis? -->

## Decision

<!-- What happens next as a direct result of this experiment? -->

## Follow-up experiments

- [ ]

## Files

- Raw data: `{{RAW_DATA_PATH}}/2-data_raw/`
- Analysis: `{{RAW_DATA_PATH}}/3-code/`
- Processed data: `{{RAW_DATA_PATH}}/4-data_processed/`
- Figures: `{{RAW_DATA_PATH}}/5-figures/`
