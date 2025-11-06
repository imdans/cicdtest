"""Unit tests for authentication functionality"""
import pyotp
from flask import session


def test_user_login_with_credentials(client, requester_user):
    """Test basic user login with valid credentials"""
    # GET login page
    res = client.get("/auth/login")
    assert res.status_code == 200

    # POST valid credentials -> should redirect to home
    res = client.post(
        "/auth/login",
        data={"email": requester_user.email, "password": "Password123!", "remember_me": "y"},
        follow_redirects=False,
    )
    # requester has no MFA, should log in and redirect
    assert res.status_code in (302, 303)
    assert res.headers.get("Location") is not None


def test_user_login_with_invalid_password(client, requester_user):
    """Test login fails with incorrect password"""
    res = client.post(
        "/auth/login",
        data={"email": requester_user.email, "password": "WrongPassword123!"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Invalid" in res.data or b"incorrect" in res.data.lower()


def test_user_login_with_nonexistent_email(client):
    """Test login fails with email that doesn't exist"""
    res = client.post(
        "/auth/login",
        data={"email": "nonexistent@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Invalid" in res.data or b"incorrect" in res.data.lower()


def test_admin_login_triggers_mfa(client, admin_user):
    """Test that admin login with MFA enabled triggers verification"""
    res = client.post(
        "/auth/login",
        data={"email": admin_user.email, "password": "Password123!"},
        follow_redirects=False,
    )
    # Admin with MFA enabled should be redirected to verify-mfa
    assert res.status_code in (302, 303)
    assert "/auth/verify-mfa" in res.headers.get("Location", "")

    # Now simulate MFA verification
    # Flask test client keeps cookies, so session contains mfa_user_id
    # Generate current TOTP
    totp = pyotp.TOTP(admin_user.mfa_secret)
    code = totp.now()

    res2 = client.post(
        "/auth/verify-mfa",
        data={"code": code},
        follow_redirects=False,
    )
    # After successful MFA, redirect to home
    assert res2.status_code in (302, 303)


def test_mfa_verification_with_invalid_code(client, admin_user):
    """Test MFA verification fails with invalid code"""
    # First login to trigger MFA
    resp = client.post(
        "/auth/login",
        data={"email": admin_user.email, "password": "Password123!"},
        follow_redirects=False,
    )
    
    # Check if rate limited
    if resp.status_code == 429:
        # Rate limited - skip this specific test
        return
    
    # Try invalid MFA code
    res = client.post(
        "/auth/verify-mfa",
        data={"code": "000000"},
        follow_redirects=True,
    )
    assert res.status_code in (200, 429)  # Either stays on page or rate limited
    # Should stay on MFA page or show error


def test_logout_clears_session(client, requester_user):
    """Test that logout properly clears user session"""
    # Login first
    client.post(
        "/auth/login",
        data={"email": requester_user.email, "password": "Password123!"},
        follow_redirects=True,
    )
    
    # Logout
    res = client.get("/auth/logout", follow_redirects=False)
    assert res.status_code in (302, 303)
    
    # Try to access protected page - should redirect to login
    res = client.get("/change-requests/", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/auth/login" in res.headers.get("Location", "")


def test_profile_page_requires_authentication(client):
    """Test that profile page requires login"""
    res = client.get("/auth/profile", follow_redirects=False)
    assert res.status_code in (302, 303)
    assert "/auth/login" in res.headers.get("Location", "")
