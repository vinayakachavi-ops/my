import re
import bcrypt
from typing import Tuple, Optional
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.models import User
from app.services.user_manager import UserManager


class AuthService:
    """
    AuthService handles user registration, credential validation, bcrypt hashing,
    and login authentication. Enforces strict password complexity policies.
    """

    # Password complexity: min 8 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special character
    PASSWORD_PATTERN = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#^()_\-+=\[\]{}|:;<>,./?~`])[A-Za-z\d@$!%*?&#^()_\-+=\[\]{}|:;<>,./?~`]{8,}$"
    )
    USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")
    EMAIL_PATTERN = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")

    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager

    @classmethod
    def hash_password(cls, plain_password: str) -> str:
        """Hash a plaintext password using bcrypt with automatic salt generation."""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @classmethod
    def verify_password(cls, plain_password: str, password_hash: str) -> bool:
        """Verify plaintext password against bcrypt hash."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
        except Exception:
            return False

    @classmethod
    def validate_password_strength(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password against security policy:
        - Minimum 8 characters
        - At least 1 lowercase letter
        - At least 1 uppercase letter
        - At least 1 digit
        - At least 1 special character
        """
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r"[a-z]", password):
            return False, "Password must include at least one lowercase letter."
        if not re.search(r"[A-Z]", password):
            return False, "Password must include at least one uppercase letter."
        if not re.search(r"\d", password):
            return False, "Password must include at least one numeric digit."
        if not re.search(r"[@$!%*?&#^()_\-+=\[\]{}|:;<>,./?~`]", password):
            return False, "Password must include at least one special character (e.g. !@#$%^&*)."
        return True, "Password meets complexity requirements."

    @classmethod
    def validate_username(cls, username: str) -> Tuple[bool, str]:
        """Validate username format (alphanumeric, underscores, hyphens, 3-32 chars)."""
        if not username or not cls.USERNAME_PATTERN.match(username):
            return False, "Username must be 3-32 characters long and contain only letters, numbers, hyphens, or underscores."
        return True, "Username is valid."

    @classmethod
    def validate_email(cls, email: str) -> Tuple[bool, str]:
        """Validate email format."""
        if not email or not cls.EMAIL_PATTERN.match(email):
            return False, "Please enter a valid email address."
        return True, "Email is valid."

    def register(
        self,
        username: str,
        email: str,
        password: str,
        role: str = "Viewer"
    ) -> User:
        """
        Register a new user account.
        New users default to the 'Viewer' role.
        """
        u_valid, u_msg = self.validate_username(username)
        if not u_valid:
            raise ValidationError(u_msg)

        e_valid, e_msg = self.validate_email(email)
        if not e_valid:
            raise ValidationError(e_msg)

        p_valid, p_msg = self.validate_password_strength(password)
        if not p_valid:
            raise ValidationError(p_msg)

        password_hash = self.hash_password(password)
        return self.user_manager.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True
        )

    def authenticate(self, identifier: str, password: str) -> User:
        """
        Authenticate a user by username or email.
        
        :raises AuthenticationError: If credentials invalid or account deactivated.
        """
        identifier = (identifier or "").strip()
        if not identifier or not password:
            raise AuthenticationError("Username/Email and Password are required.")

        user = self.user_manager.get_by_username(identifier)
        if not user:
            user = self.user_manager.get_by_email(identifier)

        if not user:
            raise AuthenticationError("Invalid username or password.")

        if not self.verify_password(password, user.password_hash):
            raise AuthenticationError("Invalid username or password.")

        if not user.is_active:
            raise AuthenticationError("Your account has been deactivated. Please contact an administrator.")

        return user
