"""Interface and behavioral tests for JWT authentication.

Interface tests  — verify imports, class signatures, route registration (should PASS).
Behavioral tests — exercise endpoints and dependencies with real implementations.
"""
from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator

import pytest

# Mark as integration (uses TestClient/AsyncClient)
pytestmark = pytest.mark.integration

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.config import Settings
from src.database import Base
from src.dependencies import get_current_user, get_optional_current_user, scope_query_by_user
from src.main import app
from src.models.user import User
from src.routers.auth import router
from src.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.services.auth_service import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    create_user,
    decode_token,
    hash_password,
    verify_password,
)

# ============================================================================
# SECTION 1 — INTERFACE TESTS (should PASS immediately)
# ============================================================================


class TestAuthSchemasInterface:
    """Verify the auth schema interfaces."""

    def test_register_request_importable(self):
        assert RegisterRequest is not None

    def test_register_request_is_pydantic(self):
        from pydantic import BaseModel
        assert issubclass(RegisterRequest, BaseModel)

    def test_register_request_fields(self):
        sig = inspect.signature(RegisterRequest)
        assert "email" in sig.parameters
        assert "password" in sig.parameters
        assert "display_name" in sig.parameters

    def test_register_request_password_min_length(self):
        """Password field should enforce min_length=8 (check via JSON schema)."""
        schema = RegisterRequest.model_json_schema()
        props = schema.get("properties", {})
        assert props.get("password", {}).get("minLength") == 8

    def test_login_request_importable(self):
        assert LoginRequest is not None

    def test_login_request_fields(self):
        sig = inspect.signature(LoginRequest)
        assert "email" in sig.parameters
        assert "password" in sig.parameters

    def test_refresh_request_importable(self):
        assert RefreshRequest is not None

    def test_refresh_request_fields(self):
        sig = inspect.signature(RefreshRequest)
        assert "refresh_token" in sig.parameters

    def test_token_response_importable(self):
        assert TokenResponse is not None

    def test_token_response_fields(self):
        sig = inspect.signature(TokenResponse)
        assert "access_token" in sig.parameters
        assert "refresh_token" in sig.parameters
        assert "token_type" in sig.parameters
        assert "expires_in" in sig.parameters

    def test_token_response_defaults(self):
        tr = TokenResponse(access_token="a", refresh_token="r")
        assert tr.token_type == "bearer"
        assert tr.expires_in == 900

    def test_user_response_importable(self):
        assert UserResponse is not None

    def test_user_response_fields(self):
        sig = inspect.signature(UserResponse)
        assert "id" in sig.parameters
        assert "email" in sig.parameters
        assert "display_name" in sig.parameters
        assert "role" in sig.parameters
        assert "organization_id" in sig.parameters
        assert "created_at" in sig.parameters


