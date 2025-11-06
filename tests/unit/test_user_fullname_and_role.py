def test_user_full_name_and_roles(db_session, requester_user, admin_user):
    requester_user.first_name = "Jane"
    requester_user.last_name = "Doe"
    db_session.commit()
    assert requester_user.full_name == "Jane Doe"
    assert requester_user.has_role("requester") is True
    assert requester_user.is_admin() is False
    assert admin_user.is_admin() is True
