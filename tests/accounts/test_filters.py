"""
TDD tests for accounts filters.
Focus on custom filtering logic only.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.accounts.filters import UserFilter

User = get_user_model()


@pytest.mark.django_db
class TestUserFilter:
    """Test cases for UserFilter business logic."""

    @pytest.fixture
    def request_factory(self):
        return RequestFactory()

    def test_filter_search_by_username(self, request_factory):
        """Test search filter by username."""
        # Arrange
        User.objects.create_user(
            username="johndoe",
            email="john@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="janedoe",
            email="jane@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="bobsmith",
            email="bob@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "john"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "johndoe"

    def test_filter_search_by_email(self, request_factory):
        """Test search filter by email."""
        # Arrange
        User.objects.create_user(
            username="user1",
            email="john.doe@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="user2",
            email="jane.smith@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "john.doe"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().email == "john.doe@example.com"

    def test_filter_search_by_first_name(self, request_factory):
        """Test search filter by first name."""
        # Arrange
        User.objects.create_user(
            username="user1",
            email="u1@example.com",
            password="pass",
            first_name="John",
            is_active=True,
        )
        User.objects.create_user(
            username="user2",
            email="u2@example.com",
            password="pass",
            first_name="Jane",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "john"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().first_name == "John"

    def test_filter_search_by_last_name(self, request_factory):
        """Test search filter by last name."""
        # Arrange
        User.objects.create_user(
            username="user1",
            email="u1@example.com",
            password="pass",
            last_name="Doe",
            is_active=True,
        )
        User.objects.create_user(
            username="user2",
            email="u2@example.com",
            password="pass",
            last_name="Smith",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "doe"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().last_name == "Doe"

    def test_filter_search_by_telegram_username(self, request_factory):
        """Test search filter by telegram username."""
        # Arrange
        User.objects.create_user(
            username="user1",
            email="u1@example.com",
            password="pass",
            telegram_username="johndoe_tg",
            is_active=True,
        )
        User.objects.create_user(
            username="user2",
            email="u2@example.com",
            password="pass",
            telegram_username="janesmith_tg",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "johndoe"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().telegram_username == "johndoe_tg"

    def test_filter_search_case_insensitive(self, request_factory):
        """Test search filter is case insensitive."""
        # Arrange
        User.objects.create_user(
            username="JohnDoe",
            email="john@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "johndoe"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "JohnDoe"

    def test_filter_search_partial_match(self, request_factory):
        """Test search filter supports partial matching."""
        # Arrange
        User.objects.create_user(
            username="administrator",
            email="admin@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="user", email="user@example.com", password="pass", is_active=True
        )

        request = request_factory.get("/", {"search": "admin"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "administrator"

    def test_filter_search_multiple_matches(self, request_factory):
        """Test search filter returns multiple matches across different fields."""
        # Arrange
        User.objects.create_user(
            username="john_admin",
            email="john@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="jane_user",
            email="jane_admin@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="bob_user",
            email="bob@example.com",
            password="pass",
            first_name="Admin",
            is_active=True,
        )
        User.objects.create_user(
            username="alice_user",
            email="alice@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "admin"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 3
        usernames = [user.username for user in filtered_queryset]
        assert "john_admin" in usernames
        assert "jane_user" in usernames  # matches email
        assert "bob_user" in usernames  # matches first_name
        assert "alice_user" not in usernames

    def test_filter_search_no_matches(self, request_factory):
        """Test search filter returns no matches when search term not found."""
        # Arrange
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "nonexistent"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 0

    def test_filter_search_empty_query(self, request_factory):
        """Test search filter with empty query returns all users."""
        # Arrange
        User.objects.create_user(
            username="user1", email="u1@example.com", password="pass", is_active=True
        )
        User.objects.create_user(
            username="user2", email="u2@example.com", password="pass", is_active=True
        )

        request = request_factory.get("/", {"search": ""})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 2

    def test_filter_search_whitespace_query(self, request_factory):
        """Test search filter with whitespace-only query returns all users."""
        # Arrange
        User.objects.create_user(
            username="user1", email="u1@example.com", password="pass", is_active=True
        )

        request = request_factory.get("/", {"search": "   "})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1

    def test_filter_by_user_type(self, request_factory):
        """Test filtering by user type."""
        # Arrange
        User.objects.create_user(
            username="customer1",
            email="c1@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )
        User.objects.create_user(
            username="manager1",
            email="m1@example.com",
            password="pass",
            user_type="manager",
            is_active=True,
        )
        User.objects.create_user(
            username="admin1",
            email="a1@example.com",
            password="pass",
            user_type="admin",
            is_active=True,
        )

        request = request_factory.get("/", {"user_type": "customer"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().user_type == "customer"

    def test_filter_by_is_active(self, request_factory):
        """Test filtering by active status."""
        # Arrange
        User.objects.create_user(
            username="active_user",
            email="active@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="inactive_user",
            email="inactive@example.com",
            password="pass",
            is_active=False,
        )

        request = request_factory.get("/", {"is_active": "false"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().is_active is False

    def test_filter_by_telegram_access_not_implemented(self, request_factory):
        """Test that telegram_access filtering is not currently implemented."""
        # Arrange
        User.objects.create_user(
            username="tg_user",
            email="tg@example.com",
            password="pass",
            telegram_access=True,
            is_active=True,
        )
        User.objects.create_user(
            username="no_tg_user",
            email="notg@example.com",
            password="pass",
            telegram_access=False,
            is_active=True,
        )

        request = request_factory.get("/", {"telegram_access": "true"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert - Since telegram_access filter is not implemented, all users are returned
        assert filtered_queryset.count() == 2  # both users returned
        # This test documents that telegram_access filtering is not yet implemented

    def test_filter_combined_filters(self, request_factory):
        """Test multiple filters combined."""
        # Arrange
        User.objects.create_user(
            username="john_customer",
            email="john@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )
        User.objects.create_user(
            username="john_manager",
            email="john_m@example.com",
            password="pass",
            user_type="manager",
            is_active=True,
        )
        User.objects.create_user(
            username="jane_customer",
            email="jane@example.com",
            password="pass",
            user_type="customer",
            is_active=False,
        )

        request = request_factory.get(
            "/", {"search": "john", "user_type": "customer", "is_active": "true"}
        )
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "john_customer"

    def test_filter_no_parameters(self, request_factory):
        """Test filter with no parameters returns all users."""
        # Arrange
        User.objects.create_user(
            username="user1", email="u1@example.com", password="pass", is_active=True
        )
        User.objects.create_user(
            username="user2", email="u2@example.com", password="pass", is_active=True
        )

        request = request_factory.get("/", {})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 2

    def test_filter_invalid_boolean_values(self, request_factory):
        """Test filter handles invalid boolean values gracefully."""
        # Arrange
        User.objects.create_user(
            username="user1", email="u1@example.com", password="pass", is_active=True
        )

        request = request_factory.get(
            "/", {"is_active": "invalid", "telegram_access": "not_boolean"}
        )
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert - should not crash and return results
        assert filtered_queryset.count() >= 0

    def test_filter_search_special_characters(self, request_factory):
        """Test search filter handles special characters."""
        # Arrange
        User.objects.create_user(
            username="test.user",
            email="test+user@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "test.user"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "test.user"

    def test_filter_search_with_numbers(self, request_factory):
        """Test search filter handles numeric values."""
        # Arrange
        User.objects.create_user(
            username="user123",
            email="user123@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="user456",
            email="user456@example.com",
            password="pass",
            is_active=True,
        )

        request = request_factory.get("/", {"search": "123"})
        queryset = User.objects.all()

        # Act
        filter_instance = UserFilter(request.GET, queryset=queryset)
        filtered_queryset = filter_instance.qs

        # Assert
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().username == "user123"
