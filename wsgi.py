#!/usr/bin/env python3
"""
WSGI entry point for Render deployment.
This file is used by Render to start the Flask application.
"""

import os
import sys
from app import app

# Ensure the app context is available
app.app_context().push()

if __name__ == "__main__":
    # Get port from environment variable (Render sets this)
    port = int(os.environ.get("PORT", 5000))
    
    # For development only - use Gunicorn in production
    if os.environ.get('FLASK_ENV') == 'development':
        app.run(host="0.0.0.0", port=port, debug=False)
    else:
        # Production mode - this should not be reached on Render
        # Render will use the startCommand: gunicorn wsgi:app
        print("Production mode - use Gunicorn to start the application")
        sys.exit(1)

