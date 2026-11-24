from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db.models import Sum, Q, Count
from decimal import Decimal
from functools import wraps
import json
import datetime

from .models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan
from .forms import (
    TransactionForm, 
    UserProfileForm, 
    UserRegisterForm, 
    AssetForm, 
    PropertyForm,
    LiabilityForm, 
    MonthlyFinancialPlanForm,
    AdminUserCreationForm,
    AdminUserEditForm,
    AdminPasswordResetForm
)


def init_user_financial_plan(user, profile=None):
    """Initializes 12 financial months for the user based strictly on their entered salary."""
    existing = MonthlyFinancialPlan.objects.filter(user=user).order_by('month_number')
    if existing.exists():
        return existing

    if profile is None:
        profile, _ = UserProfile.objects.get_or_create(user=user)

    raw_salary = profile.monthly_salary() if profile else Decimal('0.00')
    monthly_salary = max(raw_salary, Decimal('10000.00')) if raw_salary > Decimal('0.00') else Decimal('10000.00')

    month_names = [
        "April 2026", "May 2026", "June 2026", "July 2026", 
        "August 2026", "September 2026", "October 2026", "November 2026", 
        "December 2026", "January 2027", "February 2027", "March 2027"
    ]

    # No ranged percentages; baseline minimum 10k (10,000 INR) for monthly living categories
    base_min = Decimal('10000.00')

    for i, m_name in enumerate(month_names, start=1):
        MonthlyFinancialPlan.objects.create(
            user=user,
            financial_year="2026-2027",
            month_number=i,
            month_name=m_name,
            salary_income=monthly_salary,
            stocks_esops=Decimal('0.00'),
            freelance_income=Decimal('0.00'),
            gifts_bonus=Decimal('0.00'),
            liabilities_emi=Decimal('0.00'),
            food_expenses=base_min,
            household_expenses=base_min,
            vehicle_expenses=Decimal('0.00'),
            travel_expenses=base_min,
            health_expenses=base_min,
            villa_maintenance=Decimal('0.00'),
        )
    return MonthlyFinancialPlan.objects.filter(user=user).order_by('month_number')


def init_user_default_assets(user):
    """Initializes default luxury property and vehicles ONLY for the demo admin account ('shashank')."""
    if user.username != 'shashank':
        return None
    villa = Asset.objects.filter(user=user, asset_type='REAL_ESTATE').first()
    if not villa:
        villa = Asset.objects.create(
            user=user,
            name="Private Luxury Villa Estate",
            asset_type="REAL_ESTATE",
            tag="REAL ESTATE",
            purchase_price=Decimal('8500000.00'),
            current_valuation=Decimal('10000000.00'),
            image_url="images/villa.jpg",
            specification="4,800 sq ft · Private estate · 4 beds · Landscaped grounds",
            is_default=True
        )

    if not Asset.objects.filter(user=user, asset_type='CAR').exists():
        Asset.objects.create(
            user=user,
            name="BMW M3 Competition",
            asset_type="CAR",
            tag="CAR 01",
            purchase_price=Decimal('13500000.00'),
            current_valuation=Decimal('14000000.00'),
            image="asset_images/bmw_m3.jpg",
            image_url="images/bmw_m3.jpg",
            specification="3.0L TwinPower Turbo inline-6 · 503 bhp · M xDrive",
            is_default=True
        )

    if not Asset.objects.filter(user=user, asset_type='MOTORCYCLE').exists():
        Asset.objects.create(
            user=user,
            name="BMW S1000RR",
            asset_type="MOTORCYCLE",
            tag="MOTORCYCLE 01",
            purchase_price=Decimal('2400000.00'),
            current_valuation=Decimal('2500000.00'),
            image="asset_images/bmw_s1000rr.jpg",
            image_url="images/bmw_s1000rr.jpg",
            specification="999cc · 205 bhp · M Carbon Package & Dynamic Damping",
            is_default=True
        )
        Asset.objects.create(
            user=user,
            name="Modified Suzuki Hayabusa",
            asset_type="MOTORCYCLE",
            tag="MOTORCYCLE 02",
            purchase_price=Decimal('2100000.00'),
            current_valuation=Decimal('2300000.00'),
            image="asset_images/hayabusa_modified.jpg",
            image_url="images/hayabusa_modified.jpg",
            specification="1,340cc · 197 bhp · Custom Akrapovič Exhaust & Brembo brakes",
            is_default=True
        )

    if not Liability.objects.filter(user=user, liability_type='MORTGAGE').exists():
        Liability.objects.create(
            user=user,
            title="Private Villa Mortgage (Home Loan)",
            liability_type="MORTGAGE",
            total_principal=Decimal('6800000.00'),
            monthly_emi=Decimal('35000.00'),
            interest_rate=Decimal('8.45'),
            remaining_balance=Decimal('4200000.00'),
            lender="HDFC Private Wealth",
            is_active=True
        )

    return villa


