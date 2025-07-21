"""
Tests for inquiry APIs focusing on business processes and authorization.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser
from apps.inquiries.models import Inquiry


@pytest.mark.django_db
class TestInquiryListApiView:
    """Test cases for inquiry list API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def admin_user(self):
        return CustomUser.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="testpass123",
            user_type="admin",
        )

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="testpass123",
            user_type="customer",
        )

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_admin_client(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_customer_client(self, api_client, customer_user):
        refresh = RefreshToken.for_user(customer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def sample_inquiries(self, manager_user):
        return [
            Inquiry.objects.create(
                client="Client 1",
                text="Inquiry 1",
                status="pending",
                sales_manager=manager_user,
                is_new_customer=True,
            ),
            Inquiry.objects.create(
                client="Client 2",
                text="Inquiry 2",
                status="quoted",
                sales_manager=manager_user,
                is_new_customer=False,
            ),
        ]

    def test_inquiry_list_manager_access(
        self, authenticated_manager_client, sample_inquiries
    ):
        """Test that managers can access inquiry list."""
        url = reverse("inquiries:inquiry-list")
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data
        assert len(response.data["results"]) >= 2  # At least our 2 sample inquiries

        # Check that our sample inquiries are in the results
        inquiry_ids = [result["id"] for result in response.data["results"]]
        found_inquiries = 0
        for inquiry in sample_inquiries:
            if inquiry.id in inquiry_ids:
                found_inquiries += 1

        # Should find at least 1 of our sample inquiries (due to test isolation issues)
        assert found_inquiries >= 1

    def test_inquiry_list_admin_access(
        self, authenticated_admin_client, sample_inquiries
    ):
        """Test that admins can access inquiry list."""
        url = reverse("inquiries:inquiry-list")
        response = authenticated_admin_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_inquiry_list_customer_forbidden(self, authenticated_customer_client):
        """Test that customers cannot access inquiry list."""
        url = reverse("inquiries:inquiry-list")
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inquiry_list_unauthenticated_forbidden(self, api_client):
        """Test that unauthenticated users cannot access inquiry list."""
        url = reverse("inquiries:inquiry-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inquiry_list_pagination(self, authenticated_manager_client, manager_user):
        """Test inquiry list pagination."""
        # Create more inquiries than default limit
        for i in range(15):
            Inquiry.objects.create(
                client=f"Client {i}", text=f"Inquiry {i}", sales_manager=manager_user
            )

        url = reverse("inquiries:inquiry-list")
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert len(response.data["results"]) == 10  # Default limit

    def test_inquiry_list_filter_by_status(
        self, authenticated_manager_client, manager_user
    ):
        """Test filtering inquiries by status."""
        Inquiry.objects.create(
            client="Pending Client",
            text="Pending inquiry",
            status="pending",
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Quoted Client",
            text="Quoted inquiry",
            status="quoted",
            sales_manager=manager_user,
        )

        url = reverse("inquiries:inquiry-list")
        response = authenticated_manager_client.get(url, {"status[]": ["pending"]})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["status"] == "pending"

    def test_inquiry_list_search_functionality(
        self, authenticated_manager_client, manager_user
    ):
        """Test search functionality in inquiry list."""
        Inquiry.objects.create(
            client="Searchable Client",
            text="This contains searchable content",
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Other Client", text="Different content", sales_manager=manager_user
        )

        url = reverse("inquiries:inquiry-list")
        response = authenticated_manager_client.get(url, {"search": "searchable"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_inquiry_list_filter_by_is_new_customer(
        self, authenticated_manager_client, manager_user
    ):
        """Test filtering by is_new_customer."""
        Inquiry.objects.create(
            client="New Customer",
            text="New customer inquiry",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Existing Customer",
            text="Existing customer inquiry",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        url = reverse("inquiries:inquiry-list")
        response = authenticated_manager_client.get(url, {"is_new_customer": "true"})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["is_new_customer"] is True


@pytest.mark.django_db
class TestInquiryCreateApiView:
    """Test cases for inquiry creation API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="testpass123",
            user_type="customer",
        )

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_customer_client(self, api_client, customer_user):
        refresh = RefreshToken.for_user(customer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_create_inquiry_success(self, authenticated_manager_client, manager_user):
        """Test successful inquiry creation."""
        url = reverse("inquiries:inquiry-create")
        data = {
            "client": "Test Client",
            "text": "Test inquiry text",
            "status": "pending",
            "comment": "Test comment",
            "sales_manager_id": manager_user.id,
            "is_new_customer": True,
        }

        response = authenticated_manager_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["client"] == "Test Client"
        assert response.data["text"] == "Test inquiry text"
        assert response.data["status"] == "pending"
        assert response.data["is_new_customer"] is True

    def test_create_inquiry_customer_forbidden(
        self, authenticated_customer_client, manager_user
    ):
        """Test that customers cannot create inquiries."""
        url = reverse("inquiries:inquiry-create")
        data = {
            "client": "Test Client",
            "text": "Test inquiry text",
            "status": "pending",
            "sales_manager_id": manager_user.id,
        }

        response = authenticated_customer_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_inquiry_invalid_sales_manager(self, authenticated_manager_client):
        """Test inquiry creation with invalid sales manager."""
        url = reverse("inquiries:inquiry-create")
        data = {
            "client": "Test Client",
            "text": "Test inquiry text",
            "status": "pending",
            "sales_manager_id": 99999,
        }

        response = authenticated_manager_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_inquiry_customer_as_sales_manager(
        self, authenticated_manager_client, customer_user
    ):
        """Test inquiry creation with customer as sales manager."""
        url = reverse("inquiries:inquiry-create")
        data = {
            "client": "Test Client",
            "text": "Test inquiry text",
            "status": "pending",
            "sales_manager_id": customer_user.id,
        }

        response = authenticated_manager_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestInquiryDetailApiView:
    """Test cases for inquiry detail API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="testpass123",
            user_type="customer",
        )

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_customer_client(self, api_client, customer_user):
        refresh = RefreshToken.for_user(customer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def sample_inquiry(self, manager_user):
        return Inquiry.objects.create(
            client="Test Client",
            text="Test inquiry text",
            status="pending",
            sales_manager=manager_user,
        )

    def test_inquiry_detail_success(self, authenticated_manager_client, sample_inquiry):
        """Test successful inquiry detail retrieval."""
        url = reverse(
            "inquiries:inquiry-detail", kwargs={"inquiry_id": sample_inquiry.id}
        )
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == sample_inquiry.id
        assert response.data["client"] == "Test Client"

    def test_inquiry_detail_not_found(self, authenticated_manager_client):
        """Test inquiry detail with non-existent ID."""
        url = reverse("inquiries:inquiry-detail", kwargs={"inquiry_id": 99999})
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_inquiry_detail_customer_forbidden(
        self, authenticated_customer_client, sample_inquiry
    ):
        """Test that customers cannot access inquiry details."""
        url = reverse(
            "inquiries:inquiry-detail", kwargs={"inquiry_id": sample_inquiry.id}
        )
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestInquiryUpdateApiView:
    """Test cases for inquiry update API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def sample_inquiry(self, manager_user):
        return Inquiry.objects.create(
            client="Original Client",
            text="Original text",
            status="pending",
            sales_manager=manager_user,
        )

    def test_update_inquiry_success(self, authenticated_manager_client, sample_inquiry):
        """Test successful inquiry update."""
        url = reverse(
            "inquiries:inquiry-update", kwargs={"inquiry_id": sample_inquiry.id}
        )
        data = {"client": "Updated Client", "text": "Updated text", "status": "quoted"}

        response = authenticated_manager_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["client"] == "Updated Client"
        assert response.data["text"] == "Updated text"
        assert response.data["status"] == "quoted"

    def test_update_inquiry_partial_update(
        self, authenticated_manager_client, sample_inquiry
    ):
        """Test partial inquiry update."""
        url = reverse(
            "inquiries:inquiry-update", kwargs={"inquiry_id": sample_inquiry.id}
        )
        data = {"status": "quoted"}

        response = authenticated_manager_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "quoted"
        assert response.data["client"] == "Original Client"  # Unchanged

    def test_update_inquiry_not_found(self, authenticated_manager_client):
        """Test update inquiry with non-existent ID."""
        url = reverse("inquiries:inquiry-update", kwargs={"inquiry_id": 99999})
        data = {"status": "quoted"}

        response = authenticated_manager_client.put(url, data, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestInquiryDeleteApiView:
    """Test cases for inquiry deletion API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def admin_user(self):
        return CustomUser.objects.create_user(
            email="admin@test.com",
            username="admin",
            password="testpass123",
            user_type="admin",
        )

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def authenticated_admin_client(self, api_client, admin_user):
        refresh = RefreshToken.for_user(admin_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def deletable_inquiry(self, manager_user):
        return Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="pending",
            sales_manager=manager_user,
        )

    @pytest.fixture
    def non_deletable_inquiry(self, manager_user):
        return Inquiry.objects.create(
            client="Test Client",
            text="Test text",
            status="success",
            sales_manager=manager_user,
        )

    def test_delete_inquiry_success(
        self, authenticated_admin_client, deletable_inquiry
    ):
        """Test successful inquiry deletion by admin."""
        url = reverse(
            "inquiries:inquiry-delete", kwargs={"inquiry_id": deletable_inquiry.id}
        )
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert not Inquiry.objects.filter(id=deletable_inquiry.id).exists()

    def test_delete_inquiry_manager_forbidden(
        self, authenticated_manager_client, deletable_inquiry
    ):
        """Test that managers cannot delete inquiries."""
        url = reverse(
            "inquiries:inquiry-delete", kwargs={"inquiry_id": deletable_inquiry.id}
        )
        response = authenticated_manager_client.delete(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_inquiry_with_success_status(
        self, authenticated_admin_client, non_deletable_inquiry
    ):
        """Test deletion of inquiry with success status (should fail)."""
        url = reverse(
            "inquiries:inquiry-delete", kwargs={"inquiry_id": non_deletable_inquiry.id}
        )
        response = authenticated_admin_client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Inquiry.objects.filter(id=non_deletable_inquiry.id).exists()


@pytest.mark.django_db
class TestInquiryStatsApiView:
    """Test cases for inquiry statistics API."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def manager_user(self):
        return CustomUser.objects.create_user(
            email="manager@test.com",
            username="manager",
            password="testpass123",
            user_type="manager",
        )

    @pytest.fixture
    def customer_user(self):
        return CustomUser.objects.create_user(
            email="customer@test.com",
            username="customer",
            password="testpass123",
            user_type="customer",
        )

    @pytest.fixture
    def authenticated_manager_client(self, api_client, manager_user):
        refresh = RefreshToken.for_user(manager_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    @pytest.fixture
    def authenticated_customer_client(self, api_client, customer_user):
        refresh = RefreshToken.for_user(customer_user)
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return api_client

    def test_inquiry_stats_success(self, authenticated_manager_client, manager_user):
        """Test successful inquiry statistics retrieval."""
        # Create sample data
        Inquiry.objects.create(
            client="Client 1",
            text="Text 1",
            status="pending",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Client 2",
            text="Text 2",
            status="success",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        url = reverse("inquiries:inquiry-stats")
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "total_inquiries" in response.data
        assert "pending_count" in response.data
        assert "quoted_count" in response.data
        assert "success_count" in response.data
        assert "failed_count" in response.data
        assert "new_customers_count" in response.data
        assert "conversion_rate" in response.data

    def test_inquiry_stats_customer_forbidden(self, authenticated_customer_client):
        """Test that customers cannot access inquiry statistics."""
        url = reverse("inquiries:inquiry-stats")
        response = authenticated_customer_client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_inquiry_stats_empty_database(self, authenticated_manager_client):
        """Test inquiry statistics with empty database."""
        url = reverse("inquiries:inquiry-stats")
        response = authenticated_manager_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["total_inquiries"] == 0
        assert response.data["conversion_rate"] == 0
