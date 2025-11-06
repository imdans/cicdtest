from app.models.role import Role, Permission


def test_role_permissions_add_remove(db_session):
    role = Role(name="tester", description="Tester role")
    perm = Permission(name="run_tests", description="Run tests")
    db_session.add(role)
    db_session.add(perm)
    db_session.commit()

    role.add_permission(perm)
    db_session.commit()
    assert role.has_permission("run_tests") is True

    role.remove_permission(perm)
    db_session.commit()
    assert role.has_permission("run_tests") is False
