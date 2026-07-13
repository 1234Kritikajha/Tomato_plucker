#!/usr/bin/env python3
"""
Tomato Plucker Backend Startup Script
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Main startup function"""
    print("Starting Tomato Plucker Backend Server...")
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # Check if virtual environment exists
    venv_dir = backend_dir / "venv"
    if not venv_dir.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
    
    # Install dependencies
    print("Installing dependencies...")
    pip_path = venv_dir / "bin" / "pip"
    subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
    
    # Create necessary directories
    print("Creating storage directories...")
    storage_dir = backend_dir / "storage"
    (storage_dir / "uploads").mkdir(parents=True, exist_ok=True)
    (storage_dir / "exports").mkdir(parents=True, exist_ok=True)
    (storage_dir / "logs").mkdir(parents=True, exist_ok=True)
    (storage_dir / "temp").mkdir(parents=True, exist_ok=True)
    (storage_dir / "review_queue" / "low_confidence").mkdir(parents=True, exist_ok=True)
    
    # Start the server
    print("Starting FastAPI server...")
    uvicorn_path = venv_dir / "bin" / "uvicorn"
    subprocess.run([str(uvicorn_path), "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"])

if __name__ == "__main__":
    main()