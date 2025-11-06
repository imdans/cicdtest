# Project Structure

This document provides a comprehensive overview of the Change Management Software project structure with detailed explanations of each file and directory.

```
PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers/
│
├── .github/                                    # GitHub-specific configuration
│   ├── CODEOWNERS                             # Define code owners for PR reviews
│   └── workflows/                             # GitHub Actions CI/CD workflows
│       ├── ci-cd.yml                          # Continuous Integration/Deployment pipeline
│       └── merge-ready-pr.yml                 # PR merge validation workflow
│
├── .venv/                                      # Python virtual environment (local only, not in repo)
│
├── app/                                        # Main application package
│   ├── __init__.py                            # Flask app factory and initialization
│   ├── config.py                              # Application configuration classes (Dev/Test/Prod)
│   ├── extensions.py                          # Flask extensions initialization (db, login_manager, etc.)
│   │
│   ├── admin/                                 # Admin management blueprint
│   │   ├── __init__.py                       # Blueprint registration
│   │   └── routes.py                         # Admin routes: dashboard, user/project management
│   │
│   ├── api/                                   # REST API endpoints
│   │   ├── __init__.py                       # API blueprint registration
│   │   ├── audit.py                          # Audit log API endpoints
│   │   ├── auth.py                           # Authentication API endpoints
│   │   └── change_requests.py                # Change Request API endpoints
│   │
│   ├── audit/                                 # Audit logging system
│   │   ├── __init__.py                       # Audit blueprint registration
│   │   ├── events.py                         # Audit event type definitions
│   │   ├── logger.py                         # Audit logging utility functions
│   │   └── routes.py                         # Audit log viewing routes
│   │
│   ├── auth/                                  # Authentication & Authorization
│   │   ├── __init__.py                       # Auth blueprint registration
│   │   ├── decorators.py                     # RBAC decorators (admin_required, permission_required)
│   │   ├── forms.py                          # Authentication forms (Login, MFA, Profile)
│   │   ├── mfa.py                            # Multi-Factor Authentication logic
│   │   ├── rbac.py                           # Role-Based Access Control utilities
│   │   └── routes.py                         # Auth routes: login, logout, profile, MFA
│   │
│   ├── change_requests/                      # Change Request management
│   │   ├── __init__.py                       # CR blueprint registration
│   │   ├── forms.py                          # CR forms (Create, Edit, Approve, Rollback, Close)
│   │   ├── routes.py                         # CR routes: CRUD operations, workflow transitions
│   │   └── services.py                       # CR business logic and helper functions
│   │
│   ├── models/                               # Database models (SQLAlchemy ORM)
│   │   ├── __init__.py                       # Models package initialization and exports
│   │   ├── audit.py                          # AuditLog model for tracking all system events
│   │   ├── change_request.py                 # ChangeRequest, CRAttachment, CRComment models
│   │   ├── project.py                        # Project and ProjectMembership models
│   │   ├── role.py                           # Role and Permission models for RBAC
│   │   ├── user.py                           # User model with authentication methods
│   │   └── user_invitation.py                # UserInvitation model for user onboarding
│   │
│   ├── services/                             # Business logic services
│   │   ├── __init__.py                       # Services package initialization
│   │   ├── email_service.py                  # Email notification service (SMTP)
│   │   └── sla_monitor.py                    # SLA deadline monitoring background service
│   │
│   └── utils/                                # Utility functions
│       ├── __init__.py                       # Utils package initialization
│       ├── security.py                       # Security utilities (token generation, etc.)
│       └── validators.py                     # Custom validation functions
│
├── docs/                                      # Documentation
│   ├── api.md                                # API documentation and endpoint reference
│   ├── developer-guide.md                    # Developer setup and contribution guide
│   └── user-guide.md                         # End-user manual and feature guide
│
├── instance/                                  # Instance-specific files (not in repo)
│   └── dev.db                                # SQLite database file (development)
│
├── logs/                                      # Application log files (not in repo)
│   └── app.log                               # Main application log
│
├── migrations/                               # Database migrations (Flask-Migrate/Alembic)
│   ├── alembic.ini                           # Alembic configuration
│   ├── env.py                                # Migration environment setup
│   ├── README                                # Migration instructions
│   ├── script.py.mako                        # Migration script template
│   └── versions/                             # Migration version files
│       └── *.py                              # Individual migration scripts
│
├── scripts/                                  # Utility scripts
│   ├── create_admin.py                       # Script to create admin users
│   ├── create_user.py                        # Script to create regular users
│   ├── init_db.py                            # Database initialization script
│   ├── migrate_invitations.py                # Migration script for user invitations
│   ├── migrate_to_projects.py                # Migration script for project system
│   └── rollback_projects.py                  # Script to rollback project migrations
│
├── static/                                    # Static files (CSS, JavaScript, uploads)
│   ├── site.css                              # Main stylesheet (dark theme)
│   ├── js/                                   # JavaScript files
│   │   └── main.js                           # Main JavaScript (toast notifications, etc.)
│   └── uploads/                              # User-uploaded files (CR attachments)
│       ├── .gitkeep                          # Keep empty directory in git
│       └── *.{pdf,png,jpg,txt,...}           # Uploaded attachment files
│
├── templates/                                # Jinja2 HTML templates
│   ├── base.html                             # Base template with navigation and layout
│   ├── home.html                             # Home/landing page
│   ├── about.html                            # About page
│   │
│   ├── admin/                                # Admin dashboard templates
│   │   ├── create_project.html               # Project creation form
│   │   ├── create_user.html                  # User creation form
│   │   ├── dashboard.html                    # Admin dashboard with statistics
│   │   ├── project_detail.html               # Project details and member management
│   │   ├── projects.html                     # Project list view
│   │   ├── reports.html                      # System reports and analytics
│   │   └── users.html                        # User list and management
│   │
│   ├── audit/                                # Audit logging templates
│   │   ├── logs.html                         # Audit log viewer with filters
│   │   └── report.html                       # Audit report generation
│   │
│   ├── auth/                                 # Authentication templates
│   │   ├── accept_invitation.html            # User invitation acceptance
│   │   ├── login.html                        # Login form
│   │   ├── mfa_verify.html                   # MFA verification form
│   │   ├── profile.html                      # User profile and settings
│   │   └── unauthorized.html                 # Unauthorized access page
│   │
│   └── change_requests/                      # Change Request templates
│       ├── approve.html                      # CR approval form (approver view)
│       ├── close.html                        # CR closure form (approver view)
│       ├── create.html                       # CR creation form
│       ├── edit.html                         # CR editing form
│       ├── implement.html                    # CR implementation form (implementer view)
│       ├── list.html                         # CR list view with filters
│       ├── rollback.html                     # CR rollback form
│       └── view.html                         # CR detail view
│
├── tests/                                    # Test suite
│   ├── __init__.py                           # Tests package initialization
│   ├── conftest.py                           # Pytest configuration and fixtures (imports from unit)
│   │
│   ├── integration/                          # Integration tests (full workflows)
│   │   ├── __init__.py                       # Integration tests package
│   │   ├── test_admin_operations.py          # Admin operations integration tests
│   │   ├── test_admin_role_management_and_login.py  # Admin role tests
│   │   ├── test_audit_logout_event.py        # Logout audit logging tests
│   │   ├── test_auth_login_and_audit.py      # Login and audit integration
│   │   ├── test_cr_submit_and_sla.py         # CR submission with SLA tests
│   │   ├── test_cr_submit_flow.py            # CR submission workflow tests
│   │   ├── test_sla_tracking_basic.py        # Basic SLA tracking tests
│   │   └── test_workflow_approval_and_email.py  # Approval workflow with email tests
│   │
│   └── unit/                                 # Unit tests (individual components)
│       ├── __init__.py                       # Unit tests package
│       ├── conftest.py                       # Unit test fixtures (app, users, projects)
│       ├── test_audit.py                     # Audit logging tests
│       ├── test_auth.py                      # Authentication tests
│       ├── test_change_requests.py           # Change Request model tests
│       ├── test_cr_deadline_helpers.py       # CR deadline helper function tests
│       ├── test_cr_edit_submit_flow.py       # CR edit and submit tests
│       ├── test_notifications.py             # Email notification tests
│       ├── test_project.py                   # Project model tests
│       ├── test_role_permission_add_remove.py  # Role/permission tests
│       ├── test_rollback_and_admin.py        # Rollback functionality tests
│       ├── test_security_serializer.py       # Security token tests
│       ├── test_sla.py                       # SLA monitoring tests
│       ├── test_user_failed_login.py         # Failed login attempt tests
│       ├── test_user_fullname_and_role.py    # User name and role tests
│       ├── test_user_model.py                # User model tests
│       ├── test_user_password.py             # Password hashing tests
│       └── test_validators_not_empty.py      # Validator function tests
│
├── .dockerignore                             # Files to exclude from Docker builds
├── .env                                      # Environment variables (create locally, not in repo)
├── .gitignore                                # Git ignore rules
├── app.py                                    # Application entry point
├── dev-requirements.txt                      # Development dependencies (pytest, coverage, etc.)
├── pyproject.toml                            # Python project metadata (for tools like Black)
├── README.md                                 # Project overview and basic documentation
├── requirements.txt                          # Production dependencies
├── runtime.txt                               # Python runtime version (for deployment)
├── SETUP.md                                  # Comprehensive setup instructions
└── setup.sh                                  # Quick setup script (bash)
```

