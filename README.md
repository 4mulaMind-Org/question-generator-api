# Question Generator + Duplicate Detector

Production-grade AI service that **generates new exam questions** while preventing duplicates against an existing corpus. Built for the Induseuro Labs intern assignment (Question 2).

## Features

- **Question catalog** - CRUD API for storing questions with tags
- **Semantic embeddings** - each question is embedded via `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Exact duplicate detection** - normalization + hash comparison
- **Semantic duplicate detection** - cosine similarity with configurable threshold
- **Generation-time avoidance** - retrieve similar existing questions, inject into generation prompt, verify with detector, retry if duplicate
- **Pluggable generation backends** - template-based (offline) + OpenAI (drop-in)
- **Interactive API docs** - auto-generated Swagger UI at `/docs`

## Architecture

```
FastAPI Layer
   |-- POST /questions             (add question)
   |-- GET  /questions             (list all)
   |-- GET  /questions/{id}        (fetch one)
   |-- POST /detect-duplicate      (exact + semantic check)
   |-- POST /generate              (generation with avoidance)

                 |
        +--------+--------+--------+
        |        |        |        |
      CRUD   Detector  Generator  Embeddings
      (SQLA) (cosine)  (Template/ (MiniLM-
                       LLM)       L6-v2)

                 |
                 v
             SQLite DB
       (embeddings stored as JSON)
```

## Algorithms

### Exact duplicate detection
1. Normalize: lowercase -> strip punctuation -> collapse whitespace
2. Compare normalized strings for equality
3. Similarity score = 1.0

### Semantic duplicate detection
1. Embed both questions with MiniLM-L6-v2 (normalized vectors)
2. Cosine similarity = dot product (since vectors are unit-length)
3. If similarity >= threshold (default 0.85) -> duplicate
4. Return top match + all matches above 0.5 for transparency

### Generation-time avoidance
1. Retrieve top N similar existing questions (avoid_examples)
2. Generate a new candidate via backend (template or LLM)
3. Run duplicate detector on candidate
4. If duplicate -> add candidate to avoid_examples, retry
5. Max 5 attempts, then return failure with attempt log

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI | Async, auto-docs, Pydantic validation |
| ORM | SQLAlchemy 2.0 | Mature, typed, portable |
| DB | SQLite (dev) | Zero setup; swap to Postgres + pgvector in prod |
| Embeddings | sentence-transformers | Free, local, no API key, ~90MB model |
| Vector store | JSON in SQLite | Simple for demo |
| Frontend | Streamlit | Simple browser UI for live demo |

## Setup

### Prerequisites
- Python 3.11+
- pip / venv

### Install

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

First run downloads the embedding model (~90MB) - takes 30-60s.

### Run backend

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs

### Run UI (separate terminal)

```bash
streamlit run streamlit_app.py
```

Open http://localhost:8501

### Docker

```bash
docker compose up --build
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | /health | Liveness check |
| POST | /questions | Add a question to catalog |
| GET | /questions | List all questions |
| GET | /questions/{id} | Fetch one question |
| POST | /detect-duplicate | Check if text is a duplicate |
| POST | /generate | Generate a new question, avoiding duplicates |

### Example: Detect duplicate

```bash
curl -X POST http://127.0.0.1:8000/detect-duplicate \
  -H "Content-Type: application/json" \
  -d '{"content": "What is the reflection of light?"}'
```

Response:

```json
{
  "is_duplicate": true,
  "match_type": "exact",
  "top_match": {"id": 1, "content": "What is reflection of light?", "similarity": 1.0}
}
```

### Example: Generate

```bash
curl -X POST http://127.0.0.1:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "momentum"}'
```

Response:

```json
{
  "success": true,
  "question": "What is the significance of momentum?",
  "total_attempts": 1
}
```

## Trade-offs

- **SQLite + JSON embeddings vs. pgvector** - JSON in SQLite is fine for demo/1000s of questions but O(n) on similarity. Production swap: Postgres + pgvector with HNSW index -> sub-ms at millions of vectors.
- **Template generator vs. LLM** - Template backend is offline, deterministic, and free. LLM backend gives diverse questions but costs money and adds latency. The QuestionBackend protocol lets us swap without touching the orchestrator.
- **Threshold 0.85 vs. tuning** - 0.85 catches paraphrases well but can miss looser rewrites (bounce vs. reflect scored 0.78). Configurable per-request via threshold param.
- **Retry without diversity** - If template backend produces the same output repeatedly, retry fails fast. LLM backend benefits more from retries.

## Scaling

- **Embedding cache** - same input -> same vector; LRU cache on embed()
- **Batch embeddings** - model.encode(list_of_texts) is 10x faster than loop
- **Vector index** - swap JSON store for pgvector / FAISS / Qdrant
- **Async generation** - background task + webhook for LLM backends
- **Sharding by tag** - duplicate check scoped to tag family first

## Tests

```bash
python -m pytest -v
```

Covers: exact duplicate, semantic duplicate, different topic, generation with avoidance.

Expected output: 6 passed

## Project Structure

```
question2/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app + endpoints
│   ├── database.py       # SQLAlchemy engine/session
│   ├── models.py         # ORM models
│   ├── schemas.py        # Pydantic schemas
│   ├── crud.py           # DB operations + duplicate detector
│   ├── embeddings.py     # sentence-transformers wrapper
│   └── generator.py      # generation backends + avoidance orchestrator
├── tests/
│   └── test_api.py
├── streamlit_app.py      # Streamlit UI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .gitignore
└── README.md
```