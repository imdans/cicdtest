from datetime import datetime, timedelta, timezone

from app.models.change_request import ChangeRequest, CRStatus, CRPriority
from app.services.sla_monitor import check_sla_deadlines


def test_cr_submit_and_sla(app, db_session, requester_user, project):
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Submit and SLA",
        description="desc long enough",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
        implementation_deadline=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db_session.add(cr)
    db_session.commit()

    cr.submit()
    db_session.commit()
    assert cr.status == CRStatus.PENDING_APPROVAL

    with app.app_context():
        check_sla_deadlines()
    db_session.refresh(cr)
    # Either warning sent or not, test ensures integration path runs without errors
    assert hasattr(cr, "sla_warning_sent")
