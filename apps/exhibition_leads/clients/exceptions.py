"""Custom exceptions for Munich Exhibition API client"""


class MunichAPIException(Exception):
    """Base exception for Munich API errors"""

    pass


class MunichAuthenticationError(MunichAPIException):
    """Authentication failed"""

    pass


class MunichAPIConnectionError(MunichAPIException):
    """Connection to Munich API failed"""

    pass


class MunichAPITimeoutError(MunichAPIException):
    """Request to Munich API timed out"""

    pass


class MunichAPINotFoundError(MunichAPIException):
    """Resource not found in Munich API"""

    pass


class MunichAPIValidationError(MunichAPIException):
    """Validation error from Munich API"""

    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"Validation errors: {errors}")
