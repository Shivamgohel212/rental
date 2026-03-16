from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile

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
        self.assertEqual(profile.phone, self.user_data['phone'])
        
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
        self.assertFormError(response, 'form', None, 'Invalid email or password.')

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
