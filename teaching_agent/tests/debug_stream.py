"""Debug: call call_llm_stream directly and print raw output."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from teaching_agent.config import get_llm_config
from teaching_agent.helpers import build_messages
from teaching_agent.llm_client import call_llm_stream

config = get_llm_config("beginner")
print(f"model: {config.model}")

messages = build_messages("Say hello in one sentence.")

try:
    chunks = []
    for delta, tokens_used in call_llm_stream(messages, config):
        chunks.append((delta, tokens_used))
        print(f"chunk: {repr(delta)!s:40s}  tokens_used={tokens_used}")
    print(f"\nTotal chunks: {len(chunks)}")
    print(f"Full text: {''.join(d for d, _ in chunks)}")
except RuntimeError as e:
    print(f"RuntimeError: {e}")
except Exception as e:
    print(f"Unexpected error ({type(e).__name__}): {e}")
