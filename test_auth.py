import pytest
from app.services.auth_service import AuthService
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.models import Viewer, Admin


class TestAuthService:
    """Test suite verifying user registration, password strength, and authentication."""

    def test_password_strength_validation(self):
        """Verify strict password security policy enforcing length, casing, digits, and special characters."""
        # Too short (< 8 chars)
        ok, msg = AuthService.validate_password_strength("Short1!")
        assert not ok
        assert "at least 8 characters" in msg

        # Missing uppercase
        ok, msg = AuthService.validate_password_strength("nouppercase123!")
        assert not ok
        assert "uppercase" in msg

        # Missing lowercase
        ok, msg = AuthService.validate_password_strength("NOLOWERCASE123!")
        assert not ok
        assert "lowercase" in msg

        # Missing digit
        ok, msg = AuthService.validate_password_strength("NoDigitsHere!@#")
        assert not ok
        assert "digit" in msg

        # Missing special character
        ok, msg = AuthService.validate_password_strength("NoSpecialChar123")
        assert not ok
        assert "special character" in msg

        # Valid strong password
        ok, msg = AuthService.validate_password_strength("P@ssw0rdSecure2026")
        assert ok

    def test_bcrypt_hashing_and_verification(self):
        """Ensure bcrypt salts produce unique hashes and verify correctly."""
        password = "ComplexPassword#99"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        assert hash1 != hash2  # Salt ensures different hashes
        assert AuthService.verify_password(password, hash1) is True
        assert AuthService.verify_password(password, hash2) is True
        assert AuthService.verify_password("WrongPassword#99", hash1) is False

    def test_user_registration_defaults_to_viewer(self, app, auth_service):
        """Newly registered users should automatically default to the Viewer role."""
        user = auth_service.register(
            username="new_member",
            email="member@company.com",
            password="StrongPassword!123"
        )
        assert isinstance(user, Viewer)
        assert user.role == "Viewer"
        assert user.can_upload() is False
        assert user.can_view() is True
        assert user.can_download() is True
        assert user.is_active is True

    def test_authentication_with_username_and_email(self, app, auth_service):
        """Users should be able to authenticate with either username or email."""
        auth_service.register(
            username="dual_auth_user",
            email="dual@company.com",
            password="StrongPassword!123"
        )

        # Authenticate via username
        user1 = auth_service.authenticate("dual_auth_user", "StrongPassword!123")
        assert user1.username == "dual_auth_user"

        # Authenticate via email
        user2 = auth_service.authenticate("dual@company.com", "StrongPassword!123")
        assert user2.username == "dual_auth_user"

    def test_authentication_invalid_credentials(self, app, auth_service):
        """Authentication must fail with bad password or unknown user."""
        with pytest.raises(AuthenticationError):
            auth_service.authenticate("nonexistent", "SomePassword!1")

    def test_deactivated_user_cannot_login(self, app, auth_service, user_manager):
        """Deactivated users must be blocked from logging in."""
        user = auth_service.register(
            username="suspended_user",
            email="suspended@company.com",
            password="StrongPassword!123"
        )

        # Deactivate user
        user_manager.toggle_active_status(user.id)

        with pytest.raises(AuthenticationError) as exc_info:
            auth_service.authenticate("suspended_user", "StrongPassword!123")
        assert "deactivated" in str(exc_info.value).lower()
