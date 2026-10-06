from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.schema import UserRecord
from app.core.models import User, UserFactory
from app.core.exceptions import UserManagementError, ValidationError


class UserManager:
    """
    UserManager provides CRUD operations for users, persisting state to SQLite via SQLAlchemy
    and returning polymorphic domain User models (Viewer, Editor, Admin).
    """

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def to_domain_user(record: UserRecord) -> User:
        """Convert a database UserRecord into a polymorphic User domain object."""
        return UserFactory.create_user(
            role=record.role,
            id=record.id,
            username=record.username,
            email=record.email,
            password_hash=record.password_hash,
            is_active=record.is_active
        )

    def create_user(
        self,
        username: str,
        email: str,
        password_hash: str,
        role: str = "Viewer",
        is_active: bool = True
    ) -> User:
        """
        Create a new user account in the database.
        
        :raises ValidationError: If username or email already exists.
        """
        existing_username = self.session.query(UserRecord).filter_by(username=username).first()
        if existing_username:
            raise ValidationError(f"Username '{username}' is already taken.")

        existing_email = self.session.query(UserRecord).filter_by(email=email).first()
        if existing_email:
            raise ValidationError(f"Email '{email}' is already registered.")

        if role not in ("Admin", "Editor", "Viewer"):
            raise ValidationError(f"Invalid role '{role}'. Permitted roles: Admin, Editor, Viewer.")

        record = UserRecord(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return self.to_domain_user(record)

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch a user by primary key ID and return polymorphic User."""
        record = self.session.query(UserRecord).filter_by(id=user_id).first()
        return self.to_domain_user(record) if record else None

    def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by username."""
        record = self.session.query(UserRecord).filter_by(username=username).first()
        return self.to_domain_user(record) if record else None

    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch a user by email address."""
        record = self.session.query(UserRecord).filter_by(email=email).first()
        return self.to_domain_user(record) if record else None

    def list_all_users(self) -> List[User]:
        """List all users ordered by creation date."""
        records = self.session.query(UserRecord).order_by(UserRecord.created_at.asc()).all()
        return [self.to_domain_user(r) for r in records]

    def update_user(
        self,
        user_id: int,
        email: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> User:
        """
        Update user attributes (email, role, active status).
        Cannot delete users per application security specification.
        """
        record = self.session.query(UserRecord).filter_by(id=user_id).first()
        if not record:
            raise UserManagementError(f"User with ID {user_id} not found.")

        if email and email != record.email:
            existing = self.session.query(UserRecord).filter_by(email=email).first()
            if existing:
                raise ValidationError(f"Email '{email}' is already in use by another user.")
            record.email = email

        if role:
            if role not in ("Admin", "Editor", "Viewer"):
                raise ValidationError(f"Invalid role '{role}'. Permitted: Admin, Editor, Viewer.")
            record.role = role

        if is_active is not None:
            record.is_active = bool(is_active)

        self.session.commit()
        self.session.refresh(record)
        return self.to_domain_user(record)

    def toggle_active_status(self, user_id: int, requesting_user_id: Optional[int] = None) -> User:
        """
        Toggle active/deactivated status. Prevents admin self-lockout.
        """
        record = self.session.query(UserRecord).filter_by(id=user_id).first()
        if not record:
            raise UserManagementError(f"User with ID {user_id} not found.")

        if requesting_user_id and record.id == requesting_user_id and record.is_active:
            raise UserManagementError("You cannot deactivate your own administrative account.")

        record.is_active = not record.is_active
        self.session.commit()
        self.session.refresh(record)
        return self.to_domain_user(record)
