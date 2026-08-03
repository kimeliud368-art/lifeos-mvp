from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth_router, tasks, notes, chat

# Creates tables if they don't exist yet (fine for MVP; use Alembic migrations later)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LifeOS AI - MVP API")

# Allow the Flutter app (mobile/desktop/web) to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(tasks.router)
app.include_router(notes.router)
app.include_router(chat.router)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "LifeOS AI MVP backend"}
