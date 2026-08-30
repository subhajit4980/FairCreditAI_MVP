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
_cache = {}

def get_pipeline(name: str) -> Dict[str, Any]:
    """Load and cache the joblib pipeline dictionary."""
    if name not in _cache:
        filename = f"{name}_pipeline.joblib"
        if name == "fraud":
            filename = "fraud_detection_pipeline.joblib"
        path = MODELS_DIR / filename
        if not path.exists():
            raise FileNotFoundError(f"Model pipeline artifact not found at {path}")
        _cache[name] = joblib.load(path)
    return _cache[name]

def get_expected_columns(name: str) -> list:
    """Retrieve expected feature column names from metadata JSON."""
    path = MODELS_DIR / f"{name}_metadata.json"
    if not path.exists():
        payload = get_pipeline(name)
        if "feature_columns" in payload:
            return list(payload["feature_columns"])
        return []
    with open(path, "r") as f:
        meta = json.load(f)
    return meta.get("feature_columns", [])

def align_and_fill_features(features_dict: dict, expected_cols: list) -> pd.DataFrame:
    """Align feature dict to expected format, inserting default values where missing."""
    row_dict = {}
    for col in expected_cols:
        if col in features_dict:
            row_dict[col] = features_dict[col]
        else:
            col_lower = col.lower()
            if "credit_score" in col_lower:
                row_dict[col] = 50.0
            elif "match_score" in col_lower or "liveness" in col_lower:
                row_dict[col] = 0.90
            elif "kyc" in col_lower or "verified" in col_lower:
                row_dict[col] = 1.0
            else:
                row_dict[col] = 0.0
                
    df = pd.DataFrame([row_dict])
    for c in df.select_dtypes(include=["object", "category"]).columns:
        df[c] = df[c].astype("category").cat.codes + 1
        
    return df[expected_cols]

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

    # 2. Extract specific features needed for logic
    monthly_income = float(cashflow_features.get("average_monthly_income", 30000))
    monthly_expense = float(cashflow_features.get("average_monthly_expense", 15000))
    existing_emi = float(cashflow_features.get("emi_payments", 0.0)) / 12.0
    
    available_disposable_income = monthly_income - monthly_expense - existing_emi
    foir = (existing_emi / monthly_income) if monthly_income > 0 else 1.0

    # 3. Load pipelines and get expected features
    fraud_pipeline = get_pipeline("fraud")
    credit_pipeline = get_pipeline("credit_risk")
    
    fraud_model = fraud_pipeline['model'] if isinstance(fraud_pipeline, dict) and 'model' in fraud_pipeline else fraud_pipeline
    credit_model = credit_pipeline['model'] if isinstance(credit_pipeline, dict) and 'model' in credit_pipeline else credit_pipeline

    fraud_expected_features = get_expected_columns("fraud")
    credit_expected_features = get_expected_columns("credit_risk")

    # 4. Align features
    X_inf_fraud = align_and_fill_features(cashflow_features, fraud_expected_features)
    X_inf_credit = align_and_fill_features(cashflow_features, credit_expected_features)

    # 5. INFERENCE (FRAUD & DEFAULT RISK)
    fraud_prob = float(fraud_model.predict_proba(X_inf_fraud)[:, 1][0])
    pd_prob = float(credit_model.predict_proba(X_inf_credit)[:, 1][0])

    # 6. GRADING & DECISION ENGINE
    GRADE_BOUNDS = {'MAX_A': 0.15, 'MAX_B': 0.30, 'MAX_C': 0.50, 'MAX_D': 0.70}
    
    def map_pd_to_regulatory_grade(pd_val: float) -> str:
        if pd_val <= GRADE_BOUNDS['MAX_A']: return 'Grade A'
        if pd_val <= GRADE_BOUNDS['MAX_B']: return 'Grade B'
        if pd_val <= GRADE_BOUNDS['MAX_C']: return 'Grade C'
        if pd_val <= GRADE_BOUNDS['MAX_D']: return 'Grade D'
        return 'Grade E'

    risk_grade = map_pd_to_regulatory_grade(pd_prob)

    pricing_matrix = {
        'Grade A': {"base_rate": 0.105, "multiplier": 8.0},
        'Grade B': {"base_rate": 0.120, "multiplier": 6.0},
        'Grade C': {"base_rate": 0.145, "multiplier": 4.0},
        'Grade D': {"base_rate": 0.180, "multiplier": 2.0},
        'Grade E': {"base_rate": 0.240, "multiplier": 1.0},
    }

    tier = pricing_matrix.get(risk_grade, pricing_matrix['Grade E'])
    max_approved_loan = int(max(0, monthly_income * tier["multiplier"]))
    recommended_loan = int(max_approved_loan * 0.80)

    decision_str = ""
    reason_str = ""
    if fraud_prob >= 0.75:
        decision_str = "REJECTED"
        reason_str = "Severe fraud risk flag triggered."
        max_approved_loan = 0
        recommended_loan = 0
    elif pd_prob >= 0.80:
        decision_str = "REJECTED"
        reason_str = "Very high probability of default."
        max_approved_loan = 0
        recommended_loan = 0
    elif pd_prob >= 0.50 or fraud_prob >= 0.50 or risk_grade in {'Grade D', 'Grade E'}:
        decision_str = "REVIEW"
        reason_str = "Manual review recommended due to elevated risk parameters."
        recommended_loan = int(max_approved_loan * 0.50)
    elif foir > 0.45 or available_disposable_income <= 0:
        decision_str = "REVIEW"
        reason_str = "Manual review recommended due to cashflow margin or EMI burden."
        recommended_loan = int(max_approved_loan * 0.50)
    else:
        decision_str = "APPROVED"
        reason_str = "Passed alternative risk underwriting policy based on verified bank statement cashflow."

    # COMPOSITE AI CREDIT SCORE
    pd_factor = (1.0 - pd_prob) * 45
    
    # default income consistency to 0.7 if not in cashflow_features
    income_stability_index = float(cashflow_features.get('income_stability_index', cashflow_features.get('income_consistency', 0.7)))
    stability_factor = min(1.0, income_stability_index) * 30
    
    fraud_factor = (1.0 - fraud_prob) * 15
    
    savings_ratio = float(cashflow_features.get('savings_ratio', 0.0))
    savings_factor = max(0.0, min(1.0, savings_ratio + 0.5)) * 10

    ai_credit_score = int(np.clip(pd_factor + stability_factor + fraud_factor + savings_factor, 0, 100))

    # RECOMMENDATIONS
    recs = []
    if savings_ratio < 0.20:
        recs.append("Increase your monthly savings cushion above 20% of net monthly income.")
    
    atm_cash_ratio = float(cashflow_features.get('atm_cash_ratio', 0.0))
    if atm_cash_ratio > 0.20:
        recs.append("Reduce liquid cash withdrawals to improve digital financial traceability.")
        
    expense_ratio = float(cashflow_features.get('expense_ratio', 0.80))
    if expense_ratio > 0.90:
        recs.append("Reduce discretionary e-commerce and dining spending to build a cash reserve.")

    recommendations_str = " | ".join(recs) if recs else "Maintain current positive credit and balance management behaviors."

    biz_explanation = f"Evaluated borrower '{cust_id}'. AI Credit Score: {ai_credit_score}/100. Fraud Probability: {fraud_prob:.2%}, Probability of Default: {pd_prob:.2%}. Underwriting Decision: {decision_str}."
    customer_explanation = f"Your application was evaluated using your bank statement cashflow data. Your alternative AI credit score is {ai_credit_score}/100 with a {risk_grade} risk classification."

    # Return exactly matching JSON structure as in notebook, while also making sure legacy elements are present if needed.
    # We will embed both the notebook's expected outputs and the legacy fields so the rest of the app doesn't crash if it looks for lower_case keys.

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
        "Interest_Rate": tier["base_rate"],
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
        "interest_rate": tier["base_rate"],
        "business_explanation": biz_explanation,
        "customer_explanation": customer_explanation,
        "actionable_recommendations": recommendations_str,
        "monthly_income_used": int(monthly_income),
        "income_consistency": round(income_stability_index, 4),
        "expense_ratio": round(expense_ratio, 4),
        "savings_ratio": round(savings_ratio, 4),
    }

    print(f"Assessment generated for customer '{cust_id}': {json.dumps(report_data, indent=2)}")
    
    positives = []
    if income_stability_index > 0.7: positives.append("Stable income detected")
    if fraud_prob < 0.1: positives.append("Low fraud risk")
    
    negatives = []
    if pd_prob > 0.4: negatives.append("High probability of default")

    return ai_credit_score, positives, negatives, recommended_loan, report_data
