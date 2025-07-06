from rest_framework import serializers, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter
from drf_spectacular.openapi import OpenApiTypes

from apps.api_config.pagination import get_paginated_response, LimitOffsetPagination
from .services import UserServices
from .selectors import UserSelectors


class UserListApiView(APIView):
    """
    Get list of users with filtering and pagination
    """
    permission_classes = [IsAuthenticated]

    class Pagination(LimitOffsetPagination):
        default_limit = 10
        max_limit = 50

    class FilterSerializer(serializers.Serializer):
        id = serializers.IntegerField(required=False)
        email = serializers.CharField(required=False)
        username = serializers.CharField(required=False)
        first_name = serializers.CharField(required=False)
        last_name = serializers.CharField(required=False)
        user_type = serializers.ChoiceField(
            choices=[('customer', 'Customer'), ('manager', 'Manager'), ('admin', 'Admin')],
            required=False
        )
        is_active = serializers.BooleanField(required=False, allow_null=True)
        telegram_username = serializers.CharField(required=False)
        search = serializers.CharField(required=False)

    class OutputSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        username = serializers.CharField()
        email = serializers.EmailField()
        first_name = serializers.CharField()
        last_name = serializers.CharField()
        user_type = serializers.CharField()
        telegram_id = serializers.CharField()
        telegram_username = serializers.CharField()
        telegram_access = serializers.BooleanField()
        is_active = serializers.BooleanField()
        is_staff = serializers.BooleanField()
        is_superuser = serializers.BooleanField()
        date_joined = serializers.DateTimeField()
        last_login = serializers.DateTimeField()

    @extend_schema(
        tags=['User Management'],
        summary='List Users',
        description='Get paginated list of users with optional filtering by type, status, and search',
        parameters=[
            OpenApiParameter('limit', OpenApiTypes.INT, description='Items per page (default: 10)'),
            OpenApiParameter('offset', OpenApiTypes.INT, description='Number of items to skip (default: 0)'),
            OpenApiParameter('id', OpenApiTypes.INT, description='Filter by user ID'),
            OpenApiParameter('email', OpenApiTypes.STR, description='Filter by email (contains)'),
            OpenApiParameter('username', OpenApiTypes.STR, description='Filter by username (contains)'),
            OpenApiParameter('first_name', OpenApiTypes.STR, description='Filter by first name (contains)'),
            OpenApiParameter('last_name', OpenApiTypes.STR, description='Filter by last name (contains)'),
            OpenApiParameter('user_type', OpenApiTypes.STR, description='Filter by user type'),
            OpenApiParameter('is_active', OpenApiTypes.BOOL, description='Filter by active status'),
            OpenApiParameter('telegram_username', OpenApiTypes.STR, description='Filter by telegram username (contains)'),
            OpenApiParameter('search', OpenApiTypes.STR, description='Search across username, email, names'),
        ],
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'limit': 10,
                    'offset': 0,
                    'count': 50,
                    'next': 'http://localhost:8000/api/accounts/users/?limit=10&offset=10',
                    'previous': None,
                    'results': [
                        {
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
                            'is_staff': False,
                            'is_superuser': False,
                            'date_joined': '2024-01-01T00:00:00Z',
                            'last_login': '2024-01-15T10:30:00Z'
                        }
                    ]
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        # Check user permissions
        if request.user.user_type not in ['admin', 'manager']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        # Validate filters
        filters_serializer = self.FilterSerializer(data=request.query_params)
        filters_serializer.is_valid(raise_exception=True)

        # Get users queryset with filters
        users = UserSelectors.user_list(filters=filters_serializer.validated_data)

        # Return paginated response
        return get_paginated_response(
            pagination_class=self.Pagination,
            serializer_class=self.OutputSerializer,
            queryset=users,
            request=request,
            view=self,
        )


class UserDetailApiView(APIView):
    """
    Get, update, or delete a specific user
    """
    permission_classes = [IsAuthenticated]

    class UserUpdateSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150, required=False)
        email = serializers.EmailField(required=False)
        first_name = serializers.CharField(max_length=30, required=False)
        last_name = serializers.CharField(max_length=30, required=False)
        user_type = serializers.ChoiceField(
            choices=[('customer', 'Customer'), ('manager', 'Manager'), ('admin', 'Admin')],
            required=False
        )
        telegram_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
        telegram_username = serializers.CharField(max_length=100, required=False, allow_blank=True)
        telegram_access = serializers.BooleanField(required=False)
        is_active = serializers.BooleanField(required=False)

    @extend_schema(
        tags=['User Management'],
        summary='Get User',
        description='Get specific user details by ID',
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'data': {
                        'user': {
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
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def get(self, request, user_id):
        # Check permissions
        if request.user.user_type not in ['admin', 'manager'] and request.user.id != user_id:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        user = UserSelectors.get_user_by_id(user_id)
        if not user:
            return Response({
                'success': False,
                'message': 'User not found'
            }, status=status.HTTP_404_NOT_FOUND)

        user_data = UserSelectors.get_user_profile_data(user)
        return Response({
            'success': True,
            'data': {'user': user_data}
        }, status=status.HTTP_200_OK)

    @extend_schema(
        tags=['User Management'],
        summary='Update User',
        description='Update user information',
        request=UserUpdateSerializer,
        examples=[
            OpenApiExample(
                'Update Request',
                value={
                    'first_name': 'John',
                    'last_name': 'Doe',
                    'email': 'john.doe@example.com',
                    'user_type': 'manager'
                },
                request_only=True,
            ),
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'User updated successfully',
                    'data': {
                        'user': {
                            'id': 1,
                            'username': 'john_doe',
                            'email': 'john.doe@example.com',
                            'first_name': 'John',
                            'last_name': 'Doe',
                            'user_type': 'manager'
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def put(self, request, user_id):
        # Check permissions
        if request.user.user_type not in ['admin', 'manager']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.UserUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserServices.update_user(user_id, **serializer.validated_data)
            user_data = UserSelectors.get_user_profile_data(user)
            
            return Response({
                'success': True,
                'message': 'User updated successfully',
                'data': {'user': user_data}
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        tags=['User Management'],
        summary='Delete User',
        description='Deactivate user (soft delete)',
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'message': 'User deactivated successfully'
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT}
    )
    def delete(self, request, user_id):
        # Only admins can delete users
        if request.user.user_type != 'admin':
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        try:
            UserServices.delete_user(user_id)
            return Response({
                'success': True,
                'message': 'User deactivated successfully'
            }, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserCreateApiView(APIView):
    """
    Create a new user
    """
    permission_classes = [IsAuthenticated]

    class UserCreateSerializer(serializers.Serializer):
        username = serializers.CharField(max_length=150)
        email = serializers.EmailField()
        password = serializers.CharField(write_only=True, min_length=8)
        first_name = serializers.CharField(max_length=30, required=False)
        last_name = serializers.CharField(max_length=30, required=False)
        user_type = serializers.ChoiceField(
            choices=[('customer', 'Customer'), ('manager', 'Manager'), ('admin', 'Admin')],
            default='customer'
        )
        telegram_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
        telegram_username = serializers.CharField(max_length=100, required=False, allow_blank=True)
        telegram_access = serializers.BooleanField(default=False)

    @extend_schema(
        tags=['User Management'],
        summary='Create User',
        description='Create a new user account',
        request=UserCreateSerializer,
        examples=[
            OpenApiExample(
                'Create User Request',
                value={
                    'username': 'new_user',
                    'email': 'newuser@example.com',
                    'password': 'secure_password123',
                    'first_name': 'New',
                    'last_name': 'User',
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
                    'message': 'User created successfully',
                    'data': {
                        'user': {
                            'id': 5,
                            'username': 'new_user',
                            'email': 'newuser@example.com',
                            'first_name': 'New',
                            'last_name': 'User',
                            'user_type': 'customer',
                            'is_active': True
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def post(self, request):
        # Only admins and managers can create users
        if request.user.user_type not in ['admin', 'manager']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = self.UserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = UserServices.create_user(**serializer.validated_data)
            user_data = UserSelectors.get_user_profile_data(user)
            
            return Response({
                'success': True,
                'message': 'User created successfully',
                'data': {'user': user_data}
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class UserStatsApiView(APIView):
    """
    Get user statistics
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User Management'],
        summary='User Statistics',
        description='Get user statistics including counts by type and status',
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'data': {
                        'stats': {
                            'total_users': 100,
                            'active_users': 85,
                            'inactive_users': 15,
                            'user_type_counts': {
                                'customer': 60,
                                'manager': 20,
                                'admin': 5
                            }
                        }
                    }
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        # Only admins and managers can view stats
        if request.user.user_type not in ['admin', 'manager']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        stats = UserSelectors.get_users_stats()
        return Response({
            'success': True,
            'data': {'stats': stats}
        }, status=status.HTTP_200_OK)


class UserSearchApiView(APIView):
    """
    Search users
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['User Management'],
        summary='Search Users',
        description='Search users by username, email, or names',
        parameters=[
            OpenApiParameter('q', OpenApiTypes.STR, description='Search query', required=True),
            OpenApiParameter('limit', OpenApiTypes.INT, description='Maximum results (default: 10)'),
        ],
        examples=[
            OpenApiExample(
                'Success Response',
                value={
                    'success': True,
                    'data': {
                        'users': [
                            {
                                'id': 1,
                                'username': 'john_doe',
                                'email': 'john@example.com',
                                'first_name': 'John',
                                'last_name': 'Doe',
                                'user_type': 'customer'
                            }
                        ]
                    }
                },
                response_only=True,
            )
        ],
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT}
    )
    def get(self, request):
        # Check permissions
        if request.user.user_type not in ['admin', 'manager']:
            return Response({
                'success': False,
                'message': 'Permission denied'
            }, status=status.HTTP_403_FORBIDDEN)

        query = request.query_params.get('q')
        if not query:
            return Response({
                'success': False,
                'message': 'Search query is required'
            }, status=status.HTTP_400_BAD_REQUEST)

        limit = int(request.query_params.get('limit', 10))
        users = UserSelectors.search_users(query, limit)
        
        users_data = []
        for user in users:
            users_data.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'user_type': user.user_type
            })

        return Response({
            'success': True,
            'data': {'users': users_data}
        }, status=status.HTTP_200_OK)