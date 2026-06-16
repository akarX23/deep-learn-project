"""Mode-specific prompt templates for the Teaching Agent."""

from __future__ import annotations

# Each template accepts two placeholders: {topic} and {context}.
# The LLM is instructed to return a single JSON object — no markdown fences,
# no prose outside the JSON.

BEGINNER_PROMPT = """You are a patient teacher explaining a concept to someone with no prior knowledge.

Topic: {topic}
Prior session context: {context}

Explain the topic for a complete beginner. Use simple language, everyday analogies, and avoid jargon.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "A clear 5-part explanation in markdown:\\n1. What it is (in one sentence a 10-year-old could understand)\\n2. A real-world analogy\\n3. Why it matters\\n4. How it works (step by step, no jargon)\\n5. Common mistakes beginners make",
  "diagram": "A Mermaid diagram (graph TD or sequenceDiagram) that visually illustrates the concept. This field is REQUIRED — do not return null.",
  "notes": "A jargon-free bullet list of the 3-5 most important things to remember.",
  "example": "A concrete worked example with plain English commentary explaining each step."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values — do not use literal newlines inside JSON strings.
- The diagram field must contain valid Mermaid syntax starting with 'graph TD' or 'sequenceDiagram'.
- Keep total output within the token budget — be concise but complete.
- If prior session context is provided, briefly connect it to the new topic."""

INTERMEDIATE_PROMPT = """You are a knowledgeable instructor teaching someone who understands the basics.

Topic: {topic}
Prior session context: {context}

Explain the topic at an intermediate level. Use correct technical terminology, discuss trade-offs, and provide a practical code example.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "A 4-part technical explanation in markdown:\\n1. Definition and purpose\\n2. How it works internally\\n3. Trade-offs and when to use it\\n4. Common pitfalls and how to avoid them",
  "diagram": "A Mermaid diagram illustrating structure, flow, or relationships — or null if the topic does not benefit from visual representation.",
  "notes": "Structured markdown notes with subheadings covering: key properties, complexity/performance characteristics, and important variants or alternatives.",
  "example": "A Python code snippet with inline comments explaining each significant line. Include a brief explanation of what the example demonstrates."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values — do not use literal newlines inside JSON strings.
- If diagram is not applicable, set it to null (JSON null, not the string 'null').
- Keep total output within the token budget — prioritise depth over breadth.
- If prior session context is provided, build on it explicitly."""

ADVANCED_PROMPT = """You are an expert peer explaining a concept at a practitioner level.

Topic: {topic}
Prior session context: {context}

Explain the topic for an experienced practitioner. Use formal definitions, discuss edge cases, internals, and non-trivial usage patterns.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "A 5-part expert-level explanation in markdown:\\n1. Formal definition or specification\\n2. Internal mechanics and implementation details\\n3. Complexity analysis or performance characteristics\\n4. Edge cases, failure modes, and subtle invariants\\n5. Relationship to related concepts or alternative approaches",
  "diagram": "A Mermaid diagram only if it communicates something that prose cannot — e.g. a complex state machine, data flow, or architecture. Set to null if prose is sufficient.",
  "notes": "A dense technical reference or cheat-sheet in markdown: key invariants, complexity bounds, gotchas, and non-obvious behaviour.",
  "example": "A non-trivial usage example demonstrating an optimization, architectural pattern, or edge-case handling. Include commentary on why the approach is chosen over simpler alternatives."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values — do not use literal newlines inside JSON strings.
- If diagram is not applicable, set it to null (JSON null, not the string 'null').
- Assume the reader is comfortable with complexity notation, design patterns, and low-level behaviour.
- If prior session context is provided, reference it where directly relevant."""

# Map output_mode strings to their prompt template.
PROMPT_BY_MODE: dict[str, str] = {
    "beginner": BEGINNER_PROMPT,
    "intermediate": INTERMEDIATE_PROMPT,
    "advanced": ADVANCED_PROMPT,
}


