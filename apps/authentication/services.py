from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser


class AuthenticationServices:
    """
    Services for authentication-related business logic
    """

    @staticmethod
    def authenticate_user(*, username: str, password: str) -> dict:
        """
        Authenticate user and return JWT tokens with user info
        """
        user = authenticate(username=username, password=password)

        if not user:
            raise ValueError("Invalid credentials")

        if not user.is_active:
            raise ValueError("User account is disabled")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token

        # Add custom claims
        access_token["user_type"] = user.user_type
        access_token["telegram_id"] = user.telegram_id

        # Update last login
        update_last_login(None, user)

        return {
            "access": str(access_token),
            "refresh": str(refresh),
        }

    @staticmethod
    def create_user_account(
        *,
        username: str,
        email: str,
        password: str,
        user_type: str = "customer",
        telegram_id: str | None = None,
        telegram_username: str | None = None,
        **kwargs,
    ) -> CustomUser:
        """
        Create new user account with validation
        """
        # Validate user type
        valid_types = [choice[0] for choice in CustomUser.USER_TYPES]
        if user_type not in valid_types:
            raise ValueError(f"Invalid user type. Must be one of: {valid_types}")

        # Check if user already exists
        if CustomUser.objects.filter(username=username).exists():
            raise ValueError("Username already exists")

        if CustomUser.objects.filter(email=email).exists():
            raise ValueError("Email already exists")

        # Create user
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            user_type=user_type,
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            **kwargs,
        )

        return user

    @staticmethod
    def blacklist_refresh_token(*, refresh_token: str) -> None:
        """
        Blacklist refresh token for logout
        """
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            raise ValueError("Invalid refresh token")

    @staticmethod
    def change_user_password(
        *, user: CustomUser, old_password: str, new_password: str
    ) -> None:
        """
        Change user password with validation
        """
        if not user.check_password(old_password):
            raise ValueError("Current password is incorrect")

        user.set_password(new_password)
        user.save(update_fields=["password"])
