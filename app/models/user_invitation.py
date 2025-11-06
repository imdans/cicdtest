"""
User Invitation Model
Tracks invitation tokens for new users
"""
from app.extensions import db
from datetime import datetime, timezone, timedelta
import secrets


class UserInvitation(db.Model):
    """User invitation for account activation"""
    __tablename__ = 'user_invitations'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    mfa_secret = db.Column(db.String(32), nullable=True)  # Store MFA secret temporarily
    is_accepted = db.Column(db.Boolean, default=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    accepted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = db.relationship('User', back_populates='invitation', foreign_keys=[user_id])
    
    def __init__(self, user_id, mfa_secret=None, expiry_hours=48):
        self.user_id = user_id
        self.token = secrets.token_urlsafe(32)
        self.mfa_secret = mfa_secret
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
    
    def is_valid(self):
        """Check if invitation is still valid"""
        # Make expires_at timezone-aware if it's naive
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        return not self.is_accepted and datetime.now(timezone.utc) < expires
    
    def accept(self):
        """Mark invitation as accepted"""
        self.is_accepted = True
        self.accepted_at = datetime.now(timezone.utc)
    
    def __repr__(self):
        return f'<UserInvitation {self.user_id}: {self.token[:8]}...>'
