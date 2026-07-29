"""FairCreditAI scoring engine.

Three algorithms are supported and selectable per request:

- ``baseline``  — the ad-hoc formula written for the first prototype build.
  Useful as a smoke-test path while real data is wired up; not the spec.
- ``canonical`` — the algorithm specified in
  ``documents/fairCreditAI-business-idea1.jpeg``: seven 0–100 sub-scores,
  weights summing to 1.0, ``FairCreditScore = 300 + (alt × 6)``.
- ``ai_model``  — a pure-Python port of the team's alternative-data model in
  ``fairCreditAiModel/AI_Credit_Score.ipynb``. It reproduces that notebook's
  composite 1–100 score, Grade A–E, risk type, underwriting decision and
  pricing-matrix loan sizing. The notebook's probability-of-default and fraud
  probabilities come from trained ``.joblib`` pipelines; to keep the Heroku
  slug free of scikit-learn/pandas we derive them here from transparent
  heuristics over the same cashflow features. These are proxies, not the
  trained-model outputs — see ``_pd_proxy`` / ``_fraud_proxy`` below.

See ``scoring-algorithm.md`` at the repo root for the full write-up.
"""

import hashlib
import random

from .models import AAConsent, BankStatement, Document, ScoreReport


# Public algorithm identifiers — kept in sync with ScoreReport.Algorithm.
BASELINE = "baseline"
CANONICAL = "canonical"
AI_MODEL = "ai_model"
ALGORITHMS = (AI_MODEL,)

# Canonical weights (must sum to 1.0). Source: business-idea1.jpeg.
CANONICAL_WEIGHTS = {
    "income_consistency":    0.25,
    "expense_income_ratio":  0.20,
    "savings_ratio":         0.15,
    "payment_timeliness":    0.15,
    "transaction_frequency": 0.10,
    "bounce_rate":           0.10,
    "digital_engagement":    0.05,
}

# Human-friendly labels for the seven features (used in factor lists).
FEATURE_LABELS = {
    "income_consistency":    "Income consistency",
    "expense_income_ratio":  "Expense / income ratio",
    "savings_ratio":         "Savings ratio",
    "payment_timeliness":    "Payment timeliness",
    "transaction_frequency": "Transaction frequency",
    "bounce_rate":           "Bounce rate (low is good)",
    "digital_engagement":    "Digital engagement",
}


