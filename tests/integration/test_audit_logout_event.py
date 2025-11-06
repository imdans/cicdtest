from app.models.audit import AuditLog, AuditEventType, AuditEventCategory


def test_logout_creates_audit_log(client, requester_user):
    # Login first
    res = client.post(
        "/auth/login",
        data={"email": requester_user.email, "password": "Password123!"},
        follow_redirects=False,
    )
    assert res.status_code in (302, 303)

    # Logout
    res2 = client.get("/auth/logout", follow_redirects=False)
    assert res2.status_code in (302, 303)

    # Check audit log for logout event
    log = (
        AuditLog.query.filter_by(event_type=AuditEventType.LOGOUT)
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert log is not None
    assert log.event_category == AuditEventCategory.AUTHENTICATION
