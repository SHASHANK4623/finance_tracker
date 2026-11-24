from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from finance.models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan
from decimal import Decimal
import datetime


class Command(BaseCommand):
    help = "Seeds initial luxury wealth data for JPMC Software Engineer persona (Shashank)"

    def handle(self, *args, **options):
        self.stdout.write("Seeding Monarch Wealth database...")

        # 1. Create or get user
        username = "shashank"
        email = "shashank@jpmc.com"
        password = "@2468Shashank"

        user, created = User.objects.get_or_create(username=username, defaults={"email": email, "first_name": "Shashank", "last_name": "K"})
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()

        # Update profile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.occupation = "Software Engineer @ JPMC"
        profile.annual_ctc = Decimal('4000000.00')  # 40 LPA
        profile.location = "Bengaluru / Mumbai"
        profile.bio = "Software Engineer @ J.P. Morgan Chase | Private Wealth & Supercar Collector"
        profile.phone = "+91 98765 43210"
        profile.save()

        self.stdout.write(self.style.SUCCESS(f"User '{username}' ready with 40 LPA JPMC profile."))

        # 2. Seed Assets
        assets_data = [
            {
                "name": "Modified Suzuki Hayabusa",
                "asset_type": "MOTORCYCLE",
                "tag": "MOTORCYCLE 01",
                "purchase_price": Decimal('2100000.00'),
                "current_valuation": Decimal('2300000.00'),  # 23 Lakhs
                "image_url": "images/hayabusa_modified.jpg",
                "specification": "1,340cc · 197 bhp · Custom Akrapovič Exhaust & Brembo brakes",
                "is_default": True
            },
            {
                "name": "BMW S1000RR",
                "asset_type": "MOTORCYCLE",
                "tag": "MOTORCYCLE 02",
                "purchase_price": Decimal('2400000.00'),
                "current_valuation": Decimal('2500000.00'),  # 25 Lakhs
                "image_url": "images/bmw_s1000rr.jpg",
                "specification": "999cc · 205 bhp · M Carbon Package & Dynamic Damping",
                "is_default": True
            },
            {
                "name": "BMW M3 Competition",
                "asset_type": "CAR",
                "tag": "CAR 01",
                "purchase_price": Decimal('13500000.00'),
                "current_valuation": Decimal('14000000.00'),  # 1.40 Cr
                "image_url": "images/bmw_m3.jpg",
                "specification": "3.0L TwinPower Turbo inline-6 · 503 bhp · M xDrive",
                "is_default": True
            },
            {
                "name": "Private Luxury Villa",
                "asset_type": "REAL_ESTATE",
                "tag": "REAL ESTATE",
                "purchase_price": Decimal('8500000.00'),
                "current_valuation": Decimal('10000000.00'),  # 1.00 Cr
                "image_url": "images/villa.jpg",
                "specification": "4,800 sq.ft private estate · 4 Bed Suites · Landscape Garden",
                "is_default": True
            },
        ]

        asset_objects = {}
        for adata in assets_data:
            asset, _ = Asset.objects.update_or_create(
                user=user,
                name=adata["name"],
                defaults=adata
            )
            asset_objects[adata["name"]] = asset

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(assets_data)} high-value assets."))

        # 3. Seed Liabilities
        liabilities_data = [
            {
                "title": "Private Villa Mortgage (Home Loan)",
                "liability_type": "MORTGAGE",
                "total_principal": Decimal('6000000.00'),
                "monthly_emi": Decimal('35000.00'),
                "interest_rate": Decimal('8.40'),
                "remaining_balance": Decimal('5120000.00'),
                "lender": "HDFC Premium Banking",
                "is_active": True,
                "is_default": True
            },
            {
                "title": "BMW M3 Vehicle Loan",
                "liability_type": "VEHICLE_LOAN",
                "total_principal": Decimal('7000000.00'),
                "monthly_emi": Decimal('18000.00'),
                "interest_rate": Decimal('7.85'),
                "remaining_balance": Decimal('5800000.00'),
                "lender": "BMW Financial Services",
                "is_active": True,
                "is_default": True
            }
        ]

        for ldata in liabilities_data:
            Liability.objects.update_or_create(
                user=user,
                title=ldata["title"],
                defaults=ldata
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(liabilities_data)} liabilities."))

        # 4. Seed 1 Financial Year (12 Months)
        month_names = [
            "April 2026", "May 2026", "June 2026", "July 2026", 
            "August 2026", "September 2026", "October 2026", "November 2026", 
            "December 2026", "January 2027", "February 2027", "March 2027"
        ]

        for i, m_name in enumerate(month_names, start=1):
            MonthlyFinancialPlan.objects.update_or_create(
                user=user,
                financial_year="2026-2027",
                month_number=i,
                defaults={
                    "month_name": m_name,
                    "salary_income": Decimal('333333.33'),
                    "stocks_esops": Decimal('50000.00'),
                    "freelance_income": Decimal('40000.00'),
                    "gifts_bonus": Decimal('25000.00') if i in [7, 12] else Decimal('0.00'),
                    "liabilities_emi": Decimal('53000.00'),
                    "food_expenses": Decimal('25000.00'),
                    "household_expenses": Decimal('20000.00'),
                    "vehicle_expenses": Decimal('45000.00'),
                    "travel_expenses": Decimal('15000.00'),
                    "health_expenses": Decimal('10000.00'),
                    "villa_maintenance": Decimal('18500.00'),
                    "is_customized": False
                }
            )

        self.stdout.write(self.style.SUCCESS("Seeded 1 Financial Year (12 months) financial plans."))

        # 5. Seed Transactions (From Prototype Activity)
        transactions_data = [
            {
                "title": "JPMC Monthly Salary Credit",
                "transaction_type": "INCOME",
                "category": "SALARY",
                "amount": Decimal('450000.00'),
                "date": datetime.date(2026, 11, 1),
                "financial_month": 8,
                "asset": None,
                "payment_method": "Direct Deposit",
                "notes": "Salary + Monthly Performance Allowance"
            },
            {
                "title": "Freelance Cloud Architecture Advisory",
                "transaction_type": "INCOME",
                "category": "FREELANCE",
                "amount": Decimal('65000.00'),
                "date": datetime.date(2026, 11, 2),
                "financial_month": 8,
                "asset": None,
                "payment_method": "Wire Transfer",
                "notes": "High performance distributed systems advisory"
            },
            {
                "title": "Comprehensive Vehicle Insurance Premium",
                "transaction_type": "EXPENSE",
                "category": "VEHICLE_INSURANCE",
                "amount": Decimal('18000.00'),
                "date": datetime.date(2026, 11, 3),
                "financial_month": 8,
                "asset": asset_objects["BMW M3 Competition"],
                "payment_method": "HDFC Credit Card",
                "notes": "Annual zero-dep cover installment"
            },
            {
                "title": "Shell V-Power 100 Octane Fuel",
                "transaction_type": "EXPENSE",
                "category": "VEHICLE_FUEL",
                "amount": Decimal('4200.00'),
                "date": datetime.date(2026, 11, 4),
                "financial_month": 8,
                "asset": asset_objects["BMW M3 Competition"],
                "payment_method": "UPI",
                "notes": "Full tank high-octane petrol"
            },
            {
                "title": "Michelin Road 6 Hypersport Tyres",
                "transaction_type": "EXPENSE",
                "category": "VEHICLE_CONSUMABLES",
                "amount": Decimal('28000.00'),
                "date": datetime.date(2026, 11, 5),
                "financial_month": 8,
                "asset": asset_objects["BMW S1000RR"],
                "payment_method": "Credit Card",
                "notes": "Rear & Front set replacement"
            },
            {
                "title": "Custom Brembo Racing Brake Pads",
                "transaction_type": "EXPENSE",
                "category": "VEHICLE_MAINT",
                "amount": Decimal('15500.00'),
                "date": datetime.date(2026, 11, 6),
                "financial_month": 8,
                "asset": asset_objects["Modified Suzuki Hayabusa"],
                "payment_method": "UPI",
                "notes": "Brembo racing compound pads"
            },
            {
                "title": "Villa Landscaping & Pool Maintenance",
                "transaction_type": "EXPENSE",
                "category": "VILLA_MAINT",
                "amount": Decimal('12000.00'),
                "date": datetime.date(2026, 11, 8),
                "financial_month": 8,
                "asset": asset_objects["Private Luxury Villa"],
                "payment_method": "Net Banking",
                "notes": "Fortnightly villa care & filtration service"
            },
            {
                "title": "Organic Gourmet Groceries",
                "transaction_type": "EXPENSE",
                "category": "FOOD",
                "amount": Decimal('8500.00'),
                "date": datetime.date(2026, 11, 10),
                "financial_month": 8,
                "asset": None,
                "payment_method": "Apple Pay / Card",
                "notes": "Household groceries"
            },
        ]

        for tdata in transactions_data:
            Transaction.objects.update_or_create(
                user=user,
                title=tdata["title"],
                date=tdata["date"],
                defaults=tdata
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded {len(transactions_data)} initial transactions."))
        self.stdout.write(self.style.SUCCESS("All Monarch Wealth initial data seeded successfully!"))
