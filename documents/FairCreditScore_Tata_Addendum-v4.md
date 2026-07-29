# FairCreditScore — Tata Group Addendum

**A Strategic Partnership Proposal**

> Why FairCreditScore + Tata is uniquely positioned to define alternative credit scoring in India

---

**Document Version:** 1.0
**Date:** May 2026
**Companion to:** FairCreditScore Business Requirements Document (v1.0)
**Confidential — For Tata Group review only**

---

## 1. Why This Document Exists

This addendum is written specifically for conversations with the Tata Group. The full FairCreditScore Business Requirements Document describes our product, market, and architecture in detail. This document answers a narrower question: **why is Tata Group the right partner for FairCreditScore, and why is FairCreditScore the right partner for Tata?**

We have written this knowing three things about Tata Group that shape the answer:

1. Tata Capital is one of India's largest NBFCs (₹2.33 lakh crore loan book, 7.3M customers, recently IPO'd) and already a sophisticated user of the RBI Account Aggregator framework — they understand alternative-data lending deeply.
2. Tata Group operates one of the few cross-sector consented data ecosystems in India outside the super-apps, spanning payments, e-commerce, healthcare, insurance, and lifestyle.
3. Tata's brand promise centres on trust, fairness, and inclusion — which aligns precisely with FairCreditScore's regulator-aligned, explainability-first design.

This combination is rare. We believe it is the basis for a partnership that benefits the financially excluded 400 million UPI-active Indians who currently sit outside the formal credit system.

---

## 2. The Strategic Insight: Tata's Cross-Group Signal Map

No single Indian fintech can match the breadth of consented behavioural data that Tata Group already collects across its operating companies. Below is an illustrative map of the signals available within the Tata ecosystem and what each one tells a credit scoring model.

| Tata Entity | Behavioural Signal | What It Predicts |
|---|---|---|
| **Tata Neu (Tata Digital)** | UPI transactions through the super-app, purchase frequency, basket diversity | Income flow regularity, digital engagement, lifestyle stability |
| **BigBasket** | Grocery spending patterns, recurring orders, basket size, geography | Household stability, disposable income floor, location consistency |
| **Croma** | Big-ticket consumer durable purchases, EMI vs upfront preference | Disposable income peaks, debt-comfort posture, household formation |
| **Tata 1mg** | Healthcare spending, prescription regularity, chronic-care patterns | Income shock vulnerability, household demographic signals |
| **Tata CLiQ** | Apparel and lifestyle e-commerce spending | Discretionary income behaviour, lifestyle inflation patterns |
| **Tata Capital** | Loan history, repayment patterns, EMI behaviour (FIP-side data) | Direct repayment behaviour for existing borrowers |
| **Tata AIA / Tata AIG** | Insurance premium payment regularity, policy lapse / renewal | Long-term financial discipline, household risk planning |
| **IHCL (Taj Hotels)** | Travel and hospitality patterns | Income tier validation, leisure spending capacity |
| **Air India / Vistara** | Travel frequency, route patterns | Mobility, income segment markers |

> **What this means.** No external fintech — not PhonePe, not Paytm, not Google Pay, not any standalone scoring company — can assemble this signal set. PhonePe doesn't have insurance. Paytm doesn't have grocery. Google Pay doesn't have healthcare. **Tata does.** With user consent and DPDP-compliant data flows, Tata Group has access to one of the most differentiated behavioural-signal ecosystems in Indian financial services.

> **What we add.** FairCreditAI is the AI engine that converts this signal ecosystem into a single, portable, explainable credit score that works with the Account Aggregator framework, complies with the DPDP Act, and is defensible under RBI's emerging algorithmic-fairness expectations. Tata has the data; we have the model.

### 2.1 Important Caveats

We want to be precise about what this signal map does and does not mean:

- **Cross-Tata data sharing requires fresh consent under DPDP.** Group-company structure does not waive consent. We design the data flows to obtain explicit, purpose-specific consent for each signal, never to assume it.
- **Some signals are sensitive.** Healthcare data (Tata 1mg) is among the most protected categories under DPDP. We treat it accordingly — opt-in only, sharply purpose-limited, never used to deny credit on health-status grounds.
- **Not every signal will be available in Phase 1.** The Tata addendum to FairCreditScore can roll out signal-by-signal, starting with the lowest-friction sources (Tata Capital own-data, Tata Neu UPI, AA-derived bank statements) before expanding into BigBasket, Croma, and beyond.
- **Cross-group integration must be regulator-defensible.** We anticipate and pre-empt RBI questions about data minimisation and fair lending bias.

