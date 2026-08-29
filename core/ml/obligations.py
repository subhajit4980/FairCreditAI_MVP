import re
import pandas as pd
import numpy as np
from datetime import datetime

def get_day_suffix(day: int) -> str:
    """Return day of month with standard English ordinal suffix (1st, 2nd, 3rd, 4th, etc.)."""
    if 11 <= day <= 13:
        return f"{day}th"
    last_digit = day % 10
    if last_digit == 1:
        return f"{day}st"
    elif last_digit == 2:
        return f"{day}nd"
    elif last_digit == 3:
        return f"{day}rd"
    return f"{day}th"

def clean_narration_signature(narr: str) -> str:
    """Clean transaction narration to a stable signature by removing transaction IDs, dates, and noise."""
    if not isinstance(narr, str):
        return "UNKNOWN"
    s = narr.upper()
    
    # Remove dates (e.g. 12-08-2026, 12/08/26, 12-AUG-2026)
    s = re.sub(r"\b\d{1,2}[/\-](?:\d{1,2}|[A-Z]{3,4})[/\-]\d{2,4}\b", " ", s)
    s = re.sub(r"\b\d{4}[/\-]\d{1,2}[/\-]\d{1,2}\b", " ", s)
    
    # Remove numbers and transaction references (e.g. UPI txn IDs, IMPS refs)
    s = re.sub(r"\b[A-Z0-9]*\d+[A-Z0-9]*\b", " ", s)
    
    # Remove special chars and non-alphanumeric chars
    s = re.sub(r"[^A-Z\s]", " ", s)
    
    # Remove common transaction noise keywords
    noise = {
        "UPI", "IMPS", "NEFT", "RTGS", "ACH", "NACH", "DR", "CR", "TXN", "TRF", 
        "TRANSFER", "DEBIT", "CREDIT", "MB", "NET", "PAY", "PMT", "COMM", 
        "CHARGES", "FEE", "REFUND", "SETTLEMENT", "DEPOSITED", "WITHDRAWAL",
        "TO", "FROM", "BY", "FOR", "ON", "AT", "IN", "OUT", "OF"
    }
    words = [w for w in s.split() if len(w) > 2 and w not in noise]
    return " ".join(words[:3]) if words else "GENERAL OBLIGATION"

def extract_lender_name(narr: str) -> str:
    """Map narrations to clean, standardized lender names."""
    upper = narr.upper()
    lenders = {
        "BAJAJ": "Bajaj Finance",
        "HDFC": "HDFC Bank",
        "SBI": "SBI Finance",
        "ICICI": "ICICI Bank",
        "KREDITBEE": "KreditBee",
        "CASHE": "Cashe",
        "CHOLA": "Cholamandalam Finance",
        "MUTHOOT": "Muthoot Finance",
        "L&T": "L&T Finance",
        "IDFC": "IDFC First Bank",
        "AXIS": "Axis Bank",
        "LIC": "LIC Housing Finance",
        "HOME CREDIT": "Home Credit",
        "PAYME": "PayMe India",
        "MONEYTAP": "MoneyTap",
        "EARLYSALARY": "Fibe (EarlySalary)",
        "FIBE": "Fibe",
        "NAVIME": "Navi Finance",
        "NAVI": "Navi Finance",
        "ZOPMART": "ZestMoney",
        "ZEST": "ZestMoney",
        "KOTAK": "Kotak Mahindra Bank",
        "BOB": "Bank of Baroda",
        "PNB": "Punjab National Bank",
    }
    for k, v in lenders.items():
        if k in upper:
            return v
            
    # Fallback to a cleaner name from the signature
    words = [w for w in upper.split() if w not in ("ACH", "NACH", "DR", "CR", "UPI", "DEBIT", "CREDIT", "DR.")]
    if words:
        return " ".join(words[:2]).title()
    return "Lender Partner"

