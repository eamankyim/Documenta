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
