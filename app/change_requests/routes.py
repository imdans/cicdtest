"""
Change Request routes
Implements CMS-F-005, CMS-F-006, CMS-F-007
"""
import os
from flask import render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.change_requests import cr_bp
from app.change_requests.forms import ChangeRequestForm, ApprovalForm, RollbackForm, ClosureForm
from app.auth.decorators import permission_required
from app.models import ChangeRequest, CRAttachment, CRStatus, User, Project
from app.models.audit import AuditEventType
from app.audit.logger import log_cr_event
from app.services import EmailService
from app.extensions import db
from datetime import datetime


@cr_bp.route('/')
@login_required
def list_change_requests():
    """
    List change requests
    Shows CRs based on user's project access and role
    - Admins: Only CRs of projects they created
    - Requesters: Only their own CRs in assigned projects
    - Approvers: All CRs in assigned projects
    - Implementers: Only APPROVED CRs in assigned projects
    """
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    priority = request.args.get('priority')
    project_id = request.args.get('project_id', type=int)
    
    user_role_name = current_user.role.name.lower() if current_user.role else None
    
    # Build query based on user role and project access
    if user_role_name == 'admin':
        # Admins see only CRs of projects they created
        admin_projects = Project.query.filter_by(created_by_id=current_user.id).all()
        admin_project_ids = [p.id for p in admin_projects]
        
        if not admin_project_ids:
            flash('You have not created any projects yet.', 'info')
            return render_template('change_requests/list.html', change_requests=None, user_projects=[])
        
        query = ChangeRequest.query.filter(ChangeRequest.project_id.in_(admin_project_ids))
        user_projects_list = admin_projects
        
    else:
        # Get user's assigned projects
        user_projects = [p.id for p in current_user.get_projects()]
        
        if not user_projects:
            flash('You are not assigned to any project. Contact admin.', 'warning')
            return render_template('change_requests/list.html', change_requests=None, user_projects=[])
        
        # Filter by projects user has access to
        query = ChangeRequest.query.filter(ChangeRequest.project_id.in_(user_projects))
        
        if user_role_name == 'requester':
            # Requesters only see their own CRs
            query = query.filter(ChangeRequest.requester_id == current_user.id)
        
        elif user_role_name == 'implementer':
            # Implementers only see APPROVED CRs (ready for implementation)
            query = query.filter(ChangeRequest.status.in_([
                CRStatus.APPROVED,
                CRStatus.IN_PROGRESS,
                CRStatus.IMPLEMENTED,
                CRStatus.CLOSED,
                CRStatus.ROLLED_BACK
            ]))
        
        # Approvers see all CRs in their projects (no additional filter needed)
        
        user_projects_list = current_user.get_projects()
    
    # Apply filters
    if project_id:
        query = query.filter(ChangeRequest.project_id == project_id)
    
    if status:
        query = query.filter(ChangeRequest.status == status)
    
    if priority:
        query = query.filter(ChangeRequest.priority == priority)
    
    # Order by created date descending
    query = query.order_by(ChangeRequest.created_at.desc())
    
    # Paginate
    change_requests = query.paginate(page=page, per_page=20, error_out=False)
    
    return render_template('change_requests/list.html', 
                         change_requests=change_requests,
                         user_projects=user_projects_list)


