# FairCreditScore — SAFe Epics, Features, User Stories

This document captures the SAFe artifacts implemented in the FairCreditScore
prototype. Naming convention: `FCS-EPIC-NNN`, `FCS-FEAT-NNN`, `US-NNN`.

---

## 1. Epic — `FCS-EPIC-001`

| Field | Detail |
|---|---|
| Epic ID | FCS-EPIC-001 |
| PI range | PI-1 → PI-3 (May 2026 → Dec 2026) |
| Business Owner | Founders / Product Lead |
| Status | In progress (prototype delivered, productionisation underway) |

### Hypothesis statement
> **For** the 400+ million UPI-active Indians and 64 million MSMEs that lack
> a CIBIL score, **who** are excluded from formal credit despite responsible
> financial behaviour, **the** FairCreditScore platform powered by
> FairCreditAI **is a** consent-based, RBI Account Aggregator–compliant
> alternative credit scoring engine **that** produces an explainable
> 300–900 score in seconds. **Unlike** traditional bureaus that grade only
> past borrowing, **our solution** grades cash-flow health, payment
> discipline, savings behaviour, and digital footprint.

### Acceptance criteria (WSJF-prioritised)

1. (WSJF-1) A new customer can sign up, provide AA consent, upload PAN +
   Aadhaar, and receive a FairCreditScore in <60 seconds.
2. (WSJF-2) The score is explainable — it surfaces the top 3 positive and
   top 3 negative factors per the canonical algorithm spec.
3. (WSJF-3) Operations staff can verify uploaded documents and inspect any
   customer's score history.
4. (WSJF-4) Administrators can manage user roles, see platform KPIs, and
   browse the source-of-truth documents.
5. (WSJF-5) Lender partners can fetch a customer's score via a JSON API.
6. (WSJF-6) The same backend plugs into the live Setu Bridge AA in
   production with a focused engineering pass.

### Non-functional requirements

| Category | Requirement |
|---|---|
| Platform | Django 5.1 + Postgres-ready (SQLite local). Heroku-deployable today. |
| Performance | Score generation <250 ms p95 on synthetic data; wiki page render <100 ms. |
| Security | Role-gated views (admin / ops / customer). CSRF on all state-changing forms. Wiki traversal-safe. |
| Data isolation | Customers can only see their own documents, consents, and scores. Operations users see all customers but cannot edit user roles. |
| Compliance | DPDP-Act-aligned consent capture; AA framework state machine modelled. |
| Accessibility | Mobile-first responsive (320 px and up); keyboard-navigable forms; WCAG 2.1 AA colour contrast on key surfaces. |

---

## 2. Features

### `FCS-FEAT-001` — Customer onboarding & profile

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Customer can self-serve sign-up, edit profile (name, DOB,
  address, occupation, income, Aadhaar last-4), and view dashboard.
- **Acceptance criteria:**
  - Given a fresh user, when they POST `/signup/` with a username, mobile,
    PAN, and password, then a `User` (role=customer) and `CustomerProfile`
    are created and they are auto-logged-in.
  - Given a logged-in customer, when they edit `/me/profile/`, then the
    `CustomerProfile` row is updated and an `AuditLog(action=profile_update)`
    entry is appended.
- **Dependencies:** none.

### `FCS-FEAT-002` — Document upload & verification

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Customer uploads PDF/JPG/PNG up to 10 MB tagged with
  doc_type. Operations role approves or rejects with optional notes.
- **Acceptance criteria:**
  - Given a customer on `/me/documents/upload/`, when they POST a 5 MB PDF,
    then a `Document(status=uploaded)` row is created and the file lands in
    `media/documents/YYYY/MM/`.
  - Given an ops user on `/ops/documents/?status=uploaded`, when they POST
    `decision=approve`, then `Document.status` flips to `verified` and
    `reviewed_by`, `reviewed_at` are set.
  - Given any user other than ops/admin, when they GET `/ops/documents/`,
    then they are redirected to the login page.
- **Dependencies:** FCS-FEAT-001.

### `FCS-FEAT-003` — Account Aggregator consent (mock)

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1 (mock) → PI-2 (live Setu)
- **Description:** Customer initiates a Setu-style consent, reviews on a
  hosted-style screen, approves or revokes. Status persists.
- **Acceptance criteria:**
  - Given a customer with no consent, when they POST `/me/consent/initiate/`,
    then a 32-char handle is created, an `AAConsent(status=pending)` row is
    written, and they land on `/me/consent/<handle>/`.
  - Given a pending consent, when the customer POSTs `approve`, then
    `status=active` and `approved_at` is stamped.
