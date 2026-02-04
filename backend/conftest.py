# conftest.py - Global pytest configuration
"""
Global pytest configuration.

This file is automatically loaded by pytest before collecting tests.
We use it to ensure debug scripts are never collected.
"""
import glob
import os
import pytest
import asyncio

# Collect all debug_*.py files anywhere in the backend tree and ignore them
_backend_root = os.path.dirname(os.path.abspath(__file__))
collect_ignore = []

# Add all debug_*.py files
for pattern in ["**/debug_*.py", "scripts/**/*.py"]:
    for path in glob.glob(os.path.join(_backend_root, pattern), recursive=True):
        # Make relative to backend root
        collect_ignore.append(os.path.relpath(path, _backend_root))

# Also add common paths that should never be collected
collect_ignore.extend([
    "scripts/",
    "app/",  # Likely old app structure
])


# =============================================================================
# Async Test Fixtures for SQLAlchemy + asyncpg
# =============================================================================

@pytest.fixture(scope="function")
def event_loop():
    """
    Create a fresh event loop for each test function.
    
    This is crucial for async tests with SQLAlchemy/asyncpg to avoid 
    "Event loop is closed" errors from stale connection pools.
    """
    loop = asyncio.new_event_loop()
    yield loop
    # Clean shutdown
    loop.run_until_complete(loop.shutdown_asyncgens())
    loop.close()


@pytest.fixture(scope="function")
async def async_db():
    """
    Provide a fresh async database session for each test.
    
    Creates a new engine and session per test to avoid connection pool
    corruption between tests with different event loops.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from homelab.config import get_settings
    
    settings = get_settings()
    
    # Create fresh engine for this test
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )
    
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_maker() as session:
        yield session
    
    # Dispose engine to close all connections
    await engine.dispose()
