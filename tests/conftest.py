"""
Global pytest configuration and fixtures.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test.client import Client
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """
    Fixture to provide DRF API client for API testing.
    """
    return APIClient()


@pytest.fixture
def client():
    """
    Fixture to provide Django test client.
    """
    return Client()


@pytest.fixture
def user_factory():
    """
    Factory fixture for creating test users.
    """

    def create_user(
        email="test@example.com",
        password="testpassword123",
        user_type="customer",
        **kwargs,
    ):
        return User.objects.create_user(
            email=email, password=password, user_type=user_type, **kwargs
        )

    return create_user


@pytest.fixture
def customer_user(user_factory):
    """
    Fixture to create a customer user.
    """
    return user_factory(email="customer@example.com", user_type="customer")


@pytest.fixture
def manager_user(user_factory):
    """
    Fixture to create a manager user.
    """
    return user_factory(email="manager@example.com", user_type="manager")


@pytest.fixture
def admin_user(user_factory):
    """
    Fixture to create an admin user.
    """
    return user_factory(email="admin@example.com", user_type="admin")


@pytest.fixture
def authenticated_client(api_client, customer_user):
    """
    Fixture to provide authenticated API client with customer user.
    """
    refresh = RefreshToken.for_user(customer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def manager_client(api_client, manager_user):
    """
    Fixture to provide authenticated API client with manager user.
    """
    refresh = RefreshToken.for_user(manager_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """
    Fixture to provide authenticated API client with admin user.
    """
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client
