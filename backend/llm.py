"""
llm.py
------
Thin wrapper around Groq's chat completion API (OpenAI-compatible format).
Kept isolated in its own module so swapping providers later (Gemini, etc.)
only means changing this file - good talking point for the "performance/
benchmarking" extra credit if you compare providers later.
"""

import os
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Llama 3.1 8B is fast and free-tier friendly. Swap for other Groq models
# (e.g. llama-3.3-70b-versatile) if you want to compare quality/speed.
MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT_TEMPLATE = """You are a focused study assistant helping a student learn the subject: "{subject}".

Rules you must follow:
- Stay strictly on the topic of {subject}. If the user goes off-topic, gently redirect them.
- Default mode: act like a flashcard/quiz partner. Ask short questions, wait for the
  student's answer, then tell them if they were right or wrong and explain briefly.
- If the student asks you to explain a concept instead of quizzing them, explain it
  clearly and concisely, then offer to quiz them on it.
- Keep answers short (a few sentences max) - this is a chat interface, not an essay.
- Be encouraging but honest about mistakes.
"""


def build_system_prompt(subject: str) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(subject=subject)


def get_chat_reply(subject: str, history: list[dict]) -> str:
    """
    history: list of {"role": "user"|"assistant", "content": str}
    Returns the assistant's reply text.
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Check your .env file.")

    messages = [{"role": "system", "content": build_system_prompt(subject)}] + history

    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
