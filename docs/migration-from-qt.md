# MxA Mobile - Migration from Qt Desktop to Web Application

## Overview

This document explains the migration of the forensic_toolkit Qt desktop application to the MxA Mobile web application, detailing what was preserved, what was replaced, and what was adapted.

## Migration Approach

**Philosophy**: Preserve working business logic, replace only UI and storage layers.

**Success Metrics**:
- 70%+ of processing logic preserved
- All features from desktop version available in web version
- Improved multi-user support
- Better scalability

## What Was Preserved (Reused As-Is or With Minimal Changes)

### 1. Parser Modules (`forensic_toolkit/parsers/`)
**Status**: ✅ Preserved with minimal adaptation

All parser modules remain functionally identical:
- `whatsapp_html.py` - WhatsApp HTML chat parsing
- `whatsapp_pdf_parser.py` - WhatsApp PDF export parsing
- `messages_parser.py` - SMS/text message parsing (CSV/Excel)
- `calls_parser.py` - Call log parsing (CSV/Excel)
- `email_parser.py` - Email file parsing (.eml, .msg, .mbox)
- `audio_parser.py` - Audio file handling and transcription
- `image_parser.py` - Image metadata extraction
- `common.py` - Shared parser utilities

**Adaptation Required**:
- File paths now reference MinIO object storage instead of local filesystem
- Progress callbacks emit to database/Redis instead of Qt signals

### 2. OCR Processing (`forensic_toolkit/ocr.py`)
**Status**: ✅ Preserved

- `ocr_image()` function remains unchanged
- Tesseract integration identical
- Quick text detection logic preserved
- Returns same data structure

**Wrapped As**: Celery task for background processing

### 3. Categorization Engine (`forensic_toolkit/categorizer.py`)
**Status**: ✅ Preserved

- `classify_text()` logic unchanged
- `load_category_config()` unchanged
- Category models (generic, energy, banking, SCM) preserved
- Keyword matching rules identical

**Location**: `python-backend/app/legacy_logic/categorizer.py`

### 4. Database Schema (`forensic_toolkit/db.py`)
**Status**: ✅ Adapted (SQLite → PostgreSQL)

Schema structure preserved with improvements:
- Same table names: `communications`, `attachments`, `tags`, `item_tags`
- Same column names and relationships
- Added web-specific tables: `users`, `processing_jobs`, `audit_logs`
- Changed from SQLite to PostgreSQL (better concurrency, performance)

**Improvements**:
- Proper foreign key constraints
- Better indexing
- JSONB columns for metadata
- Full-text search capabilities
- Views for common queries

### 5. Utilities (`forensic_toolkit/utils.py`)
**Status**: ✅ Preserved

- EXIF/GPS extraction functions
- Timestamp parsing
- Encoding detection
- Text normalization
- All helper functions preserved

**Location**: `python-backend/app/legacy_logic/utils.py`

### 6. Processing Workflow (`forensic_toolkit/runner.py`)
**Status**: ✅ Adapted

The core `run_analysis()` orchestration logic preserved:
- Same processing steps
- Same order of operations
- Same error handling patterns
- Same progress reporting structure

**Adaptations**:
- Wrapped as Celery task `process_case_task()`
- File I/O adapted for MinIO
- Progress updates go to PostgreSQL
- Returns job status instead of blocking

## What Was Replaced (Complete Rewrite)

### 1. Qt Desktop UI (`forensic_toolkit/gui.py`)
**Status**: ❌ Replaced with PHP web application

5,500+ lines of Qt widgets replaced with:
- PHP controllers for request handling
- PHP views for HTML rendering
- JavaScript for client-side interactivity
- CSS for styling (Roboto font preserved)

**Mapping**:
```
Qt Main Window       → PHP Dashboard Controller
Qt Case Dialog       → PHP Case Controller + Views
Qt Upload Dialog     → PHP Upload Controller + Form
Qt Progress Dialog   → Job Status Page with AJAX polling
Qt Results Viewer    → PHP Results Controller + Views
Qt Settings Dialog   → PHP Admin Controller
```

### 2. Local Filesystem Storage
**Status**: ❌ Replaced with MinIO

Desktop version stored everything locally:
- Input files in case folders
- Output files in case folders
- Media files in media subfolder
- Previews in preview subfolder

Web version uses MinIO object storage:
- `mxa-mobile-input/` - Uploaded evidence
- `mxa-mobile-output/` - Processing results
- Presigned URLs for downloads
- Better scalability and redundancy

### 3. Desktop Threading
**Status**: ❌ Replaced with Celery

Qt used QThread for background processing:
```python
class ProcessingThread(QThread):
    def run(self):
        # Process in background
```

Web version uses Celery:
```python
@celery_app.task
def process_case_task(job_id, job_data):
    # Process in background worker
```

**Advantages**:
- Multiple workers can process concurrently
- Better error handling and retry logic
- Distributed processing across servers
- No blocking of web server

### 4. Static HTML Dashboard
**Status**: ❌ Replaced with dynamic web pages

Desktop generated static HTML files in case output folder.
Web version serves dynamic pages via PHP:
- Real-time data from PostgreSQL
- Interactive filtering and searching
- AJAX updates
- Better user experience

## What Was Adapted (Logic Preserved, Implementation Changed)

### 1. Progress Reporting
**Desktop**: Qt signals/slots
```python
self.progress_signal.emit("Processing...")
```

**Web**: Database status updates
```python
job_service.update_job_status(
    job_id=job_id,
    status='processing',
    progress=50,
    current_step='Analyzing evidence'
)
```

