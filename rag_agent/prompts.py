"""Prompt templates used by the RAG agent."""

IMAGE_DESCRIPTION_PROMPT = (
    "You are analyzing a textbook image for a study topic. "
    "Describe only content relevant to the topic below. "
    "Topic: {user_prompt}. "
    "Keep response concise, factual, and useful for study notes."
)

MATERIAL_COMPILATION_PROMPT = (
    "You are compiling study material from extracted PDF pages. "
    "Use the provided retained page context to produce one coherent markdown document. "
    "Requirements: clear section headings, no redundancy, include inline tables when present, "
    "and preserve meaningful image descriptions. "
    "User topic: {user_prompt}.\n\n"
    "Retained page context:\n{context}"
)
