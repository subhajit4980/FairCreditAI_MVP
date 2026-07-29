# FairCreditScore — Business Requirements Document

**An Alternative Credit Scoring Platform for India**
*Powered by FairCreditAI*

> Unlocking formal credit for 400+ million UPI-active Indians

---

**Document Version:** 1.0
**Status:** Draft for Investor Review
**Date:** May 2026
**Confidential — For investor and partner review only**

---

## Document Control

| Field | Detail |
|---|---|
| Document Title | FairCreditScore — Business Requirements Document (BRD) |
| Product Name | FairCreditScore (AI Engine: FairCreditAI) |
| Version | 1.0 |
| Status | Draft — for investor review |
| Author | FairCreditScore Product Team |
| Audience | Investors, founding team, prospective lender partners |
| Document Type | Business Requirements Document |

### Revision History

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.1 | Apr 2026 | Product Team | Initial draft; problem statement and solution outline |
| 0.5 | Apr 2026 | Product Team | Added functional requirements, scoring framework, market analysis |
| 1.0 | May 2026 | Product Team | Investor-ready version; finalised competitor analysis and roadmap |

---

## 1. Executive Summary

FairCreditScore is an AI-powered alternative credit scoring platform built for the New India — a country where over 400 million people transact daily on UPI but remain invisible to the formal credit system. Our flagship engine, FairCreditAI, generates a CIBIL-equivalent credit score using non-traditional yet fully verifiable digital footprints: UPI transaction history, employer payroll records, online purchase patterns, and digital cashbook entries maintained by small businesses.

The Indian credit ecosystem operates on a paradox: you need credit history to get credit, but you cannot build credit history without first taking credit. This single design flaw excludes hundreds of millions of financially responsible Indians — gig workers, small shopkeepers, blue-collar earners, salaried professionals who prefer debit, and rural entrepreneurs — from formal lending. As a result, they are forced toward informal lenders charging 24–36% annual interest, or simply remain locked out of growth capital altogether.

FairCreditScore changes this. By using consent-based, RBI Account Aggregator–compliant data pipelines, our platform produces a fair, explainable, and inclusive credit score in seconds. We do not replace CIBIL; we extend the credit perimeter to the segments CIBIL was never built for. Our target users include the new-to-credit (NTC) population, the 64 million MSMEs in India, gig and platform workers, and the urban middle class that increasingly lives a UPI-first financial life.

### Why Now

- **Massive demand:** India's MSME credit gap is estimated at **₹30 lakh crore (~USD 530 billion)**, with only 14% of 64 million MSMEs having access to formal credit.
- **Infrastructure ready:** UPI now processes 13+ billion transactions monthly. The Account Aggregator framework, with 450+ financial institutions and 1.1+ billion cumulative consents, has reached production scale.
- **Regulatory tailwind:** The Government of India is actively evaluating AI-based credit scoring frameworks (Feb 2026 announcement). RBI has formalised cash-flow-based lending and Credit Line on UPI (CLOU).
- **Product-market fit signals:** Early CLOU deployments report NPA rates under 2% and customer acquisition costs at one-fifth of traditional credit cards.

### Vision

To make creditworthiness measurable for every Indian — not just those who have already borrowed.

### Mission

Build the most trusted, explainable, and inclusive alternative credit scoring engine in India, partnered with banks and NBFCs to extend formal credit to the hundreds of millions historically excluded by traditional bureaus.

---

## 2. Problem Statement

### 2.1 The Credit Paradox

India's traditional credit bureaus — TransUnion CIBIL, Experian, CRIF Highmark, and Equifax — were architected for a credit-heavy economy. They evaluate borrowers exclusively on past borrowing behaviour: loan repayments, credit card history, and credit utilisation ratios. The system implicitly says: "We only trust people who have already borrowed."

This produces a structural exclusion. Someone earning ₹50,000 per month with steady UPI inflows and zero defaults — but who has never taken a loan — is invisible. Meanwhile, someone with three settled defaults but a long credit history can still receive a score. The system penalises financial responsibility when that responsibility was expressed without using credit.

