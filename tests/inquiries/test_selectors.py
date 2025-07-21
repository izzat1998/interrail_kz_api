"""
Tests for inquiry selectors focusing on data retrieval logic.
"""

import pytest
from django.db.models import QuerySet

from apps.accounts.models import CustomUser
from apps.inquiries.models import Inquiry
from apps.inquiries.selectors import InquirySelectors


@pytest.mark.django_db
class TestInquirySelectors:
    """Test cases for InquirySelectors data retrieval logic."""

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
    def sample_inquiry(self, manager_user):
        """Create a sample inquiry for testing."""
        return Inquiry.objects.create(
            client="Test Client",
            text="Test inquiry text",
            comment="Test comment",
            status="pending",
            sales_manager=manager_user,
            is_new_customer=True,
        )

    def test_get_inquiry_by_id_success(self, sample_inquiry, manager_user):
        """Test successful inquiry retrieval by ID."""
        result = InquirySelectors.get_inquiry_by_id(inquiry_id=sample_inquiry.id)

        assert isinstance(result, dict)
        assert result["id"] == sample_inquiry.id
        assert result["client"] == "Test Client"
        assert result["text"] == "Test inquiry text"
        assert result["comment"] == "Test comment"
        assert result["status"] == "pending"
        assert result["status_display"] == sample_inquiry.get_status_display()
        assert result["is_new_customer"] is True
        assert result["created_at"] == sample_inquiry.created_at
        assert result["updated_at"] == sample_inquiry.updated_at

    def test_get_inquiry_by_id_with_sales_manager(self, sample_inquiry, manager_user):
        """Test inquiry retrieval with sales manager data."""
        result = InquirySelectors.get_inquiry_by_id(inquiry_id=sample_inquiry.id)

        assert result["sales_manager"] is not None
        assert result["sales_manager"]["id"] == manager_user.id
        assert result["sales_manager"]["username"] == manager_user.username
        assert result["sales_manager"]["email"] == manager_user.email

    def test_get_inquiry_by_id_without_sales_manager(self):
        """Test inquiry retrieval without sales manager."""
        inquiry = Inquiry.objects.create(
            client="Test Client", text="Test inquiry text", sales_manager=None
        )

        result = InquirySelectors.get_inquiry_by_id(inquiry_id=inquiry.id)

        assert result["sales_manager"] is None

    def test_get_inquiry_by_id_not_found(self):
        """Test inquiry retrieval with non-existent ID."""
        with pytest.raises(Inquiry.DoesNotExist):
            InquirySelectors.get_inquiry_by_id(inquiry_id=99999)

    def test_get_sales_manager_by_id_success(self, manager_user):
        """Test successful sales manager retrieval by ID."""
        result = InquirySelectors.get_sales_manager_by_id(manager_id=manager_user.id)

        assert result == manager_user
        assert result.user_type == "manager"

    def test_get_sales_manager_by_id_not_found(self):
        """Test sales manager retrieval with non-existent ID."""
        with pytest.raises(CustomUser.DoesNotExist):
            InquirySelectors.get_sales_manager_by_id(manager_id=99999)

    def test_get_inquiries_list_no_filters(self, sample_inquiry):
        """Test getting inquiries list without filters."""
        result = InquirySelectors.get_inquiries_list()

        assert isinstance(result, QuerySet)
        assert sample_inquiry in result

    def test_get_inquiries_list_with_empty_filters(self, sample_inquiry):
        """Test getting inquiries list with empty filters."""
        result = InquirySelectors.get_inquiries_list(filters={})

        assert isinstance(result, QuerySet)
        assert sample_inquiry in result

    def test_get_inquiries_list_with_status_filter(self, manager_user):
        """Test getting inquiries list filtered by status."""
        pending_inquiry = Inquiry.objects.create(
            client="Pending Client",
            text="Pending text",
            status="pending",
            sales_manager=manager_user,
        )
        quoted_inquiry = Inquiry.objects.create(
            client="Quoted Client",
            text="Quoted text",
            status="quoted",
            sales_manager=manager_user,
        )

        result = InquirySelectors.get_inquiries_list(filters={"status": ["pending"]})

        assert pending_inquiry in result
        assert quoted_inquiry not in result

    def test_get_inquiries_list_with_search_filter(self, manager_user):
        """Test getting inquiries list with search filter."""
        searchable_inquiry = Inquiry.objects.create(
            client="Searchable Client",
            text="This contains searchable text",
            sales_manager=manager_user,
        )
        other_inquiry = Inquiry.objects.create(
            client="Other Client", text="Different content", sales_manager=manager_user
        )

        result = InquirySelectors.get_inquiries_list(filters={"search": "searchable"})

        assert searchable_inquiry in result
        assert other_inquiry not in result

    def test_get_inquiries_list_with_is_new_customer_filter(self, manager_user):
        """Test getting inquiries list filtered by is_new_customer."""
        new_customer_inquiry = Inquiry.objects.create(
            client="New Customer",
            text="New customer inquiry",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        existing_customer_inquiry = Inquiry.objects.create(
            client="Existing Customer",
            text="Existing customer inquiry",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        result = InquirySelectors.get_inquiries_list(filters={"is_new_customer": True})

        assert new_customer_inquiry in result
        assert existing_customer_inquiry not in result

    def test_get_inquiries_list_with_sales_manager_filter(
        self, manager_user, admin_user
    ):
        """Test getting inquiries list filtered by sales manager."""
        manager_inquiry = Inquiry.objects.create(
            client="Manager Client", text="Manager inquiry", sales_manager=manager_user
        )
        admin_inquiry = Inquiry.objects.create(
            client="Admin Client", text="Admin inquiry", sales_manager=admin_user
        )

        result = InquirySelectors.get_inquiries_list(
            filters={"sales_manager_id": manager_user.id}
        )

        assert manager_inquiry in result
        assert admin_inquiry not in result

    def test_get_inquiries_list_uses_select_related(self):
        """Test that get_inquiries_list uses select_related for optimization."""
        result = InquirySelectors.get_inquiries_list()

        # Check that the queryset has select_related applied
        assert "sales_manager" in str(result.query)

    def test_get_inquiries_stats_empty_database(self):
        """Test getting statistics with no inquiries."""
        stats = InquirySelectors.get_inquiries_stats()

        assert stats["total_inquiries"] == 0
        assert stats["pending_count"] == 0
        assert stats["quoted_count"] == 0
        assert stats["success_count"] == 0
        assert stats["failed_count"] == 0
        assert stats["new_customers_count"] == 0
        assert stats["conversion_rate"] == 0

    def test_get_inquiries_stats_with_data(self, manager_user):
        """Test getting statistics with various inquiry data."""
        # Create inquiries with different statuses
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
            status="pending",
            is_new_customer=False,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Client 3",
            text="Text 3",
            status="quoted",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Client 4",
            text="Text 4",
            status="success",
            is_new_customer=False,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Client 5",
            text="Text 5",
            status="success",
            is_new_customer=True,
            sales_manager=manager_user,
        )
        Inquiry.objects.create(
            client="Client 6",
            text="Text 6",
            status="failed",
            is_new_customer=False,
            sales_manager=manager_user,
        )

        stats = InquirySelectors.get_inquiries_stats()

        assert stats["total_inquiries"] == 6
        assert stats["pending_count"] == 2
        assert stats["quoted_count"] == 1
        assert stats["success_count"] == 2
        assert stats["failed_count"] == 1
        assert stats["new_customers_count"] == 3
        # Conversion rate: 2 success / 6 total * 100 = 33.33...
        assert abs(stats["conversion_rate"] - 33.333333333333336) < 0.001

    def test_get_inquiries_stats_conversion_rate_calculation(self, manager_user):
        """Test conversion rate calculation with different scenarios."""
        # Create 3 success out of 10 total
        for i in range(7):
            Inquiry.objects.create(
                client=f"Client {i}",
                text=f"Text {i}",
                status="pending",
                sales_manager=manager_user,
            )
        for i in range(3):
            Inquiry.objects.create(
                client=f"Success Client {i}",
                text=f"Success Text {i}",
                status="success",
                sales_manager=manager_user,
            )

        stats = InquirySelectors.get_inquiries_stats()

        assert stats["total_inquiries"] == 10
        assert stats["success_count"] == 3
        assert stats["conversion_rate"] == 30.0

    def test_get_inquiries_stats_uses_single_query(self):
        """Test that stats method uses efficient single query."""
        # This is more of a structural test
        import inspect

        source = inspect.getsource(InquirySelectors.get_inquiries_stats)

        # Should contain aggregate method call
        assert "aggregate" in source
        # Should use Count and Case/When for conditional counting
        assert "Count" in source
        assert "Case" in source
        assert "When" in source

    def test_get_inquiries_stats_all_status_types(self, manager_user):
        """Test stats with all possible status types."""
        status_choices = ["pending", "quoted", "success", "failed"]

        for status in status_choices:
            Inquiry.objects.create(
                client=f"{status.title()} Client",
                text=f"{status.title()} Text",
                status=status,
                sales_manager=manager_user,
            )

        stats = InquirySelectors.get_inquiries_stats()

        assert stats["total_inquiries"] == 4
        assert stats["pending_count"] == 1
        assert stats["quoted_count"] == 1
        assert stats["success_count"] == 1
        assert stats["failed_count"] == 1
        assert stats["conversion_rate"] == 25.0  # 1 success / 4 total

    def test_get_inquiries_stats_zero_division_protection(self):
        """Test that stats method handles zero division gracefully."""
        # No inquiries in database
        stats = InquirySelectors.get_inquiries_stats()

        # Should not raise ZeroDivisionError
        assert stats["conversion_rate"] == 0
