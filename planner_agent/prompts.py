"""Prompt templates for the planner agent."""

LEVEL_QUIZ_INFERENCE_PROMPT = """Given the user prompt below, determine:
1. The user's knowledge level: one of "beginner", "intermediate", or "advanced"
2. A confidence score between 0.0 and 1.0
3. Whether the user is requesting a quiz/test/assessment

Respond ONLY with a JSON object:
{{"level": "...", "confidence": 0.0, "quiz_requested": false}}

User prompt: {user_prompt}
"""
