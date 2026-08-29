from django.test import TestCase

from .models import CustomerProfile, ScoreReport, User
from .scoring import AI_MODEL, _score_ai_model, generate_score

STRONG = {
    "income_consistency": 0.90, "expense_ratio": 0.45, "savings_ratio": 0.30,
    "payment_timeliness": 0.95, "transaction_frequency": 120, "bounce_rate": 0.0,
    "digital_engagement": 0.85,
}
WEAK = {
    "income_consistency": 0.55, "expense_ratio": 0.95, "savings_ratio": 0.02,
    "payment_timeliness": 0.60, "transaction_frequency": 40, "bounce_rate": 0.06,
    "digital_engagement": 0.30,
}


import datetime

class AiModelScoringFormulaTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create(username="test_customer", role=User.Role.CUSTOMER)
        CustomerProfile.objects.create(
            user=self.customer, 
            monthly_income=60000,
            date_of_birth=datetime.date(1995, 1, 1),
            occupation="Salaried private",
            gender="Male",
            education="Bachelor's"
        )

    def test_score_bounds_and_shape(self):
        for features in (STRONG, WEAK):
            score, pos, neg, loan, a = _score_ai_model(features, self.customer)
            self.assertTrue(1 <= score <= 100)
            self.assertGreaterEqual(loan, 0)
            self.assertIn(a["risk_grade"], {"Grade A", "Grade B", "Grade C", "Grade D", "Grade E"})
            self.assertIn(a["risk_type"], {"Low", "Medium", "High"})
            self.assertIn(a["underwriting_decision"], {"APPROVED", "REVIEW", "REJECTED"})

    def test_strong_outranks_weak(self):
        strong_score, *_ = _score_ai_model(STRONG, self.customer)
        weak_score, *_ = _score_ai_model(WEAK, self.customer)
        self.assertGreater(strong_score, weak_score)

    def test_probabilities_stay_in_range(self):
        _, _, _, _, a = _score_ai_model(WEAK, self.customer)
        self.assertTrue(0.0 <= a["probability_of_default"] <= 1.0)
        self.assertTrue(0.0 <= a["fraud_probability"] <= 1.0)


class AiModelPersistenceTests(TestCase):
    def test_generate_score_persists_assessment(self):
        user = User.objects.create(username="ai_customer", role=User.Role.CUSTOMER)
        CustomerProfile.objects.create(
            user=user, 
            monthly_income=80000,
            date_of_birth=datetime.date(1995, 1, 1),
            occupation="Salaried private",
            gender="Male",
            education="Bachelor's"
        )
        report = generate_score(user, algorithm=AI_MODEL)

        self.assertEqual(report.algorithm, ScoreReport.Algorithm.AI_MODEL)
        self.assertTrue(1 <= report.score <= 100)
        self.assertIn("underwriting_decision", report.ai_assessment)
        self.assertEqual(report.ai_assessment["monthly_income_used"], 80000)
        self.assertEqual(report.recommended_loan_amount, report.ai_assessment["recommended_loan_amount"])

    def test_ai_model_requires_complete_profile(self):
        user = User.objects.create(username="ai_no_profile", role=User.Role.CUSTOMER)
        with self.assertRaises(ValueError):
            generate_score(user, algorithm=AI_MODEL)

    def test_ai_model_works_with_missing_income_using_fallback(self):
        user = User.objects.create(username="ai_no_income", role=User.Role.CUSTOMER)
        CustomerProfile.objects.create(
            user=user, 
            monthly_income=None,
            date_of_birth=datetime.date(1995, 1, 1),
            occupation="Salaried private",
            gender="Male",
            education="Bachelor's"
        )
        report = generate_score(user, algorithm=AI_MODEL)
        self.assertEqual(report.ai_assessment["monthly_income_used"], 20186)


from core.ml.obligations import clean_narration_signature, extract_lender_name, detect_obligations
import pandas as pd

