from typing import Any

from django.db.models import QuerySet

from apps.accounts.models import CustomUser

from .filters import InquiryFilter
from .models import Inquiry


class InquirySelectors:
    """
    Selectors for inquiry-related data retrieval
    """

    @staticmethod
    def get_inquiry_instance_by_id(*, inquiry_id: int) -> Inquiry:
        """
        Get inquiry model instance by ID
        """
        return Inquiry.objects.select_related("sales_manager").get(id=inquiry_id)

    @staticmethod
    def get_inquiry_by_id(*, inquiry_id: int) -> dict[str, Any]:
        """
        Get inquiry by ID with error handling and formatting
        """
        inquiry = Inquiry.objects.select_related("sales_manager").get(id=inquiry_id)

        # Format the data similar to accounts app pattern
        return {
            "id": inquiry.id,
            "client": inquiry.client,
            "text": inquiry.text,
            "attachment_url": inquiry.attachment.url if inquiry.attachment else None,
            "attachment_name": inquiry.attachment.name.split('/')[-1] if inquiry.attachment else None,
            "has_attachment": bool(inquiry.attachment),
            "comment": inquiry.comment,
            "status": inquiry.status,
            "status_display": inquiry.get_status_display(),
            "sales_manager": (
                {
                    "id": inquiry.sales_manager.id,
                    "username": inquiry.sales_manager.username,
                    "email": inquiry.sales_manager.email,
                }
                if inquiry.sales_manager
                else None
            ),
            "is_new_customer": inquiry.is_new_customer,
            "created_at": inquiry.created_at,
            "updated_at": inquiry.updated_at,
        }

    @staticmethod
    def get_sales_manager_by_id(*, manager_id: int) -> CustomUser:
        """
        Get sales manager by ID with error handling
        """
        return CustomUser.objects.get(id=manager_id)

    @staticmethod
    def get_inquiries_list(
        *, filters: dict[str, Any] | None = None
    ) -> QuerySet[Inquiry]:
        """
        Get filtered and paginated inquiries list
        """
        filters = filters or {}
        qs = Inquiry.objects.select_related("sales_manager").all()
        return InquiryFilter(filters, qs).qs

    @staticmethod
    def get_inquiries_stats() -> dict[str, Any]:
        """
        Get inquiry statistics using a single database query
        """
        from django.db.models import Case, Count, IntegerField, When

        stats = Inquiry.objects.aggregate(
            total_inquiries=Count("id"),
            pending_count=Count(
                Case(
                    When(status="pending", then=1),
                    output_field=IntegerField(),
                )
            ),
            quoted_count=Count(
                Case(
                    When(status="quoted", then=1),
                    output_field=IntegerField(),
                )
            ),
            success_count=Count(
                Case(
                    When(status="success", then=1),
                    output_field=IntegerField(),
                )
            ),
            failed_count=Count(
                Case(
                    When(status="failed", then=1),
                    output_field=IntegerField(),
                )
            ),
            new_customers_count=Count(
                Case(
                    When(is_new_customer=True, then=1),
                    output_field=IntegerField(),
                )
            ),
        )

        stats["conversion_rate"] = (
            stats["success_count"] / stats["total_inquiries"] * 100
            if stats["total_inquiries"] > 0
            else 0
        )

        return stats
