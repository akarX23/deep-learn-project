# Quickstart: Docker Agent Deployments

## Prerequisites
- Docker engine installed and running
- Docker Compose CLI available
- Repository cloned locally

## 1. Validate compose configuration
```bash
docker compose config
```
Expected result: configuration renders without errors.

## 2. Build all in-scope application services
```bash
docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent
```
Expected result: all images build successfully.

## 3. Build one service independently
```bash
docker compose build planner-agent
```
Expected result: only planner-agent image is rebuilt.

### Per-service independent build matrix

```bash
docker compose build backend-service
docker compose build orchestrator-agent
docker compose build planner-agent
docker compose build rag-agent
docker compose build teaching-agent
docker compose build quiz-agent
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
docker compose ps orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent
```
Expected result: agent services start only after `kafka` and `backend-service` are healthy.

## 7. Verify shared uploads volume path contract

1. Ensure backend and RAG containers both mount the shared uploads location.
2. Write a test file via backend upload flow.
3. Confirm RAG can resolve and read the same path.

Expected result: backend-emitted upload paths are directly readable by RAG.

## 8. Verify restart behavior (smoke)
1. Stop one in-scope container abruptly.
2. Re-run `docker compose ps`.
Expected result: service attempts automatic restart per compose restart policy.

## 9. Verify Kafka logger level policy

Inspect service startup code for each Kafka-using service and confirm:

```python
logging.getLogger("kafka").setLevel(logging.WARNING)
```

Expected result: all in-scope Kafka-using services configure Kafka logger level to warning.

## 10. Validation notes

- Compose schema/rendering validation:
	- `docker compose config` must render successfully.
- Full build validation:
	- `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent` must complete.
- Targeted build validation:
	- Any single command from the build matrix must rebuild only that service.
- Runtime smoke validation:
	- `docker compose up -d` followed by `docker compose ps` shows all in-scope services as running or restarting.
- Healthcheck/dependency validation:
	- `kafka` and `backend-service` report healthy status.
	- Agent services declare and honor dependency links to both healthy services.
- Shared uploads validation:
	- Backend and RAG share uploads volume mapping.
	- Backend-produced upload paths are readable by RAG.
- Kafka logging validation:
	- Kafka logger level is set to warning in each Kafka-using service.
- Restart policy validation:
	- Stopping one in-scope container triggers restart attempt (`restart: unless-stopped`).

### Latest validation evidence (2026-06-15)

- `docker compose config`: passed (compose renders with service_healthy dependency conditions).
- `docker compose build backend-service orchestrator-agent planner-agent rag-agent teaching-agent quiz-agent`: passed.
- `docker compose build planner-agent`: passed (targeted build).
- `docker compose up -d`: passed; `kafka` and `backend-service` reached `healthy`.
- `docker compose ps`: confirmed agent services running after healthy dependencies.
- `grep -n "healthcheck:" docker-compose.yaml`: two entries (kafka, backend-service).
- `grep -n "condition: service_healthy" docker-compose.yaml`: health-aware dependency links present for kafka-ui and all in-scope agent services.
- Restart smoke: `docker compose exec -T planner-agent sh -lc "kill -9 1"` followed by `docker compose ps planner-agent` confirmed container recovered to `Up`.

## 11. Stop the stack
```bash
docker compose down
```

## Notes
- Healthchecks are required for `kafka` and `backend-service`.
- Shared uploads volume mapping between backend and RAG is required.
- Kafka logger warning-level policy is required for Kafka-using services.
- Service names in commands must match the compose service keys implemented in this feature.
