"""
Inquiry business logic tests.
Focus on business rules, workflow, and core functionality.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.inquiries.models import Inquiry
from apps.inquiries.selectors import InquirySelectors
from apps.inquiries.services import InquiryServices


@pytest.mark.django_db
class TestInquiryLifecycle:
    """Test complete inquiry business workflow."""

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

    def test_inquiry_creation_business_logic(self, manager_user):
        """Test inquiry creation with business validation."""
        inquiry = InquiryServices.create_inquiry(
            client="Business Corp",
            text="Need corporate travel package",
            sales_manager_id=manager_user.id,
            is_new_customer=True,
            comment="High priority client",
        )

        assert inquiry.client == "Business Corp"
        assert inquiry.text == "Need corporate travel package"
        assert inquiry.sales_manager == manager_user
        assert inquiry.is_new_customer is True
        assert inquiry.comment == "High priority client"
        assert inquiry.status == "pending"  # Default status

    def test_inquiry_status_progression(self, manager_user):
        """Test inquiry status changes through business workflow."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test inquiry",
            status="pending",
            sales_manager=manager_user,
        )

        # Progress through workflow: pending → quoted → success
        inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, status="quoted", comment="Quote prepared and sent"
        )
        assert inquiry.status == "quoted"

        inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry, status="success", comment="Client accepted quote"
        )
        assert inquiry.status == "success"

    def test_inquiry_assignment_validation(self, manager_user):
        """Test sales manager assignment business rules."""
        # Manager can be assigned
        inquiry = InquiryServices.create_inquiry(
            client="Test Client",
            text="Test inquiry",
            sales_manager_id=manager_user.id,
        )
        assert inquiry.sales_manager == manager_user

    def test_customer_cannot_be_sales_manager(self):
        """Test that customers cannot be assigned as sales managers."""
        customer = CustomUser.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
            user_type="customer",
        )

        with pytest.raises(
            ValueError, match="Sales manager must be a manager or admin user"
        ):
            InquiryServices.create_inquiry(
                client="Test Client",
                text="Test inquiry",
                sales_manager_id=customer.id,
            )

    def test_inquiry_deletion_business_rules(self, manager_user):
        """Test inquiry deletion business constraints."""
        # Can delete pending inquiry
        pending_inquiry = Inquiry.objects.create(
            client="Pending Client",
            text="Pending inquiry",
            status="pending",
            sales_manager=manager_user,
        )

        InquiryServices.delete_inquiry(inquiry=pending_inquiry)
        assert not Inquiry.objects.filter(id=pending_inquiry.id).exists()

        # Cannot delete successful inquiry
        success_inquiry = Inquiry.objects.create(
            client="Success Client",
            text="Success inquiry",
            status="success",
            sales_manager=manager_user,
        )

        with pytest.raises(
            ValueError, match="Cannot delete inquiry with success or quoted status"
        ):
            InquiryServices.delete_inquiry(inquiry=success_inquiry)

    def test_inquiry_update_validation(self, manager_user):
        """Test inquiry update business validation."""
        inquiry = Inquiry.objects.create(
            client="Original Client",
            text="Original text",
            sales_manager=manager_user,
        )

        # Valid updates
        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry,
            client="Updated Client",
            text="Updated text",
            is_new_customer=True,
        )

        assert updated_inquiry.client == "Updated Client"
        assert updated_inquiry.text == "Updated text"
        assert updated_inquiry.is_new_customer is True

    def test_inquiry_without_sales_manager(self):
        """Test inquiry creation without assigned sales manager."""
        inquiry = InquiryServices.create_inquiry(
            client="Unassigned Client",
            text="Unassigned inquiry",
            sales_manager_id=None,
        )

        assert inquiry.sales_manager is None
        assert inquiry.client == "Unassigned Client"


