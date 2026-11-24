from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
import json

from finance.models import UserProfile, Asset, Liability, Transaction, MonthlyFinancialPlan


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

        # Check annual inflow is exactly 18 Lakhs (not 50 Lakhs!)
        dash_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_resp.context['annual_income'], Decimal('1800000.00'))
        self.assertEqual(dash_resp.context['monthly_income'], Decimal('150000.00'))

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
