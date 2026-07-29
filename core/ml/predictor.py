import os
import json
import joblib
import datetime
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any

from django.utils import timezone
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
        # Fall back to checking cache payload features
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
    
    # Handle string/categorical types
    for c in df.select_dtypes(include=["object", "category"]).columns:
        df[c] = df[c].astype("category").cat.codes + 1
        
    return df[expected_cols]

def predict_alternative_credit(customer: User, cashflow_features: dict) -> Tuple[int, list, list, int, dict]:
    """Execute machine learning pipelines to compute alternative credit metrics.
    
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
     
    if profile and profile.monthly_income is not None:
        monthly_income = float(profile.monthly_income)
    elif "average_monthly_income" in cashflow_features:
        monthly_income = float(cashflow_features["average_monthly_income"])
    else:
        monthly_income = 30000.0
    print(f"Monthly Income: {monthly_income}")
    today = datetime.date.today()
    dob = profile.date_of_birth
    age = float(today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day)))
        
    occ = profile.occupation.lower()
    if "salaried" in occ:
        employment_type = "Salaried"
    elif "shop" in occ or "owner" in occ or "self" in occ:
        employment_type = "Self-Employed"
    else:
        employment_type = "Freelancer"
            
    verified_docs = Document.objects.filter(customer=customer, status=Document.Status.VERIFIED).count()
    kyc_status = 1.0 if verified_docs > 0 else 0.0
    
    # Combined dictionary of ALL engineered/inferred features
    full_features = {
        **cashflow_features,
        "Gender": profile.gender,
        "Age": age,
        "Education": profile.education,
        "Employment_Type": employment_type,
        "Annual_Income": monthly_income * 12.0,
        "Monthly_Income": monthly_income,
        "Account_Type": "Savings",
        "Customer_Segment": "Retail",
        "Savings_Balance": cashflow_features.get("average_balance", 10000.0),
        "Credit_Card_Holder": 1.0 if cashflow_features.get("digital_engagement", 0.0) > 0.6 else 0.0,
        "Device_Age_Years": 2.0,
        "OS": "Android",
        "Rooted": 0.0,
        "SIM_Age_Years": 0.0,
        "Phone_Vintage_Years": 0.0,
        "KYC_Status": kyc_status,
        "Face_Match_Score": 0.0,
        "OCR_Match_Score": 0.0,
        "Liveness_Score": 0.0,
        "Address_Match_Score": 0.0,
        "biometric_identity_score": 0.0,
        "fraud_record_count": 0.0,
        "avg_device_risk": 0.0,
        "avg_geo_risk": 0.0,
        "avg_velocity_risk": 0.00,
        "avg_aml_risk": 0.00,
        "total_fraud_events": 0.0,
        "total_loans": 0.0,
        "total_monthly_emi": cashflow_features.get("emi_payments", 0.0),
        "avg_credit_score": 00.0,
        "approved_loan_count": 0.0,
    }
    
    # 2. Get expectation headers & align inputs
    credit_cols = get_expected_columns("credit_risk")
    fraud_cols = get_expected_columns("fraud")
    
    X_credit = align_and_fill_features(full_features, credit_cols)
    X_fraud = align_and_fill_features(full_features, fraud_cols)
    
    # 3. Load pipelines and predict probabilities
    credit_payload = get_pipeline("credit_risk")
    fraud_payload = get_pipeline("fraud")
    
    credit_model = credit_payload["model"] if isinstance(credit_payload, dict) and "model" in credit_payload else credit_payload
    fraud_model = fraud_payload["model"] if isinstance(fraud_payload, dict) and "model" in fraud_payload else fraud_payload
    
    pd_prob = float(credit_model.predict_proba(X_credit)[:, 1][0])
    print(f"Predicted Probability of Default (PD): {pd_prob:.4f}")
    fraud_prob = float(fraud_model.predict_proba(X_fraud)[:, 1][0])
    print(f"Predicted Fraud Probability: {fraud_prob:.4f}")
    
    # 4. Underwriting Decision Engine
    income_consistency = float(cashflow_features.get("income_consistency", 0.7))
    effective_income = monthly_income * (income_consistency ** 1.5)
    
    monthly_expense = cashflow_features.get("expense_ratio", 0.5) * effective_income
    existing_emi = cashflow_features.get("emi_payments", 0.0) / 12.0
    
    available_disposable_income = effective_income - monthly_expense - existing_emi
    foir = (existing_emi / effective_income) if effective_income > 0 else 1.0
    
    # Map default risk (PD) to Regulatory Grade
    # Grade bounds (PD values where grades change)
    if pd_prob <= 0.15:
        risk_grade = "Grade A"
    elif pd_prob <= 0.30:
        risk_grade = "Grade B"
    elif pd_prob <= 0.50:
        risk_grade = "Grade C"
    elif pd_prob <= 0.70:
        risk_grade = "Grade D"
    else:
        risk_grade = "Grade E"
        
    pricing_matrix = {
        "Grade A": {"base_rate": 0.105, "multiplier": 8.0},
        "Grade B": {"base_rate": 0.120, "multiplier": 6.0},
        "Grade C": {"base_rate": 0.145, "multiplier": 4.0},
        "Grade D": {"base_rate": 0.180, "multiplier": 2.0},
        "Grade E": {"base_rate": 0.240, "multiplier": 1.0},
    }
    
    tier = pricing_matrix.get(risk_grade, pricing_matrix["Grade E"])
    max_approved_loan = int(max(0, effective_income * tier["multiplier"])* 0.10)
    
    recommended_loan = int(max_approved_loan * 0.80)
    
    if fraud_prob >= 0.75:
        decision = "REJECTED"
        reason = "Severe fraud risk flag triggered by XGBoost Classifier."
        max_approved_loan = recommended_loan = 0
    elif pd_prob >= 0.80:
        decision = "REJECTED"
        reason = "Very high probability of default inferred by Extra Trees model."
        max_approved_loan = recommended_loan = 0
    elif float(cashflow_features.get("savings_ratio", 0.0)) < 0.0 or float(cashflow_features.get("expense_ratio", 0.5)) >= 1.0 or available_disposable_income <= 0:
        decision = "REJECTED"
        reason = "Negative cashflow surplus (savings ratio is negative or expenses exceed income)."
        max_approved_loan = recommended_loan = 0
    elif pd_prob >= 0.50 or fraud_prob >= 0.50 or risk_grade in {"Grade D", "Grade E"}:
        decision = "REVIEW"
        reason = "Manual review recommended due to elevated ML risk parameters."
        recommended_loan = int(max_approved_loan * 0.50)
    elif foir > 0.45:
        decision = "REVIEW"
        reason = "Manual review recommended due to cashflow margin or EMI burden."
        recommended_loan = int(max_approved_loan * 0.50)
    else:
        decision = "APPROVED"
        reason = "Passed ML-driven risk underwriting policy based on verified bank statement cashflow."
        
    # 5. Composite AI Credit Score (0-100)
    pd_factor = (1.0 - pd_prob) * 45
    stability_factor = min(1.0, float(cashflow_features.get("income_stability_index", 0.7))) * 30
    fraud_factor = (1.0 - fraud_prob) * 15
    savings_factor = max(0.0, min(1.0, float(cashflow_features.get("savings_ratio", 0.1)) + 0.5)) * 10
    
    score = int(np.clip(pd_factor + stability_factor + fraud_factor + savings_factor, 0, 100))
    
    # 6. SHAP-style Attributions
    factor_rows = [
        ("Repayment capacity (low default risk)", pd_factor, 45),
        ("Income stability", stability_factor, 30),
        ("Clean profile (low fraud risk)", fraud_factor, 15),
        ("Savings cushion", savings_factor, 10),
    ]
    positives = [
        {"factor": label, "impact": f"+{gained:.0f} pts"}
        for label, gained, _cap in sorted(factor_rows, key=lambda r: r[1], reverse=True)
        if gained >= 5
    ][:4]
    negatives = [
        {"factor": f"{label} below target", "impact": f"-{cap - gained:.0f} pts"}
        for label, gained, cap in sorted(factor_rows, key=lambda r: r[2] - r[1], reverse=True)
        if cap - gained >= 3
    ][:4]
    
    # 7. Categorized Recommendations (5 specific keys)
    categorized_recommendations = {
        "Liquidity & Savings": [],
        "Digital Traceability": [],
        "Spending Discipline": [],
        "Debt & Obligation Management": [],
        "Wealth Building & Stability": []
    }
    
    savings_r = float(cashflow_features.get("savings_ratio", 0.0))
    if savings_r < 0.20:
        categorized_recommendations["Liquidity & Savings"].append("Increase your monthly savings cushion above 20% of net monthly income to buffer against unexpected expenses.")
    else:
        categorized_recommendations["Liquidity & Savings"].append("Keep maintaining your strong monthly savings cushion of at least 20%.")
        
    atm_r = float(cashflow_features.get("atm_cash_ratio", 0.0))
    digital_e = float(cashflow_features.get("digital_engagement", 0.8))
    if atm_r > 0.20:
        categorized_recommendations["Digital Traceability"].append("Reduce liquid cash withdrawals to improve digital financial traceability.")
    if digital_e < 0.80:
        categorized_recommendations["Digital Traceability"].append("Conduct more transactions via UPI/Netbanking instead of paper checks to build a stronger transaction velocity trail.")
    if not categorized_recommendations["Digital Traceability"]:
        categorized_recommendations["Digital Traceability"].append("Your digital transaction history is robust and highly traceable.")
        
    expense_r = float(cashflow_features.get("expense_ratio", 0.5))
    disc_r = float(cashflow_features.get("discretionary_expense_ratio", 0.0))
    ess_r = float(cashflow_features.get("essential_expense_ratio", 0.0))
    if expense_r > 0.90 or disc_r > 0.40:
        categorized_recommendations["Spending Discipline"].append("Reduce discretionary e-commerce and dining spending to build a cash reserve.")
    if ess_r > 0.50:
        categorized_recommendations["Spending Discipline"].append("Limit utility/grocery expenses to under 50% of monthly spending to preserve capital for financial buffers.")
    if not categorized_recommendations["Spending Discipline"]:
        categorized_recommendations["Spending Discipline"].append("You exhibit excellent spending discipline and budget control.")
        
    shadow_emi = float(cashflow_features.get("emi_payments", 0.0))
    if foir > 0.15 or shadow_emi > 0.0:
        categorized_recommendations["Debt & Obligation Management"].append("Keep existing shadow EMI obligations below 15% of monthly income to prevent payment delays.")
    if pd_prob > 0.20 or risk_grade in ("Grade C", "Grade D", "Grade E"):
        categorized_recommendations["Debt & Obligation Management"].append("Avoid taking any new credit lines or micro-loans in the next 3 months.")
    if not categorized_recommendations["Debt & Obligation Management"]:
        categorized_recommendations["Debt & Obligation Management"].append("You have a clean payment and low bounce history with well-managed debt obligations.")
        
    inv_r = float(cashflow_features.get("investment_ratio", 0.0))
    stab_idx = float(cashflow_features.get("income_stability_index", 0.7))
    if inv_r < 0.05:
        categorized_recommendations["Wealth Building & Stability"].append("Consider investing at least 5-10% of monthly earnings into mutual funds/SIPs to build credit assets.")
    if stab_idx < 0.70:
        categorized_recommendations["Wealth Building & Stability"].append("Maintain your salaried/business employment profile stability to support future higher credit limit offers.")
    if not categorized_recommendations["Wealth Building & Stability"]:
        categorized_recommendations["Wealth Building & Stability"].append("Your financial profile displays strong long-term stability and wealth-building potential.")

    risk_types = {
        "Grade A": "Low",
        "Grade B": "Low",
        "Grade C": "Medium",
        "Grade D": "High",
        "Grade E": "High",
    }
    
    cust_id = customer.username.upper() if getattr(customer, "username", None) else "NTC_00000000001"
    if not (cust_id.startswith("CUST_") or cust_id.startswith("NTC_")):
        cust_id = f"NTC_{customer.id:011d}" if getattr(customer, "id", None) else "NTC_00000000001"

    key_strengths = []
    for pos in positives:
        key_strengths.append(f"{pos['factor']} ({pos['impact']})")
    if not key_strengths:
        key_strengths.append("Consistent transaction and profile activity.")
        
    key_improvement_areas = []
    for neg in negatives:
        key_improvement_areas.append(f"{neg['factor']} ({neg['impact']})")
    if not key_improvement_areas:
        key_improvement_areas.append("No critical improvements required. Maintain your behavior.")

    biz_explanation = {
        "Executive_Underwriting_Summary": f"Evaluated borrower '{cust_id}'. Alternative Credit Score: {score}/100. Decision: {decision}. Risk Grade: {risk_grade}. Decision Reason: {reason}.",
        "Risk_Decomposition": {
            "Probability_of_Default_PD": round(pd_prob, 4),
            "Fraud_Probability": round(fraud_prob, 4),
            "Risk_Grade": risk_grade,
            "Risk_Classification": risk_types.get(risk_grade, "High")
        },
        "Financial_Cashflow_Analysis": {
            "Calculated_Monthly_Income": int(monthly_income),
            "Calculated_Monthly_Expense": int(monthly_expense),
            "Available_Surplus": int(available_disposable_income),
            "Debt_to_Income_Ratio_FOIR": round(foir, 4),
            "Income_Stability_Index": round(cashflow_features.get("income_stability_index", 0.7), 4),
            "Savings_Ratio": round(savings_r, 4),
            "Essential_Expense_Ratio": round(ess_r, 4),
            "Discretionary_Expense_Ratio": round(disc_r, 4)
        },
        "Underwriter_Key_Observations": [
            f"Alternative credit score evaluated at {score}/100 with a {risk_grade} risk classification.",
            f"Probability of Default is {pd_prob:.2%} (vs standard review thresholds).",
            f"Fraud probability is {fraud_prob:.2%}, classification shows profile is {'Critical' if fraud_prob >= 0.75 else 'Suspicious' if fraud_prob >= 0.50 else 'Clean'}.",
            f"Calculated FOIR is {foir:.2%} with a monthly disposable income of ₹{int(available_disposable_income):,}.",
            f"Digital engagement score is {digital_e:.2%}, demonstrating strong traceability."
        ]
    }

    customer_explanation = {
        "Application_Status": decision,
        "Loan_Offer_Summary": {
            "Max_Approved_Limit": max_approved_loan,
            "Recommended_Loan_Amount": recommended_loan,
            "Interest_Rate": tier["base_rate"]
        },
        "Credit_Score_Drivers": {
            "Key_Strengths": key_strengths,
            "Key_Improvement_Areas": key_improvement_areas
        },
        "Next_Steps": [
            "Accept the loan offer online in the borrower dashboard.",
            "Complete quick e-KYC and sign the e-NACH auto-debit mandate.",
            "Disbursal will be processed directly to your linked bank account within 2 hours."
        ] if decision == "APPROVED" else [
            "Our underwriting team will contact you to perform manual document review.",
            "Keep your latest salary slips or income tax returns ready if requested.",
            "Reach out to customer support if you have additional bank statement data."
        ] if decision == "REVIEW" else [
            "We cannot extend a credit offer at this time due to high risk indicators.",
            "Follow the actionable recommendations below to improve your cashflow metrics.",
            "You are eligible to re-apply in 90 days after improving your savings ratio."
        ]
    }

    assessment = {
        # CamelCase keys matching the requested exact JSON structure:
        "CustomerID": cust_id,
        "AI_Credit_Score": score,
        "Income_Stability_Score": round(cashflow_features.get("income_stability_index", 0.7), 4),
        "Fraud_Probability": round(fraud_prob, 4),
        "Probability_of_Default": round(pd_prob, 4),
        "Risk_Grade": risk_grade,
        "Underwriting_Decision": decision,
        "Decision_Reason": reason,
        "Max_Approved_Limit": max_approved_loan,
        "Recommended_Loan_Amount": recommended_loan,
        "Interest_Rate": tier["base_rate"],
        "Business_Explanation": biz_explanation,
        "Customer_Explanation": customer_explanation,
        "Actionable_Recommendations": categorized_recommendations,
        "Monthly_Trends": cashflow_features.get("monthly_trends", []),

        # Lowercase keys for templates/core/score_detail.html compatibility:
        "ai_credit_score": score,
        "income_stability_score": round(cashflow_features.get("income_stability_index", 0.7), 4),
        "fraud_probability": round(fraud_prob, 4),
        "probability_of_default": round(pd_prob, 4),
        "risk_grade": risk_grade,
        "risk_type": risk_types.get(risk_grade, "High"),
        "underwriting_decision": decision,
        "decision_reason": reason,
        "max_approved_limit": max_approved_loan,
        "recommended_loan_amount": recommended_loan,
        "interest_rate": tier["base_rate"],
        "monthly_income_used": int(monthly_income),
        "business_explanation": biz_explanation,
        "customer_explanation": customer_explanation,
        "actionable_recommendations": categorized_recommendations,
        "monthly_trends": cashflow_features.get("monthly_trends", []),
    }
    return score, positives, negatives, recommended_loan, assessment
