# Documentation Todo — Reusable Checklist

A step-by-step checklist for producing complete project documentation.
Copy this file into any new project and work through it top to bottom.

---

## 1. README.md (repo root)

- [ ] One-paragraph project description (what it does, who uses it, what technology)
- [ ] Directory / folder structure (tree with one-line description per entry)
- [ ] Data models table (model name | key fields | description)
- [ ] Data flow section (numbered steps or ASCII flowchart)
- [ ] Prerequisites (runtime versions, services, OS)
- [ ] Setup instructions (clone → venv → install → env file → DB → migrate → superuser → run)
- [ ] Admin workflow table (URL | purpose)
- [ ] End-user workflow table (URL | action)
- [ ] Parser / integration formats supported (table of formats + examples)
- [ ] Deduplication / idempotency strategy
- [ ] Key design decisions table (decision | rationale)
- [ ] Tech stack table (layer | technology)
- [ ] Troubleshooting section (common errors + fix commands)

**Tool:** plain Markdown, keep in repo root.

---

## 2. SAFe Artifacts — `docs/SAFe/EPIC_AND_FEATURES.md`

### 2a. Epic
- [ ] Epic ID, PI range, Business Owner, Status
- [ ] Hypothesis statement (For / Who / The / Is a / That / Unlike / Our solution)
- [ ] Acceptance criteria (numbered, WSJF-prioritised)
- [ ] Non-functional requirements (platform, performance, security, data isolation)

### 2b. Features (one section per feature)
- [ ] Feature ID, parent epic, PI, description
- [ ] Acceptance criteria (Given/When/Then style where helpful)
- [ ] Dependencies on other features

### 2c. User Stories (grouped under each feature)
- [ ] Story ID, actor, goal, business value
- [ ] Given / When / Then acceptance criteria
- [ ] Cover: happy path, edge cases, error states, data isolation

### 2d. Program Increment Plan
- [ ] Table: PI | Features | Key milestones

**Naming convention:** `<PROJECT>-EPIC-001`, `<PROJECT>-FEAT-001`, `US-001`

---

## 3. System Architecture Document — `docs/<Project>_Architecture/SystemArchitecture.md`

Use this nine-section structure:

| # | Section | Content |
|---|---|---|
| 1 | Introduction | Purpose, scope, intended audience, document conventions |
| 2 | System Overview | Context paragraph, high-level architecture table (layers), quality attributes |
| 3 | Architectural Design | Style (MTV/MVC/Clean), design patterns table, data flow narrative, API surface tables |
| 4 | System Components | Component diagram reference, data models table, service layer description, matching/resolution logic |
| 5 | Deployment Architecture | Deployment diagram reference, runtime requirements table, env config table, deployment steps |
| 6 | Security Architecture | Auth/authorisation, data isolation rules, input validation, data protection |
| 7 | Testing Strategy | Coverage targets per module, recommended stack, test run commands |
| 8 | Scalability & Performance | Per-operation estimates, DB indexing notes, frontend notes |
| 9 | Monitoring & Observability | Logging events table (event | level | description), health checks, metrics |

---

## 4. Architecture Diagrams — `docs/<Project>_Architecture/diagrams/`

Create four diagrams as PlantUML `.puml` source files, then export to `.png`.

### Diagram 1 — High-Level Architecture
```
Layers as UML packages with colour coding:
  yellow  = Presentation (browser / frontend)
  blue    = Application (controllers / views / services)
  green   = Infrastructure (ORM / parsers / adapters)
  pink    = Data Store (database)
  purple  = Cross-cutting (logging / config / admin)

Show data flow arrows between layers with protocol labels.
```

### Diagram 2 — Request Data Flow (Sequence Diagram)
```
Cover the 3-5 most important workflows end-to-end:
  - Primary import / create flow
  - Primary read / view flow
  - Background / async flow (if any)
  - Error / conflict resolution flow
  - Admin override / reclassification flow

Participants: Frontend | API/Views | Service Layer | Repository/ORM | Database | External (if any)
```

