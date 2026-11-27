from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator
from decimal import Decimal


class UserProfile(models.Model):
    """User profile extending default Django User with wealth persona & profile picture."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    occupation = models.CharField(max_length=150, default="Private Wealth Member")
    annual_ctc = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Annual CTC in INR (e.g., 40 LPA = 40,00,000)"
    )
    avatar = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=100, default="Bengaluru / Mumbai")
    bio = models.TextField(blank=True, default="Private Wealth Portfolio Tracker")
    created_at = models.DateTimeField(auto_now_add=True)

    def monthly_salary(self):
        """Calculates default monthly salary based on CTC."""
        return (self.annual_ctc / Decimal('12.00')).quantize(Decimal('0.01'))

    @property
    def has_avatar(self):
        """Returns True only if an avatar is set and its file exists on disk/storage."""
        if not self.avatar or not self.avatar.name:
            return False
        try:
            return self.avatar.storage.exists(self.avatar.name)
        except Exception:
            return False

    def __str__(self):
        return f"{self.user.username} - {self.occupation}"


class Asset(models.Model):
    """Tracks high-value assets (Villa, Hayabusa, BMW S1000RR, BMW M3, etc.)."""
    
    TYPE_CHOICES = [
        ('MOTORCYCLE', 'Motorcycle'),
        ('CAR', 'Performance Car'),
        ('REAL_ESTATE', 'Real Estate / Villa'),
        ('EQUITY', 'Company Stocks & ESOPs'),
        ('LUXURY', 'Jewelry & Watches'),
        ('OTHER', 'Other Asset'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=120)
    asset_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='OTHER')
    tag = models.CharField(max_length=40, default="ASSET", help_text="e.g. MOTORCYCLE 01, CAR 01, REAL ESTATE")
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    current_valuation = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    image = models.ImageField(upload_to='asset_images/', blank=True, null=True)
    image_url = models.CharField(max_length=500, blank=True, help_text="URL or static image path")
    pinterest_url = models.URLField(max_length=500, blank=True, null=True, help_text="Pinterest reference link")
    specification = models.CharField(max_length=255, blank=True, help_text="Specs, e.g. 1340cc 197 HP / 4.0L Twin Turbo")
    is_default = models.BooleanField(default=True, help_text="Persist across all financial months")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-current_valuation']

    def __str__(self):
        return f"{self.name} (₹{self.current_valuation:,.2f})"


class Liability(models.Model):
    """Tracks debts, mortgages, vehicle loans, and recurring EMIs."""

    TYPE_CHOICES = [
        ('MORTGAGE', 'Villa Home Loan / Mortgage'),
        ('VEHICLE_LOAN', 'Vehicle Financing Loan'),
        ('PERSONAL_LOAN', 'Personal Loan'),
        ('CREDIT_CARD', 'Credit Line / Cards'),
        ('OTHER', 'Other Liability'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liabilities')
    title = models.CharField(max_length=150)
    liability_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='OTHER')
    total_principal = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    monthly_emi = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('8.50'), help_text="Annual interest %")
    remaining_balance = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    lender = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=True, help_text="Persist across all 12 financial months")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Liabilities'
        ordering = ['-monthly_emi']

    def __str__(self):
        return f"{self.title} (EMI: ₹{self.monthly_emi:,.2f}/mo)"


class Transaction(models.Model):
    """Income and Expense ledger items with categorization and asset association."""

    TYPE_CHOICES = [
        ('EXPENSE', 'Expense'),
        ('INCOME', 'Income'),
    ]

    CATEGORY_CHOICES = [
        # Income categories
        ('SALARY', 'Monthly Salary (JPMC)'),
        ('ESOP', 'ESOPs & Company Stocks'),
        ('FREELANCE', 'Freelancing'),
        ('GIFTS', 'Gifts & Bonuses'),
        ('OTHER_INCOME', 'Other Income'),
        
        # Expense categories
        ('FOOD', 'Food Expenses & Groceries'),
        ('HOUSEHOLD', 'Household Expenses'),
        ('VEHICLE_FUEL', 'Fuel & Petrol'),
        ('VEHICLE_MAINT', 'Vehicle Servicing & Repairs'),
        ('VEHICLE_CONSUMABLES', 'Tyres & Consumables'),
        ('VEHICLE_INSURANCE', 'Vehicle Insurance & Tax'),
        ('TRAVEL', 'Traveling Expenses'),
        ('HEALTH', 'Health & Medical Expenses'),
        ('VILLA_MAINT', 'Villa Maintenance & Utilities'),
        ('LIFESTYLE', 'Lifestyle & Entertainment'),
        ('OTHER_EXPENSE', 'Other Expenses'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    title = models.CharField(max_length=200, help_text="Brief description, e.g. Full tank petrol")
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='EXPENSE')
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='OTHER_EXPENSE')
    asset = models.ForeignKey(
        Asset, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='transactions',
        help_text="Specific asset linked to this transaction (e.g. BMW M3, Hayabusa, Villa)"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date = models.DateField()
    financial_month = models.PositiveSmallIntegerField(
        default=1,
        help_text="Financial month index (1 for Month 1 / April ... 12 for Month 12 / March)"
    )
    payment_method = models.CharField(max_length=50, default='Bank Transfer')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        sign = "+" if self.transaction_type == 'INCOME' else "-"
        return f"{self.title} | {sign}₹{self.amount:,.2f} ({self.get_category_display()})"


class MonthlyFinancialPlan(models.Model):
    """
    Manages 1 financial year (12 months) projections and defaults.
    Users can toggle items as income or expense and adjust per month.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_plans')
    financial_year = models.CharField(max_length=20, default="2026-2027")
    month_number = models.PositiveSmallIntegerField(help_text="1 to 12")
    month_name = models.CharField(max_length=20)
    
    # Incomes
    salary_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('333333.33'))
    stocks_esops = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('50000.00'))
    freelance_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('40000.00'))
    gifts_bonus = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    # Liabilities & EMIs
    liabilities_emi = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('35000.00'))
    
    # Core Expenses
    food_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('25000.00'))
    household_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('20000.00'))
    vehicle_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('45000.00'))
    travel_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('15000.00'))
    health_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('10000.00'))
    villa_maintenance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('18500.00'))
    
    is_customized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'financial_year', 'month_number')
        ordering = ['month_number']

    def other_income(self):
        return self.freelance_income + self.gifts_bonus

    def living_and_health_expenses(self):
        return (
            self.food_expenses +
            self.household_expenses +
            self.travel_expenses +
            self.health_expenses
        )

    def total_projected_income(self):
        return self.salary_income + self.stocks_esops + self.freelance_income + self.gifts_bonus

    def total_projected_expense(self):
        return (
            self.liabilities_emi + 
            self.food_expenses + 
            self.household_expenses + 
            self.vehicle_expenses + 
            self.travel_expenses + 
            self.health_expenses + 
            self.villa_maintenance
        )

    def projected_surplus(self):
        return self.total_projected_income() - self.total_projected_expense()

    def __str__(self):
        return f"{self.user.username} - FY {self.financial_year} - {self.month_name}"


# Auto create UserProfile when a User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