@pytest.mark.django_db
class TestInquiryDataRetrieval:
    """Test inquiry data retrieval and statistics."""

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def sample_inquiries(self, manager_user):
        """Create diverse inquiry data for testing."""
        return [
            Inquiry.objects.create(
                client="Client A",
                text="Inquiry A",
                status="pending",
                is_new_customer=True,
                sales_manager=manager_user,
            ),
            Inquiry.objects.create(
                client="Client B",
                text="Inquiry B",
                status="quoted",
                is_new_customer=False,
                sales_manager=manager_user,
            ),
            Inquiry.objects.create(
                client="Client C",
                text="Inquiry C",
                status="success",
                is_new_customer=True,
                sales_manager=manager_user,
            ),
            Inquiry.objects.create(
                client="Client D",
                text="Inquiry D",
                status="failed",
                is_new_customer=False,
                sales_manager=manager_user,
            ),
        ]

    def test_inquiry_statistics_calculation(self, sample_inquiries):
        """Test business statistics calculation."""
        stats = InquirySelectors.get_inquiries_stats()

        assert stats["total_inquiries"] == 4
        assert stats["pending_count"] == 1
        assert stats["quoted_count"] == 1
        assert stats["success_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["new_customers_count"] == 2
        assert stats["conversion_rate"] == 25.0  # 1 success out of 4 total

    def test_inquiry_filtering_by_status(self, sample_inquiries):
        """Test filtering inquiries by status."""
        pending_inquiries = InquirySelectors.get_inquiries_list(
            filters={"status": ["pending"]}
        )
        assert len(pending_inquiries) == 1
        assert pending_inquiries[0].status == "pending"

    def test_inquiry_filtering_by_customer_type(self, sample_inquiries):
        """Test filtering inquiries by new customer status."""
        new_customer_inquiries = InquirySelectors.get_inquiries_list(
            filters={"is_new_customer": True}
        )
        assert len(new_customer_inquiries) == 2
        for inquiry in new_customer_inquiries:
            assert inquiry.is_new_customer is True

    def test_inquiry_search_functionality(self, sample_inquiries):
        """Test inquiry search across client and text fields."""
        search_results = InquirySelectors.get_inquiries_list(
            filters={"search": "Client A"}
        )
        assert len(search_results) == 1
        assert search_results[0].client == "Client A"

    def test_inquiry_retrieval_with_sales_manager(self, sample_inquiries):
        """Test inquiry retrieval includes sales manager data."""
        inquiry = sample_inquiries[0]
        inquiry_data = InquirySelectors.get_inquiry_by_id(inquiry_id=inquiry.id)

        assert inquiry_data["id"] == inquiry.id
        assert inquiry_data["client"] == "Client A"
        assert inquiry_data["sales_manager"]["username"] == "manager"


@pytest.mark.django_db
class TestInquiryAPIBusinessLogic:
    """Test inquiry API endpoints business logic."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

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

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
            user_type="customer",
        )

    def test_inquiry_creation_via_api(self, api_client, manager_user):
        """Test inquiry creation through API endpoint."""
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        url = reverse("inquiries:inquiry-create")
        data = {
            "client": "API Test Client",
            "text": "API test inquiry",
            "sales_manager_id": manager_user.id,
            "is_new_customer": True,
            "comment": "Created via API",
            "status": "pending",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["client"] == "API Test Client"
        assert response.data["is_new_customer"] is True

    def test_inquiry_update_via_api(self, api_client, manager_user):
        """Test inquiry update through API endpoint."""
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Create inquiry
        inquiry = Inquiry.objects.create(
            client="Original Client",
            text="Original text",
            status="pending",
            sales_manager=manager_user,
        )

        # Update inquiry
        url = reverse("inquiries:inquiry-update", kwargs={"inquiry_id": inquiry.id})
        data = {
            "status": "quoted",
            "comment": "Quote prepared",
        }

        response = api_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "quoted"
        assert response.data["comment"] == "Quote prepared"

    def test_inquiry_list_pagination(self, api_client, manager_user):
        """Test inquiry list pagination business logic."""
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Create multiple inquiries
        for i in range(15):
            Inquiry.objects.create(
                client=f"Client {i}",
                text=f"Inquiry {i}",
                sales_manager=manager_user,
            )

        url = reverse("inquiries:inquiry-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "results" in response.data
        assert len(response.data["results"]) == 10  # Default pagination limit

    def test_inquiry_stats_business_data(self, api_client, manager_user):
        """Test inquiry statistics API returns business metrics."""
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Create sample data
        Inquiry.objects.create(
            client="Success Client",
            text="Success inquiry",
            status="success",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Pending Client",
            text="Pending inquiry",
            status="pending",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        url = reverse("inquiries:inquiry-stats")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_inquiries"] == 2
        assert response.data["success_count"] == 1
        assert response.data["new_customers_count"] == 1
        assert response.data["conversion_rate"] == 50.0

    def test_customer_access_restrictions(self, api_client, customer_user):
        """Test that customers cannot access inquiry management."""
        refresh = RefreshToken.for_user(customer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Test various inquiry endpoints
        endpoints = [
            reverse("inquiries:inquiry-list"),
            reverse("inquiries:inquiry-create"),
            reverse("inquiries:inquiry-stats"),
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_deletion_privileges(self, api_client, admin_user):
        """Test admin-specific deletion capabilities."""
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Create deletable inquiry
        inquiry = Inquiry.objects.create(
            client="Deletable Client",
            text="Deletable inquiry",
            status="pending",
            sales_manager=admin_user,
        )

        url = reverse("inquiries:inquiry-delete", kwargs={"inquiry_id": inquiry.id})
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert not Inquiry.objects.filter(id=inquiry.id).exists()


@pytest.mark.django_db
class TestInquiryBusinessValidation:
    """Test business validation rules for inquiries."""

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            username="manager",
            email="manager@example.com",
            password="testpass123",
            user_type="manager",
        )

    def test_inquiry_field_validation(self, manager_user):
        """Test inquiry field validation logic."""
        # Test successful creation with valid fields
        inquiry = InquiryServices.create_inquiry(
            client="Valid Client",
            text="Valid inquiry text",
            sales_manager_id=manager_user.id,
        )
        assert inquiry.client == "Valid Client"
        assert inquiry.text == "Valid inquiry text"

    def test_status_transitions(self, manager_user):
        """Test valid status transitions in business workflow."""
        Inquiry.objects.create(
            client="Test Client",
            text="Test inquiry",
            status="pending",
            sales_manager=manager_user,
        )

        # Valid transitions
        valid_statuses = ["quoted", "success", "failed"]
        for w in valid_statuses:
            test_inquiry = Inquiry.objects.create(
                client="Test Client",
                text="Test inquiry",
                status="pending",
                sales_manager=manager_user,
            )

            updated = InquiryServices.update_inquiry(inquiry=test_inquiry, status=w)
            assert updated.status == w

    def test_new_customer_flag_logic(self, manager_user):
        """Test new customer flag business logic."""
        # Default to False when not specified
        inquiry = InquiryServices.create_inquiry(
            client="Test Client",
            text="Test inquiry",
            sales_manager_id=manager_user.id,
        )
        assert inquiry.is_new_customer is False

        # Explicitly set to True
        new_customer_inquiry = InquiryServices.create_inquiry(
            client="New Client",
            text="New inquiry",
            sales_manager_id=manager_user.id,
            is_new_customer=True,
        )
        assert new_customer_inquiry.is_new_customer is True

    def test_nonexistent_sales_manager_validation(self):
        """Test validation for non-existent sales manager."""
        with pytest.raises(ValueError, match="Sales manager not found"):
            InquiryServices.create_inquiry(
                client="Test Client",
                text="Test inquiry",
                sales_manager_id=99999,  # Non-existent ID
            )

    def test_create_inquiry_with_comment(self, manager_user):
        """Test creating inquiry with comment field."""
        inquiry = InquiryServices.create_inquiry(
            client="Comment Client",
            text="Comment inquiry",
            comment="Initial comment",
            sales_manager_id=manager_user.id,
        )

        assert inquiry.comment == "Initial comment"

    def test_update_inquiry_all_fields(self, manager_user):
        """Test updating all inquiry fields."""
        inquiry = Inquiry.objects.create(
            client="Original Client",
            text="Original text",
            status="pending",
            sales_manager=manager_user,
            is_new_customer=False,
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry,
            client="Updated Client",
            text="Updated text",
            status="quoted",
            comment="Updated comment",
            is_new_customer=True,
        )

        assert updated_inquiry.client == "Updated Client"
        assert updated_inquiry.text == "Updated text"
        assert updated_inquiry.status == "quoted"
        assert updated_inquiry.comment == "Updated comment"
        assert updated_inquiry.is_new_customer is True

    def test_delete_inquiry_with_failed_status(self, manager_user):
        """Test deleting inquiry with failed status."""
        inquiry = Inquiry.objects.create(
            client="Failed Client",
            text="Failed inquiry",
            status="failed",
            sales_manager=manager_user,
        )

        # Should be able to delete failed inquiries
        InquiryServices.delete_inquiry(inquiry=inquiry)
        assert not Inquiry.objects.filter(id=inquiry.id).exists()

    def test_inquiry_update_with_same_sales_manager(self, manager_user):
        """Test updating inquiry with same sales manager."""
        inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            sales_manager=manager_user,
        )

        updated_inquiry = InquiryServices.update_inquiry(
            inquiry=inquiry,
            sales_manager_id=manager_user.id,  # Same manager
        )

        assert updated_inquiry.sales_manager == manager_user
