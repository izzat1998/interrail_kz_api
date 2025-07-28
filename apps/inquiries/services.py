from django.db import transaction

from apps.accounts.models import CustomUser

from .models import Inquiry


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
                sales_manager = InquirySelectors.get_sales_manager_by_id(
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
                sales_manager = InquirySelectors.get_sales_manager_by_id(
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
