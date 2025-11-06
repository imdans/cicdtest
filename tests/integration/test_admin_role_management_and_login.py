from app.models import User


def test_admin_role_management_and_login(client, db_session, admin_user):
    # Admin exists and can log in via client
    resp = client.post(
        "/auth/login",
        data={"email": admin_user.email, "password": "Password123!"},
        follow_redirects=False,
    )
    # For admin with MFA enabled, expect redirect to verify_mfa
    assert resp.status_code in (302, 303)
    assert "/auth/verify-mfa" in resp.headers.get("Location", "")
