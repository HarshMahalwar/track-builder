"""
Tests for the accounts app.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse
import json

User = get_user_model()


class UserModelTest(TestCase):
    """Tests for the custom User model."""

    def test_create_user(self):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.assertEqual(user.username, "testuser")
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_user_str(self):
        user = User.objects.create_user(
            username="johndoe",
            password="pass123",
        )
        self.assertEqual(str(user), "johndoe")

    def test_user_default_fields(self):
        user = User.objects.create_user(
            username="testuser",
            password="pass123",
        )
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
        self.assertEqual(user.email, "")


class RegisterViewTest(TestCase):
    """Tests for the registration endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:register")

    def test_register_success(self):
        data = {
            "username": "newuser",
            "password": "complexpass123!",
            "password_confirm": "complexpass123!",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_password_mismatch(self):
        data = {
            "username": "newuser",
            "password": "complexpass123!",
            "password_confirm": "differentpass!",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password_confirm", response.json()["errors"])

    def test_register_duplicate_username(self):
        User.objects.create_user(username="existing", password="pass123")
        data = {
            "username": "existing",
            "password": "complexpass123!",
            "password_confirm": "complexpass123!",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("username", response.json()["errors"])

    def test_register_short_password(self):
        data = {
            "username": "newuser",
            "password": "short",
            "password_confirm": "short",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json()["errors"])

    def test_register_missing_fields(self):
        data = {}
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_register_invalid_json(self):
        response = self.client.post(
            self.url,
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class LoginViewTest(TestCase):
    """Tests for the login endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:login")
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )

    def test_login_success(self):
        data = {
            "username": "testuser",
            "password": "testpass123",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"], "testuser")

    def test_login_invalid_credentials(self):
        data = {
            "username": "testuser",
            "password": "wrongpass",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_nonexistent_user(self):
        data = {
            "username": "nouser",
            "password": "testpass123",
        }
        response = self.client.post(
            self.url,
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 401)

    def test_login_invalid_json(self):
        response = self.client.post(
            self.url,
            data="not json",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)


class LogoutViewTest(TestCase):
    """Tests for the logout endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:logout")
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
        )

    def test_logout_get(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Signed Out")

    def test_logout_post(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)

    def test_logout_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class ProfileViewTest(TestCase):
    """Tests for the profile endpoint."""

    def setUp(self):
        self.client = Client()
        self.url = reverse("accounts:profile")
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )

    def test_profile_authenticated(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["email"], "test@example.com")
        self.assertEqual(data["id"], self.user.id)

    def test_profile_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Not authenticated")

    def test_profile_has_correct_fields(self):
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(self.url)
        data = response.json()
        expected_fields = {"id", "username", "email", "first_name", "last_name"}
        self.assertEqual(set(data.keys()), expected_fields)
