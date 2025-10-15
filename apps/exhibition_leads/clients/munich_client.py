"""Munich Exhibition API Client"""

import logging

import requests
from django.conf import settings

from .auth_manager import MunichAuthManager
from .exceptions import (
    MunichAPIConnectionError,
    MunichAPIException,
    MunichAPINotFoundError,
    MunichAPITimeoutError,
    MunichAPIValidationError,
)

logger = logging.getLogger(__name__)


class MunichExhibitionClient:
    """Client for interacting with Munich Exhibition API"""

    def __init__(self):
        self.base_url = settings.MUNICH_API_BASE_URL.rstrip("/")
        self.timeout = settings.MUNICH_API_TIMEOUT
        self.auth_manager = MunichAuthManager()

    def _get_headers(self):
        """Get request headers with authentication"""
        token = self.auth_manager.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response):
        """Handle API response and raise appropriate exceptions"""
        if response.status_code == 200 or response.status_code == 201:
            return response.json()
        elif response.status_code == 204:
            return None
        elif response.status_code == 404:
            raise MunichAPINotFoundError("Resource not found")
        elif response.status_code == 400:
            raise MunichAPIValidationError(response.json())
        else:
            raise MunichAPIException(
                f"API error: {response.status_code} - {response.text}"
            )

    # ==================== LEAD OPERATIONS ====================

    def list_leads(self, params: dict | None = None) -> dict:
        """
        Get list of leads from Munich API

        Args:
            params: Query parameters (search, category_id, importance, company_type, mode_of_transport, page, page_size)
                   - Supports multiple values for: category_id, importance, company_type, mode_of_transport

        Returns:
            Dict with 'count', 'next', 'previous', 'results'
        """
        url = f"{self.base_url}/api/leads/list/"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                params=params or {},
                timeout=self.timeout,
            )
            logger.info(f"Listed leads with params: {params}")
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def get_lead(self, lead_id: int) -> dict:
        """
        Get single lead details

        Args:
            lead_id: Lead ID in Munich API

        Returns:
            Lead object
        """
        url = f"{self.base_url}/api/leads/{lead_id}/"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            logger.info(f"Retrieved lead {lead_id}")
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def create_lead(self, data: dict) -> dict:
        """
        Create new lead in Munich API

        Args:
            data: Lead data (full_name, company_name, position, etc.)

        Returns:
            Created lead object
        """
        url = f"{self.base_url}/api/leads/create/"

        try:
            response = requests.post(
                url, headers=self._get_headers(), json=data, timeout=self.timeout
            )
            logger.info(f"Created lead: {data.get('full_name', 'Unknown')}")
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def update_lead(self, lead_id: int, data: dict) -> dict:
        """
        Update existing lead in Munich API

        Args:
            lead_id: Lead ID to update
            data: Updated lead data

        Returns:
            Updated lead object
        """
        url = f"{self.base_url}/api/leads/{lead_id}/update/"

        try:
            response = requests.put(
                url, headers=self._get_headers(), json=data, timeout=self.timeout
            )
            logger.info(f"Updated lead {lead_id}")
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def delete_lead(self, lead_id: int) -> bool:
        """
        Delete lead from Munich API

        Args:
            lead_id: Lead ID to delete

        Returns:
            True if successful
        """
        url = f"{self.base_url}/api/leads/{lead_id}/delete/"

        try:
            response = requests.delete(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            logger.info(f"Deleted lead {lead_id}")
            return response.status_code == 204

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    # ==================== REFERENCE DATA ====================

    def get_categories(self) -> list[dict]:
        """Get list of lead categories"""
        url = f"{self.base_url}/api/leads/categories/"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            data = self._handle_response(response)
            return data.get("results", []) if isinstance(data, dict) else data

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def get_shipment_directions(self) -> list[dict]:
        """Get list of shipment directions"""
        url = f"{self.base_url}/api/leads/shipment-directions/"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")

    def get_companies(self) -> list[dict]:
        """Get list of companies"""
        url = f"{self.base_url}/api/companies/list/"

        try:
            response = requests.get(
                url, headers=self._get_headers(), timeout=self.timeout
            )
            return self._handle_response(response)

        except requests.exceptions.Timeout:
            raise MunichAPITimeoutError("Request timed out")
        except requests.exceptions.RequestException as e:
            raise MunichAPIConnectionError(f"Connection error: {str(e)}")
