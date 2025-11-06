"""
Email Notification Service
Handles all email notifications for the Change Management System
"""
import os
import smtplib
import email.utils
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from flask import current_app, render_template_string
from datetime import datetime
import io
import qrcode


class EmailService:
    """Service for sending email notifications"""
    
    @staticmethod
    def _get_smtp_config():
        """Get SMTP configuration from app config"""
        return {
            'server': current_app.config.get('SMTP_SERVER', 'smtp.gmail.com'),
            'port': current_app.config.get('SMTP_PORT', 587),
            'username': current_app.config.get('SMTP_USERNAME'),
            'password': current_app.config.get('SMTP_PASSWORD'),
            'from_email': current_app.config.get('SMTP_FROM_EMAIL', 'noreply@changemanagement.com'),
            'from_name': current_app.config.get('SMTP_FROM_NAME', 'Change Management System')
        }
    
    @staticmethod
    def _send_email(to_email, subject, html_content, attachments=None, plain_text=None):
        """
        Send an email
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            attachments: List of tuples (filename, content, mime_type)
            plain_text: Plain text alternative (optional)
        """
        try:
            config = EmailService._get_smtp_config()
            
            # Skip if SMTP not configured
            if not config['username'] or not config['password']:
                current_app.logger.warning(f"SMTP not configured. Email to {to_email} not sent: {subject}")
                return False
            
            # Create message with proper MIME structure
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject
            msg['From'] = f"{config['from_name']} <{config['from_email']}>"
            msg['To'] = to_email
            
            # Critical anti-spam headers
            msg['Reply-To'] = config['from_email']
            msg['Message-ID'] = f"<{hash(subject + to_email + str(hash(html_content[:100])))}@changemanagement.com>"
            msg['Date'] = email.utils.formatdate(localtime=True)
            msg['X-Priority'] = '3'
            msg['X-Mailer'] = 'Python-SMTP'
            msg['Return-Path'] = config['from_email']
            msg['Importance'] = 'Normal'
            msg['X-MSMail-Priority'] = 'Normal'
            msg['MIME-Version'] = '1.0'
            
            # Create related part for HTML with embedded images
            msg_related = MIMEMultipart('related')
            msg.attach(msg_related)
            
            # Create alternative part for text and HTML
            msg_alternative = MIMEMultipart('alternative')
            msg_related.attach(msg_alternative)
            
            # Attach plain text version first (important for spam filters)
            if plain_text:
                text_part = MIMEText(plain_text, 'plain', 'utf-8')
                msg_alternative.attach(text_part)
            
            # Attach HTML content
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg_alternative.attach(html_part)
            
            # Attach inline images to related part (not as attachments)
            if attachments:
                for filename, content, mime_type in attachments:
                    if mime_type.startswith('image/'):
                        img = MIMEImage(content)
                        img.add_header('Content-ID', f'<{filename}>')
                        img.add_header('Content-Disposition', 'inline', filename=filename)
                        msg_related.attach(img)  # Attach to related, not msg
            
            # Send email
            with smtplib.SMTP(config['server'], config['port']) as server:
                server.starttls()
                server.login(config['username'], config['password'])
                server.send_message(msg)
            
            current_app.logger.info(f"Email sent successfully to {to_email}: {subject}")
            return True
            
        except Exception as e:
            current_app.logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    @staticmethod
    def send_user_invitation(user, invitation_token, mfa_secret=None, qr_code_data=None):
        """
        Send invitation email to newly created user
        Args:
            user: User object
            invitation_token: Unique token for accepting invitation
            mfa_secret: MFA secret key (optional, only for admins)
            qr_code_data: MFA QR code URI (optional, only for admins)
        """
        accept_url = f"{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/auth/accept-invitation/{invitation_token}"
        
        attachments = []
        qr_code_html = ""
        
        # Generate QR code only if MFA is enabled (admins only)
        if qr_code_data and mfa_secret:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(qr_code_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            
            attachments.append(('qrcode.png', img_buffer.read(), 'image/png'))
            qr_code_html = f"""
            <table width="100%" cellpadding="0" cellspacing="0" style="margin: 25px 0;">
                <tr>
                    <td style="background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; padding: 25px;">
                        <h3 style="color: #856404; margin: 0 0 10px 0; font-size: 18px;">🔐 Multi-Factor Authentication Setup</h3>
                        <p style="color: #856404; margin: 0 0 20px 0; font-size: 14px;">As an administrator, your account requires MFA for enhanced security.</p>
                        
                        <table width="100%" cellpadding="20" cellspacing="0" style="background: white; border-radius: 5px;">
                            <tr>
                                <td align="center">
                                    <p style="margin: 0 0 10px 0; color: #333; font-weight: bold;">Step 1: Install an authenticator app</p>
                                    <p style="margin: 0 0 20px 0; font-size: 13px; color: #666;">Google Authenticator, Authy, or Microsoft Authenticator</p>
                                    
                                    <p style="margin: 0 0 15px 0; color: #333; font-weight: bold;">Step 2: Scan this QR code</p>
                                    <table cellpadding="0" cellspacing="0" style="margin: 0 auto;">
                                        <tr>
                                            <td style="padding: 15px; background: white; border: 3px solid #667eea; border-radius: 10px;">
                                                <img src="cid:qrcode.png" alt="MFA QR Code" width="200" height="200" style="display: block; margin: 0; padding: 0;"/>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="margin: 20px 0 10px 0; color: #333; font-weight: bold;">Or manually enter this code:</p>
                                    <p style="margin: 0; font-family: 'Courier New', monospace; font-size: 16px; color: #667eea; font-weight: bold; letter-spacing: 2px;">{mfa_secret}</p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            """
        
        # Role-specific message
        role_message = ""
        if user.role.name.lower() == 'admin':
            role_message = '<p style="color: #856404; background: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107;"><strong>Administrator Access:</strong> You have full system access including user management, project configuration, and audit logs.</p>'
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
            <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px 0;">
                <tr>
                    <td align="center">
                        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                            <!-- Header -->
                            <tr>
                                <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                                    <h1 style="color: #ffffff; margin: 0; font-size: 28px; font-weight: 600;">Welcome to CMS</h1>
                                    <p style="color: #ffffff; margin: 10px 0 0 0; font-size: 14px; opacity: 0.9;">Change Management System</p>
                                </td>
                            </tr>
                            
                            <!-- Content -->
                            <tr>
                                <td style="padding: 40px 30px;">
                                    <p style="font-size: 16px; color: #333; margin: 0 0 20px 0;">Hello <strong>{user.first_name or user.email.split('@')[0]}</strong>,</p>
                                    
                                    <p style="font-size: 15px; color: #555; line-height: 1.6; margin: 0 0 25px 0;">
                                        You have been invited to join the Change Management System. Click the button below to accept your invitation and set up your account.
                                    </p>
                                    
                                    {role_message}
                                    
                                    <!-- Account Details Box -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-left: 4px solid #667eea; margin: 25px 0;">
                                        <tr>
                                            <td style="padding: 20px;">
                                                <p style="margin: 0 0 15px 0; font-size: 14px; color: #333; font-weight: 600;">Your Account Details:</p>
                                                <p style="margin: 5px 0; font-size: 14px; color: #555;">📧 <strong>Email:</strong> {user.email}</p>
                                                <p style="margin: 5px 0; font-size: 14px; color: #555;">👤 <strong>Username:</strong> {user.username}</p>
                                                <p style="margin: 5px 0; font-size: 14px; color: #555;">🎭 <strong>Role:</strong> {user.role.name.title()}</p>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    {qr_code_html}
                                    
                                    <!-- CTA Button -->
                                    <table width="100%" cellpadding="0" cellspacing="0" style="margin: 35px 0;">
                                        <tr>
                                            <td align="center">
                                                <a href="{accept_url}" 
                                                   target="_blank"
                                                   style="display: inline-block; padding: 16px 40px; background-color: #667eea; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; box-shadow: 0 2px 4px rgba(102, 126, 234, 0.4);">
                                                    Accept Invitation & Activate Account
                                                </a>
                                            </td>
                                        </tr>
                                    </table>
                                    
                                    <p style="text-align: center; font-size: 12px; color: #666; margin: 10px 0 0 0;">
                                        Or copy and paste this link in your browser:<br>
                                        <a href="{accept_url}" style="color: #667eea; word-break: break-all;">{accept_url}</a>
                                    </p>
                                    
                                    <p style="font-size: 13px; color: #999; margin: 25px 0 0 0; padding-top: 20px; border-top: 1px solid #eee;">
                                        ⏰ <strong>Note:</strong> This invitation expires in 48 hours. If you didn't expect this invitation, please ignore this email.
                                    </p>
                                </td>
                            </tr>
                            
                            <!-- Footer -->
                            <tr>
                                <td style="background-color: #f8f9fa; padding: 20px 30px; text-align: center; border-top: 1px solid #eee;">
                                    <p style="margin: 0; font-size: 12px; color: #999;">
                                        © 2025 Change Management System | TheChangeMakers
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        
        # Create plain text version for better deliverability
        plain_text = f"""
Welcome to Change Management System
====================================

Hello {user.first_name or user.email.split('@')[0]},

You have been invited to join the Change Management System.

Your Account Details:
- Email: {user.email}
- Username: {user.username}
- Role: {user.role.name.title()}

{"As an administrator, your account requires Multi-Factor Authentication (MFA) for enhanced security." if user.role.name.lower() == 'admin' else ""}

{"MFA Setup Instructions:" if mfa_secret else ""}
{"1. Install an authenticator app (Google Authenticator, Authy, or Microsoft Authenticator)" if mfa_secret else ""}
{"2. Scan the QR code in the HTML version of this email" if mfa_secret else ""}
{"3. Or manually enter this code: " + mfa_secret if mfa_secret else ""}

To activate your account:
1. Click this link: {accept_url}
2. Set your password
3. Login with your email and password
{"4. Enter the 6-digit code from your authenticator app" if user.role.name.lower() == 'admin' else ""}

Note: This invitation expires in 48 hours.

If you didn't expect this invitation, please ignore this email.

---
© 2025 Change Management System | TheChangeMakers
        """
        
        return EmailService._send_email(
            user.email,
            "Invitation: Join Change Management System",
            html_content,
            attachments,
            plain_text
        )
    
    @staticmethod
    def send_cr_submission_notification(change_request, approvers):
        """Notify approvers when a CR is submitted"""
        for approver in approvers:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #667eea;">New Change Request Submitted</h2>
                <p>Hello {approver.first_name or approver.email},</p>
                <p>A new change request has been submitted and requires your approval.</p>
                
                <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                    <p><strong>Title:</strong> {change_request.title}</p>
                    <p><strong>Requester:</strong> {change_request.requester.email}</p>
                    <p><strong>Project:</strong> {change_request.project.name}</p>
                    <p><strong>Priority:</strong> {change_request.priority.value}</p>
                </div>
                
                <p>Please review and approve this change request at your earliest convenience.</p>
                <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{change_request.id}" 
                   style="display: inline-block; padding: 12px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;">
                    View Change Request
                </a>
            </body>
            </html>
            """
            EmailService._send_email(approver.email, f"New CR: {change_request.cr_number}", html_content)
    
    @staticmethod
    def send_cr_approval_notification(change_request, implementers):
        """Notify implementers when a CR is approved"""
        for implementer in implementers:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #28a745;">Change Request Approved</h2>
                <p>Hello {implementer.first_name or implementer.email},</p>
                <p>A change request has been approved and is ready for implementation.</p>
                
                <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0;">
                    <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                    <p><strong>Title:</strong> {change_request.title}</p>
                    <p><strong>Approved By:</strong> {change_request.approver.email if change_request.approver else 'N/A'}</p>
                    <p><strong>Project:</strong> {change_request.project.name}</p>
                </div>
                
                <p>Please begin implementation according to the approved plan.</p>
                <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{change_request.id}" 
                   style="display: inline-block; padding: 12px 30px; background: #28a745; color: white; text-decoration: none; border-radius: 5px;">
                    View Change Request
                </a>
            </body>
            </html>
            """
            EmailService._send_email(implementer.email, f"CR Approved: {change_request.cr_number}", html_content)
    
    def send_cr_rejection_notification(self, change_request, comments=None):
        """Notify requester when CR is rejected"""
        rejection_reason = comments or change_request.rejection_reason or 'Not specified'
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #dc3545;">Change Request Rejected</h2>
            <p>Hello {change_request.requester.first_name or change_request.requester.email},</p>
            <p>Your change request has been reviewed and rejected.</p>
            
            <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0;">
                <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                <p><strong>Title:</strong> {change_request.title}</p>
                <p><strong>Rejection Reason:</strong> {rejection_reason}</p>
            </div>
            
            <p>Please review the feedback and resubmit if necessary.</p>
        </body>
        </html>
        """
        EmailService._send_email(change_request.requester.email, f"CR Rejected: {change_request.cr_number}", html_content)
    
    @staticmethod
    def send_sla_breach_warning(change_request, hours_remaining):
        """Notify stakeholders of approaching SLA deadline"""
        recipients = [change_request.requester.email]
        if change_request.approver:
            recipients.append(change_request.approver.email)
        if change_request.implementer:
            recipients.append(change_request.implementer.email)
        
        for email in set(recipients):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #ff6b6b;">⚠️ SLA Deadline Warning</h2>
                <p>This is an automated reminder that a change request is approaching its SLA deadline.</p>
                
                <div style="background: #fff3cd; padding: 20px; border-left: 4px solid #ff6b6b; margin: 20px 0;">
                    <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                    <p><strong>Title:</strong> {change_request.title}</p>
                    <p><strong>Time Remaining:</strong> {hours_remaining} hours</p>
                    <p><strong>Current Status:</strong> {change_request.status.value}</p>
                </div>
                
                <p>Please take immediate action to prevent SLA breach.</p>
            </body>
            </html>
            """
            EmailService._send_email(email, f"SLA Warning: {change_request.cr_number}", html_content)
    
    @staticmethod
    def send_cr_closure_notification(change_request):
        """Notify stakeholders when CR is closed"""
        recipients = [change_request.requester.email]
        if change_request.approver:
            recipients.append(change_request.approver.email)
        if change_request.implementer:
            recipients.append(change_request.implementer.email)
        
        for email in set(recipients):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #667eea;">Change Request Closed</h2>
                <p>A change request has been completed and closed.</p>
                
                <div style="background: #f9f9f9; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
                    <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                    <p><strong>Title:</strong> {change_request.title}</p>
                    <p><strong>Final Status:</strong> {change_request.status.value}</p>
                    <p><strong>Closure Comments:</strong> {change_request.closure_comments or 'N/A'}</p>
                </div>
                
                <p>Thank you for your participation in this change request process.</p>
            </body>
            </html>
            """
            EmailService._send_email(email, f"CR Closed: {change_request.cr_number}", html_content)

    @staticmethod
    def send_cr_implementation_start(change_request):
        """Notify implementer when CR is approved and ready for implementation"""
        if not change_request.implementer:
            current_app.logger.warning(f"No implementer assigned for CR {change_request.cr_number}")
            return
        
        implementation_notes_html = ""
        if change_request.implementation_notes:
            implementation_notes_html = f"""
            <div style="background: #cce5ff; padding: 15px; border-left: 4px solid #007bff; margin: 20px 0;">
                <p><strong>📝 Implementation Notes:</strong></p>
                <p>{change_request.implementation_notes}</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #28a745;">🚀 Change Request Ready for Implementation</h2>
            <p>Dear {change_request.implementer.username},</p>
            <p>A change request has been <strong>approved</strong> and is ready for implementation.</p>
            
            <div style="background: #d4edda; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0;">
                <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                <p><strong>Title:</strong> {change_request.title}</p>
                <p><strong>Project:</strong> {change_request.project.name}</p>
                <p><strong>Priority:</strong> <span style="color: #dc3545;">{change_request.priority.value.upper()}</span></p>
                <p><strong>Approved By:</strong> {change_request.approver.username if change_request.approver else 'N/A'}</p>
                <p><strong>Approved Date:</strong> {change_request.approved_date.strftime('%Y-%m-%d %H:%M') if change_request.approved_date else 'N/A'}</p>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <p><strong>📋 Description:</strong></p>
                <p>{change_request.description}</p>
            </div>
            
            {implementation_notes_html}
            
            <p><strong>⚠️ Please ensure:</strong></p>
            <ul>
                <li>Review all implementation notes and requirements</li>
                <li>Follow the rollback plan if issues occur</li>
                <li>Update the CR status after implementation</li>
                <li>Document any code changes made</li>
            </ul>
            
            <div style="margin: 30px 0;">
                <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/change-requests/{change_request.id}" 
                   style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Change Request
                </a>
            </div>
            
            <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
        </body>
        </html>
        """
        EmailService._send_email(
            change_request.implementer.email,
            f"[ACTION REQUIRED] Implement CR: {change_request.cr_number}",
            html_content
        )

    @staticmethod
    def send_cr_implementation_complete(change_request, changed_code=None):
        """Notify approver when implementation is complete"""
        if not change_request.approver:
            current_app.logger.warning(f"No approver assigned for CR {change_request.cr_number}")
            return
        
        code_changes_html = ""
        if changed_code:
            code_changes_html = f"""
            <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #6c757d; margin: 20px 0;">
                <p><strong>💻 Code Changes:</strong></p>
                <pre style="background: #e9ecef; padding: 10px; border-radius: 5px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 0.9em;">{changed_code}</pre>
            </div>
            """
        
        implementation_notes_html = ""
        if change_request.implementation_notes:
            implementation_notes_html = f"""
            <div style="background: #e2e3e5; padding: 15px; border-left: 4px solid #6c757d; margin: 20px 0;">
                <p><strong>📝 Implementation Notes:</strong></p>
                <p>{change_request.implementation_notes}</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #17a2b8;">✅ Change Request Implementation Complete</h2>
            <p>Dear {change_request.approver.username},</p>
            <p>The implementation of a change request has been completed and is awaiting your review for closure.</p>
            
            <div style="background: #d1ecf1; padding: 20px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                <p><strong>Title:</strong> {change_request.title}</p>
                <p><strong>Project:</strong> {change_request.project.name}</p>
                <p><strong>Implemented By:</strong> {change_request.implementer.username if change_request.implementer else 'N/A'}</p>
                <p><strong>Implementation Date:</strong> {change_request.implementation_date.strftime('%Y-%m-%d %H:%M') if change_request.implementation_date else 'N/A'}</p>
            </div>
            
            {code_changes_html}
            {implementation_notes_html}
            
            <p><strong>📋 Next Steps:</strong></p>
            <ul>
                <li>Review the implementation details</li>
                <li>Verify all changes are working correctly</li>
                <li>Close the CR if satisfactory, or request rollback if issues found</li>
            </ul>
            
            <div style="margin: 30px 0;">
                <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/change-requests/{change_request.id}" 
                   style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Review & Close CR
                </a>
            </div>
            
            <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
        </body>
        </html>
        """
        EmailService._send_email(
            change_request.approver.email,
            f"[ACTION REQUIRED] Review Implemented CR: {change_request.cr_number}",
            html_content
        )

    @staticmethod
    def send_cr_rollback_request(change_request, rollback_reason):
        """Notify implementer when a rollback is requested"""
        if not change_request.implementer:
            current_app.logger.warning(f"No implementer assigned for CR {change_request.cr_number}")
            return
        
        rollback_plan_html = ""
        if change_request.rollback_plan:
            rollback_plan_html = f"""
            <div style="background: #d1ecf1; padding: 15px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                <p><strong>📋 Rollback Plan:</strong></p>
                <p>{change_request.rollback_plan}</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #dc3545;">⏪ Rollback Requested for Change Request</h2>
            <p>Dear {change_request.implementer.username},</p>
            <p><strong style="color: #dc3545;">URGENT:</strong> A rollback has been requested for a change request you implemented.</p>
            
            <div style="background: #f8d7da; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0;">
                <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                <p><strong>Title:</strong> {change_request.title}</p>
                <p><strong>Project:</strong> {change_request.project.name}</p>
                <p><strong>Requested By:</strong> {change_request.approver.username if change_request.approver else 'N/A'}</p>
            </div>
            
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <p><strong>🚨 Rollback Reason:</strong></p>
                <p>{rollback_reason}</p>
            </div>
            
            {rollback_plan_html}
            
            <p><strong>⚠️ Action Required:</strong></p>
            <ul>
                <li>Review the rollback reason immediately</li>
                <li>Follow the rollback plan to revert changes</li>
                <li>Update the CR status after rollback completion</li>
                <li>Document any issues encountered during rollback</li>
            </ul>
            
            <div style="margin: 30px 0;">
                <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/change-requests/{change_request.id}" 
                   style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View CR & Execute Rollback
                </a>
            </div>
            
            <p style="color: #dc3545; font-weight: bold;">⏰ This is a HIGH PRIORITY request. Please address immediately.</p>
            <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
        </body>
        </html>
        """
        EmailService._send_email(
            change_request.implementer.email,
            f"[URGENT] Rollback Required: {change_request.cr_number}",
            html_content
        )

    @staticmethod
    def send_cr_rollback_complete(change_request):
        """Notify approver when rollback is complete"""
        if not change_request.approver:
            current_app.logger.warning(f"No approver assigned for CR {change_request.cr_number}")
            return
        
        rollback_reason_html = ""
        if change_request.rollback_reason:
            rollback_reason_html = f"""
            <div style="background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0;">
                <p><strong>📝 Rollback Reason:</strong></p>
                <p>{change_request.rollback_reason}</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #6c757d;">🔄 Rollback Complete</h2>
            <p>Dear {change_request.approver.username},</p>
            <p>The rollback for a change request has been completed successfully.</p>
            
            <div style="background: #e2e3e5; padding: 20px; border-left: 4px solid #6c757d; margin: 20px 0;">
                <p><strong>CR Number:</strong> {change_request.cr_number}</p>
                <p><strong>Title:</strong> {change_request.title}</p>
                <p><strong>Project:</strong> {change_request.project.name}</p>
                <p><strong>Rolled Back By:</strong> {change_request.implementer.username if change_request.implementer else 'N/A'}</p>
                <p><strong>Rollback Date:</strong> {change_request.rolled_back_at.strftime('%Y-%m-%d %H:%M') if change_request.rolled_back_at else 'N/A'}</p>
            </div>
            
            {rollback_reason_html}
            
            <p>All changes have been reverted to the previous state. The change request status has been updated.</p>
            
            <div style="margin: 30px 0;">
                <a href="{os.getenv('BASE_URL', 'http://localhost:5000')}/change-requests/{change_request.id}" 
                   style="background: #6c757d; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Change Request
                </a>
            </div>
            
            <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
        </body>
        </html>
        """
        EmailService._send_email(
            change_request.approver.email,
            f"Rollback Complete: {change_request.cr_number}",
            html_content
        )

    @staticmethod
    def send_implementation_complete_notification(cr):
        """
        Send notification to approver when CR is marked as implemented (CMSF-019).
        Alerts approver to review and close the CR.
        """
        if not cr.approver:
            current_app.logger.warning(f"No approver assigned for CR {cr.cr_number}")
            return
        
        deadline_info = ""
        if cr.implementation_deadline:
            deadline_info = f"""
            <div style="background: #d4edda; padding: 15px; border-left: 4px solid #28a745; margin: 20px 0;">
                <p><strong>⏰ Deadline Status:</strong></p>
                <p>Implementation Deadline: {cr.implementation_deadline.strftime('%Y-%m-%d %H:%M')}</p>
                <p>Status: {'✅ Completed on time' if datetime.now() <= cr.implementation_deadline else '⚠️ Completed after deadline'}</p>
            </div>
            """
        
        rollback_info = ""
        if cr.rollback_plan or cr.rollback_plan_file:
            rollback_info = """
            <div style="background: #f8f9fa; padding: 15px; border-left: 4px solid #6c757d; margin: 20px 0;">
                <p><strong>🔄 Rollback Plan Available:</strong></p>
                <p>A rollback plan is available if any issues are found during review.</p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #28a745;">✅ CR Implementation Complete - Closure Required</h2>
            <p>Dear {cr.approver.username},</p>
            <p>The implementation of a change request has been <strong>completed</strong> and is now awaiting your review and closure.</p>
            
            <div style="background: #d4edda; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0;">
                <p><strong>CR Number:</strong> {cr.cr_number}</p>
                <p><strong>Title:</strong> {cr.title}</p>
                <p><strong>Project:</strong> {cr.project.name}</p>
                <p><strong>Implemented By:</strong> {cr.implementer.username if cr.implementer else 'N/A'}</p>
                <p><strong>Status:</strong> <span style="color: #28a745; font-weight: bold;">IMPLEMENTED</span></p>
            </div>
            
            {deadline_info}
            {rollback_info}
            
            <p><strong>📋 Next Steps - Action Required:</strong></p>
            <ul>
                <li>Review the implementation details and verify all changes</li>
                <li>Test the implemented changes in the appropriate environment</li>
                <li>Close the CR if everything is satisfactory</li>
                <li>Request rollback if any issues are found</li>
            </ul>
            
            <div style="margin: 30px 0;">
                <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{cr.id}/close" 
                   style="background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin-right: 10px;">
                    Close Change Request
                </a>
                <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{cr.id}" 
                   style="background: #17a2b8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    View Details
                </a>
            </div>
            
            <p style="color: #856404; background: #fff3cd; padding: 10px; border-radius: 5px; border-left: 4px solid #ffc107;">
                <strong>⚠️ Note:</strong> Please complete the closure process promptly. The complete timeline will be sent to the admin upon closure for record-keeping (CMSF-019).
            </p>
            
            <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
        </body>
        </html>
        """
        
        return EmailService._send_email(
            cr.approver.email,
            f"[ACTION REQUIRED] Close CR: {cr.cr_number} - Implementation Complete",
            html_content
        )

    @staticmethod
    def send_closure_timeline_email(cr):
        """
        Send complete CR timeline to admin after closure (CMSF-019).
        Provides detailed timeline for archival and reporting purposes.
        """
        # Get admin users
        from app.models import User
        admins = User.query.filter(User.role.has(name='admin')).all()
        
        if not admins:
            current_app.logger.warning(f"No admins found to send timeline for CR {cr.cr_number}")
            return
        
        # Get timeline as dictionary
        timeline = cr.get_timeline()
        
        # Generate timeline HTML
        timeline_html = ""
        timeline_events = [
            ('created', 'Created', '🚀'),
            ('submitted', 'Submitted', '�'),
            ('approved', 'Approved', '✅'),
            ('implemented', 'Implemented', '⚙️'),
            ('closed', 'Closed', '🏁')
        ]
        
        for key, label, icon in timeline_events:
            event_data = timeline.get(key)
            if event_data and event_data.get('date'):
                timeline_html += f"""
                <tr style="border-bottom: 1px solid #dee2e6;">
                    <td style="padding: 10px; white-space: nowrap;">{icon} {label}</td>
                    <td style="padding: 10px;">{event_data['date'].strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td style="padding: 10px;">{event_data.get('user', 'N/A')}</td>
                </tr>
                """
        
        # Calculate total time
        time_taken = ""
        if cr.closed_date and cr.created_at:
            delta = cr.closed_date - cr.created_at
            days = delta.days
            hours = (delta.seconds // 3600)
            minutes = ((delta.seconds % 3600) // 60)
            time_taken = f"{days} days, {hours} hours, {minutes} minutes"
        
        # Deadline compliance
        deadline_status = "N/A"
        if cr.implementation_deadline:
            if cr.implementation_date and cr.implementation_date <= cr.implementation_deadline:
                deadline_status = "✅ Met (Completed on time)"
            elif cr.implementation_date:
                deadline_status = "⚠️ Missed (Completed after deadline)"
            else:
                deadline_status = "❌ Not completed by deadline"
        
        for admin in admins:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #667eea;">🏁 Change Request Closed - Complete Timeline</h2>
                <p>Dear {admin.username},</p>
                <p>A change request has been successfully closed. Below is the complete timeline for your records (CMSF-019).</p>
                
                <div style="background: #e7f3ff; padding: 20px; border-left: 4px solid #667eea; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #667eea;">CR Summary</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">CR Number:</td><td style="padding: 5px;">{cr.cr_number}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Title:</td><td style="padding: 5px;">{cr.title}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Project:</td><td style="padding: 5px;">{cr.project.name}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Priority:</td><td style="padding: 5px;"><span style="color: #dc3545; font-weight: bold;">{cr.priority.value.upper()}</span></td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Risk Level:</td><td style="padding: 5px;"><span style="color: #ffc107; font-weight: bold;">{cr.risk_level.value.upper()}</span></td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Final Status:</td><td style="padding: 5px;"><span style="color: #28a745; font-weight: bold;">{cr.status.value.upper()}</span></td></tr>
                    </table>
                </div>
                
                <div style="background: #f8f9fa; padding: 20px; border-left: 4px solid #6c757d; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">⏱️ Timeline Metrics</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">Total Time:</td><td style="padding: 5px;">{time_taken}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">SLA Deadline:</td><td style="padding: 5px;">{cr.implementation_deadline.strftime('%Y-%m-%d %H:%M') if cr.implementation_deadline else 'N/A'}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Deadline Status:</td><td style="padding: 5px;">{deadline_status}</td></tr>
                    </table>
                </div>
                
                <div style="background: #fff; padding: 20px; border: 1px solid #dee2e6; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #495057;">📋 Complete Timeline</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        {timeline_html}
                    </table>
                </div>
                
                <div style="background: #d4edda; padding: 20px; border-left: 4px solid #28a745; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #155724;">👥 Stakeholders</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">Requester:</td><td style="padding: 5px;">{cr.requester.username} ({cr.requester.email})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Approver:</td><td style="padding: 5px;">{cr.approver.username if cr.approver else 'N/A'} ({cr.approver.email if cr.approver else 'N/A'})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Implementer:</td><td style="padding: 5px;">{cr.implementer.username if cr.implementer else 'N/A'} ({cr.implementer.email if cr.implementer else 'N/A'})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Closed By:</td><td style="padding: 5px;">{cr.closed_by.username if cr.closed_by else 'N/A'} ({cr.closed_by.email if cr.closed_by else 'N/A'})</td></tr>
                    </table>
                </div>
                
                {f'''
                <div style="background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">📝 Closure Notes</h3>
                    <p>{cr.closure_notes}</p>
                </div>
                ''' if cr.closure_notes else ''}
                
                <div style="margin: 30px 0;">
                    <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{cr.id}" 
                       style="background: #667eea; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Full Details
                    </a>
                </div>
                
                <p style="color: #666; font-size: 0.9em;">
                    This timeline has been automatically archived for record-keeping purposes as per CMSF-019.<br>
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </body>
            </html>
            """
            
            EmailService._send_email(
                admin.email,
                f"[CLOSED] CR Timeline: {cr.cr_number} - {cr.title}",
                html_content
            )

    @staticmethod
    def send_sla_warning_email(cr):
        """
        Send SLA warning email 24 hours before deadline (CMSF-016).
        Alerts all stakeholders of approaching deadline.
        """
        recipients = []
        if cr.implementer:
            recipients.append((cr.implementer.email, cr.implementer.username))
        if cr.approver:
            recipients.append((cr.approver.email, cr.approver.username))
        recipients.append((cr.requester.email, cr.requester.username))
        
        time_remaining = cr.time_until_deadline()
        hours_remaining = int(time_remaining.total_seconds() / 3600) if time_remaining else 0
        
        for email, username in set(recipients):
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #ff6b6b;">⚠️ SLA DEADLINE WARNING - 24 HOURS REMAINING</h2>
                <p>Dear {username},</p>
                <p><strong style="color: #dc3545;">URGENT:</strong> A change request is approaching its SLA deadline in approximately 24 hours.</p>
                
                <div style="background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">⏰ Deadline Information</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">CR Number:</td><td style="padding: 5px;">{cr.cr_number}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Title:</td><td style="padding: 5px;">{cr.title}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Project:</td><td style="padding: 5px;">{cr.project.name}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Current Status:</td><td style="padding: 5px;"><span style="color: #007bff; font-weight: bold;">{cr.status.value.upper()}</span></td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Deadline:</td><td style="padding: 5px; color: #dc3545; font-weight: bold;">{cr.implementation_deadline.strftime('%Y-%m-%d %H:%M')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Time Remaining:</td><td style="padding: 5px; color: #dc3545; font-weight: bold;">~{hours_remaining} hours</td></tr>
                    </table>
                </div>
                
                <div style="background: #f8d7da; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">🚨 Action Required</h3>
                    <ul style="margin: 10px 0;">
                        <li><strong>Implementer:</strong> Complete implementation immediately to avoid SLA breach</li>
                        <li><strong>Approver:</strong> Expedite review and closure process if already implemented</li>
                        <li><strong>Requester:</strong> Follow up with stakeholders if needed</li>
                    </ul>
                </div>
                
                <div style="margin: 30px 0;">
                    <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{cr.id}" 
                       style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View Change Request Immediately
                    </a>
                </div>
                
                <p style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px; font-weight: bold;">
                    ⏰ This is an automated SLA warning as per CMSF-016. Please take immediate action to prevent deadline breach.
                </p>
                
                <p style="color: #666; font-size: 0.9em;">This is an automated notification from the Change Management System.</p>
            </body>
            </html>
            """
            
            EmailService._send_email(
                email,
                f"[URGENT] SLA WARNING: {cr.cr_number} - 24 Hours to Deadline",
                html_content
            )

    @staticmethod
    def send_sla_breach_email(cr):
        """
        Send SLA breach notification to admin with rollback plan (CMSF-015).
        Alerts admin when deadline has passed without completion.
        """
        from app.models import User
        admins = User.query.filter(User.role.has(name='admin')).all()
        
        if not admins:
            current_app.logger.warning(f"No admins found to notify of SLA breach for CR {cr.cr_number}")
            return
        
        breach_time = datetime.now() - cr.implementation_deadline if cr.implementation_deadline else None
        hours_overdue = int(breach_time.total_seconds() / 3600) if breach_time else 0
        
        rollback_info = ""
        if cr.rollback_plan or cr.rollback_plan_file:
            rollback_info = f"""
            <div style="background: #d1ecf1; padding: 20px; border-left: 4px solid #17a2b8; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #0c5460;">🔄 Rollback Plan Available</h3>
                {f'<p><strong>Text Plan:</strong></p><pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; overflow-x: auto;">{cr.rollback_plan}</pre>' if cr.rollback_plan else ''}
                {f'<p><strong>File Plan:</strong> <a href="{current_app.config.get("BASE_URL", "http://127.0.0.1:5000")}/static/uploads/{cr.rollback_plan_file}" style="color: #17a2b8;">Download Rollback Plan</a></p>' if cr.rollback_plan_file else ''}
            </div>
            """
        
        for admin in admins:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #dc3545;">🚨 SLA BREACH ALERT - DEADLINE EXCEEDED</h2>
                <p>Dear {admin.username},</p>
                <p><strong style="color: #dc3545; font-size: 1.2em;">CRITICAL:</strong> A change request has breached its SLA deadline (CMSF-015).</p>
                
                <div style="background: #f8d7da; padding: 20px; border-left: 4px solid #dc3545; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #721c24;">⏰ Breach Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">CR Number:</td><td style="padding: 5px;">{cr.cr_number}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Title:</td><td style="padding: 5px;">{cr.title}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Project:</td><td style="padding: 5px;">{cr.project.name}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Priority:</td><td style="padding: 5px;"><span style="color: #dc3545; font-weight: bold;">{cr.priority.value.upper()}</span></td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Current Status:</td><td style="padding: 5px;"><span style="color: #ffc107; font-weight: bold;">{cr.status.value.upper()}</span></td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Deadline Was:</td><td style="padding: 5px; color: #dc3545;">{cr.implementation_deadline.strftime('%Y-%m-%d %H:%M')}</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Time Overdue:</td><td style="padding: 5px; color: #dc3545; font-weight: bold;">~{hours_overdue} hours</td></tr>
                    </table>
                </div>
                
                <div style="background: #fff3cd; padding: 20px; border-left: 4px solid #ffc107; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #856404;">👥 Responsible Parties</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 5px; font-weight: bold; width: 40%;">Requester:</td><td style="padding: 5px;">{cr.requester.username} ({cr.requester.email})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Approver:</td><td style="padding: 5px;">{cr.approver.username if cr.approver else 'Not assigned'} ({cr.approver.email if cr.approver else 'N/A'})</td></tr>
                        <tr><td style="padding: 5px; font-weight: bold;">Implementer:</td><td style="padding: 5px;">{cr.implementer.username if cr.implementer else 'Not assigned'} ({cr.implementer.email if cr.implementer else 'N/A'})</td></tr>
                    </table>
                </div>
                
                {rollback_info}
                
                <div style="background: #e2e3e5; padding: 20px; border-left: 4px solid #6c757d; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #383d41;">📋 Recommended Actions</h3>
                    <ol style="margin: 10px 0; padding-left: 20px;">
                        <li>Contact implementer immediately to determine status and completion ETA</li>
                        <li>Assess impact of delay on business operations</li>
                        <li>Consider executing rollback plan if critical issues arise</li>
                        <li>Document reasons for delay for future reference</li>
                        <li>Escalate to stakeholders if necessary</li>
                    </ol>
                </div>
                
                <div style="margin: 30px 0;">
                    <a href="{current_app.config.get('BASE_URL', 'http://127.0.0.1:5000')}/change-requests/{cr.id}" 
                       style="background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        View CR & Take Action
                    </a>
                </div>
                
                <p style="color: #721c24; background: #f8d7da; padding: 10px; border-radius: 5px; font-weight: bold;">
                    🚨 This is a critical SLA breach notification as per CMSF-015. Immediate administrative attention required.
                </p>
                
                <p style="color: #666; font-size: 0.9em;">
                    This is an automated notification from the Change Management System.<br>
                    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
            </body>
            </html>
            """
            
            EmailService._send_email(
                admin.email,
                f"[CRITICAL] SLA BREACH: {cr.cr_number} - Deadline Exceeded by {hours_overdue}h",
                html_content
            )


