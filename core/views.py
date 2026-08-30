import io
import mimetypes
import random
import secrets
from datetime import date, timedelta
from pathlib import Path

import markdown as md_lib
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.files.base import ContentFile
from django.db.models import Avg, Count, Q
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_POST

from .forms import (
    BankStatementUploadForm,
    CustomerProfileForm,
    CustomerSignupForm,
    DocumentUploadForm,
    StaffUserForm,
)
from .models import (
    AAConsent,
    AuditLog,
    BankStatement,
    CustomerProfile,
    Document,
    ScoreReport,
    User,
)
from .parsers import parse_csv_statement, parse_excel_statement, parse_xml_statement, parse_finbox_transactions_json
from .scoring import ALGORITHMS, AI_MODEL, generate_score


def _audit(actor, action, target="", detail=""):
    AuditLog.objects.create(actor=actor, action=action, target=str(target), detail=detail)


# --- Auth & landing ---------------------------------------------------------

def home(request):
    if request.user.is_authenticated:
        return redirect("post_login_redirect")
    return render(request, "core/home.html")


def signup(request):
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            _audit(user, "signup")
            messages.success(request, "Welcome to FairCreditScore!")
            return redirect("customer_dashboard")
    else:
        form = CustomerSignupForm()
    return render(request, "core/signup.html", {"form": form})


@login_required
def post_login_redirect(request):
    u = request.user
    if u.is_admin_role:
        return redirect("admin_dashboard")
    if u.is_ops_role:
        return redirect("ops_dashboard")
    return redirect("customer_dashboard")


# --- Role gates -------------------------------------------------------------

def customer_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_customer_role)(view)


def ops_required(view):
    return user_passes_test(lambda u: u.is_authenticated and (u.is_ops_role or u.is_admin_role))(view)


def admin_required(view):
    return user_passes_test(lambda u: u.is_authenticated and u.is_admin_role)(view)


# --- Customer views ---------------------------------------------------------

