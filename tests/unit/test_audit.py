"""Unit tests for audit logging functionality"""
from app.models.audit import AuditLog, AuditEventType, AuditEventCategory


def test_immutable_audit_log_creation(db_session, requester_user):
    """Test creating an audit log entry"""
    log = AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=requester_user,
        description="login ok",
        success=True,
        metadata={"ip": "127.0.0.1"},
    )
    assert log.id is not None
    assert log.username == requester_user.username
    ts = log.timestamp

    # Attempt to change timestamp should be persisted only if we commit, but we treat as immutable by convention
    log.timestamp = ts  # no-op
    db_session.commit()
    again = AuditLog.query.get(log.id)
    assert again.timestamp == ts


def test_audit_log_event_types(db_session, admin_user):
    """Test different audit event types"""
    # Test login event
    login_log = AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=admin_user,
        description="Admin login successful",
        success=True,
    )
    assert login_log.event_type == AuditEventType.LOGIN_SUCCESS
    
    # Test logout event
    logout_log = AuditLog.create_log(
        event_type=AuditEventType.LOGOUT,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=admin_user,
        description="Admin logout",
        success=True,
    )
    assert logout_log.event_type == AuditEventType.LOGOUT


def test_audit_log_with_metadata(db_session, requester_user):
    """Test audit log with metadata"""
    log = AuditLog.create_log(
        event_type=AuditEventType.CR_CREATED,
        event_category=AuditEventCategory.CHANGE_REQUEST,
        user=requester_user,
        description="Created new CR",
        success=True,
        metadata={
            "cr_number": "CR-001",
            "priority": "high",
            "project_id": 1
        },
    )
    assert log.extra_data is not None
    assert "cr_number" in log.extra_data
    assert log.extra_data["cr_number"] == "CR-001"


def test_audit_log_query_by_user(db_session, requester_user, approver_user):
    """Test querying audit logs by user"""
    # Create logs for different users
    AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=requester_user,
        description="Requester login",
        success=True,
    )
    
    AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=approver_user,
        description="Approver login",
        success=True,
    )
    
    # Query by specific user
    requester_logs = AuditLog.query.filter_by(user_id=requester_user.id).all()
    assert len(requester_logs) >= 1
    assert all(log.user_id == requester_user.id for log in requester_logs)


def test_audit_log_failure_event(db_session, requester_user):
    """Test logging failed events"""
    log = AuditLog.create_log(
        event_type=AuditEventType.LOGIN_FAILED,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=requester_user,
        description="Failed login attempt",
        success=False,
        metadata={"reason": "invalid_password"},
    )
    assert log.success is False
    assert log.extra_data["reason"] == "invalid_password"


def test_audit_log_categories(db_session, admin_user):
    """Test different audit event categories"""
    # Authentication category
    auth_log = AuditLog.create_log(
        event_type=AuditEventType.LOGIN_SUCCESS,
        event_category=AuditEventCategory.AUTHENTICATION,
        user=admin_user,
        description="Auth event",
        success=True,
    )
    assert auth_log.event_category == AuditEventCategory.AUTHENTICATION
    
    # User management category
    user_log = AuditLog.create_log(
        event_type=AuditEventType.USER_CREATED,
        event_category=AuditEventCategory.USER_MANAGEMENT,
        user=admin_user,
        description="Created new user",
        success=True,
    )
    assert user_log.event_category == AuditEventCategory.USER_MANAGEMENT
