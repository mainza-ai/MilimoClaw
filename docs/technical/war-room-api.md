# War Room API Specification

**Version:** 1.0
**Date:** March 18, 2026
**Author:** Milimo Claw Team

---

## Overview

This document defines the REST and WebSocket API for the War Room, enabling mobile app integration for approve/veto actions from anywhere.

---

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Mobile App     │────▶│  War Room Server │────▶│   Milimo Claw    │
│  (React Native)  │     │  (Fastify/Express)│     │   (CLI/Python)   │
└──────────────────┘     └──────────────────┘     └──────────────────┘
        │                        │                        │
        │    REST/WebSocket      │    IPC/File            │
        └────────────────────────┴────────────────────────┘
```

---

## Authentication

### JWT Token Authentication

All API requests require a valid JWT token in the `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

### Token Generation

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "squad_id": "my-squad",
  "device_id": "device-uuid",
  "biometric_verified": true
}

Response:
{
  "token": "eyJhbGciOiJSUzI1NiIs...",
  "refresh_token": "refresh_token_here",
  "expires_in": 3600
}
```

### Token Refresh

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "refresh_token_here"
}
```

---

## REST API

### Pending Actions

#### List Pending Actions

```http
GET /api/v1/pending
Authorization: Bearer <token>

Response:
{
  "items": [
    {
      "id": "action-uuid",
      "type": "auto_approval",
      "claw_role": "content",
      "action_type": "send_email",
      "description": "Send follow-up email to client@example.com",
      "payload": {
        "to": "client@example.com",
        "subject": "Project Update"
      },
      "confidence": 0.85,
      "risk_level": "low",
      "created_at": "2026-03-18T10:00:00Z",
      "expires_at": "2026-03-18T11:00:00Z"
    }
  ],
  "total": 1,
  "has_more": false
}
```

#### Get Action Details

```http
GET /api/v1/pending/:id
Authorization: Bearer <token>

Response:
{
  "id": "action-uuid",
  "type": "auto_approval",
  "claw_role": "content",
  "action_type": "send_email",
  "description": "Send follow-up email to client@example.com",
  "payload": { ... },
  "confidence": 0.85,
  "risk_level": "low",
  "created_at": "2026-03-18T10:00:00Z",
  "expires_at": "2026-03-18T11:00:00Z",
  "context": {
    "client": "Acme Corp",
    "project": "Website Redesign",
    "previous_actions": 3
  }
}
```

### Action Decisions

#### Approve Action

```http
POST /api/v1/pending/:id/approve
Authorization: Bearer <token>
Content-Type: application/json

{
  "biometric_verified": true,
  "notes": "Approved during client meeting"
}

Response:
{
  "success": true,
  "action_id": "action-uuid",
  "status": "approved",
  "approved_at": "2026-03-18T10:05:00Z"
}
```

#### Veto Action

```http
POST /api/v1/pending/:id/veto
Authorization: Bearer <token>
Content-Type: application/json

{
  "reason": "Client requested pause on all communications",
  "biometric_verified": true
}

Response:
{
  "success": true,
  "action_id": "action-uuid",
  "status": "vetoed",
  "vetoed_at": "2026-03-18T10:05:00Z"
}
```

### Status

#### Get War Room Status

```http
GET /api/v1/status
Authorization: Bearer <token>

Response:
{
  "squad_id": "my-squad",
  "mesh_status": "healthy",
  "claws_online": 5,
  "pending_count": 3,
  "approved_today": 12,
  "vetoed_today": 2,
  "rate_limit": {
    "used": 5,
    "limit": 10,
    "resets_at": "2026-03-19T00:00:00Z"
  },
  "last_activity": "2026-03-18T10:00:00Z"
}
```

#### Get Claw Health

```http
GET /api/v1/status/claws
Authorization: Bearer <token>

Response:
{
  "claws": [
    {
      "role": "content",
      "status": "online",
      "region": "us-east-1",
      "last_heartbeat": "2026-03-18T10:00:00Z",
      "actions_today": 8
    },
    {
      "role": "ops",
      "status": "online",
      "region": "eu-west-1",
      "last_heartbeat": "2026-03-18T09:59:00Z",
      "actions_today": 5
    }
  ]
}
```

