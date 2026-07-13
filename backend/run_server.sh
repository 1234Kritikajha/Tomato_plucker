#!/bin/bash

# Simple startup script for Tomato Plucker Backend
# Assumes dependencies are already installed

echo "Starting Tomato Plucker Backend Server..."

# Change to backend directory
cd "$(dirname "$0")"

# Start the server directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload