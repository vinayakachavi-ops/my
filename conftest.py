import pytest
from app import create_app
from app.config import TestConfig
from app.database.connection import db_session, create_all_tables, drop_all_tables
from app.services.user_manager import UserManager
from app.services.auth_service import AuthService
from app.services.encryption_service import EncryptionService
from app.services.file_manager import FileManager


@pytest.fixture(scope="session")
def test_config():
    return TestConfig


@pytest.fixture
def app(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    key_file = tmp_path / ".test_key"

    class DynamicTestConfig(TestConfig):
        UPLOAD_FOLDER = upload_dir
        ENCRYPTION_KEY_PATH = key_file
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{tmp_path / 'test.db'}"

    app_instance = create_app(DynamicTestConfig)

    with app_instance.app_context():
        create_all_tables()
        yield app_instance
        drop_all_tables()
        db_session.remove()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def session(app):
    return db_session


@pytest.fixture
def user_manager(session):
    return UserManager(session)


@pytest.fixture
def auth_service(user_manager):
    return AuthService(user_manager)


@pytest.fixture
def encryption_service(tmp_path):
    key_file = tmp_path / "enc.key"
    return EncryptionService(key_file_path=key_file)


@pytest.fixture
def file_manager(session, tmp_path, encryption_service):
    upload_dir = tmp_path / "files"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return FileManager(
        session=session,
        upload_folder=upload_dir,
        encryption_service=encryption_service,
        allowed_extensions={"txt", "pdf", "png", "jpg", "csv", "json"},
        max_file_size=5 * 1024 * 1024
    )
