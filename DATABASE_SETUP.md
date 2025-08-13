# Database Setup Guide for SPLITTER

This guide will walk you through setting up PostgreSQL on Render and configuring your SPLITTER application to use it.

## Prerequisites

- A Render account
- Your SPLITTER application code
- Basic understanding of environment variables

## Step 1: Create PostgreSQL Database on Render

1. **Log into Render Dashboard**
   - Go to [render.com](https://render.com) and sign in

2. **Create New PostgreSQL Service**
   - Click "New +" button
   - Select "PostgreSQL" from the services list
   - Choose your plan (Free tier available for development)

3. **Configure Database**
   - **Name**: `splitter-db` (or your preferred name)
   - **Database**: `splitter_db`
   - **User**: `splitter_user` (or your preferred username)
   - **Region**: Choose closest to your users
   - **PostgreSQL Version**: Latest stable (15 or 16)

4. **Create Database**
   - Click "Create PostgreSQL Database"
   - Wait for the database to be provisioned (usually 2-3 minutes)

## Step 2: Get Database Connection Details

1. **Copy Connection String**
   - Once created, click on your database service
   - Go to "Connections" tab
   - Copy the "External Database URL"

2. **Format**: The URL will look like:
   ```
   postgresql://username:password@host:port/database
   ```

## Step 3: Configure Your Application

### Option A: Local Development

1. **Create `.env` file** (copy from `env.example`):
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file**:
   ```env
   FLASK_ENV=development
   FLASK_DEBUG=1
   SECRET_KEY=your-secret-key-here
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database setup**:
   ```bash
   python setup_database.py
   ```

5. **Run migration** (if you have existing data):
   ```bash
   python migrate_to_postgres.py
   ```

### Option B: Render Deployment

1. **Set Environment Variables** in your Render service:
   - Go to your web service on Render
   - Click "Environment" tab
   - Add these variables:
     - `DATABASE_URL`: Your PostgreSQL connection string
     - `SECRET_KEY`: A secure random string
     - `FLASK_ENV`: `production`

2. **Deploy**: Render will automatically run the build script which includes:
   - Installing dependencies
   - Setting up database tables
   - Running migrations

## Step 4: Test Database Connection

1. **Local Testing**:
   ```bash
   # Test basic database connection
   python -c "
   from app_simple import app
   from models import db
   with app.app_context():
       db.engine.execute('SELECT 1')
       print('Database connection successful!')
   "
   
   # Run comprehensive database tests
   python test_app_simple_db.py
   ```

2. **Render Testing**: Check the build logs for database setup messages

## Database Schema

Your application will create these tables:

- **users**: User accounts and subscription plans
- **projects**: PDF conversion projects and content
- **tokens**: Access tokens for projects
- **reset_tokens**: Password reset functionality

## Migration from File-Based Storage

If you have existing data in JSON files:

1. **Backup your data**:
   ```bash
   cp -r outputs/ outputs_backup/
   ```

2. **Run migration**:
   ```bash
   python migrate_to_postgres.py
   ```

3. **Verify migration**:
   - Check database tables for your data
   - Test application functionality

## Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if database is running on Render
   - Verify connection string format
   - Ensure IP whitelist includes your location

2. **Authentication Failed**:
   - Verify username/password in connection string
   - Check if database user has proper permissions

3. **Table Creation Failed**:
   - Ensure database exists
   - Check user permissions
   - Verify SQLAlchemy version compatibility

### Debug Commands

```bash
# Test database connection
python setup_database.py

# Check database tables
python -c "
from app_simple import app
from models import db
with app.app_context():
    print(db.engine.table_names())
"

# View migration status
python migrate_to_postgres.py
```

## Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **Database Access**: Use connection pooling for production
3. **Backups**: Enable automatic backups on Render
4. **SSL**: Always use SSL connections in production

## Next Steps

After successful database setup:

1. **Test your application** thoroughly
2. **Monitor database performance** on Render dashboard
3. **Set up regular backups** if not already enabled
4. **Consider connection pooling** for high-traffic applications

## Support

If you encounter issues:

1. Check Render service logs
2. Verify environment variables
3. Test database connection manually
4. Review this guide for common solutions

---

**Note**: This setup assumes you're using the updated application code with the new database configuration. Make sure all files are properly updated before proceeding.
