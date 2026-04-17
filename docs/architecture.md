# MxA Mobile - System Architecture

## Overview

MxA Mobile is a three-tier web application for communication intelligence and digital forensics analysis.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      User's Web Browser                         │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              SSO Server (192.168.1.59)                          │
│                     Keycloak                                    │
│              - OIDC Authentication                              │
│              - Role-based Access Control                        │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│       Application Server (192.168.1.66)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Apache + PHP 8.1 (Web Frontend)                         │  │
│  │  - Controllers (Auth, Cases, Upload, Jobs, Results)      │  │
│  │  - Services (Keycloak, Python API, MinIO)                │  │
│  │  - Views (Dashboard, Cases, Results, Admin)              │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PostgreSQL 13+                                          │  │
│  │  - User data                                             │  │
│  │  - Case metadata                                         │  │
│  │  - Job tracking                                          │  │
│  │  - Communications & Attachments                          │  │
│  │  - Audit logs                                            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│         Python Server (192.168.1.90)                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI (Port 8104)                                     │  │
│  │  - REST API Endpoints                                    │  │
│  │  - Job submission                                        │  │
│  │  - Status polling                                        │  │
│  │  - Results retrieval                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Celery Workers (Queue: mxa_mobile)                      │  │
│  │  - Evidence parsing (WhatsApp, SMS, emails)             │  │
│  │  - OCR processing                                        │  │
│  │  - Audio transcription (Whisper AI)                     │  │
│  │  - GPS/EXIF extraction                                   │  │
│  │  - Categorization                                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Redis                                                   │  │
│  │  - Celery message broker                                │  │
│  │  - Task result backend                                  │  │
│  │  - Session cache                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  MinIO (S3-compatible)                                   │  │
│  │  - Bucket: mxa-mobile-input (uploaded files)            │  │
│  │  - Bucket: mxa-mobile-output (results, previews)        │  │
│  │  - Bucket: mxa-mobile-temp (temporary processing)       │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### PHP Frontend (192.168.1.66)
- **Purpose**: Web UI and user interaction
- **Technologies**: PHP 8.1, Apache 2.4
- **Responsibilities**:
  - User authentication via Keycloak OIDC
  - Case/workspace management
  - File upload orchestration
  - Job submission and monitoring
  - Results visualization
  - Role-based access control

### Python Backend (192.168.1.90)
- **Purpose**: Processing engine
- **Technologies**: Python 3.9+, FastAPI, Celery
- **Responsibilities**:
  - Evidence parsing and analysis
  - Background job processing
  - OCR and transcription
  - Data enrichment (GPS, categorization)
  - Object storage management

### PostgreSQL Database (192.168.1.66)
- **Purpose**: Metadata storage
- **Responsibilities**:
  - User accounts (mapped from Keycloak)
  - Case definitions
  - Processing job tracking
  - Communications metadata
  - Attachment metadata
  - Tags and categorization
  - Audit logs

### MinIO Object Storage (192.168.1.90)
- **Purpose**: File and artifact storage
- **Responsibilities**:
  - Uploaded evidence files
  - Generated reports
  - Preview images/documents
  - Processed outputs

### Redis (192.168.1.90)
- **Purpose**: Message broker and cache
- **Responsibilities**:
  - Celery task queue
  - Task result storage
  - Session caching (optional)

### Keycloak (192.168.1.59)
- **Purpose**: Identity and access management
- **Responsibilities**:
  - User authentication (OIDC)
  - Role assignment
  - Token issuance and validation

## Data Flow

### 1. User Login Flow
```
User → PHP Frontend → Keycloak (OIDC) → PHP Frontend → Dashboard
```

### 2. Evidence Upload Flow
```
User uploads files → PHP Frontend → MinIO (input bucket)
→ PHP Frontend → Python API (job submission)
→ Celery Queue → Background processing
```

### 3. Processing Flow
```
Celery Worker retrieves job
→ Downloads files from MinIO
→ Parses evidence (WhatsApp, SMS, calls, emails)
→ Performs OCR on images
→ Extracts GPS/EXIF metadata
→ Transcribes audio (optional)
→ Categorizes communications
→ Stores metadata in PostgreSQL
→ Uploads results to MinIO (output bucket)
→ Updates job status
```

### 4. Results Viewing Flow
```
User requests results → PHP Frontend → Python API → PostgreSQL query
→ Returns metadata → PHP renders view
→ User clicks attachment → MinIO presigned URL → Direct download
```

## Security Architecture

### Authentication
- **Method**: OAuth 2.0 / OIDC via Keycloak
- **Flow**: Authorization Code Flow with PKCE
- **Tokens**: JWT access tokens, refresh tokens
- **Session**: PHP server-side sessions with token storage