---

## Key Components Explained

### Application Structure (app/)

The application follows a **blueprint-based architecture** for modularity:

- **Blueprints**: Each major feature (auth, admin, change_requests, audit, api) is a separate blueprint
- **Models**: SQLAlchemy ORM models define database schema
- **Services**: Business logic separated from route handlers
- **Extensions**: Shared Flask extensions (database, login manager, CSRF protection)

### Authentication & Authorization

- **Multi-Factor Authentication (MFA)**: TOTP-based for admin users
- **Role-Based Access Control (RBAC)**: 4 roles (Admin, Approver, Implementer, Requester)
- **Session Management**: Secure sessions with configurable timeout
- **Audit Logging**: All authentication events are logged

### Change Request Workflow

1. **Draft** → Create and edit CR
2. **Submitted** → Submit for approval
3. **Pending Approval** → Awaiting approver decision
4. **Approved** → Approved by approver, assigned to implementer
5. **In Progress** → Implementation started
6. **Implemented** → Implementation complete
7. **Closed** → Verified and closed by approver
8. **Rolled Back** → Reverted due to issues (alternative path from Implemented)
9. **Rejected** → Rejected by approver (alternative path from Pending Approval)

### SLA Monitoring

- **Background Scheduler**: Checks deadlines every hour
- **24-hour Warning**: Email sent when deadline is within 24 hours
- **Breach Detection**: Automatic detection and notification of missed deadlines
- **Rollback Plan**: Required for all change requests

