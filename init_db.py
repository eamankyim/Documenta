#!/usr/bin/env python3
"""
Database initialization script for SPLITTER application.
This script will create the database and migrate existing data from JSON files.
"""

import os
import json
import uuid
from datetime import datetime
from app import app, db
from models import User, Project, Token, ResetToken
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize the database and create tables"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Migrate existing data if JSON files exist
        migrate_existing_data()

def migrate_existing_data():
    """Migrate existing data from JSON files to database"""
    print("Checking for existing data to migrate...")
    
    # Migrate users
    users_file = os.path.join('outputs', 'users.json')
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            for email, user_data in users_data.items():
                # Check if user already exists
                existing_user = User.query.filter_by(email=email).first()
                if not existing_user:
                    user = User(
                        email=email,
                        name=user_data.get('name', ''),
                        password_hash=user_data.get('password_hash', ''),
                        plan=user_data.get('plan', 'Free'),
                        created_at=datetime.fromisoformat(user_data.get('created_at', datetime.utcnow().isoformat())),
                        plan_updated_at=datetime.fromisoformat(user_data.get('plan_updated_at', datetime.utcnow().isoformat())) if user_data.get('plan_updated_at') else None
                    )
                    db.session.add(user)
                    print(f"Migrated user: {email}")
            
            db.session.commit()
            print("Users migration completed!")
        except Exception as e:
            print(f"Error migrating users: {e}")
    
    # Migrate projects from HTML files
    outputs_dir = 'outputs'
    if os.path.exists(outputs_dir):
        for filename in os.listdir(outputs_dir):
            if filename.endswith('_converted.html'):
                unique_id = filename.split('_')[0]
                
                # Check if project already exists
                existing_project = Project.query.filter_by(unique_id=unique_id).first()
                if not existing_project:
                    file_path = os.path.join(outputs_dir, filename)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Extract title
                        title = 'Untitled Document'
                        import re
                        title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            title = re.sub(r'\s+', ' ', title_match.group(1)).strip()
                        
                        if not title or title == 'Untitled Document':
                            h1_match = re.search(r'<h1[^>]*class=["\"][^"\"]*main-title[^"\"]*["\"][^>]*>(.*?)</h1>', content, re.IGNORECASE | re.DOTALL)
                            if h1_match:
                                title = re.sub(r'<[^>]+>', '', h1_match.group(1))
                                title = re.sub(r'\s+', ' ', title).strip()
                        
                        project = Project(
                            unique_id=unique_id,
                            filename=filename,
                            title=title or 'Untitled Document',
                            content=content,
                            size=len(content),
                            created_at=datetime.fromtimestamp(os.path.getctime(file_path)),
                            updated_at=datetime.fromtimestamp(os.path.getmtime(file_path))
                        )
                        db.session.add(project)
                        print(f"Migrated project: {unique_id}")
                    except Exception as e:
                        print(f"Error migrating project {unique_id}: {e}")
        
        db.session.commit()
        print("Projects migration completed!")
    
    # Migrate tokens
    tokens_file = os.path.join('outputs', 'tokens.json')
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                tokens_data = json.load(f)
            
            for unique_id, token_value in tokens_data.items():
                # Check if token already exists
                existing_token = Token.query.filter_by(unique_id=unique_id).first()
                if not existing_token:
                    token = Token(
                        unique_id=unique_id,
                        token=token_value
                    )
                    db.session.add(token)
                    print(f"Migrated token for project: {unique_id}")
            
            db.session.commit()
            print("Tokens migration completed!")
        except Exception as e:
            print(f"Error migrating tokens: {e}")
    
    # Migrate reset tokens
    reset_tokens_file = os.path.join('outputs', 'reset_tokens.json')
    if os.path.exists(reset_tokens_file):
        try:
            with open(reset_tokens_file, 'r', encoding='utf-8') as f:
                reset_tokens_data = json.load(f)
            
            for email, token_data in reset_tokens_data.items():
                # Check if reset token already exists
                existing_reset_token = ResetToken.query.filter_by(email=email, token=token_data['token']).first()
                if not existing_reset_token:
                    reset_token = ResetToken(
                        email=email,
                        token=token_data['token'],
                        expires=datetime.fromisoformat(token_data['expires'])
                    )
                    db.session.add(reset_token)
                    print(f"Migrated reset token for: {email}")
            
            db.session.commit()
            print("Reset tokens migration completed!")
        except Exception as e:
            print(f"Error migrating reset tokens: {e}")

if __name__ == '__main__':
    init_database()
    print("Database initialization completed!")
