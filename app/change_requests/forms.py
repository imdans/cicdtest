"""
Change Request forms
Implements CMS-F-005, CMS-F-006, CMS-F-007, CMS-F-017, CMS-F-019
"""
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, DateTimeField, SubmitField, MultipleFileField
from wtforms.validators import DataRequired, Length, Optional


class ChangeRequestForm(FlaskForm):
    """
    Change Request creation/edit form
    Implements CMS-F-005, CMS-F-007
    """
    title = StringField('Title', validators=[
        DataRequired(),
        Length(min=10, max=256, message='Title must be between 10 and 256 characters')
    ])
    
    description = TextAreaField('Description', validators=[
        DataRequired(),
        Length(min=20, message='Description must be at least 20 characters')
    ])
    
    justification = TextAreaField('Justification', validators=[
        Optional()
    ])
    
    impact_assessment = TextAreaField('Impact Assessment', validators=[
        Optional()
    ])
    
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], validators=[DataRequired()])
    
    risk_level = SelectField('Risk Level', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ], validators=[DataRequired()])
    
    # CMSF-015: Implementation deadline for SLA tracking
    implementation_deadline = DateTimeField('Implementation Deadline (for SLA tracking)', 
                                           format='%Y-%m-%dT%H:%M',
                                           validators=[Optional()])
    
    # CMSF-017: Rollback plan (text)
    rollback_plan = TextAreaField('Rollback Plan (Required for High-Risk Changes)', 
                                  validators=[Optional()])
    
    # CMSF-017: Rollback plan file attachment
    rollback_plan_file = FileField('Rollback Plan Document', validators=[
        FileAllowed(['txt', 'pdf', 'doc', 'docx'], 'Only document files allowed')
    ])
    
    # CMS-F-006: Attach supporting documents
    attachments = MultipleFileField('Attachments', validators=[
        FileAllowed(['txt', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg'],
                   'Only documents and images allowed')
    ])
    
    submit = SubmitField('Save as Draft')
    submit_for_approval = SubmitField('Submit for Approval')


class ApprovalForm(FlaskForm):
    """Form for approving/rejecting CRs"""
    comments = TextAreaField('Comments', validators=[Optional()])
    approve = SubmitField('Approve')
    reject = SubmitField('Reject')


class RollbackForm(FlaskForm):
    """Form for rolling back CRs (CMSF-018)"""
    reason = TextAreaField('Rollback Reason', validators=[
        DataRequired(),
        Length(min=20, message='Reason must be at least 20 characters')
    ])
    submit = SubmitField('Rollback Change')


class ClosureForm(FlaskForm):
    """Form for closing CRs (CMSF-019)"""
    closure_notes = TextAreaField('Closure Notes', validators=[
        DataRequired(),
        Length(min=20, message='Closure notes must be at least 20 characters')
    ])
    comments = TextAreaField('Additional Comments', validators=[Optional()])
    submit = SubmitField('Close Change Request')