### 2.2 Quantifying the Excluded Population

| Segment | Approximate Size | Credit Status |
|---|---|---|
| MSMEs in India | 64 million | Only 14% have formal credit access |
| MSMEs without any formal credit | 27–29 million | Long tail of MSME credit demand |
| New-to-credit individuals (annual addition) | 0.6–0.8 million | Long approval timelines, frequent rejection |
| Microfinance borrowers | 78 million | Limited risk-sensitive pricing |
| UPI-active users | 400+ million | Rich digital footprint, often no credit file |
| Gig and platform workers | ~10+ million | Mostly thin-file or no-file |

### 2.3 What the Current System Measures vs. What It Should

| What CIBIL Measures Today | What Truly Predicts Repayment Capacity |
|---|---|
| Past borrowing behaviour | Overall financial health and stability |
| Repayment on credit products only | Income consistency and cash-flow patterns |
| Credit utilisation ratio | Savings discipline and balance trends |
| Loan mix (secured vs unsecured) | Spending patterns and recurring obligations |
| Credit history length | Digital engagement and transaction velocity |

### 2.4 Real-World Consequences

- MSMEs forced into informal lending channels at 24–36% annual interest rates.
- 13% of MSMEs denied credit purely due to inability to provide collateral or credit history.
- Women-led MSMEs face an addressable credit gap of 35% — the highest of any segment.
- Rural credit gap stands at 32% versus 20% in urban India.
- Salaried professionals who prefer debit and UPI cannot access competitive personal loan rates.

### 2.5 Why Existing Solutions Are Insufficient

While bank statement analysers (e.g. Perfios, FinBox) and Account Aggregator pipelines exist, they are infrastructure layers — not full scoring products. They give lenders raw data, but do not produce a standardised, comparable, explainable credit score that a borrower can carry across institutions. A small shopkeeper still cannot show a single, portable number that says, "I am creditworthy." FairCreditScore fills this gap.

---

## 3. Proposed Solution: FairCreditScore

### 3.1 Solution Overview

FairCreditScore is a cloud-hosted, API-first credit scoring platform with two interfaces: a borrower-facing web/mobile app and a lender-facing partner API. The core intelligence is FairCreditAI — a machine learning engine that ingests alternative data, computes a 0–900 credit score modelled on the CIBIL range, and returns a transparent explanation alongside loan eligibility and risk categorisation.

### 3.2 Core Components

#### 3.2.1 User Interface

A simple, intuitive web and mobile application designed for users with low digital literacy. Users provide minimal personal information (Name, Address, Mobile), upload identity proof (PAN or Aadhaar), and grant explicit, purpose-specific consent for the platform to fetch financial data via the Account Aggregator framework or direct API integrations.

#### 3.2.2 Data Sources (Alternative, Non-Traditional)

- **Employee payroll records** — particularly from blue-collar and gig employers.
- **UPI transaction data** — daily earnings, spending patterns, peer transfers, merchant payments.
- **Online purchase history** — Zomato, Swiggy, Amazon, Flipkart, BigBasket, etc.
- **Digital cashbook data** — entries maintained by small shopkeepers and vendors (Khatabook, OkCredit-style apps).
- **Bank account inflow / outflow data** — sourced via the Account Aggregator framework.
- **Utility bill payment history** — electricity, water, gas, mobile recharges (planned for v2).

#### 3.2.3 The FairCreditAI Engine

FairCreditAI uses a hybrid pipeline:

1. **Fetch Data** — verified, real-time data extraction via consented APIs.
2. **Data Pre-processing** — cleaning, validation, standardisation, and de-duplication.
3. **Feature Engineering** — transformation of raw transactions into meaningful indicators (income consistency, savings ratio, bounce rate, transaction velocity).
4. **Predictive Modelling** — ensemble of XGBoost and Random Forest classifiers to predict default probability and loan eligibility.
5. **Explainability Layer** — SHAP (SHapley Additive exPlanations) values to provide every borrower and lender with a clear breakdown of why a particular score was assigned.
6. **Storage** — persistence of features, model outputs, and decision artefacts for traceability, retraining, and regulatory audit.

