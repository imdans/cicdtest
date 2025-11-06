def test_user_failed_login_lock_and_reset(db_session, requester_user):
    for _ in range(5):
        requester_user.increment_failed_login()
    assert requester_user.is_locked is True
    requester_user.reset_failed_login()
    assert requester_user.failed_login_attempts == 0
    assert requester_user.is_locked is False
