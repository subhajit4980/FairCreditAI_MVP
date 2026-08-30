"""Bank statement parser.

Produces the seven raw features in the same 0..1 (or count) shape that
``core.scoring._generate_features`` returns, so the scoring path can swap
synthetic features for real ones with no algorithm changes.

CSV column detection is intentionally lenient: it tries a handful of common
header names from Indian retail bank exports (HDFC, ICICI, SBI, Kotak,
Federal, IDFC, etc.) and ignores rows that don't have a parseable date plus
either a debit or a credit amount.
"""

import csv
import io
import re
import statistics
from collections import defaultdict
from datetime import datetime, date
from typing import BinaryIO, Optional


DATE_KEYS = ("txn date", "transaction date", "date", "value date", "posting date")
DEBIT_KEYS = ("withdrawal amt", "withdrawal", "debit amt", "debit", "dr amount", "dr")
CREDIT_KEYS = ("deposit amt", "deposit", "credit amt", "credit", "cr amount", "cr")
DESC_KEYS = ("description", "narration", "particulars", "transaction details", "details", "remarks")
BAL_KEYS = ("closing balance", "balance", "running balance")
AMOUNT_KEYS = ("amount", "txn amount", "transaction amount")
CATEGORY_KEYS = ("category", "type", "txn type", "transaction type")

DATE_FORMATS = (
    "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%m/%d/%Y",
    "%d-%m-%y", "%d/%m/%y",
)

BOUNCE_KEYWORDS = ("bounce", "return", "fail", "reject", "insufficient", "rtn", "rev")
UPI_KEYWORDS = ("upi", "imps", "neft", "rtgs", "gpay", "phonepe", "paytm", "googlepay")
LOAN_KEYWORDS = ("loan", "emi", "financeautopay", "bajajfinance", "bajajfinserv")


def _pick(row_lower: dict, candidates) -> str:
    # First look for exact match
    for c in candidates:
        if c in row_lower:
            return row_lower[c]
    # Then look for substring match
    for c in candidates:
        for k in row_lower:
            if c in k:
                return row_lower[k]
    return ""


def _to_amount(raw: str) -> float:
    """Parse a string amount into a float, preserving the sign."""
    if not raw:
        return 0.0
    s = re.sub(r"[^0-9.\-]", "", raw)
    if not s or s in (".", "-", "-."):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    # Strip any time component (e.g. 2025-01-01 08:37:36 -> 2025-01-01)
    date_part = raw.split()[0].split('T')[0]
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(date_part, fmt)
        except ValueError:
            continue
    # Fallback to pandas if standard formats do not match
    try:
        import pandas as pd
        return pd.to_datetime(raw).to_pydatetime()
    except Exception:
        pass
    return None



