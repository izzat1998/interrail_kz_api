from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser

from .models import Inquiry
from .utils import (
    calculate_completion_grade,
    calculate_quote_grade,
    get_business_hours_between,
)


class InquiryServices:
    """
    Services for inquiry-related business logic
    """

    @staticmethod
    def create_inquiry(
        *,
        client: str,
        text: str = None,
        attachment = None,
        comment: str = "",
        sales_manager_id: int = None,
        is_new_customer: bool = False,
        status: str = "pending",
        **kwargs,
    ) -> Inquiry:
        """
        Create new inquiry with validation
        Requires at least text or attachment (or both)
        """
        # Validate that at least one content type is provided
        has_text = bool(text and text.strip())
        has_attachment = bool(attachment)

        if not has_text and not has_attachment:
            raise ValueError("Must provide either text or attachment (or both).")

        # Handle sales manager resolution
        sales_manager = None
        if sales_manager_id is not None:
            from .selectors import InquirySelectors

            try:
                sales_manager = InquirySelectors.get_sales_manager_by_id_or_telegram(
                    manager_id=sales_manager_id
                )
            except CustomUser.DoesNotExist:
                raise ValueError("Sales manager not found")

        # Business logic validation
        if sales_manager and sales_manager.user_type not in ["manager", "admin"]:
            raise ValueError("Sales manager must be a manager or admin user")

        with transaction.atomic():
            inquiry = Inquiry(
                client=client.strip(),
                text=text.strip() if text else None,
                attachment=attachment,
                comment=comment.strip(),
                sales_manager=sales_manager,
                is_new_customer=is_new_customer,
                status=status,
                **kwargs,
            )
            # Run validation before saving
            inquiry.full_clean()
            inquiry.save()

        return inquiry

    @staticmethod
    def update_inquiry(
        *,
        inquiry: Inquiry,
        client: str = None,
        text: str = None,
        attachment = ...,  # Use Ellipsis to distinguish between None and not provided
        status: str = None,
        comment: str = None,
        sales_manager_id: int = None,
        is_new_customer: bool = None,
        **kwargs,
    ) -> Inquiry:
        """
        Update inquiry with validation
        Supports text, attachment, or both
        """
        update_fields = []
        sales_manager = None

        # Handle content updates (text and/or attachment)
        content_updated = False
        if text is not None:
            inquiry.text = text.strip() if text else None
            update_fields.append("text")
            content_updated = True

        if attachment is not ...:  # Only update if attachment was explicitly provided
            # Delete old attachment if exists and we're updating it
            if inquiry.attachment:
                inquiry.attachment.delete(save=False)
            inquiry.attachment = attachment
            update_fields.append("attachment")
            content_updated = True

        # Validate that at least one content type remains after update
        if content_updated:
            has_text = bool(inquiry.text and inquiry.text.strip())
            has_attachment = bool(inquiry.attachment)

            if not has_text and not has_attachment:
                raise ValueError("Must provide either text or attachment (or both).")

        # Handle sales manager resolution
        if sales_manager_id is not None:
            from .selectors import InquirySelectors

            try:
                sales_manager = InquirySelectors.get_sales_manager_by_id_or_telegram(
                    manager_id=sales_manager_id
                )
            except CustomUser.DoesNotExist:
                raise ValueError("Sales manager not found")

        if client is not None:
            if not client.strip():
                raise ValueError("Client name cannot be empty")
            inquiry.client = client.strip()
            update_fields.append("client")

        if comment is not None:
            inquiry.comment = comment.strip()
            update_fields.append("comment")

        if sales_manager is not None:
            if sales_manager.user_type not in ["manager", "admin"]:
                raise ValueError("Sales manager must be a manager or admin user")
            inquiry.sales_manager = sales_manager
            update_fields.append("sales_manager")

        if status is not None:
            inquiry.status = status
            update_fields.append("status")

        if is_new_customer is not None:
            inquiry.is_new_customer = is_new_customer
            update_fields.append("is_new_customer")

        if update_fields:
            with transaction.atomic():
                # Run validation before saving
                inquiry.full_clean()
                inquiry.save(update_fields=update_fields)

        return inquiry

    @staticmethod
    def delete_inquiry(*, inquiry: Inquiry) -> None:
        """
        Delete inquiry with validation
        Also cleans up attached files
        """
        if inquiry.status in ["success", "quoted"]:
            raise ValueError("Cannot delete inquiry with success or quoted status")

        # Clean up attachment file if exists
        if inquiry.attachment:
            inquiry.attachment.delete(save=False)

        inquiry.delete()


