from abc import ABC
from typing import Optional, Dict, Any, Type
from app.core.permissions import Permissions


class User(Permissions, ABC):
    """
    Abstract base class representing a user within SecureShare.
    Inherits from the Permissions interface to guarantee polymorphic
    permission methods across all role subclasses.
    """

    def __init__(
        self,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        role: str,
        is_active: bool = True
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active

    def to_dict(self) -> Dict[str, Any]:
        """Serialize user details along with evaluated permissions."""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "permissions": {
                "can_upload": self.can_upload(),
                "can_view": self.can_view(),
                "can_download": self.can_download(),
                "can_manage_users": self.can_manage_users(),
                "can_assign_roles": self.can_assign_roles()
            }
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id}, username='{self.username}', role='{self.role}', active={self.is_active})>"


class Viewer(User):
    """
    Viewer role: Base authenticated tier.
    Permitted to view and download files only.
    Cannot upload files, manage users, or assign roles.
    """

    def __init__(
        self,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        role: str = "Viewer",
        is_active: bool = True
    ):
        super().__init__(
            id=id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )

    def can_upload(self) -> bool:
        return False

    def can_view(self) -> bool:
        return True

    def can_download(self) -> bool:
        return True

    def can_manage_users(self) -> bool:
        return False

    def can_assign_roles(self) -> bool:
        return False


class Editor(Viewer):
    """
    Editor role: Inherits view and download permissions from Viewer,
    and extends capabilities by enabling file uploads.
    Cannot manage users or assign roles.
    """

    def __init__(
        self,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        role: str = "Editor",
        is_active: bool = True
    ):
        super().__init__(
            id=id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )

    def can_upload(self) -> bool:
        return True


class Admin(Editor):
    """
    Admin role: Inherits view, download, and upload permissions from Editor,
    and extends capabilities by enabling user management and role assignment.
    """

    def __init__(
        self,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        role: str = "Admin",
        is_active: bool = True
    ):
        super().__init__(
            id=id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )

    def can_manage_users(self) -> bool:
        return True

    def can_assign_roles(self) -> bool:
        return True


class UserFactory:
    """
    Factory class responsible for instantiating polymorphic User objects
    based on the role string.
    """

    _ROLE_MAP: Dict[str, Type[User]] = {
        "Viewer": Viewer,
        "Editor": Editor,
        "Admin": Admin
    }

    @classmethod
    def create_user(
        cls,
        role: str,
        id: Optional[int],
        username: str,
        email: str,
        password_hash: str,
        is_active: bool = True
    ) -> User:
        """Instantiate the concrete User subclass corresponding to the specified role."""
        subclass = cls._ROLE_MAP.get(role)
        if not subclass:
            # Default fallback to Viewer for safe access control
            subclass = Viewer
            role = "Viewer"
        return subclass(
            id=id,
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )
