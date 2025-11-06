"""Unit tests for change request models and workflows"""
from datetime import datetime, timedelta, timezone

from app.models import ChangeRequest, CRStatus, CRPriority, CRRiskLevel


def test_submit_change_request_model(db_session, requester_user, project):
    """Test creating and submitting a change request"""
    # link requester to project
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Add feature X to system",
        description="Detailed description of change with enough length to pass validation.",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
        implementation_deadline=datetime.now(timezone.utc) + timedelta(days=3),
    )
    db_session.add(cr)
    db_session.commit()

    cr.submit()
    db_session.commit()

    assert cr.status == CRStatus.PENDING_APPROVAL
    assert cr.submitted_at is not None


def test_cr_number_generation(db_session):
    """Test that CR number is generated correctly"""
    cr_number = ChangeRequest.generate_cr_number()
    assert cr_number is not None
    assert cr_number.startswith("CR-")
    assert len(cr_number) > 3


def test_approval_workflow_transitions(db_session, requester_user, approver_user, project):
    """Test the approval workflow from pending to approved"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Change Y",
        description="Enough description characters for validation.",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    # Approver can approve when PENDING_APPROVAL
    assert cr.can_approve(approver_user)
    cr.approve(approver_user, "Looks good")
    db_session.commit()

    assert cr.status == CRStatus.APPROVED
    assert cr.approver_id == approver_user.id
    assert cr.approval_comments == "Looks good"


def test_rejection_workflow(db_session, requester_user, approver_user, project):
    """Test rejecting a change request"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Change Z",
        description="Description that will be rejected.",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.PENDING_APPROVAL,
    )
    db_session.add(cr)
    db_session.commit()

    # Approver can reject
    assert cr.can_approve(approver_user)
    cr.reject(approver_user, "Not needed at this time")
    db_session.commit()

    assert cr.status == CRStatus.REJECTED
    assert cr.rejection_reason == "Not needed at this time"


def test_implementation_workflow(db_session, requester_user, approver_user, implementer_user, project):
    """Test implementing an approved change request"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")
    add_member(project, implementer_user, "implementer")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Implement feature",
        description="Feature to implement.",
        priority=CRPriority.HIGH,
        requester_id=requester_user.id,
        status=CRStatus.APPROVED,
        implementer_id=implementer_user.id,
    )
    db_session.add(cr)
    db_session.commit()

    # Implementer can start implementation
    cr.start_implementation(implementer_user)
    db_session.commit()
    assert cr.status == CRStatus.IN_PROGRESS

    # Implementer completes implementation (using complete_implementation method)
    cr.complete_implementation()
    db_session.commit()
    assert cr.status == CRStatus.IMPLEMENTED


def test_closure_workflow(db_session, requester_user, approver_user, project):
    """Test closing an implemented change request"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Close CR",
        description="CR to be closed.",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.IMPLEMENTED,
        approver_id=approver_user.id,
    )
    db_session.add(cr)
    db_session.commit()

    # Close CR
    cr.close(approver_user, "Verified and working")
    db_session.commit()
    
    assert cr.status == CRStatus.CLOSED
    assert cr.closure_comments == "Verified and working"
    assert cr.closed_date is not None


def test_rollback_workflow(db_session, requester_user, approver_user, project):
    """Test rolling back an implemented change request"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Rollback CR",
        description="CR to be rolled back.",
        priority=CRPriority.CRITICAL,
        requester_id=requester_user.id,
        status=CRStatus.IMPLEMENTED,
        rollback_plan="Restore previous version from backup",
    )
    db_session.add(cr)
    db_session.commit()

    # Rollback CR
    cr.rollback(approver_user, "Issues found in production")
    db_session.commit()
    
    assert cr.status == CRStatus.ROLLED_BACK
    assert cr.rollback_reason == "Issues found in production"
    assert cr.rolled_back_at is not None


def test_risk_level_assignment(db_session, requester_user, project):
    """Test that risk levels can be assigned to CRs"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="High risk change",
        description="This change has high risk.",
        priority=CRPriority.HIGH,
        risk_level=CRRiskLevel.HIGH,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
    )
    db_session.add(cr)
    db_session.commit()

    assert cr.risk_level == CRRiskLevel.HIGH


def test_timeline_tracking(db_session, requester_user, project):
    """Test that timeline events are tracked"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Timeline test",
        description="Test timeline tracking.",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
    )
    db_session.add(cr)
    db_session.commit()

    cr.submit()
    db_session.commit()

    timeline = cr.get_timeline()
    assert timeline is not None
    assert len(timeline) > 0
