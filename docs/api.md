# API Documentation

This project exposes a RESTful HTTP API under `/api/` for authentication, change requests, and audit operations.

## Base URL

```
Development: http://localhost:5000/api
Production: https://your-domain.com/api
```

## Authentication

### Health Check
```http
GET /api/auth/ping
```

**Response:**
```json
{
  "ok": true,
  "service": "auth"
}
```

### Verify Credentials
```http
POST /api/auth/verify
Content-Type: application/json

{
  "username": "string",
  "password": "string"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "john.doe",
    "email": "john@example.com",
    "role": "requester"
  }
}
```

**Error Response (401):**
```json
{
  "error": "Invalid credentials"
}
```

## Change Requests

### Health Check
```http
GET /api/change-requests/ping
```

### List Change Requests (TODO)
```http
GET /api/change-requests/
```

### Get Change Request Details (TODO)
```http
GET /api/change-requests/<id>
```

### Create Change Request (TODO)
```http
POST /api/change-requests/
```

## Audit Logs

### Health Check
```http
GET /api/audit/ping
```

### Get Audit Logs (TODO)
```http
GET /api/audit/logs
```

## Security

- All API endpoints require HTTPS in production (TLS 1.2+)
- Authentication endpoints are rate-limited (5 requests per minute)
- All requests are logged in the audit trail
- CSRF protection is enabled for state-changing operations

## Error Responses

All errors follow this format:

```json
{
  "error": "Error message description"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid input)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

