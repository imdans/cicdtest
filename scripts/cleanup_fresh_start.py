#!/usr/bin/env python3
"""
Fresh Start Cleanup Script
Clears all data except the admin user harsha.1305h@gmail.com
- Deletes all projects, CRs, users (except admin)
- Clears all logs
- Removes all __pycache__ directories
- Clears uploaded files
"""
import os
import sys
import shutil
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.extensions import db
from app.models import (
    User, Project, ProjectMembership, ChangeRequest, 
    CRAttachment, CRComment, UserInvitation, AuditLog
)

def clear_pycache(root_dir):
    """Remove all __pycache__ directories recursively"""
    print("\n🗑️  Clearing __pycache__ directories...")
    count = 0
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if '__pycache__' in dirnames:
            cache_path = os.path.join(dirpath, '__pycache__')
            shutil.rmtree(cache_path)
            count += 1
            print(f"   Removed: {cache_path}")
    print(f"✅ Cleared {count} __pycache__ directories")

def clear_logs(root_dir):
    """Clear all log files"""
    print("\n🗑️  Clearing log files...")
    logs_dir = os.path.join(root_dir, 'logs')
    if os.path.exists(logs_dir):
        for filename in os.listdir(logs_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(logs_dir, filename)
                os.remove(file_path)
                print(f"   Removed: {file_path}")
    print("✅ Log files cleared")

def clear_uploads(root_dir):
    """Clear uploaded files (keep .gitkeep)"""
    print("\n🗑️  Clearing uploaded files...")
    uploads_dir = os.path.join(root_dir, 'static', 'uploads')
    if os.path.exists(uploads_dir):
        count = 0
        for filename in os.listdir(uploads_dir):
            if filename != '.gitkeep':
                file_path = os.path.join(uploads_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
        print(f"✅ Cleared {count} uploaded files")
    
    # Clear rollback plans
    rollback_dir = os.path.join(root_dir, 'static', 'uploads', 'rollback_plans')
    if os.path.exists(rollback_dir):
        count = 0
        for filename in os.listdir(rollback_dir):
            if filename != '.gitkeep':
                file_path = os.path.join(rollback_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    count += 1
        print(f"✅ Cleared {count} rollback plan files")

def clear_database(admin_email):
    """Clear all database records except admin user"""
    print("\n🗑️  Clearing database...")
    
    # Find admin user
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        print(f"❌ Admin user {admin_email} not found!")
        return False
    
    print(f"✅ Found admin: {admin.email} (ID: {admin.id})")
    
    # Delete in correct order to respect foreign keys
    
    # 1. Delete all audit logs
    count = AuditLog.query.delete()
    print(f"   Deleted {count} audit logs")
    
    # 2. Delete CR-related records
    count = CRComment.query.delete()
    print(f"   Deleted {count} CR comments")
    
    count = CRAttachment.query.delete()
    print(f"   Deleted {count} CR attachments")
    
    count = ChangeRequest.query.delete()
    print(f"   Deleted {count} change requests")
    
    # 3. Delete project memberships
    count = ProjectMembership.query.delete()
    print(f"   Deleted {count} project memberships")
    
    # 4. Delete projects
    count = Project.query.delete()
    print(f"   Deleted {count} projects")
    
    # 5. Delete user invitations (except admin's if exists)
    count = UserInvitation.query.filter(UserInvitation.user_id != admin.id).delete()
    print(f"   Deleted {count} user invitations")
    
    # 6. Delete all users except admin
    deleted_users = []
    users_to_delete = User.query.filter(User.id != admin.id).all()
    for user in users_to_delete:
        deleted_users.append(user.email)
        db.session.delete(user)
    print(f"   Deleted {len(deleted_users)} users:")
    for email in deleted_users:
        print(f"      - {email}")
    
    # Commit all changes
    try:
        db.session.commit()
        print("✅ Database cleared successfully")
        return True
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error clearing database: {str(e)}")
        return False

def main():
    """Main cleanup function"""
    print("=" * 70)
    print("🧹 FRESH START CLEANUP SCRIPT")
    print("=" * 70)
    print("\nThis script will:")
    print("  1. Clear all __pycache__ directories")
    print("  2. Clear all log files")
    print("  3. Clear all uploaded files")
    print("  4. Delete all projects, CRs, and users (except admin)")
    print("  5. Keep only admin: harsha.1305h@gmail.com")
    print("\n⚠️  WARNING: This action cannot be undone!")
    
    # Confirm
    response = input("\nType 'YES' to proceed: ")
    if response != 'YES':
        print("❌ Cleanup cancelled")
        return
    
    # Get project root directory
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    print(f"\n📁 Project root: {root_dir}")
    
    # Create Flask app context
    app = create_app()
    with app.app_context():
        # 1. Clear __pycache__
        clear_pycache(root_dir)
        
        # 2. Clear logs
        clear_logs(root_dir)
        
        # 3. Clear uploads
        clear_uploads(root_dir)
        
        # 4. Clear database
        if not clear_database('harsha.1305h@gmail.com'):
            print("\n❌ Database cleanup failed!")
            return
    
    print("\n" + "=" * 70)
    print("✅ CLEANUP COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print("\n📝 Summary:")
    print("  - All __pycache__ directories removed")
    print("  - All log files cleared")
    print("  - All uploaded files removed")
    print("  - All projects and CRs deleted")
    print("  - All users deleted (except harsha.1305h@gmail.com)")
    print("\n🚀 You can now start fresh!")
    print("\nNext steps:")
    print("  1. Restart your Flask server: python app.py")
    print("  2. Login as admin: harsha.1305h@gmail.com")
    print("  3. Create new projects and users")

if __name__ == '__main__':
    main()