@customer_required
def customer_dashboard(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    latest_score = ScoreReport.objects.filter(customer=request.user).first()
    documents = Document.objects.filter(customer=request.user).order_by("-uploaded_at")
    consents = AAConsent.objects.filter(customer=request.user).order_by("-created_at")
    return render(
        request,
        "core/customer_dashboard.html",
        {
            "profile": profile,
            "latest_score": latest_score,
            "documents": documents,
            "consents": consents,
        },
    )


@customer_required
def customer_profile(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            _audit(request.user, "profile_update")
            messages.success(request, "Profile updated.")
            return redirect("customer_dashboard")
    else:
        form = CustomerProfileForm(instance=profile)
    return render(request, "core/customer_profile.html", {"form": form})


@customer_required
def upload_document(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.customer = request.user
            doc.save()
            _audit(request.user, "document_upload", target=doc.id, detail=doc.doc_type)
            messages.success(request, f"{doc.get_doc_type_display()} uploaded. Pending verification.")
            return redirect("customer_dashboard")
    else:
        form = DocumentUploadForm()
    return render(request, "core/upload_document.html", {"form": form})


@customer_required
@require_POST
def initiate_consent(request):
    """Initiates consent via Finbox, falls back to mock if Finbox fails."""
    from core.finbox import FinboxClient
    client = FinboxClient()
    res = client.create_session(request.user.username, request.user.email)
    if res and res.get("RetStatus") == "SUCCESS":
        handle = res["tclStatementID"]
        redirect_url = res["redirectUrl"]
        consent = AAConsent.objects.create(
            customer=request.user,
            handle=handle,
            status=AAConsent.Status.PENDING,
            aa_provider="Finbox BankConnect"
        )
        _audit(request.user, "consent_initiated_finbox", target=consent.id)
        return redirect(redirect_url)
    
    # Fallback to local mock consent screen
    handle = secrets.token_hex(16)
    consent = AAConsent.objects.create(
        customer=request.user,
        handle=handle,
        status=AAConsent.Status.PENDING,
        aa_provider="Finbox BankConnect (Mock Fallback)"
    )
    _audit(request.user, "consent_initiated", target=consent.id)
    return redirect("consent_review", handle=handle)


@customer_required
def consent_review(request, handle):
    consent = get_object_or_404(AAConsent, handle=handle, customer=request.user)
    return render(request, "core/consent_review.html", {"consent": consent})


@customer_required
@require_POST
def consent_approve(request, handle):
    consent = get_object_or_404(AAConsent, handle=handle, customer=request.user)
    consent.status = AAConsent.Status.ACTIVE
    consent.approved_at = timezone.now()
    consent.save()
    _audit(request.user, "consent_approved", target=consent.id)
    messages.success(request, "Consent approved. We can now fetch your data via the Account Aggregator.")
    return redirect("customer_dashboard")


@customer_required
@require_POST
def consent_revoke(request, handle):
    consent = get_object_or_404(AAConsent, handle=handle, customer=request.user)
    consent.status = AAConsent.Status.REVOKED
    consent.revoked_at = timezone.now()
    consent.save()
    _audit(request.user, "consent_revoked", target=consent.id)
    messages.info(request, "Consent revoked.")
    return redirect("customer_dashboard")


def _persist_bank_statement(uploaded_file, customer, actor):
    """Parse a CSV / XLS / XLSX statement and save a BankStatement row."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    name = (uploaded_file.name or "").lower()
    parsed = None
    if name.endswith((".xls", ".xlsx")):
        try:
            parsed = parse_excel_statement(io.BytesIO(raw), name)
        except Exception as exc:
            parsed = None
            excel_error = f"Excel parse error: {exc}"
        else:
            excel_error = None
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("latin-1", errors="replace")
        parsed = parse_csv_statement(text)
        excel_error = None

    bs = BankStatement(customer=customer, file=uploaded_file, uploaded_by=actor)
    if parsed:
        bs.parsed_features = parsed["features"]
        bs.txn_count = parsed["txn_count"]
        bs.period_months = parsed["period_months"]
        bs.parsed_at = timezone.now()
        bs.parse_notes = (
            f"{parsed['txn_count']} txns over ~{parsed['period_months']:.1f} months. "
            f"avg inflow ₹{parsed['monthly_avg_inflow']:.0f}/mo, "
            f"avg outflow ₹{parsed['monthly_avg_outflow']:.0f}/mo, "
            f"bounces={parsed['bounces']}, upi_txns={parsed['upi_txns']}, "
            f"counterparties={parsed['distinct_counterparties']}."
        )
    else:
        bs.parse_notes = excel_error or (
            "No recognizable transactions found. Expected columns like Date, "
            "Description, Debit/Withdrawal, Credit/Deposit."
        )
    bs.save()
    return bs, bool(parsed), bs.parse_notes


@customer_required
def upload_bank_statement(request):
    if request.method == "POST":
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bs, ok, msg = _persist_bank_statement(
                form.cleaned_data["file"], request.user, request.user
            )
            _audit(request.user, "bank_statement_upload", target=bs.id, detail=msg)
            if ok:
                messages.success(request, f"Bank statement parsed: {msg}")
            else:
                messages.warning(request, f"Statement uploaded but parser couldn't read it: {msg}")
            return redirect("customer_dashboard")
    else:
        form = BankStatementUploadForm()
    return render(request, "core/upload_bank_statement.html", {"form": form})


@customer_required
@require_POST
def generate_my_score(request):
    algorithm = request.POST.get("algorithm", AI_MODEL)
    if algorithm not in ALGORITHMS:
        algorithm = AI_MODEL
    try:
        report = generate_score(request.user, algorithm=algorithm)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("customer_profile")
    _audit(
        request.user,
        "score_generated",
        target=report.id,
        detail=f"{report.score} ({algorithm})",
    )
    messages.success(
        request,
        f"New {report.get_algorithm_display()} score: {report.score}",
    )
    return redirect("score_detail", pk=report.id)


@login_required
def score_detail(request, pk):
    if request.user.is_admin_role or request.user.is_ops_role:
        visible_customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
        report = get_object_or_404(ScoreReport, pk=pk)
        if report.customer.role == User.Role.CUSTOMER and report.customer.onboarded_by is None:
            raise Http404("not found")
    else:
        report = get_object_or_404(ScoreReport, pk=pk, customer=request.user)
    return render(request, "core/score_detail.html", {"report": report})


# --- Operations views -------------------------------------------------------

@ops_required
def ops_dashboard(request):
    visible_customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    pending_docs = Document.objects.filter(status=Document.Status.UPLOADED, customer__in=visible_customers).count()
    active_consents = AAConsent.objects.filter(status=AAConsent.Status.ACTIVE, customer__in=visible_customers).count()
    pending_consents = AAConsent.objects.filter(status=AAConsent.Status.PENDING, customer__in=visible_customers).count()
    total_customers = visible_customers.count()
    recent_scores = ScoreReport.objects.filter(customer__in=visible_customers).select_related("customer")[:10]
    return render(
        request,
        "core/ops_dashboard.html",
        {
            "pending_docs": pending_docs,
            "active_consents": active_consents,
            "pending_consents": pending_consents,
            "total_customers": total_customers,
            "recent_scores": recent_scores,
        },
    )


@ops_required
def ops_documents(request):
    status = request.GET.get("status", "uploaded")
    visible_customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    docs = Document.objects.select_related("customer").filter(status=status, customer__in=visible_customers).order_by("-uploaded_at")
    return render(request, "core/ops_documents.html", {"documents": docs, "status": status})


@ops_required
@require_POST
def ops_review_document(request, pk):
    visible_customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    doc = get_object_or_404(Document, pk=pk, customer__in=visible_customers)
    decision = request.POST.get("decision")
    notes = request.POST.get("notes", "").strip()
    if decision == "approve":
        doc.status = Document.Status.VERIFIED
    elif decision == "reject":
        doc.status = Document.Status.REJECTED
    else:
        messages.error(request, "Invalid decision.")
        return redirect("ops_documents")
    doc.notes = notes
    doc.reviewed_by = request.user
    doc.reviewed_at = timezone.now()
    doc.save()
    _audit(request.user, f"document_{decision}", target=doc.id)
    messages.success(request, f"Document {decision}d.")
    return redirect("ops_documents")


@ops_required
def ops_customers(request):
    q = request.GET.get("q", "").strip()
    customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    if q:
        customers = customers.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(mobile__icontains=q) | Q(pan__icontains=q) | Q(profile__full_name__icontains=q)
        )
    customers = customers.annotate(
        score_count=Count("scores"), doc_count=Count("documents", distinct=True)
    ).order_by("-date_joined")[:100]
    return render(request, "core/ops_customers.html", {"customers": customers, "q": q})


@ops_required
def ops_customer_detail(request, pk):
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    return render(
        request,
        "core/ops_customer_detail.html",
        {
            "customer": customer,
            "documents": customer.documents.all().order_by("-uploaded_at"),
            "consents": customer.consents.all().order_by("-created_at"),
            "scores": customer.scores.all(),
            "bank_statements": customer.bank_statements.all()[:10],
        },
    )


@ops_required
def ops_edit_customer_profile(request, pk):
    """Operations edits/completes a customer's profile details."""
    visible_customers = User.objects.filter(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    customer = get_object_or_404(visible_customers, pk=pk)
    profile, _ = CustomerProfile.objects.get_or_create(user=customer)
    if request.method == "POST":
        form = CustomerProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            _audit(request.user, "ops_profile_update", target=customer.id)
            messages.success(request, f"Profile for '{customer.username}' updated.")
            return redirect("ops_customer_detail", pk=customer.id)
    else:
        form = CustomerProfileForm(instance=profile)
    return render(
        request,
        "core/ops_edit_customer_profile.html",
        {"form": form, "customer": customer}
    )


@ops_required
def ops_create_customer(request):
    """Operations onboards a new customer account on their behalf."""
    if request.method == "POST":
        form = CustomerSignupForm(request.POST)
        if form.is_valid():
            user = form.save(onboarded_by=request.user)
            _audit(request.user, "ops_created_customer", target=user.id, detail=user.username)
            messages.success(request, f"Customer '{user.username}' created.")
            return redirect("ops_customer_detail", pk=user.id)
    else:
        form = CustomerSignupForm()
    return render(request, "core/ops_create_customer.html", {"form": form})


@ops_required
def ops_upload_bank_statement(request, pk):
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    if request.method == "POST":
        form = BankStatementUploadForm(request.POST, request.FILES)
        if form.is_valid():
            bs, ok, msg = _persist_bank_statement(
                form.cleaned_data["file"], customer, request.user
            )
            _audit(
                request.user,
                "ops_bank_statement_upload",
                target=bs.id,
                detail=f"customer={customer.username}; {msg}",
            )
            if ok:
                messages.success(request, f"Statement parsed for {customer.username}: {msg}")
            else:
                messages.warning(request, f"Statement uploaded but parser couldn't read it: {msg}")
            return redirect("ops_customer_detail", pk=customer.id)
    else:
        form = BankStatementUploadForm()
    return render(
        request,
        "core/ops_upload_bank_statement.html",
        {"form": form, "customer": customer},
    )


def _synthetic_aa_csv(customer) -> str:
    """Generate a believable 6-month UPI+bank CSV for a customer.

    Mirrors what Setu Bridge would return after AA consent — salary on the 5th,
    rent on the 10th, recurring mobile/electricity, daily UPI for groceries
    and food, occasional ATM. Seeded by customer.id so each customer always
    sees the same 'fetched' dataset.
    """
    rng = random.Random(customer.id * 17 + 31)
    salary = rng.choice([28000, 38000, 45000, 60000, 78000])
    rent = int(salary * rng.uniform(0.22, 0.42))
    months_back = 6
    today = date.today()
    start = today.replace(day=1) - timedelta(days=months_back * 30)
    lines = ["Date,Description,Withdrawal,Deposit,Balance"]
    balance = rng.randint(5000, 35000)
    daily_descs = [
        "UPI/GPAY/MILK SHOP",
        "UPI/PAYTM/VEGETABLES",
        "UPI/GPAY/RESTAURANT",
        "UPI/PHONEPE/GROCERY",
        "UPI/PAYTM/PETROL",
        "UPI/GPAY/AMAZON",
        "UPI/PHONEPE/SWIGGY",
    ]
    cur = start
    while cur <= today:
        if cur.day == 5:
            balance += salary
            lines.append(f"{cur:%d-%m-%Y},SALARY VIA NEFT,,{salary},{balance}")
        if cur.day == 6:
            balance -= 299
            lines.append(f"{cur:%d-%m-%Y},UPI/PHONEPE/MOBILE RECHARGE,299,,{balance}")
        if cur.day == 10:
            balance -= rent
            lines.append(f"{cur:%d-%m-%Y},UPI/IMPS/RENT TRANSFER,{rent},,{balance}")
        if cur.day == 20:
            amt = rng.randint(1500, 2600)
            balance -= amt
            lines.append(f"{cur:%d-%m-%Y},UPI/PHONEPE/ELECTRICITY,{amt},,{balance}")
        if cur.day == 28:
            amt = rng.randint(2000, 5000)
            balance -= amt
            lines.append(f"{cur:%d-%m-%Y},ATM WITHDRAWAL,{amt},,{balance}")
        if cur.weekday() in (1, 3, 5):
            amt = rng.randint(80, 950)
            balance -= amt
            desc = rng.choice(daily_descs)
            lines.append(f"{cur:%d-%m-%Y},{desc},{amt},,{balance}")
        cur += timedelta(days=1)
    return "\n".join(lines) + "\n"


@ops_required
@require_POST
def ops_fetch_aa(request, pk):
    """Initiates AA fetch via Finbox and redirects the user to the consent screen."""
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    
    from core.finbox import FinboxClient
    client = FinboxClient()
    return_url = request.build_absolute_uri(reverse('ops_aa_callback', args=[pk]))
    res = client.create_session(customer.username, customer.email, return_url=return_url)
    
    if res and res.get("RetStatus") == "SUCCESS":
        handle = res["tclStatementID"]
        redirect_url = res["redirectUrl"]
        consent = AAConsent.objects.create(
            customer=customer,
            handle=handle,
            status=AAConsent.Status.PENDING,
            aa_provider="Finbox BankConnect"
        )
        _audit(request.user, "ops_consent_initiated", target=consent.id)
        return redirect(redirect_url)
        
    # Mock Fallback if Finbox fails
    csv_text = _synthetic_aa_csv(customer)
    parsed = parse_csv_statement(csv_text)
    
    bs = BankStatement(
        customer=customer,
        uploaded_by=request.user,
        source=BankStatement.Source.AA_FETCH,
    )
    filename = f"aa_fetch_mock_{customer.username}_{int(timezone.now().timestamp())}.csv"
    bs.file.save(filename, ContentFile(csv_text.encode("utf-8")), save=False)
    
    if parsed:
        bs.parsed_features = parsed["features"]
        bs.txn_count = parsed["txn_count"]
        bs.period_months = parsed["period_months"]
        bs.parsed_at = timezone.now()
        bs.parse_notes = (
            f"Mock fetch: {parsed['txn_count']} txns over ~{parsed['period_months']:.1f} months. "
            f"avg inflow ₹{parsed['monthly_avg_inflow']:.0f}/mo, "
            f"avg outflow ₹{parsed['monthly_avg_outflow']:.0f}/mo, "
            f"bounces={parsed['bounces']}, upi_txns={parsed['upi_txns']}, "
            f"counterparties={parsed['distinct_counterparties']}."
        )
    else:
        bs.parse_notes = "Fetch failed to parse."
        
    bs.save()
    _audit(
        request.user,
        "ops_aa_fetch_mock",
        target=bs.id,
        detail=f"customer={customer.username}; {bs.parse_notes}",
    )
    
    if parsed:
        messages.success(request, f"Fetched transactions for {customer.username} via Account Aggregator (Simulated Mock Fallback): {bs.txn_count} txns.")
    else:
        messages.warning(request, f"Fetch completed but parser failed: {bs.parse_notes}")
        
    return redirect("ops_customer_detail", pk=customer.id)


@ops_required
def ops_aa_callback(request, pk):
    """Callback view when Finbox redirects back after consent flow."""
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    consent = customer.consents.filter(status=AAConsent.Status.PENDING).order_by("-created_at").first()
    
    if not consent:
        messages.error(request, "No pending consent found to process.")
        return redirect("ops_customer_detail", pk=customer.id)

    from core.finbox import FinboxClient
    client = FinboxClient()
    
    parsed = None
    xml_text = None
    tx_res = None
    
    # 1. Try UAT session progress status to get direct XML response first
    progress_res = client.fetch_session_progress_status(consent.handle)
    if progress_res and progress_res.get("Response"):
        xml_text = progress_res["Response"]
        parsed = parse_xml_statement(xml_text)
        if parsed:
            consent.status = AAConsent.Status.ACTIVE
            consent.save()
    
    # 2. Try to fetch parsed transactions directly (JSON format)
    if not parsed:
        tx_res = client.fetch_transactions(consent.handle)
        if tx_res and "transactions" in tx_res:
            parsed = parse_finbox_transactions_json(tx_res)
            if parsed:
                consent.status = AAConsent.Status.ACTIVE
                consent.save()
                
    # 3. Fall back to raw AA S3 XML download if transactions JSON is unavailable
    if not parsed:
        res = client.fetch_raw_aa(consent.handle)
        if res and "statements" in res:
            for stmt in res["statements"]:
                download_url = stmt.get("url") or stmt.get("pdf_url")
                if download_url:
                    xml_text = client.download_xml(download_url)
                    if xml_text:
                        parsed = parse_xml_statement(xml_text)
                        if parsed:
                            consent.status = AAConsent.Status.ACTIVE
                            consent.save()
                            break

    if not parsed:
        consent.status = AAConsent.Status.REVOKED
        consent.save()
        messages.error(request, "Failed to retrieve or parse Account Aggregator data from Finbox.")
        return redirect("ops_customer_detail", pk=customer.id)

    bs = BankStatement(
        customer=customer,
        uploaded_by=request.user,
        source=BankStatement.Source.AA_FETCH,
    )
    
    if xml_text:
        filename = f"aa_fetch_{customer.username}_{int(timezone.now().timestamp())}.xml"
        bs.file.save(filename, ContentFile(xml_text.encode("utf-8")), save=False)
    else:
        import json
        filename = f"aa_fetch_{customer.username}_{int(timezone.now().timestamp())}.json"
        bs.file.save(filename, ContentFile(json.dumps(tx_res).encode("utf-8")), save=False)

    bs.parsed_features = parsed["features"]
    bs.txn_count = parsed["txn_count"]
    bs.period_months = parsed["period_months"]
    bs.parsed_at = timezone.now()
    prefix = "Finbox AA JSON " if not xml_text else "Finbox AA XML "
    bs.parse_notes = (
        f"{prefix}fetch: {parsed['txn_count']} txns over ~{parsed['period_months']:.1f} months. "
        f"avg inflow ₹{parsed['monthly_avg_inflow']:.0f}/mo, "
        f"avg outflow ₹{parsed['monthly_avg_outflow']:.0f}/mo, "
        f"bounces={parsed['bounces']}, upi_txns={parsed['upi_txns']}, "
        f"counterparties={parsed['distinct_counterparties']}."
    )
    
    bs.save()
    _audit(
        request.user,
        "ops_aa_fetch_callback",
        target=bs.id,
        detail=f"customer={customer.username}; {bs.parse_notes}",
    )
    
    messages.success(request, f"Fetched transactions for {customer.username} via Account Aggregator (Finbox): {bs.txn_count} txns.")
    return redirect("ops_customer_detail", pk=customer.id)


@ops_required
@require_POST
def ops_generate_score(request, pk):
    """Operations generates a score for a customer on their behalf."""
    customer = get_object_or_404(User, pk=pk, role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    algorithm = request.POST.get("algorithm", AI_MODEL)
    if algorithm not in ALGORITHMS:
        algorithm = AI_MODEL
    try:
        report = generate_score(customer, algorithm=algorithm)
    except ValueError as e:
        messages.error(request, f"Cannot generate score: {e}")
        return redirect("ops_customer_detail", pk=customer.id)
    _audit(
        request.user,
        "ops_score_generated",
        target=report.id,
        detail=f"customer={customer.username} {report.score} ({algorithm})",
    )
    messages.success(
        request,
        f"{report.get_algorithm_display()} score generated for {customer.username}: {report.score}",
    )
    return redirect("ops_customer_detail", pk=customer.id)


# --- Admin views ------------------------------------------------------------

@admin_required
def admin_dashboard(request):
    visible_users = User.objects.filter(
        Q(role__in=[User.Role.ADMIN, User.Role.OPS]) |
        Q(is_superuser=True) |
        Q(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    )
    stats = {
        "total_users": visible_users.count(),
        "customers": visible_users.filter(role=User.Role.CUSTOMER).count(),
        "ops_users": visible_users.filter(role=User.Role.OPS).count(),
        "admins": visible_users.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True)).distinct().count(),
        "documents": Document.objects.filter(customer__in=visible_users).count(),
        "verified_docs": Document.objects.filter(status=Document.Status.VERIFIED, customer__in=visible_users).count(),
        "active_consents": AAConsent.objects.filter(status=AAConsent.Status.ACTIVE, customer__in=visible_users).count(),
        "scores_generated": ScoreReport.objects.filter(customer__in=visible_users).count(),
        "avg_score": int(ScoreReport.objects.filter(customer__in=visible_users).aggregate(a=Avg("score"))["a"] or 0),
    }
    recent_audit = AuditLog.objects.filter(
        Q(actor__isnull=True) | Q(actor__in=visible_users)
    ).select_related("actor")[:20]
    return render(
        request,
        "core/admin_dashboard.html",
        {"stats": stats, "recent_audit": recent_audit},
    )


@admin_required
def admin_users(request):
    visible_users = User.objects.filter(
        Q(role__in=[User.Role.ADMIN, User.Role.OPS]) |
        Q(is_superuser=True) |
        Q(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    )
    users = visible_users.order_by("-date_joined")
    return render(request, "core/admin_users.html", {"users": users})


@admin_required
def admin_user_edit(request, pk=None):
    visible_users = User.objects.filter(
        Q(role__in=[User.Role.ADMIN, User.Role.OPS]) |
        Q(is_superuser=True) |
        Q(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    )
    user = get_object_or_404(visible_users, pk=pk) if pk else None
    if request.method == "POST":
        form = StaffUserForm(request.POST, instance=user)
        if form.is_valid():
            if not user:
                form.instance.onboarded_by = request.user
            saved = form.save(commit=True)
            _audit(request.user, "user_saved", target=saved.id)
            messages.success(request, "User saved.")
            return redirect("admin_users")
    else:
        form = StaffUserForm(instance=user)
    return render(request, "core/admin_user_edit.html", {"form": form, "edit_user": user})


@admin_required
def admin_audit(request):
    visible_users = User.objects.filter(
        Q(role__in=[User.Role.ADMIN, User.Role.OPS]) |
        Q(is_superuser=True) |
        Q(role=User.Role.CUSTOMER, onboarded_by__isnull=False)
    )
    logs = AuditLog.objects.filter(
        Q(actor__isnull=True) | Q(actor__in=visible_users)
    ).select_related("actor")[:300]
    return render(request, "core/admin_audit.html", {"logs": logs})


# --- Admin wiki (Jekyll-style browser of /documents) ------------------------

WIKI_ROOT = Path(settings.BASE_DIR) / "documents"

# Extensions we render inline; everything else is offered as a download.
WIKI_RENDERABLE = {".md", ".markdown"}
WIKI_IMAGE = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


def _wiki_safe_path(rel_path: str) -> Path:
    """Resolve a wiki path safely under WIKI_ROOT or raise Http404."""
    candidate = (WIKI_ROOT / rel_path).resolve()
    try:
        candidate.relative_to(WIKI_ROOT.resolve())
    except ValueError:
        raise Http404("path escapes wiki root")
    return candidate


def _wiki_breadcrumbs(rel_path: str):
    parts = [p for p in rel_path.split("/") if p]
    crumbs, cum = [], ""
    for p in parts:
        cum = f"{cum}/{p}".lstrip("/")
        crumbs.append({"name": p, "rel": cum})
    return crumbs


@admin_required
def admin_wiki(request, rel_path: str = ""):
    rel_path = (rel_path or "").strip("/")
    target = _wiki_safe_path(rel_path) if rel_path else WIKI_ROOT

    if not target.exists():
        raise Http404("not found")

    if target.is_dir():
        entries = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.name.startswith("."):
                continue
            child_rel = (Path(rel_path) / child.name).as_posix() if rel_path else child.name
            entries.append({
                "name": child.name,
                "rel": child_rel,
                "is_dir": child.is_dir(),
                "size": child.stat().st_size if child.is_file() else None,
                "ext": child.suffix.lower(),
            })
        return render(request, "core/admin_wiki_index.html", {
            "entries": entries,
            "rel_path": rel_path,
            "breadcrumbs": _wiki_breadcrumbs(rel_path),
            "wiki_root_name": WIKI_ROOT.name,
        })

    # File request
    ext = target.suffix.lower()
    if ext in WIKI_RENDERABLE:
        raw = target.read_text(encoding="utf-8", errors="replace")
        html = md_lib.markdown(
            raw,
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
        )
        return render(request, "core/admin_wiki_page.html", {
            "rel_path": rel_path,
            "breadcrumbs": _wiki_breadcrumbs(rel_path),
            "filename": target.name,
            "content_html": mark_safe(html),
            "wiki_root_name": WIKI_ROOT.name,
        })

    if ext in WIKI_IMAGE:
        return render(request, "core/admin_wiki_page.html", {
            "rel_path": rel_path,
            "breadcrumbs": _wiki_breadcrumbs(rel_path),
            "filename": target.name,
            "content_html": mark_safe(
                f'<img src="/admin-portal/wiki/raw/{rel_path}" alt="{target.name}" '
                'style="max-width:100%;height:auto;border-radius:8px;border:1px solid #e3e8f0;">'
            ),
            "wiki_root_name": WIKI_ROOT.name,
        })

    # Fallback: serve the raw file as a download via the helper view.
    return redirect("admin_wiki_raw", rel_path=rel_path)


@admin_required
def admin_wiki_raw(request, rel_path: str):
    target = _wiki_safe_path(rel_path.strip("/"))
    if not target.exists() or not target.is_file():
        raise Http404("not found")
    content_type, _ = mimetypes.guess_type(target.name)
    return FileResponse(open(target, "rb"), content_type=content_type or "application/octet-stream")


# --- Lender API mock --------------------------------------------------------

def lender_api_score(request, customer_id: int):
    """Mock lender-side endpoint that returns the latest score JSON for a customer."""
    customer = get_object_or_404(User, pk=customer_id, role=User.Role.CUSTOMER)
    report = ScoreReport.objects.filter(customer=customer).first()
    if not report:
        return JsonResponse({"error": "no score available"}, status=404)
    return JsonResponse(
        {
            "customer_id": customer.id,
            "username": customer.username,
            "score": report.score,
            "band": report.get_band_display(),
            "recommended_loan_amount": report.recommended_loan_amount,
            "top_positive_factors": report.top_positive_factors,
            "top_negative_factors": report.top_negative_factors,
            "generated_at": report.generated_at.isoformat(),
        },
        json_dumps_params={"ensure_ascii": False}
    )
