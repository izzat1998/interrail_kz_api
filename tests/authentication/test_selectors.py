"""
TDD tests for authentication selectors.
Focus on custom data retrieval and business logic only.
"""

import pytest
from django.contrib.auth import get_user_model

from apps.authentication.selectors import AuthenticationSelectors

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationSelectors:
    """Test cases for AuthenticationSelectors business logic."""

    def test_get_user_profile_complete_data(self):
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
        profile = AuthenticationSelectors.get_user_profile(user=user)

        # Assert
        expected_fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "telegram_id",
            "telegram_username",
            "telegram_access",
            "is_active",
            "date_joined",
            "last_login",
        ]

        for field in expected_fields:
            assert field in profile

        assert profile["username"] == "testuser"
        assert profile["email"] == "test@example.com"
        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Doe"
        assert profile["user_type"] == "manager"
        assert profile["telegram_id"] == "123456789"
        assert profile["telegram_username"] == "johndoe_tg"
        assert profile["telegram_access"] is True
        assert profile["is_active"] is True

    def test_get_user_profile_minimal_data(self):
        """Test getting user profile with minimal required data."""
        # Arrange
        user = User.objects.create_user(
            username="minimaluser",
            email="minimal@example.com",
            password="testpassword123",
        )

        # Act
        profile = AuthenticationSelectors.get_user_profile(user=user)

        # Assert
        assert profile["username"] == "minimaluser"
        assert profile["email"] == "minimal@example.com"
        assert profile["user_type"] == "customer"  # default from model
        assert profile["telegram_id"] is None
        assert profile["telegram_username"] is None
        assert profile["telegram_access"] is False  # default

    def test_get_user_permissions_admin_user(self):
        """Test getting permissions for admin user type."""
        # Arrange
        user = User.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpassword123",
            user_type="admin",
        )

        # Act
        permissions = AuthenticationSelectors.get_user_permissions(user=user)

        # Assert
        expected_admin_permissions = {
            "can_manage_users": True,
            "can_view_all_users": True,
            "can_access_admin": True,
            "can_manage_routes": True,
            "can_book_tickets": True,
        }

        for permission, expected_value in expected_admin_permissions.items():
            assert permissions[permission] == expected_value

    def test_get_user_permissions_manager_user(self):
        """Test getting permissions for manager user type."""
        # Arrange
        user = User.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpassword123",
            user_type="manager",
        )

        # Act
        permissions = AuthenticationSelectors.get_user_permissions(user=user)

        # Assert
        expected_manager_permissions = {
            "can_manage_users": False,
            "can_view_all_users": True,
            "can_access_admin": False,
            "can_manage_routes": True,
            "can_book_tickets": True,
        }

        for permission, expected_value in expected_manager_permissions.items():
            assert permissions[permission] == expected_value

    def test_get_user_permissions_customer_user(self):
        """Test getting permissions for customer user type."""
        # Arrange
        user = User.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpassword123",
            user_type="customer",
        )

        # Act
        permissions = AuthenticationSelectors.get_user_permissions(user=user)

        # Assert
        expected_customer_permissions = {
            "can_manage_users": False,
            "can_view_all_users": False,
            "can_access_admin": False,
            "can_manage_routes": False,
            "can_book_tickets": True,
        }

        for permission, expected_value in expected_customer_permissions.items():
            assert permissions[permission] == expected_value

    def test_get_user_permissions_returns_all_permission_keys(self):
        """Test that permissions selector returns all expected permission keys."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            user_type="customer",
        )

        # Act
        permissions = AuthenticationSelectors.get_user_permissions(user=user)

        # Assert
        expected_permission_keys = {
            "can_manage_users",
            "can_view_all_users",
            "can_access_admin",
            "can_manage_routes",
            "can_book_tickets",
        }

        assert set(permissions.keys()) == expected_permission_keys

        # All values should be boolean
        for permission_value in permissions.values():
            assert isinstance(permission_value, bool)

    def test_get_user_by_telegram_id_found(self):
        """Test finding user by telegram ID when user exists."""
        # Arrange
        user = User.objects.create_user(
            username="telegram_user",
            email="telegram@example.com",
            password="testpassword123",
            telegram_id="123456789",
        )

        # Act
        found_user = AuthenticationSelectors.get_user_by_telegram_id(
            telegram_id="123456789"
        )

        # Assert
        assert found_user is not None
        assert found_user.id == user.id
        assert found_user.telegram_id == "123456789"

    def test_get_user_by_telegram_id_not_found(self):
        """Test finding user by telegram ID when user doesn't exist."""
        # Act
        found_user = AuthenticationSelectors.get_user_by_telegram_id(
            telegram_id="nonexistent"
        )

        # Assert
        assert found_user is None

    def test_get_user_by_telegram_id_empty_telegram_id(self):
        """Test finding user with empty telegram ID."""
        # Arrange
        User.objects.create_user(
            username="user_no_telegram",
            email="notelegram@example.com",
            password="testpassword123",
            # telegram_id is None by default
        )

        # Act
        found_user = AuthenticationSelectors.get_user_by_telegram_id(telegram_id="")

        # Assert
        assert found_user is None

    def test_check_user_exists_by_username_found(self):
        """Test checking user existence by username when user exists."""
        # Arrange
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act
        result = AuthenticationSelectors.check_user_exists(username="existinguser")

        # Assert
        assert result["exists"] is True
        assert result["field"] == "username"

    def test_check_user_exists_by_email_found(self):
        """Test checking user existence by email when user exists."""
        # Arrange
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act
        result = AuthenticationSelectors.check_user_exists(email="existing@example.com")

        # Assert
        assert result["exists"] is True
        assert result["field"] == "email"

    def test_check_user_exists_not_found(self):
        """Test checking user existence when user doesn't exist."""
        # Act
        result = AuthenticationSelectors.check_user_exists(
            username="nonexistent", email="nonexistent@example.com"
        )

        # Assert
        assert result["exists"] is False
        assert result["field"] is None

    def test_check_user_exists_username_priority(self):
        """Test that username check has priority over email when both exist."""
        # Arrange
        User.objects.create_user(
            username="user1", email="user1@example.com", password="testpassword123"
        )
        User.objects.create_user(
            username="user2", email="user2@example.com", password="testpassword123"
        )

        # Act - check with existing username and different existing email
        result = AuthenticationSelectors.check_user_exists(
            username="user1", email="user2@example.com"
        )

        # Assert - should return username as the field that exists
        assert result["exists"] is True
        assert result["field"] == "username"

    def test_check_user_exists_no_parameters(self):
        """Test checking user existence with no parameters."""
        # Act
        result = AuthenticationSelectors.check_user_exists()

        # Assert
        assert result["exists"] is False
        assert result["field"] is None

    def test_permissions_logic_completeness(self):
        """Test that permission logic covers all user types defined in model."""
        # Arrange - test all user types from model
        user_types = ["customer", "manager", "admin"]

        for user_type in user_types:
            user = User.objects.create_user(
                username=f"{user_type}_user",
                email=f"{user_type}@example.com",
                password="testpassword123",
                user_type=user_type,
            )

            # Act
            permissions = AuthenticationSelectors.get_user_permissions(user=user)

            # Assert - all permission values should be boolean
            for permission_key, permission_value in permissions.items():
                assert isinstance(
                    permission_value, bool
                ), f"Permission {permission_key} for {user_type} should be boolean"

            # Assert - at least one permission should be True for each user type
            assert any(
                permissions.values()
            ), f"User type {user_type} should have at least one permission"
