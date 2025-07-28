"""
End-to-end business flow tests for user journeys.
Focus on complete user workflows rather than individual components.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser


@pytest.mark.django_db
class TestCustomerJourney:
    """Test complete customer user journey workflows."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_customer_registration_and_login_flow(self, api_client):
        """Test: Customer registers → logs in → accesses profile."""
        # Register new customer
        register_url = reverse("authentication:register")
        register_data = {
            "username": "newcustomer",
            "email": "customer@example.com",
            "password": "securepass123",
            "user_type": "customer",
        }

        register_response = api_client.post(register_url, register_data)
        assert register_response.status_code == status.HTTP_201_CREATED
        assert register_response.data["success"] is True

        # Login with new credentials
        login_url = reverse("authentication:login")
        login_data = {"username": "newcustomer", "password": "securepass123"}

        login_response = api_client.post(login_url, login_data)
        assert login_response.status_code == status.HTTP_200_OK
        assert login_response.data["success"] is True

        # Access profile with tokens
        profile_url = reverse("authentication:profile")
        access_token = register_response.data["data"]["access_token"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        profile_response = api_client.get(profile_url)
        assert profile_response.status_code == status.HTTP_200_OK
        assert profile_response.data["data"]["profile"]["user_type"] == "customer"

    def test_customer_cannot_access_manager_features(self, api_client):
        """Test: Customer user cannot access manager-only features."""
        # Create and authenticate customer
        customer = CustomUser.objects.create_user(
            username="customer",
            email="customer@example.com",
            password="testpass123",
            user_type="customer",
        )

        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(customer)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        # Try to access inquiry list (manager only)
        inquiry_list_url = reverse("inquiries:inquiry-list")
        response = api_client.get(inquiry_list_url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # # Try to create inquiry (manager only)
        # inquiry_create_url = reverse("inquiries:inquiry-create")
        # response = api_client.post(inquiry_create_url, {"client": "Test"})
        # assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestManagerJourney:
    """Test complete manager user journey workflows."""

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
    def authenticated_manager_client(self, api_client, manager_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_manager_inquiry_workflow(self, authenticated_manager_client, manager_user):
        """Test: Manager creates inquiry → updates status → tracks to completion."""
        # Create inquiry
        create_url = reverse("inquiries:inquiry-create")
        create_data = {
            "client": "Business Client",
            "text": "Need travel package for 10 people",
            "sales_manager_id": manager_user.id,
            "is_new_customer": True,
            "status": "pending",
        }

        create_response = authenticated_manager_client.post(
            create_url, create_data, format="json"
        )
        assert create_response.status_code == status.HTTP_201_CREATED
        inquiry_id = create_response.data["id"]

        # Update inquiry status to quoted
        update_url = reverse(
            "inquiries:inquiry-update", kwargs={"inquiry_id": inquiry_id}
        )
        update_data = {"status": "quoted", "comment": "Quote sent to client"}

        update_response = authenticated_manager_client.put(
            update_url, update_data, format="json"
        )
        assert update_response.status_code == status.HTTP_200_OK
        assert update_response.data["status"] == "quoted"

        # Final update to success
        final_data = {"status": "success", "comment": "Client accepted quote"}
        final_response = authenticated_manager_client.put(
            update_url, final_data, format="json"
        )
        assert final_response.status_code == status.HTTP_200_OK
        assert final_response.data["status"] == "success"

    def test_manager_can_access_all_inquiries(
        self, authenticated_manager_client, manager_user
    ):
        """Test: Manager can view and manage all inquiries."""
        # Create test inquiry
        from apps.inquiries.models import Inquiry

        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test inquiry", sales_manager=manager_user
        )

        # Access inquiry list
        list_url = reverse("inquiries:inquiry-list")
        list_response = authenticated_manager_client.get(list_url)
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data["results"]) >= 1

        # Access specific inquiry
        detail_url = reverse(
            "inquiries:inquiry-detail", kwargs={"inquiry_id": inquiry.id}
        )
        detail_response = authenticated_manager_client.get(detail_url)
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data["id"] == inquiry.id

        # Access statistics
        stats_url = reverse("inquiries:inquiry-stats")
        stats_response = authenticated_manager_client.get(stats_url)
        assert stats_response.status_code == status.HTTP_200_OK
        assert "total_inquiries" in stats_response.data


@pytest.mark.django_db
class TestAdminJourney:
    """Test admin-specific business workflows."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        return CustomUser.objects.create_user(
            username="admin",
            email="admin@example.com",
            password="testpass123",
            user_type="admin",
        )

    @pytest.fixture
    def authenticated_admin_client(self, api_client, admin_user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_admin_can_delete_inquiries(self, authenticated_admin_client, admin_user):
        """Test: Admin can delete appropriate inquiries."""
        from apps.inquiries.models import Inquiry

        # Create deletable inquiry (pending status)
        deletable_inquiry = Inquiry.objects.create(
            client="Test Client",
            text="Test inquiry",
            status="pending",
            sales_manager=admin_user,
        )

        # Admin can delete pending inquiry
        delete_url = reverse(
            "inquiries:inquiry-delete", kwargs={"inquiry_id": deletable_inquiry.id}
        )
        delete_response = authenticated_admin_client.delete(delete_url)
        assert delete_response.status_code == status.HTTP_200_OK

        # Verify inquiry is deleted
        assert not Inquiry.objects.filter(id=deletable_inquiry.id).exists()

    def test_admin_cannot_delete_successful_inquiries(
        self, authenticated_admin_client, admin_user
    ):
        """Test: Admin cannot delete inquiries with success status."""
        from apps.inquiries.models import Inquiry

        # Create non-deletable inquiry (success status)
        success_inquiry = Inquiry.objects.create(
            client="Successful Client",
            text="Successful inquiry",
            status="success",
            sales_manager=admin_user,
        )

        # Admin cannot delete success inquiry
        delete_url = reverse(
            "inquiries:inquiry-delete", kwargs={"inquiry_id": success_inquiry.id}
        )
        delete_response = authenticated_admin_client.delete(delete_url)
        assert delete_response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify inquiry still exists
        assert Inquiry.objects.filter(id=success_inquiry.id).exists()