class ObligationDetectionTests(TestCase):
    def test_clean_narration_signature(self):
        self.assertEqual(clean_narration_signature("ACH DEBIT BAJAJ FINANCE 12345"), "BAJAJ FINANCE")
        self.assertEqual(clean_narration_signature("UPI/DR/MUTHOOT/9827349@PAYTM"), "MUTHOOT PAYTM")

    def test_extract_lender_name(self):
        self.assertEqual(extract_lender_name("ACH DEBIT BAJAJ FINSERV"), "Bajaj Finance")
        self.assertEqual(extract_lender_name("ACH DEBIT CHOLA FINANCE"), "Cholamandalam Finance")

    def test_detect_obligations_paid_and_bounced(self):
        dates = [
            "2026-01-05", "2026-02-05", "2026-03-05", "2026-04-05", "2026-05-05",
            "2026-02-06",
            "2026-01-10", "2026-05-20"
        ]
        withdrawals = [
            3500.0, 3500.0, 3500.0, 3500.0, 3500.0,
            295.0,
            100.0, 500.0
        ]
        deposits = [0.0] * len(dates)
        narrations = [
            "ACH DR BAJAJ FINANCE EMI 1",
            "ACH DR BAJAJ FINANCE EMI 2",
            "ACH DR BAJAJ FINANCE EMI 3",
            "ACH DR BAJAJ FINANCE EMI 4",
            "ACH DR BAJAJ FINANCE EMI 5",
            "BAJAJ FINANCE EMI BOUNCE CHARGES",
            "UPI TO TEA SHOP",
            "ATM CASH WITHDRAWAL"
        ]
        balances = [10000.0] * len(dates)
        
        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Withdrawal Amount": withdrawals,
            "Deposit Amount": deposits,
            "Narration": narrations,
            "Closing Balance": balances
        })
        
        obligations = detect_obligations(df)
        self.assertEqual(len(obligations), 1)
        o = obligations[0]
        self.assertEqual(o["lender"], "Bajaj Finance")
        self.assertEqual(o["amount"], 3500.0)
        self.assertEqual(o["preferred_day"], 5)
        self.assertEqual(o["status"], "Active")
        self.assertEqual(len(o["payment_timeline"]), 5)
        
    def test_detect_obligations_bounced_only(self):
        dates = [
            "2026-01-05", "2026-02-05", "2026-03-05",
            "2026-03-10"
        ]
        withdrawals = [
            3500.0, 295.0, 3500.0,
            100.0
        ]
        deposits = [0.0] * len(dates)
        narrations = [
            "ACH DR BAJAJ FINANCE EMI",
            "BAJAJ FINANCE RETURN/BOUNCE",
            "ACH DR BAJAJ FINANCE EMI",
            "UPI SHOP"
        ]
        balances = [10000.0] * len(dates)
        
        df = pd.DataFrame({
            "Date": pd.to_datetime(dates),
            "Withdrawal Amount": withdrawals,
            "Deposit Amount": deposits,
            "Narration": narrations,
            "Closing Balance": balances
        })
        
        obligations = detect_obligations(df)
        self.assertEqual(len(obligations), 1)
        o = obligations[0]
        self.assertEqual(o["status"], "Bounced")
        timeline = o["payment_timeline"]
        self.assertEqual(timeline[0]["status"], "Paid")
        self.assertEqual(timeline[1]["status"], "Bounced")
        self.assertEqual(timeline[2]["status"], "Paid")


from django.urls import reverse

