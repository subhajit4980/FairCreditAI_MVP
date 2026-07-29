# FairCreditScore — Features Log

A running log of major features that have been built in this prototype, plus
features planned for the next iterations. The prototype is built on
Django 5.1 + Postgres-ready settings (SQLite by default for local) and is the
implementation of the BRD and Prototype Build Guide in `documents/`.

---

## Built — v0.1 (Prototype skeleton)

### Platform / infrastructure
- Django 5.1 project `faircredit` with `core` app.
- Custom `User` model with three roles: `admin`, `ops`, `customer`. Role checks via
  `is_admin_role`, `is_ops_role`, `is_customer_role` properties and view decorators
  (`customer_required`, `ops_required`, `admin_required`).
- Postgres-ready settings (`POSTGRES_DB`, `POSTGRES_USER`, etc. env vars) with
  SQLite fallback so the prototype runs out of the box.
- Responsive single stylesheet (`static/css/app.css`) — desktop-first with a
  mobile breakpoint at 768 px including a collapsible nav menu.
- Static + media file serving wired for development; 10 MB upload cap.
- Audit log (`AuditLog`) capturing every signup, profile edit, document upload,
  document review, consent action, score generation, and user-management action.
- Seed management command `python manage.py seed_demo` provisioning an admin,
  an ops user, and the four investor-pitch personas (Ramesh, Priya, Anil,
  Lakshmi) from the build guide.

### Authentication
- Customer self-service signup form (`/signup/`).
- Login / logout via Django's built-in auth views (custom-templated).
- Post-login routing that sends each role to the right dashboard.

### Customer features (`/me/...`)
- Customer dashboard with the FairCreditScore "dial" (300–900 band, gradient
  bar, marker), latest band label, and quick actions.
- Customer profile editor: full name, DOB, address, occupation, monthly income,
  Aadhaar last-4.
- Document upload with type selector (PAN, Aadhaar, bank statement, salary
  slip, other), MIME guard (PDF/JPG/PNG), and 10 MB size cap.
- Document list with verification status badges (Pending / Verified /
  Rejected) and ops review notes.
- Account Aggregator consent flow (mock Setu Bridge):
  - Initiate consent → `pending`.
  - Review screen mirroring an AA consent UI (provider, FI types, purpose,
    handle, mock OTP `123456`).
  - Approve → `active`.
  - Revoke → `revoked`.
- "Generate my score" action that produces a fresh `ScoreReport` and returns
  the score detail page.
- Score detail view with:
  - 300–900 dial.
  - Top positive / negative SHAP-style factor lists.
  - Underlying feature dump (income consistency, expense ratio, savings ratio,
    payment timeliness, transaction frequency, bounce rate, digital
    engagement).
  - Indicative loan eligibility amount.

### FairCreditAI engine (mock)
- `core/scoring.py` — deterministic seeded scoring engine that:
  - Computes seven baseline features (the seven from the build guide).
  - Adds bonuses for active AA consent, verified documents, and complete
    profile data.
  - Maps the synthetic 0–900 raw score into the 300–900 CIBIL-equivalent band
    (Poor / Fair / Good / Very Good / Excellent).
  - Emits SHAP-style top-positive / top-negative factor lists.
  - Recommends an indicative loan amount.

### Operations role (`/ops/...`)
- Operations dashboard with KPIs (total customers, pending docs, active
  consents, pending consents) and a recent-scores feed.
- Document review queue with tabs for `uploaded` / `verified` / `rejected`
  and inline approve / reject form (with notes).
- Customer search (username / email / mobile / PAN) with per-customer
  document and score counts.
- Customer detail page exposing all documents, consents, and score history.

### Administrator role (`/admin-portal/...`)
- Admin dashboard with platform-wide KPIs (total users by role, documents,
  verified docs, active consents, scores generated, average score).
- Recent activity stream from the audit log.
- User management (list + create + edit + role change + activate/deactivate).
- Full audit-trail view (most recent 300 entries).
- The vanilla Django admin is also available at `/django-admin/` for power users.

### Lender API mock
- `GET /api/lender/score/<customer_id>/` returns the customer's latest score
  as JSON, including SHAP factors and recommended loan amount — the exact
  shape called out in the build guide for the lender-side demo.

---

## Planned — v0.2 and beyond

### Live Setu Bridge integration (Week 1–2 of build guide)
- Replace mock consent flow with real `POST /Consent` and consent-status
  polling against `docs.setu.co`.
- Webhook endpoint for Setu consent notifications (Beeceptor-relay-friendly).
- Data fetch + persistence of FI bank statement payloads.

### Real feature engineering (Week 3)
- Parse mock FIP bank-statement JSON, compute the seven baseline features
  from real cash-flow data instead of synthetic values.
- UPI-specific features: distinct counterparty count, merchant-vs-P2P ratio,
  peak transaction hours, location stability.

### Production scoring model (Week 4)
- Replace synthetic seeded score with a trained XGBoost model.
- Wire SHAP for true per-feature attribution.
- Calibrate to the published 300–900 CIBIL-equivalent formula.

### Borrower experience polish (Week 5)
- Hindi + English language toggle (i18n already enabled).
- Loading states + animations for the consent → fetch → score pipeline.
- "Factors that improved your score" / "Factors to work on" plain-language
  recommendations.

### Lender experience (Week 6)
- Lender-admin dashboard with aggregate stats.
- Postman collection for `/api/lender/...`.
- API-key auth for lender endpoints.

### Compliance & ops
- DPDP Act audit checklist + privacy policy pages.
- Soft-delete + retention policy for documents and consents.
- ISO 27001 control mapping document.
- Account aggregator FIU registration via NBFC anchor (production prerequisite).

### Multi-AA gateway
- Add Finvu as a fallback AA provider, behind a routing layer so the consent
  flow chooses the AA based on bank availability.

### Persona library
- Expand the seeded personas with realistic mock transaction histories so the
  scoring engine has actual data to work on instead of synthetic noise.
