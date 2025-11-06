"""
SLA Monitoring Service
Implements CMSF-015 and CMSF-016
Background task to monitor implementation deadlines and send alerts
"""
from datetime import datetime, timedelta
from flask import current_app
from app.models import ChangeRequest, CRStatus
from app.services.email_service import EmailService
from app.extensions import db


def check_sla_deadlines():
    """
    Check all active CRs for SLA deadline warnings and breaches.
    Called periodically by scheduler (every hour recommended).
    
    CMSF-016: Send warning 24 hours before deadline
    CMSF-015: Notify admin on breach with rollback plan
    """
    with current_app.app_context():
        try:
            from datetime import timezone
            current_time = datetime.now(timezone.utc)
            
            # Get all CRs that are not yet closed or rolled back
            active_statuses = [CRStatus.APPROVED, CRStatus.IN_PROGRESS, CRStatus.IMPLEMENTED]
            active_crs = ChangeRequest.query.filter(
                ChangeRequest.status.in_(active_statuses),
                ChangeRequest.implementation_deadline.isnot(None)
            ).all()
            
            for cr in active_crs:
                # Skip if already implemented and closed
                if cr.status == CRStatus.CLOSED:
                    continue
                
                # Check for deadline breach (CMSF-015)
                if cr.check_sla_breach():
                    current_app.logger.warning(f"SLA BREACH detected for CR {cr.cr_number}")
                    
                    # Send breach notification to admin (only once)
                    if not cr.sla_warning_sent:  # Reuse flag to prevent duplicate breach emails
                        email_service = EmailService()
                        email_service.send_sla_breach_email(cr)
                        cr.sla_warning_sent = True
                        db.session.commit()
                        current_app.logger.info(f"SLA breach email sent for CR {cr.cr_number}")
                
                # Check for 24-hour warning (CMSF-016)
                elif cr.is_deadline_warning_needed() and not cr.sla_warning_sent:
                    time_remaining = cr.time_until_deadline()
                    if time_remaining:
                        hours_remaining = time_remaining.total_seconds() / 3600
                        
                        # Send warning if less than 24 hours remaining (considering hourly check)
                        # This catches any time from 0 to 24 hours
                        if 0 < hours_remaining <= 24:
                            current_app.logger.warning(
                                f"SLA WARNING: CR {cr.cr_number} has {hours_remaining:.1f} hours until deadline"
                            )
                            
                            email_service = EmailService()
                            email_service.send_sla_warning_email(cr)
                            cr.sla_warning_sent = True
                            db.session.commit()
                            current_app.logger.info(f"SLA warning email sent for CR {cr.cr_number}")
            
            current_app.logger.info(f"SLA check completed. Checked {len(active_crs)} active CRs.")
            
        except Exception as e:
            current_app.logger.error(f"Error in SLA monitoring task: {str(e)}")
            db.session.rollback()


def start_sla_monitoring(app):
    """
    Initialize and start the SLA monitoring background task.
    Uses APScheduler to run checks periodically.
    
    Args:
        app: Flask application instance
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        
        scheduler = BackgroundScheduler()
        
        # Schedule SLA checks every 10 minutes for more responsive warnings
        scheduler.add_job(
            func=lambda: check_sla_deadlines(),
            trigger=IntervalTrigger(minutes=10),
            id='sla_monitoring',
            name='Check SLA deadlines for all CRs',
            replace_existing=True
        )
        
        scheduler.start()
        app.logger.info("SLA monitoring scheduler started successfully (checks every 10 minutes)")
        
        # Store scheduler in app for cleanup on shutdown
        app.sla_scheduler = scheduler
        
        # Register shutdown handler
        import atexit
        atexit.register(lambda: scheduler.shutdown())
        
        return scheduler
        
    except ImportError:
        app.logger.warning(
            "APScheduler not installed. SLA monitoring disabled. "
            "Install with: pip install apscheduler"
        )
        return None
    except Exception as e:
        app.logger.error(f"Failed to start SLA monitoring: {str(e)}")
        return None


def check_sla_now():
    """
    Manually trigger an immediate SLA check.
    Useful for testing or on-demand checks.
    """
    check_sla_deadlines()
