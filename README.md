# FairCreditScore

> Original brief from the product owner: *We need a prototype to showcase our
> idea of FairCreditScore. Build a web application (desktop + mobile views)
> based on Django, Python, Postgres. Administrator, operations, and customer
> roles. Customers can view their score, upload PDFs (PAN, Aadhaar), and
> provide consent to fetch data via Account Aggregator. Maintain
> `features.md`, `bugs-fixed.md`, `chat-history.md` logs.*

FairCreditScore is a Django prototype of an alternative credit-scoring
platform for India. It walks an end-to-end borrower flow — sign-up, document
upload, RBI-Account-Aggregator-style consent, score generation, score
explanation, and a JSON lender API — using our alternative-data Credit AI Model.
The data behind the score is currently synthetic (per-user seeded RNG); the
flow is real. See `aa-setu-approach.md` for what's mocked vs. wired.

---

## Directory structure

```
fair-credit-ai-sajal-bhadra/
├── README.md                            ← this file
├── Procfile                             Heroku release + web entrypoints
├── runtime.txt                          Python pin
├── requirements.txt                     Django, gunicorn, whitenoise, dj-database-url, Markdown, …
├── manage.py
├── faircredit/                          Django project (settings, urls, wsgi/asgi)
│   ├── settings.py                      Postgres-ready, WhiteNoise, env-driven
│   └── urls.py                          Includes core.urls + django-admin
├── core/                                The single Django app
│   ├── models.py                        User, CustomerProfile, Document, AAConsent, ScoreReport, AuditLog
│   ├── views.py                         Auth, customer / ops / admin / wiki / lender API
│   ├── forms.py                         Signup, profile, document upload, staff user
│   ├── scoring.py                       FairCreditAI alternative-data credit scoring engine
│   ├── urls.py                          App routes
│   ├── admin.py                         Vanilla Django admin registration
│   └── management/commands/seed_demo.py Seeds admin / ops / four personas
├── templates/core/                      Server-rendered HTML
├── static/css/app.css                   Single responsive stylesheet
├── documents/                           BRD + competitor analysis
├── docs/
│   ├── SAFe/EPIC_AND_FEATURES.md        Epic, features, user stories, PI plan
│   └── FairCreditScore_Architecture/
│       ├── SystemArchitecture.md        9-section architecture doc
│       └── diagrams/                    PlantUML .puml + rendered .png

├── aa-setu-approach.md                  Honest write-up of mock vs. live AA path
├── features.md                          Running log of major features (built + planned)
├── bugs-fixed.md                        Running log of bugs identified + resolved
├── chat-history.md                      Running log of product owner ↔ engineer interactions
└── todo.md / todo-documentation.md      Source of truth for outstanding asks
```

---

## Data models

| Model | Key fields | Description |
|---|---|---|
| `User` (extends `AbstractUser`) | `role`, `mobile`, `pan` | Custom user with role enum (admin / ops / customer) |
| `CustomerProfile` | `user (1-1)`, `full_name`, `monthly_income`, `aadhaar_last4` | Per-customer profile data |
| `Document` | `customer`, `doc_type`, `file`, `status`, `reviewed_by`, `notes` | Uploaded ID/income document (PAN, Aadhaar, bank statement, salary slip) |
| `AAConsent` | `customer`, `handle (unique)`, `aa_provider`, `fi_types`, `status`, `approved_at`, `revoked_at` | Account Aggregator consent artifact |
| `ScoreReport` | `customer`, `algorithm`, `score (1–100)`, `band`, 7 feature floats, `top_positive_factors` (JSON), `top_negative_factors` (JSON), `recommended_loan_amount` | Generated FairCreditScore record |
| `AuditLog` | `actor`, `action`, `target`, `detail`, `timestamp` | Append-only audit trail |

---

## Data flow

1. Customer signs up → `User` + `CustomerProfile` created and auto-logged-in.
2. Customer uploads a PAN PDF → `Document(status=uploaded)` written to
   `media/documents/YYYY/MM/`.
3. Customer initiates AA consent → 32-char handle + `AAConsent(status=pending)`.
4. Customer approves consent on the mock review screen → `status=active`.
5. Customer clicks **Generate my score**:
   - `core/scoring.py::generate_score(user)` processes transaction history, computes the AI credit score (1-100), and records SHAP-style factors.
