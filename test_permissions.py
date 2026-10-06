import pytest
from app.core.permissions import Permissions
from app.core.models import User, Viewer, Editor, Admin, UserFactory


class TestPermissionsHierarchy:
    """
    Test suite verifying the object-oriented role hierarchy, inheritance,
    and polymorphic permission evaluation.
    """

    def test_viewer_permissions(self):
        """Viewer should only have view and download permissions."""
        viewer = Viewer(
            id=1,
            username="alice_viewer",
            email="alice@test.com",
            password_hash="hash1"
        )
        assert isinstance(viewer, Permissions)
        assert isinstance(viewer, User)
        assert viewer.can_view() is True
        assert viewer.can_download() is True
        assert viewer.can_upload() is False
        assert viewer.can_manage_users() is False
        assert viewer.can_assign_roles() is False

    def test_editor_inherits_and_extends_viewer(self):
        """Editor subclass inherits view/download from Viewer and adds upload capability."""
        editor = Editor(
            id=2,
            username="bob_editor",
            email="bob@test.com",
            password_hash="hash2"
        )
        # Inheritance check
        assert isinstance(editor, Viewer)
        assert isinstance(editor, User)
        assert isinstance(editor, Permissions)
        # Permitted capabilities
        assert editor.can_view() is True       # Inherited from Viewer
        assert editor.can_download() is True   # Inherited from Viewer
        assert editor.can_upload() is True     # Extended by Editor
        # Restricted capabilities
        assert editor.can_manage_users() is False
        assert editor.can_assign_roles() is False

    def test_admin_inherits_and_extends_editor(self):
        """Admin subclass inherits view/download/upload from Editor and adds user management & role assignment."""
        admin = Admin(
            id=3,
            username="charlie_admin",
            email="charlie@test.com",
            password_hash="hash3"
        )
        # Multi-level inheritance verification
        assert isinstance(admin, Editor)
        assert isinstance(admin, Viewer)
        assert isinstance(admin, User)
        assert isinstance(admin, Permissions)
        # All capabilities permitted
        assert admin.can_view() is True          # Inherited from Viewer
        assert admin.can_download() is True      # Inherited from Viewer
        assert admin.can_upload() is True        # Inherited from Editor
        assert admin.can_manage_users() is True  # Extended by Admin
        assert admin.can_assign_roles() is True  # Extended by Admin

    def test_polymorphic_permission_checks(self):
        """
        Demonstrate polymorphism: Iterating through distinct user role objects
        and executing permission checks through the interface contract without
        branching on role strings.
        """
        users: list[User] = [
            Viewer(1, "v1", "v1@t.com", "h1"),
            Editor(2, "e1", "e1@t.com", "h2"),
            Admin(3, "a1", "a1@t.com", "h3")
        ]

        expected_upload = [False, True, True]
        expected_manage = [False, False, True]

        for i, user in enumerate(users):
            # Polymorphic call: user.can_upload() behaves according to runtime class
            assert user.can_upload() == expected_upload[i], (
                f"Expected can_upload={expected_upload[i]} for class {user.__class__.__name__}"
            )
            # Polymorphic call: user.can_manage_users()
            assert user.can_manage_users() == expected_manage[i], (
                f"Expected can_manage_users={expected_manage[i]} for class {user.__class__.__name__}"
            )

    def test_user_factory_instantiation(self):
        """Verify UserFactory creates correct polymorphic subclass instances."""
        v = UserFactory.create_user("Viewer", 10, "u_v", "v@t.com", "h")
        e = UserFactory.create_user("Editor", 20, "u_e", "e@t.com", "h")
        a = UserFactory.create_user("Admin", 30, "u_a", "a@t.com", "h")
        unknown = UserFactory.create_user("Unknown", 40, "u_u", "u@t.com", "h")

        assert isinstance(v, Viewer)
        assert isinstance(e, Editor)
        assert isinstance(a, Admin)
        # Safe fallback defaults to Viewer
        assert isinstance(unknown, Viewer)
        assert unknown.can_upload() is False

    def test_to_dict_serialization(self):
        """Verify to_dict exposes evaluated permissions dictionary."""
        editor = Editor(5, "ed_test", "ed@t.com", "hash")
        d = editor.to_dict()
        assert d["username"] == "ed_test"
        assert d["role"] == "Editor"
        assert d["permissions"]["can_upload"] is True
        assert d["permissions"]["can_manage_users"] is False
