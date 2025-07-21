from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class UserServices:
    """
    Services for user-related business logic
    """

    @staticmethod
    def create_user(
        *,
        username: str,
        email: str,
        password: str,
        user_type: str = "customer",
        **kwargs,
    ) -> User:
        """
        Create a new user with validation
        """
        # Validation
        if not username or not username.strip():
            raise ValueError("Username cannot be empty")

        if not email or not email.strip():
            raise ValueError("Email cannot be empty")

        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        username = username.strip()
        email = email.strip().lower()

        if User.objects.filter(username=username).exists():
            raise ValueError("Username already exists")

        if User.objects.filter(email=email).exists():
            raise ValueError("Email already exists")

        if user_type not in dict(User.USER_TYPES):
            raise ValueError("Invalid user type")

        with transaction.atomic():
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type=user_type,
                **kwargs,
            )

        return user

    @staticmethod
    def update_user(*, user_id: int, **update_data) -> User:
        """
        Update user information with validation
        """
        from .selectors import UserSelectors

        try:
            user = UserSelectors.get_user_by_id(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        update_fields = []

        # Validate and handle username update
        if "username" in update_data:
            username = update_data["username"]
            if not username or not username.strip():
                raise ValueError("Username cannot be empty")
            username = username.strip()

            if User.objects.filter(username=username).exclude(id=user_id).exists():
                raise ValueError("Username already exists")

            user.username = username
            update_fields.append("username")

        # Validate and handle email update
        if "email" in update_data:
            email = update_data["email"]
            if not email or not email.strip():
                raise ValueError("Email cannot be empty")
            email = email.strip().lower()

            if User.objects.filter(email=email).exclude(id=user_id).exists():
                raise ValueError("Email already exists")

            user.email = email
            update_fields.append("email")

        # Handle user type update
        if "user_type" in update_data:
            user_type = update_data["user_type"]
            if user_type not in dict(User.USER_TYPES):
                raise ValueError("Invalid user type")
            user.user_type = user_type
            update_fields.append("user_type")

        # Handle password update
        if "password" in update_data:
            password = update_data["password"]
            if not password or len(password) < 8:
                raise ValueError("Password must be at least 8 characters long")
            user.set_password(password)
            update_fields.append("password")

        # Handle other fields
        allowed_fields = [
            "first_name",
            "last_name",
            "telegram_id",
            "telegram_username",
            "telegram_access",
            "is_active",
        ]
        for field in allowed_fields:
            if field in update_data:
                value = update_data[field]
                if field in ["first_name", "last_name"] and value:
                    value = value.strip()
                setattr(user, field, value)
                update_fields.append(field)

        if update_fields:
            with transaction.atomic():
                user.save(
                    update_fields=(
                        update_fields if "password" not in update_fields else None
                    )
                )

        return user

    @staticmethod
    def delete_user(*, user_id: int) -> None:
        """
        Soft delete user (deactivate) with validation
        """
        from .selectors import UserSelectors

        try:
            user = UserSelectors.get_user_by_id(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        if user.is_superuser:
            raise ValueError("Cannot delete superuser")

        user.is_active = False
        user.save(update_fields=["is_active"])

    @staticmethod
    def activate_user(*, user_id: int) -> User:
        """
        Activate a deactivated user
        """
        from .selectors import UserSelectors

        try:
            user = UserSelectors.get_user_by_id(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        user.is_active = True
        user.save(update_fields=["is_active"])
        return user

    @staticmethod
    def change_user_type(*, user_id: int, new_user_type: str) -> User:
        """
        Change user type with validation
        """
        from .selectors import UserSelectors

        if new_user_type not in dict(User.USER_TYPES):
            raise ValueError("Invalid user type")

        try:
            user = UserSelectors.get_user_by_id(user_id=user_id)
        except User.DoesNotExist:
            raise ValueError("User not found")

        if user.is_superuser and new_user_type != "admin":
            raise ValueError("Cannot change superuser type to non-admin")

        user.user_type = new_user_type
        user.save(update_fields=["user_type"])
        return user
