"""
User Model for Change Management System
Implements CMS-F-001, CMS-F-002, CMS-F-003
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import pyotp
from app.extensions import db, login_manager


class User(UserMixin, db.Model):
    """
    User model with authentication support
    Implements CMS-F-001: User authentication
    Implements CMS-F-002: MFA for administrators
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Profile
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    
    # MFA (CMS-F-002)
    mfa_secret = db.Column(db.String(32))  # TOTP secret
    mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_verified = db.Column(db.Boolean, default=False)  # Session-level verification
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    is_locked = db.Column(db.Boolean, default=False)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_login = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))  # IPv6 support
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    role = db.relationship('Role', back_populates='users')
    
    # Change requests created by user
    change_requests = db.relationship('ChangeRequest', 
                                     back_populates='requester',
                                     foreign_keys='ChangeRequest.requester_id')
    
    # Audit logs
    audit_logs = db.relationship('AuditLog', back_populates='user', lazy='dynamic')
    
    # Project memberships
    project_memberships = db.relationship('ProjectMembership', back_populates='user', cascade='all, delete-orphan')
    
    # Invitation relationship
    invitation = db.relationship('UserInvitation', back_populates='user', uselist=False, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f'{self.first_name} {self.last_name}'
        return self.username
    
    def set_password(self, password):
        """
        Hash and set user password
        
        Args:
            password: Plain text password
        """
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """
        Verify password
        
        Args:
            password: Plain text password to verify
        
        Returns:
            bool: True if password matches
        """
        return check_password_hash(self.password_hash, password)
    
    def generate_mfa_secret(self):
        """
        Generate MFA secret for TOTP
        CMS-F-002: MFA for administrators
        
        Returns:
            str: Base32 encoded secret
        """
        self.mfa_secret = pyotp.random_base32()
        return self.mfa_secret
    
    def get_totp_uri(self, issuer_name='CMS'):
        """
        Get TOTP provisioning URI for QR code
        
        Args:
            issuer_name: Name of the issuing organization
        
        Returns:
            str: TOTP URI
        """
        if not self.mfa_secret:
            self.generate_mfa_secret()
        
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )
    
    def verify_totp(self, token):
        """
        Verify TOTP token
        
        Args:
            token: 6-digit TOTP code
        
        Returns:
            bool: True if token is valid
        """
        if not self.mfa_secret:
            return False
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 time step window
    
    def has_permission(self, permission):
        """
        Check if user has a specific permission
        CMS-F-003: Role-based access control
        
        Args:
            permission: Permission name to check
        
        Returns:
            bool: True if user has permission
        """
        if not self.role:
            return False
        return self.role.has_permission(permission)
    
    def has_role(self, role_name):
        """
        Check if user has a specific role
        
        Args:
            role_name: Role name to check
        
        Returns:
            bool: True if user has role
        """
        return self.role and self.role.name == role_name
    
    def is_admin(self):
        """Check if user is an administrator"""
        return self.has_role('admin')
    
    def increment_failed_login(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.is_locked = True
    
    def reset_failed_login(self):
        """Reset failed login attempts after successful login"""
        self.failed_login_attempts = 0
        self.is_locked = False
    
    def update_last_login(self, ip_address):
        """
        Update last login timestamp and IP
        
        Args:
            ip_address: IP address of the login
        """
        self.last_login = datetime.utcnow()
        self.last_login_ip = ip_address
    
    # Project-related methods
    def get_projects(self):
        """Get all active projects user is a member of"""
        return [m.project for m in self.project_memberships if m.is_active and m.project.is_active]
    
    def get_project_role(self, project):
        """Get user's role in a specific project"""
        membership = next((m for m in self.project_memberships 
                          if m.project_id == project.id and m.is_active), None)
        return membership.role if membership else None
    
    def has_project_access(self, project):
        """Check if user has access to a project"""
        if self.is_admin():
            return True
        return any(m.project_id == project.id and m.is_active for m in self.project_memberships)
    
    def can_access_cr(self, change_request):
        """
        Check if user can access a specific change request
        - Admins: Only CRs of projects they created
        - Requesters: Only their own CRs
        - Approvers: All CRs in assigned projects
        - Implementers: Only approved CRs in assigned projects
        """
        user_role_name = self.role.name.lower() if self.role else None
        
        if user_role_name == 'admin':
            # Admins can only access CRs of projects they created
            return change_request.project.created_by_id == self.id
        
        # Check if user has access to the project
        if not self.has_project_access(change_request.project):
            return False
        
        if user_role_name == 'requester':
            # Requesters can only access their own CRs
            return change_request.requester_id == self.id
        
        elif user_role_name == 'implementer':
            # Implementers can only access approved CRs
            from app.models.change_request import CRStatus
            return change_request.status in [
                CRStatus.APPROVED,
                CRStatus.IN_PROGRESS,
                CRStatus.IMPLEMENTED,
                CRStatus.CLOSED,
                CRStatus.ROLLED_BACK
            ]
        
        elif user_role_name == 'approver':
            # Approvers can access all CRs in their projects
            return True
        
        return False


@login_manager.user_loader
def load_user(user_id):
    """
    Load user for Flask-Login
    
    Args:
        user_id: User ID
    
    Returns:
        User object or None
    """
    return User.query.get(int(user_id))