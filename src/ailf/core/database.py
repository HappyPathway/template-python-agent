"""Database Configuration and Session Management

This module provides essential database functionality built on SQLAlchemy.
It offers:
- Configuration: Centralized database setup and connection management
- Session Management: Context manager for handling database sessions
- Base Models: Declarative base for defining database models
- Multiple Backend Support: Support for SQLite, PostgreSQL, and other backends

Key Components:
- `DatabaseManager`: Abstract base class for database operations
- `SQLiteManager`: Implementation for SQLite databases
- `PostgresManager`: Implementation for PostgreSQL databases
- `Base`: Declarative base for ORM models

Example Usage:
    ```python
    from ailf.core.database import SQLiteManager, Base
    
    db = SQLiteManager("app.db")
    with db.session() as session:
        users = session.query(User).all()
    ```

Use this module to interact with databases reliably and efficiently.
"""

import os
from pathlib import Path
from abc import ABC, abstractmethod
from contextlib import contextmanager
from typing import Generator, Optional, Dict, Any, Union

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import Pool

from ailf.core.logging import setup_logging

# Initialize logger
logger = setup_logging('database')

# Create declarative base
Base = declarative_base()

class DatabaseManager(ABC):
    """Abstract base class for database management."""
    
    def __init__(self, uri: Optional[str] = None, **kwargs):
        """Initialize database manager.
        
        Args:
            uri: Database URI
            **kwargs: Additional engine configuration
        """
        self.uri = uri
        self.engine_kwargs = kwargs
        self._engine = None
        self._session_factory = None
        
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine.
        
        Returns:
            SQLAlchemy engine
        """
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine
        
    @abstractmethod
    def _create_engine(self) -> Engine:
        """Create database engine.
        
        Returns:
            SQLAlchemy engine
        """
        pass
    
    @property
    def session_factory(self):
        """Get session factory.
        
        Returns:
            Session factory
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine, 
                autocommit=False, 
                autoflush=False
            )
        return self._session_factory
        
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """Get a database session as a context manager.
        
        Yields:
            SQLAlchemy session
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
            
    def init_db(self) -> None:
        """Initialize database by creating tables."""
        Base.metadata.create_all(bind=self.engine)
        
    def drop_db(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)


class SQLiteManager(DatabaseManager):
    """SQLite database manager."""
    
    def __init__(
        self, 
        db_path: Optional[str] = None,
        in_memory: bool = False,
        **kwargs
    ):
        """Initialize SQLite database manager.
        
        Args:
            db_path: Path to database file
            in_memory: Use in-memory database
            **kwargs: Additional engine configuration
        """
        if in_memory:
            uri = "sqlite:///:memory:"
        elif db_path:
            uri = f"sqlite:///{db_path}"
        else:
            # Default to project root directory
            default_path = os.path.join(os.getcwd(), 'database.db')
            uri = f"sqlite:///{default_path}"
            
        super().__init__(uri=uri, **kwargs)
        self.db_path = db_path
        
    def _create_engine(self) -> Engine:
        """Create SQLite engine.
        
        Returns:
            SQLAlchemy engine
        """
        connect_args = self.engine_kwargs.pop('connect_args', {})
        # Enable foreign keys by default
        connect_args.setdefault('check_same_thread', False)
        
        return create_engine(
            self.uri,
            connect_args=connect_args,
            **self.engine_kwargs
        )


class PostgresManager(DatabaseManager):
    """PostgreSQL database manager."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        username: str = "postgres",
        password: Optional[str] = None,
        database: str = "postgres",
        **kwargs
    ):
        """Initialize PostgreSQL database manager.
        
        Args:
            host: Database host
            port: Database port
            username: Database username
            password: Database password
            database: Database name
            **kwargs: Additional engine configuration
        """
        # Build connection URI
        uri = f"postgresql://{username}"
        if password:
            uri += f":{password}"
        uri += f"@{host}:{port}/{database}"
        
        super().__init__(uri=uri, **kwargs)
        self.host = host
        self.port = port
        self.database = database
        
    def _create_engine(self) -> Engine:
        """Create PostgreSQL engine.
        
        Returns:
            SQLAlchemy engine
        """
        pool_size = self.engine_kwargs.pop('pool_size', 5)
        max_overflow = self.engine_kwargs.pop('max_overflow', 10)
        
        return create_engine(
            self.uri,
            pool_size=pool_size,
            max_overflow=max_overflow,
            **self.engine_kwargs
        )


# Default database manager for backward compatibility
default_db_manager = SQLiteManager()

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session from the default manager.
    
    This function is provided for backward compatibility.
    
    Yields:
        SQLAlchemy session
    """
    with default_db_manager.session() as session:
        yield session
        
def init_db() -> None:
    """Initialize default database by creating tables."""
    default_db_manager.init_db()
    
def drop_db() -> None:
    """Drop all default database tables."""
    default_db_manager.drop_db()


__all__ = [
    "Base",
    "DatabaseManager",
    "SQLiteManager", 
    "PostgresManager",
    "get_session",
    "init_db",
    "drop_db"
]
