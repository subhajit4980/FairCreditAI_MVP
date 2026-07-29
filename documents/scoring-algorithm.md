# FairCreditScore — Scoring Algorithm

This document explains how the FairCreditScore is computed. It captures both
the **canonical algorithm** as specified by the product owner in
`documents/fairCreditAI-business-idea1.jpeg`, and the **current implementation**
in `core/scoring.py` as of this commit.

> **Honesty note.** The first version of `core/scoring.py` was written before
> the canonical algorithm sheet was reviewed. It uses the same seven features
> the BRD names, but the weights and the 0–100 → 300–900 conversion do **not**
> match the JPEG. Section 4 below lists the gap and the planned fix.

---

## 1. Inputs — the seven features

Both the canonical algorithm and the current implementation use the same seven
parameters drawn from a borrower's UPI / bank-statement footprint. Each is
normalised to a 0–100 sub-score before weighting.

| # | Feature | What it measures |
|---|---|---|
| 1 | **Income Consistency** | How regular and stable the inflows are month-on-month |
| 2 | **Expense / Income Ratio** | How much of monthly income leaves the account as expense |
| 3 | **Savings Ratio** | Net residual after expense, as a share of income |
| 4 | **Payment Timeliness** | On-time payment rate for recurring bills, EMIs, mandates |
| 5 | **Transaction Frequency** | Volume of monthly UPI / bank transactions |
| 6 | **Bounce Rate** | Cheque, NACH and mandate bounce rate |
| 7 | **Digital Engagement** | Breadth of digital footprint (UPI counterparties, merchant mix, recurring digital activity) |

---

## 2. Canonical algorithm (per `fairCreditAI-business-idea1.jpeg`)

### Step 1 — Normalise each parameter to 0–100
The example values from the sheet:

| Parameter | Normalised value (0–100) |
|---|---|
| Income Consistency | 80 |
| Expense / Income Ratio | 70 |
| Savings Ratio | 60 |
| Payment Timeliness | 90 |
| Transaction Frequency | 80 |
| Bounce Rate | 70 |
| Digital Engagement | 85 |

### Step 2 — Weighted alt credit score (0–100)

```
AltCreditScore = (IncomeConsistency       × 0.25)
               + (ExpenseIncomeRatio      × 0.20)
               + (SavingsRatio            × 0.15)
               + (PaymentTimeliness       × 0.15)
               + (TransactionFrequency    × 0.10)
               + (BounceRate              × 0.10)
               + (DigitalEngagement       × 0.05)
```

Weight table:

| Parameter | Weight |
|---|---|
| Income Consistency | 0.25 |
| Expense / Income Ratio | 0.20 |
| Savings Ratio | 0.15 |
| Payment Timeliness | 0.15 |
| Transaction Frequency | 0.10 |
| Bounce Rate | 0.10 |
| Digital Engagement | 0.05 |
| **Total** | **1.00** |

Worked example from the sheet:

```
AltCreditScore = (80 × 0.25) + (70 × 0.20) + (60 × 0.15)
               + (90 × 0.15) + (80 × 0.10) + (70 × 0.10) + (85 × 0.05)
             =  20 + 14 + 9 + 13.5 + 8 + 7 + 4.25
             =  75.75
```

### Step 3 — Convert to a CIBIL-like 300–900 range

```
FairCreditScore = 300 + (AltCreditScore × 6)
```

Worked example:

```
FairCreditScore = 300 + (75.75 × 6)
               = 300 + 454.5
               = 754.5  →  ~755
```

### Properties of the canonical formula
- Bounded between `300` (when AltCreditScore = 0) and `900` (when AltCreditScore = 100).
- Linear: a 1-point gain on the 0–100 alt score is exactly +6 points on the
  CIBIL-like score.
- The seven weights sum to 1.0, so the alt score is a clean weighted average.

---

## 3. Current implementation (`core/scoring.py`, today)

The current code path is in `core/scoring.py::generate_score(customer)`:

1. Generate seven pseudo-random feature values seeded by the user id (so the
   same user always gets the same baseline). All seven are stored as 0–1
   floats (not 0–100).
2. Combine the features into a 300–900 score with the following ad-hoc
   formula:

   ```python
   base = 540
   base += int(income_consistency        * 120)   # max +120
   base += int((1 - expense_ratio)       *  80)   # max +80, expense penalised
   base += int(savings_ratio             * 120)   # max +120
   base += int(payment_timeliness        * 100)   # max +100
   base += min(60, int(transaction_frequency / 3))# capped at +60
   base -= int(bounce_rate               * 600)   # bounce penalised heavily
   base += int(digital_engagement        *  60)   # max +60
   ```

