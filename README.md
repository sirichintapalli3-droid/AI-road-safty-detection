# AI Road Safety System

An AI-assisted traffic monitoring platform built with Python, FastAPI, React, YOLO, ByteTrack, OpenCV, EasyOCR, SQLAlchemy, and MySQL.

The project analyzes uploaded traffic images and videos, supports browser camera capture, detects vehicles, tracks unique vehicles, estimates traffic density, estimates speed when calibrated, checks movement direction, reads number plates with a custom model and OCR, identifies possible accidents, and sends real-time alerts to the dashboard.

## Current Status

The working foundation includes Phases 1-11:

- FastAPI backend with Swagger documentation
- React/Vite responsive monitoring dashboard
- MySQL and SQLAlchemy configuration
- YOLO vehicle detection
- ByteTrack object tracking and unique counting
- Traffic density classification
- Browser camera preview and frame capture
- Custom helmet detection endpoint
- Custom number-plate detection and EasyOCR endpoint
- Calibrated speed estimation and wrong-way analysis
- Possible-accident analysis for images and videos
- Real-time WebSocket alerts
- JWT authentication and role-based authorization API

## Important Accuracy Note

This is an engineering prototype, not a guaranteed safety authority. AI results are observations and should be reviewed by a human. A single image cannot prove that an accident happened. Speed is only meaningful after camera calibration. Helmet and number-plate detection require custom trained weights; the general COCO model does not provide those classes.

## Project Structure

```text
AI-Road-Safety-System/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── vehicle_detection.py
│   │   │   ├── helmet_detection.py
│   │   │   └── number_plate.py
│   │   ├── middleware/
│   │   │   └── auth.py
│   │   ├── models/
│   │   │   └── user.py
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── detection.py
│   │   │   ├── helmet.py
│   │   │   ├── number_plate.py
│   │   │   └── alerts.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── security.py
│   │   │   └── alerts.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── hooks/useAlerts.js
│   │   ├── services/api.js
│   │   ├── App.jsx
│   │   └── styles.css
│   └── package.json
├── models/
├── datasets/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Technology

### Backend

- Python 3.10+
- FastAPI and Uvicorn
- SQLAlchemy 2
- MySQL with PyMySQL
- Pydantic Settings
- JWT with `python-jose`
- Argon2 password hashing with `pwdlib`

### AI and vision

- Ultralytics YOLO
- ByteTrack
- OpenCV
- NumPy
- EasyOCR
- PyTorch, installed through Ultralytics

### Frontend

- React
- Vite
- Browser MediaDevices API
- WebSocket client
- Responsive CSS dashboard

## Windows Prerequisites

Install:

- Python 3.10 or newer
- Node.js 20 or newer
- npm
- Docker Desktop, only needed for the Docker workflow
- A browser with camera permission support, such as Chrome or Edge

## Local Installation

### 1. Backend

Open PowerShell in the project root:

```powershell
cd backend
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
```

If PowerShell blocks virtual-environment activation:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.venv\Scripts\Activate.ps1
```

Start FastAPI:

```powershell
py -3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/health`

### 2. Frontend

Open a second PowerShell window:

```powershell
cd frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

Open the Vite URL shown in the terminal, usually `http://localhost:5173`. If that port is busy, Vite may use `http://localhost:5176`; that port is included in the backend CORS configuration.

### 3. Docker

From the project root:

```powershell
docker compose up --build
```

Services:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- MySQL: `localhost:3306`

Stop Docker services:

```powershell
docker compose down
```

## Dashboard Usage

### Upload an ordinary photo

1. Open **Objects** mode.
2. Choose a JPEG, PNG, or WebP image.
3. Select **Run vehicle detection**.
4. The result shows model-produced object detections.

Detected COCO classes include person, bicycle, car, motorcycle, bus, and truck.

### Use the camera

1. Choose **Objects** or **Accident image** mode.
2. Choose **Camera**.
3. Allow browser camera permission.
4. Select **Capture and assess**.

The browser captures one frame and sends it to FastAPI. Continuous camera tracking is not implemented yet.

### Upload a traffic video

1. Choose **Video** mode.
2. Select an MP4, AVI, or MOV file.
3. Select **Track and analyze video**.
4. The dashboard displays processed frames, unique vehicles, class counts, peak visible vehicles, average visible vehicles, and density.

### Accident image assessment

1. Choose **Accident image** mode.
2. Upload a photo.
3. Select **Assess accident image**.

The result is one of:

- `POSSIBLE_ACCIDENT`: overlapping vehicle boxes were found; review required
- `NO_ACCIDENT_EVIDENCE`: no overlapping vehicle boxes were found

A single frame cannot confirm an accident. Video analysis is more appropriate for temporal collision evidence.

### Dashboard colors

- Green: latest analysis is safe or no danger is active
- Yellow: medium-density or review-recommended result
- Red: possible accident, overspeeding, wrong-way, or no-helmet danger
- Amber/neutral: the system is connecting or waiting for input

## API Reference

### System

```text
GET  /api/
GET  /api/health
```