6. Customer views the score detail page (dial + factors + raw features).
7. Operations user reviews uploaded documents (approve / reject + notes).
8. Lender partner GETs `/api/lender/score/<customer_id>/` → JSON.
9. Admin browses `/admin-portal/wiki/<file.md>` → markdown rendered Jekyll-style.

```
Customer ─ POST /me/score/generate/ ──► generate_my_score()
                                          │
                                          ▼
                              core.scoring.generate_score(user)
                                          │
                                          ▼
                             AI Credit Scoring Model (1-100)
                                          │
                                          ▼
                                     ScoreReport
                                          │
                                          ▼
                                 /me/score/<pk>/
```

---

## Prerequisites

- Python 3.11+
- Java 8+ (only if you want to re-render the PlantUML diagrams to PNG)
- Postgres 14+ in production; SQLite by default for dev
- A modern browser

---

## Setup

```bash
git clone https://github.com/sayan801/fair-credit-ai-sajal-bhadra.git
cd fair-credit-ai-sajal-bhadra

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (optional) point at a Postgres
# export DATABASE_URL=postgres://user:pass@localhost:5432/faircredit

python manage.py migrate
python manage.py seed_demo      # creates admin / ops / four personas
python manage.py createsuperuser  # optional, for /django-admin/
python manage.py runserver
```

Open `http://127.0.0.1:8000`.

### Seeded demo accounts

| Role | Username | Password |
|---|---|---|
| Administrator | `admin` | `admin12345` |
| Operations | `ops` | `ops12345` |
| Customer (Ramesh — kirana shop) | `ramesh` | `demo12345` |
| Customer (Priya — salaried debit) | `priya` | `demo12345` |
| Customer (Anil — gig worker) | `anil` | `demo12345` |
| Customer (Lakshmi — SHG / micro) | `lakshmi` | `demo12345` |

---

## Administrator workflow

| URL | Purpose |
|---|---|
| `/admin-portal/` | KPIs (total users by role, docs, verified docs, active consents, scores, avg score) + recent audit |
| `/admin-portal/users/` | User list (every role) |
| `/admin-portal/users/new/` | Create a new user with role |
| `/admin-portal/users/<id>/edit/` | Edit role / activate / set password |
| `/admin-portal/audit/` | Full audit trail (most recent 300) |
| `/admin-portal/wiki/` | Browse `documents/` (Jekyll-style) |
| `/admin-portal/wiki/<path>` | Render a markdown page or preview an image |
| `/admin-portal/wiki/raw/<path>` | Download the raw file |
| `/django-admin/` | Vanilla Django admin (superuser) |

## Operations workflow

| URL | Purpose |
|---|---|
| `/ops/` | Pending docs, active consents, recent scores feed |
| `/ops/documents/?status=uploaded\|verified\|rejected` | Document review queue |
| `/ops/documents/<id>/review/` (POST) | Approve or reject a document with notes |
| `/ops/customers/?q=<term>` | Search customers (username / email / mobile / PAN) |
| `/ops/customers/<id>/` | Customer detail (docs + consents + score history) |

## Customer workflow

| URL | Action |
|---|---|
| `/signup/` | Create a customer account |
| `/login/` | Sign in |
| `/me/` | Dashboard: latest score, AA consent, documents, profile summary |
| `/me/profile/` | Edit profile (name, DOB, address, occupation, income, Aadhaar last-4) |
| `/me/documents/upload/` | Upload PDF/JPG/PNG (≤ 10 MB) tagged with doc type |
| `/me/consent/initiate/` (POST) | Start AA consent — generates a handle + pending row |
| `/me/consent/<handle>/` | Review consent (mock Setu Bridge screen) |
| `/me/consent/<handle>/approve/` (POST) | Approve consent (mock OTP `123456`) |
| `/me/consent/<handle>/revoke/` (POST) | Revoke an active consent |
| `/me/score/generate/` (POST) | Generate a new score |
| `/me/score/<id>/` | Score detail (dial + SHAP-style factors + raw features) |

## Lender API

| Method | Path | Returns |
|---|---|---|
| GET | `/api/lender/score/<customer_id>/` | `{customer_id, username, score, band, recommended_loan_amount, top_positive_factors, top_negative_factors, generated_at}` |

