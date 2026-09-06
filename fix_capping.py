import re
import random
import pandas as pd

def _cap_aa_transactions_and_recalc_balance(df: pd.DataFrame) -> pd.DataFrame:
    """If an Account Aggregator transaction amount exceeds 20,000, cap it to a random
    value between 2,000 and 10,000. Recalculates the running balance from the oldest
    transaction to ensure the math adds up and the closing balance never drops below zero.
    Also ensures average monthly income doesn't exceed 50k.
    """
    if df.empty:
        return df
        
    # Safely convert to datetime for accurate sorting
    if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
        date_strs = df["Date"].astype(str).str.strip()
        has_day_first = False
        for s in date_strs:
            parts = re.split(r"[-/]", s)
            if len(parts) >= 3 and parts[0].isdigit() and int(parts[0]) > 12:
                has_day_first = True
                break
        df["Date"] = pd.to_datetime(date_strs, format="mixed", dayfirst=has_day_first, errors="coerce")
        
    df = df.dropna(subset=["Date"])
    df = df.sort_values(by="Date").reset_index(drop=True)
    if df.empty:
        return df
    
    # Estimate the starting balance right before the first transaction
    first_row = df.iloc[0]
    running_balance = first_row["Closing Balance"] + first_row["Withdrawal Amount"] - first_row["Deposit Amount"]
    
    new_balances = []
    new_withdrawals = []
    new_deposits = []
    
    monthly_income_tracker = {}
    
    for idx, row in df.iterrows():
        withdrawal = abs(row["Withdrawal Amount"])
        deposit = abs(row["Deposit Amount"])
        
        dt = row["Date"]
        month_key = f"{dt.year}-{dt.month}" if pd.notnull(dt) else "unknown"
        current_month_income = monthly_income_tracker.get(month_key, 0)
        
        # Base capping for deposits
        if deposit > 20000:
            deposit = float(random.randint(2000, 10000))
            
        # Target max monthly income of ~45,000 to keep average safely below 50k
        if current_month_income + deposit > 45000:
            allowed = max(0.0, 45000.0 - current_month_income)
            if allowed > 0:
                deposit = min(deposit, allowed)
            else:
                deposit = float(random.randint(10, 500))
                
        monthly_income_tracker[month_key] = current_month_income + deposit
            
        # Cap withdrawals and ensure we never withdraw more than the available balance
        if withdrawal > 20000:
            capped = float(random.randint(2000, 10000))
            withdrawal = min(capped, running_balance + deposit)
        else:
            withdrawal = min(withdrawal, running_balance + deposit)
            
        running_balance = running_balance + deposit - withdrawal
        
        new_withdrawals.append(withdrawal)
        new_deposits.append(deposit)
        new_balances.append(running_balance)
        
    df["Withdrawal Amount"] = new_withdrawals
    df["Deposit Amount"] = new_deposits
    df["Closing Balance"] = new_balances
    
    return df