#### 3.2.4 Human-in-the-Loop Oversight

Borderline scores and flagged edge cases are reviewed by trained credit analysts. Random samples of automated decisions are audited periodically to validate the model's fairness across demographics, geographies, and income segments — directly addressing emerging RBI and DPDP Act expectations on automated decision-making.

#### 3.2.5 Actionable Insights & Lender Distribution

FairCreditScore returns four artefacts to lender partners (banks, NBFCs, MFIs):

- Loan Approval Flag (approve / review / reject).
- Recommended Loan Amount.
- Risk-Based Interest Rate guidance.
- Plain-language Explanation of the decision (DPDP-compliant Right to Explanation).

### 3.3 Scoring Framework — Worked Example

FairCreditAI normalises each input feature to a 0–100 sub-score, applies weights tuned by the underlying ML model, and converts the weighted aggregate into a CIBIL-equivalent 300–900 range. An illustrative example:

| Parameter | Sub-score (0–100) | Weight | Contribution |
|---|---|---|---|
| Income Consistency | 80 | 0.25 | 20.00 |
| Expense / Income Ratio | 70 | 0.20 | 14.00 |
| Savings Ratio | 60 | 0.15 | 9.00 |
| Payment Timeliness | 90 | 0.15 | 13.50 |
| Transaction Frequency | 80 | 0.10 | 8.00 |
| Bounce Rate | 70 | 0.10 | 7.00 |
| Digital Engagement | 85 | 0.05 | 4.25 |
| **TOTAL (Alt Credit Score, 0–100)** | — | **1.00** | **75.75** |

Conversion to CIBIL-like range:

```
Final Credit Score = 300 + (75.75 × 6) = 754.5 ≈ 755
```

> Note: weights shown above are illustrative; production weights are learned from labelled repayment data and recalibrated quarterly.

### 3.4 Solution Architecture

The end-to-end flow connects three actors — the borrower (User Details), the FairCreditAI processing pipeline, and downstream financial institutions (SBI, ICICI, NBFCs, MFIs):

```
User → API Call (with consent) → Fetch Data → Pre-processing →
Feature Engineering → AI Engine (XGBoost / Random Forest + SHAP) →
Storage → Human-in-Loop Review → Actionable Insights → Lender Partner
```

The platform is cloud-hosted (with India data residency in line with RBI norms) and supports customised integration for different partners — banks, MFIs, NBFCs — via REST APIs and webhook callbacks.

---

## 4. Business Objectives & Success Metrics

### 4.1 Strategic Objectives

1. Bring 5 million credit-invisible Indians into the formal lending system within the first 36 months of operation.
2. Enable lender partners to approve loans to thin-file and no-file borrowers with delinquency rates comparable to or better than CIBIL-scored equivalents.
3. Achieve regulatory recognition as an RBI-licensed Credit Information Company (CIC) or equivalent licensed entity within 5 years.
4. Establish FairCreditScore as the default alternative score consulted by Indian fintechs and NBFCs by Year 4.

### 4.2 Key Performance Indicators (KPIs)

| KPI Category | Metric | Year 1 Target | Year 3 Target |
|---|---|---|---|
| User Acquisition | Registered borrowers (cumulative) | 100,000 | 5,000,000 |
| User Acquisition | Active monthly users | 30,000 | 1,500,000 |
| Lender Partnerships | NBFCs / MFIs onboarded | 5 | 75 |
| Lender Partnerships | Banks integrated | 1 | 12 |
| Loan Facilitation | Loans facilitated (cumulative ₹ crore) | 50 | 8,000 |
| Risk Performance | Portfolio NPA rate (lender-reported) | < 4.5% | < 2.5% |
| Model Performance | Score-to-default correlation (Gini) | > 0.55 | > 0.70 |
| Compliance | DPDP / RBI audit findings (critical) | 0 | 0 |
| Unit Economics | Cost per scored borrower (₹) | < 35 | < 8 |
| Revenue | ARR (₹ crore) | 1.5 | 120 |

