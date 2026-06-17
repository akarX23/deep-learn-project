# Quickstart: UI Frontend WebSocket Integration

## 1. Environment setup

Set required environment variables (example values):

```env
UI_WEBSOCKET_URL=ws://localhost:8001/ws/events
UI_SIMULATOR_ENABLED=true
BACKEND_WS_ENABLED=true
BACKEND_WS_PATH=/ws/events
```

Notes:
- Frontend reads WebSocket endpoint from environment.
- Backend relay and frontend URL must point to the same path.

## 2. Install dependencies

From repository root:

```bash
pip install -r requirements.txt
```

If Streamlit is not yet present in `requirements.txt`, add and install it in the implementation phase.

## 3. Run backend relay service

```bash
python -m backend_service.app.main
```

Expected behavior:
- Service starts with existing lifespan Kafka startup logic.
- WebSocket relay endpoint is available when `BACKEND_WS_ENABLED=true`.

## 4. Run Streamlit UI

Example command (path depends on final implementation module):

```bash
streamlit run ui_frontend/app.py
```

Expected behavior:
- UI attempts websocket connection automatically.
- Connection state indicator shows lifecycle transitions.
- Chat, Quiz, Evaluation tabs and Status panel are visible.

## 5. Validate simulator flow

In UI:
1. Enable simulator mode.
2. Run happy-path scenario.
3. Confirm event routing:
   - teaching events -> Chat
   - planner status -> Status panel
   - quiz events -> Quiz
   - evaluation events -> Evaluation

## 6. Run tests

```bash
pytest -q
```

Target coverage for this feature:
- Schema validation tests for all event families.
- Routing matrix tests for supported and unknown event types.
- Reconnection transition tests.
- Stream token ordering/dedup tests.
- Backend relay integration tests.

## 7. Manual acceptance checks

- Disconnect network/backend and confirm reconnect attempt starts within 2 seconds.
- Replay interleaved planner/teaching/quiz/evaluation events and verify UI remains stable.
- Inject unknown event type and verify diagnostics capture without crash.
- Verify 95% event visibility within 1 second under representative local load.
