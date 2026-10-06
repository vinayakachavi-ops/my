from typing import Optional, List
from sqlalchemy.orm import Session
from app.database.schema import AuditLogRecord


class AuditService:
    """
    AuditService logs security-sensitive actions across SecureShare
    including authentications, role assignments, file uploads, and downloads.
    """

    def __init__(self, session: Session):
        self.session = session

    def log(
        self,
        action: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[str] = None
    ) -> AuditLogRecord:
        """Create and commit an audit log entry."""
        record = AuditLogRecord(
            user_id=user_id,
            username=username,
            action=action,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
            details=details
        )
        self.session.add(record)
        self.session.commit()
        return record

    def list_recent_logs(self, limit: int = 100) -> List[AuditLogRecord]:
        """Fetch the most recent audit log entries ordered descending by timestamp."""
        return (
            self.session.query(AuditLogRecord)
            .order_by(AuditLogRecord.timestamp.desc())
            .limit(limit)
            .all()
        )
