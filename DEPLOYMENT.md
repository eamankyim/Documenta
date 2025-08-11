# SPLITTER Deployment Guide for Render

## Overview
This guide explains how to deploy the SPLITTER application to Render with persistent storage to solve the data loss issue.

## Problem Solved
- **Before**: Projects and user data were stored in local files (`outputs/` folder) which were lost on server restarts
- **After**: Data is now stored persistently using either database storage or improved file storage

## Two Solutions Available

### Solution 1: Database Storage (Recommended for Production)
Uses SQLAlchemy with:
- **Local Development**: SQLite database (`splitter.db`)
- **Render Production**: PostgreSQL database (provided by Render)

### Solution 2: Improved File Storage (Simpler, Works on Any Python Version)
Enhanced file-based storage with better persistence and error handling.

## Quick Fix for Python 3.13 Compatibility Issues

If you encounter SQLAlchemy compatibility errors on Render, use the simplified version:

**Files to use:**
- `app_simple.py` (instead of `app.py`)
- `requirements-simple.txt` (instead of `requirements.txt`)

**Render Configuration:**
- **Build Command:** `pip install -r requirements-simple.txt`
- **Start Command:** `python app_simple.py`

## Solution 1: Database Deployment (Advanced)

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

## Solution 2: Simplified File Storage (Recommended for Quick Fix)

### 1. Render Configuration
**Build Command:**
```bash
pip install -r requirements-simple.txt
```

**Start Command:**
```bash
python app_simple.py
```

### 2. Benefits of Simplified Solution
- ✅ **No Python version compatibility issues**
- ✅ **Works on Python 3.13+**
- ✅ **Improved file persistence**
- ✅ **Better error handling**
- ✅ **Faster deployment**

## Data Persistence Features

Both solutions provide:
- ✅ User accounts and authentication
- ✅ Project content and metadata
- ✅ Access tokens
- ✅ Data survives server restarts

## Local Development

### With Database (Solution 1):
1. Install dependencies: `pip install -r requirements.txt`
2. Initialize database: `python init_db.py`
3. Run: `python app.py`

### With Simplified Storage (Solution 2):
1. Install dependencies: `pip install -r requirements-simple.txt`
2. Run: `python app_simple.py`

## Migration from File Storage

If you have existing data:
- **Solution 1**: Run `python init_db.py` to migrate to database
- **Solution 2**: Your existing files will work automatically

## Troubleshooting

### Python 3.13 Compatibility Issues
- **Error**: `AssertionError: Class directly inherits TypingOnly`
- **Solution**: Use `app_simple.py` and `requirements-simple.txt`

### Database Connection Issues
- Verify `DATABASE_URL` environment variable
- Check PostgreSQL service status
- Ensure database credentials are correct

### File Storage Issues
- Check file permissions
- Verify `outputs/` directory exists
- Check console output for specific error messages

## File Structure

```
SPLITTER/
├── app.py                 # Database version (may have Python 3.13 issues)
├── app_simple.py          # Simplified version (Python 3.13 compatible)
├── models.py              # Database models (for Solution 1)
├── requirements.txt       # Database dependencies
├── requirements-simple.txt # Simple dependencies
├── init_db.py            # Database setup (for Solution 1)
├── build.sh              # Render build script
└── DEPLOYMENT.md         # This file
```

## Recommendation

**For immediate deployment on Render:**
1. Use `app_simple.py` and `requirements-simple.txt`
2. This avoids Python 3.13 compatibility issues
3. Provides improved file persistence
4. Faster deployment and testing

**For production with database:**
1. Use `app.py` and `requirements.txt`
2. Specify Python 3.11 in `runtime.txt`
3. Provides full database features
4. Better scalability and performance

## Support
If you encounter issues:
1. Check Render logs for error messages
2. Try the simplified solution first
3. Verify environment variables are set
4. Check Python version compatibility

Your projects will now persist across deployments and server restarts! 🎉
