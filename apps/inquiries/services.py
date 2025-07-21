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
        text: str,
        comment: str = "",
        sales_manager_id: int = None,
        is_new_customer: bool = False,
        status: str = "pending",
        **kwargs,
    ) -> Inquiry:
        """
        Create new inquiry with validation
        """
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
            inquiry = Inquiry.objects.create(
                client=client.strip(),
                text=text.strip(),
                comment=comment.strip(),
                sales_manager=sales_manager,
                is_new_customer=is_new_customer,
                status=status,
                **kwargs,
            )

        return inquiry

    @staticmethod
    def update_inquiry(
        *,
        inquiry: Inquiry,
        client: str = None,
        text: str = None,
        status: str = None,
        comment: str = None,
        sales_manager_id: int = None,
        is_new_customer: bool = None,
        **kwargs,
    ) -> Inquiry:
        """
        Update inquiry with validation
        """
        update_fields = []
        sales_manager = None
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

        if text is not None:
            if not text.strip():
                raise ValueError("Inquiry text cannot be empty")
            inquiry.text = text.strip()
            update_fields.append("text")

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
                inquiry.save(update_fields=update_fields)

        return inquiry

    @staticmethod
    def delete_inquiry(*, inquiry: Inquiry) -> None:
        """
        Delete inquiry with validation
        """
        if inquiry.status in ["success", "quoted"]:
            raise ValueError("Cannot delete inquiry with success or quoted status")

        inquiry.delete()
