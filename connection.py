from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

Base = declarative_base()
_engine = None

# Scoped session created once so module imports always have a valid session proxy
db_session = scoped_session(sessionmaker(autoflush=False, autocommit=False))


def init_db(database_uri: str):
    """Initialize SQLAlchemy engine and configure scoped session."""
    global _engine
    _engine = create_engine(
        database_uri,
        connect_args={"check_same_thread": False} if "sqlite" in database_uri else {},
        echo=False
    )
    db_session.configure(bind=_engine)
    return _engine, db_session


def create_all_tables():
    """Create all schema tables in the database."""
    if _engine is not None:
        Base.metadata.create_all(bind=_engine)


def drop_all_tables():
    """Drop all tables (used for testing resets)."""
    if _engine is not None:
        Base.metadata.drop_all(bind=_engine)


def get_db():
    """Helper to access the current scoped database session."""
    return db_session
