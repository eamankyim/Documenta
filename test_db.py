#!/usr/bin/env python3
"""
Database test script to verify PostgreSQL connection and operations.
Run this script to test if your database setup is working correctly.
"""

import os
import sys
from flask import Flask
from models import db, User, Project, Token, ResetToken

def transform_database_url(url):
    """Transform postgresql:// URLs to use psycopg3 instead of psycopg2"""
    if url and url.startswith('postgresql://'):
        # Replace postgresql:// with postgresql+psycopg:// to force psycopg3
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

def test_database():
    """Test the database connection and basic operations"""
    print("🧪 Testing PostgreSQL database connection and operations...")
    print("=" * 60)
    
    # Create a minimal Flask app
    app = Flask(__name__)
    
    # Get database URL from environment and transform it
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set!")
        print("Please set DATABASE_URL to your PostgreSQL connection string.")
        return False
    
    # Transform URL to use psycopg3
    transformed_url = transform_database_url(database_url)
    print(f"Original DATABASE_URL: {database_url}")
    print(f"Transformed to use psycopg3: {transformed_url}")
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = transformed_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    try:
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Test 1: Create tables
            print("✓ Creating database tables...")
            db.create_all()
            print("✓ Tables created successfully!")
            
            # Test 2: Test basic operations
            print("✓ Testing basic database operations...")
            
            # Create a test user
            test_user = User(
                email='test@example.com',
                name='Test User',
                plan='Free'
            )
            test_user.set_password('testpassword123')
            
            db.session.add(test_user)
            db.session.commit()
            print("✓ Test user created successfully!")
            
            # Query the user
            user = User.query.filter_by(email='test@example.com').first()
            if user and user.check_password('testpassword123'):
                print("✓ User authentication working!")
            else:
                print("✗ User authentication failed!")
                return False
            
            # Test 3: Create a test project
            print("✓ Testing project creation...")
            test_project = Project(
                unique_id='test-project-123',
                filename='test.html',
                title='Test Project',
                content='<html><body><h1>Test Content</h1></body></html>',
                size=50,
                user_id=user.id
            )
            
            db.session.add(test_project)
            db.session.commit()
            print("✓ Test project created successfully!")
            
            # Test 4: Query projects
            projects = Project.query.filter_by(user_id=user.id).all()
            if len(projects) == 1:
                print("✓ Project query working!")
            else:
                print("✗ Project query failed!")
                return False
            
            # Test 5: Test token operations
            print("✓ Testing token operations...")
            test_token = Token(
                unique_id='test-project-123',
                token='test-token-456'
            )
            
            db.session.add(test_token)
            db.session.commit()
            print("✓ Test token created successfully!")
            
            # Test 6: Clean up test data
            print("✓ Cleaning up test data...")
            db.session.delete(test_token)
            db.session.delete(test_project)
            db.session.delete(test_user)
            db.session.commit()
            print("✓ Test data cleaned up successfully!")
            
            print("\n🎉 All database tests passed successfully!")
            print(f"Database URL: {database_url}")
            print("Your PostgreSQL setup is working correctly!")
            
            return True
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == '__main__':
    success = test_database()
    sys.exit(0 if success else 1)