> Production hardening: add API-key auth, signed requests, and rate limits.

---

## Document upload — formats supported

| Format | Use cases |
|---|---|
| PDF | PAN card, Aadhaar card, bank statement, salary slip |
| JPG / JPEG | Photos of physical ID cards |
| PNG | Screenshots / scanned IDs |

Limit: 10 MB per file. Validation enforced in `core.forms.DocumentUploadForm.clean_file`.

## Deduplication / idempotency strategy

- AA consent handles are 32-char `secrets.token_hex(16)`-derived (128 bits of
  entropy) and `unique=True` in the DB → safe to replay on network blips.
- Document review accepts only `decision=approve|reject`; any other value is
  rejected with a flash message rather than corrupting state.
- Score generation always *appends* a `ScoreReport`; we never mutate prior
  scores — operations users can audit drift over time.
- `AuditLog` is append-only; every meaningful state change writes one row.

---

## Key design decisions

| Decision | Rationale |
|---|---|
| Single Django app `core` | Prototype is small enough that splitting into multiple apps would be premature ceremony. |
| Custom `User` with role enum | Cleaner than three proxy models; lets the same view base reuse Django auth. |
| Single Credit AI Model scoring | Standardized alternative-data scoring model on a 1-100 scale. |
| Mock AA flow rather than live Setu | Setu sandbox needs registered credentials + a public webhook — out of scope for a first build. The state machine and UX are real. See `aa-setu-approach.md`. |
| WhiteNoise for static | Removes the need for an extra static-asset host on Heroku; works with `CompressedManifestStaticFilesStorage`. |
| Markdown wiki as its own admin route | `documents/` is the source of truth for the BRD — admins should be able to read it without repo access. Path traversal is blocked. |
| Synthetic scoring seeded by `user.id` | Makes each persona reproducible across sessions for consistent demo behaviour. |
| Mobile-first responsive CSS | The target borrower is UPI-active and phone-only. 320 px is the floor. |

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web framework | Django 5.1 |
| Database | Postgres 14+ in prod, SQLite in dev |
| Static files | WhiteNoise (compressed manifest) |
| WSGI server | gunicorn |
| Auth | Django session auth + custom role decorators |
| Markdown | python-markdown |
| Diagrams | PlantUML (Java + Graphviz to render to PNG) |
| Deployment target | Heroku (Procfile + runtime.txt) |

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `RuntimeError: Could not connect` to DB on Heroku | `DATABASE_SSL=1` on a non-SSL DB | `heroku config:set DATABASE_SSL=0` |
| `403 CSRF` on a form POST | Missing `DJANGO_CSRF_TRUSTED_ORIGINS` in prod | `heroku config:set DJANGO_CSRF_TRUSTED_ORIGINS=https://your-app.herokuapp.com` |
| `405 method not allowed` on logout | Logout link uses GET (Django 5 dropped GET) | The base template POSTs via a tiny form; update any custom links. |
| Static files 404 in prod | WhiteNoise manifest missing | `python manage.py collectstatic --noinput` (Heroku does this automatically) |
| Wiki shows the raw markdown instead of rendering | Path resolves to a binary | Ensure file extension is `.md` / `.markdown`; otherwise it downloads. |
| Diagrams won't render to PNG | `dot` not on PATH | `apt install graphviz` (or platform equivalent) |
| Score generation produces 300 always | Synthetic features generated zeroes | Re-seed: `python manage.py seed_demo` |

---

## Documentation map

- **Spec:** `documents/FairCreditScore_BRD-v4.md`,
  `documents/FairCreditScore_Prototype_Build_Guide-v4.md`
- **Algorithm:** Alternative Credit Scoring Model (1-100)
- **AA integration:** `aa-setu-approach.md` (mock vs. live Setu)
- **SAFe artifacts:** `docs/SAFe/EPIC_AND_FEATURES.md`
- **Architecture:** `docs/FairCreditScore_Architecture/SystemArchitecture.md` + `diagrams/*.png`
- **Logs:** `features.md`, `bugs-fixed.md`, `chat-history.md`

---

## License

Confidential — for investor and partner review only.
you need to write A log of  Chat History in chat-history.md.
# FairCreditAI_MVP
