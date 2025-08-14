#!/usr/bin/env python3
"""
Test script to verify Render deployment setup.
Run this locally to check if your app can start without errors.
"""

import os
import sys

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from flask import Flask
        print("✅ Flask imported successfully")
    except ImportError as e:
        print(f"❌ Flask import failed: {e}")
        return False
    
    try:
        from flask_sqlalchemy import SQLAlchemy
        print("✅ Flask-SQLAlchemy imported successfully")
    except ImportError as e:
        print(f"❌ Flask-SQLAlchemy import failed: {e}")
        return False
    
    try:
        from datetime import datetime, timezone
        print("✅ datetime imported successfully")
    except ImportError as e:
        print(f"❌ datetime import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        # Set environment variable for testing
        os.environ['DATABASE_URL'] = 'postgresql://splitter_user:Sb74paNPJ8M5FpopNYwVSJQvVwLcJBev@dpg-d2e6aobe5dus73fjrtc0-a.oregon-postgres.render.com/splitter_db'
        
        from app import app, db
        
        with app.app_context():
            # Test database connection
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("✅ Database connection successful")
            
            # Check if tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✅ Found tables: {tables}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_app_startup():
    """Test if the app can start without errors"""
    print("\n🔍 Testing app startup...")
    
    try:
        from app import app
        
        # Test basic app functionality
        with app.test_client() as client:
            response = client.get('/health')
            if response.status_code == 200:
                print("✅ Health endpoint working")
                print(f"   Response: {response.get_json()}")
            else:
                print(f"⚠️  Health endpoint returned status: {response.status_code}")
        
        print("✅ App startup successful")
        return True
        
    except Exception as e:
        print(f"❌ App startup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Render Deployment Setup")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Check your requirements.txt")
        return False
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection failed. Check your DATABASE_URL")
        return False
    
    # Test app startup
    if not test_app_startup():
        print("\n❌ App startup failed. Check your Flask app configuration")
        return False
    
    print("\n🎉 All tests passed! Your app should deploy successfully on Render.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