class AdminDashboardVisibilityTests(TestCase):
    def setUp(self):
        # Create an admin user
        self.admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@example.com",
            password="adminpassword"
        )
        self.admin.role = User.Role.ADMIN
        self.admin.save()

        # Create an operations user
        self.ops = User.objects.create_user(
            username="ops_user",
            email="ops@example.com",
            password="opspassword"
        )
        self.ops.role = User.Role.OPS
        self.ops.save()

        # Create self-registered individual customer user (onboarded_by is None)
        self.individual_customer = User.objects.create_user(
            username="individual_customer",
            email="individual@example.com",
            password="customerpassword"
        )
        self.individual_customer.role = User.Role.CUSTOMER
        self.individual_customer.save()

        # Create customer user onboarded by ops team
        self.ops_onboarded_customer = User.objects.create_user(
            username="ops_onboarded",
            email="opsonboarded@example.com",
            password="customerpassword",
            onboarded_by=self.ops
        )
        self.ops_onboarded_customer.role = User.Role.CUSTOMER
        self.ops_onboarded_customer.save()

        # Create customer user onboarded by admin team
        self.admin_onboarded_customer = User.objects.create_user(
            username="admin_onboarded",
            email="adminonboarded@example.com",
            password="customerpassword",
            onboarded_by=self.admin
        )
        self.admin_onboarded_customer.role = User.Role.CUSTOMER
        self.admin_onboarded_customer.save()

    def test_admin_dashboard_visibility_and_stats(self):
        # Log in as admin
        self.client.login(username="admin_user", password="adminpassword")

        # Get the dashboard response
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Check stats
        stats = response.context["stats"]
        # Total users should be: admin, ops, ops_onboarded_customer, admin_onboarded_customer.
        # individual_customer should not be visible.
        self.assertEqual(stats["total_users"], 4)
        self.assertEqual(stats["customers"], 2) # ops_onboarded_customer, admin_onboarded_customer
        self.assertEqual(stats["ops_users"], 1) # ops_user
        self.assertEqual(stats["admins"], 1) # admin_user

    def test_admin_users_list_visibility(self):
        # Log in as admin
        self.client.login(username="admin_user", password="adminpassword")

        # Get the users list response
        response = self.client.get(reverse("admin_users"))
        self.assertEqual(response.status_code, 200)

        # Check users in list
        users_in_context = response.context["users"]
        usernames = [u.username for u in users_in_context]
        self.assertIn("admin_user", usernames)
        self.assertIn("ops_user", usernames)
        self.assertIn("ops_onboarded", usernames)
        self.assertIn("admin_onboarded", usernames)
        self.assertNotIn("individual_customer", usernames)

    def test_admin_edit_user_prevention(self):
        # Log in as admin
        self.client.login(username="admin_user", password="adminpassword")

        # Try to edit an onboarded user (should succeed)
        edit_url = reverse("admin_user_edit", kwargs={"pk": self.ops_onboarded_customer.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 200)

        # Try to edit an individual user (should return 404)
        invalid_edit_url = reverse("admin_user_edit", kwargs={"pk": self.individual_customer.pk})
        response = self.client.get(invalid_edit_url)
        self.assertEqual(response.status_code, 404)

    def test_admin_edit_user_full_name(self):
        # Log in as admin
        self.client.login(username="admin_user", password="adminpassword")

        # Edit profile full name of the admin onboarded customer
        edit_url = reverse("admin_user_edit", kwargs={"pk": self.admin_onboarded_customer.pk})
        
        # Ensure a profile exists first to refresh from
        from core.models import CustomerProfile
        CustomerProfile.objects.get_or_create(user=self.admin_onboarded_customer)
        
        response = self.client.post(
            edit_url,
            {
                "username": self.admin_onboarded_customer.username,
                "email": "newemail@example.com",
                "role": User.Role.CUSTOMER,
                "is_active": True,
                "mobile": "1234567890",
                "full_name": "Edited Admin Onboarded FullName",
                "password": ""
            }
        )
        self.assertEqual(response.status_code, 302)

        # Verify the profile is updated
        self.admin_onboarded_customer.profile.refresh_from_db()
        self.assertEqual(self.admin_onboarded_customer.profile.full_name, "Edited Admin Onboarded FullName")


from core.models import Document, AAConsent

class OpsDashboardVisibilityTests(TestCase):
    def setUp(self):
        # Create an operations user
        self.ops = User.objects.create_user(
            username="ops_user",
            email="ops@example.com",
            password="opspassword"
        )
        self.ops.role = User.Role.OPS
        self.ops.save()

        # Create self-registered individual customer user (onboarded_by is None)
        self.individual_customer = User.objects.create_user(
            username="individual_customer",
            email="individual@example.com",
            password="customerpassword"
        )
        self.individual_customer.role = User.Role.CUSTOMER
        self.individual_customer.save()
        CustomerProfile.objects.create(user=self.individual_customer, full_name="Individual User")

        self.indiv_doc = Document.objects.create(
            customer=self.individual_customer,
            doc_type=Document.DocType.PAN,
            status=Document.Status.UPLOADED,
            file="documents/test_pan.pdf"
        )

        # Create customer user onboarded by ops team
        self.ops_onboarded_customer = User.objects.create_user(
            username="ops_onboarded",
            email="opsonboarded@example.com",
            password="customerpassword",
            onboarded_by=self.ops
        )
        self.ops_onboarded_customer.role = User.Role.CUSTOMER
        self.ops_onboarded_customer.save()
        CustomerProfile.objects.create(user=self.ops_onboarded_customer, full_name="Onboarded User")

        self.onboarded_doc = Document.objects.create(
            customer=self.ops_onboarded_customer,
            doc_type=Document.DocType.PAN,
            status=Document.Status.UPLOADED,
            file="documents/onboarded_pan.pdf"
        )

    def test_ops_dashboard_visibility_and_stats(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Get dashboard response
        response = self.client.get(reverse("ops_dashboard"))
        self.assertEqual(response.status_code, 200)

        # Check total customer count is 1, not 2
        self.assertEqual(response.context["total_customers"], 1)
        self.assertEqual(response.context["pending_docs"], 1)

    def test_ops_customers_list_visibility(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Get customer list without query
        response = self.client.get(reverse("ops_customers"))
        self.assertEqual(response.status_code, 200)

        # Onboarded customer should be in list, individual should not
        customers = response.context["customers"]
        usernames = [c.username for c in customers]
        self.assertIn("ops_onboarded", usernames)
        self.assertNotIn("individual_customer", usernames)

        # Search by full name (should return onboarded customer)
        response_search = self.client.get(reverse("ops_customers"), {"q": "Onboarded"})
        self.assertEqual(response_search.status_code, 200)
        usernames_search = [c.username for c in response_search.context["customers"]]
        self.assertIn("ops_onboarded", usernames_search)
        self.assertNotIn("individual_customer", usernames_search)

        # Search by non-existent name (should return empty list)
        response_empty = self.client.get(reverse("ops_customers"), {"q": "NonExistentName"})
        self.assertEqual(response_empty.status_code, 200)
        self.assertEqual(len(response_empty.context["customers"]), 0)

    def test_ops_customer_detail_visibility(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Details of onboarded customer should be 200
        response = self.client.get(reverse("ops_customer_detail", kwargs={"pk": self.ops_onboarded_customer.pk}))
        self.assertEqual(response.status_code, 200)

        # Details of individual customer should be 404
        response = self.client.get(reverse("ops_customer_detail", kwargs={"pk": self.individual_customer.pk}))
        self.assertEqual(response.status_code, 404)

    def test_ops_documents_list_visibility(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Get documents response
        response = self.client.get(reverse("ops_documents"))
        self.assertEqual(response.status_code, 200)

        # Document of onboarded customer should be in context, individual should not
        docs = response.context["documents"]
        doc_ids = [d.id for d in docs]
        self.assertIn(self.onboarded_doc.id, doc_ids)
        self.assertNotIn(self.indiv_doc.id, doc_ids)

    def test_ops_review_document_prevention(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Reviewing onboarded user's document should redirect
        response = self.client.post(reverse("ops_review_document", kwargs={"pk": self.onboarded_doc.pk}), {"decision": "approve", "notes": "good"})
        self.assertEqual(response.status_code, 302)

        # Reviewing individual user's document should return 404
        response = self.client.post(reverse("ops_review_document", kwargs={"pk": self.indiv_doc.pk}), {"decision": "approve", "notes": "good"})
        self.assertEqual(response.status_code, 404)

    def test_ops_edit_customer_profile(self):
        # Log in as operations
        self.client.login(username="ops_user", password="opspassword")

        # Get edit profile page for onboarded user
        response = self.client.get(reverse("ops_edit_customer_profile", kwargs={"pk": self.ops_onboarded_customer.pk}))
        self.assertEqual(response.status_code, 200)

        # Post profile update
        response_post = self.client.post(
            reverse("ops_edit_customer_profile", kwargs={"pk": self.ops_onboarded_customer.pk}),
            {
                "full_name": "Updated Onboarded Name",
                "date_of_birth": "1990-05-15",
                "gender": "Male",
                "education": "Bachelor's",
                "occupation": "Salaried private",
                "monthly_income": 75000,
                "address": "123 Main St",
                "aadhaar_last4": "1234"
            }
        )
        self.assertEqual(response_post.status_code, 302) # redirects back to customer details

        # Verify profile updated in DB
        self.ops_onboarded_customer.profile.refresh_from_db()
        self.assertEqual(self.ops_onboarded_customer.profile.full_name, "Updated Onboarded Name")
        self.assertEqual(self.ops_onboarded_customer.profile.occupation, "Salaried private")
        self.assertEqual(self.ops_onboarded_customer.profile.monthly_income, 75000)

        # Accessing edit profile page for individual user should return 404
        response_invalid = self.client.get(reverse("ops_edit_customer_profile", kwargs={"pk": self.individual_customer.pk}))
        self.assertEqual(response_invalid.status_code, 404)

    def test_staff_user_form_creates_profile(self):
        from core.forms import StaffUserForm
        form = StaffUserForm(
            data={
                "username": "new_customer_admin_onboarded",
                "email": "newadminonboarded@example.com",
                "role": User.Role.CUSTOMER,
                "mobile": "9999988888",
                "full_name": "Admin Onboarded FullName",
                "is_active": True,
                "password": "somepassword123"
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        
        # Verify the user has a CustomerProfile with the full name populated
        self.assertEqual(user.profile.full_name, "Admin Onboarded FullName")





