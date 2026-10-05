"""Security audit test suite.
Tests authentication, password hashing, admin RBAC, rate limiting, sanitization, and security headers.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.core.rate_limit import limiter
from app.core.sanitizer import is_safe_url, sanitize_query, sanitize_text
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.main import app


# ────────────────────────────────────────────────────────────
# 1. Cryptographic Password Hashing & JWT Tests
# ────────────────────────────────────────────────────────────

def test_password_hashing_and_verification():
    raw_password = "SecurePassword123!"
    hashed = hash_password(raw_password)

    # Must not store plaintext
    assert hashed != raw_password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    # Correct password verifies
    assert verify_password(raw_password, hashed) is True

    # Incorrect password fails
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_token_creation_and_validation():
    data = {"sub": "user_abc_123", "email": "test@shopbuddy.io", "is_admin": False}
    token = create_access_token(data)
    assert isinstance(token, str) and len(token) > 20

    # Successful decoding
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "user_abc_123"
    assert payload["email"] == "test@shopbuddy.io"
    assert payload["is_admin"] is False
    assert "exp" in payload
    assert "iat" in payload

    # Tampered token rejected
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None


# ────────────────────────────────────────────────────────────
# 2. XSS and Input Sanitization Tests
# ────────────────────────────────────────────────────────────

def test_xss_sanitization_text():
    # Dangerous script injection
    payload = "<script>alert('XSS')</script>Hello World"
    sanitized = sanitize_text(payload)
    assert "<script>" not in sanitized
    assert "alert('XSS')" not in sanitized
    assert "Hello World" in sanitized

    # Iframe injection
    payload_iframe = "<iframe src='http://evil.com'></iframe>My Note"
    assert "<iframe" not in sanitize_text(payload_iframe)

    # Control chars removed
    payload_null = "Hello\x00\x08World"
    assert "\x00" not in sanitize_text(payload_null)


def test_search_query_sanitization():
    xss_query = "<script>stealCookies()</script>laptop under 50000"
    clean = sanitize_query(xss_query)
    assert "<script>" not in clean
    assert "laptop under 50000" in clean


def test_safe_url_validation():
    assert is_safe_url("https://www.amazon.in/dp/B09G9FPHY6") is True
    assert is_safe_url("http://flipkart.com/item") is True
    assert is_safe_url("javascript:alert(document.cookie)") is False
    assert is_safe_url("data:text/html,<script>alert(1)</script>") is False
    assert is_safe_url("vbscript:msgbox(1)") is False
    assert is_safe_url(None) is False
    assert is_safe_url("") is False


# ────────────────────────────────────────────────────────────
# 3. HTTP Security Headers & Admin Route Protection
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_security_headers_present():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/admin/health")
        assert response.status_code == 200
        headers = response.headers

        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Content-Security-Policy" in headers


@pytest.mark.asyncio
async def test_admin_route_unauthorized_access_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Without credentials, admin endpoints must return 403 Forbidden
        response = await client.get("/api/v1/admin/providers")
        assert response.status_code == 403
        assert "forbidden" in response.json()["detail"].lower() or "admin" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_route_authorized_with_key():
    settings = get_settings()
    admin_token = settings.admin_api_token
    assert admin_token is not None, "ADMIN_API_TOKEN must be configured"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/admin/providers",
            headers={"X-Admin-Key": admin_token},
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ────────────────────────────────────────────────────────────
# 4. User Registration and Login Flow
# ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_auth_registration_and_login_flow():
    import uuid
    unique_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    password = "StrongPassword99!"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Register
        reg_res = await client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email,
                "password": password,
                "name": "Audit Test User",
                "country": "IN",
                "currency": "INR",
            },
        )
        assert reg_res.status_code == 200
        data = reg_res.json()
        assert "access_token" in data
        assert data["user"]["email"] == unique_email
        token = data["access_token"]

        # Duplicate email rejected
        dup_res = await client.post(
            "/api/v1/auth/register",
            json={"email": unique_email, "password": password},
        )
        assert dup_res.status_code == 400

        # Login with correct password
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": password},
        )
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()

        # Login with incorrect password
        bad_login = await client.post(
            "/api/v1/auth/login",
            json={"email": unique_email, "password": "WrongPassword1!"},
        )
        assert bad_login.status_code == 401

        # Authenticated profile access
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        assert me_res.json()["email"] == unique_email


# ────────────────────────────────────────────────────────────
# 5. Rate Limiting Tests
# ────────────────────────────────────────────────────────────

def test_rate_limiter_threshold():
    limiter._records.clear()
    key = "test_client_key"

    # Allow up to 3 requests
    for _ in range(3):
        limited, _ = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
        assert limited is False

    # 4th request must be rate-limited
    limited, retry_after = limiter.is_rate_limited(key, max_requests=3, window_seconds=60)
    assert limited is True
    assert retry_after > 0
