from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from app.services.auth_service import AuthService
from app.services.user_manager import UserManager
from app.services.audit_service import AuditService
from app.database.connection import db_session
from app.core.exceptions import AuthenticationError, ValidationError

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def get_auth_services():
    user_mgr = UserManager(db_session)
    auth_srv = AuthService(user_mgr)
    audit_srv = AuditService(db_session)
    return user_mgr, auth_srv, audit_srv


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if getattr(g, "current_user", None):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        ip_addr = request.remote_addr
        user_agent = request.user_agent.string

        _, auth_srv, audit_srv = get_auth_services()

        try:
            user = auth_srv.authenticate(identifier, password)
            session.clear()
            session["user_id"] = user.id
            session.permanent = True

            audit_srv.log(
                action="LOGIN_SUCCESS",
                user_id=user.id,
                username=user.username,
                ip_address=ip_addr,
                user_agent=user_agent,
                details=f"User '{user.username}' ({user.role}) logged in successfully."
            )

            flash(f"Welcome back, {user.username}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))

        except AuthenticationError as e:
            audit_srv.log(
                action="LOGIN_FAILED",
                username=identifier,
                ip_address=ip_addr,
                user_agent=user_agent,
                details=f"Failed login attempt for identifier '{identifier}': {str(e)}"
            )
            flash(str(e), "danger")

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if getattr(g, "current_user", None):
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        ip_addr = request.remote_addr
        user_agent = request.user_agent.string

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html", username=username, email=email)

        _, auth_srv, audit_srv = get_auth_services()

        try:
            # New registrations always default to Viewer role
            new_user = auth_srv.register(
                username=username,
                email=email,
                password=password,
                role="Viewer"
            )

            audit_srv.log(
                action="USER_REGISTERED",
                user_id=new_user.id,
                username=new_user.username,
                ip_address=ip_addr,
                user_agent=user_agent,
                details=f"New user '{new_user.username}' registered as Viewer."
            )

            flash("Registration successful! You may now log in with your credentials.", "success")
            return redirect(url_for("auth.login"))

        except (ValidationError, Exception) as e:
            flash(str(e), "danger")
            return render_template("auth/register.html", username=username, email=email)

    return render_template("auth/register.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    user = getattr(g, "current_user", None)
    if user:
        _, _, audit_srv = get_auth_services()
        audit_srv.log(
            action="LOGOUT",
            user_id=user.id,
            username=user.username,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string,
            details=f"User '{user.username}' logged out."
        )

    session.clear()
    flash("You have been logged out securely.", "info")
    return redirect(url_for("auth.login"))
