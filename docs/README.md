# docs/: guides and website

This folder holds the guides and the website.

**Guides** (Markdown, readable on GitHub or in any editor): [getting started](getting-started.md), the
[cheat sheet](CHEATSHEET.md), [the rules](CONVENTIONS.md), the
[lab data SOP](SOP.md), [using AI](ai-agents.md) and the
[ChatGPT briefing](ai-briefing.md), [why it is built this way](design-notes.md),
and the [overview and specification](AI_ELN_overview_and_spec.md).

**Website**: <https://shechterlab.github.io/AI_ELN/>, served by GitHub Pages
from this folder.

| file | what it is |
|---|---|
| `index.html` | the landing page |
| `guide.html` | displays a guide; it fetches the `.md` file and renders it in the browser, so there is no second copy |
| `lab.yaml` | the lab's name, links, colours, and fonts; the pages, the notebook, and the printouts read it. Edit this file to use the site for another lab |
| `assets/brand.js` | applies `lab.yaml` to a page |
| `assets/site.css` | styles, matching the lab's other sites (shechterlab.org and the tool pages) |
| `app/` | the notebook itself, running in the browser on a folder you choose; see [`app/README.md`](app/README.md) |
| `assets/site.js` | theme button and the "Name an experiment" box, which uses the notebook's own naming code (`app/lib/names.js`) |
| `assets/guide.js` | the list of guides and link rewriting |
| `assets/marked.min.js` | Markdown renderer ([marked](https://github.com/markedjs/marked) 12.0.2, MIT), vendored |
| `img/` | screenshots of the notebook page, taken from the sandbox |
| `.nojekyll` | tells GitHub Pages to serve the files without a build |

## Enabling the site

Repository **Settings → Pages → Build and deployment → Deploy from a
branch**, branch `main`, folder `/docs`, Save. The site is published at the
address above. There is no build step.

## Using the site for another lab

1. Copy the repository.
2. Edit `lab.yaml`: `lab_name`, `institution`, `department`, `lab_url`,
   `repository_url`, `site_url`, the five `color_` values, the three `font_`
   names and `font_stylesheet`.
3. Replace the logo file and point `logo:` at it.
4. Turn on GitHub Pages as described above.

No page needs editing and there is no build step. Text marked
`data-lab="..."` in the HTML is filled from `lab.yaml`, and links to this
lab's repository are rewritten to yours. Run
`python3 scripts/build_js_templates.py` once so the copy used offline
matches your file.

## Editing

- **A guide:** edit the `.md` file. The site shows the new text once it
  is on `main`.
- **A new guide:** add the `.md` file and one line to the `DOCS` list in
  `assets/guide.js`.
- **The landing page:** edit `index.html`. To preview:
  `cd docs && python3 -m http.server`, then open <http://127.0.0.1:8000/>.
- **Screenshots:** run the page on the sandbox
  (`python3 scripts/eln_web.py --root sandbox/alex`) and capture `/`,
  `/new/experiment`, and `/note/ALXe0002`.

`tests/test_site.py` checks that every link on the pages points at a file
that exists, that the guide list matches the `.md` files here, and that
the list of files kept for offline use is complete.
