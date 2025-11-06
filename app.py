"""
Main application entry point
Run with TLS 1.2+ enforcement in production
"""
import os
from dotenv import load_dotenv
from app import create_app, create_ssl_context

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == '__main__':
    # Get environment
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        # Run with TLS in production (CMS-SR-001)
        ssl_context = create_ssl_context(app)
        app.run(
            host='0.0.0.0',
            port=443,
            ssl_context=ssl_context,
            debug=False
        )
    else:
        # Development mode
        app.run(
            host='127.0.0.1',
            port=5000,
            debug=True
        )