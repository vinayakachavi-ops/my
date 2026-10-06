from app.routes.auth_routes import auth_bp
from app.routes.dashboard_routes import dashboard_bp
from app.routes.file_routes import file_bp
from app.routes.admin_routes import admin_bp

__all__ = ["auth_bp", "dashboard_bp", "file_bp", "admin_bp"]
