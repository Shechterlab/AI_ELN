# Samples

One Markdown file per durable physical/biological asset — plasmid, oligo,
antibody, cell line, mouse line, peptide, protein prep — from
[`templates/sample.md`](../templates/sample.md). `sample_type` in the front
matter says which kind it is; there's one template because the questions
that matter (what is it, where did it come from, how do we know it works,
what should a labmate know before using it) are the same for all of them.

This is what replaces Jacob's `JSRg###` / `JSRp###` / `JSRi###` / `JSRs####`
ID prefixes — same idea (one stable ID per physical thing, reused in every
experiment note that touches it), just without a different prefix per
sample type. Pick whatever ID scheme the lab likes; it just needs to be
stable and unique.

To start one:

```bash
cp templates/sample.md Samples/JSRp072.md
```
