#!/usr/bin/env python3
"""
Database setup script for Render deployment.
This script will create the database tables and handle any initial setup needed.
"""

import os
import sys
from flask import Flask
from models import init_db

def create_app():
    """Create a minimal Flask app for database operations"""
    app = Flask(__name__)
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        sys.exit(1)
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
    
    return app

def setup_database():
    """Set up the database tables"""
    print("Setting up database for Render deployment...")
    
    try:
        # Create the Flask app
        app = create_app()
        
        # Initialize database
        db = init_db(app)
        
        print("Database setup completed successfully!")
        print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
        
        # Test database connection
        with app.app_context():
            # Try to query the database to test connection
            from models import User
            user_count = User.query.count()
            print(f"Database connection test successful! Found {user_count} users.")
            
    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)

if __name__ == '__main__':
    setup_database()
