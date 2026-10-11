from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import database, models, schemas, crud
from . import generator
from .generator import TemplateGenerator


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: purane questions ke embeddings backfill karo
    db = database.SessionLocal()
    try:
        n = crud.backfill_embeddings(db)
        print(f"[startup] Backfilled embeddings for {n} question(s).")
    finally:
        db.close()
    yield


models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="Question Generator + Duplicate Detector",
    lifespan=lifespan,
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/questions", response_model=schemas.QuestionOut)
def add_question(payload: schemas.QuestionCreate, db: Session = Depends(database.get_db)):
    return crud.create_question(db, payload)


@app.get("/questions", response_model=list[schemas.QuestionOut])
def get_all(db: Session = Depends(database.get_db)):
    return crud.list_questions(db)


@app.get("/questions/{qid}", response_model=schemas.QuestionOut)
def get_one(qid: int, db: Session = Depends(database.get_db)):
    q = crud.get_question(db, qid)
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    return q


@app.post("/detect-duplicate", response_model=schemas.DuplicateCheckResponse)
def check_duplicate(payload: schemas.DuplicateCheckRequest, db: Session = Depends(database.get_db)):
    return crud.detect_duplicate(db, payload.content, payload.threshold)

# Singleton backend (swap to OpenAIGenerator later if key available)
_backend = TemplateGenerator()


@app.post("/generate", response_model=schemas.GenerateResponse)
def generate_question(payload: schemas.GenerateRequest, db: Session = Depends(database.get_db)):
    result = generator.generate_with_avoidance(
        db=db,
        topic=payload.topic,
        backend=_backend,
        max_attempts=payload.max_attempts,
        threshold=payload.threshold,
    )
    return result