### Authorization
- **Roles**: Defined in Keycloak
  - `user`: Basic access (create cases, upload, view own results)
  - `analyst`: Advanced access (all user permissions + tagging, exports)
  - `admin`: Full access (user management, settings, all cases)
- **Enforcement**: Both PHP (page-level) and Python API (endpoint-level)

### Data Protection
- **In Transit**: HTTPS (should be configured in production)
- **At Rest**: PostgreSQL encryption, MinIO encryption at rest
- **Isolation**: Case-based access control, row-level security
- **Audit**: All actions logged with user, IP, timestamp

## Scalability Considerations

### Horizontal Scaling
- **PHP Frontend**: Stateless, can run multiple instances behind load balancer
- **Celery Workers**: Can add more workers for parallel processing
- **PostgreSQL**: Master-slave replication for read scaling
- **MinIO**: Distributed mode for increased storage/throughput

### Performance Optimization
- **Caching**: Redis for session data, API responses
- **Database**: Indexed columns, materialized views
- **Object Storage**: Presigned URLs for direct client downloads
- **Background Jobs**: Queue-based decoupling prevents blocking

## Monitoring and Observability

### Logging
- **PHP**: Structured logs to `/var/www/mxa-mobile-app/current/storage/logs`
- **Python**: JSON logs to `/opt/apps/mxa-mobile/logs`
- **Apache**: Access/error logs
- **PostgreSQL**: Query logs (configurable)

### Health Checks
- **FastAPI**: `/health` - Basic liveness
- **FastAPI**: `/health/ready` - Readiness (checks DB, MinIO)
- **PHP**: Can implement `/health.php` endpoint

### Metrics
- Job completion rates
- Processing times per case
- Queue depths
- Storage usage
- User activity

## Deployment Topology

### Production Layout
```
192.168.1.59:8080   → Keycloak SSO
192.168.1.66:80     → Apache/PHP Frontend
192.168.1.66:5432   → PostgreSQL Database
192.168.1.90:8104   → FastAPI Backend
192.168.1.90:9000   → MinIO Object Storage
192.168.1.90:6379   → Redis
```

### Network Requirements
- Keycloak ↔ PHP: HTTP (OIDC endpoints)
- PHP ↔ Python API: HTTP (REST API)
- PHP ↔ PostgreSQL: TCP 5432
- PHP ↔ MinIO: HTTP/S 9000
- Python ↔ PostgreSQL: TCP 5432
- Python ↔ MinIO: HTTP/S 9000
- Python ↔ Redis: TCP 6379
- Celery ↔ Redis: TCP 6379

## Technology Stack Summary

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Web Server | Apache | 2.4+ | HTTP server |
| Frontend Language | PHP | 8.1+ | Web application |
| Backend Language | Python | 3.9+ | Processing engine |
| Web Framework | FastAPI | 0.104+ | REST API |
| Task Queue | Celery | 5.3+ | Background jobs |
| Message Broker | Redis | 6.0+ | Queue backend |
| Database | PostgreSQL | 13+ | Metadata storage |
| Object Storage | MinIO | Latest | File storage |
| Authentication | Keycloak | Latest | OIDC/SSO |
| OCR | Tesseract | 4.0+ | Text extraction |
| AI Transcription | Whisper | via faster-whisper | Audio to text |

## Design Patterns

### PHP Application
- **MVC Pattern**: Controllers, Services, Repositories, Views
- **Service Layer**: External service abstractions (Keycloak, Python API, MinIO)
- **Repository Pattern**: Database access abstraction
- **Dependency Injection**: Services injected into controllers

### Python Application
- **Layered Architecture**: API → Services → Tasks → Legacy Logic
- **Adapter Pattern**: Storage abstraction (filesystem → MinIO)
- **Task Queue Pattern**: Asynchronous processing with Celery
- **Preserved Logic**: Forensic toolkit logic wrapped, not rewritten

## Migration from Qt Desktop

### Preserved Components
- All parser modules (WhatsApp, SMS, emails, etc.)
- OCR processing logic
- Categorization engine
- GPS/EXIF extraction
- Audio transcription integration
- Database schema structure (SQLite → PostgreSQL)

### Replaced Components
- Qt GUI → PHP web views
- Local filesystem → MinIO object storage
- Desktop threading → Celery background tasks
- Qt signals → HTTP polling / status endpoints
- Static HTML dashboard → Dynamic web pages

### Adapted Components
- `run_analysis()` → Celery task
- Progress callbacks → Database status updates
- File path handling → Object storage references

## Future Enhancements

- WebSocket support for real-time progress updates
- Machine learning for improved categorization
- Multi-language support
- Advanced network analysis
- Timeline visualization improvements
- Export to multiple formats (PDF, JSON, CSV)
- Integration with other forensic tools