def _seeded_random(user_id: int) -> random.Random:
    seed = int(hashlib.sha256(str(user_id).encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _band_for(score: int) -> str:
    if score >= 800:
        return ScoreReport.Band.EXCELLENT
    if score >= 740:
        return ScoreReport.Band.VERY_GOOD
    if score >= 670:
        return ScoreReport.Band.GOOD
    if score >= 580:
        return ScoreReport.Band.FAIR
    return ScoreReport.Band.POOR


def _recommended_loan(score: int) -> int:
    if score >= 800:
        return 1_500_000
    if score >= 740:
        return 800_000
    if score >= 670:
        return 350_000
    if score >= 580:
        return 100_000
    return 0


def _generate_features(customer):
    """Synthetic features stored on the report (0..1 floats / counts)."""
    rng = _seeded_random(customer.id)
    
    income_consistency = round(rng.uniform(0.55, 0.95), 2)
    expense_ratio = round(rng.uniform(0.35, 0.75), 2)
    savings_ratio = round(rng.uniform(0.05, 0.40), 2)
    payment_timeliness = round(rng.uniform(0.60, 0.99), 2)
    transaction_frequency = round(rng.uniform(20, 180), 1)
    bounce_rate = round(rng.uniform(0, 0.08), 3)
    digital_engagement = round(rng.uniform(0.30, 0.95), 2)
    
    # Advanced features
    average_monthly_income = round(rng.uniform(20000, 120000), 2)
    average_monthly_expense = average_monthly_income * expense_ratio
    monthly_savings = average_monthly_income - average_monthly_expense
    
    total_income = average_monthly_income * 6.0
    total_expense = average_monthly_expense * 6.0
    
    average_transaction_amount = round(rng.uniform(200, 5000), 2)
    median_transaction_amount = average_transaction_amount * round(rng.uniform(0.5, 0.9), 2)
    largest_deposit = round(rng.uniform(10000, 50000), 2)
    largest_withdrawal = round(rng.uniform(5000, 25000), 2)
    
    average_balance = round(rng.uniform(5000, 75000), 2)
    minimum_balance = round(rng.uniform(100, 5000), 2)
    maximum_balance = average_balance * 2.0
    balance_variance = (average_balance * 0.4) ** 2
    
    transaction_consistency = round(rng.uniform(0.5, 0.9), 4)
    expense_stability = round(rng.uniform(0.6, 0.95), 4)
    income_stability_index = round(income_consistency * 0.6 + expense_stability * 0.4, 4)
    financial_buffer = round(minimum_balance / (average_monthly_expense + 1), 4)
    
    essential_expense = total_expense * round(rng.uniform(0.2, 0.5), 2)
    discretionary_expense = total_expense * round(rng.uniform(0.2, 0.4), 2)
    atm_withdrawals = total_expense * (1.0 - digital_engagement)
    emi_payments = total_expense * round(rng.uniform(0.0, 0.15), 2)
    investment_amount = total_income * round(rng.uniform(0.0, 0.1), 2)
    salary_credits = total_income * round(rng.uniform(0.7, 1.0), 2)
    
    essential_expense_ratio = round(essential_expense / (total_expense + 1), 4)
    discretionary_expense_ratio = round(discretionary_expense / (total_expense + 1), 4)
    atm_cash_ratio = round(atm_withdrawals / (total_expense + 1), 4)
    investment_ratio = round(investment_amount / (total_income + 1), 4)
    salary_ratio = round(salary_credits / (total_income + 1), 4)

    monthly_trends = []
    months = ["Jan 2026", "Feb 2026", "Mar 2026", "Apr 2026", "May 2026", "Jun 2026"]
    for m in months:
        credits = round(average_monthly_income * rng.uniform(0.85, 1.15), 2)
        debits = round(credits * expense_ratio * rng.uniform(0.9, 1.1), 2)
        monthly_trends.append({"month": m, "credit": credits, "debit": debits})

    return {
        "monthly_trends": monthly_trends,
        "income_consistency": income_consistency,
        "expense_ratio": expense_ratio,
        "savings_ratio": savings_ratio,
        "payment_timeliness": payment_timeliness,
        "transaction_frequency": transaction_frequency,
        "bounce_rate": bounce_rate,
        "digital_engagement": digital_engagement,
        
        "average_monthly_income": average_monthly_income,
        "average_monthly_expense": average_monthly_expense,
        "monthly_savings": monthly_savings,
        "total_income": total_income,
        "total_expense": total_expense,
        "average_transaction_amount": average_transaction_amount,
        "median_transaction_amount": median_transaction_amount,
        "largest_deposit": largest_deposit,
        "largest_withdrawal": largest_withdrawal,
        "average_balance": average_balance,
        "minimum_balance": minimum_balance,
        "maximum_balance": maximum_balance,
        "balance_variance": balance_variance,
        "transaction_consistency": transaction_consistency,
        "expense_stability": expense_stability,
        "income_stability_index": income_stability_index,
        "financial_buffer": financial_buffer,
        
        "essential_expense": essential_expense,
        "discretionary_expense": discretionary_expense,
        "atm_withdrawals": atm_withdrawals,
        "emi_payments": emi_payments,
        "investment_amount": investment_amount,
        "salary_credits": salary_credits,
        "essential_expense_ratio": essential_expense_ratio,
        "discretionary_expense_ratio": discretionary_expense_ratio,
        "atm_cash_ratio": atm_cash_ratio,
        "investment_ratio": investment_ratio,
        "salary_ratio": salary_ratio,
    }



# ---------------------------------------------------------------------------
# Baseline algorithm (the original prototype formula).
# ---------------------------------------------------------------------------

def _score_baseline(features, *, has_active_consent, verified_docs, profile_complete):
    base = 540
    base += int(features["income_consistency"] * 120)
    base += int((1 - features["expense_ratio"]) * 80)
    base += int(features["savings_ratio"] * 120)
    base += int(features["payment_timeliness"] * 100)
    base += min(60, int(features["transaction_frequency"] / 3))
    base -= int(features["bounce_rate"] * 600)
    base += int(features["digital_engagement"] * 60)

    if has_active_consent:
        base += 35
    base += min(30, verified_docs * 10)
    if profile_complete:
        base += 15

    score = max(300, min(900, base))

    positives, negatives = [], []
    if features["income_consistency"] >= 0.8:
        positives.append({"factor": "Strong, consistent income inflows", "impact": "+45 pts"})
    elif features["income_consistency"] < 0.65:
        negatives.append({"factor": "Irregular income pattern", "impact": "-30 pts"})

    if features["savings_ratio"] >= 0.2:
        positives.append({"factor": "Healthy savings ratio", "impact": "+40 pts"})
    elif features["savings_ratio"] < 0.1:
        negatives.append({"factor": "Low savings ratio", "impact": "-25 pts"})

    if features["payment_timeliness"] >= 0.9:
        positives.append({"factor": "Excellent bill payment timeliness", "impact": "+35 pts"})
    elif features["payment_timeliness"] < 0.75:
        negatives.append({"factor": "Occasional late payments", "impact": "-20 pts"})

    if features["bounce_rate"] <= 0.01:
        positives.append({"factor": "Near-zero cheque/mandate bounces", "impact": "+25 pts"})
    elif features["bounce_rate"] > 0.04:
        negatives.append({"factor": "Elevated bounce rate", "impact": "-35 pts"})

    if features["digital_engagement"] >= 0.7:
        positives.append({"factor": "Strong digital footprint (UPI activity)", "impact": "+20 pts"})

    if not has_active_consent:
        negatives.append({"factor": "No Account Aggregator consent on file", "impact": "-35 pts"})
    if verified_docs == 0:
        negatives.append({"factor": "Identity documents not yet verified", "impact": "-20 pts"})

    return score, positives[:4], negatives[:4]


# ---------------------------------------------------------------------------
# Canonical algorithm (from documents/fairCreditAI-business-idea1.jpeg).
# ---------------------------------------------------------------------------

def _to_subscores(features):
    """Project the synthetic feature values onto the 0..100 sub-score scale.

    Each sub-score is oriented so 100 = ideal. ``expense_income_ratio`` and
    ``bounce_rate`` are inverted because lower raw values are better.
    """
    return {
        "income_consistency":    max(0.0, min(100.0, features["income_consistency"] * 100)),
        # Expense ratio: 0 expense → 100, 1.0 expense → 0.
        "expense_income_ratio":  max(0.0, min(100.0, (1 - features["expense_ratio"]) * 100)),
        # Savings ratio: 0.40 (40%) treated as ideal → 100.
        "savings_ratio":         max(0.0, min(100.0, features["savings_ratio"] * 250)),
        "payment_timeliness":    max(0.0, min(100.0, features["payment_timeliness"] * 100)),
        # Transaction frequency: 100+ transactions/month is the ceiling.
        "transaction_frequency": max(0.0, min(100.0, features["transaction_frequency"])),
        # Bounce rate: 0 bounces → 100, 10% → 0.
        "bounce_rate":           max(0.0, min(100.0, 100 - features["bounce_rate"] * 1000)),
        "digital_engagement":    max(0.0, min(100.0, features["digital_engagement"] * 100)),
    }


def _score_canonical(features):
    sub = _to_subscores(features)
    alt = sum(sub[k] * w for k, w in CANONICAL_WEIGHTS.items())  # 0..100
    score = round(300 + alt * 6)
    score = max(300, min(900, score))

    # SHAP-style attributions: each feature's contribution in CIBIL points is
    # ``subscore * weight * 6``. For "what hurt" we surface the points that
    # were *missed* relative to a perfect 100 sub-score.
    contributions = []
    for key, weight in CANONICAL_WEIGHTS.items():
        gained = sub[key] * weight * 6
        missed = (100 - sub[key]) * weight * 6
        contributions.append((key, sub[key], gained, missed))

    pos_sorted = sorted(contributions, key=lambda r: r[2], reverse=True)
    neg_sorted = sorted(contributions, key=lambda r: r[3], reverse=True)

    positives = [
        {
            "factor": f"{FEATURE_LABELS[key]} (sub-score {sub_val:.0f}/100)",
            "impact": f"+{gained:.0f} pts",
        }
        for (key, sub_val, gained, _missed) in pos_sorted[:3]
        if gained >= 5
    ]
    negatives = [
        {
            "factor": f"{FEATURE_LABELS[key]} below target ({sub_val:.0f}/100)",
            "impact": f"-{missed:.0f} pts",
        }
        for (key, sub_val, _gained, missed) in neg_sorted[:3]
        if missed >= 5
    ]
    return score, positives, negatives


# ---------------------------------------------------------------------------
# AI model algorithm (pure-Python port of fairCreditAiModel/AI_Credit_Score).
# ---------------------------------------------------------------------------

# PD -> regulatory grade bounds (from the notebook's GRADE_BOUNDS).
AI_GRADE_BOUNDS = (
    (0.15, "Grade A"),
    (0.30, "Grade B"),
    (0.50, "Grade C"),
    (0.70, "Grade D"),
)  # PD above the last bound -> "Grade E".

# Pricing matrix by grade: base annual interest rate + monthly-income multiplier
# used to size the sanctioned limit (from the notebook's pricing_matrix).
AI_PRICING_MATRIX = {
    "Grade A": {"base_rate": 0.105, "multiplier": 8.0},
    "Grade B": {"base_rate": 0.120, "multiplier": 6.0},
    "Grade C": {"base_rate": 0.145, "multiplier": 4.0},
    "Grade D": {"base_rate": 0.180, "multiplier": 2.0},
    "Grade E": {"base_rate": 0.240, "multiplier": 1.0},
}

# Grade -> coarse risk type surfaced to the UI (issue #12: Low / Medium / High).
AI_RISK_TYPE = {
    "Grade A": "Low",
    "Grade B": "Low",
    "Grade C": "Medium",
    "Grade D": "High",
    "Grade E": "High",
}

# Default monthly income (INR) when the profile has none, mirroring the
# notebook's ``row.get('average_monthly_income', 30000)`` fallback.
AI_DEFAULT_MONTHLY_INCOME = 30000


def _clamp(value, low, high):
    return max(low, min(high, value))


def _pd_proxy(features):
    """Heuristic probability-of-default in ``[0.02, 0.98]``.

    Stands in for ``credit_model.predict_proba`` (which needs the trained
    ``.joblib`` pipeline). Higher expense ratio, less consistent income, thin
    savings, late payments and bounces all push PD up. Weights over the first
    four terms sum to 0.90 with a 0.10 bounce term on top.
    """
    savings_norm = _clamp(features["savings_ratio"] / 0.40, 0.0, 1.0)
    pd_raw = (
        0.35 * features["expense_ratio"]
        + 0.25 * (1 - features["income_consistency"])
        + 0.20 * (1 - savings_norm)
        + 0.10 * (1 - features["payment_timeliness"])
        + 0.10 * _clamp(features["bounce_rate"] * 5, 0.0, 1.0)
    )
    return _clamp(pd_raw, 0.02, 0.98)


def _fraud_proxy(features):
    """Heuristic fraud probability in ``[0.01, 0.95]``.

    Stands in for ``fraud_model.predict_proba``. A weak digital footprint
    (cash-heavy behaviour) and elevated bounces raise suspicion; fraud stays
    low for the typical clean profile.
    """
    fraud_raw = (
        0.04
        + 0.10 * (1 - features["digital_engagement"])
        + 0.10 * _clamp(features["bounce_rate"] * 5, 0.0, 1.0)
    )
    return _clamp(fraud_raw, 0.01, 0.95)


def _ai_grade(pd_prob):
    for bound, grade in AI_GRADE_BOUNDS:
        if pd_prob <= bound:
            return grade
    return "Grade E"


def _ai_band(score):
    """Map the 0–100 AI score onto the shared five-band scale."""
    if score >= 80:
        return ScoreReport.Band.EXCELLENT
    if score >= 65:
        return ScoreReport.Band.VERY_GOOD
    if score >= 50:
        return ScoreReport.Band.GOOD
    if score >= 35:
        return ScoreReport.Band.FAIR
    return ScoreReport.Band.POOR


def _score_ai_model(features, customer):
    """Port of the notebook's underwriting + composite scoring engine.

    Returns ``(score, positives, negatives, recommended_loan, assessment)``
    where ``assessment`` is the full report dict persisted on the ScoreReport.
    """
    from core.ml.predictor import predict_alternative_credit
    return predict_alternative_credit(customer, features)



# ---------------------------------------------------------------------------
# Public dispatcher.
# ---------------------------------------------------------------------------

def _features_for(customer):
    """Return (features_dict, source_label).

    Prefers the most recent parsed bank-statement features over the
    seeded-synthetic generator.
    """
    bs = (
        BankStatement.objects.filter(customer=customer, parsed_at__isnull=False)
        .exclude(parsed_features={})
        .order_by("-uploaded_at")
        .first()
    )
    if bs and bs.parsed_features:
        # Defensive copy + ensure all seven keys exist.
        synth = _generate_features(customer)
        merged = {**synth, **bs.parsed_features}
        return merged, f"bank_statement#{bs.id}"
    return _generate_features(customer), "synthetic"


def generate_score(customer, algorithm: str = AI_MODEL) -> ScoreReport:
    algorithm = AI_MODEL

    features, source = _features_for(customer)

    has_active_consent = AAConsent.objects.filter(
        customer=customer, status=AAConsent.Status.ACTIVE
    ).exists()
    verified_docs = Document.objects.filter(
        customer=customer, status=Document.Status.VERIFIED
    ).count()
    profile = getattr(customer, "profile", None)
    profile_complete = bool(profile and profile.monthly_income)

    assessment = {}
    if algorithm == AI_MODEL:
        score, positives, negatives, recommended_loan, assessment = _score_ai_model(
            features, customer=customer
        )
        band = _ai_band(score)
    elif algorithm == CANONICAL:
        score, positives, negatives = _score_canonical(features)
        band = _band_for(score)
        recommended_loan = _recommended_loan(score)
    else:
        score, positives, negatives = _score_baseline(
            features,
            has_active_consent=has_active_consent,
            verified_docs=verified_docs,
            profile_complete=profile_complete,
        )
        band = _band_for(score)
        recommended_loan = _recommended_loan(score)

    return ScoreReport.objects.create(
        customer=customer,
        algorithm=algorithm,
        score=score,
        band=band,
        income_consistency=features["income_consistency"],
        expense_ratio=features["expense_ratio"],
        savings_ratio=features["savings_ratio"],
        payment_timeliness=features["payment_timeliness"],
        transaction_frequency=features["transaction_frequency"],
        bounce_rate=features["bounce_rate"],
        digital_engagement=features["digital_engagement"],
        top_positive_factors=positives,
        top_negative_factors=negatives,
        recommended_loan_amount=recommended_loan,
        ai_assessment=assessment,
    )
