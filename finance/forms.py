from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan
from decimal import Decimal
import os


class EmailLoginForm(forms.Form):
    """Authenticates users using their registered email address and password."""

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address',
            'autofocus': 'autofocus',
        })
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••••••',
        })
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        email = (cleaned_data.get('email') or '').strip()
        password = cleaned_data.get('password')

        if email and password:
            candidates = User.objects.filter(email__iexact=email)
            inactive_match = False

            for candidate in candidates:
                user = authenticate(self.request, username=candidate.username, password=password)
                if user is not None:
                    self.user_cache = user
                    break
                if candidate.check_password(password) and not candidate.is_active:
                    inactive_match = True

            if self.user_cache is None:
                if inactive_match:
                    raise ValidationError("This account is inactive. Please contact an administrator.")
                raise ValidationError("Invalid email address or password.")

        return cleaned_data

    def get_user(self):
        return self.user_cache


class TransactionForm(forms.ModelForm):
    """Form for logging Income & Expense transactions with JS validation support."""
    
    financial_month = forms.IntegerField(
        required=False,
        initial=1,
        widget=forms.Select(
            choices=[(i, f"Month {i}") for i in range(1, 13)],
            attrs={'class': 'form-select'}
        )
    )

    class Meta:
        model = Transaction
        fields = [
            'title', 
            'transaction_type', 
            'category', 
            'asset', 
            'amount', 
            'date', 
            'financial_month', 
            'payment_method', 
            'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'e.g. Shell V-Power 100 Petrol', 
                'required': 'required'
            }),
            'transaction_type': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'asset': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input', 
                'placeholder': '0.00', 
                'step': '0.01', 
                'min': '0.01',
                'required': 'required'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-input', 
                'type': 'date', 
                'required': 'required'
            }),
            'financial_month': forms.Select(
                choices=[(i, f"Month {i}") for i in range(1, 13)],
                attrs={'class': 'form-select'}
            ),
            'payment_method': forms.TextInput(attrs={
                'class': 'form-input', 
                'placeholder': 'e.g. UPI, HDFC Card, Bank Transfer'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea', 
                'rows': 2, 
                'placeholder': 'Optional invoice reference, mileage, workshop...'
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None or amount <= Decimal('0.00'):
            raise ValidationError("Transaction amount must be greater than zero.")
        return amount

    def clean_financial_month(self):
        fm = self.cleaned_data.get('financial_month')
        if not fm:
            date = self.cleaned_data.get('date')
            if date:
                fm = (date.month - 4) % 12 + 1
            else:
                fm = 1
        return fm


class UserProfileForm(forms.ModelForm):
    """Profile management form with avatar upload validation."""
    
    first_name = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    last_name = forms.CharField(max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={'class': 'form-input'}))

    class Meta:
        model = UserProfile
        fields = ['occupation', 'annual_ctc', 'avatar', 'phone', 'location', 'bio']
        widgets = {
            'occupation': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Software Engineer @ JPMC'}),
            'annual_ctc': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '4000000.00', 'step': '10000'}),
            'avatar': forms.FileInput(attrs={'class': 'form-file-input', 'accept': 'image/*'}),
            'phone': forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210'}),
            'location': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Bengaluru / Mumbai'}),
            'bio': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        if avatar and hasattr(avatar, 'size'):
            # Max 3 MB validation
            max_size = 3 * 1024 * 1024
            if avatar.size > max_size:
                raise ValidationError("Profile image size cannot exceed 3MB.")
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                raise ValidationError("Allowed image formats are .jpg, .jpeg, .png, and .webp.")
        return avatar

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and self.instance and self.instance.user:
            if User.objects.filter(email=email).exclude(pk=self.instance.user.pk).exists():
                raise ValidationError("A user with this email address already exists.")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)
        user.email = self.cleaned_data.get('email', user.email)
        if commit:
            user.save()
            profile.save()
        return profile


class AssetForm(forms.ModelForm):
    """Form to add or edit luxury assets."""
    
    class Meta:
        model = Asset
        fields = ['name', 'asset_type', 'tag', 'purchase_price', 'current_valuation', 'specification', 'pinterest_url', 'image', 'image_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. BMW M3 Competition'}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'tag': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. CAR 01, MOTORCYCLE 01'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000'}),
            'current_valuation': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000'}),
            'specification': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Specs / Details'}),
            'pinterest_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://pin.it/...'}),
            'image': forms.FileInput(attrs={'class': 'form-file-input', 'accept': 'image/*'}),
            'image_url': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'images/hayabusa_modified.jpg'}),
        }


