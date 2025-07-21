"""
Core permissions business logic tests.
Focus on permission system functionality.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser
from apps.core.permissions import IsAdminOnly, IsManagerOrAdmin


@pytest.mark.django_db
class TestCorePermissions:
    """Test core permission classes business logic."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
            user_type="customer",
        )

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def admin_user(self):
        return CustomUser.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            user_type="admin",
        )

    def test_manager_permission_class(
        self, api_client, customer_user, manager_user, admin_user
    ):
        """Test IsManagerOrAdmin permission class."""
        permission = IsManagerOrAdmin()

        # Mock request objects
        class MockRequest:
            def __init__(self, user):
                self.user = user

        class MockView:
            pass

        # Customer should not have permission
        customer_request = MockRequest(customer_user)
        assert not permission.has_permission(customer_request, MockView())

        # Manager should have permission
        manager_request = MockRequest(manager_user)
        assert permission.has_permission(manager_request, MockView())

        # Admin should have permission
        admin_request = MockRequest(admin_user)
        assert permission.has_permission(admin_request, MockView())

    def test_admin_permission_class(
        self, api_client, customer_user, manager_user, admin_user
    ):
        """Test IsAdminOnly permission class."""
        permission = IsAdminOnly()

        # Mock request objects
        class MockRequest:
            def __init__(self, user):
                self.user = user

        class MockView:
            pass

        # Customer should not have permission
        customer_request = MockRequest(customer_user)
        assert not permission.has_permission(customer_request, MockView())

        # Manager should not have permission
        manager_request = MockRequest(manager_user)
        assert not permission.has_permission(manager_request, MockView())

        # Admin should have permission
        admin_request = MockRequest(admin_user)
        assert permission.has_permission(admin_request, MockView())

    def test_permission_with_unauthenticated_user(self):
        """Test permission classes with unauthenticated user."""
        from django.contrib.auth.models import AnonymousUser

        permission_manager = IsManagerOrAdmin()
        permission_admin = IsAdminOnly()

        class MockRequest:
            def __init__(self):
                self.user = AnonymousUser()

        class MockView:
            pass

        unauthenticated_request = MockRequest()

        # Both permissions should deny unauthenticated users
        assert not permission_manager.has_permission(
            unauthenticated_request, MockView()
        )
        assert not permission_admin.has_permission(unauthenticated_request, MockView())

    def test_permission_with_inactive_user(self, manager_user, admin_user):
        """Test permission classes behavior with inactive users."""
        # Note: Our permission classes only check user_type and authentication, not is_active
        # This is the current business logic as implemented
        manager_user.is_active = False
        manager_user.save()

        admin_user.is_active = False
        admin_user.save()

        permission_manager = IsManagerOrAdmin()
        permission_admin = IsAdminOnly()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        class MockView:
            pass

        # Current implementation allows inactive users if they have correct user_type
        # This documents current behavior, not necessarily desired behavior
        manager_request = MockRequest(manager_user)
        admin_request = MockRequest(admin_user)

        # These pass because permissions only check user_type, not is_active
        assert permission_manager.has_permission(manager_request, MockView())
        assert permission_admin.has_permission(admin_request, MockView())

    def test_customer_only_permission_class(
        self, customer_user, manager_user, admin_user
    ):
        """Test IsCustomerOnly permission class."""
        from apps.core.permissions import IsCustomerOnly

        permission = IsCustomerOnly()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        class MockView:
            pass

        # Customer should have permission
        customer_request = MockRequest(customer_user)
        assert permission.has_permission(customer_request, MockView())

        # Manager should not have permission
        manager_request = MockRequest(manager_user)
        assert not permission.has_permission(manager_request, MockView())

        # Admin should not have permission
        admin_request = MockRequest(admin_user)
        assert not permission.has_permission(admin_request, MockView())

    def test_owner_or_manager_permission_class(
        self, customer_user, manager_user, admin_user
    ):
        """Test IsOwnerOrManagerOrAdmin permission class."""
        from apps.core.permissions import IsOwnerOrManagerOrAdmin

        permission = IsOwnerOrManagerOrAdmin()

        class MockRequest:
            def __init__(self, user):
                self.user = user

        class MockView:
            pass

        class MockObject:
            def __init__(self, user=None, owner=None, created_by=None):
                if user:
                    self.user = user
                if owner:
                    self.owner = owner
                if created_by:
                    self.created_by = created_by

        # All authenticated users should have base permission
        customer_request = MockRequest(customer_user)
        manager_request = MockRequest(manager_user)
        admin_request = MockRequest(admin_user)

        assert permission.has_permission(customer_request, MockView())
        assert permission.has_permission(manager_request, MockView())
        assert permission.has_permission(admin_request, MockView())

        # Test object-level permissions
        customer_object = MockObject(user=customer_user)

        # Customer can access their own object
        assert permission.has_object_permission(
            customer_request, MockView(), customer_object
        )

        # Manager can access any object
        assert permission.has_object_permission(
            manager_request, MockView(), customer_object
        )

        # Admin can access any object
        assert permission.has_object_permission(
            admin_request, MockView(), customer_object
        )

        # Test with owner field
        owner_object = MockObject(owner=customer_user)
        assert permission.has_object_permission(
            customer_request, MockView(), owner_object
        )

        # Test with created_by field
        created_object = MockObject(created_by=customer_user)
        assert permission.has_object_permission(
            customer_request, MockView(), created_object
        )

        # Test object without ownership fields
        no_owner_object = MockObject()
        assert not permission.has_object_permission(
            customer_request, MockView(), no_owner_object
        )
        assert permission.has_object_permission(
            manager_request, MockView(), no_owner_object
        )
        assert permission.has_object_permission(
            admin_request, MockView(), no_owner_object
        )
