"""
Change Request Model
Implements CMS-F-005, CMS-F-006, CMS-F-007
"""
from datetime import datetime, timezone
from enum import Enum
from app.extensions import db


class CRStatus(str, Enum):
    """Change Request status enumeration"""
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    PENDING_APPROVAL = 'pending_approval'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    IN_PROGRESS = 'in_progress'
    IMPLEMENTED = 'implemented'
    CLOSED = 'closed'
    ROLLED_BACK = 'rolled_back'


class CRPriority(str, Enum):
    """Change Request priority enumeration"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class CRRiskLevel(str, Enum):
    """Change Request risk level enumeration"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'


class ChangeRequest(db.Model):
    """
    Change Request model
    Implements CMS-F-005: Submit new CR
    Implements CMS-F-006: Attach supporting documents
    Implements CMS-F-007: Edit CRs before submission
    """
    __tablename__ = 'change_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    cr_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Project reference
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    project = db.relationship('Project', back_populates='change_requests')
    
    # Basic information
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False)
    justification = db.Column(db.Text)
    impact_assessment = db.Column(db.Text)
    
    # Status and priority
    status = db.Column(db.Enum(CRStatus), default=CRStatus.DRAFT, nullable=False, index=True)
    priority = db.Column(db.Enum(CRPriority), default=CRPriority.MEDIUM, nullable=False)
    risk_level = db.Column(db.Enum(CRRiskLevel), default=CRRiskLevel.LOW, nullable=False)
    
    # Users and roles
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    requester = db.relationship('User', foreign_keys=[requester_id], back_populates='change_requests')
    
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approver = db.relationship('User', foreign_keys=[approver_id])
    
    implementer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    implementer = db.relationship('User', foreign_keys=[implementer_id])
    
    # Dates and deadlines
    approved_date = db.Column(db.DateTime)
    implementation_date = db.Column(db.DateTime)
    implementation_deadline = db.Column(db.DateTime)  # CMSF-015: Implementation deadline for SLA tracking
    closed_date = db.Column(db.DateTime)
    
    # SLA tracking (CMSF-015, CMSF-016)
    sla_deadline = db.Column(db.DateTime)
    is_sla_breached = db.Column(db.Boolean, default=False)
    sla_warning_sent = db.Column(db.Boolean, default=False)  # Track if 24h warning sent
    
    # Rollback information (CMS-F-017, CMS-F-018)
    rollback_plan = db.Column(db.Text)  # Text description of rollback plan
    rollback_plan_file = db.Column(db.String(512))  # File path to rollback plan attachment
    rollback_reason = db.Column(db.Text)
    rolled_back_at = db.Column(db.DateTime)
    rolled_back_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    rolled_back_by = db.relationship('User', foreign_keys=[rolled_back_by_id])
    
    # Approval/rejection information
    approval_comments = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    
    # Closure information (CMSF-019)
    closure_comments = db.Column(db.Text)
    closure_notes = db.Column(db.Text)  # Detailed closure notes from approver
    closed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    closed_by = db.relationship('User', foreign_keys=[closed_by_id])
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    submitted_at = db.Column(db.DateTime)
    
    # Relationships
    attachments = db.relationship('CRAttachment', back_populates='change_request',
                                 cascade='all, delete-orphan')
    comments = db.relationship('CRComment', back_populates='change_request',
                              cascade='all, delete-orphan', order_by='CRComment.created_at')
    
    def __repr__(self):
        return f'<ChangeRequest {self.cr_number}>'
    
    @staticmethod
    def generate_cr_number():
        """
        Generate unique CR number
        Format: CR-YYYYMMDD-XXXX
        
        Returns:
            str: Unique CR number
        """
        today = datetime.now(timezone.utc).strftime('%Y%m%d')
        prefix = f'CR-{today}'
        
        # Get count of CRs created today
        count = ChangeRequest.query.filter(
            ChangeRequest.cr_number.like(f'{prefix}%')
        ).count()
        
        return f'{prefix}-{count + 1:04d}'
    
    def can_edit(self, user):
        """
        Check if user can edit this CR
        CMS-F-007: Edit CRs until approved
        
        Args:
            user: User object
        
        Returns:
            bool: True if user can edit
        """
        # Cannot edit approved, implemented, closed, rejected, or rolled back CRs
        # Once approved, no one can edit - not even admins
        non_editable_statuses = [
            CRStatus.APPROVED,
            CRStatus.IMPLEMENTED,
            CRStatus.CLOSED,
            CRStatus.REJECTED,
            CRStatus.ROLLED_BACK
        ]
        
        # No one can edit after approval
        if self.status in non_editable_statuses:
            return False
        
        # Before approval: Requester can edit their own CR
        if self.requester_id == user.id:
            return True
        
        # Admins can also edit before approval
        if user.has_permission('manage_system'):
            return True
        
        return False
    
    def can_submit(self, user):
        """Check if user can submit this CR"""
        return self.requester_id == user.id and self.status == CRStatus.DRAFT
    
    def can_approve(self, user):
        """Check if user can approve this CR"""
        return user.has_permission('approve_cr') and self.status == CRStatus.PENDING_APPROVAL
    
    def can_implement(self, user):
        """Check if user can implement this CR"""
        return user.has_permission('implement_cr') and self.status == CRStatus.APPROVED
    
    def submit(self):
        """Submit CR for approval"""
        if self.status == CRStatus.DRAFT:
            self.status = CRStatus.PENDING_APPROVAL
            self.submitted_at = datetime.now(timezone.utc)
            # Set SLA deadline (example: 5 business days)
            self.sla_deadline = datetime.now(timezone.utc).replace(hour=23, minute=59, second=59)
    
    def approve(self, approver, comments=None):
        """
        Approve CR
        
        Args:
            approver: User object who approved
            comments: Approval comments
        """
        self.status = CRStatus.APPROVED
        self.approver_id = approver.id
        self.approved_date = datetime.now(timezone.utc)
        self.approval_comments = comments
    
    def reject(self, approver, reason):
        """
        Reject CR
        
        Args:
            approver: User object who rejected
            reason: Rejection reason
        """
        self.status = CRStatus.REJECTED
        self.approver_id = approver.id
        self.approved_date = datetime.now(timezone.utc)
        self.rejection_reason = reason
    
    def start_implementation(self, implementer):
        """
        Start CR implementation
        
        Args:
            implementer: User object implementing the CR
        """
        self.status = CRStatus.IN_PROGRESS
        self.implementer_id = implementer.id
        self.implementation_date = datetime.now(timezone.utc)
    
    def complete_implementation(self):
        """Mark CR as implemented"""
        self.status = CRStatus.IMPLEMENTED
    
    def close(self, user, comments=None, notes=None):
        """
        Close CR (CMSF-019)
        
        Args:
            user: User closing the CR (approver)
            comments: Closure comments
            notes: Detailed closure notes
        """
        self.status = CRStatus.CLOSED
        self.closed_date = datetime.now(timezone.utc)
        self.closed_by_id = user.id
        self.closure_comments = comments
        self.closure_notes = notes
    
    def rollback(self, user, reason):
        """
        Rollback CR
        CMS-F-018: Support rollback execution with justification
        
        Args:
            user: User performing rollback
            reason: Rollback reason
        """
        self.status = CRStatus.ROLLED_BACK
        self.rolled_back_at = datetime.now(timezone.utc)
        self.rolled_back_by_id = user.id
        self.rollback_reason = reason
    
    def check_sla_breach(self):
        """
        Check if SLA deadline is breached (CMSF-015)
        
        Returns:
            bool: True if deadline breached
        """
        if self.implementation_deadline and not self.is_sla_breached:
            if datetime.now(timezone.utc) > self.implementation_deadline:
                self.is_sla_breached = True
                return True
        return False
    
    def time_until_deadline(self):
        """
        Get time remaining until implementation deadline
        
        Returns:
            timedelta or None: Time remaining
        """
        if self.implementation_deadline:
            # Make implementation_deadline timezone-aware if it's naive
            deadline = self.implementation_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return deadline - datetime.now(timezone.utc)
        return None
    
    def is_deadline_warning_needed(self):
        """
        Check if 24h warning should be sent (CMSF-016)
        
        Returns:
            bool: True if warning needed
        """
        if self.implementation_deadline and not self.sla_warning_sent and not self.is_sla_breached:
            time_left = self.time_until_deadline()
            if time_left and time_left.total_seconds() <= 86400:  # 24 hours
                return True
        return False
    
    def get_timeline(self):
        """
        Get complete CR timeline for closure email
        
        Returns:
            dict: Timeline with all key events
        """
        return {
            'created': {
                'date': self.created_at,
                'user': self.requester.email if self.requester else None,
                'role': 'Requester'
            },
            'submitted': {
                'date': self.submitted_at,
                'user': self.requester.email if self.requester else None,
                'role': 'Requester'
            } if self.submitted_at else None,
            'approved': {
                'date': self.approved_date,
                'user': self.approver.email if self.approver else None,
                'role': 'Approver'
            } if self.approved_date else None,
            'implemented': {
                'date': self.implementation_date,
                'user': self.implementer.email if self.implementer else None,
                'role': 'Implementer'
            } if self.implementation_date else None,
            'closed': {
                'date': self.closed_date,
                'user': self.closed_by.email if self.closed_by else None,
                'role': 'Closer'
            } if self.closed_date else None,
        }
    
    def to_dict(self):
        """Convert CR to dictionary"""
        return {
            'id': self.id,
            'cr_number': self.cr_number,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'risk_level': self.risk_level.value,
            'requester': self.requester.username if self.requester else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CRAttachment(db.Model):
    """
    Change Request attachment model
    Implements CMS-F-006: Attach supporting documents to a CR
    """
    __tablename__ = 'cr_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey('change_requests.id'), nullable=False)
    change_request = db.relationship('ChangeRequest', back_populates='attachments')
    
    filename = db.Column(db.String(256), nullable=False)
    original_filename = db.Column(db.String(256), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer)  # Size in bytes
    mime_type = db.Column(db.String(128))
    
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_by = db.relationship('User')
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<CRAttachment {self.original_filename}>'


class CRComment(db.Model):
    """Change Request comment model"""
    __tablename__ = 'cr_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    change_request_id = db.Column(db.Integer, db.ForeignKey('change_requests.id'), nullable=False)
    change_request = db.relationship('ChangeRequest', back_populates='comments')
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User')
    
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f'<CRComment by {self.user.username}>'