class TestAuthRouterInterface:
    """Verify the auth router interface."""

    def test_router_importable(self):
        assert router is not None
        assert router.prefix == "/auth"

    def test_router_has_register_endpoint(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        assert ("/auth/register", ("POST",)) in routes

    def test_router_has_login_endpoint(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        assert ("/auth/login", ("POST",)) in routes

    def test_router_has_refresh_endpoint(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        assert ("/auth/refresh", ("POST",)) in routes

    def test_router_has_me_endpoint(self):
        routes = {(r.path, tuple(sorted(r.methods or []))) for r in router.routes}
        assert ("/auth/me", ("GET",)) in routes

    def test_router_endpoint_has_correct_methods(self):
        """Verify method types per endpoint."""
        for r in router.routes:
            if "/auth/register" in r.path or "/auth/login" in r.path or "/auth/refresh" in r.path:
                assert "POST" in r.methods
            elif "/auth/me" in r.path:
                assert "GET" in r.methods


class TestAuthRouterRegistration:
    """Verify the auth router is registered in the FastAPI app.

    FastAPI >=0.115 uses _IncludedRouter wrappers; we traverse
    original_router.routes to collect included route paths.
    """

    def _collect_paths(self, app) -> set[str]:
        """Collect all route paths from an app, handling _IncludedRouter."""
        paths: set[str] = set()
        for r in app.routes:
            if hasattr(r, "path") and r.path:
                paths.add(r.path)
            # _IncludedRouter keeps the original APIRouter
            if hasattr(r, "original_router"):
                for sr in r.original_router.routes:
                    if hasattr(sr, "path") and sr.path:
                        paths.add(sr.path)
        return paths

    def test_auth_router_registered_in_main(self):
        """Auth router should be included in the main app."""
        from src.main import app
        paths = self._collect_paths(app)
        assert "/auth/register" in paths, f"Auth routes not found in {sorted(paths)}"
        assert "/auth/login" in paths
        assert "/auth/refresh" in paths
        assert "/auth/me" in paths


class TestAuthConfigInterface:
    """Verify JWT config fields exist on Settings."""

    def test_jwt_settings_fields_exist(self):
        from src.config import Settings
        sig = inspect.signature(Settings)
        assert "JWT_SECRET" in sig.parameters
        assert "JWT_ALGORITHM" in sig.parameters
        assert "ACCESS_TOKEN_EXPIRE_MINUTES" in sig.parameters
        assert "REFRESH_TOKEN_EXPIRE_DAYS" in sig.parameters

    def test_jwt_settings_defaults(self):
        from src.config import Settings
        s = Settings()
        assert s.JWT_ALGORITHM == "HS256"
        assert s.ACCESS_TOKEN_EXPIRE_MINUTES == 15
        assert s.REFRESH_TOKEN_EXPIRE_DAYS == 30


class TestAuthDependenciesInterface:
    """Verify the auth dependency interfaces."""

    def test_get_current_user_importable(self):
        assert get_current_user is not None

    def test_get_current_user_is_async(self):
        assert inspect.iscoroutinefunction(get_current_user)

    def test_get_current_user_has_oauth2_scheme(self):
        """get_current_user should use OAuth2PasswordBearer with tokenUrl."""
        from fastapi.security import OAuth2PasswordBearer

        from src.dependencies import oauth2_scheme
        assert isinstance(oauth2_scheme, OAuth2PasswordBearer)

    def test_get_optional_current_user_importable(self):
        assert get_optional_current_user is not None

    def test_get_optional_current_user_is_async(self):
        assert inspect.iscoroutinefunction(get_optional_current_user)

    def test_scope_query_by_user_importable(self):
        assert scope_query_by_user is not None

    def test_scope_query_by_user_is_async(self):
        assert inspect.iscoroutinefunction(scope_query_by_user)


# ============================================================================
# SECTION 2 — BEHAVIORAL TESTS (real integration tests)
# ============================================================================


@pytest.fixture
def settings() -> Settings:
    return Settings(
        JWT_SECRET="test-secret-key-for-testing-only",
        DATABASE_URL="sqlite+aiosqlite://",
    )


class TestAuthService:
    """Real behavioral tests for the auth service layer."""

    async def _init_db(self) -> tuple[AsyncSession, AsyncEngine]:
        """Create an in-memory SQLite database with tables for testing."""
        engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        session = session_factory()
        return session, engine

    async def _create_test_user(
        self, db: AsyncSession, email: str = "test@example.com", password: str = "password123"
    ) -> User:
        body = RegisterRequest(email=email, password=password, display_name="Test User")
        return await create_user(db, body)

    @pytest.mark.asyncio
    async def test_create_user_creates_user_with_hashed_password(self):
        """Creating a user should store a hashed password, not plaintext."""
        session, engine = await self._init_db()
        try:
            user = await self._create_test_user(session)
            assert user.id is not None
            assert user.email == "test@example.com"
            assert user.password_hash != "password123"
            assert user.password_hash.startswith("$2b$")  # bcrypt hash prefix
            assert user.is_active is True
            assert user.role == "user"
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_create_user_raises_on_duplicate_email(self):
        """Creating a user with an existing email should raise ValueError."""
        session, engine = await self._init_db()
        try:
            await self._create_test_user(session, email="dup@example.com")
            with pytest.raises(ValueError, match="Email already registered"):
                await self._create_test_user(session, email="dup@example.com")
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Valid email+password should return the user."""
        session, engine = await self._init_db()
        try:
            await self._create_test_user(session)
            user = await authenticate_user(session, "test@example.com", "password123")
            assert user is not None
            assert user.email == "test@example.com"
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Wrong password should return None."""
        session, engine = await self._init_db()
        try:
            await self._create_test_user(session)
            user = await authenticate_user(session, "test@example.com", "wrongpassword")
            assert user is None
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent_email(self):
        """Non-existent email should return None."""
        session, engine = await self._init_db()
        try:
            user = await authenticate_user(session, "nobody@example.com", "password123")
            assert user is None
        finally:
            await session.close()
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_hash_password_and_verify(self):
        """Password hashing and verification should work correctly."""
        password = "my-secret-password!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong-password", hashed) is False

    def test_create_access_token(self, settings: Settings):
        """Access token should contain the user id and expiry."""
        token = create_access_token("user-123", settings)
        payload = decode_token(token, settings)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_create_refresh_token(self, settings: Settings):
        """Refresh token should contain the user id and type."""
        token = create_refresh_token("user-123", settings)
        payload = decode_token(token, settings)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self, settings: Settings):
        """An invalid token should return None."""
        payload = decode_token("not-a-valid-jwt", settings)
        assert payload is None

    def test_decode_expired_token(self, settings: Settings):
        """An expired token should return None."""
        from datetime import timedelta
        token = create_access_token("user-123", settings, expires_delta=timedelta(seconds=-1))
        payload = decode_token(token, settings)
        assert payload is None


class TestAuthEndpoints:
    """Real end-to-end tests for the auth HTTP endpoints.

    Uses an in-memory SQLite database with tables created per test.
    The app's get_db dependency is overridden to use the test database.
    """

    _engine = None
    _session_factory = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            cls._engine = create_async_engine("sqlite+aiosqlite://", echo=False)
        return cls._engine

    @classmethod
    def _get_session_factory(cls):
        if cls._session_factory is None:
            cls._session_factory = async_sessionmaker(
                bind=cls._get_engine(),
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return cls._session_factory

    async def _init_db(self):
        """Create all tables for the in-memory database."""
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop_db(self):
        """Drop all tables from the in-memory database."""
        engine = self._get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def _override_get_db(self) -> AsyncGenerator[AsyncSession]:
        """Override for the app's get_db dependency."""
        session = self._get_session_factory()()
        try:
            yield session
        finally:
            await session.close()

    async def _make_client(self, settings: Settings) -> AsyncClient:
        """Create a test client with overridden dependencies."""
        from src.dependencies import get_db, get_settings_dep

        app.dependency_overrides[get_settings_dep] = lambda: settings
        app.dependency_overrides[get_db] = self._override_get_db

        transport = ASGITransport(app=app)
        return AsyncClient(transport=transport, base_url="http://test")

    @pytest.mark.asyncio
    async def test_register_creates_user(self, settings: Settings):
        """POST /auth/register with valid data should return 201 and user profile."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/auth/register",
                json={"email": "new@example.com", "password": "password123", "display_name": "New User"},
            )
            assert response.status_code == 201, f"Body: {response.text}"
            data = response.json()
            assert data["email"] == "new@example.com"
            assert data["display_name"] == "New User"
            assert data["role"] == "user"
            assert "id" in data
            assert "created_at" in data
            assert "password" not in data  # never expose password
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, settings: Settings):
        """POST /auth/register with duplicate email should return 409."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            await client.post(
                "/auth/register",
                json={"email": "dup@example.com", "password": "password123"},
            )
            response = await client.post(
                "/auth/register",
                json={"email": "dup@example.com", "password": "otherpass"},
            )
            assert response.status_code == 409
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_login_success(self, settings: Settings):
        """POST /auth/login with valid credentials should return tokens."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            # Register first
            await client.post(
                "/auth/register",
                json={"email": "login@example.com", "password": "password123"},
            )
            # Login
            response = await client.post(
                "/auth/login",
                json={"email": "login@example.com", "password": "password123"},
            )
            assert response.status_code == 200, f"Body: {response.text}"
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] > 0
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, settings: Settings):
        """POST /auth/login with wrong password should return 401."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            await client.post(
                "/auth/register",
                json={"email": "fail@example.com", "password": "password123"},
            )
            response = await client.post(
                "/auth/login",
                json={"email": "fail@example.com", "password": "wrongpass"},
            )
            assert response.status_code == 401
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_me_with_valid_token(self, settings: Settings):
        """GET /auth/me with valid token should return user profile."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            # Register and login
            await client.post(
                "/auth/register",
                json={"email": "me@example.com", "password": "password123", "display_name": "Me User"},
            )
            login_resp = await client.post(
                "/auth/login",
                json={"email": "me@example.com", "password": "password123"},
            )
            token = login_resp.json()["access_token"]

            # Access /me
            response = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert response.status_code == 200, f"Body: {response.text}"
            data = response.json()
            assert data["email"] == "me@example.com"
            assert data["display_name"] == "Me User"
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_me_without_token(self, settings: Settings):
        """GET /auth/me without token should return 401."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            response = await client.get("/auth/me")
            assert response.status_code == 401
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_me_with_invalid_token(self, settings: Settings):
        """GET /auth/me with invalid token should return 401."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid-jwt-token"},
            )
            assert response.status_code == 401
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_refresh_with_valid_token(self, settings: Settings):
        """POST /auth/refresh with valid refresh token should return new tokens."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            # Register and login to get tokens
            await client.post(
                "/auth/register",
                json={"email": "refresh@example.com", "password": "password123"},
            )
            login_resp = await client.post(
                "/auth/login",
                json={"email": "refresh@example.com", "password": "password123"},
            )
            refresh_token = login_resp.json()["refresh_token"]

            # Refresh
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert response.status_code == 200, f"Body: {response.text}"
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            # Token rotation: new refresh token should differ from old one
            assert data["refresh_token"] != refresh_token
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self, settings: Settings):
        """POST /auth/refresh with invalid token should return 401."""
        await self._init_db()
        client = await self._make_client(settings)
        try:
            response = await client.post(
                "/auth/refresh",
                json={"refresh_token": "not-a-real-refresh-token"},
            )
            assert response.status_code == 401
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
            await self._drop_db()


class TestUserIdScoping:
    """User ID-based scoping — verify no user_id params leak into P0 endpoints."""

    def test_no_user_id_auto_populate_in_brand_voice(self):
        """Brand voice endpoints should not yet auto-populate user_id."""
        from src.routers.brand_voice import create_brand_voice
        sig = inspect.signature(create_brand_voice)
        params = list(sig.parameters.keys())
        assert "current_user" not in params, (
            "create_brand_voice should not have current_user until P2"
        )

    def test_no_user_id_filter_in_brand_voice_list(self):
        """Brand voice list should not yet filter by user_id."""
        from src.routers.brand_voice import list_brand_voices
        sig = inspect.signature(list_brand_voices)
        params = list(sig.parameters.keys())
        assert "current_user" not in params, (
            "list_brand_voices should not have current_user until P2"
        )
