# Question Generator + Duplicate Detector

Production-grade AI service that **generates new exam questions** while preventing duplicates against an existing corpus. Built for the Induseuro Labs intern assignment (Question 2).

## Features

- **Question catalog** — CRUD API for storing questions with tags
- **Semantic embeddings** — each question is embedded via `sentence-transformers/all-MiniLM-L6-v2` (384-dim)
- **Exact duplicate detection** — normalization + hash comparison
- **Semantic duplicate detection** — cosine similarity with configurable threshold
- **Generation-time avoidance** — retrieve similar existing questions, inject into generation prompt, verify with detector, retry if duplicate
- **Pluggable generation backends** — template-based (offline) + OpenAI (drop-in)
- **Interactive API docs** — auto-generated Swagger UI at `/docs`

## Architecture
