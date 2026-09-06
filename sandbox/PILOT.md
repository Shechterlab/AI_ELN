# Pilot: the AI features, run against this sandbox

Everything below was produced by an AI agent (Claude, in a Claude Code
session) working inside this repository with `AGENTS.md` and the skills in
`.agents/skills/lab/` loaded, against the fictional record in this folder.
Commands are shown exactly as run; answers are shown exactly as given. The
sandbox was reset with `rebuild.py` afterwards, so the experiment created
in §3 is not in the committed files.

Nothing here is real data. The point is to show the *shape* of what each
path produces before anyone tries it on real notes.

## 1. "What do we know about SNRPB chromatin retention after PRMT5 inhibition?"

Skill: `eln-search-and-cite`. Filter first, read only the matches, answer
with IDs, say what the record does not contain.

```
$ eln.py --root sandbox find --text SNRPB
ALXe0002  complete  Alex Example    SNRPB chromatin retention after 48 h PRMT5 inhibition in A549
ALXe0003  complete  Alex Example    SNRPB chromatin retention after PRMT5 inhibition in HeLa
ALXe0004  active    Alex Example    RNA-seq after 48 h PRMT5 inhibition in A549
JORe0001  complete  Jordan Example  Chromatin retention of FLAG-SNRPB R107K/R111K versus wild type
JORe0002  complete  Jordan Example  SNRPB localization by immunofluorescence after PRMT5 inhibition
JORe0003  paused    Jordan Example  Arginine methylation sites on SNRPB by mass spectrometry

$ eln.py --root sandbox find --project PRMT5-ChromatinRelease --status complete --ids
ALXe0001 ALXe0002 ALXe0003 JORe0001 JORe0002
```

Then the Results and Interpretation sections of the four complete notes
that mention SNRPB were read. The answer:

> **Supported.** 48 h PRMT5 inhibition (EPZ015666, 1 µM) roughly doubles
> the chromatin-bound fraction of SNRPB in A549: 0.31 ± 0.05 (DMSO) to
> 0.58 ± 0.07, n = 3, paired t-test p = 0.01 (ALXe0002).\* The same direction
> is seen in HeLa with a smaller effect, 0.28/0.30 to 0.41/0.46, n = 2, and
> one of the two fractionations showed slight chromatin carry-over
> (ALXe0003). The fractionation method itself was validated at 300 mM KCl
> (ALXe0001).
>
> **Preliminary.** A methyl-site mutant, FLAG-SNRPB R107K/R111K, is more
> chromatin-bound than wild type (0.55 vs 0.33), which points the same way
> as inhibition, but this is a single replicate and the mutant migrates
> slightly slower on the gel for reasons the note says are unexplained
> (JORe0001). The note's own Decision is to repeat at n = 3 with a
> revertant control before it goes in a figure.
>
> **Conflicting.** Immunofluorescence after the same treatment shows no
> change in SNRPB distribution: speckle count 18 vs 19 per nucleus,
> diffuse fraction 0.42 vs 0.44, two coverslips on two days (JORe0002). The
> note interprets this as either a change below IF resolution or the
> fractionation shift reflecting extraction resistance rather than
> relocalization; it is flagged for discussion.
>
> **Not in the record.** Whether symmetric dimethyl-arginine on SNRPB is
> actually lost under these conditions was not measured (ALXe0002 says no
> SDMA blot was run). Nothing in the exported notes addresses total SNRPB
> protein levels after inhibition. Which arginines are methylated in cells
> is the subject of JORe0003, which is paused.
>
> **In progress.** RNA-seq under the same conditions (ALXe0004) is awaiting
> sequencing.

A deliberately unanswerable question was also asked ("Did PRMT5 inhibition
change SNRPB protein levels?"):

```
$ eln.py --root sandbox find --text "protein level" --ids
(nothing)
```

The correct answer per the skill, and the one given, is: *nothing in the
record addresses total SNRPB protein levels; ALXe0002 quantified fraction
ratios, not abundance.* No guess was offered.

\* Those are the figures the ALXe0002 note stated when this was run. §6
below re-analysed the data file with a vendored skill, found the note's
SD and p-value did not match it, and the note was corrected (now SD 0.04,
p = 0.003). The answer above was faithful to the note; the note was wrong.
That order of events is the point of §6.

## 2. "Update the project page for SNRPB-ArginineMethylation"

Skill: `eln-project-synthesis`. Gather, then rewrite *Current state* in
place, every line citing IDs; single-experiment findings go under
*needing replication*.

```
$ eln.py --root sandbox find --project SNRPB-ArginineMethylation
JORe0001  complete  Jordan Example  Chromatin retention of FLAG-SNRPB R107K/R111K versus wild type
JORe0003  paused    Jordan Example  Arginine methylation sites on SNRPB by mass spectrometry
```

What the agent wrote for the page's *Current state* (the committed sandbox
page is left empty on purpose so you can try this yourself):