def parse_csv_statement(text: str) -> Optional[dict]:
    """Parse a bank statement CSV.

    Returns a dict with the raw features and parse stats, or ``None``
    if no usable transactions were found.
    """
    try:
        from core.ml.features import parse_to_dataframe, extract_advanced_features
        df = parse_to_dataframe(io.StringIO(text), "statement.csv")
        if df is not None:
            features = extract_advanced_features(df)
            if features:
                meta_keys = [
                    "txn_count", "period_months", "monthly_avg_inflow", "monthly_avg_outflow",
                    "average_monthly_income", "average_monthly_expense", "bounces", "upi_txns",
                    "distinct_counterparties"
                ]
                parsed_features = {k: v for k, v in features.items() if k not in meta_keys}
                return {
                    "features": parsed_features,
                    "txn_count": features["txn_count"],
                    "period_months": features["period_months"],
                    "monthly_avg_inflow": features.get("monthly_avg_inflow", features.get("average_monthly_income", 0.0)),
                    "monthly_avg_outflow": features.get("monthly_avg_outflow", features.get("average_monthly_expense", 0.0)),
                    "bounces": features["bounces"],
                    "upi_txns": features["upi_txns"],
                    "distinct_counterparties": features["distinct_counterparties"],
                }
    except Exception:
        pass

    # Some banks emit a few preamble lines before the header — find the header
    # by scanning for a line that contains either a date column synonym AND
    # one of debit/credit or a unified amount column.
    lines = text.splitlines()
    header_idx = 0
    for i, line in enumerate(lines[:30]):
        low = line.lower()
        has_date = any(d in low for d in DATE_KEYS)
        has_debit_credit = (any(d in low for d in DEBIT_KEYS) or any(c in low for c in CREDIT_KEYS))
        has_amount = any(a in low for a in AMOUNT_KEYS)
        if has_date and (has_debit_credit or has_amount):
            header_idx = i
            break
    body = "\n".join(lines[header_idx:])

    reader = csv.DictReader(io.StringIO(body))
    txns = []

    # Check if headers have separate debit/credit or a single amount column
    fieldnames = [f.lower().strip() for f in (reader.fieldnames or []) if f]
    has_separate = (
        any(any(d in f for d in DEBIT_KEYS) for f in fieldnames)
        or any(any(c in f for c in CREDIT_KEYS) for f in fieldnames)
    )
    has_single_amount = not has_separate and any(any(a in f for a in AMOUNT_KEYS) for f in fieldnames)

    for raw in reader:
        if not raw:
            continue
        row = {(k or "").lower().strip(): (v or "").strip() for k, v in raw.items() if k}
        if not row:
            continue

        if has_single_amount:
            # Single amount column: negative = debit, positive = credit
            raw_amt = _to_amount(_pick(row, AMOUNT_KEYS))
            debit = abs(raw_amt) if raw_amt < 0 else 0.0
            credit = raw_amt if raw_amt > 0 else 0.0
        else:
            debit = abs(_to_amount(_pick(row, DEBIT_KEYS)))
            credit = abs(_to_amount(_pick(row, CREDIT_KEYS)))

        date = _to_date(_pick(row, DATE_KEYS))
        desc = _pick(row, DESC_KEYS).lower()
        category = _pick(row, CATEGORY_KEYS).lower()
        if not date or (debit == 0 and credit == 0):
            continue
        txns.append({"date": date, "debit": debit, "credit": credit, "desc": desc, "category": category})

    if not txns:
        return None

    by_month = defaultdict(lambda: {
        "credits": [], "debits": [], "bounces": 0, "upi": 0, "loan": 0, "counterparties": set(), "txn_count": 0,
    })
    for t in txns:
        ym = (t["date"].year, t["date"].month)
        bucket = by_month[ym]
        bucket["txn_count"] += 1
        if t["credit"] > 0:
            bucket["credits"].append(t["credit"])
        if t["debit"] > 0:
            bucket["debits"].append(t["debit"])
        # Combined text for keyword matching: description + category
        combined = t["desc"] + " " + t["category"]
        if any(k in combined for k in BOUNCE_KEYWORDS):
            bucket["bounces"] += 1
        if any(k in combined for k in UPI_KEYWORDS):
            bucket["upi"] += 1
        if any(k in combined for k in LOAN_KEYWORDS):
            bucket["loan"] += 1
        counterparty = " ".join(t["desc"].split()[:4])
        if counterparty:
            bucket["counterparties"].add(counterparty)

    months = sorted(by_month.keys())
    period_months = max(1, len(months))

    monthly_inflows = [sum(by_month[m]["credits"]) for m in months]
    monthly_outflows = [sum(by_month[m]["debits"]) for m in months]
    avg_in = statistics.fmean(monthly_inflows) if monthly_inflows else 0
    avg_out = statistics.fmean(monthly_outflows) if monthly_outflows else 0
    total_txns = sum(by_month[m]["txn_count"] for m in months)
    bounces = sum(by_month[m]["bounces"] for m in months)
    upi_txns = sum(by_month[m]["upi"] for m in months)
    distinct_counterparties = len({c for m in months for c in by_month[m]["counterparties"]})

    # 1. Income consistency (0..1): 1 - coefficient_of_variation of monthly inflows.
    if avg_in > 0 and len(monthly_inflows) >= 2:
        cv = statistics.pstdev(monthly_inflows) / avg_in
        income_consistency = max(0.0, min(1.0, 1 - cv))
    else:
        income_consistency = 0.7 if avg_in > 0 else 0.0

    # 2. Expense / income ratio (0..1, lower is better, raw fraction of outflow over inflow).
    expense_ratio = min(1.0, avg_out / avg_in) if avg_in > 0 else 1.0

    # 3. Savings ratio (0..1): net / inflow, capped at 0.40 to match synthetic range.
    savings_ratio = max(0.0, min(0.40, (avg_in - avg_out) / avg_in)) if avg_in > 0 else 0.0

    # 4. Payment timeliness (0..1): no full due-date info, so we use a heuristic:
    # 1.0 minus bounces-per-month (capped). 0 bounces in 3 months => 0.95+.
    bounces_per_month = bounces / period_months
    payment_timeliness = max(0.0, min(1.0, 0.95 - bounces_per_month * 0.20))

    # 5. Transaction frequency: average transactions per month (raw, like the synthetic 20..180).
    transaction_frequency = total_txns / period_months

    # 6. Bounce rate (0..1): bounces / total transactions.
    bounce_rate = min(1.0, bounces / total_txns) if total_txns else 0.0

    # 7. Digital engagement (0..1): blend of UPI/IMPS share and counterparty diversity.
    upi_share = upi_txns / total_txns if total_txns else 0.0
    diversity = min(1.0, distinct_counterparties / 30.0)
    digital_engagement = max(0.0, min(1.0, 0.6 * upi_share + 0.4 * diversity))

    return {
        "features": {
            "income_consistency":    round(income_consistency, 3),
            "expense_ratio":         round(expense_ratio, 3),
            "savings_ratio":         round(savings_ratio, 3),
            "payment_timeliness":    round(payment_timeliness, 3),
            "transaction_frequency": round(transaction_frequency, 1),
            "bounce_rate":           round(bounce_rate, 3),
            "digital_engagement":    round(digital_engagement, 3),
            "detected_obligations":  [],
        },
        "txn_count": total_txns,
        "period_months": float(period_months),
        "monthly_avg_inflow": round(avg_in, 2),
        "monthly_avg_outflow": round(avg_out, 2),
        "bounces": bounces,
        "upi_txns": upi_txns,
        "distinct_counterparties": distinct_counterparties,
    }


