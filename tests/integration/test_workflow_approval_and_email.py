"""Integration tests for complete CR workflow including approval and email notifications"""
import smtplib

from app.models.change_request import ChangeRequest, CRStatus, CRPriority
from app.services.email_service import EmailService


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
        return True


def test_workflow_approval_and_email(monkeypatch, app, db_session, requester_user, approver_user, implementer_user, project):
    """Test complete approval workflow with email notifications"""
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    app.config.update(SMTP_USERNAME="x", SMTP_PASSWORD="y")

    # Create CR and approve
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Integration approve",
        description="desc long enough",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    assert cr.can_approve(approver_user) is True
    cr.approve(approver_user, comments="ok")
    db_session.commit()
    assert cr.status == CRStatus.APPROVED

    # Simulate notification
    EmailService.send_cr_approval_notification(cr, [implementer_user])


def test_workflow_rejection_and_email(monkeypatch, app, db_session, requester_user, approver_user, project):
    """Test rejection workflow with email notifications"""
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    app.config.update(SMTP_USERNAME="x", SMTP_PASSWORD="y")

    # Create CR and reject
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Integration reject",
        description="desc long enough to test rejection",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    # Reject CR
    cr.reject(approver_user, "Not approved")
    db_session.commit()
    assert cr.status == CRStatus.REJECTED

    # Send rejection notification
    email_service = EmailService()
    email_service.send_cr_rejection_notification(cr, "Not approved")


def test_workflow_implementation_and_closure(monkeypatch, app, db_session, requester_user, approver_user, implementer_user, project):
    """Test complete workflow from approval to implementation to closure"""
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    app.config.update(SMTP_USERNAME="x", SMTP_PASSWORD="y")

    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, implementer_user, "implementer")

    # Create and approve CR
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Full workflow CR",
        description="Testing complete workflow",
        priority=CRPriority.HIGH,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    # Approve
    cr.approve(approver_user, "Approved for implementation")
    db_session.commit()
    assert cr.status == CRStatus.APPROVED

    # Start implementation
    cr.start_implementation(implementer_user)
    db_session.commit()
    assert cr.status == CRStatus.IN_PROGRESS

    # Mark as implemented
    cr.complete_implementation()
    db_session.commit()
    assert cr.status == CRStatus.IMPLEMENTED

    # Close CR
    cr.close(approver_user, "Verified and working")
    db_session.commit()
    assert cr.status == CRStatus.CLOSED


def test_workflow_rollback(monkeypatch, app, db_session, requester_user, approver_user, project):
    """Test rollback workflow"""
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    app.config.update(SMTP_USERNAME="x", SMTP_PASSWORD="y")

    # Create implemented CR
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Rollback test CR",
        description="CR to be rolled back",
        priority=CRPriority.CRITICAL,
        requester_id=requester_user.id,
        status=CRStatus.IMPLEMENTED,
        rollback_plan="Restore from backup",
    )
    db_session.add(cr)
    db_session.commit()

    # Rollback
    cr.rollback(approver_user, "Issues found")
    db_session.commit()
    assert cr.status == CRStatus.ROLLED_BACK
    assert cr.rollback_reason == "Issues found"