### Authentication

```text
POST /api/auth/register
POST /api/auth/login
GET  /api/auth/me
GET  /api/auth/admin-check
```

Registration creates a normal `user` account. There is no public admin-registration endpoint. An administrator must be created or promoted through a controlled database/deployment process.

Example registration body:

```json
{"email":"user@example.com","password":"minimum-8-characters"}
```

Login and registration return a bearer token. Send it to protected endpoints as:

```text
Authorization: Bearer <access-token>
```

### Detection and analysis

```text
POST /api/detection/image
POST /api/detection/accident-image
POST /api/detection/video/track
POST /api/detection/video/analyze-speed
POST /api/detection/video/detect-accidents
POST /api/helmet/image
POST /api/number-plates/image
```

All upload endpoints use `multipart/form-data` with a field named `file`.

### WebSocket alerts

```text
ws://localhost:8000/api/ws/alerts
```

The stream sends `CONNECTED` immediately and can broadcast:

- `ACCIDENT_SUSPECTED`
- `NO_HELMET`
- `OVERSPEEDING`
- `WRONG_WAY`
- `NUMBER_PLATE_DETECTED`

Authentication for the WebSocket channel is planned for a later hardening pass.

## Configuration

Backend settings are loaded from `backend/.env`:

```env
APP_NAME=AI Road Safety System
APP_VERSION=0.1.0
ENVIRONMENT=development
API_PREFIX=/api
DATABASE_URL=mysql+pymysql://road_safety:road_safety@localhost:3306/road_safety
FRONTEND_ORIGINS=http://localhost:5173,http://localhost:5176
MAX_UPLOAD_SIZE_MB=200

YOLO_MODEL_PATH=yolo11n.pt
YOLO_CONFIDENCE=0.25
YOLO_DEVICE=cpu

HELMET_MODEL_PATH=models/helmet.pt
HELMET_CONFIDENCE=0.35
PLATE_MODEL_PATH=models/number_plate.pt
PLATE_CONFIDENCE=0.35
OCR_LANGUAGES=en

DENSITY_MEDIUM_THRESHOLD=5
DENSITY_HIGH_THRESHOLD=15
DENSITY_VERY_HIGH_THRESHOLD=30

PIXELS_PER_METER=0
SPEED_LIMIT_KMH=50
ALLOWED_DIRECTION_DEGREES=0
WRONG_WAY_MIN_DISPLACEMENT_PIXELS=15

ACCIDENT_IOU_THRESHOLD=0.2
ACCIDENT_MIN_MOTION_PIXELS=5

JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Never use the example JWT secret or development database password in a shared deployment. Do not commit `.env` files.

## AI Models and Datasets

The general YOLO model is downloaded automatically on first use when `YOLO_MODEL_PATH` points to a missing supported model such as `yolo11n.pt`. Model weights are ignored by Git.

Custom models are required for:

- Helmet: classes `helmet` and `no_helmet`
- Number plate: class `license_plate`, `number_plate`, or `plate`

Useful dataset starting points include UFPR-ALPR, CCPD, and a properly licensed regional number-plate dataset. Build a helmet dataset from camera views similar to the target deployment. Confirm licenses and keep camera locations separate between training and testing.

## Validation Commands

Backend syntax and dependencies:

```powershell
py -3 -m compileall -q backend\app
py -3 -m pip check
```

Frontend production build:

```powershell
npm.cmd --prefix frontend run build
```

Health check:

```powershell
curl.exe http://localhost:8000/api/health
```

## Troubleshooting

### `ERR_CONNECTION_REFUSED` on port 8000

Start FastAPI:

```powershell
py -3 -m uvicorn app.main:app --app-dir "c:\path\to\AI-Road-Safety-System\backend" --host 0.0.0.0 --port 8000
```

### CORS error from port 5176

Restart FastAPI after changing `.env`. `FRONTEND_ORIGINS` must include the exact frontend origin, including its port.

### Camera permission denied

Use `http://localhost`, allow camera permission in browser site settings, close other applications using the camera, and reload the page. The application needs an actual camera; browser privacy settings can block access.

### `503` from helmet or plate endpoints

The required custom model file is missing or cannot be loaded. Configure the correct model path and ensure the model has the expected class names.

### Speed values are empty

Set a real `PIXELS_PER_METER` value after calibrating the camera. With `PIXELS_PER_METER=0`, empty speed values are intentional.

### MySQL startup warning

The API can start while MySQL is unavailable, but user-table creation and authentication require a reachable database. Start MySQL with Docker Compose or update `DATABASE_URL`.

## Remaining Roadmap

The next production work should include:

1. Background jobs for long video processing
2. Persistent cameras, detections, violations, accidents, and alerts tables
3. Authenticated WebSocket connections
4. Continuous camera/video streaming with server-side tracking
5. Evidence image storage and retention rules
6. Full violations, accidents, reports, and camera-management pages
7. Custom-model evaluation, metrics, and confidence calibration
8. Docker secrets, migrations, structured logging, tests, and deployment hardening
"# AI-road-safty-detection" 
