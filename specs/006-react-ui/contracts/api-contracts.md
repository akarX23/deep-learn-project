# Contracts: React Web UI for AI Tutor

**Phase**: Phase 1 — Design
**Feature**: `specs/006-react-ui`
**Date**: 2026-06-18

This document defines the interface contracts between the React SPA and the existing Python backend. The SPA is a pure consumer — it does not expose an API; it only calls backend endpoints and subscribes to backend WebSocket events.

UI refresh note: this iteration updates frontend presentation and stream handling boundaries (direct stream updates in `StreamResponseBox`) without changing endpoint or event names.

---

## REST API Contract

### POST /api/chat/request

**Direction**: React SPA → Python FastAPI backend
**Content-Type**: `multipart/form-data` (browser-set with boundary)

#### Request Fields

| Field | Type | Required | Constraint |
|---|---|---|---|
| `user_prompt` | form string | Yes | Non-empty |
| `sid` | form string | Yes | Socket.IO session ID obtained on connection |
| `user_level` | repeated form string | No | Default `[]`; repeated keys for list encoding |
| `files` | file upload(s) | No | PDF only, max 3, each ≤ 20 MB |

#### Success Response

```
HTTP 200 OK
Content-Type: application/json
{ "request_id": "<uuid>", ... }
```

#### Error Responses

| Status | Condition |
|---|---|
| 400 | Invalid `UserRequest` payload (e.g., empty `user_prompt`) |
| 422 | FastAPI validation error |
| 500 | Internal server error |

**Client handling**: On non-2xx response, display an error message in the chat area. Do not retry automatically.

**Client rendering note**: User message rendering may include local `attachments` metadata (filename chips) derived from submitted files. This is a frontend-only view model and does not alter request/response payloads.

---

## WebSocket (Socket.IO) Contract

### Connection

| Parameter | Value |
|---|---|
| Server URL | `VITE_WS_URL` environment variable |
| Protocol | Socket.IO v4 (polling + WebSocket upgrade) |
| Reconnection | Enabled; max 5 attempts; 1s–5s delay |

**On connect**: Capture `socket.id` and store as `sid` for all subsequent REST requests.

---

### Event: `stream-tokens-skt` (inbound)

**Direction**: Backend → React SPA
**Emitted by**: `backend_service` (forwarded from Kafka `stream-tokens` topic)

#### Payload (`StreamTokensEventBody`)

```typescript
{
  from_service: string;          // e.g., "teaching-agent"
  sid: string;                   // Target browser session ID
  data: {
    token?: string;              // Text fragment to append (streaming packets)
    done?: boolean;              // Explicit stream completion marker
    tokens_used?: number;        // Optional completion usage metric
    [key: string]: any;          // Other agent-specific fields (ignored in this iteration)
  };
}
```

**Routing rule**: If `from_service === "teaching-agent"`, process stream in `StreamResponseBox`; otherwise, discard silently.

**Completion rule**: Stream completion occurs only when `data.done === true`.

**Usage rule**: If `data.tokens_used` is provided on completion payload, render it as a small secondary line beneath the related stream response.

**Progress placeholder compatibility**: Placeholder text can remain static; no dedicated progress event fields are required in this iteration.

---

### Event: `clarify-user-level-skt` (inbound)

**Direction**: Backend → React SPA
**Emitted by**: `backend_service` (forwarded from planner agent)

#### Payload (`ClarifyUserLevelEvent`)

```typescript
{
  request_id: string;
  user_prompt: string;
  sid: string;
  reason?: string;
}
```

**Handling**: Display `reason` (or a generic clarification message if absent) as an assistant info bubble in the chat history.

---

## Environment Variable Contract

All variables must be present in the runtime environment before the app initialises. Missing variables throw a startup error (caught in `src/config.ts`).

| Variable | Example (dev) | Example (prod) | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | `https://api.example.com` | FastAPI backend base URL |
| `VITE_WS_URL` | `http://localhost:8000` | `https://api.example.com` | Socket.IO server URL |

All variables must be present in `.env.example` (committed to repository) with placeholder values.

---

## Non-Breaking Guarantee

- No new required request fields.
- No renamed event names.
- No renamed payload fields.
- Existing backend implementations remain compatible; completion metadata (`done`, `tokens_used`) is interpreted when present.
