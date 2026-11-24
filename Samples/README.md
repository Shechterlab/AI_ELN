# Samples

In a notebook, `Samples/` holds one Markdown file per physical or
biological thing that is kept, made from
[`templates/sample.md`](../templates/sample.md): plasmid, oligo, antibody,
cell line, mouse line, peptide, protein prep, slide, or gel. Create one with
**New sample** on the page, `launchers/New Sample`, or
`python3 scripts/eln.py new sample --type plasmid --title "..."`.

The ID is your initials, a letter for the type, and four digits. The tool
assigns it:

| letter | type | letter | type |
|---|---|---|---|
| `p` | plasmid | `m` | mouse-line |
| `i` | oligo | `t` | peptide |
| `a` | antibody | `r` | protein-prep |
| `c` | cell-line | `s` | slide |
| `g` | gel / blot | | |

The scheme is Jacob Roth's (`JSRg###`, `JSRp###`, `JSRi###`, `JSRs####`)
with four digits for every type and a few more letters. Each thing has one
ID, and that ID is written in every experiment note (`samples: [JSRp0001]`)
and every filename that refers to the thing. A sample ID with someone
else's initials refers to a sample in that person's notebook.

Which experiments used a sample is not written in the sample note. It is
worked out from the experiment notes: see `Inventory/samples.csv` or
`python3 scripts/eln.py find --sample JSRp0001`.

`status`: `active` | `depleted` | `retired`.

This copy of the folder, in the tools folder, is empty unless the tools
folder itself is used as the notebook.
