"""
Initialize the database (development helper).
Creates all tables and inserts default roles.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models import Role


def main():
    """Initialize database with tables and default data"""
    app = create_app("development")
    with app.app_context():
        # Drop all tables (careful in production!)
        db.drop_all()
        
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Insert default roles and permissions
        Role.insert_default_roles()
        print("✓ Default roles and permissions inserted")
        
        print("\nDatabase initialized successfully!")
        print("\nAvailable roles:")
        for role in Role.query.all():
            permissions = [p.name for p in role.permissions]
            print(f"  - {role.name}: {', '.join(permissions)}")


if __name__ == "__main__":
    main()

