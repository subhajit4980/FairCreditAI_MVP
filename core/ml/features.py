import io
import re
import pandas as pd
import numpy as np
from datetime import datetime
from typing import BinaryIO, Optional

# Synonyms for columns in Indian retail bank exports
DATE_KEYS = ["txn date", "transaction date", "date", "value date", "posting date"]
DEBIT_KEYS = ["withdrawal amt", "withdrawal", "debit amt", "debit", "dr amount", "dr"]
CREDIT_KEYS = ["deposit amt", "deposit", "credit amt", "credit", "cr amount", "cr"]
DESC_KEYS = ["description", "narration", "particulars", "transaction details", "details", "remarks"]
BAL_KEYS = ["closing balance", "balance", "running balance"]

# Heuristic keywords for baseline algorithms compatibility
BOUNCE_KEYWORDS = ["bounce", "return", "fail", "reject", "insufficient", "rtn", "rev"]
UPI_KEYWORDS = ["upi", "imps", "neft", "rtgs", "gpay", "phonepe", "paytm", "googlepay"]

def categorize_narration(narr: str) -> str:
    if not isinstance(narr, str):
        return "OTHERS"
    narr_upper = narr.upper()
    if re.search(r"SALARY|NETSALARY|PAYROLL", narr_upper):
        return "SALARY"
    if re.search(r"ZERODHA|GROWW|MFAUTOPAY|PAYTMMONEY|MUTUAL|SIP", narr_upper):
        return "INVESTMENTS_SIP"
    if re.search(r"BESCOM|TATAPOWER|AIRTEL|RECHARGE|UTILITY|BILL", narr_upper):
        return "UTILITIES_BILLS"
    if re.search(r"BLINKIT|ZEPTO|BIGBASKET|GROCERY|SUPERMARKET", narr_upper):
        return "GROCERY"
    if re.search(r"SWIGGY|ZOMATO|RESTAURANT|FOOD|CAFE", narr_upper):
        return "FOOD_DELIVERY"
    if re.search(r"AMAZON|FLIPKART|MYNTRA|SHOPPING", narr_upper):
        return "ECOMMERCE_SHOPPING"
    if re.search(r"UBER|OLA|IRCTC|FASTAG|TRAVEL", narr_upper):
        return "TRAVEL_MOBILITY"
    if re.search(r"ATM-WDL|CASH|NFS", narr_upper):
        return "ATM_CASH"
    if re.search(r"EMI|LOAN|BAJAJFINSERV|HOMEEMI|PERSONALEMI", narr_upper):
        return "SHADOW_EMI"
    return "OTHERS"

def parse_to_dataframe(file_path_or_stream, filename: str) -> Optional[pd.DataFrame]:
    """Parse CSV or Excel file into a standardized DataFrame."""
    name = filename.lower()
    
    if name.endswith((".xlsx", ".xls")):
        # Excel
        if name.endswith(".xlsx"):
            from openpyxl import load_workbook
            wb = load_workbook(file_path_or_stream, read_only=True, data_only=True)
            ws = wb.active
            rows = []
            for row in ws.iter_rows(values_only=True):
                rows.append([str(v) if v is not None else "" for v in row])
        else:
            import xlrd
            wb = xlrd.open_workbook(file_contents=file_path_or_stream.read() if hasattr(file_path_or_stream, "read") else open(file_path_or_stream, "rb").read())
            sheet = wb.sheet_by_index(0)
            rows = []
            for r in range(sheet.nrows):
                rows.append([str(sheet.cell_value(r, c)) for c in range(sheet.ncols)])
        
        if not rows:
            return None
            
        df = pd.DataFrame(rows[1:], columns=rows[0])
    else:
        # CSV
        if hasattr(file_path_or_stream, "read"):
            raw = file_path_or_stream.read()
            # Restore pointer if stream
            if hasattr(file_path_or_stream, "seek"):
                file_path_or_stream.seek(0)
        else:
            with open(file_path_or_stream, "rb") as f:
                raw = f.read()
                
        if isinstance(raw, bytes):
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                text = raw.decode("latin-1", errors="replace")
        else:
            text = raw
            
        lines = text.splitlines()
        header_idx = 0
        for i, line in enumerate(lines[:30]):
            low = line.lower()
            if any(d in low for d in DATE_KEYS) and (
                any(d in low for d in DEBIT_KEYS) or any(c in low for c in CREDIT_KEYS)
            ):
                header_idx = i
                break
        
        body = "\n".join(lines[header_idx:])
        df = pd.read_csv(io.StringIO(body))

    # Rename columns to standard ones
    df.columns = [str(c).lower().strip() for c in df.columns]
    
    col_mapping = {}
    for col in df.columns:
        if any(k in col for k in DATE_KEYS) and "value" not in col:
            col_mapping[col] = "Date"
        elif any(k in col for k in DEBIT_KEYS):
            col_mapping[col] = "Withdrawal Amount"
        elif any(k in col for k in CREDIT_KEYS):
            col_mapping[col] = "Deposit Amount"
        elif any(k in col for k in BAL_KEYS):
            col_mapping[col] = "Closing Balance"
        elif any(k in col for k in DESC_KEYS):
            col_mapping[col] = "Narration"
            
    df = df.rename(columns=col_mapping)
    required = ["Date", "Withdrawal Amount", "Deposit Amount", "Closing Balance", "Narration"]
    
    # Fill missing columns with default/zero
    for r in required:
        if r not in df.columns:
            if r == "Narration":
                df[r] = "OTHERS"
            else:
                df[r] = 0.0
                
    return df[required]