# ---------------------------------------------------------------------------
# Reflection (Phase 3) — critique + revision prompt templates
# ---------------------------------------------------------------------------
#
# Critique templates accept {topic}, {output_mode}, {current_output}.
# Revision templates accept {topic}, {output_mode}, {context}, {current_output},
# {revision_instructions}. Every non-placeholder brace is escaped ({{ }}) so the
# templates stay str.format-safe; substituted values (e.g. the JSON in
# {current_output}) are not re-processed by format.


BEGINNER_REFLECTION_PROMPT = """You are a strict reviewer critiquing a {output_mode}-level explanation written for a complete beginner.

Topic: {topic}

Current output (JSON):
{current_output}

Identify concrete, actionable weaknesses. Focus especially on:
- Whether the real-world analogy is apt and genuinely aids understanding.
- Any jargon a complete beginner would not know (must be removed or plainly explained).
- Whether the Mermaid diagram is simple and readable (beginner diagrams must stay simple).
- Whether the worked example is accessible, with plain-English commentary on each step.
- Whether the five-part explanation structure is present and clear.

Return ONLY a JSON object with exactly these fields:

{{
  "quality_score": 7,
  "issues": [
    {{"field": "explanation|diagram|notes|example", "issue": "<specific, concrete weakness>", "severity": "low|medium|high"}}
  ],
  "revision_instructions": "<concise, direct instructions telling the revision step exactly what to fix>"
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- quality_score is an integer from 1 to 10.
- If the output is already strong, return an empty issues list, a high quality_score, and a brief revision_instructions.
- Be specific and actionable: revision_instructions is the only signal the revision step receives.
- Do not rewrite the content yourself — only critique it."""


INTERMEDIATE_REFLECTION_PROMPT = """You are a strict reviewer critiquing a {output_mode}-level explanation written for a learner who knows the basics.

Topic: {topic}

Current output (JSON):
{current_output}

Identify concrete, actionable weaknesses. Focus especially on:
- Technical accuracy and correct use of terminology.
- Correctness and idiomatic quality of the Python code example.
- Completeness of the trade-off analysis (when to use it vs. when not to).
- Whether the how-it-works mechanics are explained at the right depth.
- Whether a diagram is warranted and, if present, accurate.

Return ONLY a JSON object with exactly these fields:

{{
  "quality_score": 7,
  "issues": [
    {{"field": "explanation|diagram|notes|example", "issue": "<specific, concrete weakness>", "severity": "low|medium|high"}}
  ],
  "revision_instructions": "<concise, direct instructions telling the revision step exactly what to fix>"
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- quality_score is an integer from 1 to 10.
- If the output is already strong, return an empty issues list, a high quality_score, and a brief revision_instructions.
- Be specific and actionable: revision_instructions is the only signal the revision step receives.
- Do not rewrite the content yourself — only critique it."""


ADVANCED_REFLECTION_PROMPT = """You are a strict reviewer critiquing a {output_mode}-level explanation written for an experienced practitioner.

Topic: {topic}

Current output (JSON):
{current_output}

Identify concrete, actionable weaknesses. Focus especially on:
- Formal correctness of definitions and any complexity (time/space) claims.
- Coverage of edge cases, failure modes, and subtle invariants.
- Depth of the internals and implementation discussion.
- Whether the example demonstrates genuinely non-trivial usage.
- Whether a diagram, where used, communicates more than prose.

Return ONLY a JSON object with exactly these fields:

{{
  "quality_score": 7,
  "issues": [
    {{"field": "explanation|diagram|notes|example", "issue": "<specific, concrete weakness>", "severity": "low|medium|high"}}
  ],
  "revision_instructions": "<concise, direct instructions telling the revision step exactly what to fix>"
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- quality_score is an integer from 1 to 10.
- If the output is already strong, return an empty issues list, a high quality_score, and a brief revision_instructions.
- Be specific and actionable: revision_instructions is the only signal the revision step receives.
- Do not rewrite the content yourself — only critique it."""