> ### Supported conclusions
>
> - Replacing the two candidate PRMT5 target arginines on SNRPB (R107K/R111K)
>   increases its chromatin-bound fraction in A549, 0.55 vs 0.33 for wild
>   type (JORe0001; n = 1, see below).
>
> ### Open questions / conflicting observations
>
> - Which arginines on SNRPB are methylated in cells is unknown; the mass
>   spectrometry experiment to answer it is paused pending a proteomics
>   core slot, with IP eluates at −80 °C (JORe0003).
> - The R107K/R111K mutant migrates slightly slower than wild type on the
>   gel; the note does not explain this, and it needs to be understood
>   before the retention difference is trusted (JORe0001).
>
> ### Experiments needing replication
>
> - JORe0001 (n = 1). Planned: n = 3 with a K107R/K111R revertant control.

And the short sections: *Experiments* — JORe0001 (complete, n = 1),
JORe0003 (paused); *Reagents in use* — JORp0001, JORp0002, ALXc0001;
*Related protocols* — P_CellularFractionation, P_WesternBlot.

## 3. "Start the n=3 repeat of the R107K/R111K experiment with the revertant control, for Jordan, notebook NB04-035"

Skill: `eln-record-experiment`. Check that the referenced things exist,
then create through the tool, never by hand.

```
$ eln.py --root sandbox find --kind protocol --ids
P_CellularFractionation
P_Immunofluorescence
P_WesternBlot
$ eln.py --root sandbox find --kind sample --text SNRPB --ids
ALXa0001
JORp0001
JORp0002
$ eln.py --root sandbox new experiment --initials JOR --researcher "Jordan Example" \
    --title "FLAG-SNRPB R107K/R111K chromatin retention, n=3 with K107R/K111R revertant" \
    --project "PRMT5-ChromatinRelease, SNRPB-ArginineMethylation" --type "Fractionation, WesternBlot" \
    --protocol "P_CellularFractionation, P_WesternBlot" --samples "ALXc0001, JORp0001, JORp0002, ALXa0003" \
    --related JORe0001 --notebook NB04-035
Created JORe0004
  Experiments/JORe0004_FLAG-SNRPB-R107K-R111K-chromatin-retention-n-3-with-K107R/1-notes/JORe0004.md
  Experiments/JORe0004_.../1-notes/JORe0004_P_CellularFractionation_20260610.md  (snapshot)
  Experiments/JORe0004_.../1-notes/JORe0004_P_WesternBlot_20260502.md  (snapshot)
```

The header it produced (title quoted automatically because it contains a
comma; every reference resolves):

```yaml
---
type: experiment
experiment_id: JORe0004
title: "FLAG-SNRPB R107K/R111K chromatin retention, n=3 with K107R/K111R revertant"
researcher: Jordan Example
project: [PRMT5-ChromatinRelease, SNRPB-ArginineMethylation]
date_started: 2026-09-06
status: active
experiment_type: [Fractionation, WesternBlot]
protocols: [P_CellularFractionation, P_WesternBlot]
samples: [ALXc0001, JORp0001, JORp0002, ALXa0003]
notebook_reference: NB04-035
related_experiments: [JORe0001]
---
```

```
$ eln.py --root sandbox validate
Checked 8 experiments, 3 protocols, 7 samples, 2 projects: 0 errors, 0 warnings
```

One thing the agent noticed and would raise with the person: the request
mentions a *revertant* construct (K107R/K111R), but no such plasmid exists
in `Samples/`. It did not invent one; the right next step is
`new sample --type plasmid` once the construct is made.

## 4. Lab meeting brief

```
$ eln.py --root sandbox report
```

produces, from the one experiment tagged `meeting`:

> ### ALXe0004 - RNA-seq after 48 h PRMT5 inhibition in A549
> Alex Example | project: PRMT5-ChromatinRelease | status: active | started 2026-08-25
>
> **Objective.** Which transcripts change splicing or abundance when PRMT5 is inhibited under the same conditions that increase SNRPB chromatin retention (ALXe0002)?
>
> **Results.** Awaiting sequencing (expected week of 2026-09-15).
>
> **Interpretation.** _(not written yet)_
>
> **Decision.** Analysis plan to pre-register before data arrive: differential intron retention (rMATS) as the confirmatory test; everything else exploratory.

