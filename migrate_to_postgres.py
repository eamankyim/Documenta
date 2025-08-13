#!/usr/bin/env python3
"""
Migration script to move from file-based storage to PostgreSQL database.
This script will migrate existing data from JSON files to the PostgreSQL database.
"""

import os
import json
import uuid
from datetime import datetime
from app_simple import app
from models import init_db, User, Project, Token, ResetToken
from werkzeug.security import generate_password_hash

def migrate_to_postgres():
    """Migrate all existing data to PostgreSQL database"""
    print("Starting migration to PostgreSQL...")
    
    # Initialize database
    db = init_db(app)
    
    with app.app_context():
        # Migrate users
        migrate_users()
        
        # Migrate projects
        migrate_projects()
        
        # Migrate tokens
        migrate_tokens()
        
        # Migrate reset tokens
        migrate_reset_tokens()
        
        print("Migration to PostgreSQL completed successfully!")

def migrate_users():
    """Migrate users from JSON files to database"""
    print("Migrating users...")
    
    users_file = os.path.join('outputs', 'users.json')
    if os.path.exists(users_file):
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users_data = json.load(f)
            
            migrated_count = 0
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
                    migrated_count += 1
            
            db.session.commit()
            print(f"Successfully migrated {migrated_count} users!")
        except Exception as e:
            print(f"Error migrating users: {e}")
            db.session.rollback()
    else:
        print("No users.json file found to migrate.")

def migrate_projects():
    """Migrate projects from HTML files to database"""
    print("Migrating projects...")
    
    outputs_dir = 'outputs'
    if os.path.exists(outputs_dir):
        migrated_count = 0
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
                        migrated_count += 1
                    except Exception as e:
                        print(f"Error migrating project {unique_id}: {e}")
        
        try:
            db.session.commit()
            print(f"Successfully migrated {migrated_count} projects!")
        except Exception as e:
            print(f"Error committing projects: {e}")
            db.session.rollback()
    else:
        print("No outputs directory found to migrate projects.")

def migrate_tokens():
    """Migrate tokens from JSON files to database"""
    print("Migrating tokens...")
    
    tokens_file = os.path.join('outputs', 'tokens.json')
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                tokens_data = json.load(f)
            
            migrated_count = 0
            for unique_id, token_value in tokens_data.items():
                # Check if token already exists
                existing_token = Token.query.filter_by(unique_id=unique_id).first()
                if not existing_token:
                    token = Token(
                        unique_id=unique_id,
                        token=token_value
                    )
                    db.session.add(token)
                    migrated_count += 1
            
            db.session.commit()
            print(f"Successfully migrated {migrated_count} tokens!")
        except Exception as e:
            print(f"Error migrating tokens: {e}")
            db.session.rollback()
    else:
        print("No tokens.json file found to migrate.")

def migrate_reset_tokens():
    """Migrate reset tokens from JSON files to database"""
    print("Migrating reset tokens...")
    
    reset_tokens_file = os.path.join('outputs', 'reset_tokens.json')
    if os.path.exists(reset_tokens_file):
        try:
            with open(reset_tokens_file, 'r', encoding='utf-8') as f:
                reset_tokens_data = json.load(f)
            
            migrated_count = 0
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
                    migrated_count += 1
            
            db.session.commit()
            print(f"Successfully migrated {migrated_count} reset tokens!")
        except Exception as e:
            print(f"Error migrating reset tokens: {e}")
            db.session.rollback()
    else:
        print("No reset_tokens.json file found to migrate.")

if __name__ == '__main__':
    migrate_to_postgres()
