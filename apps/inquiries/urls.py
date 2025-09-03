from django.urls import path

from .apis import (
    DashboardKPIApiView,
    InquiryCreateApiView,
    InquiryDeleteApiView,
    InquiryDetailApiView,
    InquiryFailedApiView,
    InquiryKPILockApiView,
    InquiryListApiView,
    # KPI Actions
    InquiryQuoteApiView,
    InquiryStatsApiView,
    InquirySuccessApiView,
    InquiryUpdateApiView,
    # KPI Weights APIs
    KPIWeightsApiView,
    KPIWeightsUpdateApiView,
    # KPI APIs
    ManagerKPIApiView,
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

    # KPI Statistics APIs
    path("kpi/manager/<int:manager_id>/", ManagerKPIApiView.as_view(), name="manager-kpi"),
    path("kpi/dashboard/", DashboardKPIApiView.as_view(), name="dashboard-kpi"),

    # KPI Action APIs
    path("<int:inquiry_id>/quote/", InquiryQuoteApiView.as_view(), name="inquiry-quote"),
    path("<int:inquiry_id>/success/", InquirySuccessApiView.as_view(), name="inquiry-success"),
    path("<int:inquiry_id>/failed/", InquiryFailedApiView.as_view(), name="inquiry-failed"),
    path("<int:inquiry_id>/kpi-lock/", InquiryKPILockApiView.as_view(), name="inquiry-kpi-lock"),

    # KPI Weights Management APIs
    path("kpi/weights/", KPIWeightsApiView.as_view(), name="kpi-weights"),
    path("kpi/weights/update/", KPIWeightsUpdateApiView.as_view(), name="kpi-weights-update"),
]

urlpatterns = inquiry_patterns