followed by the active-by-project table, recently completed, and paused.
The `_(not written yet)_` marker is deliberate: it makes an empty section
visible in the meeting rather than silently omitted.

## 5. Export for ChatGPT

```
$ eln.py --root sandbox export --project SNRPB-ArginineMethylation --out export.md
Exported 3 experiment(s), 20,881 characters -> export.md
```

The file contains the primer from `docs/ai-briefing.md`'s rules in short
form, an inventory table, then twelve files: the project's experiments,
both project pages, the two protocols and four samples they reference,
and ALXe0002 (pulled in because JORe0001 lists it under
`related_experiments`). One hop of references, nothing more.

Asked, with only that export as context and following
`docs/ai-briefing.md`, *"Which experiments used JORp0002 and what did each
find?"*, the answer given was:

> JORp0002 (pcDNA3-FLAG-SNRPB R107K/R111K) appears in the `samples` field
> of two experiments in this export. JORe0001 (complete, n = 1) found the
> mutant's chromatin fraction was 0.55 versus 0.33 for wild type, with a
> note that the mutant migrates slightly slower on the gel. JORe0004 is
> active and has no results yet. Neither note reports the plasmid's
> sequence verification beyond the sample record's statement that it was
> verified on 2026-06-25.

## What this pilot showed

- **Filter-first works.** Every question started from `find`, not from
  reading the whole vault, and the answers cite IDs a person can open.
- **The record's hedges survived.** "Single replicate", "unexplained
  migration", "conflicts with" all made it into the answers because the
  notes said them; the skills forbid upgrading them.
- **Negative answers are given, not papered over.** The unanswerable
  question produced "nothing in the record addresses this."
- **Creation stays inside the rules.** The agent checked that protocols and
  samples existed, ran the tool, and the validator came back clean.
- **One thing to watch:** `--root` must be passed (or `AI_ELN_ROOT` set)
  when working on a record that isn't the repo's own. During this pilot it
  was found that `--root` only worked after the subcommand; it now works in
  either position.
- **Not tested here:** ChatGPT itself. The export and the briefing were
  exercised by the same agent that wrote the answers, following the
  briefing's rules. The first real test is pasting an export into the
  lab's ChatGPT and asking §1's question.

## 6. Using a vendored K-Dense skill: re-analysing ALXe0002's data

Skill: `statistical-analysis` (from `.agents/skills/vendor/k-dense-scientific/`,
scientific-agent-skills v2.66.0). Its test-selection guide says: two paired
groups, continuous outcome, normal → paired t-test; non-normal → Wilcoxon
signed-rank. Its reporting standard asks for means and SDs, `t(df)`, `p`,
an effect size, and a confidence interval. Following that on
`4-data_processed/ALXe0002_chromatin-fraction.csv` with SciPy:

```
condition  DMSO  PRMT5i          n = 3 paired replicates
1          0.29    0.55          DMSO   0.31 +/- 0.04 (mean +/- SD)
2          0.36    0.66          PRMT5i 0.58 +/- 0.07
3          0.28    0.53          mean paired difference 0.27, 95% CI [0.20, 0.34]
                                 paired t(2) = 17.7, p = 0.003; Cohen's dz = 10.2
                                 Shapiro-Wilk on differences p = 0.36 (uninformative at n = 3)
                                 Wilcoxon signed-rank p = 0.25 (the floor for n = 3)
```

**What it caught.** As first written, the note said "0.31 ± 0.05 … paired
t-test p = 0.01". The data file gives an SD of 0.04 and p = 0.003. The
note was corrected in `rebuild.py`. A stated statistic that does not match
the data file next to it is the most common kind of notebook error, and an
agent holding both can catch it in seconds; that is what the vendored
`verifying-results-before-claiming` skill asks for before any claim is
repeated. (The absurd dz of 10 also says the sandbox data are too clean to
be real, which they are.)

**What it needed.** The skill's guidance is Markdown and needed nothing.
The skill's own script, `assumption_checks.py`, imports numpy, pandas,
scipy, matplotlib, and seaborn, none of which ship with Python. It ran
unchanged under `uv run --with numpy --with pandas --with scipy --with
matplotlib --with seaborn python …`, which downloads them into a throwaway
environment on first use and leaves the system Python untouched. That one
command is the whole "installation" story for the script layer of these
skills; see `docs/ai-agents.md`.