@login_required
def dashboard_view(request):
    """Main Monarch luxury wealth & expenses analysis dashboard."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    if user.username == 'shashank':
        init_user_default_assets(user)

    # 1. High-level KPI aggregates
    total_assets = Asset.objects.filter(user=user).aggregate(Sum('current_valuation'))['current_valuation__sum'] or Decimal('0.00')
    total_liabilities = Liability.objects.filter(user=user, is_active=True).aggregate(Sum('remaining_balance'))['remaining_balance__sum'] or Decimal('0.00')
    net_worth = total_assets - total_liabilities

    # 2. Ensure 12-month Financial Plan exists
    plans = MonthlyFinancialPlan.objects.filter(user=user).order_by('month_number')
    if not plans.exists():
        plans = init_user_financial_plan(user, profile)

    # 3. Monthly Calculation: Income and Expenses calculated on a MONTHLY basis (not daily!)
    today = datetime.date.today()
    default_financial_month = (today.month - 4) % 12 + 1  # e.g. Nov -> Month 8

    selected_month_param = request.GET.get('month')
    try:
        selected_month_num = int(selected_month_param)
        if not (1 <= selected_month_num <= 12):
            selected_month_num = default_financial_month
    except (TypeError, ValueError):
        selected_month_num = default_financial_month

    selected_plan = plans.filter(month_number=selected_month_num).first()
    selected_month_name = selected_plan.month_name if selected_plan else f"Month {selected_month_num}"

    # Month selector navigation items
    months_selector = [
        {
            'num': p.month_number,
            'name': p.month_name,
            'short_name': p.month_name.replace(" 2026", "").replace(" 2027", ""),
            'is_selected': (p.month_number == selected_month_num),
            'is_current': (p.month_number == default_financial_month),
        }
        for p in plans
    ]

    # Calculate MONTHLY metrics for this month
    month_tx = Transaction.objects.filter(user=user, financial_month=selected_month_num)
    month_actual_income = month_tx.filter(transaction_type='INCOME').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    month_actual_expense = month_tx.filter(transaction_type='EXPENSE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    base_plan_income = selected_plan.total_projected_income() if selected_plan else profile.monthly_salary()
    base_plan_expense = selected_plan.total_projected_expense() if selected_plan else Decimal('0.00')

    monthly_income = max(base_plan_income, month_actual_income) if base_plan_income > Decimal('0.00') else month_actual_income
    monthly_expenses = max(base_plan_expense, month_actual_expense) if base_plan_expense > Decimal('0.00') else month_actual_expense
    monthly_surplus = monthly_income - monthly_expenses

    # 4. Assets (Collection & Residence)
    assets = Asset.objects.filter(user=user)
    collection_assets = assets.exclude(asset_type='REAL_ESTATE')
    villa_asset = assets.filter(asset_type='REAL_ESTATE').first()

    # 5. Cost of ownership breakdown (Calculated for the selected month)
    if selected_plan and selected_plan.total_projected_expense() > Decimal('0.00'):
        fuel_cost = month_tx.filter(category='VEHICLE_FUEL').aggregate(Sum('amount'))['amount__sum'] or (selected_plan.vehicle_expenses * Decimal('0.40'))
        service_cost = month_tx.filter(category__in=['VEHICLE_MAINT', 'VEHICLE_CONSUMABLES']).aggregate(Sum('amount'))['amount__sum'] or (selected_plan.vehicle_expenses * Decimal('0.60'))
        villa_cost = month_tx.filter(category='VILLA_MAINT').aggregate(Sum('amount'))['amount__sum'] or selected_plan.villa_maintenance
        insurance_cost = month_tx.filter(category='VEHICLE_INSURANCE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        lifestyle_cost = month_tx.filter(category__in=['FOOD', 'HOUSEHOLD', 'TRAVEL', 'HEALTH', 'LIFESTYLE', 'OTHER_EXPENSE']).aggregate(Sum('amount'))['amount__sum'] or (
            selected_plan.food_expenses + selected_plan.household_expenses + selected_plan.travel_expenses + selected_plan.health_expenses
        )
    else:
        fuel_cost = month_tx.filter(category='VEHICLE_FUEL').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        service_cost = month_tx.filter(category__in=['VEHICLE_MAINT', 'VEHICLE_CONSUMABLES']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        villa_cost = month_tx.filter(category='VILLA_MAINT').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        insurance_cost = month_tx.filter(category='VEHICLE_INSURANCE').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        lifestyle_cost = month_tx.filter(category__in=['FOOD', 'HOUSEHOLD', 'TRAVEL', 'HEALTH', 'LIFESTYLE', 'OTHER_EXPENSE']).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    # Calculate percentage widths for ownership bars
    max_cost = max(fuel_cost, service_cost, villa_cost, insurance_cost, lifestyle_cost, Decimal('1.00'))
    ownership_mix = {
        'fuel': {'amount': fuel_cost, 'pct': min(int((fuel_cost / max_cost) * 100), 100)},
        'servicing': {'amount': service_cost, 'pct': min(int((service_cost / max_cost) * 100), 100)},
        'villa': {'amount': villa_cost, 'pct': min(int((villa_cost / max_cost) * 100), 100)},
        'insurance': {'amount': insurance_cost, 'pct': min(int((insurance_cost / max_cost) * 100), 100)},
        'lifestyle': {'amount': lifestyle_cost, 'pct': min(int((lifestyle_cost / max_cost) * 100), 100)},
    }

    # 4. Monthly Transactions with Pagination (Scoped to active calculation month by default)
    show_all_months = request.GET.get('all_months') == '1'
    if show_all_months:
        transactions_qs = Transaction.objects.filter(user=user).select_related('asset')
    else:
        transactions_qs = Transaction.objects.filter(user=user, financial_month=selected_month_num).select_related('asset')

    paginator = Paginator(transactions_qs, 6)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    # 5. Form for new transaction modal
    form = TransactionForm(initial={'financial_month': selected_month_num})
    
    # Liabilities list
    liabilities = Liability.objects.filter(user=user, is_active=True)

    # 6. Ensure 12-month Financial Plan exists
    plans = MonthlyFinancialPlan.objects.filter(user=user).order_by('month_number')
    if not plans.exists():
        plans = init_user_financial_plan(user, profile)

    # 7. Graphical Presentation Data (Monthly & Yearly)
    chart_months = [p.month_name.replace(" 2026", "").replace(" 2027", "") for p in plans]
    chart_incomes = [float(p.total_projected_income()) for p in plans]
    chart_expenses = [float(p.total_projected_expense()) for p in plans]
    chart_surplus = [float(p.projected_surplus()) for p in plans]

    # Annual Projected Totals
    annual_income = sum(chart_incomes)
    annual_expense = sum(chart_expenses)
    annual_surplus = annual_income - annual_expense
    savings_rate = round((annual_surplus / annual_income * 100), 1) if annual_income > 0 else 0
    debt_ratio = round(float((total_liabilities / total_assets) * 100), 1) if total_assets > 0 else 0

    # Inflows Breakdown
    annual_salary = sum(p.salary_income for p in plans)
    annual_stocks = sum(p.stocks_esops for p in plans)
    annual_freelance = sum(p.freelance_income for p in plans)

    # Annual Expense Breakdown Categories
    annual_liabilities = sum(float(p.liabilities_emi) for p in plans)
    annual_vehicles = sum(float(p.vehicle_expenses) for p in plans)
    annual_villa = sum(float(p.villa_maintenance) for p in plans)
    annual_living = sum(float(p.food_expenses + p.household_expenses) for p in plans)
    annual_travel = sum(float(p.travel_expenses) for p in plans)
    annual_health = sum(float(p.health_expenses) for p in plans)

    # Asset Portfolio Breakdown
    asset_labels = [a.name for a in assets]
    asset_values = [float(a.current_valuation) for a in assets]
    if not asset_labels:
        asset_labels = ['No Assets Registered']
        asset_values = [0]

    charts_payload = {
        'months': chart_months,
        'incomes': chart_incomes,
        'expenses': chart_expenses,
        'surplus': chart_surplus,
        'annual': {
            'income': annual_income,
            'expense': annual_expense,
            'surplus': annual_surplus,
            'savings_rate': savings_rate,
            'debt_ratio': debt_ratio,
        },
        'expense_mix': {
            'labels': ['Debt & EMIs', 'Vehicles & Performance', 'Residence & Property', 'Living & Household', 'Travel & Lifestyle', 'Health & Wellness'],
            'data': [annual_liabilities, annual_vehicles, annual_villa, annual_living, annual_travel, annual_health]
        },
        'portfolio': {
            'labels': asset_labels,
            'data': asset_values
        }
    }

    # Calculate villa appreciation metrics
    villa_appreciation = Decimal('0.00')
    villa_appreciation_pct = 0.0
    if villa_asset:
        villa_appreciation = villa_asset.current_valuation - villa_asset.purchase_price
        if villa_asset.purchase_price > Decimal('0.00'):
            villa_appreciation_pct = round(float((villa_appreciation / villa_asset.purchase_price) * 100), 1)

    context = {
        'profile': profile,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': net_worth,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'monthly_surplus': monthly_surplus,
        'selected_month_num': selected_month_num,
        'selected_month_name': selected_month_name,
        'months_selector': months_selector,
        'default_financial_month': default_financial_month,
        'assets': assets,
        'collection_assets': collection_assets,
        'villa': villa_asset,
        'villa_appreciation': villa_appreciation,
        'villa_appreciation_pct': villa_appreciation_pct,
        'ownership_mix': ownership_mix,
        'transactions': page_obj,
        'show_all_months': show_all_months,
        'liabilities': liabilities,
        'form': form,
        'active_tab': 'overview',
        'charts_json': json.dumps(charts_payload),
        'savings_rate': savings_rate,
        'debt_ratio': debt_ratio,
        'annual_income': Decimal(str(annual_income)),
        'annual_expense': Decimal(str(annual_expense)),
        'annual_surplus': Decimal(str(annual_surplus)),
        'annual_salary': annual_salary,
        'annual_stocks': annual_stocks,
        'annual_freelance': annual_freelance,
        'annual_liabilities': annual_liabilities,
        'annual_vehicles': annual_vehicles,
        'annual_villa': annual_villa,
        'annual_living': annual_living,
        'annual_travel': annual_travel,
        'annual_health': annual_health,
    }
    return render(request, 'dashboard.html', context)


@login_required
def property_view(request):
    """
    Dedicated view allowing the user to view, add, or edit their luxury property / residence.
    When accessed via GET without edit=1, renders the interactive split showcase (property.html).
    When edit=1 or POST, renders/processes the edit form (edit_property.html).
    """
    user = request.user
    if user.username == 'shashank':
        property_asset = init_user_default_assets(user)
    else:
        property_asset = Asset.objects.filter(user=user, asset_type='REAL_ESTATE').first()
    if not property_asset:
        property_asset = Asset.objects.filter(user=user, asset_type='REAL_ESTATE').first()
    is_edit_requested = request.GET.get('edit') == '1' or request.method == 'POST'

    if request.method == 'POST':
        if property_asset:
            form = PropertyForm(request.POST, request.FILES, instance=property_asset)
        else:
            form = PropertyForm(request.POST, request.FILES)

        if form.is_valid():
            prop = form.save(commit=False)
            prop.user = user
            prop.asset_type = 'REAL_ESTATE'
            if not prop.tag:
                prop.tag = 'REAL ESTATE'
            prop.save()
            messages.success(request, f"Property '{prop.name}' saved successfully.")
            return redirect('property')
        else:
            messages.error(request, "Error saving property. Please check your inputs.")
            return render(request, 'edit_property.html', {'form': form, 'asset': property_asset, 'is_new': property_asset is None, 'active_tab': 'property'})

    # Handle GET request
    if property_asset and not is_edit_requested:
        # Calculate appreciation & portfolio contribution
        appreciation = property_asset.current_valuation - property_asset.purchase_price
        appreciation_pct = 0.0
        if property_asset.purchase_price > Decimal('0.00'):
            appreciation_pct = round(float((appreciation / property_asset.purchase_price) * 100), 1)

        total_assets = Asset.objects.filter(user=user).aggregate(Sum('current_valuation'))['current_valuation__sum'] or Decimal('1.00')
        asset_share = 0.0
        if total_assets > Decimal('0.00'):
            asset_share = round(float((property_asset.current_valuation / total_assets) * 100), 1)

        context = {
            'asset': property_asset,
            'appreciation': appreciation,
            'appreciation_pct': appreciation_pct,
            'asset_share': asset_share,
            'active_tab': 'property',
        }
        return render(request, 'property.html', context)

    # Edit existing or add new residence
    if property_asset:
        form = PropertyForm(instance=property_asset)
    else:
        form = PropertyForm(initial={
            'name': 'Private Luxury Villa Estate',
            'purchase_price': Decimal('8500000.00'),
            'current_valuation': Decimal('10000000.00'),
            'specification': '4,800 sq ft · Private estate · 4 beds · Landscaped grounds',
        })

    context = {
        'form': form,
        'asset': property_asset,
        'is_new': property_asset is None,
        'active_tab': 'property',
    }
    return render(request, 'edit_property.html', context)


@login_required
def add_asset_view(request):
    """Allows adding any new high-value asset (Motorcycle, Car, Equity, Luxury Watches, Other)."""
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES)
        if form.is_valid():
            asset = form.save(commit=False)
            asset.user = request.user
            asset.save()
            messages.success(request, f"Asset '{asset.name}' added successfully to your portfolio.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error adding asset. Please check the form fields.")
    else:
        form = AssetForm(initial={
            'asset_type': 'MOTORCYCLE',
            'tag': 'MOTORCYCLE 03',
            'purchase_price': Decimal('0.00'),
            'current_valuation': Decimal('0.00')
        })

    return render(request, 'add_asset.html', {'form': form, 'active_tab': 'overview'})


@login_required
def edit_asset_view(request, pk):
    """Modifies high-value property / assets (Villa, Hayabusa, BMW S1000RR, BMW M3)."""
    asset = get_object_or_404(Asset, pk=pk, user=request.user)

    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES, instance=asset)
        if form.is_valid():
            form.save()
            messages.success(request, f"Asset '{asset.name}' updated successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error updating asset. Please check inputs.")
    else:
        form = AssetForm(instance=asset)

    context = {
        'form': form,
        'asset': asset,
        'active_tab': 'overview',
    }
    return render(request, 'edit_asset.html', context)


@login_required
def delete_asset_view(request, pk):
    """Deletes an asset record."""
    asset = get_object_or_404(Asset, pk=pk, user=request.user)
    name = asset.name
    asset.delete()
    messages.success(request, f"Asset '{name}' removed from your portfolio.")
    return redirect('dashboard')


@login_required
def transactions_view(request):
    """Full-ledger transaction page with search, category filtering, and pagination."""
    user = request.user
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '')
    type_filter = request.GET.get('type', '')

    transactions_qs = Transaction.objects.filter(user=user).select_related('asset')

    if query:
        transactions_qs = transactions_qs.filter(
            Q(title__icontains=query) | Q(notes__icontains=query) | Q(payment_method__icontains=query)
        )
    if category_filter:
        transactions_qs = transactions_qs.filter(category=category_filter)
    if type_filter:
        transactions_qs = transactions_qs.filter(transaction_type=type_filter)

    paginator = Paginator(transactions_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    form = TransactionForm()

    context = {
        'transactions': page_obj,
        'query': query,
        'category_filter': category_filter,
        'type_filter': type_filter,
        'categories': Transaction.CATEGORY_CHOICES,
        'form': form,
        'active_tab': 'transactions',
    }
    return render(request, 'transactions.html', context)


@login_required
def add_transaction_view(request):
    """Creates a new transaction via modal (supports AJAX and standard POST)."""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('ajax') == 'true'

        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.save()

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Transaction recorded successfully.',
                    'transaction': {
                        'id': transaction.id,
                        'title': transaction.title,
                        'category': transaction.get_category_display(),
                        'asset': transaction.asset.name if transaction.asset else 'General',
                        'date': transaction.date.strftime('%d %b'),
                        'type': transaction.transaction_type,
                        'amount': f"{transaction.amount:,.2f}"
                    }
                })

            messages.success(request, f"Transaction '{transaction.title}' recorded.")
            return redirect('dashboard')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
            messages.error(request, "Please correct the errors in the transaction form.")
            return redirect('dashboard')

    return redirect('dashboard')


@login_required
def edit_transaction_view(request, pk):
    """Modifies an existing transaction record."""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, f"Transaction '{transaction.title}' updated successfully.")
            next_url = request.GET.get('next', 'dashboard')
            return redirect(next_url)
        else:
            messages.error(request, "Error updating transaction. Please check your inputs.")
    else:
        form = TransactionForm(instance=transaction)

    context = {
        'form': form,
        'transaction': transaction,
        'active_tab': 'transactions',
    }
    return render(request, 'edit_transaction.html', context)


@login_required
def delete_transaction_view(request, pk):
    """Deletes an existing transaction."""
    transaction = get_object_or_404(Transaction, pk=pk, user=request.user)
    title = transaction.title
    transaction.delete()
    messages.success(request, f"Transaction '{title}' deleted successfully.")
    
    next_url = request.GET.get('next', 'dashboard')
    return redirect(next_url)


@login_required
def edit_financial_plan_view(request, pk):
    """Modifies a specific month's projections in the 1 Financial Year model."""
    plan = get_object_or_404(MonthlyFinancialPlan, pk=pk, user=request.user)

    if request.method == 'POST':
        form = MonthlyFinancialPlanForm(request.POST, instance=plan)
        if form.is_valid():
            updated_plan = form.save(commit=False)
            updated_plan.is_customized = True
            updated_plan.save()
            messages.success(request, f"Financial plan for '{plan.month_name}' updated successfully.")
            return redirect('financial_plan')
        else:
            messages.error(request, "Error updating monthly financial plan.")
    else:
        form = MonthlyFinancialPlanForm(instance=plan)

    context = {
        'form': form,
        'plan': plan,
        'active_tab': 'financial_plan',
    }
    return render(request, 'edit_financial_plan.html', context)