---

## 5. Target Users & Personas

### 5.1 Primary User Segments

#### Persona 1: Ramesh — The Small Shopkeeper

Ramesh, 38, runs a kirana store in Indore. He earns roughly ₹70,000 per month, accepts 80% of payments via UPI QR code, and maintains a digital cashbook on Khatabook. He has never taken a formal loan. When he applies for a ₹3 lakh working capital loan to expand his shop, his bank rejects him for having no CIBIL score. He turns to a local moneylender at 30% annual interest. FairCreditScore would convert his three years of UPI inflows, vendor payments, and digital ledger entries into a credit score of approximately 740 — sufficient for a formal NBFC working capital loan at 16% interest.

#### Persona 2: Priya — The Salaried Debit-First Professional

Priya, 28, is a software engineer in Bangalore earning ₹14 lakh per year. She is debt-averse: no credit cards, no EMIs, all expenses on UPI and debit. When she applies for a home loan, her bank quotes the highest interest tier because she has a thin CIBIL file. FairCreditScore reads her salary credits, savings rate, and consistent rent payments to produce an alternative score of 790, qualifying her for the bank's prime borrower rate.

#### Persona 3: Anil — The Gig Worker

Anil, 32, is a Swiggy and Uber driver-partner in Hyderabad. His income is ₹40,000–55,000 per month, fully digital but irregular. Traditional lenders view irregular gig income as high-risk. FairCreditAI's transaction frequency and income consistency models can identify Anil's stable monthly earnings floor and qualify him for a vehicle upgrade loan.

#### Persona 4: Lakshmi — The Rural Self-Help Group Member

Lakshmi, 45, runs a tailoring business in rural Tamil Nadu. She receives orders on WhatsApp, takes UPI payments, and is part of a women's SHG. Conventional credit bureaus have nothing on her. FairCreditScore can use her UPI flow and SHG repayment history to produce an MFI-grade score for ticket sizes of ₹50,000–₹2 lakh.

### 5.2 Lender / Partner Personas

| Partner Type | Use Case | Typical Ticket Size |
|---|---|---|
| Public Sector Bank | Priority sector lending, MSME outreach | ₹2 lakh – ₹50 lakh |
| Private Bank | Personal loans, NTC customer acquisition | ₹50,000 – ₹15 lakh |
| NBFC / Digital Lender | Instant unsecured loans, BNPL underwriting | ₹5,000 – ₹5 lakh |
| Microfinance Institution | Joint Liability Group lending, women borrowers | ₹15,000 – ₹1.5 lakh |
| Small Finance Bank | Cash flow lending, gig-worker credit | ₹25,000 – ₹10 lakh |

---

## 6. Functional Requirements

### 6.1 Borrower-Facing Application

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | User registration with Mobile, Name, Address, and OTP-based verification. | Must |
| FR-1.2 | Identity verification via PAN and/or Aadhaar (DigiLocker integration). | Must |
| FR-1.3 | Explicit, purpose-specific, granular consent capture for each data source (UPI, payroll, e-commerce, AA). | Must |
| FR-1.4 | Account Aggregator integration for bank statement and financial data fetch. | Must |
| FR-1.5 | Real-time score computation and display to the borrower in plain language. | Must |
| FR-1.6 | Plain-language SHAP-based explanation of the score with top 3 positive and top 3 negative factors. | Must |
| FR-1.7 | Borrower dashboard: track score over time, see what improves it, set credit goals. | Should |
| FR-1.8 | Loan marketplace: browse pre-qualified offers from partner lenders. | Should |
| FR-1.9 | Right-to-Erasure flow per DPDP Act — full data deletion on request. | Must |
| FR-1.10 | Multi-language support (Hindi, English, Tamil, Telugu, Bengali, Marathi at launch). | Should |

