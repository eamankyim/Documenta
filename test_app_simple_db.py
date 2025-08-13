#!/usr/bin/env python3
"""
Test script for app_simple.py database integration.
This script will test the database connection and basic operations.
"""

import os
import sys
from app_simple import app
from models import db, User, Project, Token, ResetToken

def test_app_simple_database():
    """Test database connection and basic operations with app_simple.py"""
    print("Testing app_simple.py database integration...")
    
    try:
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
            
            print("\n🎉 All app_simple.py database tests passed successfully!")
            print("Your PostgreSQL setup is working correctly with app_simple.py!")
            
            return True
            
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == '__main__':
    success = test_app_simple_database()
    sys.exit(0 if success else 1)
