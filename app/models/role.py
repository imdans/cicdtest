"""
Role and Permission Models
Implements CMS-F-003: Role-based access control
"""
from app.extensions import db


# Association table for role-permission many-to-many relationship
role_permissions = db.Table(
    'role_permissions',
    db.Column('role_id', db.Integer, db.ForeignKey('roles.id'), primary_key=True),
    db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True)
)


class Role(db.Model):
    """
    Role model for RBAC
    Implements CMS-F-003: Role-based access control
    """
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    
    # Relationships
    permissions = db.relationship('Permission', secondary=role_permissions,
                                 back_populates='roles', lazy='subquery')
    users = db.relationship('User', back_populates='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    def has_permission(self, permission_name):
        """
        Check if role has a specific permission
        
        Args:
            permission_name: Permission name to check
        
        Returns:
            bool: True if role has permission
        """
        return any(p.name == permission_name for p in self.permissions)
    
    def add_permission(self, permission):
        """Add permission to role"""
        if permission not in self.permissions:
            self.permissions.append(permission)
    
    def remove_permission(self, permission):
        """Remove permission from role"""
        if permission in self.permissions:
            self.permissions.remove(permission)
    
    @staticmethod
    def insert_default_roles():
        """
        Insert default roles and permissions
        Should be called during database initialization
        """
        from app.extensions import db
        
        # Define default permissions
        default_permissions = {
            'requester': [
                'submit_cr',
                'view_own_cr',
                'edit_own_cr',
                'attach_files'
            ],
            'approver': [
                'submit_cr',
                'view_own_cr',
                'view_all_cr',
                'approve_cr',
                'reject_cr',
                'request_changes'
            ],
            'implementer': [
                'view_all_cr',
                'implement_cr',
                'update_implementation_status'
            ],
            'admin': [
                'submit_cr',
                'view_own_cr',
                'view_all_cr',
                'edit_own_cr',
                'approve_cr',
                'reject_cr',
                'request_changes',
                'implement_cr',
                'rollback_cr',
                'manage_users',
                'manage_roles',
                'manage_system',
                'view_audit_logs',
                'attach_files',
                'update_implementation_status'
            ]
        }
        
        for role_name, permission_names in default_permissions.items():
            role = Role.query.filter_by(name=role_name).first()
            
            if not role:
                role = Role(
                    name=role_name,
                    description=f'{role_name.capitalize()} role'
                )
                db.session.add(role)
            
            # Add permissions
            for perm_name in permission_names:
                permission = Permission.query.filter_by(name=perm_name).first()
                
                if not permission:
                    permission = Permission(
                        name=perm_name,
                        description=f'{perm_name.replace("_", " ").capitalize()}'
                    )
                    db.session.add(permission)
                
                role.add_permission(permission)
        
        db.session.commit()


class Permission(db.Model):
    """Permission model for fine-grained access control"""
    __tablename__ = 'permissions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(256))
    
    # Relationships
    roles = db.relationship('Role', secondary=role_permissions,
                           back_populates='permissions', lazy='dynamic')
    
    def __repr__(self):
        return f'<Permission {self.name}>'
