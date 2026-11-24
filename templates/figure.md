---
type: figure
figure_id: {{FIGURE_ID}}
title: {{TITLE}}
researcher: {{RESEARCHER}}
project: [{{PROJECT}}]
experiments: [{{EXPERIMENTS}}]
label: {{LABEL}}  # what it is called where it is used (Figure 2, Fig. S3); change it when the numbering changes
target: {{TARGET}}  # where it is going: a journal, a grant, a talk, a thesis
tools: [{{TOOLS}}]  # what it is made with: R, Prism, Illustrator, CanvasX, Python, PowerPoint
width_mm:
height_mm:
date_started: {{DATE}}
date_final:
status: draft  # draft | final | published | retired
tags: [{{TAGS}}]
---

# {{TITLE}}

`{{FIGURE_ID}}` · {{RESEARCHER}} · {{DATE}}

## Purpose

<!-- One or two sentences: what the figure has to show, and where it will be used. -->

## Panels

<!-- One row per panel. "From" is the experiment the panel's data came from (its ID). "Data" is the file that was
     plotted. "Made with" is the script or program that drew it. "File" is the panel as it sits in 2-panels/. -->

| Panel | Shows | From | Data | Made with | File |
|---|---|---|---|---|---|
| a | | | | | |

## Legend

<!-- The legend as it will be printed. For each panel with a comparison: n, what n counts, and the test. -->

## Size and format

<!-- What the journal or the slide needs: width, smallest text size, fonts, colour mode, resolution, file format.
     Put the finished width and height in the header (width_mm, height_mm). -->

## Versions

<!-- One line per version that was sent to anyone: date, the file in 4-exports/, who got it, what changed. -->

## Files

- Panels, one file each: `2-panels/`
- The file the figure is laid out in (Illustrator, CanvasX, Prism, PowerPoint, an R or Python script): `3-source/`
- The finished figure, one file per version: `4-exports/`
