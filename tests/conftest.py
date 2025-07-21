"""
Global pytest configuration and fixtures for business-focused testing.
"""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """
    Fixture to provide DRF API client for business flow testing.
    """
    return APIClient()
