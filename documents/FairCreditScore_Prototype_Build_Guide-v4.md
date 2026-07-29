# FairCreditScore — Prototype Build Guide

## Choosing an Account Aggregator with Developer APIs (Sandbox / Test Mode)

**Document Version:** 1.0
**Date:** May 2026
**Purpose:** Recommend a specific Account Aggregator partner and provide a concrete roadmap to build a working FairCreditScore prototype for investor demos.

---

## 1. The Short Answer

**For your prototype, use Setu Bridge (powered by OneMoney as the licensed AA).**

Setu has the strongest developer experience in the Indian Account Aggregator ecosystem, a working public sandbox with mock data, sample apps on GitHub, and self-serve sign-up that lets you start building within minutes rather than weeks. You will not need RBI / NBFC sponsorship to access the sandbox — that requirement applies only when you go to production.

---

## 2. Why Setu (vs Finvu, OneMoney direct, Anumati, or others)

There are 16 RBI-licensed Account Aggregators in India. Only a few of them publish a self-serve developer experience. Here is the landscape you actually have to choose from for prototype work.

| Provider | Sandbox availability | Sign-up friction | Mock data quality | Best for |
|---|---|---|---|---|
| **Setu (Bridge)** | Yes — public, well-documented | Self-serve — minutes | Excellent — multiple mock FIPs (Setu FIP, Setu FIP-2) covering all 23 FI types | **Recommended for your prototype** |
| **Finvu** | Yes — public GitHub sandbox (`finvu.github.io/sandbox/`) | Self-serve via support email | Good — community + ReBIT spec implementations | Good alternative; more "raw" experience |
| **OneMoney (direct)** | Yes — sandbox + dev portal | Sign-up + business team contact | Good — middleware tools (FinPro / FinShare) | Best for production; heavier for prototype |
| **Anumati (Perfios)** | Limited public sandbox | Enterprise sales-led | N/A self-serve | Better for production after pilot stage |
| **CAMSFinServ, NeSL, CRIF Connect** | Enterprise-only | Sales-led | N/A | Not suitable for prototype |

The decision factors:

1. **Time to first working API call.** Setu can get you from sign-up to a successful mock consent flow in under an hour. Finvu in a day or two. OneMoney direct in three to five days. Others in weeks.

2. **Quality of mock data.** Setu provides two pre-built mock FIPs that simulate real bank data across savings accounts, deposits, mutual funds, insurance, and pension — across 23 FI types. This gives you a believable demo for investors. The "FIP-2" account uses a static OTP `123456` for fast iteration.

3. **Multi-AA gateway.** Setu's Bridge has a smart-routing layer that can connect to multiple licensed AAs through one integration. So even though you start with OneMoney as the underlying AA in sandbox, switching to additional AAs in production is configuration, not re-engineering.

4. **Sample code on GitHub.** Setu publishes a working Personal Finance Management sample app (`SetuHQ/account-aggregator-sample-app`) that you can fork and modify into your FairCreditScore prototype rather than building from zero.

5. **Documentation depth.** Setu's docs at `docs.setu.co` cover every step — onboarding, consent creation, data fetch, notifications, error handling, the works. Finvu's are good but sparser. OneMoney's docs are dense and enterprise-formatted.

For a prototype demo where the goal is to show investors a working flow in 4–6 weeks, Setu is the clear choice. Finvu is a strong fallback if Setu's commercial model later doesn't fit — and there's no lock-in, since the AA framework is standardised.

---

## 3. What the Sandbox Gives You

The Setu AA sandbox lets you exercise the full FIU lifecycle without being a registered FIU yourself:

- **Pre-built consent screens.** Setu hosts the user-facing consent UI — your app sends the user to a Setu URL, the user reviews the data request, approves it, and is redirected back. You don't build the consent UX.
- **Mock FIP data.** Bank statements, transactions, account balances, even mutual fund holdings — all generated in the official AA JSON/XML schema.
- **Consent flow APIs.** Create consent, check status, fetch data, revoke consent — all callable from your backend.
- **Notification webhooks.** Setu pushes you a callback when a consent status changes; for the prototype you can use a free service like Beeceptor or webhook.site to capture these without spinning up infrastructure.
- **Static OTP option.** Setu FIP-2 accounts use OTP `123456` so you can iterate without waiting for SMSes.

What you do **not** get in the sandbox:

- Real user data — everything is mock.
- Real bank integrations — you cannot fetch actual customer data without becoming a registered FIU through an NBFC anchor.
- Production rate limits or SLAs — sandbox is for development only.

