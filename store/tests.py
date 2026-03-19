from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .models import UserProfile, Clothing, RentalOrder, Category
from datetime import date, timedelta

class AuthViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        
        # Test User
        self.user_data = {
            'email': 'testuser@example.com',
            'password': 'testpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '1234567890'
        }
        
    def test_register_view_get(self):
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'register.html')
        
    def test_register_user_post(self):
        response = self.client.post(self.register_url, self.user_data)
        self.assertRedirects(response, reverse('home'))
        
        # Check if user and profile were created
        user = User.objects.get(username=self.user_data['email'])  # username is the same as email
        self.assertEqual(user.email, self.user_data['email'])
        self.assertEqual(user.first_name, self.user_data['first_name'])
        
        # In Django tests, signals run normally so userprofile should be created
        profile = UserProfile.objects.get(user=user)
        self.assertIsNotNone(profile)
        
        # Check if user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_view_get(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_user_post(self):
        # Create user first
        User.objects.create_user(username=self.user_data['email'], email=self.user_data['email'], password=self.user_data['password'])
        
        login_data = {
            'email': self.user_data['email'],
            'password': self.user_data['password']
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertRedirects(response, reverse('home'))
        
        # Check if user is logged in
        self.assertTrue('_auth_user_id' in self.client.session)
        
    def test_login_user_invalid(self):
        login_data = {
            'email': 'wrong@example.com',
            'password': 'wrongpassword'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 200)  # Re-renders login page
        self.assertFormError(response.context['form'], None, 'Invalid email or password.')

    def test_logout_user(self):
        # Create user first
        user = User.objects.create_user(username=self.user_data['email'], email=self.user_data['email'], password=self.user_data['password'])
        
        # Force login
        self.client.force_login(user)
        self.assertTrue('_auth_user_id' in self.client.session)
        
        # Test logout
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse('home'))
        self.assertFalse('_auth_user_id' in self.client.session)

class BookingOverlapTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='password')
        self.category = Category.objects.create(name='Test Category', slug='test-cat')
        self.product = Clothing.objects.create(
            owner=self.user,
            title='Test Item',
            description='Test Description',
            category=self.category,
            gender='men',
            size='M',
            brand='Test Brand',
            price_per_day=100.00,
            security_deposit=500.00,
            is_available=True
        )
        
    def test_overlapping_bookings(self):
        # Create an initial confirmed order: Oct 10 to Oct 12
        RentalOrder.objects.create(
            user=self.user,
            product=self.product,
            start_date=date(2024, 10, 10),
            end_date=date(2024, 10, 12),
            rental_days=3,
            price_per_day=100,
            deposit=500,
            total_amount=800,
            status='confirmed'
        )
        
        # 1. Exact overlap: fail
        try:
            RentalOrder.objects.create(
                user=self.user,
                product=self.product,
                start_date=date(2024, 10, 10),
                end_date=date(2024, 10, 12),
                rental_days=3,
                price_per_day=100,
                deposit=500,
                total_amount=800,
                status='confirmed'
            )
            self.fail("ValidationError not raised for exact overlap")
        except ValidationError:
            pass
        except Exception as e:
            self.fail(f"Wrong exception raised: {type(e).__name__}: {e}")
            
        # 2. Parital overlap (end): fail
        with self.assertRaises(ValidationError):
            RentalOrder.objects.create(
                user=self.user,
                product=self.product,
                start_date=date(2024, 10, 9),
                end_date=date(2024, 10, 10),
                rental_days=2,
                price_per_day=100,
                deposit=500,
                total_amount=700,
                status='confirmed'
            )
            
        # 3. Partial overlap (start): fail
        with self.assertRaises(ValidationError):
            RentalOrder.objects.create(
                user=self.user,
                product=self.product,
                start_date=date(2024, 10, 12),
                end_date=date(2024, 10, 14),
                rental_days=3,
                price_per_day=100,
                deposit=500,
                total_amount=800,
                status='confirmed'
            )
            
        # 4. Adjacent (no overlap): succeed
        order = RentalOrder.objects.create(
            user=self.user,
            product=self.product,
            start_date=date(2024, 10, 13),
            end_date=date(2024, 10, 15),
            rental_days=3,
            price_per_day=100,
            deposit=500,
            total_amount=800,
            status='confirmed'
        )
        self.assertIsNotNone(order.pk)
