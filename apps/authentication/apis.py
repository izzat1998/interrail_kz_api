from rest_framework import serializers, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken, UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from drf_spectacular.utils import extend_schema, OpenApiExample
from drf_spectacular.openapi import OpenApiTypes

from .services import AuthenticationServices
from .selectors import AuthenticationSelectors


# API Views
class LoginApiView(APIView):
    """
    User login endpoint
    """
    permission_classes = [AllowAny]

    class LoginSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        password = serializers.CharField(write_only=True)

    @extend_schema(
        tags=['Authentication'],
        summary='User Login',
        description='Authenticate user with username/password and return JWT tokens',
        request=LoginSerializer,
        examples=[
            OpenApiExample(
                'Login Example',
                value={
                    'username': 'john_doe',
                    'password': 'secure_password123'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'Login successful',
                    'data': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'user': {
                            'id': 1,
                            'username': 'john_doe',
                            'email': 'john@example.com',
                            'user_type': 'customer',
                            'telegram_id': '123456789',
                            'telegram_username': 'john_doe_tg'
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            auth_data = AuthenticationServices.authenticate_user(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            
            return Response({
                'success': True,
                'message': 'Login successful',
                'data': auth_data
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_401_UNAUTHORIZED)


class RegisterApiView(APIView):
    """
    User registration endpoint
    """
    permission_classes = [AllowAny]

    class RegisterSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        email = serializers.EmailField()
        password = serializers.CharField(write_only=True, min_length=8)
        user_type = serializers.ChoiceField(
            choices=[('customer', 'Customer'), ('manager', 'Manager'), ('admin', 'Admin')],
            default='customer'
        )
        telegram_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
        telegram_username = serializers.CharField(max_length=100, required=False, allow_blank=True)

    @extend_schema(
        tags=['Authentication'],
        summary='User Registration',
        description='Register a new user account and return JWT tokens',
        request=RegisterSerializer,
        examples=[
            OpenApiExample(
                'Registration Example',
                value={
                    'username': 'new_user',
                    'email': 'newuser@example.com',
                    'password': 'secure_password123',
                    'user_type': 'customer',
                    'telegram_id': '987654321',
                    'telegram_username': 'new_user_tg'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'Registration successful',
                    'data': {
                        'access_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'refresh_token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...',
                        'user': {
                            'id': 2,
                            'username': 'new_user',
                            'email': 'newuser@example.com',
                            'user_type': 'customer'
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={
            201: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = AuthenticationServices.create_user_account(**serializer.validated_data)
            
            # Generate tokens for the new user
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            access_token['user_type'] = user.user_type
            access_token['telegram_id'] = user.telegram_id
            
            return Response({
                'success': True,
                'message': 'Registration successful',
                'data': {
                    'access_token': str(access_token),
                    'refresh_token': str(refresh),
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'user_type': user.user_type,
                    }
                }
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class VerifyTokenApiView(APIView):
    """
    Verify JWT token validity
    """
    permission_classes = [AllowAny]

    class VerifyTokenSerializer(serializers.Serializer):
        token = serializers.CharField()

    @extend_schema(
        tags=['Authentication'],
        summary='Verify JWT Token',
        description='Verify if JWT token is valid and return user information',
        request=VerifyTokenSerializer,
        examples=[
            OpenApiExample(
                'Verify Token Example',
                value={
                    'token': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Valid Token Response',
                value={
                    'success': True,
                    'message': 'Token is valid',
                    'data': {
                        'user': {
                            'id': 1,
                            'username': 'john_doe',
                            'email': 'john@example.com',
                            'user_type': 'customer',
                            'telegram_id': '123456789',
                            'telegram_username': 'john_doe_tg'
                        },
                        'token_info': {
                            'exp': 1640995200,
                            'iat': 1640991600,
                            'jti': 'abc123def456',
                            'user_id': 1
                        }
                    }
                },
                response_only=True,
            ),
            OpenApiExample(
                'Invalid Token Response',
                value={
                    'success': False,
                    'message': 'Invalid or expired token'
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.VerifyTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            # Verify token
            token = UntypedToken(serializer.validated_data['token'])
            
            # Get user from token
            user_id = token.payload.get('user_id')
            if not user_id:
                return Response({
                    'success': False,
                    'message': 'Invalid token payload'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get user instance
            from apps.accounts.models import CustomUser
            try:
                user = CustomUser.objects.get(id=user_id)
            except CustomUser.DoesNotExist:
                return Response({
                    'success': False,
                    'message': 'User not found'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            if not user.is_active:
                return Response({
                    'success': False,
                    'message': 'User account is disabled'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            return Response({
                'success': True,
                'message': 'Token is valid',
                'data': {
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'user_type': user.user_type,
                        'telegram_id': user.telegram_id,
                        'telegram_username': user.telegram_username,
                    },
                    'token_info': {
                        'exp': token.payload.get('exp'),
                        'iat': token.payload.get('iat'),
                        'jti': token.payload.get('jti'),
                        'user_id': token.payload.get('user_id'),
                    }
                }
            }, status=status.HTTP_200_OK)
            
        except (InvalidToken, TokenError):
            return Response({
                'success': False,
                'message': 'Invalid or expired token'
            }, status=status.HTTP_401_UNAUTHORIZED)


class RefreshTokenApiView(APIView):
    """
    Token refresh endpoint
    """
    permission_classes = [AllowAny]

    class RefreshTokenSerializer(serializers.Serializer):
        refresh = serializers.CharField()

    @extend_schema(
        tags=['Authentication'],
        summary='Refresh JWT Token',
        description='Get a new access token using refresh token',
        request=RefreshTokenSerializer,
        examples=[
            OpenApiExample(
                'Refresh Token Example',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'data': {
                        'access': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    }
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            401: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            refresh_token = RefreshToken(serializer.validated_data['refresh'])
            access_token = refresh_token.access_token
            
            # Add custom claims if user exists
            user_id = refresh_token.payload.get('user_id')
            if user_id:
                from apps.accounts.models import CustomUser
                try:
                    user = CustomUser.objects.get(id=user_id)
                    access_token['user_type'] = user.user_type
                    access_token['telegram_id'] = user.telegram_id
                except CustomUser.DoesNotExist:
                    pass
            
            return Response({
                'success': True,
                'data': {
                    'access': str(access_token)
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Invalid refresh token'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutApiView(APIView):
    """
    User logout endpoint (blacklist refresh token)
    """
    permission_classes = [IsAuthenticated]

    class LogoutSerializer(serializers.Serializer):
        refresh = serializers.CharField()

    @extend_schema(
        tags=['Authentication'],
        summary='User Logout',
        description='Logout user by blacklisting the refresh token',
        request=LogoutSerializer,
        examples=[
            OpenApiExample(
                'Logout Example',
                value={
                    'refresh': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'Logout successful'
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            AuthenticationServices.blacklist_refresh_token(
                refresh_token=serializer.validated_data['refresh']
            )
            
            return Response({
                'success': True,
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)



class UserProfileApiView(APIView):
    """
    Get current user profile
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User Profile'],
        summary='Get User Profile',
        description='Get current authenticated user profile and permissions',
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'data': {
                        'profile': {
                            'id': 1,
                            'username': 'john_doe',
                            'email': 'john@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'user_type': 'customer',
                            'telegram_id': '123456789',
                            'telegram_username': 'john_doe_tg',
                            'telegram_access': True,
                            'is_active': True,
                            'date_joined': '2024-01-01T00:00:00Z',
                            'last_login': '2024-01-15T10:30:00Z'
                        },
                        'permissions': {
                            'can_manage_users': False,
                            'can_view_all_users': False,
                            'can_access_admin': False,
                            'can_manage_routes': False,
                            'can_book_tickets': True
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
        }
    )
    def get(self, request):
        profile_data = AuthenticationSelectors.get_user_profile(user=request.user)
        permissions = AuthenticationSelectors.get_user_permissions(user=request.user)
        
        return Response({
            'success': True,
            'data': {
                'profile': profile_data,
                'permissions': permissions
            }
        }, status=status.HTTP_200_OK)


class ChangePasswordApiView(APIView):
    """
    Change user password
    """
    permission_classes = [IsAuthenticated]

    class ChangePasswordSerializer(serializers.Serializer):
        old_password = serializers.CharField(write_only=True)
        new_password = serializers.CharField(write_only=True, min_length=8)

    @extend_schema(
        tags=['User Profile'],
        summary='Change Password',
        description='Change current user password',
        request=ChangePasswordSerializer,
        examples=[
            OpenApiExample(
                'Change Password Example',
                value={
                    'old_password': 'current_password123',
                    'new_password': 'new_secure_password456'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'Password changed successfully'
                },
                response_only=True,
            )
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: OpenApiTypes.OBJECT,
        }
    )
    def post(self, request):
        serializer = self.ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            AuthenticationServices.change_user_password(
                user=request.user,
                old_password=serializer.validated_data['old_password'],
                new_password=serializer.validated_data['new_password']
            )
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
