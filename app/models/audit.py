"""
Audit Log Model
Implements CMS-F-013, CMS-F-014, CMS-SR-004
Immutable audit trails for compliance
"""
from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """
    Immutable audit log model
    Implements CMS-F-013: Immutable audit trails
    Implements CMS-SR-004: Audit logs protected against tampering
    """
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Event information
    event_type = db.Column(db.String(64), nullable=False, index=True)
    event_category = db.Column(db.String(64), nullable=False, index=True)
    event_description = db.Column(db.Text)
    
    # User information
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user = db.relationship('User', back_populates='audit_logs')
    username = db.Column(db.String(64))  # Denormalized for immutability
    
    # Request information
    ip_address = db.Column(db.String(45))  # IPv6 support
    user_agent = db.Column(db.String(256))
    request_method = db.Column(db.String(10))
    request_path = db.Column(db.String(256))
    
    # Resource information
    resource_type = db.Column(db.String(64))  # e.g., 'ChangeRequest', 'User'
    resource_id = db.Column(db.Integer)
    
    # Status and result
    status_code = db.Column(db.Integer)
    success = db.Column(db.Boolean, default=True)
    error_message = db.Column(db.Text)
    
    # Additional data (JSON)
    extra_data = db.Column(db.JSON)
    
    # Timestamp (immutable, timezone-aware)
    timestamp = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    def __repr__(self):
        return f'<AuditLog {self.event_type} by {self.username} at {self.timestamp}>'
    
    def to_dict(self):
        """Convert audit log to dictionary"""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'event_category': self.event_category,
            'event_description': self.event_description,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'request_method': self.request_method,
            'request_path': self.request_path,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'status_code': self.status_code,
            'success': self.success,
            'error_message': self.error_message,
            'extra_data': self.extra_data,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    @staticmethod
    def create_log(event_type, event_category, user=None, ip_address=None,
                   description=None, resource_type=None, resource_id=None,
                   success=True, metadata=None, request=None):
        """
        Create an audit log entry
        
        Args:
            event_type: Type of event (e.g., 'login', 'logout', 'cr_created')
            event_category: Category (e.g., 'authentication', 'change_request')
            user: User object (optional)
            ip_address: IP address (optional)
            description: Event description (optional)
            resource_type: Type of resource affected (optional)
            resource_id: ID of resource affected (optional)
            success: Whether event was successful
            metadata: Additional metadata (dict)
            request: Flask request object (optional)
        
        Returns:
            AuditLog: Created audit log entry
        """
        log = AuditLog(
            event_type=event_type,
            event_category=event_category,
            event_description=description,
            success=success,
            resource_type=resource_type,
            resource_id=resource_id,
            extra_data=metadata or {}
        )
        
        # User information
        if user:
            log.user_id = user.id
            log.username = user.username
        
        # Request information
        if request:
            log.ip_address = request.remote_addr
            log.user_agent = request.headers.get('User-Agent', '')[:256]
            log.request_method = request.method
            log.request_path = request.path
        elif ip_address:
            log.ip_address = ip_address
        
        db.session.add(log)
        db.session.commit()
        
        return log


# Event type constants for consistency
class AuditEventType:
    """Audit event type constants"""
    # Authentication events (CMS-F-004)
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILED = 'login_failed'
    LOGOUT = 'logout'
    MFA_ENABLED = 'mfa_enabled'
    MFA_DISABLED = 'mfa_disabled'
    MFA_VERIFIED = 'mfa_verified'
    MFA_FAILED = 'mfa_failed'
    PASSWORD_CHANGED = 'password_changed'
    ACCOUNT_LOCKED = 'account_locked'
    ACCOUNT_UNLOCKED = 'account_unlocked'
    
    # Change Request events
    CR_CREATED = 'cr_created'
    CR_UPDATED = 'cr_updated'
    CR_SUBMITTED = 'cr_submitted'
    CR_APPROVED = 'cr_approved'
    CR_REJECTED = 'cr_rejected'
    CR_IMPLEMENTED = 'cr_implemented'
    CR_CLOSED = 'cr_closed'
    CR_ROLLED_BACK = 'cr_rolled_back'
    CR_VIEWED = 'cr_viewed'
    
    # User management events
    USER_CREATED = 'user_created'
    USER_UPDATED = 'user_updated'
    USER_DELETED = 'user_deleted'
    ROLE_CHANGED = 'role_changed'
    
    # System events
    UNAUTHORIZED_ACCESS = 'unauthorized_access'
    PERMISSION_DENIED = 'permission_denied'


class AuditEventCategory:
    """Audit event category constants"""
    AUTHENTICATION = 'authentication'
    CHANGE_REQUEST = 'change_request'
    USER_MANAGEMENT = 'user_management'
    SYSTEM = 'system'
    SECURITY = 'security'