### Email Notifications

Email notifications are sent for:
- CR submission (to approvers)
- CR approval (to implementer and requester)
- CR rejection (to requester)
- SLA warnings (24-hour notice)
- SLA breaches (to admins)
- CR implementation (to approver)
- CR closure (to requester)

### Project-Based Access Control

- **Projects**: Organize change requests by project
- **Project Membership**: Users assigned to projects with specific roles
- **Role-Based Views**: Users only see CRs in their assigned projects
- **Admin Isolation**: Admins only manage projects they created

### Security Features

- **Password Hashing**: Werkzeug secure password hashing
- **CSRF Protection**: Flask-WTF CSRF tokens
- **Rate Limiting**: Login attempt rate limiting
- **Session Security**: HTTPOnly, SameSite cookies
- **TLS Support**: Production TLS 1.2+ enforcement
- **Audit Trail**: Immutable audit logs for all actions

### Database

- **Development**: SQLite (instance/dev.db)
- **Production**: PostgreSQL recommended
- **Migrations**: Flask-Migrate (Alembic) for schema versioning
- **Soft Deletes**: Users and projects use is_active flag

### Testing

- **Unit Tests**: Test individual components (models, services, utilities)
- **Integration Tests**: Test complete workflows and interactions
- **Coverage**: Comprehensive test coverage for all critical paths
- **Fixtures**: Reusable test data (users, projects, CRs)

---

## File Naming Conventions

- **Python files**: Snake_case (e.g., `user_model.py`, `email_service.py`)
- **HTML templates**: Lowercase with hyphens (e.g., `create-project.html`)
- **CSS/JS files**: Lowercase (e.g., `site.css`, `main.js`)
- **Test files**: Prefixed with `test_` (e.g., `test_auth.py`)

## Import Structure

```python
# Standard library imports
import os
from datetime import datetime

# Third-party imports
from flask import Flask, render_template
from flask_login import login_required

# Local application imports
from app.models import User, ChangeRequest
from app.services import EmailService
```

---

## Configuration Environments

The application supports three environments (defined in `app/config.py`):

1. **Development** (`FLASK_ENV=development`)
   - Debug mode enabled
   - SQLite database
   - Detailed error pages
   - Auto-reload on code changes

2. **Testing** (`FLASK_ENV=testing`)
   - In-memory SQLite database
   - CSRF disabled
   - Fast test execution

3. **Production** (`FLASK_ENV=production`)
   - Debug mode disabled
   - PostgreSQL recommended
   - TLS enforcement
   - Gunicorn WSGI server

---

## Entry Points

- **Web Application**: `app.py` (Flask development server)
- **WSGI Production**: `app:app` (Gunicorn/uWSGI)
- **CLI Commands**: `flask` commands (db, shell, etc.)
- **Tests**: `pytest` (from project root)

---

## Directory Ownership

- **app/**: Core application code (developers)
- **templates/**: Frontend developers
- **static/**: Frontend developers
- **tests/**: QA and developers
- **migrations/**: Database administrators
- **scripts/**: DevOps and administrators
- **docs/**: Technical writers and developers

---

This structure follows **Flask best practices** and **separation of concerns** principles for maintainability and scalability.