### 2. File Path Handling
**Desktop**: Local filesystem paths
```python
media_path = os.path.join(case_dir, 'media', filename)
```

**Web**: MinIO object storage
```python
object_name = f'cases/{case_number}/media/{filename}'
minio_service.upload_file(local_path, object_name)
```

### 3. Dashboard Generation
**Desktop**: Generate static HTML files
```python
generate_dashboard(records, attachments, case_dir)
```

**Web**: API endpoints return JSON, PHP renders views
```python
@router.get("/communications")
async def get_communications(case_id: int):
    return db.get_communications(case_id)
```

## Architecture Comparison

### Desktop Architecture
```
┌─────────────┐
│   Qt GUI    │
│  (Desktop)  │
└──────┬──────┘
       │
┌──────▼──────┐      ┌──────────┐
│  Processing │─────►│ SQLite   │
│   Logic     │      │ Database │
└──────┬──────┘      └──────────┘
       │
┌──────▼──────┐
│   Local     │
│ Filesystem  │
└─────────────┘
```

### Web Architecture
```
┌─────────────┐
│ Web Browser │
└──────┬──────┘
       │ HTTP
┌──────▼──────┐      ┌──────────┐
│ PHP         │─────►│PostgreSQL│
│ Frontend    │      │ Database │
└──────┬──────┘      └──────────┘
       │ HTTP
┌──────▼──────┐      ┌──────────┐
│  FastAPI    │─────►│  Redis   │
│  Backend    │      │  Queue   │
└──────┬──────┘      └──────────┘
       │
┌──────▼──────┐      ┌──────────┐
│   Celery    │─────►│  MinIO   │
│   Workers   │      │ Storage  │
│  (Legacy    │      └──────────┘
│   Logic)    │
└─────────────┘
```

## Feature Parity Matrix

| Feature | Desktop | Web | Status |
|---------|---------|-----|--------|
| **Evidence Ingestion** |
| WhatsApp HTML | ✅ | ✅ | ✅ Preserved |
| WhatsApp PDF | ✅ | ✅ | ✅ Preserved |
| SMS/Text Messages | ✅ | ✅ | ✅ Preserved |
| Call Logs | ✅ | ✅ | ✅ Preserved |
| Emails | ✅ | ✅ | ✅ Preserved |
| Audio Transcription | ✅ | ✅ | ✅ Preserved |
| Image OCR | ✅ | ✅ | ✅ Preserved |
| GPS/EXIF Extraction | ✅ | ✅ | ✅ Preserved |
| **Processing** |
| Categorization | ✅ | ✅ | ✅ Preserved |
| Attachment Linking | ✅ | ✅ | ✅ Preserved |
| Deduplication | ✅ | ✅ | ✅ Preserved |
| **Analysis** |
| Timeline View | ✅ | ✅ | ✅ Reimplemented |
| Network Graph | ✅ | ✅ | ✅ Reimplemented |
| GPS Map | ✅ | ✅ | ✅ Reimplemented |
| Search | ✅ | ✅ | ✅ Improved |
| Filtering | ✅ | ✅ | ✅ Improved |
| **Collaboration** |
| Multi-user | ❌ | ✅ | 🆕 New Feature |
| Role-based Access | ❌ | ✅ | 🆕 New Feature |
| Audit Logging | ❌ | ✅ | 🆕 New Feature |
| Concurrent Processing | ❌ | ✅ | 🆕 New Feature |

## Benefits of Web Architecture

### For Users
1. **Accessibility**: Access from any device with a browser
2. **Collaboration**: Multiple analysts can work on the same case
3. **No Installation**: No desktop software to install/update
4. **Consistent Experience**: Same UI across all devices

### For Operations
1. **Centralized Management**: Single deployment to update all users
2. **Scalability**: Add more workers to handle load
3. **Monitoring**: Centralized logging and metrics
4. **Security**: Centralized authentication and audit logging

### For Development
1. **Code Reuse**: 70% of logic preserved
2. **Maintainability**: Clear separation of concerns
3. **Testing**: Easier to test API endpoints
4. **Deployment**: Automated deployment pipelines

## Migration Checklist

- [x] Preserve all parser modules
- [x] Preserve OCR logic
- [x] Preserve categorization engine
- [x] Migrate database schema (SQLite → PostgreSQL)
- [x] Replace Qt UI with PHP web frontend
- [x] Replace local storage with MinIO
- [x] Adapt progress reporting
- [x] Wrap processing as Celery tasks
- [x] Implement authentication (Keycloak)
- [x] Add multi-user support
- [x] Add audit logging
- [x] Create deployment artifacts
- [x] Write comprehensive documentation

## Known Limitations and Future Work

### Current Limitations
1. **Real-time Updates**: Uses polling instead of WebSocket (acceptable for v1)
2. **Audio Transcription**: May be slow for large files (consider dedicated worker queue)
3. **Large File Uploads**: Limited by PHP/Apache settings (configurable)

### Future Enhancements
1. WebSocket support for real-time progress
2. Bulk operations on communications
3. Advanced search with query builder
4. Export to additional formats
5. Integration with other forensic tools
6. Machine learning for improved categorization

## Conclusion

The migration successfully transformed a single-user desktop application into a scalable, multi-user web application while preserving the core processing logic that makes the forensic toolkit valuable. The web architecture provides better collaboration, accessibility, and maintainability without sacrificing functionality.

**Key Achievement**: Over 70% of the proven processing logic was preserved, reducing risk and development time while gaining the benefits of a modern web architecture.
