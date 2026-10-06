class SecureShareException(Exception):
    """Base exception for SecureShare application errors."""
    pass


class AuthenticationError(SecureShareException):
    """Raised when authentication credentials or state are invalid."""
    pass


class PermissionDeniedError(SecureShareException):
    """Raised when an action violates the user's role permissions."""
    def __init__(self, message: str = "Access Denied: You lack the required permission to perform this action.", required_permission: str = None):
        super().__init__(message)
        self.required_permission = required_permission


class ValidationError(SecureShareException):
    """Raised when input data validation fails."""
    pass


class EncryptionError(SecureShareException):
    """Raised when file encryption or decryption fails."""
    pass


class UserManagementError(SecureShareException):
    """Raised when a user management operation fails."""
    pass


class FileManagementError(SecureShareException):
    """Raised when a file storage or retrieval operation fails."""
    pass