REFLECTION_PROMPT_BY_MODE: dict[str, str] = {
    "beginner": BEGINNER_REFLECTION_PROMPT,
    "intermediate": INTERMEDIATE_REFLECTION_PROMPT,
    "advanced": ADVANCED_REFLECTION_PROMPT,
}


BEGINNER_REVISION_PROMPT = """You are improving an existing {output_mode}-level explanation for a complete beginner, based on reviewer feedback.

Topic: {topic}
Prior session context: {context}

Current output (JSON):
{current_output}

Revision instructions from the reviewer:
{revision_instructions}

Apply the revision instructions to improve the current output. Preserve what already works — do not reinvent from scratch. Keep the beginner structure: (1) one-sentence plain-English summary, (2) real-world analogy, (3) numbered step-by-step walkthrough, (4) reference to the diagram, (5) three key takeaways.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "The improved 5-part explanation in markdown.",
  "diagram": "A simple, valid Mermaid diagram (graph TD or sequenceDiagram). REQUIRED — do not return null.",
  "notes": "A jargon-free bullet list of the most important things to remember.",
  "example": "A concrete worked example with plain-English commentary on each step."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- The diagram field is REQUIRED and must contain valid Mermaid starting with 'graph TD' or 'sequenceDiagram'.
- Address every point in the revision instructions; keep total output within the token budget."""


INTERMEDIATE_REVISION_PROMPT = """You are improving an existing {output_mode}-level explanation for a learner who knows the basics, based on reviewer feedback.

Topic: {topic}
Prior session context: {context}

Current output (JSON):
{current_output}

Revision instructions from the reviewer:
{revision_instructions}

Apply the revision instructions to improve the current output. Preserve what already works — do not reinvent from scratch. Keep the intermediate structure: precise definition, how-it-works mechanics with correct terminology, a Python code example, and trade-off analysis.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "The improved technical explanation in markdown.",
  "diagram": "A Mermaid diagram illustrating structure/flow, or null if the topic does not benefit from one.",
  "notes": "Structured markdown notes with subheadings (key properties, complexity, variants).",
  "example": "A Python code snippet with inline comments explaining each significant line."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- If a diagram is not applicable, set it to null (JSON null, not the string 'null').
- Address every point in the revision instructions; keep total output within the token budget."""


ADVANCED_REVISION_PROMPT = """You are improving an existing {output_mode}-level explanation for an experienced practitioner, based on reviewer feedback.

Topic: {topic}
Prior session context: {context}

Current output (JSON):
{current_output}

Revision instructions from the reviewer:
{revision_instructions}

Apply the revision instructions to improve the current output. Preserve what already works — do not reinvent from scratch. Keep the advanced structure: formal definition, internal mechanics with time/space complexity, edge cases and failure modes, real-world implications, and a pointer to further exploration.

Return ONLY a JSON object with exactly these fields:

{{
  "explanation": "The improved expert-level explanation in markdown.",
  "diagram": "A Mermaid diagram only if it communicates more than prose (e.g. a state machine or data flow); otherwise null.",
  "notes": "A dense technical reference / cheat-sheet in markdown.",
  "example": "A non-trivial usage example (optimization, edge-case handling, or architectural pattern) with commentary."
}}

Rules:
- Output valid JSON only. No markdown code fences. No text before or after the JSON. Escape all newlines as \\n within string values.
- If a diagram is not applicable, set it to null (JSON null, not the string 'null').
- Address every point in the revision instructions; keep total output within the token budget."""


REVISION_PROMPT_BY_MODE: dict[str, str] = {
    "beginner": BEGINNER_REVISION_PROMPT,
    "intermediate": INTERMEDIATE_REVISION_PROMPT,
    "advanced": ADVANCED_REVISION_PROMPT,
}
