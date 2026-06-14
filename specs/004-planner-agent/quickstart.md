# Quickstart: Planner Agent

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-14

## Prerequisites

- Python 3.11+
- Active virtual environment:

```bash
source .venv/bin/activate
```

- Kafka running and topics bootstrapped
- Planner environment variables configured

## Environment Variables

```bash
export PLANNER_TEXT_PROVIDER=hosted_vllm
export PLANNER_TEXT_MODEL=gpt-4o-mini
export PLANNER_TEXT_API_BASE=http://localhost:8080/v1
export PLANNER_TEXT_API_KEY=dev-key
export PLANNER_TEXT_TEMPERATURE=0.1
export PLANNER_TEXT_MAX_TOKENS=200
export PLANNER_LEVEL_CONFIDENCE_THRESHOLD=0.75
export PLANNER_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

`planner_agent/config.py` loads `.env.local` with `override=False` so system-set values remain authoritative.

## Run the Worker

Single worker, single consumer (init + completion topics):

```bash
python -m planner_agent.worker
```

## Runtime Behavior

- Worker subscribes to `init-planner`, `rag-complete`, `teaching-complete`, `quiz-complete`.
- Each message is routed by `message.topic`.
- Payload is schema-validated by topic.
- `init-planner` invokes `PlannerAgent.run(...)`.
- Completion topics invoke `PlannerAgent.resume(...)`.
- Dispatch events are produced with Kafka key=`request_id`.
- Graph pauses using `interrupt()` semantics and resumes via `Command(resume=...)`.

## Quality Gates

```bash
pytest planner_agent/tests -q
ruff check project planner_agent
ruff format --check project planner_agent
python -m compileall project planner_agent -q
```

## Smoke Test Input

```json
{
  "user_prompt": "Explain gradient descent and then quiz me",
  "user_level": ["beginner"],
  "sid": "session-quickstart-1",
  "file_paths": ["/tmp/notes.pdf"]
}
```

Expected flow:
1. `init-planner` consumed
2. `rag` dispatch (if files present)
3. `teaching-request` dispatch per level
4. `quiz-request` dispatch when requested
5. completion topics consumed and resumed
6. `workflow-complete` emitted
