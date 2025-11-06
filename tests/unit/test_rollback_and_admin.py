from app.models import ChangeRequest, CRStatus, CRPriority, Role


def test_rollback_execution(db_session, requester_user, implementer_user, project):
    cr = ChangeRequest(
        cr_number=ChangeRequest.generate_cr_number(),
        project_id=project.id,
        title="Rollback test",
        description="long enough description",
        priority=CRPriority.LOW,
        requester_id=requester_user.id,
        status=CRStatus.IMPLEMENTED,
        implementer_id=implementer_user.id,
    )
    db_session.add(cr)
    db_session.commit()

    cr.rollback(implementer_user, "Issue found, revert")
    db_session.commit()

    assert cr.status == CRStatus.ROLLED_BACK
    assert cr.rollback_reason is not None
    assert cr.rolled_back_by_id == implementer_user.id


def test_admin_role_management_basics(db_session):
    # Ensure default roles exist and admin has manage_users permission
    admin = Role.query.filter_by(name="admin").first()
    assert admin is not None
    assert admin.has_permission("manage_users")