---

## 3. The Three Tata Doors — and Which to Open First

We recommend approaching the Tata Group through three parallel but distinct conversations, each with a different commercial structure.

### 3.1 Door 1 — Tata Capital (the Lender Pilot)

**Audience:** Chief Risk Officer, Head of Underwriting, CTO, Head of MSME Lending.

**Pitch:** "FairCreditScore extends Tata Capital's underwriting reach into thin-file and no-file MSME and gig-worker segments — without expanding your risk envelope. We provide a second-opinion alternative score, plain-language explanations for adverse-action notices, and a champion-challenger pilot framework so you can measure us against your existing model on a defined cohort before committing."

**Commercial structure:**
- 90-day controlled pilot: 10,000 MSME or gig-worker applicants.
- Champion-challenger setup: Tata Capital's existing model decides; FairCreditScore scores in parallel; outcomes tracked.
- Pilot fee: ₹15–25 lakh fixed + per-score variable.
- Success criteria: Gini lift of ≥0.05 vs Tata Capital's existing thin-file model; or expansion of approval pool by ≥15% at constant NPA.
- Phase 2: production integration with per-score commercial terms.

**Why this works for Tata Capital:**
- Public-market story: AI-driven inclusion narrative for analyst days post-IPO.
- Risk-controlled: the pilot does not touch live underwriting decisions until proven.
- Defensible: every score returned with SHAP-based explanation supports Right-to-Explanation under DPDP and adverse-action transparency norms.
- Inclusion: directly serves the "underserved MSMEs and informal sector workers in smaller towns" segment Tata Capital has highlighted in its IPO narrative.

**Honest risk:** Tata Capital has deep internal tech capability through TCS and historically prefers to build. Our defence: speed-to-market (4 months vs 18), regulatory specialisation, dedicated explainability research, and the ability to iterate model architectures faster than an in-house team within a regulated NBFC can.

### 3.2 Door 2 — Tata Digital / Tata Neu (the Embedded Scoring Play)

**Audience:** Tata Neu product leadership, Head of Financial Services within Tata Digital.

**Pitch:** "Embed a FairCreditScore-powered credit-readiness layer inside Tata Neu. Every Neu user with a healthy alternative score sees pre-qualified loan offers from Tata Capital, Tata AIA insurance recommendations, and BNPL eligibility at checkout for BigBasket and Croma — all powered by one explainable score, one consent flow, one user-controlled data dashboard."

**Commercial structure:**
- Co-built feature: "Your Tata Score" inside the Tata Neu app.
- Revenue share on loans originated through the embedded layer.
- Joint product roadmap, FairCreditScore as the AI engine, Tata Digital as the surface.
- Equity: optional minority strategic investment from Tata Capital Growth Fund or Tata Sons venture arm.

**Why this works for Tata Digital:**
- Tata Neu has been searching for high-engagement financial-services use cases. A live, evolving credit score that improves with the user's Tata-ecosystem activity is sticky in a way few features are.
- Creates a flywheel: more Tata Neu activity → better score → better loan terms → more reason to use Tata Neu.
- Differentiates Tata Neu from Paytm and PhonePe — neither of which has the cross-sector signal depth to build a meaningful alternative score.

**Why we recommend opening this door first.** Tata Digital is younger, more product-led, and has shorter decision cycles than Tata Capital. A partnership here often unlocks the Tata Capital conversation with momentum. If Door 2 closes a soft commitment in 60 days, Door 1 typically follows in another 90.

### 3.3 Door 3 — TCS BFSI (the White-Label Distribution Play)

**Audience:** TCS BFSI vertical leadership, BaNCS product team.

**Pitch:** "License a white-labelled FairCreditScore engine as a module inside TCS's banking and lending platform offerings. TCS sells alternative credit assessment to its global BFSI client base; FairCreditScore provides the regulator-aligned, India-tested AI engine."