### Diagram 3 — Component Diagram
```
Show all modules / classes within the application layer:
  - Group by responsibility (Models, Domain/Service, Application, Presentation, Infrastructure)
  - Draw dependency arrows (A --> B means A depends on B)
  - Label key method names inside components where helpful
```

### Diagram 4 — Deployment Diagram
```
Show runtime topology:
  - Client machine (browser / app)
  - Application server (runtime, web server, process manager)
  - Database server
  - File storage (local or cloud)
  - Reverse proxy (if production)

Include connection protocols (HTTPS:443, TCP:5432, etc.)
Add a note distinguishing dev vs production setup.
```

### Exporting diagrams to PNG

**Requires:** Java 8+ and PlantUML jar.

```bash
# Download PlantUML (one-time)
curl -L -o /tmp/plantuml.jar \
  https://github.com/plantuml/plantuml/releases/download/v1.2024.8/plantuml-1.2024.8.jar

# Render all diagrams in a folder
java -jar /tmp/plantuml.jar -tpng -o docs/<Project>_Architecture/diagrams/ \
  docs/<Project>_Architecture/diagrams/*.puml
```

**Windows:**
```bat
java -jar C:\temp\plantuml.jar -tpng -o "docs\<Project>_Architecture\diagrams" "docs\<Project>_Architecture\diagrams\*.puml"
```

Commit both `.puml` (source) and `.png` (rendered) files.
Add `.png` files to git; `.puml` files are the single source of truth.

---

## 5. Git Conventions

- [ ] Commit documentation in a single dedicated commit after the feature is stable
- [ ] Commit message format:
  ```
  Add <project> SAFe artifacts and system architecture documentation

  - docs/SAFe/EPIC_AND_FEATURES.md: N epics, N features, N user stories
  - docs/<Project>_Architecture/SystemArchitecture.md: 9-section architecture doc
  - docs/<Project>_Architecture/diagrams/*.puml: 4 PlantUML source diagrams
  ```
- [ ] Separate commit for PNG exports:
  ```
  Export PlantUML diagrams to PNG
  Rendered using PlantUML <version> + Java <version>
  ```

---

## 6. Folder Structure Convention

```
docs/
├── SAFe/
│   └── EPIC_AND_FEATURES.md
├── <Project>_Architecture/
│   ├── SystemArchitecture.md
│   └── diagrams/
│       ├── 01_high_level_architecture.puml
│       ├── 01_high_level_architecture.png
│       ├── 02_sequence_diagram.puml
│       ├── 02_sequence_diagram.png
│       ├── 03_component_diagram.puml
│       ├── 03_component_diagram.png
│       ├── 04_deployment_diagram.puml
│       └── 04_deployment_diagram.png
└── todo-documentation.md       ← this file
```

---

## 7. PlantUML Colour Palette (Bootstrap-friendly)

| Layer | Background | Border |
|---|---|---|
| Presentation | `#FFFDE7` | `#F9A825` |
| Application | `#E3F2FD` | `#1565C0` |
| Domain/Service | `#E8F5E9` | `#2E7D32` |
| Infrastructure | `#FFF9C4` | `#F57F17` |
| Data Store | `#FCE4EC` | `#C62828` |
| Cross-Cutting | `#EDE7F6` | `#4527A0` |

Apply with `skinparam package { BackgroundColor<<Layer>> #HEXHEX }`.

---

## 8. Checklist — When Documentation Is "Done"

- [ ] README answers: what is it, how do I set it up, how do I use it, how does it work
- [ ] SAFe doc covers every implemented feature with at least one user story each
- [ ] Architecture doc has all 9 sections filled (no placeholder headings)
- [ ] All 4 diagrams exist as both `.puml` and `.png`
- [ ] Diagrams are referenced from SystemArchitecture.md with `![title](diagrams/0N_name.png)`
- [ ] All docs committed to `main` (or `docs` branch if team convention differs)
- [ ] `db/README.md` updated with correct dump/restore commands if a database is involved
