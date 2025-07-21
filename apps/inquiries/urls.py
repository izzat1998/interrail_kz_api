from django.urls import path

from .apis import (
    InquiryCreateApiView,
    InquiryDeleteApiView,
    InquiryDetailApiView,
    InquiryListApiView,
    InquiryStatsApiView,
    InquiryUpdateApiView,
)

app_name = "inquiries"

# Django Styleguide compliant URL patterns
# Following the pattern: 1 URL per API operation
inquiry_patterns = [
    # Inquiry list and create operations
    path("", InquiryListApiView.as_view(), name="inquiry-list"),
    path("create/", InquiryCreateApiView.as_view(), name="inquiry-create"),
    # Inquiry detail operations
    path("<int:inquiry_id>/", InquiryDetailApiView.as_view(), name="inquiry-detail"),
    path(
        "<int:inquiry_id>/update/",
        InquiryUpdateApiView.as_view(),
        name="inquiry-update",
    ),
    path(
        "<int:inquiry_id>/delete/",
        InquiryDeleteApiView.as_view(),
        name="inquiry-delete",
    ),
    # Inquiry utility operations
    path("stats/", InquiryStatsApiView.as_view(), name="inquiry-stats"),
]

urlpatterns = inquiry_patterns
