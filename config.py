import os
from datetime import timedelta

def transform_database_url(url):
    """Transform postgresql:// URLs to use psycopg3 instead of psycopg2"""
    if url and url.startswith('postgresql://'):
        # Replace postgresql:// with postgresql+psycopg:// to force psycopg3
        return url.replace('postgresql://', 'postgresql+psycopg://', 1)
    return url

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-me-in-production')
    UPLOAD_FOLDER = 'uploads'
    OUTPUT_FOLDER = 'outputs'
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    
    # Database configuration - transform URL to use psycopg3
    SQLALCHEMY_DATABASE_URI = transform_database_url(os.environ.get('DATABASE_URL'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # File upload settings
    ALLOWED_EXTENSIONS = {'pdf'}
    CONVERSION_ENABLED = False  # Disable PDF extraction/conversion; use as formatting tool only

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # Use SQLite for local development if no DATABASE_URL is set
    SQLALCHEMY_DATABASE_URI = transform_database_url(os.environ.get('DATABASE_URL')) or 'sqlite:///dev.db'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Ensure DATABASE_URL is set in production and transform it
    SQLALCHEMY_DATABASE_URI = transform_database_url(os.environ.get('DATABASE_URL'))
    
    def __init__(self):
        # Don't crash the app - just log a warning
        if not self.SQLALCHEMY_DATABASE_URI:
            print("WARNING: DATABASE_URL environment variable not set in production!")
            print("Falling back to development database configuration...")
            # Fall back to development config instead of crashing
            self.SQLALCHEMY_DATABASE_URI = 'sqlite:///prod_fallback.db'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
