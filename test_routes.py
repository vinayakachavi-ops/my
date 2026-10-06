import io
import pytest
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService


class TestRouteRBAC:
    """End-to-end HTTP integration tests verifying polymorphic route protection."""

    @pytest.fixture
    def test_users(self, app, session):
        user_mgr = UserManager(session)
        auth_srv = AuthService(user_mgr)

        admin = auth_srv.register("route_admin", "admin@route.com", "AdminPass!123", role="Admin")
        editor = auth_srv.register("route_editor", "editor@route.com", "EditorPass!123", role="Editor")
        viewer = auth_srv.register("route_viewer", "viewer@route.com", "ViewerPass!123", role="Viewer")

        return {
            "admin": admin,
            "editor": editor,
            "viewer": viewer
        }

    def login_user(self, client, identifier, password):
        # Retrieve login page to get CSRF token
        res = client.get("/auth/login")
        return client.post("/auth/login", data={
            "identifier": identifier,
            "password": password
        }, follow_redirects=True)

    def test_unauthenticated_redirect(self, client):
        """Unauthenticated access to protected routes redirects to login."""
        res = client.get("/dashboard", follow_redirects=False)
        assert res.status_code == 302
        assert "/auth/login" in res.headers["Location"]

        res_files = client.get("/files/", follow_redirects=False)
        assert res_files.status_code == 302
        assert "/auth/login" in res_files.headers["Location"]

    def test_viewer_access_and_restrictions(self, client, test_users):
        """Viewer can view files but is forbidden (403) from uploading or admin panel."""
        self.login_user(client, "route_viewer", "ViewerPass!123")

        # Can access dashboard
        res_dash = client.get("/dashboard")
        assert res_dash.status_code == 200
        assert b"Viewer Privilege Tier" in res_dash.data

        # Can view files vault
        res_files = client.get("/files/")
        assert res_files.status_code == 200

        # Attempt to upload: forbidden by polymorphic check (can_upload() -> False)
        data = {
            "file": (io.BytesIO(b"Viewer trying to upload"), "unauthorized.txt")
        }
        res_upload = client.post("/files/upload", data=data, content_type="multipart/form-data")
        assert res_upload.status_code == 403
        assert b"Access Denied" in res_upload.data
        assert b"can_upload" in res_upload.data

        # Attempt to access admin panel: forbidden (can_manage_users() -> False)
        res_admin = client.get("/admin/")
        assert res_admin.status_code == 403
        assert b"Access Denied" in res_admin.data
        assert b"can_manage_users" in res_admin.data

    def test_editor_can_upload_but_no_admin(self, client, test_users):
        """Editor can upload files but is forbidden (403) from admin panel."""
        self.login_user(client, "route_editor", "EditorPass!123")

        # Can access files page
        res_files = client.get("/files/")
        assert res_files.status_code == 200

        # Upload file succeeds
        data = {
            "file": (io.BytesIO(b"Editor content to encrypt"), "editor_doc.txt")
        }
        res_upload = client.post("/files/upload", data=data, content_type="multipart/form-data", follow_redirects=True)
        assert res_upload.status_code == 200
        assert b"uploaded and encrypted successfully" in res_upload.data

        # Attempt to access admin panel: forbidden
        res_admin = client.get("/admin/")
        assert res_admin.status_code == 403
        assert b"Access Denied" in res_admin.data

    def test_admin_has_full_access(self, client, test_users):
        """Admin can access admin panel, create accounts, and assign roles."""
        self.login_user(client, "route_admin", "AdminPass!123")

        # Can access admin panel
        res_admin = client.get("/admin/")
        assert res_admin.status_code == 200
        assert b"Administrative Control Panel" in res_admin.data
        assert b"route_viewer" in res_admin.data

        # Can assign role to viewer -> Editor
        viewer_id = test_users["viewer"].id
        res_role = client.post(f"/admin/users/{viewer_id}/role", data={
            "role": "Editor"
        }, follow_redirects=True)
        assert res_role.status_code == 200
        assert b"updated to &#39;Editor&#39;" in res_role.data or b"updated to 'Editor'" in res_role.data
