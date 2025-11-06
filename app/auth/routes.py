"""
Authentication routes
Implements CMS-F-001, CMS-F-002, CMS-F-004
"""
from flask import render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import auth_bp
from app.auth.forms import LoginForm, MFAVerifyForm, ProfileForm, AcceptInvitationForm
from app.models import User, UserInvitation
from app.models.audit import AuditLog, AuditEventType, AuditEventCategory
from app.extensions import db, limiter, csrf
from werkzeug.security import generate_password_hash


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    """
    User login
    Implements CMS-F-001: Authenticate users via email and password
    Implements CMS-F-004: Log all login attempts
    """
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        
        # Check if user exists and password is correct
        if user and user.check_password(form.password.data):
            # Check if account is locked
            if user.is_locked:
                AuditLog.create_log(
                    event_type=AuditEventType.LOGIN_FAILED,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    user=user,
                    description=f'Login attempt for locked account: {user.email}',
                    request=request,
                    success=False,
                    metadata={'reason': 'account_locked'}
                )
                flash('Your account has been locked. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Check if account is active
            if not user.is_active:
                AuditLog.create_log(
                    event_type=AuditEventType.LOGIN_FAILED,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    user=user,
                    description=f'Login attempt for inactive account: {user.email}',
                    request=request,
                    success=False,
                    metadata={'reason': 'account_inactive'}
                )
                flash('Your account is inactive. Please contact an administrator.', 'danger')
                return redirect(url_for('auth.login'))
            
            # Reset failed login attempts
            user.reset_failed_login()
            user.update_last_login(request.remote_addr)
            db.session.commit()
            
            # CMS-F-002: Check if MFA is required for admins
            if user.is_admin() and user.mfa_enabled:
                # Store user ID in session for MFA verification
                session['mfa_user_id'] = user.id
                session['mfa_verified'] = False
                
                AuditLog.create_log(
                    event_type=AuditEventType.LOGIN_SUCCESS,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    user=user,
                    description=f'Login successful for {user.email}, MFA required',
                    request=request,
                    success=True
                )
                
                flash('Please enter your MFA code.', 'info')
                return redirect(url_for('auth.verify_mfa'))
            
            # Login user
            login_user(user, remember=form.remember_me.data)
            session['mfa_verified'] = True  # No MFA required
            
            # Log successful login (CMS-F-004)
            AuditLog.create_log(
                event_type=AuditEventType.LOGIN_SUCCESS,
                event_category=AuditEventCategory.AUTHENTICATION,
                user=user,
                description=f'Login successful for {user.email}',
                request=request,
                success=True
            )
            
            flash('Login successful!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('index'))
        
        else:
            # Failed login attempt
            if user:
                user.increment_failed_login()
                db.session.commit()
                
                # Log failed login (CMS-F-004)
                AuditLog.create_log(
                    event_type=AuditEventType.LOGIN_FAILED,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    user=user,
                    description=f'Failed login attempt for {user.email}',
                    request=request,
                    success=False,
                    metadata={
                        'failed_attempts': user.failed_login_attempts,
                        'account_locked': user.is_locked
                    }
                )
            else:
                # Log failed login with unknown user
                AuditLog.create_log(
                    event_type=AuditEventType.LOGIN_FAILED,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    description=f'Failed login attempt for unknown email: {form.email.data}',
                    request=request,
                    success=False,
                    metadata={'email': form.email.data}
                )
            
            flash('Invalid email or password', 'danger')
    
    return render_template('auth/login.html', form=form)


@auth_bp.route('/verify-mfa', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def verify_mfa():
    """
    Verify MFA code
    Implements CMS-F-002: MFA for admins
    """
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = User.query.get(user_id)
    if not user:
        flash('Invalid session. Please log in again.', 'danger')
        return redirect(url_for('auth.login'))
    
    form = MFAVerifyForm()
    
    # Generate provisioning URI for setup
    import pyotp
    import qrcode
    import qrcode.image.svg
    import io
    
    totp = pyotp.TOTP(user.mfa_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name='Change Management System'
    )
    
    # Generate QR code as SVG (no Pillow required)
    factory = qrcode.image.svg.SvgPathImage
    qr = qrcode.QRCode(image_factory=factory)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    # Convert to SVG string
    buffer = io.BytesIO()
    img = qr.make_image()
    img.save(buffer)
    qr_code_svg = buffer.getvalue().decode()
    
    if form.validate_on_submit():
        if user.verify_totp(form.code.data):
            # MFA verified successfully
            login_user(user)
            session['mfa_verified'] = True
            session.pop('mfa_user_id', None)
            
            # Log successful MFA
            AuditLog.create_log(
                event_type=AuditEventType.MFA_VERIFIED,
                event_category=AuditEventCategory.AUTHENTICATION,
                user=user,
                description=f'MFA verified for {user.username}',
                request=request,
                success=True
            )
            
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            # Log failed MFA
            AuditLog.create_log(
                event_type=AuditEventType.MFA_FAILED,
                event_category=AuditEventCategory.AUTHENTICATION,
                user=user,
                description=f'Failed MFA attempt for {user.username}',
                request=request,
                success=False
            )
            
            flash('Invalid MFA code. Please try again.', 'danger')
    
    return render_template('auth/mfa_verify.html', 
                         form=form, 
                         qr_code_svg=qr_code_svg,
                         mfa_secret=user.mfa_secret,
                         email=user.email)


@auth_bp.route('/logout')
def logout():
    """User logout"""
    if current_user.is_authenticated:
        # Log logout
        AuditLog.create_log(
            event_type=AuditEventType.LOGOUT,
            event_category=AuditEventCategory.AUTHENTICATION,
            user=current_user,
            description=f'User {current_user.username} logged out',
            request=request,
            success=True
        )
    
    # Clear Flask-Login session
    logout_user()
    
    # Clear all session data
    session.clear()
    
    # Add flash message
    flash('You have been logged out successfully.', 'info')
    
    return redirect(url_for('auth.login'))


@auth_bp.route('/accept-invitation/<token>', methods=['GET', 'POST'])
@csrf.exempt  # Exempt from CSRF since token provides security
def accept_invitation(token):
    """Accept user invitation and set password"""
    current_app.logger.info(f"Accept invitation route called with token: {token[:10]}... Method: {request.method}")
    
    # Check if user is already logged in
    if current_user.is_authenticated:
        logout_user()
        session.clear()
    
    # Find invitation
    invitation = UserInvitation.query.filter_by(token=token).first()
    
    if not invitation:
        current_app.logger.error(f"Invalid invitation token: {token}")
        flash('Invalid invitation link.', 'danger')
        return redirect(url_for('auth.login'))
    
    if not invitation.is_valid():
        current_app.logger.warning(f"Expired or used invitation: {token}")
        flash('This invitation has expired or has already been accepted.', 'warning')
        return redirect(url_for('auth.login'))
    
    user = invitation.user
    current_app.logger.info(f"Valid invitation found for user: {user.email}")
    
    form = AcceptInvitationForm()
    
    if form.validate_on_submit():
        current_app.logger.info(f"Form validated for user: {user.email}")
        
        try:
            # Update user name and password
            full_name = form.full_name.data.strip()
            if ' ' in full_name:
                parts = full_name.rsplit(' ', 1)
                user.first_name = parts[0]
                user.last_name = parts[1]
            else:
                user.first_name = full_name
                user.last_name = ''
            
            user.password_hash = generate_password_hash(form.password.data)
            user.is_active = True
            # MFA is already configured via invitation (admin-only)
            
            # Mark invitation as accepted
            invitation.accept()
            
            db.session.commit()
            
            current_app.logger.info(f"Account activated successfully for: {user.email}")
            
            # Log the account activation
            AuditLog.create_log(
                event_type=AuditEventType.USER_CREATED,
                event_category=AuditEventCategory.USER_MANAGEMENT,
                user=user,
                description=f'User {user.email} accepted invitation and activated account',
                request=request,
                success=True
            )
            
            # Custom message based on role
            if user.mfa_enabled:
                flash('Your account has been activated successfully! You can now log in with your password and authenticator app.', 'success')
            else:
                flash('Your account has been activated successfully! You can now log in with your password.', 'success')
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error activating account for {user.email}: {str(e)}")
            flash(f'An error occurred while activating your account. Please try again.', 'danger')
    
    return render_template('auth/accept_invitation.html', form=form, invitation=invitation, token=token)


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """
    User profile page - view and edit profile
    """
    form = ProfileForm()
    
    if request.method == 'GET':
        # Pre-populate form with current user data
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.email.data = current_user.email
    
    if form.validate_on_submit():
        try:
            # Update basic info
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            
            # Check if email is being changed
            if form.email.data != current_user.email:
                # Check if email is already taken
                existing_user = User.query.filter_by(email=form.email.data).first()
                if existing_user:
                    flash('This email is already in use.', 'danger')
                    return render_template('auth/profile.html', form=form)
                current_user.email = form.email.data
            
            # Handle password change
            if form.current_password.data:
                if not current_user.check_password(form.current_password.data):
                    flash('Current password is incorrect.', 'danger')
                    return render_template('auth/profile.html', form=form)
                
                if not form.new_password.data:
                    flash('Please enter a new password.', 'danger')
                    return render_template('auth/profile.html', form=form)
                
                current_user.set_password(form.new_password.data)
                
                # Log password change
                AuditLog.create_log(
                    event_type=AuditEventType.PASSWORD_CHANGED,
                    event_category=AuditEventCategory.AUTHENTICATION,
                    user=current_user,
                    description=f'Password changed by user: {current_user.email}',
                    request=request,
                    success=True
                )
                flash('Password updated successfully!', 'success')
            
            db.session.commit()
            
            # Log profile update
            AuditLog.create_log(
                event_type=AuditEventType.USER_UPDATED,
                event_category=AuditEventCategory.USER_MANAGEMENT,
                user=current_user,
                description=f'Profile updated by user: {current_user.email}',
                request=request,
                success=True
            )
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating profile for {current_user.email}: {str(e)}")
            flash('An error occurred while updating your profile.', 'danger')
    
    return render_template('auth/profile.html', form=form)