def extract_advanced_features(df: pd.DataFrame) -> dict:
    """Run full feature engineering on standard DataFrame."""
    tx = df.copy()
    for col in ["Withdrawal Amount", "Deposit Amount", "Closing Balance"]:
        if col in tx.columns:
            if tx[col].dtype == object:
                tx[col] = tx[col].astype(str).str.replace(r"[^\d.\-]", "", regex=True)
            tx[col] = pd.to_numeric(tx[col], errors="coerce").fillna(0.0)
        
    tx["Date"] = pd.to_datetime(tx["Date"], errors="coerce")
    tx = tx.dropna(subset=["Date"]).sort_values("Date")
    
    if tx.empty:
        return {}
        
    tx["year_month"] = tx["Date"].dt.to_period("M").astype(str)
    tx["is_debit"] = tx["Withdrawal Amount"].gt(0)
    tx["is_credit"] = tx["Deposit Amount"].gt(0)
    tx["debit_amt"] = np.where(tx["is_debit"], tx["Withdrawal Amount"], 0.0)
    tx["credit_amt"] = np.where(tx["is_credit"], tx["Deposit Amount"], 0.0)
    tx["amount"] = np.where(tx["is_credit"], tx["Deposit Amount"], tx["Withdrawal Amount"])
    tx["category_parsed"] = tx["Narration"].apply(categorize_narration)
    
    # Monthly aggregations
    monthly = tx.groupby("year_month").agg(
        monthly_income=("credit_amt", "sum"),
        monthly_expense=("debit_amt", "sum")
    ).reset_index()
    monthly["monthly_savings"] = monthly.monthly_income - monthly.monthly_expense
    
    total_txns = len(tx)
    period_months = max(1.0, float(tx["year_month"].nunique()))
    
    # Aggregates
    transaction_frequency = float(total_txns / period_months)
    average_transaction_amount = float(tx["amount"].mean())
    median_transaction_amount = float(tx["amount"].median())
    largest_deposit = float(tx["Deposit Amount"].max())
    largest_withdrawal = float(tx["Withdrawal Amount"].max())
    average_balance = float(tx["Closing Balance"].mean())
    minimum_balance = float(tx["Closing Balance"].min())
    maximum_balance = float(tx["Closing Balance"].max())
    balance_variance = float(tx["Closing Balance"].var()) if total_txns > 1 else 0.0
    
    std_amount = tx["amount"].std(ddof=0) if total_txns else 0.0
    mean_amount = tx["amount"].mean() if total_txns else 0.0
    transaction_consistency = float(1 / (1 + std_amount / (mean_amount + 1)))
    
    average_monthly_income = float(monthly["monthly_income"].mean())
    average_monthly_expense = float(monthly["monthly_expense"].mean())
    monthly_savings = float(monthly["monthly_savings"].mean())
    
    std_income = monthly["monthly_income"].std(ddof=0) if len(monthly) >= 2 else 0.0
    mean_income = monthly["monthly_income"].mean()
    income_consistency = float(1 / (1 + std_income / (mean_income + 1))) if mean_income > 0 else 0.7
    
    std_expense = monthly["monthly_expense"].std(ddof=0) if len(monthly) >= 2 else 0.0
    mean_expense = monthly["monthly_expense"].mean()
    expense_stability = float(1 / (1 + std_expense / (mean_expense + 1))) if mean_expense > 0 else 0.7
    
    total_income = float(tx["credit_amt"].sum())
    total_expense = float(tx["debit_amt"].sum())
    
    essential_expense = float(tx.loc[tx["category_parsed"].isin(["UTILITIES_BILLS", "GROCERY"]), "debit_amt"].sum())
    discretionary_expense = float(tx.loc[tx["category_parsed"].isin(["FOOD_DELIVERY", "ECOMMERCE_SHOPPING", "TRAVEL_MOBILITY"]), "debit_amt"].sum())
    atm_withdrawals = float(tx.loc[tx["category_parsed"] == "ATM_CASH", "debit_amt"].sum())
    emi_payments = float(tx.loc[tx["category_parsed"] == "SHADOW_EMI", "debit_amt"].sum())
    investment_amount = float(tx.loc[tx["category_parsed"] == "INVESTMENTS_SIP", "debit_amt"].sum())
    salary_credits = float(tx.loc[tx["category_parsed"] == "SALARY", "credit_amt"].sum())
    
    expense_ratio = float(total_expense / total_income) if total_income > 0 else 1.0
    savings_ratio = float(monthly_savings / average_monthly_income) if average_monthly_income > 0 else 0.0
    
    essential_expense_ratio = float(essential_expense / total_expense) if total_expense > 0 else 0.0
    discretionary_expense_ratio = float(discretionary_expense / total_expense) if total_expense > 0 else 0.0
    atm_cash_ratio = float(atm_withdrawals / total_expense) if total_expense > 0 else 0.0
    investment_ratio = float(investment_amount / total_income) if total_income > 0 else 0.0
    salary_ratio = float(salary_credits / total_income) if total_income > 0 else 0.0
    
    financial_buffer = float(max(0.0, minimum_balance) / average_monthly_expense) if average_monthly_expense > 0 else 0.0
    income_stability_index = float(income_consistency * 0.6 + expense_stability * 0.4)
    
    # Heuristics for baseline algorithm compatibility
    bounces = 0
    upi_txns = 0
    for idx, row in tx.iterrows():
        desc = str(row["Narration"]).lower()
        if any(k in desc for k in BOUNCE_KEYWORDS):
            bounces += 1
        if any(k in desc for k in UPI_KEYWORDS):
            upi_txns += 1
            
    distinct_counterparties = len(tx["Narration"].astype(str).str.lower().str.split().str[:4].str.join(" ").dropna().unique())
    
    # 0..1 versions of payment timeliness & digital engagement
    bounces_per_month = bounces / period_months
    payment_timeliness = max(0.0, min(1.0, 0.95 - bounces_per_month * 0.20))
    bounce_rate = min(1.0, bounces / total_txns) if total_txns else 0.0
    
    upi_share = upi_txns / total_txns if total_txns else 0.0
    diversity = min(1.0, distinct_counterparties / 30.0)
    digital_engagement = max(0.0, min(1.0, 0.6 * upi_share + 0.4 * diversity))
    
    monthly_trends = []
    for _, row in monthly.iterrows():
        monthly_trends.append({
            "month": str(row["year_month"]),
            "credit": round(float(row["monthly_income"]), 2),
            "debit": round(float(row["monthly_expense"]), 2)
        })
    
    return {
        "monthly_trends": monthly_trends,
        # Core 21 cashflow features
        "transaction_frequency": round(transaction_frequency, 1),
        "average_transaction_amount": round(average_transaction_amount, 2),
        "median_transaction_amount": round(median_transaction_amount, 2),
        "largest_deposit": round(largest_deposit, 2),
        "largest_withdrawal": round(largest_withdrawal, 2),
        "average_balance": round(average_balance, 2),
        "minimum_balance": round(minimum_balance, 2),
        "maximum_balance": round(maximum_balance, 2),
        "balance_variance": round(balance_variance, 2),
        "transaction_consistency": round(transaction_consistency, 4),
        "average_monthly_income": round(average_monthly_income, 2),
        "income_consistency": round(income_consistency, 4),
        "average_monthly_expense": round(average_monthly_expense, 2),
        "monthly_savings": round(monthly_savings, 2),
        "expense_stability": round(expense_stability, 4),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "expense_ratio": round(expense_ratio, 4),
        "savings_ratio": round(savings_ratio, 4),
        "financial_buffer": round(financial_buffer, 4),
        "income_stability_index": round(income_stability_index, 4),
        
        # Intermediate / Diagnostic columns
        "essential_expense": round(essential_expense, 2),
        "discretionary_expense": round(discretionary_expense, 2),
        "atm_withdrawals": round(atm_withdrawals, 2),
        "emi_payments": round(emi_payments, 2),
        "investment_amount": round(investment_amount, 2),
        "salary_credits": round(salary_credits, 2),
        "essential_expense_ratio": round(essential_expense_ratio, 4),
        "discretionary_expense_ratio": round(discretionary_expense_ratio, 4),
        "atm_cash_ratio": round(atm_cash_ratio, 4),
        "investment_ratio": round(investment_ratio, 4),
        "salary_ratio": round(salary_ratio, 4),
        
        # Compatibility features
        "payment_timeliness": round(payment_timeliness, 3),
        "bounce_rate": round(bounce_rate, 4),
        "digital_engagement": round(digital_engagement, 3),
        
        # Extra stats for database parsed notes
        "txn_count": total_txns,
        "period_months": float(period_months),
        "monthly_avg_inflow": round(average_monthly_income, 2),
        "monthly_avg_outflow": round(average_monthly_expense, 2),
        "bounces": bounces,
        "upi_txns": upi_txns,
        "distinct_counterparties": distinct_counterparties,
    }
