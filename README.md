# Documenta - HTML Document Editor

A web-based HTML document editor with user authentication and project management.

## Features

- Create and edit HTML documents
- User authentication and project management
- Real-time editing with auto-save
- Project sharing with secure tokens
- Responsive design

## Deployment on Render

This app is designed to work with Render's free tier, which has an ephemeral file system. Here's how data persistence works:

### Data Storage Strategy

1. **Primary Storage**: PostgreSQL database (persistent)
   - All document content is stored in the database
   - User accounts and project metadata
   - Authentication tokens

2. **File System**: Temporary cache (ephemeral)
   - Files are recreated from database on startup
   - Used for immediate editing performance
   - Automatically synced when missing

### How It Handles Render Restarts

When Render restarts the service (due to inactivity):
1. **File system is reset** - All files in `outputs/` are lost
2. **Database remains intact** - All data is preserved
3. **App automatically recreates files** - Missing files are restored from database
4. **Users can continue editing** - No data loss occurs

### Key Features for Persistence

- **Database-first approach**: Always reads from database first
- **Auto-file recreation**: Missing files are automatically recreated
- **Graceful fallbacks**: App works even if file system is empty
- **Startup sync**: All missing files are restored on app startup

## Local Development

1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables (see `env.example`)
3. Run: `python app.py`

## Production Deployment

The app is configured for Render deployment with:
- Gunicorn WSGI server
- PostgreSQL database
- Health checks
- Auto-deployment on git push 