# User Guide

Welcome to the Change Management System (CMS). This guide will help you use the system effectively.

## Getting Started

### First Login

1. Navigate to the login page at `/auth/login`
2. Enter your username and password
3. If you're an administrator with MFA enabled, you'll be prompted for a 6-digit code

**Default Admin Credentials (Development):**
- Username: `admin`
- Password: `Admin@123`
- ⚠️ Change this immediately after first login!

### User Roles

The system has four main roles:

1. **Requester** - Can submit and track their own change requests
2. **Approver** - Can review and approve/reject change requests
3. **Implementer** - Can implement approved changes
4. **Admin** - Full system access with user management capabilities

## Managing Change Requests

### Creating a Change Request

1. Navigate to "Change Requests" → "Create New"
2. Fill in the required fields:
   - **Title**: Brief description (10-256 characters)
   - **Description**: Detailed explanation (minimum 20 characters)
   - **Justification**: Why this change is needed
   - **Impact Assessment**: Expected impact on systems/users
   - **Priority**: Low, Medium, High, or Critical
   - **Risk Level**: Low, Medium, or High
   - **Rollback Plan**: Required for high-risk changes
3. Attach supporting documents (optional)
4. Choose to:
   - **Save as Draft**: Keep working on it later
   - **Submit for Approval**: Send to approvers

### Editing a Change Request

- Draft CRs can be edited by the requester
- Once submitted, only admins can edit
- Navigate to the CR and click "Edit"

### Viewing Change Requests

- **List View**: See all your CRs or all CRs (if you have permission)
- **Filter**: By status, priority, or date range
- **Details**: Click on a CR number to see full details

### Change Request Lifecycle

```
Draft → Submitted → Pending Approval → Approved → In Progress → Implemented → Closed
                                    ↓
                                Rejected
```

## For Approvers

### Reviewing Change Requests

1. Navigate to "Change Requests"
2. Filter by status "Pending Approval"
3. Click on a CR to review details
4. Click "Approve" or "Reject"
5. Add comments explaining your decision

### Approval Criteria

Consider:
- Business justification
- Risk assessment
- Impact on systems and users
- Rollback plan adequacy
- Resource availability

## For Implementers

### Implementing Changes

1. View approved CRs
2. Click "Start Implementation"
3. Follow the implementation plan
4. Update status as you progress
5. Mark as "Implemented" when complete

### Rollback Procedure

If issues occur:
1. Navigate to the CR
2. Click "Rollback"
3. Provide detailed reason
4. Follow the rollback plan

## Audit Logs

Administrators can view system audit logs:

1. Navigate to "Audit" → "View Logs"
2. Filter by:
   - Event type
   - Date range
   - Username
3. Export logs to CSV for compliance

## Security Best Practices

### Password Requirements
- Minimum 8 characters
- Include uppercase, lowercase, numbers, and special characters
- Change regularly
- Don't share passwords

### Multi-Factor Authentication (MFA)
- All administrators must enable MFA
- Use an authenticator app (Google Authenticator, Authy, etc.)
- Keep backup codes secure

### Session Security
- Log out when finished
- Don't leave sessions unattended
- Clear browser cache on shared computers

## Getting Help

If you encounter issues:

1. Check this user guide
2. Contact your system administrator
3. Review audit logs (if you have permission)
4. Report security issues immediately

## Keyboard Shortcuts

- `Ctrl+S` - Save draft (when editing)
- `Esc` - Cancel/Close modal
- `Tab` - Navigate form fields

## Mobile Access

The system is responsive and works on mobile devices, though desktop is recommended for complex operations.

