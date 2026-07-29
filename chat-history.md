# FairCreditScore — Chat History Log

A condensed running log of the conversation between the product owner and
Claude (acting as the engineering pair) while bootstrapping this prototype.
This is meant to be human-readable, not a verbatim transcript.

---

## Session 1 — 2 May 2026

**User:** "We need a prototype to showcase our idea of FairCreditScore. Please
read the documents folder carefully. Then build a web application (desktop view
+ mobile view) based on django, python, postgres stack. We need to have views
for administrator, operations role.. then customers can view their score..
upload their document pdf (pancard, aadhar card etc) and provide consent to
fetch data via Account aggregator. You need to write a log of all major
features built and planned in features.md, a running log of every bug
identified and resolved in bugs-fixed.md, and a log of chat history in
chat-history.md."

**Assistant:** Read `README.md` and skimmed `documents/FairCreditScore_Prototype_Build_Guide-v4.md`
plus `documents/FairCreditScore_BRD-v4.md`. Confirmed the target architecture
(Django + Postgres, with Setu Bridge AA mocked for the prototype) and the
six-week build plan. Decided to:

1. Use Django 5.1 with a custom `User` model that carries a role enum
   (admin / ops / customer) so the three dashboards can share auth.
2. Default to SQLite for local dev but make Postgres a one-env-var switch
   so the prototype is deploy-ready.
3. Mock the Setu consent flow end-to-end (initiate → review → approve / revoke)
   so the borrower journey is real even though no live AA call is happening.
4. Implement a deterministic seeded scoring engine in `core/scoring.py` that
   produces the same 7 features called out in the build guide and emits
   SHAP-style top-positive / top-negative factor lists.
5. Add a lender API mock at `GET /api/lender/score/<customer_id>/` returning
   the JSON shape the build guide specifies.
6. Add a `seed_demo` management command that creates an admin, an ops user,
   and the four investor-pitch personas (Ramesh, Priya, Anil, Lakshmi).

**Build steps performed:**

- `pip install django psycopg[binary] Pillow`.
- `django-admin startproject faircredit .` and `python manage.py startapp core`.
- Wrote `faircredit/settings.py` (Postgres-ready, custom user, media/static,
  10 MB upload cap, India locale).
- Wrote `core/models.py`: `User`, `CustomerProfile`, `Document`, `AAConsent`,
  `ScoreReport`, `AuditLog`.
- Wrote `core/forms.py`: signup, profile, document upload, staff user form.
- Wrote `core/views.py`: home, signup, role gate decorators, customer
  dashboard / profile / upload / consent flow / score generation, ops
  dashboard / document review / customer search and detail, admin dashboard
  / users / audit, lender API mock.
- Wrote `core/urls.py` and replaced `faircredit/urls.py` so the project wires
  through the core app and exposes `/django-admin/` for the built-in admin.
- Wrote responsive templates under `templates/core/` (base + 14 pages).
- Wrote `static/css/app.css` — single sheet, mobile breakpoint at 768 px,
  collapsible nav.
- Ran `makemigrations`, `migrate`, `seed_demo`. Hit B-001 through B-010
  along the way (see `bugs-fixed.md`).
- Smoke-tested all three dashboards by signing in as `admin`, `ops`, and
  `ramesh` over curl, then checking `/api/lender/score/3/` returns the
  expected JSON.

**Default credentials seeded for the demo:**

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin12345` |
| Operations | `ops` | `ops12345` |
| Customer (Ramesh) | `ramesh` | `demo12345` |
| Customer (Priya) | `priya` | `demo12345` |
| Customer (Anil) | `anil` | `demo12345` |
| Customer (Lakshmi) | `lakshmi` | `demo12345` |

**User:** "please commit and push the code"

**Assistant:** Committing the prototype skeleton and pushing it to
`claude/review-readme-start-SpWBu`.

---

## Open follow-ups

- Replace the mock Setu consent flow with real Setu Bridge API calls once
  sandbox credentials are issued.
- Replace synthetic scoring with a trained XGBoost + SHAP pipeline on real
  AA data fetched in v0.2.
- Add Hindi i18n for the borrower flow.
- Wire CI (lint + tests + docker build) before extending the prototype.
