# MxA Mobile - Communication Intelligence Web Application

**Product Name:** MxA Mobile  
**Repository:** mxa-mobile  
**Hostname:** mobile.gismartanalytics.com

## Overview

MxA Mobile is a web-based communication intelligence and digital forensics platform designed for analysts to parse, analyze, categorize, and visualize evidence from multiple sources including WhatsApp, SMS, calls, emails, audio files, images, and documents.

## Architecture

This is a **standalone, self-contained product** built on a three-tier architecture:

### Infrastructure

1. **SSO Server (192.168.1.59)**
   - Keycloak for authentication and authorization
   - OIDC-based login
   - Role-based access control

2. **Application Server (192.168.1.66)**
   - Apache + PHP 8.1 web frontend
   - PostgreSQL database
   - Metadata storage

3. **Python Server (192.168.1.90)**
   - Python + FastAPI processing engine
   - Celery + Redis for background jobs
   - MinIO for object/file storage
   - OCR and AI transcription

### Components

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│  PHP Frontend   │◄────►│    Keycloak      │
│  (Apache/PHP)   │      │  (Auth/SSO)      │
└────────┬────────┘      └──────────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ Python Backend  │◄────►│   PostgreSQL     │
│ (FastAPI/       │      │   (Metadata)     │
│  Celery)        │      └──────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     MinIO       │
│ (File Storage)  │
└─────────────────┘
```

## Features

### Evidence Ingestion
- WhatsApp chats (HTML/PDF exports)
- Text messages (CSV/Excel)
- Call logs (CSV/Excel)
- Email files (.eml, .msg, .mbox)
- Audio files with AI transcription
- Images with OCR and GPS extraction
- Documents (PDF, Word, Excel)

### Processing & Analysis
- Automated parsing and categorization
- OCR text extraction from images
- GPS/EXIF metadata extraction
- Audio transcription (Whisper AI)
- Attachment linking and verification
- Communication timeline analysis
- Network visualization
- Keyword-based categorization (Personal, Promotional, Industry-specific)

### Data Management
- Case-based organization
- Multi-user access with role controls
- PostgreSQL metadata storage
- MinIO object storage for files
- Background job processing
- Real-time progress tracking

### Visualization & Reporting
- Interactive dashboard
- Timeline views
- Network graphs
- GPS maps
- Tag management
- Export capabilities

## Directory Structure

```
mxa-v2/
├── php-app/              PHP web frontend
├── python-backend/       Python processing engine
├── database/             PostgreSQL schema and migrations
├── docs/                 Documentation
├── deploy/               Deployment configurations
└── forensic_toolkit/     Original Qt desktop application (reference)
```

## Product-Specific Configuration

All configuration is environment-specific and comes from `.env` files:

### Key Settings
- PHP App: `/var/www/mxa-mobile-app/current`
- Python App: `/opt/apps/mxa-mobile`
- Database: `mxa_mobile`
- DB User: `mxa_mobile_user`
- Keycloak Client: `mxa-mobile-web`
- MinIO Buckets: `mxa-mobile-input`, `mxa-mobile-output`
- FastAPI Port: `8104`
- Celery Queue: `mxa_mobile`

## Quick Start

### Prerequisites
- PHP 8.1+
- Python 3.9+
- PostgreSQL 13+
- Redis 6+
- MinIO
- Apache 2.4+

### Installation

1. **Clone repository**
   ```bash
   git clone <repository-url>
   cd mxa-v2
   ```

2. **Set up PHP frontend**
   ```bash
   cd php-app
   cp .env.example .env
   # Edit .env with your configuration
   composer install
   ```

3. **Set up Python backend**
   ```bash
   cd python-backend
   cp .env.example .env
   # Edit .env with your configuration
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   psql -U postgres -f database/schema.sql
   ```

5. **Configure services**
   - Copy Apache config: `deploy/apache/mxa-mobile.conf`
   - Install systemd services: `deploy/systemd/`

### Running Locally

**PHP Development Server:**
```bash
cd php-app/public
php -S localhost:8000
```

**Python API:**
```bash
cd python-backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8104 --reload
```

**Celery Worker:**
```bash
cd python-backend
source venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info -Q mxa_mobile
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Architecture](docs/architecture.md) - System design and data flow
- [Deployment](docs/deployment.md) - Production deployment guide
- [Configuration](docs/configuration.md) - Environment variables and settings
- [Database](docs/database.md) - Schema and migrations
- [API](docs/api.md) - Python API endpoints
- [Authentication](docs/authentication.md) - Keycloak integration
- [Maintenance](docs/maintenance.md) - Operational procedures
- [Troubleshooting](docs/troubleshooting.md) - Common issues and solutions
- [Migration from Qt](docs/migration-from-qt.md) - Desktop to web migration notes

## Security

- **Authentication:** Keycloak OIDC Authorization Code Flow
- **Authorization:** Role-based access control
- **Sessions:** Secure PHP session handling with CSRF protection
- **Secrets:** All credentials in environment variables, never in code
- **File Validation:** Strict upload validation and sandboxing
- **Data Isolation:** Case-based access control with row-level security
- **Audit Logging:** Comprehensive activity logging

## Development

### Code Style
- **PHP:** PSR-12 coding standard
- **Python:** PEP 8 with Black formatter
- **JavaScript:** ESLint with standard config

### Testing
```bash
# PHP tests
cd php-app
./vendor/bin/phpunit

# Python tests
cd python-backend
pytest
```

## Support

For issues, questions, or feature requests, please contact the development team.

## License

Proprietary - All rights reserved

## Product Isolation

This repository represents a **fully independent product**. It does not and must not:
- Share code with other products
- Depend on other products
- Reference other product configurations
- Share databases, queues, buckets, or logs
- Assume a shared monolith architecture

Each deployment maintains complete isolation with its own infrastructure stack.