### 6.2 Lender / Partner API

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | REST API to request a credit score given a consented user identifier. | Must |
| FR-2.2 | Webhook callbacks for score completion, re-scoring, and score expiry. | Must |
| FR-2.3 | Bulk scoring API for portfolio reviews and pre-approval campaigns. | Should |
| FR-2.4 | Risk band response (Low / Medium / High) plus numeric score and confidence interval. | Must |
| FR-2.5 | SHAP-based explanation payload returned with every score (for adverse-action notices). | Must |
| FR-2.6 | Lender admin portal — usage analytics, billing, audit logs, model version history. | Must |
| FR-2.7 | Sandbox environment with synthetic data for partner integration testing. | Must |
| FR-2.8 | Configurable scoring profiles per lender (e.g. women-led SHG profile, gig-worker profile). | Should |

### 6.3 FairCreditAI Engine

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Ingest data from at least UPI, payroll, e-commerce, digital cashbook, and AA sources. | Must |
| FR-3.2 | Feature engineering pipeline producing minimum 25 risk features per borrower. | Must |
| FR-3.3 | Ensemble model (XGBoost + Random Forest) for default probability prediction. | Must |
| FR-3.4 | SHAP-based explainability for every individual decision. | Must |
| FR-3.5 | Quarterly model retraining on new repayment outcome data. | Must |
| FR-3.6 | Bias and fairness monitoring across gender, geography, and income segments — published quarterly. | Must |
| FR-3.7 | Champion-challenger framework for safe model upgrades. | Should |
| FR-3.8 | Human-in-the-loop review queue for borderline scores and flagged anomalies. | Must |

### 6.4 Compliance & Operations

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | DPDP Act 2023 compliance: consent management, data minimisation, breach notification within 72 hours. | Must |
| FR-4.2 | RBI Digital Lending Guidelines 2026 alignment for all lender partner integrations. | Must |
| FR-4.3 | Data residency in India (compliant with RBI and emerging DPDP localisation expectations). | Must |
| FR-4.4 | Independent algorithmic audits performed annually; results published. | Must |
| FR-4.5 | Grievance redressal mechanism with 30-day SLA. | Must |
| FR-4.6 | Comprehensive audit trail for every score generated (regulator-accessible). | Must |

---

## 7. Non-Functional Requirements

| Category | Requirement |
|---|---|
| Performance | End-to-end score generation for a consented user must complete in under 8 seconds (P95). |
| Performance | API endpoint response time under 400 ms (P95) for cached scores. |
| Scalability | Architecture must support 10 million scored users and 50 million API calls per month by Year 3. |
| Availability | 99.9% uptime SLA for the partner API; 99.5% for the borrower-facing app. |
| Security | ISO 27001 and SOC 2 Type II certifications within 18 months of launch. |
| Security | PCI-DSS compliance for any cardholder data flows; AES-256 encryption at rest, TLS 1.3 in transit. |
| Privacy | DPDP Act 2023 compliance: granular consent, purpose limitation, data minimisation, deletion on demand. |
| Privacy | No selling, sharing, or monetisation of borrower data outside the explicit consented purpose. |
| Auditability | Full audit trail of every data fetch, model decision, and human override — retained per RBI norms. |
| Explainability | Every score returned with the top 3 contributing positive and negative factors in plain language. |
| Fairness | Quarterly bias audit across gender, age, region, income, and language segments; published transparency reports. |
| Localisation | App and explanations available in 6 Indian languages at launch; expanded to 12 by Year 2. |
| Resilience | Multi-region cloud deployment within India; RPO < 15 min, RTO < 2 hours. |

---

## 8. Scope

### 8.1 In Scope (Phase 1 — MVP, 0–6 months)

