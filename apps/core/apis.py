import logging

from django.db import connection
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class HealthCheckApiView(APIView):
    """
    Health check endpoint for monitoring and load balancers
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health Check"],
        summary="Health Check",
        description="Check the health status of the API service",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "version": {"type": "string"},
                    "checks": {
                        "type": "object",
                        "properties": {
                            "database": {"type": "string"},
                            "redis": {"type": "string"},
                        },
                    },
                },
            }
        },
    )
    def get(self, request):
        """
        Perform health checks and return system status
        """
        health_data = {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
            "version": "1.0.0",
            "checks": {},
        }

        # Database health check
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                health_data["checks"]["database"] = "healthy"
        except Exception as e:
            health_data["checks"]["database"] = f"unhealthy: {str(e)}"
            health_data["status"] = "unhealthy"
            logger.error(f"Database health check failed: {str(e)}")

        # Return appropriate status code
        status_code = (
            status.HTTP_200_OK
            if health_data["status"] == "healthy"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )

        return Response(health_data, status=status_code)


class ReadinessCheckApiView(APIView):
    """
    Readiness check endpoint for Kubernetes/Docker deployments
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health Check"],
        summary="Readiness Check",
        description="Check if the API service is ready to serve requests",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "ready": {"type": "boolean"},
                },
            }
        },
    )
    def get(self, request):
        """
        Simple readiness check
        """
        return Response({"status": "ready", "ready": True}, status=status.HTTP_200_OK)


class LivenessCheckApiView(APIView):
    """
    Liveness check endpoint for Kubernetes/Docker deployments
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health Check"],
        summary="Liveness Check",
        description="Check if the API service is alive and running",
        responses={
            200: {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "alive": {"type": "boolean"},
                },
            }
        },
    )
    def get(self, request):
        """
        Simple liveness check
        """
        return Response({"status": "alive", "alive": True}, status=status.HTTP_200_OK)
