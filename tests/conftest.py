import sys
from unittest.mock import MagicMock
import pytest
import pytest_asyncio
from sqlalchemy import JSON, String, Text, TypeDecorator, CHAR

# --- Non-invasive Monkeypatching for SQLite Tests ---
# This "hijacks" the postgresql dialect module and fixes bcrypt session BEFORE any models or services are loaded.
# Production code stays 100% clean, while tests run smoothly on SQLite and Python 3.13.

# 1. Fix bcrypt 'longer than 72 bytes' ValueError on Python 3.13
# This is a known issue with passlib's bug detection and modern bcrypt.
try:
    import bcrypt
    original_hashpw = bcrypt.hashpw
    def mocked_hashpw(password, salt):
        # Truncate password if it's over 72 bytes to avoid ValueError in newer bcrypt versions
        if isinstance(password, str):
            encoded_password = password.encode('utf-8')
        else:
            encoded_password = password
            
        if len(encoded_password) > 72:
            encoded_password = encoded_password[:72]
            
        return original_hashpw(encoded_password, salt)
    
    bcrypt.hashpw = mocked_hashpw
except ImportError:
    pass

def setup_sqllite_compatibility():
    from uuid import UUID as PyUUID

    # 2. Define our SQLite-friendly types
    class SQLiteGUID(TypeDecorator):
        impl = CHAR
        cache_ok = True
        def load_dialect_impl(self, dialect: any): return dialect.type_descriptor(CHAR(32))
        def process_bind_param(self, value, dialect):
            if value is None: return value
            return "%.32x" % (PyUUID(str(value)).int if not isinstance(value, PyUUID) else value.int)
        def process_result_value(self, value, dialect):
            if value is None: return value
            return PyUUID(value)

    # 3. Create a mock postgresql dialect module
    mock_pg = MagicMock()
    mock_pg.ARRAY = lambda inner: JSON
    mock_pg.INET = String(45)
    mock_pg.UUID = lambda as_uuid=True: SQLiteGUID()
    
    # 4. Inject the mock into sys.modules so 'src.db.tables' gets it
    sys.modules['sqlalchemy.dialects.postgresql'] = mock_pg

# Run setup before anything else
setup_sqllite_compatibility()

# Now import the models and DB service
from src.db.tables import Base
from src.db.database import DatabaseService

# Final touch: Patch Vector class in the loaded tables module
import src.db.tables as tables
class SQLiteVector(Text):
    def get_col_spec(self, **kw): return "TEXT"
    def bind_processor(self, dialect): return JSON().bind_processor(dialect)
    def result_processor(self, dialect, coltype): return JSON().result_processor(dialect, coltype)

tables.Vector = SQLiteVector

@pytest_asyncio.fixture
async def db_service():
    """Async fixture for DatabaseService using in-memory SQLite."""
    # Use in-memory SQLite for fast testing
    test_db_url = "sqlite+aiosqlite:///:memory:"
    service = DatabaseService(database_url=test_db_url)
    
    # Initialize schema in memory
    async with service._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield service
    
    # Clean up
    await service.close()
