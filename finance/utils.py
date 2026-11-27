from decimal import Decimal, ROUND_HALF_UP
import random


MONTH_NAMES_FY_2026_2027 = [
    "April 2026", "May 2026", "June 2026", "July 2026",
    "August 2026", "September 2026", "October 2026", "November 2026",
    "December 2026", "January 2027", "February 2027", "March 2027",
]


def _round_hundreds(value: Decimal) -> Decimal:
    """Rounds a Decimal amount to the nearest 100 INR for realistic financial figures."""
    return (value / Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * Decimal('100')


def generate_random_month_figures(
    base_salary: Decimal,
    month_number: int,
    fixed_emi: Decimal = Decimal('0.00'),
    randomize_income: bool = True,
    include_luxury_assets: bool = True,
) -> dict:
    """
    Generates realistic monthly ups & downs for all users while keeping base salary and home expenses constant,
    and strictly guaranteeing that total income is greater than total expenses.

    - Constant income: salary_income
    - Randomized income: stocks_esops, freelance_income, gifts_bonus
    - Constant expenses: liabilities_emi, household_expenses, villa_maintenance (Residence Care)
    - Randomized expenses: food_expenses, travel_expenses, vehicle_expenses, health_expenses
    """
    salary_base = max(Decimal(base_salary), Decimal('10000.00')).quantize(Decimal('0.01'))
    salary_income = salary_base  # Always keep monthly salary constant

    salary_scale = max(salary_base / Decimal('333333.33'), Decimal('0.05'))

    if randomize_income:
        # Ups and downs in ESOPs/Stocks, Freelancing, and Bonus
        stocks_esops = (
            _round_hundreds(Decimal(random.randint(25000, 95000)) * salary_scale)
            if random.random() < 0.80
            else Decimal('0.00')
        )
        freelance_income = _round_hundreds(Decimal(random.randint(10000, 90000)) * salary_scale)
        bonus_chance = 0.65 if month_number in (7, 8, 12) else 0.35
        gifts_bonus = (
            _round_hundreds(Decimal(random.randint(20000, 85000)) * salary_scale)
            if random.random() < bonus_chance
            else Decimal('0.00')
        )
    else:
        stocks_esops = Decimal('0.00')
        freelance_income = Decimal('0.00')
        gifts_bonus = Decimal('0.00')

    total_income = salary_income + stocks_esops + freelance_income + gifts_bonus

    # Constant home & liability commitments across all 12 months
    liabilities_emi = max(Decimal(fixed_emi), Decimal('0.00')).quantize(Decimal('0.01'))
    household_expenses = _round_hundreds(Decimal('20000.00') * salary_scale)
    villa_maintenance = _round_hundreds(Decimal('18500.00') * salary_scale)
    if household_expenses < Decimal('1000.00'):
        household_expenses = Decimal('1000.00')
    if villa_maintenance < Decimal('500.00'):
        villa_maintenance = Decimal('500.00')

    fixed_expenses = liabilities_emi + household_expenses + villa_maintenance

    # Randomized variable expenses (travel, food, vehicle, health) scaled to salary
    variable_expenses = {
        'food_expenses': _round_hundreds(Decimal(random.randint(16000, 38000)) * salary_scale),
        'travel_expenses': _round_hundreds(Decimal(random.randint(6000, 55000)) * salary_scale),
        'vehicle_expenses': _round_hundreds(Decimal(random.randint(14000, 62000)) * salary_scale),
        'health_expenses': _round_hundreds(Decimal(random.randint(4000, 28000)) * salary_scale),
    }

    for key in variable_expenses:
        if variable_expenses[key] < Decimal('500.00'):
            variable_expenses[key] = Decimal('500.00')

    variable_total = sum(variable_expenses.values())
    total_expense = fixed_expenses + variable_total

    # IMP: Strictly enforce total_income > total_expense (cap expenses at <= 78% of total_income)
    max_allowed_total = (total_income * Decimal('0.78')).quantize(Decimal('0.01'))

    if total_expense > max_allowed_total:
        available_for_variable = max(max_allowed_total - fixed_expenses, Decimal('0.00'))
        if variable_total > Decimal('0.00') and available_for_variable > Decimal('0.00'):
            ratio = available_for_variable / variable_total
            for key in variable_expenses:
                variable_expenses[key] = (variable_expenses[key] * ratio).quantize(Decimal('1.'), rounding=ROUND_HALF_UP)
        else:
            for key in variable_expenses:
                variable_expenses[key] = Decimal('0.00')

        total_expense = fixed_expenses + sum(variable_expenses.values())

    # Final safety guard: if constant EMI + home expenses alone meet/exceed income, boost freelance_income
    if total_income <= total_expense:
        shortfall = total_expense - total_income
        extra_buffer = max((total_expense * Decimal('0.25')).quantize(Decimal('1.')), Decimal('5000.00'))
        freelance_income += shortfall + extra_buffer
        total_income = salary_income + stocks_esops + freelance_income + gifts_bonus

    return {
        'salary_income': salary_income,
        'stocks_esops': stocks_esops,
        'freelance_income': freelance_income,
        'gifts_bonus': gifts_bonus,
        'liabilities_emi': liabilities_emi,
        'household_expenses': household_expenses,
        'villa_maintenance': villa_maintenance,
        **variable_expenses,
    }
