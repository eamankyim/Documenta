#!/usr/bin/env bash
# Build script for Render deployment

# Install dependencies
pip install -r render-requirements.txt

# Initialize the database
python render_setup.py

echo "Build completed successfully!"