For an investor demo, this is exactly the right set of constraints. Investors do not need to see a real person's data. They need to see your end-to-end product flow working: borrower journey, consent capture, data fetch, score generation, explanation. Mock data demonstrates this completely.

---

## 4. Prototype Architecture — Recommended Stack

The simplest credible stack to show investors the end-to-end FairCreditScore flow:

```
┌─────────────────────────┐
│  Borrower Web App       │ Next.js + Tailwind
│  (Borrower journey,     │
│  consent initiation,    │
│  score display)         │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Backend API            │ FastAPI (Python) or NestJS (Node)
│  (Consent orchestration,│
│  data fetch, score calc)│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐         ┌─────────────────────────┐
│  Setu Bridge / AA       │◄───────►│  Setu Mock FIPs         │
│  (Consent + Data APIs)  │         │  (Mock bank data)       │
└─────────────────────────┘         └─────────────────────────┘
            │
            ▼
┌─────────────────────────┐
│  FairCreditAI Engine    │ scikit-learn + XGBoost + SHAP
│  (Feature engineering,  │
│  scoring model,         │
│  SHAP explanations)     │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Lender API Mock        │ Express endpoint
│  (Returns score +       │
│  explanation as JSON)   │
└─────────────────────────┘
```

**Storage:** SQLite or Postgres (single-instance, no clustering). Enough for the demo.
**Hosting:** Vercel for the frontend, Railway / Render / Fly.io for the backend. Free tiers cover demo needs.
**Notifications:** Beeceptor or webhook.site for consent webhooks during development; switch to your own endpoint later.

---

## 5. Prototype Build Plan — 6-Week Roadmap

This assumes a small team of 2–3 engineers and is sized to produce a credible investor demo.

### Week 1 — Setu Onboarding & Backend Skeleton
- Sign up at `docs.setu.co` → request Account Aggregator product on Bridge.
- Get sandbox credentials (`x-product-instance-id`, `x-client_id`, `x-client-secret`).
- Set up notification endpoint with Beeceptor.
- Stand up a minimal FastAPI / NestJS backend, deploy to Render / Fly.
- Make first successful mock consent creation API call.
- Fork `SetuHQ/account-aggregator-sample-app` for reference.

### Week 2 — End-to-End Consent + Data Fetch
- Build borrower-app entry screen (name, mobile, PAN — static UI).
- Implement Setu consent flow: redirect → approval → callback.
- Implement data fetch API; receive mock bank statement JSON.
- Parse and store transactions in Postgres.
- Verify the full pipeline works for at least one mock user end-to-end.

### Week 3 — Feature Engineering
- Compute the seven features in your worked example: income consistency, expense/income ratio, savings ratio, payment timeliness, transaction frequency, bounce rate, digital engagement.
- Add UPI-specific features: distinct counterparty count, merchant-vs-P2P ratio, peak transaction hours, location stability.
- Validate features on multiple mock-user profiles to ensure variance.

### Week 4 — FairCreditAI Scoring Model
- Train a baseline XGBoost model. For the prototype, you can use synthetic labels — generate plausible "default" / "no default" outcomes correlated with your features. This is acceptable for a demo as long as you label it as a baseline calibration model, not production.
- Wire SHAP explainability so each score returns top contributing factors.
- Convert the 0–100 score into the 300–900 CIBIL-equivalent range using your published formula.
- Return a structured JSON response: `{score, risk_band, top_positive_factors, top_negative_factors, recommended_loan_amount}`.

### Week 5 — Borrower-Facing UI
- Build the score-display page with the 300–900 dial, plain-language SHAP explanations, and a "factors that improved your score" / "factors that hurt your score" breakdown.
- Build a simple loan-eligibility teaser: "Based on your score, you qualify for personal loans up to ₹X at Y% interest from partner lenders."
- Multilingual: at minimum, English + Hindi for the demo.
- Polish: animations, loading states, friendly error handling.

### Week 6 — Lender API + Investor Demo Polish
- Build the lender-side API: `POST /score?user_id=...` returning the score, risk band, and SHAP explanation as JSON. Add a Postman collection.
- Build a tiny lender admin dashboard showing aggregate stats from your demo applicants — gives investors a feel for the lender-side product.
- Pre-load 4–5 distinct mock-user profiles tied to your personas: Ramesh (kirana), Priya (salaried debit), Anil (gig worker), Lakshmi (SHG). Each tells a different scoring story.
- Record a 3-minute demo video as a backup for cases where the live demo can't run.
- Pitch dry-runs.

---

## 6. The Demo Script

