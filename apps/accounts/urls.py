from django.urls import path
from .apis import (
    UserListApiView,
    UserDetailApiView,
    UserCreateApiView,
    UserStatsApiView,
    UserSearchApiView,
)

app_name = 'accounts'

urlpatterns = [
    # User CRUD operations
    path('users/', UserListApiView.as_view(), name='user-list'),
    path('users/create/', UserCreateApiView.as_view(), name='user-create'),
    path('users/<int:user_id>/', UserDetailApiView.as_view(), name='user-detail'),
    
    # User utilities
    path('users/search/', UserSearchApiView.as_view(), name='user-search'),
    path('users/stats/', UserStatsApiView.as_view(), name='user-stats'),
]