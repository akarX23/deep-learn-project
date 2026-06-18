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


QUESTION_STEMS_PROMPT = """You are an expert quiz designer for an AI Tutor application.

Your task: Generate quiz question stems from the teaching content.

TEACHING CONTENT:
{teaching_content}

TOPIC: {topic}

REQUIREMENTS:
- Generate exactly {mcq_single_count} MCQ single-answer questions (type: "mcq-single")
- Generate exactly {mcq_multi_count} MCQ multiple-answer questions (type: "mcq-multi")
- Generate exactly 4 descriptive questions (type: "descriptive")
- All questions MUST be grounded strictly in the teaching content — no external facts
- Every question MUST include: id, type, prompt, sub_concept, max_points
- max_points rules: 1 for each mcq-single, 2 for each mcq-multi, 5 for each descriptive
- For descriptive questions include a rubric list of 4-6 key points
- For MCQ questions DO NOT include options and DO NOT include topic_deep_dive yet

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "mcq-single",
      "prompt": "...",
      "sub_concept": "...",
      "max_points": 1
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


MCQ_OPTIONS_PROMPT = """You are an expert quiz designer for an AI Tutor application.

Your task: Complete one MCQ question by generating options and explanations.

TEACHING CONTENT:
{teaching_content}

TOPIC: {topic}

QUESTION TO COMPLETE:
- id: {question_id}
- type: {question_type}
- prompt: {question_prompt}
- sub_concept: {sub_concept}
- max_points: {max_points}

REQUIREMENTS:
- Ground everything strictly in the teaching content
- Include topic_deep_dive: a 3-5 sentence explanation for remediation
- If type is "mcq-single":
  - provide exactly 4 options
  - mark exactly 1 option as is_correct=true
- If type is "mcq-multi":
  - provide 4-6 options
  - mark at least 2 options as is_correct=true
- Every option must include:
  - id
  - text
  - is_correct
  - explanation (why correct or incorrect)

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "options": [
    {{"id": "q1a", "text": "...", "is_correct": true, "explanation": "..."}},
    {{"id": "q1b", "text": "...", "is_correct": false, "explanation": "..."}}
  ],
  "topic_deep_dive": "..."
}}
"""

DESCRIPTIVE_GRADING_PROMPT = """You are an expert educational assessor for an AI Tutor application.

Your task: Grade the learner's descriptive answers against the provided rubrics.

TOPIC: {topic}

ANSWERS TO GRADE:
{answers_block}

For each answer:
- Score it against its rubric (0 to max_score)
- Provide a confidence_score between 0.0 and 1.0 representing how confidently the learner demonstrated understanding
- Provide a model_answer: the ideal complete response
- Provide feedback: brief qualitative comment referencing what the learner covered and what they missed

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "grades": [
    {{
      "question_id": "...",
      "score": <integer>,
      "max_score": <integer>,
      "confidence_score": <float 0.0-1.0>,
      "model_answer": "...",
      "feedback": "..."
    }}
  ]
}}
"""


SWOT_ANALYSIS_PROMPT = """You are an expert educational psychologist for an AI Tutor application.

Based on the learner's quiz performance data below, generate a concise SWOT analysis of their learning.

TOPIC: {topic}
OVERALL SCORE: {overall_score}/{max_score} ({overall_percentage:.1f}%)
STRONG SUB-CONCEPTS (scored >= 50%): {strong_concepts}
WEAK SUB-CONCEPTS (scored < 50%): {weak_concepts}
RECOMMENDED ACTION: {recommended_action}

Generate a SWOT analysis with 2-4 bullet points per quadrant, grounded in the quiz data above.

- Strengths: what the learner clearly understands
- Weaknesses: specific gaps or misconceptions revealed
- Opportunities: areas where targeted review could quickly improve understanding
- Threats: risks to long-term retention if weaknesses are not addressed

RESPONSE FORMAT — return ONLY valid JSON, no markdown fences:
{{
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "opportunities": ["...", "..."],
  "threats": ["...", "..."]
}}
"""
