# DPDP GUI Compliance Scanner

A comprehensive toolkit for scanning web and Windows applications for compliance with the **Digital Personal Data Protection (DPDP) Act, 2023** of India.

Built for **NIC (National Informatics Centre)**.

---

## Features

- **Web Application Scanning** - Crawls websites, extracts DOM, analyzes content
- **Windows GUI Scanning** - OCR + OpenCV for desktop applications
- **SPA Support** - Route-based navigation for React/Angular/Vue apps
- **Multi-language Support** - English + Hindi (Tesseract OCR)
- **Real-time Progress** - WebSocket updates during scan
- **Evidence Collection** - Screenshots with annotations
- **Comprehensive Reports** - PDF and Excel formats
- **Enhanced Findings** - Visual diagrams, code examples, penalty information

---

## DPDP Sections Covered

| Section | Description |
|---------|-------------|
| Section 5 | Privacy Notice |
| Section 6 | Consent Management |
| Section 6(6) | Consent Withdrawal |
| Section 8 | Data Retention |
| Section 8(6) | Breach Notification |
| Section 9 | Children's Data Protection |
| Section 10 | Significant Data Fiduciary |
| Section 11-12 | Right to Access & Correction |
| Section 13 | Grievance Redressal |
| Section 14 | Right to Nomination |
| Section 18 | Dark Patterns Detection |

---

## Quick Start (Docker)

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/EktaOryggitech/DPDP-Compliance-Toolkit.git
   cd DPDP-Compliance-Toolkit
   ```

2. **Start all services**
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

3. **Wait for services to initialize** (first time takes 2-3 minutes)
   ```bash
   docker compose -f docker/docker-compose.yml logs -f
   ```
   Press `Ctrl+C` to exit logs once you see "Application startup complete"

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Default Login

```
Email: admin@example.com
Password: admin123
```

---

## Services Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  DPDP Compliance Scanner                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Frontend   │    │   Backend    │    │   Worker     │  │
│  │   (React)    │───▶│  (FastAPI)   │───▶│  (Celery)    │  │
│  │  Port 3000   │    │  Port 8000   │    │              │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                             │                    │          │
│                      ┌──────┴──────┐            │          │
│                      ▼             ▼            ▼          │
│               ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│               │ Postgres │  │  Redis   │  │  MinIO   │    │
│               │   (DB)   │  │ (Queue)  │  │ (Files)  │    │
│               │ Port 5432│  │ Port 6379│  │ Port 9000│    │
│               └──────────┘  └──────────┘  └──────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Docker Commands

### Start Services
```bash
docker compose -f docker/docker-compose.yml up -d
```

### Stop Services
```bash
docker compose -f docker/docker-compose.yml down
```

### View Logs
```bash
# All services
docker compose -f docker/docker-compose.yml logs -f

# Specific service
docker logs dpdp_backend -f
docker logs dpdp_frontend -f
docker logs dpdp_celery_worker -f
```

### Rebuild After Code Changes
```bash
docker compose -f docker/docker-compose.yml build backend frontend --no-cache
docker compose -f docker/docker-compose.yml up -d backend frontend
```

### Reset Database
```bash
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

---

## Project Structure

```
dpdp-gui-scanner/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── api/v1/            # API Routes
│   │   ├── core/              # Config, Database, Security
│   │   ├── detectors/         # DPDP Compliance Detectors
│   │   ├── evidence/          # Screenshot & Annotation
│   │   ├── models/            # SQLAlchemy Models
│   │   ├── nlp/               # NLP Analysis
│   │   ├── reports/           # PDF/Excel Generators
│   │   ├── scanners/          # Web & Windows Scanners
│   │   ├── schemas/           # Pydantic Schemas
│   │   └── workers/           # Celery Tasks
│   └── Dockerfile
├── frontend/                   # React Frontend
│   ├── src/
│   │   ├── components/        # Reusable components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # API client & utilities
│   │   ├── pages/             # Page components
│   │   └── stores/            # Zustand state stores
│   └── Dockerfile
├── docker/
│   ├── docker-compose.yml     # Full setup
│   └── docker-compose.minimal.yml
└── README.md
```

---

## Environment Variables

The Docker setup uses sensible defaults. For production, create a `.env` file:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/dpdp_scanner

# Redis
REDIS_URL=redis://redis:6379/0

# Security
SECRET_KEY=your-secure-secret-key-change-in-production

# Session
SESSION_INACTIVITY_TIMEOUT_MINUTES=5
HEARTBEAT_INTERVAL_SECONDS=30

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

---

## Running a Scan

1. Login at http://localhost:3000
2. Go to **Applications** → **Add Application**
3. Enter application name and URL (e.g., `https://www.example.com`)
4. Go to **Scans** → **New Scan**
5. Select application and scan type:
   - **Quick** - 20 pages, basic checks
   - **Standard** - 50 pages, all sections
   - **Deep** - 200 pages, NLP + OCR analysis
6. Click **Start Scan**
7. View real-time progress and results

---

## API Documentation

Once running, access the interactive API docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Troubleshooting

### Port Already in Use
```bash
# Check what's using the port
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Kill the process or change ports in docker-compose.yml
```

### Docker Issues
```bash
# Restart Docker Desktop
# Then rebuild
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d --build
```

### Database Connection Issues
```bash
# Reset the database
docker compose -f docker/docker-compose.yml down -v
docker compose -f docker/docker-compose.yml up -d
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python, FastAPI, SQLAlchemy, Celery |
| Frontend | React, TypeScript, TailwindCSS, Zustand |
| Database | PostgreSQL |
| Queue | Redis |
| Storage | MinIO (S3-compatible) |
| Scanning | Playwright, Tesseract OCR, OpenCV |
| Reports | ReportLab (PDF), OpenPyXL (Excel) |

---

## License

Proprietary - Oryggi Technologies

---

## Support

For issues or questions, contact the development team.
