"""SQLAlchemy base configuration and database connection."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

# Declarative base for all models
Base = declarative_base()

# Global session factory
SessionLocal = None


def get_database_url() -> str:
    """Get PostgreSQL connection URL from environment.

    Returns:
        Database URL string

    Raises:
        ValueError: If DATABASE_URL is not set
    """
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable not set. "
            "Example: postgresql://user:pass@localhost:5432/aws2openstack"
        )
    return url


def get_engine(echo: bool = False):
    """Create SQLAlchemy engine.

    Args:
        echo: Whether to log SQL statements (for debugging)

    Returns:
        SQLAlchemy engine instance
    """
    return create_engine(
        get_database_url(),
        echo=echo,
        pool_pre_ping=True,  # Verify connections before using
        poolclass=NullPool,  # Don't pool connections (safe for CLI usage)
    )


def get_session_factory():
    """Create session factory bound to database engine.

    Returns:
        Sessionmaker factory
    """
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    """Get a database session.

    Yields:
        SQLAlchemy session

    Usage:
        with get_session() as session:
            session.query(Model).all()
    """
    global SessionLocal
    if SessionLocal is None:
        SessionLocal = get_session_factory()

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