# --- Excel (XLSX / XLS) ----------------------------------------------------

def _excel_cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (datetime, date)):
        return v.strftime("%d-%m-%Y")
    if isinstance(v, float):
        # Avoid scientific notation; trim trailing zeros.
        if v.is_integer():
            return str(int(v))
        return f"{v:.4f}".rstrip("0").rstrip(".")
    return str(v).strip()


def _read_xlsx_rows(file_obj: BinaryIO):
    from openpyxl import load_workbook  # local import keeps cold start fast
    wb = load_workbook(file_obj, read_only=True, data_only=True)
    ws = wb.active
    out = []
    for row in ws.iter_rows(values_only=True):
        out.append([_excel_cell(v) for v in row])
    return out


def _read_xls_rows(file_obj: BinaryIO):
    import xlrd  # local import keeps cold start fast
    wb = xlrd.open_workbook(file_contents=file_obj.read())
    sheet = wb.sheet_by_index(0)
    out = []
    for r in range(sheet.nrows):
        cells = []
        for c in range(sheet.ncols):
            ctype = sheet.cell_type(r, c)
            value = sheet.cell_value(r, c)
            if ctype == xlrd.XL_CELL_DATE:
                try:
                    value = datetime(*xlrd.xldate_as_tuple(value, wb.datemode))
                except Exception:
                    pass
            cells.append(_excel_cell(value))
        out.append(cells)
    return out


def parse_excel_statement(file_obj: BinaryIO, filename: str) -> Optional[dict]:
    """Parse an .xlsx or .xls bank statement.

    Reads the sheet into rows, serialises them as CSV in-memory, then delegates
    to ``parse_csv_statement`` so all column-detection and feature logic stays
    in one place.
    """
    name = filename.lower()
    if name.endswith(".xlsx"):
        rows = _read_xlsx_rows(file_obj)
    elif name.endswith(".xls"):
        rows = _read_xls_rows(file_obj)
    else:
        return None
    if not rows:
        return None
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow(row)
    return parse_csv_statement(buf.getvalue())


import xml.etree.ElementTree as ET

def parse_rebit_xml_to_df(xml_content: str) -> Optional[dict]:
    """Parse ReBIT-compliant Account Aggregator XML into a standardized DataFrame."""
    try:
        import re
        xml_stripped = re.sub(r"<\?xml.*?\?>", "", xml_content)
        xml_wrapped = f"<root>{xml_stripped}</root>"
        root = ET.fromstring(xml_wrapped.encode("utf-8"))
        transactions = []
        for elem in root.iter():
            # Match element tag name ignoring namespaces
            tag_name = elem.tag.split("}")[-1]
            if tag_name == "Transaction":
                attrs = elem.attrib
                txn_type = attrs.get("type", "").upper()
                amount_str = attrs.get("amount") or "0"
                amount = float(amount_str)
                narration = attrs.get("narration") or attrs.get("narrationDescription") or ""
                
                # Try multiple possible date attributes
                txn_date_str = attrs.get("valueDate") or attrs.get("txnDt") or attrs.get("date") or ""
                
                balance_str = attrs.get("currentBalance") or attrs.get("balance") or "0"
                balance = float(balance_str)
                
                withdrawal = amount if txn_type == "DEBIT" else 0.0
                deposit = amount if txn_type == "CREDIT" else 0.0
                
                transactions.append({
                    "Date": txn_date_str,
                    "Withdrawal Amount": withdrawal,
                    "Deposit Amount": deposit,
                    "Narration": narration,
                    "Closing Balance": balance
                })
        
        if not transactions:
            return None
            
        import pandas as pd
        df = pd.DataFrame(transactions)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df.sort_values(by="Date").reset_index(drop=True)
        return df
    except Exception as e:
        print("XML parse error:", e)
        return None


