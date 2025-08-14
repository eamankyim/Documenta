#!/usr/bin/env bash
# Build script for Render deployment

# Install dependencies
pip install -r render-requirements.txt

# Initialize the database
python setup_database.py

# Run database migration if needed
if [ -f "migrate_to_postgres.py" ]; then
    echo "Running database migration..."
    python migrate_to_postgres.py
fi

echo "Build completed successfully!"

# NOTE: Render requires a Start Command, so we'll start the app here
# If you prefer to use the Procfile, set Start Command to: python app.py
# Otherwise, this script will handle both build and start

echo "Starting Flask application..."
exec python app.py
