from drf_spectacular.openapi import OpenApiTypes
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .authentication import CookieJWTAuthentication
from .selectors import AuthenticationSelectors
from .services import AuthenticationServices, TelegramAuthenticationServices


# API Views
class LoginApiView(APIView):
    """
    User login endpoint
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    class LoginSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        password = serializers.CharField(write_only=True)

    @extend_schema(
        tags=["Authentication"],
        summary="User Login",
        description="Authenticate user with username/password and set JWT tokens as HTTP-only cookies",
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                "Login Example",
                value={"username": "john_doe", "password": "secure_password123"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"success": True},
                response_only=True,
                description="JWT tokens are set as HTTP-only cookies (access_token, refresh_token)",
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = self.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            auth_data = AuthenticationServices.authenticate_user(
                username=serializer.validated_data["username"],
                password=serializer.validated_data["password"],
            )
            access = str(auth_data["access"])
            refresh = str(auth_data["refresh"])

            res = Response(
                {
                    "success": True,
                },
                status=status.HTTP_200_OK,
            )
            # Set HttpOnly cookie
            res.set_cookie(
                key="access_token",
                value=access,
                httponly=True,
                secure=True,  # set False if testing on http
                samesite="None",  # Changed from None to Lax for HTTP
                max_age=30 * 60,  # 30 minutes (matches JWT access token lifetime)
            )
            res.set_cookie(
                key="refresh_token",
                value=refresh,
                httponly=True,
                secure=True,
                samesite="None",  # Changed from None to Lax for HTTP
                max_age=86400 * 7,  # 7 day
            )
            return res

        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class RegisterApiView(APIView):
    """
    User registration endpoint
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    class RegisterSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        email = serializers.EmailField()
        password = serializers.CharField(write_only=True, min_length=8)
        user_type = serializers.ChoiceField(
            choices=[
                ("customer", "Customer"),
                ("manager", "Manager"),
                ("admin", "Admin"),
            ],
            default="customer",
        )
        telegram_id = serializers.CharField(
            max_length=50, required=False, allow_blank=True
        )
        telegram_username = serializers.CharField(
            max_length=100, required=False, allow_blank=True
        )

    @extend_schema(
        tags=["Authentication"],
        summary="User Registration",
        description="Register a new user account and return JWT tokens",
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                "Registration Example",
                value={
                    "username": "new_user",
                    "email": "newuser@example.com",
                    "password": "secure_password123",
                    "user_type": "customer",
                    "telegram_id": "987654321",
                    "telegram_username": "new_user_tg",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "success": True,
                    "message": "Registration successful",
                    "data": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "user": {
                            "id": 2,
                            "username": "new_user",
                            "email": "newuser@example.com",
                            "user_type": "customer",
                        },
                    },
                },
                response_only=True,
            ),
        ],
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = self.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = AuthenticationServices.create_user_account(
                **serializer.validated_data
            )

            # Generate tokens for the new user
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token["user_type"] = user.user_type
            access_token["telegram_id"] = user.telegram_id

            return Response(
                {
                    "success": True,
                    "message": "Registration successful",
                    "data": {
                        "access_token": str(access_token),
                        "refresh_token": str(refresh),
                        "user": {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "user_type": user.user_type,
                        },
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class VerifyTokenApiView(APIView):
    """
    Verify JWT token and return user information
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    class EmptySerializer(serializers.Serializer):
        pass

    @extend_schema(
        tags=["Authentication"],
        summary="Verify JWT Token",
        description="Verify JWT token validity and return user information and token details",
        request=EmptySerializer,
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "user": {
                        "id": 1,
                        "username": "john_doe",
                        "email": "john@example.com",
                        "user_type": "customer",
                        "telegram_id": "123456789",
                        "telegram_username": "john_doe_tg",
                    },
                    "token_info": {
                        "exp": 1640995200,
                        "iat": 1640991600,
                        "user_id": 1,
                    },
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        return Response(
            {
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "email": request.user.email,
                    "user_type": getattr(request.user, "user_type", None),
                    "telegram_id": getattr(request.user, "telegram_id", None),
                    "telegram_username": getattr(
                        request.user, "telegram_username", None
                    ),
                },
                "token_info": {
                    "exp": request.auth.payload["exp"],
                    "iat": request.auth.payload["iat"],
                    "user_id": request.auth.payload["user_id"],
                },
            }
        )


class RefreshTokenApiView(APIView):
    """
    Token refresh endpoint using HTTP-only cookies
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    class EmptySerializer(serializers.Serializer):
        pass

    @extend_schema(
        tags=["Authentication"],
        summary="Refresh JWT Token",
        description="Refresh JWT tokens using HTTP-only refresh token cookie and set new tokens as cookies",
        request=EmptySerializer,
        examples=[
            OpenApiExample(
                "Success Response",
                value={"success": True},
                response_only=True,
                description="New JWT tokens are set as HTTP-only cookies (access_token, refresh_token)",
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        # Get refresh token from HTTP-only cookie
        refresh_token_str = request.COOKIES.get("refresh_token")

        if not refresh_token_str:
            return Response(
                {"success": False, "message": "Refresh token not found in cookies"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            # Validate refresh token
            refresh_token = RefreshToken(refresh_token_str)

            # Get user and generate new tokens
            user_id = refresh_token.payload.get("user_id")
            if not user_id:
                return Response(
                    {"success": False, "message": "Invalid token payload"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            from apps.accounts.models import CustomUser

            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response(
                    {"success": False, "message": "User not found"},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            # Generate new refresh token for rotation
            new_refresh_token = RefreshToken.for_user(user)
            new_access_token = new_refresh_token.access_token

            # Add custom claims to new access token
            new_access_token["user_type"] = user.user_type
            new_access_token["telegram_id"] = user.telegram_id

            # Blacklist old refresh token
            refresh_token.blacklist()

            # Create response with success message
            res = Response({"success": True}, status=status.HTTP_200_OK)

            # Set new tokens as HTTP-only cookies
            res.set_cookie(
                key="access_token",
                value=str(new_access_token),
                httponly=True,
                secure=True,  # set False if testing on http
                samesite="None",  # Changed from None to Lax for HTTP
                max_age=30 * 60,  # 30 minutes (matches JWT access token lifetime)
            )
            res.set_cookie(
                key="refresh_token",
                value=str(new_refresh_token),
                httponly=True,
                secure=True,
                samesite="None",  # Changed from None to Lax for HTTP
                max_age=86400 * 7,  # 7 days
            )

            return res

        except (InvalidToken, TokenError):
            return Response(
                {"success": False, "message": "Invalid or expired refresh token"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except Exception:
            return Response(
                {"success": False, "message": "Token refresh failed"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class LogoutApiView(APIView):
    """
    User logout endpoint using HTTP-only cookies
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [AllowAny]

    class EmptySerializer(serializers.Serializer):
        pass

    @extend_schema(
        tags=["Authentication"],
        summary="User Logout",
        description="Logout user by blacklisting refresh token from HTTP-only cookies and clearing all auth cookies",
        examples=[
            OpenApiExample(
                "Success Response",
                value={"success": True, "message": "Logout successful"},
                response_only=True,
                description="Refresh token is blacklisted and all auth cookies are cleared",
            )
        ],
        request=EmptySerializer,
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        # Get refresh token from HTTP-only cookie
        refresh_token_str = request.COOKIES.get("refresh_token")

        # Create response first
        res = Response(
            {"success": True, "message": "Logout successful"}, status=status.HTTP_200_OK
        )

        # Clear auth cookies regardless of token validity
        res.delete_cookie(
            key="access_token",
            samesite="None",
        )
        res.delete_cookie(
            key="refresh_token",
            samesite="None",
        )

        # If refresh token exists, try to blacklist it
        if refresh_token_str:
            try:
                refresh_token = RefreshToken(refresh_token_str)
                refresh_token.blacklist()
            except (InvalidToken, TokenError, Exception):
                # Token might be invalid/expired, but still clear cookies
                # Don't fail the logout process
                pass

        return res


class UserProfileApiView(APIView):
    """
    Get current user profile
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    class EmptySerializer(serializers.Serializer):
        pass

    @extend_schema(
        tags=["User Profile"],
        summary="Get User Profile",
        description="Get current authenticated user profile and permissions",
        examples=[
            OpenApiExample(
                "Success Response",
                value={
                    "success": True,
                    "data": {
                        "profile": {
                            "id": 1,
                            "username": "john_doe",
                            "email": "john@example.com",
                            "first_name": "John",
                            "last_name": "Doe",
                            "user_type": "customer",
                            "telegram_id": "123456789",
                            "telegram_username": "john_doe_tg",
                            "telegram_access": True,
                            "is_active": True,
                            "date_joined": "2024-01-01T00:00:00Z",
                            "last_login": "2024-01-15T10:30:00Z",
                        },
                        "permissions": {
                            "can_manage_users": False,
                            "can_view_all_users": False,
                            "can_access_admin": False,
                            "can_manage_routes": False,
                            "can_book_tickets": True,
                        },
                    },
                },
                response_only=True,
            )
        ],
        request=EmptySerializer,
        responses={
            200: OpenApiTypes.OBJECT,
        },
    )
    def get(self, request):
        profile_data = AuthenticationSelectors.get_user_profile(user=request.user)
        permissions = AuthenticationSelectors.get_user_permissions(user=request.user)

        return Response(
            {
                "success": True,
                "data": {"profile": profile_data, "permissions": permissions},
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordApiView(APIView):
    """
    Change user password
    """

    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [IsAuthenticated]

    class ChangePasswordSerializer(serializers.Serializer):
        old_password = serializers.CharField(write_only=True)
        new_password = serializers.CharField(write_only=True, min_length=8)

    @extend_schema(
        tags=["User Profile"],
        summary="Change Password",
        description="Change current user password",
        request=ChangePasswordSerializer,
        examples=[
            OpenApiExample(
                "Change Password Example",
                value={
                    "old_password": "current_password123",
                    "new_password": "new_secure_password456",
                },
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={"success": True, "message": "Password changed successfully"},
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = self.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            AuthenticationServices.change_user_password(
                user=request.user,
                old_password=serializer.validated_data["old_password"],
                new_password=serializer.validated_data["new_password"],
            )

            return Response(
                {"success": True, "message": "Password changed successfully"},
                status=status.HTTP_200_OK,
            )

        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TelegramAuthApiView(APIView):
    """
    Telegram bot authentication endpoint - check if telegram_id exists
    """

    permission_classes = [AllowAny]

    class TelegramAuthSerializer(serializers.Serializer):
        telegram_id = serializers.CharField(max_length=50)

    @extend_schema(
        tags=["Telegram Authentication"],
        summary="Telegram ID Authentication",
        description="Check if telegram_id exists for a manager and authenticate or request phone verification",
        request=TelegramAuthSerializer,
        examples=[
            OpenApiExample(
                "Telegram Auth Request",
                value={"telegram_id": "123456789"},
                request_only=True,
            ),
            OpenApiExample(
                "User Found Response",
                value={
                    "success": True,
                    "authenticated": True,
                    "data": {
                        "user_id": 1,
                        "username": "manager_user",
                        "user_type": "manager",
                        "telegram_id": "123456789",
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    },
                },
                response_only=True,
            ),
            OpenApiExample(
                "Phone Required Response",
                value={
                    "success": True,
                    "authenticated": False,
                    "requires_phone": True,
                    "message": "Please provide your phone number for verification",
                },
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = self.TelegramAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data["telegram_id"]

        # Check if user exists with this telegram_id
        auth_data = TelegramAuthenticationServices.authenticate_by_telegram_id(
            telegram_id=telegram_id
        )

        if auth_data:
            return Response(
                {
                    "success": True,
                    "authenticated": True,
                    "data": auth_data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": True,
                    "authenticated": False,
                    "requires_phone": True,
                    "message": "Please provide your phone number for verification",
                },
                status=status.HTTP_200_OK,
            )


class TelegramPhoneAuthApiView(APIView):
    """
    Telegram phone verification endpoint - link telegram_id to manager by phone
    """

    permission_classes = [AllowAny]

    class TelegramPhoneAuthSerializer(serializers.Serializer):
        telegram_id = serializers.CharField(max_length=50)
        phone = serializers.CharField(max_length=20)

    @extend_schema(
        tags=["Telegram Authentication"],
        summary="Telegram Phone Verification",
        description="Verify manager by phone number and link telegram_id for future authentication",
        request=TelegramPhoneAuthSerializer,
        examples=[
            OpenApiExample(
                "Phone Verification Request",
                value={"telegram_id": "123456789", "phone": "+77777777777"},
                request_only=True,
            ),
            OpenApiExample(
                "Success Response",
                value={
                    "success": True,
                    "authenticated": True,
                    "message": "Phone verified successfully. You are now authorized for Telegram access.",
                    "data": {
                        "user_id": 1,
                        "username": "manager_user",
                        "user_type": "manager",
                        "telegram_id": "123456789",
                        "phone": "+77777777777",
                        "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    },
                },
                response_only=True,
            ),
            OpenApiExample(
                "Not Authorized Response",
                value={
                    "success": False,
                    "authenticated": False,
                    "message": "Phone number not found or you are not authorized to use this bot. Please contact your administrator.",
                },
                response_only=True,
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            403: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        },
    )
    def post(self, request):
        serializer = self.TelegramPhoneAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        telegram_id = serializer.validated_data["telegram_id"]
        phone = serializer.validated_data["phone"]

        # Try to authenticate by phone and link telegram_id
        auth_data = TelegramAuthenticationServices.authenticate_by_phone(
            telegram_id=telegram_id, phone=phone
        )

        if auth_data:
            return Response(
                {
                    "success": True,
                    "authenticated": True,
                    "message": "Phone verified successfully. You are now authorized for Telegram access.",
                    "data": auth_data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {
                    "success": False,
                    "authenticated": False,
                    "message": "Phone number not found or you are not authorized to use this bot. Please contact your administrator.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )
