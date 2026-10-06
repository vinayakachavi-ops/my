from abc import ABC, abstractmethod


class Permissions(ABC):
    """
    Abstract interface defining the role-based permission contract.
    Enforces that every role/user subclass provides concrete boolean
    checks for core system capabilities.
    """

    @abstractmethod
    def can_upload(self) -> bool:
        """Determines if the user can upload new files."""
        pass

    @abstractmethod
    def can_view(self) -> bool:
        """Determines if the user can view/list/preview files."""
        pass

    @abstractmethod
    def can_download(self) -> bool:
        """Determines if the user can download decrypted files."""
        pass

    @abstractmethod
    def can_manage_users(self) -> bool:
        """Determines if the user can create, update, or deactivate accounts."""
        pass

    @abstractmethod
    def can_assign_roles(self) -> bool:
        """Determines if the user can modify user access roles."""
        pass