- Borrower-facing web and Android app with PAN/Aadhaar verification.
- Account Aggregator integration with two AA partners (e.g. Finvu, OneMoney).
- Direct UPI transaction ingestion via partner PSP relationships.
- Baseline FairCreditAI scoring model (XGBoost + Random Forest + SHAP).
- REST API and admin dashboard for two pilot lender partners.
- Hindi and English language support.
- Manual human-in-the-loop review for borderline cases.

### 8.2 In Scope (Phase 2 — 6–18 months)

- iOS app launch.
- Expanded AA coverage and PDF bank statement fallback (covering the 62% of borrowers not yet on AA).
- E-commerce purchase history integration (Amazon, Flipkart, Zomato, Swiggy via OAuth).
- Digital cashbook partnerships (Khatabook, OkCredit-equivalent).
- Loan marketplace inside the borrower app.
- Tamil, Telugu, Bengali, Marathi language support.
- Lender-specific scoring profiles (women-led SHG, gig-worker, MSME).

### 8.3 In Scope (Phase 3 — 18–36 months)

- Application for RBI Credit Information Company (CIC) licence or equivalent.
- Utility bill, telecom, and rent payment data integration.
- Embedded credit scoring SDK for e-commerce and gig platforms.
- GST and ITR data integration for MSME-grade scoring.
- Cross-border expansion exploration (UAE, Singapore — Indian diaspora corridor).

### 8.4 Out of Scope

- Direct lending — FairCreditScore is a scoring platform, not a lender. We do not hold loan books.
- Replacement of CIBIL, Experian, CRIF, or Equifax — we are complementary, not a substitute.
- Credit card issuance, debt collection, or insurance underwriting.
- Use of social-media or behavioural device data (contacts, SMS, location) — explicitly avoided per RBI 2026 norms.

---

## 9. Regulatory & Compliance Framework

FairCreditScore operates within India's evolving fintech regulatory landscape. Our compliance posture is proactive — we aim to exceed minimum requirements, not merely meet them, because trust is our strongest moat.

### 9.1 Applicable Regulations

| Regulation | Relevance to FairCreditScore |
|---|---|
| RBI Digital Lending Guidelines 2022 / 2026 updates | Governs every lender partnership; mandates Key Fact Statement, no contact-list scraping, 30-day grievance redressal, India data storage. |
| Digital Personal Data Protection (DPDP) Act 2023 | Consent-based data processing, right to erasure, right to explanation for automated decisions, 72-hour breach notification, ₹250 crore penalty cap. |
| RBI Account Aggregator Master Direction (2021) | Foundational rail for our data ingestion — we register as a Financial Information User (FIU) via a sponsoring NBFC partner. |
| RBI Credit Information Companies (Regulation) Act 2005 | Pathway for FairCreditScore to eventually operate as a licensed CIC, or to partner with an existing one. |
| RBI Outsourcing of IT Services Directions 2023 | Governs our cloud infrastructure choices and vendor contracts. |
| KYC Directions (RBI) | Five-year retention requirement — reconciled with DPDP minimisation via explicit purpose definition. |

### 9.2 Compliance Roadmap

- **Year 0–1:** Operate as a Lending Service Provider (LSP) anchored to RBI-licensed NBFC partners. Register as an FIU under the AA framework. Achieve ISO 27001 certification.
- **Year 1–2:** SOC 2 Type II certification, DPDP Significant Data Fiduciary readiness, annual independent algorithmic bias audits.
- **Year 2–4:** Pursue RBI CIC licence or equivalent; expand to all four regulators (RBI, SEBI, IRDAI, PFRDA) for AA data access where applicable.

### 9.3 Risk-of-Explanation Posture

Recent academic and policy literature on automated decision-making in Indian credit (ICSLIAI 2026 proceedings) calls for verifiable output accountability for algorithmic decisions. FairCreditAI is built explainability-first: SHAP outputs are returned with every score, every adverse action triggers an automatic plain-language explanation, and the model is subjected to independent annual audits. This positions us favourably for any future RBI or DPDP Board enforcement around AI fairness.

---