@login_required
def edit_liability_view(request, pk):
    """Modifies a liability or loan record."""
    liability = get_object_or_404(Liability, pk=pk, user=request.user)

    if request.method == 'POST':
        form = LiabilityForm(request.POST, instance=liability)
        if form.is_valid():
            form.save()
            messages.success(request, f"Liability '{liability.title}' updated successfully.")
            return redirect('dashboard')
        else:
            messages.error(request, "Error updating liability.")
    else:
        form = LiabilityForm(instance=liability)

    context = {
        'form': form,
        'liability': liability,
        'active_tab': 'overview',
    }
    return render(request, 'edit_liability.html', context)


@login_required
def profile_view(request):
    """Manages the persona, bio, profile picture upload, and annual CTC."""
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        old_ctc = profile.annual_ctc
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            updated_profile = form.save()
            if updated_profile.annual_ctc != old_ctc:
                new_monthly_salary = updated_profile.monthly_salary()
                MonthlyFinancialPlan.objects.filter(
                    user=request.user, 
                    is_customized=False
                ).update(salary_income=new_monthly_salary)

            messages.success(request, "Your wealth persona & profile have been updated successfully.")
            return redirect('profile')
        else:
            messages.error(request, "Error updating profile. Please check file format and inputs.")
    else:
        form = UserProfileForm(instance=profile)

    context = {
        'profile': profile,
        'form': form,
        'active_tab': 'profile',
    }
    return render(request, 'profile.html', context)