**Commercial structure:**
- Licensing agreement: per-deployment fee + revenue share on TCS client implementations.
- Joint go-to-market for India domestic and Indian diaspora corridor markets (UAE, Singapore).
- Long sales cycle (12–18 months); commercially significant once landed.

**Why we recommend this third.** TCS sales cycles are long, and they will want proof points before they put their name on something. Doors 1 and 2 generate those proof points. TCS becomes the multiplier once we have a working partnership at Tata Capital and Tata Neu.

### 3.4 Recommended Sequence

| Month | Door | Activity |
|---|---|---|
| 0–1 | Tata Digital | Initial conversations, product-fit workshops, exploratory partnership scoping |
| 1–3 | Tata Capital | First risk team meeting, pilot scoping, technical due diligence |
| 3–6 | Tata Digital | Tata Neu integration design, Phase 1 build kickoff |
| 3–6 | Tata Capital | 90-day pilot execution |
| 6–9 | Both | Evaluation, contract finalisation, joint announcement |
| 9–12 | TCS BFSI | Initial conversations leveraging Tata Capital and Tata Neu proof points |
| 12+ | Tata Capital Growth Fund | Strategic equity round, if pursued |

---

## 4. Why FairCreditScore vs Build Internally

Tata Group has deep technology capability through TCS, in-house data science teams at Tata Capital, and growing AI talent across Tata Digital. The natural question is: *why partner with FairCreditScore instead of building this internally?*

| Internal-build Reality | FairCreditScore Advantage |
|---|---|
| 18–24 months to first production credit-scoring model with regulatory sign-off | 4–6 months to pilot, 9–12 months to production |
| Internal teams optimise for one lender's risk appetite | We optimise for portability across lenders, which is what makes the score valuable |
| Explainability and bias-audit infrastructure built reactively under regulatory pressure | Designed-in from day one; SHAP, fairness audits, and DPDP compliance native to the architecture |
| Hard to attract specialised credit-AI talent into an NBFC org structure | Our entire team is dedicated to this single problem |
| Algorithmic accountability sits inside Tata Capital — full reputational exposure on adverse outcomes | Distributed accountability — FairCreditScore as a regulated scoring entity assumes algorithmic ownership |
| No external benchmarks; model drifts in isolation | Our model is calibrated against multiple lender partners' outcome data, producing a more generalisable signal |
| Cannot be sold or licensed externally — pure cost centre | Tata Capital can use FairCreditScore as input; Tata Digital can embed it; TCS can license it; the IP is the same |

The honest framing: Tata could absolutely build this. The question is whether spending 18–24 months and ₹50–80 crore in opportunity cost to build something we have already built is the best use of Tata's strategic capital. We believe the partnership-then-optional-acquisition path is faster, cheaper, and lower-risk.

---

## 5. Risk and Mitigation — From Tata's Perspective

Written from the perspective of a Tata Capital risk officer or Tata Digital product head evaluating this proposal.

| Tata's Concern | Our Mitigation |
|---|---|
| **Brand risk:** any FairCreditScore data or fairness incident damages the Tata brand. | DPDP-native architecture, ISO 27001 + SOC 2 roadmap, India data residency, quarterly published bias audits, contractually-binding data governance terms in the partnership agreement. |
| **Model risk:** our score performs badly in production. | Champion-challenger pilot framework so live underwriting decisions are not dependent on FairCreditScore until proven. Defined Gini, KS, and NPA thresholds before production rollout. |
| **Regulatory risk:** RBI changes alternative-scoring norms. | We operate as an LSP anchored to an NBFC partner in Phase 1, pursuing an independent CIC licence by Year 4. Engaged with RBI Regulatory Sandbox. |
| **Vendor risk:** FairCreditScore as a small company fails or is acquired by a competitor. | Source-code escrow option; right of first refusal in the partnership agreement; optional strategic equity stake by Tata Capital Growth Fund mitigates exit risk. |
| **Data leakage risk:** signals from Tata-Group consented data flowing to non-Tata lenders via the FairCreditScore platform. | Strict tenant isolation. Tata-derived signals contractually firewalled from non-Tata lender models. Independent auditor verifies. |
| **Fairness risk:** the model produces biased outcomes against women, rural, or specific linguistic groups. | Quarterly fairness audit across gender, geography, age, income, language. Annual independent algorithmic audit. Published transparency report. Tata-specific cohort fairness review. |
| **DPDP risk:** consent flows for cross-Tata signals create exposure under the DPDP Act. | Granular, purpose-specific consent design. DPIA conducted before each new signal goes live. DPO oversight on every data flow. |
| **Build-vs-buy regret:** Tata wishes it had built this internally. | Acquisition right-of-first-negotiation built into the partnership agreement. If FairCreditScore is the right long-term home for this capability inside Tata, we structure for that outcome. |

