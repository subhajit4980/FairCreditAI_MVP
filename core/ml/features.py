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

def get_counterparty_signature(narr: str) -> str:
    if not isinstance(narr, str):
        return "UNKNOWN"
    narr = narr.upper()
    # Extract UPI VPA if present
    upi_match = re.search(r"([A-Z0-9.\-_]+@[A-Z]{2,})", narr)
    if upi_match:
        return upi_match.group(1)
    # Clean special characters and keep the first two significant words
    cleaned = re.sub(r"[^A-Z\s]", " ", narr)
    words = [w for w in cleaned.split() if len(w) > 2]
    return " ".join(words[:2]) if words else "OTHERS"

def parse_to_dataframe(file_path_or_stream, filename: str) -> Optional[pd.DataFrame]:
    """Parse CSV or Excel file into a standardized DataFrame."""
    name = filename.lower()
    
    if name.endswith((".xlsx", ".xls")):
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
        if hasattr(file_path_or_stream, "read"):
            raw = file_path_or_stream.read()
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
            
    # Fallback: if 'Date' wasn't mapped, but there is some date column (like value date), map it
    if "Date" not in col_mapping.values():
        for col in df.columns:
            if any(k in col for k in DATE_KEYS):
                col_mapping[col] = "Date"
                break

    df = df.rename(columns=col_mapping)

    required = ["Date", "Withdrawal Amount", "Deposit Amount", "Closing Balance", "Narration"]
    
    for r in required:
        if r not in df.columns:
            if r == "Narration":
                df[r] = "OTHERS"
            else:
                df[r] = 0.0
                
    return df[required]