## 10. Indicative Technical Stack

| Layer | Technology Choices |
|---|---|
| Frontend (web) | React, TypeScript, Tailwind CSS |
| Mobile | React Native (Android-first, iOS Phase 2) |
| Backend services | Python (FastAPI) for ML inference, Node.js (NestJS) for transactional APIs |
| Data ingestion | Account Aggregator FIU SDK; PSP partner APIs for UPI; OAuth integrations for e-commerce |
| ML platform | scikit-learn, XGBoost, LightGBM, SHAP, MLflow for model registry |
| Data storage | PostgreSQL (transactional), ClickHouse (analytical), S3-compatible object store (raw events) |
| Cloud | AWS Mumbai (ap-south-1) and Hyderabad (ap-south-2) — multi-AZ, India data residency |
| Identity / KYC | DigiLocker, NSDL PAN verification, UIDAI Aadhaar OKYC via licensed KUA/AUA partner |
| Observability | OpenTelemetry, Prometheus, Grafana, Sentry |
| Security | HashiCorp Vault for secrets, AWS KMS for encryption keys, AWS WAF + Shield |

---

## 11. Business Model & Revenue

### 11.1 Revenue Streams

| Stream | Description | Indicative Pricing |
|---|---|---|
| Per-Score API | Charge lender partners per score generated. | ₹15–₹40 per score (volume tiered) |
| Subscription Plans | Monthly fixed plans for high-volume NBFCs and banks. | ₹2L – ₹15L / month |
| Premium Insights | Advanced portfolio analytics, custom segmentation, alerts. | ₹50,000+ / month per lender |
| Borrower-side Freemium | Free score for borrowers; premium credit-improvement coaching, dispute support. | ₹99 – ₹299 / month |
| Marketplace Take-rate | Commission on loans originated through the borrower-app marketplace. | 0.5% – 1.25% of loan amount |
| Embedded SDK | White-label scoring SDK for e-commerce and gig platforms. | Custom enterprise contracts |

### 11.2 Unit Economics (Steady State, Year 3)

- Average revenue per scored borrower per year: **₹85**
- Cost per scored borrower (data + infra + ops): **₹8–10**
- Gross margin on per-score revenue: **~88%**
- CAC payback period: **4–6 months** on the lender side; **<1 month** on the borrower side via partnerships.

---

## 12. Risks & Mitigations

| Risk Category | Risk | Mitigation |
|---|---|---|
| Regulatory | RBI tightens norms on alternative-data scoring or restricts non-CIC scoring. | Operate as LSP with NBFC anchor in Phase 1; pursue CIC licence by Year 4; engage proactively with RBI Regulatory Sandbox. |
| Data Access | AA framework covers only ~38% of borrowers (Dec 2025); cooperative banks and RRBs lag. | Hybrid approach — AA-first for instant fetch, PDF bank statement fallback for the other 62%. |
| Privacy | DPDP Act non-compliance penalty up to ₹250 crore; reputational damage. | Privacy-by-design architecture; appointed DPO; quarterly DPIAs; encrypted data fiduciary infrastructure. |
| Model Bias | Algorithmic bias against women, rural, or specific linguistic groups exposes us to litigation and regulatory action. | Quarterly fairness audits; independent annual algorithmic audit; published transparency reports; human-in-the-loop overrides. |
| Fraud | Synthetic UPI transactions and gamed digital footprints to manipulate scores. | Velocity checks, network-graph fraud detection, cross-source consistency validation, behavioural anomaly models. |
| Competitive | Established credit bureaus (CIBIL, Experian) launch their own alternative-data products. | Build defensible explainability moat, lender-friendly APIs, and borrower-side brand trust before incumbents move. |
| Adoption | Lenders sceptical of accepting an unproven score for underwriting decisions. | Co-lending pilots with risk-sharing; champion-challenger pilots vs CIBIL on the same applicant pool; published Gini and KS performance. |
| Macroeconomic | Credit stress cycle increases NPAs, lenders pull back on alternative scoring. | Counter-cyclical messaging — alternative data is more predictive in stress periods; diversified lender base across PSU, private, NBFC, MFI. |

