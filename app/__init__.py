from flask import Flask, redirect, request, render_template
from .config import config_by_name
from .extensions import db, migrate, login_manager, csrf, limiter
import ssl
import os
from datetime import datetime, timezone, timedelta


def create_app(config_name=None):
    config_name = config_name or os.environ.get('FLASK_ENV', 'development')
    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(config_by_name[config_name])
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max upload

    # initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.session_protection = 'strong'  # Enhanced session protection
    login_manager.refresh_view = 'auth.login'
    csrf.init_app(app)
    limiter.init_app(app)

    # Custom Jinja filter for IST timezone conversion
    @app.template_filter('to_ist')
    def to_ist_filter(dt):
        """Convert UTC datetime to IST (Indian Standard Time - UTC+5:30)"""
        if dt is None:
            return 'N/A'
        # If datetime is naive, assume it's UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to IST (UTC + 5:30)
        ist = dt.astimezone(timezone(timedelta(hours=5, minutes=30)))
        return ist.strftime('%Y-%m-%d %H:%M:%S IST')

    # register blueprints (deferred imports to avoid circulars)
    from .auth.routes import auth_bp
    from .change_requests.routes import cr_bp
    from .audit.routes import audit_bp
    from .api import api_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(cr_bp, url_prefix="/change-requests")
    app.register_blueprint(audit_bp, url_prefix="/audit")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # Root route - show home page
    @app.route('/')
    def index():
        return render_template('home.html')
    
    # About page
    @app.route('/about')
    def about():
        return render_template('about.html')
    
    # Health check endpoint for Docker/Heroku
    @app.route('/health')
    def health():
        """Health check endpoint for container orchestration"""
        try:
            # Check database connection
            db.session.execute(db.text('SELECT 1'))
            return {'status': 'healthy', 'database': 'connected'}, 200
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 503

    # Enforce TLS in production-like configs
    @app.before_request
    def enforce_tls():
        if app.config.get("ENFORCE_HTTPS") and not request.is_secure:
            url = request.url.replace("http://", "https://", 1)
            return redirect(url, code=301)

    # Initialize SLA monitoring (CMSF-015, CMSF-016)
    if not app.config.get('TESTING', False):
        from app.services.sla_monitor import start_sla_monitoring
        start_sla_monitoring(app)
        app.logger.info("SLA monitoring initialized")

    return app


def create_ssl_context(app):
    """
    Create SSL context for TLS 1.2+ enforcement
    CMS-SR-001: TLS 1.2+ required
    """
    cert_file = app.config.get('SSL_CERT_FILE', 'cert.pem')
    key_file = app.config.get('SSL_KEY_FILE', 'key.pem')
    
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        app.logger.warning('SSL certificate files not found. Using adhoc SSL.')
        return 'adhoc'
    
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2  # Enforce TLS 1.2+
    context.load_cert_chain(cert_file, key_file)
    
    return context

