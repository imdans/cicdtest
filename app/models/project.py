"""
Project Model
Multi-project support with user role assignments
"""
from datetime import datetime, timezone
from app.extensions import db


class Project(db.Model):
    """
    Project model for organizing change requests
    Users are assigned to projects with specific roles
    """
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True, index=True)
    description = db.Column(db.Text)
    code = db.Column(db.String(32), unique=True, index=True)  # Project code/identifier
    
    # Created by admin (track which admin created this project)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_projects')
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    change_requests = db.relationship('ChangeRequest', back_populates='project', cascade='all, delete-orphan')
    members = db.relationship('ProjectMembership', back_populates='project', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def get_members_by_role(self, role_name):
        """Get all users with a specific role in this project"""
        return [m.user for m in self.members if m.role.name == role_name and m.is_active]
    
    def has_member(self, user):
        """Check if user is a member of this project"""
        return any(m.user_id == user.id and m.is_active for m in self.members)
    
    def get_user_role(self, user):
        """Get user's role in this project"""
        membership = next((m for m in self.members if m.user_id == user.id and m.is_active), None)
        return membership.role if membership else None
    
    def to_dict(self):
        """Convert project to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'code': self.code,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'member_count': len([m for m in self.members if m.is_active])
        }


class ProjectMembership(db.Model):
    """
    Project membership model
    Links users to projects with specific roles
    """
    __tablename__ = 'project_memberships'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # References
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # Status
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    joined_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    project = db.relationship('Project', back_populates='members')
    user = db.relationship('User', back_populates='project_memberships')
    role = db.relationship('Role')
    
    # Unique constraint: one user can only have one active role per project
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='unique_project_user'),
    )
    
    def __repr__(self):
        return f'<ProjectMembership {self.user.email} in {self.project.name} as {self.role.name}>'
