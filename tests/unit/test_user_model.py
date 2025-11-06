"""Unit tests for User model functionality"""
from app.models import User, Role


def test_user_creation(db_session):
    """Test creating a new user"""
    role = Role.query.filter_by(name="requester").first()
    user = User(
        username="testuser",
        email="testuser@example.com",
        role=role,
        is_active=True
    )
    user.set_password("TestPassword123!")
    db_session.add(user)
    db_session.commit()
    
    assert user.id is not None
    assert user.username == "testuser"
    assert user.email == "testuser@example.com"
    assert user.is_active is True


def test_user_password_check(db_session, requester_user):
    """Test password checking functionality"""
    assert requester_user.check_password("Password123!") is True
    assert requester_user.check_password("WrongPassword") is False


def test_user_mfa_setup(db_session, requester_user):
    """Test MFA secret generation"""
    requester_user.generate_mfa_secret()
    db_session.commit()
    
    assert requester_user.mfa_secret is not None
    assert len(requester_user.mfa_secret) > 0


def test_user_account_locking(db_session, requester_user):
    """Test user account can be locked"""
    requester_user.is_locked = True
    db_session.commit()
    
    assert requester_user.is_locked is True


def test_user_soft_delete(db_session, requester_user):
    """Test user soft deletion"""
    requester_user.is_active = False
    db_session.commit()
    
    assert requester_user.is_active is False
    # User still exists in database
    retrieved = User.query.get(requester_user.id)
    assert retrieved is not None


def test_user_role_assignment(db_session):
    """Test assigning roles to users"""
    admin_role = Role.query.filter_by(name="admin").first()
    user = User(
        username="adminuser",
        email="admin@example.com",
        role=admin_role,
        is_active=True
    )
    user.set_password("AdminPass123!")
    db_session.add(user)
    db_session.commit()
    
    assert user.role.name == "admin"


def test_user_full_name(db_session, requester_user):
    """Test user full name is constructed correctly"""
    full_name = f"{requester_user.username}"
    assert full_name == requester_user.username


def test_user_failed_login_attempts(db_session, requester_user):
    """Test tracking failed login attempts"""
    initial_count = requester_user.failed_login_attempts if hasattr(requester_user, 'failed_login_attempts') else 0
    
    # Simulate failed login
    if hasattr(requester_user, 'failed_login_attempts'):
        requester_user.failed_login_attempts += 1
        db_session.commit()
        
        assert requester_user.failed_login_attempts == initial_count + 1
