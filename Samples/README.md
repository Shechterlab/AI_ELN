# Samples

One Markdown file per durable physical or biological thing, from
[`templates/sample.md`](../templates/sample.md): plasmid, oligo, antibody,
cell line, mouse line, peptide, protein prep, slide, or gel. Create one with
`launchers/New Sample` or `python3 scripts/eln.py new sample --type plasmid --title "..."`.

The ID is your initials + a type letter + four digits, assigned by the tool:

| letter | type | letter | type |
|---|---|---|---|
| `p` | plasmid | `m` | mouse-line |
| `i` | oligo | `t` | peptide |
| `a` | antibody | `r` | protein-prep |
| `c` | cell-line | `s` | slide |
| `g` | gel / blot | | |

This is Jacob's `JSRg###` / `JSRp###` / `JSRi###` / `JSRs####` idea with a
uniform width and a few more letters. The point is the same: one stable ID
per physical thing, reused in every experiment note (`samples: [JSRp0001]`)
and every filename that touches it.

Which experiments used a sample is **derived**, so it can't go stale: see
`Inventory/samples.csv` or `python3 scripts/eln.py find --sample JSRp0001`.

`status`: `active` | `depleted` | `retired`.
