#!/usr/bin/env python3
"""
Startup script for Render deployment.
This ensures proper database initialization and handles startup errors gracefully.
"""

import os
import time
import sys
from app import app, db

def wait_for_database(max_attempts=30, delay=2):
    """Wait for database to be available"""
    print("Waiting for database connection...")
    
    for attempt in range(max_attempts):
        try:
            with app.app_context():
                db.session.execute('SELECT 1')
                print("Database connection successful!")
                return True
        except Exception as e:
            print(f"Database connection attempt {attempt + 1}/{max_attempts} failed: {e}")
            if attempt < max_attempts - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print("Max database connection attempts reached. Starting app anyway...")
                return False
    
    return False

def initialize_database():
    """Initialize database tables if needed"""
    try:
        with app.app_context():
            # Check if tables exist
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                print("Creating database tables...")
                db.create_all()
                print("Database tables created successfully!")
            else:
                print(f"Database tables already exist: {existing_tables}")
                
    except Exception as e:
        print(f"Database initialization warning: {e}")
        print("Continuing with app startup...")

if __name__ == "__main__":
    print("=" * 50)
    print("STARTING DOCUMENTA APPLICATION")
    print("=" * 50)
    
    # Wait for database
    db_ready = wait_for_database()
    
    # Initialize database
    if db_ready:
        initialize_database()
    
    print("Application startup completed!")
    print("=" * 50)
