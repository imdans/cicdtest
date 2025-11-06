import os
import uuid
import pytest
from flask import Flask

from app import create_app
from app.extensions import db as _db
from app.models import Role, Permission, User, Project, ProjectMembership


@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SERVER_NAME": "localhost",
    })
    with app.app_context():
        _db.create_all()
        # seed default roles/permissions if available
        try:
            Role.insert_default_roles()
        except Exception:
            _db.session.rollback()
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db_session(app):
    with app.app_context():
        yield _db.session
        _db.session.rollback()


def _get_role(name: str) -> Role:
    role = Role.query.filter_by(name=name).first()
    if not role:
        role = Role(name=name)
        _db.session.add(role)
        _db.session.commit()
    return role


@pytest.fixture()
def admin_user(db_session):
    role = _get_role("admin")
    suffix = uuid.uuid4().hex[:8]
    user = User(username=f"admin_{suffix}", email=f"admin_{suffix}@example.com", role=role, is_active=True)
    user.set_password("Password123!")
    user.mfa_enabled = True
    user.generate_mfa_secret()
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def approver_user(db_session):
    role = _get_role("approver")
    suffix = uuid.uuid4().hex[:8]
    user = User(username=f"approver_{suffix}", email=f"approver_{suffix}@example.com", role=role, is_active=True)
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def implementer_user(db_session):
    role = _get_role("implementer")
    suffix = uuid.uuid4().hex[:8]
    user = User(username=f"impl_{suffix}", email=f"impl_{suffix}@example.com", role=role, is_active=True)
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def requester_user(db_session):
    role = _get_role("requester")
    suffix = uuid.uuid4().hex[:8]
    user = User(username=f"req_{suffix}", email=f"req_{suffix}@example.com", role=role, is_active=True)
    user.set_password("Password123!")
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture()
def project(db_session, admin_user):
    suffix = uuid.uuid4().hex[:6]
    project = Project(name=f"Test Project {suffix}", code=f"TP{suffix}", description="A test project", created_by=admin_user)
    db_session.add(project)
    db_session.commit()
    return project


def add_member(project, user, role_name=None):
    role = user.role if not role_name else Role.query.filter_by(name=role_name).first()
    pm = ProjectMembership(project=project, user=user, role=role, is_active=True)
    _db.session.add(pm)
    _db.session.commit()
    return pm
