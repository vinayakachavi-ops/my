import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load variables from .env if present
load_dotenv(BASE_DIR / ".env")



class Config:
    """Base application configuration."""

    SECRET_KEY = os.environ.get("SECURESHARE_SECRET_KEY") or "dev-insecure-secret-key-change-in-prod-8f0a3e8d2c"
    
    # Database configuration
    INSTANCE_DIR = BASE_DIR / "instance"
    INSTANCE_DIR.mkdir(exist_ok=True)
    _raw_db_url = os.environ.get("DATABASE_URL")
    if _raw_db_url and _raw_db_url.startswith("sqlite:///") and not Path(_raw_db_url[10:]).is_absolute():
        _db_path = (BASE_DIR / _raw_db_url[10:]).resolve()
        _db_path.parent.mkdir(parents=True, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{_db_path.as_posix()}"
    elif _raw_db_url:
        SQLALCHEMY_DATABASE_URI = _raw_db_url
    else:
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{(INSTANCE_DIR / 'secureshare.db').as_posix()}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploads configuration
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS = {
        "pdf", "docx", "doc", "txt", "md", "csv", "json", "xml",
        "png", "jpg", "jpeg", "gif", "svg", "webp",
        "xlsx", "xls", "zip", "tar", "gz", "py", "js", "html", "css"
    }

    # Encryption key storage path (if not supplied via env var)
    ENCRYPTION_KEY_PATH = BASE_DIR / ".encryption_key"

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("FLASK_ENV") == "production"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours in seconds


class TestConfig(Config):
    """Configuration for automated testing."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    UPLOAD_FOLDER = BASE_DIR / "test_uploads"
    ENCRYPTION_KEY_PATH = BASE_DIR / ".test_encryption_key"
    SECRET_KEY = "test-secret-key-12345"
