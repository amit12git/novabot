"""Phase 2: Augmentation + Generation.

Augmentation = assemble a prompt containing the retrieved chunks.
Generation   = send that prompt to a local LLM via Ollama.

Prerequisites:
    brew install ollama
    ollama pull llama3.2      # ~2GB, good quality for its size
    ollama serve              # if not already running (brew usually auto-starts it)
    pip install requests
"""

import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3.2"

# ---------- AUGMENTATION ----------

PROMPT_TEMPLATE = """You are a helpful assistant. Answer the question using ONLY the context below.
If the answer is not in the context, say "I don't have that information in the documents."

Context:
{context}

Question: {question}

Answer:"""


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Assemble the augmented prompt: retrieved chunks + user question.

    Each chunk is labeled with its source file so the model can cite it.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}: {chunk['source']}]\n{chunk['text']}")
    context = "\n\n".join(context_parts)
    return PROMPT_TEMPLATE.format(context=context, question=question)


# ---------- GENERATION ----------

def generate(prompt: str) -> str:
    """Send the prompt to Ollama and return the model's answer."""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # low = factual, grounded answers
            },
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json()["response"].strip()