---

## WebSocket API

### Connection

```javascript
const ws = new WebSocket('wss://warroom.milimo.dev/ws', {
  headers: {
    'Authorization': 'Bearer <token>'
  }
});
```

### Events

#### Subscribe to Pending Actions

```json
{
  "type": "subscribe",
  "channel": "pending"
}
```

#### New Pending Action Event

```json
{
  "type": "pending:new",
  "data": {
    "id": "action-uuid",
    "type": "auto_approval",
    "description": "Send follow-up email...",
    "risk_level": "low",
    "created_at": "2026-03-18T10:00:00Z"
  }
}
```

#### Action Resolved Event

```json
{
  "type": "pending:resolved",
  "data": {
    "id": "action-uuid",
    "status": "approved",
    "resolved_at": "2026-03-18T10:05:00Z",
    "resolved_by": "mobile:user-uuid"
  }
}
```

#### Heartbeat

```json
// Client sends
{
  "type": "ping"
}

// Server responds
{
  "type": "pong",
  "timestamp": "2026-03-18T10:00:00Z"
}
```

---

## Push Notifications

### Firebase Cloud Messaging (FCM)

```json
{
  "to": "device_token",
  "notification": {
    "title": "Action Requires Approval",
    "body": "Content claw wants to send an email to client@example.com"
  },
  "data": {
    "action_id": "action-uuid",
    "type": "pending_action",
    "risk_level": "high"
  },
  "android": {
    "priority": "high"
  },
  "apns": {
    "payload": {
      "aps": {
        "sound": "default",
        "badge": 1
      }
    }
  }
}
```

### Notification Types

| Type | Title Template | Priority |
|------|----------------|----------|
| `pending_action` | "Action Requires Approval" | High (if risk_level=high) |
| `action_approved` | "Action Approved" | Normal |
| `action_vetoed` | "Action Vetoed" | Normal |
| `claw_offline` | "Claw Offline" | High |
| `rate_limit_warning` | "Rate Limit Warning" | High |

---

## Rate Limiting

### API Rate Limits

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/api/v1/pending` | 100 | 1 minute |
| `/api/v1/pending/:id/approve` | 20 | 1 minute |
| `/api/v1/pending/:id/veto` | 20 | 1 minute |
| WebSocket connections | 5 | per device |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1710763200
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Invalid or expired token",
    "details": {
      "token_expired": true
    }
  },
  "request_id": "req-uuid"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_FAILED` | 401 | Invalid/expired token |
| `AUTHORIZATION_FAILED` | 403 | Not authorized for squad |
| `ACTION_NOT_FOUND` | 404 | Action ID doesn't exist |
| `ACTION_EXPIRED` | 410 | Action already expired |
| `ACTION_RESOLVED` | 409 | Action already approved/vetoed |
| `RATE_LIMITED` | 429 | Too many requests |
| `BIOMETRIC_REQUIRED` | 403 | Biometric verification required |

---

## Security

### TLS Requirements

- TLS 1.3 required for all connections
- HSTS enabled with 1-year max-age
- Certificate pinning recommended for mobile apps

### Biometric Authentication

For high-risk actions, biometric verification is required:

```json
{
  "type": "approve",
  "action_id": "action-uuid",
  "biometric_verified": true,
  "biometric_type": "face_id"
}
```

### Audit Logging

All actions are logged with:
- Timestamp
- User ID
- Device ID
- Action type
- IP address
- Biometric verification status

---

## Implementation Notes

### Offline Queue

Mobile app should queue decisions when offline:
1. Store approve/veto decisions locally
2. Sync when connection restored
3. Handle conflicts (action may have expired)

### Push Notification Handling

1. Display notification
2. Update app badge count
3. Deep link to action details
4. Handle notification tap

### WebSocket Reconnection

Exponential backoff with jitter:
- Initial: 1s
- Max: 30s
- Jitter: ±500ms
