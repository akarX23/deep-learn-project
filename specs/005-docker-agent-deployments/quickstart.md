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

## 6. Verify restart behavior (smoke)
1. Stop one in-scope container abruptly.
2. Re-run `docker compose ps`.
Expected result: service attempts automatic restart per compose restart policy.

## 7. Stop the stack
```bash
docker compose down
```

## Notes
- Healthchecks are intentionally out of scope for this feature.
- Service names in commands must match the compose service keys implemented in this feature.
