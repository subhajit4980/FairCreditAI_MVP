---
name: diagram-mmplpnht
description: >-
  Create project diagrams in four artifacts after reading requirements: Mermaid
  (.mmd), PlantUML (.puml), rendered PNGs, and a viewable HTML index. Use when
  the user asks to diagram an architecture/workflow/data-model or wants diagrams
  in mermaid/plantuml/png/html — e.g. "create diagrams for this design",
  "diagram the integration in mermaid and plantuml", "make mmd/puml/png/html
  diagrams from the PRD", "visualize the architecture". Reads the project's
  requirements/docs first, picks the right diagram set, authors both sources,
  renders PNGs, and generates a self-contained HTML viewer.
---

# diagram-mmplpnht — multi-format diagrams (Mermaid · PlantUML · PNG · HTML)

Produce, for each diagram, **four** artifacts that stay paired:
`NN-name.mmd` (Mermaid) · `NN-name.puml` (PlantUML) · `NN-name.png`
(Mermaid render) · `NN-name.puml.png` (PlantUML render) — plus one
`index.html` that renders all the Mermaid diagrams live.

## Step 0 — Read the requirements first

Before drawing anything, read the relevant project material (PRD, architecture
doc, README, brownfield/SAD docs, code). Identify the **few high-value views**
the diagrams should convey — typically a subset of:

- **Context / component architecture** → flowchart (Mermaid) / component diagram (PlantUML)
- **Sequence / end-to-end workflow** → `sequenceDiagram` / `@startuml` sequence
- **State machine / lifecycle** → `stateDiagram-v2` / `@startuml` state
- **Data model** → `erDiagram` / PlantUML entity
- **Before/after or option comparison** → grouped flowchart / packages

Propose 3–6 diagrams (don't over-produce). **Ground each in the source** (cite
the file/section it reflects) so the diagram is accurate, not decorative.

## Step 1 — Author Mermaid (`.mmd`)

One file per diagram, named `NN-kebab-name.mmd` (e.g. `01-component-architecture.mmd`),
starting with a `%% <title/comment>` line. Choose the right diagram type.

**Mermaid gotchas (these WILL bite):**
- A semicolon `;` in `Note`/message text is a **statement separator** → use commas.
- Avoid parentheses `()` in sequence `participant X as <alias>` aliases.
- Use `<br/>` (not `\n`) for line breaks inside node labels.
- Keep node ids simple; quote labels with special chars: `A["text /api/x"]`.

## Step 2 — Author PlantUML (`.puml`)

Same content as the `.mmd`, wrapped `@startuml NN-name` … `@enduml`. Mapping:

| Mermaid | PlantUML |
|---|---|
| `flowchart` (boxes + subgraphs) | component diagram: `rectangle`/`package` groups, `database`/`cloud` shapes, `-->` / `..>` |
| `sequenceDiagram` | sequence: `participant "X" as A`, `A -> B : msg`, `A --> B : return`, `note over A`, `loop … end`, `autonumber` |
| `stateDiagram-v2` | `[*] --> S`, `state S { … }`, `S --> T : label` |
| `erDiagram` | `entity`/`enum` + relationships |

PlantUML message text may contain `{...}` and `()` freely (more readable than
Mermaid there). Keep `.mmd` and `.puml` **in sync by hand — edit both** when a
diagram changes.

## Step 3 — Render PNGs

First check tooling: `node`, `npm`, `java`, `dot` (graphviz). Install what's missing.

**Mermaid → PNG** (`@mermaid-js/mermaid-cli`, bundles a headless Chromium):
```bash
# one-time install (in a scratch dir to avoid touching the project):
( cd /tmp && npm init -y >/dev/null 2>&1 && npm i @mermaid-js/mermaid-cli >/dev/null 2>&1 )
MMDC=/tmp/node_modules/.bin/mmdc   # adjust to install path
# containers run as root → Chromium needs --no-sandbox:
printf '{"args":["--no-sandbox","--disable-setuid-sandbox","--disable-dev-shm-usage"]}' > /tmp/pptr.json
"$MMDC" -i 01-name.mmd -o 01-name.png -p /tmp/pptr.json -b white -t default --scale 3
```

**PlantUML → PNG** (`plantuml` + `graphviz`; sequence diagrams don't need dot,
but component/state/package diagrams do):
```bash
apt-get install -y plantuml graphviz   # or use plantuml.jar with Java
# PlantUML's output filename = the name after @startuml, which equals the base
# name → it COLLIDES with the Mermaid .png. Render to a temp dir, then copy with
# a .puml.png suffix so both coexist:
plantuml -tpng -o /tmp/puml ./*.puml
for b in 01-name 02-name …; do cp "/tmp/puml/$b.png" "./$b.puml.png"; done
```

> **Collision rule:** Mermaid render = `NN-name.png`; PlantUML render =
> `NN-name.puml.png`. Never let PlantUml overwrite the Mermaid PNG in place — if
> it does, `git checkout -- ./*.png` restores the tracked Mermaid renders.

## Step 4 — Generate the HTML viewer (`index.html`)

Self-contained page that renders every Mermaid diagram live via the CDN, with a
link to each PNG and source. Build it **from the `.mmd` files** so it stays in
sync: read each `.mmd`, strip `%%` comment lines, **HTML-escape** the body
(so `<br/>`, `-->` etc. survive), and inline it in `<pre class="mermaid">…</pre>`.
Load `mermaid@10` as an ES module from `https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs`
and call `mermaid.initialize({ startOnLoad: true, securityLevel: 'loose' })`.
A short Python generator (loop over the diagrams, `html.escape` each body) is the
reliable way. Re-run it whenever a `.mmd` changes. (PlantUML doesn't render
client-side without a server, so the HTML is Mermaid-based; link the `.puml.png`
for the PlantUML view.)

## Step 5 — Layout, README, verify

- Put everything in a `diagrams/` folder (e.g. under `docs/…/diagrams/`).
- Add a `README.md` listing the diagrams, the four formats, and the exact
  regeneration commands + the collision/gotcha notes above.
- **Verify before declaring done:** open/Read the rendered PNGs to confirm they
  actually rendered correctly (a parse error yields no/blank output). Fix and
  re-render until clean.
- If the project commits docs, stage and commit the `diagrams/` folder.

## Tooling quick-reference

| Need | Tool | Note |
|---|---|---|
| Mermaid → PNG | `@mermaid-js/mermaid-cli` (`mmdc`) | needs Node + headless Chromium (`--no-sandbox` in containers) |
| PlantUML → PNG | `plantuml` + `graphviz` | needs Java; `dot` required for non-sequence diagrams |
| HTML viewer | mermaid ESM via CDN | renders in the browser; no build step |

## Non-goals

- Don't invent components/flows — every diagram must trace to the requirements/code.
- Don't produce a dozen diagrams; a tight, accurate set beats breadth.
</content>
