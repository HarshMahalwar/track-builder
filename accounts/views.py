"""
Views for the accounts app.
"""

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import json

User = get_user_model()


class RegisterSerializer:
    """Minimal serializer for user registration."""

    def __init__(self, data: dict):
        self.data = data
        self.errors: dict = {}

    def is_valid(self) -> bool:
        username = self.data.get("username", "").strip()
        password = self.data.get("password", "")
        password_confirm = self.data.get("password_confirm", "")

        if not username:
            self.errors["username"] = ["This field is required."]
        elif User.objects.filter(username=username).exists():
            self.errors["username"] = ["A user with that username already exists."]

        if not password:
            self.errors["password"] = ["This field is required."]
        elif len(password) < 8:
            self.errors["password"] = ["Password must be at least 8 characters."]

        if password != password_confirm:
            self.errors["password_confirm"] = ["Passwords do not match."]

        return len(self.errors) == 0

    def save(self) -> User:
        return User.objects.create_user(
            username=self.data["username"],
            password=self.data["password"],
        )


@method_decorator(csrf_exempt, name="dispatch")
class RegisterView(View):
    """Handle user registration."""

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        serializer = RegisterSerializer(data)
        if serializer.is_valid():
            user = serializer.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return JsonResponse(
                {"message": "Registration successful", "user": user.username},
                status=201,
            )
        return JsonResponse({"errors": serializer.errors}, status=400)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(View):
    """Handle user login."""

    def get(self, request):
        return render(request, "account/login.html")

    def post(self, request):
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        username = data.get("username")
        password = data.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            return JsonResponse({"message": "Login successful", "user": user.username})
        return JsonResponse({"error": "Invalid credentials"}, status=401)


class LogoutView(View):
    """Handle user logout."""

    def get(self, request):
        logout(request)
        return render(request, "account/logout.html")

    def post(self, request):
        logout(request)
        return JsonResponse({"message": "Logout successful"})


class ProfileView(View):
    """Return the current user's profile."""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)

        return JsonResponse(
            {
                "id": request.user.id,
                "username": request.user.username,
                "email": request.user.email,
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
            }
        )
