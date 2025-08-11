#!/usr/bin/env python3
"""
Render deployment database setup script.
This script initializes the database when deploying to Render.
"""

import os
from app import app, db

def init_database():
    """Initialize the database and create tables"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully on Render!")

if __name__ == '__main__':
    init_database()
    print("Render database setup completed!")
