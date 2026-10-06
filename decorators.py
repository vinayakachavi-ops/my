import functools
import secrets
from flask import session, redirect, url_for, flash, request, abort, g, render_template
from app.core.models import User
from app.core.exceptions import PermissionDeniedError


def get_current_user() -> User | None:
    """Retrieve the polymorphic User domain object stored in Flask's g context."""
    return getattr(g, "current_user", None)


def generate_csrf_token() -> str:
    """Generate or retrieve a per-session CSRF token."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf():
    """Verify CSRF token for state-altering HTTP methods."""
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Allow token from form or header
        sent_token = request.form.get("csrf_token") or request.headers.get("X-CSRFToken")
        session_token = session.get("_csrf_token")
        if not session_token or not sent_token or not secrets.compare_digest(session_token, sent_token):
            abort(400, description="Invalid or missing CSRF token.")


def login_required(f):
    """
    Decorator requiring an active authenticated user.
    Redirects unauthenticated visitors to login.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        if not user.is_active:
            flash("Your account has been deactivated. Please contact an administrator.", "danger")
            session.clear()
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated_function


def require_permission(permission_name: str):
    """
    Polymorphic permission enforcement decorator.
    
    Calls the corresponding abstract permission method directly on the concrete
    User subclass instance (Viewer, Editor, Admin) without any hardcoded role conditionals:
    - 'upload'        -> user.can_upload()
    - 'view'          -> user.can_view()
    - 'download'      -> user.can_download()
    - 'manage_users'  -> user.can_manage_users()
    - 'assign_roles'  -> user.can_assign_roles()
    """
    PERMISSION_METHOD_MAP = {
        "upload": "can_upload",
        "view": "can_view",
        "download": "can_download",
        "manage_users": "can_manage_users",
        "assign_roles": "can_assign_roles",
    }

    method_name = PERMISSION_METHOD_MAP.get(permission_name)
    if not method_name:
        raise ValueError(f"Unknown permission check: '{permission_name}'")

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth.login", next=request.path))

            if not user.is_active:
                flash("Your account is deactivated.", "danger")
                session.clear()
                return redirect(url_for("auth.login"))

            # Polymorphic check: invoking method directly on User subclass
            check_func = getattr(user, method_name, None)
            if not callable(check_func) or not check_func():
                # Raise PermissionDeniedError to trigger the dedicated 403 page
                raise PermissionDeniedError(
                    message=f"Access Denied: Your account role ({user.role}) does not have '{permission_name}' permission.",
                    required_permission=permission_name
                )

            return f(*args, **kwargs)
        return decorated_function
    return decorator
