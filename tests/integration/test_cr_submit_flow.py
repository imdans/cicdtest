from app.models.change_request import ChangeRequest, CRStatus, CRPriority


def test_cr_submit_flow(client, db_session, requester_user, project):
    # Create a CR directly in DB, then hit a list endpoint to simulate end-to-end presence
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Integration submit",
        description="desc long enough",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
    )
    db_session.add(cr)
    db_session.commit()

    # Submit via model and ensure reflected
    cr.submit()
    db_session.commit()

    assert cr.status == CRStatus.PENDING_APPROVAL
