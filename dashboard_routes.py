from flask import Blueprint, render_template, g, current_app
from app.routes.decorators import login_required
from app.database.connection import db_session
from app.database.schema import FileRecord, UserRecord, AuditLogRecord
from app.services.file_manager import FileManager
from app.services.encryption_service import EncryptionService

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@dashboard_bp.route("/dashboard")
@login_required
def index():
    user = g.current_user

    # Gather high-level stats
    total_files = db_session.query(FileRecord).count()
    my_files_count = db_session.query(FileRecord).filter_by(uploader_id=user.id).count()
    
    total_users = 0
    recent_activity = []
    if user.can_manage_users():
        total_users = db_session.query(UserRecord).count()
        recent_activity = (
            db_session.query(AuditLogRecord)
            .order_by(AuditLogRecord.timestamp.desc())
            .limit(5)
            .all()
        )
    else:
        recent_activity = (
            db_session.query(AuditLogRecord)
            .filter_by(user_id=user.id)
            .order_by(AuditLogRecord.timestamp.desc())
            .limit(5)
            .all()
        )

    # Allowed actions list determined polymorphically via user methods
    allowed_actions = []
    if user.can_view():
        allowed_actions.append({"name": "Browse Files", "desc": "View encrypted document inventory", "url": "/files", "icon": "folder"})
    if user.can_download():
        allowed_actions.append({"name": "Download Files", "desc": "Decrypt and download files in memory", "url": "/files", "icon": "download"})
    if user.can_upload():
        allowed_actions.append({"name": "Upload Files", "desc": "Encrypt and securely store new files", "url": "/files", "icon": "upload"})
    if user.can_manage_users():
        allowed_actions.append({"name": "User Management", "desc": "Manage accounts and access permissions", "url": "/admin", "icon": "users"})
    if user.can_assign_roles():
        allowed_actions.append({"name": "Role Assignment", "desc": "Modify Viewer, Editor, and Admin roles", "url": "/admin", "icon": "shield"})

    return render_template(
        "dashboard.html",
        user=user,
        total_files=total_files,
        my_files_count=my_files_count,
        total_users=total_users,
        recent_activity=recent_activity,
        allowed_actions=allowed_actions
    )
