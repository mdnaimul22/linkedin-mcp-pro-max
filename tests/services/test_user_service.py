import pytest
from uuid import UUID

from src.db.database import DatabaseService
from src.services.user import UserService
from src.services.tenant import TenantService
from src.helpers.models import TenantCreate, UserCreate, UserUpdate


@pytest.fixture
def tenant_service(db_service: DatabaseService):
    """Fixture for TenantService."""
    return TenantService(db_service)


@pytest.fixture
def user_service(db_service: DatabaseService):
    """Fixture for UserService."""
    return UserService(db_service)


@pytest.mark.asyncio
async def test_user_tenant_lifecycle(tenant_service: TenantService, user_service: UserService):
    """Verify that we can create a tenant and a user within it."""
    
    # 1. Create a Tenant
    tenant_data = TenantCreate(
        name="Test Agency",
        slug="test-agency",
        billing_email="billing@testagency.com",
        industry="Technology"
    )
    tenant = await tenant_service.create_tenant(tenant_data)
    assert isinstance(tenant.id, UUID)
    assert tenant.name == "Test Agency"

    # 2. Create a User in that Tenant
    user_data = UserCreate(
        tenant_id=tenant.id,
        email="admin@testagency.com",
        name="Admin User",
        password_hash="dummy_hash", # Normally hashed by service, but UserCreate takes hash
        role="admin"
    )
    # Actually, UserService.create_user handles hashing if we want, 
    # but here we follow the schema. Let's see how create_user is implemented.
    # In my implementation, I hash it if it's plain, but let's test basic creation first.
    
    user = await user_service.create_user(user_data)
    assert user.email == "admin@testagency.com"
    assert user.tenant_id == tenant.id
    assert user.status == "active" # Default status

    # 3. Retrieve User
    fetched = await user_service.get_user_by_email("admin@testagency.com")
    assert fetched is not None
    assert fetched.id == user.id

    # 4. Update User
    update_data = UserUpdate(name="Updated Admin")
    updated = await user_service.update_user(user.id, update_data)
    assert updated.name == "Updated Admin"

    # 5. List Users
    all_users = await user_service.list_users(tenant_id=tenant.id)
    assert len(all_users) == 1
    assert all_users[0].id == user.id


@pytest.mark.asyncio
async def test_user_authentication(user_service: UserService, tenant_service: TenantService):
    """Verify that user authentication works with password hashing."""
    
    # Create tenant
    tenant = await tenant_service.create_tenant(TenantCreate(
        name="Auth Test",
        slug="auth-test",
        billing_email="auth@test.com"
    ))
    
    # Create user with plain password to be hashed (using our service logic)
    # Wait, my create_user implementation used data.model_dump().
    # Let's verify if create_user hashes it.
    
    # I'll create a user manually with a known hash for this test to be sure
    hashed = user_service._hash_password("secret123")
    user_data = UserCreate(
        tenant_id=tenant.id,
        email="auth@test.com",
        password_hash=hashed
    )
    await user_service.create_user(user_data)
    
    # Test valid login
    auth_user = await user_service.authenticate_user("auth@test.com", "secret123")
    assert auth_user is not None
    assert auth_user.email == "auth@test.com"
    
    # Test invalid login
    failed_user = await user_service.authenticate_user("auth@test.com", "wrongpassword")
    assert failed_user is None
