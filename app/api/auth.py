"""
Authentication API endpoints
"""
from flask import jsonify, request
from app.api import api_bp
from app.models import User
from app.models.audit import AuditLog, AuditEventType, AuditEventCategory


@api_bp.route("/auth/ping")
def auth_ping():
    """API health check"""
    return jsonify({"ok": True, "service": "auth"})


@api_bp.route('/auth/verify', methods=['POST'])
def verify_credentials():
    """
    Verify user credentials
    Returns user info if valid
    """
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Missing credentials'}), 400
    
    user = User.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        # Log successful API authentication
        AuditLog.create_log(
            event_type=AuditEventType.LOGIN_SUCCESS,
            event_category=AuditEventCategory.AUTHENTICATION,
            user=user,
            description=f'API authentication successful for {username}',
            request=request,
            success=True
        )
        
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role.name if user.role else None
            }
        })
    
    # Log failed API authentication
    AuditLog.create_log(
        event_type=AuditEventType.LOGIN_FAILED,
        event_category=AuditEventCategory.AUTHENTICATION,
        description=f'Failed API authentication for {username}',
        request=request,
        success=False
    )
    
    return jsonify({'error': 'Invalid credentials'}), 401