@login_required
def financial_plan_view(request):
    """1 Financial Year (12 months) overview, projections table and interactive charts."""
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)
    plans = MonthlyFinancialPlan.objects.filter(user=user).order_by('month_number')

    if not plans.exists():
        plans = init_user_financial_plan(user, profile)

    # Calculate year totals
    year_salary = sum(p.salary_income for p in plans)
    year_stocks = sum(p.stocks_esops for p in plans)
    year_freelance = sum(p.freelance_income for p in plans)
    year_total_income = sum(p.total_projected_income() for p in plans)
    year_total_expense = sum(p.total_projected_expense() for p in plans)
    year_surplus = year_total_income - year_total_expense
    savings_rate = round(float((year_surplus / year_total_income) * 100), 1) if year_total_income > 0 else 0

    chart_months = [p.month_name.replace(" 2026", "").replace(" 2027", "") for p in plans]
    chart_incomes = [float(p.total_projected_income()) for p in plans]
    chart_expenses = [float(p.total_projected_expense()) for p in plans]
    chart_surplus = [float(p.projected_surplus()) for p in plans]

    charts_payload = {
        'months': chart_months,
        'incomes': chart_incomes,
        'expenses': chart_expenses,
        'surplus': chart_surplus,
    }

    context = {
        'plans': plans,
        'year_salary': year_salary,
        'year_stocks': year_stocks,
        'year_freelance': year_freelance,
        'year_total_income': year_total_income,
        'year_total_expense': year_total_expense,
        'year_surplus': year_surplus,
        'savings_rate': savings_rate,
        'charts_json': json.dumps(charts_payload),
        'active_tab': 'financial_plan',
    }
    return render(request, 'financial_plan.html', context)


