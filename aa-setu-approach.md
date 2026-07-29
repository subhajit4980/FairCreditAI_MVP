# Account Aggregator integration — current approach

> **Short answer: no, the prototype is not currently fetching real data from
> Setu's developer APIs. The Account Aggregator (AA) flow is end-to-end
> simulated.** This document explains exactly what is real, what is mocked,
> and what it takes to switch the prototype to live Setu sandbox calls.

---

## 1. What the prototype actually does today

The customer journey runs end-to-end:

1. Customer signs up and lands on the dashboard.
2. Customer clicks **Provide AA consent**.
3. We call `core.views.initiate_consent`, which generates a 32-character
   handle (`secrets.token_hex(16)`) and creates an `AAConsent` row with
   status `pending`.
4. Customer is redirected to the **mock consent screen** at
   `/me/consent/<handle>/`, which mimics the Setu consent UI: provider name
   (`Setu Bridge (Sandbox)`), FI types
   (`DEPOSIT,TERM_DEPOSIT,RECURRING_DEPOSIT,MUTUAL_FUNDS`), purpose, and a
   note that the static OTP would be `123456`.
5. Customer clicks **Approve**. The `AAConsent` row flips to `active` and
   `approved_at` is stamped.
6. When the customer hits **Generate my score**, the scoring engine in
   `core/scoring.py` reads:
   - whether an `active` consent exists on file (boolean), and
   - how many `verified` documents exist (count),
   but **does not call any external API**. Features are synthesised from
   a per-user seeded RNG (so each persona is reproducible).

In short: the **flow is real**, the **state machine is real**, the **data is
not**.

## 2. Why the data is mocked for now

- The Setu sandbox requires a registered developer account, sandbox
  credentials (`x-product-instance-id`, `x-client_id`, `x-client-secret`),
  and a publicly reachable webhook endpoint for consent notifications.
  None of those are configured in this prototype.
- The prototype's job is to validate the **product** end-to-end (borrower
  flow, ops review, lender API) so investors can see it work. Mock data is
  acceptable at this stage — and the Build Guide
  (`documents/FairCreditScore_Prototype_Build_Guide-v4.md`) explicitly says
  so in Section 7 ("What This Prototype Is Not — and Honest Caveats").
- Once Setu credentials are issued, the integration is one focused PR
  away — see Section 4 below.

## 3. Where the mock lives

| Surface | File | Notes |
|---|---|---|
| Initiate consent | `core/views.py::initiate_consent` | Generates a handle locally, no Setu API call |
| Approve / revoke | `core/views.py::consent_approve`, `consent_revoke` | Flips `AAConsent.status` directly |
| Consent UI | `templates/core/consent_review.html` | Mimics the Setu consent screen, mentions OTP `123456` |
| Score features | `core/scoring.py::_generate_features` | Seeded synthetic features (not derived from any bank statement) |
| Provider label | `core/models.py::AAConsent.aa_provider` | Defaults to `"Setu Bridge (Sandbox)"` for visual fidelity |

There is no HTTP client, no webhook receiver, and no `requests`/`httpx`
dependency talking to `fiu.setu.co`.

## 4. What it takes to make this live (Setu sandbox)

The Build Guide already describes the full path; this section is the
engineering checklist.

### 4.1 Provision Setu sandbox

1. Sign up at `docs.setu.co` and request access to the
   **Account Aggregator** product on **Bridge**.
2. Note the three credentials Setu issues:
   - `x-product-instance-id`
   - `x-client_id`
   - `x-client-secret`
3. Set up a notification endpoint (Beeceptor / webhook.site for development;
   a `core.views.aa_webhook` endpoint for production).

Add these to environment variables:

```
SETU_API_BASE=https://fiu-sandbox.setu.co
SETU_PRODUCT_INSTANCE_ID=...
SETU_CLIENT_ID=...
SETU_CLIENT_SECRET=...
SETU_WEBHOOK_URL=https://<your-host>/aa/webhook/
```

### 4.2 Add a thin client (proposed module: `core/setu.py`)

```python
import os, httpx

class SetuClient:
    def __init__(self):
        self.base = os.environ["SETU_API_BASE"]
        self.headers = {
            "x-product-instance-id": os.environ["SETU_PRODUCT_INSTANCE_ID"],
            "x-client-id":           os.environ["SETU_CLIENT_ID"],
            "x-client-secret":       os.environ["SETU_CLIENT_SECRET"],
            "Content-Type": "application/json",
        }

    def create_consent(self, vua, fi_types, purpose):
        # POST /Consent
        ...

    def consent_status(self, consent_handle):
        # GET /Consent/handle/{handle}
        ...

    def fetch_data(self, consent_id):
        # POST /Sessions, then GET /Sessions/{id}
        ...
```

### 4.3 Replace the mock view bodies

- `initiate_consent` calls `SetuClient().create_consent(...)`, stores the
  returned `consentHandle` in `AAConsent.handle`, and **redirects the
  browser to the Setu-hosted consent URL** (we don't render our own consent
  screen — Setu hosts it).
- `consent_approve` / `consent_revoke` are no longer customer-driven.
  Instead, an `aa_webhook(request)` view receives Setu's notification and
  updates `AAConsent.status` based on the payload.
- After consent goes `ACTIVE`, a Celery / RQ job calls
  `SetuClient().fetch_data(consent_id)` and stores the bank-statement
  payload in a new `AAFetchedData` table.

### 4.4 Replace synthetic features with real ones

`core/scoring.py::_generate_features` becomes
`core/feature_engineering.py::compute_features(payload)` which derives the
seven features from real transactions:

- `income_consistency` — coefficient of variation across monthly inflows.
- `expense_ratio` — debits / credits per month, averaged.
- `savings_ratio` — closing balance trend.
- `payment_timeliness` — share of recurring debits posted on/before the
  scheduled date.
- `transaction_frequency` — monthly txn count.
- `bounce_rate` — count of NACH/cheque return narrations.
- `digital_engagement` — distinct UPI counterparties + merchant share.

The canonical scoring path in `scoring.py` already accepts these as 0–100
sub-scores, so the spec-compliant scoring math doesn't change — only the
feature source does.

### 4.5 Add the webhook endpoint

```python
# core/urls.py
path("aa/webhook/", views.aa_webhook, name="aa_webhook"),
```

Signature-verify the webhook using the shared secret Setu provisions when
you register the endpoint.

### 4.6 Acceptance criteria for "live"

- [ ] Real `consentHandle` from Setu visible on `AAConsent.handle`.
- [ ] User redirected to Setu-hosted consent URL, not a local template.
- [ ] Webhook updates `AAConsent.status` automatically.
- [ ] After approval, a fetch job populates `AAFetchedData` with the JSON
      payload that Setu's mock FIPs return.
- [ ] `scoring.py` uses `compute_features(payload)` for the real path; the
      synthetic seeded path remains available behind a feature flag for
      offline demos.

## 5. Investor-pitch wording

When asked at a pitch:

> "The prototype runs the entire AA flow end-to-end against a simulated
> Setu Bridge environment. Every stage — consent initiation, consent
> review, approval, score generation, lender API — is wired and persistent.
> The data behind the score is synthetic, deterministic per persona. The
> Setu integration itself is one focused engineering pass away — the same
> consent state machine, the same scoring math; we plug in the live Setu
> client and a webhook receiver and we're on real bank data."

That answer is honest, concrete, and matches what the Build Guide already
told investors to expect.

---

*Source files: `core/views.py`, `core/models.py`, `core/scoring.py`,
`templates/core/consent_review.html`. Spec source:
`documents/FairCreditScore_Prototype_Build_Guide-v4.md`.*
