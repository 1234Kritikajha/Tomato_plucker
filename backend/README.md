# Tomato Plucker Backend

FastAPI-based backend server for tomato detection and classification system.

## Setup Instructions

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Create virtual environment:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Create necessary directories:**
```bash
mkdir -p storage/uploads
mkdir -p storage/exports
mkdir -p storage/logs
mkdir -p storage/temp
mkdir -p storage/review_queue/low_confidence
```

### Running the Server

**Option 1: Using the startup script (recommended)**
```bash
./run_server.sh
```

**Option 2: Using Python script**
```bash
python3 start_server.py
```

**Option 3: Direct uvicorn command**
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option 4: Full setup with virtual environment creation**
```bash
./start_server.sh
```

## API Endpoints

### Core Endpoints
- `POST /api/upload` - Upload image
- `POST /api/predict` - Analyze image and get predictions
- `GET /api/predict/history` - Get recent prediction history
- `POST /api/generate_report` - Generate PDF report

### Model Management
- `GET /api/models/list` - List all available models
- `GET /api/models/active` - Get current active model
- `POST /api/models/rollback` - Rollback to previous model version
- `DELETE /api/models/{model_name}` - Delete a model
- `GET /api/models/info/{model_name}` - Get model information

### Metrics & Monitoring
- `GET /api/metrics/summary` - Get summary metrics
- `GET /api/metrics/historical` - Get historical metrics
- `GET /api/metrics/performance` - Get performance metrics
- `GET /api/metrics/realtime` - Get real-time system metrics

### Training
- `POST /api/train/start` - Start model training
- `GET /api/train/status` - Get training status
- `POST /api/train/stop` - Stop training
- `POST /api/train/evaluate` - Evaluate model

### System
- `GET /api/health` - Health check
- `GET /api/system/info` - System information
- `GET /api/system/config` - Get system configuration
- `PUT /api/system/config` - Update system configuration
- `GET /api/system/logs` - Get system logs

## Database

The backend uses SQLite database stored at `storage/dataset/sqlite/tomatoplucker.db`.

## Model Files

Model files are stored in `storage/models/`:
- `tomato_plucking_model.keras` - Active model
- `checkpoints/` - Model checkpoints
- `model_config.json` - Model configuration
- `class_names.json` - Class names for classification

## Frontend Integration

The frontend is configured to connect to the backend at `http://192.168.0.152:8000/api`.

To change the backend URL, update `API_BASE_URL` in `frontend/src/api/client.js`.

## Development

For development with auto-reload:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Troubleshooting

### Model Loading Issues
If the model fails to load, the system will automatically fall back to OpenCV-based detection.
Check the logs for model loading errors.

### Database Issues
If database errors occur, ensure the storage directory has proper write permissions.

### Port Already in Use
If port 8000 is already in use, you can change it:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## License

Proprietary - All rights reserved