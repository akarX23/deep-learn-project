# Contract: User-Request Ingestion API

**Endpoint**: `POST /api/chat/request`  
**Content-Type**: `multipart/form-data`  
**Feature**: User Story 3 (Priority: P3) — Ingest User Requests with File Uploads and Route to Planner

## Request Contract

### Request Body

The endpoint accepts `multipart/form-data` with:

1. **JSON Field**: `request` (serialized JSON containing `UserRequest` schema)
2. **File Fields**: 0–3 files uploaded as `files[]` (multipart upload)

### `UserRequest` Schema (JSON payload)

```json
{
  "user_prompt": "string (non-empty)",
  "user_level": ["string", "..."],
  "file_data": null,
  "sid": "string (session id)"
}
```

| Field | Type | Constraint | Description |
|-------|------|-----------|-------------|
| `user_prompt` | string | non-empty | End-user query text |
| `user_level` | list[string] | (none) | User experience level labels |
| `file_data` | any | nullable | Placeholder for file metadata; currently ignored |
| `sid` | string | non-empty | Session identifier for response routing |

### File Upload Constraints

- **Max files per request**: 3 (if exceeded, log warning but do not reject)
- **File field name**: `files[]` (multipart array)
- **File naming**: Any name allowed; absolute path is computed on save
- **No advanced validation**: File type, size checks are deferred

### Example Request

```bash
curl -X POST http://localhost:8000/api/chat/request \
  -F 'request={"user_prompt":"Explain neural networks","user_level":["beginner"],"file_data":null,"sid":"session-123"}' \
  -F 'files[]=@document1.pdf' \
  -F 'files[]=@document2.txt'
```

## Response Contract

### Success Response (200 OK)

```json
{
  "message": "Request accepted and queued for planner processing"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | Confirmation that request has been accepted |

### Validation Failure Response (400 Bad Request)

```json
{
  "error": "string (error description)"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Validation error message (e.g., missing/invalid `UserRequest` fields) |

### Server Error Response (500 Internal Server Error)

```json
{
  "error": "string (error description)"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Server error message (e.g., file save failed, Kafka publish failed) |

## Implementation Notes

### File Handling

1. Files are saved to directory specified by `UPLOAD_DIR` environment variable (default: `./uploads`).
2. Absolute paths are computed and passed to the `PlannerRequestEvent`.
3. Files are retained indefinitely (cleanup deferred to future iterations).

### Kafka Publishing

1. After files are successfully saved, a `PlannerRequestEvent` is published to topic `planner`.
2. `PlannerRequestEvent` schema:
   - `user_prompt`: copied from request
   - `user_level`: copied from request
   - `sid`: copied from request
   - `file_paths`: list of absolute paths to saved files

### Error Handling

- **Validation errors**: Return 400 with simple error message.
- **File save failure**: Return 500 with error message; files that were saved remain in uploads directory.
- **Kafka publish failure**: Return 500 with error message; files remain in uploads directory.
- **Excess files (>3)**: Log warning, but do not reject request.

## Contract Guarantees

1. **Idempotency**: Not guaranteed in this iteration; repeated requests with the same payload create duplicate files and events.
2. **Atomicity**: Not guaranteed; Kafka publish may fail even if files are saved.
3. **Ordering**: Publish order is not guaranteed across concurrent requests.

## Future Enhancements (TODO)

- File type validation (PDF, DOCX, etc.)
- Per-file size limits
- Total upload size limit enforcement (not just warnings)
- Deduplication and cleanup policies
- Request idempotency via correlation IDs
