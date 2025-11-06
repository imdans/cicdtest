"""
Create a custom user (development helper).
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Role


def main(username, email, password, role_name='requester'):
    """Create a custom user"""
    app = create_app("development")
    with app.app_context():
        # Ensure database is initialized
        db.create_all()
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"✗ User with email '{email}' already exists!")
            print(f"  Username: {existing_user.username}")
            return
        
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            print(f"✗ Username '{username}' already exists!")
            return
        
        # Get role
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            print(f"✗ Role '{role_name}' not found. Please run init_db.py first.")
            return
        
        # Create user
        user = User(
            username=username,
            email=email,
            role_id=role.id,
            first_name=username.split('.')[0].capitalize() if '.' in username else username.capitalize(),
            last_name='',
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✓ User created successfully!")
        print(f"\n  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Role: {role_name}")
        print(f"  Password: {password}")


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        username = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        role_name = sys.argv[4] if len(sys.argv) > 4 else 'requester'
        main(username, email, password, role_name)
    else:
        print("Usage: python scripts/create_user.py <username> <email> <password> [role]")
        print("Roles: requester, approver, implementer, admin")
        sys.exit(1)
