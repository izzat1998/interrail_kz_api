from rest_framework.permissions import BasePermission


class IsManagerOrAdmin(BasePermission):
    """
    Permission class that allows access only to managers and admins
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type in ["manager", "admin"]
        )


class IsAdminOnly(BasePermission):
    """
    Permission class that allows access only to admins
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "admin"
        )


class IsCustomerOnly(BasePermission):
    """
    Permission class that allows access only to customers
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.user_type == "customer"
        )


class IsOwnerOrManagerOrAdmin(BasePermission):
    """
    Permission class that allows access to object owners, managers, and admins
    Useful for detail views where users can access their own data
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin and managers can access any object
        if request.user.user_type in ["manager", "admin"]:
            return True

        # Check if object has owner field and user is the owner
        if hasattr(obj, "user") and obj.user == request.user:
            return True
        if hasattr(obj, "owner") and obj.owner == request.user:
            return True
        if hasattr(obj, "created_by") and obj.created_by == request.user:
            return True

        return False
