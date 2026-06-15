"""
End-to-end smoke test for the Teaching Agent Kafka integration.

Usage:
    PYTHONPATH=. python teaching_agent/tests/e2e_smoke.py

Prerequisites:
    - Backend service running (topics bootstrapped)
    - Teaching agent worker running in a separate terminal:
          PYTHONPATH=. python teaching_agent/worker.py
    - TEACHING_MODEL set in .env.local or environment
    - BACKEND_KAFKA_BOOTSTRAP_SERVERS set in .env.local (default: localhost:9092)
"""

from __future__ import annotations

import json
import os
import sys
import uuid

from dotenv import load_dotenv

load_dotenv(".env.local", override=False)

BOOTSTRAP_SERVERS = os.getenv("BACKEND_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TEACHING_TOPIC = "teaching"
COMPLETE_TOPIC = "teaching-complete"
TIMEOUT_SECONDS = 90


def run() -> None:
    from kafka import KafkaConsumer, KafkaProducer

    request_id = str(uuid.uuid4())
    payload = {
        "request_id": request_id,
        "session_ctx": {"session_id": "e2e-test-session"},
        "topic": "What is gradient descent?",
        "output_mode": "beginner",
        "context": "",
    }

    # Create consumer FIRST so we catch any message produced after this point.
    # auto_offset_reset="latest" positions us at the current end of the partition.
    consumer = KafkaConsumer(
        COMPLETE_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        consumer_timeout_ms=TIMEOUT_SECONDS * 1000,
        group_id=f"e2e-smoke-{request_id[:8]}",
        enable_auto_commit=False,
    )
    # Initial poll triggers partition assignment and pins the latest offset.
    consumer.poll(timeout_ms=3000)

    # Publish request after consumer is positioned.
    producer = KafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    producer.send(TEACHING_TOPIC, payload)
    producer.flush()
    producer.close()
    print(f"[e2e] Published TeachingRequestEvent  request_id={request_id}")
    print(f"[e2e] Waiting up to {TIMEOUT_SECONDS}s for TeachingCompletionEvent on '{COMPLETE_TOPIC}'...")

    found = False
    for record in consumer:
        msg = record.value
        if msg.get("request_id") != request_id:
            continue  # ignore unrelated messages from concurrent tests

        found = True
        status = msg.get("status", "unknown")
        print(f"\n[e2e] {'SUCCESS' if status == 'ok' else 'RECEIVED (error)'}  status={status}")
        print(f"  request_id:  {msg.get('request_id')}")
        print(f"  topic:       {msg.get('topic')}")
        print(f"  output_mode: {msg.get('output_mode')}")
        print(f"  model:       {msg.get('model')}")
        print(f"  tokens_used: {msg.get('tokens_used')}")
        print(f"  duration_ms: {msg.get('duration_ms')}")
        if status == "ok" and msg.get("content"):
            content = msg["content"]
            explanation = content.get("explanation", "")
            print(f"  explanation: {explanation[:150]}{'...' if len(explanation) > 150 else ''}")
            if content.get("diagram"):
                print(f"  diagram:     (present, {len(content['diagram'])} chars)")
        if msg.get("errors"):
            print(f"  errors:      {msg['errors']}")
        break

    consumer.close()

    if not found:
        print(f"\n[e2e] TIMEOUT — no response for request_id={request_id} after {TIMEOUT_SECONDS}s")
        print("      Check that the teaching agent worker is running and TEACHING_MODEL is set.")
        sys.exit(1)

    sys.exit(0 if found and msg.get("status") == "ok" else 1)


if __name__ == "__main__":
    run()
