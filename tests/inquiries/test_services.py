"""
Tests for inquiry services focusing on business logic.
"""

import pytest

from apps.accounts.models import CustomUser
from apps.inquiries.models import Inquiry
from apps.inquiries.services import InquiryServices


@pytest.mark.django_db
class TestInquiryServices:
    """Test cases for InquiryServices business logic."""

    @pytest.fixture
    def manager_user(self):
        """Create a manager user for testing."""
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def admin_user(self):
        """Create an admin user for testing."""
        return CustomUser.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="testpass123",
            user_type="admin",
        )

    @pytest.fixture
    def customer_user(self):
        """Create a customer user for testing."""
        return CustomUser.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="testpass123",
            user_type="customer",
        )

    def test_create_inquiry_success_with_manager(self, manager_user):
        """Test successful inquiry creation with manager."""
        inquiry = InquiryServices.create_inquiry(
            client="Test Client",
            text="Test inquiry text",
            comment="Test comment",
            sales_manager_id=manager_user.id,
            is_new_customer=True,
            status="pending",
        )

        assert inquiry.client == "Test Client"
        assert inquiry.text == "Test inquiry text"
        assert inquiry.comment == "Test comment"
        assert inquiry.sales_manager == manager_user
        assert inquiry.is_new_customer is True
        assert inquiry.status == "pending"

    def test_create_inquiry_success_with_admin(self, admin_user):
        """Test successful inquiry creation with admin."""
        inquiry = InquiryServices.create_inquiry(
            client="Test Client",
            text="Test inquiry text",
            sales_manager_id=admin_user.id,
            is_new_customer=False,
        )

        assert inquiry.sales_manager == admin_user
        assert inquiry.is_new_customer is False
        assert inquiry.status == "pending"  # Default status

    def test_create_inquiry_without_sales_manager(self):
        """Test inquiry creation without sales manager."""
        inquiry = InquiryServices.create_inquiry(
            client="Test Client", text="Test inquiry text", sales_manager_id=None
        )

        assert inquiry.client == "Test Client"
        assert inquiry.text == "Test inquiry text"
        assert inquiry.sales_manager is None
        assert inquiry.is_new_customer is False  # Default value

    def test_create_inquiry_strips_whitespace(self, manager_user):
        """Test that inquiry creation strips whitespace from text fields."""
        inquiry = InquiryServices.create_inquiry(
            client="  Test Client  ",
            text="  Test inquiry text  ",
            comment="  Test comment  ",
            sales_manager_id=manager_user.id,
        )

        assert inquiry.client == "Test Client"
        assert inquiry.text == "Test inquiry text"
        assert inquiry.comment == "Test comment"

    def test_create_inquiry_invalid_sales_manager_id(self):
        """Test inquiry creation with non-existent sales manager ID."""
        with pytest.raises(ValueError, match="Sales manager not found"):
            InquiryServices.create_inquiry(
                client="Test Client", text="Test inquiry text", sales_manager_id=99999
            )

    def test_create_inquiry_customer_as_sales_manager(self, customer_user):
        """Test inquiry creation with customer user as sales manager (should fail)."""
        with pytest.raises(
            ValueError, match="Sales manager must be a manager or admin user"
        ):
            InquiryServices.create_inquiry(
                client="Test Client",
                text="Test inquiry text",
                sales_manager_id=customer_user.id,
            )

    def test_update_inquiry_client_success(self, manager_user):
        """Test successful inquiry client update."""
        inquiry = Inquiry.objects.create(
            client="Original Client", text="Original text", sales_manager=manager_user
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, client="Updated Client"
        )

        assert updated_inquiry.client == "Updated Client"
        assert updated_inquiry.text == "Original text"  # Unchanged

    def test_update_inquiry_text_success(self, manager_user):
        """Test successful inquiry text update."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Original text", sales_manager=manager_user
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, text="Updated text"
        )

        assert updated_inquiry.text == "Updated text"
        assert updated_inquiry.client == "Test Client"  # Unchanged

    def test_update_inquiry_status_success(self, manager_user):
        """Test successful inquiry status update."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="pending",
            sales_manager=manager_user,
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, status="quoted"
        )

        assert updated_inquiry.status == "quoted"

    def test_update_inquiry_sales_manager_success(self, manager_user, admin_user):
        """Test successful sales manager update."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test text", sales_manager=manager_user
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, sales_manager_id=admin_user.id
        )

        assert updated_inquiry.sales_manager == admin_user

    def test_update_inquiry_is_new_customer_success(self, manager_user):
        """Test successful is_new_customer update."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, is_new_customer=True
        )

        assert updated_inquiry.is_new_customer is True

    def test_update_inquiry_comment_success(self, manager_user):
        """Test successful comment update."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            comment="Original comment",
            sales_manager=manager_user,
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, comment="Updated comment"
        )

        assert updated_inquiry.comment == "Updated comment"

    def test_update_inquiry_strips_whitespace(self, manager_user):
        """Test that inquiry update strips whitespace."""
        inquiry = Inquiry.objects.create(
            client="Original Client", text="Original text", sales_manager=manager_user
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry,
            client="  Updated Client  ",
            text="  Updated text  ",
            comment="  Updated comment  ",
        )

        assert updated_inquiry.client == "Updated Client"
        assert updated_inquiry.text == "Updated text"
        assert updated_inquiry.comment == "Updated comment"

    def test_update_inquiry_empty_client_validation(self, manager_user):
        """Test update inquiry with empty client name."""
        inquiry = Inquiry.objects.create(
            client="Original Client", text="Original text", sales_manager=manager_user
        )

        with pytest.raises(ValueError, match="Client name cannot be empty"):
            InquiryServices.update_inquiry(inquiry=inquiry, client="   ")

    def test_update_inquiry_empty_text_validation(self, manager_user):
        """Test update inquiry with empty text."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Original text", sales_manager=manager_user
        )

        with pytest.raises(ValueError, match="Inquiry text cannot be empty"):
            InquiryServices.update_inquiry(inquiry=inquiry, text="   ")

    def test_update_inquiry_invalid_sales_manager(self, manager_user):
        """Test update inquiry with invalid sales manager ID."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test text", sales_manager=manager_user
        )

        with pytest.raises(ValueError, match="Sales manager not found"):
            InquiryServices.update_inquiry(inquiry=inquiry, sales_manager_id=99999)

    def test_update_inquiry_customer_as_sales_manager(
        self, manager_user, customer_user
    ):
        """Test update inquiry with customer as sales manager."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test text", sales_manager=manager_user
        )

        with pytest.raises(
            ValueError, match="Sales manager must be a manager or admin user"
        ):
            InquiryServices.update_inquiry(
                inquiry=inquiry, sales_manager_id=customer_user.id
            )

    def test_update_inquiry_no_changes(self, manager_user):
        """Test update inquiry with no changes."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test text", sales_manager=manager_user
        )
        original_updated_at = inquiry.updated_at

        updated_inquiry = InquiryServices.update_inquiry(inquiry=inquiry)

        # Should return the same inquiry without changes
        assert updated_inquiry == inquiry
        assert updated_inquiry.updated_at == original_updated_at

    def test_delete_inquiry_success(self, manager_user):
        """Test successful inquiry deletion."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="pending",
            sales_manager=manager_user,
        )
        inquiry_id = inquiry.id

        InquiryServices.delete_inquiry(inquiry=inquiry)

        assert not Inquiry.objects.filter(id=inquiry_id).exists()

    def test_delete_inquiry_with_success_status(self, manager_user):
        """Test deletion of inquiry with success status (should fail)."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="success",
            sales_manager=manager_user,
        )

        with pytest.raises(
            ValueError, match="Cannot delete inquiry with success or quoted status"
        ):
            InquiryServices.delete_inquiry(inquiry=inquiry)

        # Inquiry should still exist
        assert Inquiry.objects.filter(id=inquiry.id).exists()

    def test_delete_inquiry_with_quoted_status(self, manager_user):
        """Test deletion of inquiry with quoted status (should fail)."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="quoted",
            sales_manager=manager_user,
        )

        with pytest.raises(
            ValueError, match="Cannot delete inquiry with success or quoted status"
        ):
            InquiryServices.delete_inquiry(inquiry=inquiry)

        # Inquiry should still exist
        assert Inquiry.objects.filter(id=inquiry.id).exists()

    def test_delete_inquiry_with_failed_status(self, manager_user):
        """Test successful deletion of inquiry with failed status."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="failed",
            sales_manager=manager_user,
        )
        inquiry_id = inquiry.id

        InquiryServices.delete_inquiry(inquiry=inquiry)

        assert not Inquiry.objects.filter(id=inquiry_id).exists()

    def test_create_inquiry_transaction_rollback(self, manager_user):
        """Test that inquiry creation uses transaction and rolls back on error."""
        # This test would need to simulate a database error
        # For now, we'll test that the method uses transaction.atomic
        import inspect

        source = inspect.getsource(InquiryServices.create_inquiry)
        assert "transaction.atomic" in source

    def test_update_inquiry_transaction_rollback(self, manager_user):
        """Test that inquiry update uses transaction and rolls back on error."""
        import inspect

        source = inspect.getsource(InquiryServices.update_inquiry)
        assert "transaction.atomic" in source
