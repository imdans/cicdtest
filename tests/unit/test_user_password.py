def test_user_password_hashing_and_check(db_session, requester_user):
    requester_user.set_password("secret123")
    db_session.commit()
    assert requester_user.check_password("secret123") is True
    assert requester_user.check_password("wrong") is False
