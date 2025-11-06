from app.models.change_request import ChangeRequest, CRStatus, CRPriority


def test_change_request_edit_and_submit_flow(db_session, requester_user, admin_user, project):
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Edit until approved",
        description="desc long enough",
        priority=CRPriority.MEDIUM,
        requester_id=requester_user.id,
        status=CRStatus.DRAFT,
    )
    db_session.add(cr)
    db_session.commit()

    # Requester can edit draft
    assert cr.can_edit(requester_user) is True
    # Admin can edit before approval
    assert cr.can_edit(admin_user) is True
    # Submit -> still editable until approved
    cr.submit()
    db_session.commit()
    assert cr.status == CRStatus.PENDING_APPROVAL
    assert cr.can_edit(requester_user) is True
    # After approval -> no one can edit
    cr.status = CRStatus.APPROVED
    db_session.commit()
    assert cr.can_edit(requester_user) is False
    assert cr.can_edit(admin_user) is False
