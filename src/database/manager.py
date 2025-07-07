# src/database/manager.py
"""Database engine and session management."""

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import config from project root (adjust import path as needed)
from config import config


def get_engine(db_url: Optional[str] = None):
    """
    Create and configure a SQLAlchemy engine based on database type.
    
    Args:
        db_url: Optional database URL (currently not used in PostgreSQL case)
        
    Returns:
        Configured SQLAlchemy engine
    """
    if config.database.db_type == 'postgres':
        return create_engine(
            os.getenv('DATABASE_URL'),
            pool_size=20,
            max_overflow=10
        )
    
    # SQLite configuration
    return create_engine(
        f"sqlite:///{config.database.db_path}",
        pool_size=10,
        max_overflow=20
    )


def get_session_factory(engine):
    """
    Create a session factory bound to the given engine.
    
    Args:
        engine: SQLAlchemy engine instance
        
    Returns:
        Configured session factory
    """
    return sessionmaker(bind=engine)