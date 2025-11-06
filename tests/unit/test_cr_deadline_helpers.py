from datetime import datetime, timedelta, timezone

from app.models.change_request import ChangeRequest, CRStatus, CRPriority


def test_change_request_deadline_helpers(db_session, requester_user, project):
    # No deadline
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="No deadline",
        description="desc long enough",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.APPROVED,
    )
    db_session.add(cr)
    db_session.commit()
    assert cr.time_until_deadline() is None
    assert cr.is_deadline_warning_needed() is False

    # With deadline but warning already sent -> no new warning
    cr2 = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Deadline but warned",
        description="desc long enough",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.APPROVED,
        implementation_deadline=datetime.now(timezone.utc) + timedelta(hours=6),
        sla_warning_sent=True,
    )
    db_session.add(cr2)
    db_session.commit()
    assert cr2.is_deadline_warning_needed() is False
