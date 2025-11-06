# Change Management Software - Setup Guide

This guide will walk you through setting up the Change Management Software on your local machine from scratch.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Clone the Repository](#clone-the-repository)
- [Python Environment Setup](#python-environment-setup)
- [Install Dependencies](#install-dependencies)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Create Admin User](#create-admin-user)
- [Run the Application](#run-the-application)
- [Access the Application](#access-the-application)
- [Running Tests](#running-tests)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before you begin, ensure you have the following installed on your system:

- **Python 3.9 or higher** - [Download Python](https://www.python.org/downloads/)
- **Git** - [Download Git](https://git-scm.com/downloads)
- **pip** (Python package manager) - Usually comes with Python
- **virtualenv** or **venv** (for creating virtual environments)

### Verify Prerequisites

```bash
# Check Python version (should be 3.9+)
python3 --version

# Check Git version
git --version

# Check pip version
pip3 --version
```

---

## Clone the Repository

1. Open your terminal/command prompt
2. Navigate to the directory where you want to clone the project
3. Clone the repository:

```bash
git clone https://github.com/pestechnology/PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers.git
```

4. Navigate into the project directory:

```bash
cd PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers
```

---

## Python Environment Setup

It's recommended to use a virtual environment to isolate project dependencies.

### Create Virtual Environment

**On macOS/Linux:**
```bash
python3 -m venv .venv
```

**On Windows:**
```bash
python -m venv .venv
```

### Activate Virtual Environment

**On macOS/Linux:**
```bash
source .venv/bin/activate
```

**On Windows:**
```bash
.venv\Scripts\activate
```

You should see `(.venv)` prefix in your terminal prompt indicating the virtual environment is active.

---

## Install Dependencies

With the virtual environment activated, install all required packages:

```bash
# Upgrade pip to latest version
pip install --upgrade pip

# Install production dependencies
pip install -r requirements.txt

# (Optional) Install development dependencies for testing
pip install -r dev-requirements.txt
```

### Verify Installation

```bash
pip list
```

You should see packages like Flask, SQLAlchemy, Flask-Login, etc.

---

## Environment Configuration

The application uses environment variables for configuration.

### Create `.env` File

Create a `.env` file in the project root directory:

```bash
touch .env
```

### Configure Environment Variables

Open `.env` in your text editor and add the following:

```env
# Flask Configuration
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key-here-change-in-production

# Database Configuration
DATABASE_URL=sqlite:///instance/dev.db

# Email Configuration (Optional - for email notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Change Management System

# Session Configuration
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=3600

# Security Configuration
WTF_CSRF_ENABLED=True
```

**Important Notes:**
- Replace `your-secret-key-here-change-in-production` with a strong random string
- For email notifications, use Gmail App Passwords (not your regular password)
- Set `SESSION_COOKIE_SECURE=True` in production with HTTPS

### Generate Secret Key

To generate a secure secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and use it as your `SECRET_KEY` in `.env`

---

## Database Setup

### Initialize Database

The application uses Flask-Migrate for database migrations.

1. **Initialize the database:**

```bash
flask db upgrade
```

This will create the SQLite database at `instance/dev.db` with all required tables.

2. **Verify Database Creation:**

```bash
ls instance/
```

You should see `dev.db` file.

---

## Create Admin User

You need at least one admin user to access the admin dashboard.

### Using the create_admin Script

```bash
python scripts/create_admin.py
```

Follow the prompts to enter:
- Username
- Email
- Password (minimum 8 characters with uppercase, lowercase, and numbers)

### Alternative: Using Flask Shell

```bash
flask shell
```

Then run:

```python
from app.models import User, Role
from app.extensions import db

# Get admin role
admin_role = Role.query.filter_by(name='admin').first()

# Create admin user
admin = User(
    username='admin',
    email='admin@example.com',
    role=admin_role,
    is_active=True
)
admin.set_password('Admin123!')  # Change this password!
admin.generate_mfa_secret()  # Enable MFA for admin

db.session.add(admin)
db.session.commit()

print(f"Admin user created: {admin.email}")
exit()
```

---

## Run the Application

### Development Server

Start the Flask development server:

```bash
flask run
```

Or alternatively:

```bash
python app.py
```

You should see output like:

```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

### Production Server (Optional)

For production deployment, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## Access the Application

1. Open your web browser
2. Navigate to: **http://127.0.0.1:5000** or **http://localhost:5000**
3. You should see the home page

### Login as Admin

1. Click "Login" or navigate to http://127.0.0.1:5000/auth/login
2. Enter your admin credentials:
   - Email: `admin@example.com`
   - Password: `Admin123!` (or whatever you set)
3. If MFA is enabled, scan the QR code with Google Authenticator and enter the 6-digit code

### Create Projects and Users

1. After logging in as admin, go to the Admin Dashboard
2. Create projects
3. Create users with different roles (requester, approver, implementer)
4. Assign users to projects

---

## Running Tests

The application includes comprehensive unit and integration tests.

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=app --cov-report=html
```

View coverage report by opening `htmlcov/index.html` in your browser.

### Run Specific Test Files

```bash
# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_auth.py
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. **ImportError: No module named 'flask'**

**Solution:** Make sure your virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate  # On macOS/Linux
pip install -r requirements.txt
```

#### 2. **Database not found error**

**Solution:** Initialize the database:
```bash
flask db upgrade
```

#### 3. **Port 5000 already in use**

**Solution:** Either kill the process using port 5000 or run on a different port:
```bash
flask run --port 5001
```

#### 4. **Email notifications not working**

**Solution:** 
- Verify SMTP credentials in `.env`
- For Gmail, use App Passwords instead of regular password
- Enable "Less secure app access" or use OAuth2

#### 5. **Secret key error**

**Solution:** Make sure `SECRET_KEY` is set in your `.env` file

#### 6. **Permission denied when creating database**

**Solution:** Ensure the `instance/` directory exists:
```bash
mkdir -p instance
```

#### 7. **MFA QR code not showing**

**Solution:** Install required packages:
```bash
pip install qrcode pillow
```

---

## Project Structure

```
PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers/
├── app/                    # Main application package
│   ├── __init__.py        # App factory
│   ├── admin/             # Admin blueprint
│   ├── api/               # REST API endpoints
│   ├── auth/              # Authentication & authorization
│   ├── audit/             # Audit logging
│   ├── change_requests/   # Change request management
│   ├── models/            # Database models
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── migrations/            # Database migrations
├── scripts/               # Utility scripts
├── static/                # Static files (CSS, JS, uploads)
├── templates/             # HTML templates
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   └── integration/      # Integration tests
├── instance/             # Instance-specific files (database)
├── logs/                 # Application logs
├── .env                  # Environment variables (create this)
├── app.py                # Application entry point
├── requirements.txt      # Production dependencies
├── dev-requirements.txt  # Development dependencies
└── README.md             # Project documentation
```

---

## Next Steps

After successful setup:

1. **Explore the Admin Dashboard** - Create projects and manage users
2. **Review Documentation** - Check `docs/` folder for detailed guides
3. **Configure Email** - Set up SMTP for notifications
4. **Customize Settings** - Adjust configuration in `app/config.py`
5. **Deploy to Production** - Follow production deployment guides

---

## Support

For issues or questions:

- Check the [Documentation](docs/)
- Review existing [GitHub Issues](https://github.com/pestechnology/PESU_RR_AIML_B_P05_Change_management_software_TheChangeMakers/issues)
- Contact the development team

---

## Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Flask-Login Documentation](https://flask-login.readthedocs.io/)

---

**Congratulations! 🎉** Your Change Management Software is now set up and running!
