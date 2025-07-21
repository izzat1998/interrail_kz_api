"""
TDD tests for accounts services.
Focus on custom business logic only.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.services import UserServices

User = get_user_model()


@pytest.mark.django_db
class TestUserServices:
    """Test cases for UserServices business logic."""

    def test_create_user_success(self):
        """Test successful user creation with all fields."""
        # Act
        user = UserServices.create_user(
            username="newuser",
            email="newuser@example.com",
            password="newpassword123",
            user_type="manager",
            first_name="John",
            last_name="Doe",
            telegram_id="123456789",
            telegram_username="johndoe_tg",
        )

        # Assert
        assert user.username == "newuser"
        assert user.email == "newuser@example.com"
        assert user.user_type == "manager"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.telegram_id == "123456789"
        assert user.telegram_username == "johndoe_tg"
        assert user.check_password("newpassword123")
        assert user.is_active is True

    def test_create_user_with_default_customer_type(self):
        """Test user creation with default customer type."""
        # Act
        user = UserServices.create_user(
            username="defaultuser",
            email="default@example.com",
            password="testpassword123",
        )

        # Assert
        assert user.user_type == "customer"  # default from service
        assert user.is_active is True

    def test_create_user_duplicate_username_raises_error(self):
        """Test user creation fails with duplicate username."""
        # Arrange
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Username already exists"):
            UserServices.create_user(
                username="existing",
                email="different@example.com",
                password="testpassword123",
            )

    def test_create_user_duplicate_email_raises_error(self):
        """Test user creation fails with duplicate email."""
        # Arrange
        User.objects.create_user(
            username="existing",
            email="existing@example.com",
            password="testpassword123",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Email already exists"):
            UserServices.create_user(
                username="newuser",
                email="existing@example.com",
                password="testpassword123",
            )

    def test_create_user_invalid_user_type_raises_error(self):
        """Test user creation fails with invalid user type."""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid user type"):
            UserServices.create_user(
                username="newuser",
                email="newuser@example.com",
                password="testpassword123",
                user_type="invalid_type",
            )

    def test_create_user_case_sensitive_username_validation(self):
        """Test username uniqueness is case sensitive."""
        # Arrange
        User.objects.create_user(
            username="TestUser", email="test@example.com", password="testpassword123"
        )

        # Act - Different case should be allowed
        user = UserServices.create_user(
            username="testuser",  # different case
            email="different@example.com",
            password="testpassword123",
        )

        # Assert
        assert user.username == "testuser"
        assert User.objects.filter(username="TestUser").exists()
        assert User.objects.filter(username="testuser").exists()

    def test_create_user_email_case_handling(self):
        """Test email case handling during user creation."""
        # Arrange
        existing_user = User.objects.create_user(
            username="existing", email="TEST@Example.com", password="testpassword123"
        )

        # Act & Assert - Check if emails are case-insensitive or normalized
        try:
            UserServices.create_user(
                username="newuser",
                email="test@example.com",  # different case
                password="testpassword123",
            )
            # If this succeeds, emails are case-sensitive
            assert User.objects.filter(email__iexact="test@example.com").count() == 2
        except ValueError as e:
            # If this fails, emails are case-insensitive
            assert "Email already exists" in str(e)
            # Check what email was actually stored
            assert existing_user.email.lower() == "test@example.com"

    @patch("apps.accounts.services.transaction.atomic")
    def test_create_user_uses_transaction(self, mock_atomic):
        """Test user creation uses database transaction."""
        # Arrange
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock()

        # Act
        UserServices.create_user(
            username="transactiontest",
            email="transaction@example.com",
            password="testpassword123",
        )

        # Assert
        mock_atomic.assert_called_once()

    def test_update_user_success_partial_update(self):
        """Test successful partial user update."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword",
            user_type="customer",
        )

        # Act
        updated_user = UserServices.update_user(
            user_id=user.id, email="newemail@example.com", user_type="manager"
        )

        # Assert
        assert updated_user.username == "testuser"  # unchanged
        assert updated_user.email == "newemail@example.com"  # changed
        assert updated_user.user_type == "manager"  # changed
        assert updated_user.check_password("oldpassword")  # unchanged

    def test_update_user_success_with_password(self):
        """Test successful user update with password change."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="oldpassword"
        )

        # Act
        updated_user = UserServices.update_user(
            user_id=user.id, password="newpassword123"
        )

        # Assert
        assert updated_user.check_password("newpassword123")
        assert not updated_user.check_password("oldpassword")

    def test_update_user_nonexistent_user_raises_error(self):
        """Test updating non-existent user raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            UserServices.update_user(user_id=99999, email="new@example.com")

    def test_update_user_duplicate_username_raises_error(self):
        """Test updating to duplicate username raises error."""
        # Arrange
        User.objects.create_user(
            username="user1", email="user1@example.com", password="testpassword123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Username already exists"):
            UserServices.update_user(user_id=user2.id, username="user1")

    def test_update_user_duplicate_email_raises_error(self):
        """Test updating to duplicate email raises error."""
        # Arrange
        User.objects.create_user(
            username="user1", email="user1@example.com", password="testpassword123"
        )
        user2 = User.objects.create_user(
            username="user2", email="user2@example.com", password="testpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Email already exists"):
            UserServices.update_user(user_id=user2.id, email="user1@example.com")

    def test_update_user_invalid_user_type_raises_error(self):
        """Test updating to invalid user type raises error."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid user type"):
            UserServices.update_user(user_id=user.id, user_type="invalid_type")

    def test_update_user_same_username_allowed(self):
        """Test updating user with same username is allowed."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act
        updated_user = UserServices.update_user(
            user_id=user.id,
            username="testuser",  # same username
            email="newemail@example.com",
        )

        # Assert
        assert updated_user.username == "testuser"
        assert updated_user.email == "newemail@example.com"

    def test_update_user_same_email_allowed(self):
        """Test updating user with same email is allowed."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act
        updated_user = UserServices.update_user(
            user_id=user.id, email="test@example.com", first_name="John"  # same email
        )

        # Assert
        assert updated_user.email == "test@example.com"
        assert updated_user.first_name == "John"

    @patch("apps.accounts.services.transaction.atomic")
    def test_update_user_uses_transaction(self, mock_atomic):
        """Test user update uses database transaction."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )
        mock_atomic.return_value.__enter__ = MagicMock()
        mock_atomic.return_value.__exit__ = MagicMock()

        # Act
        UserServices.update_user(user_id=user.id, email="new@example.com")

        # Assert
        mock_atomic.assert_called_once()

    def test_delete_user_success_soft_delete(self):
        """Test successful user soft delete (deactivation)."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            is_active=True,
        )

        # Act
        UserServices.delete_user(user_id=user.id)

        # Assert
        user.refresh_from_db()
        assert user.is_active is False
        assert User.objects.filter(id=user.id).exists()  # user still exists

    def test_delete_user_nonexistent_user_raises_error(self):
        """Test deleting non-existent user raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            UserServices.delete_user(user_id=99999)

    def test_delete_user_already_inactive_no_error(self):
        """Test deleting already inactive user doesn't raise error."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            is_active=False,
        )

        # Act & Assert - should not raise error
        UserServices.delete_user(user_id=user.id)
        user.refresh_from_db()
        assert user.is_active is False

    def test_activate_user_success(self):
        """Test successful user activation."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            is_active=False,
        )

        # Act
        activated_user = UserServices.activate_user(user_id=user.id)

        # Assert
        assert activated_user.is_active is True
        user.refresh_from_db()
        assert user.is_active is True

    def test_activate_user_nonexistent_user_raises_error(self):
        """Test activating non-existent user raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            UserServices.activate_user(user_id=99999)

    def test_activate_user_already_active_no_error(self):
        """Test activating already active user doesn't raise error."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            is_active=True,
        )

        # Act & Assert - should not raise error
        activated_user = UserServices.activate_user(user_id=user.id)
        assert activated_user.is_active is True

    def test_change_user_type_success(self):
        """Test successful user type change."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            user_type="customer",
        )

        # Act
        updated_user = UserServices.change_user_type(
            user_id=user.id, new_user_type="manager"
        )

        # Assert
        assert updated_user.user_type == "manager"
        user.refresh_from_db()
        assert user.user_type == "manager"

    def test_change_user_type_nonexistent_user_raises_error(self):
        """Test changing user type for non-existent user raises error."""
        # Act & Assert
        with pytest.raises(ValueError, match="User not found"):
            UserServices.change_user_type(user_id=99999, new_user_type="manager")

    def test_change_user_type_invalid_type_raises_error(self):
        """Test changing to invalid user type raises error."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid user type"):
            UserServices.change_user_type(user_id=user.id, new_user_type="invalid_type")

    def test_change_user_type_same_type_allowed(self):
        """Test changing user type to same type is allowed."""
        # Arrange
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpassword123",
            user_type="manager",
        )

        # Act
        updated_user = UserServices.change_user_type(
            user_id=user.id, new_user_type="manager"  # same type
        )

        # Assert
        assert updated_user.user_type == "manager"

    def test_all_user_types_are_valid(self):
        """Test that all defined user types are considered valid."""
        # Arrange
        user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpassword123"
        )

        valid_types = ["customer", "manager", "admin"]

        # Act & Assert
        for user_type in valid_types:
            updated_user = UserServices.change_user_type(
                user_id=user.id, new_user_type=user_type
            )
            assert updated_user.user_type == user_type
