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

    Requires a valid parsed bank statement.
    """
    bs = (
        BankStatement.objects.filter(customer=customer, parsed_at__isnull=False)
        .exclude(parsed_features={})
        .order_by("-uploaded_at")
        .first()
    )
    if bs and bs.parsed_features:
        return bs.parsed_features, f"bank_statement#{bs.id}"
    
    raise ValueError("Cannot generate score: No valid bank statement data found. Please upload a bank statement or connect your account.")


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