- **Dependencies:** FCS-FEAT-001.
- **Caveat:** see `aa-setu-approach.md` — flow is real, data is mocked.

### `FCS-FEAT-004` — FairCreditScore generation (dual algorithm)

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1 (synthetic) → PI-3 (XGBoost+SHAP on real data)
- **Description:** Customer can generate a 300–900 score using either the
  prototype baseline heuristic or the canonical weighted spec from
  `documents/fairCreditAI-business-idea1.jpeg`.
- **Acceptance criteria:**
  - Given a customer, when they POST `/me/score/generate/` with
    `algorithm=canonical`, then a `ScoreReport(algorithm=canonical)` row is
    created with `score = round(300 + (alt × 6))`.
  - Given a customer, when they POST with `algorithm=baseline`, then
    `ScoreReport(algorithm=baseline)` is created using the prototype
    formula. Both flows succeed for the same customer with different
    numeric outputs.
- **Dependencies:** FCS-FEAT-003 (consent, optional bonus).

### `FCS-FEAT-005` — Operations console

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Operations users review documents, search customers, and
  inspect any customer's history (documents, consents, scores).
- **Acceptance criteria:**
  - `/ops/` shows pending-doc count, active-consent count, and recent
    scores feed.
  - `/ops/customers/?q=<term>` filters on username, email, mobile, PAN.
- **Dependencies:** FCS-FEAT-002.

### `FCS-FEAT-006` — Administrator console

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Admin views platform KPIs, manages user roles, browses
  audit log.
- **Acceptance criteria:**
  - `/admin-portal/users/` lists every user; `/admin-portal/users/new/`
    creates a new user with a chosen role.
  - `/admin-portal/audit/` shows the most recent 300 audit events.
- **Dependencies:** FCS-FEAT-005.

### `FCS-FEAT-007` — Admin wiki for `documents/`

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Admin browses the repo's `documents/` folder Jekyll-style:
  markdown rendered inline, images previewed, other files downloadable.
- **Acceptance criteria:**
  - `/admin-portal/wiki/` lists the contents of `documents/`.
  - `/admin-portal/wiki/<file.md>` renders a markdown file with headings,
    code blocks, tables, and blockquotes styled like a Jekyll wiki.
  - Path traversal (`..`) is blocked with a 404.
- **Dependencies:** FCS-FEAT-006.

### `FCS-FEAT-008` — Lender API

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Lender partners fetch a customer's latest score as JSON.
- **Acceptance criteria:**
  - `GET /api/lender/score/<customer_id>/` returns `{customer_id, score,
    band, recommended_loan_amount, top_positive_factors,
    top_negative_factors, generated_at}` — or 404 if no score exists.
- **Dependencies:** FCS-FEAT-004.

### `FCS-FEAT-009` — Mobile-friendly UX

- **Parent epic:** FCS-EPIC-001
- **PI:** PI-1
- **Description:** Every page works on phones 320 px wide and up while
  preserving desktop appearance.
- **Acceptance criteria:**
  - On a 360 × 640 viewport, every page lays out without horizontal page
    scroll; tables horizontally scroll inside a `.table-wrap` container.
  - Touch targets are ≥40 px.
  - Form inputs are ≥16 px to avoid iOS zoom-on-focus.
- **Dependencies:** FCS-FEAT-001 through 008.

---

## 3. User Stories

### Under FCS-FEAT-001 (Onboarding)

- **US-001 — Customer signup**
  - As a new prospective borrower, I want to sign up with my mobile and PAN,
    so that I can start the FairCreditScore journey.
  - **Given** I am on `/signup/`, **when** I submit valid credentials,
    **then** I land on `/me/` and see the empty-score card.
  - Edge: invalid PAN format → form validation error.

- **US-002 — Profile edit**
  - As a customer, I want to add my income and Aadhaar last-4 so my score
    reflects my full profile.
  - **Given** I am on `/me/profile/`, **when** I save the form, **then** I
    am redirected to `/me/` and the updated values are visible.

### Under FCS-FEAT-002 (Documents)

- **US-003 — Upload PDF**
  - As a customer, I want to upload my PAN PDF and Aadhaar PDF so the ops
    team can verify my identity.
  - **Given** a 5 MB PDF tagged "PAN Card", **when** I submit, **then** the
    document appears in my dashboard with status "Pending".
  - Edge: 12 MB upload → "File too large (max 10MB)" form error.

- **US-004 — Ops approves a document**
  - As an ops user, I want to approve uploaded documents with optional
    notes so that the customer's identity is confirmed.
  - **Given** there is a pending PAN document, **when** I click Approve,
    **then** the badge flips to "Verified" and `Document.reviewed_by` is me.

