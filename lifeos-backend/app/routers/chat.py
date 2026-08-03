import os
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import anthropic

from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"

# Tools the AI can call on the user's behalf
TOOLS = [
    {
        "name": "create_task",
        "description": "Create a to-do task for the user.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string"}},
            "required": ["title"],
        },
    },
    {
        "name": "create_note",
        "description": "Save a note for the user.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["content"],
        },
    },
]


def run_tool(tool_name: str, tool_input: dict, user: models.User, db: Session):
    if tool_name == "create_task":
        task = models.Task(user_id=user.id, title=tool_input["title"])
        db.add(task)
        db.commit()
        return {"status": "created", "task": tool_input["title"]}

    if tool_name == "create_note":
        note = models.Note(
            user_id=user.id,
            title=tool_input.get("title"),
            content=tool_input["content"],
        )
        db.add(note)
        db.commit()
        return {"status": "created", "note": tool_input.get("title") or tool_input["content"][:30]}

    return {"status": "unknown_tool"}


def extract_memory_fact(user_message: str, ai_reply: str, user: models.User, db: Session):
    """Lightweight second call: decide if this exchange contains a durable fact worth remembering."""
    extraction_prompt = f"""Given this exchange, extract ONE durable fact about the user worth
remembering long-term (a goal, preference, project, deadline, or similar) — or say NONE if
there isn't one. Reply with ONLY the fact as a short sentence, or the word NONE. Do not add
any other text.

User: {user_message}
Assistant: {ai_reply}"""

    result = client.messages.create(
        model=MODEL,
        max_tokens=100,
        messages=[{"role": "user", "content": extraction_prompt}],
    )
    fact_text = result.content[0].text.strip()

    if fact_text and fact_text.upper() != "NONE":
        memory = models.Memory(user_id=user.id, fact=fact_text)
        db.add(memory)
        db.commit()


@router.post("/", response_model=schemas.ChatResponse)
def chat(
    chat_in: schemas.ChatRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    # 1. Pull existing memory to give the AI context
    memories = db.query(models.Memory).filter(models.Memory.user_id == user.id).all()
    memory_text = "\n".join(f"- {m.fact}" for m in memories) or "(nothing remembered yet)"

    system_prompt = f"""You are LifeOS, a friendly, reliable personal assistant.
Here is what you remember about this user so far:
{memory_text}

Use this context naturally when relevant. You can create tasks or notes for the user
using the provided tools when they ask you to remember or track something actionable."""

    # 2. Save the user's message
    db.add(models.ChatMessage(user_id=user.id, role="user", content=chat_in.message))
    db.commit()

    # 3. Call Claude with tool access
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        tools=TOOLS,
        messages=[{"role": "user", "content": chat_in.message}],
    )

    reply_text = ""
    for block in response.content:
        if block.type == "text":
            reply_text += block.text
        elif block.type == "tool_use":
            run_tool(block.name, block.input, user, db)

    if not reply_text:
        reply_text = "Done!"

    # 4. Save the assistant's reply
    db.add(models.ChatMessage(user_id=user.id, role="assistant", content=reply_text))
    db.commit()

    # 5. Extract any durable fact for long-term memory
    extract_memory_fact(chat_in.message, reply_text, user, db)

    return {"reply": reply_text}


@router.get("/memory", response_model=list[schemas.MemoryOut])
def list_memory(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    return db.query(models.Memory).filter(models.Memory.user_id == user.id).order_by(models.Memory.created_at.desc()).all()


@router.delete("/memory/{memory_id}")
def delete_memory(memory_id: str, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    memory = db.query(models.Memory).filter(models.Memory.id == memory_id, models.Memory.user_id == user.id).first()
    if memory:
        db.delete(memory)
        db.commit()
    return {"ok": True}
