import os
from app.config import Config
from app.database.connection import init_db, create_all_tables, db_session
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService


def seed_database():
    """Seed initial administrator and demonstration role accounts."""
    print("[*] Initializing SecureShare database schema...")
    init_db(Config.SQLALCHEMY_DATABASE_URI)
    create_all_tables()

    user_mgr = UserManager(db_session)
    auth_srv = AuthService(user_mgr)
    audit_srv = AuditService(db_session)

    accounts = [
        {
            "username": "admin",
            "email": "admin@secureshare.local",
            "password": "Admin@12345",
            "role": "Admin",
            "desc": "System Administrator (Full access, RBAC, User Management)"
        },
        {
            "username": "editor",
            "email": "editor@secureshare.local",
            "password": "Editor@12345",
            "role": "Editor",
            "desc": "Content Editor (Upload, View, Download)"
        },
        {
            "username": "viewer",
            "email": "viewer@secureshare.local",
            "password": "Viewer@12345",
            "role": "Viewer",
            "desc": "Standard Viewer (View and Download only)"
        }
    ]

    print("\n" + "=" * 60)
    print("           SECURSHARE SEED ACCOUNT INITIALIZATION")
    print("=" * 60)

    for acc in accounts:
        existing = user_mgr.get_by_username(acc["username"])
        if existing:
            print(f"[!] Account '{acc['username']}' ({existing.role}) already exists. Skipping.")
            continue

        new_user = auth_srv.register(
            username=acc["username"],
            email=acc["email"],
            password=acc["password"],
            role=acc["role"]
        )

        audit_srv.log(
            action="USER_CREATED",
            user_id=new_user.id,
            username=new_user.username,
            ip_address="127.0.0.1",
            user_agent="SeedScript/1.0",
            details=f"System seed created default {acc['role']} account '{acc['username']}'."
        )

        print(f"[+] Created {acc['role']:<7} : {acc['username']:<10} | Email: {acc['email']:<24} | Password: {acc['password']}")
        print(f"    Permissions: upload={new_user.can_upload()}, manage={new_user.can_manage_users()}")

    print("=" * 60)
    print("[OK] Seed script finished successfully.\n")


if __name__ == "__main__":
    seed_database()
