# Quickstart: Planner Agent

**Feature**: `004-planner-agent`  
**Branch**: `005-add-planner-agent`  
**Date**: 2026-06-13

---

## Prerequisites

- Python 3.11+, `.venv` activated (`source .venv/bin/activate`)
- Kafka running locally (`docker-compose up kafka`)
- Environment variables set (see below)
- `langgraph>=1.2.0` and `langchain-core>=1.4.0` in `requirements.txt`

---

## Environment Variables

```bash
# LLM for level inference and quiz detection
export PLANNER_TEXT_MODEL=gpt-4o-mini
export PLANNER_TEXT_API_BASE=http://localhost:8080/v1   # or remote
export PLANNER_TEXT_API_KEY=your-api-key

# Inference settings
export PLANNER_TEXT_TEMPERATURE=0.1
export PLANNER_TEXT_MAX_TOKENS=200
export PLANNER_LEVEL_CONFIDENCE_THRESHOLD=0.75

# Kafka
export PLANNER_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

---

## Running the Planner Worker

The worker consumes `init-planner` and invokes the LangGraph workflow per request:

```bash
python -m planner_agent.worker
```

The worker polls `init-planner` indefinitely. Stop with Ctrl-C.

---

## Graph Flow Reference

```
[START]
  └─► infer_level
        ├─[low confidence]─► produce clarify-user-level event ──► [END]
        └─[finalized]──────► has file_paths?
              ├─[yes]─► run_rag ──produces rag-request──► interrupt()
              │          (future: resumed by rag-complete consumer)
              └─[no]──► fan_out_teach
                    └─► teach_node × N (one per user level, via Send API)
                          ──produces teaching-request per level──► interrupt()
                          (future: resumed by teaching-complete consumer)
                          └─► quiz_requested?
                                ├─[yes]─► run_quiz ──produces quiz-request──► interrupt()
                                │          (future: resumed by quiz-complete consumer)
                                └─[no]──► finish
                                              └──produces workflow-complete──► [END]
```

**Current phase**: Graph builds and runs through `infer_level`. Interrupt nodes (`run_rag`, `teach_node`, `run_quiz`) publish Kafka events and pause. Resumption uses `Command(resume=payload)` from `langgraph.types` — this is a **future phase** TODO, implemented when the Kafka consumer is added.

---

## Running Tests

```bash
pytest planner_agent/tests -q
```

---

## Triggering a Request Manually

Produce a test event to `init-planner` to watch the planner fire:

```bash
python - <<'EOF'
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode(),
)
producer.send("init-planner", {
    "user_prompt": "Explain backpropagation to me",
    "user_level": [],
    "sid": "test-session-1",
    "file_paths": [],
})
producer.flush()
print("Event sent.")
EOF
```

**With pre-defined levels** (skips inference):

```bash
python - <<'EOF'
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode(),
)
producer.send("init-planner", {
    "user_prompt": "Explain backpropagation, and give me a quiz",
    "user_level": ["beginner", "advanced"],
    "sid": "test-session-2",
    "file_paths": ["/uploads/lecture.pdf"],
})
producer.flush()
print("Event sent.")
EOF
```

Expected: RAG event → `rag-request` topic → interrupt; then two Teaching events → `teaching-request` topic (beginner + advanced) → interrupt; then Quiz event (quiz intent detected) → `quiz-request` topic → interrupt.

---

## Module Responsibilities

| Module | Role |
|---|---|
| `planner_agent/worker.py` | Entry point: Kafka consumer loop for `init-planner`, calls `PlannerAgent.run()` per message |
| `planner_agent/agent.py` | `PlannerAgent` class: `PlannerState` TypedDict (internal, not shared), `StateGraph` build, all node implementations |
| `planner_agent/config.py` | `get_llm_config()` reading `PLANNER_TEXT_*` env vars |
| `planner_agent/kafka.py` | Kafka producer factory (`make_producer()`) |
| `planner_agent/prompts.py` | `LEVEL_QUIZ_INFERENCE_PROMPT` template |
| `project/schemas.py` | `UserLevelEnum`, `LevelInferenceResult`, `TeachingRequestEvent`, `QuizRequestEvent`, `ClarifyUserLevelEvent`, `WorkflowCompleteEvent` (shared Kafka contracts only) |
| `project/topics.py` | `PlannerAgentTopics`, `AgentCompletionTopics` enums + updated `get_all_topic_names()` |
