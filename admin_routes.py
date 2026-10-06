from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from app.routes.decorators import login_required, require_permission
from app.database.connection import db_session
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.core.exceptions import ValidationError, UserManagementError

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def get_admin_services():
    user_mgr = UserManager(db_session)
    auth_srv = AuthService(user_mgr)
    audit_srv = AuditService(db_session)
    return user_mgr, auth_srv, audit_srv


@admin_bp.route("/", methods=["GET"])
@login_required
@require_permission("manage_users")
def index():
    """Admin dashboard showing user management table and security audit log."""
    user_mgr, _, audit_srv = get_admin_services()
    users = user_mgr.list_all_users()
    logs = audit_srv.list_recent_logs(limit=150)
    
    return render_template(
        "admin/index.html",
        users=users,
        logs=logs,
        current_admin=g.current_user
    )


@admin_bp.route("/users/create", methods=["POST"])
@login_required
@require_permission("manage_users")
def create_user():
    """Admin creates a new user account with specified role."""
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "Viewer")

    _, auth_srv, audit_srv = get_admin_services()

    try:
        new_user = auth_srv.register(
            username=username,
            email=email,
            password=password,
            role=role
        )

        audit_srv.log(
            action="USER_CREATED",
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Admin '{g.current_user.username}' created new user '{new_user.username}' with role '{role}'."
        )

        flash(f"User account '{new_user.username}' ({role}) created successfully.", "success")
    except (ValidationError, Exception) as e:
        flash(f"Failed to create user: {str(e)}", "danger")

    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@login_required
@require_permission("assign_roles")
def change_role(user_id: int):
    """Admin assigns a new role to an existing user."""
    new_role = request.form.get("role", "").strip()
    user_mgr, _, audit_srv = get_admin_services()

    try:
        target_user = user_mgr.get_by_id(user_id)
        if not target_user:
            flash("User not found.", "danger")
            return redirect(url_for("admin.index"))

        # Prevent admin from demoting themselves if it would remove all admins
        if target_user.id == g.current_user.id and new_role != "Admin":
            all_users = user_mgr.list_all_users()
            admin_count = sum(1 for u in all_users if u.role == "Admin" and u.is_active)
            if admin_count <= 1:
                flash("Cannot demote the only remaining active Administrator.", "danger")
                return redirect(url_for("admin.index"))

        old_role = target_user.role
        updated_user = user_mgr.update_user(user_id=user_id, role=new_role)

        audit_srv.log(
            action="ROLE_CHANGED",
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Admin '{g.current_user.username}' updated role of user '{updated_user.username}' from '{old_role}' to '{new_role}'."
        )

        flash(f"Role for user '{updated_user.username}' updated to '{new_role}'.", "success")
    except (ValidationError, UserManagementError) as e:
        flash(f"Failed to update role: {str(e)}", "danger")

    return redirect(url_for("admin.index"))


@admin_bp.route("/users/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@require_permission("manage_users")
def toggle_status(user_id: int):
    """Admin toggles activation status (active <-> deactivated). Deactivated users cannot log in."""
    user_mgr, _, audit_srv = get_admin_services()

    try:
        updated_user = user_mgr.toggle_active_status(
            user_id=user_id,
            requesting_user_id=g.current_user.id
        )

        status_text = "activated" if updated_user.is_active else "deactivated"
        action_name = "USER_ACTIVATED" if updated_user.is_active else "USER_DEACTIVATED"

        audit_srv.log(
            action=action_name,
            user_id=g.current_user.id,
            username=g.current_user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"Admin '{g.current_user.username}' {status_text} user '{updated_user.username}'."
        )

        flash(f"User '{updated_user.username}' has been {status_text}.", "success")
    except UserManagementError as e:
        flash(str(e), "danger")
    except Exception as e:
        flash(f"Status update failed: {str(e)}", "danger")

    return redirect(url_for("admin.index"))