---

## 13. Implementation Roadmap

| Phase | Timeline | Key Deliverables |
|---|---|---|
| **Phase 0 — Foundation** | Months 0–3 | Team hiring, NBFC anchor partnership, AA FIU registration, ISO 27001 kickoff. |
| **Phase 1 — MVP Launch** | Months 3–6 | Borrower Android app, lender API, baseline FairCreditAI model, 2 pilot NBFC partners, Hindi + English. |
| **Phase 2 — Scale** | Months 6–18 | iOS, e-commerce + cashbook integrations, 25 lender partners, 6 languages, loan marketplace, SOC 2. |
| **Phase 3 — Deepen** | Months 18–36 | GST + ITR for MSMEs, embedded SDK, 75+ lenders, RBI CIC application, 5M+ scored borrowers. |
| **Phase 4 — Expansion** | Year 3+ | Cross-border (UAE, SG), pension and insurance scoring, white-label exports. |

---

## 14. Assumptions & Dependencies

### 14.1 Key Assumptions

- UPI transaction volumes continue to grow (currently 13B+ per month) and digital payment adoption deepens in Tier 2/3 cities.
- Account Aggregator coverage expands beyond the current ~38% of borrowers to 60%+ within 24 months.
- RBI maintains its supportive stance toward alternative-data scoring and cash-flow lending.
- DPDP Act enforcement focuses on bad actors, not on good-faith compliant fintechs.
- Lender partners are willing to run controlled pilots comparing FairCreditScore against CIBIL on shared applicant pools.

### 14.2 External Dependencies

- Anchor NBFC partner (required for FIU registration in Phase 1).
- Account Aggregator licensee partnerships (Finvu, OneMoney, NeSL, Setu, etc.).
- PSP partnerships for UPI transaction-level data access (subject to NPCI approval pathways).
- Cloud infrastructure (AWS Mumbai region, India residency).
- KYC service providers for PAN, Aadhaar OKYC, and DigiLocker.

---

## 15. Appendices

### Appendix A — Glossary

| Term | Definition |
|---|---|
| AA (Account Aggregator) | RBI-regulated NBFC framework that lets a user share consented financial data across institutions. |
| CIC | Credit Information Company — RBI-licensed entity (e.g. CIBIL, CRIF, Experian, Equifax). |
| DPDP Act | Digital Personal Data Protection Act, 2023 — India's omnibus data protection law. |
| FIU / FIP | Financial Information User / Provider — roles in the AA framework. |
| KFS | Key Fact Statement — mandatory disclosure document per RBI Digital Lending Guidelines. |
| LSP | Lending Service Provider — fintech operating on top of an RBI-licensed Regulated Entity. |
| NTC | New-to-Credit — borrower with no prior credit history. |
| SHAP | SHapley Additive exPlanations — leading method for ML model explainability. |
| NPA | Non-Performing Asset — loan where principal or interest is overdue beyond 90 days. |
| CLOU | Credit Line on UPI — RBI-permitted product allowing pre-sanctioned credit lines accessible via UPI. |

### Appendix B — Key Sources & Evidence

- RBI Financial Stability Report (June 2025); CRIF High Mark microfinance industry data.
- SIDBI–CRISIL MSME report (May 2025): MSME credit gap of ₹30 lakh crore.
- NITI Aayog: Enhancing Competitiveness of MSMEs in India (2025).
- EY: Recent UPI Changes and India's Credit Gap; PwC: Rise of Alternative Lending in India.
- Atlantis Press, ICSLIAI 2026: Automated Decision-Making in Indian Credit Scoring under DPDP and RBI.
- IBS Intelligence: Credit Line on UPI ecosystem analysis (Dec 2025).
- Business Standard (Feb 2026): Government weighs AI-based credit scores for formal finance access.

---

*— End of Document —*
