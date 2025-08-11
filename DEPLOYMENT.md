# SPLITTER Deployment Guide for Render

## Overview
This guide explains how to deploy the SPLITTER application to Render with persistent database storage to solve the data loss issue.

## Problem Solved
- **Before**: Projects and user data were stored in local files (`outputs/` folder) which were lost on server restarts
- **After**: All data is now stored in a persistent database (SQLite for local dev, PostgreSQL for Render)

## Database Migration
The application now uses SQLAlchemy with:
- **Local Development**: SQLite database (`splitter.db`)
- **Render Production**: PostgreSQL database (provided by Render)

## Deployment Steps

### 1. Render Configuration
In your Render dashboard, configure:

**Environment Variables:**
```
SECRET_KEY=your-secure-secret-key-here
DATABASE_URL=postgresql://username:password@host:port/database
```

**Build Command:**
```bash
chmod +x build.sh && ./build.sh
```

**Start Command:**
```bash
python app.py
```

### 2. Database Setup
The build script automatically:
- Installs all dependencies
- Creates database tables
- Sets up the schema

### 3. Data Persistence
All data is now stored in the database:
- ✅ User accounts and authentication
- ✅ Project content and metadata
- ✅ Access tokens
- ✅ Password reset tokens

## Local Development
To run locally with the new database:

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Initialize database:
```bash
python init_db.py
```

3. Run the application:
```bash
python app.py
```

## Migration from File Storage
If you have existing data in JSON files and HTML files, run:
```bash
python init_db.py
```

This will migrate:
- Users from `outputs/users.json`
- Projects from HTML files in `outputs/`
- Tokens from `outputs/tokens.json`
- Reset tokens from `outputs/reset_tokens.json`

## Benefits of Database Storage
- **Persistent**: Data survives server restarts and deployments
- **Scalable**: Can handle multiple users and projects efficiently
- **Reliable**: ACID compliance and data integrity
- **Backup-friendly**: Easy to backup and restore

## Troubleshooting

### Database Connection Issues
- Verify `DATABASE_URL` environment variable is set correctly
- Check that PostgreSQL service is running on Render
- Ensure database credentials are correct

### Migration Issues
- Check that all required files exist before migration
- Verify file permissions for reading JSON and HTML files
- Check console output for specific error messages

### Performance Issues
- Database queries are optimized with proper indexing
- Consider adding database connection pooling for high traffic
- Monitor database performance in Render dashboard

## File Structure Changes
```
SPLITTER/
├── app.py                 # Main application (updated for database)
├── models.py             # Database models (NEW)
├── init_db.py            # Local database setup (NEW)
├── render_setup.py       # Render database setup (NEW)
├── build.sh              # Render build script (NEW)
├── render-requirements.txt # Render dependencies (NEW)
├── requirements.txt      # Local dependencies (updated)
└── DEPLOYMENT.md         # This file (NEW)
```

## Support
If you encounter issues:
1. Check the Render logs for error messages
2. Verify all environment variables are set
3. Ensure the build script runs successfully
4. Check that the database tables are created

The application will now maintain all your projects and user data across deployments and server restarts!
