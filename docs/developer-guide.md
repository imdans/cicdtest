# Developer Guide

This guide covers development setup, architecture, and contribution guidelines for the Change Management System.

## Development Setup

### Prerequisites

- Python 3.8+ 
- pip and virtualenv
- SQLite (dev) or MySQL/PostgreSQL (production)
- Git

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers

# Run setup script
chmod +x workflow.sh
./workflow.sh

# Activate virtual environment
source .venv/bin/activate

# Run the application
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

### Manual Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/init_db.py

# Create admin user
python scripts/create_admin.py

# Run application
flask run
```

## Project Structure

```
app/
├── __init__.py                 # Flask app factory with TLS
├── config.py                   # Configuration classes
├── extensions.py               # Flask extensions initialization
├── models/                     # Database models
│   ├── user.py                # User with MFA support
│   ├── role.py                # Roles and permissions (RBAC)
│   ├── audit.py               # Immutable audit logs
│   └── change_request.py      # Change request models
├── auth/                       # Authentication module
│   ├── routes.py              # Login, MFA, logout
│   ├── forms.py               # Authentication forms
│   └── decorators.py          # RBAC decorators
├── audit/                      # Audit logging
│   ├── logger.py              # Audit logging utilities
│   └── routes.py              # Audit log viewing/export
└── change_requests/            # Change request management
    ├── routes.py              # CRUD operations
    └── forms.py               # CR forms

tests/
├── conftest.py                # Pytest fixtures
├── test_auth.py               # Authentication tests
├── test_audit.py              # Audit logging tests
└── test_change_requests.py    # CR tests
```

## Architecture

### Application Factory Pattern

The application uses the factory pattern (`create_app()`) to support multiple configurations:

```python
from app import create_app

# Development
app = create_app('development')

# Testing  
app = create_app('testing')

# Production
app = create_app('production')
```

### Database Models

**User Model** (`app/models/user.py`)
- Authentication with password hashing
- MFA support with TOTP
- Role-based permissions
- Account lockout after failed attempts

**Role & Permission Models** (`app/models/role.py`)
- Many-to-many relationship
- Default roles: requester, approver, implementer, admin
- Fine-grained permission system

**ChangeRequest Model** (`app/models/change_request.py`)
- Full lifecycle tracking
- File attachments
- Comments and approval workflow
- Rollback support

**AuditLog Model** (`app/models/audit.py`)
- Immutable audit trail
- Event type categorization
- IP tracking and metadata

### Security Features

**TLS 1.2+ Enforcement** (`CMS-SR-001`)
```python
# In production
ssl_context = create_ssl_context(app)
app.run(ssl_context=ssl_context)
```

**Rate Limiting**
```python
from app.extensions import limiter

@limiter.limit("5 per minute")
def login():
    ...
```

**CSRF Protection**
- Enabled globally via Flask-WTF
- Automatic token validation on POST requests

**MFA for Administrators** (`CMS-F-002`)
```python
if user.is_admin() and user.mfa_enabled:
    # Require TOTP verification
    return redirect(url_for('auth.verify_mfa'))
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run with verbose output
pytest -v
```

### Test Structure

Tests are organized by feature:
- `test_auth.py` - Authentication (CMS-F-001, CMS-F-002, CMS-F-003)
- `test_audit.py` - Audit logging (CMS-F-013, CMS-F-014)
- `test_change_requests.py` - CR management (CMS-F-005, CMS-F-006, CMS-F-007)

## Database Migrations

Using Flask-Migrate (Alembic):

```bash
# Initialize migrations (first time only)
flask db init

# Create migration after model changes
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback migration
flask db downgrade
```

## Configuration

Environment-specific settings in `app/config.py`:

**Development:**
- SQLite database
- Debug mode enabled
- No HTTPS enforcement

**Testing:**
- In-memory SQLite
- CSRF disabled
- Fast password hashing

**Production:**
- PostgreSQL/MySQL recommended
- HTTPS enforced
- Secure cookies

### Environment Variables

```bash
# Required for production
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="postgresql://user:pass@host/dbname"
export FLASK_ENV=production

# Optional
export SSL_CERT_FILE="/path/to/cert.pem"
export SSL_KEY_FILE="/path/to/key.pem"
```

## Adding New Features

### 1. Create Model

```python
# app/models/new_model.py
from app.extensions import db

class NewModel(db.Model):
    __tablename__ = 'new_table'
    id = db.Column(db.Integer, primary_key=True)
    # ... fields
```

### 2. Create Routes

```python
# app/new_module/routes.py
from flask import Blueprint

new_bp = Blueprint('new', __name__)

@new_bp.route('/')
def index():
    return render_template('new/index.html')
```

### 3. Register Blueprint

```python
# app/__init__.py
from .new_module.routes import new_bp
app.register_blueprint(new_bp, url_prefix='/new')
```

### 4. Create Tests

```python
# tests/test_new_feature.py
def test_new_feature(client):
    response = client.get('/new/')
    assert response.status_code == 200
```

## Code Style

### Python Style
- Follow PEP 8
- Use type hints where helpful
- Document functions with docstrings
- Keep functions focused and small

### Imports
```python
# Standard library
import os
import sys

# Third-party
from flask import Flask

# Local
from app.models import User
```

### Naming Conventions
- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`

## Debugging

### Enable Debug Mode

```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
flask run
```

### View Logs

```python
app.logger.debug('Debug message')
app.logger.info('Info message')
app.logger.warning('Warning message')
app.logger.error('Error message')
```

### Database Inspection

```bash
# SQLite
sqlite3 dev.db
> .tables
> SELECT * FROM users;

# Python shell
flask shell
>>> from app.models import User
>>> User.query.all()
```

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with workers
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:create_app('production')"]
```

### Security Checklist

- [ ] Change default admin password
- [ ] Set strong SECRET_KEY
- [ ] Use HTTPS (TLS 1.2+)
- [ ] Configure firewall
- [ ] Enable MFA for admins
- [ ] Regular security audits
- [ ] Keep dependencies updated
- [ ] Backup database regularly

## Contributing

1. Create feature branch
2. Make changes with tests
3. Run full test suite
4. Submit pull request
5. Wait for code review

## Resources

- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Flask-Login: https://flask-login.readthedocs.io/
- pytest: https://docs.pytest.org/

