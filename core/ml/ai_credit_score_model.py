import numpy as np
import pandas as pd

class AICreditScoreModel:
    def __init__(self, fraud_model, credit_model, fraud_features, credit_features):
        self.fraud_model = fraud_model
        self.credit_model = credit_model
        self.fraud_features = fraud_features
        self.credit_features = credit_features
        self.GRADE_BOUNDS = {'MAX_A': 0.15, 'MAX_B': 0.30, 'MAX_C': 0.50, 'MAX_D': 0.70}
        self.pricing_matrix = {
            'Grade A': {"base_rate": 0.105, "multiplier": 4.0},
            'Grade B': {"base_rate": 0.120, "multiplier": 3.5},
            'Grade C': {"base_rate": 0.145, "multiplier": 2.5},
            'Grade D': {"base_rate": 0.180, "multiplier": 1.5},
            'Grade E': {"base_rate": 0.240, "multiplier": 1.0},
        }

    def _align_and_fill_features(self, features_dict: dict, expected_cols: list) -> pd.DataFrame:
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

    def map_pd_to_regulatory_grade(self, pd_val: float) -> str:
        if pd_val <= self.GRADE_BOUNDS['MAX_A']: return 'Grade A'
        if pd_val <= self.GRADE_BOUNDS['MAX_B']: return 'Grade B'
        if pd_val <= self.GRADE_BOUNDS['MAX_C']: return 'Grade C'
        if pd_val <= self.GRADE_BOUNDS['MAX_D']: return 'Grade D'
        return 'Grade E'

    def predict(self, cashflow_features: dict) -> dict:
        monthly_income = float(cashflow_features.get("average_monthly_income", 30000))
        monthly_expense = float(cashflow_features.get("average_monthly_expense", 15000))
        existing_emi = float(cashflow_features.get("emi_payments", 0.0)) / 12.0
        
        available_disposable_income = monthly_income - monthly_expense - existing_emi
        foir = (existing_emi / monthly_income) if monthly_income > 0 else 1.0

        X_inf_fraud = self._align_and_fill_features(cashflow_features, self.fraud_features)
        X_inf_credit = self._align_and_fill_features(cashflow_features, self.credit_features)

        fraud_prob = float(self.fraud_model.predict_proba(X_inf_fraud)[:, 1][0])
        pd_prob = float(self.credit_model.predict_proba(X_inf_credit)[:, 1][0])

        risk_grade = self.map_pd_to_regulatory_grade(pd_prob)
        tier = self.pricing_matrix.get(risk_grade, self.pricing_matrix['Grade E'])
        
        max_approved_loan = int(max(0, monthly_income * tier["multiplier"]))* 0.50
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

        max_approved_loan = (int(max_approved_loan) // 10000) * 10000
        recommended_loan = (int(recommended_loan) // 10000) * 10000

        pd_factor = (1.0 - pd_prob) * 45
        income_stability_index = float(cashflow_features.get('income_stability_index', cashflow_features.get('income_consistency', 0.7)))
        stability_factor = min(1.0, income_stability_index) * 30
        fraud_factor = (1.0 - fraud_prob) * 15
        savings_ratio = float(cashflow_features.get('savings_ratio', 0.0))
        savings_factor = max(0.0, min(1.0, savings_ratio + 0.5)) * 10

        ai_credit_score = int(np.clip(pd_factor + stability_factor + fraud_factor + savings_factor, 0, 100))

        # RECOMMENDATIONS
        categorized_recommendations = {
            "Spending Discipline": [],
            "Debt & Obligation Management": [],
            "Wealth Building & Stability": []
        }
        ess_r = float(cashflow_features.get("essential_expense_ratio", 0.0))
        expense_ratio = float(cashflow_features.get('expense_ratio', 0.80))
        disc_r = expense_ratio - ess_r if expense_ratio > ess_r else 0.0
        if expense_ratio > 0.90 or disc_r > 0.40:
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
        if inv_r < 0.05:
            categorized_recommendations["Wealth Building & Stability"].append("Consider investing at least 5-10% of monthly earnings into mutual funds/SIPs to build credit assets.")
        if income_stability_index < 0.70:
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
        
        digital_e = float(cashflow_features.get("digital_engagement", 0.5))

        from django.utils.translation import gettext as _
        
        # SHAP-style logic calculation
        repayment_pts = int(round(pd_factor))
        repayment_deficit = 45 - repayment_pts
        stability_pts = int(round(stability_factor))
        stability_deficit = 30 - stability_pts
        fraud_pts = int(round(fraud_factor))
        fraud_deficit = 15 - fraud_pts
        savings_pts = int(round(savings_factor))
        savings_deficit = 10 - savings_pts
        
        helped = [
            {"label": _("Repayment capacity (low default risk)"), "pts": f"+{repayment_pts} pts"},
            {"label": _("Income stability"), "pts": f"+{stability_pts} pts"},
            {"label": _("Clean profile (low fraud risk)"), "pts": f"+{fraud_pts} pts"},
            {"label": _("Savings cushion"), "pts": f"+{savings_pts} pts"}
        ]
        
        hurt = []
        if repayment_deficit > 0:
            hurt.append({"label": _("Repayment capacity (low default risk) below target"), "pts": f"-{repayment_deficit} pts"})
        if stability_deficit > 0:
            hurt.append({"label": _("Income stability below target"), "pts": f"-{stability_deficit} pts"})
        if fraud_deficit > 0:
            hurt.append({"label": _("High fraud risk indicators"), "pts": f"-{fraud_deficit} pts"})
        if savings_deficit > 0:
            hurt.append({"label": _("Low savings cushion"), "pts": f"-{savings_deficit} pts"})

        biz_explanation = {
            "Executive_Underwriting_Summary": f"Evaluated borrower. Alternative Credit Score: {ai_credit_score}/100. Decision: {decision_str}. Risk Grade: {risk_grade}. Decision Reason: {reason_str}.",
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
                "Income_Stability_Index": round(income_stability_index, 4),
                "Savings_Ratio": round(savings_ratio, 4),
                "Essential_Expense_Ratio": round(ess_r, 4),
                "Discretionary_Expense_Ratio": round(disc_r, 4)
            },
            "Score_Factors": {
                "helped": helped,
                "hurt": hurt
            }
        }

        key_strengths = []
        if income_stability_index >= 0.75:
            key_strengths.append(f"Highly stable income streams detected (Index: {income_stability_index:.2f}). Regular cash inflows indicate low income volatility, which supports strong repayment capability.")
        elif income_stability_index > 0.6:
            key_strengths.append("Consistent primary income source identified. Your month-on-month cash flow is predictable.")
            
        if fraud_prob < 0.05:
            key_strengths.append("Excellent digital footprint and extremely low fraud risk profile. Identity and transaction velocity align perfectly with trusted patterns.")
            
        if savings_ratio >= 0.30:
            key_strengths.append(f"Exceptional savings behavior ({savings_ratio:.1%} of net income). This robust surplus significantly boosts loan eligibility and provides an excellent safety net.")
        elif savings_ratio >= 0.15:
            key_strengths.append(f"Healthy savings buffer maintained ({savings_ratio:.1%} of net income). Demonstrates strong financial discipline and the ability to absorb unexpected expenses.")
            
        if foir < 0.20 and pd_prob < 0.3:
            key_strengths.append(f"Low existing debt obligations (FOIR: {foir:.1%}) resulting in strong repayment capacity for new credit facilities.")
            
        if not key_strengths:
            key_strengths.append("Consistent transaction activity and baseline profile stability observed across the statement period.")

        key_improvement_areas = []
        if pd_prob > 0.40:
            key_improvement_areas.append("Elevated probability of default risk flagged by AI model based on recent transaction velocity and account balance trends.")
            
        if savings_ratio < 0.05:
            key_improvement_areas.append(f"Critical: Monthly savings ratio is very low ({savings_ratio:.1%}). Needs immediate improvement to build a cash reserve and prevent reliance on short-term debt.")
        elif savings_ratio < 0.10:
            key_improvement_areas.append(f"Borderline savings ratio ({savings_ratio:.1%}). Try to optimize discretionary expenses to improve month-end surplus.")
            
        if expense_ratio > 0.85:
            key_improvement_areas.append(f"High expense-to-income ratio ({expense_ratio:.1%}) indicates tight month-to-month liquidity, leaving little room for new EMI payments.")
            
        if foir > 0.45:
            key_improvement_areas.append(f"Existing EMI and fixed obligations consume a significant portion of income (FOIR: {foir:.1%}). Consider consolidating or paying down existing debt.")
            
        if not key_improvement_areas:
            key_improvement_areas.append("No critical improvements required. Keep up the excellent financial behavior!")

        customer_explanation = {
            "Application_Status": decision_str,
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
            ] if decision_str == "APPROVED" else [
                "Our underwriting team will contact you to perform manual document review.",
                "Keep your latest salary slips or income tax returns ready if requested.",
                "Reach out to customer support if you have additional bank statement data."
            ] if decision_str == "REVIEW" else [
                "We cannot extend a credit offer at this time due to high risk indicators.",
                "Follow the actionable recommendations below to improve your cashflow metrics.",
                "You are eligible to re-apply in 90 days after improving your savings ratio."
            ]
        }
        
        return {
            "ai_credit_score": ai_credit_score,
            "fraud_probability": round(fraud_prob, 4),
            "probability_of_default": round(pd_prob, 4),
            "risk_grade": risk_grade,
            "underwriting_decision": decision_str,
            "decision_reason": reason_str,
            "max_approved_limit": max_approved_loan,
            "recommended_loan_amount": recommended_loan,
            "interest_rate": tier["base_rate"],
            "actionable_recommendations": categorized_recommendations,
            "business_explanation": biz_explanation,
            "customer_explanation": customer_explanation,
            "Business_Explanation": biz_explanation,
            "Customer_Explanation": customer_explanation,
            "Actionable_Recommendations": categorized_recommendations,
            "income_stability_index": round(income_stability_index, 4),
            "expense_ratio": round(expense_ratio, 4),
            "savings_ratio": round(savings_ratio, 4),
            "monthly_income_used": int(monthly_income)
        }