def detect_obligations(df: pd.DataFrame) -> list:
    """Analyzes a bank statement dataframe to detect recurring EMI/loan obligations and compile timelines/bounces."""
    if df is None or df.empty:
        return []
        
    required = ["Date", "Withdrawal Amount", "Narration"]
    for r in required:
        if r not in df.columns:
            return []
            
    # Copy and filter debit transactions
    debits = df[df["Withdrawal Amount"] > 0].copy()
    if debits.empty:
        return []
        
    # Ensure Date is datetime
    debits["Date"] = pd.to_datetime(debits["Date"])
    
    # Compute signature
    debits["signature"] = debits["Narration"].apply(clean_narration_signature)
    
    # Identify bounce transactions
    bounce_keywords = ["bounce", "return", "fail", "insufficient", "rtn", "rev"]
    bounce_mask = df["Narration"].astype(str).str.lower().str.contains("|".join(bounce_keywords))
    bounces_df = df[bounce_mask & (df["Withdrawal Amount"] > 0)].copy()
    bounces_df["Date"] = pd.to_datetime(bounces_df["Date"])
    
    detected_obligations = []
    
    # Group by signature
    for sig, sig_group in debits.groupby("signature"):
        sig_group = sig_group.sort_values("Date")
        tx_list = sig_group.to_dict("records")
        
        # Cluster transactions by amount (within 8% variation tolerance)
        clusters = []
        for tx in tx_list:
            matched = False
            for cluster in clusters:
                median_amt = np.median([c["Withdrawal Amount"] for c in cluster])
                if abs(tx["Withdrawal Amount"] - median_amt) / median_amt <= 0.08:
                    cluster.append(tx)
                    matched = True
                    break
            if not matched:
                clusters.append([tx])
                
        for cluster in clusters:
            n = len(cluster)
            # Require at least 2 payments to form a repeating pattern
            if n < 2:
                continue
                
            dates = [tx["Date"] for tx in cluster]
            amounts = [tx["Withdrawal Amount"] for tx in cluster]
            median_amount = float(np.median(amounts))
            
            # Calculate intervals
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, n)]
            mean_interval = float(np.mean(intervals))
            
            # Determine recurring frequency
            is_recurring = False
            frequency = "Monthly"
            
            if 20 <= mean_interval <= 40:
                is_recurring = True
                frequency = "Monthly"
            elif 5 <= mean_interval <= 12:
                is_recurring = True
                frequency = "Weekly"
            elif 12 <= mean_interval <= 18:
                is_recurring = True
                frequency = "Bi-weekly"
            elif 75 <= mean_interval <= 105:
                is_recurring = True
                frequency = "Quarterly"
            else:
                # Check for loan keywords in narration with slightly looser interval due to missed payments
                narr_has_loan = any(k in sig.upper() for k in ["EMI", "LOAN", "LEND", "BAJAJ", "CHOLA", "MUTHOOT", "FINANCE", "KREDITBEE"])
                if narr_has_loan and 20 <= mean_interval <= 70:
                    is_recurring = True
                    frequency = "Monthly"
                    
            if not is_recurring:
                continue
                
            # Resolve Lender Name
            lender_name = extract_lender_name(cluster[0]["Narration"])
            
            # Preferred Day of Month
            preferred_day = int(np.round(np.mean([d.day for d in dates])))
            
            start_date = dates[0]
            end_date = dates[-1]
            
            # Calculate Active vs Completed based on 45 days threshold from statement end
            max_statement_date = pd.to_datetime(df["Date"]).max()
            days_since_last_payment = (max_statement_date - end_date).days
            
            status = "Active"
            if days_since_last_payment > 45:
                status = "Completed"
                
            # Build chronological timeline
            timeline = []
            periods = pd.period_range(start=start_date.to_period("M"), end=end_date.to_period("M"), freq="M")
            
            has_bounces = False
            for p in periods:
                month_str = p.strftime("%b %Y")
                # Look for payment in this month
                month_txs = [tx for tx in cluster if tx["Date"].year == p.year and tx["Date"].month == p.month]
                
                if month_txs:
                    timeline.append({
                        "month": month_str,
                        "date": month_txs[0]["Date"].strftime("%d-%m-%Y"),
                        "amount": float(month_txs[0]["Withdrawal Amount"]),
                        "status": "Paid"
                    })
                else:
                    # Check for bounce transaction matching lender/sig in this month
                    expected_date = datetime(p.year, p.month, min(preferred_day, 28))
                    sig_word = sig.split()[0] if sig.split() else "NO_SIG"
                    month_bounces = bounces_df[
                        (bounces_df["Date"].dt.year == p.year) & 
                        (bounces_df["Date"].dt.month == p.month) &
                        (bounces_df["Narration"].str.upper().str.contains(sig_word))
                    ]
                    
                    if not month_bounces.empty:
                        has_bounces = True
                        timeline.append({
                            "month": month_str,
                            "date": month_bounces.iloc[0]["Date"].strftime("%d-%m-%Y"),
                            "amount": float(median_amount),
                            "status": "Bounced"
                        })
                    else:
                        timeline.append({
                            "month": month_str,
                            "date": expected_date.strftime("%d-%m-%Y"),
                            "amount": float(median_amount),
                            "status": "Missed"
                        })
                        
            if has_bounces and status == "Active":
                status = "Bounced"
                
            explainable_reason = (
                f"Classified as recurring {frequency.lower()} obligation to {lender_name}. "
                f"Identified {n} payments of average ₹{median_amount:,.0f} spaced by ~{int(mean_interval)} days on the {get_day_suffix(preferred_day)}."
            )
            
            factor_insights = f"Regular EMI of ₹{median_amount:,.0f} to {lender_name} on the {get_day_suffix(preferred_day)} of each month."
            
            detected_obligations.append({
                "lender": lender_name,
                "signature": sig,
                "amount": median_amount,
                "frequency": frequency,
                "preferred_day": preferred_day,
                "preferred_day_display": get_day_suffix(preferred_day),
                "total_payments": n,
                "total_paid": float(sum(amounts)),
                "first_payment_date": start_date.strftime("%d-%m-%Y"),
                "last_payment_date": end_date.strftime("%d-%m-%Y"),
                "status": status,
                "explainable_reason": explainable_reason,
                "factor_insights": factor_insights,
                "payment_timeline": timeline
            })
            
    return detected_obligations
