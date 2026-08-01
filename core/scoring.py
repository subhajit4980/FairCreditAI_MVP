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
AI_MODEL = "ai_model"
ALGORITHMS = (AI_MODEL,)


def _seeded_random(user_id: int) -> random.Random:
    seed = int(hashlib.sha256(str(user_id).encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)





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
        raw_credits = round(credits * rng.uniform(1.05, 1.15), 2)
        raw_debits = round(debits * rng.uniform(1.02, 1.08), 2)
        monthly_trends.append({
            "month": m,
            "credit": credits,
            "debit": debits,
            "raw_credit": raw_credits,
            "raw_debit": raw_debits
        })

    sanitization_stats = {
        "self_transfer_credits_count": rng.randint(2, 5),
        "self_transfer_credits_amount": round(average_monthly_income * rng.uniform(0.04, 0.08), 2),
        "self_transfer_debits_count": rng.randint(3, 7),
        "self_transfer_debits_amount": round(average_monthly_expense * rng.uniform(0.03, 0.06), 2),
        "loan_credits_count": rng.randint(0, 2),
        "loan_credits_amount": round(average_monthly_income * rng.uniform(0.05, 0.12), 2),
        "cash_deposit_credits_count": rng.randint(1, 3),
        "cash_deposit_credits_amount": round(average_monthly_income * rng.uniform(0.02, 0.05), 2),
        "winsorized_credits_count": rng.randint(0, 1),
        "winsorized_credits_amount": round(rng.uniform(0, 5000), 2)
    }

    return {
        "monthly_trends": monthly_trends,
        "sanitization_stats": sanitization_stats,
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

    score, positives, negatives, recommended_loan, assessment = _score_ai_model(
        features, customer=customer
    )
    band = _ai_band(score)

    if not assessment:
        assessment = {
            "monthly_trends": features.get("monthly_trends", []),
            "sanitization_stats": features.get("sanitization_stats", {})
        }

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
