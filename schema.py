from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRecord(Base):
    """SQLAlchemy model for persistent user accounts."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="Viewer")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    files = relationship("FileRecord", back_populates="uploader", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogRecord", back_populates="user")

    def __repr__(self):
        return f"<UserRecord {self.username} [{self.role}]>"


class FileRecord(Base):
    """SQLAlchemy model for stored encrypted files."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes before encryption
    mime_type = Column(String(100), nullable=False, default="application/octet-stream")
    uploader_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checksum = Column(String(64), nullable=False)  # SHA-256 hex checksum of original content
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)

    uploader = relationship("UserRecord", back_populates="files")

    def __repr__(self):
        return f"<FileRecord {self.original_filename} (id={self.id})>"


class AuditLogRecord(Base):
    """SQLAlchemy model for system security audit trail."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username = Column(String(64), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=utcnow, nullable=False, index=True)

    user = relationship("UserRecord", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLogRecord {self.action} by {self.username} at {self.timestamp}>"
