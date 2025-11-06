"""
Admin routes for project and user management
Admin-only access
"""
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.auth.decorators import admin_required
from app.models import User, Role, Project, ProjectMembership, ChangeRequest, UserInvitation
from app.extensions import db
from app.services import EmailService
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
import pyotp
import secrets


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with overview statistics - CMSF-021"""
    from app.models.change_request import CRStatus, CRPriority
    from sqlalchemy import and_, or_
    
    # Get projects created by current admin
    admin_projects = Project.query.filter_by(created_by_id=current_user.id, is_active=True).all()
    admin_project_ids = [p.id for p in admin_projects]
    
    # Basic stats
    stats = {
        'total_projects': Project.query.filter_by(is_active=True).count(),
        'my_projects': len(admin_projects),
        'total_users': User.query.filter_by(is_active=True).count(),
        'total_crs': ChangeRequest.query.count(),
        'unassigned_users': User.query.outerjoin(ProjectMembership).filter(ProjectMembership.id == None).count()
    }
    
    # CMSF-021: CR Statistics Dashboard
    cr_stats = {
        'pending': ChangeRequest.query.filter(
            ChangeRequest.status.in_([CRStatus.DRAFT, CRStatus.SUBMITTED, CRStatus.PENDING_APPROVAL])
        ).count(),
        'approved': ChangeRequest.query.filter_by(status=CRStatus.APPROVED).count(),
        'in_progress': ChangeRequest.query.filter_by(status=CRStatus.IN_PROGRESS).count(),
        'implemented': ChangeRequest.query.filter_by(status=CRStatus.IMPLEMENTED).count(),
        'closed': ChangeRequest.query.filter_by(status=CRStatus.CLOSED).count(),
        'rejected': ChangeRequest.query.filter_by(status=CRStatus.REJECTED).count(),
        'rolled_back': ChangeRequest.query.filter_by(status=CRStatus.ROLLED_BACK).count(),
        'sla_breached': ChangeRequest.query.filter_by(is_sla_breached=True).count()
    }
    
    # Priority breakdown
    priority_stats = {
        'critical': ChangeRequest.query.filter_by(priority=CRPriority.CRITICAL).count(),
        'high': ChangeRequest.query.filter_by(priority=CRPriority.HIGH).count(),
        'medium': ChangeRequest.query.filter_by(priority=CRPriority.MEDIUM).count(),
        'low': ChangeRequest.query.filter_by(priority=CRPriority.LOW).count()
    }
    
    # My projects analytics
    my_project_analytics = []
    for project in admin_projects:
        project_crs = ChangeRequest.query.filter_by(project_id=project.id).all()
        analytics = {
            'project': project,
            'total_crs': len(project_crs),
            'pending': len([cr for cr in project_crs if cr.status in [CRStatus.DRAFT, CRStatus.SUBMITTED, CRStatus.PENDING_APPROVAL]]),
            'approved': len([cr for cr in project_crs if cr.status == CRStatus.APPROVED]),
            'closed': len([cr for cr in project_crs if cr.status == CRStatus.CLOSED]),
            'members': ProjectMembership.query.filter_by(project_id=project.id).count(),
            'sla_breached': len([cr for cr in project_crs if cr.is_sla_breached])
        }
        my_project_analytics.append(analytics)
    
    recent_projects = Project.query.filter_by(is_active=True).order_by(Project.created_at.desc()).limit(5).all()
    
    # Get recently closed CRs with timeline details (CMSF-019)
    closed_crs = ChangeRequest.query.filter_by(status=CRStatus.CLOSED).order_by(
        ChangeRequest.closed_date.desc()
    ).limit(10).all()
    
    # Calculate metrics for closed CRs
    closed_cr_metrics = []
    for cr in closed_crs:
        metrics = {
            'cr': cr,
            'timeline': cr.get_timeline(),
            'total_time': None,
            'sla_met': None
        }
        
        # Calculate total time taken
        if cr.closed_date and cr.created_at:
            delta = cr.closed_date - cr.created_at
            days = delta.days
            hours = (delta.seconds // 3600)
            metrics['total_time'] = f"{days}d {hours}h"
        
        # Check if SLA was met
        if cr.implementation_deadline and cr.implementation_date:
            metrics['sla_met'] = cr.implementation_date <= cr.implementation_deadline
        
        closed_cr_metrics.append(metrics)
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         cr_stats=cr_stats,
                         priority_stats=priority_stats,
                         my_project_analytics=my_project_analytics,
                         recent_projects=recent_projects,
                         closed_cr_metrics=closed_cr_metrics)


@admin_bp.route('/projects')
@login_required
@admin_required
def projects():
    """List all projects"""
    all_projects = Project.query.filter_by(is_active=True).order_by(Project.created_at.desc()).all()
    return render_template('admin/projects.html', projects=all_projects)


@admin_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_project():
    """Create a new project"""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name or not code:
            flash('Project name and code are required', 'danger')
            return render_template('admin/create_project.html'), 400
        
        # Check if code already exists
        if Project.query.filter_by(code=code).first():
            flash('Project code already exists', 'danger')
            return render_template('admin/create_project.html'), 400
        
        project = Project(
            name=name,
            code=code,
            description=description,
            is_active=True
        )
        
        db.session.add(project)
        db.session.commit()
        
        flash(f'Project "{name}" created successfully', 'success')
        return redirect(url_for('admin.project_detail', project_id=project.id))
    
    return render_template('admin/create_project.html')


@admin_bp.route('/projects/<int:project_id>')
@login_required
@admin_required
def project_detail(project_id):
    """View project details"""
    project = Project.query.get_or_404(project_id)
    members = ProjectMembership.query.filter_by(project_id=project_id, is_active=True).all()
    crs = ChangeRequest.query.filter_by(project_id=project_id).order_by(ChangeRequest.created_at.desc()).limit(10).all()
    
    # Get unassigned users
    assigned_user_ids = [m.user_id for m in members]
    unassigned_users = User.query.filter(
        User.is_active == True,
        ~User.id.in_(assigned_user_ids) if assigned_user_ids else True
    ).all()
    
    roles = Role.query.all()
    
    return render_template('admin/project_detail.html', 
                         project=project, 
                         members=members, 
                         crs=crs,
                         unassigned_users=unassigned_users,
                         roles=roles)


@admin_bp.route('/projects/<int:project_id>/add-member', methods=['POST'])
@login_required
@admin_required
def add_project_member(project_id):
    """Add a user to a project"""
    project = Project.query.get_or_404(project_id)
    
    user_id = request.form.get('user_id', '').strip()
    role_id = request.form.get('role_id', '').strip()
    
    if not user_id or not role_id:
        flash('User and role are required', 'danger')
        return redirect(url_for('admin.project_detail', project_id=project_id))
    
    user = User.query.get_or_404(int(user_id))
    role = Role.query.get_or_404(int(role_id))
    
    # Check if already a member
    existing = ProjectMembership.query.filter_by(
        project_id=project_id,
        user_id=int(user_id)
    ).first()
    
    if existing:
        if existing.is_active:
            flash(f'{user.email} is already a member of this project', 'warning')
        else:
            existing.is_active = True
            existing.role_id = int(role_id)
            flash(f'{user.email} re-added to project', 'success')
    else:
        membership = ProjectMembership(
            project_id=project_id,
            user_id=int(user_id),
            role_id=int(role_id),
            is_active=True
        )
        db.session.add(membership)
        flash(f'{user.email} added to project as {role.name}', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.project_detail', project_id=project_id))


@admin_bp.route('/projects/<int:project_id>/remove-member/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def remove_project_member(project_id, user_id):
    """Remove a user from a project"""
    membership = ProjectMembership.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first_or_404()
    
    membership.is_active = False
    db.session.commit()
    
    flash(f'{membership.user.email} removed from project', 'success')
    return redirect(url_for('admin.project_detail', project_id=project_id))


@admin_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    """
    Delete a project (soft delete by marking inactive) - requires admin password
    Projects with active CRs cannot be deleted
    All project members will be removed
    """
    project = Project.query.get_or_404(project_id)
    
    # Verify admin password
    admin_password = request.form.get('admin_password', '')
    
    if not admin_password:
        flash('❌ Admin password is required to delete a project.', 'danger')
        return redirect(url_for('admin.project_detail', project_id=project_id))
    
    # Check admin password
    from werkzeug.security import check_password_hash
    if not check_password_hash(current_user.password_hash, admin_password):
        flash('❌ Incorrect admin password. Project deletion cancelled.', 'danger')
        return redirect(url_for('admin.project_detail', project_id=project_id))
    
    # Count members and CRs before deletion
    from app.models.change_request import ChangeRequest, CRStatus
    active_crs = ChangeRequest.query.filter_by(project_id=project_id).count()
    member_count = ProjectMembership.query.filter_by(project_id=project_id, is_active=True).count()
    
    # Close all related change requests
    if active_crs > 0:
        ChangeRequest.query.filter_by(project_id=project_id).update({
            'status': CRStatus.CLOSED,
            'rejection_reason': f'Auto-closed due to project deletion by admin {current_user.email}'
        })
    
    # Count members before deletion
    
    # Soft delete: mark as inactive
    project.is_active = False
    
    # Deactivate all project memberships
    ProjectMembership.query.filter_by(project_id=project_id).update({'is_active': False})
    
    db.session.commit()
    
    flash(f'✅ Project "{project.name}" deleted successfully. {active_crs} CR(s) closed and {member_count} member(s) removed.', 'success')
    return redirect(url_for('admin.projects'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """List all users"""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_user():
    """Create a new user and send invitation email"""
    roles = Role.query.all()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        username = request.form.get('username', '').strip()
        role_id = request.form.get('role_id', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        
        if not email or not role_id:
            flash('Email and role are required', 'danger')
            return render_template('admin/create_user.html', roles=roles), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('User with this email already exists', 'danger')
            return render_template('admin/create_user.html', roles=roles), 400
        
        # Generate temporary password
        temp_password = secrets.token_urlsafe(16)
        
        # Get role to check if MFA should be enabled
        role = Role.query.get(int(role_id))
        enable_mfa = (role.name.lower() == 'admin')  # Only admins get MFA
        
        # Generate MFA secret only for admins
        mfa_secret = pyotp.random_base32() if enable_mfa else None
        
        # Create user (inactive until invitation accepted)
        user = User(
            email=email,
            username=username or email.split('@')[0],
            password_hash=generate_password_hash(temp_password),
            role_id=int(role_id),
            first_name=first_name,
            last_name=last_name,
            is_active=False,  # Inactive until invitation accepted
            mfa_secret=mfa_secret,
            mfa_enabled=enable_mfa  # MFA only for admins
        )
        
        db.session.add(user)
        db.session.flush()  # Get user.id
        
        # Create invitation
        invitation = UserInvitation(
            user_id=user.id,
            mfa_secret=mfa_secret
        )
        db.session.add(invitation)
        db.session.commit()
        
        # Generate MFA QR code URI only for admins
        qr_uri = None
        if enable_mfa and mfa_secret:
            qr_uri = pyotp.totp.TOTP(mfa_secret).provisioning_uri(
                name=user.email,
                issuer_name='Change Management System'
            )
        
        # Send invitation email
        try:
            EmailService.send_user_invitation(
                user=user,
                invitation_token=invitation.token,
                mfa_secret=mfa_secret if enable_mfa else None,
                qr_code_data=qr_uri
            )
            flash(f'✅ User "{email}" created and invitation email sent successfully!', 'success')
            current_app.logger.info(f'Invitation email sent to {email}')
        except Exception as e:
            error_msg = str(e)
            current_app.logger.error(f'Failed to send invitation email to {email}: {error_msg}')
            flash(f'⚠️ User created but email failed to send. Error: {error_msg}', 'warning')
            flash('Please check your SMTP configuration in .env file', 'info')
        
        return redirect(url_for('admin.users'))
    
    return render_template('admin/create_user.html', roles=roles)


@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    """Generate comprehensive reports for projects with member performance analysis"""
    from app.models.change_request import CRStatus, CRPriority
    from datetime import datetime, timedelta
    
    # Get selected project from query params
    selected_project_id = request.args.get('project_id', type=int)
    
    projects = Project.query.filter_by(is_active=True).all()
    selected_project = None
    project_report = None
    
    if selected_project_id:
        selected_project = Project.query.get(selected_project_id)
        
        if selected_project:
            # Get all CRs for this project
            project_crs = ChangeRequest.query.filter_by(project_id=selected_project.id).all()
            
            # Status breakdown
            status_counts = {
                'draft': 0,
                'submitted': 0,
                'pending': 0,
                'approved': 0,
                'in_progress': 0,
                'implemented': 0,
                'closed': 0,
                'rejected': 0,
                'rolled_back': 0
            }
            
            for cr in project_crs:
                if cr.status == CRStatus.DRAFT:
                    status_counts['draft'] += 1
                elif cr.status == CRStatus.SUBMITTED:
                    status_counts['submitted'] += 1
                elif cr.status == CRStatus.PENDING_APPROVAL:
                    status_counts['pending'] += 1
                elif cr.status == CRStatus.APPROVED:
                    status_counts['approved'] += 1
                elif cr.status == CRStatus.IN_PROGRESS:
                    status_counts['in_progress'] += 1
                elif cr.status == CRStatus.IMPLEMENTED:
                    status_counts['implemented'] += 1
                elif cr.status == CRStatus.CLOSED:
                    status_counts['closed'] += 1
                elif cr.status == CRStatus.REJECTED:
                    status_counts['rejected'] += 1
                elif cr.status == CRStatus.ROLLED_BACK:
                    status_counts['rolled_back'] += 1
            
            # Priority breakdown
            priority_counts = {
                'critical': len([cr for cr in project_crs if cr.priority == CRPriority.CRITICAL]),
                'high': len([cr for cr in project_crs if cr.priority == CRPriority.HIGH]),
                'medium': len([cr for cr in project_crs if cr.priority == CRPriority.MEDIUM]),
                'low': len([cr for cr in project_crs if cr.priority == CRPriority.LOW])
            }
            
            # Member performance analysis
            members = ProjectMembership.query.filter_by(project_id=selected_project.id, is_active=True).all()
            member_performance = []
            
            for membership in members:
                user = membership.user
                role = membership.role
                
                # Count CRs by role
                crs_created = len([cr for cr in project_crs if cr.requester_id == user.id])
                crs_approved = len([cr for cr in project_crs if cr.approver_id == user.id])
                crs_implemented = len([cr for cr in project_crs if cr.implementer_id == user.id])
                
                # Calculate average resolution time for implementer
                avg_resolution_time = None
                if crs_implemented > 0:
                    completed_crs = [cr for cr in project_crs if cr.implementer_id == user.id and cr.implementation_date and cr.approved_date]
                    if completed_crs:
                        total_hours = sum([
                            (cr.implementation_date - cr.approved_date).total_seconds() / 3600 
                            for cr in completed_crs
                        ])
                        avg_hours = total_hours / len(completed_crs)
                        avg_resolution_time = f"{int(avg_hours // 24)}d {int(avg_hours % 24)}h"
                
                # Calculate approval rate for approvers
                approval_rate = None
                if crs_approved > 0:
                    approved_crs = [cr for cr in project_crs if cr.approver_id == user.id]
                    approved_count = len([cr for cr in approved_crs if cr.status in [CRStatus.APPROVED, CRStatus.IN_PROGRESS, CRStatus.IMPLEMENTED, CRStatus.CLOSED]])
                    approval_rate = f"{(approved_count / crs_approved * 100):.1f}%"
                
                # SLA compliance for implementers
                sla_breached = len([cr for cr in project_crs if cr.implementer_id == user.id and cr.is_sla_breached])
                
                member_performance.append({
                    'user': user,
                    'role': role.name,
                    'crs_created': crs_created,
                    'crs_approved': crs_approved,
                    'crs_implemented': crs_implemented,
                    'avg_resolution_time': avg_resolution_time,
                    'approval_rate': approval_rate,
                    'sla_breached': sla_breached,
                    'total_activities': crs_created + crs_approved + crs_implemented
                })
            
            # Sort by total activities
            member_performance.sort(key=lambda x: x['total_activities'], reverse=True)
            
            # SLA compliance
            total_with_deadline = len([cr for cr in project_crs if cr.implementation_deadline])
            sla_breached_count = len([cr for cr in project_crs if cr.is_sla_breached])
            sla_compliance_rate = 0
            if total_with_deadline > 0:
                sla_compliance_rate = ((total_with_deadline - sla_breached_count) / total_with_deadline * 100)
            
            project_report = {
                'project': selected_project,
                'total_crs': len(project_crs),
                'status_counts': status_counts,
                'priority_counts': priority_counts,
                'member_performance': member_performance,
                'member_count': len(members),
                'sla_compliance_rate': f"{sla_compliance_rate:.1f}%",
                'sla_breached_count': sla_breached_count
            }
    
    # Summary for all projects
    project_summaries = []
    for project in projects:
        from app.models.change_request import CRStatus
        
        crs = ChangeRequest.query.filter_by(project_id=project.id).all()
        members = ProjectMembership.query.filter_by(project_id=project.id, is_active=True).count()
        
        summary = {
            'project': project,
            'total_crs': len(crs),
            'pending_crs': len([cr for cr in crs if cr.status == CRStatus.PENDING_APPROVAL]),
            'closed_crs': len([cr for cr in crs if cr.status == CRStatus.CLOSED]),
            'members': members,
            'sla_breached': len([cr for cr in crs if cr.is_sla_breached])
        }
        project_summaries.append(summary)
    
    # Get current date for report generation timestamp
    from datetime import datetime
    current_date = datetime.now().strftime('%B %d, %Y')
    
    return render_template('admin/reports.html', 
                         projects=projects,
                         project_summaries=project_summaries,
                         selected_project=selected_project,
                         project_report=project_report,
                         current_date=current_date)


@admin_bp.route('/reports/export-pdf')
@login_required
@admin_required
def export_report_pdf():
    """Export project report as PDF"""
    from datetime import datetime
    from weasyprint import HTML, CSS
    from flask import make_response
    import io
    
    project_id = request.args.get('project_id', type=int)
    
    if not project_id:
        flash('❌ Please select a project to export', 'danger')
        return redirect(url_for('admin.reports'))
    
    # Get the same data as the reports view
    from app.models.change_request import CRStatus, CRPriority
    
    project = Project.query.get_or_404(project_id)
    
    # Get all CRs for this project
    crs = ChangeRequest.query.filter_by(project_id=project_id).all()
    
    # Calculate status counts
    status_counts = {status: 0 for status in CRStatus}
    for cr in crs:
        status_counts[cr.status] += 1
    
    # Calculate priority counts
    priority_counts = {priority: 0 for priority in CRPriority}
    for cr in crs:
        priority_counts[cr.priority] += 1
    
    # Calculate member performance
    memberships = ProjectMembership.query.filter_by(project_id=project_id).all()
    member_performance = []
    
    for membership in memberships:
        user = membership.user
        user_crs = [cr for cr in crs if cr.requester_id == user.id]
        approved_crs = [cr for cr in user_crs if cr.status in [CRStatus.APPROVED, CRStatus.IN_PROGRESS, CRStatus.IMPLEMENTED, CRStatus.CLOSED]]
        implemented_crs = [cr for cr in crs if cr.implementer_id == user.id and cr.status in [CRStatus.IMPLEMENTED, CRStatus.CLOSED]]
        
        # Calculate average resolution time
        closed_crs = [cr for cr in user_crs if cr.status == CRStatus.CLOSED and cr.approved_date and cr.closed_date]
        avg_resolution_time = None
        if closed_crs:
            total_days = sum((cr.closed_date - cr.approved_date).days for cr in closed_crs)
            avg_days = total_days / len(closed_crs)
            avg_resolution_time = f"{avg_days:.1f} days"
        
        # Calculate approval rate
        approval_rate = None
        if user_crs:
            approval_rate = f"{(len(approved_crs) / len(user_crs)) * 100:.1f}%"
        
        # Count SLA breaches
        sla_breached = len([cr for cr in user_crs if cr.is_sla_breached])
        
        member_performance.append({
            'user': user,
            'role': membership.role,
            'crs_created': len(user_crs),
            'crs_approved': len(approved_crs),
            'crs_implemented': len(implemented_crs),
            'avg_resolution_time': avg_resolution_time,
            'approval_rate': approval_rate,
            'sla_breached': sla_breached
        })
    
    # Calculate SLA compliance rate
    total_crs = len(crs)
    breached_crs = len([cr for cr in crs if cr.is_sla_breached])
    sla_compliance_rate = f"{((total_crs - breached_crs) / total_crs * 100):.1f}%" if total_crs > 0 else "N/A"
    
    project_report = {
        'project': project,
        'total_crs': total_crs,
        'status_counts': status_counts,
        'priority_counts': priority_counts,
        'member_performance': member_performance,
        'sla_compliance_rate': sla_compliance_rate,
        'sla_breached_count': breached_crs
    }
    
    current_date = datetime.now().strftime('%B %d, %Y')
    
    # Render the PDF template
    html_content = render_template('admin/report_pdf.html',
                                  project_report=project_report,
                                  current_date=current_date)
    
    # Generate PDF
    pdf_file = HTML(string=html_content).write_pdf()
    
    # Create response
    response = make_response(pdf_file)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=report_{project.code}_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user (admin only, requires password confirmation)"""
    # Get the user to delete
    user_to_delete = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user_to_delete.id == current_user.id:
        flash('❌ You cannot delete your own account', 'danger')
        return redirect(url_for('admin.users'))
    
    # Get admin password from form
    admin_password = request.form.get('admin_password', '').strip()
    
    if not admin_password:
        flash('❌ Admin password is required to delete users', 'danger')
        return redirect(url_for('admin.users'))
    
    # Verify admin password
    if not check_password_hash(current_user.password_hash, admin_password):
        flash('❌ Incorrect admin password', 'danger')
        return redirect(url_for('admin.users'))
    
    # Count CRs before deletion
    from app.models.change_request import ChangeRequest, CRStatus
    change_requests_count = ChangeRequest.query.filter_by(requester_id=user_to_delete.id).count()
    as_approver = ChangeRequest.query.filter_by(approver_id=user_to_delete.id).count()
    as_implementer = ChangeRequest.query.filter_by(implementer_id=user_to_delete.id).count()
    total_crs = change_requests_count + as_approver + as_implementer
    
    # Close all CRs where user is requester
    if change_requests_count > 0:
        ChangeRequest.query.filter_by(requester_id=user_to_delete.id).update({
            'status': CRStatus.CLOSED,
            'rejection_reason': f'Auto-closed due to requester deletion by admin {current_user.email}'
        })
    
    # Unassign user from CRs where they are approver or implementer
    if as_approver > 0:
        ChangeRequest.query.filter_by(approver_id=user_to_delete.id).update({'approver_id': None})
    
    if as_implementer > 0:
        ChangeRequest.query.filter_by(implementer_id=user_to_delete.id).update({'implementer_id': None})
    
    # Remove user from all project memberships
    ProjectMembership.query.filter_by(user_id=user_to_delete.id).update({'is_active': False})
    
    # Log user deletion
    from app.models.audit import AuditLog, AuditEventType, AuditEventCategory
    
    AuditLog.create_log(
        event_type=AuditEventType.USER_DELETED,
        event_category=AuditEventCategory.USER_MANAGEMENT,
        user=current_user,
        description=f'Admin {current_user.email} deleted user {user_to_delete.email}',
        resource_type='User',
        resource_id=user_to_delete.id,
        request=request,
        success=True,
        metadata={
            'deleted_user_id': user_to_delete.id,
            'deleted_user_email': user_to_delete.email,
            'deleted_user_role': user_to_delete.role.name if user_to_delete.role else 'N/A'
        }
    )
    
    # Delete user (cascade will delete invitation and related records)
    email = user_to_delete.email
    db.session.delete(user_to_delete)
    db.session.commit()
    
    if total_crs > 0:
        flash(f'✅ User "{email}" deleted successfully. {total_crs} CR(s) closed/unassigned and all project memberships removed.', 'success')
    else:
        flash(f'✅ User "{email}" deleted successfully.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/trigger-sla-check', methods=['POST'])
@login_required
@admin_required
def trigger_sla_check():
    """
    Manually trigger SLA deadline check (for testing/immediate check)
    Admin-only access
    """
    try:
        from app.services.sla_monitor import check_sla_deadlines
        check_sla_deadlines()
        flash('✅ SLA check triggered successfully. Check logs for details.', 'success')
    except Exception as e:
        current_app.logger.error(f"Error triggering SLA check: {str(e)}")
        flash(f'❌ Error triggering SLA check: {str(e)}', 'danger')
    
    return redirect(request.referrer or url_for('admin.dashboard'))
