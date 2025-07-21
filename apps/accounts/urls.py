from django.urls import path

from .apis import (
    UserCreateApiView,
    UserDeleteApiView,
    UserDetailApiView,
    UserListApiView,
    UserSearchApiView,
    UserStatsApiView,
    UserUpdateApiView,
)

app_name = "accounts"

# Django Styleguide compliant URL patterns
# Following the pattern: 1 URL per API operation
user_patterns = [
    # User list and create operations
    path("", UserListApiView.as_view(), name="list"),
    path("create/", UserCreateApiView.as_view(), name="create"),
    # User detail operations
    path("<int:user_id>/", UserDetailApiView.as_view(), name="detail"),
    path("<int:user_id>/update/", UserUpdateApiView.as_view(), name="update"),
    path("<int:user_id>/delete/", UserDeleteApiView.as_view(), name="delete"),
    # User utility operations
    path("search/", UserSearchApiView.as_view(), name="search"),
    path("stats/", UserStatsApiView.as_view(), name="stats"),
]

urlpatterns = user_patterns
