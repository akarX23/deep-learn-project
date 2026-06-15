"""Prompt templates for the planner agent."""

LEVEL_QUIZ_INFERENCE_PROMPT = """Given the user prompt below, determine:
1. The user's knowledge level: one of "beginner", "intermediate", or "advanced"
2. A confidence score between 0.0 and 1.0
3. Whether the user is requesting a quiz/test/assessment

If the user has explicitly stated their level, use that. Otherwise, infer the level based on the content and phrasing of the prompt. If the prompt is ambiguous, then keep the confidence score very low.
Increase the confidence score only if the user has provided enough detail on what they would like to learn, or if the prompt contains specific jargon or references that indicate a certain level of expertise. 
If the user is asking for a quiz/test/assessment, set quiz_requested to true.

Do not think at all on this problem. The focus is to provide the answer as fast as possible.
/no_think

Respond ONLY with a JSON object:
{{"level": "...", "confidence": 0.0, "quiz_requested": false}}

User prompt: {user_prompt}
"""