- **US-005 — Ops rejects a bad scan**
  - As an ops user, I want to reject illegible uploads so customers know to
    re-upload.
  - **Given** a pending document, **when** I click Reject with note "Blurry",
    **then** the customer sees status "Rejected" and the note.

### Under FCS-FEAT-003 (AA consent)

- **US-006 — Initiate consent**
  - As a customer, I want to initiate AA consent so that bank data can be
    fetched.
  - **Given** the dashboard, **when** I click "Provide AA consent", **then**
    I land on the consent review page with a unique handle.

- **US-007 — Approve consent**
  - As a customer, I want to approve a consent (mock OTP `123456`) so that
    my data can be used for scoring.
  - **Given** a pending consent, **when** I click Approve, **then** the
    consent badge flips to Active.

- **US-008 — Revoke consent**
  - As a customer, I want to revoke a consent so I can stop data sharing.
  - **Given** an active consent, **when** I click Revoke, **then** status
    flips to Revoked and `revoked_at` is stamped.

### Under FCS-FEAT-004 (Scoring)

- **US-009 — Generate baseline score**
  - As a customer, I want to generate a score using the prototype heuristic
    so I can see my number quickly.
  - **Given** the dashboard, **when** I select Baseline and click Generate,
    **then** I land on `/me/score/<id>/` with a 300–900 dial.

- **US-010 — Generate canonical score**
  - As a customer, I want to generate a score using the canonical algorithm
    spec so I can see the spec-compliant version.
  - **Given** the dashboard, **when** I select Canonical and click Generate,
    **then** I land on `/me/score/<id>/` and the algorithm badge says
    "Canonical (weighted spec)".

- **US-011 — View score breakdown**
  - As a customer, I want to see what helped and hurt my score so I can
    improve it.
  - **Given** a generated score, **when** I click View Breakdown, **then** I
    see top positive and top negative SHAP-style factors.

### Under FCS-FEAT-005 (Operations)

- **US-012 — Search a customer**
  - As an ops user, I want to search by mobile number so I can pull up a
    caller in a support call.
  - **Given** `/ops/customers/`, **when** I enter "9000022222", **then** the
    matching customer (Priya) is shown.

### Under FCS-FEAT-006 (Administrator)

- **US-013 — Add an ops user**
  - As an admin, I want to create a new ops user so I can onboard a
    teammate.
  - **Given** `/admin-portal/users/new/`, **when** I save the form, **then**
    the new user appears in the user list with role Operations.

### Under FCS-FEAT-007 (Wiki)

- **US-014 — Browse wiki**
  - As an admin, I want to browse `documents/` from the web so I don't need
    repo access to read the BRD.
  - **Given** `/admin-portal/wiki/`, **when** I click on `FairCreditScore_BRD-v4.md`,
    **then** the markdown renders Jekyll-style with headings, code, and tables.

- **US-015 — Block path traversal**
  - As a security-conscious admin, I want path traversal blocked so wiki
    cannot read files outside `documents/`.
  - **Given** `/admin-portal/wiki/../README.md`, **when** I navigate,
    **then** I get a 404.

### Under FCS-FEAT-008 (Lender API)

- **US-016 — Lender pulls a score**
  - As a lender partner, I want to GET a customer's score as JSON so I can
    integrate FairCreditScore into my underwriting flow.
  - **Given** customer 3 has a score, **when** I GET
    `/api/lender/score/3/`, **then** I receive a JSON body with score,
    band, factors, and recommended loan amount.

### Under FCS-FEAT-009 (Mobile UX)

- **US-017 — Customer dashboard on a phone**
  - As a customer on a 360 px phone, I want the dashboard to be readable
    without zoom or horizontal scroll.
  - **Given** I open `/me/` on iPhone SE width, **when** the page renders,
    **then** the score dial, AA card, document list, and profile card stack
    vertically and the tables scroll horizontally inside the card.

---

## 4. Program Increment Plan

| PI | Features | Key milestones |
|---|---|---|
| PI-1 (May–Aug 2026) | FCS-FEAT-001 → FCS-FEAT-009 | Prototype demo for investors; Heroku deploy; admin wiki |
| PI-2 (Sep–Nov 2026) | Live Setu Bridge integration replacing the mock; webhook receiver; real feature engineering | NBFC anchor signed; FIU registration with Sahamati |
| PI-3 (Dec 2026 +) | XGBoost + SHAP on real consented data; multi-AA gateway (Finvu fallback); first lender pilot (Tata Capital 90-day) | Production cutover; ISO 27001 kickoff |
