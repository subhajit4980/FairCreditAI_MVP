import os
import json
import joblib
import datetime
from pathlib import Path
from django.utils import timezone
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

from core.models import User, CustomerProfile, Document, ScoreReport

MODELS_DIR = Path(__file__).parent / "models"
from core.ml.ai_credit_score_model import AICreditScoreModel

def predict_alternative_credit(customer: User, cashflow_features: dict) -> Tuple[int, list, list, int, dict]:
    """Execute AI-based alternative credit scoring & loan underwriting engine.
    
    Returns:
        (score, positives, negatives, recommended_loan, assessment_dict)
    """
    # 1. Gather Demographic & Profile features
    profile = getattr(customer, "profile", None)
    if (not profile or 
        profile.date_of_birth is None or 
        not getattr(profile, "occupation", None) or 
        not getattr(profile, "gender", None) or 
        not getattr(profile, "education", None)):
        raise ValueError(
            "Incomplete profile details. Please complete your profile details (including Date of Birth, Gender, Education, and Occupation) before generating a score."
        )

    # Base ID
    cust_id = customer.username.upper() if getattr(customer, "username", None) else "NTC_00000000001"
    if not (cust_id.startswith("CUST_") or cust_id.startswith("NTC_")):
        cust_id = f"NTC_{customer.id:011d}" if getattr(customer, "id", None) else "NTC_00000000001"

    # Merge profile details into cashflow_features
    # This ensures that demographic data is passed into align_and_fill_features if expected by the model
    if profile:
        today = datetime.date.today()
        dob = profile.date_of_birth
        age = float(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
        cashflow_features['Age'] = age
        cashflow_features['Gender'] = profile.gender
        cashflow_features['Education'] = profile.education
        
        occ = profile.occupation.lower()
        if "salaried" in occ:
            cashflow_features['Employment_Type'] = "Salaried"
        elif "shop" in occ or "owner" in occ or "self" in occ:
            cashflow_features['Employment_Type'] = "Self-Employed"
        else:
            cashflow_features['Employment_Type'] = "Freelancer"

        if profile.monthly_income is not None:
            cashflow_features['Monthly_Income'] = float(profile.monthly_income)
            cashflow_features['Annual_Income'] = float(profile.monthly_income) * 12

    verified_docs = Document.objects.filter(customer=customer, status=Document.Status.VERIFIED).count()
    cashflow_features['KYC_Status'] = 1.0 if verified_docs > 0 else 0.0

    # 2. Load unified model
    path = MODELS_DIR / "AI_Credit_Score.joblib"
    if not path.exists():
        raise FileNotFoundError(f"Unified model not found at {path}")
    ai_model = joblib.load(path)
    
    # 3. Predict
    out = ai_model.predict(cashflow_features)

    ai_credit_score = out["ai_credit_score"]
    fraud_prob = out["fraud_probability"]
    pd_prob = out["probability_of_default"]
    risk_grade = out["risk_grade"]
    decision_str = out["underwriting_decision"]
    reason_str = out["decision_reason"]
    max_approved_loan = out["max_approved_limit"]
    recommended_loan = out["recommended_loan_amount"]
    base_rate = out["interest_rate"]
    recommendations_str = out["actionable_recommendations"]
    income_stability_index = out["income_stability_index"]
    expense_ratio = out["expense_ratio"]
    savings_ratio = out["savings_ratio"]
    monthly_income = out["monthly_income_used"]

    biz_explanation = out["Business_Explanation"]
    customer_explanation = out["Customer_Explanation"]

    report_data = {
        "CustomerID": cust_id,
        "AI_Credit_Score": ai_credit_score,
        "Income_Stability_Score": round(income_stability_index, 4),
        "Fraud_Probability": round(fraud_prob, 4),
        "Probability_of_Default": round(pd_prob, 4),
        "Risk_Grade": risk_grade,
        "Underwriting_Decision": decision_str,
        "Decision_Reason": reason_str,
        "Max_Approved_Limit": max_approved_loan,
        "Recommended_Loan_Amount": recommended_loan,
        "Interest_Rate": base_rate,
        "Business_Explanation": biz_explanation,
        "Customer_Explanation": customer_explanation,
        "Actionable_Recommendations": recommendations_str,

        # Included for backward compatibility in templates
        "ai_credit_score": ai_credit_score,
        "fraud_probability": round(fraud_prob, 4),
        "probability_of_default": round(pd_prob, 4),
        "risk_grade": risk_grade,
        "underwriting_decision": decision_str,
        "decision_reason": reason_str,
        "max_approved_limit": max_approved_loan,
        "recommended_loan_amount": recommended_loan,
        "interest_rate": base_rate,
        "business_explanation": biz_explanation,
        "customer_explanation": customer_explanation,
        "actionable_recommendations": recommendations_str,
        "monthly_income_used": int(monthly_income),
        "income_consistency": round(income_stability_index, 4),
        "expense_ratio": round(expense_ratio, 4),
        "savings_ratio": round(savings_ratio, 4),
        "monthly_trends": cashflow_features.get("monthly_trends", []),
        "sanitization_stats": cashflow_features.get("sanitization_stats", {}),
        "Monthly_Trends": cashflow_features.get("monthly_trends", []),
        "Sanitization_Stats": cashflow_features.get("sanitization_stats", {}),
    }

    print(f"Assessment generated for customer '{cust_id}': {json.dumps(report_data, indent=2)}")
    
    positives = []
    if income_stability_index > 0.7: positives.append("Stable income detected")
    if fraud_prob < 0.1: positives.append("Low fraud risk")
    
    negatives = []
    if pd_prob > 0.4: negatives.append("High probability of default")

    return ai_credit_score, positives, negatives, recommended_loan, report_data
