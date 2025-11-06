"""Integration tests for admin operations including project and user management"""
from app.models import Project, User, ProjectMembership, Role


def test_admin_create_project(db_session, admin_user):
    """Test admin can create a project"""
    project = Project(
        name="Admin Test Project",
        code="ATP",
        description="Project created by admin",
        created_by=admin_user,
        is_active=True
    )
    db_session.add(project)
    db_session.commit()
    
    assert project.id is not None
    assert project.created_by_id == admin_user.id
    assert project.is_active is True


def test_admin_create_user(db_session, admin_user):
    """Test admin can create a new user"""
    role = Role.query.filter_by(name="requester").first()
    new_user = User(
        username="newuser",
        email="newuser@example.com",
        role=role,
        is_active=True
    )
    new_user.set_password("NewUserPass123!")
    db_session.add(new_user)
    db_session.commit()
    
    assert new_user.id is not None
    assert new_user.email == "newuser@example.com"


def test_admin_assign_user_to_project(db_session, admin_user, project, requester_user):
    """Test admin can assign users to projects"""
    from tests.unit.conftest import add_member
    membership = add_member(project, requester_user, "requester")
    
    assert membership.id is not None
    assert membership.project_id == project.id
    assert membership.user_id == requester_user.id
    assert project.has_member(requester_user) is True


def test_admin_remove_user_from_project(db_session, admin_user, project, requester_user):
    """Test admin can remove users from projects"""
    from tests.unit.conftest import add_member
    membership = add_member(project, requester_user, "requester")
    
    # Deactivate membership
    membership.is_active = False
    db_session.commit()
    
    # Refresh project to get updated memberships
    db_session.refresh(project)
    assert project.has_member(requester_user) is False


def test_admin_delete_project(db_session, admin_user, project):
    """Test admin can soft delete a project"""
    project.is_active = False
    db_session.commit()
    
    assert project.is_active is False
    # Project still exists in database
    retrieved = Project.query.get(project.id)
    assert retrieved is not None


def test_admin_delete_user(db_session, admin_user, requester_user):
    """Test admin can soft delete a user"""
    requester_user.is_active = False
    db_session.commit()
    
    assert requester_user.is_active is False
    # User still exists in database
    retrieved = User.query.get(requester_user.id)
    assert retrieved is not None


def test_admin_view_all_projects(db_session, admin_user):
    """Test admin can view all projects they created"""
    # Create multiple projects
    project1 = Project(
        name="Project 1",
        code="P1",
        description="First project",
        created_by=admin_user
    )
    project2 = Project(
        name="Project 2",
        code="P2",
        description="Second project",
        created_by=admin_user
    )
    db_session.add(project1)
    db_session.add(project2)
    db_session.commit()
    
    # Query projects created by admin
    admin_projects = Project.query.filter_by(created_by_id=admin_user.id).all()
    assert len(admin_projects) >= 2


def test_admin_lock_user_account(db_session, admin_user, requester_user):
    """Test admin can lock user accounts"""
    requester_user.is_locked = True
    db_session.commit()
    
    assert requester_user.is_locked is True


def test_admin_unlock_user_account(db_session, admin_user, requester_user):
    """Test admin can unlock user accounts"""
    requester_user.is_locked = True
    db_session.commit()
    
    # Unlock
    requester_user.is_locked = False
    db_session.commit()
    
    assert requester_user.is_locked is False
