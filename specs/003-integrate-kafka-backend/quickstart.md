# Quickstart: Backend Kafka Startup Topic Bootstrap

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

## 6. Run tests

```bash
.venv/bin/python -m pytest backend_service/tests/ -q
```

## 7. Quality checks

```bash
.venv/bin/ruff check project backend_service
.venv/bin/ruff format --check project backend_service
.venv/bin/python -m compileall project backend_service
```

## 8. Performance notes

- Topic bootstrap step target: ≤5 seconds against a local Kafka cluster (SC-003).
- Bootstrap time is O(n) over topic count — currently 2 topics, well within budget.

## 9. Adding new topics

1. Add the topic to the appropriate enum in `project/topics.py`.
2. If needed, add a new getter function and include it in `get_all_topic_names()`.
3. Restart the backend service — the new topic will be created on next startup automatically.
