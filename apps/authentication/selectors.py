from apps.accounts.models import CustomUser


class AuthenticationSelectors:
    """
    Selectors for authentication-related data retrieval
    """

    @staticmethod
    def get_user_profile(*, user: CustomUser) -> dict:
        """
        Get complete user profile data
        """
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type,
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "telegram_access": user.telegram_access,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
        }

    @staticmethod
    def get_user_permissions(*, user: CustomUser) -> dict:
        """
        Get user permissions based on user_type
        """
        permissions = {
            "can_manage_users": False,
            "can_view_all_users": False,
            "can_access_admin": False,
            "can_manage_routes": False,
            "can_book_tickets": False,
        }

        if user.user_type == "admin":
            permissions.update(
                {
                    "can_manage_users": True,
                    "can_view_all_users": True,
                    "can_access_admin": True,
                    "can_manage_routes": True,
                    "can_book_tickets": True,
                }
            )
        elif user.user_type == "manager":
            permissions.update(
                {
                    "can_view_all_users": True,
                    "can_manage_routes": True,
                    "can_book_tickets": True,
                }
            )
        elif user.user_type == "customer":
            permissions.update(
                {
                    "can_book_tickets": True,
                }
            )

        return permissions

    @staticmethod
    def get_user_by_telegram_id(*, telegram_id: str) -> CustomUser | None:
        """
        Get user by Telegram ID
        """
        try:
            return CustomUser.objects.get(telegram_id=telegram_id)
        except CustomUser.DoesNotExist:
            return None

    @staticmethod
    def check_user_exists(*, username: str = None, email: str = None) -> dict:
        """
        Check if user exists by username or email
        """
        result = {"exists": False, "field": None}

        if username and CustomUser.objects.filter(username=username).exists():
            result = {"exists": True, "field": "username"}
        elif email and CustomUser.objects.filter(email=email).exists():
            result = {"exists": True, "field": "email"}

        return result
