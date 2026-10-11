import re
import json
from sqlalchemy.orm import Session
from . import models, schemas
from .embeddings import embed, cosine_similarity


def normalize(text: str) -> str:
    """Lowercase, punctuation hatao, extra space collapse karo."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def create_question(db: Session, payload: schemas.QuestionCreate) -> models.Question:
    vec = embed(payload.content.strip())
    q = models.Question(
        content=payload.content.strip(),
        normalized=normalize(payload.content),
        tags=payload.tags.strip(),
        embedding=json.dumps(vec),
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def list_questions(db: Session):
    return db.query(models.Question).order_by(models.Question.id).all()


def get_question(db: Session, qid: int):
    return db.query(models.Question).filter(models.Question.id == qid).first()


# ---------- Duplicate Detection ----------

def find_exact_duplicate(db: Session, text: str):
    norm = normalize(text)
    return db.query(models.Question).filter(models.Question.normalized == norm).first()


def detect_duplicate(db: Session, text: str, threshold: float = 0.85):
    """
    Returns dict with:
      - is_duplicate: bool
      - match_type: 'exact' | 'semantic' | 'none'
      - top_match: {id, content, similarity} or None
      - all_matches: list of {id, content, similarity} above 0.5
    """
    # 1) Exact check
    exact = find_exact_duplicate(db, text)
    if exact:
        return {
            "is_duplicate": True,
            "match_type": "exact",
            "top_match": {"id": exact.id, "content": exact.content, "similarity": 1.0},
            "all_matches": [{"id": exact.id, "content": exact.content, "similarity": 1.0}],
        }

    # 2) Semantic check
    query_vec = embed(text)
    all_qs = db.query(models.Question).all()

    scored = []
    for q in all_qs:
        if not q.embedding:
            continue
        q_vec = json.loads(q.embedding)
        sim = cosine_similarity(query_vec, q_vec)
        scored.append({"id": q.id, "content": q.content, "similarity": round(sim, 4)})

    scored.sort(key=lambda x: x["similarity"], reverse=True)

    if scored and scored[0]["similarity"] >= threshold:
        return {
            "is_duplicate": True,
            "match_type": "semantic",
            "top_match": scored[0],
            "all_matches": [s for s in scored if s["similarity"] >= 0.5],
        }

    return {
        "is_duplicate": False,
        "match_type": "none",
        "top_match": scored[0] if scored else None,
        "all_matches": [s for s in scored if s["similarity"] >= 0.5],
    }


def backfill_embeddings(db: Session):
    """Startup pe purane questions ke liye embedding generate karo."""
    qs = db.query(models.Question).filter(models.Question.embedding.is_(None)).all()
    for q in qs:
        q.embedding = json.dumps(embed(q.content))
    if qs:
        db.commit()
    return len(qs)