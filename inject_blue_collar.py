import random
from datetime import timedelta
from django.utils import timezone
from core.models import User, ScoreReport, CustomerProfile

INDIAN_NAMES = [
    "Raju", "Suresh", "Ramesh", "Sunil", "Anil", "Deepak", "Vikash", "Rahul", 
    "Amit", "Prakash", "Manoj", "Ajay", "Santosh", "Vijay", "Ashok", 
    "Gopal", "Dinesh", "Mukesh", "Rajesh", "Pramod"
]

SURNAMES = [
    "Kumar", "Singh", "Sharma", "Yadav", "Verma", "Patil", "Das", "Chauhan",
    "Gupta", "Mishra", "Pandey", "Paswan", "Gaur", "Nishad", "Manjhi"
]

OCCUPATIONS = [
    "Plumber", "Electrician", "Delivery Partner", "Carpenter", 
    "Security Guard", "Construction Worker", "Factory Worker", 
    "Painter", "Mechanic", "Driver", "Tailor", "Cleaner", 
    "Welder", "Gardener", "Machine Operator"
]

def run():
    # Strictly find an Operations user to act as the onboarder
    ops_user = User.objects.filter(role=User.Role.OPS).first()

    if not ops_user:
        print("No operations user found. Please create an OPS user first.")
        return

    now = timezone.now()
    generated_count = 0

    print("Generating 20 Indian blue-collar borrowers...")
    for _ in range(20):
        first_name = random.choice(INDIAN_NAMES)
        last_name = random.choice(SURNAMES)
        full_name = f"{first_name} {last_name}"
        
        idx = random.randint(1000, 999999)
        username = f"{first_name.lower()}_{idx}"
        email = f"{username}@example.com"
        
        customer = User.objects.create(
            username=username,
            email=email,
            role=User.Role.CUSTOMER,
            onboarded_by=ops_user
        )
        customer.set_password("password123")
        customer.save()
        
        occupation = random.choice(OCCUPATIONS)
        monthly_income = random.randint(12000, 25000)
        
        CustomerProfile.objects.create(
            user=customer, 
            full_name=full_name,
            occupation=occupation,
            monthly_income=monthly_income
        )
        
        # Score range 50 to 75 as requested
        score = random.randint(50, 75)
        
        if score >= 80: band = "excellent"
        elif score >= 70: band = "very_good"
        elif score >= 60: band = "good"
        elif score >= 50: band = "fair"
        else: band = "poor"
        
        # Ensure the score is generated in August
        august_day = random.randint(1, 31)
        generated_at = now.replace(
            month=8, 
            day=august_day, 
            hour=random.randint(0, 23), 
            minute=random.randint(0, 59),
            second=random.randint(0, 59)
        )
        
        # Slightly weaker financial metrics for lower scores
        report = ScoreReport(
            customer=customer,
            algorithm="ai_model",
            score=score,
            band=band,
            income_consistency=random.uniform(0.3, 0.7),
            expense_ratio=random.uniform(0.6, 0.9), # High expense ratio
            savings_ratio=random.uniform(0.05, 0.2), # Low savings
            payment_timeliness=random.uniform(0.4, 0.8),
            transaction_frequency=random.uniform(0.3, 0.7),
            bounce_rate=random.uniform(0.05, 0.2), # Higher bounce rate
            digital_engagement=random.uniform(0.1, 0.5),
            top_positive_factors=["Steady employment history"],
            top_negative_factors=["High expense to income ratio", "Low monthly savings"],
            recommended_loan_amount=random.randint(2, 5) * 5000, # 10k to 25k recommended loan
        )
        report.save()
        
        # Overwrite auto_now_add field
        ScoreReport.objects.filter(id=report.id).update(generated_at=generated_at)
        
        generated_count += 1
        
    print(f"Successfully injected {generated_count} blue-collar borrowers with scores between 50 and 75.")

if __name__ == '__main__':
    run()
