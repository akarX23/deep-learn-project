"""Prompt templates used by the RAG agent."""

IMAGE_DESCRIPTION_PROMPT = (
    "You are an educational content analyst. "
    "Describe the provided image(s) concisely, focusing on diagrams, figures, "
    "equations, charts, and visual data relevant for study material. "
    "If an image is decorative or not useful, state that briefly.\n\n"
    "Study topic context: {user_prompt}"
)

MATERIAL_COMPILATION_PROMPT = (
    "You are compiling study material from extracted PDF pages. "
    "Use the provided retained page context to produce one coherent markdown document. "
    "Requirements: clear section headings, no redundancy, include inline tables when present, "
    "and preserve meaningful image descriptions. "
    "User topic: {user_prompt}.\n\n"
    "Retained page context:\n{context}"
)
