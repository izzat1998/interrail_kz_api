"""
TDD tests for authentication services.
Focus on custom business logic only.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.services import AuthenticationServices

User = get_user_model()


@pytest.mark.django_db
class TestAuthenticationServices:
    """Test cases for AuthenticationServices business logic."""

    def test_authenticate_user_success(self):
        """Test successful user authentication with valid credentials."""
        # Arrange
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            user_type="customer",
            telegram_id="123456789",
        )

        # Act
        result = AuthenticationServices.authenticate_user(
            username="testuser", password="testpassword123"
        )

        # Assert
        assert "access" in result
        assert "refresh" in result
        assert result["access"] is not None
        assert result["refresh"] is not None

        # Verify JWT token contains custom claims
        # Note: Custom claims are added to access token, not refresh token
        from rest_framework_simplejwt.tokens import AccessToken

        access_token = AccessToken(result["access"])
        assert access_token["user_type"] == "customer"
        assert access_token["telegram_id"] == "123456789"

    def test_authenticate_user_invalid_credentials(self):
        """Test authentication fails with invalid credentials."""
        # Arrange
        User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid credentials"):
            AuthenticationServices.authenticate_user(
                username="testuser", password="wrongpassword"
            )

    def test_authenticate_user_inactive_account(self):
        """Test authentication fails with inactive user account."""
        # Arrange
        User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            is_active=False,
        )

        # Act & Assert - Django's authenticate() returns None for inactive users
        with pytest.raises(ValueError, match="Invalid credentials"):
            AuthenticationServices.authenticate_user(
                username="testuser", password="testpassword123"
            )

    def test_authenticate_user_nonexistent_user(self):
        """Test authentication fails with non-existent username."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid credentials"):
            AuthenticationServices.authenticate_user(
                username="nonexistent", password="testpassword123"
            )

    def test_create_user_account_success(self):
        """Test successful user account creation."""
        # Act
        user = AuthenticationServices.create_user_account(
            username="newuser",
            email="newuser@example.com",
            password="newpassword123",
            user_type="manager",
            telegram_id="987654321",
            telegram_username="newuser_tg",
        )

        # Assert
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.user_type == "manager"
        assert user.telegram_id == "987654321"
        assert user.telegram_username == "newuser_tg"
        assert user.check_password("newpassword123")
        assert user.is_active is True

    def test_create_user_account_default_customer_type(self):
        """Test user account creation with default customer type."""
        # Act
        user = AuthenticationServices.create_user_account(
            username="customer",
            email="customer@example.com",
            password="testpassword123",
        )

        # Assert
        assert user.user_type == "customer"  # default value from service method

    def test_create_user_account_invalid_user_type(self):
        """Test user creation fails with invalid user type."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid user type"):
            AuthenticationServices.create_user_account(
                username="newuser",
                email="newuser@example.com",
                password="testpassword123",
                user_type="invalid_type",
            )

    def test_create_user_account_duplicate_username(self):
        """Test user creation fails with duplicate username."""
        # Arrange
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Username already exists"):
            AuthenticationServices.create_user_account(
                username="existinguser",
                email="different@example.com",
                password="testpassword123",
            )

    def test_create_user_account_duplicate_email(self):
        """Test user creation fails with duplicate email."""
        # Arrange
        User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Email already exists"):
            AuthenticationServices.create_user_account(
                username="newuser",
                email="existing@example.com",
                password="testpassword123",
            )

    def test_blacklist_refresh_token_success(self):
        """Test successful refresh token blacklisting."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        refresh = RefreshToken.for_user(user)
        refresh_token_str = str(refresh)

        # Act
        AuthenticationServices.blacklist_refresh_token(refresh_token=refresh_token_str)

        # Assert - token should be blacklisted (can't be used again)
        with pytest.raises(ValueError, match="Invalid refresh token"):
            AuthenticationServices.blacklist_refresh_token(
                refresh_token=refresh_token_str
            )

    def test_blacklist_refresh_token_invalid_token(self):
        """Test blacklisting fails with invalid token."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid refresh token"):
            AuthenticationServices.blacklist_refresh_token(
                refresh_token="invalid-token"
            )

    def test_change_user_password_success(self):
        """Test successful password change."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpassword123"
        )

        # Act
        AuthenticationServices.change_user_password(
            user=user, old_password="oldpassword123", new_password="newpassword456"
        )

        # Assert
        user.refresh_from_db()
        assert user.check_password("newpassword456")
        assert not user.check_password("oldpassword123")

    def test_change_user_password_wrong_old_password(self):
        """Test password change fails with wrong old password."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Current password is incorrect"):
            AuthenticationServices.change_user_password(
                user=user, old_password="wrongpassword", new_password="newpassword456"
            )

        # Verify password wasn't changed
        user.refresh_from_db()
        assert user.check_password("oldpassword123")

    @patch("apps.authentication.services.update_last_login")
    def test_authenticate_user_updates_last_login(self, mock_update_last_login):
        """Test that authentication updates user's last login."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act
        AuthenticationServices.authenticate_user(
            username="testuser", password="testpassword123"
        )

        # Assert
        mock_update_last_login.assert_called_once_with(None, user)

    def test_create_user_account_with_additional_fields(self):
        """Test user creation with additional fields passed through kwargs."""
        # Act
        user = AuthenticationServices.create_user_account(
            username="newuser",
            email="newuser@example.com",
            password="testpassword123",
            first_name="John",
            last_name="Doe",
            telegram_access=True,
        )

        # Assert
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.telegram_access is True
