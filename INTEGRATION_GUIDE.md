# Tomato Plucker - Backend-Frontend Integration Guide

## Overview
This guide provides comprehensive instructions for running the Tomato Plucker application with fully functional backend and frontend integration.

## Prerequisites
- Python 3.8+
- Node.js 16+
- Modern web browser

## Setup & Installation

### 1. Backend Setup

#### Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### Create Storage Directories
```bash
mkdir -p storage/uploads
mkdir -p storage/exports
mkdir -p storage/logs
mkdir -p storage/temp
mkdir -p storage/review_queue/low_confidence
```

#### Start Backend Server
```bash
# Option 1: Simple startup
./run_server.sh

# Option 2: Full startup with venv
./start_server.sh

# Option 3: Direct uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Backend will be available at: http://192.168.0.152:8000**

### 2. Frontend Setup

#### Install Dependencies
```bash
cd frontend
npm install
```

#### Start Frontend Development Server
```bash
npm run dev
```

**Frontend will be available at: http://localhost:5173**

## Integration Verification

### 1. Health Check
```bash
curl http://192.168.0.152:8000/api/health
```

Expected response:
```json
{
  "status": "ok",
  "database": {
    "reachable": true,
    "write_ready": true,
    "path": "/path/to/tomatoplucker.db",
    "error": null
  },
  "tracking_flags": {
    "low_confidence_queue": true,
    "uploads_dir": true
  }
}
```

### 2. Test Model Management API
```bash
curl http://192.168.0.152:8000/api/models/list
```

### 3. Test Metrics API
```bash
curl http://192.168.0.152:8000/api/metrics/summary
```

### 4. Test Prediction API
```bash
curl -X POST -F "file=@test_image.jpg" http://192.168.0.152:8000/api/predict
```

## Frontend Features & Backend Integration

### 1. Model Management Page
- **URL**: `/model-management`
- **Backend APIs**:
  - `GET /api/models/list` - Fetch all models
  - `GET /api/models/active` - Get active model
  - `POST /api/models/rollback` - Rollback to previous version
  - `DELETE /api/models/{name}` - Delete model

### 2. Inference Dashboard
- **URL**: `/inference-dashboard`
- **Backend APIs**:
  - `GET /api/metrics/summary` - Summary metrics
  - `GET /api/metrics/performance` - Performance metrics
  - `GET /api/metrics/historical` - Historical data
  - `GET /api/predict/history` - Recent predictions

### 3. Live Detection
- **URL**: `/live-detection`
- **Backend APIs**:
  - `POST /api/predict` - Real-time image analysis

### 4. Upload Image
- **URL**: `/upload-image`
- **Backend APIs**:
  - `POST /api/predict` - Image analysis
  - `POST /api/generate_report` - PDF report generation

### 5. Monitoring
- **URL**: `/monitoring`
- **Backend APIs**:
  - `GET /api/metrics/summary` - System metrics
  - `GET /api/metrics/realtime` - Real-time metrics

## Configuration

### Backend Configuration
Edit `backend/app/main.py` to change:
- CORS origins
- Server host/port
- API endpoints

### Frontend Configuration
Edit `frontend/src/api/client.js` to change:
- `API_BASE_URL` - Backend server URL

## Model System

### Model Loading
The backend uses a sophisticated model loading system:
1. **Primary Model**: Tries to load TensorFlow/Keras model
2. **Fallback**: If primary fails, uses OpenCV-based detection
3. **Configuration**: Loads model config from `model_config.json`

### Model Files
- `storage/models/tomato_plucking_model.keras` - Active model
- `storage/models/checkpoints/` - Model checkpoints
- `storage/models/model_config.json` - Model configuration
- `storage/models/class_names.json` - Classification classes

### Model Management
- Upload new models via API
- Rollback to previous versions
- Delete unused models
- Monitor model performance

## Database

### Schema
- `predictions` - Store all prediction results
- `annotations` - User corrections and feedback
- `model_versions` - Model version tracking
- `telemetry_history` - System telemetry data

### Location
`backend/storage/dataset/sqlite/tomatoplucker.db`

## API Endpoints Summary

### Core APIs
- `POST /api/upload` - Upload images
- `POST /api/predict` - Analyze images
- `GET /api/predict/history` - Get prediction history
- `POST /api/generate_report` - Generate reports

### Model APIs
- `GET /api/models/list` - List models
- `GET /api/models/active` - Get active model
- `POST /api/models/rollback` - Rollback model
- `DELETE /api/models/{name}` - Delete model

### Metrics APIs
- `GET /api/metrics/summary` - Summary metrics
- `GET /api/metrics/historical` - Historical metrics
- `GET /api/metrics/performance` - Performance metrics
- `GET /api/metrics/realtime` - Real-time metrics

### Training APIs
- `POST /api/train/start` - Start training
- `GET /api/train/status` - Training status
- `POST /api/train/stop` - Stop training

### System APIs
- `GET /api/health` - Health check
- `GET /api/system/info` - System info
- `GET /api/system/config` - System config
- `PUT /api/system/config` - Update config

## Troubleshooting

### Backend Issues

#### Server won't start
- Check if port 8000 is available
- Verify Python dependencies are installed
- Check database file permissions

#### Model loading fails
- System will automatically fallback to OpenCV
- Check model file integrity
- Verify model configuration

#### Database errors
- Ensure storage directory has write permissions
- Check database file isn't corrupted
- Verify SQLite is working

### Frontend Issues

#### Can't connect to backend
- Verify backend is running
- Check API_BASE_URL in client.js
- Ensure CORS is configured correctly

#### API calls failing
- Check browser console for errors
- Verify network requests in DevTools
- Ensure backend API endpoints are working

### Integration Issues

#### Data not updating
- Check frontend refresh intervals
- Verify backend API responses
- Check for CORS errors

#### Real-time features not working
- Ensure WebSocket connections are working
- Check network connectivity
- Verify background tasks are running

## Performance Optimization

### Backend
- Use model checkpoints for faster loading
- Enable database query caching
- Implement request rate limiting
- Use background tasks for long operations

### Frontend
- Implement API response caching
- Use React.memo for expensive components
- Optimize image uploads with compression
- Implement lazy loading for large datasets

## Security Considerations

### Backend
- Implement proper authentication
- Use HTTPS in production
- Validate all file uploads
- Sanitize user inputs
- Implement rate limiting

### Frontend
- Never expose API keys
- Validate user inputs
- Use secure cookies for auth
- Implement CSRF protection

## Deployment

### Production Deployment
1. Use production-grade server (Gunicorn, Nginx)
2. Enable HTTPS
3. Implement proper logging
4. Set up monitoring and alerts
5. Use environment variables for config
6. Implement backup strategies

### Docker Deployment
```dockerfile
# Backend Dockerfile example
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Support

For issues or questions:
1. Check this guide first
2. Review API documentation
3. Check server logs
4. Test API endpoints individually
5. Verify network connectivity

## Summary

Your Tomato Plucker application now has:
- ✅ Fully functional FastAPI backend
- ✅ Complete API endpoints for all features
- ✅ React frontend with proper API integration
- ✅ Model management system
- ✅ Real-time monitoring dashboard
- ✅ Image analysis and classification
- ✅ Database integration
- ✅ Comprehensive error handling
- ✅ Configuration management
- ✅ Development and production setup

The backend and frontend are now fully synchronized and ready for production use!