# ---------------------- AUTHENTICATION & ADMIN USER MANAGEMENT ---------------------- #

def admin_required(view_func):
    """Decorator ensuring the requesting user is authenticated and is staff or superuser."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Administrator privileges are required to access user management.")
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@admin_required
def manage_users_view(request):
    """
    Luxury Admin Console: View, search, filter, and manage all registered platform users.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    role_filter = request.GET.get('role', '').strip()

    users_qs = User.objects.all().select_related('profile').prefetch_related('assets').order_by('-date_joined')

    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(profile__occupation__icontains=query)
        )

    if status_filter == 'active':
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == 'inactive':
        users_qs = users_qs.filter(is_active=False)

    if role_filter == 'admin':
        users_qs = users_qs.filter(Q(is_staff=True) | Q(is_superuser=True))
    elif role_filter == 'member':
        users_qs = users_qs.filter(is_staff=False, is_superuser=False)

    # High-level statistics
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    admin_count = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count()
    total_aum = Asset.objects.aggregate(Sum('current_valuation'))['current_valuation__sum'] or Decimal('0.00')

    paginator = Paginator(users_qs, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    create_form = AdminUserCreationForm()

    context = {
        'users': page_obj,
        'total_users': total_users,
        'active_users': active_users,
        'admin_count': admin_count,
        'total_aum': total_aum,
        'query': query,
        'status_filter': status_filter,
        'role_filter': role_filter,
        'create_form': create_form,
        'active_tab': 'users',
    }
    return render(request, 'admin/manage_users.html', context)


@admin_required
def create_user_view(request):
    """Admin endpoint to create a new user account with immediate portfolio setup."""
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()

            job_role = form.cleaned_data.get('job_role', 'Private Wealth Member')
            annual_salary = form.cleaned_data.get('annual_salary', Decimal('0.00'))

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.occupation = job_role
            profile.annual_ctc = annual_salary
            profile.bio = f"{job_role} | Account configured by Administrator"
            profile.save()

            init_user_financial_plan(user, profile)
            messages.success(request, f"User '{user.username}' successfully created with financial portfolio initialized.")
        else:
            errors_str = " ".join([f"{f}: {err[0]}" for f, err in form.errors.items()])
            messages.error(request, f"Error creating user: {errors_str}")

    return redirect('manage_users')


@admin_required
def edit_user_view(request, user_id):
    """Admin endpoint to modify an existing user's credentials, role, status, and compensation."""
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        form = AdminUserEditForm(request.POST, instance=target_user, profile=profile)
        if form.is_valid():
            updated_user = form.save()

            job_role = form.cleaned_data.get('job_role')
            annual_salary = form.cleaned_data.get('annual_salary')

            profile_changed = False
            if job_role is not None and job_role != profile.occupation:
                profile.occupation = job_role
                profile_changed = True

            if annual_salary is not None and annual_salary != profile.annual_ctc:
                profile.annual_ctc = annual_salary
                profile_changed = True
                new_salary = profile.monthly_salary()
                MonthlyFinancialPlan.objects.filter(user=target_user, is_customized=False).update(salary_income=new_salary)

            if profile_changed:
                profile.save()

            messages.success(request, f"User '{updated_user.username}' updated successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, "Error updating user. Please check form fields.")
    else:
        form = AdminUserEditForm(instance=target_user, profile=profile)

    context = {
        'form': form,
        'target_user': target_user,
        'profile': profile,
        'active_tab': 'users',
    }
    return render(request, 'admin/edit_user.html', context)


@admin_required
def toggle_user_status_view(request, user_id):
    """Quick toggle to activate or suspend a member's account."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user.pk == request.user.pk:
            messages.error(request, "Security violation: You cannot deactivate your own administrative account.")
            return redirect('manage_users')

        target_user.is_active = not target_user.is_active
        target_user.save()
        status_word = "activated" if target_user.is_active else "deactivated"
        messages.success(request, f"User '{target_user.username}' has been {status_word}.")

    return redirect('manage_users')


@admin_required
def delete_user_view(request, user_id):
    """Admin endpoint to permanently delete a user and their financial records."""
    if request.method == 'POST':
        target_user = get_object_or_404(User, pk=user_id)
        if target_user.pk == request.user.pk:
            messages.error(request, "Security violation: You cannot delete your own administrative account.")
            return redirect('manage_users')

        username = target_user.username
        target_user.delete()
        messages.success(request, f"User '{username}' and associated financial records deleted.")

    return redirect('manage_users')


@admin_required
def reset_user_password_view(request, user_id):
    """Admin view to reset password for any user account."""
    target_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = AdminPasswordResetForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            target_user.set_password(new_password)
            target_user.save()
            messages.success(request, f"Password for user '{target_user.username}' was updated successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, "Error resetting password. Passwords must match.")
    else:
        form = AdminPasswordResetForm()

    context = {
        'form': form,
        'target_user': target_user,
        'active_tab': 'users',
    }
    return render(request, 'admin/reset_password.html', context)


@admin_required
def user_detail_view(request, user_id):
    """Admin view to inspect a specific user's comprehensive wealth portfolio."""
    target_user = get_object_or_404(User, pk=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    user_assets = Asset.objects.filter(user=target_user)
    user_liabilities = Liability.objects.filter(user=target_user)
    user_transactions = Transaction.objects.filter(user=target_user)[:15]
    user_plans = MonthlyFinancialPlan.objects.filter(user=target_user).order_by('month_number')

    total_assets = user_assets.aggregate(Sum('current_valuation'))['current_valuation__sum'] or Decimal('0.00')
    total_liabilities = user_liabilities.filter(is_active=True).aggregate(Sum('remaining_balance'))['remaining_balance__sum'] or Decimal('0.00')
    net_worth = total_assets - total_liabilities

    context = {
        'target_user': target_user,
        'profile': profile,
        'assets': user_assets,
        'liabilities': user_liabilities,
        'transactions': user_transactions,
        'plans': user_plans,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'net_worth': net_worth,
        'active_tab': 'users',
    }
    return render(request, 'admin/user_detail.html', context)


def login_view(request):
    """
    Unified User & Admin Authentication Login View.
    Always redirects directly to the Overview menu upon login.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.username == 'shashank':
                init_user_default_assets(user)
            messages.success(request, f"Welcome back, {user.first_name or user.username}.")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()

    return render(request, 'auth/login.html', {'form': form})


def register_view(request):
    """New user sign-up view with immediate profile, financial plan, and luxury asset initialization."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Create user profile with their provided Job Role and Annual Salary
            job_role = form.cleaned_data.get('job_role', 'Private Wealth Member')
            annual_salary = form.cleaned_data.get('annual_salary', Decimal('0.00'))
            
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.occupation = job_role
            profile.annual_ctc = annual_salary
            profile.bio = f"{job_role} | Private Wealth Portfolio Tracker"
            profile.save()

            init_user_financial_plan(user, profile)
            login(request, user)
            messages.success(request, f"Account created successfully. Welcome to MONARCH, {user.first_name or user.username}.")
            return redirect('dashboard')
        else:
            messages.error(request, "Please correct the registration errors below.")
    else:
        form = UserRegisterForm()

    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    """User logout."""
    logout(request)
    messages.info(request, "You have been logged out of your session.")
    return redirect('login')
