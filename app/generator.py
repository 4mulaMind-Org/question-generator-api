"""
Question generation with duplicate-avoidance.

Two backends:
  - TemplateGenerator: no API key needed, uses topic-specific templates
  - OpenAIGenerator:   uses OpenAI API (plug in later)

The generate_with_avoidance() function is backend-agnostic.
"""
import random
from typing import Protocol
from sqlalchemy.orm import Session
from . import crud


# ---------- Backend interface ----------

class QuestionBackend(Protocol):
    def generate(self, topic: str, avoid_examples: list[str]) -> str:
        """Generate a new question on `topic`, avoiding questions similar to `avoid_examples`."""
        ...


# ---------- Template backend (no API) ----------

TEMPLATES = {
    "physics": [
        "Define {topic} and explain its significance in physics.",
        "What are the key properties of {topic}?",
        "How would you demonstrate {topic} experimentally?",
        "State two real-world applications of {topic}.",
        "Compare {topic} with a related phenomenon.",
        "Derive the mathematical expression for {topic}.",
        "What happens to {topic} when the medium changes?",
        "Explain the laws governing {topic} with an example.",
    ],
    "math": [
        "Prove the theorem related to {topic}.",
        "Find the general solution for equations involving {topic}.",
        "Give two practical applications of {topic}.",
    ],
    "default": [
        "Explain {topic} in your own words.",
        "What is the significance of {topic}?",
        "List three key facts about {topic}.",
        "Describe a real-world scenario involving {topic}.",
    ],
}


class TemplateGenerator:
    """Picks templates based on topic; skips ones matching avoid_examples (roughly)."""

    def generate(self, topic: str, avoid_examples: list[str]) -> str:
        # Pick template family by rough keyword match
        family = "default"
        tl = topic.lower()
        if any(k in tl for k in ["light", "motion", "force", "energy", "physics", "reflection"]):
            family = "physics"
        elif any(k in tl for k in ["algebra", "geometry", "calculus", "math"]):
            family = "math"

        templates = TEMPLATES[family]
        random.shuffle(templates)

        avoid_lower = [a.lower() for a in avoid_examples]
        for tpl in templates:
            candidate = tpl.format(topic=topic)
            # crude avoidance: skip if exact substring overlap with any avoid example
            if not any(candidate.lower() in a or a in candidate.lower() for a in avoid_lower):
                return candidate

        # fallback if everything matched
        return f"Explain {topic} with a novel example."


# ---------- OpenAI backend (optional, for later) ----------

class OpenAIGenerator:
    """Requires OPENAI_API_KEY env var. Wired later."""

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model

    def generate(self, topic: str, avoid_examples: list[str]) -> str:
        # Placeholder — main proper impl baad mein de dunga jab key ho
        from openai import OpenAI
        client = OpenAI()

        avoid_block = "\n".join(f"- {q}" for q in avoid_examples) or "(none yet)"

        prompt = (
            f"Generate ONE new exam-style question about: {topic}.\n"
            f"Do NOT duplicate or paraphrase any of these existing questions:\n"
            f"{avoid_block}\n\n"
            f"Return only the question text, no numbering, no quotes."
        )

        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
        )
        return resp.choices[0].message.content.strip()


# ---------- Orchestrator: generation + avoidance ----------

def generate_with_avoidance(
    db: Session,
    topic: str,
    backend: QuestionBackend,
    max_attempts: int = 5,
    threshold: float = 0.85,
) -> dict:
    """
    1. Retrieve top similar existing questions (avoid_examples)
    2. Ask backend to generate a new question
    3. Check via detector
    4. If duplicate → retry up to max_attempts
    """
    # Get similar existing questions to feed as "avoid these"
    # Simple approach: just take last N from DB (production: vector search)
    recent = crud.list_questions(db)[-10:]
    avoid_examples = [q.content for q in recent]

    attempts = []
    for attempt in range(1, max_attempts + 1):
        candidate = backend.generate(topic, avoid_examples)
        check = crud.detect_duplicate(db, candidate, threshold=threshold)

        attempts.append({
            "attempt": attempt,
            "candidate": candidate,
            "is_duplicate": check["is_duplicate"],
            "match_type": check["match_type"],
            "similarity": check["top_match"]["similarity"] if check["top_match"] else None,
        })

        if not check["is_duplicate"]:
            return {
                "success": True,
                "question": candidate,
                "attempts": attempts,
                "total_attempts": attempt,
            }

        # add this failed candidate to avoid list so next try differs
        avoid_examples.append(candidate)

    return {
        "success": False,
        "question": None,
        "attempts": attempts,
        "total_attempts": max_attempts,
        "reason": "Could not generate a non-duplicate question in max attempts",
    }