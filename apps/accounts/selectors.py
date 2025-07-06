from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from typing import Dict, Any, List, Optional

from .filters import UserFilter

User = get_user_model()


class UserSelectors:
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """
        Get user by username
        """
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None
    
    @staticmethod
    def user_list(*, filters: Optional[Dict[str, Any]] = None) -> QuerySet[User]:
        """
        Get users list with filtering using django-filter
        """
        filters = filters or {}
        
        qs = User.objects.all().order_by('-date_joined')
        
        return UserFilter(filters, qs).qs
    
    @staticmethod
    def get_user_list_by_type(user_type: str) -> QuerySet[User]:
        """
        Get users by type
        """
        return User.objects.filter(user_type=user_type, is_active=True).order_by('username')
    
    @staticmethod
    def get_user_profile_data(user: User) -> Dict[str, Any]:
        """
        Get formatted user profile data
        """
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'user_type': user.user_type,
            'telegram_id': user.telegram_id,
            'telegram_username': user.telegram_username,
            'telegram_access': user.telegram_access,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
    
    @staticmethod
    def get_users_stats() -> Dict[str, Any]:
        """
        Get user statistics
        """
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        
        # Count by user type
        user_type_counts = {}
        for user_type, _ in User.USER_TYPES:
            user_type_counts[user_type] = User.objects.filter(user_type=user_type, is_active=True).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'inactive_users': total_users - active_users,
            'user_type_counts': user_type_counts
        }
    
    @staticmethod
    def search_users(query: str, limit: int = 10) -> List[User]:
        """
        Search users by username, email, or names
        """
        return User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query),
            is_active=True
        )[:limit]