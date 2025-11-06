"""Unit tests for project models and functionality"""
from app.models import Project, ProjectMembership, Role


def test_project_creation(db_session, admin_user):
    """Test creating a new project"""
    project = Project(
        name="Test Project Alpha",
        code="TPA",
        description="A test project for unit testing",
        created_by=admin_user
    )
    db_session.add(project)
    db_session.commit()

    assert project.id is not None
    assert project.name == "Test Project Alpha"
    assert project.code == "TPA"
    assert project.created_by_id == admin_user.id
    assert project.is_active is True


def test_project_membership(db_session, project, requester_user):
    """Test adding members to a project"""
    from tests.unit.conftest import add_member
    membership = add_member(project, requester_user, "requester")
    
    assert membership.id is not None
    assert membership.project_id == project.id
    assert membership.user_id == requester_user.id
    assert membership.is_active is True


def test_get_members_by_role(db_session, project, requester_user, approver_user):
    """Test getting project members by role"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    add_member(project, approver_user, "approver")
    
    requesters = project.get_members_by_role("requester")
    assert len(requesters) == 1
    assert requesters[0].id == requester_user.id
    
    approvers = project.get_members_by_role("approver")
    assert len(approvers) == 1
    assert approvers[0].id == approver_user.id


def test_has_member(db_session, project, requester_user, approver_user):
    """Test checking if user is a project member"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    
    assert project.has_member(requester_user) is True
    assert project.has_member(approver_user) is False


def test_get_user_role(db_session, project, requester_user):
    """Test getting user's role in a project"""
    from tests.unit.conftest import add_member
    add_member(project, requester_user, "requester")
    
    role = project.get_user_role(requester_user)
    assert role is not None
    assert role.name == "requester"


def test_project_to_dict(db_session, project):
    """Test converting project to dictionary"""
    project_dict = project.to_dict()
    
    assert 'id' in project_dict
    assert 'name' in project_dict
    assert 'code' in project_dict
    assert 'is_active' in project_dict
    assert 'member_count' in project_dict
    assert project_dict['name'] == project.name


def test_project_soft_delete(db_session, project):
    """Test soft deleting a project"""
    project.is_active = False
    db_session.commit()
    
    assert project.is_active is False
    # Project still exists in database
    retrieved = Project.query.get(project.id)
    assert retrieved is not None
    assert retrieved.is_active is False
