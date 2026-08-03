from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("/", response_model=List[schemas.NoteOut])
def list_notes(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Note).filter(models.Note.user_id == user.id).order_by(models.Note.created_at.desc()).all()


@router.post("/", response_model=schemas.NoteOut)
def create_note(note_in: schemas.NoteCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    note = models.Note(user_id=user.id, title=note_in.title, content=note_in.content)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


@router.delete("/{note_id}")
def delete_note(note_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"ok": True}
