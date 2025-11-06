"""
Create an administrative user (development helper).
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import User, Role


def main(email="admin@example.com", password="Admin@123", username="admin"):
    """Create an admin user"""
    app = create_app("development")
    with app.app_context():
        # Ensure database is initialized
        db.create_all()
        
        # Check if user already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            print(f"✗ User '{username}' already exists!")
            return
        
        # Get admin role
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            print("✗ Admin role not found. Please run init_db.py first.")
            return
        
        # Create admin user
        user = User(
            username=username,
            email=email,
            role_id=admin_role.id,
            first_name="System",
            last_name="Administrator",
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✓ Admin user created successfully!")
        print(f"\n  Username: {username}")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print(f"\n  ⚠️  Please change the password after first login!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        email = sys.argv[1]
        password = sys.argv[2] if len(sys.argv) > 2 else "Admin@123"
        username = sys.argv[3] if len(sys.argv) > 3 else "admin"
        main(email, password, username)
    else:
        main()

