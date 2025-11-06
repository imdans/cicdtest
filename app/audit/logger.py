"""
Audit logging utilities
Implements CMS-F-013, CMS-F-014
"""
from flask import request
from flask_login import current_user
from app.models.audit import AuditLog, AuditEventType, AuditEventCategory


def log_http_request(request_obj, response):
    """
    Log HTTP requests for audit trail
    
    Args:
        request_obj: Flask request object
        response: Flask response object
    """
    # Skip logging for static files and health checks
    if request_obj.path.startswith('/static/') or request_obj.path == '/health':
        return
    
    # Only log authenticated requests or important endpoints
    if current_user.is_authenticated or request_obj.path.startswith('/auth/'):
        AuditLog.create_log(
            event_type='http_request',
            event_category=AuditEventCategory.SYSTEM,
            user=current_user if current_user.is_authenticated else None,
            description=f'{request_obj.method} {request_obj.path}',
            request=request_obj,
            success=response.status_code < 400,
            metadata={
                'method': request_obj.method,
                'path': request_obj.path,
                'status_code': response.status_code
            }
        )


def log_cr_event(event_type, cr, user, description=None, metadata=None):
    """
    Log change request event
    
    Args:
        event_type: Type of CR event
        cr: ChangeRequest object
        user: User performing the action
        description: Event description
        metadata: Additional metadata
    """
    AuditLog.create_log(
        event_type=event_type,
        event_category=AuditEventCategory.CHANGE_REQUEST,
        user=user,
        description=description or f'{event_type} for CR {cr.cr_number}',
        resource_type='ChangeRequest',
        resource_id=cr.id,
        request=request,
        success=True,
        metadata=metadata or {}
    )
