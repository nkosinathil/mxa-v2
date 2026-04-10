# MxA Mobile - API Documentation

## Base URLs

- **Production**: `http://192.168.1.90:8104`
- **Development**: `http://localhost:8104`

## Authentication

All endpoints (except `/health`) require authentication via Bearer token obtained from Keycloak.

```http
Authorization: Bearer <access_token>
```

## Health Endpoints

### GET /health
Basic health check.

**Response**:
```json
{
  "status": "healthy",
  "service": "MxA Mobile Backend",
  "version": "1.0.0"
}
```

### GET /health/ready
Readiness check with dependency validation.

**Response**:
```json
{
  "ready": true,
  "database": true,
  "minio": true,
  "message": "Service is ready"
}
```

## Job Endpoints

### POST /api/jobs
Submit a new processing job.

**Request Body**:
```json
{
  "case_id": 1,
  "case_number": "CASE-001",
  "modes": ["whatsapp", "texts", "emails"],
  "category_models": ["generic", "energy"],
  "transcribe_audio": true,
  "audio_max_seconds": 600
}
```

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "case_id": 1,
  "status": "queued",
  "message": "Job submitted successfully"
}
```

### GET /api/jobs/{job_id}/status
Get job status and progress.

**Response**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "case_id": 1,
  "status": "processing",
  "progress": 45,
  "current_step": "Analyzing evidence",
  "result": null,
  "error": null,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:23Z"
}
```

**Status Values**:
- `queued` - Waiting to be processed
- `processing` - Currently being processed
- `completed` - Successfully completed
- `failed` - Processing failed

### GET /api/jobs
List all jobs with optional filters.

**Query Parameters**:
- `case_id` (optional) - Filter by case ID
- `status` (optional) - Filter by status
- `limit` (optional, default: 100) - Maximum results

**Response**: Array of job status objects

## Results Endpoints

### GET /api/results/communications
Get communications for a case.

**Query Parameters**:
- `case_id` (required) - Case ID
- `mode` (optional) - Filter by mode (whatsapp, texts, etc.)
- `category` (optional) - Filter by category
- `date_from` (optional) - Start date (YYYY-MM-DD)
- `date_to` (optional) - End date (YYYY-MM-DD)
- `search` (optional) - Search text
- `limit` (optional, default: 100)
- `offset` (optional, default: 0)

**Response**:
```json
[
  {
    "id": 1,
    "mode": "whatsapp",
    "timestamp": "2024-01-15T08:30:00Z",
    "sender": "John Doe",
    "receiver": "Jane Smith",
    "message": "Meeting at 3pm",
    "category": "Personal",
    "attachment_count": 2
  }
]
```

### GET /api/results/attachments
Get attachments for a case.

**Query Parameters**:
- `case_id` (required)
- `communication_id` (optional)
- `file_type` (optional)
- `has_ocr` (optional)
- `has_gps` (optional)
- `limit` (optional)
- `offset` (optional)

**Response**:
```json
[
  {
    "id": 1,
    "communication_id": 1,
    "filename": "image.jpg",
    "file_type": "image/jpeg",
    "found_status": "found",
    "has_ocr": true,
    "has_gps": true
  }
]
```

### GET /api/results/timeline
Get timeline data for visualization.

**Query Parameters**:
- `case_id` (required)

**Response**:
```json
{
  "case_id": 1,
  "timeline": [
    {
      "date": "2024-01-15",
      "count": 45,
      "modes": {
        "whatsapp": 20,
        "texts": 15,
        "emails": 10
      }
    }
  ]
}
```

### GET /api/results/network
Get network visualization data.

**Query Parameters**:
- `case_id` (required)

**Response**:
```json
{
  "case_id": 1,
  "network": {
    "nodes": [
      {"id": "john", "label": "John Doe", "type": "person"},
      {"id": "jane", "label": "Jane Smith", "type": "person"}
    ],
    "edges": [
      {"source": "john", "target": "jane", "weight": 45}
    ]
  }
}
```

### GET /api/results/gps
Get GPS data for map visualization.

**Query Parameters**:
- `case_id` (required)

**Response**:
```json
{
  "case_id": 1,
  "gps_points": [
    {
      "lat": -26.2041,
      "lon": 28.0473,
      "timestamp": "2024-01-15T08:30:00Z",
      "attachment_id": 1,
      "filename": "photo.jpg"
    }
  ]
}
```

## Case Endpoints

### GET /api/cases/{case_id}
Get case details.

**Response**:
```json
{
  "id": 1,
  "case_number": "CASE-001",
  "case_name": "Investigation Alpha",
  "description": "Case description",
  "status": "active",
  "created_at": "2024-01-15T10:00:00Z"
}
```

### GET /api/cases
List all cases.

**Query Parameters**:
- `status` (optional) - Filter by status
- `limit` (optional, default: 100)

**Response**: Array of case objects

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

**HTTP Status Codes**:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## Rate Limiting

Currently not implemented. May be added in future versions.

## Pagination

List endpoints support pagination via `limit` and `offset` parameters.

Example:
```
GET /api/results/communications?case_id=1&limit=50&offset=100
```

## Future API Additions

Planned for future versions:
- WebSocket endpoint for real-time updates
- Bulk operations endpoints
- Advanced search with query DSL
- Export endpoints (PDF, CSV, JSON)
- Tag management endpoints
- Statistics and analytics endpoints
