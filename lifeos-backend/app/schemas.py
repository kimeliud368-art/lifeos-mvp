from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


# --- Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Tasks ---
class TaskCreate(BaseModel):
    title: str
    due_date: Optional[datetime] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = None
    due_date: Optional[datetime] = None


class TaskOut(BaseModel):
    id: str
    title: str
    done: bool
    due_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Notes ---
class NoteCreate(BaseModel):
    title: Optional[str] = None
    content: str


class NoteOut(BaseModel):
    id: str
    title: Optional[str] = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# --- Chat ---
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


class MemoryOut(BaseModel):
    id: str
    fact: str
    category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