Investors do not want a feature tour; they want a story. The prototype should let you walk through this in under 4 minutes:

1. **The problem (30 seconds).** Open with Ramesh's profile on a slide: 38, runs a kirana shop, ₹70,000/month UPI inflows, no CIBIL score, rejected by his bank, paying 30% to a moneylender.

2. **The solution (60 seconds).** Open the borrower app live. Enter Ramesh's mobile and PAN. Click "Generate my score." The Setu consent screen loads. Approve. Wait 5–8 seconds.

3. **The score appears (60 seconds).** Show the 300–900 dial settling at 740. Show the SHAP breakdown: "Your strong UPI inflow consistency and low bounce rate gave you 280 points. Your shorter banking history reduced 60 points." This is the "wow" moment — investors have never seen an alternative score that explains itself.

4. **The lender side (45 seconds).** Switch to the lender admin dashboard. Show the same applicant flowing through the API. Show the JSON response with the SHAP explanations, recommended loan amount, and risk band.

5. **Switch personas (45 seconds).** Run Priya (debit-first salaried, score: 790) and Anil (gig worker, score: 680) to show the model handles different segments.

The flow takes under 4 minutes and demonstrates what no incumbent has: a working, explainable, portable alternative score.

---

## 7. What This Prototype Is Not — and Honest Caveats

For your own clarity and for what you tell investors:

- **The model is a baseline, not a production scoring engine.** Production scoring requires labelled repayment outcome data from real lenders, which only comes after pilots. Be transparent about this.
- **All data is mock.** No real users, no real banks. The end-to-end flow is real; the data is simulated.
- **You are not yet a registered FIU.** Production launch requires NBFC anchor partnership and Sahamati FIU registration. The prototype lets you validate product and pitch before incurring that overhead.
- **Setu sandbox terms apply.** Sandbox use is free for development. Production pricing is roughly ₹20–30 per data fetch (volume tiered). Build into your unit economics.

These caveats actually strengthen the pitch. Investors are wary of founders who overclaim. A clean "this is a working prototype on a regulator-approved sandbox; production requires the NBFC partnership we describe in the BRD" answer is exactly what they want to hear.

---

## 8. Production Path After the Prototype

When you raise the funds and start moving toward live customers:

| Step | Activity | Timeline | Owner |
|---|---|---|---|
| 1 | Sign anchor NBFC partnership | 60–90 days | Founders + lawyer |
| 2 | Register as FIU with Sahamati under NBFC anchor | 30–45 days | Compliance |
| 3 | Move from Setu sandbox to Setu production environment | 2–4 weeks | Engineering |
| 4 | Add a second AA partner (e.g. Finvu) for redundancy via Setu's multi-AA gateway | 4–6 weeks | Engineering |
| 5 | Add bank statement PDF parsing (Perfios / FinBox) for non-AA banks | 6–8 weeks | Engineering |
| 6 | DPDP Act compliance audit, ISO 27001 kickoff | 6 months | CISO |
| 7 | First lender pilot (e.g. Tata Capital 90-day pilot from the Tata addendum) | Months 4–6 | Founders |

The key point is that the prototype work is not throwaway. The Setu integration you build for the demo is the same integration you keep for production — you flip it from sandbox to live credentials, add a second AA partner, and you are running.

---

## 9. Useful Links to Hand to Your Engineers

- **Setu AA documentation:** `https://docs.setu.co/data/account-aggregator/overview`
- **Setu AA quickstart guide:** `https://docs.setu.co/data/account-aggregator/quickstart`
- **Setu sample PFM app (fork this):** `https://github.com/SetuHQ/account-aggregator-sample-app`
- **Setu sign-up:** `https://docs.setu.co/` (top-right "Sign Up")
- **Finvu sandbox (alternative):** `https://finvu.github.io/sandbox/`
- **OneMoney developer docs (alternative):** `https://docs.onemoney.in/`
- **Sahamati (FIU registration body, for production):** `https://sahamati.org.in`
- **AA framework FI types reference:** `https://docs.setu.co/data/account-aggregator/fi-data-types`

---

## 10. Final Recommendation

Go with Setu Bridge for the prototype. Build to the 6-week plan in Section 5. Use the four-persona demo flow in Section 6 for investor pitches. Keep Finvu as your fallback if Setu's commercial terms become a problem at scale. Once you have funding and an NBFC anchor, the production path is essentially a configuration change on the same Setu integration plus a second AA partner for redundancy.

The prototype work directly de-risks your Tata Capital pilot pitch — you walk into that conversation with a working product, not a deck.

---

*— End of Document —*
