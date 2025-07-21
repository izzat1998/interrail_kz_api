"""
TDD tests for accounts selectors.
Focus on custom data retrieval and business logic only.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.selectors import UserSelectors

User = get_user_model()


@pytest.mark.django_db
class TestUserSelectors:
    """Test cases for UserSelectors business logic."""

    def test_get_user_profile_data_complete(self):
        """Test getting complete user profile data."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
            user_type="manager",
            telegram_id="123456789",
            telegram_username="johndoe_tg",
            telegram_access=True,
        )

        # Act
        profile_data = UserSelectors.get_user_profile_data(user=user)

        # Assert
        expected_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "user_type_display",
            "telegram_id",
            "telegram_username",
            "telegram_access",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "created_at",
            "updated_at",
        ]

        for field in expected_fields:
            assert field in profile_data

        assert profile_data["username"] == "testuser"
        assert profile_data["email"] == "test@example.com"
        assert profile_data["first_name"] == "John"
        assert profile_data["last_name"] == "Doe"
        assert profile_data["user_type"] == "manager"
        assert profile_data["telegram_id"] == "123456789"
        assert profile_data["telegram_username"] == "johndoe_tg"
        assert profile_data["telegram_access"] is True
        assert profile_data["is_active"] is True

    def test_get_user_profile_data_minimal(self):
        """Test getting user profile data with minimal fields."""
        # Arrange
        user = User.objects.create_user(
            username="minimaluser",
            email="minimal@example.com",
            password="testpassword123",
        )

        # Act
        profile_data = UserSelectors.get_user_profile_data(user=user)

        # Assert
        assert profile_data["username"] == "minimaluser"
        assert profile_data["email"] == "minimal@example.com"
        assert profile_data["user_type"] == "customer"  # default from model
        assert profile_data["telegram_id"] is None
        assert profile_data["telegram_username"] is None
        assert profile_data["telegram_access"] is False  # default
        assert profile_data["first_name"] == ""
        assert profile_data["last_name"] == ""

    def test_get_user_profile_data_structure(self):
        """Test user profile data returns correct data types."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act
        profile_data = UserSelectors.get_user_profile_data(user=user)

        # Assert
        assert isinstance(profile_data, dict)
        assert isinstance(profile_data["id"], int)
        assert isinstance(profile_data["username"], str)
        assert isinstance(profile_data["email"], str)
        assert isinstance(profile_data["is_active"], bool)
        assert isinstance(profile_data["telegram_access"], bool)

    def test_get_users_stats_with_various_users(self):
        """Test user statistics calculation with various user types and statuses."""
        # Arrange
        # Create users of different types and statuses
        User.objects.create_user(
            username="customer1",
            email="c1@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )
        User.objects.create_user(
            username="customer2",
            email="c2@example.com",
            password="pass",
            user_type="customer",
            is_active=False,
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
        User.objects.create_user(
            username="admin2",
            email="a2@example.com",
            password="pass",
            user_type="admin",
            is_active=False,
        )

        # Act
        stats = UserSelectors.get_users_stats()

        # Assert
        assert stats["total_users"] == 5
        assert stats["active_users"] == 3
        assert stats["inactive_users"] == 2

        # Check user type distribution
        user_type_counts = stats["user_type_counts"]
        assert user_type_counts["customer"] == 1  # only active customer
        assert user_type_counts["manager"] == 1
        assert user_type_counts["admin"] == 1  # only active admin

    def test_get_users_stats_empty_database(self):
        """Test user statistics with no users in database."""
        # Act
        stats = UserSelectors.get_users_stats()

        # Assert
        assert stats["total_users"] == 0
        assert stats["active_users"] == 0
        assert stats["inactive_users"] == 0
        assert stats["user_type_counts"]["customer"] == 0
        assert stats["user_type_counts"]["manager"] == 0
        assert stats["user_type_counts"]["admin"] == 0

    def test_get_users_stats_only_one_type(self):
        """Test user statistics with only one user type."""
        # Arrange
        for i in range(3):
            User.objects.create_user(
                username=f"customer{i}",
                email=f"c{i}@example.com",
                password="pass",
                user_type="customer",
            )

        # Act
        stats = UserSelectors.get_users_stats()

        # Assert
        assert stats["total_users"] == 3
        assert stats["active_users"] == 3
        assert stats["inactive_users"] == 0
        assert stats["user_type_counts"]["customer"] == 3
        assert stats["user_type_counts"]["manager"] == 0
        assert stats["user_type_counts"]["admin"] == 0

    def test_get_users_stats_structure(self):
        """Test user statistics returns correct data structure."""
        # Act
        stats = UserSelectors.get_users_stats()

        # Assert
        assert isinstance(stats, dict)
        assert "total_users" in stats
        assert "active_users" in stats
        assert "inactive_users" in stats
        assert "user_type_counts" in stats

        user_type_counts = stats["user_type_counts"]
        assert isinstance(user_type_counts, dict)
        assert "customer" in user_type_counts
        assert "manager" in user_type_counts
        assert "admin" in user_type_counts

        # All values should be integers
        assert isinstance(stats["total_users"], int)
        assert isinstance(stats["active_users"], int)
        assert isinstance(stats["inactive_users"], int)
        assert isinstance(user_type_counts["customer"], int)
        assert isinstance(user_type_counts["manager"], int)
        assert isinstance(user_type_counts["admin"], int)

    def test_search_users_by_username(self):
        """Test user search by username."""
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

        # Act
        results = UserSelectors.search_users(query="john")

        # Assert
        assert len(results) == 1
        assert results[0].username == "johndoe"

    def test_search_users_by_email(self):
        """Test user search by email."""
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

        # Act
        results = UserSelectors.search_users(query="john.doe")

        # Assert
        assert len(results) == 1
        assert results[0].email == "john.doe@example.com"

    def test_search_users_by_first_name(self):
        """Test user search by first name."""
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

        # Act
        results = UserSelectors.search_users(query="john")

        # Assert
        assert len(results) == 1
        assert results[0].first_name == "John"

    def test_search_users_by_last_name(self):
        """Test user search by last name."""
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

        # Act
        results = UserSelectors.search_users(query="doe")

        # Assert
        assert len(results) == 1
        assert results[0].last_name == "Doe"

    def test_search_users_case_insensitive(self):
        """Test user search is case insensitive."""
        # Arrange
        User.objects.create_user(
            username="JohnDoe",
            email="john@example.com",
            password="pass",
            is_active=True,
        )

        # Act
        results_lower = UserSelectors.search_users(query="johndoe")
        results_upper = UserSelectors.search_users(query="JOHNDOE")
        results_mixed = UserSelectors.search_users(query="JohnDoe")

        # Assert
        assert len(results_lower) == 1
        assert len(results_upper) == 1
        assert len(results_mixed) == 1
        assert results_lower[0].username == "JohnDoe"
        assert results_upper[0].username == "JohnDoe"
        assert results_mixed[0].username == "JohnDoe"

    def test_search_users_partial_match(self):
        """Test user search supports partial matching."""
        # Arrange
        User.objects.create_user(
            username="administrator",
            email="admin@example.com",
            password="pass",
            is_active=True,
        )

        # Act
        results = UserSelectors.search_users(query="admin")

        # Assert
        assert len(results) == 1
        assert results[0].username == "administrator"

    def test_search_users_multiple_matches(self):
        """Test user search returns multiple matches."""
        # Arrange
        User.objects.create_user(
            username="john_admin",
            email="john@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="jane_admin",
            email="jane@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="bob_user",
            email="bob@example.com",
            password="pass",
            is_active=True,
        )

        # Act
        results = UserSelectors.search_users(query="admin")

        # Assert
        assert len(results) == 2
        usernames = [user.username for user in results]
        assert "john_admin" in usernames
        assert "jane_admin" in usernames
        assert "bob_user" not in usernames

    def test_search_users_excludes_inactive_users(self):
        """Test user search excludes inactive users."""
        # Arrange
        User.objects.create_user(
            username="activeuser",
            email="active@example.com",
            password="pass",
            is_active=True,
        )
        User.objects.create_user(
            username="inactiveuser",
            email="inactive@example.com",
            password="pass",
            is_active=False,
        )

        # Act
        results = UserSelectors.search_users(query="user")

        # Assert
        assert len(results) == 1
        assert results[0].username == "activeuser"

    def test_search_users_with_limit(self):
        """Test user search respects limit parameter."""
        # Arrange
        for i in range(5):
            User.objects.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password="pass",
                is_active=True,
            )

        # Act
        results = UserSelectors.search_users(query="testuser", limit=3)

        # Assert
        assert len(results) == 3

    def test_search_users_no_matches(self):
        """Test user search returns empty list when no matches."""
        # Arrange
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass",
            is_active=True,
        )

        # Act
        results = UserSelectors.search_users(query="nonexistent")

        # Assert
        assert len(results) == 0
        # Can be either list or QuerySet, both support len() and iteration

    def test_get_user_list_by_type_customer(self):
        """Test getting user list filtered by customer type."""
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
            username="customer2",
            email="c2@example.com",
            password="pass",
            user_type="customer",
            is_active=False,
        )

        # Act
        results = UserSelectors.get_user_list_by_type(user_type="customer")

        # Assert
        assert len(results) == 1  # only active customer
        assert results[0].username == "customer1"
        assert results[0].user_type == "customer"

    def test_get_user_list_by_type_manager(self):
        """Test getting user list filtered by manager type."""
        # Arrange
        User.objects.create_user(
            username="manager1",
            email="m1@example.com",
            password="pass",
            user_type="manager",
            is_active=True,
        )
        User.objects.create_user(
            username="manager2",
            email="m2@example.com",
            password="pass",
            user_type="manager",
            is_active=True,
        )
        User.objects.create_user(
            username="customer1",
            email="c1@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )

        # Act
        results = UserSelectors.get_user_list_by_type(user_type="manager")

        # Assert
        assert len(results) == 2
        usernames = [user.username for user in results]
        assert "manager1" in usernames
        assert "manager2" in usernames
        assert "customer1" not in usernames

    def test_get_user_list_by_type_excludes_inactive(self):
        """Test user list by type excludes inactive users."""
        # Arrange
        User.objects.create_user(
            username="active_admin",
            email="active@example.com",
            password="pass",
            user_type="admin",
            is_active=True,
        )
        User.objects.create_user(
            username="inactive_admin",
            email="inactive@example.com",
            password="pass",
            user_type="admin",
            is_active=False,
        )

        # Act
        results = UserSelectors.get_user_list_by_type(user_type="admin")

        # Assert
        assert len(results) == 1
        assert results[0].username == "active_admin"

    def test_get_user_list_by_type_ordered_by_username(self):
        """Test user list by type is ordered by username."""
        # Arrange
        User.objects.create_user(
            username="zebra",
            email="z@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )
        User.objects.create_user(
            username="alpha",
            email="a@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )
        User.objects.create_user(
            username="beta",
            email="b@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )

        # Act
        results = UserSelectors.get_user_list_by_type(user_type="customer")

        # Assert
        assert len(results) == 3
        assert results[0].username == "alpha"
        assert results[1].username == "beta"
        assert results[2].username == "zebra"

    def test_get_user_list_by_type_invalid_type(self):
        """Test user list by type with invalid user type returns empty list."""
        # Arrange
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass",
            user_type="customer",
            is_active=True,
        )

        # Act
        results = UserSelectors.get_user_list_by_type(user_type="invalid_type")

        # Assert
        assert len(results) == 0
        # Can be either list or QuerySet, both support len() and iteration
