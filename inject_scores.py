import random
from datetime import timedelta
from django.utils import timezone
from core.models import User, ScoreReport, CustomerProfile

def run():
    ops_user = User.objects.filter(role__in=[User.Role.ADMIN, User.Role.OPS]).first()
    if not ops_user:
        ops_user = User.objects.filter(is_superuser=True).first()

    if not ops_user:
        print("No ops/admin user found to act as onboarder.")
        return

    now = timezone.now()

    # Create 15 customers
    for i in range(15):
        idx = random.randint(1000, 999999)
        username = f"dummy_user_{idx}"
        email = f"{username}@example.com"
        
        customer = User.objects.create(
            username=username,
            email=email,
            role=User.Role.CUSTOMER,
            onboarded_by=ops_user
        )
        customer.set_password("password123")
        customer.save()
        
        CustomerProfile.objects.create(user=customer, full_name=f"Dummy User {idx}")
        
        score = random.randint(50, 95)
        if score >= 80: band = "excellent"
        elif score >= 70: band = "very_good"
        elif score >= 60: band = "good"
        elif score >= 50: band = "fair"
        else: band = "poor"
        
        days_ago = random.randint(0, 30)
        generated_at = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        
        report = ScoreReport(
            customer=customer,
            algorithm="ai_model",
            score=score,
            band=band,
            income_consistency=random.uniform(0.5, 1.0),
            expense_ratio=random.uniform(0.3, 0.8),
            savings_ratio=random.uniform(0.1, 0.5),
            payment_timeliness=random.uniform(0.7, 1.0),
            transaction_frequency=random.uniform(0.4, 0.9),
            bounce_rate=random.uniform(0.0, 0.1),
            digital_engagement=random.uniform(0.3, 0.9),
            top_positive_factors=["Stable Income"],
            top_negative_factors=[],
            recommended_loan_amount=random.randint(1, 10) * 10000,
        )
        report.save()
        
        # Overwrite auto_now_add field
        ScoreReport.objects.filter(id=report.id).update(generated_at=generated_at)
        
    print("Successfully injected 15 customers and score reports.")

if __name__ == '__main__':
    run()
