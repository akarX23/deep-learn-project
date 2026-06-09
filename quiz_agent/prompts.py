"""LLM prompt templates for the Quiz Agent."""

from __future__ import annotations

QUESTION_GENERATION_PROMPT = """You are an expert quiz designer for an AI Tutor application.

Your task: Generate a complete, structured quiz from the teaching content provided below.

TEACHING CONTENT:
{teaching_content}

TOPIC: {topic}

REQUIREMENTS:
- Generate exactly {mcq_single_count} MCQ single-answer questions (type: "mcq-single")
- Generate exactly {mcq_multi_count} MCQ multiple-answer questions (type: "mcq-multi")
- Generate exactly 4 descriptive questions (type: "descriptive")
- All questions MUST be grounded strictly in the teaching content — no external facts
- Every question MUST include a sub_concept tag naming the sub-topic it tests
- Assign max_points: 1 for each MCQ single, 2 for each MCQ multi, 5 for each descriptive

For MCQ single-answer questions:
- Provide exactly 4 options
- Mark exactly 1 option as is_correct: true
- For every option, provide an explanation:
  - Correct option: explain WHY it is correct
  - Incorrect options: explain WHY they are wrong (concise, topic-grounded)
- Provide topic_deep_dive: a 3-5 sentence explanation of the concept, used when learner answers wrong

For MCQ multiple-answer questions:
- Provide 4-6 options
- Mark 2 or more as is_correct: true
- For every option provide an explanation (same rules as above)
- Provide topic_deep_dive for the question

For descriptive questions:
- Provide a rubric: list of 4-6 key points expected in a complete answer (~150 words)
- No options or topic_deep_dive needed

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "mcq-single",
      "prompt": "...",
      "sub_concept": "...",
      "max_points": 1,
      "topic_deep_dive": "...",
      "options": [
        {{"id": "q1a", "text": "...", "is_correct": true, "explanation": "..."}},
        {{"id": "q1b", "text": "...", "is_correct": false, "explanation": "..."}},
        {{"id": "q1c", "text": "...", "is_correct": false, "explanation": "..."}},
        {{"id": "q1d", "text": "...", "is_correct": false, "explanation": "..."}}
      ]
    }},
    {{
      "id": "q9",
      "type": "descriptive",
      "prompt": "...",
      "sub_concept": "...",
      "max_points": 5,
      "rubric": ["key point 1", "key point 2", "..."]
    }}
  ]
}}
"""

DESCRIPTIVE_GRADING_PROMPT = """You are an expert educational assessor for an AI Tutor application.

Your task: Grade the learner's descriptive answers against the provided rubrics.

TOPIC: {topic}

ANSWERS TO GRADE:
{answers_block}

For each answer:
- Score it against its rubric (0 to max_score)
- Provide a model_answer: the ideal complete response
- Provide feedback: brief qualitative comment referencing what the learner covered and what they missed

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "grades": [
    {{
      "question_id": "...",
      "score": <integer>,
      "max_score": <integer>,
      "model_answer": "...",
      "feedback": "..."
    }}
  ]
}}
"""
