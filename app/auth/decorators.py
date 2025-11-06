"""
Authentication and authorization decorators
Implements CMS-F-003: Role-based access control
"""
from functools import wraps
from flask import abort, redirect, url_for, flash
from flask_login import current_user
from app.models.audit import AuditLog, AuditEventType, AuditEventCategory


def login_required_with_audit(f):
    """
    Decorator to require login and log unauthorized access attempts
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Log unauthorized access attempt
            from flask import request
            AuditLog.create_log(
                event_type=AuditEventType.UNAUTHORIZED_ACCESS,
                event_category=AuditEventCategory.SECURITY,
                description=f'Unauthorized access attempt to {request.path}',
                request=request,
                success=False
            )
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(permission):
    """
    Decorator to require a specific permission
    Implements CMS-F-003: Role-based access control
    
    Args:
        permission: Permission name required
    
    Returns:
        Decorated function
    
    Usage:
        @permission_required('approve_cr')
        def approve_change_request():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                # Log permission denied
                from flask import request
                AuditLog.create_log(
                    event_type=AuditEventType.PERMISSION_DENIED,
                    event_category=AuditEventCategory.SECURITY,
                    user=current_user,
                    description=f'Permission denied: {permission} for {request.path}',
                    request=request,
                    success=False,
                    metadata={'required_permission': permission}
                )
                flash(f'Access Denied: You need the "{permission}" permission to access this feature.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def role_required(role_name):
    """
    Decorator to require a specific role
    
    Args:
        role_name: Role name required (e.g., 'admin', 'approver')
    
    Returns:
        Decorated function
    
    Usage:
        @role_required('admin')
        def admin_dashboard():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            
            if not current_user.has_role(role_name):
                # Log permission denied
                from flask import request
                AuditLog.create_log(
                    event_type=AuditEventType.PERMISSION_DENIED,
                    event_category=AuditEventCategory.SECURITY,
                    user=current_user,
                    description=f'Role required: {role_name} for {request.path}',
                    request=request,
                    success=False,
                    metadata={'required_role': role_name}
                )
                flash(f'Access Denied: This feature requires the "{role_name}" role.', 'danger')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Decorator to require admin role
    Convenience decorator for admin-only views
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin():
            flash('Access Denied: This feature requires administrator privileges.', 'danger')
            return redirect(url_for('index'))
        
        return f(*args, **kwargs)
    return decorated_function


def mfa_required(f):
    """
    Decorator to require MFA verification
    Implements CMS-F-002: MFA for administrators
    
    For admin users, ensures MFA is verified in the current session
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check if user is admin and MFA is enabled
        if current_user.is_admin() and current_user.mfa_enabled:
            # Check if MFA is verified in this session
            from flask import session
            if not session.get('mfa_verified', False):
                flash('Multi-factor authentication required.', 'warning')
                return redirect(url_for('auth.verify_mfa'))
        
        return f(*args, **kwargs)
    return decorated_function