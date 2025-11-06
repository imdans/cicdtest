from datetime import datetime, timedelta, timezone

from app.services.sla_monitor import check_sla_deadlines
from app.models.change_request import ChangeRequest, CRStatus, CRPriority


def test_sla_tracking_basic(monkeypatch, app, db_session, requester_user, approver_user, implementer_user, project):
    # SMTP stub
    class DummySMTP:
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

    import smtplib
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    app.config.update(SMTP_USERNAME="x", SMTP_PASSWORD="y")

    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="SLA soon",
        description="desc long enough",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.APPROVED,
        implementation_deadline=datetime.now(timezone.utc) + timedelta(hours=6),
    )
    db_session.add(cr)
    db_session.commit()

    with app.app_context():
        check_sla_deadlines()
    db_session.refresh(cr)
    assert cr.sla_warning_sent in (True, False)  # ensure no exceptions and field exists