class InquiryKPIServices:
    """
    KPI-specific services for inquiry management
    Handles automatic KPI calculation and status management
    """

    @staticmethod
    def quote_inquiry(*, inquiry: Inquiry, quoted_at: timezone.datetime = None) -> Inquiry:
        """
        Mark inquiry as quoted and calculate quote KPI metrics

        Args:
            inquiry: Inquiry instance to quote
            quoted_at: Custom quote timestamp (defaults to now)

        Returns:
            Updated inquiry with quote KPI data
        """
        if inquiry.is_locked:
            raise ValueError("Cannot update locked inquiry")

        if inquiry.status not in ["pending"]:
            raise ValueError(f"Cannot quote inquiry with status '{inquiry.status}'")

        quote_timestamp = quoted_at or timezone.now()

        with transaction.atomic():
            # Calculate quote time and grade
            quote_time = get_business_hours_between(inquiry.created_at, quote_timestamp)
            quote_grade = calculate_quote_grade(quote_time)

            # Update inquiry
            inquiry.status = "quoted"
            inquiry.quoted_at = quote_timestamp
            inquiry.quote_time = quote_time
            inquiry.quote_grade = quote_grade

            inquiry.save(update_fields=[
                'status', 'quoted_at', 'quote_time', 'quote_grade'
            ])

        return inquiry

    @staticmethod
    def complete_inquiry_success(*, inquiry: Inquiry, success_at: timezone.datetime = None) -> Inquiry:
        """
        Mark inquiry as successful and calculate completion KPI metrics

        Args:
            inquiry: Inquiry instance to mark as successful
            success_at: Custom success timestamp (defaults to now)

        Returns:
            Updated inquiry with completion KPI data
        """
        if inquiry.is_locked:
            raise ValueError("Cannot update locked inquiry")

        if inquiry.status not in ["quoted"]:
            raise ValueError(f"Cannot mark inquiry as successful with status '{inquiry.status}'")

        if not inquiry.quoted_at:
            raise ValueError("Cannot mark as successful without quote timestamp")

        success_timestamp = success_at or timezone.now()

        with transaction.atomic():
            # Calculate resolution time and grade
            resolution_time = get_business_hours_between(inquiry.quoted_at, success_timestamp)
            completion_grade = calculate_completion_grade(resolution_time)

            # Update inquiry
            inquiry.status = "success"
            inquiry.success_at = success_timestamp
            inquiry.resolution_time = resolution_time
            inquiry.completion_grade = completion_grade

            inquiry.save(update_fields=[
                'status', 'success_at', 'resolution_time', 'completion_grade'
            ])

        return inquiry

    @staticmethod
    def complete_inquiry_failed(*, inquiry: Inquiry, failed_at: timezone.datetime = None) -> Inquiry:
        """
        Mark inquiry as failed and calculate completion KPI metrics

        Args:
            inquiry: Inquiry instance to mark as failed
            failed_at: Custom failed timestamp (defaults to now)

        Returns:
            Updated inquiry with completion KPI data
        """
        if inquiry.is_locked:
            raise ValueError("Cannot update locked inquiry")

        if inquiry.status not in ["quoted"]:
            raise ValueError(f"Cannot mark inquiry as failed with status '{inquiry.status}'")

        if not inquiry.quoted_at:
            raise ValueError("Cannot mark as failed without quote timestamp")

        failed_timestamp = failed_at or timezone.now()

        with transaction.atomic():
            # Calculate resolution time and grade
            resolution_time = get_business_hours_between(inquiry.quoted_at, failed_timestamp)
            completion_grade = calculate_completion_grade(resolution_time)

            # Update inquiry
            inquiry.status = "failed"
            inquiry.failed_at = failed_timestamp
            inquiry.resolution_time = resolution_time
            inquiry.completion_grade = completion_grade

            inquiry.save(update_fields=[
                'status', 'failed_at', 'resolution_time', 'completion_grade'
            ])

        return inquiry

    @staticmethod
    def recalculate_kpi_metrics(*, inquiry: Inquiry, force: bool = False) -> Inquiry:
        """
        Recalculate KPI metrics for an inquiry

        Args:
            inquiry: Inquiry instance to recalculate
            force: Force recalculation even if inquiry is locked

        Returns:
            Updated inquiry with recalculated KPI data
        """
        if inquiry.is_locked and not force:
            raise ValueError("Cannot recalculate metrics for locked inquiry (use force=True to override)")

        if inquiry.auto_completion and not force:
            return inquiry  # Skip auto-completion inquiries unless forced

        update_fields = []

        with transaction.atomic():
            # Recalculate quote metrics if quoted
            if inquiry.quoted_at and inquiry.created_at:
                quote_time = get_business_hours_between(inquiry.created_at, inquiry.quoted_at)
                quote_grade = calculate_quote_grade(quote_time)

                if inquiry.quote_time != quote_time:
                    inquiry.quote_time = quote_time
                    update_fields.append('quote_time')

                if inquiry.quote_grade != quote_grade:
                    inquiry.quote_grade = quote_grade
                    update_fields.append('quote_grade')

            # Recalculate completion metrics if completed
            completion_timestamp = inquiry.success_at or inquiry.failed_at
            if completion_timestamp and inquiry.quoted_at:
                resolution_time = get_business_hours_between(inquiry.quoted_at, completion_timestamp)
                completion_grade = calculate_completion_grade(resolution_time)

                if inquiry.resolution_time != resolution_time:
                    inquiry.resolution_time = resolution_time
                    update_fields.append('resolution_time')

                if inquiry.completion_grade != completion_grade:
                    inquiry.completion_grade = completion_grade
                    update_fields.append('completion_grade')

            # Save only if there are changes
            if update_fields:
                inquiry.save(update_fields=update_fields)

        return inquiry

    @staticmethod
    def lock_inquiry_kpi(*, inquiry: Inquiry) -> Inquiry:
        """Lock inquiry to prevent KPI recalculation"""
        if not inquiry.is_locked:
            inquiry.is_locked = True
            inquiry.save(update_fields=['is_locked'])
        return inquiry

    @staticmethod
    def unlock_inquiry_kpi(*, inquiry: Inquiry) -> Inquiry:
        """Unlock inquiry to allow KPI recalculation"""
        if inquiry.is_locked:
            inquiry.is_locked = False
            inquiry.save(update_fields=['is_locked'])
        return inquiry

    @staticmethod
    def set_auto_completion(*, inquiry: Inquiry, auto_completion: bool = True) -> Inquiry:
        """Set auto-completion flag to skip automatic KPI calculations"""
        if inquiry.auto_completion != auto_completion:
            inquiry.auto_completion = auto_completion
            inquiry.save(update_fields=['auto_completion'])
        return inquiry
