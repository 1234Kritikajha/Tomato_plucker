#!/bin/bash

# Tomato Plucker Backend Startup Script

echo "Starting Tomato Plucker Backend Server..."

# Change to backend directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating storage directories..."
mkdir -p storage/uploads
mkdir -p storage/exports
mkdir -p storage/logs
mkdir -p storage/temp
mkdir -p storage/review_queue/low_confidence

# Start the server
echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload