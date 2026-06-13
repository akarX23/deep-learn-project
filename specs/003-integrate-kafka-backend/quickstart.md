# Quickstart: Backend Kafka Bootstrap + RAG Test-Event API

## 1. Install dependencies

```bash
pip install -r requirements.txt
```

## 2. Configure environment

Set Kafka runtime settings in `.env.local`:

```env
BACKEND_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
BACKEND_KAFKA_CLIENT_ID=backend-service
BACKEND_KAFKA_STARTUP_RETRY_COUNT=5
BACKEND_KAFKA_STARTUP_RETRY_TIMEOUT_SECONDS=2
APP_ENV=dev
BACKEND_ENABLE_TEST_EVENT_APIS=true
```

Optional secure-cluster settings:

```env
BACKEND_KAFKA_SECURITY_PROTOCOL=
BACKEND_KAFKA_SASL_MECHANISM=
BACKEND_KAFKA_SASL_USERNAME=
BACKEND_KAFKA_SASL_PASSWORD=
BACKEND_KAFKA_SSL_CAFILE=
```

## 3. Start local Kafka infrastructure

```bash
docker compose up -d kafka kafka-ui
```

Wait until Kafka is ready (typically under 30 seconds):

```bash
docker compose logs kafka | grep "Kafka Server started"
```

## 4. Run backend service

```bash
python -m backend_service.app.main
```

Expected startup output:

```
INFO  Kafka admin connect attempt 1/6
INFO  Kafka admin connected
INFO  Bootstrapping Kafka topics: ['rag', 'rag-complete']
DEBUG Topic created: rag
DEBUG Topic created: rag-complete
INFO  Topic bootstrap complete: 2 created, 0 already existed, 0 errors
```

On subsequent startups (topics already exist):

```
INFO  Bootstrapping Kafka topics: ['rag', 'rag-complete']
DEBUG Topic already exists: rag
DEBUG Topic already exists: rag-complete
INFO  Topic bootstrap complete: 0 created, 2 already existed, 0 errors
```

## 5. Verify topics in Kafka UI

Open http://localhost:8080 and confirm `rag` and `rag-complete` appear in the Topics list.

## 6. Publish rag test event (default payload)

```bash
curl -s -X POST http://localhost:8001/api/v1/test-events/rag \
	-H "Content-Type: application/json" \
	-d '{
		"request_id": "test-req-123",
		"session_ctx": {"mode": "quick"},
		"user_request": "Summarize gradient descent",
		"file_paths": ["rag_agent/tests/inputs/sample.pdf"],
		"created_at": null,
		"source": "backend-service"
	}'
```

Expected successful response shape:

```json
{
	"request_id": "test-...",
	"topic": "rag",
	"publish_status": "published",
	"metadata": {
		"partition": 0,
		"offset": 42,
		"timestamp": 1781234567890
	}
}
```

If broker metadata is not fully available, fields may be `null` while publish remains successful.

## 7. Use the default input factory from utils.py

The `default_rag_test_event()` factory in `backend_service/app/utils.py` returns a fully initialized `RAGRequestEvent` with a fresh `uuid4`-based `request_id` and representative defaults:

```python
from backend_service.app.utils import default_rag_test_event

event = default_rag_test_event()
print(event.request_id)   # e.g. "test-4a7f9c..."
print(event.user_request) # "Summarize gradient descent for local integration testing."
```

To publish a test event using the factory defaults:

```bash
curl -s -X POST http://localhost:8001/api/v1/test-events/rag \
	-H "Content-Type: application/json" \
	-d '{
		"request_id": "test-req-456",
		"session_ctx": {"source": "backend-service", "mode": "integration-test"},
		"user_request": "Summarize gradient descent for local integration testing.",
		"file_paths": ["rag_agent/tests/inputs/sample.pdf"],
		"created_at": null,
		"source": "backend-service"
	}'
```

## 8. Environment gating behavior
- Request body is the complete `RAGRequestEvent` object.
- Schema defaults are applied where fields are omitted.
- Final payload is validated against `RAGRequestEvent` before publish.

## 8a. Connect to the WebSocket channel (Socket.IO)

The backend mounts a Socket.IO server on the FastAPI app. The frontend connects as a Socket.IO client and is assigned a `sid`, which IS the application `session_id`.

```python
import socketio

sio = socketio.Client()

@sio.on("stream-tokens")
def on_stream_tokens(data):
    print("stream-tokens:", data)

sio.connect("http://localhost:8001")
print("session_id (sid):", sio.sid)
sio.wait()
```

Shared event contracts (names + body schemas) live in `project/events.py` and are importable by both frontend and backend:

```python
from project.events import StreamTokensEventBody, WebSocketEvents

print(WebSocketEvents.STREAM_TOKENS.value)  # "stream-tokens"
payload = StreamTokensEventBody(
	from_service="rag-agent",
	content="hello",
	metadata={"index": 1, "done": False},
)
```

## 8b. Emit an event to a session from the backend

From backend code, route a payload to a specific session via its `session_id` (== `sid`):

```python
from backend_service.app.socket import emit_event
from project.events import WebSocketEvents, StreamTokensEventBody

payload = StreamTokensEventBody(
	from_service="rag-agent",
	content="hello",
	metadata={"index": 1, "done": False},
)

await emit_event(WebSocketEvents.STREAM_TOKENS, payload.model_dump(), session_id)
```

## 8c. Use the shared `UserRequest` schema

The backend request contract includes `UserRequest` in `project/schemas.py`:

```python
from project.schemas import UserRequest

req = UserRequest(
	user_prompt="Explain gradient descent simply",
	user_level=["beginner"],
	file_data={"files": ["notes.pdf"]},
	sid="abc123",
)
```

No additional custom validation or exception handling is required for this schema in the current iteration.

> Note: Listener bodies and the full `stream-tokens` emission flow are lightweight stubs in this iteration; edge cases (disconnect cleanup, missing session, auth, back-pressure) are marked TODO.

## 9. Run tests

```bash
.venv/bin/python -m pytest backend_service/tests/ -q
```

## 10. Quality checks

```bash
.venv/bin/ruff check project backend_service
.venv/bin/ruff format --check project backend_service
.venv/bin/python -m compileall project backend_service
```

## 11. Performance notes

- Topic bootstrap step target: ≤5 seconds against a local Kafka cluster (SC-003).
- Test-event API target: ≤2 seconds p95 for single-request local publish/ack path.
- Bootstrap time is O(n) over topic count — currently 2 topics, well within budget.

## 12. Adding new topics

1. Add the topic to the appropriate enum in `project/topics.py`.
2. If needed, add a new getter function and include it in `get_all_topic_names()`.
3. Restart the backend service — the new topic will be created on next startup automatically.
4. Add a topic-specific test-event route and response contract entry if test publish support is required.
