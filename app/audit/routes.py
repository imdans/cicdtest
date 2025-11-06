"""
Audit routes
Implements CMS-F-014: Generate audit reports
"""
from flask import render_template, request, send_file
from flask_login import login_required
from app.audit import audit_bp
from app.auth.decorators import permission_required
from app.models import AuditLog
from datetime import datetime, timedelta
import csv
import io


@audit_bp.route('/logs')
@login_required
@permission_required('view_audit_logs')
def view_logs():
    """
    View audit logs
    Implements CMS-F-014: View audit logs
    """
    # Get query parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    event_type = request.args.get('event_type')
    event_category = request.args.get('event_category')
    username = request.args.get('username')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = AuditLog.query
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    
    if username:
        query = query.filter(AuditLog.username.like(f'%{username}%'))
    
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(AuditLog.timestamp >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(AuditLog.timestamp <= date_to_obj)
    
    # Order by timestamp descending
    query = query.order_by(AuditLog.timestamp.desc())
    
    # Paginate
    logs = query.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('audit/logs.html', logs=logs)


@audit_bp.route('/export')
@login_required
@permission_required('view_audit_logs')
def export_logs():
    """
    Export audit logs to CSV
    Implements CMS-F-014: Export audit logs
    """
    # Get filters from query parameters
    event_type = request.args.get('event_type')
    event_category = request.args.get('event_category')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Build query
    query = AuditLog.query
    
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    
    if date_from:
        date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
        query = query.filter(AuditLog.timestamp >= date_from_obj)
    
    if date_to:
        date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(AuditLog.timestamp <= date_to_obj)
    
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(['ID', 'Timestamp', 'Event Type', 'Category', 'Username', 
                     'IP Address', 'Description', 'Success'])
    
    # Write data
    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.isoformat(),
            log.event_type,
            log.event_category,
            log.username or 'N/A',
            log.ip_address or 'N/A',
            log.event_description or 'N/A',
            'Yes' if log.success else 'No'
        ])
    
    # Prepare response
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'audit_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )