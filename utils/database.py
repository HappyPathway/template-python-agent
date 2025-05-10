"""Database Configuration and Session Management

This module provides essential database functionality built on SQLAlchemy.
It offers:
- Configuration: Centralized database setup and connection management
- Session Management: Context manager for handling database sessions
- Base Model: Declarative base for defining database models

Key Components:
- `engine`: SQLAlchemy engine for database connections
- `SessionLocal`: Factory for creating database sessions
- `Base`: Declarative base for ORM models
- `get_session`: Context manager for database sessions

Example Usage:
    ```python
    from core.database import get_session, Base
    
    with get_session() as session:
        users = session.query(User).all()
    ```

Use this module to interact with databases reliably and efficiently.
"""
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from .core.logging import setup_logging  # Corrected import

# Initialize logger
logger = setup_logging('database')

def get_database_url(db_path: Optional[str] = None) -> str:
    """Get database connection URL.
    
    Args:
        db_path: Optional path to database file. Defaults to project root.
        
    Returns:
        Database URL string
    """
    if not db_path:
        # Default to project root
        db_path = os.path.join(os.path.dirname(__file__), '..', 'database.db')
    return f'sqlite:///{db_path}'

# Create engine and session factory with default path
engine = create_engine(get_database_url(), echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# Create declarative base
Base = declarative_base()

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a Database Session as a Context Manager

    This function provides a context manager for creating and managing database sessions.
    It ensures that sessions are properly closed after use, reducing the risk of resource leaks.
    Sessions will auto-commit on success and rollback on error.

    Returns:
        Session: An active SQLAlchemy session for database operations.

    Example:
        ```python
        from core.database import get_session

        with get_session() as session:
            user = User(name="test")
            session.add(user)
            # Auto-commits if no errors, rolls back if there are any
        ```

    Why Use This Function:
        - Simplifies session management
        - Ensures proper cleanup of resources
        - Automatic commit/rollback handling
        - Integrates seamlessly with SQLAlchemy ORM
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        session.rollback()
        raise
    finally:
        session.close()

def init_db() -> None:
    """Initialize the database by creating all defined tables.
    
    Uses SQLAlchemy models to create database schema.
    Should be called during application setup.
    
    Example:
        ```python
        from utils.database import init_db
        
        init_db()  # Creates all tables
        ```
        
    Raises:
        SQLAlchemyError: If table creation fails
    """
    Base.metadata.create_all(bind=engine)

def drop_db() -> None:
    """Drop all tables from the database."""
    Base.metadata.drop_all(bind=engine)
