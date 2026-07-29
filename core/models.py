from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        OPS = "ops", "Operations"
        CUSTOMER = "customer", "Customer"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.CUSTOMER)
    mobile = models.CharField(max_length=15, blank=True)
    pan = models.CharField(max_length=10, blank=True)

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_ops_role(self):
        return self.role == self.Role.OPS

    @property
    def is_customer_role(self):
        return self.role == self.Role.CUSTOMER


class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(
        max_length=10,
        blank=True,
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
    )
    education = models.CharField(
        max_length=40,
        blank=True,
        choices=[
            ("High School", "High School"),
            ("Bachelor's", "Bachelor's"),
            ("Master's", "Master's"),
            ("Doctorate", "Doctorate"),
            ("Diploma", "Diploma"),
            ("Graduate", "Graduate"),
        ]
    )
    address = models.TextField(blank=True)
    occupation = models.CharField(max_length=80, blank=True)
    monthly_income = models.PositiveIntegerField(null=True, blank=True)
    aadhaar_last4 = models.CharField(max_length=4, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name or self.user.username


class Document(models.Model):
    class DocType(models.TextChoices):
        PAN = "pan", "PAN Card"
        AADHAAR = "aadhaar", "Aadhaar Card"
        BANK_STATEMENT = "bank_statement", "Bank Statement"
        SALARY_SLIP = "salary_slip", "Salary Slip"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=20, choices=DocType.choices)
    file = models.FileField(upload_to="documents/%Y/%m/")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.UPLOADED)
    notes = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_documents"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer.username} - {self.get_doc_type_display()}"


class AAConsent(models.Model):
    """Account Aggregator consent artifact (mock)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        EXPIRED = "expired", "Expired"

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    handle = models.CharField(max_length=64, unique=True)
    aa_provider = models.CharField(max_length=40, default="Setu Bridge (Sandbox)")
    fi_types = models.CharField(
        max_length=200,
        default="DEPOSIT,TERM_DEPOSIT,RECURRING_DEPOSIT,MUTUAL_FUNDS",
    )
    purpose = models.CharField(max_length=120, default="Credit assessment - FairCreditScore")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.customer.username} - {self.handle} ({self.status})"


class ScoreReport(models.Model):
    class Band(models.TextChoices):
        POOR = "poor", "Poor"
        FAIR = "fair", "Fair"
        GOOD = "good", "Good"
        VERY_GOOD = "very_good", "Very Good"
        EXCELLENT = "excellent", "Excellent"

    class Algorithm(models.TextChoices):
        BASELINE = "baseline", "Baseline (prototype heuristic)"
        CANONICAL = "canonical", "Weighted Score Algorithm"
        AI_MODEL = "ai_model", "AI Model (alternative-data, 1-100)"

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="scores")
    algorithm = models.CharField(
        max_length=16, choices=Algorithm.choices, default=Algorithm.AI_MODEL
    )
    score = models.PositiveSmallIntegerField()  # 300-900
    band = models.CharField(max_length=12, choices=Band.choices)
    income_consistency = models.FloatField(default=0)
    expense_ratio = models.FloatField(default=0)
    savings_ratio = models.FloatField(default=0)
    payment_timeliness = models.FloatField(default=0)
    transaction_frequency = models.FloatField(default=0)
    bounce_rate = models.FloatField(default=0)
    digital_engagement = models.FloatField(default=0)
    top_positive_factors = models.JSONField(default=list)
    top_negative_factors = models.JSONField(default=list)
    recommended_loan_amount = models.PositiveIntegerField(default=0)
    # Full AI-model assessment (fraud prob, PD, grade, risk type, underwriting
    # decision, interest rate, limits, explanations). Populated only by the
    # ``ai_model`` algorithm; empty dict for baseline/canonical.
    ai_assessment = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-generated_at"]

    def __str__(self):
        return f"{self.customer.username} - {self.score} ({self.band})"


class BankStatement(models.Model):
    """A bank statement uploaded (or pulled from AA) for a customer.

    The CSV is parsed at upload time; the seven derived raw features and
    transaction stats are persisted so scoring can use them deterministically.
    """

    class Source(models.TextChoices):
        UPLOAD = "upload", "Manual upload"
        AA_FETCH = "aa_fetch", "Account Aggregator fetch"

    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bank_statements")
    file = models.FileField(upload_to="bank_statements/%Y/%m/")
    source = models.CharField(max_length=16, choices=Source.choices, default=Source.UPLOAD)
    uploaded_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="uploaded_statements"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    parsed_features = models.JSONField(default=dict)  # raw 0..1 floats (same shape as scoring.py)
    txn_count = models.PositiveIntegerField(default=0)
    period_months = models.FloatField(default=0)
    parse_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"{self.customer.username} - statement {self.id}"


class AuditLog(models.Model):
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    action = models.CharField(max_length=80)
    target = models.CharField(max_length=200, blank=True)
    detail = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} {self.actor} {self.action}"
