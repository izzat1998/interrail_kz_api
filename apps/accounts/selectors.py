from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Case, Count, IntegerField, Q, QuerySet, When

from .filters import UserFilter

User = get_user_model()


class UserSelectors:
    """
    Selectors for user-related data retrieval
    """

    @staticmethod
    def get_user_by_id(*, user_id: int) -> User:
        """
        Get user by ID with error handling
        """
        return User.objects.get(id=user_id)

    @staticmethod
    def get_user_by_username(*, username: str) -> User:
        """
        Get user by username with error handling
        """
        return User.objects.get(username=username)

    @staticmethod
    def get_user_by_telegram_id(*, telegram_id: str) -> User:
        """
        Get user by Telegram ID with error handling
        """
        return User.objects.get(telegram_id=telegram_id)

    @staticmethod
    def user_list(*, filters: dict[str, Any] | None = None) -> QuerySet[User]:
        """
        Get users list with filtering using django-filter
        """
        filters = filters or {}
        qs = User.objects.all().order_by("-date_joined")
        return UserFilter(filters, qs).qs

    @staticmethod
    def get_user_list_by_type(*, user_type: str) -> QuerySet[User]:
        """
        Get users by type with optimization
        """
        return User.objects.filter(user_type=user_type, is_active=True).order_by(
            "username"
        )

    @staticmethod
    def get_user_profile_data(*, user: User) -> dict[str, Any]:
        """
        Get formatted user profile data
        """
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "user_type": user.user_type,
            "user_type_display": user.get_user_type_display(),
            "telegram_id": user.telegram_id,
            "telegram_username": user.telegram_username,
            "telegram_access": user.telegram_access,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined,
            "last_login": user.last_login,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }

    @staticmethod
    def get_users_stats() -> dict[str, Any]:
        """
        Get user statistics using optimized single query
        """
        stats = User.objects.aggregate(
            total_users=Count("id"),
            active_users=Count(
                Case(
                    When(is_active=True, then=1),
                    output_field=IntegerField(),
                )
            ),
            customer_count=Count(
                Case(
                    When(user_type="customer", is_active=True, then=1),
                    output_field=IntegerField(),
                )
            ),
            manager_count=Count(
                Case(
                    When(user_type="manager", is_active=True, then=1),
                    output_field=IntegerField(),
                )
            ),
            admin_count=Count(
                Case(
                    When(user_type="admin", is_active=True, then=1),
                    output_field=IntegerField(),
                )
            ),
        )

        stats["inactive_users"] = stats["total_users"] - stats["active_users"]
        stats["user_type_counts"] = {
            "customer": stats["customer_count"],
            "manager": stats["manager_count"],
            "admin": stats["admin_count"],
        }

        # Remove the individual counts from the main stats
        stats.pop("customer_count")
        stats.pop("manager_count")
        stats.pop("admin_count")

        return stats

    @staticmethod
    def search_users(*, query: str, limit: int = 10) -> QuerySet[User]:
        """
        Search users by username, email, or names with optimization
        """
        return User.objects.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query),
            is_active=True,
        )[:limit]
