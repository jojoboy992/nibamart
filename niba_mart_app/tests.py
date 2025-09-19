from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from niba_mart_app.models import Product  # replace 'yourapp' with your actual app name


class SimplePageTests(TestCase):
    def test_home_page(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_about_page(self):
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'about.html')

    def test_contact_page(self):
        response = self.client.get(reverse('contact'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'contact.html')

    def test_user_profile_page(self):
        User = get_user_model()
        user = User.objects.create_user(username='tester', password='password')
        response = self.client.get(reverse('user_profile', args=[user.username]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'profile.html')


class AuthenticatedViewsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='tester', password='password')
        login_success = self.client.login(username='tester', password='password')
        assert login_success, "Login failed during test setup"

    def test_edit_profile_page(self):
        response = self.client.get(reverse('edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_profile.html')

    def test_create_product_post(self):
        response = self.client.post(reverse('create_product'), {
            'name': 'Test Product',
            'description': 'A test',
            'price': 10.99,
            'category': 'electronics',
        })
        self.assertEqual(response.status_code, 302)  # redirected after success
        self.assertTrue(Product.objects.filter(name='Test Product').exists())

    def test_signup_sends_email(self):
        response = self.client.post(reverse('signup'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Testpass123',
            'password2': 'Testpass123',
        })
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Your Verification Code', mail.outbox[0].subject)

    def test_logout(self):
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
