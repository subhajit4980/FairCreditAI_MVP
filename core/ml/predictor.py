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
    """Execute rule-based alternative credit scoring & loan underwriting engine.
    
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

    # 2. Extract Redesigned Cashflow Features
    days_range = float(cashflow_features.get("days_range", 180))
    bounces = float(cashflow_features.get("bounces", 0))
    self_transfer_ratio = float(cashflow_features.get("self_transfer_ratio", 0.0))
    savings_ratio = float(cashflow_features.get("savings_ratio", 0.0))
    discretionary_expense_ratio = float(cashflow_features.get("discretionary_expense_ratio", 0.3))
    income_recurrence = float(cashflow_features.get("income_recurrence", 0.7))
    income_concentration = float(cashflow_features.get("income_concentration", 0.0))
    balance_retention_ratio = float(cashflow_features.get("balance_retention_ratio", 0.0))
    low_balance_frequency = float(cashflow_features.get("low_balance_frequency", 0.0))
    foir = float(cashflow_features.get("foir", 0.0))
    payment_timeliness = float(cashflow_features.get("payment_timeliness", 0.95))
    counterparty_breadth = float(cashflow_features.get("counterparty_breadth", 0.5))
    bounces_per_month = float(cashflow_features.get("bounces_per_month", 0.0))
    
    # 3. RULE-BASED SCORING CALCULATION (0-100)
    # A. Income Quality & Stability (30% weight)
    s_income = (income_recurrence * 100.0 * 0.70) + (income_concentration * 100.0 * 0.30)
    
    # B. Liquidity & Buffer (25% weight)
    score_brr = min(100.0, balance_retention_ratio * 100.0)
    score_lbf = (1.0 - low_balance_frequency) * 100.0
    s_liquidity = (score_brr * 0.60) + (score_lbf * 0.40)
    
    # C. Expense & Obligation (20% weight)
    score_foir = max(0.0, (1.0 - foir) * 100.0)
    score_dsr = max(0.0, (1.0 - discretionary_expense_ratio) * 100.0)
    s_expense = (score_foir * 0.70) + (score_dsr * 0.30)
    
    # D. Payment Discipline (15% weight)
    score_timeliness = max(0.0, payment_timeliness * 100.0 - (bounces * 10.0))
    s_discipline = score_timeliness
    
    # E. Transaction Diversity (10% weight)
    score_cbd = counterparty_breadth * 100.0
    s_diversity = score_cbd
    
    # Composite Score
    score = int(np.clip(
        (s_income * 0.30) + (s_liquidity * 0.25) + (s_expense * 0.20) + (s_discipline * 0.15) + (s_diversity * 0.10),
        0.0, 100.0
    ))

    # 4. PRICING & RISK TIER MATRIX
    pricing_matrix = {
        "Grade A": {"base_rate": 0.105, "multiplier": 8.0},
        "Grade B": {"base_rate": 0.120, "multiplier": 6.0},
        "Grade C": {"base_rate": 0.145, "multiplier": 4.0},
        "Grade D": {"base_rate": 0.180, "multiplier": 2.0},
        "Grade E": {"base_rate": 0.240, "multiplier": 0.0},
    }
    
    if score >= 85:
        risk_grade = "Grade A"
    elif score >= 70:
        risk_grade = "Grade B"
    elif score >= 55:
        risk_grade = "Grade C"
    elif score >= 40:
        risk_grade = "Grade D"
    else:
        risk_grade = "Grade E"
        
    tier = pricing_matrix[risk_grade]
    
    # Map back probability metrics for compatibility
    pd_prob = 0.08 if score >= 85 else 0.18 if score >= 70 else 0.35 if score >= 55 else 0.60 if score >= 40 else 0.85
    fraud_prob = 0.80 if self_transfer_ratio > 0.40 else 0.50 if bounces_per_month > 3.0 else 0.02

    # 5. UNDERWRITING DECISION ENGINE & KNOCKOUT RULES
    effective_income = monthly_income * (income_recurrence ** 1.5)
    monthly_expense = cashflow_features.get("expense_ratio", 0.5) * effective_income
    detected_obligations = cashflow_features.get("detected_obligations", [])
    active_obligations = [o for o in detected_obligations if o["status"] == "Active"]
    total_active_monthly_emi = sum(o["amount"] for o in active_obligations)
    
    if total_active_monthly_emi > 0:
        existing_emi = total_active_monthly_emi
        foir = total_active_monthly_emi / (monthly_income + 1)
    else:
        existing_emi = cashflow_features.get("emi_payments", 0.0) / 12.0
        
    available_disposable_income = effective_income - monthly_expense - existing_emi
    
    ko_triggered = False
    reject_reason = ""
    insufficient_history = False
    
    if days_range < 180:
        ko_triggered = True
        insufficient_history = True
        reject_reason = f"Minimum transaction history failure: statement duration is {int(days_range)} days (required: 180+ days)."
        score = 0
        risk_grade = "Grade E"
        tier = pricing_matrix[risk_grade]
        pd_prob = 0.85
    elif bounces >= 3:
        ko_triggered = True
        reject_reason = f"Excessive mandate/ECS bounces: {int(bounces)} bounces detected (required: less than 3)."
    elif self_transfer_ratio > 0.40:
        ko_triggered = True
        reject_reason = f"Exceeded self-transfer fraud limits: {self_transfer_ratio:.1%} of credits are self-transfers (required: less than 40%)."
    elif savings_ratio < 0.0 or discretionary_expense_ratio >= 1.0 or available_disposable_income <= 0:
        ko_triggered = True
        reject_reason = "Negative cashflow surplus (savings ratio is negative or expenses exceed stable income)."

    if ko_triggered or score < 40:
        decision = "REJECTED"
        reason = reject_reason if reject_reason else f"Alternative credit score {score}/100 is below the minimum Tier D threshold."
        max_approved_loan = 0
        recommended_loan = 0
    else:
        # S_dispo cap rule
        s_dispo = max(0.0, available_disposable_income)
        limit_cap = (s_dispo * 12.0) / 0.15
        max_approved_loan = int(min(effective_income * tier["multiplier"], limit_cap))
        recommended_loan = int(max_approved_loan * 0.80)
        
        if score >= 70:
            decision = "APPROVED"
            reason = "Passed alternative cashflow risk underwriting policy."
        else:
            decision = "REVIEW"
            reason = "Manual review recommended due to Tier D risk parameters."

    # 6. DYNAMIC DRIFTERS DEFINITION
    positives = []
    negatives = []
    
    if income_recurrence >= 0.80:
        positives.append(f"Strong income recurrence and consistency ({income_recurrence:.1%}) (+20 pts)")
    else:
        negatives.append(f"Income recurrence below target ({income_recurrence:.1%}) (-15 pts)")
        
    if balance_retention_ratio >= 0.30:
        positives.append(f"Healthy balance retention ratio ({balance_retention_ratio:.1%}) (+15 pts)")
    else:
        negatives.append(f"Weak balance retention buffer ({balance_retention_ratio:.1%}) (-10 pts)")
        
    if savings_ratio >= 0.10:
        positives.append(f"Positive monthly savings ratio ({savings_ratio:.1%}) (+15 pts)")
    else:
        negatives.append(f"Low savings buffer ({savings_ratio:.1%}) (-10 pts)")
        
    if bounces == 0:
        positives.append("Clean repayment profile with zero ECS/cheque bounces (+15 pts)")
    else:
        negatives.append(f"Mandate/ECS bounces recorded ({int(bounces)} bounces) (-15 pts)")

    key_strengths = list(positives) if positives else ["Consistent transaction activity."]
    key_improvement_areas = list(negatives) if negatives else ["Maintain current financial behavior."]

    # 7. RECOMMENDATIONS GENERATION
    categorized_recommendations = {
        "Liquidity & Savings": [],
        "Digital Traceability": [],
        "Spending Discipline": [],
        "Debt & Obligation Management": [],
        "Wealth Building & Stability": []
    }
    
    if savings_ratio < 0.20:
        categorized_recommendations["Liquidity & Savings"].append("Increase your monthly savings cushion above 20% of net monthly income to buffer against unexpected expenses.")
    else:
        categorized_recommendations["Liquidity & Savings"].append("Keep maintaining your strong monthly savings cushion of at least 20%.")
        
    if self_transfer_ratio > 0.15:
        categorized_recommendations["Digital Traceability"].append("Reduce internal self-account transfers to improve transparent digital banking records.")
    else:
        categorized_recommendations["Digital Traceability"].append("Your digital transaction history is robust and highly traceable.")
        
    if discretionary_expense_ratio > 0.40:
        categorized_recommendations["Spending Discipline"].append("Reduce discretionary e-commerce and dining spending to build a cash reserve.")
    else:
        categorized_recommendations["Spending Discipline"].append("You exhibit excellent spending discipline and budget control.")
        
    if foir > 0.15 or existing_emi > 0.0:
        categorized_recommendations["Debt & Obligation Management"].append("Keep existing shadow EMI obligations below 15% of monthly income to prevent payment delays.")
    if decision == "REJECTED":
        categorized_recommendations["Debt & Obligation Management"].append("Pay down existing shadow obligations and avoid any new credit card / BNPL loading.")
    else:
        categorized_recommendations["Debt & Obligation Management"].append("Maintain current credit balance discipline.")
        
    if investment_ratio := float(cashflow_features.get("investment_ratio", 0.0)) < 0.05:
        categorized_recommendations["Wealth Building & Stability"].append("Consider investing at least 5-10% of monthly earnings into mutual funds/SIPs to build credit assets.")
    else:
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
            "Income_Stability_Index": round(income_recurrence, 4),
            "Savings_Ratio": round(savings_ratio, 4),
            "Essential_Expense_Ratio": round(cashflow_features.get("essential_expense_ratio", 0.20), 4),
            "Discretionary_Expense_Ratio": round(discretionary_expense_ratio, 4)
        },
        "Underwriter_Key_Observations": [
            f"Alternative credit score evaluated at {score}/100 with a {risk_grade} risk classification.",
            f"Rule-based default probability (PD) is {pd_prob:.2%} and fraud risk check is {fraud_prob:.2%}.",
            f"Self-transfer volume check shows ratio at {self_transfer_ratio:.2%}.",
            f"Income concentration score is {income_concentration:.4f}."
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
            "Keep your latest bank statements and identity cards ready.",
            "Reach out to customer support if you have additional bank statement data."
        ] if decision == "REVIEW" else [
            "We cannot extend a credit offer at this time due to high risk indicators.",
            "Follow the actionable recommendations below to improve your cashflow metrics.",
            "You are eligible to re-apply in 90 days after improving your savings ratio."
        ]
    }

    assessment = {
        "CustomerID": cust_id,
        "AI_Credit_Score": score,
        "insufficient_history": insufficient_history,
        "days_range": int(days_range),
        "Income_Stability_Score": round(income_recurrence, 4),
        "Fraud_Probability": round(fraud_prob, 4),
        "Probability_of_Default": round(pd_prob, 4),
        "Risk_Grade": risk_grade,
        "Underwriting_Decision": decision,
        "Decision_Reason": reason,
        "Max_Approved_Limit": max_approved_loan,
        "Recommended_Loan_Amount": recommended_loan,
        "Interest_Rate": tier["base_rate"],
        "Total_Active_EMI": int(total_active_monthly_emi),
        "Active_Obligations_Count": len(active_obligations),
        "Bounced_Obligations_Count": sum(1 for o in detected_obligations if o["status"] == "Bounced"),
        "Business_Explanation": biz_explanation,
        "Customer_Explanation": customer_explanation,
        "Actionable_Recommendations": categorized_recommendations,
        "Monthly_Trends": cashflow_features.get("monthly_trends", []),
        "Sanitization_Stats": cashflow_features.get("sanitization_stats", {}),
        "Detected_Obligations": detected_obligations,
 
        "ai_credit_score": score,
        "insufficient_history": insufficient_history,
        "days_range": int(days_range),
        "income_stability_score": round(income_recurrence, 4),
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
        "total_active_emi": int(total_active_monthly_emi),
        "active_obligations_count": len(active_obligations),
        "bounced_obligations_count": sum(1 for o in detected_obligations if o["status"] == "Bounced"),
        "business_explanation": biz_explanation,
        "customer_explanation": customer_explanation,
        "actionable_recommendations": categorized_recommendations,
        "monthly_trends": cashflow_features.get("monthly_trends", []),
        "sanitization_stats": cashflow_features.get("sanitization_stats", {}),
        "detected_obligations": detected_obligations,
    }
    print(f"Assessment generated for customer '{cust_id}': {json.dumps(assessment, indent=2)}")
    return score, positives, negatives, recommended_loan, assessment
