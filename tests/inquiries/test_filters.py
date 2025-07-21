"""
Tests for inquiry filters focusing on filtering logic.
"""

import pytest
from django.db.models import QuerySet

from apps.accounts.models import CustomUser
from apps.inquiries.filters import InquiryFilter
from apps.inquiries.models import Inquiry


@pytest.mark.django_db
class TestInquiryFilter:
    """Test cases for InquiryFilter filtering logic."""

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
    def sample_inquiries(self, manager_user, admin_user):
        """Create sample inquiries for testing."""
        return [
            Inquiry.objects.create(
                client="ABC Company",
                text="Need logistics service for containers",
                comment="Urgent request",
                status="pending",
                sales_manager=manager_user,
                is_new_customer=True,
            ),
            Inquiry.objects.create(
                client="XYZ Corporation",
                text="Railway transport inquiry",
                comment="Regular customer",
                status="quoted",
                sales_manager=admin_user,
                is_new_customer=False,
            ),
            Inquiry.objects.create(
                client="DEF Industries",
                text="Bulk cargo transportation",
                comment="Special requirements",
                status="success",
                sales_manager=manager_user,
                is_new_customer=True,
            ),
            Inquiry.objects.create(
                client="GHI Logistics",
                text="Express delivery needed",
                comment="Time sensitive",
                status="failed",
                sales_manager=admin_user,
                is_new_customer=False,
            ),
        ]

    def test_filter_no_filters_returns_all(self, sample_inquiries):
        """Test that no filters returns all inquiries."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({}, queryset=queryset)

        assert len(filter_obj.qs) == 4
        for inquiry in sample_inquiries:
            assert inquiry in filter_obj.qs

    def test_filter_by_client_exact_match(self, sample_inquiries):
        """Test filtering by client with exact match."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"client": "ABC Company"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().client == "ABC Company"

    def test_filter_by_client_partial_match(self, sample_inquiries):
        """Test filtering by client with partial match (icontains)."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"client": "Company"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().client == "ABC Company"

    def test_filter_by_client_case_insensitive(self, sample_inquiries):
        """Test filtering by client is case insensitive."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"client": "abc company"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().client == "ABC Company"

    def test_filter_by_text_partial_match(self, sample_inquiries):
        """Test filtering by text with partial match."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"text": "transport"}, queryset=queryset)

        assert len(filter_obj.qs) == 2
        clients = [inquiry.client for inquiry in filter_obj.qs]
        assert "XYZ Corporation" in clients
        assert "DEF Industries" in clients

    def test_filter_by_comment_partial_match(self, sample_inquiries):
        """Test filtering by comment with partial match."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"comment": "customer"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().client == "XYZ Corporation"

    def test_filter_by_status_exact_match(self, sample_inquiries):
        """Test filtering by status with exact match."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"status": ["pending"]}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().status == "pending"

    def test_filter_by_status_multiple_results(self, sample_inquiries):
        """Test filtering by status that returns multiple results."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"status": ["quoted"]}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().status == "quoted"

    def test_filter_by_is_new_customer_true(self, sample_inquiries):
        """Test filtering by is_new_customer=True."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"is_new_customer": True}, queryset=queryset)

        assert len(filter_obj.qs) == 2
        for inquiry in filter_obj.qs:
            assert inquiry.is_new_customer is True

    def test_filter_by_is_new_customer_false(self, sample_inquiries):
        """Test filtering by is_new_customer=False."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"is_new_customer": False}, queryset=queryset)

        assert len(filter_obj.qs) == 2
        for inquiry in filter_obj.qs:
            assert inquiry.is_new_customer is False

    def test_filter_by_sales_manager_id(self, sample_inquiries, manager_user):
        """Test filtering by sales_manager_id."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter(
            {"sales_manager_id": manager_user.id}, queryset=queryset
        )

        assert len(filter_obj.qs) == 2
        for inquiry in filter_obj.qs:
            assert inquiry.sales_manager == manager_user

    def test_filter_by_id(self, sample_inquiries):
        """Test filtering by inquiry ID."""
        target_inquiry = sample_inquiries[0]
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"id": target_inquiry.id}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first() == target_inquiry

    def test_search_filter_client_match(self, sample_inquiries):
        """Test search filter finding match in client field."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "ABC"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().client == "ABC Company"

    def test_search_filter_text_match(self, sample_inquiries):
        """Test search filter finding match in text field."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "logistics"}, queryset=queryset)

        assert len(filter_obj.qs) == 2
        clients = [inquiry.client for inquiry in filter_obj.qs]
        assert "ABC Company" in clients
        assert "GHI Logistics" in clients

    def test_search_filter_comment_match(self, sample_inquiries):
        """Test search filter finding match in comment field."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "urgent"}, queryset=queryset)

        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().comment == "Urgent request"

    def test_search_filter_multiple_field_matches(self, sample_inquiries):
        """Test search filter finding matches across multiple fields."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "express"}, queryset=queryset)

        # Should find "Express delivery needed" in text field
        assert len(filter_obj.qs) == 1
        assert filter_obj.qs.first().text == "Express delivery needed"

    def test_search_filter_case_insensitive(self, sample_inquiries):
        """Test search filter is case insensitive."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "LOGISTICS"}, queryset=queryset)

        assert len(filter_obj.qs) == 2

    def test_search_filter_empty_value(self, sample_inquiries):
        """Test search filter with empty value returns all."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": ""}, queryset=queryset)

        assert len(filter_obj.qs) == 4

    def test_search_filter_no_matches(self, sample_inquiries):
        """Test search filter with no matches returns empty."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"search": "nonexistent"}, queryset=queryset)

        assert len(filter_obj.qs) == 0

    def test_multiple_filters_combined(self, sample_inquiries, manager_user):
        """Test combining multiple filters."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter(
            {
                "status": ["pending"],
                "is_new_customer": True,
                "sales_manager_id": manager_user.id,
            },
            queryset=queryset,
        )

        assert len(filter_obj.qs) == 1
        inquiry = filter_obj.qs.first()
        assert inquiry.status == "pending"
        assert inquiry.is_new_customer is True
        assert inquiry.sales_manager == manager_user

    def test_filters_with_search_combined(self, sample_inquiries, manager_user):
        """Test combining regular filters with search."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter(
            {"search": "transport", "sales_manager_id": manager_user.id},
            queryset=queryset,
        )

        assert len(filter_obj.qs) == 1
        inquiry = filter_obj.qs.first()
        assert "transport" in inquiry.text.lower()
        assert inquiry.sales_manager == manager_user

    def test_filter_returns_queryset(self, sample_inquiries):
        """Test that filter returns a QuerySet instance."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({}, queryset=queryset)

        assert isinstance(filter_obj.qs, QuerySet)

    def test_filter_meta_fields_definition(self):
        """Test that filter Meta fields are properly defined."""
        expected_fields = [
            "id",
            "client",
            "text",
            "comment",
            "status",
            "is_new_customer",
            "sales_manager",
            "search",
        ]

        assert InquiryFilter.Meta.fields == expected_fields
        assert InquiryFilter.Meta.model == Inquiry

    def test_filter_choice_field_valid_choices(self, sample_inquiries):
        """Test that status filter uses valid choices."""
        queryset = Inquiry.objects.all()

        # Test all valid status choices
        for status_choice, _ in Inquiry.STATUS_CHOICES:
            filter_obj = InquiryFilter({"status": status_choice}, queryset=queryset)
            # Should not raise any errors
            list(filter_obj.qs)  # Evaluate queryset

    def test_filter_invalid_sales_manager_id(self, sample_inquiries):
        """Test filtering with invalid sales_manager_id."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter({"sales_manager_id": 99999}, queryset=queryset)

        assert len(filter_obj.qs) == 0

    def test_filter_with_none_values(self, sample_inquiries):
        """Test filters with None values."""
        queryset = Inquiry.objects.all()
        filter_obj = InquiryFilter(
            {"client": None, "status": None, "search": None}, queryset=queryset
        )

        # Should return all inquiries (None values should be ignored)
        assert len(filter_obj.qs) == 4
