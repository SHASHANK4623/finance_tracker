from django.test import TestCase, Client
from django.core.management import call_command
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
import json

from finance.models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan
from finance.utils import generate_random_month_figures


class MonarchWealthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='shashank',
            email='shashank@jpmc.com',
            password='Password123!',
            first_name='Shashank'
        )
        self.user1.profile.occupation = 'Software Engineer @ JPMC'
        self.user1.profile.annual_ctc = Decimal('4000000.00')
        self.user1.profile.save()

        self.user2 = User.objects.create_user(
            username='alex_investor',
            email='alex@example.com',
            password='Password123!',
            first_name='Alex'
        )
        self.user2.profile.occupation = 'Investor'
        self.user2.profile.annual_ctc = Decimal('6000000.00')
        self.user2.profile.save()

        # Give user1 an initial property and a vehicle
        self.prop1 = Asset.objects.create(
            user=self.user1,
            name='Private Villa Estate',
            asset_type='REAL_ESTATE',
            tag='REAL ESTATE',
            purchase_price=Decimal('8500000.00'),
            current_valuation=Decimal('10000000.00'),
            specification='4,800 sq ft · Private estate'
        )
        self.bike1 = Asset.objects.create(
            user=self.user1,
            name='Suzuki Hayabusa',
            asset_type='MOTORCYCLE',
            tag='MOTORCYCLE 01',
            purchase_price=Decimal('2100000.00'),
            current_valuation=Decimal('2300000.00')
        )

    def test_login_page_removes_demo_credentials(self):
        """Test that default demo account credentials are removed from login form."""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "@2468Shashank")
        self.assertNotContains(response, "Default Demo Account")

    def test_user_can_edit_property(self):
        """Test that user1 can edit their property."""
        self.client.login(username='shashank', password='Password123!')
        
        # Check GET property page
        response = self.client.get(reverse('property'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Villa Estate')

        # POST update property
        post_data = {
            'name': 'Updated Luxury Hilltop Villa',
            'purchase_price': '9000000.00',
            'current_valuation': '12500000.00',
            'specification': '5,500 sq ft · 5 Suites · Helipad',
            'pinterest_url': 'https://pin.it/example',
            'image_url': 'images/villa.jpg'
        }
        post_response = self.client.post(reverse('property'), post_data)
        self.assertRedirects(post_response, reverse('dashboard'))

        # Verify in DB
        self.prop1.refresh_from_db()
        self.assertEqual(self.prop1.name, 'Updated Luxury Hilltop Villa')
        self.assertEqual(self.prop1.current_valuation, Decimal('12500000.00'))
        self.assertEqual(self.prop1.specification, '5,500 sq ft · 5 Suites · Helipad')

    def test_different_user_can_add_property(self):
        """Test that user2 (who has no property) can register/give their property."""
        self.client.login(username='alex_investor', password='Password123!')
        
        # User 2 has no property initially
        self.assertFalse(Asset.objects.filter(user=self.user2, asset_type='REAL_ESTATE').exists())

        post_data = {
            'name': 'Downtown Seaside Penthouse',
            'purchase_price': '6000000.00',
            'current_valuation': '7500000.00',
            'specification': '3,200 sq ft · Panoramic Sea View',
            'pinterest_url': '',
            'image_url': ''
        }
        response = self.client.post(reverse('property'), post_data)
        self.assertRedirects(response, reverse('dashboard'))

        new_prop = Asset.objects.filter(user=self.user2, asset_type='REAL_ESTATE').first()
        self.assertIsNotNone(new_prop)
        self.assertEqual(new_prop.name, 'Downtown Seaside Penthouse')
        self.assertEqual(new_prop.current_valuation, Decimal('7500000.00'))

    def test_different_user_profile_bio_and_isolation(self):
        """Test that different users can give their bio and profile independently."""
        self.client.login(username='alex_investor', password='Password123!')
        
        post_data = {
            'first_name': 'Alexander',
            'last_name': 'Wright',
            'email': 'alex@example.com',
            'occupation': 'Venture Partner & Angel Investor',
            'annual_ctc': '6000000.00',
            'phone': '+91 99999 88888',
            'location': 'Bengaluru',
            'bio': 'Tech Investor | Multi-asset portfolio builder'
        }
        response = self.client.post(reverse('profile'), post_data)
        self.assertRedirects(response, reverse('profile'))

        profile2 = UserProfile.objects.get(user=self.user2)
        self.assertEqual(profile2.occupation, 'Venture Partner & Angel Investor')
        self.assertEqual(profile2.bio, 'Tech Investor | Multi-asset portfolio builder')
        self.assertEqual(profile2.annual_ctc, Decimal('6000000.00'))
        self.user2.refresh_from_db()
        self.assertEqual(self.user2.first_name, 'Alexander')

        # Check user1 profile is untouched
        profile1 = UserProfile.objects.get(user=self.user1)
        self.assertNotEqual(profile1.bio, profile2.bio)

    def test_user_can_log_income_and_expense_transactions(self):
        """Test logging income and expenses for a user."""
        self.client.login(username='alex_investor', password='Password123!')

        # Log Income
        resp_income = self.client.post(reverse('add_transaction'), {
            'title': 'Consulting Retainer Income',
            'transaction_type': 'INCOME',
            'category': 'FREELANCE',
            'amount': '150000.00',
            'date': '2026-11-20',
            'financial_month': 8,
            'payment_method': 'Bank Transfer'
        })
        self.assertRedirects(resp_income, reverse('dashboard'))

        # Log Expense
        resp_expense = self.client.post(reverse('add_transaction'), {
            'title': 'High Octane Fuel',
            'transaction_type': 'EXPENSE',
            'category': 'VEHICLE_FUEL',
            'amount': '5500.00',
            'date': '2026-11-21',
            'financial_month': 8,
            'payment_method': 'Credit Card'
        })
        self.assertRedirects(resp_expense, reverse('dashboard'))

        t_count = Transaction.objects.filter(user=self.user2).count()
        self.assertEqual(t_count, 2)

    def test_graphical_presentation_data_rendered_on_dashboard(self):
        """Test dashboard provides monthly and yearly chart JSON data."""
        self.client.login(username='shashank', password='Password123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

        # Context contains charts_json
        self.assertIn('charts_json', response.context)
        charts_data = json.loads(response.context['charts_json'])

        # Monthly series
        self.assertIn('months', charts_data)
        self.assertEqual(len(charts_data['months']), 12)
        self.assertIn('incomes', charts_data)
        self.assertIn('expenses', charts_data)
        self.assertIn('surplus', charts_data)

        # Yearly series
        self.assertIn('annual', charts_data)
        self.assertIn('savings_rate', charts_data['annual'])
        self.assertIn('expense_mix', charts_data)
        self.assertIn('portfolio', charts_data)

        # Rendered in HTML
        self.assertContains(response, 'monthlyChart')
        self.assertContains(response, 'yearlyFlowChart')
        self.assertContains(response, 'portfolioChart')

    def test_graphical_presentation_data_on_financial_plan(self):
        """Test 1-Year Financial Plan renders visual trajectory chart."""
        self.client.login(username='shashank', password='Password123!')
        response = self.client.get(reverse('financial_plan'))
        self.assertEqual(response.status_code, 200)

        self.assertIn('charts_json', response.context)
        self.assertContains(response, 'planTrajectoryChart')

    def test_add_and_delete_collection_asset(self):
        """Test adding a vehicle asset and deleting it."""
        self.client.login(username='shashank', password='Password123!')

        # Add asset
        resp_add = self.client.post(reverse('add_asset'), {
            'name': 'Ducati Panigale V4',
            'asset_type': 'MOTORCYCLE',
            'tag': 'MOTORCYCLE 03',
            'purchase_price': '2800000.00',
            'current_valuation': '2900000.00',
            'specification': '1103cc 215 bhp'
        })
        self.assertRedirects(resp_add, reverse('dashboard'))

        ducati = Asset.objects.filter(user=self.user1, name='Ducati Panigale V4').first()
        self.assertIsNotNone(ducati)

        # Delete asset
        resp_del = self.client.post(reverse('delete_asset', kwargs={'pk': ducati.id}))
        self.assertRedirects(resp_del, reverse('dashboard'))
        self.assertFalse(Asset.objects.filter(user=self.user1, name='Ducati Panigale V4').exists())

    def test_registration_sets_job_role_and_exact_salary(self):
        """Test registration asks for job role & salary and avoids hardcoding 50L."""
        resp = self.client.post(reverse('register'), {
            'username': 'rachel_pm',
            'first_name': 'Rachel',
            'last_name': 'Green',
            'email': 'rachel@example.com',
            'job_role': 'Staff Product Manager',
            'annual_salary': '1800000.00',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertRedirects(resp, reverse('dashboard'))

        rachel = User.objects.get(username='rachel_pm')
        self.assertEqual(rachel.profile.occupation, 'Staff Product Manager')
        self.assertEqual(rachel.profile.annual_ctc, Decimal('1800000.00'))
        self.assertEqual(rachel.profile.monthly_salary(), Decimal('150000.00'))

        # Check annual salary matches entered 18 Lakhs, with ups & downs across the year and positive surplus
        dash_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_resp.context['annual_salary'], Decimal('1800000.00'))
        self.assertGreaterEqual(dash_resp.context['monthly_income'], Decimal('150000.00'))
        self.assertGreater(dash_resp.context['annual_income'], dash_resp.context['annual_expense'])

        # Check all 12 months on financial_plan have ups & downs for the new user and are editable monthly
        fp_resp = self.client.get(reverse('financial_plan'))
        self.assertEqual(fp_resp.status_code, 200)
        self.assertContains(fp_resp, 'Other Income')
        rachel_plans = list(MonthlyFinancialPlan.objects.filter(user=rachel).order_by('month_number'))
        self.assertEqual(len(rachel_plans), 12)
        self.assertGreater(len({p.total_projected_income() for p in rachel_plans}), 1)
        self.assertGreater(len({p.total_projected_expense() for p in rachel_plans}), 1)

        # Verify monthly-wise edit works and marks month customized
        m1 = rachel_plans[0]
        edit_resp = self.client.post(reverse('edit_financial_plan', kwargs={'pk': m1.pk}), {
            'salary_income': '150000.00',
            'stocks_esops': '25000.00',
            'freelance_income': '30000.00',
            'gifts_bonus': '10000.00',
            'liabilities_emi': '12000.00',
            'food_expenses': '15000.00',
            'household_expenses': '10000.00',
            'vehicle_expenses': '8000.00',
            'travel_expenses': '5000.00',
            'health_expenses': '4000.00',
            'villa_maintenance': '6000.00',
        })
        self.assertRedirects(edit_resp, reverse('financial_plan'))
        m1.refresh_from_db()
        self.assertTrue(m1.is_customized)
        self.assertEqual(m1.other_income(), Decimal('40000.00'))

        # Test salary below minimum 10k is rejected by form validation
        self.client.logout()
        resp_low = self.client.post(reverse('register'), {
            'username': 'low_salary',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'low@example.com',
            'job_role': 'Intern',
            'annual_salary': '5000.00',  # below 10k
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        self.assertEqual(resp_low.status_code, 200)
        self.assertFalse(User.objects.filter(username='low_salary').exists())

    def test_monthly_calculation_and_month_selector(self):
        """Test that income and expenses are calculated based on month not daily."""
        self.client.login(username='shashank', password='Password123!')
        
        # Test default month (Nov = Month 8)
        resp_nov = self.client.get(reverse('dashboard') + '?month=8')
        self.assertEqual(resp_nov.status_code, 200)
        self.assertEqual(resp_nov.context['selected_month_num'], 8)
        self.assertIn('November', resp_nov.context['selected_month_name'])

        # Monthly income is calculated for that month, not daily sum
        monthly_income_nov = resp_nov.context['monthly_income']
        self.assertGreater(monthly_income_nov, Decimal('300000.00'))

        # Test selecting a different month (e.g. Month 5 / August)
        resp_aug = self.client.get(reverse('dashboard') + '?month=5')
        self.assertEqual(resp_aug.status_code, 200)
        self.assertEqual(resp_aug.context['selected_month_num'], 5)
        self.assertIn('August', resp_aug.context['selected_month_name'])

    def test_randomized_income_and_expenses_always_positive_surplus(self):
        """Randomly generated income & expenses vary across months and always keep income > expenses."""
        # Normal and high-EMI stress cases
        for base_salary, fixed_emi in [
            (Decimal('333333.33'), Decimal('53000.00')),
            (Decimal('10000.00'), Decimal('0.00')),
            (Decimal('50000.00'), Decimal('80000.00')),
        ]:
            for month in range(1, 13):
                fig = generate_random_month_figures(
                    base_salary=base_salary,
                    month_number=month,
                    fixed_emi=fixed_emi,
                    randomize_income=True,
                    include_luxury_assets=True,
                )
                total_inc = fig['salary_income'] + fig['stocks_esops'] + fig['freelance_income'] + fig['gifts_bonus']
                total_exp = (
                    fig['liabilities_emi']
                    + fig['food_expenses']
                    + fig['household_expenses']
                    + fig['vehicle_expenses']
                    + fig['travel_expenses']
                    + fig['health_expenses']
                    + fig['villa_maintenance']
                )
                self.assertGreater(total_inc, total_exp)

    def test_randomize_financial_plan_endpoint_and_seed_data(self):
        """Test POST /financial-plan/randomize/ and seed_data preserving customized months."""
        self.client.login(username='shashank', password='Password123!')
        resp = self.client.post(reverse('randomize_financial_plan'))
        self.assertRedirects(resp, reverse('financial_plan'))

        plans = list(MonthlyFinancialPlan.objects.filter(user=self.user1).order_by('month_number'))
        self.assertEqual(len(plans), 12)
        # Salary and home/EMI expenses stay constant across all 12 months
        self.assertEqual(len({p.salary_income for p in plans}), 1)
        self.assertEqual(len({p.household_expenses for p in plans}), 1)
        self.assertEqual(len({p.villa_maintenance for p in plans}), 1)
        self.assertEqual(len({p.liabilities_emi for p in plans}), 1)

        # Variable income & expenses (travel, food, vehicle, health) have ups and downs
        incomes = {p.total_projected_income() for p in plans}
        expenses = {p.total_projected_expense() for p in plans}
        self.assertGreater(len(incomes), 1)
        self.assertGreater(len(expenses), 1)
        self.assertGreater(len({p.travel_expenses for p in plans}), 1)
        self.assertGreater(len({p.food_expenses for p in plans}), 1)
        self.assertGreater(len({p.vehicle_expenses for p in plans}), 1)
        self.assertGreater(len({p.health_expenses for p in plans}), 1)
        for p in plans:
            self.assertGreater(p.total_projected_income(), p.total_projected_expense())

        # Verify seed_data preserves customized months
        custom_plan = plans[0]
        custom_plan.salary_income = Decimal('777777.00')
        custom_plan.is_customized = True
        custom_plan.save()

        call_command('seed_data')
        custom_plan.refresh_from_db()
        self.assertEqual(custom_plan.salary_income, Decimal('777777.00'))
        self.assertTrue(custom_plan.is_customized)

    def test_dashboard_property_grid_and_original_aspect_stage(self):
        """Test all real estate properties render in a grid and showcase supports original aspect ratios."""
        Asset.objects.create(
            user=self.user1,
            name='Goa Beachfront Penthouse',
            asset_type='REAL_ESTATE',
            tag='REAL ESTATE 02',
            purchase_price=Decimal('12000000.00'),
            current_valuation=Decimal('14500000.00'),
            specification='3,400 sq ft · Oceanfront deck'
        )
        self.client.login(username='shashank', password='Password123!')
        dash_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_resp.status_code, 200)
        self.assertContains(dash_resp, 'property-grid')
        self.assertContains(dash_resp, 'Private Villa Estate')
        self.assertContains(dash_resp, 'Goa Beachfront Penthouse')
        self.assertContains(dash_resp, 'applyOriginalAspectStage')

        prop_resp = self.client.get(reverse('property'))
        self.assertEqual(prop_resp.status_code, 200)
        self.assertContains(prop_resp, 'applyOriginalAspectStage')

    def test_missing_avatar_file_uses_clean_fallback(self):
        """If profile.avatar points to a missing file (e.g. ephemeral storage), render fallback instead of broken img."""
        self.user1.profile.avatar = 'profile_pics/nonexistent_avatar.jpg'
        self.user1.profile.save()
        self.assertFalse(self.user1.profile.has_avatar)

        self.client.login(username='shashank', password='Password123!')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'nonexistent_avatar.jpg')

    def test_email_login_authentication(self):
        """Users log in with email and password (not username)."""
        get_resp = self.client.get(reverse('login'))
        self.assertEqual(get_resp.status_code, 200)
        self.assertContains(get_resp, 'name="email"')
        self.assertNotContains(get_resp, 'name="username"')

        # Wrong password fails
        bad_resp = self.client.post(reverse('login'), {
            'email': 'shashank@jpmc.com',
            'password': 'WrongPassword!'
        })
        self.assertEqual(bad_resp.status_code, 200)
        self.assertFalse(bad_resp.wsgi_request.user.is_authenticated)

        # Case-insensitive valid email succeeds
        ok_resp = self.client.post(reverse('login'), {
            'email': 'SHASHANK@JPMC.COM',
            'password': 'Password123!'
        })
        self.assertRedirects(ok_resp, reverse('dashboard'))