@cr_bp.route('/create', methods=['GET', 'POST'])
@login_required
@permission_required('submit_cr')
def create():
    """
    Create new change request
    Implements CMS-F-005: Submit new Change Request
    Implements CMS-F-006: Attach supporting documents
    """
    # Get user's projects
    user_projects = current_user.get_projects() if not current_user.is_admin() else Project.query.filter_by(is_active=True).all()
    
    if not user_projects:
        flash('You are not assigned to any project. Contact admin to create CRs.', 'warning')
        return redirect(url_for('cr.list_change_requests'))
    
    form = ChangeRequestForm()
    
    if form.validate_on_submit():
        project_id = request.form.get('project_id', type=int)
        
        if not project_id:
            flash('Please select a project.', 'danger')
            return render_template('change_requests/create.html', form=form, user_projects=user_projects)
        
        # Verify user has access to selected project
        if not current_user.is_admin() and not current_user.has_project_access(Project.query.get(project_id)):
            flash('You do not have access to this project.', 'danger')
            return redirect(url_for('cr.list_change_requests'))
        
        # Create CR
        cr = ChangeRequest(
            cr_number=ChangeRequest.generate_cr_number(),
            project_id=project_id,
            title=form.title.data,
            description=form.description.data,
            justification=form.justification.data,
            impact_assessment=form.impact_assessment.data,
            priority=form.priority.data,
            risk_level=form.risk_level.data,
            implementation_deadline=form.implementation_deadline.data,  # CMSF-015: SLA tracking
            rollback_plan=form.rollback_plan.data,
            requester_id=current_user.id,
            status=CRStatus.DRAFT
        )
        
        # Validate rollback plan for high-risk changes (CMSF-017)
        if cr.risk_level == 'high' and not (cr.rollback_plan or form.rollback_plan_file.data):
            flash('Rollback plan (text or file) is required for high-risk changes.', 'danger')
            return render_template('change_requests/create.html', form=form, user_projects=user_projects)
        
        db.session.add(cr)
        db.session.flush()  # Get CR ID
        
        # Handle rollback plan file upload (CMSF-017)
        if form.rollback_plan_file.data:
            file = form.rollback_plan_file.data
            if file.filename:
                filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                unique_filename = f"rollback_{timestamp}_{filename}"
                
                # Create rollback_plans subdirectory
                rollback_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'rollback_plans')
                os.makedirs(rollback_folder, exist_ok=True)
                
                file_path = os.path.join(rollback_folder, unique_filename)
                file.save(file_path)
                
                # Store relative path
                cr.rollback_plan_file = os.path.join('rollback_plans', unique_filename)
        
        # Handle file uploads (CMS-F-006)
        if form.attachments.data:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            os.makedirs(upload_folder, exist_ok=True)
            
            for file in form.attachments.data:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    # Add timestamp to avoid conflicts
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(upload_folder, unique_filename)
                    
                    # Save file
                    file.save(file_path)
                    
                    # Create attachment record
                    attachment = CRAttachment(
                        change_request_id=cr.id,
                        filename=unique_filename,
                        original_filename=filename,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        uploaded_by_id=current_user.id
                    )
                    db.session.add(attachment)
        
        # Check if submitting for approval
        if 'submit_for_approval' in request.form:
            cr.submit()
        
        db.session.commit()
        
        # Log CR creation
        log_cr_event(
            AuditEventType.CR_CREATED,
            cr,
            current_user,
            f'Change request {cr.cr_number} created by {current_user.username}',
            metadata={
                'title': cr.title,
                'priority': cr.priority.value,
                'status': cr.status.value
            }
        )
        
        # Send email notification to approvers if submitted for approval
        if cr.status == CRStatus.PENDING_APPROVAL:
            try:
                # Get approvers for the project (users with approve_cr permission)
                project = Project.query.get(cr.project_id)
                approvers = [member.user for member in project.members 
                           if member.user.has_permission('approve_cr')]
                
                if approvers:
                    email_service = EmailService()
                    email_service.send_cr_submission_notification(cr, approvers)
                else:
                    current_app.logger.warning(f"No approvers found for project {project.name}")
            except Exception as e:
                current_app.logger.error(f"Failed to send CR submission notification: {str(e)}")
        
        if cr.status == CRStatus.PENDING_APPROVAL:
            flash(f'Change request {cr.cr_number} submitted for approval!', 'success')
        else:
            flash(f'Change request {cr.cr_number} saved as draft.', 'success')
        
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    return render_template('change_requests/create.html', form=form, user_projects=user_projects)


