# attendance_bot/tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import delete

from models import Base
from core.security import SecurityManager

# Test database URL
TEST_DATABASE_URL = "postgresql+asyncpg://attendance:attendance_secret@localhost:5432/attendance_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
AsyncTestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(db_engine):
    async with AsyncTestSession() as session:
        yield session
        # Cleanup after each test
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(delete(table))
        await session.commit()


@pytest.fixture
def security_manager():
    return SecurityManager()


@pytest.fixture
def sample_user_data():
    return {
        "employee_number": "EMP001",
        "full_name": "Test User",
        "username": "testuser",
        "email": "test@example.com",
        "password": "TestPassword123!",
        "phone": "13800138000",
        "role": "employee",
    }
