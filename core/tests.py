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
