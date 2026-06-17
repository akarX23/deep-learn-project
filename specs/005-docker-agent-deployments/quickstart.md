# Quickstart: Docker Agent Deployments

## Prerequisites
- Docker engine installed and running
- Docker Compose CLI available
- Repository cloned locally
- `.env.local` populated with runtime values, including `UI_WEBSOCKET_URL`, `UI_BACKEND_URL`, and optionally `UI_SIMULATOR_ENABLED`

## 1. Validate compose configuration
```bash
docker compose config
```
Expected result: configuration renders without errors.

## 2. Build all in-scope application services
```bash
docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent ui-frontend
```
Expected result: all images build successfully.

## 3. Build one service independently
```bash
docker compose build ui-frontend
```
Expected result: only the selected service image is rebuilt.

Timing note for SC-004: each targeted service build should complete in under 3 minutes on a standard development machine.

### Per-service independent build matrix

```bash
docker compose build backend-service
docker compose build orchestrator-agent
docker compose build planner-agent
docker compose build rag-agent
docker compose build teaching-agent
docker compose build quiz-agent
docker compose build ui-frontend
```
Expected result: each command rebuilds only the selected service image.

## 4. Start full local stack
```bash
docker compose up -d
```
Expected result: infrastructure and in-scope application services start from one command.

## 5. Verify running services
```bash
docker compose ps
```
Expected result: all in-scope services show running or restarting states according to policy.

## 6. Verify healthchecks and dependency gating

```bash
docker compose ps kafka backend-service
```
Expected result: both services report healthy status.

```bash
docker compose ps orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent ui-frontend
```
Expected result: agent services start only after `kafka` and `backend-service` are healthy, and `ui-frontend` starts only after `backend-service` is healthy.

## 7. Verify UI frontend reachability

1. Open the frontend URL in a browser after the stack starts.
2. Confirm the Streamlit app renders.
3. If required env vars are missing, confirm the app shows a visible configuration error.

Expected result: the Streamlit UI loads and uses the compose-provided environment variables.

## 8. Verify shared uploads volume path contract

1. Ensure backend and RAG containers both mount the shared uploads location.
2. Write a test file via backend upload flow.
3. Confirm RAG can resolve and read the same path.

Expected result: backend-emitted upload paths are directly readable by RAG.

## 9. Verify restart behavior (smoke)
1. Stop one in-scope container abruptly.
2. Re-run `docker compose ps`.

Expected result: service attempts automatic restart per compose restart policy.

## 10. Verify Kafka logger level policy

Inspect service startup code for each Kafka-using service and confirm:

```python
logging.getLogger("kafka").setLevel(logging.WARNING)
```

Expected result: all in-scope Kafka-using services configure Kafka logger level to warning.

## 11. Verify LiteLLM logger level policy

Inspect service startup code for each LiteLLM-using service and confirm:

```python
logging.getLogger("LiteLLM").setLevel(logging.WARNING)
```

Expected result: all in-scope LiteLLM-using services configure LiteLLM logger level to warning.

## 12. Validation notes

- Compose schema/rendering validation:
	- `docker compose config` must render successfully.
- Full build validation:
	- `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent ui-frontend` must complete.
- Targeted build validation:
	- Any single command from the build matrix must rebuild only that service.
- Runtime smoke validation:
	- `docker compose up -d` followed by `docker compose ps` shows all in-scope services as running or restarting.
- Healthcheck/dependency validation:
	- `kafka` and `backend-service` report healthy status.
	- Agent services declare and honor dependency links to both healthy services.
	- `ui-frontend` declares and honors dependency on healthy `backend-service`.
- UI validation:
	- Browser access to the Streamlit frontend succeeds after stack startup.
	- Missing UI env vars surface a visible configuration failure.
- Shared uploads validation:
	- Backend and RAG share uploads volume mapping.
	- Backend-produced upload paths are readable by RAG.
- Kafka logging validation:
	- Kafka logger level is set to warning in each Kafka-using service.
- LiteLLM logging validation:
	- LiteLLM logger level is set to warning in each LiteLLM-using service.
- Restart policy validation:
	- Stopping one in-scope container triggers restart attempt (`restart: unless-stopped`).

### Latest validation evidence

- Validation run date: 2026-06-17
- `docker compose config`: passed (`compose_config_ok`).
- Full backend/agent build: `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent` passed; all six images reported `Built`.
- Full build including frontend: `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent ui-frontend` passed; all seven images reported `Built`.
- Per-service build matrix: individual `docker compose build <service>` commands passed for `backend-service`, `orchestrator-agent`, `planner-agent`, `rag-agent`, `teaching-agent`, `quiz-agent`, and `ui-frontend`.
- Targeted frontend build: `docker compose build ui-frontend` passed (`deep-learn/ui-frontend:local` built).
- Full stack startup: `docker compose up -d` passed; containers for `planner-agent` and `ui-frontend` were created and started.
- Runtime status check: `docker compose ps kafka backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent ui-frontend` showed `kafka` and `backend-service` healthy and all in-scope application services `Up`.
- UI reachability check: `curl http://localhost:8501` returned HTTP `200`.
- UI env failure-mode check: running `UIConfig.from_env()` with `UI_BACKEND_URL` unset returned `EXPECTED_BACKEND_URL_ERROR: UI_BACKEND_URL is required`.
- Restart smoke check: after `kill -9 1` inside `planner-agent`, `docker compose ps planner-agent` showed the service recovered to `Up`.
- Kafka logger audit: grep matched warning-level configuration in `backend_service/app/main.py`, `orchestrator_agent/worker.py`, `planner_agent/worker.py`, `rag_agent/worker.py`, `teaching_agent/worker.py`, `quiz_agent/agent.py`, and `quiz_agent/worker.py`.
- LiteLLM logger audit: grep matched warning-level configuration in `orchestrator_agent/worker.py`, `planner_agent/worker.py`, `rag_agent/worker.py`, `teaching_agent/worker.py`, `quiz_agent/agent.py`, and `quiz_agent/worker.py`.

## 13. Stop the stack
```bash
docker compose down
```

## Notes
- Healthchecks are required for `kafka` and `backend-service`.
- Shared uploads volume mapping between backend and RAG is required.
- Kafka logger warning-level policy is required for Kafka-using services.
- UI frontend env vars are required at runtime and should be documented in `.env.local.example` during implementation.
- Service names in commands must match the compose service keys implemented in this feature.