class PropertyForm(forms.ModelForm):
    """Form tailored specifically for luxury Real Estate and Residential property."""

    class Meta:
        model = Asset
        fields = ['name', 'purchase_price', 'current_valuation', 'specification', 'pinterest_url', 'image', 'image_url']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Private Luxury Villa Estate, Seaside Penthouse'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '8500000.00', 'step': '10000'}),
            'current_valuation': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '10000000.00', 'step': '10000'}),
            'specification': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 4,800 sq ft · Private estate · 4 beds · Landscaped pool'}),
            'pinterest_url': forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://pin.it/...'}),
            'image': forms.FileInput(attrs={'class': 'form-file-input', 'accept': 'image/*'}),
            'image_url': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'images/villa.jpg'}),
        }


class LiabilityForm(forms.ModelForm):
    """Form to modify debts, mortgages, and vehicle loans."""

    class Meta:
        model = Liability
        fields = ['title', 'liability_type', 'total_principal', 'monthly_emi', 'interest_rate', 'remaining_balance', 'lender', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Villa Mortgage'}),
            'liability_type': forms.Select(attrs={'class': 'form-select'}),
            'total_principal': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000'}),
            'monthly_emi': forms.NumberInput(attrs={'class': 'form-input', 'step': '100'}),
            'interest_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.05'}),
            'remaining_balance': forms.NumberInput(attrs={'class': 'form-input', 'step': '1000'}),
            'lender': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. HDFC Premium Banking'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }


class MonthlyFinancialPlanForm(forms.ModelForm):
    """Form to modify a specific month's financial projection without range constraints."""

    class Meta:
        model = MonthlyFinancialPlan
        fields = [
            'salary_income',
            'stocks_esops',
            'freelance_income',
            'gifts_bonus',
            'liabilities_emi',
            'food_expenses',
            'household_expenses',
            'vehicle_expenses',
            'travel_expenses',
            'health_expenses',
            'villa_maintenance'
        ]
        widgets = {
            'salary_income': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'stocks_esops': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'freelance_income': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'gifts_bonus': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'liabilities_emi': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'food_expenses': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'household_expenses': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'vehicle_expenses': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'travel_expenses': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'health_expenses': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
            'villa_maintenance': forms.NumberInput(attrs={'class': 'form-input', 'step': 'any', 'min': '0'}),
        }


class UserRegisterForm(forms.ModelForm):
    """User registration form with password confirmation, job role, and annual salary (minimum 10k)."""
    job_role = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Software Engineer, Doctor, Financial Analyst', 'required': 'required'})
    )
    annual_salary = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('10000.00'),
        required=True,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': 'e.g. 1200000.00 (Minimum ₹10,000 INR)', 'step': 'any', 'min': '10000.00', 'required': 'required'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Create secure password', 'required': 'required'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm your password', 'required': 'required'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose username', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'name@example.com', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
        }

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match.")
        return confirm_password

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email


class AdminUserCreationForm(forms.ModelForm):
    """Admin form to create a new user with full role & wealth profile."""
    job_role = forms.CharField(
        max_length=150,
        required=True,
        initial='Private Wealth Member',
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Director of Engineering, VP Finance'})
    )
    annual_salary = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=True,
        initial=Decimal('1200000.00'),
        widget=forms.NumberInput(attrs={'class': 'form-input', 'placeholder': '1200000.00', 'step': '10000'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Temporary or permanent password', 'required': 'required'})
    )
    is_staff = forms.BooleanField(
        required=False,
        label="Grant Administrator Privileges",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        label="Account Active",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Username', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'user@example.com', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Last Name'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email


class AdminUserEditForm(forms.ModelForm):
    """Admin form to modify existing user details, roles, and compensation."""
    job_role = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Senior Wealth Analyst'})
    )
    annual_salary = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.00'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-input', 'step': '10000'})
    )
    is_staff = forms.BooleanField(
        required=False,
        label="Administrator Status",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    is_active = forms.BooleanField(
        required=False,
        label="Active Account",
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'class': 'form-input', 'required': 'required'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)
        if profile:
            self.fields['job_role'].initial = profile.occupation
            self.fields['annual_salary'].initial = profile.annual_ctc

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if self.instance and self.instance.pk:
            if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
                raise ValidationError("A user with this email address already exists.")
        return email


class AdminPasswordResetForm(forms.Form):
    """Admin form to directly reset a user's password."""
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'New password', 'required': 'required'}),
        label="New Password"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Confirm new password', 'required': 'required'}),
        label="Confirm New Password"
    )

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get('new_password')
        cpw = cleaned_data.get('confirm_password')
        if pw and cpw and pw != cpw:
            raise ValidationError("Passwords do not match.")
        return cleaned_data