3. Apply non-feature bonuses:
   - `+35` if the customer has an active AA consent on file.
   - `+10` per verified document, capped at `+30`.
   - `+15` if the profile (monthly income) is filled in.
4. Clamp to `[300, 900]`.
5. Map the numeric score to a band:

   | Range | Band |
   |---|---|
   | 800 – 900 | Excellent |
   | 740 – 799 | Very Good |
   | 670 – 739 | Good |
   | 580 – 669 | Fair |
   | 300 – 579 | Poor |

6. Build SHAP-style top-positive / top-negative factor lists using simple
   thresholds (e.g. `income_consistency >= 0.8 → "+45 pts"` positive). These
   labels are illustrative, not the literal partial-derivative attributions
   that a real SHAP run would return.
7. Recommend an indicative loan amount based on the band:

   | Band | Indicative loan amount |
   |---|---|
   | Excellent | ₹15,00,000 |
   | Very Good | ₹8,00,000 |
   | Good | ₹3,50,000 |
   | Fair | ₹1,00,000 |
   | Poor | ₹0 |

### Why this is *not* the canonical algorithm
- Weights are implicit in the integer multipliers (120, 80, 120, 100, …) and
  do **not** match `[0.25, 0.20, 0.15, 0.15, 0.10, 0.10, 0.05]`.
- It does **not** use the linear `300 + (alt × 6)` mapping; it has a base of
  540 and adds offsets directly into the 300–900 space.
- It adds extra bumps for AA consent / verified documents / profile
  completeness that the canonical formula does not contain.
- Bounce rate is *negatively* signed in the current code, while the canonical
  algorithm normalises bounce rate to a 0–100 sub-score (where 100 = no
  bounces) and adds it positively.

### Why the current code exists
- The first build pass needed *something* that produced believable end-to-end
  scores so the consent → score → display flow could be wired up before the
  canonical formula was reviewed against the JPEG.
- It is deterministic per user id, so the four seeded personas (Ramesh,
  Priya, Anil, Lakshmi) always show the same number across sessions.

---

## 4. Gap analysis and the next change

To bring `core/scoring.py` in line with the canonical algorithm:

1. Switch the seven features from 0–1 floats to 0–100 sub-scores. Either keep
   the synthetic generator and scale, or compute them from real AA data once
   that path is live.
2. Replace the ad-hoc combination with the exact weighted sum from the JPEG:

   ```python
   alt = (
       0.25 * income_consistency
       + 0.20 * expense_income_ratio_subscore
       + 0.15 * savings_ratio
       + 0.15 * payment_timeliness
       + 0.10 * transaction_frequency
       + 0.10 * bounce_rate_subscore
       + 0.05 * digital_engagement
   )
   credit_score = round(300 + alt * 6)
   ```

   Note that `expense_income_ratio_subscore` and `bounce_rate_subscore` are
   the *normalised* versions where 100 means the ideal (low expense ratio,
   zero bounces). The JPEG implies this by listing both as straight 0–100
   values (70 each in the example).
3. Move the AA-consent / verified-docs / profile-completeness bonuses out of
   the score itself. They belong as *eligibility gates* (you need an active
   consent and a verified PAN to be scored at all) rather than as score
   inflators that double-count signals already in the seven features.
4. Replace the threshold-based factor labels with real SHAP attributions once
   the model moves from synthetic to trained (Week 4 of the build guide).

Until that change lands, treat the score numbers shown in the prototype as
indicative of the *flow* — not as the canonical FairCreditScore.

---

## 5. Pseudocode of the canonical algorithm (for reference)

```python
def fair_credit_score(features: dict[str, float]) -> int:
    """features: each value is a 0-100 normalised sub-score."""
    weights = {
        "income_consistency":     0.25,
        "expense_income_ratio":   0.20,
        "savings_ratio":          0.15,
        "payment_timeliness":     0.15,
        "transaction_frequency":  0.10,
        "bounce_rate":            0.10,
        "digital_engagement":     0.05,
    }
    alt = sum(features[k] * w for k, w in weights.items())   # 0..100
    return round(300 + alt * 6)                              # 300..900
```

---

*Source: `documents/fairCreditAI-business-idea1.jpeg` (canonical algorithm),
`core/scoring.py` (current implementation), `documents/FairCreditScore_BRD-v4.md`
and `documents/FairCreditScore_Prototype_Build_Guide-v4.md` (feature list and
ranges).*
