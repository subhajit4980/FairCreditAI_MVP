"""Seed demo users + the four investor-pitch personas from the build guide."""

from django.core.management.base import BaseCommand

from core.models import CustomerProfile, User
from core.scoring import generate_score


PERSONAS = [
    {
        "username": "ramesh",
        "full_name": "Ramesh Kumar",
        "occupation": "Kirana shop owner",
        "monthly_income": 70000,
        "mobile": "9000011111",
        "pan": "ABCDE1234F",
        "date_of_birth": "1990-05-15",
        "gender": "Male",
        "education": "Bachelor's",
    },
    {
        "username": "priya",
        "full_name": "Priya Iyer",
        "occupation": "Salaried (debit-first)",
        "monthly_income": 95000,
        "mobile": "9000022222",
        "pan": "BCDEF2345G",
        "date_of_birth": "1995-10-20",
        "gender": "Female",
        "education": "Master's",
    },
    {
        "username": "anil",
        "full_name": "Anil Verma",
        "occupation": "Gig worker (rideshare)",
        "monthly_income": 42000,
        "mobile": "9000033333",
        "pan": "CDEFG3456H",
        "date_of_birth": "1998-03-12",
        "gender": "Male",
        "education": "High School",
    },
    {
        "username": "lakshmi",
        "full_name": "Lakshmi Devi",
        "occupation": "SHG member, microenterprise",
        "monthly_income": 28000,
        "mobile": "9000044444",
        "pan": "DEFGH4567I",
        "date_of_birth": "1985-07-25",
        "gender": "Female",
        "education": "Graduate",
    },
]


class Command(BaseCommand):
    help = "Seed an admin, an ops user, and the four demo customer personas."

    def handle(self, *args, **options):
        admin, created = User.objects.get_or_create(
            username="admin",
            defaults={"role": User.Role.ADMIN, "is_staff": True, "is_superuser": True, "email": "admin@faircredit.example"},
        )
        if created:
            admin.set_password("admin12345")
            admin.role = User.Role.ADMIN
            admin.is_staff = True
            admin.is_superuser = True
            admin.save()
            self.stdout.write(self.style.SUCCESS("Created admin / admin12345"))

        ops, created = User.objects.get_or_create(
            username="ops",
            defaults={"role": User.Role.OPS, "is_staff": True, "email": "ops@faircredit.example"},
        )
        if created:
            ops.set_password("ops12345")
            ops.role = User.Role.OPS
            ops.is_staff = True
            ops.save()
            self.stdout.write(self.style.SUCCESS("Created ops / ops12345"))

        for p in PERSONAS:
            user, created = User.objects.get_or_create(
                username=p["username"],
                defaults={
                    "role": User.Role.CUSTOMER,
                    "mobile": p["mobile"],
                    "pan": p["pan"],
                    "email": f"{p['username']}@example.com",
                },
            )
            if created:
                user.set_password("demo12345")
                user.save()
                import datetime
                CustomerProfile.objects.create(
                    user=user,
                    full_name=p["full_name"],
                    occupation=p["occupation"],
                    monthly_income=p["monthly_income"],
                    date_of_birth=datetime.date.fromisoformat(p["date_of_birth"]),
                    gender=p["gender"],
                    education=p["education"],
                )
                generate_score(user)
                self.stdout.write(self.style.SUCCESS(f"Created customer {p['username']} / demo12345"))
        self.stdout.write(self.style.SUCCESS("Seed complete."))