---

## 6. The Tata Capital Pilot — A Concrete Proposal

To make this tangible, here is a specific 90-day pilot structure for Tata Capital. Numbers are indicative and open to negotiation.

| Pilot Parameter | Proposal |
|---|---|
| **Duration** | 90 days from data integration go-live |
| **Cohort size** | 10,000 MSME or gig-worker loan applications |
| **Geography** | 3 states, mix of Tier-1 and Tier-2/3 cities |
| **Segment** | Thin-file applicants (CIBIL-3 score or no CIBIL file) currently at high rejection rate |
| **Architecture** | Champion-challenger: Tata Capital's existing model is decision-maker; FairCreditScore scores in parallel; outcomes tracked over 6 months post-pilot |
| **Data sources (pilot)** | Account Aggregator bank statements (primary); Tata Capital's own loan history (FIP); Tata Neu UPI activity (where applicant is a Neu user with consent) |
| **Pilot fee** | ₹20 lakh fixed + ₹25 per scored applicant |
| **Success criteria** | (a) Gini lift ≥ 0.05 vs incumbent thin-file model, OR (b) approval-pool expansion ≥ 15% at constant 6-month NPA, OR (c) NPA reduction ≥ 100 bps at constant approval rate |
| **Phase 2 trigger** | Any one of the three success criteria + Tata Capital risk committee sign-off |
| **Phase 2 commercials** | ₹35 per score (volume-tiered, dropping to ₹15 above 5L scores/quarter) + ₹2 lakh / month minimum |

This pilot is designed to be **low-risk for Tata Capital and high-information for both parties**. If the pilot fails, Tata Capital has lost a defined sum and gained substantial intelligence on alternative-data scoring. If it succeeds, both parties have a quantitative basis to expand.

---

## 7. The Specific Asks

We are asking Tata Group for three things, in order of priority:

1. **A 90-day pilot with Tata Capital** on the structure described in Section 6. This is the highest-priority ask. It is concrete, time-bound, and risk-controlled.

2. **An exploratory product workshop with Tata Digital / Tata Neu** within the next 60 days, to scope the embedded scoring opportunity inside the super-app.

3. **A view from Tata Capital Growth Fund** on whether a strategic equity round is of interest, separately from the partnership conversation. This is optional and decoupled from the partnership; we are not gating the partnership on equity.

We are deliberately asking for three things because Tata Group is large, decisions move at different speeds across entities, and we want to give the right opportunity to the right team. None of these asks is a condition for the others.

---

## 8. Closing — Why This Matters Beyond the Commercial

India is in the middle of the largest credit-architecture shift since the introduction of the modern banking system. UPI changed payments. The Account Aggregator framework changed consent. The DPDP Act changed data rights. Credit Line on UPI is changing where credit lives.

Yet credit *assessment* — the connective tissue between a borrower and a lender — is still anchored to a paradigm imported from 1960s America. CIBIL, Experian, CRIF, and Equifax score people who have already borrowed. They were never built for the 400 million Indians whose financial lives now run on UPI and digital ledgers.

FairCreditScore is built for that India. We believe the right partner is the Indian institution with the most credible, generations-long claim to public trust, the broadest cross-sector consented data ecosystem, and the strategic depth to think across NBFC lending, super-app distribution, and global tech licensing in a single conversation.

That institution is Tata.

We would be honoured to start this conversation.

---

**Contact**
FairCreditScore Founding Team
*[Founder Name] — [email] — [phone]*

---

*— End of Addendum —*
