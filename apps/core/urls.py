from django.urls import path

from .apis import HealthCheckApiView, LivenessCheckApiView, ReadinessCheckApiView

app_name = "core"

urlpatterns = [
    # Health check endpoints
    path("health/", HealthCheckApiView.as_view(), name="health-check"),
    path("ready/", ReadinessCheckApiView.as_view(), name="readiness-check"),
    path("alive/", LivenessCheckApiView.as_view(), name="liveness-check"),
]