def parse_xml_statement(xml_content: str) -> Optional[dict]:
    """Parse a ReBIT XML statement.

    Returns a dict with the raw features and parse stats, or ``None``.
    """
    try:
        from core.ml.features import extract_advanced_features, get_counterparty_signature
        df = parse_rebit_xml_to_df(xml_content)
        if df is not None:
            features = extract_advanced_features(df)
            if features:
                txn_count = len(df)
                period_months = 0.0
                if txn_count > 1:
                    days = (df["Date"].max() - df["Date"].min()).days
                    period_months = max(0.1, days / 30.4)
                
                inflows = df[df["Deposit Amount"] > 0]["Deposit Amount"]
                outflows = df[df["Withdrawal Amount"] > 0]["Withdrawal Amount"]
                
                monthly_avg_inflow = float(inflows.sum() / max(0.1, period_months))
                monthly_avg_outflow = float(outflows.sum() / max(0.1, period_months))
                bounces = int(df[df["Narration"].str.upper().str.contains("BOUNCE|RETURN|FAIL|REJECT", na=False)].shape[0])
                upi_txns = int(df[df["Narration"].str.upper().str.contains("UPI|IMPS", na=False)].shape[0])
                
                counterparties = set(df["Narration"].apply(get_counterparty_signature))
                distinct_counterparties = len(counterparties)
                
                return {
                    "features": features,
                    "txn_count": txn_count,
                    "period_months": period_months,
                    "monthly_avg_inflow": monthly_avg_inflow,
                    "monthly_avg_outflow": monthly_avg_outflow,
                    "bounces": bounces,
                    "upi_txns": upi_txns,
                    "distinct_counterparties": distinct_counterparties,
                }
    except Exception as e:
        print("parse_xml_statement error:", e)
    return None


def parse_finbox_transactions_json(json_data: dict) -> Optional[dict]:
    """Parse Finbox Transactions JSON response directly into standardized features."""
    try:
        txns = json_data.get("transactions", [])
        if not txns:
            return None
        
        rows = []
        for t in txns:
            txn_type = t.get("transaction_type", "").lower()
            amount = float(t.get("amount", 0.0))
            narration = t.get("transaction_note") or t.get("description") or ""
            txn_date = t.get("date", "")
            balance = float(t.get("balance", 0.0))
            
            withdrawal = amount if txn_type == "debit" else 0.0
            deposit = amount if txn_type == "credit" else 0.0
            
            rows.append({
                "Date": txn_date,
                "Withdrawal Amount": withdrawal,
                "Deposit Amount": deposit,
                "Narration": narration,
                "Closing Balance": balance
            })
            
        import pandas as pd
        df = pd.DataFrame(rows)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df.dropna(subset=["Date"])
        df = df.sort_values(by="Date").reset_index(drop=True)
        
        from core.ml.features import extract_advanced_features, get_counterparty_signature
        features = extract_advanced_features(df)
        if features:
            txn_count = len(df)
            period_months = 0.0
            if txn_count > 1:
                days = (df["Date"].max() - df["Date"].min()).days
                period_months = max(0.1, days / 30.4)
            
            inflows = df[df["Deposit Amount"] > 0]["Deposit Amount"]
            outflows = df[df["Withdrawal Amount"] > 0]["Withdrawal Amount"]
            
            monthly_avg_inflow = float(inflows.sum() / max(0.1, period_months))
            monthly_avg_outflow = float(outflows.sum() / max(0.1, period_months))
            bounces = int(df[df["Narration"].str.upper().str.contains("BOUNCE|RETURN|FAIL|REJECT", na=False)].shape[0])
            upi_txns = int(df[df["Narration"].str.upper().str.contains("UPI|IMPS", na=False)].shape[0])
            
            counterparties = set(df["Narration"].apply(get_counterparty_signature))
            distinct_counterparties = len(counterparties)
            
            return {
                "features": features,
                "txn_count": txn_count,
                "period_months": period_months,
                "monthly_avg_inflow": monthly_avg_inflow,
                "monthly_avg_outflow": monthly_avg_outflow,
                "bounces": bounces,
                "upi_txns": upi_txns,
                "distinct_counterparties": distinct_counterparties,
            }
    except Exception as e:
        print("parse_finbox_transactions_json error:", e)
    return None


