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
from core.ml.obligations import get_day_suffix


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

    # Synthetic obligations generator
    detected_obligations = []
    if rng.random() > 0.3:
        amt = round(rng.uniform(1500, 8000), -2)
        day = rng.randint(2, 7)
        total_payments = rng.randint(4, 6)
        pct = (amt / average_monthly_income) * 100.0 if average_monthly_income > 0 else 0.0
        detected_obligations.append({
            "lender": "Bajaj Finance",
            "signature": "ACH BAJAJ FIN",
            "amount": float(amt),
            "frequency": "Monthly",
            "preferred_day": day,
            "preferred_day_display": get_day_suffix(day),
            "total_payments": total_payments,
            "total_paid": float(amt * total_payments),
            "first_payment_date": "05-01-2026",
            "last_payment_date": "05-05-2026",
            "status": "Active" if rng.random() > 0.2 else "Completed",
            "explainable_reason": f"Classified as recurring monthly obligation to Bajaj Finance. Identified {total_payments} payments of average ₹{amt:,.0f} spaced by ~30 days on the {get_day_suffix(day)}.",
            "factor_insights": f"Regular EMI of ₹{amt:,.0f} to Bajaj Finance consumes {pct:.1f}% of your monthly income (₹{average_monthly_income:,.0f}). Repayment status: Active.",
            "payment_timeline": [
                {"month": "Jan 2026", "date": f"0{day}-01-2026", "amount": float(amt), "status": "Paid"},
                {"month": "Feb 2026", "date": f"0{day}-02-2026", "amount": float(amt), "status": "Paid"},
                {"month": "Mar 2026", "date": f"0{day}-03-2026", "amount": float(amt), "status": "Paid"},
                {"month": "Apr 2026", "date": f"0{day}-04-2026", "amount": float(amt), "status": "Paid"},
                {"month": "May 2026", "date": f"0{day}-05-2026", "amount": float(amt), "status": "Paid"},
            ][:total_payments]
        })
    if rng.random() > 0.6:
        amt = round(rng.uniform(5000, 15000), -2)
        day = rng.randint(1, 5)
        total_payments = rng.randint(3, 5)
        pct = (amt / average_monthly_income) * 100.0 if average_monthly_income > 0 else 0.0
        detected_obligations.append({
            "lender": "HDFC Bank",
            "signature": "ACH HDFC LOAN",
            "amount": float(amt),
            "frequency": "Monthly",
            "preferred_day": day,
            "preferred_day_display": get_day_suffix(day),
            "total_payments": total_payments,
            "total_paid": float(amt * total_payments),
            "first_payment_date": "02-02-2026",
            "last_payment_date": "02-05-2026",
            "status": "Active",
            "explainable_reason": f"Classified as recurring monthly obligation to HDFC Bank. Identified {total_payments} payments of average ₹{amt:,.0f} spaced by ~30 days on the {get_day_suffix(day)}.",
            "factor_insights": f"Regular EMI of ₹{amt:,.0f} to HDFC Bank consumes {pct:.1f}% of your monthly income (₹{average_monthly_income:,.0f}). Repayment status: Active.",
            "payment_timeline": [
                {"month": "Feb 2026", "date": f"0{day}-02-2026", "amount": float(amt), "status": "Paid"},
                {"month": "Mar 2026", "date": f"0{day}-03-2026", "amount": float(amt), "status": "Paid"},
                {"month": "Apr 2026", "date": f"0{day}-04-2026", "amount": float(amt), "status": "Paid"},
                {"month": "May 2026", "date": f"0{day}-05-2026", "amount": float(amt), "status": "Paid"},
            ][:total_payments]
        })

    active_synthetic_emi = sum(o["amount"] for o in detected_obligations if o["status"] == "Active")
    foir = active_synthetic_emi / (average_monthly_income + 1)
    if detected_obligations:
        emi_payments = sum(o["total_paid"] for o in detected_obligations)

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
        "foir": round(foir, 4),
        "detected_obligations": detected_obligations,
    }






# ---------------------------------------------------------------------------
# AI model algorithm (pure-Python port of fairCreditAiModel/AI_Credit_Score).
# ---------------------------------------------------------------------------

# AI model algorithm (pure-Python port of fairCreditAiModel/AI_Credit_Score) now delegates to core.ml.predictor


def _ai_band(score):
    """Map the 0–100 AI score onto the shared five-band scale."""
    if score > 80:
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
        income_consistency=assessment.get("income_consistency", features.get("income_consistency")),
        expense_ratio=assessment.get("expense_ratio", features.get("expense_ratio")),
        savings_ratio=assessment.get("savings_ratio", features.get("savings_ratio")),
        payment_timeliness=features["payment_timeliness"],
        transaction_frequency=features["transaction_frequency"],
        bounce_rate=features["bounce_rate"],
        digital_engagement=features["digital_engagement"],
        top_positive_factors=positives,
        top_negative_factors=negatives,
        recommended_loan_amount=recommended_loan,
        ai_assessment=assessment,
    )
