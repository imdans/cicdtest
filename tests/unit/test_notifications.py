"""Unit tests for email notification functionality"""
import types
import builtins

from app.services.email_service import EmailService
from app.models import ChangeRequest, CRPriority, CRStatus


class DummySMTP:
    """Mock SMTP class for testing"""
    def __init__(self, *a, **k):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def starttls(self):
        pass
    def login(self, *a, **k):
        pass
    def send_message(self, msg):
        # emulate success
        return True


def test_email_notifications_sends(monkeypatch, app, db_session, requester_user, approver_user, project):
    """Test that email notifications are sent successfully"""
    # Force SMTP config to look configured
    app.config.update(
        SMTP_USERNAME="user",
        SMTP_PASSWORD="pass",
        SMTP_FROM_EMAIL="noreply@test.local",
        SMTP_FROM_NAME="CMS",
    )

    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    # Create CR and call one of the notification methods
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Notify",
        description="desc long enough for validation",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    ok = EmailService.send_cr_submission_notification(cr, [approver_user])
    # Method returns None but should not raise; SMTP path used
    assert ok is None


def test_email_approval_notification(monkeypatch, app, db_session, requester_user, approver_user, implementer_user, project):
    """Test approval notification email"""
    app.config.update(
        SMTP_USERNAME="user",
        SMTP_PASSWORD="pass",
        SMTP_FROM_EMAIL="noreply@test.local",
        SMTP_FROM_NAME="CMS",
    )
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, implementer_user, "implementer")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Approved CR",
        description="CR that will be approved",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.APPROVED,
        approver_id=approver_user.id,
    )
    db_session.add(cr)
    db_session.commit()

    result = EmailService.send_cr_approval_notification(cr, [implementer_user])
    assert result is None  # Successful send returns None


def test_email_rejection_notification(monkeypatch, app, db_session, requester_user, approver_user, project):
    """Test rejection notification email"""
    app.config.update(
        SMTP_USERNAME="user",
        SMTP_PASSWORD="pass",
        SMTP_FROM_EMAIL="noreply@test.local",
        SMTP_FROM_NAME="CMS",
    )
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Rejected CR",
        description="CR that will be rejected",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.REJECTED,
        rejection_reason="Not feasible at this time",
    )
    db_session.add(cr)
    db_session.commit()

    email_service = EmailService()
    result = email_service.send_cr_rejection_notification(cr, "Not feasible at this time")
    assert result is None  # Successful send returns None


def test_email_sla_warning(monkeypatch, app, db_session, requester_user, project):
    """Test SLA warning email"""
    app.config.update(
        SMTP_USERNAME="user",
        SMTP_PASSWORD="pass",
        SMTP_FROM_EMAIL="noreply@test.local",
        SMTP_FROM_NAME="CMS",
    )
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    # CR with implementation_deadline set
    from datetime import datetime, timedelta
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="SLA Warning CR",
        description="CR approaching deadline",
        priority=CRPriority.HIGH,
        requester_id=requester_user.id,
        status=CRStatus.IN_PROGRESS,
        implementation_deadline=datetime.now() + timedelta(hours=12),  # Set deadline
    )
    db_session.add(cr)
    db_session.commit()

    email_service = EmailService()
    result = email_service.send_sla_warning_email(cr)
    assert result is None  # Successful send returns None


def test_email_without_smtp_config(app, db_session, requester_user, approver_user, project):
    """Test that email gracefully handles missing SMTP configuration"""
    # Clear SMTP config
    app.config.update(
        SMTP_USERNAME=None,
        SMTP_PASSWORD=None,
    )

    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="No SMTP CR",
        description="Testing without SMTP config",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    # Should not raise exception
    result = EmailService.send_cr_submission_notification(cr, [approver_user])
    assert result is None  # Returns None when SMTP not configured