def extract_advanced_features(df: pd.DataFrame) -> dict:
    """Run production-grade credit and fraud feature engineering on standard DataFrame."""
    tx = df.copy()
    for col in ["Withdrawal Amount", "Deposit Amount", "Closing Balance"]:
        if col in tx.columns:
            if not pd.api.types.is_numeric_dtype(tx[col]):
                tx[col] = tx[col].astype(str).str.replace(r"[^\d.\-]", "", regex=True)
            tx[col] = pd.to_numeric(tx[col], errors="coerce").fillna(0.0)
        
    # Auto-detect date format from the series to resolve ambiguous formats (like 4/1/2026)
    date_strs = tx["Date"].astype(str).str.strip()
    has_day_first = False
    has_month_first = False
    for val in date_strs:
        if not val or val.lower() in ["nan", "nat", ""]:
            continue
        parts = re.split(r"[/\- ]", val)
        if len(parts) >= 2:
            try:
                p1 = int(float(parts[0]))
                p2 = int(float(parts[1]))
                if p1 < 100 and p2 < 100:
                    if p1 > 12 and p2 <= 12:
                        has_day_first = True
                        break
                    if p2 > 12 and p1 <= 12:
                        has_month_first = True
                        break
            except ValueError:
                continue

    if has_month_first:
        tx["Date"] = pd.to_datetime(date_strs, dayfirst=False, errors="coerce")
    elif has_day_first:
        tx["Date"] = pd.to_datetime(date_strs, dayfirst=True, errors="coerce")
    else:
        tx["Date"] = pd.to_datetime(date_strs, errors="coerce")
        
    tx = tx.dropna(subset=["Date"]).sort_values("Date")
    
    if tx.empty:
        return {}
        
    tx["year_month"] = tx["Date"].dt.to_period("M").astype(str)
    tx["is_debit"] = tx["Withdrawal Amount"].gt(0)
    tx["is_credit"] = tx["Deposit Amount"].gt(0)
    
    desc_upper = tx["Narration"].astype(str).str.upper()
    
    # 1. ANTI-GAMING SANITIZATION
    # A. Exclude P2P Self-Transfers & Wallet Loads
    is_self = desc_upper.str.contains(
        r"\bSELF\b|\bOWN A/C\b|\bOWN ACCOUNT\b|\bINTERNAL\b|\bMY OWN\b|\bWALLET LOAD\b|\bTO WALLET\b",
        regex=True
    )
    
    # B. Exclude Loan Disbursements from Income credits
    is_loan = desc_upper.str.contains(
        r"LOAN|DISB|FINANCE|DISBURSEMENT|CREDIT LINE|ADVANCE|PAYLATER|CASHE|KREDITBEE|LEND",
        regex=True
    )
    
    # C. Identify Cash Deposits to discount
    is_cash_dep = desc_upper.str.contains(r"CASH DEP|CASH DEPOSIT|CDM|CASH IN", regex=True)
    
    # Compute base credit amounts
    raw_credit = tx["Deposit Amount"].values
    sanitized_credit = np.copy(raw_credit)
    
    # Apply self-transfer & loan disbursement exclusions
    sanitized_credit[is_self] = 0.0
    sanitized_credit[is_loan] = 0.0
    
    # Apply 50% discount to Cash Deposits
    sanitized_credit[is_cash_dep] = sanitized_credit[is_cash_dep] * 0.50
    
    # D. Winsorize Large Credit Inflow Spikes (> 99th Percentile with a ₹50,000 floor)
    credit_txns = sanitized_credit[sanitized_credit > 0]
    winsorize_limit = float(np.percentile(credit_txns, 99)) if len(credit_txns) > 0 else 50000.0
    winsorize_limit = max(50000.0, winsorize_limit)
    sanitized_credit[sanitized_credit > winsorize_limit] = winsorize_limit
    
    # Apply self-transfer exclusions to debits
    raw_debit = tx["Withdrawal Amount"].values
    sanitized_debit = np.copy(raw_debit)
    sanitized_debit[is_self] = 0.0
    
    tx["credit_amt"] = sanitized_credit
    tx["debit_amt"] = sanitized_debit
    tx["amount"] = np.where(tx["is_credit"], sanitized_credit, sanitized_debit)
    tx["category_parsed"] = tx["Narration"].apply(categorize_narration)
    
    # Monthly aggregations
    monthly = tx.groupby("year_month").agg(
        monthly_income=("credit_amt", "sum"),
        monthly_expense=("debit_amt", "sum"),
        raw_income=("Deposit Amount", "sum"),
        raw_expense=("Withdrawal Amount", "sum")
    ).reset_index()
    monthly["monthly_savings"] = monthly.monthly_income - monthly.monthly_expense
    print("Monthly income and expense aggregation completed for Customer ID:\n", monthly)

    total_txns = len(tx)
    period_months = max(1.0, float(tx["year_month"].nunique()))
    days_range = (tx["Date"].max() - tx["Date"].min()).days
    
    # 2. FEATURE EXTRACTION
    average_monthly_income = float(monthly["monthly_income"].mean())
    average_monthly_expense = float(monthly["monthly_expense"].mean())
    monthly_savings = float(monthly["monthly_savings"].mean())
    
    # Weighted Income Recurrence Index (I_RI)
    monthly_recurrence = []
    tx["month_str"] = tx["Date"].dt.to_period("M").astype(str)
    for _, group in tx.groupby("month_str"):
        credit_days = group.loc[group["credit_amt"] > 0, "Date"].dt.date.nunique()
        monthly_recurrence.append(min(1.0, credit_days / 4.0))
    income_recurrence = float(np.mean(monthly_recurrence)) if monthly_recurrence else 0.70
    
    # Income Concentration Coefficient (I_CC)
    credit_tx = tx[tx["is_credit"] & ~is_self & ~is_loan].copy()
    if not credit_tx.empty:
        credit_tx["counterparty"] = credit_tx["Narration"].apply(get_counterparty_signature)
        grouped = credit_tx.groupby("counterparty")["credit_amt"].sum()
        total_sanitized = grouped.sum()
        if total_sanitized > 0:
            proportions = grouped / total_sanitized
            hhi = float((proportions ** 2).sum())
            income_concentration = 1.0 - hhi
        else:
            income_concentration = 0.0
    else:
        income_concentration = 0.0
        
    # Average Daily Balance (ADB)
    try:
        daily_series = tx.set_index("Date")["Closing Balance"].resample("D").last().ffill()
        average_daily_balance = float(daily_series.mean()) if not daily_series.empty else 0.0
        
        # Balance Retention Ratio (B_RR)
        balance_retention_ratio = (
            min(2.0, average_daily_balance / average_monthly_income)
            if average_monthly_income > 0
            else 0.0
        )
        # Low Balance Frequency (L_BF)
        low_bal_days = (daily_series < 500.0).sum() if not daily_series.empty else 0
        total_days = len(daily_series) if not daily_series.empty else 1
        low_balance_frequency = float(low_bal_days / total_days)
    except Exception:
        # Fallback if resample fails due to duplicate index or format issues
        average_daily_balance = float(tx["Closing Balance"].mean())
        balance_retention_ratio = min(2.0, average_daily_balance / average_monthly_income) if average_monthly_income > 0 else 0.0
        low_balance_frequency = float((tx["Closing Balance"] < 500.0).sum() / len(tx))
        
    # Exclude self-transfer volume for HHI & spends
    total_income = float(tx["credit_amt"].sum())
    total_expense = float(tx["debit_amt"].sum())
    
    # Categorized expenditures
    essential_expense = float(tx.loc[tx["category_parsed"].isin(["UTILITIES_BILLS", "GROCERY"]), "debit_amt"].sum())
    discretionary_expense = float(tx.loc[tx["category_parsed"].isin(["FOOD_DELIVERY", "ECOMMERCE_SHOPPING", "TRAVEL_MOBILITY"]), "debit_amt"].sum())
    emi_payments = float(tx.loc[tx["category_parsed"] == "SHADOW_EMI", "debit_amt"].sum())
    
    # Ratios
    savings_ratio = float(monthly_savings / average_monthly_income) if average_monthly_income > 0 else 0.0
    foir = (emi_payments / period_months) / (average_monthly_income + 1)
    discretionary_expense_ratio = float(discretionary_expense / total_expense) if total_expense > 0 else 0.0
    
    # Bounces & Mandates
    bounces = 0
    upi_txns = 0
    for _, row in tx.iterrows():
        desc = str(row["Narration"]).lower()
        if any(k in desc for k in BOUNCE_KEYWORDS):
            bounces += 1
        if any(k in desc for k in UPI_KEYWORDS):
            upi_txns += 1
            
    bounces_per_month = bounces / period_months
    payment_timeliness = max(0.0, min(1.0, 1.0 - bounces_per_month * 0.20))
    bounce_rate = min(1.0, bounces / total_txns) if total_txns else 0.0
    
    # Digital Transactions Breadth & Spend Diversity
    distinct_counterparties = len(tx["Narration"].astype(str).str.lower().str.split().str[:4].str.join(" ").dropna().unique())
    counterparty_breadth = min(1.0, distinct_counterparties / 30.0)
    
    # Self-Transfer Fraud checks
    self_transfer_credits = tx.loc[is_self & tx["is_credit"], "Deposit Amount"].sum()
    total_raw_credits = tx["Deposit Amount"].sum()
    self_transfer_ratio = float(self_transfer_credits / total_raw_credits) if total_raw_credits > 0 else 0.0

    # Count & amount removed calculations
    is_credit = tx["is_credit"]
    is_debit = tx["is_debit"]
    
    self_cred_mask = is_self & is_credit
    self_deb_mask = is_self & is_debit
    loan_cred_mask = is_loan & is_credit & ~is_self
    cash_cred_mask = is_cash_dep & is_credit & ~is_self & ~is_loan
    
    # Winsorization details
    pre_winsorized = np.copy(raw_credit)
    pre_winsorized[is_self] = 0.0
    pre_winsorized[is_loan] = 0.0
    pre_winsorized[is_cash_dep] = pre_winsorized[is_cash_dep] * 0.50
    
    winsorized_mask = (pre_winsorized > winsorize_limit) & (pre_winsorized > 0)
    winsorized_diff = np.maximum(0.0, pre_winsorized - sanitized_credit)
    
    sanitization_stats = {
        "self_transfer_credits_count": int(self_cred_mask.sum()),
        "self_transfer_credits_amount": round(float(tx.loc[self_cred_mask, "Deposit Amount"].sum()), 2),
        "self_transfer_debits_count": int(self_deb_mask.sum()),
        "self_transfer_debits_amount": round(float(tx.loc[self_deb_mask, "Withdrawal Amount"].sum()), 2),
        "loan_credits_count": int(loan_cred_mask.sum()),
        "loan_credits_amount": round(float(tx.loc[loan_cred_mask, "Deposit Amount"].sum()), 2),
        "cash_deposit_credits_count": int(cash_cred_mask.sum()),
        "cash_deposit_credits_amount": round(float(tx.loc[cash_cred_mask, "Deposit Amount"].sum() * 0.5), 2),
        "winsorized_credits_count": int(winsorized_mask.sum()),
        "winsorized_credits_amount": round(float(winsorized_diff.sum()), 2),
    }
    
    monthly_trends = []
    for _, row in monthly.iterrows():
        monthly_trends.append({
            "month": str(row["year_month"]),
            "credit": round(float(row["monthly_income"]), 2),
            "debit": round(float(row["monthly_expense"]), 2),
            "raw_credit": round(float(row["raw_income"]), 2),
            "raw_debit": round(float(row["raw_expense"]), 2)
        })
        
    return {
        "monthly_trends": monthly_trends,
        "sanitization_stats": sanitization_stats,
        "txn_count": total_txns,
        "period_months": float(period_months),
        "days_range": days_range,
        "bounces": bounces,
        "bounces_per_month": round(bounces_per_month, 2),
        "self_transfer_ratio": round(self_transfer_ratio, 4),
        
        # Production Features Set
        "average_monthly_income": round(average_monthly_income, 2),
        "average_monthly_expense": round(average_monthly_expense, 2),
        "monthly_savings": round(monthly_savings, 2),
        "savings_ratio": round(savings_ratio, 4),
        "income_recurrence": round(income_recurrence, 4),
        "income_concentration": round(income_concentration, 4),
        "average_daily_balance": round(average_daily_balance, 2),
        "balance_retention_ratio": round(balance_retention_ratio, 4),
        "low_balance_frequency": round(low_balance_frequency, 4),
        "foir": round(foir, 4),
        "discretionary_expense_ratio": round(discretionary_expense_ratio, 4),
        "payment_timeliness": round(payment_timeliness, 4),
        "counterparty_breadth": round(counterparty_breadth, 4),
        "bounce_rate": round(bounce_rate, 4),
        
        # Compatibility legacy keys (dummy mapping for models consistency)
        "transaction_frequency": round(total_txns / period_months, 1),
        "average_transaction_amount": round(tx["amount"].mean() if total_txns else 0.0, 2),
        "median_transaction_amount": round(tx["amount"].median() if total_txns else 0.0, 2),
        "largest_deposit": round(tx["Deposit Amount"].max(), 2),
        "largest_withdrawal": round(tx["Withdrawal Amount"].max(), 2),
        "average_balance": round(average_daily_balance, 2),
        "minimum_balance": round(tx["Closing Balance"].min(), 2),
        "maximum_balance": round(tx["Closing Balance"].max(), 2),
        "balance_variance": round(tx["Closing Balance"].var() if total_txns > 1 else 0.0, 2),
        "transaction_consistency": round(0.85, 4),
        "expense_stability": round(0.85, 4),
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "expense_ratio": round(total_expense / total_income if total_income > 0 else 1.0, 4),
        "financial_buffer": round(max(0.0, tx["Closing Balance"].min()) / (average_monthly_expense + 1), 4),
        "income_stability_index": round(income_recurrence * 0.6 + 0.85 * 0.4, 4),
        "essential_expense": round(essential_expense, 2),
        "discretionary_expense": round(discretionary_expense, 2),
        "atm_withdrawals": round(tx.loc[tx["category_parsed"] == "ATM_CASH", "debit_amt"].sum(), 2),
        "emi_payments": round(emi_payments, 2),
        "investment_amount": round(tx.loc[tx["category_parsed"] == "INVESTMENTS_SIP", "debit_amt"].sum(), 2),
        "salary_credits": round(tx.loc[tx["category_parsed"] == "SALARY", "credit_amt"].sum(), 2),
        "essential_expense_ratio": round(essential_expense / total_expense if total_expense > 0 else 0.0, 4),
        "atm_cash_ratio": round(tx.loc[tx["category_parsed"] == "ATM_CASH", "debit_amt"].sum() / total_expense if total_expense > 0 else 0.0, 4),
        "investment_ratio": round(tx.loc[tx["category_parsed"] == "INVESTMENTS_SIP", "debit_amt"].sum() / total_income if total_income > 0 else 0.0, 4),
        "salary_ratio": round(tx.loc[tx["category_parsed"] == "SALARY", "credit_amt"].sum() / total_income if total_income > 0 else 0.0, 4),
        "digital_engagement": round(upi_txns / total_txns if total_txns else 0.0, 3),
        "upi_txns": upi_txns,
        "distinct_counterparties": distinct_counterparties,
    }