@cr_bp.route('/<int:cr_id>')
@login_required
def view(cr_id):
    """
    View change request details
    Access control based on role and project membership
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    # Check if user can access this CR (includes role-based and project-based checks)
    if not current_user.can_access_cr(cr):
        flash('Access Denied: You do not have permission to view this change request.', 'danger')
        return redirect(url_for('cr.list_change_requests'))
    
    # Log CR view
    log_cr_event(
        AuditEventType.CR_VIEWED,
        cr,
        current_user,
        f'Change request {cr.cr_number} viewed by {current_user.email}'
    )
    
    return render_template('change_requests/view.html', cr=cr)


@cr_bp.route('/<int:cr_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(cr_id):
    """
    Edit change request
    Implements CMS-F-007: Edit CRs before submission
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    # Check project access first
    if not current_user.can_access_cr(cr):
        flash('Access Denied: You do not have permission to access this change request.', 'danger')
        return redirect(url_for('cr.list_change_requests'))
    
    # Check if user can edit
    if not cr.can_edit(current_user):
        flash('Access Denied: You do not have permission to edit this change request.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr_id))
    
    form = ChangeRequestForm(obj=cr)
    
    if form.validate_on_submit():
        # Update CR
        cr.title = form.title.data
        cr.description = form.description.data
        cr.justification = form.justification.data
        cr.impact_assessment = form.impact_assessment.data
        cr.priority = form.priority.data
        cr.risk_level = form.risk_level.data
        cr.rollback_plan = form.rollback_plan.data
        
        # Validate rollback plan for high-risk changes
        if cr.risk_level == 'high' and not cr.rollback_plan:
            flash('Rollback plan is required for high-risk changes.', 'danger')
            return render_template('change_requests/edit.html', form=form, cr=cr)
        
        # Handle new file uploads
        if form.attachments.data:
            upload_folder = current_app.config['UPLOAD_FOLDER']
            
            for file in form.attachments.data:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    unique_filename = f"{timestamp}_{filename}"
                    file_path = os.path.join(upload_folder, unique_filename)
                    
                    file.save(file_path)
                    
                    attachment = CRAttachment(
                        change_request_id=cr.id,
                        filename=unique_filename,
                        original_filename=filename,
                        file_path=file_path,
                        file_size=os.path.getsize(file_path),
                        uploaded_by_id=current_user.id
                    )
                    db.session.add(attachment)
        
        # Check if submitting for approval
        if 'submit_for_approval' in request.form and cr.status == CRStatus.DRAFT:
            cr.submit()
        
        db.session.commit()
        
        # Log CR update
        log_cr_event(
            AuditEventType.CR_UPDATED,
            cr,
            current_user,
            f'Change request {cr.cr_number} updated by {current_user.username}',
            metadata={'title': cr.title, 'status': cr.status.value}
        )
        
        flash('Change request updated successfully!', 'success')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    return render_template('change_requests/edit.html', form=form, cr=cr)


@cr_bp.route('/<int:cr_id>/approve', methods=['GET', 'POST'])
@login_required
@permission_required('approve_cr')
def approve(cr_id):
    """
    Approve or reject change request
    Implements CMS-F-009: Allow approvers to accept, reject, or request changes
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    if not cr.can_approve(current_user):
        flash('This change request is not in a state that can be approved.', 'warning')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    form = ApprovalForm()
    
    if form.validate_on_submit():
        if 'approve' in request.form:
            cr.approve(current_user, form.comments.data)
            
            # Log approval
            log_cr_event(
                AuditEventType.CR_APPROVED,
                cr,
                current_user,
                f'Change request {cr.cr_number} approved by {current_user.username}',
                metadata={'comments': form.comments.data}
            )
            
            # Send email notification to implementers
            try:
                project = Project.query.get(cr.project_id)
                implementers = [member.user for member in project.members if member.user.role.name == 'implementer']
                
                if implementers:
                    email_service = EmailService()
                    email_service.send_cr_approval_notification(cr, implementers)
            except Exception as e:
                current_app.logger.error(f"Failed to send CR approval notification: {str(e)}")
            
            flash(f'Change request {cr.cr_number} approved!', 'success')
            
        elif 'reject' in request.form:
            if not form.comments.data:
                flash('Please provide a reason for rejection.', 'danger')
                return render_template('change_requests/approve.html', form=form, cr=cr)
            
            cr.reject(current_user, form.comments.data)
            
            # Log rejection
            log_cr_event(
                AuditEventType.CR_REJECTED,
                cr,
                current_user,
                f'Change request {cr.cr_number} rejected by {current_user.username}',
                metadata={'reason': form.comments.data}
            )
            
            # Send email notification to requester
            try:
                email_service = EmailService()
                email_service.send_cr_rejection_notification(cr, form.comments.data)
            except Exception as e:
                current_app.logger.error(f"Failed to send CR rejection notification: {str(e)}")
            
            flash(f'Change request {cr.cr_number} rejected.', 'info')
        
        db.session.commit()
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    return render_template('change_requests/approve.html', form=form, cr=cr)


@cr_bp.route('/<int:cr_id>/rollback', methods=['GET', 'POST'])
@login_required
@permission_required('rollback_cr')
def rollback(cr_id):
    """
    Rollback change request
    Implements CMS-F-018: Support rollback execution with justification
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    form = RollbackForm()
    
    if form.validate_on_submit():
        cr.rollback(current_user, form.reason.data)
        db.session.commit()
        
        # Log rollback
        log_cr_event(
            AuditEventType.CR_ROLLED_BACK,
            cr,
            current_user,
            f'Change request {cr.cr_number} rolled back by {current_user.username}',
            metadata={'reason': form.reason.data}
        )
        
        flash(f'Change request {cr.cr_number} has been rolled back.', 'info')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    return render_template('change_requests/rollback.html', form=form, cr=cr)


@cr_bp.route('/<int:cr_id>/implement', methods=['GET', 'POST'])
@login_required
@permission_required('implement_cr')
def implement(cr_id):
    """
    Implementer workspace for CR implementation
    Implements CMSF-015: Track implementation with deadline countdown
    Allows implementers to view files, make changes, and mark CR as implemented
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    # Check if user has access to this CR's project
    if not current_user.is_admin() and not current_user.has_project_access(cr.project):
        flash('You do not have access to this project.', 'danger')
        return redirect(url_for('cr.list_change_requests'))
    
    # Only approved CRs can be implemented
    if cr.status not in [CRStatus.APPROVED, CRStatus.IN_PROGRESS]:
        flash('Only approved CRs can be implemented.', 'warning')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    if request.method == 'POST':
        action = request.form.get('action')
        current_app.logger.info(f"Implement POST - action: {action}, form keys: {list(request.form.keys())}")
        
        if action == 'start':
            # Start implementation
            if cr.status == CRStatus.APPROVED:
                cr.start_implementation(current_user)
                db.session.commit()
                
                log_cr_event(
                    AuditEventType.CR_UPDATED,
                    cr,
                    current_user,
                    f'Implementation started for CR {cr.cr_number}',
                    metadata={'old_status': 'approved', 'new_status': 'in_progress'}
                )
                
                flash('✅ Implementation started. You can now work on this CR.', 'success')
                return redirect(url_for('cr.implement', cr_id=cr.id))
        
        elif action == 'mark_implemented':
            # Mark as implemented
            cr.complete_implementation()
            db.session.commit()
            
            log_cr_event(
                AuditEventType.CR_IMPLEMENTED,
                cr,
                current_user,
                f'CR {cr.cr_number} marked as implemented by {current_user.username}'
            )
            
            # Send notification to approver for closure (CMSF-019)
            try:
                if cr.approver:
                    email_service = EmailService()
                    email_service.send_implementation_complete_notification(cr)
            except Exception as e:
                current_app.logger.error(f"Failed to send implementation complete notification: {str(e)}")
            
            flash('✅ CR marked as implemented! Approver has been notified for closure.', 'success')
            return redirect(url_for('cr.view', cr_id=cr.id))
        
        elif action == 'save_file':
            # Save edited file content (AJAX request)
            file_id = request.form.get('file_id', type=int)
            file_content = request.form.get('file_content')
            
            current_app.logger.info(f"Save file - file_id: {file_id}, content length: {len(file_content) if file_content is not None else 'None'}")
            
            if file_id and file_content is not None:
                attachment = CRAttachment.query.get(file_id)
                if attachment and attachment.change_request_id == cr.id:
                    try:
                        # Save the updated file content
                        with open(attachment.file_path, 'w') as f:
                            f.write(file_content)
                        
                        return jsonify({'success': True, 'message': 'File saved successfully'})
                    except Exception as e:
                        return jsonify({'success': False, 'message': f'Error saving file: {str(e)}'}), 500
                else:
                    return jsonify({'success': False, 'message': 'File not found or access denied'}), 404
            else:
                return jsonify({'success': False, 'message': 'Missing file ID or content'}), 400
        
        elif action == 'upload_file':
            # Upload new file attachment (AJAX request)
            if 'files' not in request.files:
                return jsonify({'success': False, 'message': 'No files provided'}), 400
            
            files = request.files.getlist('files')
            if not files or files[0].filename == '':
                return jsonify({'success': False, 'message': 'No files selected'}), 400
            
            uploaded_count = 0
            for file in files:
                if file and file.filename:
                    try:
                        filename = secure_filename(file.filename)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        unique_filename = f"{timestamp}_{filename}"
                        
                        # Create uploads directory if it doesn't exist
                        upload_dir = os.path.join(current_app.root_path, '..', 'static', 'uploads')
                        os.makedirs(upload_dir, exist_ok=True)
                        
                        filepath = os.path.join(upload_dir, unique_filename)
                        file.save(filepath)
                        
                        # Create attachment record
                        attachment = CRAttachment(
                            change_request_id=cr.id,
                            filename=unique_filename,
                            original_filename=filename,
                            file_path=filepath,
                            file_size=os.path.getsize(filepath),
                            uploaded_by_id=current_user.id
                        )
                        db.session.add(attachment)
                        uploaded_count += 1
                    except Exception as e:
                        current_app.logger.error(f"Error uploading file {file.filename}: {str(e)}")
                        continue
            
            if uploaded_count > 0:
                db.session.commit()
                log_cr_event(
                    AuditEventType.CR_UPDATED,
                    cr,
                    current_user,
                    f'{uploaded_count} file(s) uploaded during implementation'
                )
                return jsonify({'success': True, 'message': f'{uploaded_count} file(s) uploaded successfully'})
            else:
                return jsonify({'success': False, 'message': 'Failed to upload files'}), 500
        
        else:
            flash('❌ Invalid action.', 'danger')
            return redirect(url_for('cr.implement', cr_id=cr.id))
    
    # Calculate time remaining
    time_remaining = None
    is_deadline_passed = False
    if cr.implementation_deadline:
        time_remaining = cr.time_until_deadline()
        if time_remaining:
            if time_remaining.total_seconds() < 0:
                is_deadline_passed = True
    
    return render_template('change_requests/implement.html', 
                         cr=cr, 
                         time_remaining=time_remaining,
                         is_deadline_passed=is_deadline_passed)


@cr_bp.route('/<int:cr_id>/add-rollback-plan', methods=['POST'])
@login_required
def add_rollback_plan(cr_id):
    """
    Add or update rollback plan for a CR.
    Only requestor can add rollback plan before approval.
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    # Check permissions - only requestor can add rollback plan
    if cr.requester_id != current_user.id:
        flash('Only the requestor can add a rollback plan.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    # Check status - only draft/submitted CRs can have rollback plan added
    if cr.status not in [CRStatus.DRAFT, CRStatus.SUBMITTED]:
        flash('Rollback plan can only be added to draft or submitted CRs.', 'warning')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    # Handle file upload
    if 'rollback_file' not in request.files:
        flash('No file provided.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    file = request.files['rollback_file']
    
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    if file:
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"rollback_{cr.cr_number}_{timestamp}_{filename}"
            
            # Create rollback_plans directory if it doesn't exist
            rollback_dir = os.path.join(current_app.root_path, '..', 'static', 'uploads', 'rollback_plans')
            os.makedirs(rollback_dir, exist_ok=True)
            
            filepath = os.path.join(rollback_dir, unique_filename)
            file.save(filepath)
            
            # Update CR with rollback plan file
            cr.rollback_plan_file = unique_filename
            db.session.commit()
            
            log_cr_event(
                AuditEventType.CR_UPDATED,
                cr,
                current_user,
                f'Rollback plan file uploaded for CR {cr.cr_number}'
            )
            
            flash('✅ Rollback plan uploaded successfully!', 'success')
        except Exception as e:
            current_app.logger.error(f"Error uploading rollback plan: {str(e)}")
            flash(f'❌ Error uploading rollback plan: {str(e)}', 'danger')
    
    return redirect(url_for('cr.view', cr_id=cr.id))


@cr_bp.route('/<int:cr_id>/close', methods=['GET', 'POST'])
@login_required
@permission_required('approve_cr')
def close_cr(cr_id):
    """
    Close a change request (CMSF-019).
    Only approvers can close implemented CRs.
    Sends complete timeline to admin.
    """
    cr = ChangeRequest.query.get_or_404(cr_id)
    
    # Verify CR is in correct state for closure
    if cr.status != CRStatus.IMPLEMENTED:
        flash('❌ Only implemented CRs can be closed.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    # Verify user is the approver or has admin privileges
    if cr.approver_id != current_user.id and not current_user.has_permission('manage_users'):
        flash('❌ Only the assigned approver can close this CR.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    
    form = ClosureForm()
    
    if form.validate_on_submit():
        # Close the CR
        cr.close(current_user, form.closure_notes.data, form.comments.data)
        
        try:
            db.session.commit()
            
            log_cr_event(
                AuditEventType.CR_CLOSED,
                cr,
                current_user,
                f'CR {cr.cr_number} closed by {current_user.username}'
            )
            
            # Send timeline to admin (CMSF-019)
            try:
                email_service = EmailService()
                email_service.send_closure_timeline_email(cr)
            except Exception as e:
                current_app.logger.error(f"Failed to send closure timeline email: {str(e)}")
            
            flash('✅ Change Request successfully closed! Timeline sent to admin.', 'success')
            return redirect(url_for('cr.view', cr_id=cr.id))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error closing CR {cr.cr_number}: {str(e)}")
            flash('❌ Error closing change request. Please try again.', 'danger')
    
    # Calculate total time taken
    time_taken = None
    if cr.created_at and cr.closed_date:
        time_taken = cr.closed_date - cr.created_at
    elif cr.created_at:
        time_taken = datetime.now() - cr.created_at
    
    # Convert timeline dict to list for template
    timeline_dict = cr.get_timeline()
    timeline = []
    event_mapping = {
        'created': 'Created',
        'submitted': 'Submitted',
        'approved': 'Approved',
        'implemented': 'Implemented',
        'closed': 'Closed'
    }
    
    for key, label in event_mapping.items():
        if timeline_dict.get(key):
            timeline.append({
                'event': label,
                'timestamp': timeline_dict[key]['date'],
                'user': timeline_dict[key]['user'],
                'role': timeline_dict[key]['role']
            })
    
    return render_template('change_requests/close.html', 
                         cr=cr, 
                         form=form,
                         timeline=timeline,
                         time_taken=time_taken)


@cr_bp.route('/attachments/<int:attachment_id>/download')
@login_required
def download_attachment(attachment_id):
    """
    Download a CR attachment
    User must have access to view the associated CR
    """
    from flask import send_file
    from app.models.change_request import CRAttachment
    
    attachment = CRAttachment.query.get_or_404(attachment_id)
    cr = attachment.change_request
    
    # Check if user has access to view this CR
    if not current_user.can_access_cr(cr):
        flash('You do not have permission to access this change request.', 'danger')
        return redirect(url_for('cr.list_change_requests'))
    
    try:
        return send_file(
            attachment.file_path,
            as_attachment=True,
            download_name=attachment.original_filename,
            mimetype=attachment.mime_type
        )
    except FileNotFoundError:
        flash('File not found. It may have been deleted.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
    except Exception as e:
        current_app.logger.error(f"Error downloading attachment: {str(e)}")
        flash('Error downloading file.', 'danger')
        return redirect(url_for('cr.view', cr_id=cr.id))
