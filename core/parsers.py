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

DATE_FORMATS = (
    "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d-%B-%Y", "%Y-%m-%d", "%m/%d/%Y",
    "%d-%m-%y", "%d/%m/%y",
)

BOUNCE_KEYWORDS = ("bounce", "return", "fail", "reject", "insufficient", "rtn", "rev")
UPI_KEYWORDS = ("upi", "imps", "neft", "rtgs", "gpay", "phonepe", "paytm", "googlepay")


def _pick(row_lower: dict, candidates) -> str:
    for c in candidates:
        for k in row_lower:
            if c in k:
                return row_lower[k]
    return ""


def _to_amount(raw: str) -> float:
    if not raw:
        return 0.0
    s = re.sub(r"[^0-9.\-]", "", raw)
    if not s or s in (".", "-", "-."):
        return 0.0
    try:
        return abs(float(s))
    except ValueError:
        return 0.0


def _to_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
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
                meta_keys = ["txn_count", "period_months", "monthly_avg_inflow", "monthly_avg_outflow", "bounces", "upi_txns", "distinct_counterparties"]
                parsed_features = {k: v for k, v in features.items() if k not in meta_keys}
                return {
                    "features": parsed_features,
                    "txn_count": features["txn_count"],
                    "period_months": features["period_months"],
                    "monthly_avg_inflow": features["monthly_avg_inflow"],
                    "monthly_avg_outflow": features["monthly_avg_outflow"],
                    "bounces": features["bounces"],
                    "upi_txns": features["upi_txns"],
                    "distinct_counterparties": features["distinct_counterparties"],
                }
    except Exception:
        pass

    # Some banks emit a few preamble lines before the header — find the header
    # by scanning for a line that contains either a date column synonym AND
    # one of debit/credit.
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

    reader = csv.DictReader(io.StringIO(body))
    txns = []
    for raw in reader:
        if not raw:
            continue
        row = {(k or "").lower().strip(): (v or "").strip() for k, v in raw.items() if k}
        if not row:
            continue
        debit = _to_amount(_pick(row, DEBIT_KEYS))
        credit = _to_amount(_pick(row, CREDIT_KEYS))
        date = _to_date(_pick(row, DATE_KEYS))
        desc = _pick(row, DESC_KEYS).lower()
        if not date or (debit == 0 and credit == 0):
            continue
        txns.append({"date": date, "debit": debit, "credit": credit, "desc": desc})

    if not txns:
        return None

    by_month = defaultdict(lambda: {
        "credits": [], "debits": [], "bounces": 0, "upi": 0, "counterparties": set(), "txn_count": 0,
    })
    for t in txns:
        ym = (t["date"].year, t["date"].month)
        bucket = by_month[ym]
        bucket["txn_count"] += 1
        if t["credit"] > 0:
            bucket["credits"].append(t["credit"])
        if t["debit"] > 0:
            bucket["debits"].append(t["debit"])
        if any(k in t["desc"] for k in BOUNCE_KEYWORDS):
            bucket["bounces"] += 1
        if any(k in t["desc"] for k in UPI_KEYWORDS):
            bucket["upi"] += 1
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
